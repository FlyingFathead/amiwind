# SPDX-License-Identifier: GPL-3.0-only
"""Checksum-bound visual reduction recipes; no source meshes or texture pixels.

Recipes alter converter profiles only. The mesh preparer retains the original
geometry for collision. A different source packet keeps its ordinary profile.
"""
import hashlib
import json
from pathlib import Path


def load_recipes(path=None):
    path = Path(path) if path else Path(__file__).resolve().parents[1] / 'config/visual-recipes.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('format') != 1:
        raise ValueError('Unknown visual recipe format')
    return data


def apply_recipe(profile, model, recipe, document):
    """Return a new profile only when both source identity and packet SHA match."""
    if not recipe:
        return profile
    entries = document['recipes'][recipe]['models']
    source = model['source'].replace('\\', '/').lower()
    entry = entries.get(source)
    if entry is None:
        cap = document['recipes'][recipe].get('default_visual_ratio')
        if cap is None or source.rsplit('/', 1)[-1].startswith('terrain_'):
            return profile
        if not 0 < cap <= 1:
            raise ValueError('Invalid recipe ratio cap')
        error = document['recipes'][recipe].get('default_error_share', 0.0025)
        if not 0 <= error <= 0.05:
            raise ValueError('Invalid recipe error bound')
        from mesh_methods import apply
        return apply(dict(profile, ratio=min(float(profile.get('ratio', 1)), cap),
                          meshopt_error_share=error, lod_preserve_border=True),
                     source, {'mesh_method': 'meshopt+merge'})
    if model.get('sha256') != entry['sha256']:
        return profile
    if 'collision_tolerance' in entry:
        # coarser collision pieces for this mesh only (mesh_geometry.collision_parts' tolerance, default 2 units of
        # open space a convex piece may fill); its drawn mesh is unchanged unless the entry also reduces it
        # (CHIM-COLLISION-UNION-FALLBACK-41: a gnarly Telvanni root's collision was ~95 % of its bytes)
        tolerance = float(entry['collision_tolerance'])
        if not 2 <= tolerance <= 32:
            raise ValueError('Invalid collision tolerance (2-32 units): ' + source)
        profile = dict(profile, collision_tolerance=tolerance)
        if not any(k in entry for k in ('primitive', 'panel', 'ratio')):
            return dict(profile, visual_recipe={'name': recipe, 'sha256': entry['sha256']})
    if 'primitive' in entry:
        return dict(profile, visual_primitive=dict(entry['primitive']),
                    visual_recipe={'name': recipe, 'sha256': entry['sha256']})
    if 'panel' in entry:
        return dict(profile, visual_panel=dict(entry['panel']),
                    visual_recipe={'name': recipe, 'sha256': entry['sha256']})
    ratio, error = float(entry['ratio']), float(entry['error_share'])
    if not 0 < ratio <= 1 or not 0 <= error <= 0.05:
        raise ValueError('Invalid visual reduction bounds: ' + source)
    from mesh_methods import apply
    result = apply(dict(profile, ratio=ratio), source, {'mesh_method': 'meshopt+merge'})
    result.update(meshopt_error_share=error, lod_preserve_border=True,
                  visual_recipe={'name': recipe, 'sha256': entry['sha256']})
    return result


EVERYWHERE_VARIABLE = 'AMIWIND_VISUAL_EVERYWHERE'   # off: every mesh keeps its original visual (the method before)


def everywhere_recipe(document):
    """The recipe applied in every CHIM cell and town frame (document 'everywhere'), unless switched off with
    AMIWIND_VISUAL_EVERYWHERE=off. A cell's own recipe wins for the meshes it names; an everywhere recipe has no
    default ratio, so a mesh it does not name keeps its profile."""
    import os
    name = document.get('everywhere')
    if not name or os.environ.get(EVERYWHERE_VARIABLE, 'on') == 'off':
        return None
    if name not in document['recipes'] or document['recipes'][name].get('default_visual_ratio') is not None:
        raise ValueError('everywhere recipe %r must exist and must not cap unnamed meshes' % name)
    return name


def sprite_key(key, digest):
    """A mesh key with its sprite replacement (DIGEST: the sprite's SHA-256); a chim.units.UnitKey keeps its
    previous form the same way, so units stored under it are still found."""
    from chim.units import UnitKey
    new = UnitKey(hashlib.sha256((str(key) + ':sprite:' + digest).encode()).hexdigest())
    previous = getattr(key, 'previous', None)
    if previous is not None:
        new.previous = hashlib.sha256((previous + ':sprite:' + digest).encode()).hexdigest()
    return new


def prepare_sprite_replacements(recipe, index, archive, palette, references,
                                prepared, mesh_fps, centre, out):
    """Bake recipe-selected flora using the existing sprite renderer and static protocol.

    Preserve collision and the source/model pool. Return frame-local entity rows
    plus asset hashes for the image stage; generated pixels stay in build output.
    """
    import hashlib
    import re
    import struct
    import numpy as np
    from mwad.scene import read_asset
    from prepare_quake import _preview_model
    from prepare_tree_sprites import validate_sprite
    from prepare_world_flora import sprite_entity
    from world_flora_policy import stable_sprite_name
    recipes = load_recipes()['recipes']
    prepared, mesh_fps = dict(prepared), dict(mesh_fps)
    rows, assets = [], []
    with Path(archive).open('rb') as source:
        for mi, model in enumerate(index['models']):
            key = model['source'].replace(chr(92), '/').lower()
            selected_recipe = model.get('_visual_recipe', recipe)
            entries = recipes[selected_recipe].get('sprites', {}) if selected_recipe else {}
            wanted = entries.get(key)
            refs = [r for r in references if r['model_index'] == mi]
            if wanted is None or not refs:
                continue
            packet = read_asset(source, model)
            if hashlib.sha256(packet).hexdigest() != wanted['geometry_sha256']:
                raise ValueError('Sprite recipe geometry mismatch: ' + key)
            textures = {}
            for material in model['materials']:
                ti = material['texture_index']
                if ti is not None and ti not in textures:
                    raw = read_asset(source, index['textures'][ti])
                    _, w, h = struct.unpack_from('>4sHH', raw)
                    textures[ti] = np.frombuffer(raw[8:], np.uint8).reshape(h, w, 4)
            _, raw, generated, _ = _preview_model((mi, model, packet, textures, list(palette), set()))
            if raw is None or generated is None:
                raise ValueError('Sprite recipe did not produce a sprite: ' + key)
            stats = validate_sprite(raw)
            name = stable_sprite_name(model['source'])
            path = Path(out) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            assets.append(dict(path=name, sha256=digest, bytes=len(raw), **{'sprite_type': stats['sprite_type']}))
            asset = {'sprite_asset_name': name, 'source_xy_bake_center': generated[1]}
            for ref in refs:
                text = sprite_entity(ref, asset, [centre[0]*.25, centre[1]*.25, 0])
                rows.append(dict(re.findall(r'"([^"\n]*)"\s+"([^"\n]*)"', text)))
            data = list(prepared[mi])
            data[2] = []
            data[4] = dict(data[4], representation='collision_only')
            prepared[mi] = tuple(data)
            mesh_fps[mi] = sprite_key(mesh_fps[mi], digest)
    return prepared, mesh_fps, rows, assets


def cell_settings(cell):
    """Explicit per-cell conversion recipes; other cells retain their settings."""
    key = '%d,%d' % tuple(cell)
    return load_recipes().get('cell_settings', {}).get(key, {})


def scope_reference_recipes(index, settings, document=None):
    """Bind conversion policy to the original CELL, including its apron copies.

    A shared source mesh may be placed in cells with different policies. Split
    only that in-memory model binding; retain original references and packets.
    Undeclared cells keep their ordinary profiles, even in a recipe frame.
    """
    document = load_recipes() if document is None else document
    cells = document.get('cell_settings', {})
    home = tuple(settings.get('source_cell', ()))
    if not settings.get('visual_recipe') and not settings.get('clip_to_terrain') and not any(
            cells.get('%d,%d' % tuple(ref['cell']), {})
            for ref in index['references'] if len(ref.get('cell') or []) == 2):
        return index
    bindings, references, assigned = {}, [], set()
    models = [dict(model, _visual_recipe=None, _clip_to_terrain=False) for model in index['models']]
    for ref in index['references']:
        cell = tuple(ref.get('cell') or home)
        policy = cells.get('%d,%d' % cell, {}) if len(cell) == 2 else {}
        if cell == home:
            policy = dict(policy, **{k: settings[k] for k in ('visual_recipe', 'clip_to_terrain') if k in settings})
        recipe = policy.get('visual_recipe')
        clip = bool(policy.get('clip_to_terrain', False))
        key = (ref['model_index'], recipe, clip)
        if key not in bindings:
            mi = ref['model_index']
            model = dict(index['models'][mi], _visual_recipe=recipe, _clip_to_terrain=clip)
            if mi not in assigned:
                bindings[key] = mi
                models[mi] = model
                assigned.add(mi)
            else:
                bindings[key] = len(models)
                models.append(model)
        references.append(dict(ref, model_index=bindings[key]))
    return dict(index, models=models, references=references)
