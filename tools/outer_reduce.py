# SPDX-License-Identifier: GPL-3.0-only
"""The outer-measures reduction of an actor model (MESH-SEAM-METHOD-62, docs/MODEL_REDUCTION.md section 8): one rule
for the residents and the creatures.

The whole model is welded (positions rounded to WELD decimals, so the parts that share points at a seam become one
surface) and reduced as ONE closed surface by the manifold quadric reducer (mold_shell.quadric_simplify: the link
condition, the anchored turn limit, no new rim). The six extreme points
are locked, so the model's box stays the original's; the original's own open rims (a skirt's hem) may thin along
themselves (the boundary term) but not pull inward. Every face's quadric is weighed by (median radius / the radius
of the bone that moves it)^2, so an error on a thin limb costs as much as a proportionally larger one on the body; a
bone whose girth still falls under outer_hull.GIRTH_KEEP gets BOOST times its weight and the reduction runs again, up
to ROUNDS rounds. The result is kept only when it passes tools/outer_hull.py (extent, girth by bone, no lost piece,
hull, no new open edge, joins closed); each reduced face is then given to the shape it lies on and the bake's own
texture and frame work (npc_geometry._bake, with this geometry as its per-shape reduction: given) makes the model.

Within today's triangles only (the coordinator's rule, 2026-11-20, the +2 % triangle cap): the bake makes today's model
first and tries this reduction at today's face count; the new model replaces it only when it passes. A model that
does not pass keeps today's output. AMIWIND_ACTOR_REDUCER: outer (the default: as above) or today (never tried, the
model of v0.0.67 byte for byte). mold_shell and npc_geometry themselves are not changed: the weights apply for the
length of one call (weighted) and the reduced geometry for the length of one bake (given), so the static meshes'
units and the build stages that import the bake keep their keys (npc_geometry is in the key of 31 of the v0.0.67
release's 50 stages, the chim stage among them; this file only in the actor stages').

Two modes for the shared-vertex comparison on the Pi (A/B, not for a release build): shared (the reduction at today's
face count, kept whether or not it passes, written on shared vertices: npc_geometry.shared_vertex_mdl, the model's
original textures in one atlas, each vertex posed once) and needed (the fewest faces, from today's count up, at which
the reduction passes, found by halving in steps of NEEDED_STEP, on shared vertices: the models of over 1,024 faces the
per-face tiles cannot hold). The engine draws any triangle count on at most SHARED_VERTEX_LIMIT shared vertices.
"""
import os
from contextlib import contextmanager

import numpy as np

MODES = ('outer', 'today', 'shared', 'needed')
SHARED_MODES = ('shared', 'needed')
SHARED_VERTEX_LIMIT = 2000  # engine/aga/src/model.c AW_AliasBudgetAllows: any triangle count on at most 2,000 vertices
NEEDED_STEP = 40            # faces: the needed count's precision
NEEDED_MAX = 1600           # faces: the needed search's ceiling (and the source's own count; the budget sheet's largest
                            # need was the Alit's 1,314)
NEAREST = 12               # source triangles tried per point for its closest point
WELD = 3                # decimals: points closer than this are one point of the welded surface
ROUNDS = 6              # reductions per model at most (the adaptive girth weights; Weerhat passed in the fifth)
BOOST = 4.0             # a bone that failed its girth: its faces' weight times this, per round
WEIGHT_RANGE = (1.0, 25.0)
MIN_RADIUS = 0.05       # Quake units: a bone's radius is never taken as smaller (a weight's ceiling)
THIN_RIMS = True        # the original's open rims thin along themselves (mold_shell boundary_weight 1.0), not kept whole
MARGIN = 0.08           # girth sought over outer_hull.GIRTH_KEEP: the pose box's byte grid costs a thin limb some
                        # (Weerhat's forearm: 0.81 reduced, 0.75 as drawn)


def mode():
    """AMIWIND_ACTOR_REDUCER: outer (default), today, shared or needed (the A/B modes). Read here only."""
    value = os.environ.get('AMIWIND_ACTOR_REDUCER', '').strip() or 'outer'
    if value not in MODES:
        raise ValueError('AMIWIND_ACTOR_REDUCER must be outer, today, shared or needed')
    return value


def weld(points, faces, decimals=WELD):
    """(welded points, welded faces, the source face index of each welded face): degenerate faces and repeats of
    one face (the same three points in the same order) left out."""
    points = np.asarray(points, float)
    faces = np.asarray(faces)[:, :3]
    pts, inv = np.unique(np.round(points, decimals), axis=0, return_inverse=True)
    ff = np.asarray(inv).reshape(-1)[faces]
    good = np.flatnonzero((ff[:, 0] != ff[:, 1]) & (ff[:, 1] != ff[:, 2]) & (ff[:, 0] != ff[:, 2]))
    ff, first = np.unique(ff[good], axis=0, return_index=True)
    return pts, ff, good[first]


def group_of_faces(groups, count):
    """Each source face's group name ('' for none): GROUPS {name: source face indices}."""
    out = np.full(count, '', dtype=object)
    for name, idx in groups.items():
        out[np.asarray(idx, int)] = name
    return out


def weights(src_points, src_faces, face_group):
    """Per source face: (median radius / its group's radius)^2 within WEIGHT_RANGE (1 for faces of no group). A
    group's radius: the RMS spread of its faces' points across their two narrow principal axes."""
    radius = {}
    for name in set(face_group.tolist()) - {''}:
        pts = np.asarray(src_points, float)[np.unique(np.asarray(src_faces)[face_group == name])]
        if len(pts) < 4:
            continue
        sv = np.linalg.svd(pts - pts.mean(0), full_matrices=False)[1] / np.sqrt(len(pts))
        radius[name] = max(float(np.sqrt((sv[1] ** 2 + sv[2] ** 2) / 2)), MIN_RADIUS)
    if not radius:
        return np.ones(len(face_group))
    med = float(np.median(list(radius.values())))
    return np.array([np.clip((med / radius[g]) ** 2, *WEIGHT_RANGE) if g in radius else 1.0 for g in face_group])


@contextmanager
def weighted(face_weight):
    """mold_shell.quadric_simplify with every face's plane quadric times FACE_WEIGHT (in the order the faces are
    given), for the length of the block; the module is the same file outside it."""
    import mold_shell
    original = mold_shell._plane_quadric
    calls = [0]

    def plane_quadric(p0, p1, p2):
        k = original(p0, p1, p2)
        i = calls[0]
        calls[0] += 1
        return k * face_weight[i] if i < len(face_weight) else k
    mold_shell._plane_quadric = plane_quadric
    try:
        yield
    finally:
        mold_shell._plane_quadric = original


class OutOfOrder(RuntimeError):
    """The bake asked its reducer for another shape than the next one given (given): today's model stands."""


def _stays(points, *args, **kwargs):
    return points, 0


@contextmanager
def given(shapes, entries):
    """npc_geometry._bake with ENTRIES [(exact, points, faces)] per shape of SHAPES as its per-shape reduction, for
    the length of the block. The bake calls its reducer (simplify_shape) once per shape that has faces, in shape
    order, when its quota is under the shape's faces (outer_bake gives every quota 0); each call returns the next
    shape's reduced geometry, and the whole hair's pushes (the head under the hair, the hair outside the head) leave
    it where the reduction put it and the check judged it. A call with another shape's points raises OutOfOrder.
    Yields a function that is True once every given shape was taken. npc_geometry is the same file outside it."""
    import npc_geometry as G
    queue = [(len(np.unique(np.round(np.asarray(s['positions'][0], float), 5), axis=0)), entries[i][1], entries[i][2])
             for i, s in enumerate(shapes) if len(s['faces'])]
    taken = [0]

    def simplify_shape(points, faces, quota, preserve_shell=False):
        k = taken[0]
        if k >= len(queue) or len(points) != queue[k][0]:
            raise OutOfOrder('the bake asked for shape %d of %d out of the order given' % (k, len(queue)))
        taken[0] = k + 1
        return queue[k][1], queue[k][2]
    names = ('simplify_shape', 'keep_head_inside_cover', 'keep_outside_surface')
    original = {name: getattr(G, name) for name in names}
    G.simplify_shape, G.keep_head_inside_cover, G.keep_outside_surface = simplify_shape, _stays, _stays
    try:
        yield lambda: taken[0] == len(queue)
    finally:
        for name, function in original.items():
            setattr(G, name, function)


def locked_points(pts, ff, thin_rims=False):
    """The points the reduction keeps: the original's own open rims (unless THIN_RIMS) and the six extreme points."""
    from static_lod import boundary_vertices
    locked = set() if thin_rims else set(int(v) for v in boundary_vertices(np.asarray(ff, dtype=np.int64)))
    used = np.unique(ff)
    for axis in range(3):
        locked.add(int(used[np.argmin(pts[used, axis])]))
        locked.add(int(used[np.argmax(pts[used, axis])]))
    return locked


def reduce(shapes, target, groups, rounds=ROUNDS, thin_rims=False, keep_failing=False):
    """(points, faces, outer_hull row) of the welded whole reduced to TARGET faces or fewer, passing the outer-hull
    check; None when no round passes. SHAPES: the source (positions[0] the pose the check reads); GROUPS: {part:
    source face indices} (outer_hull.body_groups / creature_groups). KEEP_FAILING: the last round's result (its row's
    problems listed) when none passes, and the welded whole itself when it has TARGET faces or fewer (mode shared)."""
    import outer_hull as H
    from mold_shell import quadric_simplify
    sp, sf = H.source_whole(shapes)
    pts, ff, source_face = weld(sp, sf)
    if len(ff) <= target:
        if keep_failing:
            row = H.measure(shapes, pts, ff, groups)
            row['problems'] = H.problems(row)
            return pts, ff, row
        return None                 # nothing to reduce: today's model stands
    if all('bone_name' in s for s in shapes):
        # every face by the bone that moves it (all its pieces), the groups' names for the girth's bones
        source_group = H._face_label(np.concatenate([np.asarray(s['bone_name'], dtype=object) for s in shapes]), sf)
        source_group = np.array([g if g in groups else '' for g in source_group.tolist()], dtype=object)
    else:
        source_group = group_of_faces(groups, len(sf))
    face_group = source_group[source_face]
    base = weights(sp, sf, source_group)[source_face]
    locked = sorted(locked_points(pts, ff, thin_rims))
    boost = np.ones(len(ff))
    last = None
    for _ in range(rounds):
        with weighted(base * boost):
            v, f = quadric_simplify(pts, ff, [int(target)], max_turn=0.3, locked=locked, anchored=True,
                                    boundary_weight=1.0 if thin_rims else 0.0)[int(target)]
        if len(f) > target and not keep_failing:
            return None             # (KEEP_FAILING: the reducer's nearest count is kept, its faces recorded)
        last = (v, f)
        thin = {k.split(' #')[0] for k, g in H.girth(sp, sf, v, f, groups).items() if g < H.GIRTH_KEEP + MARGIN}
        if not thin:
            row = H.measure(shapes, v, f, groups)
            row['problems'] = H.problems(row)
            return (v, f, row) if not row['problems'] or keep_failing else None
        for name in thin:
            boost[face_group == name] *= BOOST
    if keep_failing and last is not None:
        row = H.measure(shapes, last[0], last[1], groups)
        row['problems'] = H.problems(row)
        return last[0], last[1], row
    return None


def labelled(shapes, sources, parents=None, bone_names=None):
    """Copies of SHAPES with each vertex's bone ('bone_name', outer_hull.label_bones: export_actor-like SOURCES,
    carried onto BONE_NAMES up PARENTS when both are given); None when they do not match."""
    import outer_hull as H
    out = [dict(s) for s in shapes]
    ok = H.label_bones(out, sources, parents, set(bone_names) if parents is not None and bone_names else None)
    return out if ok else None


def outer_bake(shapes, materials, textures, palette, sources, target, parents=None, bone_names=None):
    """The bake's model made by this reduction at TARGET faces (today's count): (frames, faces, uv, skin, row) as
    npc_geometry.bake returns them plus the outer-hull row, or None (today's model stands). SHAPES: the bake's input
    (npc_geometry.assemble shapes, frame 0 the rest pose; the skeletal bake's extra shape-tag frame carried too)."""
    import mesh_seam_check as M
    import npc_geometry as G
    import outer_hull as H
    named = labelled(shapes, sources, parents, bone_names)
    if named is None:
        return None
    groups = H.bone_faces(named) or H.shape_faces(named)
    # the open rims thinned along themselves rather than kept whole (measured 2026-11-20: Weerhat passes at today's
    # 664 with them thinned, needs 744 with them kept; no model passed with them kept that failed thinned)
    found = reduce(named, target, groups, thin_rims=THIN_RIMS)
    if found is None:
        return None
    v, f, row = found
    owner = M.assign_faces(named, v, f)
    entries = [(False, v, f[owner == i]) for i in range(len(shapes))]
    limit = next((lim for lim in G.ALIAS_FACE_LIMITS if lim >= len(f)), G.ALIAS_FACE_LIMITS[-1])
    try:
        with given(shapes, entries) as complete:
            frames, faces, uv, skin = G._bake(shapes, materials, textures, palette, limit, None, [0] * len(shapes),
                                              None, frozenset(), len(f) > 960)
            if not complete():
                return None
    except OutOfOrder:
        return None
    return frames, faces, uv, skin, row


def closest_bary(p, a, b, c):
    """The barycentric coordinates (n, 3) of the closest point of each triangle (a, b, c) to each point P (all (n, 3)):
    the regions of the triangle's corners, edges and face, in the order of Ericson's closest-point test."""
    ab, ac = b - a, c - a
    ap, bp, cp = p - a, p - b, p - c
    d1, d2 = (ab * ap).sum(1), (ac * ap).sum(1)
    d3, d4 = (ab * bp).sum(1), (ac * bp).sum(1)
    d5, d6 = (ab * cp).sum(1), (ac * cp).sum(1)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    denom = va + vb + vc
    denom = np.where(np.abs(denom) < 1e-12, 1e-12, denom)
    v, w = vb / denom, vc / denom
    out = np.column_stack((1 - v - w, v, w))

    def put(mask, coords):
        out[mask] = coords[mask] if np.ndim(coords) == 2 else coords

    def safe(x, y):
        return x / np.where(np.abs(y) < 1e-12, 1e-12, y)
    t = safe(d4 - d3, (d4 - d3) + (d5 - d6))
    put((va <= 0) & (d4 - d3 >= 0) & (d5 - d6 >= 0), np.column_stack((0 * t, 1 - t, t)))
    t = safe(d2, d2 - d6)
    put((vb <= 0) & (d2 >= 0) & (d6 <= 0), np.column_stack((1 - t, 0 * t, t)))
    put((d6 >= 0) & (d5 <= d6), np.array([0.0, 0.0, 1.0]))
    t = safe(d1, d1 - d3)
    put((vc <= 0) & (d1 >= 0) & (d3 <= 0), np.column_stack((1 - t, t, 0 * t)))
    put((d3 >= 0) & (d4 <= d3), np.array([0.0, 1.0, 0.0]))
    put((d1 <= 0) & (d2 <= 0), np.array([1.0, 0.0, 0.0]))
    return out


def nearest_triangles(points, tris, k=NEAREST):
    """(triangle index, barycentric (n, 3), distance) of the closest of TRIS (m, 3, 3) to each of POINTS, among the
    K whose centres are nearest."""
    from scipy.spatial import cKDTree
    points = np.asarray(points, float)
    k = max(1, min(int(k), len(tris)))
    _, cand = cKDTree(tris.mean(1)).query(points, k=k)
    cand = np.asarray(cand).reshape(len(points), -1)
    best = np.full(len(points), np.inf)
    index = np.zeros(len(points), int)
    bary = np.zeros((len(points), 3))
    for j in range(cand.shape[1]):
        t = cand[:, j]
        b = closest_bary(points, tris[t, 0], tris[t, 1], tris[t, 2])
        d = np.linalg.norm(points - (b[:, :, None] * tris[t]).sum(1), axis=1)
        better = d < best
        best[better], index[better], bary[better] = d[better], t[better], b[better]
    return index, bary, best


def charts(faces, count):
    """Each source face's texture chart: the connected pieces of a shape's faces over shared vertex indices (a texture
    seam is a row of vertices the source repeats with other texture coordinates)."""
    parent = np.arange(count)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b, c in np.asarray(faces)[:, :3]:
        for u, w in ((a, b), (b, c)):
            ru, rw = find(u), find(w)
            if ru != rw:
                parent[ru] = rw
    return np.array([find(a) for a in np.asarray(faces)[:, 0]])


def shared_shapes(shapes, points, faces, owner):
    """Per shape of SHAPES (the source, frame 0 the rest pose), the reduced FACES on POINTS that OWNER gives it, on
    vertices of its own (positions: one frame). Each face lies in the texture chart of its nearest source triangle
    (charts); a vertex is shared by the faces of one chart, its texture coordinates and colour those of the closest
    point of that chart's source surface, so a vertex on a texture seam is one vertex per chart and no face is
    stretched across a seam. Returns ([shape], {'vertices', 'charts'})."""
    points = np.asarray(points, float)
    faces = np.asarray(faces)[:, :3]
    out, chart_count = [], 0
    for i, s in enumerate(shapes):
        mine = faces[np.asarray(owner) == i]
        src = np.asarray(s['positions'][0], float)
        sf = np.asarray(s['faces'])[:, :3]
        colours = np.asarray(s.get('colours', np.ones((len(src), 4))), float)
        base = {k: val for k, val in s.items() if k not in ('positions', 'faces', 'uv', 'colours', 'bone_name')}
        if not len(mine) or not len(sf):
            out.append({**base, 'positions': np.zeros((1, 0, 3)), 'faces': np.zeros((0, 3), int),
                        'uv': np.zeros((0, 2)), 'colours': np.ones((0, 4))})
            continue
        tris, uvt, colt = src[sf], np.asarray(s['uv'], float)[sf], colours[sf]
        chart = charts(sf, len(src))
        face_chart = chart[nearest_triangles(points[mine].mean(1), tris)[0]]
        pts, uv, col = [], [], []
        local = np.zeros(mine.shape, int)
        for c in np.unique(face_chart):
            in_chart = np.flatnonzero(face_chart == c)
            used, inverse = np.unique(mine[in_chart], return_inverse=True)
            own = np.flatnonzero(chart == c)
            t, b, _ = nearest_triangles(points[used], tris[own])
            local[in_chart] = sum(len(p) for p in pts) + np.asarray(inverse).reshape(-1, 3)
            pts.append(points[used])
            uv.append((b[:, :, None] * uvt[own][t]).sum(1))
            col.append((b[:, :, None] * colt[own][t]).sum(1))
        chart_count += len(np.unique(face_chart))
        out.append({**base, 'positions': np.concatenate(pts)[None], 'faces': local,
                    'uv': np.clip(np.concatenate(uv), 0.0, 1.0), 'colours': np.concatenate(col)})
    return out, {'vertices': int(sum(s['positions'].shape[1] for s in out)), 'charts': int(chart_count)}


def shared_bake(shapes, materials, textures, palette, sources, targets, parents=None, bone_names=None,
                keep_failing=False):
    """The bake's model made by this reduction on shared vertices (npc_geometry.shared_vertex_mdl) at the first of
    TARGETS (face counts) where it passes (or, KEEP_FAILING, at TARGETS[0] whatever it gives): (frames, faces, uv,
    skin, row, facts) with the frames the rest pose and the shape tag (skeletal_actor.SHAPE_TAG), or None. SHAPES: the
    skeletal bake's tagged input (frame 0 the rest pose)."""
    import mesh_seam_check as M
    from npc_geometry import shared_vertex_mdl
    from skeletal_actor import SHAPE_TAG
    named = labelled(shapes, sources, parents, bone_names)
    if named is None:
        return None
    groups = hull_groups(named)
    for target in targets:
        found = reduce(named, int(target), groups, thin_rims=THIN_RIMS, keep_failing=keep_failing)
        if found is None:
            continue
        v, f, row = found
        owner = M.assign_faces(named, v, f)
        parts, facts = shared_shapes(named, v, f, owner)
        if facts['vertices'] > SHARED_VERTEX_LIMIT:
            continue
        tagged = [{**s, 'positions': np.concatenate((s['positions'][:1],
                                                     s['positions'][:1] + [(k + 1) * SHAPE_TAG, 0, 0]))}
                  for k, s in enumerate(parts)]
        frames, faces, uv, skin = shared_vertex_mdl(*tinted(tagged, materials, textures), palette)
        return frames, faces, uv, skin, row, dict(facts, target=int(target), faces=int(len(faces)))
    return None


def tinted(shapes, materials, textures):
    """(shapes, materials, textures) for npc_geometry.shared_vertex_mdl, which takes plain vertex colours and diffuse
    only: a shape with a tint (its material's diffuse, its vertices' mean colour) gets its texture tinted by it as a
    texture of its own (one per texture and tint), its colours plain. A shape without a tint keeps its material."""
    shapes, materials, textures = list(shapes), list(materials), dict(textures)
    made = {}
    for i, s in enumerate(shapes):
        m = materials[s['material']]
        colour = np.asarray(s['colours'], float)
        mean = colour[:, :3].mean(0) if len(colour) else np.ones(3)
        tint = np.asarray(m.get('diffuse', (1.0, 1.0, 1.0)), float)[:3] * mean
        if np.allclose(tint, 1.0) and (not len(colour) or np.allclose(colour[:, :3], 1.0)):
            continue
        key = (m.get('texture_index'), tuple(np.round(tint, 3)))
        if key not in made:
            base = textures.get(m.get('texture_index'))
            image = np.full((4, 4, 4), 220, np.uint8) if base is None else np.array(base, copy=True)
            image[:, :, :3] = np.clip(image[:, :, :3].astype(float) * tint, 0, 255).astype(np.uint8)
            name = ('tinted', len(made))
            textures[name] = image
            materials.append({**m, 'texture_index': name, 'diffuse': [1.0, 1.0, 1.0]})
            made[key] = len(materials) - 1
        shapes[i] = {**s, 'material': made[key], 'colours': np.ones_like(colour)}
    return shapes, materials, textures


def hull_groups(named):
    """The outer-hull groups of labelled shapes (outer_hull.bone_faces, else shape_faces)."""
    import outer_hull as H
    return H.bone_faces(named) or H.shape_faces(named)


def needed_bake(shapes, materials, textures, palette, sources, today, parents=None, bone_names=None, accept=None):
    """shared_bake at the fewest faces, from TODAY up to NEEDED_MAX (or the source's own count), at which the
    reduction passes and ACCEPT (found -> bool: the caller's check of the model as drawn) takes it, to NEEDED_STEP
    faces: today's count first, then the ceiling, then halving. None when the ceiling fails."""
    import outer_hull as H
    named = labelled(shapes, sources, parents, bone_names)
    if named is None:
        return None

    def at(target):
        found = shared_bake(shapes, materials, textures, palette, sources, [target], parents, bone_names)
        return found if found is not None and (accept is None or accept(found)) else None
    lo = int(today)
    best = at(lo)
    if best is not None:
        return best
    hi = min(len(H.source_whole(named)[1]), NEEDED_MAX)
    best = at(hi) if hi > lo else None
    if best is None:
        return None
    while hi - lo > NEEDED_STEP:
        mid = (lo + hi) // 2
        found = at(mid)
        if found is None:
            lo = mid
        else:
            hi, best = mid, found
    return best


def accepts(shapes, sources, points, faces, parents=None, bone_names=None):
    """The outer-hull row of a baked model (POINTS: its rest frame as the engine reads it, FACES) against SHAPES when
    it passes, else None: the model the bake ships is the one judged (the pose box's byte grid moves every point by
    up to half a step, which a thin limb's girth feels)."""
    row = drawn_row(shapes, sources, points, faces, parents, bone_names)
    return row if row is not None and not row['problems'] else None


def drawn_row(shapes, sources, points, faces, parents=None, bone_names=None):
    """The outer-hull row of a baked model (POINTS: its rest frame as the engine reads it, FACES) against SHAPES,
    passing or not; None when the shapes' bones cannot be labelled."""
    import outer_hull as H
    named = labelled(shapes, sources, parents, bone_names)
    if named is None:
        return None
    row = H.measure(named, points, faces, hull_groups(named))
    row['problems'] = H.problems(row)
    return row


def summary(row, reducer='outer', **more):
    """The receipt's line of a model made by this reduction (MORE: a shared model's vertices, target, seam faces)."""
    return {'reducer': reducer, 'extent': row['extent'], 'least_girth': row['least_girth'], 'hull': row['hull'],
            'open': row['open'], 'seam_gap': row['seam_gap'], 'lost': len(row.get('lost', [])),
            **({'passes': not row.get('problems')} if reducer != 'outer' else {}), **more}
