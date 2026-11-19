# SPDX-License-Identifier: GPL-3.0-only
"""The surface check of the creature library's models against their source meshes (CREATURE-RACER-HOLES-67;
CREATURE-MESH-HOLES-62 and CREATURE-RACER-MESH-SPIKE-58 are the earlier cases).

Every model the library bakes (standing models, skeletal or kf; corpses aside) is compared, in the idle's first pose,
with its source mesh posed the same way (halloween_cast.creature_shapes, Quake units): the model's first frame (a
skeletal model's rest frame is quantised in the pose box the engine draws every pose in, so a coarse box shows here as
it shows in the game). Per model: its triangles against the source's, the share of the source's surface within
TOLERANCE of the model's (samples every SPACING units, tools/drawn_collision.sample_triangles), the box's largest
step, and the shapes whose surface the model lost by the reduction check of the kf route (npc_geometry.lost_shapes:
samples farther than 5 % of the model's size from any baked face).

A model whose gallery profile says 'whole' must be whole: every source triangle, at least WHOLE_COVERAGE of the
source's surface within TOLERANCE, no shape lost; otherwise the library stage stops (the cliff racer was baked at 474
of its 965 triangles for five builds, unseen by any check). The other models are reported (the creature library's
report 'surface_check'). Measured on the v0.0.67-dev2 library: the racer 474 of 965 triangles, 66 % of its source's
surface within half a unit; on the whole route 965 of 965 and 100 %.
"""
import numpy as np

TOLERANCE = 1.0         # Quake units
SPACING = 0.5           # Quake units between samples
WHOLE_COVERAGE = 0.99


def read_alias(raw):
    """(first frame positions (n, 3) in model units, faces (m, 3), skin size) of an alias model (npc_geometry.animated_mdl's
    layout; a skeletal model's rest frame)."""
    import struct
    h = struct.unpack_from('<4si3f3ff3f8if', raw, 0)
    scale, origin = np.array(h[2:5]), np.array(h[5:8])
    w, hh, nv, nt = h[13], h[14], h[15], h[16]
    at = 84 + 4 + w * hh + 12 * nv
    faces = np.array(struct.unpack_from('<%di' % (4 * nt), raw, at)).reshape(nt, 4)[:, 1:]
    at += 16 * nt + 4 + 8 + 16
    xyz = np.frombuffer(raw, np.uint8, 4 * nv, at).reshape(nv, 4)[:, :3].astype(float)
    return xyz * scale + origin, faces, (w, hh), scale


def source_shapes(data, mesh, biped):
    """The source mesh's visible shapes posed at its idle's first time (halloween_cast.creature_shapes)."""
    import creature_library
    import creature_tables as T
    import halloween_cast
    from prepare_scenery import nif_reader
    creature_library.layered_assets(data)
    assets = T._open(data)
    N = nif_reader()
    rig = T.open_rig(N, assets.read, mesh, biped)
    idle = rig.window('idle')
    if idle is None:
        raise ValueError('no idle group')
    source, start, _ = idle
    shapes = halloween_cast.creature_shapes(N, rig.raw, halloween_cast.RigSkeleton(rig, source).pose, [start],
                                            assets)[0]
    effects = {e['shape'] for e in T.effect_shapes(N, rig.raw)}
    return [s for s in shapes if s['name'] not in effects]


def coverage(source_tris, pos, faces, tolerance=TOLERANCE, spacing=SPACING):
    """The share of the source triangles' surface (n x 3 x 3) within TOLERANCE of the model's (POS, FACES)."""
    from drawn_collision import sample_triangles
    from scipy.spatial import cKDTree
    a, _ = sample_triangles(source_tris, spacing)
    b, _ = sample_triangles(np.asarray(pos, float)[np.asarray(faces)], spacing)
    if not len(a):
        return 1.0
    if not len(b):
        return 0.0
    d, _ = cKDTree(b).query(a, distance_upper_bound=tolerance)
    return float(np.isfinite(d).mean())


def problems(row):
    """The reasons a model stops the stage: only a whole-profile model's (fewer triangles than its source, its source's
    surface under WHOLE_COVERAGE, a shape whose surface it lost)."""
    out = []
    if row.get('whole'):
        if row['triangles'] < row['source_triangles']:
            out.append('%d of its %d source triangles' % (row['triangles'], row['source_triangles']))
        if row['coverage'] < WHOLE_COVERAGE:
            out.append('%.1f %% of the source surface within %.1f units (at least %.0f %%)' % (
                100 * row['coverage'], TOLERANCE, 100 * WHOLE_COVERAGE))
        if row['lost_shapes']:
            out.append('surface lost on %s' % ', '.join(row['lost_shapes']))
    return out


def check(task):
    """Worker: (key, row or None, error) of one model: task (key, data, mesh, model bytes, biped, whole)."""
    from npc_geometry import lost_shapes
    key, data, mesh, raw, biped, whole = task
    try:
        shapes = source_shapes(data, mesh, biped)
        pos, faces, _skin, step = read_alias(raw)
        source = np.concatenate([s['positions'][0][np.asarray(s['faces'])] for s in shapes])
        row = {'triangles': int(len(faces)), 'source_triangles': int(sum(len(s['faces']) for s in shapes)),
               'coverage': round(coverage(source, pos, faces), 4), 'box_step': round(float(np.max(step)), 3),
               'lost_shapes': sorted(lost_shapes(shapes, pos, faces)), 'whole': bool(whole)}
        row['problems'] = problems(row)
        return key, row, None
    except Exception as error:  # noqa: BLE001 (a model the check cannot read is reported, not a stop)
        return key, None, '%s: %s' % (type(error).__name__, error)


def check_library(data, done, id1, bipedal, whole, jobs=1, log=print):
    """{'rows': {key: row}, 'unchecked': {key: why}, 'stops': [lines]} of the library's standing models DONE ({key:
    record}, files written under ID1): WHOLE the meshes whose profile says whole (a problem of theirs is a stop)."""
    from pathlib import Path
    from build_jobs import resolve_jobs
    from build_parallel import ordered_map
    tasks = []
    for key, record in sorted(done.items()):
        if record.get('corpse') or '@' in key:
            continue
        path = Path(id1) / record['model']
        if not path.is_file():
            continue
        mesh = key
        tasks.append((key, data, mesh, path.read_bytes(), bool((bipedal or {}).get(mesh)), mesh in whole))
    out = {'rows': {}, 'unchecked': {}, 'stops': [], 'tolerance_units': TOLERANCE,
           'rule': 'creature_surface: a whole-profile model keeps every source triangle and its surface'}
    if not tasks:
        return out
    workers = min(resolve_jobs(jobs), len(tasks))
    wanted = {task[0] for task in tasks if task[5]}
    # largest model first (its bytes: faces and vertices), so the big creatures do not form the tail
    for key, row, error in ordered_map(check, tasks, workers, cost=lambda task: len(task[3])):
        if row is None:
            out['unchecked'][key] = error
            if key in wanted:
                out['stops'].append('%s: the check could not read it (%s)' % (key, error))
            continue
        out['rows'][key] = row
        if row['problems']:
            out['stops'].append('%s: %s' % (key, '; '.join(row['problems'])))
    low = sorted(out['rows'].items(), key=lambda kv: kv[1]['coverage'])[:6]
    log('Creature library: surface check of %d models: the lowest source coverage %s; shapes lost on %d models; '
        '%d not checked' % (len(out['rows']), ', '.join('%s %.0f %%' % (k, 100 * r['coverage']) for k, r in low),
                            sum(1 for r in out['rows'].values() if r['lost_shapes']), len(out['unchecked'])),
        flush=True)
    return out
