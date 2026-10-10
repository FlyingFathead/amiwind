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
from vis_options import add_vis_option, light_args, map_threads, vis_args
from npc_geometry import Assets, Skeleton, assemble, bake, animated_mdl, add_root_rule_arg, apply_root_rule
from npc_anim import foot_class, publish as publish_anim, voices_of
import npc_items
from prepare_scenery import export_refs
from prepare_mesh_bsp import add_dressing_option, append_meshes, apply_dressing_option, interior_dressing
from prepare_quake import box, wad, miptex, CENTRE, SCALE
from prepare_npcs import quote, display_text
from player_hull import lumps, pack_lumps, rebuild_world_hull
from prepare_doors import prepare as prepare_doors
import npc_lod


def entity(fields):
    return '{\n' + '\n'.join(quote(k)+' '+quote(v) for k,v in fields.items()) + '\n}'


def interior_visual_profile(model, area=None):
    """Visual/collision profile of one interior mesh ('meshes/...' path), or
    None when the mesh keeps the assembly default. Shared with the world
    estimate (tools/world_estimate_data.py) so both use the same rule."""
    if not model.startswith('meshes/i/'):
        return None
    profile = {'ratio':1., 'texture_size':32,
               'collision_source':'root_node_or_visual',
               'hollow_collision':not ('rock' in model or 'boulder' in model)}
    if area == 'balmora' and profile['hollow_collision']:
        profile['exact_collision_bevels'] = True
    return profile


def build_room(task):
    data, scene, entry, qbsp, vis, light, timings = task[:7]
    # Optional (vis threads, vis mode); older 7-field tasks keep -threads 1 -fast.
    vis_threads, vis_mode = task[7:9] if len(task) > 7 else (1, 'fast')
    # Optional 10th field: dressing kept by the Seyda Neen rooms (prepare below,
    # interior_dressing); other callers keep the earlier skip rule (receipted).
    dressing = task[9] if len(task) > 9 else False
    slug = entry['map']
    cell = read_interior(child_ci(data, 'Morrowind.esm'), entry['cell'],
                         include_interior_entrances=entry.get('original_door_arrivals', False))
    root = scene/'area-work'/slug
    root.mkdir(parents=True, exist_ok=False)
    refs, omitted = select_geometry(cell, harvest_references=entry.get('harvest_references', ()),
                                    harvest_master_sha256=entry.get('harvest_master_sha256'))
    profiles = {}
    for ref in refs:
        model = 'meshes/'+ref['model'].replace('\\','/').lower()
        profile = interior_visual_profile(model, entry.get('area'))
        if profile is not None:
            profiles[model] = profile
    groups = {slug:{'references':[r['number'] for r in refs], 'visual_profiles':profiles}}
    refs = [dict(r, scene_groups=[slug]) for r in refs]
    from interior_lighting import cell_lighting
    lighting = cell_lighting(cell)
    if slug=='addamasartus':
        lighting={**lighting,'lights':[],'shared_ambient':True}
    # Lava pools become Quake liquid brushes (tools/lava.py, docs/LAVA.md); --lava static keeps
    # the earlier rule (the pool activator is left out, select_geometry).
    import lava as lava_rules
    lava_mode=lava_rules.lava_mode()
    pools=(lava_rules.pools_of(data,cell['refs'],lava_rules.molten_objects_of(child_ci(data,'Morrowind.esm')))
           if lava_mode=='quake' else [])
    if pools:
        lighting={**lighting,'lights':list(lighting.get('lights',[]))+
                  [light for p in pools for light in lava_rules.glow_lights(p['hull'],p['top'])]}
    parts = root/'source'
    export_refs(data, parts, refs, groups, [0,0,0], 8192, 128,
                {'cell':cell['name'], 'lighting':lighting}, jobs=1)
    index = json.loads((parts/'scenery-index.json').read_text())
    if index['errors']:raise ValueError(slug+': '+str(index['errors']))
    low = np.floor(np.min([r['bounds'][0] for r in index['references']],axis=0)*SCALE)-32
    high = np.ceil(np.max([r['bounds'][1] for r in index['references']],axis=0)*SCALE)+32
    pool_box=lava_rules.quake_bounds(pools,[0,0,0],SCALE)
    if pool_box:
        low=np.minimum(low,np.floor(np.array(pool_box[0]))-32);high=np.maximum(high,np.ceil(np.array(pool_box[1]))+32)
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
    lava_brushes,lava_entities,lava_records=lava_rules.map_parts(pools,[0,0,0],SCALE)
    if pools:
        walls+=lava_brushes
        assets=Assets(data,BSA(child_ci(data,'Morrowind.bsa')))
        layers=max((p['layers'] for p in pools),key=len)
        textures+=lava_rules.wad_entries(assets.texture,layers,tile)
    (root/'room.wad').write_bytes(wad(textures))
    if not cell['entrances']:raise ValueError('No source entrance for '+cell['name'])
    entrance = cell['entrances'][0]['destination']
    spawn = [v*SCALE for v in entrance['position']];spawn[2]+=16.875
    yaw = (90-math.degrees(entrance['rotation_radians'][2]))%360
    label = cell['name'].removeprefix('Seyda Neen, ').removeprefix('Balmora, ')
    source = '{\n"classname" "worldspawn"\n"wad" "room.wad"\n"message" '+quote(label)+'\n'+timings+'\n'+'\n'.join(walls)+'\n}\n'
    source += entity({'classname':'info_player_start','origin':' '.join(map(str,spawn)),'angle':yaw})+'\n'
    source += ''.join(text+'\n' for text in lava_entities)
    if pools:
        # the pools' "lava layer" loop (their script's sound), at most lava.LOOP_LIMIT emitters per room
        lava_volumes,lava_sound_receipts=lava_rules.convert_sounds(data,pools,scene/'id1/sound',shutil.which('ffmpeg') or 'ffmpeg')
        source += ''.join(text+'\n' for text in lava_rules.loop_entities(pools,[0,0,0],SCALE,lava_volumes))
    (root/'room.map').write_text(source,encoding='cp1252')
    with (root/'compile.log').open('w') as log:
        for exe,args in [(qbsp,['-nopercent','room.map']),
                         (vis,vis_args('room.bsp',vis_threads,vis_mode)),
                         (light,light_args('-minlight','24','room.bsp'))]:
            subprocess.run([str(Path(exe).resolve()),*args],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
    base=root/'base.bsp';(root/'room.bsp').rename(base)
    rebuild_world_hull(base,root/'room.map',qbsp)
    retain_selected=entry.get('area')=='balmora' or entry.get('retain_selected_geometry',False)
    report=append_meshes(base,root/'room.bsp',parts,scene/'id1/gfx/palette.lmp',centre=(0,0),lighting=lighting,jobs=1,
                         references=[r['number'] for r in index['references']] if retain_selected else None,
                         retain_dressing=True if retain_selected else dressing,
                         map_identity='bmtemple' if slug=='bmtemple' else None)
    if report['unique_models']>220:raise ValueError(slug+': inline model budget exceeded')
    report.update(map=slug,cell=cell['name'],spawn=spawn,yaw=yaw,omitted=omitted+report['omitted'],
                  water_height=water,master_sha256=cell['master_sha256'],
                  lava={'mode':lava_mode,'pools':lava_records})
    if entry.get('original_door_arrivals') or entry.get('harvest_references'):
        report.update(original_arrivals=cell['entrances'],
                      harvest_excluded_references=[r['number'] for r in entry.get('harvest_references', ())],
                      retained_geometry_references=[r['number'] for r in refs],
                      bsp_sha256=hashlib.sha256((root/'room.bsp').read_bytes()).hexdigest())
    (root/'conversion.json').write_text(json.dumps(report,indent=2)+'\n')
    return report, cell


def room_unit(task):
    """(unit cache, inputs) of one interior room (build_room), or (None, None) when the cache is off or the
    game data identity is unknown (BUILD-IMAGE-NO-RESUME-33: a stage resumes from its finished rooms)."""
    import hashlib
    from pass_cache import UnitCache, game_data_digest, tool_digest
    cache = UnitCache.open('interior-room', {}, __file__)
    data_identity = game_data_digest() if cache is not None else None
    if data_identity is None:
        return None, None
    data, scene, entry, qbsp, vis, light, timings = task[:7]
    vis_mode = task[8] if len(task) > 8 else 'fast'
    dressing = task[9] if len(task) > 9 else False
    palette = hashlib.sha256((Path(scene) / 'id1/gfx/palette.lmp').read_bytes()).hexdigest()
    return cache, {'entry': entry, 'timings': timings, 'vis_mode': vis_mode, 'dressing': dressing,
                   'palette': palette, 'tools': tool_digest(qbsp, vis, light), 'game_data': data_identity}


def build_room_cached(task):
    """Worker: build_room, or the room recorded for the same inputs (its folder and receipt). Rows that do not
    survive JSON exactly are never cached, so a cached room returns what a built one would."""
    try:
        cache, inputs = room_unit(task)
        if cache is not None:
            from pass_cache import input_digest
            input_digest(inputs)  # every input has a content key
    except (TypeError, ValueError, OSError):
        cache = None
    if cache is None:
        return build_room(task)
    from pass_cache import json_exact
    root = Path(task[1]) / 'area-work' / task[2]['map']
    row = cache.restore_unit(inputs, root)
    if row is not None:
        return row['report'], row['cell']
    report, cell = build_room(task)
    if json_exact({'report': report, 'cell': cell}):
        cache.store_unit(inputs, {'report': report, 'cell': cell}, root)
    return report, cell


_resident_assets={}
_resident_rigs={}
_resident_sounds={}

def build_resident(task):
    # Optional 6th field: the near/far model settings (tools/npc_lod.py task_settings);
    # older 5-field tasks bake the single model as before.
    data, palette, appearance, greeting, ffmpeg = task[:5]
    lod = task[5] if len(task) > 5 else None
    key=str(Path(data).resolve())
    if key not in _resident_assets:_resident_assets[key]=Assets(data,BSA(child_ci(data,'Morrowind.bsa')))
    assets=_resident_assets[key];rig=(key,appearance['skeleton'])
    if rig not in _resident_rigs:_resident_rigs[rig]=Skeleton(assets,appearance['skeleton'])
    skeleton=_resident_rigs[rig]
    dead=appearance.get('initially_dead',False)
    import npc_anim
    profile_name,profile=npc_anim.selected_profile()
    kit=None
    if dead:times,step=np.array([skeleton.events['death1: stop']]),0.
    elif profile_name=='idle':times,step=skeleton.idle_times(8)   # the previous method, unchanged
    else:
        # Animation kit (docs/ANIMATION.md): idle first, then the profile's groups.
        female=None
        if appearance.get('female') and appearance['skeleton']=='meshes/base_anim.nif':
            rig=(key,npc_anim.FEMALE_SKELETON)
            if rig not in _resident_rigs:_resident_rigs[rig]=Skeleton(assets,npc_anim.FEMALE_SKELETON)
            female=_resident_rigs[rig]
        kit,groups=npc_anim.plan(skeleton,profile,female,appearance.get('weight',1.))
        times=npc_anim.idle_compatible_times(groups);step=groups[0]['step']
    anim={}
    item_times=times;mover_item_times=None
    if lod is not None and not kit:
        # The same bake (npc_lod.bake_far is this ladder), plus the other levels with --npc-lod on.
        # The animation kit (kit) bakes one model; near/far levels are for idle-only residents.
        import npc_lod
        levels,lod_facts=npc_lod.resident_bake(data,assets,skeleton,appearance,palette,times,lod)
        raw=levels[npc_lod.MAP_LEVEL]
        facts={'triangles':lod_facts['far_triangles'],'frames':lod_facts['frames'],'bounds':lod_facts['bounds']}
    else:
        shapes,materials,textures=assemble(assets,appearance,kit or skeleton,times)
        for budget in (480,384,320,256,192):
            # reference_frames=8: the face quotas of the idle-only model (head topology unchanged).
            try:frames,faces,uv,skin=bake(shapes,materials,textures,palette,budget=budget,reference_frames=8 if kit else None);break
            except ValueError as error:
                if str(error)!='Alias vertex budget exceeded' or budget==192:
                    raise ValueError(appearance['id']+': '+str(error)) from error
        if kit:
            # One bake gives both models: the standing model is a subset of the mover's frames (react+full).
            standing_name,mover_name=npc_anim.split_profile(profile_name)
            nv,nt,(sw,sh)=frames.shape[1],len(faces),skin.size
            def model(gs,index):
                names=[g['name']+'%02d'%i for g in gs for i in range(g['count'])]
                return animated_mdl(frames[index],faces,uv,skin,names=names)
            def describe(gs):
                return [{k:v for k,v in g.items() if k!='events'}|{'events':[list(e) for e in g['events']]} for g in gs]
            foot=appearance.get('foot','bare')
            if key not in _resident_sounds:
                _resident_sounds[key]=npc_anim.soun_records(child_ci(data,'Morrowind.esm'))
            if mover_name:
                mover_groups,mover_index=npc_anim.fit(groups,nv,nt,sw,sh)
                keep={g['name']:g['count'] for g in groups if g['name'] in dict(npc_anim.profiles()[standing_name])}
                standing_groups,standing_index=npc_anim.select(groups,keep)
            else:
                mover_groups=None
                standing_groups,standing_index=npc_anim.fit(groups,nv,nt,sw,sh)
            raw=model(standing_groups,standing_index)
            # Item tags (<model>.tag) have one row per frame of THIS model (aw_items.c refuses any other
            # count): the standing model's frames, not every kit sample (ANIMKIT-ITEM-TAG-FRAMES-35).
            item_times=np.asarray(standing_index,dtype=float)
            sound_groups=mover_groups or standing_groups
            # Voice barks: the lines this actor can say per voice topic (mwad.npc.voice_lines), both models.
            # (the callers resolve them with the master's topics: appearance['voices'], npc_anim.voices_of)
            lines={t:[(s,tuple(tuple(x) for x in c) if c else None) for s,c in v] for t,v in (appearance.get('voices') or {}).items()}
            barks=npc_anim.voice_words(lines)
            anim={'profile':profile_name,'layout':(npc_anim.layout(standing_groups,foot)+' '+barks).strip(),'foot':foot,
                  'voices':{t:[[s,[list(x) for x in c] if c else None] for s,c in v] for t,v in lines.items()},
                  'groups':describe(standing_groups),'frame_bytes':npc_anim.frame_bytes(nv),
                  '_sounds':npc_anim.sound_payload(assets,_resident_sounds[key],npc_anim.needed_sounds(sound_groups,foot))}
            if mover_name:
                mover=model(mover_groups,mover_index)
                anim['mover']={'profile':mover_name,'layout':(npc_anim.layout(mover_groups,foot)+' '+barks).strip(),'groups':describe(mover_groups),
                               'bytes':len(mover),'frames':len(mover_index),'sha256':hashlib.sha256(mover).hexdigest()}
                anim['_mover']=mover
                mover_item_times=np.asarray(mover_index,dtype=float)
        else:raw=animated_mdl(frames,faces,uv,skin)
        facts={'triangles':len(faces),'frames':len(frames),
               'bounds':[frames.min((0,1)).tolist(),frames.max((0,1)).tolist()]}
    # Carried weapon/shield (both animation methods): drawn while fighting as separate item
    # models on the hand bones' per-frame tags (tools/npc_items.py; NPC-WEAPON-MESH-33).
    tag,items,mover_tag=(None,{},None) if dead else (npc_items.resident_items(assets,palette,appearance,kit or skeleton,item_times)+(None,)
        if mover_item_times is None else npc_items.resident_items(assets,palette,appearance,kit,item_times,mover_item_times))
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
    record={'appearance':appearance,'greeting':greeting,
        'step':float(step),'triangles':facts['triangles'],'frames':facts['frames'],
        'bounds':facts['bounds'],
        'sha256':hashlib.sha256(raw).hexdigest(),'voice_seconds':duration,
        **({'anim':anim} if anim else {}),**({'_item_tag':tag,'_items':items} if tag else {}),**({'_mover_item_tag':mover_tag} if mover_tag else {})}
    if lod is not None and lod.get('mode')=='on' and not kit:
        record['lod']={k:lod_facts.get(k) for k in ('head_error','levels')}
        record['_levels']=levels
    return appearance['id'],raw,voice,record


def prepare(data_files,scene,qbsp,vis,light,ffmpeg='ffmpeg',jobs=None,vis_mode='fast',rooms=True):
    """rooms=False: a quick test build without interiors (--exclude interiors,
    tools/build_exclusions.py). The rooms are not compiled; the exterior residents
    are placed and the door tables written as usual, so their doors say the area is
    unavailable."""
    data=resolve_data_files(data_files);scene=ensure_external(scene,'area conversion')
    palette=(scene/'id1/gfx/palette.lmp').read_bytes()
    ext=lumps((scene/'id1/maps/seyda.bsp').read_bytes())[0].decode('cp1252')
    timings='\n'.join(re.findall(r'"aw_(?:hand_[^"\n]+|eye_height)" "[^"\n]+"',ext))
    entries=[s for s in SCENES if s['interior'] and s['map'] not in ('prison','census')
             and s.get('area', 'seyda') == 'seyda']
    if not rooms:
        print(f'Quick test build: {len(entries)} Seyda Neen rooms left out (--exclude interiors).',flush=True)
        entries=[]
    # Rooms compile side by side: divide the job budget between them.
    workers=min(resolve_jobs(jobs),max(1,len(entries)))
    tasks=[(data,scene,s,qbsp,vis,light,timings,map_threads(resolve_jobs(jobs),workers),vis_mode,interior_dressing())
           for s in entries]
    rooms={};reports=[]
    # Longest room first: history, else its placed references (BUILD-ORDERED-WINDOW-33).
    from build_costs import costed_map, room_sizes
    sizes=room_sizes(data,[(e['map'],e['cell']) for e in entries])
    # A quick test build without interiors runs no room (and records no room times).
    for report,cell in (costed_map('area-rooms',build_room_cached,tasks,[e['map'] for e in entries],max(1,min(resolve_jobs(jobs),len(tasks))),
                                  fallback=sizes.get if sizes else None)
                        if tasks else ()):
        slug=report['map'];rooms[slug]=cell;reports.append(report)
        shutil.copyfile(scene/'area-work'/slug/'room.bsp',scene/'id1/maps'/f'{slug}.bsp')
        print('Interior ready:',slug,report['bytes'],'bytes',flush=True)
    return populate(data,scene,rooms,reports,ffmpeg,jobs)


def populate(data,scene,rooms,reports,ffmpeg='ffmpeg',jobs=None,
             include_exterior=True,report_name='area-report.json',doors=True,exclude_residents=()):
    palette=(scene/'id1/gfx/palette.lmp').read_bytes()
    kinds,cells,topics=load_master(child_ci(data,'Morrowind.esm'))
    cast=[]
    for cell in cells if include_exterior else []:
        for ref in cell['refs']:
            key=ref['id'].casefold()
            if not ref.get('deleted') and key in kinds['NPC_'] and not key.startswith('chargen ') and inside(ref['position']):
                cast.append(('seyda',ref))
    for slug,cell in rooms.items():
        cast.extend((slug,r) for r in cell['refs'] if not r.get('deleted') and r['type']=='NPC_'
                    and r['id'].casefold() not in exclude_residents)
    identifiers=sorted({r['id'].casefold() for _,r in cast})
    tasks=[];models={}
    for identifier in identifiers:
        appearance=npc_items.attach_items(kinds,identifier,outfit(kinds,identifier))
        stats=first(kinds['NPC_'][identifier],'NPDT')
        appearance['initially_dead']=len(stats)==52 and struct.unpack_from('<h',stats,38)[0]<=0
        appearance['foot']=foot_class(kinds,appearance)
        if not appearance['initially_dead']:appearance['voices']=voices_of(topics,appearance)
        greeting={'text':'','voice':''} if appearance['initially_dead'] else greeting_fixture(topics,appearance)
        tasks.append((data,palette,appearance,greeting,ffmpeg,npc_lod.task_settings()))
    for identifier,raw,voice,record in ordered_map(build_resident,tasks,max(1,min(resolve_jobs(jobs),len(tasks)))):
        stem='a_'+hashlib.sha256(identifier.encode()).hexdigest()[:12]
        record.update(model='progs/'+stem+'.mdl',voice='npc/'+stem+'.wav' if voice else '')
        (scene/'id1'/record['model']).write_bytes(raw)
        publish_anim(scene/'id1',record)
        npc_items.publish(scene/'id1',record)
        if voice:(scene/'id1/sound'/record['voice']).write_bytes(voice)
        behavior=behavior_record(kinds['NPC_'][identifier],SCALE)
        record['behavior']=behavior;record['settings']=greeting_settings(kinds,behavior,SCALE)
        models[identifier]=record
        print('Resident ready:',identifier,flush=True)
    # Near/far models (tools/npc_lod.py): near files and the pairing manifest.
    lod_report=npc_lod.publish(scene/'id1',models,kinds)
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
            from actor_grounding import fields as grounding_fields
            fields={**grounding_fields(ref['id']),'classname':'aw_corpse' if record['appearance'].get('initially_dead') else 'aw_npc','aw_ref':ref['number'],'model':record['model'],
                    'origin':' '.join(f'{v:.5f}' for v in pos),
                    'angles':f"0 {-math.degrees(ref['rotation_radians'][2]):.5f} 0",
                    'netname':display_text(record['appearance']['name']),'aw_voice':record['voice'],
                    'aw_line':display_text(record['greeting']['text']),'aw_idle_step':record['step'],
                    'aw_hello_distance':settings['distance'],'aw_hello_reset':settings['reset_distance'],
                    'aw_greet_duration':settings['duration']}
            entities.append(entity(fields));placed.append({'map':slug,'reference':ref['number'],'id':ref['id'],'position':pos})
        b[0]=('\n'.join(entities)+'\n\0').encode('cp1252');path.write_bytes(pack_lumps(b))
        if slug=='seyda':shutil.copyfile(path,scene/'seyda.bsp')
    # Town interiors (import_town.py) write their own door banks.
    doors=prepare_doors(data,scene) if doors else None
    report={'rooms':reports,'cast':placed,'models':models,'doors':doors,'npc_lod':lod_report,
            'scope':'original placed humanoid residents, blocking idle actors and bounded greetings; combat, services, schedules and small-item interactions remain separate systems'}
    (scene/report_name).write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('data-files','scene','qbsp','vis','light'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--ffmpeg',default='ffmpeg');add_jobs(p);add_vis_option(p);add_dressing_option(p);add_root_rule_arg(p)
    p.add_argument('--no-rooms',action='store_true',help='Quick test build (--exclude interiors): do not compile the rooms')
    npc_lod.add_converter_options(p)
    a=p.parse_args()
    apply_root_rule(a)
    apply_dressing_option(a);npc_lod.apply_options(a)
    import build_profile; build_profile.instrument('area')  # sub-stage timers (docs/BUILD_PROFILE.md)
    prepare(a.data_files,a.scene,a.qbsp,a.vis,a.light,a.ffmpeg,a.jobs,a.vis_mode,rooms=not a.no_rooms)
