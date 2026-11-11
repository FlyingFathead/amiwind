#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""List converted interior rooms by horizontal size, for config/large-rooms.txt (FOG-300-DEFAULT-57).

    python3 tools/large_rooms.py AREA_WORK [--min 1024] [--write config/large-rooms.txt]

AREA_WORK is a build's chim-room-batches/scene/area-work folder: each room's conversion.json holds its
bounds in local units. Prints the rooms whose larger horizontal side is at least --min, largest first;
--write writes them as the large-rooms table (every large room of the world, INTERIOR-FAR-BLANK-MANOR-56).
The room build checks every room it converts against the table (missing_large_rooms).
"""
import argparse
import json
import re
from pathlib import Path

LARGE_ROOM_SIDE = 1024.0      # local units: a room with a longer horizontal side is a large room
TABLE = Path(__file__).resolve().parents[1] / 'config/large-rooms.txt'
HEADER = """# Large rooms (FOG-300-DEFAULT-57, INTERIOR-FAR-BLANK-MANOR-56): interiors that
# fade into their cell's fog colour (dark grey when the record has none) at the
# player's draw distance and draw nothing past it (aw_fog 1, the default; 0 or 2
# turns it off). One room per line: map name [cap in local units, 100..4096].
# Every room with a side of at least %d local units, from the converted size:
# tools/large_rooms.py AREA_WORK --write (the room build stops on a large room
# that is missing here). %d rooms.
"""


def room_size(work):
    """(longest side, x size, y size, map, cell, placements) of one converted room folder, or None without bounds."""
    path = Path(work) / 'conversion.json'
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding='utf-8'))
    bounds = data.get('bounds')
    if not bounds:
        return None
    dx, dy = bounds[1][0] - bounds[0][0], bounds[1][1] - bounds[0][1]
    return (max(dx, dy), dx, dy, data['map'], data['cell'], data.get('placements'))


def listed(table=TABLE):
    """The map names of the large-rooms table."""
    out = set()
    for line in Path(table).read_text(encoding='ascii').split('\n'):
        match = re.match(r'([a-z0-9_]{1,15})(?: [0-9]+)?$', line)
        if match and not line.startswith('#'):
            out.add(match[1])
    return out


def missing_large_rooms(works, table=TABLE, side=LARGE_ROOM_SIDE):
    """[(map, cell, longest side)] of the converted rooms (folders with conversion.json) at least side across that
    the large-rooms table does not list: such a room would draw without fog or a draw cut."""
    names = listed(table)
    out = []
    for work in works:
        row = room_size(work)
        if row and row[0] >= side and row[3] not in names:
            out.append((row[3], row[4], row[0]))
    return out


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
    parser.add_argument('--min', type=float, default=LARGE_ROOM_SIDE,
                        help='smallest longest side, local units (default %d)' % LARGE_ROOM_SIDE)
    parser.add_argument('--write', type=Path, help='write the rooms as the large-rooms table')
    args = parser.parse_args(argv)
    found = [row for row in rooms(args.area_work) if row[0] >= args.min]
    if args.write:
        body = ''.join('%s\n' % row[3] for row in sorted(found, key=lambda r: r[3]))
        args.write.write_bytes((HEADER % (args.min, len(found)) + body).encode('ascii'))
        print('%s: %d large rooms' % (args.write, len(found)))
        return 0
    print('# %d rooms with a side of at least %d local units' % (len(found), args.min))
    for _, dx, dy, name, cell, placements in found:
        print('# %s: %d x %d local units, %s placements\n%s' % (cell, dx, dy, placements, name))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
