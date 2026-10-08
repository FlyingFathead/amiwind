# SPDX-License-Identifier: GPL-3.0-only
"""World estimate check: convert a stratified sample of maps with this
repository's converters, on your machine and from your own data, and compare
the measured BSPs and heap with the frozen estimates.

Interiors use prepare_area.build_room; exteriors use the town converter steps
of import_town (audit, scenery export, model preparation, terrain map,
qbsp/vis/light, mesh assembly, visual bounding) on a 3x3-cell frame centred on
the sample's frame. The heap is check_world_map_heap on the raw BSP and on the
optimizer's output (optimize_world_maps), which needs the Amiga SDK (--sdk).
Only Morrowind.esm maps are sampled: the converters read that master.
The measured maps are saved as validation/results.json ('measured') and are
the input of `estimate-calibrate`.
"""
import collections
import contextlib
import hashlib
import json
import os
import shutil
import struct
import subprocess
import time
import traceback
from pathlib import Path

import world_estimate_data as D

LUMPS = ('entities', 'planes', 'textures', 'vertexes', 'visibility', 'nodes', 'texinfo', 'faces',
         'lighting', 'clipnodes', 'leafs', 'marksurfaces', 'edges', 'surfedges', 'models')
SIZES = {'planes': 20, 'vertexes': 12, 'nodes': 24, 'texinfo': 40, 'faces': 20, 'clipnodes': 8, 'leafs': 28,
         'marksurfaces': 2, 'edges': 4, 'surfedges': 4, 'models': 64}
COMPARE = ('faces', 'texinfo', 'nodes', 'clipnodes', 'vertexes', 'lighting_bytes', 'bsp_bytes')


def bsp_lumps(raw):
    """Record counts and byte sizes of a BSP29 file (the estimate's targets)."""
    if len(raw) < 124 or struct.unpack_from('<i', raw)[0] != 29:
        raise ValueError('not a BSP29 file')
    lumps = {}
    for k, name in enumerate(LUMPS):
        off, ln = struct.unpack_from('<ii', raw, 4 + 8 * k)
        lumps[name] = raw[off:off + ln]
    row = {'bsp_bytes': len(raw)}
    for k, s in SIZES.items():
        row[k] = len(lumps[k]) // s
    row.update(lighting_bytes=len(lumps['lighting']), visibility_bytes=len(lumps['visibility']),
               texture_bytes=len(lumps['textures']), entity_bytes=len(lumps['entities']))
    row['max_extent'], row['bad_extent_faces'] = surface_extents(lumps)
    ents = lumps['entities'].decode('cp1252', 'replace')
    row['func_walls'] = ents.count('"classname" "func_wall"')
    row['flames'] = ents.count('"classname" "aw_flame"')
    return row


def surface_extents(lumps):
    """Largest lit-surface extent and faces over 256 texels, computed in double
    precision from the stored 32-bit values like the 68040's extended precision
    (model.c CalcSurfaceExtents; MESH-EXTENT-GRID-31)."""
    import numpy as np
    face = np.dtype([('plane', '<u2'), ('side', '<u2'), ('first', '<i4'), ('num', '<u2'), ('ti', '<u2'),
                     ('st', 'u1', 4), ('lo', '<i4')])
    tex = np.dtype([('v', '<f4', (2, 4)), ('miptex', '<i4'), ('flags', '<i4')])
    faces = np.frombuffer(lumps['faces'], face)
    faces = faces[faces['num'] > 0]
    if not len(faces):
        return 0.0, 0
    verts = np.frombuffer(lumps['vertexes'], '<f4').reshape(-1, 3).astype(np.float64)
    edges = np.frombuffer(lumps['edges'], '<u2').reshape(-1, 2)
    surf = np.frombuffer(lumps['surfedges'], '<i4')
    texinfo = np.frombuffer(lumps['texinfo'], tex)
    num = faces['num'].astype(np.int64)
    starts = np.zeros(len(faces), np.int64)
    starts[1:] = np.cumsum(num)[:-1]
    idx = np.repeat(faces['first'].astype(np.int64) - starts, num) + np.arange(int(num.sum()))
    se = surf[idx]
    vi = np.where(se >= 0, edges[np.abs(se), 0], edges[np.abs(se), 1])
    tv = texinfo['v'][faces['ti'][np.repeat(np.arange(len(faces)), num)]].astype(np.float64)
    p = verts[vi]
    s = (p * tv[:, 0, :3]).sum(1) + tv[:, 0, 3]
    t = (p * tv[:, 1, :3]).sum(1) + tv[:, 1, 3]
    es = np.ceil(np.maximum.reduceat(s, starts) / 16) * 16 - np.floor(np.minimum.reduceat(s, starts) / 16) * 16
    et = np.ceil(np.maximum.reduceat(t, starts) / 16) * 16 - np.floor(np.minimum.reduceat(t, starts) / 16) * 16
    special = (texinfo['flags'][faces['ti']] & 1) != 0
    ext = np.where(special, 0, np.maximum(es, et))
    return float(ext.max()), int((ext > 256).sum())


def generic_palette():
    """A neutral 256-colour palette (6x6x6 cube and greys). Sample conversion
    only needs a valid palette; record counts do not depend on its colours."""
    out = bytearray()
    for r in range(6):
        for g in range(6):
            for b in range(6):
                out += bytes((r * 51, g * 51, b * 51))
    for i in range(40):
        v = 6 + i * 6
        out += bytes((v, v, v))
    return bytes(out)


@contextlib.contextmanager
def tool_output(path):
    """Send this process's stdout, including child compilers writing to file
    descriptor 1, to a log file while converting."""
    import sys
    sys.stdout.flush()
    saved = os.dup(1)
    with open(path, 'a') as log:
        os.dup2(log.fileno(), 1)
        try:
            with contextlib.redirect_stdout(log):
                yield
        finally:
            sys.stdout.flush()
            os.dup2(saved, 1)
            os.close(saved)


def _hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def select(preds, n, masters):
    """Stratified sample: half interiors, half exterior regions, each by
    quantile bins of the predicted heap, deterministic order inside a bin."""
    land = set(masters['Morrowind.esm']['lands'])
    ints = sorted((r for r in preds if r['set'] == 'vvardenfell' and r['space'] == 'interior'
                   and r['cur_refs'] > 0 and r['cur']['faces'] > 0), key=lambda r: r['cur']['heap_final'])
    exts = sorted((r for r in preds if r['set'] == 'vvardenfell' and r['space'] == 'exterior' and r['cur_refs'] > 0
                   and all((r['centre_cell'][0] + dx, r['centre_cell'][1] + dy) in land
                           for dx in (-1, 0, 1) for dy in (-1, 0, 1))), key=lambda r: r['cur']['heap_final'])
    n_int = min(len(ints), n // 2)
    n_ext = min(len(exts), n - n_int)
    pick = []
    for b in range(n_int):
        seg = ints[len(ints) * b // n_int: len(ints) * (b + 1) // n_int]
        pick.append(sorted(seg, key=lambda r: _hash(r['cell'] + 'int%d' % b))[0])
    used = collections.Counter()
    for b in range(n_ext):
        seg = exts[len(exts) * b // n_ext: len(exts) * (b + 1) // n_ext]
        cand = sorted(seg, key=lambda r: _hash(r['map'] + 'ext%d' % b))
        cand.sort(key=lambda r: used[r['frame']])
        used[cand[0]['frame']] += 1
        pick.append(cand[0])
    return pick


# ---------------------------------------------------------------- conversion

def convert_interior(data, scene, quake, sample):
    from prepare_area import build_room
    out = {'map': sample['map'], 'cell': sample['cell'], 'attempts': []}
    t0 = time.monotonic()
    for attempt, extra in enumerate(({}, {'original_door_arrivals': True})):
        if attempt and 'No source entrance' not in out['attempts'][-1].get('error', ''):
            break
        work = scene / 'area-work' / sample['map']
        if work.exists():
            shutil.move(str(work), str(work) + '-a%d' % attempt)
        entry = {'map': sample['map'], 'cell': sample['cell'], 'interior': True, 'area': D.INTERIOR_AREA, **extra}
        rec = {'attempt': attempt + 1, 'flags': extra}
        try:
            with tool_output(scene / 'convert.log'):
                build_room((data, scene, entry, quake['qbsp'], quake['vis'], quake['light'], ''))
            rec['status'] = 'ok'
        except Exception as exc:  # noqa: BLE001 - recorded per map
            rec.update(status='failed', error=('%s: %s' % (type(exc).__name__, exc))[:300])
        if (work / 'room.bsp').is_file():
            rec['bsp_path'] = str(work / 'room.bsp')
        out['attempts'].append(rec)
    out['seconds'] = round(time.monotonic() - t0, 1)
    last = out['attempts'][-1]
    return {'status': last['status'], 'error': last.get('error'), 'seconds': out['seconds'],
            'bsp_path': last.get('bsp_path')}


def convert_frame(data, work, quake, palette, fid, centre_cell, regions, jobs):
    """Convert the listed region indices of one 3x3-cell frame with the town converter's steps."""
    from mwad.audit import audit, normpath
    from town_config import town_field
    from town_regions import regions as make_regions, select_references, visual_profile, collision_coverage
    from prepare_scenery import export_refs
    from prepare_mesh_bsp import append_meshes, _prepare_model
    from build_parallel import ordered_map
    from surface_flatten import load_profiles
    from player_hull import rebuild_world_hull
    from bound_balmora_visuals import bound_visuals
    from import_town import ground_assets, terrain_at, terrain_map
    from vis_options import light_args, vis_args
    s = D.region_settings()
    s.update(source_cell=list(centre_cell), source_radius=1, terrain_material_repairs=[],
             centre=[(centre_cell[0] + .5) * D.CELL, (centre_cell[1] + .5) * D.CELL])
    out = work / 'exteriors' / fid
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    results = {}
    with tool_output(out / 'frame.log'):
        audit(data, out / 'audit', tuple(s['source_cell']), s['source_radius'], 2)
        references = json.loads((out / 'audit/placements.json').read_text())
        selected = [r for r in references if r.get('type') not in ('NPC_', 'CREA', 'LEVC', 'LEVI')
                    and normpath(r.get('model', '')) and
                    not normpath(r.get('model', '')).rsplit('/', 1)[-1].startswith('marker_')]
        profiles = {normpath('meshes/' + r['model']): {'collision_source': 'root_node_or_visual'} for r in selected}
        group = town_field(s, 'visual_group')
        groups = {group: {'references': [r['number'] for r in selected], 'visual_profiles': profiles}}
        export_refs(data, out / 'scenery', selected, groups, [*s['centre'], 0],
                    metadata={'runtime_bounds': s['bounds']}, jobs=jobs)
        index = json.loads((out / 'scenery/scenery-index.json').read_text())
        grids = {tuple(g['cell']): g for g in json.loads((out / 'audit/terrain-source.json').read_text())}
        terrain_wad = ground_assets(data, out / 'audit', palette)
        vprof = index['groups'][group]['visual_profiles']
        flatten = load_profiles()
        tasks = []
        for mi, model in enumerate(index['models']):
            profile = {**vprof[model['source']], **visual_profile(model['source'], model['triangles'])}
            if model['source'] in flatten:
                profile['flatten'] = flatten[model['source']]
            vprof[model['source']] = profile
            tasks.append((mi, model, profile, out / 'scenery/scenery.mwpak', index['textures']))
        (out / 'scenery/scenery-index.json').write_text(json.dumps(index, indent=2) + '\n')
        prepared = dict(ordered_map(_prepare_model, tasks, min(jobs, max(1, len(tasks)))))
        entries = make_regions(s)
        for n in regions:
            entry = entries[n]
            root = out / entry['name']
            root.mkdir()
            rec = {}
            t0 = time.monotonic()
            try:
                chosen = select_references(index, entry, s)
                (root / 'terrain.wad').write_bytes(terrain_wad)
                spawn = [(entry['core'][0][i] + entry['core'][1][i]) / 2 for i in range(2)]
                spawn.append(terrain_at(grids, s, *spawn)[0] + 40)
                (root / 'terrain.map').write_text(terrain_map(entry, grids, s, spawn, ''))
                with (root / 'compile.log').open('w') as clog:
                    for exe, args in ((quake['qbsp'], ['-nopercent', 'terrain.map']),
                                      (quake['vis'], vis_args('terrain.bsp', jobs, 'fast')),
                                      (quake['light'], light_args('-minlight', '24', 'terrain.bsp'))):
                        subprocess.run([str(exe), *args], cwd=root, stdout=clog, stderr=subprocess.STDOUT, check=True)
                base = root / 'base.bsp'
                shutil.copyfile(root / 'terrain.bsp', base)
                rebuild_world_hull(base, root / 'terrain.map', quake['qbsp'])
                append_meshes(base, root / 'scene.bsp', out / 'scenery', work / 'palette.lmp', centre=s['centre'],
                              jobs=jobs, references=chosen, prepared_models=prepared, retain_dressing=True,
                              collision_bounds=collision_coverage(entry, s), collision_compiler=quake['qbsp'],
                              collision_cache=out / 'collision-cache')
                bounded, _ = bound_visuals((root / 'scene.bsp').read_bytes(), entry['coverage'])
                (root / 'scene.bsp').write_bytes(bounded)
                rec.update(status='ok', bsp_path=str(root / 'scene.bsp'))
            except Exception as exc:  # noqa: BLE001 - recorded per map
                rec.update(status='failed', error=('%s: %s' % (type(exc).__name__, exc))[:300],
                           traceback=traceback.format_exc()[-1200:])
            rec['seconds'] = round(time.monotonic() - t0, 1)
            for p in ('base.bsp', 'terrain.bsp', 'terrain.prt', 'terrain.wad'):
                if (root / p).exists():
                    (root / p).unlink()
            results[n] = rec
    return results


def heap_rows(paths, sdk, stage):
    """Raw and optimized heap (check_world_map_heap) of each converted BSP."""
    from check_world_map_heap import compile_target_sizes, inspect_maps
    from optimize_world_maps import optimize_maps
    sizes, _ = compile_target_sizes(sdk)
    if stage.exists():
        shutil.rmtree(stage)
    raw = stage / 'raw/id1/maps'
    fin = stage / 'final/id1/maps'
    raw.mkdir(parents=True)
    fin.mkdir(parents=True)
    for name, p in paths.items():
        shutil.copyfile(p, raw / (name + '.bsp'))
    out = collections.defaultdict(dict)
    for r in inspect_maps(raw, sizes)['maps']:
        out[r['map'].removesuffix('.bsp')]['heap_raw'] = r['estimated_total_bytes']
    for name in paths:
        one = stage / 'single' / name / 'id1/maps'
        one.mkdir(parents=True)
        shutil.copyfile(raw / (name + '.bsp'), one / (name + '.bsp'))
        try:
            with tool_output(stage / 'optimize.log'):
                optimize_maps(one, one.parent.parent / 'optimize.json', jobs=1)
            shutil.move(str(one / (name + '.bsp')), str(fin / (name + '.bsp')))
            out[name]['final_bsp_bytes'] = (fin / (name + '.bsp')).stat().st_size
        except Exception as exc:  # noqa: BLE001 - recorded per map
            out[name]['optimize_error'] = ('%s: %s' % (type(exc).__name__, exc))[:200]
    if any(fin.glob('*.bsp')):
        for r in inspect_maps(fin, sizes)['maps']:
            out[r['map'].removesuffix('.bsp')]['heap_final'] = r['estimated_total_bytes']
    return out


def quake_tools(args):
    candidates = [args.quake_tools] if args.quake_tools else []
    if os.environ.get('ERICW_BIN'):
        candidates.append(Path(os.environ['ERICW_BIN']))
    tools = {}
    for name in ('qbsp', 'vis', 'light'):
        found = next((d / name for d in candidates if (d / name).is_file()), None)
        found = found or (Path(shutil.which(name)) if shutil.which(name) else None)
        if found is None:
            raise ValueError('--sample-convert needs ericw-tools %s (use --quake-tools DIR)' % name)
        tools[name] = found.resolve()
    return tools


def stats(p, t):
    import numpy as np
    p = np.array([x for x, y in zip(p, t) if y], float)
    t = np.array([y for y in t if y], float)
    if not len(t):
        return None
    rel = (p - t) / t
    return {'n': int(len(t)), 'median_abs_pct': round(float(np.median(np.abs(rel))) * 100, 2),
            'p90_abs_pct': round(float(np.percentile(np.abs(rel), 90)) * 100, 2),
            'max_abs_pct': round(float(np.abs(rel).max()) * 100, 2), 'bias_pct': round(float(np.median(rel)) * 100, 2)}


def run(args, data, masters, meshes, model, preds, rows, out, limits, progress=print):
    """Select, freeze, convert, measure and compare (writes OUT/validation/)."""
    vdir = out / 'validation'
    vdir.mkdir(parents=True, exist_ok=True)
    work = (Path(args.work) if args.work else out / 'work') / 'sample'
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    quake = quake_tools(args)
    palette = Path(args.palette).read_bytes() if args.palette else generic_palette()
    (work / 'palette.lmp').write_bytes(palette)
    scene = work / 'scene'
    (scene / 'id1/gfx').mkdir(parents=True)
    (scene / 'id1/gfx/palette.lmp').write_bytes(palette)
    sample = select(preds, args.sample_convert, masters)
    frozen = [{k: v for k, v in r.items()} for r in sample]
    (vdir / 'sample.json').write_text(json.dumps({'frozen_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                                                   'maps': frozen}, indent=1) + '\n', encoding='utf-8', newline='\n')
    progress('sample conversion: %d maps frozen (%d interior, %d exterior)' % (
        len(sample), sum(r['space'] == 'interior' for r in sample), sum(r['space'] == 'exterior' for r in sample)))
    results = {}
    t0 = time.monotonic()
    for r in sample:
        if r['space'] == 'interior':
            results[r['map']] = convert_interior(data, scene, quake, r)
            progress('  %s %s' % (r['map'], results[r['map']]['status']))
    frames = collections.defaultdict(list)
    for r in sample:
        if r['space'] == 'exterior':
            frames[(r['frame'], tuple(r['centre_cell']))].append(r)
    for (fid, cc), regs in sorted(frames.items()):
        try:
            got = convert_frame(data, work, quake, palette, fid, cc, [int(x['map'][-3:]) for x in regs], args.jobs)
            for x in regs:
                results[x['map']] = got[int(x['map'][-3:])]
        except Exception as exc:  # noqa: BLE001 - a frame failure fails its regions only
            for x in regs:
                results[x['map']] = {'status': 'failed', 'error': 'frame: %s: %s' % (type(exc).__name__, str(exc)[:200])}
        for x in regs:
            progress('  %s %s' % (x['map'], results[x['map']]['status']))
    timing = {'convert_s': round(time.monotonic() - t0, 1)}
    paths = {k: v['bsp_path'] for k, v in results.items() if v.get('bsp_path')}
    for k, p in paths.items():
        results[k]['bsp'] = bsp_lumps(Path(p).read_bytes())
    if args.sdk:
        t1 = time.monotonic()
        for k, h in heap_rows(paths, args.sdk, work / 'heap-stage').items():
            results[k].update(h)
        timing['heap_s'] = round(time.monotonic() - t1, 1)
    else:
        progress('  no --sdk: heap not measured for the sample (lumps only)')
    measured = []
    for r in sample:
        res = results.get(r['map'], {})
        if res.get('bsp') and res.get('heap_raw'):
            measured.append({'map': r['map'], 'space': r['space'], 'cell': r.get('cell'), 'frame': r.get('frame'),
                             'centre_cell': r.get('centre_cell'), 'bsp': res['bsp'], 'heap_raw': res['heap_raw'],
                             'heap_final': res.get('heap_final'), 'final_bsp_bytes': res.get('final_bsp_bytes'),
                             'seconds': res.get('seconds')})
    public = {k: {kk: vv for kk, vv in v.items() if kk not in ('bsp_path', 'traceback')} for k, v in results.items()}
    (vdir / 'results.json').write_text(json.dumps({'timing': timing, 'results': public, 'measured': measured},
                                                  indent=1) + '\n', encoding='utf-8', newline='\n')
    compare(sample, results, limits, vdir)
    progress('sample conversion done in %.0f s; see %s' % (time.monotonic() - t0, vdir / 'compare.json'))


def compare(sample, results, limits, vdir):
    import csv
    import io
    rows = []
    for s in sample:
        r = results.get(s['map'], {})
        b = r.get('bsp') or {}
        p = s['cur']
        row = {'map': s['map'], 'space': s['space'],
               'name': s.get('cell') or 'exterior %s %s' % (s['centre_cell'], s['region']),
               'status': r.get('status'), 'error': (r.get('error') or '')[:100], 'seconds': r.get('seconds'),
               'pred_seconds': p['seconds'], 'variants': p['n_var']}
        for k in COMPARE:
            row[k + '_pred'] = p[k]
            row[k + '_true'] = b.get(k)
        row['inline_pred'] = max(0, p['models'] - 1)
        row['inline_true'] = (b['models'] - 1) if b else None
        row['funcwall_pred'] = s['cur_refs']
        row['funcwall_true'] = b.get('func_walls')
        row['extent_pred'] = p.get('known_maxext')
        row['extent_true'] = b.get('max_extent')
        row['flames_pred'] = s['cur_flames']
        row['flames_true'] = b.get('flames')
        if r.get('heap_final'):
            row.update(heap_true=r['heap_final'], heap_pred=p['heap_final'], heap_kind='optimized')
        elif r.get('heap_raw'):
            row.update(heap_true=r['heap_raw'], heap_pred=p['heap_raw'], heap_kind='raw')
        else:
            row.update(heap_true=None, heap_pred=p['heap_final'], heap_kind='not measured')
        rows.append(row)
    ok = [r for r in rows if r['faces_true']]
    errors = {}
    for sp in ('interior', 'exterior', 'all'):
        sub = [r for r in ok if sp == 'all' or r['space'] == sp]
        errors[sp] = {k: stats([r[k + '_pred'] for r in sub], [r[k + '_true'] for r in sub])
                      for k in list(COMPARE) + ['heap', 'inline', 'funcwall', 'flames']}
    gates = []
    agree = collections.Counter()
    for r in rows:
        g = {'map': r['map'], 'name': r['name'], 'status': r['status']}
        for k, lim in (('heap', limits['heap_budget']), ('texinfo', limits['texinfo']), ('extent', limits['surface_extent']),
                       ('clipnodes', limits['clipnodes']), ('faces', limits['faces']), ('inline', limits['inline_models'])):
            pv, tv = r[k + '_pred'], r[k + '_true']
            g[k] = '%s/%s' % ('FAIL' if pv and pv > lim else 'pass', 'n/a' if tv is None else ('FAIL' if tv > lim else 'pass'))
            if tv is not None:
                agree['agree' if (pv > lim) == (tv > lim) else 'disagree'] += 1
        gates.append(g)
    doc = {'errors': errors, 'gate_agreement': dict(agree), 'rows': rows, 'gates_pred_vs_true': gates,
           'validation': [{'map': r['map'], 'name': r['name'], 'space': r['space'], 'heap_true': r['heap_true'],
                           'heap_pred': r['heap_pred']} for r in rows]}
    (vdir / 'compare.json').write_text(json.dumps(doc, indent=1) + '\n', encoding='utf-8', newline='\n')
    buf = io.StringIO()
    w = csv.DictWriter(buf, list(rows[0].keys()) if rows else ['map'], lineterminator='\n')
    w.writeheader()
    w.writerows(rows)
    (vdir / 'compare.csv').write_bytes(buf.getvalue().encode('utf-8'))
    return doc


def feature_pairs(masters, meshes, measured):
    """(feature row, measured) pairs for calibration, features recomputed from the census."""
    world = D.World(masters, 'Morrowind.esm', meshes)
    settings = D.region_settings()
    by_cell = {c['name'].casefold(): c for c in world.cells if c['interior'] and not c['deleted']}
    pairs = []
    frames = collections.defaultdict(dict)
    for m in measured:
        if m['space'] == 'interior':
            c = by_cell.get((m.get('cell') or '').casefold())
            if c is None:
                continue
            f = next(D.interior_maps(world, 'i', [c]))
            f['map'] = m['map']
            pairs.append((f, m))
        else:
            frames[(m['frame'], tuple(m['centre_cell']))][m['map']] = m
    for (fid, cc), want in frames.items():
        for f in D.exterior_frames(world, [(fid, cc)], settings):
            if f['map'] in want:
                pairs.append((f, want[f['map']]))
    return pairs
