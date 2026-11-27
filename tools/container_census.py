#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The world-wide container count (CONTAINER-WINDOW-59, CONTAINER-LOOT-TABLES-66, INTERIOR-PLACED-ITEMS-47).

Every placed container (CONT) of the game masters present in the data files (Morrowind.esm, Tribunal.esm,
Bloodmoon.esm), interior and exterior, by cell, with what the original gives it: organic (flora, harvested, never
opened) or opened, its record id and name, its contents (fixed items, levelled lists), a script (and whether that script
takes the activation: OnActivate), an owner, a lock, a trap, a key. With a build run, for every container that opens in
the original, five answers read from the run's own files, by the same rules the engine uses:

  1. in the build: the master that places it is one the build reads (focus.awf's identity table names the files);
  2. drawn: indoors the room map keeps its placement (a CHIM room's record) or draws it as a brush of its own (a
     compiled room's func_wall carrying its aw_ref); outdoors a CHIM world region's scenery holds it (or a map draws it
     as a brush of its own);
  3. aimable: it has a container row ('C', action 1) in the use table the engine reads (id1/areas.awa, the per-area
     copy of id1/focus.awf) and the engine can aim at it (aw_inventory.c placed_target): a room's container where the
     view ray meets its placement box (chim_room.c ChimRoom_RayRef), else where it meets the container's measured box
     (tools/prepare_focus.py CONTAINER_BOXES), within the place's row and box tables (FOCUS_ROWS, FOCUS_BOARDS); a row
     whose reference an edict carries is left to that edict (focus_load) unless the engine keeps container rows
     (CONTAINER_EDICT_ROWS_KEPT);
  4. opens: E opens its strip (aw_cstrip.c): unlocked (a locked one says Locked: the engine has no key use, lockpick or
     Open spell for containers yet, CONTAINER_KEY_OPENS); a trapped one springs its trap first;
  5. contents filled: the area record holds its contents list with every entry of the record (items, levelled lists).

Writes the full table (every container, every cell) as JSON; --summary writes the public measurement (totals, the
gaps by reason, the cells with gaps) that docs/performance/container-census.json keeps and the gate test reads.

    python3 tools/container_census.py --data-files DIR --run RUN [--out FILE] [--summary FILE] [--masters LIST]
"""
import argparse
import json
from pathlib import Path
import re
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

from mwad.esm import GAME_MASTERS, records, subrecords, string, first   # noqa: E402
from mwad.paths import resolve_data_files, child_ci                    # noqa: E402
import prepare_focus as pf                                              # noqa: E402
from ref_identity import stable_ref, split                             # noqa: E402

SCHEMA = 'amiwind-container-census-2'
FILE_NAME = 'container-census.json'
FOCUS = 'image/boot/id1/focus.awf'
AREAS = 'image/boot/id1/areas.awa'
MAPS = 'image/boot/id1/maps'
REGIONS = 'chim-world/work'
# the scenery a frame exports and places as its own beside its scenery folder (tools/chim/seyda.py: the tutorial barrel,
# and the containers that open, SEYDA-CONTAINERS-NOT-DRAWN-67)
OWN_EXPORTS = ('opening-barrel-source', 'open-containers-source')
ROOM_SOURCE_MASK = 0xFFFFFF
# The engine's tables (aw_inventory.c): rows of one place (a room, or the 3 x 3 exterior cells) and their boxes
FOCUS_ROWS = 1536
FOCUS_BOARDS = 1536     # PLANT-BOX-AIM-69 (256 until v0.0.69-dev6: the plants' boxes took signposts out of the table)
# The engine's rules (tests/test_container_census.py reads them against aw_inventory.c):
# CONTAINER_EDICT_ROWS_KEPT: a container drawn as an edict of its own (a compiled room's func_wall with its aw_ref)
# keeps its row (aimed at where the view ray meets that brush, or its box); False: the row is left to the edict, which
# has no use, so the container is never aimed at (the v0.0.66 engine and before).
CONTAINER_EDICT_ROWS_KEPT = True       # CONTAINER-BRUSH-ROWS-67 (v0.0.67)
# CONTAINER_KEY_OPENS: a locked container opens for the player who carries its key (its area record names the key,
# tools/prepare_area_tables.py); False: Locked, always (v0.0.66 and before).
CONTAINER_KEY_OPENS = True             # LOCKED-CONTAINERS-NEVER-OPEN-67 (v0.0.67)
# ROOM_STABLE_IDS: the engine reads a room record's placement number (the merged master's: master index * 2**22 + the
# reference's own number, tools/chim/cut.py source_ref) as the stable reference id of the use table (master index *
# 2**20 + number, tools/ref_identity.py); False: it compares the two as they are, so an expansion's room placement is
# never matched (its containers fall back to their measured box, its items count as not drawn; v0.0.66 and before).
ROOM_STABLE_IDS = True                 # REF-IDENTITY-MERGED-MASTER-66, the engine side (v0.0.67)
# The rules of the v0.0.66 engine, for a count of a build made with it (--engine-rules v0.0.66)
RULES_V066 = {'edict_rows_kept': False, 'key_opens': False, 'room_stable_ids': False}
MERGED_SHIFT, STABLE_SHIFT = 22, 20


def stable_of_merged(number):
    """The stable reference id of a room placement's source number (its low 24 bits, the merged master's form)."""
    n = int(number) & ROOM_SOURCE_MASK
    return (n >> MERGED_SHIFT) << STABLE_SHIFT | (n & ((1 << MERGED_SHIFT) - 1))
CONT_RESPAWN = 2                       # the CONT record's Respawn flag (OpenMW esm3 loadcont)
# PRISON-SHIP-ITEMS-TAKEABLE-65: the cells whose containers never open in the original, with why: nothing opens before
# the release papers' EnableInventoryMenu (OpenMW 0.53 Container::activate), and the ship is left behind before them
CLOSED_IN_ORIGINAL = {'imperial prison ship': 'the Inventory window is allowed only by the release papers, after '
                                              'the ship is left behind'}
# the cells whose containers open only after the release papers (counted as opening; the journey checks it)
AFTER_THE_PAPERS = frozenset({'seyda neen, census and excise office'})
# the opening's own object: E on the courtyard barrel takes Fargoth's ring (aw_opening.c, aw_activated.h)
OPENING_OWN = {172851: 'the courtyard barrel: the opening takes its ring (aw_opening.c), no strip'}
ON_ACTIVATE = re.compile(r'\bonactivate\b')


# ---------------------------------------------------------------------------------------------------- the masters

def present_masters(data):
    """The game masters in DATA in load order (the base game first)."""
    return tuple(m for i, m in enumerate(GAME_MASTERS) if child_ci(Path(data), m, required=i == 0) is not None)


def script_takes_activation(raw):
    """{folded script id} of every script whose text reads OnActivate (comments left out): the original then gives
    the activation to the script, which opens the container only with its own Activate (OpenMW 0.51 World::activate
    and the local script's OnActivate flag)."""
    out = set()
    for tag, flags, payload in records(raw):
        if tag != 'SCPT' or flags & 0x20:
            continue
        fields = list(subrecords(payload))
        head, text = first(fields, 'SCHD'), first(fields, 'SCTX')
        if not head or not text:
            continue
        name = head[:32].split(b'\0', 1)[0].decode('cp1252', 'replace').casefold()
        body = '\n'.join(line.split(';', 1)[0] for line in text.decode('cp1252', 'replace').casefold().splitlines())
        if ON_ACTIVATE.search(body):
            out.add(name)
    return out


def cont_records(raw, levelled, items=None):
    """{folded id: record} of every live CONT record: name, model, organic, script, respawn, its NPCO entries as
    [(folded id, count, 'item' | 'levelled' | 'unknown')]."""
    out = {}
    for tag, flags, payload in records(raw):
        if tag != 'CONT' or flags & 0x20:
            continue
        fields = list(subrecords(payload))
        if any(k == 'DELE' for k, _ in fields):
            continue
        ident = string(first(fields, 'NAME'), 'NAME', errors='replace').casefold()
        name = string(first(fields, 'FNAM'), 'FNAM', errors='replace').strip() if first(fields, 'FNAM') else ''
        flag = first(fields, 'FLAG') or b''
        bits = struct.unpack_from('<I', flag)[0] if len(flag) >= 4 else 0
        model = string(first(fields, 'MODL'), 'MODL', errors='replace').replace('/', '\\').casefold() \
            if first(fields, 'MODL') else ''
        script = string(first(fields, 'SCRI'), 'SCRI', errors='replace').casefold() if first(fields, 'SCRI') else ''
        entries = []
        for key, value in fields:
            if key != 'NPCO' or len(value) < 36:
                continue
            count = struct.unpack_from('<i', value)[0]
            entry = value[4:36].split(b'\0', 1)[0].decode('ascii', 'replace').casefold()
            if not entry or not count:
                continue
            kind = 'levelled' if entry in levelled else 'item' if items is None or entry in items else 'unknown'
            entries.append((entry, abs(count), kind))
        out[ident] = {'name': name, 'model': model, 'organic': bool(bits & pf.CONT_ORGANIC), 'script': script,
                      'respawn': bool(bits & CONT_RESPAWN), 'entries': entries}
    return out


def census(data_files, masters=None):
    """(masters, records, places) of every placed container of MASTERS (default: every game master present) in
    DATA_FILES; each place a dict (see the module text)."""
    from cell_numbers import load_table, room_numbers
    from mwad.masters import master_bytes
    data = resolve_data_files(Path(data_files))
    masters = tuple(masters) if masters else present_masters(data)
    raw = master_bytes(data, masters)
    numbers = room_numbers(load_table(data)[0])
    levelled = pf.item_lists(raw)
    items = {k for k, v in pf.objects_of(raw, levelled).items() if v[0] == 'I'}
    conts = cont_records(raw, levelled, items)
    takes = script_takes_activation(raw)
    places = []
    for cell, interior, grid, _region, refs in pf.cells_of(raw):
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
            reference = stable_ref(pf.MASTER, ref['number'])
            places.append({
                'closed_in_original': CLOSED_IN_ORIGINAL.get((cell or '').casefold()) if interior else None,
                'after_the_papers': interior and (cell or '').casefold() in AFTER_THE_PAPERS,
                'reference': reference, 'master': split(reference)[0], 'cell': cell or '',
                'grid': None if interior else list(grid), 'interior': interior, 'key': key, 'id': ident,
                'name': rec['name'], 'model': rec['model'],
                # FARGOTH-STASH-STUMP-69: only an organic container of a harvest kind is picked in the world; every
                # other one opens its window (tools/prepare_focus.py harvest_picked) and is counted to open
                'organic': rec['organic'] and pf.harvest_picked(rec['model']), 'script': rec['script'],
                'on_activate': bool(rec['script'] and rec['script'] in takes), 'respawn': rec['respawn'],
                'items': sum(1 for e in rec['entries'] if e[2] == 'item'),
                'lists': sum(1 for e in rec['entries'] if e[2] == 'levelled'),
                'unknown_entries': sum(1 for e in rec['entries'] if e[2] == 'unknown'),
                'lock': pf.lock_level(ref), 'trapped': bool(ref.get('TNAM')), 'keyed': bool(ref.get('KNAM')),
                'owned': bool(ref.get('ANAM') or ref.get('CNAM')), 'data_ok': len(ref.get('DATA', b'')) == 24})
    return masters, conts, places


# ---------------------------------------------------------------------------------------------------- the run

def is_box(field):
    """True when a row's 32-byte id field holds a packed box (prepare_focus board_box: half extents, a unit
    quaternion), the engine's own test (aw_inventory.c focus_board_add)."""
    h = struct.unpack_from('<3f', field)
    q = struct.unpack_from('<4f', field, 12)
    return all(0 <= v < 100000 for v in h) and all(-1.01 <= v <= 1.01 for v in q) and \
        0.98 <= sum(v * v for v in q) <= 1.02


def row_accepted(row):
    """The engine keeps this 96-byte row (aw_inventory.c focus_add_row): a kind it shows, a name, a weight in range,
    a named board with its box. Returns (kept, takes a box slot)."""
    kind = chr(row[0])
    if kind not in 'IADCN':
        return False, False
    name = row[28:64].split(b'\0', 1)[0]
    weight = struct.unpack_from('<f', row, 20)[0]
    if not name or not (0 <= weight < 1000000):
        return False, False
    boxed = is_box(row[64:96]) if kind in 'NC' else False
    if kind == 'N' and not boxed:
        return False, False
    return True, boxed


def read_focus(raw):
    """focus.awf -> ({key: [row bytes]}, the identity table's content files)."""
    if raw[:4] not in (b'AWF2', b'AWF3'):
        raise ValueError('focus.awf is not AWF2/AWF3')
    rooms = struct.unpack_from('<I', raw, 4)[0]
    index = [struct.unpack_from('<III', raw, 8 + 12 * i) for i in range(rooms)]
    base = 8 + 12 * rooms
    table = {key: [raw[base + (first_row + j) * pf.ROW:base + (first_row + j + 1) * pf.ROW] for j in range(count)]
             for key, first_row, count in index}
    files = []
    if raw[:4] == b'AWF3':
        at = base + sum(c for _, _, c in index) * pf.ROW
        if raw[at:at + 4] == b'AWO1':
            pool_at = at + 8 + 8 * struct.unpack_from('<I', raw, at + 4)[0]
            at = pool_at + 4 + struct.unpack_from('<I', raw, pool_at)[0]
            if raw[at:at + 4] == b'AWC1':
                items_at = at + 8 + 12 * struct.unpack_from('<I', raw, at + 4)[0]
                at = items_at + 4 + 36 * struct.unpack_from('<I', raw, items_at)[0]
                if raw[at:at + 4] == b'AWI1':
                    p = at + 5
                    for _ in range(raw[at + 4]):
                        length = raw[p + 1]
                        files.append(raw[p + 2:p + 2 + length].decode('ascii', 'replace'))
                        p += 2 + length + 12
    return table, files


def read_area_containers(raw):
    """id1/areas.awa -> ({area key: [row bytes]}, {reference: (contents kept, flags, lock, key slot)}); the key slot
    is the key's item index + 1 in its area (0 none, and in an areas.awa before v0.0.67)."""
    if raw[:4] != b'AWA1':
        raise ValueError('areas.awa is not AWA1')
    n = struct.unpack_from('<I', raw, 4)[0]
    rows, conts = {}, {}
    for i in range(n):
        key, offset, size = struct.unpack_from('<III', raw, 24 + 12 * i)
        rec = raw[offset:offset + size]
        if rec[:4] != b'AWB1':
            continue
        nrows, owners, owned, ncont, _ncontents, _nitems = struct.unpack_from('<6H', rec, 4)
        at = 16
        rows[key] = [rec[at + j * pf.ROW:at + (j + 1) * pf.ROW] for j in range(nrows)]
        at += nrows * pf.ROW + owners * 32 + owned * 8
        for j in range(ncont):
            ref, _first, kept, flags, lock, key = struct.unpack_from('<IHHBBH', rec, at + 12 * j)
            conts[ref] = (kept, flags, lock, key)
    return rows, conts


def room_record_of(run, path):
    """The CHIM room record a room map of RUN's image names, read (chim.room_records.read_room_record), or None for a
    map that is not a CHIM room. The record is looked for beside the map in the image's id1 first, then in the CHIM
    interiors stage of the run (RUN/chim-interiors/<store>/rooms/<room>.crm): an image whose room store sits on the
    world partition holds no store in its boot id1 (CONTAINER-COUNT-LOOSE-ROOM-PATH-68: the count read only id1 and
    stopped at the first room map). ValueError when neither holds it."""
    from chim.room_records import read_room_record
    from map_files import room_record
    found = room_record(path)
    if found is None:
        return None
    store, room = found
    for root in (Path(path).parent.parent, Path(run) / STAGE_ROOMS):
        candidate = root / store / 'rooms' / (room + '.crm')
        if candidate.is_file():
            return read_room_record(candidate.read_bytes())
    raise ValueError('CHIM room map %s names %s/rooms/%s.crm, which neither the image nor the run holds'
                     % (Path(path).name, store, room))


STAGE_ROOMS = 'chim-interiors'      # the run's CHIM interiors stage (tools/chim/interior.py OUT/<store>/rooms)


def map_rooms(run):
    """{room number: ('chim', {placed source numbers, as the room record has them}) | ('bsp', None)} of the image's
    room maps, and {reference: map name} of every brush (func_wall) that carries an aw_ref (any map)."""
    from chim.frame_map import entities
    from map_files import LEGACY_EXT, MAP_EXTS
    rooms, edicts = {}, {}
    for path in sorted((Path(run) / MAPS).iterdir()):
        if path.suffix not in MAP_EXTS:
            continue
        try:
            ents = entities(path.read_bytes())
        except ValueError:
            continue
        world = ents[0] if ents else {}
        for e in ents[1:]:
            ref = e.get('aw_ref')
            if ref and e.get('classname') == 'func_wall':
                try:
                    edicts.setdefault(int(float(ref)), path.name)
                except ValueError:
                    pass
        number = str(world.get('_aw_cell_int', ''))
        if not number.isdigit():
            continue
        if path.suffix == LEGACY_EXT:
            rooms.setdefault(int(number), ('bsp', None))
            continue
        room = room_record_of(run, path)
        if room is not None:
            kind, placed = rooms.setdefault(int(number), ('chim', set()))
            if kind == 'chim':
                placed.update(int(p['ref']) & ROOM_SOURCE_MASK for p in room['placements'])
    return rooms, edicts


def exterior_scenery(run):
    """{source references} the CHIM world regions draw (their scenery indexes, less the references a region lost)."""
    drawn = set()
    root = Path(run) / REGIONS
    if not root.is_dir():
        return drawn
    for work in sorted(root.iterdir()):
        indexes = [i for i in [work / 'scenery' / 'scenery-index.json'] +
                   [work / name / 'scenery-index.json' for name in OWN_EXPORTS] if i.is_file()]
        if not indexes:
            continue
        refs = [r for i in indexes for r in json.loads(i.read_text(encoding='utf-8')).get('references', [])]
        lost = set()
        coverage = work / 'coverage.json'
        if coverage.is_file():
            lost = {int(r) if not isinstance(r, dict) else int(r.get('number', 0))
                    for r in json.loads(coverage.read_text(encoding='utf-8')).get('lost_references', [])}
        for r in refs:
            if r.get('type') == 'CONT' and r.get('number') not in lost:
                drawn.add(stable_ref(pf.MASTER, r['number']))
    return drawn


def window_slots(table, key):
    """{reference: (row slot, box slot or None)} of the rows the engine keeps for the place KEY (a room alone; an
    exterior cell with its eight neighbours, aw_inventory.c focus_load order), and the place's rows and boxes."""
    if key < 0x80000000:
        keys = [key]
    else:
        gx, gy = (key >> 12 & 0xFFF) - pf.GRID_BIAS, (key & 0xFFF) - pf.GRID_BIAS
        keys = [pf.exterior_key(gx + dx, gy + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
    out, rows, boxes = {}, 0, 0
    for k in keys:
        for row in table.get(k, ()):
            kept, boxed = row_accepted(row)
            if not kept:
                continue
            ref = struct.unpack_from('<I', row, 4)[0]
            box = None
            if boxed:
                if boxes < FOCUS_BOARDS:
                    box = boxes
                boxes += 1
                if row[0] == ord('N') and box is None:
                    continue           # a board past the box table is not kept at all
            if rows < FOCUS_ROWS and row[0] == ord('C'):
                out[ref] = (rows, box)
            rows += 1
    return out, rows, boxes


def judge(places, run, edict_rows_kept=None, key_opens=None, room_stable_ids=None):
    """Every place gets 'build' {in_build, drawn, aimable, opens, filled, aim, gaps} against RUN, by the engine rules
    (default: this tree's CONTAINER_EDICT_ROWS_KEPT, CONTAINER_KEY_OPENS, ROOM_STABLE_IDS). Returns the run facts."""
    edict_rows_kept = CONTAINER_EDICT_ROWS_KEPT if edict_rows_kept is None else edict_rows_kept
    key_opens = CONTAINER_KEY_OPENS if key_opens is None else key_opens
    room_stable_ids = ROOM_STABLE_IDS if room_stable_ids is None else room_stable_ids
    run = Path(run)
    table, files = read_focus((run / FOCUS).read_bytes())
    areas = run / AREAS
    if areas.is_file():
        area_rows, area_conts = read_area_containers(areas.read_bytes())
        table = area_rows             # the engine reads the area tables (aw_inventory.c area_ready)
    else:
        area_conts = None
    rooms, edicts = map_rooms(run)
    scenery = exterior_scenery(run)
    rows_of, built = {}, set()
    for key, rows in table.items():
        for row in rows:
            ref = struct.unpack_from('<I', row, 4)[0]
            if 0 < ref < 0x800000:
                built.add(split(ref)[0].casefold())     # the masters the build reads: those with rows
            if row[0] == ord('C'):
                rows_of[ref] = (key, row)
    stable_rooms = {k: (kind, {stable_of_merged(n) for n in placed} if kind == 'chim' else None)
                    for k, (kind, placed) in rooms.items()}
    slots_cache, most_rows, most_boxes = {}, 0, 0
    for p in places:
        b = p['build'] = {'in_build': False, 'drawn': False, 'aimable': False, 'opens': False, 'filled': False,
                          'aim': None, 'gaps': []}
        if p['organic'] or p.get('closed_in_original'):
            continue
        gaps = b['gaps']
        if p['master'].casefold() not in built:
            gaps.append('not in this build: %s is not one of its masters' % p['master'])
            continue
        b['in_build'] = True
        ref = p['reference']
        edict = ref in edicts
        room_ray = False
        if p['interior']:
            room = stable_rooms.get(p['key']) if p['key'] is not None else None
            if room is None:
                gaps.append('not drawn: its room is not in this build')
            elif room[0] == 'chim':
                b['drawn'] = ref in room[1] or edict
                # the engine's room ray finds the placement when its number reads as this id (aw_inventory.c
                # placed_target, chim_room.c ChimRoom_RayRef)
                room_ray = ref in room[1] and (room_stable_ids or ref in rooms[p['key']][1])
                if not b['drawn']:
                    gaps.append('not drawn: the room map leaves its placement out')
                elif ref in room[1] and not room_ray:
                    gaps.append('the room draws it under the merged master\'s number: the engine does not match it '
                                'to its row (aimed by its measured box only)')
            else:
                b['drawn'] = edict
                if not edict:
                    gaps.append('not drawn: the compiled room map has no brush of it')
        else:
            b['drawn'] = ref in scenery or edict
            if not b['drawn']:
                gaps.append('not drawn: no CHIM world region holds it')
        found = rows_of.get(ref)
        if found is None:
            gaps.append('no use-table row: %s' % ('the record has no name' if not p['name'] else
                                                 'no room number' if p['key'] is None else
                                                 'past the room row cap or left out'))
        else:
            key, row = found
            if key not in slots_cache:
                slots_cache[key] = window_slots(table, key)
                most_rows = max(most_rows, slots_cache[key][1])
                most_boxes = max(most_boxes, slots_cache[key][2])
            slots = slots_cache[key][0]
            accepted = row_accepted(row)[0] and row[2] & 3 == pf.ACT_TAKE
            if not accepted:
                gaps.append('its row does not open (action %d)' % row[2])
            elif ref not in slots:
                gaps.append('past the place\'s %d rows' % FOCUS_ROWS)
            elif ref in OPENING_OWN and edict:
                gaps.append(OPENING_OWN[ref])
            elif edict and not edict_rows_kept:
                gaps.append('drawn as a brush of its own (%s): its row is left to the brush, which has no use'
                            % edicts[ref])
            else:
                if edict:
                    b['aim'] = 'brush'
                elif room_ray:
                    b['aim'] = 'room placement box'
                elif slots[ref][1] is not None:
                    b['aim'] = 'measured box'
                elif is_box(row[64:96]):
                    gaps.append('its box is past the place\'s %d boxes' % FOCUS_BOARDS)
                else:
                    gaps.append('no box: near-the-point aim only (model %s not measured)' % (p['model'] or '?'))
                b['aimable'] = b['aim'] is not None and b['drawn']
        if b['aimable']:
            # the key travels in the container's area record (LOCKED-CONTAINERS-NEVER-OPEN-67)
            key_slot = area_conts.get(ref, (0, 0, 0, 0))[3] if area_conts is not None else 0
            if p['lock'] <= 0:
                b['opens'] = True
            elif key_opens and key_slot:
                b['opens'] = True
                b['with_key'] = True
            elif not key_opens:
                gaps.append('locked (level %d): the engine has no key use, lockpick or Open spell for containers'
                            % p['lock'] if not p['keyed'] else
                            'locked (level %d), its key in the data: the engine does not use a key on a container'
                            % p['lock'])
            elif p['keyed']:
                gaps.append('locked (level %d), its key in the data: the area record does not name it' % p['lock'])
            else:
                gaps.append('locked (level %d), no key: lockpicks and the Open spell are not in the game yet'
                            % p['lock'])
        expected = p['items'] + p['lists']
        if area_conts is not None:
            kept = area_conts.get(ref)
            if kept is None:
                gaps.append('no contents record in its area')
            elif kept[0] < expected:
                gaps.append('contents: %d of %d entries kept' % (kept[0], expected))
            else:
                b['filled'] = True
        if p['unknown_entries']:
            gaps.append('contents: %d entries name no item or levelled list in the data' % p['unknown_entries'])
    return {'files': files, 'masters_built': sorted(m for m in GAME_MASTERS if m.casefold() in built),
            'rooms': len(rooms), 'brushes': len(edicts), 'most_rows': most_rows, 'most_boxes': most_boxes,
            'area_tables': area_conts is not None,
            'engine_rules': {'container_edict_rows_kept': edict_rows_kept, 'container_key_opens': key_opens,
                             'room_stable_ids': room_stable_ids}}


# ---------------------------------------------------------------------------------------------------- the tables

COLUMNS = ('to_open', 'in_build', 'drawn', 'aimable', 'opens', 'filled')
KINDS = ('fixed', 'levelled', 'empty', 'scripted', 'on_activate', 'owned', 'locked', 'trapped', 'keyed', 'respawn')


def kinds_of(p):
    return {'fixed': p['items'] > 0, 'levelled': p['lists'] > 0, 'empty': not p['items'] and not p['lists'],
            'scripted': bool(p['script']), 'on_activate': p['on_activate'], 'owned': p['owned'],
            'locked': p['lock'] > 0, 'trapped': p['trapped'], 'keyed': p['keyed'], 'respawn': p['respawn']}


def cell_name(p):
    if p['interior']:
        return p['cell']
    return '%s (%d,%d)' % (p['cell'], *p['grid']) if p['cell'] else '%d,%d' % tuple(p['grid'])


def tally(masters, places, run=None, facts=None):
    """The counts: totals by master and side, the gaps by reason, and one row per cell."""
    def empty():
        return dict({c: 0 for c in COLUMNS}, placed=0, organic=0, closed_in_original=0, after_the_papers=0,
                    opens_with_key=0, **{k: 0 for k in KINDS})
    totals, cells, reasons = {}, {}, {}
    for p in places:
        side = 'interior' if p['interior'] else 'exterior'
        for bucket in (totals.setdefault('all', {}).setdefault(side, empty()),
                       totals.setdefault(p['master'], {}).setdefault(side, empty()),
                       cells.setdefault((p['master'], side, cell_name(p)), empty())):
            bucket['placed'] += 1
            if p['organic']:
                bucket['organic'] += 1
                continue
            if p.get('closed_in_original'):
                bucket['closed_in_original'] += 1
                continue
            bucket['after_the_papers'] += bool(p.get('after_the_papers'))
            bucket['to_open'] += 1
            for k, v in kinds_of(p).items():
                bucket[k] += bool(v)
            b = p.get('build')
            if b:
                for c in COLUMNS[1:]:
                    bucket[c] += bool(b[c])
                bucket['opens_with_key'] += bool(b.get('with_key'))
        b = p.get('build')
        if b and not p['organic'] and not p.get('closed_in_original'):
            for g in b['gaps']:
                reason = re.sub(r'\(level \d+\)', '(level N)', re.sub(r' \([^)]*\.(bsp|chim)\)', '', g))
                reason = re.sub(r'model [^ )]+', 'model M', re.sub(r'\d+ of \d+', 'N of M', reason))
                reason = re.sub(r'action \d+', 'action N', re.sub(r'(\d+) entries', 'N entries', reason))
                r = reasons.setdefault(reason, {'containers': 0, 'cells': set()})
                r['containers'] += 1
                r['cells'].add(cell_name(p))
    rows = [dict(master=m, side=s, cell=c, **v) for (m, s, c), v in sorted(cells.items(), key=lambda kv: kv[0])]
    out = {'schema': SCHEMA, 'masters': list(masters), 'totals': totals,
           'gaps': {r: {'containers': v['containers'], 'cells': len(v['cells']),
                        'top_cells': sorted(v['cells'])[:12]}
                    for r, v in sorted(reasons.items(), key=lambda kv: -kv[1]['containers'])},
           'cells': rows}
    if run:
        out['run'] = dict(facts or {}, path=str(run), name=Path(run).name)
    return out


def summary(full):
    """The public measurement: the totals, the gaps, the cells with a gap among the ones the build holds."""
    keep = [r for r in full['cells'] if r['in_build'] and any(r[c] < r['in_build'] for c in COLUMNS[2:])]
    return {k: full[k] for k in ('schema', 'masters', 'totals', 'gaps', 'run') if k in full} | {
        'cells_with_gaps': [{k: r[k] for k in ('master', 'side', 'cell') + COLUMNS + ('locked', 'keyed')}
                            for r in keep]}


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


def lines(t):
    """The count as text: one line a master and side, then the gaps."""
    out = []
    for master, sides in t['totals'].items():
        for side, v in sides.items():
            out.append('%-14s %-8s placed %6d, to open %6d: in build %6d, drawn %6d, aimable %6d, opens %6d, '
                       'contents filled %6d' % (master, side, v['placed'], v['to_open'], v['in_build'], v['drawn'],
                                                v['aimable'], v['opens'], v['filled']))
    for reason, v in t['gaps'].items():
        out.append('  gap: %6d containers in %4d cells: %s' % (v['containers'], v['cells'], reason))
    return out


# The gaps the committed measurement may hold (docs/performance/CONTAINERS.json), each with the register entry that
# holds its cause and the most containers it may count; tests/test_container_census.py fails on a gap reason not here
# or past its count, so a container that stops opening fails the gate. Lowered as fixes land, never raised without
# its entry (a ratchet).
KNOWN_GAPS = {
    'locked (level N), no key: lockpicks and the Open spell are not in the game yet':
        ('LOCKED-CONTAINERS-NEVER-OPEN-67', 1142),
    # Solstheim's exterior (152, not in the CHIM world yet) and, until a build with its fix, Seyda Neen's 14
    'not drawn: no CHIM world region holds it': ('BUILD-EXPANSIONS-31 SEYDA-CONTAINERS-NOT-DRAWN-67', 166),
    # Mournhold's Great Bazaar (41) and Godsreach (5): rooms not in the build
    'not drawn: its room is not in this build': ('BUILD-EXPANSIONS-31', 46),
    # until a build whose area records name the keys (tools/prepare_area_tables.py, v0.0.67)
    'locked (level N), its key in the data: the area record does not name it': ('LOCKED-CONTAINERS-NEVER-OPEN-67', 136),
    # the courtyard barrel stays the opening's own object (E takes Fargoth's ring)
    'the courtyard barrel: the opening takes its ring (aw_opening.c), no strip': ('CHIM-COURT-BARREL-USE-33', 1),
}


def verdict(t, known=None):
    """The problems of the count T (tally or summary): a gap reason KNOWN does not list, or a gap past its count.
    [] when the count holds."""
    known = KNOWN_GAPS if known is None else known
    out = []
    for reason, v in t.get('gaps', {}).items():
        if reason not in known:
            out.append('%d containers: %s (no register entry allows this gap)' % (v['containers'], reason))
        elif v['containers'] > known[reason][1]:
            out.append('%d containers: %s (%s allows %d)' % (v['containers'], reason, *known[reason]))
    return out


def build_step(run, data_files, log=print):
    """The builder's container count after a passed image (tools/build.py): RUN/container-census.json (the summary)
    and RUN/container-census-full.json, a line per master and side, the verdict against KNOWN_GAPS. Never raises:
    a count that cannot be made is said and the build goes on. Returns the problems ([] holds), None when skipped."""
    started = time.monotonic()
    try:
        if not (Path(run) / FOCUS).is_file():
            log('Container count: skipped (no use table in this run)')
            return None
        log('Container count: started (1 worker: the masters, the use table, the room maps, the CHIM regions)')
        masters, _conts, places = census(data_files)
        facts = judge(places, run)
        t = tally(masters, places, run, facts)
        full = dict(t, containers=places)
        (Path(run) / FILE_NAME).write_text(json.dumps(summary(t), indent=1, sort_keys=True) + '\n',
                                           encoding='utf-8', newline='\n')
        (Path(run) / FILE_NAME.replace('.json', '-full.json')).write_text(
            json.dumps(full, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
        for line in lines(t):
            log('Container count: ' + line.strip())
        problems = verdict(t)
        for line in problems:
            log('Container count: WARNING: ' + line)
        log('Container count: %s, written %s (took %.1f s)' % ('holds' if not problems else '%d problems' % len(problems),
                                                               Path(run) / FILE_NAME, time.monotonic() - started))
        return problems
    except Exception as exc:  # noqa: BLE001 - a measurement; the build's own stages passed
        log('Container count: not made: %s: %s' % (type(exc).__name__, exc))
        return None


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('--data-files', required=True, type=Path)
    p.add_argument('--run', type=Path)
    p.add_argument('--masters', help='comma list of game masters (default: every one present in the data files)')
    p.add_argument('--engine-rules', choices=('current', 'v0.0.66'), default='current',
                   help='the engine rules to judge by: this tree\'s (default), or those of the v0.0.66 engine')
    p.add_argument('--out', type=Path, help='the full table (JSON)')
    p.add_argument('--summary', type=Path, help='the public measurement (JSON)')
    p.add_argument('--json', action='store_true', help='print the totals and gaps as JSON')
    p.add_argument('--boxes', action='store_true', help='also build this tree\'s focus table and count the boxes')
    a = p.parse_args(argv)
    started = time.monotonic()
    steps = 3 if a.run else 2
    print('=== PHASE 1/%d: reading the masters ===' % steps, flush=True)
    masters, _conts, places = census(a.data_files, a.masters.split(',') if a.masters else None)
    print('  %d placed containers in %s (%.1f s)' % (len(places), ', '.join(masters), time.monotonic() - started),
          flush=True)
    facts = None
    if a.run:
        print('=== PHASE 2/%d: judging every container against the run ===' % steps, flush=True)
        facts = judge(places, a.run, **(RULES_V066 if a.engine_rules == 'v0.0.66' else {}))
        print('  run read (%.1f s): %d room maps, %d brushes with a reference' %
              (time.monotonic() - started, facts['rooms'], facts['brushes']), flush=True)
    print('=== PHASE %d/%d: tallying ===' % (steps, steps), flush=True)
    t = tally(masters, places, a.run, facts)
    if a.boxes:
        payload, _ = pf.build(a.data_files)
        t['this_tree'] = window_boxes(payload)
    if a.out:
        full = dict(t, containers=[{k: v for k, v in p.items()} for p in places])
        a.out.write_text(json.dumps(full, indent=0, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
        print('  written %s' % a.out, flush=True)
    if a.summary:
        a.summary.write_text(json.dumps(summary(t), indent=1, sort_keys=True) + '\n', encoding='utf-8',
                             newline='\n')
        print('  written %s' % a.summary, flush=True)
    if a.json:
        print(json.dumps({k: t[k] for k in ('masters', 'totals', 'gaps', 'run') if k in t}, indent=1))
    else:
        print('\n'.join(lines(t)))
    if a.run:
        problems = verdict(t)
        print('verdict: %s' % ('holds (every gap has its register entry and count)' if not problems else
                               '%d problems:\n  ' % len(problems) + '\n  '.join(problems)))
    print('took %.1f s' % (time.monotonic() - started), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
