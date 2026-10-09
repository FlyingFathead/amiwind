# SPDX-License-Identifier: GPL-3.0-only
"""Seyda Neen's CHIM source stage (format 0.5, milestone M2).

Seyda Neen's exterior is not made by the town converter that Balmora and the
Vivec districts use. The legacy builder's scene and bsp stages make one
complete town map (prepare_quake: seyda.map; prepare_mesh_bsp: the placed
meshes appended as func_wall), which the image step cuts into the region maps
sn000... (prepare_seyda_regions). This stage reads the same inputs from the
legacy run folder, with the same functions, so the CHIM frame holds what the
region maps hold:

- placements: the bsp stage's selection (scenery_selection.select_runtime_refs
  over the scene's runtime bounds, prepare_mesh_bsp.DRESSING_EXCLUDED left
  out), its converter profiles (scenery groups' visual profiles,
  static_lod.rock_profile, the exterior flattening profiles) and the shared
  mesh converter (prepare_mesh_bsp._prepare_model);
- ground: the scene stage's own triangles (prepare_quake.town_ground_triangles:
  shoreline samples in 128-unit tiles and the port's 32-unit patch) over its
  GROUND_BOUNDS, and the same sampler (prepare_world_regions.terrain_triangles)
  for the tiles the frame adds around them, so the frame is a whole number of
  sectors. Those tiles read the canonical LAND of the whole island (the
  world-survey stage's terrain-source.npz, prepare_world_regions.Terrain), not
  the scene stage's nine-cell audit, so the frame's edge is the real coast and
  hills rather than the audit's ocean fallback; the two sources must agree on
  every audited cell (checked);
- ground textures: the scene stage's town.wad (gN, *water);
- the opening references (prepare_opening_refs.opening_references, the same
  reading of the master): placements on the ship's disable list carry the
  story-hidden flag (the legacy "aw_story_hidden" key the opening hides,
  aw_opening.c), and the tutorial barrel is converted and placed as the
  opening-references stage adds it to the scene.

The frame: Seyda Neen's centre (prepare_quake.CENTRE, the origin of the region
maps, door arrivals, harvest catalogues and saves), cell (-2, -9), its box
GROUND_BOUNDS rounded out to whole sectors.

The legacy run folder (`--legacy-run`, tools/build.py's run folder) holds
work/generated/seyda-neen (the terrain audit), scenery/ (scenery index and
archive), alias-scene/ (town.wad).
"""
import json
import math
from pathlib import Path

AREA = 'seyda'
CONFIG = 'seyda_area.json'
TERRAIN_APRON = 768          # prepare_quake.TERRAIN_APRON (tests check they agree)
TILE = 128


def _config(root=None):
    root = Path(root) if root else Path(__file__).resolve().parents[2]
    return json.loads((root / 'config' / CONFIG).read_text(encoding='utf-8'))


def ground_bounds(root=None):
    """prepare_quake.GROUND_BOUNDS from the config (light: no converter imports)."""
    (lx, ly), (hx, hy) = _config(root)['bounds']
    return (lx - TERRAIN_APRON, ly - TERRAIN_APRON), (hx + TERRAIN_APRON, hy + TERRAIN_APRON)


def centre(root=None):
    return tuple(float(v) for v in _config(root)['centre'])


def frame_box(grain=256, sector_chunks=3, root=None):
    """The frame in frame-local units: GROUND_BOUNDS rounded out to whole sectors."""
    unit = grain * sector_chunks
    (lx, ly), (hx, hy) = ground_bounds(root)
    return ((math.floor(lx / unit) * unit, math.floor(ly / unit) * unit),
            (math.ceil(hx / unit) * unit, math.ceil(hy / unit) * unit))


def world_box(grain=256, sector_chunks=3, root=None):
    """The frame's ground box in Morrowind units (as chim.areas compares frames)."""
    (lx, ly), (hx, hy) = frame_box(grain, sector_chunks, root)
    cx, cy = centre(root)
    return cx + 4 * lx, cy + 4 * ly, cx + 4 * hx, cy + 4 * hy


def source_cell(root=None):
    cx, cy = centre(root)
    return math.floor(cx / 8192), math.floor(cy / 8192)


def audit_terrain(grids):
    """prepare_world_regions.Terrain over the scene stage's audit grids (as town_ground_triangles)."""
    import numpy as np
    from prepare_world_regions import Terrain
    terrain = Terrain.__new__(Terrain)
    terrain.cells = {tuple(g['cell']): i for i, g in enumerate(grids)}
    terrain.heights = np.asarray([g['heights'] for g in grids], dtype=float)
    terrain.materials = np.asarray([g['materials'] for g in grids], dtype=int)
    return terrain


def canonical_terrain(survey, grids):
    """The canonical LAND (world-survey terrain-source.npz), checked against the audit grids: every
    audited cell has the same heights and materials in both."""
    import numpy as np
    from prepare_world_regions import Terrain
    terrain = Terrain(Path(survey))
    for g in grids:
        cell = tuple(g['cell'])
        if cell not in terrain.cells:
            raise ValueError('Canonical LAND lacks the audited Seyda Neen cell %s' % (cell,))
        i = terrain.cells[cell]
        if not (np.array_equal(terrain.heights[i], np.asarray(g['heights'], dtype=float))
                and np.array_equal(terrain.materials[i], np.asarray(g['materials'], dtype=int))):
            raise ValueError('Canonical LAND and the scene stage\'s audit differ in cell %s' % (cell,))
    return terrain


def ground_triangles(grids, low, high, canonical=None):
    """[(triangle, material)] over the frame (frame-local units): the scene stage's own triangles
    inside GROUND_BOUNDS (prepare_quake.town_ground_triangles, unchanged), the same sampler
    (prepare_world_regions.terrain_triangles) for every other tile of the frame, over the
    canonical LAND when given (canonical_terrain), else over the audit grids."""
    from prepare_quake import CENTRE, GROUND_BOUNDS, SCALE, town_ground_triangles
    from prepare_world_regions import terrain_triangles
    out = [(tri, int(m)) for tri, m in town_ground_triangles(grids)]
    terrain = canonical if canonical is not None else audit_terrain(grids)
    ox, oy = (v * SCALE for v in CENTRE)
    (gx0, gy0), (gx1, gy1) = GROUND_BOUNDS
    for y in range(int(low[1]), int(high[1]), TILE):
        for x in range(int(low[0]), int(high[0]), TILE):
            if gx0 <= x < gx1 and gy0 <= y < gy1:
                continue
            for tri in terrain_triangles(terrain, x + ox, y + oy):
                material = terrain.sample(*(sum(p[k] for p in tri) / 3 for k in (0, 1)))[1]
                out.append(([[p[0] - ox, p[1] - oy, p[2]] for p in tri], int(material)))
    return out


def placements(index):
    """The bsp stage's placed meshes: (selected references, omitted record, profiles by mesh)."""
    from prepare_mesh_bsp import DRESSING_EXCLUDED
    from prepare_quake import CENTRE, SCALE
    from scenery_selection import select_runtime_refs
    from static_lod import rock_profile
    from surface_flatten import load_profiles
    selected, report = select_runtime_refs(index, CENTRE, SCALE, 736)
    kept, omitted = [], []
    for ref in selected:
        source = index['models'][ref['model_index']]['source']
        term = next((t for t in DRESSING_EXCLUDED if t in source), None)
        if term:
            omitted.append({'reference': ref['number'], 'model': source,
                            'reason': 'dressing excluded by the mesh converter (%s)' % term})
        else:
            kept.append(dict(ref))
    profiles = {name: profile for group in index.get('groups', {}).values()
                for name, profile in group.get('visual_profiles', {}).items()}
    flatten = load_profiles(scene_kind='exterior')
    for mi in dict.fromkeys(r['model_index'] for r in kept):
        model = index['models'][mi]
        profiles.setdefault(model['source'], rock_profile(model['source'], model['triangles']))
        if model['source'] in flatten:
            profiles[model['source']] = {**profiles[model['source']], 'flatten': flatten[model['source']]}
    return kept, {'selected_groups': report['selected_groups'], 'omitted': report['omitted'] + omitted}, profiles


def ground_textures(town_wad, materials, data=None, palette=None):
    """{'gN': miptex, '*water': miptex}: the scene stage's town.wad for its own materials; a material
    only the canonical LAND around it uses is made as the world's terrain makes it
    (prepare_world_regions.ground_textures, with the build's palette)."""
    from chim.build import wad_lumps
    lumps = wad_lumps(Path(town_wad).read_bytes())
    out = {k: v for k, v in lumps.items() if k == '*water' or (k.startswith('g') and int(k[1:]) in materials)}
    missing = sorted(m for m in materials if 'g%d' % m not in lumps)
    if missing:
        if data is None:
            raise ValueError('Seyda ground materials without a texture in town.wad: '
                             + ', '.join('g%d' % m for m in missing))
        from prepare_world_regions import ground_textures as world_ground
        out.update(world_ground(data, missing, palette))
    return out


def opening_barrel(data, work, barrel):
    """The tutorial barrel exported as prepare_opening_refs exports it (its own scenery archive):
    (scenery index, archive path)."""
    from prepare_quake import CENTRE
    from prepare_scenery import export_refs
    parts = Path(work) / 'opening-barrel-source'
    if not (parts / 'scenery-index.json').is_file():
        group = 'opening_barrel'
        export_refs(data, parts, [dict(barrel, scene_groups=[group])], {group: {'references': [barrel['number']]}},
                    [*CENTRE, 0], 4096, 32, {'scope': 'authored tutorial barrel'})
    return json.loads((parts / 'scenery-index.json').read_text(encoding='utf-8')), parts / 'scenery.mwpak'


def prepare_area(legacy, data, work, pal_bytes, qbsp, jobs, cache, timer, settings_override, rebuild_meshes,
                 mesh_occluders, harvest_set, flora):
    """Seyda Neen's frame input, source section, parity record and mesh count (chim.build.build_areas)."""
    from chim.build import frame_input, mesh_fingerprint, mesh_unit
    from chim.ground import TriangleGround
    from chim.terrain import TERRAIN_CEILING, WATER_LEVEL
    from chim.units import fingerprint, run_units
    from import_town import TERRAIN_FLOOR
    from prepare_quake import CENTRE, SCALE
    from surface_flatten import mount_references
    from visual_offsets import apply_visual_offsets
    import time
    if legacy is None:
        raise ValueError('The CHIM Seyda Neen frame needs the legacy run folder (--legacy-run): its terrain audit, '
                         'scenery and scene stage')
    legacy = Path(legacy)
    for need in ('work/generated/seyda-neen/terrain-source.json', 'scenery/scenery-index.json',
                 'scenery/scenery.mwpak', 'alias-scene/town.wad', 'world-survey/terrain-source.npz'):
        if not (legacy / need).is_file():
            raise ValueError('Legacy run folder lacks %s (run the setup, terrain, scenery, scene and world-survey '
                             'stages first)' % need)
    grain = (settings_override or {}).get('grain', 256)
    with timer.section('source stage'):
        index = json.loads((legacy / 'scenery/scenery-index.json').read_text(encoding='utf-8'))
        selected, omitted, profiles = placements(index)
    archive = legacy / 'scenery/scenery.mwpak'
    items = []
    used = list(dict.fromkeys(r['model_index'] for r in selected))
    for mi in used:
        model = index['models'][mi]
        profile = profiles.get(model['source'], {})
        fp = mesh_fingerprint(model, profile, index['textures'])
        if model['source'] in rebuild_meshes:
            fp = fingerprint('mesh', fp, 'rebuild', time.time_ns())
        items.append((fp, (mi, model, profile, archive, index['textures'])))
    with timer.section('meshes'):
        prepared = dict(zip(used, run_units('mesh', items, mesh_unit, jobs, cache)))
    mesh_fps = {mi: fp for mi, (fp, _) in zip(used, items)}
    mount_references(index, selected, prepared, CENTRE, SCALE)
    apply_visual_offsets(index, selected)
    parity = {'harvest_removed': [], 'town_flora_added': [], 'omitted': omitted['omitted']}
    # Town flora as the image installs it into the region maps (install_town_flora with the region
    # layout's entries at the town origin): meshes and the solid sprites' collision as placements;
    # the sprites themselves are point entities of the region maps that the frame map carries.
    models, textures = list(index['models']), list(index['textures'])
    with timer.section('opening references'):
        from prepare_opening_refs import BARREL, opening_references
        from static_lod import rock_profile
        _, wanted, disabled = opening_references(data)
        hidden = {r['number'] for r in wanted if r['id'].casefold() in disabled}
        for r in selected:
            if r['number'] in hidden:
                r['_story_hidden'] = True
        barrel = next(r for r in wanted if r['id'].casefold() == BARREL)
        if barrel['number'] not in {r['number'] for r in selected}:
            bindex, barchive = opening_barrel(data, work, barrel)
            base = len(textures)
            textures += bindex['textures']
            items, added = [], {}
            for ref in bindex['references']:
                model = bindex['models'][ref['model_index']]
                if ref['model_index'] not in added:
                    profile = rock_profile(model['source'], model['triangles'])
                    fp = fingerprint('mesh', 'opening', mesh_fingerprint(model, profile, bindex['textures']))
                    items.append((fp, (ref['model_index'], model, profile, barchive, bindex['textures'])))
                    added[ref['model_index']] = len(models)
                    models.append(dict(model, _profile=profile, _archive=str(barchive),
                                       materials=[dict(m, texture_index=None if m.get('texture_index') is None
                                                       else m['texture_index'] + base) for m in model['materials']]))
            for (fp, task), result in zip(items, run_units('mesh', items, mesh_unit, jobs, cache)):
                prepared[added[task[0]]] = result
                mesh_fps[added[task[0]]] = fp
            for ref in bindex['references']:
                selected.append(dict(ref, model_index=added[ref['model_index']]))
        parity['opening'] = {'story_hidden': sorted(hidden & {r['number'] for r in selected}),
                             'barrel': barrel['number']}
    with timer.section('town flora'):
        if flora:
            from chim.build import add_town_flora, town_flora
            from prepare_seyda_regions import regions as layout
            origin = [CENTRE[0] * SCALE, CENTRE[1] * SCALE, 0.0]
            found = town_flora(AREA, flora, {r['number'] for r in selected},
                               [{**e, 'origin': origin} for e in layout()])
            if found:
                parity['town_flora_added'] = add_town_flora(found, flora, models, textures, prepared, mesh_fps,
                                                            selected, jobs, cache)
    if harvest_set:
        removed = harvest_set & {r['number'] for r in selected}
        selected = [r for r in selected if r['number'] not in removed]
        parity['harvest_removed'] = sorted(removed)
    with timer.section('ground samples'):
        grids = json.loads((legacy / 'work/generated/seyda-neen/terrain-source.json').read_text(encoding='utf-8'))
        low, high = frame_box(grain)
        size = ((high[0] - low[0]) // TILE, (high[1] - low[1]) // TILE)
        canonical = canonical_terrain(legacy / 'world-survey', grids)
        ground = TriangleGround(ground_triangles(grids, low, high, canonical), TILE, low, size)
        materials = {m for items_ in ground.tiles.values() for _, m in items_}
        ground_tex = ground_textures(legacy / 'alias-scene/town.wad', materials, data, pal_bytes)
    frame = {'cell': source_cell(), 'centre': tuple(float(v) for v in CENTRE),
             'low': (float(low[0]), float(low[1])), 'span': (high[0] - low[0], high[1] - low[1])}
    spec = frame_input(frame=frame, centre=CENTRE, models=models, references=selected,
                       prepared=prepared, profiles=profiles, mesh_fps=mesh_fps, texture_records=textures,
                       archive=archive, palette=pal_bytes, heights=None, materials=None, step=TILE,
                       floor=TERRAIN_FLOOR, ceiling=TERRAIN_CEILING, ground_textures=ground_tex, qbsp=qbsp,
                       collision_cache=Path(work) / 'collision-cache', jobs=jobs, cache=cache, timer=timer,
                       settings=settings_override, mesh_occluders=mesh_occluders, ground=ground)
    doors = [[(r['position'][0] - CENTRE[0]) * SCALE, (r['position'][1] - CENTRE[1]) * SCALE]
             for r in selected if r.get('type') == 'DOOR' and r.get('destination')]
    section = {'town': AREA, 'cell': list(frame['cell']),
               'placements': [{'ref': r['number'], 'cell': list(r.get('cell') or [])} for r in selected],
               'doors': doors, 'terrain_step': TILE, 'terrain_low': [low[0], low[1]],
               'terrain_tiles': size[0] * size[1], 'water_level': WATER_LEVEL,
               'terrain_size': list(size), 'terrain_triangles': ground.rows(),
               'story_hidden': sorted(r['number'] for r in selected if r.get('_story_hidden'))}
    return spec, section, parity, len(prepared)
