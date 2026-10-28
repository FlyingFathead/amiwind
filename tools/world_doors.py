# SPDX-License-Identifier: GPL-3.0-only
"""The world door table (v0.0.50, CHIM-REGION-DOORS-NO-ROOMS-48): every authored load door and teleport marker of
Morrowind.esm, the frame that holds it and where it leads, both ways, from the game's own door records
(mwad.interior.original_doors: the DOOR references with a destination). Nothing new is placed: the table only links
what the original data links.

One holder rule for every door, the build's own ownership rule (chim/regions.py plan): a town frame holds every point
inside its frame box (actor_grounding_census.area_box; Seyda Neen, Balmora and Vivec were built as towns before the
region frames, and their frames win over the region frames); any other exterior point is held by the CHIM region frame
of its cell; a door inside a room is held by that room's map.

The image step (tools/build_aga.py write_world_doors) runs after the room batch links:
  - every door whose holder bank lacks it gets a row (its box from the door mesh, town_interiors.door_mesh_bounds);
  - every row still "-" gets its target and arrival from the table;
  - a teleport marker (PrisonMarker: where an arrest takes the player) is never a row of a bank (no door to touch):
    it is a row of kind "marker" in the table (world-doors.json), for the jail system and the game's scripts;
  - every door and marker that does not resolve is listed, and the image fails (unresolved_problems): the build
    check of "every exterior entrance linked to its interior".

    python3 tools/world_doors.py audit --data-files DIR --id1 ID1 [--out FILE]
        the same resolution, read only, against a built image's door banks (prints the counts and the unresolved)
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

FORMAT = 'aw-world-doors-1'
SCALE = .25                       # town_interiors.SCALE: Morrowind units to map units
MARKER_IDS = frozenset({'prisonmarker'})
# The opening's maps: the prison ship, the census office, the docks between them and Seyda Neen's courtyard. Their doors
# belong to the opening scene (engine aw_opening.c, aw_intro.c: no leaving the census office before the papers are
# done, and then by one door only), so the table checks them but never writes a row from or into them (the maintainer,
# 24 October 2026).
OPENING_MAPS = frozenset({'prison', 'census', 'intro_docks', 'sncourt'})
EXTERIOR_LABEL = 'Exterior world'  # room_batches.EXTERIOR_LABEL, frame_map.DOOR_LABEL_DEFAULT
DOOR_BANK = 'AWD3'


def kind(door):
    """'marker' for a teleport marker (no door on screen), else 'door'."""
    return 'marker' if door['id'].casefold() in MARKER_IDS else 'door'


def direction(door):
    a = 'room' if door['source_interior'] else 'exterior'
    b = 'room' if door['destination_interior'] else 'exterior'
    return a + '_to_' + b


def town_holders(areas, root=None):
    """[(name, box, centre)] of the CHIM town frames the image holds, in AREAS order: the frame box in Morrowind units
    (the box the build drops region cells for) and the centre the town's map is local to."""
    from actor_grounding_census import area_box
    out = []
    for name in areas:
        if name == 'seyda':
            from chim.seyda import centre
            middle = centre(root)
        else:
            from town_config import load_settings
            middle = load_settings(name, root)['centre']
        out.append((name, tuple(area_box(name, root)), (float(middle[0]), float(middle[1]))))
    return out


def holder(position, towns, regions):
    """(map, kind, frame) of the frame that holds an exterior POSITION: the first town whose box holds it
    (towns: town_holders), else the CHIM region frame of its cell (regions: room_batches.region_frames,
    {(x, y): (map, origin)}); None when the image holds neither."""
    from room_batches import exterior_cell
    for name, box, middle in towns:
        if box[0] <= position[0] <= box[2] and box[1] <= position[1] <= box[3]:
            return name, 'town', middle
    region = regions.get(exterior_cell(position))
    if region is not None:
        return region[0], 'region', region[1]
    return None


def local_point(point, frame_kind, frame):
    """A Morrowind point in the holder map's units: a town map is local to its centre (x, y; town_interiors
    local_arrival), a region frame to its origin (chim.frame_map.region_door_rows), a room map to the room's own
    recentring (frame: its offset or None)."""
    if frame_kind == 'town':
        return [(point[0] - frame[0]) * SCALE, (point[1] - frame[1]) * SCALE, point[2] * SCALE]
    if frame_kind == 'region':
        return [point[k] * SCALE - frame[k] for k in range(3)]
    shift = frame or [0, 0, 0]
    return [(point[k] - shift[k]) * SCALE for k in range(3)]


def exit_target(destination, towns, regions):
    """(map, arrival, yaw) of a way out to the outdoors by the holder rule (the town whose box holds the arrival point,
    else its cell's region frame), or None."""
    from town_interiors import FEET, arrival_yaw
    found = holder(destination['position'], towns, regions)
    if found is None:
        return None
    name, frame_kind, frame = found
    point = local_point(destination['position'], frame_kind, frame)
    point[2] += FEET
    return name, point, arrival_yaw(destination['rotation_radians'][2])


def room_target(destination, cell, rooms, offsets):
    """(map, arrival, yaw) of a way into room CELL (casefolded) the image holds, or None."""
    from town_interiors import local_arrival
    name = rooms.get(cell)
    if not name:
        return None
    arrival, yaw = local_arrival(destination, offset=offsets.get(cell))
    return name, arrival, yaw


def table(doors, rooms, towns, regions, offsets=None):
    """The world door table: one row per authored door and marker. rooms: {original cell casefold: room map} of every
    room the image holds; towns: town_holders; regions: {(x, y): (map, origin)}; offsets: town_interiors.room_offsets.
    Each row: reference, kind, direction, source (map, holder kind) and target (map, arrival, yaw) or the reason it
    does not resolve."""
    offsets = offsets or {}
    rows = []
    for door in sorted(doors, key=lambda d: d['number']):
        row = {'reference': door['number'], 'id': door['id'], 'kind': kind(door), 'direction': direction(door),
               'source_cell': door['source_cell'], 'destination_cell': door['destination_cell'] or EXTERIOR_LABEL}
        if door['source_interior']:
            room = rooms.get(door['source_cell'].casefold())
            source = (room, 'room', offsets.get(door['source_cell'].casefold())) if room else None
        else:
            source = holder(door['position'], towns, regions)
        if door['destination_interior']:
            target = room_target(door['destination'], door['destination_cell'].casefold(), rooms, offsets)
        else:
            target = exit_target(door['destination'], towns, regions)
        if source is None:
            row['problem'] = 'its own place is in no frame or room of this image'
        elif target is None:
            row['problem'] = ('room %s is not in this image' % door['destination_cell'] if door['destination_interior']
                              else 'its exterior arrival is in no frame of this image')
        if source is not None:
            row['source'] = source[0]
            row['holder'] = source[1]
            row['frame'] = list(source[2]) if source[2] is not None else None   # local_point's transform
        if target is not None:
            row['target'] = target[0]
            row['arrival'] = [round(v, 5) for v in target[1]]
            row['yaw'] = round(target[2], 5)
        rows.append(row)
    return rows


def door_box(bounds, frame_kind, frame, pad=None):
    """The door's touch box in the holder map's units from its original mesh bounds (town_interiors.door_mesh_bounds),
    widened by PAD on every side. A room bank widens by half a unit (town_interiors.room_bank); the town banks of
    Seyda Neen and Balmora do too, the Vivec and region frame banks do not (bank_pad measures it per bank)."""
    if pad is None:
        pad = .5 if frame_kind == 'room' else 0.
    low, high = (local_point(corner, frame_kind, frame) for corner in bounds)
    return [v - pad for v in low], [v + pad for v in high]


def bank_pad(lines, holders, door_bounds):
    """The pad the rows of one bank already carry: measured on its first row whose door the table holds (its box
    against door_box with no pad), rounded to a quarter unit; None when no row can be measured."""
    from room_batches import parse_row
    for line in lines[1:]:
        parsed = parse_row(line)
        if parsed is None:
            continue
        reference = int(parsed[0][2])
        if reference not in holders or reference not in door_bounds:
            continue
        _, frame_kind, frame = holders[reference]
        low, _ = door_box(door_bounds[reference], frame_kind, frame, pad=0.)
        box = [float(v) for v in parsed[0][3].split()]
        return round(sum(low[k] - box[k] for k in range(3)) / 3 * 4) / 4
    return None


def bank_path(id1, name):
    """The bank the engine reads for map NAME (aw_scene.c read_links_for: doors-<name>.txt, else scene-doors-<name>.txt),
    or the doors-<name>.txt to write when there is none."""
    for path in (Path(id1) / ('doors-%s.txt' % name), Path(id1) / ('scene-doors-%s.txt' % name)):
        if path.is_file():
            return path
    return Path(id1) / ('doors-%s.txt' % name)


def row_line(source, target, reference, box, arrival, yaw, label):
    from town_interiors import bank_row
    return bank_row(source, target, reference, box[0], box[1], arrival, yaw, label)


def holders_of(rows):
    """{reference: (map, holder kind, frame)} of the table's rows that have a holder."""
    return {row['reference']: (row['source'], row['holder'], row['frame']) for row in rows if 'source' in row}


def apply(id1, rows, door_bounds):
    """Write the table into the image's door banks: a missing door gets its row, a row still "-" its target. door_bounds:
    {reference: original mesh bounds} (town_interiors.door_mesh_bounds). Markers are never written into a bank.
    Returns {'added', 'filled', 'banks_changed': {file: sha256}}."""
    from room_batches import parse_row, row_text
    from town_interiors import BANK_ROWS
    holders = holders_of(rows)
    by_bank = {}
    for row in rows:
        if row['kind'] != 'door' or 'source' not in row or 'target' not in row:
            continue
        if row['source'] in OPENING_MAPS or row['target'] in OPENING_MAPS:
            continue                                   # the opening scene's own doors stay as it wrote them
        by_bank.setdefault(row['source'], []).append(row)
    added, filled, changed = 0, 0, {}
    for name, wanted in sorted(by_bank.items()):
        path = bank_path(id1, name)
        lines = path.read_text(encoding='cp1252').split('\n') if path.is_file() else [DOOR_BANK, '']
        if lines[0] != DOOR_BANK:
            raise ValueError('%s: not an %s door bank' % (path.name, DOOR_BANK))
        if lines[-1] != '':
            lines.append('')
        present = {}
        for i, line in enumerate(lines[1:], 1):
            parsed = parse_row(line)
            if parsed is not None:
                present.setdefault(int(parsed[0][2]), []).append(i)
        dirty = False
        pad = bank_pad(lines, holders, door_bounds)
        for row in wanted:
            numbers = present.get(row['reference'])
            if numbers:
                for i in numbers:
                    fields, separator, label = parse_row(lines[i])
                    if fields[1] != '-':
                        continue
                    fields[1] = row['target']
                    # parse_row fields: source, target, ref, box text, arrival x y z, yaw (as link_banks fills them)
                    fields[4:8] = ['%.5f' % v for v in (*row['arrival'], row['yaw'])]
                    lines[i] = row_text(fields, separator, label)
                    filled += 1
                    dirty = True
                continue
            source_map, frame_kind, frame = holders[row['reference']]
            box = door_box(door_bounds[row['reference']], frame_kind, frame, pad)
            label = row['destination_cell'] if row['direction'] != 'room_to_exterior' else EXTERIOR_LABEL
            lines.insert(len(lines) - 1, row_line(source_map, row['target'], row['reference'], box, row['arrival'],
                                                  row['yaw'], label))
            added += 1
            dirty = True
        rows_now = sum(1 for line in lines[1:] if parse_row(line) is not None)
        if rows_now > BANK_ROWS:
            raise ValueError('%s: %d doors, the engine keeps %d' % (path.name, rows_now, BANK_ROWS))
        if dirty:
            raw = '\n'.join(lines).encode('cp1252')     # the banks are cp1252 (town_interiors.bank_row labels)
            path.write_bytes(raw)
            changed[path.name] = hashlib.sha256(raw).hexdigest()
    return {'added': added, 'filled': filled, 'banks_changed': changed}


TELEPORT_NAMES = 'teleport-names.txt'      # config/ and the game data: dbg tp NAME (engine aw_scene.c named_place)
GLOBAL_PLACE = 'global'                    # the map of an outdoor place: x y z are original global coordinates


def teleport_names(raw):
    """{name: (map, [x, y, z], yaw, label)} of a teleport-names.txt (AWTN1), checked as the engine reads it (name at
    most 23 characters, map 15, label 95; '#' lines are comments). Raises ValueError on a bad line."""
    lines = raw.decode('cp1252').splitlines()
    if not lines or lines[0] != 'AWTN1':
        raise ValueError('%s: the first line must be AWTN1' % TELEPORT_NAMES)
    out = {}
    for number, line in enumerate(lines[1:], 2):
        if not line or line.startswith('#'):
            continue
        parts = line.split('|')
        if len(parts) != 5:
            raise ValueError('%s line %d: name|map|x y z|yaw|label' % (TELEPORT_NAMES, number))
        name, target, point, yaw, label = parts
        values = point.split()
        if (not name or len(name) > 23 or not target or len(target) > 15 or len(values) != 3 or not label
                or len(label.encode('cp1252')) > 95 or name.casefold() in out):
            raise ValueError('%s line %d: a bad or repeated field' % (TELEPORT_NAMES, number))
        out[name.casefold()] = (target, [float(v) for v in values], float(yaw), label)
    return out


def teleport_name_problems(names, rooms):
    """One line per named place whose map is not a room the image holds (rooms: {cell: map})."""
    held = set(rooms.values())
    return ['named place %s: map %s is not in this image' % (name, place[0])
            for name, place in sorted(names.items()) if place[0] != GLOBAL_PLACE and place[0] not in held]


def unresolved_problems(rows):
    """One line per door or marker of the table that does not resolve: the build check (every entrance and every way
    out of the game linked; the image fails otherwise)."""
    return ['%s %d (%s, %s -> %s): %s' % (row['kind'], row['reference'], row['direction'], row['source_cell'] or '?',
                                         row['destination_cell'], row['problem']) for row in rows if 'problem' in row]


def summary(rows):
    out = {}
    for row in rows:
        entry = out.setdefault(row['kind'] + ' ' + row['direction'], {'rows': 0, 'resolved': 0})
        entry['rows'] += 1
        entry['resolved'] += 'problem' not in row
    return out


def audit(data_files, id1):
    """The door audit of a built image, read only: every authored door of the master against the image's door banks.
    A door counts as linked when a bank row of its reference has a target map the engine can run. Returns the
    report (counts per direction and every door that is not linked)."""
    from map_files import map_file, town_map_present
    from mwad.interior import original_doors
    from mwad.paths import child_ci
    from room_batches import parse_row
    doors = original_doors(child_ci(data_files, 'Morrowind.esm').read_bytes())
    id1 = Path(id1)
    maps = id1 / 'maps'
    banks = {}
    for bank in sorted(set(id1.glob('doors-*.txt')) | set(id1.glob('scene-doors*.txt'))):
        lines = bank.read_text(encoding='cp1252').split('\n')
        if not lines or lines[0] != DOOR_BANK:
            continue
        for line in lines[1:]:
            parsed = parse_row(line)
            if parsed is not None:
                banks.setdefault(int(parsed[0][2]), []).append((bank.name, parsed[0][1]))
    runnable = {}

    def can_run(name):
        if name not in runnable:
            # a region frame lives in the CHIM world (its .cut beside the maps); a town runs as <name>-chim
            runnable[name] = name != '-' and (town_map_present(maps, name) or (maps / (name + '.cut')).is_file()
                                              or map_file(maps, name).is_file())
        return runnable[name]

    counts, missing = {}, []
    for door in doors:
        key = kind(door) + ' ' + direction(door)
        entry = counts.setdefault(key, {'rows': 0, 'linked': 0})
        entry['rows'] += 1
        rows = banks.get(door['number'], [])
        if any(can_run(target) for _, target in rows):
            entry['linked'] += 1
        elif kind(door) == 'door':
            missing.append({'reference': door['number'], 'direction': direction(door), 'source_cell': door['source_cell'],
                            'destination_cell': door['destination_cell'] or EXTERIOR_LABEL,
                            'rows': [list(r) for r in rows]})
    return {'doors': len(doors), 'counts': counts, 'not_linked': len(missing), 'missing': missing}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('audit', help='every door of the master against a built image (read only)')
    a.add_argument('--data-files', required=True, type=Path)
    a.add_argument('--id1', required=True, type=Path)
    a.add_argument('--out', type=Path)
    args = parser.parse_args(argv)
    report = audit(args.data_files, args.id1)
    if args.out:
        args.out.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print('doors and markers: %d' % report['doors'])
    for key in sorted(report['counts']):
        print('  %-28s %5d linked of %5d' % (key, report['counts'][key]['linked'], report['counts'][key]['rows']))
    print('doors not linked: %d' % report['not_linked'])
    for row in report['missing'][:60]:
        print('  %d %s: %s -> %s' % (row['reference'], row['direction'], row['source_cell'], row['destination_cell']))
    return 1 if report['not_linked'] else 0


if __name__ == '__main__':
    sys.exit(main())
