# SPDX-License-Identifier: GPL-3.0-only
"""Synthetic CHIM data for the engine's host tests (no game data).

box_bsp() writes a one-model BSP29 brush image made of axis-aligned boxes:
render faces, a point hull (nodes) and the two standing hulls (clipnodes);
terrain_bsp() a chunk's terrain as a world subtree. write_world() writes
chim/ in the world format the builder writes, through the builder's own
writers (tools/chim/format.py): the index, one frame file and its sector
files, every model and texture stored once in the first sector that needs it.
"""
import struct
import zlib
from pathlib import Path

# The engine's standing hulls (model.c AW_DecodeClipnodes: the scaled player and Quake's large hull).
HULLS = (None, ((-7.32, -7.12, -16.625), (7.32, 7.12, 16.625)), ((-32, -32, -24), (32, 32, 64)))
LOADER_ORDER = (3, 12, 13, 2, 8, 1, 6, 7, 11, 4, 10, 14, 5, 0)
FILE_ORDER = LOADER_ORDER + (9,)
EMPTY, SOLID = -1, -2


def miptex(name, size=16, seed=1):
    pixels = bytes((seed * 31 + i * 7) & 255 for i in range(size * size * 85 // 64))
    offsets = (40, 40 + size * size, 40 + size * size * 5 // 4, 40 + size * size * 21 // 16)
    return name.encode().ljust(16, b'\0') + struct.pack('<2I4I', size, size, *offsets) + pixels


def box_bsp(boxes, texture_ids=None, lighting=0, entities=b'', models=1, miptex_name='surface0'):
    """boxes: [((x0, y0, z0), (x1, y1, z1))], separated by at least 72 units on x
    or y so the standing hulls stay apart; texture_ids: None for a miptex lump with
    one texture, else the CHIM reference list (one local texture).

    Each tree (point hull in the nodes, both standing hulls in the clipnodes)
    splits the boxes on axial planes in the gaps between them; a single box is
    a chain of its six planes with the outside going to the empty leaf."""
    planes, vertexes, edges, surfedges, faces, texinfo = [], [], [(0, 0)], [], [], []
    plane_index = {}

    def plane(axis, dist):
        key = (axis, float(dist))
        if key not in plane_index:
            normal = [0.0, 0.0, 0.0]
            normal[axis] = 1.0
            planes.append(struct.pack('<4fi', *normal, float(dist), axis))
            plane_index[key] = len(planes) - 1
        return plane_index[key]

    for axis in range(3):
        s, t = [(0, 1, 0), (0, 0, 1)] if axis == 0 else [(1, 0, 0), (0, 0, 1)] if axis == 1 else [(1, 0, 0), (0, 1, 0)]
        texinfo.append(struct.pack('<8fii', *s, 0.0, *t, 0.0, 0, 0))
    # Faces: one per box side (side order: x1, x0, y1, y0, z1, z0), four own edges each.
    sides = [(0, 1), (0, 0), (1, 1), (1, 0), (2, 1), (2, 0)]
    first_face = []
    for lo, hi in boxes:
        bounds = (lo, hi)
        first_face.append(len(faces))
        for axis, high in sides:
            p = plane(axis, bounds[high][axis])
            others = [x for x in range(3) if x != axis]
            first_vertex = len(vertexes)
            for a, b in ((0, 0), (0, 1), (1, 1), (1, 0)):
                v = [0.0, 0.0, 0.0]
                v[axis] = bounds[high][axis]
                v[others[0]] = bounds[a][others[0]]
                v[others[1]] = bounds[b][others[1]]
                vertexes.append(struct.pack('<3f', *v))
            first_edge = len(surfedges)
            for e in range(4):
                edges.append((first_vertex + e, first_vertex + (e + 1) % 4))
                surfedges.append(len(edges) - 1)
            faces.append(struct.pack('<HhihH4Bi', p, 0 if high else 1, first_edge, 4, axis, 0, 255, 255, 255, -1))

    def tree(hull, records, solid, empty):
        """Records: point hull (node, children in leaf form) or clip hull."""
        expand = HULLS[hull]

        def box_planes(i, axis, high):
            lo, hi = boxes[i]
            if not expand:
                return (hi if high else lo)[axis]
            return hi[axis] - expand[0][axis] if high else lo[axis] - expand[1][axis]

        def emit(rec):
            records.append(rec)
            return len(records) - 1

        def build(group):
            if len(group) == 1:
                i = group[0]
                base = len(records)
                for k, (axis, high) in enumerate(sides):
                    inside = solid if k == 5 else base + k + 1
                    front, back = (empty, inside) if high else (inside, empty)
                    emit([plane(axis, box_planes(i, axis, high)), front, back, i, k])
                return base
            best = None
            for axis in (0, 1):
                order = sorted(group, key=lambda j: boxes[j][0][axis])
                for k in range(1, len(order)):
                    gap_lo = max(boxes[j][1][axis] for j in order[:k])
                    gap_hi = min(boxes[j][0][axis] for j in order[k:])
                    if gap_hi - gap_lo >= 72:
                        score = abs(k - len(order) / 2.0)
                        if best is None or score < best[0]:
                            best = (score, axis, order[:k], order[k:], (gap_lo + gap_hi) / 2.0)
            if best is None:
                raise ValueError('boxes too close for separate hulls')
            _, axis, left, right, cut = best
            at = emit(None)
            records[at] = [plane(axis, cut), build(right), build(left), None, None]
            return at
        return build(list(range(len(boxes))))

    nodes = []
    tree(0, nodes, -1, -2)       # leaf 0 is solid (child -1), leaf 1 empty (child -2)
    node_bytes = b''
    for p, front, back, box, side in nodes:
        if box is None:
            mins, maxs, first, count = (-4096, -4096, -4096), (4096, 4096, 4096), 0, 0
        else:
            mins = [int(x) for x in boxes[box][0]]
            maxs = [int(x) + 1 for x in boxes[box][1]]
            first, count = first_face[box] + side, 1
        node_bytes += struct.pack('<ihh6h2H', p, front, back, *mins, *maxs, first, count)
    clip_bytes, roots = b'', []
    for hull in (1, 2):
        records = []
        tree(hull, records, SOLID, EMPTY)
        base = len(clip_bytes) // 8
        roots.append(base)
        for p, front, back, _, _ in records:
            kids = [c + base if c >= 0 else 0x10000 + c for c in (front, back)]
            clip_bytes += struct.pack('<iHH', p, *kids)
    leafs = struct.pack('<2i6h2H4B', SOLID, -1, *[0] * 6, 0, 0, 0, 0, 0, 0)
    leafs += struct.pack('<2i6h2H4B', EMPTY, -1, -4096, -4096, -4096, 4096, 4096, 4096, 0, 0, 0, 0, 0, 0)
    lo = [min(b[0][k] for b in boxes) for k in range(3)]
    hi = [max(b[1][k] for b in boxes) for k in range(3)]
    dmodels = b''
    for _ in range(models):
        dmodels += struct.pack('<9f7i', *lo, *hi, 0, 0, 0, 0, roots[0], roots[1], 0, 1, 0, len(faces))
    if texture_ids is None:
        textures = struct.pack('<2i', 1, 8) + miptex(miptex_name)
    else:
        textures = struct.pack('<%di' % (1 + len(texture_ids)), len(texture_ids), *texture_ids)
    lumps = [entities, b''.join(planes), textures, b''.join(vertexes), b'', node_bytes,
             b''.join(texinfo), b''.join(faces), bytes((i * 13) & 255 for i in range(lighting)), clip_bytes,
             leafs, b'', b''.join(struct.pack('<HH', *e) for e in edges),
             b''.join(struct.pack('<i', e) for e in surfedges), dmodels]
    head = bytearray(struct.pack('<i', 29) + bytes(120))
    body = bytearray()
    for k in FILE_ORDER:
        data = lumps[k]
        struct.pack_into('<ii', head, 4 + 8 * k, 124 + len(body), len(data))
        body += data
        body += bytes((4 - len(body) % 4) % 4)
    return bytes(head + body)


def terrain_bsp(box, ground, water=None, texture_id=3, light=12):
    """A chunk's terrain as format 0.1 writes it: a world BSP subtree. Node 0
    is the ground plane (back: solid leaf 0); where the ground lies below the
    water level, the water plane splits the space above it into a water leaf
    and an air leaf. Faces sit on their node's plane; each non-solid leaf
    lists the faces seen from it. Hull 1 (clipnodes): the ground raised by the
    standing hull's half height. Returns the brush image; the leaf count
    (leaf 0 not counted) is image_leaves(image)."""
    x0, y0, x1, y1 = box
    wet = water is not None and ground < water
    planes = [struct.pack('<4fi', 0.0, 0.0, 1.0, float(ground), 2)]
    if wet:
        planes.append(struct.pack('<4fi', 0.0, 0.0, 1.0, float(water), 2))
    planes.append(struct.pack('<4fi', 0.0, 0.0, 1.0, float(ground) - HULLS[1][0][2], 2))
    clip_plane = len(planes) - 1
    vertexes, edges, surfedges, faces = [], [(0, 0)], [], []

    def quad(z, plane, side, light_ofs):
        first_vertex = len(vertexes)
        corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        if side:
            corners.reverse()
        for x, y in corners:
            vertexes.append(struct.pack('<3f', x, y, z))
        first_edge = len(surfedges)
        for e in range(4):
            edges.append((first_vertex + e, first_vertex + (e + 1) % 4))
            surfedges.append(len(edges) - 1)
        faces.append(struct.pack('<HhihH4Bi', plane, side, first_edge, 4, 0 if light_ofs >= 0 else 1,
                                 0, 255, 255, 255, light_ofs))
        return len(faces) - 1
    ground_face = quad(ground, 0, 0, 0)
    leaf = lambda contents, zlo, zhi, first, count: struct.pack(
        '<2i6h2H4B', contents, -1, int(x0), int(y0), int(zlo), int(x1), int(y1), int(zhi), first, count, 0, 0, 0, 0)
    leafs = struct.pack('<2i6h2H4B', -2, -1, *[0] * 6, 0, 0, 0, 0, 0, 0)
    if wet:
        up = quad(water, 1, 0, -1)
        down = quad(water, 1, 1, -1)
        marks = [ground_face, down, up]
        # leaf 1 water (ground face + water seen from below), leaf 2 air (water from above)
        leafs += leaf(-3, ground, water, 0, 2) + leaf(-1, water, 2048, 2, 1)
        nodes = struct.pack('<ihh6h2H', 0, 1, -1, int(x0), int(y0), int(ground), int(x1), int(y1), 2048, 0, 1)
        nodes += struct.pack('<ihh6h2H', 1, -3, -2, int(x0), int(y0), int(ground), int(x1), int(y1), 2048, 1, 2)
    else:
        marks = [ground_face]
        leafs += leaf(-1, ground, 2048, 0, 1)
        nodes = struct.pack('<ihh6h2H', 0, -2, -1, int(x0), int(y0), int(ground), int(x1), int(y1), 2048, 0, 1)
    clipnodes = struct.pack('<iHH', clip_plane, 0xFFFF, 0xFFFE)     # front empty, back solid
    texinfo = struct.pack('<8fii', 1, 0, 0, 0, 0, 1, 0, 0, 0, 0)
    texinfo += struct.pack('<8fii', 1, 0, 0, 0, 0, 1, 0, 0, 0, 1)    # TEX_SPECIAL (water)
    dmodels = struct.pack('<9f7i', x0, y0, -1024.0, x1, y1, 2048.0, 0, 0, 0, 0, 0, 0, 0, 0, 0, len(faces))
    lumps = [b'', b''.join(planes), struct.pack('<2i', 1, texture_id), b''.join(vertexes), b'', nodes, texinfo,
             b''.join(faces), bytes([light]) * 256, clipnodes, leafs,
             b''.join(struct.pack('<H', m) for m in marks), b''.join(struct.pack('<HH', *e) for e in edges),
             b''.join(struct.pack('<i', e) for e in surfedges), dmodels]
    head = bytearray(struct.pack('<i', 29) + bytes(120))
    body = bytearray()
    for k in FILE_ORDER:
        data = lumps[k]
        struct.pack_into('<ii', head, 4 + 8 * k, 124 + len(body), len(data))
        body += data
        body += bytes((4 - len(body) % 4) % 4)
    return bytes(head + body)


def image_leaves(image):
    """Leaves of a brush image, leaf 0 not counted."""
    return struct.unpack_from('<i', image, 4 + 8 * 10 + 4)[0] // 28 - 1


def compress_row(row):
    """Quake vis compression: zero bytes become (0, run length)."""
    out, i = bytearray(), 0
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


def chain_bsp(boxes):
    """A placed model's point hull as the CHIM builder writes it: one run of
    six planes per convex piece; outside any plane goes on to the next piece
    (a graph whose outside branches all share the next piece), inside all six
    is solid. No faces; the texture lump is an empty reference list."""
    planes, nodes = [], []
    sides = [(0, 1), (0, 0), (1, 1), (1, 0), (2, 1), (2, 0)]
    for i, (lo, hi) in enumerate(boxes):
        nxt = 6 * (i + 1) if i + 1 < len(boxes) else -2        # -2: leaf 1, empty
        for k, (axis, high) in enumerate(sides):
            normal = [0.0, 0.0, 0.0]
            normal[axis] = 1.0
            planes.append(struct.pack('<4fi', *normal, float((hi if high else lo)[axis]), axis))
            inside = 6 * i + k + 1 if k < 5 else -1             # -1: leaf 0, solid
            front, back = (nxt, inside) if high else (inside, nxt)
            nodes.append(struct.pack('<ihh6h2H', len(planes) - 1, front, back, -4096, -4096, -4096,
                                     4096, 4096, 4096, 0, 0))
    leafs = struct.pack('<2i6h2H4B', -2, -1, *[0] * 6, 0, 0, 0, 0, 0, 0)
    leafs += struct.pack('<2i6h2H4B', -1, -1, *[0] * 6, 0, 0, 0, 0, 0, 0)
    lo = [min(b[0][k] for b in boxes) for k in range(3)]
    hi = [max(b[1][k] for b in boxes) for k in range(3)]
    clip = struct.pack('<iHH', 0, 0xFFFF, 0xFFFE)
    models = struct.pack('<9f7i', *lo, *hi, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    lumps = [b'', b''.join(planes), struct.pack('<i', 0), b'', b'', b''.join(nodes), b'', b'', b'', clip,
             leafs, b'', b'', b'', models]
    head = bytearray(struct.pack('<i', 29) + bytes(120))
    body = bytearray()
    for k in FILE_ORDER:
        struct.pack_into('<ii', head, 4 + 8 * k, 124 + len(body), len(lumps[k]))
        body += lumps[k]
        body += bytes((4 - len(body) % 4) % 4)
    return bytes(head + body)


def render_bytes(image):
    """Start of the collision lump (clipnodes) of a brush image."""
    return struct.unpack_from('<i', image, 4 + 8 * 9)[0]


# ---------------------------------------------------------------- CHIM packs

def placement(pid, ref, model, origin, yaw, owner, box, leaves=1, story_hidden=False):
    """48-byte record; box: drawn box (mins, maxs), stored rounded outward."""
    import math
    from chim import format as F
    lo = [math.floor(v) for v in box[0]]
    hi = [math.ceil(v) for v in box[1]]
    return F.placement(pid, ref, model, origin, yaw, owner, 0, 0, (lo, hi), leaves, story_hidden=story_hidden)


def pack_order(nx, ny, sector):
    """Chunk coordinates in pack order (a chunk's index is its position)."""
    from chim import format as F
    return F.sector_order(nx, ny, sector)[0]


def write_world(root, cell, low, grain, nx, ny, chunks, models, textures, owned_total, settings=None,
                sees=None, sector=3, model_textures=None, terrain_textures=(3,), sees_placement=None,
                lead=None, rows=False, refs=False, placed=False, reach=False):
    """chunks: {(cx, cy): (owned records, reach records, terrain image)};
    models: brush images by id; textures: miptex bytes by id;
    sees(a, b): chunk index a sees chunk index b (PVS rows), default all;
    sees_placement(a, pid): a view from chunk index a may see placement pid
    (format 0.3 placement rows), default all;
    model_textures: {model id: texture ids} for the home sectors;
    lead: (cell, placements) of an earlier frame of the same world (an empty frame file listed first in
    the file table): this frame's placement ids then start at that count (worlds of several frames);
    rows: sector files in one folder per sector row (format 0.6, frames of more than 64 sectors);
    refs: terrain references (format 0.7): each chunk's terrain moved to chunk-local units, stored once per
    content as a TERR record (homed where first met) and named by a CHK1 reference block.
    placed: world format 0.8 (chim.placed): the records are 56 bytes (chim.placed.placement) and every chunk head says
    so.
    reach (with placed): world format 0.9 (chim.reach): every reach copy is written as a reference to its owner
    record (the owner chunk's index and the record's position among that chunk's owned records)."""
    first = lead[1] if lead else 0
    from chim import format as F
    order, sectors = F.sector_order(nx, ny, sector)
    index = {c: i for i, c in enumerate(order)}
    model_textures = model_textures or {}
    home_model, home_texture = {}, {}
    for i, c in enumerate(order):
        s = i // (sector * sector)
        owned, reached, image = chunks[c]
        for tex in terrain_textures:
            home_texture.setdefault(tex, s)
        for rec in owned + reached:
            m = F.read_placement(rec)['model']
            if m not in home_model:
                home_model[m] = s
                for tex in model_textures.get(m, ()):
                    home_texture.setdefault(tex, s)
    for m in range(len(models)):
        home_model.setdefault(m, 0)
    for k in range(len(textures)):
        home_texture.setdefault(k, 0)
    folder = 'frames/x%+03d/y%+03d' % cell
    version = F.REFS_FORMAT_VERSION if refs else F.FORMAT_VERSION
    chunk_record, chunk_record_ref = F.chunk_record, F.chunk_record_ref
    if placed:
        from chim import placed as P
        version = P.FORMAT_VERSION
        chunk_record, chunk_record_ref = P.chunk_record, P.chunk_record_ref
    position = {}
    if reach:
        from chim import reach as RI
        version = RI.FORMAT_VERSION
        chunk_record, chunk_record_ref = RI.chunk_record, RI.chunk_record_ref
        for i, c in enumerate(order):
            for k, rec in enumerate(chunks[c][0]):
                position[F.read_placement(rec)['pid']] = (i, k)
    terrain_id, terrain_images, ref_of = {}, [], {}
    if refs:
        for i, c in enumerate(order):
            shift = (low[0] + c[0] * grain, low[1] + c[1] * grain, 0.0)
            local = F.translate_image(chunks[c][2], tuple(-v for v in shift))
            if local not in terrain_id:
                terrain_id[local] = len(terrain_images)
                terrain_images.append((local, i // (sector * sector)))
            ref_of[i] = (terrain_id[local], shift)
    sector_files, chunk_rows = [], []
    for s, (sx, sy) in enumerate(sectors):
        records = []
        for i in range(s * sector * sector, (s + 1) * sector * sector):
            c = order[i]
            owned, reached, image = chunks[c]
            if reach:
                reached = [RI.reach_ref(*position[F.read_placement(rec)['pid']]) for rec in reached]
            bits = bytearray((len(order) + 7) // 8)
            for other in range(len(order)):
                if sees is None or sees(i, other):
                    bits[other >> 3] |= 1 << (other & 7)
            pbits = bytearray((owned_total + 7) // 8)
            for pid in range(owned_total):
                if sees_placement is None or sees_placement(i, pid + first):
                    pbits[pid >> 3] |= 1 << (pid & 7)
            if refs:
                data, render, coll = chunk_record_ref(owned, reached, compress_row(bytes(bits)),
                                                        F.terrain_ref(ref_of[i][0], 0, 0, 0, 0, ref_of[i][1]),
                                                        image_leaves(image), compress_row(bytes(pbits)))
            else:
                data, render, coll = chunk_record(owned, reached, compress_row(bytes(bits)), image,
                                                    F.render_extent(image), image_leaves(image),
                                                    compress_row(bytes(pbits)))
            records.append((b'CHNK', i, data))
            chunk_rows.append([c[0], c[1], s, None, render, coll, len(owned), len(reached), -64, 64])
        records += [(b'TERR', t, img) for t, (img, home) in enumerate(terrain_images) if home == s]
        records += [(b'MODL', m, models[m]) for m in sorted(home_model) if home_model[m] == s]
        records += [(b'TEXR', k, textures[k]) for k in sorted(home_texture) if home_texture[k] == s]
        sector_files.append((records, F.sector_file(records, version)))
    terrain_at = {}
    for s, (records, data) in enumerate(sector_files):
        for r in F.read_sector(data):
            if r['kind'] == b'TERR':
                terrain_at[r['id']] = (s, r['offset'])
    for s, (records, data) in enumerate(sector_files):
        if refs:
            for k, (kind, i, rec) in enumerate(records):
                if kind == b'CHNK':
                    tid, shift = ref_of[i]
                    img = terrain_images[tid][0]
                    row = (2 if lead else 1) + terrain_at[tid][0]      # the file table: [lead], frame, sectors
                    records[k] = (kind, i, rec[:-F.TERRAIN_REF.size] + F.terrain_ref(
                        tid, row, terrain_at[tid][1], len(img), F.render_extent(img), shift))
            data = F.sector_file(records, version)
        sector_files[s] = data
    located = {}
    for s, data in enumerate(sector_files):
        for r in F.read_sector(data):
            located[(r['kind'], r['id'])] = (s, r['offset'], r['bytes'])
    for i, row in enumerate(chunk_rows):
        row[3] = located[(b'CHNK', i)][1]
    frame = dict(cell=cell, centre=(0.0, 0.0), low=low, grain=grain, nx=nx, ny=ny, sector_chunks=sector,
                 owned_total=owned_total)
    frame_bytes = F.frame_file(frame, [tuple(r) for r in chunk_rows],
                               [(sx, sy, len(d), F.crc32(d)) for (sx, sy), d in zip(sectors, sector_files)], version)
    files, lead_files = [], []
    if lead:
        lead_frame = dict(cell=lead[0], centre=(0.0, 0.0), low=low, grain=grain, nx=1, ny=1, sector_chunks=1,
                          owned_total=lead[1])
        lead_bytes = F.frame_file(lead_frame, [], [], version)
        lead_path = 'frames/x%+03d/y%+03d/frame.ccf' % lead[0]
        files.append(dict(kind=b'FRAM', sector=0, cell=lead[0], bytes=len(lead_bytes), crc=F.crc32(lead_bytes),
                          entries=0, path=lead_path))
        lead_files.append((lead_path, lead_bytes))
    files.append(dict(kind=b'FRAM', sector=0, cell=cell, bytes=len(frame_bytes), crc=F.crc32(frame_bytes),
                      entries=len(order), path=folder + '/frame.ccf'))
    rows_before = len(files)
    def sector_path(s):
        return folder + ('/r%02d/' % sectors[s][1] if rows else '/') + F.sector_name(s)
    for s, d in enumerate(sector_files):
        files.append(dict(kind=b'SECT', sector=s, cell=cell, bytes=len(d), crc=F.crc32(d),
                          entries=len(F.read_sector(d)), path=sector_path(s)))
    model_rows = []
    for m, image in enumerate(models):
        s, o, n = located[(b'MODL', m)]
        model_rows.append(('m%d' % m, rows_before + s, o, n, F.render_extent(image)))
    texture_rows = []
    for k, mip in enumerate(textures):
        s, o, n = located[(b'TEXR', k)]
        w, h = struct.unpack_from('<2I', mip, 16)
        texture_rows.append(('t%d' % k, rows_before + s, o, n, w, h))
    s = dict(draw_distance=540.0, hysteresis=96.0, collision_margin=224.0, prefetch_margin=256.0,
             terrain_light=12)
    s.update(settings or {})
    s.update(grain=grain, placements=owned_total + first, models=len(models), textures=len(textures),
             frames=2 if lead else 1, sector_chunks=sector)
    index = F.index_file(s, files, model_rows, texture_rows, version)
    out = Path(root) / 'chim'
    for rel, blob in [('world.cwi', index), (folder + '/frame.ccf', frame_bytes)] + \
            [(sector_path(k), d) for k, d in enumerate(sector_files)] + lead_files:
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
    return out


def map_bytes(entity_text):
    """A minimal BSP29 file whose entity lump is entity_text (bytes, without the closing NUL)."""
    text = entity_text + b'\0'
    header = struct.pack('<i', 29) + struct.pack('<2i', 124, len(text)) + bytes(124 - 12)
    return header + text


# ---------------------------------------------------------------- a world of region frames (type 1 crossings)

# Region frames as the CHIM builder makes them (docs/chim/CHIM_REGIONS.md): one cell of 2,048 units each,
# centred on the cell, with a 896-unit terrain margin: 15 x 15 chunks of 256 units from -1,920.
REGION_CELL, REGION_GRAIN, REGION_NX, REGION_LOW, REGION_SECTOR = 2048, 256, 15, -1920.0, 3
# The placements of every frame, frame-local: (name, x, y). 'border' sits in the chunk that straddles the
# east border (x 896..1152); 'apron' is outside the frame's cell, on its east neighbour's ground (a copy of
# the neighbour's 'twin', at the same place); every frame has a 'twin' at its own west side.
REGION_PLACEMENTS = (('centre', 0.0, 0.0), ('border', 1000.0, 0.0), ('west', -1000.0, 0.0),
                     ('twin', -948.0, 100.0), ('apron', 1100.0, 100.0))


def region_ground(gx, gy):
    """The ground height of the chunk at global chunk lattice (gx, gy): the same in every frame that holds it."""
    return float(((gx * 3 + gy * 5) % 4) * 8)


def region_chunk_lattice(cell, cx, cy):
    """Global chunk lattice coordinates of frame cell's chunk (cx, cy)."""
    step = REGION_CELL // REGION_GRAIN
    return cell[0] * step + cx, cell[1] * step + cy


def write_region_world(root, cells, settings=None, statics=True):
    """chim/ with one region frame per cell (pack order as given) and maps/w_<x>_<y>.bsp frame maps:
    terrain references (format 0.7), the REGION_PLACEMENTS of each frame (model 0), one streamed aw_flora
    static per frame (progs/f.spr, written by the C test) at frame-local (500, 500). Placement ids run on
    across frames in pack order. Returns {cell: first placement id}."""
    from chim import format as F
    models = [box_bsp([((-16, -16, 0), (16, 16, 64))], texture_ids=[0])]
    textures = [miptex('surface%d' % i, seed=i) for i in range(4)]
    version = F.REFS_FORMAT_VERSION
    order, sectors = F.sector_order(REGION_NX, REGION_NX, REGION_SECTOR)
    index_of = {c: i for i, c in enumerate(order)}
    out = Path(root) / 'chim'
    files, blobs, firsts, model_rows, texture_rows = [], [], {}, [], []
    first = 0
    renders = {}
    for frame_index, cell in enumerate(cells):
        firsts[tuple(cell)] = first
        folder = 'frames/x%+03d/y%+03d' % tuple(cell)
        frame_row = len(files)
        owned = {c: [] for c in order}
        for k, (name, x, y) in enumerate(REGION_PLACEMENTS):
            c = (int((x - REGION_LOW) // REGION_GRAIN), int((y - REGION_LOW) // REGION_GRAIN))
            gx, gy = region_chunk_lattice(cell, *c)
            z = region_ground(gx, gy)
            owned[c].append(placement(first + k, 1000 * (len(firsts)) + k, 0, (x, y, z), 0.0, index_of[c],
                                      ((x - 17, y - 17, z - 1), (x + 17, y + 17, z + 65))))
        owned_total = len(REGION_PLACEMENTS)
        terrain_id, terrain_images, ref_of = {}, [], {}
        for i, c in enumerate(order):
            x0, y0 = REGION_LOW + c[0] * REGION_GRAIN, REGION_LOW + c[1] * REGION_GRAIN
            image = terrain_bsp((x0, y0, x0 + REGION_GRAIN, y0 + REGION_GRAIN),
                                region_ground(*region_chunk_lattice(cell, *c)))
            local = F.translate_image(image, (-x0, -y0, 0.0))
            if local not in terrain_id:
                terrain_id[local] = len(terrain_images)
                terrain_images.append((local, i // (REGION_SECTOR * REGION_SECTOR), image_leaves(image)))
            ref_of[i] = (terrain_id[local], (x0, y0, 0.0), image_leaves(image))
        everything = bytes((len(order) + 7) // 8 * [255])
        pbits = bytes((owned_total + 7) // 8 * [255])
        first_sector = {}
        records_of = []
        for s in range(len(sectors)):
            records = []
            for i in range(s * REGION_SECTOR * REGION_SECTOR, (s + 1) * REGION_SECTOR * REGION_SECTOR):
                records.append([b'CHNK', i, None])
            records += [[b'TERR', t, img] for t, (img, home, _) in enumerate(terrain_images) if home == s]
            if frame_index == 0 and s == 0:
                records += [[b'MODL', m, models[m]] for m in range(len(models))]
                records += [[b'TEXR', k, textures[k]] for k in range(len(textures))]
            records_of.append(records)
        # TERR rows: where each terrain record lands (offsets do not depend on the CHNK records' contents
        # beyond their sizes, which a reference block fixes: write twice).
        def sector_blobs(terr_at):
            blobs_now = []
            for s, records in enumerate(records_of):
                recs = []
                for kind, i, data in records:
                    if kind == b'CHNK':
                        c = order[i]
                        tid, shift, leaves = ref_of[i]
                        row, offset = terr_at.get(tid, (0, 0))
                        img = terrain_images[tid][0]
                        data, renders[i], _ = F.chunk_record_ref(owned[c], [], compress_row(everything),
                                                  F.terrain_ref(tid, row, offset, len(img), F.render_extent(img),
                                                                shift),
                                                  leaves, compress_row(pbits))
                    recs.append((kind, i, data))
                blobs_now.append(F.sector_file(recs, version))
            return blobs_now
        sector_data = sector_blobs({})
        terr_at = {}
        for s, d in enumerate(sector_data):
            for r in F.read_sector(d):
                if r['kind'] == b'TERR':
                    terr_at[r['id']] = (frame_row + 1 + s, r['offset'])
        sector_data = sector_blobs(terr_at)
        located = {}
        chunk_rows = []
        for s, d in enumerate(sector_data):
            for r in F.read_sector(d):
                located[(r['kind'], r['id'])] = (s, r['offset'], r['bytes'])
        for i, c in enumerate(order):
            s, o, n = located[(b'CHNK', i)]
            chunk_rows.append((c[0], c[1], s, o, renders[i], 0, len(owned[c]), 0, -64, 64))
        if frame_index == 0:
            for m, image in enumerate(models):
                s, o, n = located[(b'MODL', m)]
                model_rows.append(('m%d' % m, frame_row + 1 + s, o, n, F.render_extent(image)))
            for k, mip in enumerate(textures):
                s, o, n = located[(b'TEXR', k)]
                w, h = struct.unpack_from('<2I', mip, 16)
                texture_rows.append(('t%d' % k, frame_row + 1 + s, o, n, w, h))
        centre = (cell[0] * 4.0 * REGION_CELL + 2.0 * REGION_CELL, cell[1] * 4.0 * REGION_CELL + 2.0 * REGION_CELL)
        frame = dict(cell=tuple(cell), centre=centre, low=(REGION_LOW, REGION_LOW), grain=REGION_GRAIN,
                     nx=REGION_NX, ny=REGION_NX, sector_chunks=REGION_SECTOR, owned_total=owned_total)
        frame_bytes = F.frame_file(frame, chunk_rows,
                                   [(sx, sy, len(d), F.crc32(d)) for (sx, sy), d in zip(sectors, sector_data)],
                                   version)
        files.append(dict(kind=b'FRAM', sector=0, cell=tuple(cell), bytes=len(frame_bytes),
                          crc=F.crc32(frame_bytes), entries=len(order), path=folder + '/frame.ccf'))
        blobs.append((folder + '/frame.ccf', frame_bytes))
        for s, d in enumerate(sector_data):
            path = folder + '/' + F.sector_name(s)
            files.append(dict(kind=b'SECT', sector=s, cell=tuple(cell), bytes=len(d), crc=F.crc32(d),
                              entries=len(F.read_sector(d)), path=path))
            blobs.append((path, d))
        # The frame map: worldspawn naming the frame, one streamed flora static.
        sx, sy = 500.0, 500.0
        c = (int((sx - REGION_LOW) // REGION_GRAIN), int((sy - REGION_LOW) // REGION_GRAIN))
        z = region_ground(*region_chunk_lattice(cell, *c))
        text = b'{\n"classname" "worldspawn"\n"_chim_frame" "%d %d"\n"_chim_streamed_statics" "%d"\n}\n' % (
            cell[0], cell[1], 1 if statics else 0)
        if statics:
            text += (b'{\n"classname" "aw_flora"\n"model" "progs/f.spr"\n"origin" "%g %g %g"\n"aw_scale" "1"\n'
                     b'"_chim_chunk" "%d"\n"_chim_box" "%g %g %g %g %g %g"\n}\n' % (
                         sx, sy, z, index_of[c], sx - 8, sy - 8, z, sx + 8, sy + 8, z + 16))
        text += b'{\n"classname" "info_player_start"\n"origin" "0 0 64"\n}\n'
        maps = Path(root) / 'maps'
        maps.mkdir(parents=True, exist_ok=True)
        (maps / ('w_%d_%d.bsp' % tuple(cell))).write_bytes(map_bytes(text))
        first += owned_total
    s = dict(draw_distance=540.0, hysteresis=96.0, collision_margin=224.0, prefetch_margin=256.0, terrain_light=12)
    s.update(settings or {})
    s.update(grain=REGION_GRAIN, placements=first, models=len(models), textures=len(textures), frames=len(cells),
             sector_chunks=REGION_SECTOR)
    for rel, blob in [('world.cwi', F.index_file(s, files, model_rows, texture_rows, version))] + blobs:
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
    return firsts


def frame_header_bytes(cell=(0, 0), pad=0, key=True):
    """A minimal BSP29 file whose entity lump is a worldspawn naming a CHIM frame ("_chim_frame" "X Y");
    key=False: the same file without the key (not a frame map). pad: extra bytes, for distinct content."""
    worldspawn = b'{\n"classname" "worldspawn"\n' + (b'"_chim_frame" "%d %d"\n' % tuple(cell) if key else b'') + b'}\n\0'
    header = struct.pack('<i', 29) + struct.pack('<2i', 124, len(worldspawn)) + bytes(124 - 12)
    return header + worldspawn + bytes(pad)
