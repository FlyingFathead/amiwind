#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Every teleport and door arrival into a room of an image, checked by number (TP-BEING-TRIBUNAL-FALLS-THROUGH-67).

A teleport to a person or creature in a room (dbg tp, the Beings rows of id1/tp-places.lut and the placements files
id1/tpk/*.tpk of the common kinds), a teleport to a room (its map's info_player_start) and every door into a room
(the door banks id1/*doors-<map>.txt) end in the same arrival search, the engine's (aw_scene.c standing_spot, here
tools/arrival_spot.py): from 8 units over the arrival down to 88 under it, the first spot with a walkable floor, a
clear standing box and dry feet. For each arrival this tool runs that search on the room's collision (a CHIM room:
its map's shell and every placement of its room record, chim/room_scene.py) and compares the spot with the floor
under the arrival:

  on-floor     the spot stands on that floor, or within a step of it (the search may step 16 units aside)
  below-floor  the spot's feet are more than UNDER units under that floor: the player falls or stands under the room
  blocked      no spot: the engine falls back to the room's start (and, for a being, the free spot beside it)

The arrival is the engine's: a being's row holds its feet and the engine lifts it to a door's height
(aw_listbox_rules.c AW_TpBeingArrival: the feet less the player's box bottom plus a quarter unit, the same 16.875 as
town_interiors.FEET); a door's arrival is stored lifted; a room's start is its info_player_start. With --raw-beings the
being rows are searched from their feet, as the engine did before v0.0.67 (the A/B of the fix).

Exit 1 when any arrival is below-floor (each named), 0 otherwise. Usage:
  tp_arrivals.py ID1_DIR [--out report.json] [--jobs N] [--raw-beings] [--layer base|Tribunal|Bloodmoon]
"""
import argparse
import json
import os
import re
import struct
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

for _p in (Path(__file__).resolve().parents[1] / 'src', Path(__file__).resolve().parent):
    if str(_p) not in sys.path:
        sys.path.insert(1 if str(_p).endswith('tools') else 0, str(_p))

from arrival_spot import Collision, standing_spot  # noqa: E402
from player_hull import MINS, STEP_HEIGHT  # noqa: E402

UNDER = STEP_HEIGHT + 4          # a spot more than a step (and a little) under the arrival's floor is under the room
LIFT = -MINS[2] + .25            # aw_listbox_rules.c AW_TpBeingArrival (the player's box bottom less, plus .25)
DEPTH = 512.0                    # how far under the arrival a floor is looked for
TAGS = ('Tribunal', 'Bloodmoon')


def layer(label):
    """The layer a label names (dbg tp's expansion tag, tools/tp_places_lut.py tagged), else 'base'."""
    for tag in TAGS:
        if '(%s)' % tag in label:
            return tag
    return 'base'


def floor_under(collision, feet):
    """The floor under FEET: the standing box dropped from 4 units over the feet, DEPTH down (None: none, or the box
    starts in something)."""
    origin = (feet[0], feet[1], feet[2] + 4 - MINS[2])
    try:
        ground = collision.ground(origin, DEPTH)
    except ValueError:
        return None
    return None if ground is None else ground + MINS[2]


def judge(collision, arrival, feet_z):
    """The verdict of one arrival: the engine's search from ARRIVAL, the floor under (ARRIVAL x y, FEET_Z)."""
    floor = floor_under(collision, (arrival[0], arrival[1], feet_z))
    try:
        spot = standing_spot(collision, arrival)
    except ValueError as exc:
        return {'floor': floor, 'spot': None, 'verdict': 'blocked', 'why': str(exc)}
    out = {'floor': None if floor is None else round(floor, 2), 'spot': None if spot is None else
           [round(v, 2) for v in spot]}
    if spot is None:
        out['verdict'] = 'blocked'
    elif floor is not None and spot[2] + MINS[2] < floor - UNDER:
        out['verdict'] = 'below-floor'
        out['under'] = round(floor - (spot[2] + MINS[2]), 2)
    else:
        out['verdict'] = 'on-floor'
    return out


def read_kind(data):
    """[(id, map, x, y, z)] of an AWTK placements file (tools/tp_places_lut.py encode_kind)."""
    if data[:4] != b'AWTK':
        raise ValueError('not AWTK')
    count = struct.unpack_from('>I', data, 8)[0]
    rows = []
    for i in range(count):
        at = 16 + i * 64
        ident = data[at:at + 32].split(b'\0')[0].decode('latin-1')
        m = data[at + 32:at + 48].split(b'\0')[0].decode('ascii')
        x, y, z, _ = struct.unpack_from('>iiiI', data, at + 48)
        rows.append((ident, m, x, y, z))
    return rows


def arrivals(id1):
    """{map: [arrival row]} of every room arrival of the image ID1: being rows (their feet), the common kinds'
    placements, the rooms' own rows and every door into a room."""
    import tp_places_lut as tpl
    id1 = Path(id1)
    rows = tpl.read_table((id1 / tpl.NAME).read_bytes())
    room_layer = {r['map']: layer(r['name']) for r in rows if r['flags'] & tpl.F_ROOM and not r['flags'] & tpl.F_BEING}
    out = {}

    def add(row):
        out.setdefault(row['map'], []).append(row)
    for r in rows:
        if not r['map']:
            continue
        if r['flags'] & tpl.F_NEAREST:
            for ident, m, x, y, z in read_kind((id1 / tpl.KIND_DIR / (r['map'] + '.tpk')).read_bytes()):
                if m:
                    add({'kind': 'being', 'name': r['name'], 'id': ident, 'map': m, 'layer': layer(r['name']),
                         'point': [x, y, z], 'common': r['map']})
        elif r['flags'] & tpl.F_BEING:
            add({'kind': 'being', 'name': r['name'], 'id': r['id'], 'map': r['map'], 'layer': layer(r['name']),
                 'point': [r['x'], r['y'], r['z']]})
        elif r['flags'] & tpl.F_ROOM:
            add({'kind': 'room', 'name': r['name'], 'id': '', 'map': r['map'], 'layer': layer(r['name']),
                 'point': None})
    for bank in sorted(id1.glob('*doors-*.txt')):
        lines = bank.read_text(encoding='cp1252').splitlines()
        if not lines or lines[0] != 'AWD3':
            continue
        for line in lines[1:]:
            text, _, label = line.partition('\t')
            head = text.split()
            if len(head) != 13 or head[1] not in room_layer:
                continue
            add({'kind': 'door', 'name': '%s -> %s (%s)' % (head[0], head[1], label), 'id': head[2], 'map': head[1],
                 'layer': room_layer[head[1]], 'point': [float(v) for v in head[9:12]]})
    return out


def start_of(raw):
    """The info_player_start origin of a map's entity text, or None."""
    from audit_walkability import lumps
    for block in re.findall(r'\{[^{}]*\}', lumps(raw)[0].decode('cp1252')):
        e = dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', block))
        if e.get('classname') == 'info_player_start' and 'origin' in e:
            return tuple(map(float, e['origin'].split()))
    return None


def collision_of(path):
    from map_files import is_chim_room
    if is_chim_room(path):
        from chim.room_scene import room_collision
        return room_collision(path)
    return Collision(path.read_bytes())


def check_map(job):
    """The verdicts of one map's arrivals: JOB = (id1, map, rows, raw_beings)."""
    id1, name, rows, raw_beings = job
    from map_files import map_file
    path = map_file(Path(id1) / 'maps', name)      # the engine's resolution: <name>.chim, else <name>.bsp
    out = []
    try:
        collision = collision_of(path)
        start = start_of(path.read_bytes())
    except (OSError, ValueError, KeyError) as exc:
        return [dict(r, verdict='unreadable', why='%s: %s' % (path.name, exc)) for r in rows]
    for r in rows:
        r = dict(r)
        if r['kind'] == 'room':
            if start is None:
                r.update(verdict='unreadable', why='no info_player_start')
                out.append(r)
                continue
            arrival, feet = start, start[2] + MINS[2]
        elif r['kind'] == 'being':
            feet = float(r['point'][2])
            arrival = (float(r['point'][0]), float(r['point'][1]), feet + (0 if raw_beings else LIFT))
        else:
            arrival = tuple(r['point'])
            feet = arrival[2] - LIFT
        r['arrival'] = [round(v, 3) for v in arrival]
        r.update(judge(collision, arrival, feet))
        out.append(r)
    return out


def check(id1, jobs=None, raw_beings=False, only_layer=None, progress=print):
    t0 = time.time()
    by_map = arrivals(id1)
    if only_layer:
        by_map = {m: [r for r in rows if r['layer'] == only_layer] for m, rows in by_map.items()}
        by_map = {m: rows for m, rows in by_map.items() if rows}
    total = sum(len(v) for v in by_map.values())
    progress('=== PHASE 1/2: %d arrivals in %d room maps (%.1f s) ===' % (total, len(by_map), time.time() - t0))
    work = [(str(id1), m, rows, raw_beings) for m, rows in sorted(by_map.items(), key=lambda kv: -len(kv[1]))]
    jobs = jobs or os.cpu_count() or 1
    progress('=== PHASE 2/2: the arrival search, %d processes ===' % jobs)
    results, done, last = [], 0, time.time()
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        for got in pool.map(check_map, work, chunksize=4):
            results.extend(got)
            done += 1
            if time.time() - last > 5:
                last = time.time()
                rate = done / (last - t0)
                progress('  %d / %d maps, %.1f maps/s, ETA %.0f s' % (done, len(work), rate,
                                                                    (len(work) - done) / max(rate, 1e-6)))
    counts = {}
    for r in results:
        c = counts.setdefault('%s %s' % (r['layer'], r['kind']), {})
        c[r['verdict']] = c.get(r['verdict'], 0) + 1
    below = [r for r in results if r['verdict'] == 'below-floor']
    return {'format': 1, 'id1': str(id1), 'raw_beings': raw_beings, 'counts': counts, 'below_floor': below,
            'rows': results, 'status': 'failed' if below else 'passed', 'seconds': round(time.time() - t0, 1),
            'rule': 'aw_scene.c standing_spot (tools/arrival_spot.py) from each arrival; a being row lifted %.3f '
                    'over its feet (aw_listbox_rules.c AW_TpBeingArrival); below-floor = the spot\'s feet more than '
                    '%.1f under the floor under the arrival' % (0 if raw_beings else LIFT, UNDER)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('id1', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--jobs', type=int)
    parser.add_argument('--raw-beings', action='store_true')
    parser.add_argument('--layer', choices=('base',) + TAGS)
    a = parser.parse_args(argv)
    report = check(a.id1, a.jobs, a.raw_beings, a.layer, progress=lambda s: print(s, flush=True))
    for key in sorted(report['counts']):
        print('%-16s %s' % (key, json.dumps(report['counts'][key], sort_keys=True)), flush=True)
    for r in report['below_floor']:
        print('BELOW THE FLOOR: %s (%s) in %s: arrival %s, floor %s, spot %s, %.1f under' % (
            r['name'], r['kind'], r['map'], r['arrival'], r['floor'], r['spot'], r['under']), flush=True)
    if a.out:
        a.out.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
        print('wrote %s' % a.out, flush=True)
    print('Room arrivals: %s, %d checked, %d below the floor (%.1f s)' % (
        report['status'], len(report['rows']), len(report['below_floor']), report['seconds']), flush=True)
    return 1 if report['below_floor'] else 0


if __name__ == '__main__':
    sys.exit(main())
