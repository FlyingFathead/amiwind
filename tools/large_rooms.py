#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""List converted interior rooms by horizontal size, for config/large-rooms.txt (FOG-300-DEFAULT-57).

    python3 tools/large_rooms.py AREA_WORK [--min 1024]

AREA_WORK is a build's chim-room-batches/scene/area-work folder: each room's conversion.json holds its
bounds in local units. Prints the rooms whose larger horizontal side is at least --min, largest first.
"""
import argparse
import json
from pathlib import Path


def rooms(area_work):
    """(longest side, x size, y size, map, cell, placements) of every converted room with bounds."""
    rows = []
    for path in sorted(Path(area_work).glob('*/conversion.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        bounds = data.get('bounds')
        if not bounds:
            continue
        dx, dy = bounds[1][0] - bounds[0][0], bounds[1][1] - bounds[0][1]
        rows.append((max(dx, dy), dx, dy, data['map'], data['cell'], data.get('placements')))
    return sorted(rows, reverse=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('area_work', type=Path)
    parser.add_argument('--min', type=float, default=1024.0, help='smallest longest side, local units (default 1024)')
    args = parser.parse_args(argv)
    found = [row for row in rooms(args.area_work) if row[0] >= args.min]
    print('# %d rooms with a side of at least %d local units' % (len(found), args.min))
    for _, dx, dy, name, cell, placements in found:
        print('# %s: %d x %d local units, %s placements\n%s' % (cell, dx, dy, placements, name))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
