#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Rock shell audit: do the CHIM rocks keep the shells of the original rocks? (CHIM-ROCKS-OPEN-SHELLS-43)

Most Morrowind rock meshes are one-sided shells that are open where the original buries them: the bottom of a
boulder, the inner side of each rock of a rock cluster (terrain_rocks_*: up to ten open cups). None of them asks
for two-sided drawing (no NiStencilProperty; OpenMW turns face culling off only for draw mode "both",
components/nifosg/nifloader.cpp), so the original shows them closed only because the open rims sit below the
ground. A CHIM rock can therefore open up in four ways, and this audit measures each one, island-wide, for every
rock mesh (world_scenery.scenery_kind 'rock'):

1. two-sidedness: a rock whose source draws both sides (draw mode 3) while the converter keeps one-sided winding
   (prepare_scenery.model_geometry 'runtime_policy');
2. lost or turned faces: the stored CHIM model of an unreduced rock must cover the source surface facing the same
   way (sampled source points within TOLERANCE of a stored face whose plane normal points the same side);
3. the placement turn: the rims must stay buried with the converter's rotation (prepare_scenery.reference_rotation,
   Z then Y then X, the order of OpenMW's Misc::Convert::makeOsgQuat); the audit also scores the other orders, so
   a wrong turn shows as a better score for another order;
4. moved rims: the rims of the STORED models, placed as the engine places them (CHIM placement origin and yaw,
   chim.cut.rotation), against the CHIM chunk terrain, compared per mesh with the source rims against the original
   LAND heights. A mesh whose CHIM rims stand above the ground clearly more often than the original's opened up in
   conversion (reduction pulling a rim up).

Usage (inside the builder image; game data and a CHIM world are read only):
  rock_shell_audit.py audit --data-files DIR --world RUN/chim-world --out REPORT.json [--jobs N]
  rock_shell_audit.py check --report REPORT.json [--known config/rock-shell-known.json]
"""
import argparse
import collections
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

FORMAT = 'amiwind-rock-shell-audit-1'
KNOWN = Path(__file__).resolve().parents[1] / 'config/rock-shell-known.json'
TOLERANCE = 0.35          # local units (1.4 source units): a stored face this close covers a source sample
COVER_LIMIT = 0.01        # an unreduced stored rock may miss or turn at most this share of the source area
GROUND_MARGIN = 1.0       # local units (4 source units) above the ground before a rim sample counts as exposed
EXPOSURE_LIMIT = 0.05     # CHIM rims exposed more than the original's by this share = opened in conversion
MIN_PLACEMENTS = 5        # ... over at least this many compared placements
RIM_STEPS = (.1, .3, .5, .7, .9)
CONVERTER_TURN = 'converter (Z, then Y, then X)'
VARIANTS_PER_MESH = 4     # stored variants compared with the source per mesh (most placed, plus a tilted one)


# ---------------------------------------------------------------- geometry (pure, unit tested)

def is_rock(stem):
    """The rock formations of the open-world converter (world_scenery.scenery_kind)."""
    stem = stem.casefold()
    return 'rock' in stem or 'boulder' in stem or stem in ('terrain_ma_20', 'terrain_ma_30')


def shell_edges(vertices, faces, decimals=2):
    """Welded triangle soup facts: (points, open edges, non-manifold edges, flipped edges). A flipped edge is
    shared by two triangles that run it the same way (one of them is wound against its neighbour)."""
    import numpy as np
    points, inverse = np.unique(np.round(np.asarray(vertices, float)[:, :3], decimals), axis=0, return_inverse=True)
    tris = inverse.reshape(-1)[np.asarray(faces, int)[:, :3]]
    undirected, directed = collections.Counter(), collections.Counter()
    for t in tris:
        for i in range(3):
            a, b = int(t[i]), int(t[(i + 1) % 3])
            if a != b:
                undirected[(min(a, b), max(a, b))] += 1
                directed[(a, b)] += 1
    open_edges = [e for e, n in undirected.items() if n == 1]
    nonmanifold = [e for e, n in undirected.items() if n > 2]
    flipped = [e for e, n in undirected.items() if n == 2 and 2 in (directed[e], directed[(e[1], e[0])])]
    return points, open_edges, nonmanifold, flipped


def polygon_open_edges(polygons, decimals=2, eps=0.02):
    """(points, open edges) of a polygon soup (stored BSP faces). Merged faces leave T-junctions (a neighbour's
    vertex in the middle of a merged edge), so every edge is split at the welded vertices lying on it first."""
    import numpy as np
    polygons = [np.asarray(p, float) for p in polygons if len(p) >= 3]
    if not polygons:
        return np.zeros((0, 3)), []
    points, inverse = np.unique(np.round(np.concatenate(polygons), decimals), axis=0, return_inverse=True)
    inverse = inverse.reshape(-1)
    segments = []
    at = 0
    for p in polygons:
        ids = inverse[at:at + len(p)]
        at += len(p)
        for i in range(len(ids)):
            a, b = int(ids[i]), int(ids[(i + 1) % len(ids)])
            if a == b:
                continue
            d = points[b] - points[a]
            t = ((points - points[a]) @ d) / float(d @ d)
            off = np.linalg.norm(points[a] + t[:, None] * d - points, axis=1)
            inner = np.flatnonzero((t > 1e-4) & (t < 1 - 1e-4) & (off < eps))
            chain = [a] + [int(k) for k in inner[np.argsort(t[inner])]] + [b]
            segments += [(min(x, y), max(x, y)) for x, y in zip(chain, chain[1:])]
    count = collections.Counter(segments)
    return points, [e for e, n in count.items() if n == 1]


def rim_samples(points, edges):
    """Sample points along open edges (RIM_STEPS per edge)."""
    import numpy as np
    if not edges:
        return np.zeros((0, 3))
    t = np.array(RIM_STEPS)
    return np.concatenate([points[a] * (1 - t)[:, None] + points[b] * t[:, None] for a, b in edges])


def edge_length(points, edges):
    import numpy as np
    return float(sum(np.linalg.norm(points[a] - points[b]) for a, b in edges))


def coverage(source_tris, stored_tris, stored_normals, tolerance=TOLERANCE):
    """Area shares of the source surface the stored faces cover facing the same way ('same'), only facing the
    other way ('turned') or not at all ('missing'). source_tris (n, 3, 3) in the stored model's frame; stored_tris
    (m, 3, 3) with the plane normal of each stored face (Quake faces are wound clockwise, so the plane, not the
    vertex order, says which side is the front)."""
    import numpy as np
    from scipy.spatial import cKDTree
    from seam_audit import _pair_distance
    source_tris = np.asarray(source_tris, float)
    stored_tris = np.asarray(stored_tris, float)
    stored_normals = np.asarray(stored_normals, float)
    bary = np.array([[1 / 3, 1 / 3, 1 / 3], [.6, .2, .2], [.2, .6, .2], [.2, .2, .6]])
    samples = np.einsum('kj,ijd->ikd', bary, source_tris).reshape(-1, 3)
    cross = np.cross(source_tris[:, 1] - source_tris[:, 0], source_tris[:, 2] - source_tris[:, 0])
    area = np.linalg.norm(cross, axis=1) / 2
    normals = np.repeat(cross / np.maximum(2 * area[:, None], 1e-12), len(bary), axis=0)
    k = min(24, len(stored_tris))
    _, idx = cKDTree(stored_tris.mean(axis=1)).query(samples, k=k)
    idx = np.asarray(idx).reshape(len(samples), k)
    near = stored_tris[idx]
    dist = _pair_distance(samples[:, None, :], near[:, :, 0], near[:, :, 1], near[:, :, 2])
    dots = np.einsum('ikd,id->ik', stored_normals[idx], normals)
    close = dist < tolerance
    same = (close & (dots > .3)).any(axis=1)
    turned = (close & (dots < -.3)).any(axis=1) & ~same
    weight = np.repeat(area / len(bary), len(bary))
    total = max(float(weight.sum()), 1e-12)
    return {'same': round(float(weight[same].sum() / total), 4),
            'turned': round(float(weight[turned].sum() / total), 4),
            'missing': round(float(weight[~same & ~turned].sum() / total), 4)}


def axis_rotation(axis, angle):
    import numpy as np
    c, s = math.cos(angle), math.sin(angle)
    return {'x': np.array([[1, 0, 0], [0, c, -s], [0, s, c]]),
            'y': np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]),
            'z': np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])}[axis]


def candidate_rotations():
    """{label: rotation_radians -> 3x3}: the converter's turn and the three other readings a wrong angle
    calculation would give (other order, other sign). The authored placements bury the rims best with the right
    one."""
    from prepare_scenery import reference_rotation
    r = axis_rotation
    return {
        CONVERTER_TURN: lambda a: reference_rotation({'rotation_radians': list(a)}),
        'other order (X, then Y, then Z)': lambda a: r('z', -a[2]) @ r('y', -a[1]) @ r('x', -a[0]),
        'other sign': lambda a: r('x', a[0]) @ r('y', a[1]) @ r('z', a[2]),
        'other order and sign': lambda a: r('z', a[2]) @ r('y', a[1]) @ r('x', a[0]),
    }


def land_heights(lands):
    """Vectorised height(x, y) over original LAND cells {(cx, cy): 65x65 heights} (bilinear inside a quad;
    nan where no LAND)."""
    import numpy as np

    def height(x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        cx, cy = np.floor(x / 8192).astype(int), np.floor(y / 8192).astype(int)
        out = np.full(len(x), np.nan)
        for key in set(zip(cx.tolist(), cy.tolist())):
            h = lands.get(key)
            if h is None:
                continue
            sel = (cx == key[0]) & (cy == key[1])
            fx, fy = (x[sel] - key[0] * 8192) / 128, (y[sel] - key[1] * 8192) / 128
            i, j = np.minimum(fx.astype(int), 63), np.minimum(fy.astype(int), 63)
            u, v = fx - i, fy - j
            out[sel] = (h[j, i] * (1 - u) * (1 - v) + h[j, i + 1] * u * (1 - v) + h[j + 1, i] * (1 - u) * v
                        + h[j + 1, i + 1] * u * v)
        return out
    return height


def triangle_ground(triangles, cell=64.0):
    """height(x, y) -> highest ground triangle at x, y (None outside): the CHIM chunk terrain faces."""
    import numpy as np
    tris = np.asarray(triangles, float)
    grid = collections.defaultdict(list)
    lo, hi = tris[:, :, :2].min(1), tris[:, :, :2].max(1)
    for i in range(len(tris)):
        for gx in range(int(math.floor(lo[i, 0] / cell)), int(math.floor(hi[i, 0] / cell)) + 1):
            for gy in range(int(math.floor(lo[i, 1] / cell)), int(math.floor(hi[i, 1] / cell)) + 1):
                grid[(gx, gy)].append(i)

    def height(x, y):
        best = None
        for i in grid.get((int(math.floor(x / cell)), int(math.floor(y / cell))), ()):
            a, b, c = tris[i]
            v0, v1 = b[:2] - a[:2], c[:2] - a[:2]
            det = v0[0] * v1[1] - v0[1] * v1[0]
            if abs(det) < 1e-9:
                continue
            wx, wy = x - a[0], y - a[1]
            u = (wx * v1[1] - wy * v1[0]) / det
            v = (v0[0] * wy - v0[1] * wx) / det
            if u >= -1e-6 and v >= -1e-6 and u + v <= 1 + 1e-6:
                z = a[2] + u * (b[2] - a[2]) + v * (c[2] - a[2])
                best = z if best is None else max(best, z)
        return best
    return height


def exposed(world_points, height, margin):
    """(exposed, measured): rim samples more than margin above the ground, of those with ground under them."""
    n = total = 0
    for x, y, z in world_points:
        g = height(x, y)
        if g is None or g != g:
            continue
        total += 1
        n += z > g + margin
    return int(n), int(total)


# ---------------------------------------------------------------- data (game files and a CHIM world)

def parse_variant(name):
    """{stem, scale, rotation, flattened, offset} of a CHIM model name (chim.build.variant_name)."""
    import re
    m = re.match(r'^(.*?)@s([0-9.e+-]+)(?:@t([^@]+))?(@f[^@]+)?(?:@v([^@]+))?$', name.split('#')[0])
    if not m:
        return None
    stem, scale, tilt, flattened, offset = m.groups()
    rotation = [float(x) for x in tilt.split(',')] if tilt else []
    return {'stem': stem, 'scale': float(scale), 'rotation': (rotation + [0., 0., 0.])[:3],
            'flattened': bool(flattened), 'offset': [float(x) for x in offset.split(',')] if offset else [0., 0., 0.]}


def stored_frame(variant):
    """Source points (source units) -> the stored model's frame (chim.models.variant_unit: scale and tilt baked
    in, the yaw of an untilted variant left to the entity)."""
    import numpy as np
    rot = variant['rotation']
    tilted = any(abs(math.sin(a)) > 1e-7 or math.cos(a) < 0 for a in rot[:2])
    if tilted:
        yaw = axis_rotation('z', -rot[2])
        r = yaw.T @ candidate_rotations()[CONVERTER_TURN](rot)
    else:
        r = np.eye(3)
    delta = r @ np.array(variant['offset']) * variant['scale']
    return lambda p: (np.asarray(p, float) * .25) @ r.T * variant['scale'] + delta


def stored_faces(image):
    """[(polygon, plane normal)] of a stored model (chim.validate.face_polygons)."""
    from chim import format as F
    from chim.validate import face_polygons
    import numpy as np
    return [(np.asarray(p, float), np.asarray(n, float)) for p, n, _, _ in face_polygons(F.read_brush_image(image))
            if len(p) >= 3]


def triangles_of(faces):
    import numpy as np
    tris, normals = [], []
    for p, n in faces:
        for k in range(1, len(p) - 1):
            tris.append((p[0], p[k], p[k + 1]))
            normals.append(n)
    return np.array(tris, float).reshape(-1, 3, 3), np.array(normals, float).reshape(-1, 3)


_STATE = {}


def _mesh_worker(task):
    """Source facts, two-sidedness, stored-model coverage and the original rims' exposure of one rock mesh."""
    import numpy as np
    model, variants, placements, data_files, world = task
    from prepare_scenery import nif_reader, model_geometry
    from mwad.scene import unpack_geometry
    from world_estimate_data import MeshSource
    from chim import format as F
    if 'source' not in _STATE:
        _STATE['source'] = MeshSource(data_files)
        _STATE['land'] = land_heights(original_lands(data_files))
        _, files, models, _ = F.read_index((Path(world) / 'chim/world.cwi').read_bytes())
        _STATE['index'] = (files, models)
    row = {'model': model, 'placements': len(placements)}
    try:
        raw, _ = _STATE['source'].read(model)
        packet, materials, _, _ = model_geometry(raw, nif_reader(), repair_uv=True)
        vv, ff, _ = unpack_geometry(packet)
        v, f = np.array(vv, float), np.array(ff, int)
    except Exception as exc:  # noqa: BLE001 - reported, not audited
        row['status'] = 'unreadable: %s' % str(exc)[:120]
        return row
    row['status'] = 'ok'
    from town_regions import visual_profile
    # the CHIM converter's reduction of this mesh (town and CHIM areas: terrain_rock_* to 64 triangles)
    row['reduced'] = visual_profile(model, len(f)).get('ratio', 1) < 1
    points, open_edges, nonmanifold, flipped = shell_edges(v, f)
    row.update(triangles=int(len(f)), open_edges=len(open_edges), open_length=round(edge_length(points, open_edges), 1),
               nonmanifold_edges=len(nonmanifold), flipped_edges=len(flipped),
               draw_modes=dict(collections.Counter(m['source_visibility']['draw_mode_name'] for m in materials)),
               two_sided=any(m['source_visibility']['draw_mode'] == 3 for m in materials))
    # 3: the original rims against the original LAND, with every candidate turn
    samples = rim_samples(points, open_edges)
    height = _STATE.get('land')
    row['original_exposure'] = {}
    row['original_refs'] = {}
    if len(samples) and height is not None:
        for label, turn in candidate_rotations().items():
            n = total = 0
            for p in placements:
                w = samples @ turn(p['r']).T * p['s'] + np.array(p['p'])
                g = height(w[:, 0], w[:, 1])
                ok = ~np.isnan(g)
                e = int((w[ok, 2] > g[ok] + GROUND_MARGIN * 4).sum())
                n += e
                total += int(ok.sum())
                if label == CONVERTER_TURN and ok.any():
                    row['original_refs'][str(p['n'])] = [e, int(ok.sum())]
            row['original_exposure'][label] = round(n / max(total, 1), 4)
    # 2: stored variants against the source
    files, models = _STATE['index']
    tris = v[f[:, :3], :3]
    row['variants'] = []
    for var in variants:
        out = dict(var)
        parsed = parse_variant(var['name'])
        entry = models[var['id']]
        if parsed is None or parsed['flattened'] or entry['name'] != var['name']:
            out['skip'] = 'flattened or unparsed'
            row['variants'].append(out)
            continue
        with open(Path(world) / 'chim' / files[entry['file']]['path'], 'rb') as fh:
            fh.seek(entry['offset'])
            faces = stored_faces(fh.read(entry['bytes']))
        out['stored_faces'] = len(faces)
        if faces:
            st, sn = triangles_of(faces)
            out['coverage'] = coverage(stored_frame(parsed)(tris), st, sn)
            pts, edges = polygon_open_edges([p for p, _ in faces])
            out['stored_open_length'] = round(edge_length(pts, edges) / (.25 * parsed['scale']), 1)
        row['variants'].append(out)
    return row


def _frame_worker(task):
    """Rims of the stored rock models placed in one CHIM frame against its chunk terrain."""
    import numpy as np
    world, index = task
    from chim.validate import load_frame
    from chim.cut import rotation
    from chim import format as F
    from chim.validate import face_polygons
    (_, frame, chunks), models = load_frame(world, index)
    rims = _STATE.setdefault('rims', {})
    rows, height = [], None
    for c in chunks:
        for r in c['owned']:
            m = models.get(r['model'])
            if m is None or not is_rock(m['name'].split('@')[0].rsplit('/', 1)[-1]):
                continue
            if height is None:
                ground = []
                for k in chunks:
                    if not k.get('image'):
                        continue
                    for p, n, _, _ in face_polygons(F.read_brush_image(k['image'])):
                        if len(p) >= 3 and n[2] >= .2:
                            ground += [(p[0], p[j], p[j + 1]) for j in range(1, len(p) - 1)]
                height = triangle_ground(ground) if ground else (lambda x, y: None)
            if r['model'] not in rims:
                if len(rims) > 4000:
                    rims.clear()
                rims[r['model']] = rim_samples(*polygon_open_edges([p for p, _ in stored_faces(m['image'])]))
            s = rims[r['model']]
            if len(s):
                e, t = exposed(s @ rotation(r['yaw']).T + np.array(r['origin']), height, GROUND_MARGIN)
                rows.append((m['name'].split('@')[0], r['ref'] & 0xffffff, e, t))
    return rows


def original_lands(data_files):
    """{(cx, cy): 65x65 heights} of every master's LAND records (later masters win)."""
    from world_estimate_data import MASTERS, parse_master
    from mwad.paths import child_ci
    lands = {}
    for name in MASTERS:
        path = child_ci(Path(data_files), name, required=False)
        if path is not None and path.is_file():
            lands.update(parse_master(path)['lands'])
    return lands


def audit(data_files, world, jobs=None, progress=print):
    from build_jobs import resolve_jobs
    from build_parallel import ordered_map
    from world_estimate_data import MASTERS, parse_master
    from world_scenery import scenery_kind
    from mwad.paths import child_ci
    from chim import format as F
    jobs = resolve_jobs(jobs)
    objects, placed = {}, collections.defaultdict(list)
    for name in MASTERS:
        path = child_ci(Path(data_files), name, required=False)
        if path is None or not path.is_file():
            continue
        m = parse_master(path)
        objects.update(m['objects'])
        for cell in m['cells']:
            if cell['interior']:
                continue
            for r in cell['refs']:
                o = objects.get(r['id'])
                if r.get('del') or 'p' not in r or not o or o.get('deleted') or not o.get('model'):
                    continue
                if scenery_kind(r['id'], {'type': o['type'], 'model': o['model']}) == 'rock':
                    placed[o['model']].append({k: r[k] for k in ('n', 'p', 'r', 's')})
    stats = json.loads((Path(world) / 'chim-stats.json').read_text(encoding='utf-8'))
    variants = collections.defaultdict(list)
    for m in stats['models']['per_model']:
        base = m['name'].split('@')[0]
        if is_rock(base.rsplit('/', 1)[-1]):
            variants['meshes/' + base + '.nif'].append({k: m[k] for k in ('name', 'id', 'placements', 'faces')})
    del stats
    tasks = []
    for model in sorted(set(placed) | set(variants)):
        vs = sorted(variants.get(model, []), key=lambda x: -x['placements'])
        chosen = vs[:VARIANTS_PER_MESH - 1] + [x for x in vs[VARIANTS_PER_MESH - 1:] if '@t' in x['name']][:1]
        tasks.append((model, chosen, placed.get(model, []), str(data_files), str(world)))
    rows = []
    for i, row in enumerate(ordered_map(_mesh_worker, tasks, jobs, cost=lambda t: len(t[2]) + 1)):
        row['stored_variants'] = len(variants.get(row['model'], []))
        rows.append(row)
        if progress and (i % 40 == 0 or i == len(tasks) - 1):
            progress('rock shells: mesh %d/%d %s' % (i + 1, len(tasks), row['model']))
    _, files, _, _ = F.read_index((Path(world) / 'chim/world.cwi').read_bytes())
    frames = list(range(sum(1 for f in files if f['kind'] == b'FRAM')))
    chim = {}
    for i, found in enumerate(ordered_map(_frame_worker, [(str(world), k) for k in frames], jobs)):
        for base, ref, e, t in found:
            if t and (ref not in chim or t > chim[ref][2]):
                chim[ref] = (base, e, t)
        if progress and (i % 100 == 0 or i == len(frames) - 1):
            progress('rock shells: frame %d/%d' % (i + 1, len(frames)))
    return summarise(rows, chim)


def summarise(rows, chim):
    """Per mesh: the CHIM rims' mean exposure next to the original's over the placements both measure."""
    by_model = {'meshes/' + base + '.nif': [] for base, _, _ in chim.values()}
    for ref, (base, e, t) in chim.items():
        by_model['meshes/' + base + '.nif'].append((ref, e / t))
    total = [0, 0., 0.]
    for row in rows:
        orig = row.pop('original_refs', {})
        pairs = [(share, orig[str(ref)][0] / orig[str(ref)][1]) for ref, share in by_model.get(row['model'], [])
                 if str(ref) in orig and orig[str(ref)][1]]
        if pairs:
            row['rim_exposure'] = {'compared': len(pairs), 'chim': round(sum(p[0] for p in pairs) / len(pairs), 4),
                                   'original': round(sum(p[1] for p in pairs) / len(pairs), 4)}
            total[0] += len(pairs)
            total[1] += sum(p[0] for p in pairs)
            total[2] += sum(p[1] for p in pairs)
    best = collections.Counter()
    for row in rows:
        exp = row.get('original_exposure') or {}
        if exp:
            best[min(exp, key=exp.get)] += 1
    return {'format': FORMAT, 'meshes': len(rows),
            'two_sided_meshes': sorted(r['model'] for r in rows if r.get('two_sided')),
            'best_turn_per_mesh': dict(best),
            'rim_exposure': {'compared': total[0], 'chim': round(total[1] / max(total[0], 1), 4),
                             'original': round(total[2] / max(total[0], 1), 4)},
            'rows': rows}


def check(report, known=None):
    """Failures: a two-sided rock drawn one-sided; an unreduced stored rock that misses or turns more than
    COVER_LIMIT of its source; a mesh whose CHIM rims stand above the ground more than EXPOSURE_LIMIT more often
    than the original's (unless a known, registered finding no worse than recorded); another rotation reading
    burying the original rims best on more meshes than the converter's."""
    known = known or {}
    failures = []
    for row in report['rows']:
        model = row['model']
        if row.get('two_sided'):
            failures.append({'model': model, 'reason': 'source draws both sides; the converter keeps one side'})
        for v in row.get('variants', []):
            c = v.get('coverage')
            if c and not row.get('reduced') and (c['missing'] > COVER_LIMIT or c['turned'] > COVER_LIMIT):
                failures.append({'model': model, 'variant': v['name'],
                                 'reason': 'stored model misses %.1f %% / turns %.1f %% of the source' % (
                                     100 * c['missing'], 100 * c['turned'])})
        exp = row.get('rim_exposure')
        if exp and exp['compared'] >= MIN_PLACEMENTS:
            extra = exp['chim'] - exp['original']
            k = known.get(model)
            if extra > EXPOSURE_LIMIT and (k is None or extra > k['extra'] + .02):
                failures.append({'model': model, 'reason': 'rims above the ground %.1f %% more often than the '
                                 'original%s' % (100 * extra, '' if k is None else ' (more than recorded, %s)'
                                                 % k.get('bug', '?'))})
    turns = report.get('best_turn_per_mesh') or {}
    if turns and max(turns, key=turns.get) != CONVERTER_TURN:
        failures.append({'model': '(all rocks)', 'reason': 'another rotation reading buries the rims best: %s' % turns})
    return failures


def load_known(path=KNOWN):
    path = Path(path)
    if not path.is_file():
        return {}
    return {row['model']: row for row in json.loads(path.read_text(encoding='utf-8')).get('known', [])}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('audit')
    a.add_argument('--data-files', type=Path, required=True)
    a.add_argument('--world', type=Path, required=True, help='a CHIM world stage folder (chim-world)')
    a.add_argument('--out', type=Path, required=True)
    a.add_argument('--jobs', type=int)
    a.add_argument('--known', type=Path, default=KNOWN)
    c = sub.add_parser('check')
    c.add_argument('--report', type=Path, required=True)
    c.add_argument('--known', type=Path, default=KNOWN)
    args = p.parse_args(argv)
    if args.cmd == 'audit':
        report = audit(args.data_files, args.world, args.jobs)
        args.out.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
        e = report['rim_exposure']
        print('Rock shells: %d meshes, %d two-sided; rims above ground: CHIM %.2f %%, original %.2f %% (%d placements)'
              % (report['meshes'], len(report['two_sided_meshes']), 100 * e['chim'], 100 * e['original'],
                 e['compared']))
        print('Best-burying turn per mesh: %s' % report['best_turn_per_mesh'])
    else:
        report = json.loads(args.report.read_text(encoding='utf-8'))
    failures = check(report, load_known(args.known))
    for f in failures:
        print('ROCK SHELL: %s%s: %s' % (f['model'], ' ' + f['variant'] if 'variant' in f else '', f['reason']))
    print('Rock shell check: %d failure(s)' % len(failures))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
