# SPDX-License-Identifier: GPL-3.0-only
"""The stable reference id of every placed reference (CELL-CHANGES-59): the key the engine's world change list and the
saved games use (engine/aga/src/aw_ledger.h), made at build time from the game's own reference identity.

A placed reference is identified by the content file that made it and its reference number there (the FRMR of a CELL;
the high byte of a FRMR in a plugin points at one of its masters, as tools/door_graph.py reads it). The bare number is
never the key: Tribunal's and Bloodmoon's own references start again at 1 and would collide with Morrowind's.

The id is a fixed function of (content file, low 24 bits), never of build order, so a rebuilt world keeps every key:

    id = FILE_INDEX * 2**20 + number       (number < 2**20 = 1,048,576)

with FILE_INDEX from CONTENT_FILES, a fixed list by name (0 Morrowind.esm, 1 Tribunal.esm, 2 Bloodmoon.esm). Morrowind's
own references are their own ids, so every save made before this table keeps its keys. Ids stay below 2**23: the
range from 0x800000 is the old saves' builder-made roles (aw_save.h AW_SaveChangeKey). The game's files as measured
on 2 November 2026 (a read-only count of every CELL's FRMR): Morrowind.esm 316,116 references, largest
484,481; Tribunal.esm 15,103, largest 26,408; Bloodmoon.esm 26,473, largest 33,635: all far below 2**20.
"""

NUMBER_BITS = 20
NUMBER_LIMIT = 1 << NUMBER_BITS
ID_LIMIT = 0x800000
# The content files by their fixed index; a new one is added at the end, never in between (the ids of the others
# must not move).
CONTENT_FILES = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')


class RefIdentityError(ValueError):
    """A reference that has no stable id: an unknown content file or a number past the field."""


def file_index(name):
    """The fixed index of content file NAME (case-insensitive)."""
    folded = name.casefold()
    for index, known in enumerate(CONTENT_FILES):
        if known.casefold() == folded:
            return index
    raise RefIdentityError(f'{name}: not a content file with a fixed index (tools/ref_identity.py CONTENT_FILES)')


def stable_ref(content_file, number):
    """The stable id of reference NUMBER (its low 24 bits) of CONTENT_FILE."""
    low = int(number) & 0xFFFFFF
    if not low:
        raise RefIdentityError(f'{content_file}: reference number 0 has no id')
    if low >= NUMBER_LIMIT:
        raise RefIdentityError(f'{content_file}: reference number {low} does not fit {NUMBER_BITS} bits')
    ref = file_index(content_file) * NUMBER_LIMIT + low
    assert ref < ID_LIMIT
    return ref


def owner_of(frmr, content_file, masters):
    """The content file a FRMR of CONTENT_FILE belongs to: its own (high byte 0, or past its master list) or the
    master the high byte names (1-based), as tools/door_graph.py reads a plugin's references."""
    high = int(frmr) >> 24
    return content_file if high == 0 or high > len(masters) else masters[high - 1]


def stable_ref_of_frmr(frmr, content_file, masters=()):
    """The stable id of a FRMR as CONTENT_FILE (with MASTERS) writes it."""
    return stable_ref(owner_of(frmr, content_file, masters), int(frmr) & 0xFFFFFF)


def split(ref):
    """(content file, number) of a stable id: the inverse of stable_ref."""
    index, low = divmod(int(ref), NUMBER_LIMIT)
    if not 0 < ref < ID_LIMIT or index >= len(CONTENT_FILES) or not low:
        raise RefIdentityError(f'{ref}: not a stable reference id')
    return CONTENT_FILES[index], low
