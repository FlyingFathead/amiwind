# SPDX-License-Identifier: GPL-3.0-only
"""Start straight in the game: --direct-to-game-map START and --quick-character.

A quick test build that boots straight into an area with a ready-made
character: no intro movie, no ship, no character creation. It uses the one
quick-start mechanism the MiniWind playtest build uses (id1/miniwind.txt, read
by engine/aga/src/aw_miniwind.c; aw_scene.c aw_quick_start): this module adds
the start point and the character to that file. A normal build without these
options still starts with the full intro.

START has four forms (parse):

  AREA                  a town the build holds (balmora, seyda_neen, vivec_arena):
                        its arrival point
  interior:<cell id>    an interior the build holds, e.g. "interior:Balmora, Council Club":
                        the arrival point of a door into it
  cell:X,Y              an exterior cell (grid numbers): its centre, dropped to the ground
  pos:X,Y,Z[@HEADING]   a spot in the global coordinates the debug HUD shows
                        (GLOBAL XYZ), so a spot can be copied from a screenshot;
                        HEADING in degrees (0 = north, 90 = east)

Checks: check() before any stage runs (syntax, the area/interior/cell is in
the build); resolve() at image time against the final payload (the door
arrival of an interior; for cell and pos the region map that owns the point
and the engine's arrival search on its collision: a spot in water or a wall
moves to the nearest standing spot, or the build stops with the reason).

--quick-character RACE,CLASS[,NAME]: the character (default: the Hors preset,
Nord Barbarian born under The Steed, as the debug teleport creates). RACE and
CLASS are checked against the playable races and classes of the masters.

Development versions only: release candidates and finals refuse both options.
"""
import json
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
OPTION = '--direct-to-game-map'
CHARACTER_OPTION = '--quick-character'
CELL_UNITS = 8192          # one Morrowind exterior cell in global units
LOCAL_SCALE = 0.25         # global units -> map units (the converter's scale)
LIMIT = 2000000            # the engine's bound on a global coordinate (aw_world.c)
AREA_ALIASES = {'seyda_neen': 'seyda', 'seydaneen': 'seyda', 'vivec': 'vivec_arena', 'arena': 'vivec_arena'}
# The engine's buffers (aw_miniwind.h): one byte for the terminator.
START_CHARS, CHARACTER_CHARS = 95, 127
DEFAULT_CHARACTER = {'race': 'Nord', 'class': 'Barbarian', 'birth': 'Charioteer', 'female': False, 'name': 'Hors'}
NAME_CHARS = 31
NO_INTERIORS_NOTE = ('towns imported from config/towns.json (the Vivec Arena) have no converted interiors yet '
                     '(IMPORT-TOWN-NO-INTERIORS-32)')


class Start:
    """A parsed start point."""

    def __init__(self, kind, text, **fields):
        self.kind, self.text = kind, text
        self.__dict__.update(fields)

    def describe(self):
        """Words for the startup screen and the receipts: 'Balmora', 'Vivec, Arena Pit',
        'cell -3,-2', 'position -20480 -12288 1200'."""
        if self.kind == 'area':
            return self.title
        if self.kind == 'interior':
            return self.cell
        if self.kind == 'cell':
            return 'cell %d,%d' % (self.x, self.y)
        return 'position %s %s %s' % tuple(_number(v) for v in (self.x, self.y, self.z))

    def record(self):
        row = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        row['describe'] = self.describe()
        return row


def _number(value):
    return ('%.3f' % value).rstrip('0').rstrip('.')


def towns_table(root=ROOT):
    return json.loads((Path(root) / 'config/towns.json').read_text(encoding='utf-8'))['towns']


def town_title(town, root=ROOT):
    row = next(t for t in towns_table(root) if t['id'] == town)
    if 'town' in row:
        return row['town']['title']
    config = json.loads((Path(root) / 'config' / row['config']).read_text(encoding='utf-8'))
    return config.get('town', {}).get('title') or town.replace('_', ' ').title()


def parse(text, root=ROOT):
    """START -> Start; ValueError with the reason for anything else."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError(OPTION + ' needs a start point: an area (balmora), interior:<cell id>, cell:X,Y or '
                         'pos:X,Y,Z[@HEADING]')
    text = text.strip()
    if any(not (' ' <= c <= '~') for c in text):
        raise ValueError(OPTION + ': printable ASCII only: %r' % text)
    kind, colon, value = text.partition(':')
    kind = kind.strip().casefold()
    if not colon:
        name = AREA_ALIASES.get(text.casefold(), text.casefold())
        if name not in {t['id'] for t in towns_table(root)}:
            raise ValueError('%s %s: unknown area; areas: %s (or interior:<cell id>, cell:X,Y, pos:X,Y,Z)'
                             % (OPTION, text, ', '.join(['balmora', 'seyda_neen', 'vivec_arena'])))
        return Start('area', text, town=name, title=town_title(name, root))
    value = value.strip()
    if kind == 'interior':
        if not value or len(value) > 63:
            raise ValueError(OPTION + ' interior:<cell id> needs the cell ID (1-63 characters), e.g. '
                             '"interior:Balmora, Council Club"')
        return Start('interior', text, cell=value)
    if kind == 'cell':
        match = re.fullmatch(r'\s*(-?\d{1,3})\s*,\s*(-?\d{1,3})\s*', value)
        if not match:
            raise ValueError(OPTION + ' cell:X,Y needs two whole grid numbers, e.g. cell:-3,-2')
        x, y = int(match.group(1)), int(match.group(2))
        return Start('cell', text, x=x, y=y, gx=x * CELL_UNITS + CELL_UNITS / 2, gy=y * CELL_UNITS + CELL_UNITS / 2,
                     heading=0.0)
    if kind == 'pos':
        number = r'\s*(-?\d+(?:\.\d+)?)\s*'
        match = re.fullmatch(number + ',' + number + ',' + number + r'(?:@' + number + r')?', value)
        if not match:
            raise ValueError(OPTION + ' pos:X,Y,Z[@HEADING] needs three numbers (the debug HUD\'s GLOBAL XYZ) and '
                             'an optional heading in degrees, e.g. pos:-20480,-12288,1200@90')
        x, y, z = (float(match.group(i)) for i in (1, 2, 3))
        heading = float(match.group(4)) if match.group(4) is not None else 0.0
        if any(abs(v) > LIMIT for v in (x, y, z)):
            raise ValueError(OPTION + ' pos: coordinates beyond +-%d are outside the world' % LIMIT)
        if not 0 <= heading < 360:
            raise ValueError(OPTION + ' pos: HEADING is 0 to 359.999 degrees')
        return Start('pos', text, x=x, y=y, z=z, gx=x, gy=y, heading=heading)
    raise ValueError('%s %s: unknown form "%s:"; use an area, interior:<cell id>, cell:X,Y or pos:X,Y,Z[@HEADING]'
                     % (OPTION, text, kind))


# ------------------------------------------------------------------ what a build holds

def scene_rows(root=ROOT):
    rows = []
    for name in ('seyda_area.json', 'balmora_interiors.json'):
        path = Path(root) / 'config' / name
        if path.is_file():
            rows += json.loads(path.read_text(encoding='utf-8')).get('scenes', [])
    return rows


def town_grid(town, root=ROOT):
    """The exterior cells a town area converts (its config's source_cell +- source_radius)."""
    row = next(t for t in towns_table(root) if t['id'] == town)
    config = json.loads((Path(root) / 'config' / row['config']).read_text(encoding='utf-8'))
    if 'source_cell' not in config:
        return set()
    cx, cy = config['source_cell']
    r = config.get('source_radius', 0)
    return {(x, y) for x in range(cx - r, cx + r + 1) for y in range(cy - r, cy + r + 1)}


def build_scope(towns, world, interiors_excluded=False, miniwind_scope=None, root=ROOT):
    """What a build holds: {'towns': [...], 'interiors': {cell casefold: (map, town)}, 'world': bool,
    'cells': {(x, y): town} for the town grids}. towns: the town IDs it converts; world: the open
    world is built (a full build); miniwind_scope: the MiniWind scope ('full', 'exterior') or None."""
    interiors = {}
    for scene in scene_rows(root):
        if scene.get('interior') is not True or not scene.get('cell'):
            continue
        area = scene.get('area', 'seyda')
        opening = scene['map'] in ('prison', 'census')
        if miniwind_scope:
            from miniwind import START_MAPS
            # MiniWind holds Balmora's rooms (full scope) and, as a direct start only, the prison
            # ship the intro stage builds anyway (tools/miniwind.py START_MAPS); never the Census office.
            if scene['map'] in START_MAPS:
                interiors[scene['cell'].casefold()] = (scene['map'], area)
                continue
            if opening or area not in towns or miniwind_scope == 'exterior':
                continue
        elif area not in towns or (interiors_excluded and not opening):
            continue
        interiors[scene['cell'].casefold()] = (scene['map'], area)
    cells = {}
    for town in towns:
        for cell in town_grid(town, root):
            cells.setdefault(cell, town)
    return {'towns': list(towns), 'interiors': interiors, 'world': bool(world), 'cells': cells}


def check(start, scope):
    """The start point against what the build holds (before any stage runs); returns the start."""
    if start.kind == 'area':
        if start.town not in scope['towns']:
            raise ValueError('%s %s: %s is not in this build (it holds %s)'
                             % (OPTION, start.text, start.title, ', '.join(scope['towns']) or 'no town'))
        return start
    if start.kind == 'interior':
        row = scope['interiors'].get(start.cell.casefold())
        if row is None:
            held = sorted(scope['interiors'])
            raise ValueError('%s "%s": the interior "%s" is not in this build. %s. This build holds %d interiors%s'
                             % (OPTION, start.text, start.cell, NO_INTERIORS_NOTE[0].upper() + NO_INTERIORS_NOTE[1:],
                                len(held), '' if not held else ' (the converted Seyda Neen and Balmora rooms; '
                                'their cell IDs are in config/seyda_area.json and config/balmora_interiors.json)'))
        start.map, start.town = row
        return start
    cell = (int(start.gx // CELL_UNITS), int(start.gy // CELL_UNITS))
    if not scope['world'] and cell not in scope['cells']:
        raise ValueError('%s %s: cell %d,%d is outside the area this build holds (cells %s)'
                         % (OPTION, start.text, cell[0], cell[1],
                            ', '.join('%d,%d' % c for c in sorted(scope['cells'])) or 'none'))
    start.cell_xy = list(cell)
    return start


def check_cell_exists(start, data_files):
    """cell:X,Y must be an exterior cell of the masters."""
    if start.kind != 'cell':
        return start
    from content_closure import Master
    master = Master.load(data_files)
    if ('exterior', start.x, start.y) not in master.cells:
        raise ValueError('%s %s: the masters have no exterior cell %d,%d' % (OPTION, start.text, start.x, start.y))
    return start


# ------------------------------------------------------------------ the character

def _playable(data_files):
    """({race id casefold: id}, {class id casefold: id}) of the playable races and classes."""
    from mwad.audit import records, subrecords
    races, classes = {}, {}
    for name in ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm'):
        path = next((p for p in Path(data_files).iterdir() if p.name.casefold() == name.casefold()), None)
        if path is None:
            continue
        for tag, flags, raw in records(path.read_bytes()):
            if tag not in ('RACE', 'CLAS'):
                continue
            fields = dict(subrecords(raw))
            identifier = fields.get('NAME', b'').split(b'\0', 1)[0].decode('cp1252', 'replace')
            data = fields.get('RADT' if tag == 'RACE' else 'CLDT', b'')
            # RADT ends with the flags (playable = 1); CLDT: attributes, specialization, skills, flags.
            playable = len(data) >= 4 and struct.unpack_from('<i', data, len(data) - 4 - (4 if tag == 'CLAS' else 0))[0] & 1
            (races if tag == 'RACE' else classes)[identifier.casefold()] = (identifier, bool(playable))
    return races, classes


def parse_character(text, data_files=None):
    """--quick-character RACE,CLASS[,NAME] -> the character record (DEFAULT_CHARACTER when None)."""
    if text is None:
        return dict(DEFAULT_CHARACTER)
    parts = [p.strip() for p in str(text).split(',')]
    if len(parts) not in (2, 3) or not all(parts):
        raise ValueError(CHARACTER_OPTION + ' takes RACE,CLASS[,NAME], e.g. "Dark Elf,Battlemage,Ilmeni"')
    character = dict(DEFAULT_CHARACTER, race=parts[0].replace('_', ' '), **{'class': parts[1].replace('_', ' ')})
    if len(parts) == 3:
        character['name'] = parts[2]
    for key in ('race', 'class', 'name'):
        value = character[key]
        if len(value) > NAME_CHARS or any(not (' ' <= c <= '~') or c in '|' for c in value):
            raise ValueError('%s: %s must be 1-%d printable characters without "|": %r'
                             % (CHARACTER_OPTION, key, NAME_CHARS, value))
    if data_files is not None:
        races, classes = _playable(data_files)
        for key, table in (('race', races), ('class', classes)):
            row = table.get(character[key].casefold())
            if row is None or not row[1]:
                names = sorted(v[0] for v in table.values() if v[1])
                raise ValueError('%s: %s "%s" is not a playable %s of your game files; choose one of: %s'
                                 % (CHARACTER_OPTION, key, character[key], key, ', '.join(names)))
            character[key] = row[0]
    return character


def character_line(character):
    """The data file's character line value (aw_miniwind.c): RACE|CLASS|BIRTH|m or f|NAME."""
    value = '|'.join([character['race'], character['class'], character['birth'],
                      'f' if character['female'] else 'm', character['name']])
    if len(value) > CHARACTER_CHARS:
        raise ValueError(CHARACTER_OPTION + ': the character line is too long for the engine')
    return value


# ------------------------------------------------------------------ image time

def town_rows(runtime, root=ROOT):
    """Runtime town rows (town_config.runtime_towns) with each town's map origin: map units =
    global x 0.25 - origin (aw_world.c). Seyda Neen and Balmora keep theirs in the world
    directory; here they come from the same sources: Seyda's scene centre and Balmora's config."""
    rows = []
    for town in runtime:
        row = dict(town)
        if row.get('world_slot') in (0, 1):
            if row['name'] == 'seyda':
                from prepare_quake import CENTRE
                row['origin'] = [CENTRE[0] * LOCAL_SCALE, CENTRE[1] * LOCAL_SCALE, 0.0]
            else:
                registry = next(t for t in towns_table(root) if t['id'] == row['id'])
                config = json.loads((Path(root) / 'config' / registry['config']).read_text(encoding='utf-8'))
                scale = config.get('scale', LOCAL_SCALE)
                row['origin'] = [config['centre'][0] * scale, config['centre'][1] * scale, 0.0]
        rows.append(row)
    return rows


def _region_directory(path):
    from arrival_spot import read_directory
    return read_directory(path)


def _world_directory(path):
    """world/regions.awr (AWR2): [(name, origin xyz, core x0 y0 x1 y1)] of the open-world maps."""
    raw = Path(path).read_bytes()
    if raw[:4] != b'AWR2':
        raise ValueError('Invalid world region directory')
    count = struct.unpack_from('<I', raw, 4)[0]
    rows, offset = [], 64
    for index in range(count):
        values = struct.unpack_from('<11f', raw, offset + 8)
        rows.append(('vf%04d' % index, values[0:3], values[3:7]))
        offset += 52
    return rows


def player_start(bsp):
    """(x, y, z, yaw) of a map's info_player_start (its entity lump), or None."""
    raw = Path(bsp).read_bytes() if Path(bsp).is_file() else b''
    if len(raw) < 124:
        return None
    offset, length = struct.unpack_from('<ii', raw, 4)
    if offset < 0 or length < 0 or offset + length > len(raw):
        return None
    text = raw[offset:offset + length].decode('cp1252', errors='replace')
    for body in re.findall(r'\{([^{}]*)\}', text):
        fields = dict(re.findall(r'"([^"]*)"\s+"([^"]*)"', body))
        if fields.get('classname') == 'info_player_start' and 'origin' in fields:
            x, y, z = (float(v) for v in fields['origin'].split())
            return x, y, z, float(fields.get('angle', 0)) % 360.0
    return None


def door_arrival(id1, target):
    """(x, y, z, yaw) of the first door link into map `target` in the payload's door tables."""
    for path in sorted(Path(id1).glob('*doors*.txt')):
        lines = path.read_text(encoding='cp1252', errors='replace').splitlines()
        if not lines or not lines[0].startswith('AWD'):
            continue
        for line in lines[1:]:
            head = line.split('\t', 1)[0].split()
            if len(head) >= 13 and head[1] == target:
                x, y, z, yaw = (float(v) for v in head[9:13])
                return x, y, z, yaw
    return None


def resolve(start, id1, towns, collision_for=None):
    """The engine's start line for this payload (aw_miniwind.c, aw_scene.c aw_quick_start):
    'town NAME' or 'map MAP X Y Z YAW' (map-local units, yaw in degrees), and the record.

    towns: runtime town rows (town_config.runtime_towns: name, regions, origin...). For cell and
    pos the owner region of the point (a town's region core, else an open-world map) and the
    engine's arrival search on its collision (collision_for(map name) -> arrival_spot.Collision-
    like object; default: the region map's BSP) decide the spot."""
    id1 = Path(id1)
    if start.kind == 'area':
        return 'town ' + start.town, {'kind': 'town', 'town': start.town}
    if start.kind == 'interior':
        if not (id1 / 'maps' / (start.map + '.bsp')).is_file():
            raise ValueError('%s "%s": the image has no map for this interior (maps/%s.bsp)'
                             % (OPTION, start.text, start.map))
        arrival, source = door_arrival(id1, start.map), 'door arrival'
        if arrival is None:
            # A room no door leads into (the prison ship): the map's own player start.
            arrival, source = player_start(id1 / 'maps' / (start.map + '.bsp')), "the map's info_player_start"
        if arrival is None:
            raise ValueError('%s "%s": no door leads into %s in this build and its map has no player start, '
                             'so it has no arrival point' % (OPTION, start.text, start.cell))
        x, y, z, yaw = arrival
        return 'map %s %s %s %s %s' % (start.map, *(_number(v) for v in (x, y, z, yaw))), \
            {'kind': 'map', 'map': start.map, 'arrival': [x, y, z], 'yaw': yaw, 'from': source}
    owner, local = None, None
    for town in towns:
        table = id1 / town['regions']
        if not table.is_file():
            continue
        origin = town['origin']
        point = (start.gx * LOCAL_SCALE - origin[0], start.gy * LOCAL_SCALE - origin[1])
        directory = _region_directory(table)
        for row in directory['regions']:
            x0, y0, x1, y1 = row['core']
            if x0 <= point[0] < x1 and y0 <= point[1] < y1:
                owner, local, region = town['name'], point, row['name']
                break
        if owner:
            break
    if owner is None and (id1 / 'world/regions.awr').is_file():
        for name, origin, core in _world_directory(id1 / 'world/regions.awr'):
            point = (start.gx * LOCAL_SCALE - origin[0], start.gy * LOCAL_SCALE - origin[1])
            if core[0] <= point[0] < core[2] and core[1] <= point[1] < core[3]:
                owner, local, region = name, point, name
                break
    if owner is None:
        raise ValueError('%s %s: no map of this build holds global %s %s'
                         % (OPTION, start.text, _number(start.gx), _number(start.gy)))
    from arrival_spot import Collision, standing_spot
    collision = collision_for(region) if collision_for else Collision((id1 / 'maps' / (region + '.bsp')).read_bytes())
    if start.kind == 'pos':
        preferred = (local[0], local[1], start.z * LOCAL_SCALE)
    else:
        top = collision.ground((local[0], local[1], 4096.0), 8192.0) if hasattr(collision, 'ground') else None
        if top is None:
            raise ValueError('%s %s: no ground under the cell centre in %s' % (OPTION, start.text, region))
        preferred = (local[0], local[1], top + 0.25)
    spot = standing_spot(collision, preferred)
    if spot is None:
        raise ValueError('%s %s: no standing spot near %s %s %s in %s (water, a wall or no floor within 64 units); '
                         'pick a spot on dry walkable ground' % (OPTION, start.text, *(_number(v) for v in preferred),
                                                                region))
    moved = max(abs(a - b) for a, b in zip(spot, preferred)) > 0.5
    yaw = (90.0 - start.heading) % 360.0  # global heading (0 = north) -> engine yaw (0 = east)
    line = 'map %s %s %s %s %s' % (owner, *(_number(v) for v in (*spot, yaw)))
    return line, {'kind': 'map', 'map': owner, 'region': region, 'requested': list(preferred), 'arrival': list(spot),
                  'yaw': yaw, 'moved_to_standing_spot': moved,
                  'from': 'engine arrival search on the region collision (arrival_spot.standing_spot)'}


def summary(start):
    return 'quick test build: direct to ' + start.describe()


QUICK_TITLE = 'ATTENTION: THIS IS A QUICK TEST BUILD'
LOGO_TITLE = 'Quick Test Build'


def notice_features(start, excluded=()):
    """The notice's second line in a build that is not MiniWind."""
    text = 'DIRECT TO: ' + start.describe()
    if excluded:
        text += '; excluded: ' + ', '.join(excluded)
    return text[:511]


def town_of(start, resolved):
    """The data file's town line: the start's town (the quick start falls back to it)."""
    if getattr(start, 'town', None):
        return start.town
    return 'balmora' if resolved.get('map', '').startswith('bm') else 'seyda'


def logo_lines(version, chim, scene, measure=len, width=10 ** 9):
    """The startup screen of a direct start that is not MiniWind: its name, the version line
    and "Scene: <start>" (the engine adds "Press ENTER to start")."""
    import miniwind
    version_line = 'AmiWind v%s' % version + (' / CHIM v%s' % chim if chim else '')
    return [LOGO_TITLE, version_line] + miniwind.wrap(miniwind.SCENE_PREFIX + miniwind.check_description(scene),
                                                    measure, width)


def area_label(start):
    """A short ASCII tag for run folder and HDF names: direct-balmora, direct-vivec-arena-pit."""
    words = re.sub(r'[^a-z0-9]+', '-', start.describe().casefold()).strip('-')
    return 'direct-' + (words[:40].rstrip('-') or 'start')


def closure_cells(start, root=ROOT):
    """The cells an --exclude-unreferenced closure of a direct start covers: the start area,
    interior or cell (content_closure cell specs)."""
    from content_closure import area_cells
    if start.kind == 'area':
        return area_cells(start.town, root)
    if start.kind == 'interior':
        return ['interior:' + start.cell]
    cx, cy = (int(start.gx // CELL_UNITS), int(start.gy // CELL_UNITS))
    return ['cell:%d,%d' % (cx, cy)]
