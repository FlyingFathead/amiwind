# SPDX-License-Identifier: GPL-3.0-only
"""Target-ABI guard companion cache and loader costs, separate from BSP geometry."""
from pathlib import Path
import json
import re
import struct
from prepare_guard_torches import fingerprint_entries

# Runtime frees this admission probe before entering the ordinary alias loader.
ADMISSION_PROBE_BYTES = 1024 * 1024


def alias_cost(raw, sizes):
    required=('aliashdr','maliasframedesc','mdl','stvert','mtriangle','maliasskindesc','trivertx','cache_system','hunk')
    if any(not isinstance(sizes.get(key),int) or sizes[key]<=0 for key in required):
        raise ValueError('Actual target alias ABI measurements are required')
    if len(raw)<84 or raw[:4]!=b'IDPO' or struct.unpack_from('<i',raw,4)[0]!=6:
        raise ValueError('Invalid guard alias header')
    skins,w,h,nv,nt,nf=struct.unpack_from('<6i',raw,48)
    if skins!=1 or w<=0 or w%4 or not 0<h<=480 or not 0<nv<=1999 or not 0<nt<=666 or nf not in (8,21):
        raise ValueError('Guard alias exceeds bounded format')
    start=88+w*h+nv*12+nt*16
    if struct.unpack_from('<i',raw,84)[0] or start+nf*(28+nv*4)!=len(raw):
        raise ValueError('Grouped or truncated guard alias')
    if any(struct.unpack_from('<i',raw,start+i*(28+nv*4))[0] for i in range(nf)):
        raise ValueError('Grouped guard alias frame')
    align=lambda value:(value+15)&~15
    alloc=lambda value:sizes['hunk']+align(value)
    header=alloc(sizes['aliashdr']+(nf-1)*sizes['maliasframedesc']+sizes['mdl']+nv*sizes['stvert']+nt*sizes['mtriangle'])
    decoded=header+alloc(sizes['maliasskindesc'])+alloc(w*h)+nf*alloc(nv*sizes['trivertx'])
    return {'file_bytes':len(raw),'frames':nf,'vertices':nv,'triangles':nt,
            'decoded_hunk_bytes':decoded,'cache_bytes':align(decoded+sizes['cache_system']),
            'external_malloc_peak_bytes':len(raw)+decoded,
            'source_file_hunk_fallback_bytes':alloc(len(raw)+1),
            'decoded_malloc_copy_supported':decoded<=512*1024,'source_malloc_supported':len(raw)<=512*1024}


def profile(id1, sizes):
    id1=Path(id1)
    path=id1/'gfx/guard-torches.json'
    if not path.is_file():
        if (id1/'gfx/guard-torches.awg').exists():raise ValueError('Guard heap registry missing manifest')
        return None
    def read(name):
        p=id1/name
        return p.read_bytes() if p.is_file() else None
    fingerprint_entries(read)  # Exact registry, companion and base-model hashes.
    report=json.loads(path.read_text(encoding='utf-8'))
    names=sorted({row[key] for row in report['records'] for key in ('body_model','torch_model')})
    models={name:alias_cost((id1/name).read_bytes(),sizes) for name in names}
    return {'records':report['records'],'models':models,
            'global_warm_cache_ceiling_bytes':sum(row['cache_bytes'] for row in models.values()),
            'admission_probe_bytes':ADMISSION_PROBE_BYTES,
            'maximum_external_malloc_peak_bytes':max(ADMISSION_PROBE_BYTES, max((row['external_malloc_peak_bytes'] for row in models.values()),default=0)) if models else 0,
            'scope':'All unique warm caches are evictable within the existing game heap. OS malloc and static BSS are separate Fast RAM costs.'}


def map_cost(entity_bytes, prepared):
    zero={'matching_guard_placements':0,'active_model_union':[],'automatic_model_union':[],
          'active_cache_bytes':0,'automatic_cache_bytes':0,'conservative_game_heap_peak_bytes':0,
          'external_malloc_peak_bytes':0,'admission_probe_bytes':0,'source_and_decoded_hunk_fallback_peak_bytes':0}
    if prepared is None:return zero
    lookup={(row['source_id'].casefold(),row['base_model']):row for row in prepared['records']}
    active=set();automatic=set();placements=0
    for block in re.findall(r'\{[^{}]*\}',entity_bytes.decode('cp1252')):
        ent=dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"',block))
        if ent.get('classname')!='aw_npc':continue
        # Runtime matches TES record IDs case-insensitively; model paths stay exact.
        row=lookup.get((ent.get('aw_source_id','').casefold(),ent.get('model')))
        if row:
            placements+=1;active.update((row['body_model'],row['torch_model']))
            if row['auto_inventory_eligible']:automatic.update((row['body_model'],row['torch_model']))
    models=prepared['models']
    cached=sum(models[name]['cache_bytes'] for name in active)
    # Conservative fallback: original source file can occupy high hunk if its
    # malloc fails, while decoded staging remains live if copy malloc fails.
    # Charge this on top of the entire active cache union, without assuming
    # either malloc succeeds or that old cache entries have been evicted first.
    fallback=max((models[name]['decoded_hunk_bytes']+models[name]['source_file_hunk_fallback_bytes'] for name in active),default=0)
    return {'matching_guard_placements':placements,'active_model_union':sorted(active),
            'automatic_model_union':sorted(automatic),'active_cache_bytes':cached,
            'automatic_cache_bytes':sum(models[name]['cache_bytes'] for name in automatic),
            'conservative_game_heap_peak_bytes':cached+fallback,
            'source_and_decoded_hunk_fallback_peak_bytes':fallback,
            'admission_probe_bytes':ADMISSION_PROBE_BYTES if active else 0,
            'external_malloc_peak_bytes':max(ADMISSION_PROBE_BYTES, max((models[name]['external_malloc_peak_bytes'] for name in active),default=0)) if active else 0,
            'scope':'Forced-on union of every matching map guard, before PVS/distance reduction. Not measured runtime use.'}


def apply(report, cost):
    report['guard_torches']=cost
    if not cost['conservative_game_heap_peak_bytes']:return
    report['geometry_and_sprite_peak_before_guard_bytes']=report['peak_loader_bytes']
    report['peak_loader_bytes']+=cost['conservative_game_heap_peak_bytes']
    report['resident_loader_bytes']+=cost['active_cache_bytes']
    report['resident_bytes_at_peak']+=cost['active_cache_bytes']
    report['classifier_allocation_failure_fallback_peak_bytes']+=cost['conservative_game_heap_peak_bytes']
    report['peak_section']='conservative guard companion cache/load overlap'
