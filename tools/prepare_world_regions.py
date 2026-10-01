#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Compile private terrain BSPs using the measured Vvardenfell polygon splits.

The original survey remains immutable. Scenery residency estimates select the
partition even though this first pass adds only terrain/water outside the towns.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import numpy as np
from PIL import Image
from mwad.audit import BSA, load_esm
from mwad.paths import ensure_external, child_ci
from npc_geometry import Assets
from prepare_quake import brush, box, miptex, wad
from player_hull import lumps, pack_lumps
from compact_bsp import compact
from deduplicate_bsp import deduplicate
from build_jobs import add_jobs, resolve_jobs
from build_parallel import ordered_map

SCALE = .25
STEP = 128
OVERLAP = 896
_terrain = None


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def plan(survey):
    report = json.loads((survey / 'world-survey.json').read_text())
    if report['format'] != 'AmiWind world survey 1' or report['terrain']['height_seams']:
        raise ValueError('Expected a complete, seam-checked world survey')
    if report['settings']['overlap_runtime'] != OVERLAP:
        raise ValueError('Survey overlap differs from the compiled region profile')
    entries = []
    for cell in sorted(report['cells'], key=lambda c: tuple(c['cell'])):
        n = cell['screen']['candidate']
        if n not in (1, 2, 4, 8) or cell['unresolved_placements']:
            raise ValueError('Unresolved subdivision candidate: ' + str(cell['cell']))
        size = 2048 // n
        for y in range(n):
            for x in range(n):
                lo = [cell['cell'][0] * 2048 + x * size, cell['cell'][1] * 2048 + y * size]
                origin = [lo[0] + size // 2, lo[1] + size // 2, 0]
                core = [[-size // 2, -size // 2], [size // 2, size // 2]]
                coverage = [[v - OVERLAP for v in core[0]], [v + OVERLAP for v in core[1]]]
                entries.append(dict(name=f'vf{len(entries):04d}', cell=cell['cell'],
                    divisions=n, subcell=[x, y], source_label=cell['name'],
                    source_region=cell['region'], origin=origin, core=core, coverage=coverage,
                    geometry_screen=cell['screen']))
    if len(entries) > 8192:
        raise ValueError('World directory exceeds bounded runtime capacity')
    return report, entries


class Terrain:
    def __init__(self, survey):
        with np.load(survey / 'terrain-source.npz', allow_pickle=False) as data:
            self.cells = {tuple(c): i for i, c in enumerate(data['cells'])}
            self.heights = data['heights'].copy()
            self.materials = data['materials'].copy()
            if int(data['spacing']) != 128 or self.heights.shape != (len(self.cells), 65, 65):
                raise ValueError('Unexpected full-resolution terrain packet')
            if not np.isfinite(self.heights).all() or np.any(data['water'] != 0):
                raise ValueError('Nonfinite height or unsupported water levels')
        repairs = json.loads((Path(__file__).resolve().parents[1] / 'config/balmora.json').read_text())
        for repair in repairs.get('terrain_material_repairs', []):
            index = self.cells[tuple(repair['cell'])]
            x, y = repair['tile']
            if self.materials[index, y, x] != repair['source_material']:
                raise ValueError('Terrain repair no longer matches the surveyed source')
            self.materials[index, y, x] = repair['material']

    def sample(self, x, y):
        # Input is global runtime units. Grid vertices remain source-aligned,
        # including at negative cells and across unlike subdivision sizes.
        cx, cy = math.floor(x / 2048), math.floor(y / 2048)
        ix, iy = (x - cx * 2048) / 32, (y - cy * 2048) / 32
        key = (cx, cy)
        if key not in self.cells:
            for other, xx, yy in [((cx-1, cy), 64, iy), ((cx, cy-1), ix, 64), ((cx-1, cy-1), 64, 64)]:
                if other in self.cells and (xx != 64 or ix == 0) and (yy != 64 or iy == 0):
                    key, ix, iy = other, xx, yy
                    break
        if key not in self.cells:
            return -512., 0  # Explicit ocean-only cells have no authored LAND.
        index = self.cells[key]
        return float(self.heights[index, round(iy), round(ix)]) * SCALE, int(self.materials[index, min(15, int(iy)//4), min(15, int(ix)//4)])


def terrain_wad(data, survey, palette):
    master = load_esm(child_ci(data, 'Morrowind.esm'))
    assets = Assets(data, BSA(child_ci(data, 'Morrowind.bsa')))
    pal = Image.new('P', (1, 1)); pal.putpalette(palette)
    with np.load(survey / 'terrain-source.npz', allow_pickle=False) as packet:
        used = sorted(set(packet['materials'].flatten().tolist()) | {0})
    textures = []
    for key in used:
        im = (Image.fromarray(assets.texture(master['textures'][key]['texture'])).convert('RGB')
              if key else Image.new('RGB', (32, 32), (89, 85, 71)))
        im = im.resize((32, 32), Image.Resampling.BOX).quantize(palette=pal, dither=Image.Dither.NONE)
        textures.append(('g'+str(key), 68, miptex('g'+str(key), im)))
    for name, color, size in [('stone', (80, 79, 70), (64, 64)), ('*water', (65, 87, 91), (64, 64)), ('sky', (102, 119, 136), (256, 128))]:
        im = Image.new('RGB', size, color).quantize(palette=pal, dither=Image.Dither.NONE)
        textures.append((name, 68, miptex(name, im)))
    return wad(textures)


def map_text(entry, terrain):
    low, high = entry['coverage']; ox, oy, _ = entry['origin']
    samples = {(x, y): terrain.sample(x+ox, y+oy)[0]
               for y in range(low[1], high[1]+1, STEP) for x in range(low[0], high[0]+1, STEP)}
    zmin, zmax = min(samples.values()), max(samples.values())
    oz = round((zmin+zmax)/256)*128
    entry['origin'][2] = oz
    bottom = zmin-oz-64; top = zmax-oz+256
    if max(abs(bottom-32), abs(top+32), abs(-oz)) >= 4000:
        raise ValueError('Local coordinate budget requires a finer region: '+entry['name'])
    brushes = []
    for y in range(low[1], high[1], STEP):
        for x in range(low[0], high[0], STEP):
            corners = [[x+dx, y+dy, samples[x+dx, y+dy]-oz] for dx, dy in ((0,0),(STEP,0),(STEP,STEP),(0,STEP))]
            material = terrain.sample(x+ox+STEP/2, y+oy+STEP/2)[1]
            for ids in ((0,1,2),(0,2,3)):
                tri = [corners[i] for i in ids]
                brushes.append(brush(tri+[[p[0],p[1],bottom] for p in tri],
                    [(0,1,2),(3,4,5),(0,1,4),(1,2,5),(2,0,3)], 'g'+str(material)))
    x0,y0=low; x1,y1=high
    if bottom < -oz:
        brushes.append(box([x0,y0,bottom],[x1,y1,-oz],'*water'))
    brushes.extend([
        box([x0-32,y0-32,bottom-32],[x1+32,y1+32,bottom],'stone'),
        box([x0-32,y0-32,top],[x1+32,y1+32,top+32],'sky'),
        box([x0-32,y0-32,bottom],[x0,y1+32,top],'sky'),
        box([x1,y0-32,bottom],[x1+32,y1+32,top],'sky'),
        box([x0,y0-32,bottom],[x1,y0,top],'sky'),
        box([x0,y1,bottom],[x1,y1+32,top],'sky')])
    spawn = terrain.sample(ox,oy)[0]-oz+24
    return ('{\n"classname" "worldspawn"\n"wad" "terrain.wad"\n"message" "Vvardenfell"\n'
            +'\n'.join(brushes)+'\n}\n{\n"classname" "info_player_start"\n'
            +f'"origin" "0 0 {spawn}"\n"angle" "90"\n}}\n')


def compile_region(task):
    global _terrain
    survey, out, entry, bindir = task
    if _terrain is None:
        _terrain = Terrain(survey)
    started = time.monotonic(); root=out/entry['name']; root.mkdir(exist_ok=True)
    source=root/'terrain.map'; content=map_text(entry, _terrain)
    key=hashlib.sha256(b'world-terrain-hull-v3-deduplicated'+content.encode()+(out/'terrain.wad').read_bytes()).hexdigest()
    receipt=root/'conversion.json'
    if receipt.exists():
        previous=json.loads(receipt.read_text())
        if previous.get('input_sha256')==key and (root/'scene.bsp').exists() and digest(root/'scene.bsp')==previous['converted']['sha256']:
            return previous
    shutil.copyfile(out/'terrain.wad', root/'terrain.wad')
    source.write_text(content)
    with (root/'compile.log').open('w') as log:
        for name,args in [('qbsp',['-nopercent', 'terrain.map']), ('vis',['-threads','1','-fast','terrain.bsp']), ('light',['-threads','1','-minlight','24','terrain.bsp'])]:
            subprocess.run([str(bindir/name),*args],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
    target=root/'scene.bsp'
    base=lumps((root/'terrain.bsp').read_bytes())
    # Drop the soon-to-be-replaced Quake player hull before grafting. Retain
    # the independent large-actor hull and every visible/point-collision node.
    struct.pack_into('<i',base[14],40,-1)
    struct.pack_into('<i',base[14],48,-1)
    pruned,_=compact(pack_lumps(base));target.write_bytes(pruned)
    # Same standing humanoid hull as the established town conversions.
    with (root/'hull.log').open('w') as log:
        from player_hull import scaled_map, graft_hull
        collision=root/'standing-collision.map';collision.write_text(scaled_map(source.read_text()))
        subprocess.run([str(bindir/'qbsp'),'-nopercent',collision.name],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
        target.write_bytes(graft_hull(target.read_bytes(),collision.with_suffix('.bsp').read_bytes()))
    packed,storage=deduplicate(target.read_bytes());target.write_bytes(packed)
    data=lumps(packed)
    metrics=dict(bytes=target.stat().st_size,faces=len(data[7])//20,clipnodes=len(data[9])//8,
                 vertices=len(data[3])//12,sha256=digest(target),seconds=round(time.monotonic()-started,3))
    if metrics['bytes']>4*1024*1024 or metrics['faces']>30000 or metrics['clipnodes']>32767:
        raise ValueError('Converted terrain budget exceeded: '+entry['name'])
    result=dict(entry,converted=metrics,input_sha256=key,storage=storage)
    (root/'conversion.json').write_text(json.dumps(result,indent=2)+'\n')
    for path in root.iterdir():
        if path.is_file() and path.name not in ('scene.bsp','conversion.json','compile.log','hull.log'):path.unlink()
    return result


def prepare(survey,data,scene,out,bindir,jobs,only=None):
    survey=survey.resolve();out=ensure_external(out,'world terrain').resolve();out.mkdir(parents=True,exist_ok=True)
    scene=ensure_external(scene,'private scene').resolve();bindir=bindir.resolve()
    report, entries=plan(survey)
    if digest(child_ci(data,'Morrowind.esm'))!=report['master_sha256'] or digest(child_ci(data,'Morrowind.bsa'))!=report['bsa_sha256']:
        raise ValueError('Original inputs differ from the measured survey')
    if (out/'world-regions.json').exists():
        raise ValueError('Completed conversion is immutable; choose a fresh directory')
    (out/'terrain.wad').write_bytes(terrain_wad(data,survey,(scene/'id1/gfx/palette.lmp').read_bytes()))
    if only:
        entries=[e for e in entries if e['name'] in only]
        if len(entries)!=len(set(only)):raise ValueError('Unknown diagnostic region')
    results=[]
    for result in ordered_map(compile_region,[(survey,out,e,bindir) for e in entries],jobs):
        results.append(result)
        print(result['name'],result['converted'],flush=True)
    receipt=dict(format='AmiWind playable terrain regions 1',master_sha256=report['master_sha256'],
        survey_sha256=digest(survey/'world-survey.json'),terrain_sha256=digest(survey/'terrain-source.npz'),
        scale=SCALE,sample_stride=4,overlap=OVERLAP,draw_distance=540,
        scope='Terrain and water; existing town geometry remains separate. Other scenery and actors are not converted.',
        diagnostic_subset=bool(only),regions=results)
    if not only:
        packet=bytearray(b'AWR2'+struct.pack('<I',len(results)))
        for name in ('Seyda Neen','Balmora'):
            area=next(a for a in report['areas'] if a['name']==name)
            origin=[v*SCALE for v in area['centre']]+[0]
            lo=[min(r['core'][0][k] for r in area['regions'])*SCALE-origin[k]+96 for k in range(2)]
            hi=[max(r['core'][1][k] for r in area['regions'])*SCALE-origin[k]-96 for k in range(2)]
            packet.extend(struct.pack('<7f',*origin,*lo,*hi))
        for e in results:
            packet.extend(struct.pack('<8s11f',e['name'].encode(),*e['origin'],*e['core'][0],*e['core'][1],*e['coverage'][0],*e['coverage'][1]))
            shutil.copyfile(out/e['name']/'scene.bsp',scene/'id1/maps'/f"{e['name']}.bsp")
        (scene/'id1/world').mkdir(parents=True,exist_ok=True)
        (scene/'id1/world/regions.awr').write_bytes(packet)
    (out/'world-regions.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('survey','data-files','scene','out','bindir'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--only',nargs='+',help='Diagnostic subset; never publishes a partial world directory')
    add_jobs(p);a=p.parse_args()
    prepare(a.survey,a.data_files,a.scene,a.out,a.bindir,resolve_jobs(a.jobs),a.only)
