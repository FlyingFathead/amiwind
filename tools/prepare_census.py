#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Build the owned Census Office cell and retain placed-reference identities."""
import argparse
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from mwad.paths import resolve_data_files, child_ci, ensure_external
from mwad.interior import read_interior, select_geometry
from mwad.npc import load_master, text
from prepare_scenery import export_refs
from prepare_mesh_bsp import add_dressing_option, append_meshes, apply_dressing_option, interior_dressing
from prepare_quake import box, wad, miptex
from prepare_npcs import quote
from player_hull import lumps, pack_lumps, rebuild_world_hull
from prepare_doors import prepare as prepare_doors
from build_jobs import add_jobs, resolve_jobs
from vis_options import add_vis_option, light_args, vis_args


def prepare(data_files, scene, qbsp, vis, light, jobs=None, vis_mode='fast'):
    data_files=resolve_data_files(data_files);scene=ensure_external(scene,'census conversion')
    from ui_palette import reserve
    reserve(data_files,scene/'id1')
    target=scene/'id1/maps/census.bsp'
    if target.exists():raise ValueError('Census map already exists; use a fresh scene')
    cell=read_interior(child_ci(data_files,'Morrowind.esm'),'Seyda Neen, Census and Excise Office')
    refs,omitted=select_geometry(cell)
    refs += [r for r in cell['refs'] if r['id'].casefold()=='chargen statssheet' and not r.get('deleted')]
    profiles={}
    for r in refs:
        model='meshes/'+r['model'].replace('\\','/').lower()
        if model.startswith('meshes/i/'):
            profiles[model]={'ratio':1.0,'texture_size':32,'collision_source':'root_node','hollow_collision':True}
    group='census_interior';groups={group:{'references':[r['number'] for r in refs],'visual_profiles':profiles}}
    refs=[dict(r,scene_groups=[group]) for r in refs]
    from interior_lighting import cell_lighting
    lighting=cell_lighting(cell)
    parts=scene/'census-source'
    # Retain detail in rectangular wall art until the final bounded BSP bake.
    # A 32-pixel intermediate reduced tall tapestries to only 16 pixels wide,
    # then the BSP upscaled that loss. Runtime texture budgets stay unchanged.
    export_refs(data_files,parts,refs,groups,[0,0,0],4096,128,{'scope':'Census Office geometry and registration paper','cell':cell['name'],'lighting':lighting},jobs=jobs)
    index=json.loads((parts/'scenery-index.json').read_text())
    if index['errors']:raise ValueError('Census conversion errors: '+str(index['errors']))
    low=np.floor(np.min([r['bounds'][0] for r in index['references']],axis=0)*.25)-32
    high=np.ceil(np.max([r['bounds'][1] for r in index['references']],axis=0)*.25)+32
    walls=[]
    for axis in range(3):
        a=low.copy();b=high.copy();b[axis]=low[axis]+8;walls.append(box(a,b,'voidwall'))
        a=low.copy();b=high.copy();a[axis]=high[axis]-8;walls.append(box(a,b,'voidwall'))
    palette=(scene/'id1/gfx/palette.lmp').read_bytes();tile=Image.new('P',(16,16),255);tile.putpalette(palette)
    (scene/'census.wad').write_bytes(wad([('voidwall',0x43,miptex('voidwall',tile))]))
    ext=lumps((scene/'id1/maps/seyda.bsp').read_bytes())[0].decode('ascii')
    timings='\n'.join(re.findall(r'"aw_(?:hand_[^"\n]+|eye_height)" "[^"\n]+"',ext))
    # Actual exterior customs door destination supplies the default entry too.
    entrance=next(r for r in cell['entrances'] if r['id'].casefold()=='chargen customs door')
    spawn=[v*.25 for v in entrance['destination']['position']];spawn[2]+=16.875
    heading=(90-math.degrees(entrance['destination']['rotation_radians'][2]))%360
    source='{\n"classname" "worldspawn"\n"wad" "census.wad"\n"message" "Census and Excise Office"\n'+timings+'\n'+'\n'.join(walls)+'\n}\n'
    source+='{\n"classname" "info_player_start"\n"origin" "'+' '.join(map(str,spawn))+'"\n"angle" "'+str(heading)+'"\n}\n'
    (scene/'census.map').write_text(source)
    for exe,args in [(qbsp,['-nopercent','census.map']),(vis,vis_args('census.bsp',resolve_jobs(jobs),vis_mode)),(light,light_args('-minlight','24','census.bsp'))]:
        subprocess.run([str(Path(exe).resolve()),*args],cwd=scene,check=True)
    base=scene/'census-base.bsp';(scene/'census.bsp').rename(base);rebuild_world_hull(base,scene/'census.map',qbsp)
    report=append_meshes(base,scene/'census.bsp',parts,scene/'id1/gfx/palette.lmp',centre=(0,0),lighting=lighting,jobs=jobs,
                         retain_dressing=interior_dressing())
    kinds,_,_=load_master(child_ci(data_files,'Morrowind.esm'));entities=[]
    for identifier,stem,role in [('chargen class','census',6),('chargen captain','captain',7),('chargen door guard','hall',8)]:
        ref=next(r for r in cell['refs'] if r['id'].casefold()==identifier and not r.get('deleted'))
        model='progs/np_'+stem+'.mdl'
        if not (scene/'id1'/model).is_file():raise ValueError('Run intro actor conversion first: '+model)
        fields={'classname':'aw_npc','model':model,'origin':' '.join(f'{v*.25:.5f}' for v in ref['position']),
                'angles':f"0 {-math.degrees(ref['rotation_radians'][2]):.5f} 0",'netname':text(kinds['NPC_'][identifier],'FNAM'),
                'aw_intro_role':role,'aw_ref':ref['number'],'aw_idle_step':'.15','aw_walk_step':'.125'}
        entities.append('{\n'+'\n'.join(quote(k)+' '+quote(v) for k,v in fields.items())+'\n}')
    b=lumps((scene/'census.bsp').read_bytes());b[0]=b[0].rstrip(b'\0')+('\n'+'\n'.join(entities)+'\n\0').encode('cp1252')
    target.write_bytes(pack_lumps(b));shutil.copyfile(target,scene/'census.bsp')
    prepare_doors(data_files,scene)
    report.update(cell=cell['name'],master_sha256=cell['master_sha256'],omitted=omitted+report['omitted'],spawn=spawn)
    (scene/'census-conversion.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('data-files','scene','qbsp','vis','light'):p.add_argument('--'+n,type=Path,required=True)
    add_jobs(p);add_vis_option(p);add_dressing_option(p);a=p.parse_args();apply_dressing_option(a)
    import build_profile;build_profile.instrument('census')
    prepare(a.data_files,a.scene,a.qbsp,a.vis,a.light,a.jobs,a.vis_mode)
