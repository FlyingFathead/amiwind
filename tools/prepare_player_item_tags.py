#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Write per-frame player item tags without rebuilding/altering existing bodies."""
import argparse,hashlib,json,struct
from pathlib import Path
import npc_anim
from npc_geometry import Skeleton
from npc_items import bone_tags,tag_text
from prepare_player_view import _sources,body_appearance,BODY_PROFILE,BODY_EXTRA,BODY_READY

def prepare(data_files,base_id1,out_id1):
    base_id1=Path(base_id1);out_id1=Path(out_id1)
    kinds,assets,rigs=_sources(Path(data_files));report=[]
    rows=(base_id1/'view/bodies.txt').read_text().splitlines()
    if not rows or rows[0]!='AWPB1':raise ValueError('Player body catalogue unavailable')
    for row in rows[1:]:
        race,female,path=row.split('\t');female=bool(int(female))
        appearance=body_appearance(kinds,race,female);rig=appearance['skeleton']
        if rig not in rigs:rigs[rig]=Skeleton(assets,rig)
        female_rig=None
        if female and rig=='meshes/base_anim.nif':
            if npc_anim.FEMALE_SKELETON not in rigs:rigs[npc_anim.FEMALE_SKELETON]=Skeleton(assets,npc_anim.FEMALE_SKELETON)
            female_rig=rigs[npc_anim.FEMALE_SKELETON]
        profile=list(npc_anim.profiles()[BODY_PROFILE])+[list(g) for g in BODY_EXTRA+BODY_READY]
        kit,groups=npc_anim.plan(rigs[rig],profile,female_rig,appearance.get('weight',1.))
        kit,groups=npc_anim.player_layers(kit,groups,compact=True)
        times=npc_anim.idle_compatible_times(groups)
        raw=(base_id1/path).read_bytes()
        if len(raw)<84 or raw[:4]!=b'IDPO':raise ValueError('Actual body is not an MDL')
        sw,sh,nv,nt,frames=struct.unpack_from('<5i',raw,52)
        fitted,index=npc_anim.fit(groups,nv,nt,sw,sh)
        if len(index)!=frames or npc_anim.player_layout(fitted).strip()!=(base_id1/path).with_suffix('.anm').read_text().strip():
            raise ValueError('Tag plan differs from exact body frame/layout '+path)
        tags=bone_tags(kit,times,appearance,{'weapon':True,'shield':True})
        text=tag_text([tags[int(i)] for i in index],{})
        target=(out_id1/path).with_suffix('.tag');target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text,encoding='ascii',newline='\n')
        report.append(dict(model=path,model_sha256=hashlib.sha256(raw).hexdigest(),frames=frames,tag=str(target.relative_to(out_id1)),tag_sha256=hashlib.sha256(text.encode()).hexdigest()))
    return {'bodies':report,'scope':'tag-only; existing MDL/ANM bytes and frame indexing unchanged'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-files',required=True,type=Path);p.add_argument('--base-id1',required=True,type=Path);p.add_argument('--out-id1',required=True,type=Path);p.add_argument('--report',required=True,type=Path)
    a=p.parse_args();a.report.write_text(json.dumps(prepare(a.data_files,a.base_id1,a.out_id1),indent=2)+'\n',encoding='utf-8',newline='\n')
if __name__=='__main__':main()
