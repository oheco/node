#!/usr/bin/env python3
"""Run selected upstream regression tests against a native HarmonyOS Node."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('node', type=Path)
parser.add_argument('--jobs', type=int, default=2)
args = parser.parse_args()
source = Path(__file__).resolve().parents[2]
node = args.node.resolve()
if sys.platform not in ('ohos', 'openharmony'):
    raise SystemExit('Run in the native HarmonyOS terminal')
if not os.environ.get('TMPDIR'):
    raise SystemExit('Set TMPDIR to private writable storage before running')

# Retain the upstream test bodies and status rules. The explicit selection
# covers the compatibility changes and representative runtime facilities.
tests = [
    'buffer-sharedarraybuffer', 'buffer-arraybuffer', 'buffer-alloc',
    'buffer-tostring', 'buffer-tostring-range', 'buffer-copy', 'buffer-fill',
    'buffer-bytelength', 'buffer-isutf8',
    'whatwg-encoding-custom-*',
    'crypto-hash', 'crypto-sign-verify', 'crypto-random', 'crypto-randomuuid',
    'fs-readfile', 'fs-readfile-error', 'fs-readfilesync-utf8-sizes',
    'fs-write-file', 'fs-write-file-flush', 'fs-fsync', 'fs-symlink', 'fs-watch',
    'child-process-fork-and-spawn', 'child-process-spawnsync',
    'child-process-spawnsync-input', 'child-process-spawnsync-shell',
    'worker-message-channel', 'worker-message-channel-sharedarraybuffer',
    'worker-message-port-arraybuffer', 'worker-message-port-wasm-module',
    'stream-pipeline', 'stream-pipeline-process',
    'net-pingpong', 'http-parser',
    'inspector-module', 'inspector-contexts',
    'module-create-require', 'sqlite-transactions', 'sqlite-data-types',
]
environment = os.environ.copy()
for name in ('NODE_OPTIONS', 'NODE_PATH', 'LD_PRELOAD', 'LD_LIBRARY_PATH'):
    environment.pop(name, None)
with tempfile.TemporaryDirectory(prefix='node-upstream-') as temporary:
    environment['NODE_TEST_DIR'] = temporary
    command = [sys.executable, str(source / 'tools/test.py'),
        '--shell', str(node), '--arch', 'arm64', '-j', str(args.jobs),
        '--timeout', '60', '--progress', 'tap', '--report',
        *['parallel/test-' + name for name in tests]]
    print('Running selected upstream regression tests', flush=True)
    result = subprocess.run(command, cwd=source, env=environment)
    raise SystemExit(result.returncode)
