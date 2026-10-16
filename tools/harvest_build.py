#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Harvestable mushrooms, built by default (BUILD-HARVEST-NOT-BUILT-32).

Two halves, no private plan input:

- ``prepare`` (builder step ``harvest``): read the player's own master and
  archive, convert every exterior small-mushroom model once into a shared
  one-frame MDL against the palette the image step ends with, and record every
  original placement (identity, pose, bounds, model). Nothing map-specific.
- ``install`` (image step, on the final maps): derive the plan from the region
  directories the image actually ships (world/regions.awr, the Seyda Neen and
  Balmora sub-cell tables, the intro docks), write one AWH4 catalogue per map
  that covers plants, run the geometry gate on that final map (no baked
  mushroom left where a harvestable one is placed), and admit the map only when
  the repository heap check (tools/check_world_map_heap.py) passes with its
  catalogue. Maps that fail admission ship without harvest, and the receipt
  says which and why.

Settings are those the shipped catalogues were made with: at most 256 plants
per map (the runtime bound), interned root spans, per-map model registries.
Original data and generated files stay private.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
# src first: tools/mwad.py is the CLI, src/mwad the package.
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

SOURCE_FORMAT = 'AmiWind harvest source 1'
STAGING_FORMAT = 'AmiWind harvest staging 1'
PLAN_FORMAT = 'AmiWind external harvest plan 1'
SOURCE_RECEIPT = 'harvest-source.json'
MAX_PLANTS = 256
TEXTURE_SIZE = 32
NAME = re.compile(r'[a-z0-9_]{1,24}')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(raw):
    return dict(sha256=digest(raw), bytes=len(raw))


def runtime_limits(source=None):
    """The engine's harvest bounds (engine/aga/src/aw_harvest.h)."""
    text = Path(source or ROOT / 'engine/aga/src/aw_harvest.h').read_text(encoding='utf-8')
    limits = {}
    for name in ('PLANTS', 'MODELS', 'NODES', 'EDGES'):
        match = re.search(r'^\s*#define\s+AW_HARVEST_' + name + r'\s+(\d+)\s*$', text, re.M)
        if not match:
            raise ValueError('Cannot identify runtime harvest bound AW_HARVEST_' + name)
        limits[name.lower()] = int(match[1])
    if limits['plants'] != MAX_PLANTS:
        raise ValueError('Runtime plant bound differs from the harvest builder setting')
    return limits


def exterior_references(context):
    """Every exterior original small-mushroom placement, in master order."""
    from prepare_harvest import placement_source_key
    master_sha256 = context['full']['master_sha256']
    refs = [dict(r, source_key=placement_source_key(r, master_sha256))
            for r in context['full']['references'] if r['kind'] == 'small_mushroom']
    if not refs:
        raise ValueError('The master has no exterior small-mushroom placements')
    return refs


def _convert_model(task):
    """Worker: one shared MDL from the source packet (opens its own handle)."""
    from harvest_alias_mesh import convert
    packet, index, number, palette = task
    with open(packet, 'rb') as archive:
        raw, report = convert(archive, index, index['models'][number], palette)
    return number, raw, report


def registry_line(name, raw):
    scale = struct.unpack_from('<3f', raw, 8)
    lo = struct.unpack_from('<3f', raw, 20)
    hi = [lo[i] + scale[i] * 255 for i in range(3)]
    return name + ' ' + digest(raw) + ' ' + ' '.join(format(v, '.9g') for v in (*lo, *hi))


def prepare(data_files, scene_palette, out, *, jobs=None):
    """Builder step: shared models and placement source from the player's data."""
    from build_parallel import ordered_map
    from mwad.paths import child_ci, ensure_external, resolve_data_files
    from prepare_hand_catalog import runtime_palette
    from prepare_harvest import source_context, prepare_graph
    from prepare_harvest_alias import alias_angles, validate_references
    from prepare_scenery import export_refs
    data = resolve_data_files(data_files)
    out = ensure_external(out, 'harvest source')
    if out.exists():
        raise ValueError('Harvest output already exists: ' + str(out))
    master = child_ci(data, 'Morrowind.esm').read_bytes()
    context = source_context(master, max_plants=MAX_PLANTS, intern_root_spans=True)
    refs = exterior_references(context)
    # Every placement must be representable before anything is written: the
    # same graph checks as a catalogue (no scripts, ownership, restocking...).
    prepare_graph(dict(context, max_plants=len(refs)), refs,
                  lambda r: ({'model': '@0', 'representation': 'external_alias', 'scale': r['scale']},
                             [v * .25 for v in r['position']], alias_angles(r)))
    palette = runtime_palette(data, scene_palette)
    if len(palette) != 768:
        raise ValueError('Expected a 768-byte RGB palette')
    out.mkdir(parents=True)
    export_refs(data, out / 'source', refs, {}, [0, 0, 0], texture_size=TEXTURE_SIZE, jobs=jobs)
    index_raw = (out / 'source/scenery-index.json').read_bytes()
    index = json.loads(index_raw)
    if index['errors']:
        raise ValueError('Harvest model conversion failed: ' + json.dumps(index['errors']))
    packet = out / 'source/scenery.mwpak'
    with packet.open('rb') as archive:
        checked = validate_references(context, index, archive)
    if len(checked) != len(refs):
        raise ValueError('Harvest source packet lost placements')
    numbers = sorted({r['model_index'] for r in checked}, key=lambda n: index['models'][n]['source'])
    models = []
    tasks = [(str(packet), index, number, palette) for number in numbers]
    for number, raw, report in ordered_map(_convert_model, tasks, jobs):
        model = index['models'][number]
        name = 'progs/harvest/' + digest(raw)[:24] + '.mdl'
        if any(row['path'] == name for row in models):
            raise ValueError('Duplicate generated harvest model: ' + name)
        target = out / 'payload' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        models.append(dict(path=name, **pin(raw), source=model['source'], source_sha256=model['source_sha256'],
                           packet_model=number, registry=registry_line(name, raw), conversion=report))
    (out / 'palette.lmp').write_bytes(palette)
    receipt = dict(format=SOURCE_FORMAT,
                   settings=dict(max_plants=MAX_PLANTS, intern_root_spans=True, compact_models=True,
                                 texture_size=TEXTURE_SIZE),
                   master=pin(master), scene_palette_sha256=digest(Path(scene_palette).read_bytes()),
                   palette=pin(palette), index=pin(index_raw), packet=pin(packet.read_bytes()),
                   global_slots=len(context['indices']), global_catalogue_sha256=context['catalogue'],
                   placements=len(checked), models=models,
                   scope='Every exterior original small-mushroom placement; maps, catalogues, geometry '
                         'gate and heap admission are decided by the image step on its final maps')
    (out / SOURCE_RECEIPT).write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8', newline='\n')
    return receipt


# --- plan: maps and their coverage, from what the image ships -------------

def town_origin(town):
    """Local map origin (quarter-scale) of a fixed town's sub-cells."""
    if town == 'seyda':
        from prepare_quake import CENTRE
        return [CENTRE[0] * .25, CENTRE[1] * .25, 0.]
    from town_config import load_settings
    settings = load_settings(town)
    return [v * settings['scale'] for v in settings['centre']] + [0.]


def town_rows(table, prefix, origin):
    """Sub-cell rows (name, core, coverage) of an AWBR1 region table."""
    lines = Path(table).read_text(encoding='ascii').splitlines()
    if not lines or lines[0].split()[:1] != ['AWBR1'] or int(lines[0].split()[1]) != len(lines) - 1:
        raise ValueError('Invalid town region table: ' + str(table))
    rows = []
    for number, line in enumerate(lines[1:]):
        parts = line.split()
        if len(parts) != 9 or parts[0] != f'{prefix}{number:03d}':
            raise ValueError('Invalid town region row: ' + str(table))
        v = list(map(float, parts[1:]))
        rows.append(dict(name=parts[0], origin=list(origin), coverage=[v[4:6], v[6:8]]))
    return rows


def chim_regions(id1, chim_world):
    """{map name: row} of the CHIM world's region frames (chim.frame_map.region_frame_rows): the open-world maps
    the image replaces by CHIM frame maps. {} without a CHIM world or region frames."""
    if not chim_world:
        return {}
    from chim.frame_map import region_frame_rows
    return region_frame_rows(id1, chim_world)


def plan_rows(id1, native=(), regions=None):
    """Every exterior map the image ships, with its origin and coverage.

    The world maps come from world/regions.awr, the Seyda Neen and Balmora
    sub-cells from their region tables, the intro docks from its fixed route
    bounds. Only maps present in maps/ count, except the sub-cells of the towns
    in `native`: towns on CHIM made from the game data (tools/chim_town.py), which
    have a region table and no region maps. Their rows say chim=True; the engine
    loads their catalogues by region on the CHIM frame (aw_harvest_runtime.c
    AW_HarvestFollow). `regions` (chim_regions): the open-world maps a CHIM region
    frame replaces; their rows say chim=True with the frame's id, cells and origin
    (the frame map's coordinates), whether or not a legacy map was made, and a
    divided cell's alias rows are left out (the engine never loads them). The
    engine loads such a catalogue with the frame map of the same name
    (AW_HarvestBegin); the CHIM world leaves these plants out (chim.build
    harvest_numbers), so without it they are nowhere (HARVEST-CHIM-REGION-LOSS-41).
    Sorted by name.
    """
    id1 = Path(id1)
    regions = regions or {}
    aliases = {a for row in regions.values() for a in row['aliases']}
    rows = []
    directory = id1 / 'world/regions.awr'
    chim = set()
    if directory.is_file():
        from prepare_harvest_room import world_directory
        for r in world_directory(directory.read_bytes()):
            if r['town'] or r['name'] in aliases:
                continue
            region = regions.get(r['name'])
            if region is None:
                rows.append(dict(name=r['name'], origin=r['origin'], coverage=r['coverage']))
            else:
                rows.append(dict(name=r['name'], origin=list(region['origin']), coverage=r['coverage'],
                                 frame=region['frame'], cells=[list(c) for c in region['cells']]))
                chim.add(r['name'])
    from town_config import runtime_towns
    for town in runtime_towns()[:2]:  # the fixed towns: Seyda Neen and Balmora
        table = id1 / town['regions']
        if table.is_file():
            found = town_rows(table, town['prefix'], town_origin(town['id']))
            if town['id'] in native:
                chim.update(r['name'] for r in found)
            rows += found
    if (id1 / 'maps/intro_docks.bsp').is_file():
        from prepare_intro_docks import BOUNDS
        rows.append(dict(name='intro_docks', origin=town_origin('seyda'),
                         coverage=[[BOUNDS[0], BOUNDS[1]], [BOUNDS[2], BOUNDS[3]]]))
    names = [r['name'] for r in rows]
    if len(set(names)) != len(names) or not all(NAME.fullmatch(n) for n in names):
        raise ValueError('Duplicate or invalid harvest map names')
    for row in rows:
        values = row['origin'] + row['coverage'][0] + row['coverage'][1]
        if len(row['origin']) != 3 or not all(math.isfinite(v) for v in values) or any(
                row['coverage'][0][i] >= row['coverage'][1][i] for i in range(2)):
            raise ValueError('Invalid harvest map coverage: ' + row['name'])
    return sorted((dict(r, chim=True) if r['name'] in chim else r for r in rows
                   if r['name'] in chim or (id1 / 'maps' / (r['name'] + '.bsp')).is_file()), key=lambda r: r['name'])


def select(row, refs):
    """Placements whose transformed bounds touch the map's coverage."""
    ox, oy = row['origin'][0], row['origin'][1]
    (lx, ly), (hx, hy) = row['coverage']
    selected = []
    for ref in refs:
        (ax, ay, _), (bx, by, _) = ref['bounds']
        if bx * .25 - ox >= lx and by * .25 - oy >= ly and ax * .25 - ox <= hx and ay * .25 - oy <= hy:
            selected.append(ref)
    return selected


# --- geometry gate ----------------------------------------------------------

def _gate(task):
    """Worker: the geometry gate on one final map; returns an error or None."""
    import numpy as np
    from prepare_harvest_alias import reject_existing_geometry
    path, refs, origin = task
    try:
        reject_existing_geometry(Path(path).read_bytes(), refs, np.array(origin, dtype=float))
    except ValueError as error:
        return str(error)
    return None


def geometry_gate(maps, selections, jobs=None):
    """reject_existing_geometry on every candidate's final map, in parallel."""
    from build_parallel import ordered_map
    tasks = [(str(Path(maps) / (name + '.bsp')),
              [dict(number=r['number'], position=r['position']) for r in refs], origin)
             for name, (refs, origin) in sorted(selections.items())]
    failures = {}
    for (path, _, _), error in zip(tasks, ordered_map(_gate, tasks, jobs)):
        if error:
            failures[Path(path).stem] = error
    return failures


# --- heap admission -----------------------------------------------------------

def heap_admission(id1, names, sizes, jobs=None):
    """Repository heap check (parallel) per candidate map, its catalogue installed.

    Each map's harvest charge depends only on its own catalogue and models
    (tools/compact_harvest_heap.py), so one pass decides every map.
    """
    from build_jobs import resolve_jobs
    from check_world_map_heap import inspect_maps
    if not names:
        return {}
    report = inspect_maps(Path(id1) / 'maps', sizes, jobs=resolve_jobs(jobs), only=set(names))
    return {r['map'][:-4]: dict(gate=r['gate'], estimated_total_bytes=r['estimated_total_bytes'],
                                estimated_clearance_bytes=r['estimated_clearance_bytes'],
                                harvest=(r.get('harvest_external') or {}).get('conservative_game_heap_peak_bytes', 0),
                                harvest_allocator=r.get('additional_external_allocation_allowance_bytes', 0))
            for r in report['maps']}


# --- image step ------------------------------------------------------------------

def load_source(source):
    source = Path(source)
    receipt = json.loads((source / SOURCE_RECEIPT).read_text(encoding='utf-8'))
    if receipt.get('format') != SOURCE_FORMAT:
        raise ValueError('Unknown harvest source receipt')
    for row in receipt['models']:
        if not re.fullmatch(r'progs/harvest/[0-9a-f]{24}\.mdl', row['path']):
            raise ValueError('Invalid harvest model path: ' + row['path'])
        if pin((source / 'payload' / row['path']).read_bytes()) != {k: row[k] for k in ('sha256', 'bytes')}:
            raise ValueError('Harvest model differs from its source receipt: ' + row['path'])
    for label, path in (('index', 'source/scenery-index.json'), ('packet', 'source/scenery.mwpak'),
                        ('palette', 'palette.lmp')):
        if pin((source / path).read_bytes()) != {k: receipt[label][k] for k in ('sha256', 'bytes')}:
            raise ValueError('Harvest source file differs from its receipt: ' + path)
    return receipt


def source_placements(source, data_files):
    """The source receipt, the master's harvest context and every checked placement."""
    from mwad.paths import child_ci, resolve_data_files
    from prepare_harvest import source_context
    from prepare_harvest_alias import validate_references
    source = Path(source)
    receipt = load_source(source)
    master = child_ci(resolve_data_files(data_files), 'Morrowind.esm').read_bytes()
    if pin(master) != receipt['master']:
        raise ValueError('Harvest source was made from another master')
    settings = receipt['settings']
    context = source_context(master, max_plants=settings['max_plants'],
                             intern_root_spans=settings['intern_root_spans'])
    if (context['catalogue'], len(context['indices'])) != (receipt['global_catalogue_sha256'], receipt['global_slots']):
        raise ValueError('Global harvest placement index differs from the source receipt')
    index = json.loads((source / 'source/scenery-index.json').read_bytes())
    with (source / 'source/scenery.mwpak').open('rb') as archive:
        refs = validate_references(context, index, archive)
    return receipt, context, refs


def map_selections(id1, refs, native=(), regions=None):
    """(plan rows, {map: placements}) for every shipped exterior map with plants."""
    rows = plan_rows(id1, native, regions)
    return rows, {row['name']: selected for row in rows for selected in [select(row, refs)] if selected}


def _clear(task):
    """Worker: remove baked brush mushrooms bound to harvestable placements."""
    from player_hull import lumps
    from remove_harvest_geometry import remove_geometry
    path, refs, origin = task
    path = Path(path)
    raw = path.read_bytes()
    text = lumps(raw)[0].rstrip(b'\0').decode('cp1252')
    bound = set(re.findall(r'"aw_ref"\s+"([^"\n]*)"', text))
    targets = [r for r in refs if str(r['number']) in bound]
    if not targets:
        return path.stem, 0, None
    result, report = remove_geometry(raw, targets, origin)
    temporary = path.with_name(path.name + '.harvest-tmp')
    temporary.write_bytes(result)
    os.replace(temporary, path)
    return path.stem, len(targets), dict(source_sha256=report['source_sha256'], result_sha256=report['result_sha256'],
                                         removed=[str(r['number']) for r in targets])


def clear_baked(source, id1, work, *, data_files, jobs=None, native=(), chim_world=None):
    """Image step, before the final passes: remove baked harvestable mushrooms.

    Some converters (Balmora) bake every mushroom as a brush entity bound to its
    original reference. A harvestable plant must not also exist as baked geometry,
    so those exact entities are removed (tools/remove_harvest_geometry.py: exact
    original reference and pose, every surviving surface and hull verified).
    Runs before hidden-surface culling, compaction and the heap check.
    """
    from build_parallel import ordered_map
    id1, work = Path(id1), Path(work)
    _, _, refs = source_placements(source, data_files)
    regions = chim_regions(id1, chim_world)
    rows, selections = map_selections(id1, refs, native, **({'regions': regions} if regions else {}))
    origins = {row['name']: row['origin'] for row in rows}
    chim = {row['name'] for row in rows if row.get('chim')}  # no map: the CHIM world leaves them out
    tasks = [(str(id1 / 'maps' / (name + '.bsp')), selections[name], origins[name]) for name in sorted(selections)
             if name not in chim]
    cleared = {}
    for name, count, report in ordered_map(_clear, tasks, jobs):
        if count:
            cleared[name] = report
    work.mkdir(parents=True, exist_ok=True)
    receipt = dict(format='AmiWind harvest baked geometry removal 1', maps_checked=len(tasks),
                   maps_changed=len(cleared), placements_removed=sum(len(r['removed']) for r in cleared.values()),
                   maps=cleared, tool='tools/remove_harvest_geometry.py remove_geometry')
    (work / 'harvest-baked-removal.json').write_text(json.dumps(receipt, indent=2) + '\n',
                                                     encoding='utf-8', newline='\n')
    return receipt


def install(source, id1, work, *, data_files, sizes, jobs=None, native=(), chim_world=None):
    """Image step: catalogues for the final maps, geometry gate, heap admission.

    ``sizes`` are the target ABI sizes of the heap check
    (check_world_map_heap.compile_target_sizes). Writes the admitted catalogues
    and the models they use into ``id1`` and the plan and receipt into ``work``.
    A geometry gate failure stops the build, and so does a map whose baked
    mushrooms clear_baked removed but which the heap check then refuses, and a
    CHIM map (town sub-cell or region frame, chim_world) over the runtime bounds:
    the CHIM world leaves its plants out, so they would be lost.
    """
    import numpy as np
    from prepare_harvest import identity_key
    from prepare_harvest_alias import catalogue
    source, id1, work = Path(source), Path(id1), Path(work)
    receipt, context, refs = source_placements(source, data_files)
    settings = receipt['settings']
    palette = (id1 / 'gfx/palette.lmp').read_bytes()
    if digest(palette) != receipt['palette']['sha256']:
        raise ValueError('Harvest models were converted with another palette than this image; rebuild the '
                         'harvest step from the same scene (BUILD-HARVEST-NOT-BUILT-32)')
    if list(id1.glob('harvest-*.txt')) or (id1 / 'progs/harvest').exists():
        raise ValueError('The image stage already has harvest files')
    if sizes is None:
        raise ValueError('Harvest admission needs the target sizes of the heap check')
    removal_path = work / 'harvest-baked-removal.json'
    removal = json.loads(removal_path.read_text(encoding='utf-8')) if removal_path.is_file() else dict(maps={})
    models = {row['packet_model']: row for row in receipt['models']}
    order = {row['packet_model']: i for i, row in enumerate(receipt['models'])}
    limits = runtime_limits()
    regions = chim_regions(id1, chim_world)
    rows, found = map_selections(id1, refs, native, **({'regions': regions} if regions else {}))
    chim = {row['name'] for row in rows if row.get('chim')}
    candidates, selections, capacity = {}, {}, {}
    for row in rows:
        selected = found.get(row['name'])
        if not selected:
            continue
        used = sorted({r['model_index'] for r in selected}, key=order.__getitem__)
        if len(selected) > limits['plants'] or len(used) > limits['models']:
            capacity[row['name']] = dict(plants=len(selected), models=len(used))
            continue
        raw, _ = catalogue(context, selected, np.array(row['origin'], dtype=float),
                           {number: i for i, number in enumerate(used)}, [models[n]['registry'] for n in used])
        candidates[row['name']] = dict(row=row, raw=raw, plants=len(selected),
                                       models=[models[n]['path'] for n in used])
        selections[row['name']] = (selected, row['origin'])
    over = sorted(n for n in capacity if n in chim)
    if over:
        raise ValueError('Harvest: CHIM map(s) over the runtime catalogue bounds (%d plants, %d models): the CHIM world '
                         'leaves their plants out, so they would be lost: ' % (limits['plants'], limits['models']) +
                         '; '.join('%s: %d plants, %d models' % (n, capacity[n]['plants'], capacity[n]['models'])
                                   for n in over))
    # A CHIM town's sub-cells have no map: no baked mushroom to find (the CHIM world leaves the harvest
    # placements out, chim.build harvest_numbers) and no per-map heap check (the CHIM heap gate counts
    # the frame); the runtime capacity bounds above still apply.
    failures = geometry_gate(id1 / 'maps', {n: v for n, v in selections.items() if n not in chim}, jobs)
    if failures:
        raise ValueError('Harvest geometry gate failed (baked mushroom where a harvestable one is placed) on '
                         f'{len(failures)} map(s): ' + '; '.join(f'{n}: {e}' for n, e in sorted(failures.items())))
    # Stage every candidate, then admit by the heap check; failures are removed. A CHIM town's catalogues
    # take no part in the per-map heap check and are written after it: their frame map is written later in
    # the image step, so a catalogue staged before the check would have no map yet
    # (BUILD-HARVEST-NATIVE-TOWN-ORDER-36); every later check runs once the frame maps are there.
    for name, item in candidates.items():
        if name not in chim:
            (id1 / ('harvest-' + name + '.txt')).write_bytes(item['raw'])
        for path in item['models']:
            target = id1 / path
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / 'payload' / path, target)
    per_map = [n for n in candidates if n not in chim]
    heap = heap_admission(id1, per_map, sizes, jobs) if per_map else {}
    for name in candidates:
        if name in chim:
            (id1 / ('harvest-' + name + '.txt')).write_bytes(candidates[name]['raw'])
    heap.update({n: dict(gate='pass', estimated_clearance_bytes=None, estimated_total_bytes=None, harvest=None,
                         rule='CHIM frame: no per-map heap check') for n in candidates if n in chim})
    admitted = sorted(n for n in candidates if heap[n]['gate'] == 'pass')
    lost = sorted(set(removal['maps']) - set(admitted))
    if lost:
        raise ValueError('Harvest: baked mushrooms were removed from map(s) that cannot take a catalogue '
                         '(heap check or runtime capacity): ' + ', '.join(lost))
    for name in sorted(set(candidates) - set(admitted)):
        (id1 / ('harvest-' + name + '.txt')).unlink()
    used = sorted({path for name in admitted for path in candidates[name]['models']})
    for row in receipt['models']:
        if row['path'] not in used and (id1 / row['path']).exists():
            (id1 / row['path']).unlink()
    if not used and (id1 / 'progs/harvest').is_dir():
        (id1 / 'progs/harvest').rmdir()
    work.mkdir(parents=True, exist_ok=True)
    plan = dict(format=PLAN_FORMAT, max_plants=settings['max_plants'],
                intern_root_spans=settings['intern_root_spans'], compact_models=settings['compact_models'],
                global_catalogue_sha256=receipt['global_catalogue_sha256'], global_slots=receipt['global_slots'],
                inputs={k: receipt[k] for k in ('master', 'index', 'packet', 'palette')},
                maps=[dict(name=n, **(dict(path=None, chim=True, **({'frame': candidates[n]['row']['frame']}
                                                                    if 'frame' in candidates[n]['row'] else {}))
                                       if n in chim else
                                       dict(path=f'maps/{n}.bsp', **pin((id1 / 'maps' / (n + '.bsp')).read_bytes()))),
                           origin=candidates[n]['row']['origin'], coverage=candidates[n]['row']['coverage'],
                           keys=[identity_key(r['source_key']) for r in selections[n][0]])
                      for n in sorted(candidates)])
    (work / 'harvest-plan.json').write_text(json.dumps(plan, indent=2) + '\n', encoding='utf-8', newline='\n')
    families = {}
    for row in rows:
        family = 'world' if row['name'].startswith('vf') else row['name'] if row['name'] == 'intro_docks' else row['name'][:2]
        stats = families.setdefault(family, dict(maps=0, with_plants=0, admitted=0, plants=0))
        stats['maps'] += 1
        stats['with_plants'] += row['name'] in candidates or row['name'] in capacity
        stats['admitted'] += row['name'] in admitted
        stats['plants'] += candidates[row['name']]['plants'] if row['name'] in admitted else 0
    staging = dict(format=STAGING_FORMAT, source_sha256=digest((source / SOURCE_RECEIPT).read_bytes()),
                   palette_sha256=digest(palette), maps_considered=len(rows), candidates=len(candidates),
                   admitted=len(admitted), plants=sum(candidates[n]['plants'] for n in admitted),
                   models=len(used), families=families,
                   geometry_gate=dict(status='passed', maps=len(selections),
                                      check='reject_existing_geometry on every candidate final map'),
                   baked_removal=dict(maps=len(removal['maps']),
                                      placements=sum(len(r['removed']) for r in removal['maps'].values())),
                   heap_admission=dict(status='checked',
                                       rule='admitted when the repository heap check passes with the catalogue'),
                   not_admitted={n: dict(plants=candidates[n]['plants'], reason='heap check fails with the catalogue',
                                         **{k: heap[n][k] for k in ('estimated_total_bytes', 'estimated_clearance_bytes',
                                                                    'harvest')})
                                 for n in sorted(set(candidates) - set(admitted))},
                   over_runtime_capacity=capacity,
                   chim_region_catalogues={n: dict(frame=candidates[n]['row']['frame'], plants=candidates[n]['plants'],
                                                   **pin(candidates[n]['raw']))
                                           for n in admitted if 'frame' in candidates[n]['row']},
                   catalogues=[dict(map=n, path='harvest-' + n + '.txt', **pin(candidates[n]['raw']),
                                    plants=candidates[n]['plants'], models=len(candidates[n]['models']),
                                    heap_clearance_bytes=heap[n]['estimated_clearance_bytes'])
                               for n in admitted],
                   files=[dict(path=p, **pin((id1 / p).read_bytes())) for p in
                          sorted(['harvest-' + n + '.txt' for n in admitted] + used)],
                   plan=dict(path='harvest-plan.json', sha256=digest((work / 'harvest-plan.json').read_bytes())))
    (work / 'harvest-staging.json').write_text(json.dumps(staging, indent=2) + '\n', encoding='utf-8', newline='\n')
    return staging


COVERAGE_FORMAT = 'AmiWind harvest CHIM coverage 1'
COVERAGE_REPORT = 'harvest-chim-coverage.json'
CELL_UNITS = 8192.0     # one Morrowind exterior cell, game units


def chim_coverage(id1, chim_world, refs, rows, frame_maps=False):
    """Every harvestable plant the CHIM world leaves out is placed by the image (HARVEST-CHIM-REGION-LOSS-41).

    The CHIM world leaves every harvest placement out of its frames (chim.build harvest_numbers; its receipt lists
    them per frame, parity harvest_removed), because the image installs them as catalogues. So each such plant must
    be in the catalogue of a map the image ships (`rows`, plan_rows: legacy maps, CHIM town sub-cells, CHIM region
    frame maps), or inside a legacy map's coverage (that map keeps it, catalogued or baked; the entity tracker and
    the heap check judge it there). A plant inside a CHIM region frame's own cell must be in that frame map's
    catalogue: that map is what the engine loads there. frame_maps: also require the frame map of each such
    catalogue to be in id1/maps (the final payload). Returns the report; 'missing' names every plant left out
    (empty: passed)."""
    from entity_tracker import harvest_refs
    from map_files import frame_map_path
    id1 = Path(id1)
    receipt_path = Path(chim_world) / 'chim-receipt.json'
    parity = json.loads(receipt_path.read_text(encoding='utf-8')).get('parity') or {}
    removed = {}
    for frame, record in sorted(parity.items()):
        for number in record.get('harvest_removed') or ():
            removed.setdefault(int(number), []).append(frame)
    by_number = {r['number']: r for r in refs}
    catalogues = {}
    for row in rows:
        path = id1 / ('harvest-%s.txt' % row['name'])
        if path.is_file():
            catalogues[row['name']] = harvest_refs(path.read_bytes())
    catalogued = set().union(*catalogues.values()) if catalogues else set()
    legacy = [row for row in rows if not row.get('chim')]
    own = {tuple(c): row for row in rows if 'frame' in row for c in row['cells']}
    missing = []
    counts = dict(region_cell=0, catalogue=0, legacy_map=0)
    for number, frames in sorted(removed.items()):
        ref = by_number.get(number)
        if ref is None:
            missing.append(dict(ref=number, frames=frames, reason='not a placement of the harvest source'))
            continue
        cell = [int(math.floor(ref['position'][k] / CELL_UNITS)) for k in range(2)]
        region = own.get(tuple(cell))
        if region is not None:
            if number in catalogues.get(region['name'], ()):
                counts['region_cell'] += 1
            else:
                missing.append(dict(ref=number, cell=cell, frames=frames, map=region['name'], frame=region['frame'],
                                    reason="not in the catalogue of its own cell's CHIM region frame map"))
        elif number in catalogued:
            counts['catalogue'] += 1
        elif any(select(row, [ref]) for row in legacy):
            counts['legacy_map'] += 1
        else:
            missing.append(dict(ref=number, cell=cell, frames=frames,
                                reason='in no shipped catalogue and inside no legacy map'))
    without = []
    if frame_maps:
        without = sorted(row['name'] for row in rows if 'frame' in row and row['name'] in catalogues
                         and not frame_map_path(id1, row['name']).is_file())
    return dict(format=COVERAGE_FORMAT, chim_receipt_sha256=digest(receipt_path.read_bytes()),
                frames=len(parity), plants=len(removed), placed=counts,
                region_frame_catalogues=sum(1 for row in rows if 'frame' in row and row['name'] in catalogues),
                missing=missing, catalogues_without_frame_map=without,
                rule="every harvest placement the CHIM world leaves out is in a shipped catalogue (for a CHIM region "
                     "cell: its own cell's frame map catalogue) or inside a legacy map")


def require_chim_coverage(source, id1, work, *, data_files, chim_world, native=(), frame_maps=False,
                          report_name=COVERAGE_REPORT):
    """chim_coverage on the image's plan, written to work/<report_name>; a ValueError naming the plants
    (reference, cell, frame, map) when any is left out. None without a CHIM world."""
    if not chim_world or not (Path(chim_world) / 'chim-receipt.json').is_file():
        return None
    _, _, refs = source_placements(source, data_files)
    rows = plan_rows(id1, native, chim_regions(id1, chim_world))
    report = chim_coverage(id1, chim_world, refs, rows, frame_maps=frame_maps)
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    (work / report_name).write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    print('Harvest CHIM coverage%s: %d plants the CHIM world leaves out (%d frames): %d in their CHIM region frame '
          'map catalogue, %d in another shipped catalogue, %d inside a legacy map; left out: %d; catalogues without '
          'their frame map: %d.' % (' (final payload)' if frame_maps else '', report['plants'], report['frames'],
                                    report['placed']['region_cell'], report['placed']['catalogue'],
                                    report['placed']['legacy_map'], len(report['missing']),
                                    len(report['catalogues_without_frame_map'])), flush=True)
    problems = ['ref %s (cell %s, frame %s%s): %s' % (m['ref'], ','.join(map(str, m.get('cell') or ['?'])),
                                                     m.get('frame') or '/'.join(m['frames'][:3]),
                                                     ', map ' + m['map'] if m.get('map') else '', m['reason'])
                for m in report['missing']]
    problems += ['%s: catalogue without its CHIM region frame map' % n for n in report['catalogues_without_frame_map']]
    if problems:
        raise ValueError('Harvest CHIM coverage failed (HARVEST-CHIM-REGION-LOSS-41): %d plant(s) or catalogue(s) '
                         'left out; see %s: %s' % (len(problems), report_name, '; '.join(problems[:12])))
    return report


def native_towns(args):
    """Towns of the image's --chim-town outputs (tools/chim_town.py): on CHIM, no legacy region maps."""
    return [json.loads((Path(path) / 'entities.json').read_text(encoding='utf-8'))['town']
            for path in getattr(args, 'chim_town', None) or []]


def image_step(args, id1, work, *, jobs=None):
    """build_aga.py finalize_image hook: install, print and summarize for build.json."""
    if not getattr(args, 'harvest', None):
        print('[warning] No harvest source given: this image has no harvestable mushrooms '
              '(builder default is the harvest step; --no-harvest is for debugging only).', flush=True)
        return dict(status='not_requested')
    from check_world_map_heap import compile_target_sizes
    chim_world = getattr(args, 'chim_world', None)
    staging = install(args.harvest, id1, work, data_files=args.data_files,
                      sizes=compile_target_sizes(args.sdk)[0], jobs=jobs, native=native_towns(args),
                      chim_world=chim_world)
    print(f"Harvest: {staging['admitted']}/{staging['candidates']} maps with mushrooms admitted by the heap check, "
          f"{staging['plants']} plants, {staging['models']} shared models; not admitted: "
          f"{', '.join(staging['not_admitted']) or 'none'}.", flush=True)
    # Every placed plant must be pickable by the engine's pick rule (HARVEST-BITTERCOAST-29): replayed
    # offline on the final maps, before any disk is made.
    from harvest_pick_audit import audit as pick_audit, check as pick_check
    pick = pick_audit(id1, jobs, progress=None)
    (Path(work) / 'harvest-pick-audit.json').write_text(json.dumps(pick, indent=1) + '\n', encoding='utf-8',
                                                        newline='\n')
    failures = pick_check(pick)
    print(f"Harvest pick audit: {pick['plants']} plants in {pick['maps']} maps; cannot be picked: {len(failures)} "
          f"(earlier engine rule: {len(pick['unpickable_before'])}); no standing position in reach: "
          f"{len(pick['unreachable'])}; catalogues followed on CHIM maps: {len(pick['catalogues_without_map'])}.", flush=True)
    if failures:
        raise ValueError('Harvest pick audit: %d placed plants cannot be picked (%s); see harvest-pick-audit.json'
                         % (len(failures), ', '.join(map(str, failures[:10]))))
    # Fail fast, before the CHIM frame maps: every plant the CHIM world leaves out has a catalogue
    # (HARVEST-CHIM-REGION-LOSS-41); finalize_image runs it again on the final payload (frame_maps=True).
    coverage = require_chim_coverage(args.harvest, id1, work, data_files=args.data_files, chim_world=chim_world,
                                     native=native_towns(args))
    report = Path(work) / 'harvest-staging.json'
    return dict(status='installed', pick_audit={k: (len(pick[k]) if isinstance(pick[k], list) else pick[k]) for k in
                                                ('plants', 'maps', 'unpickable_before', 'unpickable_fixed', 'unreachable',
                                                 'catalogues_without_map')}, report=str(report.relative_to(Path(work).parent)), report_sha256=digest(report.read_bytes()),
                **{k: staging[k] for k in ('maps_considered', 'candidates', 'admitted', 'plants', 'models', 'families',
                                           'baked_removal', 'geometry_gate')},
                not_admitted=sorted(staging['not_admitted']), over_runtime_capacity=sorted(staging['over_runtime_capacity']),
                chim_region_catalogues=len(staging['chim_region_catalogues']),
                chim_coverage=None if coverage is None else dict(plants=coverage['plants'], placed=coverage['placed'],
                                                                 missing=len(coverage['missing'])))


def main(argv=None):
    from build_jobs import add_jobs, resolve_jobs
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare', help='Builder step: shared models and placement source')
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--palette', type=Path, required=True, help='Scene palette (intro-scene/id1/gfx/palette.lmp)')
    p.add_argument('--out', type=Path, required=True)
    add_jobs(p)
    args = parser.parse_args(argv)
    receipt = prepare(args.data_files, args.palette, args.out, jobs=resolve_jobs(args.jobs))
    print(f"Harvest source: {receipt['placements']} exterior placements, {len(receipt['models'])} shared models.",
          flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
