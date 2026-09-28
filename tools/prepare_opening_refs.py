#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Bind converted exterior objects to authored opening reference identities."""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.audit import records,subrecords,string,cell_data
from mwad.paths import ensure_external,resolve_data_files,child_ci
from prepare_quake import CENTRE
from prepare_scenery import export_refs
from prepare_mesh_bsp import append_meshes
from player_hull import lumps,pack_lumps


def prepare(data_files,scene):
    data_files=resolve_data_files(data_files);scene=ensure_external(scene,'opening references')
    raw=child_ci(data_files,'Morrowind.esm').read_bytes();objects={};cells=[];disabled=None
    for tag,flags,payload in records(raw):
        if tag not in ('SCPT','CELL','STAT','CONT','ACTI','LIGH','DOOR','NPC_'):continue
        subs=list(subrecords(payload));f=dict(subs)
        if tag=='SCPT' and string(f['SCHD'][:32]).casefold()=='chargenclassnpc':
            disabled={x.casefold() for x in re.findall(r'"([^"]+)"\s*->\s*disable',string(f['SCTX']),re.I)}
        elif tag=='CELL':
            cell=cell_data(subs)
            if not cell['flags']&1:cells.append(cell)
        elif 'NAME' in f and 'DELE' not in f:
            objects[string(f['NAME']).casefold()]={'type':tag,'model':string(f.get('MODL',b''))}
    if not disabled:raise ValueError('Original ship disable list missing')
    refs=[dict(r,**objects.get(r['id'].casefold(),{})) for c in cells for r in c['refs'] if not r.get('deleted')]
    wanted=[r for r in refs if r['id'].casefold() in disabled or r['id'].casefold()=='chargen barrel fatigue']
    def point(ref):return [(ref['position'][i]-(CENTRE[i] if i<2 else 0))*.25 for i in range(3)]
    path=scene/'id1/maps/seyda.bsp';b=lumps(path.read_bytes());found=set();ent=b[0].rstrip(b'\0').decode('cp1252')
    def bind(match):
        block=match.group();f=dict(re.findall(r'"([^"]+)"\s+"([^"]*)"',block))
        if f.get('classname') not in ('func_wall','aw_npc') or 'origin' not in f:return block
        pos=list(map(float,f['origin'].split()))
        candidates=refs if f.get('classname')=='aw_npc' else wanted
        hits=[r for r in candidates if all(abs(a-b)<.002 for a,b in zip(pos,point(r)))
              and (f.get('classname')!='aw_npc' or r.get('type')=='NPC_')]
        if len(hits)>1:raise ValueError('Ambiguous placed reference at '+str(pos))
        if not hits:return block
        ref=hits[0];found.add(ref['number'])
        extra='\n"aw_ref" "'+str(ref['number'])+'"\n'
        if ref['id'].casefold() in disabled:extra+='"aw_story_hidden" "1"\n'
        block=re.sub(r'\n"aw_ref" "[^"]*"','',block)
        block=re.sub(r'\n"aw_story_hidden" "[^"]*"','',block)
        return block[:-1]+extra+'}'
    ent=re.sub(r'\{[^{}]*\}',bind,ent);b[0]=(ent+'\0').encode('cp1252');path.write_bytes(pack_lumps(b))
    barrel=next(r for r in wanted if r['id'].casefold()=='chargen barrel fatigue')
    if barrel['number'] not in found:
        parts=scene/'opening-barrel-source';group='opening_barrel';barrel['scene_groups']=[group]
        export_refs(data_files,parts,[barrel],{group:{'references':[barrel['number']]}},[*CENTRE,0],4096,32,{'scope':'authored tutorial barrel'})
        base=scene/'seyda-before-barrel.bsp';shutil.copyfile(path,base)
        append_meshes(base,path,parts,scene/'id1/gfx/palette.lmp');found.add(barrel['number'])
    shutil.copyfile(path,scene/'seyda.bsp')
    result={'bound':sorted(found),'not_converted':[r['number'] for r in wanted if r['number'] not in found],
            'source_disable_ids':sorted(disabled)}
    (scene/'opening-refs.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files',type=Path,required=True);p.add_argument('--scene',type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.data_files,a.scene),indent=2))
