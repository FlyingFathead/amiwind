# SPDX-License-Identifier: GPL-3.0-only
"""Planar merge: coplanar triangles with one texture mapping become one convex Quake face.

Quake faces are convex planar polygons, not triangles. The converter's polygon step
(mesh_geometry.surface_polygons) already merges triangles whose plane and mapping round to the same
key, two at a time while their union stays convex. This step finds the merges that one misses:

1. regions: triangles joined across a shared edge (positions welded at 0.001 units) when they have the
   same material, lie in the same plane (every corner within PLANE_EPS of the region's first
   triangle's plane, normals within 1e-6) and carry the same texture mapping up to whole texture
   repeats (every corner within TOL_TEXELS texels of the first triangle's mapping after removing a
   whole-texture shift: the same texels);
2. convex faces: each region split into convex polygons by joining faces across their shared edges
   while the union stays convex (Hertel-Mehlhorn), longest edges first, at most MAX_VERTS corners;
   collinear corners on the outline are kept, so a neighbour's edge that meets the face there still
   meets a corner (no T-junction gap);
3. the converter's 240-texel extent split (mesh_geometry.split_surface), unchanged.

polygons() returns the converter's face list or the merged one, whichever has fewer faces (ties: the
converter's), so a mesh never gets more faces from this step. Lossless: the surface, materials and
texture mapping are the source's. Deterministic: fixed orders everywhere, no randomness.

Measured on the owner's data (v0.0.36-dev3): Balmora's 226 meshes 45,105 -> 44,324 faces, Seyda Neen's
60 meshes 21,659 -> 21,458; organic meshes (the silt strider) gain nothing (docs/chim/MESH_METHODS.md).
"""
from collections import defaultdict

import numpy as np

TOL_TEXELS = 0.05
PLANE_EPS = 0.01
MAX_VERTS = 32


def _triangles(v, f):
    """The converter's triangles (mesh_geometry.surface_polygons): Quake units, no slivers under 0.05."""
    out = []
    for face in f:
        p = v[face[:3], :3] * .25
        uv = v[face[:3], 3:5]
        n = np.cross(p[1] - p[0], p[2] - p[0])
        a = np.linalg.norm(n)
        if a < .05:
            continue
        n /= a
        A = np.vstack((p[1] - p[0], p[2] - p[0], n))
        b = np.vstack((uv[1] - uv[0], uv[2] - uv[0], [0, 0]))
        axes = np.linalg.solve(A, b)
        out.append({'p': p, 'n': n, 'd': float(n @ p[0]), 'm': int(face[3]), 'axes': axes,
                    'off': uv[0] - p[0] @ axes})
    return out


def _compatible(seed, t, texsize):
    if t['m'] != seed['m'] or float(seed['n'] @ t['n']) < 1 - 1e-6:
        return False
    if np.max(np.abs(t['p'] @ seed['n'] - seed['d'])) > PLANE_EPS:
        return False
    diff = (t['p'] @ t['axes'] + t['off']) - (t['p'] @ seed['axes'] + seed['off'])
    diff -= np.round(diff.mean(axis=0))
    return float(np.abs(diff).max()) * texsize <= TOL_TEXELS


def _regions(tris, texsize):
    vid = {}
    idx = [[vid.setdefault(tuple(np.round(q, 3)), len(vid)) for q in t['p']] for t in tris]
    pos = np.zeros((len(vid), 3))
    seen = np.zeros(len(vid), dtype=bool)
    for ix, t in zip(idx, tris):
        for k, q in zip(ix, t['p']):
            if not seen[k]:
                pos[k] = q
                seen[k] = True
    edges = defaultdict(list)
    for i, ix in enumerate(idx):
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edges[(min(ix[a], ix[b]), max(ix[a], ix[b]))].append(i)
    nb = defaultdict(set)
    for owners in edges.values():
        if len(owners) == 2:
            i, j = owners
            nb[i].add(j)
            nb[j].add(i)
    region = [-1] * len(tris)
    out = []
    for s in range(len(tris)):
        if region[s] >= 0:
            continue
        rid = len(out)
        region[s] = rid
        members, todo = [s], sorted(nb[s])
        while todo:
            t = todo.pop(0)
            if region[t] >= 0 or not _compatible(tris[s], tris[t], texsize):
                continue
            region[t] = rid
            members.append(t)
            todo.extend(sorted(j for j in nb[t] if region[j] < 0))
        out.append(members)
    return out, idx, pos


def _convex(cycle, pos, n):
    if len(cycle) > MAX_VERTS:
        return False
    k = len(cycle)
    for i in range(k):
        a, b, c = pos[cycle[i - 1]], pos[cycle[i]], pos[cycle[(i + 1) % k]]
        if float(np.cross(b - a, c - b) @ n) < -1e-6:
            return False
    return True


def _convex_split(members, idx, pos, n):
    polys = {i: list(idx[t]) for i, t in enumerate(members)}
    changed = True
    while changed:
        changed = False
        owner = {}
        for pid, cyc in polys.items():
            for i in range(len(cyc)):
                owner[(cyc[i], cyc[(i + 1) % len(cyc)])] = pid
        cand = sorted((-float(np.linalg.norm(pos[a] - pos[b])), p, owner[(b, a)], a, b)
                      for (a, b), p in owner.items() if (b, a) in owner and p < owner[(b, a)])
        for _, p, q, a, b in cand:
            merged = _union(polys[p], polys[q])
            if merged is None or not _convex(merged, pos, n):
                continue
            polys[p] = merged
            del polys[q]
            changed = True
            break
    return [pos[c] for _, c in sorted(polys.items())]


def _union(P, Q):
    """The boundary of two faces that share one or more consecutive edges (every shared edge removed), or None
    when it is not one simple cycle."""
    edges = [(P[i], P[(i + 1) % len(P)]) for i in range(len(P))] + [(Q[i], Q[(i + 1) % len(Q)]) for i in range(len(Q))]
    present = set(edges)
    rest = [(x, y) for x, y in edges if (y, x) not in present]
    after = {}
    for x, y in rest:
        if x in after:
            return None
        after[x] = y
    start = min(after)
    cycle, x = [start], after[start]
    while x != start:
        if x not in after or len(cycle) > len(rest):
            return None
        cycle.append(x)
        x = after[x]
    return cycle if len(cycle) == len(rest) else None


def _lead_with_corner(points, n):
    """The polygon rotated to start at its sharpest corner: the face's plane is taken from its first
    three points (prepare_mesh_bsp._prepare_placement), which must not be collinear."""
    k = len(points)
    area = [float(np.cross(points[(i + 1) % k] - points[i], points[(i + 2) % k] - points[i]) @ n) for i in range(k)]
    start = int(np.argmax(area))
    return np.roll(points, -start, axis=0)


def merged_polygons(v, f, texsize):
    """The planar-merge face list (patch, material, axes, offset, normal), axes per Quake unit."""
    from mesh_geometry import split_surface
    tris = _triangles(np.asarray(v, float), np.asarray(f, int))
    regions, idx, pos = _regions(tris, texsize)
    out = []
    for members in regions:
        s = tris[members[0]]
        ax = np.column_stack((s['axes'].T * texsize, s['off'] * texsize))
        for poly in _convex_split(members, idx, pos, s['n']):
            for patch in split_surface(poly, ax):
                out.append((_lead_with_corner(np.asarray(patch, float), s['n']), s['m'], s['axes'], s['off'], s['n']))
    return out


def converter_polygons(v, f, texsize):
    """The converter's own face list (mesh_geometry.surface_polygons + split_surface)."""
    from mesh_geometry import split_surface, surface_polygons
    return [(patch, mat, ax, off, normal) for poly, mat, ax, off, normal in surface_polygons(v, f)
            for patch in split_surface(poly, np.column_stack((ax.T * texsize, off * texsize)))]


def polygons(v, f, texsize):
    """(faces, method): the merged face list when it has fewer faces than the converter's, else the
    converter's. method is 'merge' or 'converter'."""
    base = converter_polygons(v, f, texsize)
    merged = merged_polygons(v, f, texsize)
    return (merged, 'merge') if len(merged) < len(base) else (base, 'converter')
