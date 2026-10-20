#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The fixed crossing route: CHIM cell crossings timed in a headless FS-UAE session.

CHIM-CROSSING-SLUGGISH-43, docs/PLAN-v0.0.45.md step 1.1 (the A of every crossing comparison; method and results in
docs/performance/CROSSING_BASELINE.md). The route is data (ROUTE below): legs in original Morrowind global
coordinates, each a level noclip flight across one cell edge, diagonally through one cell corner where four frames
meet, or around a corner in a small square, in a light region (Ascadian Isles, Bitter Coast) and at a heavy town frame
(Balmora). One boot per memory size and engine; every leg is flown three times in a row (teleport back, settle, cross
again), always in the same order, at the same speed, altitude and time of day.

Subcommands:
  route                 print the route as JSON
  session ...           drive one FS-UAE session over the route (run inside an FS-UAE container; the game image
                        must be a fresh writable play copy, never a sealed disk)
  parse SESSION_DIR     per-crossing JSON from a session's console log, state samples and the engine's
                        diagnostic logs (written by aw_savelogs, read back from the play copy)
  table RUN.json ...    the markdown table: median and max per crossing kind (edge, corner) and memory size

Engine sources of the numbers (stock engine, no instrumentation added):
  console "Scene ready: MAP, N ms"   crossing start to player placed on the new frame (aw_scene.c)
  console "CHIM: primed: ... ms"     loading the chunk ring at the arrival point (chim_world.c, chim_debug 1)
  cell-load-profile.tsv              map file bytes/reads/disk/decode time, entities, server spawn (aw_stream.c)
  cell-visible-profile.tsv           crossing start to the first presented frame of the new map
  frame-stalls.csv                   every frame over 100 ms, with its frame number (aw_profile.c)
  walk-profile.csv                   the map every 10 frames: which stall belongs to which crossing
  state.txt rcount line (aw_rcount 2) per second: CHIM KiB/reads, surface cache blocks and texels drawn
Emulator times are relative only (BENCH-JIT-PROFILE-32); bytes, reads and surface blocks are the main currency.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

CELL = 8192
ROUTE_VERSION = 2
REPEATS = 3

# Leg: name, region, weight (light/heavy), kind (edge, corner, corner-loop), start X Y (global, 640 units before the
# border; a corner leg 640 units before the corner on the diagonal), yaw (0 east, 90 north), the flight in seconds,
# the altitude Z (global, above the highest ground of the leg), and what it crosses. One boot per memory size and
# engine; each leg is flown REPEATS times in a row (teleport back, settle, cross again). Corners come first.
ROUTE = {
    'version': ROUTE_VERSION,
    'time': '1200',
    'repeats': REPEATS,
    'speed_note': 'noclip, +forward with the engine defaults (measured speed recorded per run)',
    'legs': [
        {'name': 'ai-c1', 'region': 'Ascadian Isles', 'weight': 'light', 'kind': 'corner',
         'start': [24124, -49604], 'yaw': 45, 'seconds': 5, 'z': 2600, 'crosses': 'corner 3,-6: cell 2,-7 to 3,-6'},
        {'name': 'ai-c2', 'region': 'Ascadian Isles', 'weight': 'light', 'kind': 'corner',
         'start': [32316, -41412], 'yaw': 45, 'seconds': 5, 'z': 2600, 'crosses': 'corner 4,-5: cell 3,-6 to 4,-5'},
        {'name': 'bc-c1', 'region': 'Bitter Coast', 'weight': 'light', 'kind': 'corner',
         'start': [-25028, -33220], 'yaw': 45, 'seconds': 5, 'z': 3200, 'crosses': 'corner -3,-4: cell -4,-5 to -3,-4'},
        {'name': 'bm-c1', 'region': 'Balmora', 'weight': 'heavy', 'kind': 'corner',
         'start': [-33220, -25028], 'yaw': 45, 'seconds': 5, 'z': 4200,
         'crosses': 'corner -4,-3: cell -5,-4 into the Balmora frame'},
        # corner loops: a square of 1,300 units around a corner, four crossings in about 11 s (walking around a
        # corner, where frames are left and entered again in quick succession)
        {'name': 'ai-l1', 'region': 'Ascadian Isles', 'weight': 'light', 'kind': 'corner-loop', 'loop': True,
         'start': [23926, -49802], 'yaw': 0, 'turns': [[0, 2.8], [90, 2.8], [180, 2.8], [270, 2.8]], 'z': 2600,
         'crosses': 'a square around corner 3,-6 (cells 2,-7 / 3,-7 / 3,-6 / 2,-6)'},
        {'name': 'bm-l1', 'region': 'Balmora', 'weight': 'heavy', 'kind': 'corner-loop', 'loop': True,
         'start': [-32118, -23926], 'yaw': 180, 'turns': [[180, 2.8], [270, 2.8], [0, 2.8], [90, 2.8]], 'z': 4200,
         'crosses': 'a square around corner -4,-3 (cells -5,-4 / -4,-4 / the Balmora frame / -5,-3)'},
        {'name': 'ai-e1', 'region': 'Ascadian Isles', 'weight': 'light', 'kind': 'edge',
         'start': [23936, -45056], 'yaw': 0, 'seconds': 5, 'z': 2600, 'crosses': 'cell 2,-6 to 3,-6'},
        {'name': 'ai-e2', 'region': 'Ascadian Isles', 'weight': 'light', 'kind': 'edge',
         'start': [28672, -41600], 'yaw': 90, 'seconds': 5, 'z': 2600, 'crosses': 'cell 3,-6 to 3,-5'},
        {'name': 'bc-e1', 'region': 'Bitter Coast', 'weight': 'light', 'kind': 'edge',
         'start': [-33408, -36864], 'yaw': 0, 'seconds': 5, 'z': 3200, 'crosses': 'cell -5,-5 to -4,-5'},
        {'name': 'bc-e2', 'region': 'Bitter Coast', 'weight': 'light', 'kind': 'edge',
         'start': [-28672, -33408], 'yaw': 90, 'seconds': 5, 'z': 3200, 'crosses': 'cell -4,-5 to -4,-4'},
        {'name': 'bm-e1', 'region': 'Balmora', 'weight': 'heavy', 'kind': 'edge',
         'start': [-33408, -12288], 'yaw': 0, 'seconds': 5, 'z': 4200, 'crosses': 'cell -5,-2 into the Balmora frame'},
        {'name': 'bm-e2', 'region': 'Balmora', 'weight': 'heavy', 'kind': 'edge',
         'start': [-8832, -12288], 'yaw': 0, 'seconds': 5, 'z': 4200, 'crosses': 'the Balmora frame out to cell -1,-2'},
    ],
}


def route_legs(names=None):
    """The legs by name (route order), or all of them."""
    legs = ROUTE['legs']
    if names:
        wanted = set(names)
        return [leg for leg in legs if leg['name'] in wanted]
    return list(legs)


def leg_base(label):
    """A repeat's label NAME#N belongs to the leg NAME."""
    return label.split('#')[0]


def leg_seconds(leg):
    return sum(t[1] for t in leg['turns']) if leg.get('turns') else leg['seconds']


def corner_distance(x, y):
    """Distance in units from a global point to the nearest cell corner."""
    cx = round(x / CELL) * CELL
    cy = round(y / CELL) * CELL
    return int(math.hypot(x - cx, y - cy))


# ---------------------------------------------------------------- parsing

RE_LOADING = re.compile(r'Loading AmiWind \S+: (\S+)\.\.\.')
RE_SEG = re.compile(r'^seg (\S+)\s*$')
RE_FLIGHT = re.compile(r'^flight (\S+) (start|end)\s*$')
RE_READY = re.compile(r'Scene ready: (\S+), (\d+) ms, (\d+) hunk bytes')
RE_PRIMED = re.compile(r'CHIM: primed: (\d+) active, (\d+) loaded, (\d+) models, (\d+) textures, (\d+) KiB in (\d+) reads, (\d+) ms')
RE_FRAME = re.compile(r'CHIM: map frame (-?\d+) (-?\d+): (\d+) chunks, (\d+) files, (\d+) models, (\d+) textures, zone (\d+) KiB')
RE_MEMORY = re.compile(r'^Memory: .*')
RE_HEAP = re.compile(r'^Heap \S+ \S+: low \d+ high \d+ peak \d+ / (\d+),')


def parse_console(text):
    """Map loads in console order, each with its segment (leg) and whether it happened during the leg's flight."""
    loads, seg, flying, memory, heap = [], 'boot', False, '', None
    cur = None
    for line in text.splitlines():
        line = line.rstrip('\r')
        if not memory and RE_MEMORY.match(line):
            memory = line
        m = RE_HEAP.match(line)
        if m and heap is None:
            heap = int(m.group(1))
        m = RE_SEG.match(line)
        if m:
            seg, flying = m.group(1), False
            continue
        m = RE_FLIGHT.match(line)
        if m:
            flying = m.group(2) == 'start'
            continue
        m = RE_LOADING.search(line)
        if m:
            cur = {'seg': seg, 'map': m.group(1), 'crossing': flying, 'ready_ms': None, 'hunk_bytes': None,
                   'prime_ms': None, 'prime_kib_total': None, 'prime_reads_total': None, 'frame': None}
            loads.append(cur)
            continue
        if cur is None:
            continue
        m = RE_FRAME.search(line)
        if m:
            cur['frame'] = {'x': int(m.group(1)), 'y': int(m.group(2)), 'chunks': int(m.group(3)),
                            'files': int(m.group(4)), 'models': int(m.group(5)), 'textures': int(m.group(6)),
                            'zone_kib': int(m.group(7))}
        m = RE_PRIMED.search(line)
        if m:
            cur['prime_ms'] = int(m.group(7))
            cur['prime_kib_total'] = int(m.group(5))
            cur['prime_reads_total'] = int(m.group(6))
            cur['prime_active'] = int(m.group(1))
            cur['prime_loaded'] = int(m.group(2))
        m = RE_READY.search(line)
        if m and m.group(1) == cur['map']:
            cur['ready_ms'] = int(m.group(2))
            cur['hunk_bytes'] = int(m.group(3))
    # the CHIM read counters are totals since the start: per load, the difference to the previous primed line
    prev_kib = prev_reads = None
    for ld in loads:
        if ld['prime_kib_total'] is not None:
            if prev_kib is not None:
                ld['prime_kib'] = ld['prime_kib_total'] - prev_kib
                ld['prime_reads'] = ld['prime_reads_total'] - prev_reads
            prev_kib, prev_reads = ld['prime_kib_total'], ld['prime_reads_total']
    return {'memory': memory, 'heap_bytes': heap, 'loads': loads}


def parse_cell_load(text):
    """cell-load-profile.tsv rows (aw_stream.c AW_StreamLoadEnd), in load order."""
    rows = []
    for line in text.splitlines():
        p = line.rstrip('\r').split('\t')
        if len(p) < 9 or not p[0].startswith('maps/'):
            continue
        try:
            rows.append({'model': p[0], 'disk_bytes': int(p[2]), 'disk_reads': int(p[3]),
                         'disk_ms': round(float(p[4]) * 1000), 'decode_ms': round(float(p[5]) * 1000),
                         'world_ms': round(float(p[6]) * 1000), 'entities_ms': round(float(p[7]) * 1000),
                         'spawn_ms': round(float(p[8]) * 1000)})
        except ValueError:
            continue
    return rows


def parse_visible(text):
    rows = []
    for line in text.splitlines():
        p = line.rstrip('\r').split('\t')
        if len(p) >= 3 and p[0].startswith('maps/'):
            try:
                rows.append({'model': p[0], 'visible_ms': round(float(p[2]) * 1000)})
            except ValueError:
                pass
    return rows


def parse_stalls(text):
    rows = []
    for line in text.splitlines():
        p = line.strip().split(',')
        if len(p) == 3 and p[0].isdigit():
            rows.append({'time_ms': int(p[0]), 'frame': int(p[1]), 'ms': int(p[2]) // 1000})
    return rows


def parse_walk(text):
    rows = []
    for line in text.splitlines():
        p = line.strip().split(',')
        if len(p) >= 11 and p[0].isdigit():
            rows.append({'frame': int(p[0]), 'map': p[10]})
    return rows


RE_RC = {
    'pk': re.compile(r' pk (\d+)'),
    'frames': re.compile(r'^(\d+) frames'),
    'scb': re.compile(r' scb (\d+)/(\d+)'),
    'rd': re.compile(r' rd (\d+)/(\d+)'),
    'rb': re.compile(r' rb (\d+) (\d+)/(\d+)'),
}


def parse_rcount(line):
    """The rcount fields used here: frames in the second, peak frame (ms), surface cache blocks/texels drawn per
    frame (averages), CHIM KiB/reads in the second, frame-world rebuilds."""
    out = {}
    m = RE_RC['frames'].search(line)
    if m:
        out['frames'] = int(m.group(1))
    m = RE_RC['pk'].search(line)
    if m:
        out['pk_ms'] = int(m.group(1)) // 1000
    m = RE_RC['scb'].search(line)
    if m:
        out['scb_blocks'], out['scb_texels'] = int(m.group(1)), int(m.group(2))
    m = RE_RC['rd'].search(line)
    if m:
        out['rd_kib'], out['rd_reads'] = int(m.group(1)), int(m.group(2))
    m = RE_RC['rb'].search(line)
    if m:
        out['rb'] = int(m.group(1))
    return out


def model_is(model, map_name):
    """maps/NAME.chim, or a CHIM town's frame map maps/NAME-chim.chim, belongs to the map NAME."""
    base = model.split('/')[-1].rsplit('.', 1)[0]
    return base == map_name or base == map_name + '-chim'


def match_by_model(loads, rows, key):
    """Attach rows (cell-load or visible profile) to loads in order, by model name (maps/NAME.*)."""
    j = 0
    for ld in loads:
        k = j
        while k < len(rows) and not model_is(rows[k]['model'], ld['map']):
            k += 1
        if k < len(rows):
            ld[key] = {a: b for a, b in rows[k].items() if a != 'model'}
            j = k + 1


def stall_for(walk, stalls, old, new, after_frame):
    """The crossing frame from walk-profile (last row on OLD, first on NEW after AFTER_FRAME), its stall and the stalls
    of the 3 s after it."""
    last_old = first_new = None
    for r in walk:
        if r['frame'] <= after_frame:
            continue
        if model_is(r['map'], old):
            last_old = r['frame']
        elif model_is(r['map'], new) and last_old is not None:
            first_new = r['frame']
            break
    if first_new is None:
        return None, after_frame
    inside = [s for s in stalls if last_old < s['frame'] <= first_new]
    if not inside:
        return {'frame_ms': 0, 'window_ms': 0, 'window_frames': 0, 'frames': [last_old, first_new]}, first_new
    hit = max(inside, key=lambda s: s['ms'])
    window = [s for s in stalls if hit['time_ms'] <= s['time_ms'] <= hit['time_ms'] + 3000]
    return {'frame_ms': hit['ms'], 'window_ms': sum(s['ms'] for s in window), 'window_frames': len(window),
            'window_max_ms': max(s['ms'] for s in window), 'frames': [last_old, first_new]}, first_new


def parse_session(d):
    d = Path(d)
    con = parse_console((d / 'awctl' / 'console.log').read_text(errors='replace'))
    logs = d / 'hdflogs'

    def read(name):
        p = logs / name
        return p.read_text(errors='replace') if p.exists() else ''

    loads = con['loads']
    match_by_model(loads, parse_cell_load(read('cell-load-profile.tsv')), 'load')
    match_by_model(loads, parse_visible(read('cell-visible-profile.tsv')), 'visible')
    stalls, walk = parse_stalls(read('frame-stalls.csv')), parse_walk(read('walk-profile.csv'))
    samples = []
    sp = d / 'samples.jsonl'
    if sp.exists():
        samples = [json.loads(x) for x in sp.read_text().splitlines() if x.strip()]
    meta = json.loads((d / 'session.json').read_text()) if (d / 'session.json').exists() else {}
    legs = {leg['name']: leg for leg in ROUTE['legs']}
    crossings, prev_map, cursor = [], None, 0
    seg_cursor = {}
    for ld in loads:
        if ld['crossing'] and prev_map:
            leg = legs.get(leg_base(ld['seg']), {})
            st, cursor = stall_for(walk, stalls, prev_map, ld['map'], cursor)
            row = {'leg': ld['seg'], 'kind': leg.get('kind'), 'weight': leg.get('weight'),
                   'region': leg.get('region'), 'from': prev_map, 'to': ld['map'],
                   'ready_ms': ld['ready_ms'], 'prime_ms': ld['prime_ms'],
                   'prime_kib': ld.get('prime_kib'), 'prime_reads': ld.get('prime_reads'),
                   'frame': ld['frame'], 'load': ld.get('load'), 'visible': ld.get('visible'), 'stall': st}
            if ld.get('load') and ld['prime_ms'] is not None and ld['ready_ms'] is not None:
                spawn = ld['load']['spawn_ms']
                row['split_ms'] = {
                    'map_read': ld['load']['disk_ms'],
                    'map_parse': max(0, ld['load']['world_ms'] - ld['load']['disk_ms']),
                    'entities': ld['load']['entities_ms'],
                    'server_rest': max(0, spawn - ld['load']['world_ms'] - ld['load']['entities_ms']),
                    'ring_prime': ld['prime_ms'],
                    'other_to_ready': max(0, ld['ready_ms'] - spawn - ld['prime_ms']),
                }
                if ld.get('visible'):
                    row['split_ms']['ready_to_visible'] = max(0, ld['visible']['visible_ms'] - ld['ready_ms'])
            # the state samples of this leg's flight: crossing point, the two seconds after it
            # (a corner loop crosses several times in one flight: search on from the previous crossing's sample)
            fl = [s for s in samples if s.get('leg') == ld['seg'] and s.get('flight')]
            start = seg_cursor.get(ld['seg'], 0)
            first = next((i for i, s in enumerate(fl) if i > start and s.get('server') == ld['map']
                          and fl[i - 1].get('server') != ld['map']), None)
            if first is not None:
                # the approach: the worst rendered frame of the flight's seconds before this crossing (since the
                # previous crossing on a corner loop)
                before = []
                for s in fl[start:first]:
                    rc = s.get('rcount')
                    if rc and rc not in before:
                        before.append(rc)
                if start:
                    before = before[2:]     # the previous crossing's own two seconds are not approach
                if before:
                    row['approach_peak_ms'] = max(parse_rcount(rc).get('pk_ms', 0) for rc in before)
                seg_cursor[ld['seg']] = first
                # the state file can show one stale position at the switch: the first new-map sample within 1500
                # units of the last old-map one
                a = fl[max(0, first - 1)]
                b = next((s for s in fl[first:] if s.get('global') and a.get('global') and
                          math.hypot(s['global'][0] - a['global'][0], s['global'][1] - a['global'][1]) < 1500), None)
                if a.get('global') and b:
                    x = (a['global'][0] + b['global'][0]) / 2
                    y = (a['global'][1] + b['global'][1]) / 2
                    row['at'] = [int(x), int(y)]
                    row['corner_distance'] = corner_distance(x, y)
                after = []
                # the rcount line still showing at the switch is the second before it
                seen = {a.get('rcount')}
                for s in fl[first:]:
                    rc = s.get('rcount')
                    if rc and rc not in seen:
                        seen.add(rc)
                        after.append(parse_rcount(rc))
                    if len(after) >= 3:
                        break
                if after and not row['stall']:
                    # no frame-stall log: the longest frame of the first two rcount seconds after the switch (the
                    # same number as the stall log where both exist), no 3 s window
                    row['stall'] = {'frame_ms': max(r.get('pk_ms', 0) for r in after[:2]), 'source': 'rcount'}
                if after:
                    row['after_3s'] = {
                        'chim_kib': sum(r.get('rd_kib', 0) for r in after),
                        'chim_reads': sum(r.get('rd_reads', 0) for r in after),
                        'surface_blocks': sum(r.get('scb_blocks', 0) * r.get('frames', 0) for r in after),
                        'surface_texels': sum(r.get('scb_texels', 0) * r.get('frames', 0) for r in after),
                        'peak_ms': max(r.get('pk_ms', 0) for r in after),
                    }
            crossings.append(row)
        prev_map = ld['map']
    teleports = [{'leg': ld['seg'], 'map': ld['map'], 'ready_ms': ld['ready_ms']} for ld in loads if not ld['crossing']]
    speed = None
    for label in sorted({s.get('leg') for s in samples if s.get('leg')}):
        fl = [s for s in samples if s.get('leg') == label and s.get('flight') and s.get('global')]
        for p, q in zip(fl, fl[1:]):
            dist = math.hypot(q['global'][0] - p['global'][0], q['global'][1] - p['global'][1])
            if q['t'] > p['t'] and 0 < dist < 1500:
                speed = speed or []
                speed.append(dist / (q['t'] - p['t']))
    return {'session': d.name, 'memory': con['memory'], 'heap_bytes': con.get('heap_bytes'),
            'meta': meta, 'route_version': meta.get('route_version', ROUTE_VERSION),
            'speed_units_s': int(statistics.median(speed)) if speed else None,
            'crossings': crossings, 'teleports': teleports, 'stall_rows': len(stalls), 'walk_rows': len(walk)}


# ---------------------------------------------------------------- table

def _med(v):
    v = [x for x in v if x is not None]
    return int(statistics.median(v)) if v else None


def _max(v):
    v = [x for x in v if x is not None]
    return max(v) if v else None


def _fmt(v):
    return '-' if v is None else str(v)


def table(runs):
    """Markdown: one row per memory size and crossing kind (edge, corner), and per weight (light, heavy)."""
    groups = {}
    for run in runs:
        mem = run.get('meta', {}).get('fast_mb') or '?'
        for c in run['crossings']:
            for key in ((mem, c['kind'], 'all'), (mem, c['kind'], c['weight'])):
                groups.setdefault(key, []).append(c)
    lines = ['| Fast RAM | Crossing | Where | Crossings | Stall frame median / max (ms) | Stall 3 s median / max (ms) '
             '| Ready median / max (ms) | Map file KiB / reads (median) | Ring KiB / reads (median) '
             '| Surface cache texels drawn, 3 s after (thousands, median) | Approach worst frame median / max (ms) |',
             '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']

    def mem_key(k):
        try:
            return int(k)
        except (TypeError, ValueError):
            return 0
    for key in sorted(groups, key=lambda k: (mem_key(k[0]), k[1] or '', {'all': 0, 'light': 1, 'heavy': 2}.get(k[2], 3))):
        cs = groups[key]
        sf = [c['stall']['frame_ms'] if c.get('stall') else None for c in cs]
        sw = [c['stall'].get('window_ms') if c.get('stall') else None for c in cs]
        rd = [c['ready_ms'] for c in cs]
        mk = [(c['load']['disk_bytes'] + 1023) // 1024 if c.get('load') else None for c in cs]
        mr = [c['load']['disk_reads'] if c.get('load') else None for c in cs]
        rk = [c.get('prime_kib') for c in cs]
        rr = [c.get('prime_reads') for c in cs]
        sb = [c['after_3s']['surface_texels'] // 1000 if c.get('after_3s') else None for c in cs]
        ap = [c.get('approach_peak_ms') for c in cs]
        lines.append('| %s MB | %s | %s | %d | %s / %s | %s / %s | %s / %s | %s / %s | %s / %s | %s | %s / %s |' % (
            key[0], key[1], key[2], len(cs), _fmt(_med(sf)), _fmt(_max(sf)), _fmt(_med(sw)), _fmt(_max(sw)),
            _fmt(_med(rd)), _fmt(_max(rd)), _fmt(_med(mk)), _fmt(_med(mr)), _fmt(_med(rk)), _fmt(_med(rr)),
            _fmt(_med(sb)), _fmt(_med(ap)), _fmt(_max(ap))))
    return '\n'.join(lines) + '\n'


def split_table(runs):
    """Markdown: median milliseconds per section of a crossing, per memory size, kind and weight."""
    groups = {}
    for run in runs:
        mem = run.get('meta', {}).get('fast_mb') or '?'
        for c in run['crossings']:
            if c.get('split_ms'):
                groups.setdefault((mem, c['kind'], c.get('weight')), []).append(c['split_ms'])
    names = ['map_read', 'map_parse', 'entities', 'server_rest', 'ring_prime', 'other_to_ready', 'ready_to_visible']
    lines = ['| Fast RAM | Crossing | Where | n | ' + ' | '.join(n.replace('_', ' ') for n in names) + ' |',
             '| --- | --- | --- | --- | ' + ' | '.join('---' for _ in names) + ' |']
    for key in sorted(groups, key=lambda k: (int(k[0]) if str(k[0]).isdigit() else 0, k[1] or '', k[2] or '')):
        rows = groups[key]
        lines.append('| %s MB | %s | %s | %d | %s |' % (key[0], key[1], key[2], len(rows),
                                                        ' | '.join(_fmt(_med([r.get(n) for r in rows])) for n in names)))
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------- session (inside an FS-UAE container)

class Session:
    def __init__(self, a):
        self.a = a
        self.out = Path(a.out)
        self.awctl = self.out / 'awctl'
        self.logs = self.out / 'logs'
        for p in (self.awctl, self.logs, self.out / 'home', self.out / 'clips'):
            p.mkdir(parents=True, exist_ok=True)
        self.display = str(a.display)
        self.env = dict(os.environ, HOME=str(self.out / 'home'), DISPLAY=':' + self.display,
                        LIBGL_ALWAYS_SOFTWARE='1', GALLIUM_DRIVER='llvmpipe', SDL_AUDIODRIVER='dummy')
        self.procs = []
        self.samples = (self.out / 'samples.jsonl').open('a', encoding='utf-8', newline='\n')
        self.t0 = time.time()

    def log(self, text):
        line = '%s %s' % (time.strftime('%H:%M:%S'), text)
        print(line, flush=True)
        with (self.logs / 'commands.log').open('a', encoding='utf-8', newline='\n') as f:
            f.write(line + '\n')

    def start(self):
        a = self.a
        cfg = ['[config]', 'amiga_model = A1200', 'cpu = 68040-NOMMU', 'fpu = 68040',
               'uae_cpu_24bit_addressing = false', 'chip_memory = 2048', 'slow_memory = 0', 'fast_memory = 0',
               'zorro_iii_memory = %d' % (a.fast_mb * 1024), 'kickstart_file = %s' % a.kickstart,
               'hard_drive_0 = %s' % a.hdf, 'hard_drive_0_type = hdf',
               'hard_drive_1 = %s' % self.awctl, 'hard_drive_1_label = AWCTL', 'hard_drive_1_priority = -128',
               'joystick_port_1 = none', 'middle_click_ungrab = 0', 'floppy_drive_volume = 0', 'fullscreen = 0',
               'window_width = 800', 'window_height = 600', 'initial_input_grab = 0', 'automatic_input_grab = 0',
               'jit_compiler = 1', 'uae_cpu_speed = max', 'base_dir = %s' % (self.out / 'home' / 'fs-uae')]
        (self.out / 'amiwind.fs-uae').write_text('\n'.join(cfg) + '\n', encoding='utf-8', newline='\n')
        if a.audio:
            run = self.out / 'home' / 'run'
            run.mkdir(exist_ok=True)
            self.env.update(SDL_AUDIODRIVER='pulseaudio', XDG_RUNTIME_DIR=str(run))
            subprocess.run(['pulseaudio', '-D', '--exit-idle-time=-1', '--disallow-exit', '-n',
                            '--load=module-native-protocol-unix', '--load=module-null-sink sink_name=aw'],
                           env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)
            subprocess.run(['pactl', 'set-default-sink', 'aw'], env=self.env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.procs.append(subprocess.Popen(['Xvfb', ':' + self.display, '-screen', '0', '1024x768x24', '-nolisten',
                                            'tcp', '+extension', 'GLX'], env=self.env,
                                           stdout=(self.logs / 'xvfb.log').open('w', encoding='utf-8', newline='\n'), stderr=subprocess.STDOUT))
        time.sleep(2)
        self.fsuae = subprocess.Popen(['fs-uae', str(self.out / 'amiwind.fs-uae')], env=self.env,
                                      stdout=(self.logs / 'fsuae.log').open('w', encoding='utf-8', newline='\n'), stderr=subprocess.STDOUT)
        self.procs.append(self.fsuae)

    def alive(self):
        return self.fsuae.poll() is None

    def xdo(self, *args):
        w = subprocess.run(['xdotool', 'search', '--name', 'FS-UAE'], env=self.env, capture_output=True, text=True)
        win = (w.stdout.split() or [''])[0]
        if win:
            subprocess.run(['xdotool', 'windowfocus', '--sync', win], env=self.env, capture_output=True)
        subprocess.run(['xdotool'] + list(args), env=self.env, capture_output=True)

    def console_line(self, text):
        self.xdo('key', '--clearmodifiers', 'F10')
        time.sleep(1)
        self.xdo('type', '--clearmodifiers', '--delay', '40', '--', text)
        time.sleep(0.3)
        self.xdo('key', '--clearmodifiers', 'Return')

    def rc(self, text, wait=0.0):
        cmd = self.awctl / 'cmd.txt'
        for _ in range(80):
            if not cmd.exists():
                break
            time.sleep(0.25)
        tmp = self.awctl / 'cmd.txt.tmp'
        tmp.write_text(text + '\n', encoding='utf-8', newline='\n')
        tmp.replace(cmd)
        with (self.logs / 'commands.log').open('a', encoding='utf-8', newline='\n') as f:
            f.write('%s rc %s\n' % (time.strftime('%H:%M:%S'), text))
        if wait:
            time.sleep(wait)

    def state(self):
        p = self.awctl / 'state.txt'
        for _ in range(4):
            try:
                text = p.read_text(errors='replace')
            except OSError:
                text = ''
            if text.rstrip().endswith('end'):
                out = {}
                for line in text.splitlines():
                    k, _, v = line.partition(' ')
                    out[k] = v
                return out
            time.sleep(0.1)
        return {}

    @staticmethod
    def floats(v):
        try:
            return [float(x) for x in v.split()]
        except (AttributeError, ValueError):
            return None

    def sample(self, leg, flight):
        s = self.state()
        row = {'t': round(time.time() - self.t0, 2), 'leg': leg, 'flight': flight, 'server': s.get('server'),
               'global': self.floats(s.get('global')), 'angles': self.floats(s.get('angles')),
               'rcount': s.get('rcount')}
        self.samples.write(json.dumps(row) + '\n')
        self.samples.flush()
        return row

    def wait(self, seconds, test):
        end = time.time() + seconds
        while time.time() < end:
            if test():
                return True
            if not self.alive():
                raise RuntimeError('emulator gone')
            time.sleep(1)
        return False

    def settle(self, quiet=4, limit=90):
        """Until the CHIM streamer reads nothing for QUIET consecutive rcount lines (the ring is loaded)."""
        q, last, end = 0, None, time.time() + limit
        while q < quiet and time.time() < end:
            rc = self.state().get('rcount')
            if rc and rc != last:
                last = rc
                f = parse_rcount(rc)
                q = q + 1 if f.get('rd_kib', 0) == 0 and f.get('rd_reads', 0) == 0 and f.get('rb', 0) == 0 else 0
            if not self.alive():
                raise RuntimeError('emulator gone')
            time.sleep(0.5)
        return q >= quiet

    def aim(self, yaw, pitch):
        def aimed():
            ang = self.floats(self.state().get('angles'))
            return bool(ang) and abs(ang[0] - pitch) < 1.5 and \
                min(abs(ang[1] - yaw) % 360, 360 - abs(ang[1] - yaw) % 360) < 1.5
        for _ in range(6):
            self.rc('aw_aim %s %s' % (yaw, pitch))
            end = time.time() + 2.5
            while time.time() < end:
                time.sleep(0.2)
                if aimed():
                    return True
        self.log('aim %s %s not confirmed: %s' % (yaw, pitch, self.state().get('angles')))
        return False

    def boot(self):
        # the image's autoexec turns the remote console on: state.txt appears as soon as the engine runs
        self.wait(40, lambda: (self.awctl / 'state.txt').exists())
        n = 0
        while not (self.awctl / 'state.txt').exists() and n < 240:
            if not self.alive():
                raise RuntimeError('emulator gone during boot')
            self.console_line('aw_remote 1')
            time.sleep(2)
            self.xdo('key', '--clearmodifiers', 'Escape')
            time.sleep(20)
            n += 22
        if not self.wait(20, lambda: (self.awctl / 'state.txt').exists()):
            raise RuntimeError('no state.txt after boot')
        self.rc('early_game_demo_start_1 1; aw_demo_start')
        if not self.wait(300, lambda: self.state().get('server') not in (None, '', 'none')):
            raise RuntimeError('demo start failed')
        time.sleep(5)
        self.log('in game after %d s: %s' % (time.time() - self.t0, self.state().get('server')))
        for c in ['version', 'dbg daynightcycle off', 'dbg set time %s' % ROUTE['time'], 'dbg headlamp off',
                  'aw_logs_live 0', 'aw_npc_movers 0', 'showpause 0', 'con_notifytime 3', 'aw_rcount 2', 'chim_debug 1', 'chim',
                  'aw_savelogs', 'noclip']:
            self.rc(c, 0.3)
        for c in [x.strip() for x in self.a.extra.split(';') if x.strip()]:
            self.rc(c, 1)

    def ready_count(self):
        try:
            return (self.awctl / 'console.log').read_text(errors='replace').count('Scene ready: ')
        except OSError:
            return 0

    def noclip_on(self):
        text = (self.awctl / 'console.log').read_text(errors='replace')
        last = max(text.rfind('noclip ON'), text.rfind('noclip OFF'))
        if last < 0 or text.startswith('noclip OFF', last):
            self.rc('noclip', 2)

    def leg(self, leg, capture=False, label=None):
        name = label or leg['name']
        self.rc('echo seg %s' % name, 0.3)
        self.noclip_on()
        # the start point; where the teleport finds no clear standing surface (the engine then uses the scene
        # spawn), the same line further back: 256 units a try, so the crossing stays inside the flight
        back = (-math.cos(math.radians(leg['yaw'])), -math.sin(math.radians(leg['yaw'])))
        reached = False
        for k in range(4):
            x, y = int(leg['start'][0] + back[0] * 256 * k), int(leg['start'][1] + back[1] * 256 * k)
            before = self.ready_count()
            self.rc('dbg tp %d %d' % (x, y))
            self.wait(150, lambda: self.ready_count() > before)
            if self.wait(12, lambda: (lambda g: bool(g) and math.hypot(g[0] - x, g[1] - y) < 300)(
                    self.floats(self.state().get('global')))):
                reached = True
                break
            self.log('%s: start %d %d not reached (global %s), moving back' % (name, x, y, self.state().get('global')))
        if not reached:
            return False
        self.rc('echo start %s %d %d' % (name, x, y), 0.3)
        self.noclip_on()
        g = self.floats(self.state().get('global'))
        if g and g[2] < leg['z'] + self.a.z_offset - 100:
            # straight up (noclip upmove), so the start point stays where it is
            self.aim(leg['yaw'], 0)
            self.rc('+moveup')
            end = time.time() + 60
            while time.time() < end:
                h = self.floats(self.state().get('global'))
                if h and h[2] >= leg['z'] + self.a.z_offset - 150:
                    break
                time.sleep(0.15)
            self.rc('-moveup', 0.5)
        self.aim(leg['yaw'], 0)
        # settled: two rcount seconds in a row with no CHIM read and no frame-world update
        self.settle(2, 60)
        self.rc('aw_savelogs', 1)
        self.log('%s start %s %s' % (name, self.state().get('global'), self.state().get('angles')))
        ff = None
        if capture:
            ff = self.capture_start(name, leg_seconds(leg) + 2)
        self.rc('echo flight %s start' % name, 0.5)
        self.rc('+forward')
        turns = leg.get('turns') or [[leg['yaw'], leg['seconds']]]
        for i, (yaw, seconds) in enumerate(turns):
            if i:
                # a turn of a corner loop, halfway between two crossings: the diagnostic logs are written here
                # so the small walk-profile buffer never drops a crossing's frames
                self.rc('aw_aim %s 0; aw_savelogs' % yaw)
            end = time.time() + seconds
            while time.time() < end:
                self.sample(name, True)
                time.sleep(0.25)
            if not self.alive():
                raise RuntimeError('emulator gone in flight')
        self.rc('-forward')
        self.rc('echo flight %s end' % name)
        for _ in range(4):
            self.sample(name, True)
            time.sleep(0.5)
        if ff:
            ff.wait()
        self.rc('aw_savelogs', 1)
        self.log('%s done %s' % (name, self.state().get('global')))
        return True

    def ground(self, leg, points=6, length=4200):
        """Calibration only (never in a measured run): the ground height at POINTS spots along the leg."""
        x0, y0 = leg['start']
        dx, dy = math.cos(math.radians(leg['yaw'])), math.sin(math.radians(leg['yaw']))
        heights = []
        for k in range(points):
            x, y = int(x0 + dx * length * k / (points - 1)), int(y0 + dy * length * k / (points - 1))
            self.rc('dbg tp %d %d' % (x, y))
            near = lambda: (lambda g: bool(g) and math.hypot(g[0] - x, g[1] - y) < 300)(self.floats(self.state().get('global')))
            self.wait(120, near)
            time.sleep(3)
            g = self.floats(self.state().get('global'))
            heights.append(int(g[2]) if g else None)
        self.log('ground %s %s' % (leg['name'], heights))
        with (self.out / 'ground.jsonl').open('a', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps({'leg': leg['name'], 'heights': heights}) + '\n')

    def capture_start(self, name, seconds):
        args = ['ffmpeg', '-loglevel', 'error', '-y', '-f', 'x11grab', '-draw_mouse', '0', '-framerate', '25',
                '-video_size', '1024x768', '-t', str(seconds), '-i', ':' + self.display]
        if self.a.audio:
            args += ['-f', 'pulse', '-t', str(seconds), '-i', 'aw.monitor', '-c:a', 'aac', '-b:a', '96k']
        args += ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24', '-pix_fmt', 'yuv420p',
                 str(self.out / 'clips' / (name + '-raw.mp4'))]
        return subprocess.Popen(args, env=self.env, stdout=(self.logs / ('ffmpeg-%s.log' % name)).open('w', encoding='utf-8', newline='\n'),
                                stderr=subprocess.STDOUT)

    def stop(self):
        try:
            if self.alive():
                self.rc('aw_savelogs', 3)
        finally:
            for p in reversed(self.procs):
                if p.poll() is None:
                    p.terminate()
            time.sleep(3)
            for p in self.procs:
                if p.poll() is None:
                    p.kill()
            if self.a.audio:
                subprocess.run(['pulseaudio', '-k'], env=self.env, capture_output=True)
            shutil.copy(self.awctl / 'console.log', self.logs / 'console.log') if (self.awctl / 'console.log').exists() else None

    def read_logs(self):
        """The engine's diagnostic logs, from the play copy's boot partition (written there by aw_savelogs)."""
        dest = self.out / 'hdflogs'
        dest.mkdir(exist_ok=True)
        for name in ('cell-load-profile.tsv', 'cell-visible-profile.tsv', 'frame-stalls.csv', 'walk-profile.csv',
                     'frame-profile.txt'):
            r = subprocess.run([self.a.xdftool, self.a.hdf, 'open', 'part=DH0', '+', 'read', name, str(dest / name)],
                               capture_output=True, text=True)
            if r.returncode:
                self.log('reading %s from the play copy failed (%d): %s' % (name, r.returncode,
                                                                           (r.stdout + r.stderr).strip()[-300:]))


def run_session(a):
    s = Session(a)
    meta = {'route_version': ROUTE_VERSION, 'fast_mb': a.fast_mb, 'label': a.label, 'started': time.strftime('%Y-%m-%d %H:%M:%S %z'),
            'legs': [leg['name'] for leg in route_legs(a.legs)], 'repeats': a.repeats, 'capture': a.capture,
            'preset': 'FS-UAE JIT, 68040, A1200'}
    (s.out / 'session.json').write_text(json.dumps(meta, indent=1) + '\n', encoding='utf-8', newline='\n')
    rc = 0
    try:
        s.start()
        s.boot()
        meta['first_crossing_s'] = None
        for leg in route_legs(a.legs):
            if a.ground:
                s.noclip_on()
                s.ground(leg)
                continue
            for n in range(1, a.repeats + 1):
                label = '%s#%d' % (leg['name'], n)
                if meta['first_crossing_s'] is None:
                    meta['first_crossing_s'] = round(time.time() - s.t0)
                if not s.leg(leg, capture=(leg['name'] == a.capture and n == 1), label=label):
                    rc = 2
    except RuntimeError as e:
        s.log('stopped: %s' % e)
        rc = 1
    finally:
        s.stop()
        s.read_logs()
        meta['ended'] = time.strftime('%Y-%m-%d %H:%M:%S %z')
        meta['result'] = rc
        (s.out / 'session.json').write_text(json.dumps(meta, indent=1) + '\n', encoding='utf-8', newline='\n')
    return rc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('route')
    se = sub.add_parser('session')
    se.add_argument('--hdf', required=True, help='a fresh writable play copy of the game image')
    se.add_argument('--kickstart', required=True)
    se.add_argument('--fast-mb', type=int, required=True, help='Zorro III Fast RAM in MB (16, 128)')
    se.add_argument('--out', required=True)
    se.add_argument('--label', default='')
    se.add_argument('--legs', nargs='*')
    se.add_argument('--repeats', type=int, default=REPEATS, help='flights of each leg in a row (teleport back each time)')
    se.add_argument('--extra', default='', help='console commands after the start, separated by ";" (diagnostics)')
    se.add_argument('--z-offset', type=int, default=0, help='added to every leg\'s flight height (clips closer to the '
                    'ground; not for measurements)')
    se.add_argument('--capture', default='', help='record this leg as a clip')
    se.add_argument('--audio', action='store_true')
    se.add_argument('--display', type=int, default=77)
    se.add_argument('--xdftool', default='xdftool')
    se.add_argument('--ground', action='store_true', help='calibration: ground heights along each leg, no flights')
    pa = sub.add_parser('parse')
    pa.add_argument('session')
    pa.add_argument('--json')
    ta = sub.add_parser('table')
    ta.add_argument('runs', nargs='+')
    a = ap.parse_args(argv)
    if a.cmd == 'route':
        print(json.dumps(ROUTE, indent=1))
        return 0
    if a.cmd == 'session':
        return run_session(a)
    if a.cmd == 'parse':
        r = parse_session(a.session)
        text = json.dumps(r, indent=1) + '\n'
        if a.json:
            Path(a.json).write_text(text, encoding='utf-8', newline='\n')
        else:
            sys.stdout.write(text)
        return 0
    runs = [json.loads(Path(p).read_text()) for p in a.runs]
    sys.stdout.write(table(runs) + '\n' + split_table(runs))
    return 0


if __name__ == '__main__':
    sys.exit(main())
