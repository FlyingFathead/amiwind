# SPDX-License-Identifier: GPL-3.0-only
"""Compact terrain records (world format 0.10, EXPERIMENTAL, build setting terrain_pack 'compact', default 'bsp29'):
a lossless repack of a chunk terrain's brush image (a TERR record of format 0.7) that the engine expands back into
the very same bytes before its usual loaders read them (docs/chim/WORLD_FORMAT.md "Compact terrain records (0.10,
experimental)"; the T1 option of the squeeze measurement of 20 October 2026).

The record stays a sector record of kind TERR; it starts with the magic 'TRC1' instead of the BSP29 version (29), so
the engine and the tools tell the two forms apart by content. Layout (big-endian head, the payloads keep the brush
image's little-endian bytes so expanding is byte shuffling, no float arithmetic):

  head (16)        'TRC1', u32 image bytes (expanded), u32 render bytes (expanded), u16 15, u16 0
  lump table       15 entries of 8 bytes in the brush image's file order (chim.format.FILE_ORDER):
                   u8 method, u8 0, u16 0, u32 payload bytes
  payloads         in the same order, each starting on a 4-byte boundary

Methods (each exact; a lump that does not fit one is stored RAW):
  0 RAW        the lump's bytes
  1 PLANES     u32 n; n codes (u8, padded to 4); then per plane: code 0: its 20 bytes, else its 4 distance bytes.
               Code 1 + 24 x type + 8 x axis + 4 x negative + zero signs: the normal is the unit vector on that axis
               (negative: pointing down the axis), its two other components zeros whose sign bits are the two bits
               of `zero signs` (bit 0 the lower axis), bit for bit, and the stored type is `type` (0-5).
  2 UNIFORM    u32 n, u8 value, 3 zero bytes: n bytes all of that value (the terrain's one light value)
  3 CLIPNODES  u32 n; per clipnode: u16 plane, i16 child, i16 child (every plane number below 65,536)
  4 NODES      u32 n; per node: u16 plane, then its other 20 bytes (every plane number below 65,536)

Eligibility: a record is written compact only when it is smaller and the compact record plus the expanded image fit
the engine's smallest loading buffer (EXPAND_ROOM: chim_local.h CHIM_MIN_BUFFER, model.h AW_BRUSH_SLICE_BYTES), so
the engine can read it and expand it in that buffer and load it as an image, never as a stream; every other record
stays a plain BSP29 image (both forms in one world).

Nothing here is reached by a default build: no unit kind and no stair code import it; only the pack in chim.world
(after every unit) and the readers call it, and only for a 0.10 world. Importing it lets chim.format read and write
format 0.10.
"""
import struct

from chim import format as F

FORMAT_VERSION = (0, 10)
SETTING = 'terrain_pack'
MODES = ('bsp29', 'compact', 'generate')     # generate: chim.thgt where it applies, else compact
MAGIC = b'TRC1'
HEAD = struct.Struct('>4sIIHH')                 # 16 bytes
ENTRY = struct.Struct('>BBHI')                  # 8 bytes
RAW, PLANES, UNIFORM, CLIPNODES, NODES = 0, 1, 2, 3, 4
EXPAND_ROOM = 16384 + 2064                      # engine CHIM_MIN_BUFFER (AW_BRUSH_SLICE_BYTES)
LUMP_PLANES, LUMP_LIGHTING, LUMP_CLIPNODES, LUMP_NODES = 1, 8, 9, 5
ONE = struct.pack('<f', 1.0)
MINUS_ONE = struct.pack('<f', -1.0)
ZERO = struct.pack('<f', 0.0)
MINUS_ZERO = struct.pack('<f', -0.0)

if FORMAT_VERSION not in F.READ_VERSIONS:
    F.READ_VERSIONS = F.READ_VERSIONS + (FORMAT_VERSION,)


def terrain_pack(settings):
    """The build setting terrain_pack: 'bsp29' (default) or 'compact' (EXPERIMENTAL, world format 0.10, needs
    terrain references: only TERR records are packed)."""
    settings = settings or {}
    value = str(settings.get(SETTING, 'bsp29'))
    if value not in MODES:
        raise ValueError('Unknown CHIM terrain pack: %s (bsp29, compact or generate)' % value)
    if value != 'bsp29' and str(settings.get('terrain_refs', 'off')) != 'on':
        raise ValueError('The %s terrain pack (world format 0.10/0.11) needs terrain references (terrain_refs on)'
                         % value)
    return value


def is_compact(data):
    return bytes(data[:4]) == MAGIC


# ---------------------------------------------------------------- lumps

def _plane_code(raw):
    """The code of one 20-byte plane (0: stored whole)."""
    n = [raw[0:4], raw[4:8], raw[8:12]]
    kind = struct.unpack_from('<i', raw, 16)[0]
    if not 0 <= kind <= 5:
        return 0
    for axis in range(3):
        others = [n[k] for k in range(3) if k != axis]
        if all(o in (ZERO, MINUS_ZERO) for o in others) and n[axis] in (ONE, MINUS_ONE):
            signs = (1 if others[0] == MINUS_ZERO else 0) | (2 if others[1] == MINUS_ZERO else 0)
            return 1 + 24 * kind + 8 * axis + (4 if n[axis] == MINUS_ONE else 0) + signs
    return 0


def _pack_planes(data):
    count = len(data) // 20
    codes = bytes(_plane_code(data[k * 20:k * 20 + 20]) for k in range(count))
    out = bytearray(struct.pack('<I', count)) + codes + bytes(F.align(count) - count)
    for k in range(count):
        out += data[k * 20 + 12:k * 20 + 16] if codes[k] else data[k * 20:k * 20 + 20]
    return bytes(out)


def _unpack_planes(data):
    count = struct.unpack_from('<I', data)[0]
    codes = data[4:4 + count]
    at = 4 + F.align(count)
    out = bytearray()
    for c in codes:
        if not c:
            out += data[at:at + 20]
            at += 20
            continue
        c -= 1
        kind, rest = divmod(c, 24)
        axis, rest = divmod(rest, 8)
        negative, signs = divmod(rest, 4)
        others = [k for k in range(3) if k != axis]
        normal = [ZERO, ZERO, ZERO]
        normal[axis] = MINUS_ONE if negative else ONE
        normal[others[0]] = MINUS_ZERO if signs & 1 else ZERO
        normal[others[1]] = MINUS_ZERO if signs & 2 else ZERO
        out += b''.join(normal) + data[at:at + 4] + struct.pack('<i', kind)
        at += 4
    return bytes(out), at


def _pack_lump(k, data):
    """(method, payload) of lump k: the smallest exact method, else RAW."""
    data = bytes(data)
    best = (RAW, data)
    if k == LUMP_PLANES and data:
        p = _pack_planes(data)
        if len(p) < len(best[1]):
            best = (PLANES, p)
    elif k == LUMP_LIGHTING and len(data) > 8 and data == bytes([data[0]]) * len(data):
        best = (UNIFORM, struct.pack('<IB3x', len(data), data[0]))
    elif k == LUMP_CLIPNODES and data:
        rows = [struct.unpack_from('<ihh', data, at) for at in range(0, len(data), 8)]
        if all(0 <= r[0] <= 0xFFFF for r in rows):
            best = (CLIPNODES, struct.pack('<I', len(rows)) + b''.join(struct.pack('<Hhh', *r) for r in rows))
    elif k == LUMP_NODES and data:
        rows = [data[at:at + 24] for at in range(0, len(data), 24)]
        if all(0 <= struct.unpack_from('<i', r)[0] <= 0xFFFF for r in rows):
            best = (NODES, struct.pack('<I', len(rows)) + b''.join(struct.pack('<H', struct.unpack_from('<i', r)[0])
                                                                   + r[4:] for r in rows))
    return best


def _unpack_lump(method, payload):
    if method == RAW:
        return payload
    if method == PLANES:
        return _unpack_planes(payload)[0]
    if method == UNIFORM:
        n, v = struct.unpack_from('<IB', payload)
        return bytes([v]) * n
    if method == CLIPNODES:
        n = struct.unpack_from('<I', payload)[0]
        return b''.join(struct.pack('<ihh', *struct.unpack_from('<Hhh', payload, 4 + 6 * k)) for k in range(n))
    if method == NODES:
        n = struct.unpack_from('<I', payload)[0]
        return b''.join(struct.pack('<i', struct.unpack_from('<H', payload, 4 + 22 * k)[0])
                        + payload[4 + 22 * k + 2:4 + 22 * k + 22] for k in range(n))
    raise ValueError('Unknown compact terrain method %d' % method)


# ---------------------------------------------------------------- records

def encode(image):
    """The compact record of a brush image, or None when it would not be exact, not smaller, or not fit the engine's
    smallest loading buffer together with the expanded image."""
    image = bytes(image)
    lumps = F.read_brush_image(image)
    rebuilt, render = F.brush_image(lumps)
    if rebuilt != image:
        return None                     # not the builder's own layout: the expansion could not give these bytes
    entries, body = [], bytearray()
    for k in F.FILE_ORDER:
        method, payload = _pack_lump(k, lumps[k])
        if _unpack_lump(method, payload) != bytes(lumps[k]):
            raise AssertionError('compact terrain method %d is not exact' % method)
        body += bytes(F.align(len(body)) - len(body))
        entries.append(ENTRY.pack(method, 0, 0, len(payload)))
        body += payload
    head = HEAD.pack(MAGIC, len(image), render, 15, 0)
    out = F.pad(head + b''.join(entries) + bytes(body))
    if len(out) >= len(image) or len(out) + len(image) > EXPAND_ROOM:
        return None
    if decode(out) != image:
        raise AssertionError('compact terrain record does not expand to its image')
    return out


def decode(data):
    """The brush image a compact record expands to (a BSP29 image is returned unchanged)."""
    data = bytes(data)
    if not is_compact(data):
        return data
    magic, image_bytes, render, count, _ = HEAD.unpack_from(data)
    if count != 15:
        raise ValueError('Compact terrain record with %d lumps' % count)
    at = HEAD.size + 15 * ENTRY.size
    lumps = [b''] * 15
    for slot, k in enumerate(F.FILE_ORDER):
        method, _, _, n = ENTRY.unpack_from(data, HEAD.size + slot * ENTRY.size)
        at = F.align(at)
        if at + n > len(data):
            raise ValueError('Compact terrain lump outside the record')
        lumps[k] = _unpack_lump(method, data[at:at + n])
        at += n
    image, got_render = F.brush_image(lumps)
    if len(image) != image_bytes or got_render != render:
        raise ValueError('Compact terrain record expands to %d bytes, its head says %d' % (len(image), image_bytes))
    return image
