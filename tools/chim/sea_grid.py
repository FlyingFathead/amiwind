# SPDX-License-Identifier: GPL-3.0-only
"""The open sea of the map's box: the exterior cells no master has a record for, as the original game makes them.

Solstheim's cells lie in the same exterior grid as Vvardenfell's, and the original game has open sea everywhere
between and around the islands: a cell no master has a CELL record for is made on first use as an empty exterior
with water (OpenMW apps/openmw/mwworld/worldmodel.cpp 55-62 createEsmCell, HasWater; 106-121 getOrCreateExterior),
the water at the sea level (apps/openmw/mwworld/cell.cpp 98-102) over the flat default height (components/esm3/
loadland.hpp 77 DEFAULT_HEIGHT -2048; components/esmterrain/storage.cpp 571-577). The world map spans the box of
every exterior CELL record of the loaded masters (apps/openmw/mwrender/globalmap.cpp 291-308): that box is where the
map ends (SOL-SEA-CROSSING-68, CHIM-SEA-BETWEEN-ISLANDS-64).

So the builder builds every cell of that box. Cells with a record are built as before (land, seabed, the listed
open-sea cells with a record); the RECORDLESS cells are the shared ocean chunk (tools/chim/ocean.py), listed in two
cell files marked "recordless" (tools/chim/regions.py, the rule above select):

- config/chim-sea-grid.json: the recordless cells inside the box of the base game's own records (Morrowind.esm and
  Tribunal.esm): the base world, so a build without Bloodmoon has its own whole map;
- config/solstheim-sea-grid.json: the recordless cells of the area Bloodmoon's records add to the box: the build
  module bloodmoon-solstheim (tools/bloodmoon_solstheim_module.py).

Every cell of the box is then a frame of one of the two worlds; the walls of the world (the edge current,
tools/world_bounds.py) stand only at the box's outer edge. The lists are written from the game data by this tool and
checked by the build's preflight in seconds (tools/chim/regions.py recordless_problems).

Commands (in the shell container, the game data read only):
  sea_grid.py report --data-files DIR       the boxes and the counts
  sea_grid.py write --data-files DIR        write the two lists (config/, this source tree)
  sea_grid.py check --data-files DIR        the lists match the game data (exit 1 when not)
"""
import argparse
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')
BASE_MASTERS = ('Morrowind.esm', 'Tribunal.esm')
CELLS_FORMAT = 'aw-chim-cells-1'
BASE_CELLS = 'config/chim-cells.json'
BASE_GRID = 'config/chim-sea-grid.json'
MODULE_SEA = 'config/solstheim-sea-cells.json'
MODULE_GRID = 'config/solstheim-sea-grid.json'
FLAG_DELETED = 0x20               # record header flag
CELL_INTERIOR = 1                 # CELL DATA flag
_SCANS = {}


def _subrecords(payload):
    at = 0
    while at + 8 <= len(payload):
        tag, size = struct.unpack_from('<4sI', payload, at)
        yield tag, payload[at + 8:at + 8 + size]
        at += 8 + size


def scan_master(path):
    """({exterior CELL cells}, {LAND cells}) of one master file, live records only; read once per process and file
    (path, size, modification time)."""
    path = Path(path)
    stat = path.stat()
    key = (str(path.resolve()), stat.st_size, stat.st_mtime_ns)
    if key in _SCANS:
        return _SCANS[key]
    cells, land = set(), set()
    with path.open('rb') as stream:
        while True:
            header = stream.read(16)
            if not header:
                break
            if len(header) != 16:
                raise ValueError('%s: truncated record header' % path.name)
            tag, size, _, flags = struct.unpack('<4sIII', header)
            if tag not in (b'CELL', b'LAND'):
                stream.seek(size, 1)
                continue
            payload = stream.read(size)
            if len(payload) != size or flags & FLAG_DELETED:
                if len(payload) != size:
                    raise ValueError('%s: truncated record' % path.name)
                continue
            fields = {}
            for sub, data in _subrecords(payload):
                if tag == b'CELL' and sub == b'FRMR':
                    break
                fields.setdefault(sub, data)
            if b'DELE' in fields:
                continue
            if tag == b'CELL':
                data = fields.get(b'DATA', b'')
                if len(data) >= 12:
                    bits, x, y = struct.unpack_from('<Iii', data)
                    if not bits & CELL_INTERIOR:
                        cells.add((x, y))
            elif len(fields.get(b'INTV', b'')) == 8:
                land.add(struct.unpack('<ii', fields[b'INTV']))
    _SCANS[key] = (cells, land)
    return cells, land


def _master_paths(data_files, masters):
    from mwad.paths import child_ci
    out = []
    for name in masters:
        try:
            path = child_ci(Path(data_files), name)
        except (FileNotFoundError, ValueError):
            path = None
        if path is None or not Path(path).is_file():
            if name == MASTERS[0]:
                raise ValueError('%s: no %s' % (data_files, name))
            continue
        out.append((name, Path(path)))
    return out


def exterior_cells(data_files, masters=MASTERS):
    """{(x, y)} with an exterior CELL record in any of MASTERS present in DATA_FILES."""
    out = set()
    for _, path in _master_paths(data_files, masters):
        out |= scan_master(path)[0]
    return out


def recorded_cells(data_files, masters=MASTERS):
    """{(x, y)} with an exterior CELL or a LAND record in any of MASTERS present in DATA_FILES."""
    out = set()
    for _, path in _master_paths(data_files, masters):
        cells, land = scan_master(path)
        out |= cells | land
    return out


def box(cells):
    """(x0, y0, x1, y1), inclusive, of CELLS."""
    if not cells:
        raise ValueError('no cells')
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    return min(xs), min(ys), max(xs), max(ys)


def box_cells(b):
    x0, y0, x1, y1 = b
    return {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}


def inside(cell, b):
    return b[0] <= cell[0] <= b[2] and b[1] <= cell[1] <= b[3]


def read_cells(path):
    """The cells of an aw-chim-cells-1 file, [] when there is none."""
    path = Path(path)
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    out = []
    for c in data.get('cells') or []:
        x, y = (c.split(',') if isinstance(c, str) else c)
        out.append((int(x), int(y)))
    return out


def plan(records_all, records_base, recorded, listed_base=(), listed_module=()):
    """{'box': joint box, 'base_box': the base game's box, 'base': [...], 'module': [...]}: the recordless cells of
    the joint box (no CELL or LAND record in any master: RECORDED), not already listed by a cell file
    (LISTED_BASE, LISTED_MODULE), split by the base game's box. RECORDS_ALL / RECORDS_BASE: the exterior CELL
    records of every master / of the base game's masters (the boxes, OpenMW globalmap.cpp 291-308)."""
    joint = box(records_all)
    base_box = box(records_base)
    listed = {tuple(c) for c in listed_base} | {tuple(c) for c in listed_module}
    free = sorted(c for c in box_cells(joint) if c not in recorded and c not in listed)
    return {'box': list(joint), 'base_box': list(base_box),
            'base': [c for c in free if inside(c, base_box)],
            'module': [c for c in free if not inside(c, base_box)]}


def plan_from_data(data_files, root=ROOT):
    root = Path(root)
    return plan(exterior_cells(data_files), exterior_cells(data_files, BASE_MASTERS), recorded_cells(data_files),
                read_cells(root / BASE_CELLS), read_cells(root / MODULE_SEA))


def cell_file(cells, where, b, base_box):
    """The aw-chim-cells-1 document of one list (WHERE: 'base' or 'module')."""
    reason = ('The open sea of the map\'s box that no master has a CELL or LAND record for, %s. The original game '
              'makes each such cell on first use as an empty exterior with water over the flat default height '
              '(OpenMW worldmodel.cpp createEsmCell, loadland.hpp DEFAULT_HEIGHT), so each is the shared ocean chunk '
              '(tools/chim/ocean.py); taken as open sea without a tracker status, after every other cell of its '
              'world (tools/chim/regions.py, the recordless rule). Written by tools/chim/sea_grid.py write from the '
              'game data; the build\'s preflight checks it against the masters (SOL-SEA-CROSSING-68).'
              % ('inside the box of the base game\'s own records (Morrowind.esm, Tribunal.esm): the base world'
                 if where == 'base' else
                 'in the area Bloodmoon\'s records add to the box: the build module bloodmoon-solstheim'))
    notes = ('The map\'s box (every exterior CELL record of Morrowind.esm, Tribunal.esm and Bloodmoon.esm, OpenMW '
             'globalmap.cpp): cells x %d..%d, y %d..%d; the base game\'s box: x %d..%d, y %d..%d. %d cells.'
             % (b[0], b[2], b[1], b[3], base_box[0], base_box[2], base_box[1], base_box[3], len(cells)))
    return {'format': CELLS_FORMAT, 'recordless': True, 'cells': ['%d,%d' % c for c in cells], 'reason': reason,
            'notes': notes}


def write_lists(data_files, root=ROOT):
    root = Path(root)
    p = plan_from_data(data_files, root)
    for rel, where in ((BASE_GRID, 'base'), (MODULE_GRID, 'module')):
        doc = cell_file(p[where], where, p['box'], p['base_box'])
        (root / rel).write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8', newline='\n')
    return p


def check_lists(data_files, root=ROOT):
    """[problem]: the two lists against the game data."""
    root = Path(root)
    p = plan_from_data(data_files, root)
    problems = []
    for rel, where in ((BASE_GRID, 'base'), (MODULE_GRID, 'module')):
        have = sorted(read_cells(root / rel))
        if have != p[where]:
            problems.append('%s: %d cells, the game data gives %d (%d missing, %d extra)'
                            % (rel, len(have), len(p[where]), len(set(p[where]) - set(have)),
                               len(set(have) - set(p[where]))))
    return problems


def main(argv=None):
    sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=('report', 'write', 'check'))
    ap.add_argument('--data-files', required=True, type=Path)
    ap.add_argument('--root', type=Path, default=ROOT)
    a = ap.parse_args(argv)
    if a.command == 'check':
        problems = check_lists(a.data_files, a.root)
        for line in problems:
            print('sea grid: ' + line)
        print('sea grid: %s' % ('the lists match the game data' if not problems else 'MISMATCH'))
        return 1 if problems else 0
    p = write_lists(a.data_files, a.root) if a.command == 'write' else plan_from_data(a.data_files, a.root)
    print('sea grid: the map\'s box x %d..%d, y %d..%d; the base game\'s box x %d..%d, y %d..%d; recordless cells: '
          '%d in the base world, %d in the module%s' % (p['box'][0], p['box'][2], p['box'][1], p['box'][3],
                                                       p['base_box'][0], p['base_box'][2], p['base_box'][1],
                                                       p['base_box'][3], len(p['base']), len(p['module']),
                                                       ' (written)' if a.command == 'write' else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
