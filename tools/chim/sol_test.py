# SPDX-License-Identifier: GPL-3.0-only
"""TEST BUILDS ONLY (tools/build.py --chim-sol-test, DLC-BUILD-LATER): the Bloodmoon layer's CHIM frames in the image.

The layer's CHIM world (run/chim-sol, tools/chim_build.py on the layered data folder) goes into the image as its own
store, id1/chimsol/ (world.cwi and its sector files, the same paths inside the store as the base world's id1/chim/),
and each of its frames gets a frame map sol<cell> (map_files.frame_map_path) whose worldspawn names that store ("_chim_world"
"chimsol": the engine selects the store from the map, chim_world.c Chim_StoreSelect) and closes its edges
("_chim_edge" "closed": the frame touches no Vvardenfell frame). The map is made the way a CHIM region frame map is
made from the game data (chim.frame_map._region_map_game_data: the open-world worldspawn, the player start on the
frame's own ground), so `dbg tp sol<cell>` (a map name) stands the player in it. Nothing of the base world changes:
the base store, its frame maps, the region directory and every base key stay as they are; the option is off by
default and an image without it is byte for byte the image before it."""
import json
import shutil
from pathlib import Path

STORE = 'chimsol'
EDGE_KEY = '_chim_edge'
STORE_KEY = '_chim_world'


def map_name(cell):
    """The frame map's name of a Solstheim frame at CELL: sol, then m/p and the number of each coordinate."""
    return 'sol' + ''.join(('m' if v < 0 else 'p') + str(abs(int(v))) for v in cell)


def install(world_dir, id1, hand_fields):
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
    for path in sorted(source.rglob('*')):
        if path.is_file():
            out = target / path.relative_to(source)
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, out)
            files += 1
            size += path.stat().st_size
    world = FM.load(world_dir)
    maps = []
    for frame in table['frames']:
        cell = tuple(frame['cell'])
        name = map_name(cell)
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
    print('[chim-sol] TEST: store %s (%d files, %d bytes) and %d Solstheim frame maps: %s' % (
        STORE, files, size, len(maps), ', '.join('%s (frame %s)' % (m['map'], m['id']) for m in maps)), flush=True)
    return {'store': STORE, 'files': files, 'bytes': size, 'maps': maps}
