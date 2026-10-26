#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Door graph: every load door of the game and every interior cell it leads to (docs/chim/DOOR_GRAPH.md).

Phase 1 of converting every interior to a CHIM room (docs/chim/INTERIOR_STORE.md, docs/ROADMAP.md step 3). Reads
your own Morrowind.esm and, when present, Tribunal.esm and Bloodmoon.esm (a missing expansion is a warning, never an
error: docs/ROADMAP.md step 7), merges them in load order as the game does, and writes one JSON (format
aw-door-graph-1): every load door (exterior to interior, interior to interior, interior to exterior), and per
interior cell its master, its island (Vvardenfell, Solstheim, Mournhold or none), its entrances and exits, how it is
reached, and the hard cases a batch conversion sets aside (lava at or under the water, over a CHIM room limit on the
32 MiB minimum machine, behaves like an exterior; teleport-only and unreachable go to the parity batch). Water, lava,
Levitate-only and over the 16 MiB zone are notes: those rooms are converted like any room (v0.0.48).

    python3 tools/door_graph.py graph --data-files DIR --out GRAPH.json [--mesh-cache FILE] [--sdk DIR] [--jobs N]
        parse the masters (every core: each master is cut into record ranges parsed side by side) and write the
        graph. With --mesh-cache, every mesh the rooms place is measured with the asset census functions (cached
        by SHA-256 in FILE, every core) and each room gets its store set (bytes, vertexes) and the zone and vertex
        limit checks. With --sdk too, the store set is also counted as the engine holds it loaded (zone bytes, the
        target's structure sizes) and checked against the 32 MiB minimum machine (CHIM-ROOM-ESTIMATE-48).
    python3 tools/door_graph.py plan --graph GRAPH.json --out PLAN.json [--md PLAN.md] [--config-dir DIR]
        [--batch-rooms N]
        the Vvardenfell rooms that can become CHIM rooms now, in batches in a player's order (towns first, towns
        whose rooms are in the game today first among them; then the other rooms in the game; then the rest by
        region), each batch with the store growth it costs; then a final parity batch of the rooms no door reaches
        (each keeps its state: test cell, teleport only, no entrance and no script); the other hard cases aside with
        their reasons; and one later batch per expansion (its rooms, its parity rooms, why it waits).

    python3 tools/door_graph.py room-batches --plan PLAN.json --graph GRAPH.json --out config/room-batches.json
        [--previous config/room-batches.json]
        the public part of the plan the builder converts by (--room-batches, tools/room_batches.py): per batch its
        rooms by name, their map names, save ids and order, and their entrance cells; nothing else of the game data.

Nothing derived from your files is part of this repository: the graph and the plan are private data (the room list
holds only room names, already public, batch numbers and exterior cell numbers).
"""
import argparse
import collections
import json
import math
import os
import re
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):
    # src first, always: tools/mwad.py (the CLI) would shadow the mwad package when tools/ comes before src/, as it
    # does when PYTHONPATH names both (DOOR-GRAPH-MWAD-SHADOW-48)
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

from mwad.esm import GAME_MASTERS, records, subrecords  # noqa: E402

FORMAT = 'aw-door-graph-1'
PLAN_FORMAT = 'aw-batch-plan-1'
MW_CELL = 8192                     # Morrowind units per exterior cell
ISLANDS = ('Vvardenfell', 'Solstheim', 'Mournhold')
NO_ISLAND = 'none'
TELEPORT_ISLAND = {'Tribunal.esm': 'Mournhold', 'Bloodmoon.esm': 'Solstheim'}
OBJECT_TAGS = frozenset('STAT DOOR MISC WEAP CONT CREA LIGH NPC_ ARMO CLOT REPA ACTI APPA LOCK PROB INGR BOOK '
                        'ALCH LEVI LEVC BODY'.split())
ACTOR_TAGS = frozenset({'NPC_', 'CREA', 'LEVC'})
CELL_HAS_WATER = 0x02
CELL_BEHAVES_EXTERIOR = 0x80
# Levitate-only (an approximate rule, docs/chim/DOOR_GRAPH.md): a load door in a Telvanni room that stands more than
# LEVITATE_RISE Morrowind units above every point where the player arrives in that room cannot be walked to (the
# towers have shafts, not stairs). A room whose every load door in is such a door is Levitate-only.
LEVITATE_RISE = 256.0
# Outdoors (Telvanni settlements walk on raised walkways, so the terrain alone does not tell): a door into a Telvanni
# tower complex more than LEVITATE_TOWER_STEP above the complex's lowest outdoor door, or more than LEVITATE_TOWER_TOP
# above the terrain under it.
LEVITATE_TOWER_STEP = 512.0
LEVITATE_TOWER_TOP = 3072.0
TELVANNI_SHARE = 0.25              # share of the room's architecture placements from the Telvanni interior kit
TELVANNI_KIT = re.compile(r'(^|/)in_t_')
# What sets a room aside (v0.0.48, the maintainer's decisions of 23 October 2026: water, lava and Levitate-only rooms
# are converted like any room and keep a note; the size limit is the zone of the 32 MiB minimum machine)
HARD_REASONS = ('unreachable', 'teleport_only', 'behaves_exterior', 'lava_under_water', 'over_limit')
NOTES = ('levitate_only', 'water', 'lava', 'zone_over_16mb')
ROOM_STATES = ('on_chim_rooms', 'room_map', 'converted', 'not_started', 'hard_case', 'test_cell', 'teleport_only',
               'no_entrance')
TOWN_MIN_ROOMS = 4                 # a named exterior cell with fewer rooms behind its doors is not a town (batch plan)
# Parity (docs/chim/DOOR_GRAPH.md "Rooms set aside, and how they come back"): no room is left out. A room no door reaches
# (unreachable or teleport-only) is converted like any other room in a final parity batch, so it exists in the image and a
# script or a console command can reach it later; it keeps its reason as a state, never an exclusion.
PARITY_REASONS = ('unreachable', 'teleport_only')
PARITY_STATES = collections.OrderedDict((('test_cell', 'test cell'), ('teleport_only', 'teleport only'),
                                         ('no_entrance', 'no entrance, no script')))
# The developers' test cells of the masters (no door reaches them; named in docs/chim/DOOR_GRAPH.md).
TEST_CELLS = frozenset(n.casefold() for n in (
    'Character Stuff Wonderland', 'Clutter Warehouse - Everything Must Go!', 'Draugr Test', "ken's test hole",
    "Mark's Script Testing Cell", "Mark's Vampire Test Cell", 'Redoran interior', 'Redoran interior2', 'ToddTest'))
# The expansions' rooms wait for their land: one later batch per master, with the reason it waits.
LATER = collections.OrderedDict((
    ('Tribunal.esm', ('Mournhold', "Mournhold is reached only by script (Tribunal's teleport): its rooms wait for the "
                                   'scripts step (roadmap step 6)')),
    ('Bloodmoon.esm', ('Solstheim', "Solstheim's exterior (Bloodmoon) is not on CHIM yet: its rooms come in with the "
                                    'island (roadmap step 7)'))))


# ------------------------------------------------------------------ small helpers

def cstr(raw):
    return bytes(raw).split(b'\0', 1)[0].decode('cp1252', 'replace')


def normmodel(model):
    model = (model or '').strip().replace('\\', '/').lower()
    if not model:
        return ''
    return model if model.startswith('meshes/') else 'meshes/' + model


def exterior_of(position):
    """The exterior cell (x, y) a world position lies in."""
    return (int(math.floor(position[0] / MW_CELL)), int(math.floor(position[1] / MW_CELL)))


def ckey(xy):
    return '%d,%d' % tuple(xy)


def resolve_jobs(jobs):
    return max(1, int(jobs)) if jobs else (os.cpu_count() or 1)


# ------------------------------------------------------------------ parsing (one record range per worker)

def record_ranges(path, parts):
    """Cut a master into `parts` byte ranges on record boundaries (record headers only are read).
    Returns (TES3 masters list, [(start, end)])."""
    size = os.path.getsize(path)
    offsets = []
    masters = []
    with open(path, 'rb') as f:
        pos = 0
        while pos < size:
            f.seek(pos)
            head = f.read(16)
            if len(head) < 16:
                raise ValueError('%s: truncated record header at %d' % (path, pos))
            tag, length = struct.unpack_from('<4sI', head)
            if pos == 0:
                if tag != b'TES3':
                    raise ValueError('%s: not a TES3 file' % path)
                masters = [cstr(v) for k, v in subrecords(f.read(length)) if k == 'MAST']
            offsets.append(pos)
            pos += 16 + length
        if pos != size:
            raise ValueError('%s: last record overruns the file' % path)
    offsets.append(size)
    parts = max(1, min(parts, len(offsets) - 1))
    cuts, target = [0], size / parts
    i = 0
    for k in range(1, parts):
        want = target * k
        while i < len(offsets) - 1 and offsets[i] < want:
            i += 1
        if offsets[i] > cuts[-1] and offsets[i] < size:
            cuts.append(offsets[i])
    cuts.append(size)
    return masters, [(a, b) for a, b in zip(cuts, cuts[1:]) if b > a]


def _ref_fields(ref, tag, data):
    if tag == 'NAME':
        ref['id'] = cstr(data).casefold()
    elif tag == 'DATA' and len(data) == 24:
        v = struct.unpack('<6f', data)
        if all(math.isfinite(x) for x in v):
            ref['p'] = list(v[:3])
            ref['r'] = list(v[3:])
    elif tag == 'XSCL' and len(data) == 4:
        ref['s'] = struct.unpack('<f', data)[0]
    elif tag == 'DELE':
        ref['del'] = True
    elif tag == 'DODT' and len(data) == 24:
        v = struct.unpack('<6f', data)
        if all(math.isfinite(x) for x in v):
            ref['dest'] = list(v[:3])
            ref['dest_r'] = list(v[3:])
    elif tag == 'DNAM':
        ref['dcell'] = cstr(data)


def parse_cell(payload, flags):
    """One CELL record: header, then its references. Exterior cells keep only their load doors and deletions."""
    header, refs, ref = {}, [], None
    for tag, data in subrecords(payload):
        if tag == 'FRMR' and len(data) == 4:
            ref = {'n': struct.unpack('<I', data)[0]}
            refs.append(ref)
        elif tag in ('MVRF', 'CNAM', 'CNDT') and ref is None:
            continue
        elif ref is None:
            header.setdefault(tag, data)
        elif tag in ('MVRF', 'CNAM', 'CNDT'):
            # A moved reference: its record follows with its own FRMR; positions are world positions anyway.
            continue
        else:
            _ref_fields(ref, tag, data)
    if len(header.get('DATA', b'')) != 12:
        return None
    cflags, x, y = struct.unpack('<Iii', header['DATA'])
    interior = bool(cflags & 1)
    water = None
    if 'WHGT' in header and len(header['WHGT']) == 4:
        water = struct.unpack('<f', header['WHGT'])[0]
    elif 'INTV' in header and len(header['INTV']) == 4:
        water = float(struct.unpack('<i', header['INTV'])[0])
    if water is not None and not math.isfinite(water):
        water = None
    if not interior:
        refs = [r for r in refs if 'dest' in r or r.get('del')]
    return {'interior': interior, 'flags': cflags, 'x': x, 'y': y, 'name': cstr(header.get('NAME', b'')),
            'region': cstr(header.get('RGNN', b'')), 'water': water,
            'deleted': bool(flags & 0x20) or 'DELE' in header, 'refs': refs}


def parse_range(task):
    """Worker: the objects, scripts, quoted cell names and cells of one record range of one master."""
    import lava
    path, start, end = task
    with open(path, 'rb') as f:
        f.seek(start)
        raw = f.read(end - start)
    objects, contracts, quoted, cells, lands = {}, {}, set(), [], {}
    for tag, flags, payload in records(raw):
        if tag in OBJECT_TAGS:
            s = {}
            for k, v in subrecords(payload):
                s.setdefault(k, v)
            if 'NAME' not in s:
                continue
            key = cstr(s['NAME']).casefold()
            if 'DELE' in s or flags & 0x20:
                objects[key] = None
                continue
            objects[key] = [tag, normmodel(cstr(s.get('MODL', b''))), cstr(s.get('SCRI', b'')).casefold()]
        elif tag == 'SCPT':
            s = {}
            for k, v in subrecords(payload):
                s.setdefault(k, v)
            text = s.get('SCTX', b'').decode('cp1252', 'replace')
            quoted.update(q.casefold() for q in re.findall(r'"([^"\n]+)"', text))
            name = cstr(s.get('SCHD', b'')[:32]).casefold()
            dps, _sound = lava.script_contract(text)
            if name and dps > 0:
                contracts[name] = dps
        elif tag == 'INFO':
            for k, v in subrecords(payload):
                if k == 'BNAM':
                    quoted.update(q.casefold() for q in re.findall(r'"([^"\n]+)"', v.decode('cp1252', 'replace')))
        elif tag == 'CELL':
            c = parse_cell(payload, flags)
            if c is not None:
                cells.append(c)
        elif tag == 'LAND':
            s = dict(subrecords(payload))
            if len(s.get('INTV', b'')) == 8 and len(s.get('VHGT', b'')) == 4232:
                lands[struct.unpack('<ii', s['INTV'])] = bytes(s['VHGT'])
    return {'objects': objects, 'contracts': contracts, 'quoted': sorted(quoted), 'cells': cells, 'lands': lands}


def find_masters(data_files, warn=print):
    """[(name, path)] of the present masters in load order; Morrowind.esm is required."""
    from mwad.paths import child_ci
    out = []
    for name in GAME_MASTERS:
        path = child_ci(Path(data_files), name, required=False)
        if path is None or not path.is_file():
            if name == GAME_MASTERS[0]:
                raise ValueError('Morrowind.esm not found in %s' % data_files)
            warn('door graph: WARNING: %s is missing; its cells and doors are left out (expansions are optional)'
                 % name)
            continue
        out.append((name, path))
    return out


def parse_masters(data_files, jobs=None, warn=print, timings=None):
    """Every present master parsed on every core: each master is cut into record ranges, all ranges of all masters
    run side by side (build_parallel.ordered_map), results merged in load order."""
    from build_parallel import ordered_map
    from mwad.esm import sha256_file
    jobs = resolve_jobs(jobs)
    present = find_masters(data_files, warn)
    sizes = {name: os.path.getsize(path) for name, path in present}
    total = sum(sizes.values())
    tasks, owner, mast = [], [], {}
    for name, path in present:
        parts = max(1, round(jobs * 2 * sizes[name] / total))
        masters, ranges = record_ranges(path, parts)
        mast[name] = masters
        for a, b in ranges:
            tasks.append((str(path), a, b))
            owner.append(name)
    started = time.monotonic()
    results = list(ordered_map(parse_range, tasks, jobs, cost=lambda t: t[2] - t[1]))
    hashes = list(ordered_map(sha256_file, [str(p) for _, p in present], jobs, cost=os.path.getsize))
    if timings is not None:
        timings['parse_seconds'] = round(time.monotonic() - started, 3)
        timings['ranges'] = len(tasks)
        timings['workers'] = jobs
    parsed = collections.OrderedDict((name, {'objects': {}, 'contracts': {}, 'quoted': set(), 'cells': [],
                                             'lands': {}, 'masters': mast[name], 'sha256': h, 'bytes': sizes[name]})
                                     for (name, _), h in zip(present, hashes))
    for name, res in zip(owner, results):
        m = parsed[name]
        m['lands'].update(res['lands'])
        m['objects'].update(res['objects'])
        m['contracts'].update(res['contracts'])
        m['quoted'].update(res['quoted'])
        m['cells'].extend(res['cells'])
    return parsed


# ------------------------------------------------------------------ merging (the game's load order)

def merge(parsed):
    """Objects, molten objects, quoted names and cells over every master, later masters overriding earlier ones.
    A reference is keyed by (owning master, index): FRMR's high byte names the master it changes (0 = this file)."""
    objects, contracts, quoted, lands = {}, {}, set(), {}
    interiors, exteriors = collections.OrderedDict(), {}
    for name, m in parsed.items():
        lands.update(m['lands'])
        for k, o in m['objects'].items():
            if o is None:
                objects.pop(k, None)
            else:
                objects[k] = o
        contracts.update(m['contracts'])
        quoted |= set(m['quoted'])
        for c in m['cells']:
            key = c['name'].casefold() if c['interior'] else (c['x'], c['y'])
            if c['interior'] and not c['name']:
                continue
            table = interiors if c['interior'] else exteriors
            refs = collections.OrderedDict()
            for r in c['refs']:
                hi, lo = r['n'] >> 24, r['n'] & 0xffffff
                own = name if hi == 0 or hi > len(m['masters']) else m['masters'][hi - 1]
                refs[(own, lo)] = r
            have = table.get(key)
            if have is None:
                table[key] = dict(c, refs=refs, master=name, modified_by=[])
                continue
            have['modified_by'].append(name)
            for f in ('flags', 'water', 'region', 'deleted', 'name'):
                if c.get(f) not in (None, '') or f in ('flags', 'deleted'):
                    have[f] = c[f]
            if c['water'] is None and not c['flags'] & CELL_HAS_WATER:
                have['water'] = None
            for k, r in refs.items():
                have['refs'][k] = r
    for table in (interiors, exteriors):
        for c in table.values():
            c['refs'] = [r for r in c['refs'].values() if not r.get('del') and r.get('id')]
    molten = {k for k, o in objects.items() if o[2] and o[2] in contracts}
    return objects, molten, quoted, interiors, exteriors, lands


def solstheim_box(parsed, exteriors):
    """(xmin, xmax, ymin, ymax) of the exterior cells Bloodmoon.esm adds, one cell of margin; None without it."""
    added = [c for c in exteriors.values() if c['master'] == 'Bloodmoon.esm']
    if not added:
        return None
    xs = [c['x'] for c in added]
    ys = [c['y'] for c in added]
    return (min(xs) - 1, max(xs) + 1, min(ys) - 1, max(ys) + 1)


def island_of(xy, box):
    if box and box[0] <= xy[0] <= box[1] and box[2] <= xy[1] <= box[3]:
        return 'Solstheim'
    return 'Vvardenfell'


# ------------------------------------------------------------------ the graph

def door_rows(objects, interiors, exteriors):
    """Every live load door: (source key, interior?, ref, door object, position, destination key, interior?, dest)."""
    out = []
    for interior, table in ((True, interiors), (False, exteriors)):
        for key, c in table.items():
            if c['deleted']:
                continue
            for r in c['refs']:
                if 'dest' not in r or 'p' not in r:
                    continue
                o = objects.get(r['id'])
                if o is None:
                    continue
                target = (r.get('dcell') or '').casefold()
                out.append({'from': key, 'from_interior': interior, 'ref': r['n'], 'object': r['id'],
                            'model': o[1], 'pos': r['p'], 'to': target or exterior_of(r['dest']),
                            'to_interior': bool(target), 'dest': r['dest'],
                            'dest_yaw': (r.get('dest_r') or [0, 0, 0])[2]})
    return out


def door_kind(d):
    side = ('exterior', 'interior')
    return side[d['from_interior']] + '_to_' + side[d['to_interior']]


def room_contents(c, objects, molten):
    from mwad.interior import omission_reason
    counts = collections.Counter()
    kept, models, kept_models = 0, set(), set()
    arch = telvanni = 0
    lava = 0
    for r in c['refs']:
        o = objects.get(r['id'])
        if o is None:
            continue
        tag, model = o[0], o[1]
        counts[tag] += 1
        if r['id'] in molten:       # a lava name or texture alone is not molten (lava-rock caves): tools/lava.py
            lava += 1
        if model:
            models.add(model)
            if omission_reason({'number': r['n'], 'id': r['id'], 'type': tag, 'model': model[len('meshes/'):]}) is None:
                kept += 1
                kept_models.add(model)
            if tag == 'STAT' and '/in_' in '/' + model.rsplit('/', 1)[-1]:
                arch += 1
                telvanni += bool(TELVANNI_KIT.search(model))
    return {'counts': dict(sorted(counts.items())), 'placements': sum(1 for r in c['refs'] if
                                                                        (objects.get(r['id']) or [0, ''])[1]),
            'kept_placements': kept, 'models': sorted(models), 'kept_models': sorted(kept_models),
            'actors': sum(counts[t] for t in ACTOR_TAGS), 'lights': counts['LIGH'], 'lava': lava,
            'telvanni': bool(arch) and telvanni / arch >= TELVANNI_SHARE}


def reach(rooms, doors, quoted):
    """Breadth-first from every exterior load door, then from every room a script or dialogue names."""
    out_edges = collections.defaultdict(list)
    for d in doors:
        if d['from_interior'] and d['to_interior']:
            out_edges[d['from']].append(d)
    into = collections.Counter(d['to'] for d in doors if d['to_interior'])
    info = {k: {'access': 'unreachable', 'depth': None, 'root': None} for k in rooms}
    queue = collections.deque()
    for d in sorted((d for d in doors if not d['from_interior'] and d['to_interior']),
                    key=lambda d: (d['from'], d['ref'])):
        k = d['to']
        if k in info and info[k]['depth'] is None:
            info[k].update(access='door', depth=1, root=('exterior', d['from']))
            queue.append(k)

    def walk(access):
        while queue:
            k = queue.popleft()
            for d in out_edges.get(k, ()):
                t = d['to']
                if t in info and info[t]['depth'] is None:
                    info[t].update(access=access, depth=info[k]['depth'] + 1, root=info[k]['root'])
                    queue.append(t)
    walk('door')
    for k in sorted(rooms):
        if info[k]['depth'] is None and k in quoted:
            info[k].update(access='teleport' if into[k] else 'teleport_only', depth=0, root=('teleport', k))
            queue.append(k)
    walk('teleport')
    for k in rooms:
        info[k]['door_in'] = into[k] > 0
    return info


def land_height(lands, position):
    """Terrain height (Morrowind units) at a world position: the nearest LAND vertex; None without LAND."""
    xy = exterior_of(position)
    vhgt = lands.get(xy)
    if vhgt is None:
        return None
    col = min(64, max(0, int(round((position[0] - xy[0] * MW_CELL) / 128.0))))
    row = min(64, max(0, int(round((position[1] - xy[1] * MW_CELL) / 128.0))))
    # VHGT: a base offset, then 65 x 65 signed deltas; the first column runs down the rows, each row along x.
    h = struct.unpack_from('<f', vhgt)[0]
    d = vhgt[4:4 + 65 * 65]
    for r in range(row + 1):
        h += struct.unpack_from('b', d, r * 65)[0]
    for c in range(1, col + 1):
        h += struct.unpack_from('b', d, row * 65 + c)[0]
    return h * 8.0


def levitate_doors(rooms, doors, contents, lands):
    """Load doors into or inside a Telvanni room that a walking player cannot reach (docs/chim/DOOR_GRAPH.md):
    - inside a Telvanni room: higher than LEVITATE_RISE above every point where the player arrives in that room
      through a door not needing Levitate, from anywhere except the door's own target (coming back down from a
      room does not get you up to it);
    - outdoors, leading into a Telvanni room: more than LEVITATE_TOWER_STEP above the lowest outdoor door into the
      same tower complex (rooms joined by interior doors), or more than LEVITATE_TOWER_TOP above the terrain."""
    # Tower complexes: rooms joined by interior doors. The lowest outdoor door into a complex is its foot.
    parent = {k: k for k in rooms}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k
    for d in doors:
        if d['from_interior'] and d['to_interior'] and d['from'] in rooms and d['to'] in rooms:
            parent[find(d['from'])] = find(d['to'])
    foot = {}
    for d in doors:
        if not d['from_interior'] and d['to_interior'] and d['to'] in rooms:
            c = find(d['to'])
            foot[c] = min(foot.get(c, d['pos'][2]), d['pos'][2])
    high = set()
    for d in doors:
        if not d['from_interior'] and d['to_interior'] and d['to'] in rooms and contents[d['to']]['telvanni']:
            ground = land_height(lands, d['pos'])
            if d['pos'][2] - foot[find(d['to'])] > LEVITATE_TOWER_STEP or (
                    ground is not None and d['pos'][2] - ground > LEVITATE_TOWER_TOP):
                high.add((d['from'], d['ref']))
    # Inside: only arrivals through doors a walking player can use count, so repeat until nothing changes (each
    # round can only add Levitate doors: fewer arrivals, lower floors).
    inside = [d for d in doors if d['from_interior'] and d['from'] in rooms and contents[d['from']]['telvanni']]
    while True:
        arrivals = collections.defaultdict(list)
        for d in doors:
            if d['to_interior'] and (d['from'], d['ref']) not in high:
                arrivals[d['to']].append((d['from'], d['dest'][2]))
        added = False
        for d in inside:
            key = (d['from'], d['ref'])
            if key in high:
                continue
            walk_in = [z for src, z in arrivals.get(d['from'], ()) if src != d['to']]
            if walk_in and d['pos'][2] - max(walk_in) > LEVITATE_RISE:
                high.add(key)
                added = True
        if not added:
            return high


def walkable(rooms, doors, high):
    """Rooms a player reaches on foot: over load doors from the exterior that are not Levitate doors."""
    edges = collections.defaultdict(list)
    for d in doors:
        if d['to_interior'] and (d['from'], d['ref']) not in high:
            edges[d['from'] if d['from_interior'] else None].append(d['to'])
    seen, stack = set(), [None]
    while stack:
        k = stack.pop()
        for t in edges.get(k, ()):
            if t in rooms and t not in seen:
                seen.add(t)
                stack.append(t)
    return seen


def room_limits(source=None):
    """The CHIM room limits from the engine sources (chim/chim_room.c and the headers it uses)."""
    # Imported here, not at the top: engine_limits names the whole engine source folder, so a top-level import made
    # every stage that reads this module (the tracker data stage, cell-progress) count engine edits
    # (BUILD-CELL-PROGRESS-ENGINE-KEY-48). Fast RAM: the safe minimum and the baseline that still starts; a room's
    # set is checked against what the minimum gives a room, the baseline's fit is reported.
    import engine_limits as EL
    from engine_limits import BASELINE_FAST_RAM_MIB, MIN_FAST_RAM_MIB
    src = Path(source) if source else EL.SOURCE
    room_c = (src / 'chim/chim_room.c').read_text(encoding='utf-8', errors='replace')
    m = re.search(r'h\.count\s*>\s*(\d+)', room_c)
    if not m:
        raise ValueError('chim_room.c: the placement count limit (h.count > N) not found')
    record_max = int(m.group(1))
    reserve = EL.define('chim/chim_local.h', 'CHIM_EFRAG_RESERVE', src)
    efrag_limit = EL.define('client.h', 'AW_EFRAG_LIMIT', src) - reserve
    from chim.heap import room_zone_limits
    small = EL.fast_ram_memory(BASELINE_FAST_RAM_MIB, src)
    safe = EL.fast_ram_memory(MIN_FAST_RAM_MIB, src)
    # the image's room heap gate's model (chim.heap.room_zone_limits) for a room map before which the Hunk holds the
    # measured start-up bytes and after which the client's measured per-map allocations load (ROOM-AKULAKHAN-HEAP-52)
    gate = room_zone_limits(EL.MEASURED_HUNK['before_map_bytes'], EL.MEASURED_HUNK['client_per_map_bytes'], source=src)
    return {'source': 'engine/aga/src: chim/chim_room.c, chim/chim_local.h, client.h, quakedef.h, bspfile.h, '
                      'chim/chim_world.c, chim/chim_zone.h, aw_heapsize.h, sys_amiga.c',
            'placements_record_max': record_max,
            # ChimRoom_Link: a placement waits once used efrags + CHIM_EFRAG_RESERVE/4 pass chim_efrag_limit; every
            # placement takes at least one efrag.
            'placements_linked_max': efrag_limit - reserve // 4,
            'room_map_edicts_max': EL.define('quakedef.h', 'MAX_EDICTS', src),
            'model_vertexes_max': EL.define('bspfile.h', 'MAX_MAP_VERTS', src),
            # Every model of the room loads whole (chim_room.c). A room map has no frame world, so it keeps no
            # frame-world pool blocks: the room has the whole zone less the loading buffer (chim_world.c). Models
            # and textures prefer the automatic cache banks (chim_zone.c AllocIn), so with more Fast RAM the room
            # holds the banks as well (CHIM-ROOM-ESTIMATE-48); a room past them grows into the free Fast RAM and the
            # Hunk's rest (chim_world.c Chim_RoomGrow, ROOM-AKULAKHAN-HEAP-52).
            'zone_room_bytes': gate['zone_room_bytes'],
            'min_fast_ram_mib': MIN_FAST_RAM_MIB,
            'room_bytes_min_fast': gate['min_fast_room_bytes'],
            # one model is one block: the largest a room's model can be is the largest of the zone and the banks
            'block_bytes_min_fast': gate['block_bytes_min_fast'],
            'fast_ram': {str(BASELINE_FAST_RAM_MIB): small, str(MIN_FAST_RAM_MIB): safe}}


def lava_under_water(data_files, cell, water):
    """Why a room with water and lava cannot be a CHIM room yet, or None: a lava pool whose bed reaches the water
    level (chim.interior.room_liquids: water and lava in one leaf are not carved). The pools come from the game data
    as the room converter makes them (tools/lava.py pools_of on the room's references, the master that adds it); a
    room it cannot read is held with that reason (never guessed)."""
    import lava
    from mwad.interior import read_interiors
    from mwad.paths import child_ci
    try:
        master = child_ci(Path(data_files), cell['master'])
        room = read_interiors(master, [cell['name']])[0]
        pools = lava.pools_of(data_files, room['refs'], lava.molten_objects_of(master))
    except Exception as error:  # noqa: BLE001 (named, the room is held)
        return 'lava and water not checked: %s: %s' % (type(error).__name__, error)
    level = water * 0.25
    low = [round(p['top'] * 0.25 - lava.LIQUID_DEPTH - lava.BED_THICKNESS, 2) for p in pools]
    under = [v for v in low if v < level]
    if under:
        return 'lava at or under the water level: %d of %d pools reach %.2f (water %.2f, Quake units)' % (
            len(under), len(pools), min(under), level)
    return None


def over_limit(room, limits, sizes):
    """Which CHIM room limits a room passes (names), from its placements and, when measured, its store set.
    zone_bytes: the room's need (store_set 'need_bytes') over what a machine with the minimum Fast RAM gives a room
    ('room_bytes_min_fast'); the 16 MiB baseline's zone alone is reported per room ('fits_16mb'), not a limit."""
    out = []
    if room['kept_placements'] > min(limits['placements_record_max'], limits['placements_linked_max']):
        out.append('placements')
    if room['actors'] + room['lights'] + room['load_doors'] > limits['room_map_edicts_max']:
        out.append('room_map_entities')
    if sizes is not None:
        need = sizes.get('need_bytes', sizes['bytes'])
        if need > limits.get('room_bytes_min_fast', limits['zone_room_bytes']):
            out.append('zone_bytes')
        if sizes.get('largest_model_zone_bytes', 0) > limits.get('block_bytes_min_fast', 1 << 62):
            out.append('model_block')
        if sizes['largest_model_vertexes'] > limits['model_vertexes_max']:
            out.append('model_vertexes')
    return out


def model_zone_bytes(c, sizes):
    """The zone block one store model takes when loaded (chim.heap.image_bytes, point hull only), estimated from its
    asset census counts (CHIM-ROOM-ESTIMATE-48): the engine's in-memory structures (msurface, mtexinfo, mplane, ...
    from the target compiler), not the BSP29 lumps on disk. Measured against the 43 Balmora rooms of the CHIM rooms
    sandbox (23 October 2026): 0.82 to 1.05 of the measured blocks, 0.92 in all (DOOR_GRAPH.md)."""
    def a16(x):
        return (int(x) + 15) & ~15
    faces, nodes = c['faces'], c['nodes']
    arena = sum(a16(x) for x in (
        c['vertexes'] * sizes['mvertex'], (c['edges'] + 1) * sizes['medge'], c['surfedges'] * sizes['int'],
        len(c['textures']) * sizes['pointer'], c['clipnodes'] * sizes['dclipnode'],
        (c['planes'] + c['cplanes']) * sizes['mplane'], c['texinfo'] * sizes['mtexinfo'], faces * sizes['msurface'],
        faces * sizes['pointer'], (nodes + 1) * sizes['mleaf'], sizes['dmodel'], nodes * sizes['dclipnode']))
    return sizes['hunk'] + a16(sizes['model'] + arena)


def placement_zone_bytes(sizes):
    """One placement of a room record in the zone (chim_room.c): its record (56), its matrix (9 floats) and its
    run-time placement (an entity plus an allowance of 64 for its drawn box, yaw and links)."""
    return 56 + 9 * sizes['float'] + sizes['entity'] + 64


def mesh_table(data_files, models, cache, jobs, progress=print, sizes=None):
    """{model: {'bytes', 'geometry', 'hull', 'vertexes', 'textures': {key: bytes}, 'status'}} with the asset census
    functions (interior profile), every core, cached by SHA-256. With the target's structure sizes (sizes, from
    check_world_map_heap.compile_target_sizes) each row also has 'zone' (model_zone_bytes) and 'texture_zone'
    ({key: zone bytes}, chim.heap.texture_bytes)."""
    import asset_census as A
    rows = A.scan_meshes(data_files, sorted(models), cache, jobs, progress)
    out = {}
    for m, row in rows.items():
        c = A._bytes_of(rows, m, 'interior')
        if c is None:
            out[m] = {'status': row.get('status') or 'error', 'bytes': 0, 'geometry': 0, 'hull': 0, 'vertexes': 0,
                      'textures': {}}
            continue
        tex = {t: A.miptex_bytes(int(t.split('|')[1])) for t in c['textures']}
        g, h = A.geometry_bytes(c), A.hull_bytes(c)
        out[m] = {'status': 'ok', 'geometry': g, 'hull': h, 'bytes': g + h, 'vertexes': c['vertexes'],
                  'textures': tex}
        if sizes is not None:
            from chim.heap import texture_bytes
            out[m]['zone'] = model_zone_bytes(c, sizes)
            out[m]['texture_zone'] = {t: texture_bytes(int(t.split('|')[1]), int(t.split('|')[1]), sizes)
                                      for t in c['textures']}
    return out


def store_set(models, meshes, placements=0, sizes=None):
    """Bytes of a room's store set: its unique models (render + collision) and their unique textures (the asset
    census bytes, BSP29 on disk). With zone figures in the rows (mesh_table with sizes): 'zone_bytes', what its
    models and textures take loaded, and 'need_bytes', that plus its placements (placement_zone_bytes)."""
    tex, total, verts, largest, missing = {}, 0, 0, 0, 0
    zone, tex_zone, block = 0, {}, 0
    for m in models:
        row = meshes.get(m)
        if not row or row['status'] != 'ok':
            missing += 1
            continue
        total += row['bytes']
        verts += row['vertexes']
        largest = max(largest, row['vertexes'])
        tex.update(row['textures'])
        if 'zone' in row:
            zone += row['zone']
            block = max(block, row['zone'])
            tex_zone.update(row['texture_zone'])
    out = {'bytes': total + sum(tex.values()), 'model_bytes': total, 'texture_bytes': sum(tex.values()),
           'textures': len(tex), 'vertexes': verts, 'largest_model_vertexes': largest, 'models_unmeasured': missing}
    if sizes is not None:
        out['zone_bytes'] = zone + sum(tex_zone.values())
        out['zone_model_bytes'] = zone
        out['zone_texture_bytes'] = sum(tex_zone.values())
        out['largest_model_zone_bytes'] = block
        out['need_bytes'] = out['zone_bytes'] + placements * placement_zone_bytes(sizes)
    return out


def build_graph(data_files, jobs=None, mesh_cache=None, warn=print, engine_source=None, target_sizes=None):
    timings = {}
    t0 = time.monotonic()
    parsed = parse_masters(data_files, jobs, warn, timings)
    objects, molten, quoted, interiors, exteriors, lands = merge(parsed)
    box = solstheim_box(parsed, exteriors)
    doors = door_rows(objects, interiors, exteriors)
    rooms = {k: c for k, c in interiors.items() if not c['deleted']}
    contents = {k: room_contents(c, objects, molten) for k, c in rooms.items()}
    info = reach(rooms, doors, quoted)
    high = levitate_doors(rooms, doors, contents, lands)
    on_foot = walkable(rooms, doors, high)
    limits = room_limits(engine_source)
    meshes = None
    if mesh_cache:
        t1 = time.monotonic()
        used = {m for c in contents.values() for m in c['kept_models']}
        meshes = mesh_table(data_files, used, mesh_cache, resolve_jobs(jobs), warn, sizes=target_sizes)
        timings['mesh_seconds'] = round(time.monotonic() - t1, 3)
        timings['meshes'] = len(used)
    entrances, exits = collections.defaultdict(list), collections.defaultdict(list)
    for d in doors:
        if d['to_interior']:
            entrances[d['to']].append(d)
        if d['from_interior']:
            exits[d['from']].append(d)

    def label(key, interior):
        if interior:
            return rooms[key]['name'] if key in rooms else key
        return ckey(key)

    # Island and settlement: the exterior cell its door chain starts from; teleport roots of Tribunal are Mournhold.
    def place(k):
        root = info[k]['root']
        if root is None:
            return NO_ISLAND, None, None
        if root[0] == 'exterior':
            ext = exteriors.get(root[1]) or {}
            return (island_of(root[1], box), ckey(root[1]),
                    {'name': ext.get('name', ''), 'region': ext.get('region', '')})
        # A room reached by script: the expansion that adds it names its land (Mournhold is reached only so).
        return TELEPORT_ISLAND.get(rooms[root[1]]['master'], NO_ISLAND), None, None
    out_rooms = []
    for k in sorted(rooms, key=lambda n: n):
        c, ct, inf = rooms[k], contents[k], info[k]
        island, ext_cell, ext_info = place(k)
        ins = entrances.get(k, [])
        outs = exits.get(k, [])
        water = bool(c['flags'] & CELL_HAS_WATER) and c['water'] is not None
        room = {'name': c['name'], 'master': c['master'], 'modified_by': c['modified_by'], 'island': island,
                'entrance_exterior': ext_cell, 'settlement': (ext_info or {}).get('name') or None,
                'region': (ext_info or {}).get('region') or c['region'] or None,
                'access': inf['access'], 'door_in': inf['door_in'], 'depth': inf['depth'],
                'entrances': [{'from': label(d['from'], d['from_interior']), 'from_interior': d['from_interior'],
                               'ref': d['ref'], 'levitate': (d['from'], d['ref']) in high} for d in ins],
                'exits': [{'to': label(d['to'], d['to_interior']), 'to_interior': d['to_interior'], 'ref': d['ref']}
                          for d in outs],
                'water': {'flag': bool(c['flags'] & CELL_HAS_WATER), 'height': c['water']} if water else None,
                'behaves_exterior': bool(c['flags'] & CELL_BEHAVES_EXTERIOR),
                'counts': ct['counts'], 'placements': ct['placements'], 'kept_placements': ct['kept_placements'],
                'actors': ct['actors'], 'lights': ct['lights'], 'lava': ct['lava'], 'telvanni': ct['telvanni'],
                'load_doors': len(outs), 'models': ct['kept_models'], 'unique_meshes': len(ct['models'])}
        sizes = (store_set(ct['kept_models'], meshes, ct['kept_placements'], target_sizes)
                 if meshes is not None else None)
        room['store_set'] = sizes
        if sizes is not None and 'need_bytes' in sizes:
            room['fits_16mb'] = sizes['need_bytes'] <= limits['zone_room_bytes']
        room['over_limit'] = over_limit(room, limits, sizes)
        hard, notes = [], []
        if inf['access'] == 'unreachable':
            hard.append('unreachable')
        if inf['access'] == 'teleport_only':
            hard.append('teleport_only')
        # Levitate-only, water and lava rooms are converted like any room (the maintainer's decisions of 23 October
        # 2026: CHIM rooms carry their water and lava; a Levitate-only room is in, not reachable on foot until the
        # spell exists): notes, not hard cases
        if inf['access'] == 'door' and k not in on_foot:
            notes.append('levitate_only')
        if room['behaves_exterior']:
            hard.append('behaves_exterior')
        if water:
            notes.append('water')
        if ct['lava']:
            notes.append('lava')
        if water and ct['lava']:
            under = lava_under_water(data_files, c, c['water'])
            if under:
                # converted like any room since 23 October 2026: the CHIM room liquids carve such a pool into the
                # water (chim.interior.liquid_world); a note with the numbers (CHIM-ROOM-LAVA-UNDER-WATER-48)
                notes.append('lava_under_water')
                room['lava_under_water'] = under
        if room['over_limit']:
            hard.append('over_limit')
        if room.get('fits_16mb') is False:
            notes.append('zone_over_16mb')        # loads with the 32 MB machine's bank, not on 16 MB
        room['hard'] = hard
        room['notes'] = notes
        out_rooms.append(room)
    kinds = collections.Counter(door_kind(d) for d in doors)
    dangling = sum(1 for d in doors if d['to_interior'] and d['to'] not in rooms)
    timings['total_seconds'] = round(time.monotonic() - t0, 3)
    summary = summarize(out_rooms, kinds, dangling, len(high))
    return {'format': FORMAT, 'generator': 'tools/door_graph.py',
            'masters': [{'name': n, 'sha256': m['sha256'], 'bytes': m['bytes'], 'masters': m['masters']}
                        for n, m in parsed.items()],
            'missing_masters': [n for n in GAME_MASTERS if n not in parsed],
            'solstheim_cells': list(box) if box else None, 'limits': limits,
            'rules': {'levitate_rise': LEVITATE_RISE, 'levitate_tower_step': LEVITATE_TOWER_STEP,
                      'levitate_tower_top': LEVITATE_TOWER_TOP, 'telvanni_share': TELVANNI_SHARE,
                      'telvanni_kit': TELVANNI_KIT.pattern},
            'timings': timings, 'summary': summary,
            'doors': [{'kind': door_kind(d), 'from': label(d['from'], d['from_interior']), 'ref': d['ref'],
                       'object': d['object'], 'pos': [round(v, 1) for v in d['pos']],
                       'to': label(d['to'], d['to_interior']) if not d['to_interior'] or d['to'] in rooms else d['to'],
                       'dest': [round(v, 1) for v in d['dest']], 'dangling': d['to_interior'] and d['to'] not in rooms,
                       'levitate': (d['from'], d['ref']) in high} for d in doors],
            'meshes': ({m: {k: v for k, v in r.items() if k not in ('textures', 'texture_zone')}
                        for m, r in sorted(meshes.items())}
                       if meshes is not None else None),
            'textures': ({t: b for r in meshes.values() for t, b in r['textures'].items()}
                         if meshes is not None else None),
            'mesh_textures': ({m: sorted(r['textures']) for m, r in sorted(meshes.items())}
                              if meshes is not None else None),
            'rooms': out_rooms}


def summarize(rooms, kinds, dangling, levitate_doors_count):
    per_master = collections.Counter(r['master'] for r in rooms)
    per_island = collections.Counter(r['island'] for r in rooms)
    access = collections.Counter(r['access'] for r in rooms)
    hard = collections.Counter(h for r in rooms for h in r['hard'])
    limits = collections.Counter(x for r in rooms for x in r['over_limit'])
    return {'rooms': len(rooms), 'per_master': dict(sorted(per_master.items())),
            'per_island': dict(sorted(per_island.items())), 'doors': dict(sorted(kinds.items())),
            'doors_total': sum(kinds.values()), 'dangling_doors': dangling, 'levitate_doors': levitate_doors_count,
            'access': dict(sorted(access.items())),
            'reachable': sum(1 for r in rooms if r['access'] != 'unreachable'),
            'unreachable': access['unreachable'], 'door_in': sum(1 for r in rooms if r['door_in']),
            'hard': dict(sorted(hard.items())), 'over_limit': dict(sorted(limits.items())),
            'hard_rooms': sum(1 for r in rooms if r['hard']),
            'notes': dict(sorted(collections.Counter(n for r in rooms for n in r.get('notes', ())).items()))}


# ------------------------------------------------------------------ the batch plan

def our_rooms(config_dir):
    """{interior name (casefold): our map} of the rooms in the game today (the repo's scene lists)."""
    import cell_progress
    return cell_progress.our_maps(config_dir)


def parity_state(room):
    """The state of a room no door reaches (test_cell, teleport_only, no_entrance), else None."""
    hard = room.get('hard') or ()
    if not any(h in hard for h in PARITY_REASONS):
        return None
    if room['name'].casefold() in TEST_CELLS:
        return 'test_cell'
    return 'teleport_only' if 'teleport_only' in hard else 'no_entrance'


def in_vvardenfell_plan(room):
    """The plan's rooms: the rooms whose door chain starts on Vvardenfell, and every room of the base game
    (Morrowind.esm) wherever its chain starts or when none does (the maintainer's milestone of 23 October 2026: every
    interior of the base game, test cells included). The expansions' other rooms wait in their later batches."""
    return room['island'] == 'Vvardenfell' or room['master'] == GAME_MASTERS[0]


def later_master(room):
    """The expansion whose later batch holds a room outside the Vvardenfell plan (by its land, else its master)."""
    for master, (island, _) in LATER.items():
        if room['island'] == island:
            return master
    return room['master'] if room['master'] in LATER else None


def parity_order(room):
    return list(PARITY_STATES).index(parity_state(room)), room['name'].casefold()


def parity_rows(rooms):
    return [{'room': r['name'], 'state': parity_state(r), 'label': PARITY_STATES[parity_state(r)],
             'reasons': list(r['hard']), 'master': r['master'], 'island': r['island']}
            for r in sorted(rooms, key=parity_order)]


def plan(graph, config_dir=None, batch_rooms=40, chim_rooms=()):
    """Vvardenfell rooms to convert now, in batches in a player's order, with the store growth of each batch."""
    in_game = our_rooms(config_dir) if config_dir else {}
    chim_rooms = {n.casefold() for n in chim_rooms}
    # Vvardenfell: the rooms whose door chain starts there, and the base game's rooms with no island (reached by
    # script or not at all: they can only be hard cases).
    rooms = [r for r in graph['rooms'] if in_vvardenfell_plan(r)]
    ready = [r for r in rooms if not r['hard']]
    parity = [r for r in rooms if parity_state(r)]
    aside = [r for r in rooms if r['hard'] and not parity_state(r)]
    # A town: a named exterior cell with at least TOWN_MIN_ROOMS rooms behind its doors (a lone named ruin or
    # tomb goes with its region).
    size = collections.Counter(r['settlement'] for r in rooms if r['settlement'])
    towns = {name for name, n in size.items() if n >= TOWN_MIN_ROOMS}
    town_in_game = {r['settlement'] for r in ready if r['settlement'] in towns and r['name'].casefold() in in_game}

    def tier(r):
        if r['settlement'] in towns:
            return 0 if r['settlement'] in town_in_game else 1
        return 2 if r['name'].casefold() in in_game else 3
    def group(r):
        return r['settlement'] if tier(r) < 2 else (r['region'] or 'no region')
    groups = collections.OrderedDict()
    for r in sorted(ready, key=lambda r: (tier(r), -size[r['settlement']] if tier(r) < 2 else 0, group(r),
                                          r['depth'] or 0, r['name'].casefold())):
        groups.setdefault((tier(r), group(r)), []).append(r)
    meshes = graph.get('meshes') or {}
    textures = graph.get('textures') or {}
    mesh_tex = graph.get('mesh_textures') or {}
    have_m, have_t = set(), set()
    batches = []
    tier_names = ('town with rooms in the game', 'town', 'in the game', 'region', 'parity')
    # A group larger than a batch is split; small groups of one kind share a batch, in order, up to its size.
    packed = []
    for (t, name), members in groups.items():
        if len(members) > batch_rooms:
            parts = -(-len(members) // batch_rooms)          # even parts, none over the batch size
            cuts = [len(members) * k // parts for k in range(parts + 1)]
            for k in range(parts):
                packed.append([t, [name], k + 1, members[cuts[k]:cuts[k + 1]]])
        elif packed and packed[-1][0] == t and packed[-1][2] == 0 and len(packed[-1][3]) + len(members) <= batch_rooms:
            packed[-1][1].append(name)
            packed[-1][3] += members
        else:
            packed.append([t, [name], 0, list(members)])
    # The final parity batch: every room no door reaches, converted like any room (it keeps its reason as a state).
    if parity:
        packed.append([4, ['no door reaches'], 0, sorted(parity, key=parity_order)])
    for t, names, part_no, part in packed:
        new_m = {m for r in part for m in r['models']} - have_m
        new_t = {x for m in new_m for x in mesh_tex.get(m, ())} - have_t
        have_m |= new_m
        have_t |= new_t
        growth = sum((meshes.get(m) or {}).get('bytes', 0) for m in new_m) + sum(textures.get(x, 0) for x in new_t)
        batches.append({'batch': len(batches) + 1, 'kind': tier_names[t], 'groups': names,
                        'part': part_no, 'rooms': [r['name'] for r in part],
                        'in_game': sum(1 for r in part if r['name'].casefold() in in_game),
                        'placements': sum(r['kept_placements'] for r in part),
                        'notes': dict(sorted(collections.Counter(n for r in part
                                                                 for n in r.get('notes', ())).items())),
                        'new_models': len(new_m), 'new_textures': len(new_t),
                        'store_growth_bytes': growth if meshes else None,
                        'store_after_bytes': None})
        if t == 4:
            batches[-1]['parity'] = parity_rows(part)
    total = 0
    for b in batches:
        if b['store_growth_bytes'] is not None:
            total += b['store_growth_bytes']
            b['store_after_bytes'] = total
    reasons = collections.Counter(h for r in aside for h in r['hard'])
    # The expansions' rooms: one later batch per master, its parity rooms listed under it.
    later = []
    for master, (island, why) in LATER.items():
        members = sorted((r for r in graph['rooms'] if not in_vvardenfell_plan(r) and later_master(r) == master),
                         key=lambda r: r['name'].casefold())
        if not members:
            continue
        held = [r for r in members if r['hard'] and not parity_state(r)]
        later.append({'batch': 'later: ' + island, 'island': island, 'master': master, 'waits_for': why,
                      'rooms': [r['name'] for r in members],
                      'ready': sum(1 for r in members if not r['hard']), 'aside': len(held),
                      'aside_reasons': dict(sorted(collections.Counter(h for r in held for h in r['hard']).items())),
                      'parity': parity_rows([r for r in members if parity_state(r)])})
    return {'format': PLAN_FORMAT, 'generator': 'tools/door_graph.py plan', 'graph_masters': graph['masters'],
            'island': 'Vvardenfell', 'batch_rooms': batch_rooms,
            'order': 'towns first (towns with rooms in the game today first, then by rooms), then the other rooms '
                     'in the game, then the rest by region; inside a group by door depth',
            'store_measured': bool(meshes),
            'summary': {'rooms': len(rooms), 'ready': len(ready), 'aside': len(aside), 'batches': len(batches),
                        'parity': len(parity),
                        'parity_states': dict(sorted(collections.Counter(parity_state(r) for r in parity).items())),
                        'later': {b['island']: len(b['rooms']) for b in later},
                        'every_room': len(rooms) + sum(len(b['rooms']) for b in later),
                        'graph_rooms': len(graph['rooms']),
                        'batch_sizes': [len(b['rooms']) for b in batches],
                        'aside_reasons': dict(sorted(reasons.items())),
                        'ready_notes': dict(sorted(collections.Counter(n for r in ready
                                                                       for n in r.get('notes', ())).items())),
                        'store_bytes': total if meshes else None, 'in_game_ready': sum(1 for r in ready if
                                                                                      r['name'].casefold() in in_game),
                        'on_chim_rooms': sum(1 for r in rooms if r['name'].casefold() in chim_rooms)},
            'batches': batches, 'later': later,
            'aside': [{'room': r['name'], 'reasons': r['hard'], 'over_limit': r['over_limit']}
                      for r in sorted(aside, key=lambda r: r['name'].casefold())]}


def plan_markdown(doc, stamp=''):
    s = doc['summary']
    mib = (lambda b: '%.1f MiB' % (b / 1048576.0) if b is not None else 'not measured')
    lines = ['# Interior batch plan (private)', '', stamp, '',
             'Vvardenfell rooms: %d; ready now: %d; no door reaches: %d (the final parity batch); %d batches in all; '
             'set aside: %d.' % (s['rooms'], s['ready'], s.get('parity', 0), s['batches'], s['aside']),
             'Order: ' + doc['order'] + '.', 'Store after every batch: ' + mib(s['store_bytes']) + '.', '',
             '## Set aside', '', '| reason | rooms |', '| --- | ---: |']
    lines += ['| %s | %d |' % (k, v) for k, v in s['aside_reasons'].items()]
    lines += ['', '## Batches', '',
              '| # | kind | groups | rooms | in game | placements | new models | growth | store |',
              '| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for b in doc['batches']:
        groups = '; '.join(b['groups']) if len(b['groups']) <= 4 else '%s and %d more' % (
            '; '.join(b['groups'][:3]), len(b['groups']) - 3)
        lines.append('| %d | %s | %s%s | %d | %d | %d | %d | %s | %s |' % (
            b['batch'], b['kind'], groups, (' (part %d)' % b['part']) if b['part'] else '', len(b['rooms']),
            b['in_game'], b['placements'], b['new_models'], mib(b['store_growth_bytes']), mib(b['store_after_bytes'])))
    parity = [(b['batch'], p) for b in doc['batches'] for p in b.get('parity', ())]
    parity += [(b['batch'], p) for b in doc.get('later', ()) for p in b['parity']]
    if parity:
        lines += ['', '## No door reaches (parity: converted, kept with their state)', '',
                  '| batch | room | state | reasons |', '| --- | --- | --- | --- |']
        lines += ['| %s | %s | %s | %s |' % (b, p['room'], p['label'], ', '.join(p['reasons'])) for b, p in parity]
    if doc.get('later'):
        lines += ['', '## Later batches (expansions)', '', '| batch | master | rooms | ready | set aside | waits for |',
                  '| --- | --- | ---: | ---: | ---: | --- |']
        lines += ['| %s | %s | %d | %d | %d | %s |' % (b['batch'], b['master'], len(b['rooms']), b['ready'], b['aside'],
                                                      b['waits_for']) for b in doc['later']]
    return '\n'.join(l for l in lines) + '\n'


# ------------------------------------------------------------------ command line

def write_json(path, doc):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(doc, indent=1, sort_keys=False, default=list) + '\n', encoding='utf-8', newline='\n')
    tmp.replace(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    g = sub.add_parser('graph', help='parse the masters and write the door graph')
    g.add_argument('--data-files', type=Path, required=True)
    g.add_argument('--out', type=Path, required=True)
    g.add_argument('--mesh-cache', type=Path, help='measure every room mesh (asset census, cached in this file)')
    g.add_argument('--jobs', type=int, help='workers (default: every core)')
    g.add_argument('--sdk', type=Path, help='the Amiga SDK (m68k-amigaos-gcc): with --mesh-cache, each room set is '
                                            'also measured as the engine holds it in memory (zone bytes)')
    p = sub.add_parser('plan', help='batch the Vvardenfell rooms that can be converted now')
    p.add_argument('--graph', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--md', type=Path)
    p.add_argument('--config-dir', type=Path, default=ROOT / 'config', help='scene lists: the rooms in the game')
    p.add_argument('--chim-rooms', type=Path, help='a chim-rooms-receipt.json: the rooms already on CHIM rooms')
    p.add_argument('--batch-rooms', type=int, default=40)
    p.add_argument('--stamp', default='')
    r = sub.add_parser('room-batches', help='the public room list of a batch plan (config/room-batches.json)')
    r.add_argument('--plan', type=Path, required=True)
    r.add_argument('--graph', type=Path, required=True)
    r.add_argument('--out', type=Path, required=True)
    r.add_argument('--previous', type=Path, help='the list it replaces: its rooms keep their ids (save IDs)')
    a = ap.parse_args(argv)
    if a.cmd == 'room-batches':
        import room_batches
        plan_doc = json.loads(a.plan.read_text(encoding='utf-8'))
        graph = json.loads(a.graph.read_text(encoding='utf-8'))
        if plan_doc.get('format') != PLAN_FORMAT or graph.get('format') != FORMAT:
            raise SystemExit('room-batches needs an %s plan and an %s graph' % (PLAN_FORMAT, FORMAT))
        previous = json.loads(a.previous.read_text(encoding='utf-8')) if a.previous and a.previous.is_file() else None
        doc = room_batches.from_plan(plan_doc, graph, previous)
        a.out.write_text(room_batches.dumps(doc), encoding='utf-8', newline='\n')
        print('room list: %d batches, %d rooms, next id %d' % (len(doc['batches']),
                                                                sum(len(b['rooms']) for b in doc['batches']),
                                                                doc['next_id']))
        return 0
    if a.cmd == 'graph':
        jobs = resolve_jobs(a.jobs)
        print('door graph: %d workers (cores %d); the masters are cut into record ranges parsed side by side'
              % (jobs, os.cpu_count() or 1), flush=True)
        target = None
        if a.sdk:
            from check_world_map_heap import compile_target_sizes
            target = compile_target_sizes(a.sdk)[0]
        doc = build_graph(a.data_files, jobs, a.mesh_cache, warn=lambda m: print(m, flush=True), target_sizes=target)
        write_json(a.out, doc)
        print(json.dumps({'summary': doc['summary'], 'timings': doc['timings']}, indent=1))
        return 0
    graph = json.loads(a.graph.read_text(encoding='utf-8'))
    if graph.get('format') != FORMAT:
        raise SystemExit('%s: not an %s file' % (a.graph, FORMAT))
    chim = []
    if a.chim_rooms:
        chim = [r.get('cell') or r.get('room') for r in json.loads(a.chim_rooms.read_text())['rooms']]
    doc = plan(graph, a.config_dir, a.batch_rooms, [c for c in chim if c])
    write_json(a.out, doc)
    if a.md:
        a.md.write_text(plan_markdown(doc, a.stamp), encoding='utf-8', newline='\n')
    print(json.dumps(doc['summary'], indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
