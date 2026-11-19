#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The standing bevels of a classic room map's shell (the prison ship's hold; PRISON-SHIP-POLY-COLLISION-65).

The hold is a classic BSP29 room map, built by tools/prepare_interior.py through the mesh converter
(prepare_mesh_bsp.append_meshes), not a CHIM room, so the CHIM rooms' bevel rule (--chim-hollow-bevels, room type 2,
COLLISION-WORLDWIDE-REDUCTION-64) never reached it: its shell (in_prison_ship, 1,205 authored collision plates) has
stairs, and a hollow mesh with stairs gets exact standing bevels on every plate (mesh_geometry, COLLISION-STAIR-SLOPE-32).
That is 28,873 of the map's 29,182 clipnodes, a point descent of about 840 tree steps in the walkable space.

This module gives the shell the rooms' rule without changing the converter's shared code (whose functions are in the
key of every CHIM model unit): it prepares the room's models itself, exactly as append_meshes would
(prepare_mesh_bsp._prepare_model with the same profiles), sets the shell's bevels on its prepared record, and hands
the models to append_meshes(prepared_models=...). Values (hollow_bevels_env): 1 = exact standing bevels on the
walkable plates only (chim.models.walkable_pieces: floors, treads, ledges), the walls approximate; 2 = approximate on
every plate; 0 = the converter's own choice (exact on every plate here), the method before.
"""
import os
from pathlib import Path

HOLLOW_BEVELS_VARIABLE = 'AMIWIND_HOLLOW_BEVELS'    # --chim-hollow-bevels (hollow_bevels_env.export_hollow_bevels)
ROOM_MAP_HOLLOW_BEVELS = (0, 1, 2)


def room_map_hollow_bevels(own):
    """The hollow bevels of a classic room map's shell: the builder option --chim-hollow-bevels when given, else the
    room map's own value OWN (the prison ship's hold: 1)."""
    text = os.environ.get(HOLLOW_BEVELS_VARIABLE, '').strip()
    value = (int(text) if text.isdigit() else -1) if text else int(own)
    if value not in ROOM_MAP_HOLLOW_BEVELS:
        raise ValueError('hollow bevels must be 0, 1 or 2 (%s)' % HOLLOW_BEVELS_VARIABLE)
    return value


def set_shell_bevels(prepared, bevels):
    """Set the standing bevels of one prepared model record (v, f, polys, parts, lod) by the rule; returns a receipt.
    The record's lod carries them to the collider (prepare_mesh_bsp._bevels): 'collision_bevels' (every piece exact)
    or 'collision_bevels_pieces' (the positions of the exact pieces)."""
    v, f, polys, parts, lod = prepared
    before = ('all' if lod.get('collision_bevels') else len(lod.get('collision_bevels_pieces', ())))
    if bevels == 0 or not parts:
        return {'bevels': bevels, 'pieces': len(parts or ()), 'exact_before': before, 'exact_after': before}
    from chim.models import walkable_pieces
    keep = sorted(walkable_pieces(parts)) if bevels == 1 else []
    lod.pop('collision_bevels', None)
    lod.pop('collision_bevels_pieces', None)
    if keep:
        lod['collision_bevels_pieces'] = keep
    lod['collision'] = ('room hollow bevels 1: exact standing bevels on the %d walkable plates of %d, approximate on '
                        'the rest' % (len(keep), len(parts)) if bevels == 1 else
                        'room hollow bevels 2: approximate standing bevels on all %d plates' % len(parts))
    return {'bevels': bevels, 'pieces': len(parts), 'exact_before': before, 'exact_after': len(keep)}


def prepare_room_models(scenery, shell_source, bevels, jobs=None):
    """({model index: prepared record} of every model of the room's scenery index, receipt), prepared as
    prepare_mesh_bsp._append_meshes prepares them (its profiles, the rocks' default profile, the interior flatten
    profiles), with the shell's bevels set by the rule. The listed source shapes of room_map_shapes are drawn as the
    original draws them: kept whole through the visual reduction (ROOM_MAP_WHOLE_SHAPES), or kept whole and then drawn
    as the boxes of their parts (ROOM_MAP_BOX_SHAPES); --room-shapes off reduces them like the rest, the method
    before. A model's receipts are its prepared lod's 'whole_shapes' and 'box_shapes'."""
    import json
    from build_jobs import resolve_jobs
    from build_parallel import ordered_map
    from prepare_mesh_bsp import _prepare_model, rock_profile
    from room_map_shapes import box_shape_parts, box_shapes, whole_shape_view, whole_shapes
    from surface_flatten import load_profiles
    scenery = Path(scenery)
    index = json.loads((scenery / 'scenery-index.json').read_text())
    profiles = {name: profile for group in index.get('groups', {}).values()
                for name, profile in group.get('visual_profiles', {}).items()}
    flatten = load_profiles(scene_kind='interior' if 'cell' in index else 'exterior')
    tasks, whole = [], {}
    for mi, model in enumerate(index['models']):
        profile = profiles.setdefault(model['source'], rock_profile(model['source'], model['triangles']))
        if model['source'] in flatten:
            profile = {**profile, 'flatten': flatten[model['source']]}
        model, profile, whole[mi] = whole_shape_view(model, profile, whole_shapes(model['source']))
        tasks.append((mi, model, profile, scenery / 'scenery.mwpak', index['textures']))
    workers = min(resolve_jobs(jobs), max(1, len(tasks)))
    # largest first by source triangles: the shell (32,297) starts before the props
    models = dict(ordered_map(_prepare_model, tasks, workers, cost=lambda task: task[1].get('triangles') or 0))
    for mi, receipt in whole.items():
        if receipt:
            models[mi][4]['whole_shapes'] = receipt
            models[mi], _ = box_shape_parts(models[mi], index['models'][mi], box_shapes(index['models'][mi]['source']))
    shells = [mi for mi, model in enumerate(index['models']) if model['source'] == shell_source]
    if len(shells) != 1:
        raise ValueError('The room shell %s is not one model of the scenery index' % shell_source)
    receipt = dict(set_shell_bevels(models[shells[0]], bevels), model=shell_source,
                   rule='room_map_collision: the CHIM rooms\' hollow bevels on a classic room map\'s shell')
    return models, receipt
