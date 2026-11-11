#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The world-wide check of the hollow-model bevel default (COLLISION-WORLDWIDE-REDUCTION-64).

    python3 tools/hollow_bevel_sweep.py AREA_WORK [--rooms N] [--jobs J] [--bevels 2] [--out REPORT.json]

AREA_WORK is a build's chim-room-batches/scene/area-work folder (one converted room per folder). For every hollow
model of every room (its profile has hollow_collision), each collision piece's standing hull is made the way the
CHIM builder writes it (prepare_mesh_bsp.standing_planes) with exact bevels on every plate (type 0, the method up to
v0.0.64-dev4) and with the default (--bevels, 2 = approximate everywhere; 1 = exact on near-horizontal plates), and
a standing box is swept along every wall plate: player origins on both sides of the plate (its centre and its corners
pulled a quarter in) at 17 to 48 units. "pushed" = a point solid with type 0 and empty with the default: the player
would get further into the wall (any one fails the check). "early" = empty with type 0 and solid with the default:
the player stops sooner; reported, and counted against --early-share at 24 units and more.

Collision bytes per model are the chain estimate (every standing plane one 20-byte plane and one 8-byte clipnode),
for both types, summed per room and for the world. Exit 1 on any push-through or an early share over the limit.
"""
import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

DISTANCES = (17.0, 18.0, 20.0, 24.0, 32.0, 48.0)
FAR = 24.0                     # early stops from here count against the limit (beyond the bevels' usual margin)
PLANE_BYTES, CLIPNODE_BYTES = 20, 8


def _solid(planes_of, pieces, pts):
    import numpy as np
    from scipy.spatial import cKDTree
    out = np.zeros(len(pts), bool)
    if not len(pts):
        return out
    tree = cKDTree(pts)
    for (points, *_), planes in zip(pieces, planes_of):
        c = points.mean(0)
        ids = tree.query_ball_point(c, float(np.linalg.norm(points - c, axis=1).max()) + 64.0)
        if not ids:
            continue
        ids = np.asarray(ids)
        inside = (pts[ids] @ planes[:, :3].T + planes[:, 3]).max(1) < 0
        out[ids[inside]] = True
    return out


def model_sweep(parts, bevels):
    """{'pieces', 'walkable', 'points', 'pushed', 'early', 'early_far', 'bytes_exact', 'bytes_default'} of one model."""
    import numpy as np
    from prepare_mesh_bsp import standing_planes
    from chim.models import hull_pieces, walkable_pieces
    pieces = hull_pieces(parts)
    walk = walkable_pieces(parts)
    exact, default = [], []
    for k, (p, h, *_) in enumerate(pieces):
        eq = np.unique(np.round(h.equations, 5), axis=0)
        exact.append(standing_planes(p, eq, True))
        default.append(standing_planes(p, eq, (k in walk) if bevels == 1 else False) if bevels else exact[-1])
    pts, dist = [], []
    for k, part in enumerate(parts):
        p = np.asarray(part[0], float)[:, :3]
        if k in walk or len(p) < 3:
            continue
        n = np.cross(p[1] - p[0], p[2] - p[0])
        ln = np.linalg.norm(n)
        if ln < 1e-9:
            continue
        n /= ln
        c = p[:3].mean(0)
        for b in [c] + [q + (c - q) * 0.25 for q in p[:3]]:
            for s in (1.0, -1.0):
                for d in DISTANCES:
                    pts.append(b + s * d * n)
                    dist.append(d)
    pts, dist = np.array(pts).reshape(-1, 3), np.array(dist)
    s0, s1 = _solid(exact, pieces, pts), _solid(default, pieces, pts)
    early = (~s0) & s1
    return {'pieces': len(pieces), 'walkable': len(walk), 'points': int(len(pts)), 'pushed': int((s0 & ~s1).sum()),
            'early': int(early.sum()), 'early_far': int((early & (dist >= FAR)).sum()),
            'points_far': int((dist >= FAR).sum()),
            'bytes_exact': sum(len(e) for e in exact) * (PLANE_BYTES + CLIPNODE_BYTES),
            'bytes_default': sum(len(e) for e in default) * (PLANE_BYTES + CLIPNODE_BYTES)}


def room_sweep(task):
    """The sweep of one converted room folder: {'room', 'cell', 'models': {source: model_sweep}, totals} or None."""
    work, bevels = Path(task[0]), task[1]
    index_path = work / 'source/scenery-index.json'
    if not index_path.is_file():
        return None
    sys.path[:0] = [str(Path(__file__).resolve().parent)]
    from prepare_mesh_bsp import _prepare_model, rock_profile
    index = json.loads(index_path.read_text())
    conv = json.loads((work / 'conversion.json').read_text()) if (work / 'conversion.json').is_file() else {}
    profiles = {n: p for g in index.get('groups', {}).values() for n, p in g.get('visual_profiles', {}).items()}
    used = sorted({r.get('model_index') for r in index.get('references', []) if r.get('model_index') is not None})
    out = {'room': conv.get('map', work.name), 'cell': conv.get('cell'), 'models': {}, 'errors': []}
    for mi in used:
        model = index['models'][mi]
        profile = profiles.get(model['source']) or rock_profile(model['source'], model['triangles'])
        if not profile.get('hollow_collision'):
            continue
        try:
            _, (_v, _f, _polys, parts, _lod) = _prepare_model((mi, dict(model), profile,
                                                               str(work / 'source/scenery.mwpak'), index['textures']))
            if parts:
                out['models'][model['source']] = model_sweep(parts, bevels)
        except Exception as error:      # noqa: BLE001 (one model's failure is named in the report, the rest go on)
            out['errors'].append('%s: %s: %s' % (model['source'], type(error).__name__, error))
    for key in ('pushed', 'early', 'early_far', 'points', 'points_far', 'bytes_exact', 'bytes_default'):
        out[key] = sum(m[key] for m in out['models'].values())
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('area_work', type=Path)
    ap.add_argument('--bevels', type=int, choices=(1, 2), default=2)
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--rooms', type=int, default=0, help='only the first N rooms (0: all)')
    ap.add_argument('--only', nargs='*', default=(), help='only these room folders')
    ap.add_argument('--verbose', action='store_true', help='name every room, also those without hollow models')
    ap.add_argument('--early-share', type=float, default=0.02,
                    help='largest share of the far sample points (24 units and more) that may stop early (0.02)')
    ap.add_argument('--out', type=Path)
    a = ap.parse_args(argv)
    works = sorted(p for p in a.area_work.iterdir() if (p / 'source/scenery-index.json').is_file())
    if a.only:
        works = [w for w in works if w.name in a.only]
    if a.rooms:
        works = works[:a.rooms]
    rooms = []
    with ProcessPoolExecutor(max_workers=max(1, a.jobs)) as pool:
        for row in pool.map(room_sweep, [(str(w), a.bevels) for w in works], chunksize=1):
            if a.verbose and row is not None and not row['models']:
                print('%s: no hollow model (%s)' % (row['room'], '; '.join(row['errors'][:3]) or 'none listed'))
            if row and row['models']:
                rooms.append(row)
                print('%-14s %-40s models %3d pushed %d early %d (far %d of %d) bytes %d -> %d%s' % (
                    row['room'], (row['cell'] or '')[:40], len(row['models']), row['pushed'], row['early'],
                    row['early_far'], row['points_far'], row['bytes_exact'], row['bytes_default'],
                    ('  errors %d' % len(row['errors'])) if row['errors'] else ''), flush=True)
    total = {k: sum(r[k] for r in rooms) for k in ('pushed', 'early', 'early_far', 'points_far', 'bytes_exact',
                                                    'bytes_default')}
    share = total['early_far'] / max(1, total['points_far'])
    worst = sorted(rooms, key=lambda r: r['early_far'] / max(1, r['points_far']), reverse=True)[:10]
    report = {'bevels': a.bevels, 'rooms': len(rooms), 'total': total, 'early_far_share': share,
              'limit': a.early_share, 'worst_rooms': [(r['room'], r['cell'], r['early_far'], r['points_far'])
                                                      for r in worst], 'per_room': rooms}
    print('world: %d rooms with hollow models; pushed %d; early %d (far %d of %d = %.4f, limit %.4f); collision '
          'bytes %d -> %d (%.1f %%)' % (len(rooms), total['pushed'], total['early'], total['early_far'],
                                        total['points_far'], share, a.early_share, total['bytes_exact'],
                                        total['bytes_default'],
                                        100.0 * total['bytes_default'] / max(1, total['bytes_exact'])))
    if a.out:
        a.out.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    errors = sum(len(r['errors']) for r in rooms)
    if total['pushed'] or share > a.early_share or errors:
        print('FAIL: %d pushed through, early share %.4f (limit %.4f), %d model errors' % (
            total['pushed'], share, a.early_share, errors))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
