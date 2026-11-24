# SPDX-License-Identifier: GPL-3.0-only
"""The expansions' CHIM stores in the image: ONE store per selected layer, beside the island's id1/chim/.

A build that selects an expansion layer (tools/build.py expansion_selection: --dlc / --no-dlc, default both) and
whose plan carries that layer's CHIM world stage (STAGE_PREFIX + the layer's name, run/<stage>, made by the layer
stages from the normal stage outputs) gives the image `--chim-layer-world STORE=WORLD` for it. The image then installs
the layer's world as its own store (the store names of the layer plan, tools/layout_plan.py STORE_UNITS):

- Bloodmoon (Solstheim): store chimsol, region frames: the store, one frame map slNNNN per frame, the Solstheim rows
  of the open-world region table (world/regions-sl.awr) and the region names (tools/chim/sol_test.py install, the
  same code the Solstheim test frame used);
- Tribunal (Mournhold): store chimiti, rooms: the store only; its room maps name the store themselves
  ("_chim_world" "chimiti") and come with the layer's room lists;
- Tribunal's module tribunal-mournhold (Mournhold's outdoor districts, a small map of its own): store chimmh, region
  frames: the store, one frame map mhNNNN per frame and the districts' rows file world/regions-mh.awr
  (MODULE_STAGES below).

The engine selects a store from the map it loads (chim_world.c Chim_StoreSelect) and refuses a door or a travel
destination whose map, or whose map's store, is not in the image (aw_scene.c, the unbuilt-target guard).

With no layer selected (--no-dlc), or with no layer stage in the plan, nothing is added: the image is byte for byte
the image without this module."""
import shutil
from pathlib import Path

# layer name (expansions_report / build.DLC_CHOICES) -> its store and what the store holds
LAYERS = {
    'Bloodmoon': {'store': 'chimsol', 'kind': 'frames'},
    'Tribunal': {'store': 'chimiti', 'kind': 'rooms'},
}
STAGE_PREFIX = 'chim-layer-'
OPTION = '--chim-layer-world'
# The expansions' build modules whose stage makes a CHIM world of its own (tools/build.py "THE EXPANSIONS AS BUILD
# MODULES"): stage name -> its expansion layer, its store and what the store holds. Mournhold's outdoor districts
# (module tribunal-mournhold) are region frames in the store chimmh: the store, one frame map mhNNNN per frame and
# the districts' own rows file world/regions-mh.awr (tools/chim/sol_test.py LANDS; engine aw_world.c), a small map
# of its own beside Vvardenfell's.
MODULE_STAGES = {
    'tribunal-mournhold': {'layer': 'Tribunal', 'store': 'chimmh', 'kind': 'frames'},
    # Solstheim's outdoor cells (module bloodmoon-solstheim, tools/bloodmoon_solstheim_module.py): region frames in
    # the store chimsol, one frame map slNNNN per frame and the rows file world/regions-sl.awr
    'bloodmoon-solstheim': {'layer': 'Bloodmoon', 'store': 'chimsol', 'kind': 'frames'},
    # the recordless open sea of the area Bloodmoon adds to the map's box (the module's second world stage,
    # SOL-SEA-CROSSING-68): the store chimsea, its frame maps numbered on after Solstheim's (tools/chim/sol_test.py
    # LANDS 'after'), so it comes after bloodmoon-solstheim in this table and in the image's options
    'bloodmoon-solstheim-sea': {'layer': 'Bloodmoon', 'store': 'chimsea', 'kind': 'frames'},
}


def store_kinds():
    """{store: kind} of every store the image can install (the layers' and the modules')."""
    return dict({spec['store']: spec['kind'] for spec in LAYERS.values()},
                **{spec['store']: spec['kind'] for spec in MODULE_STAGES.values()})


def stage_name(layer):
    """The plan's stage that makes LAYER's CHIM world (run/<stage>)."""
    if layer not in LAYERS:
        raise ValueError('expansion layer %r has no CHIM store (known: %s)' % (layer, ', '.join(sorted(LAYERS))))
    return STAGE_PREFIX + layer.lower()


def image_options(selected, stage_names, run):
    """The image's --chim-layer-world options: one per SELECTED layer whose stage is among STAGE_NAMES, in the
    layer plan's order (Tribunal, Bloodmoon: the masters' load order). [] for no layer (the image unchanged)."""
    out, stores = [], {}
    for layer in ('Tribunal', 'Bloodmoon'):
        if layer in (selected or ()) and stage_name(layer) in stage_names:
            out += [OPTION, '%s=%s' % (LAYERS[layer]['store'], Path(run) / stage_name(layer))]
            stores[LAYERS[layer]['store']] = stage_name(layer)
    for stage, spec in MODULE_STAGES.items():
        if spec['layer'] in (selected or ()) and stage in stage_names:
            if spec['store'] in stores:
                # one store, one stage: a plan with a layer stage and a module stage for the same store is a builder
                # fault, said here before any stage instead of by the image step at the end
                raise ValueError('the stages %s and %s both make the store %s: one plan holds one of them'
                                 % (stores[spec['store']], stage, spec['store']))
            out += [OPTION, '%s=%s' % (spec['store'], Path(run) / stage)]
            stores[spec['store']] = stage
    return out


def parse(values):
    """[(store, world dir)] of the image's --chim-layer-world STORE=WORLD values; a store named twice, an unknown
    store or a missing '=' stops the image step at once (before anything is written)."""
    known = store_kinds()
    out, seen = [], set()
    for value in values or ():
        store, sep, world = str(value).partition('=')
        if not sep or not world:
            raise ValueError('%s %r: expected STORE=WORLD' % (OPTION, value))
        if store not in known:
            raise ValueError('%s: unknown store %r (known: %s)' % (OPTION, store, ', '.join(sorted(known))))
        if store in seen:
            raise ValueError('%s: store %s given twice' % (OPTION, store))
        seen.add(store)
        out.append((store, Path(world)))
    return out


def frame_holders(values):
    """{(x, y): (frame map, origin)} of the frames of every --chim-layer-world store that holds region frames, by the
    names install() gives their frame maps (the store's world table in order: mh0000, mh0001, ...): the shape of
    room_batches.region_frames, so the image's door tables link a door in or into such a frame as they link one of
    the base world's region frames (MOURNHOLD-EXTERIOR-CELLS-66: a district's doors). {} for none."""
    out = {}
    for held in frame_holders_by_store(values).values():
        out.update(held)
    return out


def frame_holders_by_store(values):
    """{store: {(x, y): (frame map, origin)}}: frame_holders kept apart by store. A land whose maps are numbered on
    after another's (sol_test LANDS 'after': chimsea after chimsol) counts that land's frames whatever the order of
    VALUES; so a check that walks one store's world (the door check) names its frames as the image does, and the far
    sea's sl0153.. never take the names of Solstheim's own sl0000.. (the v0.0.68 release build's door check, 83
    Solstheim doors traced in the far sea's world: DOOR-CHECK-SEA-STORE-NAMES-68). A store given without its 'after'
    land is numbered from 0, as install() numbers it alone (the expansion preflight checks one store by itself)."""
    from chim.regions import TABLE_FILE, read_table
    from chim.sol_test import land_of, map_name
    kinds = store_kinds()
    stores, counts = [], {}
    for store, world in parse(values):
        if kinds[store] != 'frames':
            continue
        table = read_table(Path(world) / TABLE_FILE) or {}
        frames = table.get('frames') or []
        counts[store] = len(frames)
        stores.append((store, land_of(store, world), frames))
    out = {}
    for store, land, frames in stores:
        offset = counts.get(land.get('after'), 0)
        out[store] = {tuple(frame['cell']): (map_name(offset + index, land['prefix'], land['limit']),
                                             list(frame['origin'])) for index, frame in enumerate(frames)}
    return out


def copy_store(source, target):
    """Copy the store folder SOURCE (world.cwi and its packs) to TARGET; (files, bytes)."""
    if not (Path(source) / 'world.cwi').is_file():
        raise ValueError('%s: no CHIM world in %s' % (OPTION, source))
    if Path(target).exists():
        raise ValueError('%s: %s already exists' % (OPTION, target))
    files = size = 0
    for path in sorted(Path(source).rglob('*')):
        if path.is_file():
            out = Path(target) / path.relative_to(source)
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, out)
            files += 1
            size += path.stat().st_size
    return files, size


def install(values, id1, hand_fields, actors=None):
    """Install every --chim-layer-world store into ID1. Returns [record] (one per store), [] for none.
    ACTORS: a call (store, world folder) -> the store's frame actor inputs or None (tools/build_aga.py
    layer_actor_inputs), or None: a store of frames then carries its cells' people in its frame maps
    (chim.sol_test.install)."""
    pairs = parse(values)
    kinds = store_kinds()
    records = []
    for store, world in pairs:
        if kinds[store] == 'frames':
            from chim.sol_test import install as install_frames
            record = install_frames(world, id1, hand_fields, store=store,
                                    actors=actors(store, world) if actors is not None else None)
        else:
            files, size = copy_store(world / 'chim', Path(id1) / store)
            record = {'store': store, 'files': files, 'bytes': size, 'maps': []}
            print('[chim-layer] store %s (%d files, %d bytes)' % (store, files, size), flush=True)
        record['kind'] = kinds[store]
        records.append(record)
    return records
