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
  ("_chim_world" "chimiti") and come with the layer's room lists.

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


def stage_name(layer):
    """The plan's stage that makes LAYER's CHIM world (run/<stage>)."""
    if layer not in LAYERS:
        raise ValueError('expansion layer %r has no CHIM store (known: %s)' % (layer, ', '.join(sorted(LAYERS))))
    return STAGE_PREFIX + layer.lower()


def image_options(selected, stage_names, run):
    """The image's --chim-layer-world options: one per SELECTED layer whose stage is among STAGE_NAMES, in the
    layer plan's order (Tribunal, Bloodmoon: the masters' load order). [] for no layer (the image unchanged)."""
    out = []
    for layer in ('Tribunal', 'Bloodmoon'):
        if layer in (selected or ()) and stage_name(layer) in stage_names:
            out += [OPTION, '%s=%s' % (LAYERS[layer]['store'], Path(run) / stage_name(layer))]
    return out


def parse(values):
    """[(store, world dir)] of the image's --chim-layer-world STORE=WORLD values; a store named twice, an unknown
    store or a missing '=' stops the image step at once (before anything is written)."""
    known = {spec['store']: layer for layer, spec in LAYERS.items()}
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


def install(values, id1, hand_fields):
    """Install every --chim-layer-world store into ID1. Returns [record] (one per store), [] for none."""
    pairs = parse(values)
    kinds = {spec['store']: spec['kind'] for spec in LAYERS.values()}
    records = []
    for store, world in pairs:
        if kinds[store] == 'frames':
            from chim.sol_test import install as install_frames
            record = install_frames(world, id1, hand_fields, store=store)
        else:
            files, size = copy_store(world / 'chim', Path(id1) / store)
            record = {'store': store, 'files': files, 'bytes': size, 'maps': []}
            print('[chim-layer] store %s (%d files, %d bytes)' % (store, files, size), flush=True)
        record['kind'] = kinds[store]
        records.append(record)
    return records
