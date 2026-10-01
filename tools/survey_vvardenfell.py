#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Survey owned base-master terrain and geometry; emit private map and planning data."""
import argparse
from collections import Counter, defaultdict
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import numpy as np
from PIL import Image
from mwad.audit import BSA, load_esm, normpath, records, subrecords
from mwad.paths import child_ci, ensure_external
from mwad.scene import unpack_geometry
from npc_geometry import Assets
from prepare_scenery import nif_reader, model_geometry, world_bounds
from build_parallel import ordered_map
from build_jobs import add_jobs, resolve_jobs
from world_survey import CELL_SIZE, SUBTILES, area_catalogue, SpatialIndex, triangle_bins, evaluate_cell

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'source-visible-centroids-v1'
_assets = None


def sha_file(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def mesh_scan(task):
    global _assets
    data, cache, name = task
    if _assets is None:
        _assets = Assets(Path(data), BSA(child_ci(Path(data), 'Morrowind.bsa')))
    key = hashlib.sha256(name.encode()).hexdigest()[:24]
    folder = Path(cache)
    receipt = folder / (key + '.json')
    packet = folder / (key + '.npz')
    try:
        raw = _assets.read(name)
        source_hash = hashlib.sha256(raw).hexdigest()
        if receipt.exists() and packet.exists():
            r = json.loads(receipt.read_text())
            if r.get('source_sha256') == source_hash and r.get('profile') == PROFILE and r.get('cache_sha256') == sha_file(packet):
                return r
        geometry, materials, bounds, repairs = model_geometry(raw, nif_reader(), repair_uv=True)
        verts, faces, _ = unpack_geometry(geometry)
        positions = np.asarray(verts)[:, :3]
        centres = positions[np.asarray(faces)[:, :3]].mean(axis=1).astype(np.float32)
        np.savez_compressed(packet, centres=centres)
        r = dict(model=name, status='measured', profile=PROFILE, source_sha256=source_hash,
                 source_bytes=len(raw), triangles=len(faces), vertices=len(verts), bounds=bounds,
                 material_count=len(materials), cache=packet.name, cache_sha256=sha_file(packet), repairs=repairs)
    except Exception as e:
        r = dict(model=name, status='unresolved', error=type(e).__name__ + ': ' + str(e))
    write_json(receipt, r)
    return r


def terrain_arrays(master, out, assets):
    keys = sorted(master['lands'])
    if not keys:
        raise ValueError('No terrain heights')
    x0, y0 = np.min(keys, axis=0); x1, y1 = np.max(keys, axis=0) + 1
    h = np.full(((y1-y0)*32, (x1-x0)*32), np.nan, dtype=np.float32)
    rgb = np.zeros((*h.shape, 3), dtype=np.uint8)
    materials = {0: [89, 85, 71]}
    missing = []
    for n, record in master['textures'].items():
        try:
            pixels = assets.texture(record['texture'])
            materials[n] = Image.fromarray(pixels).convert('RGB').resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
        except Exception as e:
            materials[n] = [255, 0, 255]
            missing.append(dict(material=n, texture=record['texture'], error=str(e)))
    seas = {}
    for tag, flags, payload in records(child_ci(assets.bsa.path.parent, 'Morrowind.esm').read_bytes()):
        if tag != 'CELL':
            continue
        fields = {}
        for k, v in subrecords(payload):
            if k == 'FRMR':
                break
            fields[k] = v
        bits, x, y = struct.unpack('<Iii', fields['DATA'])
        if not bits & 1 and 'WHGT' in fields:
            seas[x, y] = struct.unpack('<f', fields['WHGT'])[0]
    stats = {}; seams = []
    for (cx, cy), land in master['lands'].items():
        heights = np.asarray(land['heights'], dtype=np.float32)
        if not np.isfinite(heights).all():
            raise ValueError('Nonfinite terrain')
        rows = slice((cy-y0)*32, (cy-y0+1)*32); cols = slice((cx-x0)*32, (cx-x0+1)*32)
        sample = heights[1:65:2, 1:65:2]
        h[rows, cols] = sample
        tiles = np.asarray([[materials.get(m, [255, 0, 255]) for m in row] for row in land['materials']], dtype=float)
        pixels = tiles.repeat(2, 0).repeat(2, 1)
        dx = heights[1:65:2, 2:65:2] - heights[1:65:2, 0:63:2]
        dy = heights[2:65:2, 1:65:2] - heights[0:63:2, 1:65:2]
        light = np.clip(1.15 + (dy-dx)/1800, .55, 1.5)
        pixels = np.clip(pixels * light[:, :, None], 0, 255)
        water = seas.get((cx, cy), 0.)
        if not math.isfinite(water):
            raise ValueError('Nonfinite exterior water level')
        submerged = sample < water
        pixels[submerged] = [34, 66, 84]
        rgb[rows, cols] = pixels.astype(np.uint8)
        stats[cx, cy] = dict(min_height=float(heights.min()), max_height=float(heights.max()),
            water_height=water, water_source='CELL.WHGT' if (cx, cy) in seas else 'exterior-zero-level',
            land_fraction=float(np.mean(~submerged)), terrain_source_triangles=8192,
            terrain_materials=sorted(set(np.asarray(land['materials']).flatten().tolist())))
        for other, edge, target in [((cx+1, cy), heights[:, -1], (slice(None), 0)),
                                    ((cx, cy+1), heights[-1, :], (0, slice(None)))]:
            if other in master['lands']:
                gap = float(np.abs(edge - np.asarray(master['lands'][other]['heights'])[target]).max())
                if gap:
                    seams.append(dict(cell=[cx, cy], neighbour=list(other), maximum_height_delta=gap))
    # Stored images are north-up. The raw height grid retains increasing world Y.
    rgba = np.concatenate((rgb, (np.isfinite(h)*255).astype(np.uint8)[:, :, None]), axis=2)
    Image.fromarray(rgba[::-1]).save(out/'terrain.png')
    np.savez_compressed(out/'terrain-samples.npz', heights=h, bounds=np.array([x0,y0,x1,y1]), spacing=256)
    # Preserve every authored sample, including both copies of shared borders.
    # This is the conversion baseline; the small preview is never its input.
    np.savez_compressed(out/'terrain-source.npz', cells=np.array(keys, dtype=np.int32),
        heights=np.asarray([master['lands'][k]['heights'] for k in keys], dtype=np.float32),
        materials=np.asarray([master['lands'][k]['materials'] for k in keys], dtype=np.uint16),
        water=np.asarray([seas.get(k, 0.) for k in keys], dtype=np.float32), spacing=128)
    return list(map(int, [x0,y0,x1,y1])), stats, dict(missing_textures=missing, height_seams=seams,
        terrain_preview='32 samples per cell, averaged source texture colour plus relief; not full UV terrain',
        water_policy='CELL WHGT when present; otherwise exterior sea level zero')


def bsp_measure(path):
    from player_hull import lumps
    raw = path.read_bytes(); data = lumps(raw)
    faces = list(struct.iter_unpack('<hhihh4Bi', data[7]))
    return dict(bsp_bytes=len(raw), source_sha256=hashlib.sha256(raw).hexdigest(),
                bsp_faces=len(faces), bsp_fan_triangles=sum(max(0, f[3]-2) for f in faces),
                bsp_clipnodes=len(data[9])//8, bsp_models=len(data[14])//64)


def run(a):
    out = ensure_external(a.out, 'world survey'); out.mkdir(parents=True, exist_ok=True)
    if (out/'world-survey.json').exists():
        raise ValueError('Finished survey is immutable; choose a new output directory (cache may be reused)')
    cache = ensure_external(a.cache or out/'mesh-cache', 'world mesh cache'); cache.mkdir(parents=True, exist_ok=True)
    data = a.data_files.resolve(); start = time.monotonic()
    print('Reading base-master terrain and exterior references.', flush=True)
    master = load_esm(child_ci(data, 'Morrowind.esm'))
    areas = area_catalogue(ROOT); assets = Assets(data, BSA(child_ci(data,'Morrowind.bsa')))
    bounds, terrain, terrain_report = terrain_arrays(master, out, assets)
    grouped = defaultdict(list); issues = []; types = Counter(); excluded = Counter(); per_cell = defaultdict(Counter)
    for cell, record in master['cells'].items():
        for r in record['refs']:
            if r.get('deleted'):
                excluded['deleted'] += 1; continue
            obj = master['objects'].get(r.get('id','').casefold())
            if not obj:
                issues.append(dict(cell=list(cell), reference=r['number'], reason='missing-base', source_id=r.get('id'))); continue
            kind = obj['type']; types[kind] += 1; per_cell[cell][kind] += 1
            if kind in ('NPC_', 'CREA', 'LEVC', 'LEVI'):
                excluded['actors-or-leveled-lists'] += 1; continue
            model = normpath(obj['model'])
            if not model or model.rsplit('/',1)[-1].startswith('marker_'):
                excluded['nonvisual-or-marker'] += 1; continue
            if 'position' not in r:
                issues.append(dict(cell=list(cell), reference=r['number'], reason='missing-transform')); continue
            if not model.startswith('meshes/'):
                model = 'meshes/' + model
            grouped[model].append(dict(r, cell=list(cell), type=kind))
    print(f"{len(master['cells'])} exterior cells, {len(terrain)} height grids, {sum(map(len,grouped.values()))} static/item placements, {len(grouped)} unique meshes; {resolve_jobs(a.jobs)} workers.",flush=True)
    scans = {}; tasks = [(str(data),str(cache),name) for name in sorted(grouped)]
    for r in ordered_map(mesh_scan, tasks, a.jobs):
        scans[r['model']] = r
        if len(scans)%50 == 0 or r['status'] != 'measured':
            print(f"Meshes {len(scans)}/{len(tasks)}: {r['model']} {r['status']} {r.get('error','')}",flush=True)
    rows = []; bins = Counter(); owned = Counter(); unresolved_cells = Counter(tuple(i['cell']) for i in issues)
    for model, refs in grouped.items():
        r = scans[model]
        if r['status'] != 'measured':
            for ref in refs:
                unresolved_cells[tuple(ref['cell'])] += 1
                issues.append(dict(cell=ref['cell'],reference=ref['number'],model=model,reason=r['error']))
            continue
        with np.load(cache/r['cache'], allow_pickle=False) as packet:
            centres = packet['centres']
        for ref in refs:
            bounds3 = world_bounds(r['bounds'], ref)
            rows.append(dict(reference=ref['number'],cell=ref['cell'],source_id=ref['id'],model=model,
                             bounds=bounds3,triangles=r['triangles']))
            owned[tuple(ref['cell'])] += r['triangles']
            for key,count in triangle_bins(centres, ref):
                bins[key] += count
    expected = sum(r['triangles'] for r in rows)
    if sum(bins.values()) != expected or sum(owned.values()) != expected:
        raise ValueError('Placed geometry count is not conserved')
    index = SpatialIndex(rows)
    calibration = []
    for area in areas:
        for r in area['regions']:
            row = dict(area=area['name'],region=r['name'],**index.measure(r['coverage']))
            if a.maps and (a.maps/(r['name']+'.bsp')).is_file():
                row.update(bsp_measure(a.maps/(r['name']+'.bsp')))
            calibration.append(row)
    limit = a.triangle_limit or max(r['placed_source_triangles'] for r in calibration)
    if limit <= 0:
        raise ValueError('No reference geometry for screening limit')
    print('Screening 1, 4, 16, 64 region options; source geometry ceiling',limit,flush=True)
    cells = []
    for cell in sorted(set(master['cells']) | set(terrain)):
        item = dict(cell=list(cell),name=master['cells'].get(cell,{}).get('name',''),
                    region=master['cells'].get(cell,{}).get('region',''),
                    has_terrain=cell in terrain,types=dict(per_cell[cell]),
                    owned_source_triangles=owned[cell], unresolved_placements=unresolved_cells[cell],
                    **terrain.get(cell,{}))
        item['spatial_source_triangles'] = sum(bins[(cell[0]*SUBTILES+x,cell[1]*SUBTILES+y)] for y in range(SUBTILES) for x in range(SUBTILES))
        item['subtiles'] = [bins[(cell[0]*SUBTILES+x,cell[1]*SUBTILES+y)] for y in range(SUBTILES) for x in range(SUBTILES)]
        item['screen'] = evaluate_cell(cell,index,limit,a.overlap)
        if issues:
            # A failed mesh has unknown extent, so even neighbouring coverage
            # cannot be certified complete. Keep estimates, flag every screen.
            item['screen']['status'] = 'incomplete-source-geometry'
        cells.append(item)
    report = dict(format='AmiWind world survey 1',master_sha256=master['sha256'],
        bsa_sha256=sha_file(child_ci(data,'Morrowind.bsa')),cell_size=CELL_SIZE,subtiles=SUBTILES,
        terrain_bounds=bounds,areas=areas,cells=cells,calibration=calibration,
        settings=dict(source_triangle_limit=limit,limit_basis='explicit' if a.triangle_limit else 'maximum existing-region source geometry',
                      overlap_world=a.overlap,overlap_runtime=a.overlap*.25,divisions=[1,2,4,8]),
        terrain=terrain_report,summary=dict(exterior_cells=len(master['cells']),terrain_cells=len(terrain),
            measured_placements=len(rows),unique_meshes=len(scans),unresolved_meshes=sum(r['status']!='measured' for r in scans.values()),
            unresolved_placements=len(issues),placed_source_triangles=expected,excluded=dict(excluded),types=dict(types),
            candidate_counts=dict(Counter(str(r['screen']['candidate']) for r in cells)),seconds=round(time.monotonic()-start,2)),
        boundaries=['Base master only; no expansions or plugin merging.','Actors/leveled lists are counted, not meshed.',
                    'Centroid bins conserve source triangles; complete transformed object bounds determine residency.',
                    'Source triangle counts are not converted BSP faces, frame cost or RAM.',
                    'Subdivision candidates require converted collision/texture/heap and native transition checks.',
                    'Terrain image is averaged source texture colour, not full original texture reproduction.'])
    write_json(out/'world-survey.json',report)
    write_json(out/'mesh-survey.json',list(scans.values()))
    write_json(out/'placement-issues.json',issues)
    write_json(out/'placed-geometry.json',rows)
    from render_world_survey import render
    render(report,out)
    print(json.dumps(report['summary'],indent=2),flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--cache',type=Path);p.add_argument('--maps',type=Path,help='Optional existing private BSP directory for calibration')
    p.add_argument('--triangle-limit',type=int,help='Explicit source-geometry screening ceiling; not a runtime guarantee')
    p.add_argument('--overlap',type=float,default=3584,help='Source-world overlap; default equals 896 current runtime units')
    add_jobs(p);a=p.parse_args()
    if a.triangle_limit is not None and a.triangle_limit<=0:p.error('Triangle limit must be positive')
    if not math.isfinite(a.overlap) or a.overlap<0:p.error('Overlap must be finite and nonnegative')
    run(a)


if __name__=='__main__':main()
