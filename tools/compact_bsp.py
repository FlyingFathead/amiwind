# SPDX-License-Identifier: GPL-3.0-only
"""Compact selected BSP29 models without changing retained geometry or hulls.

World leaves and visibility bytes retain their original indices. Unreferenced
brush geometry, collision nodes, planes, textures and vertices are removed.
No mesh simplification, scale conversion or collision rebaking is performed.
"""
import re
import struct
from player_hull import lumps, pack_lumps


def entities(data):
    return [dict(re.findall(r'"([^"\n]*)"\s+"([^"\n]*)"', block))
            for block in re.findall(r'\{[^{}]*\}', bytes(data).decode('ascii').rstrip('\0'))]


def entity_bytes(records):
    return ('\n'.join('{\n'+'\n'.join('"'+k+'" "'+v+'"' for k,v in e.items())+'\n}'
                      for e in records)+'\n\0').encode('ascii')


def compact(raw, records=None, prune_world=False, visual_bounds=None):
    data=lumps(raw)
    if records is None: records=entities(data[0])
    records=[dict(e) for e in records]
    formats={1:'<4fi',3:'<3f',5:'<i2h6h2H',6:'<8f2i',7:'<HhihH4Bi',
             9:'<iHH',10:'<ii6h2H4B',11:'<H',12:'<HH',13:'<i',14:'<9f7i'}
    src={i:[list(r) for r in struct.iter_unpack(fmt,data[i])] for i,fmt in formats.items()}
    kept={0}
    pool_text=records[0].get('aw_render_pool') if records else None
    pool_model=None
    if pool_text is not None:
        if not re.fullmatch(r'\*\d+',pool_text):raise ValueError('Invalid auxiliary render pool')
        pool_model=int(pool_text[1:]);kept.add(pool_model)
    for e in records:
        if e.get('model','').startswith('*'): kept.add(int(e['model'][1:]))
    if not kept or min(kept)<0 or max(kept)>=len(src[14]): raise ValueError('Invalid brush model')
    models=sorted(kept); remap_model={n:i for i,n in enumerate(models)}
    def closure(roots,index,terminal):
        found=set(); stack=list(roots)
        while stack:
            n=stack.pop()
            if terminal(n) or n in found: continue
            if n<0 or n>=len(src[index]): raise ValueError('Invalid BSP tree child')
            found.add(n);stack.extend(src[index][n][1:3])
        return sorted(found)
    nodes=closure((src[14][m][9] for m in models),5,lambda n:n<0)
    clips=closure((src[14][m][h] for m in models for h in (10,11,12)),9,lambda n:n<0 or n>=65520)
    faces=set()
    for m in models:
        first,count=src[14][m][14:16];faces.update(range(first,first+count))
    # Node face ranges and leaf marks are world geometry; these remain intact.
    for n in nodes:
        first,count=src[5][n][9:11];faces.update(range(first,first+count))
    world_first,world_count=src[14][0][14:16]
    if prune_world:
        visible={m[0] for m in src[11]}
        faces={f for f in faces if not world_first<=f<world_first+world_count or f in visible}
    # Keep complete polygons that intersect the certified visible coverage.
    # Inline brush models can span well beyond a region; selecting the whole
    # model need not retain its distant visual faces. Collision trees stay intact.
    visual_removed=0
    if visual_bounds is not None:
        from audit_walkability import axes
        import math
        low,high=visual_bounds
        if len(low)!=2 or len(high)!=2 or not all(math.isfinite(v) for v in (*low,*high)) or any(low[i]>=high[i] for i in range(2)):
            raise ValueError('Expected finite nonempty XY visual bounds')
        placements={m:[] for m in models if m}
        for e in records:
            if e.get('model','').startswith('*'):
                m=int(e['model'][1:])
                if not m or m==pool_model:continue
                origin=tuple(map(float,e.get('origin','0 0 0').split()))
                angles=tuple(map(float,e.get('angles','0 0 0').split()))
                if len(origin)!=3 or len(angles)!=3 or not all(math.isfinite(v) for v in (*origin,*angles)):
                    raise ValueError('Invalid visual placement')
                placements[m].append((origin,axes(angles)))
        tested=set();visible_faces=set()
        for m in models:
            if not m or m==pool_model:continue
            first,count=src[14][m][14:16]
            for f in range(first,first+count):
                if f not in faces:continue
                tested.add(f)
                face=src[7][f];points=[]
                for se in src[13][face[2]:face[2]+face[3]]:
                    edge=src[12][abs(se[0])]
                    points.append(src[3][edge[0 if se[0]>=0 else 1]])
                visible=False
                for origin,basis in placements[m]:
                    world=[[origin[i]+sum(v[j]*basis[j][i] for j in range(3)) for i in range(2)] for v in points]
                    if world and all(max(v[i] for v in world)>=low[i] and min(v[i] for v in world)<=high[i] for i in range(2)):
                        visible=True;break
                if visible:visible_faces.add(f)
        # Aliased models may share a face range. Keep a face if ANY retained
        # placement needs it; never prune a marked world face through an alias.
        remove=tested-visible_faces-set(range(world_first,world_first+world_count))
        faces-=remove;visual_removed=len(remove)
    faces=sorted(faces)
    def mapping(values):return {v:i for i,v in enumerate(values)}
    nf=mapping(faces); nn=mapping(nodes); nc=mapping(clips)
    def face_range(first,count):
        selected=[f for f in range(first,first+count) if f in nf]
        return [nf[selected[0]],len(selected)] if selected else [0,0]
    planes=sorted({src[7][f][0] for f in faces}|{src[5][n][0] for n in nodes}|{src[9][c][0] for c in clips})
    np=mapping(planes)
    texinfo=sorted({src[7][f][4] for f in faces});nt=mapping(texinfo)
    texture_ids=sorted({src[6][t][8] for t in texinfo});nx=mapping(texture_ids)
    surfedges=sorted({s for f in faces for s in range(src[7][f][2],src[7][f][2]+src[7][f][3])});ns=mapping(surfedges)
    # Keep index zero reserved: a reversed edge must never become negative zero.
    edges=sorted({0}|{abs(src[13][s][0]) for s in surfedges});ne=mapping(edges)
    vertices=sorted({v for e in edges for v in src[12][e]});nv=mapping(vertices)
    out=[bytearray(b) for b in data]
    def emit(index, rows):out[index]=bytearray().join(struct.pack(formats[index],*r) for r in rows)
    emit(1,(src[1][p] for p in planes));emit(3,(src[3][v] for v in vertices))
    emit(12,([nv[v] for v in src[12][e]] for e in edges))
    emit(13,([(-1 if src[13][s][0]<0 else 1)*ne[abs(src[13][s][0])]] for s in surfedges))
    emit(6,(src[6][t][:8]+[nx[src[6][t][8]],src[6][t][9]] for t in texinfo))
    emit(7,([np[src[7][f][0]],src[7][f][1],ns[src[7][f][2]] if src[7][f][3] else 0,
             src[7][f][3],nt[src[7][f][4]]]+src[7][f][5:] for f in faces))
    emit(5,([np[src[5][n][0]]]+[nn[c] if c>=0 else c for c in src[5][n][1:3]]+
            src[5][n][3:9]+face_range(*src[5][n][9:11]) for n in nodes))
    emit(9,([np[src[9][c][0]]]+[nc[ch] if ch<65520 else ch for ch in src[9][c][1:3]] for c in clips))
    leaves=[];marks=[]
    for leaf in src[10]:
        row=list(leaf);first,count=row[8:10];row[8]=len(marks)
        selected=[nf[src[11][m][0]] for m in range(first,first+count) if src[11][m][0] in nf]
        row[9]=len(selected);marks.extend([f] for f in selected);leaves.append(row)
    emit(10,leaves);emit(11,marks)
    rebuilt=[]
    for m in models:
        row=list(src[14][m]);row[9]=nn[row[9]] if row[9]>=0 else row[9]
        for h in (10,11,12):row[h]=nc[row[h]] if row[h]>=0 else row[h]
        row[14:16]=face_range(*row[14:16]);rebuilt.append(row)
    emit(14,rebuilt)
    for e in records:
        if e.get('model','').startswith('*'):e['model']='*'+str(remap_model[int(e['model'][1:])])
    if pool_model is not None:records[0]['aw_render_pool']='*'+str(remap_model[pool_model])
    out[0]=bytearray(entity_bytes(records))
    total=struct.unpack_from('<i',data[2])[0]
    offsets=list(struct.unpack_from('<'+str(total)+'i',data[2],4))
    if any(t<0 or t>=total for t in texture_ids):raise ValueError('Invalid texture index')
    valid=sorted(set(o for o in offsets if o>=0)); ends={o:(valid[i+1] if i+1<len(valid) else len(data[2])) for i,o in enumerate(valid)}
    texture=bytearray(struct.pack('<i',len(texture_ids))+bytes(4*len(texture_ids)))
    for i,t in enumerate(texture_ids):
        offset=offsets[t]
        struct.pack_into('<i',texture,4+i*4,len(texture) if offset>=0 else -1)
        if offset>=0:texture+=data[2][offset:ends[offset]]
    out[2]=texture
    result=pack_lumps(out)
    report={'bytes_before':len(raw),'bytes_after':len(result),'models_before':len(src[14]),'models_after':len(models),
            'faces_before':len(src[7]),'faces_after':len(faces),'clipnodes_before':len(src[9]),'clipnodes_after':len(clips),
            'visual_faces_removed_outside_coverage':visual_removed,'visual_bounds':visual_bounds,
            'world_collision':'unchanged','world_visibility':'PVS unchanged; unmarked faces pruned' if prune_world else 'unchanged','retained_models':models}
    return result,report
