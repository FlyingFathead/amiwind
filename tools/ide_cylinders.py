#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""IDE cylinder check of built drive files (IMAGE-IDE-CYLINDER-TAIL-59).

An IDE port reads a drive's size as whole cylinders of 16 heads x 63 sectors, so a drive file that is not
whole cylinders hides its last blocks (a read there raises Kickstart's "has a read error" requester). This is the
same check the builder runs on the drives it writes (world_volumes.require_ide_cylinders), usable on any finished
image: the master builder (aw) runs it on every built image, the release guard repeats it on the kit.

  ide_cylinders.py check PATH [PATH ...] [--json]
      PATH is a drive file or a folder (searched for *.hdf, no symbolic links followed); exit 1 when a drive
      is not whole cylinders; a folder with no drive passes and says so. --json prints one line for tools.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from world_volumes import IDE_CYLINDER_SECTORS, require_ide_cylinders  # noqa: E402


def find_drives(paths):
    drives = []
    for path in map(Path, paths):
        if path.is_dir():
            drives += sorted(p for p in path.rglob('*.hdf') if p.is_file() and not p.is_symlink())
        elif path.is_file():
            drives.append(path)
    return drives


def check_drives(paths):
    """{verdict, drives, failing, detail}: every drive file under PATHS judged by require_ide_cylinders."""
    rows, failing = [], []
    for drive in find_drives(paths):
        size = drive.stat().st_size
        try:
            require_ide_cylinders(drive.name, size, [])
            rows.append(dict(file=drive.name, bytes=size, cylinders=size // (IDE_CYLINDER_SECTORS * 512), ok=True))
        except ValueError as exc:
            rows.append(dict(file=drive.name, bytes=size, ok=False, detail=str(exc)))
            failing.append(str(exc))
    verdict = 'failed' if failing else ('passed' if rows else 'no-drives')
    detail = ('%d drive(s) whole IDE cylinders' % len(rows) if verdict == 'passed' else
              'no drive file found' if verdict == 'no-drives' else ' | '.join(failing)[:500])
    return dict(verdict=verdict, drives=rows, failing=failing, detail=detail)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)
    check = sub.add_parser('check')
    check.add_argument('paths', nargs='+')
    check.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    result = check_drives(args.paths)
    if args.json:
        print(json.dumps(result))
    else:
        print('IDE cylinders: %s: %s' % (result['verdict'], result['detail']))
    return 1 if result['verdict'] == 'failed' else 0


if __name__ == '__main__':
    sys.exit(main())
