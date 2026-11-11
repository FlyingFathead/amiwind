# SPDX-License-Identifier: GPL-3.0-only
"""TEST BUILDS ONLY (tools/build.py --chim-sol-test, DLC-BUILD-LATER): the Bloodmoon layer's CHIM frames in the image.

The layer's CHIM world (run/chim-sol, tools/chim_build.py on the layered data folder) goes into the image as its own
store, id1/chimsol/ (world.cwi and its sector files, the same paths inside the store as the base world's id1/chim/),
and each of its frames gets a frame map slNNNN (map_files.frame_map_path; the open-world map form of the engine,
aw_maps.h AW_TerrainId) whose worldspawn names that store ("_chim_world" "chimsol": the engine selects the store from
the map, chim_world.c Chim_StoreSelect) and closes its edges ("_chim_edge" "closed"). The map is made the way a CHIM
region frame map is made from the game data (chim.frame_map._region_map_game_data: the open-world worldspawn, the
player start on the frame's own ground). Each frame also gets its row in the open-world region table
(world/regions-sl.awr, after Vvardenfell's rows in the engine's one table: dbg tp X Y and camera marks find a
Solstheim point by its coordinates), and the cells their region names (world/region-names.awn with Bloodmoon's
regions added after the base ones: the HUD reads "Solstheim / <region>"). Nothing of the base world changes:
the base store, its frame maps, the region directory and every base key stay as they are; the option is off by
default and an image without it is byte for byte the image before it."""
import json
import shutil
from pathlib import Path

STORE = 'chimsol'
EDGE_KEY = '_chim_edge'
STORE_KEY = '_chim_world'


import struct

DIRECTORY = 'world/regions-sl.awr'      # the Solstheim rows of the open-world region table (engine aw_world.c)
REGION_NAMES = 'world/region-names.awn'  # per-cell region and place names (tools/prepare_world_ui.py region_names)
COVER = 896                              # a row's cover reaches this far past its core (aw_world.c read_row)


def map_name(index):
    """The frame map's name of the INDEX-th Solstheim frame (the ownership table's order): sl and four digits, the
    open-world map form the engine knows (aw_maps.h AW_TerrainId: terrain IDs from AW_SOLSTHEIM_TERRAIN_BASE)."""
    if not 0 <= index < 4096:
        raise ValueError('--chim-sol-test: Solstheim frame index %r out of range' % index)
    return 'sl%04d' % index


def directory_rows(frames):
    """world/regions-sl.awr: 'AWS1', u32 rows, then per frame (in order) the 52-byte row the engine reads: its name
    (slNNNN, NUL padded to 8), origin (3 f32, map units), core (4 f32: x0 y0 x1 y1, frame-local) and cover (the core
    COVER units wider), little-endian."""
    out = [b'AWS1' + struct.pack('<I', len(frames))]
    for i, frame in enumerate(frames):
        (x0, y0), (x1, y1) = frame['core']
        core = (x0, y0, x1, y1)
        cover = (x0 - COVER, y0 - COVER, x1 + COVER, y1 + COVER)
        out.append(map_name(i).encode('ascii').ljust(8, b'\0') +
                   struct.pack('<3f4f4f', *[float(v) for v in frame['origin']], *core, *cover))
    return b''.join(out)


def read_region_names(raw):
    """(names, places, {(x, y): (name index, place index)}) of an ARN2 file (prepare_world_ui.region_names)."""
    if raw[:4] != b'ARN2':
        raise ValueError('--chim-sol-test: %s is not ARN2' % REGION_NAMES)
    n, p, c = struct.unpack_from('<III', raw, 4)
    at = 16
    names = [raw[at + 64 * i:at + 64 * (i + 1)].rstrip(b'\0') for i in range(n)]
    at += 64 * n
    places = [raw[at + 64 * i:at + 64 * (i + 1)].rstrip(b'\0') for i in range(p)]
    at += 64 * p
    cells = {}
    for i in range(c):
        x, y, r, q = struct.unpack_from('<iiII', raw, at + 16 * i)
        cells[x, y] = (r, q)
    return names, places, cells


def merged_region_names(base_raw, layer_raw):
    """The base region-names file with the layer's regions, places and cells added: every base name keeps its index
    (the weather table, region-weather.aww, is indexed by it), new names follow; a cell the base names keeps its
    row. LAYER_RAW: the same file made from the layered master (Morrowind.esm + Bloodmoon.esm)."""
    names, places, cells = read_region_names(base_raw)
    lnames, lplaces, lcells = read_region_names(layer_raw)
    from prepare_world_ui import NO_NAME

    def index_of(table, value):
        if value not in table:
            table.append(value)
        return table.index(value)
    for xy, (r, q) in sorted(lcells.items()):
        if xy in cells:
            continue
        cells[xy] = (index_of(names, lnames[r]) if r != NO_NAME else NO_NAME,
                     index_of(places, lplaces[q]) if q != NO_NAME else NO_NAME)
    return (b'ARN2' + struct.pack('<III', len(names), len(places), len(cells))
            + b''.join(n.ljust(64, b'\0') for n in names) + b''.join(p.ljust(64, b'\0') for p in places)
            + b''.join(struct.pack('<iiII', x, y, *cells[x, y]) for x, y in sorted(cells)))


def install(world_dir, id1, hand_fields, alternatives=()):
    """Copy the layer's store into ID1/chimsol and write one frame map per frame of WORLD_DIR's ownership table.
    Returns the record: {'store', 'files', 'bytes', 'maps': [{'map', 'frame', 'cell', 'bytes', 'sha256', ...}]}."""
    from chim import frame_map as FM
    from chim.regions import TABLE_FILE, read_table
    world_dir, id1 = Path(world_dir), Path(id1)
    table = read_table(world_dir / TABLE_FILE)
    if not table or not table.get('frames'):
        raise ValueError('--chim-sol-test: %s holds no CHIM region frames' % world_dir)
    source = world_dir / 'chim'
    if not (source / 'world.cwi').is_file():
        raise ValueError('--chim-sol-test: no CHIM world in %s' % source)
    target = id1 / STORE
    if target.exists():
        raise ValueError('--chim-sol-test: %s already exists' % target)
    files = 0
    size = 0
    alt_records = []
    if alternatives:
        # ALTERNATIVES: [(method value, the other build's world folder)]: one store, the original trees plus their
        # alternative models for aw_tree_crowns (tools/chim/alt_models.py); only one method per store for now
        if len(alternatives) != 1:
            raise ValueError('--chim-sol-test: one alternative tree method per store')
        from chim.alt_models import merge
        method, alt_dir = alternatives[0]
        alt_records.append(merge(source, Path(alt_dir) / 'chim', target, int(method)))
    else:
        for path in sorted(source.rglob('*')):
            if path.is_file():
                out = target / path.relative_to(source)
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, out)
    for path in sorted(target.rglob('*')):
        if path.is_file():
            files += 1
            size += path.stat().st_size
    world = FM.load(world_dir)
    maps = []
    for index, frame in enumerate(table['frames']):
        cell = tuple(frame['cell'])
        name = map_name(index)
        _, record, chunks = (FM.frames_at(world['frames'], cell) or [(0, next(
            f for f in world['frames'] if tuple(f[1]['cell']) == cell))])[0][1]
        g, (lx, ly) = record['grain'], record['low']
        lo = (lx, ly, min(c['zmin'] for c in chunks) - FM.FLOOR_MARGIN)
        hi = (lx + record['nx'] * g, ly + record['ny'] * g, FM.frame_top(chunks))
        grid = ([{'cx': c['cx'], 'cy': c['cy'], 'index': c['index']} for c in chunks], tuple(record['low']), g,
                record['nx'], record['ny'])
        ground = FM.frame_ground(world, cell)
        if ground is None:
            raise ValueError('--chim-sol-test: frame %s has no ground under its centre for the player start'
                             % frame['id'])
        worldspawn = dict(FM.open_world_worldspawn(hand_fields), message='Solstheim')
        worldspawn[STORE_KEY] = STORE
        worldspawn[EDGE_KEY] = 'closed'
        task = {'id1': str(id1), 'frame': frame, 'name': name, 'origin': list(frame['origin']),
                'placed': sorted(FM.chim_placements(world_dir, cell, world=world)),
                'bounds': [list(lo), list(hi)], 'grid': json.loads(json.dumps(grid)), 'stream': FM.stream_enabled(),
                'rows': 'game-data', 'aliases': [], 'worldspawn': worldspawn,
                'start_z': ground + FM.START_HEIGHT - frame['origin'][2]}
        data, report = FM._region_map_game_data(task)
        from map_files import frame_map_path
        path = frame_map_path(id1, name)
        if path.exists():
            raise ValueError('--chim-sol-test: frame map %s already present' % path.name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        maps.append(dict(report, cell=list(cell), store=STORE, tp='dbg tp ' + name))
    # the Solstheim rows of the region table, and the region names of its cells (Bloodmoon.esm's REGN and CELL rows,
    # read from the layered master the chim-sol-data stage wrote next to WORLD_DIR)
    (id1 / DIRECTORY).parent.mkdir(parents=True, exist_ok=True)
    (id1 / DIRECTORY).write_bytes(directory_rows(table['frames']))
    layered = world_dir.parent / 'chim-sol-data' / 'Morrowind.esm'
    names_path = id1 / REGION_NAMES
    if layered.is_file() and names_path.is_file():
        from prepare_world_ui import region_names
        names_path.write_bytes(merged_region_names(names_path.read_bytes(), region_names(layered.read_bytes())))
    print('[chim-sol] TEST: store %s (%d files, %d bytes) and %d Solstheim frame maps: %s' % (
        STORE, files, size, len(maps), ', '.join('%s (frame %s)' % (m['map'], m['id']) for m in maps)), flush=True)
    return {'store': STORE, 'files': files, 'bytes': size, 'maps': maps, 'alternatives': alt_records}
