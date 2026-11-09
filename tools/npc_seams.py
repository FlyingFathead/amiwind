# SPDX-License-Identifier: GPL-3.0-only
"""Seam locks of a whole NPC body (NPC-BODY-REGRESSION-62, the body reduction design step 3, 3.1).

Every body part is reduced on its own. The joints between parts are decided once for the whole outfit, before any
shape is reduced: for each rim loop of a shape, the run of its rim vertices that lie within NEAR of a rim vertex of
another shape is a shared polyline; Douglas-Peucker at DP_TOL picks a subset of it, and that subset is locked in the
shape and the matched vertices are locked in its neighbour. Both sides keep the same points, so the seam cannot open
(the chord error stays under DP_TOL, half the joint audit's tolerance).

Vertex indices are those of the shape's frame-0 positions welded as npc_geometry._bake welds them
(np.unique of the positions rounded to 5 decimals).
"""
from collections import Counter, defaultdict

import numpy as np

NEAR = 0.05            # a rim vertex this close to another shape's rim vertex is on the joint (npc_seam_audit.NEAR)
DP_TOL = 0.125         # npc_seam_audit.TOL / 2
BOUNDARY_WEIGHT = 4.0  # the boundary-plane quadric's weight (mold_shell.quadric_simplify)


def weld(shape):
    """(points, faces) of a shape's frame 0, welded as _bake welds it."""
    points, inverse = np.unique(np.round(shape['positions'][0], 5), axis=0, return_inverse=True)
    return points, inverse.reshape(-1)[np.asarray(shape['faces'])].astype(np.int32)


def rim_loops(faces):
    """The rim (one-face edge) chains of a face list, as vertex lists."""
    uses = Counter(tuple(sorted((int(t[i]), int(t[(i + 1) % 3])))) for t in faces for i in range(3))
    adjacent = defaultdict(list)
    for (x, y), n in uses.items():
        if n == 1:
            adjacent[x].append(y)
            adjacent[y].append(x)
    seen, loops = set(), []
    for start in adjacent:
        if start in seen:
            continue
        loop, prev, cur = [start], None, start
        seen.add(start)
        while True:
            nxt = [n for n in adjacent[cur] if n != prev and n not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            loop.append(cur)
            seen.add(cur)
        loops.append(loop)
    return loops


def douglas_peucker(points, tol):
    """Indices of a closed or open polyline's points that Douglas-Peucker keeps at TOL (both far ends always)."""
    n = len(points)
    if n <= 3:
        return set(range(n))
    d = np.linalg.norm(points[:, None] - points[None], axis=2)
    i0, j0 = map(int, np.unravel_index(d.argmax(), d.shape))
    keep = {i0, j0}

    def split(i, j):
        seq = list(range(i, j + 1)) if i < j else list(range(i, n)) + list(range(0, j + 1))
        if len(seq) <= 2:
            return
        a, b = points[seq[0]], points[seq[-1]]
        ab = b - a
        length = np.linalg.norm(ab)
        inner = seq[1:-1]
        p = points[inner]
        if length < 1e-9:
            dist = np.linalg.norm(p - a, axis=1)
        else:
            dist = np.linalg.norm(p - (a + np.clip((p - a) @ ab / (length * length), 0, 1)[:, None] * ab), axis=1)
        k = int(dist.argmax())
        if dist[k] > tol:
            keep.add(inner[k])
            split(seq[0], inner[k])
            split(inner[k], seq[-1])
    split(i0, j0)
    split(j0, i0)
    return keep


def lock_mode():
    """AMIWIND_NPC_SEAM_LOCKS: rims (the default: every rim vertex of every shape locked, joints and free hems alike,
    so no rim can move or open; Jiub: 0 new open edges at today's 620 faces), full (every vertex of a joint rim locked
    on both sides) or dp (the Douglas-Peucker subset of a joint rim at DP_TOL, fewer faces). Read here only."""
    import os
    value = os.environ.get('AMIWIND_NPC_SEAM_LOCKS', '').strip() or 'rims'
    if value not in ('full', 'dp', 'rims'):
        raise ValueError('AMIWIND_NPC_SEAM_LOCKS must be full, dp or rims')
    return value


def joint_locks(shapes, skip=()):
    """[set of welded vertex indices] per shape: the seam vertices both sides of every joint keep (SKIP: shape indices
    left out, e.g. a head kept whole)."""
    mode = lock_mode()
    full = mode in ('full', 'rims')
    from scipy.spatial import cKDTree
    welded = [weld(s) for s in shapes]
    rims = [set(int(v) for t in rim_loops(f) for v in t) for _, f in welded]
    trees = [cKDTree(p) for p, _ in welded]
    # 'rims': every rim vertex of every shape (free hems too), so no rim edge can move or open
    locks = [set(r) if mode == 'rims' and i not in skip else set() for i, r in enumerate(rims)]
    for i, (pi, fi) in enumerate(welded):
        if i in skip or not rims[i]:
            continue
        for j, (pj, fj) in enumerate(welded):
            if j == i or j in skip or not rims[j]:
                continue
            for loop in rim_loops(fi):
                dist, near = trees[j].query(pi[loop])
                matched = [(v, int(k)) for v, d, k in zip(loop, dist, near) if d < NEAR and int(k) in rims[j]]
                if len(matched) < 3:
                    continue
                keep = range(len(matched)) if full else douglas_peucker(pi[[v for v, _ in matched]], DP_TOL)
                for t in keep:
                    locks[i].add(int(matched[t][0]))
                    locks[j].add(matched[t][1])
    return locks


def seam_quotas(shapes, total):
    """Per-shape face quotas for a TOTAL with every shape's seams locked: each shape's fewest faces under its locks,
    the rest shared in proportion to the faces above that; None when the fewest do not fit TOTAL."""
    locks = joint_locks(shapes)
    welded = [weld(s) for s in shapes]
    least, source = [], []
    for i, (p, f) in enumerate(welded):
        source.append(len(f))
        least.append(len(simplify_body(p, f, 4, locks[i])[1]) if len(f) > 4 else len(f))
    if sum(least) > total:
        return None
    spare = total - sum(least)
    room = max(1, sum(source) - sum(least))
    # the quotas count the source faces; a few more than the fewest stay as a margin for the locked reducer
    return [max(1, min(source[i], least[i] + int(spare * (source[i] - least[i]) / room) - 2))
            for i in range(len(shapes))]


def simplify_body(points, faces, quota, locked):
    """One body shape reduced with its seam vertices LOCKED and its free rims held (the boundary term)."""
    from mold_shell import quadric_simplify
    from static_lod import LOCKED_MAX_TURN
    v, f = quadric_simplify(points, faces, [int(quota)], max_turn=LOCKED_MAX_TURN, locked=locked, anchored=True,
                            boundary_weight=BOUNDARY_WEIGHT)[int(quota)]
    return np.asarray(v, float), np.asarray(f, np.int32)
