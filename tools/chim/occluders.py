# SPDX-License-Identifier: GPL-3.0-only
"""Occluders from a model's closed render mesh (buildings with hollow collision shells).

The visibility rows (chim.visibility) block sight lines with space that is
surely solid. Solid collision pieces are convex and give that directly; a
building with a hollow collision shell (thin wall prisms, kept open so its
underpasses stay walkable) does not, yet its walls hide what is behind them.
Here the building's render mesh decides what is inside it: a point is enclosed
when rays in the four horizontal directions and straight up all meet the mesh
(an open-bottomed house sitting on the ground still encloses its rooms; an
awning, an arch or a courtyard open to the sky does not). The enclosed space
is sampled on an 8-unit voxel grid in the model frame and eroded, so a whole
16-unit visibility cell whose centre falls on a remaining voxel lies inside
(CHIM-PVS-HOLLOW-33).
"""
import math

import numpy as np

VOXEL = 8.0
ERODE_XY = 3        # voxels: a 16-unit cell (half diagonal 11.3) around any point of a kept voxel stays inside
ERODE_Z = 1


def triangles(polys):
    """Fan triangles (n, 3, 3) of convex planar polygons."""
    out = []
    for q in polys:
        q = np.asarray(q, float)
        for k in range(1, len(q) - 1):
            out.append((q[0], q[k], q[k + 1]))
    return np.array(out, float).reshape(-1, 3, 3)


def axis_hits(tris, axis, a_coords, b_coords):
    """Hit coordinates along `axis` of lines parallel to it, one line per (a, b) on the other two axes.

    Returns a list (one per line) of sorted hit coordinates (barycentric test in the
    plane of the other two axes; lines through an edge count once per triangle)."""
    o = [k for k in range(3) if k != axis]
    P = tris[:, :, o]                    # (t, 3, 2)
    v0, v1, v2 = P[:, 0], P[:, 1], P[:, 2]
    d = (v1[:, 0] - v0[:, 0]) * (v2[:, 1] - v0[:, 1]) - (v2[:, 0] - v0[:, 0]) * (v1[:, 1] - v0[:, 1])
    keep = np.abs(d) > 1e-9
    tris, v0, v1, v2, d = tris[keep], v0[keep], v1[keep], v2[keep], d[keep]
    pts = np.column_stack([a_coords, b_coords])            # (n, 2)
    out = []
    step = max(1, 200000 // max(1, len(tris)))
    for s in range(0, len(pts), step):
        p = pts[s:s + step, None, :]                       # (m, 1, 2)
        w1 = ((p[..., 0] - v0[:, 0]) * (v2[:, 1] - v0[:, 1]) - (v2[:, 0] - v0[:, 0]) * (p[..., 1] - v0[:, 1])) / d
        w2 = ((v1[:, 0] - v0[:, 0]) * (p[..., 1] - v0[:, 1]) - (p[..., 0] - v0[:, 0]) * (v1[:, 1] - v0[:, 1])) / d
        w0 = 1 - w1 - w2
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        coord = w0 * tris[:, 0, axis] + w1 * tris[:, 1, axis] + w2 * tris[:, 2, axis]
        for row_in, row_c in zip(inside, coord):
            out.append(np.sort(row_c[row_in]))
    return out


def enclosed_grid(polys, voxel=VOXEL):
    """Voxel centres of the model's bounding box that the render mesh encloses.

    Returns (origin of voxel (0, 0, 0)'s centre, voxel size, bool array [x, y, z])."""
    tris = triangles(polys)
    if not len(tris):
        return (0.0, 0.0, 0.0), voxel, np.zeros((0, 0, 0), bool)
    lo, hi = tris.reshape(-1, 3).min(0), tris.reshape(-1, 3).max(0)
    # sample positions are offset from round numbers so lines rarely pass exactly through edges
    xs = np.arange(lo[0] + voxel / 2 + 0.0137, hi[0], voxel)
    ys = np.arange(lo[1] + voxel / 2 + 0.0211, hi[1], voxel)
    zs = np.arange(lo[2] + voxel / 2 + 0.0173, hi[2], voxel)
    grid = np.zeros((len(xs), len(ys), len(zs)), bool)
    if not grid.size:
        return (float(lo[0]), float(lo[1]), float(lo[2])), voxel, grid
    Y, Z = np.meshgrid(ys, zs, indexing='ij')
    xhits = axis_hits(tris, 0, Y.ravel(), Z.ravel())       # lines along x, one per (y, z)
    X, Z2 = np.meshgrid(xs, zs, indexing='ij')
    yhits = axis_hits(tris, 1, X.ravel(), Z2.ravel())      # lines along y, one per (x, z)
    X2, Y2 = np.meshgrid(xs, ys, indexing='ij')
    zhits = axis_hits(tris, 2, X2.ravel(), Y2.ravel())     # lines along z, one per (x, y)
    px = np.zeros(grid.shape, bool)
    nx_ = np.zeros(grid.shape, bool)
    for k, h in enumerate(xhits):
        j, m = divmod(k, len(zs))
        if len(h):
            px[:, j, m] = xs < h[-1]
            nx_[:, j, m] = xs > h[0]
    py = np.zeros(grid.shape, bool)
    ny_ = np.zeros(grid.shape, bool)
    for k, h in enumerate(yhits):
        i, m = divmod(k, len(zs))
        if len(h):
            py[i, :, m] = ys < h[-1]
            ny_[i, :, m] = ys > h[0]
    up = np.zeros(grid.shape, bool)
    for k, h in enumerate(zhits):
        i, j = divmod(k, len(ys))
        if len(h):
            up[i, j, :] = zs < h[-1]
    grid = px & nx_ & py & ny_ & up
    return (float(xs[0]), float(ys[0]), float(zs[0])), voxel, grid


def erode(grid, rxy=ERODE_XY, rz=ERODE_Z):
    """Keep voxels whose neighbours within rxy (x, y, Chebyshev) and rz (z) are all enclosed."""
    if not grid.size:
        return grid
    g = grid.copy()
    for axis, r in ((0, rxy), (1, rxy), (2, rz)):
        out = g.copy()
        for k in range(1, r + 1):
            out[tuple(slice(k, None) if a == axis else slice(None) for a in range(3))] &= \
                g[tuple(slice(None, -k) if a == axis else slice(None) for a in range(3))]
            out[tuple(slice(None, -k) if a == axis else slice(None) for a in range(3))] &= \
                g[tuple(slice(k, None) if a == axis else slice(None) for a in range(3))]
            # voxels near the grid edge have outside neighbours
            edge = [slice(None)] * 3
            edge[axis] = slice(0, k)
            out[tuple(edge)] = False
            edge[axis] = slice(g.shape[axis] - k, None)
            out[tuple(edge)] = False
        g = out
    return g


def solid_columns(polys, voxel=VOXEL):
    """The occluder of one model: {'origin', 'voxel', 'shape', 'bits'} of the eroded enclosed grid
    (bits packed, model frame), or None when nothing remains."""
    origin, voxel, grid = enclosed_grid(polys, voxel)
    grid = erode(grid)
    if not grid.any():
        return None
    return {'origin': origin, 'voxel': voxel, 'shape': list(grid.shape),
            'bits': np.packbits(grid.ravel()).tobytes()}


def unpack(occ):
    n = int(np.prod(occ['shape']))
    return np.unpackbits(np.frombuffer(occ['bits'], np.uint8))[:n].astype(bool).reshape(occ['shape'])


def column_runs(grid):
    """{(i, j): [(k0, k1), ...]} runs of enclosed voxels per column (inclusive)."""
    out = {}
    for i, j in zip(*np.nonzero(grid.any(axis=2))):
        col = grid[i, j]
        runs, k = [], 0
        while k < len(col):
            if col[k]:
                s = k
                while k + 1 < len(col) and col[k + 1]:
                    k += 1
                runs.append((s, k))
            k += 1
        out[(int(i), int(j))] = runs
    return out


def place_columns(occ, origin, yaw, cell, low, nx, ny):
    """Frame cells (cell units) whose centre falls on a kept voxel of a placed occluder.

    Yields (i, j, z0, z1): cell index and the solid interval (world z) of the longest run."""
    grid = unpack(occ)
    runs = column_runs(grid)
    if not runs:
        return
    ox, oy, oz = occ['origin']
    v = occ['voxel']
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    # bounds of the placed grid
    corners = np.array([[ox - v / 2 + a * (grid.shape[0] * v), oy - v / 2 + b * (grid.shape[1] * v)]
                        for a in (0, 1) for b in (0, 1)])
    wx = corners[:, 0] * c - corners[:, 1] * s + origin[0]
    wy = corners[:, 0] * s + corners[:, 1] * c + origin[1]
    i0 = max(0, int(math.floor((wx.min() - low[0]) / cell)))
    i1 = min(nx, int(math.ceil((wx.max() - low[0]) / cell)))
    j0 = max(0, int(math.floor((wy.min() - low[1]) / cell)))
    j1 = min(ny, int(math.ceil((wy.max() - low[1]) / cell)))
    for i in range(i0, i1):
        for j in range(j0, j1):
            cx = low[0] + (i + 0.5) * cell - origin[0]
            cy = low[1] + (j + 0.5) * cell - origin[1]
            mx, my = cx * c + cy * s, -cx * s + cy * c        # into the model frame (inverse yaw)
            gi = int(math.floor((mx - ox) / v + 0.5))
            gj = int(math.floor((my - oy) / v + 0.5))
            r = runs.get((gi, gj))
            if not r:
                continue
            k0, k1 = max(r, key=lambda kk: kk[1] - kk[0])
            yield i, j, oz + k0 * v + origin[2], oz + k1 * v + origin[2]
