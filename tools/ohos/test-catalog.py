#!/usr/bin/env python3
"""Validate the published package through the official oo index in isolation."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--version', default='24.21.0-ohos.1')
parser.add_argument('--proxy', required=True)
parser.add_argument('--parent', type=Path, help='parent of the temporary install directory')
args = parser.parse_args()
if sys.platform not in ('ohos', 'openharmony'):
    raise SystemExit('Run in the native HarmonyOS terminal')
oo = shutil.which('oo')
if not oo:
    raise SystemExit('oo must already be installed and in PATH')
commands = ('node', 'npm', 'npx', 'corepack')
environment = os.environ.copy()
for key in ('NODE_OPTIONS', 'NODE_PATH', 'LD_PRELOAD', 'LD_LIBRARY_PATH'):
    environment.pop(key, None)
for key in ('HTTPS_PROXY', 'HTTP_PROXY', 'https_proxy', 'http_proxy'):
    environment[key] = args.proxy
environment['NO_PROXY'] = environment['no_proxy'] = 'localhost,127.0.0.1,::1'
environment['OHECO_INDEX_URL'] = 'https://oheco.github.io/oheco-packages/index/v2/index.json'
environment['OHECO_NO_AUTO_UPDATE'] = '1'
with tempfile.TemporaryDirectory(prefix='node catalog space ', dir=args.parent) as temporary:
    root = Path(temporary)
    environment['OHECO_ROOT'] = str(root / 'oheco')
    bin_dir = root / 'oheco/bin'
    environment['PATH'] = str(bin_dir) + os.pathsep + environment['PATH']
    for key, name in (('npm_config_userconfig', 'user.npmrc'),
                      ('npm_config_globalconfig', 'global.npmrc')):
        file = root / name
        file.touch()
        environment[key] = str(file)
    environment['npm_config_cache'] = str(root / 'npm-cache')

    def run(command):
        print('+ ' + shlex.join(map(str, command)), flush=True)
        return subprocess.run(list(map(str, command)), env=environment,
                              cwd=root, check=True, timeout=900)

    run([oo, 'update'])
    run([oo, 'install', f'nodejs@{args.version}', '--no-switch'])
    for name in commands:
        assert not os.path.lexists(bin_dir / name), f'{name} was enabled too early'
        run([bin_dir / f'{name}@{args.version}', '--version'])
    run([oo, 'switch', 'nodejs', args.version])
    for name in commands:
        run([bin_dir / name, '--version'])
    run([bin_dir / 'node', '-e',
         "const a=require('node:assert/strict'); a.equal(process.version,'v24.21.0'); "
         "a.equal(process.platform,'openharmony'); a.equal(process.arch,'arm64'); "
         "console.log('catalog-runtime-ok');"])
    run([bin_dir / 'node', Path(__file__).with_name('smoke.mjs')])
    run([oo, 'list'])
    run([oo, 'remove', f'nodejs@{args.version}'])
    for name in commands:
        assert not os.path.lexists(bin_dir / name)
        assert not os.path.lexists(bin_dir / f'{name}@{args.version}')
    assert not (root / 'oheco/packages/nodejs' / args.version).exists()
    print('PASS official index, install without activation, versioned commands, '
          'switch, regular commands, runtime smoke tests and removal', flush=True)
