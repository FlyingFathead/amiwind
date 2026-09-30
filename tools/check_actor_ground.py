#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Independent, fail-closed check of packaged initial actor support.

Runs on the host after placement baking. Reads actual BSPs and quantized MDLs;
does not move actors. Only explicitly ground-classified initial states are held
to standing contact. Authored airborne/dead states are reported separately.
"""
import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from actor_grounding import initial_state
from audit_walkability import Scene, axes
from player_hull import lumps


def entities(raw):
    return [dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', block))
            for block in re.findall(r'\{[^{}]*\}', lumps(raw)[0].decode('cp1252'))]


def model_frames(raw):
    """Decode final quantized alias positions; reject unsupported grouped poses."""
    if len(raw)<84:raise ValueError('Truncated actor model')
    h=struct.unpack_from('<4si3f3ff3f8if',raw)
    ns,w,height,nv,nt,nf=h[12:18]
    if h[:2]!=(b'IDPO',6) or not 0<nv<=1999 or not 0<nf<=32 or not 0<ns<=32:
        raise ValueError('Unsupported actor model')
    if not 0<w<=4096 or not 0<height<=480 or not 0<nt<=4096:
        raise ValueError('Invalid actor model counts')
    if not all(math.isfinite(v) for v in h[2:8]) or min(h[2:5])<=0:
        raise ValueError('Invalid actor model transform')
    at=84
    for _ in range(ns):
        if struct.unpack_from('<i',raw,at)[0]:raise ValueError('Grouped skin needs a support decoder')
        at+=4+w*height
    at+=nv*12+nt*16;frames=[]
    for _ in range(nf):
        if struct.unpack_from('<i',raw,at)[0]:raise ValueError('Grouped frame needs a support decoder')
        at+=28;points=[]
        for i in range(nv):
            xyz=struct.unpack_from('<3B',raw,at+i*4)
            points.append(tuple(xyz[k]*h[2+k]+h[5+k] for k in range(3)))
        at+=nv*4;frames.append(points)
    if at!=len(raw):raise ValueError('Actor model length mismatch')
    return frames


def owner(maps, name, point):
    for area,prefix in (('balmora','bm'),('seyda','sn')):
        if name==area or re.fullmatch(prefix+r'\d{3}',name):
            directory=maps.parent/(area+'-regions.txt')
            if not directory.is_file():raise ValueError('Missing owner directory: '+area)
            for line in directory.read_text().splitlines()[1:]:
                v=line.split();x0,y0,x1,y1=map(float,v[1:5])
                if x0<=point[0]<x1 and y0<=point[1]<y1:
                    if not (maps/(v[0]+'.bsp')).is_file():raise ValueError('Missing owner BSP: '+v[0])
                    return v[0]
            raise ValueError('No owning core for actor in '+name)
    return name


def contact_samples(frames, angles, intro=False):
    """Every distinct low rendered vertex in the supported initial idle poses.

    The intro has eight idle poses followed by talk/walk poses. Ordinary resident
    models contain only their idle cycle. Future pose layouts must be declared.
    This tests low mesh contact, not semantic left/right foot IK or all animation.
    """
    if intro:
        if len(frames)!=21:raise ValueError('Unexpected intro pose layout')
        frames=frames[:8]
    elif len(frames)!=8:raise ValueError('Undeclared ground-resident pose layout')
    basis=axes(angles);samples={}
    for fi,points in enumerate(frames):
        low=min(p[2] for p in points)
        # A half-unit band includes the quantized soles without using the
        # collision-box minimum or mistaking a lowered origin for visible feet.
        for p in points:
            if p[2]>low+.5:continue
            world=tuple(sum(p[j]*basis[j][i] for j in range(3)) for i in range(3))
            key=tuple(round(v,5) for v in world)
            samples.setdefault(key,[]).append(fi)
    return samples


def audit(maps):
    maps=Path(maps);rows=[];placements={};errors=[];hashes={};copies=0;owner_seen=set()
    @lru_cache(maxsize=3)
    def scene(name):return Scene((maps/(name+'.bsp')).read_bytes(),hull=0)
    @lru_cache(maxsize=128)
    def poses(name):
        p=Path(name)
        if p.is_absolute() or '..' in p.parts:raise ValueError('Unsafe actor model path')
        raw=(maps.parent/p).read_bytes();hashes[name]=hashlib.sha256(raw).hexdigest()
        return model_frames(raw)
    for path in sorted(maps.glob('*.bsp')):
        map_seen=set()
        raw=path.read_bytes();hashes['maps/'+path.name]=hashlib.sha256(raw).hexdigest()
        for e in entities(raw):
            if e.get('classname') not in ('aw_npc','aw_corpse'):continue
            copies+=1
            row=dict(map=path.stem,reference=e.get('aw_ref'),source_id=e.get('aw_source_id'),
                     name=e.get('netname'),model=e.get('model'))
            try:
                if not row['source_id']:raise ValueError('Missing original actor identity')
                state=initial_state(row['source_id']);row['initial_state']=state
                if int(e.get('aw_ground_mode',-1))!=int(state!='ground'):
                    raise ValueError('Entity support mode disagrees with classified source')
                if (e['classname']=='aw_corpse')!=(state=='authored_dead'):
                    raise ValueError('Death pose/classification mismatch')
                point=tuple(map(float,e['origin'].split()));angles=tuple(map(float,e.get('angles','0 0 0').split()))
                if len(point)!=3 or len(angles)!=3 or not all(map(math.isfinite,point+angles)):
                    raise ValueError('Invalid actor transform')
                target=owner(maps,path.stem,point);row['owner']=target
                identity=e.get('aw_ref') or ('intro:'+e.get('aw_intro_role',''))
                key=(target,identity)
                if identity in map_seen:raise ValueError('Duplicate placed reference inside one scene')
                map_seen.add(identity)
                if path.stem==target:owner_seen.add(key)
                signature=(row['source_id'],row['model'],point,angles,state)
                if key in placements:
                    if signature!=placements[key]:raise ValueError('Overlap copy differs from canonical placement')
                    continue
                placements[key]=signature;row['position']=point
                if state!='ground':row['status']='explicit-exception';rows.append(row);continue
                samples=contact_samples(poses(row['model']),angles,bool(float(e.get('aw_intro_role',0))))
                measured=[];failures=[]
                for local,frames in samples.items():
                    foot=tuple(point[k]+local[k] for k in range(3))
                    hit=scene(target).floor((foot[0],foot[1],foot[2]+2),6)
                    sample=dict(foot=foot,frames=sorted(set(frames)),support_status=hit['status'])
                    if hit['status']=='supported':
                        sample.update(gap=foot[2]-hit['height'],support_reference=hit['reference'])
                        if sample['gap']<-.5 or sample['gap']>1.0:failures.append(sample)
                    else:failures.append(sample)
                    measured.append(sample)
                gaps=[m['gap'] for m in measured if 'gap' in m]
                row.update(status='failed-contact' if failures else 'grounded',sample_count=len(measured),
                           minimum_gap=min(gaps) if gaps else None,maximum_gap=max(gaps) if gaps else None,
                           failures=failures)
                if failures:errors.append(dict(**{k:row[k] for k in ('map','reference','source_id')},error='Initial mesh contact outside support tolerance'))
            except (ValueError,KeyError,OSError,struct.error) as exc:
                row.update(status='invalid',error=str(exc));errors.append(row.copy())
            rows.append(row)
    if not copies:errors.append(dict(error='No actor placements found'))
    for key in placements.keys()-owner_seen:
        errors.append(dict(owner=key[0],reference=key[1],error='Canonical owner omits its actor placement'))
    return dict(format=1,status='failed' if errors else 'passed',placement_copies=copies,
                distinct_placements=len(placements),summary=dict(Counter(r['status'] for r in rows)),
                tolerance={'minimum_gap':-.5,'maximum_gap':1.0,'sole_band':.5},
                scope='Initial ground-resident idle poses, packaged point collision, explicit source classification; no moving platforms, footsteps, IK or future animation proof.',
                rows=rows,errors=errors,payload_sha256=hashes)


def require(maps, output):
    report=audit(maps);Path(output).write_text(json.dumps(report,indent=2)+'\n')
    if report['status']!='passed':raise ValueError(f"Actor placement gate failed: {len(report['errors'])} unresolved cases; see {output}")
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('maps',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();require(a.maps,a.out)


if __name__=='__main__':main()
