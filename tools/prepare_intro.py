#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Bake original actor talk/blink/walk poses and introductory speech privately."""
import argparse,hashlib,json,math,re,shutil,struct,subprocess,sys,tempfile,wave
from pathlib import Path, PurePosixPath
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.audit import BSA,records,subrecords,string
from mwad.npc import load_master,outfit,text,first
from mwad.interior import read_interior
from mwad.paths import copy_tree,ensure_external
from npc_geometry import Assets,Skeleton,assemble,bake,animated_mdl,add_root_rule_arg,apply_root_rule
from npc_faces import ActorSkeleton,actor_samples,envelope
from player_hull import lumps,pack_lumps
from prepare_npcs import quote
from prepare_quake import CENTRE
from build_jobs import add_jobs, resolve_jobs
from build_parallel import Background, ordered_map


def voice_convert(assets,source,target,ffmpeg='ffmpeg',speech=True,gain_db=0):
    if not math.isfinite(gain_db) or not -60<=gain_db<=0:
        raise ValueError('Audio gain must be finite and between -60 and 0 dB')
    target.parent.mkdir(parents=True,exist_ok=True)
    requested=source;resolved=source.replace('\\','/')
    try:raw=assets.read('sound/'+resolved)
    except KeyError:
        if Path(resolved).suffix.casefold()!='.wav':raise
        resolved=str(PurePosixPath(resolved).with_suffix('.mp3'));raw=assets.read('sound/'+resolved)
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/'source';p.write_bytes(raw)
        filters=['-af',f'volume={gain_db:g}dB'] if gain_db else []
        subprocess.run([ffmpeg,'-v','error','-nostdin','-y','-i',str(p),*filters,'-ac','1','-ar','11025','-c:a','pcm_u8',str(target)],check=True)
    if speech:target.with_suffix('.lip').write_bytes(envelope(target))
    with wave.open(str(target)) as w:duration=w.getnframes()/w.getframerate()
    return {'requested':requested,'source':resolved,'source_sha256':hashlib.sha256(raw).hexdigest(),'gain_db':gain_db,'seconds':duration,'bytes':target.stat().st_size}

def ship_hull_convert(assets,source,target,ffmpeg='ffmpeg'):
    """Always start with the owned source: never attenuate a previous build."""
    receipt=voice_convert(assets,source,target,ffmpeg,speech=False,gain_db=-5)
    raw=target.read_bytes();cue=b'cue '+struct.pack('<I',28)+struct.pack('<III4sIII',1,0,0,b'data',0,0,0)
    raw=raw+cue;raw=raw[:4]+struct.pack('<I',len(raw)-8)+raw[8:];target.write_bytes(raw)
    return {**receipt,'bytes':len(raw),'output_sha256':hashlib.sha256(raw).hexdigest(),'runtime_loop_start':0}

def navigation(master,name):
    """Preserve original node/connection order, converted to local quarter units."""
    found=[]
    for tag,flags,raw in records(master.read_bytes()):
        if tag!='PGRD':continue
        f=dict(subrecords(raw))
        if string(f.get('NAME',b'')).casefold()!=name.casefold():continue
        points=list(struct.iter_unpack('<iiiBBH',f['PGRP']));edges=list(struct.iter_unpack('<i',f.get('PGRC',b'')))
        if not 0<len(points)<=128 or len(edges)>512:raise ValueError('Path grid exceeds runtime budget')
        result=bytearray(struct.pack('<4sH',b'AWN1',len(points)));at=0
        for x,y,z,auto,count,pad in points:
            result.extend(struct.pack('<3fH',x*.25,y*.25,z*.25,count))
            for i in range(count):
                if at>=len(edges) or not 0<=edges[at][0]<len(points):raise ValueError('Malformed path connection')
                result.extend(struct.pack('<H',edges[at][0]));at+=1
        if at!=len(edges):raise ValueError('Unconsumed path connections')
        found.append(bytes(result))
    if len(found)!=1:raise ValueError('Path grid must resolve uniquely: '+name)
    return found[0]

def ship_ambience(data,out,ffmpeg='ffmpeg'):
    """The prison's two scripted hull barrels loop Boat Hull at volume 0.4."""
    return add_ship_ambience(out,*ship_ambience_sound(data,out,ffmpeg))


def ship_ambience_sound(data,out,ffmpeg='ffmpeg'):
    """(emitter entities, receipt) of ship_ambience: the sound conversion, which writes only its own
    sound file, so it can run beside the actor bakes (intro_sounds); add_ship_ambience edits the map."""
    assets=Assets(data,BSA(data/'Morrowind.bsa'));objects={};sounds={};scripts={}
    for tag,flags,raw in records((data/'Morrowind.esm').read_bytes()):
        if tag not in ('CONT','SOUN','SCPT'):continue
        f=dict(subrecords(raw))
        if tag=='CONT':objects[string(f.get('NAME',b'')).casefold()]=string(f.get('SCRI',b'')).casefold()
        elif tag=='SOUN':sounds[string(f.get('NAME',b'')).casefold()]=f
        else:scripts[string(f['SCHD'][:32]).casefold()]=string(f.get('SCTX',b''))
    script=scripts['sound_boat_hull']
    if not re.search(r'PlayLoopSound3DVP\s+"Boat Hull"\s+0\.4\s*,\s*1\.0',script,re.I):raise ValueError('Unsupported hull sound script')
    sound=sounds['boat hull'];voice='env/boat_hull.wav';target=out/'id1/sound'/voice
    receipt=ship_hull_convert(assets,string(sound['FNAM']),target,ffmpeg)
    cell=read_interior(data/'Morrowind.esm','Imperial Prison Ship');entities=[]
    for ref in cell['refs']:
        if objects.get(ref['id'].casefold())!='sound_boat_hull' or ref.get('deleted'):continue
        fields={'classname':'aw_loop','aw_voice':voice,'origin':' '.join(str(v*.25) for v in ref['position']),
                'aw_volume':str(.4*sound['DATA'][0]/255),'aw_attenuation':'2'}
        entities.append('{\n'+'\n'.join(quote(k)+' '+quote(v) for k,v in fields.items())+'\n}')
    return entities,{**receipt,'emitters':len(entities),'source_script':script,'runtime_loop_start':0,'volume':.4*sound['DATA'][0]/255,
            'attenuation':'Quake spatial falloff approximation; not original distance-model parity'}


def add_ship_ambience(out,entities,receipt):
    """Append ship_ambience_sound's emitters to the prison map; its receipt."""
    path=out/'id1/maps/prison.bsp';b=lumps(path.read_bytes());b[0]=b[0].rstrip(b'\0')+('\n'+'\n'.join(entities)+'\n\0').encode('cp1252')
    path.write_bytes(pack_lumps(b));(out/'prison.bsp').write_bytes(path.read_bytes())
    return receipt


def intro_sounds(data,out,ffmpeg='ffmpeg'):
    """(scripts, navigation, speech, ship ambience parts) of prepare(): the character-generation
    speech lines, the prison path grid and the hull sound. They read only the game data and write
    only their own files (id1/intro, id1/sound/intro, id1/sound/env), so prepare() runs them beside
    the actor bakes (build_parallel.Background); the map edits stay in prepare()."""
    assets=Assets(data,BSA(data/'Morrowind.bsa'));scripts={};speech={}
    # Convert all authored Say lines from the base game's character-generation scripts.
    lines={};allrecords=list(records((data/'Morrowind.esm').read_bytes()))
    for tag,flags,raw in allrecords:
        if tag!='SCPT':continue
        fields=dict(subrecords(raw));name=string(fields['SCHD'][:32]);script=string(fields.get('SCTX',b''))
        if not name.casefold().startswith('chargen'):continue
        scripts[name]=script
        for source,subtitle in re.findall(r'(?im)^\s*say\s*,?\s*"([^"]+)"\s*,?\s*"([^"]*)"',script):
            stem=Path(source.replace('\\','/')).stem.lower().replace(' ','_')
            if stem in lines and lines[stem]['text']!=subtitle:raise ValueError('Conflicting introductory line '+stem)
            lines[stem]={'voice':source,'text':subtitle,'script':name}
    dest=out/'id1/intro';dest.mkdir(exist_ok=True)
    nav=navigation(data/'Morrowind.esm','Imperial Prison Ship');(dest/'prison.awn').write_bytes(nav)
    navigation_report={'prison':{'sha256':hashlib.sha256(nav).hexdigest(),'nodes':struct.unpack_from('<H',nav,4)[0]}}
    for i,(stem,line) in enumerate(sorted(lines.items())):
        voice='intro/'+stem+'.wav';receipt=voice_convert(assets,line['voice'],out/'id1/sound'/voice,ffmpeg)
        # No original dialogue is copied into the public runtime source.
        (dest/(stem+'.txt')).write_bytes(line['text'].encode('cp1252')+b'\0')
        speech[stem]={**line,**receipt,'runtime_voice':voice}
    return scripts,navigation_report,speech,ship_ambience_sound(data,out,ffmpeg)


_actor_context = None


def _actor(task):
    global _actor_context
    data, palette, identifier, stem, role, appearance = task
    if _actor_context is None or _actor_context[0] != data:
        assets=Assets(data,BSA(data/'Morrowind.bsa'));base=Skeleton(assets)
        skeletons={False:ActorSkeleton(base),True:ActorSkeleton(base,Skeleton(assets,'meshes/base_anim_female.nif'))}
        _actor_context=(data,assets,skeletons)
    _,assets,skeletons=_actor_context
    skeleton=skeletons[appearance['female']];times,facesamples,step,walkstep=actor_samples(skeleton)
    shapes,materials,textures=assemble(assets,appearance,skeleton,times,facesamples)
    frames,faces,uv,skin=bake(shapes,materials,textures,palette)
    raw=animated_mdl(frames,faces,uv,skin);model='progs/np_'+stem+'.mdl'
    report={'model':model,'frames':len(frames),'triangles':len(faces),'vertices':frames.shape[1],
        'sha256':hashlib.sha256(raw).hexdigest(),'talk_displacement':float(abs(frames[11]-frames[8]).max()),
        'blink_displacement':float(abs(frames[12]-frames[8]).max()),'idle_step':float(step),'walk_step':float(walkstep),'appearance':appearance}
    return identifier,role,raw,report


def prepare(data,scene,out,ffmpeg='ffmpeg',jobs=None,movie=True,cache=None,cache_report=None):
    """CACHE: a per-file cache folder for the movie (tools/file_cache.py); None converts it. movie=False: quick test build."""
    data=ensure_external(data,'owned data');scene=ensure_external(scene,'existing scene');out=ensure_external(out,'intro conversion')
    if out.exists():raise ValueError('Choose a new output')
    copy_tree(scene,out)
    # Speech, path grid and hull sound convert beside the actor bakes (intro_sounds).
    sounds=Background(intro_sounds,data,out,ffmpeg,jobs=jobs)
    kinds,cells,topics=load_master(data/'Morrowind.esm')
    palette=(out/'id1/gfx/palette.lmp').read_bytes();report={'actors':{},'speech':{},'scripts':{}}
    prison=read_interior(data/'Morrowind.esm','Imperial Prison Ship')
    actors=[('chargen name','jiub',1),('chargen boat guard 2','escort',2),('chargen boat guard 3','upper',3),
            ('chargen boat guard 1','deck',4),('chargen dock guard','dock',5),('chargen class','census',6),
            ('chargen captain','captain',7),('chargen door guard','hall',8),('fargoth','fargoth',0),('imperial guard','imperial_guard',0)]
    entities={'prison':[],'seyda':[]}
    tasks=[(data,palette,identifier,stem,role,outfit(kinds,identifier)) for identifier,stem,role in actors]
    workers=min(resolve_jobs(jobs),len(tasks));print(f'Intro actor workers: {workers}',flush=True)
    for identifier,role,raw,record in ordered_map(_actor,tasks,workers):
        model=record['model'];appearance=record['appearance'];step=record['idle_step'];walkstep=record['walk_step']
        (out/'id1'/model).write_bytes(raw);report['actors'][identifier]=record
        print('actor',identifier,'talk',report['actors'][identifier]['talk_displacement'],flush=True)
        if not role:continue
        refs=[(prison,r) for r in prison['refs'] if r['id'].casefold()==identifier]
        refs.extend((c,r) for c in cells for r in c['refs'] if r['id'].casefold()==identifier)
        for cell,ref in refs:
            interior=bool(cell['flags']&1);name='prison' if interior else 'seyda'
            p=[(ref['position'][i]-(CENTRE[i] if not interior and i<2 else 0))*.25 for i in range(3)]
            if not interior and (abs(p[0])>1024 or abs(p[1])>1024):continue
            fields={'classname':'aw_npc','model':model,'origin':' '.join(f'{v:.5f}' for v in p),
                'angles':f"0 {-math.degrees(ref['rotation_radians'][2]):.5f} 0",'netname':appearance['name'],
                'aw_intro_role':role,'aw_idle_step':f'{step:.7f}','aw_walk_step':f'{walkstep:.7f}'}
            from actor_grounding import fields as grounding_fields
            fields.update(grounding_fields(identifier));fields['aw_ref']=ref['number']
            entities[name].append('{\n'+'\n'.join(quote(k)+' '+quote(v) for k,v in fields.items())+'\n}')
    # Replace the bounded town actors' model paths; all older assets remain available.
    for name in entities:
        path=out/f'id1/maps/{name}.bsp';b=lumps(path.read_bytes());ent=b[0].rstrip(b'\0').decode('cp1252')
        ent=ent.replace('"progs/fargoth.mdl"','"progs/np_fargoth.mdl"').replace('"progs/imperial_guard.mdl"','"progs/np_imperial_guard.mdl"')
        b[0]=(ent+'\n'+'\n'.join(entities[name])+'\n\0').encode('cp1252');raw=pack_lumps(b);path.write_bytes(raw);(out/(name+'.bsp')).write_bytes(raw)
    report['scripts'],report['navigation'],report['speech'],ambience=sounds.result()
    for identifier in ('fargoth','imperial_guard'):
        wav=out/f'id1/sound/npc/{identifier}.wav'
        if wav.exists():wav.with_suffix('.lip').write_bytes(envelope(wav))
    # Authoritative scripts/conditions, for auditing rather than a compatibility claim.
    report['ambience']=add_ship_ambience(out,*ambience)
    # Movies are optional loose installation files, not entries in Morrowind.bsa.
    videos=[p for p in data.rglob('*') if p.is_file() and
            p.name.casefold()=='mw_intro.bik' and p.parent.name.casefold()=='video']
    if len(videos)>1:raise ValueError('Multiple intro movies; select one installation')
    if not movie:
        # Quick test build (--exclude video, tools/build_exclusions.py): New Game starts in the ship.
        print('Quick test build: intro movie left out (--exclude video).',flush=True)
        report['movie']={'status':'excluded by --exclude video (quick test build); start directly in ship'}
    elif videos:
        from prepare_video import cached_prepare_video,video_cache_identity
        converted=out/'intro-video'
        report['movie'],outcome=cached_prepare_video(videos[0],converted,ffmpeg,cache=(str(cache),video_cache_identity(ffmpeg)) if cache else None)
        shutil.copyfile(converted/'mw_intro.awv',out/'id1/intro/mw_intro.awv')
        from file_cache import write_report
        write_report(cache_report,'intro',{'videos':{'hit':int(outcome=='hit'),'miss':int(outcome!='hit'),'enabled':bool(cache)}})
    else:
        print('[warning] Video not found; will not be included: Video/mw_intro.bik',flush=True)
        report['movie']={'status':'missing optional Video/mw_intro.bik; start directly in ship'}
    (out/'intro-conversion.json').write_text(json.dumps(report,indent=2)+'\n')
    ready=json.loads((out/'scene-ready.json').read_text());ready['intro_assets']={'version':1,'actor_frames':21,'talk_frames':[8,9,10,11],'blink_frame':12,'walk_frames':list(range(13,21))}
    (out/'scene-ready.json').write_text(json.dumps(ready,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('data-files','scene','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--ffmpeg',default='ffmpeg')
    p.add_argument('--no-movie',action='store_true',help='Quick test build (--exclude video): leave the intro movie out')
    p.add_argument('--cache',type=Path,help='Per-file cache folder: the movie converted before (same source, size, ffmpeg and code) is copied and verified instead of converted again')
    p.add_argument('--cache-report',type=Path,help='Write the per-file cache hits and misses here (build summary)')
    add_jobs(p);add_root_rule_arg(p);a=p.parse_args();apply_root_rule(a);prepare(a.data_files,a.scene,a.out,a.ffmpeg,a.jobs,movie=not a.no_movie,cache=a.cache,cache_report=a.cache_report)
