"""Write/check SHA-256 of exact Git index blobs, independent of checkout CRLF.

Stage intended files; run write; stage SOURCE-MANIFEST.sha256; run check.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

MANIFEST = 'SOURCE-MANIFEST.sha256'


def git(root, *args, data=None):
    result = subprocess.run(['git', '-C', str(root), *args], input=data,
                            capture_output=True, check=False)
    if result.returncode:
        raise ValueError(result.stderr.decode('utf-8', errors='replace').strip())
    return result.stdout


def index_files(root):
    files = {}
    for record in git(root, 'ls-files', '--stage', '-z').split(b'\0'):
        if not record:
            continue
        meta, raw_path = record.split(b'\t', 1)
        mode, oid, stage = meta.split()
        path = raw_path.decode('utf-8')
        if stage != b'0':
            raise ValueError(f'Unresolved Git conflict: {path}')
        if mode == b'160000':
            raise ValueError(f'Submodule needs a separate source manifest: {path}')
        if any(char in path for char in ('\n', '\r', '\\')):
            raise ValueError(f'Path cannot be represented in this manifest: {path!r}')
        files[path] = oid.decode('ascii')
    return files


def render(root, files):
    paths = sorted(path for path in files if path != MANIFEST)
    data = git(root, 'cat-file', '--batch', data=''.join(
        files[path] + '\n' for path in paths).encode('ascii'))
    lines = []
    offset = 0
    for path in paths:
        end = data.index(b'\n', offset)
        oid, kind, size = data[offset:end].split()
        if kind != b'blob' or oid.decode('ascii') != files[path]:
            raise ValueError(f'Not a Git file blob: {path}')
        start = end + 1
        end = start + int(size)
        digest = hashlib.sha256(data[start:end]).hexdigest()
        if data[end:end + 1] != b'\n':
            raise ValueError(f'Invalid Git blob framing: {path}')
        lines.append(f'{digest}  {path}\n')
        offset = end + 1
    return ''.join(lines).encode('utf-8')


def run(command, root):
    files = index_files(root)
    expected = render(root, files)
    if command == 'write':
        (root / MANIFEST).write_bytes(expected)
        print(f'Wrote {MANIFEST}: {len(files) - (MANIFEST in files)} Git files. '
              'Stage the manifest before check.')
        return 0
    if MANIFEST not in files:
        raise ValueError(f'{MANIFEST} is not staged/tracked. Run write and git add it.')
    actual = git(root, 'cat-file', 'blob', files[MANIFEST])
    if actual != expected:
        old = set(actual.decode('utf-8', errors='replace').splitlines())
        new = set(expected.decode('utf-8').splitlines())
        changed = sorted({line.split('  ', 1)[-1] for line in old ^ new})
        raise ValueError('Manifest differs from Git index (including order/format). '
                         'Run write and stage it. ' + ', '.join(changed))
    drift = git(root, 'diff', '--name-only', '-z').split(b'\0')
    if any(drift):
        raise ValueError('Unstaged tracked changes: ' + ', '.join(
            p.decode('utf-8', errors='replace') for p in drift if p))
    print(f'Source manifest OK: {len(files) - 1} exact Git blobs; no unstaged drift.')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('write', 'check'))
    args = parser.parse_args()
    try:
        root = Path(git(Path.cwd(), 'rev-parse', '--show-toplevel').decode('utf-8').strip())
        return run(args.command, root)
    except (ValueError, OSError, UnicodeError) as error:
        print(f'Source manifest FAILED: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
