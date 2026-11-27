#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The item sweep of a compiled room (CENSUS-SHELF-PLATE-BAKED-67; the same check is meant for every interior,
GAMEPLAY-PARITY-NEXT-69): every placed reference of the original cell, counted by category, against what the room's
map holds. Each live reference is one of:
  entity    an entity of the map carries its reference (aw_ref): a brush of its own (func_wall: furniture, an item, a
            container, a door), an actor (aw_npc), a flame (aw_flame). The engine aims at, takes, opens or talks to
            the thing through that edict.
  placed    drawn by the engine's placed item list (progs/items/placed.awp, the room's key: an item model by its
            reference, WORLD-OBJECT-PLACEMENT-59), aimed at and taken through its focus row.
  baked     in the room's bake (the conversion report's group) but carried by no entity: part of the room's geometry,
            drawn and solid, never aimed at or taken.
  left out  not in the map: the converter's rule (mwad.interior.omission_reason) when one applies, else "not in the
            map".
--check refuses (exit 1) when a takeable item of the cell (the original's carryable kinds, and a light that can be
carried) is neither an entity of its own nor on the placed list, or a container is not an entity, naming each: it
could not be aimed at, taken or opened.
Reads the master, the map and the placed list; writes only --out (JSON) and --md.

    room_item_census.py --data-files DIR --cell "Seyda Neen, Census and Excise Office" --map census.bsp
                        [--report census-conversion.json] [--placed placed.awp] [--out census.json] [--md census.md]
                        [--check]
"""
import argparse
import json
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

# The original's record kinds by the names the tables use.
CATEGORY = {
    'MISC': 'misc', 'WEAP': 'weapon', 'ARMO': 'armour', 'CLOT': 'clothing', 'BOOK': 'book', 'INGR': 'ingredient',
    'ALCH': 'potion', 'APPA': 'apparatus', 'LOCK': 'lockpick', 'PROB': 'probe', 'REPA': 'repair item',
    'LIGH': 'light', 'CONT': 'container', 'DOOR': 'door', 'ACTI': 'activator', 'NPC_': 'NPC', 'CREA': 'creature',
    'STAT': 'static', 'LEVC': 'levelled creature', 'LEVI': 'levelled item',
}
ORDER = list(CATEGORY.values())
# The kinds a player can take (OpenMW 0.53 mwclass: each of these classes' activate gives the take action); a light
# only when its record says it can be carried (LHDT flag 0x2, mwclass/light.cpp Light::activate).
TAKEABLE = ('ALCH', 'APPA', 'ARMO', 'BOOK', 'CLOT', 'INGR', 'LOCK', 'MISC', 'PROB', 'REPA', 'WEAP')
LIGHT_CARRY = 0x2


def takeable(ref):
    """1 when the player can take the placed reference in the original."""
    if ref.get('type') in TAKEABLE:
        return True
    return ref.get('type') == 'LIGH' and bool((ref.get('light') or {}).get('flags', 0) & LIGHT_CARRY)


def _entity_text(data):
    if len(data) < 4 + 15 * 8:
        raise ValueError('not a map: %d bytes' % len(data))
    offset, size = struct.unpack_from('<ii', data, 4)
    if offset < 0 or size < 0 or offset + size > len(data):
        raise ValueError('the entity lump lies outside the map')
    return data[offset:offset + size].decode('latin-1').split('\0', 1)[0]


def map_room(data):
    """The room number of the map bytes DATA (its worldspawn's _aw_cell_int, tools/cell_numbers.py), 0 none."""
    block = re.search(r'\{[^{}]*\}', _entity_text(data))
    value = dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', block.group(0))).get('_aw_cell_int', '') if block else ''
    return int(value) if value.isdigit() else 0


def map_references(data):
    """{reference: [entity class, ...]} of the map bytes DATA (a Quake BSP): every entity of the entity lump that
    carries aw_ref, by its classname."""
    text = _entity_text(data)
    found = {}
    for block in re.findall(r'\{[^{}]*\}', text):
        fields = dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', block))
        value = fields.get('aw_ref', '')
        if not value.isdigit() or int(value) <= 0:
            continue
        found.setdefault(int(value), []).append(fields.get('classname', '?'))
    return found


def placed_references(raw, room):
    """The references the placed item list RAW (an AWP1 file, tools/prepare_item_models.py read_placed) draws in
    room ROOM."""
    from prepare_item_models import read_placed
    return {row[0] for row in read_placed(raw).get(room, ())}


STATES = ('entity', 'placed list', 'baked', 'left out')


def census(refs, held, baked=(), omission=None, placed=()):
    """The sweep of one room. REFS: the cell's references (mwad.interior read_interior: number, id, type, model,
    deleted, light); HELD: map_references; BAKED: the references of the room's bake (the conversion report's group);
    OMISSION: a reference's converter rule or None (mwad.interior.omission_reason by default); PLACED: the references
    the placed item list draws in this room (placed_references).
    Returns {'rows': [...], 'categories': {category: counts}, 'problems': [...]}."""
    if omission is None:
        from mwad.interior import omission_reason
        omission = omission_reason
    baked, placed = set(baked), set(placed)
    rows, categories, problems = [], {}, []
    for ref in refs:
        category = CATEGORY.get(ref.get('type'), ref.get('type') or '?')
        counts = categories.setdefault(category, {'placed': 0, 'entity': 0, 'placed list': 0, 'baked': 0,
                                                  'left out': 0, 'deleted': 0, 'takeable': 0})
        row = {'reference': ref['number'], 'id': ref.get('id', ''), 'category': category}
        if ref.get('deleted'):
            counts['deleted'] += 1
            row['state'] = 'deleted'
            rows.append(row)
            continue
        counts['placed'] += 1
        can_take = takeable(ref)
        counts['takeable'] += can_take
        if ref['number'] in held:
            row['state'] = 'entity'
            row['entities'] = sorted(held[ref['number']])
        elif ref['number'] in placed:
            row['state'] = 'placed list'
        elif ref['number'] in baked:
            row['state'] = 'baked'
        else:
            row['state'] = 'left out'
            try:
                row['reason'] = omission(ref) or 'not in the map'
            except (KeyError, TypeError):
                row['reason'] = 'not in the map'
        counts[row['state']] += 1
        if can_take:
            row['takeable'] = True
        if (can_take and row['state'] not in ('entity', 'placed list')) or (
                ref.get('type') == 'CONT' and row['state'] != 'entity'):
            problems.append('%s %s (%s, reference %d) is %s: it cannot be aimed at, %s' % (
                'a takeable' if can_take else 'a', category, row['id'], ref['number'],
                row['state'] + (' (' + row['reason'] + ')' if row.get('reason') else ''),
                'taken' if can_take else 'opened'))
        rows.append(row)
    return {'rows': rows, 'categories': categories, 'problems': problems}


# The opening's two compiled rooms and their maps (tools/prepare_census.py, the interior stage's prison map): the image
# step sweeps them (build_aga.py) and stops the image when one has a problem.
OPENING_ROOMS = (('Imperial Prison Ship', 'prison'), ('Seyda Neen, Census and Excise Office', 'census'))


def opening_sweep(master, id1, rooms=OPENING_ROOMS, numbers=None):
    """The sweep of the opening rooms an image's id1 holds (its maps/<name>.bsp and progs/items/placed.awp), the
    master read once: {'rooms': {cell: result + 'md'}, 'absent': [cells whose map the image does not hold],
    'problems': ['cell: problem', ...]}.
    NUMBERS: {folded cell ID: room number} (tools/cell_numbers.py room_numbers), the table the image step stamps into
    each interior map's worldspawn (_aw_cell_int) late in the step (stamp_staged_cells): the sweep runs before that,
    when the map carries no number yet, so its room on the placed list is the table's (OPENING-SWEEP-BEFORE-STAMP-69:
    without it the prison ship's 79 items on the placed list read as left out and the dev6 build stopped). A map that
    carries a number other than the table's is a problem."""
    from mwad.interior import read_interiors
    id1 = Path(id1)
    present = [(cell, name) for cell, name in rooms if (id1 / 'maps' / (name + '.bsp')).is_file()]
    out = {'rooms': {}, 'absent': [cell for cell, name in rooms if (cell, name) not in present], 'problems': []}
    if not present:
        return out
    placed_raw = (id1 / 'progs/items/placed.awp').read_bytes() if (id1 / 'progs/items/placed.awp').is_file() else b''
    cells = read_interiors(master, [cell for cell, _ in present])
    for (cell, name), data in zip(present, cells):
        raw = (id1 / 'maps' / (name + '.bsp')).read_bytes()
        stamped = map_room(raw)
        listed = (numbers or {}).get(cell.casefold(), 0)
        room = stamped or listed
        result = census(data['refs'], map_references(raw), placed=placed_references(placed_raw, room)
                        if placed_raw and room else ())
        if stamped and listed and stamped != listed:
            result['problems'].append('the map says room %d, the cell number table %d: the placed list is read under '
                                      'the map\'s' % (stamped, listed))
        result.update(map=name + '.bsp', room=room, md=render_md(cell, result))
        out['rooms'][cell] = result
        out['problems'] += ['%s: %s' % (cell, p) for p in result['problems']]
    return out


def render_md(room, result):
    """The table of one room: a row per category (placed, entity, baked, left out, deleted, takeable), then the
    differences named."""
    columns = ('placed', 'entity', 'placed list', 'baked', 'left out', 'deleted', 'takeable')
    lines = ['# Item sweep: %s' % room, '', '| category | ' + ' | '.join(columns) + ' |',
             '|---|' + '---|' * len(columns)]
    cats = result['categories']
    for name in [c for c in ORDER if c in cats] + sorted(c for c in cats if c not in ORDER):
        lines.append('| %s | %s |' % (name, ' | '.join(str(cats[name][k]) for k in columns)))
    lines.append('| all | %s |' % ' | '.join(str(sum(c[k] for c in cats.values())) for k in columns))
    lines += ['', '"placed" counts the live references of the original cell; "placed list" the ones the engine draws '
              'from its placed item list.', '', '## Not drawn as an entity or from the placed list', '']
    other = [r for r in result['rows'] if r.get('state') in ('baked', 'left out')]
    lines += ['- %s `%s` (reference %d): %s%s' % (r['category'], r['id'], r['reference'], r['state'],
                                                 ' (' + r['reason'] + ')' if r.get('reason') else '')
              for r in other] or ['- none']
    lines += ['', '## Problems', ''] + (['- ' + p for p in result['problems']] or ['- none'])
    return '\n'.join(lines) + '\n'


# ======================================================================================================================
# The world census (WORLD-OBJECT-PLACEMENT-59): every item the masters place that a player can take or steal, in every
# room and every exterior cell of every master the build reads, against what a finished build makes of it. The opening
# sweep above is the strict case of two rooms (no problem allowed); this one counts the whole world and holds its gaps
# to a ratchet (KNOWN_GAPS), as tools/container_census.py does for the containers (their own list: a container is not
# counted here).
#
# For each placed takeable reference, five answers, read from the run's own files by the engine's rules
# (engine/aga/src/aw_inventory.c focus_load, placed_read_key, AW_AreaEffectHide; tests/test_room_item_census.py reads
# the rules against the source):
#   in build   its master is one the build reads, and indoors its room is in the image;
#   drawn      indoors: an entity of the room map carries its reference (aw_ref), or the CHIM room record places it, or
#              the placed item list draws it (a row of its own, offered only when the room draws nothing of it);
#              outdoors: the placed item list draws it (every row of the 3 x 3 cells), an entity of a frame map carries
#              it, or a CHIM world piece places it (a store of frames: the base world, Solstheim's, Mournhold's);
#   aimable    drawn, and its item row ('I') is in the use table the engine reads (id1/areas.awa, else focus.awf)
#              within the place's FOCUS_ROWS (a room alone; outdoors the 3 x 3 cells in focus_load order);
#   takeable   aimable, its row takes it (or reads it, a book: the read screen takes it), and every drawn copy goes
#              with the take: an entity and a room placement by reference, a placed list row by the world change list,
#              a CHIM world piece only through its hide row ('P', id1/areas.awa effect links, tools/effect_links.py);
#   owner kept the row says owned exactly when the original does (the reference's owner ANAM, else its faction CNAM:
#              OpenMW 0.51 mechanicsmanagerimp itemTaken), and its area names that owner.
# ======================================================================================================================

WORLD_SCHEMA = 'amiwind-world-item-census-1'
WORLD_FILE = 'world-item-census.json'
IMAGE_ID1 = 'image/boot/id1'
# the engine's tables (aw_inventory.c FOCUS_ROWS; tests/test_room_item_census.py reads them against the source)
FOCUS_ROWS = 1536
# the engine's rules (aw_inventory.c; tests/test_room_item_census.py reads each against the source):
# PLACED_INDOORS_UNDRAWN_ONLY: indoors a placed list row is drawn only when the room draws nothing of the item (its row's
# edict flag: no entity carries it and the CHIM room record does not place it); outdoors every row is offered.
PLACED_INDOORS_UNDRAWN_ONLY = True
# PIECES_HIDDEN_BY_ROW: a CHIM world piece goes with a take or a Disable only through its 'P' effect link row.
PIECES_HIDDEN_BY_ROW = True
# A 'P' row's aux bit 0 (tools/effect_links.py PLACE_LISTED, OUTDOOR-ITEM-CHIM-COPY-STAYS-69): the placed item list draws
# the reference, and the engine hides the piece whenever its area is applied: the piece is not a drawn copy.
PLACE_LISTED = 1
WORLD_CATEGORIES = ('weapon', 'armour', 'clothing', 'book', 'potion', 'ingredient', 'misc', 'gold', 'key', 'apparatus',
                    'lockpick', 'probe', 'repair item', 'light')
STATE_COLUMNS = ('placed', 'in_build', 'drawn', 'aimable', 'takeable', 'owned', 'owner_kept')
MISC_KEY = 1              # MCDT flags: a key
MERGED_SHIFT, STABLE_SHIFT = 22, 20


def stable_of_merged(number):
    """The stable reference id of a placement's source number in the merged master's form (2^22 x master + number;
    the base game's numbers are both forms; a cut piece's high bits left out): tools/container_census.py's rule."""
    n = int(number) & 0xFFFFFF
    return (n >> MERGED_SHIFT) << STABLE_SHIFT | (n & ((1 << MERGED_SHIFT) - 1))


def item_records(raw):
    """{folded id: {'tag', 'category', 'name', 'script'}} of every record of RAW (a master's bytes, merged or not) that
    a player can take in the original: the TAKEABLE kinds, and a light whose LHDT says it can be carried (a fixed
    light is scenery). A misc item is split into gold (gold_*) and keys (MCDT key flag), as the items index counts."""
    from mwad.esm import first, records, string, subrecords
    out = {}
    for tag, flags, payload in records(raw):
        if tag not in TAKEABLE and tag != 'LIGH':
            continue
        fields = list(subrecords(payload))
        if flags & 0x20 or any(k == 'DELE' for k, _ in fields) or not first(fields, 'NAME'):
            continue
        ident = string(first(fields, 'NAME'), 'NAME', errors='replace').casefold()
        if tag == 'LIGH':
            data = first(fields, 'LHDT')
            if len(data) < 24 or not struct.unpack_from('<i', data, 20)[0] & LIGHT_CARRY:
                out.pop(ident, None)
                continue
        category = CATEGORY[tag]
        if tag == 'MISC':
            data = first(fields, 'MCDT')
            if ident.startswith('gold_'):
                category = 'gold'
            elif len(data) >= 12 and struct.unpack_from('<i', data, 8)[0] & MISC_KEY:
                category = 'key'
        name = string(first(fields, 'FNAM'), 'FNAM', errors='replace').strip() if first(fields, 'FNAM') else ''
        script = string(first(fields, 'SCRI'), 'SCRI', errors='replace').casefold() if first(fields, 'SCRI') else ''
        out[ident] = {'tag': tag, 'category': category, 'name': name, 'script': script}
    return out


def reference_owner(ref):
    """(owner id folded, 1 when a faction owns it) of a placed reference (its ANAM, else its CNAM), or None."""
    from mwad.esm import string
    for key, faction in (('ANAM', 0), ('CNAM', 1)):
        if ref.get(key):
            ident = string(ref[key], key, errors='replace').strip().casefold()
            if ident:
                return ident, faction
    return None


def world_places(data_files, masters=None, places=None):
    """(masters, places) of every placed reference of MASTERS (default: every game master in DATA_FILES) whose record
    a player can take (item_records), interior and exterior. PLACES: the districts the build presents as exterior
    cells (tools/presented_exterior.py build_places; MOURNHOLD-EXTERIOR-CELLS-66): their items are keyed by their
    block's cells at the moved positions, as the use table and the placed list key them. Each place: reference (the
    stable id), master, cell, grid, interior, presented, key (the use table's: a room number or an exterior key; None
    when the cell has neither), id, name, category, tag, position (game units), owner, script."""
    from cell_numbers import load_table, room_numbers
    from container_census import present_masters
    from mwad.masters import master_bytes
    from mwad.paths import resolve_data_files
    import prepare_focus as pf
    from ref_identity import RefIdentityError, split, stable_ref
    data = resolve_data_files(Path(data_files))
    masters = tuple(masters) if masters else present_masters(data)
    raw = master_bytes(data, masters)
    numbers = room_numbers(load_table(data)[0])
    items = item_records(raw)
    presented = {name.casefold() for name in (places or {})}
    out = []
    for cell, interior, grid, _region, refs in pf.cells_presented(raw, places):
        for ref in refs:
            if 'DELE' in ref or 'NAME' not in ref:
                continue
            ident = ref['NAME'].split(b'\0')[0].decode('cp1252', 'replace').casefold()
            record = items.get(ident)
            if record is None:
                continue
            try:
                reference = stable_ref(pf.MASTER, ref['number'])
            except RefIdentityError:
                continue
            if interior:
                key = numbers.get(cell.casefold()) if cell else None
            else:
                key = pf.exterior_key(*grid) if all(abs(g) < pf.GRID_BIAS for g in grid) else None
            data_ok = len(ref.get('DATA', b'')) == 24
            out.append({'reference': reference, 'master': split(reference)[0], 'cell': cell or '',
                        'grid': None if interior else [int(grid[0]), int(grid[1])], 'interior': bool(interior),
                        'presented': (cell or '').casefold() in presented, 'key': key, 'id': ident,
                        'name': record['name'], 'category': record['category'], 'tag': record['tag'],
                        'position': [round(v, 2) for v in struct.unpack_from('<3f', ref['DATA'])] if data_ok else None,
                        'owner': reference_owner(ref), 'script': record['script']})
    return masters, out


# ---------------------------------------------------------------------------------------------------- the run

def read_areas(raw):
    """id1/areas.awa -> ({area key: [row bytes]}, {area key: {reference: (owner id, faction)}}, {area key: {reference
    of a 'P' effect link row: its aux bits, or-ed}}): the use table the engine reads (tools/prepare_area_tables.py
    layout), each area's owners, and its hide rows (tools/effect_links.py; aux PLACE_LISTED: the piece is gone for
    good, the placed list draws the item)."""
    import effect_links
    if raw[:4] != b'AWA1':
        raise ValueError('areas.awa is not AWA1')
    n = struct.unpack_from('<I', raw, 4)[0]
    rows, owners, hides = {}, {}, {}
    for i in range(n):
        key, offset, size = struct.unpack_from('<III', raw, 24 + 12 * i)
        rec = raw[offset:offset + size]
        if rec[:4] != b'AWB1':
            continue
        nrows, nowners, nowned = struct.unpack_from('<3H', rec, 4)
        at = 16
        rows[key] = [rec[at + j * 96:at + (j + 1) * 96] for j in range(nrows)]
        at += nrows * 96
        ids = [rec[at + 32 * j:at + 32 * (j + 1)].split(b'\0', 1)[0].decode('ascii', 'replace') for j in range(nowners)]
        at += nowners * 32
        own = owners[key] = {}
        for j in range(nowned):
            reference, index, faction = struct.unpack_from('<IBB', rec, at + 8 * j)
            if index < len(ids):
                own[reference] = (ids[index], faction & 1)
        for kind, aux, _k, ref in effect_links.read_section(rec):
            if kind == effect_links.KIND_PLACE:
                hides.setdefault(key, {})[ref] = hides.get(key, {}).get(ref, 0) | aux
    return rows, owners, hides


def read_focus_table(raw):
    """focus.awf -> ({key: [row bytes]}, {key: {reference: (owner id, faction)}}, {}), the shape read_areas gives (an
    image without area tables; owners from the one owners list)."""
    import prepare_area_tables as pat
    rooms, owners, _containers, _refs, _levelled = pat.read_focus(raw)
    by_key = {}
    for key, rows in rooms.items():
        refs = {struct.unpack_from('<I', r, 4)[0] for r in rows}
        by_key[key] = {r: owners[r] for r in refs if r in owners}
    return rooms, by_key, {}


def read_placed_rows(raw):
    """{key: {reference: (x, y, z)}} of a placed item list (AWP1)."""
    from prepare_item_models import read_placed
    return {key: {row[0]: row[3] for row in rows} for key, rows in read_placed(raw).items()}


def scan_maps(maps_dir):
    """({room number: {'map', 'kind' ('chim' | 'bsp'), 'record' (the CHIM room's store and room, or None),
    'entities': {reference: [classes]}}}, {reference: [(frame map, class)]}): every room map of MAPS_DIR by its
    _aw_cell_int, and every entity of the other maps (the frame maps outdoors) that carries an aw_ref."""
    from chim.frame_map import entities
    from map_files import LEGACY_EXT, MAP_EXTS, ROOM_KEY
    rooms, outdoors = {}, {}
    for path in sorted(Path(maps_dir).iterdir()) if Path(maps_dir).is_dir() else ():
        if path.suffix not in MAP_EXTS:
            continue
        try:
            ents = entities(path.read_bytes())
        except (ValueError, struct.error):
            continue
        world = ents[0] if ents else {}
        number = str(world.get('_aw_cell_int', ''))
        held = {}
        for e in ents[1:]:
            value = e.get('aw_ref', '')
            try:
                ref = stable_of_merged(int(float(value)))     # a merged master's number names its owning master
            except ValueError:
                continue
            if ref > 0:
                held.setdefault(ref, []).append(e.get('classname', '?'))
        if number.isdigit() and int(number) > 0:
            record = (world.get('_chim_world') or 'chim', world[ROOM_KEY]) if ROOM_KEY in world else None
            room = rooms.setdefault(int(number), {'map': path.name, 'kind': 'bsp' if path.suffix == LEGACY_EXT and
                                                  record is None else 'chim', 'record': record, 'entities': {}})
            for ref, classes in held.items():
                room['entities'].setdefault(ref, []).extend(classes)
            continue
        for ref, classes in held.items():
            outdoors.setdefault(ref, []).extend((path.stem, c) for c in classes)
    return rooms, outdoors


def room_placements(rooms, stores):
    """{room number: {stable ids the CHIM room record places}} of ROOMS (scan_maps), each record read from the first
    folder of STORES ({store name: folder holding rooms/<room>.crm}) that holds it; a room whose record is found in
    none is left out (its placements unknown: counted as not drawn by the room)."""
    from chim.room_records import read_room_record
    out = {}
    for number, room in rooms.items():
        if not room['record']:
            continue
        store, name = room['record']
        path = Path(stores.get(store, '')) / 'rooms' / (name + '.crm') if stores.get(store) else None
        if path is None or not path.is_file():
            continue
        out[number] = {stable_of_merged(p['ref']) for p in read_room_record(path.read_bytes())['placements']}
    return out


def world_pieces(world):
    """{stable ids} of every placement (every cut piece's source) of a loaded CHIM world (chim.frame_map.load /
    chim.validate.load_world's frames)."""
    from chim.cut import source_ref
    out = set()
    for _, _, chunks in world['frames']:
        for c in chunks:
            for r in c['owned']:
                out.add(stable_of_merged(source_ref(r['ref'])))
    return out


def load_pieces(world_dirs, jobs=None):
    """world_pieces of every CHIM world folder of WORLD_DIRS (a stage folder holding chim/world.cwi), each read on the
    worker pool (chim.validate.load_world with JOBS) and freed before the next."""
    from build_jobs import resolve_jobs
    from chim import placed, placement_light, reach  # noqa: F401 (the world formats' headers)
    from chim.validate import Failures, load_world
    out = set()
    for folder in world_dirs:
        fails = Failures()
        frames = load_world(folder, fails, jobs=resolve_jobs(jobs))[5]
        if fails:
            raise ValueError('CHIM world %s does not load: %s' % (folder, '; '.join(fails[:3])))
        out |= world_pieces({'frames': frames})
    return out


def image_step_args(run):
    """The image step's own arguments in RUN's build state (tools/build.py steps): {option: [values]}."""
    state = json.loads((Path(run) / 'build-state.json').read_text(encoding='utf-8'))
    for step in state.get('steps') or ():
        command = step.get('command') if isinstance(step, dict) else None
        at = [i for i, v in enumerate(command or ()) if isinstance(v, str) and v.endswith('build_aga.py')]
        if not at or command[at[0] + 1:at[0] + 2] != ['image']:
            continue
        out = {}
        for i, v in enumerate(command):
            if isinstance(v, str) and v.startswith('--') and i + 1 < len(command):
                nxt = command[i + 1]
                if isinstance(nxt, str) and not nxt.startswith('--'):
                    out.setdefault(v, []).append(nxt)
        return out
    return {}


def run_sources(run, pieces=None, jobs=None, log=None):
    """Everything judge_world reads of a finished build RUN: the use table, the owners and hide rows (areas.awa, else
    focus.awf), the placed list, the room maps and their CHIM room records, the frame maps' entities, and the CHIM world
    pieces (PIECES: given, e.g. by the image step that already loaded the worlds; else read from the run's stores)."""
    run = Path(run)
    id1 = run / IMAGE_ID1
    args = image_step_args(run)
    if (id1 / 'areas.awa').is_file():
        rows, owners, hides = read_areas((id1 / 'areas.awa').read_bytes())
        table = 'areas.awa'
    else:
        rows, owners, hides = read_focus_table((id1 / 'focus.awf').read_bytes())
        table = 'focus.awf'
    placed = read_placed_rows((id1 / 'progs/items/placed.awp').read_bytes()) \
        if (id1 / 'progs/items/placed.awp').is_file() else {}
    rooms, outdoors = scan_maps(id1 / 'maps')
    stores = {}
    for folder in (args.get('--chim-interiors') or []) + [str(run / 'chim-interiors')]:
        for store in (Path(folder).iterdir() if Path(folder).is_dir() else ()):
            if (store / 'rooms').is_dir():
                stores.setdefault(store.name, str(store))
    for store in (id1.iterdir() if id1.is_dir() else ()):
        if (store / 'rooms').is_dir():
            stores.setdefault(store.name, str(store))
    if pieces is None:
        worlds = [v for v in args.get('--chim-world') or [str(run / 'chim-world')] if (Path(v) / 'chim').is_dir()]
        worlds += [v.split('=', 1)[1] for v in args.get('--chim-layer-world') or () if '=' in v]
        worlds += list(args.get('--chim-sol-world') or ())
        if log:
            log('reading the CHIM world pieces of %d stores: %s' % (len(worlds), ', '.join(Path(w).name for w in worlds)))
        pieces = load_pieces([w for w in worlds if (Path(w) / 'chim' / 'world.cwi').is_file()], jobs)
    built = set()
    for key_rows in rows.values():
        for row in key_rows:
            ref = struct.unpack_from('<I', row, 4)[0]
            if 0 < ref < 0x800000:
                built.add(ref >> STABLE_SHIFT)
    return {'rows': rows, 'owners': owners, 'hides': hides, 'placed': placed, 'rooms': rooms,
            'room_placements': room_placements(rooms, stores), 'outdoors': outdoors, 'pieces': pieces,
            'masters_built': built, 'table': table, 'stores': sorted(stores), 'args': args}


def window_keys(key):
    """The keys the engine reads for the place KEY: a room alone; an exterior cell with its eight neighbours, in
    focus_load's order (dx outer, dy inner)."""
    import prepare_focus as pf
    if key < 0x80000000:
        return [key]
    gx, gy = (key >> 12 & 0xFFF) - pf.GRID_BIAS, (key & 0xFFF) - pf.GRID_BIAS
    return [pf.exterior_key(gx + dx, gy + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]


def item_slots(rows, key):
    """{reference: (row slot, row bytes)} of the item rows ('I') the engine keeps for the place KEY: every row it accepts
    (tools/container_census.py row_accepted) counts toward FOCUS_ROWS, in focus_load's order."""
    from container_census import row_accepted
    out, n = {}, 0
    for k in window_keys(key):
        for row in rows.get(k, ()):
            if not row_accepted(row)[0]:
                continue
            if n < FOCUS_ROWS and row[0] == ord('I'):
                out.setdefault(struct.unpack_from('<I', row, 4)[0], (n, row))
            n += 1
    return out


def judge_world(places, sources):
    """Every place gets 'build' {in_build, drawn, aimable, takeable, owner_kept, copies, aim, gaps} against SOURCES
    (run_sources), by the engine's rules (the module text above)."""
    import prepare_focus as pf
    from ref_identity import file_index
    slots_cache = {}
    rows, placed, rooms, outdoors = sources['rows'], sources['placed'], sources['rooms'], sources['outdoors']
    room_placed, pieces = sources['room_placements'], sources['pieces']
    hides = {}
    for area in sources['hides'].values():
        for ref, aux in (area.items() if isinstance(area, dict) else ((r, 0) for r in area)):
            hides[ref] = hides.get(ref, 0) | aux
    for p in places:
        b = p['build'] = {'in_build': False, 'drawn': False, 'aimable': False, 'takeable': False,
                          'owner_kept': False, 'copies': [], 'aim': None, 'gaps': []}
        gaps, ref, key = b['gaps'], p['reference'], p['key']
        if file_index(p['master']) not in sources['masters_built']:
            gaps.append('not in this build: %s is not one of its masters' % p['master'])
            continue
        if key is None:
            gaps.append('no place key: %s' % ('the cell is not in the room number table' if p['interior'] else
                                              'the exterior cell lies outside the key grid'))
            continue
        if key not in slots_cache:
            slots_cache[key] = item_slots(rows, key)
        found = slots_cache[key].get(ref)
        row = found[1] if found else None
        in_placed = ref in placed.get(key, {})
        copies = b['copies']
        if key < 0x80000000:
            room = rooms.get(key)
            if room is None:
                gaps.append('not built: its room map is not in the image')
                continue
            b['in_build'] = True
            live = bool(room['entities'].get(ref))
            in_room = ref in room_placed.get(key, ())
            if live:
                copies.append('entity')
            if in_room:
                copies.append('room placement')
            # the placed row is offered only when the room draws nothing of the item and its use row exists
            if in_placed and row is not None and not live and not in_room:
                copies.append('placed list')
        else:
            b['in_build'] = True
            live = bool(outdoors.get(ref))
            if live:
                copies.append('entity')
            # a piece with a PLACE_LISTED row is gone whenever its area is applied (aw_inventory.c AW_AreaEffectsApply)
            if ref in pieces and not hides.get(ref, 0) & PLACE_LISTED:
                copies.append('CHIM piece')
            if in_placed and row is not None and not live:
                copies.append('placed list')
            elif ref in pieces and hides.get(ref, 0) & PLACE_LISTED:
                gaps.append('not drawn: its CHIM piece is hidden for the placed list, which does not draw it')
        b['drawn'] = bool(copies)
        if not copies and any(g.startswith('not drawn') for g in gaps):
            pass
        elif not copies:
            if in_placed and row is None:
                gaps.append('not drawn: on the placed list, but it has no use-table row')
            elif key < 0x80000000 and rooms[key]['kind'] == 'bsp':
                gaps.append('not drawn: the compiled room map neither carries it nor lists it')
            elif key < 0x80000000:
                gaps.append('not drawn: the room neither places it nor lists it on the placed list')
            else:
                gaps.append('not drawn: no placed list row, frame map entity or CHIM piece')
        elif 'CHIM piece' in copies and 'placed list' in copies:
            gaps.append('drawn twice outdoors: the placed list and a CHIM piece at the same spot')
        if row is None:
            gaps.append('no use-table row: %s' % ('the record has no name' if not p['name'] else
                                                 'past the place\'s %d rows or left out' % FOCUS_ROWS))
        if row is not None and copies:
            b['aimable'] = True
            b['aim'] = ('the entity' if 'entity' in copies else 'the room placement' if 'room placement' in copies
                        else 'the placed model' if 'placed list' in copies else 'its point only (a CHIM piece)')
            action = row[2] & 3
            if action not in (pf.ACT_TAKE, pf.ACT_READ):
                gaps.append('its row does not take it (action %d)' % action)
            elif 'CHIM piece' in copies and ref not in hides:
                gaps.append('taken, but its CHIM piece stays drawn: no hide row')
            else:
                b['takeable'] = True
        if row is not None:
            want = p['owner']
            owned_row = bool(row[1]) and bool(row[2] & pf.ACT_OWNED)
            listed = sources['owners'].get(key, {}).get(ref)
            if want is None:
                b['owner_kept'] = not row[1] and not row[2] & pf.ACT_OWNED
                if not b['owner_kept']:
                    gaps.append('owned in the row, not in the original')
            elif not owned_row:
                gaps.append('owned in the original, free to take in the row: taking it is not theft')
            elif listed is None or listed[0] != want[0] or listed[1] != want[1]:
                gaps.append('owned, but its area does not name whom it is stolen from (%s)'
                            % ('none' if listed is None else 'another'))
            else:
                b['owner_kept'] = True
        if in_placed and p['position'] is not None and 'placed list' in copies:
            at = placed[key][ref]
            if max(abs(a - b_) for a, b_ in zip(at, p['position'])) > 1.0:
                gaps.append('the placed list draws it away from its place')
    return {'table': sources['table'], 'stores': sources['stores'], 'rooms': len(rooms),
            'rooms_with_records': len(room_placed), 'pieces': len(pieces), 'placed_keys': len(placed),
            'hide_rows': len(hides), 'masters_built': sorted(sources['masters_built'])}


def world_cell_name(p):
    if p['interior'] or not p['grid']:
        return p['cell']
    return '%s (%d,%d)' % (p['cell'], *p['grid']) if p['cell'] else '%d,%d' % tuple(p['grid'])


def gap_reason(text):
    """A gap's text with its numbers and names taken out: the tally's reason."""
    text = re.sub(r'action \d+', 'action N', text)
    return re.sub(r'(Morrowind|Tribunal|Bloodmoon)\.esm', 'M.esm', text)


def world_tally(masters, places, facts=None, run=None):
    """The counts: per master, side and category the STATE_COLUMNS, the gaps by reason (count, cells, examples)."""
    def empty():
        return {c: 0 for c in STATE_COLUMNS}
    totals, reasons = {}, {}
    for p in places:
        side = 'interior' if p['interior'] and not p['presented'] else 'exterior'
        b = p.get('build') or {}
        for bucket in (totals.setdefault('all', {}).setdefault(side, {}).setdefault('all', empty()),
                       totals.setdefault('all', {}).setdefault(side, {}).setdefault(p['category'], empty()),
                       totals.setdefault(p['master'], {}).setdefault(side, {}).setdefault('all', empty()),
                       totals.setdefault(p['master'], {}).setdefault(side, {}).setdefault(p['category'], empty())):
            bucket['placed'] += 1
            bucket['owned'] += p['owner'] is not None
            for c in ('in_build', 'drawn', 'aimable', 'takeable'):
                bucket[c] += bool(b.get(c))
            bucket['owner_kept'] += bool(b.get('owner_kept')) and p['owner'] is not None
        for g in b.get('gaps', ()):
            r = reasons.setdefault(gap_reason(g), {'items': 0, 'cells': set(), 'by_master': {}, 'examples': []})
            r['items'] += 1
            r['cells'].add(world_cell_name(p))
            r['by_master'][p['master']] = r['by_master'].get(p['master'], 0) + 1
            if len(r['examples']) < 12:
                r['examples'].append('%s: %s `%s` (reference %d)' % (world_cell_name(p), p['name'] or '?', p['id'],
                                                                    p['reference']))
    out = {'schema': WORLD_SCHEMA, 'masters': list(masters), 'totals': totals,
           'gaps': {r: {'items': v['items'], 'cells': len(v['cells']), 'by_master': v['by_master'],
                        'examples': v['examples']}
                    for r, v in sorted(reasons.items(), key=lambda kv: -kv[1]['items'])}}
    if run is not None:
        out['run'] = dict(facts or {}, name=Path(run).name)
    return out


def world_failures(places):
    """[{reference, master, cell, id, name, category, position, gaps}] of every place with a gap."""
    return [{'reference': p['reference'], 'master': p['master'], 'cell': world_cell_name(p), 'id': p['id'],
             'name': p['name'], 'category': p['category'], 'position': p['position'],
             'copies': (p.get('build') or {}).get('copies', []), 'gaps': (p.get('build') or {}).get('gaps', [])}
            for p in places if (p.get('build') or {}).get('gaps')]


def world_lines(t):
    out = []
    for master, sides in t['totals'].items():
        for side, cats in sides.items():
            v = cats['all']
            out.append('%-14s %-8s placed %6d: in build %6d, drawn %6d, aimable %6d, takeable %6d; owned %5d, owner '
                       'kept %5d' % (master, side, v['placed'], v['in_build'], v['drawn'], v['aimable'], v['takeable'],
                                     v['owned'], v['owner_kept']))
    for reason, v in t['gaps'].items():
        out.append('  gap: %6d items in %4d cells: %s' % (v['items'], v['cells'], reason))
    return out


def world_md(t, title='World item census'):
    """The tables as Markdown: one table per master (rows: side and category), then the gaps with examples."""
    lines = ['# %s' % title, '']
    if t.get('run'):
        lines += ['Build `%s`, counted with tools/room_item_census.py world (use table %s).' % (
            t['run'].get('name'), t['run'].get('table')), '']
    lines += ['Columns: placed = the references the masters place; in build = its master and its room are in the '
              'image; drawn = an entity, a room placement, the placed list or a CHIM piece draws it; aimable = drawn '
              'and its use-table row is read; takeable = aimable, its row takes it and every drawn copy goes with the '
              'take; owned = the original says taking it is theft; owner kept = the row says so and names whom it is '
              'stolen from.',
              '']
    cols = STATE_COLUMNS
    for master, sides in t['totals'].items():
        lines += ['## %s' % ('All masters' if master == 'all' else master), '',
                  '| side | category | ' + ' | '.join(cols) + ' |', '|---|---|' + '---|' * len(cols)]
        for side, cats in sides.items():
            for cat in ['all'] + [c for c in WORLD_CATEGORIES if c in cats]:
                lines.append('| %s | %s | %s |' % (side, cat, ' | '.join(str(cats[cat][c]) for c in cols)))
        lines.append('')
    lines += ['## Gaps', '']
    for reason, v in t['gaps'].items():
        lines += ['### %s' % reason, '', '%d items in %d cells (%s).' % (
            v['items'], v['cells'], ', '.join('%s %d' % kv for kv in sorted(v['by_master'].items()))), '']
        lines += ['- ' + e for e in v['examples']] + ['']
    return '\n'.join(lines) + '\n'


# The gaps the committed measurement may hold (docs/performance/WORLD_ITEMS.json), each with the register entries that
# hold its cause and the most items it may count; tests/test_room_item_census.py fails on a gap reason not here or past
# its count, so an item that stops being drawn, aimed at or taken fails the gate. Lowered as fixes land, never raised
# without its entry (a ratchet). The counts of the v0.0.69-dev5 run (the first world census, 27 November 2026).
KNOWN_GAPS = {
    # outdoors the placed list and a CHIM piece both draw the item; the piece has no hide row (the fix: tools/effect_links.py
    # PLACE_LISTED rows; 0 from the first build with it)
    'drawn twice outdoors: the placed list and a CHIM piece at the same spot': ('OUTDOOR-ITEM-CHIM-COPY-STAYS-69', 474),
    'taken, but its CHIM piece stays drawn: no hide row': ('OUTDOOR-ITEM-CHIM-COPY-STAYS-69', 464),
    # the burned-out torches of Old Mournhold: Temple Sewers West: carriable lights with no name, no use row
    'no use-table row: the record has no name': ('ITEM-NAMELESS-NOT-TAKEN-69', 10),
    # Seyda Neen's eight travel lanterns: the town's frame defers its lights, the placed list leaves carried lights out
    'not drawn: no placed list row, frame map entity or CHIM piece': ('SEYDA-LANTERNS-MISSING-31', 8),
}


def world_verdict(t, known=None):
    """The problems of the count T: a gap reason KNOWN does not list, or a gap past its count. [] when it holds."""
    known = KNOWN_GAPS if known is None else known
    out = []
    for reason, v in t.get('gaps', {}).items():
        if reason not in known:
            out.append('%d items: %s (no register entry allows this gap)' % (v['items'], reason))
        elif v['items'] > known[reason][1]:
            out.append('%d items: %s (%s allows %d)' % (v['items'], reason, *known[reason]))
    return out


def world_summary(t, examples=None):
    """The public measurement: the schema, the masters, the totals and the gaps (examples kept, at most EXAMPLES a
    gap when given: game record ids and cells only, no machine detail)."""
    out = {k: t[k] for k in ('schema', 'masters', 'totals', 'gaps', 'run') if k in t}
    if examples is not None:
        out['gaps'] = {r: dict(v, examples=v['examples'][:examples]) for r, v in out['gaps'].items()}
    return out


MEASUREMENT_WHAT = ('Every placed item of the game masters that a player can take or steal, against what a build '
                    'makes of it (tools/room_item_census.py world); docs/performance/WORLD_ITEMS.md explains the '
                    'columns. The newest measurement is last; tests/test_room_item_census.py reads it.')


def add_measurement(path, t, examples=4):
    """PATH (docs/performance/WORLD_ITEMS.json): {'what', 'measurements': [...]} with the summary of T appended (a
    measurement of the same run replaces its earlier one)."""
    path = Path(path)
    data = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {'what': MEASUREMENT_WHAT,
                                                                                 'measurements': []}
    new = world_summary(t, examples)
    name = (new.get('run') or {}).get('name')
    data['measurements'] = [m for m in data['measurements'] if not name or (m.get('run') or {}).get('name') != name]
    data['measurements'].append(new)
    data['what'] = MEASUREMENT_WHAT
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    return data


def world_build_step(run, data_files, log=print, jobs=None):
    """The builder's world item count after a passed image (tools/build.py): RUN/world-item-census.json (the summary)
    and RUN/world-item-census-full.json (every place with a gap), a line per master and side, the verdict against
    KNOWN_GAPS. Returns the problems ([] holds), None when skipped or when the count could not be made (said)."""
    import time
    started = time.monotonic()
    try:
        if not (Path(run) / IMAGE_ID1 / 'focus.awf').is_file():
            log('World item count: skipped (no use table in this run)')
            return None
        log('World item count: started (the masters, the use table, the maps, the CHIM rooms and world pieces)')
        args = image_step_args(run)
        import prepare_focus as pf
        places = pf.presented_places((args.get('--presented-receipt') or [None])[0],
                                     (args.get('--presented-cells') or [''])[0])
        masters, items = world_places(data_files, places=places)
        facts = judge_world(items, run_sources(run, jobs=jobs, log=lambda m: log('World item count: ' + m)))
        t = world_tally(masters, items, facts, run)
        (Path(run) / WORLD_FILE).write_text(json.dumps(world_summary(t), indent=1, sort_keys=True) + '\n',
                                            encoding='utf-8', newline='\n')
        (Path(run) / WORLD_FILE.replace('.json', '-full.json')).write_text(
            json.dumps(dict(t, failures=world_failures(items)), sort_keys=True) + '\n', encoding='utf-8',
            newline='\n')
        for line in world_lines(t):
            log('World item count: ' + line.strip())
        problems = world_verdict(t)
        for line in problems:
            log('World item count: WARNING: ' + line)
        log('World item count: %s (took %.1f s)' % ('holds' if not problems else '%d problems' % len(problems),
                                                    time.monotonic() - started))
        return problems
    except Exception as exc:  # noqa: BLE001 - a measurement after a passed image
        log('World item count: not made: %s: %s' % (type(exc).__name__, exc))
        return None


def world_main(argv):
    import time
    p = argparse.ArgumentParser(prog='room_item_census.py world',
                                description='The world item census of a finished build (WORLD-OBJECT-PLACEMENT-59).')
    p.add_argument('--data-files', required=True, type=Path)
    p.add_argument('--run', required=True, type=Path, help='a finished build run folder')
    p.add_argument('--masters', help='comma list of game masters (default: every one present in the data files)')
    p.add_argument('--jobs', type=int, default=None, help='workers for reading the CHIM worlds')
    p.add_argument('--out', type=Path, help='the full table (JSON: the tally and every place with a gap)')
    p.add_argument('--summary', type=Path, help='the public measurement (JSON)')
    p.add_argument('--md', type=Path, help='the tables (Markdown)')
    p.add_argument('--measurement', type=Path, help='the public measurement file the summary is appended to '
                                                   '(docs/performance/WORLD_ITEMS.json)')
    p.add_argument('--check', action='store_true', help='exit 1 when the verdict against KNOWN_GAPS fails')
    p.add_argument('--show', default='', help='comma list of stable references: print each one\'s place and answers')
    p.add_argument('--show-ids', default='', help='a regular expression: print the place and answers of every item '
                                                  'whose record id matches it')
    a = p.parse_args(argv)
    started = time.monotonic()
    print('=== PHASE 1/3: reading the masters ===', flush=True)
    args = image_step_args(a.run)
    import prepare_focus as pf
    places = pf.presented_places((args.get('--presented-receipt') or [None])[0],
                                 (args.get('--presented-cells') or [''])[0])
    masters, items = world_places(a.data_files, a.masters.split(',') if a.masters else None, places)
    print('  %d placed takeable items in %s (%.1f s)' % (len(items), ', '.join(masters), time.monotonic() - started),
          flush=True)
    print('=== PHASE 2/3: reading the run and judging every item ===', flush=True)
    sources = run_sources(a.run, jobs=a.jobs, log=lambda m: print('  ' + m, flush=True))
    facts = judge_world(items, sources)
    print('  run read and judged (%.1f s): %d rooms (%d with CHIM records), %d CHIM pieces, %d hide rows' % (
        time.monotonic() - started, facts['rooms'], facts['rooms_with_records'], facts['pieces'], facts['hide_rows']),
        flush=True)
    for wanted in [int(v) for v in a.show.split(',') if v.strip()]:
        for item in [i for i in items if i['reference'] == wanted] or [{'reference': wanted, 'build': 'not a placed '
                                                                         'takeable item of these masters'}]:
            print('  show %s' % json.dumps(item, sort_keys=True), flush=True)
    if a.show_ids:
        pattern = re.compile(a.show_ids, re.I)
        for item in items:
            if pattern.search(item['id']):
                b = item.get('build') or {}
                print('  show-id %s | %s | %s `%s` ref %d %s at %s | %s | %s%s' % (
                    item['master'], world_cell_name(item), item['name'], item['id'], item['reference'],
                    item['category'], item['position'], '+'.join(b.get('copies', [])) or 'not drawn',
                    'takeable' if b.get('takeable') else 'NOT takeable',
                    '; ' + '; '.join(b['gaps']) if b.get('gaps') else ''), flush=True)
    print('=== PHASE 3/3: tallying ===', flush=True)
    t = world_tally(masters, items, facts, a.run)
    if a.out:
        a.out.write_text(json.dumps(dict(t, failures=world_failures(items)), indent=0, sort_keys=True) + '\n',
                         encoding='utf-8', newline='\n')
    if a.summary:
        a.summary.write_text(json.dumps(world_summary(t), indent=1, sort_keys=True) + '\n', encoding='utf-8',
                             newline='\n')
    if a.md:
        a.md.write_text(world_md(t), encoding='utf-8', newline='\n')
    if a.measurement:
        add_measurement(a.measurement, t)
    print('\n'.join(world_lines(t)))
    problems = world_verdict(t)
    print('verdict: %s' % ('holds (every gap has its register entry and count)' if not problems else
                           '%d problems:\n  ' % len(problems) + '\n  '.join(problems)))
    print('took %.1f s' % (time.monotonic() - started), flush=True)
    return 1 if a.check and problems else 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == 'world':
        return world_main(argv[1:])
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data-files', type=Path, help='the game data folder (its base master is read)')
    p.add_argument('--master', type=Path, help='the master file itself, in place of --data-files')
    p.add_argument('--cell', required=True)
    p.add_argument('--map', type=Path, required=True)
    p.add_argument('--report', type=Path, help="the room's conversion report: its groups' references are the bake")
    p.add_argument('--placed', type=Path, help='the placed item list (progs/items/placed.awp) the image carries')
    p.add_argument('--out', type=Path)
    p.add_argument('--md', type=Path)
    p.add_argument('--check', action='store_true')
    a = p.parse_args(argv)
    from mwad.interior import read_interior
    if a.master:
        master = a.master
    elif a.data_files:
        from mwad.masters import master_path
        from mwad.paths import resolve_data_files
        master = master_path(resolve_data_files(a.data_files))
    else:
        p.error('--data-files or --master')
    cell = read_interior(master, a.cell)
    baked = set()
    if a.report:
        report = json.loads(a.report.read_text(encoding='utf-8'))
        for group in (report.get('groups') or {}).values():
            baked.update(int(n) for n in group.get('references', ()))
    raw = a.map.read_bytes()
    room = map_room(raw)
    placed = placed_references(a.placed.read_bytes(), room) if a.placed and room else set()
    result = census(cell['refs'], map_references(raw), baked, placed=placed)
    result.update(cell=cell['name'], map=a.map.name, room=room, master_sha256=cell.get('master_sha256'))
    if a.out:
        a.out.write_text(json.dumps(result, indent=1) + '\n', encoding='utf-8', newline='\n')
    md = render_md(cell['name'], result)
    if a.md:
        a.md.write_text(md, encoding='utf-8', newline='\n')
    print(md, end='')
    if a.check and result['problems']:
        print('ROOM ITEM CENSUS: %d problem(s) in %s' % (len(result['problems']), cell['name']))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
