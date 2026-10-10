# SPDX-License-Identifier: GPL-3.0-only
"""The one implementation of the small Morrowind data-reading helpers.

Strings, deleted-record tests, record and subrecord walking, file digests, BSA
asset reads and the game's master list live here once; readers in src/mwad and
tools/ import them instead of keeping private copies (MWAD-SHARED-HELPERS-35).
"""
import hashlib
import struct
from collections.abc import Mapping

# The Morrowind masters in load order; the base pair is required, the expansions are game inputs too.
GAME_MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')
GAME_ARCHIVES = ('Morrowind.bsa', 'Tribunal.bsa', 'Bloodmoon.bsa')
GAME_CONTAINERS = tuple(name.casefold() for pair in zip(GAME_MASTERS, GAME_ARCHIVES) for name in pair)

# Every Morrowind NIF starts with this header; the full header line is the 4.0.0.2 version.
NIF_MAGIC = b'NetImmerse File Format'
NIF_TES3_HEADER = b'NetImmerse File Format, Version 4.0.0.2\n'

DELETED_FLAG = 0x20


class FormatError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise FormatError(message)


def string(data, field=None, errors='strict'):
    """A record string: up to the first NUL, decoded as cp1252.

    errors='strict' (default): an undecodable byte raises FormatError naming
    the field (and the byte position). errors='replace' is for callers that
    must tolerate foreign bytes (the closure keeps whatever it cannot resolve)."""
    data = bytes(data)
    cut = data.split(b"\0", 1)[0]
    if errors == 'replace':
        return cut.decode("cp1252", "replace")
    try:
        return cut.decode("cp1252")
    except UnicodeDecodeError as exc:
        where = f" in {field}" if field else ""
        raise FormatError(f"Undecodable cp1252 byte 0x{cut[exc.start]:02x} at {exc.start}{where}") from exc


def tag_name(raw, where="record"):
    """A four-byte record or subrecord tag as text."""
    try:
        return raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise FormatError(f"Non-ASCII {where} tag {raw!r}") from exc


def records(data):
    pos = 0
    while pos < len(data):
        require(pos + 16 <= len(data), f"Truncated record header at {pos}")
        tag, size, unused, flags = struct.unpack_from("<4sIII", data, pos)
        end = pos + 16 + size
        require(end <= len(data), f"Record {tag!r} overruns file at {pos}")
        yield tag_name(tag), flags, data[pos + 16:end]
        pos = end


def subrecords(data):
    pos = 0
    while pos < len(data):
        require(pos + 8 <= len(data), f"Truncated subrecord header at {pos}")
        tag, size = struct.unpack_from("<4sI", data, pos)
        end = pos + 8 + size
        require(end <= len(data), f"Subrecord {tag!r} overruns record at {pos}")
        yield tag_name(tag, "subrecord"), data[pos + 8:end]
        pos = end


def is_deleted(flags, subs, header_only=False):
    """True when a record is deleted: header flag 0x20 OR a DELE subrecord.

    subs: the record's (tag, data) pairs or a tag->data mapping. header_only: a
    CELL, whose placed references carry their own DELE; only the cell header
    (before the first FRMR) decides about the cell."""
    if flags & DELETED_FLAG:
        return True
    if isinstance(subs, Mapping):
        return 'DELE' in subs
    for tag, _ in subs:
        if header_only and tag == 'FRMR':
            return False
        if tag == 'DELE':
            return True
    return False


def unpack(fmt, data, field, offset=0, exact=False):
    """struct.unpack_from with a length check that names the field (FormatError, not struct.error).

    exact=True also requires the data to be exactly the format's size."""
    size = struct.calcsize(fmt)
    require(len(data) - offset >= size and (not exact or len(data) - offset == size),
            f"Malformed {field}: {len(data)} bytes, expected {'exactly ' if exact else 'at least '}{size}"
            + (f" from offset {offset}" if offset else ""))
    return struct.unpack_from(fmt, data, offset)


def first(fields, tag, default=b''):
    return next((v for k, v in fields if k == tag), default)


def text(fields, tag):
    return string(first(fields, tag), tag)


def sha256_file(path, block=1024 * 1024):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(block), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read_bsa_asset(bsa, name):
    """The bytes of one asset of a mwad.audit.BSA, by (any-case, any-slash) name."""
    from .audit import normpath
    entry = bsa.entries[normpath(name)]
    with bsa.path.open('rb') as stream:
        stream.seek(entry['offset'])
        raw = stream.read(entry['bytes'])
    require(len(raw) == entry['bytes'], 'Truncated BSA asset')
    return raw
