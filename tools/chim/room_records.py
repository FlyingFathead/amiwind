# SPDX-License-Identifier: GPL-3.0-only
"""CHIM room records as an installed image holds them: the record format and its readers (docs/chim/INTERIOR_STORE.md).

A room record (<store>/rooms/<room>.crm) is a header (kind ROOM), the room block (bounds, model count), the store model
list and the placed records (world format 0.8 placements, three angles, the light level in the flags' high byte since
world format 0.12, its tint in bits 2-4 since 0.13). The image step's checks and bakes that stand something on a room
read the room here: the record an installed room map names (installed_room), and the store models it places
(store_model_images) for their collision. tools/chim/interior.py, the room conversion that writes them, imports these
names from here.

Kept apart from interior.py on purpose (BUILD-ROOM-ACTOR-REKEY-67): a unit cache keyed on the code its bake reaches
counts every reached module's import-time code and every data file that code names. The CHIM room actor fits (the
room-actor unit cache, tools/room_actor_bake.py) read only these readers of interior.py, yet their key counted all of
interior.py's module level and, through a default value there, config/chim-rooms.json: a new room conversion setting
(the everywhere recipe in the rooms, v0.0.67-dev3) re-keyed all 2,342 fits, whose output it does not change.
"""
import struct
from pathlib import Path

from chim import format as F
from chim import placed as P  # (registers world format 0.8)

ROOM_KIND = b'ROOM'
ROOM_BLOCK = struct.Struct('>6fII')          # bounds mins, maxs; model count; 0
# World format 0.12: the placement light level in the high byte of a placed record's flags; 0.13: the light's tint
# in bits 2-4 (interior_lighting.light_tint; the engine's tint tables, r_sky.c).
FORMAT_VERSION = (0, 13)
FLAGS_AT = 46                                # the flags' offset in a placed record (chim.format.PLACEMENT)
TINT_SHIFT = 2
if FORMAT_VERSION not in F.READ_VERSIONS:
    F.READ_VERSIONS = F.READ_VERSIONS + (FORMAT_VERSION,)
if ROOM_KIND not in F.KINDS:
    F.KINDS = F.KINDS + (ROOM_KIND,)


def read_room_record(data):
    head = F.read_header(data, ROOM_KIND)
    v = ROOM_BLOCK.unpack_from(data, F.HEADER.size)
    n = v[6]
    if head['directory'] != F.HEADER.size + ROOM_BLOCK.size or head['data'] != head['directory'] + 4 * n:
        raise ValueError('Room record offsets do not match its model list')
    models = list(struct.unpack_from('>%dI' % n, data, head['directory']))
    at = head['data']
    if at + head['count'] * P.PLACEMENT.size != len(data):
        raise ValueError('Room record size does not match its placements')
    records = [P.read_placement(data, at + i * P.PLACEMENT.size) for i in range(head['count'])]
    for i, r in enumerate(records):
        flags = struct.unpack_from('>H', data, at + i * P.PLACEMENT.size + FLAGS_AT)[0]
        r['light'] = flags >> 8
        r['tint'] = (flags >> TINT_SHIFT) & 7 if head['version'] >= (0, 13) else 0
    return {'bounds': (v[0:3], v[3:6]), 'models': models, 'placements': records}


def installed_room(map_path):
    """The room record of an installed CHIM room map (maps/<room>.chim beside <store>/rooms/<room>.crm in the same
    id1), read: {'bounds', 'models', 'placements'} plus 'store' (the store folder) and 'room'; None for a map that is
    not a CHIM room. Raises ValueError when the room map names a record the image does not hold."""
    from map_files import room_record, room_record_path
    map_path = Path(map_path)
    found = room_record(map_path)
    if found is None:
        return None
    path = room_record_path(map_path.parent.parent, map_path)
    if not path.is_file():
        raise ValueError('CHIM room map %s names %s/rooms/%s.crm, which the image does not hold'
                         % (map_path.name, found[0], found[1]))
    return dict(read_room_record(path.read_bytes()), store=found[0], room=found[1])


def store_model_images(id1, store, ids):
    """{model id: brush image bytes} of the store models IDS, read from id1/<store>/world.cwi and only the pack files
    that hold them (the whole store is never read for one room)."""
    root = Path(id1) / store
    _, files, models, _ = F.read_index((root / 'world.cwi').read_bytes())
    packs, out = {}, {}
    for i in sorted(set(ids)):
        if not 0 <= i < len(models):
            raise ValueError('%s: model %d is not in the store (%d models)' % (store, i, len(models)))
        m = models[i]
        path = files[m['file']]['path']
        if path not in packs:
            packs[path] = (root / path).read_bytes()
        data = packs[path][m['offset']:m['offset'] + m['bytes']]
        if len(data) != m['bytes']:
            raise ValueError('%s: model %d runs past its pack %s' % (store, i, path))
        out[i] = data
    return out
