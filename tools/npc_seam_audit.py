#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Joint-seam audit of composed NPC appearances (docs/MODULAR_NPCS.md).

Body parts are separate meshes that meet at joints (neck/head, wrists, elbows,
knees, ankles, chest/groin) and clothing or armour rims sit over skin. The bake
reduces each part on its own; a reducer that moves a part's rim opens the joint
(the same mechanism as MESH-LOD-OPEN-SEAMS-33 on static meshes).

Metric (geometric, no rendering): from the posed, unreduced source shapes of an
appearance, a rim edge of one shape (an edge used by one triangle of it after
welding) is a joint edge when its midpoint lies within NEAR of another shape's
surface. Each joint edge gets an inset point on its own source triangle, INSET
in from the rim; the edge is open when that point lies farther than TOL from the
reduced model (all shapes): the part pulled back and nothing covers the strip.
Results: joint length, open length and share, the largest gap, per appearance
and per shape pair.

A second, view-based check renders source and reduced models from 16 directions
(orthographic, flat) and counts reduced-model pixels where the background shows
through inside the source silhouette (eroded by one pixel): holes, not outline.

Usage:
  npc_seam_audit.py audit --data-files DIR --gallery GALLERY_OUT --parts-store DIR --out REPORT.json
                          [--reference OTHER_GALLERY_OUT] [--views N] [--jobs N] [--limit N]
  npc_seam_audit.py check --report REPORT.json [--threshold 0.02] [--max-gap 0.5]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))

NEAR = 0.05        # Quake units: a rim this close to another part is a joint (actors are ~32 units tall)
TOL = 0.25         # Quake units: two 8-bit alias grid steps of a 32-unit actor
INSET = 0.5        # Quake units: inset points this far in from a joint rim must stay covered
DEFAULT_THRESHOLD = 0.02
DEFAULT_MAX_GAP = 0.75


def _pair_distance(p, a, b, c):
    """Exact distance from points p to triangles (a, b, c) (closest point on a triangle, Ericson)."""
    ab, ac = b - a, c - a
    ap, bp, cp = p - a, p - b, p - c
    d1, d2 = (ab * ap).sum(-1), (ac * ap).sum(-1)
    d3, d4 = (ab * bp).sum(-1), (ac * bp).sum(-1)
    d5, d6 = (ab * cp).sum(-1), (ac * cp).sum(-1)
    vc, vb, va = d1 * d4 - d3 * d2, d5 * d2 - d1 * d6, d3 * d6 - d5 * d4
    denom = va + vb + vc
    denom = np.where(np.abs(denom) < 1e-30, 1e-30, denom)
    q = a + ab * (vb / denom)[..., None] + ac * (vc / denom)[..., None]
    inside = (va >= 0) & (vb >= 0) & (vc >= 0)
    dist = np.where(inside, np.linalg.norm(p - q, axis=-1), np.inf)
    for s, e in ((a, b), (b, c), (c, a)):
        se = e - s
        t = np.clip(((p - s) * se).sum(-1) / np.maximum((se * se).sum(-1), 1e-30), 0, 1)
        dist = np.minimum(dist, np.linalg.norm(p - (s + se * t[..., None]), axis=-1))
    return dist


def point_triangle_distance(points, tris, tol):
    """Distance from each point to a triangle set: the 16 nearest centroids first, then all
    triangles for points still farther than tol (exact wherever the result is near tol)."""
    from scipy.spatial import cKDTree
    if not len(points):
        return np.zeros(0)
    k = min(16, len(tris))
    _, idx = cKDTree(tris.mean(axis=1)).query(points, k=k)
    near = tris[idx.reshape(len(points), k)]
    best = _pair_distance(points[:, None, :], near[:, :, 0], near[:, :, 1], near[:, :, 2]).min(axis=1)
    far = np.flatnonzero(best > tol)
    for start in range(0, len(far), 128):
        sel = far[start:start + 128]
        d = _pair_distance(points[sel, None, :], tris[None, :, 0], tris[None, :, 1], tris[None, :, 2])
        best[sel] = np.minimum(best[sel], d.min(axis=1))
    return best


def rim_edges(points, faces):
    """Rim edges (n, 2, 3) of one shape, welded by rounded position, and for each edge a point
    INSET into the shape: on its rim triangle, INSET units in from the edge midpoint (at most
    half way to the opposite corner)."""
    from collections import defaultdict
    welded, inverse = np.unique(np.round(points, 4), axis=0, return_inverse=True)
    tri = inverse.reshape(-1)[faces]
    owner = defaultdict(list)
    for t in tri:
        for i in range(3):
            owner[tuple(sorted((int(t[i]), int(t[(i + 1) % 3]))))].append(int(t[(i + 2) % 3]))
    edges = [(e, o[0]) for e, o in owner.items() if len(o) == 1]
    if not edges:
        return np.zeros((0, 2, 3)), np.zeros((0, 3))
    rims = welded[np.array([e for e, _ in edges], int)]
    mid = rims.mean(axis=1); towards = welded[[o for _, o in edges]] - mid
    length = np.linalg.norm(towards, axis=1)
    step = np.minimum(INSET, .5 * length) / np.maximum(length, 1e-12)
    return rims, mid + towards * step[:, None]


def joint_edges(shapes):
    """{(a, b): (rim edges of shape a lying on shape b, their inset points)} from the source."""
    out = {}
    tris = [s['points'][s['faces']] for s in shapes]
    for a, shape in enumerate(shapes):
        rims, inset = rim_edges(shape['points'], shape['faces'])
        if not len(rims):
            continue
        mid = rims.mean(axis=1)
        best = np.full(len(rims), np.inf); owner = np.full(len(rims), -1)
        for b, t in enumerate(tris):
            if b == a or not len(t):
                continue
            d = point_triangle_distance(mid, t, NEAR)
            take = d < best; best[take] = d[take]; owner[take] = b
        for b in set(owner[best <= NEAR].tolist()):
            sel = (best <= NEAR) & (owner == b)
            out[(a, b)] = (rims[sel], inset[sel])
    return out


def measure(shapes, reduced_tris):
    """Open joint length of one reduced model against its source shapes.

    A joint edge is open when its inset point (on the source surface, INSET in from the rim)
    lies farther than TOL from the reduced model: that part pulled back from the joint and no
    other part covers the strip. max_gap is the largest such distance, measured at the inset
    point: a lower bound of the opening (an opening of g units measures about g - INSET)."""
    joints = joint_edges(shapes)
    total = opened = 0.; worst = 0.; pairs = {}
    for (a, b), (edges, inset) in joints.items():
        length = np.linalg.norm(edges[:, 1] - edges[:, 0], axis=1)
        dist = point_triangle_distance(inset, reduced_tris, TOL)
        open_length = float(length[dist > TOL].sum())
        gap = float(np.where(dist > TOL, dist, 0).max())
        total += float(length.sum()); opened += open_length; worst = max(worst, gap)
        name = shapes[a]['name'] + ' / ' + shapes[b]['name']
        pairs[name] = {'length': round(float(length.sum()), 3), 'open_length': round(open_length, 3),
                       'max_gap': round(gap, 3)}
    return {'joint_length': round(total, 3), 'open_length': round(opened, 3),
            'open_share': round(opened / total, 5) if total else 0., 'max_gap': round(worst, 3),
            'pairs': {k: v for k, v in pairs.items() if v['open_length'] > 0}}


def model_triangles(raw):
    """Frame-0 world triangles of an alias model (as the game places them)."""
    import struct
    h = struct.unpack_from('<4si3f3ff3f8if', raw)
    sw, sh, nv, nt = h[13], h[14], h[15], h[16]
    at = 88 + sw * sh + nv * 12
    tri = np.frombuffer(raw, '<i4', nt * 4, at).reshape(nt, 4)[:, 1:]; at += nt * 16 + 28
    verts = np.frombuffer(raw, np.uint8, nv * 4, at).reshape(nv, 4)[:, :3].astype(float)
    world = verts * np.array(h[2:5]) + np.array(h[5:8])
    return world[tri]


def silhouette_holes(source_tris, reduced_tris, views=16, size=96):
    """Pixels where the background shows through the reduced model inside the source silhouette."""
    from PIL import Image, ImageDraw, ImageFilter
    lo = source_tris.reshape(-1, 3).min(0); hi = source_tris.reshape(-1, 3).max(0)
    centre = (lo + hi) / 2; scale = (size - 6) / max(float(np.max(hi - lo)), 1e-3)
    holes = 0; inside = 0
    for k in range(views):
        angle = 2 * np.pi * k / views; elevation = (-.35, 0., .35)[k % 3]
        right = np.array([-np.sin(angle), np.cos(angle), 0.])
        up = np.array([-np.cos(angle) * np.sin(elevation), -np.sin(angle) * np.sin(elevation), np.cos(elevation)])

        def mask(tris):
            image = Image.new('L', (size, size), 0); draw = ImageDraw.Draw(image)
            rel = tris - centre
            xs = rel @ right * scale + size / 2; ys = size / 2 - rel @ up * scale
            for x, y in zip(xs, ys):
                draw.polygon(list(zip(x, y)), fill=255)
            return image
        source = mask(source_tris).filter(ImageFilter.MinFilter(3))
        reduced = np.array(mask(reduced_tris)) > 0; core = np.array(source) > 0
        holes += int((core & ~reduced).sum()); inside += int(core.sum())
    return {'views': views, 'hole_pixels': holes, 'hole_share': round(holes / max(inside, 1), 6)}


# ---------------------------------------------------------------- driver

_index = None


def census_index(store):
    """{(part_key, weight, height): entry directory} of a parts store's census entries."""
    index = {}
    for entry in Path(store).glob('*/*/entry.json'):
        record = json.loads(entry.read_text())
        ident = record['identity']
        if ident.get('kind') == 'census' and record['result'].get('status') == 'ready':
            index[(ident['part_key'], *map(float, ident['scale']))] = entry.parent
    return index


def source_shapes(store_index, spec):
    """Posed source shapes of one appearance from the census entries, gallery-translated."""
    from npc_parts import part_key
    a = spec['appearance']; shapes = []
    for part in a['parts']:
        directory = store_index[(part_key(a['skeleton'], part), float(a['weight']), float(a['height']))]
        result = json.loads((directory / 'entry.json').read_text())['result']
        arrays = np.load(directory / 'payload.npz')
        for i, row in enumerate(result['shapes']):
            shapes.append({'name': row['name'], 'points': arrays[f's{i}_positions'][0],
                           'faces': arrays[f's{i}_faces'].astype(int)})
    points = np.concatenate([s['points'] for s in shapes])
    low, high = points.min(0), points.max(0)
    shift = np.array([(low[0] + high[0]) / 2, (low[1] + high[1]) / 2, low[2]])
    for s in shapes:
        s['points'] = s['points'] - shift
    return shapes


def audit_task(task):
    global _index
    store, galleries, key, spec, views = task
    if _index is None or _index[0] != store:
        _index = (store, census_index(store))
    try:
        shapes = source_shapes(_index[1], spec)
        source = np.concatenate([s['points'][s['faces']] for s in shapes])
        row = {'key': key, 'source_triangles': int(len(source))}
        for label, gallery in galleries.items():
            reduced = model_triangles((Path(gallery) / 'gallery' / (key + '.mdl')).read_bytes())
            row[label] = measure(shapes, reduced)
            row[label]['triangles'] = int(len(reduced))
            if views:
                row[label]['view'] = silhouette_holes(source, reduced, views)
    except Exception as exc:
        row = {'key': key, 'error': type(exc).__name__ + ': ' + str(exc)}
    return row


def recipe_task(task):
    """Builder stage: one composed appearance against its posed source parts (recipe file)."""
    from npc_parts import Store
    store, models, recipes, views = task
    out = []
    for recipe in recipes:
        try:
            shapes = []
            for census in recipe['census']:
                directory = Store(store).root / census[:2] / census
                result = json.loads((directory / 'entry.json').read_text())['result']
                arrays = np.load(directory / 'payload.npz')
                for i, row in enumerate(result['shapes']):
                    shapes.append({'name': row['name'], 'points': arrays[f's{i}_positions'][0] - np.array(recipe['shift']),
                                   'faces': arrays[f's{i}_faces'].astype(int)})
            reduced = model_triangles((Path(models) / (recipe['key'] + '.mdl')).read_bytes())
            row = {'key': recipe['key'], 'candidate': measure(shapes, reduced)}
            if views:
                row['candidate']['view'] = silhouette_holes(np.concatenate([x['points'][x['faces']] for x in shapes]),
                                                            reduced, views)
        except Exception as exc:
            row = {'key': recipe['key'], 'error': type(exc).__name__ + ': ' + str(exc)}
        out.append(row)
    return out


def summarise(rows, label):
    good = [r[label] for r in rows if label in r]
    if not good:
        return {}
    share = np.array([g['open_share'] for g in good]); gap = np.array([g['max_gap'] for g in good])
    out = {'appearances': len(good), 'with_open_joints': int((share > 0).sum()),
           'open_share_mean': round(float(share.mean()), 5), 'open_share_max': round(float(share.max()), 5),
           'max_gap_max': round(float(gap.max()), 3), 'max_gap_p95': round(float(np.percentile(gap, 95)), 3),
           'joint_length': round(sum(g['joint_length'] for g in good), 1),
           'open_length': round(sum(g['open_length'] for g in good), 1)}
    views = [g['view'] for g in good if 'view' in g]
    if views:
        out['view_hole_share_mean'] = round(float(np.mean([v['hole_share'] for v in views])), 6)
        out['view_hole_pixels'] = int(sum(v['hole_pixels'] for v in views))
    pairs = {}
    for g in good:
        for name, p in g['pairs'].items():
            q = pairs.setdefault(name, {'appearances': 0, 'open_length': 0., 'max_gap': 0.})
            q['appearances'] += 1; q['open_length'] += p['open_length']; q['max_gap'] = max(q['max_gap'], p['max_gap'])
    out['worst_pairs'] = dict(sorted(((k, {**v, 'open_length': round(v['open_length'], 2)}) for k, v in pairs.items()),
                                     key=lambda kv: -kv[1]['open_length'])[:25])
    return out


def audit(args):
    from build_parallel import completed_map
    from prepare_gallery import catalogue
    _, specs = catalogue(Path(args.data_files))
    keys = [k for k, s in specs.items() if s['kind'] == 'NPC_']
    if args.limit:
        keys = keys[::max(1, len(keys) // args.limit)][:args.limit]
    galleries = {'candidate': str(args.gallery)}
    if args.reference:
        galleries['reference'] = str(args.reference)
    tasks = [(str(args.parts_store), galleries, k, specs[k], args.views) for k in keys]
    rows = list(completed_map(audit_task, tasks, args.jobs))
    rows.sort(key=lambda r: r['key'])
    errors = [r for r in rows if 'error' in r]
    summary = {'format': 'AmiWind NPC joint-seam audit 1', 'near': NEAR, 'tolerance': TOL,
               'appearances': len(rows), 'errors': len(errors),
               'candidate': summarise(rows, 'candidate'), 'reference': summarise(rows, 'reference')}
    for label in galleries:
        summary[label]['worst_appearances'] = [
            {'key': r['key'], 'open_share': r[label]['open_share'], 'max_gap': r[label]['max_gap'],
             'pairs': list(r[label]['pairs'])[:4]}
            for r in sorted((r for r in rows if label in r), key=lambda r: (-r[label]['open_length'], r['key']))[:20]]
    Path(args.out).write_text(json.dumps({'summary': summary, 'appearances': rows}, indent=1) + '\n',
                              encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in summary.items()}, indent=1)[:6000])
    return 1 if errors else 0


def check(report, threshold=DEFAULT_THRESHOLD, max_gap=DEFAULT_MAX_GAP):
    """Failures: appearances whose open joint share or largest gap exceeds the limits."""
    failures = []
    for row in report['appearances']:
        if 'error' in row:
            failures.append((row['key'], row['error'])); continue
        c = row['candidate']
        if c['open_share'] > threshold or c['max_gap'] > max_gap:
            failures.append((row['key'], f"open share {c['open_share']}, largest gap {c['max_gap']}"))
    return failures


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('audit')
    a.add_argument('--data-files', type=Path, required=True)
    a.add_argument('--gallery', type=Path, required=True)
    a.add_argument('--reference', type=Path)
    a.add_argument('--parts-store', type=Path, required=True)
    a.add_argument('--out', type=Path, required=True)
    a.add_argument('--views', type=int, default=0)
    a.add_argument('--limit', type=int)
    a.add_argument('--jobs', type=int, default=1)
    c = sub.add_parser('check')
    c.add_argument('--report', type=Path, required=True)
    c.add_argument('--threshold', type=float, default=DEFAULT_THRESHOLD)
    c.add_argument('--max-gap', type=float, default=DEFAULT_MAX_GAP)
    args = p.parse_args(argv)
    if args.command == 'audit':
        return audit(args)
    failures = check(json.loads(args.report.read_text()), args.threshold, args.max_gap)
    for key, why in failures[:50]:
        print('joint gap:', key, why)
    print(f'{len(failures)} appearances over the joint-gap limits')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
