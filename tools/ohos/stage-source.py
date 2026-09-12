#!/usr/bin/env python3
"""Synchronize build inputs into native private storage without build outputs."""
import filecmp
import json
import os
from pathlib import Path
import shutil
import sys
import time

source, destination = (Path(p).resolve() for p in sys.argv[1:])
if source == destination or source in destination.parents:
    raise SystemExit('The private build source must be outside the shared checkout')
started = time.monotonic()
destination.mkdir(parents=True, exist_ok=True)
manifest = destination.parent / 'source-files.json'
previous = set(json.loads(manifest.read_text())) if manifest.exists() else set()
current = set()
changed = 0
root_excludes = {'.git', 'out', 'node', 'config.gypi', 'config.mk', 'config.status',
                 'compile_commands.json'}
for directory, dirs, files in os.walk(source, followlinks=False):
    relative = Path(directory).relative_to(source)
    dirs[:] = [d for d in dirs if d != '__pycache__' and
               (relative != Path('.') or d not in root_excludes)]
    target_dir = destination / relative
    target_dir.mkdir(parents=True, exist_ok=True)
    for name in files + [d for d in dirs if (Path(directory) / d).is_symlink()]:
        rel = relative / name
        if name.endswith('.pyc') or (relative == Path('.') and name in root_excludes):
            continue
        if rel.as_posix() == 'deps/icu_config.gypi':
            continue
        src, dst = source / rel, destination / rel
        current.add(rel.as_posix())
        if src.is_symlink():
            link = os.readlink(src)
            if dst.is_symlink() and os.readlink(dst) == link:
                continue
            if dst.exists() or dst.is_symlink():
                dst.unlink()
            dst.symlink_to(link)
            changed += 1
        elif not dst.is_file() or dst.is_symlink() or not filecmp.cmp(src, dst, shallow=False):
            if dst.is_symlink():
                dst.unlink()
            shutil.copyfile(src, dst)
            changed += 1
        if not src.is_symlink():
            # Shared-mount mode bits do not preserve Linux checkout permissions.
            # Preserve shebang entry points, including npm's node-gyp-bin helper.
            with src.open('rb') as stream:
                shebang = stream.read(2) == b'#!'
            mode = 0o755 if shebang or src.suffix in {'.sh', '.py', '.pl'} else 0o644
            if dst.stat().st_mode & 0o777 != mode:
                dst.chmod(mode)
for removed in previous - current:
    target = destination / removed
    if target.is_file() or target.is_symlink():
        target.unlink()
manifest.write_text(json.dumps(sorted(current), indent=2) + '\n')
print(f'Staged {len(current)} source files ({changed} changed) in '
      f'{time.monotonic() - started:.1f}s: {destination}', flush=True)
