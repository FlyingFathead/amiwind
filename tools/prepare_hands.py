#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Bake an owned Nord male first-person unarmed appearance into a scene."""
import argparse,json,shutil,hashlib,struct
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from mwad.npc import load_master,first,text,PART_NAMES
from mwad.audit import BSA
from mwad.paths import ensure_external
from npc_geometry import Assets,Skeleton,assemble,bake,animated_mdl
from player_hull import lumps,pack_lumps

# Fixed frame contract shared with independent runtime state logic.
CLIPS=(('idle','idlehh: start','idlehh: stop',8,False),
       ('draw','handtohand: equip start','handtohand: equip stop',6,True),
       ('lower','handtohand: unequip start','handtohand: unequip stop',4,True),
       ('punch','handtohand: chop start','handtohand: chop large follow stop',10,True))

def sample_clips(events):
    times=[];clips={}
    for name,start,stop,count,endpoint in CLIPS:
        a=events[start];b=events[stop]
        if not np.isfinite([a,b]).all() or b<=a:raise ValueError('Invalid first-person animation '+name)
        clips[name]={'first':len(times),'count':count,'duration':float(b-a)}
        times.extend(np.linspace(a,b,count,endpoint=endpoint))
    return np.array(times),clips

def prepare(data,scene,out):
    data=ensure_external(data,'owned data');scene=ensure_external(scene,'source scene');out=ensure_external(out,'hands scene')
    ready=json.loads((scene/'scene-ready.json').read_text())
    if ready.get('hands'):raise ValueError('Scene already has hands')
    kinds,_,_=load_master(data/'Morrowind.esm');assets=Assets(data,BSA(data/'Morrowind.bsa'))
    skeleton=Skeleton(assets,'meshes/base_anim.1st.nif');times,clips=sample_clips(skeleton.events)
    parts=[]
    # First-person hands take precedence; original third-person arms fill gaps.
    for part,slots in [(5,(6,7)),(6,(8,9)),(7,(11,12)),(8,(13,14))]:
        candidates=[]
        for identifier,body in kinds['BODY'].items():
            raw=first(body,'BYDT')
            if len(raw)!=4:continue
            bp,vampire,flags,kind=raw
            if bp==part and not vampire and not flags&1 and not kind and text(body,'FNAM').casefold()=='nord':
                candidates.append((identifier.endswith('.1st'),identifier,body))
        if not candidates:continue
        _,identifier,body=max(candidates,key=lambda c:(c[0],c[1]))
        for slot in slots:parts.append({'slot':slot,'attach':PART_NAMES[slot],'filter':PART_NAMES[slot],'id':identifier,'mesh':text(body,'MODL')})
    if not any(p['id'].endswith('.1st') for p in parts):raise ValueError('No Nord first-person hands')
    # Viewmodel stays in camera units; race/world scaling is not applied twice.
    shapes,materials,textures=assemble(assets,{'parts':parts,'weight':1,'height':1},skeleton,times)
    camera=skeleton.pose(float(times[0]))('Camera')[3,:3]*.25
    race_data=first(kinds['RACE']['nord'],'RADT')
    height=struct.unpack_from('<f',race_data,len(race_data)-20)[0]
    eye_height=float(camera[2]*height-16.625)
    for shape in shapes:
        xyz=shape['positions']-camera
        shape['positions']=xyz[:,:,[1,0,2]]*np.array([1,-1,1])
    frames,faces,uv,skin=bake(shapes,materials,textures,(scene/'id1/gfx/palette.lmp').read_bytes(),budget=320)
    raw=animated_mdl(frames,faces,uv,skin)
    shutil.copytree(scene,out);(out/'id1/progs/v_nord.mdl').write_bytes(raw)
    # Store derived timing in private worldspawn. Runtime does not hardcode asset times.
    b=lumps((out/'seyda.bsp').read_bytes());entities=b[0].decode('cp1252');end=entities.index('}')
    values=''.join('"aw_hand_'+name+'" "'+str(info['duration'])+'"\n' for name,info in clips.items())
    values+='"aw_eye_height" "'+str(eye_height)+'"\n'
    b[0]=bytearray((entities[:end]+values+entities[end:]).encode('cp1252'));raw_bsp=pack_lumps(b)
    (out/'seyda.bsp').write_bytes(raw_bsp);(out/'id1/maps/seyda.bsp').write_bytes(raw_bsp)
    report={'scope':'Nord male first-person unarmed appearance; visual animation only, no combat rules',
            'model':'progs/v_nord.mdl','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
            'parts':parts,'skeleton':'meshes/base_anim.1st.nif','camera_origin_scaled':camera.tolist(),'race_height':height,'eye_above_feet':eye_height+16.625,'eye_above_origin':eye_height,
            'frames':len(frames),'triangles':len(faces),'vertices':frames.shape[1], 'clips':clips,
            'bounds':[frames.min((0,1)).tolist(),frames.max((0,1)).tolist()]}
    ready['hands']=report;(out/'scene-ready.json').write_text(json.dumps(ready,indent=2)+'\n')
    (out/'hands-report.json').write_text(json.dumps(report,indent=2)+'\n')
    from prepare_hand_sprites import prepare as sprites
    sprites(out)
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['data-files','scene','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.data_files,a.scene,a.out),indent=2))
if __name__=='__main__':main()
