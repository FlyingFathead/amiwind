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


def owned_world_box(root=None):
    """Original-cell core, excluding terrain-only apron (unique owner selection)."""
    settings = _config(root)
    from town_grid import owned_bounds
    low, high = owned_bounds(settings)
    c = settings['centre']
    return c[0]+4*low[0], c[1]+4*low[1], c[0]+4*high[0], c[1]+4*high[1]


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


KELP_MESHES = frozenset('meshes/f/flora_kelp_%02d.nif' % i for i in (1, 2, 3, 4))


def added_dressing_refs(index, selected):
    """Original kelp retained in CHIM; these meshes have no flora sprite overlay."""
    return sorted(r['number'] for r in selected
                  if index['models'][r['model_index']]['source'].replace(chr(92), '/').casefold() in KELP_MESHES)


def check_dressing_additions(index, declared):
    """Bind the entity-stage parity additions to the same original carrier selection."""
    selected, _, _ = placements(index)
    expected = added_dressing_refs(index, selected)
    if sorted(declared) != expected:
        raise ValueError('CHIM kelp additions differ from original scenery selection')
    return expected


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
        if term and source.replace(chr(92), '/').casefold() not in KELP_MESHES:
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


def opening_reference(ref, audited):
    """Bind the opening exporter to its exact original CELL before capture.

    Older barrel source indices omit CELL. Recover only that missing field
    from the original audit; every other identity and transform must agree.
    """
    from chim.ownership import original
    expected = original(audited)
    actual = original(ref)
    if not actual['cell']:
        actual['cell'] = expected['cell']
    if actual != expected or len(expected['cell']) != 2:
        raise ValueError('Opening reference differs from original audit')
    return dict(ref, cell=list(expected['cell']))


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



def write_source_metadata(legacy, work, selected, harvest_set=(), settings=None):
    """Bind this direct source path to original core cells and audited references.

    Scenery alone omits actors and other unsupported types. Retain every
    original reference whose physical origin is in the core, plus selected
    external dependencies. Separate harvest handling is not static placement
    or proof of gameplay acceptance. This writes metadata, never geometry.
    """
    import hashlib
    from town_grid import audit_radius, reference_ownership
    settings = _config() if settings is None else settings
    audit_radius(settings)
    legacy, work = Path(legacy), Path(work)
    names = ('work/generated/seyda-neen/audit.json',
             'work/generated/seyda-neen/placements.json', 'scenery/scenery-index.json')
    raw = {name: (legacy / name).read_bytes() for name in names}
    area = json.loads(raw[names[0]])['area']
    if (area.get('center') != settings['source_cell'] or
            area.get('radius_cells') != settings['source_radius']):
        raise ValueError('Seyda original-reference audit scope differs from the source config')
    low, high = settings['owned_cells']
    core = {(x, y) for x in range(low[0], high[0]) for y in range(low[1], high[1])}
    audited = [(c['x'], c['y']) for c in area['cells']]
    if len(set(audited)) != len(audited) or not core <= set(audited):
        raise ValueError('Seyda original-reference audit omits or repeats a core cell')
    original = json.loads(raw[names[1]])
    identity = lambda ref: (ref.get('master', 'Morrowind.esm'), ref['number'])
    refs = {identity(ref): ref for ref in original}
    if len(refs) != len(original):
        raise ValueError('Duplicate original reference in Seyda audit')
    from collections import Counter
    declared_counts = Counter(tuple(ref['cell']) for ref in original)
    if not set(declared_counts) <= set(audited) or any(
            type(cell.get('references')) is not int or cell['references'] < 0 or
            cell['references'] != declared_counts[(cell['x'], cell['y'])] for cell in area['cells']):
        raise ValueError('Seyda original-reference audit counts differ from the reference list')
    selected_ids = {identity(ref) for ref in selected}
    if len(selected_ids) != len(selected) or not selected_ids <= set(refs):
        raise ValueError('Seyda placement has a duplicate or unaudited original identity')
    physical = lambda ref: tuple(math.floor(ref['position'][k] / 8192) for k in range(2))
    core_ids = {key for key, ref in refs.items() if physical(ref) in core}
    retained = sorted(core_ids | selected_ids)
    # harvest_set is the established master-reference-number set. Only core
    # references participate here; unrelated outer audit cells are not owners.
    harvest = {key for key in core_ids - selected_ids if key[1] in harvest_set}
    catalogue = {'references': [refs[key] for key in retained],
                 'deferred': [refs[key] for key in retained if key not in selected_ids | harvest],
                 'separate_gameplay': {'harvest': [refs[key] for key in sorted(harvest)]},
                 'deferred_basis': 'Original references not represented as static CHIM placements or separate harvest input; actor/gameplay acceptance is independent.'}
    catalogue['ownership'] = reference_ownership(catalogue['references'], settings)
    receipt = {'geometry': {key: settings[key] for key in
                           ('source_cell', 'source_radius', 'centre', 'scale', 'bounds', 'owned_cells')},
               'source_kind': 'seyda-audited-original-references',
               'files': {name: hashlib.sha256(data).hexdigest() for name, data in raw.items()},
               'selected_identity_sha256': hashlib.sha256(json.dumps(sorted(selected_ids)).encode()).hexdigest(),
               'acceptance': 'Source metadata only; conversion gates, native play and shipment are separate.'}
    work.mkdir(parents=True, exist_ok=True)
    for name, value in (('source-receipt.json', receipt), ('source-catalogue.json', catalogue)):
        (work / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')
    return receipt, catalogue



def _authored_collision_packet(task):
    """Read the same original NIF as the carrier, retaining its authored hull."""
    import hashlib
    from prepare_scenery import _read_model
    model, path, extent = task
    name, raw, result, collision, error = _read_model((model['source'], path, extent, 'root_node'))
    if error or collision is None:
        raise ValueError('Missing authored CHIM collision: %s: %s' % (name, error))
    if hashlib.sha256(raw).hexdigest() != model['source_sha256'] or \
            hashlib.sha256(result[0][0]).hexdigest() != model['sha256']:
        raise ValueError('Authored CHIM collision source differs from scenery: ' + name)
    return collision


def retain_authored_collision(data, index, archive, selected, work, jobs):
    """Supplement a legacy carrier's omitted RootCollisionNode for CHIM only.

    A source carrier can have exported the visible mesh without its authored
    collision. Adjacent CHIM frames retain that collision, so the same original
    reference must do so here too. Original carrier bytes and visual packets
    remain unchanged; a separate private archive appends only verified hulls.
    """
    import copy
    import hashlib
    from build_parallel import ordered_map
    from mwad.audit import BSA
    from mwad.paths import child_ci, ensure_external
    from mwad.scene import unpack_geometry
    used = sorted({r['model_index'] for r in selected})
    missing = [i for i in used if not index['models'][i].get('collision') and
               any(s.get('reason') == 'collision_node' for s in index['models'][i].get('skipped_shapes', []))]
    if not missing:
        return index, Path(archive)
    bsa = BSA(child_ci(data, 'Morrowind.bsa'))
    tasks = [(index['models'][i], bsa.path, bsa.entries[index['models'][i]['source']]) for i in missing]
    packets = list(ordered_map(_authored_collision_packet, tasks, min(max(1, jobs), len(tasks))))
    raw = bytearray(Path(archive).read_bytes())
    base_hash = hashlib.sha256(raw).hexdigest()
    result = copy.deepcopy(index)
    appended = []
    for i, (packet, _, bounds, skipped) in zip(missing, packets):
        v, faces, _ = unpack_geometry(packet)
        raw.extend(bytes((-len(raw)) % 512))
        record = {'source': 'NIF RootCollisionNode', 'bounds': bounds,
                  'vertices': len(v), 'triangles': len(faces), 'skipped_shapes': skipped,
                  'offset': len(raw), 'bytes': len(packet), 'sha256': hashlib.sha256(packet).hexdigest()}
        raw.extend(packet)
        result['models'][i]['collision'] = record
        appended.append({'source': result['models'][i]['source'], **record})
    digest = hashlib.sha256(raw).hexdigest()
    out = ensure_external(Path(work) / ('authored-collision-' + digest[:16]), 'CHIM authored collision')
    out.mkdir(parents=True, exist_ok=True)
    target = out / 'scenery.mwpak'
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError('Existing CHIM collision supplement differs')
    else:
        with target.open('xb') as stream:
            stream.write(raw)
    receipt = {'format': 'aw-chim-authored-collision-1', 'carrier_sha256': base_hash,
               'archive_sha256': digest, 'models': appended,
               'scope': 'Original source hulls only; native and package acceptance are separate.'}
    receipt_path = out / 'source.json'
    text = json.dumps(receipt, indent=2) + '\n'
    if receipt_path.exists():
        if receipt_path.read_text(encoding='utf-8') != text:
            raise ValueError('Existing CHIM collision supplement receipt differs')
    else:
        receipt_path.write_text(text, encoding='utf-8', newline='\n')
    return result, target


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
    for need in ('work/generated/seyda-neen/terrain-source.json',
                 'work/generated/seyda-neen/audit.json', 'work/generated/seyda-neen/placements.json',
                 'scenery/scenery-index.json',
                 'scenery/scenery.mwpak', 'alias-scene/town.wad', 'world-survey/terrain-source.npz'):
        if not (legacy / need).is_file():
            raise ValueError('Legacy run folder lacks %s (run the setup, terrain, scenery, scene and world-survey '
                             'stages first)' % need)
    grain = (settings_override or {}).get('grain', 256)
    with timer.section('source stage'):
        index = json.loads((legacy / 'scenery/scenery-index.json').read_text(encoding='utf-8'))
        selected, omitted, profiles = placements(index)
        from chim.ownership import capture
        selected = [capture(r) for r in selected]
    archive = legacy / 'scenery/scenery.mwpak'
    with timer.section('authored collision source'):
        index, archive = retain_authored_collision(data, index, archive, selected, work, jobs)
    items = []
    used = list(dict.fromkeys(r['model_index'] for r in selected))
    for mi in used:
        model = index['models'][mi]
        # the mesh's CHIM mesh method (config/mesh-methods.json), as every CHIM area applies it
        from chim.build import apply_mesh_method
        profile = profiles[model['source']] = apply_mesh_method(profiles.get(model['source'], {}), model['source'],
                                                                settings_override)
        fp = mesh_fingerprint(model, profile, index['textures'])
        if model['source'] in rebuild_meshes:
            fp = fingerprint('mesh', fp, 'rebuild', time.time_ns())
        items.append((fp, (mi, model, profile, archive, index['textures'])))
    with timer.section('meshes'):
        prepared = dict(zip(used, run_units('mesh', items, mesh_unit, jobs, cache)))
    mesh_fps = {mi: fp for mi, (fp, _) in zip(used, items)}
    mount_references(index, selected, prepared, CENTRE, SCALE)
    apply_visual_offsets(index, selected)
    parity = {'harvest_removed': [], 'town_flora_added': [], 'omitted': omitted['omitted'],
              'source_dressing_added': added_dressing_refs(index, selected)}
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
            audit = json.loads((legacy / 'work/generated/seyda-neen/placements.json').read_text())
            originals = {r['number']: r for r in audit}
            for ref in bindex['references']:
                ref = opening_reference(ref, originals[ref['number']])
                selected.append(dict(capture(ref), model_index=added[ref['model_index']]))
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
    from town_grid import owned_bounds
    frame = {'owned': owned_bounds(_config()), 'cell': source_cell(), 'centre': tuple(float(v) for v in CENTRE),
             'low': (float(low[0]), float(low[1])), 'span': (high[0] - low[0], high[1] - low[1])}
    spec = frame_input(frame=frame, centre=CENTRE, models=models, references=selected,
                       prepared=prepared, profiles=profiles, mesh_fps=mesh_fps, texture_records=textures,
                       archive=archive, palette=pal_bytes, heights=None, materials=None, step=TILE,
                       floor=TERRAIN_FLOOR, ceiling=TERRAIN_CEILING, ground_textures=ground_tex, qbsp=qbsp,
                       collision_cache=Path(work) / 'collision-cache', jobs=jobs, cache=cache, timer=timer,
                       settings=settings_override, mesh_occluders=mesh_occluders, ground=ground)
    doors = [[(r['position'][0] - CENTRE[0]) * SCALE, (r['position'][1] - CENTRE[1]) * SCALE]
             for r in selected if r.get('type') == 'DOOR' and r.get('destination')]
    from town_grid import reference_ownership
    section = {'town': AREA, 'cell': list(frame['cell']),
               'reference_ownership': reference_ownership(selected, _config()),
               'placements': [{'ref': r['number'], 'cell': list(r.get('cell') or [])} for r in selected],
               'doors': doors, 'terrain_step': TILE, 'terrain_low': [low[0], low[1]],
               'terrain_tiles': size[0] * size[1], 'water_level': WATER_LEVEL,
               'terrain_size': list(size), 'terrain_triangles': ground.rows(),
               'story_hidden': sorted(r['number'] for r in selected if r.get('_story_hidden'))}
    from chim.ownership import manifest
    section['frame_ownership'] = manifest(spec, selected)
    write_source_metadata(legacy, work, selected, harvest_set)
    return spec, section, parity, len(prepared)
