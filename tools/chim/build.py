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
import shutil
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
# Meshes the large-model cut keeps whole even when they are wider than cut_models_over: variant name prefixes
# (the mesh path without 'meshes/'). Owner decision 2026-10-10 (Vivec M3): flora stays whole until tiling it is
# measured (24 wide trees and 31 parasols around Vivec). An area may set its own list (cut_keep_whole).
CUT_KEEP_WHOLE = ('f/flora_',)
# Area config keys of the cut (config/<town>.json): the area's own value unless the build names one for every
# area (chim_build --cut-models-over).
# detail_budget: a named per-mesh triangle budget (config/chim-detail-budgets.json) as an area setting, so one area
# (all of Vivec in one frame: 'vivec-deep') takes it and the others stay whole; the build-wide --detail-budget wins
AREA_CUT_KEYS = ('cut_models_over', 'cut_mode', 'cut_keep_whole', 'detail_budget', 'clip_to_terrain')


def cut_candidate(variant, cut_over, keep_whole=CUT_KEEP_WHOLE):
    """True when the large-model cut stores this variant in pieces: wider than cut_over (local units) and not
    named by keep_whole."""
    if cut_over <= 0 or max(variant['hi'][0] - variant['lo'][0], variant['hi'][1] - variant['lo'][1]) <= cut_over:
        return False
    return not str(variant.get('name', '')).lower().startswith(tuple(p.lower() for p in keep_whole))


def area_cut_settings(area_settings, settings_override):
    """The frame settings of one area: the build-wide settings with the area's own cut keys added where the
    build does not set them."""
    out = dict(settings_override or {})
    for key in AREA_CUT_KEYS:
        if key in (area_settings or {}) and key not in out:
            out[key] = area_settings[key]
    return out
# Worker count, unit cache hits and wall time of a CHIM build (a diagnostic, build_cache.DIAGNOSTIC_NAMES).
TIMING_FILE = 'chim-timing.json'


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


# Fields of a scenery-index record that describe where the stage stored a mesh, not what it is: archive
# offsets and positions in the stage's texture list. A unit key never includes them, so the same mesh from
# two source stages (two towns, two CHIMport cells) is one unit (CHIM-UNIT-FP-SOURCE-LAYOUT-33).
LAYOUT_KEYS = ('offset',)


def canonical_materials(materials, texture_records):
    """A model's materials with each texture_index replaced by that texture's content hash."""
    out = []
    for m in materials:
        m = dict(m)
        ti = m.pop('texture_index', None)
        m['texture'] = texture_records[ti].get('sha256') if ti is not None else None
        out.append(m)
    return out


def canonical_model(model, texture_records):
    """A scenery-index model record by content: no archive offsets, textures by content hash."""
    m = {k: v for k, v in model.items() if k not in LAYOUT_KEYS and not k.startswith('_')}
    m['materials'] = canonical_materials(model['materials'], texture_records)
    if 'textures' in m:
        m['textures'] = [texture_records[i].get('sha256') for i in m['textures']]
    if isinstance(m.get('collision'), dict):
        m['collision'] = {k: v for k, v in m['collision'].items() if k not in LAYOUT_KEYS}
    return m


def mesh_fingerprint(model, profile, texture_records):
    """A mesh unit by content: its record without layout (mesh and collision hashes, materials with their
    textures' hashes), and its profile."""
    return fingerprint('mesh', canonical_model(model, texture_records), profile)


def build_frame(out, **kw):
    """A world of one frame from prepared inputs (frame_input, then chim.world.build_frames); the receipt."""
    spec = frame_input(**kw)
    receipt = build_frames(out, [spec], kw.get('settings'), TERRAIN_LIGHT, jobs=kw.get('jobs', 1),
                           cache=kw.get('cache'), timer=kw.get('timer'))
    receipt['collision_union_fallbacks'] = spec['fallbacks']
    receipt['routed_hulls'] = spec.get('routed_hulls', [])
    return receipt


def frame_input(*, frame, centre, models, references, prepared, profiles, mesh_fps, texture_records,
                archive, palette, heights, materials, step, floor, ceiling, ground_textures,
                qbsp=None, collision_cache=None, jobs=1, cache=None, timer=None, settings=None,
                mesh_occluders=True, ground=None, liquids=None, height_at=None):
    """Units of one frame from prepared inputs (shared by the area build and the tests): the frame
    input of chim.world.build_frames, plus 'fallbacks' (meshes whose collision union fell back).

    references: placed statics (scenery index rows after window mounting and
    visual offsets); prepared: {model index: _prepare_model result};
    profiles: {mesh source: converter profile}; mesh_fps: {model index:
    fingerprint}; heights: tile corner heights over the frame (rows by y);
    materials: tile materials (rows by y); ground_textures: {texture name
    ('gN', '*water'): miptex bytes}; ground (format 0.5): a chim.ground.TriangleGround over
    the frame's tiles, the converter's own triangles, instead of heights and materials;
    liquids: lava prisms in frame-local units (tools/lava.py, docs/LAVA.md), carved into the chunks
    they reach (chim.terrain.chunk_terrain); a chunk without one keeps its task, so its unit is reused.
    height_at (terrain references): the ground height at any frame-local corner, also one tile past the
    frame, so a chunk at the frame's edge gets the whole ring of its standing hull and the same content as
    the same ground inside a neighbouring frame.
    Returns the receipt."""
    from chim.models import texture_unit, variant_ref, variant_unit, yaw_degrees, depth_compile_candidate
    timer = timer or Timer()
    cache = cache or UnitCache()
    firsts = {}
    for ref in references:
        firsts.setdefault(variant_key(ref), ref)
    order = list(firsts)
    clip_spec = None
    if any(models[r['model_index']].get('_clip_to_terrain', (settings or {}).get('clip_to_terrain', False))
           for r in references):
        if (settings or {}).get('cut_models_over', 0):
            raise ValueError('Terrain clipping requires whole shared models')
        triangles = []
        if ground is not None:
            triangles = [t for j in range(ground.size[1]) for i in range(ground.size[0])
                         for t, material in ground.tile_list(i, j)]
        elif heights is not None:
            from chim.terrain import tile_polygons
            for j in range(len(heights)-1):
                for i in range(len(heights[0])-1):
                    corners = [[frame['low'][0]+(i+dx)*step, frame['low'][1]+(j+dy)*step,
                                heights[j+dy][i+dx]] for dx,dy in ((0,0),(1,0),(1,1),(0,1))]
                    for poly in tile_polygons(corners):
                        triangles.extend([[poly[0],poly[k],poly[k+1]] for k in range(1,len(poly)-1)])
        triangles = np.asarray(triangles, dtype=float).tolist()
        if not triangles:
            raise ValueError('No authoritative terrain for clip_to_terrain')
        clip_spec = dict(triangles=triangles, bottom=float(floor), overlap=0.5)
    qbsp_hash = hashlib.sha256(Path(qbsp).read_bytes()).hexdigest() if qbsp else None
    # texture keys in unit results are content hashes; index_of_sha maps them back to this stage's list
    texture_shas = [t.get('sha256') for t in texture_records]
    index_of_sha = {sha: i for i, sha in enumerate(texture_shas)}
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
                    'texture_shas': texture_shas,
                    'exact': exact, 'hollow': bool(profile.get('hollow_collision')),
                    'qbsp': str(qbsp) if qbsp else None,
                    'collision_cache': str(collision_cache) if collision_cache else None,
                    'hull_patch': model_hull_patch_on(settings), 'weld': model_weld_mode(settings)}
            # the hull mode changes the model's collision bytes (routed_hull): part of its identity
            from mesh_geometry_env import model_hull_mode
            from routed_hull import chain_depth_limit, keep_chain_set, mesh_stem
            # the heap fallback's keep-chain list (chim_build): this mesh's hull stays the chain
            task['keep_chain'] = mesh_stem(model['source']) in keep_chain_set()
            # with model_hull_patch on (the default), a model whose standing hull may be compiled (exact, or the
            # compiled model hull mode) gets the lost pieces patched in (CHIM-COMPILED-HULL-SHORT-36): other bytes,
            # another key. Off, the compiled bytes are unchanged and so is the key; the check is recorded when built.
            checked = (('hull-check-1', 'patch') if task['hull_patch'] and qbsp_hash
                       and (exact or model_hull_mode() == 'compiled'
                            or depth_compile_candidate(model['source'], model_hull_mode(), task['keep_chain'])) else None)
            fp = fingerprint('variant', mesh_fps[mi], list(k), size, exact, task['hollow'], qbsp_hash, model_hull_mode(), chain_depth_limit(),
                             task['keep_chain'], 'hull-form-v1',
                             model.get('flames'), canonical_materials(model['materials'], texture_records),
                             ref['scale'], (variant_ref(ref) if task['weld'] == 'base' else ref)['rotation_radians'],
                             ref.get('_flatten_shift', 0), ref.get('_visual_offset', [0, 0, 0]))
            if checked:
                fp = fingerprint('variant', fp, *checked)
            if task['weld'] == 'base':
                # vertices shared as in the base (chim.models.base_frame, CHIM-STRIDER-SCALED-SEAMS-36): other bytes
                # than the placed-position sharing for most scaled and tilted variants, so another key
                fp = fingerprint('variant', fp, 'weld-base-1')
            if clip_spec is not None and model.get('_clip_to_terrain', (settings or {}).get('clip_to_terrain', False)):
                poses = [(tuple(float(v) for v in (np.array(r['position'])-np.array([*centre,0]))*.25), yaw_degrees(r))
                         for r in references if variant_key(r)==k]
                task['terrain_clip'] = dict(clip_spec, placements=poses)
                fp = fingerprint('variant', fp, 'terrain-render-clip-v1', task['terrain_clip'])
            items.append((fp, task))
        results = run_units('variant', items, variant_unit, jobs, cache)
        variant_fps = {k: fp for k, (fp, _) in zip(order, items)}
        variant_tasks = {k: task for k, (_, task) in zip(order, items)}
    variants, names, fallbacks, routed, checks = {}, set(), [], [], []
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
        if res.get('hull_form') == 'routed':
            routed.append(name)
        if res.get('hull_check'):
            checks.append(dict(res['hull_check'], model=name))
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
                ti = None if flat else (index_of_sha[tkey[1]] if isinstance(tkey[1], str) else tkey[1])
                flat_rgb = prepared[mi][4].get('_flat_rgb') if flat else None
                source_archive = model.get('_archive', archive)
                task = {'archive': str(source_archive) if source_archive else None, 'textures': texture_records,
                        'model': model,
                        'material': material, 'size': tkey[3] if flat else tkey[2], 'palette': palette,
                        'flat_rgb': flat_rgb, 'kind': kind, 'glow': glow}
                # by content: the texture's hash, not its position in this stage's texture list
                fp = fingerprint('texture', [tkey[0], None if ti is not None else tkey[1], *tkey[2:]],
                                 texture_records[ti].get('sha256') if ti is not None else None,
                                 flat_rgb, palette)
                tasks[tkey] = (fp, task)
        keys = list(tasks)
        built = run_units('texture', [tasks[k] for k in keys], texture_unit, jobs, cache)
    def stage_key(k):
        # the key as the stage indexes it (the identity written into the world, as before content keys)
        return ((k[0], index_of_sha[k[1]], *k[2:]) if k[0] == 'model' and isinstance(k[1], str) and k[1] != 'flatten'
                else k)
    textures = {k: {'identity': '|'.join(map(str, stage_key(k))), 'miptex': r['miptex'], 'size': r['size'],
                    'engine': (r['kind'], r['glow']), 'source': texture_source(texture_records, stage_key(k))}
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
        refs = terrain_refs_on(settings)
        outer_ring = []                 # chunks whose standing hull ring reaches past the frame (height_at)
        tiles_x, tiles_y = nx * per, ny * per
        for cx, cy in chunks:
            # The collision box: the chunk and one ring of tiles around it inside the frame
            # (the standing box reaches less than a tile; seamless hull 1, format 0.4).
            i0, j0 = max(0, cx * per - 1), max(0, cy * per - 1)
            i1, j1 = min(tiles_x, (cx + 1) * per + 1), min(tiles_y, (cy + 1) * per + 1)
            box = (low[0] + cx * g, low[1] + cy * g, low[0] + (cx + 1) * g, low[1] + (cy + 1) * g)
            cbox = (low[0] + i0 * step, low[1] + j0 * step, low[0] + i1 * step, low[1] + j1 * step)
            # A frame with both a corner grid and irregular ground (a town frame with shoreline tiles,
            # CHIM-STITCH-SHORELINE-36) takes the triangles only in the chunks whose collision box
            # holds a refined tile; every other chunk keeps its grid task, so its unit is reused.
            # (a ground without a .refined set is irregular everywhere, as Seyda Neen's)
            refined = getattr(ground, 'refined', None)
            irregular = ground is not None and (heights is None or refined is None or any(
                (i, j) in refined for j in range(j0, j1) for i in range(i0, i1)))
            if not irregular and refs and height_at is not None and (i0, j0, i1, j1) != (
                    cx * per - 1, cy * per - 1, (cx + 1) * per + 1, (cy + 1) * per + 1):
                # a chunk at the frame's edge: its whole ring from the sampler, as inside any other frame
                i0, j0, i1, j1 = cx * per - 1, cy * per - 1, (cx + 1) * per + 1, (cy + 1) * per + 1
                outer_ring.append([cx, cy])
                cbox = (low[0] + i0 * step, low[1] + j0 * step, low[0] + i1 * step, low[1] + j1 * step)
                hs = [[height_at(low[0] + i * step, low[1] + j * step) for i in range(i0, i1 + 1)]
                      for j in range(j0, j1 + 1)]
                ms = [row[cx * per:(cx + 1) * per] for row in materials[cy * per:(cy + 1) * per]]
                task = {'box': box, 'step': step, 'heights': hs, 'materials': ms, 'floor': floor,
                        'ceiling': ceiling, 'water': WATER_LEVEL, 'light': TERRAIN_LIGHT, 'collision_box': cbox}
            elif not irregular:
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
            reach = [l for l in (liquids or ()) if lava_box_reaches(l, cbox)]
            if reach:
                task = dict(task, liquids=reach)
            if refs:
                # terrain references (format 0.7, docs/chim/WORLD_FORMAT.md "Terrain references"): the chunk's
                # terrain in chunk-local units (its low corner at 0, 0), so the same ground anywhere is the same
                # unit and the same stored record; the frame places it at its offset (the engine translates it
                # when it grafts the chunk, chim_graft.c)
                task = local_terrain_task(task, box[0], box[1])
            # Irregular ground (many small prisms per chunk) gets the standing hull compiled by qbsp
            # (CHIM-SEYDA-MEMORY-33); a regular grid keeps the routed chains (format 0.4), which hold
            # it compactly and walk it exactly. Either is selectable (terrain_hull). The fingerprint
            # holds the compiler's bytes, not its path or the cache folder.
            hull = (settings or {}).get('terrain_hull') or ('compiled' if qbsp and irregular else 'routed')
            # 'hull-check-2': a compiled hull is checked against the exact union of its pieces, lost pieces patched in,
            # else the unit falls back to the routed hull (CHIM-COMPILED-HULL-SHORT-36); older units are not reused
            fp = fingerprint('terrain', task, hull, *((qbsp_hash, 'hull-check-2') if hull == 'compiled' else (None,)))
            if hull != 'routed':
                task = dict(task, hull=hull, qbsp=str(qbsp), collision_cache=str(collision_cache))
            items.append((fp, task))
        terrain = dict(zip(chunks, run_units('terrain', items, terrain_unit, jobs, cache)))
        if refs:
            terrain = {c: dict(t, offset=(low[0] + c[0] * g, low[1] + c[1] * g, 0.0)) for c, t in terrain.items()}
    # Large-model cut (chim.cut): a placement whose model is wider than cut_models_over (default: one
    # chunk) is stored as one model per chunk it covers, so only its pieces in the ring are resident
    # (CHIM-ARENA-MEMORY-33). 512 (two chunks) cuts district-size bodies (Vivec cantons about 1,750 units,
    # the Ministry of Truth about 915) and keeps house-size models whole; 0 keeps every model whole.
    cut_over = float((settings or {}).get('cut_models_over', CUT_MODELS_OVER))
    cut_mode = (settings or {}).get('cut_mode', 'tiles')
    keep_whole = tuple((settings or {}).get('cut_keep_whole', CUT_KEEP_WHOLE))
    cuts, tiled = {}, {}
    if cut_over > 0 and cut_mode == 'tiles':
        # the model is cut once in its own frame; every placement of it places the shared tiles
        from chim.cut import tile_unit
        with timer.section('large-model cut'):
            items = []
            for k in order:
                if not cut_candidate(variants[k], cut_over, keep_whole):
                    continue
                task = dict(variant_tasks[k], grain=g)
                task.pop('qbsp', None)
                task.pop('collision_cache', None)
                items.append((fingerprint('tiles', variant_fps[k], g), task))
            keys = [k for k in order if cut_candidate(variants[k], cut_over, keep_whole)]
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
                if not cut_candidate(variants[k], cut_over, keep_whole):
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
            'terrain': terrain, 'fallbacks': sorted(set(fallbacks)), 'routed_hulls': sorted(set(routed)),
            'outer_ring_chunks': outer_ring, 'hull_checks': checks,
            'visibility': ({'heights': heights, 'step': step, 'low': tuple(low), 'mesh_occluders': mesh_occluders}
                           if ground is None else
                           {'triangles': [(t, m) for j in range(ground.size[1]) for i in range(ground.size[0])
                                          for t, m in ground.tile_list(i, j)],
                            'step': step, 'low': tuple(low), 'size': ground.size,
                            'mesh_occluders': mesh_occluders})}


TERRAIN_REFS = ('off', 'on')


def apply_mesh_method(profile, source, settings):
    """A CHIM area profile with the mesh's method keys (tools/mesh_methods.py): planar merge, or meshoptimizer +
    planar merge, or the converter's own steps. Flattened window meshes keep the converter's steps."""
    from mesh_methods import apply
    if profile.get('flatten'):
        return profile
    return apply(profile, source, settings)
MODEL_HULL_PATCH = ('off', 'on')


def model_hull_patch_on(settings):
    """Patch the pieces a compiled model hull lost (build setting model_hull_patch, 'on' by default since the
    compiled terrain hull left Balmora's ring room for it; 'off' keeps the hull as compiled, the previous method;
    collision_bsp.patch_holes, CHIM-COMPILED-HULL-SHORT-36)."""
    mode = (settings or {}).get('model_hull_patch', 'on')
    if mode not in MODEL_HULL_PATCH:
        raise ValueError('Unknown model hull patch mode: %s' % mode)
    return mode == 'on'


def model_weld_mode(settings):
    """How a model variant shares its vertices (build setting 'model_weld'): 'base' (default: as in its base,
    the prepared mesh's own frame, so every scale and tilt has the base's vertices and edges;
    CHIM-STRIDER-SCALED-SEAMS-36) or 'placed' (by the placed position rounded to 1e-5, the method before
    v0.0.36-dev3)."""
    from chim.models import MODEL_WELD
    mode = (settings or {}).get('model_weld', 'base')
    if mode not in MODEL_WELD:
        raise ValueError('Unknown model weld mode: %s' % mode)
    return mode


def terrain_refs_on(settings):
    """Terrain references (format 0.7): the build setting 'terrain_refs' ('off' by default, 'on')."""
    mode = (settings or {}).get('terrain_refs', 'off')
    if mode not in TERRAIN_REFS:
        raise ValueError('Unknown terrain references mode: %s' % mode)
    return mode == 'on'


def local_terrain_task(task, ox, oy):
    """A chunk terrain task moved by (-ox, -oy): box, collision box, tile triangles and lava prisms in
    chunk-local units. Heights and materials are tables (no positions); z is not moved."""
    def box(b):
        return (b[0] - ox, b[1] - oy, b[2] - ox, b[3] - oy)
    out = dict(task, box=box(task['box']))
    if task.get('collision_box') is not None:
        out['collision_box'] = box(task['collision_box'])
    if task.get('triangles') is not None:
        out['triangles'] = [[tx - ox, ty - oy, [[r[0] - ox, r[1] - oy, r[2], r[3] - ox, r[4] - oy, r[5],
                                                  r[6] - ox, r[7] - oy, r[8], r[9]] for r in rows]]
                            for tx, ty, rows in task['triangles']]
    if task.get('liquids'):
        out['liquids'] = [dict(l, hull=[[x - ox, y - oy] for x, y in l['hull']]) for l in task['liquids']]
    return out


def lava_box_reaches(liquid, box):
    """Does a lava prism's plan box overlap a chunk's collision box (x0, y0, x1, y1)?"""
    xs = [p[0] for p in liquid['hull']]
    ys = [p[1] for p in liquid['hull']]
    return min(xs) < box[2] and max(xs) > box[0] and min(ys) < box[3] and max(ys) > box[1]


def frame_liquids(pools, centre):
    """Lava pools of a town (world units, import_town.lava_pools) as frame-local prisms."""
    import lava
    from prepare_quake import SCALE
    out = []
    for p in pools:
        hull, top = lava.to_quake(p['hull'], p['top'], [centre[0], centre[1], 0.0], SCALE)
        out.append({'hull': [[round(x, 4), round(y, 4)] for x, y in hull], 'top': round(top, 4)})
    return out


def lava_section(pools):
    """The build's lava record (the trackers' converted status): mode and the pools by source cell."""
    import lava
    cells = {}
    for p in pools:
        x, y = lava.polygon_centroid(p['hull'])
        key = '%d,%d' % (math.floor(x / 8192), math.floor(y / 8192))
        cells[key] = cells.get(key, 0) + 1
    return {'mode': lava.lava_mode(), 'pools': len(pools), 'cells': dict(sorted(cells.items()))}


def source_stage(data, work, jobs, settings):
    """import_town.collect, or its verified earlier result."""
    from import_town import collect, source_receipt
    expected = source_receipt(data, settings)
    path = work / 'source-receipt.json'
    if path.is_file():
        previous = json.loads(path.read_text())
        if previous == expected:
            _log('source stage reused (inputs verified)')
            return json.loads((work / 'scenery/scenery-index.json').read_text())
        if any(previous.get(key) != expected[key] for key in ('geometry', 'files')):
            raise ValueError('Existing source stage was made from other inputs; use a new work folder')
        # A converter change invalidates only this source stage. Preserve the
        # earlier evidence without copying it or discarding the shared unit pool.
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        archive = work.with_name(work.name + '.stale-' + digest)
        suffix = 0
        while archive.exists():
            suffix += 1
            archive = work.with_name(work.name + '.stale-' + digest + '-' + str(suffix))
        work.rename(archive)
        _log('source conversion changed; earlier stage preserved in ' + archive.name)
    work.mkdir(parents=True, exist_ok=True)
    collect(data, work, jobs, settings)
    (work / 'source-receipt.json').write_text(json.dumps(expected, indent=2) + '\n')
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
        from chim.ownership import capture
        selected.append(dict(capture(ref), model_index=fmodels[(ref['model_index'], modes[ref['number']])]))
    return [r['number'] for r in frefs]


def build_town(town, data_files, out, palette, qbsp=None, jobs=None, settings_override=None, use_cache=True,
               rebuild_meshes=(), mesh_occluders=True, unit_cache=None, harvest=None, flora=None):
    """One town's world: build_areas([town], ...)."""
    return build_areas([town], data_files, out, palette, qbsp, jobs, settings_override, use_cache, rebuild_meshes,
                       mesh_occluders, unit_cache, harvest, flora)


HULL_FALLBACK_STEPS = 8      # meshes the heap fallback may turn back into chains


def build_areas(areas, data_files, out, palette, qbsp=None, jobs=None, settings_override=None, use_cache=True,
                rebuild_meshes=(), mesh_occluders=True, unit_cache=None, harvest=None, flora=None, legacy_run=None,
                texture_effects=(), far_terrain=True, hull_fallback_sdk=None):
    """build_world (one CHIM world, a frame per area) with the routed-hull heap fallback
    (COLLISION-TRACE-COST-33), for every caller of the shared builder. With hull_fallback_sdk (the Amiga SDK
    the heap gate probes the target sizes with) and auto hulls (mesh_geometry_env.model_hull_mode): while a
    frame's ring does not fit the CHIM zone and its peak ring holds routed meshes, the routed mesh with the
    fewest standing clipnodes keeps its chain (routed_hull.KEEP_CHAIN_VARIABLE) and the world is built again
    (every other unit comes from the cache). The receipt records it: hull_fallback = {kept_as_chain: [mesh
    stems], kept_as_chain_for_memory: count, reason}. The strict heap gate still runs after it (chim_build)."""
    args = (areas, data_files, out, palette, qbsp, jobs, settings_override, use_cache, rebuild_meshes,
            mesh_occluders, unit_cache, harvest, flora, legacy_run, texture_effects, far_terrain)
    receipt = build_world(*args)
    from mesh_geometry_env import model_hull_mode
    if hull_fallback_sdk is None or model_hull_mode() != 'auto':
        return receipt
    from routed_hull import KEEP_CHAIN_VARIABLE, keep_chain_set
    from chim.heap import require_heap
    from check_world_map_heap import compile_target_sizes
    sizes = compile_target_sizes(hull_fallback_sdk)[0]
    given = keep_chain_set()
    kept = sorted(given)
    heap_cache = (Path(unit_cache) / 'heap') if unit_cache and use_cache else None
    previous = os.environ.get(KEEP_CHAIN_VARIABLE)
    try:
        for _ in range(HULL_FALLBACK_STEPS):
            try:
                require_heap(out, sizes=sizes, jobs=jobs or 1, cache_dir=heap_cache)
                break
            except ValueError:
                pass
            candidate = routed_peak_mesh(out, set(kept))
            if candidate is None:
                break          # nothing left to fall back on: the strict heap gate reports the failure
            kept.append(candidate)
            os.environ[KEEP_CHAIN_VARIABLE] = ','.join(sorted(kept))
            _log('hull fallback: %s keeps its chain; building the world again' % candidate)
            receipt = build_world(*args)
    finally:
        if previous is None:
            os.environ.pop(KEEP_CHAIN_VARIABLE, None)
        else:
            os.environ[KEEP_CHAIN_VARIABLE] = previous
    fallback = [k for k in kept if k not in given]
    if fallback:
        receipt['hull_fallback'] = {'kept_as_chain': fallback, 'kept_as_chain_for_memory': len(fallback),
                                    'reason': 'a ring over the CHIM zone with routed hulls'}
        write_json(Path(out) / 'chim-receipt.json', receipt)
    return receipt


def routed_peak_mesh(out, kept):
    """The routed mesh (stem) with the fewest standing clipnodes in the peak ring of the first frame over the
    zone (OUT/chim-heap.json peak_models; routed: OUT/chim-receipt.json routed_hulls), or None."""
    import json
    import struct
    from chim import format as F
    from chim.validate import Failures, load_world
    from hull_chain_audit import hull_depth
    report = json.loads((Path(out) / 'chim-heap.json').read_text(encoding='utf-8'))
    bad = [f for f in report.get('frames', []) if not f['ok']]
    if not bad:
        return None
    _, _, _, _, models, _ = load_world(out, Failures())
    routed = set(json.loads((Path(out) / 'chim-receipt.json').read_text(encoding='utf-8')).get('routed_hulls', []))
    best = None
    for i in bad[0].get('peak_models', []):
        stem = models[i]['name'].split('@')[0]
        if stem in kept or models[i]['name'] not in routed:
            continue
        lumps = F.read_brush_image(models[i]['image'])
        root = struct.unpack_from('<9f7i', lumps[14])[10]
        reach, _depth = hull_depth(lumps[9], root) if lumps[9] else (0, 0)
        if best is None or (reach, stem) < best:
            best = (reach, stem)
    return best[1] if best else None


def build_world(areas, data_files, out, palette, qbsp=None, jobs=None, settings_override=None, use_cache=True,
                rebuild_meshes=(), mesh_occluders=True, unit_cache=None, harvest=None, flora=None, legacy_run=None,
                texture_effects=(), far_terrain=True):
    """One CHIM world holding a frame per area (town id of config/towns.json), stored once across them.

    rebuild_meshes: mesh sources whose units are built again (as after a converter change for them);
    unit_cache: folder of the unit cache (default OUT/work/chim-units), e.g. one kept between builds, or a
    UnitCache (chim.units.PooledUnitCache: the run's folder backed by the shared storage pool);
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
    if isinstance(unit_cache, UnitCache):
        cache = unit_cache if use_cache else UnitCache(None)   # e.g. chim.units.PooledUnitCache (shared pool)
    else:
        cache = UnitCache((Path(unit_cache) if unit_cache else out / 'work' / 'chim-units') if use_cache else None)
    pal_bytes = Path(palette).read_bytes()
    harvest_set = harvest_numbers(harvest, data) if harvest else set()
    specs, sections, parity, meshes = [], [], {}, 0
    # CHIM region frames (one cell each, registered generated areas) are prepared side by side, one area per
    # worker: each area's own steps (its source catalogue, terrain audits, ground samples) are serial, so one
    # area at a time kept most cores idle for the first 35 to 45 minutes of a 270-frame stage
    # (BUILD-CHIM-STAGE-IDLE-START-36). Towns keep the whole job budget, one after another. Same results.
    from town_config import generated_areas
    generated = generated_areas()
    regional = [t for t in areas if t in generated]
    prepared = {}
    if len(regional) > 1 and jobs > 1:
        prepared = prepare_areas_parallel(regional, generated, data, out, pal_bytes, qbsp, jobs, cache, timer,
                                          settings_override, rebuild_meshes, mesh_occluders, harvest_set, flora)
    for town in areas:
        if town in prepared:
            spec, section, parity[town], count = prepared.pop(town)
            specs.append(spec)
            sections.append(section)
            meshes += count
            continue
        if town == 'seyda':
            from chim import seyda
            spec, section, parity[town], count = seyda.prepare_area(
                legacy_run, data, out / 'work' / town, pal_bytes, qbsp, jobs, cache, timer, settings_override,
                rebuild_meshes, mesh_occluders, harvest_set, flora)
        else:
            spec, section, parity[town], count = prepare_area(
                town, data, out / 'work' / town, pal_bytes, qbsp, jobs, cache, timer, settings_override,
                rebuild_meshes, mesh_occluders, harvest_set, flora)
        # fail fast (BUILD-CHIM-VALIDATE-LATE-36): this frame's terrain geometry is checked now, not after
        # every other frame is built; the whole-world validation still runs at the end (chim_build --validate)
        with timer.section('early frame checks'):
            from chim.validate import early_frame_failures
            early = early_frame_failures(spec, section, town, jobs)
        if early:
            raise ValueError('CHIM frame checks failed (%d): %s' % (len(early), '; '.join(early[:5])))
        specs.append(spec)
        sections.append(section)
        meshes += count
    from chim.apron_policy import reconcile
    apron_dispositions = reconcile(specs, sections, out, set(regional), flora)
    from chim.apron_policy import supplement_seyda
    supplied = supplement_seyda(specs, sections)
    apron_dispositions += supplied
    if supplied:
        from chim.seyda import write_source_metadata, _config
        from town_grid import reference_ownership
        from chim.ownership import original
        section = next(s for s in sections if s['town'] == 'seyda')
        audited = json.loads((Path(legacy_run) / 'work/generated/seyda-neen/placements.json').read_text())
        by_number = {r['number']: r for r in audited}
        selected = []
        for row in section['frame_ownership']['references']:
            ref = by_number[row['original']['number']]
            if original(ref) != row['original']:
                raise ValueError('Seyda apron owner differs from original audit')
            selected.append(ref)
        write_source_metadata(legacy_run, out / 'work/seyda', selected, harvest_set)
        section['reference_ownership'] = reference_ownership(selected, _config())
    from chim.ownership import source_failures
    ownership_errors = source_failures(sections)
    if ownership_errors:
        raise ValueError('CHIM source ownership: ' + '; '.join(ownership_errors[:10]))
    effects = [load_effect(path) for path in texture_effects]
    applied = []
    for spec in specs:
        spec['textures'], record = apply_effects(spec['textures'], effects, pal_bytes)
        applied.append(record)
    receipt = build_frames(out, specs, settings_override, TERRAIN_LIGHT, jobs=jobs, cache=cache, timer=timer)
    receipt['apron_dispositions'] = apron_dispositions
    receipt['collision_union_fallbacks'] = sorted({m for s in specs for m in s['fallbacks']})
    # models whose standing hull is routed (routed_hull): the heap fallback's candidates (chim_build)
    receipt['routed_hulls'] = sorted({m for s in specs for m in s.get('routed_hulls', [])})
    # compiled model hulls checked against their pieces (CHIM-COMPILED-HULL-SHORT-36): every one the compiler
    # left short or floating, and every one patched (build setting model_hull_patch)
    found = {c['model']: c for s in specs for c in s.get('hull_checks', [])}
    receipt['compiled_model_hulls'] = {
        'checked': len(found), 'patch': model_hull_patch_on(settings_override),
        'inexact': sorted('%s short %s over %s' % (n, c['short'], c['over']) for n, c in found.items()
                          if c['short'] > 0 or c['over'] > 0),
        'patched': sorted('%s +%d nodes' % (n, c.get('patched_nodes', 0)) for n, c in found.items()
                          if c.get('patched_rounds'))}
    # The frames' far terrain (chim.far): resident distant land, a sidecar of each frame map.
    with timer.section('far terrain'):
        from chim.far import write_layers
        receipt['far_terrain'] = write_layers(out, [s['frame'] for s in specs], data) if far_terrain else []
    source = {'builder': BUILDER, 'chim_version': CHIM_VERSION, 'world_format': receipt['world_format'],
              'areas': areas, 'frames': sections}
    from chim.ownership import bind_index
    bind_index(out, source)
    write_json(out / 'chim-source.json', source)
    # Lava pools converted, by source cell (the trackers' converted status, tools/cell_lava.py).
    lava_cells = {}
    for s in sections:
        for cell, n in ((s.get('lava') or {}).get('cells') or {}).items():
            lava_cells[cell] = lava_cells.get(cell, 0) + n
    import lava
    receipt['lava'] = {'mode': lava.lava_mode(),
                       'pools': sum(lava_cells.values()), 'cells': dict(sorted(lava_cells.items()))}
    receipt.update(town=areas[0], areas=areas, source_placements=sum(len(s['placements']) for s in sections),
                   meshes=meshes, parity=parity[areas[0]] if len(areas) == 1 else parity,
                   rebuild_meshes=sorted(rebuild_meshes),
                   texture_effects=[{'name': e['name'], 'file': e['file'], 'sha256': e['sha256'],
                                     'textures': sorted({t for rec in applied for r in rec if r['name'] == e['name']
                                                         for t in r['textures']})} for e in effects],
                   )
    # Areas whose own config sets the large-model cut (AREA_CUT_KEYS), recorded only when one does, so other
    # receipts stay byte-identical; the build-wide --cut-models-over wins and is in receipt['settings']
    from town_config import load_settings as _area_settings
    area_cut = {}
    for a in areas:
        try:
            own = _area_settings(a)
        except (KeyError, ValueError, OSError):
            continue
        keys = {k: own[k] for k in AREA_CUT_KEYS if k in own}
        if keys:
            area_cut[a] = dict(keys, applied=area_cut_settings(own, settings_override).get('cut_models_over'))
    if area_cut:
        receipt['area_cut'] = area_cut
    ocean_sources = [s['ocean_runtime'] for s in sections if 'ocean_runtime' in s]
    if ocean_sources:
        receipt['ocean_runtime'] = {
            'cells': [s['cell'] for s in ocean_sources],
            'original_records': sum(len(s['references']) for s in ocean_sources),
            'deferred_records': sum(len(s['references']) for s in ocean_sources),
            'converted_records': 0, 'native_verified': False, 'packaged': False}
    write_json(out / 'chim-receipt.json', receipt)
    # Worker count, unit cache hits and wall time: a diagnostic beside the receipt, so the receipt is
    # byte-reproducible (BUILD-OUTPUTS-NOT-REPRODUCIBLE-33); chim/stats.py reads it for its build figures.
    write_json(out / TIMING_FILE, {'jobs': jobs, 'units': cache.stats, 'timing': timer.report(),
                                   'wall_seconds': round(time.time() - t0, 1)})
    _log('units: ' + ', '.join('%s %d built %d reused' % (k, v.get('built', 0), v.get('reused', 0))
                               for k, v in sorted(cache.stats.items())))
    refused = sum(v.get('write_refused', 0) for v in cache.stats.values())
    if refused:
        _log('cache write refused: %d units built locally, not stored (BUILD-CACHE-OWNER-FAILS-STAGE-34)' % refused)
    _log('wrote %s (%.1f s wall, %.1f s CPU)' % (out / 'chim', time.time() - t0, timer.report()['cpu_seconds']))
    return receipt


def detail_budget(name):
    """{lower-case mesh source: visual triangle target} of a named budget in config/chim-detail-budgets.json
    ({} for None). Dense areas (Vivec's statues, the Ministry of Truth) only when the build names one."""
    if not name:
        return {}
    import json
    data = json.loads((Path(__file__).resolve().parents[2] / 'config/chim-detail-budgets.json').read_text(encoding='utf-8'))
    if name not in data['budgets']:
        raise ValueError('Unknown detail budget: %s' % name)
    return {k.replace(chr(92), '/').lower(): int(v) for k, v in data['budgets'][name].items()}


SHORELINE_MODES = ('on', 'off')   # chim_build.py --terrain-shoreline (CHIM-STITCH-SHORELINE-36)


def shoreline_ground(sample, materials, low, high, step, liquids=(), shoreline=True, grid_origin=(0.,0.)):
    """The frame's ground as the legacy region maps triangulate it: every tile through
    prepare_world_regions.terrain_triangles (the shared sampler; Seyda Neen's frame uses it too), over
    sample(x, y) -> (height, material) in frame-local units. A tile where land and water flip between
    the 32-unit samples gets them inserted (shoreline refinement); every other tile is its two plain
    triangles 0-1-2, 0-2-3, exactly the corner grid. Each triangle takes its tile's material
    (materials: rows by y, one per tile, as the plain grid). Returns a chim.ground.TriangleGround
    with .refined = {(i, j)} of the refined tiles."""
    from chim.ground import TriangleGround
    from prepare_world_regions import STEP, Terrain, terrain_triangles
    if step != STEP:
        raise ValueError('The shoreline refinement needs %d-unit terrain tiles' % STEP)

    class _Sampler(Terrain):
        def __init__(self):            # no survey packet: the frame's own sampler
            pass

        def sample(self, x, y):
            return sample(x, y)

    terrain = _Sampler()
    if not shoreline:
        terrain.shoreline_detail = lambda x, y: False
    # CHIM-LAVA-TERRAIN-SPIKES-38: use the legacy lava sampler locally,
    # including intermediate samples on adjoining coarse tiles' edges.
    detailed = set()
    for pool in liquids:
        xs, ys = zip(*pool['hull'])
        for y in range(math.floor(min(ys) / step) * step,
                       math.floor(max(ys) / step) * step + step, step):
            for x in range(math.floor(min(xs) / step) * step,
                           math.floor(max(xs) / step) * step + step, step):
                detailed.add((x, y))
    tris, refined = [], set()
    for j, y in enumerate(range(int(low[1]), int(high[1]), step)):
        for i, x in enumerate(range(int(low[0]), int(high[0]), step)):
            neighbours = ((x, y-step), (x+step, y), (x, y+step), (x-step, y))
            edges = [edge for edge, neighbour in enumerate(neighbours) if neighbour in detailed]
            full_detail = (x, y) in detailed
            if full_detail or edges or terrain.shoreline_detail(x, y):
                refined.add((i, j))
            m = int(materials[j][i])
            tris.extend(([list(p) for p in tri], m)
                        for tri in terrain_triangles(terrain, x, y, edges, full_detail, grid_origin))
    size = ((int(high[0]) - int(low[0])) // step, (int(high[1]) - int(low[1])) // step)
    ground = TriangleGround(tris, step, low, size)
    ground.refined = refined
    return ground


def margin_grids(data, work, settings, low, high):
    """Terrain grids {cell: grid} of every source cell under the frame ground box (low, high in
    frame-local units), from a terrain audit of a square wide enough to hold it (work/audit-margin-rN,
    reused when present) and that audit's folder (its materials.json names every ground material).
    Cells without LAND are flat default land (-512 units: the legacy region maps' ocean floor,
    prepare_world_regions.Terrain.sample). Only the terrain is used."""
    from mwad.audit import audit
    sx, sy = settings['source_cell']
    c, s = settings['centre'], settings['scale']
    eps = 1e-6
    cells = [(math.floor((c[0] + x / s) / 8192), math.floor((c[1] + y / s) / 8192))
             for x in (low[0], high[0] - eps) for y in (low[1], high[1] - eps)]
    radius = max(max(abs(cx - sx), abs(cy - sy)) for cx, cy in cells)
    out = work / ('audit-margin-r%d' % radius)
    if not (out / 'terrain-source.json').is_file():
        if out.exists():
            shutil.rmtree(out)
        audit(data, out, (sx, sy), radius, 2, missing_land='flat')
    return {tuple(g['cell']): g for g in json.loads((out / 'terrain-source.json').read_text())}, out


def _area_cache(cache):
    """A worker's copy of the unit cache: the same folder and pool, its own counts (merged back by the caller)."""
    import copy
    clone = copy.copy(cache)
    clone.stats = {}
    if hasattr(clone, 'pool_stats'):
        clone.pool_stats = {k: 0 for k in clone.pool_stats}
        clone._keys = {}
    return clone


def _prepare_area_task(task):
    """Worker of prepare_areas_parallel: one generated area prepared with one job, its early frame checks and
    its timing and unit counts."""
    (town, settings, data, work, pal_bytes, qbsp, cache, settings_override, rebuild_meshes, mesh_occluders,
     harvest_set, flora) = task
    from town_config import register_generated
    from chim.validate import early_frame_failures
    register_generated([settings])
    timer = Timer()
    spec, section, parity, count = prepare_area(town, data, work, pal_bytes, qbsp, 1, cache, timer,
                                                settings_override, rebuild_meshes, mesh_occluders, harvest_set,
                                                flora)
    with timer.section('early frame checks'):
        early = early_frame_failures(spec, section, town, 1)
    return (spec, section, parity, count), early, timer.sections, cache.stats, getattr(cache, 'pool_stats', None)


def prepare_areas_parallel(towns, generated, data, out, pal_bytes, qbsp, jobs, cache, timer, settings_override,
                           rebuild_meshes, mesh_occluders, harvest_set, flora):
    """{town: prepare_area result} of generated areas (CHIM region frames), one area per worker
    (BUILD-CHIM-STAGE-IDLE-START-36). The first frame whose early checks fail stops the stage, named; unit
    counts and timings are merged into the caller's cache and timer."""
    from build_parallel import ordered_map
    tasks = [(t, generated[t], data, out / 'work' / t, pal_bytes, qbsp, _area_cache(cache), settings_override,
              rebuild_meshes, mesh_occluders, harvest_set, flora) for t in towns]
    results = {}
    with timer.section('region frames (side by side)'):
        for town, (result, early, sections, stats, pool_stats) in zip(
                towns, ordered_map(_prepare_area_task, tasks, max(1, min(jobs, len(tasks))))):
            if early:
                raise ValueError('CHIM frame checks failed (%d): %s' % (len(early), '; '.join(early[:5])))
            results[town] = result
            timer.sections.extend(dict(s, section='%s (%s)' % (s['section'], town)) for s in sections)
            for kind, counts in stats.items():
                mine = cache.stats.setdefault(kind, {})
                for k, v in counts.items():
                    mine[k] = mine.get(k, 0) + v
            if pool_stats and hasattr(cache, 'pool_stats'):
                for k, v in pool_stats.items():
                    cache.pool_stats[k] = cache.pool_stats.get(k, 0) + v
            import progress_line
            progress_line.emit('CHIM region frames', town, 'prepared', (len(results), len(towns), 'frames'))
    return results


def prepare_area(town, data, work, pal_bytes, qbsp, jobs, cache, timer, settings_override, rebuild_meshes,
                 mesh_occluders, harvest_set, flora):
    """One area's frame input, source section, parity record and mesh count (build_areas)."""
    from import_town import ground_assets, terrain_at, terrain_material, TERRAIN_CEILING, TERRAIN_FLOOR
    from prepare_quake import SCALE
    from surface_flatten import load_profiles, mount_references, NeighboringFacadeSupport
    from town_config import load_settings, town_field
    from town_regions import town_model_profile
    from visual_offsets import apply_visual_offsets
    settings = load_settings(town)
    ocean_source = None
    if settings.get('ocean_runtime'):
        from chim.ocean_runtime import admit_cell
        ocean_source = admit_cell(data, settings['source_cell'])
        # Only these new frames require references; existing inline terrain stays inline.
        settings_override = dict(settings_override or {}, terrain_refs='on')
        work.mkdir(parents=True, exist_ok=True)
        write_json(work / 'ocean-source.json', ocean_source)
    with timer.section('source stage'):
        index = source_stage(data, work, jobs, settings)
        if settings.get('region_source_apron'):
            from chim.regions import check_source_land
            check_source_land(settings, json.loads((work / 'audit/audit.json').read_text()))
    from visual_recipes import scope_reference_recipes
    index = scope_reference_recipes(index, settings)
    centre = settings['centre']
    # Profiles exactly as import_town.prepare and _append_meshes choose them.
    group = index['groups'][town_field(settings, 'visual_group')]['visual_profiles']
    flatten = load_profiles(scene_kind='exterior')
    profiles, items = {}, []
    from visual_recipes import load_recipes, apply_recipe
    recipe_name = settings.get('visual_recipe')
    recipes = load_recipes()
    archive = work / 'scenery/scenery.mwpak'
    budget = detail_budget(area_cut_settings(settings, settings_override).get('detail_budget'))
    for mi, model in enumerate(index['models']):
        profile = town_model_profile(group[model['source']], model['source'], model['triangles'])
        # CHIM models take the stair-plate rules (mesh_geometry.collision_pieces; legacy open-world maps do not,
        # BUILD-FLORA-STAIR-PLATES-BUDGET-36)
        profile['stair_plates'] = True
        if model['source'] in flatten:
            profile['flatten'] = flatten[model['source']]
        target = budget.get(model['source'].replace(chr(92), '/').lower())
        if target and model['triangles'] > target:
            # a named detail budget (config/chim-detail-budgets.json): fewer visual triangles, same collision
            # the open-boundary lock keeps a shell's rim in place (no slivers at the Vivec statues' base;
            # measured: 1,521 polygons for a 1,200 target on ex_v_vivecstatue_02)
            profile = dict(profile, ratio=target / model['triangles'], visual_triangle_target=target,
                           lod_preserve_border=True)
        # the mesh's CHIM mesh method (config/mesh-methods.json; build setting mesh_method)
        profile = apply_mesh_method(profile, model['source'], settings_override)
        model_recipe = model.get('_visual_recipe', recipe_name)
        if model_recipe:
            profile = apply_recipe(profile, model, model_recipe, recipes)
        model['_profile'] = profile
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
    from chim.ownership import capture
    selected = [capture(r) for r in index['references'] if r['number'] in inside]
    support = NeighboringFacadeSupport(data, settings, (r['number'] for r in selected))
    mount_references(index, selected, prepared, centre, SCALE, support=support)
    if support.report['used']:
        write_json(work / 'window-mount-support.json', support.report)
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
    # Flora may come from an independent source index. Apply the same explicit
    # stage after merging it; do not let it restore hidden construction stages.
    from import_town import fixed_state_references
    before_state = {r['number'] for r in selected}
    selected = fixed_state_references(work, settings, selected)
    parity['fixed_state_removed'] = sorted(before_state - {r['number'] for r in selected})
    if harvest_set:
        removed = harvest_set & {r['number'] for r in selected}
        selected = [r for r in selected if r['number'] not in removed]
        parity['harvest_removed'] = sorted(removed)
    with timer.section('ground samples'):
        grids = {tuple(g['cell']): g for g in json.loads((work / 'audit/terrain-source.json').read_text())}
        from import_town import lava_pools
        from town_config import frame_ground_bounds
        pools = lava_pools(work, data, json.loads((work / 'source-catalogue.json').read_text())['references'])
        step = settings['terrain_step']
        # the frame's ground: the bounds plus the terrain-only margin (CHIM-FAR-BAND-GAP-36), whose
        # cells (and their ground materials) come from a wider terrain audit (no placements are taken from it)
        low, high = frame_ground_bounds(settings)
        audit_dir = work / 'audit'
        if [low, high] != [list(v) for v in settings['bounds']]:
            wide, audit_dir = margin_grids(data, work, settings, low, high)
            grids = {**wide, **grids}
        ocean_materials = {}
        if ocean_source is not None:
            from chim.ocean_terrain import resolve_grids, ground_textures as ocean_ground_textures
            original_grids, ocean_materials, ocean_terrain = resolve_grids(data, grids)
            grids = {**grids, **original_grids}
            if ocean_source['masters'] != ocean_terrain['masters']:
                raise ValueError('Original ocean masters changed during preparation')
            ocean_source['terrain_apron'] = ocean_terrain
        ground = wad_lumps(ground_assets(data, audit_dir, pal_bytes, pools))
        if ocean_materials:
            extra_ground, dependencies = ocean_ground_textures(data, ocean_materials, pal_bytes)
            ground.update(extra_ground)
            ocean_source['terrain_apron']['texture_assets'] = dependencies
        if ocean_source is not None:
            write_json(work / 'ocean-source.json', ocean_source)
        ground = {k: v for k, v in ground.items() if k.startswith('g') or k in ('*water', '*lava')}
        xs = range(low[0], high[0] + 1, step)
        ys = range(low[1], high[1] + 1, step)
        heights = [[terrain_at(grids, settings, x, y)[0] for x in xs] for y in ys]
        materials = [[terrain_material(grids, settings, x + step / 2, y + step / 2) for x in xs[:-1]] for y in ys[:-1]]
        # The shoreline refinement of the legacy region maps (prepare_world_regions.terrain_triangles,
        # the same sampler Seyda Neen's frame uses): the tiles where land and water flip get the
        # original 32-unit samples, so the CHIM ground meets the legacy ground (CHIM-STITCH-SHORELINE-36).
        # 'off' keeps the plain tile grid (the method before v0.0.36).
        mode = (settings_override or {}).get('terrain_shoreline', 'on')
        if mode not in SHORELINE_MODES:
            raise ValueError('Unknown terrain shoreline mode: %s' % mode)
        tri_ground = (shoreline_ground(lambda x, y: terrain_at(grids, settings, x, y), materials, low, high, step,
                                       frame_liquids(pools, centre), shoreline=mode == 'on',
                                       grid_origin=tuple(v*SCALE for v in centre))
                      if mode == 'on' or pools else None)
        if tri_ground is not None and not tri_ground.refined:
            tri_ground = None          # no shoreline tile: the plain grid is the same ground (frame unchanged)
        height_at = None
        if terrain_refs_on(settings_override):
            # terrain references: heights one tile past the ground too (the ring of an edge chunk's hull)
            wide = margin_grids(data, work, settings, [low[0] - step, low[1] - step], [high[0] + step, high[1] + step])[0]
            wide = {**wide, **grids}

            def height_at(x, y):
                return terrain_at(wide, settings, x, y)[0]
    frame = {'cell': tuple(settings['source_cell']), 'centre': tuple(float(v) for v in centre),
             'low': (float(low[0]), float(low[1])), 'span': (high[0] - low[0], high[1] - low[1])}
    if ocean_source is not None:
        frame['ocean_runtime'] = True
        frame['ocean_masters'] = ocean_source['masters']
    if [low, high] != [list(v) for v in settings['bounds']]:
        # the box the frame owns (its placements): frames may share terrain-only margins, never this box
        # (chim.world.frame_box; adjacent CHIM region frames, docs/chim/CHIM_REGIONS.md)
        (olx, oly), (ohx, ohy) = settings['bounds']
        frame['owned'] = ((float(olx), float(oly)), (float(ohx), float(ohy)))
    from visual_recipes import prepare_sprite_replacements
    prepared, mesh_fps, sprite_rows, sprite_assets = prepare_sprite_replacements(
        recipe_name, index, archive, pal_bytes, selected, prepared, mesh_fps, centre, work / 'sprites')
    spec = frame_input(frame=frame, centre=centre, models=models, references=selected,
                       prepared=prepared, profiles=profiles, mesh_fps=mesh_fps, texture_records=textures,
                       archive=archive, palette=pal_bytes, heights=heights, materials=materials, step=step,
                       floor=TERRAIN_FLOOR, ceiling=TERRAIN_CEILING, ground_textures=ground, qbsp=qbsp,
                       collision_cache=work / 'collision-cache', jobs=jobs, cache=cache, timer=timer,
                       settings=area_cut_settings(settings, settings_override), mesh_occluders=mesh_occluders,
                       liquids=frame_liquids(pools, centre), ground=tri_ground, height_at=height_at)
    outside_apron = []
    if settings.get('region_source_apron'):
        from chim.ownership import select_compiled_apron
        selected, outside_apron = select_compiled_apron(spec, selected)
    doors = [[(r['position'][0] - centre[0]) * SCALE, (r['position'][1] - centre[1]) * SCALE]
             for r in selected if r.get('type') == 'DOOR' and r.get('destination')]
    section = {'town': town, 'cell': list(frame['cell']),
               'placements': [{'ref': r['number'], 'cell': list(r.get('cell') or [])} for r in selected],
               'doors': doors, 'terrain_step': step, 'terrain_low': [low[0], low[1]],
               'terrain_tiles': (len(xs) - 1) * (len(ys) - 1), 'water_level': WATER_LEVEL,
               'terrain_heights': heights, 'terrain_shoreline': mode,
               **({'terrain_size': list(tri_ground.size), 'terrain_triangles': tri_ground.rows(),
                   'terrain_refined_tiles': len(tri_ground.refined)} if tri_ground is not None else {}),
               # lava pools carved into the chunks as Quake liquid (docs/LAVA.md), by source cell
               'lava': lava_section(pools), 'terrain_liquids': frame_liquids(pools, centre), 'lava_depth': 8.0}
    if ocean_source is not None:
        section['ocean_runtime'] = ocean_source
    if support.report['used']:
        # work/ is not pooled; retain source-only dependencies in chim-source.json.
        section['window_mount_support'] = support.report
    if sprite_rows:
        section['sprite_entities'] = sprite_rows
        section['sprite_assets'] = [dict(a, file=(work / 'sprites' / a['path']).relative_to(work.parent.parent).as_posix())
                                    for a in sprite_assets]
    if spec.get('outer_ring_chunks'):
        # terrain references: the heights one tile past the ground that the edge chunks' hull rings hold, so
        # the validator checks those rings (chim.validate.hull_seams) instead of stopping at the frame edge
        section['terrain_outer'] = {
            'low': [low[0] - step, low[1] - step], 'chunks': spec['outer_ring_chunks'],
            'heights': [[height_at(x, y) for x in range(low[0] - step, high[0] + step + 1, step)]
                        for y in range(low[1] - step, high[1] + step + 1, step)]}
    from chim.ownership import manifest
    if outside_apron:
        section['outside_apron'] = outside_apron
    section['frame_ownership'] = manifest(spec, selected)
    return spec, section, parity, len(prepared)
