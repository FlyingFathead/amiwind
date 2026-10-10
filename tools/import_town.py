#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Convert one owned town's terrain, scenery and residents into bounded sub-cells.

Generic form of the Balmora converter. The town comes from config/towns.json
and its config file (balmora.json, vivec_arena.json): frame, sub-cell
settings, map prefix, region cap, arrival/return points, worldspawn message
and region/door file names. See docs/TOWN_IMPORT.md.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from PIL import Image
from mwad.audit import audit, BSA, normpath
from mwad.paths import child_ci, ensure_external, resolve_data_files
from mwad.npc import load_master, outfit, greeting_fixture, behavior_record, greeting_settings
from town_config import load_settings, registry_row, resident_exclusions, town_field
from town_regions import (regions, select_references, audit_coverage, owner, town_model_profile, collision_coverage,
                          intersects, local_bounds)
from build_jobs import add_jobs, resolve_jobs
from build_parallel import ordered_map
from prepare_scenery import export_refs, bsa_read
from prepare_mesh_bsp import append_meshes, _prepare_model
from prepare_quake import box, brush, miptex, wad
from prepare_area import build_resident, entity
import npc_lod
from npc_anim import foot_class, publish as publish_anim, voices_of
import npc_items
from player_hull import lumps, pack_lumps, rebuild_world_hull
from surface_flatten import load_profiles
from actor_grounding import fields as grounding_fields
from bound_balmora_visuals import bound_visuals
from vis_options import DEFAULT_VIS_MODE, add_vis_option, light_args, map_threads, vis_args
from known_inputs import input_sha256

ROOT = Path(__file__).resolve().parents[1]
# Vertical extent of a town frame's sealed box (terrain_map): ground brushes
# start at the floor, the sky box closes at the ceiling. Terrain above the
# ceiling puts the spawn point outside the box (the map leaks).
TERRAIN_FLOOR, TERRAIN_CEILING = -1024, 2048


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def source_receipt(data, settings):
    files = [child_ci(data, 'Morrowind.esm'), child_ci(data, 'Morrowind.bsa')]
    files += [p for p in data.rglob('*') if p.is_file() and p.relative_to(data).parts[0].casefold() in ('meshes', 'textures')]
    return {'geometry': {k: settings[k] for k in ('source_cell', 'source_radius', 'centre', 'scale')},
            'files': {p.relative_to(data).as_posix(): input_sha256(p) for p in sorted(files)}}


def in_frame(reference, settings):
    """Optional frame filter: keep placements whose origin lies in the bounds.

    Balmora's frame is exactly its 3x3 source cells and has no filter. A frame
    centred off the cell grid (Vivec's Arena) audits whole cells around it and
    keeps only what stands inside its bounds plus reference_margin. Points
    (residents, markers) are judged by their origin; visible objects are also
    kept when their footprint reaches into the frame (footprint_references).
    """
    margin = settings.get('reference_margin')
    if margin is None:
        return True
    low, high = settings['bounds']
    point = [(reference['position'][i] - settings['centre'][i]) * settings['scale'] for i in range(2)]
    return all(low[i] - margin <= point[i] <= high[i] + margin for i in range(2))


def footprint_in_frame(reference, settings):
    """A converted reference whose whole-object bounds reach into the frame.

    Overlap is measured from the object bounds, never just its origin (as for
    sub-cells, town_regions.py): a Vivec canton whose origin lies outside the
    frame still carries the walkways its residents stand on inside it
    (VIVEC-ARENA-ACTORS-32).
    """
    margin = settings.get('reference_margin')
    if margin is None:
        return True
    low, high = settings['bounds']
    frame = [[v - margin for v in low], [v + margin for v in high]]
    return intersects(local_bounds(reference, settings['centre'], settings['scale']), frame)


def frame_references(out, settings):
    """The frame's source placements: origin in the frame, or a converted
    footprint that reaches into it (the scenery index holds only those)."""
    index = out / 'scenery/scenery-index.json'
    footprint = ({r['number'] for r in json.loads(index.read_text())['references']}
                 if settings.get('reference_margin') is not None and index.is_file() else set())
    return [r for r in json.loads((out / 'audit/placements.json').read_text())
            if in_frame(r, settings) or r['number'] in footprint]


def split_references(references):
    """Visible scenery to convert, and the deferred residents and markers."""
    selected, deferred = [], []
    for r in references:
        model = normpath(r.get('model', ''))
        if r.get('type') in ('NPC_', 'CREA', 'LEVC', 'LEVI'):
            deferred.append(dict(r, status='resident conversion' if r['type'] == 'NPC_' else 'creature simulation pending'))
        elif not model or model.rsplit('/', 1)[-1].startswith('marker_'):
            deferred.append(dict(r, status='nonvisual source marker'))
        else:
            selected.append(r)
    return selected, deferred


def lava_split(data, selected, deferred):
    """Lava pools leave the scenery and become Quake liquid (tools/lava.py, docs/LAVA.md): returns
    (selected, deferred, pools) with the pools in world units. --lava static keeps them as models."""
    import lava
    if lava.lava_mode() != 'quake':
        return selected, deferred, []
    molten = lava.molten_objects_of(child_ci(data, 'Morrowind.esm'))
    hot = [r for r in selected if r.get('id', '').casefold() in molten]
    if not hot:
        return selected, deferred, []
    pools = lava.pools_of(data, hot, molten)
    numbers = {r['number'] for r in hot}
    return ([r for r in selected if r['number'] not in numbers],
            deferred + [dict(r, status='lava liquid (tools/lava.py)') for r in hot], pools)


def lava_pools(out, data=None, references=None):
    """The pools a source stage converted (lava-pools.json). A source stage from before the lava
    conversion has no file: it is valid only when its town has no lava pool, checked again here."""
    path = out / 'lava-pools.json'
    if path.is_file():
        return json.loads(path.read_text())['pools']
    if data is not None and references is not None:
        import lava
        if lava.lava_mode() == 'quake':
            molten = lava.molten_objects_of(child_ci(data, 'Morrowind.esm'))
            if any(r.get('id', '').casefold() in molten for r in references):
                raise ValueError('This source stage predates the lava conversion and its town has lava pools: '
                                 'use a new work folder (or --lava static)')
    return []


def scenery_groups(settings, selected):
    profiles = {normpath('meshes/' + r['model']): {'collision_source': 'root_node_or_visual'}
                for r in selected}
    return {town_field(settings, 'visual_group'): {'references': [r['number'] for r in selected], 'visual_profiles': profiles}}


def footprint_references(data, out, placements, settings, jobs):
    """Numbers of the audited visible placements whose converted bounds reach
    into the frame. Bounds exist only after conversion, so every visible
    placement of the audited cells is measured once in a scratch export."""
    candidates, _ = split_references(placements)
    probe = out / 'frame-footprint'
    if probe.exists():
        shutil.rmtree(probe)
    report = export_refs(data, probe, candidates, scenery_groups(settings, candidates), [*settings['centre'], 0],
                         metadata={'runtime_bounds': settings['bounds']}, jobs=jobs)
    if report['errors']:
        raise ValueError(town_field(settings, 'title') + ' footprint measurement incomplete; inspect '
                         + str(probe / 'conversion-errors.json'))
    index = json.loads((probe / 'scenery-index.json').read_text())
    numbers = {r['number'] for r in index['references'] if footprint_in_frame(r, settings)}
    shutil.rmtree(probe)
    return numbers


def collect(data, out, jobs, settings):
    title = town_field(settings, 'title')
    audit(data, out / 'audit', tuple(settings['source_cell']), settings['source_radius'], 2,
          missing_land=settings.get('missing_land'))
    placements = json.loads((out / 'audit/placements.json').read_text())
    footprint = (footprint_references(data, out, placements, settings, jobs)
                 if settings.get('reference_margin') is not None else set())
    references = [r for r in placements if in_frame(r, settings) or r['number'] in footprint]
    selected, deferred = split_references(references)
    selected, deferred, pools = lava_split(data, selected, deferred)
    import lava
    write_json(out / 'lava-pools.json', {'mode': lava.lava_mode(), 'pools': pools})
    groups = scenery_groups(settings, selected)
    report = export_refs(data, out / 'scenery', selected, groups, [*settings['centre'], 0],
                         metadata={'runtime_bounds': settings['bounds']}, jobs=jobs)
    write_json(out / 'source-catalogue.json', {'references': references, 'deferred': deferred})
    if report['errors'] or report['converted_references'] != len(selected):
        raise ValueError(title + ' conversion incomplete; inspect scenery/conversion-errors.json')
    index = json.loads((out / 'scenery/scenery-index.json').read_text())
    entries = regions(settings)
    write_json(out / 'coverage.json', audit_coverage(index, entries, settings))
    return settings, index, entries, references


def ground_assets(data, audit_path, palette, pools=()):
    pal = Image.new('P', (1, 1)); pal.putpalette(palette)
    materials = json.loads((audit_path / 'materials.json').read_text())
    bsa = BSA(child_ci(data, 'Morrowind.bsa'))
    textures = []
    for key, record in materials.items():
        if record['texture']:
            name = normpath('textures/' + record['texture'])
            source = next((n for n in (str(PurePosixPath(name).with_suffix('.dds')), name) if n in bsa.entries), None)
            if source is None: raise ValueError('Missing terrain material ' + name)
            im = Image.open(io.BytesIO(bsa_read(bsa, source))).convert('RGB')
        else:
            im = Image.open(io.BytesIO(bsa_read(bsa, 'textures/_land_default.dds'))).convert('RGB')
        im = im.resize((32, 32), Image.Resampling.BOX).quantize(palette=pal, dither=Image.Dither.NONE)
        textures.append(('g' + key, 68, miptex('g' + key, im)))
    for name, color in [('stone', (80, 79, 70)), ('*water', (65, 87, 91)), ('sky', (102, 119, 136))]:
        im = (Image.open(io.BytesIO(bsa_read(bsa, 'textures/water/water00.dds'))).convert('RGB').resize((64, 64), Image.Resampling.BOX)
              if name == '*water' else Image.new('RGB', (256, 128) if name == 'sky' else (64, 64), color))
        textures.append((name, 68, miptex(name, im.quantize(palette=pal, dither=Image.Dither.NONE))))
    if pools:
        import lava
        from npc_geometry import Assets
        layers = max((p['layers'] for p in pools), key=len)
        textures += lava.wad_entries(Assets(data, bsa).texture, layers, pal)
    return wad(textures)


def terrain_sample(grids, settings, x, y):
    wx, wy = [settings['centre'][i] + v / settings['scale'] for i, v in enumerate((x, y))]
    cx, cy = math.floor(wx / 8192), math.floor(wy / 8192)
    if (cx, cy) not in grids:
        # The last vertex is also the previous source cell's east/north edge.
        if (cx - 1, cy) in grids and wx == cx * 8192: cx -= 1
        if (cx, cy - 1) in grids and wy == cy * 8192: cy -= 1
        if (cx, cy) not in grids and (cx - 1, cy - 1) in grids and wx == cx * 8192 and wy == cy * 8192:
            cx -= 1; cy -= 1
    grid = grids[cx, cy]
    ix, iy = (wx - cx * 8192) / 128, (wy - cy * 8192) / 128
    return grid, cx, cy, ix, iy


def terrain_material(grids, settings, x, y):
    grid, cx, cy, ix, iy = terrain_sample(grids, settings, x, y)
    tx, ty = min(15, math.floor(ix/4)), min(15, math.floor(iy/4))
    material = grid['materials'][ty][tx]
    for repair in settings.get('terrain_material_repairs', []):
        if repair['cell'] == [cx, cy] and repair['tile'] == [tx, ty]:
            if material != repair['source_material']:
                raise ValueError('Terrain repair no longer matches its source tile')
            material = repair['material']
    return material


def terrain_at(grids, settings, x, y):
    grid, cx, cy, ix, iy = terrain_sample(grids, settings, x, y)
    return grid['heights'][round(iy)][round(ix)] * settings['scale'], terrain_material(grids, settings, x, y)


def terrain_map(entry, grids, settings, spawn, timings, pools=(), lava_volumes=None):
    low, high = entry['coverage']; step = settings['terrain_step']; brushes = []
    for y in range(low[1], high[1], step):
        for x in range(low[0], high[0], step):
            corners = []
            # A terrain tile owns its area, not the northern neighbour sampled
            # at the final height corner. Sample material inside the quad.
            material = terrain_material(grids, settings, x+step/2, y+step/2)
            for dx, dy in ((0, 0), (step, 0), (step, step), (0, step)):
                z, _ = terrain_at(grids, settings, x + dx, y + dy)
                corners.append([x + dx, y + dy, z])
            for ids in ((0, 1, 2), (0, 2, 3)):
                tri = [corners[i] for i in ids]
                pts = tri + [[p[0], p[1], TERRAIN_FLOOR] for p in tri]
                brushes.append(brush(pts, [(0, 1, 2), (3, 4, 5), (0, 1, 4), (1, 2, 5), (2, 0, 3)], f'g{material}'))
    x0, y0 = low; x1, y1 = high
    brushes += [box([x0, y0, -1000], [x1, y1, 0], '*water'),
                box([x0 - 32, y0 - 32, TERRAIN_FLOOR - 32], [x1 + 32, y1 + 32, TERRAIN_FLOOR], 'stone'),
                box([x0 - 32, y0 - 32, TERRAIN_CEILING], [x1 + 32, y1 + 32, TERRAIN_CEILING + 32], 'sky'),
                box([x0 - 32, y0 - 32, TERRAIN_FLOOR], [x0, y1 + 32, TERRAIN_CEILING], 'sky'),
                box([x1, y0 - 32, TERRAIN_FLOOR], [x1 + 32, y1 + 32, TERRAIN_CEILING], 'sky'),
                box([x0, y0 - 32, TERRAIN_FLOOR], [x1, y0, TERRAIN_CEILING], 'sky'),
                box([x0, y1, TERRAIN_FLOOR], [x1, y1 + 32, TERRAIN_CEILING], 'sky')]
    # Lava pools whose centre lies in this region's coverage (tools/lava.py: one liquid brush over a bed each).
    import lava
    centre = [*settings['centre'], 0]
    mine = [p for p in pools if low[0] <= (lava.polygon_centroid(p['hull'])[0] - centre[0]) * settings['scale'] < high[0]
            and low[1] <= (lava.polygon_centroid(p['hull'])[1] - centre[1]) * settings['scale'] < high[1]]
    lava_brushes, lava_entities, _ = lava.map_parts(mine, centre, settings['scale'])
    lava_entities += lava.loop_entities(mine, centre, settings['scale'], lava_volumes or {})
    return ('{\n"classname" "worldspawn"\n"wad" "terrain.wad"\n"message" "' + town_field(settings, 'message') + '"\n'
            + timings + '\n' + '\n'.join(brushes + lava_brushes) + '\n}\n'
            + entity({'classname': 'info_player_start', 'origin': ' '.join(map(str, spawn)), 'angle': 90}) + '\n'
            + ''.join(text + '\n' for text in lava_entities))


def travel_pose(values, settings):
    """Original DODT-style pose (x, y, z, rx, ry, rz) to this frame's local pose.

    Returns None outside the frame bounds. Z is the shared feet-to-origin lift
    of every converted travel arrival.
    """
    point = [(values[i] - (settings['centre'][i] if i < 2 else 0)) * settings['scale'] for i in range(3)]
    if not all(settings['bounds'][0][i] <= point[i] <= settings['bounds'][1][i] for i in range(2)):
        return None
    point[2] += 16.875
    return point, (90 - math.degrees(values[5])) % 360


def travel_point(kinds, identifier, settings):
    candidates = []
    for tag, raw in kinds['NPC_'][identifier]:
        if tag != 'DODT': continue
        pose = travel_pose(struct.unpack('<6f', raw), settings)
        if pose is not None:
            candidates.append(pose)
    if len(candidates) != 1: raise ValueError('Travel destination must resolve uniquely: ' + identifier)
    return candidates[0]


def arrival_point(kinds, settings):
    """Arrival from the town block: a travel NPC's destination or an explicit pose."""
    arrival = town_field(settings, 'arrival')
    if 'travel_npc' in arrival:
        return travel_point(kinds, arrival['travel_npc'], settings)
    pose = travel_pose([*arrival['source_position'], 0, 0, arrival.get('source_rotation_z', 0)], settings)
    if pose is None:
        raise ValueError('Explicit town arrival is outside the frame')
    return pose


def return_point(kinds, settings):
    """Return travel into another area, or the inert 0 0 0 0 directory slot."""
    returning = town_field(settings, 'return')
    if returning is None:
        return [0, 0, 0], 0
    other = json.loads((ROOT / 'config' / returning['config']).read_text())
    return travel_point(kinds, returning['travel_npc'], other)


def residents(data, scene, out, references, settings, kinds, topics, palette, ffmpeg, jobs):
    skip = resident_exclusions(settings)
    cast = [r for r in references if r['type'] == 'NPC_' and r['id'].casefold() not in skip]
    tasks, models = [], {}
    for identifier in sorted({r['id'].casefold() for r in cast}):
        appearance = npc_items.attach_items(kinds, identifier, outfit(kinds, identifier))
        appearance['foot'] = foot_class(kinds, appearance)
        appearance['voices'] = voices_of(topics, appearance)
        tasks.append((data, palette, appearance, greeting_fixture(topics, appearance), ffmpeg, npc_lod.task_settings()))
    for identifier, raw, voice, record in ordered_map(build_resident, tasks, min(jobs, len(tasks))):
        stem = 'a_' + hashlib.sha256(identifier.encode()).hexdigest()[:12]
        record.update(model='progs/' + stem + '.mdl', voice='npc/' + stem + '.wav')
        (scene / 'id1' / record['model']).write_bytes(raw)
        publish_anim(scene / 'id1', record)
        npc_items.publish(scene / 'id1', record)
        (scene / 'id1/sound' / record['voice']).write_bytes(voice)
        record['settings'] = greeting_settings(kinds, behavior_record(kinds['NPC_'][identifier], settings['scale']), settings['scale'])
        models[identifier] = record
        print(town_field(settings, 'title') + ' resident ready:', identifier, flush=True)
    # Near/far models (tools/npc_lod.py): near files and the pairing manifest.
    lod = npc_lod.publish(scene / 'id1', models, kinds)
    write_json(out / 'residents.json', {'cast': cast, 'models': models, 'npc_lod': lod})
    return resident_entities(cast, models, settings)


def resident_entities(cast, models, settings):
    entities = []
    for ref in cast:
        if abs(ref['scale'] - 1) > 1e-5: raise ValueError('Resident scale requires separate bake')
        record = models[ref['id'].casefold()]; greeting = record['settings']
        point = [(v - (settings['centre'][i] if i < 2 else 0)) * settings['scale'] for i, v in enumerate(ref['position'])]
        entities.append(entity({**grounding_fields(ref['id']), 'classname': 'aw_npc', 'aw_ref': ref['number'], 'model': record['model'],
            'origin': ' '.join(f'{v:.5f}' for v in point),
            'angles': f"0 {-math.degrees(ref['rotation_radians'][2]):.5f} 0",
            'netname': record['appearance']['name'], 'aw_voice': record['voice'],
            'aw_line': record['greeting']['text'], 'aw_idle_step': record['step'],
            'aw_hello_distance': greeting['distance'], 'aw_hello_reset': greeting['reset_distance'],
            'aw_greet_duration': greeting['duration']}))
    return entities


def region_directory_text(settings, entries, arrival, yaw, returning, return_yaw):
    """Native region directory (AWBR1, aw_region.c read_regions)."""
    rows = ['AWBR1 ' + ' '.join(map(str, [len(entries), settings['hysteresis'], settings['draw_distance'], *arrival, yaw, *returning, return_yaw]))]
    for entry in entries:
        rows.append(entry['name'] + ' ' + ' '.join(map(str, [*entry['core'][0], *entry['core'][1], *entry['coverage'][0], *entry['coverage'][1]])))
    return '\n'.join(rows) + '\n'


def door_bank_text(settings, references, index, rooms=None):
    """Exterior door bank (AWD3): original DOOR/DODT records of converted doors.

    rooms: optional {original cell casefold: room map} of the converted rooms
    (town_interiors). A load door into one of them gets its target and
    original arrival; every other door stays unavailable ("-").
    """
    from town_interiors import BANK_ROWS, exterior_link
    converted = {r['number']: r for r in index['references']}
    doors = ['AWD3']
    for ref in references:
        if ref['type'] != 'DOOR' or not ref.get('destination') or ref['number'] not in converted: continue
        bounds = [[(v - (settings['centre'][i] if i < 2 else 0)) * settings['scale'] for i, v in enumerate(p)] for p in converted[ref['number']]['bounds']]
        label = ref.get('destination_cell') or 'Exterior world'
        if any(c in label for c in '\r\n'): raise ValueError('Invalid door label')
        link = exterior_link(ref, rooms) if rooms else None
        target, place = ('-', [0, 0, 0, 0]) if link is None else (link[0], [*link[1], link[2]])
        doors.append(town_field(settings, 'map') + ' ' + target + ' ' + str(ref['number']) + ' ' + ' '.join(map(str, [*bounds[0], *bounds[1], *place])) + ' ' + label)
    if len(doors) - 1 > BANK_ROWS:
        raise ValueError(town_field(settings, 'title') + ': door bank exceeds %d rows' % BANK_ROWS)
    return '\n'.join(doors) + '\n'


def spawn_at(text, point):
    """The arrival region's spawn entity at the stored arrival; the engine falls
    back to this spawn point when an arrival search fails."""
    def place(match):
        block = match[0]
        if '"classname" "info_player_start"' not in block:
            return block
        return re.sub(r'"origin" "[^"\n]*"', '"origin" "' + ' '.join(map(str, point)) + '"', block)
    return re.sub(r'\{[^{}]*\}', place, text)


def publish(scene, out, settings, entries, references, index, npc_entities, arrival, yaw, returning, return_yaw, rooms=None):
    # Every region seeds all stable actor IDs. The runtime restores their latest
    # state and deactivates residents outside this region's coverage.
    home = entries[owner(arrival, entries)]
    for entry in entries:
        payload = lumps((out / entry['name'] / 'scene.bsp').read_bytes())
        text = payload[0].decode('cp1252').rstrip('\0\n')
        if entry is home:
            text = spawn_at(text, arrival)
        payload[0] = (text + '\n' + '\n'.join(npc_entities) + '\n\0').encode('cp1252')
        (scene / 'id1/maps' / (entry['name'] + '.bsp')).write_bytes(pack_lumps(payload))
    shutil.copyfile(scene / 'id1/maps' / (entries[owner(arrival, entries)]['name'] + '.bsp'),
                    scene / 'id1/maps' / (town_field(settings, 'map') + '.bsp'))
    (scene / 'id1' / town_field(settings, 'region_file')).write_text(
        region_directory_text(settings, entries, arrival, yaw, returning, return_yaw))
    (scene / 'id1' / town_field(settings, 'door_file')).write_text(door_bank_text(settings, references, index, rooms), encoding='cp1252')


def prepare(town, data_files, scene, out, qbsp, vis, light, ffmpeg='ffmpeg', jobs=None, collect_only=False,
            vis_mode=DEFAULT_VIS_MODE, dry_run=False):
    """Convert one town; dry_run converts every region and room, records limit
    failures in <out>/dry-run.json instead of stopping, and publishes nothing."""
    settings = load_settings(town); title = town_field(settings, 'title')
    blocked = registry_row(town).get('blocked')
    if blocked and not dry_run:
        raise ValueError(title + ' is blocked in config/towns.json: ' + blocked + ' (measure it with --dry-run)')
    data = resolve_data_files(data_files); scene = ensure_external(scene, title + ' scene')
    out = ensure_external(out, title + ' work'); jobs = resolve_jobs(jobs)
    if not out.exists():
        out.mkdir(parents=True)
        settings, index, entries, references = collect(data, out, jobs, settings)
        write_json(out / 'source-receipt.json', source_receipt(data, settings))
    else:
        # Explicit resume reuses immutable source conversion, never another input.
        if not (out / 'source-receipt.json').is_file() or json.loads((out / 'source-receipt.json').read_text()) != source_receipt(data, settings):
            raise ValueError('Resume geometry inputs differ or are unverified; use a fresh output directory')
        receipt = json.loads((out / 'audit/audit.json').read_text())
        if receipt['input']['esm_sha256'] != input_sha256(child_ci(data, 'Morrowind.esm')):
            raise ValueError('Resume source master differs')
        index = json.loads((out / 'scenery/scenery-index.json').read_text())
        entries = regions(settings)
        references = frame_references(out, settings)
    if collect_only: return json.loads((out / 'coverage.json').read_text())
    palette = (scene / 'id1/gfx/palette.lmp').read_bytes()
    ext = lumps((scene / 'id1/maps/seyda.bsp').read_bytes())[0].decode('cp1252')
    timings = '\n'.join(re.findall(r'"aw_(?:hand_[^"\n]+|eye_height)" "[^"\n]+"', ext))
    grids = {tuple(g['cell']): g for g in json.loads((out / 'audit/terrain-source.json').read_text())}
    pools = lava_pools(out, data, references)
    # the pools' loop sound (their script's "lava layer"), from the user's own files, beside the residents' voices
    import lava
    lava_volumes = lava.convert_sounds(data, pools, scene / 'id1/sound', ffmpeg)[0] if pools else {}
    terrain_wad = ground_assets(data, out / 'audit', palette, pools)
    kinds, cells, topics = load_master(child_ci(data, 'Morrowind.esm'))
    arrival, yaw = arrival_point(kinds, settings)
    returning, return_yaw = return_point(kinds, settings)
    npc_entities = residents(data, scene, out, references, settings, kinds, topics, palette, ffmpeg, jobs)
    write_json(out / 'coverage.json', audit_coverage(index, entries, settings))
    profiles = index['groups'][town_field(settings, 'visual_group')]['visual_profiles']; flatten = load_profiles()
    tasks = []
    for mi, model in enumerate(index['models']):
        # Select immutable offline representations; every placed reference and
        # authored collision mesh is retained. The original MWSC mesh is kept.
        profile = town_model_profile(profiles[model['source']], model['source'], model['triangles'])
        if model['source'] in flatten: profile['flatten'] = flatten[model['source']]
        profiles[model['source']] = profile
        tasks.append((mi, model, profile, out / 'scenery/scenery.mwpak', index['textures']))
    write_json(out / 'scenery/scenery-index.json', index)
    prepared = dict(ordered_map(_prepare_model, tasks, min(jobs, len(tasks))))
    print(title + ' shared geometry ready:', len(prepared), flush=True)
    reports, failures = [], {}

    def limit(name, message):
        if not dry_run:
            raise ValueError(message)
        failures.setdefault(name, []).append(message)
        print(title + ' limit:', message, flush=True)
    context = {'entries': entries, 'index': index, 'settings': settings, 'grids': grids, 'terrain_wad': terrain_wad,
               'pools': pools, 'lava_volumes': lava_volumes,
               'timings': timings, 'arrival': arrival, 'prepared': prepared, 'out': out, 'scene': scene,
               'qbsp': qbsp, 'vis': vis, 'light': light, 'vis_mode': vis_mode, 'dry_run': dry_run}
    for entry, report, messages in compile_regions(context, jobs):
        for message in messages:
            limit(entry['name'], message)
        reports.append(report)
        print(title + ' region ready:', entry['name'], report['instances'], report['clipnodes'], flush=True)
    rooms = convert_interiors(data, scene, settings, qbsp, vis, light, ffmpeg, jobs, vis_mode, timings, dry_run)
    if dry_run:
        for name, failure in rooms['failed'].items():
            failures.setdefault(name, []).append(failure['error'])
        write_json(out / 'dry-run.json', {'town': town_field(settings, 'id'), 'failures': failures,
                                          'excluded': rooms['excluded'], 'rooms': rooms['receipt'],
                                          'regions': [dict(r, references=len(r['references'])) for r in reports]})
        return {'regions': len(entries), 'failures': len(failures), 'rooms': len(rooms['receipt'])}
    # The stored arrival is the engine's own standing spot for the original
    # pose on the converted collision, so the runtime search's first candidate
    # is valid (VIVEC-ARENA-TP-ARRIVAL-32).
    from arrival_spot import resolve
    arrival = resolve(lambda name: (out / name / 'scene.bsp').read_bytes(), entries, arrival, owner)
    # Publish converted payloads only after every region and room passes its limits.
    publish(scene, out, settings, entries, references, index, npc_entities, arrival, yaw, returning, return_yaw,
            rooms['cells'])
    write_json(out / 'regions.json', {'settings': settings, 'arrival': arrival, 'yaw': yaw, 'return': returning, 'return_yaw': return_yaw, 'regions': entries, 'reports': reports})
    if rooms['receipt'] or rooms['excluded']:
        write_json(out / 'interiors.json', {'rooms': rooms['receipt'], 'excluded': rooms['excluded']})
    return {'regions': len(entries), 'arrival': arrival, 'scenery_references': len(index['references']),
            **({'interiors': len(rooms['receipt']), 'excluded_interiors': len(rooms['excluded'])}
               if rooms['receipt'] or rooms['excluded'] else {})}


def compile_regions(context, jobs):
    """Yield (entry, report, limit messages) for every region, in region order.

    Regions are independent (each writes only its own folder; the collision
    cache is content-addressed): they compile side by side on the shared pool,
    tool threads and model workers split between them, and each region's log
    output is printed in region order (BUILD-IDLE-STAGES-33; the serial loop held
    12 workers on 2.8 cores in the v0.0.32 build). Bytes equal the serial loop's.
    """
    import pickle
    from build_scratch import scratch_dir
    entries = context['entries']
    workers = min(jobs, max(1, len(entries)))
    threads = map_threads(jobs, workers)
    with scratch_dir('aw-town-regions-') as temporary:
        path = Path(temporary) / 'context.pickle'
        path.write_bytes(pickle.dumps(context, protocol=4))
        try:
            cache, shared = region_cache(context)
        except (TypeError, ValueError, OSError):  # an input that has no content key: convert every region
            cache, shared = None, None
        owner_index = owner(context['arrival'], entries)
        tasks = [(str(path), number, threads, cache,
                  None if cache is None else dict(shared, entry=entries[number], arrival_region=number == owner_index))
                 for number in range(len(entries))]
        # Longest first (build_costs): history, else the placed references per region.
        from build_costs import costed_map
        sizes = {entry['name']: len(select_references(context['index'], entry, context['settings'])) + 1
                 for entry in entries}
        pool = costed_map('town-%s-regions' % town_field(context['settings'], 'id'), _compile_region_cached, tasks,
                          [entry['name'] for entry in entries], workers, fallback=sizes.get)
        for entry, ((report, messages), text) in zip(entries, pool):
            if text:
                sys.stdout.write(text); sys.stdout.flush()
            yield entry, report, messages


_REGION_CONTEXT = {}


def _region_context(path):
    """The shared region inputs, read once per worker process."""
    if path not in _REGION_CONTEXT:
        import pickle
        _REGION_CONTEXT.clear()
        _REGION_CONTEXT[path] = pickle.loads(Path(path).read_bytes())
    return _REGION_CONTEXT[path]


def region_cache(context):
    """(the town region unit cache, the inputs every region shares by content), or (None, None) when the cache
    is off or the game data identity is unknown. A region's key adds its record and whether it holds the town's
    arrival (BUILD-IMAGE-NO-RESUME-33: the stage resumes from its finished regions)."""
    import hashlib
    from pass_cache import UnitCache, game_data_digest, input_digest, tool_digest
    cache = UnitCache.open('town-region', {}, __file__)
    identity = game_data_digest() if cache is not None else None
    if identity is None or context.get('dry_run'):
        return None, None
    out, scene = Path(context['out']), Path(context['scene'])

    def file_digest(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None
    shared = {'game_data': identity, 'settings': input_digest(context['settings']),
              'index': input_digest(context['index']),
              'grids': input_digest(sorted([list(k), v] for k, v in context['grids'].items())),
              'terrain_wad': hashlib.sha256(context['terrain_wad']).hexdigest(), 'timings': context['timings'],
              'arrival': context['arrival'], 'vis_mode': context['vis_mode'],
              'scenery_packet': file_digest(out / 'scenery/scenery.mwpak'),
              'palette': file_digest(scene / 'id1/gfx/palette.lmp'),
              'tools': tool_digest(context['qbsp'], context['vis'], context['light'])}
    return cache, shared


def _compile_region_cached(task):
    """Worker: _compile_region, or the region recorded for the same inputs (its folder, receipt and log text).
    Rows that do not survive JSON exactly are never cached."""
    path, number, threads, cache, inputs = task
    if cache is None:
        return _compile_region((path, number, threads))
    from pass_cache import json_exact
    root = Path(_region_context(path)['out']) / inputs['entry']['name']
    row = cache.restore_unit(inputs, root) if not root.exists() else None
    if row is not None:
        return (row['report'], row['messages']), row['text']
    (report, messages), text = _compile_region((path, number, threads))
    row = {'report': report, 'messages': messages, 'text': text}
    if json_exact(row):
        cache.store_unit(inputs, row, root)
    return (report, messages), text


def _compile_region(task):
    """Worker: compile one town region; ((report, limit messages), its output text)."""
    from build_parallel import captured
    return captured(_compile_region_now, task)


def _compile_region_now(task):
    path, number, threads = task
    c = _region_context(path)
    entries, settings, out = c['entries'], c['settings'], c['out']
    entry = entries[number]
    messages = []

    def limit(message):
        # Without dry_run the first limit stops the stage, as the serial loop did.
        if not c['dry_run']:
            raise ValueError(message)
        messages.append(message)
    root = out / entry['name']; root.mkdir(exist_ok=True)
    selected = select_references(c['index'], entry, settings)
    if len(selected) + 32 > settings['entity_budget']:
        limit(f"{entry['name']}: entity budget exceeded ({len(selected)})")
    (root / 'terrain.wad').write_bytes(c['terrain_wad'])
    spawn = [(entry['core'][0][i] + entry['core'][1][i]) / 2 for i in range(2)]
    spawn.append(terrain_at(c['grids'], settings, *spawn)[0] + 40)
    if entry == entries[owner(c['arrival'], entries)]: spawn = c['arrival']
    pools = c.get('pools') or ()          # lava pools (tools/lava.py); a town without lava calls the map writer as before
    (root / 'terrain.map').write_text(terrain_map(entry, c['grids'], settings, spawn, c['timings'], pools,
                                                  c.get('lava_volumes')) if pools
                                      else terrain_map(entry, c['grids'], settings, spawn, c['timings']))
    qbsp, vis, light = c['qbsp'], c['vis'], c['light']
    with (root / 'compile.log').open('w') as log:
        for exe, args in ((qbsp, ['-nopercent', 'terrain.map']), (vis, vis_args('terrain.bsp', threads, c['vis_mode'])),
                          (light, light_args('-minlight', '24', 'terrain.bsp'))):
            subprocess.run([str(Path(exe).resolve()), *args], cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True)
    base = root / 'base.bsp'; shutil.copyfile(root / 'terrain.bsp', base)
    rebuild_world_hull(base, root / 'terrain.map', qbsp)
    report = append_meshes(base, root / 'scene.bsp', out / 'scenery', c['scene'] / 'id1/gfx/palette.lmp',
                           centre=settings['centre'], jobs=threads, references=selected,
                           prepared_models=c['prepared'], retain_dressing=True,
                           collision_bounds=collision_coverage(entry, settings),
                           collision_compiler=qbsp, collision_cache=out / 'collision-cache')
    if report['unique_models'] > settings['model_budget']:
        limit(f"{entry['name']}: inline model budget exceeded ({report['unique_models']} > {settings['model_budget']})")
    bounded, visual_report = bound_visuals((root / 'scene.bsp').read_bytes(), entry['coverage'])
    (root / 'scene.bsp').write_bytes(bounded)
    report.update(region=entry, references=selected, visual_coverage=visual_report)
    write_json(root / 'conversion.json', report)
    return report, messages


def convert_interiors(data, scene, settings, qbsp, vis, light, ffmpeg, jobs, vis_mode, timings, dry_run=False):
    """The town's listed rooms (town_interiors), their residents and door banks."""
    import town_interiors
    from prepare_area import populate
    result = town_interiors.convert(data, scene, settings, qbsp, vis, light, timings, jobs, vis_mode, dry_run)
    result['receipt'] = []
    if result['rooms']:
        try:
            populate(data, scene, result['rooms'], result['reports'], ffmpeg, jobs, include_exterior=False,
                     report_name=town_field(settings, 'id') + '-interiors.json', doors=False,
                     exclude_residents=resident_exclusions(settings))
        except ValueError as error:
            if not dry_run:
                raise
            result['failed']['residents'] = {'cell': '', 'error': 'residents: %s' % error}
        result['receipt'] = town_interiors.write_room_banks(data, scene, result)
        reports = {r['map']: r for r in result['reports']}
        for row in result['receipt']:
            report = reports[row['map']]
            row.update({k: report.get(k) for k in ('faces', 'clipnodes', 'bytes', 'instances', 'unique_models',
                                                     'coordinate_extent')})
    return result


def parser(description=__doc__, town=True):
    p = argparse.ArgumentParser(description=description)
    if town:
        p.add_argument('--town', required=True, help='Town id from config/towns.json (balmora, vivec_arena)')
    for name in ('data-files', 'scene', 'out'): p.add_argument('--' + name, type=Path, required=True)
    for name in ('qbsp', 'vis', 'light'): p.add_argument('--' + name, type=Path)
    p.add_argument('--ffmpeg', default='ffmpeg'); p.add_argument('--collect-only', action='store_true'); add_jobs(p)
    if town:
        p.add_argument('--dry-run', action='store_true',
                       help='Convert every region and room, record limit failures in <out>/dry-run.json, publish nothing')
    add_vis_option(p)
    npc_lod.add_converter_options(p)
    return p


if __name__ == '__main__':
    p = parser()
    from scenery_reduce import add_options, apply_options
    add_options(p)
    a = p.parse_args()
    apply_options(a)
    npc_lod.apply_options(a)
    import build_profile; build_profile.instrument('town')  # sub-stage timers (docs/BUILD_PROFILE.md)
    print(json.dumps(prepare(a.town, a.data_files, a.scene, a.out, a.qbsp, a.vis, a.light, a.ffmpeg, a.jobs,
                             a.collect_only, a.vis_mode, a.dry_run), indent=2))
