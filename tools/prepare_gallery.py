#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Convert the complete owned base-game NPC/creature catalogue for inspection.

Stable numbers follow type/source ID; browsing follows decreasing largest extent.
Failures remain catalogue entries and are recorded in the private audit. A model
is an unarmed base posture; this does not implement equipment/gameplay simulation.
"""
import argparse
import csv
import hashlib
import json
import struct
from pathlib import Path
import sys
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.audit import BSA, normpath
from mwad.npc import load_master, outfit, text
from mwad.paths import child_ci, ensure_external
from mwad.scene import unpack_geometry
from npc_geometry import Assets, Skeleton, assemble, bake, animated_mdl
from prepare_scenery import model_geometry, nif_reader
from prepare_quake import box, miptex, wad
from build_parallel import ordered_map
from build_jobs import add_jobs

_assets = None
_skeletons = {}


def creature_shapes(assets, mesh):
    """Sample the authored rest transforms, including skin inverse bind matrices."""
    packet, materials, bounds, skipped = model_geometry(assets.read(normpath('meshes/' + mesh)), nif_reader(),repair_uv=True)
    vertices, faces, _ = unpack_geometry(packet)
    v = np.array(vertices); f = np.array(faces, dtype=int); shapes = []; textures = {}
    for i, material in enumerate(materials):
        selected = f[f[:, 3] == i, :3]
        if not len(selected): continue
        source = material.pop('texture_source'); material['texture_index'] = source
        if source and source not in textures: textures[source] = assets.texture(source)
        used, remap = np.unique(selected, return_inverse=True)
        shapes.append(dict(name=material['source_shape'], part=-1, positions=v[None, used, :3] * .25,
                           faces=remap.reshape(-1, 3), uv=v[used, 3:5], colours=v[used, 5:9] / 255,
                           material=i))
    return shapes, materials, textures, skipped


def compact_atlas(raw):
    """Gallery-only 8px face tiles; retain every vertex, face and actual scale."""
    h=list(struct.unpack_from('<4si3f3ff3f8if',raw));ns,w,height,nv=h[12:16]
    if ns!=1 or struct.unpack_from('<i',raw,84)[0] or w%8 or height%2:
        raise ValueError('Unsupported gallery atlas')
    skin=Image.frombytes('P',(w,height),raw[88:88+w*height]).resize((w//2,height//2),Image.Resampling.NEAREST)
    h[13]=w//2;h[14]=height//2
    result=bytearray(struct.pack('<4si3f3ff3f8if',*h))+struct.pack('<i',0)+skin.tobytes()
    at=88+w*height
    for i in range(nv):
        seam,s,t=struct.unpack_from('<iii',raw,at+i*12);result+=struct.pack('<iii',seam,s//2,t//2)
    return bytes(result)+raw[at+nv*12:]


def convert_model(task):
    global _assets
    data, output, key, spec, palette = task
    face_limit=spec.get('face_limit',666)
    path = Path(output) / (key + '.mdl'); receipt = path.with_suffix('.json')
    if path.is_file() and receipt.is_file():
        saved = json.loads(receipt.read_text())
        raw=path.read_bytes()
        if saved.get('sha256') == hashlib.sha256(raw).hexdigest():
            if saved.get('atlas_profile')!='face8-v1':
                raw=compact_atlas(raw);path.write_bytes(raw)
                saved.update(atlas_profile='face8-v1',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
                receipt.write_text(json.dumps(saved,indent=2)+'\n')
            return saved
    try:
        source_repairs=[]
        if _assets is None:
            data = Path(data); _assets = Assets(data, BSA(child_ci(data, 'Morrowind.bsa')))
        if spec['kind'] == 'NPC_':
            appearance = spec['appearance']; source = appearance['skeleton']
            if source not in _skeletons: _skeletons[source] = Skeleton(_assets, source)
            skeleton = _skeletons[source]
            times, _ = skeleton.idle_times(1)
            shapes, materials, textures = assemble(_assets, appearance, skeleton, times)
        else:
            shapes, materials, textures, source_repairs = creature_shapes(_assets, spec['mesh'])
        points = np.concatenate([s['positions'][0] for s in shapes]); low = points.min(0); high = points.max(0)
        # Gallery translation only: retain original scale and shape proportions.
        shift = np.array([(low[0]+high[0])/2, (low[1]+high[1])/2, low[2]])
        for shape in shapes: shape['positions'] -= shift
        for budget in (480, 384, 320, 256, 192):
            try:
                frames, faces, uv, skin = bake(shapes, materials, textures, palette, budget,face_limit=face_limit)
                raw = compact_atlas(animated_mdl(frames, faces, uv, skin,vertex_limit=2331)); break
            except ValueError as exc:
                if 'Alias' not in str(exc) or budget == 192: raise
        path.write_bytes(raw)
        result = dict(key=key, status='ready', source_bounds=[low.tolist(), high.tolist()],
                      dimensions=(high-low).tolist(), triangles=len(faces), vertices=frames.shape[1], bytes=len(raw),
                      face_limit=face_limit,
                      sha256=hashlib.sha256(raw).hexdigest(),atlas_profile='face8-v1',source_repairs=source_repairs)
    except Exception as exc:
        result = dict(key=key, status='failed', error=type(exc).__name__ + ': ' + str(exc))
    receipt.write_text(json.dumps(result, indent=2) + '\n'); return result


def safe_label(value):
    return ''.join(c if 32 <= ord(c) <= 126 else '?' for c in value).replace('\t', ' ')[:95]


def footprint(dimensions, palette):
    """Thin double-sided square at true XY extent; no collision or actor rescale."""
    side = max(dimensions[:2])/2 + .5; inner = max(0, side-.4)
    points = np.array([[-side,-side,0],[side,-side,0],[side,side,0],[-side,side,0],
                       [-inner,-inner,0],[inner,-inner,0],[inner,inner,0],[-inner,inner,0]])
    triangles = []
    for i in range(4):
        j=(i+1)%4
        for tri in ((i,j,4+j),(i,4+j,4+i)): triangles.extend((tri,tri[::-1]))
    pal = np.array(list(palette)).reshape(256,3).astype(float)
    ink = int(np.argmin(((pal-[210,185,96])**2).sum(1)))
    skin = Image.new('P',(4,4),ink);skin.putpalette(palette)
    return animated_mdl(points[None,:,:],np.array(triangles),np.zeros((8,2)),skin)


def catalogue(data):
    kinds, _, _ = load_master(child_ci(data, 'Morrowind.esm'))
    entries = []; specs = {}
    for kind in ('CREA', 'NPC_'):
        for identifier, fields in sorted(kinds[kind].items()):
            entry = dict(number=len(entries)+1, kind=kind, id=identifier, name=text(fields, 'FNAM'), models=[])
            for equipped in ((True, False) if kind == 'NPC_' else (True,)):
                try:
                    if kind == 'NPC_':
                        app = outfit(kinds, identifier, equipped=equipped)
                        app = {k: app[k] for k in ('parts', 'skeleton', 'height', 'weight')}
                        spec = dict(kind=kind, appearance=app)
                    else: spec = dict(kind=kind, mesh=text(fields, 'MODL'))
                    key = 'm' + hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:16]
                    if key in specs and specs[key] != spec: raise ValueError('Model key collision')
                    specs[key] = spec; entry['models'].append(key)
                except (ValueError, KeyError) as exc:
                    entry['models'].append('-'); entry.setdefault('errors', []).append(str(exc))
            if len(entry['models']) == 1: entry['models'] *= 2
            entries.append(entry)
    return entries, specs


def inspection_table(entries, results, output, reviews=None):
    """Tie source records and both presentations to content-addressed reviews.

    Numbering is deterministic for a fixed master inventory. Original source IDs
    remain the authority when inventory changes. A changed model checksum never
    inherits approval from a previous conversion of the same appearance key.
    """
    reviewed = reviews or {}
    fields = ['gallery_number','record_type','source_id','friendly_name','variant',
              'model_key','model_sha256','conversion','inspection','shared_uses']
    uses = {}
    for e in entries:
        for key in e['models']:uses[key] = uses.get(key,0)+1
    with Path(output).open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,delimiter='\t');writer.writeheader()
        for e in sorted(entries,key=lambda e:e['number']):
            for variant,key in zip(('equipped','base_body'),e['models']):
                result=results.get(key,{});digest=result.get('sha256','')
                check=reviewed.get(key,{});status='unreviewed'
                if digest and check.get('sha256')==digest and check.get('status') in ('accepted','rejected'):
                    status=check['status']
                writer.writerow(dict(gallery_number=e['number'],record_type=e['kind'],source_id=e['id'],
                    friendly_name=e['name'],variant=variant,model_key=key,model_sha256=digest,
                    conversion=result.get('status','failed'),inspection=status,shared_uses=uses.get(key,0)))


def gallery_map(out, palette):
    pal = Image.new('P', (1, 1)); pal.putpalette(palette)
    floor = Image.new('RGB', (64, 64), (113, 117, 112))
    for x in range(64): floor.putpixel((x, 0), (87, 91, 87)); floor.putpixel((0, x), (87, 91, 87))
    sky = Image.new('RGB', (256, 128), (102, 119, 136))
    (out/'gallery.wad').write_bytes(wad([(name, 68, miptex(name, im.quantize(palette=pal, dither=Image.Dither.NONE))) for name, im in [('floor', floor), ('sky', sky)]]))
    brushes = [box([-2048, -2048, -32], [2048, 2048, 0], 'floor'),
               box([-2080, -2080, 2048], [2080, 2080, 2080], 'sky'),
               box([-2080, -2080, -32], [-2048, 2080, 2048], 'sky'),
               box([2048, -2080, -32], [2080, 2080, 2048], 'sky'),
               box([-2048, -2080, -32], [2048, -2048, 2048], 'sky'),
               box([-2048, 2048, -32], [2048, 2080, 2048], 'sky')]
    (out/'charplane.map').write_text('{\n"classname" "worldspawn"\n"wad" "gallery.wad"\n"message" "Character Model Gallery"\n"_sunlight" "200"\n"_sun_mangle" "90 -90 0"\n' + '\n'.join(brushes) + '\n}\n{\n"classname" "info_player_start"\n"origin" "96 0 20"\n"angle" "180"\n}\n')


def finish_catalogue(entries,results,out,palette,reviews=None):
    models=out/'gallery'
    for e in entries:
        e['variants'] = [results.get(k, dict(status='failed')) for k in e['models']]
        e['dimensions'] = e['variants'][0].get('dimensions', [0, 0, 0])
    for key,r in results.items():
        if r['status']=='ready':
            (models/('f'+key[1:]+'.mdl')).write_bytes(footprint(r['dimensions'],palette))
    entries.sort(key=lambda e: (-max(e['dimensions']), -np.prod(e['dimensions']), e['number']))
    lines = ['AWG1 ' + str(len(entries))]
    for e in entries:
        models_ = [k if r['status'] == 'ready' else '-' for k, r in zip(e['models'], e['variants'])]
        lines.append('\t'.join([str(e['number']), e['kind'], *models_, *(f'{v:.5f}' for v in e['dimensions']), safe_label(e['id']), safe_label(e['name'])]))
    (models/'catalog.txt').write_text('\n'.join(lines)+'\n', encoding='ascii')
    (out/'gallery-audit.json').write_text(json.dumps(dict(entries=entries, models=results), indent=2)+'\n')
    inspection_table(entries,results,models/'inspection.tsv',reviews)
    gallery_map(out, palette)
    failed = sum(r['status'] != 'ready' for r in results.values())
    return failed


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files', type=Path, required=True); p.add_argument('--palette', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True); add_jobs(p)
    p.add_argument('--reviews',type=Path,help='Private model-key/checksum inspection decisions to carry forward')
    a = p.parse_args(); out = ensure_external(a.out, 'gallery'); out.mkdir(parents=True, exist_ok=True)
    models = out/'gallery'; models.mkdir(exist_ok=True); palette = a.palette.read_bytes()
    if len(palette) != 768: raise ValueError('Expected 256-colour palette')
    entries, specs = catalogue(a.data_files)
    print(f'{len(entries)} source records; {len(specs)} distinct body/outfit models', flush=True)
    results = {}
    for result in ordered_map(convert_model, [(str(a.data_files), str(models), key, spec, palette) for key, spec in specs.items()], a.jobs):
        results[result['key']] = result
        if len(results) % 25 == 0 or result['status'] != 'ready': print(f'{len(results)}/{len(specs)} {result["key"]}: {result["status"]} {result.get("error", "")}', flush=True)
    failed=finish_catalogue(entries,results,out,palette,json.loads(a.reviews.read_text()) if a.reviews else None)
    print(f'Complete catalogue; {failed} failed model conversions remain visible.',flush=True)
    if failed: sys.exit(2)


if __name__ == '__main__': main()
