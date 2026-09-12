#!/usr/bin/env python3
"""Package the native build with relocatable npm entry points and local headers."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--build-root', type=Path, default=Path(os.environ.get(
    'NODE_OHOS_BUILD_ROOT', '/data/storage/el2/base/haps/entry/files/node-24.21.0-build')))
parser.add_argument('--output', type=Path)
parser.add_argument('--revision', default='ohos.1')
args = parser.parse_args()
if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', args.revision):
    raise SystemExit('Invalid adaptation revision')
checkout = Path(__file__).resolve().parents[2]
source = args.build_root / 'source'
output = (args.output or checkout / 'out').resolve()
if sys.platform not in ('ohos', 'openharmony'):
    raise SystemExit('Package the signed native build on the HarmonyOS host')
version = '24.21.0'
name = f'node-v{version}-{args.revision}-arm64'
archive = output / f'{name}.tar.gz'
output.mkdir(parents=True, exist_ok=True)
if archive.exists():
    raise SystemExit(f'Refusing to overwrite {archive}; use another output directory')
node = source / 'out/Release/node'
if not node.is_file():
    raise SystemExit(f'Build Node first: missing {node}')
subprocess.run([str(node), '-e',
    f'if(process.version!=="v{version}"||process.platform!=="openharmony"||process.arch!=="arm64")process.exit(1)'],
    check=True)

with tempfile.TemporaryDirectory(prefix='package-', dir=args.build_root) as temporary:
    stage = Path(temporary) / name
    subprocess.run([sys.executable, str(source / 'tools/install.py'), 'install',
        '--dest-dir', str(stage), '--prefix', '', '--root-dir', str(source),
        '--build-dir', 'out/Release', '--config-gypi-path', str(source / 'config.gypi'),
        '--silent'], cwd=source, check=True)
    helpers = stage / 'libexec/nodejs'
    helpers.mkdir(parents=True)
    shutil.copyfile(checkout / 'tools/ohos/cc-sign.sh', helpers / 'cc-sign.sh')
    shutil.copyfile(checkout / 'tools/ohos/cxx-sign.sh', helpers / 'cxx-sign.sh')
    # Use command names in compiler settings; Make can then handle a prefix
    # containing spaces without splitting the compiler's filesystem path.
    (helpers / 'node-ohos-cc').symlink_to('cc-sign.sh')
    (helpers / 'node-ohos-cxx').symlink_to('cxx-sign.sh')
    for command, entry in [('npm', 'npm/bin/npm-cli.js'),
                           ('npx', 'npm/bin/npx-cli.js'),
                           ('corepack', 'corepack/dist/corepack.js')]:
        launcher = stage / 'bin' / command
        if not launcher.exists():
            continue
        launcher.unlink()
        launcher.write_text(f'''#!/bin/sh
set -eu
node_self=$(readlink -f -- "$0")
node_bin=$(CDPATH= cd -- "$(dirname -- "$node_self")" && pwd -P)
node_prefix=$(CDPATH= cd -- "$node_bin/.." && pwd -P)
export PATH="$node_prefix/libexec/nodejs:$node_bin:$PATH"
export CC=${{CC:-node-ohos-cc}}
export CXX=${{CXX:-node-ohos-cxx}}
exec "$node_bin/node" "$node_prefix/lib/node_modules/{entry}" "$@"
''')
    doc = stage / 'share/doc/nodejs'
    doc.mkdir(parents=True)
    shutil.copyfile(checkout / 'tools/ohos/README.md', doc / 'README.ohos.md')
    for filename in ('VALIDATION.md', 'smoke.mjs'):
        file = checkout / 'tools/ohos' / filename
        if file.exists():
            shutil.copyfile(file, doc / filename)
    license_dir = stage / 'share/licenses/nodejs'
    license_dir.mkdir(parents=True)
    shutil.copyfile(checkout / 'LICENSE', license_dir / 'LICENSE')
    for cache in stage.rglob('__pycache__'):
        shutil.rmtree(cache)
    for bytecode in stage.rglob('*.pyc'):
        bytecode.unlink()
    for file in stage.rglob('*'):
        if file.is_symlink():
            resolved = file.resolve(strict=True)
            if resolved != stage and stage not in resolved.parents:
                raise SystemExit(f'Archive link escapes package: {file}')
            continue
        if file.is_dir():
            file.chmod(0o755)
            continue
        with file.open('rb') as stream:
            magic = stream.read(4)
        file.chmod(0o755 if magic == b'\x7fELF' or magic.startswith(b'#!') else 0o644)

    def normalize(member):
        member.uid = member.gid = 0
        member.uname = member.gname = 'root'
        member.pax_headers = {}
        if member.isdir():
            member.mode = 0o755
        elif member.isfile():
            member.mode = 0o755 if member.mode & 0o111 else 0o644
        return member

    with tarfile.open(archive, 'w:gz', compresslevel=6) as tar:
        tar.add(stage, arcname=name, filter=normalize)
print(archive)
