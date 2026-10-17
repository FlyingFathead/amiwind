# SPDX-License-Identifier: GPL-3.0-only
"""Interiors of a converted town, linked through their original load doors.

A town config may list the interior cells reached through its load doors
("interiors", see town_config.interiors). tools/import_town.py converts each
listed room with the shared interior converter (prepare_area.build_room, the
Balmora interior policy: every selected placement retained, exact standing
bevels on hollow shells), places its residents, and writes door banks:

- the town's exterior bank (scene-doors-<map>.txt) links each load door to
  its room's map and original arrival;
- every room gets doors-<room>.txt: doors into other listed rooms, and exits
  to the town frame whose handoff core holds the original exit point (the
  same first-in-table-order rule as the engine's world handoff);
- a door into a room that is not listed, excluded or failed keeps target "-":
  the engine shows the room as unavailable and never loads it.

How Quake does it: a room is a level of its own and a door is a changelevel
with a spawn point (the door bank), as for Balmora's interiors. No new engine
mechanism; the runtime only needs the rooms' save IDs (aw_town_table.h).
"""
import json
import math
from pathlib import Path
import shutil
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from town_config import FIXED_TOWNS, handoff_core, interiors, load_registry, town_field

ROOT = Path(__file__).resolve().parents[1]
SCALE = .25
FEET = 16.875            # feet-to-origin lift of every converted arrival
COORD_LIMIT = 4096       # MSG_WriteCoord: 1/8-unit shorts (INTERIOR-COORDS-31)
BANK_ROWS = 256          # aw_scene.c AW_SCENE_LINKS: read_links_for keeps at most 256 links (was 128; whole-city Vivec: 157)
MODEL_LIMIT = 220        # prepare_area.build_room's inline model budget


def arrival_yaw(rotation_z):
    return round((90 - math.degrees(rotation_z)) % 360, 5) % 360


def listed_rooms(settings, root=None):
    """The rooms a town's frame leads into: its own listed interiors, then those of the towns named by its
    "interiors_from" (all of Vivec in one frame, vivec_city, takes the eight district rows' rooms with their
    map names and save IDs, so a room is listed once in the town table)."""
    from town_config import load_settings
    rows = list(interiors(settings))
    for town in settings.get('interiors_from') or []:
        rows += interiors(load_settings(town, root))
    return rows


def frame_towns(root=None, prefer=()):
    """Table frames with a world handoff, in table order: (map, title, settings, core). prefer: town ids tried
    first (the towns this build holds: a room of the Vivec districts leads out into vivec_city when the build
    holds the whole city, not into a district frame the disk does not have)."""
    out = []
    for row in load_registry(root)['towns'][len(FIXED_TOWNS):]:
        if row.get('world_slot', -1) >= 0 or row.get('town') is not None:
            continue
        settings = json.loads((Path(root or ROOT) / 'config' / row['config']).read_text(encoding='utf-8'))
        out.append((town_field(settings, 'map'), town_field(settings, 'title'), settings, handoff_core(settings)))
    first = [t for t in out if t[2].get('town', {}).get('id') in prefer]
    return first + [t for t in out if t not in first]


def exit_town(position, towns):
    """First table frame whose handoff core holds an original exterior point."""
    for name, title, settings, core in towns:
        local = [(position[k] - settings['centre'][k]) * settings['scale'] for k in range(2)]
        if all(core[0][k] <= local[k] <= core[1][k] for k in range(2)):
            return name, title, settings
    return None


def room_offsets(root=None):
    """{original cell (casefolded): [x, y, z]} of every listed room moved toward the origin ("recentre" in its
    town's interiors row, original units; INTERIOR-COORDS-31). Every position of such a room (its placements,
    lights, residents, door boxes and every arrival into it) has this subtracted; the room itself is unchanged."""
    offsets = {}
    for row in load_registry(root)['towns']:
        settings = json.loads((Path(root or ROOT) / 'config' / row['config']).read_text(encoding='utf-8'))
        for room in interiors(settings):
            if room.get('recentre'):
                offsets[room['cell'].casefold()] = list(room['recentre'])
    return offsets


def recentre_cell(cell, offset):
    """The room's cell record with OFFSET (original units) subtracted from every reference position and every
    arrival into it (its entrances' destinations); the water height moves with z. Returns a new record."""
    if not offset or not any(offset):
        return cell
    def moved(position):
        return [position[k] - offset[k] for k in range(3)]
    out = dict(cell)
    out['refs'] = [dict(ref, position=moved(ref['position'])) if 'position' in ref else ref for ref in cell['refs']]
    out['entrances'] = [dict(e, destination=dict(e['destination'], position=moved(e['destination']['position'])))
                        for e in cell.get('entrances', [])]
    if cell.get('water_height') is not None:
        out['water_height'] = cell['water_height'] - offset[2]
    out['recentred_by'] = list(offset)
    return out


def local_arrival(destination, settings=None, offset=None):
    """Original DODT position to the target map's local arrival (feet lifted). offset: the target room's
    recentring (room_offsets), subtracted first."""
    position = destination['position']
    if offset:
        position = [position[k] - offset[k] for k in range(3)]
    point = [(position[k] - (settings['centre'][k] if settings is not None and k < 2 else 0)) * SCALE for k in range(3)]
    point[2] += FEET
    return point, arrival_yaw(destination['rotation_radians'][2])


def bank_row(source, target, reference, mins, maxs, arrival, yaw, label):
    if any(ord(c) < 32 for c in label) or len(label.encode('cp1252')) > 95:
        raise ValueError('Invalid door label')
    return (source + ' ' + target + ' ' + str(reference) + ' '
            + ' '.join(f'{v:.5f}' for v in (*mins, *maxs, *arrival, yaw)) + '\t' + label)


def bank_text(rows):
    if len(rows) > BANK_ROWS:
        raise ValueError('Door bank exceeds %d rows' % BANK_ROWS)
    return '\n'.join(['AWD3', *rows]) + '\n'


def available_rooms(root=None, converted=None):
    """Original cell (casefolded) -> runtime map of every listed, not excluded room.

    converted: optional {cell casefold: bool}; a room this run failed to convert
    is not linked.
    """
    rooms = {}
    for row in load_registry(root)['towns']:
        if row.get('town') is not None:
            continue
        settings = json.loads((Path(root or ROOT) / 'config' / row['config']).read_text(encoding='utf-8'))
        for room in interiors(settings):
            key = room['cell'].casefold()
            if room['exclude'] is None and (converted is None or converted.get(key, True)):
                rooms[key] = room['map']
    return rooms


def room_bank(room, doors, rooms, towns, door_bounds, offsets=None, offset=None):
    """doors-<room>.txt rows of one converted room.

    doors: original door links whose source is this room (mwad.interior.original_doors).
    door_bounds: reference -> [[x, y, z], [x, y, z]] original door mesh bounds.
    offsets: room_offsets() (arrivals into a recentred room); offset: this room's own recentring (its door boxes).
    """
    rows = []
    offsets = offsets or {}
    shift = offset or [0, 0, 0]
    for door in sorted(doors, key=lambda d: d['number']):
        low, high = door_bounds[door['number']]
        mins = [(v - shift[k]) * SCALE - .5 for k, v in enumerate(low)]
        maxs = [(v - shift[k]) * SCALE + .5 for k, v in enumerate(high)]
        if door['destination_interior']:
            target = rooms.get(door['destination_cell'].casefold(), '-')
            arrival, yaw = local_arrival(door['destination'], offset=offsets.get(door['destination_cell'].casefold()))
            label = door['destination_cell']
        else:
            town = exit_town(door['destination']['position'], towns)
            if town is None:
                target, label = '-', 'Exterior world'
                arrival, yaw = [0, 0, 0], 0
            else:
                target, label = town[0], town[1]
                arrival, yaw = local_arrival(door['destination'], town[2])
        if target == '-':
            arrival, yaw = [0, 0, 0], 0
        rows.append(bank_row(room, target, door['number'], mins, maxs, arrival, yaw, label))
    return rows


def exterior_link(ref, rooms, offsets=None):
    """(target, arrival, yaw) of one exterior load door, or None when unavailable. offsets: room_offsets()
    (None: read from the town table)."""
    cell = ref.get('destination_cell')
    target = rooms.get(cell.casefold()) if cell else None
    if not target or not ref.get('destination'):
        return None
    if offsets is None:
        offsets = room_offsets()
    arrival, yaw = local_arrival(ref['destination'], offset=offsets.get(cell.casefold()))
    return target, arrival, yaw


def bsp_extent(raw):
    """Largest absolute coordinate of any brush model's bounds in a BSP29 file."""
    offset, length = struct.unpack_from('<ii', raw, 4 + 8 * 14)
    if raw[:4] != struct.pack('<i', 29) or length % 64:
        raise ValueError('Expected a BSP29 file')
    extent = 0.
    for at in range(offset, offset + length, 64):
        extent = max(extent, *map(abs, struct.unpack_from('<6f', raw, at)))
    return extent


def build_room_checked(task):
    """prepare_area.build_room plus the coordinate range; returns (status, value). Finished rooms come from the
    room unit cache (prepare_area.build_room_cached; BUILD-IMAGE-NO-RESUME-33).

    A room over its inline model limit is converted again with its nonsolid plants as sprites (step 1 of
    docs/INTERIOR_SECTIONS.md "Interiors over a limit: the order"; interior_plants, AMIWIND_INTERIOR_PLANTS
    =meshes keeps the earlier rule: the room fails). The receipt says which step the room needed."""
    from prepare_area import build_room_cached as build_room
    import interior_plants
    data, scene, entry = task[:3]
    try:
        try:
            report, cell = build_room(task)
            report['limit_steps'] = []
        except ValueError as error:
            if 'inline model budget exceeded' not in str(error) or interior_plants.plant_mode() != 'auto':
                raise
            print('Interior over its model limit, plants as sprites:', entry['map'], str(error), flush=True)
            import shutil as _shutil
            _shutil.rmtree(Path(scene) / 'area-work' / entry['map'], ignore_errors=True)
            task = (task[0], task[1], {**entry, 'plant_sprites': True}, *task[3:])
            report, cell = build_room(task)
            report['limit_steps'] = [{'step': 'plants as sprites', 'because': str(error)}]
        extent = bsp_extent((Path(scene) / 'area-work' / entry['map'] / 'room.bsp').read_bytes())
        report['coordinate_extent'] = extent
        if extent >= COORD_LIMIT:
            raise ValueError('%s: room coordinates reach %.1f, beyond the +-%d network range'
                             % (entry['map'], extent, COORD_LIMIT))
        return 'ok', (report, cell)
    except Exception as error:  # recorded per room by the caller
        return 'failed', '%s: %s' % (type(error).__name__, error)


# The reason of a room a MiniWind interior scope leaves out (convert only_cells; MINIWIND-NO-INTERIOR-SCOPE-42).
ONLY_CELLS_LEFT_OUT = 'not in this build (MiniWind --miniwind-scope interior: its start room only)'


def only_rooms(listed, only_cells, title):
    """listed with every room outside only_cells (cell IDs) excluded as ONLY_CELLS_LEFT_OUT; listed itself when
    only_cells is None. A cell that is no converted room of the list stops the stage."""
    if only_cells is None:
        return listed
    wanted = {cell.casefold() for cell in only_cells}
    unknown = sorted(wanted - {room['cell'].casefold() for room in listed if room['exclude'] is None})
    if unknown:
        raise ValueError('%s: not a converted room of this town: %s' % (title, ', '.join(unknown)))
    return [room if room['cell'].casefold() in wanted or room['exclude'] is not None else
            dict(room, exclude=ONLY_CELLS_LEFT_OUT) for room in listed]


def convert(data, scene, settings, qbsp, vis, light, timings, jobs, vis_mode, dry_run=False, only_cells=None):
    """Convert the town's listed rooms; returns {'rooms', 'cells', 'failed', 'excluded', 'reports'}.
    only_cells: convert only these listed rooms (cell IDs; a MiniWind interior scope); every other room is
    excluded with that reason, and a name that is no listed room stops the stage."""
    from build_parallel import ordered_map
    from vis_options import map_threads
    from interior_plants import plant_mode
    listed = only_rooms(listed_rooms(settings), only_cells, town_field(settings, 'title'))
    work = [room for room in listed if room['exclude'] is None]
    result = {'rooms': {}, 'cells': {}, 'reports': [], 'failed': {},
              'excluded': {room['map']: {'cell': room['cell'], 'reason': room['exclude']}
                           for room in listed if room['exclude'] is not None}}
    if not work:
        return result
    # A room reached only from other rooms takes its spawn from the original
    # interior entrances (the converter's original_door_arrivals option).
    from mwad.interior import original_doors
    from mwad.paths import child_ci
    outside = {door['destination_cell'].casefold() for door in original_doors(child_ci(data, 'Morrowind.esm').read_bytes())
               if not door['source_interior'] and door['destination_interior']}
    workers = min(jobs, len(work))
    tasks = [(data, scene, {'map': room['map'], 'cell': room['cell'], 'interior': True, 'area': 'balmora',
                            **({} if room['cell'].casefold() in outside else {'original_door_arrivals': True}),
                            **({'recentre': room['recentre']} if room.get('recentre') else {}),
                            **({'plant_sprites': True} if room.get('plants') == 'sprites' and plant_mode() == 'auto'
                               else {})},
              qbsp, vis, light, timings, map_threads(jobs, workers), vis_mode) for room in work]
    from build_costs import costed_map, room_sizes
    sizes = room_sizes(data, [(room['map'], room['cell']) for room in work])
    rooms = costed_map('town-%s-rooms' % town_field(settings, 'id'), build_room_checked, tasks,
                       [room['map'] for room in work], workers, fallback=sizes.get if sizes else None)
    for room, (status, value) in zip(work, rooms):
        if status != 'ok':
            # "room_failures": "unavailable" (a town config setting; the whole-city Vivec frame): a room past an
            # engine limit is listed as failed and its doors show it unavailable; the other rooms ship
            if not dry_run and settings.get('room_failures') != 'unavailable':
                raise ValueError(town_field(settings, 'title') + ' interior failed: ' + value)
            result['failed'][room['map']] = {'cell': room['cell'], 'error': value}
            print('Interior failed:', room['map'], value, flush=True)
            continue
        report, cell = value
        shutil.copyfile(Path(scene) / 'area-work' / room['map'] / 'room.bsp', Path(scene) / 'id1/maps' / (room['map'] + '.bsp'))
        # files the room needs besides its map (its plant sprites, interior_plants): same bytes = same file
        for name in (report.get('plant_sprites') or {}).get('sprite_files', {}):
            source, target = Path(scene) / 'area-work' / room['map'] / 'id1' / name, Path(scene) / 'id1' / name
            if target.is_file() and target.read_bytes() != source.read_bytes():
                raise ValueError('Room file %s differs from the one another room wrote' % name)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        result['rooms'][room['map']] = cell
        result['cells'][room['cell'].casefold()] = room['map']
        result['reports'].append(report)
        print('Interior ready:', room['map'], report['bytes'], flush=True)
    return result


def door_mesh_bounds(data, doors):
    """Original door mesh bounds (source units) per door reference."""
    from mwad.audit import BSA
    from mwad.paths import child_ci
    from prepare_scenery import bsa_read, model_geometry, nif_reader, world_bounds
    bsa = BSA(child_ci(data, 'Morrowind.bsa')); reader = nif_reader(); cache = {}; out = {}
    for door in doors:
        model = 'meshes/' + door['model'].replace('\\', '/').lower()
        if model not in cache:
            cache[model] = model_geometry(bsa_read(bsa, model), reader)[2]
        out[door['number']] = world_bounds(cache[model], door)
    return out


def write_room_banks(data, scene, result, root=None, prefer=()):
    """doors-<room>.txt for every converted room; returns the link receipt."""
    from mwad.interior import original_doors
    from mwad.paths import child_ci
    if not result['rooms']:
        return []
    converted = {cell: True for cell in result['cells']}
    converted.update({room['cell'].casefold(): False for room in result['failed'].values()})
    # rooms a MiniWind interior scope left out (convert only_cells) are not in the image: their doors say unavailable
    converted.update({room['cell'].casefold(): False for room in result.get('excluded', {}).values()
                      if room.get('reason') == ONLY_CELLS_LEFT_OUT})
    rooms = available_rooms(root, converted)
    offsets = room_offsets(root)
    towns = frame_towns(root, prefer)
    by_cell = {}
    for door in original_doors(child_ci(data, 'Morrowind.esm').read_bytes()):
        if door['source_interior']:
            by_cell.setdefault(door['source_cell'].casefold(), []).append(door)
    receipt = []
    for name, cell in result['rooms'].items():
        doors = by_cell.get(cell['name'].casefold(), [])
        rows = room_bank(name, doors, rooms, towns, door_mesh_bounds(data, doors), offsets,
                         offsets.get(cell['name'].casefold()))
        (Path(scene) / 'id1' / ('doors-' + name + '.txt')).write_text(bank_text(rows), encoding='cp1252')
        receipt.append({'map': name, 'cell': cell['name'], 'doors': len(rows),
                        'unavailable': sum(1 for r in rows if r.split(' ', 2)[1] == '-')})
    return receipt
