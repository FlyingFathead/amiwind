# SPDX-License-Identifier: GPL-3.0-only
"""Irregular ground (format 0.5): the converter's own terrain triangles, per 128-unit tile.

Seyda Neen's ground is not a regular grid of tile corners: the scene stage
inserts shoreline samples into the 128-unit tiles
(prepare_world_regions.terrain_triangles) and lays a 32-unit patch at the port
(prepare_quake.town_ground_triangles). A TriangleGround holds those triangles
by tile, so the builder (chunk terrain), the validator (coverage, heights and
standing hull seams) and the visibility rows (sight lines over the ground)
read one surface. Every triangle lies inside one tile of the grid (its
centroid's tile); chunk edges lie on tile edges, so no triangle crosses a
chunk edge.

Light: plain Python and numpy, no converter imports.
"""
import math

import numpy as np

EPS = 1e-6


def tile_of(tri, step, low):
    cx = sum(p[0] for p in tri) / 3.0
    cy = sum(p[1] for p in tri) / 3.0
    return int(math.floor((cx - low[0]) / step)), int(math.floor((cy - low[1]) / step))


def _bary(tri, x, y):
    (ax, ay, _), (bx, by, _), (cx, cy, _) = tri
    den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    u = ((by - cy) * (x - cx) + (cx - bx) * (y - cy)) / den
    v = ((cy - ay) * (x - cx) + (ax - cx) * (y - cy)) / den
    return u, v, 1.0 - u - v


def clip_convex_xy(poly, x0, y0, x1, y1):
    """A 3-D convex polygon clipped in plan to a rectangle (Sutherland-Hodgman; z interpolated)."""
    pts = [tuple(float(v) for v in p) for p in poly]
    for axis, bound, sign in ((0, x0, 1.0), (0, x1, -1.0), (1, y0, 1.0), (1, y1, -1.0)):
        out = []
        for i in range(len(pts)):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            dp, dq = sign * (p[axis] - bound), sign * (q[axis] - bound)
            if dp >= 0:
                out.append(p)
            if (dp >= 0) != (dq >= 0):
                t = dp / (dp - dq)
                out.append(tuple(p[k] + (q[k] - p[k]) * t for k in range(3)))
        pts = out
        if not pts:
            return []
    return pts


class TriangleGround:
    """Ground triangles by tile: height at a point, highest ground over a rectangle.

    triangles: [(3 corner points (x, y, z) in frame-local units, material)]."""

    def __init__(self, triangles, step, low, size):
        self.step = float(step)
        self.low = (float(low[0]), float(low[1]))
        self.size = (int(size[0]), int(size[1]))          # tiles across, along
        self.tiles = {}
        for tri, material in triangles:
            t = tile_of(tri, step, low)
            if not (0 <= t[0] < self.size[0] and 0 <= t[1] < self.size[1]):
                raise ValueError('Ground triangle outside the tile grid: %s' % (tri,))
            self.tiles.setdefault(t, []).append(([tuple(float(v) for v in p) for p in tri], material))
        missing = self.size[0] * self.size[1] - len(self.tiles)
        if missing:
            raise ValueError('Ground has %d tiles without triangles' % missing)
        self._packed = None

    @classmethod
    def from_source(cls, source):
        """The ground of a source manifest section ('terrain_triangles': flat rows x0 y0 z0 x1 y1 z1 x2 y2 z2 m)."""
        rows = source['terrain_triangles']
        tris = [([r[0:3], r[3:6], r[6:9]], int(r[9])) for r in rows]
        return cls(tris, source['terrain_step'], source['terrain_low'], source['terrain_size'])

    def rows(self):
        """Manifest rows, tile by tile (y, then x), each tile's triangles in their given order."""
        out = []
        for j in range(self.size[1]):
            for i in range(self.size[0]):
                for tri, m in self.tiles[(i, j)]:
                    out.append([round(v, 6) for p in tri for v in p] + [int(m)])
        return out

    def tile_list(self, i, j):
        return self.tiles[(i, j)]

    def clamp_tile(self, x, y):
        i = min(self.size[0] - 1, max(0, int(math.floor((x - self.low[0]) / self.step))))
        j = min(self.size[1] - 1, max(0, int(math.floor((y - self.low[1]) / self.step))))
        return i, j

    def height(self, x, y, near=None):
        """Ground height at (x, y) (clamped to the grid): the triangle holding the point, from the
        tile holding `near` when given (a corner on a tile edge, read from its own tile)."""
        best, best_w = None, -1e9
        for tri, _ in self.tiles[self.clamp_tile(*(near or (x, y)))]:
            w = min(_bary(tri, x, y))
            if w > best_w:
                best, best_w = tri, w
        u, v, t = _bary(best, x, y)
        return u * best[0][2] + v * best[1][2] + t * best[2][2]

    def max_over(self, x0, y0, x1, y1):
        """Highest ground over a rectangle (clamped to the grid), exact: the maximum of the
        planar pieces of every triangle clipped to the rectangle."""
        hx, hy = self.low[0] + self.size[0] * self.step, self.low[1] + self.size[1] * self.step
        x0, x1 = max(self.low[0], x0), min(hx - EPS, x1)
        y0, y1 = max(self.low[1], y0), min(hy - EPS, y1)
        i0, j0 = self.clamp_tile(x0, y0)
        i1, j1 = self.clamp_tile(x1, y1)
        best = -1e30
        for j in range(j0, j1 + 1):
            for i in range(i0, i1 + 1):
                for tri, _ in self.tiles[(i, j)]:
                    for p in clip_convex_xy(tri, x0, y0, x1, y1):
                        best = max(best, p[2])
        return best

    # numpy form for the visibility rows (many points at once)
    def _pack(self):
        k = max(len(v) for v in self.tiles.values())
        tri = np.zeros((self.size[1], self.size[0], k, 3, 3))
        used = np.zeros((self.size[1], self.size[0], k), bool)
        for (i, j), items in self.tiles.items():
            for n, (t, _) in enumerate(items):
                tri[j, i, n] = t
                used[j, i, n] = True
        self._packed = (tri, used)
        return self._packed

    def __getstate__(self):
        # the lookup caches are rebuilt where they are used (pool workers), never pickled into tasks
        return {k: v for k, v in self.__dict__.items() if k not in ('_packed', '_cells')}

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._packed = None

    CELL = 8.0      # fast path: an 8-unit cell lying inside one triangle reads that triangle's plane

    def _planes(self):
        """Per 8-unit cell: the plane (a, b, c: z = a x + b y + c) of the one triangle that holds the whole
        cell, or NaN where the cell straddles triangle edges (those points take the exact path)."""
        import numpy as np
        per = int(round(self.step / self.CELL))
        nx, ny = self.size[0] * per, self.size[1] * per
        planes = np.full((ny, nx, 3), np.nan)
        offs = np.arange(per) * self.CELL
        for (i, j), items in self.tiles.items():
            x0, y0 = self.low[0] + i * self.step, self.low[1] + j * self.step
            gx, gy = np.meshgrid(x0 + offs, y0 + offs)                  # cell low corners (per x per)
            corners = [(gx, gy), (gx + self.CELL, gy), (gx, gy + self.CELL), (gx + self.CELL, gy + self.CELL)]
            for tri, _ in items:
                (ax, ay, az), (bx, by, bz), (cx, cy, cz) = tri
                den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
                if abs(den) < 1e-12:
                    continue
                inside = np.ones(gx.shape, bool)
                for px, py in corners:
                    u = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / den
                    v = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / den
                    inside &= (u >= -1e-9) & (v >= -1e-9) & (1 - u - v >= -1e-9)
                if not inside.any():
                    continue
                n = np.cross(np.subtract((bx, by, bz), (ax, ay, az)), np.subtract((cx, cy, cz), (ax, ay, az)))
                a, b = -n[0] / n[2], -n[1] / n[2]
                c = az - a * ax - b * ay
                block = planes[j * per:(j + 1) * per, i * per:(i + 1) * per]
                block[inside] = (a, b, c)
        self._cells = (planes, per)
        return self._cells

    def __call__(self, x, y):
        import numpy as np
        planes, per = getattr(self, '_cells', None) or self._planes()
        x, y = np.asarray(x, float), np.asarray(y, float)
        shape = np.broadcast(x, y).shape
        x, y = np.broadcast_to(x, shape).ravel(), np.broadcast_to(y, shape).ravel()
        i = np.clip(np.floor((x - self.low[0]) / self.CELL).astype(int), 0, planes.shape[1] - 1)
        j = np.clip(np.floor((y - self.low[1]) / self.CELL).astype(int), 0, planes.shape[0] - 1)
        p = planes[j, i]
        z = p[:, 0] * x + p[:, 1] * y + p[:, 2]
        slow = np.isnan(z)
        if slow.any():
            z[slow] = self._exact(x[slow], y[slow])
        return z.reshape(shape)

    def _exact(self, x, y):
        tri, used = self._packed or self._pack()
        x, y = np.asarray(x, float), np.asarray(y, float)
        shape = np.broadcast(x, y).shape
        x, y = np.broadcast_to(x, shape).ravel(), np.broadcast_to(y, shape).ravel()
        i = np.clip(np.floor((x - self.low[0]) / self.step).astype(int), 0, self.size[0] - 1)
        j = np.clip(np.floor((y - self.low[1]) / self.step).astype(int), 0, self.size[1] - 1)
        t = tri[j, i]                                      # (n, k, 3, 3)
        a, b, c = t[:, :, 0], t[:, :, 1], t[:, :, 2]
        den = (b[..., 1] - c[..., 1]) * (a[..., 0] - c[..., 0]) + (c[..., 0] - b[..., 0]) * (a[..., 1] - c[..., 1])
        ok = used[j, i] & (np.abs(den) > 1e-12)
        den = np.where(ok, den, 1.0)
        X, Y = x[:, None], y[:, None]
        u = ((b[..., 1] - c[..., 1]) * (X - c[..., 0]) + (c[..., 0] - b[..., 0]) * (Y - c[..., 1])) / den
        v = ((c[..., 1] - a[..., 1]) * (X - c[..., 0]) + (a[..., 0] - c[..., 0]) * (Y - c[..., 1])) / den
        w = 1.0 - u - v
        score = np.where(ok, np.minimum(np.minimum(u, v), w), -np.inf)
        n = np.argmax(score, axis=1)
        r = np.arange(len(x))
        z = u[r, n] * a[r, n, 2] + v[r, n] * b[r, n, 2] + w[r, n] * c[r, n, 2]
        return z.reshape(shape)
