# SPDX-License-Identifier: GPL-3.0-only
"""Stairway collision mesh (stair collision method 1) and the geometric stair check.

Method 0 (the default, unchanged) builds a mesh's collision from convex proxies and then repairs what they bury on a
flight of stairs (mesh_geometry.mitigate_stairs, clear_visible_treads); a walk of the built frames (stair_walk.py)
proved the result. Method 1 builds each flight's collision so that it is walkable by construction and proves it by
arithmetic on the collision itself, with no walk:

- the rules are the game's movement rules: the player steps up at most STEP_HEIGHT (8.5 units here: Morrowind's
  34 units at the converter's scale of 0.25; OpenMW 0.51 components/misc/constants.hpp sStepSizeUp, used by
  apps/openmw/mwphysics/stepper.cpp) and stands on a surface whose normal z is at least WALKABLE_Z (0.69 here, about
  46 degrees: sMaxSlope 46, stepper.cpp isWalkableSlope); the standing box is player_hull.MINS/MAXS;
- a flight (mesh_geometry.flight_treads: three or more tread levels joined by climbable risers) keeps its collision
  when that collision already passes the check (an authored RootCollisionNode ramp through the nosings, a proxy that
  is a walkable ramp); otherwise its collision is replaced by ONE RAMP: the convex hull of its treads' corners and the
  same corners dropped under the lowest tread, whose top runs through the nosings (as a Quake mapper clips a stair);
  where that ramp would stand more than a step over a tread, be too steep, or cut through other drawn geometry (a
  spiral stair, a flight beside a wall that turns), ONE SOLID BLOCK PER TREAD instead (the tread's corners down to
  under the lowest tread), which the step rule climbs. The drawn steps are never changed;
- the check (check_flights) samples every drawn tread of every flight and, from the collision pieces' plane
  equations alone, finds what the standing box would stand on there: it must exist, stand at most a step over the
  drawn tread and at most a step under it (a ramp through the risers' feet sinks the feet into the drawn steps, as
  the original's own collision ramps do; a hole is a rise of two steps to the next tread), be walkable (normal z), leave the standing box's height
  free, and neighbouring samples (across a riser, along a ramp) whose drawn treads are at most a step apart must stand
  at most a step apart. Each failure names the flight, the tread level and the point.

Morrowind collides with the RootCollisionNode of a mesh, else with its drawn triangles (OpenMW 0.51
components/nifbullet/bulletnifloader.cpp); either is the collision mesh handed to collision_pieces here.
"""
import numpy as np
from scipy.spatial import ConvexHull, cKDTree

import mesh_geometry as mg

FLOOR_TOLERANCE = .5       # collision this little under a drawn tread is that tread's own surface (a plate's rounding)
SAMPLE_GRID = 4            # tread samples per triangle edge (barycentric grid; mesh_geometry.VISIBLE_TREAD_INSET)
NEIGHBOUR = 4.             # samples this close in plan are neighbours: their standing heights differ by a step at most
CUT_THROUGH = .5           # a ramp holding another drawn vertex deeper than this cuts through drawn geometry
CONVEX_SLACK = 1.15        # a tread whose hull covers more than this share of its own area is not one convex block
UNDER = 1.                 # ramps and blocks reach this far under the flight's lowest tread
RAMP_EPS = 1e-3
STAND_SLACK = .25          # a standing surface this little over a step above a drawn tread still counts (uneven treads)


def player():
    from player_hull import MINS, MAXS, STEP_HEIGHT, WALKABLE_Z
    return STEP_HEIGHT, WALKABLE_Z, MAXS[2] - MINS[2]


DETECTORS = ('levels', 'risers')
TOUCH = 2.5                # treads this close in plan meet at a step (a bevelled nosing between them: 1.6 on the Hlaalu steps)
RISE_MIN = 1.              # a rise under this is trim, not a step (the stair walk's RISE_MIN)


def flights(v, f, step=None, detector='levels', collision=None):
    """The flights of a mesh as drawn: a list of tread triangle index arrays.

    collision: the mesh's authored collision (its RootCollisionNode: (v, f)), or None (the drawn mesh collides). A
    drawn level face with nothing of it under it is not a tread: the original stands nobody there (OpenMW 0.51
    components/nifbullet/bulletnifloader.cpp collides with the RootCollisionNode alone). The roots of a Grazelands
    tree (flora_tree_gl_06: faces within 10 degrees of level, 1 to 2.5 units apart, over none of its collision)
    read as a flight without it (CHIM-STAIR-METHOD1-UNFIXED-48).

    levels (default): from the walkable level faces alone (level_flights): treads that meet in plan within TOUCH at a
    rise of RISE_MIN..step, along an edge the standing box fits (FLIGHT_WIDTH), FLIGHT_LEVELS or more levels in one
    such chain. risers: mesh_geometry.flight_treads (treads joined by a vertical riser at their very edge), the
    detector of method 0's stair rules; it finds no flight where a bevelled nosing sits between riser and tread
    (measured: ex_hlaalu_steps_03..07, ex_vivec_ps_01, ex_v_palace_steps_01, ex_de_docks_steps)."""
    if detector not in DETECTORS:
        raise ValueError('Unknown flight detector: %s' % detector)
    if detector == 'risers':
        return _riser_flights(v, f, step)
    return level_flights(v, f, step, collision)


def _riser_flights(v, f, step=None):
    """mesh_geometry.flight_treads' treads in staircases: joined where a riser pairs them (stair_treads) or where
    two level triangles of one tread share a corner."""
    keep = [int(t) for t in mg.flight_treads(v, f, step)]
    if not keep:
        return []
    pairs = []
    mg.stair_treads(v, f, step, pairs=pairs)
    parent = {t: t for t in keep}

    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for _, top, low in pairs:
        ids = [int(t) for t in top + low if int(t) in parent]
        for t in ids[1:]:
            parent[root(t)] = root(ids[0])
    tris = _tris(v, f)
    corner = {}
    for t in keep:
        h = float(tris[t][:, 2].mean())
        for k in np.round(tris[t] * 16).astype(np.int64).tolist():
            for o, oh in corner.setdefault(tuple(k), []):
                if abs(oh - h) < .25:
                    parent[root(t)] = root(o)
            corner[tuple(k)].append((t, h))
    found = {}
    for t in keep:
        found.setdefault(root(t), []).append(t)
    return [np.array(sorted(g), int) for g in sorted(found.values(), key=min)]


def _tread_groups(t, ids):
    """Level triangles t (of ids) joined into treads: same level (within .25) and sharing a corner. Lists of positions."""
    zc = t[:, :, 2].mean(axis=1)
    parent = list(range(len(ids)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    corner = {}
    for i in range(len(ids)):
        for k in np.round(t[i] * 16).astype(np.int64).tolist():
            for j in corner.setdefault(tuple(k), []):
                if abs(zc[i] - zc[j]) < .25:
                    parent[root(i)] = root(j)
            corner[tuple(k)].append(i)
    groups = {}
    for i in range(len(ids)):
        groups.setdefault(root(i), []).append(i)
    return sorted(groups.values(), key=min)


def _inside_plan(p, t):
    """True when plan point p lies inside one of the triangles t (their xy)."""
    a, b, c = t[:, 0, :2], t[:, 1, :2], t[:, 2, :2]
    v0, v1, v2 = b - a, c - a, p - a
    d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1)
    d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
    den = d00 * d11 - d01 * d01
    with np.errstate(divide='ignore', invalid='ignore'):
        u = (d11 * d20 - d01 * d21) / den
        w = (d00 * d21 - d01 * d20) / den
    return bool(((np.abs(den) > 1e-12) & (u > 1e-3) & (w > 1e-3) & (u + w < 1 - 1e-3)).any())


def _plan_distances(pts, e0, e1):
    """Plan distances from points pts (N, 2) to segments e0[k]-e1[k] (M, 2): (N, M)."""
    ab = e1 - e0
    l = np.maximum((ab * ab).sum(axis=1), 1e-12)
    t = np.clip(((pts[:, None, :] - e0[None]) * ab[None]).sum(axis=2) / l[None], 0, 1)
    return np.linalg.norm(e0[None] + ab[None] * t[..., None] - pts[:, None, :], axis=2)


def _boundary(t):
    """Boundary edges (plan, (K, 2) start and end) of triangles t: edges that belong to one triangle only."""
    count, ends = {}, {}
    for tri in t:
        for a, b in zip(tri, np.roll(tri, -1, axis=0)):
            key = tuple(sorted((tuple(np.round(a * 16).astype(np.int64)), tuple(np.round(b * 16).astype(np.int64)))))
            count[key] = count.get(key, 0) + 1
            ends[key] = (a[:2], b[:2])
    edges = [ends[k] for k, n in count.items() if n == 1]
    if not edges:
        return np.zeros((0, 2)), np.zeros((0, 2))
    return np.array([e[0] for e in edges]), np.array([e[1] for e in edges])


def _meeting_length(upper, lower, touch=TOUCH):
    """How long the plan boundary of tread triangles upper runs within touch of lower's boundary (sampled every half
    unit along upper's boundary edges)."""
    a0, a1 = _boundary(upper)
    b0, b1 = _boundary(lower)
    if not len(a0) or not len(b0):
        return 0.
    total = 0.
    for a, b in zip(a0, a1):
        length = float(np.linalg.norm(b - a))
        n = max(2, int(length / .5) + 1)
        pts = a + (b - a) * np.linspace(0, 1, n)[:, None]
        total += length * float((_plan_distances(pts, b0, b1).min(axis=1) <= touch).mean())
    return total


def _uncovered(tris, ids, coll, step):
    """Level faces ids of tris (drawn) under none of whose sample points (tread_samples) the authored collision
    triangles coll hold anything (no collision triangle over the point in plan reaching up to a step over it)."""
    if not len(ids):
        return set()
    pts, owner = tread_samples(tris, ids)
    a, b, c = coll[:, 0, :2], coll[:, 1, :2], coll[:, 2, :2]
    lo, hi = coll.min(axis=1), coll.max(axis=1)
    v0, v1 = b - a, c - a
    d00, d01, d11 = (v0 * v0).sum(1), (v0 * v1).sum(1), (v1 * v1).sum(1)
    den = d00 * d11 - d01 * d01
    good = np.abs(den) > 1e-12
    held = set()
    for p, i in zip(pts, owner):
        if int(i) in held:
            continue
        near = good & (lo[:, 0] <= p[0]) & (hi[:, 0] >= p[0]) & (lo[:, 1] <= p[1]) & (hi[:, 1] >= p[1]) \
            & (lo[:, 2] <= p[2] + step)
        if not near.any():
            continue
        v2 = p[:2] - a[near]
        d20, d21 = (v2 * v0[near]).sum(1), (v2 * v1[near]).sum(1)
        u = (d11[near] * d20 - d01[near] * d21) / den[near]
        w = (d00[near] * d21 - d01[near] * d20) / den[near]
        if ((u >= -1e-6) & (w >= -1e-6) & (u + w <= 1 + 1e-6)).any():
            held.add(int(i))
    return {int(i) for i in ids} - held


def level_flights(v, f, step=None, collision=None):
    """Flights from walkable level faces (the 'levels' detector of flights). collision: see flights."""
    s_step, _, _ = player()
    step = s_step if step is None else step
    tris = _tris(v, f)
    nz, area = _normals(tris)
    level = np.flatnonzero((nz > mg.TREAD_NZ) & (area >= 2.))
    if collision is not None and len(level):
        # a drawn level face the mesh's own authored collision holds nothing under is not stood on in the original
        # (OpenMW collides with the RootCollisionNode alone): never a tread (CHIM-STAIR-METHOD1-UNFIXED-48)
        drop = _uncovered(tris, level, _tris(*collision), step)
        level = np.array([i for i in level if int(i) not in drop], int)
    if len(level) < mg.FLIGHT_LEVELS:
        return []
    t = tris[level]
    treads = _tread_groups(t, level)
    z = np.array([t[g][:, :, 2].mean() for g in treads])
    lo = np.array([t[g].reshape(-1, 3).min(axis=0) for g in treads])
    hi = np.array([t[g].reshape(-1, 3).max(axis=0) for g in treads])
    parent = list(range(len(treads)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i in range(len(treads)):
        # candidates: a rise of RISE_MIN..step over tread i, boxes within TOUCH in plan
        rise = z - z[i]
        cand = np.flatnonzero((rise >= RISE_MIN) & (rise <= step + 1e-3)
                              & (lo[:, 0] <= hi[i, 0] + TOUCH) & (hi[:, 0] >= lo[i, 0] - TOUCH)
                              & (lo[:, 1] <= hi[i, 1] + TOUCH) & (hi[:, 1] >= lo[i, 1] - TOUCH))
        for j in cand:
            low, up = t[treads[i]], t[treads[j]]
            # one over the other (a shelf over a floor) is not a step
            if _inside_plan(up.mean(axis=(0, 1))[:2], low) or _inside_plan(low.mean(axis=(0, 1))[:2], up):
                continue
            if _meeting_length(up, low) >= mg.FLIGHT_WIDTH:
                parent[root(j)] = root(i)
    comps = {}
    for i in range(len(treads)):
        comps.setdefault(root(i), []).append(i)
    out = []
    for members in comps.values():
        if len(members) < mg.FLIGHT_LEVELS:
            continue
        hs = sorted(z[members])
        n, last = 1, hs[0]
        for h in hs[1:]:
            if h - last > RISE_MIN:
                n += 1
                last = h
        if n >= mg.FLIGHT_LEVELS:
            out.append(np.array(sorted(int(level[k]) for m in members for k in treads[m]), int))
    return sorted(_extend_walkways(tris, out, step), key=lambda g: int(g[0]))


def _extend_walkways(tris, found, step):
    """A walkway flight (every rise at most WALKWAY_RISE) with the walkable level boards it continues into (meeting
    within TOUCH at a rise of at most WALKWAY_RISE, along FLIGHT_WIDTH): a rope bridge's level middle joins its two
    sloping halves, so the whole bridge is one walkway. Stair flights are returned as they are."""
    walk = [g for g in found if is_walkway(tris, g, step)]
    if not walk:
        return found
    nz, area = _normals(tris)
    level = np.flatnonzero((nz > mg.TREAD_NZ) & (area >= 2.))
    t = tris[level]
    groups, zg, _, edges = _tread_graph(t, level, step, min_rise=0., touch=WALKWAY_TOUCH)
    parent = list(range(len(groups)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, j in edges:
        if abs(zg[j] - zg[i]) <= WALKWAY_RISE:
            parent[root(i)] = root(j)
    group_of = {int(level[x]): gi for gi, g in enumerate(groups) for x in g}
    stairs = [g for g in found if not any(g is w for w in walk)]
    taken = set(int(x) for g in stairs for x in g)
    merged = {}
    for g in walk:
        r = root(group_of[int(g[0])])
        merged.setdefault(r, set()).update(int(x) for x in g)
    out = list(stairs)
    for r, tri in merged.items():
        tri.update(int(level[x]) for gi, gg in enumerate(groups) if root(gi) == r for x in gg)
        out.append(np.array(sorted(tri - taken), int))
    return out


def _tris(v, f):
    return v[f[:, :3], :3] * .25


def _normals(tris):
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    a = np.linalg.norm(n, axis=1)
    nz = np.zeros(len(tris))
    ok = a > 1e-9
    nz[ok] = n[ok, 2] / a[ok]
    return nz, a / 2


def tread_samples(tris, ids, grid=SAMPLE_GRID, inset=mg.VISIBLE_TREAD_INSET):
    """Sample points over tread triangles ids: (points, triangle of each point)."""
    g = np.linspace(inset, 1 - 2 * inset, grid)
    bary = np.array([(a, b) for a in g for b in g if a + b <= 1 - inset + 1e-9])
    T = tris[ids]
    pts = T[:, None, 0] + bary[None, :, 0, None] * (T[:, None, 1] - T[:, None, 0]) \
        + bary[None, :, 1, None] * (T[:, None, 2] - T[:, None, 0])
    return pts.reshape(-1, 3), np.repeat(np.asarray(ids), len(bary))


def _open_column(tris, pts, height):
    """Top of the open column over each point: the lowest drawn surface over it (more than .3 up), capped at the
    standing box's height (mesh_geometry.visible_tread_samples' rule)."""
    top = pts[:, 2] + height
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    m00, m01 = b[:, 0] - a[:, 0], c[:, 0] - a[:, 0]
    m10, m11 = b[:, 1] - a[:, 1], c[:, 1] - a[:, 1]
    det = m00 * m11 - m01 * m10
    good = np.abs(det) > 1e-9
    lo, hi = tris.min(axis=1), tris.max(axis=1)
    for k, p in enumerate(pts):
        near = good & (lo[:, 0] <= p[0]) & (hi[:, 0] >= p[0]) & (lo[:, 1] <= p[1]) & (hi[:, 1] >= p[1]) \
            & (hi[:, 2] > p[2] + .3) & (lo[:, 2] < top[k])
        if not near.any():
            continue
        i = np.flatnonzero(near)
        d = det[i]
        u = ((p[0] - a[i, 0]) * m11[i] - (p[1] - a[i, 1]) * m01[i]) / d
        w = ((p[1] - a[i, 1]) * m00[i] - (p[0] - a[i, 0]) * m10[i]) / d
        ok = (u >= -1e-6) & (w >= -1e-6) & (u + w <= 1 + 1e-6)
        if not ok.any():
            continue
        hz = (a[i, 2] + u * (b[i, 2] - a[i, 2]) + w * (c[i, 2] - a[i, 2]))[ok]
        hz = hz[hz > p[2] + .3]
        if len(hz):
            top[k] = min(top[k], float(hz.min()))
    return top


def _equations(piece):
    points, hull = piece[0], piece[1]
    eq = hull.equations if hull is not None else ConvexHull(np.asarray(points, float)).equations
    return np.asarray(points, float), eq


def column_intervals(pieces, pts):
    """Per piece, the vertical interval it is solid in over each point's column: (low, high, normal z of the top
    face), arrays of shape (pieces, points); an empty interval has low > high. Pure plane arithmetic."""
    n = len(pts)
    lows = np.full((len(pieces), n), np.inf)
    highs = np.full((len(pieces), n), -np.inf)
    tops = np.zeros((len(pieces), n))
    for k, piece in enumerate(pieces):
        points, eq = _equations(piece)
        lo, hi = points.min(axis=0) - 1e-3, points.max(axis=0) + 1e-3
        sel = np.flatnonzero((pts[:, 0] >= lo[0]) & (pts[:, 0] <= hi[0]) & (pts[:, 1] >= lo[1]) & (pts[:, 1] <= hi[1]))
        if not len(sel):
            continue
        p = pts[sel]
        r = -(p[:, :2] @ eq[:, :2].T + eq[:, 3])            # c * z <= r for each plane
        c = eq[:, 2]
        with np.errstate(divide='ignore', invalid='ignore'):
            ups = np.where(c[None, :] > 1e-9, r / c[None, :], np.inf)
            down = np.where(c[None, :] < -1e-9, r / c[None, :], -np.inf).max(axis=1)
        j = np.argmin(ups, axis=1)
        up = ups[np.arange(len(p)), j]
        inside = np.where(np.abs(c)[None, :] <= 1e-9, r, np.inf).min(axis=1) >= -1e-6
        keep = inside & (up - down > .01)
        lows[k, sel[keep]] = down[keep]
        highs[k, sel[keep]] = up[keep]
        tops[k, sel[keep]] = c[j][keep]
    return lows, highs, tops


CHECK_FORMS = ('box', 'point')


def check_flight(pieces, tris, ids, step=None, walkable=None, height=None, samples=None, form='box'):
    """The geometric stair check of one flight (tread triangles ids of the drawn mesh, tris its triangles in
    converter units) against collision pieces [(points, hull, ids, error)]: a list of failures, each a dict with
    the check, the tread level (0 = lowest), the point and the measured value. Empty: walkable by the rules.

    form 'box' (default): the standing box's footprint over each tread sample (its corners, edge midpoints and
    centre, player_hull.MINS/MAXS): the box rests on the highest collision top in reach (a step down to a step up of
    the drawn tread) under any of them, as the engine's box rests on the highest support it overlaps. A sample where
    collision stands in the box's height over that rest (a wall, a rail, a roof next to the tread) is a place the box
    cannot be: not a fault there (the recorded walks never put the box there either, CHIM-STAIR-COLLISION-MESH-47),
    but a tread level with no place at all where the box fits fails ('no place on the tread for the standing box').
    A place where the box rests on a surface steeper than walkable is treated the same way (the box slides off);
    a tread level where it rests only on such surfaces fails ('standing surface too steep'). Failures also: no
    support in reach ('no floor under the drawn tread'), and between neighbouring places the box stands whose drawn
    treads are at most a step apart, a rise over a step. form 'point': _check_point. Calibrated against the recorded
    walks of the v0.0.46 release build (tools/stair_mesh_calibrate.py).
    samples: a dict to receive the tested points ('points', 'owner') and per point the checks it failed ('failed')."""
    if form not in CHECK_FORMS:
        raise ValueError('Unknown check form: %s' % form)
    if form == 'point':
        return _check_point(pieces, tris, ids, step, walkable, height, samples)
    from player_hull import MINS, MAXS
    s_step, s_walk, s_height = player()
    step = s_step if step is None else step
    walkable = s_walk if walkable is None else walkable
    height = s_height if height is None else height
    pts, owner = tread_samples(tris, ids)
    top = _open_column(tris, pts, height)
    room = top >= pts[:, 2] + height - 1e-6
    pts, owner = pts[room], owner[room]
    failed_at = [set() for _ in range(len(pts))]
    if samples is not None:
        samples.update(points=pts, owner=owner, failed=failed_at)
    if not len(pts):
        return []
    levels = np.unique(np.round(tris[ids][:, :, 2].mean(axis=1) * 4) / 4)
    level_of = {t: int(np.searchsorted(levels, round(float(tris[t][:, 2].mean()) * 4) / 4)) for t in ids}
    grown = expanded(pieces)
    off = grown                     # (the box-expanded pieces, handed on to the seam rule and the dense retry)
    n = len(pts)
    lows, highs, normals = box_columns(grown, pts)
    z = pts[:, 2][None, :, None]
    solid = lows < highs
    cand = solid & (highs >= z - step - 1e-3) & (highs <= z + step + STAND_SLACK)
    rest_all = np.where(cand, highs, -np.inf)
    stand = rest_all.max(axis=(0, 2))
    # the box rests on the highest support under its footprint below its head (a ramp rising across the footprint
    # carries it on the ramp's highest point there); the place is on the tread when that rest is within a step of it
    under = solid & (highs >= z - step - 1e-3) & (highs <= z + height - .05)
    rest_any = np.where(under, highs, -np.inf).max(axis=(0, 2))
    stand = np.where(np.isfinite(stand), np.maximum(stand, rest_any), stand)
    # the box rests on every support whose top is at its rest height; it stands when one of them is walkable
    at_rest = solid & (highs >= stand[None, :, None] - .25) & (highs <= stand[None, :, None] + 1e-6)
    snz = np.where(at_rest, normals, -np.inf).max(axis=(0, 2))
    on_tread = stand <= pts[:, 2] + step + STAND_SLACK + _slope_lift(snz)
    base = np.where(np.isfinite(stand), stand, pts[:, 2])[None, :, None]
    blocked = (solid & (lows < base + height - .05) & (highs > base + .05)).any(axis=(0, 2))
    fits = np.isfinite(stand) & ~blocked & on_tread
    failures = []

    def fail(check, i, value):
        failed_at[i].add(check)
        failures.append({'check': check, 'level': level_of[int(owner[i])], 'triangle': int(owner[i]),
                         'point': [round(float(x), 3) for x in pts[i]], 'value': round(float(value), 3)})
    zs = pts[:, 2]
    # a place where the box rests on a surface too steep to stand on slides off it (as on a rail's top next to the
    # tread): like a place it does not fit, not a fault there; a tread with no place to stand at all is
    steep = fits & (snz < walkable - 1e-3)
    fits = fits & ~steep
    for i in range(n):
        if np.isfinite(stand[i]):
            continue
        hi = highs[:, i, :][solid[:, i, :] & (highs[:, i, :] > zs[i] + step + STAND_SLACK) & (lows[:, i, :] < zs[i] + height)]
        if len(hi):
            continue        # higher solid in the footprint and nothing in reach: the box cannot be here (see fits)
        lo = highs[:, i, :][solid[:, i, :] & (highs[:, i, :] < zs[i] - step)]
        fail('no floor under the drawn tread', i, (zs[i] - float(lo.max())) if len(lo) else -1.)
    # every tread level needs a place where the box fits
    lev = np.array([level_of[int(t)] for t in owner])
    for L in sorted(set(lev.tolist())):
        at = np.flatnonzero(lev == L)
        if not fits[at].any() and not all('no floor under the drawn tread' in failed_at[i] for i in at):
            # the box may fit only on a narrow line of the tread (a stair 16 units wide for a box 14.6 wide): the
            # tread again on a grid FINE_GRID times as dense before it fails
            tri_l = sorted({int(owner[q]) for q in at})
            fine, _ = tread_samples(tris, tri_l, grid=SAMPLE_GRID * FINE_GRID)
            fine = fine[_open_column(tris, fine, height) >= fine[:, 2] + height - 1e-6]
            if len(fine) and _box_places(grown, fine, step, walkable, height)[1].any():
                continue
            i = int(at[0])
            if steep[at].any():
                j = int(at[np.argmax(snz[at] * steep[at] - (~steep[at]))])
                fail('standing surface too steep (normal z)', j, snz[j])
            else:
                hi = highs[:, at, :][solid[:, at, :] & (highs[:, at, :] > zs[at][None, :, None] + step + STAND_SLACK)]
                fail('no place on the tread for the standing box', i, float(hi.min() - zs[i]) if len(hi) else -1.)
    good = np.flatnonzero(fits)
    if len(good) > 1:
        tree = cKDTree(pts[good, :2])
        for a, b in tree.query_pairs(NEIGHBOUR):
            ia, ib = good[a], good[b]
            if abs(zs[ia] - zs[ib]) > step + STAND_SLACK:
                continue
            rise = abs(stand[ia] - stand[ib])
            if rise > step + 1e-3:
                fail('rise between neighbouring standing points over a step', ia if stand[ia] < stand[ib] else ib, rise)
    # seams: from every tread to the next one up (treads meeting a step apart, _tread_graph) the box has a way within
    # the step rule. Between the closest places it stands on the two treads (SEAM_PAIRS pairs), the standing height
    # is followed along the straight line in SEAM_STEP steps by plane arithmetic (_seam_profile): each step rests on
    # the highest support under the footprint that is at most a step up from the last, with the box's height free.
    # A seam no pair passes fails: a lip over a step, or a gap the box drops into
    groups, zg, _, edges = _tread_graph(tris[ids], np.asarray(ids), step)
    group_of = {int(ids[x]): gi for gi, g in enumerate(groups) for x in g}
    g_of = np.array([group_of.get(int(o), -1) for o in owner])
    for i, j in sorted(edges):
        A = np.flatnonzero((g_of == i) & fits)
        B = np.flatnonzero((g_of == j) & fits)
        if not len(A) or not len(B):
            continue        # a tread with no place to stand already fails ('no place on the tread ...')
        # the places near the seam: within the box's half width and a touch of the other tread (a landing's far
        # side does not lead to the step; a straight line from there may cross the flight beside it)
        tt = tris[ids]
        # treads that meet only in plan, one under the other's flight (a slab running on under the steps): no drawn
        # standing room near where they meet on one side, so no way to be checked there
        if not (_room_near(tris, ids, groups[i], tt[groups[j]], height)
                and _room_near(tris, ids, groups[j], tt[groups[i]], height)):
            continue
        PA, SA = pts[A], stand[A]
        PB, SB = pts[B], stand[B]

        def nearest(P, S, other, gi):
            # the places of a tread nearest the other tread (sampled FINE_GRID times as densely when none of the
            # coarse places lies within the box's half width and a touch of it: big treads, sparse samples)
            d = _tread_distance(P[:, :2], tt[groups[other]])
            if not len(d) or d.min() > MAXS[0] + TOUCH:
                tri_g = [int(ids[x]) for x in groups[gi]]
                fine, _ = tread_samples(tris, tri_g, grid=SAMPLE_GRID * FINE_GRID)
                fine = fine[_open_column(tris, fine, height) >= fine[:, 2] + height - 1e-6]
                if len(fine):
                    st, ok = _box_places(grown, fine, step, walkable, height)
                    if ok.any():
                        P, S = np.vstack((P, fine[ok])), np.concatenate((S, st[ok]))
                        d = _tread_distance(P[:, :2], tt[groups[other]])
            keep = np.argsort(d)[:SEAM_NEAREST]
            return P[keep], S[keep]
        PA, SA = nearest(PA, SA, j, i)
        PB, SB = nearest(PB, SB, i, j)
        d = np.linalg.norm(PA[:, None, :2] - PB[None, :, :2], axis=2)
        order = np.argsort(d, axis=None)[:SEAM_PAIRS]
        why = None
        for k in order:
            a, b = int(k // len(PB)), int(k % len(PB))
            why = _seam_profile(grown, PA[a], SA[a], PB[b], step, height)
            if why is None:
                break
        if why is not None:
            # named at the nearest sampled place of the lower tread
            k = int(order[0])
            pa = PA[k // len(PB)]
            at = A[int(np.argmin(np.linalg.norm(pts[A, :2] - pa[:2], axis=1)))]
            fail('no passage to the next tread within the step rule (%s)' % why[0], int(at), why[1])
    return failures


SEAM_PAIRS = 12            # the closest pairs of places on two treads tried as a way from one to the other
SEAM_NEAREST = 8           # ... among each tread's places nearest the other tread
SEAM_STEP = 1.             # the seam profile's spacing along the way (units)


FINE_GRID = 3              # a tread with no place for the box is sampled this many times as densely before it fails


def _box_places(grown, pts, step, walkable, height):
    """(stand, fits) of the standing box over points PTS (check_flight's box rule, GROWN: expanded pieces): the rest on
    the highest support under the footprint below its head, the place counting when that rest is within a step of the
    point's tread, its height free over it and the surface walkable."""
    n = len(pts)
    if not grown or not n:
        return np.full(n, -np.inf), np.zeros(n, bool)
    lows, highs, normals = box_columns(grown, pts)
    z = pts[:, 2][None, :, None]
    solid = lows < highs
    cand = solid & (highs >= z - step - 1e-3) & (highs <= z + step + STAND_SLACK)
    stand = np.where(cand, highs, -np.inf).max(axis=(0, 2))
    under = solid & (highs >= z - step - 1e-3) & (highs <= z + height - .05)
    stand = np.where(np.isfinite(stand), np.maximum(stand, np.where(under, highs, -np.inf).max(axis=(0, 2))), stand)
    at_rest = solid & (highs >= stand[None, :, None] - .25) & (highs <= stand[None, :, None] + 1e-6)
    snz = np.where(at_rest, normals, -np.inf).max(axis=(0, 2))
    base = np.where(np.isfinite(stand), stand, pts[:, 2])[None, :, None]
    blocked = (solid & (lows < base + height - .05) & (highs > base + .05)).any(axis=(0, 2))
    fits = (np.isfinite(stand) & ~blocked & (stand <= pts[:, 2] + step + STAND_SLACK + _slope_lift(snz))
            & (snz >= walkable - 1e-3))
    return stand, fits


def _slope_lift(nz):
    """How much higher than under its centre the standing box rests on a slope of normal z NZ: half its footprint
    times the slope (a box over a ramp rests on the ramp's highest point under it, as Quake's box does)."""
    from player_hull import MAXS
    nz = np.clip(np.asarray(nz, float), 1e-3, 1.)
    return np.where(nz >= mg.TREAD_NZ, 0., MAXS[0] * np.sqrt(1. - nz * nz) / nz)


def _room_near(tris, ids, group, other, height):
    """True when the tread (GROUP: positions in ids) has a point with the standing box's height free in the drawn
    mesh within the box's half width and TOUCH of the triangles OTHER (sampled FINE_GRID times as densely)."""
    from player_hull import MAXS
    tri_g = [int(ids[x]) for x in group]
    fine, _ = tread_samples(tris, tri_g, grid=SAMPLE_GRID * FINE_GRID)
    fine = fine[_open_column(tris, fine, height) >= fine[:, 2] + height - 1e-6]
    return bool(len(fine)) and bool((_tread_distance(fine[:, :2], other) <= MAXS[0] + TOUCH).any())


def _tread_distance(pts2, t):
    """Plan distance from points PTS2 to triangles T (0 inside one)."""
    if not len(pts2):
        return np.zeros(0)
    e0 = t[:, :, :2].reshape(-1, 2)
    e1 = np.roll(t[:, :, :2], -1, axis=1).reshape(-1, 2)
    d = _plan_distances(pts2, e0, e1).min(axis=1)
    inside = np.array([_inside_plan(p, t) for p in pts2])
    return np.where(inside, 0., d)


def _near_tread(pts2, t, reach=None):
    """Which plan points PTS2 lie within REACH (default: the standing box's half width and TOUCH) of triangles T."""
    from player_hull import MAXS
    reach = MAXS[0] + TOUCH if reach is None else reach
    e0 = t[:, :, :2].reshape(-1, 2)
    e1 = np.roll(t[:, :, :2], -1, axis=1).reshape(-1, 2)
    d = _plan_distances(pts2, e0, e1).min(axis=1)
    return d <= reach


def expanded(pieces):
    """The pieces grown by the standing box (the Minkowski sum with it, edge bevels included, as the engine's standing
    hull is): a point (the box's centre) is inside one exactly when the box there overlaps the piece."""
    from itertools import product
    from player_hull import MINS, MAXS
    corners = np.array(list(product(*zip(MINS, MAXS))))
    out = []
    for piece in pieces:
        points, _ = _equations(piece)
        grown = (points[:, None, :] - corners[None, :, :]).reshape(-1, 3)
        try:
            out.append((grown, ConvexHull(grown), piece[2], 0.))
        except Exception:
            continue
    return out


def box_columns(grown, pts):
    """For the standing box with its feet over points PTS, per expanded piece (expanded): the lowest bottom and the
    highest top of the piece under the box's footprint, and the normal z of the surface the box rests on at that top
    (an edge gives its bevel, as the engine reads it): arrays (pieces, points, 1); no overlap: +inf / -inf. Exact for
    convex pieces: no sampling of the footprint."""
    from player_hull import MINS, MAXS
    n = len(pts)
    if not grown:
        return np.full((1, n, 1), np.inf), np.full((1, n, 1), -np.inf), np.zeros((1, n, 1))
    lows, highs, normals = column_intervals(grown, pts)
    solid = lows < highs
    lows = np.where(solid, lows + MAXS[2], np.inf)
    highs = np.where(solid, highs + MINS[2], -np.inf)
    return lows[:, :, None], highs[:, :, None], normals[:, :, None]


def _seam_profile(grown, a, rest, b, step, height):
    """The standing box going in a straight line from place a (resting at REST) to place b: None when every point
    on the way rests on a support at most a step above the last rest (anything lower is a drop, allowed) with the
    box's height free over it; else (reason, value): 'lip' (the highest support under the footprint is over a step
    up), 'blocked' (solid in the box's height) or 'gap' (no support under the footprint at all)."""
    n = max(2, int(np.ceil(np.linalg.norm(b[:2] - a[:2]) / SEAM_STEP)) + 1)
    line = a[None, :] + (b - a)[None, :] * np.linspace(0, 1, n)[:, None]
    lows, highs, _ = box_columns(grown, line)
    solid = lows < highs
    last = float(rest)
    for q in range(n):
        lq, hq, sq = lows[:, q, :], highs[:, q, :], solid[:, q, :]
        under = sq & (lq < last + height - .05)            # supports under the box's head at the last rest
        if not under.any():
            return 'gap', float(np.linalg.norm(line[q, :2] - a[:2]))
        reach = under & (hq <= last + step + STAND_SLACK)
        if not reach.any():
            return 'lip', float(hq[under].min() - last)
        top = float(hq[reach].max())
        blk = sq & (lq < top + height - .05) & (hq > top + .05)
        if blk.any():
            # an obstacle rising from the box's feet (over a step: it could not be stepped onto) is a lip, one
            # higher up (a low roof, a beam) blocks
            if (lq[blk] <= top + step).any():
                return 'lip', float(hq[blk].max() - top)
            return 'blocked', float(np.linalg.norm(line[q, :2] - a[:2]))
        last = top
    return None


def _check_point(pieces, tris, ids, step=None, walkable=None, height=None, samples=None):
    """The first form of the check (form 'point', kept for A/B): the vertical line over each sample only. The geometric stair check of one flight (tread triangles ids of the drawn mesh, tris its triangles in
    converter units) against collision pieces [(points, hull, ids, error)]: a list of failures, each a dict with
    the check, the tread level (0 = lowest), the point and the measured value. Empty: walkable by the rules.
    samples: a dict to receive the tested points ('points', 'owner') and per point the checks it failed ('failed')."""
    s_step, s_walk, s_height = player()
    step = s_step if step is None else step
    walkable = s_walk if walkable is None else walkable
    height = s_height if height is None else height
    pts, owner = tread_samples(tris, ids)
    top = _open_column(tris, pts, height)
    room = top >= pts[:, 2] + height - 1e-6        # standing room over the drawn tread (else its authors' collision)
    pts, owner = pts[room], owner[room]
    failed_at = [set() for _ in range(len(pts))]
    if samples is not None:
        samples.update(points=pts, owner=owner, failed=failed_at)
    if not len(pts):
        return []
    levels = np.unique(np.round(tris[ids][:, :, 2].mean(axis=1) * 4) / 4)
    level_of = {t: int(np.searchsorted(levels, round(float(tris[t][:, 2].mean()) * 4) / 4)) for t in ids}
    lows, highs, normals = column_intervals(pieces, pts)
    if not len(pieces):        # no collision at all: one empty piece keeps the arrays' shape
        lows, highs, normals = np.full((1, len(pts)), np.inf), np.full((1, len(pts)), -np.inf), np.zeros((1, len(pts)))
    z = pts[:, 2]
    # what the box stands on: the highest solid top within [tread - step, tread + step]
    cand = (highs >= z[None, :] - step - 1e-3) & (highs <= z[None, :] + step + STAND_SLACK) & (lows < highs)
    stand = np.where(cand, highs, -np.inf).max(axis=0)
    which = np.where(cand, highs, -np.inf).argmax(axis=0)
    snz = normals[which, np.arange(len(pts))]
    failures = []

    def fail(check, i, value):
        failed_at[i].add(check)
        failures.append({'check': check, 'level': level_of[int(owner[i])], 'triangle': int(owner[i]),
                         'point': [round(float(x), 3) for x in pts[i]], 'value': round(float(value), 3)})
    # solid over the drawn tread higher than a step (a block, a ramp too high) or in the standing box over the floor
    base = np.where(np.isfinite(stand), stand, z)
    over = (lows < (base + height - .05)[None, :]) & (highs > (base + .05)[None, :]) & (lows < highs)
    for i in range(len(pts)):
        if not np.isfinite(stand[i]):
            higher = highs[:, i][(highs[:, i] > z[i] + step + STAND_SLACK) & (lows[:, i] < z[i] + height)]
            if len(higher):
                fail('over a step above the drawn tread', i, float(higher.min()) - z[i])
            else:
                lower = highs[:, i][(highs[:, i] < z[i] - step) & (lows[:, i] < highs[:, i])]
                fail('no floor under the drawn tread', i, (z[i] - float(lower.max())) if len(lower) else -1.)
            continue
        if snz[i] < walkable - 1e-3:
            fail('standing surface too steep (normal z)', i, snz[i])
        if over[:, i].any():
            fail('solid in the standing box over the floor', i, float(lows[over[:, i], i].min()) - stand[i])
    # neighbouring samples (across a riser, along a ramp) differ by a step at most
    good = np.flatnonzero(np.isfinite(stand))
    if len(good) > 1:
        tree = cKDTree(pts[good, :2])
        for a, b in tree.query_pairs(NEIGHBOUR):
            ia, ib = good[a], good[b]
            if abs(z[ia] - z[ib]) > step + STAND_SLACK:
                continue        # the drawn treads themselves are more than a step apart: a ledge, not a step
            rise = abs(stand[ia] - stand[ib])
            if rise > step + 1e-3:
                fail('rise between neighbouring standing points over a step', ia if stand[ia] < stand[ib] else ib, rise)
    return failures


def check_flights(pieces, vis_v, vis_f, step=None, groups=None):
    """check_flight for every flight of the drawn mesh: [(flight number, failures)]."""
    tris = _tris(vis_v, vis_f)
    groups = flights(vis_v, vis_f, step) if groups is None else groups
    return [(k, check_flight(pieces, tris, ids, step)) for k, ids in enumerate(groups)]


def _hull_piece(points, ids=()):
    points = np.unique(np.round(np.asarray(points, float) * 16) / 16, axis=0)
    if len(points) < 4 or np.linalg.matrix_rank(points - points[0]) < 3:
        return None
    return (points, ConvexHull(points), list(ids), 0.)


def flight_ramp(tris, ids, others, step=None, walkable=None):
    """ONE RAMP for a flight: the hull of its tread corners and the same corners UNDER under the lowest tread.
    (piece, None) or (None, reason) when the ramp stands more than a step over a tread, is too steep, or holds
    another drawn point (others: points of the drawn mesh off this flight) deeper than CUT_THROUGH."""
    s_step, s_walk, _ = player()
    step = s_step if step is None else step
    walkable = s_walk if walkable is None else walkable
    pts = tris[ids].reshape(-1, 3)
    z0 = float(pts[:, 2].min()) - UNDER
    piece = _hull_piece(np.vstack((pts, np.column_stack((pts[:, :2], np.full(len(pts), z0))))), ids)
    if piece is None:
        return None, 'degenerate flight'
    samples, _ = tread_samples(tris, ids)
    lows, highs, normals = column_intervals([piece], samples)
    over = highs[0] - samples[:, 2]
    if not np.isfinite(over).all():
        return None, 'ramp misses a tread'
    if over.max() > step + STAND_SLACK:
        return None, 'ramp %.2f over a tread (step %.2f)' % (over.max(), step)
    if normals[0].min() < walkable - RAMP_EPS:
        return None, 'ramp too steep (normal z %.3f)' % normals[0].min()
    if len(others):
        eq = piece[1].equations
        lo, hi = piece[0].min(axis=0), piece[0].max(axis=0)
        near = others[np.all((others >= lo) & (others <= hi), axis=1)]
        if len(near):
            depth = -(near @ eq[:, :3].T + eq[:, 3]).max(axis=1)
            if depth.max() > CUT_THROUGH:
                return None, 'ramp cuts through drawn geometry (%.2f deep)' % depth.max()
    return piece, None


WALKWAY_RISE = 2.5         # a flight whose every rise is at most this is a walkway (planks, a rope bridge, a dock)
WALKWAY_THICK = 1.         # a walkway plate's thickness under its top
WALKWAY_TOUCH = 6.         # boards of a walkway this far apart in plan are one way (the gaps of a rope bridge; the box is 14.6 wide)


def flight_plate(tris, ids, others, step=None, walkable=None, thick=WALKWAY_THICK):
    """ONE SLOPED PLATE for treads of a walkway: the hull of their corners and the same corners THICK lower (a slab
    following the boards), checked as flight_ramp checks a ramp. (piece, None) or (None, reason)."""
    s_step, s_walk, _ = player()
    step = s_step if step is None else step
    walkable = s_walk if walkable is None else walkable
    pts = tris[ids].reshape(-1, 3)
    piece = _hull_piece(np.vstack((pts, pts - [0., 0., thick])), ids)
    if piece is None:
        return None, 'degenerate walkway'
    samples, _ = tread_samples(tris, ids)
    lows, highs, normals = column_intervals([piece], samples)
    over = highs[0] - samples[:, 2]
    if not np.isfinite(over).all():
        return None, 'plate misses a board'
    if over.max() > step + STAND_SLACK:
        return None, 'plate %.2f over a board' % over.max()
    if normals[0].min() < walkable - RAMP_EPS:
        return None, 'plate too steep (normal z %.3f)' % normals[0].min()
    if len(others):
        eq = piece[1].equations
        lo, hi = piece[0].min(axis=0), piece[0].max(axis=0)
        near = others[np.all((others >= lo) & (others <= hi), axis=1)]
        if len(near):
            depth = -(near @ eq[:, :3].T + eq[:, 3]).max(axis=1)
            if depth.max() > CUT_THROUGH:
                return None, 'plate cuts through drawn geometry (%.2f deep)' % depth.max()
    return piece, None


def is_walkway(tris, ids, step=None):
    """A flight whose treads all meet at rises of at most WALKWAY_RISE: boards, a rope bridge, a dock, not a stair."""
    s_step, _, _ = player()
    step = s_step if step is None else step
    _, zg, _, edges = _tread_graph(tris[ids], np.asarray(ids), step)
    return bool(edges) and max(zg[j] - zg[i] for i, j in edges) <= WALKWAY_RISE


def _as_mesh(t):
    """Triangles t (converter units) as a source mesh (v, f) for the mesh_geometry functions (source units)."""
    v = np.hstack((t.reshape(-1, 3) * 4., np.zeros((len(t) * 3, 2))))
    f = np.column_stack((np.arange(len(t) * 3).reshape(-1, 3), np.zeros(len(t), int)))
    return v, f


def _board_plates(tris, ids):
    """Thin plates of treads (their surface polygons, mesh_geometry.shell_collision_parts): a walkway's boards where
    no sloped plate holds."""
    return mg.shell_collision_parts(*_as_mesh(tris[ids]))


def _chain_order(members, edges):
    """Treads of a run in walking order: along the tread graph from an end (a sagging bridge goes down and up again,
    so not by height); what the walk does not reach is appended in turn."""
    inside = set(members)
    nb = {m: [] for m in members}
    for i, j in edges:
        if i in inside and j in inside:
            nb[i].append(j)
            nb[j].append(i)
    order, seen = [], set()
    for start in sorted(members, key=lambda m: (len(nb[m]), m)):
        if start in seen:
            continue
        cur = start
        while cur is not None and cur not in seen:
            seen.add(cur)
            order.append(cur)
            cur = next((n for n in nb[cur] if n not in seen), None)
    return order


RAMP_UNITS = ('run', 'flight')   # one ramp per run of steps between landings (default), or one per flight (the first)
LANDING_AREA = 2.5               # a tread with this many times the flight's median tread area is a landing


def _tread_graph(t, ids, step, min_rise=RISE_MIN, touch=TOUCH):
    """The treads of a flight (_tread_groups), their levels and areas, and which meet a step apart (plan within
    TOUCH, a rise of RISE_MIN..step, along at least FLIGHT_WIDTH of edge). min_rise 0 (walkways): boards at one
    level meet too (each such pair once, lower index first)."""
    groups = _tread_groups(t, ids)
    zg = np.array([t[g][:, :, 2].mean() for g in groups])
    _, area = _normals(t)
    ag = np.array([area[g].sum() for g in groups])
    lo = np.array([t[g].reshape(-1, 3).min(axis=0) for g in groups])
    hi = np.array([t[g].reshape(-1, 3).max(axis=0) for g in groups])
    edges = set()
    for i in range(len(groups)):
        for j in range(len(groups)):
            r = zg[j] - zg[i]
            if i == j or not (min_rise <= r <= step + STAND_SLACK) or (r < RISE_MIN and j < i):
                continue
            if (lo[j, 0] > hi[i, 0] + touch or hi[j, 0] < lo[i, 0] - touch
                    or lo[j, 1] > hi[i, 1] + touch or hi[j, 1] < lo[i, 1] - touch):
                continue
            # one over the other (a step standing on a slab that runs on under the flight) is not a step: the
            # flight detector's own rule (level_flights)
            if (_inside_plan(t[groups[j]].mean(axis=(0, 1))[:2], t[groups[i]])
                    or _inside_plan(t[groups[i]].mean(axis=(0, 1))[:2], t[groups[j]])):
                continue
            if _meeting_length(t[groups[j]], t[groups[i]], touch) >= mg.FLIGHT_WIDTH:
                edges.add((i, j))
    return groups, zg, ag, edges


def run_ramps(tris, ids, others, step=None):
    """ONE RAMP PER RUN: a flight split at its landings (treads LANDING_AREA times the median tread or meeting more
    than two others), each run of steps between them climbed from its lowest tread up as far as one ramp holds
    (flight_ramp: at most a step over every tread, walkable, through no other drawn geometry), a new ramp started
    where it no longer does; a tread no ramp of two or more treads holds, and every landing, is one block per tread
    (tread_blocks). Returns (pieces, ramps, tread blocks)."""
    s_step, _, _ = player()
    step = s_step if step is None else step
    t = tris[ids]
    groups, zg, ag, edges = _tread_graph(t, ids, step)
    walkway = bool(edges) and max(zg[j] - zg[i] for i, j in edges) <= WALKWAY_RISE
    if walkway:
        # boards at one level are part of the way: the graph with level pairs, landings only at forks
        groups, zg, ag, edges = _tread_graph(t, ids, step, min_rise=0., touch=WALKWAY_TOUCH)
    degree = np.zeros(len(groups), int)
    for i, j in edges:
        degree[i] += 1
        degree[j] += 1
    med = float(np.median(ag)) if len(ag) else 0.
    landing = ((ag > LANDING_AREA * med) | (degree > 2)) & (not walkway)
    parent = list(range(len(groups)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, j in edges:
        if not landing[i] and not landing[j]:
            parent[root(i)] = root(j)
    runs = {}
    for i in range(len(groups)):
        if not landing[i]:
            runs.setdefault(root(i), []).append(i)
    out, ramps, blocks = [], 0, 0
    # a walkway's plates may pass through its ropes and posts (thin, under the boards' line): no cut-through test
    make = (lambda tr, ii, oth, st: flight_plate(tr, ii, np.zeros((0, 3)), st)) if walkway else flight_ramp
    block_treads = [i for i in range(len(groups)) if landing[i]]
    for members in runs.values():
        members = _chain_order(members, edges)
        start = 0
        while start < len(members):
            best, end = None, start + 1
            for stop in range(start + 2, len(members) + 1):
                tri = [ids[x] for g in members[start:stop] for x in groups[g]]
                piece, _ = make(tris, np.array(tri, int), others, step)
                if piece is None:
                    break
                best, end = piece, stop
            if best is not None:
                out.append(best)
                ramps += 1
            else:
                block_treads.append(members[start])
            start = end
    if block_treads:
        tri = np.array([ids[x] for g in block_treads for x in groups[g]], int)
        made = _board_plates(tris, tri) if walkway else tread_blocks(tris, tri, step)
        out.extend(made)
        blocks += len(made)
    if ramps and check_flight(out, tris, ids, step):
        # a seam between a ramp (or plate) and the block or landing next to it fails the step rule: the flight as
        # blocks (or boards), which meet tread to tread as drawn
        alt = _board_plates(tris, np.asarray(ids)) if walkway else tread_blocks(tris, np.asarray(ids), step)
        if not check_flight(alt, tris, ids, step):
            return alt, 0, len(alt)
    return out, ramps, blocks


def tread_blocks(tris, ids, step=None):
    """ONE SOLID BLOCK PER TREAD of a flight: the tread's corners down to UNDER under the next lower tread it meets
    (within TOUCH in plan, a rise of up to a step), or UNDER under itself when none is lower: solid steps the step
    rule climbs, never solid under a landing or a balcony deeper than a step. A tread is its level triangles joined
    at shared corners; a tread whose hull covers more than CONVEX_SLACK of its own area (an L-shaped landing) is one
    block per triangle."""
    s_step, _, _ = player()
    step = s_step if step is None else step
    t = tris[ids]
    groups = _tread_groups(t, ids)
    zg = np.array([t[g][:, :, 2].mean() for g in groups])
    lo = np.array([t[g].reshape(-1, 3).min(axis=0) for g in groups])
    hi = np.array([t[g].reshape(-1, 3).max(axis=0) for g in groups])
    _, area = _normals(t)
    out = []
    for gi, members in enumerate(groups):
        drop = zg[gi] - zg
        below = np.flatnonzero((drop > .25) & (drop <= step + STAND_SLACK)
                               & (lo[:, 0] <= hi[gi, 0] + TOUCH) & (hi[:, 0] >= lo[gi, 0] - TOUCH)
                               & (lo[:, 1] <= hi[gi, 1] + TOUCH) & (hi[:, 1] >= lo[gi, 1] - TOUCH))
        z0 = float((zg[below].min() if len(below) else zg[gi]) - UNDER)
        sets = [members]
        p = t[members].reshape(-1, 3)
        try:
            plan = ConvexHull(p[:, :2]).volume
        except Exception:
            plan = 0.
        if plan > CONVEX_SLACK * float(area[members].sum()):
            # not convex in plan (an L-shaped landing, boards touching at corners): one block per convex surface
            # polygon of the tread (mesh_geometry.surface_polygons merges its coplanar triangles), not per triangle
            for q, *_ in mg.surface_polygons(*_as_mesh(t[members]), geometry_only=True):
                q = np.asarray(q, float)
                piece = _hull_piece(np.vstack((q, np.column_stack((q[:, :2], np.full(len(q), z0))))),
                                    [ids[m] for m in members])
                if piece is not None:
                    out.append(piece)
            continue
        for s in sets:
            q = t[s].reshape(-1, 3)
            piece = _hull_piece(np.vstack((q, np.column_stack((q[:, :2], np.full(len(q), z0))))),
                                [ids[m] for m in s])
            if piece is not None:
                out.append(piece)
    return out


def _flight_region(tris, ids, coll, step, height):
    """Collision triangles (coll: their converter-unit triangles) that belong to a flight being replaced: over its
    treads in plan (within mesh_geometry's touch of .75) and either a tread (level, at most a step over the tread
    under it), a riser (steep, at most a step tall, within the flight's height range) or an upward face lower than
    the standing box over the tread (a ramp over the steps). Downward faces (the flight's underside) stay."""
    t = tris[ids]
    zt = t[:, :, 2].mean(axis=1)
    zlo, zhi = float(zt.min()), float(zt.max())
    cen = coll.mean(axis=1)
    nz, _ = _normals(coll)
    e0 = t[:, :, :2]
    e1 = np.roll(e0, -1, axis=1)
    lo, hi = t.reshape(-1, 3).min(axis=0) - 1., t.reshape(-1, 3).max(axis=0) + 1.
    cand = np.flatnonzero((cen[:, 0] >= lo[0]) & (cen[:, 0] <= hi[0]) & (cen[:, 1] >= lo[1]) & (cen[:, 1] <= hi[1])
                          & (cen[:, 2] >= zlo - step - 1.) & (cen[:, 2] <= zhi + height))
    out = []
    a, b, c = t[:, 0, :2], t[:, 1, :2], t[:, 2, :2]
    for i in cand:
        p = cen[i, :2]
        # the tread under the centroid (inside it in plan), else the nearest tread edge within .75
        v0, v1, v2 = b - a, c - a, p - a
        d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1)
        d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
        den = d00 * d11 - d01 * d01
        with np.errstate(divide='ignore', invalid='ignore'):
            u = (d11 * d20 - d01 * d21) / den
            w = (d00 * d21 - d01 * d20) / den
        inside = (np.abs(den) > 1e-12) & (u >= -1e-6) & (w >= -1e-6) & (u + w <= 1 + 1e-6)
        if inside.any():
            under = zt[inside]
        else:
            d = mg._segment_distance(p, p, e0.reshape(-1, 2), e1.reshape(-1, 2)).reshape(-1, 3).min(axis=1)
            if d.min() > .75:
                continue
            under = zt[d <= .75]
        zc = cen[i, 2]
        tall = float(np.ptp(coll[i][:, 2]))
        if nz[i] > mg.TREAD_NZ:
            hit = ((zc >= under - FLOOR_TOLERANCE) & (zc <= under + step + 1e-3)).any()
        elif nz[i] < mg.TREAD_NZ and nz[i] >= mg.RISER_NZ:
            hit = ((zc >= under - step - 1e-3) & (zc <= under + height)).any()
        elif abs(nz[i]) < mg.RISER_NZ:
            hit = tall <= step + .5 and zlo - step - 1. <= coll[i][:, 2].min() and coll[i][:, 2].max() <= zhi + .5
        else:
            hit = False
        if hit:
            out.append(int(i))
    return out


def _over_treads(tri, treads, touch=.75):
    """True when collision triangle TRI faces upward (not a wall, not an underside) and lies over the tread triangles
    TREADS in plan: its centre inside one of them, or every corner within TOUCH of them."""
    nz, _ = _normals(tri[None])
    if nz[0] < mg.RISER_NZ:
        return False
    if _inside_plan(tri.mean(axis=0)[:2], treads):
        return True
    e0 = treads[:, :, :2].reshape(-1, 2)
    e1 = np.roll(treads[:, :, :2], -1, axis=1).reshape(-1, 2)
    d = _plan_distances(tri[:, :2], e0, e1).min(axis=1)
    inside = [_inside_plan(c[:2], treads) for c in tri]
    return all(x or y <= touch for x, y in zip(inside, d))


def _standing_region(tris, ids, height):
    """The standing space over a flight: (footprint, bottom, top) - the convex hull in plan of the tread samples that
    have the standing box's height free in the drawn mesh (counter-clockwise), from half a unit under the lowest tread
    to the standing box's height over the highest."""
    pts, _ = tread_samples(tris, ids)
    pts = pts[_open_column(tris, pts, height) >= pts[:, 2] + height - 1e-6]
    if len(pts) < 3:
        return None
    try:
        hull = ConvexHull(pts[:, :2])
    except Exception:
        return None
    ring = pts[hull.vertices, :2]
    zt = tris[ids][:, :, 2]
    return ring, float(zt.min()) - FLOOR_TOLERANCE, float(zt.max()) + height


def _clip_points(points, eq, n, d):
    """Vertices of the convex piece (points, hull equations eq) cut to the half-space n . x >= d."""
    from scipy.spatial import ConvexHull as Hull
    side = points @ n - d
    keep = list(points[side >= -1e-9])
    hull = Hull(points)
    for tri in hull.simplices:
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            sa, sb = side[a], side[b]
            if (sa < -1e-9 < sb) or (sb < -1e-9 < sa):
                t = sa / (sa - sb)
                keep.append(points[a] + t * (points[b] - points[a]))
    return np.array(keep) if keep else np.zeros((0, 3))


def _clip_out(piece, region, others):
    """A convex collision piece without the part inside REGION (_standing_region): the convex parts of it outside
    each footprint edge, above the top and below the bottom (they may overlap: collision is their union). The piece
    unchanged when the region is None or other drawn geometry (OTHERS: points of the drawn mesh off the flights) lies
    in the part that would go."""
    if region is None:
        return [piece]
    ring, bottom, top = region
    points, eq = _equations(piece)
    inside = np.ones(len(others), bool) if len(others) else np.zeros(0, bool)
    if len(others):
        inside &= (others[:, 2] > bottom) & (others[:, 2] < top)
        inside &= (others @ eq[:, :3].T + eq[:, 3]).max(axis=1) < -1e-6
        for a, b in zip(ring, np.roll(ring, -1, axis=0)):
            e = b - a
            inside &= (e[0] * (others[:, 1] - a[1]) - e[1] * (others[:, 0] - a[0])) > 0
        if inside.any():
            return [piece]
    cuts = [(np.array([0., 0., 1.]), top), (np.array([0., 0., -1.]), -bottom)]
    for a, b in zip(ring, np.roll(ring, -1, axis=0)):
        e = b - a
        nrm = np.array([e[1], -e[0], 0.])          # outward for a counter-clockwise ring
        nrm /= max(np.linalg.norm(nrm), 1e-12)
        cuts.append((nrm, float(nrm[:2] @ a)))
    out = []
    for nrm, d in cuts:
        q = _clip_points(points, eq, nrm, d)
        if len(q) >= 4:
            made = _hull_piece(q, piece[2])
            if made is not None and made[1].volume > 1e-3:
                out.append(made)
    return out


def _blocks_flight(piece, tris, ids, step, height):
    """True when a collision piece stands in a flight's standing space: solid over a drawn tread sample more than
    FLOOR_TOLERANCE over the tread and lower than the standing box over it, and higher than a step there (it
    would bury the tread) or reaching into the box over the ramp."""
    pts, _ = tread_samples(tris, ids)
    # only where the drawn mesh leaves the standing box's height free over the tread (the check's own rule): a rail
    # or a rope drawn over the edge of a board keeps its collision
    pts = pts[_open_column(tris, pts, height) >= pts[:, 2] + height - 1e-6]
    if not len(pts):
        return False
    lows, highs, _ = column_intervals([piece], pts)
    z = pts[:, 2]
    solid = (lows[0] < highs[0]) & (highs[0] > z + step + 1e-3) & (lows[0] < z + height)
    return bool(solid.any())


def collision_pieces_mesh(v, f, profile, stairs=None, visible=None, runs=None, record=None, drawn=None,
                          authored=False):
    """Stair collision method 1 (see the module): (pieces, exact, note) as mesh_geometry.collision_pieces returns
    them. A mesh with no flight as drawn: exactly method 0. Every flight is checked (check_flight) on the mesh's own
    collision as method 0 converts it before its repairs over the drawn flights (no visible-tread rule); when every
    flight passes, method 0's collision is returned unchanged ('kept'); the flights that fail are replaced
    by a ramp or by tread blocks, the collision mesh's own triangles of those flights removed, the rest of the mesh
    converted as before, a remaining piece that stands in a replaced flight's standing space made the authored plates
    of its triangles. When the result still fails the check on any flight, the mesh keeps method 0's collision (never
    worse than method 0) and the note names the flights that failed. The note records per flight what was done.
    record (a dict, optional): 'removed' is set to the collision triangles (indices into f) of the replaced flights
    when the stairway mesh is shipped (never on the method 0 fallback).
    drawn: the mesh as drawn before any visual reduction (v, its exterior-selected faces), when it differs from
    visible (a visual recipe's or detail budget's reduced mesh): the flights, their stairway mesh and its proof come
    from it, as the build's stair check (mesh_report) and flight_unit read the mesh; method 0's visible-tread rule
    keeps the visible mesh. Built and proved on the reduced mesh, the slave market's ramp (recipe ratio 0.1) left a
    drawn tread 18.8 units over its floor (CHIM-STAIR-METHOD1-UNFIXED-48). None: the visible mesh is the drawn mesh.
    authored: v, f is the mesh's RootCollisionNode (flights: collision)."""
    step, _, height = player()
    runs = profile.get('stair_ramps', 'run') if runs is None else runs
    if runs not in RAMP_UNITS:
        raise ValueError('Unknown stair ramp unit: %s' % runs)
    profile = {k: x for k, x in profile.items() if k not in ('stair_collision', 'stair_ramps')}   # method 0's calls
    vis_v, vis_f = (v, f) if visible is None else visible
    if drawn is not None:
        vis_v, vis_f = drawn       # the flights and their proof: the mesh as drawn (visible stays method 0's)
    # authored: (v, f) is the mesh's RootCollisionNode; a drawn face it holds nothing under is no tread (flights)
    groups = flights(vis_v, vis_f, collision=(v, f) if authored else None) if len(vis_f) else []
    if not groups or profile.get('collision_none'):
        return mg.collision_pieces(v, f, profile, stairs, visible)
    vt = _tris(vis_v, vis_f)
    # the mesh's own collision (its RootCollisionNode, else the drawn mesh) as method 0 converts it before any repair
    # over the drawn flights: a flight it already makes walkable (an authored ramp through the nosings, a proxy that is
    # a walkable ramp) keeps it; the visible-tread rule's plate repairs are what method 1 replaces
    raw, _, _ = mg.collision_pieces(v, f, profile, stairs, None)
    replace = [k for k, ids in enumerate(groups) if check_flight(raw, vt, ids)]
    words = []
    if not replace:
        base, exact, note = mg.collision_pieces(v, f, profile, stairs, visible)    # method 0 exactly
        words.append('stair mesh: %d flights, the collision already passes the stair check (kept)' % len(groups))
        return base, exact, '; '.join(x for x in (note, *words) if x)
    coll = _tris(v, f)
    drop = set()
    for k in replace:
        drop.update(_flight_region(vt, groups[k], coll, step, height))
    keep = np.array([i for i in range(len(f)) if i not in drop], int)
    # the drawn triangles of the replaced flights (treads, risers, nosings: on or under a ramp by design); the rest of
    # the drawn mesh still goes to method 0's visible-tread rule, so everything off these flights is built as before
    flight_vis = set(int(t) for k in replace for t in groups[k])
    for k in replace:
        flight_vis.update(_flight_region(vt, groups[k], vt, step, height))
    off = np.array([i for i in range(len(vis_f)) if i not in flight_vis], int)
    others = vt[off].reshape(-1, 3) if len(off) else np.zeros((0, 3))
    rest_visible = (vis_v, vis_f[off]) if len(off) else None
    if drawn is not None and visible is not None:
        # method 0's visible-tread rule on the visible mesh less its triangles over the replaced flights
        seen = _tris(*visible)
        gone = set()
        for k in replace:
            gone.update(_flight_region(vt, groups[k], seen, step, height))
        left = np.array([i for i in range(len(visible[1])) if i not in gone], int)
        rest_visible = (visible[0], visible[1][left]) if len(left) else None
    rest = []
    if len(keep):
        rest, _, rest_note = mg.collision_pieces(v, f[keep], profile, stairs, rest_visible)
        # the piece ids index f[keep]; back to f
        rest = [(p, h, [int(keep[i]) for i in ids], e) for p, h, ids, e in rest]
        if rest_note:
            words.append(rest_note)
    made = []
    actions = []
    for k in replace:
        ids = groups[k]
        if runs == 'flight':
            piece, why = flight_ramp(vt, ids, others, step)
            if piece is not None:
                made.append(piece)
                actions.append('flight %d: one ramp' % k)
            else:
                blocks = tread_blocks(vt, ids)
                made.extend(blocks)
                actions.append('flight %d: %d tread blocks (%s)' % (k, len(blocks), why))
        else:
            pieces_k, nr, nb = run_ramps(vt, ids, others, step)
            made.extend(pieces_k)
            actions.append('flight %d: %d ramps, %d tread blocks' % (k, nr, nb))
    # a remaining piece standing in a replaced flight's space: the authored plates of its triangles, without the
    # upward faces lying over the replaced flights (a walkway's own deck in its collision mesh: the new plates are the
    # deck now; plating it again cost a rope bridge about 300 plates)
    walks = [k for k in replace if is_walkway(vt, groups[k], step)]
    stair_tris = [vt[groups[k]] for k in replace if k not in walks]
    walk_tris = [vt[groups[k]] for k in walks]
    stair_tris = np.concatenate(stair_tris) if stair_tris else np.zeros((0, 3, 3))
    walk_tris = np.concatenate(walk_tris) if walk_tris else np.zeros((0, 3, 3))

    def over(tri):
        return ((len(stair_tris) and _over_treads(tri, stair_tris))
                or (len(walk_tris) and _over_treads(tri, walk_tris, WALKWAY_TOUCH)))
    regions = {k: _standing_region(vt, groups[k], height) for k in replace}

    def blocking(piece):
        return [k for k in replace if _blocks_flight(piece, vt, groups[k], step, height)]

    def assemble(mode):
        # a remaining piece standing in a replaced flight's space: 'keep' loses its upward faces over the replaced
        # flights and is made convex pieces again; 'clip' then cuts what still stands there out of the flight's
        # standing space (its footprint up to the standing box's height; never where other drawn geometry is in
        # that part: a pillar on a landing keeps its collision); 'plate' makes what still stands there the authored
        # plates of its triangles (a rope bridge's rails cost ~300 pieces that way). The check decides between them.
        out, n = [], 0
        for piece in rest:
            hit = blocking(piece)
            if not hit:
                out.append(piece)
                continue
            n += 1
            subs = [piece]
            if piece[2]:
                tri_ids = np.array([i for i in piece[2] if not over(coll[i])], int)
                subs = [(sub[0], sub[1], [int(tri_ids[i]) for i in sub[2]], sub[3])
                        for sub in mg.collision_parts(v, f[tri_ids])] if len(tri_ids) else []
            for sub in subs:
                hit = blocking(sub)
                if not hit or mode == 'keep':
                    out.append(sub)
                    continue
                parts = [sub]
                for k in hit:
                    parts = [q for part in parts for q in _clip_out(part, regions[k], others)]
                if mode == 'plate' and sub[2] and any(blocking(q) for q in parts):
                    out.extend(mg.shell_collision_parts(v, f[np.array(sub[2], int)]))
                else:
                    out.extend(parts)
        return out + made, n
    # every way that passes the check, the one with the fewest planes kept (none passes: the last, which the final
    # check below reports)
    best = None
    for mode in ('keep', 'clip', 'plate'):
        final, plated = assemble(mode)
        if not any(x for _, x in check_flights(final, vis_v, vis_f, groups=groups)):
            cost = sum(len(_equations(q)[1]) for q in final)
            if best is None or cost < best[0]:
                best = (cost, mode, final, plated)
    if best is not None:
        _, mode, final, plated = best
    words.append('remaining collision over the flights: %s' % mode)
    result = check_flights(final, vis_v, vis_f, groups=groups)
    failed = [(k, x) for k, x in result if x]
    if failed:
        # never worse than method 0: a mesh whose flights the stairway mesh cannot all make pass keeps method 0's
        # collision, and the note names what failed (the open list, CHIM-STAIR-COLLISION-MESH-47)
        base, exact, note = mg.collision_pieces(v, f, profile, stairs, visible)
        words = ['stair mesh: %d flights; the stairway mesh did not pass the stair check (%s): method 0 kept'
                 % (len(groups), '; '.join('flight %d: %d samples, first %s' % (k, len(x), x[0]['check'])
                                          for k, x in failed))]
        return base, exact, '; '.join(x for x in (note, *words) if x)
    words.append('stair mesh: %d flights, %d kept, %d replaced (%s); %d collision triangles of the flights removed, '
                 '%d pieces in a flight converted again; check: %s'
                 % (len(groups), len(groups) - len(replace), len(replace), ', '.join(actions), len(drop), plated,
                    'passed' if not failed else '%d flights FAILED (%s)' % (
                        len(failed), '; '.join('flight %d: %d samples, first %s' % (k, len(x), x[0]['check'])
                                               for k, x in failed))))
    if record is not None:
        record['removed'] = sorted(int(i) for i in drop)
    return final, True, '; '.join(words)


# ---------------------------------------------------------------- the build's stair check (method 1 builds)

REPORT_NAME = 'stair-check.json'          # per CHIM work folder (chim.build)
WORLD_REPORT = 'chim-stair-check.json'    # the CHIM stage's collected report (chim_build)


def mesh_report(pieces, vis_v, vis_f, note='', collision=None):
    """The stair check of one converted mesh as the build ships it: its flights, which collision method it ships
    with (1: a stairway mesh replaced flights; 0: kept or fell back) and per failing flight the checks and the first
    failing point. None for a mesh without flights. collision: its authored collision (flights)."""
    groups = flights(vis_v, vis_f, collision=collision) if len(vis_f) else []
    if not groups:
        return None
    tris = _tris(vis_v, vis_f)
    failed = []
    for k, ids in enumerate(groups):
        found = check_flight(pieces, tris, ids)
        if found:
            checks = {}
            for x in found:
                checks[x['check']] = checks.get(x['check'], 0) + 1
            failed.append({'flight': k, 'checks': checks, 'first': found[0]})
    note = note or ''
    return {'flights': len(groups), 'ships_method': 1 if 'replaced (' in note else 0,
            'how': 'replaced' if 'replaced (' in note else ('method 0 kept' if 'method 0 kept' in note else 'kept'),
            'failed': failed}


KNOWN = 'config/stair-check-known.json'     # the meshes method 1 cannot make pass yet (one register class)


def load_known(path=None):
    """{mesh (lower case, forward slashes): reason} of the meshes whose flights method 1 cannot make pass yet: listed
    and registered as one class (the file's 'class'), never dropped; their failures are reported, not a stop."""
    import json
    from pathlib import Path
    path = Path(path) if path else Path(__file__).resolve().parents[1] / KNOWN
    if not path.is_file():
        return {}, None
    data = json.loads(path.read_text(encoding='utf-8'))
    return ({m.replace(chr(92), '/').casefold(): why for m, why in data.get('meshes', {}).items()},
            data.get('class'))


def collect(out, known=None):
    """The CHIM stage's stair check: every work folder's REPORT_NAME under OUT/work, as one report (written to
    OUT/WORLD_REPORT). Status 'failed' when a mesh that is not on the known list (config/stair-check-known.json)
    fails the check under the method it ships with; 'known' when only listed meshes fail (each named in 'known' with
    its failing flights; a listed mesh that now passes is named in 'known_passing'); 'passed' otherwise."""
    import json
    from pathlib import Path
    listed, cls = load_known() if known is None else (known, None)
    rows = []
    for path in sorted((Path(out) / 'work').glob('*/' + REPORT_NAME)):
        for row in json.loads(path.read_text(encoding='utf-8')).get('meshes', ()):
            rows.append(dict(row, frame_work=path.parent.name))
    meshes = {}
    for r in rows:
        meshes.setdefault(r['mesh'], r)
    def key(m):
        return m.replace(chr(92), '/').casefold()
    failing = sorted(m for m, r in meshes.items() if r['failed'] and key(m) not in listed)
    known_failing = sorted(m for m, r in meshes.items() if r['failed'] and key(m) in listed)
    report = {'format': 1, 'method': 1,
              'status': 'failed' if failing else ('known' if known_failing else 'passed'),
              'meshes': len(meshes), 'flights': sum(r['flights'] for r in meshes.values()),
              'ships_method_1': sorted(m for m, r in meshes.items() if r['ships_method'] == 1),
              'failing': [{'mesh': m, 'ships_method': meshes[m]['ships_method'], 'how': meshes[m]['how'],
                           'failed': meshes[m]['failed']} for m in failing],
              'known_class': cls,
              'known': [{'mesh': m, 'reason': listed[key(m)], 'ships_method': meshes[m]['ships_method'],
                         'how': meshes[m]['how'], 'failed': meshes[m]['failed']} for m in known_failing],
              'known_passing': sorted(m for m, r in meshes.items() if not r['failed'] and key(m) in listed)}
    (Path(out) / WORLD_REPORT).write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    return report


def require(out, known=None):
    """collect, and a ValueError naming every mesh (and its first failing flight and point) that fails the check
    under the method it ships with and is not on the known list (config/stair-check-known.json)."""
    report = collect(out, known)
    if report['failing']:
        first = report['failing'][:5]
        raise ValueError('Stair check failed on %d of %d meshes with flights (method each ships with): %s%s'
                         % (len(report['failing']), report['meshes'],
                            '; '.join('%s (method %d, %s): flight %d %s at %s' % (
                                x['mesh'], x['ships_method'], x['how'], x['failed'][0]['flight'],
                                x['failed'][0]['first']['check'], x['failed'][0]['first']['point']) for x in first),
                            '; ...' if len(report['failing']) > 5 else ''))
    return report


# ---------------------------------------------------------------- method 1 in the converter (its own worker)

def collision_pieces(v, f, profile, stairs=None, visible=None, record=None, drawn=None, authored=False):
    """mesh_geometry.collision_pieces with stair collision method 1 for a profile with stair_collision 'mesh'
    (collision_pieces_mesh); any other profile: mesh_geometry.collision_pieces exactly. record, drawn, authored: see
    collision_pieces_mesh (drawn also for the authored-ramp rule's check)."""
    if profile.get('stair_collision') == 'mesh':
        return keep_stair_ramps(v, f, *collision_pieces_mesh(v, f, profile, stairs, visible, record=record,
                                                             drawn=drawn, authored=authored), visible, drawn)
    return mg.collision_pieces(v, f, profile, stairs, visible)


def drawn_mesh(model, archive_path):
    """(v, faces) of a scenery-index model as drawn: its triangles with the exterior selection applied, before any
    visual reduction (what flight_unit, mesh_report and tools/stair_mesh_survey.py read)."""
    from mwad.scene import read_asset, unpack_geometry
    from exterior_visibility import apply_exterior_selection
    with open(archive_path, 'rb') as archive:
        vv, ff, _ = unpack_geometry(read_asset(archive, model))
    v, f = np.array(vv), np.array(ff)
    return v, apply_exterior_selection(f, model)


def authored_collision(model, archive_path):
    """(v, f) of a scenery-index model's authored collision (its RootCollisionNode), or None when the drawn mesh
    collides (flights: collision)."""
    if not model.get('collision'):
        return None
    from mwad.scene import read_asset, unpack_geometry
    with open(archive_path, 'rb') as archive:
        vv, ff, _ = unpack_geometry(read_asset(archive, model['collision']))
    return np.array(vv), np.array(ff)


def _same_mesh(a, b):
    """True when two (v, f) meshes are the same arrays (no visual reduction between them)."""
    return (a[0].shape == b[0].shape and a[1].shape == b[1].shape and np.array_equal(a[0], b[0])
            and np.array_equal(a[1], b[1]))


def keep_stair_ramps(v, f, pieces, exact, note, visible, drawn=None):
    """An authored stair ramp stays a ramp (tools/authored_ramps.py): a convex piece that stands over a ramp of the
    collision mesh lying on a drawn flight, steeper than walkable or more than a step over it where the authored
    surfaces are not, becomes the authored plates of its own triangles; kept only when the stair check of the mesh's
    flights is not worse with it (the check is the proof). drawn: as collision_pieces_mesh."""
    from authored_ramps import keep_authored_ramps, stair_ramp_faces
    if visible is None or not pieces:
        return pieces, exact, note
    vis_v, vis_f = visible if drawn is None else drawn
    ids = stair_ramp_faces(v, f, vis_v, vis_f)
    kept, kept_exact, extra = keep_authored_ramps(v, f, pieces, exact, ids)
    if extra is None or kept is pieces:
        return pieces, exact, note
    before = sum(1 for _, x in check_flights(pieces, vis_v, vis_f) if x)
    after = sum(1 for _, x in check_flights(kept, vis_v, vis_f) if x)
    if after > before:
        return pieces, exact, '; '.join(x for x in (note, extra + ': not kept (the stair check failed on %d flights '
                                                    'with it, %d without)' % (after, before)) if x)
    return kept, kept_exact, '; '.join(x for x in (note, extra) if x)


def flight_unit(task):
    """The number of flights of stairs one CHIM mesh holds as drawn (unit kind 'stair-flights', chim.units): flights()
    on its drawn triangles with the exterior selection applied, before any visual reduction (as mesh_report and
    tools/stair_mesh_survey.py read them). The CHIM model builder gives a mesh with a flight stair collision method 1
    (profile stair_collision 'mesh', unit kind 'mesh-stair'); every other mesh keeps the default worker, profile and
    unit key, since method 1 is method 0 exactly on a mesh without a flight. task: (scenery-index model record,
    archive path)."""
    model, archive_path = task
    v, vis_f = drawn_mesh(model, archive_path)
    return len(flights(v, vis_f, collision=authored_collision(model, archive_path))) if len(vis_f) else 0


def mesh_unit_stair(task):
    """The CHIM mesh unit of a stair collision method 1 build (unit kind 'mesh-stair', chim.units.CODE_ENTRIES): the
    default worker (chim.build.mesh_unit, prepare_mesh_bsp._prepare_model) with its collision made by
    collision_pieces above, and the mesh's stair check in its lod ('stair_check', mesh_report). The shared converter
    modules hold no method 1 code, so a default build's mesh units keep their code keys. The collision triangles of
    the flights the stairway mesh replaced (indices into the collision mesh) go into the lod
    ('stair_removed_triangles'): the collision surface gate does not measure them (chim.build.hull_surface_unit,
    CHIM-HULL-SURFACE-RESURVEY-48)."""
    import prepare_mesh_bsp
    from chim.build import mesh_unit
    from exterior_visibility import apply_exterior_selection
    default = prepare_mesh_bsp.collision_pieces
    record = {}
    _, model, profile, archive_path, *_ = task
    drawn = drawn_mesh(model, archive_path) if profile.get('stair_collision') == 'mesh' else None
    authored = bool(model.get('collision'))

    def method1(v, f, profile, stairs=None, visible=None):
        # the flights from the mesh as drawn when the visible mesh is a reduced one (collision_pieces_mesh drawn)
        own = drawn if drawn is not None and visible is not None and not _same_mesh(drawn, visible) else None
        return collision_pieces(v, f, profile, stairs, visible, record=record, drawn=own, authored=authored)
    prepare_mesh_bsp.collision_pieces = method1
    try:
        out = mesh_unit(task)
    finally:
        prepare_mesh_bsp.collision_pieces = default
    _, model, profile, *_ = task
    if profile.get('stair_collision') == 'mesh':
        v, f, _, pieces, lod = out
        if record.get('removed'):
            lod['stair_removed_triangles'] = [int(i) for i in record['removed']]
        vis_f = apply_exterior_selection(np.asarray(f), model)
        report = mesh_report(pieces, np.asarray(v), vis_f, lod.get('collision') or '',
                             collision=authored_collision(model, archive_path))
        if report:
            lod['stair_check'] = report
    return out
