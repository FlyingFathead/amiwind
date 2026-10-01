# SPDX-License-Identifier: GPL-3.0-only
"""Explicit NPC grounding policy and source identity for runtime release audits."""
import json
from pathlib import Path
import re
from mwad.audit import records, subrecords, cell_data
from player_hull import lumps, pack_lumps
from audit_walkability import Scene
from functools import lru_cache

POLICY = Path(__file__).resolve().parents[1]/'config/actor_grounding.json'
INTRO_IDS = {1:'chargen name',2:'chargen boat guard 2',3:'chargen boat guard 3',
             4:'chargen boat guard 1',5:'chargen dock guard',6:'chargen class',
             7:'chargen captain',8:'chargen door guard'}


def initial_state(identifier):
    policy = json.loads(POLICY.read_text())
    if policy['format'] != 2 or policy['unclassified'] != 'error':
        raise ValueError('Unsupported grounding policy')
    identifier=identifier.casefold()
    rules={key.casefold():value for key,value in policy['exceptions'].items()}
    if identifier in rules:
        rule=rules[identifier]
        if rule['mode'] not in ('scripted_airborne','flying','levitating','swimming','authored_dead') or not rule.get('reason'):
            raise ValueError('Unknown or undocumented initial support state')
        return rule['mode']
    if identifier in policy['ground_npcs']:return 'ground'
    raise ValueError('Unclassified initial support state: '+identifier)


def fields(identifier):
    if any(c in identifier for c in ('"','\n','\r','\0')):raise ValueError('Invalid source ID')
    return {'aw_source_id': identifier, 'aw_ground_mode': int(initial_state(identifier)!='ground')}


def annotate(maps, master):
    """Upgrade retained BSP entity metadata without changing geometry or placement."""
    refs = {}
    for kind, flags, raw in records(Path(master).read_bytes()):
        if kind != 'CELL': continue
        for ref in cell_data(list(subrecords(raw)))['refs']:
            if not ref.get('deleted'): refs[ref['number']] = ref['id']
    report = []
    for path in sorted(Path(maps).glob('*.bsp')):
        data = lumps(path.read_bytes()); changed = [False]
        def update(match):
            block = match[0]; e = dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', block))
            if e.get('classname') not in ('aw_npc','aw_corpse'): return block
            identifier = refs.get(int(float(e.get('aw_ref', '0')))) or INTRO_IDS.get(int(float(e.get('aw_intro_role',0))))
            if not identifier:raise ValueError(path.name+': actor has no original identity')
            values = fields(identifier)
            for key in values: block = re.sub(r'\n"'+key+r'"\s+"[^"\n]*"', '', block)
            addition = ''.join(f'"{key}" "{value}"\n' for key, value in values.items())
            changed[0] = True
            report.append(dict(map=path.stem, reference=e.get('aw_ref'), **values))
            return block[:-1]+addition+'}'
        text = re.sub(r'\{[^{}]*\}', update, data[0].decode('cp1252'))
        if changed[0]: data[0] = text.encode('cp1252'); path.write_bytes(pack_lumps(data))
    return report


def bake_ground(maps):
    """Fit rendered idle soles to converted support, preserving authored inputs.

    Try vertical correction first, then the nearest half-unit XY point within
    32 units. Never cross an owner core, wall, unsupported gap, or a storey-sized
    support change. The independent packaged audit remains the release gate.
    """
    from check_actor_ground import entities, model_frames, contact_samples, owner
    import math
    import struct
    import itertools
    maps=Path(maps)
    @lru_cache(maxsize=3)
    def scene(name): return Scene((maps/(name+'.bsp')).read_bytes(),hull=0)
    @lru_cache(maxsize=128)
    def soles(model,angles,intro):
        name=Path(model)
        if name.is_absolute() or '..' in name.parts:raise ValueError('Unsafe actor model path')
        return tuple(contact_samples(model_frames((maps.parent/name).read_bytes()),angles,intro))
    offsets=sorted(((x*.5,y*.5) for x in range(-64,65) for y in range(-64,65)
                    if x*x+y*y<=4096),key=lambda p:(p[0]*p[0]+p[1]*p[1],p))
    results={};report=[]
    class SupportScene(Scene):
        def __init__(self, original, bounds):
            # Read-only collision data shared with the full scene. Bounds are
            # used only to propose placements; the final audit is unfiltered.
            self.__dict__.update(original.__dict__)
            self.bounds=bounds

        def _trace_brushes(self, start, end):
            for brush,box in self.bounds:
                if box is None or all(max(start[k],end[k])>=box[k] and
                        min(start[k],end[k])<=box[k+2] for k in (0,1)):
                    yield brush
    def contact(s,point,samples):
        for local in samples:
            foot=[point[k]+local[k] for k in range(3)]
            hit=s.floor((foot[0],foot[1],foot[2]+2),6)
            if hit['status']!='supported' or not -.5<=foot[2]-hit['height']<=1.0:return False
        return True
    def neighbourhood(name,point,samples):
        # Conservative visible-model bounds accelerate candidate searches only.
        # World collision is always retained. The final independent audit traces
        # the complete unfiltered scene and can reject any proposed placement.
        raw=(maps/(name+'.bsp')).read_bytes();all_scene=scene(name)
        models=list(struct.iter_unpack('<9f7i',lumps(raw)[14]))
        objects=[dict(model='*0')]+[e for e in entities(raw)
                 if e.get('classname')=='func_wall' and re.fullmatch(r'\*\d+',e.get('model',''))]
        reach=34+max(max(abs(v[0]),abs(v[1])) for v in samples)
        selected=[]
        for brush,e in zip(all_scene.brushes,objects):
            root,origin,basis,ref=brush;m=models[int(e['model'][1:])]
            corners=[tuple(origin[i]+sum(v[j]*basis[j][i] for j in range(3)) for i in range(3))
                     for v in itertools.product(*[(m[k],m[k+3]) for k in range(3)])]
            if e['model']=='*0' or all(max(v[k] for v in corners)>=point[k]-reach and
                    min(v[k] for v in corners)<=point[k]+reach for k in (0,1)):
                # Leave a small numerical margin at transformed model edges.
                box=None if e['model']=='*0' else tuple(
                    [min(v[k] for v in corners)-.01 for k in (0,1)]+
                    [max(v[k] for v in corners)+.01 for k in (0,1)])
                selected.append((brush,box))
        return SupportScene(all_scene,selected)
    def path_clear(s,old,new,base):
        distance=math.hypot(new[0]-old[0],new[1]-old[1])
        previous=[old[0],old[1],base+16]
        height=base
        for step in range(1,max(1,math.ceil(distance/2))+1):
            f=step/max(1,math.ceil(distance/2))
            xy=[old[k]+(new[k]-old[k])*f for k in range(2)]
            hit=s.floor([*xy,height+8],16)
            if hit['status']!='supported' or abs(hit['height']-height)>4.5:return False
            point=[*xy,hit['height']+16]
            if s.trace(previous,point):return False
            previous=point;height=hit['height']
        return True
    def fit(name,e,authored,angles):
        samples=soles(e['model'],angles,bool(float(e.get('aw_intro_role',0))))
        s=neighbourhood(name,authored,samples)
        center=s.floor([*authored[:2],authored[2]+8],40)
        result=dict(map=name,reference=e.get('aw_ref'),source_id=e.get('aw_source_id'),
                    name=e.get('netname'),authored_origin=authored,authored_z=authored[2],
                    status=center['status'],support_reference=center.get('reference'))
        if center['status']!='supported':return result
        original=[*authored[:2],center['height']+.25]
        original=[round(v,5) for v in original]
        # Retain already valid original placements exactly.
        if contact(s,original,samples):
            result.update(placed_origin=original,placed_z=original[2],mesh_contact='unchanged',attempts=0)
            return result
        for attempt,(dx,dy) in enumerate(offsets,1):
            candidate=[authored[0]+dx,authored[1]+dy,0]
            try: target=owner(maps,name,candidate)
            except ValueError: continue
            if target!=name:continue
            support=s.floor([*candidate[:2],authored[2]+8],40)
            if support['status']!='supported' or abs(support['height']-center['height'])>16:continue
            low=authored[2]-32;high=authored[2]+8
            for local in samples:
                hit=s.floor([candidate[0]+local[0],candidate[1]+local[1],support['height']+local[2]+8],24)
                if hit['status']!='supported':low=math.inf;break
                low=max(low,hit['height']-local[2]-.48)
                high=min(high,hit['height']-local[2]+.98)
                if low>high:break
            if low>high:continue
            candidate[2]=min(high,max(low,original[2]))
            candidate=[round(v,5) for v in candidate]
            if not contact(s,candidate,samples) or not path_clear(s,original,candidate,center['height']):continue
            result.update(placed_origin=candidate,placed_z=candidate[2],mesh_contact='fitted',attempts=attempt,
                          correction_from_origin_grounding=[round(candidate[k]-original[k],5) for k in range(3)])
            return result
        result.update(status='unresolved-mesh-contact',attempts=len(offsets));return result
    for path in sorted(maps.glob('*.bsp')):
        data=lumps(path.read_bytes());changed=[False]
        def update(match):
            block=match[0];e=dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"',block))
            if e.get('classname')!='aw_npc' or float(e.get('aw_ground_mode',0)):return block
            point=list(map(float,e['origin'].split()))
            authored=list(map(float,e.get('aw_authored_origin',e['origin']).split()))
            authored[2]=float(e.get('aw_authored_z',authored[2]))
            angles=tuple(map(float,e.get('angles','0 0 0').split()))
            if len(authored)!=3 or not all(map(math.isfinite,authored)):raise ValueError('Invalid authored position')
            selected=owner(maps,path.stem,authored)
            key=(selected,e.get('aw_ref'),tuple(authored),angles,e['model'])
            if key not in results:
                results[key]=fit(selected,e,authored,angles);report.append(results[key])
                print('Actor support:',selected,e.get('aw_ref','intro'),results[key].get('mesh_contact',results[key]['status']),flush=True)
            result=results[key]
            # Never leave stale certification on an unresolved placement.
            for field in ('aw_ground_valid','aw_ground_baked','aw_authored_origin','aw_authored_z'):
                block=re.sub(r'\n"'+field+r'"\s+"[^"\n]*"','',block)
            placed=result.get('placed_origin')
            if placed is not None:
                block=re.sub(r'"origin"\s+"[^"\n]*"','"origin" "'+' '.join(f'{v:.5f}' for v in placed)+'"',block)
                block=block[:-1]+'"aw_ground_valid" "1"\n"aw_ground_baked" "'+' '.join(f'{v:.5f}' for v in placed)+'"\n}'
            addition='"aw_authored_origin" "'+' '.join(f'{v:.5f}' for v in authored)+'"\n'+f'"aw_authored_z" "{authored[2]:.5f}"\n'
            changed[0]=True
            return block[:-1]+addition+'}'
        text=re.sub(r'\{[^{}]*\}',update,data[0].decode('cp1252'))
        if changed[0]:data[0]=text.encode('cp1252');path.write_bytes(pack_lumps(data))
    return report
