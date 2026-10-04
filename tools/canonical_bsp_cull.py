# SPDX-License-Identifier: GPL-3.0-only
"""Canonical source-based host BSP visual culling with deduplicated render ranges.

Collision and PVS remain original. Returned candidate is not acceptance: terrain
render/physical alignment, serialized geometry and target budget need separate gates.
"""
from pathlib import Path
import sys,struct,json,hashlib,math,collections,time
import numpy as np
from canonical_land_reference import CanonicalLand
from canonical_face_clip import CanonicalClipper
from player_hull import lumps,pack_lumps
from compact_bsp import compact,entities,entity_bytes
from replace_bsp_world import rows,FORMATS,verify_collision
from canonical_world_cull import retain_sky_textures, cull_world_render

def _quantize_polygon(p):
    p=np.asarray(p,dtype='<f4').astype(float);keep=[]
    for point in p:
        if not keep or not np.array_equal(point,keep[-1]):keep.append(point)
    if len(keep)>1 and np.array_equal(keep[0],keep[-1]):keep.pop()
    if len(keep)<3:return None
    p=np.array(keep)
    if sum(np.linalg.norm(np.cross(p[i]-p[0],p[i+1]-p[0])) for i in range(1,len(p)-1))==0:return None
    return p

def _stable_local_parts(parts,source,origin,rotation,clip):
    """Validate the geometry actually stored, after local float32 rounding.

    A yawed placement can round across a LAND tile/contact boundary while
    converting a world-space cut back to local BSP vertices. Recut those
    serialized vertices against the same canonical surface and policy. Never
    enlarge the tolerance or silently accept a nonconverging fragment.
    """
    world=source@rotation.T+origin
    if len(parts)==1 and np.array_equal(parts[0],world):return [source],0,0,0
    pending=[(p,0) for p in reversed(parts)];stable=[];recuts=maximum_depth=zeros=0
    while pending:
        part,depth=pending.pop();p=_quantize_polygon((part-origin)@rotation)
        maximum_depth=max(maximum_depth,depth)
        if p is None:zeros+=1;continue
        serialized=p@rotation.T+origin;following=clip.clip(serialized)
        if len(following)==1 and np.array_equal(following[0],serialized):
            stable.append(p);continue
        if depth>=8:raise ValueError('Serialized placement fragment is not repeat-stable')
        recuts+=1;pending.extend((q,depth+1) for q in reversed(following))
    return stable,recuts,maximum_depth,zeros

def cull_bsp(raw,land,policy,progress=None):
    if not policy["enabled"]:return raw,{"policy":policy,"unchanged":True}
    if progress is None:progress=lambda value:None
    data=lumps(raw);r=rows(data);original=rows(data);records=entities(data[0]);clip=CanonicalClipper(land,policy["overlap"],boundary_tolerance=policy.get('boundary_tolerance',0.0))
    if records and 'aw_render_pool' in records[0]:raise ValueError('An original unculled seed is required; existing render pool cannot be recut')
    oldfaces=r[7];newfaces=list(oldfaces[:r[14][0][15]]);groups=collections.defaultdict(list)
    counts=collections.Counter();originalmodels=len(r[14]);vertices={tuple(v):i for i,v in enumerate(r[3])}
    for e in records:
        if e.get('model','').startswith('*') and e.get('classname')=='func_wall':
            # Converter static exterior props only. Moving func_door/func_train
            # brushes retain their original visual model and collision.
            m=int(e['model'][1:]);groups[tuple(r[14][m][14:16])].append((m,e))
    def poly(f):return np.array([r[3][r[12][abs(r[13][i][0])][0 if r[13][i][0]>=0 else 1]] for i in range(f[2],f[2]+f[3])])
    def emit(fid,p):
        f=list(oldfaces[fid]);q=poly(f);ids=[]
        if np.array_equal(p,q):newfaces.append(f);return
        n=sum((np.cross(q[i]-q[0],q[i+1]-q[0]) for i in range(1,len(q)-1)),np.zeros(3))
        vector=sum((np.cross(p[i]-p[0],p[i+1]-p[0]) for i in range(1,len(p)-1)),np.zeros(3))
        if vector@n<0:p=p[::-1]
        for point in p:
            key=tuple(point)
            if key not in vertices:vertices[key]=len(r[3]);r[3].append(list(point))
            ids.append(vertices[key])
        if max(ids)>65535:raise ValueError('BSP29 vertex overflow')
        f[2:4]=[len(r[13]),len(ids)]
        for a,b in zip(ids,ids[1:]+ids[:1]):edge=len(r[12]);r[12].append([a,b]);r[13].append([edge])
        if f[-1]>=0:
            info=np.array(r[6][f[4]][:8]).reshape(2,4)
            def extent(points):
                uv=points@info[:,:3].T+info[:,3]
                low=np.floor(uv.min(axis=0)/16).astype(int);high=np.ceil(uv.max(axis=0)/16).astype(int)
                return low,high-low+1
            oldlow,oldsize=extent(q);newlow,newsize=extent(p);offset=newlow-oldlow
            if np.any(offset<0) or np.any(offset+newsize>oldsize):raise ValueError('Lightmap crop exceeds original extent')
            styles=sum(s!=255 for s in f[5:9]);oldoffset=f[-1];f[-1]=len(data[8])
            for style in range(styles):
                start=oldoffset+style*int(np.prod(oldsize));block=np.frombuffer(data[8][start:start+int(np.prod(oldsize))],dtype=np.uint8).reshape(oldsize[1],oldsize[0])
                data[8].extend(block[offset[1]:offset[1]+newsize[1],offset[0]:offset[0]+newsize[0]].tobytes())
            counts['lightmapped_fragments_cropped']+=1
        newfaces.append(f)
    deltas=[]
    for groupnumber,((first,count),placements) in enumerate(groups.items()):
        batches=collections.defaultdict(list);common=[]
        for fid in range(first,first+count):
            q=poly(oldfaces[fid]);results=[]
            for m,e in placements:
                origin=np.array(list(map(float,e.get('origin','0 0 0').split())));angles=list(map(float,e.get('angles','0 0 0').split()))
                if angles[0]!=0 or angles[2]!=0:raise ValueError('Unsupported pitch/roll placement')
                theta=math.radians(angles[1]);rotation=np.array([[math.cos(theta),-math.sin(theta),0],[math.sin(theta),math.cos(theta),0],[0,0,1.]])
                world=q@rotation.T+origin;parts=clip.clip(world)
                local,recuts,depth,zeros=_stable_local_parts(parts,q,origin,rotation,clip)
                counts['post_float32_reclips']+=recuts
                counts['maximum_post_float32_reclip_depth']=max(counts['maximum_post_float32_reclip_depth'],depth)
                counts['post_float32_zero_fragments_removed']+=zeros
                results.append(local);counts['placed_faces_processed']+=1
                if not local:counts['placed_fully_buried_removed']+=1
                elif len(local)!=1 or not np.array_equal(local[0],q):counts['placed_crossing_or_subdivided']+=1
            keys=[tuple(p.astype('<f4').tobytes() for p in parts) for parts in results]
            if all(k==keys[0] for k in keys):common.extend((fid,p) for p in results[0])
            else:
                variants=collections.defaultdict(list)
                for index,key in enumerate(keys):variants[key].append(index)
                for key,users in variants.items():
                    if key:batches[tuple(users)].extend((fid,p) for p in results[users[0]])
        newfirst=len(newfaces)
        for fid,p in common:emit(fid,p)
        for m,e in placements:r[14][m][14:16]=[newfirst,len(common)]
        for users,parts in batches.items():deltas.append((parts,[placements[i] for i in users]))
        progress({'groups_completed':groupnumber+1,'groups_total':len(groups),'counts':dict(counts),'common_faces':len(newfaces)})
    # Canonical LAND diagnostic model is separate and immutable in this stage.
    for m in range(originalmodels):
        if m==0 or any(m==model for placements in groups.values() for model,e in placements):continue
        first,count=original[14][m][14:16];r[14][m][14:16]=[len(newfaces),count];newfaces.extend(oldfaces[first:first+count])
    poolfirst=len(newfaces);bindings=collections.defaultdict(list)
    for parts,users in deltas:
        first=len(newfaces)
        for fid,p in parts:emit(fid,p)
        for m,e in users:bindings[e['aw_ref']].append((first-poolfirst,len(parts)))
    for e in records:
        if e.get('aw_ref') in bindings:e['aw_render_ranges']=','.join(str(first)+':'+str(count) for first,count in bindings[e['aw_ref']])
    pool=list(original[14][0]);pool[9:13]=[-1,-1,-1,-1];pool[14:16]=[poolfirst,len(newfaces)-poolfirst];poolid=len(r[14]);r[14].append(pool)
    holder={'classname':'info_null','model':'*'+str(poolid),'aw_ref':'temporary_render_pool_holder'}
    r[7]=newfaces;data[0]=bytearray(entity_bytes(records+[holder]))
    for i,fmt in FORMATS.items():data[i]=bytearray().join(struct.pack(fmt,*row) for row in r[i])
    candidate,compaction=compact(pack_lumps(data));target=lumps(candidate)
    finalrecords=[e for e in entities(target[0]) if e.get('aw_ref')!='temporary_render_pool_holder']
    poolindex=compaction['retained_models'].index(poolid)
    finalrecords[0]['aw_render_pool']='*'+str(poolindex);target[0]=bytearray(entity_bytes(finalrecords))
    target[2],sky=retain_sky_textures(target[2],lumps(raw)[2]);candidate=pack_lumps(target)
    a=lumps(raw);b=lumps(candidate);parsed=(rows(a),rows(b))
    for m in range(originalmodels):
        for hull in range(4):verify_collision(a,b,m,m,hull,parsed=parsed)
    candidate,world_receipt=cull_world_render(candidate,land,policy)
    b=lumps(candidate)
    return candidate,{"policy":policy,"world":world_receipt,'canonical':land.metadata(),'counts':dict(counts),'delta_batches':len(deltas),'extra_delta_models':1,'extra_delta_entities':0,'pool_model':poolindex,'pool_faces':pool[15],'bound_placements':len(bindings),'range_records':sum(map(len,bindings.values())),'original_stored_faces':len(oldfaces),'candidate_stored_faces':len(b[7])//20,'original_bytes':len(raw),'candidate_bytes':len(candidate),'collision_checks':originalmodels*4,'compaction':compaction,'acceptance':'INCOMPLETE: original rendered and physical LAND alignment to canonical source, source float32 burial inventory, matching ABI memory and target appearance/loading must pass before packaging'}
