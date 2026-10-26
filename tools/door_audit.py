# SPDX-License-Identifier: GPL-3.0-only
"""The door entrance audit (DOOR-ENTRANCE-AUDIT-51): one checklist row per load door of the original game that leads
from an exterior cell into an interior, checked the way the engine uses a door, not only on paper.

The image's own door table (image/world-doors.json, tools/world_doors.py) proves that every door has a row with a
target: the v0.0.51 final said all 3,133 resolve, yet five exterior entrances could not be entered in play. This audit
follows the engine's path (engine/aga/src/aw_scene.c):
  - read_links_for(sv.name): the engine reads ONE door bank, doors-<running map>.txt (else scene-doors-<map>.txt), and
    keeps a row only when it parses as AWD3 (14 fields), both map names are maps the engine knows (aw_maps.h AW_MapId,
    the generated aw_town_table.h), the box is at most 256 units a side, every value within +/-32768, the yaw in
    [0, 360) and the label has no control character; at most AW_SCENE_LINKS (256) rows are kept;
  - aimed_door: only rows whose source is the running map, a ray from the eye within 56 units of the row's box, in
    the running map's coordinates;
  - with "chim crossing 1" (default-game.cfg, the default since v0.0.47) a crossing between two region frames streams
    (chim_chunks.c window): the running map keeps the frame the map started on, so only that frame's bank is read.
    A region frame's door is then usable only when the player came into its frame by a level change (a door out of a
    room, a teleport, a load, a crossing from a town), never after walking in from another region frame.
Per door: its number, id and model; its exterior cell and position; the interior it leads to; the original lock level
and key; the CHIM region or town frame that holds it; whether that frame places the door (CHIM source); whether the
holder's bank has an engine-valid row for it whose box holds the placed door; whether the target is a map the engine
runs and the arrival is inside the room; whether the room's way out leads back to the right exterior; the reason for
every check that fails; and whether it can be used after walking in.

    python3 tools/door_audit.py --data-files DIR --build BUILD --out DIR [--spot GX GY GZ LX LY LZ ...] [--jobs N]
        BUILD: a build folder (image/boot/id1, image/world-doors.json, chim-world/, engine/runtime/src, the room
        records in chim-interiors/); --id1, --world-doors, --chim-world, --engine-src and --room-store name them one
        by one instead. --spot: a place a player could not
        enter a door, as the engine's position line gives it (global original units, then the running map's local
        units): the audit names the door, the frame the player's map was and why that door was not usable there.
        Writes OUT/door-audit.json, OUT/door-checklist.csv and OUT/door-audit.md (private: built from your game data).
"""
import argparse
import csv
import json
import math
import mmap
import os
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

FORMAT = 'aw-door-audit-1'
SCALE = .25                 # Morrowind units to map units (town_interiors.SCALE)
CELL_MAP = 2048             # one exterior cell in map units (8192 Morrowind units)
SCENE_LINKS = 256           # aw_scene.c AW_SCENE_LINKS
REACH = 56.0                # aw_scene.c door_hit: the use ray's length
LINE_BYTES = 384            # aw_scene.c read_links_for: fgets buffer
BOX_TOLERANCE = 4.0         # map units: the placed door and its original place agree this closely
BOX_REACH = 96.0            # map units: a door mesh's bounds lie this near its placed origin (yurt flaps: up to 80)
ROOM_TOLERANCE = 32.0       # map units: an arrival this far outside the room record's bounds still lands inside
BACK_DISTANCE = 1024.0      # Morrowind units: a way out "comes back" when it arrives this near the entrance door
EXIT_SEARCH = 4096.0        # Morrowind units: the room's exits searched for the one that leads back to this door
MARKER_IDS = frozenset({'prisonmarker'})   # world_doors.MARKER_IDS: a teleport marker has no door to use
OPENING_MAPS = frozenset({'prison', 'census', 'intro_docks', 'sncourt'})   # world_doors.OPENING_MAPS
WALK_IN = 'yes'
LEVEL_CHANGE_ONLY = 'only after a level change into its frame'

_NAME = r'(\S+)'
_NUM = r'([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)'
ROW3 = re.compile(r'^\s*' + r'\s+'.join([_NAME, _NAME, r'(\d+)'] + [_NUM] * 10) + r'\s+([^\r\n]*)')


# ------------------------------------------------------------------ the engine's names and door banks

def c_strings(text):
    return re.findall(r'"((?:[^"\\]|\\.)*)"', text)


def engine_map_names(maps_h, table_h):
    """The map names the engine knows (aw_maps.h AW_MapId) from the texts of aw_maps.h and the generated
    aw_town_table.h: {'fixed', 'interior', 'extra', 'town_interior', 'room_batch'} name sets. The vfNNNN terrain
    names are a rule (map_valid), not a list."""
    def block(pattern, text):
        m = re.search(pattern, text, re.S)
        return set(c_strings(m.group(1))) - {''} if m else set()
    return {'fixed': block(r'AW_MapId\(const char \*name\)\s*\{\s*static const char \*const names\[[^\]]*\]\s*=\s*'
                           r'\{(.*?)\};', maps_h),
            'interior': block(r'AW_InteriorMapName\(int n\)\s*\{\s*static const char \*const names\[[^\]]*\]\s*=\s*'
                              r'\{(.*?)\};', maps_h),
            'extra': block(r'#define AW_TOWN_EXTRA_NAMES\s*\{(.*?)\}', table_h),
            'town_interior': block(r'#define AW_TOWN_INTERIOR_NAMES\s*\{(.*?)\}', table_h),
            'room_batch': block(r'#define AW_ROOM_BATCH_NAMES\s*\{(.*?)\}', table_h)}


def terrain_id(name):
    """aw_maps.h AW_TerrainId: vf and four digits below 8192, else -1."""
    if len(name) != 6 or not name.startswith('vf') or not name[2:].isdigit():
        return -1
    n = int(name[2:])
    return n if n < 8192 else -1


def map_valid(name, names):
    """aw_scene.c map_valid (AW_MapId(name) >= 0) over engine_map_names."""
    if name in names['fixed'] or terrain_id(name) >= 0 or name in names['interior'] or name in names['extra'] \
            or name in names['town_interior']:
        return True
    return name.startswith('ri') and len(name) == 12 and name in names['room_batch']


def parse_bank(text, names):
    """The rows the engine keeps of one door bank TEXT (aw_scene.c read_links_for, AWD3): {'version', 'links':
    [{'index', 'line', 'source', 'target', 'reference', 'mins', 'maxs', 'arrival', 'yaw', 'label'}], 'dropped':
    [{'line', 'reference', 'reason'}]}. A bank of another version keeps nothing here (only AWD3 is written now)."""
    lines = text.split('\n')
    out = {'version': lines[0] if lines else '', 'links': [], 'dropped': []}
    if not lines or lines[0].rstrip('\r') != 'AWD3':
        return out
    for number, line in enumerate(lines[1:], 2):
        if not line.strip():
            continue
        m = ROW3.match(line)
        ref = None
        if m:
            ref = int(m.group(3))
        elif len(line.split()) > 2 and line.split()[2].isdigit():
            ref = int(line.split()[2])          # a short row still names its door
        reason = None
        if len(line) + 1 >= LINE_BYTES:
            reason = 'line longer than the engine reads (%d bytes)' % (LINE_BYTES - 1)
        elif not m or not m.group(14):
            reason = 'not 14 fields'
        else:
            source, target = m.group(1), m.group(2)
            values = [float(m.group(k)) for k in range(4, 14)]
            mins, maxs, arrival, yaw = values[0:3], values[3:6], values[6:9], values[9]
            label = m.group(14)[:95]
            if len(source) > 15 or len(target) > 15:
                reason = 'a map name over 15 characters'
            elif not map_valid(source, names):
                reason = 'source map %s is not a map the engine knows' % source
            elif not map_valid(target, names) and target != '-':
                reason = 'target map %s is not a map the engine knows' % target
            elif any(ord(c) < 32 for c in label):
                reason = 'a control character in the label'
            elif not all(abs(mins[k]) < 32768 and abs(maxs[k]) < 32768 and maxs[k] >= mins[k]
                         and maxs[k] - mins[k] <= 256 and abs(arrival[k]) < 32768 for k in range(3)):
                reason = 'box or arrival out of the engine range (a side over 256 or a value past 32768)'
            elif not 0 <= yaw < 360:
                reason = 'yaw outside [0, 360)'
        if reason is None and len(out['links']) >= SCENE_LINKS:
            reason = 'past the %d rows the engine keeps' % SCENE_LINKS
        if reason is not None:
            out['dropped'].append({'line': number, 'reference': ref, 'reason': reason})
            continue
        out['links'].append({'index': len(out['links']), 'line': number, 'source': source, 'target': target,
                             'reference': ref, 'mins': mins, 'maxs': maxs, 'arrival': arrival, 'yaw': yaw,
                             'label': label})
    return out


def crossing_mode(cfg_text):
    """The cell crossing method a default-game.cfg leaves (its last "chim crossing 0|1" line; 0 without one)."""
    mode = 0
    for line in cfg_text.split('\n'):
        m = re.match(r'\s*chim crossing\s+([01])\s*$', line.split('//')[0])
        if m:
            mode = int(m.group(1))
    return mode


# ------------------------------------------------------------------ geometry

def box_gap(mins, maxs, point):
    """Distance from POINT to the box (0 inside)."""
    return math.sqrt(sum(max(mins[k] - point[k], 0, point[k] - maxs[k]) ** 2 for k in range(len(point))))


def directory_frame(directory, point):
    """(name, origin) of the first open-world directory row (chim.frame_map.world_directory: name, origin, core)
    whose core holds map-unit POINT (global map units), as the engine takes it; None outside every row."""
    for name, origin, core in directory:
        x, y = point[0] - origin[0], point[1] - origin[1]
        if core[0] <= x <= core[2] and core[1] <= y <= core[3]:
            return name, origin
    return None


def running_origin(global_point, local_point):
    """The running map's origin (map units) from the engine's position line: global Morrowind units and the same
    point in the running map's units."""
    return [global_point[k] * SCALE - local_point[k] for k in range(3)]


def lock_of(door):
    """(lock level, key id) of an original reference from its subrecords (mwad.interior original_subrecords:
    FLTV int32, KNAM the key); (0, '') when it is not locked."""
    level, key = 0, ''
    for sub in door.get('original_subrecords') or []:
        raw = bytes.fromhex(sub['hex'])
        if sub['tag'] == 'FLTV' and len(raw) == 4:
            level = struct.unpack('<i', raw)[0]
        elif sub['tag'] == 'KNAM':
            key = raw.split(b'\0', 1)[0].decode('cp1252', 'replace')
    return level, key


# ------------------------------------------------------------------ the CHIM source: what each frame places

def _lines(path, start, end):
    """The lines (no newline) of bytes [start, end) of PATH, read one at a time (a worker never holds its range)."""
    with open(path, 'rb') as f:
        f.seek(start)
        at = start
        while at < end:
            raw = f.readline()
            if not raw:
                break
            at += len(raw)
            yield raw.rstrip(b'\n').decode('utf-8')


def _source_unit(task):
    """Worker: the frames of one byte range of chim-source.json (written by parallel_json.dumps, indent 1): per frame
    its cell, town, the references its placements select, the pieces it owns (origin, story hidden) and its story
    hidden list."""
    from chim.cut import source_ref
    path, start, end = task
    frames, frame, key, sub, numbers, piece = [], None, None, None, None, {}
    for line in _lines(path, start, end):
        if line == '  {':
            frame = {'cell': None, 'town': None, 'selected': set(), 'owned': {}, 'hidden': set()}
            frames.append(frame)
            key = None
            continue
        if frame is None:
            continue
        m = re.match(r'^   "(\w+)": ?(.*)$', line)
        if m:
            key, rest = m.group(1), m.group(2)
            if key == 'cell':
                numbers = []
            elif key == 'town':
                frame['town'] = json.loads(rest.rstrip(','))
            continue
        if key == 'cell' and numbers is not None:
            v = line.strip().rstrip(',')
            if v == ']' or v == '],':
                frame['cell'] = tuple(int(n) for n in numbers)
                numbers = None
            elif v:
                numbers.append(v)
        elif key == 'placements':
            m = re.match(r'^     "ref": (\d+)', line)
            if m:
                frame['selected'].add(source_ref(int(m.group(1))))
        elif key == 'frame_ownership':
            if re.match(r'^      "origin": \[', line):
                sub, piece = 'origin', {'origin': []}
            elif sub == 'origin' and re.match(r'^       [-\d]', line):
                piece['origin'].append(float(line.strip().rstrip(',')))
            elif re.match(r'^      "ref": (\d+)', line):
                ref = source_ref(int(re.match(r'^      "ref": (\d+)', line).group(1)))
                sub = None
                frame['owned'].setdefault(ref, piece if piece.get('origin') else {'origin': []})
                piece = {'ref': ref}
            elif re.match(r'^      "story_hidden": true', line) and piece.get('ref') is not None:
                frame['owned'][piece['ref']]['story_hidden'] = True
            elif re.match(r'^      "\w+"', line):
                sub = None
        elif key == 'story_hidden':
            v = line.strip().rstrip(',')
            if v.isdigit():
                frame['hidden'].add(int(v))
    return frames


def source_frames(path, jobs=None):
    """[{'cell', 'town', 'selected', 'owned', 'hidden'}] of every frame of a CHIM source manifest (chim-source.json),
    in its order, read on every core: the file is cut at frame boundaries and each range is read by one worker
    (BUILD-IMAGE-UNDERUSED-32: the manifest is 600+ MB)."""
    from build_jobs import resolve_jobs
    from build_parallel import in_order_map
    jobs = resolve_jobs(jobs)
    with open(path, 'rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
        opening = data.find(b'\n "frames": [\n')
        if opening < 0:
            raise ValueError('%s: no frames list where parallel_json.dumps writes it' % path)
        closing = data.find(b'\n ]', opening + 1)
        starts, at = [], opening
        while True:
            at = data.find(b'\n  {\n', at + 1, closing)
            if at < 0:
                break
            starts.append(at + 1)
    if not starts:
        return []
    per = max(1, -(-len(starts) // (jobs * 4)))
    bounds = starts[::per] + [closing + 1]
    tasks = [(str(path), bounds[k], bounds[k + 1]) for k in range(len(bounds) - 1)]
    return [f for part in in_order_map(_source_unit, tasks, min(jobs, len(tasks))) for f in part]


def holder_frame(frames, holder_kind, holder_area, cell, region_ids=None):
    """The CHIM source frame that holds a door: the town's frame for a town holder, else the region frame of CELL
    (region_ids: {(x, y): frame id} of chim-regions.json; a region frame's "town" field is its frame id)."""
    wanted = (region_ids or {}).get(tuple(cell))
    for f in frames:
        if holder_kind == 'town' and f['town'] == holder_area:
            return f
        if holder_kind == 'region' and f['cell'] == tuple(cell) and f['town'] in (None, wanted):
            return f
    return None


# ------------------------------------------------------------------ the audit

def room_record_bounds(data):
    """(mins, maxs) of a CHIM room record (.crm: the CHIM header, then the room block's bounds, chim.interior
    ROOM_BLOCK). Read without the format version check: an audit reads images of earlier world formats too, and the
    room block has kept its place since the first room record."""
    from chim import format as F
    from chim.interior import ROOM_BLOCK, ROOM_KIND
    if len(data) < F.HEADER.size + ROOM_BLOCK.size:
        raise ValueError('room record shorter than its header')
    magic, kind = F.HEADER.unpack_from(data)[:2]
    if magic != F.MAGIC or kind != ROOM_KIND:
        raise ValueError('not a CHIM room record')
    v = ROOM_BLOCK.unpack_from(data, F.HEADER.size)
    return tuple(v[0:3]), tuple(v[3:6])


class Image:
    """The built image as the audit reads it; tests give their own object with the same methods."""

    def __init__(self, id1, engine_src, world_dir, jobs=None, store_roots=()):
        from chim.frame_map import world_directory
        self.id1 = Path(id1)
        self.store_roots = [Path(p) for p in store_roots]
        self.maps = self.id1 / 'maps'
        src = Path(engine_src)
        self.names = engine_map_names((src / 'aw_maps.h').read_text(encoding='utf-8', errors='replace'),
                                      (src / 'aw_town_table.h').read_text(encoding='utf-8', errors='replace'))
        cfg = self.id1 / 'default-game.cfg'
        self.crossing = crossing_mode(cfg.read_text(encoding='cp1252', errors='replace')) if cfg.is_file() else 0
        self.directory = world_directory(self.id1) if (self.id1 / 'world/regions.awr').is_file() else []
        self.frames = source_frames(Path(world_dir) / 'chim-source.json', jobs) if world_dir else []
        table = Path(world_dir) / 'chim-regions.json' if world_dir else None
        doc = json.loads(table.read_text(encoding='utf-8')) if table and table.is_file() else {}
        self.leave_margin = doc.get('leave_margin', 0)
        self.region_ids = {tuple(f['cell']): f['id'] for f in doc.get('frames') or []}
        self._banks, self._rooms = {}, {}

    def bank(self, name):
        """(file name, parse_bank) of the bank the engine reads for map NAME, or (None, None) without one."""
        if name not in self._banks:
            found = (None, None)
            for file in ('doors-%s.txt' % name, 'scene-doors-%s.txt' % name):
                path = self.id1 / file
                if path.is_file():
                    found = (file, parse_bank(path.read_text(encoding='cp1252'), self.names))
                    break
            self._banks[name] = found
        return self._banks[name]

    def map_runs(self, name):
        """The engine knows map NAME and the image holds its file (a CHIM frame .cut, a town's -chim map, a room)."""
        from map_files import map_file, town_map_present
        return map_valid(name, self.names) and (town_map_present(self.maps, name) or (self.maps / (name + '.cut'))
                                                .is_file() or map_file(self.maps, name).is_file())

    def room_bounds(self, name):
        """The room record's bounds (map units) of CHIM room map NAME, or None for another map: its record
        <store>/rooms/<room>.crm from id1, else from the extra store roots (a build's chim-interiors stage: the image
        step packs the store from there)."""
        if name not in self._rooms:
            from map_files import map_file, room_record
            found, bounds = room_record(map_file(self.maps, name)) if map_file(self.maps, name).is_file() else None, None
            for root in [self.id1] + list(self.store_roots) if found else []:
                path = Path(root) / found[0] / 'rooms' / (found[1] + '.crm')
                if path.is_file():
                    bounds = room_record_bounds(path.read_bytes())
                    break
            self._rooms[name] = bounds
        return self._rooms[name]


def regions_by_cell(data_files, jobs=None):
    """{(x, y): region id} of every exterior cell of the present masters (tools/door_graph.py parse and merge)."""
    import door_graph
    parsed = door_graph.parse_masters(data_files, jobs=jobs, warn=lambda *a: None)
    exteriors = door_graph.merge(parsed)[4]
    return {key: c.get('region') or '' for key, c in exteriors.items()}


def _frame_transforms(world_rows, directory):
    """{map: (kind, transform)} to turn a map's local point back into Morrowind units: a region frame by its directory
    origin, a town by its centre (world_doors.local_point)."""
    out = {name: ('region', list(origin)) for name, origin, _ in directory}
    for row in world_rows:
        if row.get('holder') == 'town' and row.get('source') and row.get('frame'):
            out.setdefault(row['source'], ('town', row['frame']))
    return out


def to_global(point, transform):
    kind, frame = transform
    if kind == 'town':
        return [point[0] / SCALE + frame[0], point[1] / SCALE + frame[1], point[2] / SCALE]
    return [(point[k] + frame[k]) / SCALE for k in range(3)]


def check_door(door, world_row, image, exits, world_rows, transforms, region=''):
    """One checklist row for exterior door DOOR (mwad.interior.original_doors) with its world door table row
    WORLD_ROW (or None); EXITS: the original doors out of its destination room into the exterior; WORLD_ROWS: the
    table by reference. Every check says 'yes', 'no' or 'not checked', and 'problems' lists why for every 'no'."""
    level, key = lock_of(door)
    row = {'reference': door['number'], 'id': door['id'], 'model': door.get('model', ''),
           'cell': list(door['source_grid']), 'position': [round(v, 1) for v in door['position']],
           'region': region, 'destination_cell': door['destination_cell'], 'lock_level': level, 'key': key,
           'locked': 'yes' if level > 0 or key else 'no'}
    problems = []
    checks = dict.fromkeys(('holder', 'placed', 'bank_row', 'use_box', 'engine_frame', 'target_room', 'arrival_inside',
                            'way_back'), 'not checked')
    row['checks'] = checks
    row['problems'] = problems
    row['walk_in'] = 'no'
    row['usable_on_arrival'] = 'no'
    if world_row is None or 'source' not in world_row:
        checks['holder'] = 'no'
        problems.append('no frame or town of the image holds the door (world-doors.json: %s)'
                        % ((world_row or {}).get('problem') or 'no row'))
        return row
    holder, kind = world_row['source'], world_row['holder']
    row.update(holder=holder, holder_kind=kind)
    checks['holder'] = 'yes' if image.map_runs(holder) else 'no'
    if checks['holder'] == 'no':
        problems.append('its frame map %s does not run (unknown to the engine or not in the image)' % holder)
    frame_origin = world_row.get('frame')
    local = None
    if kind == 'region' and frame_origin is not None:
        local = [door['position'][k] * SCALE - frame_origin[k] for k in range(3)]
    elif kind == 'town' and frame_origin is not None:
        local = [(door['position'][0] - frame_origin[0]) * SCALE, (door['position'][1] - frame_origin[1]) * SCALE,
                 door['position'][2] * SCALE]
    # the CHIM frame that holds it places the door (the model the player should see)
    frame = holder_frame(image.frames, kind, holder if kind == 'town' else None, door['source_grid'],
                         getattr(image, 'region_ids', None)) if image.frames else None
    row['area'] = None if frame is None else (frame['town'] or 'cell %d,%d' % frame['cell'])
    placed_origin = None
    if image.frames:
        if frame is None:
            checks['placed'] = 'no'
            problems.append('no CHIM source frame for its holder')
        elif door['number'] in frame['hidden'] or frame['owned'].get(door['number'], {}).get('story_hidden'):
            # disabled in the original until a script enables it: hidden the same way here, not a fault
            checks['placed'] = 'not checked'
            row['note'] = 'story hidden: not drawn until a script shows it, as in the original'
        elif door['number'] in frame['owned'] or door['number'] in frame['selected']:
            checks['placed'] = 'yes'
            origin = frame['owned'].get(door['number'], {}).get('origin')
            placed_origin = origin if origin and len(origin) == 3 else None
        else:
            checks['placed'] = 'no'
            problems.append('its frame does not place the door model')
    # the holder's bank as the engine keeps it
    file, bank = image.bank(holder)
    link = None
    if bank is None:
        checks['bank_row'] = 'no'
        problems.append('no door bank doors-%s.txt' % holder)
    else:
        mine = [l for l in bank['links'] if l['reference'] == door['number']]
        own = [l for l in mine if l['source'] == holder]
        dropped = [d for d in bank['dropped'] if d['reference'] == door['number']]
        if own:
            link = own[0]
            checks['bank_row'] = 'yes'
        else:
            checks['bank_row'] = 'no'
            problems.append(('its row in %s is dropped by the engine: %s' % (file, dropped[0]['reason'])) if dropped
                            else ('its row in %s names another source map (the engine compares it with the running '
                                  'map)' % file) if mine else 'no row for it in %s' % file)
    if link is not None:
        row['bank'] = {'file': file, 'line': link['line'], 'box': [link['mins'], link['maxs']],
                       'target': link['target'], 'arrival': link['arrival']}
        point = placed_origin or local
        if point is None:
            checks['use_box'] = 'not checked'
        else:
            # the box is the door mesh's bounds at its place; a mesh may hang well off its pivot (the Ashlander yurt
            # flaps: 45 to 80 units), so the box must lie near the placed origin, not around it
            gap = box_gap(link['mins'], link['maxs'], point)
            row['use_box_gap'] = round(gap, 2)
            moved = math.dist(placed_origin, local) if placed_origin and local else 0.0
            row['placed_offset'] = round(moved, 2)
            checks['use_box'] = 'yes' if gap <= BOX_REACH and moved <= BOX_TOLERANCE else 'no'
            if gap > BOX_REACH:
                problems.append('its use box is %.0f map units from the %s door' %
                                (gap, 'placed' if placed_origin else 'original'))
            if moved > BOX_TOLERANCE:
                problems.append('its frame places the door %.0f map units from its original place (the box is at the '
                                'original)' % moved)
    # the frame the engine runs at the door's place (the first directory row whose core holds it)
    if kind == 'region' and image.directory:
        at = directory_frame(image.directory, [v * SCALE for v in door['position']])
        row['engine_frame'] = at[0] if at else None
        checks['engine_frame'] = 'yes' if at and at[0] == holder else 'no'
        if checks['engine_frame'] == 'no':
            problems.append('the engine runs %s at the door, its bank is %s' % (at[0] if at else 'no frame', holder))
        if at and local is not None and link is not None:
            margin = 1024 + image.leave_margin
            edge = min(margin - abs(link['mins'][0]), margin - abs(link['maxs'][0]),
                       margin - abs(link['mins'][1]), margin - abs(link['maxs'][1]))
            row['frame_edge'] = round(edge, 1)
            if edge < REACH:
                row['near_frame_edge'] = True
    elif kind == 'town':
        checks['engine_frame'] = 'yes'
    # the room it leads into
    target = link['target'] if link else world_row.get('target')
    row['target'] = target
    if target is None or target == '-':
        checks['target_room'] = 'no'
        problems.append('it leads nowhere ("-": interior unavailable)' if target == '-'
                        else 'no room of the image for %s' % door['destination_cell'])
    elif target in OPENING_MAPS:
        # the opening scene's own doors (world_doors.OPENING_MAPS: aw_opening.c, aw_intro.c hold them): the story
        # decides when they open; its maps are not region frames or rooms, so this audit leaves them to the opening
        checks['target_room'] = checks['arrival_inside'] = checks['way_back'] = 'not checked'
        row['note'] = 'the opening scene\'s door (into %s)' % target
    elif not image.map_runs(target):
        checks['target_room'] = 'no'
        problems.append('its room map %s does not run' % target)
    else:
        checks['target_room'] = 'yes'
        if world_row.get('target') and world_row['target'] != target:
            problems.append('its bank row leads to %s, the door table to %s' % (target, world_row['target']))
            checks['target_room'] = 'no'
        bounds = image.room_bounds(target)
        arrival = link['arrival'] if link else world_row.get('arrival')
        if bounds is None or arrival is None:
            checks['arrival_inside'] = 'not checked'
        else:
            gap = box_gap(bounds[0], bounds[1], arrival)
            checks['arrival_inside'] = 'yes' if gap <= ROOM_TOLERANCE else 'no'
            if checks['arrival_inside'] == 'no':
                problems.append('its arrival is %.0f map units outside the room' % gap)
    # the way back out: the room's exit nearest this door, its row in the room's bank
    near = sorted(((math.dist(e['destination']['position'][:2], door['position'][:2]), e) for e in exits),
                  key=lambda t: t[0])
    near = [t for t in near if t[0] <= EXIT_SEARCH]
    if target in OPENING_MAPS:
        pass
    elif not near:
        checks['way_back'] = 'no'
        problems.append('no exit of %s leads back near this door' % door['destination_cell'])
    elif checks['target_room'] == 'yes':
        exit_door = near[0][1]
        row['exit_reference'] = exit_door['number']
        _, room_bank = image.bank(target)
        back = [l for l in (room_bank or {}).get('links', []) if l['reference'] == exit_door['number']
                and l['source'] == target]
        expected = (world_rows.get(exit_door['number']) or {}).get('target')
        if not back:
            checks['way_back'] = 'no'
            problems.append('the room %s has no engine-valid row for its exit %d' % (target, exit_door['number']))
        elif back[0]['target'] == '-' or not image.map_runs(back[0]['target']):
            checks['way_back'] = 'no'
            problems.append('the way out %d leads to %s, which does not run' % (exit_door['number'], back[0]['target']))
        else:
            transform = transforms.get(back[0]['target'])
            out = to_global(back[0]['arrival'], transform) if transform else None
            row['way_back'] = {'target': back[0]['target'], 'expected': expected}
            if out is None:
                checks['way_back'] = 'not checked'
            else:
                distance = math.dist(out[:2], door['position'][:2])
                row['way_back']['distance'] = round(distance, 1)
                checks['way_back'] = 'yes' if distance <= BACK_DISTANCE else 'no'
                if checks['way_back'] == 'no':
                    problems.append('the way out arrives %.0f units from this door (%s)' % (distance,
                                                                                          back[0]['target']))
            if expected and back[0]['target'] != expected:
                problems.append('the way out leads to %s, the door table says %s' % (back[0]['target'], expected))
    paper = all(checks[k] in ('yes', 'not checked') for k in checks) and not problems
    row['usable_on_arrival'] = 'yes' if paper else 'no'
    if paper:
        row['walk_in'] = LEVEL_CHANGE_ONLY if kind == 'region' and image.crossing == 1 else WALK_IN
    return row


def summarize(rows):
    """Per region: doors, each check's yes count, usable on arrival, usable after walking in, locked."""
    out = {}
    for row in rows:
        entry = out.setdefault(row['region'] or '(no region)', {'doors': 0, 'usable_on_arrival': 0, 'walk_in': 0,
                                                                'locked': 0, 'checks': {}})
        entry['doors'] += 1
        entry['usable_on_arrival'] += row['usable_on_arrival'] == 'yes'
        entry['walk_in'] += row['walk_in'] == WALK_IN
        entry['locked'] += row['locked'] == 'yes'
        for k, v in row['checks'].items():
            entry['checks'][k] = entry['checks'].get(k, 0) + (v == 'yes')
    return dict(sorted(out.items()))


def explain_spot(spot, doors, rows_by_ref, image):
    """Why a player at SPOT (global Morrowind xyz + running-map local xyz, the engine's position line) could not use
    the nearest exterior load door: the running map, the door's own frame, whether the running map's bank (the only
    one the engine reads) has the door, and the door's box in the running map's coordinates against the player."""
    g, l = spot[:3], spot[3:6]
    door = min((d for d in doors if not d['source_interior'] and d['destination_interior']),
               key=lambda d: math.dist(d['position'][:2], g[:2]))
    out = {'spot': list(spot), 'reference': door['number'], 'id': door['id'], 'destination_cell': door['destination_cell'],
           'door_distance': round(math.dist(door['position'][:2], g[:2]), 1)}
    origin = running_origin(g, l)
    running = next((name for name, o, _ in image.directory if abs(o[0] - origin[0]) < 2 and abs(o[1] - origin[1]) < 2),
                   None)
    out['running_map'] = running
    out['running_origin'] = [round(v, 1) for v in origin]
    out['running_cell'] = [int(math.floor(origin[0] / CELL_MAP)), int(math.floor(origin[1] / CELL_MAP))]
    row = rows_by_ref.get(door['number'])
    if row:
        out['holder'] = row.get('holder')
        out['door_row'] = {k: row.get(k) for k in ('checks', 'problems', 'usable_on_arrival', 'walk_in')}
    reasons = []
    if running is None:
        reasons.append('the running map is not a region frame of the directory')
    elif row and row.get('holder') != running:
        file, bank = image.bank(running)
        has = bank is not None and any(x['reference'] == door['number'] for x in bank['links'])
        out['running_bank'] = {'file': file, 'rows': len(bank['links']) if bank else 0, 'has_door': has}
        reasons.append('the player stood in a streamed frame: the running map is %s (cell %d,%d), the door belongs '
                       'to %s; the engine reads only doors-%s.txt (aw_scene.c read_links(): sv.name), which %s'
                       % (running, out['running_cell'][0], out['running_cell'][1], row.get('holder'), running,
                          'has it' if has else ('has no row for door %d' % door['number'] if bank else 'does not exist')))
        if row.get('bank') and row.get('holder') in dict((n, o) for n, o, _ in image.directory):
            home = dict((n, o) for n, o, _ in image.directory)
            shift = [home[row['holder']][k] - origin[k] for k in range(2)] + [0.0]
            mins = [row['bank']['box'][0][k] + shift[k] for k in range(3)]
            maxs = [row['bank']['box'][1][k] + shift[k] for k in range(3)]
            out['door_box_in_running_map'] = [[round(v, 1) for v in mins], [round(v, 1) for v in maxs]]
            out['player_to_box'] = round(box_gap(mins, maxs, l), 1)
    if row and row.get('problems'):
        reasons.extend(row['problems'])
    out['reasons'] = reasons
    return out


def audit(doors, world_rows, image, regions=None, spots=()):
    """The audit report: one row per exterior-to-room load door of DOORS (mwad.interior.original_doors), the region
    summary, the problems and the explained SPOTS."""
    regions = regions or {}
    by_ref = {r['reference']: r for r in world_rows}
    transforms = _frame_transforms(world_rows, image.directory)
    exits = {}
    for d in doors:
        if d['source_interior'] and not d['destination_interior']:
            exits.setdefault(d['source_cell'].casefold(), []).append(d)
    rows = []
    for d in sorted(doors, key=lambda d: d['number']):
        if d['source_interior'] or not d['destination_interior'] or d['id'].casefold() in MARKER_IDS:
            continue
        rows.append(check_door(d, by_ref.get(d['number']), image, exits.get(d['destination_cell'].casefold(), []),
                               by_ref, transforms, regions.get(tuple(d['source_grid']), '')))
    rows_by_ref = {r['reference']: r for r in rows}
    problems = [{'reference': r['reference'], 'id': r['id'], 'cell': r['cell'], 'destination_cell': r['destination_cell'],
                 'problems': r['problems']} for r in rows if r['problems']]
    counts = {'doors': len(rows), 'usable_on_arrival': sum(r['usable_on_arrival'] == 'yes' for r in rows),
              'walk_in': sum(r['walk_in'] == WALK_IN for r in rows),
              'level_change_only': sum(r['walk_in'] == LEVEL_CHANGE_ONLY for r in rows),
              'locked': sum(r['locked'] == 'yes' for r in rows),
              'near_frame_edge': sum(bool(r.get('near_frame_edge')) for r in rows),
              'with_problems': len(problems)}
    for key in ('holder', 'placed', 'bank_row', 'use_box', 'engine_frame', 'target_room', 'arrival_inside', 'way_back'):
        counts['check ' + key] = {v: sum(r['checks'][key] == v for r in rows) for v in ('yes', 'no', 'not checked')}
    return {'format': FORMAT, 'crossing': image.crossing, 'counts': counts, 'regions': summarize(rows),
            'problems': problems, 'spots': [explain_spot(s, doors, rows_by_ref, image) for s in spots], 'rows': rows}


CSV_FIELDS = ('reference', 'id', 'model', 'cell', 'position', 'region', 'destination_cell', 'locked', 'lock_level',
              'key', 'holder', 'holder_kind', 'holder_runs', 'placed', 'bank_row', 'use_box', 'engine_frame', 'target', 'target_room',
              'arrival_inside', 'way_back', 'usable_on_arrival', 'walk_in', 'use_box_gap', 'note', 'problems')


def write_outputs(report, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'door-audit.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8',
                                         newline='\n')
    with open(out / 'door-checklist.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(CSV_FIELDS)
        for r in report['rows']:
            values = dict(r, **r['checks'])
            values['holder'], values['holder_runs'] = r.get('holder', ''), r['checks']['holder']
            values['cell'] = '%d,%d' % tuple(r['cell'])
            values['position'] = ' '.join('%.0f' % v for v in r['position'])
            values['problems'] = '; '.join(r['problems'])
            w.writerow([values.get(k, '') for k in CSV_FIELDS])
    c = report['counts']
    lines = ['# Door entrance audit', '',
             'Exterior load doors into interiors: %d. Usable when the player arrives in their frame by a level change: '
             '%d. Usable after walking in from another frame: %d (cell crossings type %d). Locked in the original: %d. '
             'With a problem: %d.' % (c['doors'], c['usable_on_arrival'], c['walk_in'], report['crossing'],
                                      c['locked'], c['with_problems']), '',
             '| Check | yes | no | not checked |', '| --- | --- | --- | --- |']
    for key in ('holder', 'placed', 'bank_row', 'use_box', 'engine_frame', 'target_room', 'arrival_inside', 'way_back'):
        v = c['check ' + key]
        lines.append('| %s | %d | %d | %d |' % (key, v['yes'], v['no'], v['not checked']))
    lines += ['', '## Per region', '', '| Region | doors | usable on arrival | usable walking in | locked |',
              '| --- | --- | --- | --- | --- |']
    for name, e in report['regions'].items():
        lines.append('| %s | %d | %d | %d | %d |' % (name, e['doors'], e['usable_on_arrival'], e['walk_in'], e['locked']))
    if report['spots']:
        lines += ['', '## Explained places', '']
        for s in report['spots']:
            reach = (' The player was %.0f map units from its use box in the running map\'s coordinates (reach %d).'
                     % (s['player_to_box'], REACH)) if 'player_to_box' in s else ''
            lines.append('- %s: door %d (%s) into %s, %.0f units away: %s.%s' % (
                ' '.join('%g' % v for v in s['spot'][:3]), s['reference'], s['id'], s['destination_cell'],
                s['door_distance'], '; '.join(s['reasons']) or 'no problem found', reach))
    lines += ['', '## Problems', '']
    if not report['problems']:
        lines.append('None found by the checks above.')
    for p in report['problems']:
        lines.append('- %d %s (cell %d,%d) -> %s: %s' % (p['reference'], p['id'], p['cell'][0], p['cell'][1],
                                                         p['destination_cell'], '; '.join(p['problems'])))
    (out / 'door-audit.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--data-files', required=True, type=Path)
    parser.add_argument('--build', type=Path)
    parser.add_argument('--id1', type=Path)
    parser.add_argument('--world-doors', type=Path)
    parser.add_argument('--chim-world', type=Path)
    parser.add_argument('--engine-src', type=Path)
    parser.add_argument('--room-store', type=Path, action='append', default=[],
                        help='a folder holding <store>/rooms/*.crm beside id1 (default: BUILD/chim-interiors)')
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--spot', nargs=6, type=float, action='append', default=[],
                        metavar=('GX', 'GY', 'GZ', 'LX', 'LY', 'LZ'))
    parser.add_argument('--jobs', type=int)
    args = parser.parse_args(argv)
    b = args.build
    id1 = args.id1 or (b / 'image/boot/id1')
    world_doors_path = args.world_doors or (b / 'image/world-doors.json')
    chim_world = args.chim_world or (b / 'chim-world' if b else None)
    engine_src = args.engine_src or (b / 'engine/runtime/src' if b and (b / 'engine/runtime/src/aw_maps.h').is_file()
                                     else ROOT / 'engine/aga/src')
    from mwad.interior import original_doors
    from mwad.paths import child_ci
    doors = original_doors(child_ci(args.data_files, 'Morrowind.esm').read_bytes())
    world_rows = json.loads(Path(world_doors_path).read_text(encoding='utf-8'))['rows']
    stores = args.room_store or ([b / 'chim-interiors'] if b and (b / 'chim-interiors').is_dir() else [])
    image = Image(id1, engine_src, chim_world, args.jobs, stores)
    report = audit(doors, world_rows, image, regions_by_cell(args.data_files, args.jobs), args.spot)
    write_outputs(report, args.out)
    c = report['counts']
    print('door audit: %d exterior entrances; usable on arrival %d, walking in %d, only after a level change %d; '
          'locked %d; with problems %d' % (c['doors'], c['usable_on_arrival'], c['walk_in'], c['level_change_only'],
                                           c['locked'], c['with_problems']))
    for s in report['spots']:
        print('  spot %s: door %d -> %s: %s' % (' '.join('%g' % v for v in s['spot'][:3]), s['reference'],
                                                s['destination_cell'], '; '.join(s['reasons'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
