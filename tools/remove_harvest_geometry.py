"""Exact-reference removal of verified mushroom instances from a BSP29.

No texture selection, polygon culling, world pruning, collision rebake or LOD.
Callers must first bind refs to the original master and geometry packet. The
original placement key, numeric reference and authored exporter pose are all
required; unsupported entity metadata/render pools fail closed.
"""
import hashlib,math,re,struct
from compact_bsp import compact,entities
from player_hull import lumps
from replace_bsp_world import rows,texture_blobs,verify_collision,verify_inline_rendering


def require(value,message):
    if not value:raise ValueError(message)


def strict_entities(data):
    text=bytes(data).decode('ascii').rstrip('\0');blocks=re.findall(r'\{[^{}]*\}',text)
    require(not re.sub(r'\{[^{}]*\}','',text).strip(),'Unparsed entity bytes')
    result=[]
    for block in blocks:
        pairs=re.findall(r'"([^"\n]*)"\s+"([^"\n]*)"',block)
        require(len(dict(pairs))==len(pairs),'Duplicate entity attribute')
        require(not re.sub(r'"([^"\n]*)"\s+"([^"\n]*)"','',block[1:-1]).strip(),'Unparsed entity attribute')
        result.append(dict(pairs))
    require(result and result[0].get('classname')=='worldspawn','Missing worldspawn')
    require(not any('aw_render_pool' in e or 'aw_render_ranges' in e for e in result),'Render-pool range remapping requires separate support')
    return result


def number_vector(text):
    try:values=list(map(float,text.split()))
    except (ValueError,AttributeError):raise ValueError('Invalid entity pose') from None
    require(len(values)==3 and all(math.isfinite(v) for v in values),'Invalid entity pose')
    return values


def face_signature(data,r,tex,number):
    f=r[7][number];ti=r[6][f[4]];out=[]
    out.append(bytes(data[1][f[0]*20:f[0]*20+20]))
    out.append(struct.pack('<hh',f[1],f[3]))
    for se, in r[13][f[2]:f[2]+f[3]]:
        v=r[12][abs(se)][0 if se>=0 else 1];out.append(bytes(data[3][v*12:v*12+12]))
    out.extend((bytes(data[6][f[4]*40:f[4]*40+32]),struct.pack('<i',ti[9]),
                b'\xffmissing' if tex[ti[8]] is None else tex[ti[8]],struct.pack('<4Bi',*f[5:10])))
    h=hashlib.sha256()
    for v in out:h.update(struct.pack('<I',len(v)));h.update(v)
    return h.digest()


def verify_survivors(source_raw,target_raw,retained_models,removed_indices):
    """Resolve all remapped data; compare world and every surviving model."""
    a,b=lumps(source_raw),lumps(target_raw);ar,br=rows(a),rows(b)
    ae,be=strict_entities(a[0]),strict_entities(b[0]);remap={v:i for i,v in enumerate(retained_models)}
    require(len(br[14])==len(retained_models) and retained_models[0]==0,'Unexpected retained model table')
    expected=[]
    for i,e in enumerate(ae):
        if i in removed_indices:continue
        row=dict(e)
        if row.get('model','').startswith('*'):
            old=int(row['model'][1:]);require(old in remap,'Survivor model missing');row['model']='*'+str(remap[old])
        expected.append(row)
    require(be==expected,'Surviving entity attributes or order changed')
    at,bt=texture_blobs(a[2]),texture_blobs(b[2]);af={};bf={}
    def sig(data,r,tex,cache,n):
        if n not in cache:cache[n]=face_signature(data,r,tex,n)
        return cache[n]
    def sa(n):return sig(a,ar,at,af,n)
    def sb(n):return sig(b,br,bt,bf,n)
    checked=0
    for new,old in enumerate(retained_models):
        am,bm=ar[14][old],br[14][new]
        require(bytes(a[14][old*64:old*64+36])==bytes(b[14][new*64:new*64+36]) and am[13]==bm[13] and am[15]==bm[15],
                'Surviving model bounds/origin/visibility/face count changed')
        require([sa(i) for i in range(am[14],am[14]+am[15])]==[sb(i) for i in range(bm[14],bm[14]+bm[15])],
                'Surviving resolved geometry/UV/material/light changed')
        checked+=am[15]
        for hull in range(4):verify_collision(a,b,old,new,hull,(ar,br))
        # Preserve render-node bounds and ordered face associations as well as
        # the collision planes/contents checked by the paired hull comparator.
        stack=[(am[9],bm[9])];seen=set()
        while stack:
            x,y=stack.pop()
            if (x,y) in seen:continue
            seen.add((x,y))
            if x<0 or y<0:
                require(x==y,'Render leaf identity changed');continue
            an,bn=ar[5][x],br[5][y]
            require(an[3:9]==bn[3:9],'Render node bounds changed')
            require([sa(i) for i in range(an[9],an[9]+an[10])]==[sb(i) for i in range(bn[9],bn[9]+bn[10])],
                    'Render node face associations changed')
            stack.extend(zip(an[1:3],bn[1:3]))
    require(a[4]==b[4] and a[8]==b[8],'Visibility or light sample bytes changed')
    require(len(ar[10])==len(br[10]),'Leaf count changed')
    mark_count=0
    for al,bl in zip(ar[10],br[10]):
        require(al[:8]+al[10:]==bl[:8]+bl[10:],'Leaf contents/visibility/bounds/ambient changed')
        am=[sa(ar[11][i][0]) for i in range(al[8],al[8]+al[9])]
        bm=[sb(br[11][i][0]) for i in range(bl[8],bl[8]+bl[9])]
        require(am==bm,'World leaf face associations changed');mark_count+=len(am)
    inline_faces=verify_inline_rendering(a,b,retained_models,0,(ar,br))
    return dict(survivor_entities=len(be),survivor_models=len(retained_models),resolved_model_face_comparisons=checked,
        inline_face_comparisons=inline_faces,collision_tree_comparisons=4*len(retained_models),
        world_leaf_face_comparisons=mark_count,world_visibility_and_light_bytes='identical',
        surviving_entity_attributes='identical except explicit inline model index remap',
        resolved_positions_planes_winding_uv_material_styles_light_offsets='byte-identical',
        model_bounds_origins_visibility_leaf_counts='identical')


def remove_geometry(raw,refs,origin):
    data=lumps(raw);r=rows(data);records=strict_entities(data[0]);wanted={};keys=set()
    require(len(origin)==3 and all(math.isfinite(v) for v in origin),'Invalid map origin')
    for ref in refs:
        require(ref.get('type')=='CONT' and ref.get('kind')=='small_mushroom','Target is not an original mushroom container')
        key=ref.get('source_key');require(isinstance(key,(list,tuple)) and len(key)==4 and key[1]=='exterior' and key[3]==ref['number'],
                                      'Full original placement key required')
        frozen=(key[0],key[1],tuple(key[2]),key[3]);require(frozen not in keys,'Duplicate original placement key');keys.add(frozen)
        number=str(ref['number']);require(number not in wanted,'Ambiguous numeric original reference');wanted[number]=ref
    require(wanted,'No target placements')
    removed=[];bound=[];matched=set()
    for i,e in enumerate(records):
        number=e.get('aw_ref')
        if number not in wanted:continue
        require(number not in matched,'Duplicate original reference entity');matched.add(number);ref=wanted[number]
        require(set(e)=={'classname','aw_ref','model','origin','angles'} and e['classname']=='func_wall','Unrecognized target entity attributes/class')
        require(re.fullmatch(r'\*[1-9]\d*',e['model']) is not None,'Target requires an inline model')
        model=int(e['model'][1:]);require(model<len(r[14]),'Invalid target model')
        position=number_vector(e['origin']);angles=number_vector(e['angles'])
        expected=[x*.25-o for x,o in zip(ref['position'],origin)]
        require(all(abs(a-b)<=0.000011 for a,b in zip(position,expected)),'Target origin differs from original exporter pose')
        yaw=-ref['rotation_radians'][2]*180/math.pi
        require(abs(angles[0])<=1e-10 and abs(angles[2])<=1e-10 and abs((angles[1]-yaw+180)%360-180)<=1e-7,
                'Target rotation differs from original exporter pose')
        removed.append(i);bound.append(dict(entity_index=i,entity=e,source_key=ref['source_key'],source_id=ref['id'],
                                            source_model=ref['model'],inline_model=model,expected_origin=expected))
    require(matched==set(wanted),'Missing target reference entity')
    # This path cannot remove anything already merged into the world renderer.
    worldfaces=set(range(r[14][0][14],sum(r[14][0][14:16])))
    worldfaces.update(n[0] for n in r[11]);stack=[r[14][0][9]];seen=set()
    while stack:
        node=stack.pop()
        if node<0 or node in seen:continue
        seen.add(node);n=r[5][node];worldfaces.update(range(n[9],n[9]+n[10]));stack.extend(n[1:3])
    for item in bound:
        m=r[14][item['inline_model']]
        require(not (set(range(m[14],m[14]+m[15]))&worldfaces),'Target geometry is referenced by the world renderer')
    survivors=[e for i,e in enumerate(records) if i not in set(removed)]
    result,compaction=compact(raw,survivors,prune_world=False,visual_bounds=None)
    proof=verify_survivors(raw,result,compaction['retained_models'],set(removed))
    require(not any(e.get('aw_ref') in wanted for e in entities(lumps(result)[0])),'Target entity survived removal')
    return result,dict(format='Exact original harvest geometry exclusion 1',source_sha256=hashlib.sha256(raw).hexdigest(),
        result_sha256=hashlib.sha256(result).hexdigest(),removed=bound,compaction=compaction,proof=proof,
        policy='Only exact original-reference entities removed; compact unused data; preserve every surviving model and world surface/hull')
