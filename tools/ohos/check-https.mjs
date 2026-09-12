import assert from 'node:assert/strict';
import net from 'node:net';
import tls from 'node:tls';
import { once } from 'node:events';

const proxy = new URL(process.argv[2]);
assert.equal(proxy.protocol, 'socks5h:');
assert.equal(proxy.username, '');
assert.equal(proxy.password, '');
const hostname = 'registry.npmjs.org';

async function readExactly(socket, length) {
  const parts = [];
  let received = 0;
  while (received < length) {
    const part = socket.read(length - received);
    if (part === null) {
      if (socket.destroyed || socket.readableEnded) throw new Error('Proxy closed the connection');
      await once(socket, 'readable');
    } else {
      parts.push(part);
      received += part.length;
    }
  }
  return Buffer.concat(parts);
}

async function tunnel() {
  const socket = net.connect(Number(proxy.port), proxy.hostname);
  socket.setTimeout(20000, () => socket.destroy(new Error('Proxy connection timed out')));
  try {
    await once(socket, 'connect');
    socket.write(Buffer.from([5, 1, 0]));
    assert.deepEqual(await readExactly(socket, 2), Buffer.from([5, 0]));
    const domain = Buffer.from(hostname);
    socket.write(Buffer.concat([Buffer.from([5, 1, 0, 3, domain.length]), domain, Buffer.from([1, 187])]));
    const reply = await readExactly(socket, 4);
    assert.equal(reply[0], 5);
    assert.equal(reply[1], 0, `SOCKS connection failed: ${reply[1]}`);
    const addressLength = reply[3] === 1 ? 4 : reply[3] === 4 ? 16 :
      reply[3] === 3 ? (await readExactly(socket, 1))[0] : -1;
    assert.ok(addressLength >= 0);
    await readExactly(socket, addressLength + 2);
    return socket;
  } catch (error) {
    socket.destroy();
    throw error;
  }
}

async function request(ca) {
  const socket = await tunnel();
  const secure = tls.connect({ socket, servername: hostname, rejectUnauthorized: true,
    ...(ca === undefined ? {} : { ca }) });
  secure.setTimeout(20000, () => secure.destroy(new Error('TLS request timed out')));
  try {
    await once(secure, 'secureConnect');
    assert.equal(secure.authorized, true);
    const protocol = secure.getProtocol();
    secure.write(`GET /is-number/7.0.0 HTTP/1.1\r\nHost: ${hostname}\r\nConnection: close\r\n\r\n`);
    const chunks = [];
    for await (const chunk of secure) chunks.push(chunk);
    const status = Buffer.concat(chunks).toString().split('\r\n', 1)[0];
    assert.match(status, /^HTTP\/1\.[01] 200 /);
    return { tls: protocol, status };
  } finally {
    secure.destroy();
    socket.destroy();
  }
}

console.log('Verified registry HTTPS through SOCKS5:', await request());
await assert.rejects(request([]), error =>
  ['UNABLE_TO_GET_ISSUER_CERT_LOCALLY', 'UNABLE_TO_VERIFY_LEAF_SIGNATURE',
    'SELF_SIGNED_CERT_IN_CHAIN', 'CERT_UNTRUSTED'].includes(error.code));
console.log('PASS trusted registry certificate accepted; empty trust store rejected');
