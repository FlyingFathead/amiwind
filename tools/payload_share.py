#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Store repeated content of the boot payload once, as the last step before the disk layout.

Three methods, each a builder option that is on by default (build.py --file-aliases on and --shared-skins on
since v0.0.47, --shared-shapes on since v0.0.63; off keeps every copy, the method before; docs/PAYLOAD_SHARING.md):

file aliases (IMAGE-DUPLICATE-FILES-46): byte-identical files (SHA-256 of the content) of the kinds the engine
    opens through its file search (models, sounds, sprites, animation layouts and item tags: COM_FindFile) are
    stored once. The other names go into id1/file-aliases.txt; when the
    engine finds no file of a name it looks the name up there and opens the stored copy (aw_file_alias.c). Amiga
    FFS has no links, so a name table is the only way to give one stored file several names.

shared skins (IMAGE-ACTOR-SKIN-REPEATS-46): a single-skin actor model (progs/a_*.mdl) whose skin pixels another
    model repeats stores them once in progs/skins/<16 hex>.awk; the model keeps its header and says where its
    skin is (skin type "AWSK", the 16 hex digits of the pixels' SHA-256, the pixel count) in place of the
    pixels. The engine's alias loaders read the pixels from that file into the same place (model.c), so the
    decoded model is byte-identical and the game holds no more memory than before. expand_shared_skin is the
    reference of what the engine rebuilds.

shared shapes (IMAGE-BIGGER-THAN-ORIGINAL-62): an actor model (progs/*.mdl: a_, n_, c_, the player bodies, the
    view models) whose texture coordinates and triangles (the ST block, numverts x 12 bytes, and the triangle
    block, numtris x 16 bytes) another model repeats stores the two blocks once, ST then triangles, in
    progs/shapes/<16 hex>.aws1; the model keeps "AWSH", the 16 hex digits of the blocks' SHA-256, the ST bytes and
    the triangle bytes (28 bytes, little-endian) in their place. Every model of a repeated shape points to the
    file. The engine's alias loaders read the blocks from that file into the same place before decoding
    (model.c AW_SharedShapeExpand, model_alias_stream.inc), so the decoded model is byte-identical and resident
    memory is unchanged. It runs after the shared skins (a model can carry both references) and before the file
    aliases. expand_shared_shape is the reference of what the engine rebuilds.

skin tiles (IMAGE-BIGGER-THAN-ORIGINAL-62, method B; EXPERIMENTAL, build.py --skin-tiles on, off by default): the
    single inline skins of progs/a_*.mdl and n_*.mdl are cut into 16x16 tiles; every distinct tile is stored once in
    one pool, chunk files of 65,536 tiles (progs/tiles/<16 hex>-<chunk>.awtp), and each model keeps "AWTL", the
    pool's 16 hex digits, the pixel and tile counts and one u32 tile number per tile in place of its pixels. The
    engine's file loader rebuilds the model before decoding (model.c AW_TiledSkinExpand). It runs after the
    shared shapes and before the file aliases. expand_tiled_skin is the reference of what the engine rebuilds.

Usage (read only, a dry measurement over a staged payload; nothing is written):

    payload_share.py measure BOOT [--file-aliases] [--shared-skins] [--shared-shapes] [--skin-tiles] [--jobs N]
                             [--json OUT]
    payload_share.py identity ID1 [--jobs N] [--json OUT]   (every shared-shape form rebuilds its model)
"""
import argparse
import fnmatch
import hashlib
import json
from pathlib import Path
import struct
import sys

ALIAS_FILE = 'file-aliases.txt'                        # id1-relative
ALIAS_MAGIC = 'AWALIAS1'
# Kinds the engine opens through COM_FindFile. Not the soundtrack (.mws): aw_music.c opens its tracks by path.
ALIAS_KINDS = ('.mdl', '.wav', '.spr', '.anm', '.tag')
ALIAS_MIN_BYTES = 4096        # smaller repeats cost the game more table memory than they save on disk
ALIAS_NAME_LIMIT = 63         # MAX_QPATH 64 with its terminator

SKIN_DIR = 'progs/skins'
SKIN_EXT = '.awk'
SKIN_PATTERNS = ('progs/a_*.mdl',)
SKIN_TYPE = b'AWSK'           # skin type of a shared skin; read little-endian it is 0x4B535741
SKIN_SINGLE = 0
MDL_HEADER = 84
SKIN_REF = 4 + 16 + 4         # type, 16 hex digits, pixel count: in place of type + pixels
SKIN_FULL_LIMIT = 512 * 1024  # the engine's alias file staging limit (model.c AW_ALIAS_STAGING_LIMIT)

SHAPE_DIR = 'progs/shapes'
SHAPE_EXT = '.aws1'
SHAPE_PATTERNS = ('progs/*.mdl',)   # top level of progs/ only (fnmatch's * also matches /: checked in plan_shapes)
SHAPE_TYPE = b'AWSH'          # in place of the ST block; read little-endian 0x48535741, never an onseam value (0, 0x20)
SHAPE_REF = 4 + 16 + 4 + 4    # type, 16 hex digits, ST bytes, triangle bytes: in place of both blocks
ST_BYTES = 12                 # stvert_t: onseam, s, t
TRI_BYTES = 16                # dtriangle_t: facesfront, 3 vertex indices
NPC_LOD_MANIFEST = 'progs/npc-lod.txt'   # aw_npc_lod.c checks those files' byte sizes: their models keep their blocks

TILE_DIR = 'progs/tiles'
TILE_EXT = '.awtp'            # .awp is taken (animation layouts): "AmiWind tile pool"
TILE_PATTERNS = ('progs/a_*.mdl', 'progs/n_*.mdl')
TILE_TYPE = b'AWTL'           # skin type of a tiled skin; read little-endian 0x4C545741
TILE = 16                     # a tile is 16 x 16 pixels, stored as 16 rows of 16 bytes
TILE_BYTES = TILE * TILE
TILE_CHUNK = 65536            # tiles per pool chunk file (16 MiB): a tile number's high 16 bits name the chunk
TILE_GAP = 8                  # model.c AW_TILE_GAP: tiles read through (not sought over) between two wanted ones
TILE_RUN = 64                 # model.c AW_TILE_RUN: tiles per read (a 16 KiB transient buffer)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _hashes(paths, jobs):
    try:
        from build_parallel import hash_files
        return hash_files(paths, jobs)
    except ImportError:                                  # standalone measurement
        return [sha256(Path(p).read_bytes()) for p in paths]


# ---- shared skins

def skin_of(raw):
    """(offset, pixel bytes) of a single-skin model's pixels, or None for anything else (groups, several skins,
    a shared skin already, another format)."""
    if len(raw) < MDL_HEADER + 4 or raw[:4] != b'IDPO' or struct.unpack_from('<i', raw, 4)[0] != 6:
        return None
    count, width, height = struct.unpack_from('<3i', raw, 48)
    if count != 1 or width < 1 or height < 1 or width & 3:
        return None
    if raw[MDL_HEADER:MDL_HEADER + 4] != struct.pack('<i', SKIN_SINGLE):
        return None
    pixels = width * height
    if MDL_HEADER + 4 + pixels > len(raw):
        return None
    return MDL_HEADER + 4, pixels


def skin_name(digest):
    return SKIN_DIR + '/' + digest[:16] + SKIN_EXT


def shared_model(raw, digest):
    """The stored form of RAW (a single-skin model) whose pixels live in skin_name(DIGEST)."""
    at, pixels = skin_of(raw)
    return raw[:MDL_HEADER] + SKIN_TYPE + digest[:16].encode('ascii') + struct.pack('<I', pixels) + raw[at + pixels:]


def is_shared(raw):
    return len(raw) >= MDL_HEADER + SKIN_REF and raw[:4] == b'IDPO' and raw[MDL_HEADER:MDL_HEADER + 4] == SKIN_TYPE


def expand_shared_skin(stored, read_skin):
    """The model the engine decodes from a stored shared-skin model: READ_SKIN(id1-relative name) gives the
    skin file's bytes. Raises ValueError like the engine refuses."""
    if not is_shared(stored):
        raise ValueError('Not a shared-skin model')
    ref = stored[MDL_HEADER + 4:MDL_HEADER + 20].decode('ascii')
    if any(c not in '0123456789abcdef' for c in ref):
        raise ValueError('Invalid shared skin name')
    pixels = struct.unpack_from('<I', stored, MDL_HEADER + 20)[0]
    width, height = struct.unpack_from('<2i', stored, 52)
    if pixels != width * height:
        raise ValueError('Shared skin size differs from the model header')
    skin = read_skin(SKIN_DIR + '/' + ref + SKIN_EXT)
    if len(skin) != pixels:
        raise ValueError('Shared skin file has the wrong size')
    return stored[:MDL_HEADER] + struct.pack('<i', SKIN_SINGLE) + skin + stored[MDL_HEADER + SKIN_REF:]


def plan_skins(id1, patterns=SKIN_PATTERNS):
    """{pixel SHA-256: [id1-relative model paths]} of skins two or more matching models repeat (sorted)."""
    id1 = Path(id1)
    users = {}
    for path in sorted(id1.rglob('*.mdl')):
        rel = path.relative_to(id1).as_posix()
        if not any(fnmatch.fnmatchcase(rel, p) for p in patterns):
            continue
        raw = path.read_bytes()
        found = skin_of(raw)
        if not found or len(raw) > SKIN_FULL_LIMIT:
            continue
        at, pixels = found
        users.setdefault(sha256(raw[at:at + pixels]), []).append(rel)
    groups = {d: paths for d, paths in users.items() if len(paths) > 1}
    prefixes = {}
    for digest in groups:
        if prefixes.setdefault(digest[:16], digest) != digest:
            raise ValueError('Two shared skins with the same 16-digit name: ' + digest[:16])
    return dict(sorted(groups.items()))


def apply_skins(id1, groups, write=True):
    """Store each skin of GROUPS once and rewrite its models (WRITE=False: count only). Returns the record."""
    id1 = Path(id1)
    before = after = 0
    for digest, paths in groups.items():
        skin_bytes = None
        for rel in paths:
            raw = (id1 / rel).read_bytes()
            at, pixels = skin_of(raw)
            pixels_raw = raw[at:at + pixels]
            if sha256(pixels_raw) != digest:
                raise ValueError('Skin of %s changed while sharing' % rel)
            stored = shared_model(raw, digest)
            if expand_shared_skin(stored, lambda name: pixels_raw) != raw:
                raise ValueError('Shared-skin form of %s does not rebuild the model' % rel)
            before += len(raw)
            after += len(stored)
            skin_bytes = pixels_raw
            if write:
                (id1 / rel).write_bytes(stored)
        after += len(skin_bytes)
        if write:
            target = id1 / skin_name(digest)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(skin_bytes)
    return {'skins': len(groups), 'models': sum(len(p) for p in groups.values()),
            'bytes_before': before, 'bytes_after': after, 'bytes_saved': before - after,
            'files_added': len(groups)}


# ---- shared shapes

def _skin_end(raw):
    """Where the one skin of a single-skin model ends (inline pixels or a shared-skin reference), or None."""
    if len(raw) < MDL_HEADER + 4 or raw[:4] != b'IDPO' or struct.unpack_from('<i', raw, 4)[0] != 6:
        return None
    count, width, height = struct.unpack_from('<3i', raw, 48)
    if count != 1 or width < 1 or height < 1 or width & 3:
        return None
    kind = raw[MDL_HEADER:MDL_HEADER + 4]
    if kind == SKIN_TYPE:
        return MDL_HEADER + SKIN_REF
    if kind == TILE_TYPE:
        tiles = _tiled_count(raw)
        return None if tiles is None else MDL_HEADER + 4 + tiled_ref_bytes(tiles)
    if kind == struct.pack('<i', SKIN_SINGLE):
        return MDL_HEADER + 4 + width * height
    return None


def shape_of(raw):
    """(offset, ST bytes, triangle bytes) of a single-skin model's two blocks, or None for anything else (skin
    groups, several skins, a shared shape already, another format, too short)."""
    at = _skin_end(raw)
    if at is None:
        return None
    verts, tris = struct.unpack_from('<2i', raw, 60)
    if verts < 1 or tris < 1 or raw[at:at + 4] == SHAPE_TYPE:
        return None
    st, tri = verts * ST_BYTES, tris * TRI_BYTES
    if at + st + tri > len(raw):
        return None
    return at, st, tri


def shape_name(digest):
    return SHAPE_DIR + '/' + digest[:16] + SHAPE_EXT


def shared_shape_model(raw, digest):
    """The stored form of RAW whose ST and triangle blocks live in shape_name(DIGEST)."""
    at, st, tri = shape_of(raw)
    return raw[:at] + SHAPE_TYPE + digest[:16].encode('ascii') + struct.pack('<2I', st, tri) + raw[at + st + tri:]


def is_shape_shared(raw):
    at = _skin_end(raw)
    return at is not None and len(raw) >= at + SHAPE_REF and raw[at:at + 4] == SHAPE_TYPE


def expand_shared_shape(stored, read_shape):
    """The model the engine decodes from a stored shared-shape model: READ_SHAPE(id1-relative name) gives the
    shape file's bytes. Raises ValueError where the engine refuses (model.c AW_SharedShapeExpand)."""
    if not is_shape_shared(stored):
        raise ValueError('Not a shared-shape model')
    at = _skin_end(stored)
    ref = stored[at + 4:at + 20].decode('ascii')
    if any(c not in '0123456789abcdef' for c in ref):
        raise ValueError('Invalid shared shape name')
    st, tri = struct.unpack_from('<2I', stored, at + 20)
    verts, tris = struct.unpack_from('<2i', stored, 60)
    if st != verts * ST_BYTES or tri != tris * TRI_BYTES:
        raise ValueError('Shared shape size differs from the model header')
    shape = read_shape(SHAPE_DIR + '/' + ref + SHAPE_EXT)
    if len(shape) != st + tri:
        raise ValueError('Shared shape file has the wrong size')
    return stored[:at] + shape + stored[at + SHAPE_REF:]


def _npc_lod_stems(id1):
    """Model stems named in the NPC level-of-detail manifest (their level files' byte sizes are checked by the
    engine against the manifest, so they are never rewritten)."""
    path = Path(id1) / NPC_LOD_MANIFEST
    if not path.is_file():
        return ()
    words = path.read_text(encoding='utf-8', errors='replace').split()
    return tuple(sorted({w[:-4] for w in words if w.startswith('progs/') and w.endswith('.mdl')}))


def _shape_row(path):
    raw = path.read_bytes()
    found = shape_of(raw)
    if not found or len(raw) > SKIN_FULL_LIMIT:
        return None
    at, st, tri = found
    return sha256(raw[at:at + st + tri]), st + tri


def plan_shapes(id1, patterns=SHAPE_PATTERNS, jobs=None):
    """{blocks SHA-256: [id1-relative model paths]} of ST + triangle blocks two or more matching models repeat."""
    id1 = Path(id1)
    lod = _npc_lod_stems(id1)
    paths = []
    for path in sorted(id1.glob('progs/*.mdl')):
        rel = path.relative_to(id1).as_posix()
        if rel.count('/') != 1 or not any(fnmatch.fnmatchcase(rel, p) for p in patterns):
            continue
        if any(rel.startswith(stem) for stem in lod):
            continue
        paths.append(path)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max(1, jobs or 4)) as pool:   # hashlib and reads release the GIL
        rows = list(pool.map(_shape_row, paths))
    users = {}
    for path, row in zip(paths, rows):
        if row:
            users.setdefault(row[0], []).append(path.relative_to(id1).as_posix())
    groups = {d: names for d, names in users.items() if len(names) > 1}
    prefixes = {}
    for digest in groups:
        if prefixes.setdefault(digest[:16], digest) != digest:
            raise ValueError('Two shared shapes with the same 16-digit name: ' + digest[:16])
    return dict(sorted(groups.items()))


def apply_shapes(id1, groups, write=True):
    """Store each shape of GROUPS once and rewrite its models (WRITE=False: count only). Returns the record."""
    id1 = Path(id1)
    before = after = 0
    for digest, paths in groups.items():
        blocks = None
        for rel in paths:
            raw = (id1 / rel).read_bytes()
            at, st, tri = shape_of(raw)
            mine = raw[at:at + st + tri]
            if sha256(mine) != digest:
                raise ValueError('Shape of %s changed while sharing' % rel)
            stored = shared_shape_model(raw, digest)
            if expand_shared_shape(stored, lambda name: mine) != raw:
                raise ValueError('Shared-shape form of %s does not rebuild the model' % rel)
            before += len(raw)
            after += len(stored)
            blocks = mine
            if write:
                (id1 / rel).write_bytes(stored)
        after += len(blocks)
        if write:
            target = id1 / shape_name(digest)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blocks)
    return {'shapes': len(groups), 'models': sum(len(p) for p in groups.values()),
            'bytes_before': before, 'bytes_after': after, 'bytes_saved': before - after,
            'files_added': len(groups)}


def identity(id1, jobs=None):
    """Read only, over a real payload ID1: plan the shapes, make every model's stored form in memory, rebuild it
    as the engine does (expand_shared_shape with the planned shape files) and compare the bytes with the original
    model. The engine's own C path is checked over the same models by tests/aga_shared_shape_test.c."""
    id1 = Path(id1)
    groups = plan_shapes(id1, jobs=jobs)
    store, models, same, saved = {}, 0, 0, 0
    for digest, paths in groups.items():
        for rel in paths:
            raw = (id1 / rel).read_bytes()
            at, st, tri = shape_of(raw)
            store.setdefault(shape_name(digest), raw[at:at + st + tri])
            stored = shared_shape_model(raw, digest)
            rebuilt = expand_shared_shape(stored, lambda name: store[name])
            models += 1
            same += rebuilt == raw
            saved += len(raw) - len(stored)
    saved -= sum(len(b) for b in store.values())
    return {'id1': str(id1), 'shapes': len(groups), 'models': models, 'byte_identical': same,
            'bytes_saved': saved}


# ---- skin tiles

def tiled_ref_bytes(tiles):
    """Bytes after the skin type of a tiled skin: 16 hex digits, the pixel count, the tile count, one u32 tile
    number per tile (chunk file = number >> 16, tile in it = number & 0xffff)."""
    return 16 + 4 + 4 + 4 * tiles


def _tiled_count(raw):
    """The tile count of a stored tiled-skin model, or None when RAW is none (or does not fit its header)."""
    if len(raw) < MDL_HEADER + 28 or raw[MDL_HEADER:MDL_HEADER + 4] != TILE_TYPE:
        return None
    width, height = struct.unpack_from('<2i', raw, 52)
    pixels, tiles = struct.unpack_from('<2I', raw, MDL_HEADER + 20)
    if (width < 1 or height < 1 or width % TILE or height % TILE or pixels != width * height or
            tiles != pixels // TILE_BYTES or MDL_HEADER + 4 + tiled_ref_bytes(tiles) > len(raw)):
        return None
    return tiles


def tile_skin_of(raw):
    """(offset, width, height) of a single-skin model's inline pixels when they cut into whole tiles, or None."""
    found = skin_of(raw)
    if not found:
        return None
    width, height = struct.unpack_from('<2i', raw, 52)
    if width % TILE or height % TILE:
        return None
    return found[0], width, height


def cut_tiles(pixels, width, height):
    """The tiles of a skin in row-major tile order, each 16 rows of 16 bytes."""
    out = []
    for ty in range(0, height, TILE):
        for tx in range(0, width, TILE):
            at = ty * width + tx
            out.append(b''.join(pixels[at + r * width:at + r * width + TILE] for r in range(TILE)))
    return out


def tile_pool_name(digest, chunk):
    """The id1-relative name of chunk CHUNK (tile numbers CHUNK << 16 and up) of the tile pool DIGEST."""
    return '%s/%s-%02x%s' % (TILE_DIR, digest[:16], chunk, TILE_EXT)


def tiled_model(raw, digest, numbers):
    """The stored form of RAW (a single-skin model with whole tiles) whose tiles are NUMBERS of pool DIGEST."""
    at, width, height = tile_skin_of(raw)
    return (raw[:MDL_HEADER] + TILE_TYPE + digest[:16].encode('ascii') +
            struct.pack('<2I', width * height, len(numbers)) + struct.pack('<%dI' % len(numbers), *numbers) +
            raw[at + width * height:])


def is_tiled(raw):
    return _tiled_count(raw) is not None


def expand_tiled_skin(stored, read_pool):
    """The model the engine decodes from a stored tiled-skin model: READ_POOL(id1-relative name) gives a pool
    chunk file's bytes. Raises ValueError where the engine refuses (model.c AW_TiledSkinExpand)."""
    tiles = _tiled_count(stored)
    if tiles is None:
        raise ValueError('Not a tiled-skin model')
    ref = stored[MDL_HEADER + 4:MDL_HEADER + 20].decode('ascii')
    if any(c not in '0123456789abcdef' for c in ref):
        raise ValueError('Invalid tile pool name')
    width, height = struct.unpack_from('<2i', stored, 52)
    numbers = struct.unpack_from('<%dI' % tiles, stored, MDL_HEADER + 28)
    chunks = {}
    for n in sorted(set(n >> 16 for n in numbers)):
        if n > 0xff:
            raise ValueError('Tile number past the last chunk')
        chunks[n] = read_pool(tile_pool_name(ref, n))
        if len(chunks[n]) % TILE_BYTES:
            raise ValueError('Tile pool chunk of a wrong size')
    pixels = bytearray(width * height)
    across = width // TILE
    for slot, n in enumerate(numbers):
        x, y = slot % across * TILE, slot // across * TILE
        pool, at = chunks[n >> 16], (n & 0xffff) * TILE_BYTES
        if at + TILE_BYTES > len(pool):
            raise ValueError('Tile pool too short')
        for r in range(TILE):
            pixels[(y + r) * width + x:(y + r) * width + x + TILE] = pool[at + r * TILE:at + (r + 1) * TILE]
    return (stored[:MDL_HEADER] + struct.pack('<i', SKIN_SINGLE) + bytes(pixels) +
            stored[MDL_HEADER + 4 + tiled_ref_bytes(tiles):])


def read_plan(numbers, gap=TILE_GAP, run=TILE_RUN):
    """(reads, tiles read) the engine makes for a skin's tile NUMBERS: sorted, a read covering up to RUN tiles,
    reading through holes of up to GAP tiles (model.c AW_TiledSkinExpand)."""
    wanted = sorted(set(numbers))
    reads = tiles = 0
    i = 0
    while i < len(wanted):
        start = last = wanted[i]
        i += 1
        while (i < len(wanted) and wanted[i] - start < run and wanted[i] - last <= gap and
               wanted[i] >> 16 == start >> 16):
            last = wanted[i]
            i += 1
        reads += 1
        tiles += last - start + 1
    return reads, tiles


def _tile_row(path):
    raw = path.read_bytes()
    if len(raw) > SKIN_FULL_LIMIT:
        return None
    found = tile_skin_of(raw)
    if not found:
        return None
    end = found[0] + found[1] * found[2]
    if raw[end:end + 4] == SHAPE_TYPE:                   # group by the shape: skins on one UV layout share tiles
        key = raw[end + 4:end + 20].decode('ascii')
    else:
        verts, tris = struct.unpack_from('<2i', raw, 60)
        key = sha256(raw[end:end + verts * ST_BYTES + tris * TRI_BYTES])[:16]
    return key


def plan_tiles(id1, patterns=TILE_PATTERNS, jobs=None):
    """{'digest', 'tiles': [tile bytes], 'models': [(id1-relative path, [tile numbers])]}: one tile pool for the
    single inline actor skins (the models taken by their shape, then by name). Tiles that two or more skins use
    come first, the most used first (a load reads them in few runs), then each skin's own tiles in model order
    (one run per skin). Stored in chunk files of TILE_CHUNK tiles (16 MiB) so a seek stays short."""
    id1 = Path(id1)
    lod = _npc_lod_stems(id1)
    paths = []
    for path in sorted(id1.glob('progs/*.mdl')):
        rel = path.relative_to(id1).as_posix()
        if rel.count('/') != 1 or not any(fnmatch.fnmatchcase(rel, p) for p in patterns):
            continue
        if any(rel.startswith(stem) for stem in lod):
            continue
        paths.append(path)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max(1, jobs or 4)) as pool:
        keys = list(pool.map(_tile_row, paths))
    order = sorted((key, path.relative_to(id1).as_posix()) for path, key in zip(paths, keys) if key)
    cuts, uses, first = [], {}, {}
    for i, (_, rel) in enumerate(order):
        raw = (id1 / rel).read_bytes()
        at, width, height = tile_skin_of(raw)
        cut = cut_tiles(raw[at:at + width * height], width, height)
        cuts.append((rel, cut))
        for t in set(cut):
            uses[t] = uses.get(t, 0) + 1
            first.setdefault(t, i)
    ranked = sorted(uses, key=lambda t: (0, -uses[t], first[t]) if uses[t] > 1 else (1, first[t], 0))
    if len(ranked) > TILE_CHUNK * 256:
        raise ValueError('Too many distinct skin tiles for the tile pool: %d' % len(ranked))
    number = {t: n for n, t in enumerate(ranked)}
    pool = {'tiles': ranked, 'models': [(rel, [number[t] for t in cut]) for rel, cut in cuts]}
    pool['digest'] = sha256(b''.join(ranked)) if ranked else ''
    return pool


def apply_tiles(id1, pool, write=True):
    """Write the pool's chunk files and rewrite its models (WRITE=False: count only). Returns the record, with the
    reads a load makes (model.c AW_TiledSkinExpand)."""
    id1 = Path(id1)
    before = after = models = 0
    reads, files = [], []
    tiles = pool['tiles']
    chunks = [b''.join(tiles[c:c + TILE_CHUNK]) for c in range(0, len(tiles), TILE_CHUNK)]
    for rel, numbers in pool['models']:
        raw = (id1 / rel).read_bytes()
        stored = tiled_model(raw, pool['digest'], numbers)
        if expand_tiled_skin(stored, lambda name: chunks[int(name[-len(TILE_EXT) - 2:-len(TILE_EXT)], 16)]) != raw:
            raise ValueError('Tiled-skin form of %s does not rebuild the model' % rel)
        before += len(raw)
        after += len(stored)
        models += 1
        reads.append(read_plan(numbers))
        files.append(len({n >> 16 for n in numbers}))
        if write:
            (id1 / rel).write_bytes(stored)
    after += sum(len(c) for c in chunks)
    if write:
        for c, blob in enumerate(chunks):
            target = id1 / tile_pool_name(pool['digest'], c)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
    counts = sorted(r for r, _ in reads)
    return {'pools': 1 if chunks else 0, 'chunks': len(chunks), 'models': models, 'tiles': len(tiles),
            'bytes_before': before, 'bytes_after': after, 'bytes_saved': before - after, 'files_added': len(chunks),
            'largest_pool_bytes': max((len(c) for c in chunks), default=0),
            'chunk_files_per_skin': {'mean': round(sum(files) / len(files), 1) if files else 0,
                                     'max': max(files, default=0)},
            'reads_per_skin': {'mean': round(sum(counts) / len(counts), 1) if counts else 0,
                               'p95': counts[int(len(counts) * 0.95)] if counts else 0,
                               'max': counts[-1] if counts else 0},
            'tile_bytes_read_per_skin_mean': round(sum(t for _, t in reads) * TILE_BYTES / len(reads)) if reads else 0}


# ---- file aliases

def table_name(name):
    """True for a name the engine's alias table can carry: printable ASCII, no TAB, at most 63 bytes."""
    return 0 < len(name) <= ALIAS_NAME_LIMIT and all(32 <= ord(c) < 127 for c in name)


def fold_key(name):
    """The engine's alias order (common.c COM_AliasCompare): bytes with a-z read as A-Z."""
    return bytes(c - 32 if 97 <= c <= 122 else c for c in name.encode('ascii'))


def plan_aliases(id1, kinds=ALIAS_KINDS, min_bytes=ALIAS_MIN_BYTES, jobs=None):
    """[(stored id1-relative path, [alias paths], bytes)] of byte-identical files: the stored copy is the
    first name in the engine's order; names the table cannot carry stay files of their own."""
    id1 = Path(id1)
    paths = [p for p in sorted(id1.rglob('*')) if p.is_file() and p.suffix.lower() in kinds
             and p.stat().st_size >= min_bytes and p.relative_to(id1).as_posix() != ALIAS_FILE]
    by_hash = {}
    for path, digest in zip(paths, _hashes(paths, jobs)):
        by_hash.setdefault(digest, []).append(path.relative_to(id1).as_posix())
    groups = []
    for digest, names in sorted(by_hash.items()):
        names = sorted((n for n in names if table_name(n)), key=lambda n: (fold_key(n), n))
        if len(names) < 2:
            continue
        groups.append((names[0], names[1:], (id1 / names[0]).stat().st_size))
    groups.sort(key=lambda g: fold_key(g[0]))
    return groups


def alias_table(groups):
    """The text of id1/file-aliases.txt (common.c COM_InitFileAliases): 'AWALIAS1 <stored> <aliases>', one
    stored name per line, then '<alias>TAB<stored index>' per alias in the engine's order (ASCII, LF)."""
    aliases = sorted(((name, index) for index, (_, names, _) in enumerate(groups) for name in names),
                     key=lambda row: fold_key(row[0]))
    keys = [fold_key(name) for name, _ in aliases]
    if len(set(keys)) != len(keys):
        raise ValueError('Two alias names differ only in case')
    lines = ['%s %d %d' % (ALIAS_MAGIC, len(groups), len(aliases))]
    lines += [target for target, _, _ in groups]
    lines += ['%s\t%d' % row for row in aliases]
    return ('\n'.join(lines) + '\n').encode('ascii')


def read_alias_table(raw):
    """{alias name (case-folded): stored name}: the host reference of what the engine reads (same checks)."""
    lines = raw.decode('ascii').split('\n')
    head = lines[0].split(' ')
    if len(head) != 3 or head[0] != ALIAS_MAGIC or lines[-1] != '':
        raise ValueError('Invalid alias table')
    count, aliases = int(head[1]), int(head[2])
    if len(lines) != 2 + count + aliases:
        raise ValueError('Alias table length differs from its header')
    stored = lines[1:1 + count]
    out, previous = {}, None
    for line in lines[1 + count:-1]:
        name, tab, index = line.partition('\t')
        if not tab or not table_name(name) or not index.isdigit() or int(index) >= count:
            raise ValueError('Invalid alias table entry: ' + line)
        if previous is not None and fold_key(previous) >= fold_key(name):
            raise ValueError('Alias table out of order at ' + name)
        out[name.casefold()] = stored[int(index)]
        previous = name
    return out


def apply_aliases(id1, groups, write=True):
    """Remove every alias file of GROUPS and write the table (WRITE=False: count only). Returns the record."""
    id1 = Path(id1)
    table = alias_table(groups) if groups else b''
    removed = sum(len(a) for _, a, _ in groups)
    saved = sum(len(a) * size for _, a, size in groups)
    if write and groups:
        if (id1 / ALIAS_FILE).exists():
            raise ValueError('The payload already has ' + ALIAS_FILE)
        for _, aliases, _ in groups:
            for name in aliases:
                (id1 / name).unlink()
        (id1 / ALIAS_FILE).write_bytes(table)
    memory = len(table) + 8 * removed + 4 * len(groups)   # common.c: the text, 8 B per alias, 4 B per stored name
    return {'groups': len(groups), 'files_removed': removed, 'bytes_saved': saved - len(table),
            'table_bytes': len(table), 'engine_memory_bytes': memory if groups else 0,
            'by_kind': _by_kind(groups)}


def _by_kind(groups):
    out = {}
    for _, aliases, size in groups:
        for name in aliases:
            row = out.setdefault(name.rsplit('/', 1)[0] + '/*' + Path(name).suffix.lower(), {'files': 0, 'bytes': 0})
            row['files'] += 1
            row['bytes'] += size
    return dict(sorted(out.items(), key=lambda kv: -kv[1]['bytes']))


# ---- both, in the image step

def share_payload(id1, *, file_aliases=False, shared_skins=False, shared_shapes=False, skin_tiles=False, jobs=None,
                  write=True, log=print):
    """The image step's last payload pass (finalize_image, after every check that reads the payload by name or
    size): shared skins first, then shared shapes (models that then become byte-identical are aliased too), then
    file aliases. Returns the record for build.json; 'bytes_removed' is what DH0 lost (the layout plan allows for
    it)."""
    record = {'file_aliases': bool(file_aliases), 'shared_skins': bool(shared_skins), 'bytes_removed': 0}
    if shared_shapes:
        record['shared_shapes'] = True
    if skin_tiles:
        record['skin_tiles'] = True
    if shared_skins:
        skins = apply_skins(id1, plan_skins(id1), write)
        record['skins'] = skins
        record['bytes_removed'] += skins['bytes_saved']
        log('Shared skins (--shared-skins on): %d skins stored once for %d models, %d bytes saved'
            % (skins['skins'], skins['models'], skins['bytes_saved']))
    if shared_shapes:
        log('=== Shared shapes (--shared-shapes on): hashing the ST and triangle blocks of progs/*.mdl ===')
        shapes = apply_shapes(id1, plan_shapes(id1, jobs=jobs), write)
        record['shapes'] = shapes
        record['bytes_removed'] += shapes['bytes_saved']
        log('Shared shapes (--shared-shapes on): %d shapes stored once for %d models, %d bytes saved'
            % (shapes['shapes'], shapes['models'], shapes['bytes_saved']))
    if skin_tiles:
        log('=== Skin tiles (--skin-tiles on): cutting the skins of progs/a_*.mdl and n_*.mdl into 16x16 tiles ===')
        tiles = apply_tiles(id1, plan_tiles(id1, jobs=jobs), write)
        record['tiles'] = tiles
        record['bytes_removed'] += tiles['bytes_saved']
        log('Skin tiles (--skin-tiles on): %d skins in one tile pool of %d chunk files (%d tiles), %d bytes saved, '
            '%.1f reads per skin' % (tiles['models'], tiles['chunks'], tiles['tiles'], tiles['bytes_saved'],
                                     tiles['reads_per_skin']['mean']))
    if file_aliases:
        aliases = apply_aliases(id1, plan_aliases(id1, jobs=jobs), write)
        record['aliases'] = aliases
        record['bytes_removed'] += aliases['bytes_saved']
        log('File aliases (--file-aliases on): %d files stored once under %d names more, %d bytes saved, '
            'table %d bytes (game memory about %d bytes)' % (aliases['groups'], aliases['files_removed'],
                                                             aliases['bytes_saved'], aliases['table_bytes'],
                                                             aliases['engine_memory_bytes']))
    return record


def measure(boot, file_aliases, shared_skins, jobs=None, shared_shapes=False, skin_tiles=False):
    """Dry run over a staged payload BOOT (read only): what each method saves on its own and both together.
    Both together are measured on a scratch view: the skin pass's stored forms counted, then aliases over them
    (a model pair that becomes byte-identical only after sharing is counted as the alias pass would see it)."""
    id1 = Path(boot) / 'id1'
    out = {'boot': str(boot)}
    if shared_skins:
        groups = plan_skins(id1)
        out['shared_skins'] = apply_skins(id1, groups, write=False)
    if shared_shapes:
        out['shared_shapes'] = apply_shapes(id1, plan_shapes(id1, jobs=jobs), write=False)
    if skin_tiles:
        out['skin_tiles'] = apply_tiles(id1, plan_tiles(id1, jobs=jobs), write=False)
    if file_aliases:
        out['file_aliases'] = apply_aliases(id1, plan_aliases(id1, jobs=jobs), write=False)
    if file_aliases and shared_skins:
        out['both'] = _both(id1, jobs)
    return out


def _both(id1, jobs):
    """Aliases over the payload as it would be after the skin pass (in memory: stored forms hashed)."""
    groups = plan_skins(id1)
    stored = {}
    for digest, paths in groups.items():
        for rel in paths:
            stored[rel] = shared_model((id1 / rel).read_bytes(), digest)
    files = [p for p in sorted(id1.rglob('*')) if p.is_file()]
    rows = {}
    plain = [p for p in files if p.relative_to(id1).as_posix() not in stored]
    for path, digest in zip(plain, _hashes(plain, jobs)):
        rows[path.relative_to(id1).as_posix()] = (digest, path.stat().st_size)
    for rel, raw in stored.items():
        rows[rel] = (sha256(raw), len(raw))
    for digest, paths in groups.items():
        raw = (id1 / paths[0]).read_bytes()
        at, pixels = skin_of(raw)
        rows[skin_name(digest)] = (digest, pixels)
    by_hash = {}
    for rel, (digest, size) in rows.items():
        if Path(rel).suffix.lower() in ALIAS_KINDS and size >= ALIAS_MIN_BYTES:
            by_hash.setdefault(digest, []).append((rel, size))
    alias_groups = []
    for members in by_hash.values():
        names = sorted((n for n, _ in members if table_name(n)), key=lambda n: (fold_key(n), n))
        if len(names) > 1:
            alias_groups.append((names[0], names[1:], members[0][1]))
    alias_groups.sort(key=lambda g: fold_key(g[0]))
    table = len(alias_table(alias_groups)) if alias_groups else 0
    alias_saved = sum(len(a) * size for _, a, size in alias_groups)
    before = sum(p.stat().st_size for p in files)
    after = sum(size for _, size in rows.values()) - alias_saved + table
    return {'payload_before': before, 'payload_after': after, 'bytes_saved': before - after,
            'alias_files': sum(len(a) for _, a, _ in alias_groups), 'alias_table_bytes': table,
            'skins': len(groups), 'skin_files_added': len(groups)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='action', required=True)
    m = sub.add_parser('measure', help='Dry run over a staged payload folder (read only)')
    m.add_argument('boot', type=Path)
    m.add_argument('--file-aliases', action='store_true')
    m.add_argument('--shared-skins', action='store_true')
    m.add_argument('--shared-shapes', action='store_true')
    m.add_argument('--skin-tiles', action='store_true')
    m.add_argument('--jobs', type=int, default=None)
    m.add_argument('--json', type=Path)
    k = sub.add_parser('identity', help='Read only: every shared-shape form of a real payload rebuilds its model')
    k.add_argument('id1', type=Path)
    k.add_argument('--jobs', type=int, default=None)
    k.add_argument('--json', type=Path)
    args = parser.parse_args(argv)
    if args.action == 'identity':
        result = identity(args.id1, args.jobs)
        text = json.dumps(result, indent=1)
        if args.json:
            args.json.write_text(text + '\n', encoding='utf-8', newline='\n')
        print(text)
        return 0 if result['byte_identical'] == result['models'] else 1
    if not (args.file_aliases or args.shared_skins or args.shared_shapes or args.skin_tiles):
        args.file_aliases = args.shared_skins = args.shared_shapes = args.skin_tiles = True
    result = measure(args.boot, args.file_aliases, args.shared_skins, args.jobs, args.shared_shapes, args.skin_tiles)
    text = json.dumps(result, indent=1)
    if args.json:
        args.json.write_text(text + '\n', encoding='utf-8', newline='\n')
    print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
