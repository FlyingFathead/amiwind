#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""CHIMport: convert the whole island to CHIM cell by cell, from the sea inwards, and audit every cell.

    chimport.py plan   --data-files DIR --out RUN [--rings N] [--cells "x,y x,y"]
    chimport.py run    --data-files DIR --palette PALETTE.lmp --out RUN [--qbsp QBSP] [--workers N] [--jobs N]
                       [--rings N] [--cells "x,y ..."] [--retry-failed] [--timeout S] [--dry-run]
    chimport.py cell   --data-files DIR --palette PALETTE.lmp --cell X,Y --out CELLDIR [--unit-cache DIR] ...
    run, cell, world:  [--storage-pool auto|on|off] [--reuse-mode copy|hardlink|pool] [--storage-pool-dir DIR]
                       [--frame-settings build|cell-v1] [--cell-shape cell|region] [--mesh-method-set NAME]
    plan, run:         [--region NAME]  (the cells of a region of plan.json; repeatable)
    chimport.py ocean  --data-files DIR --palette PALETTE.lmp --out RUN [--rect X0,X1,Y0,Y1] [--margin N] [--dry-run]
                       [--storage-pool ...] [--tracker DIR --tracker-tool tools/cell_progress.py]
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

A cell is converted as a default build converts it: the build's frame settings (FRAME_SETTING_SETS 'build') and the
converter switches a build exports (export_build_switches), so its units carry the keys a build asks for and its
figures are measured on what a build stores; each result records them (result.json "settings").
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


def _own_search_path():
    """src before tools at the front of sys.path: the package src/mwad must win over the command tools/mwad.py.
    Called again after imports that put tools/ first (stair_walk.py; CHIMPORT-CLI-MWAD-SHADOW-66)."""
    for _p in (ROOT / 'tools', ROOT / 'src'):
        while str(_p) in sys.path:
            sys.path.remove(str(_p))
        sys.path.insert(0, str(_p))


_own_search_path()

PLAN_FORMAT = 'aw-chimport-plan-1'
STATE_FORMAT = 'aw-chimport-state-1'
CELL_FORMAT = 'aw-chimport-cell-1'
CELL_UNITS = 8192                       # Morrowind units per exterior cell
SCALE = 0.25                            # world scale of every converted frame
HALF = int(CELL_UNITS * SCALE) // 2       # 1024 map units: half a cell
# World settings of a one-cell frame: 8 x 8 chunks of 256 units; sectors must divide 8 (Balmora's 3 x 3 cell
# frame uses 3), so a cell frame stores 4 x 4 chunk sectors.
# build (the default since v0.0.68): also the settings a default build's CHIM stage hands chim.build.build_areas
# (tools/build.py chim_stage_options over the defaults of tools/build_parser.py: --terrain-hull compiled,
# --terrain-refs on, --terrain-pack generate, --uv-scroll turbulent, which tools/chim_build.py turns into these keys),
# so a cell's frame is stored as a build stores it, its memory figures are measured on that, and its units carry the
# keys a build asks for (CHIMPORT-UNITS-NOT-SHARED-WITH-BUILD-68, CHIMPORT-HEAP-NOT-BUILD-FRAMES-68).
# tests/test_chimport_build_settings.py checks this copy against tools/build.py: a build default changed there
# fails that test until the copy here follows it. cell-v1: the settings before (the island's runs of October 2026:
# terrain copied into every chunk with the BSP29 packing, routed terrain hulls on regular ground, still scrolling
# textures), kept selectable for A/B (--frame-settings cell-v1).
FRAME_SETTING_SETS = {
    'build': {'grain': 256, 'sector_chunks': 4, 'terrain_hull': 'compiled', 'terrain_refs': 'on',
              'terrain_pack': 'generate', 'uv_scroll': 'turbulent'},
    'cell-v1': {'grain': 256, 'sector_chunks': 4},
}
FRAME_SETTINGS_DEFAULT = 'build'
FRAME_SETTINGS = FRAME_SETTING_SETS[FRAME_SETTINGS_DEFAULT]
# The shape of a cell's frame (CHIMPORT-HEAP-NOT-BUILD-FRAMES-68, part 2). cell (the default for now): the cell's own
# frame with nothing of its neighbours; its memory figures are the cell "alone". region: the frame a build installs for
# the cell, made by the build's own function (chim.regions.frame_settings over chim.regions.frame_row, the margin
# chim.regions.TERRAIN_MARGIN as tools/chim_build.py gives it): the neighbours' placements and terrain within the
# margin are copied in (source radius 1, the apron), so its memory figures are the ones a build measures for that
# frame. Its 15 x 15 chunks take the world's default sectors, as a build's do (no sector_chunks of CHIMport's own).
CELL_SHAPES = ('cell', 'region')
CELL_SHAPE_DEFAULT = 'cell'
# A region frame is built here as a world of its own, but it stands for one frame of the build's world: a piece of a
# neighbour's model wholly outside it is held by that neighbour's own frame when the neighbour has one
# (chim.ownership.select_compiled_apron, CHIM-FRAME-EDGE-CLAMPS-OUTSIDE-TILES-68). The world a run's frames stand for:
# the run's own cells and the cells the project's reference calls finished, written once per run (RUN/<this>).
WORLD_CELLS_FILE = 'world-frame-cells.json'
CELL_REFERENCE = ROOT / 'docs' / 'chim' / 'cell-progress-reference.json'


def world_frame_cells(run_cells, reference=CELL_REFERENCE):
    """{'cells': [[x, y], ...], 'run_cells', 'reference_sha256'}: RUN_CELLS and the land and seabed cells the reference
    calls finished (chim.regions.kind_of), sorted."""
    import hashlib
    from chim.regions import kind_of, load_status
    reference = Path(reference)
    finished = set()
    sha = None
    if reference.is_file():
        sha = hashlib.sha256(reference.read_bytes()).hexdigest()
        finished = {tuple(c) for c, rec in load_status(reference).items() if kind_of(rec.get('status')) in ('land', 'seabed')}
    cells = sorted({tuple(c) for c in run_cells} | finished)
    return {'format': 'aw-chimport-world-cells-1', 'cells': [list(c) for c in cells],
            'run_cells': len({tuple(c) for c in run_cells}), 'reference_sha256': sha}


def frame_settings(name=None, qbsp=None, shape=None):
    """The frame settings a cell is built with (FRAME_SETTING_SETS[NAME], default build). The compiled terrain hull
    needs qbsp: without it the setting is left out, so the terrain hull is chim.build's auto (routed on regular
    ground), which the result's settings record shows. SHAPE region: without CHIMport's sector size (a region frame's
    15 x 15 chunks take the world's default, as in a build)."""
    settings = dict(FRAME_SETTING_SETS[name or FRAME_SETTINGS_DEFAULT])
    if not qbsp and settings.get('terrain_hull') == 'compiled':
        settings.pop('terrain_hull')
    if (shape or CELL_SHAPE_DEFAULT) == 'region':
        settings.pop('sector_chunks', None)
    return settings


def export_build_switches():
    """Export the converter switches a default build exports, with the build's own resolver and exporters
    (tools/build.py export_converter_environment: build_font_options.resolve_font_options over
    config/build-defaults.json, then mesh_geometry_env.export_stair_rules and export_model_hull, lava.export_lava,
    hollow_bevels_env.export_hollow_bevels, scenery_reduce.apply_options), so every unit a cell makes is keyed as a
    build keys it (chim.units.tool_fingerprint hashes the raw values of chim.units.SWITCHES; unset reads as the same
    default, so nothing converts differently: CHIMPORT-UNITS-NOT-SHARED-WITH-BUILD-68). A value the caller set in the
    environment stays (an A/B run); the cell results record what they ran with. Returns {'switches': {name: value of
    every chim.units.SWITCHES entry}, 'explicit': [names the caller set]}."""
    import argparse
    import hollow_bevels_env
    import lava
    import scenery_reduce
    from build_font_options import resolve_font_options
    from chim.units import SWITCHES
    from mesh_geometry_env import export_model_hull, export_stair_rules
    explicit = {name: os.environ[name] for name in SWITCHES if os.environ.get(name, '').strip()}
    options = resolve_font_options(argparse.Namespace())
    export_stair_rules(options['follow_original_stair_rules'])
    export_model_hull(options['model_hull'])
    lava.export_lava(options['lava'])
    hollow_bevels_env.export_hollow_bevels(None)
    scenery_reduce.apply_options(argparse.Namespace(texinfo_snap=None, scenery_reduce=None,
                                                    scenery_reduce_texels=None))
    os.environ.update(explicit)
    return {'switches': switch_values(), 'explicit': sorted(explicit)}


def switch_values():
    """{name: value} of the unit-keyed converter switches (chim.units.SWITCHES) as this process sees them."""
    from chim.units import SWITCHES
    return {name: os.environ.get(name, '') for name in SWITCHES}


def settings_record(frame, palette, name=None, shape=None):
    """The settings a cell or a run converts with, as its results record them: the frame settings (their set's name
    and the effective keys), the cell shape, the unit-keyed switches, the palette's SHA-256 (it must be the build's
    census palette, intro-scene/id1/gfx/palette.lmp, for the texture units to be a build's)."""
    import hashlib
    try:
        palette_sha = hashlib.sha256(Path(palette).read_bytes()).hexdigest()
    except OSError:
        palette_sha = None
    return {'frame_settings': name or FRAME_SETTINGS_DEFAULT, 'frame': dict(frame),
            'cell_shape': shape or CELL_SHAPE_DEFAULT, 'switches': switch_values(), 'palette_sha256': palette_sha}
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


def census(esm, land_records=()):
    """{(x, y): {land, name, region, refs, by_type, categories, meshes}} for every exterior cell that has land
    or placed records (the base master's own records; deleted references left out). land_records: every live LAND
    record of the masters, also those without height data: such a cell with nothing placed is a seabed cell
    (`seabed`: True), converted as its own cell with flat ground, never open ocean (CHIMPORT-OCEAN-LAND-41)."""
    from mwad.audit import normpath
    out = {}
    seabed = set(land_records) - set(esm['lands'])
    for key in set(esm['cells']) | set(esm['lands']) | seabed:
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
        if key not in esm['lands'] and not refs and key not in seabed:
            continue
        out[key] = {'land': key in esm['lands'], 'name': cell['name'], 'region': cell['region'], 'refs': len(refs),
                    'by_type': dict(by_type), 'categories': dict(cats), 'missing_objects': missing,
                    'meshes': sorted(meshes)}
        if key in seabed:
            out[key]['seabed'] = True
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
    sea = {c for c, v in cells.items() if not v['land'] and (v['refs'] or v.get('seabed'))}
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
    from mwad.masters import master_path, selected_masters
    data = resolve_data_files(data_files)
    esm = load_esm(master_path(data))
    from chim.ocean_runtime import land_cells
    # the LAND records of the masters the merged file holds (AMIWIND_MASTERS): a layer's seabed cells (LAND without
    # heights) are seabed like the island's; with the base game alone this is the base master's own, as before
    cells = census(esm, land_cells(data, selected_masters()))
    order = order_cells(cells)
    rows = []
    for i, (c, ring) in enumerate(order, 1):
        v = cells[c]
        rows.append(dict(v, x=c[0], y=c[1], ring=ring, order=i))
    return {'format': PLAN_FORMAT, 'generated': now_iso(), 'master': 'Morrowind.esm', 'esm_sha256': esm['sha256'],
            'rule': 'ring 0 = sea cells without land that hold records, and seabed cells (a LAND record without '
                    'heights); ring 1 = land touching the sea; inwards',
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

def cell_settings(cell, missing_land='flat', shape=None):
    """Converter settings of a one-cell frame (the town settings shape of docs/TOWN_IMPORT.md). SHAPE region: the
    settings of the region frame a build makes for the cell, by the build's own function (chim.regions.frame_settings,
    CELL_SHAPES), where a cell without land is always flat default ground."""
    if (shape or CELL_SHAPE_DEFAULT) == 'region':
        if missing_land != 'flat':          # None: --missing-land refuse
            raise ValueError('the region shape is the frame a build installs, where a cell without land is flat ground '
                             '(not --missing-land %s)' % (missing_land or 'refuse'))
        from chim import regions
        return regions.frame_settings(regions.frame_row(tuple(cell), regions.TERRAIN_MARGIN), regions.TERRAIN_MARGIN)
    x, y = cell
    ident = 'c%s%d_%s%d' % ('m' if x < 0 else 'p', abs(x), 'm' if y < 0 else 'p', abs(y))
    from visual_recipes import cell_settings as recipe_cell_settings
    return {
        **recipe_cell_settings((x, y)),
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
    import cache_provenance
    cache_provenance.sidecar_unit(path, kind, fp)


@contextlib.contextmanager
def generated_frames(settings_list):
    """The region-shape frames of SETTINGS_LIST registered as a build's chim stage registers its region frames
    (town_config.register_generated: the converter treats them as generated areas, as in a build), and taken out again
    afterwards (an entry that was there before is put back)."""
    import town_config
    regional = [s for s in settings_list if s.get('region_source_apron')]
    before = {s['town']['id']: town_config.generated_areas().get(s['town']['id']) for s in regional}
    town_config.register_generated(regional)
    try:
        yield
    finally:
        for ident, old in before.items():
            if old is None:
                town_config._GENERATED.pop(ident, None)
            else:
                town_config._GENERATED[ident] = old


@contextlib.contextmanager
def cell_area(settings):
    """Make the CHIM builder read these settings for the cell's area id (the builder takes areas by id), with
    unit cache writes that are safe while other cells share the cache. A region-shape frame is also a generated area
    while the block runs (generated_frames)."""
    import town_config
    from chim.units import UnitCache
    ident = settings['town']['id']
    original, put = town_config.load_settings, UnitCache.put

    def load(town_id, root=None):
        return settings if town_id == ident else original(town_id, root)
    town_config.load_settings = load
    UnitCache.put = _shared_put
    try:
        with generated_frames([settings]):
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


MARKER_REASON = 'nonvisual source marker'   # import_town's reason for a record with a marker model
ELIGIBLE = ('passed', 'empty', 'ocean')   # cells usable as release candidates (complete apart from lighting)
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


ACCEPTED_CHAINS = ROOT / 'config' / 'hull-chain-accepted.json'


def accepted_chains(path=ACCEPTED_CHAINS):
    """{mesh stem: reason} of meshes the maintainer accepted as standing-hull chains (config/hull-chain-accepted.json):
    models whose collision the router cannot split (COLLISION-ROUTE-NO-SPLIT-36); the hull audit passes them with
    the kept-as-chain outcome, as the meshes the heap fallback keeps for memory. {} without the file."""
    path = Path(path)
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    return {_mesh_stem(r['mesh']): r['reason'] for r in data.get('meshes', [])}


def _mesh_stem(name):
    stem = (name or '').split('@')[0].replace(chr(92), '/').lower()
    stem = stem.rsplit('/', 1)[-1]
    return stem[:-4] if stem.endswith('.nif') else stem


# A LIGH placement without a mesh: in Quake terms a light entity (baked by the light compiler, animated by a
# lightstyle); CHIM frames have no light entities or lightmaps yet, so it is deferred with this reason.
MESHLESS_LIGHT_REASON = 'light without a mesh: no CHIM light path yet (CHIM-MESHLESS-LIGHTS-33)'


def _placed_cell(r):
    """The cell a source placement belongs to, (x, y) or None."""
    c = r.get('cell')
    return (int(c[0]), int(c[1])) if isinstance(c, (list, tuple)) and len(c) == 2 else None


def record_accounting(work, source, chim_refs, owned=None):
    """Per record type: placed in the cell, converted (in the CHIM world), deferred (reason), failed. OWNED: the cell
    of a region-shape frame: only its own placements are counted (the neighbours' copies are apron_figures')."""
    placements = read_json(work / 'audit/placements.json') or []
    if owned is not None:
        placements = [r for r in placements if _placed_cell(r) == tuple(owned)]
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


def source_facts(work, owned=None):
    """What the cell's source stage read for the cell (its terrain audit, work/audit/audit.json): the references, whether
    the cell had no land there (flat ground at the default height), and the SHA-256 of the master it read. {} when the
    audit was not written. OWNED: the cell of a region-shape frame, whose source stage reads its neighbours too: the
    references and the land are the owned cell's; the neighbours' are named apart (apron_references, and the
    neighbours read as flat default ground, apron_default_land_cells)."""
    audit = read_json(Path(work) / 'audit' / 'audit.json') or {}
    area = audit.get('area') or {}
    if not area:
        return {}
    master = (audit.get('input') or {}).get('esm_sha256')
    if owned is None:
        return {'references': area.get('references'), 'default_land': bool(area.get('default_land_cells')),
                'master_sha256': master}
    owned = tuple(owned)
    placements = read_json(Path(work) / 'audit' / 'placements.json') or []
    mine = sum(1 for r in placements if _placed_cell(r) == owned)
    flat = {(int(c[0]), int(c[1])) for c in area.get('default_land_cells') or []}
    return {'references': mine, 'default_land': owned in flat, 'master_sha256': master,
            'apron_references': len(placements) - mine,
            'apron_default_land_cells': [ckey(c) for c in sorted(flat - {owned})]}


def apron_figures(work, world, owned, chim_refs):
    """The neighbours' share of a region-shape frame (its apron; CHIMPORT-HEAP-NOT-BUILD-FRAMES-68): per neighbouring
    cell, the placements the source stage read there, how many of them the frame holds, and the frame's chunks over
    that cell (its terrain there); the owned cell's chunks; and the neighbours read as flat default ground (no LAND
    record: the sea, or a cell with no record), named so that a smaller apron is never silent: a neighbour the source
    stage did not read is a problem of the cell (problems; convert_cell records it as an error). Without a world (its
    validation failed) the chunk figures are None: not measured."""
    owned = tuple(owned)
    area = (read_json(Path(work) / 'audit' / 'audit.json') or {}).get('area') or {}
    read = {(int(c['x']), int(c['y'])) for c in area.get('cells') or []}
    flat = {(int(c[0]), int(c[1])) for c in area.get('default_land_cells') or []}
    measured = world is not None
    cells = collections.OrderedDict()

    def row(cell):
        return cells.setdefault(ckey(cell), {'read': cell in read, 'ground': 'flat default' if cell in flat else 'land',
                                             'placements_read': 0, 'placements_in_frame': 0,
                                             'chunks': 0 if measured else None})
    for dx, dy in sorted(NEIGHBOURS):
        row((owned[0] + dx, owned[1] + dy))
    for r in read_json(Path(work) / 'audit' / 'placements.json') or []:
        c = _placed_cell(r)
        if c is None or c == owned:
            continue
        rec = row(c)
        rec['placements_read'] += 1
        if r.get('number') in chim_refs:
            rec['placements_in_frame'] += 1

    def side(centre):
        # the cell a chunk centre lies over, along one axis, in frame-local map units (the owned cell is -HALF..HALF);
        # a chunk across the owned cell's edge (its centre on the edge) is the owned cell's on both sides alike
        if abs(centre) <= HALF:
            return 0
        steps = 1 + int((abs(centre) - HALF) // (2 * HALF))
        return steps if centre > 0 else -steps
    owned_chunks = 0 if measured else None
    for item in (world or {}).get('frames') or []:
        frame, chunks = (item[1], item[2]) if isinstance(item, (list, tuple)) else (item, item.get('chunks') or [])
        g, (lx, ly) = frame['grain'], frame['low']
        for ch in chunks:
            dx, dy = side(lx + (ch['cx'] + 0.5) * g), side(ly + (ch['cy'] + 0.5) * g)
            if (dx, dy) == (0, 0):
                owned_chunks += 1
            else:
                row((owned[0] + dx, owned[1] + dy))['chunks'] += 1
    # without the audit (the build failed before its source stage) the cell has failed already: nothing to name here
    problems = ['neighbour %s was not read by the source stage (the apron would be smaller than a build\'s)' % k
                for k, v in cells.items() if area and not v['read']]
    return {'cells': dict(cells), 'owned_chunks': owned_chunks,
            'chunks': sum(v['chunks'] for v in cells.values()) if measured else None,
            'placements_read': sum(v['placements_read'] for v in cells.values()),
            'placements_in_frame': sum(v['placements_in_frame'] for v in cells.values()),
            'flat_default_ground': [ckey(c) for c in sorted(flat - {owned})], 'problems': problems}


PLAN_MISMATCH = 'plan-mismatch'
APRON_INCOMPLETE = 'apron-incomplete'     # a region-shape cell whose source stage did not read a neighbour


def plan_mismatch(row, res):
    """Why a converted cell's build did not read what the run's plan holds for it, [] when it did
    (CHIMPORT-LAYER-CELL-EMPTY-67). The plan reads the selected masters merged; a build that read less (no land where
    the plan has land, fewer placements than the plan's) converted another cell than the one planned, for example an
    expansion's cell read from the base game's file alone, built as flat ground with nothing placed and counted as
    empty. Such a cell fails instead of counting as done."""
    if not res.get('converted'):
        return []
    key = ckey((row['x'], row['y']))
    facts = res.get('source') or {}
    placed = ((res.get('records') or {}).get('totals') or {}).get('placed')
    problems = []
    if row.get('land') and facts.get('default_land'):
        problems.append('the plan has land for %s, the build read none (flat ground at the default height)' % key)
    if row.get('refs') and placed is not None and placed < row['refs']:
        problems.append('the plan holds %d placements in %s, the build read %d' % (row['refs'], key, placed))
    if problems and facts.get('master_sha256'):
        problems.append('the build read the master with SHA-256 %s' % facts['master_sha256'])
    return problems


def check_against_plan(row, res):
    """RES with a plan-mismatch error added when its build read less than its plan row (plan_mismatch); the status
    follows (cell_status: an error fails the cell)."""
    problems = plan_mismatch(row, res)
    if problems:
        res.setdefault('errors', []).append({'stage': 'plan-check', 'mechanism': PLAN_MISMATCH,
                                             'message': '; '.join(problems)})
    return res


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
        accepted = accepted_chains()     # maintainer-accepted chains (COLLISION-ROUTE-NO-SPLIT-36): kept as chain too
        over = [h for h in hulls if h.get('over', h['depth'] >= LEGACY_CHAIN_DEPTH)]
        # meshes the heap fallback kept as chains for memory: their own outcome, not a failure
        owner = [h for h in over if _mesh_stem(h['name']) in accepted and _mesh_stem(h['name']) not in kept_stems]
        for_memory = [h for h in over if _mesh_stem(h['name']) in kept_stems]
        deep = [h for h in over if h not in for_memory and h not in owner]
        owner_stems = sorted({_mesh_stem(h['name']) for h in owner})
        put('hull_bevels', 'failed' if deep else 'passed',
            '%d models over the hull-chain limit (max depth %d)%s%s%s' % (
                len(deep), max([h['depth'] for h in hulls] or [0]),
                ': ' + ', '.join('%s (depth %d, %d clipnodes)' % (h['name'], h['depth'], h['clipnodes'])
                                 for h in sorted(deep, key=lambda h: -h['depth'])[:8]) if deep else '',
                '; %d kept as chain for memory' % len(for_memory) if for_memory else '',
                '; kept as chain, maintainer-accepted: %s' % ', '.join(
                    '%s (%s)' % (m, accepted[m]) for m in owner_stems) if owner_stems else ''),
            over_limit=len(deep), max_depth=max([h['depth'] for h in hulls] or [0]),
            over_limit_models=[{'name': h['name'], 'depth': h['depth'], 'clipnodes': h['clipnodes']}
                               for h in sorted(deep, key=lambda h: -h['depth'])],
            kept_as_chain_for_memory=sorted({_mesh_stem(h['name']) for h in for_memory} | kept_stems),
            kept_as_chain_owner_accepted=owner_stems,
            routed=len((receipt or {}).get('routed_hulls') or []))
        for_memory = for_memory + owner
        if not deep and (for_memory or kept_stems):
            # the tracker's KEPT_CHAIN_OUTCOME: passed, with meshes the heap fallback kept as chains for memory
            a['hull_bevels']['outcome'] = KEPT_CHAIN_OUTCOME
    put('hidden_faces', 'not_measured', 'no CHIM hidden-face audit yet (CHIM-HIDDEN-FACES-33)')
    put('sprite_shape', 'not_measured', 'flora converted as meshes; no sprites in a CHIMport cell')
    actors = sum(v['placed'] for t, v in records['by_type'].items() if t in ('NPC_', 'CREA', 'LEVC'))
    put('actor_grounding', 'not_measured', '%d actors deferred to the actor pipeline' % actors, actors=actors)
    doors = records['by_type'].get('DOOR', {})
    if doors:
        # DOOR records with a marker model (PrisonMarker, DivineMarker, TempleMarker: Marker_*.nif) are destinations
        # of the game's scripts, not doors anyone walks through; they stay deferred and are not missing door links
        # (CHIMPORT-DOOR-MARKER-AUDIT-36).
        # The converter names a marker placement by tools/editor_markers.py marker_status ("editor marker (not
        # drawn): <kind>") since the editor markers got their own module; the audit still looked only for the
        # earlier text, so a cell with a marker door read "failed" with every walkable door converted (seen on
        # Mournhold's Royal Palace courtyard, CHIMPORT-DOOR-MARKER-AUDIT-36 again). Both texts count.
        deferred = doors.get('deferred')
        markers = 0
        if isinstance(deferred, dict):
            from editor_markers import marker_status
            prefix = marker_status('')
            markers = sum(n for reason, n in deferred.items() if reason == MARKER_REASON or reason.startswith(prefix))
        walkable = doors['placed'] - markers
        ok = doors['converted'] == walkable
        put('door_links', 'passed' if ok else 'failed', '%d of %d doors converted%s' % (
            doors['converted'], walkable, '; %d marker doors deferred' % markers if markers else ''),
            converted=doors['converted'], placed=doors['placed'], markers=markers)
    else:
        put('door_links', 'not_measured', 'no doors in the cell')
    vis = (measured or {}).get('visibility') or {}
    if vis:
        put('vis', 'passed', 'visibility rows measured', **{k: v for k, v in vis.items() if isinstance(v, (int, float))})
    else:
        put('vis', 'not_measured', 'no visibility measurement')
    return a


def convert_cell(cell, data_files, palette, out, qbsp=None, unit_cache=None, jobs=1, missing_land='flat', abi_sizes=None,
                 frame=None, frame_name=None, shape=None, world_cells=None):
    """Build, audit and measure one cell. Writes OUT/result.json; returns it. Never raises for a cell problem.
    FRAME: the frame settings (default frame_settings(None, qbsp, shape), a build's; FRAME_NAME their set's name),
    recorded in the result with the cell shape, the switches and the palette (result['settings']). SHAPE region: the
    frame a build installs for the cell (CELL_SHAPES): its records and plan check count the owned cell only, and the
    neighbours' share is recorded apart (result['apron'], apron_figures). WORLD_CELLS (region): the cells with a frame
    of their own in the world the frame stands for (chim.build build_world frame_cells; None: the cell alone);
    the result names them and which of its eight neighbours were among them (result['world_frames'])."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    t0, c0 = time.time(), os.times()
    frame = dict(frame) if frame is not None else frame_settings(frame_name, qbsp, shape)
    result = {'format': CELL_FORMAT, 'cell': list(cell), 'key': ckey(cell), 'started': now_iso(), 'errors': [],
              'converted': False, 'settings': settings_record(frame, palette, frame_name, shape)}
    owned = tuple(cell) if (shape or CELL_SHAPE_DEFAULT) == 'region' else None
    settings = cell_settings(cell, missing_land, shape)
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
    if world_cells is not None:
        x, y = cell
        result['world_frames'] = {
            'cells': len(world_cells),
            'neighbours_with_a_frame': sorted([list(c) for c in world_cells if c != tuple(cell)
                                               and abs(c[0] - x) <= 1 and abs(c[1] - y) <= 1]),
            'note': 'measured with these neighbours as frames of the same world: a piece of theirs wholly outside '
                    'this frame is held by their frame, not here'}
    with cell_area(settings) as ident:
        from chim.build import build_areas
        receipt = stage('build', lambda: build_areas([ident], data_files, out, palette, qbsp, jobs, dict(frame), True, (),
                                                     True, unit_cache, None, None, None, [],
                                                     frame_cells=None if world_cells is None else list(world_cells)))
    work = out / 'work' / settings['town']['id']
    source = read_json(out / 'chim-source.json')
    chim_refs = {int(p['ref']) for s in (source or {}).get('frames', []) for p in s.get('placements', [])}
    records = record_accounting(work, source, chim_refs, owned)
    result['records'] = records
    result['source'] = source_facts(work, owned)
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
    if owned is not None:
        # the neighbours' share of the frame as its own numbers (the frame's memory and faces are the whole frame's)
        result['apron'] = stage('apron', lambda: apron_figures(work, world, owned, chim_refs))
        for problem in (result['apron'] or {}).get('problems') or []:
            result['errors'].append({'stage': 'apron', 'mechanism': APRON_INCOMPLETE, 'message': problem})
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
    """passed | empty | ocean | hull_pending | failed | not_converted. hull_pending = failing only POLICY_PENDING audits. empty = converted, nothing placed in the cell (terrain and water
    only), no error and no failed audit: counted apart so empty sea cells do not inflate "passed". ocean = a cell
    without LAND, written as a reference to the shared ocean chunk (`chimport.py ocean`), no error, no failed audit."""
    if not res.get('converted'):
        return 'not_converted'
    failed = {m for m, a in (res.get('audits') or {}).items() if a['status'] == 'failed'}
    if res.get('ocean'):
        return 'failed' if res.get('errors') or failed else OCEAN_STATUS
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
        with generated_frames(settings_list):
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
                heap=True, pool=None, link=False, frame=None, frame_name=None, shape=None):
    """One CHIM world holding every converted cell so far (a frame per cell, every unit from the run's shared
    cache: stored once), then the world audits on the whole of it: format validation, the streaming walk
    (measure), the heap rings and the stats. Each cell's source stage is reused from its cell folder (linked).
    Writes RUN/world/NAME/ (world.json: what it holds and what the audits found). FRAME, SHAPE: as convert_cell."""
    out = run_dir / 'world' / name
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    frame = dict(frame) if frame is not None else frame_settings(frame_name, qbsp, shape)
    settings = [cell_settings((r['x'], r['y']), missing_land, shape) for r in rows]
    work = out / 'work'
    work.mkdir(exist_ok=True)
    for r, s in zip(rows, settings):
        link = work / s['town']['id']
        target = run_dir / 'cells' / cell_dir((r['x'], r['y'])) / 'work' / s['town']['id']
        if not link.exists() and target.is_dir():
            link.symlink_to(target, target_is_directory=True)
    report = {'format': 'aw-chimport-world-1', 'name': name, 'cells': [ckey((r['x'], r['y'])) for r in rows],
              'started': now_iso(), 'errors': [], 'settings': settings_record(frame, palette, frame_name, shape)}

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
        receipt = step('build', lambda: build_areas(ids, data_files, out, palette, qbsp, jobs, dict(frame),
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
                        'AMIWIND_PROFILE_INTERVAL', 'AMIWIND_STAGE_TRACE', 'AMIWIND_BUILD_BUDGET',
                        # the selected layers: keyed per cell by what they change there (layer_touch), never whole
                        'AMIWIND_MASTERS',
                        # who runs the cell, never what its bytes are: the master builder's request id, each request
                        # its own (CHIMPORT-CELL-KEY-REQUEST-ID-67: no cell of one request was linked by the next), and
                        # the builder's other run facts (RUN_ENV of the cache provenance records), as the build's stage
                        # keys leave them out (tools/build_cache.py IGNORED_ENV)
                        'AMIWIND_AW_REQUEST', 'AMIWIND_RUN_NAME', 'AMIWIND_RUN_COMMIT', 'AMIWIND_RUN_VERSION',
                        'AMIWIND_RUN_JOB', 'AMIWIND_RUN_TOOLS_SHA256', 'AMIWIND_RUN_CHIM_VERSION',
                        'AMIWIND_RUN_WORLD_FORMAT', 'AMIWIND_RUN_KIND'}
# The expansion layers' game files: never in a cell key as whole files; a cell keys what they change in it
# (layer_touch: its own and its neighbours' merged CELL and LAND records, the records of the objects placed there
# and the layer archives' copies of those objects' models). CHIMPORT-CELL-KEY-LAYERS-65.
LAYER_INPUT_FILES = frozenset(('tribunal.esm', 'tribunal.bsa', 'bloodmoon.esm', 'bloodmoon.bsa'))
LAYER_ARCHIVES = {'Tribunal.esm': 'Tribunal.bsa', 'Bloodmoon.esm': 'Bloodmoon.bsa'}
TOUCH_RADIUS = 1          # cell_settings source_radius: the frame reads its 3 x 3 cells
_TOUCH = {}
_CODE = {}


def _index_master(raw):
    """({(x, y): CELL payload}, {(x, y): LAND payload}, {object id: payload}) of one standalone master's bytes."""
    import struct
    from mwad.esm import records, subrecords
    cells, lands, objects = {}, {}, {}
    for tag, _flags, payload in records(raw):
        if tag == 'CELL':
            data = next((d for t, d in subrecords(payload) if t == 'DATA'), b'')
            if len(data) >= 12:
                bits, x, y = struct.unpack_from('<Iii', data)
                if not bits & 1:
                    cells[(x, y)] = payload
        elif tag == 'LAND':
            data = next((d for t, d in subrecords(payload) if t == 'INTV'), b'')
            if len(data) >= 8:
                lands[struct.unpack_from('<ii', data)] = payload
        elif tag not in ('TES3', 'DIAL', 'INFO', 'PGRD', 'LTEX'):
            name = next((d for t, d in subrecords(payload) if t == 'NAME'), None)
            if name is not None:
                objects[bytes(name).split(b'\0', 1)[0].decode('cp1252', 'replace').casefold()] = payload
    return cells, lands, objects


def _placed_ids(payload):
    """The object ids a CELL payload places (the NAME of every reference after its FRMR)."""
    from mwad.esm import subrecords
    out, inside = set(), False
    for tag, data in subrecords(payload):
        if tag == 'FRMR':
            inside = True
        elif tag == 'NAME' and inside:
            out.add(bytes(data).split(b'\0', 1)[0].decode('cp1252', 'replace').casefold())
    return out


def _model(payload):
    from mwad.esm import subrecords
    data = next((d for t, d in subrecords(payload) if t == 'MODL'), None)
    if data is None:
        return None
    path = bytes(data).split(b'\0', 1)[0].decode('cp1252', 'replace').replace('\\', '/').casefold()
    return path if path.startswith('meshes/') else 'meshes/' + path


def _touch_index(data_files, masters):
    key = (str(data_files), tuple(masters))
    if key not in _TOUCH:
        from mwad.masters import master_bytes
        from mwad.paths import child_ci
        base = _index_master(master_bytes(data_files, masters[:1]))
        merged = _index_master(master_bytes(data_files, masters))
        archives = {}
        for name in masters[1:]:
            try:
                path = child_ci(Path(data_files), LAYER_ARCHIVES[name])
            except (FileNotFoundError, ValueError, KeyError):
                continue
            if path.is_file():
                import hashlib
                from mwad.audit import BSA
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                for entry in BSA(path).entries:
                    archives[str(entry).replace('\\', '/').casefold()] = digest
        _TOUCH[key] = (base, merged, archives)
    return _TOUCH[key]


def layer_touch(cell, data_files, masters=None):
    """What the selected expansion layers change in CELL's frame, as a digest, or None when they change nothing
    there (then the cell's key is the base game's own key): its own and its neighbours' (TOUCH_RADIUS) merged CELL
    and LAND records against the base game's, the merged records of every object placed there against the base
    game's, and the layer archives holding a copy of one of those objects' models."""
    from mwad.masters import selected_masters
    from file_cache import digest_json
    import hashlib
    masters = selected_masters(masters)
    if len(masters) == 1:
        return None
    (b_cells, b_lands, b_objects), (m_cells, m_lands, m_objects), archives = _touch_index(data_files, masters)
    x, y = cell
    changed, ids = [], set()
    for dx in range(-TOUCH_RADIUS, TOUCH_RADIUS + 1):
        for dy in range(-TOUCH_RADIUS, TOUCH_RADIUS + 1):
            near = (x + dx, y + dy)
            for kind, base, merged in (('cell', b_cells, m_cells), ('land', b_lands, m_lands)):
                if base.get(near) != merged.get(near):
                    changed.append([kind, list(near), hashlib.sha256(merged.get(near) or b'').hexdigest()])
            if near in m_cells:
                ids |= _placed_ids(m_cells[near])
    for ident in sorted(ids):
        payload = m_objects.get(ident)
        if b_objects.get(ident) != payload:
            changed.append(['object', ident, hashlib.sha256(payload or b'').hexdigest()])
        model = _model(payload) if payload else None
        if model and model in archives:
            changed.append(['archive model', model, archives[model]])
    if not changed:
        return None
    return digest_json({'format': 'chimport-layer-touch-1', 'masters': list(masters), 'changed': changed})


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


def cell_key(cell, data_files, palette, qbsp=None, abi_sizes=None, missing_land='flat', frame=None, shape=None,
             world_cells=None, method_set=None):
    """(key, reason): the hash of exactly what a cell's outputs depend on - the cell, its shape (SHAPE, CELL_SHAPES),
    the frames of the world it stands for (WORLD_CELLS, a region frame: its neighbours' pieces outside it),
    and its frame settings (FRAME, default frame_settings(None, qbsp, shape)), the game inputs (input lock), the
    palette, the qbsp binary, the engine ABI sizes, the converter's code, the AMIWIND_* switches and the Python/numpy
    versions. (None, reason) when an input cannot be hashed."""
    import hashlib
    import shutil
    from file_cache import digest_json, sha256_file
    inputs = inputs_identity(data_files)
    if inputs is None:
        return None, 'no input lock: the game inputs of this cell are not hashed'
    # the layers' files are keyed per cell by what they change in it (CHIMPORT-CELL-KEY-LAYERS-65)
    inputs = [row for row in inputs if Path(row[0]).name.casefold() not in LAYER_INPUT_FILES]
    try:
        touch = layer_touch(tuple(cell), data_files)
    except (OSError, ValueError) as exc:
        return None, 'the layers of this cell cannot be read: %s' % exc
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
    parts = {'format': CELL_KEY_FORMAT, 'cell': list(cell), 'settings': cell_settings(cell, missing_land, shape),
             'frame': dict(frame) if frame is not None else frame_settings(None, qbsp, shape),
             'palette': hashlib.sha256(Path(palette).read_bytes()).hexdigest(), 'qbsp': q,
             'abi_sizes': abi_sizes, 'inputs': inputs, 'code': code_identity(),
             'env': {k: v for k, v in sorted(os.environ.items())
                     if k.startswith('AMIWIND_') and k not in CELL_KEY_IGNORED_ENV},
             'hashseed': os.environ.get('PYTHONHASHSEED'), 'python': sys.version, 'numpy': numpy_version}
    if touch:
        parts['layers'] = touch      # absent when the layers change nothing here: the base game's own key
    if (shape or CELL_SHAPE_DEFAULT) != CELL_SHAPE_DEFAULT:
        parts['shape'] = shape       # absent for the default shape: its keys as before
    if world_cells is not None:
        # every cell of the world: a neighbour's piece can lie in any cell its model reaches (a key may never
        # under-declare)
        parts['world_frames'] = sorted([list(c) for c in world_cells])
    if method_set is not None:
        # a mesh method set (config/mesh-method-sets.json): another conversion of its meshes; absent without one, so
        # every key is as before (its rows are in the code part, config/ being part of it)
        parts['mesh_method_set'] = method_set
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
                        abi_sizes=None, pool=None, origin=None, reuse_mode='copy', frame_name=None, shape=None,
                        world_cells=None, method_set=None):
    """convert_cell through the shared storage pool. POOL None: exactly convert_cell (after removing read-only shared
    links a pooled earlier attempt left in OUT). Otherwise records result['pool']: stored vs linked bytes, units
    reused / computed / failed, and whether the whole cell was linked from an earlier identical conversion.
    FRAME_NAME: the frame settings' set (FRAME_SETTING_SETS; None: the default, build); SHAPE: the cell shape
    (CELL_SHAPES; None: the default, cell); METHOD_SET: the mesh method set installed for the conversion
    (method_set_installed; None: none), in the cell key and the result's settings."""
    if method_set is not None:
        res = _convert_cell_pooled(cell, data_files, palette, out, qbsp, unit_cache, jobs, missing_land, abi_sizes,
                                   pool, origin, reuse_mode, frame_name, shape, world_cells, method_set)
        res.setdefault('settings', {})['mesh_method_set'] = method_set
        write_json(Path(out) / 'result.json', res)
        return res
    return _convert_cell_pooled(cell, data_files, palette, out, qbsp, unit_cache, jobs, missing_land, abi_sizes,
                                pool, origin, reuse_mode, frame_name, shape, world_cells)


def _convert_cell_pooled(cell, data_files, palette, out, qbsp=None, unit_cache=None, jobs=1, missing_land='flat',
                         abi_sizes=None, pool=None, origin=None, reuse_mode='copy', frame_name=None, shape=None,
                         world_cells=None, method_set=None):
    out = Path(out)
    # the default set and shape pass nothing on: the calls are the ones before (named sets and shapes only)
    named = {} if frame_name in (None, FRAME_SETTINGS_DEFAULT) else {'frame_name': frame_name}
    if shape not in (None, CELL_SHAPE_DEFAULT):
        named['shape'] = shape
    if world_cells is not None:
        named['world_cells'] = world_cells
    frame = frame_settings(frame_name, qbsp, shape)
    if pool is None:
        release_pooled(out)              # nothing to do in a folder a pooled run never wrote
        return convert_cell(cell, data_files, palette, out, qbsp, unit_cache, jobs, missing_land, abi_sizes, **named)
    import storage_pool
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    setting = storage_pool.setting(pool, origin or 'option', out, log=lambda line: print(line, flush=True))
    link = setting['links'] and reuse_mode in ('hardlink', 'pool')
    cells = CellPool(pool, link=link)
    key, why = cell_key(cell, data_files, palette, qbsp, abi_sizes, missing_land, frame, shape, world_cells,
                        method_set)
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
    res = convert_cell(cell, data_files, palette, out, qbsp, units, jobs, missing_land, abi_sizes, **named)
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


RETRY_RESULTS = ('failed', 'hull_pending', 'not_converted')   # recorded results --retry-failed runs again


def pending_rows(rows, state, retry_failed=False):
    """The rows still to run: never run, stopped, and with RETRY_FAILED also every cell whose last result is
    not usable (RETRY_RESULTS). A cell that converted without an error is 'done' in state.json even when an
    audit failed (memory fit, doors, hull chains), so the runner state alone never selects it again
    (CHIMPORT-RETRY-AUDIT-FAILED-36): the recorded result decides."""
    out = []
    for r in rows:
        entry = state['cells'].get(ckey((r['x'], r['y'])), {})
        s = entry.get('status')
        if s == 'done' and not (retry_failed and entry.get('result') in RETRY_RESULTS):
            continue
        if s == 'failed' and not retry_failed:
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
        apron = res.get('apron')
        if apron:
            # a region-shape cell: the records above are the owned cell's; the neighbours' copies are their own numbers
            for field in ('placements_read', 'placements_in_frame', 'chunks'):
                t['apron_' + field] = t.get('apron_' + field, 0) + (apron.get(field) or 0)
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
    for f in ('apron_placements_read', 'apron_placements_in_frame', 'apron_chunks'):
        if any(f in t for t in rings_tot.values()):        # region-shape cells only: the summary as before otherwise
            total[f] = sum(t.get(f, 0) for t in rings_tot.values())
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
    if (args.out / WORLD_CELLS_FILE).is_file() and getattr(args, 'cell_shape', None) == 'region':
        cmd += ['--world-cells', str(args.out / WORLD_CELLS_FILE)]
    return cmd + frame_arguments(args)


def frame_arguments(args):
    """--frame-settings, --cell-shape and --mesh-method-set for a cell or world process: only a set or shape other
    than the default (the default command line stays as it was)."""
    name = getattr(args, 'frame_settings', None)
    shape = getattr(args, 'cell_shape', None)
    method_set = getattr(args, 'mesh_method_set', None)
    return (['--frame-settings', name] if name not in (None, FRAME_SETTINGS_DEFAULT) else []) + \
        (['--cell-shape', shape] if shape not in (None, CELL_SHAPE_DEFAULT) else []) + \
        (['--mesh-method-set', method_set] if method_set else [])


@contextlib.contextmanager
def method_set_installed(name, out):
    """The mesh method set NAME (config/mesh-method-sets.json, chim.method_sets) installed in this cell or world
    process while it converts, its report written into OUT; yields the set's record for the results and the cell key
    ({'set', 'methods'}), or None without a set (nothing installed, every key as before)."""
    if not name:
        yield None
        return
    from chim import method_sets
    record, restore = method_sets.install(name, report=out)
    print('chimport: %s' % method_sets.line(record), flush=True)
    try:
        yield {'set': record['set'], 'methods': record['methods']}
    finally:
        restore()


def world_command(args, ring):
    return ([sys.executable, str(Path(__file__).resolve()), 'world', '--data-files', str(args.data_files),
             '--palette', str(args.palette), '--out', str(args.out), '--through-ring', str(ring), '--jobs', str(args.jobs)]
            + (['--qbsp', str(args.qbsp)] if args.qbsp else []) + pool_arguments(args, getattr(args, 'pool_dir', None))
            + frame_arguments(args))


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


def presented_data_folder(data_files, folder, masters=None):
    """The data folder a run reads: with expansions selected, the presented data folder FOLDER made from DATA_FILES
    (tools/presented_data.py: the merged master of the selected game files under the base file's name, the other
    selected masters header-only, everything else linked), so the plan, the input lock and every cell's build read
    the same merged master; with the base game alone DATA_FILES itself. (folder, receipt or None)."""
    from mwad.paths import resolve_data_files
    import presented_data
    folder, receipt = presented_data.make(resolve_data_files(data_files), folder, masters)
    if receipt is None:
        print('chimport: the base game alone: the data folder is read as it is', flush=True)
    else:
        print('chimport: presented data folder %s: masters %s, presented master SHA-256 %s, %d entries linked'
              % (folder, ','.join(receipt['masters']), receipt['presented_sha256'], len(receipt['linked'])),
              flush=True)
    return Path(folder), receipt


def run(args):
    run_dir = args.out
    if getattr(args, 'mesh_method_set', None):
        # an unknown set or a bad row stops the run before any cell starts (each cell process installs it)
        from chim import method_sets
        print('chimport: %s' % method_sets.line(method_sets.rows(args.mesh_method_set)[0]), flush=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    args.pool_dir, pool_origin = pool_choice(args)
    if getattr(args, 'presented_data', None):
        # the expansions' cells exist only in the merged master: every reader of the run reads it under the base
        # file's name (CHIMPORT-LAYER-CELL-EMPTY-67: the plain data folder gave flat empty cells)
        args.data_files, _ = presented_data_folder(args.data_files, args.presented_data)
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
    # what every cell converts with, recorded once for the run (each cell's result records its own too):
    # CHIMPORT-UNITS-NOT-SHARED-WITH-BUILD-68, CHIMPORT-HEAP-NOT-BUILD-FRAMES-68
    name = getattr(args, 'frame_settings', None) or FRAME_SETTINGS_DEFAULT
    shape = getattr(args, 'cell_shape', None) or CELL_SHAPE_DEFAULT
    state['settings'] = dict(settings_record(frame_settings(name, args.qbsp, shape), args.palette, name, shape),
                             explicit=(getattr(args, 'build_switches', None) or {}).get('explicit', []))
    print('chimport: cell shape %s; frame settings %s %s; switches %s%s' % (
        shape, name, json.dumps(state['settings']['frame'], sort_keys=True),
        ' '.join('%s=%s' % (k[len('AMIWIND_'):], v) for k, v in sorted(state['settings']['switches'].items()) if v),
        '; set by the caller: ' + ', '.join(state['settings']['explicit']) if state['settings']['explicit'] else ''),
        flush=True)
    if shape == 'region' and not args.dry_run:
        # the world each region frame stands for: this run's cells and the reference's finished cells
        # (chim.ownership.select_compiled_apron, CHIM-FRAME-EDGE-CLAMPS-OUTSIDE-TILES-68)
        cells = world_frame_cells([(r['x'], r['y']) for r in rows])
        write_json(run_dir / WORLD_CELLS_FILE, cells)
        state['world_frame_cells'] = {'cells': len(cells['cells']), 'run_cells': cells['run_cells'],
                                      'reference_sha256': cells['reference_sha256']}
        print('chimport: the world of the region frames holds %d cells (%d of this run, the rest finished in the '
              'reference)' % (len(cells['cells']), cells['run_cells']), flush=True)
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
                # a cell whose build read less than its plan holds fails (CHIMPORT-LAYER-CELL-EMPTY-67)
                check_against_plan(r, res)
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
    summary['settings'] = state.get('settings')
    write_json(run_dir / 'summary.json', summary)
    for _ in range(2):              # the last cells' feed: wait for a running feed, then feed what is left
        if feeder['proc'] is not None:
            feeder['proc'].wait()
        maybe_feed(force=True)
    if feeder['proc'] is not None:
        feeder['proc'].wait()
    return 0


# ------------------------------------------------------------------ the open sea: cells without LAND (K-OCEAN)

OCEAN_PLAN_FORMAT = 'aw-chimport-ocean-plan-1'
OCEAN_DIR = 'ocean'
OCEAN_MARGIN = 2                # cells of open sea around the island rectangle (the horizon ring)
OCEAN_NAMESPACE = 'chim-ocean'  # the shared ocean chunk's key in the storage pool's index
OCEAN_STATUS = 'ocean'
OCEAN_REF_NAME = 'ocean.json'


def parse_rect(text):
    """'X0,X1,Y0,Y1' (inclusive cell bounds) -> (x0, x1, y0, y1)."""
    parts = [int(v) for v in re.split(r'[\s,;]+', (text or '').strip()) if v]
    if len(parts) != 4 or parts[0] > parts[1] or parts[2] > parts[3]:
        raise ValueError('--rect takes X0,X1,Y0,Y1 with X0 <= X1 and Y0 <= Y1')
    return tuple(parts)


def master_lands(data_files, masters=None):
    """(base, others): the base master's LAND heights {(x, y): rows} (Morrowind.esm, mwad.audit.load_esm) and the
    cells that have a LAND record in any other master of the data folder (Tribunal, Bloodmoon: never open sea),
    plus the base master's exterior cells {(x, y): {name, region, refs}}. MASTERS: the masters merged into the base
    file (default AMIWIND_MASTERS); a presented data folder passes the base file alone, as its Morrowind.esm already
    is the merged master of the selected ones (tools/presented_data.py)."""
    from mwad.audit import load_esm
    from mwad.esm import is_deleted, records, subrecords
    from mwad.paths import child_ci, resolve_data_files
    from mwad.masters import master_path
    data = resolve_data_files(data_files)
    esm = load_esm(master_path(data, masters))
    base = {k: v['heights'] for k, v in esm['lands'].items()}
    others = set()
    for path in sorted(p for p in data.iterdir() if p.is_file() and p.suffix.casefold() == '.esm'
                       and p.name.casefold() != 'morrowind.esm'):
        for tag, flags, payload in records(path.read_bytes()):
            if tag != 'LAND':
                continue
            subs = list(subrecords(payload))
            s = dict(subs)
            if len(s.get('INTV', b'')) == 8 and not is_deleted(flags, subs):
                import struct
                others.add(struct.unpack('<ii', s['INTV']))
    cells = {k: {'name': c['name'], 'region': c['region'], 'refs': sum(1 for r in c['refs'] if not r.get('deleted'))}
             for k, c in esm['cells'].items()}
    return base, others, cells, esm['sha256']


def ocean_record_masters(data_files, masters=None):
    """{(x, y): (master, ...)}: the selected game masters (MASTERS, default AMIWIND_MASTERS; in load order) that hold
    a live exterior CELL record of the cell, each read from its own file in the original data folder. The merged
    master no longer says where a record came from, and a presented data folder holds the other masters header-only,
    so this reads the game's own files. A selected master missing from the folder is left out (the caller says what
    was read)."""
    import struct
    from mwad.esm import is_deleted, records, subrecords
    from mwad.masters import selected_masters
    from mwad.paths import child_ci, resolve_data_files
    try:
        data = resolve_data_files(data_files)
    except ValueError:
        data = Path(data_files)
    out = {}
    for name in selected_masters(masters):
        path = child_ci(data, name, required=False) if data.is_dir() else None
        if path is None or not path.is_file():
            continue
        for tag, flags, payload in records(path.read_bytes()):
            if tag != 'CELL':
                continue
            header = []
            for sub, body in subrecords(payload):       # the cell header ends at its DATA (refs follow)
                header.append((sub, body))
                if sub == 'DATA':
                    break
            body = dict(header).get('DATA', b'')
            if len(body) < 12 or is_deleted(flags, header, header_only=True):
                continue
            bits, x, y = struct.unpack_from('<Iii', body)
            if bits & 1:                                 # an interior
                continue
            held = out.setdefault((x, y), [])
            if name not in held:
                held.append(name)
    return {c: tuple(v) for c, v in out.items()}


def ocean_base_world_cells(root=None):
    """The cells of the base world's default cell list (config/chim-cells.json, format aw-chim-cells-1). An open-sea
    cell in it is a frame of the base world whatever master holds its record, so it is Vvardenfell's (the routing-row
    cell -6,26 has no record at all). Empty when the list cannot be read (the caller says how many it read)."""
    path = Path(root or ROOT) / 'config' / ('chim-cells' + '.json')
    try:
        doc = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return frozenset()
    out = set()
    for c in doc.get('cells') or ():
        x, y = c.split(',') if isinstance(c, str) else c
        out.add((int(x), int(y)))
    return frozenset(out)


def ocean_set(cell, holders=(), listed=()):
    """The master set an open-sea cell's map belongs to, for the tracker (tools/cell_progress.py ingest gives the cell
    the island of the nearest island cell of that set; TRACKER-OCEAN-CELL-ISLAND-BASE-ONLY-68):
    - a cell of the base world's cell list (LISTED): 'vvardenfell', whatever master holds its record (the base world
      builds it as one of its frames);
    - else the first master in load order that holds its CELL record (HOLDERS): Morrowind.esm 'vvardenfell',
      Tribunal.esm 'tribunal', Bloodmoon.esm 'bloodmoon' (a record in Bloodmoon.esm only: Solstheim's sea);
    - a cell with no record in any master: None, no set hint (the nearest island cell of any set)."""
    from mwad.esm import GAME_MASTERS
    if tuple(cell) in listed:
        return 'vvardenfell'
    names = {'morrowind.esm': 'vvardenfell', 'tribunal.esm': 'tribunal', 'bloodmoon.esm': 'bloodmoon'}
    held = {h.casefold() for h in holders or ()}
    for name in GAME_MASTERS:
        if name.casefold() in held:
            return names.get(name.casefold())
    return None


def ocean_left_out(cell, base_lands, other_lands, cells, planned):
    """Why CELL is not one of the open-sea plan's cells (chimport.py ocean --cells names only cells of the plan)."""
    cell = tuple(cell)
    if cell in base_lands:
        return 'it has a LAND record (land or seabed: a CHIMport cell of its own, chimport.py run)'
    if cell in other_lands:
        return 'it has a LAND record in another master of the data folder'
    refs = (cells.get(cell) or {}).get('refs')
    if refs:
        return ('it holds %d placed record(s) (a sea cell with content: a CHIMport cell of its own, or an ocean frame '
                'named in a cell list)' % refs)
    if cell in planned:
        return 'it is in the run\'s plan.json'
    return 'it lies outside the open-sea plan (beyond the rectangle and its margin, with no cell record)'


def plan_ocean(base_lands, other_lands=(), cells=None, rect=None, margin=OCEAN_MARGIN, planned=()):
    """The open-sea cells: every cell of the island rectangle (default: the bounding box of the base master's
    LAND cells) grown by MARGIN cells, without a LAND record in any master, without placed records and not in
    the CHIMport plan. Rows carry the seam check against LAND neighbours (chim.ocean.seam_steps)."""
    from chim.ocean import seam_steps
    cells = cells or {}
    if rect is None:
        if not base_lands:
            raise ValueError('No LAND cells: name the rectangle with --rect')
        xs = [c[0] for c in base_lands]
        ys = [c[1] for c in base_lands]
        rect = (min(xs), max(xs), min(ys), max(ys))
    x0, x1, y0, y1 = rect
    if margin < 0:
        raise ValueError('--margin must be 0 or more')
    planned = set(planned)
    skip = set(base_lands) | set(other_lands) | planned
    rows, kept = [], collections.Counter()
    grown = [(x, y) for y in range(y0 - margin, y1 + margin + 1) for x in range(x0 - margin, x1 + margin + 1)]
    # The base master's own exterior cells without LAND beyond the grown rectangle are map cells too (named sea cells
    # the legacy table drew with flat terrain, for example on Azura's Coast).
    in_grown = set(grown)
    beyond = sorted(c for c in cells if c not in in_grown)
    for c in grown + beyond:
        x, y = c
        info = cells.get(c) or {}
        if c in base_lands:
            kept['land'] += 1
            continue
        if c in other_lands:
            kept['other_master_land'] += 1
            continue
        if info.get('refs'):
            kept['records_without_land'] += 1
            continue
        if c in skip:
            kept['planned'] += 1
            continue
        inside = x0 <= x <= x1 and y0 <= y <= y1
        where = 'rect' if inside else ('margin' if c in in_grown else 'record')
        rows.append({'x': x, 'y': y, 'name': info.get('name') or '', 'region': info.get('region') or '',
                     'land': False, 'margin': not inside, 'where': where, 'record': c in cells,
                     'seam': seam_steps(c, base_lands)})
    return {'format': OCEAN_PLAN_FORMAT, 'generated': now_iso(), 'rect': list(rect), 'margin': margin,
            'rule': 'cells of the rectangle (+ margin) and every exterior cell record of the base master, without LAND '
                    'in any master, without placed records, not in plan.json: open sea, one reference each to the shared '
                    'ocean chunk',
            'map_cells': (x1 - x0 + 1 + 2 * margin) * (y1 - y0 + 1 + 2 * margin),
            'rect_cells': (x1 - x0 + 1) * (y1 - y0 + 1), 'left_out': dict(kept),
            'cells': rows, 'counts': {'ocean': len(rows), 'inside_rect': sum(1 for r in rows if not r['margin']),
                                      'margin': sum(1 for r in rows if r['where'] == 'margin'),
                                      'beyond': sum(1 for r in rows if r['where'] == 'record'),
                                      'seam_edges': sum(len(r['seam']['edges']) for r in rows),
                                      'seam_over': sum(1 for r in rows if r['seam']['over'])}}


def ocean_ground_textures(data_files, palette_bytes, near=None):
    """{'g0', '*water': miptex} as the builder makes them (import_town.ground_assets: material 0 = the default land
    texture, water from water00), through a one-material audit folder that is removed afterwards."""
    from build_scratch import scratch_dir
    from chim.build import wad_lumps
    from import_town import ground_assets
    from mwad.paths import resolve_data_files
    with scratch_dir(prefix='ocean-', near=near, keep_on_failure=False) as tmp:
        audit = Path(tmp)
        (audit / 'materials.json').write_bytes(b'{"0": {"id": "default", "texture": null}}\n')
        ground = wad_lumps(ground_assets(resolve_data_files(data_files), audit, palette_bytes))
    if near is not None:
        with contextlib.suppress(OSError):          # the run's own scratch root, when nothing else is in it
            (Path(near) / '.scratch').rmdir()
    return {k: v for k, v in ground.items() if k in ('g0', '*water')}


def ocean_cell_result(row, ref, chunk_audits, chunk_info, ref_bytes):
    """A CHIMport cell result (aw-chimport-cell-1) of an open-sea cell: the reference, the shared chunk's audits
    and the cell's own seam check; status 'ocean'."""
    from chim.ocean import SEAM_TOLERANCE
    seam = row['seam']
    audits = {m: {'status': 'not_measured', 'detail': 'open sea: nothing of this kind in the cell', 'numbers': {}}
              for m in MECHANISMS}
    audits.update(chunk_audits)
    if seam['edges'] or seam['corners']:
        audits['seam_tears'] = {
            'status': 'failed' if seam['over'] else 'passed',
            'detail': 'shared chunk tiles seamlessly; %d LAND edges, largest height step %.0f units (tolerance %d)%s'
                      % (len(seam['edges']), seam['max_step'], SEAM_TOLERANCE,
                         '; over it: ' + ', '.join(seam['over']) if seam['over'] else ''),
            'numbers': {'land_edges': len(seam['edges']), 'max_step': seam['max_step'], 'over': len(seam['over'])}}
    records = {'by_type': {}, 'totals': {'placed': 0, 'converted': 0, 'deferred': 0, 'failed': 0, 'skipped': 0}}
    stats = {'records': records['totals'], 'meshes': {'unique_in_cell': 0, 'new': 0, 'reused': 0},
             'faces': {'source_triangles': 0, 'stored': chunk_info.get('faces', 0) + chunk_info.get('water_faces', 0),
                       'placed': None, 'terrain': None},
             'textures': {'count': len(chunk_info.get('textures') or ()), 'bytes': chunk_info.get('texture_bytes')},
             'disk': {'files': 1, 'chim_bytes': ref_bytes, 'chunks': 64, 'legacy_region_bytes': None,
                      'shared_chunk_bytes': chunk_info.get('bytes')},
             'collision': {'models': 0, 'clipnodes': chunk_info.get('clipnodes'), 'max_hull_depth': 0, 'over_limit': 0},
             'memory': {}, 'vis': {}, 'ocean': {'chunk': ref['chunk']['sha256'], 'seam': seam}}
    res = {'format': CELL_FORMAT, 'cell': [row['x'], row['y']], 'key': ckey((row['x'], row['y'])), 'converted': True,
           'ocean': ref, 'errors': [], 'records': records, 'audits': audits, 'stats': stats, 'wall_s': 0.0,
           'cpu_s': 0.0, 'started': now_iso(), 'finished': now_iso(), 'stages': {}, 'units': None,
           'ring': None, 'order': None, 'name': row['name'], 'region': row['region'], 'land': False,
           'margin': row['margin']}
    if 'set' in row:
        # the master set of the cell's map (ocean_set) and the masters that hold its CELL record: the tracker feed
        # passes the set on (None = no record: no set hint); a row without it (an older plan) passes none
        res['set'] = row['set']
        res['record_masters'] = list(row.get('record_masters') or ())
    res['status'] = cell_status(res)
    return res


def ocean_chunk_audits(failures, figures, info):
    """Audit rows of the shared chunk, the same for every ocean cell that references it."""
    from chim.heap import POOL_SLOTS, engine_memory
    memory = engine_memory()
    budget = (memory['zone_kib'] - POOL_SLOTS * memory['pool_kib']) * 1024
    fmt = [f for f in failures if 'seam' not in f and 'cover' not in f]
    seam = [f for f in failures if 'seam' in f]
    cover = [f for f in failures if 'cover' in f]
    resident = info['chunk_bytes'] + info['texture_bytes']
    return {
        'format_validation': {'status': 'failed' if fmt else 'passed', 'numbers': {'failures': len(fmt)},
                              'detail': 'shared ocean chunk reads back (%d validator failures)' % len(fmt)},
        'seam_tears': {'status': 'failed' if seam else 'passed', 'numbers': {'failures': len(seam),
                                                                             'points': figures.get('hull_points', 0)},
                       'detail': 'shared chunk standing hull at its edges and its copies\' (%d failures)' % len(seam)},
        'far_terrain': {'status': 'failed' if cover else 'passed', 'numbers': {'failures': len(cover)},
                        'detail': 'every tile covered by seabed and water faces (%d failures)' % len(cover)},
        'memory_fit': {'status': 'passed' if resident <= budget else 'failed',
                       'numbers': {'resident_bytes': resident, 'budget_bytes': budget},
                       'detail': 'one shared chunk %d B + textures %d B resident for every ocean chunk in the ring '
                                 '(zone budget %d B)' % (info['chunk_bytes'], info['texture_bytes'], budget)},
        'hull_bevels': {'status': 'passed' if info['hull_chain_max'] < LEGACY_CHAIN_DEPTH else 'failed',
                        'numbers': {'max_depth': info['hull_chain_max'], 'clipnodes': info['clipnodes']},
                        'detail': 'seabed standing hull: longest chain %d' % info['hull_chain_max']},
    }


def ocean_chunk(run_dir, data_files, palette, pool=None, link=True):
    """The shared ocean chunk of this run: (path in RUN/ocean, sha256, info, pool record). Looked up by its content
    key in the storage pool (linked, never built again), else built, validated and stored once."""
    import hashlib
    from chim import ocean as O
    odir = run_dir / OCEAN_DIR
    odir.mkdir(parents=True, exist_ok=True)
    pal = Path(palette).read_bytes()
    ground = ocean_ground_textures(data_files, pal, run_dir)
    task = O.ocean_task()
    key = O.ocean_key(task, ground, pal)
    record = {'key': key, 'chunk': 'computed', 'stored_bytes': 0, 'linked_bytes': 0, 'stored_files': 0,
              'linked_files': 0, 'reused_bytes': 0, 'errors': []}
    meta_path = odir / 'ocean-chunk.json'
    index = None
    if pool is not None:
        import storage_pool
        from file_cache import FileCache
        index = FileCache(Path(pool), OCEAN_NAMESPACE, None, fallback=False)
        meta = index.lookup(key)
        info = ((meta or {}).get('facts') or {}).get('info')
        if meta is not None and info:
            target = odir / ('ocean-%s.cco' % meta['sha256'][:16])
            try:
                placed = storage_pool.place(Path(pool), meta['sha256'], target, link=link)
            except OSError as exc:
                placed = False
                record['errors'].append(str(exc))
            if placed:
                write_json(meta_path, {'key': key, 'sha256': meta['sha256'], 'info': info})
                record.update(chunk='reused', linked_bytes=target.stat().st_size, linked_files=1)
                return target, meta['sha256'], info, record
    data, info = O.build_ocean(ground, pal, task)        # one small unit: the pool keeps it, no run-local cache
    failures, figures = O.validate_ocean(data)
    info = dict(info, key=key, validation={'failures': failures, 'figures': figures})
    digest = hashlib.sha256(data).hexdigest()
    target = odir / ('ocean-%s.cco' % digest[:16])
    tmp = target.with_name(target.name + '.%d.tmp' % os.getpid())
    tmp.write_bytes(data)
    tmp.replace(target)
    write_json(meta_path, {'key': key, 'sha256': digest, 'info': info})
    if pool is not None and not failures:
        import storage_pool
        try:
            existed = storage_pool.object_path(Path(pool), digest).is_file()
            if storage_pool.put(Path(pool), target, digest)[0] == 'skipped':
                raise OSError('cannot be hard-linked with the pool')
            index.point(key, digest, len(data), {'info': info})
            record['linked_bytes' if existed else 'stored_bytes'] += len(data)
            record['linked_files' if existed else 'stored_files'] += 1
        except OSError as exc:
            record['errors'].append(str(exc))
    elif pool is None:
        record.update(stored_bytes=len(data), stored_files=1)
    return target, digest, info, record


def ocean(args):
    """chimport.py ocean: plan the open-sea cells, make (or link) the shared ocean chunk, write one reference and
    one result per cell, and feed the tracker. One writer per run folder (run.lock)."""
    run_dir = args.out
    run_dir.mkdir(parents=True, exist_ok=True)
    originals, masters = args.data_files, None
    if getattr(args, 'presented_data', None):
        # with expansions selected their cells exist only in the merged master: read the presented data folder as
        # `run` does (its Morrowind.esm IS the merged master of the selected ones, the others header-only)
        args.data_files, receipt = presented_data_folder(args.data_files, args.presented_data)
        if receipt is not None:
            masters = (receipt['masters'][0],)
    base, others, cells, esm_sha = master_lands(args.data_files, masters)
    plan = read_json(run_dir / 'plan.json') or {'cells': []}
    planned = {(r['x'], r['y']) for r in plan['cells']}
    doc = plan_ocean(base, others, cells, parse_rect(args.rect) if args.rect else None, args.margin, planned)
    doc['esm_sha256'] = esm_sha
    c = doc['counts']
    print('chimport ocean: rectangle x %d..%d, y %d..%d + margin %d = %d map cells; %d open-sea cells (%d inside the '
          'rectangle, %d in the margin, %d named cells beyond it); left out: %s; %d LAND edges, %d cells with a seam '
          'step over the tolerance'
          % (*doc['rect'], doc['margin'], doc['map_cells'], c['ocean'], c['inside_rect'], c['margin'], c['beyond'],
             ', '.join('%s %d' % kv for kv in sorted(doc['left_out'].items())) or 'none', c['seam_edges'],
             c['seam_over']), flush=True)
    # each cell's set: the master that holds its CELL record, read from the game's own files (the base world's listed
    # cells stay Vvardenfell's; no record, no set: TRACKER-OCEAN-CELL-ISLAND-BASE-ONLY-68)
    holders = ocean_record_masters(originals)
    listed = ocean_base_world_cells()
    for row in doc['cells']:
        cell = (row['x'], row['y'])
        row['record_masters'] = list(holders.get(cell, ()))
        row['set'] = ocean_set(cell, holders.get(cell, ()), listed)
    wanted = parse_cells(getattr(args, 'cells', None))
    if wanted:
        have = {(r['x'], r['y']): r for r in doc['cells']}
        refused = ['%s: %s' % (ckey(cell), ocean_left_out(cell, base, others, cells, planned))
                   for cell in wanted if cell not in have]
        if refused:
            print('chimport ocean: REFUSED: %d of the %d named cells are not open sea of the plan: %s'
                  % (len(refused), len(wanted), '; '.join(refused)), file=sys.stderr, flush=True)
            return 2
        doc['selection'] = {'cells': [ckey(cell) for cell in wanted], 'of': len(doc['cells'])}
        doc['cells'] = [have[cell] for cell in dict.fromkeys(wanted)]
    sets = collections.Counter(row['set'] or 'none' for row in doc['cells'])
    print('chimport ocean: %s%d cells; their set by the master of their CELL record: %s (%d record(s) read from %s; '
          '%d cells of the base world\'s list kept on Vvardenfell)'
          % ('named: ' if wanted else '', len(doc['cells']), ', '.join('%s %d' % kv for kv in sorted(sets.items())),
             len(holders), ', '.join(sorted({m for v in holders.values() for m in v})) or 'no master',
             sum(1 for row in doc['cells'] if (row['x'], row['y']) in listed)), flush=True)
    for row in doc['cells'] if wanted else ():
        print('  %d,%d: set %s; CELL record in %s; seam: %d LAND edge(s), largest step %.0f'
              % (row['x'], row['y'], row['set'] or 'none (the nearest island)',
                 ', '.join(row['record_masters']) or 'no master', len(row['seam']['edges']), row['seam']['max_step']),
              flush=True)
    if args.dry_run:
        return 0
    pool, origin = pool_choice(args)
    try:
        lock = RunLock(run_dir).__enter__()
    except RunLocked as exc:
        print(exc, file=sys.stderr, flush=True)
        return 3
    try:
        t0 = time.time()
        link = True
        if pool is not None:
            import storage_pool
            link = storage_pool.setting(pool, origin or 'option', run_dir,
                                        log=lambda line: print(line, flush=True))['links'] and args.reuse_mode != 'copy'
        path, digest, info, record = ocean_chunk(run_dir, args.data_files, args.palette, pool, link)
        validation = info.get('validation') or {}
        if validation.get('failures'):
            print('chimport ocean: the shared chunk FAILS its checks: %s' % '; '.join(validation['failures'][:10]),
                  file=sys.stderr, flush=True)
            return 4
        chunk_audits = ocean_chunk_audits(validation.get('failures') or [], validation.get('figures') or {}, info)
        size = path.stat().st_size
        print('chimport ocean: shared chunk %s (%d B, %s; %d faces, %d water faces, %d clipnodes)'
              % (path.name, size, record['chunk'], info['faces'], info['water_faces'], info['clipnodes']), flush=True)
        write_json(run_dir / OCEAN_DIR / 'plan.json', doc)
        from chim.ocean import dumps, reference
        written = 0
        for row in doc['cells']:
            cdir = run_dir / 'cells' / cell_dir((row['x'], row['y']))
            ref = reference((row['x'], row['y']), digest, size, info)
            text = dumps(ref).encode('utf-8')
            cdir.mkdir(parents=True, exist_ok=True)
            tmp = cdir / (OCEAN_REF_NAME + '.%d.tmp' % os.getpid())
            tmp.write_bytes(text)
            tmp.replace(cdir / OCEAN_REF_NAME)
            res = ocean_cell_result(row, ref, chunk_audits, info, len(text))
            res['pool'] = {'cell': 'reference', 'stored_bytes': len(text), 'stored_files': 1}
            write_json(cdir / 'result.json', res)
            record['stored_bytes'] += len(text)
            record['stored_files'] += 1
            written += 1
        summary = {'format': 'aw-chimport-ocean-summary-1', 'finished': now_iso(), 'cells': written,
                   'chunk': {'file': path.name, 'sha256': digest, 'bytes': size, 'key': info.get('key')},
                   'pool': dict(record, dir=str(pool) if pool else None), 'wall_s': round(time.time() - t0, 2),
                   'seam': {'edges': c['seam_edges'], 'cells_over': c['seam_over']}}
        write_json(run_dir / OCEAN_DIR / 'summary.json', summary)
        print('chimport ocean: %d cells written as references; storage pool: stored %d B (%d files), linked %d B (%d '
              'files)' % (written, record['stored_bytes'], record['stored_files'], record['linked_bytes'],
                          record['linked_files']), flush=True)
    finally:
        lock.__exit__(None, None, None)
    if args.tracker and args.tracker_tool:
        return feed_tracker(run_dir, args.tracker, args.tracker_tool, args.tracker_ingest)
    return 0


def ocean_rows(run_dir):
    """The ocean plan's rows (RUN/ocean/plan.json), shaped like plan rows for the feed."""
    doc = read_json(Path(run_dir) / OCEAN_DIR / 'plan.json') or {'cells': []}
    return [dict(r, ring=None, order=None, refs=0, categories={}) for r in doc['cells']]


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
    if res.get('apron'):
        # a region-shape cell: the records are the owned cell's; what its neighbours put in the frame stands apart
        stats['apron'] = {k: res['apron'].get(k) for k in ('placements_read', 'placements_in_frame', 'chunks',
                                                         'owned_chunks')}
    audits = {m: dict({'status': a['status'], 'detail': a.get('detail'), 'numbers': a.get('numbers') or {}},
                      **({'outcome': a['outcome']} if a.get('outcome') else {}))
              for m, a in (res.get('audits') or {}).items() if m in TRACKER_MECHANISMS}
    if cell_status(res) == 'hull_pending':
        # not a failure while the hull-chain rule is being settled: shown apart, never red
        for m in POLICY_PENDING:
            if m in audits and audits[m]['status'] == 'failed':
                audits[m] = dict(audits[m], status='not_measured',
                                 detail='hull policy pending: ' + (audits[m]['detail'] or ''), policy_pending=True)
    extra = {}
    if cell_status(res) == OCEAN_STATUS:
        # open sea (no LAND): a reference to the shared ocean chunk; its own tracker status, counted as done
        extra = {'ocean': True, 'margin': bool((plan_row or {}).get('margin'))}
        if 'set' in res:
            # 'set': the master set whose map the sea belongs to, from the master that holds the cell's record
            # (chimport.py ocean, ocean_set); None for a cell without one, the nearest island of any set. It was
            # 'vvardenfell' for every ocean cell, so Solstheim's open sea got Vvardenfell's island
            # (TRACKER-OCEAN-CELL-ISLAND-BASE-ONLY-68); a result written before it carries none and names no set
            extra['set'] = res['set']
    return {'converted': bool(res['converted']), 'status': cell_status(res), 'empty': cell_status(res) == 'empty',
            **extra,
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
    for r in ocean_rows(run_dir):          # open-sea cells (chimport.py ocean): references to the shared chunk
        rows.setdefault(ckey((r['x'], r['y'])), r)
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
                          'world_format': '%d.%d' % FORMAT_VERSION, 'run': run_dir.name,
                          # what the audits ran against (CHIMPORT-STATUS-STALE-41): a later build compares the
                          # converter hash with its own and says when the results predate its converter
                          'amiwind_version': (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
                          if (ROOT / 'VERSION').is_file() else None,
                          'converter_sha256': code_identity()},
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
    refused = entry_check.guard_imports(ROOT, log=print if a.cmd in ('run', 'ocean') else None)
    record = entry_check.check(ROOT, a.working_version, Path(a.out),
                               accept_mismatch=a.accept_version_mismatch or os.environ.get('AMIWIND_ACCEPT_VERSION_MISMATCH'))
    if a.cmd in ('run', 'ocean'):
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
    """The command line, with the stair walk off by default (BUILD-STAIR-WALK-OFF-46; an explicit
    AMIWIND_STAIR_WALK wins); the default is restored when it returns."""
    import stair_walk
    _own_search_path()      # stair_walk puts tools/ first, which would load tools/mwad.py as the package mwad
    before = stair_walk.DEFAULT_OFF
    stair_walk.DEFAULT_OFF = True
    # the converter switches _cli exports (export_build_switches) are this command's: restored when it returns, so a
    # caller in the same process (a test) keeps its own environment
    from chim.units import SWITCHES
    switches = {name: os.environ.get(name) for name in SWITCHES}
    try:
        return _cli(argv)
    finally:
        stair_walk.DEFAULT_OFF = before
        for name, value in switches.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _cli(argv=None):
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
        q.add_argument('--retry-failed', action='store_true', help='run failed cells again: runner failures and every cell whose last result is failed, '
                       'hull_pending or not_converted (audit failures included)')
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
        q.add_argument('--presented-data', type=Path, metavar='DIR',
                       help='with expansions selected (AMIWIND_MASTERS), make the presented data folder DIR from '
                            '--data-files (tools/presented_data.py: the merged master under the base file\'s name, the '
                            'other masters header-only, everything else linked) and read it instead; the base game '
                            'alone reads --data-files as it is')
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
    c.add_argument('--world-cells', type=Path,
                   help='with --cell-shape region: the cells of the world the frame stands for (the run writes '
                        'RUN/%s: its cells and the reference\'s finished cells); a neighbour\'s piece wholly outside '
                        'the frame is held by its own cell\'s frame when that cell is one of them' % WORLD_CELLS_FILE)
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
    o = sub.add_parser('ocean', help='open-sea cells (no LAND) of the island rectangle + a margin ring as references '
                       'to ONE shared ocean chunk; fed to the tracker as status "ocean"')
    o.add_argument('--data-files', type=Path, required=True)
    o.add_argument('--palette', type=Path, required=True)
    o.add_argument('--out', type=Path, required=True)
    o.add_argument('--rect', help='island rectangle X0,X1,Y0,Y1 in cells, inclusive (default: the bounding box of the '
                   'base master LAND cells)')
    o.add_argument('--margin', type=int, default=OCEAN_MARGIN,
                   help='cells of open sea around the rectangle for the horizon (default %d)' % OCEAN_MARGIN)
    o.add_argument('--dry-run', action='store_true', help='print the plan and its seam figures only')
    o.add_argument('--cells', help='only these cells of the open-sea plan, "x,y x,y ...": a named cell that is not '
                   'open sea of the plan (LAND, placed records, plan.json, beyond it) is refused with its reason and '
                   'nothing is written')
    o.add_argument('--presented-data', type=Path, metavar='DIR',
                   help='with expansions selected (AMIWIND_MASTERS), make the presented data folder DIR from '
                        '--data-files (tools/presented_data.py) and plan from it, as `run` does; the masters that hold '
                        'each cell\'s record (its set) are read from --data-files itself')
    o.add_argument('--tracker', type=Path, help='CHIM Progress Tracker folder to feed afterwards')
    o.add_argument('--tracker-tool', type=Path, help='the tracker ingester (tools/cell_progress.py)')
    o.add_argument('--tracker-ingest', default='', help='extra arguments of the tracker ingest, one string')
    add_pool_options(o)
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
        q.add_argument('--frame-settings', choices=sorted(FRAME_SETTING_SETS), default=FRAME_SETTINGS_DEFAULT,
                       help='the frame settings of a cell: build (default: those a default build\'s CHIM stage uses, '
                            'so the cell is stored and measured as a build stores it) or cell-v1 (the settings before '
                            'v0.0.68, for A/B)')
        q.add_argument('--cell-shape', choices=CELL_SHAPES, default=CELL_SHAPE_DEFAULT,
                       help='the shape of a cell\'s frame: cell (default: the cell alone, nothing of its neighbours) or '
                            'region (the frame a build installs for the cell, its neighbours\' placements and terrain '
                            'within the margin copied in; the records count the owned cell, the apron is named apart)')
        q.add_argument('--mesh-method-set', metavar='NAME',
                       help='the named set of config/mesh-method-sets.json for the meshes it lists (chim.method_sets; '
                            'unset: today\'s methods): installed in every cell and world process, part of each cell\'s '
                            'key, recorded in its result, method C\'s figures in CELL/mesh-method-set.json')
    for q in (r, c, w, o):
        q.add_argument('--working-version', type=Path, metavar='FILE',
                       help='working-version record for the entry check (default: AMIWIND_WORKING_VERSION, then '
                            'OUT/../WORKING_VERSION.json; tools/entry_check.py)')
        q.add_argument('--accept-version-mismatch', metavar='REASON',
                       help='convert although the source VERSION differs from the working version (say why)')
    a = ap.parse_args(argv)
    if getattr(a, 'cell_shape', None) == 'region' and getattr(a, 'missing_land', 'flat') != 'flat':
        ap.error('--cell-shape region is the frame a build installs, where a cell without land is flat ground: '
                 'not --missing-land %s' % a.missing_land)
    if a.cmd in ('run', 'cell', 'world', 'ocean'):
        refused = entry(a)
        if refused:
            print(refused, file=sys.stderr)
            return 2
        # the converter switches a default build exports, so every unit is keyed as a build keys it; the cell and
        # world processes a run starts inherit them (main restores the environment when it returns)
        a.build_switches = export_build_switches()
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
        world_cells = None
        if a.world_cells is not None:
            if a.cell_shape != 'region':
                ap.error('--world-cells needs --cell-shape region')
            world_cells = [tuple(c) for c in read_json(a.world_cells)['cells']]
        with method_set_installed(a.mesh_method_set, a.out) as method_set:
            named = {} if method_set is None else {'method_set': method_set}
            res = convert_cell_pooled((x, y), a.data_files, a.palette, a.out, a.qbsp, a.unit_cache, a.jobs,
                                      None if a.missing_land == 'refuse' else a.missing_land, sizes, pool, origin,
                                      a.reuse_mode, frame_name=a.frame_settings, shape=a.cell_shape,
                                      world_cells=world_cells, **named)
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
        with method_set_installed(a.mesh_method_set, a.out / 'world' / name):
            rep = build_world(a.out, a.data_files, a.palette, name, rows, a.qbsp, a.jobs,
                              read_json(a.abi_sizes) if a.abi_sizes else read_json(a.out / 'abi-sizes.json'),
                              heap=a.heap, pool=pool, link=link, frame_name=a.frame_settings, shape=a.cell_shape)
        print(json.dumps({'name': rep['name'], 'built': rep['built'], 'cells': len(rep['cells']), 'wall_s': rep['wall_s'],
                          'heap': rep.get('heap'), 'disk': rep.get('disk'),
                          'validation_failures': (rep.get('validation') or {}).get('failure_count'),
                          'errors': [e['mechanism'] for e in rep['errors']]}))
        return 0
    if a.cmd == 'ocean':
        return ocean(a)
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
