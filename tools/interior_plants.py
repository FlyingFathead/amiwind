# SPDX-License-Identifier: GPL-3.0-only
"""Plants of a converted interior drawn as sprites (v0.0.42 plan 2.1, docs/INTERIOR_SECTIONS.md step 1).

Every placed object of an interior is its own inline model (INTERIOR-INLINE-LIMIT-31: 220 per room). A room
over that limit first gets its numerous decorative plants as sprites: a sprite is no inline model, only one
model slot per sprite file, and costs a few hundred bytes of pixels instead of faces, lightmaps and hull.

Which placements (candidates):
  - static scenery only (STAT): a harvestable plant (CONT) keeps its mesh and its pick;
  - a flora mesh ("flora_" in the model name, world_flora.flora_kind not a tree or a log);
  - nonsolid in the original: an NC/NCO marker, or ground vegetation without an authored collision node
    (prepare_tree_sprites.collision_metadata, the world flora rule); a plant you could bump into keeps its mesh.
How it looks:
  - the sprite bake of the world flora (prepare_quake._preview_model): the plant's own outline from its
    alpha, view-parallel, original scale (aw_flora static, aw_scale);
  - sprites are not lit by the renderer, so each sprite is shaded with the room's colormap at the light its
    placement gets (interior_lighting.point_light at the plant's centre, the light a lit face there gets,
    in steps of LIGHT_STEP), one sprite file per plant mesh and light step.
Which rooms (AMIWIND_INTERIOR_PLANTS, INTERIOR-MORAG-TONG-FPS-43):
  - auto (the default from v0.0.43-dev3): every converted interior, whatever its limits. A converted room is
    one vis leaf (its placements are inline models), so every plant mesh in front of the camera is drawn every
    frame; island-wide the nonsolid static plants were 397 placements and 78,502 faces in 74 rooms (dev2).
    Static trees of a room become sprites too (tree_candidates): a solid tree keeps its collision as a
    collision-only model (the CHIM sprite recipe's rule, visual_recipes.prepare_sprite_replacements), so the
    player still bumps into the trunk; island-wide 10 trees, 8,121 faces in 6 rooms (Morag Tong: the planter
    ash tree, 1,454 faces). Logs keep their meshes (a lying log is no view-parallel shape);
  - plants: the nonsolid plants of every room, trees keep their meshes;
  - over-limit: the v0.0.42 rule: sprites only for a room over its inline model limit
    (town_interiors.build_room_checked) or a room the town config lists with "plants": "sprites";
  - meshes: every plant a mesh (a room over its model limit fails as before).
"""
import hashlib
import json
import math
import os
from pathlib import Path
import struct

import numpy as np

PLANTS_ENV = 'AMIWIND_INTERIOR_PLANTS'
PLANT_MODES = ('auto', 'plants', 'over-limit', 'meshes')
# light quantum of a shaded sprite: the room light at a placement, rounded to this many of 255
LIGHT_STEP = 16
# Quake's normal lightstyle value ('m' = 12 * 22, the style 0 faces are drawn with)
STYLE_NORMAL = 264
SPRITE_DIR = 'progs/aw_flora'
NOT_SPRITES = ('tree', 'flora_log')


def plant_mode():
    value = os.environ.get(PLANTS_ENV, '') or 'auto'
    if value not in PLANT_MODES:
        raise ValueError('%s must be one of %s, not %r' % (PLANTS_ENV, ', '.join(PLANT_MODES), value))
    return value


def every_room(mode=None):
    """True when the plants of every converted room become sprites (modes auto and plants)."""
    return (mode or plant_mode()) in ('auto', 'plants')


def trees_too(mode=None):
    """True when the static trees of a room become sprites as well (mode auto)."""
    return (mode or plant_mode()) == 'auto'


def room_wants_sprites(entry, mode=None):
    """True when the room ENTRY (a prepare_area room entry) draws its plants as sprites: every room in modes
    auto/plants; in mode over-limit only a room asked for it (entry 'plant_sprites': over its model limit, or
    the town config row "plants": "sprites"); never in mode meshes."""
    mode = mode or plant_mode()
    if mode == 'meshes':
        return False
    return every_room(mode) or bool(entry.get('plant_sprites'))


def is_tree_mesh(model):
    """True for a flora tree mesh ('flora_' name, world_flora.flora_kind 'tree') that may become a sprite."""
    from world_flora import flora_kind
    stem = model.replace('\\', '/').casefold().rsplit('/', 1)[-1]
    return stem.startswith('flora_') and stem.endswith('.nif') and flora_kind(stem) == 'tree'


def tree_candidates(refs, collision_of):
    """(sprite reference numbers, collision-kept models, receipt rows) of a room's static trees. A tree that is
    solid in the original (collision_of(model)['mode'] not 'nonsolid') keeps its collision: its model becomes
    collision-only ('meshes/...' paths in the second value); a harvestable or usable tree keeps its mesh."""
    chosen, solid, rows = [], set(), []
    for ref in refs:
        model = ref.get('model', '').replace('\\', '/').casefold()
        if not is_tree_mesh(model):
            continue
        if ref.get('type') != 'STAT':
            rows.append({'reference': ref['number'], 'model': model, 'kept': 'mesh',
                         'reason': 'harvestable or usable (%s): keeps its mesh' % ref.get('type')})
            continue
        collision = collision_of(model)
        chosen.append(ref['number'])
        if collision['mode'] == 'nonsolid':
            rows.append({'reference': ref['number'], 'model': model, 'kept': 'sprite', 'reason': collision['reason']})
        else:
            solid.add('meshes/' + model)
            rows.append({'reference': ref['number'], 'model': model, 'kept': 'sprite, collision kept',
                         'reason': 'solid in the original (%s): collision-only model' % collision['reason']})
    return chosen, sorted(solid), rows


def is_flora_mesh(model):
    """True for a flora mesh that may become a sprite ('meshes/...' or 'x/y.nif' path)."""
    from world_flora import flora_kind
    stem = model.replace('\\', '/').casefold().rsplit('/', 1)[-1]
    if not stem.startswith('flora_') or not stem.endswith('.nif'):
        return False
    return flora_kind(stem) not in NOT_SPRITES


def candidates(refs, collision_of):
    """(sprite reference numbers, receipt rows) of a room's placements. collision_of(model) -> the
    collision_metadata row of a 'x/y.nif' model (cached by the caller)."""
    chosen, rows = [], []
    for ref in refs:
        model = ref.get('model', '').replace('\\', '/').casefold()
        if not is_flora_mesh(model):
            continue
        if ref.get('type') != 'STAT':
            rows.append({'reference': ref['number'], 'model': model, 'kept': 'mesh',
                         'reason': 'harvestable or usable (%s): keeps its mesh and pick' % ref.get('type')})
            continue
        collision = collision_of(model)
        if collision['mode'] != 'nonsolid':
            rows.append({'reference': ref['number'], 'model': model, 'kept': 'mesh',
                         'reason': 'solid in the original (%s)' % collision['reason']})
            continue
        chosen.append(ref['number'])
        rows.append({'reference': ref['number'], 'model': model, 'kept': 'sprite', 'reason': collision['reason']})
    return chosen, rows


def light_level(point, lighting):
    """The baked light (0..255) a lit face at POINT (map units) gets, rounded to LIGHT_STEP."""
    from interior_lighting import point_light
    flat = {**lighting, 'facing': False}
    value = max(0., min(255., point_light(np.asarray(point, float), flat)))
    return int(min(255, LIGHT_STEP * round(value / LIGHT_STEP)))


def shade_row(level):
    """Colormap row the engine draws a lit face of light LEVEL with (r_surf.c: blocklights = sample x the style
    value, t = (255 x 256 - blocklights) >> (8 - VID_CBITS), at least 64; the row is t >> 8)."""
    t = (255 * 256 - level * STYLE_NORMAL) >> 2
    return max(64, t) >> 8


def shade_sprite(raw, colormap, level):
    """The sprite bytes with every opaque pixel shaded through colormap row shade_row(level) (255 stays
    transparent)."""
    row = shade_row(level)
    table = colormap[row * 256:(row + 1) * 256]
    if len(table) != 256:
        raise ValueError('Colormap has no row %d' % row)
    pixels = bytes(255 if p == 255 else table[p] for p in raw[56:])
    return raw[:56] + pixels


def sprite_name(model, level, raw):
    """Stable file name of a shaded interior plant sprite (the world flora's path form)."""
    digest = hashlib.sha256(b'interior plant\0' + model.encode() + b'\0%d\0' % level + raw).hexdigest()[:16]
    return '%s/f_%s.spr' % (SPRITE_DIR, digest)


def bake_models(parts, wanted_models, palette):
    """{model source: (sprite bytes, xy bake centre)} for the exported models of a room (parts: the room's
    export_refs folder) named in wanted_models ('meshes/...')."""
    from mwad.scene import read_asset
    from prepare_quake import _preview_model
    index = json.loads((Path(parts) / 'scenery-index.json').read_text())
    out = {}
    with (Path(parts) / 'scenery.mwpak').open('rb') as archive:
        textures = {}
        for mi, model in enumerate(index['models']):
            if model['source'] not in wanted_models:
                continue
            used = {m['texture_index'] for m in model['materials'] if m['texture_index'] is not None}
            for ti in used - set(textures):
                raw = read_asset(archive, index['textures'][ti])
                magic, width, height = struct.unpack_from('>4sHH', raw)
                if magic != b'MWT1' or len(raw) != 8 + width * height * 4:
                    raise ValueError('Invalid exported plant texture: ' + model['source'])
                textures[ti] = np.frombuffer(raw[8:], np.uint8).reshape(height, width, 4)
            bake = {**model, 'source': 'flora_' + model['source']}
            _, raw, generated, report = _preview_model((mi, bake, read_asset(archive, model),
                                                        {i: textures[i] for i in used}, list(palette), set()))
            if raw is None or report['kind'] != 'sprite':
                raise ValueError('Plant did not bake to a sprite: ' + model['source'])
            out[model['source']] = (raw, generated[1])
    missing = set(wanted_models) - set(out)
    if missing:
        raise ValueError('Plant sprites not baked: ' + ', '.join(sorted(missing)))
    return out


def place(parts, refs, numbers, lighting, palette, colormap, id1):
    """aw_flora entity texts for the placements NUMBERS of a room, their shaded sprite files written under
    ID1 (same bytes = same file). Returns (entities, receipt)."""
    from prepare_tree_sprites import validate_sprite
    by_number = {r['number']: r for r in refs}
    chosen = [by_number[n] for n in numbers]
    wanted = {'meshes/' + r['model'].replace('\\', '/').casefold() for r in chosen}
    baked = bake_models(parts, wanted, palette)
    entities, files, rows = [], {}, []
    index = json.loads((Path(parts) / 'scenery-index.json').read_text())
    bounds = {r['number']: r['bounds'] for r in index['references']}
    for ref in chosen:
        source = 'meshes/' + ref['model'].replace('\\', '/').casefold()
        raw, centre = baked[source]
        low, high = (np.asarray(b, float) for b in bounds[ref['number']])
        level = light_level((low + high) / 2 * .25, lighting) if lighting else 128
        shaded = shade_sprite(raw, colormap, level)
        validate_sprite(shaded)
        name = sprite_name(source, level, raw)
        target = Path(id1) / name
        if name not in files:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_file() and target.read_bytes() != shaded:
                raise ValueError('Plant sprite name taken by other bytes: ' + name)
            target.write_bytes(shaded)
            files[name] = hashlib.sha256(shaded).hexdigest()
        entities.append(sprite_entity(ref, name, centre))
        rows.append({'reference': ref['number'], 'model': source, 'light': level, 'sprite': name})
    return entities, {'sprites': rows, 'files': files}


def sprite_entity(ref, name, centre, world_scale=.25):
    """The aw_flora static of one plant (the world flora's fields, prepare_world_flora.sprite_entity): the model's
    xy bake centre turned and scaled with the placement, view-parallel, the original scale."""
    from prepare_scenery import reference_rotation
    offset = reference_rotation(ref) @ np.array([*centre, 0.]) * ref['scale']
    point = [(ref['position'][k] + float(offset[k])) * world_scale for k in range(3)]
    if ref['scale'] <= 0 or not all(math.isfinite(v) for v in point + [ref['scale']]):
        raise ValueError('Invalid interior plant sprite transform: %s' % ref['number'])
    fields = {'classname': 'aw_flora', 'model': name, 'aw_scale': format(ref['scale'], '.9g'),
              'aw_ref': str(ref['number']), 'origin': ' '.join(format(v, '.9g') for v in point), 'angles': '0 0 0'}
    return '{\n' + '\n'.join('"' + k + '" "' + v + '"' for k, v in fields.items()) + '\n}'


def add_entities(bsp, entities):
    """Append entity texts to a BSP29 file's entity lump (in place)."""
    from player_hull import lumps, pack_lumps
    path = Path(bsp)
    b = lumps(path.read_bytes())
    text = bytes(b[0]).rstrip(b'\0').decode('cp1252')
    b[0] = (text.rstrip('\n') + '\n' + '\n'.join(entities) + '\n\0').encode('cp1252')
    path.write_bytes(pack_lumps(b))


def install_room_files(scene, slug, report):
    """Copy the files a converted room needs besides its map (its plant sprites, written under the room's own
    area-work/<slug>/id1 by place()) into the scene's id1. Same bytes = same file; a name another room wrote with
    other bytes is refused. Every room installer calls this (v0.0.44-dev1: the Balmora interiors and area
    installers copied only room.bsp, so the image step refused a Mages Guild plant sprite; town_interiors already
    copied them). Returns the installed names."""
    import shutil
    from pathlib import Path
    names = sorted((report.get('plant_sprites') or {}).get('sprite_files', {}))
    for name in names:
        source, target = Path(scene) / 'area-work' / slug / 'id1' / name, Path(scene) / 'id1' / name
        if target.is_file() and target.read_bytes() != source.read_bytes():
            raise ValueError('Room %s: file %s differs from the one another room wrote' % (slug, name))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return names
