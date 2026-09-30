#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Resolve authored DOOR sound IDs and SOUN files for converted entrances."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.audit import BSA,records,subrecords,string,cell_data
from mwad.paths import resolve_data_files,child_ci,ensure_external
from npc_geometry import Assets
from prepare_intro import voice_convert


def catalogue(raw, wanted):
    doors={};sounds={};cells=[]
    for tag,_,payload in records(raw):
        if tag not in ('DOOR','SOUN','CELL'):continue
        parts=list(subrecords(payload));s=dict(parts)
        if 'DELE' in s:continue
        if tag=='DOOR':doors[string(s['NAME']).casefold()]=[string(s.get(k,b'')).casefold() for k in ('SNAM','ANAM')]
        elif tag=='SOUN':sounds[string(s['NAME']).casefold()]={'source':string(s['FNAM']),'volume':s['DATA'][0]/255}
        else:cells.append(cell_data(parts))
    out=[]
    for cell in cells:
        for ref in cell['refs']:
            if ref.get('deleted') or ref['number'] not in wanted:continue
            ids=doors.get(ref['id'].casefold())
            if ids is None:continue
            row={'reference':ref['number'],'base':ref['id'],'sounds':[]}
            for identifier in ids:
                if identifier and identifier not in sounds:raise ValueError('Missing authored door sound '+identifier)
                row['sounds'].append(dict(id=identifier,**sounds[identifier]) if identifier else None)
            out.append(row)
    return sorted(out,key=lambda r:r['reference'])


def prepare(data,scene,ffmpeg='ffmpeg'):
    data=resolve_data_files(data);scene=ensure_external(scene,'door audio');wanted={172860}
    for p in (scene/'id1').glob('scene-doors*.txt'):
        lines=p.read_text(encoding='cp1252').splitlines()
        if not lines or lines[0]!='AWD3':raise ValueError('Door audio needs placed-reference AWD3 links')
        wanted.update(int(line.split()[2]) for line in lines[1:] if line.strip())
    rows=catalogue(child_ci(data,'Morrowind.esm').read_bytes(),wanted)
    if len(rows)>128:raise ValueError('Door sound catalogue exceeds runtime bound')
    assets=Assets(data,BSA(child_ci(data,'Morrowind.bsa')));converted={};lines=['AWSFX1']
    for row in rows:
        names=[];volumes=[];durations=[]
        for sound in row['sounds']:
            if sound is None:names.append('-');volumes.append(0);durations.append(0);continue
            source=sound['source'].replace('\\','/').casefold()
            name='doors/d'+hashlib.sha256(source.encode()).hexdigest()[:16]+'.wav'
            if source not in converted:
                receipt=voice_convert(assets,sound['source'],scene/'id1/sound'/name,ffmpeg,speech=False)
                converted[source]=dict(receipt,path=name)
            names.append(name);volumes.append(sound['volume']);durations.append(converted[source]['seconds'])
        lines.append(f"{row['reference']} {' '.join(names)} "+' '.join(f'{v:.6f}' for v in (*volumes,*durations)))
    (scene/'id1/door-sounds.txt').write_text('\n'.join(lines)+'\n')
    report={'doors':rows,'files':list(converted.values()),'format':'AWSFX1','runtime':'11025 Hz mono unsigned PCM; source SOUN volume'}
    (scene/'door-audio.json').write_text(json.dumps(report,indent=2)+'\n');return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-files',type=Path,required=True);p.add_argument('--scene',type=Path,required=True);p.add_argument('--ffmpeg',default='ffmpeg')
    a=p.parse_args();r=prepare(a.data_files,a.scene,a.ffmpeg);print('Door audio:',len(r['doors']),'doors,',len(r['files']),'unique samples')
