#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Bind converted exterior objects to authored opening reference identities."""
import argparse
import json
from pathlib import Path
import re

import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.audit import records,subrecords,string,cell_data
from mwad.paths import ensure_external,resolve_data_files,child_ci,replace_bytes,replace_copy
from prepare_quake import CENTRE
from prepare_scenery import export_refs
from prepare_mesh_bsp import append_meshes
from player_hull import lumps,pack_lumps


def opening_references(data_files):
    """(every exterior reference with its object type and model, the references the opening binds:
    the ship's disable list of ChargenClassNPC and the tutorial barrel, the disable list ids).
    One reading of the master for the legacy scene (prepare) and the CHIM builder (chim.seyda)."""
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
    wanted=[r for r in refs if r['id'].casefold() in disabled or r['id'].casefold()==BARREL]
    return refs,wanted,disabled


BARREL='chargen barrel fatigue'


def prepare(data_files,scene,allow_append=True):
    data_files=resolve_data_files(data_files);scene=ensure_external(scene,'opening references')
    from mwad.paths import unshare_tree
    unshare_tree(scene)  # in place: BUILD-POOL-READONLY-SCENE-WRITE-35
    refs,wanted,disabled=opening_references(data_files)
    def point(ref):return [(ref['position'][i]-(CENTRE[i] if i<2 else 0))*.25 for i in range(3)]
    path=scene/'id1/maps/seyda.bsp';raw=path.read_bytes();b=lumps(raw);found=set()
    # Seyda Neen's entities come from the scene entity list, not the carrier's lump (BUILD-SEYDA-ENTITY-BUS-48)
    from seyda_entities import publish as publish_entities, writer_lump
    b[0]=writer_lump(scene,raw);ent=b[0].rstrip(b'\0').decode('cp1252')
    # A source-only carrier (the bsp stage's --seyda-source carrier, BUILD-SEYDA-HULL2-32) has no geometry: the
    # barrel is already one of its placements, and appending meshes to it is refused.
    from prepare_seyda_source import is_source_carrier_lump
    carrier=is_source_carrier_lump(b[0])
    if carrier:allow_append=False
    by_number={r['number']:r for r in wanted}
    def bind(match):
        block=match.group();f=dict(re.findall(r'"([^"]+)"\s+"([^"]*)"',block))
        if f.get('classname') not in ('func_wall','aw_npc') or 'origin' not in f:return block
        pos=list(map(float,f['origin'].split()))
        candidates=refs if f.get('classname')=='aw_npc' else wanted
        hits=[r for r in candidates if all(abs(a-b)<.002 for a,b in zip(pos,point(r)))
              and (f.get('classname')!='aw_npc' or r.get('type')=='NPC_')]
        if carrier and not hits and f.get('classname')=='func_wall' and f.get('aw_ref','').isdigit() \
                and int(f['aw_ref']) in by_number:
            # the carrier's placement carries its original reference: identity by number, not by origin
            hits=[by_number[int(f['aw_ref'])]]
        if len(hits)>1:raise ValueError('Ambiguous placed reference at '+str(pos))
        if not hits:return block
        ref=hits[0];found.add(ref['number'])
        extra='\n"aw_ref" "'+str(ref['number'])+'"\n'
        if ref['id'].casefold() in disabled:extra+='"aw_story_hidden" "1"\n'
        block=re.sub(r'\n"aw_ref" "[^"]*"','',block)
        block=re.sub(r'\n"aw_story_hidden" "[^"]*"','',block)
        return block[:-1]+extra+'}'
    # Validate a direct source carrier before rewriting any entity bytes.
    ent=re.sub(r'\{[^{}]*\}',bind,ent)
    barrel=next(r for r in wanted if r['id'].casefold()==BARREL)
    if barrel['number'] not in found and not allow_append:
        raise ValueError('seyda: source-only carrier is missing the original tutorial barrel %d (AW_REF_COURTYARD_BARREL); geometry append refused'%barrel['number'])
    # replaced whole: the area stage made this map (BUILD-POOL-READONLY-SCENE-WRITE-35)
    b[0]=(ent+'\0').encode('cp1252');replace_bytes(path,pack_lumps(b))
    if barrel['number'] not in found:
        parts=scene/'opening-barrel-source';group='opening_barrel';barrel['scene_groups']=[group]
        export_refs(data_files,parts,[barrel],{group:{'references':[barrel['number']]}},[*CENTRE,0],4096,32,{'scope':'authored tutorial barrel'})
        base=scene/'seyda-before-barrel.bsp';replace_copy(path,base)
        append_meshes(base,path,parts,scene/'id1/gfx/palette.lmp');found.add(barrel['number'])
    replace_copy(path,scene/'seyda.bsp')
    publish_entities(scene,path.read_bytes())
    result={'bound':sorted(found),'not_converted':[r['number'] for r in wanted if r['number'] not in found],
            'source_disable_ids':sorted(disabled)}
    (scene/'opening-refs.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-files',type=Path,required=True);p.add_argument('--scene',type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.data_files,a.scene),indent=2))
