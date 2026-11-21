# SPDX-License-Identifier: GPL-3.0-only
"""Method C of the mesh method sets (config/mesh-method-sets.json, chim.method_sets; SOL-GLACIER-METHODS-AB-COMPARE-68):
a placed model's collision with exact footing, made from today's pieces after the placement's scale and tilt.

Today a listed ice model's collision is one convex piece per triangle of its collision mesh (the walkable surface
kept: config/collision-hull-surface.json), about two thirds of a copy's bytes (docs/chim/SOLSTHEIM_GLACIER.md). Method
C keeps that collision where the player stands and makes the rest coarser, per placed variant, in this order:

1. every piece holding a triangle that is walkable AS PLACED (its normal's z, after the copy's scale and tilt, at least
   player_hull.WALKABLE_Z) stays as it is: the walkable surface is today's, exactly;
2. the triangles of the other pieces become convex proxies (mesh_geometry.collision_parts at the row's tolerance);
3. each proxy is tested against TODAY's collision top on a grid over the walkable surface (the row's grid, 2 local
   units = 8 game units): where it rises more than the row's rise (2 local units = 8 game units) over today's top
   there, it is split at the median of its triangles along their longest axis (mesh_geometry._proxy_piece), again
   until each part passes; a part of SPLIT_MIN triangles or fewer that still rises goes back to today's own pieces.
4. a walkable cell whose new top then lies more than the rise under both today's top and the drawn ice (or has no top:
   a walkable triangle without a piece of its own) gets back today's pieces that make today's top there; where the new
   top stands on the drawn ice and today's stood higher (one of today's pieces reaching over the ice), the ice stays.
The test is the acceptance itself, measured on the same grid: on the walkable surface nothing is lost and nothing rises
more than the row's rise over today's top or drops more under it, except where it now stands on the drawn ice (counted
apart). Every placed variant reports its figures (FIGURES_KEY, taken out of the result by chim.method_sets before the
converter sees it).

The drawn faces are not touched. The collision mesh must be the model's own mesh (no authored collision node, no
reduced collision record, no stair collision replacement): a model that is not is refused, named.

Own unit kinds (KINDS: the converter's variant, BSP2 variant and image-budget tile kinds, each with '-c'), registered by
chim.method_sets for the process that installs a set, so no existing kind's key reaches this module; each worker runs
the converter's own worker with prepare_mesh_bsp._prepare_placement giving the method's pieces for that one call and
the original function again after it, whatever happens (as chim.union_bsp2 swaps the compiler).
"""
import time
from types import SimpleNamespace

import numpy as np

FORM = 'exact-footing-1'
FIGURES_KEY = 'collision_exact'
GAME = 4.0                       # game units per converter unit
DEFAULTS = {'tolerance': 2.0, 'grid': 2.0, 'rise': 2.0, 'split_min': 4}
# the converter's kind -> (this method's kind, its worker in this module)
KINDS = {'variant': ('variant-c', 'variant_unit_c'),
         'variant-bsp2': ('variant-bsp2-c', 'variant_unit_bsp2_c'),
         'tiles-budget': ('tiles-budget-c', 'budget_tile_unit_c'),
         'tiles-budget-union': ('tiles-budget-union-c', 'budget_tile_unit_union_c')}


def settings(row):
    """The method's settings from its row in a set (DEFAULTS for what the row leaves out); unknown keys refused."""
    row = dict(row or {})
    unknown = sorted(set(row) - set(DEFAULTS) - {'about'})
    if unknown:
        raise ValueError('method C: unknown setting(s) %s' % ', '.join(unknown))
    out = {k: type(v)(row.get(k, v)) for k, v in DEFAULTS.items()}
    if not (out['tolerance'] > 0 and out['grid'] > 0 and out['rise'] > 0 and out['split_min'] >= 1):
        raise ValueError('method C: tolerance, grid and rise must be positive and split_min at least 1: %r' % out)
    return out


def placed_triangles(data, ref, centre):
    """The collision triangles of prepared mesh DATA as the placement REF puts its pieces (prepare_mesh_bsp
    _prepare_placement: scale and tilt, the yaw left to the entity), converter units. Refused when the pieces are not
    made from the model's own mesh."""
    from prepare_mesh_bsp import SCALE, _placement_frame
    from prepare_scenery import reference_rotation
    v, f, _, components, lod = data
    lod = lod or {}
    # (the converter's note 'authored collision surfaces: ...' is the walkable-surface rule on the model's own mesh;
    # a RootCollisionNode is another mesh, whose triangles the pieces' ids name)
    if 'RootCollisionNode' in str(lod.get('collision', '')) or lod.get('collision_mesh') \
            or len(lod.get('stair_removed_triangles') or ()):
        raise ValueError('method C needs the collision made from the model\'s own mesh (%s)'
                         % (lod.get('collision') or 'a reduced or stair collision mesh'))
    f = np.asarray(f, int)
    top = max((max(ids) for _, _, ids, _ in components if len(ids)), default=-1)
    if top >= len(f):
        raise ValueError('method C: a piece names triangle %d of %d' % (top, len(f)))
    _, rotation = _placement_frame(ref, centre)
    r = rotation.T @ reference_rotation(ref)
    return (np.asarray(v, float)[f[:, :3], :3] * SCALE) @ r.T * float(ref['scale'])


def walkable(tris):
    """Per triangle: walkable as placed (its normal's z at least player_hull.WALKABLE_Z)."""
    from player_hull import WALKABLE_Z
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    a = np.linalg.norm(n, axis=1)
    nz = np.where(a > 1e-9, n[:, 2] / np.maximum(a, 1e-12), 0.0)
    return nz >= WALKABLE_Z


HOLD = 0.05                      # a triangle's centre this close outside a piece is in it (stored hulls are rounded)
THICK = 0.25                     # a flat piece's top lies this much over its triangle at most (thickened 0.2, rounded)


def holding(parts, tris):
    """[the indices of TRIS whose centre lies in piece i (within HOLD)] for every piece of PARTS: which triangles of
    the collision mesh each piece is made of (the pieces do not always carry their triangles' numbers)."""
    from scipy.spatial import cKDTree
    centres = tris.mean(axis=1)
    tree = cKDTree(centres)
    out = []
    for points, hull, _, _ in parts:
        p = np.asarray(points, float)
        lo, hi = p.min(axis=0), p.max(axis=0)
        near = tree.query_ball_point((lo + hi) / 2, float(np.linalg.norm(hi - lo)) / 2 + HOLD)
        if not near:
            out.append(np.zeros(0, int))
            continue
        near = np.asarray(near, int)
        eq = np.asarray(hull.equations, float)
        inside = (centres[near] @ eq[:, :3].T + eq[:, 3] <= HOLD).all(axis=1)
        out.append(np.sort(near[inside]))
    return out


def column(equations, X, Y):
    """(top, bottom, inside) of one convex piece over grid points X, Y: its top and bottom where a vertical line
    through the point crosses it."""
    hi = np.full(X.shape, np.inf)
    lo = np.full(X.shape, -np.inf)
    ok = np.ones(X.shape, dtype=bool)
    for nx, ny, nz, d in np.asarray(equations, float):
        r = -(d + nx * X + ny * Y)
        if nz > 1e-6:
            hi = np.minimum(hi, r / nz)
        elif nz < -1e-6:
            lo = np.maximum(lo, r / nz)
        else:
            ok &= r >= -1e-6
    return hi, lo, ok & (hi >= lo)


class Grid:
    """The test grid over a variant's collision: cell centres every STEP over the box of its triangles."""

    def __init__(self, tris, step):
        pts = tris.reshape(-1, 3)
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        self.step = step
        self.xs = np.arange(lo[0] + step / 2, hi[0], step)
        self.ys = np.arange(lo[1] + step / 2, hi[1], step)

    def window(self, points):
        p = np.asarray(points, float)
        i0, i1 = np.searchsorted(self.xs, p[:, 0].min()), np.searchsorted(self.xs, p[:, 0].max(), 'right')
        j0, j1 = np.searchsorted(self.ys, p[:, 1].min()), np.searchsorted(self.ys, p[:, 1].max(), 'right')
        if i0 >= i1 or j0 >= j1:
            return None
        X, Y = np.meshgrid(self.xs[i0:i1], self.ys[j0:j1])
        return (slice(j0, j1), slice(i0, i1)), X, Y

    def top(self, parts):
        """The collision top over the grid (-inf where no piece is)."""
        out = np.full((len(self.ys), len(self.xs)), -np.inf)
        for points, hull, _, _ in parts:
            w = self.window(points)
            if w is None:
                continue
            at, X, Y = w
            hi, _, good = column(hull.equations, X, Y)
            sub = out[at]
            sub[good] = np.maximum(sub[good], hi[good])
        return out

    def walkable_tops(self, tris, walk, heights=None):
        """Grid cells whose topmost collision triangle is walkable as placed: the walkable surface. HEIGHTS (a list):
        gets the topmost triangle's height per cell (-inf where none)."""
        top = np.full((len(self.ys), len(self.xs)), -np.inf)
        flag = np.zeros(top.shape, dtype=bool)
        for t, w in zip(tris, walk):
            a, b, c = t
            win = self.window(t)
            if win is None:
                continue
            at, X, Y = win
            den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(den) < 1e-9:
                continue
            l1 = ((b[1] - c[1]) * (X - c[0]) + (c[0] - b[0]) * (Y - c[1])) / den
            l2 = ((c[1] - a[1]) * (X - c[0]) + (a[0] - c[0]) * (Y - c[1])) / den
            l3 = 1 - l1 - l2
            inside = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
            z = l1 * a[2] + l2 * b[2] + l3 * c[2]
            sub = top[at]
            better = inside & (z > sub)
            sub[better] = z[better]
            flag[at][better] = bool(w)
        if heights is not None:
            heights.append(top)
        return flag


def exact_footing(data, ref, centre, parts, row=None):
    """(the method's pieces, figures) for one placed variant: PARTS are today's placed pieces (prepare_mesh_bsp
    _prepare_placement), DATA its prepared mesh, REF and CENTRE the placement. See the module text."""
    from mesh_geometry import _proxy_piece, collision_parts
    from prepare_mesh_bsp import SCALE
    t0 = time.time()
    cfg = settings(row)
    figures = {'form': FORM, 'pieces_today': len(parts)}
    if not parts:
        return list(parts), dict(figures, pieces=0, seconds=0.0)
    tris = placed_triangles(data, ref, centre)
    walk = walkable(tris)
    holds = holding(parts, tris)                 # piece -> the triangles whose centre lies in it
    kept_at = [i for i in range(len(parts)) if walk[holds[i]].any()]
    kept = set(kept_at)
    covered = np.zeros(len(tris), dtype=bool)
    for i in kept_at:
        covered[holds[i]] = True
    # the triangles to make again: in some piece today, in no kept piece; a piece that holds no triangle's centre
    # (a plate the converter added, a toe cut) stays as it is
    pieces_of = {}
    for i in range(len(parts)):
        if i not in kept:
            for t in holds[i]:
                if not covered[t]:
                    pieces_of.setdefault(int(t), []).append(i)
    steep = np.array(sorted(pieces_of), dtype=int)
    replaced = {i for i in range(len(parts)) if i not in kept and len(holds[i])
                and all(int(t) in pieces_of or covered[t] for t in holds[i])}
    untouched = [i for i in range(len(parts)) if i not in kept and i not in replaced]
    grid = Grid(tris, cfg['grid'])
    today = grid.top(parts)
    heights = []
    surface = grid.walkable_tops(tris, walk, heights) & np.isfinite(today)
    drawn = heights[0]                           # the topmost triangle's height: the ice as drawn

    def rises(equations, points):
        w = grid.window(points)
        if w is None:
            return False
        at, X, Y = w
        hi, _, good = column(equations, X, Y)
        over = good & surface[at] & (hi - today[at] > cfg['rise'])
        return bool(over.any())
    out = [parts[i] for i in kept_at] + [parts[i] for i in untouched]
    back, counts = set(), {'proxies': 0, 'splits': 0, 'parts_back': 0, 'untouched': len(untouched)}
    if len(steep):
        own = tris[steep]

        def keep_or_split(local):
            part = _proxy_piece(own, list(local))
            if part is not None and not rises(part[1].equations, part[0]):
                out.append((part[0], SimpleNamespace(equations=part[1].equations), [int(t) for t in steep[local]],
                            part[3]))
                counts['proxies'] += 1
                return
            if part is None or len(local) <= cfg['split_min']:
                counts['parts_back'] += 1
                for t in steep[local]:
                    back.update(pieces_of[int(t)])
                return
            counts['splits'] += 1
            centres = own[local].mean(axis=1)
            axis = int(np.argmax(np.ptp(centres, axis=0)))
            order = np.argsort(centres[:, axis], kind='stable')
            mid = len(order) // 2
            keep_or_split(np.asarray(local)[order[:mid]])
            keep_or_split(np.asarray(local)[order[mid:]])
        vertices = own.reshape(-1, 3) / SCALE          # collision_parts takes mesh units (it scales by 0.25)
        faces = np.column_stack([np.arange(len(vertices)).reshape(-1, 3), np.zeros(len(own), int)])
        for points, hull, ids, error in collision_parts(vertices, faces, cfg['tolerance']):
            if rises(hull.equations, points):
                keep_or_split(np.asarray(ids, int))
            else:
                out.append((points, SimpleNamespace(equations=hull.equations), [int(t) for t in steep[ids]], error))
                counts['proxies'] += 1
    out.extend(parts[i] for i in sorted(back))
    # the repair: a walkable cell whose new top lies more than the rise under both today's top and the drawn ice (or
    # has none: lost) gets back today's replaced pieces that make today's top there; a cell where the new top stands
    # on the drawn ice while today's stood higher (a piece of today reaching over the ice) keeps the ice
    after = grid.top(out)
    low = surface & (~np.isfinite(after) | (after < np.minimum(today, drawn + THICK) - cfg['rise']))
    restored = set()
    if low.any():
        lowest = np.where(np.isfinite(after), after, -np.inf)
        for i in sorted(replaced - back):
            w = grid.window(parts[i][0])
            if w is None:
                continue
            at, X, Y = w
            hi, _, good = column(parts[i][1].equations, X, Y)
            if (good & low[at] & (hi >= today[at] - cfg['rise']) & (hi > lowest[at])).any():
                restored.add(i)
        out.extend(parts[i] for i in sorted(restored))
        after = grid.top(out)
    # the figures, measured on the result itself: the walkable surface's move against today's top
    move = (after[surface] - today[surface]) * GAME
    lost = int((~np.isfinite(after[surface])).sum())
    finite = np.isfinite(move)
    # dropped more than the rise under today's top but standing within the rise of the drawn ice: today's top stood
    # over the ice there (a piece of today reaching over it), counted apart
    on_ice = finite & (move < -cfg['rise'] * GAME) & (after[surface] >= drawn[surface] - cfg['rise'])
    largest, where = 0.0, None
    if finite.any():
        k = int(np.argmax(np.where(finite & ~on_ice, np.abs(move), -1)))
        largest = float(abs(move[k])) if finite[k] and not on_ice[k] else 0.0
        jj, ii = np.nonzero(surface)
        where = [round(float(grid.xs[ii[k]]) * GAME), round(float(grid.ys[jj[k]]) * GAME)] if largest else None
    above = (today[surface] - drawn[surface]) * GAME
    figures.update(counts, pieces=len(out), kept=len(kept_at), back=len(back), restored=len(restored),
                   triangles=int(len(tris)), walkable_triangles=int(walk.sum()), grid_game_units=cfg['grid'] * GAME,
                   walkable_cells=int(surface.sum()), lost_cells=lost,
                   over_8_cells=int((finite & ~on_ice & (np.abs(move) > 8.0)).sum()),
                   over_rise_cells=int((finite & ~on_ice & (np.abs(move) > cfg['rise'] * GAME)).sum()),
                   on_drawn_ice_cells=int(on_ice.sum()),
                   on_drawn_ice_largest=round(float(above[on_ice].max()), 2) if on_ice.any() else 0.0,
                   moved_over_8_cells=int((finite & (np.abs(move) > 8.0)).sum()),
                   largest_move=round(largest, 2), largest_at=where, settings=cfg,
                   seconds=round(time.time() - t0, 2))
    return out, figures


class Placement:
    """prepare_mesh_bsp._prepare_placement giving method C's pieces for one prepared mesh (DATA) while it is
    installed; every other call goes to the original. The figures of each placement it made are kept in FIGURES."""

    def __init__(self, data, row):
        import prepare_mesh_bsp
        self.module, self.data, self.row = prepare_mesh_bsp, data, row
        self.original = prepare_mesh_bsp._prepare_placement
        self.made, self.figures = {}, []

    def __call__(self, task):
        got = self.original(task)
        ref, data, _, centre = task[:4]
        if data is not self.data:
            return got
        key = (id(ref), tuple(float(c) for c in centre))
        if key not in self.made:
            parts, figures = exact_footing(data, ref, centre, got[1], self.row)
            self.made[key] = parts
            self.figures.append(figures)
        return (got[0], self.made[key], *got[2:])

    def __enter__(self):
        self.module._prepare_placement = self
        return self

    def __exit__(self, *exc):
        self.module._prepare_placement = self.original
        return False


def _with_figures(result, figures):
    """RESULT with the method's figures under FIGURES_KEY: a variant's dict, or the first tile of (grain, tiles)."""
    if not figures:
        return result
    if isinstance(result, dict):
        return dict(result, **{FIGURES_KEY: figures[-1]})
    grain, tiles = result
    if not tiles:
        return result
    return grain, [dict(tiles[0], **{FIGURES_KEY: figures[-1]}), *tiles[1:]]


def run_c(task, worker):
    """WORKER(TASK) (a converter unit worker) with method C's pieces for the task's prepared mesh."""
    row = task.get('collision_exact_row')
    plain = {k: v for k, v in task.items() if k != 'collision_exact_row'}
    with Placement(plain['data'], row) as placement:
        result = worker(plain)
    return _with_figures(result, placement.figures)


def variant_unit_c(task):
    """chim.models.variant_unit with method C (unit kind 'variant-c')."""
    from chim import models as M
    return run_c(task, M.variant_unit)


def variant_unit_bsp2_c(task):
    """chim.union_bsp2.variant_unit_bsp2 with method C (unit kind 'variant-bsp2-c')."""
    from chim import union_bsp2 as U
    return run_c(task, U.variant_unit_bsp2)


def budget_tile_unit_c(task):
    """chim.budget_tiles.budget_tile_unit with method C (unit kind 'tiles-budget-c')."""
    from chim import budget_tiles as B
    return run_c(task, B.budget_tile_unit)


def budget_tile_unit_union_c(task):
    """chim.union_bsp2.budget_tile_unit_union with method C (unit kind 'tiles-budget-union-c')."""
    from chim import union_bsp2 as U
    return run_c(task, U.budget_tile_unit_union)


def take_figures(result):
    """(RESULT without the method's figures, the figures or None): what the converter gets and what is reported."""
    if isinstance(result, dict) and FIGURES_KEY in result:
        return {k: v for k, v in result.items() if k != FIGURES_KEY}, result[FIGURES_KEY]
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], list) and result[1] \
            and isinstance(result[1][0], dict) and FIGURES_KEY in result[1][0]:
        grain, tiles = result
        first = {k: v for k, v in tiles[0].items() if k != FIGURES_KEY}
        return (grain, [first, *tiles[1:]]), tiles[0][FIGURES_KEY]
    return result, None
