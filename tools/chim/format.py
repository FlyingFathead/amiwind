# SPDX-License-Identifier: GPL-3.0-only
"""CHIM world format 0.5: binary layout, writers and readers.

Two byte orders, on purpose (docs/chim/WORLD_FORMAT.md):

- CHIM's own structures (file headers, directories, placement records, the
  index) are big-endian, the 68k's native order: the engine reads them with
  no swapping.
- Brush images (shared models and chunk terrain) are BSP29 lump sets in
  Quake's little-endian order, so the engine's existing section loaders
  (model.c Mod_Load* through AW_LoadBrushSection) decode them unchanged.
  Lump 2 (textures) of a brush image is a CHIM texture reference list
  instead of a miptex lump.

Everything here is pure Python on bytes; no game data is involved.
"""
import struct
import zlib

from chim import FORMAT_VERSION

MAGIC = b'CHIM'
KINDS = (b'INDX', b'FRAM', b'SECT')
HEADER = struct.Struct('>4s4sHHIIIII')          # 32 bytes, every file
SETTINGS = struct.Struct('>ffffHBBIIIIHH')        # 40 bytes, index
INDEX_TOC = struct.Struct('>IIIIIIII')            # 32 bytes, index
FILE_ENTRY = struct.Struct('>4sHhhHIIII32s')      # 60 bytes, index
MODEL_DIR = struct.Struct('>HHIIIII')             # 24 bytes, index
TEXTURE_DIR = struct.Struct('>HHIIIIHH')          # 24 bytes, index
FRAME_BLOCK = struct.Struct('>hhffffHHHHI')      # 32 bytes, frame file
CHUNK_ENTRY = struct.Struct('>HHHHIIIHHhh')       # 28 bytes, frame file
SECTOR_ENTRY = struct.Struct('>HHII')             # 12 bytes, frame file
RECORD_ENTRY = struct.Struct('>4sIII')            # 16 bytes, sector file
CHUNK_HEAD = struct.Struct('>4sHHIIHHHH')         # 24 bytes
PLACEMENT = struct.Struct('>IIIffffHbb6hHH')      # 48 bytes
CHUNK_MAGIC = b'CHK0'

# BSP29 lumps. File order of a brush image is the order AW_LoadBrushSection
# decodes them (model.c Mod_LoadBrushModel), so a streamed load reads it
# front to back without seeking, except that the clipnodes (the standing
# hull, collision only) come last: everything before them is the render part.
LUMPS = ('entities', 'planes', 'textures', 'vertexes', 'visibility', 'nodes', 'texinfo', 'faces',
         'lighting', 'clipnodes', 'leafs', 'marksurfaces', 'edges', 'surfedges', 'models')
LOADER_ORDER = (3, 12, 13, 2, 8, 1, 6, 7, 11, 4, 10, 14, 5, 0)
COLLISION_LUMPS = (9,)
FILE_ORDER = LOADER_ORDER + COLLISION_LUMPS
RECORD = {1: 20, 3: 12, 5: 24, 6: 40, 7: 20, 9: 8, 10: 28, 11: 2, 12: 4, 13: 4, 14: 64}
BSP_HEADER = 4 + 15 * 8
BSPVERSION = 29

# Classic FFS rules (hard requirements of every file the builder writes).
FFS_NAME_CHARS = 30
FFS_MAX_PACK = 1 << 30            # files stay well under 2 GiB: at most 1 GiB
FFS_MAX_DIRECTORY_ENTRIES = 72    # one FFS directory block has 72 hash chains

# A record is the owner record when its owner field equals the chunk that
# holds it; otherwise it is a reach copy. Flags:
FLAG_OVER_16_LEAVES = 1   # the drawn box reaches more than MAX_ENT_LEAFS (16) non-solid leaves
FLAG_STORY_HIDDEN = 2     # format 0.5: hidden by the opening story (legacy "aw_story_hidden", aw_opening.c)
MAX_ENT_LEAFS = 16


def crc32(data):
    return zlib.crc32(data) & 0xFFFFFFFF


def name_hash(name):
    """FNV-1a, 32 bits, over the UTF-8 name."""
    h = 0x811C9DC5
    for b in name.encode('utf-8'):
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


def align(n, a=4):
    return (n + a - 1) // a * a


def pad(data, a=4):
    return bytes(data) + bytes(align(len(data), a) - len(data))


def header(kind, count, directory_offset, data_offset, file_bytes):
    return HEADER.pack(MAGIC, kind, FORMAT_VERSION[0], FORMAT_VERSION[1], HEADER.size, count,
                       directory_offset, data_offset, file_bytes)


def read_header(data, kind=None):
    if len(data) < HEADER.size:
        raise ValueError('CHIM file shorter than its header')
    magic, k, major, minor, size, count, diro, datao, total = HEADER.unpack_from(data)
    if magic != MAGIC or k not in KINDS:
        raise ValueError('Not a CHIM file')
    if kind is not None and k != kind:
        raise ValueError('Expected a CHIM %s file, found %s' % (kind.decode(), k.decode()))
    if (major, minor) != FORMAT_VERSION:
        raise ValueError('CHIM world format %d.%d, expected %d.%d' % (major, minor, *FORMAT_VERSION))
    if size != HEADER.size or total != len(data) or not size <= diro <= datao <= total:
        raise ValueError('CHIM header offsets do not match the file')
    return {'kind': k, 'count': count, 'directory': diro, 'data': datao, 'bytes': total}


# ---------------------------------------------------------------- brush images

def brush_image(lumps):
    """BSP29 image of 15 lumps in FILE_ORDER; returns (bytes, render_bytes).

    render_bytes is the length of the prefix holding the header and every lump
    except the collision lumps, which follow it."""
    if len(lumps) != 15:
        raise ValueError('A brush image has 15 lumps')
    head = bytearray(struct.pack('<i', BSPVERSION) + bytes(120))
    body = bytearray()
    render = None
    for k in FILE_ORDER:
        if k in COLLISION_LUMPS and render is None:
            render = BSP_HEADER + len(body)
        data = bytes(lumps[k])
        if k in RECORD and len(data) % RECORD[k]:
            raise ValueError('Lump %s is not a whole number of records' % LUMPS[k])
        body += bytes(align(len(body)) - len(body))
        struct.pack_into('<ii', head, 4 + 8 * k, BSP_HEADER + len(body), len(data))
        body += data
    image = bytes(head) + bytes(body)
    return pad(image), render


def read_brush_image(data):
    """15 lump byte strings of a brush image (any lump order)."""
    if len(data) < BSP_HEADER or struct.unpack_from('<i', data)[0] != BSPVERSION:
        raise ValueError('Brush image is not BSP29')
    out = []
    for k in range(15):
        o, n = struct.unpack_from('<ii', data, 4 + 8 * k)
        if o < BSP_HEADER or n < 0 or o + n > len(data):
            raise ValueError('Brush image lump %s outside the image' % LUMPS[k])
        if k in RECORD and n % RECORD[k]:
            raise ValueError('Brush image lump %s is not a whole number of records' % LUMPS[k])
        out.append(data[o:o + n])
    return out


def render_extent(data):
    """End of the render part of a brush image (start of its collision lumps)."""
    starts = {k: struct.unpack_from('<i', data, 4 + 8 * k)[0] for k in range(15)}
    ends = {k: starts[k] + struct.unpack_from('<i', data, 8 + 8 * k)[0] for k in range(15)}
    render_end = max(ends[k] for k in range(15) if k not in COLLISION_LUMPS)
    collision_start = min(starts[k] for k in COLLISION_LUMPS)
    if collision_start < render_end:
        raise ValueError('Collision lumps must follow the render part')
    return collision_start


def texture_refs(global_ids):
    """Lump 2 of a brush image: count, then one global texture id per local index."""
    return struct.pack('<i%di' % len(global_ids), len(global_ids), *global_ids)


def read_texture_refs(lump):
    if len(lump) < 4:
        raise ValueError('Texture reference lump too short')
    n = struct.unpack_from('<i', lump)[0]
    if n < 0 or len(lump) != 4 + 4 * n:
        raise ValueError('Texture reference lump size mismatch')
    return list(struct.unpack_from('<%di' % n, lump, 4))


def texture_class(engine_name):
    """What the engine does with a texture besides drawing it: self-lit level, liquid/sky, or plain."""
    if engine_name.startswith('emit') and '_' in engine_name:
        return engine_name[:engine_name.index('_')]
    if engine_name.startswith(('*', 'sky')):
        return engine_name[:1] if engine_name.startswith('*') else 'sky'
    return ''


def texture_content(engine_name, miptex_bytes):
    """Identity of a stored texture: engine class and every mip level's pixels (not its name)."""
    return texture_class(engine_name).encode('ascii') + b'|' + bytes(miptex_bytes[40:])


# ---------------------------------------------------------------- placement records

def placement(pid, ref, model, origin, yaw, owner, cell_dx, cell_dy, box, leaves, story_hidden=False):
    """box: drawn box (mins, maxs) as stored shorts; leaves: non-solid leaves it reaches;
    story_hidden: the opening story hides it (FLAG_STORY_HIDDEN)."""
    flags = (FLAG_OVER_16_LEAVES if leaves > MAX_ENT_LEAFS else 0) | (FLAG_STORY_HIDDEN if story_hidden else 0)
    return PLACEMENT.pack(pid, ref, model, *origin, yaw, owner, cell_dx, cell_dy, *box[0], *box[1],
                          min(leaves, 65535), flags)


def read_placement(data, offset=0):
    v = PLACEMENT.unpack_from(data, offset)
    return {'pid': v[0], 'ref': v[1], 'model': v[2], 'origin': tuple(v[3:6]), 'yaw': v[6], 'owner': v[7],
            'cell_dx': v[8], 'cell_dy': v[9], 'box': (tuple(v[10:13]), tuple(v[13:16])), 'leaves': v[16],
            'flags': v[17]}


def record_args(r):
    """placement() arguments of a read record (to write it again)."""
    return (r['pid'], r['ref'], r['model'], r['origin'], r['yaw'], r['owner'], r['cell_dx'], r['cell_dy'],
            r['box'], r['leaves'], bool(r['flags'] & FLAG_STORY_HIDDEN))


# ---------------------------------------------------------------- spatial order

def hilbert_index(n, x, y):
    """Position of (x, y) on the Hilbert curve over an n x n grid (n a power of two)."""
    d = 0
    s = n // 2
    while s > 0:
        rx = 1 if x & s else 0
        ry = 1 if y & s else 0
        d += s * s * ((3 * rx) ^ ry)
        if ry == 0:
            if rx == 1:
                x, y = s - 1 - x, s - 1 - y
            x, y = y, x
        s //= 2
    return d


def spatial_order(nx, ny):
    """Chunk coordinates of an nx x ny frame in Hilbert order (pack order)."""
    n = 1
    while n < max(nx, ny):
        n *= 2
    return sorted(((x, y) for x in range(nx) for y in range(ny)), key=lambda c: hilbert_index(n, *c))


# ---------------------------------------------------------------- chunk records

def sector_order(nx, ny, s):
    """Chunk coordinates of a frame in pack order: sectors of s x s chunks in Hilbert order,
    each sector's chunks in Hilbert order inside it. Returns (chunk order, sector order)."""
    if nx % s or ny % s:
        raise ValueError('Sector size must divide the frame in chunks')
    sectors = spatial_order(nx // s, ny // s)
    inner = spatial_order(s, s)
    chunks = [(sx * s + ix, sy * s + iy) for sx, sy in sectors for ix, iy in inner]
    return chunks, sectors


def chunk_record(owned, reach, pvs, image, image_render, leaves, pvl=b''):
    """One chunk: head, placement records (owned, then reach copies), compressed
    cluster PVS row, compressed potentially-visible placement row, terrain image
    (a world BSP subtree).

    Returns (bytes, render_bytes, collision_bytes)."""
    recs = b''.join(owned) + b''.join(reach)
    image_at = align(CHUNK_HEAD.size + len(recs) + len(pvs) + len(pvl))
    head = CHUNK_HEAD.pack(CHUNK_MAGIC, len(owned), len(reach), image_at, image_render, len(pvs), leaves, len(pvl), 0)
    data = (head + recs + pvs + pvl + bytes(image_at - CHUNK_HEAD.size - len(recs) - len(pvs) - len(pvl))
            + image)
    render = image_at + image_render
    return data, render, len(data) - render


def read_chunk(raw):
    """A chunk record's parts (see chunk_record)."""
    magic, n_owned, n_reach, image_at, image_render, pvs_bytes, leaves, pvl_bytes, _ = CHUNK_HEAD.unpack_from(raw)
    if magic != CHUNK_MAGIC:
        raise ValueError('Not a chunk record')
    recs = [read_placement(raw, CHUNK_HEAD.size + k * PLACEMENT.size) for k in range(n_owned + n_reach)]
    pvs_at = CHUNK_HEAD.size + (n_owned + n_reach) * PLACEMENT.size
    if image_at < pvs_at + pvs_bytes + pvl_bytes or image_at + image_render > len(raw):
        raise ValueError('Chunk record parts overlap or overrun')
    return {'owned': recs[:n_owned], 'reach': recs[n_owned:], 'pvs': raw[pvs_at:pvs_at + pvs_bytes],
            'pvl': raw[pvs_at + pvs_bytes:pvs_at + pvs_bytes + pvl_bytes],
            'leaves': leaves, 'image': raw[image_at:], 'image_render': image_render,
            'render': image_at + image_render}


# ---------------------------------------------------------------- sector files

def sector_file(records):
    """records: [(kind, id, data)] in pack order; kind b'CHNK' (chunk index in the frame),
    b'MODL' (model id) or b'TEXR' (texture id). Every record starts on a 4-byte boundary."""
    diro = HEADER.size
    datao = align(diro + len(records) * RECORD_ENTRY.size)
    body = bytearray()
    entries = []
    for kind, rid, data in records:
        entries.append(RECORD_ENTRY.pack(kind, rid, datao + len(body), len(data)))
        body += pad(data)
    total = datao + len(body)
    out = bytearray(header(b'SECT', len(records), diro, datao, total)) + b''.join(entries)
    out += bytes(datao - len(out)) + body
    return bytes(out)


def read_sector(data):
    """Records of a sector file in file order: [{kind, id, offset, bytes, data}]; checks that the
    records tile the data area exactly (each one once, no gaps beyond 4-byte padding, no overlaps)."""
    h = read_header(data, b'SECT')
    out = []
    at = h['data']
    for i in range(h['count']):
        kind, rid, o, n = RECORD_ENTRY.unpack_from(data, h['directory'] + i * RECORD_ENTRY.size)
        if kind not in (b'CHNK', b'MODL', b'TEXR'):
            raise ValueError('Sector record %d has an unknown kind' % i)
        if o != at or o + n > len(data):
            raise ValueError('Sector record %d is not where the previous one ended' % i)
        out.append({'kind': kind, 'id': rid, 'offset': o, 'bytes': n, 'data': data[o:o + n]})
        at = align(o + n)
    if at != len(data):
        raise ValueError('Sector file has bytes after its last record')
    return out


# ---------------------------------------------------------------- frame files

def frame_file(frame, chunks, sectors):
    """frame: dict(cell, centre, low, grain, nx, ny, sector_chunks, owned_total);
    chunks: [(cx, cy, sector, offset, render, collision, owned, reach, zmin, zmax)] in pack order;
    sectors: [(sx, sy, bytes, crc)] in pack order."""
    block = FRAME_BLOCK.pack(frame['cell'][0], frame['cell'][1], frame['centre'][0], frame['centre'][1],
                             frame['low'][0], frame['low'][1], frame['grain'], frame['nx'], frame['ny'],
                             frame['sector_chunks'], frame['owned_total'])
    diro = HEADER.size + FRAME_BLOCK.size
    sectors_at = diro + len(chunks) * CHUNK_ENTRY.size
    total = sectors_at + len(sectors) * SECTOR_ENTRY.size
    out = header(b'FRAM', len(chunks), diro, sectors_at, total) + block
    out += b''.join(CHUNK_ENTRY.pack(cx, cy, sector, 0, offset, render, coll, owned, reach, zmin, zmax)
                    for cx, cy, sector, offset, render, coll, owned, reach, zmin, zmax in chunks)
    out += b''.join(SECTOR_ENTRY.pack(*s) for s in sectors)
    return out


def read_frame(data):
    h = read_header(data, b'FRAM')
    v = FRAME_BLOCK.unpack_from(data, HEADER.size)
    frame = {'cell': (v[0], v[1]), 'centre': (v[2], v[3]), 'low': (v[4], v[5]), 'grain': v[6], 'nx': v[7],
             'ny': v[8], 'sector_chunks': v[9], 'owned_total': v[10]}
    s = frame['sector_chunks']
    if not s or frame['nx'] % s or frame['ny'] % s or h['count'] != frame['nx'] * frame['ny']:
        raise ValueError('Frame file sizes do not agree')
    nsec = (frame['nx'] // s) * (frame['ny'] // s)
    if h['data'] + nsec * SECTOR_ENTRY.size != len(data):
        raise ValueError('Frame file sector table size mismatch')
    chunks = []
    for i in range(h['count']):
        cx, cy, sector, _, offset, render, coll, owned, reach, zmin, zmax = CHUNK_ENTRY.unpack_from(
            data, h['directory'] + i * CHUNK_ENTRY.size)
        chunks.append({'index': i, 'cx': cx, 'cy': cy, 'sector': sector, 'offset': offset, 'render': render,
                       'collision': coll, 'owned_count': owned, 'reach_count': reach, 'zmin': zmin, 'zmax': zmax})
    sectors = [dict(zip(('sx', 'sy', 'bytes', 'crc'), SECTOR_ENTRY.unpack_from(data, h['data'] + k * SECTOR_ENTRY.size)))
               for k in range(nsec)]
    return frame, chunks, sectors


def sector_name(index):
    return 's%02d.ccs' % index


# ---------------------------------------------------------------- the index

def index_file(settings, files, models, textures):
    """settings: dict; files: [dict(kind, sector, cell, bytes, crc, entries, path)] (frames and sectors);
    models: [(name, file, offset, bytes, render)] by model id; textures: [(name, file, offset, bytes, w, h)]
    by texture id. `file` is a row of the file table."""
    s = SETTINGS.pack(settings['draw_distance'], settings['hysteresis'], settings['collision_margin'],
                      settings['prefetch_margin'], settings['grain'], settings['terrain_light'], 0,
                      settings['placements'], settings['models'], settings['textures'], settings['frames'],
                      settings['sector_chunks'], 0)
    names = bytearray()

    def name_at(name):
        at = len(names)
        names.extend(name.encode('utf-8') + b'\0')
        return at
    rows = []
    for f in files:
        path = f['path'].encode('ascii')
        if len(path) > 31:
            raise ValueError('Index path longer than 31 bytes: ' + f['path'])
        rows.append(FILE_ENTRY.pack(f['kind'], f['sector'], f['cell'][0], f['cell'][1], 0, f['bytes'], f['crc'],
                                    f['entries'], 0, path))
    mrows = [MODEL_DIR.pack(fi, 0, o, n, r, name_at(nm), name_hash(nm)) for nm, fi, o, n, r in models]
    order = sorted(range(len(models)), key=lambda i: models[i][0])
    trows = [TEXTURE_DIR.pack(fi, 0, o, n, name_at(nm), name_hash(nm), w, hh) for nm, fi, o, n, w, hh in textures]
    files_at = HEADER.size + SETTINGS.size + INDEX_TOC.size
    models_at = files_at + len(rows) * FILE_ENTRY.size
    order_at = models_at + len(mrows) * MODEL_DIR.size
    textures_at = order_at + 4 * len(models)
    names_at = textures_at + len(trows) * TEXTURE_DIR.size
    total = align(names_at + len(names))
    toc = INDEX_TOC.pack(files_at, len(rows), models_at, len(mrows), order_at, textures_at, len(trows), names_at)
    out = (header(b'INDX', len(rows), files_at, names_at, total) + s + toc + b''.join(rows) + b''.join(mrows)
           + struct.pack('>%dI' % len(order), *order) + b''.join(trows) + bytes(names))
    return out + bytes(total - len(out))


def _name(data, offset):
    end = data.index(b'\0', offset)
    return data[offset:end].decode('utf-8')


def read_index(data):
    """(settings, files, models, textures) of an index file."""
    h = read_header(data, b'INDX')
    v = SETTINGS.unpack_from(data, HEADER.size)
    settings = dict(zip(('draw_distance', 'hysteresis', 'collision_margin', 'prefetch_margin', 'grain',
                         'terrain_light', 'reserved', 'placements', 'models', 'textures', 'frames',
                         'sector_chunks', 'reserved2'), v))
    files_at, nfiles, models_at, nmodels, order_at, textures_at, ntextures, names_at = INDEX_TOC.unpack_from(
        data, HEADER.size + SETTINGS.size)
    if (files_at != h['directory'] or nfiles != h['count'] or names_at != h['data']
            or models_at != files_at + nfiles * FILE_ENTRY.size or order_at != models_at + nmodels * MODEL_DIR.size
            or textures_at != order_at + 4 * nmodels or names_at != textures_at + ntextures * TEXTURE_DIR.size):
        raise ValueError('Index table of contents does not match its tables')
    files = []
    for i in range(nfiles):
        kind, sector, cx, cy, _, n, crc, entries, _, path = FILE_ENTRY.unpack_from(data, files_at + i * FILE_ENTRY.size)
        files.append({'kind': kind, 'sector': sector, 'cell': (cx, cy), 'bytes': n, 'crc': crc,
                      'entries': entries, 'path': path.rstrip(b'\0').decode('ascii')})
    models = []
    for i in range(nmodels):
        fi, _, o, n, r, nat, nh = MODEL_DIR.unpack_from(data, models_at + i * MODEL_DIR.size)
        name = _name(data, names_at + nat)
        if name_hash(name) != nh:
            raise ValueError('Model name hash mismatch: ' + name)
        models.append({'name': name, 'file': fi, 'offset': o, 'bytes': n, 'render': r})
    order = list(struct.unpack_from('>%dI' % nmodels, data, order_at))
    if sorted(order) != list(range(nmodels)) or [models[i]['name'] for i in order] != sorted(m['name'] for m in models):
        raise ValueError('Model name order table is not a sorted permutation')
    textures = []
    for i in range(ntextures):
        fi, _, o, n, nat, nh, w, hh = TEXTURE_DIR.unpack_from(data, textures_at + i * TEXTURE_DIR.size)
        name = _name(data, names_at + nat)
        if name_hash(name) != nh:
            raise ValueError('Texture name hash mismatch: ' + name)
        textures.append({'name': name, 'file': fi, 'offset': o, 'bytes': n, 'width': w, 'height': hh})
    return settings, files, models, textures
