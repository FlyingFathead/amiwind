# SPDX-License-Identifier: GPL-3.0-only
"""Chunk visibility: a cluster PVS per chunk, in Quake's compressed vis rows.

Quake's vis computes leaf-to-leaf visibility through portals; outdoors that
gave almost nothing (docs/performance/TOWN-VISIBILITY.md), because the open
street leaves are huge and buildings were brush entities vis cannot see. CHIM
keeps Quake's PVS mechanism (a bit row per cluster, zero-run compressed as in
Mod_DecompressVis; R_MarkLeaves marks what is potentially visible; entities
linked to leaves are culled with them) but computes the rows for chunks
(Quake 2 calls them clusters) directly from the geometry that occludes
outdoors: the ground, and the solid collision volumes of placed objects.

Chunk B is potentially visible from chunk A when any sampled sight line from
a standing (or raised) eye in A to a sample point of B's content (ground,
eye height, the top of the tallest object in B) clears both the ground and
every solid occluder cell, or the reverse line from B to A does. Chunks
beyond the ring (draw distance + hysteresis) are never resident and not
marked. A chunk always sees itself and its eight neighbours. Sampled, so it
can miss a narrow gap: the validator reports the numbers and the engine
counters must confirm there is no popping before the rows are trusted.
"""
import math

import numpy as np

EYE = 33.0           # player eye above the feet (standing hull 16.625 + eye height 16.4)
RAISED = 64.0        # a second, raised eye (stairs, roofs, jumps)
CELL = 16.0          # occluder grid
MARGIN = 2.0         # a sight line must pass this far inside ground or occluder to count as blocked
STEP = 12.0          # sight line sample spacing
FRACTIONS = (1 / 6, 0.5, 5 / 6)


# ---------------------------------------------------------------- Quake vis rows

def compress_row(row):
    """Quake vis compression: zero bytes become (0, run length)."""
    out = bytearray()
    i = 0
    while i < len(row):
        if row[i]:
            out.append(row[i])
            i += 1
            continue
        n = 0
        while i < len(row) and not row[i] and n < 255:
            n += 1
            i += 1
        out += bytes((0, n))
    return bytes(out)


def decompress_row(data, nbytes):
    """Mod_DecompressVis."""
    out = bytearray()
    i = 0
    while len(out) < nbytes:
        if i >= len(data):
            raise ValueError('Vis row ends early')
        if data[i]:
            out.append(data[i])
            i += 1
        else:
            if i + 1 >= len(data):
                raise ValueError('Vis row ends inside a zero run')
            out += bytes(data[i + 1])
            i += 2
    if len(out) != nbytes or i != len(data):
        raise ValueError('Vis row length mismatch')
    return bytes(out)


def bits_to_row(bits):
    row = bytearray((len(bits) + 7) // 8)
    for k, b in enumerate(bits):
        if b:
            row[k >> 3] |= 1 << (k & 7)
    return bytes(row)


def row_to_bits(row, n):
    return [bool(row[k >> 3] & (1 << (k & 7))) for k in range(n)]


# ---------------------------------------------------------------- geometry

class Ground:
    """Ground height from tile corner heights (rows by y), triangles 0-1-2 and 0-2-3 per tile."""

    def __init__(self, heights, step, low):
        self.h = np.asarray(heights, dtype=float)
        self.step, self.low = float(step), (float(low[0]), float(low[1]))

    def __call__(self, x, y):
        s = self.step
        ny, nx = self.h.shape[0] - 1, self.h.shape[1] - 1
        fx, fy = (np.asarray(x) - self.low[0]) / s, (np.asarray(y) - self.low[1]) / s
        i = np.clip(np.floor(fx).astype(int), 0, nx - 1)
        j = np.clip(np.floor(fy).astype(int), 0, ny - 1)
        u, v = np.clip(fx - i, 0, 1), np.clip(fy - j, 0, 1)
        h = self.h
        z00, z10, z11, z01 = h[j, i], h[j, i + 1], h[j + 1, i + 1], h[j + 1, i]
        a = z00 + (z10 - z00) * u + (z11 - z10) * v
        b = z00 + (z11 - z01) * u + (z01 - z00) * v
        return np.where(u >= v, a, b)


class Occluders:
    """Solid vertical intervals on a 16-unit grid: [lo, hi] where a column of the cell is surely inside a solid piece."""

    def __init__(self, low, span):
        self.low = (float(low[0]), float(low[1]))
        self.nx, self.ny = int(math.ceil(span[0] / CELL)), int(math.ceil(span[1] / CELL))
        self.lo = np.full((self.ny, self.nx), np.inf)
        self.hi = np.full((self.ny, self.nx), -np.inf)
        self.pieces = 0

    def add(self, equations, points):
        """A convex solid (scipy ConvexHull equations n.x + d <= 0 inside) in frame coordinates."""
        lo, hi = points.min(axis=0), points.max(axis=0)
        i0 = max(0, int(math.floor((lo[0] - self.low[0]) / CELL)))
        i1 = min(self.nx, int(math.ceil((hi[0] - self.low[0]) / CELL)))
        j0 = max(0, int(math.floor((lo[1] - self.low[1]) / CELL)))
        j1 = min(self.ny, int(math.ceil((hi[1] - self.low[1]) / CELL)))
        if i1 <= i0 or j1 <= j0:
            return
        xs = self.low[0] + np.arange(i0, i1 + 1) * CELL
        ys = self.low[1] + np.arange(j0, j1 + 1) * CELL
        X, Y = np.meshgrid(xs, ys)                         # cell corners
        n, d = equations[:, :3], equations[:, 3]
        rhs = -(d[None, None, :] + X[..., None] * n[:, 0] + Y[..., None] * n[:, 1])
        nz = n[:, 2]
        with np.errstate(divide='ignore', invalid='ignore'):
            bound = rhs / nz
        up = np.where(nz > 1e-9, bound, np.inf).min(axis=2)
        down = np.where(nz < -1e-9, bound, -np.inf).max(axis=2)
        flat_ok = np.where(np.abs(nz) <= 1e-9, rhs >= 0, True).all(axis=2)
        up = np.where(flat_ok, up, -np.inf)
        # a cell's column is solid where all four corner columns are (convexity)
        clo = np.maximum.reduce([down[:-1, :-1], down[1:, :-1], down[:-1, 1:], down[1:, 1:]])
        chi = np.minimum.reduce([up[:-1, :-1], up[1:, :-1], up[:-1, 1:], up[1:, 1:]])
        ok = chi - clo > 2 * MARGIN
        if not ok.any():
            return
        self.pieces += 1
        cur_lo, cur_hi = self.lo[j0:j1, i0:i1], self.hi[j0:j1, i0:i1]
        better = ok & ((chi - clo) > (cur_hi - cur_lo))
        cur_lo[better] = clo[better]
        cur_hi[better] = chi[better]

    def add_interval(self, i, j, lo, hi):
        """Cell (i, j) is surely solid between lo and hi (kept when longer than what the cell has)."""
        if hi - lo > 2 * MARGIN and hi - lo > self.hi[j, i] - self.lo[j, i]:
            self.lo[j, i], self.hi[j, i] = lo, hi

    def blocks(self, x, y, z):
        i = np.clip(np.floor((x - self.low[0]) / CELL).astype(int), 0, self.nx - 1)
        j = np.clip(np.floor((y - self.low[1]) / CELL).astype(int), 0, self.ny - 1)
        return (z > self.lo[j, i] + MARGIN) & (z < self.hi[j, i] - MARGIN)

    def cells(self):
        return int(np.isfinite(self.lo).sum())


def sight_clear(P, Q, ground, occluders):
    """Per sight line P[k] -> Q[k]: True when neither the ground nor an occluder blocks it."""
    P, Q = np.asarray(P, float), np.asarray(Q, float)
    length = np.linalg.norm(Q - P, axis=1)
    K = max(2, int(math.ceil(float(length.max()) / STEP)))
    t = (np.arange(K) + 0.5) / K
    pts = P[:, None, :] + (Q - P)[:, None, :] * t[None, :, None]
    along = length[:, None] * t[None, :]
    inner = (along > 8.0) & (along < length[:, None] - 8.0)
    x, y, z = pts[..., 0], pts[..., 1], pts[..., 2]
    blocked = (z < ground(x, y) - MARGIN)
    if occluders is not None:
        blocked |= occluders.blocks(x, y, z)
    return ~(blocked & inner).any(axis=1)


def chunk_points(box, ground, zs):
    """3 x 3 sample points of a chunk at heights zs(x, y) -> list of z arrays."""
    xs = [box[0] + f * (box[2] - box[0]) for f in FRACTIONS]
    ys = [box[1] + f * (box[3] - box[1]) for f in FRACTIONS]
    X, Y = np.meshgrid(xs, ys)
    X, Y = X.ravel(), Y.ravel()
    g = ground(X, Y)
    return np.concatenate([np.column_stack([X, Y, z(g)]) for z in zs])


def pvs_unit(task):
    """Visible pairs (a, b), a < b, for one block of source chunks (a pool worker)."""
    seen, stats = cluster_pvs(*task['args'], sources=task['sources'])
    pairs = sorted((a, b) for a, bs in seen.items() for b in bs if a < b)
    return {'pairs': pairs, 'stats': stats}


def cluster_pvs(nx, ny, grain, low, ground, occluders, tops, ring_offsets, sources=None):
    """Visible chunk sets: {(cx, cy): set of (cx, cy)} for every chunk of the frame.

    tops: {(cx, cy): highest z of content in the chunk (ground or a placement's drawn box)}.
    sources: only test pairs whose lower chunk is one of these (one block of a parallel run)."""
    def box(c):
        return (low[0] + c[0] * grain, low[1] + c[1] * grain, low[0] + (c[0] + 1) * grain, low[1] + (c[1] + 1) * grain)
    eyes = {}
    targets = {}
    need = None
    if sources is not None:
        need = {tuple(c) for c in sources}
        need |= {(c[0] + dx, c[1] + dy) for c in list(need) for dx, dy in ring_offsets}
    for cx in range(nx):
        for cy in range(ny):
            c = (cx, cy)
            if need is not None and c not in need:
                continue
            eyes[c] = chunk_points(box(c), ground, (lambda g: g + EYE, lambda g: g + EYE + RAISED))
            top = tops[c]
            targets[c] = chunk_points(box(c), ground, (lambda g: g + 8.0, lambda g: g + EYE,
                                                       lambda g, top=top: np.maximum(g + 8.0, top)))
    seen = {(cx, cy): {(cx, cy)} for cx in range(nx) for cy in range(ny)}
    tested = blocked = 0
    for (cx, cy) in (list(seen) if sources is None else [tuple(c) for c in sources]):
        for dx, dy in ring_offsets:
            b = (cx + dx, cy + dy)
            if not (0 <= b[0] < nx and 0 <= b[1] < ny) or b <= (cx, cy):
                continue
            a = (cx, cy)
            if max(abs(dx), abs(dy)) <= 1:
                seen[a].add(b)
                seen[b].add(a)
                continue
            tested += 1
            visible = False
            for src, dst in ((a, b), (b, a)):
                E, T = eyes[src], targets[dst]
                # one centre line first; then every eye to every target
                if sight_clear(E[4:5], T[13:14], ground, occluders)[0]:
                    visible = True
                    break
                P = np.repeat(E, len(T), axis=0)
                Q = np.tile(T, (len(E), 1))
                if sight_clear(P, Q, ground, occluders).any():
                    visible = True
                    break
            if visible:
                seen[a].add(b)
                seen[b].add(a)
            else:
                blocked += 1
    return seen, {'pairs_tested': tested, 'pairs_blocked': blocked}


# ---------------------------------------------------------------- placement visibility

def box_points(lo, hi):
    """Sample points of a drawn box: five on the top face, four side midpoints at two heights."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    xa, xb = x0 + (x1 - x0) / 6, x1 - (x1 - x0) / 6
    ya, yb = y0 + (y1 - y0) / 6, y1 - (y1 - y0) / 6
    xm, ym = (x0 + x1) / 2, (y0 + y1) / 2
    pts = [(xa, ya, z1), (xb, ya, z1), (xa, yb, z1), (xb, yb, z1), (xm, ym, z1)]
    for z in (z0 + (z1 - z0) / 4, (z0 + z1) / 2):
        pts += [(x0, ym, z), (x1, ym, z), (xm, y0, z), (xm, y1, z)]
    return np.array(pts, float)


def placement_visibility(grain, low, ground, occluders, viewers=(), candidates=None, near=None, boxes=None):
    """Potentially visible placements per viewer chunk.

    viewers: [(cx, cy)]; candidates: {chunk: sorted pids whose drawn box touches its ring};
    near: {chunk: pids whose box touches the chunk's 3 x 3 neighbourhood (always visible)};
    boxes: {pid: (lo, hi)}. A placement is visible from a chunk when any sight line from the
    chunk's eyes (3 x 3 points at standing and raised eye height) to one of its box points
    clears the ground and the occluders. Returns ({chunk: set of pids}, stats)."""
    out, tested, blocked = {}, 0, 0
    for c in viewers:
        box = (low[0] + c[0] * grain, low[1] + c[1] * grain, low[0] + (c[0] + 1) * grain,
               low[1] + (c[1] + 1) * grain)
        E = chunk_points(box, ground, (lambda g: g + EYE, lambda g: g + EYE + RAISED))
        seen = set((near or {}).get(c, ()))
        todo = [p for p in (candidates or {}).get(c, ()) if p not in seen]
        tested += len(todo)
        # first one line per placement (centre eye to the top centre), then the rest for those still hidden
        if todo:
            P = np.repeat(E[4:5], len(todo), axis=0)
            Q = np.array([box_points(*boxes[p])[4] for p in todo])
            ok = sight_clear(P, Q, ground, occluders)
            seen.update(p for p, v in zip(todo, ok) if v)
            todo = [p for p, v in zip(todo, ok) if not v]
        for p in todo:
            T = box_points(*boxes[p])
            P = np.repeat(E, len(T), axis=0)
            Q = np.tile(T, (len(E), 1))
            if sight_clear(P, Q, ground, occluders).any():
                seen.add(p)
            else:
                blocked += 1
        out[c] = seen
    return out, {'placements_tested': tested, 'placements_blocked': blocked}


def pvl_unit(task):
    """Visible placements of one block of viewer chunks (a pool worker)."""
    seen, stats = placement_visibility(*task['args'], viewers=task['viewers'], candidates=task['candidates'],
                                       near=task['near'], boxes=task['boxes'])
    return {'visible': {'%d,%d' % c: sorted(v) for c, v in seen.items()}, 'stats': stats}
