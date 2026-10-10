# SPDX-License-Identifier: GPL-3.0-only
"""Stable interior cell numbers for the debug HUD ("INT 412") and `dbg cell`.

Every interior cell of the owner's masters gets one plain number, the same in
every build: the base master's interior cells sorted by cell ID (case folded)
take 1..N, then each expansion master in fixed order appends the cells it adds,
sorted the same way. A missing expansion therefore never renumbers the cells
before it. The builder stamps the number and the full cell ID into each staged
interior map's worldspawn (_aw_cell_int, _aw_cell_id) and writes the whole
table into the build folder (cell-numbers.json), so a number seen in the HUD
can always be resolved. Exterior cells need no table: the engine derives the
grid from the coordinates the HUD already shows (8192 original units per cell).
"""
import hashlib
import json
import math
from pathlib import Path
import struct

MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')
NUMBER_KEY = '_aw_cell_int'
ID_KEY = '_aw_cell_id'
# Original cell IDs are at most 63 bytes; the engine keeps 64.
ID_LIMIT = 63


def interior_cell_ids(raw):
    """Interior cell IDs of one master, in file order (deleted cells skipped)."""
    out, pos = [], 0
    while pos < len(raw):
        if pos + 16 > len(raw):
            raise ValueError('Truncated record header at %d' % pos)
        tag, size, _, flags = struct.unpack_from('<4sIII', raw, pos)
        start, end = pos + 16, pos + 16 + size
        if end > len(raw):
            raise ValueError('Record overruns master at %d' % pos)
        pos = end
        if tag != b'CELL' or flags & 0x20:
            continue
        name, data, deleted, at = None, None, False, start
        while at + 8 <= end:
            sub, length = struct.unpack_from('<4sI', raw, at)
            body = raw[at + 8:at + 8 + length]
            at += 8 + length
            if sub == b'FRMR':
                break
            if sub == b'NAME':
                name = body.rstrip(b'\0').decode('cp1252')
            elif sub == b'DATA' and len(body) == 12:
                data = struct.unpack('<Iii', body)
            elif sub == b'DELE':
                deleted = True
        if name and data and data[0] & 1 and not deleted:
            out.append(name)
    return out


def number_cells(masters):
    """masters: [(master file name, [cell IDs])] in MASTERS order -> table rows."""
    rows, seen = [], set()
    for master, names in masters:
        new = sorted({n for n in names if n.casefold() not in seen}, key=lambda n: (n.casefold(), n))
        for name in new:
            if name.casefold() in seen:
                raise ValueError('Interior cell IDs differ only by case: ' + name)
            seen.add(name.casefold())
            rows.append({'number': len(rows) + 1, 'cell': name, 'master': master})
    return rows


def load_table(data_files):
    """Number the interiors of the masters present in DATA_FILES (base master required)."""
    from mwad.paths import child_ci
    data_files = Path(data_files)
    masters, hashes = [], {}
    for n, name in enumerate(MASTERS):
        path = child_ci(data_files, name, required=n == 0)
        if path is None:
            continue
        raw = path.read_bytes()
        hashes[name] = hashlib.sha256(raw).hexdigest()
        masters.append((name, interior_cell_ids(raw)))
    return number_cells(masters), hashes


def cell_fields(row):
    """Worldspawn fields for one numbered interior."""
    cell = row['cell']
    if not cell.isascii() or '"' in cell or any(ord(c) < 32 for c in cell) or len(cell) > ID_LIMIT:
        raise ValueError('Interior cell ID cannot be carried in a worldspawn key: ' + repr(cell))
    return {NUMBER_KEY: str(row['number']), ID_KEY: cell}


def interior_map_cells(map_names):
    """Map name -> original cell ID for the staged interior maps (scene catalogue + town lists)."""
    from area_config import SCENES
    from town_config import town_interiors
    cells = {s['map']: s['cell'] for s in SCENES if s.get('interior') is True}
    cells.update({room['map']: room['cell'] for room in town_interiors()})
    return {name: cells[name] for name in sorted(map_names) if name in cells}


def _plan(task):
    path, fields = task
    from hand_metadata import stamp
    raw = Path(path).read_bytes()
    return hashlib.sha256(raw).hexdigest(), stamp(raw, fields) != raw


def _write(task):
    path, fields, original = task
    from hand_metadata import stamp
    path = Path(path)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != original:
        raise ValueError('Map changed during cell number staging: ' + path.name)
    stamped = stamp(raw, fields)
    path.write_bytes(stamped)
    if path.read_bytes() != stamped:
        raise ValueError('Cell number write verification failed: ' + path.name)
    return path.name


def stamp_staged_cells(id1, data_files, map_names, out_path, jobs=1):
    """Stamp every staged interior map with its cell number + ID; write the lookup table."""
    from build_parallel import ordered_map
    id1 = Path(id1)
    rows, hashes = load_table(data_files)
    by_id = {row['cell'].casefold(): row for row in rows}
    assigned, tasks, unknown = [], [], []
    for name, cell in interior_map_cells(map_names).items():
        row = by_id.get(cell.casefold())
        if row is None:
            unknown.append({'map': name, 'cell': cell})
            continue
        fields = cell_fields(row)
        assigned.append({'map': name, 'number': row['number'], 'cell': row['cell']})
        tasks.append((str(id1 / 'maps' / (name + '.bsp')), fields))
    if unknown:
        raise ValueError('Interior maps name cells the masters do not have: ' +
                         ', '.join(u['map'] + ' (' + u['cell'] + ')' for u in unknown[:8]))
    workers = max(1, min(jobs, len(tasks) or 1))
    planned = list(ordered_map(_plan, tasks, workers)) if tasks else []
    changed = list(ordered_map(_write, [(path, fields, h) for (path, fields), (h, needs) in zip(tasks, planned)
                                        if needs], workers)) if tasks else []
    report = {'status': 'passed', 'format': 1,
              'rule': 'base master interiors sorted by cell ID take 1..N; each expansion appends its new cells, sorted',
              'masters_sha256': hashes, 'interior_cells': len(rows),
              'worldspawn_keys': [NUMBER_KEY, ID_KEY], 'maps': assigned, 'changed_maps': changed,
              'table': rows}
    Path(out_path).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('[cell-numbers] %d interior cells numbered; %d staged interior maps stamped' % (len(rows), len(assigned)),
          flush=True)
    return {k: v for k, v in report.items() if k != 'table'}


def exterior_cell(x, y):
    """Original grid cell of a global position (same rule as the engine: floor, 8192 units)."""
    return math.floor(x / 8192.0), math.floor(y / 8192.0)


if __name__ == '__main__':
    import argparse
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
    parser = argparse.ArgumentParser(description='Print the interior cell number table of a Data Files folder.')
    parser.add_argument('data_files')
    parser.add_argument('--find', help='print only rows whose cell ID contains this text (case-insensitive)')
    args = parser.parse_args()
    table, _ = load_table(args.data_files)
    for row in table:
        if not args.find or args.find.casefold() in row['cell'].casefold():
            print('INT %d\t%s\t%s' % (row['number'], row['cell'], row['master']))
