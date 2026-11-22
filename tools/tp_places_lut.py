#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The settlements table (AWTP1, id1/tp-places.lut) for `dbg tp` with no argument (TP-PICKER-57): every named place
of the island (towns, villages, camps, forts, strongholds, ruins) with the point you arrive at, compiled at build
time so the engine only reads it while its list box is open (nothing resident; engine/aga/src/aw_tpplaces.c).

Where the names come from: the game's own exterior CELL names (the names the world map shows: OpenMW 0.51
apps/openmw/mwgui/mapwindow.cpp marks every exterior cell with a name). Cells of one name (a town over several
cells) are one place.

Where you arrive, in this order (our own code; the first two as OpenMW's `coc` finds a place,
apps/openmw/mwworld/worldimp.cpp findExteriorPosition):
1. a CocMarkerHeading in one of the place's cells (the game's own teleport arrival), the one nearest the middle of
   the place's cells;
2. else the arrival of a door into the place (a door reference with a destination and no destination cell leads
   outside; its destination lies in one of the place's cells): the one nearest the middle of the place's cells,
   among those above the sea when there are any, and among those on the street (street_doors: on land the doors
   standing lowest over the terrain, the game's LAND heights; over the water the lowest walkway near the middle).
   A door's arrival is where the game itself puts you on the street (TPNAMES-HEIGHTS-56: the cell middle of a
   hillside town can be a roof or a rock; OpenMW's next fallback, an XMarkerHeading, can be anywhere a script
   needs, so it is not used);
3. else where the placed object nearest the middle of the place's cells stands, above the water (no doors or
   markers), with no height: the engine stands you on the floor there (dbg tp X Y); the cell middle itself can
   be the sea (Fields of Kummu in the v0.0.57-dev1 settlement sweep);
4. else the middle of the place's cells with no height.
The height of 1 and 2 is the marker's own plus 32 units, so "the floor at or below it" (dbg tp X Y Z) is that
street.

The expansions (TP-LIST-EXPANSIONS-66): the places and the room names are read through the merging reader of exactly
the build's selected layers (mwad.masters, AMIWIND_MASTERS); with the base game alone that is Morrowind.esm itself
and the table is unchanged. An outdoor place that only an expansion adds (Solstheim) is listed only when the image
holds a CHIM frame of one of its cells, in the base world or in the expansion's own store (the image's
--chim-layer-world values); the others are named in the report (places_not_built).

Rooms (TP-MENU-INTERIORS-63): the image step adds one row for every converted room the image holds
(add_rooms, called where the image knows its room maps), labelled "<the room's cell name> (interior)" on every room
row, so a room never clashes with an outdoor place of the same name and typing "interior" filters to the rooms.
A room row has flag 8 and its room map name; choosing it runs `dbg tp <map>`, which enters at the door's arrival.

Beings and categories (v0.0.66, TP-MENU-CATEGORY-FILTER-66, DBG-TP-TO-NPC-66): one Beings row per person or creature
(NPC_ and CREA records alike) placed in a cell the image holds, by its own display name (FNAM), never its record id.
A name placed once: "Name"; placed 2 to 4 times in different places: "Name, <place>" each; placed COMMON_AT times or
more (slaughterfish, mudcrabs, generic guards): one row "Name" with flag 32 whose placements file id1/tpk/<map>.tpk
lists them all, so the engine takes you to the nearest one. A being row has flag 16, its record id, and a room map
with the being's point in that room's units (world_doors.local_point), or no map and the global point outdoors. A
being whose cell the image does not hold is left out and named in the report (beings_not_built).
Expansion tags: a place, room or being that a later layer first defines (not one it only edits) carries " (Tribunal)"
or " (Bloodmoon)" after its name in this list only.
The names list id1/tp-names.lut (AWTN, aw_listbox.h) is what the box holds while open: per row the category
(1 exteriors, 2 interiors, 3 beings), the label length and the label, row for row as this table.

File (big-endian): header 16 bytes: "AWTP", u16 version 3, u16 row bytes 128, u32 rows, u32 0. Rows x 128, sorted by
name (case ignored): name[64] (Latin-1, NUL-padded, at most 63 bytes), i32 x, i32 y, i32 z (original global
units), u8 flags (1 z given, 2 door arrival, 4 CocMarkerHeading, 8 a room), u8 the place's cells (at most 255),
u16 0, map[16] (a room row's map name, NUL-padded; else zero), id[32] (a being's record id). Version 2 (row 96, no id)
and version 1 (row 48: name[32], then the same 16 bytes,
no map) is the earlier table; the engine and read_table read both, so an older disk keeps its settlements list.

  python3 tools/tp_places_lut.py --data-files DIR --out tp-places.lut [--report report.json]
"""
import argparse
import hashlib
import json
import math
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))
from mwad.audit import cell_data, records, subrecords  # noqa: E402  (the package, before tools/mwad.py)

MAGIC = b'AWTP'
VERSION = 3
NAME = 'tp-places.lut'
NAMES = 'tp-names.lut'
KIND_DIR = 'tpk'
HEADER = 16
ROW = 128
ROW_V2 = 96
ID_BYTES = 32
F_BEING, F_NEAREST = 16, 32
COMMON_AT = 5                   # placements of one name from which it is a common kind (the nearest one)
CAT_EXTERIOR, CAT_INTERIOR, CAT_BEING = 1, 2, 3
NAME_BYTES = 64
MAP_BYTES = 16
ROW_V1, NAME_BYTES_V1 = 48, 32   # the earlier table (no rooms), still read
ROOM_SUFFIX = ' (interior)'
F_ROOM = 8
CELL_UNITS = 8192
LIFT = 32                       # original units above the marker: "the floor at or below" is its street
SEA_LEVEL = 0                   # the open world's water level (original units)
LAND_MARGIN = 64                # a land spot stands at least this far above the water
GROUND_SLACK = 100              # a street door stands at most this far above the place's lowest door-to-ground
NEAR_DOOR = 1024                # over the water: the doors this near the middle one are the same spot
F_HAS_Z, F_DOOR, F_COC = 1, 2, 4
COC_MARKER = 'cocmarkerheading'


def _cell_of(x, y):
    return (math.floor(x / CELL_UNITS), math.floor(y / CELL_UNITS))


def land_heights(fields):
    """(cell x, cell y, 65 x 65 heights in original units) of a LAND record, or None without VHGT (OpenMW
    components/esm3/loadland.cpp: a float offset, then each row starts from the previous row's first height and adds
    signed byte deltas; the result times 8)."""
    f = dict(fields)
    if len(f.get('INTV', b'')) < 8 or len(f.get('VHGT', b'')) < 4 + 65 * 65:
        return None
    x, y = struct.unpack_from('<ii', f['INTV'])
    v = f['VHGT']
    row = struct.unpack_from('<f', v)[0]
    deltas = v[4:4 + 65 * 65]
    grid = []
    for r in range(65):
        row += struct.unpack_from('<b', deltas, r * 65)[0]
        h, line = row, [row * 8]
        for c in range(1, 65):
            h += struct.unpack_from('<b', deltas, r * 65 + c)[0]
            line.append(h * 8)
        grid.append(line)
    return x, y, grid


def ground_at(lands, x, y):
    """The terrain height under (x, y) from LANDS {cell: grid} (nearest vertex, 128 units apart), or None."""
    cx, cy = _cell_of(x, y)
    grid = lands.get((cx, cy))
    if grid is None:
        return None
    u = min(64, max(0, round((x - cx * CELL_UNITS) / 128.0)))
    v = min(64, max(0, round((y - cy * CELL_UNITS) / 128.0)))
    return grid[v][u]


def collect(raw, lands=None):
    """({key: {'name', 'cells': set, 'coc': [pos]}}, [door arrival positions into the open world]); LANDS, when a
    dict is given, receives {cell: heights} of every LAND record."""
    places = {}
    doors = []
    for tag, flags, payload in records(raw):
        if tag == 'LAND' and lands is not None and not flags & 0x20:
            got = land_heights(list(subrecords(payload)))
            if got:
                lands[(got[0], got[1])] = got[2]
            continue
        if tag != 'CELL' or flags & 0x20:
            continue
        c = cell_data(list(subrecords(payload)))
        refs = [r for r in c['refs'] if not r.get('deleted')]
        for r in refs:
            if 'destination' in r and not r.get('destination_cell'):
                doors.append(tuple(r['destination']['position']))
        if c['flags'] & 1 or not c['name'].strip():
            continue
        key = c['name'].strip().casefold()
        place = places.setdefault(key, {'name': c['name'].strip(), 'cells': set(), 'coc': []})
        place['cells'].add((c['x'], c['y']))
        place['coc'] += [tuple(r['position']) for r in refs
                         if r.get('id', '').casefold() == COC_MARKER and 'position' in r]
        # land spots: placed objects above the water (no doors, no markers), for a place without a door
        place.setdefault('land', []).extend(
            tuple(r['position']) for r in refs if 'position' in r and 'destination' not in r
            and r['position'][2] >= SEA_LEVEL + LAND_MARGIN and not r.get('id', '').casefold().endswith('marker'))
    return places, doors


def street_doors(points, lands, near):
    """The door arrivals of a place that stand on its street, not on a tower, a ruin top or a high walkway (the
    v0.0.57 settlement sweeps: Bal Isra's tower door put the player on top of the ruin; Vivec, Temple's and
    Uvirith's Grave's high doors stood over floors the collision does not hold, so the player dropped to the
    level below):
    - on land (the terrain under at least one door above the water): the doors at most GROUND_SLACK above the
      lowest door-to-terrain height of the place;
    - over the water (Vivec's cantons stand in the sea): the lowest of the doors within NEAR_DOOR of NEAR (the
      door nearest the middle), so the arrival is the lowest walkway there."""
    heights = [(p, ground_at(lands, p[0], p[1])) for p in points]
    land = [(p, p[2] - g) for p, g in heights if g is not None and g >= SEA_LEVEL]
    if land:
        lowest = min(above for _, above in land)
        return [p for p, above in land if above <= lowest + GROUND_SLACK]
    close = [p for p in points if (p[0] - near[0]) ** 2 + (p[1] - near[1]) ** 2 <= NEAR_DOOR ** 2]
    return [min(close or [near], key=lambda p: (p[2], p))]


def arrival(place, doors_by_cell, lands=None):
    """(x, y, z, flags) of PLACE (the order in the module text)."""
    cells = sorted(place['cells'])
    mx = sum((x + 0.5) * CELL_UNITS for x, _ in cells) / len(cells)
    my = sum((y + 0.5) * CELL_UNITS for _, y in cells) / len(cells)

    def nearest(points):
        return min(points, key=lambda p: ((p[0] - mx) ** 2 + (p[1] - my) ** 2, p))
    if place['coc']:
        p = nearest(place['coc'])
        return round(p[0]), round(p[1]), round(p[2]) + LIFT, F_HAS_Z | F_COC
    inside = [p for cell in cells for p in doors_by_cell.get(cell, ())]
    # above the sea first (a canal or sewer exit under the water line is no street: Vivec's Foreign Quarter)
    inside = [p for p in inside if p[2] >= SEA_LEVEL] or inside
    if inside:
        if lands:
            inside = street_doors(inside, lands, nearest(inside)) or inside
        p = nearest(inside)
        return round(p[0]), round(p[1]), round(p[2]) + LIFT, F_HAS_Z | F_DOOR
    if place.get('land'):
        # no door: where the nearest placed object above the water stands, on the floor there (no height: an
        # object's origin can be its top); the cell middle can be the sea (Fields of Kummu, the dev1 sweep)
        p = nearest(place['land'])
        return round(p[0]), round(p[1]), 0, 0
    return round(mx), round(my), 0, 0


def encode_name(name):
    raw = name.encode('latin-1', 'replace')
    return raw[:NAME_BYTES - 1]


def exterior_cells(raw):
    """{(x, y)} of every exterior cell of a master (path or bytes)."""
    raw = raw if isinstance(raw, (bytes, bytearray)) else Path(raw).read_bytes()
    out = set()
    for tag, flags, payload in records(raw):
        if tag != 'CELL' or flags & 0x20:
            continue
        data = next((d for t, d in subrecords(payload) if t == 'DATA'), b'')
        if len(data) >= 12:
            bits, x, y = struct.unpack_from('<Iii', data)
            if not bits & 1:
                out.add((x, y))
    return out


# ---------------------------------------------------------------- beings and expansion tags (v0.0.66)

BEING_TAGS = ('NPC_', 'CREA')


def being_records(raw):
    """{record id casefolded: (record id, display name)} of every NPC_ and CREA record with a display name (FNAM)."""
    out = {}
    for tag, flags, payload in records(raw):
        if tag not in BEING_TAGS or flags & 0x20:
            continue
        f = {}
        for sub_tag, sub_data in subrecords(payload):
            f.setdefault(sub_tag, sub_data)
        ident = f.get('NAME', b'').split(b'\0')[0].decode('latin-1').strip()
        name = f.get('FNAM', b'').split(b'\0')[0].decode('latin-1').strip()
        if ident and name and 'DELE' not in f:
            out[ident.casefold()] = (ident, name)
    return out


def layer_keys(raw):
    """(record ids, exterior cells, interior cell names), casefolded, that a master defines or edits."""
    ids, cells, rooms = set(), set(), set()
    for tag, flags, payload in records(raw):
        if tag in BEING_TAGS:
            name = next((d for t, d in subrecords(payload) if t == 'NAME'), b'')
            ids.add(name.split(b'\0')[0].decode('latin-1').strip().casefold())
        elif tag == 'CELL':
            f = {}
            for sub_tag, sub_data in subrecords(payload):
                f.setdefault(sub_tag, sub_data)
            if len(f.get('DATA', b'')) < 12:
                continue
            bits, x, y = struct.unpack_from('<Iii', f['DATA'])
            if bits & 1:
                rooms.add(f.get('NAME', b'').split(b'\0')[0].decode('latin-1').strip().casefold())
            else:
                cells.add((x, y))
    return ids, cells, rooms


def layer_tags(layers):
    """{'records': {id: tag}, 'cells': {(x, y): tag}, 'rooms': {name: tag}} from LAYERS [(master name, bytes)] in load
    order: a key first defined by a later layer is tagged with that layer's name ("Tribunal"); keys the base game
    defines are never tagged, though a layer edits them."""
    out = {'records': {}, 'cells': {}, 'rooms': {}}
    seen = [set(), set(), set()]
    for index, (master, raw) in enumerate(layers):
        tag = Path(master).stem
        for k, (key, keys) in enumerate(zip(('records', 'cells', 'rooms'), layer_keys(raw))):
            for item in keys - seen[k]:
                if index:
                    out[key][item] = tag
            seen[k] |= keys
    return out


def tagged(name, tag):
    """NAME with ' (TAG)' after it (cut so the tag always fits the name field)."""
    if not tag:
        return name
    suffix = ' (%s)' % tag
    keep = NAME_BYTES - 1 - len(suffix)
    return name.encode('latin-1', 'replace')[:keep].decode('latin-1').rstrip() + suffix


def untagged(label):
    """The label without its expansion tag and the room suffix (what the search is meant to find)."""
    for tag in ('Tribunal', 'Bloodmoon'):
        label = label.replace(' (%s)' % tag, '')
    return label[:-len(ROOM_SUFFIX)] if label.endswith(ROOM_SUFFIX) else label


def placements(raw, beings, rooms=None, cell_ok=None, offsets=None):
    """([placement], [left out]) of every being reference of RAW: {'id', 'name', 'place', 'map', 'x', 'y', 'z'}.
    Interior ones only in ROOMS {cell casefold: map} (point in the room's units, world_doors.local_point with the room's
    recentring OFFSETS), exterior ones only where CELL_OK((x, y)) holds (global point). ROOMS None: no interiors;
    CELL_OK None: no exteriors."""
    from world_doors import local_point
    out, left = [], []
    for tag, flags, payload in records(raw):
        if tag != 'CELL' or flags & 0x20:
            continue
        c = cell_data(list(subrecords(payload)))
        interior = bool(c['flags'] & 1)
        for r in c['refs']:
            got = beings.get(r.get('id', '').casefold())
            if not got or r.get('deleted') or 'position' not in r:
                continue
            ident, name = got
            if interior:
                if rooms is None:
                    continue
                m = rooms.get(c['name'].strip().casefold())
                if not m:
                    left.append('%s (%s)' % (name, c['name'].strip()))
                    continue
                p = local_point(r['position'], 'room', (offsets or {}).get(c['name'].strip().casefold()))
                out.append({'id': ident, 'name': name, 'place': c['name'].strip(), 'map': m,
                            'x': round(p[0]), 'y': round(p[1]), 'z': round(p[2])})
            else:
                if cell_ok is None:
                    continue
                if not cell_ok((c['x'], c['y'])):
                    left.append('%s (%d, %d)' % (name, c['x'], c['y']))
                    continue
                place = c['name'].strip() or c.get('region', '').strip() or '%d, %d' % (c['x'], c['y'])
                p = r['position']
                out.append({'id': ident, 'name': name, 'place': place, 'map': '',
                            'x': round(p[0]), 'y': round(p[1]), 'z': round(p[2])})
    return out, left


def kind_file_name(label):
    """The placements file of a common kind: 'k' + the CRC-32 of its label (casefolded), 9 characters."""
    import zlib
    return 'k%08x' % (zlib.crc32(label.casefold().encode('latin-1', 'replace')) & 0xFFFFFFFF)


def encode_kind(rows):
    """The AWTK bytes (aw_listbox.h) of placement ROWS."""
    out = bytearray(b'AWTK' + struct.pack('>HHII', 1, 64, len(rows), 0))
    for r in rows:
        out += r['id'].encode('latin-1', 'replace')[:ID_BYTES - 1].ljust(ID_BYTES, b'\0')
        out += r['map'].encode('ascii')[:MAP_BYTES - 1].ljust(MAP_BYTES, b'\0')
        out += struct.pack('>iiiI', r['x'], r['y'], r['z'], 0)
    return bytes(out)


def being_rows(found, record_tags=None):
    """(table rows, {kind file name: AWTK bytes}) of the placements FOUND (the module text's rule)."""
    record_tags = record_tags or {}
    groups = {}
    for p in found:
        label = tagged(p['name'], record_tags.get(p['id'].casefold()))
        groups.setdefault(label.casefold(), (label, []))[1].append(p)
    rows, kinds = [], {}
    for key in sorted(groups):
        label, group = groups[key]
        group.sort(key=lambda p: (p['map'], p['place'], p['id'], p['x'], p['y'], p['z']))
        places = {p['place'].casefold() for p in group}
        if len(group) >= COMMON_AT or (len(group) > 1 and len(places) < len(group)):
            name = kind_file_name(label)
            kinds[name] = encode_kind(group)
            rows.append({'name': label, 'x': 0, 'y': 0, 'z': 0, 'flags': F_BEING | F_NEAREST | F_HAS_Z,
                         'cells': 0, 'map': name, 'id': ''})
            continue
        for p in group:
            text = label
            if len(group) > 1:   # "Dagoth Ur, Facility Cavern": a place already named after the being stays as it is
                text = p['place'] if p['place'].casefold().startswith(p['name'].casefold() + ',') \
                    and label == p['name'] else label + ', ' + p['place']
            raw = text.encode('latin-1', 'replace')[:NAME_BYTES - 1].decode('latin-1')
            rows.append({'name': raw, 'x': p['x'], 'y': p['y'], 'z': p['z'],
                         'flags': F_BEING | F_HAS_Z | (F_ROOM if p['map'] else 0), 'cells': 0,
                         'map': p['map'], 'id': p['id']})
    return rows, kinds


def category(flags):
    if flags & F_BEING:
        return CAT_BEING
    return CAT_INTERIOR if flags & F_ROOM else CAT_EXTERIOR


def encode_names(table):
    """The AWTN bytes of a table: row for row, the category, the label length and the label."""
    rows = read_table(table)
    body = bytearray()
    for r in rows:
        label = r['name'].encode('latin-1', 'replace')[:NAME_BYTES - 1]
        body += bytes((category(r['flags']), len(label))) + label
    return b'AWTN' + struct.pack('>HHII', 1, 0, len(rows), len(body)) + bytes(body)


def read_names(data):
    """[(category, label)] of an AWTN list."""
    if data[:4] != b'AWTN':
        raise ValueError('not AWTN')
    _, _, count, size = struct.unpack_from('>HHII', data, 4)
    if len(data) != HEADER + size:
        raise ValueError('AWTN size mismatch')
    out, at = [], HEADER
    for _ in range(count):
        cat, n = data[at], data[at + 1]
        out.append((cat, data[at + 2:at + 2 + n].decode('latin-1')))
        at += 2 + n
    if at != len(data):
        raise ValueError('AWTN rows do not fill it')
    return out


def write_list(id1, table, kinds=None):
    """id1/tp-places.lut, id1/tp-names.lut and (KINDS given) id1/tpk/*.tpk, the earlier kind files replaced; the
    names list's bytes (what the box holds while open: the labels plus 4 bytes a row)."""
    id1 = Path(id1)
    (id1 / NAME).write_bytes(table)
    names = encode_names(table)
    (id1 / NAMES).write_bytes(names)
    if kinds is not None:
        folder = id1 / KIND_DIR
        if folder.is_dir():
            for old in sorted(folder.glob('k*.tpk')):
                old.unlink()
        if kinds:
            folder.mkdir(parents=True, exist_ok=True)
        for name in sorted(kinds):
            (folder / (name + '.tpk')).write_bytes(kinds[name])
    rows = struct.unpack_from('>I', names, 8)[0]
    return len(names) - HEADER + 4 * rows


def build_master(master, base_cells=None, frames=None, tags=None):
    """(table bytes, report) of a master (path or bytes). With BASE_CELLS (the base game's exterior cells, given when
    expansion layers are merged in) an outdoor place none of whose cells is a base cell is listed only when one of its
    cells is in FRAMES (the exterior cells the image holds frames for); the rest are named in the report
    ('places_not_built'). TAGS (layer_tags) tag the places a later layer first defines. The report also holds the
    outdoor beings of the cells the table lists ('beings_exterior'; the room step adds them, image_rooms)."""
    t0 = time.time()
    raw = master if isinstance(master, (bytes, bytearray)) else Path(master).read_bytes()
    lands = {}
    places, doors = collect(raw, lands)
    cell_tags = (tags or {}).get('cells', {})
    for place in places.values():
        first = sorted(place['cells'])
        if first and all(c in cell_tags for c in first):
            place['name'] = tagged(place['name'], cell_tags[first[0]])
    not_built = []
    if base_cells is not None:
        frames = set(frames or ())
        for key in sorted(places):
            cells = places[key]['cells']
            if not cells & base_cells and not cells & frames:
                not_built.append(places.pop(key)['name'])
    doors_by_cell = {}
    for p in doors:
        doors_by_cell.setdefault(_cell_of(p[0], p[1]), []).append(p)
    rows = []
    for key in sorted(places):
        place = places[key]
        x, y, z, flags = arrival(place, doors_by_cell, lands)
        rows.append({'name': place['name'], 'x': x, 'y': y, 'z': z, 'flags': flags,
                     'cells': len(place['cells']), 'cut': len(place['name'].encode('latin-1', 'replace'))
                     >= NAME_BYTES})
    data = encode_table(rows)
    report = {
        'format': 'AWTP%d' % VERSION, 'rows': len(rows), 'bytes': len(data),
        'sha256': hashlib.sha256(data).hexdigest(),
        'arrivals': {'coc_marker': sum(1 for r in rows if r['flags'] & F_COC),
                     'door': sum(1 for r in rows if r['flags'] & F_DOOR),
                     'cell_middle': sum(1 for r in rows if not r['flags'] & F_HAS_Z)},
        'names_cut': [r['name'] for r in rows if r['cut']],
        'places': [{k: r[k] for k in ('name', 'x', 'y', 'z', 'flags', 'cells')} for r in rows],
        'resident_bytes': 0, 'open_bytes': len(data),
        'seconds': round(time.time() - t0, 3),
    }
    if base_cells is not None:
        report['places_not_built'] = not_built
    frames_set = set(frames or ())
    found, left = placements(raw, being_records(raw), rooms=None,
                             cell_ok=lambda c: base_cells is None or c in base_cells or c in frames_set)
    report['beings_exterior'] = found
    report['beings_not_built'] = left
    report['record_tags'] = dict(sorted((tags or {}).get('records', {}).items()))
    report['room_tags'] = dict(sorted((tags or {}).get('rooms', {}).items()))
    return data, report


def encode_table(rows):
    """The AWTP3 bytes of ROWS ({'name', 'x', 'y', 'z', 'flags', 'cells'[, 'map']}), sorted by name (case ignored)."""
    if len(rows) > 65535:
        raise ValueError('Settlements table: %d rows, at most 65535' % len(rows))
    rows = sorted(rows, key=lambda r: (r['name'].casefold(), r['name'], r.get('map', '')))
    out = bytearray(MAGIC + struct.pack('>HHII', VERSION, ROW, len(rows), 0))
    for r in rows:
        out += encode_name(r['name']).ljust(NAME_BYTES, b'\0')
        out += struct.pack('>iiiBBH', r['x'], r['y'], r['z'], r['flags'], min(255, r['cells']), 0)
        out += r.get('map', '').encode('ascii')[:MAP_BYTES].ljust(MAP_BYTES, b'\0')
        out += r.get('id', '').encode('latin-1', 'replace')[:ID_BYTES - 1].ljust(ID_BYTES, b'\0')
    return bytes(out)


def room_label(cell_name):
    """"<cell name> (interior)", the cell name cut so the suffix always fits the name field."""
    keep = NAME_BYTES - 1 - len(ROOM_SUFFIX)
    return cell_name.encode('latin-1', 'replace')[:keep].decode('latin-1').rstrip() + ROOM_SUFFIX


def interior_names(raw):
    """{cell casefold: the cell's own name} of every interior cell of a master (path or bytes)."""
    raw = raw if isinstance(raw, (bytes, bytearray)) else Path(raw).read_bytes()
    out = {}
    for tag, flags, payload in records(raw):
        if tag != 'CELL' or flags & 0x20:
            continue
        f = {}
        for sub_tag, sub_data in subrecords(payload):   # the cell's own NAME and DATA come before its references'
            f.setdefault(sub_tag, sub_data)
        if len(f.get('DATA', b'')) >= 4 and struct.unpack_from('<I', f['DATA'])[0] & 1 and f.get('NAME'):
            name = f['NAME'].split(b'\0')[0].decode('latin-1').strip()
            if name:
                out.setdefault(name.casefold(), name)
    return out


def add_rooms(table, rooms, names=None, room_tags=None):
    """(AWTP2 bytes, report) of TABLE (v1 or v2) with one row per room of ROOMS {cell casefold: map name}: the label
    room_label of the cell's own name (NAMES {casefold: name}, else the key), flag F_ROOM, the map; earlier room rows
    are replaced. A room whose map name does not fit, or is not lower-case letters, digits and _, is left out (listed)."""
    names = names or {}
    room_tags = room_tags or {}
    rows = [r for r in read_table(table) if not r['flags'] & (F_ROOM | F_BEING)]
    added, left_out = 0, []
    for key in sorted(rooms):
        m = rooms[key]
        if not m or len(m) >= MAP_BYTES or not all(c.isdigit() or c == '_' or 'a' <= c <= 'z' for c in m):
            left_out.append(key)
            continue
        rows.append({'name': room_label(tagged(names.get(key, key), room_tags.get(key))), 'x': 0, 'y': 0, 'z': 0,
                     'flags': F_ROOM, 'cells': 0,
                     'map': m})
        added += 1
    data = encode_table(rows)
    return data, {'rows': len(rows), 'rooms': added, 'rooms_left_out': left_out, 'bytes': len(data),
                  'sha256': hashlib.sha256(data).hexdigest(), 'open_bytes': len(data), 'resident_bytes': 0}


def image_rooms(id1, rooms, master, out=None):
    """The image's room rows: id1/tp-places.lut rewritten with ROOMS {cell casefold: map} (the room maps this image
    holds) named from MASTER's interior cells; the report beside the table's (tp-places-rooms.json)."""
    target = Path(id1) / NAME
    if not target.is_file():
        return None
    t0 = time.time()
    places = {}
    if out is not None and (Path(out) / 'tp-places-table.json').is_file():
        places = json.loads((Path(out) / 'tp-places-table.json').read_text(encoding='utf-8'))
    data, report = add_rooms(target.read_bytes(), rooms, interior_names(master), places.get('room_tags'))
    data, beings = add_beings(data, master, rooms, places.get('beings_exterior', []), places.get('record_tags'))
    kinds = beings.pop('kind_files_data')        # bytes: written as files, never into the JSON report
    report.update(beings)
    report['names_bytes_open'] = write_list(id1, data, kinds)
    report['bytes'] = len(data)
    report['sha256'] = hashlib.sha256(data).hexdigest()
    report['beings_not_built'] = sorted(set(places.get('beings_not_built', [])) | set(report['beings_not_built']))
    if out is not None:
        (Path(out) / 'tp-places-rooms.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n',
                                                         encoding='utf-8', newline='\n')
    print('Settlements table: %d rooms and %d being rows (%d common kinds) added, %d rows, %d bytes on disk, %d bytes '
          'held while the box is open (%d rooms and %d beings left out; took %.1f s, 1 core; 0 bytes resident)' % (
              report['rooms'], report['being_rows'], report['kinds'], report['rows'], report['bytes'],
              report['names_bytes_open'], len(report['rooms_left_out']), len(report['beings_not_built']),
              time.time() - t0), flush=True)
    return report


def add_beings(table, master, rooms, exterior, record_tags=None, offsets=None):
    """(AWTP3 bytes, report) of TABLE with its being rows replaced: the room placements of MASTER in ROOMS plus the
    outdoor ones EXTERIOR (the table step's report), grouped by being_rows. The report holds 'kind_files_data'
    {name: AWTK bytes} for write_list."""
    raw = master if isinstance(master, (bytes, bytearray)) else Path(master).read_bytes()
    if offsets is None:
        try:
            from town_interiors import room_offsets
            offsets = room_offsets()
        except (OSError, ValueError, KeyError):
            offsets = {}
    inside, left = placements(raw, being_records(raw), rooms=rooms, cell_ok=None, offsets=offsets)
    found = inside + list(exterior)
    brows, kinds = being_rows(found, record_tags)
    rows = [r for r in read_table(table) if not r['flags'] & F_BEING] + brows
    data = encode_table(rows)
    return data, {'being_rows': len(brows), 'beings_placed': len(found), 'kinds': len(kinds),
                  'kind_files_bytes': sum(len(v) for v in kinds.values()),
                  'kind_file_largest': max((len(v) for v in kinds.values()), default=0),
                  'beings_not_built': left, 'rows': len(rows), 'kind_files_data': kinds}


def read_table(data):
    """[{'name', 'x', 'y', 'z', 'flags', 'cells', 'map'}] of an AWTP2 or AWTP1 table (the engine's
    AW_TpPlacesRows/Row; version 1 rows have no map)."""
    if data[:4] != MAGIC:
        raise ValueError('not AWTP')
    version, row, count, _ = struct.unpack_from('>HHII', data, 4)
    sizes = {1: (ROW_V1, NAME_BYTES_V1), 2: (ROW_V2, NAME_BYTES), 3: (ROW, NAME_BYTES)}
    if version not in sizes or row != sizes[version][0] or len(data) != HEADER + count * row:
        raise ValueError('AWTP header or size mismatch')
    name_bytes = sizes[version][1]
    rows = []
    for i in range(count):
        at = HEADER + i * row
        name = data[at:at + name_bytes].split(b'\0')[0].decode('latin-1')
        x, y, z, flags, cells, _ = struct.unpack_from('>iiiBBH', data, at + name_bytes)
        m = data[at + name_bytes + 16:at + name_bytes + 16 + MAP_BYTES].split(b'\0')[0].decode('ascii') \
            if version >= 2 else ''
        ident = data[at + name_bytes + 32:at + row].split(b'\0')[0].decode('latin-1') if version == 3 else ''
        rows.append({'name': name, 'x': x, 'y': y, 'z': z, 'flags': flags, 'cells': cells, 'map': m, 'id': ident})
    return rows


# ---------------------------------------------------------------- the image step

def layer_inputs(data, chim_world=None, masters=None, layer_worlds=None):
    """(masters, base exterior cells, frame cells) for the selected layers (mwad.masters.selected_masters: the
    build's AMIWIND_MASTERS, the same selection every layer-reading stage uses); (masters, None, None) with the base
    game alone. Frame cells: the exterior cells the CHIM world CHIM_WORLD holds frames for (chim/frames/.../frame.ccf)
    and the cells of the frames in the expansions' own stores LAYER_WORLDS (the image's --chim-layer-world values,
    chim.layer_stores.frame_holders: a land built by its module, Solstheim's cells in the store chimsol, is in the
    game by that store and not by the base world; TP-LIST-MODULE-STORE-PLACES-68)."""
    from mwad.masters import selected_masters
    from mwad.paths import child_ci
    masters = selected_masters(masters)
    if len(masters) == 1:
        return masters, None, None
    base = exterior_cells(child_ci(Path(data), masters[0]))
    frames = set()
    if chim_world:
        from chim.heap import frame_cells
        root = Path(chim_world) / 'chim' / 'frames'
        if root.is_dir():
            frames = frame_cells(p.relative_to(Path(chim_world) / 'chim') for p in root.rglob('frame.ccf'))
    if layer_worlds:
        from chim.layer_stores import frame_holders
        frames = set(frames) | {tuple(cell) for cell in frame_holders(layer_worlds)}
    return masters, base, frames


def image_step(data, id1, out=None, jobs=1, chim_world=None, layer_worlds=None, args=None):
    """The image step: id1/tp-places.lut from DATA's selected layers (the merging reader, mwad.masters; the base
    game alone = Morrowind.esm itself) through the unit cache (keyed by the merged master's SHA-256 and this module's
    source; with expansion layers also by the layer list and the layer-only exterior cells the image has frames for);
    the report beside it in OUT (tp-places-table.json). One unit: the island compiles in about a second on one core
    (the report's seconds), so it is not split."""
    from build_scratch import scratch_dir
    from mwad.esm import sha256_file
    from mwad.masters import master_path
    from pass_cache import UnitCache
    if args is not None:      # the image step's own options: the base CHIM world and the expansions' stores
        chim_world = chim_world or getattr(args, 'chim_world', None)
        layer_worlds = layer_worlds or getattr(args, 'chim_layer_world', None)
    masters, base_cells, frames = layer_inputs(data, chim_world, layer_worlds=layer_worlds)
    master = master_path(Path(data), masters)
    inputs = {'master_sha256': sha256_file(master)}
    if base_cells is not None:
        inputs['masters'] = list(masters)
        inputs['layer_frames'] = sorted(list(c) for c in frames - base_cells)
    cache = UnitCache.open('tp-places-table', {'format': 'AWTP%d' % VERSION}, __file__)
    target = Path(id1) / NAME
    t0 = time.time()
    print('Settlements table: start (1 unit cache lookup, 1 core if built: one unit)', flush=True)
    with scratch_dir(prefix='tp-places-', near=out if out is not None else Path(id1).parent,
                     keep_on_failure=False) as tmp:
        folder = Path(tmp) / 'unit'
        row = cache.restore_unit(inputs, folder) if cache else None
        if row is not None:
            report = json.loads((folder / 'report.json').read_text(encoding='utf-8'))
            raw = (folder / NAME).read_bytes()
            report['reused'] = True
        else:
            tags = None
            if base_cells is not None:
                from mwad.paths import child_ci
                tags = layer_tags([(m, child_ci(Path(data), m).read_bytes()) for m in masters])
            raw, report = build_master(master, base_cells, frames, tags)
            folder.mkdir(parents=True)
            (folder / NAME).write_bytes(raw)
            (folder / 'report.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n',
                                                encoding='utf-8', newline='\n')
            if cache:
                cache.store_unit(inputs, {'bytes': len(raw)}, folder)
            report['reused'] = False
    if hashlib.sha256(raw).hexdigest() != report['sha256']:
        raise ValueError('Settlements table: SHA-256 differs from its report')
    target.parent.mkdir(parents=True, exist_ok=True)
    report['names_bytes_open'] = write_list(target.parent, raw)
    if out is not None:
        Path(out).mkdir(parents=True, exist_ok=True)
        (Path(out) / 'tp-places-table.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n',
                                                        encoding='utf-8', newline='\n')
    print('Settlements table: %s %s, %d bytes, %d places (%d CocMarker, %d door, %d cell middle; took %.1f s, '
          '1 core; 0 bytes resident)' % (
              'reused' if report['reused'] else 'built', NAME, len(raw), report['rows'],
              report['arrivals']['coc_marker'], report['arrivals']['door'], report['arrivals']['cell_middle'],
              time.time() - t0), flush=True)
    if 'places_not_built' in report:
        print('Settlements table: layers %s; %d expansion outdoor places not listed (no frame in this image): %s' % (
            ', '.join(masters), len(report['places_not_built']), ', '.join(report['places_not_built']) or 'none'),
            flush=True)
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True, help='the AWTP1 file to write')
    p.add_argument('--report', type=Path)
    a = p.parse_args(argv)
    from mwad.paths import child_ci
    from mwad.masters import master_path
    raw, report = build_master(master_path(a.data_files))
    a.out.write_bytes(raw)
    if a.report:
        a.report.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print('Settlements table: %d bytes, %d places (%s), %.2f s' % (
        len(raw), report['rows'], ', '.join('%s %d' % kv for kv in sorted(report['arrivals'].items())),
        report['seconds']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
