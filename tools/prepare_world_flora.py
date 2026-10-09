#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Layer original flora visuals/collision over retained private world scenery.

Outputs contain owned data and must remain private. Scale-aware aw_flora runtime
and image installation are separate gates; no target acceptance is implied.

Explicit adaptive collision packing retains passing default candidates. It
retries aggregation only after an entity or model-slot reserve failure (vf2098), and rejects
any reserve/content failure in that retry. Passing vf0634 keeps shared default
hulls. No limits or source content are reduced; target timing remains a gate.
"""
import argparse
import contextlib
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import time

from build_jobs import add_jobs, resolve_jobs
from build_parallel import ordered_map
from engine_limits import limits as engine_limits
from player_hull import lumps, pack_lumps
from world_scenery import region_references
from world_flora_policy import source_key

_CACHE = {}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def identity(key):
    return json.dumps(key, separators=(',', ':'))


def mesh_profile(model, refs, mode='mesh'):
    """Converter profile of one flora model placed by refs (the overlay's and the CHIM builder's)."""
    collision_none = next(r['source_collision']['mode'] == 'nonsolid' for r in refs)
    profile = {'texture_size': 32, 'collision_only': mode == 'collision_only', 'collision_none': collision_none}
    if mode == 'mesh':
        profile['ratio'] = min(1., 120 / max(1, model['triangles']))
    if mode == 'mesh' and any(r.get('kind') == 'small_mushroom' for r in refs):
        profile['preserve_shared_seams'] = True
    return profile


def effective_representation(ref):
    if ref.get('requires_interaction'):
        return 'mesh_pending_interaction'
    return ref['renderer_policy']


def sprite_entity(ref, asset, origin, world_scale=.25):
    """Scale/rotate model XY bake centre; retain exact source transforms in receipt."""
    from prepare_scenery import reference_rotation
    import numpy as np
    path = asset['sprite_asset_name']
    if len(path.encode('ascii')) >= 64 or not re.fullmatch(r'progs/aw_flora/f_[0-9a-f]{16}\.spr', path):
        raise ValueError('Invalid flora runtime model path')
    offset = reference_rotation(ref) @ np.array([*asset['source_xy_bake_center'], 0.]) * ref['scale']
    point = [(ref['position'][k] + float(offset[k])) * world_scale - origin[k] for k in range(3)]
    if ref['scale'] <= 0 or not all(math.isfinite(v) and abs(v) <= 3.4028234663852886e38 for v in point + [ref['scale']] + ref['rotation_radians']):
        raise ValueError('Invalid flora runtime sprite transform')
    if struct.unpack('<f', struct.pack('<f', ref['scale']))[0] <= 0:
        raise ValueError('Flora scale underflows float32 protocol')
    # Type2 deliberately faces the viewer; original source rotation stays in the
    # receipt and the separately transformed collision, not discarded metadata.
    fields = {'classname': 'aw_flora', 'model': path, 'aw_scale': format(ref['scale'], '.9g'),
              'aw_ref': str(ref['number']), 'origin': ' '.join(format(v, '.9g') for v in point),
              'angles': '0 0 0'}  # view-parallel; do not imply a TES-to-Quake Euler mapping
    return '{\n' + '\n'.join('"' + k + '" "' + v + '"' for k, v in fields.items()) + '\n}'


def remove_legacy_sprites(raw, bindings, selected):
    """Bind old sprites by source key, source-model mapping AND model/pose/scale."""
    if not bindings:
        return raw, []
    available = {identity(r['source_key']): r for r in selected}
    seen, removed = set(), []
    data = lumps(raw)
    def replace(match):
        block = match.group(); fields = dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', block))
        if fields.get('classname') != 'aw_static':
            return block
        matches = []
        for binding in bindings:
            key = identity(binding['source_key'])
            ref = available.get(key)
            if ref is None or binding['source_model'].replace('\\', '/').casefold().removeprefix('meshes/') != ref['model']:
                raise ValueError('Legacy sprite binding lacks an exact original source-model mapping')
            if fields.get('model') != binding['model'] or 'origin' not in fields:
                continue
            point = list(map(float, fields['origin'].split()))
            if len(point) == 3 and all(abs(point[k] - binding['origin'][k]) <= .001 for k in range(3)) and float(fields.get('aw_scale', 1)) == binding['scale']:
                matches.append(binding)
        if len(matches) > 1:
            raise ValueError('Ambiguous legacy sprite source binding')
        if not matches:
            return block
        binding = matches[0]; key = identity(binding['source_key'])
        if key in seen:
            raise ValueError('Duplicate legacy sprite representation')
        seen.add(key);removed.append(binding['source_key']);return ''
    text = re.sub(r'\{[^{}]*\}', replace, data[0].rstrip(b'\0').decode('cp1252'))
    if seen != {identity(b['source_key']) for b in bindings}:
        raise ValueError('Required legacy sprite binding was not found')
    data[0] = bytearray((text + '\0').encode('cp1252'))
    return pack_lumps(data), removed


def verify_retained_content(before, after):
    """Old source models, textures, faces, collision and LAND remain semantic-identical."""
    from replace_bsp_world import texture_blobs
    a, b = lumps(before), lumps(after)
    for index in (3, 4, 6, 8, 10, 11, 12, 13, 14):
        if not b[index].startswith(a[index]):
            raise ValueError('Flora overlay altered retained BSP lump ' + str(index))
    textures_a, textures_b = texture_blobs(a[2]), texture_blobs(b[2])
    if textures_b[:len(textures_a)] != textures_a:
        raise ValueError('Flora overlay altered retained texture payloads')
    for section, stride, fmt in ((5, 24, '<i'), (9, 8, '<i'), (7, 20, '<H')):
        prefix = struct.calcsize(fmt)
        for offset in range(0, len(a[section]), stride):
            old = struct.unpack_from(fmt, a[section], offset)[0]
            new = struct.unpack_from(fmt, b[section], offset)[0]
            if a[1][old*20:(old+1)*20] != b[1][new*20:(new+1)*20] or a[section][offset+prefix:offset+stride] != b[section][offset+prefix:offset+stride]:
                raise ValueError('Flora overlay altered retained face/collision semantics')
    return {'retained_models': len(a[14]) // 64, 'retained_faces': len(a[7]) // 20,
            'retained_textures': len(textures_a), 'retained_content': 'verified'}


def aggregate_collision(index, refs, prepared, entry):
    """Opt-in comparison: combine exact transformed resident convex pieces.

    This reduces collision entity count, at the cost of a longer per-entity
    union traversal. Explicit adaptive mode accepts it only after a default
    entity/model-slot reserve failure, with all reserves and retained content verified.
    """
    import numpy as np
    from prepare_scenery import reference_rotation
    from prepare_mesh_bsp import _prepare_placement
    pieces=[]
    for ref in refs:
        delta=(np.array(ref['position'])-np.array([entry['origin'][0]/.25,entry['origin'][1]/.25,0.]))*.25
        rotation=reference_rotation(ref)
        source_data=prepared[ref['model_index']]
        _,baseline_parts,_,_=_prepare_placement((ref,source_data,32,[v/.25 for v in entry['origin'][:2]],None))
        yaw=-ref['rotation_radians'][2];co,si=math.cos(yaw),math.sin(yaw)
        runtime=np.array([[co,-si,0],[si,co,0],[0,0,1]])
        if len(baseline_parts)!=len(source_data[3]):raise ValueError('Collision source piece count changed')
        for part,(points,hull,ids,error) in enumerate(source_data[3]):
            transformed=points@rotation.T*ref['scale']+delta
            expected=baseline_parts[part][0]@runtime.T+delta
            if not np.isfinite(transformed).all() or not np.allclose(transformed,expected,rtol=1e-12,atol=1e-9):
                raise ValueError('Aggregate collision changes original transformed convex geometry')
            low,high=transformed.min(axis=0),transformed.max(axis=0)
            if all(high[k]>=entry['coverage'][0][k] and low[k]<=entry['coverage'][1][k] for k in range(2)):
                pieces.append((transformed,None,ids,error))
    if not pieces:return None
    vertices=np.zeros((sum(len(p[0]) for p in pieces),9))
    vertices[:,:3]=np.vstack([p[0] for p in pieces])/.25
    model={'source':'meshes/aw_flora_collision.nif','triangles':0,'materials':[]}
    ref={**refs[0],'model_index':0,'scale':1.,'rotation_radians':[0.,0.,0.],
         'position':[entry['origin'][0]/.25,entry['origin'][1]/.25,0.]}
    profile={'collision_only':True,'texture_size':32}
    subset={**index,'models':[model],'references':[ref],
            'groups':{'world_flora':{'references':[],'visual_profiles':{model['source']:profile}}}}
    data=(vertices,np.empty((0,4),dtype=int),[],pieces,
          {'representation':'collision_only aggregate comparison','original_collision_instances':len(refs),
           'world_convex_geometry_equivalence':'verified against original per-instance placement and runtime yaw'})
    return subset,{0:data},[ref['number']]


# static_entities: the engine's budget (client.h MAX_STATIC_ENTITIES, tools/engine_limits.py) less 32
# for the scene's own statics.
RESERVES = {'models_plus_sprites': 240, 'entities': 550, 'static_entities': engine_limits()['max_static_entities'] - 32,
            'nodes': 32767, 'clipnodes': 32767, 'bytes': 4 * 1024 * 1024}


class FloraReserveError(ValueError):
    def __init__(self, report):
        self.report = report
        super().__init__(report)


def admission_contract(profile):
    if profile not in ('world','town'):
        raise ValueError('Unknown flora admission profile')
    return {'profile':profile,'file_budget_bytes':RESERVES['bytes'] if profile=='world' else None,
            'final_target_abi_gate':'required; source estimate only, target gameplay remains pending',
            'map_allowance_bytes':6*1024*1024,'baseline_reserve_bytes':3*1024*1024,
            'safety_headroom_bytes':2*1024*1024,
            'final_heap_verified':False,'final_transport_gate':'required; complete runtime signon and all static/model capacities'}


def reserve_violations(metrics, admission_profile='world'):
    admission_contract(admission_profile)
    limits=dict(RESERVES)
    # Town BSPs use the engine's unsigned clipnode encoding; the lower world
    # conversion reserve remains unchanged. Final ABI heap gate is mandatory.
    if admission_profile=='town':limits['clipnodes']=65520
    violations=[{'metric':key,'actual':metrics[key],'limit':limit}
                for key,limit in limits.items()
                if (key!='bytes' or admission_profile=='world') and metrics[key]>limit]
    if metrics.get('catalogue_placements',0)>1000:
        violations.append({'metric':'catalogue_placements','actual':metrics['catalogue_placements'],'limit':1000})
    if metrics.get('visible_entity_floor',0)>1112:
        violations.append({'metric':'visible_entity_floor','actual':metrics['visible_entity_floor'],'limit':1112})
    return violations


def overlay_region(source, out, flora, index, receipt, entry, palette,
                   retained_mesh_keys=(), legacy_sprite_bindings=(), aggregate_sprite_collision=False,
                   collision_packing='per_instance', admission_profile='world'):
    """Explicit adaptive mode retries only an entity or model-slot reserve failure.

    Candidate preservation and every reserve/content check remain mandatory.
    The accepted source placement set is never reduced to fit a budget.
    """
    admission_contract(admission_profile)
    if admission_profile=='town' and not re.fullmatch(r'(?:sn|bm)[0-9]{3}|intro_docks|sncourt',entry['name']):
        raise ValueError('Town admission requires an explicit bounded town map')
    if collision_packing not in ('per_instance', 'adaptive'):
        raise ValueError('Unknown flora collision packing mode')
    if collision_packing == 'adaptive' and aggregate_sprite_collision:
        raise ValueError('Adaptive packing and forced aggregate comparison are exclusive')
    kwargs={'retained_mesh_keys':retained_mesh_keys,'legacy_sprite_bindings':legacy_sprite_bindings,'admission_profile':admission_profile}
    if collision_packing != 'adaptive':
        result=_overlay_candidate(source,out,flora,index,receipt,entry,palette,
                                  aggregate_sprite_collision=aggregate_sprite_collision,**kwargs)
        result['collision_packing']={'mode':'aggregate_comparison' if aggregate_sprite_collision else 'per_instance',
                                    'selected_strategy':'aggregate' if aggregate_sprite_collision else 'per_instance',
                                    'attempts':[{'strategy':'aggregate' if aggregate_sprite_collision else 'per_instance',
                                                 'metrics':result['reserve_metrics'],'status':'accepted'}]}
        return result
    destination=Path(out);destination.parent.mkdir(parents=True,exist_ok=True)
    attempts=[]
    for strategy in ('per_instance','aggregate'):
        local=destination.parent/('collision-'+strategy);local.mkdir(exist_ok=False)
        candidate=local/'scene.bsp'
        try:
            result=_overlay_candidate(source,candidate,flora,index,receipt,entry,palette,
                                      aggregate_sprite_collision=strategy=='aggregate',**kwargs)
        except FloraReserveError as error:
            attempts.append({'strategy':strategy,'status':'rejected',**error.report,
                             'candidate_directory':str(local)})
            retry=strategy=='per_instance' and any(v['metric'] in ('entities','models_plus_sprites') for v in error.report['violations'])
            if retry:continue
            failure={'mode':'adaptive','selected_strategy':None,'attempts':attempts}
            (destination.parent/'collision-packing.json').write_text(json.dumps(failure,indent=2)+'\n',encoding='utf-8')
            raise FloraReserveError(failure) from error
        attempts.append({'strategy':strategy,'status':'accepted','metrics':result['reserve_metrics'],
                         'retained_content':result['retained_content']})
        result['collision_packing']={'mode':'adaptive','selected_strategy':strategy,'attempts':attempts}
        os.replace(candidate,destination)
        (destination.parent/'collision-packing.json').write_text(json.dumps(result['collision_packing'],indent=2)+'\n',encoding='utf-8')
        return result
    raise AssertionError('Adaptive collision selection exhausted unexpectedly')


def _overlay_candidate(source, out, flora, index, receipt, entry, palette,
                   retained_mesh_keys=(), legacy_sprite_bindings=(), aggregate_sprite_collision=False, admission_profile='world'):
    """Reusable town/world consumer: source BSP + coverage + engine-world origin.

    Existing Balmora meshes can be retained by exact source key. Seyda legacy
    sprites require explicit source-model/path/pose/scale bindings for replacement.
    """
    from prepare_mesh_bsp import append_meshes, _prepare_model
    selected = region_references(index, entry)
    from prepare_tree_sprites import unique_reference_numbers
    unique_reference_numbers(receipt['placements'])
    unique_reference_numbers(index['references'])
    original_refs = {r['number']: r for r in receipt['placements']}
    # Old yaw-only sprite quads can touch a town apron even when the original
    # fully tilted model bounds do not. Exact existing source bindings are
    # legitimate resident copies, not new/scattered placements. Preserve that
    # membership without changing terrain coverage or inventing source bounds.
    selected_numbers={r['number'] for r in selected}
    bound_extras=[]
    indexed={r['number']:r for r in index['references']}
    for key in [*retained_mesh_keys,*(b['source_key'] for b in legacy_sprite_bindings)]:
        number=key[-1];original=original_refs.get(number)
        if original is None or identity(key)!=identity(original['source_key']) or number not in indexed:
            raise ValueError('Existing town representation lacks exact original source key')
        if number in selected_numbers:continue
        ref=copy.deepcopy(indexed[number])
        ref['position'][2]-=entry['origin'][2]/.25
        for edge in ref['bounds']:edge[2]-=entry['origin'][2]/.25
        selected.append(ref);selected_numbers.add(number);bound_extras.append(key)
    selected.sort(key=lambda r:r['number'])
    for ref in selected:
        ref.update({k: original_refs[ref['number']][k] for k in
                    ('source_key', 'renderer_policy', 'requires_interaction', 'model')})
        ref['source_collision'] = original_refs[ref['number']]['source_collision']
    raw = Path(source).read_bytes();base_hash = hashlib.sha256(raw).hexdigest()
    raw, removed = remove_legacy_sprites(raw, legacy_sprite_bindings, selected)
    local = Path(out).parent;local.mkdir(parents=True, exist_ok=True)
    start = local / 'flora-input.bsp';start.write_bytes(raw);current = start
    packet = Path(flora) / 'source/scenery.mwpak';alias = local / 'scenery.mwpak'
    if not alias.exists():
        try:os.link(packet, alias)
        except OSError:shutil.copyfile(packet, alias)
    retained = {identity(k) for k in retained_mesh_keys}
    active = [r for r in selected if identity(r['source_key']) not in retained]
    stages = []
    for mode in ('mesh', 'collision_only'):
        refs = [r for r in active if (effective_representation(r) == 'sprite') == (mode == 'collision_only')
                and (mode != 'collision_only' or r['source_collision']['mode'] != 'nonsolid')]
        if not refs:
            continue
        profiles = {}
        prepared = {}
        for mi in {r['model_index'] for r in refs}:
            model = index['models'][mi]
            profile = mesh_profile(model, [r for r in refs if r['model_index'] == mi], mode)
            collision_none = profile['collision_none']
            profiles[model['source']] = profile
            key = (str(packet.resolve()), mi, mode, collision_none, bool(profile.get('preserve_shared_seams')))
            if key not in _CACHE:
                _, _CACHE[key] = _prepare_model((mi, model, profile, packet, index['textures']))
            prepared[mi] = _CACHE[key]
        subset = {**index, 'references': refs,
                  'groups': {'world_flora': {'references': [], 'visual_profiles': profiles}}}
        reference_numbers=[r['number'] for r in refs]
        if aggregate_sprite_collision and mode == 'collision_only':
            combined=aggregate_collision(index,refs,prepared,entry)
            if combined is None:continue
            subset,prepared,reference_numbers=combined
        (local / 'scenery-index.json').write_text(json.dumps(subset) + '\n', encoding='utf-8', newline='\n')
        destination = local / ('flora-' + mode + '.bsp')
        stages.append(append_meshes(current, destination, local, palette,
                       centre=[v / .25 for v in entry['origin'][:2]], jobs=1,
                       references=reference_numbers, prepared_models=prepared,
                       retain_dressing=True, collision_bounds=entry['coverage'],
                       map_identity=entry['name'],cell_identity=','.join(map(str,entry['cell'])) if entry.get('cell') else None,subcell_identity=entry['name'] if entry.get('subcell') is not None else None))
        current = destination
    data = lumps(current.read_bytes());assets = {a['model']: a for a in receipt['assets']}
    sprite_refs = [r for r in active if effective_representation(r) == 'sprite']
    entities = [sprite_entity(original_refs[r['number']], assets[r['model']], entry['origin']) for r in sprite_refs]
    data[0] = data[0].rstrip(b'\0') + ('\n' + '\n'.join(entities) + '\n\0').encode('ascii')
    final = pack_lumps(data);verification = verify_retained_content(raw, final)
    models = len(data[14]) // 64
    blocks = re.findall(rb'\{[^{}]*\}', data[0])
    static = sum(b'"classname" "aw_flora"' in block or b'"classname" "aw_static"' in block for block in blocks)
    precaches = {a['sprite_asset_name'] for a in receipt['assets'] if any(r['model'] == a['model'] for r in sprite_refs)}
    metrics={'models_plus_sprites':models+len(precaches),'bsp_models':models,'sprite_precaches':len(precaches),
             'entities':len(blocks),'static_entities':static,'nodes':len(data[5])//24,
             'clipnodes':len(data[9])//8,'bytes':len(final)}
    if admission_profile=='town':
        from scenery_admission import catalogue_count
        captured=catalogue_count(entry['name'],data[0])
        metrics['raw_entity_records']=metrics['entities']
        metrics['catalogue_placements']=captured
        metrics['entities']-=captured
        metrics['visible_entity_floor']=metrics['raw_entity_records']-2
    violations=reserve_violations(metrics,admission_profile)
    if violations:
        failure={'name':entry['name'],'metrics':metrics,'limits':RESERVES,'violations':violations,
                 'admission':admission_contract(admission_profile),
                 'strategy':'aggregate' if aggregate_sprite_collision else 'per_instance',
                 'retained_content':verification,'reason':'reserves exceeded; no source content dropped'}
        (local/'reserve-failure.json').write_text(json.dumps(failure,indent=2)+'\n',encoding='utf-8')
        (local/'candidate-scene.bsp').write_bytes(final)
        raise FloraReserveError(failure)
    Path(out).write_bytes(final)
    source_records = [{**original_refs[r['number']], 'effective_representation':
        ('retained_existing_mesh' if identity(r['source_key']) in retained else effective_representation(r))} for r in selected]
    report = {'name': entry['name'], 'reserve_metrics':metrics, 'admission':admission_contract(admission_profile), 'base_sha256': base_hash, 'sha256': hashlib.sha256(final).hexdigest(),
              'bytes': len(final), 'bsp_models': models, 'entities': len(blocks), 'static_entities': static,
              'sprite_types': len(precaches), 'sprite_instances': len(sprite_refs),
              'mesh_pending_interaction_instances': sum(r['requires_interaction'] for r in selected),
              'interaction_status': 'not_implemented' if any(r['requires_interaction'] for r in selected) else 'not_required',
              'sprite_pixel_bytes': sum(a['pixel_bytes'] for a in assets.values() if a['sprite_asset_name'] in precaches),
              'nodes': len(data[5]) // 24, 'clipnodes': len(data[9]) // 8,
              'source_references': source_records, 'retained_content': verification,
              'static_transport_floor_bytes': 33 * len(sprite_refs),
              'static_transport_format': 'svc_aw_spawnstatic opcode1 + float-pose/scale payload32; total signon requires final runtime audit',
              'existing_aw_static_entities': sum(b'\"classname\" \"aw_static\"' in block for block in blocks),
              'func_wall_entities': sum(b'\"classname\" \"func_wall\"' in block for block in blocks),
              'actor_entities': sum(b'\"classname\" \"aw_npc\"' in block for block in blocks),
              'removed_legacy_sprite_keys': removed, 'collision_stages': stages,
              'existing_bound_original_refs_outside_source_bounds': bound_extras,
              'aggregate_sprite_collision': aggregate_sprite_collision,
              'unsupported_interactions': [r['source_key'] for r in selected if r['requires_interaction']]}
    for path in (start, local / 'flora-mesh.bsp', local / 'flora-collision_only.bsp', alias, local / 'scenery-index.json'):
        if path.exists() and path != Path(out):path.unlink()
    return report


def convert_region(task):
    terrain, base, flora, palette, out, entry, aggregate_sprite_collision, collision_packing = task
    receipt = json.loads((flora / 'tree-sprites.json').read_text(encoding='utf-8'))
    index = json.loads((flora / 'source/scenery-index.json').read_text(encoding='utf-8'))
    local = out / entry['name'];local.mkdir(exist_ok=False)
    try:
        with (local / 'conversion.log').open('w', encoding='utf-8') as log, contextlib.redirect_stdout(log):
            result = overlay_region(base / entry['name'] / 'scene.bsp', local / 'scene.bsp', flora,
                                    index, receipt, entry, palette, aggregate_sprite_collision=aggregate_sprite_collision, collision_packing=collision_packing)
    except (ValueError, OSError, struct.error, OverflowError) as error:
        result={'name':entry['name'],'conversion_status':'failed','error_type':type(error).__name__,
                'error':str(error),'reserve_report':getattr(error,'report',None)}
        (local/'conversion-failure.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        return result
    (local / 'conversion.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    return result


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def input_contract(terrain,base,flora,palette,receipt):
    hashes={name:digest(flora/name) for name in ('tree-sprites.json','source/scenery-index.json','source/scenery.mwpak')}
    hashes.update({'terrain_directory':digest(terrain/'world-regions.json'),
                   'base_receipt':digest(base/'world-scenery.json'),'palette':digest(palette),
                   'full_reference_set':canonical_hash(receipt['placements'])})
    for asset in receipt['assets']:
        actual=digest(flora/asset['sprite_asset_name'])
        if actual!=asset['sha256']:raise ValueError('Resume/current flora sprite hash mismatch')
        hashes[asset['sprite_asset_name']]=actual
    return {'format':'AmiWind flora input contract 1','hashes':hashes,'sha256':canonical_hash(hashes)}



def resume_contract_matches(previous, current, allow_region_changes=False):
    """Directory refinement may reuse maps only with unchanged owned inputs.

    Each map still verifies actual base/candidate bytes, all original refs,
    transforms, retained content and every reserve. Only the two container
    receipt hashes may differ; no palette/asset/full-reference change is waived.
    """
    if previous.get('sha256') != canonical_hash(previous.get('hashes', {})):
        return False
    if current.get('sha256') != canonical_hash(current.get('hashes', {})):
        return False
    ignored={'terrain_directory','base_receipt'} if allow_region_changes else set()
    return ({k:v for k,v in previous['hashes'].items() if k not in ignored} ==
            {k:v for k,v in current['hashes'].items() if k not in ignored})

def cached_region(resume,base,entry,receipt,index,collision_packing,aggregate_sprite_collision):
    """Validate bytes, every reserve, complete original refs and sprite transforms."""
    folder=resume/entry['name'];path=folder/'scene.bsp'
    report=json.loads((folder/'conversion.json').read_text(encoding='utf-8'))
    raw=path.read_bytes();source=(base/entry['name']/'scene.bsp').read_bytes()
    if report['name']!=entry['name'] or report['sha256']!=hashlib.sha256(raw).hexdigest() or report['base_sha256']!=hashlib.sha256(source).hexdigest() or report['bytes']!=len(raw):
        raise ValueError('Cached region bytes/base receipt mismatch')
    original={r['number']:r for r in receipt['placements']}
    selected=region_references(index,entry)
    expected=[{**original[r['number']],'effective_representation':effective_representation(original[r['number']])} for r in selected]
    if canonical_hash(expected)!=canonical_hash(report['source_references']):
        raise ValueError('Cached region source identities/transforms/policy differ')
    mode='aggregate_comparison' if aggregate_sprite_collision else collision_packing
    if report.get('collision_packing',{}).get('mode')!=mode:raise ValueError('Cached region packing mode differs')
    data=lumps(raw);blocks=re.findall(rb'\{[^{}]*\}',data[0])
    parsed=[dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"',block.decode('cp1252'))) for block in blocks]
    sprites=[r for r in expected if r['effective_representation']=='sprite'];assets={a['model']:a for a in receipt['assets']}
    want=[dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"',sprite_entity(r,assets[r['model']],entry['origin']))) for r in sprites]
    actual=[fields for fields in parsed if fields.get('classname')=='aw_flora']
    if canonical_hash(sorted(actual,key=lambda x:int(x['aw_ref'])))!=canonical_hash(sorted(want,key=lambda x:int(x['aw_ref']))):
        raise ValueError('Cached flora sprite original pose/scale/model differs')
    precaches={assets[r['model']]['sprite_asset_name'] for r in sprites}
    metrics={'models_plus_sprites':len(data[14])//64+len(precaches),'bsp_models':len(data[14])//64,
             'sprite_precaches':len(precaches),'entities':len(blocks),
             'static_entities':sum(f.get('classname') in ('aw_flora','aw_static') for f in parsed),
             'nodes':len(data[5])//24,'clipnodes':len(data[9])//8,'bytes':len(raw)}
    if reserve_violations(metrics):raise ValueError('Cached region exceeds current unchanged reserves')
    report['retained_content']=verify_retained_content(source,raw)
    report['reserve_metrics']=metrics
    return report


def prepare(terrain, base, flora, palette, out, jobs=None, only=None, aggregate_sprite_collision=False, collision_packing='per_instance', resume_from=None, adopt_legacy_resume_inputs=False, resume_unchanged_regions=False):
    from mwad.paths import ensure_external
    terrain, base, flora, palette = map(Path, (terrain, base, flora, palette))
    out = ensure_external(Path(out), 'private world flora overlay');out.mkdir(parents=True, exist_ok=False)
    directory = json.loads((terrain / 'world-regions.json').read_text(encoding='utf-8'))
    base_receipt = json.loads((base / 'world-scenery.json').read_text(encoding='utf-8'))
    receipt = json.loads((flora / 'tree-sprites.json').read_text(encoding='utf-8'))
    if base_receipt.get('diagnostic_subset') or receipt.get('diagnostic_subset'):
        raise ValueError('Full flora overlay requires full base scenery and flora census')
    if directory['master_sha256'] != receipt['master_sha256'] or digest(palette) != receipt['palette_sha256'] or receipt['palette_sha256'] != base_receipt['palette_sha256']:
        raise ValueError('Flora source master/palette differs from retained world')
    entries = directory['regions']
    expected_base = {r['name']: r for r in base_receipt['regions']}
    for entry in entries:
        if entry['name'] not in expected_base or digest(base / entry['name'] / 'scene.bsp') != expected_base[entry['name']]['sha256']:
            raise ValueError('Retained scenery region mismatch')
    if only:
        entries = [e for e in entries if e['name'] in only]
        if len(entries) != len(set(only)):raise ValueError('Unknown flora diagnostic region')
    started=time.monotonic();results=[];failures=[]
    contract=input_contract(terrain,base,flora,palette,receipt)
    (out/'input-contract.json').write_text(json.dumps(contract,indent=2)+'\n',encoding='utf-8')
    index=json.loads((flora/'source/scenery-index.json').read_text(encoding='utf-8'))
    staged_source=out/'source';staged_source.mkdir()
    for name in ('scenery.mwpak','scenery-index.json'):shutil.copyfile(flora/'source'/name,staged_source/name)
    shutil.copyfile(flora/'tree-sprites.json',out/'tree-sprites.json')
    resume=Path(resume_from) if resume_from else None;reuse=False
    adoption={'resume_from':str(resume) if resume else None,'reused':[],'regenerated':[],'current_contract_sha256':contract['sha256']}
    if resume:
        old=resume/'input-contract.json'
        if old.exists():
            previous=json.loads(old.read_text(encoding='utf-8'))
            reuse=resume_contract_matches(previous,contract,resume_unchanged_regions)
            adoption['historical_source_contract']=('owned input hashes matched; explicit directory refinement; each cached region revalidated' if resume_unchanged_regions else 'matched') if reuse else 'mismatch; regenerate'
        elif adopt_legacy_resume_inputs:
            reuse=True
            adoption['historical_source_contract']='not recorded; explicit supervisory adoption of unchanged original invocation inputs'
            adoption['validation']='current hashes + each candidate bytes/base/content/full source refs/sprite transforms/reserves; historical hashes not claimed'
        else:
            adoption['historical_source_contract']='not recorded; regenerate'
    pending=[]
    for entry in entries:
        if reuse:
            try:cached=cached_region(resume,base,entry,receipt,index,collision_packing,aggregate_sprite_collision)
            except (ValueError,OSError,KeyError,TypeError,struct.error) as error:
                adoption['regenerated'].append({'name':entry['name'],'reason':str(error)})
            else:
                local=out/entry['name'];local.mkdir()
                shutil.copyfile(resume/entry['name']/'scene.bsp',local/'scene.bsp')
                cached['resume_validation']={'status':'verified','input_contract_sha256':contract['sha256'],
                                             'source_directory':str(resume/entry['name']),
                                             'historical_source_contract':adoption['historical_source_contract']}
                (local/'conversion.json').write_text(json.dumps(cached,indent=2)+'\n',encoding='utf-8')
                results.append(cached);adoption['reused'].append(entry['name']);continue
        pending.append(entry)
    (out/'resume-validation.json').write_text(json.dumps(adoption,indent=2)+'\n',encoding='utf-8')
    print('FLORA RESUME',len(results),'validated regions;',len(pending),'to convert',flush=True)
    for result in ordered_map(convert_region,[(terrain,base,flora,palette,out,e,aggregate_sprite_collision,collision_packing) for e in pending],resolve_jobs(jobs)):
        if result.get('conversion_status')=='failed':failures.append(result)
        else:results.append(result)
        print('FLORA REGION',len(results)+len(failures),'/',len(entries),result['name'],result.get('conversion_status','complete'),flush=True)
    results.sort(key=lambda r:r['name'])
    status={'completed_regions':len(results),'failed_regions':len(failures),'reused_regions':len(adoption['reused']),
            'input_contract_sha256':contract['sha256'],'failures':failures}
    (out/'conversion-status.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
    if failures:raise ValueError('Flora conversion incomplete; all completed receipts/failures preserved: '+str(out/'conversion-status.json'))
    covered = {identity(r['source_key']) for e in results for r in e['source_references']}
    expected = {identity(r['source_key']) for r in receipt['placements']}
    if not only and covered != expected:raise ValueError('Full-world flora overlay omitted/invented source references')
    for asset in receipt['assets']:
        source = flora / asset['sprite_asset_name'];target = out / asset['sprite_asset_name']
        if digest(source) != asset['sha256']:raise ValueError('Flora shared sprite hash mismatch')
        target.parent.mkdir(parents=True, exist_ok=True);shutil.copyfile(source, target)
    result = {'format': 'AmiWind world flora overlay 1', 'diagnostic_subset': bool(only),
              'runtime_activation': False, 'collision_packing':collision_packing, 'aggregate_sprite_collision_comparison': aggregate_sprite_collision, 'master_sha256': receipt['master_sha256'],
              'source_staging_sha256': {name: digest(out/name) for name in ('source/scenery.mwpak','source/scenery-index.json','tree-sprites.json')},
              'base_world_scenery_receipt_sha256': digest(base / 'world-scenery.json'),
              'palette_sha256': receipt['palette_sha256'], 'assets': receipt['assets'],
              'input_contract_sha256':contract['sha256'],'resume':adoption,
              'source_selection': receipt['selection'], 'source_counts': receipt.get('source_counts', {}),
              'deferred_references': receipt.get('deferred_references', []),
              'covered_unique_original_refs': len(covered),
              'region_copy_instances': sum(len(r['source_references']) for r in results),
              'seconds': round(time.monotonic() - started, 3), 'regions': results,
              'scope': 'Original flora placement overlay; retained LAND/rocks/mushrooms verified. Town consumers and stateful interactions have separate acceptance.'}
    (out / 'world-flora.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('terrain', 'base', 'flora', 'palette', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--resume-from',type=Path)
    parser.add_argument('--resume-unchanged-regions',action='store_true',help='After bounded subdivision, allow only directory/base-receipt hashes to differ; every cached map and unchanged asset/source input remains verified')
    parser.add_argument('--adopt-legacy-resume-inputs',action='store_true',help='Explicit adoption of unchanged original invocation inputs when historical contract was not recorded; per-region validation remains mandatory')
    parser.add_argument('--collision-packing',choices=('per_instance','adaptive'),default='per_instance')
    parser.add_argument('--aggregate-sprite-collision', action='store_true', help='Opt-in collision union comparison; performance acceptance required')
    parser.add_argument('--only', nargs='+');add_jobs(parser);args = parser.parse_args()
    result = prepare(args.terrain, args.base, args.flora, args.palette, args.out, args.jobs, args.only, args.aggregate_sprite_collision, args.collision_packing,args.resume_from,args.adopt_legacy_resume_inputs,args.resume_unchanged_regions)
    print('WORLD FLORA SOURCE COVERAGE', result['covered_unique_original_refs'], 'original refs; runtime acceptance pending')

if __name__ == '__main__':main()
