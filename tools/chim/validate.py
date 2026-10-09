#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Validate a CHIM world and measure it.

Proves, from the files alone (plus the builder's source manifest):

- every placement is stored exactly once (one owner record; reach copies are
  identical records in exactly the other chunks its drawn box touches);
- every model and every texture is stored exactly once (unique content and
  names, each one used) and every brush image is well formed (indices in
  range, surface extents within the engine's 256-texel limit);
- every terrain face is stored exactly once: sample points of every ground
  tile are covered by exactly one ground face, and by exactly one upward water
  face where the ground lies below the water;
- every file obeys the classic FFS rules and the index matches the files.

Measures: bytes by kind against today's region maps, bytes per crossing on a
walk through the town's doors (and today's region map reads on the same
walk), largest chunk and model, model and texture counts.

    python3 tools/chim/validate.py OUT [--source OUT/chim-source.json]
        [--legacy-maps DIR --legacy-regions FILE] [--json REPORT]
"""
import argparse
import collections
import hashlib
import json
import math
import statistics
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import format as F  # noqa: E402
from chim.terrain import box_leaves, tree_depth  # noqa: E402
from chim.visibility import decompress_row, row_to_bits  # noqa: E402


class Failures(list):
    def check(self, ok, message):
        if not ok:
            self.append(message)
        return ok


# ---------------------------------------------------------------- files and FFS rules

def ffs_rules(root, fails):
    """Names <= 30 characters, few entries per directory, files below the size limit."""
    sizes = {}
    for d in [root, *[p for p in root.rglob('*') if p.is_dir()]]:
        entries = list(d.iterdir())
        fails.check(len(entries) <= F.FFS_MAX_DIRECTORY_ENTRIES,
                    'FFS: %s holds %d entries (limit %d)' % (d.name, len(entries), F.FFS_MAX_DIRECTORY_ENTRIES))
        for e in entries:
            fails.check(len(e.name) <= F.FFS_NAME_CHARS, 'FFS: name longer than 30 characters: ' + e.name)
            fails.check(all(32 < ord(ch) < 127 and ch not in ':/' for ch in e.name), 'FFS: unsafe name ' + e.name)
            if e.is_file():
                sizes[e.relative_to(root).as_posix()] = e.stat().st_size
                fails.check(e.stat().st_size <= F.FFS_MAX_PACK, 'FFS: %s larger than the 1 GiB pack limit' % e.name)
    return sizes


# ---------------------------------------------------------------- brush images

def brush_checks(lumps, ntextures, label, fails):
    """Index ranges of a brush image; returns the global texture ids it references."""
    from surface_grid import check_lumps
    refs = F.read_texture_refs(lumps[2])
    fails.check(all(0 <= t < ntextures for t in refs), label + ': texture reference outside the texture pack')
    fails.check(len(set(refs)) == len(refs), label + ': texture referenced twice')
    planes = len(lumps[1]) // 20
    verts = len(lumps[3]) // 12
    nodes = list(struct.iter_unpack('<ihh6h2H', lumps[5]))
    texinfo = list(struct.iter_unpack('<8fii', lumps[6]))
    faces = list(struct.iter_unpack('<HhihH4Bi', lumps[7]))
    clip = list(struct.iter_unpack('<iHH', lumps[9]))
    leafs = len(lumps[10]) // 28
    edges = list(struct.iter_unpack('<HH', lumps[12]))
    surfedges = [v[0] for v in struct.iter_unpack('<i', lumps[13])]
    models = list(struct.iter_unpack('<9f7i', lumps[14]))
    ok = fails.check(len(models) == 1, label + ': one dmodel expected')
    fails.check(all(t[8] < len(refs) for t in texinfo), label + ': texinfo texture outside the reference list')
    fails.check(edges[:1] == [(0, 0)] or not edges, label + ': edge 0 must be the unused dummy edge')
    fails.check(all(a < verts and b < verts for a, b in edges[1:]), label + ': edge vertex out of range')
    fails.check(all(0 < abs(e) < len(edges) for e in surfedges), label + ': surfedge out of range')
    for f in faces:
        if not fails.check(f[0] < planes and f[4] < len(texinfo) and f[2] + f[3] <= len(surfedges) and f[3] >= 3
                           and (f[9] == -1 or 0 <= f[9] < len(lumps[8])), label + ': face record out of range'):
            break
    for n in nodes:
        if not fails.check(n[0] < planes and all(c < len(nodes) if c >= 0 else -c - 1 < leafs for c in n[1:3]),
                           label + ': node out of range'):
            break
    for c in clip:
        if not fails.check(c[0] < planes and all(k < len(clip) or k >= 0xFFF0 for k in c[1:3]),
                           label + ': clipnode out of range'):
            break
    if ok:
        m = models[0]
        fails.check(m[14] == 0 and m[15] == len(faces), label + ': dmodel faces do not cover the face lump')
        h0 = m[9]
        fails.check(h0 < len(nodes) if h0 >= 0 else -h0 - 1 < leafs, label + ': point hull root out of range')
        fails.check(all(h < len(clip) if h >= 0 else h in (-1, -2) for h in m[10:13]), label + ': hull root out of range')
        # Quake walks a model's hulls only from the head node upwards (ROUTED-HULL-NODE-ORDER-33)
        from hull_chain_audit import below_head
        if 0 <= m[10] < len(clip):
            fails.check(not below_head(lambda n: clip[n][1:3], m[10]), label + ': standing hull reaches a clipnode below its head node')
        if 0 <= h0 < len(nodes):
            fails.check(not below_head(lambda n: [c for c in nodes[n][1:3] if c >= 0], h0, 1 << 30),
                        label + ': point hull reaches a node below its head node')
    try:
        check_lumps(lumps, 0)
    except ValueError as e:
        fails.append('%s: %s' % (label, e))
    return refs


def world_tree(lumps, label, fails):
    """A chunk's world subtree as plain (nodes, leaf contents) for box_leaves, checked by Quake world rules.

    Leaf 0 solid; leaf contents empty, solid or water; every face on exactly one
    node and on that node's plane; marksurfaces in range; head node 0 is node 0."""
    import numpy as np
    planes = list(struct.iter_unpack('<4fi', lumps[1]))
    nodes = list(struct.iter_unpack('<ihh6h2H', lumps[5]))
    faces = list(struct.iter_unpack('<HhihH4Bi', lumps[7]))
    leafs = list(struct.iter_unpack('<2i6h2H4B', lumps[10]))
    marks = [m[0] for m in struct.iter_unpack('<H', lumps[11])]
    d = struct.unpack('<9f7i', lumps[14][:64]) if len(lumps[14]) >= 64 else None
    ok = fails.check(bool(nodes) and d is not None and d[9] == 0, label + ': head node 0 must be the subtree root')
    fails.check(bool(leafs) and leafs[0][0] == -2, label + ': leaf 0 must be solid')
    fails.check(all(lf[0] in (-1, -2, -3) for lf in leafs), label + ': leaf contents other than empty, solid, water')
    fails.check(all(lf[8] + lf[9] <= len(marks) for lf in leafs) and all(m < len(faces) for m in marks),
                label + ': marksurfaces out of range')
    owner = [0] * len(faces)
    for n in nodes:
        for f in range(n[9], n[9] + n[10]):
            if f < len(faces):
                owner[f] += 1
                fails.check(faces[f][0] == n[0], label + ': face %d not on its node plane' % f)
    fails.check(all(k == 1 for k in owner), label + ': faces not on exactly one node')
    if not ok:
        return [], [-2]
    out = [(np.array(planes[n[0]][:3]), planes[n[0]][3], n[1], n[2]) for n in nodes]
    return out, [lf[0] for lf in leafs]


def face_polygons(lumps):
    """[(points, normal, texinfo flags, lit)] of a brush image's faces."""
    import numpy as np
    verts = np.array(list(struct.iter_unpack('<3f', lumps[3]))) if lumps[3] else np.zeros((0, 3))
    planes = list(struct.iter_unpack('<4fi', lumps[1]))
    texinfo = list(struct.iter_unpack('<8fii', lumps[6]))
    edges = list(struct.iter_unpack('<HH', lumps[12]))
    surfedges = [v[0] for v in struct.iter_unpack('<i', lumps[13])]
    out = []
    for f in struct.iter_unpack('<HhihH4Bi', lumps[7]):
        ids = [edges[e][0] if e >= 0 else edges[-e][1] for e in surfedges[f[2]:f[2] + f[3]]]
        n = np.array(planes[f[0]][:3]) * (-1 if f[1] else 1)
        out.append((verts[ids], n, texinfo[f[4]][9], f[9] >= 0))
    return out


def inside_convex_xy(poly, x, y, eps=1e-6):
    sign = 0
    n = len(poly)
    for i in range(n):
        ax, ay = poly[i][0], poly[i][1]
        bx, by = poly[(i + 1) % n][0], poly[(i + 1) % n][1]
        c = (bx - ax) * (y - ay) - (by - ay) * (x - ax)
        if abs(c) <= eps:
            return None          # on an edge: sample points avoid edges
        s = 1 if c > 0 else -1
        if sign and s != sign:
            return False
        sign = s
    return True


# ---------------------------------------------------------------- terrain coverage

SAMPLES = 7
# Sample fractions per axis differ, so no sample lies on a tile's diagonal (x = y) or edge.
FRACTIONS_X = [(i + 0.37) / SAMPLES for i in range(SAMPLES)]
FRACTIONS_Y = [(i + 0.61) / SAMPLES for i in range(SAMPLES)]


_GROUNDS = {}


def triangle_ground(source):
    """The manifest's irregular ground (format 0.5, 'terrain_triangles'), or None for a corner grid."""
    if source.get('terrain_triangles') is None:
        return None
    key = id(source['terrain_triangles'])
    if key not in _GROUNDS:
        from chim.ground import TriangleGround
        _GROUNDS.clear()
        _GROUNDS[key] = (source['terrain_triangles'], TriangleGround.from_source(source))
    return _GROUNDS[key][1]


def terrain_height(source, x, y):
    """Ground height at (x, y) from the manifest's tile corner heights (tile triangles 012, 023),
    or from its own triangles (format 0.5)."""
    tg = triangle_ground(source)
    if tg is not None:
        return tg.height(x, y)
    step, (lx, ly) = source['terrain_step'], source['terrain_low']
    i, j = int((x - lx) // step), int((y - ly) // step)
    h = source['terrain_heights']
    u, v = (x - lx - i * step) / step, (y - ly - j * step) / step
    z00, z10, z11, z01 = h[j][i], h[j][i + 1], h[j + 1][i + 1], h[j + 1][i]
    if u >= v:      # triangle (0,0) (1,0) (1,1)
        return z00 + (z10 - z00) * u + (z11 - z10) * v
    return z00 + (z11 - z01) * u + (z01 - z00) * v


def hull_contents(lumps, root, p):
    """Contents of point p in a standing hull: walk the clipnodes as SV_HullPointContents does."""
    planes, clips = lumps[1], lumps[9]
    num = root
    while num >= 0:
        pi, front, back = struct.unpack_from('<iHH', clips, 8 * num)
        n0, n1, n2, dist = struct.unpack_from('<4f', planes, 20 * pi)
        d = n0 * p[0] + n1 * p[1] + n2 * p[2] - dist
        child = front if d >= 0 else back
        num = child - 65536 if child >= 0xFFF0 else child
    return num


def ground_max(source, x0, y0, x1, y1):
    """Highest ground over the rectangle (clamped to the terrain): the source heightfield's
    maximum, found exactly at the rectangle corners, the tile corners inside it and the
    crossings of its edges with tile edges and diagonals (format 0.5: the ground's own triangles
    clipped to the rectangle)."""
    tg = triangle_ground(source)
    if tg is not None:
        return tg.max_over(x0, y0, x1, y1)
    step, (lx, ly) = source['terrain_step'], source['terrain_low']
    h = source['terrain_heights']
    hx, hy = lx + (len(h[0]) - 1) * step, ly + (len(h) - 1) * step
    eps = 1e-6
    x0, x1 = max(lx, x0), min(hx - eps, x1)
    y0, y1 = max(ly, y0), min(hy - eps, y1)
    xs = [lx + k * step for k in range(int(math.ceil((x0 - lx) / step)), int((x1 - lx) // step) + 1)]
    ys = [ly + k * step for k in range(int(math.ceil((y0 - ly) / step)), int((y1 - ly) // step) + 1)]
    points = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)] + [(x, y) for x in xs for y in ys]
    points += [(x, y) for x in xs for y in (y0, y1)] + [(x, y) for y in ys for x in (x0, x1)]
    # diagonals x - y = (lx - ly) + k * step
    base = lx - ly
    for y in (y0, y1):
        for k in range(int(math.floor((x0 - y - base) / step)), int(math.ceil((x1 - y - base) / step)) + 1):
            x = base + k * step + y
            if x0 <= x <= x1:
                points.append((x, y))
    for x in (x0, x1):
        for k in range(int(math.floor((x - y1 - base) / step)), int(math.ceil((x - y0 - base) / step)) + 1):
            y = x - base - k * step
            if y0 <= y <= y1:
                points.append((x, y))
    return max(terrain_height(source, min(max(x, lx), hx - eps), min(max(y, ly), hy - eps)) for x, y in points)


SEAM_DEPTHS = (0.25, 2.0, 5.0)        # sample distances inside a chunk edge (the box reaches 7.32)
SEAM_ALONG = (0.03, 0.2, 0.4, 0.6, 0.8, 0.97)
SEAM_TOLERANCE = 0.25                 # exact standing hull: solid just below the stand height, empty just above


def hull_seams(chunk, box, source, fails):
    """Standing hull seams (format 0.4): near every chunk edge, a player box whose bottom is
    just below the highest ground under it (the neighbour's ground included) is solid in the
    chunk's standing hull, and one just above it is empty: the box stands on the ground, not
    above it (CHIM-TERRAIN-HULL-BEVELS-33). Returns samples checked."""
    from player_hull import MINS, MAXS
    lumps = F.read_brush_image(chunk['image'])
    root = struct.unpack_from('<9f7i', lumps[14])[10]
    label = 'chunk %d,%d' % (chunk['cx'], chunk['cy'])
    x0, y0, x1, y1 = box
    samples = []
    for t in SEAM_ALONG:
        for d in SEAM_DEPTHS:
            samples += [(x0 + d, y0 + t * (y1 - y0)), (x1 - d, y0 + t * (y1 - y0)),
                        (x0 + t * (x1 - x0), y0 + d), (x0 + t * (x1 - x0), y1 - d)]
    checked = 0
    for x, y in samples:
        top = ground_max(source, x + MINS[0], y + MINS[1], x + MAXS[0], y + MAXS[1])
        stand = top - MINS[2]                       # lowest origin whose box clears the ground
        low = (x, y, stand - SEAM_TOLERANCE)
        high = (x, y, stand + SEAM_TOLERANCE)
        checked += 1
        if not fails.check(hull_contents(lumps, root, low) == -2,
                           '%s: standing hull empty at %.2f %.2f %.2f, below the ground under the box '
                           '(hull 1 seam)' % ((label,) + low)):
            return checked
        if not fails.check(hull_contents(lumps, root, high) == -1,
                           '%s: standing hull solid at %.2f %.2f %.2f, above the ground under the box '
                           '(the box would rest above it)' % ((label,) + high)):
            return checked
    return checked


def terrain_coverage(chunk, box, source, fails):
    """Each ground sample covered once by a ground face; water once where the ground is below it."""
    polys = face_polygons(F.read_brush_image(chunk['image']))
    ground = [p for p in polys if not p[2] & 1]
    water_up = [p for p in polys if p[2] & 1 and p[1][2] > 0]
    step = source['terrain_step']
    level = source['water_level']
    label = 'chunk %d,%d' % (chunk['cx'], chunk['cy'])
    tg = triangle_ground(source)
    for pts, n, flags, lit in ground:
        if tg is not None:
            # each corner on its own face's tile: no clamping error on steep source slopes
            cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
            zs = [tg.height(p[0], p[1], near=(cx, cy)) for p in pts]
        else:
            zs = [terrain_height(source, min(max(p[0], box[0] + 1e-3), box[2] - 1e-3),
                                 min(max(p[1], box[1] + 1e-3), box[3] - 1e-3)) for p in pts]
        if not fails.check(all(box[0] - 1e-3 <= p[0] <= box[2] + 1e-3 and box[1] - 1e-3 <= p[1] <= box[3] + 1e-3
                                for p in pts), label + ': ground face outside its chunk'):
            return
        fails.check(lit, label + ': ground face without lightmap')
        fails.check(max(abs(p[2] - z) for p, z in zip(pts, zs)) < 0.01, label + ': ground face off the terrain')
    tiles = 0
    for ty in range(int(box[1]), int(box[3]), step):
        for tx in range(int(box[0]), int(box[2]), step):
            tiles += 1
            for fy in FRACTIONS_Y:
                for fx in FRACTIONS_X:
                    x, y = tx + fx * step, ty + fy * step
                    hits = sum(1 for p in ground if inside_convex_xy(p[0], x, y))
                    if not fails.check(hits == 1, '%s: ground sample %.1f %.1f covered %d times' % (label, x, y, hits)):
                        return
                    wet = terrain_height(source, x, y) < level - 1e-6
                    whits = sum(1 for p in water_up if inside_convex_xy(p[0], x, y))
                    if abs(terrain_height(source, x, y) - level) > 1e-3 and not fails.check(
                            whits == (1 if wet else 0), '%s: water sample %.1f %.1f covered %d times' % (label, x, y, whits)):
                        return
    return tiles


# ---------------------------------------------------------------- the world

def load_world(out, fails):
    """Read every file of a CHIM world and check the file structure: the index lists exactly the
    files on disk, sizes and CRCs match, every sector file is tiled exactly by its records, the
    frame and index directories point at those records, and every chunk, model and texture is
    stored in exactly one record."""
    root = Path(out) / 'chim'
    sizes = ffs_rules(root, fails)
    settings, files, mdir, tdir = F.read_index((root / 'world.cwi').read_bytes())
    listed = {f['path'] for f in files} | {'world.cwi'}
    fails.check(set(sizes) == listed, 'index lists %s, disk holds %s' % (sorted(listed - set(sizes)),
                                                                         sorted(set(sizes) - listed)))
    blobs = {}
    for f in files:
        data = (root / f['path']).read_bytes() if (root / f['path']).is_file() else b''
        blobs[f['path']] = data
        fails.check(len(data) == f['bytes'] and F.crc32(data) == f['crc'], 'index size/CRC mismatch: ' + f['path'])
    records = {}                        # (file row, offset) -> record
    stored = collections.Counter()      # (kind, id, frame) -> records
    sectors = {}
    for row, f in enumerate(files):
        if f['kind'] != b'SECT':
            continue
        try:
            recs = F.read_sector(blobs[f['path']])
        except ValueError as e:
            fails.append('%s: %s' % (f['path'], e))
            continue
        fails.check(len(recs) == f['entries'], 'sector record count differs from its index row: ' + f['path'])
        kinds = [r['kind'] for r in recs]
        fails.check(kinds == sorted(kinds, key=lambda k: (b'CHNK', b'MODL', b'TEXR').index(k)),
                    f['path'] + ': records not in the order chunks, models, textures')
        for kind in (b'MODL', b'TEXR'):
            ids = [r['id'] for r in recs if r['kind'] == kind]
            fails.check(ids == sorted(ids), f['path'] + ': %s records not in id order' % kind.decode())
        sectors[(tuple(f['cell']), f['sector'])] = {'row': row, 'path': f['path'], 'records': recs}
        for r in recs:
            records[(row, r['offset'])] = r
            stored[(r['kind'], r['id'], tuple(f['cell']) if r['kind'] == b'CHNK' else None)] += 1
    fails.check(all(n == 1 for n in stored.values()), 'records stored more than once: %s'
                % sorted(k[:2] for k, n in stored.items() if n > 1)[:5])
    textures, models = [], []
    for kind, directory, out_list in ((b'TEXR', tdir, textures), (b'MODL', mdir, models)):
        for i, e in enumerate(directory):
            r = records.get((e['file'], e['offset']))
            ok = fails.check(r is not None and r['kind'] == kind and r['id'] == i and r['bytes'] == e['bytes'],
                             '%s %d: the index directory does not point at its record' % (kind.decode(), i))
            data = r['data'] if ok else b''
            item = dict(e, file=files[e['file']]['path'] if e['file'] < len(files) else '?', file_row=e['file'])
            item['miptex' if kind == b'TEXR' else 'image'] = data
            out_list.append(item)
        fails.check(sum(1 for k in stored if k[0] == kind) == len(directory),
                    '%s records without a directory entry' % kind.decode())
    frames = []
    for f in files:
        if f['kind'] != b'FRAM':
            continue
        try:
            frame, chunks, sector_rows = F.read_frame(blobs[f['path']])
        except ValueError as e:
            fails.append('%s: %s' % (f['path'], e))
            continue
        cell = tuple(f['cell'])
        fails.check(tuple(frame['cell']) == cell and len(chunks) == f['entries'],
                    'frame file does not match its index row: ' + f['path'])
        order, sector_list = F.sector_order(frame['nx'], frame['ny'], frame['sector_chunks'])
        fails.check([(c['cx'], c['cy']) for c in chunks] == order, f['path'] + ': chunks not in pack order')
        fails.check([(s['sx'], s['sy']) for s in sector_rows] == sector_list, f['path'] + ': sectors not in pack order')
        per = frame['sector_chunks'] ** 2
        for si, s in enumerate(sector_rows):
            sec = sectors.get((cell, si))
            if not fails.check(sec is not None, f['path'] + ': sector %d missing' % si):
                continue
            blob = blobs[sec['path']]
            fails.check(s['bytes'] == len(blob) and s['crc'] == F.crc32(blob),
                        f['path'] + ': sector %d size/CRC mismatch' % si)
            ids = [r['id'] for r in sec['records'] if r['kind'] == b'CHNK']
            fails.check(ids == list(range(si * per, (si + 1) * per)), sec['path'] + ': holds other chunks')
        out_chunks = []
        for c in chunks:
            sec = sectors.get((cell, c['sector']))
            r = records.get((sec['row'], c['offset'])) if sec else None
            if not fails.check(r is not None and r['kind'] == b'CHNK' and r['id'] == c['index']
                               and c['sector'] == c['index'] // per and r['bytes'] == c['render'] + c['collision'],
                               f['path'] + ': chunk %d entry does not point at its record' % c['index']):
                continue
            try:
                parts = F.read_chunk(r['data'])
            except ValueError as e:
                fails.append('chunk %d: %s' % (c['index'], e))
                continue
            fails.check(parts['render'] == c['render'] and len(parts['owned']) == c['owned_count']
                        and len(parts['reach']) == c['reach_count'], 'chunk %d: head differs from its entry' % c['index'])
            out_chunks.append(dict(c, **parts, file=sec['path']))
        frames.append((f['path'], frame, out_chunks))
    fails.check(settings['models'] == len(models) and settings['textures'] == len(textures)
                and settings['frames'] == len(frames), 'index totals do not match the files')
    return settings, files, sizes, textures, models, frames


def first_met(chunks, models_tex):
    """Model and texture ids in the order a walk through the chunks first meets them, with the sector
    each is first met in (the home rule): a chunk's ground textures, then each placement record's
    model (owned, then reach copies, by id) and that model's textures."""
    model_order, texture_order, model_home, texture_home = [], [], {}, {}

    def texture(t, sector):
        if t not in texture_home:
            texture_home[t] = sector
            texture_order.append(t)
    for c in chunks:
        for t in c['terrain_textures']:
            texture(t, c['sector'])
        for r in c['owned'] + c['reach']:
            m = r['model']
            if m not in model_home and 0 <= m < len(models_tex):
                model_home[m] = c['sector']
                model_order.append(m)
                for t in models_tex[m]:
                    texture(t, c['sector'])
    return model_order, texture_order, model_home, texture_home


def source_sections(source, frames):
    """{frame file path: its source section}. A manifest with "frames" has a section per frame
    (matched by cell); an older one-frame manifest is the section of the only frame."""
    if source is None:
        return {}
    if 'frames' not in source:
        return {frames[0][0]: source} if len(frames) == 1 else {}
    by_cell = {tuple(s['cell']): s for s in source['frames']}
    return {path: by_cell[tuple(frame['cell'])] for path, frame, _ in frames if tuple(frame['cell']) in by_cell}


def frame_of_point(world, x, y):
    """Index of the frame whose ground holds the Morrowind position (x, y), or None."""
    for k, (_, frame, _) in enumerate(world['frames']):
        lxp, lyp = (x - frame['centre'][0]) * 0.25, (y - frame['centre'][1]) * 0.25
        (lx, ly), g = frame['low'], frame['grain']
        if lx <= lxp < lx + frame['nx'] * g and ly <= lyp < ly + frame['ny'] * g:
            return k
    return None


def sky_bank_texels(textures, palette, exempt=()):
    """CHIM-TEXTURE-SPECKS-33 gate: with a palette that passes the image's sky-bank guard, no CHIM
    texture may keep texels on the seven banked entries (the image repaints them as sky colours, so
    such texels show as bright specks). Textures an opted-in texture effect changed (`exempt`
    identities, from the receipt) are left out. Returns [(texture name, texels on the bank)]."""
    import numpy as np
    from sky_palette_overlay import BANK, bank_safe
    if palette is None or not bank_safe(palette):
        return []
    banked = np.zeros(256, bool)
    banked[list(BANK)] = True
    found = []
    for t in textures:
        if t['name'] in exempt:
            continue
        mip = t['miptex']
        w, h, *offsets = struct.unpack_from('<6I', mip, 16)
        n = 0
        for level, at in enumerate(offsets):
            size = (w >> level) * (h >> level)
            if at and size and at + size <= len(mip):
                n += int(banked[np.frombuffer(mip, np.uint8, size, at)].sum())
        if n:
            found.append((t['name'], n))
    return found


def validate(out, source=None, palette=None):
    from world_chunk_estimate import placed_box
    fails = Failures()
    settings, files, sizes, textures, models, frames = load_world(out, fails)
    # textures: well formed and stored once
    tex_content = collections.Counter()
    for i, t in enumerate(textures):
        mip = t['miptex']
        name, w, h, *ofs = struct.unpack_from('<16s6I', mip)
        ok = fails.check((w, h) == (t['width'], t['height']) and w % 16 == 0 and h % 16 == 0
                         and len(mip) == 40 + w * h * 85 // 64 and ofs[0] == 40, 'texture %d: bad miptex' % i)
        engine = name.split(b'\0')[0].decode('ascii', 'replace')
        if ok:
            tex_content[F.texture_content(engine, mip)] += 1
    fails.check(all(v == 1 for v in tex_content.values()), 'textures: %d stored more than once'
                % sum(v - 1 for v in tex_content.values() if v > 1))
    fails.check(len({t['name'] for t in textures}) == len(textures), 'textures: duplicate identity names')
    receipt_path = Path(out) / 'chim-receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.is_file() else {}
    exempt = {t for e in receipt.get('texture_effects') or [] for t in e.get('textures', [])}
    banked = sky_bank_texels(textures, palette, exempt)
    fails.check(not banked, 'textures: %d texels on the sky-bank palette entries in %d textures (first: %s); '
                'the image repaints them as sky colours (CHIM-TEXTURE-SPECKS-33)'
                % (sum(n for _, n in banked), len(banked), ', '.join('%s %d' % b for b in banked[:3])))
    used_tex = set()
    # models: well formed and stored once
    model_hash = collections.Counter(hashlib.sha256(m['image']).hexdigest() for m in models)
    fails.check(all(v == 1 for v in model_hash.values()), 'models: %d stored more than once'
                % sum(v - 1 for v in model_hash.values() if v > 1))
    fails.check(len({m['name'] for m in models}) == len(models), 'models: duplicate names')
    model_bounds, models_tex = [], []
    for i, m in enumerate(models):
        lumps = F.read_brush_image(m['image'])
        fails.check(F.render_extent(m['image']) <= m['render'] + 3 and m['render'] <= F.render_extent(m['image']),
                    'model %d: render part does not end at the collision lumps' % i)
        models_tex.append(brush_checks(lumps, len(textures), 'model %d (%s)' % (i, m['name']), fails))
        used_tex.update(models_tex[-1])
        d = struct.unpack('<9f7i', lumps[14][:64]) if len(lumps[14]) >= 64 else (0,) * 16
        model_bounds.append((d[0:3], d[3:6]))
    # chunks and placements
    all_refs = set()
    used_models = set()
    terrain_tiles = 0
    seam_samples = 0
    per_chunk = []
    pids = []
    leaf_counts, chunk_counts, visibility = [], [], []
    sector_path = {(tuple(f['cell']), f['sector']): f['path'] for f in files if f['kind'] == b'SECT'}
    sections = source_sections(source, frames)
    if source is not None:
        fails.check(len(sections) == len(frames) and (len(frames) == 1 or len(source.get('frames', [])) == len(frames)),
                    'source manifest: %d frame sections for %d frames' % (len(sections), len(frames)))
    met_models, met_textures = [], []
    for path, frame, chunks in frames:
        g, (lx, ly), nx, ny = frame['grain'], frame['low'], frame['nx'], frame['ny']
        order = F.sector_order(nx, ny, frame['sector_chunks'])[0]
        owners = collections.defaultdict(list)
        copies = collections.defaultdict(list)
        trees, vis = {}, {}
        nbytes = (len(order) + 7) // 8
        frame_chunks = []
        for c in chunks:
            fails.check(F.render_extent(c['image']) >= c['image_render'], path + ': chunk %d collision before render'
                        % c['index'])
            lumps = F.read_brush_image(c['image'])
            used_tex.update(brush_checks(lumps, len(textures), 'chunk %d,%d terrain' % (c['cx'], c['cy']), fails))
            trees[(c['cx'], c['cy'])] = world_tree(lumps, 'chunk %d,%d' % (c['cx'], c['cy']), fails)
            fails.check(c['leaves'] == len(trees[(c['cx'], c['cy'])][1]) - 1,
                        'chunk %d,%d: head leaf count differs from its subtree' % (c['cx'], c['cy']))
            try:
                row = decompress_row(c['pvs'], nbytes)
                vis[(c['cx'], c['cy'])] = {order[k] for k, b in enumerate(row_to_bits(row, len(order))) if b}
            except ValueError as e:
                fails.append('chunk %d,%d: PVS row: %s' % (c['cx'], c['cy'], e))
                vis[(c['cx'], c['cy'])] = set()
            box = (lx + c['cx'] * g, ly + c['cy'] * g, lx + (c['cx'] + 1) * g, ly + (c['cy'] + 1) * g)
            if sections.get(path) is not None:
                terrain_tiles += terrain_coverage(c, box, sections[path], fails) or 0
                seam_samples += hull_seams(c, box, sections[path], fails) or 0
            for r in c['owned']:
                owners[r['ref']].append((path, c['index'], r))
                fails.check(r['owner'] == c['index'], 'placement %d: owner record names another chunk' % r['ref'])
            for r in c['reach']:
                copies[r['ref']].append((path, c['index'], r))
            for r in c['owned'] + c['reach']:
                if fails.check(r['model'] < len(models), 'placement %d: model id out of range' % r['ref']):
                    used_models.add(r['model'])
            entry = {'file': c['file'], 'frame': path, 'index': c['index'], 'cell': (c['cx'], c['cy']),
                     'sector': c['sector'], 'offset': c['offset'], 'render': c['render'],
                     'collision': c['collision'], 'faces': len(lumps[7]) // 20, 'owned': c['owned'],
                     'reach': c['reach'], 'records': c['owned'] + c['reach'],
                     'terrain_textures': F.read_texture_refs(lumps[2])}
            per_chunk.append(entry)
            frame_chunks.append(entry)
        # home rule: every model and texture lives in the sector where the pack walk first meets it
        model_order, texture_order, model_home, texture_home = first_met(frame_chunks, models_tex)
        cell = tuple(frame['cell'])
        for kind, home, items in (('model', model_home, models), ('texture', texture_home, textures)):
            wrong = [i for i, sec in home.items() if i not in (met_models if kind == 'model' else met_textures)
                     and items[i]['file'] != sector_path.get((cell, sec))]
            fails.check(not wrong, '%ss not stored in the sector that first needs them: %s' % (kind, wrong[:5]))
        met_models += [m for m in model_order if m not in met_models]
        met_textures += [t for t in texture_order if t not in met_textures]
        # owners and reach copies
        for ref, rows in owners.items():
            if not fails.check(len(rows) == 1, 'placement %d stored as owner %d times' % (ref, len(rows))):
                continue
            _, ci, r = rows[0]
            x, y = r['origin'][0], r['origin'][1]
            own = (min(nx - 1, max(0, int((x - lx) // g))), min(ny - 1, max(0, int((y - ly) // g))))
            fails.check(order[ci] == own, 'placement %d: owner chunk does not hold its origin' % ref)
            if r['model'] >= len(models):
                continue
            lo, hi = placed_box(r['origin'], (0.0, r['yaw'], 0.0), *model_bounds[r['model']])
            box = (tuple(int(math.floor(v - 1)) for v in lo), tuple(int(math.ceil(v + 1)) for v in hi))
            fails.check(tuple(r['box']) == box, 'placement %d: stored drawn box %s, model bounds give %s'
                        % (ref, r['box'], box))
            lo, hi = r['box']
            a = (min(nx - 1, max(0, int((lo[0] - lx) // g))), min(ny - 1, max(0, int((lo[1] - ly) // g))))
            b = (min(nx - 1, max(0, int((hi[0] - lx) // g))), min(ny - 1, max(0, int((hi[1] - ly) // g))))
            want = {(i, j) for i in range(a[0], b[0] + 1) for j in range(a[1], b[1] + 1)} - {own}
            leaves = sum(len(box_leaves(*trees[k], lo, hi)) for k in want | {own} if k in trees)
            fails.check(r['leaves'] == min(leaves, 65535), 'placement %d: record says %d leaves, its box reaches %d'
                        % (ref, r['leaves'], leaves))
            fails.check(bool(r['flags'] & F.FLAG_OVER_16_LEAVES) == (leaves > F.MAX_ENT_LEAFS),
                        'placement %d: over-16-leaves flag wrong' % ref)
            if sections.get(path) is not None:
                hidden = sections[path].get('story_hidden', [])
                fails.check(bool(r['flags'] & F.FLAG_STORY_HIDDEN) == (ref in hidden),
                            'placement %d: story-hidden flag differs from the source' % ref)
            leaf_counts.append(leaves)
            chunk_counts.append(len(want) + 1)
            got = [order[k] for _, k, _ in copies.get(ref, [])]
            fails.check(sorted(got) == sorted(want), 'placement %d: reach copies %s, drawn box touches %s'
                        % (ref, sorted(got), sorted(want)))
            fails.check(all(rr == r for _, _, rr in copies.get(ref, [])),
                        'placement %d: a reach copy differs from the owner record' % ref)
        fails.check(not set(copies) - set(owners), 'reach copies without an owner record: %s'
                    % sorted(set(copies) - set(owners))[:5])
        fails.check(not all_refs & set(owners), 'placements owned by two frames')
        # cluster PVS rows: itself and its neighbours, symmetric, nothing beyond the ring
        from asset_census import ring_offsets
        offs = ring_offsets(g, settings['draw_distance'] + settings['hysteresis'])
        for c, seen in vis.items():
            ring = {(c[0] + dx, c[1] + dy) for dx, dy in offs}
            near = {(c[0] + dx, c[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)} & set(vis)
            fails.check(near <= seen, 'chunk %d,%d: PVS misses itself or a neighbour' % c)
            fails.check(seen <= ring, 'chunk %d,%d: PVS marks a chunk beyond the ring' % c)
            fails.check(all(c in vis.get(b, set()) for b in seen), 'chunk %d,%d: PVS not symmetric' % c)
        # potentially visible placements: a bit row over the frame's placements (from its lowest id)
        records_of = {(c['cx'], c['cy']): c['owned'] + c['reach'] for c in chunks}
        frame_pids = [rows[0][2]['pid'] for rows in owners.values()]
        base = min(frame_pids) if frame_pids else 0
        pvl = {}
        for c in chunks:
            cell = (c['cx'], c['cy'])
            try:
                bits = row_to_bits(decompress_row(c['pvl'], (frame['owned_total'] + 7) // 8), frame['owned_total'])
            except ValueError as e:
                fails.append('chunk %d,%d: placement row: %s' % (cell[0], cell[1], e))
                continue
            seen = {base + k for k, b in enumerate(bits) if b}
            ring = {(cell[0] + dx, cell[1] + dy) for dx, dy in offs}
            cand = {r['pid'] for b in ring if b in records_of for r in records_of[b]}
            near = {r['pid'] for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                    for r in records_of.get((cell[0] + dx, cell[1] + dy), ())}
            fails.check(seen <= cand, 'chunk %d,%d: placement row marks a placement outside the ring' % cell)
            fails.check(near <= seen, 'chunk %d,%d: placement row misses a placement next to the chunk' % cell)
            pvl[cell] = seen
        visibility.append({'file': path, 'vis': vis, 'trees': trees, 'pvl': pvl,
                           'ring': {c: {(c[0] + dx, c[1] + dy) for dx, dy in offs} & set(vis) for c in vis}})
        all_refs |= set(owners)
        pids += [rows[0][2]['pid'] for rows in owners.values()]
    pids.sort()
    fails.check(pids == list(range(len(pids))) and len(pids) == settings['placements'],
                'placement ids are not 0..n-1 once each')
    fails.check(used_models == set(range(len(models))), 'models never placed: %d' % (len(models) - len(used_models)))
    fails.check(met_models == list(range(len(models))) and met_textures == list(range(len(textures))),
                'model and texture ids are not in the order the pack walk first meets them')
    fails.check(used_tex == set(range(len(textures))), 'textures never used: %d' % (len(textures) - len(used_tex)))
    if source is not None:
        from chim.cut import source_ref
        want = {int(r['ref']) for s in sections.values() for r in s['placements']}
        all_refs = {source_ref(r) for r in all_refs}         # a cut placement's pieces count as its reference
        fails.check(all_refs == want, 'placements: %d missing, %d not in the source'
                    % (len(want - all_refs), len(all_refs - want)))
        tiles = sum(s['terrain_tiles'] for s in sections.values())
        fails.check(terrain_tiles == tiles, 'terrain: %d tiles checked, source has %d' % (terrain_tiles, tiles))
    world = {'settings': settings, 'files': files, 'sizes': sizes, 'textures': textures, 'models': models,
             'frames': frames, 'chunks': per_chunk, 'leaf_counts': leaf_counts, 'chunk_counts': chunk_counts,
             'visibility': visibility, 'seam_samples': seam_samples}
    return fails, world


# ---------------------------------------------------------------- measurements

def ring_needs(ring_chunks, models, textures, model_tex, sizes):
    """What a ring needs read, in a fixed order (the cache evicts in this order): the whole files of
    the ring's sectors (by path), then models and textures homed outside them (ring order)."""
    need = {}
    files = {ch['file'] for ch in ring_chunks}
    for f in sorted(files):
        need[('s', f)] = (f, 0, sizes[f])
    for ch in ring_chunks:
        texs = list(ch['terrain_textures'])
        for r in ch['records']:
            m = models[r['model']]
            if m['file'] not in files:
                need[('m', r['model'])] = (m['file'], m['offset'], m['offset'] + m['bytes'])
            texs += model_tex[r['model']]
        for t in texs:
            tx = textures[t]
            if tx['file'] not in files:
                need[('t', t)] = (tx['file'], tx['offset'], tx['offset'] + tx['bytes'])
    return need


def walk_measure(world, source, legacy_sizes=None, legacy_regions=None, extra_caps=(0, 1 << 20, 2 << 20), cost=None,
                 frame_index=0):
    """Bytes read per chunk crossing along a walk through the source's doors (and today's map reads).

    Sector reading (format 0.2): when a chunk enters the ring, the whole file of
    its sector is read (its chunks, and the models and textures first needed
    there); a model or texture a ring chunk needs whose home sector is not in
    the ring is read on its own. Every crossing reads file by file in ascending
    order; runs are reads joined over the forward gaps the cost model calls free;
    the time is the cost model's estimate (chim.readcost). source: the frame's
    source section (its doors); frame_index: the frame walked."""
    from chim.readcost import DEFAULT, crossing_ms, merge_runs
    cost = cost or DEFAULT
    from asset_census import door_route, ring_offsets, walk_chunks
    settings = world['settings']
    path, frame, chunks = world['frames'][frame_index]
    g, (lx, ly), nx, ny = frame['grain'], frame['low'], frame['nx'], frame['ny']
    by_cell = {c['cell']: c for c in world['chunks'] if c['frame'] == path}
    models, textures, sizes = world['models'], world['textures'], world['sizes']
    model_tex = [F.read_texture_refs(F.read_brush_image(m['image'])[2]) for m in models]

    class Grid:
        grain = g

        @staticmethod
        def index(x, y):
            return (min(nx - 1, max(0, int((x - lx) // g))), min(ny - 1, max(0, int((y - ly) // g))))
    route = door_route(source['doors'])
    seq = walk_chunks(route, Grid)
    reach = settings['draw_distance'] + settings['hysteresis']
    ring_off = ring_offsets(g, reach)

    def items(c):
        ring = [(c[0] + dx, c[1] + dy) for dx, dy in ring_off if (c[0] + dx, c[1] + dy) in by_cell]
        return ring_needs([by_cell[k] for k in ring], models, textures, model_tex, sizes)
    memo = {}
    replays = {}
    out = {'route_stops': len(route), 'route_length_units': round(sum(math.hypot(b[0] - a[0], b[1] - a[1])
                                                                       for a, b in zip(route, route[1:])), 1),
           'chunks_visited': len(seq), 'ring_chunks': len(ring_off)}
    for cap in extra_caps:
        cache = collections.OrderedDict()
        loads, runs, resident, cold, times, files = [], [], [], None, [], []
        replay = []
        for step, c in enumerate(seq):
            if c not in memo:
                memo[c] = items(c)
            need = memo[c]
            read = []
            for key, rng in need.items():
                if key in cache:
                    cache.move_to_end(key)
                else:
                    cache[key] = rng
                    read.append(rng)
            size = sum(b - a for _, a, b in read)
            rr = merge_runs(read, cost['skip_free_bytes'])
            replay.append({'crossing': step, 'runs': [list(r) for r in rr],
                           'estimated_ms': round(crossing_ms(rr, cost), 3)})
            if step == 0:
                cold = size
                cold_ms = crossing_ms(rr, cost)
            else:
                loads.append(size)
                runs.append(len(rr))
                files.append(len({r[0] for r in rr}))
                times.append(crossing_ms(rr, cost))
            need_bytes = sum(b - a for _, a, b in need.values())
            resident.append(need_bytes)
            total = sum(b - a for _, a, b in cache.values())
            for key in list(cache):
                if total <= need_bytes + cap:
                    break
                if key not in need:
                    a = cache.pop(key)
                    total -= a[2] - a[1]
        moving = [x for x in loads if x]
        out['extra_%d' % cap] = {
            'cold_bytes': cold, 'crossings': len(loads), 'crossings_reading': len(moving),
            'bytes_read': sum(loads), 'per_crossing_p50': statistics.median(moving) if moving else 0,
            'per_crossing_max': max(loads) if loads else 0,
            'seek_runs_p50': statistics.median([r for r, x in zip(runs, loads) if x]) if moving else 0,
            'seek_runs_max': max(runs) if runs else 0,
            'files_per_crossing_p50': statistics.median(files) if files else 0,
            'estimated_ms_p50': round(statistics.median(times), 1) if times else 0,
            'estimated_ms_max': round(max(times), 1) if times else 0,
            'estimated_ms_total': round(sum(times)), 'cold_estimated_ms': round(cold_ms, 1),
            'resident_p50': statistics.median(resident), 'resident_max': max(resident)}
        replays[cap] = replay
    if legacy_sizes and legacy_regions:
        from town_regions import owner
        entries = [{'name': n, 'core': [r['core'][0:2], r['core'][2:4]]} for n, r in legacy_regions.items()]
        cur, reads, names = None, [], []
        for (x0, y0), (x1, y1) in zip(route, route[1:] or route):
            n = max(1, int(math.hypot(x1 - x0, y1 - y0) / 16.0))
            for k in range(n + 1):
                pnt = (x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n)
                o = owner(pnt, entries, cur, settings['hysteresis'])
                if o is not None and o != cur:
                    if cur is not None:
                        reads.append(legacy_sizes[entries[o]['name']])
                        names.append(entries[o]['name'])
                    cur = o
        legacy_ms = [cost['open_ms'] + n / 1024 * cost['seq_ms_per_kib'] for n in reads]
        out['legacy'] = {'crossings': len(reads), 'bytes_read': sum(reads),
                         'per_crossing_p50': statistics.median(reads) if reads else 0,
                         'per_crossing_max': max(reads) if reads else 0,
                         'estimated_ms_p50': round(statistics.median(legacy_ms), 1) if reads else 0,
                         'estimated_ms_max': round(max(legacy_ms), 1) if reads else 0,
                         'estimated_ms_total': round(sum(legacy_ms))}
        replays['legacy'] = [{'crossing': k + 1, 'runs': [['%s.bsp' % n, 0, b, 1]],
                              'estimated_ms': round(ms, 3)} for k, (n, b, ms) in enumerate(zip(names, reads, legacy_ms))]
    out['cost_model'] = cost
    out['_replay'] = replays
    return out


def visibility_report(world):
    """What the cluster PVS leaves to draw, per chunk as the player's chunk.

    visible share: chunks in the PVS over chunks in the ring; world faces: ground
    and water faces of the visible chunks; entity faces: faces of the models
    placed by the visible chunks (each placement once); placements over 16 leaves."""
    model_faces = [len(F.read_brush_image(m['image'])[7]) // 20 for m in world['models']]
    chunks_of = collections.defaultdict(dict)          # frame file -> {cell: chunk}
    for c in world['chunks']:
        chunks_of[c['frame']][c['cell']] = c
    shares, frame_shares, world_faces, entity_faces, sent, sent_over, depths = [], [], [], [], [], [], []
    pvl_sent, pvl_faces, pvl_over = [], [], []
    record_of = {r['pid']: r for c in world['chunks'] for r in c['owned']}
    for v in world['visibility']:
        by_cell = chunks_of[v['file']]
        for c, seen_p in v.get('pvl', {}).items():
            pvl_sent.append(len(seen_p))
            pvl_faces.append(sum(model_faces[record_of[q]['model']] for q in seen_p if q in record_of))
            pvl_over.append(sum(1 for q in seen_p if q in record_of and record_of[q]['flags'] & F.FLAG_OVER_16_LEAVES))
        for c, seen in v['vis'].items():
            ring = v['ring'][c]
            shares.append(len(seen) / len(ring))
            frame_shares.append(len(seen) / len(v['vis']))
            world_faces.append(sum(by_cell[b]['faces'] for b in seen))
            placed = {}
            for b in seen:
                for r in by_cell[b]['records']:
                    placed[r['pid']] = r
            entity_faces.append(sum(model_faces[r['model']] for r in placed.values()))
            sent.append(len(placed))
            sent_over.append(sum(1 for r in placed.values() if r['flags'] & F.FLAG_OVER_16_LEAVES))
        depths += [tree_depth(nodes) for nodes, _ in v['trees'].values()]
    grid_depth = max(math.ceil(math.log2(max(1, f['nx']))) + math.ceil(math.log2(max(1, f['ny'])))
                     for _, f, _ in world['frames'])
    totals = [w + e for w, e in zip(world_faces, entity_faces)]
    lc, cc = sorted(world['leaf_counts']), sorted(world['chunk_counts'])

    def pct(v, q):
        v = sorted(v)
        return v[min(len(v) - 1, int(q * (len(v) - 1)))] if v else 0
    return {
        'visible_share_of_ring': {'mean': round(statistics.mean(shares), 4), 'p50': round(pct(shares, .5), 4),
                                  'min': round(min(shares), 4)},
        'visible_share_of_frame': {'mean': round(statistics.mean(frame_shares), 4), 'max': round(max(frame_shares), 4)},
        'world_faces_per_view': {'p50': pct(world_faces, .5), 'max': max(world_faces)},
        'entity_faces_per_view': {'p50': pct(entity_faces, .5), 'max': max(entity_faces)},
        'world_face_share': round(sum(world_faces) / sum(totals), 4) if sum(totals) else None,
        'placements_sent_per_view': {'p50': pct(sent, .5), 'max': max(sent)},
        'placements_over_16_leaves': sum(1 for x in lc if x > F.MAX_ENT_LEAFS),
        'placements_over_16_leaves_sent_per_view': {'p50': pct(sent_over, .5), 'max': max(sent_over)},
        'leaves_per_placement': {'p50': pct(lc, .5), 'p95': pct(lc, .95), 'max': lc[-1] if lc else 0},
        'chunks_per_placement': {'p50': pct(cc, .5), 'p95': pct(cc, .95), 'max': cc[-1] if cc else 0},
        'chunk_bsp_depth': {'max': max(depths) if depths else 0, 'p50': pct(depths, .5)},
        'frame_grid_depth': grid_depth,
        'world_depth_max': grid_depth + (max(depths) if depths else 0),
        'placement_list': {
            'placements_per_view': {'p50': pct(pvl_sent, .5), 'max': max(pvl_sent) if pvl_sent else 0},
            'entity_faces_per_view': {'p50': pct(pvl_faces, .5), 'max': max(pvl_faces) if pvl_faces else 0},
            'over_16_leaves_per_view': {'p50': pct(pvl_over, .5), 'max': max(pvl_over) if pvl_over else 0},
            'placements_share_of_chunk_rows': round(sum(pvl_sent) / sum(sent), 4) if sum(sent) else None,
            'faces_share_of_chunk_rows': round(sum(pvl_faces) / sum(entity_faces), 4) if sum(entity_faces) else None}}


def camera_report(world, cameras):
    """Per camera (name, Morrowind x, y): placements and model faces the views would send:
    every placement of the ring, the chunk rows' placements, and the placement list."""
    model_faces = [len(F.read_brush_image(m['image'])[7]) // 20 for m in world['models']]
    record_of = {r['pid']: r for c in world['chunks'] for r in c['owned']}
    out = []
    for name, x, y in cameras:
        k = frame_of_point(world, x, y)
        if k is None:
            out.append({'camera': name, 'frame': None})
            continue
        path, frame, _ = world['frames'][k]
        by_cell = {c['cell']: c for c in world['chunks'] if c['frame'] == path}
        vis = world['visibility'][k]
        g, (lx, ly) = frame['grain'], frame['low']
        lxp, lyp = (x - frame['centre'][0]) * 0.25, (y - frame['centre'][1]) * 0.25
        cell = (min(frame['nx'] - 1, max(0, int((lxp - lx) // g))), min(frame['ny'] - 1, max(0, int((lyp - ly) // g))))

        def count(chunks):
            pids = {r['pid'] for b in chunks for r in by_cell[b]['records']}
            return len(pids), sum(model_faces[record_of[q]['model']] for q in pids)
        ring_n, ring_f = count(vis['ring'][cell])
        pvs_n, pvs_f = count(vis['vis'][cell])
        pl = vis['pvl'].get(cell, set())
        out.append({'camera': name, 'frame': list(frame['cell']), 'local': [round(lxp, 1), round(lyp, 1)],
                    'chunk': list(cell),
                    'ring_placements': ring_n, 'ring_faces': ring_f, 'chunk_rows_placements': pvs_n,
                    'chunk_rows_faces': pvs_f, 'placement_list': len(pl),
                    'placement_list_faces': sum(model_faces[record_of[q]['model']] for q in pl)})
    return out


def measure(world, source=None, legacy_maps=None, legacy_regions=None, cost=None, cameras=()):
    files = world['files']
    by_kind = collections.Counter()
    for f in files:
        by_kind[f['kind'].decode()] += f['bytes']
    by_kind['INDX'] += world['sizes'].get('world.cwi', 0)
    chunks = world['chunks']
    biggest = max(chunks, key=lambda c: c['render'] + c['collision'])
    big_model = max(world['models'], key=lambda m: m['bytes'])
    records = sum(len(c['records']) for c in chunks)
    res = {'bytes_total': sum(by_kind.values()), 'bytes_by_kind': dict(by_kind),
           'models': len(world['models']), 'textures': len(world['textures']), 'chunks': len(chunks),
           'placements': world['settings']['placements'], 'placement_records': records,
           'reach_copies': records - world['settings']['placements'],
           'largest_chunk': {'cell': list(biggest['cell']), 'render': biggest['render'],
                             'collision': biggest['collision']},
           'largest_model': {'name': big_model['name'], 'bytes': big_model['bytes'], 'render': big_model['render']},
           'model_bytes': {'render': sum(m['render'] for m in world['models']),
                           'collision': sum(m['bytes'] - m['render'] for m in world['models'])},
           'chunk_bytes': {'render': sum(c['render'] for c in chunks), 'collision': sum(c['collision'] for c in chunks)},
           'sectors': sum(1 for f in files if f['kind'] == b'SECT'),
           'largest_sector_bytes': max([f['bytes'] for f in files if f['kind'] == b'SECT'] or [0])}
    res['visibility'] = visibility_report(world)
    if cameras:
        res['cameras'] = camera_report(world, cameras)
    legacy_sizes = regions = None
    if legacy_maps and legacy_regions:
        from world_chunk_estimate import read_regions
        regions = read_regions(Path(legacy_regions).read_text(encoding='utf-8'))
        legacy_sizes = {n: (Path(legacy_maps) / (n + '.bsp')).stat().st_size for n in regions}
        res['legacy'] = {'regions': len(regions), 'bytes_total': sum(legacy_sizes.values()),
                         'ratio_legacy_over_chim': round(sum(legacy_sizes.values()) / res['bytes_total'], 2)}
    sections = source_sections(source, world['frames'])
    walks = {}
    for k, (path, frame, _) in enumerate(world['frames']):
        section = sections.get(path)
        if section and section.get('doors'):
            walks['%d,%d' % tuple(frame['cell'])] = walk_measure(world, section, legacy_sizes if k == 0 else None,
                                                                 regions if k == 0 else None, cost=cost, frame_index=k)
    if walks:
        res['walk'] = next(iter(walks.values()))       # the first frame's (pack order)
        if len(walks) > 1:
            res['walks'] = walks
    return res


def write_replays(folder, replays, volume, legacy_volume='AW_LEGACY:'):
    """replay-extra<N>.txt (`awbench replay` lists: "X crossing", "R path offset bytes") and
    replay-extra<N>.json (the cost model's estimate per crossing) for every cache size."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    from chim.readcost import features
    for cap, rows in replays.items():
        name = 'replay-legacy' if cap == 'legacy' else 'replay-extra%d' % cap
        prefix = legacy_volume if cap == 'legacy' else volume + 'chim/'
        lines = []
        for row in rows:
            lines.append('X %d' % row['crossing'])
            for f, a, b, _ in row['runs']:
                lines.append('R %s%s %d %d' % (prefix, f, a, b - a))
        (folder / (name + '.txt')).write_bytes(('\n'.join(lines) + '\n').encode('ascii'))
        (folder / (name + '.json')).write_text(
            json.dumps([dict(features(r['runs']), crossing=r['crossing'], estimated_ms=r['estimated_ms'])
                        for r in rows], indent=0) + '\n', encoding='utf-8', newline='\n')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('out', type=Path, help='builder output folder (holds chim/)')
    ap.add_argument('--source', type=Path, help='source manifest (default OUT/chim-source.json if present)')
    ap.add_argument('--legacy-maps', type=Path, help="folder with today's region maps")
    ap.add_argument('--legacy-regions', type=Path, help="today's region table (name core coverage rows)")
    ap.add_argument('--json', type=Path, help='write the report here')
    ap.add_argument('--palette', type=Path,
                    help='game palette of the build (id1/gfx/palette.lmp): checks that no texture keeps texels on '
                         "the image's sky-bank entries (CHIM-TEXTURE-SPECKS-33)")
    ap.add_argument('--read-cost', type=Path, help='cost model JSON (tools/chim/readcost.py); default: built in')
    ap.add_argument('--camera', nargs=3, action='append', default=[], metavar=('NAME', 'X', 'Y'),
                    help='report the placements a view at this Morrowind position sends (repeatable)')
    ap.add_argument('--replay-dir', type=Path,
                    help='write the walk\'s reads per crossing for `awbench replay` (one list per cache size)')
    ap.add_argument('--replay-volume', default='AW_CHIM:',
                    help='Amiga path of the folder holding chim/ (default AW_CHIM:)')
    ap.add_argument('--replay-legacy-volume', default='AW_LEGACY:',
                    help='Amiga path of the folder holding today\'s region maps (default AW_LEGACY:)')
    a = ap.parse_args(argv)
    src_path = a.source or (a.out / 'chim-source.json')
    source = json.loads(src_path.read_text(encoding='utf-8')) if src_path.is_file() else None
    fails, world = validate(a.out, source, a.palette.read_bytes() if a.palette else None)
    report = {'ok': not fails, 'failures': fails[:200], 'failure_count': len(fails),
              'source_checked': source is not None}
    if not fails:
        cost = json.loads(a.read_cost.read_text(encoding='utf-8')) if a.read_cost else None
        cameras = [(n, float(x), float(y)) for n, x, y in a.camera]
        report['measured'] = measure(world, source, a.legacy_maps, a.legacy_regions, cost, cameras)
        replays = report['measured'].get('walk', {}).pop('_replay', {})
        if a.replay_dir:
            write_replays(a.replay_dir, replays, a.replay_volume, a.replay_legacy_volume)
    text = json.dumps(report, indent=1, sort_keys=True) + '\n'
    if a.json:
        a.json.write_bytes(text.encode('utf-8'))
    sys.stdout.write(text)
    return 0 if not fails else 1


if __name__ == '__main__':
    raise SystemExit(main())
