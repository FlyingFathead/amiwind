# SPDX-License-Identifier: GPL-3.0-only
"""Generated terrain records (world format 0.11, EXPERIMENTAL, build setting terrain_pack 'generate'): a chunk's
terrain stored as its heights and the few facts the builder decided, from which the engine generates the render part
of the brush image (chim/chim_thgt.c), the same bytes as the TERR record it replaces (docs/chim/WORLD_FORMAT.md
"Generated terrain records (0.11, experimental)"; the S0/S1 proofs of the CHIM template).

What is generated and what is stored:
- generated: the vertexes, edges, surfedges, faces, texture mappings (texinfo), leaves, marksurfaces, nodes (the
  tree, its bounds, its faces), the uniform light lump and the model, by the builder's own regular-path rule
  (chim.terrain.chunk_terrain: axial splits on the tile grid, the tile diagonal where a tile is two triangles, the
  ground plane, the cut of a ground polygon whose texture span passes 240 texels (mesh_geometry.split_surface), the
  water plane and face where the ground lies under water, the ground cut where the water line crosses it);
- stored: the corner heights (f32), per tile its texture slot and four bits of decided facts (one quad or two
  triangles; under water; the texture axis of each ground polygon), the plane index of every node, the plane lump
  and the standing hull (clipnodes) as chim.terc packs them (the hull is qbsp's compiled union: not generated), the
  texture references and the light value and size.
The planes are stored, not computed, so the generation needs no floating-point arithmetic beyond copying stored
values, floor/ceil of exact values and the crossing point of an edge and a cut (p + (q - p) * d / (d - e), in double
as the builder computes it; the engine sets a 68k FPU to double rounding precision while generating): an Amiga FPU
gives the same bytes as the builder (not yet measured on a 68040 or 68060).

Record version 1 holds a regular-path record (the tile rule). Record version 2 holds a record of the converter's own
triangles (shoreline insertion, 32-unit detail tiles: chunk_terrain's irregular path, region_subtree): the 32-unit
samples of the chunk and, per tile, its triangles as sample indices in the order the builder gave them (the pack
hands them over from the frame's ground, chunk_triangles); the generator then splits each tile on the triangles'
edges as the builder does (split_line, split_keep, clean_xy, ground_plane), in plain IEEE double arithmetic, and the
engine computes the same (square roots included). Lava records are not generated (their prisms are not in the
record). Only a record whose generation equals the stored record byte for byte is written so (encode checks it),
and only within the engine generator's fixed buffers (MAX_POLY and the rest); every other record stays as chim.terc
writes it. The engine expands it in its loading buffer as it does a compact record (same buffer rule).

Record (big-endian head; the plane and clipnode payloads are chim.terc's method payloads, little-endian):
  head (72)        'THG1', u32 image bytes, u32 render bytes, u16 1, u16 tiles x, u16 tiles y, u16 nodes,
                   f32 x0, y0, x1, y1, floor, ceiling, water level, step, u16 light samples, u8 light value,
                   u8 water texture slot (255: none), u32 plane payload bytes, u32 clipnode payload bytes,
                   u32 texture refs bytes, u32 croot (version 2: u16 2 after the image and render sizes)
  heights          version 1: (tiles x + 1) x (tiles y + 1) f32, by row (y), then x;
                   version 2: the 32-unit samples, (4 tiles x + 1) x (4 tiles y + 1) f32 (0 where no triangle uses one)
  tiles            version 1, per tile (by row): u8 texture slot, u8 facts (bit 0 one quad, bit 1 under water,
                   bits 2-3 the axis pair of the first ground polygon, bits 4-5 of the second), padded to 4;
                   version 2, per tile: u8 texture slot, u8 triangle count, padded to 4; then every tile's
                   triangles, three u8 sample indices each (v * 5 + u within the tile's 5 x 5 samples), padded to 4
  node planes      u16 per node, padded to 4
  texture refs     lump 2, verbatim
  planes           chim.terc payload of lump 1 (method PLANES or RAW: first u8 of a 4-byte prefix)
  clipnodes        chim.terc payload of lump 9 (method CLIPNODES or RAW)

Nothing here is reached by a default build: no unit kind and no stair code import it; only the pack in chim.world
(after every unit) and the readers call it, and only for a 0.11 world. Importing it lets chim.format read and write
format 0.11.
"""
import math
import struct

from chim import format as F
from chim import terc as TC

FORMAT_VERSION = (0, 11)
MAGIC = b'THG1'
HEAD = struct.Struct('>4sIIHHHHffffffffHBBIIII')
CONTENTS_SOLID, CONTENTS_EMPTY, CONTENTS_WATER = -2, -1, -3
TEX_SPECIAL = 1
# chim.terrain.BASE_AXES by pair (a base normal and its opposite share s and t): (s, t)
PAIRS = (((1.0, 0.0, 0.0), (0.0, -1.0, 0.0)), ((0.0, 1.0, 0.0), (0.0, 0.0, -1.0)), ((1.0, 0.0, 0.0), (0.0, 0.0, -1.0)))
GUARD = 1 / 16                  # surface_grid.GRID_GUARD
SOLID_LEAF = struct.pack('<2i6h2H4B', -2, -1, *[0] * 6, 0, 0, 0, 0, 0, 0)
# the engine generator's fixed buffers (chim_thgt.c); a record that needs more is not written generated
MAX_POLY, MAX_CALL_VERTS, MAX_PIECES, MAX_TEXINFO, MAX_ITEMS, ARENA_POINTS = 16, 32, 16, 64, 64, 6144

if FORMAT_VERSION not in F.READ_VERSIONS:
    F.READ_VERSIONS = F.READ_VERSIONS + (FORMAT_VERSION,)


class NotGenerated(ValueError):
    """The record is not one this generator makes (the builder keeps it as it was)."""


def is_generated(data):
    return bytes(data[:4]) == MAGIC


def F32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def _floor(v):
    return int(math.floor(v))


def _ceil(v):
    return int(math.ceil(v))


def short_box(b):
    return [_floor(v) for v in b[:3]] + [_ceil(v) for v in b[3:]]


# ---------------------------------------------------------------- the generator (mirrored by chim_thgt.c)

def generate(p):
    """The 15 lumps of a terrain image from its record's facts P (dict, decode_facts' form); the rule of
    chim.terrain.chunk_terrain's regular path, with planes and the hull taken from P."""
    x0, y0, x1, y1 = p['box']
    step, floor_z, ceiling, water = p['step'], p['floor'], p['ceiling'], p['water']
    nx, ny = p['tiles']
    heights, tiles, node_planes = p['heights'], p['tile_facts'], p['node_planes']   # version 2: 32-unit samples
    verts, edges, surf, faces, texinfo = bytearray(), bytearray(struct.pack('<HH', 0, 0)), bytearray(), [], bytearray()
    tx_index = {}
    node_rows, leaf_rows, marks = [], [], []
    leaf_count = [1]                                        # leaf 0: the shared solid leaf

    def texinfo_of(pair, slot, flags):
        key = (pair, slot, flags)
        if key not in tx_index:
            if len(tx_index) >= MAX_TEXINFO:
                raise NotGenerated('more texture mappings than the engine holds')
            tx_index[key] = len(texinfo) // 40
            s, t = PAIRS[pair]
            texinfo.extend(struct.pack('<8fii', *s, 0.0, *t, 0.0, slot, flags))
        return tx_index[key]

    def emit(surfaces, plane):
        """surfaces: [(points, pair, slot, flags, side, light)]; one vertex and edge map per call
        (BrushLumps.faces), points counter-clockwise, stored reversed."""
        first = len(faces)
        vmap, emap = {}, {}

        def vertex(pt):
            key = (round(pt[0] * 1e5), round(pt[1] * 1e5), round(pt[2] * 1e5))     # BrushLumps.faces: 1e-5
            if key not in vmap:
                if len(vmap) >= MAX_CALL_VERTS:
                    raise NotGenerated('more corners in one face call than the engine holds')
                vmap[key] = len(verts) // 12
                verts.extend(struct.pack('<3f', *pt))
            return vmap[key]
        for pts, pair, slot, flags, side, light in surfaces:
            tx = texinfo_of(pair, slot, flags)
            if len(pts) > MAX_POLY:
                raise NotGenerated('a face of more corners than the engine holds')
            vs = [vertex(pt) for pt in pts[::-1]]
            firstedge = len(surf) // 4
            for a, c in zip(vs, vs[1:] + vs[:1]):
                if (a, c) in emap:
                    ed = emap[a, c]
                elif (c, a) in emap:
                    ed = -emap[c, a]
                else:
                    if len(emap) >= 2 * MAX_CALL_VERTS:
                        raise NotGenerated('more edges in one face call than the engine holds')
                    ed = len(edges) // 4
                    emap[a, c] = ed
                    edges.extend(struct.pack('<HH', a, c))
                surf.extend(struct.pack('<i', ed))
            styles, lightofs = ((0, 255, 255, 255), 0) if light else ((255, 255, 255, 255), -1)
            faces.append((plane, side, firstedge, len(vs), tx, styles, lightofs))
        return list(range(first, len(faces)))

    def add_node(bounds):
        node_rows.append([None, None, bounds, 0, 0])
        return len(node_rows) - 1

    def add_leaf(contents, bounds, fs):
        leaf_rows.append((contents, bounds, len(marks), len(fs)))
        marks.extend(fs)
        leaf_count[0] += 1
        return -1 - (leaf_count[0] - 1)

    def plane_of(k):
        if k >= len(node_planes):
            raise NotGenerated('more nodes than the record names')
        return node_planes[k]

    def crossing(pt, q, d, e):
        """p + (q - p) * d / (d - e), per component, in IEEE double (numpy's element-wise order); the one place
        the generator computes a coordinate (the engine sets its FPU to double precision for it)."""
        return tuple(pt[k] + (q[k] - pt[k]) * d / (d - e) for k in range(3))

    def clip_below(poly):
        out = []
        for i, pt in enumerate(poly):
            q = poly[(i + 1) % len(poly)]
            dp, dq = pt[2] - water, q[2] - water
            if dp <= 0:
                if len(out) >= MAX_POLY:
                    raise NotGenerated('a water polygon of more corners than the engine holds')
                out.append(pt)
            if (dp < 0 < dq) or (dq < 0 < dp):
                if len(out) >= MAX_POLY:
                    raise NotGenerated('a water polygon of more corners than the engine holds')
                out.append(crossing(pt, q, dp, dq))
        return out if len(out) >= 3 else None

    def split_surface(poly, pair):
        """mesh_geometry.split_surface: a face whose texture span passes 240 texels (with the 1/16 guard, on the
        16-texel grid) is cut 224 texels from its low line, back part first; the texture axes are whole units."""
        axes = PAIRS[pair]
        uv = [[sum(pt[k] * axes[a][k] for k in range(3)) for a in range(2)] for pt in poly]
        for a in range(2):
            lo = math.floor((min(v[a] for v in uv) - GUARD) / 16) * 16
            hi = math.ceil((max(v[a] for v in uv) + GUARD) / 16) * 16
            if hi - lo <= 240:
                continue
            cut = lo + 224
            dist = [v[a] - cut for v in uv]
            front, back = [], []
            for i, pt in enumerate(poly):
                j = (i + 1) % len(poly)
                d, e = dist[i], dist[j]
                if len(front) >= MAX_POLY - 1 or len(back) >= MAX_POLY - 1:
                    raise NotGenerated('a texture split of more corners than the engine holds')
                if d <= 1e-6:
                    back.append(pt)
                if d >= -1e-6:
                    front.append(pt)
                if (d > 1e-6 and e < -1e-6) or (d < -1e-6 and e > 1e-6):
                    q = crossing(pt, poly[j], d, e)
                    front.append(q)
                    back.append(q)
            if len(back) < 3 or len(front) < 3:
                raise NotGenerated('a texture split leaves a sliver')
            return split_surface(back, pair) + split_surface(front, pair)
        return [poly]

    def surface_subtree(poly, xy, pair, slot, under):
        zlo = min(pt[2] for pt in poly)
        me = add_node((xy[0], xy[1], min(zlo, water) - 1, xy[2], xy[3], ceiling))
        pi = plane_of(me)
        parts = split_surface(poly, pair)
        if len(parts) > MAX_PIECES:
            raise NotGenerated('more texture split pieces than the engine holds')
        fs = emit([(part, pair, slot, 0, 0, True) for part in parts], pi)
        node_rows[me][3:5] = [fs[0], len(fs)]
        if under:
            if not zlo < water:
                raise NotGenerated('a tile marked under water lies over it')
            low = clip_below(poly)
            if low is None:
                raise NotGenerated('a tile marked under water has no water face')
            flat = [(pt[0], pt[1], water) for pt in low]
            wn = add_node((xy[0], xy[1], zlo - 1, xy[2], xy[3], ceiling))
            wpi = plane_of(wn)
            wf = emit([(flat, 0, p['water_slot'], TEX_SPECIAL, 0, False),
                       (flat[::-1], 0, p['water_slot'], TEX_SPECIAL, 1, False)], wpi)
            node_rows[wn][3:5] = [wf[0], len(wf)]
            tile = fs + wf
            node_rows[wn][0] = add_leaf(CONTENTS_EMPTY, (xy[0], xy[1], water, xy[2], xy[3], ceiling), tile)
            node_rows[wn][1] = add_leaf(CONTENTS_WATER, (xy[0], xy[1], zlo, xy[2], xy[3], water), tile)
            node_rows[me][0] = wn
        else:
            node_rows[me][0] = add_leaf(CONTENTS_EMPTY, (xy[0], xy[1], zlo, xy[2], xy[3], ceiling), fs)
        node_rows[me][1] = -1
        return me

    # ---- record version 2, the converter's own triangles: chim.terrain.chunk_terrain's irregular path
    # (irregular_tile -> region_subtree -> surface_subtree). Every value in plain IEEE double, in the order the C
    # code computes it: sums left to right, lengths as the square root of the sum of squares, no library dot product.
    def area_xy(poly):
        s = 0.0
        n = len(poly)
        for k in range(n):
            a, b = poly[k], poly[(k + 1) % n]
            s += a[0] * b[1] - a[1] * b[0]
        return 0.5 * s

    def cross_of(a, b):
        return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])

    def length(n):
        return math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2])

    def ground_plane(poly):
        p0 = poly[0]
        best, bl = None, 0.0
        for i in range(1, len(poly) - 1):
            a = (poly[i][0] - p0[0], poly[i][1] - p0[1], poly[i][2] - p0[2])
            b = (poly[i + 1][0] - p0[0], poly[i + 1][1] - p0[1], poly[i + 1][2] - p0[2])
            n = cross_of(a, b)
            ln = length(n)
            if best is None or ln > bl:
                best, bl = n, ln
        n = (best[0] / bl, best[1] / bl, best[2] / bl)
        if n[2] < 0:
            n = (-n[0], -n[1], -n[2])
        return n, n[0] * p0[0] + n[1] * p0[1] + n[2] * p0[2]

    def split_keep(poly, n, d, keep):
        out = []
        for i in range(len(poly)):
            pt, q = poly[i], poly[(i + 1) % len(poly)]
            dp = keep * (n[0] * pt[0] + n[1] * pt[1] - d)
            dq = keep * (n[0] * q[0] + n[1] * q[1] - d)
            if dp >= -1e-9:
                if len(out) >= MAX_POLY:
                    raise NotGenerated('a split piece of more corners than the engine holds')
                out.append(pt)
            if (dp > 1e-9 and dq < -1e-9) or (dp < -1e-9 and dq > 1e-9):
                t = dp / (dp - dq)
                if len(out) >= MAX_POLY:
                    raise NotGenerated('a split piece of more corners than the engine holds')
                out.append((pt[0] + (q[0] - pt[0]) * t, pt[1] + (q[1] - pt[1]) * t, pt[2] + (q[2] - pt[2]) * t))
        return out

    def clean_xy(pts, eps=1e-7):
        out = []
        for pt in pts:
            if not out or abs(pt[0] - out[-1][0]) > eps or abs(pt[1] - out[-1][1]) > eps:
                out.append(pt)
        if len(out) > 1 and abs(out[0][0] - out[-1][0]) <= eps and abs(out[0][1] - out[-1][1]) <= eps:
            out.pop()
        changed = True
        while changed and len(out) > 3:
            changed = False
            for i in range(len(out)):
                a, b, c = out[i - 1], out[i], out[(i + 1) % len(out)]
                if abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) <= eps:
                    out.pop(i)
                    changed = True
                    break
        return out

    def split_line(region, items):
        best, best_key = None, None
        for poly in items:
            for i in range(len(poly)):
                a, b = poly[i], poly[(i + 1) % len(poly)]
                ex, ey = b[0] - a[0], b[1] - a[1]
                ln = math.sqrt(ex * ex + ey * ey)
                if ln < 1e-6:
                    continue
                n = (ey / ln, -ex / ln)
                if n[0] < -1e-12 or (abs(n[0]) <= 1e-12 and n[1] < 0):
                    n = (-n[0], -n[1])
                d = n[0] * a[0] + n[1] * a[1]
                side = [n[0] * x + n[1] * y - d for x, y in region]
                if max(side) <= 1e-6 or min(side) >= -1e-6:
                    continue
                cuts = front = back = 0
                for q in items:
                    dv = [n[0] * pt[0] + n[1] * pt[1] - d for pt in q]
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
            raise NotGenerated('an irregular region no edge splits')
        return best

    def key6(v):
        return round(v * 1e6)

    def dedupe(poly, eps=1e-6):
        out = []
        for pt in poly:
            if not out or max(abs(pt[k] - out[-1][k]) for k in range(3)) > eps:
                out.append(pt)
        if len(out) > 1 and max(abs(out[0][k] - out[-1][k]) for k in range(3)) <= eps:
            out.pop()
        return out if len(out) >= 3 else None

    def irregular_surface(poly, xy, slot):
        a = (poly[1][0] - poly[0][0], poly[1][1] - poly[0][1], poly[1][2] - poly[0][2])
        b = (poly[2][0] - poly[0][0], poly[2][1] - poly[0][1], poly[2][2] - poly[0][2])
        n = cross_of(a, b)
        ln = length(n)
        n = (n[0] / ln, n[1] / ln, n[2] / ln)
        best, pair = -1.0, None
        for k, c in enumerate((n[2], -n[2], n[0], -n[0], n[1], -n[1])):       # chim.terrain.BASE_AXES order
            if c > best:
                best, pair = c, k // 2
        if pair is None:
            raise NotGenerated('a ground polygon without texture axes')
        zlo = min(pt[2] for pt in poly)
        me = add_node((xy[0], xy[1], min(zlo, water) - 1, xy[2], xy[3], ceiling))
        pi = plane_of(me)
        parts = split_surface(poly, pair)
        if len(parts) > MAX_PIECES:
            raise NotGenerated('more texture split pieces than the engine holds')
        fs = emit([(part, pair, slot, 0, 0, True) for part in parts], pi)
        node_rows[me][3:5] = [fs[0], len(fs)]
        low = clip_below(poly)
        if low is not None:
            low = dedupe(low)
        flat = [(pt[0], pt[1], water) for pt in low] if low is not None and zlo < water else None
        if flat is not None and abs(area_xy(flat)) > 1e-9:
            if p['water_slot'] is None:
                raise NotGenerated('water without its texture slot')
            wn = add_node((xy[0], xy[1], zlo - 1, xy[2], xy[3], ceiling))
            wpi = plane_of(wn)
            wf = emit([(flat, 0, p['water_slot'], TEX_SPECIAL, 0, False),
                       (flat[::-1], 0, p['water_slot'], TEX_SPECIAL, 1, False)], wpi)
            node_rows[wn][3:5] = [wf[0], len(wf)]
            tile = fs + wf
            node_rows[wn][0] = add_leaf(CONTENTS_EMPTY, (xy[0], xy[1], water, xy[2], xy[3], ceiling), tile)
            node_rows[wn][1] = add_leaf(CONTENTS_WATER, (xy[0], xy[1], zlo, xy[2], xy[3], water), tile)
            node_rows[me][0] = wn
        else:
            node_rows[me][0] = add_leaf(CONTENTS_EMPTY, (xy[0], xy[1], zlo, xy[2], xy[3], ceiling), fs)
        node_rows[me][1] = -1
        return me

    arena = [0]

    def region_subtree(region, items, slot):
        xs, ys = [pt[0] for pt in region], [pt[1] for pt in region]
        xy = (min(xs), min(ys), max(xs), max(ys))
        planes = [ground_plane(poly) for poly in items]
        n0, d0 = planes[0]
        if all(max(abs(n[k] - n0[k]) for k in range(3)) < 1e-6 and abs(d - d0) < 1e-3 for n, d in planes):
            exact = {}
            for poly in items:
                for pt in poly:
                    exact[(key6(pt[0]), key6(pt[1]))] = pt[2]
            face = []
            for x, y in region:
                z = exact.get((key6(x), key6(y)))
                face.append((x, y, z if z is not None else (d0 - n0[0] * x - n0[1] * y) / n0[2]))
            return irregular_surface(face, xy, slot)
        n, d = split_line(region, items)
        zlo = min(pt[2] for poly in items for pt in poly)
        me = add_node((xy[0], xy[1], min(zlo, water) - 1, xy[2], xy[3], ceiling))
        sides = []
        base = arena[0]
        for keep in (1.0, -1.0):
            part = clean_xy(split_keep([(x, y, 0.0) for x, y in region], n, d, keep))
            kept = []
            for poly in items:
                piece = split_keep(poly, n, d, keep)
                if len(piece) >= 3 and abs(area_xy(piece)) > 1e-6:
                    if len(kept) >= MAX_ITEMS or arena[0] + len(piece) > ARENA_POINTS:
                        raise NotGenerated('more split pieces than the engine holds')
                    arena[0] += len(piece)
                    kept.append(piece)
            if not kept or len(part) < 3:
                raise NotGenerated('an irregular split leaves an empty side')
            sides.append(region_subtree([(pt[0], pt[1]) for pt in part], kept, slot))
            arena[0] = base
        node_rows[me][0], node_rows[me][1] = sides
        return me

    def irregular_tile(i, j):
        x, y = x0 + i * step, y0 + j * step
        slot, tris = tiles[j][i]
        items = []
        for tri in tris:
            poly = [(x + 32.0 * (v % 5), y + 32.0 * (v // 5), heights[4 * j + v // 5][4 * i + v % 5]) for v in tri]
            if area_xy(poly) < 0:
                poly = poly[::-1]
            items.append(poly)
        if not items or len(items) > MAX_ITEMS or 3 * len(items) > ARENA_POINTS:
            raise NotGenerated('a tile without triangles, or more than the engine holds')
        arena[0] = 3 * len(items)
        return region_subtree([(x, y), (x + step, y), (x + step, y + step), (x, y + step)], items, slot)

    def tile_subtree(i, j):
        if p.get('version', 1) == 2:
            return irregular_tile(i, j)
        x, y = x0 + i * step, y0 + j * step
        slot, facts = tiles[j][i]
        h = lambda a, b: heights[j + b][i + a]      # noqa: E731
        c = [(x, y, h(0, 0)), (x + step, y, h(1, 0)), (x + step, y + step, h(1, 1)), (x, y + step, h(0, 1))]
        xy = (x, y, x + step, y + step)
        under = bool(facts & 2)
        if facts & 1:
            return surface_subtree(c, xy, (facts >> 2) & 3, slot, under)
        zlo = min(pt[2] for pt in c)
        me = add_node((x, y, min(zlo, water) - 1, x + step, y + step, ceiling))
        node_rows[me][0] = surface_subtree([c[0], c[1], c[2]], xy, (facts >> 2) & 3, slot, under)
        node_rows[me][1] = surface_subtree([c[0], c[2], c[3]], xy, (facts >> 4) & 3, slot, under)
        return me

    def grid_subtree(i0, j0, i1, j1):
        if i1 - i0 == 1 and j1 - j0 == 1:
            return tile_subtree(i0, j0)
        if i1 - i0 >= j1 - j0:
            mid = (i0 + i1) // 2
            halves = ((mid, j0, i1, j1), (i0, j0, mid, j1))
        else:
            mid = (j0 + j1) // 2
            halves = ((i0, mid, i1, j1), (i0, j0, i1, mid))
        me = add_node(None)
        node_rows[me][0] = grid_subtree(*halves[0])
        node_rows[me][1] = grid_subtree(*halves[1])
        return me
    if p.get('version', 1) == 1 and p['water_slot'] is None and any(f & 2 for row in tiles for _, f in row):
        raise NotGenerated('water without its texture slot')
    grid_subtree(0, 0, nx, ny)
    if len(node_rows) != len(node_planes):
        raise NotGenerated('the record names %d node planes, the tree has %d nodes' % (len(node_planes), len(node_rows)))
    for k in range(len(node_rows) - 1, -1, -1):
        if node_rows[k][2] is None:
            kids = [node_rows[c][2] for c in node_rows[k][0:2] if c >= 0]
            node_rows[k][2] = tuple(min(b[i] for b in kids) for i in range(3)) + \
                tuple(max(b[i] for b in kids) for i in range(3, 6))
    lumps = [b''] * 15
    lumps[1] = p['planes']
    lumps[2] = p['texture_refs']
    lumps[3] = bytes(verts)
    lumps[5] = b''.join(struct.pack('<ihh6h2H', node_planes[k], r[0], r[1], *short_box(r[2]), r[3], r[4])
                        for k, r in enumerate(node_rows))
    lumps[6] = bytes(texinfo)
    lumps[7] = b''.join(struct.pack('<HhihH4Bi', f[0], f[1], f[2], f[3], f[4], *f[5], f[6]) for f in faces)
    lumps[8] = bytes([p['light']]) * p['light_samples']
    lumps[9] = p['clipnodes']
    lumps[10] = SOLID_LEAF + b''.join(struct.pack('<2i6h2H4B', c, -1, *short_box(b), fm, nm, 0, 0, 0, 0)
                                      for c, b, fm, nm in leaf_rows)
    lumps[11] = struct.pack('<%dH' % len(marks), *marks)
    lumps[12] = bytes(edges)
    lumps[13] = bytes(surf)
    lumps[14] = struct.pack('<9f7i', x0, y0, floor_z, x1, y1, ceiling, 0, 0, 0, 0, p['croot'], p['croot'], p['croot'],
                            0, 0, len(faces))
    return lumps


# ---------------------------------------------------------------- the record

def _pad4(b):
    return bytes(b) + bytes((-len(b)) % 4)


def _lump_payload(k, data):
    method, payload = TC._pack_lump(k, data)
    return struct.pack('<B3x', method) + payload


def _lump_of(payload):
    return TC._unpack_lump(payload[0], payload[4:])


def facts_of(image):
    """The record's facts read from a stored TERR image, or NotGenerated. The tile facts (quad, water, axis pairs,
    slot) are read from the faces the image holds; generate() then has to give back the image byte for byte."""
    lumps = F.read_brush_image(image)
    if lumps[0] or lumps[4]:
        raise NotGenerated('entities or visibility present')
    mins, maxs = struct.unpack_from('<3f', lumps[14], 0), struct.unpack_from('<3f', lumps[14], 12)
    heads = struct.unpack_from('<4i', lumps[14], 36)
    step = 128.0
    x0, y0, x1, y1 = mins[0], mins[1], maxs[0], maxs[1]
    nx, ny = (x1 - x0) / step, (y1 - y0) / step
    if nx != int(nx) or ny != int(ny) or nx < 1 or ny < 1 or len(lumps[14]) != 64 or heads[0] != 0:
        raise NotGenerated('not a chunk on the tile grid')
    nx, ny = int(nx), int(ny)
    verts = [struct.unpack_from('<3f', lumps[3], a) for a in range(0, len(lumps[3]), 12)]
    edges = list(struct.iter_unpack('<HH', lumps[12]))
    surf = [v[0] for v in struct.iter_unpack('<i', lumps[13])]
    tex = list(struct.iter_unpack('<8fii', lumps[6]))
    heights = [[None] * (nx + 1) for _ in range(ny + 1)]
    tiles = [[[None, 0, [], []] for _ in range(nx)] for _ in range(ny)]   # slot, water, [pairs], [planes]
    water_slot = None
    pair_of = {(s, t): k for k, (s, t) in enumerate(PAIRS)}
    for f in struct.iter_unpack('<HhihH4Bi', lumps[7]):
        vs = [verts[edges[e][0] if e >= 0 else edges[-e][1]] for e in surf[f[2]:f[2] + f[3]]]
        ti = tex[f[4]]
        if any(ti[k] for k in (3, 7)):
            raise NotGenerated('a texture offset')
        cx, cy = sum(v[0] for v in vs) / len(vs), sum(v[1] for v in vs) / len(vs)
        i, j = int((cx - x0) // step), int((cy - y0) // step)
        if not (0 <= i < nx and 0 <= j < ny):
            raise NotGenerated('a face outside the chunk')
        if ti[9] & TEX_SPECIAL:
            water_slot = ti[8]
            tiles[j][i][1] = 1
            continue
        tiles[j][i][0] = ti[8]
        st = (tuple(ti[0:3]), tuple(ti[4:7]))
        if st not in pair_of:
            raise NotGenerated('texture axes of no base pair')
        # one ground polygon per plane (a polygon cut by the texture split keeps its plane)
        if f[0] not in tiles[j][i][3]:
            tiles[j][i][3].append(f[0])
            tiles[j][i][2].append(pair_of[st])
        for v in vs:
            a, b = (v[0] - x0) / step, (v[1] - y0) / step
            if a != int(a) or b != int(b):
                continue                    # a texture-split or water-line point: generated
            a, b = int(a), int(b)
            if heights[b][a] is not None and heights[b][a] != v[2]:
                raise NotGenerated('two heights at one corner')
            heights[b][a] = v[2]
    if any(h is None for row in heights for h in row):
        raise NotGenerated('a corner without a ground vertex')
    facts = []
    for row in tiles:
        out = []
        for slot, under, pairs, _ in row:
            if slot is None or len(pairs) not in (1, 2):
                raise NotGenerated('a tile without its ground faces')
            v = (1 if len(pairs) == 1 else 0) | (2 if under else 0) | (pairs[0] << 2) | \
                ((pairs[1] if len(pairs) == 2 else 0) << 4)
            out.append((slot, v))
        facts.append(out)
    light = lumps[8]
    if light and light != bytes([light[0]]) * len(light):
        raise NotGenerated('a light lump of several values')
    return {'box': (x0, y0, x1, y1), 'step': step, 'floor': mins[2], 'ceiling': maxs[2], 'water': 0.0,
            'tiles': (nx, ny), 'heights': heights, 'tile_facts': facts,
            'node_planes': [struct.unpack_from('<i', lumps[5], a)[0] for a in range(0, len(lumps[5]), 24)],
            'planes': bytes(lumps[1]), 'texture_refs': bytes(lumps[2]), 'clipnodes': bytes(lumps[9]),
            'light': light[0] if light else 0, 'light_samples': len(light), 'croot': heads[1],
            'water_slot': water_slot}


def facts_of_triangles(image, triangles):
    """Record version 2: the facts of a TERR image made from the converter's own triangles (chunk_terrain's irregular
    path). triangles: {(i, j): [(three (x, y, z) corners in the image's units, material)]} by tile of the chunk, in
    the order the builder gave them. Every corner must lie on the 32-unit sample grid of its tile; one material per
    tile. The texture slots are read from the image's faces; generate() then has to give back the image."""
    lumps = F.read_brush_image(image)
    if lumps[0] or lumps[4]:
        raise NotGenerated('entities or visibility present')
    mins, maxs = struct.unpack_from('<3f', lumps[14], 0), struct.unpack_from('<3f', lumps[14], 12)
    heads = struct.unpack_from('<4i', lumps[14], 36)
    step = 128.0
    x0, y0, x1, y1 = mins[0], mins[1], maxs[0], maxs[1]
    nx, ny = (x1 - x0) / step, (y1 - y0) / step
    if nx != int(nx) or ny != int(ny) or nx < 1 or ny < 1 or len(lumps[14]) != 64 or heads[0] != 0:
        raise NotGenerated('not a chunk on the tile grid')
    nx, ny = int(nx), int(ny)
    if any(struct.unpack_from('<i', lumps[10], a)[0] == -5 for a in range(0, len(lumps[10]), 28)):
        raise NotGenerated('lava (its prisms are not in the record)')
    verts = [struct.unpack_from('<3f', lumps[3], a) for a in range(0, len(lumps[3]), 12)]
    edges = list(struct.iter_unpack('<HH', lumps[12]))
    surf = [v[0] for v in struct.iter_unpack('<i', lumps[13])]
    tex = list(struct.iter_unpack('<8fii', lumps[6]))
    slots = [[None] * nx for _ in range(ny)]
    water_slot = None
    for f in struct.iter_unpack('<HhihH4Bi', lumps[7]):
        vs = [verts[edges[e][0] if e >= 0 else edges[-e][1]] for e in surf[f[2]:f[2] + f[3]]]
        ti = tex[f[4]]
        if ti[9] & TEX_SPECIAL:
            if water_slot is not None and water_slot != ti[8]:
                raise NotGenerated('two water textures')
            water_slot = ti[8]
            continue
        cx, cy = sum(v[0] for v in vs) / len(vs), sum(v[1] for v in vs) / len(vs)
        i, j = int((cx - x0) // step), int((cy - y0) // step)
        if not (0 <= i < nx and 0 <= j < ny):
            raise NotGenerated('a face outside the chunk')
        if slots[j][i] is not None and slots[j][i] != ti[8]:
            raise NotGenerated('two ground textures in one tile')
        slots[j][i] = ti[8]
    heights = [[0.0] * (4 * nx + 1) for _ in range(4 * ny + 1)]
    seen = [[False] * (4 * nx + 1) for _ in range(4 * ny + 1)]
    tiles = []
    for j in range(ny):
        row = []
        for i in range(nx):
            tris = triangles.get((i, j))
            if not tris or slots[j][i] is None or slots[j][i] > 255 or len(tris) > 255:
                raise NotGenerated('a tile without its triangles or ground texture')
            if len({m for _, m in tris}) != 1:
                raise NotGenerated('two materials in one tile')
            tx, ty = x0 + i * step, y0 + j * step
            out = []
            for tri, _ in tris:
                ids = []
                for pt in tri:
                    u, v = (pt[0] - tx) / 32.0, (pt[1] - ty) / 32.0
                    if u != int(u) or v != int(v) or not (0 <= u <= 4 and 0 <= v <= 4) or \
                            tx + 32.0 * int(u) != pt[0] or ty + 32.0 * int(v) != pt[1]:
                        raise NotGenerated('a triangle corner off the 32-unit sample grid')
                    u, v = int(u), int(v)
                    gx, gy = 4 * i + u, 4 * j + v
                    z = float(pt[2])
                    if F32(z) != z:
                        raise NotGenerated('a height that is not single precision')
                    if seen[gy][gx] and heights[gy][gx] != z:
                        raise NotGenerated('two heights at one sample')
                    heights[gy][gx], seen[gy][gx] = z, True
                    ids.append(v * 5 + u)
                out.append(tuple(ids))
            row.append((slots[j][i], out))
        tiles.append(row)
    light = lumps[8]
    if light and light != bytes([light[0]]) * len(light):
        raise NotGenerated('a light lump of several values')
    return {'version': 2, 'box': (x0, y0, x1, y1), 'step': step, 'floor': mins[2], 'ceiling': maxs[2],
            'water': 0.0, 'tiles': (nx, ny), 'heights': heights, 'tile_facts': tiles,
            'node_planes': [struct.unpack_from('<i', lumps[5], a)[0] for a in range(0, len(lumps[5]), 24)],
            'planes': bytes(lumps[1]), 'texture_refs': bytes(lumps[2]), 'clipnodes': bytes(lumps[9]),
            'light': light[0] if light else 0, 'light_samples': len(light), 'croot': heads[1],
            'water_slot': water_slot}


_TILE_INDEX = {}


class _ChunkTiles:
    """{(i, j): [(corners, material)]} of one chunk's tiles, read on demand (facts_of_triangles uses .get)."""

    def __init__(self, by_tile, i0, j0, ox, oy):
        self.by_tile, self.i0, self.j0, self.ox, self.oy = by_tile, i0, j0, ox, oy

    def get(self, key, default=None):
        rows = self.by_tile.get((self.i0 + key[0], self.j0 + key[1]))
        if rows is None:
            return default
        return [([[round(pt[0], 6) - self.ox, round(pt[1], 6) - self.oy, round(pt[2], 6)] for pt in tri], m)
                for tri, m in rows]


def chunk_triangles(ground, offset):
    """The converter's own triangles of one chunk for record version 2, or None for a frame whose ground is a corner
    grid. ground: the frame's irregular ground as the frame spec keeps it (chim.build: 'triangles' tile by tile,
    'step', 'low'); offset: the chunk's terrain offset (its low corner in the frame). The corners are moved to
    chunk-local units exactly as the builder moves its terrain task (chim.build.local_terrain_task: rounded to 1e-6,
    then the offset taken off), so they are the values chunk_terrain was given."""
    if not ground or ground.get('triangles') is None:
        return None
    key = id(ground['triangles'])
    if key not in _TILE_INDEX:
        from chim.ground import tile_of
        by_tile = {}
        for tri, m in ground['triangles']:
            by_tile.setdefault(tile_of(tri, ground['step'], ground['low']), []).append((tri, m))
        _TILE_INDEX.clear()                 # one frame at a time (the pack walks frame by frame)
        _TILE_INDEX[key] = by_tile
    step, low = float(ground['step']), ground['low']
    i0, j0 = int(round((offset[0] - low[0]) / step)), int(round((offset[1] - low[1]) / step))
    return _ChunkTiles(_TILE_INDEX[key], i0, j0, offset[0], offset[1])


def _record(p, image, render):
    """The record bytes of facts P (version 1 or 2), or None when a value does not fit its field."""
    if any(k > 0xFFFF or k < 0 for k in p['node_planes']) or len(p['node_planes']) > 0xFFFF:
        return None
    nx, ny = p['tiles']
    if any(F32(h) != h for row in p['heights'] for h in row):
        return None
    hs = b''.join(struct.pack('>f', h) for row in p['heights'] for h in row)
    version = p.get('version', 1)
    if version == 1:
        if any(slot > 255 for row in p['tile_facts'] for slot, _ in row):
            return None
        tl = _pad4(bytes(b for row in p['tile_facts'] for slot, v in row for b in (slot, v)))
    else:
        table = bytes(b for row in p['tile_facts'] for slot, tris in row for b in (slot, len(tris)))
        tl = _pad4(table) + _pad4(bytes(v for row in p['tile_facts'] for _, tris in row for t in tris for v in t))
    npl = _pad4(struct.pack('>%dH' % len(p['node_planes']), *p['node_planes']))
    planes = _pad4(_lump_payload(1, p['planes']))
    clip = _pad4(_lump_payload(9, p['clipnodes']))
    refs = _pad4(p['texture_refs'])
    ws = p['water_slot'] if p['water_slot'] is not None else 0xFF
    if ws > 0xFF or p['light_samples'] > 0xFFFF:
        return None
    head = HEAD.pack(MAGIC, len(image), render, version, nx, ny, len(p['node_planes']), *p['box'], p['floor'],
                     p['ceiling'], p['water'], p['step'], p['light_samples'], p['light'], ws, len(planes), len(clip),
                     len(refs), p['croot'])
    return head + hs + tl + npl + refs + planes + clip


def encode(image, triangles=None):
    """The generated record of a TERR image, or None when this generator does not give it back byte for byte, it
    is not smaller, or does not fit the engine's smallest loading buffer with its image. Version 1 (the regular
    path) from the image alone; version 2 (the converter's own triangles) when triangles names them (see
    facts_of_triangles)."""
    image = bytes(image)
    out = None
    for version in ((1, 2) if triangles is not None else (1,)):
        try:
            p = facts_of(image) if version == 1 else facts_of_triangles(image, triangles)
            rebuilt, render = F.brush_image(generate(p))
        except (NotGenerated, ValueError, struct.error, IndexError, KeyError, ZeroDivisionError):
            continue
        if rebuilt != image:
            continue
        out = _record(p, image, render)
        if out is not None:
            break
    if out is None or len(out) >= len(image) or len(out) + len(image) > TC.EXPAND_ROOM:
        return None
    if decode(out) != image:
        raise AssertionError('generated terrain record does not give back its image')
    return out


def decode_facts(data):
    v = HEAD.unpack_from(data)
    if v[0] != MAGIC or v[3] not in (1, 2):
        raise ValueError('Not a generated terrain record')
    version = v[3]
    nx, ny, nn = v[4], v[5], v[6]
    x0, y0, x1, y1, floor_z, ceiling, water, step = v[7:15]
    samples, light, ws, n_pl, n_clip, n_refs, croot = v[15:22]
    at = HEAD.size
    gx, gy = (nx + 1, ny + 1) if version == 1 else (4 * nx + 1, 4 * ny + 1)
    heights = [[struct.unpack_from('>f', data, at + 4 * (j * gx + i))[0] for i in range(gx)] for j in range(gy)]
    at += 4 * gx * gy
    if version == 1:
        facts = [[(data[at + 2 * (j * nx + i)], data[at + 2 * (j * nx + i) + 1]) for i in range(nx)]
                 for j in range(ny)]
        at += F.align(2 * nx * ny)
    else:
        table = [(data[at + 2 * k], data[at + 2 * k + 1]) for k in range(nx * ny)]
        at += F.align(2 * nx * ny)
        facts, k, tri_at = [], 0, at
        for j in range(ny):
            row = []
            for i in range(nx):
                slot, count = table[k]
                k += 1
                row.append((slot, [tuple(data[tri_at + 3 * t:tri_at + 3 * t + 3]) for t in range(count)]))
                tri_at += 3 * count
            facts.append(row)
        at += F.align(tri_at - at)
    planes_of_nodes = list(struct.unpack_from('>%dH' % nn, data, at))
    at += F.align(2 * nn)
    refs = data[at:at + n_refs]
    at += n_refs
    planes = _lump_of(data[at:at + n_pl])
    at += n_pl
    clip = _lump_of(data[at:at + n_clip])
    n = struct.unpack_from('<i', refs)[0]
    return {'version': version, 'box': (x0, y0, x1, y1), 'step': step, 'floor': floor_z, 'ceiling': ceiling,
            'water': water, 'tiles': (nx, ny), 'heights': heights, 'tile_facts': facts,
            'node_planes': planes_of_nodes, 'planes': planes, 'texture_refs': refs[:4 + 4 * n], 'clipnodes': clip,
            'light': light, 'light_samples': samples, 'croot': croot, 'water_slot': None if ws == 0xFF else ws}


def decode(data):
    """The brush image a generated record gives (any other record is returned unchanged)."""
    data = bytes(data)
    if not is_generated(data):
        return data
    image, _ = F.brush_image(generate(decode_facts(data)))
    v = HEAD.unpack_from(data)
    if len(image) != v[1]:
        raise ValueError('Generated terrain record gives %d bytes, its head says %d' % (len(image), v[1]))
    return image
