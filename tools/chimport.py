#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""CHIMport: convert the whole island to CHIM cell by cell, from the sea inwards, and audit every cell.

    chimport.py plan   --data-files DIR --out RUN [--rings N] [--cells "x,y x,y"]
    chimport.py run    --data-files DIR --palette PALETTE.lmp --out RUN [--qbsp QBSP] [--workers N] [--jobs N]
                       [--rings N] [--cells "x,y ..."] [--retry-failed] [--timeout S] [--dry-run]
    chimport.py cell   --data-files DIR --palette PALETTE.lmp --cell X,Y --out CELLDIR [--unit-cache DIR] ...
    run, cell, world:  [--storage-pool auto|on|off] [--reuse-mode copy|hardlink|pool] [--storage-pool-dir DIR]
    plan, run:         [--region NAME]  (the cells of a region of plan.json; repeatable)
    chimport.py status --out RUN
    chimport.py export --out RUN [--csv FILE] [--json FILE]

Every exterior cell of the base master becomes its own CHIM frame (one cell = 2048 x 2048 map units,
8 x 8 chunks), built by the CHIM builder (tools/chim/build.py) with ALL its placed records: terrain,
statics, flora, lights, doors, containers, activators and items as meshes; NPCs, creatures and
markers are recorded as deferred with the converter's reason. Every cell is then run through the
mechanism audits the builder has (world format validation, sky-bank texels, terrain seams and
coverage, stair walk, CHIM heap rings, standing-hull chain depth, visibility rows) and its figures
are recorded (docs/chim/CHIMPORT.md).

Order: the plan's rings. Ring 0 = sea cells without land that hold anything (wrecks, rocks, kelp,
creatures); ring 1 = land cells touching the sea; ring 2 the next layer in, and so on (the same onion
peel as the CHIM Progress Tracker's spiral). Inside a ring the walk steps to the nearest unvisited
cell so the converted area grows contiguously.

Run folder (private: everything in it is derived from your own game files):
  plan.json            the order (cells, rings, census per cell)
  state.json           per cell: pending, done, failed (+ attempts); a restart continues from here
  units/               the shared unit cache (store once: meshes, variants, textures converted once)
  cells/xNN_yNN/       the cell's CHIM world, reports and result.json (format aw-chimport-cell-1)
  progress.jsonl       one line per finished cell (time, CPU, result): the perf ledger's input
  STOP                 create it to stop starting new cells (running cells finish)
  run.lock             held by the one `run` writing state.json; a second `run` on the folder refuses

With --storage-pool on every unit and cell output is stored once in the shared storage pool (tools/storage_pool.py,
the builder's pool; --storage-pool-dir names one pool for builds and the CHIMporter) and hard-linked into the run;
units and whole cells whose key is already there are linked, not converted again. Every run reports stored vs
linked bytes and units reused / computed / failed (summary.json "pool", state.json "pool").

A failing cell never stops the run: its error is recorded with a mechanism class, and the run moves on.
Failures are reported grouped by mechanism so they get fixed once at the shared layer.
"""
import argparse
import collections
import contextlib
import csv
import datetime
import io
import json
import math
import os
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

PLAN_FORMAT = 'aw-chimport-plan-1'
STATE_FORMAT = 'aw-chimport-state-1'
CELL_FORMAT = 'aw-chimport-cell-1'
CELL_UNITS = 8192                       # Morrowind units per exterior cell
SCALE = 0.25                            # world scale of every converted frame
HALF = int(CELL_UNITS * SCALE) // 2       # 1024 map units: half a cell
# World settings of a one-cell frame: 8 x 8 chunks of 256 units; sectors must divide 8 (Balmora's 3 x 3 cell
# frame uses 3), so a cell frame stores 4 x 4 chunk sectors.
FRAME_SETTINGS = {'grain': 256, 'sector_chunks': 4}
NEIGHBOURS = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]
MECHANISMS = ('format_validation', 'sky_bank_texels', 'seam_tears', 'far_terrain', 'stair_walk', 'memory_fit',
              'hull_bevels', 'hidden_faces', 'sprite_shape', 'actor_grounding', 'door_links', 'vis')
# Record tags of the base master by category (stats); flora = flora_* ids (statics and containers).
CATEGORIES = collections.OrderedDict([
    ('statics', ('STAT',)), ('lights', ('LIGH',)), ('doors', ('DOOR',)), ('containers', ('CONT',)),
    ('activators', ('ACTI',)), ('actors', ('NPC_',)), ('creatures', ('CREA', 'LEVC')),
    ('items', ('MISC', 'WEAP', 'ARMO', 'CLOT', 'REPA', 'APPA', 'LOCK', 'PROB', 'INGR', 'BOOK', 'ALCH', 'LEVI')),
])
# Error text -> mechanism class (first match wins). A class names WHY, so it is fixed once for every cell.
ERROR_CLASSES = [
    ('runner-usage', r'usage: chimport\.py'),
    ('measure-empty-world', r'max\(\) iterable argument is empty|min\(\) iterable argument is empty'),
    ('missing-terrain', r'missing terrain|Selected square has missing'),
    ('scenery-conversion', r'conversion incomplete|conversion-errors'),
    ('sub-cell-partition', r'Sub-cell|Region directory|Overlap must cover'),
    ('stair-walk', r'Stair walkability gate|Stair gate'),
    ('heap-ring', r'CHIM heap gate'),
    ('world-validation', r'fails validation|does not read back'),
    ('collision-union', r'qbsp|collision union'),
    ('mesh-conversion', r'NIF|nif|mesh'),
    ('terrain-range', r'Height cannot fit|terrain|TERRAIN'),
    ('timeout', r'timed out|Timeout'),
    ('memory', r'MemoryError|Killed|out of memory'),
]


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec='seconds')


def ckey(cell):
    return '%d,%d' % tuple(cell)


def parse_cells(text):
    out = []
    for part in re.split(r'[\s;]+', (text or '').strip()):
        if part:
            x, _, y = part.partition(',')
            out.append((int(x), int(y)))
    return out


def cell_dir(cell):
    return 'x%+03d_y%+03d' % tuple(cell)


def write_json(path, value, pretty=True):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=1 if pretty else None, sort_keys=True, separators=None if pretty else (',', ':'))
    tmp = path.with_name(path.name + '.%d.tmp' % os.getpid())
    tmp.write_bytes((text + '\n').encode('utf-8'))
    tmp.replace(path)


def read_json(path):
    path = Path(path)
    return json.loads(path.read_bytes().decode('utf-8')) if path.is_file() else None


def classify(message):
    for name, pattern in ERROR_CLASSES:
        if re.search(pattern, message or ''):
            return name
    return 'other'


# ------------------------------------------------------------------ plan: census and order

def category_of(tag, object_id):
    if tag in ('STAT', 'CONT') and object_id.lower().startswith('flora_'):
        return 'flora'
    for name, tags in CATEGORIES.items():
        if tag in tags:
            return name
    return 'other'


def census(esm):
    """{(x, y): {land, name, region, refs, by_type, categories, meshes}} for every exterior cell that has land
    or placed records (the base master's own records; deleted references left out)."""
    from mwad.audit import normpath
    out = {}
    for key in set(esm['cells']) | set(esm['lands']):
        cell = esm['cells'].get(key, {'name': '', 'region': '', 'refs': []})
        refs = [r for r in cell['refs'] if not r.get('deleted')]
        by_type, cats, meshes, missing = collections.Counter(), collections.Counter(), set(), 0
        for r in refs:
            obj = esm['objects'].get(r['id'].lower())
            if obj is None:
                missing += 1
                by_type['(missing object)'] += 1
                continue
            by_type[obj['type']] += 1
            cats[category_of(obj['type'], r['id'])] += 1
            if obj['model']:
                meshes.add('meshes/' + normpath(obj['model']))
        if key not in esm['lands'] and not refs:
            continue
        out[key] = {'land': key in esm['lands'], 'name': cell['name'], 'region': cell['region'], 'refs': len(refs),
                    'by_type': dict(by_type), 'categories': dict(cats), 'missing_objects': missing,
                    'meshes': sorted(meshes)}
    return out


def rings(land):
    """{cell: ring} by onion peel: ring 1 = land touching non-land (8 neighbours), then inwards."""
    remaining, out, k = set(land), {}, 1
    while remaining:
        layer = [c for c in remaining if any((c[0] + dx, c[1] + dy) not in remaining for dx, dy in NEIGHBOURS)]
        for c in layer or list(remaining):
            out[c] = k
        remaining.difference_update(layer or list(remaining))
        k += 1
    return out


def _clockwise(cell, centre):
    return math.atan2(cell[0] - centre[0], cell[1] - centre[1]) % (2 * math.pi)


def walk(cells, start_near, centre):
    """One ring: nearest unvisited cell next, clockwise on ties, starting next to start_near."""
    todo = sorted(cells)
    if not todo:
        return []
    if start_near is None:
        cur = min(todo, key=lambda c: (_clockwise(c, centre), c))
    else:
        cur = min(todo, key=lambda c: ((c[0] - start_near[0]) ** 2 + (c[1] - start_near[1]) ** 2,
                                       _clockwise(c, centre), c))
    order = [cur]
    todo.remove(cur)
    while todo:
        here, ang = cur, _clockwise(cur, centre)
        cur = min(todo, key=lambda c: ((c[0] - here[0]) ** 2 + (c[1] - here[1]) ** 2,
                                       (_clockwise(c, centre) - ang) % (2 * math.pi), c))
        order.append(cur)
        todo.remove(cur)
    return order


def order_cells(cells):
    """[(cell, ring)]: ring 0 (sea cells with content, walked around the island's centre), then the land
    rings outside in. cells: {cell: {land, refs}}."""
    land = {c for c, v in cells.items() if v['land']}
    sea = {c for c, v in cells.items() if not v['land'] and v['refs']}
    centre = ((sum(c[0] for c in land) / len(land), sum(c[1] for c in land) / len(land)) if land else (0.0, 0.0))
    ring_of = rings(land)
    out = [(c, 0) for c in walk(sea, None, centre)]
    last = out[-1][0] if out else None
    by_ring = collections.defaultdict(list)
    for c, k in ring_of.items():
        by_ring[k].append(c)
    for k in sorted(by_ring):
        w = walk(by_ring[k], last, centre)
        out.extend((c, k) for c in w)
        last = w[-1]
    return out


def make_plan(data_files):
    from mwad.audit import load_esm
    from mwad.paths import child_ci, resolve_data_files
    data = resolve_data_files(data_files)
    esm = load_esm(child_ci(data, 'Morrowind.esm'))
    cells = census(esm)
    order = order_cells(cells)
    rows = []
    for i, (c, ring) in enumerate(order, 1):
        v = cells[c]
        rows.append(dict(v, x=c[0], y=c[1], ring=ring, order=i))
    return {'format': PLAN_FORMAT, 'generated': now_iso(), 'master': 'Morrowind.esm', 'esm_sha256': esm['sha256'],
            'rule': 'ring 0 = sea cells without land that hold records; ring 1 = land touching the sea; inwards',
            'cells': rows}


def region_names(plan):
    return sorted({r.get('region') or '' for r in plan['cells']} - {''})


def match_regions(plan, names):
    """The plan's region names for NAMES (case does not matter; "Bitter Coast" also finds "Bitter Coast Region").
    An unknown name is refused with the list of the plan's regions."""
    known = region_names(plan)
    by_fold = {n.casefold(): n for n in known}
    out = []
    for name in names or ():
        key = name.strip().casefold()
        hit = by_fold.get(key) or by_fold.get(key + ' region')
        if hit is None:
            raise ValueError('Unknown region %r. Regions in the plan: %s' % (name, '; '.join(known)))
        out.append(hit)
    return out


def select(plan, rings_limit=None, cells=None, regions=None):
    rows = plan['cells']
    if regions:
        want_regions = set(match_regions(plan, regions))
        rows = [r for r in rows if r.get('region') in want_regions]
    if cells:
        want = set(cells)
        rows = [r for r in rows if (r['x'], r['y']) in want]
    if rings_limit is not None:
        rows = [r for r in rows if r['ring'] < rings_limit]
    return rows


# ------------------------------------------------------------------ one cell

def cell_settings(cell, missing_land='flat'):
    """Converter settings of a one-cell frame (the town settings shape of docs/TOWN_IMPORT.md)."""
    x, y = cell
    ident = 'c%s%d_%s%d' % ('m' if x < 0 else 'p', abs(x), 'm' if y < 0 else 'p', abs(y))
    return {
        'format': 1, 'source_cell': [x, y], 'source_radius': 0,
        'centre': [x * CELL_UNITS + CELL_UNITS // 2, y * CELL_UNITS + CELL_UNITS // 2], 'scale': SCALE,
        'bounds': [[-HALF, -HALF], [HALF, HALF]], 'core_size': 1024, 'overlap': 896, 'hysteresis': 96,
        'draw_distance': 540, 'terrain_step': 128, 'terrain_material_repairs': [], 'entity_budget': 1000,
        'model_budget': 220, 'collision_margin': 224, 'region_core_overrides': {},
        'missing_land': missing_land,
        'town': {'id': ident, 'title': 'Cell %d,%d' % (x, y), 'map': ident, 'map_prefix': 'zc', 'region_cap': 64,
                 'message': 'Cell %d,%d' % (x, y), 'region_file': ident + '-regions.txt',
                 'door_file': 'scene-doors-' + ident + '.txt', 'visual_group': ident,
                 'arrival': {'source_position': [x * CELL_UNITS + 4096.0, y * CELL_UNITS + 4096.0, 0.0],
                             'reason': 'CHIMport cell frame (no arrival)'}, 'return': None},
    }


def _shared_put(self, kind, fp, value):
    """UnitCache.put with a temporary name of its own per process: several cells write one shared cache, and two
    of them may store the same unit at once (the same temporary name made the second rename fail)."""
    import pickle
    if self.folder is None:
        return
    path = self._path(kind, fp)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.%d.tmp' % os.getpid())
    tmp.write_bytes(pickle.dumps((fp, value), protocol=4))
    tmp.replace(path)


@contextlib.contextmanager
def cell_area(settings):
    """Make the CHIM builder read these settings for the cell's area id (the builder takes areas by id), with
    unit cache writes that are safe while other cells share the cache."""
    import town_config
    from chim.units import UnitCache
    ident = settings['town']['id']
    original, put = town_config.load_settings, UnitCache.put

    def load(town_id, root=None):
        return settings if town_id == ident else original(town_id, root)
    town_config.load_settings = load
    UnitCache.put = _shared_put
    try:
        yield ident
    finally:
        town_config.load_settings = original
        UnitCache.put = put


def hull_figures(models):
    """Standing-hull (hull 1) clipnodes and chain depth per model image (tools/hull_chain_audit.py)."""
    import struct
    from hull_chain_audit import hull_depth
    from chim import format as F
    rows = []
    for m in models:
        lumps = F.read_brush_image(m['image'])
        clips, mods = lumps[9], lumps[14]
        if len(mods) < 64:
            continue
        head = struct.unpack_from('<i', mods, 36 + 4)[0]       # dmodel_t headnode[1]
        reach, depth = hull_depth(clips, head)
        rows.append({'name': m.get('name'), 'clipnodes': reach, 'depth': depth, 'over': hull_over_limit(depth, reach)})
    return rows


ELIGIBLE = ('passed', 'empty')        # cells usable as release candidates (complete apart from lighting)
KEPT_CHAIN_OUTCOME = 'kept_as_chain'   # hull audit outcome the CHIM Progress Tracker shows (counts as passed)
LEGACY_CHAIN_DEPTH = 256      # the audit's own threshold until the shared rule is in the builder line


def hull_over_limit(depth, reach):
    """The hull-chain check. With the shared rule in the builder (hull_chain_audit.over_limit: a chain deeper
    than routed_hull.CHAIN_DEPTH_LIMIT, routed hulls never reported) it is used as is; before that, the audit's
    own rule: a standing hull 256 clipnodes deep or more."""
    try:
        from hull_chain_audit import over_limit
    except ImportError:
        return depth >= LEGACY_CHAIN_DEPTH
    return bool(over_limit(depth, reach))


def kept_as_chain(receipt):
    """Meshes the builder's heap fallback kept as chains for memory (chim-receipt.json hull_fallback)."""
    fb = (receipt or {}).get('hull_fallback') or {}
    return sorted(fb.get('kept_chain') or []) if isinstance(fb, dict) else sorted(fb)


def _mesh_stem(name):
    stem = (name or '').split('@')[0].replace(chr(92), '/').lower()
    stem = stem.rsplit('/', 1)[-1]
    return stem[:-4] if stem.endswith('.nif') else stem


# A LIGH placement without a mesh: in Quake terms a light entity (baked by the light compiler, animated by a
# lightstyle); CHIM frames have no light entities or lightmaps yet, so it is deferred with this reason.
MESHLESS_LIGHT_REASON = 'light without a mesh: no CHIM light path yet (CHIM-MESHLESS-LIGHTS-33)'


def record_accounting(work, source, chim_refs):
    """Per record type: placed in the cell, converted (in the CHIM world), deferred (reason), failed."""
    placements = read_json(work / 'audit/placements.json') or []
    cat = read_json(work / 'source-catalogue.json') or {}
    deferred = {r['number']: r.get('status', 'deferred') for r in cat.get('deferred', [])}
    errors = read_json(work / 'scenery/conversion-errors.json') or []
    failed = {}
    for e in errors if isinstance(errors, list) else errors.get('errors', []):
        n = e.get('number') if isinstance(e, dict) else None
        if n is not None:
            failed[n] = str(e.get('error') or e.get('message') or e)[:200]
    by_type = collections.OrderedDict()
    for r in placements:
        tag = r.get('type') or '(missing object)'
        row = by_type.setdefault(tag, {'placed': 0, 'converted': 0, 'deferred': {}, 'failed': 0, 'skipped': {}})
        row['placed'] += 1
        n = r.get('number')
        if n in chim_refs:
            row['converted'] += 1
        elif n in deferred:
            why = deferred[n]
            if tag == 'LIGH' and why == 'nonvisual source marker':
                # a light without a mesh is a light, not a marker; CHIM has no light path for it yet
                why = MESHLESS_LIGHT_REASON
            row['deferred'][why] = row['deferred'].get(why, 0) + 1
        elif n in failed:
            row['failed'] += 1
        else:
            reason = 'not in the frame (outside the cell bounds or removed by a selection)'
            if not r.get('type'):
                reason = 'object id not in the base master'
            row['skipped'][reason] = row['skipped'].get(reason, 0) + 1
    tot = {'placed': sum(v['placed'] for v in by_type.values()),
           'converted': sum(v['converted'] for v in by_type.values()),
           'deferred': sum(sum(v['deferred'].values()) for v in by_type.values()),
           'failed': sum(v['failed'] for v in by_type.values()),
           'skipped': sum(sum(v['skipped'].values()) for v in by_type.values())}
    return {'by_type': by_type, 'totals': tot, 'conversion_errors': list(failed.values())[:20]}


def audits_of(validate_report, stairs, heap, hulls, measured, records, receipt):
    """Each mechanism: status passed|failed|not_measured, detail text, numbers."""
    a = {}
    fails = validate_report.get('failures', []) if validate_report else []

    def put(mech, status, detail, **numbers):
        a[mech] = {'status': status, 'detail': detail, 'numbers': numbers}

    if validate_report is None:
        put('format_validation', 'not_measured', 'world not built')
    else:
        put('format_validation', 'passed' if validate_report['ok'] else 'failed',
            '%d validator failures' % validate_report['failure_count'], failures=validate_report['failure_count'])
    groups = {'sky_bank_texels': r'sky bank|sky-bank|banked', 'seam_tears': r'seam',
              'far_terrain': r'terrain coverage|not covered|ground hole|coverage'}
    for mech, pat in groups.items():
        if validate_report is None:
            put(mech, 'not_measured', 'world not built')
            continue
        hits = [f for f in fails if re.search(pat, f, re.I)]
        label = {'sky_bank_texels': 'textures with texels on the sky bank (CHIM-TEXTURE-SPECKS-33)',
                 'seam_tears': 'terrain/hull seam failures (validator hull_seams)',
                 'far_terrain': 'terrain coverage failures (validator terrain_coverage; the far-terrain layer is '
                                'not in this builder yet)'}[mech]
        put(mech, 'failed' if hits else 'passed', '%d %s' % (len(hits), label), failures=len(hits))
    if stairs is None:
        put('stair_walk', 'not_measured', 'stair gate did not run')
    elif stairs.get('status') == 'skipped':
        put('stair_walk', 'not_measured', 'stair rule off')
    else:
        n = len(stairs.get('failures') or [])
        put('stair_walk', 'failed' if n else 'passed', '%d steps cannot be walked of %s tested (%d advisory)'
            % (n, stairs.get('tested', 0), len(stairs.get('advisory_failures', []))), failures=n,
            tested=stairs.get('tested', 0))
    if heap is None or heap.get('ok') is None:
        put('memory_fit', 'not_measured', (heap or {}).get('status') or 'heap gate did not run')
    else:
        fr = heap.get('frames') or []
        put('memory_fit', 'passed' if heap.get('ok', heap.get('status') == 'passed') else 'failed',
            'heap rings %s; least headroom %s B' % (heap.get('status'), min([f.get('headroom_bytes', 0) for f in fr] or [0])),
            least_headroom=min([f.get('headroom_bytes', 0) for f in fr] or [0]))
    if hulls is None:
        put('hull_bevels', 'not_measured', 'no models')
    else:
        kept = kept_as_chain(receipt)
        kept_stems = {_mesh_stem(k) for k in kept}
        over = [h for h in hulls if h.get('over', h['depth'] >= LEGACY_CHAIN_DEPTH)]
        # meshes the heap fallback kept as chains for memory: their own outcome, not a failure
        for_memory = [h for h in over if _mesh_stem(h['name']) in kept_stems]
        deep = [h for h in over if h not in for_memory]
        put('hull_bevels', 'failed' if deep else 'passed',
            '%d models over the hull-chain limit (max depth %d)%s' % (
                len(deep), max([h['depth'] for h in hulls] or [0]),
                '; %d kept as chain for memory' % len(for_memory) if for_memory else ''),
            over_limit=len(deep), max_depth=max([h['depth'] for h in hulls] or [0]),
            kept_as_chain_for_memory=sorted({_mesh_stem(h['name']) for h in for_memory} | kept_stems),
            routed=len((receipt or {}).get('routed_hulls') or []))
        if not deep and (for_memory or kept_stems):
            # the tracker's KEPT_CHAIN_OUTCOME: passed, with meshes the heap fallback kept as chains for memory
            a['hull_bevels']['outcome'] = KEPT_CHAIN_OUTCOME
    put('hidden_faces', 'not_measured', 'no CHIM hidden-face audit yet (CHIM-HIDDEN-FACES-33)')
    put('sprite_shape', 'not_measured', 'flora converted as meshes; no sprites in a CHIMport cell')
    actors = sum(v['placed'] for t, v in records['by_type'].items() if t in ('NPC_', 'CREA', 'LEVC'))
    put('actor_grounding', 'not_measured', '%d actors deferred to the actor pipeline' % actors, actors=actors)
    doors = records['by_type'].get('DOOR', {})
    if doors:
        ok = doors['converted'] == doors['placed']
        put('door_links', 'passed' if ok else 'failed', '%d of %d doors converted' % (doors['converted'], doors['placed']),
            converted=doors['converted'], placed=doors['placed'])
    else:
        put('door_links', 'not_measured', 'no doors in the cell')
    vis = (measured or {}).get('visibility') or {}
    if vis:
        put('vis', 'passed', 'visibility rows measured', **{k: v for k, v in vis.items() if isinstance(v, (int, float))})
    else:
        put('vis', 'not_measured', 'no visibility measurement')
    return a


def convert_cell(cell, data_files, palette, out, qbsp=None, unit_cache=None, jobs=1, missing_land='flat', abi_sizes=None):
    """Build, audit and measure one cell. Writes OUT/result.json; returns it. Never raises for a cell problem."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    t0, c0 = time.time(), os.times()
    result = {'format': CELL_FORMAT, 'cell': list(cell), 'key': ckey(cell), 'started': now_iso(), 'errors': [],
              'converted': False}
    settings = cell_settings(cell, missing_land)
    stages = {}

    def stage(name, fn):
        s = time.time()
        try:
            return fn()
        except Exception as exc:   # noqa: BLE001 - every cell problem is recorded, never fatal for the run
            msg = '%s: %s' % (type(exc).__name__, exc)
            result['errors'].append({'stage': name, 'mechanism': classify(msg), 'message': msg[:2000],
                                     'trace': traceback.format_exc()[-3000:]})
            return None
        finally:
            stages[name] = round(time.time() - s, 2)

    receipt = None
    with cell_area(settings) as ident:
        from chim.build import build_areas
        receipt = stage('build', lambda: build_areas([ident], data_files, out, palette, qbsp, jobs, dict(FRAME_SETTINGS), True, (),
                                                     True, unit_cache, None, None, None, []))
    work = out / 'work' / settings['town']['id']
    source = read_json(out / 'chim-source.json')
    chim_refs = {int(p['ref']) for s in (source or {}).get('frames', []) for p in s.get('placements', [])}
    records = record_accounting(work, source, chim_refs)
    result['records'] = records
    validate_report = stairs = heap = hulls = measured = None
    world = None
    if receipt is not None:
        result['converted'] = True
        pal = Path(palette).read_bytes()

        def run_validate():
            from chim.validate import validate
            fails, w = validate(out, source, pal)
            rep = {'ok': not fails, 'failures': fails[:200], 'failure_count': len(fails), 'source_checked': True}
            write_json(out / 'chim-validate.json', rep)
            return rep, w
        got = stage('validate', run_validate)
        if got:
            validate_report, world = got
            # A world without models (an empty sea cell: terrain and water only) has nothing to stream-measure;
            # chim.validate.measure needs at least one model (CHIM-MEASURE-EMPTY-FRAME-33).
            if validate_report['ok'] and world['models']:
                def run_measure():
                    from chim.validate import measure
                    m = measure(world, source, None, None, None, [])
                    m.get('walk', {}).pop('_replay', None)
                    write_json(out / 'chim-validate.json', dict(validate_report, measured=m))
                    return m
                measured = stage('measure', run_measure)

        def run_stairs():
            from chim.collision import require_stairs
            try:
                require_stairs(out, jobs)
            except ValueError:
                if not (out / 'chim-stairs.json').is_file():
                    raise
            return read_json(out / 'chim-stairs.json')
        stairs = stage('stairs', run_stairs)

        def run_heap():
            from chim.heap import require_heap
            try:
                require_heap(out, sizes=abi_sizes, jobs=jobs)
            except ValueError:
                if not (out / 'chim-heap.json').is_file():
                    raise
            return read_json(out / 'chim-heap.json')
        heap = stage('heap', run_heap)
        if world is not None:
            hulls = stage('hulls', lambda: hull_figures(world['models']))

            def run_stats():
                from chim.stats import chim_stats, dumps
                st = chim_stats(world, measured or {}, receipt, None, None, (), source=source)
                (out / 'chim-stats.json').write_bytes(dumps(st).encode('utf-8'))
                return st
            stage('stats', run_stats)
    result['audits'] = audits_of(validate_report, stairs, heap, hulls, measured, records, receipt)
    result['stats'] = cell_stats(out, receipt, world, records, hulls, heap, measured, work)
    c1 = os.times()
    result.update(finished=now_iso(), wall_s=round(time.time() - t0, 2),
                  cpu_s=round((c1.user - c0.user) + (c1.system - c0.system) + (c1.children_user - c0.children_user)
                              + (c1.children_system - c0.children_system), 2),
                  stages=stages, units=(receipt or {}).get('units'))
    result['status'] = cell_status(result)
    write_json(out / 'result.json', result)
    return result


# Audits whose failure threshold is a policy still being settled: a cell failing ONLY these is reported as
# "hull policy pending", apart from failures (the router and the audit are to read one shared threshold).
POLICY_PENDING = ('hull_bevels',)


def cell_status(res):
    """passed | empty | hull_pending | failed | not_converted. hull_pending = failing only POLICY_PENDING audits. empty = converted, nothing placed in the cell (terrain and water
    only), no error and no failed audit: counted apart so empty sea cells do not inflate "passed"."""
    if not res.get('converted'):
        return 'not_converted'
    failed = {m for m, a in (res.get('audits') or {}).items() if a['status'] == 'failed'}
    if res.get('errors') or failed - set(POLICY_PENDING):
        return 'failed'
    if failed:
        return 'hull_pending'
    if not (res.get('records') or {}).get('totals', {}).get('placed'):
        return 'empty'
    return 'passed'


def cell_stats(out, receipt, world, records, hulls, heap, measured, work):
    st = read_json(out / 'chim-stats.json') or {}
    units = (receipt or {}).get('units') or {}
    mesh = units.get('mesh', {})
    files = list((out / 'chim').rglob('*')) if (out / 'chim').is_dir() else []
    audit = (read_json(work / 'audit/audit.json') or {}).get('area', {})
    src_tris = None
    idx = read_json(work / 'scenery/scenery-index.json')
    if idx:
        tri_of = [m.get('triangles') or 0 for m in idx.get('models', [])]
        src_tris = sum(tri_of[r['model_index']] for r in idx.get('references', []) if r.get('model_index') is not None
                       and r['model_index'] < len(tri_of))
    faces = st.get('faces') or {}
    textures = (world or {}).get('textures') or []
    fr = (heap or {}).get('frames') or []
    out_stats = {
        'records': records['totals'],
        'meshes': {'unique_in_cell': mesh.get('built', 0) + mesh.get('reused', 0), 'new': mesh.get('built', 0),
                   'reused': mesh.get('reused', 0), 'source_direct_models': audit.get('direct_unique_models')},
        'faces': {'source_triangles': src_tris, 'stored': faces.get('stored'), 'placed': faces.get('placed'),
                  'terrain': faces.get('terrain'), 'models_stored': faces.get('models_stored')},
        'textures': {'count': len(textures), 'bytes': sum(len(t.get('miptex', b'')) for t in textures)},
        'disk': {'files': sum(1 for f in files if f.is_file()), 'chim_bytes': sum(f.stat().st_size for f in files if f.is_file()),
                 'chunks': len((world or {}).get('chunks') or []), 'legacy_region_bytes': None},
        'collision': {'models': len(hulls or []), 'clipnodes': sum(h['clipnodes'] for h in hulls or []),
                      'max_hull_depth': max([h['depth'] for h in hulls or []] or [0]),
                      'over_limit': sum(1 for h in hulls or [] if h.get('over')),
                      'routed': len((receipt or {}).get('routed_hulls') or []),
                      'kept_as_chain_for_memory': kept_as_chain(receipt)},
        'memory': {'heap_status': (heap or {}).get('status'), 'zone_bytes': max([f.get('zone_bytes', 0) for f in fr] or [0]) or None,
                   'budget_bytes': max([f.get('budget_bytes', 0) for f in fr] or [0]) or None,
                   'active_radius': (heap or {}).get('active_radius'), 'load_radius': (heap or {}).get('load_radius'),
                   'active_ring_peak': max([f.get('peak_bytes', 0) for f in fr] or [0]) if fr else None,
                   'load_ring_peak': max([(f.get('load_ring') or {}).get('peak_bytes', 0) for f in fr] or [0]) if fr else None,
                   'least_headroom_bytes': min([f.get('headroom_bytes', 0) for f in fr] or [0]) if fr else None,
                   'largest_block': max([f.get('largest_block_bytes', 0) for f in fr] or [0]) if fr else None},
        'vis': {k: v for k, v in ((measured or {}).get('visibility') or {}).items() if isinstance(v, (int, float))},
    }
    return out_stats


# ------------------------------------------------------------------ the growing world

@contextlib.contextmanager
def cells_area(settings_list):
    """cell_area for many cells at once (one world, a frame per cell)."""
    import town_config
    from chim.units import UnitCache
    by_id = {s['town']['id']: s for s in settings_list}
    original, put = town_config.load_settings, UnitCache.put

    def load(town_id, root=None):
        return by_id[town_id] if town_id in by_id else original(town_id, root)
    town_config.load_settings = load
    UnitCache.put = _shared_put
    try:
        yield list(by_id)
    finally:
        town_config.load_settings = original
        UnitCache.put = put


def converted_cells(run_dir, plan):
    """Plan rows (in order) whose cell world was built."""
    out = []
    for r in sorted(plan['cells'], key=lambda r: r['order']):
        res = read_json(run_dir / 'cells' / cell_dir((r['x'], r['y'])) / 'result.json')
        if res and res.get('converted'):
            out.append(r)
    return out


def build_world(run_dir, data_files, palette, name, rows, qbsp=None, jobs=1, abi_sizes=None, missing_land='flat',
                heap=True, pool=None, link=False):
    """One CHIM world holding every converted cell so far (a frame per cell, every unit from the run's shared
    cache: stored once), then the world audits on the whole of it: format validation, the streaming walk
    (measure), the heap rings and the stats. Each cell's source stage is reused from its cell folder (linked).
    Writes RUN/world/NAME/ (world.json: what it holds and what the audits found)."""
    out = run_dir / 'world' / name
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    settings = [cell_settings((r['x'], r['y']), missing_land) for r in rows]
    work = out / 'work'
    work.mkdir(exist_ok=True)
    for r, s in zip(rows, settings):
        link = work / s['town']['id']
        target = run_dir / 'cells' / cell_dir((r['x'], r['y'])) / 'work' / s['town']['id']
        if not link.exists() and target.is_dir():
            link.symlink_to(target, target_is_directory=True)
    report = {'format': 'aw-chimport-world-1', 'name': name, 'cells': [ckey((r['x'], r['y'])) for r in rows],
              'started': now_iso(), 'errors': []}

    def step(label, fn):
        s0 = time.time()
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - recorded in world.json
            msg = '%s: %s' % (type(exc).__name__, exc)
            report['errors'].append({'stage': label, 'mechanism': classify(msg), 'message': msg[:2000],
                                     'trace': traceback.format_exc()[-3000:]})
            return None
        finally:
            report.setdefault('stages', {})[label] = round(time.time() - s0, 1)
    units = run_dir / 'units'
    if pool is not None:
        from chim.units import PooledUnitCache
        units = PooledUnitCache(units, pool, link=link)
    with cells_area(settings) as ids:
        from chim.build import build_areas
        receipt = step('build', lambda: build_areas(ids, data_files, out, palette, qbsp, jobs, dict(FRAME_SETTINGS),
                                                    True, (), True, units, None, None, None, []))
    if pool is not None:
        report['pool'] = dict(units.pool_stats, dir=str(pool))
    if receipt is not None:
        source = read_json(out / 'chim-source.json')
        pal = Path(palette).read_bytes()
        from chim.validate import validate
        got = step('validate', lambda: validate(out, source, pal))
        if got:
            fails, world = got
            report['validation'] = {'ok': not fails, 'failure_count': len(fails), 'failures': fails[:100]}
            if not fails:
                def measure_all():
                    from chim.validate import measure
                    m = measure(world, source, None, None, None, [])
                    m.get('walk', {}).pop('_replay', None)
                    return m
                measured = step('measure', measure_all)
                if measured is not None:
                    write_json(out / 'chim-validate.json', dict(report['validation'], measured=measured))
                    report['walk'] = measured.get('walk')
                    report['visibility'] = measured.get('visibility')

                    def stats():
                        from chim.stats import chim_stats, dumps
                        st = chim_stats(world, measured, receipt, None, None, (), source=source)
                        (out / 'chim-stats.json').write_bytes(dumps(st).encode('utf-8'))
                        return {k: st.get(k) for k in ('counts', 'faces', 'disk') if k in st}
                    report['stats'] = step('stats', stats)

        heap_audit = heap

        def heap():
            from chim.heap import require_heap
            try:
                # per-frame audit with its own cache (the ring walk of each frame meets only its neighbours)
                require_heap(out, sizes=abi_sizes, jobs=jobs, cache_dir=run_dir / 'world' / 'heap-cache')
            except ValueError:
                if not (out / 'chim-heap.json').is_file():
                    raise
            h = read_json(out / 'chim-heap.json') or {}
            fr = h.get('frames') or []
            return {'status': h.get('status'), 'frames': len(fr),
                    'frames_over': sum(1 for f in fr if f.get('ok') is False),
                    'least_headroom_bytes': min([f.get('headroom_bytes', 0) for f in fr] or [0]) if fr else None,
                    'active_ring_peak': max([f.get('peak_bytes', 0) for f in fr] or [0]) if fr else None,
                    'load_ring_peak': max([(f.get('load_ring') or {}).get('peak_bytes', 0) for f in fr] or [0])
                    if fr else None}
        if heap_audit:
            report['heap'] = step('heap', heap)
        else:
            report['heap'] = {'status': 'not measured (world --no-heap)'}
        files = [f for f in (out / 'chim').rglob('*') if f.is_file()]
        report['disk'] = {'files': len(files), 'bytes': sum(f.stat().st_size for f in files),
                          'largest_file': max([f.stat().st_size for f in files] or [0]),
                          'directories': len({f.parent for f in files})}
        report['units'] = receipt.get('units')
        report['placements'] = receipt.get('placements')
        report['models'] = receipt.get('models')
    report.update(finished=now_iso(), wall_s=round(time.time() - t0, 1), built=receipt is not None)
    write_json(out / 'world.json', report)
    return report


# ------------------------------------------------------------------ the shared storage pool

# --storage-pool auto|on|off and --reuse-mode copy|hardlink|pool, as in tools/build.py (docs/BUILD_CACHE.md), over
# the same content-addressed store (tools/storage_pool.py, tools/file_cache.py keys). Default off: the run's own
# units/ cache only, as before (CHIMPORT-NO-SHARED-POOL-35).
POOL_SETTINGS = ('auto', 'on', 'off')
REUSE_MODES = ('copy', 'hardlink', 'pool')
CELL_NAMESPACE = 'chimport-cell'
CELL_KEY_FORMAT = 1
MANIFEST_FORMAT = 'aw-chimport-cell-manifest-1'
MANIFEST_NAME = 'pool-manifest.json'
# Written again by the runner after the cell (never shared), or the cell's source stage, which the growing world
# reuses and may write into (shared files are read-only): neither is pooled.
CELL_NOT_POOLED = ('result.json', 'cell.log', MANIFEST_NAME)
CELL_NOT_POOLED_DIRS = ('work',)
# Environment variables that name places, worker counts or bookkeeping, never what a cell's bytes are.
CELL_KEY_IGNORED_ENV = {'AMIWIND_INPUTS_LOCK', 'AMIWIND_STORAGE_POOL', 'AMIWIND_CACHE_FALLBACK', 'AMIWIND_BUILD_JOBS',
                        'AMIWIND_BUILD_JOBS_FILE', 'AMIWIND_PROFILE_SECTIONS', 'AMIWIND_BUILD_PROFILE',
                        'AMIWIND_PROFILE_INTERVAL', 'AMIWIND_STAGE_TRACE', 'AMIWIND_BUILD_BUDGET'}
_CODE = {}


def pool_choice(args):
    """(pool folder or None, origin). The folder comes from --storage-pool-dir > AMIWIND_STORAGE_POOL >
    --workspace W (W/cache/asset-pool-v1), as for the builder (tools/storage_pool.resolve_dir). auto = on when a
    folder is named; off (the default) = the run's own units/ cache only."""
    import storage_pool
    setting = getattr(args, 'storage_pool', None) or 'off'
    mode = getattr(args, 'reuse_mode', None) or 'copy'
    pool, origin = storage_pool.resolve_dir(getattr(args, 'workspace', None), getattr(args, 'storage_pool_dir', None))
    if setting == 'on' and pool is None:
        raise ValueError('--storage-pool on needs a pool folder: --storage-pool-dir DIR, AMIWIND_STORAGE_POOL or '
                         '--workspace W')
    enabled = setting == 'on' or (setting == 'auto' and pool is not None)
    if mode != 'copy' and not enabled:
        raise ValueError('--reuse-mode %s takes reused units from the storage pool: add --storage-pool on (or auto '
                         'with a pool folder)' % mode)
    return (pool if enabled else None), origin


def pool_arguments(args, pool):
    """The pool options a cell process gets from the runner (none when the pool is off: the command is unchanged)."""
    if pool is None:
        return []
    return ['--storage-pool', 'on', '--storage-pool-dir', str(pool),
            '--reuse-mode', getattr(args, 'reuse_mode', None) or 'copy']


def code_identity():
    """SHA-256 over every file of tools/, src/ and config/ plus VERSION and CHIM_VERSION: the whole converter.
    Deliberately broad (a cell key may never under-declare); the fine-grained reuse is the units'."""
    if 'sha' not in _CODE:
        import hashlib
        h = hashlib.sha256(b'chimport-code-1\0')
        files = []
        for top in ('tools', 'src', 'config'):
            files += [p for p in (ROOT / top).rglob('*')
                      if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
        files += [ROOT / name for name in ('VERSION', 'CHIM_VERSION') if (ROOT / name).is_file()]
        for path in sorted(files):
            h.update(path.relative_to(ROOT).as_posix().encode() + b'\0')
            h.update(hashlib.sha256(path.read_bytes()).digest())
        _CODE['sha'] = h.hexdigest()
    return _CODE['sha']


def inputs_identity(data_files):
    """The game inputs a cell reads, from the run's input lock (AMIWIND_INPUTS_LOCK): [(path in the data folder,
    SHA-256)] sorted, or None when there is no lock or an input is unhashed (then no cell key)."""
    from known_inputs import LOCK_ENV
    lock = os.environ.get(LOCK_ENV)
    record = read_json(lock) if lock else None
    files = (record or {}).get('files') or {}
    if not files:
        return None
    try:
        from mwad.paths import resolve_data_files
        base = str(resolve_data_files(data_files))
    except Exception:  # noqa: BLE001 - no data folder here: absolute names (a miss, never a wrong hit)
        base = None
    rows = []
    for name, entry in files.items():
        if not entry.get('sha256'):
            return None
        rel = os.path.relpath(name, base).replace(os.sep, '/') if base and name.startswith(base) else name
        rows.append([rel, entry['sha256']])
    return sorted(rows)


def cell_key(cell, data_files, palette, qbsp=None, abi_sizes=None, missing_land='flat'):
    """(key, reason): the hash of exactly what a cell's outputs depend on - the cell and its frame settings, the
    game inputs (input lock), the palette, the qbsp binary, the engine ABI sizes, the converter's code, the
    AMIWIND_* switches and the Python/numpy versions. (None, reason) when an input cannot be hashed."""
    import hashlib
    import shutil
    from file_cache import digest_json, sha256_file
    inputs = inputs_identity(data_files)
    if inputs is None:
        return None, 'no input lock: the game inputs of this cell are not hashed'
    q = None
    if qbsp:
        found = shutil.which(str(qbsp)) or str(qbsp)
        try:
            q = sha256_file(found)
        except OSError:
            return None, 'qbsp cannot be read'
    try:
        import numpy
        numpy_version = numpy.__version__
    except ImportError:
        numpy_version = None
    parts = {'format': CELL_KEY_FORMAT, 'cell': list(cell), 'settings': cell_settings(cell, missing_land),
             'frame': FRAME_SETTINGS, 'palette': hashlib.sha256(Path(palette).read_bytes()).hexdigest(), 'qbsp': q,
             'abi_sizes': abi_sizes, 'inputs': inputs, 'code': code_identity(),
             'env': {k: v for k, v in sorted(os.environ.items())
                     if k.startswith('AMIWIND_') and k not in CELL_KEY_IGNORED_ENV},
             'hashseed': os.environ.get('PYTHONHASHSEED'), 'python': sys.version, 'numpy': numpy_version}
    return digest_json(parts), None


def release_pooled(folder):
    """Remove the read-only shared links (pooled files) of a cell folder before the cell is built again, so writers
    that replace or rewrite files never meet a read-only shared inode. The bytes stay in the pool: only links go."""
    removed = 0
    for here, dirs, names in os.walk(folder):
        for name in names:
            path = Path(here) / name
            try:
                info = os.lstat(path)
            except OSError:
                continue
            if not path.is_symlink() and info.st_nlink > 1 and not info.st_mode & 0o222:
                path.unlink()
                removed += 1
    return removed


class CellPool:
    """A cell's outputs in the shared pool: every file stored once (hard links), and a manifest keyed by the cell
    key, so the same cell with the same inputs and code is linked, never converted again, in any run."""

    def __init__(self, pool, link=True):
        import storage_pool
        from file_cache import FileCache
        self.pool = Path(pool)
        self.link = link
        self.storage_pool = storage_pool
        self.index = FileCache(self.pool, CELL_NAMESPACE, None, fallback=False)
        self.stats = {'stored_files': 0, 'stored_bytes': 0, 'linked_files': 0, 'linked_bytes': 0,
                      'reused_files': 0, 'reused_bytes': 0, 'errors': []}

    def fetch(self, key, out):
        """Place the pooled outputs of KEY into OUT; the manifest, or None (not pooled, or an object is missing)."""
        import hashlib
        meta = self.index.lookup(key)
        if meta is None:
            return None
        try:
            raw = self.storage_pool.object_path(self.pool, meta['sha256']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != meta['sha256']:
                return None
            manifest = json.loads(raw.decode('utf-8'))
        except (OSError, ValueError):
            return None
        if manifest.get('format') != MANIFEST_FORMAT or manifest.get('key') != key:
            return None
        placed = files = 0
        for rel, info in sorted(manifest['files'].items()):
            try:
                if not self.storage_pool.place(self.pool, info['sha256'], Path(out) / rel, link=self.link):
                    self.stats['errors'].append('%s: not in the pool' % rel)
                    return None
            except OSError as exc:
                self.stats['errors'].append('%s: %s' % (rel, exc))
                return None
            placed += info['bytes']
            files += 1
        self.stats['reused_files'] += files
        self.stats['reused_bytes'] += placed
        return manifest

    def store(self, out, key, result):
        """Pool OUT's outputs (by hard link: no second copy) and, with KEY and an error-free result, the manifest.
        Returns the manifest's SHA-256, or None when no manifest was stored."""
        out = Path(out)
        files, links_inside = {}, False
        for here, dirs, names in os.walk(out):
            rel_here = Path(here).relative_to(out)
            if rel_here == Path('.'):
                dirs[:] = [d for d in dirs if d not in CELL_NOT_POOLED_DIRS]
            dirs.sort()
            for name in sorted(names):
                rel = (rel_here / name).as_posix()
                path = Path(here) / name
                if rel in CELL_NOT_POOLED or name.endswith(('.tmp', self.storage_pool.TEMPORARY)) \
                        or '.pool-link-probe.' in name:
                    continue
                if path.is_symlink():
                    links_inside = True
                    continue
                files[rel] = path
        record = {}
        for rel, path in files.items():
            try:
                digest = self.storage_pool.sha256_file(path)
                size = path.stat().st_size
                existed = self.storage_pool.object_path(self.pool, digest).is_file()
                if self.storage_pool.put(self.pool, path, digest)[0] == 'skipped':
                    raise OSError('cannot be hard-linked with the pool')
            except OSError as exc:
                self.stats['errors'].append('%s: %s' % (rel, exc))
                continue
            record[rel] = {'sha256': digest, 'bytes': size}
            if existed:
                self.stats['linked_files'] += 1
                self.stats['linked_bytes'] += size
            else:
                self.stats['stored_files'] += 1
                self.stats['stored_bytes'] += size
        if key is None or result.get('errors') or links_inside or len(record) != len(files):
            return None
        manifest = {'format': MANIFEST_FORMAT, 'key': key, 'cell': result.get('cell'), 'files': record,
                    'result': {k: v for k, v in result.items() if k != 'pool'}}
        path = out / MANIFEST_NAME
        write_json(path, manifest)
        try:
            digest = self.storage_pool.sha256_file(path)
            if self.storage_pool.put(self.pool, path, digest)[0] == 'skipped':
                raise OSError('cannot be hard-linked with the pool')
            self.index.point(key, digest, path.stat().st_size,
                             {'cell': result.get('cell'), 'objects': sorted({r['sha256'] for r in record.values()})})
        except OSError as exc:
            self.stats['errors'].append('%s: %s' % (MANIFEST_NAME, exc))
            return None
        return digest


POOL_TOTAL_FIELDS = ('units_reused', 'units_computed', 'units_failed', 'units_from_pool', 'stored_bytes', 'linked_bytes',
                     'reused_bytes', 'stored_files', 'linked_files')


def pool_totals(results):
    """Stored vs linked bytes, cells and units reused / computed / failed over cell results' "pool" records."""
    t = dict({'cells': 0, 'cells_reused': 0, 'cells_computed': 0, 'cells_failed': 0}, **{k: 0 for k in POOL_TOTAL_FIELDS})
    for res in results:
        p = (res or {}).get('pool')
        if not p:
            continue
        t['cells'] += 1
        if p.get('cell') == 'reused':
            t['cells_reused'] += 1
        elif res.get('errors') or not res.get('converted'):
            t['cells_failed'] += 1
        else:
            t['cells_computed'] += 1
        for k in POOL_TOTAL_FIELDS:
            t[k] += int(p.get(k) or 0)
    return t


def pool_line(t):
    return ('chimport: storage pool: stored %.1f MB, linked %.1f MB, reused from the pool %.1f MB; cells reused %d / '
            'computed %d / failed %d; units reused %d (%d from the pool) / computed %d / failed %d'
            % (t['stored_bytes'] / 1e6, t['linked_bytes'] / 1e6, t['reused_bytes'] / 1e6, t['cells_reused'],
               t['cells_computed'], t['cells_failed'], t['units_reused'], t['units_from_pool'], t['units_computed'],
               t['units_failed']))


def unit_counts(stats):
    """(reused, built, write refusals) over a unit cache's per-kind stats."""
    rows = [v for v in (stats or {}).values() if isinstance(v, dict)]
    return (sum(int(v.get('reused', 0)) for v in rows), sum(int(v.get('built', 0)) for v in rows),
            sum(int(v.get('write_refused', 0)) for v in rows))


def convert_cell_pooled(cell, data_files, palette, out, qbsp=None, unit_cache=None, jobs=1, missing_land='flat',
                        abi_sizes=None, pool=None, origin=None, reuse_mode='copy'):
    """convert_cell through the shared storage pool. POOL None: exactly convert_cell (after removing read-only shared
    links a pooled earlier attempt left in OUT). Otherwise records result['pool']: stored vs linked bytes, units
    reused / computed / failed, and whether the whole cell was linked from an earlier identical conversion."""
    out = Path(out)
    if pool is None:
        release_pooled(out)              # nothing to do in a folder a pooled run never wrote
        return convert_cell(cell, data_files, palette, out, qbsp, unit_cache, jobs, missing_land, abi_sizes)
    import storage_pool
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    setting = storage_pool.setting(pool, origin or 'option', out, log=lambda line: print(line, flush=True))
    link = setting['links'] and reuse_mode in ('hardlink', 'pool')
    cells = CellPool(pool, link=link)
    key, why = cell_key(cell, data_files, palette, qbsp, abi_sizes, missing_land)
    record = {'dir': str(pool), 'origin': setting['origin'], 'links': setting['links'], 'warning': setting['warning'],
              'reuse_mode': reuse_mode if setting['links'] else 'copy', 'cell_key': key, 'cell_key_missing': why}
    if key is not None:
        manifest = cells.fetch(key, out)
        if manifest is not None:
            res = dict(manifest['result'])
            res.update(started=now_iso(), finished=now_iso(), wall_s=round(time.time() - t0, 2), cpu_s=0.0,
                       original_wall_s=manifest['result'].get('wall_s'), original_cpu_s=manifest['result'].get('cpu_s'))
            record.update(cell='reused', reused_bytes=cells.stats['reused_bytes'],
                          reused_files=cells.stats['reused_files'])
            res['pool'] = record
            write_json(out / 'result.json', res)
            return res
    release_pooled(out)
    from chim.units import PooledUnitCache
    units = PooledUnitCache(unit_cache or (out / 'work' / 'chim-units'), pool, link=link)
    res = convert_cell(cell, data_files, palette, out, qbsp, units, jobs, missing_land, abi_sizes)
    manifest = cells.store(out, key, res) if setting['links'] else None
    reused, built, refused = unit_counts(units.stats)
    us = units.pool_stats
    record.update(cell='computed', manifest=manifest,
                  stored_bytes=cells.stats['stored_bytes'] + us['stored_bytes'],
                  linked_bytes=cells.stats['linked_bytes'] + us['linked_bytes'],
                  reused_bytes=us['reused_bytes'], stored_files=cells.stats['stored_files'] + us['stored_units'],
                  linked_files=cells.stats['linked_files'] + us['linked_units'],
                  units_reused=reused, units_computed=built, units_failed=refused + us['errors'],
                  units_from_pool=us['reused_units'], errors=cells.stats['errors'][:20])
    res['pool'] = record
    write_json(out / 'result.json', res)
    return res


# ------------------------------------------------------------------ one writer per run folder

class RunLocked(RuntimeError):
    pass


class RunLock:
    """An exclusive lock on RUN/run.lock for the whole `run` (one writer of state.json): a second `run` on the same
    folder refuses with the holder's pid and start time. The operating system drops the lock when the holder
    exits, however it exits (no stale lock to clean up)."""

    def __init__(self, run_dir):
        self.path = Path(run_dir) / 'run.lock'
        self.handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(self.path, 'a+', encoding='utf-8', newline='\n')
        try:
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            try:
                holder = Path(self.path).read_text(encoding='utf-8').strip() or 'another process'
            except OSError:
                holder = 'another process'
            handle.close()
            raise RunLocked('chimport: another run is already writing %s (lock %s held by %s). One run per RUN '
                            'folder: use --workers for more cells at once, or give each worker its own RUN folder '
                            'sharing one storage pool (--storage-pool-dir).'
                            % (self.path.parent / 'state.json', self.path, holder))
        if os.name != 'nt':
            handle.seek(0)
            handle.truncate()
            handle.write('pid %d since %s\n' % (os.getpid(), now_iso()))
            handle.flush()
        self.handle = handle
        return self

    def __exit__(self, *exc):
        if self.handle is not None:
            if os.name == 'nt':
                try:
                    import msvcrt
                    self.handle.seek(0)
                    msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            self.handle.close()
            self.handle = None
        return False


# ------------------------------------------------------------------ the run

def load_state(run):
    st = read_json(run / 'state.json')
    return st or {'format': STATE_FORMAT, 'cells': {}, 'created': now_iso()}


def pending_rows(rows, state, retry_failed=False):
    out = []
    for r in rows:
        s = state['cells'].get(ckey((r['x'], r['y'])), {}).get('status')
        if s == 'done' or (s == 'failed' and not retry_failed):
            continue
        out.append(r)
    return out


def summarise(run, plan=None):
    """Totals per ring and failure classes by mechanism from the finished cells' results."""
    plan = plan or read_json(run / 'plan.json') or {'cells': []}
    ring_of = {ckey((r['x'], r['y'])): r['ring'] for r in plan['cells']}
    rings_tot = collections.OrderedDict()
    classes = collections.Counter()
    audit_fail = collections.Counter()
    seen_new = []
    distinct = set()
    for r in sorted(plan['cells'], key=lambda r: r['order']):
        res = read_json(run / 'cells' / cell_dir((r['x'], r['y'])) / 'result.json')
        if not res:
            continue
        k = r['ring']
        t = rings_tot.setdefault(k, {'ring': k, 'cells': 0, 'converted': 0, 'passed': 0, 'empty': 0, 'hull_pending': 0, 'failed': 0, 'not_converted': 0,
                                     'new_meshes': 0, 'reused_meshes': 0, 'wall_s': 0.0, 'cpu_s': 0.0,
                                     'chim_bytes': 0, 'records_placed': 0, 'records_converted': 0,
                                     'distinct_meshes_new': 0, 'distinct_meshes_total': 0})
        t['cells'] += 1
        t['converted'] += 1 if res['converted'] else 0
        status = cell_status(res)
        t[status if status in ('passed', 'empty', 'hull_pending') else 'failed'] += 1
        t['not_converted'] += status == 'not_converted'
        m = res['stats']['meshes']
        # the census' distinct source meshes, against the mesh units the builder converted (new_meshes)
        cell_meshes = set(r.get('meshes') or ())
        t['distinct_meshes_new'] += len(cell_meshes - distinct)
        distinct |= cell_meshes
        t['distinct_meshes_total'] = len(distinct)
        t['new_meshes'] += m['new']
        t['reused_meshes'] += m['reused']
        t['wall_s'] = round(t['wall_s'] + res['wall_s'], 1)
        t['cpu_s'] = round(t['cpu_s'] + res['cpu_s'], 1)
        t['chim_bytes'] += res['stats']['disk']['chim_bytes']
        t['records_placed'] += res['records']['totals']['placed']
        t['records_converted'] += res['records']['totals']['converted']
        for e in res['errors']:
            classes['%s (%s)' % (e['mechanism'], e['stage'])] += 1
        for mech, a in res['audits'].items():
            if a['status'] == 'failed':
                audit_fail[mech] += 1
        seen_new.append([r['order'], m['new']])
    total = {'cells': sum(t['cells'] for t in rings_tot.values()), 'planned': len(plan['cells'])}
    for f in ('converted', 'passed', 'empty', 'hull_pending', 'failed', 'not_converted', 'new_meshes', 'reused_meshes', 'chim_bytes', 'records_placed',
              'records_converted'):
        total[f] = sum(t[f] for t in rings_tot.values())
    total['wall_s'] = round(sum(t['wall_s'] for t in rings_tot.values()), 1)
    # summary-level "done": passed cells with content plus empty sea cells (each still on its own line)
    total['done'] = total['passed'] + total['empty']
    for t in rings_tot.values():
        t['done'] = t['passed'] + t['empty']
    total['cpu_s'] = round(sum(t['cpu_s'] for t in rings_tot.values()), 1)
    return {'total': total, 'rings': list(rings_tot.values()), 'error_classes': dict(classes.most_common()),
            'audit_failures': dict(audit_fail.most_common())}


def cell_command(args, row):
    cmd = [sys.executable, str(Path(__file__).resolve()), 'cell', '--data-files', str(args.data_files),
           '--palette', str(args.palette), '--cell=%d,%d' % (row['x'], row['y']),   # '=': '-6,25' is not an option
           '--out', str(args.out / 'cells' / cell_dir((row['x'], row['y']))),
           '--unit-cache', str(args.out / 'units'), '--jobs', str(args.jobs)]
    cmd += pool_arguments(args, getattr(args, 'pool_dir', None))
    if args.qbsp:
        cmd += ['--qbsp', str(args.qbsp)]
    if (args.out / 'abi-sizes.json').is_file():
        cmd += ['--abi-sizes', str(args.out / 'abi-sizes.json')]
    return cmd


def world_command(args, ring):
    return ([sys.executable, str(Path(__file__).resolve()), 'world', '--data-files', str(args.data_files),
             '--palette', str(args.palette), '--out', str(args.out), '--through-ring', str(ring), '--jobs', str(args.jobs)]
            + (['--qbsp', str(args.qbsp)] if args.qbsp else []) + pool_arguments(args, getattr(args, 'pool_dir', None)))


def probe_abi_sizes(run_dir, sdk):
    """The engine target's ABI sizes, probed once per run with the SDK's compiler (the heap gate's input)."""
    from check_world_map_heap import compile_target_sizes
    sizes = compile_target_sizes(sdk)[0]
    write_json(run_dir / 'abi-sizes.json', sizes)
    return sizes


def inputs_lock(run_dir, data_files):
    """Hash the game inputs once per run (tools/known_inputs.InputLock) so every cell's source stage reads the
    hashes from the lock instead of hashing the masters and archives again (AMIWIND_INPUTS_LOCK)."""
    from known_inputs import LOCK_ENV, InputLock
    from mwad.paths import resolve_data_files
    data = resolve_data_files(data_files)
    files = [p for p in data.iterdir() if p.is_file()]
    files += [p for p in data.rglob('*') if p.is_file() and p.relative_to(data).parts[0].casefold() in ('meshes', 'textures')]
    lock = InputLock(run_dir / 'inputs.lock', mode='auto')
    lock.prepare(files)
    lock.save()
    os.environ[LOCK_ENV] = str(run_dir / 'inputs.lock')
    return lock


def run(args):
    run_dir = args.out
    run_dir.mkdir(parents=True, exist_ok=True)
    args.pool_dir, pool_origin = pool_choice(args)
    if args.dry_run:
        return _run(args, None)
    try:
        lock = RunLock(run_dir).__enter__()
    except RunLocked as exc:
        print(exc, file=sys.stderr, flush=True)
        return 3
    try:
        return _run(args, pool_origin)
    finally:
        lock.__exit__(None, None, None)


def _run(args, pool_origin):
    run_dir = args.out
    plan = read_json(run_dir / 'plan.json')
    if plan is None:
        plan = make_plan(args.data_files)
        write_json(run_dir / 'plan.json', plan)
    rows = select(plan, args.rings, parse_cells(args.cells), getattr(args, 'region', None))
    if args.sdk and not (run_dir / 'abi-sizes.json').is_file() and not args.dry_run:
        probe_abi_sizes(run_dir, args.sdk)
    if not args.dry_run:
        inputs_lock(run_dir, args.data_files)
    state = load_state(run_dir)
    if args.pool_dir is not None and not args.dry_run:
        import storage_pool
        state['pool'] = storage_pool.setting(args.pool_dir, pool_origin, run_dir,
                                             log=lambda line: print(line, flush=True))
        state['pool'].update(reuse_mode=getattr(args, 'reuse_mode', None) or 'copy', checked=now_iso())
    todo = pending_rows(rows, state, args.retry_failed)
    print('chimport: %d cells selected, %d to do, %d workers x %d jobs%s' % (
        len(rows), len(todo), args.workers, args.jobs,
        '' if args.pool_dir is None else ', storage pool %s (reuse %s)' % (args.pool_dir, args.reuse_mode)), flush=True)
    if args.dry_run:
        for r in todo:
            print('  ring %d  cell %d,%d  %s  %d records' % (r['ring'], r['x'], r['y'], r['name'] or r['region'], r['refs']))
        return 0
    running = {}
    queue = list(todo)
    ring_left = collections.Counter(r['ring'] for r in queue)
    worlds_due = []
    feeder = {'proc': None, 'last': time.time()}

    def maybe_feed(force=False):
        if not args.tracker or not args.tracker_tool:
            return
        fp = feeder['proc']
        if fp is not None and fp.poll() is None:
            return
        if not force and time.time() - feeder['last'] < args.feed_every:
            return
        feeder['last'] = time.time()
        cmd = [sys.executable, str(Path(__file__).resolve()), 'feed-tracker', '--out', str(run_dir),
               '--tracker', str(args.tracker), '--tracker-tool', str(args.tracker_tool),
               '--tracker-ingest=' + args.tracker_ingest]
        feeder['proc'] = subprocess.Popen(cmd, stdout=(run_dir / 'feed.log').open('ab'), stderr=subprocess.STDOUT)
    log = (run_dir / 'progress.jsonl').open('a', encoding='utf-8', newline='\n')
    finished = []
    try:
        while queue or running or worlds_due:
            stop = (run_dir / 'STOP').exists()
            # The growing world builds alone: no cell runs beside it (its memory grows with the island), and
            # cells start again only when it has finished.
            world_busy = any(k.startswith('world:') for k in running)
            while worlds_due and not running:
                k = worlds_due.pop(0)
                cmd = world_command(args, k)
                (run_dir / 'world').mkdir(exist_ok=True)
                wlog = (run_dir / 'world' / ('ring-%d.log' % k)).open('wb')
                running['world:%d' % k] = (subprocess.Popen(cmd, stdout=wlog, stderr=subprocess.STDOUT), {'ring': k},
                                           time.time(), wlog)
                print('chimport: building the world through ring %d' % k, flush=True)
            maybe_feed()
            world_busy = world_busy or any(k.startswith('world:') for k in running)
            while queue and not stop and not worlds_due and not world_busy and len(running) < args.workers:
                r = queue.pop(0)
                key = ckey((r['x'], r['y']))
                cdir = run_dir / 'cells' / cell_dir((r['x'], r['y']))
                cdir.mkdir(parents=True, exist_ok=True)
                old = cdir / 'result.json'
                if old.exists():
                    old.unlink()
                logf = (cdir / 'cell.log').open('wb')
                p = subprocess.Popen(cell_command(args, r), stdout=logf, stderr=subprocess.STDOUT)
                running[key] = (p, r, time.time(), logf)
                st = state['cells'].setdefault(key, {'attempts': 0})
                st.update(status='running', attempts=st['attempts'] + 1, started=now_iso())
                write_json(run_dir / 'state.json', state)
            if stop and not running:
                print('chimport: STOP file found; stopped with %d cells left' % len(queue), flush=True)
                break
            time.sleep(1.0)
            for key in list(running):
                p, r, t0, logf = running[key]
                limit = args.world_timeout if key.startswith('world:') else args.timeout
                timed_out = limit and time.time() - t0 > limit
                if p.poll() is None and not timed_out:
                    continue
                if timed_out and p.poll() is None:
                    p.kill()
                    p.wait()
                logf.close()
                del running[key]
                if key.startswith('world:'):
                    wrep = read_json(run_dir / 'world' / ('ring-%d' % r['ring']) / 'world.json') or {}
                    print('chimport: world through ring %d: %s, %d cells, %d errors (%.0f s)'
                          % (r['ring'], 'built' if wrep.get('built') else 'NOT built', len(wrep.get('cells', [])),
                             len(wrep.get('errors', [])), time.time() - t0), flush=True)
                    continue
                ring_left[r['ring']] -= 1
                if ring_left[r['ring']] == 0:
                    last_ring = not any(ring_left[k] for k in ring_left if k > r['ring'])
                    if not args.no_world and (r['ring'] % max(1, args.world_every) == 0 or last_ring):
                        worlds_due.append(r['ring'])
                    maybe_feed(force=True)
                cdir = run_dir / 'cells' / cell_dir((r['x'], r['y']))
                res = read_json(cdir / 'result.json')
                if res is None:
                    tail = (cdir / 'cell.log').read_bytes()[-3000:].decode('utf-8', 'replace')
                    msg = ('cell timed out after %d s' % args.timeout) if timed_out else \
                        'cell process exited %s without a result: %s' % (p.returncode, tail[-600:])
                    res = {'format': CELL_FORMAT, 'cell': [r['x'], r['y']], 'key': key, 'converted': False,
                           'errors': [{'stage': 'process', 'mechanism': classify(msg), 'message': msg}],
                           'records': {'by_type': {}, 'totals': {'placed': 0, 'converted': 0, 'deferred': 0,
                                                                 'failed': 0, 'skipped': 0}},
                           'audits': {m: {'status': 'not_measured', 'detail': 'cell did not finish', 'numbers': {}}
                                      for m in MECHANISMS},
                           'stats': {'meshes': {'new': 0, 'reused': 0, 'unique_in_cell': 0}, 'disk': {'chim_bytes': 0}},
                           'wall_s': round(time.time() - t0, 2), 'cpu_s': 0.0, 'finished': now_iso()}
                    write_json(cdir / 'result.json', res)
                res.update(ring=r['ring'], order=r['order'], name=r['name'], region=r['region'], land=r['land'])
                write_json(cdir / 'result.json', res)
                res['status'] = cell_status(res)
                finished.append(res)
                ok = res['converted'] and not res['errors']
                state['cells'][key].update(status='done' if ok else 'failed', result=res['status'], finished=now_iso(),
                                           wall_s=res['wall_s'],
                                           audits_failed=sorted(m for m, a in res['audits'].items()
                                                                if a['status'] == 'failed'),
                                           errors=sorted({e['mechanism'] for e in res['errors']}))
                write_json(run_dir / 'state.json', state)
                line = {'run': str(run_dir), 'stage': 'chimport-cell', 'cell': key, 'ring': r['ring'],
                        'order': r['order'], 'wall_s': res['wall_s'], 'cpu_s': res.get('cpu_s'),
                        'converted': res['converted'], 'errors': [e['mechanism'] for e in res['errors']],
                        'audits_failed': state['cells'][key]['audits_failed'],
                        'new_meshes': res['stats']['meshes']['new'], 'reused_meshes': res['stats']['meshes']['reused'],
                        'chim_bytes': res['stats']['disk']['chim_bytes'], 'finished': res.get('finished'),
                        'workers': args.workers, 'jobs': args.jobs}
                if res.get('pool'):
                    line['pool'] = {k: res['pool'].get(k) for k in ('cell',) + POOL_TOTAL_FIELDS}
                log.write(json.dumps(line, sort_keys=True) + '\n')
                log.flush()
                print('chimport: %s ring %d %s (%.0f s)%s' % (key, r['ring'], 'converted' if res['converted'] else 'FAILED',
                      res['wall_s'], '' if ok else ' ' + ', '.join(state['cells'][key]['errors'] + state['cells'][key]['audits_failed'])),
                      flush=True)
                write_json(run_dir / 'summary.json', summarise(run_dir, plan))
    finally:
        log.close()
        for key, (p, r, t0, logf) in running.items():
            p.kill()
            if key in state['cells']:
                state['cells'][key]['status'] = 'pending'
        if args.pool_dir is not None:
            # This run's stored vs linked bytes and units reused / computed / failed (the run's receipt).
            totals = pool_totals(finished)
            state.setdefault('pool', {})['last_run'] = dict(totals, finished=now_iso())
            print(pool_line(totals), flush=True)
        write_json(run_dir / 'state.json', state)
    summary = summarise(run_dir, plan)
    if args.pool_dir is not None:
        summary['pool'] = state.get('pool')
    write_json(run_dir / 'summary.json', summary)
    for _ in range(2):              # the last cells' feed: wait for a running feed, then feed what is left
        if feeder['proc'] is not None:
            feeder['proc'].wait()
        maybe_feed(force=True)
    if feeder['proc'] is not None:
        feeder['proc'].wait()
    return 0


# ------------------------------------------------------------------ export

EXPORT_FIELDS = ['order', 'ring', 'x', 'y', 'name', 'region', 'land', 'converted', 'passed', 'status', 'eligible', 'errors', 'audits_failed',
                 'records_placed', 'records_converted', 'records_deferred', 'records_failed', 'records_skipped',
                 'statics', 'flora', 'lights', 'doors', 'containers', 'activators', 'actors', 'creatures', 'items',
                 'meshes_unique', 'meshes_new', 'meshes_reused', 'faces_source', 'faces_stored', 'faces_placed',
                 'textures', 'texture_bytes', 'chunks', 'chim_bytes', 'clipnodes', 'max_hull_depth',
                 'heap_least_headroom', 'wall_s', 'cpu_s']


def export_rows(run):
    plan = read_json(run / 'plan.json') or {'cells': []}
    rows = []
    for r in plan['cells']:
        res = read_json(run / 'cells' / cell_dir((r['x'], r['y'])) / 'result.json')
        if not res:
            continue
        s, tot = res.get('stats', {}), res['records']['totals']
        cats = r.get('categories', {})
        rows.append({
            'order': r['order'], 'ring': r['ring'], 'x': r['x'], 'y': r['y'], 'name': r['name'], 'region': r['region'],
            'land': r['land'], 'converted': res['converted'],
            'passed': cell_status(res) == 'passed', 'status': cell_status(res), 'eligible': cell_status(res) in ELIGIBLE,
            'errors': ' | '.join('%s: %s' % (e['mechanism'], e['message'][:120]) for e in res['errors']),
            'audits_failed': ' '.join(m for m, a in res['audits'].items() if a['status'] == 'failed'),
            'records_placed': tot['placed'], 'records_converted': tot['converted'], 'records_deferred': tot['deferred'],
            'records_failed': tot['failed'], 'records_skipped': tot['skipped'],
            **{k: cats.get(k, 0) for k in ('statics', 'flora', 'lights', 'doors', 'containers', 'activators', 'actors',
                                           'creatures', 'items')},
            'meshes_unique': s.get('meshes', {}).get('unique_in_cell'), 'meshes_new': s.get('meshes', {}).get('new'),
            'meshes_reused': s.get('meshes', {}).get('reused'),
            'faces_source': s.get('faces', {}).get('source_triangles'), 'faces_stored': s.get('faces', {}).get('stored'),
            'faces_placed': s.get('faces', {}).get('placed'), 'textures': s.get('textures', {}).get('count'),
            'texture_bytes': s.get('textures', {}).get('bytes'), 'chunks': s.get('disk', {}).get('chunks'),
            'chim_bytes': s.get('disk', {}).get('chim_bytes'), 'clipnodes': s.get('collision', {}).get('clipnodes'),
            'max_hull_depth': s.get('collision', {}).get('max_hull_depth'),
            'heap_least_headroom': s.get('memory', {}).get('least_headroom_bytes'),
            'wall_s': res.get('wall_s'), 'cpu_s': res.get('cpu_s')})
    rows.sort(key=lambda r: r['order'])
    return rows


def write_csv(path, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=EXPORT_FIELDS, lineterminator='\n')
    w.writeheader()
    for r in rows:
        w.writerow(r)
    Path(path).write_bytes(buf.getvalue().encode('utf-8'))


# ------------------------------------------------------------------ CHIM Progress Tracker feed

TRACKER_RESULT = 'aw-cell-result-1'
TRACKER_MECHANISMS = ('format_validation', 'stair_walk', 'memory_fit', 'seam_tears', 'hull_bevels', 'sky_bank_texels',
                      'hidden_faces', 'far_terrain', 'sprite_shape', 'actor_grounding', 'door_links')


def tracker_cell(res, plan_row):
    """One cell of an aw-cell-result-1 file (the tracker's per-cell result schema) from a CHIMport result."""
    st = res.get('stats') or {}
    tot = res['records']['totals']
    faces = st.get('faces') or {}
    placed, terrain = faces.get('placed'), faces.get('terrain')
    disk = st.get('disk') or {}
    cats = (plan_row or {}).get('categories') or {}
    stats = {
        'records': dict({'refs_total': tot['placed'], 'converted': tot['converted'], 'deferred': tot['deferred'],
                         'failed': tot['failed'], 'skipped': tot['skipped']},
                        **{k: cats.get(k, 0) for k in ('statics', 'flora', 'lights', 'doors', 'containers', 'activators',
                                                      'actors', 'creatures', 'items')}),
        'records_by_type': res['records']['by_type'],
        'meshes': {'new': (st.get('meshes') or {}).get('new', 0), 'reused': (st.get('meshes') or {}).get('reused', 0),
                   'unique': (st.get('meshes') or {}).get('unique_in_cell', 0)},
        'faces': {'before': faces.get('source_triangles'), 'after': None if placed is None else placed - (terrain or 0),
                  'chim_terrain': terrain, 'chim_placed': None if placed is None else placed - (terrain or 0),
                  'chim_stored': faces.get('stored')},
        'textures': st.get('textures') or {},
        'bytes': {'chim': disk.get('chim_bytes'), 'legacy': disk.get('legacy_region_bytes')},
        'chunks': {'count': disk.get('chunks'), 'bytes': disk.get('chim_bytes')},
        'collision': st.get('collision') or {},
        'memory': st.get('memory') or {},
        'vis': st.get('vis') or {},
        'time': {'convert_s': res.get('wall_s'), 'cpu_s': res.get('cpu_s')},
    }
    audits = {m: dict({'status': a['status'], 'detail': a.get('detail'), 'numbers': a.get('numbers') or {}},
                      **({'outcome': a['outcome']} if a.get('outcome') else {}))
              for m, a in (res.get('audits') or {}).items() if m in TRACKER_MECHANISMS}
    if cell_status(res) == 'hull_pending':
        # not a failure while the hull-chain rule is being settled: shown apart, never red
        for m in POLICY_PENDING:
            if m in audits and audits[m]['status'] == 'failed':
                audits[m] = dict(audits[m], status='not_measured',
                                 detail='hull policy pending: ' + (audits[m]['detail'] or ''), policy_pending=True)
    return {'converted': bool(res['converted']), 'status': cell_status(res), 'empty': cell_status(res) == 'empty',
            # usable now: passed (lighting aside, which the lighting audit judges) or empty sea
            'eligible': cell_status(res) in ELIGIBLE,
            'stats': stats, 'audits': audits,
            'errors': [{'stage': e['stage'], 'mechanism': e['mechanism'], 'message': e['message'][:500]}
                       for e in res.get('errors') or []],
            'provenance': {'builder': 'chimport', 'ring': (plan_row or {}).get('ring'),
                           'order': (plan_row or {}).get('order'), 'finished': res.get('finished')}}


def feed(run_dir, build=None, all_cells=False):
    """Write RUN/tracker/result-NNN.json (aw-cell-result-1) with the finished cells not fed before; returns its
    path or None. The tracker's ingester stores it (cell_progress.py result --file) and is the only writer."""
    plan = read_json(run_dir / 'plan.json') or {'cells': []}
    rows = {ckey((r['x'], r['y'])): r for r in plan['cells']}
    fed_path = run_dir / 'tracker' / 'fed.json'
    fed = read_json(fed_path) or {}
    from chim import CHIM_VERSION, FORMAT_VERSION
    cells = {}
    for key, r in rows.items():
        cdir = run_dir / 'cells' / cell_dir((r['x'], r['y']))
        res = read_json(cdir / 'result.json')
        if not res or (not all_cells and fed.get(key) == res.get('finished')):
            continue
        cells[key] = tracker_cell(res, r)
        fed[key] = res.get('finished')
    if not cells:
        return None
    doc = {'format': TRACKER_RESULT, 'build': build or 'chimport-' + run_dir.name, 'generated': now_iso(),
           'provenance': {'builder': 'chimport', 'chim_version': CHIM_VERSION,
                          'world_format': '%d.%d' % FORMAT_VERSION, 'run': run_dir.name},
           'cells': cells}
    n = len(list((run_dir / 'tracker').glob('result-*.json'))) if (run_dir / 'tracker').is_dir() else 0
    path = run_dir / 'tracker' / ('result-%04d.json' % (n + 1))
    write_json(path, doc)
    write_json(fed_path, fed)
    return path


def feed_tracker(run_dir, tracker, tool, ingest_args=''):
    """feed(), then the tracker's own ingester stores the result file and refreshes its data (it stays the only
    writer of the progress data). Returns 0, or the ingester's exit code."""
    import shlex
    fed_path = run_dir / 'tracker' / 'fed.json'
    before = read_json(fed_path)
    path = feed(run_dir)
    if path is None:
        print('%s chimport feed: nothing new' % now_iso(), flush=True)
        return 0
    rc = subprocess.call([sys.executable, str(tool), 'result', '--out', str(tracker), '--file', str(path)])
    if rc != 0:
        # not stored: these cells are fed again next time
        write_json(fed_path, before or {})
        print('%s chimport feed: %s refused by the tracker (exit %d); kept for the next feed'
              % (now_iso(), path.name, rc), flush=True)
        return rc
    if rc == 0:
        rc = subprocess.call([sys.executable, str(tool), 'ingest', '--out', str(tracker)] + shlex.split(ingest_args or ''))
    print('%s chimport feed: %s -> tracker (exit %d)' % (now_iso(), path.name, rc), flush=True)
    return rc


# ------------------------------------------------------------------ command line

def entry(a):
    """The entry check of run/cell/world (tools/entry_check.py; BUILD-IMAGE-STALE-PYTHONPATH-35): builder code
    only from this source tree, and the source VERSION equal to the working version when a record is found.
    `run` prints the block and passes the record on to its cells. Returns the refusal text or None."""
    import entry_check
    refused = entry_check.guard_imports(ROOT, log=print if a.cmd == 'run' else None)
    record = entry_check.check(ROOT, a.working_version, Path(a.out),
                               accept_mismatch=a.accept_version_mismatch or os.environ.get('AMIWIND_ACCEPT_VERSION_MISMATCH'))
    if a.cmd == 'run':
        print('\n'.join(entry_check.lines(record, 'chimport entry check')), flush=True)
        if record['working_version']['record']:
            os.environ[entry_check.ENV] = str(Path(record['working_version']['record']).resolve())
        if a.accept_version_mismatch:
            os.environ['AMIWIND_ACCEPT_VERSION_MISMATCH'] = a.accept_version_mismatch
    if refused:
        return refused
    if not record['ok']:
        return 'chimport entry check refused: ' + '; '.join(record['refusals'])
    return None


def add_pool_options(q):
    """The builder's storage pool options (tools/build.py), for the CHIMporter's units and cell outputs."""
    q.add_argument('--storage-pool', choices=POOL_SETTINGS, default='off',
                   help='Store every unit (meshes, variants, textures, terrain, visibility) and every cell output once '
                        'in the shared content-addressed storage pool and link them into the run; a unit or a whole '
                        'cell already in the pool (any earlier run, any workspace) is linked, not converted again. '
                        'off (default: the run\'s own units/ cache, as before), on, or auto (on when a pool folder '
                        'is named). See docs/chim/CHIMPORT.md')
    q.add_argument('--reuse-mode', choices=REUSE_MODES, default='copy',
                   help='How units and cells found in the pool reach the run: copy (default) or a read-only hard '
                        'link (hardlink and pool: the pool is the reuse source). Needs the storage pool')
    q.add_argument('--storage-pool-dir', type=Path, metavar='DIR',
                   help='The pool folder (else AMIWIND_STORAGE_POOL, else WORKSPACE/cache/asset-pool-v1 with '
                        '--workspace). Name the builder\'s pool to share ONE pool between builds and the CHIMporter')
    q.add_argument('--workspace', type=Path, help='a build workspace: its pool WORKSPACE/cache/asset-pool-v1')


def add_region_option(q):
    q.add_argument('--region', action='append', metavar='NAME',
                   help='only the cells of this region as named in plan.json (repeatable; "Bitter Coast" finds '
                        '"Bitter Coast Region"; an unknown name lists the plan\'s regions)')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split('\n', 2)[2])
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('plan', help='write RUN/plan.json (census and ring order) and print it')
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--rings', type=int)
    p.add_argument('--cells')
    add_region_option(p)
    r = sub.add_parser('run', help='convert and audit the selected cells (resumable, parallel)')
    for q in (r,):
        q.add_argument('--data-files', type=Path, required=True)
        q.add_argument('--palette', type=Path, required=True)
        q.add_argument('--out', type=Path, required=True)
        q.add_argument('--qbsp', type=Path)
        q.add_argument('--sdk', type=Path, help='Amiga SDK: the CHIM heap gate probes the engine ABI sizes once')
        q.add_argument('--workers', type=int, default=8, help='cells converted at once (default 8)')
        q.add_argument('--jobs', type=int, default=2, help='worker processes inside each cell (default 2)')
        q.add_argument('--rings', type=int, help='only rings 0..N-1')
        q.add_argument('--cells', help='only these cells: "x,y x,y ..."')
        q.add_argument('--retry-failed', action='store_true', help='run failed cells again')
        q.add_argument('--timeout', type=int, default=3600, help='seconds per cell before it is stopped (default 3600)')
        q.add_argument('--dry-run', action='store_true', help='print what would run')
        q.add_argument('--world-every', type=int, default=1,
                       help='build the growing world every N rings (and after the last); its whole-world audit grows '
                            'with the island and blocks the cells while it runs (default 1)')
        q.add_argument('--world-timeout', type=int, default=6 * 3600,
                       help='seconds before a growing-world build is stopped (default 6 h; it grows with the island)')
        q.add_argument('--no-world', action='store_true',
                       help='do not build the growing world (every converted cell so far) after each ring')
        q.add_argument('--tracker', type=Path, help='CHIM Progress Tracker folder: finished cells are fed to it '
                       'automatically (its own ingester stores them: cell_progress.py result, then ingest)')
        q.add_argument('--tracker-tool', type=Path, help='the tracker ingester (tools/cell_progress.py)')
        q.add_argument('--tracker-ingest', default='',
                       help='extra arguments of the tracker ingest after a feed (its usual inputs), one string')
        q.add_argument('--feed-every', type=int, default=180, help='seconds between automatic feeds (default 180)')
        add_region_option(q)
        add_pool_options(q)
    c = sub.add_parser('cell', help='convert and audit one cell (what `run` starts per cell)')
    c.add_argument('--data-files', type=Path, required=True)
    c.add_argument('--palette', type=Path, required=True)
    c.add_argument('--cell', required=True)
    c.add_argument('--out', type=Path, required=True)
    c.add_argument('--qbsp', type=Path)
    c.add_argument('--unit-cache', type=Path)
    c.add_argument('--jobs', type=int, default=2)
    c.add_argument('--abi-sizes', type=Path, help='engine ABI sizes JSON (written by `run --sdk`)')
    c.add_argument('--sdk', type=Path, help='Amiga SDK (probe the ABI sizes for this cell)')
    add_pool_options(c)
    c.add_argument('--missing-land', default='flat', choices=('flat', 'refuse'),
                   help='a cell without land: flat seabed at the default height (default) or refuse')
    w = sub.add_parser('world', help='build one CHIM world of every converted cell so far and audit it whole')
    w.add_argument('--data-files', type=Path, required=True)
    w.add_argument('--palette', type=Path, required=True)
    w.add_argument('--out', type=Path, required=True)
    w.add_argument('--name', help='world folder name (default ring-K, or all)')
    w.add_argument('--through-ring', type=int, help='only cells of rings 0..K')
    w.add_argument('--qbsp', type=Path)
    w.add_argument('--jobs', type=int, default=2)
    w.add_argument('--abi-sizes', type=Path)
    add_pool_options(w)
    w.add_argument('--no-heap', dest='heap', action='store_false',
                   help='leave out the whole-world heap audit (per frame, --jobs; CHIM-WORLD-AUDIT-SCALING-33)')
    f = sub.add_parser('feed', help='write the finished cells not fed yet as a tracker result file (aw-cell-result-1)')
    f.add_argument('--out', type=Path, required=True)
    f.add_argument('--build', help='build name in the tracker (default chimport-<run folder name>)')
    f.add_argument('--all', action='store_true', help='every finished cell, also those fed before')
    ft = sub.add_parser('feed-tracker', help='feed, then store the result with the tracker ingester and re-ingest')
    ft.add_argument('--out', type=Path, required=True)
    ft.add_argument('--tracker', type=Path, required=True)
    ft.add_argument('--tracker-tool', type=Path, required=True)
    ft.add_argument('--tracker-ingest', default='')
    s = sub.add_parser('status', help='print the totals per ring and the failure classes')
    s.add_argument('--out', type=Path, required=True)
    e = sub.add_parser('export', help='per-cell stats as CSV and/or JSON')
    e.add_argument('--out', type=Path, required=True)
    e.add_argument('--csv', type=Path)
    e.add_argument('--json', type=Path)
    for q in (r, c, w):
        q.add_argument('--working-version', type=Path, metavar='FILE',
                       help='working-version record for the entry check (default: AMIWIND_WORKING_VERSION, then '
                            'OUT/../WORKING_VERSION.json; tools/entry_check.py)')
        q.add_argument('--accept-version-mismatch', metavar='REASON',
                       help='convert although the source VERSION differs from the working version (say why)')
    a = ap.parse_args(argv)
    if a.cmd in ('run', 'cell', 'world'):
        refused = entry(a)
        if refused:
            print(refused, file=sys.stderr)
            return 2
    if a.cmd == 'plan':
        plan = read_json(a.out / 'plan.json') or make_plan(a.data_files)
        write_json(a.out / 'plan.json', plan)
        rows = select(plan, a.rings, parse_cells(a.cells), a.region)
        rings_n = collections.Counter(r['ring'] for r in rows)
        print('chimport plan: %d cells (%s)' % (len(rows), ', '.join('ring %d: %d' % kv for kv in sorted(rings_n.items()))))
        return 0
    if a.cmd == 'run':
        return run(a)
    if a.cmd == 'cell':
        x, y = parse_cells(a.cell)[0]
        sizes = read_json(a.abi_sizes) if a.abi_sizes else None
        if sizes is None and a.sdk:
            from check_world_map_heap import compile_target_sizes
            sizes = compile_target_sizes(a.sdk)[0]
        pool, origin = pool_choice(a)
        res = convert_cell_pooled((x, y), a.data_files, a.palette, a.out, a.qbsp, a.unit_cache, a.jobs,
                                  None if a.missing_land == 'refuse' else a.missing_land, sizes, pool, origin,
                                  a.reuse_mode)
        print(json.dumps({'cell': res['key'], 'converted': res['converted'], 'errors': [e['mechanism'] for e in res['errors']],
                          'audits_failed': [m for m, v in res['audits'].items() if v['status'] == 'failed'],
                          'wall_s': res['wall_s'], 'pool': res.get('pool', {}).get('cell')}))
        return 0
    if a.cmd == 'world':
        plan = read_json(a.out / 'plan.json')
        rows = [r for r in converted_cells(a.out, plan) if a.through_ring is None or r['ring'] <= a.through_ring]
        name = a.name or ('ring-%d' % a.through_ring if a.through_ring is not None else 'all')
        pool, origin = pool_choice(a)
        link = False
        if pool is not None:
            import storage_pool
            link = storage_pool.setting(pool, origin, a.out)['links'] and a.reuse_mode != 'copy'
        rep = build_world(a.out, a.data_files, a.palette, name, rows, a.qbsp, a.jobs,
                          read_json(a.abi_sizes) if a.abi_sizes else read_json(a.out / 'abi-sizes.json'), heap=a.heap,
                          pool=pool, link=link)
        print(json.dumps({'name': rep['name'], 'built': rep['built'], 'cells': len(rep['cells']), 'wall_s': rep['wall_s'],
                          'heap': rep.get('heap'), 'disk': rep.get('disk'),
                          'validation_failures': (rep.get('validation') or {}).get('failure_count'),
                          'errors': [e['mechanism'] for e in rep['errors']]}))
        return 0
    if a.cmd == 'feed':
        path = feed(a.out, a.build, a.all)
        print(path or 'chimport feed: nothing new')
        return 0
    if a.cmd == 'feed-tracker':
        return feed_tracker(a.out, a.tracker, a.tracker_tool, a.tracker_ingest)
    if a.cmd == 'status':
        print(json.dumps(summarise(a.out), indent=1, sort_keys=True))
        return 0
    if a.cmd == 'export':
        rows = export_rows(a.out)
        if a.csv:
            write_csv(a.csv, rows)
        if a.json:
            write_json(a.json, {'format': 'aw-chimport-export-1', 'generated': now_iso(), 'summary': summarise(a.out),
                                'cells': rows})
        if not a.csv and not a.json:
            write_csv('/dev/stdout', rows)
        return 0
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
