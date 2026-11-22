# SPDX-License-Identifier: GPL-3.0-only
"""The AWMS1 file (id1/mwscript.awm): every compiled script and the tables they index. Big-endian.

  header   "AWMS" u16 version (1) u16 sections u32 file bytes u32 resident bytes
  directory, one row per section: tag[4] u32 offset u32 rows u32 bytes
  CONF  20 bytes: u32 activation range (game units) u16 opcodes per frame u16 opcodes per script run, then the
        script engine's table sizes counted from the game (v0.0.66, EXPANSION-SCRIPT-LIMITS-66; plan.py): u16 attached
        instances, u16 their local values, u16 parked objects, u32 parked values, u16 0. An older file's 8-byte CONF
        gives the engine its earlier constants (256, 4,096, 2,816, 9,216).
  The sections up to CODE are what the engine keeps in memory (the "resident bytes" from the start of the file);
  BIND and STRS stay on disk: the bindings are read at each map change, a string only when one is logged.
  GLOB  8 bytes a global:   u8 type (0 short, 1 long, 2 float) u8 0 u16 name u32 initial value (raw cell)
  JRNL  2 bytes a topic:    u16 name
  SNDS  18 bytes a sound:   u8 pool name[8] u16 length (1/100 s) u8 volume u8 flags (1 mapped, 2 a dungeon ambience:
                            AMBIENCE_SOUNDS)
                            u16 near u16 far (hearing distances in game units, the SOUN record's min/max times the
                            game settings) u16 name
  VOIC  12 bytes a voice:   u8 pool name[8] u16 length (1/100 s) u16 path
  MUSI  4 bytes a track:    u8 track number (255 none) u8 flags (1 mapped) u16 path
  OBJS  12 bytes an object: u32 reference (0: not placed once) u16 id u16 script (0xFFFF none) u16 placed u16 flags
                            (1: the id names a script, its global instance)
  SCRP  16 bytes a script:  u16 name u8 locals u8 stack u16 flags u16 far trigger u32 code offset u32 code bytes
                            (far trigger: game units of a scripted sky/far event's GetDistance Player check,
                            events.far_triggers, 0 none; SCRIPTED-EVENT-PAST-DRAW-DISTANCE-62)
  CODE  the bytecode of every script, one after another
  BIND  24 bytes a placed scripted reference, ascending: u32 reference u16 script u16 flags
                            i16 cell x (or u16 the interior's stable number, the room map's _aw_cell_int)
                            i16 cell y i32 x y z (game units); flags 8 (compiler.BIND_HELD, v0.0.62): an item a
                            placed container or actor holds, its reference compiler.held_key (bit 30, the item's
                            number in bits 24-29, the holder's reference), cell and position the holder's; flags 16
                            (compiler.BIND_PRESENTED, v0.0.68): a placement in a district the build presents as
                            exterior cells, the room flag and number kept, x y z its moved place
  STRT  2 bytes a start script: u16 script
  NEWG  2 bytes a script a new game starts once (Main's CharGenState block: Startup, VampireCheck; v0.0.62,
        NPC-STORY-DISABLED-AT-START-42): u16 script; resident, optional (an older file: none)
  NGWE  4 bytes a region's weather a new game sets for a new-game script AmiWind's own code carries (v0.0.63,
        OPENING-WEATHER-NOT-CLOUDY-63; CharGen's ChangeWeather): u16 the region's catalogue index (the sorted region
        ids of the build's masters, as ChangeWeather's: gamedata.region_catalogue), u8 weather, u8 0; resident,
        optional (an older file: none)
  NGCS  4 bytes the control switches a new-game script AmiWind's own code carries sets on its first run (v0.0.66,
        OPENING-FIGHTING-ON-BEFORE-PAPERS-66; CharGen's DisablePlayerControls, -Jumping, -ViewSwitch, VanityMode,
        -Fighting, -Magic): u16 the switches it leaves off, u16 those it leaves on (gamedata.CONTROL_BITS, the
        engine's aw_story.h AW_CONTROL_* bits); resident, optional (an older file: none)
  HELD  20 bytes an actor standing on an object a script disables (events.py; v0.0.62, SCRIPTED-EVENT-FALLING-MAGE-61),
        sorted by actor: u32 the actor's reference u32 the object's reference f32 x y z (the actor's placed position,
        game units); resident, optional (an older file: none)
  STRS  u32 offset per string, then the NUL-ended strings (cp1252)
  OACT, ACTB, AINV, AITM, ASPT, ASPL, ASPC, ASPE, AEFF, AMGE, AENC, APCS: the actor table (actors.py;
        docs/ACTOR_STATE.md)
  PCEL  the cells each GetPCCell name matches (resident; pccell_section below)
  PMOV  20 bytes a move of the player (PositionCell; resident; written in write() below)
  VISI  12 bytes an actor a PositionCell may bring into a room (resident; written in write() below)
  PLAC  12 bytes an object a Place call names (PlaceAtPC, PlaceAtMe, PlaceItem, PlaceItemCell; resident; write() below)
  PADD  8 bytes a carryable item record that names a script (its OnPCAdd slot, or 0xFF none; resident; write() below)
  LACT  8 bytes a scripted NPC or creature record a levelled list names (resident; write() below)
  EQUP  8 bytes a carried item whose script has OnPCEquip or PCSkipEquip (resident; write() below)
  WATR  8 bytes a room whose cell has the water flag (v0.0.68, GETWATERLEVEL-COLUMN-NOT-ROOM-67), ascending by the
        room's stable number: u16 the number (the room map's _aw_cell_int), u8 flags (1: the water flag), u8 0, f32 the
        room's water level in the original's units (gamedata.interior_water); resident, optional (an older file: the
        engine finds the level from the room map's water, as before). GetWaterLevel reads the loaded room's row (the
        engine's aw_water.h).
  TOPC  2 bytes a dialogue topic (DIAL type 0), sorted by folded id: u16 name (on disk; AddTopic hands the row)
  AIDX, ASPX  2 bytes a row: the AITM / ASPT rows sorted by folded id (v0.0.63, MW-CONSOLE-COMMANDS-62: the
        console's lookup of an item or spell id, a binary search); on disk, optional (an older file: a scan)
  DRSC  12 bytes a dialogue result script, sorted: u32 FNV-1a of its text, u16 length, u16 speaker script, u16 its
        compiled script (_dlg_N), u16 flags (1 did not compile); on disk
  BNAM  8 bytes a placed scripted reference by its object id (v0.0.64, WORLD-BUTTONS-62 round three): u32 FNV-1a of
        the folded id, u32 the reference (a BIND row's), sorted; on disk, optional. The console's "ID"->Activate finds
        a placement the scripts never name (the Ghostgate switches, the Marks coins: not in OBJS) by a binary search
        here, then its attached instance by the reference.
  LOCN  the scripts' variables by name (v0.0.66, SAVE-SCRIPT-ROW-HINT-ONLY-65; on disk, optional: an older file keeps
        locals by their slot only): 8 bytes a script with variables that is not a dialogue result script, ascending by
        script: u16 script, u8 its variables, u8 flags (1: two of its names share a key, those keys are 0), u32 the
        index of its first key; then a u32 key per variable in slot order (local_key: the folded name's FNV-1a in bits
        0-29, the type in bits 30-31, 0 short 1 long 2 float; 0 no name). A save keeps each local with its key and each
        script's layout signature, so a rebuilt script restores every value into the variable of its name.
  HITM  the items placed holders hold, by item (v0.0.66, SAVE-ITEM-SCRIPT-LOCALS-66; on disk, optional): 8 bytes a
        BIND row of a held item, ascending: u32 its reference (compiler.held_key), u32 the name hash of the item's record
        id (name_hash). A save keeps a held item's locals by (holder, item), not by its ordinal among the holder's items.
  SCRH  every script row's name hash (v0.0.66, SAVE-SCRIPT-ROW-HINT-ONLY-65; on disk, optional): u32 name_hash a row,
        so a load finds a saved script whose row moved in a rebuilt file with one read.
  RGNS  2 bytes a region of the image's region catalogue, in its order (v0.0.68, MW-CONSOLE-COMMANDS-62;
        gamedata.region_catalogue): u16 the region's id as its record writes it. The row number is the region index a
        compiled ChangeWeather or ModRegion hands the engine; the console's ChangeWeather and ModRegion find a typed id
        here (a read of a few rows per console line) and dbg weather names the region it shows. On disk, optional (an
        older file: the console names no region).
  WERE  4 bytes a row, 10 rows (v0.0.68, MW-CONSOLE-COMMANDS-62; codegen.Program.werewolf_settings, the numbers a
        compiled BecomeWerewolf and SetWerewolfAcrobatics hand the engine): rows 0-8 BecomeWerewolf's, the werewolf's
        eight attributes then 27 skills from the game settings (GMST fWereWolf*), a byte each (255: none), four to a
        row, high byte first; row 9 SetWerewolfAcrobatics' value (fWereWolfAcrobatics). Signed 32-bit. The console's
        BecomeWerewolf and SetWerewolfAcrobatics read them (10 reads of 4 bytes per console line). On disk, optional
        (an older file: the console's player forms refuse).
  EFFN  2 bytes a magic effect, 143 rows in the game's numbering (v0.0.68, MW-CONSOLE-COMMANDS-62; codegen.EFFECT_NAMES,
        the table a compiled GetEffect takes its number from): u16 the effect's game setting id without "sEffect".
        Row N is the number a compiled GetEffect hands the engine; the console's GetEffect finds a typed id here (one
        read of the section and the names up to the match, per console line). On disk, optional (an older file: the
        console's GetEffect takes a number only).
  CELN  24 bytes a cell a console line can name (v0.0.68, MW-CONSOLE-COMMANDS-62; cell_rows below): every interior
        cell, every exterior cell name and every district the build presents as exterior cells, sorted by (u32 the
        FNV-1a of the name's cp1252 bytes with A-Z lowered, the folded name): u32 hash, u16 name (as its record writes
        it), u8 kind (1 a room, 2 a named exterior cell, 3 a presented district), u8 flags (1: no room map in the
        repo's room lists), u16 the room's stable number (the room map's _aw_cell_int; 0 for an exterior name), u16 the
        room map's name (0xFFFF none), f32 x y z: a room's recentring (rooms.room_table, subtracted before the quarter
        scale) or a presented district's move (presented_exterior.moved_position: x and y added). The console's
        PositionCell, PlaceItemCell, AIFollowCell and AIEscortCell find a typed cell here by a binary search (about a
        dozen reads of 24 bytes, then its name) and work it out as the compiler does (codegen.Program.player_move,
        actor_move, place, ai_cell); its GetPCCell reads the room's name by its number. On disk, optional (an older
        file: the console's cell forms refuse).
  CELG  4 bytes an exterior grid cell (v0.0.68, MW-CONSOLE-COMMANDS-62; grid_rows below), sorted by (x, y): i8 x, i8 y,
        u16 the name OpenMW's getCellName gives it (the cell's own name, else its region's, else sDefaultCellname; a
        presented district's block cells its name). The console's GetPCCell outdoors reads the player's cell's name
        here (a binary search). On disk, optional.

The engine keeps scripts, globals, quests and worn items in a save by the name hash of their id (aw_ledger.h,
name_hash below): write() refuses a file in which two different names share one (their saved values would mix).

A pool name is the 8 bytes of a converted file's name in the media catalogue: sound/pool/a<16 hex>.wav.
"""
import struct

from .opcodes import NAME, LAYOUT

MAGIC = b'AWMS'
VERSION = 1
TYPES = {'s': 0, 'l': 1, 'f': 2}
ORDER = ('CONF', 'GLOB', 'JRNL', 'SNDS', 'VOIC', 'MUSI', 'OBJS', 'SCRP', 'STRT', 'NEWG', 'NGWE', 'NGCS', 'HELD', 'OACT', 'PCEL', 'PMOV', 'SPFX', 'VISI', 'PLAC', 'PADD', 'LACT', 'EQUP', 'WATR', 'CODE', 'BIND', 'STRS',
         'ACTB', 'AINV', 'AITM', 'ASPT', 'ASPL', 'TOPC', 'ASPC', 'ASPE', 'AEFF', 'AMGE', 'DRSC', 'AENC', 'APCS',
         'AIDX', 'ASPX') + ('BNAM',) + ('LOCN', 'HITM', 'SCRH') + ('RGNS', 'WERE', 'EFFN') + ('CELN', 'CELG')
# The actor sections (actors.py, docs/ACTOR_STATE.md): OACT is resident (a script's target -> its actor row); the
# others stay on disk and are read a row at a time by the engine's actor state (aw_actorstate.c).
ACTOR_SECTIONS = ('OACT', 'ACTB', 'AINV', 'AITM', 'ASPT', 'ASPL', 'ASPC', 'ASPE', 'AEFF', 'AMGE', 'AENC', 'APCS',
                  'AIDX', 'ASPX')
DEFAULT_CONF = {'range_units': 12288, 'ops_per_frame': 4000, 'ops_per_run': 2000,
                # the engine's earlier constants (aw_mwvm.h AW_MWVM_*_DEFAULT): a build writes the counted plan instead
                'instances': 256, 'cells': 4096, 'parked': 2816, 'park_cells': 9216}
CONF_BYTES = 20
RESIDENT = ORDER[:ORDER.index('BIND')]


def conf_bytes(conf):
    """The CONF section of CONF (DEFAULT_CONF's keys): 20 bytes."""
    from .plan import check_plan
    check_plan(conf)
    return struct.pack('>IHHHHHIH', conf['range_units'], conf['ops_per_frame'], conf['ops_per_run'],
                       conf['instances'], conf['cells'], conf['parked'], conf['park_cells'], 0)


def conf_read(raw):
    """DEFAULT_CONF's keys from a CONF section's bytes (8-byte: the earlier constants)."""
    out = dict(DEFAULT_CONF)
    out['range_units'], out['ops_per_frame'], out['ops_per_run'] = struct.unpack_from('>IHH', raw, 0)
    if len(raw) >= CONF_BYTES:
        out['instances'], out['cells'], out['parked'], out['park_cells'] = struct.unpack_from('>HHHI', raw, 8)
    return out
# The engine's limits (the interpreter's MAX_SCRIPTS and MAX_GLOBALS; tests/test_mwscript.py keeps them equal): a file over them is refused there and every
# script stays off (MWSCRIPT-REFUSED-SCRIPT-COUNT-58), so the builder refuses it here first.
ENGINE_MAX_SCRIPTS = 16384
ENGINE_MAX_GLOBALS = 512
# SNDS flags. 2: a dungeon ambience (TOMB-MUSIC-OVER-AMBIENT-60, decided for the project 5 November 2026): while a
# script loops one of these SOUN records (PlayLoopSound3D(VP) of the original's sound markers: sound_haunted and
# sound_spirit_whisper in the ancestral tombs, sound_cave_drip and sound_cave_wind in the caves) the engine rests the
# exploration music (aw_music.c AW_MusicAmbience); battle music still plays. Folded SOUN ids.
SOUND_MAPPED = 1
SOUND_AMBIENCE = 2
AMBIENCE_SOUNDS = frozenset(('haunted', 'spirit ambient voices', 'cave drip', 'cave wind'))


def check_limits(scripts, globals_):
    """Raise ValueError when the engine would refuse a file with this many scripts or globals."""
    if scripts > ENGINE_MAX_SCRIPTS:
        raise ValueError('%d scripts: the engine takes at most %d (the interpreter refuses more)' % (scripts, ENGINE_MAX_SCRIPTS))
    if globals_ > ENGINE_MAX_GLOBALS:
        raise ValueError('%d globals: the engine takes at most %d (the interpreter refuses more)' % (globals_, ENGINE_MAX_GLOBALS))


def _hash8(row):
    path = row.get('path_pool') or ''
    if not row.get('resolved') or not path:
        return b'\0' * 8
    name = path.rsplit('/', 1)[-1]
    if not (name.startswith('a') and name.endswith('.wav') and len(name) == 21):
        raise ValueError('Not a media pool name: ' + path)
    return bytes.fromhex(name[1:17])


def _centis(row):
    return max(0, min(0xFFFF, int(round(row.get('seconds', 0) * 100))))


def pccell_section(table):
    """(bytes, rows) of PCEL: u32 offset (from the section's start) per row, then each row: u16 rooms, u16 outdoor
    cells (bit 15: the name also matches sDefaultCellname, an outdoor cell with no record; not used yet), u16 per
    room (its stable number), then s8 x, s8 y per outdoor cell; rows padded to 2 bytes."""
    rows = table.rows if table is not None else []
    head = bytearray()
    body = bytearray()
    for r in rows:
        head += struct.pack('>I', 4 * len(rows) + len(body))
        body += struct.pack('>HH', len(r['rooms']), len(r['outside']) | (0x8000 if r['wilderness'] else 0))
        body += b''.join(struct.pack('>H', n) for n in r['rooms'])
        body += b''.join(struct.pack('>bb', x, y) for x, y in r['outside'])
        if len(r['outside']) > 0x7FFF or len(r['rooms']) > 0xFFFF:
            raise ValueError('GetPCCell row too long: ' + r['name'])
    return bytes(head + body), len(rows)


# Records the player can carry (the original's item records; their script runs while carried)
CARRIED = ('ALCH', 'APPA', 'ARMO', 'BOOK', 'CLOT', 'INGR', 'LIGH', 'LOCK', 'MISC', 'PROB', 'REPA', 'WEAP')


def fnv1a(text):
    """The engine's AW_MwvmTextHash of a folded record id (cp1252)."""
    h = 0x811C9DC5
    for b in text.casefold().encode('cp1252', 'replace'):
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


NO_SLOT = 0xFF   # a PADD row whose script has no OnPCAdd local: the script runs while carried, nothing is set
WATER_FLAG = 1   # a WATR row's flags: the room's cell carries the water flag (CELL flags 0x02)
WATER_ROW = struct.Struct('>HBBf')


def water_rows(data):
    """The WATR rows (v0.0.68, GETWATERLEVEL-COLUMN-NOT-ROOM-67): [(stable number, flags, level)] of every interior cell
    of DATA (gamedata.GameData) whose cell has the water flag and a stable number (the room map's _aw_cell_int),
    ascending by number, the level in the original's units. GetWaterLevel in such a room reads its level; in a room
    with no row, the lowest float; outdoors 0 (OpenMW apps/openmw/mwscript/cellextensions.cpp OpGetWaterLevel)."""
    numbers = getattr(data, 'interior_numbers', {}) or {}
    rows = []
    for cell, water in (getattr(data, 'interior_water', {}) or {}).items():
        number = numbers.get(cell)
        if not water.get('water') or not number:
            continue
        if not 0 < number <= 0xFFFF:
            raise ValueError('WATR: room %r has the stable number %r, past the row\'s 16 bits' % (cell, number))
        rows.append((number, WATER_FLAG, float(water.get('level', 0.0))))
    rows.sort()
    for a, b in zip(rows, rows[1:]):
        if a[0] == b[0]:
            raise ValueError('WATR: two water rooms share the stable number %d' % a[0])
    return rows


def water_section(rows):
    """(bytes, rows) of the WATR section of ROWS (water_rows)."""
    return b''.join(WATER_ROW.pack(n, f, 0, level) for n, f, level in rows), len(rows)


def new_game_weather_rows(program, compiled):
    """The NGWE rows (v0.0.63, OPENING-WEATHER-NOT-CLOUDY-63): [(region index, weather)] of the ChangeWeather lines of
    the new game's scripts (Main's CharGenState block) that the build does not run, because AmiWind's own code
    carries them (compiled hand-written: CharGen). A script that runs sets its own weather. A region the image has not
    is left out, as ChangeWeather's call is no code then."""
    from .codegen import SCRIPT_HANDWRITTEN
    from .gamedata import new_game_weather, region_catalogue
    p = program
    regions = region_catalogue(p.data)
    scripts = getattr(p.data, 'scripts', {})
    out = []
    for name in getattr(p.data, 'new_game', []):
        k = p.scripts.index.get(name)
        if k is None or not (compiled[k].flags & SCRIPT_HANDWRITTEN):
            continue
        s = scripts.get(name)
        for region, weather in new_game_weather(getattr(s, 'text', '') if s else ''):
            if region in regions and 0 <= weather < 10:
                out.append((regions.index(region), weather))
    return out


def region_rows(data):
    """The RGNS rows (v0.0.68, MW-CONSOLE-COMMANDS-62): the region ids of DATA's region catalogue in its order
    (gamedata.region_catalogue), each as its record writes it (gamedata.region_ids; the folded id when unknown). Row N is
    region index N, the number a compiled ChangeWeather or ModRegion hands the engine."""
    written = getattr(data, 'region_ids', {}) or {}
    from .gamedata import region_catalogue
    return [written.get(r, r) for r in region_catalogue(data)]


WERE_ROWS = 10   # 9 BecomeWerewolf numbers (35 settings, four a number) and SetWerewolfAcrobatics' one


def werewolf_rows(program):
    """The WERE rows (v0.0.68, MW-CONSOLE-COMMANDS-62): the numbers a compiled BecomeWerewolf hands the engine, then
    SetWerewolfAcrobatics' one, from the same function the compiler takes them from (codegen.Program.werewolf_settings);
    [] for a program without it."""
    settings = getattr(program, 'werewolf_settings', None)
    if settings is None:
        return []
    rows = list(settings(True)) + list(settings(False))
    if len(rows) != WERE_ROWS:
        raise ValueError('WERE: %d werewolf numbers, the engine reads %d' % (len(rows), WERE_ROWS))
    return rows


# CELN kinds and flags (the engine's aw_mwconsole.h AW_MWCON_CELL_*)
CELL_ROOM, CELL_EXTERIOR, CELL_PRESENTED = 1, 2, 3
CELL_NO_MAP = 1
CELL_ROW = 24


def cell_fold(name):
    """A cell name's bytes as the console's lookup folds them: cp1252, A-Z lowered (the engine's aw_mwconsole.c fold)."""
    return bytes(b + 32 if 65 <= b <= 90 else b for b in name.encode('cp1252', 'replace'))


def cell_hash(name):
    """The CELN key of a cell name: 32-bit FNV-1a of its folded bytes (aw_mwconsole.c cell_hash)."""
    h = 0x811C9DC5
    for b in cell_fold(name):
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


def cell_rows(program):
    """The CELN rows (v0.0.68, MW-CONSOLE-COMMANDS-62): [(hash, name, kind, flags, number, map name or None, offset)]
    sorted by (hash, folded name). Every interior cell of the build's masters by its stable number
    (cell_numbers.number_cells, the number the room maps carry) with its room map and recentring from the program's room
    table (rooms.room_table; a room the lists lack is flagged, as PositionCell of the player then stays "not yet"); a
    district the build presents as exterior cells (program.presented) is kind 3 with its move instead; every exterior
    cell name once (OpenMW's findCell finds an exterior by its name). [] for a program without game data."""
    data = getattr(program, 'data', None)
    if data is None or not getattr(data, 'interior_ids', None):
        return []
    from cell_numbers import number_cells
    rooms = getattr(program, 'rooms', None) or {}
    presented = getattr(program, 'presented', None) or {}
    rows = {}
    for r in number_cells(data.interior_ids):
        key = r['cell'].casefold()
        room, place = rooms.get(key), presented.get(key)
        if r['number'] > 0xFFFF:
            raise ValueError('CELN: interior %r has number %d, past the table\'s 16 bits' % (r['cell'], r['number']))
        if place is not None:
            if room and any(room.get('offset') or ()):
                # the console moves a presented district's places by its move alone, as the compiler does
                raise ValueError('CELN: presented district %r is also a recentred room' % r['cell'])
            kind, offset = CELL_PRESENTED, (float(place['offset'][0]), float(place['offset'][1]), 0.0)
        else:
            kind, offset = CELL_ROOM, tuple(float(v) for v in ((room or {}).get('offset') or (0.0, 0.0, 0.0)))
        rows[cell_fold(r['cell'])] = (r['cell'], kind, 0 if room else CELL_NO_MAP, r['number'],
                                      room['map'] if room else None, offset)
    for key, place in sorted(presented.items()):
        if cell_fold(place['cell']) not in rows:
            rows[cell_fold(place['cell'])] = (place['cell'], CELL_PRESENTED, CELL_NO_MAP, 0, None,
                                              (float(place['offset'][0]), float(place['offset'][1]), 0.0))
    for (x, y), (cell, region) in sorted(data.exteriors.items()):
        if cell and cell_fold(cell) not in rows:
            rows[cell_fold(cell)] = (cell, CELL_EXTERIOR, 0, 0, None, (0.0, 0.0, 0.0))
    return sorted(((cell_hash(v[0]),) + v for k, v in rows.items()), key=lambda r: (r[0], cell_fold(r[1])))


def grid_rows(program):
    """The CELG rows (v0.0.68, MW-CONSOLE-COMMANDS-62): [(x, y, name)] sorted by (x, y), every exterior grid cell by the
    name OpenMW's getCellName gives it (its own name, else its region's name, else sDefaultCellname), and the block cells
    of every district the build presents by the district's name (as codegen.Program.pccell matches them)."""
    data = getattr(program, 'data', None)
    if data is None:
        return []
    names = {}
    for (x, y), (cell, region) in data.exteriors.items():
        names[(x, y)] = cell or data.regions.get(region) or data.default_cell_name
    for place in (getattr(program, 'presented', None) or {}).values():
        for dx in range(place['size'][0]):
            for dy in range(place['size'][1]):
                names[(place['block'][0] + dx, place['block'][1] + dy)] = place['cell']
    bad = sorted(xy for xy in names if not all(-128 <= v <= 127 for v in xy))
    if bad:
        raise ValueError('CELG: exterior cells outside the table\'s -128..127: %s' % bad[:4])
    return [(x, y, names[(x, y)]) for x, y in sorted(names)]


def cell_sections(cells, grid, string):
    """(CELN bytes, CELG bytes) of cell_rows' CELLS and grid_rows' GRID; STRING interns a string, its index."""
    celn = b''.join(struct.pack('>IHBBHH3f', h, string(name), kind, flags, number,
                                string(room_map) if room_map else 0xFFFF, *offset)
                    for h, name, kind, flags, number, room_map, offset in cells)
    celg = b''.join(struct.pack('>bbH', x, y, string(name)) for x, y, name in grid)
    return celn, celg


def new_game_control_rows(program, compiled):
    """The NGCS rows (v0.0.66, OPENING-FIGHTING-ON-BEFORE-PAPERS-66): [(off, on)] of the control switches each new-game
    script (Main's CharGenState block) the build does not run, because AmiWind's own code carries it (compiled
    hand-written: CharGen), sets on its first run; one row a script that sets any. A script that runs sets its own."""
    from .codegen import SCRIPT_HANDWRITTEN
    from .gamedata import new_game_controls
    p = program
    scripts = getattr(p.data, 'scripts', {})
    out = []
    for name in getattr(p.data, 'new_game', []):
        k = p.scripts.index.get(name)
        if k is None or not (compiled[k].flags & SCRIPT_HANDWRITTEN):
            continue
        s = scripts.get(name)
        off, on = new_game_controls(getattr(s, 'text', '') if s else '')
        if off or on:
            out.append((off, on))
    return out


def pcadd_rows(program):
    """PADD (v0.0.62, CENSUS-INTRO-SCRIPTS-62; every scripted item since MWSCRIPT-UNPLACED-ATTACH-62): one row per
    carryable item record that names a script, sorted by the FNV-1a of the folded record id: (hash, script index, the
    OnPCAdd slot or NO_SLOT). OpenMW 0.51 runs the script of an item in the player's inventory (its local OnPCAdd reads 1
    once the item arrives); the engine starts the item's carried instance when it arrives and at every map change while
    it is carried, and stops it when the last one leaves (aw_mwhost.c carried_sync)."""
    rows = []
    bases = getattr(program.data, 'bases', {}) or {}
    for ident, (tag, script) in bases.items():
        if tag not in CARRIED or not script or script not in program.scripts.index:
            continue
        slot = (program.script_locals.get(script) or {}).get('onpcadd')
        rows.append((fnv1a(ident), program.scripts.index[script], NO_SLOT if slot is None else slot[1]))
    return sorted(set(rows))


def levelled_actor_rows(program):
    """LACT (v0.0.62, MWSCRIPT-UNPLACED-ATTACH-62): one row per NPC or creature record a levelled creature list names
    whose record names a script, sorted by the FNV-1a of the folded record id (the actor table's base hash): (hash,
    script index). The engine attaches that script to the actor a levelled list gives when it spawns, under the
    list's reference (OpenMW 0.51 mwclass/creaturelevlist.cpp: the list's pick is a new actor of that record, whose
    script runs as any placed actor's)."""
    rows = []
    bases = getattr(program.data, 'bases', {}) or {}
    for ident in getattr(program.data, 'levelled_actors', ()) or ():
        tag, script = bases.get(ident, (None, ''))
        if tag not in ('CREA', 'NPC_') or not script or script not in program.scripts.index:
            continue
        rows.append((fnv1a(ident), program.scripts.index[script]))
    return sorted(set(rows))


def name_hash(ident):
    """The engine's AW_LedgerNameHash (aw_ledger.c): FNV-1a over the id with A-Z folded, 0 becomes 1 (as
    prepare_focus.name_hash): the key a save keeps a script, a global, a quest, an item and a variable by."""
    h = 2166136261
    for c in ident.encode('cp1252', 'replace'):
        if 65 <= c <= 90:
            c += 32
        h = ((h ^ c) * 16777619) & 0xFFFFFFFF
    return h or 1


LOCAL_TYPES = {'s': 0, 'l': 1, 'f': 2}
LOCN_COLLIDED = 1


def local_key(name, letter):
    """A script variable's key in LOCN and in a save (aw_ledger.h slice 8): the folded name's name_hash in bits 0-29,
    its type in bits 30-31 (0 short, 1 long, 2 float), never 0."""
    return ((name_hash(name) & 0x3FFFFFFF) | (LOCAL_TYPES[letter] << 30)) or 1


def local_rows(program, compiled):
    """LOCN (v0.0.66, SAVE-SCRIPT-ROW-HINT-ONLY-65): ([(script index, [key per slot], flags)], report) for every
    compiled script with variables that is not a dialogue result script (a result script runs on its speaker's
    variables), ascending by script. Two names of one script whose keys share the name bits (bits 0-29) are written 0
    and the script flagged LOCN_COLLIDED: the engine restores those two only while the script's variables are as saved,
    never into another variable. The report: scripts, variables, and the collided names."""
    from .codegen import SCRIPT_DIALOGUE
    rows, collided, count = [], [], 0
    for index, c in enumerate(compiled):
        if not c.nlocals or c.flags & SCRIPT_DIALOGUE:
            continue
        keys, names = [0] * c.nlocals, [None] * c.nlocals
        for name, (letter, slot) in (program.script_locals.get(c.ident) or {}).items():
            if 0 <= slot < c.nlocals:
                keys[slot], names[slot] = local_key(name, letter), name
        shared = {}
        for slot, key in enumerate(keys):
            if key:
                shared.setdefault(key & 0x3FFFFFFF, []).append(slot)
        flags = 0
        for slots in shared.values():
            if len(slots) > 1:
                flags |= LOCN_COLLIDED
                collided.append({'script': c.name, 'names': [names[s] for s in slots]})
                for s in slots:
                    keys[s] = 0
        rows.append((index, keys, flags))
        count += len(keys)
    return rows, {'scripts': len(rows), 'variables': count, 'collided': collided}


def locn_section(rows):
    """(bytes, rows) of LOCN: the 8-byte script rows, then the keys."""
    head, keys = bytearray(), bytearray()
    for index, row_keys, flags in rows:
        if not 0 < len(row_keys) <= 255 or index > 0xFFFF:
            raise ValueError('LOCN: script %d with %d variables' % (index, len(row_keys)))
        head += struct.pack('>HBBI', index, len(row_keys), flags, len(keys) // 4)
        keys += b''.join(struct.pack('>I', k) for k in row_keys)
    return bytes(head + keys), len(rows)


def held_item_rows(binds):
    """HITM (v0.0.66, SAVE-ITEM-SCRIPT-LOCALS-66): [(held key, name_hash of the item's record id)] of every BIND row of
    an item a placed holder holds (compiler.BIND_HELD), sorted by key."""
    return sorted((b['reference'], name_hash(b['id'])) for b in binds if b['flags'] & 8 and b.get('id'))


def check_name_hashes(label, names, bits=0xFFFFFFFF):
    """Raise ValueError when two different names (folded) share name_hash (in BITS): a save keeps these by the hash,
    so their saved values would mix (SAVE-SCRIPT-ROW-HINT-ONLY-65: never mixed; the builder refuses the file)."""
    seen = {}
    for name in names:
        folded = name.casefold()
        h = name_hash(name) & bits
        if seen.setdefault(h, folded) != folded:
            raise ValueError('%s %r and %r share the name hash %08x: their saved values would mix' %
                             (label, seen[h], folded, h))


def bound_name_rows(binds):
    """BNAM (v0.0.64, WORLD-BUTTONS-62 round three): [(FNV-1a of the folded object id, reference)] of every placed
    scripted reference of BIND (an item a holder carries has no place of its own: left out), sorted."""
    return sorted({(fnv1a(b['id']), b['reference']) for b in binds
                   if b.get('id') and b.get('type') != 'HELD' and not b['flags'] & 8})


def write(program, compiled, binds, conf=None):
    """The file's bytes, and a size table {section: bytes}. CONF: config/mwscript.json's activation and budget."""
    p = program
    check_limits(len(compiled), len(p.globals))
    # a save keeps these by their name hash: two names of one hash would mix their values (SAVE-SCRIPT-ROW-HINT-ONLY-65)
    check_name_hashes('scripts', [row['name'] for row in p.scripts.rows])
    check_name_hashes('globals', [row['name'] for row in p.globals.rows])
    check_name_hashes('quests', [row['name'] for row in p.journal.rows])
    conf = dict(DEFAULT_CONF, **(conf or {}))
    confb = conf_bytes(conf)
    for c in compiled:
        p.string(c.name)
    sections = {}
    # scripts and code first: they intern their names
    code = bytearray()
    scrp = bytearray()
    far = getattr(p, 'far', None) or {}
    for row, c in zip(p.scripts.rows, compiled):
        scrp += struct.pack('>HBBHHII', p.string(row['name']), c.nlocals, min(255, c.max_depth), c.flags,
                            far.get(row['name'].casefold(), 0),
                            len(code), len(c.code))
        code += c.code
    glob = bytearray()
    for row in p.globals.rows:
        kind = TYPES[row['type']]
        v = row['value']
        whole = 0 if v != v else int(max(-2 ** 31, min(2 ** 31 - 1, v)))   # the record stores a float: clamp, NaN 0
        if kind == 0:
            whole = (whole + 32768) % 65536 - 32768
        value = struct.pack('>f', v) if kind == 2 else struct.pack('>i', whole)
        glob += struct.pack('>BBH', kind, 0, p.string(row['name'])) + value
    jrnl = b''.join(struct.pack('>H', p.string(r['name'])) for r in p.journal.rows)
    snds = bytearray()
    folded = {i: k for k, i in p.sounds.index.items()}
    for i, r in enumerate(p.sounds.rows):
        lo, hi = p.data.sound_range({'min': r.get('min', 0), 'max': r.get('max', 0)})
        flags = (SOUND_MAPPED if r.get('resolved') else 0) | (SOUND_AMBIENCE if ' '.join(folded.get(i, '').split()) in AMBIENCE_SOUNDS else 0)
        snds += _hash8(r) + struct.pack('>HBBHHH', _centis(r), r.get('volume', 255) & 255,
                                        flags, min(lo, 0xFFFF), min(hi, 0xFFFF),
                                        r['name_string'])
    snds = bytes(snds)
    voic = b''.join(_hash8(r) + struct.pack('>HH', _centis(r), r['name_string']) for r in p.voices.rows)
    musi = b''.join(struct.pack('>BBH', r.get('track', 255) if r.get('resolved') else 255,
                                1 if r.get('resolved') else 0, r['name_string']) for r in p.music.rows)
    objs = b''.join(struct.pack('>IHHHH', r['reference'], r['id_string'],
                                0xFFFF if r['script'] is None else r['script'], min(r['placed'], 0xFFFF),
                                1 if r['kind'] == 'script' else 0) for r in p.objects.rows)
    bind = bytearray()
    for b in binds:
        if isinstance(b['cell'], tuple):
            cx, cy = b['cell']
            cell = struct.pack('>hh', max(-32768, min(32767, cx)), max(-32768, min(32767, cy)))
        else:
            cell = struct.pack('>Hh', b['cell'], 0)
        bind += struct.pack('>IHH', b['reference'], b['script'], b['flags']) + cell + struct.pack('>iii', *b['position'])
    strt = b''.join(struct.pack('>H', p.scripts.index[s]) for s in p.data.start_scripts if s in p.scripts.index)
    newg = b''.join(struct.pack('>H', p.scripts.index[s]) for s in getattr(p.data, 'new_game', [])
                    if s in p.scripts.index)
    ngwe_rows = new_game_weather_rows(p, compiled)
    ngcs_rows = new_game_control_rows(p, compiled)
    held_rows = getattr(p, 'held', None) or []
    held = b''.join(struct.pack('>IIfff', r['actor'], r['support'], *r['position'])
                    for r in sorted(held_rows, key=lambda r: r['actor']))
    pcel = pccell_section(getattr(p, 'pccells', None))
    # PMOV, 20 bytes a move of the player (PositionCell, v0.0.54): u8 kind (1 outdoors, 2 into a room) u8 0 u16 the
    # room map's name (string index, 0xFFFF outdoors) f32 x y z (outdoors the original's units; a room its map's own
    # units, as a door's arrival) f32 yaw (degrees)
    moves = getattr(p, 'moves', None)
    pmov = (b''.join(struct.pack('>BBHffff', r['kind'], 0, r['map'], *r['at'], r['yaw']) for r in moves.rows)
            if moves is not None else b'', len(moves) if moves is not None else 0)
    # SPFX (v0.0.57, SPELL-EFFECTS-57): 4 bytes a spell a Cast names (u16 first effect, u8 effects, u8 0), then 8
    # bytes an effect (u8 kind 0 drain 1 damage 2 restore 3 fortify 4 cure 5 an effect by its number with no attribute
    # or skill (v0.0.62, codegen.PASSIVE_EFFECTS), u8 stat (kind 5: the effect number), u16 seconds, u16 low, u16 high);
    # resident
    spfx_rows = getattr(p, 'spfx', None)
    head, body, first = bytearray(), bytearray(), 0
    for r in (spfx_rows.rows if spfx_rows is not None else []):
        head += struct.pack('>HBB', first, len(r['effects']), 0)
        for e in r['effects']:
            body += struct.pack('>BBHHH', *e)
        first += len(r['effects'])
    spfx = (bytes(head + body), len(spfx_rows) if spfx_rows is not None else 0)
    # VISI (v0.0.62, MWSCRIPT-POSITIONCELL-ACTORS-62): 12 bytes an actor a PositionCell may bring into a room, sorted
    # by (room, reference): u32 the room's stable number, u32 the actor's reference, u16 its home room map's name
    # (string index; 0xFFFF outdoors or a room this build lacks), u16 0; resident
    visitors = getattr(p, 'visitors', None) or {}
    visi = (b''.join(struct.pack('>IIHH', room, ref, home, 0) for (room, ref), home in sorted(visitors.items())),
            len(visitors))
    # PLAC (v0.0.62, MWSCRIPT-PLACE-OBJECTS-62): 12 bytes an object the scripts' Place calls name, in the order of
    # codegen.Program.place_rows (sorted by folded id): u16 id, u16 the template's home room map (0xFFFF none), u32 the
    # template reference (0 none), u16 the record's script (0xFFFF none), u8 kind (0 an actor, 1 an item, 2 other),
    # u8 flags (1 the engine can make it; v0.0.67: 2 a point of its own, no map places the record, its script runs on
    # it; 4 a levelled creature list, one creature of it rolled at the player's level); resident
    places = p.place_rows() if hasattr(p, 'place_rows') else []
    plac = (b''.join(struct.pack('>HHIHBB', r['id'], r['home'], r['template'], r['script'], r['kind'],
                                 (1 if r['carried'] else 0) | (2 if r.get('point') else 0) |
                                 (4 if r.get('levelled') else 0)) for r in places), len(places))
    # EQUP (v0.0.62, MWSCRIPT-GAP-FUNCTIONS-62): 8 bytes a carried item whose script declares OnPCEquip or
    # PCSkipEquip, sorted by folded id: u16 id, u16 its script, u8 OnPCEquip's slot, u8 PCSkipEquip's slot (0xFF none),
    # u16 0; resident
    equips = p.equip_rows() if hasattr(p, 'equip_rows') else []
    equp = (b''.join(struct.pack('>HHBBH', r[1], r[2], r[3], r[4], 0) for r in equips), len(equips))
    # the engine runs a worn item's script under the low 24 bits of its id's hash (aw_mwhost.c carried_key)
    check_name_hashes('worn items', [r[0] for r in equips], 0xFFFFFF)
    # TOPC, 2 bytes a dialogue topic (v0.0.57): u16 name, sorted by folded id (AddTopic hands the row number); on disk
    rows = getattr(p, 'topic_rows', None)
    topics = sorted(rows(), key=rows().get) if rows else []
    names = getattr(p.data, 'topics', {})
    topc = (b''.join(struct.pack('>H', p.string(names[k])) for k in topics), len(topics))
    # RGNS (v0.0.68, MW-CONSOLE-COMMANDS-62): the region catalogue's ids in its order, u16 name; on disk. Interned here,
    # before STRS is written below
    regions = region_rows(p.data)
    rgns = (b''.join(struct.pack('>H', p.string(name)) for name in regions), len(regions))
    # EFFN (v0.0.68, MW-CONSOLE-COMMANDS-62): the magic effects' ids in the game's numbering, u16 name; on disk. Interned
    # here, before STRS is written below
    from .codegen import EFFECT_NAMES
    effn = (b''.join(struct.pack('>H', p.string(name)) for name in EFFECT_NAMES), len(EFFECT_NAMES))
    # CELN and CELG (v0.0.68, MW-CONSOLE-COMMANDS-62): the console's cell table; on disk. Interned here, before STRS is
    # written below
    cells, grid = cell_rows(p), grid_rows(p)
    celn_bytes, celg_bytes = cell_sections(cells, grid, p.string)
    celn, celg = (celn_bytes, len(cells)), (celg_bytes, len(grid))
    # DRSC (v0.0.58, DIALOGUE-COMPLETE-58): the dialogue's result scripts, 12 bytes a row sorted by (hash, length,
    # speaker script): u32 FNV-1a of the result text, u16 its length, u16 the speaker's script (0xFFFF none), u16 the
    # compiled _dlg_N script, u16 flags (1: did not compile); on disk, read when an answer is shown
    drsc_rows = []
    for r in getattr(p, 'results', []):
        sp = p.scripts.index.get(r['speaker_script'], 0xFFFF) if r['speaker_script'] else 0xFFFF
        index = p.scripts.index[r['script']]
        broken = 1 if compiled[index].error is not None else 0
        drsc_rows.append((r['hash'], min(0xFFFF, r['length']), sp, index, broken))
    drsc_rows.sort()
    drsc = (b''.join(struct.pack('>IHHHH', *r) for r in drsc_rows), len(drsc_rows))
    blob = bytearray()
    offsets = []
    for s in p.strings.rows:
        offsets.append(len(blob))
        blob += s.encode('cp1252', 'replace') + b'\0'
    strs = b''.join(struct.pack('>I', o) for o in offsets) + bytes(blob)
    sections = {'CONF': (confb, 1), 'STRS': (strs, len(p.strings)), 'GLOB': (bytes(glob), len(p.globals)), 'JRNL': (jrnl, len(p.journal)),
                'SNDS': (snds, len(p.sounds)), 'VOIC': (voic, len(p.voices)), 'MUSI': (musi, len(p.music)),
                'OBJS': (objs, len(p.objects)), 'SCRP': (bytes(scrp), len(compiled)),
                'CODE': (bytes(code), len(compiled)), 'BIND': (bytes(bind), len(binds)),
                'STRT': (strt, len(strt) // 2), 'NEWG': (newg, len(newg) // 2), 'HELD': (held, len(held_rows)), 'PCEL': pcel, 'PMOV': pmov, 'TOPC': topc, 'SPFX': spfx,
                'VISI': visi, 'PLAC': plac, 'EQUP': equp, 'DRSC': drsc,
                'NGWE': (b''.join(struct.pack('>HBB', r, w, 0) for r, w in ngwe_rows), len(ngwe_rows)),
                'NGCS': (b''.join(struct.pack('>HH', off, on) for off, on in ngcs_rows), len(ngcs_rows))}
    # PADD (v0.0.62, CENSUS-INTRO-SCRIPTS-62, MWSCRIPT-UNPLACED-ATTACH-62): 8 bytes a carryable item record that names
    # a script, sorted by the FNV-1a of its folded id: u32 hash, u16 script, u8 the OnPCAdd local's slot (0xFF: none),
    # u8 0; resident
    padd_rows = pcadd_rows(p)
    sections['PADD'] = (b''.join(struct.pack('>IHBB', h, s, slot, 0) for h, s, slot in padd_rows), len(padd_rows))
    # LACT (v0.0.62, MWSCRIPT-UNPLACED-ATTACH-62): 8 bytes a scripted NPC or creature record a levelled list names,
    # sorted by the FNV-1a of its folded id: u32 hash, u16 script, u16 0; resident
    lact_rows = levelled_actor_rows(p)
    sections['LACT'] = (b''.join(struct.pack('>IHH', h, s, 0) for h, s in lact_rows), len(lact_rows))
    # WATR (v0.0.68, GETWATERLEVEL-COLUMN-NOT-ROOM-67): every water room's own level; resident
    sections['WATR'] = water_section(water_rows(p.data))
    bnam_rows = bound_name_rows(binds)
    sections['BNAM'] = (b''.join(struct.pack('>II', h, r) for h, r in bnam_rows), len(bnam_rows))
    # LOCN and HITM (v0.0.66): the scripts' variables by name and the held items by item, for the save; on disk
    locn_rows, p.local_names_report = local_rows(p, compiled)
    sections['LOCN'] = locn_section(locn_rows)
    hitm_rows = held_item_rows(binds)
    sections['HITM'] = (b''.join(struct.pack('>II', k, h) for k, h in hitm_rows), len(hitm_rows))
    sections['SCRH'] = (b''.join(struct.pack('>I', name_hash(row['name'])) for row in p.scripts.rows), len(p.scripts.rows))
    sections['RGNS'] = rgns
    were = werewolf_rows(p)
    sections['WERE'] = (b''.join(struct.pack('>i', v) for v in were), len(were))
    sections['EFFN'] = effn
    sections['CELN'] = celn
    sections['CELG'] = celg
    actors = getattr(p, 'actors', None)
    if actors is not None:
        sections.update(actors.sections(p.objects.rows))
        # the actor rows interned strings: STRS is written again with them
        blob, offsets = bytearray(), []
        for s in p.strings.rows:
            offsets.append(len(blob))
            blob += s.encode('cp1252', 'replace') + b'\0'
        sections['STRS'] = (b''.join(struct.pack('>I', o) for o in offsets) + bytes(blob), len(p.strings))
    else:
        sections.update({tag: (b'', 0) for tag in ACTOR_SECTIONS})
    head = 16 + 16 * len(ORDER)
    out = bytearray()
    directory = bytearray()
    at = head
    body = bytearray()
    resident = head
    for tag in ORDER:
        data, rows = sections[tag]
        pad = (-len(data)) % 4
        if tag == 'BIND':
            resident = at
        directory += tag.encode('ascii') + struct.pack('>III', at, rows, len(data))
        body += data + b'\0' * pad
        at += len(data) + pad
    out += MAGIC + struct.pack('>HHII', VERSION, len(ORDER), head + len(body), resident) + directory + body
    sizes = {tag: len(sections[tag][0]) for tag in ORDER}
    sizes['resident'] = resident
    return bytes(out), sizes


def read(raw):
    """{'version', tag: bytes, tag+'_rows': n} of an AWMS1 file; raises ValueError on a bad file."""
    if raw[:4] != MAGIC:
        raise ValueError('Not an AWMS file')
    version, count, size, resident = struct.unpack_from('>HHII', raw, 4)
    if version != VERSION or size != len(raw):
        raise ValueError('Unsupported AWMS file')
    out = {'version': version, 'resident': resident}
    for i in range(count):
        tag, offset, rows, length = struct.unpack_from('>4sIII', raw, 16 + 16 * i)
        tag = tag.decode('ascii')
        if offset + length > len(raw):
            raise ValueError('AWMS section past the end: ' + tag)
        out[tag] = raw[offset:offset + length]
        out[tag + '_rows'] = rows
    return out


def strings(f):
    n = f['STRS_rows']
    blob = f['STRS'][4 * n:]
    out = []
    for i in range(n):
        o = struct.unpack_from('>I', f['STRS'], 4 * i)[0]
        out.append(blob[o:blob.index(b'\0', o)].decode('cp1252'))
    return out


def scripts(f):
    rows = []
    for i in range(f['SCRP_rows']):
        name, nl, depth, flags, _, off, length = struct.unpack_from('>HBBHHII', f['SCRP'], 16 * i)
        rows.append({'name': name, 'locals': nl, 'stack': depth, 'flags': flags,
                     'code': f['CODE'][off:off + length]})
    return rows


def decode(code):
    """[(offset, opcode name, [operands])] of one script's bytecode; raises ValueError on bad code."""
    out, i = [], 0
    while i < len(code):
        op = code[i]
        if op not in NAME:
            raise ValueError('bad opcode 0x%02x at %d' % (op, i))
        start = i
        i += 1
        args = []
        layout = LAYOUT[op]
        if layout in ('N', 'F'):
            # F (NOTYET): u16 the function's number first, then as N (MESSAGEBOX)
            number = struct.unpack_from('>H', code, i)[0] if layout == 'F' else None
            i += 2 if layout == 'F' else 0
            name, flags, nstr = struct.unpack_from('>HBB', code, i)
            i += 4
            strs = list(struct.unpack_from('>%dH' % nstr, code, i))
            i += 2 * nstr
            args = ([number] if layout == 'F' else []) + [name, flags, nstr] + strs
        else:
            for letter in layout:
                fmt = {'b': '>b', 'B': '>B', 'h': '>h', 'H': '>H', 'i': '>i', 'f': '>f'}[letter]
                args.append(struct.unpack_from(fmt, code, i)[0])
                i += struct.calcsize(fmt)
        out.append((start, NAME[op], args))
        if i > len(code):
            raise ValueError('operand past the end')
    return out


def disassemble(code, names=None):
    lines = []
    for at, name, args in decode(code):
        text = ' '.join(str(a) for a in args)
        if name == 'NOTYET' and names:
            text = '#%d %s flags=%#x strings=%s' % (args[0], names[args[1]], args[2], [names[s] for s in args[4:]])
        if name in ('JMP', 'JZ', 'JNEB', 'JCMPB'):
            size = {'JMP': 3, 'JZ': 3, 'JNEB': 4, 'JCMPB': 5}[name]
            text += ' -> %d' % (at + size + args[-1])
        lines.append('%5d %-13s %s' % (at, name, text))
    return '\n'.join(lines)
