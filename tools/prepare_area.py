#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Convert the starting area's rooms and residents from the user's owned master."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import struct
import sys
import tempfile
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import numpy as np
from PIL import Image
from mwad.audit import BSA
from mwad.interior import read_interior, select_geometry
from mwad.npc import load_master, outfit, greeting_fixture, behavior_record, greeting_settings, first
from mwad.paths import resolve_data_files, child_ci, ensure_external
from area_config import SCENES, inside
from build_jobs import add_jobs, resolve_jobs
from build_parallel import ordered_map
from npc_geometry import Assets, Skeleton, assemble, bake, animated_mdl
from prepare_scenery import export_refs
from prepare_mesh_bsp import append_meshes
from prepare_quake import box, wad, miptex, CENTRE, SCALE
from prepare_npcs import quote, display_text
from player_hull import lumps, pack_lumps, rebuild_world_hull
from prepare_doors import prepare as prepare_doors


def entity(fields):
    return '{\n' + '\n'.join(quote(k)+' '+quote(v) for k,v in fields.items()) + '\n}'


def build_room(task):
    data, scene, entry, qbsp, vis, light, timings = task
    slug = entry['map']
    cell = read_interior(child_ci(data, 'Morrowind.esm'), entry['cell'])
    root = scene/'area-work'/slug
    root.mkdir(parents=True, exist_ok=False)
    refs, omitted = select_geometry(cell)
    profiles = {}
    for ref in refs:
        model = 'meshes/'+ref['model'].replace('\\','/').lower()
        if model.startswith('meshes/i/'):
            profiles[model] = {'ratio':1., 'texture_size':32,
                               'collision_source':'root_node_or_visual',
                               'hollow_collision':not ('rock' in model or 'boulder' in model)}
            if entry.get('area') == 'balmora' and profiles[model]['hollow_collision']:
                profiles[model]['exact_collision_bevels'] = True
    groups = {slug:{'references':[r['number'] for r in refs], 'visual_profiles':profiles}}
    refs = [dict(r, scene_groups=[slug]) for r in refs]
    lighting = {**cell['lighting'], 'lights':[dict(r['light'],position=r['position'])
                for r in cell['refs'] if r.get('light') and not r.get('deleted')]}
    if slug=='addamasartus':
        lighting={**lighting,'lights':[],'shared_ambient':True}
    parts = root/'source'
    export_refs(data, parts, refs, groups, [0,0,0], 8192, 128,
                {'cell':cell['name'], 'lighting':lighting}, jobs=1)
    index = json.loads((parts/'scenery-index.json').read_text())
    if index['errors']:raise ValueError(slug+': '+str(index['errors']))
    low = np.floor(np.min([r['bounds'][0] for r in index['references']],axis=0)*SCALE)-32
    high = np.ceil(np.max([r['bounds'][1] for r in index['references']],axis=0)*SCALE)+32
    walls = []
    for axis in range(3):
        a=low.copy();b=high.copy();b[axis]=low[axis]+8;walls.append(box(a,b,'voidwall'))
        a=low.copy();b=high.copy();a[axis]=high[axis]-8;walls.append(box(a,b,'voidwall'))
    palette = (scene/'id1/gfx/palette.lmp').read_bytes()
    tile = Image.new('P',(16,16),255);tile.putpalette(palette)
    textures=[('voidwall',0x43,miptex('voidwall',tile))]
    water=cell.get('water_height')
    if water is not None:
        level=water*SCALE
        if not low[2]<level<high[2]:raise ValueError(slug+': water outside room bounds')
        a=low+8;b=high-8;b[2]=level
        walls.append(box(a,b,'*water'))
        liquid=Image.new('RGB',(64,64),(65,87,91)).quantize(palette=tile,dither=Image.Dither.NONE)
        textures.append(('*water',0x43,miptex('*water',liquid)))
    (root/'room.wad').write_bytes(wad(textures))
    if not cell['entrances']:raise ValueError('No source entrance for '+cell['name'])
    entrance = cell['entrances'][0]['destination']
    spawn = [v*SCALE for v in entrance['position']];spawn[2]+=16.875
    yaw = (90-math.degrees(entrance['rotation_radians'][2]))%360
    label = cell['name'].removeprefix('Seyda Neen, ').removeprefix('Balmora, ')
    source = '{\n"classname" "worldspawn"\n"wad" "room.wad"\n"message" '+quote(label)+'\n'+timings+'\n'+'\n'.join(walls)+'\n}\n'
    source += entity({'classname':'info_player_start','origin':' '.join(map(str,spawn)),'angle':yaw})+'\n'
    (root/'room.map').write_text(source,encoding='cp1252')
    with (root/'compile.log').open('w') as log:
        for exe,args in [(qbsp,['-nopercent','room.map']),
                         (vis,['-threads','1','-fast','room.bsp']),
                         (light,['-threads','1','-minlight','24','room.bsp'])]:
            subprocess.run([str(Path(exe).resolve()),*args],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
    base=root/'base.bsp';(root/'room.bsp').rename(base)
    rebuild_world_hull(base,root/'room.map',qbsp)
    report=append_meshes(base,root/'room.bsp',parts,scene/'id1/gfx/palette.lmp',centre=(0,0),lighting=lighting,jobs=1,
                         references=[r['number'] for r in index['references']] if entry.get('area')=='balmora' else None,
                         retain_dressing=entry.get('area')=='balmora')
    if report['unique_models']>220:raise ValueError(slug+': inline model budget exceeded')
    report.update(map=slug,cell=cell['name'],spawn=spawn,yaw=yaw,omitted=omitted,
                  water_height=water,master_sha256=cell['master_sha256'])
    (root/'conversion.json').write_text(json.dumps(report,indent=2)+'\n')
    return report, cell


_resident_assets={}
_resident_rigs={}

def build_resident(task):
    data, palette, appearance, greeting, ffmpeg = task
    key=str(Path(data).resolve())
    if key not in _resident_assets:_resident_assets[key]=Assets(data,BSA(child_ci(data,'Morrowind.bsa')))
    assets=_resident_assets[key];rig=(key,appearance['skeleton'])
    if rig not in _resident_rigs:_resident_rigs[rig]=Skeleton(assets,appearance['skeleton'])
    skeleton=_resident_rigs[rig]
    dead=appearance.get('initially_dead',False)
    if dead:times,step=np.array([skeleton.events['death1: stop']]),0.
    else:times,step=skeleton.idle_times(8)
    shapes,materials,textures=assemble(assets,appearance,skeleton,times)
    for budget in (480,384,320,256,192):
        try:frames,faces,uv,skin=bake(shapes,materials,textures,palette,budget=budget);break
        except ValueError as error:
            if str(error)!='Alias vertex budget exceeded' or budget==192:
                raise ValueError(appearance['id']+': '+str(error)) from error
    raw=animated_mdl(frames,faces,uv,skin)
    voice=b'';duration=0.
    if not dead:
      with tempfile.TemporaryDirectory() as tmp:
          tmp=Path(tmp);(tmp/'voice.mp3').write_bytes(assets.read('sound/'+greeting['voice']))
          subprocess.run([ffmpeg,'-v','error','-nostdin','-i',str(tmp/'voice.mp3'),
                          '-ac','1','-ar','11025','-c:a','pcm_u8',str(tmp/'voice.wav')],check=True)
          with wave.open(str(tmp/'voice.wav')) as sound:
              duration=sound.getnframes()/sound.getframerate()
              if duration>15:raise ValueError('Greeting exceeds 15-second budget')
          voice=(tmp/'voice.wav').read_bytes()
    return appearance['id'],raw,voice,{'appearance':appearance,'greeting':greeting,
        'step':float(step),'triangles':len(faces),'frames':len(frames),
        'bounds':[frames.min((0,1)).tolist(),frames.max((0,1)).tolist()],
        'sha256':hashlib.sha256(raw).hexdigest(),'voice_seconds':duration}


def prepare(data_files,scene,qbsp,vis,light,ffmpeg='ffmpeg',jobs=None):
    data=resolve_data_files(data_files);scene=ensure_external(scene,'area conversion')
    palette=(scene/'id1/gfx/palette.lmp').read_bytes()
    ext=lumps((scene/'id1/maps/seyda.bsp').read_bytes())[0].decode('cp1252')
    timings='\n'.join(re.findall(r'"aw_(?:hand_[^"\n]+|eye_height)" "[^"\n]+"',ext))
    entries=[s for s in SCENES if s['interior'] and s['map'] not in ('prison','census')
             and s.get('area', 'seyda') == 'seyda']
    tasks=[(data,scene,s,qbsp,vis,light,timings) for s in entries]
    rooms={};reports=[]
    for report,cell in ordered_map(build_room,tasks,min(resolve_jobs(jobs),len(tasks))):
        slug=report['map'];rooms[slug]=cell;reports.append(report)
        shutil.copyfile(scene/'area-work'/slug/'room.bsp',scene/'id1/maps'/f'{slug}.bsp')
        print('Interior ready:',slug,report['bytes'],'bytes',flush=True)
    return populate(data,scene,rooms,reports,ffmpeg,jobs)


def populate(data,scene,rooms,reports,ffmpeg='ffmpeg',jobs=None,
             include_exterior=True,report_name='area-report.json'):
    palette=(scene/'id1/gfx/palette.lmp').read_bytes()
    kinds,cells,topics=load_master(child_ci(data,'Morrowind.esm'))
    cast=[]
    for cell in cells if include_exterior else []:
        for ref in cell['refs']:
            key=ref['id'].casefold()
            if not ref.get('deleted') and key in kinds['NPC_'] and not key.startswith('chargen ') and inside(ref['position']):
                cast.append(('seyda',ref))
    for slug,cell in rooms.items():
        cast.extend((slug,r) for r in cell['refs'] if not r.get('deleted') and r['type']=='NPC_')
    identifiers=sorted({r['id'].casefold() for _,r in cast})
    tasks=[];models={}
    for identifier in identifiers:
        appearance=outfit(kinds,identifier)
        stats=first(kinds['NPC_'][identifier],'NPDT')
        appearance['initially_dead']=len(stats)==52 and struct.unpack_from('<h',stats,38)[0]<=0
        greeting={'text':'','voice':''} if appearance['initially_dead'] else greeting_fixture(topics,appearance)
        tasks.append((data,palette,appearance,greeting,ffmpeg))
    for identifier,raw,voice,record in ordered_map(build_resident,tasks,min(resolve_jobs(jobs),len(tasks))):
        stem='a_'+hashlib.sha256(identifier.encode()).hexdigest()[:12]
        record.update(model='progs/'+stem+'.mdl',voice='npc/'+stem+'.wav' if voice else '')
        (scene/'id1'/record['model']).write_bytes(raw)
        if voice:(scene/'id1/sound'/record['voice']).write_bytes(voice)
        behavior=behavior_record(kinds['NPC_'][identifier],SCALE)
        record['behavior']=behavior;record['settings']=greeting_settings(kinds,behavior,SCALE)
        models[identifier]=record
        print('Resident ready:',identifier,flush=True)
    placed=[]
    for slug in (['seyda'] if include_exterior else []) + list(rooms):
        path=scene/'id1/maps'/f'{slug}.bsp';b=lumps(path.read_bytes())
        # Replace the three prototype residents, retaining scripted intro actors.
        entities=re.findall(r'\{[^{}]*\}',b[0].decode('cp1252'))
        entities=[e for e in entities if
                  not any('"classname" "'+kind+'"' in e for kind in ('aw_npc','aw_corpse'))
                  or '"aw_intro_role"' in e]
        for place,ref in cast:
            if place!=slug:continue
            if abs(ref['scale']-1)>1e-5:raise ValueError('Resident instance scale requires separate bake')
            record=models[ref['id'].casefold()];settings=record['settings']
            pos=[(v-(CENTRE[a] if slug=='seyda' and a<2 else 0))*SCALE for a,v in enumerate(ref['position'])]
            fields={'classname':'aw_corpse' if record['appearance'].get('initially_dead') else 'aw_npc','aw_ref':ref['number'],'model':record['model'],
                    'origin':' '.join(f'{v:.5f}' for v in pos),
                    'angles':f"0 {-math.degrees(ref['rotation_radians'][2]):.5f} 0",
                    'netname':display_text(record['appearance']['name']),'aw_voice':record['voice'],
                    'aw_line':display_text(record['greeting']['text']),'aw_idle_step':record['step'],
                    'aw_hello_distance':settings['distance'],'aw_hello_reset':settings['reset_distance'],
                    'aw_greet_duration':settings['duration']}
            entities.append(entity(fields));placed.append({'map':slug,'reference':ref['number'],'id':ref['id'],'position':pos})
        b[0]=('\n'.join(entities)+'\n\0').encode('cp1252');path.write_bytes(pack_lumps(b))
        if slug=='seyda':shutil.copyfile(path,scene/'seyda.bsp')
    doors=prepare_doors(data,scene)
    report={'rooms':reports,'cast':placed,'models':models,'doors':doors,
            'scope':'original placed humanoid residents, blocking idle actors and bounded greetings; combat, services, schedules and small-item interactions remain separate systems'}
    (scene/report_name).write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('data-files','scene','qbsp','vis','light'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--ffmpeg',default='ffmpeg');add_jobs(p);a=p.parse_args()
    prepare(a.data_files,a.scene,a.qbsp,a.vis,a.light,a.ffmpeg,a.jobs)
