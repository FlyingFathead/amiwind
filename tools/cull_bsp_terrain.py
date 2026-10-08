#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Apply host-side terrain visual culling to a fresh private BSP candidate."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import struct
import numpy as np
from terrain_visual_cull import ground_from_bsp,cull_surfaces,resolve_policy,IntersectedTerrainVolume
from player_hull import lumps,pack_lumps
from compact_bsp import entities,compact
from replace_bsp_world import verify_collision,rows


def cull_bsp(raw,policy, *, terrain_reference=None, terrain_reference_metadata=None, canonical_land_source=None, canonical_origin=None, require_canonical=True):
    if not policy['enabled']:return raw,{'policy':policy,'unchanged':True,'disabled':True}
    if canonical_land_source is not None:
        if canonical_origin is None:raise ValueError('Explicit compiled canonical origin XYZ is required')
        from canonical_land_reference import CanonicalLand
        from canonical_bsp_cull import cull_bsp as canonical_cull
        land=CanonicalLand(canonical_land_source,canonical_origin)
        return canonical_cull(raw,land,policy)
    if require_canonical:raise ValueError('Enabled exterior culling requires direct canonical LAND NPZ; compiled BSP proxy is not accepted')
    data=lumps(raw);terrain,terrain_policy=ground_from_bsp(raw if terrain_reference is None else terrain_reference,overlap=policy['overlap'])
    if terrain_reference is not None:
        local,local_receipt=ground_from_bsp(raw,overlap=policy['overlap'])
        terrain=IntersectedTerrainVolume(local,terrain)
        terrain_policy['rendered_local_guard']=local_receipt
        terrain_policy['envelope']='Intersection: below both authoritative global reference and actual rendered local LAND'
    terrain_policy['reference'] = terrain_reference_metadata or {'scope':'local BSP fallback','sha256':hashlib.sha256(raw if terrain_reference is None else terrain_reference).hexdigest()}
    if not terrain.prisms:return raw,{'policy':policy,'terrain':terrain_policy,'unchanged':True,'no_verified_land':True}
    formats={3:'<3f',7:'<HhihH4Bi',12:'<HH',13:'<i',14:'<9f7i'}
    r={i:[list(v) for v in struct.iter_unpack(fmt,data[i])] for i,fmt in formats.items()}
    groups=collections.defaultdict(list)
    for e in entities(data[0]):
     if e.get('model','').startswith('*'):
      model=int(e['model'][1:]);angles=list(map(float,e.get('angles','0 0 0').split()));assert angles[0]==angles[2]==0
      groups[tuple(r[14][model][14:16])].append((model,np.array(list(map(float,e.get('origin','0 0 0').split()))),angles[1],e.get('aw_ref')))
    originalfaces=r[7]
    world_first,world_count=r[14][0][14:16]
    if world_first!=0:raise ValueError('Expected leading world face range')
    for node in struct.iter_unpack('<i2h6h2H',data[5]):
     if node[10] and node[9]+node[10]>world_count:raise ValueError('Unsupported inline render-node face range')
    newfaces=list(originalfaces[:r[14][0][15]]);reports=[]
    for (first,count),placements in groups.items():
     surfaces=[]
     for face in originalfaces[first:first+count]:
      start,n=face[2:4];q=np.array([r[3][r[12][abs(r[13][i][0])][0 if r[13][i][0]>=0 else 1]] for i in range(start,start+n)])
      normal=np.cross(q[1]-q[0],q[2]-q[0]);normal/=np.linalg.norm(normal)
      surfaces.append((q,normal,None,None,0,None if face[-1]<0 else b'lightmapped'))
     kept,receipt=cull_surfaces(surfaces,terrain,[(o,yaw) for model,o,yaw,ref in placements]);receipt.update(models=[m for m,o,yaw,ref in placements],references=[ref for m,o,yaw,ref in placements]);reports.append(receipt)
     # Map metadata from retained surface identity or original affine normal. Modified
     # polys preserve face plane/texinfo/light metadata selected by source slot.
     newfirst=len(newfaces)
     it=iter(kept);nextsurface=next(it,None)
     for surface,face in zip(surfaces,originalfaces[first:first+count]):
      if nextsurface is None:break
      # cull returns unchanged objects or one clipped polygon with same n object.
      if nextsurface[1] is not surface[1]:continue
      q=nextsurface[0];record=list(face)
      if nextsurface is not surface:
       ids=[]
       for p in q:ids.append(len(r[3]));r[3].append(list(p))
       record[2]=len(r[13]);record[3]=len(ids)
       for a,b in zip(ids,ids[1:]+ids[:1]):
        edge=len(r[12]);r[12].append([a,b]);r[13].append([edge])
      newfaces.append(record);nextsurface=next(it,None)
     for model,o,yaw,ref in placements:r[14][model][14:16]=[newfirst,len(kept)]
    r[7]=newfaces
    for i,fmt in formats.items():data[i]=bytearray().join(struct.pack(fmt,*row) for row in r[i])
    # World unchanged and no stock inline render-node faces; collision tree ranges
    # have zero rendering faces in this converter. Retain trees exactly before compact.
    assert data[5]==lumps(raw)[5] and data[9]==lumps(raw)[9]
    if all(x.get('fully_buried_removed',0)==0 and x.get('crossing_clipped',0)==0 for x in reports):
     return raw,{'policy':policy,'terrain':terrain_policy,'models':reports,'unchanged':True}
    candidate,compact_receipt=compact(pack_lumps(data))
    # Verify semantic original collision for every entity by stable reference.
    a=lumps(raw);b=lumps(candidate);old={e['aw_ref']:int(e['model'][1:]) for e in entities(a[0]) if 'aw_ref' in e and e.get('model','').startswith('*')};new={e['aw_ref']:int(e['model'][1:]) for e in entities(b[0]) if 'aw_ref' in e and e.get('model','').startswith('*')}
    parsed=(rows(a),rows(b))
    for ref,m in old.items():
     for hull in range(4):verify_collision(a,b,m,new[ref],hull,parsed=parsed)
    receipt={'policy':policy,'terrain':terrain_policy,'models':reports,'source_sha256':hashlib.sha256(raw).hexdigest(),
             'candidate_sha256':hashlib.sha256(candidate).hexdigest(),'collision_semantic_checks':len(old)*4,
             'original_bytes':len(raw),'candidate_bytes':len(candidate),'net_file_bytes_saved':len(raw)-len(candidate),
             'original_stored_faces':len(originalfaces),'candidate_stored_faces':len(b[7])//20,
             'compaction':compact_receipt,'status':'Candidate; target-loader/heap acceptance remains required'}
    return candidate,receipt


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--terrain-visual-cull',choices=('true','false'))
    p.add_argument('--terrain-cull-overlap',type=float)
    p.add_argument('--terrain-cull-config',type=Path,default=Path(__file__).resolve().parents[1]/'config/terrain-visual-cull.json')
    p.add_argument('--terrain-reference-bsp',type=Path,help='Complete unculled authoritative terrain in the same compiled coordinates')
    p.add_argument('--canonical-land-source',type=Path,help='Authoritative source LAND NPZ, required when enabled')
    p.add_argument('--canonical-origin',type=float,nargs=3,metavar=('X','Y','Z'),help='source XYZ * 0.25 minus this compiled origin')
    p.add_argument('--map-identity');p.add_argument('--cell-identity');p.add_argument('--subcell-identity')
    a=p.parse_args()
    if a.out.exists():p.error('Fresh output required; input is never overwritten')
    policy=resolve_policy(json.loads(a.terrain_cull_config.read_text(encoding='utf-8')),
                          map_identity=a.map_identity or a.source.stem,cell_identity=a.cell_identity,subcell_identity=a.subcell_identity,
                          force=None if a.terrain_visual_cull is None else a.terrain_visual_cull=='true',overlap_force=a.terrain_cull_overlap)
    reference=None if a.terrain_reference_bsp is None else a.terrain_reference_bsp.read_bytes()
    metadata=None if reference is None else {'scope':'explicit global terrain reference','path':str(a.terrain_reference_bsp),'sha256':hashlib.sha256(reference).hexdigest()}
    candidate,receipt=cull_bsp(a.source.read_bytes(),policy,terrain_reference=reference,terrain_reference_metadata=metadata,canonical_land_source=a.canonical_land_source,canonical_origin=a.canonical_origin,require_canonical=True)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes(candidate)
    a.out.with_suffix('.terrain-cull.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt))

if __name__=='__main__':main()
