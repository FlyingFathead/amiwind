# SPDX-License-Identifier: GPL-3.0-only
"""Large-model cut: a placed model wider than a chunk becomes one model per chunk it covers.

A CHIM chunk keeps every model a placement in it uses resident whole. A Vivec canton body is wider than
the whole active ring (about 1,750 x 1,500 local units, 1.7-2.5 MB decoded; CHIM-ARENA-MEMORY-33), so the
ring holds every canton it touches whole. The cut stores such a placement as pieces instead: the faces
whose part lies in a chunk's column, clipped at the chunk lines, and the convex collision pieces clipped
by the column's four half-spaces. Each piece is its own model, placed at its chunk's centre without a
turn (the placement's yaw is applied to the geometry and the texture axes), so the chunk holding a
piece's origin owns it as for any placement, and only the pieces in the ring are resident.

The solid is unchanged: the standing box's expansion of a union of convex pieces is the union of their
expansions, so clipping the pieces before expanding them keeps every point's contents; the faces are the
same polygons cut into parts. Quake mechanism: brush models placed as statics (func_wall / static
entities), the same as every CHIM placement.
"""
import math

import numpy as np

CUT_STATUS = 'large-model cut'
# A piece's placement number keeps its source reference in the low bits (Morrowind reference numbers stay
# far below 2^24) and its piece index above them, so every placement number stays unique (chim.world) and
# every check that compares with the source maps it back (source_ref).
PIECE_SHIFT = 24
SOURCE_MASK = (1 << PIECE_SHIFT) - 1


def piece_ref(ref, index):
    """The placement number of piece index (1..127) of source reference ref."""
    if not 0 <= ref <= SOURCE_MASK or not 1 <= index <= 127:
        raise ValueError('Cannot number piece %d of reference %d' % (index, ref))
    return ref | (index << PIECE_SHIFT)


def source_ref(ref):
    """The source reference of a placement number (itself for a placement that is not a cut piece)."""
    return int(ref) & SOURCE_MASK


def rotation(yaw):
    """The engine's turn for a placement's yaw (world = origin + x*forward - y*right + z*up)."""
    from world_chunk_estimate import angle_vectors
    f, r, u = angle_vectors((0.0, yaw, 0.0))
    return np.array([f, [-v for v in r], u], float).T        # columns: model x, y, z in the frame


def clip_polygon(points, axis, value, keep_below):
    """Sutherland-Hodgman: the part of a planar polygon with coordinate axis < value (or >= value)."""
    out = []
    n = len(points)
    for i in range(n):
        a, b = points[i], points[(i + 1) % n]
        ina = a[axis] < value if keep_below else a[axis] >= value
        inb = b[axis] < value if keep_below else b[axis] >= value
        if ina:
            out.append(a)
        if ina != inb:
            t = (value - a[axis]) / (b[axis] - a[axis])
            out.append(a + t * (b - a))
    return out


def polygon_in_column(points, x0, y0, x1, y1):
    for axis, lo, hi in ((0, x0, x1), (1, y0, y1)):
        points = clip_polygon(points, axis, lo, False)
        if len(points) < 3:
            return []
        points = clip_polygon(points, axis, hi, True)
        if len(points) < 3:
            return []
    return points


def area(points):
    p = np.array(points)
    return 0.5 * np.linalg.norm(sum(np.cross(p[i], p[(i + 1) % len(p)]) for i in range(len(p))))


def clip_piece(points, x0, y0, x1, y1):
    """The part of a convex point set's hull inside the column x0..x1, y0..y1 (points of the clipped hull),
    or None when nothing with volume is left."""
    from scipy.optimize import linprog
    from scipy.spatial import ConvexHull, HalfspaceIntersection
    lo, hi = points.min(axis=0), points.max(axis=0)
    if lo[0] >= x0 and hi[0] <= x1 and lo[1] >= y0 and hi[1] <= y1:
        return points
    if hi[0] <= x0 or lo[0] >= x1 or hi[1] <= y0 or lo[1] >= y1:
        return None
    eq = ConvexHull(points).equations                           # n.x + d <= 0 inside
    box = np.array([[-1, 0, 0, x0], [1, 0, 0, -x1], [0, -1, 0, y0], [0, 1, 0, -y1]], float)
    hs = np.vstack([eq, box])
    # interior point: the centre of the largest ball inside (Chebyshev centre)
    norm = np.linalg.norm(hs[:, :3], axis=1)
    res = linprog(np.r_[0, 0, 0, -1], A_ub=np.c_[hs[:, :3], norm], b_ub=-hs[:, 3],
                  bounds=[(None, None)] * 3 + [(0, None)], method='highs')
    if not res.success or res.x[3] < 1e-3:
        return None
    pts = HalfspaceIntersection(hs, res.x[:3]).intersections
    return np.unique(np.round(pts, 6), axis=0)


MODES = ('tiles', 'partition', 'clip')


def model_tiles(surfaces, parts, grain):
    """{(i, j): (surfaces, parts, tile centre)} of a model cut into grain-sized tiles in its own frame
    (mode 'tiles', the default): each face and convex piece goes whole to the tile holding its centre, and
    is moved so the tile centre is its origin. The tiles are shared by every placement of the model (stored
    once); a placement puts each tile at origin + turn(tile centre) with its own yaw."""
    pts = np.vstack([np.asarray(q, float) for q, *_ in surfaces] + [np.asarray(p, float) for p, *_ in parts])
    lo = pts.min(axis=0)
    out = {}

    def tile(points):
        c = (points.min(axis=0) + points.max(axis=0)) / 2
        return (int(math.floor((c[0] - lo[0]) / grain)), int(math.floor((c[1] - lo[1]) / grain)))

    def slot(t):
        if t not in out:
            out[t] = ([], [], np.array([lo[0] + (t[0] + 0.5) * grain, lo[1] + (t[1] + 0.5) * grain, 0.0]))
        return out[t]

    for srf in surfaces:
        q = np.asarray(srf[0], float)
        surfs, _, c = slot(tile(q))
        ax = np.asarray(srf[2], float)
        # s = q.ax + off becomes (q - c).ax + off + c.ax
        surfs.append((q - c, srf[1], ax, np.asarray(srf[3], float) + c @ ax) + tuple(srf[4:]))
    for points, hull, ids, error in parts:
        f = np.asarray(points, float)
        _, prts, c = slot(tile(f))
        prts.append((f - c, None, ids, error))
    return out


def tile_unit(task):
    """The tiles of one shared model variant as model images (a pool worker; see chim.units).

    task: variant_unit's task plus grain. Returns [{'tile', 'centre', 'lumps', 'texture_keys', 'lo', 'hi',
    'occluders', 'occluder_grid', 'materials'}] in tile order; the first tile carries a hollow shell's
    whole occluder grid."""
    from prepare_mesh_bsp import NO_EMISSIVE, _prepare_placement
    from chim.models import material_texture_key, model_image_lumps
    ref, model, centre, size = task['ref'], task['model'], task['centre'], task['texsize']
    surfaces, parts, _, _ = _prepare_placement((ref, task['data'], size, centre, None, False))
    keys = {}
    for srf in surfaces:
        keys[srf[4]] = ('model',) + material_texture_key(model, srf[4], size, NO_EMISSIVE, task.get('texture_shas'))
    tiles = model_tiles(surfaces, parts, task['grain'])
    out = []
    order = sorted(tiles)
    whole_grid = None
    if task['hollow'] and order:
        from chim.occluders import solid_columns
        first = tiles[order[0]][2]
        whole_grid = solid_columns([np.asarray(srf[0], float) - first for srf in surfaces])
    for n, t in enumerate(order):
        surfs, prts, c = tiles[t]
        allp = np.vstack([np.asarray(srf[0]) for srf in surfs] + [p for p, *_ in prts])
        lo, hi = allp.min(axis=0) - 1, allp.max(axis=0) + 1
        lumps, tkeys = model_image_lumps(surfs, prts, lo, hi, lambda m: keys[m], task['exact'], None, b'')
        out.append({'tile': list(t), 'centre': [float(v) for v in c], 'lumps': [bytes(x) for x in lumps],
                    'texture_keys': tkeys, 'lo': [float(v) for v in lo], 'hi': [float(v) for v in hi],
                    'occluders': [] if task['hollow'] else [p for p, *_ in prts],
                    'occluder_grid': whole_grid if n == 0 else None,
                    'materials': {k: m for m, k in keys.items() if k in tkeys}})
    return out


def cut_pieces(surfaces, parts, origin, yaw, low, grain, nx, ny, mode='partition'):
    """{(cx, cy): (surfaces, parts, piece origin)} of one placement cut by the chunk grid of its frame.

    surfaces / parts: _prepare_placement's model-frame faces (q, n, ax, off, material, ...) and convex
    pieces (points, hull, ids, error). Every piece is moved to the frame's orientation and to its own
    origin, the centre of its chunk at the placement's height.

    mode 'partition' (default): every face and every convex piece goes whole to the chunk holding its
    centre, so the polygons and the collision solid are exactly the model's (a piece's box may reach into
    the next chunk). Mode 'clip': faces are clipped at the chunk lines and convex pieces by the chunk's
    column, so a piece stays inside its chunk; clipping a sloped face leaves a smaller slope that the stair
    gate reads as a step, and clipped pieces need exact standing bevels (measured on the Arena canton)."""
    if mode not in MODES:
        raise ValueError('Unknown cut mode: %s' % mode)
    R = rotation(yaw)
    o = np.array(origin, float)
    out = {}

    def cell_range(lo_, hi_):
        i0 = max(0, int(math.floor((lo_[0] - low[0]) / grain)))
        i1 = min(nx - 1, int(math.floor((hi_[0] - low[0]) / grain)))
        j0 = max(0, int(math.floor((lo_[1] - low[1]) / grain)))
        j1 = min(ny - 1, int(math.floor((hi_[1] - low[1]) / grain)))
        return [(i, j) for i in range(i0, i1 + 1) for j in range(j0, j1 + 1)]

    def piece_origin(c):
        return np.array([low[0] + (c[0] + 0.5) * grain, low[1] + (c[1] + 0.5) * grain, o[2]])

    def slot(c):
        if c not in out:
            out[c] = ([], [], piece_origin(c))
        return out[c]

    def home(points):
        c = (points.min(axis=0) + points.max(axis=0)) / 2
        return (min(nx - 1, max(0, int(math.floor((c[0] - low[0]) / grain)))),
                min(ny - 1, max(0, int(math.floor((c[1] - low[1]) / grain)))))

    for s in surfaces:
        q, n, ax, off = s[0], s[1], s[2], s[3]
        f = np.asarray(q, float) @ R.T + o
        nf = R @ np.asarray(n, float)
        axf = R @ np.asarray(ax, float)                            # 3 x 2: s and t axes in the frame
        if mode == 'partition':
            surfs, _, po = slot(home(f))
            surfs.append((f - po, nf, axf, np.asarray(off, float) + (po - o) @ axf) + tuple(s[4:]))
            continue
        for c in cell_range(f.min(axis=0), f.max(axis=0)):
            x0, y0 = low[0] + c[0] * grain, low[1] + c[1] * grain
            # the outer chunks of the frame keep anything that reaches past the frame's edge
            bx0 = -1e9 if c[0] == 0 else x0
            by0 = -1e9 if c[1] == 0 else y0
            bx1 = 1e9 if c[0] == nx - 1 else x0 + grain
            by1 = 1e9 if c[1] == ny - 1 else y0 + grain
            poly = polygon_in_column([p for p in f], bx0, by0, bx1, by1)
            if len(poly) < 3 or area(poly) < 1e-6:
                continue
            surfs, _, po = slot(c)
            qn = np.array(poly) - po
            # s = q.ax + off in the model frame becomes q'.(R ax) + off + (po - o).(R ax)
            offn = np.asarray(off, float) + (po - o) @ axf
            surfs.append((qn, nf, axf, offn) + tuple(s[4:]))
    for points, hull, ids, error in parts:
        f = np.asarray(points, float) @ R.T + o
        if mode == 'partition':
            _, prts, po = slot(home(f))
            prts.append((f - po, None, ids, error, False))
            continue
        for c in cell_range(f.min(axis=0), f.max(axis=0)):
            x0, y0 = low[0] + c[0] * grain, low[1] + c[1] * grain
            bx0 = -1e9 if c[0] == 0 else x0
            by0 = -1e9 if c[1] == 0 else y0
            bx1 = 1e9 if c[0] == nx - 1 else x0 + grain
            by1 = 1e9 if c[1] == ny - 1 else y0 + grain
            clipped = clip_piece(f, bx0, by0, bx1, by1)
            if clipped is None or len(clipped) < 4:
                continue
            _, prts, po = slot(c)
            # a clipped piece has new edges along the chunk line: it needs exact standing bevels there
            # (an approximate expansion bulges at edges: CHIM-TERRAIN-HULL-BEVELS-33)
            prts.append((clipped - po, None, ids, error, clipped is not f))
    return {c: v for c, v in out.items() if v[0] or v[1]}


def cut_unit(task):
    """The pieces of one cut placement as model images (a pool worker; see chim.units).

    task: variant_unit's task plus origin, yaw (the placement) and low, grain, nx, ny (the frame's
    chunk grid). Returns [{'chunk', 'origin', 'lumps', 'texture_keys', 'lo', 'hi', 'occluders',
    'occluder_grid', 'materials'}] in chunk order."""
    from prepare_mesh_bsp import NO_EMISSIVE, _prepare_placement
    from chim.models import material_texture_key, model_image_lumps
    ref, model, centre, size = task['ref'], task['model'], task['centre'], task['texsize']
    surfaces, parts, _, _ = _prepare_placement((ref, task['data'], size, centre, None, False))
    keys = {}
    for s in surfaces:
        keys[s[4]] = ('model',) + material_texture_key(model, s[4], size, NO_EMISSIVE, task.get('texture_shas'))
    out = []
    pieces = cut_pieces(surfaces, parts, task['origin'], task['yaw'], task['low'], task['grain'],
                        task['nx'], task['ny'], task.get('cut_mode', 'partition'))
    whole_grid = None
    if task['hollow'] and pieces:
        # a hollow shell occludes through its closed render mesh (CHIM-PVS-HOLLOW-33); no single piece is
        # closed, so the first piece carries the whole placement's columns, in its own frame
        from chim.occluders import solid_columns
        first = pieces[sorted(pieces)[0]][2]
        R = rotation(task['yaw'])
        o = np.array(task['origin'], float)
        whole_grid = solid_columns([np.asarray(s[0], float) @ R.T + o - first for s in surfaces])
    for n, c in enumerate(sorted(pieces)):
        surfs, prts, po = pieces[c]
        exact = True if task['exact'] else {k for k, p in enumerate(prts) if p[4]}
        prts = [p[:4] for p in prts]
        pts = [np.asarray(s[0]) for s in surfs] + [p for p, *_ in prts]
        allp = np.vstack(pts)
        lo, hi = allp.min(axis=0) - 1, allp.max(axis=0) + 1
        lumps, tkeys = model_image_lumps(surfs, prts, lo, hi, lambda m: keys[m], exact, None, b'')
        occluder_grid = whole_grid if n == 0 else None
        out.append({'chunk': list(c), 'origin': [float(v) for v in po], 'lumps': [bytes(x) for x in lumps],
                    'texture_keys': tkeys, 'lo': [float(v) for v in lo], 'hi': [float(v) for v in hi],
                    'occluders': [] if task['hollow'] else [p for p, *_ in prts],
                    'occluder_grid': occluder_grid,
                    'materials': {k: m for m, k in keys.items() if k in tkeys}})
    return out
