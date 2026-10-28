#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Measure stair collision method 0 against method 1 on a finished CHIM build, read only (CHIM-STAIR-COLLISION-MESH-47).

For every distinct mesh the build's CHIM region frames hold (chim-world/work/*/scenery: the scenery index and archive
each frame was converted from), the drawn mesh's flights of stairs are found (stair_mesh.flights). For each mesh with a
flight, its collision is built twice with the same profile, the CHIM model builder's (stair-plate rules, visible-tread
rule, measured hull-surface table): method 0 (mesh_geometry.collision_pieces as shipped) and method 1 (the same with
stair_collision 'mesh'); both are written as the same collision-only brush image (chim.models.model_image_lumps: the
routed or chained standing hull and the point hull), and the geometric stair check (stair_mesh.check_flights) is run on
both. Per frame, the collision bytes of its distinct flight meshes are summed for both methods.

What this does NOT measure: placed variants (scale, tilt: each variant of a mesh is its own stored model; here every
mesh is measured at scale 1, untilted), the frame's chunk terrain, and anything in game. No game data is written: the
output holds mesh paths, counts and sizes only. Nothing is walked.

    stair_mesh_survey.py RUN --out DIR [--jobs N] [--limit N]
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / 'src'), str(HERE)]

LUMPS = {'planes': 1, 'nodes': 5, 'clipnodes': 9}


def scan_frames(run):
    """[(frame work name, index path, archive path)] of the run's CHIM region frames."""
    out = []
    for work in sorted((Path(run) / 'chim-world' / 'work').iterdir()):
        index = work / 'scenery' / 'scenery-index.json'
        archive = work / 'scenery' / 'scenery.mwpak'
        if index.is_file() and archive.is_file():
            out.append((work.name, str(index), str(archive)))
    return out


def index_models(index, archive):
    """The models of a scenery index as the survey measures them: key (source, mesh and collision SHA-256), record,
    archive, the group profile and the placement count."""
    groups = index.get('groups', {})
    placed = {}
    for r in index.get('references', ()):
        placed[r['model_index']] = placed.get(r['model_index'], 0) + 1
    models = []
    for mi, m in enumerate(index['models']):
        profile = None
        for g in groups.values():
            vp = g.get('visual_profiles', {})
            if m['source'] in vp:
                profile = vp[m['source']]
                break
        key = (m['source'], m.get('sha256'), (m.get('collision') or {}).get('sha256'))
        models.append({'key': '|'.join(str(x) for x in key), 'source': m['source'], 'record': m, 'archive': archive,
                       'group_profile': profile, 'placements': placed.get(mi, 0)})
    return models


def _frame_models(task):
    name, index_path, archive = task
    index = json.loads(Path(index_path).read_text(encoding='utf-8'))
    return name, index_models(index, archive)


def chim_profile(source, triangles, group_profile, surface_table):
    """The CHIM model builder's profile for a mesh (chim.build: town_model_profile + stair plates + visible treads +
    the hull-surface table), without recipes and detail budgets."""
    from town_regions import town_model_profile
    from mesh_geometry import SURFACE_LOSS
    profile = town_model_profile(group_profile or {}, source, triangles, underpass_names=True)
    profile['stair_plates'] = True
    profile['visible_treads'] = True
    from mesh_geometry import STANDING_ROOM_DEPTH
    from mesh_geometry_env import standing_room_applies
    if standing_room_applies(source):
        profile['standing_room'] = STANDING_ROOM_DEPTH
    if source.replace(chr(92), '/').casefold() in surface_table:
        profile['hull_surface_loss'] = SURFACE_LOSS
    return profile


def _collision_bytes(pieces, exact):
    from chim.models import model_image_lumps
    import numpy as np
    if pieces:
        pts = np.vstack([p[0] for p in pieces])
        lo, hi = pts.min(axis=0), pts.max(axis=0)
    else:
        lo = hi = np.zeros(3)
    report = {}
    lumps, _ = model_image_lumps([], pieces, lo, hi, lambda m: 0, exact=exact, report=report)
    out = {k: len(lumps[i]) for k, i in LUMPS.items()}
    out['bytes'] = sum(out.values())
    out['hull'] = report.get('hull')
    out['pieces'] = len(pieces)
    return out


def _measure(task):
    """One mesh: flights, both methods' collision bytes, check results and times."""
    import numpy as np
    from mwad.scene import read_asset, unpack_geometry
    from exterior_visibility import apply_exterior_selection
    from stair_mesh import collision_pieces       # method 0 for a profile without stair_collision
    import stair_mesh
    m, surface_table = task
    rec = m['record']
    out = {'source': m['source'], 'key': m['key']}
    try:
        with open(m['archive'], 'rb') as archive:
            vv, ff, _ = unpack_geometry(read_asset(archive, rec))
            v, f = np.array(vv), np.array(ff)
            vis_f = apply_exterior_selection(f, rec)
            cv, cf = v, f
            if rec.get('collision'):
                a, b, _ = unpack_geometry(read_asset(archive, rec['collision']))
                cv, cf = np.array(a), np.array(b)
        out['rootcollisionnode'] = bool(rec.get('collision'))
        t = time.perf_counter()
        # a RootCollisionNode: drawn faces it holds nothing under are no treads (stair_mesh.flights collision)
        authored = bool(rec.get('collision'))
        groups = stair_mesh.flights(v, vis_f, collision=(cv, cf) if authored else None) if len(vis_f) else []
        out['flight_detect_s'] = round(time.perf_counter() - t, 4)
        out['flights'] = len(groups)
        out['flights_risers'] = len(stair_mesh.flights(v, vis_f, detector='risers')) if len(vis_f) else 0
        out['treads'] = int(sum(len(g) for g in groups))
        if not groups:
            return out
        out['flights_levels'] = [int(len(np.unique(np.round(stair_mesh._tris(v, vis_f)[g][:, :, 2].mean(axis=1))))) for g in groups]
        profile = chim_profile(m['source'], rec['triangles'], m['group_profile'], surface_table)
        if (rec.get('source_collision') or {}).get('mode') == 'nonsolid':
            profile['collision_none'] = True
        tris = stair_mesh._tris(v, vis_f)
        for method, prof in (('m0', profile), ('m1', dict(profile, stair_collision='mesh')),
                             ('m1f', dict(profile, stair_collision='mesh', stair_ramps='flight'))):
            t = time.perf_counter()
            pieces, exact, note = collision_pieces(cv, cf, prof, visible=(v, vis_f), authored=authored)
            build = time.perf_counter() - t
            t = time.perf_counter()
            found = [stair_mesh.check_flight(pieces, tris, ids) for ids in groups]
            check = time.perf_counter() - t
            row = _collision_bytes(pieces, exact)
            row.update(build_s=round(build, 3), check_s=round(check, 4), note=note,
                       flights_failing=sum(1 for x in found if x), samples_failing=sum(len(x) for x in found),
                       checks_failing=sorted({y['check'] for x in found for y in x}),
                       samples_by_check={c: sum(1 for x in found for y in x if y['check'] == c)
                                         for c in sorted({y['check'] for x in found for y in x})},
                       flights_by_check={c: sum(1 for x in found if any(y['check'] == c for y in x))
                                         for c in sorted({y['check'] for x in found for y in x})})
            out[method] = row
    except Exception as error:      # a mesh that fails is reported with its reason, never skipped silently
        out['error'] = '%s: %s' % (type(error).__name__, error)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('run')
    ap.add_argument('--out', required=True)
    ap.add_argument('--jobs', type=int, default=os.cpu_count())
    ap.add_argument('--limit', type=int, default=0, help='measure at most this many flight meshes (0: all)')
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    from chim.build import hull_surface_table
    surface_table = hull_surface_table()
    t0 = time.perf_counter()
    frames = scan_frames(a.run)
    print('[stair-mesh] %d frames; reading their scenery indexes on %d workers' % (len(frames), a.jobs), flush=True)
    meshes, per_frame = {}, {}
    with ProcessPoolExecutor(a.jobs) as pool:
        for k, (name, models) in enumerate(pool.map(_frame_models, frames, chunksize=8), 1):
            per_frame[name] = sorted({x['key'] for x in models})
            for x in models:
                meshes.setdefault(x['key'], x)
            if k % 200 == 0:
                print('[stair-mesh] indexes %d/%d, %d distinct meshes' % (k, len(frames), len(meshes)), flush=True)
    print('[stair-mesh] %d distinct meshes in %.1f s; measuring on %d workers' % (len(meshes), time.perf_counter() - t0,
                                                                                 a.jobs), flush=True)
    items = sorted(meshes.values(), key=lambda x: -x['record'].get('triangles', 0))   # largest first
    if a.limit:
        items = items[:a.limit]
    results = []
    t1 = time.perf_counter()
    with ProcessPoolExecutor(a.jobs) as pool:
        for k, r in enumerate(pool.map(_measure, [(x, surface_table) for x in items], chunksize=1), 1):
            results.append(r)
            if k % 100 == 0 or k == len(items):
                print('[stair-mesh] meshes %d/%d (%d with flights) %.0f s' % (
                    k, len(items), sum(1 for x in results if x.get('flights')), time.perf_counter() - t1), flush=True)
    by_key = {r['key']: r for r in results}
    frames_out = {}
    for name, keys in per_frame.items():
        rows = [by_key[k] for k in keys if by_key.get(k, {}).get('flights') and 'm0' in by_key[k]]
        if not rows:
            continue
        frames_out[name] = {'flight_meshes': len(rows), 'flights': sum(r['flights'] for r in rows),
                            'm0_bytes': sum(r['m0']['bytes'] for r in rows), 'm1_bytes': sum(r['m1']['bytes'] for r in rows),
                            'm0_clipnodes': sum(r['m0']['clipnodes'] // 8 for r in rows),
                            'm1_clipnodes': sum(r['m1']['clipnodes'] // 8 for r in rows),
                            'm0_planes': sum(r['m0']['planes'] // 20 for r in rows),
                            'm1_planes': sum(r['m1']['planes'] // 20 for r in rows)}
    report = {'format': 1, 'run': str(a.run), 'frames': len(frames), 'distinct_meshes': len(meshes),
              'wall_s': round(time.perf_counter() - t0, 1), 'jobs': a.jobs, 'meshes': results, 'per_frame': frames_out}
    (out / 'stair-mesh-survey.json').write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    print('[stair-mesh] done in %.1f s: %s' % (time.perf_counter() - t0, out / 'stair-mesh-survey.json'), flush=True)


if __name__ == '__main__':
    main()
