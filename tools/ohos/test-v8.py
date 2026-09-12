#!/usr/bin/env python3
"""Run focused, unmodified V8 regressions in the native Node runtime."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('node', type=Path)
args = parser.parse_args()
if sys.platform not in ('ohos', 'openharmony'):
    raise SystemExit('Run in the native HarmonyOS terminal')
node = args.node.resolve()
suite = Path(__file__).resolve().parents[2] / 'deps/v8/test/mjsunit'
tests = [
    'asm/return-types.js',
    'compiler/string-concat-escape.js',
    'compiler/string-concat-escape-nested.js',
    'turboshaft/string-escape-analysis-rematerialize-for-arguments-1.js',
    'turboshaft/string-escape-analysis-rematerialize-for-arguments-2.js',
]
# These synchronous tests use the standard mjsunit assertions and V8 intrinsics,
# without d8-specific host APIs. Execute each in a fresh process and retain the
# upstream flags and sloppy-script semantics (not CommonJS module wrapping).
runner = """
const fs = require('node:fs');
const vm = require('node:vm');
for (const filename of process.argv.slice(1)) {
  vm.runInThisContext(fs.readFileSync(filename, 'utf8'), { filename });
}
"""
environment = os.environ.copy()
for key in ('NODE_OPTIONS', 'NODE_PATH', 'LD_PRELOAD', 'LD_LIBRARY_PATH'):
    environment.pop(key, None)
for name in tests:
    file = suite / name
    flags = []
    for line in file.read_text().splitlines():
        if line.startswith('// Flags: '):
            flags.extend(shlex.split(line.removeprefix('// Flags: ')))
    print('V8 regression:', name, flush=True)
    subprocess.run([str(node), *flags, '-e', runner,
                    str(suite / 'mjsunit.js'), str(file)],
                   env=environment, check=True, timeout=60)
print(f'PASS {len(tests)} upstream V8 regression files', flush=True)
