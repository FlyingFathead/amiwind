#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Add a bounded prison-ship interior and explicit return links to a private scene."""
import argparse,json,math,shutil,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.paths import ensure_external,resolve_data_files,child_ci
from mwad.interior import read_interior,select_geometry
from prepare_scenery import export_refs
from prepare_mesh_bsp import add_dressing_option, append_meshes, apply_dressing_option, interior_dressing
from prepare_quake import box,wad,miptex,CENTRE,SCALE
from player_hull import rebuild_world_hull,lumps,pack_lumps


from build_jobs import add_jobs, resolve_jobs
from vis_options import add_vis_option, light_args, VIS_MODES

def prepare(data_files,scene,out,qbsp,vis,light,jobs=None,vis_mode='fast'):
    if vis_mode not in VIS_MODES:raise ValueError('Unknown vis mode')
    data_files=resolve_data_files(data_files);scene=ensure_external(scene,'exterior scene');out=ensure_external(out,'interior bundle')
    if out.exists():raise ValueError('Choose a new interior output')
    cell=read_interior(child_ci(data_files,'Morrowind.esm'),'Imperial Prison Ship')
    refs,omitted=select_geometry(cell)
    shell=next(r for r in refs if r['id'].casefold()=='in_prison_ship')
    door=next(r for r in refs if r['type']=='DOOR' and r.get('destination'))
    entrance=next(r for r in cell['entrances'] if r['id'].casefold()=='chargen_ship_trapdoor')
    shutil.copytree(scene,out);parts=out/'interior-source'
    # Aggressive reduction of the curved shell flattened it into hammocks and
    # furnishings. Keep structural source surfaces/UVs; reduce separate detail.
    profiles={'meshes/i/in_prison_ship.nif':{'ratio':.08,'texture_size':32,
        'collision_source':'root_node','hollow_collision':True,
        'preserve_shape_prefixes':['Tri lower hull','Tri floor','Tri lowerfloor',
                                   'Tri ceiling','Tri leftwall','Tri rightwall',
                                   'Tri Ex_De_Docks_Steps','Tri Ex_ship_plank']}}
    groups={'prison_interior':{'references':[r['number'] for r in refs],'visual_profiles':profiles}}
    refs=[dict(r,scene_groups=['prison_interior']) for r in refs]
    lighting={**cell['lighting'],'lights':[dict(r['light'],position=r['position']) for r in cell['refs'] if r.get('light') and not r.get('deleted')]}
    export_refs(data_files,parts,refs,groups,[0,0,0],4096,32,{'scope':'prison structural/furnishing preview; no opening scripts','cell':cell['name'],'omitted':omitted,'lighting':lighting},jobs=jobs)
    index=json.loads((parts/'scenery-index.json').read_text())
    if index['errors']:raise ValueError('Interior conversion errors: '+str(index['errors']))
    low=np.floor(np.min([r['bounds'][0] for r in index['references']],axis=0)*SCALE)-32
    high=np.ceil(np.max([r['bounds'][1] for r in index['references']],axis=0)*SCALE)+32
    # Sealed, dark fallback enclosure outside the actual ship. It is not an
    # authored floor or collision substitute; native spawn/route tests use the ship.
    walls=[]
    for axis in range(3):
        a=low.copy();b=high.copy();b[axis]=low[axis]+8;walls.append(box(a,b,'voidwall'))
        a=low.copy();b=high.copy();a[axis]=high[axis]-8;walls.append(box(a,b,'voidwall'))
    palette=(out/'id1/gfx/palette.lmp').read_bytes();tile=Image.new('P',(16,16),255);tile.putpalette(palette)
    (out/'prison.wad').write_bytes(wad([('voidwall',0x43,miptex('voidwall',tile))]))
    # Startup point is a prototype in the lower hold near the opening character,
    # not a claim to have implemented the authored camera/character-gen sequence.
    spawn=[0,-35,-4]
    hands=json.loads((out/'hands-report.json').read_text())
    # Reuse the exact hand timing metadata already baked into the exterior.
    import re
    ext=lumps((out/'seyda.bsp').read_bytes())[0].decode('ascii')
    timings='\n'.join(re.findall(r'"aw_(?:hand_[^"\n]+|eye_height)" "[^"\n]+"',ext))
    text='{\n"classname" "worldspawn"\n"wad" "prison.wad"\n"message" "AmiWind / Prison Ship"\n'+timings+'\n'+'\n'.join(walls)+'\n}\n'
    text+='{\n"classname" "info_player_start"\n"origin" "0 -35 -4"\n"angle" "90"\n}\n'
    (out/'prison.map').write_text(text)
    for exe,args in [(qbsp,['-nopercent','prison.map']),(vis,['-fast','prison.bsp'] if vis_mode=='fast' else ['prison.bsp']),(light,light_args('-minlight','24','prison.bsp'))]:
        subprocess.run([str(Path(exe).resolve()),*(['-threads',str(resolve_jobs(jobs))] if exe==vis else []),*args],cwd=out,check=True)
    base=out/'prison-base.bsp';(out/'prison.bsp').rename(base);rebuild_world_hull(base,out/'prison.map',qbsp)
    report=append_meshes(base,out/'prison.bsp',parts,out/'id1/gfx/palette.lmp',centre=(0,0),lighting=lighting,jobs=jobs,
                         retain_dressing=interior_dressing())
    from collision_index import index_model_collision
    report['collision_index'] = index_model_collision(out/'prison.bsp', shell['number'])
    indexed = lumps((out/'prison.bsp').read_bytes())
    report.update(nodes=len(indexed[5])//24, clipnodes=len(indexed[9])//8, bytes=(out/'prison.bsp').stat().st_size)
    shutil.copyfile(out/'prison.bsp',out/'id1/maps/prison.bsp')
    def pos(source,exterior=False):
        return [(source[0]-(CENTRE[0] if exterior else 0))*.25,(source[1]-(CENTRE[1] if exterior else 0))*.25,source[2]*.25]
    def yaw(rot):return (90-math.degrees(rot[2]))%360
    # source map, destination map, activation XYZ, arrival XYZ (standing origin), yaw
    inside_point=pos(door['position']);outside_point=pos(entrance['position'],True)
    exit_dest=pos(door['destination']['position'],True);exit_dest[2]+=16.875
    enter_dest=pos(entrance['destination']['position']);enter_dest[2]+=16.875
    links=[{'source':'prison','target':'seyda','point':inside_point,'arrival':exit_dest,'yaw':yaw(door['destination']['rotation_radians'])},
           {'source':'seyda','target':'prison','point':outside_point,'arrival':enter_dest,'yaw':yaw(entrance['destination']['rotation_radians'])}]
    (out/'id1/scene-links.txt').write_text(''.join(f"{r['source']} {r['target']} "+' '.join(f'{x:.5f}' for x in [*r['point'],*r['arrival'],r['yaw']])+'\n' for r in links))
    from prepare_doors import prepare as prepare_doors
    prepare_doors(data_files,out)
    report.update({'cell':cell['name'],'master_sha256':cell['master_sha256'],'omitted':omitted+report['omitted'],'lighting':lighting,'links':links,'spawn':spawn,
                   'notes':'static furnishing/lighting preview; no items, inventory, NPCs or opening scripts; no shadows/flicker in this bake'})
    (out/'interior-report.json').write_text(json.dumps(report,indent=2)+'\n')
    ready=json.loads((out/'scene-ready.json').read_text());ready['interior']='prison';(out/'scene-ready.json').write_text(json.dumps(ready,indent=2)+'\n')
    return {k:report[k] for k in ('faces','vertices','nodes','clipnodes','bytes','instances','unique_models','links')}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('data-files','scene','out','qbsp','vis','light'):p.add_argument('--'+n,type=Path,required=True)
    add_jobs(p);add_vis_option(p);add_dressing_option(p);a=p.parse_args();apply_dressing_option(a)
    print(json.dumps(prepare(a.data_files,a.scene,a.out,a.qbsp,a.vis,a.light,a.jobs,a.vis_mode),indent=2))
