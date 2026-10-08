#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Add three bounded, dressed idle actors to an externally converted town."""
import argparse, hashlib, json, math, shutil, subprocess, tempfile, wave
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.audit import BSA
from mwad.npc import load_master,outfit,greeting_fixture,behavior_record,greeting_settings
from mwad.paths import ensure_external
from known_inputs import input_sha256
from npc_geometry import Assets,Skeleton,assemble,bake,animated_mdl
from player_hull import lumps,pack_lumps,PROFILE
from prepare_quake import CENTRE,SCALE

def quote(value):
    if any(c in str(value) for c in ('"','\\','\0','\n','\r')):raise ValueError('Unsafe entity value')
    return '"'+str(value)+'"'

def display_text(value):
    """Readable single-line text for BSP's non-escaping quoted strings.

    Keep authored text in conversion reports; only its displayed representation
    uses apostrophes for embedded quotation marks. Never apply this to keys,
    paths or numeric fields, and retain quote() validation of the result.
    """
    text=' '.join(str(value).replace('"', "'").split())
    quote(text)
    return text

def prepare(data,scene,out,ffmpeg='ffmpeg'):
    data=ensure_external(data,'owned data');scene=ensure_external(scene,'mesh scene');out=ensure_external(out,'NPC scene')
    ready=json.loads((scene/'scene-ready.json').read_text())
    if ready.get('standing_hull_profile')!=PROFILE:raise ValueError('Rebuild matching standing hull first')
    if ready.get('npcs'):raise ValueError('Scene already has NPCs')
    shutil.copytree(scene,out)
    kinds,cells,topics=load_master(data/'Morrowind.esm');assets=Assets(data,BSA(data/'Morrowind.bsa'))
    skeleton=Skeleton(assets);times,step=skeleton.idle_times(8)
    palette=(scene/'id1/gfx/palette.lmp').read_bytes();models={};actors=[];entities=[]
    target=out/'id1/progs';sounds=out/'id1/sound/npc';sounds.mkdir(parents=True,exist_ok=True)
    for identifier,limit in [('fargoth',1),('imperial guard',2)]:
        appearance=outfit(kinds,identifier);greeting=greeting_fixture(topics,appearance)
        behavior=behavior_record(kinds['NPC_'][identifier],SCALE)
        settings=greeting_settings(kinds,behavior,SCALE)
        shapes,materials,textures=assemble(assets,appearance,skeleton,times)
        frames,faces,uv,skin=bake(shapes,materials,textures,palette)
        stem=identifier.replace(' ','_');model='progs/'+stem+'.mdl';voice='npc/'+stem+'.wav'
        raw=animated_mdl(frames,faces,uv,skin);(out/'id1'/model).write_bytes(raw)
        sound=assets.read('sound/'+greeting['voice'])
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'voice.mp3';source.write_bytes(sound)
            subprocess.run([ffmpeg,'-v','error','-nostdin','-i',str(source),'-ac','1','-ar','11025','-c:a','pcm_u8',str(out/'id1/sound'/voice)],check=True)
        with wave.open(str(out/'id1/sound'/voice)) as wav:
            if wav.getnframes()>11025*15:raise ValueError('Greeting exceeds 15-second budget')
            duration=wav.getnframes()/wav.getframerate()
        models[identifier]={'appearance':appearance,'model':model,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
            'frames':len(frames),'vertices':frames.shape[1],'triangles':len(faces),'idle_step':float(step),
            'bounds':[frames.min((0,1)).tolist(),frames.max((0,1)).tolist()],'greeting':greeting,'voice_seconds':duration,
            'behavior':behavior,'greeting_settings':settings}
        refs=[ref for cell in cells if (cell['x'],cell['y'])==(-2,-9) for ref in cell['refs'] if ref['id'].casefold()==identifier]
        refs=[ref for ref in refs if all(abs((ref['position'][i]-CENTRE[i])*SCALE)<736 for i in (0,1))]
        if len(refs)<limit:raise ValueError('Missing requested actor placements')
        for ref in refs[:limit]:
            if abs(ref['scale']-1)>1e-5:raise ValueError('Actor instance scale needs a separate bake')
            pos=[(ref['position'][i]-(CENTRE[i] if i<2 else 0))*SCALE for i in range(3)]
            fields={'classname':'aw_npc','aw_ref':str(ref['number']),'model':model,'origin':' '.join(format(x,'.5f') for x in pos),
                    'angles':'0 '+str(-ref['rotation_radians'][2]*180/math.pi)+' 0',
                    'netname':display_text(appearance['name']),'aw_voice':voice,'aw_line':display_text(greeting['text']),
                    'aw_idle_step':format(step,'.7f'),
                    'aw_hello_distance':settings['distance'],
                    'aw_hello_reset':settings['reset_distance'],
                    'aw_greet_duration':settings['duration']}
            entities.append('{\n'+'\n'.join(quote(k)+' '+quote(v) for k,v in fields.items())+'\n}')
            actors.append({'id':identifier,'reference':ref['number'],'position':pos,'angles':fields['angles']})
    b=lumps((out/'seyda.bsp').read_bytes());b[0]=b[0].rstrip(b'\0')+('\n'+'\n'.join(entities)+'\n\0').encode('cp1252')
    raw=pack_lumps(b);(out/'seyda.bsp').write_bytes(raw);(out/'id1/maps/seyda.bsp').write_bytes(raw)
    report={'scope':'three nonblocking idle actors; facing and bounded proximity/E Hello auditions; authored wandering retained but not executed; no full dialogue or combat',
            'actors':actors,'models':models,'master_sha256':input_sha256(data/'Morrowind.esm')}
    ready['npcs']=report;(out/'scene-ready.json').write_text(json.dumps(ready,indent=2)+'\n')
    (out/'npc-report.json').write_text(json.dumps(report,indent=2)+'\n');return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('data-files','scene','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--ffmpeg',default='ffmpeg');a=p.parse_args()
    try:print(json.dumps(prepare(a.data_files,a.scene,a.out,a.ffmpeg),indent=2))
    except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as e:p.exit(1,str(e)+'\n')
if __name__=='__main__':main()
