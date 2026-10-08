#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Estimate every map of a whole-world import from your own Morrowind files.

For each interior cell and each exterior town-converter region, estimate the
BSP sizes and the target heap a conversion would produce, and check them
against the engine's limits, without converting anything. Two scenarios:
'cur' (what the converters take today) and 'evr' (every placed object with a
mesh as geometry, NPCs and creatures as edicts).

What is computed and what is estimated:
- computed from your data: the census (cells, references, NPCs, creatures,
  lights, light styles, night lamps per 3x3 cells, static flames, edicts,
  inline models, coordinates) and, per mesh, the converter's own face, texture
  mapping, lightmap, node and clipnode counts and surface extents;
- estimated: map lumps (calibrated linear sums of those per-mesh counts plus
  terrain terms), heap (calibrated on check_world_map_heap), final BSP bytes
  and compile time. Coefficients: config/world-estimate-model.json, or your
  own from `estimate-calibrate`.

Usage (also via build_aga.py estimate / estimate-calibrate):
  world_estimate.py estimate --data-files DIR --out DIR [--scenario cur|evr|both]
      [--jobs N] [--texinfo-limit 32767|65535] [--sample-convert N --sdk SDK]
  world_estimate.py calibrate --data-files DIR --from OUT [OUT ...] --model-out FILE
See docs/WORLD_ESTIMATE.md.
"""
import argparse
import collections
import csv
import io
import json
import math
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import world_estimate_data as D  # noqa: E402
import world_estimate_model as M  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'config/world-estimate.json'
OUTPUT_FORMAT = 'aw-world-estimate-1'
SETS = (('Morrowind.esm', 'vvardenfell', 'i', 'w'), ('Tribunal.esm', 'tribunal', 'ti', 'b'),
        ('Bloodmoon.esm', 'bloodmoon', 'bi', 'b'))
SCENARIOS = {'cur': 'converters as they are today',
             'evr': 'every placed reference (items, activators, fine dressing as geometry; actors as edicts)'}
COLUMNS = ('map set space name mw_region frame core_cells cov_area_q2 land_frac_core refs_total buildable '
           'refs_STAT refs_DOOR refs_CONT refs_LIGH refs_ACTI refs_NPC_ refs_CREA refs_LEVC refs_LEVI refs_items '
           'load_doors npc creatures lights lights_animated styles lamps_3x3 coord_max').split()
LUMP_COLUMNS = ('faces', 'texinfo', 'nodes', 'clipnodes', 'marksurfaces', 'vertexes', 'edges', 'planes',
                'lighting_bytes', 'texture_bytes', 'entity_bytes', 'bsp_bytes', 'final_bytes', 'seconds')
for _s in ('cur', 'evr'):
    COLUMNS += [_s + '_' + k for k in ('refs_geometry', 'variants', 'textures', *LUMP_COLUMNS, 'inline_models',
                                       'heap_raw', 'heap', 'flames', 'edicts', 'known_extent', 'fallback_variants')]
GATE_NAMES = ('heap', 'faces', 'texinfo', 'texinfo_planned_65535', 'nodes', 'clipnodes', 'marksurfaces', 'vertexes',
              'edicts', 'inline_models', 'static_flames', 'lightstyles', 'lights_if_dynamic_dlights',
              'night_lamp_cache_3x3', 'coord_4096', 'surface_extent_256')
HEADLINE_GATES = ('heap', 'faces', 'texinfo', 'nodes', 'clipnodes', 'marksurfaces', 'vertexes', 'edicts',
                  'inline_models', 'static_flames', 'lightstyles', 'coord_4096', 'surface_extent_256',
                  'night_lamp_cache_3x3', 'terrain_ceiling')
for _s in ('cur', 'evr'):
    COLUMNS += [_s + '_ratio_' + g for g in GATE_NAMES] + [_s + k for k in ('_worst_ratio', '_fails', '_pass',
                                                                             '_sections_est')]
COLUMNS += ['core_refs_total', 'core_npc', 'core_creatures', 'core_lights', 'core_items']
# Added after the first private measurement; kept at the end so the earlier column order is a prefix.
EXTRA_GATES = ('terrain_ceiling',)
COLUMNS += ['terrain_max_q'] + [s + '_ratio_' + g for s in ('cur', 'evr') for g in EXTRA_GATES]
AT_RISK = 0.9   # validation bias: maps near a limit are under-predicted; treat 90 % as failing


# ---------------------------------------------------------------- limits

def _define(path, name):
    text = (ROOT / path).read_text(encoding='utf-8', errors='replace')
    m = re.search(r'^\s*#\s*define\s+' + name + r'\s+(\d+)', text, re.M)
    if not m:
        raise ValueError('Limit %s not found in %s' % (name, path))
    return int(m.group(1))


def engine_limits(texinfo_limit=32767):
    """Limits read from this repository's engine sources and converter settings."""
    from check_world_map_heap import heap_capacity, BASELINE_RESERVE_BYTES, SAFETY_HEADROOM_BYTES
    from town_config import load_settings
    if texinfo_limit not in (32767, 65535):
        raise ValueError('--texinfo-limit must be 32767 (signed loader index) or 65535 (planned unsigned)')
    budget = heap_capacity()[0]
    fixed = BASELINE_RESERVE_BYTES + SAFETY_HEADROOM_BYTES
    src = 'engine/aga/src/'
    limits = {
        'faces': _define(src + 'bspfile.h', 'MAX_MAP_FACES'),
        'marksurfaces': _define(src + 'bspfile.h', 'MAX_MAP_MARKSURFACES'),
        'texinfo': texinfo_limit, 'texinfo_planned': 65535,
        'nodes': _define(src + 'bspfile.h', 'MAX_MAP_NODES'),
        'clipnodes': 65520,        # model.c clipnode loader bound (16-bit child with contents codes)
        'vertexes': _define(src + 'bspfile.h', 'MAX_MAP_VERTS'),
        'surface_extent': 256,     # model.c CalcSurfaceExtents: extents > 256 stop the load
        'coord': 4096,             # MSG_WriteCoord sends 1/8-unit shorts (common.c): +-4096 units
        'max_edicts': _define(src + 'quakedef.h', 'MAX_EDICTS'),
        'max_static_entities': _define(src + 'client.h', 'MAX_STATIC_ENTITIES'),
        'max_dlights': _define(src + 'client.h', 'MAX_DLIGHTS'),
        'max_lightstyles': _define(src + 'quakedef.h', 'MAX_LIGHTSTYLES'),
        'inline_models': int(load_settings('balmora')['model_budget']),
        'static_flames': _define(src + 'aw_guard_torch.c', 'STATIC_FLAME_MAX'),
        'lamp_cache_3x3': _define(src + 'aw_lamps.c', 'LAMP_CACHE'),
        'heap_budget': budget, 'heap_fixed': fixed,
    }
    from import_town import TERRAIN_CEILING
    limits['terrain_ceiling'] = TERRAIN_CEILING   # town frame sky box top; higher ground leaks
    limits['heap_allowed_peak'] = budget - fixed
    return limits


def gates(limits):
    """(name, row value key, limit) per gate, in output order."""
    return [('heap', 'heap', limits['heap_budget']), ('faces', 'faces', limits['faces']),
            ('texinfo', 'texinfo', limits['texinfo']), ('texinfo_planned_65535', 'texinfo', limits['texinfo_planned']),
            ('nodes', 'nodes', limits['nodes']), ('clipnodes', 'clipnodes', limits['clipnodes']),
            ('marksurfaces', 'marksurfaces', limits['marksurfaces']), ('vertexes', 'vertexes', limits['vertexes']),
            ('edicts', 'edicts', limits['max_edicts']), ('inline_models', 'inline_models', limits['inline_models']),
            ('static_flames', 'flames', limits['static_flames']), ('lightstyles', 'styles', limits['max_lightstyles']),
            ('lights_if_dynamic_dlights', 'lights', limits['max_dlights']),
            ('night_lamp_cache_3x3', 'lamps_3x3', limits['lamp_cache_3x3']), ('coord_4096', 'coord_max', limits['coord']),
            ('surface_extent_256', 'known_extent', limits['surface_extent']),
            ('terrain_ceiling', 'terrain_max_q', limits['terrain_ceiling'])]


# ---------------------------------------------------------------- exclusions

def load_config(path=None):
    path = Path(path) if path else CONFIG
    config = json.loads(path.read_text(encoding='utf-8'))
    if config.get('format') != 'aw-world-estimate-config-1':
        raise ValueError('Unsupported world estimate configuration: ' + str(path))
    return config


def exclusion(config, masters, mode):
    """Interior cells left out of the estimate, {casefolded name: reason}.

    Default rule (IMPORT-TEST-CELLS-31): an interior cell a player cannot reach
    (no chain of load doors from an exterior cell or from a cell named by a
    script or dialogue result) is a development/test or unused cell, unless
    listed in include_cells. exclude_cells always applies. mode 'none' disables both."""
    out = {}
    if mode == 'none':
        return out
    rule = config.get('exclusion', {})
    include = {n.casefold() for n in rule.get('include_cells', [])}
    if mode == 'default' and rule.get('exclude_unreachable_interiors', True):
        reachable = D.reachable_interiors(masters)
        for m in masters.values():
            for c in m['cells']:
                key = c['name'].casefold()
                if c['interior'] and not c['deleted'] and key not in reachable and key not in include:
                    out[key] = 'unreachable: no door chain from the world or a script'
    for name in rule.get('exclude_cells', []):
        out[name.casefold()] = 'listed in exclude_cells'
    return out


# ---------------------------------------------------------------- per-map rows

_JOB = {}


def _frame_rows(frame):
    j = _JOB
    rows = []
    for f in D.exterior_frames(j['world'], [frame], j['settings'], j['cells']):
        rows.append(predict_row(f, j['model'], j['world'].meshes, j['ratios']))
    return rows


def predict_row(f, model, meshes, ratios):
    out = {k: v for k, v in f.items() if not k.endswith('_variants')}
    for scen in ('cur', 'evr'):
        p, s = M.predict(model, meshes, ratios, f, scen)
        out[scen] = {**{k: round(v) for k, v in p.items()}, 'n_var': s['n_var'], 'n_inst': s['n_inst'],
                     'src': s['src'], 'known_maxext': s['known_maxext']}
    return out


def feature_sets(masters, meshes, anchor, excluded):
    """Yield (set label, master, kind, payload) work items in output order."""
    base_int = {c['name'].casefold() for c in masters['Morrowind.esm']['cells'] if c['interior']}
    base_ext = {(c['x'], c['y']) for c in masters['Morrowind.esm']['cells'] if not c['interior']}
    for master, label, iprefix, eprefix in SETS:
        if master not in masters:
            continue
        world = D.World(masters, master, meshes)
        cells = world.cells
        if master != 'Morrowind.esm':
            cells = ([c for c in cells if c['interior'] and c['name'].casefold() not in base_int] +
                     [c for c in cells if not c['interior'] and (c['x'], c['y']) not in base_ext])
        interiors = [c for c in cells if c['interior'] and c['name'].casefold() not in excluded]
        frames = D.world_frames(world, eprefix, anchor, cells) if any(not c['interior'] for c in cells) else []
        yield label, iprefix, world, interiors, cells, frames


def build_rows(masters, meshes, model, anchor, excluded, jobs=1, progress=print):
    ratios = M.fallback_ratios(meshes)
    settings = D.region_settings()
    rows = []
    for label, iprefix, world, interiors, cells, frames in feature_sets(masters, meshes, anchor, excluded):
        t0 = time.monotonic()
        for f in D.interior_maps(world, iprefix, interiors):
            r = predict_row(f, model, meshes, ratios)
            r['set'] = label
            rows.append(r)
        _JOB.update(world=world, settings=settings, cells=cells, model=model, ratios=ratios)
        ext = []
        if jobs > 1 and frames:
            import multiprocessing as mp
            from concurrent.futures import ProcessPoolExecutor
            try:
                ctx = mp.get_context('fork')
            except ValueError:
                ctx = None
            if ctx is not None:
                with ProcessPoolExecutor(jobs, mp_context=ctx) as pool:
                    for chunk in pool.map(_frame_rows, frames, chunksize=1):
                        ext.extend(chunk)
            else:
                for fr in frames:
                    ext.extend(_frame_rows(fr))
        else:
            for fr in frames:
                ext.extend(_frame_rows(fr))
        for r in ext:
            r['set'] = label
        rows.extend(ext)
        _JOB.clear()
        progress('%s: %d interior maps, %d exterior regions on %d frames (%.0f s)' % (
            label, len(interiors), len(ext), len(frames), time.monotonic() - t0))
    return rows


def metrics_row(r, limits):
    bt = r['by_type']
    ext = r['space'] == 'exterior'
    row = {'map': r['map'], 'set': r['set'], 'space': r['space'],
           'name': r.get('cell') or ('exterior %d,%d %s' % (r['centre_cell'][0], r['centre_cell'][1], r['region'])),
           'mw_region': '' if ext else r.get('region'), 'frame': r.get('frame', ''),
           'core_cells': ' '.join(r.get('core_cells', [])), 'cov_area_q2': r.get('cov_area', ''),
           'land_frac_core': r.get('land_frac_core', ''), 'refs_total': r['refs_total'],
           'buildable': 'yes' if r['refs_total'] > 0 else 'no (sea only, no references)'}
    for t in ('STAT', 'DOOR', 'CONT', 'LIGH', 'ACTI', 'NPC_', 'CREA', 'LEVC', 'LEVI'):
        row['refs_' + t] = bt.get(t, 0)
    row.update(refs_items=r['items'], load_doors=r['load_doors'], npc=r['npc'], creatures=r['creatures'] + r['levc'],
               lights=r['lights'], lights_animated=r['lights_animated'], styles=len(r['styles']),
               lamps_3x3=r.get('lamps_3x3', 0) if ext else 0,
               coord_max=round(r.get('coord_max', 0.0), 1) if not ext else int(r.get('coord_max', 0)))
    if ext:
        for k in ('core_refs_total', 'core_npc', 'core_creatures', 'core_lights', 'core_items'):
            row[k] = r[k]
        row['terrain_max_q'] = '' if r.get('terrain_max_q') is None else r['terrain_max_q']
    ground = r['terrain_max_q'] if ext and r.get('terrain_max_q') is not None else 0
    for scen in ('cur', 'evr'):
        e = r[scen]
        pre = scen + '_'
        row[pre + 'refs_geometry'] = r[scen + '_refs']
        row[pre + 'variants'] = e['n_var']
        row[pre + 'textures'] = r[scen + '_textures']
        for k in LUMP_COLUMNS:
            row[pre + k] = e[k]
        row[pre + 'inline_models'] = max(0, e['models'] - 1)
        row[pre + 'heap_raw'] = e['heap_raw']
        row[pre + 'heap'] = e['heap_final']      # production runs the optimizer
        row[pre + 'flames'] = r[scen + '_flames']
        actors = (r['npc'] + r['creatures'] + r['levc']) if scen == 'evr' else 0
        row[pre + 'edicts'] = 2 + r[scen + '_refs'] + actors
        row[pre + 'known_extent'] = e['known_maxext']
        row[pre + 'fallback_variants'] = sum(v for k, v in e['src'].items() if k.startswith('fallback'))
    for scen in ('cur', 'evr'):
        worst = 0.0
        fails = []
        for g, key, lim in gates(limits):
            v = ground if key == 'terrain_max_q' else (row.get(scen + '_' + key, row.get(key, 0)) or 0)
            ratio = v / lim
            if g == 'surface_extent_256' and v <= lim:
                ratio = 0.0      # 256 is legal; only > 256 stops the engine
            ratio = max(ratio, 0.0)
            row[scen + '_ratio_' + g] = round(ratio, 4)
            if g in HEADLINE_GATES:
                worst = max(worst, ratio)
                if ratio > 1:
                    fails.append(g)
        row[scen + '_worst_ratio'] = round(worst, 4)
        row[scen + '_fails'] = ' '.join(fails)
        row[scen + '_pass'] = 'yes' if not fails else 'no'
        peak = max(0, row[scen + '_heap'] - limits['heap_fixed'])
        need = max(peak / limits['heap_allowed_peak'], row[scen + '_texinfo'] / limits['texinfo'],
                   row[scen + '_faces'] / limits['faces'], row[scen + '_clipnodes'] / limits['clipnodes'],
                   row[scen + '_edicts'] / limits['max_edicts'], row[scen + '_inline_models'] / limits['inline_models'],
                   row[scen + '_flames'] / limits['static_flames'], 1e-9)
        row[scen + '_sections_est'] = max(1, math.ceil(need))
    return row


def summarise(rows, limits, model):
    import numpy as np
    S = {}
    timing = model.get('timing', {})
    for label in ('vvardenfell', 'tribunal', 'bloodmoon'):
        allsub = [r for r in rows if r['set'] == label]
        sub = [r for r in allsub if r['buildable'] == 'yes']
        if not sub:
            continue
        d = {'sea_only_regions_skipped': len(allsub) - len(sub), 'maps': len(sub),
             'interiors': sum(r['space'] == 'interior' for r in sub),
             'exteriors': sum(r['space'] == 'exterior' for r in sub),
             'frames': len({r['frame'] for r in sub if r['frame']})}
        ex = [r for r in sub if r['space'] == 'exterior']
        for scen in ('cur', 'evr'):
            g = {}
            for gname, key, lim in gates(limits):
                ratios = np.array([r[scen + '_ratio_' + gname] for r in sub])
                over = ratios > 1
                g[gname] = {'fail': int(over.sum()),
                            'at_risk_0.9_1.0': None if gname == 'surface_extent_256' else int(((ratios > AT_RISK) & ~over).sum()),
                            'fail_interior': int(sum(1 for r, o in zip(sub, over) if o and r['space'] == 'interior')),
                            'fail_exterior': int(sum(1 for r, o in zip(sub, over) if o and r['space'] == 'exterior')),
                            'max_ratio': round(float(ratios.max()), 3),
                            'median_overrun_of_failing': round(float(np.median(ratios[over])), 3) if over.any() else None}
            d[scen] = {'gates': g, 'pass_all': sum(r[scen + '_pass'] == 'yes' for r in sub),
                       'fail_any': sum(r[scen + '_pass'] == 'no' for r in sub),
                       'under_90pct_of_every_limit': sum(r[scen + '_worst_ratio'] <= AT_RISK for r in sub),
                       'within_10pct_of_a_limit': sum(AT_RISK < r[scen + '_worst_ratio'] <= 1 for r in sub),
                       'sections_total': sum(r[scen + '_sections_est'] for r in sub),
                       'sum_faces': sum(r[scen + '_faces'] for r in sub),
                       'sum_bsp_bytes': sum(r[scen + '_bsp_bytes'] for r in sub),
                       'sum_final_bytes': sum(r[scen + '_final_bytes'] for r in sub),
                       'sum_seconds': sum(r[scen + '_seconds'] for r in sub),
                       'heap_median': float(np.median([r[scen + '_heap'] for r in sub])),
                       'fails_by_space': {sp: sum(1 for r in sub if r['space'] == sp and r[scen + '_pass'] == 'no')
                                          for sp in ('interior', 'exterior')}}
        d['refs_interior'] = sum(r['refs_total'] for r in sub if r['space'] == 'interior')
        d['refs_exterior_core'] = sum(r.get('core_refs_total', 0) for r in ex)
        for k, ck in (('npc', 'core_npc'), ('creatures', 'core_creatures'), ('lights', 'core_lights'),
                      ('items', 'core_items')):
            src = 'refs_items' if k == 'items' else k
            d[k] = sum(r[src] for r in sub if r['space'] == 'interior') + sum(r.get(ck, 0) for r in ex)
        finish = timing.get('finish_cpu_seconds', {})
        prep = timing.get('frame_prep_wall_seconds', 0.0)
        cpu = sum(r['evr_seconds'] + finish.get(r['space'], 0.0) for r in sub)
        d['time'] = {'cpu_seconds_evr': round(cpu), 'frame_prep_wall_s': round(d['frames'] * prep),
                     'wall_hours_8cpu': round((cpu / 8 + d['frames'] * prep) / 3600, 2),
                     'wall_hours_24cpu': round((cpu / 24 + d['frames'] * prep) / 3600, 2)}
        d['disk'] = {'raw_bsp_GB': round(d['evr']['sum_bsp_bytes'] / 1e9, 2),
                     'final_bsp_GB': round(d['evr']['sum_final_bytes'] / 1e9, 2),
                     'scratch_GB_incl_work_dirs': round(d['evr']['sum_bsp_bytes'] / 1e9 *
                                                        timing.get('scratch_bytes_per_raw_byte', 0.0), 1)}
        S[label] = d
    built = [r for r in rows if r['buildable'] == 'yes']
    keys = ('map', 'set', 'space', 'name', 'evr_heap', 'evr_faces', 'evr_texinfo', 'evr_clipnodes', 'evr_edicts',
            'evr_inline_models', 'evr_flames', 'evr_worst_ratio', 'evr_fails', 'evr_sections_est', 'npc', 'creatures',
            'refs_total')
    S['worst30'] = [{k: r[k] for k in keys} for r in sorted(built, key=lambda r: -r['evr_worst_ratio'])[:30]]
    S['worst30_heap'] = [{k: r[k] for k in ('map', 'set', 'space', 'name', 'evr_heap', 'cur_heap', 'evr_faces',
                                            'evr_texinfo', 'evr_fails')}
                         for r in sorted(built, key=lambda r: -r['evr_heap'])[:30]]
    return S


def write_csv(path, rows, columns):
    keys = list(columns)
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    buf = io.StringIO()
    w = csv.DictWriter(buf, keys, lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    Path(path).write_bytes(buf.getvalue().encode('utf-8'))


def write_json(path, value, indent=None):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes((json.dumps(value, indent=indent) + '\n').encode('utf-8'))


def town_labels(masters):
    """Exterior cell names covering at least two cells, with their cells, from your own data."""
    groups = collections.defaultdict(set)
    for name in ('Morrowind.esm', 'Bloodmoon.esm'):
        for c in masters.get(name, {}).get('cells', []):
            if not c['interior'] and c['name']:
                groups[c['name'].split(',')[0].strip()].add((c['x'], c['y']))
    return {k: sorted(v) for k, v in groups.items() if len(v) >= 2}


# ---------------------------------------------------------------- commands

def prepare_inputs(data_files, work, jobs, progress):
    from mwad.paths import resolve_data_files
    data = resolve_data_files(data_files)
    t0 = time.monotonic()
    masters = D.census(data)
    progress('census: %s (%.1f s)' % (', '.join('%s %d cells' % (k, len(v['cells'])) for k, v in masters.items()),
                                      time.monotonic() - t0))
    used = D.used_meshes(masters)
    meshes = D.scan_meshes(data, sorted(used), Path(work) / 'meshes.json', jobs=jobs, progress=progress)
    status = collections.Counter(m['status'] for m in meshes.values())
    progress('mesh scan: %d meshes %s (%.0f s)' % (len(meshes), dict(status), time.monotonic() - t0))
    return data, masters, meshes, used


def mesh_summary(meshes, used):
    status = collections.Counter(m['status'] for m in meshes.values())
    cost_errors = sum(1 for m in meshes.values() for c in (m.get('costs') or {}).values() if 'error' in c)
    return {'meshes': len(meshes), 'status': dict(status), 'cost_pass_failures': cost_errors,
            'placements_without_geometry': sum(used[k] for k, m in meshes.items() if m['status'] != 'ok')}


def estimate(args, progress=print):
    t_start = time.monotonic()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(args.work) if args.work else out / 'work'
    model = M.load_model(args.model)
    config = load_config(args.config)
    limits = engine_limits(args.texinfo_limit)
    jobs = args.jobs or 1
    data, masters, meshes, used = prepare_inputs(args.data_files, work, jobs, progress)
    excluded = exclusion(config, masters, args.exclude)
    anchor = tuple(args.frame_anchor) if args.frame_anchor else tuple(D.region_settings()['source_cell'])
    preds = build_rows(masters, meshes, model, anchor, set(excluded), jobs, progress)
    rows = [metrics_row(r, limits) for r in preds]
    if args.scenario != 'both':
        drop = 'evr' if args.scenario == 'cur' else 'cur'
        columns = [c for c in COLUMNS if not c.startswith(drop + '_')]
        rows = [{k: v for k, v in r.items() if not k.startswith(drop + '_')} for r in rows]
    else:
        columns = COLUMNS
    write_csv(out / 'metrics.csv', rows, columns)
    header = {'format': OUTPUT_FORMAT, 'limits': limits, 'gates': list(GATE_NAMES + EXTRA_GATES), 'headline_gates': list(HEADLINE_GATES),
              'scenarios': {k: v for k, v in SCENARIOS.items() if args.scenario in ('both', k)},
              'estimated_columns': ['*_faces', '*_texinfo', '*_nodes', '*_clipnodes', '*_marksurfaces', '*_vertexes',
                                    '*_edges', '*_planes', '*_lighting_bytes', '*_texture_bytes', '*_entity_bytes',
                                    '*_bsp_bytes', '*_final_bytes', '*_seconds', '*_heap_raw', '*_heap',
                                    '*_inline_models', '*_ratio_* of those', '*_sections_est'],
              'at_risk_ratio': AT_RISK, 'model': {'path': str(args.model or M.DEFAULT_MODEL),
                                                  'calibration': model.get('calibration', {}).get('source')}}
    write_json(out / 'metrics.json', {**header, 'rows': rows})
    summary = {'format': OUTPUT_FORMAT, 'limits': limits, 'texinfo_limit': args.texinfo_limit,
               'scenario': args.scenario, 'frame_anchor': list(anchor),
               'excluded_interiors': sorted(excluded.items()),
               'census': D.census_summary(masters), 'meshscan': mesh_summary(meshes, used)}
    if args.scenario == 'both':
        summary.update(summarise(rows, limits, model))
    write_json(out / 'summary.json', summary, 1)
    if args.scenario == 'both' and not args.no_charts:
        import world_estimate_charts as C
        cmp_path = out / 'validation/compare.json'
        written = C.write_charts(out / 'charts', rows, summary, limits, town_labels(masters),
                                 json.loads(cmp_path.read_text()) if cmp_path.is_file() else None)
        progress('charts: ' + ', '.join(written))
    if args.sample_convert:
        import world_estimate_sample as V
        V.run(args, data, masters, meshes, model, preds, rows, out, limits, progress)
        if args.scenario == 'both' and not args.no_charts:
            import world_estimate_charts as C
            C.write_charts(out / 'charts', rows, summary, limits, town_labels(masters),
                           json.loads((out / 'validation/compare.json').read_text()))
    built = [r for r in rows if r['buildable'] == 'yes']
    progress('estimate: %d maps (%d sea-only regions skipped), %d interiors excluded, %.0f s; results in %s' % (
        len(built), len(rows) - len(built), len(excluded), time.monotonic() - t_start, out))
    if args.scenario == 'both':
        for label in ('vvardenfell', 'tribunal', 'bloodmoon'):
            if label in summary:
                e = summary[label]['evr']
                progress('  %s evr: %d maps fail >= 1 limit, %d within 10 %%, %d under 90 %% of every limit' % (
                    label, e['fail_any'], e['within_10pct_of_a_limit'], e['under_90pct_of_every_limit']))
    return 0


def calibrate(args, progress=print):
    """Refit the coefficients from maps converted by --sample-convert runs."""
    pairs_in = []
    for d in args.from_dirs:
        res = Path(d) / 'validation/results.json'
        if not res.is_file():
            raise ValueError('No sample conversion results in ' + str(d))
        pairs_in.extend(json.loads(res.read_text(encoding='utf-8'))['measured'])
    work = Path(args.work) if args.work else Path(args.from_dirs[0]) / 'work'
    data, masters, meshes, used = prepare_inputs(args.data_files, work, args.jobs or 1, progress)
    import world_estimate_sample as V
    pairs = V.feature_pairs(masters, meshes, pairs_in)
    if len(pairs) < 6:
        raise ValueError('Calibration needs measured maps of both spaces (have %d)' % len(pairs))
    ratios = M.fallback_ratios(meshes)
    coeff = M.fit(pairs, meshes, ratios)
    cv, _ = M.cross_validate(pairs, meshes, ratios) if len(pairs) >= 15 else ({}, [])
    base = M.load_model(args.model)
    doc = M.model_document(coeff, {'source': 'estimate-calibrate on %d converted maps' % len(pairs),
                                   'maps': {sp: sum(f['space'] == sp for f, _ in pairs) for sp in M.SPACES},
                                   'cv_5fold_grouped': cv})
    doc['timing'] = base.get('timing', {})
    write_json(args.model_out, doc, 1)
    progress('calibrated model written: %s (%d maps)' % (args.model_out, len(pairs)))
    return 0


def add_estimate_options(p):
    p.add_argument('--data-files', type=Path, required=True, help='Your Morrowind installation root or Data Files')
    p.add_argument('--out', type=Path, required=True, help='Output directory (metrics.csv/.json, summary.json, charts/)')
    p.add_argument('--work', type=Path, help='Cache directory for the mesh scan (default: OUT/work)')
    p.add_argument('--scenario', choices=('cur', 'evr', 'both'), default='both',
                   help="cur: what the converters take today; evr: every placed object; both (default)")
    p.add_argument('--texinfo-limit', type=int, choices=(32767, 65535), default=32767,
                   help='Texinfo gate: 32767 (signed loader index, today) or 65535 (planned)')
    p.add_argument('--model', type=Path, help='Coefficient file (default config/world-estimate-model.json)')
    p.add_argument('--config', type=Path, help='Exclusion configuration (default config/world-estimate.json)')
    p.add_argument('--exclude', choices=('default', 'listed', 'none'), default='default',
                   help='default: unreachable interiors and exclude_cells; listed: exclude_cells only; none')
    p.add_argument('--frame-anchor', type=int, nargs=2, metavar=('CX', 'CY'),
                   help='Centre cell of one exterior frame (default: the Balmora source cell)')
    p.add_argument('--sample-convert', type=int, default=0, metavar='N',
                   help='Also convert N stratified maps with the repository converters and report the error')
    p.add_argument('--sdk', type=Path, help='Amiga SDK for the heap of --sample-convert maps (check_world_map_heap)')
    p.add_argument('--quake-tools', type=Path, help='ericw-tools bin directory (qbsp, vis, light) for --sample-convert')
    p.add_argument('--palette', type=Path, help='palette.lmp for --sample-convert (default: a generated palette)')
    p.add_argument('--no-charts', action='store_true')
    p.add_argument('--jobs', type=int, default=0, help='Worker processes (default: all CPUs)')


def add_calibrate_options(p):
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--from', dest='from_dirs', type=Path, nargs='+', required=True,
                   help='Output directories of estimate runs with --sample-convert')
    p.add_argument('--model-out', type=Path, required=True, help='Where to write the refitted coefficient file')
    p.add_argument('--model', type=Path, help='Model whose timing constants are kept (default: shipped model)')
    p.add_argument('--work', type=Path, help='Mesh scan cache (default: first --from directory /work)')
    p.add_argument('--jobs', type=int, default=0)


def resolve(args):
    if getattr(args, 'jobs', None) == 0:
        from build_jobs import resolve_jobs
        args.jobs = resolve_jobs(None)
    return args


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='action', required=True)
    add_estimate_options(sub.add_parser('estimate', help='Estimate every map'))
    add_calibrate_options(sub.add_parser('calibrate', help='Refit coefficients from converted sample maps'))
    args = resolve(p.parse_args(argv))
    try:
        return (estimate if args.action == 'estimate' else calibrate)(args)
    except (OSError, ValueError) as exc:
        p.exit(1, 'Error: %s\n' % exc)


if __name__ == '__main__':
    raise SystemExit(main())
