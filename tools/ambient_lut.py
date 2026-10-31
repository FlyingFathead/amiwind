#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The ambient behaviour table (AWAM1, id1/npc-ambient.lut): every placed actor's Wander package and the routes of
its cell's path grid, compiled at build time so the engine never searches (NPC-WANDER-NOT-EXECUTED-35,
ACTOR-WANDER-AGGRO-52; docs/NPC_PATHFINDING.md "Wander packages, compiled").

What the game does, as OpenMW 0.51 implements it (apps/openmw/mwmechanics/aiwander.cpp, pathgrid.cpp,
components/misc/pathgridutils.hpp; our own code, nothing copied):
- An actor whose first behaviour package is Wander (AI_W: distance, duration in game hours, time of day, chances for the
  idles Idle2..Idle9, repeat) wanders among the path grid points of its cell that lie within the distance of its
  starting position and are in the same strongly connected part of the grid as the point closest to it; with
  exactly one such point its starting position and points part way along that point's links are added; with none
  (no grid, or nothing in reach) it walks now and then to a random spot near its start.
- Routes between points are the grid's shortest (links are one-way as stored; cost Manhattan, as OpenMW's A*).
- An idle is chosen by the original's roll: with probability fIdleChanceMultiplier (a GMST) each idle rolls 0..100
  and the highest roll at or under its chance wins; no winner = walk (distance > 0) or roll again.
- The time of day is stored but unused (OpenMW reads it nowhere); duration only resets a repeating package.

Compiled form (one row per placed actor with a Wander package, sorted by reference number then id hash):
- the actor's local points: candidate destinations (path grid points within the compile radius of its reference
  position: the record's distance, or larger when a script's AIWander names the actor), its starting position,
  the part-way points of the one-point case, then the points routes pass through; each as i16 x y z in engine
  units relative to the reference position (original units x 0.25), so the engine adds its own spawn origin and
  needs no world coordinates;
- a next-hop table: for every local point and every destination, the next local point on the route (255: none);
- an idle profile (shared between actors): the cumulative chances of Idle2..Idle9 in 1/65536, the GMST multiplier
  applied, by the exact distribution of the roll above at 1 % steps (the engine computes a script's profile the
  same way, engine/aga/src/aw_ambient.c AW_AmbientIdleProfile).

Levelled creatures (v0.0.57, ACTORS-ALIVE-56): the creature a levelled list picks runs its own record's packages
(OpenMW 0.51 mwclass/creaturelevlist.cpp + mwclass/creature.cpp). Every placed levelled reference gets a routes row
(reference number, id hash 0, flag 16) compiled at the largest Wander distance its list can give, and every creature
such a list can give a package row (reference number 0, its id hash) with one home point; the engine joins the two
when the picked creature registers (aw_ambient.c find_actor). Same AWAM1 layout; the engine keeps only every 32nd
row's key resident and reads a block of rows per lookup.

File (big-endian): header 32 bytes: "AWAM", u16 version 1, u16 row bytes 28, u32 rows, u32 points, u32 hop bytes,
u32 profiles, u16 idle multiplier (x 65535), u16 0, u32 0. Rows x 28: u32 reference number, u32 id hash (FNV-1a of
the lower-case id), u16 distance (original units), u16 duration (hours), u8 time of day, u8 flags, u8 local points,
u8 destinations, u32 first point, u32 first hop byte, u16 profile, u16 0. Points x 8: i16 x y z, u8 kind (0 grid
point, 1 starting position, 2 part-way point), u8 0. Hops: local points x destinations bytes per row, padded to 4.
Profiles x 16: u16 x 8 cumulative.

  python3 tools/ambient_lut.py --data-files DIR --out npc-ambient.lut [--report report.json]
"""
import argparse
import hashlib
import heapq
import json
import re
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))
from mwad.audit import cell_data, records, string, subrecords  # noqa: E402  (the package, before tools/mwad.py)

MAGIC = b'AWAM'
VERSION = 1
NAME = 'npc-ambient.lut'
HEADER = 32
ROW = 28
POINT = 8
PROFILE = 16
SCALE = 0.25                    # original units to engine units (tools/prepare_quake.py SCALE)
CELL_UNITS = 8192
NONE8 = 255
MAX_LOCAL = 254                 # local points per actor (u8 indices, 255 = none)
MAX_DESTINATIONS = 64           # destinations per actor: the nearest kept beyond (reported)
MAX_WIDTH = 128                 # destinations the engine takes (aw_ambient.h AW_AMBIENT_MAX_DEST)
MIN_WANDER = 128               # OpenMW aiwander.cpp minimumWanderDistance (destination tolerance 64 x 2)
IDLE_STEPS = 100                # the idle roll's exact distribution at 1 % steps (the engine's rule too)
# row flags
F_REPEAT, F_CREATURE, F_FLYER, F_SWIMMER, F_LEVELLED = 1, 2, 4, 8, 16
# levelled creatures (same AWAM1 layout, two reserved keys): a levelled reference's routes are the row
# (reference number, LEVELLED_HASH); a creature its list can give has its package in the row (LEVELLED_REF, id hash)
LEVELLED_HASH = 0
LEVELLED_REF = 0
# point kinds
K_GRID, K_HOME, K_PARTWAY = 0, 1, 2
AREAS = {  # bytes per town, measured like tools/path_grid_stats.py AREAS: exterior centre, radius in cells, room prefix
    'seyda_neen': ((-2, -9), 1, 'Seyda Neen'),
    'balmora': ((-3, -2), 1, 'Balmora'),
}
_AIWANDER = re.compile(r'^\s*(?:(?:"([^"]+)"|([A-Za-z0-9_\'\-]+))\s*->\s*)?ai\s*wander\b(.*)$', re.I)


def fnv(text):
    """FNV-1a 32 of the lower-case id (the engine's AW_AmbientHash)."""
    h = 0x811C9DC5
    for b in text.casefold().encode('latin-1', 'replace'):
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


# ---------------------------------------------------------------- the idle roll

def idle_profile(chances, multiplier):
    """Cumulative chances of Idle2..Idle9 (8 x u16, 1/65536) of the original's roll (aiwander.cpp getRandomIdle):
    with probability MULTIPLIER every idle rolls r in [0, 100] and the highest r <= its chance wins. Exact at 1 %
    steps: P(i) = sum over x of [x < c_i] / 100 * prod over j != i of P(r_j > c_j or r_j < x), x at the step
    midpoints. Integer arithmetic only, as the engine does it (AW_AmbientIdleProfile)."""
    c = [min(100, max(0, int(v))) for v in list(chances)[:8]] + [0] * (8 - len(list(chances)[:8]))
    weight = [0] * 8
    for i in range(8):
        total = 0
        for x2 in range(1, 2 * IDLE_STEPS, 2):         # midpoints x = x2 / 2
            if x2 >= 2 * c[i]:
                break
            p = 1 << 16
            for j in range(8):
                if j != i:
                    # P(r_j > c_j) + P(r_j < min(x, c_j)) in 1/200
                    below = min(x2, 2 * c[j])
                    p = p * (200 - 2 * c[j] + below) // 200
            total += p
        weight[i] = total // IDLE_STEPS             # 1/65536
    m = max(0, min(65535, int(multiplier)))
    out = []; run = 0
    for w in weight:
        run += w * m // 65535
        out.append(min(65535, run))
    return out


# ---------------------------------------------------------------- the masters

def parse_master(raw):
    """(gmst {name: value}, actors {id: record}, cells [cell], grids {key: grid}, scripts {name: text})."""
    gmst = {}; actors = {}; cells = []; pending = []; scripts = {}
    for tag, flags, payload in records(raw):
        if flags & 0x20:
            continue
        if tag == 'GMST':
            f = dict(subrecords(payload))
            name = string(f.get('NAME', b''))
            if 'FLTV' in f and len(f['FLTV']) == 4:
                gmst[name] = struct.unpack('<f', f['FLTV'])[0]
        elif tag in ('NPC_', 'CREA'):
            ident = ''; packages = []; script = ''; cflags = 0; deleted = False
            for k, d in subrecords(payload):
                if k == 'NAME' and not ident:
                    ident = string(d).casefold()
                elif k == 'DELE':
                    deleted = True
                elif k == 'SCRI':
                    script = string(d).casefold()
                elif k == 'FLAG' and tag == 'CREA' and len(d) >= 4:
                    cflags = struct.unpack_from('<I', d)[0]
                elif k == 'AI_W' and len(d) >= 14:
                    dist, dur, hour = struct.unpack_from('<HHB', d)
                    packages.append(('wander', {'distance': dist, 'duration': dur, 'hour': hour,
                                                'idle': list(d[5:13]), 'repeat': d[13]}))
                elif k in ('AI_T', 'AI_F', 'AI_E', 'AI_A'):
                    packages.append(({'AI_T': 'travel', 'AI_F': 'follow', 'AI_E': 'escort',
                                      'AI_A': 'activate'}[k], None))
            if ident and not deleted:
                actors[ident] = {'kind': tag, 'packages': packages, 'script': script, 'flags': cflags}
        elif tag == 'CELL':
            cells.append(cell_data(list(subrecords(payload))))
        elif tag == 'PGRD':
            pending.append(parse_pgrd(list(subrecords(payload))))
        elif tag == 'SCPT':
            name = ''; text = ''
            for k, d in subrecords(payload):
                if k == 'SCHD':
                    name = d[:32].split(b'\0')[0].decode('latin-1').casefold()
                elif k == 'SCTX':
                    text = d.decode('latin-1')
            if name:
                scripts[name] = text
    interiors = {c['name'].casefold() for c in cells if c['flags'] & 1}
    grids = {}
    for g in pending:
        interior = g['grid'] == (0, 0) and g['name'].casefold() in interiors
        grids[('i', g['name'].casefold()) if interior else ('e',) + g['grid']] = g
    return gmst, actors, cells, grids, scripts


def parse_pgrd(fields):
    """One PGRD record: name, grid (x, y), points [(x, y, z)], directed links [(from, to)] (OpenMW loadpgrd.cpp:
    each point's links follow in point order)."""
    name = ''; grid = (0, 0); points = []; counts = []; raw = []
    for tag, data in fields:
        if tag == 'NAME':
            name = string(data)
        elif tag == 'DATA' and len(data) == 12:
            grid = struct.unpack('<ii', data[:8])
        elif tag == 'PGRP':
            for i in range(0, len(data) - len(data) % 16, 16):
                x, y, z, _auto, links, _pad = struct.unpack_from('<iiiBBH', data, i)
                points.append((x, y, z)); counts.append(links)
        elif tag == 'PGRC':
            raw = list(struct.unpack('<%dI' % (len(data) // 4), data[:len(data) // 4 * 4]))
    links = []; at = 0
    for i, n in enumerate(counts):
        for j in raw[at:at + n]:
            if 0 <= j < len(points):
                links.append((i, j))
        at += n
    return {'name': name, 'grid': tuple(grid), 'points': points, 'links': links}


def scripted_distances(scripts, actors):
    """{actor id: largest AIWander distance a script gives it} (explicit "id"->AIWander, or the script attached to
    the actor's record). The compile radius covers it, so a script's package needs no search either."""
    attached = {}
    for ident, a in actors.items():
        if a['script']:
            attached.setdefault(a['script'], []).append(ident)
    out = {}
    for name, text in scripts.items():
        for line in text.splitlines():
            line = line.split(';', 1)[0]
            m = _AIWANDER.match(line)
            if not m:
                continue
            words = m.group(3).replace(',', ' ').split()
            try:
                distance = int(float(words[0]))
            except (IndexError, ValueError):
                continue
            target = (m.group(1) or m.group(2) or '').casefold()
            for ident in ([target] if target else attached.get(name, [])):
                if ident in actors:
                    out[ident] = max(out.get(ident, 0), distance)
    return out


# ---------------------------------------------------------------- graphs

def strong_parts(n, links):
    """Strongly connected part id per point (Tarjan, iterative; OpenMW pathgrid.cpp's isPointConnected)."""
    adj = [[] for _ in range(n)]
    for a, b in links:
        adj[a].append(b)
    index = [None] * n; low = [0] * n; on = [False] * n; stack = []; part = [-1] * n; counter = 0; parts = 0
    for root in range(n):
        if index[root] is not None:
            continue
        work = [(root, 0)]
        while work:
            v, i = work.pop()
            if i == 0:
                index[v] = low[v] = counter; counter += 1; stack.append(v); on[v] = True
            recurse = False
            for k in range(i, len(adj[v])):
                w = adj[v][k]
                if index[w] is None:
                    work.append((v, k + 1)); work.append((w, 0)); recurse = True; break
                if on[w]:
                    low[v] = min(low[v], index[w])
            if recurse:
                continue
            if low[v] == index[v]:
                while True:
                    w = stack.pop(); on[w] = False; part[w] = parts
                    if w == v:
                        break
                parts += 1
            if work:
                u = work[-1][0]
                low[u] = min(low[u], low[v])
    return part


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])


def distances_to(points, rev, target):
    """Cost of the cheapest route from every point to TARGET (Dijkstra on the reversed links, Manhattan costs)."""
    dist = {target: 0}; heap = [(0, target)]
    while heap:
        d, v = heapq.heappop(heap)
        if d > dist.get(v, 1 << 60):
            continue
        for u in rev[v]:
            nd = d + manhattan(points[u], points[v])
            if nd < dist.get(u, 1 << 60):
                dist[u] = nd; heapq.heappush(heap, (nd, u))
    return dist


def next_hop(points, adj, dist, u):
    """The next point from U on a cheapest route (lowest index on a tie), or None."""
    best = None
    for w in adj[u]:
        if w in dist and w != u:
            cost = manhattan(points[u], points[w]) + dist[w]
            if best is None or cost < best[0] or (cost == best[0] and w < best[1]):
                best = (cost, w)
    return best[1] if best else None


# ---------------------------------------------------------------- one actor

def offset(world, origin):
    return tuple(int(round((world[k] - origin[k]) * SCALE)) for k in range(3))


def within(off, distance):
    """The engine's rule (AW_AmbientWithin): a point is in reach when 16 x (x^2 + y^2 + z^2) <= distance^2 (offsets
    in engine units, distance in original units)."""
    return 16 * (off[0] * off[0] + off[1] * off[1] + off[2] * off[2]) <= distance * distance


def compile_actor(position, grid, cell_origin, distance, radius, cache):
    """The local points and next-hop table of one actor: (points [(off, kind)], destinations, hops bytes, notes).
    position: the reference's world position; grid: its cell's grid or None; cell_origin: the grid's world
    offset (exterior points are cell-local); distance: the record's; radius: the compile radius (>= distance)."""
    notes = {}
    if grid is None or len(grid['points']) < 2 or radius <= 0:
        return [((0, 0, 0), K_HOME)], 1, bytes([0]), notes
    key = id(grid)
    if key not in cache:
        pts = grid['points']; n = len(pts)
        adj = [[] for _ in range(n)]; rev = [[] for _ in range(n)]
        for a, b in grid['links']:
            adj[a].append(b); rev[b].append(a)
        cache[key] = {'adj': adj, 'rev': rev, 'part': strong_parts(n, grid['links']), 'dist': {}}
    g = cache[key]; pts = grid['points']
    world = [(p[0] + cell_origin[0], p[1] + cell_origin[1], p[2]) for p in pts]
    local = [tuple(position[k] - cell_origin[k] for k in range(2)) + (position[2],)]
    home = local[0]
    closest = min(range(len(pts)), key=lambda i: ((pts[i][0] - home[0]) ** 2 + (pts[i][1] - home[1]) ** 2 +
                                                  (pts[i][2] - home[2]) ** 2, i))
    offs = [offset(w, position) for w in world]
    cands = [i for i in range(len(pts)) if within(offs[i], radius) and g['part'][i] == g['part'][closest]]
    if len(cands) > MAX_DESTINATIONS:
        cands.sort(key=lambda i: (offs[i][0] ** 2 + offs[i][1] ** 2 + offs[i][2] ** 2, i))
        notes['destinations_cut'] = len(cands) - MAX_DESTINATIONS
        cands = sorted(cands[:MAX_DESTINATIONS])
    # the starting position (always: a script's distance can leave one point) and the record's part-way points
    extras = [((0, 0, 0), K_HOME, closest)]
    in_record = [i for i in cands if within(offs[i], distance)]
    if len(in_record) == 1 and distance > 0:
        single = in_record[0]
        step = max(distance // 2, MIN_WANDER)
        for a, b in grid['links']:
            if a != single:
                continue
            d = [world[b][k] - world[a][k] for k in range(3)]
            length = sum(v * v for v in d) ** .5
            if length <= 0:
                continue
            go = min(step, int(length))
            spot = tuple(world[a][k] + d[k] / length * go for k in range(3))
            extras.append((offset(spot, position), K_PARTWAY, single))
    def dist_to(t):
        if t not in g['dist']:
            g['dist'][t] = distances_to(pts, g['rev'], t)
        return g['dist'][t]

    def through(cands):
        """the grid points routes between the destinations (and from the closest point) pass through, not
        destinations themselves, in first-seen order"""
        targets = list(cands) + sorted({e[2] for e in extras} - set(cands))
        seen = set(cands); order = []
        for t in targets:
            dist = dist_to(t)
            for s in cands + [closest]:
                u = s; guard = 0
                while u is not None and guard <= len(pts):
                    if u not in seen:
                        seen.add(u); order.append(u)
                    if u == t or u not in dist:
                        break
                    u = next_hop(pts, g['adj'], dist, u); guard += 1
        return order
    inner = through(cands)
    while cands and len(cands) + len(extras) + len(inner) > MAX_LOCAL:
        far = max(cands, key=lambda i: (offs[i][0] ** 2 + offs[i][1] ** 2 + offs[i][2] ** 2, i))
        cands = [i for i in cands if i != far]
        notes['local_points_cut'] = notes.get('local_points_cut', 0) + 1
        inner = through(cands)
    # local order: the destinations first (grid candidates, then the extras), then the points routes pass through,
    # so a destination's column is its local index
    grid_local = list(cands) + inner
    index = {p: (k if k < len(cands) else k + len(extras)) for k, p in enumerate(grid_local)}
    points = ([(offs[p], K_GRID) for p in cands] + [(e[0], e[1]) for e in extras] +
              [(offs[p], K_GRID) for p in inner])
    dests = len(cands)
    width = dests + len(extras)
    if width > MAX_WIDTH:
        raise ValueError('Ambient table: %d destinations, the engine takes %d' % (width, MAX_WIDTH))
    hops = bytearray([NONE8] * (len(points) * width))

    def grid_hop(u, t):
        """next local index from grid point u toward grid point t (both grid indices), or NONE8"""
        nxt = next_hop(pts, g['adj'], dist_to(t), u)
        return index.get(nxt, NONE8) if nxt is not None else NONE8
    for li, (off, kind) in enumerate(points):
        extra = dests <= li < width
        u = None if extra else (cands[li] if li < dests else inner[li - width])
        for col in range(width):
            if li == col:
                h = li
            elif not extra:
                if col < dests:
                    h = grid_hop(u, cands[col])
                else:
                    anchor = extras[col - dests][2]
                    h = col if u == anchor else grid_hop(u, anchor)
            else:                                          # an extra point walks to its anchor first
                anchor = extras[li - dests][2]
                h = index.get(anchor, NONE8)
                if col >= dests and extras[col - dests][2] == anchor:
                    h = col                                # extras of one anchor: straight across
            hops[li * width + col] = h
    return points, width, bytes(hops), notes


# ---------------------------------------------------------------- the table

def placed_wanderers(actors, cells):
    """[(cell, reference, actor id, record)] of every placed, non-deleted actor whose first package is Wander."""
    out = []
    for cell in cells:
        for ref in cell['refs']:
            ident = ref.get('id', '').casefold()
            a = actors.get(ident)
            if a is None or ref.get('deleted') or 'position' not in ref:
                continue
            if a['packages'] and a['packages'][0][0] == 'wander':
                out.append((cell, ref, ident, a))
    return out


def list_creatures(lists, lid, seen=None):
    """The creature ids (lower case) a levelled creature list can give at any player level, nested lists followed."""
    seen = set() if seen is None else seen
    if lid in seen or lid not in lists:
        return set()
    seen.add(lid)
    out = set()
    for entry, _level in lists[lid][2]:
        out |= list_creatures(lists, entry, seen) if entry in lists else {entry}
    return out


def row_flags(w, a):
    flags = F_REPEAT if w['repeat'] else 0
    if a['kind'] == 'CREA':
        flags |= F_CREATURE
        if a['flags'] & 0x20:
            flags |= F_FLYER
        if a['flags'] & 0x10 and not a['flags'] & 0x40:
            flags |= F_SWIMMER
    return flags


def build_master(master, report_areas=True):
    """(bytes, report) of the table for one master file's bytes or path."""
    raw = master if isinstance(master, (bytes, bytearray)) else Path(master).read_bytes()
    t0 = time.time()
    gmst, actors, cells, grids, scripts = parse_master(raw)
    from chim.actors import levelled_lists
    lists = levelled_lists(raw)
    multiplier = int(round(max(0.0, min(1.0, gmst.get('fIdleChanceMultiplier', 0.75))) * 65535))
    scripted = scripted_distances(scripts, actors)
    rows = []; points = []; hops = bytearray(); profiles = {}; cache = {}
    counts = {'placed_actors': 0, 'wander_first': 0, 'other_first': 0, 'no_package': 0, 'stationary': 0,
              'grid_routes': 0, 'manual_wander': 0, 'flyers_swimmers': 0, 'destinations_cut': 0,
              'local_points_cut': 0, 'scripted_radius': 0}
    first_kinds = {}
    for cell in cells:
        for ref in cell['refs']:
            a = actors.get(ref.get('id', '').casefold())
            if a is None or ref.get('deleted'):
                continue
            counts['placed_actors'] += 1
            kind = a['packages'][0][0] if a['packages'] else None
            first_kinds[kind or 'none'] = first_kinds.get(kind or 'none', 0) + 1
            counts['no_package' if kind is None else 'wander_first' if kind == 'wander' else 'other_first'] += 1
    per_row_cell = []
    for cell, ref, ident, a in placed_wanderers(actors, cells):
        w = a['packages'][0][1]
        interior = bool(cell['flags'] & 1)
        key = ('i', cell['name'].casefold()) if interior else ('e', cell['x'], cell['y'])
        grid = grids.get(key)
        origin = (0, 0, 0) if interior else (cell['x'] * CELL_UNITS, cell['y'] * CELL_UNITS, 0)
        radius = max(w['distance'], scripted.get(ident, 0))
        if radius > w['distance']:
            counts['scripted_radius'] += 1
        flags = row_flags(w, a)
        if flags & (F_FLYER | F_SWIMMER):
            counts['flyers_swimmers'] += 1
        pts, width, hop, notes = compile_actor(tuple(ref['position']), grid, origin, w['distance'], radius, cache)
        for k in ('destinations_cut', 'local_points_cut'):
            counts[k] += 1 if k in notes else 0
        if w['distance'] == 0:
            counts['stationary'] += 1
        elif width > 1 and sum(1 for p in pts if p[1] == K_GRID and within(p[0], w['distance'])) > 0:
            counts['grid_routes'] += 1
        else:
            counts['manual_wander'] += 1
        prof = tuple(idle_profile(w['idle'], multiplier))
        if prof not in profiles:
            profiles[prof] = len(profiles)
        rows.append((ref['number'], fnv(ident), min(65535, w['distance']), min(65535, w['duration']),
                     w['hour'] & 255, flags, len(pts), width, len(points), len(hops), profiles[prof]))
        points.extend(pts)
        hops += hop
        while len(hops) % 4:
            hops.append(0)
        per_row_cell.append((cell, len(pts) * POINT + len(hop) + (-len(hop)) % 4 + ROW))
    # Levelled creature references (LEVELLED_HASH rows) and the packages of the creatures they can give (LEVELLED_REF
    # rows). OpenMW 0.51 spawns the creature a list picks as an ordinary reference of that creature
    # (mwclass/creaturelevlist.cpp: ManualRef of the picked id), whose package sequence is filled from its own record's
    # packages (mwclass/creature.cpp: getAiSequence().fill(mBase->mAiPackage)); so the picked creature wanders by its
    # record. The engine knows the pick only when the cell joins: the routes are compiled once per reference at the
    # largest Wander distance among the creatures its list can give, and the package (distance, duration, idles,
    # flags) is looked up by the picked creature's id (aw_ambient.c find_levelled).
    placed_rows = len(rows)
    used = {}
    lev = {'references': 0, 'with_wander': 0, 'creatures': 0}
    for cell in cells:
        for ref in cell['refs']:
            lid = ref.get('id', '').casefold()
            if lid not in lists or ref.get('deleted') or 'position' not in ref:
                continue
            lev['references'] += 1
            creas = []
            for cid in sorted(list_creatures(lists, lid)):
                a = actors.get(cid)
                if a and a['packages'] and a['packages'][0][0] == 'wander':
                    creas.append((cid, a))
                    used[cid] = a
            if not creas:
                continue
            lev['with_wander'] += 1
            distance = max(a['packages'][0][1]['distance'] for _, a in creas)
            interior = bool(cell['flags'] & 1)
            key = ('i', cell['name'].casefold()) if interior else ('e', cell['x'], cell['y'])
            origin = (0, 0, 0) if interior else (cell['x'] * CELL_UNITS, cell['y'] * CELL_UNITS, 0)
            pts, width, hop, notes = compile_actor(tuple(ref['position']), grids.get(key), origin, distance, distance,
                                                   cache)
            for k in ('destinations_cut', 'local_points_cut'):
                counts[k] += 1 if k in notes else 0
            rows.append((ref['number'], LEVELLED_HASH, min(65535, distance), 0, 0, F_LEVELLED, len(pts), width,
                         len(points), len(hops), 0))
            points.extend(pts)
            hops += hop
            while len(hops) % 4:
                hops.append(0)
            per_row_cell.append((cell, len(pts) * POINT + len(hop) + (-len(hop)) % 4 + ROW))
    for cid, a in sorted(used.items()):
        w = a['packages'][0][1]
        prof = tuple(idle_profile(w['idle'], multiplier))
        if prof not in profiles:
            profiles[prof] = len(profiles)
        rows.append((LEVELLED_REF, fnv(cid), min(65535, w['distance']), min(65535, w['duration']), w['hour'] & 255,
                     row_flags(w, a), 1, 1, len(points), len(hops), profiles[prof]))
        points.append(((0, 0, 0), K_HOME))
        hops += bytes([0, 0, 0, 0])
    lev['creatures'] = len(used)
    order = sorted(range(len(rows)), key=lambda i: (rows[i][0], rows[i][1]))
    for r in rows[:placed_rows]:
        if r[0] == LEVELLED_REF:
            raise ValueError('Ambient table: a placement has reference number 0 (reserved for levelled packages)')
        if r[1] == LEVELLED_HASH:
            raise ValueError('Ambient table: an actor id hashes to 0 (reserved for levelled references)')
    for a, b in zip(order, order[1:]):
        if rows[a][:2] == rows[b][:2]:
            raise ValueError('Ambient table: two placements share reference %d and id hash' % rows[a][0])
    out = bytearray(MAGIC + struct.pack('>HHIIIIHHI', VERSION, ROW, len(rows), len(points), len(hops),
                                        len(profiles), multiplier, 0, 0))
    for i in order:
        r = rows[i]
        out += struct.pack('>IIHHBBBBIIHH', *r, 0)
    for (x, y, z), kind in points:
        for v in (x, y, z):
            if not -32768 <= v <= 32767:
                raise ValueError('Ambient table: a point offset is out of the i16 range')
        out += struct.pack('>hhhBB', x, y, z, kind, 0)
    out += hops
    for prof in sorted(profiles, key=profiles.get):
        out += struct.pack('>8H', *prof)
    report = {'format': 'AWAM%d' % VERSION, 'bytes': len(out), 'sha256': hashlib.sha256(out).hexdigest(),
              'rows': len(rows), 'points': len(points), 'hop_bytes': len(hops), 'profiles': len(profiles),
              'idle_multiplier': multiplier / 65535.0, 'first_package': first_kinds, 'counts': counts,
              'scripted_actors': len(scripted), 'grids': len(grids), 'levelled': lev,
              'seconds': round(time.time() - t0, 2)}
    if report_areas:
        report['areas'] = area_bytes(per_row_cell)
    return bytes(out), report


def area_bytes(per_row_cell):
    """Table bytes (rows, points, hops) of the actors of each measured town: its exterior cells and its rooms."""
    out = {}
    for area, ((cx, cy), r, prefix) in AREAS.items():
        total = rows = 0
        for cell, size in per_row_cell:
            if cell['flags'] & 1:
                hit = cell['name'].casefold().startswith(prefix.casefold())
            else:
                hit = abs(cell['x'] - cx) <= r and abs(cell['y'] - cy) <= r
            if hit:
                total += size; rows += 1
        out[area] = {'actors': rows, 'bytes': total}
    return out


def read_table(data):
    """The table back: header dict, rows [dict], points [(x, y, z, kind)], hops bytes, profiles [[8]] (tests)."""
    if data[:4] != MAGIC:
        raise ValueError('not AWAM')
    version, row_bytes, nrows, npoints, nhops, nprof, mult, _a, _b = struct.unpack_from('>HHIIIIHHI', data, 4)
    at = HEADER; rows = []
    for _ in range(nrows):
        v = struct.unpack_from('>IIHHBBBBIIHH', data, at); at += ROW
        rows.append(dict(zip(('ref', 'hash', 'distance', 'duration', 'hour', 'flags', 'points', 'destinations',
                              'first_point', 'first_hop', 'profile'), v[:11])))
    points = []
    for _ in range(npoints):
        points.append(struct.unpack_from('>hhhB', data, at)); at += POINT
    hops = data[at:at + nhops]; at += nhops
    profiles = [list(struct.unpack_from('>8H', data, at + 16 * k)) for k in range(nprof)]
    if at + 16 * nprof != len(data):
        raise ValueError('AWAM size mismatch')
    return {'version': version, 'multiplier': mult}, rows, points, hops, profiles


# ---------------------------------------------------------------- the image step

def image_step(data, id1, out=None, jobs=1):
    """The image step: id1/npc-ambient.lut from DATA's Morrowind.esm through the unit cache (keyed by the master's
    SHA-256 and this module's source); the report beside it in OUT (npc-ambient-table.json). One unit: the whole
    island compiles in seconds on one core (the report's seconds), so it is not split."""
    from build_scratch import scratch_dir
    from mwad.esm import sha256_file
    from mwad.paths import child_ci
    from pass_cache import UnitCache
    master = child_ci(Path(data), 'Morrowind.esm')
    inputs = {'master_sha256': sha256_file(master)}
    cache = UnitCache.open('npc-ambient-table', {'format': 'AWAM%d' % VERSION}, __file__)
    target = Path(id1) / NAME
    t0 = time.time()
    print('Ambient table: start (1 unit cache lookup, 1 core if built: one unit)', flush=True)
    with scratch_dir(prefix='ambient-table-', near=out if out is not None else Path(id1).parent,
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
        raise ValueError('Ambient table: SHA-256 differs from its report')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    if out is not None:
        Path(out).mkdir(parents=True, exist_ok=True)
        (Path(out) / 'npc-ambient-table.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n',
                                                          encoding='utf-8', newline='\n')
    print('Ambient table: %s %s, %d bytes, %d actors (took %.1f s, 1 core)' % (
        'reused' if report['reused'] else 'built', NAME, len(raw), report['rows'], time.time() - t0), flush=True)
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True, help='the AWAM1 file to write')
    p.add_argument('--report', type=Path)
    a = p.parse_args(argv)
    from mwad.paths import child_ci
    raw, report = build_master(child_ci(a.data_files, 'Morrowind.esm'))
    a.out.write_bytes(raw)
    if a.report:
        a.report.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print('Ambient table: %d bytes, %d actors, %.2f s' % (len(raw), report['rows'], report['seconds']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
