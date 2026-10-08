#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Distant "outer mold" shells: a closed, low-poly, render-only stand-in for a mesh.

The shell is what is left when a mesh is shrink-wrapped: openings narrower
than a threshold (windows, doors, gaps between parts) are sealed, enclosed
cavities are filled, and only the outer surface remains, simplified to a face
budget. It is meant to be drawn instead of the full mesh beyond a distance.
It never replaces the original geometry or its collision.

Pipeline (numpy + scipy only):

1. voxelise   sample every triangle at most cell/3 apart into a cell grid
2. seal       morphological closing with a ball of radius r cells, where
              r = keep_opening / (2 * cell) - 1/4: an opening at least
              keep_opening wide can never be sealed (every voxel the closing
              adds lies within r cells of the surface). Every sealed opening
              at least report_width wide is listed with its centre, size and
              width; plugs (all voxels the closing added) and cavities
              (enclosed space filled afterwards) are listed as regions.
3. fill       enclosed cavities (scipy binary_fill_holes)
4. manifold   2x2x2 blocks with diagonal or split voxel patterns are filled so
              the boundary-face surface is a closed 2-manifold
5. extract    boundary faces between solid and empty cells (cuberille)
6. simplify   quadric edge collapse (Garland-Heckbert) with link-condition
              and face-turn checks, so the shell stays a closed 2-manifold;
              vertex clustering is available as a cruder fallback
7. snap       shell vertices move to the nearest original surface point when
              it is within 1.8 cells (a voxel diagonal) and no face flips
8. materials  each shell face takes the dominant material of the nearest
              same-facing original triangles (majority vote of 7 samples) and
              a source triangle of that material, near and of similar
              orientation, so a converter can reuse its texture axes (texel
              density and alignment)
9. measure    surface deviation both ways (max/mean), silhouette error from
              several directions (area share and max distance) and roof-line
              height error from above

Usage: mold_shell.py IN.obj OUT.obj [--cell 4] [--faces 48] [--keep-opening 32] [--report-width 12]
                     [--report OUT.json] [--method quadric|cluster]
Faces in OUT.obj wind counter-clockwise seen from outside.
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage

SILHOUETTE_DIRECTIONS = tuple(
    [(math.cos(a), math.sin(a), 0.0) for a in np.arange(8) * math.pi / 4] +
    [(0.0, 0.0, -1.0)] +
    [(math.cos(a) * 0.7071, math.sin(a) * 0.7071, -0.7071) for a in np.arange(4) * math.pi / 2 + math.pi / 4])


# ---------------------------------------------------------------- geometry
def triangle_normals(tris):
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    area2 = np.linalg.norm(n, axis=1)
    with np.errstate(invalid='ignore', divide='ignore'):
        unit = np.where(area2[:, None] > 0, n / np.where(area2 > 0, area2, 1)[:, None], 0)
    return unit, area2 / 2


def _prepare_triangles(tris):
    tris = np.asarray(tris, float).reshape(-1, 3, 3)
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    ab, ac = b - a, c - a
    n = np.cross(ab, ac)
    nn = (n * n).sum(1)
    d00, d01, d11 = (ab * ab).sum(1), (ab * ac).sum(1), (ac * ac).sum(1)
    denom = d00 * d11 - d01 * d01
    good = (nn > 1e-12) & (np.abs(denom) > 1e-12)
    return dict(a=a, b=b, c=c, ab=ab, ac=ac, n=n, d00=d00, d01=d01, d11=d11, good=good,
                nn=np.where(good, nn, 1), denom=np.where(good, denom, 1))


def _pair_distances(points, t):
    """(P,T) distances and nearest points from points (P,3) to prepared triangles."""
    p = points[:, None, :]
    ap = p - t['a'][None]
    d20, d21 = (ap * t['ab'][None]).sum(2), (ap * t['ac'][None]).sum(2)
    v = (t['d11'][None] * d20 - t['d01'][None] * d21) / t['denom'][None]
    w = (t['d00'][None] * d21 - t['d01'][None] * d20) / t['denom'][None]
    inside = t['good'][None] & (v >= 0) & (w >= 0) & (v + w <= 1)
    plane = (ap * t['n'][None]).sum(2) / t['nn'][None]
    best_d = np.where(inside, np.abs(plane) * np.sqrt(t['nn'])[None], np.inf)
    best_p = p - plane[..., None] * t['n'][None]
    for e0, e1 in ((t['a'], t['b']), (t['b'], t['c']), (t['c'], t['a'])):
        seg = e1 - e0
        ll = (seg * seg).sum(1)
        u = np.clip(((p - e0[None]) * seg[None]).sum(2) / np.where(ll > 0, ll, 1)[None], 0, 1)
        q = e0[None] + u[..., None] * seg[None]
        dist = np.linalg.norm(p - q, axis=2)
        better = dist < best_d
        best_d = np.where(better, dist, best_d)
        best_p = np.where(better[..., None], q, best_p)
    return best_d, best_p


def distances_to_each(point, tris):
    """Distance from one point to every triangle (T,)."""
    return _pair_distances(np.asarray(point, float).reshape(1, 3), _prepare_triangles(tris))[0][0]


def closest_points(points, tris, chunk=200000):
    """Nearest point on a triangle set: (distance, triangle index, point) per point."""
    points = np.asarray(points, float).reshape(-1, 3)
    t = _prepare_triangles(tris)
    out_d = np.empty(len(points))
    out_i = np.empty(len(points), int)
    out_p = np.empty((len(points), 3))
    step = max(1, chunk // max(1, len(t['a'])))
    for s in range(0, len(points), step):
        best_d, best_p = _pair_distances(points[s:s + step], t)
        k = best_d.argmin(1)
        rows = np.arange(len(k))
        out_d[s:s + step] = best_d[rows, k]
        out_i[s:s + step] = k
        out_p[s:s + step] = best_p[rows, k]
    return out_d, out_i, out_p


def sample_surface(tris, count, seed=0):
    """Area-weighted, seeded surface samples (count points)."""
    tris = np.asarray(tris, float).reshape(-1, 3, 3)
    _, area = triangle_normals(tris)
    if len(tris) == 0 or area.sum() <= 0:
        return np.zeros((0, 3))
    rng = np.random.default_rng(seed)
    pick = rng.choice(len(tris), size=count, p=area / area.sum())
    r1, r2 = rng.random(count), rng.random(count)
    s = np.sqrt(r1)
    u, v = 1 - s, s * (1 - r2)
    t = tris[pick]
    return t[:, 0] * u[:, None] + t[:, 1] * v[:, None] + t[:, 2] * (1 - u - v)[:, None]


def mesh_triangles(vertices, faces):
    return np.asarray(vertices, float)[np.asarray(faces, int)]


def edge_report(faces):
    """Closed = every directed edge has exactly one opposite partner."""
    faces = np.asarray(faces, int).reshape(-1, 3)
    if len(faces) == 0:
        return {'closed': False, 'boundary_edges': 0, 'nonmanifold_edges': 0, 'euler': 0}
    directed = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    key = directed[:, 0] * (faces.max() + 1) + directed[:, 1]
    rkey = directed[:, 1] * (faces.max() + 1) + directed[:, 0]
    uniq, counts = np.unique(key, return_counts=True)
    dup = int((counts > 1).sum())
    present = np.isin(rkey, uniq)
    boundary = int((~present).sum())
    und = np.sort(directed, axis=1)
    _, ucount = np.unique(und[:, 0] * (faces.max() + 1) + und[:, 1], return_counts=True)
    nonmanifold = int((ucount > 2).sum()) + dup
    verts = len(np.unique(faces))
    euler = verts - len(ucount) + len(faces)
    return {'closed': boundary == 0 and nonmanifold == 0, 'boundary_edges': boundary,
            'nonmanifold_edges': nonmanifold, 'euler': int(euler)}


# ---------------------------------------------------------------- voxels
def voxelize(tris, cell, pad=2):
    """Surface occupancy grid. Returns (grid, origin); cell (i,j,k) spans
    origin + [i,j,k]*cell .. +cell."""
    tris = np.asarray(tris, float).reshape(-1, 3, 3)
    # Half-cell offset: axis-aligned faces at the extremes fall mid-cell, so
    # rounding never pushes them into the neighbouring cell on one side only.
    lo = tris.reshape(-1, 3).min(0) - (pad + 0.5) * cell
    hi = tris.reshape(-1, 3).max(0) + pad * cell
    shape = tuple(int(x) for x in np.ceil((hi - lo) / cell).astype(int) + 1)
    grid = np.zeros(shape, bool)
    cache = {}
    longest = np.max(np.linalg.norm(tris - np.roll(tris, 1, axis=1), axis=2), axis=1)
    for t, edge in zip(tris, longest):
        n = max(1, int(math.ceil(edge / (cell / 3.0))))
        if n not in cache:
            i, j = np.meshgrid(np.arange(n + 1), np.arange(n + 1), indexing='ij')
            keep = (i + j) <= n
            cache[n] = np.stack([i[keep], j[keep]], 1) / n
        bc = cache[n]
        pts = t[0] + bc[:, :1] * (t[1] - t[0]) + bc[:, 1:] * (t[2] - t[0])
        idx = np.floor((pts - lo) / cell).astype(int)
        grid[idx[:, 0], idx[:, 1], idx[:, 2]] = True
    return grid, lo


def closing(mask, radius):
    """Morphological closing with a Euclidean ball, via two distance
    transforms (linear time; the grid needs radius + 1 cells of padding)."""
    dilated = ndimage.distance_transform_edt(~mask) <= radius
    return ndimage.distance_transform_edt(dilated) > radius


def _regions(mask, origin, cell, distance=None):
    labels, count = ndimage.label(mask, structure=np.ones((3, 3, 3), bool))
    out = []
    if count == 0:
        return out
    objects = ndimage.find_objects(labels)
    for k, sl in enumerate(objects, 1):
        sub = labels[sl] == k
        idx = np.argwhere(sub) + [s.start for s in sl]
        lo = idx.min(0)
        hi = idx.max(0) + 1
        row = {'centre': [round(float(v), 2) for v in origin + (idx.mean(0) + 0.5) * cell],
               'size': [round(float(v), 2) for v in (hi - lo) * cell],
               'volume': round(float(len(idx) * cell ** 3), 2)}
        if distance is not None:
            row['width'] = round(float(2 * distance[sl][sub].max() * cell), 2)
        out.append(row)
    out.sort(key=lambda r: -r['volume'])
    return out


def closing_radius(cell, keep_opening):
    """Ball radius in cells. A quarter cell below keep_opening / 2 so that the
    discrete ball never reaches a voxel at exactly keep_opening / 2 and a flat
    wall never gains a layer (dilation <= r, erosion > r, r not an integer)."""
    return keep_opening / (2.0 * cell) - 0.25


def seal(surface, origin, cell, keep_opening, report_width=12.0):
    """Close openings narrower than keep_opening and fill enclosed cavities.
    Returns (solid grid, openings report). 'plugs' are the connected regions
    the closing added (corner fills and sealed gaps, often merged into one
    region per building); 'openings' splits them into one entry per sealed
    opening at least report_width wide (plug voxels at least report_width / 2
    from the original surface, labelled separately)."""
    r = closing_radius(cell, keep_opening)
    if r >= 1:
        closed = closing(surface, r) | surface
    else:
        closed = surface.copy()
    plugs = closed & ~surface
    # Width of a sealed opening ~ twice the largest distance from a plug
    # voxel to the original surface.
    dist = ndimage.distance_transform_edt(~surface) if plugs.any() else None
    solid = ndimage.binary_fill_holes(closed)
    cavities = solid & ~closed
    cores = plugs & (dist * cell >= report_width / 2.0) if dist is not None else plugs
    report = {'closing_radius_cells': round(r, 3), 'keep_opening': keep_opening,
              'max_sealable_width': round(max(0.0, 2 * r * cell), 2), 'report_width': report_width,
              'openings': _regions(cores, origin, cell, dist),
              'plugs': _regions(plugs, origin, cell, dist), 'cavities': _regions(cavities, origin, cell)}
    return solid, report


def _bad_block_table():
    corners = [(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)]
    index = {c: i for i, c in enumerate(corners)}

    def components(members):
        members = set(members)
        seen, count = set(), 0
        for m in members:
            if m in seen:
                continue
            count += 1
            stack = [m]
            seen.add(m)
            while stack:
                c = stack.pop()
                for axis in range(3):
                    d = list(c)
                    d[axis] ^= 1
                    d = tuple(d)
                    if d in members and d not in seen:
                        seen.add(d)
                        stack.append(d)
        return count

    table = np.zeros(256, bool)
    for code in range(256):
        solid = [c for c in corners if code >> index[c] & 1]
        empty = [c for c in corners if not code >> index[c] & 1]
        bad = components(solid) > 1 or components(empty) > 1
        for axis in range(3):
            for layer in (0, 1):
                quad = [c for c in corners if c[axis] == layer]
                bits = [code >> index[c] & 1 for c in quad]
                # quad corners in order: two pairs sharing the other coordinates
                others = [k for k in range(3) if k != axis]
                pos = {(c[others[0]], c[others[1]]): b for c, b in zip(quad, bits)}
                if pos[0, 0] == pos[1, 1] != pos[0, 1] == pos[1, 0]:
                    bad = True
        table[code] = bad
    return table


_BAD_BLOCKS = None


def make_manifold(solid, limit=64):
    """Fill 2x2x2 blocks whose pattern would make a non-manifold boundary."""
    global _BAD_BLOCKS
    if _BAD_BLOCKS is None:
        _BAD_BLOCKS = _bad_block_table()
    grid = np.pad(solid, 1)
    added = 0
    for _ in range(limit):
        code = np.zeros(tuple(s - 1 for s in grid.shape), np.uint16)
        bit = 0
        for x in (0, 1):
            for y in (0, 1):
                for z in (0, 1):
                    code |= grid[x:x + code.shape[0], y:y + code.shape[1], z:z + code.shape[2]].astype(np.uint16) << bit
                    bit += 1
        bad = _BAD_BLOCKS[code]
        if not bad.any():
            break
        grow = np.zeros_like(grid)
        for x in (0, 1):
            for y in (0, 1):
                for z in (0, 1):
                    grow[x:x + bad.shape[0], y:y + bad.shape[1], z:z + bad.shape[2]] |= bad
        added += int((grow & ~grid).sum())
        grid |= grow
    else:
        raise ValueError('voxel surface did not become manifold')
    return grid[1:-1, 1:-1, 1:-1], added


def cuberille(solid, origin, cell):
    """Boundary faces between solid and empty cells as an indexed, closed
    triangle mesh (counter-clockwise seen from outside)."""
    grid = np.pad(solid, 1)
    org = np.asarray(origin, float) - cell
    quads = []
    for axis in range(3):
        a, b = [(1, 2), (2, 0), (0, 1)][axis]
        lo = [slice(None)] * 3
        hi = [slice(None)] * 3
        lo[axis] = slice(0, -1)
        hi[axis] = slice(1, None)
        g0, g1 = grid[tuple(lo)], grid[tuple(hi)]
        for sign, mask in ((1, g0 & ~g1), (-1, g1 & ~g0)):
            idx = np.argwhere(mask)
            if len(idx) == 0:
                continue
            base = idx.copy()
            base[:, axis] += 1
            ea = np.zeros(3, int)
            eb = np.zeros(3, int)
            ea[a] = 1
            eb[b] = 1
            corners = np.stack([base, base + ea, base + ea + eb, base + eb], 1)
            if sign < 0:
                corners = corners[:, ::-1]
            quads.append(corners)
    if not quads:
        return np.zeros((0, 3)), np.zeros((0, 3), int)
    quads = np.concatenate(quads)
    flat = quads.reshape(-1, 3)
    uniq, inverse = np.unique(flat, axis=0, return_inverse=True)
    q = inverse.reshape(-1, 4)
    faces = np.concatenate([q[:, [0, 1, 2]], q[:, [0, 2, 3]]])
    return org + uniq * cell, faces


# ---------------------------------------------------------------- reduce
def _clean(vertices, faces):
    faces = np.asarray(faces, int).reshape(-1, 3)
    if len(faces):
        tri = vertices[faces]
        _, area = triangle_normals(tri)
        ok = (faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 2] != faces[:, 0]) & (area > 1e-9)
        faces = faces[ok]
    used = np.unique(faces)
    remap = np.full(len(vertices), -1)
    remap[used] = np.arange(len(used))
    return np.asarray(vertices, float)[used], remap[faces]


def cluster_simplify(vertices, faces, target):
    """Vertex clustering on a regular grid sized to approach the budget."""
    vertices = np.asarray(vertices, float)
    lo, hi = vertices.min(0), vertices.max(0)
    span = np.maximum(hi - lo, 1e-6)
    best = None
    for k in range(64, 0, -1):
        cell = span.max() / k
        key = np.floor((vertices - lo) / cell + 1e-9).astype(int)
        uniq, inv = np.unique(key, axis=0, return_inverse=True)
        pos = np.zeros((len(uniq), 3))
        np.add.at(pos, inv, vertices)
        pos /= np.bincount(inv, minlength=len(uniq))[:, None]
        f = inv[faces]
        f = f[(f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 2] != f[:, 0])]
        if len(f):
            f = np.unique(f, axis=0)  # drop repeated faces
        v, f = _clean(pos, f)
        best = (v, f)
        if len(f) <= target:
            break
    return best


def _plane_quadric(p0, p1, p2):
    n = np.cross(p1 - p0, p2 - p0)
    length = np.linalg.norm(n)
    if length <= 1e-12:
        return np.zeros((4, 4))
    n = n / length
    plane = np.append(n, -n @ p0)
    return np.outer(plane, plane) * (length / 2)


def quadric_simplify(vertices, faces, targets, max_turn=0.3):
    """Garland-Heckbert edge collapse that keeps a closed 2-manifold closed:
    a collapse must pass the link condition (exactly two common neighbours),
    must not turn any surviving face by more than acos(max_turn) or collapse
    it, and the mesh keeps at least 4 faces. Targets are face counts; returns
    {target: (vertices, faces)} snapshots taken on the way down (a target the
    mesh cannot reach gets the smallest valid mesh)."""
    import heapq
    V = np.array(vertices, float)
    F = [list(map(int, f)) for f in np.asarray(faces, int)]
    alive = [True] * len(F)
    vf = [set() for _ in range(len(V))]
    for i, f in enumerate(F):
        for x in f:
            vf[x].add(i)
    Q = np.zeros((len(V), 4, 4))
    for i, f in enumerate(F):
        k = _plane_quadric(V[f[0]], V[f[1]], V[f[2]])
        for x in f:
            Q[x] += k
    version = [0] * len(V)
    dead = [False] * len(V)
    count = len(F)

    def neighbours(x):
        out = set()
        for i in vf[x]:
            out.update(F[i])
        out.discard(x)
        return out

    def cost(a, b):
        q = Q[a] + Q[b]
        cands = [V[a], V[b], (V[a] + V[b]) / 2]
        A = q[:3, :3]
        if np.linalg.cond(A) < 1e4:
            opt = np.linalg.solve(A, -q[:3, 3])
            span = np.linalg.norm(V[a] - V[b])
            if np.all(opt >= np.minimum(V[a], V[b]) - span) and np.all(opt <= np.maximum(V[a], V[b]) + span):
                cands.append(opt)
        best = None
        for c in cands:
            h = np.append(c, 1.0)
            e = float(h @ q @ h)
            if best is None or e < best[0] - 1e-12:
                best = (max(e, 0.0), c)
        # Among equal-cost collapses (planar regions) take short edges first.
        return best[0] + 1e-9 * float((V[a] - V[b]) @ (V[a] - V[b])), best[1]

    heap = []

    def push(a, b):
        if a > b:
            a, b = b, a
        c, pos = cost(a, b)
        heapq.heappush(heap, (c, a, b, version[a], version[b], tuple(pos)))

    edges = set()
    for f in F:
        for k in range(3):
            a, b = f[k], f[(k + 1) % 3]
            edges.add((min(a, b), max(a, b)))
    for a, b in sorted(edges):
        push(a, b)

    def snapshot():
        idx = [i for i in range(len(F)) if alive[i]]
        return _clean(V, np.array([F[i] for i in idx], int).reshape(-1, 3))

    targets = sorted(set(int(t) for t in targets), reverse=True)
    out = {}
    while targets and count <= targets[0]:
        out[targets.pop(0)] = snapshot()
    while heap and targets:
        c, a, b, va, vb, pos = heapq.heappop(heap)
        if dead[a] or dead[b] or version[a] != va or version[b] != vb:
            continue
        shared = vf[a] & vf[b]
        if len(shared) != 2 or count - 2 < 4:
            continue
        if len((neighbours(a) & neighbours(b)) - {a, b}) != 2:
            continue
        pos = np.array(pos)
        ok = True
        for i in (vf[a] | vf[b]) - shared:
            f = F[i]
            old = V[f]
            new = np.array([pos if x in (a, b) else V[x] for x in f])
            n0 = np.cross(old[1] - old[0], old[2] - old[0])
            n1 = np.cross(new[1] - new[0], new[2] - new[0])
            l0, l1 = np.linalg.norm(n0), np.linalg.norm(n1)
            if l1 < 1e-6 * max(l0, 1e-9) or l1 < 1e-9 or (n0 @ n1) < max_turn * l0 * l1:
                ok = False
                break
        if not ok:
            continue
        for i in shared:
            alive[i] = False
            for x in F[i]:
                vf[x].discard(i)
        for i in list(vf[b]):
            F[i] = [a if x == b else x for x in F[i]]
            vf[a].add(i)
        vf[b] = set()
        dead[b] = True
        V[a] = pos
        Q[a] += Q[b]
        version[a] += 1
        count -= 2
        for n in neighbours(a):
            push(a, n)
        while targets and count <= targets[0]:
            out[targets.pop(0)] = snapshot()
    for t in targets:
        out[t] = snapshot()
    return out


def simplify(vertices, faces, target, method='quadric'):
    if len(faces) <= target:
        return _clean(vertices, faces) + ('none',)
    if method == 'cluster':
        return cluster_simplify(vertices, faces, target) + ('cluster',)
    v, f = quadric_simplify(vertices, faces, [target])[target]
    return v, f, 'quadric'


def snap_vertices(vertices, faces, tris, max_distance):
    """Move vertices onto the original surface where it is close, unless a
    face would flip or collapse; returns (vertices, snapped count)."""
    vertices = np.asarray(vertices, float)
    if len(tris) == 0 or len(vertices) == 0:
        return vertices, 0
    d, _, p = closest_points(vertices, tris)
    candidate = d <= max_distance
    out = vertices.copy()
    before, area0 = triangle_normals(vertices[faces])
    for _ in range(8):
        trial = np.where(candidate[:, None], p, vertices)
        after, area1 = triangle_normals(trial[faces])
        bad = ((before * after).sum(1) < 0.2) | (area1 < 0.05 * area0)
        if not bad.any():
            out = trial
            break
        candidate[np.unique(faces[bad])] = False
    else:
        out = vertices
        candidate[:] = False
    return out, int(candidate.sum())


# ---------------------------------------------------------------- materials
def assign_materials(vertices, faces, tris, materials, align_weight=32.0):
    """Dominant original material per shell face, plus a source triangle of
    that material for its texture axes. Votes from 7 samples per face
    (centroid, 3 near-corner, 3 mid-edge points); originals facing away
    (normal dot < 0.2) are ignored unless none face the same way. The source
    minimises distance + align_weight * (1 - normal dot), so the texture axes
    come from a nearby face of similar orientation and do not smear."""
    tris = np.asarray(tris, float).reshape(-1, 3, 3)
    materials = np.asarray(materials)
    shell = np.asarray(vertices, float)[np.asarray(faces, int)]
    sn, _ = triangle_normals(shell)
    on, _ = triangle_normals(tris)
    w = np.array([[1, 1, 1], [4, 1, 1], [1, 4, 1], [1, 1, 4], [1, 1, 0], [0, 1, 1], [1, 0, 1]], float)
    w /= w.sum(1, keepdims=True)
    face_material, face_source = [], []
    for k, t in enumerate(shell):
        pts = w @ t
        facing = (on @ sn[k]) >= 0.2
        pool = np.flatnonzero(facing) if facing.any() else np.arange(len(tris))
        _, idx, _ = closest_points(pts, tris[pool])
        src = pool[idx]
        votes = {}
        for i, s in enumerate(src):
            votes[materials[s].item()] = votes.get(materials[s].item(), 0) + (2 if i == 0 else 1)
        best = max(sorted(votes, key=str), key=lambda m: votes[m])
        face_material.append(best)
        same = pool[np.array([m.item() == best for m in materials[pool]])]
        score = distances_to_each(pts[0], tris[same]) + align_weight * (1 - on[same] @ sn[k])
        face_source.append(int(same[int(np.argmin(score))]))
    return face_material, face_source


def merge_coplanar(vertices, faces, materials, tolerance=1e-3):
    """Merge edge-adjacent coplanar triangles with the same material into
    convex polygons (Quake faces are convex polygons). Returns
    [(vertex index loop, material, source triangle list)]."""
    vertices = np.asarray(vertices, float)
    normals, _ = triangle_normals(vertices[faces])
    polys = [[list(f), m, [i], normals[i]] for i, (f, m) in enumerate(zip(np.asarray(faces).tolist(), materials))]

    def convex(loop, n):
        p = vertices[loop]
        for i in range(len(loop)):
            e0 = p[(i + 1) % len(p)] - p[i]
            e1 = p[(i + 2) % len(p)] - p[(i + 1) % len(p)]
            if np.cross(e0, e1) @ n < -1e-9:
                return False
        return True

    changed = True
    while changed:
        changed = False
        for i in range(len(polys)):
            if changed:
                break
            for j in range(i + 1, len(polys)):
                a, b = polys[i], polys[j]
                if a[1] != b[1] or a[3] @ b[3] < 1 - tolerance:
                    continue
                if abs((vertices[b[0][0]] - vertices[a[0][0]]) @ a[3]) > 1e-3:
                    continue
                la, lb = a[0], b[0]
                shared = None
                for x in range(len(la)):
                    u, v = la[x], la[(x + 1) % len(la)]
                    for y in range(len(lb)):
                        if lb[y] == v and lb[(y + 1) % len(lb)] == u:
                            shared = (x, y)
                            break
                    if shared:
                        break
                if not shared:
                    continue
                x, y = shared
                # la: ... u v ...  lb: ... v u ...  -> splice lb's path from u to v
                path = [lb[(y + 1 + k) % len(lb)] for k in range(len(lb))]  # starts at u, ends at v
                merged = la[:x + 1] + path[1:-1] + la[x + 1:]
                # drop collinear points
                pts = vertices[merged]
                keep = [k for k in range(len(merged)) if np.linalg.norm(np.cross(
                    pts[k] - pts[k - 1], pts[(k + 1) % len(pts)] - pts[k])) > 1e-9]
                merged = [merged[k] for k in keep]
                if len(set(merged)) != len(merged) or len(merged) < 3 or not convex(merged, a[3]):
                    continue
                polys[i] = [merged, a[1], a[2] + b[2], a[3]]
                polys.pop(j)
                changed = True
                break
    return [(p[0], p[1], p[2]) for p in polys]


def quake_face_count(polygons, axes):
    """Faces after Quake's 240-texel surface-extent split (mesh_geometry.split_surface);
    polygons: list of (N,3) arrays, axes: list of (2,4) texture vectors."""
    from mesh_geometry import split_surface
    return sum(len(split_surface(np.asarray(p, float), np.asarray(a, float))) for p, a in zip(polygons, axes))


# ---------------------------------------------------------------- measure
def _basis(direction):
    d = np.asarray(direction, float)
    d /= np.linalg.norm(d)
    up = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(up, d)
    u /= np.linalg.norm(u)
    return u, np.cross(d, u), d


def raster(tris2, shape, depth=None):
    """Coverage mask (and max depth) of 2-D triangles in pixel units."""
    mask = np.zeros(shape, bool)
    zbuf = np.full(shape, -np.inf) if depth is not None else None
    for k, t in enumerate(tris2):
        x0 = max(int(math.floor(t[:, 0].min())), 0)
        x1 = min(int(math.ceil(t[:, 0].max())), shape[0])
        y0 = max(int(math.floor(t[:, 1].min())), 0)
        y1 = min(int(math.ceil(t[:, 1].max())), shape[1])
        if x0 >= x1 or y0 >= y1:
            continue
        area = (t[1, 0] - t[0, 0]) * (t[2, 1] - t[0, 1]) - (t[2, 0] - t[0, 0]) * (t[1, 1] - t[0, 1])
        if abs(area) < 1e-12:
            continue
        X, Y = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5, indexing='ij')
        w0 = ((t[1, 0] - X) * (t[2, 1] - Y) - (t[2, 0] - X) * (t[1, 1] - Y)) / area
        w1 = ((t[2, 0] - X) * (t[0, 1] - Y) - (t[0, 0] - X) * (t[2, 1] - Y)) / area
        w2 = 1 - w0 - w1
        inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        mask[x0:x1, y0:y1] |= inside
        if depth is not None:
            z = w0 * depth[k, 0] + w1 * depth[k, 1] + w2 * depth[k, 2]
            sub = zbuf[x0:x1, y0:y1]
            np.maximum(sub, np.where(inside, z, -np.inf), out=sub)
    return mask, zbuf


def silhouette_errors(shell_tris, original_tris, directions=SILHOUETTE_DIRECTIONS, pixel=1.0):
    """Per direction: share of the original silhouette area that differs and
    the largest distance (units) from a differing pixel to the other outline."""
    rows = []
    for d in directions:
        u, v, _ = _basis(d)
        pts = np.concatenate([original_tris.reshape(-1, 3), shell_tris.reshape(-1, 3)])
        lo = np.array([pts @ u, pts @ v]).min(1) - 2 * pixel
        hi = np.array([pts @ u, pts @ v]).max(1) + 2 * pixel
        shape = tuple(int(x) for x in np.ceil((hi - lo) / pixel) + 1)

        def proj(t):
            return np.stack([(t @ u - lo[0]) / pixel, (t @ v - lo[1]) / pixel], -1)
        a, _ = raster(proj(original_tris), shape)
        b, _ = raster(proj(shell_tris), shape)
        diff = a ^ b
        far = 0.0
        if (b & ~a).any():
            far = max(far, float(ndimage.distance_transform_edt(~a)[b & ~a].max()))
        if (a & ~b).any():
            far = max(far, float(ndimage.distance_transform_edt(~b)[a & ~b].max()))
        rows.append({'direction': [round(float(x), 4) for x in d],
                     'area_error': round(float(diff.sum() / max(1, a.sum())), 4),
                     'max_error': round(far * pixel, 2)})
    return rows


def roofline_error(shell_tris, original_tris, pixel=1.0):
    """Top height map difference where both meshes cover the ground plan."""
    pts = np.concatenate([original_tris.reshape(-1, 3), shell_tris.reshape(-1, 3)])
    lo = pts[:, :2].min(0) - 2 * pixel
    shape = tuple(int(x) for x in np.ceil((pts[:, :2].max(0) + 2 * pixel - lo) / pixel) + 1)
    a, za = raster((original_tris[:, :, :2] - lo) / pixel, shape, original_tris[:, :, 2])
    b, zb = raster((shell_tris[:, :, :2] - lo) / pixel, shape, shell_tris[:, :, 2])
    both = a & b
    if not both.any():
        return {'max_dz': None, 'mean_dz': None, 'p95_dz': None, 'shell_higher_max': None}
    dz = zb[both] - za[both]
    # max_dz also catches openings seen from above (a sealed gap over a floor);
    # p95 is the roof-line error proper.
    return {'max_dz': round(float(np.abs(dz).max()), 2), 'mean_dz': round(float(np.abs(dz).mean()), 2),
            'p95_dz': round(float(np.percentile(np.abs(dz), 95)), 2),
            'shell_higher_max': round(float(dz.max()), 2), 'shell_lower_max': round(float(-dz.min()), 2)}


def deviation(shell_tris, original_tris, samples=4000, seed=0):
    a = sample_surface(original_tris, samples, seed)
    b = sample_surface(shell_tris, samples, seed + 1)
    da, _, _ = closest_points(a, shell_tris)
    db, _, _ = closest_points(b, original_tris)
    return {'original_to_shell_max': round(float(da.max()), 2), 'original_to_shell_mean': round(float(da.mean()), 2),
            'shell_to_original_max': round(float(db.max()), 2), 'shell_to_original_mean': round(float(db.mean()), 2),
            'hausdorff': round(float(max(da.max(), db.max())), 2)}


def pick_budget(reports, max_silhouette_error, max_area_error):
    """Smallest budget whose shell keeps every measured silhouette within
    max_silhouette_error units and the mean silhouette area error within
    max_area_error; the largest budget when none does. reports: {budget: report}."""
    for budget in sorted(reports):
        sil = reports[budget]['silhouette']
        if sil['worst_max_error'] <= max_silhouette_error and sil['mean_area_error'] <= max_area_error:
            return budget, True
    return max(reports), False


def screen_error(units, distance, width=320, fov=90.0):
    """Pixels covered by an error of `units` at `distance` on a viewport
    `width` pixels wide with horizontal field of view `fov` degrees."""
    return units * (width / 2.0) / (distance * math.tan(math.radians(fov) / 2))


# ---------------------------------------------------------------- driver
def build_shells(tris, materials=None, cell=4.0, budgets=(48,), keep_opening=32.0, method='quadric',
                 snap=True, measure=True, pixel=None, report_width=12.0):
    """Shells for a triangle soup (T,3,3) at several triangle budgets, sharing
    one voxel/seal pass. Returns {budget: shell dict} (see build_shell)."""
    t0 = time.monotonic()
    tris = np.asarray(tris, float).reshape(-1, 3, 3)
    if materials is None:
        materials = np.zeros(len(tris), int)
    materials = np.asarray(materials)
    r = closing_radius(cell, keep_opening)
    surface, origin = voxelize(tris, cell, pad=int(math.ceil(max(r, 0))) + 3)
    solid, openings = seal(surface, origin, cell, keep_opening, report_width)
    solid, manifold_added = make_manifold(solid)
    v0, f0 = cuberille(solid, origin, cell)
    common = {'input_triangles': int(len(tris)), 'cell': cell, 'voxel_grid': list(solid.shape),
              'manifold_fill_voxels': manifold_added, 'cuberille_triangles': int(len(f0)),
              'openings': openings}
    if method == 'cluster':
        levels = {b: cluster_simplify(v0, f0, b) for b in budgets}
    else:
        levels = quadric_simplify(v0, f0, budgets)
    common['prepare_seconds'] = round(time.monotonic() - t0, 3)
    out = {}
    for budget in budgets:
        t1 = time.monotonic()
        v, f = levels[budget]
        snapped = 0
        if snap:
            v, snapped = snap_vertices(v, f, tris, 1.8 * cell)
        mats, sources = assign_materials(v, f, tris, materials)
        shell_tris = mesh_triangles(v, f)
        report = dict(common, face_budget=int(budget), method=method, shell_triangles=int(len(f)),
                      snapped_vertices=snapped, **edge_report(f))
        if measure:
            px = pixel or max(cell / 4.0, 0.5)
            report['deviation'] = deviation(shell_tris, tris)
            sil = silhouette_errors(shell_tris, tris, pixel=px)
            report['silhouette'] = {'pixel': px, 'directions': sil,
                                    'worst_area_error': max(s['area_error'] for s in sil),
                                    'mean_area_error': round(float(np.mean([s['area_error'] for s in sil])), 4),
                                    'worst_max_error': max(s['max_error'] for s in sil)}
            report['roofline'] = roofline_error(shell_tris, tris, px)
        report['seconds'] = round(time.monotonic() - t1, 3)
        out[budget] = {'vertices': v, 'faces': f, 'materials': mats, 'sources': sources, 'report': report}
    return out


def build_shell(tris, materials=None, cell=4.0, faces=48, keep_opening=32.0, method='quadric',
                snap=True, measure=True, pixel=None, report_width=12.0):
    """Shell for a triangle soup (T,3,3). Returns a dict with 'vertices',
    'faces', 'materials', 'sources' (nearest original triangle per face) and
    'report'."""
    return build_shells(tris, materials, cell, (faces,), keep_opening, method, snap, measure, pixel,
                        report_width)[faces]


def read_obj(path):
    vertices, faces, mats, current = [], [], [], ''
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        part = line.split()
        if not part:
            continue
        if part[0] == 'v':
            vertices.append([float(x) for x in part[1:4]])
        elif part[0] == 'usemtl':
            current = part[1] if len(part) > 1 else ''
        elif part[0] == 'f':
            idx = [int(x.split('/')[0]) for x in part[1:]]
            idx = [i - 1 if i > 0 else len(vertices) + i for i in idx]
            for k in range(1, len(idx) - 1):
                faces.append([idx[0], idx[k], idx[k + 1]])
                mats.append(current)
    return np.array(vertices, float).reshape(-1, 3), np.array(faces, int).reshape(-1, 3), mats


def write_obj(path, vertices, faces, materials=None):
    lines = ['# outer mold shell (render-only), counter-clockwise outward']
    lines += ['v %.4f %.4f %.4f' % tuple(p) for p in vertices]
    current = None
    for k, face in enumerate(faces):
        m = materials[k] if materials is not None else None
        if m is not None and m != current:
            lines.append('usemtl %s' % m)
            current = m
        lines.append('f %d %d %d' % tuple(int(i) + 1 for i in face))
    Path(path).write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('input')
    ap.add_argument('output')
    ap.add_argument('--cell', type=float, default=4.0)
    ap.add_argument('--faces', type=int, default=48)
    ap.add_argument('--keep-opening', type=float, default=32.0)
    ap.add_argument('--report-width', type=float, default=12.0)
    ap.add_argument('--method', choices=('quadric', 'cluster'), default='quadric')
    ap.add_argument('--no-snap', action='store_true')
    ap.add_argument('--report')
    a = ap.parse_args(argv)
    v, f, mats = read_obj(a.input)
    if len(f) == 0:
        raise SystemExit('no triangles in ' + a.input)
    shell = build_shell(v[f], mats, a.cell, a.faces, a.keep_opening, a.method, not a.no_snap,
                        report_width=a.report_width)
    write_obj(a.output, shell['vertices'], shell['faces'], shell['materials'])
    text = json.dumps(shell['report'], indent=1) + '\n'
    if a.report:
        Path(a.report).write_text(text, encoding='utf-8', newline='\n')
    else:
        sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
