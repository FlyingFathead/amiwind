#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Partition the existing Seyda Neen conversion; preserve its meshes and hulls."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
from itertools import product
from audit_walkability import axes
from compact_bsp import compact, entities
from player_hull import lumps
from prepare_intro_docks import derive

CORE=768
OVERLAP=896
HYSTERESIS=96
DRAW_DISTANCE=540
# Include the existing world enclosure; partial edge cores remain explicit.
BOUNDS=((-2079,-2079),(2079,2079))
COURTYARD=(-128,-384,512,256)


def regions():
    # Keep the town/arrival route in one core; north boundary is the bridge
    # reported by the owner at Y474. Outskirts retain smaller rectangular cores.
    # Coverage still includes the complete draw-distance and hysteresis margin.
    xs=[BOUNDS[0][0],-1536,-768,1024,1792,BOUNDS[1][0]]
    ys=[BOUNDS[0][1],-1536,-768,474,1242,BOUNDS[1][1]]
    out=[]
    for y0,y1 in zip(ys,ys[1:]):
        for x0,x1 in zip(xs,xs[1:]):
            core=[[x0,y0],[x1,y1]]
            out.append({'name':f'sn{len(out):03d}','core':core,
                        'coverage':[[max(BOUNDS[0][i],core[0][i]-OVERLAP) for i in range(2)],
                                    [min(BOUNDS[1][i],core[1][i]+OVERLAP) for i in range(2)]]})
    if len(out)>64:raise ValueError('Too many Seyda Neen regions')
    if OVERLAP<math.sqrt(2)*DRAW_DISTANCE+HYSTERESIS+32:raise ValueError('Insufficient region overlap')
    return out


def select(raw, bounds, polygon=None):
    data=lumps(raw);models=list(struct.iter_unpack('<9f7i',data[14]));kept=[]
    low,high=bounds
    for e in entities(data[0]):
        if e.get('classname') not in ('func_wall','aw_static'):
            # Stable NPC identities remain available for restoration; the runtime
            # discards actors whose restored positions lie outside this region.
            kept.append(e);continue
        origin=[float(v) for v in e.get('origin','0 0 0').split()]
        if len(origin)!=3 or not all(math.isfinite(v) for v in origin):raise ValueError('Invalid entity position')
        a=[v-96 for v in origin];b=[v+96 for v in origin]
        if e.get('model','').startswith('*'):
            m=models[int(e['model'][1:])];basis=axes(tuple(map(float,e.get('angles','0 0 0').split())))
            points=[[origin[i]+sum(v[j]*basis[j][i] for j in range(3)) for i in range(3)]
                    for v in product(*[(m[j],m[j+3]) for j in range(3)])]
            a=[min(v[i] for v in points) for i in range(3)];b=[max(v[i] for v in points) for i in range(3)]
        if not all(b[i]>=low[i] and a[i]<=high[i] for i in range(2)):continue
        if polygon:
            corners=list(product((a[0],b[0]),(a[1],b[1])))
            # CCW convex polygon: reject only when the whole placed AABB is
            # outside one boundary. Keep complete intersecting objects.
            if any(all((q[0]-p[0])*(v[1]-p[1])-(q[1]-p[1])*(v[0]-p[0])<0 for v in corners)
                   for p,q in zip(polygon,polygon[1:]+polygon[:1])):continue
        kept.append(e)
    return kept


def convert(source, destination):
    source=Path(source);destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    raw=source.read_bytes();entries=regions();reports=[]
    for e in entries:
        masked,mask_report=derive(raw,(*e['coverage'][0],*e['coverage'][1]))
        converted,report=compact(masked,select(raw,e['coverage']),prune_world=True)
        (destination/(e['name']+'.bsp')).write_bytes(converted)
        reports.append(dict(e,**report))
    # Special intro scenes use the same compactor. They contain complete nearby
    # models; the dock mask keeps the established silhouette and route bounds.
    for name,bounds in [('intro_docks',None),('sncourt',COURTYARD)]:
        masked,mask_report=derive(raw) if bounds is None else derive(raw,bounds)
        low_high=((-240,-1100),(1120,620)) if bounds is None else (bounds[:2],bounds[2:])
        polygon=[(440+680*math.cos(i*math.pi/4),-240+860*math.sin(i*math.pi/4)) for i in range(8)] if bounds is None else None
        selected=select(masked,low_high,polygon)
        converted,report=compact(masked,selected,prune_world=True)
        (destination/(name+'.bsp')).write_bytes(converted)
        reports.append(dict(name=name,mask=mask_report,**report))
    # The regular default is the existing town-centre start. Door/ship arrivals
    # select their region from the actual arrival point before map loading.
    rows=['AWBR1 '+ ' '.join(map(str,[len(entries),HYSTERESIS,DRAW_DISTANCE,0,0,64,90,0,0,64,90]))]
    for e in entries:rows.append(' '.join(map(str,[e['name'],*e['core'][0],*e['core'][1],*e['coverage'][0],*e['coverage'][1]])))
    (destination.parent/'seyda-regions.txt').write_text('\n'.join(rows)+'\n')
    report={'source_sha256':hashlib.sha256(raw).hexdigest(),'regular_regions':len(entries),
            'outer_core_target':CORE,'town_core':[[-768,-768],[1024,474]],'north_bridge_y':474,'overlap':OVERLAP,'hysteresis':HYSTERESIS,'draw_distance':DRAW_DISTANCE,
            'world_terrain':'coverage faces retained; source collision plus outer coverage planes; PVS retained','regions':reports}
    (destination.parent/'seyda-regions.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('destination',type=Path)
    a=p.parse_args();r=convert(a.source,a.destination);print(f"Prepared {r['regular_regions']} Seyda regions plus dock and courtyard scenes.")
