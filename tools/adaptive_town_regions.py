# SPDX-License-Identifier: GPL-3.0-only
"""Measured adaptive town-core subdivision; never installs runtime maps.

The evaluator MUST compile/inspect the candidate's actual bounded payload. It
returns peak_loader_bytes and may retain provenance/report paths. Geometry-area
heuristics cannot substitute for that evaluator. Output is a proposed layout;
coverage, collisions, state continuity and target tests remain separate gates.
"""
import copy
import math

MIB = 1024 * 1024


def plan(entries, evaluate, *, terrain_bounds, prefix, overlap=896,
         draw_distance=540, hysteresis=96, heap_budget=11*MIB,
         non_map_reserve=3*MIB, safety_headroom=2*MIB,
         planning_peak=5*MIB, min_core=64, max_regions=64):
    from town_config import runtime_towns
    if prefix not in {town['prefix'] for town in runtime_towns()}:
        raise ValueError('Expected supported native town prefix')
    if not 1 <= max_regions <= 64 or min_core <= 0:
        raise ValueError('Invalid native region capacity or minimum core size')
    if non_map_reserve < 3*MIB or safety_headroom < 2*MIB:
        raise ValueError('Do not reduce mandatory reserve/headroom')
    ceiling=heap_budget-non_map_reserve-safety_headroom
    if not 0 < planning_peak <= ceiling:
        raise ValueError('Invalid planning peak')
    if overlap < math.sqrt(2)*draw_distance+hysteresis+32:
        raise ValueError('Insufficient visibility/hysteresis coverage overlap')
    def bounds(value):
        if len(value)!=2 or any(len(p)!=2 for p in value):
            raise ValueError('Expected XY bounds')
        if not all(math.isfinite(v) for p in value for v in p) or any(value[0][i]>=value[1][i] for i in range(2)):
            raise ValueError('Expected finite nonempty bounds')
        return [list(value[0]),list(value[1])]
    terrain_bounds=bounds(terrain_bounds)
    work=[];attempts=[];cache={}
    for index,entry in enumerate(entries):
        item=copy.deepcopy(entry);item['core']=bounds(item['core'])
        item['source_region']=entry.get('source_region',entry['name'])
        item['candidate_id']=str(index)
        work.append(item)
    if not work or len(work)>max_regions:
        raise ValueError('Initial region directory exceeds capacity')
    # A rectangular partition must not contain interior overlaps. Splits below
    # preserve every parent's union exactly, including partial outer cores.
    for i,a in enumerate(work):
        for b in work[i+1:]:
            if all(min(a['core'][1][k],b['core'][1][k]) > max(a['core'][0][k],b['core'][0][k]) for k in range(2)):
                raise ValueError('Initial cores overlap')
    def inspect(item):
        low,high=item['core']
        item['coverage']=[
            [min(low[i],max(terrain_bounds[0][i],low[i]-overlap)) for i in range(2)],
            [max(high[i],min(terrain_bounds[1][i],high[i]+overlap)) for i in range(2)]]
        key=(item['source_region'],*low,*high)
        if key not in cache:
            measured=dict(evaluate(copy.deepcopy(item)))
            peak=measured.get('peak_loader_bytes')
            if isinstance(peak,bool) or not isinstance(peak,int) or peak<0:
                raise ValueError('Evaluator must return nonnegative integer peak_loader_bytes')
            cache[key]=measured
        item['heap_estimate']=copy.deepcopy(cache[key])
        peak=item['heap_estimate']['peak_loader_bytes']
        item['growth_margin_bytes']=ceiling-peak
        item['planning_margin_bytes']=planning_peak-peak
        return item
    work=[inspect(item) for item in work]
    blocked=set();stop='planning_target_met'
    while True:
        costly=[item for item in work if item['planning_margin_bytes']<0 and item['candidate_id'] not in blocked]
        if not costly:break
        if len(work)>=max_regions:
            stop='native_region_capacity';break
        # Resolve actual gate failures first, then the largest growth concern.
        parent=max(costly,key=lambda item:(item['growth_margin_bytes']<0,-item['growth_margin_bytes']))
        low,high=parent['core'];options=[]
        for axis in range(2):
            if (high[axis]-low[axis])/2 < min_core:continue
            mid=(low[axis]+high[axis])/2
            children=[]
            for side in range(2):
                child=copy.deepcopy(parent);child['candidate_id']=parent['candidate_id']+f'.{axis}{side}'
                child['core']=copy.deepcopy(parent['core'])
                child['core'][1-side][axis]=mid
                children.append(inspect(child))
            options.append((max(c['heap_estimate']['peak_loader_bytes'] for c in children),axis,children))
        if not options:
            blocked.add(parent['candidate_id']);stop='minimum_core_reached';continue
        peak,axis,children=min(options,key=lambda opt:(opt[0],opt[1]))
        before=parent['heap_estimate']['peak_loader_bytes']
        attempts.append(dict(candidate_id=parent['candidate_id'],core=parent['core'],
                             before_peak_bytes=before,after_max_peak_bytes=peak,
                             split_axis=axis,accepted=peak<before))
        if peak>=before:
            # Overlap/shared-data floors require payload optimization instead;
            # multiplying identical-cost cells cannot be called a repair.
            blocked.add(parent['candidate_id']);stop='no_measured_reduction';continue
        where=work.index(parent);work[where:where+1]=children
    work.sort(key=lambda item:(item['core'][0][1],item['core'][0][0],item['candidate_id']))
    for index,item in enumerate(work):item['name']=f'{prefix}{index:03d}'
    failing=[item['name'] for item in work if item['growth_margin_bytes']<0]
    growth=[item['name'] for item in work if item['planning_margin_bytes']<0]
    return dict(format='AmiWind measured adaptive town proposal 1',
                status='estimate_failed' if failing else 'estimate_passed',
                runtime_validation='pending',installed=False,regions=work,
                region_count=len(work),overlap=overlap,hysteresis=hysteresis,
                draw_distance=draw_distance,heap_budget_bytes=heap_budget,
                non_map_reserve_bytes=non_map_reserve,safety_headroom_bytes=safety_headroom,
                map_peak_ceiling_bytes=ceiling,planning_peak_bytes=planning_peak,
                over_budget_regions=failing,planning_target_unmet_regions=growth,
                stop_reason='planning_target_met' if not growth else stop,
                evaluator_calls=len(cache),split_attempts=attempts)
