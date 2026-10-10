# SPDX-License-Identifier: GPL-3.0-only
"""Chunk terrain: the town converter's ground as a world BSP subtree, stored once.

The legacy town converter (import_town.terrain_map) writes every ground tile
of a region's coverage as two triangular prisms and lets qbsp/vis/light build
the region's world model; overlapping regions repeat the same tiles. Here
each tile belongs to exactly one chunk (chunk edges lie on the tile grid) and
the chunk is a shallow world BSP subtree, not a brush entity: axial splits on
tile edges, the tile diagonal, the ground plane (solid below), and the water
plane (water below, air above). Faces lie on their node's plane and leaves
carry contents and marksurfaces, as in a Quake world, so the engine can graft
the chunk roots under its frame grid, mark leaves from the chunk visibility
rows and link placements into leaves (efrags).

Faces use qbsp's texture projection; water is seen from above and below, as
qbsp emits liquid faces. Collision (the standing hull) is each tile polygon
extruded down as a convex piece, the same chain the shared models use.

Lighting: the legacy terrain bake has no light sources (light -minlight 24),
which writes one value into every sample; chunk faces share one lightmap
block of that value (as the stored lump of a region map already shares
identical blocks).
"""
import math
import struct
from types import SimpleNamespace

import numpy as np

from chim.models import SOLID_LEAF, BrushLumps, hull_pieces

TERRAIN_LIGHT = 12      # the stored sample value of today's terrain bake (minlight 24)
WATER_LEVEL = 0.0
TEX_SPECIAL = 1
TERRAIN_CEILING = 2048   # import_town: the legacy frame box closes here; leaves of open air reach it
TERRAIN_HULL_GRID = 64    # lattice of the compiled terrain hull's expanded corners (collision_bsp.compile_standing;
                          # 1024 leaves qbsp slivers: seam holes in tests/test_chim_ground.py)
CONTENTS_EMPTY, CONTENTS_SOLID, CONTENTS_WATER = -1, -2, -3
CONTENTS_LAVA = -5

# qbsp TextureAxisFromPlane: (normal, s, t) per base axis; first best wins.
BASE_AXES = (((0, 0, 1), (1, 0, 0), (0, -1, 0)), ((0, 0, -1), (1, 0, 0), (0, -1, 0)),
             ((1, 0, 0), (0, 1, 0), (0, 0, -1)), ((-1, 0, 0), (0, 1, 0), (0, 0, -1)),
             ((0, 1, 0), (1, 0, 0), (0, 0, -1)), ((0, -1, 0), (1, 0, 0), (0, 0, -1)))


def quake_texture_axes(normal):
    """3x2 texture axes (columns s, t) of a map face with shift 0, rotation 0, scale 1."""
    best, axes = -1.0, None
    for n, s, t in BASE_AXES:
        d = float(np.dot(normal, n))
        if d > best:
            best, axes = d, (s, t)
    return np.array(axes, dtype=float).T


def tile_polygons(corners):
    """Top polygons of one tile: one quad when its two triangles are coplanar."""
    c = np.asarray(corners, dtype=float)
    tris = [c[[0, 1, 2]], c[[0, 2, 3]]]
    n = np.cross(c[1] - c[0], c[2] - c[0])
    n /= np.linalg.norm(n)
    if abs(float(n @ (c[3] - c[0]))) < 1e-6:
        return [c]
    return tris


def clip_below(poly, level):
    """Part of a polygon at or below z = level (Sutherland-Hodgman)."""
    out = []
    for i, p in enumerate(poly):
        q = poly[(i + 1) % len(poly)]
        dp, dq = p[2] - level, q[2] - level
        if dp <= 0:
            out.append(p)
        if (dp < 0 < dq) or (dq < 0 < dp):
            out.append(p + (q - p) * dp / (dp - dq))
    return np.array(out) if len(out) >= 3 else None


def dedupe_points(poly, eps=1e-6):
    """A polygon without repeated consecutive corners, or None when fewer than three are left."""
    out = []
    for p in poly:
        if not out or float(np.abs(np.asarray(p) - out[-1]).max()) > eps:
            out.append(np.asarray(p, dtype=float))
    if len(out) > 1 and float(np.abs(out[0] - out[-1]).max()) <= eps:
        out.pop()
    return np.array(out) if len(out) >= 3 else None


def polygon_area_xy(poly):
    x, y = np.asarray(poly)[:, 0], np.asarray(poly)[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def ground_plane(poly):
    """Upward unit normal and distance of a ground polygon's plane."""
    p = np.asarray(poly, dtype=float)
    best = None
    for i in range(1, len(p) - 1):
        n = np.cross(p[i] - p[0], p[i + 1] - p[0])
        if best is None or np.linalg.norm(n) > np.linalg.norm(best):
            best = n
    n = best / np.linalg.norm(best)
    if n[2] < 0:
        n = -n
    return n, float(n @ p[0])


def split_keep(poly, n, d, keep):
    """The part of a polygon on one side of a vertical plane n.p = d (keep 1: front, -1: back)."""
    out = []
    pts = [tuple(float(v) for v in p) for p in poly]
    for i in range(len(pts)):
        p, q = pts[i], pts[(i + 1) % len(pts)]
        dp = keep * (n[0] * p[0] + n[1] * p[1] - d)
        dq = keep * (n[0] * q[0] + n[1] * q[1] - d)
        if dp >= -1e-9:
            out.append(p)
        if (dp > 1e-9 and dq < -1e-9) or (dp < -1e-9 and dq > 1e-9):
            t = dp / (dp - dq)
            out.append(tuple(p[k] + (q[k] - p[k]) * t for k in range(3)))
    return out


def clip_convex_xy(subject, clip):
    """The part of a convex plan polygon inside another (both counter-clockwise, (x, y) rows)."""
    out = [tuple(map(float, p[:2])) for p in subject]
    c = [tuple(map(float, p[:2])) for p in clip]
    for (ax, ay), (bx, by) in zip(c, c[1:] + c[:1]):
        if not out:
            break
        n = (by - ay, ax - bx)          # outward normal of a counter-clockwise edge: keep n.p <= d
        d = n[0] * ax + n[1] * ay
        pts, out = out, []
        for i in range(len(pts)):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            dp, dq = n[0] * p[0] + n[1] * p[1] - d, n[0] * q[0] + n[1] * q[1] - d
            if dp <= 1e-9:
                out.append(p)
            if (dp < -1e-9 and dq > 1e-9) or (dp > 1e-9 and dq < -1e-9):
                t = dp / (dp - dq)
                out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def clean_xy(points, eps=1e-7):
    """Drop repeated and collinear points of a convex polygon (in plan)."""
    pts = []
    for p in points:
        if not pts or abs(p[0] - pts[-1][0]) > eps or abs(p[1] - pts[-1][1]) > eps:
            pts.append(p)
    if len(pts) > 1 and abs(pts[0][0] - pts[-1][0]) <= eps and abs(pts[0][1] - pts[-1][1]) <= eps:
        pts.pop()
    changed = True
    while changed and len(pts) > 3:
        changed = False
        for i in range(len(pts)):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
            if abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) <= eps:
                pts.pop(i)
                changed = True
                break
    return pts


def split_line(region, items):
    """The vertical split plane of an irregular region: through an item edge that cuts the region,
    cutting the fewest items, then the most even split, then the first in item order."""
    best, best_key = None, None
    seen = set()
    for poly, _ in items:
        for i in range(len(poly)):
            a, b = poly[i], poly[(i + 1) % len(poly)]
            ex, ey = b[0] - a[0], b[1] - a[1]
            length = math.hypot(ex, ey)
            if length < 1e-6:
                continue
            n = np.array([ey / length, -ex / length, 0.0])
            if n[0] < -1e-12 or (abs(n[0]) <= 1e-12 and n[1] < 0):
                n = -n
            d = float(n[0] * a[0] + n[1] * a[1])
            key = (round(n[0], 9), round(n[1], 9), round(d, 6))
            if key in seen:
                continue
            seen.add(key)
            side = [n[0] * x + n[1] * y - d for x, y in region]
            if max(side) <= 1e-6 or min(side) >= -1e-6:
                continue                # on the region's boundary or outside it
            cuts = front = back = 0
            for q, _ in items:
                dv = [n[0] * p[0] + n[1] * p[1] - d for p in q]
                if max(dv) > 1e-6 and min(dv) < -1e-6:
                    cuts += 1
                elif max(dv) > 1e-6:
                    front += 1
                else:
                    back += 1
            score = (cuts, abs(front - back))
            if best_key is None or score < best_key:
                best, best_key = (n, d), score
    if best is None:
        raise ValueError('Irregular ground tile: no edge splits a region of %d pieces' % len(items))
    return best


class TerrainTree:
    """The chunk's world BSP in plain Python (for leaf counting): nodes and leaves.

    nodes[i] = (normal, dist, front, back); children >= 0 are nodes, < 0 are
    leaves (-1 - leaf); leaves[k] = contents (CONTENTS_SOLID leaf 0 shared)."""

    def __init__(self):
        self.nodes, self.leaves = [], [CONTENTS_SOLID]

    def depth(self):
        return tree_depth(self.nodes)

    def leaves_touched(self, lo, hi, root=0):
        """Non-solid leaves a box reaches (R_SplitEntityOnNode / BoxOnPlaneSide)."""
        return box_leaves(self.nodes, self.leaves, lo, hi, root)


def tree_depth(nodes):
    """Nodes on the longest path from node 0 to a leaf."""
    best, stack = 0, [(0, 1)] if nodes else []
    while stack:
        n, d = stack.pop()
        for c in nodes[n][2:4]:
            if c >= 0:
                stack.append((c, d + 1))
            else:
                best = max(best, d)
    return best


def box_leaves(nodes, leaves, lo, hi, root=0):
    out, stack = set(), [root]
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    while stack:
        n = stack.pop()
        if n < 0:
            if leaves[-1 - n] != CONTENTS_SOLID:
                out.add(-1 - n)
            continue
        normal, dist, front, back = nodes[n]
        near = np.where(normal >= 0, lo, hi) @ normal
        far = np.where(normal >= 0, hi, lo) @ normal
        if far >= dist:
            stack.append(front)
        if near < dist:
            stack.append(back)
    return out


def chunk_terrain(box, step, height, material, floor, texture_id, water_texture_id,
                  water_level=WATER_LEVEL, light=TERRAIN_LIGHT, ceiling=TERRAIN_CEILING, collision_box=None,
                  tiles=None, hull='routed', qbsp=None, collision_cache=None, liquids=None, lava_texture_id=None,
                  lava_depth=8.0, lava_bed=16.0):
    """Lumps of one chunk's terrain as a world BSP subtree.

    box: (x0, y0, x1, y1) on the tile grid; height(x, y) and material(x, y)
    the converter's samplers (import_town.terrain_at / terrain_material, tile
    material sampled at the tile centre); texture_id(material) the global
    texture of a ground material.

    The subtree is shallow and exact: axial splits on tile edges, a vertical
    diagonal plane where a tile is two triangles, the ground plane (back =
    solid leaf 0), and the water plane where the ground dips below it (back =
    water leaf, front = air). Faces sit on their node's plane (Quake world
    faces), every non-solid leaf lists its tile's faces as marksurfaces. Node
    0 is the root; dmodel head node 0 is the point hull (Quake's world hull 0
    is its node tree), head node 1 the standing hull.

    The standing hull (format 0.4) holds the tile prisms of the chunk and of
    every tile of collision_box (on the tile grid, holding box; default box)
    that the standing player box reaches from inside the chunk, so a point near
    a chunk border is classified against the neighbour's ground too and the
    hull is seamless where the engine grafts chunks side by side. Axial
    routing keeps each chain short (BrushLumps.routed_hull).

    tiles (format 0.5, irregular ground): tiles(x, y) -> [(triangle, material)]
    the converter's own triangles of the tile at (x, y) (shoreline samples, the
    port's 32-unit patch); height and material are then not used. The tile's
    subtree splits on the triangles' edges (vertical planes) until a leaf
    region holds one plane of one material, then the ground plane as above.
    hull (CHIM-SEYDA-MEMORY-33): 'routed' (format 0.4: routed chains of the expanded prisms) or
    'compiled': the same prisms expanded exactly by the standing box (Minkowski) and compiled by qbsp
    into one BSP, as collision_bsp.compile_standing compiles a model's exact union. The solid set is
    the same; the compiled tree is 5-70 times smaller (Seyda Neen's port chunks: 2,540-7,045 routed
    clipnodes against 456-724; flat sea: 513 against 7).
    liquids (docs/LAVA.md): lava prisms [{'hull': [[x, y], ...] counter-clockwise, 'top': z}] in the
    chunk's units (tools/lava.py). The open air above the ground is carved by each prism's planes (top,
    sides, bottom) into a CONTENTS_LAVA leaf, with the "*lava" warp face (lava_texture_id) on the top
    plane seen from above and below, as qbsp compiles a liquid brush; the bed under it (lava_bed units
    from top - lava_depth down) joins the standing hull as a convex piece, so a player stands in lava up
    to the shins and never swims (the legacy maps' tools/lava.pool_brushes).
    Returns (lumps, info) with info['tree'] the TerrainTree."""
    from mesh_geometry import split_surface
    from scipy.spatial import ConvexHull
    from surface_grid import engine_grid, face_points, sample_dimensions, texinfo_vecs
    x0, y0, x1, y1 = box
    if (x1 - x0) % step or (y1 - y0) % step:
        raise ValueError('Chunk edges must lie on the terrain tile grid')
    w = BrushLumps()
    w.lumps[10] = bytearray(SOLID_LEAF)
    tree = TerrainTree()
    node_rows, leaf_rows, marks, pieces, zs = [], [], [], [], []
    counts = {'tiles': 0, 'ground_faces': 0, 'water_faces': 0, 'lava_faces': 0, 'lava_leaves': 0}
    lavas = []
    for k, l in enumerate(liquids or ()):
        hull_xy = [(float(x), float(y)) for x, y in l['hull']]
        if len(hull_xy) < 3 or polygon_area_xy(np.array([(x, y, 0.0) for x, y in hull_xy])) <= 0:
            raise ValueError('A lava prism needs a counter-clockwise plan polygon')
        lavas.append({'k': k, 'hull': hull_xy, 'top': float(l['top']), 'bottom': float(l['top']) - lava_depth,
                      'box': (min(x for x, _ in hull_xy), min(y for _, y in hull_xy),
                              max(x for x, _ in hull_xy), max(y for _, y in hull_xy))})
    if lavas and lava_texture_id is None:
        raise ValueError('Lava prisms need the lava texture')

    def texture_of(m):
        if m[0] == 'water':
            return water_texture_id
        if m[0] == 'lava':
            return lava_texture_id
        return texture_id(m[1])

    def overlaps(region, l):
        b = l['box']
        if b[2] <= min(x for x, _ in region) or b[0] >= max(x for x, _ in region) or \
                b[3] <= min(y for _, y in region) or b[1] >= max(y for _, y in region):
            return False
        piece = clip_convex_xy(l['hull'], region)
        return len(piece) >= 3 and abs(polygon_area_xy(np.array([(x, y, 0.0) for x, y in piece]))) > 1e-6

    def lava_plan(region, ls):
        """A plan BSP of a convex region (counter-clockwise (x, y) rows) over the lava prisms ls, as qbsp splits a
        liquid brush: ['split', normal, dist, front, back] on a pool's side line that crosses the region,
        ['lava', region, top, bottom] where the region lies inside pools (overlapping pools merge: the highest top,
        the lowest bottom), ['air'] where no pool reaches. Each side line is used once per region it crosses, so
        neighbouring and overlapping pools cost a node per side, not a copy of every other pool."""
        if len(region) < 3:
            return ['air']
        ls = [l for l in ls if overlaps(region, l)]
        if not ls:
            return ['air']
        for l in ls:
            for (ax, ay), (bx, by) in zip(l['hull'], l['hull'][1:] + l['hull'][:1]):
                nx, ny = by - ay, ax - bx
                length = math.hypot(nx, ny)
                if length < 1e-9:
                    continue
                n = np.array([nx / length, ny / length, 0.0])
                d = float(n[0] * ax + n[1] * ay)
                sides = [n[0] * x + n[1] * y - d for x, y in region]
                if max(sides) > 1e-6 and min(sides) < -1e-6:
                    halves = [clean_xy([(p[0], p[1]) for p in split_keep([(x, y, 0.0) for x, y in region], n, d, k)])
                              for k in (1.0, -1.0)]
                    return ['split', n, d, lava_plan(halves[0], ls), lava_plan(halves[1], ls)]
        return ['lava', region, max(l['top'] for l in ls), min(l['bottom'] for l in ls)]

    def lava_over(poly, faces):
        """The lava plan over one ground polygon's plan area and its warp faces (both sides, on the top plane)."""
        if not lavas:
            return faces, ['air']
        area = [(float(p[0]), float(p[1])) for p in poly]
        if polygon_area_xy(np.array([(x, y, 0.0) for x, y in area])) < 0:
            area = area[::-1]
        zfloor = min(float(p[2]) for p in poly)
        # a pool under this ground gets no face inside the solid
        plan = lava_plan(area, [l for l in lavas if l['top'] > zfloor])
        up = np.array([0., 0., 1.])
        extra = []

        def walk(p):
            if p[0] == 'split':
                walk(p[3])
                walk(p[4])
            elif p[0] == 'lava':
                flat = np.array([(x, y, p[2]) for x, y in p[1]])
                ids = emit([(flat, up, quake_texture_axes(up), np.zeros(2), ('lava', None)),
                            (flat[::-1].copy(), -up, quake_texture_axes(-up), np.zeros(2), ('lava', None))],
                           w.plane(up, p[2]), lambda s: 0 if s[1][2] > 0 else 1)
                counts['lava_faces'] += len(ids)
                p.append(ids)
                extra.extend(ids)
        walk(plan)
        return faces + extra, plan

    def carve(plan, bounds, faces):
        """The open air of one tile region with the lava plan carved into it: vertical splits on the pools' sides,
        then per lava cell the top plane (holding its warp faces) and the bottom plane around a CONTENTS_LAVA leaf."""
        if plan[0] == 'air':
            return add_leaf(CONTENTS_EMPTY, bounds, faces)
        if plan[0] == 'split':
            me = add_node(plan[1], plan[2], bounds)
            w.plane(plan[1], plan[2])
            node_rows[me][2] = carve(plan[3], bounds, faces)
            node_rows[me][3] = carve(plan[4], bounds, faces)
            return me
        _, region, top, bottom, ids = plan
        up = np.array([0., 0., 1.])
        me = add_node(up, top, bounds)
        w.plane(up, top)
        node_rows[me][5:7] = [ids[0], len(ids)]
        node_rows[me][2] = add_leaf(CONTENTS_EMPTY, bounds, faces)
        low = add_node(-up, -bottom, bounds)
        w.plane(-up, -bottom)
        node_rows[me][3] = low
        node_rows[low][2] = add_leaf(CONTENTS_EMPTY, bounds, faces)
        counts['lava_leaves'] += 1
        xs, ys = [x for x, _ in region], [y for _, y in region]
        node_rows[low][3] = add_leaf(CONTENTS_LAVA, (min(xs), min(ys), bottom, max(xs), max(ys), top), faces)
        return me

    def add_node(normal, dist, bounds):
        node_rows.append([normal, dist, None, None, bounds, 0, 0])
        tree.nodes.append(None)
        return len(node_rows) - 1

    def add_leaf(contents, bounds, faces):
        leaf_rows.append((contents, bounds, len(marks), len(faces)))
        marks.extend(faces)
        tree.leaves.append(contents)
        return -1 - (len(tree.leaves) - 1)

    def emit(surfaces, pi, side_of):
        first, num = w.faces(surfaces, texture_of, flags_of=lambda s: TEX_SPECIAL if s[4][0] in ('water', 'lava') else 0,
                             light_of=lambda s: None if s[4][0] in ('water', 'lava') else 0,
                             plane_of=lambda s: (pi, side_of(s)))
        return list(range(first, first + num))

    def surface_subtree(poly, xy):
        """Ground plane node over one tile polygon, with water and air above it."""
        n = np.cross(poly[1] - poly[0], poly[2] - poly[0])
        n /= np.linalg.norm(n)
        d = float(n @ poly[0])
        axes = quake_texture_axes(n)
        ax = np.vstack([np.append(axes[:, 0], 0.), np.append(axes[:, 1], 0.)])
        zlo, zhi = float(poly[:, 2].min()), float(poly[:, 2].max())
        bounds = (xy[0], xy[1], min(zlo, water_level) - 1, xy[2], xy[3], ceiling)
        me = add_node(n, d, bounds)
        pi = w.plane(n, d)
        faces = emit([(p, n, axes, np.zeros(2), ('ground', material_here)) for p in split_surface(poly, ax)],
                     pi, lambda s: 0)
        counts['ground_faces'] += len(faces)
        node_rows[me][5:7] = [faces[0], len(faces)]
        low = clip_below(poly, water_level)
        if low is not None and tiles is not None:
            low = dedupe_points(low)        # irregular ground: no repeated corner at the water line
        if low is not None and zlo < water_level:
            flat = low.copy()
            flat[:, 2] = water_level
        else:
            flat = None
        if flat is not None and abs(polygon_area_xy(flat)) > 1e-9:
            up = np.array([0., 0., 1.])
            wn = add_node(up, water_level, (xy[0], xy[1], zlo - 1, xy[2], xy[3], ceiling))
            wpi = w.plane(up, water_level)
            water = emit([(flat, up, quake_texture_axes(up), np.zeros(2), ('water', None)),
                          (flat[::-1].copy(), -up, quake_texture_axes(-up), np.zeros(2), ('water', None))],
                         wpi, lambda s: 0 if s[1][2] > 0 else 1)
            counts['water_faces'] += len(water)
            node_rows[wn][5:7] = [water[0], len(water)]
            tile_faces, plan = lava_over(poly, faces + water)
            node_rows[wn][2] = carve(plan, (xy[0], xy[1], water_level, xy[2], xy[3], ceiling), tile_faces)
            node_rows[wn][3] = add_leaf(CONTENTS_WATER, (xy[0], xy[1], zlo, xy[2], xy[3], water_level), tile_faces)
            node_rows[me][2] = wn
        else:
            tile_faces, plan = lava_over(poly, faces)
            node_rows[me][2] = carve(plan, (xy[0], xy[1], zlo, xy[2], xy[3], ceiling), tile_faces)
        node_rows[me][3] = -1                          # solid leaf 0 below the ground
        return me

    def prism(poly):
        bottom = poly.copy()
        bottom[:, 2] = floor
        points = np.vstack([poly, bottom])
        return (points, SimpleNamespace(equations=ConvexHull(points).equations), [], 0.)

    def region_subtree(region, items):
        """Irregular tile (0.5): split the region on the items' edges until one plane is left."""
        nonlocal material_here
        xs, ys = [p[0] for p in region], [p[1] for p in region]
        xy = (min(xs), min(ys), max(xs), max(ys))
        planes = [ground_plane(poly) for poly, _ in items]
        n0, d0 = planes[0]
        if all(m == items[0][1] for _, m in items) and all(
                float(np.abs(n - n0).max()) < 1e-6 and abs(d - d0) < 1e-3 for n, d in planes):
            material_here = items[0][1]
            # a corner the source has keeps its exact height (no rounding at the water level)
            exact = {(round(p[0], 6), round(p[1], 6)): float(p[2]) for poly, _ in items for p in poly}
            face = np.array([[x, y, exact.get((round(x, 6), round(y, 6)), (d0 - n0[0] * x - n0[1] * y) / n0[2])]
                             for x, y in region])
            return surface_subtree(face, xy)
        n, d = split_line(region, items)
        zlo = min(float(poly[:, 2].min()) for poly, _ in items)
        me = add_node(n, d, (xy[0], xy[1], min(zlo, water_level) - 1, xy[2], xy[3], ceiling))
        w.plane(n, d)
        sides = []
        for keep in (1.0, -1.0):
            part = clean_xy(split_keep([(x, y, 0.0) for x, y in region], n, d, keep))
            kept = []
            for poly, m in items:
                piece = split_keep(poly, n, d, keep)
                if len(piece) >= 3 and abs(polygon_area_xy(np.array(piece))) > 1e-6:
                    kept.append((np.array(piece), m))
            sides.append(region_subtree([(p[0], p[1]) for p in part], kept))
        node_rows[me][2], node_rows[me][3] = sides
        return me

    def irregular_tile(x, y):
        counts['tiles'] += 1
        items = []
        for tri, m in tiles(x, y):
            poly = np.asarray(tri, dtype=float)
            if polygon_area_xy(poly) < 0:
                poly = poly[::-1].copy()
            items.append((poly, m))
            zs.extend(float(v) for v in poly[:, 2])
            pieces.append(prism(poly))
        return region_subtree([(x, y), (x + step, y), (x + step, y + step), (x, y + step)], items)

    def tile_subtree(x, y):
        nonlocal material_here
        if tiles is not None:
            return irregular_tile(x, y)
        counts['tiles'] += 1
        material_here = material(x + step / 2, y + step / 2)
        corners = [[x + dx, y + dy, height(x + dx, y + dy)] for dx, dy in ((0, 0), (step, 0), (step, step), (0, step))]
        zs.extend(c[2] for c in corners)
        polys = tile_polygons(corners)
        for poly in polys:
            bottom = poly.copy()
            bottom[:, 2] = floor
            points = np.vstack([poly, bottom])
            pieces.append((points, SimpleNamespace(equations=ConvexHull(points).equations), [], 0.))
        xy = (x, y, x + step, y + step)
        if len(polys) == 1:
            return surface_subtree(polys[0], xy)
        # vertical plane through the tile diagonal (0,0)-(1,1): triangle 0-1-2 lies in front
        n = np.array([1.0, -1.0, 0.0]) / math.sqrt(2.0)
        d = float(n @ np.array([x, y, 0.0]))
        zlo = min(c[2] for c in corners)
        me = add_node(n, d, (x, y, min(zlo, water_level) - 1, x + step, y + step, ceiling))
        w.plane(n, d)
        node_rows[me][2] = surface_subtree(polys[0], xy)
        node_rows[me][3] = surface_subtree(polys[1], xy)
        return me

    material_here = None

    def grid_subtree(i0, j0, i1, j1):
        if i1 - i0 == 1 and j1 - j0 == 1:
            return tile_subtree(x0 + i0 * step, y0 + j0 * step)
        if i1 - i0 >= j1 - j0:
            mid = (i0 + i1) // 2
            normal, dist = np.array([1.0, 0.0, 0.0]), float(x0 + mid * step)
            halves = ((mid, j0, i1, j1), (i0, j0, mid, j1))
        else:
            mid = (j0 + j1) // 2
            normal, dist = np.array([0.0, 1.0, 0.0]), float(y0 + mid * step)
            halves = ((i0, mid, i1, j1), (i0, j0, i1, mid))
        me = add_node(normal, dist, None)
        w.plane(normal, dist)
        node_rows[me][2] = grid_subtree(*halves[0])
        node_rows[me][3] = grid_subtree(*halves[1])
        return me
    nx, ny = int((x1 - x0) // step), int((y1 - y0) // step)
    grid_subtree(0, 0, nx, ny)
    # Node bounds: grid nodes take the union of their children's bounds.
    for k in range(len(node_rows) - 1, -1, -1):
        if node_rows[k][4] is None:
            kids = [node_rows[c][4] for c in node_rows[k][2:4] if c >= 0]
            node_rows[k][4] = tuple(min(b[i] for b in kids) for i in range(3)) + tuple(max(b[i] for b in kids)
                                                                                     for i in range(3, 6))
    for k, (normal, dist, front, back, bounds, firstface, numfaces) in enumerate(node_rows):
        pi = w.plane(normal, dist)
        # the tree used for leaf counts holds the plane as stored (the shared, single-precision record)
        stored = struct.unpack_from('<4f', w.lumps[1], 20 * pi)
        tree.nodes[k] = (np.array(stored[:3]), stored[3], front, back)
        w.lumps[5] += struct.pack('<ihh6h2H', pi, front, back, *short_box(bounds), firstface, numfaces)
    for contents, bounds, firstmark, nummarks in leaf_rows:
        w.lumps[10] += struct.pack('<2i6h2H4B', contents, -1, *short_box(bounds), firstmark, nummarks, 0, 0, 0, 0)
    w.lumps[11] = bytearray(struct.pack('<%dH' % len(marks), *marks))
    # One shared lightmap block of the uniform bake value, as large as the largest face needs.
    samples = 1
    faces = list(struct.iter_unpack('<HhihH4Bi', bytes(w.lumps[7])))
    edges = list(struct.iter_unpack('<HH', bytes(w.lumps[12])))
    surfedges = [v[0] for v in struct.iter_unpack('<i', bytes(w.lumps[13]))]
    for f in faces:
        if f[9] < 0:
            continue
        verts = [edges[e][0] if e >= 0 else edges[-e][1] for e in surfedges[f[2]:f[2] + f[3]]]
        _, extents = engine_grid(face_points(w.lumps[3], verts), texinfo_vecs(w.lumps[6], f[4]))
        dims = sample_dimensions(extents)
        samples = max(samples, dims[0] * dims[1])
    # Neighbour tiles the standing box reaches from inside the chunk (format 0.4: seamless hull 1).
    from player_hull import MINS, MAXS
    cx0, cy0, cx1, cy1 = collision_box or box
    if cx0 > x0 or cy0 > y0 or cx1 < x1 or cy1 < y1 or (x0 - cx0) % step or (y0 - cy0) % step:
        raise ValueError('The collision box must hold the chunk on the tile grid')
    reach_x, reach_y = max(-MINS[0], MAXS[0]), max(-MINS[1], MAXS[1])
    ring = 0
    for ty in range(int(cy0), int(cy1), step):
        for tx in range(int(cx0), int(cx1), step):
            if x0 <= tx < x1 and y0 <= ty < y1:
                continue
            if tx + step < x0 - reach_x or tx > x1 + reach_x or ty + step < y0 - reach_y or ty > y1 + reach_y:
                continue
            if tiles is not None:
                for tri, _ in tiles(tx, ty):
                    pieces.append(prism(np.asarray(tri, dtype=float)))
                ring += 1
                continue
            corners = [[tx + dx, ty + dy, height(tx + dx, ty + dy)]
                       for dx, dy in ((0, 0), (step, 0), (step, step), (0, step))]
            for poly in tile_polygons(corners):
                bottom = poly.copy()
                bottom[:, 2] = floor
                points = np.vstack([poly, bottom])
                pieces.append((points, SimpleNamespace(equations=ConvexHull(points).equations), [], 0.))
            ring += 1
    # The lava beds join the standing hull (every prism reaching the collision box).
    for l in lavas:
        b = l['box']
        if b[2] <= cx0 or b[0] >= cx1 or b[3] <= cy0 or b[1] >= cy1:
            continue
        points = np.array([(x, y, l['bottom']) for x, y in l['hull']] +
                          [(x, y, l['bottom'] - lava_bed) for x, y in l['hull']])
        pieces.append((points, SimpleNamespace(equations=ConvexHull(points).equations), [], 0.))
    if hull == 'compiled':
        from collision_bsp import compile_standing
        if qbsp is None or collision_cache is None:
            raise ValueError('The compiled terrain hull needs qbsp and a collision cache')
        compiled = compile_standing(hull_pieces(pieces), qbsp, collision_cache, grid=TERRAIN_HULL_GRID)
        croot = w.collider(hull_pieces(pieces), compiled=compiled, point_hull=False)[1]
    elif hull == 'routed':
        croot = w.routed_hull(hull_pieces(pieces), (x0, y0, x1, y1))
    else:
        raise ValueError('Unknown terrain hull: %s' % hull)
    zmin = min(zs + ([water_level] if counts['water_faces'] else []))
    zmax = max(zs + ([water_level] if counts['water_faces'] else []))
    lumps = w.finish([x0, y0, floor], [x1, y1, ceiling], 0, croot, 0, len(faces),
                     lighting=bytes([light]) * samples)
    info = {'tiles': counts['tiles'], 'faces': counts['ground_faces'], 'water_faces': counts['water_faces'],
            'lava_faces': counts['lava_faces'], 'lava_leaves': counts['lava_leaves'],
            'pieces': len(pieces), 'ring_tiles': ring,
            'hull_chain_max': max(getattr(w, 'hull_chains', None) or [0]),
            'clipnodes': len(w.lumps[9]) // 8, 'hull': hull, 'zmin': zmin, 'zmax': zmax, 'nodes': len(node_rows),
            'leaves': len(tree.leaves) - 1, 'depth': tree.depth(), 'tree': tree, 'texture_keys': list(w.textures)}
    return lumps, info


def terrain_unit(task):
    """One chunk's terrain from sampled data (a pool worker; see chim.units).

    task: box, step, heights (tile corner rows of the collision box, by y;
    default the chunk), materials (tile rows of the chunk, by y), floor,
    ceiling, water, light, collision_box (optional). Ground textures are the
    keys ('ground', 'gN'), water ('ground', '*water')."""
    cbox = task.get('collision_box') or task['box']
    x0, y0 = cbox[0], cbox[1]
    mx0, my0 = task['box'][0], task['box'][1]
    step = task['step']
    heights, materials = task['heights'], task['materials']

    def height(x, y):
        return heights[int(round((y - y0) / step))][int(round((x - x0) / step))]

    def material(x, y):
        return materials[int((y - my0) // step)][int((x - mx0) // step)]
    tiles = None
    if task.get('triangles') is not None:
        # format 0.5: [[tile x, tile y, [[x0 y0 z0 x1 y1 z1 x2 y2 z2 material], ...]], ...]
        by_tile = {(float(tx), float(ty)): [([r[0:3], r[3:6], r[6:9]], int(r[9])) for r in rows]
                   for tx, ty, rows in task['triangles']}

        def tiles(x, y):
            return by_tile[(float(x), float(y))]
    lumps, info = chunk_terrain(task['box'], step, height, material, task['floor'],
                                lambda m: ('ground', 'g%d' % m), ('ground', '*water'), task['water'],
                                task['light'], task['ceiling'], task.get('collision_box'), tiles,
                                task.get('hull', 'routed'), task.get('qbsp'), task.get('collision_cache'),
                                liquids=task.get('liquids'),
                                lava_texture_id=('ground', '*lava') if task.get('liquids') else None)
    return {'lumps': [bytes(x) for x in lumps], 'texture_keys': info.pop('texture_keys'), 'info': info}


def short_box(bounds):
    """Leaf and node bounds as stored: shorts, rounded outward."""
    return [int(math.floor(v)) for v in bounds[:3]] + [int(math.ceil(v)) for v in bounds[3:]]
