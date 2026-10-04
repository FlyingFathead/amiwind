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
from functools import lru_cache

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import numpy as np
from PIL import Image
from mwad.audit import BSA, load_esm
from mwad.paths import ensure_external, child_ci
from npc_geometry import Assets
from prepare_quake import brush, box, miptex, wad
from player_hull import lumps, pack_lumps
from compact_bsp import compact, entities
from deduplicate_bsp import deduplicate
from build_jobs import add_jobs, resolve_jobs
from build_parallel import ordered_map

SCALE = .25
STEP = 128
OVERLAP = 896
_terrain = None


def town_handoffs(report, root=None):
    """Use ground coverage, not the larger sea/enclosure or render bounds."""
    root = Path(root or Path(__file__).resolve().parents[1])
    towns = []
    for name, filename in [('Seyda Neen', 'seyda_area.json'), ('Balmora', 'balmora.json')]:
        area = next(a for a in report['areas'] if a['name'] == name)
        config = json.loads((root / 'config' / filename).read_text())
        if config['centre'] != area['centre'] or config['scale'] != area['scale'] or config['scale'] != SCALE:
            raise ValueError('Town ground transform differs from the survey: ' + name)
        bounds = config['bounds']
        if len(bounds) != 2 or any(len(p) != 2 for p in bounds):
            raise ValueError('Expected rectangular town ground coverage: ' + name)
        lo = [v + 96 for v in bounds[0]]
        hi = [v - 96 for v in bounds[1]]
        for k in range(2):
            covered_lo = min(r['core'][0][k] for r in area['regions']) * SCALE - config['centre'][k] * SCALE
            covered_hi = max(r['core'][1][k] for r in area['regions']) * SCALE - config['centre'][k] * SCALE
            if not (-4000 < covered_lo <= bounds[0][k] < lo[k] < hi[k] < bounds[1][k] <= covered_hi < 4000):
                raise ValueError('Town handoff is outside converted ground/regions: ' + name)
        towns.append(dict(name=name, origin=[v * SCALE for v in config['centre']] + [0],
                          core=[lo, hi], ground_bounds=bounds, exit_margin=32))
    return towns


def region_directory(report, entries):
    packet = bytearray(b'AWR2' + struct.pack('<I', len(entries)))
    for town in town_handoffs(report):
        packet.extend(struct.pack('<7f', *town['origin'], *town['core'][0], *town['core'][1]))
    for entry in entries:
        packet.extend(struct.pack('<8s11f', entry['name'].encode(), *entry['origin'],
            *entry['core'][0], *entry['core'][1], *entry['coverage'][0], *entry['coverage'][1]))
    return bytes(packet)


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()



def refine_entries(entries, refinements):
    """Keep existing map indices; replace a parent slot and append its siblings.

    Cores tile the same global area. Coverage retains the full original apron;
    source scenery is selected again by full transformed bounds, never clipped
    out of the census. Original survey and completed output stay immutable.
    """
    import copy
    result=copy.deepcopy(entries)
    if [e['name'] for e in result] != [f'vf{i:04d}' for i in range(len(result))]:
        raise ValueError('Refinement requires sequential world map indices')
    for rule in refinements:
        matches=[i for i,e in enumerate(result) if e['cell']==rule['cell']]
        if not matches:continue  # Synthetic surveys can omit this source cell.
        if len(matches)!=1:raise ValueError('Refinement parent must be an unsplit cell')
        slot=matches[0];parent=result[slot]
        if parent['name']!=rule['parent'] or parent['divisions']!=1:
            raise ValueError('Refinement parent differs from measured layout')
        n=rule['divisions']
        if n not in (2,4,8):raise ValueError('Invalid refinement divisions')
        size=2048//n;children=[]
        for y in range(n):
            for x in range(n):
                child=copy.deepcopy(parent)
                for field in ('converted','input_sha256','storage'):child.pop(field,None)
                child.update(name=parent['name'] if not children else f'vf{len(result)+len(children)-1:04d}',
                    divisions=n,subcell=[x,y],
                    origin=[parent['origin'][0]-1024+size*(x+.5),parent['origin'][1]-1024+size*(y+.5),parent['origin'][2]],
                    core=[[-size//2,-size//2],[size//2,size//2]],
                    coverage=[[-size//2-OVERLAP,-size//2-OVERLAP],[size//2+OVERLAP,size//2+OVERLAP]],
                    refinement={'parent':parent['name'],'reason':rule['reason'],
                                'source_content_policy':'original membership; unchanged mesh profiles and collision; no reserve reduction'})
                children.append(child)
        result[slot]=children[0];result.extend(children[1:])
    if len(result)>8192:raise ValueError('World directory exceeds bounded runtime capacity')
    return result

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
    refinements=json.loads((Path(__file__).resolve().parents[1]/'config/world-region-refinements.json').read_text(encoding='utf-8'))
    return report, refine_entries(entries,refinements['regions'])


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

    @lru_cache(maxsize=524288)
    def shoreline_detail(self, x, y):
        """Keep original samples where stride four changes land/water identity."""
        a, b, c, d = [self.sample(x+dx, y+dy)[0]
                      for dx, dy in ((0,0),(STEP,0),(STEP,STEP),(0,STEP))]
        for dy in range(0, STEP+1, 32):
            for dx in range(0, STEP+1, 32):
                u, v = dx/STEP, dy/STEP
                coarse = a+(b-a)*u+(c-b)*v if v<=u else a+(c-d)*u+(d-a)*v
                actual = self.sample(x+dx, y+dy)[0]
                if (actual >= 0) != (coarse >= 0):
                    return True
        return False


def terrain_triangles(terrain, x, y, required_edge_samples=()):
    """Insert shoreline samples and required coarse/fine boundary samples.

    Required edges are south (0), east (1), north (2), and west (3).
    Their original intermediate heights are kept even on entirely dry ground.

    Shared edges are decided solely from their original heights, independently
    of either tile's interior. This keeps neighbouring and overlapping meshes
    watertight without uniformly multiplying the BSP/collision workload.
    """
    required_edge_samples = frozenset(required_edge_samples)
    if any(type(edge) is not int or edge not in range(4) for edge in required_edge_samples):
        raise ValueError("Required terrain edges must be integers from 0 through 3")
    point = lambda xx, yy: [xx, yy, terrain.sample(xx, yy)[0]]
    corners = [point(x+dx, y+dy) for dx, dy in ((0,0),(STEP,0),(STEP,STEP),(0,STEP))]
    triangles = [[corners[i] for i in ids] for ids in ((0,1,2),(0,2,3))]
    if not required_edge_samples and not terrain.shoreline_detail(x, y):
        yield from triangles
        return

    def weights(p, tri):
        a, b, c = tri
        den = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        u = ((b[1]-c[1])*(p[0]-c[0])+(c[0]-b[0])*(p[1]-c[1]))/den
        v = ((c[1]-a[1])*(p[0]-c[0])+(a[0]-c[0])*(p[1]-c[1]))/den
        return u, v, 1-u-v

    def insert(p):
        nonlocal triangles
        out = []
        for tri in triangles:
            w = weights(p, tri)
            if min(w)<-1e-8:
                out.append(tri)
                continue
            for i in range(3):
                a, b = tri[i], tri[(i+1)%3]
                area = (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
                if area>1e-8:
                    out.append([a,b,p])
        triangles = out

    # Either side of an edge sees identical endpoints and original samples.
    for i in range(4):
        a, b = corners[i], corners[(i+1)%4]
        edge = [point(a[0]+(b[0]-a[0])*j/4, a[1]+(b[1]-a[1])*j/4) for j in (1,2,3)]
        if i in required_edge_samples or any((p[2]>=0)!=(a[2]+(b[2]-a[2])*j/4>=0) for j,p in enumerate(edge,1)):
            for p in edge:
                insert(p)
    pending = [point(x+dx,y+dy) for dy in (32,64,96) for dx in (32,64,96)]
    while pending:
        added = False
        for p in pending[:]:
            for tri in triangles:
                w = weights(p,tri)
                if min(w)<-1e-8:
                    continue
                height = sum(w[i]*tri[i][2] for i in range(3))
                if (p[2]>=0)!=(height>=-1e-7):
                    insert(p);pending.remove(p);added=True
                break
        if not added:
            break
    yield from triangles


def terrain_wad(data, survey, palette):
    master = load_esm(child_ci(data, 'Morrowind.esm'))
    assets = Assets(data, BSA(child_ci(data, 'Morrowind.bsa')))
    pal = Image.new('P', (1, 1)); pal.putpalette(palette)
    with np.load(survey / 'terrain-source.npz', allow_pickle=False) as packet:
        used = sorted(set(packet['materials'].flatten().tolist()) | {0})
    textures = []
    for key in used:
        im = (Image.fromarray(assets.texture(master['textures'][key]['texture'])).convert('RGB')
              if key else Image.fromarray(assets.texture('_land_default.tga')).convert('RGB'))
        im = im.resize((32, 32), Image.Resampling.BOX).quantize(palette=pal, dither=Image.Dither.NONE)
        textures.append(('g'+str(key), 68, miptex('g'+str(key), im)))
    for name, color, size in [('stone', (80, 79, 70), (64, 64)), ('*water', (65, 87, 91), (64, 64)), ('sky', (102, 119, 136), (256, 128))]:
        im = (Image.fromarray(assets.texture('water/water00.tga')).convert('RGB').resize(size, Image.Resampling.BOX)
              if name == '*water' else Image.new('RGB', size, color))
        im = im.quantize(palette=pal, dither=Image.Dither.NONE)
        textures.append((name, 68, miptex(name, im)))
    return wad(textures)


def map_text(entry, terrain):
    low, high = entry['coverage']; ox, oy, _ = entry['origin']
    triangles = [tri for y in range(low[1], high[1], STEP) for x in range(low[0], high[0], STEP)
                 for tri in terrain_triangles(terrain, x+ox, y+oy)]
    zmin = min(p[2] for tri in triangles for p in tri)
    zmax = max(p[2] for tri in triangles for p in tri)
    oz = round((zmin+zmax)/256)*128
    entry['origin'][2] = oz
    bottom = zmin-oz-64; top = max(zmax,0)-oz+256
    if max(abs(bottom-32), abs(top+32), abs(-oz)) >= 4000:
        raise ValueError('Local coordinate budget requires a finer region: '+entry['name'])
    brushes = []
    for source_tri in triangles:
        cx, cy = [sum(p[k] for p in source_tri)/3 for k in (0,1)]
        material = terrain.sample(cx, cy)[1]
        tri = [[p[0]-ox, p[1]-oy, p[2]-oz] for p in source_tri]
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
            +f'"origin" "0 0 {spawn}"\n"angle" "90"\n}}\n'
            +'{\n"classname" "info_null"\n'+f'"origin" "0 0 {max(zmax,0)-oz+96}"\n'+ '}\n')


def compile_region(task):
    global _terrain
    survey, out, entry, bindir = task
    if _terrain is None:
        _terrain = Terrain(survey)
    started = time.monotonic(); root=out/entry['name']; root.mkdir(exist_ok=True)
    source=root/'terrain.map'; content=map_text(entry, _terrain)
    key=hashlib.sha256(b'world-terrain-hull-v5-adaptive-shoreline'+content.encode()+(out/'terrain.wad').read_bytes()).hexdigest()
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
    # These terrain-only maps have no large actors. Keep point collision and
    # graft the actual standing hull; discard unused stock Quake actor hulls.
    # Detailed town hulls are built separately and remain intact.
    for offset in (40,44,48):struct.pack_into('<i',base[14],offset,-1)
    pruned,_=compact(pack_lumps(base), records=[e for e in entities(base[0]) if e.get('classname')!='info_null']);target.write_bytes(pruned)
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
        receipt['town_handoffs'] = town_handoffs(report)
        packet = region_directory(report, results)
        for e in results:
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
