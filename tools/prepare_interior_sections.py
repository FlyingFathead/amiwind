#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Create source-bound whole-reference interior sections; never install images.

The plan is explicit: this tool does not invent grid cuts, original doors or
visibility certification. Every original selected reference survives the union.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
import shutil
import struct
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from compact_bsp import compact,entities,entity_bytes
from player_hull import lumps,pack_lumps
from mwad.interior import original_doors
from build_aga import harvest_fingerprint_entries

def pin(raw):return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def section_text(plan):
    sections=plan['sections'];portals=plan['portals'];names=[s['name'] for s in sections]
    if not 2<=len(sections)<=8 or len(set(names))!=len(names) or not 1<=len(portals)<=8:
        raise ValueError('Invalid section/portal count')
    lines=[f'AWIS1 {len(sections)} {len(portals)}']
    for s in sections:
        if not re.fullmatch('[a-z0-9]{1,15}',s['name']):raise ValueError('Invalid section name')
        lo,hi=s['coverage']
        if len(lo)!=3 or len(hi)!=3 or any(not math.isfinite(v) or abs(v)>=32768 for v in lo+hi) or any(lo[k]>=hi[k] for k in range(3)):
            raise ValueError('Invalid section coverage')
        lines.append(s['name']+' '+' '.join(format(v,'.9g') for v in lo+hi))
    seen=set()
    for p in portals:
        a,b=p['from'],p['to'];axis=p['axis'];split=p['split'];margin=p['margin'];lo,hi=p['bounds']
        key=tuple(sorted((a,b)))
        if a not in names or b not in names or a==b or key in seen or axis not in (0,1,2) or not 0<margin<=32 or len(lo)!=3 or len(hi)!=3:
            raise ValueError('Invalid portal binding')
        seen.add(key)
        if not all(math.isfinite(v) for v in [split,margin,*lo,*hi]) or not lo[axis]<split-margin<split+margin<hi[axis]:
            raise ValueError('Invalid hysteresis')
        for name in (a,b):
            low,high=sections[names.index(name)]['coverage']
            if any(not low[k]<=lo[k]<hi[k]<=high[k] for k in range(3)):raise ValueError('Portal outside shared coverage')
        lines.append(f'{a} {b} {axis} '+' '.join(format(v,'.9g') for v in [split,margin,*lo,*hi]))
    return ('\n'.join(lines)+'\n').encode('ascii')

def prepare(plan,base_id1,source_index,master,doors,output):
    """Bound all input receipts; emitted banks remain additive until integration."""
    base_id1=Path(base_id1);output=Path(output)
    if output.exists():raise ValueError('Fresh section output required')
    if pin(master)['sha256']!=plan['master_sha256'] or pin(source_index)['sha256']!=plan['index_sha256']:
        raise ValueError('Source identity mismatch')
    if pin(json.dumps(doors,sort_keys=True,separators=(',',':')).encode())['sha256']!=plan['doors_sha256']:
        raise ValueError('Original transformed door receipt changed')
    source_refs={r['number']:r for r in json.loads(source_index)['references']}
    raw=(base_id1/'maps'/plan['base_map']).read_bytes()
    if pin(raw)!=plan['base']:raise ValueError('Base BSP changed')
    data=lumps(raw);records=entities(data[0]);base_refs={int(e['aw_ref']) for e in records if 'aw_ref' in e}
    if base_refs!=set(source_refs):raise ValueError('Base/reference coverage mismatch')
    sections=plan['sections'];selected=[set(s['references']) for s in sections]
    if len({s['physical_id'] for s in sections})!=len(sections) or any(s['physical_id']<8252 for s in sections):
        raise ValueError('Appended physical IDs required')
    for s in sections:
        if len(s['spawn'])!=3 or not all(math.isfinite(v) and abs(v)<32768 for v in s['spawn']) or not 0<=s['yaw']<360:
            raise ValueError('Invalid section fallback spawn')
    if any(len(s['references'])!=len(k) or not k<=base_refs for s,k in zip(sections,selected)) or set.union(*selected)!=base_refs:
        raise ValueError('Sections must retain the complete original selected union')
    text=section_text(plan)
    # Original door numbers and both directed authored destinations are checked
    # against the source master; no inverse links are inferred.
    originals={(d['source_cell'],d['number']):d for d in original_doors(master)}
    for row in doors['links']:
        original=row['original'];key=(original['source_cell'],row['reference'])
        if key not in originals or originals[key]!=original:raise ValueError('Unbound original directed door')
        if row['target']==plan['logical_map']:
            entrance=next(s for s in sections if s['name']==plan['entrance_section'])
            if row['arrival']!=entrance['spawn'] or row['yaw']!=entrance['yaw']:
                raise ValueError('Original exterior DODT arrival changed')
    output.mkdir(parents=True);id1=output/'id1';(id1/'maps').mkdir(parents=True)
    for asset in sorted(base_id1.rglob('*')):
        if asset.is_file() and asset.suffix!='.bsp' and not asset.name.startswith('harvest-'):
            target=id1/asset.relative_to(base_id1);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(asset,target)
    catalogue=(base_id1/('harvest-'+Path(plan['base_map']).stem+'.txt')).read_bytes()
    rows=[]
    for section,keep in zip(sections,selected):
        chosen=[dict(e) for e in records if 'aw_ref' not in e or int(e['aw_ref']) in keep]
        starts=[e for e in chosen if e.get('classname')=='info_player_start']
        if len(starts)!=1:raise ValueError('Expected one standing spawn')
        starts[0]['origin']=' '.join(format(v,'.9g') for v in section['spawn'])
        starts[0]['angle']=format(section['yaw'],'.9g')
        candidate,proof=compact(raw,chosen)
        target=id1/'maps'/(section['name']+'.bsp');target.write_bytes(candidate)
        (id1/('harvest-'+section['name']+'.txt')).write_bytes(catalogue)
        rows.append(dict(name=section['name'],physical_id=section['physical_id'],logical_id=plan['logical_id'],
                         references=sorted(keep),bsp=pin(candidate),compaction=proof))
    (id1/'interior-sections.txt').write_bytes(text)
    banks={s['name']:[] for s in sections};links=[]
    for row in doors['links']:
        entry=dict(row)
        if row['target']==plan['logical_map']:entry['target']=plan['entrance_section']
        if row['source']==plan['logical_map']:
            owners=[s['name'] for s,k in zip(sections,selected) if row['reference'] in k]
            if not owners:raise ValueError('Original exit missing from all sections')
        else:owners=[row['source']]
        for owner in owners:
            line=dict(entry,source=owner);banks.setdefault(owner,[]).append(line);links.append(line)
    for source,bank in banks.items():
        text='AWD3\n'
        for row in bank:
            values=[*row['mins'],*row['maxs'],*row['arrival'],row['yaw']]
            text+=f"{source} {row['target']} {row['reference']} "+' '.join(format(v,'.9g') for v in values)+'\t'+row['label']+'\n'
        (id1/('doors-'+source+'.txt')).write_text(text)
    fingerprints=harvest_fingerprint_entries(id1,plant_capacity=256)
    manifest=dict(format='AmiWind interior sections candidate 1',cell=plan['cell'],master_sha256=plan['master_sha256'],
                  logical_id=plan['logical_id'],sections=rows,union_references=sorted(base_refs),
                  original_door_links=links,harvest_bindings=fingerprints,
                  files=[dict(path=p.relative_to(id1).as_posix(),**pin(p.read_bytes())) for p in sorted(id1.rglob('*')) if p.is_file()],
                  external_dependencies=plan['external_dependencies'],
                  bank_installation='merge/add only; existing bank conflicts must fail before integration',
                  visibility_boundary='pending 3D/native certification',native_acceptance='not_run')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('plan','base-id1','source-index','master','doors','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();result=prepare(json.loads(a.plan.read_text()),a.base_id1,a.source_index.read_bytes(),a.master.read_bytes(),json.loads(a.doors.read_text()),a.out)
    print(json.dumps({k:result[k] for k in ('format','cell','logical_id','native_acceptance')},indent=2))
if __name__=='__main__':main()
