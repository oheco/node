#!/usr/bin/env python3
"""Exercise Node's native terminal REPL in a private PTY."""
import argparse
import os
import pty
import select
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('node', help='path to the native Node executable')
args = parser.parse_args()
master, slave = pty.openpty()
environment = os.environ.copy()
environment['NODE_REPL_HISTORY'] = ''
environment['TERM'] = 'xterm-256color'
process = subprocess.Popen([args.node, '--interactive'], stdin=slave,
    stdout=slave, stderr=slave, env=environment, start_new_session=True)
os.close(slave)
transcript = bytearray()

def expect(needle, timeout=20):
    deadline = time.monotonic() + timeout
    start = len(transcript)
    while needle not in transcript[start:]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f'Missing REPL output: {needle!r}')
        if select.select([master], [], [], remaining)[0]:
            data = os.read(master, 65536)
            if not data:
                raise RuntimeError('REPL closed before the expected output')
            transcript.extend(data)

try:
    expect(b'> ')
    os.write(master, b"console.log('ohos-repl-'+(19+23))\n")
    expect(b'ohos-repl-42')
    os.write(master, b"console.log('tty-state='+process.stdin.isTTY+','+process.stdout.isTTY)\n")
    expect(b'tty-state=true,true')
    os.write(master, b'console.log(String.fromCodePoint(0x9e3f,0x8499))\n')
    expect('\u9e3f\u8499'.encode())
    os.write(master, b'const unfinished =\n')
    expect(b'| ')
    os.write(master, b'\x03')
    expect(b'> ')
    os.write(master, b"console.log('recovered-'+(20+22))\n")
    expect(b'recovered-42')
    os.write(master, b'.exit\n')
    assert process.wait(timeout=10) == 0
    print('PASS PTY REPL, TTY detection, Unicode, Ctrl-C recovery and clean exit')
except BaseException:
    print(transcript.decode(errors='replace'))
    raise
finally:
    if process.poll() is None:
        process.kill()
        process.wait(timeout=10)
    os.close(master)
