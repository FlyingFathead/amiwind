#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Build one source-bound mushroom interior; runtime registration stays explicit.

Generated BSPs, original reference receipts and converted models are private.
The appended registry is a proposal until matching runtime/save tests pass.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mwad.audit import BSA
from mwad.interior import original_doors, read_interior, select_geometry
from mwad.paths import resolve_data_files, child_ci, ensure_external
from prepare_harvest import source_context, placement_source_key, identity_key, prepare_graph
from prepare_harvest_alias import pin, alias_angles, convert_plan


def append_registry(names, master_sha256, previous=None):
    """Append only: legacy0..59 and terrain60..8251 never move."""
    if not re.fullmatch('[0-9a-f]{64}',master_sha256):raise ValueError('Invalid source master pin')
    names=list(names)
    if len(set(n.casefold() for n in names))!=len(names) or any(not n or '\0' in n for n in names):
        raise ValueError('Ambiguous source interior names')
    rows=[]
    if previous is not None:
        if (previous.get('format'),previous.get('master_sha256'),previous.get('first_id'))!=(
                'AmiWind appended interior proposal 1',master_sha256,8252):
            raise ValueError('Previous map registry identity differs')
        rows=[dict(r) for r in previous['entries']]
    seen=set();slugs=set()
    for offset,row in enumerate(rows):
        expected='mi'+hashlib.sha256(('AmiWind original interior 1\n'+row['cell']).encode()).hexdigest()[:12]
        if row['id']!=8252+offset or row['map']!=expected or row['cell'].casefold() in seen or row['map'] in slugs:
            raise ValueError('Invalid or reordered prior map registry')
        seen.add(row['cell'].casefold());slugs.add(row['map'])
    for name in sorted(names):
        if name.casefold() in seen:
            if not any(r['cell']==name for r in rows):raise ValueError('Original cell spelling changed')
            continue
        slug='mi'+hashlib.sha256(('AmiWind original interior 1\n'+name).encode()).hexdigest()[:12]
        if slug in slugs:raise ValueError('Interior filename collision; never silently replace')
        rows.append(dict(cell=name,map=slug,id=8252+len(rows)))
        slugs.add(slug);seen.add(name.casefold())
    if 8252+len(rows)>32767:raise ValueError('Appended IDs exceed signed16-bit compatibility envelope')
    return dict(format='AmiWind appended interior proposal 1',master_sha256=master_sha256,
                first_id=8252,legacy_static_ids=[0,59],reserved_terrain_ids=[60,8251],entries=rows,
                status='proposal_only_not_runtime_registered')


def world_directory(raw):
    if len(raw)<64 or raw[:4]!=b'AWR2':raise ValueError('Expected AWR2')
    count=struct.unpack_from('<I',raw,4)[0]
    if not 1<=count<=8192 or len(raw)!=64+52*count:raise ValueError('AWR2 extent differs')
    rows=[]
    for index,name in enumerate(('seyda','balmora')):
        v=struct.unpack_from('<7f',raw,8+28*index)
        rows.append(dict(name=name,origin=list(v[:3]),core=[list(v[3:5]),list(v[5:7])],town=True))
    for index in range(count):
        v=struct.unpack_from('<8s11f',raw,64+52*index)
        name=v[0].split(b'\0')[0].decode('ascii')
        if name!=f'vf{index:04d}':raise ValueError('AWR2 order differs from runtime IDs')
        rows.append(dict(name=name,origin=list(v[1:4]),core=[list(v[4:6]),list(v[6:8])],
                         coverage=[list(v[8:10]),list(v[10:12])],town=False))
    for row in rows:
        values=row['origin']+sum(row['core'],[])+sum(row.get('coverage',[]),[])
        if not all(math.isfinite(v) for v in values) or any(a>=b for a,b in zip(*row['core'])):
            raise ValueError('Invalid directory bounds')
    return rows


def exterior_target(position, regions):
    """Match town-first, then ascending terrain-core selection; retain authored Z."""
    if len(position)!=3 or not all(math.isfinite(v) for v in position):raise ValueError('Invalid door arrival')
    for row in regions:
        local=[position[i]*.25-row['origin'][i] for i in range(3)]
        if all(row['core'][0][i]<=local[i]<=row['core'][1][i] for i in range(2)):
            return row['name'],local
    raise ValueError('Original exterior door arrival is outside converted directory')


def route_banks(raw, room_name, registry, directory, data_files):
    """Delta banks and exact directed provenance; no inferred reverse/lock bypass."""
    from prepare_scenery import bsa_read, model_geometry, nif_reader, world_bounds
    maps={r['cell'].casefold():r['map'] for r in registry['entries']}
    from area_config import MAP_NAMES
    for name,slug in MAP_NAMES.items():
        if name in maps and maps[name]!=slug:raise ValueError('Registry overlaps an existing interior')
        maps[name]=slug
    bsa=BSA(child_ci(data_files,'Morrowind.bsa'));reader=nif_reader();cache={};links=[];blocked=[]
    doors=[d for d in original_doors(raw) if
           (d['source_interior'] and d['source_cell'].casefold()==room_name.casefold()) or
           d['destination_cell'].casefold()==room_name.casefold()]
    for door in doors:
        extra=[s for s in door['original_subrecords'] if s['tag'] not in ('NAME','DATA','XSCL','DODT','DNAM')]
        if door['script'] or extra:
            blocked.append(dict(door=door,reason='Original script/lock/ownership/other state needs runtime support'))
            continue
        model='meshes/'+door['model'].replace('\\','/').casefold()
        if model not in cache:
            source=bsa_read(bsa,model);_,_,bounds,_=model_geometry(source,reader)
            cache[model]=(bounds,pin(source))
        bounds=world_bounds(cache[model][0],door)
        if door['source_interior']:
            slug=maps.get(door['source_cell'].casefold())
            sources=[(slug,[0.,0.,0.])] if slug else []
        else:
            sources=[]
            for row in directory:
                cover=row.get('coverage',row['core'])
                lo=[bounds[0][i]*.25-row['origin'][i] for i in range(2)]
                hi=[bounds[1][i]*.25-row['origin'][i] for i in range(2)]
                if all(hi[i]>=cover[0][i] and lo[i]<=cover[1][i] for i in range(2)):
                    sources.append((row['name'],row['origin']))
        if door['destination_interior']:
            target=maps.get(door['destination_cell'].casefold())
            arrival=[v*.25 for v in door['destination']['position']]
        else:
            target,arrival=exterior_target(door['destination']['position'],directory)
        if not sources or not target:
            blocked.append(dict(door=door,reason='Original source/destination map is not registered in proposal'));continue
        arrival[2]+=16.875
        yaw=(90-math.degrees(door['destination']['rotation_radians'][2]))%360
        label=door['destination_cell'] or 'Vvardenfell'
        if len(label.encode('cp1252'))>95 or any(ord(c)<32 for c in label):raise ValueError('Unsupported door label')
        for source,origin in sources:
            low=[bounds[0][i]*.25-origin[i]-.5 for i in range(3)]
            high=[bounds[1][i]*.25-origin[i]+.5 for i in range(3)]
            if any(abs(v)>=32768 for v in low+high+arrival) or any(high[i]-low[i]>256 for i in range(3)):
                raise ValueError('Door exceeds current runtime bounds')
            links.append(dict(source=source,target=target,reference=door['number'],mins=low,maxs=high,
                              arrival=arrival,yaw=yaw,label=label,original=door,model=cache[model][1]))
    banks={}
    for source in sorted({r['source'] for r in links}):
        rows=[r for r in links if r['source']==source]
        if len(rows)>128:raise ValueError('Door bank exceeds runtime capacity')
        lines=['AWD3']
        for row in rows:
            if max(len(row['source']),len(row['target']))>15:raise ValueError('Door map name exceeds runtime buffer')
            lines.append(row['source']+' '+row['target']+' '+str(row['reference'])+' '+
                         ' '.join(f'{v:.5f}' for v in row['mins']+row['maxs']+row['arrival']+[row['yaw']])+'\t'+row['label'])
        banks['doors-'+source+'.txt']=('\n'.join(lines)+'\n').encode('cp1252')
    return banks,dict(original_directed_doors=doors,links=links,blocked=blocked,
                      status='delta_only_merge_existing_banks_before_install',
                      runtime_blockers=['Appended interior registry not installed','Current terrain path skips door banks'],
                      reachability='unaccepted; directory selection is not a runtime traversal')


def finish_room(data_files, scene, room_name, registry, regions_raw, *, media_payload=None):
    """Finish an already-built fresh room with exact harvest and door closure."""
    import numpy as np
    from prepare_scenery import export_refs
    data=resolve_data_files(data_files);scene=Path(scene)
    raw=child_ci(data,'Morrowind.esm').read_bytes()
    registry=append_registry([],pin(raw)['sha256'],registry)
    rows=[r for r in registry['entries'] if r['cell']==room_name]
    if len(rows)!=1:raise ValueError('Room must have one exact appended registry entry')
    slug=rows[0]['map'];context=source_context(raw,max_plants=256,intern_root_spans=True)
    refs=[dict(r) for r in context['original'].values() if r['cell']==room_name]
    for ref in refs:ref['source_key']=placement_source_key(ref,context['full']['master_sha256'])
    report=json.loads((scene/'area-work'/slug/'conversion.json').read_text())
    if report['master_sha256']!=registry['master_sha256'] or set(report.get('harvest_excluded_references',[]))!={r['number'] for r in refs}:
        raise ValueError('Room build did not exclude exact source harvest references')
    palette=(scene/'id1/gfx/palette.lmp').read_bytes()
    export_refs(data,scene/'harvest-source',refs,{},[0,0,0],texture_size=32,jobs=1)
    index_raw=(scene/'harvest-source/scenery-index.json').read_bytes();index=json.loads(index_raw)
    if index['errors']:raise ValueError('Harvest source conversion failed')
    packet=scene/'harvest-source/scenery.mwpak';bsp=scene/'id1/maps'/f'{slug}.bsp'
    if pin(bsp.read_bytes())['sha256']!=report.get('bsp_sha256'):
        raise ValueError('Room BSP changed after exact source exclusions were recorded')
    bounds=np.asarray([r['bounds'] for r in index['references']])*.25
    plan=dict(format='AmiWind external harvest plan 1',max_plants=256,intern_root_spans=True,compact_models=True,
              global_catalogue_sha256=context['catalogue'],global_slots=len(context['indices']),
              inputs=dict(master=pin(raw),index=pin(index_raw),packet=pin(packet.read_bytes()),palette=pin(palette)),
              maps=[dict(name=slug,path=f'maps/{slug}.bsp',**pin(bsp.read_bytes()),origin=[0,0,0],
                         source_kind='interior',source_cell=room_name,
                         coverage=[(bounds[:,0,:2].min(0)-1).tolist(),(bounds[:,1,:2].max(0)+1).tolist()],
                         keys=[identity_key(r['source_key']) for r in refs])])
    (scene/'harvest-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    harvest=convert_plan(plan,raw,index_raw,packet,palette,scene/'id1',scene/'harvest-payload',media_payload=media_payload)
    for row in harvest['files']:
        source=scene/'harvest-payload'/row['path'];target=scene/'id1'/row['path']
        if target.exists():raise ValueError('Refusing payload overwrite')
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    banks,doors=route_banks(raw,room_name,registry,world_directory(regions_raw),data)
    delta=scene/'door-delta';delta.mkdir(exist_ok=False)
    for name,payload in banks.items():(delta/name).write_bytes(payload)
    (scene/'doors.json').write_text(json.dumps(doors,indent=2)+'\n')
    (scene/'map-registry-proposal.json').write_text(json.dumps(registry,indent=2)+'\n')
    closure=[dict(path=p.relative_to(scene/'id1').as_posix(),**pin(p.read_bytes())) for p in sorted((scene/'id1').rglob('*')) if p.is_file()]
    final=dict(format='AmiWind single harvest interior candidate 1',cell=room_name,map=slug,
               master=pin(raw),region_directory=pin(regions_raw),files=closure,
               original_plants=len(refs),models=len(harvest['models']),global_catalogue_sha256=context['catalogue'],
               original_slots=[context['indices'][identity_key(r['source_key'])] for r in refs],
               harvest=harvest,door_banks=[dict(path=n,**pin(b)) for n,b in banks.items()],
               native_acceptance='not_run',admission='pending_exact_heap_and_runtime_registration')
    (scene/'room-closure.json').write_text(json.dumps(final,indent=2)+'\n')
    return final


def convert_room(data_files, scene, cell_name, registry, palette, regions_raw, tools, *, media_payload=None):
    from prepare_area import build_room
    data=resolve_data_files(data_files);scene=ensure_external(scene,'new harvest interior')
    raw=child_ci(data,'Morrowind.esm').read_bytes();context=source_context(raw,max_plants=256,intern_root_spans=True)
    registry=append_registry([],pin(raw)['sha256'],registry)
    rows=[r for r in registry['entries'] if r['cell']==cell_name]
    if registry['master_sha256']!=pin(raw)['sha256'] or len(rows)!=1:raise ValueError('Room/source registry mismatch')
    refs=[dict(r) for r in context['original'].values() if r['cell']==cell_name]
    for ref in refs:ref['source_key']=placement_source_key(ref,context['full']['master_sha256'])
    if not refs:raise ValueError('Room has no original numeric harvestable mushrooms')
    prepare_graph(context,refs,lambda r:({'model':'@0','representation':'external_alias','scale':r['scale']},
                                        [v*.25 for v in r['position']],alias_angles(r)))
    cell=read_interior(child_ci(data,'Morrowind.esm'),cell_name,include_interior_entrances=True)
    select_geometry(cell,harvest_references=refs,harvest_master_sha256=context['full']['master_sha256'])
    if len(palette)!=768:raise ValueError('Expected RGB palette')
    scene.mkdir(parents=True,exist_ok=False);(scene/'id1/gfx').mkdir(parents=True)
    (scene/'id1/gfx/palette.lmp').write_bytes(palette)
    entry=dict(cell=cell_name,map=rows[0]['map'],original_door_arrivals=True,retain_selected_geometry=True,
               harvest_references=refs,harvest_master_sha256=context['full']['master_sha256'])
    report,_=build_room((data,scene,entry,*tools,''))
    (scene/'id1/maps').mkdir();shutil.copyfile(scene/'area-work'/entry['map']/'room.bsp',scene/'id1/maps'/f"{entry['map']}.bsp")
    return finish_room(data,scene,cell_name,registry,regions_raw,media_payload=media_payload)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('data-files','out','registry','palette','regions','qbsp','vis','light'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--cell',required=True);parser.add_argument('--media-payload',type=Path)
    args=parser.parse_args()
    result=convert_room(args.data_files,args.out,args.cell,json.loads(args.registry.read_text()),
                        args.palette.read_bytes(),args.regions.read_bytes(),[args.qbsp,args.vis,args.light],
                        media_payload=args.media_payload)
    print(json.dumps({k:result[k] for k in ('cell','map','original_plants','models','admission')},indent=2))


if __name__=='__main__':main()
