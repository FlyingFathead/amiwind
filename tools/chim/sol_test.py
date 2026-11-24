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


# The lands whose frames are a store of their own with their own rows file (engine aw_maps.h AW_TerrainId and
# aw_world.c load_directory): the map name's two letters, how many frame maps the engine's ID range holds
# (Solstheim's 3,840, then Mournhold's 256, to the end of the outdoor block), the rows file, the land's name (the
# frame maps' message), the stage
# whose master names the land's regions, and whether every frame closes its own edges ('closed') or only a frame
# with no neighbour frame does ('alone': the cells of one Mournhold district touch, and the player walks across).
LANDS = {
    # 'module': what differs when the store is made by the build module bloodmoon-solstheim (its data stage's folder
    # is beside the world; land_of): the island's cells touch, so only a frame with no neighbour closes its edges, and
    # the frames carry their static flames as the base world's region frames do. Without that folder the store is the
    # test build's single frames (--chim-sol-test), as before.
    'chimsol': {'prefix': 'sl', 'limit': 3840, 'directory': 'world/regions-sl.awr', 'title': 'Solstheim',
                'data_stage': 'chim-sol-data', 'edges': 'closed', 'flames': False,
                'module': {'data_stage': 'bloodmoon-solstheim-data', 'edges': 'alone', 'flames': True}},
    'chimmh': {'prefix': 'mh', 'limit': 256, 'directory': 'world/regions-mh.awr', 'title': 'Mournhold',
               'data_stage': 'tribunal-mournhold-data', 'edges': 'alone', 'flames': True},
    # The recordless open sea of the area Bloodmoon adds to the map's box (tools/chim/sea_grid.py; the stage
    # bloodmoon-solstheim-sea, SOL-SEA-CROSSING-68): a store of its own so Solstheim's store index does not grow (its
    # densest forest frame had 90,544 bytes left at 32 MB, the sea's 440 frames would add about 320 KB). Its frame
    # maps continue Solstheim's slNNNN numbering ('after': the land whose rows come first) and its rows are appended
    # to the same rows file, so the engine reads them in its one table (aw_world.c load_directory); each map names
    # its own store. Open sea borders the islands or the edge of the map, so no frame closes its edges ('open').
    'chimsea': {'prefix': 'sl', 'limit': 3840, 'directory': 'world/regions-sl.awr', 'title': 'Solstheim',
                'data_stage': 'bloodmoon-solstheim-data', 'edges': 'open', 'flames': False, 'after': 'chimsol'},
}


def land_of(store, world_dir=None):
    """The land of STORE as LANDS gives it, with its 'module' values in place when the module's data stage folder is
    beside WORLD_DIR (run/<data stage>): one store name, the test build's frames or the build module's. None for a
    store that is no land."""
    land = LANDS.get(store)
    if land is None:
        return None
    module = land.get('module')
    if module and world_dir is not None and (Path(world_dir).parent / module['data_stage']).is_dir():
        land = dict(land, **module)
    return {key: value for key, value in land.items() if key != 'module'}


def map_name(index, prefix='sl', limit=3840):
    """The frame map's name of the INDEX-th frame of a land (the ownership table's order): the land's two letters
    (sl: Solstheim, mh: Mournhold) and four digits, the open-world map form the engine knows (aw_maps.h
    AW_TerrainId: terrain IDs from AW_SOLSTHEIM_TERRAIN_BASE and AW_MOURNHOLD_TERRAIN_BASE)."""
    if not 0 <= index < limit:
        raise ValueError('frame index %r out of range for the %sNNNN frame maps (%d)' % (index, prefix, limit))
    return '%s%04d' % (prefix, index)


def directory_rows(frames, prefix='sl', limit=3840, before=b''):
    """world/regions-sl.awr (Mournhold: world/regions-mh.awr, PREFIX mh): 'AWS1', u32 rows, then per frame (in order)
    the 52-byte row the engine reads: its name (slNNNN, NUL padded to 8), origin (3 f32, map units), core (4 f32: x0
    y0 x1 y1, frame-local) and cover (the core COVER units wider), little-endian. BEFORE: a rows file already written
    for the land whose rows come first (LANDS 'after'): its rows are kept and these follow, numbered on."""
    start = rows_count(before) if before else 0
    out = [b'AWS1' + struct.pack('<I', start + len(frames)), before[8:]]
    for i, frame in enumerate(frames):
        (x0, y0), (x1, y1) = frame['core']
        core = (x0, y0, x1, y1)
        cover = (x0 - COVER, y0 - COVER, x1 + COVER, y1 + COVER)
        out.append(map_name(start + i, prefix, limit).encode('ascii').ljust(8, b'\0') +
                   struct.pack('<3f4f4f', *[float(v) for v in frame['origin']], *core, *cover))
    return b''.join(out)


def rows_count(raw):
    """The row count of a rows file ('AWS1', u32 rows, 52 bytes a row); a ValueError when it is not one."""
    count = struct.unpack_from('<I', raw, 4)[0] if raw[:4] == b'AWS1' and len(raw) >= 8 else -1
    if count < 0 or len(raw) != 8 + 52 * count:
        raise ValueError('not a rows file the engine reads (AWS1, 52 bytes a row)')
    return count


def closed_frames(frames, edges):
    """The cells of FRAMES whose frame map closes its edges: all of them ('closed'), or those with no frame in a
    cell beside them ('alone')."""
    cells = {tuple(f['cell']) for f in frames}
    if edges == 'closed':
        return cells
    if edges == 'open':
        return set()
    return {(x, y) for x, y in cells
            if not {(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)} & cells}


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


def presented_master(world_dir, store):
    """The master the land's data stage wrote beside WORLD_DIR (the presented game data of the store's own masters:
    there the land's cells are exterior cells), or None when STORE is no land or the stage wrote none. The one place
    that names that file for the image step (the region names below, the frames' actors:
    tools/build_aga.py layer_actor_inputs)."""
    land = land_of(store, world_dir)
    if land is None:
        return None
    path = Path(world_dir).parent / land['data_stage'] / 'Morrowind.esm'
    return path if path.is_file() else None


def install(world_dir, id1, hand_fields, alternatives=(), store=STORE, actors=None):
    """Copy the layer's store into ID1/<STORE> (chimsol) and write one frame map per frame of WORLD_DIR's ownership
    table. Also the image's layer stores (tools/chim/layer_stores.py, Bloodmoon). Returns the record:
    {'store', 'files', 'bytes', 'maps': [{'map', 'frame', 'cell', 'bytes', 'sha256', ...}]}.
    ACTORS: the frames' actor inputs (chim.frame_map.region_actor_tasks: the census of the land's own presented
    master by cell, the actor library's base texts and models, the start scripts' held references), or None: with
    them each frame map carries its cells' NPCs and creatures, fitted on the frame's own collision as the open
    world's region frames' are (DISTRICT-PEOPLE-NOT-PLACED-67); each map's record then holds 'actors'."""
    STORE = store  # noqa: N806 (the module default, or the layer plan's store name)
    land = land_of(store, world_dir) or land_of('chimsol', world_dir)
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
        # alternative models for aw_tree_crowns (tools/chim/alt_models.py): one method (the star crowns) or several
        # (the rally-game trees' methods, SOLSTHEIM-TREES-THREE-LOD-68)
        from chim.alt_models import merge, merge_many
        if len(alternatives) == 1:
            method, alt_dir = alternatives[0]
            alt_records.append(merge(source, Path(alt_dir) / 'chim', target, int(method)))
        else:
            alt_records += merge_many(source, [(int(m), Path(d) / 'chim') for m, d in alternatives], target)
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
    closed = closed_frames(table['frames'], land['edges'])
    # a land whose rows follow another's in the same rows file (LANDS 'after'): its maps are numbered on from the rows
    # already there (the other land's store installed first: layer_stores.install in the image's order)
    rows_path = id1 / land['directory']
    before = rows_path.read_bytes() if land.get('after') and rows_path.is_file() else b''
    offset = rows_count(before) if before else 0
    for index, frame in enumerate(table['frames']):
        cell = tuple(frame['cell'])
        name = map_name(offset + index, land['prefix'], land['limit'])
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
        worldspawn = dict(FM.open_world_worldspawn(hand_fields), message=land['title'])
        worldspawn[STORE_KEY] = STORE
        if cell in closed:
            worldspawn[EDGE_KEY] = 'closed'
        task = {'id1': str(id1), 'frame': frame, 'name': name, 'origin': list(frame['origin']),
                'placed': sorted(FM.chim_placements(world_dir, cell, world=world)),
                'bounds': [list(lo), list(hi)], 'grid': json.loads(json.dumps(grid)), 'stream': FM.stream_enabled(),
                'rows': 'game-data', 'aliases': [], 'worldspawn': worldspawn,
                'start_z': ground + FM.START_HEIGHT - frame['origin'][2]}
        if land['flames']:
            # Mournhold's districts: the frame's static flames, as a base region frame map carries them
            # (chim.frame_map.region_task, CHIM-EXTERIOR-FLAMES-MISSING-48)
            from chim.flames import world_frame_rows
            task['flame_rows'], task['flames'] = world_frame_rows(world, world_dir, cell)
        data, report = FM._region_map_game_data(task)
        if actors is not None:
            planned = FM.region_actor_tasks([task], world, actors)[0]
            if planned.get('actors'):
                data, report = FM.region_actor_map(planned, data, report)
            elif planned.get('actor_record'):
                report = dict(report, actors=planned['actor_record'])
        from map_files import frame_map_path
        path = frame_map_path(id1, name)
        if path.exists():
            raise ValueError('--chim-sol-test: frame map %s already present' % path.name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        maps.append(dict(report, cell=list(cell), store=STORE, tp='dbg tp ' + name, file=path.name,
                         edge='closed' if cell in closed else 'open'))
    # the frames over or near the 16 MB budget (the world's own heap gate, its receipt's 'fast_ram_32mb'): their
    # frame maps carry the 32 MB mark, as the base world's do (CHIM-FRAME-16MB-REFUSAL-48)
    receipt_path = world_dir / 'chim-receipt.json'
    fast = ((json.loads(receipt_path.read_text(encoding='utf-8')).get('fast_ram_32mb') or {}).get('frame_records')
            if receipt_path.is_file() else None) or []
    if fast:
        from chim.heap import SAFE_FAST_MB, frame_cells, mark_frame_maps
        marked = set(mark_frame_maps(id1, frame_cells(fast), maps=[m['file'] for m in maps]))
        for m in maps:
            if Path(m['file']).stem in marked:
                m['fast_mb'] = SAFE_FAST_MB
    # the land's rows of the region table, and the region names of its cells (the layer's REGN and CELL rows, read
    # from the master the land's data stage wrote next to WORLD_DIR)
    (id1 / land['directory']).parent.mkdir(parents=True, exist_ok=True)
    (id1 / land['directory']).write_bytes(directory_rows(table['frames'], land['prefix'], land['limit'], before))
    layered = world_dir.parent / land['data_stage'] / 'Morrowind.esm'
    names_path = id1 / REGION_NAMES
    # a land that follows another (the recordless sea) has no region or place of its own: the names are the other's
    if layered.is_file() and names_path.is_file() and not land.get('after'):
        from prepare_world_ui import region_names
        names_path.write_bytes(merged_region_names(names_path.read_bytes(), region_names(layered.read_bytes())))
    print('[chim-layer] store %s (%d files, %d bytes) and %d %s frame maps: %s' % (
        STORE, files, size, len(maps), land['title'],
        ', '.join('%s (frame %s)' % (m['map'], m['id']) for m in maps)), flush=True)
    return {'store': STORE, 'files': files, 'bytes': size, 'maps': maps, 'alternatives': alt_records}
