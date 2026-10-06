# SPDX-License-Identifier: GPL-3.0-only
"""Compact harvest malloc ledger, separate from Hunk/model cache residency.

Requested bytes, aligned live blocks and conservative new OS reservations are
different quantities. Never credit presumed free space in the shared allocator.
"""
import hashlib
from pathlib import Path
import re
import subprocess

# The cached 68040/FPU newlib archive was inspected with the matching SDK.
# Unknown allocators need an audited profile; a familiar compiler name is not
# evidence that malloc has the same metadata, growth or failure behavior.
KNOWN_ALLOCATOR = '5f4c949853f55b4aee66fd00fa3c37d4e8429303c5714920a8c2feb1803e114f'


def runtime_policy(engine):
    engine=Path(engine)
    header=(engine/'src/aw_harvest.h').read_text(encoding='utf-8')
    if not re.search(r'^\s*#define\s+AW_HARVEST_TEXT_BYTES\s+',header,re.M):
        return dict(mode='static',verified=True)
    checks={
        'aw_harvest.c': [
            'bytes=models*sizeof(aw_harvest_model_t)+nodes*sizeof(aw_harvest_node_t)+edges*sizeof(aw_harvest_edge_t)+plants*sizeof(aw_harvest_plant_t);',
            'p=(unsignedchar*)calloc(1,bytes);', 'next=(char*)realloc(h->text,bytes);',
            'free(h->storage);free(h->text);'],
        'aw_harvest_proxy.c': [
            'allocated_bytes=visible*sizeof(entity_t)+h->plants*(sizeof(*indices)+sizeof(*submitted));',
            'proxies=(entity_t*)calloc(1,allocated_bytes);', 'free(proxies);'],
        'aw_harvest_runtime.c': [
            'plants=(edict_t**)calloc(harvest.plants,sizeof(*plants)+sizeof(*available));',
            'AW_HarvestProxyClear();free(plants);plants=NULL;available=NULL;AW_HarvestRelease(&harvest);'],
    }
    expected_calls={'aw_harvest.c':2,'aw_harvest_proxy.c':1,'aw_harvest_runtime.c':1}
    hashes={}
    for name,patterns in checks.items():
        raw=(engine/'src'/name).read_bytes();hashes[name]=hashlib.sha256(raw).hexdigest()
        text=re.sub(r'/\*.*?\*/|//[^\n]*','',raw.decode(),flags=re.S)
        if len(re.findall(r'\b(?:malloc|calloc|realloc)\s*\(',text))!=expected_calls[name]:
            raise ValueError('Unrecognized compact harvest allocation policy: '+name)
        text=re.sub(r'\s+','',text)
        if any(pattern not in text for pattern in patterns):
            raise ValueError('Unrecognized compact harvest allocation policy: '+name)
    return dict(mode='compact_offsets',verified=True,source_sha256=hashes,
                ownership='map-owned malloc; dictionary realloc overlaps old/new; no Hunk allocation')


def allocator_policy(compiler):
    path=Path(subprocess.check_output([str(compiler),'-m68040','-m68881','-print-file-name=libc.a'],text=True).strip())
    if not path.is_file():return dict(mode='unknown',reason='Target libc archive could not be resolved')
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    if sha!=KNOWN_ALLOCATOR:return dict(mode='unknown',library_sha256=sha,reason='Unaudited target allocator')
    return dict(mode='newlib_memmap_1',library_sha256=sha,verified=True,
        block_header_bytes=16,block_alignment=16,small_block_limit_bytes=32747,
        data_arena_os_request_bytes=32760,free_node_pool_os_request_bytes=3080,
        large_block_extra_bytes=4,realloc='allocates/copies/frees; two buffers overlap',
        scope='library allocation policy; shared arena fragmentation and native free RAM are not measured')


def allocation_cost(requests):
    """Charge each simultaneously live request independently; do not assume
    reusable arena or free-tree capacity. This deliberately overcounts sharing.
    Large blocks use direct OS allocations in the audited target allocator.
    """
    if any(type(n) is not int or n<0 for n in requests):raise ValueError('Invalid malloc request')
    requests=[n for n in requests if n]
    blocks=[(n+31)&~15 for n in requests]
    reserve=sum(32760+3080 if n<=32747 else n+4 for n in blocks)
    return dict(requested_bytes=sum(requests),rounded_live_blocks_bytes=sum(blocks),
                conservative_new_os_reservation_bytes=reserve,simultaneous_requests=len(requests))


def catalogue_usage(raw,sizes):
    """Count the exact interned strings and arrays of canonical AWH1-AWH4.
    Semantic loot/pose validation remains the actual C parser's responsibility.
    Reject ambiguous or oversized fields rather than underestimate their memory.
    """
    if not 0<len(raw)<=65536:raise ValueError('Harvest catalogue byte bound')
    try:lines=raw.decode('ascii').splitlines();header=lines[0].split()
    except (UnicodeError,IndexError):raise ValueError('Invalid compact harvest text') from None
    version=header[0] if header else ''
    if version not in ('AWH1','AWH2','AWH3','AWH4'):raise ValueError('Unknown harvest format')
    try:
        nodes,edges,plants=map(int,header[1:4]);models=int(header[6]) if version=='AWH4' else 0
    except (ValueError,IndexError):raise ValueError('Invalid compact harvest counts') from None
    bounds=(sizes['harvest_node_capacity'],sizes['harvest_edge_capacity'],sizes['harvest_plant_capacity'],sizes['harvest_model_capacity'])
    if any(n<0 or n>limit for n,limit in zip((nodes,edges,plants,models),bounds)) or len(lines)!=1+models+nodes+edges+plants:
        raise ValueError('Compact harvest counts exceed measured runtime')
    strings=set()
    def intern(value):
        if len(value)>63 or any(ord(c)<32 or ord(c)>126 for c in value):raise ValueError('Invalid interned harvest text')
        if value:strings.add(value)
    at=1;paths=[]
    for line in lines[at:at+models]:
        fields=line.split()
        if len(fields)!=8:raise ValueError('Invalid harvest model record')
        intern(fields[0]);paths.append(fields[0])
    at+=models
    for line in lines[at:at+nodes]:
        prefix,separator,label=line.partition('\t');fields=prefix.split()
        if len(fields)!=6 or (version!='AWH1' and not separator):raise ValueError('Invalid harvest node record')
        intern(fields[5]);intern(label if version!='AWH1' else '')
    at+=nodes+edges
    for line in lines[at:]:
        last=14 if version=='AWH4' else 13 if version=='AWH3' else 12
        fields=line.split(maxsplit=last)
        if len(fields)!=last+1:raise ValueError('Invalid harvest plant record')
        intern(fields[0]);intern(fields[3 if version in ('AWH3','AWH4') else 2]);intern(fields[-1])
    text=1+sum(len(s)+1 for s in strings) if strings else 0
    if text>sizes['harvest_text_capacity']:raise ValueError('Harvest dictionary exceeds measured runtime')
    arrays=sum(n*sizes[key] for n,key in zip((models,nodes,edges,plants),
        ('harvest_model_record','harvest_node_record','harvest_edge_record','harvest_plant_record')))
    bindings=plants*(sizes['entity']+sizes['short']+1) if version=='AWH4' else plants*(sizes['pointer']+1)
    return dict(version=version,nodes=nodes,edges=edges,plants=plants,models=models,model_paths=paths,
        interned_strings=len(strings),dictionary_bytes=text,array_bytes=arrays,
        catalogue_requested_bytes=arrays+text,all_available_binding_bytes=bindings,
        catalogue_growth=allocation_cost([arrays,text,text]),
        resident=allocation_cost([arrays,text,bindings]))


def profile(root,sizes):
    from build_aga import harvest_fingerprint_entries
    from harvest_heap import alias_cost
    root=Path(root)
    required=('harvest_runtime_static','harvest_proxy_static','harvest_model_record','harvest_node_record',
        'harvest_edge_record','harvest_plant_record','harvest_node_capacity','harvest_edge_capacity',
        'harvest_plant_capacity','harvest_model_capacity','harvest_text_capacity','entity','pointer','short')
    if any(type(sizes.get(key)) is not int or sizes[key]<=0 for key in required):
        raise ValueError('Actual target compact harvest ABI measurements are required')
    if sizes.get('harvest_storage_policy_verified')!=1 or sizes.get('harvest_allocator_mode')!=1:
        raise ValueError('Compact harvest requires recognized runtime and target allocator policies')
    entries=harvest_fingerprint_entries(root,plant_capacity=sizes['harvest_plant_capacity'])
    records=[];models={}
    for name,sha in entries:
        raw=(root/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('Harvest input changed during heap inspection')
        if name.startswith('progs/harvest/'):
            required_alias=('aliashdr','mdl','stvert','mtriangle','maliasskindesc','trivertx','cache_system','hunk')
            if any(type(sizes.get(k)) is not int or sizes[k]<=0 for k in required_alias):raise ValueError('Actual target alias ABI measurements required')
            models[name]=dict(alias_cost(raw,sizes),sha256=sha)
        else:records.append(dict(path=name,sha256=sha,bytes=len(raw),**catalogue_usage(raw,sizes)))
    static=sizes['harvest_runtime_static']+sizes['harvest_proxy_static'];map_costs={}
    for record in records:
        active=[models[name] for name in record['model_paths']]
        cache=sum(m['cache_bytes'] for m in active)
        from alias_stream_heap import fallback as alias_fallback
        fallback=max((alias_fallback(m) for m in active),default=0)
        base=[record['array_bytes'],record['dictionary_bytes'],record['all_available_binding_bytes']]
        stages=[record['catalogue_growth'],record['resident']]
        # Model load may overlap the complete render pool. Count source and
        # decoder malloc even though the Hunk fallback is also charged: the
        # combined bound is intentionally conservative across either path.
        stages.extend(allocation_cost([*base,m['file_bytes']+1,m['decoded_hunk_bytes']]) for m in active if m.get('alias_loader_mode')!='direct_cache_stream')
        reserve=max(stage['conservative_new_os_reservation_bytes'] for stage in stages)
        map_costs[record['path'][8:-4]]=dict(active_model_union=record['model_paths'],
            warm_cache_bytes=cache,loader_fallback_bytes=fallback,
            conservative_game_heap_peak_bytes=cache+fallback,
            external_malloc_requested_peak_bytes=max(s['requested_bytes'] for s in stages),
            external_malloc_rounded_blocks_peak_bytes=max(s['rounded_live_blocks_bytes'] for s in stages),
            external_allocator_reservation_allowance_bytes=reserve,
            conservative_total_allowance_charge_bytes=cache+fallback+static+reserve,
            catalogue_requested_bytes=record['catalogue_requested_bytes'],
            all_available_binding_bytes=record['all_available_binding_bytes'],allocation_stages=stages)
    return dict(storage_mode='compact_offsets',catalogues=records,fingerprint_entries=entries,models=models,
        unique_models=len(models),global_warm_cache_ceiling_bytes=sum(m['cache_bytes'] for m in models.values()),
        map_costs=map_costs,proxy_static_bytes=sizes['harvest_proxy_static'],
        runtime_static_bytes=sizes['harvest_runtime_static'],catalogue_extension_static_bytes=0,
        additional_static_allowance_bytes=static,
        maximum_external_malloc_peak_bytes=max((r['external_malloc_requested_peak_bytes'] for r in map_costs.values()),default=0),
        scope='Exact-count catalogue/dictionary/proxy or legacy bindings are malloc-owned. Hunk cache/fallback is separate. Admission charges independent cold arena/node-pool reservation for every simultaneously live malloc, without credit for shared arena reuse. Static charge is the entire compact harvest runtime; no negative baseline-reserve credit.',
        allocator='audited newlib_memmap_1; conservative cold reservation, not measured process delta',native_acceptance='not_measured')
