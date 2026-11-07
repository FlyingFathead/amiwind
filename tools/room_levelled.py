# SPDX-License-Identifier: GPL-3.0-only
"""The rooms' levelled and placed creatures in the room maps (TOMB-NO-CREATURES-60 and -61; the builder half of
CREATURE-ROOM-LEVELLED-54).

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

The creatures placed directly in rooms (CREA references: 530 of 178 records in Morrowind.esm, the kwama queens, the
Dagoth brothers, the Dwemer centurions, the tombs' named undead; TOMB-NO-CREATURES-61) take the same entity: the
actor table gives each such creature a list of one entry after the real lists (chim.actors.placed_lists), so the
engine spawns it from its table base (its model from the actor library, its stats, sounds and behaviour as the
outdoor creatures have them) with no change to the engine. `aw_source_id` names the creature. The creatures the
resident stage bakes itself (config/interior_creatures.json: Vivec, Dagoth Ur, the Heart) have no such list and
are not written; nor is a reference whose map already holds it.

Called by the room stages after their residents (tools/chim_room_batches.py, tools/chim_rooms.py), never by the
town stages (their rooms' few levelled and placed creature references stay listed as left out: a town stage's
change re-keys its exterior frame).

Modes, each part of the room stages' keys:
  --room-levelled-creatures (AMIWIND_ROOM_LEVELLED)
    table  (default) an aw_levelled entity per levelled reference of a converted room
    off    none: the room maps as before v0.0.61 (every levelled reference listed as left out)
  --room-placed-creatures (AMIWIND_ROOM_PLACED)
    table  (default) an aw_levelled entity per placed creature reference of a converted room
    off    none: the room maps as before v0.0.62 (only the listed creatures of the resident stage)
"""
import os
from pathlib import Path

ENV = 'AMIWIND_ROOM_LEVELLED'
PLACED_ENV = 'AMIWIND_ROOM_PLACED'
MODES = ('table', 'off')
DEFAULT_MODE = 'table'
CLASSNAME = 'aw_levelled'
SCALE = 0.25                    # Quake units per Morrowind unit (prepare_quake.SCALE)
REASON_SCALED = 'levelled creature list with an instance scale: the room entity spawns at scale 1'
REASON_NO_LIST = 'levelled creature list not in the actor table\'s lists'
REASON_SCALED_CREATURE = 'creature with an instance scale: the room entity spawns at scale 1'


def _mode(env):
    value = os.environ.get(env, '').strip() or DEFAULT_MODE
    if value not in MODES:
        raise ValueError('%s takes %s, not %r' % (env, ', '.join(MODES), value))
    return value


def mode():
    return _mode(ENV)


def placed_mode():
    return _mode(PLACED_ENV)


def add_option(parser):
    parser.add_argument('--room-levelled-creatures', choices=MODES, default=DEFAULT_MODE,
                        help='The rooms\' levelled creatures (TOMB-NO-CREATURES-60): table (default: an aw_levelled '
                             'entity per levelled creature reference of a converted room, rolled by the engine from '
                             'the actor table at the player\'s level) or off (none, the room maps before v0.0.61). '
                             'Part of the room stages\' cache keys (AMIWIND_ROOM_LEVELLED)')
    parser.add_argument('--room-placed-creatures', choices=MODES, default=DEFAULT_MODE,
                        help='The creatures placed in rooms (TOMB-NO-CREATURES-61): table (default: an aw_levelled '
                             'entity per creature reference of a converted room, spawned by the engine from the '
                             'creature\'s actor table base) or off (none, the room maps before v0.0.62: only the '
                             'creatures config/interior_creatures.json lists). Part of the room stages\' cache keys '
                             '(AMIWIND_ROOM_PLACED)')
    return parser


_orders = {}


def list_index(master_path):
    """{levelled list id (lower case), or (chim.actors.PLACED, creature id) of a placed room creature: its index in
    the actor table's lists} for the master at MASTER_PATH, the same order tools/chim/actors.py write_table gives the
    table (table_list_order over the exterior's references, the rooms' roots and the rooms' placed creatures)."""
    key = str(Path(master_path).resolve())
    if key not in _orders:
        from chim import actors as A
        master = Path(master_path).read_bytes()
        rooms = A.room_references(master)
        order = A.table_list_order(A.levelled_lists(master), A.exterior_actors(master), rooms['LEVC'],
                                   A.room_placed_creatures(master, references=rooms))
        _orders[key] = {lid: i for i, lid in enumerate(order)}
    return _orders[key]


def _quote(value):
    text = str(value)
    if '"' in text or '\n' in text:
        raise ValueError('Entity value cannot hold a quote or a newline: %r' % text)
    return '"%s"' % text


def entity_text(fields):
    return '{\n' + '\n'.join('%s %s' % (_quote(k), _quote(v)) for k, v in fields.items()) + '\n}'


def entities(refs, index, slug, levelled=True, placed=False, present=()):
    """(entity field dicts, left out rows) of one room's references REFS (mwad.interior rows with 'type'): with
    LEVELLED an aw_levelled entity per non-deleted LEVC reference whose list INDEX knows, with PLACED one per
    non-deleted CREA reference whose creature has a placed list there (a creature the resident stage bakes has none
    and is skipped without a row: its own stage reports it); references in PRESENT (numbers the map already holds) are
    skipped. The others with their reason."""
    import math
    from chim.actors import PLACED
    out, left = [], []
    for ref in refs:
        kind = ref.get('type')
        if kind not in ('LEVC', 'CREA') or ref.get('deleted') or ref['number'] in present:
            continue
        if kind == 'LEVC' and not levelled or kind == 'CREA' and not placed:
            continue
        ident = ref['id'].casefold()
        key = ident if kind == 'LEVC' else (PLACED, ident)
        if key not in index:
            if kind == 'LEVC':
                left.append({'map': slug, 'reference': ref['number'], 'id': ref['id'], 'type': 'LEVC',
                             'reason': REASON_NO_LIST})
            continue
        if abs(ref.get('scale', 1.0) - 1) > 1e-5:
            left.append({'map': slug, 'reference': ref['number'], 'id': ref['id'], 'type': kind,
                         'reason': REASON_SCALED if kind == 'LEVC' else REASON_SCALED_CREATURE})
            continue
        pos = [v * SCALE for v in ref['position']]
        yaw = -math.degrees(ref.get('rotation_radians', (0.0, 0.0, 0.0))[2])
        out.append({'classname': CLASSNAME, 'aw_ref': ref['number'], 'sounds': index[key],
                    'origin': ' '.join('%.5f' % v for v in pos), 'angles': '0 %.5f 0' % yaw,
                    'aw_source_id': ident})
    return out, left


def _present(text):
    """Reference numbers (aw_ref) the entity text of a map already holds."""
    import re
    return {int(float(m)) for m in re.findall(r'"aw_ref"\s+"([0-9.]+)"', text)}


def write(maps, rooms, master_path, selection=None, placed_selection=None):
    """Append the aw_levelled entities of ROOMS ({map name: converted room cell}) to their maps under MAPS
    (<map>.bsp, whose entity lump the resident stage wrote). Returns the report: mode and placed_mode, placed (levelled
    references written), creatures (placed creature references written), left out (rows with reasons), per map
    counts. A map that already holds an aw_levelled entity is refused (written twice)."""
    from mwad.paths import replace_bytes
    from player_hull import lumps, pack_lumps
    selection = selection or mode()
    placed_selection = placed_selection or placed_mode()
    report = {'mode': selection, 'placed_mode': placed_selection, 'placed': 0, 'creatures': 0, 'left_out': [],
              'maps': {}}
    levelled, placed = selection == 'table', placed_selection == 'table'
    if not (levelled or placed):
        return report
    from chim.actors import PLACED
    index = list_index(master_path)
    placed_lists = {v for k, v in index.items() if isinstance(k, tuple) and k[0] == PLACED}
    for slug in sorted(rooms):
        path = Path(maps) / (slug + '.bsp')
        refs = rooms[slug]['refs']
        if not any(r.get('type') in ('LEVC', 'CREA') for r in refs):
            continue
        raw = path.read_bytes()
        b = lumps(raw)
        text = b[0].rstrip(b'\0').decode('cp1252')
        if '"classname" "%s"' % CLASSNAME in text and entities(refs, index, slug, levelled, placed)[0]:
            raise ValueError('Room map %s already holds %s entities' % (path.name, CLASSNAME))
        # a reference the map already holds (a listed creature the resident stage placed) is not written again
        fields, left = entities(refs, index, slug, levelled, placed, _present(text))
        report['left_out'].extend(left)
        if not fields:
            continue
        text = text.rstrip('\n') + '\n' + '\n'.join(entity_text(f) for f in fields) + '\n'
        b[0] = (text + '\0').encode('cp1252')
        replace_bytes(path, pack_lumps(b))
        creatures = sum(1 for f in fields if f['sounds'] in placed_lists)
        report['creatures'] += creatures
        report['placed'] += len(fields) - creatures
        report['maps'][slug] = len(fields)
    print('Room creatures (levelled %s, placed %s): %d levelled and %d placed creature entities in %d room maps, '
          '%d left out' % (selection, placed_selection, report['placed'], report['creatures'], len(report['maps']),
                           len(report['left_out'])), flush=True)
    return report


def drop_placed(left_out, maps_placed, rooms, index, levelled=True, placed=True):
    """LEFT_OUT (a residents report's rows) without the levelled and creature references write() placed (MAPS_PLACED:
    its 'maps'; LEVELLED and PLACED: its modes were table)."""
    done = set()
    for slug in maps_placed:
        fields, _ = entities(rooms[slug]['refs'], index, slug, levelled, placed)
        done |= {(slug, f['aw_ref']) for f in fields}
    return [r for r in left_out if not (r.get('type') in ('LEVC', 'CREA') and (r['map'], r['reference']) in done)]
