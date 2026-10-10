# SPDX-License-Identifier: GPL-3.0-only
"""Routed standing hulls: a placed model's collision as short chains behind axial clipnodes.

The converters write a model's standing hull (Quake hull 1) as one chain of
its convex pieces: outside a piece's planes goes on to the next piece, inside
all of one piece's planes is solid. A trace walks the chain piece by piece,
so a model of thousands of pieces costs thousands of node visits per test
(CHIM-HULL-CHAIN-COST-33, INTERIOR-HULL-CHAIN-33: the Arena Pit's main mesh is
one chain of 36,545 clipnodes).

The routed hull classifies every point exactly as that chain does, with short
chains: axial clipnodes at the expanded pieces' xy edges split the model's
region until a part meets at most `leaf_pieces` pieces (or no cut helps), and
each part holds the chain of the pieces that reach it. Models are also cut in z
(MODEL_AXES): a bowl of stacked tiers, a ship's decks or a tower's floors have
pieces whose xy boxes span the whole model, which xy cuts alone copy into
almost every part (the Arena Pit, COLLISION-HULL-CHAINS-33). Chunk terrain
keeps xy cuts (TERRAIN_AXES). When the finest routing does not fit the
clipnode budget, coarser parts are tried (LEAF_STEPS); the caller keeps the
chain when none fits.

Shared by the CHIM builder (chim.models.BrushLumps) and the legacy converter
(prepare_mesh_bsp.collider), so both paths use one implementation. The chain
stays selectable everywhere: AMIWIND_MODEL_HULL (mesh_geometry_env, builder
option --model-hull) is auto (routed above ROUTE_PIECES pieces), chain or
routed.
"""
import struct

HULL_LEAF_PIECES = 8          # pieces chained per part at the finest routing
ROUTE_PIECES = 16             # auto: models with more convex pieces than this are routed (legacy maps)
# CHIM: every byte of a model's hull is in each ring that holds it, and routing adds one clipnode per cut;
# auto routes only district-size models there (Vivec canton bodies, the Arena), whose chains cost the most
# per trace. House-size models keep the chain: Balmora's south-west ring has 2,528 B of headroom with chains
# and goes 1,920 B over when its 17-60-piece houses are routed (BUILD-CHIM-HULL-RING-33).
CHIM_ROUTE_PIECES = 256
# ONE rule for the router and the hull audits (CHIMport's cell audit, hull_chain_audit): a standing hull
# whose longest chain is deeper than CHAIN_DEPTH_LIMIT clipnodes is routed on CHIM (auto) and reported by
# the audits. Measured cost (a 68k bench of the engine's same-side descent, FS-UAE cycle-exact
# 68040): 1.36 us per clipnode visit with general planes at 49.7 MHz (the slow preset), 2.72 us at 24.8 MHz
# (the benchmark profile); a trace near a model walks its chain once. 256 clipnodes = 0.35 ms per trace on
# the slow preset, about 2.8 ms for a player frame's ~8 movement traces (6 % of a 20 fps frame).
CHAIN_DEPTH_LIMIT = 256
CHAIN_DEPTH_VARIABLE = 'AMIWIND_CHIM_CHAIN_DEPTH'     # measurement override of the limit (a positive integer)
US_PER_VISIT = {'slow-preset-49.7MHz': 1.36, 'benchmark-24.8MHz': 2.72}


KEEP_CHAIN_VARIABLE = 'AMIWIND_CHIM_KEEP_CHAIN'   # meshes whose CHIM hull stays the chain (the heap fallback)


def mesh_stem(source):
    """A mesh's key in the keep-chain list: its path under meshes/, lower case, without .nif."""
    stem = source.replace(chr(92), '/')
    stem = stem[len('meshes/'):] if stem.lower().startswith('meshes/') else stem
    stem = stem[:-4] if stem.lower().endswith('.nif') else stem
    return stem.lower()


def keep_chain_set():
    """The meshes the CHIM heap fallback keeps as chains (chim_build: a ring that does not fit with their
    routed hulls), from AMIWIND_CHIM_KEEP_CHAIN (comma-separated mesh stems)."""
    import os
    return {v.strip().lower() for v in os.environ.get(KEEP_CHAIN_VARIABLE, '').split(',') if v.strip()}


def chain_depth_limit():
    """CHAIN_DEPTH_LIMIT, or the measurement override in AMIWIND_CHIM_CHAIN_DEPTH."""
    import os
    value = os.environ.get(CHAIN_DEPTH_VARIABLE)
    if not value:
        return CHAIN_DEPTH_LIMIT
    if not value.isdigit() or int(value) < 1:
        raise ValueError('%s must be a positive integer, not %r' % (CHAIN_DEPTH_VARIABLE, value))
    return int(value)


def trace_cost_us(depth, profile='slow-preset-49.7MHz'):
    """Microseconds one trace spends walking a chain `depth` clipnodes deep (US_PER_VISIT)."""
    return depth * US_PER_VISIT[profile]
LEAF_STEPS = (HULL_LEAF_PIECES, 4 * HULL_LEAF_PIECES, 16 * HULL_LEAF_PIECES)
TERRAIN_AXES = (0, 1)         # chunk terrain: xy cuts (its pieces are columns of ground)
MODEL_AXES = (0, 1, 2)        # placed models: x, y and z cuts
CLIPNODE_LIMIT = 65520        # clipnode indices are 16-bit, the top values are contents


MODES = ('auto', 'chain', 'routed', 'balanced', 'compiled')


def wants_route(piece_count, mode, compiled=False, threshold=ROUTE_PIECES):
    """Whether a model's standing hull is routed: never when it is compiled (qbsp union), else by
    mode (MODES): 'chain' never, 'routed' and 'balanced' always, 'auto' above ROUTE_PIECES pieces."""
    if mode not in MODES:
        raise ValueError('Unknown model hull: %s' % mode)
    if compiled or not piece_count or mode == 'chain':
        return False
    if mode == 'compiled':
        return piece_count > threshold          # when qbsp cannot compile it, the model is routed
    return mode in ('routed', 'balanced') or piece_count > threshold


def routing(mode, shared_budget=False):
    """routed_standing's method and axes for a model hull mode: auto and routed use the nested routing in
    x, y and z (COLLISION-HULL-CHAINS-33); balanced is the earlier routing (parts by piece counts, xy cuts,
    leaf steps LEAF_STEPS), kept selectable. shared_budget: the model's clipnodes share one budget with the
    rest of a map (the legacy converter's region and interior maps): the nested routing then copies no
    pieces, so a model never takes more than its chain plus one clipnode per cut and the models after it
    still fit (measured: copies took Seyda Neen's scene map from 57,181 clipnodes past 65,520). A CHIM
    model is its own brush image with its own budget and keeps the copies."""
    if mode == 'balanced':
        return {'method': 'balanced', 'axes': TERRAIN_AXES}
    if shared_budget:
        return {'method': 'nested', 'axes': MODEL_AXES, 'steps': (0.0,)}
    return {'method': 'nested', 'axes': MODEL_AXES}


def expand(pieces, exact):
    """(planes, boxes) of the pieces expanded by the standing box (prepare_mesh_bsp.standing_planes):
    boxes (x0, y0, x1, y1, z0, z1), the xy extent first as the terrain routing reads it.
    exact: True/False for every piece, or the set of piece positions with exact bevels."""
    import numpy as np
    from player_hull import MINS, MAXS
    from prepare_mesh_bsp import standing_planes
    eqs, boxes = [], []
    for k, (points, hull, ids, error) in enumerate(pieces):
        point_eq = np.unique(np.round(hull.equations, 5), axis=0)
        eqs.append(standing_planes(points, point_eq, exact if isinstance(exact, bool) else k in exact))
        # the expanded piece's xy extent (standing_planes keeps the axial bounding planes)
        lo, hi = points.min(axis=0), points.max(axis=0)
        boxes.append((lo[0] + MINS[0], lo[1] + MINS[1], hi[0] + MAXS[0], hi[1] + MAXS[1],
                      lo[2] + MINS[2], hi[2] + MAXS[2]))
    return eqs, boxes


def region_of(pieces):
    """The region a model's routed hull covers, (x0, y0, x1, y1, z0, z1): its pieces expanded by the
    standing box, plus 1."""
    import numpy as np
    from player_hull import MINS, MAXS
    pts = np.vstack([p for p, *_ in pieces])
    return (float(pts[:, 0].min() + MINS[0] - 1), float(pts[:, 1].min() + MINS[1] - 1),
            float(pts[:, 0].max() + MAXS[0] + 1), float(pts[:, 1].max() + MAXS[1] + 1),
            float(pts[:, 2].min() + MINS[2] - 1), float(pts[:, 2].max() + MAXS[2] + 1))


def route(clip, plane, eqs, boxes, region, leaf_pieces=HULL_LEAF_PIECES, chains=None, axes=TERRAIN_AXES):
    """Append the routed hull's clipnodes to `clip` (the clipnode lump, bytearray); plane(n, d) gives a
    plane index. region: (x0, y0, x1, y1) or (x0, y0, x1, y1, z0, z1); axes: the cut axes (0 x, 1 y,
    2 z; z needs a 6-value region and boxes). Returns the root (a clipnode index, or -1 when nothing is
    solid). chains: a list that gets each part's chain length.

    A cut is chosen by the pieces on each side: the smallest larger side, then the smallest total,
    then the axis and the value (deterministic). Pieces are counted with sorted box edges, so a node
    costs O(n log n) per axis, not O(n^2)."""
    import numpy as np
    # region and boxes as (lo per axis, hi per axis); a 4-value region is unbounded in z
    reg = list(region) + ([-np.inf, np.inf] if len(region) == 4 else [])
    lo_of = np.array([[b[0], b[1], b[4] if len(b) > 4 else -np.inf] for b in boxes], float)
    hi_of = np.array([[b[2], b[3], b[5] if len(b) > 4 else np.inf] for b in boxes], float)
    if 2 in axes and (len(region) == 4 or any(len(b) < 6 for b in boxes)):
        raise ValueError('z cuts need 6-value regions and boxes')

    def chain(idx):
        if not len(idx):
            return -1                                   # CONTENTS_EMPTY
        start = len(clip) // 8
        total = sum(len(eqs[k]) for k in idx)
        if start + total >= CLIPNODE_LIMIT:
            raise ValueError('Clipnode budget exceeded')
        at = start
        if chains is not None:
            chains.append(len(idx))
        for n, k in enumerate(idx):
            eq = eqs[k]
            nxt = at + len(eq) if n + 1 < len(idx) else -1
            for j, e in enumerate(eq):
                pi = plane(e[:3], -e[3])
                inside = at + j + 1 if j + 1 < len(eq) else -2
                clip.extend(struct.pack('<iHH', pi, nxt & 65535, inside & 65535))
            at += len(eq)
        return start

    def build(r, idx):
        # strict: a point on a piece's boundary plane is outside it (d >= 0 goes to the front)
        idx = idx[np.all(lo_of[idx] < r[1], axis=1) & np.all(hi_of[idx] > r[0], axis=1)]
        n = len(idx)
        if n <= leaf_pieces:
            return chain([int(k) for k in idx])
        best = None
        for axis in axes:
            los, his = np.sort(lo_of[idx, axis]), np.sort(hi_of[idx, axis])
            cuts = np.unique(np.concatenate((los, his)))
            cuts = cuts[(cuts > r[0][axis]) & (cuts < r[1][axis])]
            if not len(cuts):
                continue
            n_lo = np.searchsorted(los, cuts, side='left')          # pieces with lo < cut reach below it
            n_hi = n - np.searchsorted(his, cuts, side='right')     # pieces with hi > cut reach above it
            helps = np.minimum(n_lo, n_hi) < n
            if not helps.any():
                continue
            big = np.where(helps, np.maximum(n_lo, n_hi), np.iinfo(np.int64).max)
            tot = n_lo + n_hi
            # (larger side, total, axis, cut): the first minimum in cut order is the smallest cut
            k = np.lexsort((cuts, tot, big))[0]
            score = (int(big[k]), int(tot[k]), axis, float(cuts[k]))
            if best is None or score < best[0]:
                best = (score, axis, float(cuts[k]))
        if best is None:
            return chain([int(k) for k in idx])
        _, axis, c = best
        lo_r, hi_r = [list(r[0]), list(r[1])], [list(r[0]), list(r[1])]
        lo_r[1][axis] = c
        hi_r[0][axis] = c
        me = len(clip) // 8
        normal = np.zeros(3)
        normal[axis] = 1.0
        pi = plane(normal, c)
        clip.extend(struct.pack('<iHH', pi, 0, 0))     # children patched below
        front = build(hi_r, idx)
        back = build(lo_r, idx)
        if max(me, front, back) >= CLIPNODE_LIMIT:
            raise ValueError('Clipnode budget exceeded')
        struct.pack_into('<iHH', clip, 8 * me, pi, front & 65535, back & 65535)
        return me
    r0 = [[float(reg[0]), float(reg[1]), float(reg[4])], [float(reg[2]), float(reg[3]), float(reg[5])]]
    import sys
    limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(limit, 4 * len(eqs) + 1000))    # a cut may shed a single piece
    try:
        return build(r0, np.arange(len(eqs)))
    finally:
        sys.setrecursionlimit(limit)


# Nested routing (route_nested, the default for placed models): at each axial cut, the pieces that straddle
# it are chained at that node (outside all of them goes on to the cut), and only the pieces wholly on one
# side go down. Every piece is written once, so the hull is never larger than the chain plus one clipnode
# per cut and always fits where the chain fits. A cut is taken when its expected cost (the straddlers'
# planes, plus each side's planes times that side's share of the part, plus TRAVERSAL planes for the cut)
# is below the part's own chain. Straddlers are copied into both sides instead (so cuts further down can
# separate them) while a copy allowance lasts: NESTED_STEPS, in clipnodes per clipnode of the chain; the
# last step (0) copies nothing and fits wherever the chain fits.
TRAVERSAL = 1.0
NESTED_STEPS = (1.0, 0.25, 0.0)
HULL_METHODS = ('nested', 'balanced')


def route_nested(clip, plane, eqs, boxes, region, copies=0.0, chains=None, axes=MODEL_AXES, traversal=TRAVERSAL):
    """Routed hull with straddling pieces chained at their cut, or copied into both sides while the copy
    allowance (copies x the chain's clipnodes) lasts (see above); route()'s output contract."""
    import numpy as np
    reg = list(region) + ([-np.inf, np.inf] if len(region) == 4 else [])
    lo_of = np.array([[b[0], b[1], b[4] if len(b) > 4 else -np.inf] for b in boxes], float)
    hi_of = np.array([[b[2], b[3], b[5] if len(b) > 4 else np.inf] for b in boxes], float)
    weight = np.array([len(e) for e in eqs], float)
    if 2 in axes and (len(region) == 4 or any(len(b) < 6 for b in boxes)):
        raise ValueError('z cuts need 6-value regions and boxes')
    allowance = [copies * float(weight.sum())]

    def chain(idx, after=-1):
        """Chain of pieces: inside one is solid, outside all goes to `after` (a clipnode or contents)."""
        if not len(idx):
            return after
        start = len(clip) // 8
        if start + sum(len(eqs[k]) for k in idx) >= CLIPNODE_LIMIT:
            raise ValueError('Clipnode budget exceeded')
        at = start
        if chains is not None:
            chains.append(len(idx))
        for n, k in enumerate(idx):
            eq = eqs[k]
            nxt = at + len(eq) if n + 1 < len(idx) else after
            for j, e in enumerate(eq):
                pi = plane(e[:3], -e[3])
                inside = at + j + 1 if j + 1 < len(eq) else -2
                clip.extend(struct.pack('<iHH', pi, nxt & 65535, inside & 65535))
            at += len(eq)
        return start

    def build(r, idx):
        n = len(idx)
        leaf_cost = float(weight[idx].sum())
        best = None
        extent = [r[1][a] - r[0][a] for a in range(3)]
        if n > 1:
            for axis in axes:
                if not np.isfinite(extent[axis]) or extent[axis] <= 0:
                    continue
                lo_k, hi_k = lo_of[idx, axis], hi_of[idx, axis]
                order_lo, order_hi = np.argsort(lo_k, kind='stable'), np.argsort(hi_k, kind='stable')
                los, his = lo_k[order_lo], hi_k[order_hi]
                wlo = np.concatenate(([0.0], np.cumsum(weight[idx][order_lo])))
                whi = np.concatenate(([0.0], np.cumsum(weight[idx][order_hi])))
                cuts = np.unique(np.concatenate((los, his)))
                cuts = cuts[(cuts > r[0][axis]) & (cuts < r[1][axis])]
                if not len(cuts):
                    continue
                below = whi[np.searchsorted(his, cuts, side='right')]               # pieces with hi <= cut
                above = wlo[-1] - wlo[np.searchsorted(los, cuts, side='left')]       # pieces with lo >= cut
                straddle = leaf_cost - below - above
                share = (cuts - r[0][axis]) / extent[axis]
                cost = traversal + straddle + share * below + (1 - share) * above
                useful = (below + above > 0) & (cost < leaf_cost)
                if not useful.any():
                    continue
                cost = np.where(useful, cost, np.inf)
                k = np.lexsort((cuts, cost))[0]
                score = (float(cost[k]), axis, float(cuts[k]))
                if best is None or score < best[0]:
                    best = (score, axis, float(cuts[k]))
        if best is None:
            return chain([int(k) for k in idx])
        _, axis, c = best
        lo_k, hi_k = lo_of[idx, axis], hi_of[idx, axis]
        low, high = idx[hi_k <= c], idx[lo_k >= c]
        middle = idx[(lo_k < c) & (hi_k > c)]
        copy = float(weight[middle].sum())
        if len(middle) and len(low) and len(high) and copy <= allowance[0]:
            # both sides shrink, so the recursion ends; the straddlers go down both ways
            allowance[0] -= copy
            low, high, middle = idx[lo_k < c], idx[hi_k > c], middle[:0]
        lo_r, hi_r = [list(r[0]), list(r[1])], [list(r[0]), list(r[1])]
        lo_r[1][axis] = c
        hi_r[0][axis] = c
        # The straddlers' chain comes first and leads to the cut written right after it, so a part's
        # root is its lowest clipnode: Quake rejects a node below a model's head node
        # (SV_RecursiveHullCheck "bad node number": hull firstclipnode = the head; ROUTED-HULL-NODE-ORDER-33).
        mid = [int(k) for k in middle]
        start = len(clip) // 8
        me = start + sum(len(eqs[k]) for k in mid)
        head = chain(mid, after=me)
        if len(clip) // 8 != me:
            raise ValueError('Routed hull layout: the cut must follow its straddlers')
        normal = np.zeros(3)
        normal[axis] = 1.0
        pi = plane(normal, c)
        clip.extend(struct.pack('<iHH', pi, 0, 0))     # children patched below
        front = build(hi_r, high) if len(high) else -1
        back = build(lo_r, low) if len(low) else -1
        if max(me, front, back) >= CLIPNODE_LIMIT:
            raise ValueError('Clipnode budget exceeded')
        struct.pack_into('<iHH', clip, 8 * me, pi, front & 65535, back & 65535)
        return head if mid else me
    r0 = [[float(reg[0]), float(reg[1]), float(reg[4])], [float(reg[2]), float(reg[3]), float(reg[5])]]
    import sys
    limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(limit, 4 * len(eqs) + 1000))
    try:
        return build(r0, np.arange(len(eqs)))
    finally:
        sys.setrecursionlimit(limit)


def routed_standing(lumps, plane, planes, pieces, exact, region=None, steps=None, axes=MODEL_AXES, method='nested'):
    """The routed standing hull of a model, appended to lumps[9] (planes to lumps[1] through plane(n, d),
    whose cache is the dict `planes`: key -> index). Tries each leaf size of `steps`; a try that runs out
    of clipnodes is undone (clipnodes, planes and their cache entries) before the next. Returns
    (root, step used, chain lengths); a ValueError when no step fits (the caller keeps the chain).
    method: 'nested' (straddlers copied while an allowance lasts, then chained at their cut; steps are
    copy allowances, NESTED_STEPS, the last writing every piece once) or 'balanced' (parts
    by piece counts, spanning pieces copied into every part they reach; steps are leaf sizes,
    LEAF_STEPS)."""
    if method not in HULL_METHODS:
        raise ValueError('Unknown routing method: %s' % method)
    steps = steps if steps is not None else (NESTED_STEPS if method == 'nested' else LEAF_STEPS)
    eqs, boxes = expand(pieces, exact)
    region = region_of(pieces) if region is None else region
    clip_len, plane_len = len(lumps[9]), len(lumps[1])
    for leaf in steps:
        chains = []
        try:
            if method == 'nested':
                return route_nested(lumps[9], plane, eqs, boxes, region, leaf, chains, axes), leaf, chains
            return route(lumps[9], plane, eqs, boxes, region, leaf, chains, axes), leaf, chains
        except ValueError as error:
            if 'budget' not in str(error):
                raise
            del lumps[9][clip_len:]
            del lumps[1][plane_len:]
            for key in [k for k, v in planes.items() if v >= plane_len // 20]:
                del planes[key]
    raise ValueError('Clipnode budget exceeded at every routing step %s' % (tuple(steps),))
