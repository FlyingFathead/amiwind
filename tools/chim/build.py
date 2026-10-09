# SPDX-License-Identifier: GPL-3.0-only
"""CHIM builder for one converted town's exterior (format 0.2: Balmora's 3 x 3 cell frame).

From your own Morrowind files, with the legacy converter's source stage and
geometry functions (one shared implementation):

1. source: import_town.collect (audit of the town's cells, every placed
   static exported to the scenery archive), the town's visual profiles;
2. units, each fingerprinted, cached and built in parallel (chim.units):
   meshes (prepare_mesh_bsp._prepare_model), model variants (mesh, scale,
   tilt, flattening and visual offset: the legacy variant key without
   lighting; _prepare_placement and the CHIM model writer), textures, chunk
   terrain, visibility rows;
3. chim.world writes the index, the frame file and the sector files; chim-source.json records what
   the validator must find (every placement, the ground heights, the doors).

Nothing derived from your files is part of this repository.
"""
import hashlib
import json
import math
import os
import struct
import time
from pathlib import Path

import numpy as np

from chim import BUILDER, CHIM_VERSION, FORMAT_VERSION
from chim.terrain import TERRAIN_LIGHT, WATER_LEVEL, terrain_unit
from chim.texfx import apply_effects, load_effect
from chim.units import Timer, UnitCache, fingerprint, run_units
from chim.world import build_frames, write_json


def _log(msg):
    print('[chim] ' + msg, flush=True)


def wad_lumps(wad):
    """{name: data} of a WAD2 file (prepare_quake.wad)."""
    magic, count, table = struct.unpack_from('<4sii', wad)
    if magic != b'WAD2':
        raise ValueError('Not a WAD2 file')
    out = {}
    for i in range(count):
        pos, disk, size, kind, comp, _, name = struct.unpack_from('<iiiBBH16s', wad, table + 32 * i)
        out[name.split(b'\0')[0].decode('ascii')] = wad[pos:pos + disk]
    return out


# local units: placements of wider models are cut by chunk (chim.cut). 0 = off by default until the cut is
# measured on Balmora and Seyda Neen (their rings have little headroom); an area turns it on with its
# settings (cut_models_over, e.g. 512: district-size bodies such as the Vivec cantons).
CUT_MODELS_OVER = 0.0


def variant_name(model, key):
    """Readable unique name: mesh, scale, tilt (and yaw when tilted), flattening, visual offset."""
    stem = model['source'].replace('\\', '/')
    stem = stem[len('meshes/'):] if stem.startswith('meshes/') else stem
    stem = stem[:-4] if stem.lower().endswith('.nif') else stem
    _, scale, r0, r1, *rest = key[:-2]
    name = '%s@s%g' % (stem.lower(), scale)
    if r0 or r1 or rest:
        name += '@t%.6g,%.6g' % (r0, r1) + (',%.6g' % rest[0] if rest else '')
    if key[-2]:
        name += '@f%g' % key[-2]
    if any(key[-1]):
        name += '@v%g,%g,%g' % key[-1]
    return name


def variant_key(ref):
    """The legacy variant identity without lighting (prepare_mesh_bsp placement groups)."""
    from prepare_mesh_bsp import _instance_key
    from visual_offsets import visual_key
    return (*_instance_key(ref, None), round(ref.get('_flatten_shift', 0), 5), visual_key(ref))


def sky_bank_textures(textures, palette):
    """Every texture's pixels moved off the sky bank (sky_palette_overlay.remap_miptex), as the image's
    sky overlay moves the region maps' pixels before it repaints those palette entries as sky colours
    (CHIM-TEXTURE-SPECKS-33: left on them, CHIM texels showed as bright specks). Applied when the
    palette passes the overlay's own guard (each banked colour within two units of its replacement),
    so the translation never changes a colour visibly, banked image or not."""
    from sky_palette_overlay import bank_safe, remap_miptex
    if not bank_safe(palette):
        return textures
    return {k: dict(v, miptex=remap_miptex(v['miptex'])) for k, v in textures.items()}


def texture_source(texture_records, key):
    """The source texture path of a model texture key (('model', texture index, size, diffuse, glow);
    flattened panels have 'flatten' for the index), else None: texture effects (chim.texfx) match their
    targets against it."""
    if len(key) > 1 and isinstance(key[1], int) and 0 <= key[1] < len(texture_records):
        return texture_records[key[1]].get('source')
    return None


def mesh_unit(task):
    """prepare_mesh_bsp._prepare_model as a unit worker (the prepared mesh only)."""
    from prepare_mesh_bsp import _prepare_model
    return _prepare_model(task)[1]


def mesh_fingerprint(model, profile, texture_records):
    """A mesh unit: its scenery record (mesh and collision hashes, materials), profile, used textures."""
    used = sorted({m.get('texture_index') for m in model['materials'] if m.get('texture_index') is not None})
    return fingerprint('mesh', model, profile, [texture_records[i].get('sha256') for i in used])


def build_frame(out, **kw):
    """A world of one frame from prepared inputs (frame_input, then chim.world.build_frames); the receipt."""
    spec = frame_input(**kw)
    receipt = build_frames(out, [spec], kw.get('settings'), TERRAIN_LIGHT, jobs=kw.get('jobs', 1),
                           cache=kw.get('cache'), timer=kw.get('timer'))
    receipt['collision_union_fallbacks'] = spec['fallbacks']
    return receipt


def frame_input(*, frame, centre, models, references, prepared, profiles, mesh_fps, texture_records,
                archive, palette, heights, materials, step, floor, ceiling, ground_textures,
                qbsp=None, collision_cache=None, jobs=1, cache=None, timer=None, settings=None,
                mesh_occluders=True, ground=None):
    """Units of one frame from prepared inputs (shared by the area build and the tests): the frame
    input of chim.world.build_frames, plus 'fallbacks' (meshes whose collision union fell back).

    references: placed statics (scenery index rows after window mounting and
    visual offsets); prepared: {model index: _prepare_model result};
    profiles: {mesh source: converter profile}; mesh_fps: {model index:
    fingerprint}; heights: tile corner heights over the frame (rows by y);
    materials: tile materials (rows by y); ground_textures: {texture name
    ('gN', '*water'): miptex bytes}; ground (format 0.5): a chim.ground.TriangleGround over
    the frame's tiles, the converter's own triangles, instead of heights and materials.
    Returns the receipt."""
    from chim.models import texture_unit, variant_unit, yaw_degrees
    timer = timer or Timer()
    cache = cache or UnitCache()
    firsts = {}
    for ref in references:
        firsts.setdefault(variant_key(ref), ref)
    order = list(firsts)
    qbsp_hash = hashlib.sha256(Path(qbsp).read_bytes()).hexdigest() if qbsp else None
    with timer.section('model variants'):
        items = []
        for k in order:
            ref = firsts[k]
            mi = ref['model_index']
            model = models[mi]
            profile = model['_profile'] if '_profile' in model else profiles[model['source']]
            size = profile.get('texture_size', 64)
            exact = bool(prepared[mi][4].get('collision_bevels'))
            task = {'ref': ref, 'data': prepared[mi], 'texsize': size, 'centre': list(centre), 'model': model,
                    'exact': exact, 'hollow': bool(profile.get('hollow_collision')),
                    'qbsp': str(qbsp) if qbsp else None,
                    'collision_cache': str(collision_cache) if collision_cache else None}
            # the hull mode changes the model's collision bytes (routed_hull): part of its identity
            from mesh_geometry_env import model_hull_mode
            fp = fingerprint('variant', mesh_fps[mi], list(k), size, exact, task['hollow'], qbsp_hash, model_hull_mode(),
                             model.get('flames'), model['materials'], ref['scale'], ref['rotation_radians'],
                             ref.get('_flatten_shift', 0), ref.get('_visual_offset', [0, 0, 0]))
            items.append((fp, task))
        results = run_units('variant', items, variant_unit, jobs, cache)
        variant_fps = {k: fp for k, (fp, _) in zip(order, items)}
        variant_tasks = {k: task for k, (_, task) in zip(order, items)}
    variants, names, fallbacks = {}, set(), []
    for k, res in zip(order, results):
        model = models[firsts[k]['model_index']]
        name = variant_name(model, k)
        n = 1
        while name in names:
            n += 1
            name = '%s#%d' % (variant_name(model, k), n)
        names.add(name)
        if res.get('collision_fallback'):
            fallbacks.append(model['source'])
        variants[k] = dict(res, name=name)
    with timer.section('textures'):
        tasks = {}
        for k, res in zip(order, results):
            mi = firsts[k]['model_index']
            model = models[mi]
            for tkey, material in res['materials'].items():
                if tkey in tasks:
                    continue
                flat = tkey[1] == 'flatten'
                kind, glow = ('flatten', 0) if flat else ('surface', tkey[4])
                ti = None if flat else tkey[1]
                flat_rgb = prepared[mi][4].get('_flat_rgb') if flat else None
                source_archive = model.get('_archive', archive)
                task = {'archive': str(source_archive) if source_archive else None, 'textures': texture_records,
                        'model': model,
                        'material': material, 'size': tkey[3] if flat else tkey[2], 'palette': palette,
                        'flat_rgb': flat_rgb, 'kind': kind, 'glow': glow}
                fp = fingerprint('texture', list(tkey), texture_records[ti].get('sha256') if ti is not None else None,
                                 flat_rgb, palette)
                tasks[tkey] = (fp, task)
        keys = list(tasks)
        built = run_units('texture', [tasks[k] for k in keys], texture_unit, jobs, cache)
    textures = {k: {'identity': '|'.join(map(str, k)), 'miptex': r['miptex'], 'size': r['size'],
                    'engine': (r['kind'], r['glow']), 'source': texture_source(texture_records, k)}
                for k, r in zip(keys, built)}
    for name, mip in ground_textures.items():
        w, h = struct.unpack_from('<II', mip, 16)
        textures[('ground', name)] = {'identity': 'ground|' + name, 'miptex': mip, 'size': (w, h), 'engine': None,
                                      'source': None}
    textures = sky_bank_textures(textures, palette)
    low = frame['low']
    g = (settings or {}).get('grain', 256)
    with timer.section('chunk terrain'):
        nx, ny = int(frame['span'][0] // g), int(frame['span'][1] // g)
        per = int(g // step)
        if per * step != g:
            raise ValueError('Chunk grain must be a whole number of terrain tiles')
        chunks = [(cx, cy) for cx in range(nx) for cy in range(ny)]
        items = []
        tiles_x, tiles_y = nx * per, ny * per
        for cx, cy in chunks:
            # The collision box: the chunk and one ring of tiles around it inside the frame
            # (the standing box reaches less than a tile; seamless hull 1, format 0.4).
            i0, j0 = max(0, cx * per - 1), max(0, cy * per - 1)
            i1, j1 = min(tiles_x, (cx + 1) * per + 1), min(tiles_y, (cy + 1) * per + 1)
            box = (low[0] + cx * g, low[1] + cy * g, low[0] + (cx + 1) * g, low[1] + (cy + 1) * g)
            cbox = (low[0] + i0 * step, low[1] + j0 * step, low[0] + i1 * step, low[1] + j1 * step)
            if ground is None:
                hs = [row[i0:i1 + 1] for row in heights[j0:j1 + 1]]
                ms = [row[cx * per:(cx + 1) * per] for row in materials[cy * per:(cy + 1) * per]]
                task = {'box': box, 'step': step, 'heights': hs, 'materials': ms, 'floor': floor,
                        'ceiling': ceiling, 'water': WATER_LEVEL, 'light': TERRAIN_LIGHT, 'collision_box': cbox}
            else:
                # format 0.5: the tiles' own triangles (the chunk and the ring of the collision box)
                tris = [[low[0] + i * step, low[1] + j * step,
                         [[round(v, 6) for p in t for v in p] + [int(m)] for t, m in ground.tile_list(i, j)]]
                        for j in range(j0, j1) for i in range(i0, i1)]
                task = {'box': box, 'step': step, 'heights': None, 'materials': None, 'triangles': tris,
                        'floor': floor, 'ceiling': ceiling, 'water': WATER_LEVEL, 'light': TERRAIN_LIGHT,
                        'collision_box': cbox}
            # Irregular ground (many small prisms per chunk) gets the standing hull compiled by qbsp
            # (CHIM-SEYDA-MEMORY-33); a regular grid keeps the routed chains (format 0.4), which hold
            # it compactly and walk it exactly. Either is selectable (terrain_hull). The fingerprint
            # holds the compiler's bytes, not its path or the cache folder.
            hull = (settings or {}).get('terrain_hull') or ('compiled' if qbsp and ground is not None else 'routed')
            fp = fingerprint('terrain', task, hull, qbsp_hash if hull == 'compiled' else None)
            if hull != 'routed':
                task = dict(task, hull=hull, qbsp=str(qbsp), collision_cache=str(collision_cache))
            items.append((fp, task))
        terrain = dict(zip(chunks, run_units('terrain', items, terrain_unit, jobs, cache)))
    # Large-model cut (chim.cut): a placement whose model is wider than cut_models_over (default: one
    # chunk) is stored as one model per chunk it covers, so only its pieces in the ring are resident
    # (CHIM-ARENA-MEMORY-33). 512 (two chunks) cuts district-size bodies (Vivec cantons about 1,750 units,
    # the Ministry of Truth about 915) and keeps house-size models whole; 0 keeps every model whole.
    cut_over = float((settings or {}).get('cut_models_over', CUT_MODELS_OVER))
    cut_mode = (settings or {}).get('cut_mode', 'tiles')
    cuts, tiled = {}, {}
    if cut_over > 0 and cut_mode == 'tiles':
        # the model is cut once in its own frame; every placement of it places the shared tiles
        from chim.cut import tile_unit
        with timer.section('large-model cut'):
            items = []
            for k in order:
                v = variants[k]
                if max(v['hi'][0] - v['lo'][0], v['hi'][1] - v['lo'][1]) <= cut_over:
                    continue
                task = dict(variant_tasks[k], grain=g)
                task.pop('qbsp', None)
                task.pop('collision_cache', None)
                items.append((fingerprint('tiles', variant_fps[k], g), task))
            keys = [k for k in order if max(variants[k]['hi'][0] - variants[k]['lo'][0],
                                            variants[k]['hi'][1] - variants[k]['lo'][1]) > cut_over]
            for k, tiles in zip(keys, run_units('tiles', items, tile_unit, jobs, cache)):
                tiled[k] = tiles
                for t in tiles:
                    variants[('tile', k, *t['tile'])] = dict(t, name='%s@tile%d,%d' % (variants[k]['name'], *t['tile']),
                                                             collision_fallback=None)
    if cut_over > 0 and cut_mode != 'tiles':
        from chim.cut import cut_unit
        with timer.section('large-model cut'):
            items = []
            for ref in references:
                k = variant_key(ref)
                v = variants[k]
                if max(v['hi'][0] - v['lo'][0], v['hi'][1] - v['lo'][1]) <= cut_over:
                    continue
                origin = [float(x) for x in (np.array(ref['position']) - np.array([*centre, 0])) * 0.25]
                task = dict(variant_tasks[k], ref=ref, origin=origin, yaw=yaw_degrees(ref), low=list(low),
                            grain=g, nx=nx, ny=ny, cut_mode=(settings or {}).get('cut_mode', 'partition'))
                task.pop('qbsp', None)
                task.pop('collision_cache', None)
                fp = fingerprint('cut', variant_fps[k], origin, task['yaw'], list(low), g, nx, ny, ref['number'],
                                 task['cut_mode'])
                items.append((fp, task))
            for (_, task), pieces in zip(items, run_units('cut', items, cut_unit, jobs, cache)):
                cuts[task['ref']['number']] = (task['ref'], pieces)
    placements = []
    for ref in references:
        cell = tuple(ref.get('cell') or (math.floor(ref['position'][0] / 8192), math.floor(ref['position'][1] / 8192)))
        if variant_key(ref) in tiled:
            from chim.cut import piece_ref, rotation
            k = variant_key(ref)
            o = (np.array(ref['position']) - np.array([*centre, 0])) * 0.25
            R = rotation(yaw_degrees(ref))
            for index, t in enumerate(tiled[k], 1):
                row = {'ref': piece_ref(ref['number'], index), 'cell': cell,
                       'origin': tuple(float(v) for v in o + R @ np.array(t['centre'])), 'yaw': yaw_degrees(ref),
                       'variant': ('tile', k, *t['tile'])}
                if ref.get('_story_hidden'):
                    row['story_hidden'] = True
                placements.append(row)
            continue
        if ref['number'] in cuts:
            base = variants[variant_key(ref)]['name']
            from chim.cut import piece_ref
            for index, piece in enumerate(cuts[ref['number']][1], 1):
                key = ('cut', ref['number'], *piece['chunk'])
                variants[key] = dict(piece, name='%s@c%d#%d,%d' % (base, ref['number'], *piece['chunk']),
                                     collision_fallback=None, cut_of=ref['number'])
                row = {'ref': piece_ref(ref['number'], index), 'cell': cell, 'origin': tuple(piece['origin']),
                       'yaw': 0.0, 'variant': key}
                if ref.get('_story_hidden'):
                    row['story_hidden'] = True
                placements.append(row)
            continue
        origin = tuple(float(v) for v in (np.array(ref['position']) - np.array([*centre, 0])) * 0.25)
        row = {'ref': ref['number'], 'cell': cell, 'origin': origin, 'yaw': yaw_degrees(ref),
               'variant': variant_key(ref)}
        if ref.get('_story_hidden'):
            row['story_hidden'] = True       # format 0.5 (FLAG_STORY_HIDDEN); absent: the 0.4 record, unchanged
        placements.append(row)
    used = {p['variant'] for p in placements}
    variants = {k: v for k, v in variants.items() if k in used}     # a model only its cut placements used
    return {'frame': frame, 'placements': placements, 'variants': variants, 'textures': textures,
            'terrain': terrain, 'fallbacks': sorted(set(fallbacks)),
            'visibility': ({'heights': heights, 'step': step, 'low': tuple(low), 'mesh_occluders': mesh_occluders}
                           if ground is None else
                           {'triangles': [(t, m) for j in range(ground.size[1]) for i in range(ground.size[0])
                                          for t, m in ground.tile_list(i, j)],
                            'step': step, 'low': tuple(low), 'size': ground.size,
                            'mesh_occluders': mesh_occluders})}


def source_stage(data, work, jobs, settings):
    """import_town.collect, or its verified earlier result."""
    from import_town import collect, source_receipt
    if (work / 'source-receipt.json').is_file():
        if json.loads((work / 'source-receipt.json').read_text()) != source_receipt(data, settings):
            raise ValueError('Existing source stage was made from other inputs; use a new work folder')
        _log('source stage reused (inputs verified)')
        return json.loads((work / 'scenery/scenery-index.json').read_text())
    work.mkdir(parents=True, exist_ok=True)
    collect(data, work, jobs, settings)
    (work / 'source-receipt.json').write_text(json.dumps(source_receipt(data, settings), indent=2) + '\n')
    return json.loads((work / 'scenery/scenery-index.json').read_text())


def harvest_numbers(harvest, data_files):
    """Placements the harvest step makes harvestable: the image removes them as baked statics
    (harvest_build.clear_baked), so the CHIM world leaves them out (the same set)."""
    from harvest_build import source_placements
    return {r['number'] for r in source_placements(harvest, data_files)[2]}


def town_flora(town, flora, town_numbers, entries=None):
    """Town flora the image installs (install_town_flora: the same region entries,
    region_references and representation), minus what the town's scenery already places.

    Meshes become placements; a sprite (aw_flora, a point entity of the region maps that the
    frame map carries) becomes a collision-only placement when its source is solid, as the
    image's overlay adds a collision-only func_wall for it (prepare_world_flora). entries:
    the region entries (default install_town_flora.town_entries; Seyda Neen passes its own).
    Returns (flora scenery index, [references], {number: 'mesh' | 'collision_only'}) or None
    for a town without town flora."""
    from install_town_flora import town_entries
    from prepare_world_flora import effective_representation
    from world_scenery import region_references
    entries = town_entries(town) if entries is None else entries
    if entries is None:
        return None
    flora = Path(flora)
    index = json.loads((flora / 'source/scenery-index.json').read_text(encoding='utf-8'))
    receipt = json.loads((flora / 'tree-sprites.json').read_text(encoding='utf-8'))
    originals = {r['number']: r for r in receipt['placements']}
    picked = {}
    for entry in entries:
        for ref in region_references(index, entry):
            number = ref['number']
            if number in town_numbers or number in picked:
                continue
            original = originals[number]
            # region_references shifts z into the region's terrain frame; the CHIM frame keeps the original
            row = dict(ref, position=[*ref['position'][:2], ref['position'][2] + entry['origin'][2] / 0.25])
            row.update({k: original[k] for k in ('renderer_policy', 'requires_interaction', 'source_collision')})
            picked[number] = row
    modes = {}
    for n, r in picked.items():
        if effective_representation(r) != 'sprite':
            modes[n] = 'mesh'
        elif r['source_collision']['mode'] != 'nonsolid':
            modes[n] = 'collision_only'
    return index, [picked[n] for n in sorted(picked) if n in modes], modes


def add_town_flora(found, flora, models, textures, prepared, mesh_fps, selected, jobs, cache):
    """Append town_flora's result: its models (per mesh and mode, prepare_world_flora.mesh_profile),
    prepared meshes and placements. Returns the placed reference numbers."""
    from prepare_world_flora import mesh_profile
    findex, frefs, modes = found
    ftextures = len(textures)
    textures += findex['textures']
    farchive = Path(flora) / 'source/scenery.mwpak'
    fmodels, items = {}, []
    for mi, mode in sorted({(r['model_index'], modes[r['number']]) for r in frefs}):
        model = findex['models'][mi]
        profile = mesh_profile(model, [r for r in frefs if r['model_index'] == mi and modes[r['number']] == mode],
                               mode)
        fp = fingerprint('mesh', 'town flora', mesh_fingerprint(model, profile, findex['textures']))
        items.append((fp, (mi, model, profile, farchive, findex['textures'])))
        placed = dict(model, _profile=profile, _archive=str(farchive),
                      materials=[dict(m, texture_index=None if m.get('texture_index') is None
                                      else m['texture_index'] + ftextures) for m in model['materials']])
        if mode != 'mesh':
            placed['source'] = model['source'] + '#' + mode     # its own variants: collision only
        fmodels[(mi, mode)] = len(models)
        models.append(placed)
    keys = sorted(fmodels)
    for key, (fp, _), result in zip(keys, items, run_units('mesh', items, mesh_unit, jobs, cache)):
        prepared[fmodels[key]] = result
        mesh_fps[fmodels[key]] = fp
    for ref in frefs:
        selected.append(dict(ref, model_index=fmodels[(ref['model_index'], modes[ref['number']])]))
    return [r['number'] for r in frefs]


def build_town(town, data_files, out, palette, qbsp=None, jobs=None, settings_override=None, use_cache=True,
               rebuild_meshes=(), mesh_occluders=True, unit_cache=None, harvest=None, flora=None):
    """One town's world: build_areas([town], ...)."""
    return build_areas([town], data_files, out, palette, qbsp, jobs, settings_override, use_cache, rebuild_meshes,
                       mesh_occluders, unit_cache, harvest, flora)


def build_areas(areas, data_files, out, palette, qbsp=None, jobs=None, settings_override=None, use_cache=True,
                rebuild_meshes=(), mesh_occluders=True, unit_cache=None, harvest=None, flora=None, legacy_run=None,
                texture_effects=(), far_terrain=True):
    """One CHIM world holding a frame per area (town id of config/towns.json), stored once across them.

    rebuild_meshes: mesh sources whose units are built again (as after a converter change for them);
    unit_cache: folder of the unit cache (default OUT/work/chim-units), e.g. one kept between builds;
    harvest: the harvest step's output (its placements are left out, as the image removes them);
    flora: the world flora assets (the town flora the image installs is added, as meshes);
    legacy_run: the legacy builder's run folder, the source of Seyda Neen's frame (chim.seyda);
    texture_effects: effect files (.chimfx, chim.texfx) applied to the textures they target, in order,
    after the sky-bank translation (none by default);
    far_terrain: write each frame's far terrain layer, OUT/far/<cx>_<cy>.far (chim.far; on by default,
    False only for comparisons: the frame map then has no far land).
    Writes OUT/chim/, OUT/chim-source.json (a section per frame) and OUT/chim-receipt.json."""
    from build_jobs import resolve_jobs
    from mwad.paths import ensure_external, resolve_data_files
    if os.environ.get('AMIWIND_TEXINFO_SNAP'):
        raise ValueError('The CHIM builder does not support --texinfo-snap (format 0.2)')
    areas = list(dict.fromkeys(areas))
    if not areas:
        raise ValueError('No CHIM area')
    t0 = time.time()
    timer = Timer()
    data = resolve_data_files(data_files)
    out = ensure_external(out, 'CHIM output')
    out.mkdir(parents=True, exist_ok=True)
    jobs = resolve_jobs(jobs)
    cache = UnitCache((Path(unit_cache) if unit_cache else out / 'work' / 'chim-units') if use_cache else None)
    pal_bytes = Path(palette).read_bytes()
    harvest_set = harvest_numbers(harvest, data) if harvest else set()
    specs, sections, parity, meshes = [], [], {}, 0
    for town in areas:
        if town == 'seyda':
            from chim import seyda
            spec, section, parity[town], count = seyda.prepare_area(
                legacy_run, data, out / 'work' / town, pal_bytes, qbsp, jobs, cache, timer, settings_override,
                rebuild_meshes, mesh_occluders, harvest_set, flora)
        else:
            spec, section, parity[town], count = prepare_area(
                town, data, out / 'work' / town, pal_bytes, qbsp, jobs, cache, timer, settings_override,
                rebuild_meshes, mesh_occluders, harvest_set, flora)
        specs.append(spec)
        sections.append(section)
        meshes += count
    effects = [load_effect(path) for path in texture_effects]
    applied = []
    for spec in specs:
        spec['textures'], record = apply_effects(spec['textures'], effects, pal_bytes)
        applied.append(record)
    receipt = build_frames(out, specs, settings_override, TERRAIN_LIGHT, jobs=jobs, cache=cache, timer=timer)
    receipt['collision_union_fallbacks'] = sorted({m for s in specs for m in s['fallbacks']})
    # The frames' far terrain (chim.far): resident distant land, a sidecar of each frame map.
    with timer.section('far terrain'):
        from chim.far import write_layers
        receipt['far_terrain'] = write_layers(out, [s['frame'] for s in specs], data) if far_terrain else []
    source = {'builder': BUILDER, 'chim_version': CHIM_VERSION, 'world_format': '%d.%d' % FORMAT_VERSION,
              'areas': areas, 'frames': sections}
    write_json(out / 'chim-source.json', source)
    receipt.update(town=areas[0], areas=areas, source_placements=sum(len(s['placements']) for s in sections),
                   meshes=meshes, jobs=jobs, parity=parity[areas[0]] if len(areas) == 1 else parity,
                   rebuild_meshes=sorted(rebuild_meshes),
                   texture_effects=[{'name': e['name'], 'file': e['file'], 'sha256': e['sha256'],
                                     'textures': sorted({t for rec in applied for r in rec if r['name'] == e['name']
                                                         for t in r['textures']})} for e in effects],
                   units=cache.stats, timing=timer.report(), wall_seconds=round(time.time() - t0, 1))
    write_json(out / 'chim-receipt.json', receipt)
    _log('units: ' + ', '.join('%s %d built %d reused' % (k, v.get('built', 0), v.get('reused', 0))
                               for k, v in sorted(cache.stats.items())))
    _log('wrote %s (%.1f s wall, %.1f s CPU)' % (out / 'chim', time.time() - t0, timer.report()['cpu_seconds']))
    return receipt


def prepare_area(town, data, work, pal_bytes, qbsp, jobs, cache, timer, settings_override, rebuild_meshes,
                 mesh_occluders, harvest_set, flora):
    """One area's frame input, source section, parity record and mesh count (build_areas)."""
    from import_town import ground_assets, terrain_at, terrain_material, TERRAIN_CEILING, TERRAIN_FLOOR
    from prepare_quake import SCALE
    from surface_flatten import load_profiles, mount_references
    from town_config import load_settings, town_field
    from town_regions import visual_profile
    from visual_offsets import apply_visual_offsets
    settings = load_settings(town)
    with timer.section('source stage'):
        index = source_stage(data, work, jobs, settings)
    centre = settings['centre']
    # Profiles exactly as import_town.prepare and _append_meshes choose them.
    group = index['groups'][town_field(settings, 'visual_group')]['visual_profiles']
    flatten = load_profiles(scene_kind='exterior')
    profiles, items = {}, []
    archive = work / 'scenery/scenery.mwpak'
    for mi, model in enumerate(index['models']):
        profile = {**group[model['source']], **visual_profile(model['source'], model['triangles'])}
        if model['source'] in flatten:
            profile['flatten'] = flatten[model['source']]
        profiles[model['source']] = profile
        fp = mesh_fingerprint(model, profile, index['textures'])
        if model['source'] in rebuild_meshes:
            fp = fingerprint('mesh', fp, 'rebuild', time.time_ns())
        items.append((fp, (mi, model, profile, archive, index['textures'])))
    with timer.section('meshes'):
        prepared = dict(enumerate(run_units('mesh', items, mesh_unit, jobs, cache)))
    mesh_fps = {mi: fp for mi, (fp, _) in enumerate(items)}
    # The town's placements, as its legacy region maps hold them (town_regions.town_references): a
    # frame centred off the cell grid (Vivec's Arena) audits whole cells around it (CHIM-PAYLOAD-PARITY-33).
    from town_regions import town_references
    inside = set(town_references(index, settings))
    selected = [dict(r) for r in index['references'] if r['number'] in inside]
    mount_references(index, selected, prepared, centre, SCALE)
    apply_visual_offsets(index, selected)
    # Payload parity with the image (CHIM-PAYLOAD-PARITY-33): the same selections it applies.
    models = list(index['models'])
    textures = list(index['textures'])
    parity = {'harvest_removed': [], 'town_flora_added': []}
    town_numbers = {r['number'] for r in selected}
    with timer.section('town flora'):
        found = town_flora(town, flora, town_numbers) if flora else None
        if found:
            parity['town_flora_added'] = add_town_flora(found, flora, models, textures, prepared, mesh_fps,
                                                        selected, jobs, cache)
    if harvest_set:
        removed = harvest_set & {r['number'] for r in selected}
        selected = [r for r in selected if r['number'] not in removed]
        parity['harvest_removed'] = sorted(removed)
    with timer.section('ground samples'):
        grids = {tuple(g['cell']): g for g in json.loads((work / 'audit/terrain-source.json').read_text())}
        ground = wad_lumps(ground_assets(data, work / 'audit', pal_bytes))
        ground = {k: v for k, v in ground.items() if k.startswith('g') or k == '*water'}
        step = settings['terrain_step']
        low, high = settings['bounds']
        xs = range(low[0], high[0] + 1, step)
        ys = range(low[1], high[1] + 1, step)
        heights = [[terrain_at(grids, settings, x, y)[0] for x in xs] for y in ys]
        materials = [[terrain_material(grids, settings, x + step / 2, y + step / 2) for x in xs[:-1]] for y in ys[:-1]]
    frame = {'cell': tuple(settings['source_cell']), 'centre': tuple(float(v) for v in centre),
             'low': (float(low[0]), float(low[1])), 'span': (high[0] - low[0], high[1] - low[1])}
    spec = frame_input(frame=frame, centre=centre, models=models, references=selected,
                       prepared=prepared, profiles=profiles, mesh_fps=mesh_fps, texture_records=textures,
                       archive=archive, palette=pal_bytes, heights=heights, materials=materials, step=step,
                       floor=TERRAIN_FLOOR, ceiling=TERRAIN_CEILING, ground_textures=ground, qbsp=qbsp,
                       collision_cache=work / 'collision-cache', jobs=jobs, cache=cache, timer=timer,
                       settings=settings_override, mesh_occluders=mesh_occluders)
    doors = [[(r['position'][0] - centre[0]) * SCALE, (r['position'][1] - centre[1]) * SCALE]
             for r in selected if r.get('type') == 'DOOR' and r.get('destination')]
    section = {'town': town, 'cell': list(frame['cell']),
               'placements': [{'ref': r['number'], 'cell': list(r.get('cell') or [])} for r in selected],
               'doors': doors, 'terrain_step': step, 'terrain_low': [low[0], low[1]],
               'terrain_tiles': (len(xs) - 1) * (len(ys) - 1), 'water_level': WATER_LEVEL,
               'terrain_heights': heights}
    return spec, section, parity, len(prepared)
