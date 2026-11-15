#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The world-wide container table (CONTAINER-WINDOW-59, CONTAINER-LOOT-TABLES-66, INTERIOR-PLACED-ITEMS-47).

From the base master (read-only): every container record (CONT) and every placed container, interior and exterior,
with what the original gives it: organic (flora, harvested) or opened, a name, contents (items and levelled lists),
a lock, a trap, a key, an owner. With a build run (optional): which of them the build makes openable and, for the
rest, why, by the same rules the engine uses:

  - a placed container needs a 'C' row in id1/focus.awf (tools/prepare_focus.py: a named, non-organic CONT, a
    numbered room or an exterior cell, the room under its row cap);
  - in a room it is aimed at by its drawn placement box (aw_inventory.c placed_target, chim_room.c ChimRoom_RayRef),
    so the room map must keep its placement (the batch room's placements.json);
  - outdoors (focus_outdoor) there is no box: the aim is the near-the-reference-point test (within 6 map units of the
    crosshair line), which a sack or a barrel standing on its origin seldom meets.

    python3 tools/container_census.py --data-files DIR [--run RUN] [--json]
"""
import argparse
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

from mwad.esm import records, subrecords, string, first          # noqa: E402
from mwad.paths import resolve_data_files                         # noqa: E402
from mwad.masters import master_path                              # noqa: E402
import prepare_focus as pf                                        # noqa: E402
from ref_identity import stable_ref                               # noqa: E402


def cont_records(raw, levelled):
    """{folded id: {'name', 'organic', 'items', 'lists'}} of every live CONT record."""
    out = {}
    for tag, flags, payload in records(raw):
        if tag != 'CONT' or flags & 0x20:
            continue
        fields = list(subrecords(payload))
        ident = string(first(fields, 'NAME'), 'NAME', errors='replace').casefold()
        name = string(first(fields, 'FNAM'), 'FNAM', errors='replace') if first(fields, 'FNAM') else ''
        flag = first(fields, 'FLAG') or b''
        organic = len(flag) >= 4 and bool(struct.unpack_from('<I', flag)[0] & pf.CONT_ORGANIC)
        items = lists = 0
        for key, value in fields:
            if key == 'NPCO' and len(value) >= 36:
                entry = string(value[4:36], 'NPCO', errors='replace').casefold()
                if entry in levelled:
                    lists += 1
                else:
                    items += 1
        out[ident] = {'name': name.strip(), 'organic': organic, 'items': items, 'lists': lists}
    return out


def census(data_files):
    from cell_numbers import load_table, room_numbers
    data = resolve_data_files(Path(data_files))
    raw = master_path(data).read_bytes()
    table, _ = load_table(data)
    # every selected master's rooms (the merged master holds them all; the base game alone looks up only its own)
    numbers = room_numbers(table)
    levelled = pf.item_lists(raw)
    conts = cont_records(raw, levelled)
    places = []
    for cell, interior, grid, _, refs in pf.cells_of(raw):
        for ref in refs:
            if 'DELE' in ref or 'NAME' not in ref:
                continue
            ident = string(ref['NAME'], 'NAME', errors='replace').casefold()
            rec = conts.get(ident)
            if rec is None:
                continue
            key = None
            if interior:
                key = numbers.get(cell.casefold()) if cell else None
            elif all(abs(g) < pf.GRID_BIAS for g in grid):
                key = pf.exterior_key(*grid)
            places.append({'reference': stable_ref(pf.MASTER, ref['number']), 'cell': cell or '%d,%d' % grid,
                           'interior': interior, 'key': key, 'id': ident, 'organic': rec['organic'],
                           'named': bool(rec['name']), 'items': rec['items'], 'lists': rec['lists'],
                           'locked': pf.lock_level(ref) > 0, 'trapped': bool(ref.get('TNAM')),
                           'keyed': bool(ref.get('KNAM')), 'owned': bool(ref.get('ANAM') or ref.get('CNAM')),
                           'data_ok': len(ref.get('DATA', b'')) == 24})
    return conts, places


def run_rows(run):
    """{reference: room key} of the 'C' rows of the run's focus.awf, and the room keys with batch-room placements."""
    from room_container_aim import FOCUS, focus_containers, map_numbers
    from chim.interior import installed_room
    from map_files import map_file
    focus = focus_containers((Path(run) / FOCUS).read_bytes())
    rows = {ref: key for key, refs in focus.items() for ref in refs}
    kept = {}
    for name, number in map_numbers(run).items():
        # every CHIM room map, batch-converted or a town's: the engine aims at a container by the room record's
        # placements whose reference (its low 24 bits, chim_room.c ROOM_SOURCE_MASK) is the row's
        room = installed_room(map_file(Path(run) / 'image/boot/id1/maps', name))
        if room is not None:
            kept.setdefault(number, set()).update(p['ref'] & ROOM_SOURCE_MASK for p in room['placements'])
    return rows, kept


ROOM_SOURCE_MASK = 0xFFFFFF


def tally(conts, places, run=None):
    def count(sel):
        return sum(1 for p in places if sel(p))
    t = {'records': len(conts), 'records_organic': sum(1 for c in conts.values() if c['organic']),
         'records_unnamed': sum(1 for c in conts.values() if not c['name']),
         'placed': len(places)}
    for side, inside in (('interior', True), ('exterior', False)):
        mine = [p for p in places if p['interior'] == inside]
        opened = [p for p in mine if not p['organic']]
        t[side] = {'placed': len(mine), 'organic': len(mine) - len(opened), 'to_open': len(opened),
                   'cells': len({p['cell'] for p in opened}),
                   'unnamed': sum(1 for p in opened if not p['named']),
                   'no_cell_number': sum(1 for p in opened if p['key'] is None),
                   'locked': sum(1 for p in opened if p['locked']), 'trapped': sum(1 for p in opened if p['trapped']),
                   'keyed': sum(1 for p in opened if p['keyed']), 'owned': sum(1 for p in opened if p['owned']),
                   'with_lists': sum(1 for p in opened if p['lists']),
                   'empty': sum(1 for p in opened if not p['items'] and not p['lists'])}
    if run:
        rows, kept = run_rows(run)
        why, cells = {}, {}
        openable = {'interior': 0, 'exterior': 0}
        for p in places:
            if p['organic']:
                continue
            side = 'interior' if p['interior'] else 'exterior'
            if p['reference'] not in rows:
                reason = ('unnamed record' if not p['named'] else 'no cell number' if p['key'] is None
                          else 'no focus row (room row cap or record left out)')
            elif p['interior'] and p['key'] not in kept:
                reason = 'room map is not a CHIM room: near-the-point aim only'
            elif p['interior'] and p['reference'] & ROOM_SOURCE_MASK not in kept[p['key']]:
                reason = 'room map leaves its placement out'
            elif not p['interior']:
                reason = 'outdoors: no placement box, near-the-point aim only'
            else:
                openable[side] += 1
                continue
            why.setdefault(side, {}).setdefault(reason, 0)
            why[side][reason] += 1
            cells.setdefault(reason, {}).setdefault(p['cell'], 0)
            cells[reason][p['cell']] += 1
        top = {r: dict(sorted(c.items(), key=lambda kv: -kv[1])[:40]) for r, c in cells.items()}
        t['run'] = {'path': str(run), 'openable': openable, 'not_openable': why,
                    'cells_per_reason': {r: len(c) for r, c in cells.items()}, 'top_cells': top}
    return t


def is_box(field):
    """True when a row's 32-byte id field holds a packed box (prepare_focus board_box: half extents, a unit
    quaternion), the engine's own test (aw_inventory.c focus_board_add)."""
    h = struct.unpack_from('<3f', field)
    q = struct.unpack_from('<4f', field, 12)
    return all(0 <= v < 100000 for v in h) and all(-1.01 <= v <= 1.01 for v in q) and \
        0.98 <= sum(v * v for v in q) <= 1.02


def window_boxes(payload):
    """OUTDOOR-CONTAINER-AIM-66: from a focus table (AWF3 bytes): the exterior container rows with a box, those
    without, and the most boxes (named boards and containers) in one 3 x 3 exterior window, which the engine's
    FOCUS_BOARDS must hold."""
    rooms = struct.unpack_from('<I', payload, 4)[0]
    per_cell, boxed, unboxed, room_most = {}, 0, 0, 0
    for i in range(rooms):
        key, first_row, count = struct.unpack_from('<III', payload, 8 + 12 * i)
        if not key & 0x80000000:
            # a room: its boards and boxed containers, all in the one table
            n = 0
            for j in range(count):
                row = payload[8 + rooms * 12 + (first_row + j) * pf.ROW:][:pf.ROW]
                n += row[0] == ord('N') or (row[0] == ord('C') and is_box(row[64:96]))
            room_most = max(room_most, n)
            continue
        gx, gy = (key >> 12 & 0xFFF) - pf.GRID_BIAS, (key & 0xFFF) - pf.GRID_BIAS
        n = 0
        for j in range(count):
            row = payload[8 + rooms * 12 + (first_row + j) * pf.ROW:][:pf.ROW]
            if row[0] == ord('N'):
                n += 1
            elif row[0] == ord('C') and row[2] & 3:
                if is_box(row[64:96]):
                    boxed += 1; n += 1
                else:
                    unboxed += 1
        per_cell[(gx, gy)] = n
    most = max((sum(per_cell.get((x + dx, y + dy), 0) for dx in (-1, 0, 1) for dy in (-1, 0, 1)), (x, y))
               for x, y in per_cell) if per_cell else (0, None)
    return {'exterior_containers_boxed': boxed, 'exterior_containers_unboxed': unboxed,
            'most_boxes_in_a_window': most[0], 'window_centre': most[1], 'most_boxes_in_a_room': room_most}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('--data-files', required=True, type=Path)
    p.add_argument('--run', type=Path)
    p.add_argument('--json', action='store_true')
    p.add_argument('--boxes', action='store_true', help='also build this tree\'s focus table and count the boxes')
    a = p.parse_args(argv)
    print('=== PHASE 1/2: reading the master ===', flush=True)
    conts, places = census(a.data_files)
    print('=== PHASE 2/2: tallying%s ===' % (' against the run' if a.run else ''), flush=True)
    t = tally(conts, places, a.run)
    if a.boxes:
        print('=== PHASE 3/3: building the focus table from this tree (boxes) ===', flush=True)
        payload, _ = pf.build(a.data_files)
        t['this_tree'] = window_boxes(payload)
    print(json.dumps(t, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
