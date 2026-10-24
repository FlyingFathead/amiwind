#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The stair check of a finished CHIM build under the Quake step rules and Morrowind's (OpenMW's), read only
(STEP-MOVEMENT-OPENMW-RULES-48, docs/STEP_MOVEMENT.md).

For every distinct mesh with a flight of stairs in the build's CHIM region frames (the meshes and profiles
tools/stair_mesh_survey.py measures), the collision is built with stair collision method 0 and method 1, and the
geometric stair check (stair_mesh.check_flight: plane arithmetic over the drawn treads, no walk) is run on each under
two rule sets:

- quake: the engine's rules today (aw_step_rules 0): a step of 8.5 map units, standing on normal z 0.69 or more;
- openmw: the step rules (aw_step_rules 1): a step of 8.75 (OpenMW's sStepSizeUp 34 over its 1-unit ground offset,
  x 0.25), standing on normal z over cos 46 degrees (sMaxSlope).

Methods: m0 (method 0), m1 (method 1 built for the Quake rules, as the converter builds it today) and m1r (method 1
built for the step rules: the converter's step and walkable slope, tools/player_hull.py, set to the openmw values while
it builds; a ramp it makes is then never steeper than the engine stands on).

The check uses each rule set's step and walkable slope only; the step rules' third try over a short steep lip and
their deeper ground test are not in it (both only let more through), so its 'openmw' verdicts are on the safe side.
Nothing is walked and no game data is written: the output holds mesh paths and counts.

    step_rules_survey.py RUN --out DIR [--jobs N] [--limit N]
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

OPENMW_WALKABLE_Z = 0.69465837    # cos 46 degrees (quakedef.h AW_OPENMW_WALKABLE_Z)
RULES = {
    'quake': {'step': 8.5, 'walkable': 0.69},
    # check_flight stands on normal z >= walkable - 1e-3: shifted so it stands only over cos 46
    'openmw': {'step': 8.75, 'walkable': OPENMW_WALKABLE_Z + 1e-3},
}
METHODS = ('m0', 'm1', 'm1r')


def _measure(task):
    import numpy as np
    from mwad.scene import read_asset, unpack_geometry
    from exterior_visibility import apply_exterior_selection
    import stair_mesh
    from stair_mesh_survey import chim_profile
    m, surface_table = task
    rec = m['record']
    out = {'source': m['source'], 'key': m['key'], 'placements': m['placements']}
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
        groups = stair_mesh.flights(v, vis_f) if len(vis_f) else []
        out['flights'] = len(groups)
        if not groups:
            return out
        profile = chim_profile(m['source'], rec['triangles'], m['group_profile'], surface_table)
        if (rec.get('source_collision') or {}).get('mode') == 'nonsolid':
            profile['collision_none'] = True
        tris = stair_mesh._tris(v, vis_f)
        import player_hull
        for method, prof in (('m0', profile), ('m1', dict(profile, stair_collision='mesh')),
                             ('m1r', dict(profile, stair_collision='mesh'))):
            saved = player_hull.STEP_HEIGHT, player_hull.WALKABLE_Z
            if method == 'm1r':
                player_hull.STEP_HEIGHT, player_hull.WALKABLE_Z = RULES['openmw']['step'], RULES['openmw']['walkable']
            try:
                pieces, _, _ = stair_mesh.collision_pieces(cv, cf, prof, visible=(v, vis_f))
            finally:
                player_hull.STEP_HEIGHT, player_hull.WALKABLE_Z = saved
            for name, rule in RULES.items():
                found = [stair_mesh.check_flight(pieces, tris, ids, step=rule['step'], walkable=rule['walkable'])
                         for ids in groups]
                out['%s_%s' % (method, name)] = {
                    'flights_failing': sum(1 for x in found if x),
                    'checks_failing': sorted({y['check'] for x in found for y in x})}
    except Exception as error:      # reported with its reason, never skipped silently
        out['error'] = '%s: %s' % (type(error).__name__, error)
    return out


def summary(results):
    """Counts per method and rule set: meshes with flights, meshes whose flights all pass, and the names of the rest."""
    rows = [r for r in results if r.get('flights') and 'error' not in r]
    out = {'flight_meshes': len(rows), 'errors': sorted(r['source'] for r in results if 'error' in r)}
    for method in METHODS:
        for name in RULES:
            k = '%s_%s' % (method, name)
            failing = sorted(r['source'] for r in rows if r[k]['flights_failing'])
            out[k] = {'pass': len(rows) - len(failing), 'fail': len(failing), 'failing': failing}
    for method in METHODS:
        q, o = '%s_quake' % method, '%s_openmw' % method
        out['%s_changed' % method] = {
            'pass_only_openmw': sorted(r['source'] for r in rows if r[q]['flights_failing'] and not r[o]['flights_failing']),
            'pass_only_quake': sorted(r['source'] for r in rows if r[o]['flights_failing'] and not r[q]['flights_failing'])}
    return out


def main(argv=None):
    import stair_mesh_survey as sms
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('run')
    ap.add_argument('--out', required=True)
    ap.add_argument('--jobs', type=int, default=os.cpu_count())
    ap.add_argument('--limit', type=int, default=0, help='measure at most this many meshes (0: all)')
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    from chim.build import hull_surface_table
    surface_table = hull_surface_table()
    t0 = time.perf_counter()
    frames = sms.scan_frames(a.run)
    meshes = {}
    with ProcessPoolExecutor(a.jobs) as pool:
        for _, models in pool.map(sms._frame_models, frames, chunksize=8):
            for x in models:
                if x['key'] in meshes:
                    meshes[x['key']]['placements'] += x['placements']
                else:
                    meshes[x['key']] = x
    items = sorted(meshes.values(), key=lambda x: -x['record'].get('triangles', 0))
    if a.limit:
        items = items[:a.limit]
    print('[step-rules] %d frames, %d distinct meshes; checking on %d workers' % (len(frames), len(items), a.jobs),
          flush=True)
    with ProcessPoolExecutor(a.jobs) as pool:
        results = list(pool.map(_measure, [(x, surface_table) for x in items], chunksize=1))
    report = {'format': 1, 'run': str(a.run), 'frames': len(frames), 'distinct_meshes': len(meshes), 'rules': RULES,
              'wall_s': round(time.perf_counter() - t0, 1), 'jobs': a.jobs, 'summary': summary(results),
              'meshes': [r for r in results if r.get('flights') or 'error' in r]}
    path = out / 'step-rules-survey.json'
    path.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    s = report['summary']
    for method in METHODS:
        for name in RULES:
            k = '%s_%s' % (method, name)
            print('[step-rules] %s: %d of %d flight meshes pass' % (k, s[k]['pass'], s['flight_meshes']), flush=True)
    print('[step-rules] done in %.1f s: %s' % (report['wall_s'], path), flush=True)


if __name__ == '__main__':
    main()
