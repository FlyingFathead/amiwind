# SPDX-License-Identifier: GPL-3.0-only
"""The one map path helper of the builder and every tool that reads, writes, packs or lists maps.

A map is maps/<name>.bsp, or maps/<name>.chim for a CHIM frame map. A frame map is a BSP29 file (the
engine's model loader dispatches on the file header, not the extension) but not a playable map without
its CHIM world: an empty world, the map's entities, collision-only boxes and the worldspawn key
"_chim_frame" "X Y"; its geometry lives in id1/chim/ (docs/chim/WORLD_FORMAT.md). The engine resolves a
map name the same way (engine/aga/src/aw_mappath.c, AW_MapPath): maps/<name>.chim when the image has a
CHIM world and the file exists, else maps/<name>.bsp. Region frames keep their cell names
(vf1637.chim beside vf1638.bsp), so the region directory, hand-over, saves and the HUD keep working.

Frame maps are identified by their worldspawn key (is_chim_frame) and the build's ownership table
(aw-chim-ownership-1, tools/chim/regions.py), never by file name.

The extension frame maps are written with is a build setting, chim_frame_ext (default "chim";
"bsp" keeps the earlier form: DON'T DELETE ANY METHOD), resolved once by tools/build.py and exported
as AMIWIND_CHIM_FRAME_EXT, which worker processes inherit.

Kept free of numpy/scipy so the builder can import it before any converter.
"""
import os
import re
from pathlib import Path

LEGACY_EXT = '.bsp'
FRAME_EXT = '.chim'
MAP_EXTS = (FRAME_EXT, LEGACY_EXT)          # resolution order: a frame map first, as the engine
FRAME_KEY = '_chim_frame'
ROOM_KEY = '_chim_room'                        # a CHIM room map's worldspawn key (tools/chim/interior.py room_map)
STREAM_CHUNK_KEY = '_chim_chunk'               # chim/frame_map.py CHUNK_KEY
STREAMED_CLASSES = ('aw_static', 'aw_flora')   # chim/frame_map.py STREAMED_CLASSES


def is_streamed_static(row, frame_map):
    """A frame map's static the engine streams with its chunk (chim/chim_statics.c): captured at load, kept in the
    CHIM list (CHIM_MAX_STATICS), never a Quake static (no cl_static_entities slot, no signon message, its model
    in the zone, not the Hunk). The one reading for every tool that counts statics."""
    return bool(frame_map) and row.get('classname') in STREAMED_CLASSES and STREAM_CHUNK_KEY in row
FRAME_EXT_VARIABLE = 'AMIWIND_CHIM_FRAME_EXT'
FRAME_EXT_CHOICES = ('chim', 'bsp')
DEFAULT_FRAME_EXT = 'chim'
_ENTITY = re.compile(rb'\{([^{}]*)\}')


def frame_ext(value=None):
    """The extension frame maps are written with: '.chim' (default) or '.bsp' (the earlier form).
    An explicit VALUE wins over the environment."""
    if value is None:
        value = os.environ.get(FRAME_EXT_VARIABLE, DEFAULT_FRAME_EXT).strip() or DEFAULT_FRAME_EXT
    value = value.lstrip('.')
    if value not in FRAME_EXT_CHOICES:
        raise ValueError(FRAME_EXT_VARIABLE + ' must be chim or bsp')
    return '.' + value


def export_frame_ext(value):
    """Export the resolved chim_frame_ext for every converter worker and the image step."""
    os.environ[FRAME_EXT_VARIABLE] = frame_ext(value)[1:]
    return os.environ[FRAME_EXT_VARIABLE]


def is_map_name(name):
    """True for a file name of a map (x.bsp or x.chim)."""
    return str(name).lower().endswith(MAP_EXTS)


def map_stem(name):
    """'maps/vf0001.chim' / 'vf0001.bsp' / 'vf0001' -> 'vf0001' (the map name the engine and saves use)."""
    base = str(name).replace('\\', '/').rsplit('/', 1)[-1]
    for ext in MAP_EXTS:
        if base.lower().endswith(ext):
            return base[:-len(ext)]
    return base


def map_file(maps_dir, name):
    """The file of map NAME in MAPS_DIR as the engine resolves it: <name>.chim when it exists, else
    <name>.bsp (returned even when absent, so callers report the usual missing map)."""
    maps_dir = Path(maps_dir)
    chim = maps_dir / (name + FRAME_EXT)
    return chim if chim.is_file() else maps_dir / (name + LEGACY_EXT)


def map_rel(id1, name):
    """id1-relative path ('maps/<name>.chim' or 'maps/<name>.bsp') of map NAME, resolved as map_file."""
    return 'maps/' + map_file(Path(id1) / 'maps', name).name


def frame_map_path(id1, name, ext=None):
    """Where a frame map named NAME is written: id1/maps/<name> + frame_ext()."""
    return Path(id1) / 'maps' / (name + frame_ext(ext))


def map_files(maps_dir, pattern='*'):
    """Every map file (x.bsp and x.chim) in MAPS_DIR whose stem matches PATTERN (fnmatch), sorted by name."""
    maps_dir = Path(maps_dir)
    if not maps_dir.is_dir():
        return []
    found = [p for ext in MAP_EXTS for p in maps_dir.glob(pattern + ext) if p.is_file()]
    return sorted(found, key=lambda p: p.name)


def worldspawn(data):
    """The worldspawn (first entity) of a BSP29 file's entity lump as {key: value}, or {}."""
    if len(data) < 12 or int.from_bytes(data[:4], 'little') != 29:
        return {}
    offset, size = int.from_bytes(data[4:8], 'little'), int.from_bytes(data[8:12], 'little')
    if offset < 0 or size <= 0 or offset + size > len(data):
        return {}
    match = _ENTITY.search(data[offset:offset + size])
    if not match:
        return {}
    text = match.group(1).decode('latin-1')
    return dict(re.findall(r'"([^"]*)"\s+"([^"]*)"', text))


def head_bytes(path):
    """The bytes of a BSP29 file up to the end of its entity lump (the header and the lump only: cheap on a
    folder of thousands of maps); b'' when the file is missing or not BSP29."""
    path = Path(path)
    try:
        with open(path, 'rb') as f:
            head = f.read(12)
            if len(head) < 12 or int.from_bytes(head[:4], 'little') != 29:
                return b''
            offset, size = int.from_bytes(head[4:8], 'little'), int.from_bytes(head[8:12], 'little')
            if offset < 12 or size <= 0 or size > (1 << 24):
                return b''
            f.seek(offset)
            lump = f.read(size)
    except OSError:
        return b''
    if len(lump) != size:
        return b''
    # the lump moved to offset 12 of a header that says so (worldspawn reads it from there)
    return (29).to_bytes(4, 'little') + (12).to_bytes(4, 'little') + size.to_bytes(4, 'little') + lump


def is_chim_frame(data):
    """True for a CHIM frame map: a BSP29 file whose worldspawn names a CHIM frame ("_chim_frame").
    DATA: the file's bytes or a path (only its header and entity lump are read)."""
    if isinstance(data, (str, Path)):
        data = head_bytes(data)
    return FRAME_KEY in worldspawn(data)


def is_chim_room(data):
    """True for a CHIM room map: a BSP29 file whose worldspawn names a CHIM room ("_chim_room"); its models are on the
    interior store, so the map optimizer leaves it as written. DATA: the file's bytes or a path."""
    if isinstance(data, (str, Path)):
        data = head_bytes(data)
    return ROOM_KEY in worldspawn(data)


def room_maps(maps_dir):
    """Every CHIM room map in MAPS_DIR (by its key, whatever its extension), sorted by file name."""
    return [p for p in map_files(maps_dir) if is_chim_room(p)]


def scene_maps(maps_dir):
    """The maps a per-map image check reads as a whole scene, sorted by file name: every x.bsp (as before) and every
    CHIM room map (maps/<room>.chim: its entities in the map, its placed meshes in its room record, room_record).
    A CHIM frame map (.chim) is checked through its CHIM world instead (IMAGE-ROOM-MAPS-LATE-PASSES-48: the checks
    after the CHIM rooms install selected maps as x.bsp and skipped every CHIM room)."""
    return [p for p in map_files(maps_dir) if p.name.lower().endswith(LEGACY_EXT) or is_chim_room(p)]


def room_record(data):
    """(store folder, room) a CHIM room map names ("_chim_world", "_chim_room"), or None. DATA: bytes or a path."""
    if isinstance(data, (str, Path)):
        data = head_bytes(data)
    world = worldspawn(data)
    if ROOM_KEY not in world:
        return None
    return world.get('_chim_world') or 'chim', world[ROOM_KEY]


def room_record_path(id1, data):
    """id1/<store>/rooms/<room>.crm of a CHIM room map (room_record), or None for any other map."""
    found = room_record(data)
    return None if found is None else Path(id1) / found[0] / 'rooms' / (found[1] + '.crm')


def frame_maps(maps_dir):
    """Every CHIM frame map in MAPS_DIR (by its key, whatever its extension), sorted by file name."""
    return [p for p in map_files(maps_dir) if is_chim_frame(p)]


def frame_cell(data):
    """(x, y) of a frame map's "_chim_frame", or None. DATA: the file's bytes or a path."""
    if isinstance(data, (str, Path)):
        data = head_bytes(data)
    value = worldspawn(data).get(FRAME_KEY)
    if not value:
        return None
    try:
        x, y = (int(v) for v in value.split())
    except ValueError:
        return None
    return x, y


def owned_frames(chim_world):
    """{(x, y): frame id} of the CHIM region frames in a CHIM world's ownership table (aw-chim-ownership-1,
    chim-regions.json); {} without one. A region frame map is the map whose "_chim_frame" names one of
    these cells (frame_cell), whatever its file is called."""
    if not chim_world:
        return {}
    from chim.regions import TABLE_FILE, read_table
    table = read_table(Path(chim_world) / TABLE_FILE)
    return {tuple(frame['cell']): frame['id'] for frame in (table or {}).get('frames', [])}


def region_frame_maps(maps_dir, chim_world):
    """{map file name: frame id} of the region frame maps in MAPS_DIR: frame maps (by their key) whose
    frame is owned by a region frame of the CHIM world's ownership table."""
    owned = owned_frames(chim_world)
    out = {}
    for path in map_files(maps_dir) if owned else []:
        cell = frame_cell(path)
        if cell in owned:
            out[path.name] = owned[cell]
    return out
