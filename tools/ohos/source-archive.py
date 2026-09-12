#!/usr/bin/env python3
"""Export the complete pinned source tree from a committed adaptation revision."""
import argparse
import gzip
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--commit', default='HEAD')
parser.add_argument('--revision', default='ohos.1')
parser.add_argument('--output', type=Path)
args = parser.parse_args()
if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', args.revision):
    raise SystemExit('Invalid adaptation revision')
checkout = Path(__file__).resolve().parents[2]
output = (args.output or checkout / 'out').resolve()
commit = subprocess.check_output(['git', 'rev-parse', '--verify',
    args.commit + '^{commit}'], cwd=checkout, text=True).strip()
timestamp = int(subprocess.check_output(['git', 'show', '-s', '--format=%ct',
    commit], cwd=checkout, text=True).strip())
name = f'node-v24.21.0-{args.revision}-source'
output.mkdir(parents=True, exist_ok=True)
archive = output / f'{name}.tar.gz'
if archive.exists():
    raise SystemExit(f'Refusing to overwrite {archive}')
# git archive records the full commit in its global PAX header. Export the
# committed tree, including all vendored dependencies, without local outputs.
with tempfile.TemporaryFile(dir=output) as temporary:
    process = subprocess.Popen(['git', 'archive', '--format=tar',
        '--prefix=' + name + '/', commit], cwd=checkout, stdout=subprocess.PIPE)
    try:
        with gzip.GzipFile(fileobj=temporary, mode='wb', filename='',
                           mtime=timestamp, compresslevel=6) as compressed:
            shutil.copyfileobj(process.stdout, compressed, length=1024 * 1024)
        if process.wait() != 0:
            raise SystemExit('git archive failed')
        temporary.seek(0)
        with archive.open('xb') as destination:
            shutil.copyfileobj(temporary, destination, length=1024 * 1024)
    finally:
        process.stdout.close()
        if process.poll() is None:
            process.terminate()
            process.wait()
print(f'{archive}\nSource commit: {commit}')
