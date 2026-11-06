# SPDX-License-Identifier: GPL-3.0-only
"""The rooms' levelled creatures in the room maps (TOMB-NO-CREATURES-60; the builder half of CREATURE-ROOM-LEVELLED-54).

Most creatures of the game's tombs, caves, mines and ruins are not placed as creatures but as levelled creature lists
(LEVC references: 1,270 in 293 rooms of Morrowind.esm; Samarys Ancestral Tomb has five and no direct creature). The
resident stage cannot bake them (the pick is the player's level at run time, never an invented roll at build time:
tools/creature_residents.py lists them as left out). Since v0.0.54 the engine rolls a room map's `aw_levelled`
entity from the actor table's lists (engine/aga/src/aw_actors.c LevelledEntity, pr_edict.c; docs/chim/WORLD_FORMAT.md
"Actor table"), with the game's rules (OpenMW 0.51 apps/openmw/mwmechanics/levelledlist.cpp and
mwclass/creaturelevlist.cpp; our own implementation in tools/chim/actors.py levelled_pick and the engine's
ChimActors_LevelledPick): the player's level, chance none, "from all levels", lists inside lists, the pick kept under
the reference so the room gives the same creature again, or nothing. This module writes those entities: one per
levelled reference of a converted room, `aw_ref` the reference number, `sounds` the list's index in the actor
table's list order (chim.actors.table_list_order: one order for the table and the rooms), origin and angle as the
room's residents (the reference's position x 0.25, yaw from its z rotation).

Called by the room stages after their residents (tools/chim_room_batches.py, tools/chim_rooms.py), never by the
town stages (their rooms' few levelled references stay listed as left out: a town stage's change re-keys its
exterior frame).

Modes (--room-levelled-creatures, environment AMIWIND_ROOM_LEVELLED; part of the room stages' keys):
  table  (default) an aw_levelled entity per levelled reference of a converted room
  off    none: the room maps as before v0.0.61 (every levelled reference listed as left out)
"""
import os
import struct
from pathlib import Path

ENV = 'AMIWIND_ROOM_LEVELLED'
MODES = ('table', 'off')
DEFAULT_MODE = 'table'
CLASSNAME = 'aw_levelled'
SCALE = 0.25                    # Quake units per Morrowind unit (prepare_quake.SCALE)
REASON_SCALED = 'levelled creature list with an instance scale: the room entity spawns at scale 1'
REASON_NO_LIST = 'levelled creature list not in the actor table\'s lists'


def mode():
    value = os.environ.get(ENV, '').strip() or DEFAULT_MODE
    if value not in MODES:
        raise ValueError('%s takes %s, not %r' % (ENV, ', '.join(MODES), value))
    return value


def add_option(parser):
    parser.add_argument('--room-levelled-creatures', choices=MODES, default=DEFAULT_MODE,
                        help='The rooms\' levelled creatures (TOMB-NO-CREATURES-60): table (default: an aw_levelled '
                             'entity per levelled creature reference of a converted room, rolled by the engine from '
                             'the actor table at the player\'s level) or off (none, the room maps before v0.0.61). '
                             'Part of the room stages\' cache keys (AMIWIND_ROOM_LEVELLED)')
    return parser


_orders = {}


def list_index(master_path):
    """{levelled list id (lower case): its index in the actor table's lists} for the master at MASTER_PATH, the same
    order tools/chim/actors.py write_table gives the table (table_list_order over the exterior's references and the
    rooms' roots)."""
    key = str(Path(master_path).resolve())
    if key not in _orders:
        from chim import actors as A
        master = Path(master_path).read_bytes()
        order = A.table_list_order(A.levelled_lists(master), A.exterior_actors(master), A.room_levelled_roots(master))
        _orders[key] = {lid: i for i, lid in enumerate(order)}
    return _orders[key]


def _quote(value):
    text = str(value)
    if '"' in text or '\n' in text:
        raise ValueError('Entity value cannot hold a quote or a newline: %r' % text)
    return '"%s"' % text


def entity_text(fields):
    return '{\n' + '\n'.join('%s %s' % (_quote(k), _quote(v)) for k, v in fields.items()) + '\n}'


def entities(refs, index, slug):
    """(entity field dicts, left out rows) of one room's references REFS (mwad.interior rows with 'type'): an
    aw_levelled entity per non-deleted LEVC reference whose list INDEX knows; the others with their reason."""
    import math
    out, left = [], []
    for ref in refs:
        if ref.get('type') != 'LEVC' or ref.get('deleted'):
            continue
        lid = ref['id'].casefold()
        if lid not in index:
            left.append({'map': slug, 'reference': ref['number'], 'id': ref['id'], 'type': 'LEVC',
                         'reason': REASON_NO_LIST})
            continue
        if abs(ref.get('scale', 1.0) - 1) > 1e-5:
            left.append({'map': slug, 'reference': ref['number'], 'id': ref['id'], 'type': 'LEVC',
                         'reason': REASON_SCALED})
            continue
        pos = [v * SCALE for v in ref['position']]
        yaw = -math.degrees(ref.get('rotation_radians', (0.0, 0.0, 0.0))[2])
        out.append({'classname': CLASSNAME, 'aw_ref': ref['number'], 'sounds': index[lid],
                    'origin': ' '.join('%.5f' % v for v in pos), 'angles': '0 %.5f 0' % yaw,
                    'aw_source_id': lid})
    return out, left


def write(maps, rooms, master_path, selection=None):
    """Append the aw_levelled entities of ROOMS ({map name: converted room cell}) to their maps under MAPS
    (<map>.bsp, whose entity lump the resident stage wrote). Returns the report: mode, placed and left out (rows
    with reasons), per map counts. A map that already holds an aw_levelled entity is refused (written twice)."""
    from mwad.paths import replace_bytes
    from player_hull import lumps, pack_lumps
    selection = selection or mode()
    report = {'mode': selection, 'placed': 0, 'left_out': [], 'maps': {}}
    if selection == 'off':
        return report
    index = list_index(master_path)
    for slug in sorted(rooms):
        fields, left = entities(rooms[slug]['refs'], index, slug)
        report['left_out'].extend(left)
        if not fields:
            continue
        path = Path(maps) / (slug + '.bsp')
        raw = path.read_bytes()
        b = lumps(raw)
        text = b[0].rstrip(b'\0').decode('cp1252')
        if '"classname" "%s"' % CLASSNAME in text:
            raise ValueError('Room map %s already holds %s entities' % (path.name, CLASSNAME))
        text = text.rstrip('\n') + '\n' + '\n'.join(entity_text(f) for f in fields) + '\n'
        b[0] = (text + '\0').encode('cp1252')
        replace_bytes(path, pack_lumps(b))
        report['placed'] += len(fields)
        report['maps'][slug] = len(fields)
    print('Room levelled creatures (%s): %d aw_levelled entities in %d room maps, %d left out' % (
        selection, report['placed'], len(report['maps']), len(report['left_out'])), flush=True)
    return report


def drop_placed(left_out, maps_placed, rooms, index):
    """LEFT_OUT (a residents report's rows) without the levelled references write() placed (MAPS_PLACED: its 'maps')."""
    placed = set()
    for slug in maps_placed:
        fields, _ = entities(rooms[slug]['refs'], index, slug)
        placed |= {(slug, f['aw_ref']) for f in fields}
    return [r for r in left_out if not (r.get('type') == 'LEVC' and (r['map'], r['reference']) in placed)]
