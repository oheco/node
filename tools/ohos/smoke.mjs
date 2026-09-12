import assert from 'node:assert/strict';
import { test } from 'node:test';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { pathToFileURL } from 'node:url';
import { spawn, spawnSync } from 'node:child_process';
import { once } from 'node:events';
import { Worker } from 'node:worker_threads';
import * as crypto from 'node:crypto';
import * as zlib from 'node:zlib';
import * as net from 'node:net';
import * as http from 'node:http';
import * as vm from 'node:vm';

await test('HarmonyOS runtime integration', async (t) => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'node-ohos-smoke-'));
  t.after(() => fs.rmSync(tmp, { recursive: true, force: true }));
  console.log(JSON.stringify({ version: process.version, platform: process.platform,
    arch: process.arch, execPath: process.execPath, versions: process.versions }));

  await t.test('native platform and full ICU', () => {
    assert.equal(process.platform, 'openharmony');
    assert.equal(process.arch, 'arm64');
    assert.equal(Intl.DateTimeFormat.supportedLocalesOf(['zh-CN', 'en-US', 'ar', 'ja']).length, 4);
    assert.match(new Intl.DateTimeFormat('zh-CN').format(new Date('2026-09-12T00:00:00Z')), /2026/);
  });

  await t.test('builtin module enumeration and inspector option parsing', () => {
    const code = `const m = require('node:module').builtinModules;
      if (!m.includes('fs') || !m.includes('crypto') || !m.every(x => typeof x === 'string')) process.exit(1);`;
    for (const value of [undefined, 'stderr', 'http', 'stderr,http']) {
      const options = value === undefined ? [] : [`--inspect-publish-uid=${value}`];
      const result = spawnSync(process.execPath, [...options, '-e', code],
        { encoding: 'utf8', timeout: 30000 });
      assert.equal(result.status, 0, result.stderr);
    }
    const empty = spawnSync(process.execPath, ['--inspect-publish-uid=', '-e', code],
      { encoding: 'utf8', timeout: 30000 });
    assert.notEqual(empty.status, 0);
    assert.match(empty.stderr, /requires an argument/);
    for (const value of ['stderr,', ',http', 'stderr,,http', 'invalid']) {
      const result = spawnSync(process.execPath, [`--inspect-publish-uid=${value}`, '-e', code],
        { encoding: 'utf8', timeout: 30000 });
      assert.notEqual(result.status, 0);
      assert.match(result.stderr, /destination can be stderr or http/);
    }
  });

  await t.test('trace event category parsing and output', () => {
    const output = path.join(tmp, 'trace.json');
    const result = spawnSync(process.execPath, ['--trace-events-enabled',
      '--trace-event-categories=v8,node', `--trace-event-file-pattern=${output}`, '-e', '0'],
      { encoding: 'utf8', timeout: 30000 });
    assert.equal(result.status, 0, result.stderr);
    const { traceEvents } = JSON.parse(fs.readFileSync(output, 'utf8'));
    assert.ok(traceEvents.some(event => /(^|,)(v8|node)(,|$)/.test(event.cat)));
  });

  await t.test('ES modules and CommonJS in a path containing spaces', async () => {
    const dir = path.join(tmp, 'module space');
    fs.mkdirSync(dir);
    fs.writeFileSync(path.join(dir, 'number.cjs'), 'module.exports = 42;\n');
    fs.writeFileSync(path.join(dir, 'number.mjs'), 'import n from "./number.cjs"; export default n;\n');
    assert.equal((await import(pathToFileURL(path.join(dir, 'number.mjs')))).default, 42);
  });

  await t.test('JSON object and array fast paths, Unicode and error cases', () => {
    const values = Array.from({ length: 1000 }, (_, index) => ({
      index, name: `item-${index}`, nested: { message: '鸿蒙\n"quoted"' },
      '\u4e2d\u6587': 'value', 'quote"key': 'escaped',
    }));
    for (let pass = 0; pass < 3; pass++) {
      assert.deepEqual(JSON.parse(JSON.stringify(values)), values);
    }
    assert.equal(JSON.stringify([NaN, Infinity, -Infinity, -0]), '[null,null,null,0]');
    assert.equal(JSON.stringify('\ud800'), '"\\ud800"');
    assert.equal(JSON.stringify({ toJSON() { return 42; } }), '42');
    const circular = {};
    circular.self = circular;
    assert.throws(() => JSON.stringify(circular), TypeError);
    assert.throws(() => JSON.stringify(1n), TypeError);
  });

  await t.test('filesystem writes, fsync, rename, symlinks and error paths', () => {
    const file = path.join(tmp, '写入.txt');
    const fd = fs.openSync(file, 'wx');
    fs.writeSync(fd, '鸿蒙\n');
    fs.fsyncSync(fd);
    fs.closeSync(fd);
    const moved = `${file}.moved`;
    fs.renameSync(file, moved);
    assert.equal(fs.readFileSync(moved, 'utf8'), '鸿蒙\n');
    fs.symlinkSync(path.basename(moved), file);
    assert.equal(fs.realpathSync(file), moved);
    assert.throws(() => fs.readFileSync(path.join(tmp, 'missing')), { code: 'ENOENT' });
  });

  await t.test('filesystem change notifications', { timeout: 15000 }, async () => {
    const file = path.join(tmp, 'watched.txt');
    fs.writeFileSync(file, 'before');
    const watcher = fs.watch(file);
    try {
      const event = once(watcher, 'change', { signal: AbortSignal.timeout(10000) });
      fs.appendFileSync(file, '-after');
      await event;
      assert.equal(fs.readFileSync(file, 'utf8'), 'before-after');
    } finally {
      watcher.close();
    }
  });

  await t.test('shared buffer string conversion and UTF-8 decoding', () => {
    const encoded = new TextEncoder().encode('鸿蒙');
    const memory = new SharedArrayBuffer(encoded.length);
    new Uint8Array(memory).set(encoded);
    assert.equal(new TextDecoder('utf-8', { fatal: true }).decode(new Uint8Array(memory)), '鸿蒙');
    assert.equal(Buffer.from(memory).toString('utf8'), '鸿蒙');
    assert.equal(Buffer.from(memory).subarray(3).toString('utf8'), '蒙');
  });

  await t.test('child process cwd, pipes, Unicode and missing executables', () => {
    const child = spawnSync(process.execPath, ['-e', 'console.log(process.cwd()); console.log("鸿蒙")'],
      { cwd: tmp, encoding: 'utf8' });
    assert.equal(child.status, 0, child.stderr);
    assert.equal(child.stdout, `${tmp}\n鸿蒙\n`);
    assert.equal(spawnSync(path.join(tmp, 'missing')).error.code, 'ENOENT');
    const shell = spawnSync('/bin/sh', ['-c', 'printf shell-ok'], { encoding: 'utf8' });
    assert.equal(shell.status, 0, shell.stderr);
    assert.equal(shell.stdout, 'shell-ok');
  });

  await t.test('asynchronous child process and signals', { timeout: 15000 }, async () => {
    const child = spawn(process.execPath, ['-e', 'console.log("ready"); setInterval(() => {}, 1000)']);
    const closed = once(child, 'close');
    await once(child.stdout, 'data');
    child.kill('SIGTERM');
    const [code, signal] = await closed;
    assert.equal(code, null);
    assert.equal(signal, 'SIGTERM');
  });

  await t.test('worker threads and shared memory atomics', { timeout: 15000 }, async () => {
    const shared = new SharedArrayBuffer(4);
    const worker = new Worker(`const {parentPort,workerData} = require('node:worker_threads');
      Atomics.add(new Int32Array(workerData), 0, 42); parentPort.postMessage('done');`,
      { eval: true, workerData: shared });
    const exit = once(worker, 'exit');
    assert.deepEqual(await once(worker, 'message'), ['done']);
    assert.deepEqual(await exit, [0]);
    assert.equal(new Int32Array(shared)[0], 42);
  });

  await t.test('TCP server and client', { timeout: 15000 }, async () => {
    const server = net.createServer(socket => socket.pipe(socket));
    server.listen(0, '127.0.0.1');
    await once(server, 'listening');
    const client = net.connect(server.address().port, '127.0.0.1');
    try {
      await once(client, 'connect');
      const received = once(client, 'data');
      client.write('network-ok');
      assert.equal((await received)[0].toString(), 'network-ok');
    } finally {
      client.destroy();
      await new Promise(resolve => server.close(resolve));
    }
  });

  await t.test('HTTP server and fetch streaming body', { timeout: 15000 }, async () => {
    const server = http.createServer((request, response) => {
      response.setHeader('content-type', 'application/json');
      response.end(JSON.stringify({ url: request.url, message: '鸿蒙' }));
    });
    server.listen(0, '127.0.0.1');
    await once(server, 'listening');
    try {
      const response = await fetch(`http://127.0.0.1:${server.address().port}/check`);
      assert.equal(response.status, 200);
      assert.deepEqual(await response.json(), { url: '/check', message: '鸿蒙' });
    } finally {
      server.closeAllConnections();
      await new Promise(resolve => server.close(resolve));
    }
  });

  await t.test('crypto, secure randomness and compression', () => {
    assert.equal(crypto.createHash('sha256').update('abc').digest('hex'),
      'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
    assert.notDeepEqual(crypto.randomBytes(32), crypto.randomBytes(32));
    assert.equal(zlib.crc32('123456789'), 0xcbf43926);
    const payload = Buffer.from('鸿蒙 '.repeat(1000));
    assert.deepEqual(zlib.gunzipSync(zlib.gzipSync(payload)), payload);
    assert.deepEqual(zlib.brotliDecompressSync(zlib.brotliCompressSync(payload)), payload);
  });

  await t.test('vm cached code', () => {
    const source = '({answer: 6 * 7})';
    const script = new vm.Script(source);
    const cachedData = script.createCachedData();
    const loaded = new vm.Script(source, { cachedData });
    assert.equal(loaded.cachedDataRejected, false);
    assert.equal(loaded.runInNewContext().answer, 42);
  });

  await t.test('WebAssembly compilation and execution', async () => {
    const bytes = Uint8Array.from([0,97,115,109,1,0,0,0,1,7,1,96,2,127,127,1,127,
      3,2,1,0,7,7,1,3,97,100,100,0,0,10,9,1,7,0,32,0,32,1,106,11]);
    const { instance } = await WebAssembly.instantiate(bytes);
    assert.equal(instance.exports.add(19, 23), 42);
  });

  await t.test('V8 optimizing JIT generates and executes machine code', () => {
    const code = `function add(a,b){return a+b;}
      %PrepareFunctionForOptimization(add); add(1,2); add(2,3);
      %OptimizeFunctionOnNextCall(add);
      if(add(19,23)!==42)process.exit(1); console.log('jit-result=42');`;
    const result = spawnSync(process.execPath, ['--allow-natives-syntax', '--trace-opt', '-e', code],
      { encoding: 'utf8', timeout: 30000 });
    assert.equal(result.status, 0, `${result.error ?? ''}\n${result.stderr}`);
    assert.match(result.stdout, /jit-result=42/);
    assert.match(result.stdout, /TURBOFAN|MAGLEV/);
  });

  await t.test('asm.js compiles through the WebAssembly module builder', () => {
    const code = `function Module() {
      'use asm';
      function add(a,b) { a=a|0; b=b|0; return (a+b)|0; }
      return add;
    }
    const add = Module();
    if(add(19,23)!==42 || !%IsAsmWasmCode(Module))process.exit(1);
    console.log('asm-wasm-result=42');`;
    const result = spawnSync(process.execPath, ['--allow-natives-syntax', '--validate-asm', '-e', code],
      { encoding: 'utf8', timeout: 30000 });
    assert.equal(result.status, 0, `${result.error ?? ''}\n${result.stderr}`);
    assert.match(result.stdout, /asm-wasm-result=42/);
  });

  await t.test('minor and major garbage collection preserve live objects', () => {
    const code = `const assert = require('node:assert/strict');
      const kept = Array.from({length: 2000}, (_, i) => ({value:i, text:'keep-'+i}));
      for (let pass=0; pass<20; pass++) {
        globalThis.garbage = Array.from({length:10000}, (_, i) => ({value:i, text:'discard-'+i}));
        if (pass % 5 === 0) gc();
      }
      globalThis.garbage = null; gc();
      for (let i=0; i<kept.length; i++) assert.deepEqual(kept[i], {value:i, text:'keep-'+i});
      console.log('gc-live-objects-ok');`;
    const result = spawnSync(process.execPath, ['--expose-gc', '--trace-gc',
      '--max-old-space-size=96', '--max-semi-space-size=1', '-e', code],
      { encoding: 'utf8', timeout: 60000 });
    assert.equal(result.status, 0, `${result.error ?? ''}\n${result.stderr}`);
    assert.match(result.stdout, /gc-live-objects-ok/);
    assert.match(result.stdout, /Scavenge|Minor Mark-Sweep/);
    assert.match(result.stdout, /Mark-Compact/);
  });

  await t.test('built-in SQLite, transactions and WAL', async () => {
    const { DatabaseSync } = await import('node:sqlite');
    const db = new DatabaseSync(path.join(tmp, 'test.db'));
    try {
      db.exec('PRAGMA journal_mode=WAL; CREATE TABLE t(v INTEGER); BEGIN; INSERT INTO t VALUES(42); COMMIT;');
      assert.equal(db.prepare('SELECT v FROM t').get().v, 42);
      db.exec('BEGIN; INSERT INTO t VALUES(99); ROLLBACK;');
      assert.equal(db.prepare('SELECT COUNT(*) AS n FROM t').get().n, 1);
    } finally {
      db.close();
    }
  });
});
