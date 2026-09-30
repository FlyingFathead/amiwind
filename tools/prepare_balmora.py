#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Convert owned Balmora terrain, scenery and residents into bounded sub-cells."""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
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
from balmora_regions import config, regions, select_references, audit_coverage, owner, visual_profile
from build_jobs import add_jobs, resolve_jobs
from build_parallel import ordered_map
from prepare_scenery import export_refs, bsa_read
from prepare_mesh_bsp import append_meshes, _prepare_model
from prepare_quake import box, brush, miptex, wad
from prepare_area import build_resident, entity
from player_hull import lumps, pack_lumps, rebuild_world_hull
from surface_flatten import load_profiles


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def source_receipt(data, settings):
    files = [child_ci(data, 'Morrowind.esm'), child_ci(data, 'Morrowind.bsa')]
    files += [p for p in data.rglob('*') if p.is_file() and p.relative_to(data).parts[0].casefold() in ('meshes', 'textures')]
    return {'geometry': {k: settings[k] for k in ('source_cell', 'source_radius', 'centre', 'scale')},
            'files': {p.relative_to(data).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}}


def collect(data, out, jobs):
    settings = config()
    audit(data, out / 'audit', tuple(settings['source_cell']), settings['source_radius'], 2)
    references = json.loads((out / 'audit/placements.json').read_text())
    selected, deferred = [], []
    for r in references:
        model = normpath(r.get('model', ''))
        if r.get('type') in ('NPC_', 'CREA', 'LEVC', 'LEVI'):
            deferred.append(dict(r, status='resident conversion' if r['type'] == 'NPC_' else 'creature simulation pending'))
        elif not model or model.rsplit('/', 1)[-1].startswith('marker_'):
            deferred.append(dict(r, status='nonvisual source marker'))
        else:
            selected.append(r)
    profiles = {normpath('meshes/' + r['model']): {'collision_source': 'root_node_or_visual'}
                for r in selected}
    groups = {'balmora': {'references': [r['number'] for r in selected], 'visual_profiles': profiles}}
    report = export_refs(data, out / 'scenery', selected, groups, [*settings['centre'], 0],
                         metadata={'runtime_bounds': settings['bounds']}, jobs=jobs)
    write_json(out / 'source-catalogue.json', {'references': references, 'deferred': deferred})
    if report['errors'] or report['converted_references'] != len(selected):
        raise ValueError('Balmora conversion incomplete; inspect scenery/conversion-errors.json')
    index = json.loads((out / 'scenery/scenery-index.json').read_text())
    entries = regions(settings)
    write_json(out / 'coverage.json', audit_coverage(index, entries, settings))
    return settings, index, entries, references


def ground_assets(data, audit_path, palette):
    pal = Image.new('P', (1, 1)); pal.putpalette(palette)
    materials = json.loads((audit_path / 'materials.json').read_text())
    bsa = BSA(child_ci(data, 'Morrowind.bsa'))
    textures = []
    for key, record in materials.items():
        if record['texture']:
            name = normpath('textures/' + record['texture'])
            source = next((n for n in (str(Path(name).with_suffix('.dds')), name) if n in bsa.entries), None)
            if source is None: raise ValueError('Missing terrain material ' + name)
            im = Image.open(io.BytesIO(bsa_read(bsa, source))).convert('RGB')
        else:
            im = Image.new('RGB', (32, 32), (89, 85, 71))
        im = im.resize((32, 32), Image.Resampling.BOX).quantize(palette=pal, dither=Image.Dither.NONE)
        textures.append(('g' + key, 68, miptex('g' + key, im)))
    for name, color in [('stone', (80, 79, 70)), ('*water', (65, 87, 91)), ('sky', (102, 119, 136))]:
        im = Image.new('RGB', (256, 128) if name == 'sky' else (64, 64), color)
        textures.append((name, 68, miptex(name, im.quantize(palette=pal, dither=Image.Dither.NONE))))
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


def terrain_map(entry, grids, settings, spawn, timings):
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
                pts = tri + [[p[0], p[1], -1024] for p in tri]
                brushes.append(brush(pts, [(0, 1, 2), (3, 4, 5), (0, 1, 4), (1, 2, 5), (2, 0, 3)], f'g{material}'))
    x0, y0 = low; x1, y1 = high
    brushes += [box([x0, y0, -1000], [x1, y1, 0], '*water'),
                box([x0 - 32, y0 - 32, -1056], [x1 + 32, y1 + 32, -1024], 'stone'),
                box([x0 - 32, y0 - 32, 2048], [x1 + 32, y1 + 32, 2080], 'sky'),
                box([x0 - 32, y0 - 32, -1024], [x0, y1 + 32, 2048], 'sky'),
                box([x1, y0 - 32, -1024], [x1 + 32, y1 + 32, 2048], 'sky'),
                box([x0, y0 - 32, -1024], [x1, y0, 2048], 'sky'),
                box([x0, y1, -1024], [x1, y1 + 32, 2048], 'sky')]
    return ('{\n"classname" "worldspawn"\n"wad" "terrain.wad"\n"message" "Balmora"\n'
            + timings + '\n' + '\n'.join(brushes) + '\n}\n'
            + entity({'classname': 'info_player_start', 'origin': ' '.join(map(str, spawn)), 'angle': 90}) + '\n')


def travel_point(kinds, identifier, settings):
    candidates = []
    for tag, raw in kinds['NPC_'][identifier]:
        if tag != 'DODT': continue
        values = struct.unpack('<6f', raw)
        point = [(values[i] - (settings['centre'][i] if i < 2 else 0)) * settings['scale'] for i in range(3)]
        if all(settings['bounds'][0][i] <= point[i] <= settings['bounds'][1][i] for i in range(2)):
            point[2] += 16.875
            candidates.append((point, (90 - math.degrees(values[5])) % 360))
    if len(candidates) != 1: raise ValueError('Travel destination must resolve uniquely: ' + identifier)
    return candidates[0]


def residents(data, scene, out, references, settings, kinds, topics, palette, ffmpeg, jobs):
    cast = [r for r in references if r['type'] == 'NPC_']
    tasks, models = [], {}
    for identifier in sorted({r['id'].casefold() for r in cast}):
        appearance = outfit(kinds, identifier)
        tasks.append((data, palette, appearance, greeting_fixture(topics, appearance), ffmpeg))
    for identifier, raw, voice, record in ordered_map(build_resident, tasks, min(jobs, len(tasks))):
        stem = 'a_' + hashlib.sha256(identifier.encode()).hexdigest()[:12]
        record.update(model='progs/' + stem + '.mdl', voice='npc/' + stem + '.wav')
        (scene / 'id1' / record['model']).write_bytes(raw)
        (scene / 'id1/sound' / record['voice']).write_bytes(voice)
        record['settings'] = greeting_settings(kinds, behavior_record(kinds['NPC_'][identifier], settings['scale']), settings['scale'])
        models[identifier] = record
        print('Balmora resident ready:', identifier, flush=True)
    write_json(out / 'residents.json', {'cast': cast, 'models': models})
    return resident_entities(cast, models, settings)


def resident_entities(cast, models, settings):
    entities = []
    for ref in cast:
        if abs(ref['scale'] - 1) > 1e-5: raise ValueError('Resident scale requires separate bake')
        record = models[ref['id'].casefold()]; greeting = record['settings']
        point = [(v - (settings['centre'][i] if i < 2 else 0)) * settings['scale'] for i, v in enumerate(ref['position'])]
        entities.append(entity({'classname': 'aw_npc', 'aw_ref': ref['number'], 'model': record['model'],
            'origin': ' '.join(f'{v:.5f}' for v in point),
            'angles': f"0 {-math.degrees(ref['rotation_radians'][2]):.5f} 0",
            'netname': record['appearance']['name'], 'aw_voice': record['voice'],
            'aw_line': record['greeting']['text'], 'aw_idle_step': record['step'],
            'aw_hello_distance': greeting['distance'], 'aw_hello_reset': greeting['reset_distance'],
            'aw_greet_duration': greeting['duration']}))
    return entities


def publish(scene, out, settings, entries, references, index, npc_entities, arrival, yaw, returning, return_yaw):
    # Every region seeds all stable actor IDs. The runtime restores their latest
    # state and deactivates residents outside this region's coverage.
    for entry in entries:
        payload = lumps((out / entry['name'] / 'scene.bsp').read_bytes())
        text = payload[0].decode('cp1252').rstrip('\0\n')
        payload[0] = (text + '\n' + '\n'.join(npc_entities) + '\n\0').encode('cp1252')
        (scene / 'id1/maps' / (entry['name'] + '.bsp')).write_bytes(pack_lumps(payload))
    shutil.copyfile(scene / 'id1/maps' / (entries[owner(arrival, entries)]['name'] + '.bsp'), scene / 'id1/maps/balmora.bsp')
    rows = ['AWBR1 ' + ' '.join(map(str, [len(entries), settings['hysteresis'], settings['draw_distance'], *arrival, yaw, *returning, return_yaw]))]
    for entry in entries:
        rows.append(entry['name'] + ' ' + ' '.join(map(str, [*entry['core'][0], *entry['core'][1], *entry['coverage'][0], *entry['coverage'][1]])))
    (scene / 'id1/balmora-regions.txt').write_text('\n'.join(rows) + '\n')
    converted = {r['number']: r for r in index['references']}
    doors = ['AWD3']
    for ref in references:
        if ref['type'] != 'DOOR' or not ref.get('destination') or ref['number'] not in converted: continue
        bounds = [[(v - (settings['centre'][i] if i < 2 else 0)) * settings['scale'] for i, v in enumerate(p)] for p in converted[ref['number']]['bounds']]
        label = ref.get('destination_cell') or 'Exterior world'
        if any(c in label for c in '\r\n'): raise ValueError('Invalid door label')
        doors.append('balmora - ' + str(ref['number']) + ' ' + ' '.join(map(str, [*bounds[0], *bounds[1], 0, 0, 0, 0])) + ' ' + label)
    (scene / 'id1/scene-doors-balmora.txt').write_text('\n'.join(doors) + '\n', encoding='cp1252')


def prepare(data_files, scene, out, qbsp, vis, light, ffmpeg='ffmpeg', jobs=None, collect_only=False):
    data = resolve_data_files(data_files); scene = ensure_external(scene, 'Balmora scene')
    out = ensure_external(out, 'Balmora work'); jobs = resolve_jobs(jobs)
    if not out.exists():
        out.mkdir(parents=True)
        settings, index, entries, references = collect(data, out, jobs)
        write_json(out / 'source-receipt.json', source_receipt(data, settings))
    else:
        # Explicit resume reuses immutable source conversion, never another input.
        settings = config()
        if not (out / 'source-receipt.json').is_file() or json.loads((out / 'source-receipt.json').read_text()) != source_receipt(data, settings):
            raise ValueError('Resume geometry inputs differ or are unverified; use a fresh output directory')
        receipt = json.loads((out / 'audit/audit.json').read_text())
        if receipt['input']['esm_sha256'] != hashlib.sha256(child_ci(data, 'Morrowind.esm').read_bytes()).hexdigest():
            raise ValueError('Resume source master differs')
        index = json.loads((out / 'scenery/scenery-index.json').read_text())
        entries = regions(settings)
        references = json.loads((out / 'audit/placements.json').read_text())
    if collect_only: return json.loads((out / 'coverage.json').read_text())
    palette = (scene / 'id1/gfx/palette.lmp').read_bytes()
    ext = lumps((scene / 'id1/maps/seyda.bsp').read_bytes())[0].decode('cp1252')
    timings = '\n'.join(re.findall(r'"aw_(?:hand_[^"\n]+|eye_height)" "[^"\n]+"', ext))
    grids = {tuple(g['cell']): g for g in json.loads((out / 'audit/terrain-source.json').read_text())}
    terrain_wad = ground_assets(data, out / 'audit', palette)
    kinds, cells, topics = load_master(child_ci(data, 'Morrowind.esm'))
    arrival, yaw = travel_point(kinds, 'darvame hleran', settings)
    seyda = json.loads((Path(__file__).resolve().parents[1] / 'config/seyda_area.json').read_text())
    returning, return_yaw = travel_point(kinds, 'selvil sareloth', seyda)
    npc_entities = residents(data, scene, out, references, settings, kinds, topics, palette, ffmpeg, jobs)
    write_json(out / 'coverage.json', audit_coverage(index, entries, settings))
    profiles = index['groups']['balmora']['visual_profiles']; flatten = load_profiles()
    tasks = []
    for mi, model in enumerate(index['models']):
        # Select immutable offline representations; every placed reference and
        # authored collision mesh is retained. The original MWSC mesh is kept.
        profile = {**profiles[model['source']], **visual_profile(model['source'], model['triangles'])}
        if model['source'] in flatten: profile['flatten'] = flatten[model['source']]
        profiles[model['source']] = profile
        tasks.append((mi, model, profile, out / 'scenery/scenery.mwpak', index['textures']))
    write_json(out / 'scenery/scenery-index.json', index)
    prepared = dict(ordered_map(_prepare_model, tasks, min(jobs, len(tasks))))
    print('Balmora shared geometry ready:', len(prepared), flush=True)
    reports = []
    for entry in entries:
        root = out / entry['name']; root.mkdir(exist_ok=True)
        selected = select_references(index, entry, settings)
        if len(selected) + 32 > settings['entity_budget']:
            raise ValueError(f"{entry['name']}: entity budget exceeded ({len(selected)})")
        (root / 'terrain.wad').write_bytes(terrain_wad)
        spawn = [(entry['core'][0][i] + entry['core'][1][i]) / 2 for i in range(2)]
        spawn.append(terrain_at(grids, settings, *spawn)[0] + 40)
        if entry == entries[owner(arrival, entries)]: spawn = arrival
        (root / 'terrain.map').write_text(terrain_map(entry, grids, settings, spawn, timings))
        with (root / 'compile.log').open('w') as log:
            for exe, args in ((qbsp, ['-nopercent', 'terrain.map']), (vis, ['-threads', '1', '-fast', 'terrain.bsp']),
                              (light, ['-threads', '1', '-minlight', '24', 'terrain.bsp'])):
                subprocess.run([str(Path(exe).resolve()), *args], cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True)
        base = root / 'base.bsp'; shutil.copyfile(root / 'terrain.bsp', base)
        rebuild_world_hull(base, root / 'terrain.map', qbsp)
        report = append_meshes(base, root / 'scene.bsp', out / 'scenery', scene / 'id1/gfx/palette.lmp',
                               centre=settings['centre'], jobs=jobs, references=selected,
                               prepared_models=prepared, retain_dressing=True)
        if report['unique_models'] > settings['model_budget']:
            raise ValueError(entry['name'] + ': inline model budget exceeded')
        report.update(region=entry, references=selected)
        write_json(root / 'conversion.json', report); reports.append(report)
        print('Balmora region ready:', entry['name'], report['instances'], report['clipnodes'], flush=True)
    # Publish converted payloads only after every region passes its limits.
    publish(scene, out, settings, entries, references, index, npc_entities, arrival, yaw, returning, return_yaw)
    write_json(out / 'regions.json', {'settings': settings, 'arrival': arrival, 'yaw': yaw, 'return': returning, 'return_yaw': return_yaw, 'regions': entries, 'reports': reports})
    return {'regions': len(entries), 'arrival': arrival, 'scenery_references': len(index['references'])}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('data-files', 'scene', 'out'): p.add_argument('--' + name, type=Path, required=True)
    for name in ('qbsp', 'vis', 'light'): p.add_argument('--' + name, type=Path)
    p.add_argument('--ffmpeg', default='ffmpeg'); p.add_argument('--collect-only', action='store_true'); add_jobs(p)
    a = p.parse_args()
    print(json.dumps(prepare(a.data_files, a.scene, a.out, a.qbsp, a.vis, a.light, a.ffmpeg, a.jobs, a.collect_only), indent=2))
