#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Stage original flora over bounded town BSPs using exact source bindings."""
import json
import math
from pathlib import Path
import re
import shutil

from player_hull import lumps
from prepare_world_flora import digest, identity, overlay_region
from prepare_tree_sprites import unique_reference_numbers


def load(value):
    return value if isinstance(value, dict) else json.loads(Path(value).read_text(encoding='utf-8'))


def normalize(model):
    return model.replace('\\', '/').casefold().removeprefix('meshes/')


def entity_fields(raw):
    return [dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', block))
            for block in re.findall(r'\{[^{}]*\}', bytes(lumps(raw)[0]).rstrip(b'\0').decode('cp1252'))]


def original_match(ref, original, model):
    """Source number alone is insufficient: verify model, cell and full transform."""
    if normalize(model['source']) != normalize(original['model']) or ref.get('cell') != original['cell']:
        raise ValueError('Town flora source reference model/cell differs from base master')
    if ref.get('id', '').casefold() != original['id'].casefold():
        raise ValueError('Town flora source record ID differs from base master')
    for field in ('position', 'rotation_radians'):
        if len(ref[field]) != 3 or any(not math.isfinite(v) or abs(v-original[field][k]) > 1e-5 for k,v in enumerate(ref[field])):
            raise ValueError('Town flora source transform differs from original: ' + field)
    if ref['scale'] != original['scale']:
        raise ValueError('Town flora source scale differs from original')


def derive_bindings(raw, source_index, scene_report, receipt, flora_index, entry):
    """Resolve real mesh aw_ref and legacy m0xx SPR entities to original keys.

    The legacy preview used model XY centre, yaw only, and scale1, accepting
    source scale within .02 of1. Reconstruct that exact old representation;
    new placements still use the complete original transforms.
    """
    unique_reference_numbers(source_index['references'])
    unique_reference_numbers(receipt['placements'])
    originals={r['number']:r for r in receipt['placements']}
    source_refs={r['number']:r for r in source_index['references']}
    global_models={normalize(m['source']):m for m in flora_index['models']}
    assets={a['model']:a for a in receipt['assets']}
    reports={normalize(m['model']):m for m in scene_report.get('models',[])} if scene_report else {}
    candidates={}
    for mi,model in enumerate(source_index['models']):
        name=normalize(model['source'])
        if name in global_models and reports.get(name,{}).get('kind','').casefold() in ('sprite','spr'):
            if model.get('source_sha256') != global_models[name].get('source_sha256') or not model.get('source_sha256'):
                raise ValueError('Legacy sprite source model hash lacks an exact base-model match')
            candidates[f'progs/m{mi:03}.spr']=(mi,name)
    seen=set();retained=[];bindings=[]
    for fields in entity_fields(raw):
        path=fields.get('model','')
        if path.startswith('*') and 'aw_ref' in fields:
            number=int(fields['aw_ref'])
            if number not in originals:continue
            original=originals[number]
            if number not in source_refs:raise ValueError('Existing town flora mesh lacks source reference binding')
            ref=source_refs[number];model=source_index['models'][ref['model_index']]
            original_match(ref,original,model)
            global_model=global_models[normalize(original['model'])]
            if not model.get('source_sha256') or model['source_sha256']!=global_model.get('source_sha256'):
                raise ValueError('Existing town flora mesh source NIF hash differs')
            expected=[original['position'][k]*.25-entry['origin'][k] for k in range(3)]
            point=list(map(float,fields.get('origin','').split()))
            if len(point)!=3 or any(not math.isfinite(v) or abs(v-expected[k])>.001 for k,v in enumerate(point)):
                raise ValueError('Existing town flora mesh pose differs from source binding')
            key=identity(original['source_key'])
            if key in seen:raise ValueError('Duplicate existing town flora representation')
            seen.add(key);retained.append(original['source_key'])
        elif fields.get('classname')=='aw_static' and path in candidates:
            mi,name=candidates[path]
            if name not in assets:raise ValueError('Legacy sprite model lacks shared bake centre receipt')
            centre=assets[name]['source_xy_bake_center']
            point=list(map(float,fields.get('origin','').split()))
            scale=float(fields.get('aw_scale',1))
            matches=[]
            for ref in source_index['references']:
                if ref['model_index']!=mi or abs(ref['scale']-1)>.02:continue
                original=originals.get(ref['number'])
                if original is None:continue
                original_match(ref,original,source_index['models'][mi])
                z=ref['rotation_radians'][2];co,si=math.cos(z),math.sin(z)
                position=[ref['position'][0]+centre[0]*co+centre[1]*si,
                          ref['position'][1]-centre[0]*si+centre[1]*co,ref['position'][2]]
                expected=[position[k]*.25-entry['origin'][k] for k in range(3)]
                if len(point)==3 and scale==1 and all(math.isfinite(point[k]) and abs(point[k]-expected[k])<=.001 for k in range(3)):
                    matches.append(original)
            if len(matches)!=1:raise ValueError('Legacy town flora sprite has missing or ambiguous original source binding')
            original=matches[0];key=identity(original['source_key'])
            if key in seen:raise ValueError('Duplicate existing town flora representation')
            seen.add(key)
            bindings.append({'source_key':original['source_key'],'source_model':name,
                             'model':path,'origin':point,'scale':scale})
        elif fields.get('classname')=='aw_flora':
            raise ValueError('Town flora already installed; rebuild from original bounded BSPs')
    return retained,bindings


def install(scene, flora, palette, *, entries, town_source_index, town_scene_report=None,
            collision_packing='adaptive', work_dir=None):
    """Validate and stage every candidate before replacing any installed map.

    entries: name/coverage/origin plus optional source_bsp; scene is the private
    image scene containing id1/maps. Provide Balmora source index and Seyda
    source index+alias scene report separately per call. Existing meshes remain.
    """
    scene,flora,palette=map(Path,(scene,flora,palette))
    receipt=load(flora/'tree-sprites.json');index=load(flora/'source/scenery-index.json')
    source_index=load(town_source_index);scene_report=load(town_scene_report) if town_scene_report else None
    if digest(palette)!=receipt['palette_sha256'] or index.get('master_sha256')!=receipt['master_sha256']:
        raise ValueError('Town flora source master/palette does not match staged bake')
    names=[e['name'] for e in entries]
    if not names or len(names)!=len(set(names)) or not all(re.fullmatch(r'(?:sn|bm)[0-9]{3}|intro_docks|sncourt',n) for n in names):
        raise ValueError('Invalid or duplicate bounded town map names')
    work=Path(work_dir) if work_dir else scene/'town-flora'/names[0][:2]
    work.mkdir(parents=True,exist_ok=False)
    replacements=[];reports=[]
    for entry in entries:
        if len(entry.get('origin',[]))!=3 or not all(math.isfinite(v) for v in entry['origin']):
            raise ValueError('Town entry needs explicit finite source-to-engine origin')
        target=scene/'id1/maps'/(entry['name']+'.bsp')
        source=Path(entry.get('source_bsp',target));raw=source.read_bytes()
        retained,bindings=derive_bindings(raw,source_index,scene_report,receipt,index,entry)
        local=work/entry['name'];candidate=local/'scene.bsp'
        report=overlay_region(source,candidate,flora,index,receipt,entry,palette,
                              retained_mesh_keys=retained,legacy_sprite_bindings=bindings,
                              collision_packing=collision_packing,admission_profile='town')
        report['retained_existing_mesh_keys']=retained
        (local/'conversion.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        reports.append(report);replacements.append((candidate,target))
    used={r['model'] for report in reports for r in report['source_references'] if r['effective_representation']=='sprite'}
    for asset in receipt['assets']:
        if asset['model'] not in used:continue
        source=flora/asset['sprite_asset_name'];target=scene/'id1'/asset['sprite_asset_name']
        if digest(source)!=asset['sha256'] or (target.exists() and digest(target)!=asset['sha256']):
            raise ValueError('Town shared sprite differs from bake/image palette')
        replacements.append((source,target))
    for source,target in replacements:
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        if digest(target)!=digest(source):raise ValueError('Town flora staging readback failed')
    result={'format':'AmiWind bounded town flora staging 1','runtime_validation':'pending',
            'admission_profile':'town','final_heap_gate_required':True,'final_heap_verified':False,
            'final_transport_gate_required':True,
            'maps':reports,'unique_original_refs':len({identity(r['source_key']) for row in reports for r in row['source_references']}),
            'retained_existing_mesh_originals':len({identity(k) for row in reports for k in row['retained_existing_mesh_keys']}),
            'removed_legacy_sprite_originals':len({identity(k) for row in reports for k in row['removed_legacy_sprite_keys']}),
            'collision_packing':collision_packing,'master_sha256':receipt['master_sha256'],'palette_sha256':receipt['palette_sha256']}
    (work/'town-flora.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result
