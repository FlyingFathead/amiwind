#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Calibrate the geometric stair check against the recorded stair walks, without walking (CHIM-STAIR-COLLISION-MESH-47).

A finished build's CHIM frames were walked once (stair_walk.py, the records in the build pool's pass cache); this
tool reads those records READ ONLY and compares them with the geometric check (stair_mesh.check_flight) on the same
tread points:

1. the frames and the walk each reused (the run's chim-world/chim-stairs.json pass_cache: frame path -> record time);
2. every distinct mesh with a flight (stair_mesh.flights), its collision as the build made it (method 0, the CHIM model
   builder's profile) and the check's verdict per tread sample;
3. every recorded step row (kind 'step', passed or failed) on a placement of such a mesh, moved into the mesh's own
   frame (the inverse of prepare_mesh_bsp._placement_frame and the placement's rotation and scale; tilted placements
   are left out and counted);
4. a tread sample is COVERED by a row when it lies in the strip the standing box sweeps over that riser (CLEARANCE
   either side of the riser point along the walk direction, the box's half width across it); per covered sample the
   walk's verdict (failed when any covering row failed) against the check's.

Output: per flight and per sample, agree / check stricter (walk passed, check failed) / check misses (walk failed,
check passed) / not covered, the failing checks behind each disagreement, and the alignment of the moved rows with
the drawn treads (how far a riser point lies from the nearest tread level). Hashes, mesh paths and counts only: no
game data. Nothing is walked.

    stair_mesh_calibrate.py RUN --cache POOL/image-passes --out DIR [--jobs N]
"""
import argparse
import collections
import glob
import json
import math
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / 'src'), str(HERE)]

CLEARANCE = 11.0          # stair_walk.CLEARANCE: the walk starts and ends this far from the riser
HALF_WIDTH = 7.32         # the standing box's half width (player_hull.MAXS[0])
TOWNS = {'frames/x-03/y-02/frame.ccf': 'balmora', 'frames/x+04/y-12/frame.ccf': 'vivec_city'}
TILT = 1e-6
# a walk row that failed before the box moved: its start place is in solid or has no floor (stair_walk.py: the box
# cannot be placed there); the walk tested nothing at that riser (counted, not compared)
WALK_SETUP = ('start in solid', 'no floor at start')


def work_dir(path):
    if path in TOWNS:
        return TOWNS[path]
    m = re.match(r'frames/x([+-])(\d+)/y([+-])(\d+)/', path)
    if not m:
        return None
    return 'rc%s%d_%s%d' % ('m' if m[1] == '-' else 'p', int(m[2]), 'm' if m[3] == '-' else 'p', int(m[4]))


def walked_frames(run):
    """{frame path: record time} from the run's stair gate pass cache ('reused from RUN (version, commit, TIME)')."""
    data = json.loads((Path(run) / 'chim-world' / 'chim-stairs.json').read_text(encoding='utf-8'))
    out = {}
    for path, how in (data.get('pass_cache') or {}).get('frames', {}).items():
        m = re.search(r'(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d \+0000)\)\s*$', how)
        if m:
            out[path] = m.group(1)
    return out


def _frame_placements(task):
    path, index_path, archive = task
    import stair_mesh_survey as survey
    index = json.loads(Path(index_path).read_text(encoding='utf-8'))
    models = survey.index_models(index, archive)
    out = []
    for r in index.get('references', ()):
        m = models[r['model_index']]
        out.append({'ref': str(r['number']), 'key': m['key'], 'position': r['position'],
                    'rotation': r['rotation_radians'], 'scale': r['scale'], 'bounds': r.get('bounds')})
    return path, index['centre'], models, out


def _mesh_samples(task):
    """Method 0 collision and the check's verdict per tread sample, per flight of one mesh."""
    import numpy as np
    from mwad.scene import read_asset, unpack_geometry
    from exterior_visibility import apply_exterior_selection
    from mesh_geometry import collision_pieces
    import stair_mesh
    import stair_mesh_survey as survey
    m, table = task
    rec = m['record']
    with open(m['archive'], 'rb') as archive:
        vv, ff, _ = unpack_geometry(read_asset(archive, rec))
        v, f = np.array(vv), np.array(ff)
        vis_f = apply_exterior_selection(f, rec)
        cv, cf = v, f
        if rec.get('collision'):
            a, b, _ = unpack_geometry(read_asset(archive, rec['collision']))
            cv, cf = np.array(a), np.array(b)
    groups = stair_mesh.flights(v, vis_f) if len(vis_f) else []
    if not groups:
        return m['key'], None
    profile = survey.chim_profile(m['source'], rec['triangles'], m['group_profile'], table)
    if (rec.get('source_collision') or {}).get('mode') == 'nonsolid':
        profile['collision_none'] = True
    pieces, _, _ = collision_pieces(cv, cf, profile, visible=(v, vis_f))
    tris = stair_mesh._tris(v, vis_f)
    levels = sorted({round(float(z), 2) for z in tris[np.concatenate(groups)][:, :, 2].mean(axis=1)})
    flights = []
    for ids in groups:
        got, first = {}, {}
        stair_mesh.check_flight(pieces, tris, ids, samples=got, form='box')
        stair_mesh.check_flight(pieces, tris, ids, samples=first, form='point')
        flights.append({'points': got['points'].tolist(), 'failed': {'box': [sorted(x) for x in got['failed']],
                                                                     'point': [sorted(x) for x in first['failed']]}})
    return m['key'], {'source': m['source'], 'flights': flights, 'levels': levels}


def _scan_records(task):
    """Step rows of the wanted placements from a batch of walk records whose time matches the frame's walk."""
    files, wanted_times, wanted = task
    out = []
    for name in files:
        try:
            r = json.loads(Path(name).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        row = r.get('row') or {}
        when = (row.get('record') or {}).get('time')
        for x in row.get('rows') or ():
            if x.get('kind') != 'step' or x.get('result') not in ('passed', 'failed'):
                continue
            mp = x.get('map')
            if wanted_times.get(mp) != when or (mp, str(x.get('ref'))) not in wanted:
                continue
            out.append({'map': mp, 'ref': str(x.get('ref')), 'point': x['point'], 'direction': x['direction'],
                        'result': x['result'], 'flight': bool(x.get('flight')), 'rise': x.get('rise'),
                        'top': x.get('top'), 'status': (x.get('detail') or {}).get('status'),
                        'angle': x.get('collision_angle'), 'over': x.get('collision_height_over_step')})
    return out


def _seg_dist(p, a, b):
    import numpy as np
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(float(ab @ ab), 1e-12), 0, 1)
    return np.linalg.norm(a + t[:, None] * ab - p, axis=1)


def main(argv=None):
    import numpy as np
    from prepare_scenery import reference_rotation
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('run')
    ap.add_argument('--cache', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--jobs', type=int, default=os.cpu_count())
    a = ap.parse_args(argv)
    t0 = time.perf_counter()
    times = walked_frames(a.run)
    work = Path(a.run) / 'chim-world' / 'work'
    tasks = []
    for path in sorted(times):
        wd = work_dir(path)
        if wd and (work / wd / 'scenery' / 'scenery-index.json').is_file():
            tasks.append((path, str(work / wd / 'scenery' / 'scenery-index.json'), str(work / wd / 'scenery' / 'scenery.mwpak')))
    print('[calibrate] %d walked frames, %d with a readable scenery index' % (len(times), len(tasks)), flush=True)
    meshes, frames = {}, {}
    with ProcessPoolExecutor(a.jobs) as pool:
        for path, centre, models, refs in pool.map(_frame_placements, tasks, chunksize=8):
            frames[path] = (centre, refs)
            for m in models:
                meshes.setdefault(m['key'], m)
    from chim.build import hull_surface_table
    table = hull_surface_table()
    found = {}
    with ProcessPoolExecutor(a.jobs) as pool:
        for key, res in pool.map(_mesh_samples, [(m, table) for m in meshes.values()], chunksize=4):
            if res:
                found[key] = res
    print('[calibrate] %d distinct meshes, %d with flights, %.0f s' % (len(meshes), len(found), time.perf_counter() - t0),
          flush=True)
    wanted, place = set(), {}
    tilted = 0
    for path, (centre, refs) in frames.items():
        for r in refs:
            if r['key'] not in found:
                continue
            if any(abs(math.sin(x)) > TILT or math.cos(x) < 0 for x in r['rotation'][:2]):
                tilted += 1
                continue
            wanted.add((path, r['ref']))
            origin = (np.array(r['position']) - np.array([*centre[:2], 0])) * .25
            place[(path, r['ref'])] = (r['key'], origin, reference_rotation({'rotation_radians': r['rotation']}), float(r['scale']))
    files = glob.glob(os.path.join(a.cache, 'stair-walk', '*', '*.json'))
    batches = [files[k::a.jobs * 4] for k in range(a.jobs * 4)]
    rows = []
    with ProcessPoolExecutor(a.jobs) as pool:
        for got in pool.map(_scan_records, [(b, times, wanted) for b in batches]):
            rows.extend(got)
    print('[calibrate] %d walk records read, %d step rows on %d untilted flight-mesh placements (%d tilted left out), '
          '%.0f s' % (len(files), len(rows), len(wanted), tilted, time.perf_counter() - t0), flush=True)
    # move every row into its mesh's frame; the samples it covers get its verdict
    walk = {k: [[[] for _ in fl['points']] for fl in v['flights']] for k, v in found.items()}
    reach = 4 * 16.625        # the standing box's half height in game units (bounds are in game units)

    def neighbours(x):
        """Other placements of the frame whose bounds, grown by the standing box, hold the row's riser point: their
        collision is in the walked frame and not in the mesh's own collision the check reads."""
        centre, refs = frames[x['map']]
        q = np.array(x['point'], float) / .25 + np.array([*centre[:2], 0])
        n = 0
        for r in refs:
            b = r.get('bounds')
            if r['ref'] == x['ref'] or not b:
                continue
            if all(b[0][i] - reach <= q[i] <= b[1][i] + reach for i in range(3)):
                n += 1
        return n
    misses_near = collections.Counter()
    align, rows_used = [], collections.Counter()
    for x in rows:
        key, origin, rot, scale = place[(x['map'], x['ref'])]
        p = rot.T @ (np.array(x['point'], float) - origin) / scale
        d3 = rot.T @ np.array([x['direction'][0], x['direction'][1], 0.])
        d = d3[:2] / max(np.linalg.norm(d3[:2]), 1e-12)
        levels = np.array(found[key]['levels'])
        align.append(float(np.abs(levels - p[2]).min()))
        hit = False
        if x['result'] == 'failed' and x['status'] in WALK_SETUP:
            rows_used['walk could not start (%s)' % x['status']] += 1
            continue
        verdict = x['result'] if x['result'] == 'passed' else 'failed:' + str(x['status'])
        if x['result'] == 'failed':
            near = neighbours(x)
            misses_near['walk failure, %s other placements within reach' % ('no' if not near else 'with')] += 1
            verdict += ' (another placement within reach)' if near else ' (this placement alone)'
            if abs(scale - 1) > 1e-3:
                verdict += ' (placed at scale %.2f)' % scale
        for fi, fl in enumerate(found[key]['flights']):
            pts = np.array(fl['points'])
            if not len(pts):
                continue
            along = _seg_dist(pts[:, :2], p[:2] - d * CLEARANCE, p[:2] + d * CLEARANCE)
            near = np.flatnonzero((along <= HALF_WIDTH) & (np.abs(pts[:, 2] - p[2]) <= 12.))
            for i in near:
                walk[key][fi][i].append(verdict)
            hit = hit or bool(len(near))
        rows_used['covering a sample' if hit else 'covering no sample'] += 1
    # agreement, per form of the check
    forms = {}
    listing = []
    for form in ('box', 'point'):
        S, F, why = collections.Counter(), collections.Counter(), collections.Counter()
        for key, v in found.items():
            for fi, fl in enumerate(v['flights']):
                cats = collections.Counter()
                for i, failed in enumerate(fl['failed'][form]):
                    w = walk[key][fi][i]
                    if not w:
                        c = 'not covered, check failed' if failed else 'not covered, check passed'
                    else:
                        wf = any(y != 'passed' for y in w)
                        c = ('agree: both failed' if failed else 'check misses (walk failed)') if wf else                             ('check stricter (walk passed)' if failed else 'agree: both passed')
                        if failed and not wf:
                            for chk in failed:
                                why[chk] += 1
                    cats[c] += 1
                    S[c] += 1
                covered = sum(n for c, n in cats.items() if not c.startswith('not covered'))
                stricter, misses = cats['check stricter (walk passed)'], cats['check misses (walk failed)']
                check_fails = any(fl['failed'][form])
                fc = 'not covered by the walk' if not covered else ('disagree' if stricter or misses else 'agree')
                F[fc] += 1
                F['check fails flight' if check_fails else 'check passes flight'] += 1
                F[('check fails' if check_fails else 'check passes') + ', ' + fc] += 1
                evidence = collections.Counter()
                for i, failed in enumerate(fl['failed'][form]):
                    w = walk[key][fi][i]
                    if w and failed and all(y == 'passed' for y in w):
                        evidence.update('check stricter: ' + c for c in failed)
                    if w and not failed and any(y != 'passed' for y in w):
                        evidence.update('check misses: walk ' + y for y in set(w) if y != 'passed')
                    if not w and failed:
                        evidence.update('not covered: ' + c for c in failed)
                listing.append({'form': form, 'mesh': v['source'], 'flight': fi, 'samples': len(fl['failed'][form]),
                                'covered': covered, 'class': fc, 'check_fails': check_fails, **dict(cats),
                                'evidence': dict(evidence)})
        forms[form] = {'samples': dict(S), 'flights': dict(F), 'stricter_by_check': dict(why)}
    walk_fail = collections.Counter((x['flight'], x['status']) for x in rows if x['result'] == 'failed')
    report = {'format': 1, 'run': str(a.run), 'frames': len(tasks), 'meshes_with_flights': len(found),
              'placements': len(wanted), 'tilted_left_out': tilted, 'rows': len(rows), 'rows_used': dict(rows_used),
              'row_alignment_to_tread_level': {'median': float(np.median(align)) if align else None,
                                               'p90': float(np.percentile(align, 90)) if align else None,
                                               'within_0_5': sum(1 for x in align if x <= .5)},
              'forms': forms, 'walk_failed_rows': {'%s, %s' % ('flight' if k[0] else 'not a flight', k[1]): n
                                                   for k, n in walk_fail.items()},
              'walk_rows': dict(collections.Counter(x['result'] for x in rows)), 'listing': listing,
              'walk_failures_neighbours': dict(misses_near),
              'wall_s': round(time.perf_counter() - t0, 1)}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'stair-mesh-calibration.json').write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: report[k] for k in report if k != 'listing'}, indent=1), flush=True)


if __name__ == '__main__':
    main()
