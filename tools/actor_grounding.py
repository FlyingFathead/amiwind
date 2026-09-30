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
    """Resolve each Balmora resident in its owner BSP, then share that position.

    Render-overlap copies can lack the supporting architectural collision. Never
    ground those copies independently against their reduced collision scene.
    Interior/other complete scenes use their own collision. Preserve authored Z
    and report unresolved cases; do not silently increase the correction bound.
    """
    maps=Path(maps);regions={}
    for area in ('balmora','seyda'):
        directory=maps.parent/(area+'-regions.txt');regions[area]=[]
        if directory.is_file():
            for line in directory.read_text().splitlines()[1:]:
                v=line.split();regions[area].append((v[0],list(map(float,v[1:5]))))
    @lru_cache(maxsize=3)
    def scene(name): return Scene((maps/(name+'.bsp')).read_bytes(),hull=0)
    results={};report=[]
    for path in sorted(maps.glob('*.bsp')):
        raw=path.read_bytes();data=lumps(raw);changed=[False]
        area=next((a for a,prefix in (('balmora','bm'),('seyda','sn'))
                   if path.stem==a or (path.stem.startswith(prefix) and path.stem[2:].isdigit())),None)
        def update(match):
            block=match[0];e=dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"',block))
            if e.get('classname')!='aw_npc' or float(e.get('aw_ground_mode',0)):return block
            point=list(map(float,e['origin'].split()));authored=float(e.get('aw_authored_z',point[2]))
            selected=path.stem
            if area:
                selected=next((name for name,b in regions[area] if b[0]<=point[0]<b[2] and b[1]<=point[1]<b[3]),None)
                if selected is None:return block
            key=(selected,e.get('aw_ref'),*point[:2],authored)
            if key not in results:
                hit=scene(selected).floor([*point[:2],authored+8],40)
                if 'reference' in hit:hit['support_reference']=hit.pop('reference')
                result=dict(map=selected,reference=e.get('aw_ref'),source_id=e.get('aw_source_id'),
                            name=e.get('netname'),authored_z=authored,**hit)
                if hit['status']=='supported':result['placed_z']=hit['height']+.25
                results[key]=result;report.append(result)
            result=results[key]
            if 'placed_z' not in result:return block
            point[2]=result['placed_z'];changed[0]=True
            block=re.sub(r'"origin"\s+"[^"\n]*"','"origin" "'+' '.join(f'{v:.5f}' for v in point)+'"',block)
            block=re.sub(r'\n"aw_authored_z"\s+"[^"\n]*"','',block)
            return block[:-1]+f'"aw_authored_z" "{authored:.5f}"\n'+'}'
        text=re.sub(r'\{[^{}]*\}',update,data[0].decode('cp1252'))
        if changed[0]:data[0]=text.encode('cp1252');path.write_bytes(pack_lumps(data))
    return report
