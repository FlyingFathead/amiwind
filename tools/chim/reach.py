# SPDX-License-Identifier: GPL-3.0-only
"""CHIM world format 0.9 (EXPERIMENTAL, build setting reach_index 'refs', default 'copies'): the reach index.

Format 0.9 is format 0.8 (chim.placed: 56-byte records, one model per mesh + scale, placed collision) with each
placement record stored once per frame. Until 0.8 every chunk that a placement's drawn box touches, besides the
chunk that owns it, held a whole copy of the owner record (a reach copy: 48 or 56 bytes). In 0.9 such a chunk holds
a 4-byte reach reference instead: the owner chunk's index in the frame (pack order) and the record's position among
that chunk's owned records (docs/chim/WORLD_FORMAT.md "Reach index (0.9, experimental)").

- Chunk record: magic CHK2 (terrain image inline, as CHK0) or CHK3 (terrain reference block, as CHK1); the head's
  reach count is the number of references; the owned records (56 bytes each, by id) are followed by the references
  (u16 owner chunk, u16 record index; by placement id, so by owner chunk and index), then the PVS row, the placement
  row and the terrain as before. The head's last u16 is the record size (56), as in 0.8.
- Everything else (index, frame file, sector files, models, textures, terrain records) is the 0.8 layout.
- The engine (chim_chunks.c LoadCatalogue) reads a reference's record from the owner chunk's own record list in the
  same frame (a span of records per owner chunk), so the run-time catalogue of every chunk holds the same placements
  as with copies; the Python readers resolve the references per frame (resolve_frame) and hand on the same records.

What it does not do: placements stay one record per FRAME that owns them, so an object in the overlapping margins of
several region frames is still stored in each of them (CHIM-PLACEMENT-MARGIN-COPIES-46: about 3.5 frames per
object). Storing an object once for the whole island needs the island chunk grid of the template (pages, a wide
table, frames as rectangles of island chunks), which is not here.

Nothing here is reached by a default build: chim.format, chim.placed, chim.collision and the unit kinds are
unchanged; only chim.world (the pack, after every unit) and the readers call it, and only for a 0.9 world.
Importing this module lets chim.format read and write format 0.9 (and imports chim.placed for 0.8).
"""
import struct

from chim import format as F
from chim import placed as P
from chim import terc  # noqa: F401  (the readers that import this module read format 0.10 too)
from chim import thgt  # noqa: F401  (and 0.11)

FORMAT_VERSION = (0, 9)
SETTING = 'reach_index'
MODES = ('copies', 'refs')        # 'copies': a whole record in every chunk the box touches (default, the method before)
CHUNK_MAGIC_REACH = b'CHK2'        # inline terrain image, reach references
CHUNK_MAGIC_REACH_REF = b'CHK3'    # terrain reference block (0.7), reach references
MAGICS = {F.CHUNK_MAGIC: CHUNK_MAGIC_REACH, F.CHUNK_MAGIC_REF: CHUNK_MAGIC_REACH_REF}
REACH_REF = struct.Struct('>HH')   # owner chunk index (frame, pack order), record index among its owned records

if FORMAT_VERSION not in F.READ_VERSIONS:
    F.READ_VERSIONS = F.READ_VERSIONS + (FORMAT_VERSION,)


def reach_mode(settings):
    """The build setting reach_index: 'copies' (default) or 'refs' (EXPERIMENTAL, world format 0.9, needs the
    placement format 0.8)."""
    settings = settings or {}
    value = str(settings.get(SETTING, 'copies'))
    if value not in MODES:
        raise ValueError('Unknown CHIM reach index: %s (copies or refs)' % value)
    if value == 'refs' and P.placement_format(settings) != '0.8':
        raise ValueError('The reach index (refs, world format 0.9) needs the placement format 0.8')
    return value


def refs_on(settings):
    return reach_mode(settings) == 'refs'


# ---------------------------------------------------------------- records

def reach_ref(owner_chunk, index):
    if not (0 <= owner_chunk <= 0xFFFF and 0 <= index <= 0xFFFF):
        raise ValueError('Reach reference out of range: chunk %d, record %d' % (owner_chunk, index))
    return REACH_REF.pack(owner_chunk, index)


def _reach_magic(data):
    magic = data[:4]
    if magic not in MAGICS:
        raise ValueError('Not a chunk record')
    return MAGICS[magic] + data[4:]


def chunk_record(owned, refs, pvs, image, image_render, leaves, pvl=b''):
    """A 0.9 chunk (CHK2): chim.placed.chunk_record with the 4-byte references in place of the reach copies."""
    data, render, collision = P.chunk_record(owned, refs, pvs, image, image_render, leaves, pvl)
    return _reach_magic(data), render, collision


def chunk_record_ref(owned, refs, pvs, ref, leaves, pvl=b''):
    """A 0.9 chunk whose terrain is a reference (CHK3)."""
    data, render, collision = P.chunk_record_ref(owned, refs, pvs, ref, leaves, pvl)
    return _reach_magic(data), render, collision


def is_reach_chunk(raw):
    return raw[:4] in (CHUNK_MAGIC_REACH, CHUNK_MAGIC_REACH_REF)


def read_chunk(raw):
    """A 0.9 chunk record's parts as chim.placed.read_chunk gives them, with 'reach_refs' [(owner chunk, record
    index)] and 'reach' a list of None of the same length (resolve_frame fills it with the owner records)."""
    magic, n_owned, n_reach, image_at, image_render, pvs_bytes, leaves, pvl_bytes, size = \
        F.CHUNK_HEAD.unpack_from(raw)
    if magic not in (CHUNK_MAGIC_REACH, CHUNK_MAGIC_REACH_REF):
        raise ValueError('Not a 0.9 chunk record')
    if size != P.PLACEMENT.size:
        raise ValueError('A 0.9 chunk record names a placement record of %d bytes' % size)
    at = F.CHUNK_HEAD.size
    owned = [P.read_placement(raw, at + k * P.PLACEMENT.size) for k in range(n_owned)]
    at += n_owned * P.PLACEMENT.size
    refs = [REACH_REF.unpack_from(raw, at + k * REACH_REF.size) for k in range(n_reach)]
    pvs_at = at + n_reach * REACH_REF.size
    if image_at < pvs_at + pvs_bytes + pvl_bytes or image_at + image_render > len(raw):
        raise ValueError('Chunk record parts overlap or overrun')
    return {'owned': owned, 'reach': [None] * n_reach, 'reach_refs': refs,
            'pvs': raw[pvs_at:pvs_at + pvs_bytes], 'pvl': raw[pvs_at + pvs_bytes:pvs_at + pvs_bytes + pvl_bytes],
            'leaves': leaves, 'image': raw[image_at:], 'image_render': image_render, 'render': image_at + image_render,
            **({'ref': F.read_terrain_ref(raw[image_at:])} if magic == CHUNK_MAGIC_REACH_REF else {})}


def read_chunk_any(raw):
    """A chunk record of any world (0.4-0.9): a 0.9 chunk's references are left unresolved (its 'reach' holds None);
    callers that read owned records only (chim.cuts, chim.far) need nothing more."""
    if is_reach_chunk(raw):
        return read_chunk(raw)
    return P.read_chunk(raw)


def resolve_frame(chunks):
    """Fill 'reach' of every 0.9 chunk of one frame (dicts with 'index', 'owned' and, for 0.9, 'reach_refs') with
    the owner records the references name, so every reader sees the records a 0.8 frame stores as copies. Raises
    ValueError naming the chunk and reference for a reference that names no record, or a record that the named
    chunk does not own."""
    by_index = {c['index']: c for c in chunks}
    for c in chunks:
        refs = c.get('reach_refs')
        if refs is None:
            continue
        out = []
        for owner, k in refs:
            o = by_index.get(owner)
            if o is None or owner == c['index'] or k >= len(o['owned']):
                raise ValueError('chunk %d: reach reference (%d, %d) names no owned record' % (c['index'], owner, k))
            r = o['owned'][k]
            if r['owner'] != owner:
                raise ValueError('chunk %d: reach reference (%d, %d) names a record owned by chunk %d'
                                 % (c['index'], owner, k, r['owner']))
            out.append(r)
        if [r['pid'] for r in out] != sorted(r['pid'] for r in out) or len({r['pid'] for r in out}) != len(out):
            raise ValueError('chunk %d: reach references not in placement id order' % c['index'])
        c['reach'] = out
    return chunks


def frame_refs(by_chunk, chunk_index):
    """{chunk: [reach reference bytes]} for one frame laid out by chim.world.frame_layout (by_chunk: owned and
    reach placements per chunk; chunk_index: chunk -> index in pack order), each chunk's references in placement id
    order (= by owner chunk and record index)."""
    position = {}
    for c, kinds in by_chunk.items():
        for k, p in enumerate(sorted(kinds['owned'], key=lambda q: q['_pid'])):
            position[p['_pid']] = (chunk_index[c], k)
    return {c: [reach_ref(*position[p['_pid']]) for p in sorted(kinds['reach'], key=lambda q: q['_pid'])]
            for c, kinds in by_chunk.items()}


# ---------------------------------------------------------------- measuring

def reach_bytes(n_reach, record_bytes=P.PLACEMENT.size):
    """(bytes as copies, bytes as references) of n reach entries."""
    return n_reach * record_bytes, n_reach * REACH_REF.size
