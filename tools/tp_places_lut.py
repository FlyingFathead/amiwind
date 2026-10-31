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

File (big-endian): header 16 bytes: "AWTP", u16 version 1, u16 row bytes 48, u32 rows, u32 0. Rows x 48, sorted by
name (case ignored): name[32] (Latin-1, NUL-padded, at most 31 bytes), i32 x, i32 y, i32 z (original global
units), u8 flags (1 z given, 2 door arrival, 4 CocMarkerHeading), u8 the place's cells (at most 255), u16 0.

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
VERSION = 1
NAME = 'tp-places.lut'
HEADER = 16
ROW = 48
NAME_BYTES = 32
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


def build_master(master):
    """(table bytes, report) of a master (path or bytes)."""
    t0 = time.time()
    raw = master if isinstance(master, (bytes, bytearray)) else Path(master).read_bytes()
    lands = {}
    places, doors = collect(raw, lands)
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
    if len(rows) > 65535:
        raise ValueError('Settlements table: %d places, at most 65535' % len(rows))
    out = bytearray(MAGIC + struct.pack('>HHII', VERSION, ROW, len(rows), 0))
    for r in rows:
        out += encode_name(r['name']).ljust(NAME_BYTES, b'\0')
        out += struct.pack('>iiiBBH', r['x'], r['y'], r['z'], r['flags'], min(255, r['cells']), 0)
    data = bytes(out)
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
    return data, report


def read_table(data):
    """[{'name', 'x', 'y', 'z', 'flags', 'cells'}] of an AWTP1 table (the engine's AW_TpPlacesRows/Row)."""
    if data[:4] != MAGIC:
        raise ValueError('not AWTP')
    version, row, count, _ = struct.unpack_from('>HHII', data, 4)
    if version != VERSION or row != ROW or len(data) != HEADER + count * ROW:
        raise ValueError('AWTP header or size mismatch')
    rows = []
    for i in range(count):
        at = HEADER + i * ROW
        name = data[at:at + NAME_BYTES].split(b'\0')[0].decode('latin-1')
        x, y, z, flags, cells, _ = struct.unpack_from('>iiiBBH', data, at + NAME_BYTES)
        rows.append({'name': name, 'x': x, 'y': y, 'z': z, 'flags': flags, 'cells': cells})
    return rows


# ---------------------------------------------------------------- the image step

def image_step(data, id1, out=None, jobs=1):
    """The image step: id1/tp-places.lut from DATA's Morrowind.esm through the unit cache (keyed by the master's
    SHA-256 and this module's source); the report beside it in OUT (tp-places-table.json). One unit: the island
    compiles in about a second on one core (the report's seconds), so it is not split."""
    from build_scratch import scratch_dir
    from mwad.esm import sha256_file
    from mwad.paths import child_ci
    from pass_cache import UnitCache
    master = child_ci(Path(data), 'Morrowind.esm')
    inputs = {'master_sha256': sha256_file(master)}
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
            raw, report = build_master(master)
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
    target.write_bytes(raw)
    if out is not None:
        Path(out).mkdir(parents=True, exist_ok=True)
        (Path(out) / 'tp-places-table.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n',
                                                        encoding='utf-8', newline='\n')
    print('Settlements table: %s %s, %d bytes, %d places (%d CocMarker, %d door, %d cell middle; took %.1f s, '
          '1 core; 0 bytes resident)' % (
              'reused' if report['reused'] else 'built', NAME, len(raw), report['rows'],
              report['arrivals']['coc_marker'], report['arrivals']['door'], report['arrivals']['cell_middle'],
              time.time() - t0), flush=True)
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True, help='the AWTP1 file to write')
    p.add_argument('--report', type=Path)
    a = p.parse_args(argv)
    from mwad.paths import child_ci
    raw, report = build_master(child_ci(a.data_files, 'Morrowind.esm'))
    a.out.write_bytes(raw)
    if a.report:
        a.report.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print('Settlements table: %d bytes, %d places (%s), %.2f s' % (
        len(raw), report['rows'], ', '.join('%s %d' % kv for kv in sorted(report['arrivals'].items())),
        report['seconds']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
