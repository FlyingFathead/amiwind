# SPDX-License-Identifier: GPL-3.0-only
"""Town configs and the runtime town registry (config/towns.json).

A converted town is one JSON file in config/ (balmora.json, vivec_arena.json):
the frame (source cell, centre, scale, bounds), the sub-cell settings and a
"town" block naming everything the converter used to hard-wire for Balmora.
config/towns.json lists every runtime town in stable save order and adds the
engine-only facts (world directory slot, behaviour flags, travel). See
docs/TOWN_IMPORT.md.
"""
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = 'towns.json'
FLAGS = ('seyda_scenes', 'legacy_payload', 'own_doors', 'scenery_catalogue', 'teleport_arrival', 'ground_place')
FIXED_TOWNS = ('seyda', 'balmora')  # names already in aw_maps.h's fixed save-ID table
NATIVE_REGION_MAX = 64              # AW_REGION_MAX in engine/aga/src/aw_region.h
HANDOFF_INSET = 96                  # same inset as prepare_world_regions.town_handoffs
# Settings written before the town block existed are Balmora's.
BALMORA_TOWN = {
    'id': 'balmora', 'title': 'Balmora', 'map': 'balmora', 'map_prefix': 'bm', 'region_cap': 64,
    'message': 'Balmora', 'region_file': 'balmora-regions.txt', 'door_file': 'scene-doors-balmora.txt',
    'visual_group': 'balmora',
    'arrival': {'travel_npc': 'darvame hleran'},
    'return': {'travel_npc': 'selvil sareloth', 'config': 'seyda_area.json'},
}
INTERIOR_MAX = 1000                 # interior maps <prefix>i000..<prefix>i999 per town
TITLE_MAX = 63                      # engine title buffers (save list, door labels)
NAME = re.compile(r'[a-z][a-z0-9_]{1,14}$')
PREFIX = re.compile(r'[a-z]{2}$')
FILE = re.compile(r'[a-z0-9_.-]{1,48}\.txt$')
SHIPPED_VERSION = re.compile(r'v\d+\.\d+\.\d+$')


def _root(root):
    return Path(root) if root else ROOT


def town_field(settings, key):
    """A town block field; settings without a town block are Balmora's."""
    town = settings.get('town')
    return (town if town is not None else BALMORA_TOWN)[key]


def validate_town(town, settings=None):
    """Reject names the engine tables, door banks or file systems cannot hold."""
    for key in ('id', 'title', 'map', 'map_prefix', 'region_cap', 'region_file'):
        if key not in town:
            raise ValueError('Town block lacks ' + key)
    if not NAME.match(town['id']) or not NAME.match(town['map']):
        raise ValueError('Town id/map must be 2-15 lower-case letters, digits or _')
    if not PREFIX.match(town['map_prefix']) or town['map_prefix'] == 'vf':
        raise ValueError('Town map prefix must be two letters other than vf')
    if town['map'].startswith(town['map_prefix']) and town['map'][2:].isdigit():
        raise ValueError('Town map name collides with its region names')
    if type(town['region_cap']) is not int or not 1 <= town['region_cap'] <= NATIVE_REGION_MAX:
        raise ValueError('Town region cap must be 1..64 (native directory capacity)')
    if not FILE.match(town['region_file']):
        raise ValueError('Invalid town region file name')
    for key in ('title', 'message'):
        value = town.get(key, 'x')
        if not isinstance(value, str) or not value or any(c in value for c in '"\r\n\\'):
            raise ValueError('Invalid town ' + key)
    if settings is None:
        return town
    for key in ('message', 'door_file', 'visual_group', 'arrival'):
        if key not in town:
            raise ValueError('Town block lacks ' + key)
    # The engine looks for scene-doors-<map>.txt (aw_scene.c read_links_for).
    if town['door_file'] != 'scene-doors-' + town['map'] + '.txt':
        raise ValueError('Town door file must be scene-doors-<map>.txt')
    arrival = town['arrival']
    explicit = 'source_position' in arrival
    if explicit == ('travel_npc' in arrival) or set(arrival) - {'travel_npc', 'source_position', 'source_rotation_z', 'reason'}:
        raise ValueError('Town arrival needs exactly one of travel_npc or source_position')
    if explicit and (len(arrival['source_position']) != 3 or
                     not all(isinstance(v, (int, float)) and math.isfinite(v)
                             for v in [*arrival['source_position'], arrival.get('source_rotation_z', 0)])):
        raise ValueError('Invalid explicit town arrival')
    returning = town.get('return')
    if returning is not None and set(returning) != {'travel_npc', 'config'}:
        raise ValueError('Town return needs travel_npc and config, or null')
    for key in ('reference_margin',):
        if key in settings and not (isinstance(settings[key], (int, float)) and settings[key] >= 0):
            raise ValueError('Invalid ' + key)
    if 'handoff_core' in settings:
        handoff_core(settings)
    interiors(settings)
    resident_exclusions(settings)
    return town


def resident_exclusions(settings):
    """NPC record ids (casefolded) the town leaves unplaced, each with a reason.

    "resident_exclusions": {"npc id": "reason"} covers residents the shared
    NPC converter cannot bake yet; the room or frame is converted without them.
    """
    rows = settings.get('resident_exclusions', {})
    if not isinstance(rows, dict):
        raise ValueError('Town resident_exclusions must map NPC ids to reasons')
    for key, reason in rows.items():
        if (not isinstance(key, str) or not key or any(c in key for c in '"\\\r\n')
                or not isinstance(reason, str) or not reason.strip()):
            raise ValueError('Town resident exclusion needs an NPC id and a reason')
    return {key.casefold() for key in rows}


def handoff_core(settings):
    """World handoff core of a table frame, in frame-local units.

    Default: the bounds inset by HANDOFF_INSET (the Arena). An explicit
    "handoff_core" is the area this frame owns when it neighbours other town
    frames; it must keep the frame edge out of view (draw distance plus the
    engine's 32-unit exit margin) from every point the player can stand in.
    """
    low, high = settings['bounds']
    core = settings.get('handoff_core')
    if core is None:
        return [[v + HANDOFF_INSET for v in low], [v - HANDOFF_INSET for v in high]]
    if (not isinstance(core, list) or len(core) != 2 or any(not isinstance(p, list) or len(p) != 2 for p in core)
            or not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for p in core for v in p)):
        raise ValueError('Town handoff_core must be [[x0, y0], [x1, y1]]')
    margin = settings['draw_distance'] + 32
    if not all(low[k] + margin <= core[0][k] < core[1][k] <= high[k] - margin for k in range(2)):
        raise ValueError('Town handoff_core must stay draw distance + 32 inside the frame bounds')
    return [list(core[0]), list(core[1])]


def interior_map(settings, index):
    """Runtime map name of the town's index-th interior (stable: lists are append-only)."""
    return town_field(settings, 'map_prefix') + 'i%03d' % index


def interiors(settings):
    """The town's interiors: [{map, cell, exclude}] in config order.

    "interiors" lists the original interior cells reached through this town's
    load doors (directly or through other listed rooms). The list is append
    only: a room's position gives its map name and save ID. A room that
    cannot be converted yet stays listed with "exclude": reason; its doors
    then show the interior as unavailable.
    """
    rows = settings.get('interiors', [])
    if not isinstance(rows, list) or len(rows) > INTERIOR_MAX:
        raise ValueError('Town interiors must be a list of at most %d rooms' % INTERIOR_MAX)
    out, cells = [], set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) - {'cell', 'exclude'} or 'cell' not in row:
            raise ValueError('Town interior needs a cell and an optional exclude reason')
        cell, reason = row['cell'], row.get('exclude')
        if (not isinstance(cell, str) or not cell or len(cell) > TITLE_MAX or not cell.isascii()
                or any(c in cell for c in '"\\') or any(ord(c) < 32 for c in cell)):
            raise ValueError('Invalid town interior cell name')
        if cell.casefold() in cells:
            raise ValueError('Town interior listed twice: ' + cell)
        if reason is not None and (not isinstance(reason, str) or not reason.strip() or any(ord(c) < 32 for c in reason)):
            raise ValueError('Town interior exclusion needs a reason')
        cells.add(cell.casefold())
        out.append({'map': interior_map(settings, index), 'cell': cell, 'exclude': reason})
    return out


def town_interiors(root=None):
    """Interiors of every registered town, in save order (towns, then list order)."""
    rows, cells = [], {}
    for index, row in enumerate(load_registry(root)['towns']):
        settings = json.loads((_root(root) / 'config' / row['config']).read_text(encoding='utf-8'))
        if row.get('town') is not None:
            continue
        for room in interiors(settings):
            key = room['cell'].casefold()
            if key in cells:
                raise ValueError('Interior listed by two towns: ' + room['cell'])
            cells[key] = row['id']
            rows.append(dict(room, town=row['id'], town_index=index, title=room['cell']))
    return rows


def load_registry(root=None):
    registry = json.loads((_root(root) / 'config' / REGISTRY).read_text(encoding='utf-8'))
    if registry.get('format') != 1 or not registry.get('towns'):
        raise ValueError('Unknown town registry format')
    ids = [row['id'] for row in registry['towns']]
    if ids[:len(FIXED_TOWNS)] != list(FIXED_TOWNS) or len(set(ids)) != len(ids):
        raise ValueError('Town registry must start with seyda, balmora and hold unique ids')
    return registry


def shipped_since(row):
    """The release a registry row's town ships in (its "shipped_since"), or None.

    A town after Seyda and Balmora with "shipped_since": "vX.Y.Z" is part of
    every release from that version on, so a default build makes it
    (BUILD-EXTRA-TOWN-OPTIN-32). Seyda and Balmora are always built; a
    blocked town cannot be shipped. A town with "withdrawn": "<reason>" keeps
    its "shipped_since" on record but is left out of default builds until the
    field is removed; --extra-town still builds it (an owner decision, e.g.
    the Vivec Arena in v0.0.33: CHIM-ARENA-MEMORY-33).
    """
    value = row.get('shipped_since')
    withdrawn(row)
    if value is None:
        return None
    if not isinstance(value, str) or not SHIPPED_VERSION.match(value):
        raise ValueError('Town shipped_since must be a release version vX.Y.Z: ' + row['id'])
    if row['id'] in FIXED_TOWNS or row.get('blocked'):
        raise ValueError('Only an unblocked town after Seyda and Balmora can be shipped_since: ' + row['id'])
    return None if row.get('withdrawn') else value


def withdrawn(row):
    """The reason a shipped town is withdrawn from default builds, or None (validated like "blocked")."""
    if 'withdrawn' not in row:
        return None
    reason = row['withdrawn']
    if not isinstance(reason, str) or not reason.strip() or row['id'] in FIXED_TOWNS:
        raise ValueError('A withdrawn town needs a reason (and cannot be Seyda or Balmora): ' + row['id'])
    return reason


def withdrawn_towns(root=None):
    """Towns with a "shipped_since" that default builds leave out ("withdrawn"), in table order."""
    return [row['id'] for row in load_registry(root)['towns'] if withdrawn(row)]


def extra_towns(root=None):
    """Towns after Seyda and Balmora that a build can import (not blocked), in table order."""
    return [row['id'] for row in load_registry(root)['towns'][len(FIXED_TOWNS):] if not row.get('blocked')]


def shipped_extra_towns(root=None):
    """Towns after Seyda and Balmora that a release ships, in table order: a default build makes them."""
    return [row['id'] for row in load_registry(root)['towns'][len(FIXED_TOWNS):] if shipped_since(row)]


def registry_row(town_id, root=None):
    for row in load_registry(root)['towns']:
        if row['id'] == town_id:
            return row
    raise ValueError('Unknown town: ' + str(town_id))


def load_settings(town_id, root=None):
    """The converter settings of one converted town (its config has a town block)."""
    row = registry_row(town_id, root)
    settings = json.loads((_root(root) / 'config' / row['config']).read_text(encoding='utf-8'))
    town = settings.get('town')
    if town is None or town.get('id') != town_id:
        raise ValueError('Town config has no matching town block: ' + row['config'])
    validate_town(town, settings)
    return settings


def handoff(settings):
    """World-directory handoff of a town frame: origin and inset ground core."""
    if settings['scale'] != .25:
        raise ValueError('Town handoff requires the shared 0.25 world scale')
    core = handoff_core(settings)
    if not all(-4000 < core[0][k] < core[1][k] < 4000 for k in range(2)):
        raise ValueError('Town handoff exceeds the bounded local coordinate range')
    return [v * settings['scale'] for v in settings['centre']] + [0.], core


def runtime_towns(root=None):
    """Rows of the engine town table, in registry (save) order."""
    rows, names, prefixes, files = [], set(), set(), set()
    registry = load_registry(root)
    for row in registry['towns']:
        settings = json.loads((_root(root) / 'config' / row['config']).read_text(encoding='utf-8'))
        town = row.get('town') or settings.get('town')
        if town is None or town['id'] != row['id']:
            raise ValueError('Town registry row has no town block: ' + row['id'])
        validate_town(town)
        if set(row.get('flags', [])) - set(FLAGS):
            raise ValueError('Unknown town flag: ' + row['id'])
        if 'blocked' in row and (not isinstance(row['blocked'], str) or not row['blocked'].strip()
                                 or row['id'] in FIXED_TOWNS):
            raise ValueError('A blocked town needs a reason (and cannot be Seyda or Balmora): ' + row['id'])
        shipped_since(row)
        slot = row.get('world_slot', -1)
        if slot not in (-1, 0, 1):
            raise ValueError('World directory holds two town slots; others use -1')
        distance = row.get('draw_distance', settings.get('draw_distance'))
        if type(distance) is not int or not 100 <= distance <= 4096:
            raise ValueError('Invalid town draw distance: ' + row['id'])
        travel = row.get('travel')
        if travel is not None and (set(travel) != {'npc', 'target', 'use_return_point'} or
                                   any(c in travel['npc'] for c in '"\\\r\n')):
            raise ValueError('Invalid town travel: ' + row['id'])
        origin, core = handoff(settings) if slot < 0 else ([0., 0., 0.], [[0, 0], [0, 0]])
        key = (town['map'], town['map_prefix'], town['region_file'])
        if key[0] in names or key[1] in prefixes or key[2] in files:
            raise ValueError('Town map, prefix and region file must be unique')
        names.add(key[0]); prefixes.add(key[1]); files.add(key[2])
        rows.append(dict(id=row['id'], name=town['map'], title=town['title'], prefix=town['map_prefix'],
                         regions=town['region_file'], region_cap=town['region_cap'], draw_distance=distance,
                         world_slot=slot, flags=list(row.get('flags', [])),
                         travel_npc=travel['npc'] if travel else '', travel_target=travel['target'] if travel else '',
                         travel_return=bool(travel and travel['use_return_point']),
                         handoff=slot < 0, origin=origin, core=core))
    names.update(r['map'] for r in town_interiors(root))
    if len(names) != len(rows) + len(town_interiors(root)):
        raise ValueError('Town interior map names must differ from town maps')
    targets = {r['name'] for r in rows}
    if any(r['travel_target'] and r['travel_target'] not in targets for r in rows):
        raise ValueError('Town travel target is not a registered town')
    if [r['world_slot'] for r in rows if r['world_slot'] >= 0] != [0, 1]:
        raise ValueError('Seyda and Balmora keep world directory slots 0 and 1')
    return rows
