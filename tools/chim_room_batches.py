#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Interior rooms by batch (builder stage chim-room-batches; docs/chim/DOOR_GRAPH.md "Rooms by batch in the builder").

Converts the rooms of the batches --batches selects from the repo's room list (config/room-batches.json,
tools/room_batches.py) as CHIM rooms, one unit per room on the shared worker pool, largest first:

  room unit     what a CHIM room needs of today's room conversion and nothing more (no qbsp, vis or light of the
                visual world: the CHIM interiors stage makes the room's models from its scenery export): the room's
                scenery export (the placements, profiles and meshes the room converter keeps, prepare_area.build_room's
                selection), its kept placements (placements.json), its plant sprites, and its room map entities
                (worldspawn, start, plant sprites) in a shell map: an empty world with the room's bounds. Keyed by
                the unit cache (interior-room-chim: the room, the game data, the code, the palette and colormap):
                a room converted once is never converted again while its inputs are unchanged.
  residents     every room's placed NPCs and creatures, as the town rooms place them (prepare_area.populate); residents
                whose model set or greeting is the same file for file share one copy (tools/resident_share.py,
                --resident-files shared, the default; per-resident keeps every copy, the previous method)
  room banks    OUT/id1/doors-<room>.txt: every load door of the room, its box from the door's mesh, every target "-":
                the image links them (room_batches.link_banks) once it knows which rooms and frames it holds

A room another stage of the plan converts (--held-by STAGE: interior, balmora-interiors, chim-rooms-TOWN, town-TOWN)
is left to it and listed (never converted twice). A room with water or lava carries them (v0.0.48, the maintainer's
decision of 23 October 2026): its unit writes the water brush and the lava pool brushes into room.map, their textures
into the shell's texture lump and the pools' loop sounds into its own id1/sound, as the room converter makes them
(prepare_area.build_room), and the CHIM interiors stage makes the liquids from them (chim.interior.room_liquids). A
room the CHIM interiors stage still cannot take (lava at or under the water) keeps its room map there, named.

    python3 tools/chim_room_batches.py --batches 1-3 --data-files DATA --scene RUN/intro-scene --out OUT
        [--held-by STAGE ...] [--ffmpeg F] [--jobs N]

OUT/scene/area-work/<room>/ is what the chim-interiors stage reads (--rooms-from); OUT/id1 is what the image installs
(--chim-room-batches); OUT/room-batches.json is the record. Nothing derived from your files is part of this repository.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
# src first, always (as tools/chim_rooms.py): tools/mwad.py would shadow the mwad package when the builder's PYTHONPATH
# (src:tools) leaves the script's own folder ahead of src (DOOR-GRAPH-MWAD-SHADOW-48)
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

from room_batches import RECORD, STAGE_FORMAT  # noqa: E402

UNIT = 'interior-room-chim'
SHELL_KEY = '_chim_room_shell'   # worldspawn key of a shell room map (chim.interior.room_map: placements from the record)
EDGE = 32.0                      # the shell's bounds stand this far outside the placements (prepare_area.build_room's box)
SPAWN_LIFT = 16.875              # town_interiors.FEET


def _log(msg):
    print('[room batches] ' + msg, flush=True)


def entity_text(fields):
    from prepare_npcs import quote
    return '{\n' + '\n'.join(quote(k) + ' ' + quote(str(v)) for k, v in fields.items()) + '\n}'


def shell_map(lo, hi, entities, textures=()):
    """A BSP29 room map with no faces (chim.frame_map.empty_world) whose entity lump is ENTITIES: what every image pass
    on room maps reads (worldspawn, residents, hands, cell numbers) until the CHIM rooms install makes its .chim.
    TEXTURES: miptex blobs its texture lump holds (a room with water or lava: "*water", "*lava", the lava bed; the
    CHIM room map takes its liquid textures from here, chim.interior.miptex_named)."""
    from chim import format as F
    from chim.frame_map import empty_world
    lumps = empty_world([math.floor(v) for v in lo], [math.ceil(v) for v in hi])
    lumps[0] = ('\n'.join(entities) + '\n\0').encode('cp1252')
    if textures:
        head = struct.pack('<i', len(textures))
        offsets, at = [], 4 + 4 * len(textures)
        for blob in textures:
            offsets.append(at)
            at += len(blob)
        lumps[2] = head + struct.pack('<%di' % len(textures), *offsets) + b''.join(textures)
    return F.brush_image(lumps)[0]


def water_plane(water, low, high):
    """(water height or None, room box top, note or None) of a room whose cell has WATER (Morrowind units) and whose
    box spans LOW..HIGH (Quake units, EDGE outside its placements). Water under everything the room places: nothing
    stands in it or sees it (the game's plane is there, out of reach), so no plane, named. Water over everything: the
    whole room is under water, the box grows to hold the plane. ROOM-BATCH-WATER-OUTSIDE-48 (two rooms were refused
    with "water outside the room bounds")."""
    if water is None:
        return None, high, None
    level = water * 0.25
    if level <= low + 8:
        return None, high, ('water height %.1f under every placement of the room (lowest %.1f): no water plane'
                            % (level, low + EDGE))
    if level >= high - 8:
        return water, level + EDGE, 'water height %.1f over every placement of the room: the room is under water' % level
    return water, high, None


def build_shell(task, jobs=1):
    """One room unit (worker): the room's scenery export, kept placements, plant sprites and shell map into
    ROOT/area-work/<map>/. Returns (report, cell). Raises ValueError naming the room on anything it cannot convert.
    JOBS: the scenery geometry workers of its export (more than one only in the stage's tail, convert; the export's
    models come back in order, so the files are the same bytes whatever the count)."""
    data, scene, entry, timings, cell = task
    import numpy as np
    import interior_plants
    from interior_lighting import cell_lighting
    from mwad.audit import BSA
    from mwad.interior import select_geometry
    from mwad.paths import child_ci
    from prepare_area import interior_visual_profile, spawn_entrance
    from prepare_scenery import export_refs
    slug = entry['map']
    if entry.get('recentre'):
        from town_interiors import recentre_cell
        cell = recentre_cell(cell, entry['recentre'])
    root = Path(scene) / 'area-work' / slug
    root.mkdir(parents=True, exist_ok=False)
    refs, omitted = select_geometry(cell)
    if not refs:
        raise ValueError('%s (%s): no placement to convert' % (slug, cell['name']))
    profiles = {}
    for ref in refs:
        model = 'meshes/' + ref['model'].replace('\\', '/').lower()
        profile = interior_visual_profile(model, 'balmora')      # the town rooms' policy (town_interiors.convert)
        if profile is not None:
            profiles[model] = profile
    # Plants as sprites, the room converter's rule (prepare_area.build_room, retain_selected rooms)
    sprite_numbers, plant_rows, tree_numbers, tree_solid = [], [], [], []
    if interior_plants.room_wants_sprites(entry):
        from prepare_scenery import bsa_read, nif_reader
        from prepare_tree_sprites import collision_metadata
        from world_flora import flora_kind
        bsa = BSA(child_ci(data, 'Morrowind.bsa'))
        reader, collisions = nif_reader(), {}

        def collision_of(model):
            if model not in collisions:
                collisions[model] = collision_metadata(bsa_read(bsa, 'meshes/' + model), reader, flora_kind(model))
            return collisions[model]
        sprite_numbers, plant_rows = interior_plants.candidates(refs, collision_of)
        if interior_plants.trees_too() or entry.get('tree_sprites'):
            tree_numbers, tree_solid, tree_rows = interior_plants.tree_candidates(refs, collision_of)
            plant_rows = plant_rows + tree_rows
        for model in tree_solid:
            profiles[model] = {**profiles.get(model, {}), 'collision_only': True}
    groups = {slug: {'references': [r['number'] for r in refs], 'visual_profiles': profiles}}
    refs = [dict(r, scene_groups=[slug]) for r in refs]
    lighting = cell_lighting(cell)
    # Water and lava, as the room converter makes them (prepare_area.build_room): the pools from the game data
    # (tools/lava.py, --lava quake) with their glow lights, the water plane at the cell's water height. The CHIM
    # interiors stage makes the room's liquids from the room.map brushes and the shell's own textures
    # (chim.interior.room_liquids, liquid_world)
    import lava as lava_rules
    from mwad.paths import child_ci
    lava_mode = lava_rules.lava_mode()
    pools = (lava_rules.pools_of(data, cell['refs'], lava_rules.molten_objects_of(child_ci(data, 'Morrowind.esm')))
             if lava_mode == 'quake' else [])
    if pools:
        lighting = {**lighting, 'lights': list(lighting.get('lights', [])) +
                    [light for p in pools for light in lava_rules.glow_lights(p['hull'], p['top'])]}
    parts = root / 'source'
    export_refs(data, parts, refs, groups, [0, 0, 0], 8192, 128, {'cell': cell['name'], 'lighting': lighting},
                jobs=max(1, int(jobs)))
    index = json.loads((parts / 'scenery-index.json').read_text())
    if index['errors']:
        raise ValueError('%s (%s): %s' % (slug, cell['name'], index['errors']))
    # the kept placements: every exported reference but the plants drawn as sprites (a solid tree keeps its
    # collision-only model placed), as prepare_area.build_room hands them to the mesh assembly
    solid_models = set(tree_solid)
    skipped = set(sprite_numbers) | {r['number'] for r in refs if r['number'] in tree_numbers and
                                     'meshes/' + r['model'].replace('\\', '/').casefold() not in solid_models}
    placements = [r['number'] for r in index['references'] if r['number'] not in skipped]
    if not placements:
        raise ValueError('%s (%s): every placement is a plant sprite; no CHIM room to make' % (slug, cell['name']))
    boxes = np.array([b for r in index['references'] for b in r['bounds']], dtype=float) * 0.25
    lo, hi = boxes.min(axis=0) - EDGE, boxes.max(axis=0) + EDGE
    pool_box = lava_rules.quake_bounds(pools, [0, 0, 0], 0.25)
    if pool_box:
        lo = np.minimum(lo, np.array(pool_box[0]) - EDGE)
        hi = np.maximum(hi, np.array(pool_box[1]) + EDGE)
    liquid_brushes, liquid_textures = [], []
    water, top, water_note = water_plane(cell.get('water_height'), lo[2], hi[2])
    hi[2] = top
    if water is not None or pools:
        from PIL import Image
        from prepare_quake import box, miptex
        palette = (Path(scene) / 'id1/gfx/palette.lmp').read_bytes()
        tile = Image.new('P', (16, 16), 255)
        tile.putpalette(palette)
        if water is not None:
            level = water * 0.25
            if not lo[2] < level < hi[2]:
                raise ValueError('%s (%s): water outside the room bounds' % (slug, cell['name']))
            a, b = lo + 8, hi - 8
            b[2] = level
            liquid_brushes.append(box(a, b, '*water'))
            liquid = Image.new('RGB', (64, 64), (65, 87, 91)).quantize(palette=tile, dither=Image.Dither.NONE)
            liquid_textures.append(miptex('*water', liquid))      # prepare_area.build_room's water texture
        if pools:
            from mwad.audit import BSA
            from npc_geometry import Assets
            assets = Assets(Path(data), BSA(child_ci(data, 'Morrowind.bsa')))
            layers = max((p['layers'] for p in pools), key=len)
            liquid_textures += [m for _, _, m in lava_rules.wad_entries(assets.texture, layers, tile)]
    lava_brushes, lava_entities, lava_records = lava_rules.map_parts(pools, [0, 0, 0], 0.25)
    liquid_brushes += lava_brushes
    # the start: the first original arrival (prepare_area.spawn_entrance); a room no door leads into (the parity
    # batch) starts above the middle of its placements, named in the receipt (to check in the game)
    if cell['entrances']:
        entrance = spawn_entrance(cell)['destination']
        spawn = [v * 0.25 for v in entrance['position']]
        spawn[2] += SPAWN_LIFT
        yaw = (90 - math.degrees(entrance['rotation_radians'][2])) % 360
        start_rule = 'first original arrival'
    else:
        spawn = [float((lo[0] + hi[0]) / 2), float((lo[1] + hi[1]) / 2), float(hi[2] - EDGE)]
        yaw, start_rule = 0.0, 'no door leads in: above the middle of the placements (to check in the game)'
    from prepare_npcs import quote
    label = cell['name'].removeprefix('Seyda Neen, ').removeprefix('Balmora, ')
    world = ['"classname" "worldspawn"', '"message" ' + quote(label), '"%s" "1"' % SHELL_KEY] + \
        ([timings] if timings else [])
    entities = ['{\n' + '\n'.join(world) + '\n}',
                entity_text({'classname': 'info_player_start', 'origin': ' '.join(map(str, spawn)), 'angle': yaw})]
    entities += lava_entities
    if pools:
        # the pools' "lava layer" loops, converted into the unit's own id1/sound (installed with the room)
        import shutil as _shutil
        (root / 'id1/sound' / lava_rules.SOUND_FOLDER).mkdir(parents=True, exist_ok=True)
        volumes, _ = lava_rules.convert_sounds(data, pools, root / 'id1/sound', _shutil.which('ffmpeg') or 'ffmpeg')
        entities += lava_rules.loop_entities(pools, [0, 0, 0], 0.25, volumes)
    if liquid_brushes:
        # the brushes chim.interior.room_liquids reads (never compiled: no qbsp for a CHIM room)
        (root / 'room.map').write_text('{\n"classname" "worldspawn"\n' + '\n'.join(liquid_brushes) + '\n}\n',
                                       encoding='utf-8', newline='\n')     # ASCII: read back as cp1252 the same
    sprite_files = {}
    plant_report = None
    if sprite_numbers or tree_numbers:
        palette = (Path(scene) / 'id1/gfx/palette.lmp').read_bytes()
        colormap = (Path(scene) / 'id1/gfx/colormap.lmp').read_bytes()
        sprites, plants = interior_plants.place(parts, refs, sprite_numbers + tree_numbers, lighting, palette,
                                                colormap, root / 'id1')
        entities += sprites
        sprite_files = plants['files']
        plant_report = {'placements': len(sprite_numbers) + len(tree_numbers), 'sprite_files': plants['files'],
                        'sprites': plants['sprites'], 'decisions': plant_rows, 'mode': interior_plants.plant_mode(),
                        'trees': len(tree_numbers), 'collision_only_models': tree_solid,
                        'rule': 'nonsolid static plants and static trees drawn as shaded sprites; a solid tree keeps '
                                'its collision (tools/interior_plants.py)'}
    elif plant_rows:
        plant_report = {'placements': 0, 'decisions': plant_rows}
    (root / 'room.bsp').write_bytes(shell_map(lo, hi, entities, liquid_textures))
    (root / 'placements.json').write_text(json.dumps(placements) + '\n', encoding='utf-8', newline='\n')
    report = {'map': slug, 'cell': cell['name'], 'form': 'chim room shell', 'spawn': spawn, 'yaw': yaw,
              'start_rule': start_rule, 'placements': len(placements), 'references': len(index['references']),
              'omitted': omitted, 'water_height': water, **({'water_note': water_note} if water_note else {}),
              'lava': {'mode': lava_mode, 'pools': lava_records},
              'bounds': [list(map(float, lo)), list(map(float, hi))], 'master_sha256': cell['master_sha256'],
              'bytes': (root / 'room.bsp').stat().st_size}
    if plant_report is not None:
        report['plant_sprites'] = plant_report
    (root / 'conversion.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    return report, cell


def open_units(scene, timings):
    """(unit cache, the inputs every room unit of this stage shares) or (None, None) when the cache is off or the game
    data identity is unknown (as prepare_area.room_unit). Opened once per stage: opening the cache hashes the
    repository's sources for its environment, and once per room that held the first room back for minutes
    (ROOM-BATCH-CORES-49: 935 rooms, about 150 ms each, on one core before any worker started)."""
    from pass_cache import UnitCache, game_data_digest
    from interior_plants import plant_mode
    cache = UnitCache.open(UNIT, {}, __file__)
    identity = game_data_digest() if cache is not None else None
    if identity is None:
        return None, None
    scene = Path(scene)
    digest = {name: hashlib.sha256((scene / 'id1/gfx' / name).read_bytes()).hexdigest()
              for name in ('palette.lmp', 'colormap.lmp') if (scene / 'id1/gfx' / name).is_file()}
    return cache, {'plants': plant_mode(), 'timings': timings, 'gfx': digest, 'game_data': identity}


def unit_inputs(entry, scene, timings, opened=None):
    """(unit cache, inputs) of one room unit, or (None, None) when the cache is off or the game data identity is
    unknown. OPENED: open_units of the stage (opened here when not given). The inputs are the room's entry and the
    shared inputs, the same key whichever way the cache was opened."""
    cache, shared = open_units(scene, timings) if opened is None else opened
    if cache is None:
        return None, None
    return cache, dict(shared, entry=entry)


# a room unit's scenery export splits over more workers in the stage's tail only when it has this many placed
# references a worker (fewer: the export's own pool would cost more to start than it saves)
REFS_PER_GEOMETRY_WORKER = 40


def _unit(task):
    """Pool worker: (map, status, value, seconds, geometry workers) of one room unit; a failure names the room and is
    recorded by the caller."""
    room, jobs = task
    started = time.perf_counter()
    try:
        return room[2]['map'], 'ok', build_shell(room, jobs), time.perf_counter() - started, jobs
    except Exception as error:  # recorded per room
        return room[2]['map'], 'failed', '%s: %s' % (type(error).__name__, error), time.perf_counter() - started, jobs


def _spread(room, offered):
    """(task, cores) of one room unit offered OFFERED cores (build_parallel.spread_map): a big room takes them for its
    scenery geometry, a small one keeps to one."""
    cores = max(1, min(int(offered), len(room[4]['refs']) // REFS_PER_GEOMETRY_WORKER))
    return (room, cores), cores


def convert(data, scene, rooms, timings, jobs, refresh=None):
    """Every room unit: restored from the unit cache when its inputs are unchanged, else converted on the shared pool
    (largest first by placed references). Returns {map: (status, value, made)}; value = (report, cell) or the error.
    refresh(rooms) -> {map: cell}: the game data cells of the rooms to convert (read once, in one pass).

    ROOM-BATCH-CORES-49: the unit cache is opened once and the cached rooms are restored on JOBS threads (file reads,
    SHA-256 and writes); the rooms to convert run on the stage's pool, which follows the stage's live allowance (the
    launch JOBS is only its share when it started), and each finished room is stored in the unit cache as it finishes,
    so a stage stopped early keeps every room it finished. In the tail, when fewer rooms are left to start than cores
    are free, a big room's scenery geometry takes the free cores (build_parallel.spread_map)."""
    from concurrent.futures import ThreadPoolExecutor
    from build_parallel import live_jobs, spread_map, stage_ceiling
    from pass_cache import json_exact
    scene = Path(scene)
    results, todo, caches = {}, [], {}
    t0 = time.perf_counter()
    opened = open_units(scene, timings) if rooms else (None, None)
    for entry in rooms:
        caches[entry['map']] = unit_inputs(entry, scene, timings, opened)

    def restore(entry):
        cache, inputs = caches[entry['map']]
        return cache.restore_unit(inputs, scene / 'area-work' / entry['map']) if cache is not None else None
    threads = max(1, min(int(jobs), len(rooms)))
    with ThreadPoolExecutor(threads) as pool:
        rows = list(pool.map(restore, rooms))
    for entry, row in zip(rooms, rows):
        if row is not None:
            results[entry['map']] = ('ok', (row['report'], row['cell']), False)
        else:
            shutil.rmtree(scene / 'area-work' / entry['map'], ignore_errors=True)
            todo.append(entry)
    _log('%d rooms: %d from the unit cache (%s), %d to convert (%.1f s, %d threads)' % (
        len(rooms), len(rooms) - len(todo), UNIT, len(todo), time.perf_counter() - t0, threads))
    if not todo:
        return results
    cells = refresh(todo)
    tasks = [(data, str(scene), entry, timings, cells[entry['map']]) for entry in todo]
    workers = max(1, min(int(jobs), len(tasks)))
    _log('converting %d rooms, largest first (placed references): %d workers now, up to %d as the stage\'s share '
         'grows; a big room\'s scenery geometry takes the free cores of the tail' % (
             len(tasks), max(1, min(live_jobs(workers), len(tasks))), max(1, min(stage_ceiling(workers), len(tasks)))))
    entries = {entry['map']: entry for entry in todo}
    for room, status, value, seconds, cores in spread_map(_unit, tasks, workers, cost=lambda t: len(t[4]['refs']),
                                                          spread=_spread):
        entry = entries[room]
        results[room] = (status, value, True)
        if status != 'ok':
            _log('%s (%s): failed: %s' % (room, entry['cell'], value))
            # nothing of a failed room reaches the CHIM interiors stage (it reads every folder with a room map)
            shutil.rmtree(scene / 'area-work' / room, ignore_errors=True)
            continue
        report, cell = value
        report['seconds'] = round(seconds, 3)
        cache, inputs = caches[room]
        if cache is not None and json_exact({'report': report, 'cell': cell}):
            cache.store_unit(inputs, {'report': report, 'cell': cell}, scene / 'area-work' / room)
        _log('%s (%s): %d placements, %.1f s%s' % (room, entry['cell'], report['placements'], seconds,
                                                   ', %d geometry workers' % cores if cores > 1 else ''))
    return results


def read_cells(data, todo):
    """{map: cell} of the rooms to convert, read in one pass over the master; a room no exterior door leads into
    takes its arrivals from the interior doors into it (town_interiors.convert's rule), in a second pass."""
    from mwad.interior import read_interiors
    from mwad.paths import child_ci
    master = child_ci(data, 'Morrowind.esm')
    names = [e['cell'] for e in todo]
    cells = dict(zip((e['map'] for e in todo), read_interiors(master, names)))
    inner = [e for e in todo if not cells[e['map']]['entrances']]
    if inner:
        for e, cell in zip(inner, read_interiors(master, [e['cell'] for e in inner], include_interior_entrances=True)):
            cells[e['map']] = cell
    return cells


def unclassified_residents(data, rooms):
    """{room: [NPC ids]} of the NPCs placed in the rooms that neither the actor grounding policy
    (config/actor_grounding.json) nor the room residents' classes by reference (config/actor_grounding_rooms.json,
    tools/actor_grounding_census.py --rooms; tools/actor_grounding.py initial_state) classify: the residents step
    refuses them, so the stage refuses first, before any room unit runs (fail fast), with the whole list. The cells
    are read in one pass and returned for the units: (problems, {map: cell})."""
    from actor_grounding import initial_state
    cells = read_cells(data, rooms)
    problems = {}
    for entry in rooms:
        for ref in cells[entry['map']]['refs']:
            if ref.get('deleted') or ref.get('type') != 'NPC_':
                continue
            try:
                initial_state(ref['id'], ref.get('number'))
            except ValueError:
                problems.setdefault(entry['cell'], []).append(ref['id'])
    return {room: sorted(set(ids)) for room, ids in problems.items()}, cells


def room_banks(data, scene, converted):
    """doors-<map>.txt of every converted room: each of its load doors (mwad.interior.original_doors) with its box
    from the door's mesh, target "-" (the image links it, room_batches.link_banks). Returns {map: doors}."""
    from mwad.interior import original_doors
    from mwad.paths import child_ci
    from town_interiors import bank_row, bank_text, door_mesh_bounds, SCALE
    by_cell = {}
    for door in original_doors(child_ci(data, 'Morrowind.esm').read_bytes()):
        if door['source_interior']:
            by_cell.setdefault(door['source_cell'].casefold(), []).append(door)
    wanted = [d for cell in converted.values() for d in by_cell.get(cell['name'].casefold(), [])]
    bounds = door_mesh_bounds(data, wanted) if wanted else {}
    out = {}
    for name, cell in converted.items():
        shift = cell.get('recentred_by') or [0, 0, 0]
        rows = []
        for door in sorted(by_cell.get(cell['name'].casefold(), []), key=lambda d: d['number']):
            low, high = bounds[door['number']]
            mins = [(v - shift[k]) * SCALE - .5 for k, v in enumerate(low)]
            maxs = [(v - shift[k]) * SCALE + .5 for k, v in enumerate(high)]
            rows.append(bank_row(name, '-', door['number'], mins, maxs, [0, 0, 0], 0,
                                 door['destination_cell'] or 'Exterior world'))
        (Path(scene) / 'id1' / ('doors-' + name + '.txt')).write_text(bank_text(rows), encoding='cp1252',
                                                                       newline='\n')
        out[name] = len(rows)
    return out


def prepare(batches, data_files, scene, out, held_by=(), ffmpeg='ffmpeg', jobs=None, root=None,
            resident_files='shared'):
    """RESIDENT_FILES: 'shared' (identical resident files written once, tools/resident_share.py) or 'per-resident'
    (the previous method: every resident keeps its own copies)."""
    import room_batches
    from build_jobs import resolve_jobs
    from mwad.paths import ensure_external, resolve_data_files
    started = time.perf_counter()
    jobs = resolve_jobs(jobs)
    data = resolve_data_files(data_files)
    scene, out = Path(scene), ensure_external(Path(out), 'room batches')
    doc = room_batches.load(root)
    if doc is None:
        raise ValueError('The repo has no room list (config/%s)' % room_batches.CONFIG)
    chosen = room_batches.parse_selection(batches, doc)
    rooms, held, refused = room_batches.plan(doc, chosen, held_by, root)
    _log('batches %s: %d rooms to convert, %d left to other stages (%s), %d refused; %d workers' % (
        room_batches.selection_text(chosen), len(rooms), len(held), ', '.join(sorted(set(held.values()))) or 'none',
        len(refused), jobs))
    out.mkdir(parents=True, exist_ok=False)
    work = out / 'scene'
    for folder in ('id1/gfx', 'id1/maps', 'id1/progs', 'id1/sound/npc'):
        (work / folder).mkdir(parents=True)
    for name in ('palette.lmp', 'colormap.lmp'):
        if (scene / 'id1/gfx' / name).is_file():
            shutil.copyfile(scene / 'id1/gfx' / name, work / 'id1/gfx' / name)
    # the hand timings every converted map carries: the hands stage's report (BUILD-SEYDA-BSP-CARRIER-48)
    from hand_metadata import scene_timings
    timings = scene_timings(scene)
    # a unit's entry is what its conversion reads (its key): the room, its map name, the room policy, its recentring
    entries = [{'map': r['build_map'], 'cell': r['room'], 'interior': True, 'area': 'balmora',
                **({'recentre': r['recentre']} if r.get('recentre') else {})} for r in rooms]
    batch_of = {r['build_map']: r['batch'] for r in rooms}
    # fail fast: every resident NPC has its grounding class before any unit runs (the residents step needs it)
    t0 = time.perf_counter()
    unclassified, cells = unclassified_residents(data, entries) if entries else ({}, {})
    if unclassified:
        ids = sorted({i for v in unclassified.values() for i in v})
        raise ValueError('%d resident NPCs in %d rooms have no grounding class (config/actor_grounding.json or '
                         'config/actor_grounding_rooms.json; fix: python3 tools/actor_grounding_census.py --rooms '
                         '--data-files DATA --write-rooms; ROOM-BATCH-NPC-GROUNDING-48): %s; rooms: %s' % (
                             len(ids), len(unclassified), ', '.join(ids),
                             '; '.join('%s (%d)' % (r, len(v)) for r, v in sorted(unclassified.items()))))
    _log('preflight: every resident NPC of %d rooms has its grounding class (%.1f s)'
         % (len(entries), time.perf_counter() - t0))
    t0 = time.perf_counter()
    results = convert(data, work, entries, timings, jobs, refresh=lambda todo: {e['map']: cells[e['map']] for e in todo})
    units_seconds = time.perf_counter() - t0
    converted, reports, failed, rows = {}, [], {}, []
    for entry in entries:
        entry = dict(entry, room=entry['cell'], batch=batch_of[entry['map']])
        status, value, made = results[entry['map']]
        if status != 'ok':
            failed[entry['room']] = value
            continue
        report, cell = value
        converted[entry['map']] = cell
        reports.append(report)
        shutil.copyfile(work / 'area-work' / entry['map'] / 'room.bsp', work / 'id1/maps' / (entry['map'] + '.bsp'))
        from interior_plants import install_room_files
        install_room_files(work, entry['map'], report)
        # a lava room's loop sounds (build_shell): same bytes = same file, as the sprites
        sounds = work / 'area-work' / entry['map'] / 'id1/sound'
        for source in sorted(p for p in sounds.rglob('*') if p.is_file()) if sounds.is_dir() else ():
            target = work / 'id1/sound' / source.relative_to(sounds)
            if target.is_file() and target.read_bytes() != source.read_bytes():
                raise ValueError('Room %s: sound %s differs from the one another room wrote'
                                 % (entry['map'], target.name))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        rows.append({'room': entry['room'], 'map': entry['map'], 'batch': entry['batch'],
                     'placements': report['placements'], 'made': made, 'seconds': report.get('seconds')})
    residents = None
    t1 = time.perf_counter()
    if converted:
        from prepare_area import populate
        residents = populate(data, work, converted, reports, ffmpeg, jobs, include_exterior=False,
                             report_name='room-batches-residents.json', doors=False)
    # identical resident files written once (ROOM-RESIDENT-MODELS-SIZE-48; tools/resident_share.py): the same model
    # set or greeting under another name points at the first one; --resident-files per-resident keeps every copy
    import resident_share
    shared = resident_share.share(work / 'id1', (residents or {}).get('models', {}), resident_files)
    if residents and shared['paths']:
        changed = resident_share.rewrite_maps(work / 'id1/maps', sorted(converted), shared['paths'])
        resident_share.rewrite_report(work / 'room-batches-residents.json', residents)
        _log('resident files shared: %d of %d model sets (%d files, %.1f MiB) and %d of %d greetings (%d files, '
             '%.1f MiB); %d room maps pointed at the kept files' % (
                 shared['models']['shared'], shared['models']['residents'], shared['models']['files_removed'],
                 shared['models']['bytes_removed'] / 1048576, shared['voices']['shared'],
                 shared['voices']['residents'], shared['voices']['files_removed'],
                 shared['voices']['bytes_removed'] / 1048576, len(changed)))
    residents_seconds = time.perf_counter() - t1
    banks =room_banks(data, work, converted) if converted else {}
    # OUT/id1 = what the image installs: the rooms' maps, banks, residents and sprites (not the run's palette)
    from mwad.paths import copy_tree
    copy_tree(work / 'id1', out / 'id1', ignore=shutil.ignore_patterns('gfx'))
    files = {p.relative_to(out / 'id1').as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted((out / 'id1').rglob('*')) if p.is_file()}
    made = sum(1 for r in rows if r['made'])
    # residents baked at a smaller animation level than the build's profile (prepare_area.build_resident: the kit
    # model over the alias byte budget at every rung; RESIDENT-ANIM-BYTE-BUDGET-48): counted by level, with ids
    fallbacks = (residents or {}).get('anim_fallback', [])
    fallback = {'count': len(fallbacks), 'by_level': {}, 'ids': {}}
    for row in fallbacks:
        fallback['by_level'][row['level']] = fallback['by_level'].get(row['level'], 0) + 1
        fallback['ids'].setdefault(row['level'], []).append(row['id'])
    record = {'format': STAGE_FORMAT, 'batches': chosen, 'selection': room_batches.selection_text(chosen),
              'rooms': rows, 'held': held, 'refused': dict(refused, **failed), 'door_banks': banks,
              'units': {'unit': UNIT, 'made': made, 'from_cache': len(rows) - made, 'failed': len(failed)},
              'residents': {'placed': len((residents or {}).get('cast', [])),
                            'left_out': len((residents or {}).get('left_out', [])),
                            'anim_fallback': fallback,
                            'shared_files': {k: v for k, v in shared.items() if k != 'paths'}},
              'files': files, 'jobs': jobs,
              'seconds': {'units': round(units_seconds, 3), 'residents': round(residents_seconds, 3),
                          'total': round(time.perf_counter() - started, 3)},
              'source': 'game data; config/%s (the batches); the room converter\'s selection without its visual '
                        'world (tools/chim_room_batches.py)' % room_batches.CONFIG}
    (out / RECORD).write_text(json.dumps(record, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    _log('%d rooms converted (%d made, %d from the unit cache), %d left to other stages, %d refused or failed; '
         '%d door banks; %.1f s (units %.1f s, residents %.1f s)' % (
             len(rows), made, len(rows) - made, len(held), len(record['refused']), len(banks),
             record['seconds']['total'], units_seconds, residents_seconds))
    if fallback['count']:
        _log('%d residents baked at a smaller animation level (alias byte budget): %s' % (
            fallback['count'], '; '.join('%s %d (%s)' % (level, n, ', '.join(fallback['ids'][level]))
                                         for level, n in sorted(fallback['by_level'].items()))))
    for room, reason in sorted(record['refused'].items()):
        _log('not converted: %s: %s' % (room, reason))
    return record


def main(argv=None):
    from build_jobs import add_jobs
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--batches', required=True, help='none, all, N, N-M or a comma list (tools/room_batches.py)')
    for name in ('data-files', 'scene', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--held-by', action='append', default=[], metavar='STAGE',
                   help='a room stage of the plan whose rooms are left to it (repeatable)')
    p.add_argument('--ffmpeg', default='ffmpeg')
    p.add_argument('--resident-files', choices=('shared', 'per-resident'), default='shared',
                   help='shared (default): residents with the same model set or greeting use one copy of the files '
                        '(tools/resident_share.py, ROOM-RESIDENT-MODELS-SIZE-48); per-resident: the previous method, '
                        'every resident keeps its own')
    add_jobs(p)
    import npc_lod
    npc_lod.add_converter_options(p)  # the residents' near/far models, as the town room stages take them
    a = p.parse_args(argv)
    npc_lod.apply_options(a)
    import build_profile
    build_profile.instrument('chim-room-batches')
    try:
        prepare(a.batches, a.data_files, a.scene, a.out, a.held_by, a.ffmpeg, a.jobs,
                resident_files=a.resident_files)
    except (OSError, ValueError) as error:
        p.exit(1, 'Error: %s\n' % error)


if __name__ == '__main__':
    main()
