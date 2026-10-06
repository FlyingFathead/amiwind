#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Add exact original exterior loading-door geometry to retained private maps.

No reverse door, locked-door bypass, image installation or admission waiver is
created. Directed activation banks are supplied and checked independently.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.interior import original_doors
from mwad.paths import resolve_data_files,child_ci
from prepare_harvest_room import world_directory
from prepare_scenery import export_refs
from prepare_mesh_bsp import append_meshes,_prepare_model
from prepare_world_flora import verify_retained_content
from world_scenery import region_references
from compact_bsp import entities
from player_hull import lumps


def pin(raw):return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def select_doors(master,numbers):
    if not numbers or len(numbers)!=len(set(numbers)):raise ValueError('Unique original door references required')
    records={}
    for d in original_doors(master):
        if d['number'] in numbers:
            if d['number'] in records:raise ValueError('Ambiguous original door reference')
            records[d['number']]=d
    if set(records)!=set(numbers):raise ValueError('Missing original door reference')
    result=[]
    for number in sorted(records):
        d=records[number]
        if d['source_interior'] or not d['destination_interior']:raise ValueError('Expected original exterior entrance')
        extra=[s for s in d['original_subrecords'] if s['tag'] not in ('NAME','DATA','XSCL','DODT','DNAM')]
        if d['script'] or extra:raise ValueError('Original lock/script/ownership needs explicit support')
        result.append(d)
    return result


def append_geometry(source,output,packet,index,entry,palette,local):
    source,output,local=Path(source),Path(output),Path(local)
    raw=source.read_bytes();selected=region_references(index,entry)
    if not selected:raise ValueError('No source door intersects this map')
    numbers={r['number'] for r in selected};old=entities(lumps(raw)[0])
    if any(e.get('aw_ref') in {str(n) for n in numbers} for e in old):raise ValueError('Original door already present; do not duplicate')
    local.mkdir(parents=True,exist_ok=False);shutil.copyfile(packet,local/'scenery.mwpak')
    subset={**index,'references':selected}
    (local/'scenery-index.json').write_text(json.dumps(subset)+'\n')
    profiles={n:p for g in subset['groups'].values() for n,p in g.get('visual_profiles',{}).items()}
    prepared={}
    for mi in {r['model_index'] for r in selected}:
        model=index['models'][mi]
        _,prepared[mi]=_prepare_model((mi,model,profiles[model['source']],Path(packet),index['textures']))
    report=append_meshes(source,output,local,Path(palette),centre=[v/.25 for v in entry['origin'][:2]],jobs=1,
        references=sorted(numbers),prepared_models=prepared,retain_dressing=True,
        collision_bounds=entry['coverage'],map_identity=entry['name'])
    candidate=output.read_bytes();proof=verify_retained_content(raw,candidate)
    new=entities(lumps(candidate)[0]);added=[e for e in new if e not in old]
    if new[:len(old)]!=old:raise ValueError('Door overlay changed retained entity order or attributes')
    if len(added)!=len(selected) or {int(e.get('aw_ref','0')) for e in added}!=numbers:
        raise ValueError('Door overlay changed unrelated entity membership')
    for r in selected:
        e=next(e for e in added if int(e['aw_ref'])==r['number'])
        origin=list(map(float,e['origin'].split()));expected=[r['position'][0]*.25-entry['origin'][0],r['position'][1]*.25-entry['origin'][1],r['position'][2]*.25]
        if any(abs(a-b)>.00002 for a,b in zip(origin,expected)):raise ValueError('Original door pose was not retained')
        if abs(float(e['angles'].split()[1])+math.degrees(r['rotation_radians'][2]))>.00002:raise ValueError('Original door yaw was not retained')
    if source.read_bytes()!=raw:raise ValueError('Retained map changed during conversion')
    return dict(base=pin(raw),candidate=pin(candidate),references=sorted(numbers),added_entities=added,
                retained=proof,conversion=report,source_collision='authored collision node when present, otherwise original visual mesh; existing convex conversion policy')


def prepare(data_files,base_id1,plan,regions_raw,door_rows,output):
    data=resolve_data_files(data_files);base=Path(base_id1);out=Path(output)
    if out.exists():raise ValueError('Fresh exterior door output required')
    master=child_ci(data,'Morrowind.esm').read_bytes();palette=(base/'gfx/palette.lmp').read_bytes()
    if pin(master)['sha256']!=plan['master_sha256'] or pin(regions_raw)['sha256']!=plan['regions_sha256']:
        raise ValueError('Original source/directory identity differs')
    if pin(json.dumps(door_rows,sort_keys=True,separators=(',',':')).encode())['sha256']!=plan['door_rows_sha256']:
        raise ValueError('Authenticated directed door rows changed')
    if len(palette)!=768 or pin(palette)['sha256']!=plan['palette_sha256']:raise ValueError('Palette identity differs')
    selected=select_doors(master,plan['references']);original={d['number']:d for d in selected}
    for row in door_rows:
        if row['reference'] in original and row['original']!=original[row['reference']]:raise ValueError('Directed door provenance differs')
    directory={r['name']:r for r in world_directory(regions_raw) if not r['town']}
    bases={}
    for row in plan['maps']:
        if row['name'] not in directory or row['name'] in bases:raise ValueError('Invalid/duplicate exterior map')
        path=base/'maps'/(row['name']+'.bsp');raw=path.read_bytes()
        if pin(raw)!={k:row[k] for k in ('bytes','sha256')}:raise ValueError('Retained exterior BSP identity differs')
        bases[row['name']]=path
    if not bases:raise ValueError('No retained exterior maps')
    out.mkdir(parents=True);(out/'id1/maps').mkdir(parents=True);(out/'id1/gfx').mkdir()
    (out/'id1/gfx/palette.lmp').write_bytes(palette)
    profiles={'meshes/'+d['model'].replace('\\','/').lower():dict(ratio=1.,texture_size=64,collision_source='root_node_or_visual',preserve_shared_seams=True) for d in selected}
    refs=[dict(d,type='DOOR',cell=d['source_grid'],scene_groups=['original_doors']) for d in selected]
    groups={'original_doors':dict(references=plan['references'],visual_profiles=profiles)}
    export_refs(data,out/'source',refs,groups,[0,0,0],texture_size=64,metadata=dict(master_sha256=plan['master_sha256'],scene_kind='exterior'),jobs=1)
    index=json.loads((out/'source/scenery-index.json').read_text())
    if index['errors'] or len(index['references'])!=len(refs):raise ValueError('Original door source conversion failed')
    required={name for name,r in directory.items() if region_references(index,r)}
    if required!=set(bases):raise ValueError('Plan does not cover every overlapping original door map')
    rows=[]
    for name,source in sorted(bases.items()):
        entry=directory[name]
        for r in region_references(index,entry):
            bank=[b for b in door_rows if b['source']==name and b['reference']==r['number']]
            if len(bank)!=1:raise ValueError('Each placed original door needs one authored activation route')
            low=[r['bounds'][0][k]*.25-(entry['origin'][k] if k<2 else 0)-.5 for k in range(3)]
            high=[r['bounds'][1][k]*.25-(entry['origin'][k] if k<2 else 0)+.5 for k in range(3)]
            if any(abs(a-b)>.0001 for a,b in zip(low+high,bank[0]['mins']+bank[0]['maxs'])):raise ValueError('Activation bounds differ from original rendered model')
        report=append_geometry(source,out/'id1/maps'/(name+'.bsp'),out/'source/scenery.mwpak',index,entry,out/'id1/gfx/palette.lmp',out/'work'/name)
        rows.append(dict(name=name,**report))
    report=dict(format='AmiWind original exterior door overlay 1',master_sha256=plan['master_sha256'],region_directory=pin(regions_raw),
        original_references=selected,models=index['models'],maps=rows,native_acceptance='not_run',
        admission='pending target heap/model limits and directed-route integration',no_original_assets_in_public_source=True)
    (out/'overlay.json').write_text(json.dumps(report,indent=2)+'\n');return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('data-files','base-id1','plan','regions','doors','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.data_files,a.base_id1,json.loads(a.plan.read_text()),a.regions.read_bytes(),json.loads(a.doors.read_text())['original_door_links'],a.out)
if __name__=='__main__':main()
