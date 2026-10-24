# SPDX-License-Identifier: GPL-3.0-only
"""An authored ramp stays a ramp (docs/COLLISION_MESHES.md recommendations 2 and 3, COLLISION-RCN-SCOPE-32).

Morrowind's artists give a staircase an authored collision ramp of at most 45 degrees (its RootCollisionNode); the
player walks the ramp, not the drawn steps. The engine stands on a surface whose normal z is at least WALKABLE_Z
(0.69, about 46 degrees), so a 45-degree ramp has about 1.4 degrees of margin. The converter turns collision
triangles into convex pieces (mesh_geometry.collision_pieces); a piece that takes in a ramp together with steeper
neighbours (a wall, a parapet, a step up at its top) can stand over the ramp with a face steeper than walkable, and
the ramp becomes a slope nobody climbs.

The check here is plane arithmetic on the pieces, no walk: over sample points of every walkable sloped face of the
collision mesh (a ramp: normal z at least WALKABLE_Z, more than 10 degrees from level), the collision just over the
ramp must not be a face steeper than walkable, and must not stand more than a step over it. The repair
(keep_authored_ramps): a piece that does either becomes the authored plates of its own triangles (exact standing
bevels; mesh_geometry.shell_collision_parts), as the stair-plate rules do for a piece that invents a steep face
(mesh_geometry._invents_steep_face, VIVEC-TEMPLE-STAIRS-33). Pieces with no source triangles of their own (plates
and ramps other rules made) are left as they are.
"""
import numpy as np
from scipy.spatial import ConvexHull

RAMP_LEVEL_NZ = .985    # a face within 10 degrees of level is a floor or a tread, not a ramp (mesh_geometry.TREAD_NZ)
RAMP_MIN_AREA = 2.      # square units at the converter's scale: smaller faces are trim
OVER = .5               # collision more than this over a ramp point covers the ramp there (a plate's rounding is .28)


def _tris(v, f):
    return np.asarray(v, float)[np.asarray(f)[:, :3], :3] * .25


def ramp_faces(v, f):
    """Indices into f of the collision mesh's ramps: walkable, not level, not trim."""
    from player_hull import WALKABLE_Z
    if not len(f):
        return np.zeros(0, int)
    t = _tris(v, f)
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    a = np.linalg.norm(n, axis=1)
    nz = np.zeros(len(t))
    ok = a > 1e-9
    nz[ok] = n[ok, 2] / a[ok]
    return np.flatnonzero(ok & (nz >= WALKABLE_Z) & (nz < RAMP_LEVEL_NZ) & (a / 2 >= RAMP_MIN_AREA))


def ramp_samples(v, f, ids):
    """(points, face of each point): each ramp face's centroid and three points 60 % of the way to its corners."""
    t = _tris(v, f)[ids]
    c = t.mean(axis=1)
    pts = [c] + [c + .6 * (t[:, k] - c) for k in range(3)]
    return np.concatenate(pts), np.tile(np.asarray(ids), 4)


def _equations(piece):
    points, hull = np.asarray(piece[0], float), piece[1]
    return points, (hull.equations if hull is not None else ConvexHull(points).equations)


def _columns(pieces, pts):
    """Per piece and point: the solid interval over the point's column (low, high) and the top face's normal z."""
    n = len(pts)
    lows = np.full((len(pieces), n), np.inf)
    highs = np.full((len(pieces), n), -np.inf)
    tops = np.ones((len(pieces), n))
    for k, piece in enumerate(pieces):
        points, eq = _equations(piece)
        lo, hi = points.min(axis=0) - 1e-3, points.max(axis=0) + 1e-3
        sel = np.flatnonzero((pts[:, 0] >= lo[0]) & (pts[:, 0] <= hi[0]) & (pts[:, 1] >= lo[1]) & (pts[:, 1] <= hi[1]))
        if not len(sel):
            continue
        p = pts[sel]
        r = -(p[:, :2] @ eq[:, :2].T + eq[:, 3])
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


def ramp_faults(pieces, v, f, ids=None):
    """The places where the collision pieces do not keep the collision mesh's ramps walkable: a list of
    {'face', 'point', 'kind' ('steep': the surface over the ramp is steeper than walkable; 'buried': collision
    stands more than a step over it), 'piece', 'over' (units over the ramp), 'nz'}."""
    from player_hull import STEP_HEIGHT, WALKABLE_Z
    ids = ramp_faces(v, f) if ids is None else np.asarray(ids, int)
    if not len(ids) or not pieces:
        return []
    pts, owner = ramp_samples(v, f, ids)
    lows, highs, tops = _columns(pieces, pts)
    probe = pts[:, 2] + OVER
    out = []
    for i in range(len(pts)):
        covering = np.flatnonzero((lows[:, i] < probe[i]) & (highs[:, i] > probe[i]))
        if not len(covering):
            continue
        k = int(covering[np.argmax(highs[covering, i])])
        over = float(highs[k, i] - pts[i, 2])
        if over > STEP_HEIGHT:
            kind = 'buried'
        elif tops[k, i] < WALKABLE_Z:
            kind = 'steep'
        else:
            continue
        out.append({'face': int(owner[i]), 'point': [round(float(x), 3) for x in pts[i]], 'kind': kind, 'piece': k,
                    'over': round(over, 3), 'nz': round(float(tops[k, i]), 4)})
    return out


STAIR_REACH = 2.5       # a ramp face whose centre lies this close in plan to a drawn tread of a flight is that flight's


def stair_ramp_faces(v, f, vis_v, vis_f):
    """The ramps of the collision mesh (ramp_faces) that belong to a staircase: the centre of the face lies over a
    drawn flight (stair_mesh.flights: within STAIR_REACH units in plan of one of its treads, and between a step under
    its lowest tread and a step over its highest). Walkable slopes elsewhere (a rock's facets, a tree's roots, a
    bed's cover) are not stair ramps: measured on the v0.0.47 build, plating every walkable slope a convex piece
    covers would grow those meshes' collision by 58 % (a rock by x120), for no staircase."""
    from player_hull import STEP_HEIGHT
    from stair_mesh import flights, _tris as vis_tris, _plan_distances
    ids = ramp_faces(v, f)
    if not len(ids) or not len(vis_f):
        return np.zeros(0, int)
    groups = flights(np.asarray(vis_v), np.asarray(vis_f))
    if not groups:
        return np.zeros(0, int)
    centres = _tris(v, f)[ids].mean(axis=1)
    vt = vis_tris(np.asarray(vis_v), np.asarray(vis_f))
    keep = np.zeros(len(ids), bool)
    for g in groups:
        t = vt[g]
        lo, hi = t[:, :, 2].min() - STEP_HEIGHT, t[:, :, 2].max() + STEP_HEIGHT
        near = np.full(len(ids), np.inf)
        p = centres[:, :2]
        for tri in t:
            a = tri[:, :2]
            b = np.roll(a, -1, axis=0)
            near = np.minimum(near, _plan_distances(p, a, b).min(axis=1))
            side = (b[None, :, 0] - a[None, :, 0]) * (p[:, None, 1] - a[None, :, 1]) \
                - (b[None, :, 1] - a[None, :, 1]) * (p[:, None, 0] - a[None, :, 0])
            inside = (side >= 0).all(axis=1) | (side <= 0).all(axis=1)
            near[inside] = 0.
        keep |= (near <= STAIR_REACH) & (centres[:, 2] >= lo) & (centres[:, 2] <= hi)
    return ids[keep]


def invented_ramp_faults(pieces, v, f, ids=None):
    """ramp_faults that the authored collision itself does not have: the same check on the collision mesh's own
    surfaces as thin plates (mesh_geometry.shell_collision_parts, what Morrowind collides with) finds nothing at that
    place. A steep authored face over an authored ramp (a bed's headboard over its sloped cover) is the artist's, not
    the converter's. ids: the ramp faces to check (default every ramp_faces)."""
    from mesh_geometry import shell_collision_parts
    faults = ramp_faults(pieces, v, f, ids)
    if not faults:
        return []
    authored = {(x['face'], tuple(x['point']))
                for x in ramp_faults(shell_collision_parts(v, np.asarray(f)), v, f, ids)}
    return [x for x in faults if (x['face'], tuple(x['point'])) not in authored]


def keep_authored_ramps(v, f, pieces, exact, ids=None):
    """(pieces, exact, note): a piece that stands over a ramp of the collision mesh (ids: the ramp faces; default
    every ramp_faces) with a face steeper than walkable or more than a step over it, where the authored surfaces do
    not, becomes the authored plates of its own triangles (exact standing bevels for those); note None when nothing
    changed. The ramp check is run again on the result and the note says what remains."""
    from mesh_geometry import shell_collision_parts
    if ids is not None and not len(ids):
        return pieces, exact, None
    faults = invented_ramp_faults(pieces, v, f, ids)
    if not faults:
        return pieces, exact, None
    culprits = sorted({x['piece'] for x in faults if len(pieces[x['piece']][2])})
    if not culprits:
        return pieces, exact, 'authored ramps: %d places over a ramp not walkable, by pieces of no own triangles' % len(
            faults)
    out, plates, kept_exact = [], [], []
    f = np.asarray(f)
    for k, piece in enumerate(pieces):
        if k in culprits:
            for plate in shell_collision_parts(v, f[np.array(piece[2], int)]):
                plates.append(len(out))
                out.append(plate)
            continue
        if exact and exact is not True and k in exact:
            kept_exact.append(len(out))
        out.append(piece)
    new_exact = True if exact is True else frozenset(kept_exact) | frozenset(plates)
    left = invented_ramp_faults(out, v, f, ids)
    note = ('authored ramps: %d convex pieces stood over a ramp of the collision mesh (%d places: %s) and became '
            '%d authored plates' % (len(culprits), len(faults),
                                    ', '.join(sorted({x['kind'] for x in faults})), len(plates)))
    if left:
        note += '; %d places still not walkable' % len(left)
    return out, new_exact, note
