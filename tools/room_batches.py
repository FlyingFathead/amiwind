#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Interior rooms by batch: the repo's public room list and the door links of the rooms a build converts.

docs/chim/DOOR_GRAPH.md "Rooms by batch in the builder". The batch plan (tools/door_graph.py plan, private: made from
your game data) orders every Vvardenfell room that can become a CHIM room now into batches. Its public part is
config/room-batches.json (format aw-room-batches-1, written by tools/door_graph.py room-batches): per batch its
number, kind and groups, and per room its cell name (the room's ID in the game data), its order, the exterior cell
its door chain starts from, the exterior cells with a load door straight into it, its door depth and its map name.
Room names are already public in the docs; positions and other game data are never in it. The builder converts the
batches `--room-batches` selects (stage chim-room-batches, tools/chim_room_batches.py) and the image links every door
of a converted room both ways (link_banks).

Map names: a room some town list or the fixed scene lists already hold keeps that map name (its save ID); every other
room is `ri` + the first 10 hex digits of the SHA-256 of its cell name in lower case (room_map), so the name is the
same in every build and never depends on the list's order. The engine knows them from aw_town_table.h
(AW_ROOM_BATCH_*, tools/town_table.py) by each room's id, its save ID from AW_ROOM_BATCH_BASE (aw_maps.h): an id is
given once and never moves or returns (room-batches keeps the previous list's ids and gives a new room the next one).
"""
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = 'room-batches.json'
FORMAT = 'aw-room-batches-1'
ID_LIMIT = 4096                # AW_ROOM_BATCH_BASE..+4096 (aw_maps.h)
MAP_PREFIX = 'ri'
MAP_DIGITS = 10
MAP_NAME = re.compile(r'ri[0-9a-f]{10}$')
CELL = re.compile(r'-?\d+,-?\d+$')
TITLE_MAX = 63                 # engine title buffers (town_config.TITLE_MAX)
SELECTION_ALL, SELECTION_NONE = 'all', 'none'
# The build option's shipped default (docs/chim/DOOR_GRAPH.md "Rooms by batch in the builder"): none until the
# maintainer decides, by the shipped-default rule (an experimental feature is off by default); proposed: all.
DEFAULT = SELECTION_NONE
MW_CELL = 8192.0               # Morrowind units per exterior cell
SCALE = .25
FEET = 16.875                  # town_interiors.FEET: the feet-to-origin lift of every converted arrival
EXTERIOR_LABEL = 'Exterior world'
ROW = re.compile(r'^(\S+) (\S+) (\d+) ((?:\S+ ){6})(\S+) (\S+) (\S+) (\S+)([ \t])(.*)$')


# ------------------------------------------------------------------ the public room list

def room_map(cell):
    """The batch map name of a room no town or scene list names: ri + 10 hex digits of SHA-256(cell, lower case)."""
    return MAP_PREFIX + hashlib.sha256(cell.casefold().encode('utf-8')).hexdigest()[:MAP_DIGITS]


def check(doc):
    """Problems of a room list (empty when it is sound)."""
    problems = []
    if not isinstance(doc, dict) or doc.get('format') != FORMAT:
        return ['not an %s document' % FORMAT]
    seen, maps, numbers, ids = set(), set(), [], set()
    for b in doc.get('batches') or []:
        n = b.get('batch')
        if type(n) is not int or n < 1:
            problems.append('batch number %r' % (n,))
            continue
        numbers.append(n)
        for order, row in enumerate(b.get('rooms') or []):
            name = row.get('room')
            if not isinstance(name, str) or not name or len(name) > TITLE_MAX or not name.isascii() or \
                    any(c in name for c in '"\\') or any(ord(c) < 32 for c in name):
                problems.append('batch %d: invalid room name %r' % (n, name))
                continue
            if name.casefold() in seen:
                problems.append('room listed twice: %s' % name)
            seen.add(name.casefold())
            if row.get('map') != room_map(name):
                problems.append('%s: map %r is not %s' % (name, row.get('map'), room_map(name)))
            if row.get('map') in maps:
                problems.append('two rooms share the map name %s' % row.get('map'))
            maps.add(row.get('map'))
            if row.get('order') != order + 1:
                problems.append('%s: order %r, expected %d (its place in batch %d)' % (name, row.get('order'),
                                                                                       order + 1, n))
            if type(row.get('id')) is not int or not 0 <= row['id'] < ID_LIMIT or row['id'] in ids:
                problems.append('%s: id %r is not a free number below %d' % (name, row.get('id'), ID_LIMIT))
            ids.add(row.get('id'))
            for cell in [row.get('entrance')] * (row.get('entrance') is not None) + list(row.get('doors_from') or []):
                if not isinstance(cell, str) or not CELL.match(cell):
                    problems.append('%s: entrance cell %r is not "x,y"' % (name, cell))
            if 'cell' in row:
                problems.append('%s: "cell" is the scene lists\' key (cell_progress.our_maps reads it as a room in '
                                'the game); the room list names rooms by "room"' % name)
    if numbers != sorted(set(numbers)):
        problems.append('batch numbers not unique and ascending: %s' % numbers)
    if ids and not (type(doc.get('next_id')) is int and doc['next_id'] > max(i for i in ids if type(i) is int)):
        problems.append('next_id %r must be past every id' % (doc.get('next_id'),))
    return problems


def dumps(doc):
    """The room list as text: one line per room, so a change to a room is a one-line diff."""
    head = {k: v for k, v in doc.items() if k != 'batches'}
    lines = ['{'] + ['  %s: %s,' % (json.dumps(k), json.dumps(v)) for k, v in head.items()] + ['  "batches": [']
    for i, b in enumerate(doc['batches']):
        meta = {k: v for k, v in b.items() if k != 'rooms'}
        lines.append('    ' + json.dumps(meta)[:-1] + ', "rooms": [')
        lines += ['      ' + json.dumps(r) + (',' if j + 1 < len(b['rooms']) else '') for j, r in enumerate(b['rooms'])]
        lines.append('    ]}' + (',' if i + 1 < len(doc['batches']) else ''))
    lines += ['  ]', '}']
    text = '\n'.join(lines) + '\n'
    if json.loads(text) != doc:
        raise ValueError('room list text does not read back as the list')
    return text


def from_plan(plan, graph, previous=None):
    """The public room list of a batch plan (aw-batch-plan-1) and its door graph (aw-door-graph-1): per batch its number,
    kind, groups and rooms; per room its name, map name, id (assign_ids), order in the batch, the exterior cell its door
    chain starts from, the exterior cells with a load door straight into it, its door depth and, in the parity batch,
    its state. Nothing else of the game data."""
    rooms = {r['name'].casefold(): r for r in graph['rooms']}
    names = [n for b in plan['batches'] for n in b['rooms']]
    ids, next_id = assign_ids(names, previous)
    states = {p['room'].casefold(): p['state'] for b in plan['batches'] for p in b.get('parity', ())}
    batches = []
    for b in plan['batches']:
        out = []
        for order, name in enumerate(b['rooms'], 1):
            r = rooms[name.casefold()]
            row = {'room': r['name'], 'map': room_map(r['name']), 'id': ids[name.casefold()], 'order': order,
                   'entrance': r.get('entrance_exterior'),
                   'doors_from': sorted({e['from'] for e in r.get('entrances', ()) if not e.get('from_interior')},
                                        key=lambda c: tuple(map(int, c.split(',')))),
                   'depth': r.get('depth')}
            if name.casefold() in states:
                row['state'] = states[name.casefold()]
            out.append(row)
        batches.append({'batch': b['batch'], 'kind': b['kind'], 'groups': list(b['groups']), 'part': b.get('part', 0),
                        'rooms': out})
    doc = {'format': FORMAT, 'generator': 'tools/door_graph.py room-batches',
           'about': 'The interior rooms the builder converts by batch (--room-batches; docs/chim/DOOR_GRAPH.md "Rooms '
                    'by batch in the builder"), made from the batch plan of the door graph: per room its name (the '
                    'cell ID in the game data), its map name (tools/room_batches.py room_map), its save id, its order '
                    'in the batch, the exterior cell its door chain starts from, the exterior cells with a load door '
                    'straight into it and its door depth. Rooms with water, lava or reached only by Levitate are '
                    'listed like any room; rooms set aside (lava at or under the water, over the size limit of the '
                    '32 MiB minimum machine, behaves like an exterior) and the expansions\' later batches are not '
                    'listed. No positions or other game data.',
           'island': plan.get('island', 'Vvardenfell'), 'order': plan.get('order'), 'next_id': next_id,
           'batches': batches}
    problems = check(doc)
    if problems:
        raise ValueError('room list: ' + '; '.join(problems[:6]))
    return doc


def load(root=None):
    """The repo's room list (config/room-batches.json), checked; None when the repo has none."""
    path = Path(root or ROOT) / 'config' / CONFIG
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding='utf-8'))
    problems = check(doc)
    if problems:
        raise ValueError('%s: %s' % (path.name, '; '.join(problems[:6])))
    return doc


def rows(doc):
    """Every room row of a room list, in list order, with its batch number."""
    return [dict(row, batch=b['batch']) for b in (doc or {}).get('batches', []) for row in b['rooms']]


def numbers(doc):
    return [b['batch'] for b in (doc or {}).get('batches', [])]


def parse_selection(text, doc=None):
    """The batch numbers a --room-batches value names: none, all (every batch of the list), N, N-M, or a comma list
    of those. A number the list does not hold is refused (with the list's numbers)."""
    if text is None:
        text = DEFAULT
    value = str(text).strip().casefold()
    have = numbers(doc)
    if value == SELECTION_NONE:
        return []
    if value == SELECTION_ALL:
        return list(have)
    chosen = set()
    for part in value.split(','):
        part = part.strip()
        m = re.fullmatch(r'(\d+)(?:-(\d+))?', part)
        if not m:
            raise ValueError('--room-batches takes none, all, N, N-M or a comma list of them, not %r' % text)
        low, high = int(m.group(1)), int(m.group(2) or m.group(1))
        if low < 1 or high < low:
            raise ValueError('--room-batches: %r is not a batch range' % part)
        chosen.update(range(low, high + 1))
    missing = sorted(chosen - set(have))
    if missing:
        raise ValueError('--room-batches: no batch %s in config/%s (it has %s)'
                         % (', '.join(map(str, missing)), CONFIG, describe_numbers(have) or 'none'))
    return sorted(chosen)


def describe_numbers(values):
    """'1-3, 5' for [1, 2, 3, 5]."""
    out, values = [], sorted(values)
    for v in values:
        if out and out[-1][1] == v - 1:
            out[-1][1] = v
        else:
            out.append([v, v])
    return ', '.join('%d' % a if a == b else '%d-%d' % (a, b) for a, b in out)


def selection_text(chosen):
    return describe_numbers(chosen) if chosen else SELECTION_NONE


# ------------------------------------------------------------------ map names and the rooms other stages convert

def listed_maps(root=None):
    """{cell casefold: map} of the rooms the repo's town lists (town_config.town_interiors) and fixed scene lists
    (area_config.SCENES interiors) already name; a cell with more than one map (a sectioned room) maps to None."""
    import area_config
    from town_config import town_interiors
    out = {}
    for scene in area_config.SCENES:
        if scene.get('interior') is True and scene.get('cell'):
            key = scene['cell'].casefold()
            out[key] = scene['map'] if key not in out else None
    for room in town_interiors(root):
        key = room['cell'].casefold()
        out[key] = room['map'] if key not in out else None
    return out


def engine_rows(doc=None, root=None):
    """The engine table of the batch rooms (AW_ROOM_BATCH_*, tools/town_table.py): [(map, title)] indexed by the rooms'
    ids (their save IDs from AW_ROOM_BATCH_BASE); a room a town or scene list holds (it has its own map name and save
    ID) and an id no row has are ("", "")."""
    doc = load(root) if doc is None else doc
    listed = listed_maps(root)
    table = rows(doc)
    out = [('', '')] * (max((r['id'] for r in table), default=-1) + 1)
    for row in table:
        if row['room'].casefold() not in listed:
            out[row['id']] = (row['map'], row['room'])
    return out


def assign_ids(names, previous=None):
    """{room casefold: id}: a room of the previous list keeps its id (save IDs never move); a new room takes the next
    number after every id ever given (the previous list's 'next_id'), in list order."""
    old = {r['room'].casefold(): r['id'] for r in rows(previous)} if previous else {}
    nxt = max([(previous or {}).get('next_id', 0)] + [v + 1 for v in old.values()])
    out = {}
    for name in names:
        key = name.casefold()
        if key in old:
            out[key] = old[key]
        else:
            out[key] = nxt
            nxt += 1
    return out, nxt


def build_map(row, listed):
    """The map name a build gives a room of the list: its town or scene list's name, else its batch name; None for a
    sectioned room (its own stage converts it)."""
    key = row['room'].casefold()
    if key in listed:
        return listed[key]
    return row['map']


def stage_cells(stage, root=None):
    """{cell casefold} a room stage of the plan converts: interior (Seyda Neen's rooms), balmora-interiors,
    chim-rooms-TOWN and town-TOWN (the town's listed rooms, not excluded). Other stages: none."""
    import area_config
    if stage == 'interior':
        return {s['cell'].casefold() for s in area_config.AREA['scenes'] if s.get('interior') is True and s.get('cell')}
    if stage == 'balmora-interiors':
        return {s['cell'].casefold() for s in area_config.BALMORA_INTERIORS}
    for prefix in ('chim-rooms-', 'town-'):
        if stage.startswith(prefix):
            from chim_rooms import listed_rooms
            return {room['cell'].casefold() for room in listed_rooms(stage[len(prefix):], root)}
    return set()


def room_stages(names):
    """The stages of a plan (names) whose rooms the batch stage leaves to them."""
    return [n for n in names if n in ('interior', 'balmora-interiors') or n.startswith(('chim-rooms-', 'town-'))]


def plan(doc, chosen, held_stages=(), root=None):
    """The rooms a build's batch stage converts: (convert, held, refused). convert: rows with 'build_map' (and the
    town row's 'recentre' when it has one); held: {room: stage} converted by another stage of the plan; refused:
    {room: reason} (a sectioned room)."""
    listed = listed_maps(root)
    by_stage = {}
    for stage in held_stages:
        for cell in stage_cells(stage, root):
            by_stage.setdefault(cell, stage)
    offsets = {}
    try:
        from town_interiors import room_offsets
        offsets = room_offsets(root)
    except (OSError, ValueError, KeyError):
        pass
    convert, held, refused = [], {}, {}
    wanted = set(chosen)
    for row in rows(doc):
        if row['batch'] not in wanted:
            continue
        key = row['room'].casefold()
        if key in by_stage:
            held[row['room']] = by_stage[key]
            continue
        name = build_map(row, listed)
        if name is None:
            refused[row['room']] = 'a sectioned room: more than one map in the scene lists (its own stage converts it)'
            continue
        convert.append(dict(row, build_map=name, **({'recentre': offsets[key]} if key in offsets else {})))
    return convert, held, refused


# ------------------------------------------------------------------ the door links (image step)

def parse_row(line):
    """(fields, separator, label) of an AWD3 door bank row: fields = [source, target, ref, box text, ax, ay, az,
    yaw]; None for a line that is no row."""
    m = ROW.match(line.rstrip('\r\n'))
    if not m:
        return None
    return list(m.groups()[:8]), m.group(9), m.group(10)


def row_text(fields, separator, label):
    return '%s %s %s %s%s %s %s %s%s%s' % (*fields, separator, label)


def exterior_cell(position):
    return int(math.floor(position[0] / MW_CELL)), int(math.floor(position[1] / MW_CELL))


def room_arrival(destination, offset=None):
    """A load door's arrival in its room's own units (town_interiors.local_arrival without a frame)."""
    from town_interiors import local_arrival
    point, yaw = local_arrival(destination, offset=offset)
    return point, yaw


def frame_arrival(destination, frames):
    """(map, arrival, yaw) of an exit into the outdoors, or None: the first town frame (frames['towns'], the engine's
    first-in-table-order handoff rule, town_interiors.exit_town) whose core holds the point, else the CHIM region
    frame of its exterior cell (frames['regions']: {(x, y): (map, origin)}; the frame-local units of
    chim.frame_map.region_door_rows)."""
    from town_interiors import arrival_yaw, exit_town, local_arrival
    position = destination['position']
    town = exit_town(position, frames.get('towns') or [])
    if town is not None:
        point, yaw = local_arrival(destination, town[2])
        return town[0], point, yaw
    region = (frames.get('regions') or {}).get(exterior_cell(position))
    if region is not None:
        name, origin = region
        point = [position[k] * SCALE - origin[k] for k in range(3)]
        point[2] += FEET
        return name, point, arrival_yaw(destination['rotation_radians'][2])
    return None


def link_banks(id1, batch_rooms, present, doors, frames, offsets=None, listed=None):
    """Link every door of the rooms the batch stage converted, both ways, in the door banks of an image (id1/doors-*.txt
    and id1/scene-doors-*.txt): a row whose target is "-" gets its target and arrival when
      - its door leads into a converted batch room (exterior to room, room to room), or
      - it is a door of a converted batch room: into any room the image holds (present), or out to the outdoors
        (frame_arrival: a town frame or a CHIM region frame the image holds).
    Every other row is left as it is. batch_rooms: {cell casefold: map} of the batch stage's rooms; present: {cell
    casefold: map} of every room map the image holds (the batch rooms included); doors: mwad.interior.original_doors;
    offsets: town_interiors.room_offsets() (arrivals into a recentred room); listed: {cell casefold} of every room of
    the room list (the doors into a listed room not converted in this build are listed as unlinked). Returns the
    receipt: counts per kind and every row of a batch room, or into a listed room, left unlinked, with the reason."""
    id1 = Path(id1)
    offsets = offsets or {}
    listed = set(listed or ())
    by_number = {}
    for door in doors:
        by_number.setdefault(door['number'], []).append(door)
    batch_maps = {m: cell for cell, m in batch_rooms.items()}
    kinds = {'exterior_to_room': 0, 'room_to_exterior': 0, 'room_to_room': 0}
    unlinked, files = [], {}
    banks = sorted(set(id1.glob('doors-*.txt')) | set(id1.glob('scene-doors-*.txt')))
    for bank in banks:
        lines = bank.read_text(encoding='cp1252').split('\n')
        if not lines or lines[0] != 'AWD3':
            continue
        changed = False
        for i, line in enumerate(lines[1:], 1):
            parsed = parse_row(line)
            if parsed is None:
                continue
            fields, separator, label = parsed
            source, target, number = fields[0], fields[1], int(fields[2])
            if target != '-':
                continue
            from_batch = source in batch_maps
            candidates = by_number.get(number, [])
            if from_batch:
                candidates = [d for d in candidates if d['source_cell'].casefold() == batch_maps[source]]
            candidates = [d for d in candidates if (d['destination_cell'] or EXTERIOR_LABEL) == label] or candidates
            if len(candidates) != 1:
                if from_batch:
                    unlinked.append({'bank': bank.name, 'reference': number, 'label': label,
                                     'reason': 'door %d: %d original doors match (game data)' % (number, len(candidates))})
                continue
            door = candidates[0]
            dest_cell = (door['destination_cell'] or '').casefold()
            link = None
            if door['destination_interior']:
                if dest_cell in batch_rooms or (from_batch and dest_cell in present):
                    point, yaw = room_arrival(door['destination'], offsets.get(dest_cell))
                    link = (present.get(dest_cell) or batch_rooms[dest_cell], point, yaw,
                            'room_to_room' if door['source_interior'] else 'exterior_to_room')
                elif from_batch or dest_cell in listed:
                    unlinked.append({'bank': bank.name, 'reference': number, 'label': label,
                                     'reason': 'room not converted in this build'})
            elif from_batch:
                found = frame_arrival(door['destination'], frames)
                if found is None:
                    unlinked.append({'bank': bank.name, 'reference': number, 'label': label,
                                     'reason': 'exterior cell %d,%d: no town or CHIM region frame in this build'
                                               % exterior_cell(door['destination']['position'])})
                else:
                    link = (found[0], found[1], found[2], 'room_to_exterior')
            if link is None:
                continue
            fields[1] = link[0]
            fields[4:8] = ['%.5f' % v for v in (*link[1], link[2])]
            lines[i] = row_text(fields, separator, label)
            kinds[link[3]] += 1
            changed = True
        if changed:
            text = '\n'.join(lines)
            bank.write_text(text, encoding='cp1252', newline='\n')
            files[bank.name] = hashlib.sha256(text.encode('cp1252')).hexdigest()
    return {'linked': kinds, 'banks_changed': files, 'unlinked': unlinked,
            'unlinked_count': len(unlinked)}


def region_frames(table, region_maps):
    """{(x, y): (map, origin)} of the CHIM region frames an image wrote: the region table's frames (chim-regions.json,
    in table order) with the frame map records chim.frame_map.build_regions returned in the same order."""
    out = {}
    if not table:
        return out
    for frame, record in zip(table.get('frames') or [], region_maps or []):
        name = Path(str(record.get('map', ''))).stem
        if name:
            out[tuple(frame['cell'])] = (name, list(frame['origin']))
    return out


def install_threads(jobs):
    """Threads of the room batch install (BUILD-IMAGE-UNDERUSED-32): the stage's live cores (JOBS), or
    AMIWIND_ROOM_INSTALL_THREADS (1: one file at a time, the method before v0.0.48)."""
    import os
    try:
        wanted = int(os.environ.get('AMIWIND_ROOM_INSTALL_THREADS', '0'))
    except ValueError:
        wanted = 0
    if wanted >= 1:
        return wanted
    from build_jobs import resolve_jobs
    from build_parallel import live_jobs
    return max(1, live_jobs(resolve_jobs(jobs)))


def install(stage_dir, id1, jobs=None):
    """Image step: copy the batch stage's id1 files (room maps, room door banks, residents, sprites) into the image.
    A file the image already holds with other bytes is refused (one file, two sources); the same bytes are the same
    file. Returns {'rooms': {cell casefold: map}, 'files': n, 'record': the stage's record}. JOBS: the threads that
    hash and copy (install_threads)."""
    import shutil
    stage_dir, id1 = Path(stage_dir), Path(id1)
    record = json.loads((stage_dir / RECORD).read_text(encoding='utf-8'))
    if record.get('format') != STAGE_FORMAT:
        raise ValueError('Not a room batches output: %s' % stage_dir)
    conflicts = []
    threads = install_threads(jobs)
    if threads > 1:
        # BUILD-IMAGE-UNDERUSED-32: 13,141 files (1.7 GB) hashed twice and copied one by one, silently, 5 to 14 s
        # on one core of the image step; now hashed and copied on the stage's threads (reading, hashing and copying
        # release the interpreter lock), the same checks in the same order and the same files
        from build_parallel import hash_existing, hash_files
        rels = list(record['files'])
        sources = hash_files([stage_dir / 'id1' / rel for rel in rels], threads)
        targets = hash_existing([id1 / rel for rel in rels], threads)
        for rel, source_sha, target_sha in zip(rels, sources, targets):
            sha = record['files'][rel]
            if source_sha != sha:
                conflicts.append('%s: changed since the stage wrote it' % rel)
            elif target_sha is not None and target_sha != sha:
                conflicts.append('%s: staged in the image with other bytes' % rel)
    else:
        for rel, sha in record['files'].items():
            source, target = stage_dir / 'id1' / rel, id1 / rel
            if hashlib.sha256(source.read_bytes()).hexdigest() != sha:
                conflicts.append('%s: changed since the stage wrote it' % rel)
            elif target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() != sha:
                conflicts.append('%s: staged in the image with other bytes' % rel)
    if conflicts:
        raise ValueError('Room batches collide with the image: %s' % '; '.join(conflicts[:8]))
    for folder in sorted({(id1 / rel).parent for rel in record['files']}):
        folder.mkdir(parents=True, exist_ok=True)
    if threads > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=threads) as pool:
            for _ in pool.map(lambda rel: shutil.copyfile(stage_dir / 'id1' / rel, id1 / rel), list(record['files']),
                              chunksize=64):
                pass
    else:
        for rel in record['files']:
            shutil.copyfile(stage_dir / 'id1' / rel, id1 / rel)
    return {'rooms': {r['room'].casefold(): r['map'] for r in record['rooms']}, 'files': len(record['files']),
            'record': record}


def staged_rooms(id1, stage_dir):
    """The batch rooms an image holds (a room map or a CHIM room map), from the stage's record."""
    from map_files import map_file
    if not stage_dir:
        return []
    path = Path(stage_dir) / RECORD
    if not path.is_file():
        return []
    record = json.loads(path.read_text(encoding='utf-8'))
    return [r['map'] for r in record.get('rooms', []) if map_file(Path(id1) / 'maps', r['map']).is_file()]


RECORD = 'room-batches.json'
STAGE_FORMAT = 'AmiWind room batches 1'
