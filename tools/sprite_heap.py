# SPDX-License-Identifier: GPL-3.0-only
"""Target sprite residency/input overlap; pixels are shared per loaded model."""
import hashlib,math,re,struct
from pathlib import PurePosixPath

# World flora sprites (trees, grass, reeds) come only from the builder's
# world-flora steps (prepare_tree_sprites.py, prepare_world_flora.py).
FLORA_SPRITE_DIR='progs/aw_flora/'

def missing_flora_message(models):
    """Name the cause when maps place flora that this build did not make (BUILD-FLORA-OPTIN-32)."""
    shown=', '.join(models[:3])+(f' and {len(models)-3} more' if len(models)>3 else '')
    return (f'World flora was not built: maps place {len(models)} flora sprite(s) missing from the image ({shown}). '
            'Trees and grass are built by default; this build left them out (--no-tree-sprites, debugging only, '
            'or a hand-run image step without --world-flora). Rebuild without --no-tree-sprites.')

def allocation(payload,header):
    return header+((payload+15)//16)*16

def float32(value):
    return struct.unpack('<f',struct.pack('<f',value))[0]

def sprite_loader_profile(source):
    """Recognize the explicit source-selected loader; otherwise retain staging.

    This is allocation-policy evidence, not proof that the loader passed tests.
    The surrounding audit records the exact model.c hash and engine receipt.
    """
    source = re.sub(r'/\*.*?\*/|//[^\n]*', '', source, flags=re.S)
    enabled = bool(re.search(r'^\s*#define\s+AW_STREAM_SPRITES\s+1\s*$', source, re.M))
    dispatch = bool(re.search(r'#if\s+AW_STREAM_SPRITES\s+if\s*\(Mod_TryStreamSprite\(mod\)\)\s*return\s+mod;', source))
    chunk = re.search(r'^\s*#define\s+AW_SPRITE_PIXEL_CHUNK\s+(\d+)\s*$', source, re.M)
    streamed = enabled and dispatch and chunk is not None
    return {'mode': 'streamed' if streamed else 'staged',
            'sprite_streaming': int(streamed),
            'conversion_stack_chunk_bytes': int(chunk.group(1)) if streamed else 0,
            'validation': 'source policy only; native and target validation separate'}

def estimate_sprite(raw,sizes):
    if len(raw)<36:raise ValueError('Truncated sprite header')
    magic,version,kind,radius,w,h,frames,beam,sync=struct.unpack_from('<4siifiiifi',raw)
    if magic!=b'IDSP' or version!=1 or not 0<=kind<=4 or not 0<frames<=128 or min(w,h)<=0:
        raise ValueError('Invalid sprite header')
    if not math.isfinite(radius) or not math.isfinite(beam):raise ValueError('Nonfinite sprite header')
    resident=allocation(sizes['msprite']+(frames-1)*sizes['mspriteframedesc'],sizes['hunk'])
    at=36;pixels=0;frame_count=0;frame_radius=0
    def frame():
        nonlocal at,pixels,resident,frame_count,frame_radius
        if at+16>len(raw):raise ValueError('Truncated sprite frame')
        x,y,fw,fh=struct.unpack_from('<4i',raw,at);at+=16
        if min(fw,fh)<=0 or fw*fh>len(raw)-at:raise ValueError('Invalid sprite frame pixels')
        count=fw*fh;at+=count;pixels+=count;frame_count+=1
        # Match Mod_SpriteFrameRadius: asymmetric frame origins matter, and
        # view-parallel sprites can turn every corner in world space.
        fx=max(abs(x),abs(x+fw));fy=max(abs(y),abs(y-fh))
        frame_radius=max(frame_radius,float32(math.sqrt(float32(fx*fx+fy*fy))))
        resident+=allocation(sizes['mspriteframe']+count,sizes['hunk'])
    for i in range(frames):
        if at+4>len(raw):raise ValueError('Truncated sprite frame type')
        typ=struct.unpack_from('<i',raw,at)[0];at+=4
        if typ==0:frame()
        elif typ==1:
            if at+4>len(raw):raise ValueError('Truncated sprite group')
            count=struct.unpack_from('<i',raw,at)[0];at+=4
            if not 0<count<=128 or at+count*4>len(raw):raise ValueError('Invalid sprite group')
            intervals=struct.unpack_from('<'+str(count)+'f',raw,at);at+=count*4
            if any(not math.isfinite(t) or t<=0 for t in intervals):raise ValueError('Invalid sprite intervals')
            resident+=allocation(sizes['mspritegroup']+(count-1)*sizes['pointer'],sizes['hunk'])
            resident+=allocation(count*sizes['float'],sizes['hunk'])
            for j in range(count):frame()
        else:raise ValueError('Invalid sprite frame type')
    if at!=len(raw):raise ValueError('Unexpected sprite trailing bytes')
    # Mod_LoadModel uses a 1024-byte stack buffer, otherwise Hunk temporary input.
    temporary=allocation(len(raw),sizes['hunk']) if len(raw)>1024 and not sizes.get('sprite_streaming',0) else 0
    return {'file_bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
            'pixel_bytes':pixels,'frames':frame_count,'resident_hunk_bytes':resident,
            'bounding_radius':frame_radius,
            'temporary_input_bytes':temporary,
            'input_loader_mode':'streamed' if sizes.get('sprite_streaming',0) else 'staged'}

def inspect_sprites(entity_bytes,asset_root,sizes):
    instances=[];signon=0;entity_count=0
    for block in re.findall(rb'\{[^{}]*\}',entity_bytes):
        ent={a.decode('cp1252'):b.decode('cp1252') for a,b in re.findall(rb'"([^"\n]+)"\s+"([^"\n]*)"',block)}
        entity_count+=1
        classname=ent.get('classname','')
        signon += 33 if classname=='aw_flora' else 14 if classname=='aw_static' else 16
        model=ent.get('model','')
        if not model.lower().endswith('.spr'):continue
        p=PurePosixPath(model)
        if p.is_absolute() or '..' in p.parts or '\\' in model or ':' in model or len(model.encode('cp1252'))>=64:
            raise ValueError('Unsafe sprite model path: '+model)
        if ent.get('classname')=='aw_flora':
            try:scale=float(ent['aw_scale'])
            except (KeyError,ValueError):raise ValueError('Missing/invalid flora scale')
            if not math.isfinite(scale) or scale<=0:raise ValueError('Invalid flora scale')
        instances.append(model)
    # The engine's static entity budget (client.h MAX_STATIC_ENTITIES, tools/engine_limits.py).
    from engine_limits import limits as engine_limits
    if len(instances)>engine_limits()['max_static_entities']:raise ValueError('Static sprite entity limit exceeded')
    # Reserve room for player/world baselines and signon control messages.
    # Count even model-less map records conservatively; no content is omitted.
    signon += 1024
    signon_capacity=sizes.get('signon_capacity',16380)
    if signon > min(signon_capacity,sizes.get('reliable_capacity',16380)):
        raise ValueError('Map signon capacity exceeded: '+str(signon)+' bytes')
    assets=[]
    missing_flora=[model for model in sorted(set(instances))
                   if model.lower().startswith(FLORA_SPRITE_DIR) and not (asset_root/model).exists()]
    if missing_flora:
        raise ValueError(missing_flora_message(missing_flora))
    for model in sorted(set(instances)):
        p=asset_root/model
        if not p.is_file() or not p.resolve().is_relative_to(asset_root.resolve()):
            raise ValueError('Missing/unsafe sprite asset: '+model)
        assets.append({'model':model,**estimate_sprite(p.read_bytes(),sizes)})
    return {'static_sprite_instances':len(instances),'unique_sprite_models':len(assets),
            'sprite_assets':assets,'resident_hunk_bytes':sum(a['resident_hunk_bytes'] for a in assets),
            'temporary_input_peak_bytes':max((a['temporary_input_bytes'] for a in assets),default=0),
            'target_entity_size_bytes':sizes.get('entity'),
            'signon_upper_bound_bytes':signon, 'signon_capacity_bytes':signon_capacity,
            'signon_margin_bytes':signon_capacity-signon,
            'single_player_transport':transport_profile(sizes),
            'acceptance':'modeled shared model pixels plus conservative input overlap; engine reserve unchanged'}


def efrag_pool_profile(source):
    """Bind page accounting to literal limits in the matching client header."""
    source=re.sub(r'/\*.*?\*/|//[^\n]*','',source,flags=re.S)
    values={}
    for key,macro in (('base_links','MAX_EFRAGS'),('page_links','AW_EFRAG_PAGE_LINKS'),
                      ('max_links','AW_EFRAG_LIMIT'),('max_statics','MAX_STATIC_ENTITIES')):
        match=re.search(r'^\s*#define\s+'+macro+r'\s+(\d+)\b',source,re.M)
        if not match:raise ValueError('Missing efrag allocation policy: '+macro)
        values[key]=int(match[1])
    if (min(values.values())<=0 or values['max_links']<values['base_links'] or
            (values['max_links']-values['base_links'])%values['page_links']):
        raise ValueError('Invalid efrag allocation policy')
    return values


def inspect_efrags(table,sprites,sizes,policy):
    """Replay static bounds against world BSP planes; charge only extra pages.

    The base pool is existing process BSS. Every overflow page has a next
    pointer followed by efrags, plus Hunk payload alignment and its header.
    Model loading precedes client static linking; no frame allocates pages.
    """
    statics=[]
    for block in re.findall(rb'\{[^{}]*\}',table['entities']):
        ent={a.decode('cp1252'):b.decode('cp1252') for a,b in re.findall(rb'"([^"\n]+)"\s+"([^"\n]*)"',block)}
        if ent.get('classname') in ('aw_static','aw_flora'):statics.append(ent)
    if len(statics)>policy['max_statics']:raise ValueError('Static entity limit exceeded')
    required=0
    if statics:
        nodes=list(struct.iter_unpack('<i2h6h2H',table['nodes']))
        leaves=list(struct.iter_unpack('<ii6h2H4B',table['leafs']))
        planes=list(struct.iter_unpack('<4fi',table['planes']))
        models=list(struct.iter_unpack('<9f7i',table['models']))
        radii={a['model']:a['bounding_radius'] for a in sprites['sprite_assets']}
        for ent in statics:
            origin=[float32(float(v)) for v in ent.get('origin','0 0 0').split()]
            scale=float32(float(ent['aw_scale'])) if ent['classname']=='aw_flora' else 1
            if len(origin)!=3 or not all(math.isfinite(v) for v in origin) or not math.isfinite(scale) or scale<=0:
                raise ValueError('Invalid static pose/scale for efrag estimate')
            if ent['classname']=='aw_static':
                # Legacy MSG_WriteCoord/MSG_ReadCoord uses signed 1/8 units.
                origin=[((int(v*8)+32768)%65536-32768)/8 for v in origin]
            model=ent.get('model','')
            if model in radii:
                extent=float32(radii[model]*scale)
                lo=[float32(v-extent) for v in origin];hi=[float32(v+extent) for v in origin]
            elif re.fullmatch(r'\*\d+',model) and int(model[1:])<len(models):
                bounds=models[int(model[1:])]
                lo=[float32(v+b-1) for v,b in zip(origin,bounds[:3])]
                hi=[float32(v+b+1) for v,b in zip(origin,bounds[3:6])]
            else:raise ValueError('Unsupported static model bounds for efrag estimate: '+model)
            if not all(math.isfinite(v) for v in lo+hi):raise ValueError('Nonfinite static bounds')
            stack=[0];visits=0
            while stack:
                node=stack.pop();visits+=1
                if visits>2*(len(nodes)+len(leaves))+1:raise ValueError('Cyclic/shared BSP traversal in efrag estimate')
                if node<0:
                    leaf=-1-node
                    if leaf>=len(leaves):raise ValueError('Invalid BSP leaf in efrag estimate')
                    if leaves[leaf][0]!=-2:required+=1
                    if required>policy['max_links']:raise ValueError('Static entity leaf-link limit exceeded: '+str(required))
                    continue
                if node>=len(nodes):raise ValueError('Invalid BSP node in efrag estimate')
                row=nodes[node]
                if not 0<=row[0]<len(planes):raise ValueError('Invalid BSP plane in efrag estimate')
                p=planes[row[0]];axis=p[4];distance=p[3]
                if 0<=axis<3:sides=1 if distance<=lo[axis] else 2 if distance>=hi[axis] else 3
                else:
                    near=[hi[i] if p[i]>=0 else lo[i] for i in range(3)]
                    far=[lo[i] if p[i]>=0 else hi[i] for i in range(3)]
                    high=float32(float32(float32(p[0]*near[0])+float32(p[1]*near[1]))+float32(p[2]*near[2]))
                    low=float32(float32(float32(p[0]*far[0])+float32(p[1]*far[1]))+float32(p[2]*far[2]))
                    sides=(1 if high>=distance else 0)|(2 if low<distance else 0)
                if sides&2:stack.append(row[2])
                if sides&1:stack.append(row[1])
    pages=(max(0,required-policy['base_links'])+policy['page_links']-1)//policy['page_links']
    payload=sizes['pointer']+policy['page_links']*sizes['efrag'] if pages else 0
    if pages and sizes.get('efrag_page',payload)!=payload:
        raise ValueError('Target efrag page layout does not match allocation policy')
    page_bytes=allocation(payload,sizes['hunk']) if pages else 0
    return {**policy,'static_entities':len(statics),'required_links':required,'overflow_pages':pages,
            'page_payload_bytes':payload,'page_alignment_bytes':(-payload)%16 if pages else 0,
            'page_hunk_header_bytes':sizes['hunk'] if pages else 0,'page_hunk_bytes':page_bytes,
            'resident_hunk_bytes':pages*page_bytes,'allocated_links':policy['base_links']+pages*policy['page_links'],
            'lifetime':'map low-Hunk; client-state reset reuses pages; map clear releases them',
            'acceptance':'source bounds/traversal estimate; native coverage tested separately'}


def transport_profile(sizes):
    """Account for larger buffers AND removal of unused single-player slots.

    This compares target-ABI client/socket Hunk allocations against the prior
    four-client/five-socket minimum. It is not a runtime free-memory measurement.
    Explicit multiplayer configurations require a separate profile.
    """
    if not all(k in sizes for k in ('client','qsocket','network_capacity','reliable_capacity')):
        return {'status':'target_profile_unavailable'}
    reliable,network=sizes['reliable_capacity'],sizes['network_capacity']
    old_client=sizes['client']-(reliable-8000)
    old_socket=sizes['qsocket']-2*(network-8192)
    if min(old_client,old_socket)<=0:raise ValueError('Invalid transport target profile')
    header=sizes['hunk']
    before=allocation(4*old_client,header)+5*allocation(old_socket,header)+allocation(8192,header)
    after=allocation(sizes['client'],header)+2*allocation(sizes['qsocket'],header)+allocation(network,header)
    static_growth=sizes['signon_capacity']-8192
    return {'status':'single_player_static_estimate','clients':1,'sockets':2,
            'previous_hunk_bytes':before,'current_hunk_bytes':after,
            'hunk_delta_bytes':after-before,'server_static_delta_bytes':static_growth,
            'combined_transport_delta_bytes':after-before+static_growth,
            'engine_reserve_bytes_unchanged':3*1024*1024,
            'runtime_validation':'pending'}
