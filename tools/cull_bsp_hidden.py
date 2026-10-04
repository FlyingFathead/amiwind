# SPDX-License-Identifier: GPL-3.0-only
"""Remove only whole static BSP faces proven inside existing opaque closed shells.

A conservative serialized exterior diagnostic, not comprehensive visibility.
Open/unknown shells are retained. Original collision and PVS remain independent.
"""
import collections,hashlib,struct
import numpy as np
from player_hull import lumps,pack_lumps
from replace_bsp_world import rows,FORMATS,texture_blobs,verify_collision
from compact_bsp import compact,entities,entity_bytes
from canonical_world_cull import retain_sky_textures


def cull_bsp(raw, *, enabled=True, scene_kind='exterior'):
    if type(enabled) is not bool:raise ValueError('hidden-surface flag must be boolean')
    if scene_kind not in ('exterior','interior'):raise ValueError('Explicit scene kind required')
    if not enabled or scene_kind=='interior':
        return raw,{'enabled':enabled,'scene_kind':scene_kind,'unchanged':True,'byte_identical':True,'stored_faces_before':len(lumps(raw)[7])//20,'stored_faces_after':len(lumps(raw)[7])//20,'removed_face_ids':[]}
    from exterior_visibility import auto_cull_hidden_surfaces
    data=lumps(raw);original=rows(data);r=rows(data);records=entities(data[0])
    if not records:raise ValueError('Worldspawn missing')
    blobs=texture_blobs(data[2]);materials=[]
    for info in r[6]:
        blob=blobs[info[8]];name='' if blob is None else blob[:16].split(b'\0')[0].decode('ascii')
        opaque=bool(name) and not name.startswith(('*','sky','{'))
        materials.append({'alpha':1.0 if opaque else 0.0,'texture_index':info[8],
                          'texture_alpha_opaque':opaque,'vertex_alpha_opaque':True,'runtime_texture':name})
    pool=None;poolfirst=poolcount=0
    if 'aw_render_pool' in records[0]:
        text=records[0]['aw_render_pool']
        if not text.startswith('*') or not text[1:].isdigit():raise ValueError('Invalid render pool')
        pool=int(text[1:]);poolfirst,poolcount=r[14][pool][14:16]
    def model_faces(model):
        first,count=r[14][model][14:16]
        return list(range(first,first+count))
    def ranges(entity):
        output=[]
        for text in entity.get('aw_render_ranges','').split(','):
            if not text:continue
            if pool is None:raise ValueError('Range without render pool')
            fields=text.split(':')
            if len(fields)!=2 or any(not x.isdigit() for x in fields):raise ValueError('Invalid render range')
            start,count=map(int,fields)
            if count<=0 or start+count>poolcount:raise ValueError('Render range outside pool')
            output.append((start,count))
        return output
    def placement_faces(entity):
        model=int(entity['model'][1:]);ids=model_faces(model)
        for start,count in ranges(entity):ids.extend(range(poolfirst+start,poolfirst+start+count))
        return tuple(dict.fromkeys(ids))
    protected=set(model_faces(0));protected_models={0};static=[];unsupported=[]
    for entity in records:
        if not entity.get('model','').startswith('*'):continue
        model=int(entity['model'][1:]);ids=placement_faces(entity)
        if entity.get('classname')=='func_wall':static.append((entity,ids))
        else:
            protected.update(ids);protected_models.add(model)
            unsupported.append({'classname':entity.get('classname'),'model':model,'reference':entity.get('aw_ref'),'reason':'not converter static exterior func_wall'})
    # Models lacking a placement are not an authorization to remove their faces.
    referenced={int(e['model'][1:]) for e in records if e.get('model','').startswith('*')}
    for model in range(1,len(r[14])):
        if model not in referenced and model!=pool:protected.update(model_faces(model));protected_models.add(model)
    proof_cache={};votes=collections.defaultdict(list);audits=[]
    vertices=np.asarray(r[3],dtype=float)
    for entity,ids in static:
        if ids not in proof_cache:
            triangles=[];owners=[]
            for fid in ids:
                face=r[7][fid];vids=[r[12][abs(r[13][i][0])][0 if r[13][i][0]>=0 else 1] for i in range(face[2],face[2]+face[3])]
                if len(vids)<3:raise ValueError('Invalid static polygon')
                q=vertices[vids];normal=np.asarray(r[1][face[0]][:3])*(1 if not face[1] else -1)
                fan=sum((np.cross(q[i]-q[0],q[i+1]-q[0]) for i in range(1,len(q)-1)),np.zeros(3))
                if fan@normal<0:vids.reverse()
                for i in range(1,len(vids)-1):triangles.append([vids[0],vids[i],vids[i+1],face[4]]);owners.append(fid)
            used=sorted({v for tri in triangles for v in tri[:3]});remap={v:i for i,v in enumerate(used)}
            local=np.asarray([[remap[v] for v in tri[:3]]+[tri[3]] for tri in triangles],dtype=np.int64).reshape((-1,4))
            kept,audit=auto_cull_hidden_surfaces(vertices[used],local,materials,enabled=True,scene_kind='exterior')
            removed=set(audit.get('removed_face_ids',[]));indices=collections.defaultdict(list)
            for i,fid in enumerate(owners):indices[fid].append(i)
            fully={fid for fid,tri in indices.items() if all(i in removed for i in tri)}
            proof_cache[ids]=(fully,audit)
        fully,audit=proof_cache[ids]
        for fid in ids:votes[fid].append(fid in fully)
        audits.append({'reference':entity.get('aw_ref'),'model':entity['model'],'input_stored_faces':len(ids),'proven_hidden_polygons':len(fully),'geometry_key':hashlib.sha256(str(ids).encode()).hexdigest()})
    remove={fid for fid,checks in votes.items() if all(checks)}-protected
    base_receipt={'enabled':True,'scene_kind':scene_kind,'stored_faces_before':len(r[7]),'removed_face_ids':sorted(remove),'static_placements':len(static),'unique_geometry_proofs':len(proof_cache),'placements':audits,'proofs':[audit for fully,audit in proof_cache.values()],'unsupported_static_cases':unsupported,'scope':'Only whole polygons strictly inside certified existing opaque convex closed components for every range user. Open interiors and unknown opacity remain; not complete hidden-surface removal.'}
    if not remove:return raw,{**base_receipt,'stored_faces_after':len(r[7]),'unchanged':True,'byte_identical':True,'status':'NO PROVEN CUTS; not a fixed map'}
    prefix=[0]
    for fid in range(len(r[7])):prefix.append(prefix[-1]+int(fid not in remove))
    def span(first,count):return [prefix[first],prefix[first+count]-prefix[first]]
    for node in r[5]:node[9:11]=span(*node[9:11])
    for model in r[14]:model[14:16]=span(*model[14:16])
    marks=[]
    for leaf in r[10]:
        first,count=leaf[8:10];selected=[prefix[r[11][i][0]] for i in range(first,first+count) if r[11][i][0] not in remove]
        leaf[8:10]=[len(marks),len(selected)];marks.extend([fid] for fid in selected)
    r[11]=marks;r[7]=[face for fid,face in enumerate(r[7]) if fid not in remove]
    for entity in records:
        if 'aw_render_ranges' not in entity:continue
        rebuilt=[]
        for start,count in ranges(entity):
            first,n=span(poolfirst+start,count)
            if n:rebuilt.append(str(first-prefix[poolfirst])+':'+str(n))
        if rebuilt:entity['aw_render_ranges']=','.join(rebuilt)
        else:entity.pop('aw_render_ranges')
    data[0]=bytearray(entity_bytes(records))
    for i,fmt in FORMATS.items():data[i]=bytearray().join(struct.pack(fmt,*row) for row in r[i])
    candidate,compaction=compact(pack_lumps(data));target=lumps(candidate)
    target[2],added=retain_sky_textures(target[2],lumps(raw)[2]);candidate=pack_lumps(target)
    after=rows(target);pair=(original,after)
    for new,old in enumerate(compaction['retained_models']):
        for hull in range(4):verify_collision(lumps(raw),target,old,new,hull,parsed=pair)
    if target[4]!=lumps(raw)[4]:raise ValueError('PVS changed')
    return candidate,{**base_receipt,'stored_faces_after':len(after[7]),'original_bytes':len(raw),'candidate_bytes':len(candidate),'collision_checks':len(compaction['retained_models'])*4,'PVS_exact':True,'compaction':compaction,'acceptance':'DIAGNOSTIC: proof-based removals only; full interiors, canonical terrain/collision alignment, memory and target appearance remain gates'}
