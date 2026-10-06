#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Prepare bounded external mushroom models without modifying retained BSPs.

This is an opt-in AWH4 converter, not global flora conversion or a disk writer.
Plans bind each original input and retained map by SHA-256 and byte count.
The output remains diagnostic until its exact runtime, heap and native gates
are accepted. Original data and generated models must remain private.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import struct

import numpy as np

from harvest_alias import model_entries
from harvest_alias_mesh import convert, alias_cost
from mwad.scene import read_asset, unpack_geometry
from player_hull import lumps
from prepare_harvest import (identity_key, source_context, prepare_graph, prepare,
                             stage_pickup_sound)
from prepare_scenery import reference_rotation, world_bounds
from world_flora_policy import source_key


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(raw):
    return dict(sha256=digest(raw), bytes=len(raw))


def check_pin(raw, expected, label):
    if pin(raw) != {k: expected[k] for k in ('sha256', 'bytes')}:
        raise ValueError('Input digest/size differs: ' + label)
    return raw


def relative_path(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-zA-Z0-9_./-]+', value):
        raise ValueError('Unsafe relative payload path')
    path = Path(value)
    if path.is_absolute() or any(p in ('', '.', '..') for p in value.split('/')):
        raise ValueError('Unsafe relative payload path')
    return path


def verified_file(root, row):
    root = Path(root).resolve()
    path = root / relative_path(row['path'])
    if path.is_symlink() or not path.resolve().is_relative_to(root):
        raise ValueError('Payload path escapes input root')
    return check_pin(path.read_bytes(), row, row['path'])


def vector(values, length, label):
    if len(values) != length or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
        raise ValueError('Invalid ' + label)
    return np.array(values, dtype=float)


def alias_angles(ref):
    rotation = reference_rotation(ref)
    pitch = math.asin(float(np.clip(rotation[2, 0], -1, 1)))
    if abs(math.cos(pitch)) > 1e-8:
        yaw = math.atan2(rotation[1, 0], rotation[0, 0])
        roll = math.atan2(rotation[2, 1], rotation[2, 2])
    else:
        yaw = math.atan2(-rotation[0, 1], rotation[1, 1]); roll = 0
    return np.degrees([pitch, yaw, roll]).tolist()


def geometry_bounds(archive, model):
    vertices, _, _ = unpack_geometry(read_asset(archive, model))
    xyz = np.asarray(vertices)[:, :3]
    bounds = np.array([xyz.min(0), xyz.max(0)])
    if np.shape(model['bounds']) != (2, 3) or not np.allclose(bounds, model['bounds'], rtol=0, atol=1e-5):
        raise ValueError('Packet model bounds differ from decoded geometry')
    return bounds.tolist()


def validate_references(context, index, archive):
    """Bind every packet reference to original master fields and model bytes."""
    if not 1 <= len(index['references']) <= 24:
        raise ValueError('Bounded batch requires 1..24 original placements')
    refs, seen, bounds = [], set(), {}
    for item in index['references']:
        ref = dict(item)
        ref['source_key'] = source_key(ref, context['full']['master_sha256'])
        key = identity_key(ref['source_key'])
        if key in seen or key not in context['original']:
            raise ValueError('Duplicate or unknown packet placement')
        seen.add(key)
        for field, value in context['original'][key].items():
            if ref.get(field) != value:
                raise ValueError('Packet original placement mismatch: ' + field)
        number = ref['model_index']
        if type(number) is not int or not 0 <= number < len(index['models']):
            raise ValueError('Invalid packet model binding')
        model = index['models'][number]
        expected = 'meshes/' + ref['model'].replace('\\', '/').casefold()
        if model['source'].replace('\\', '/').casefold() != expected:
            raise ValueError('Packet model differs from original CONT model')
        if not re.fullmatch('[0-9a-f]{64}', model.get('source_sha256', '')):
            raise ValueError('Packet lacks original model provenance')
        if number not in bounds:
            bounds[number] = geometry_bounds(archive, model)
        posed_bounds = world_bounds(bounds[number], ref)
        if np.shape(ref['bounds']) != (2, 3) or not np.allclose(posed_bounds, ref['bounds'], rtol=0, atol=1e-5):
            raise ValueError('Packet posed bounds differ from original transform')
        if not .01 <= ref['scale'] <= 100 or not all(math.isfinite(v) for v in ref['position'] + ref['rotation_radians']):
            raise ValueError('Invalid source placement transform')
        refs.append(ref)
    return refs


def region_references(row, refs):
    origin = vector(row['origin'], 3, 'map origin')
    lo = vector(row['coverage'][0], 2, 'map coverage')
    hi = vector(row['coverage'][1], 2, 'map coverage')
    if np.any(lo >= hi):
        raise ValueError('Empty/inverted map coverage')
    selected = []
    for ref in refs:
        bounds = np.array(ref['bounds']) * .25 - origin
        if np.all(bounds[1, :2] >= lo) and np.all(bounds[0, :2] <= hi):
            selected.append(ref)
    keys = [identity_key(r['source_key']) for r in selected]
    if len(row['keys']) != len(set(row['keys'])) or set(keys) != set(row['keys']):
        raise ValueError('Plan placement set differs from transformed bounds coverage')
    if not selected:
        raise ValueError('External catalogue cannot be empty')
    return selected


def reject_existing_geometry(bsp, refs, origin):
    entities = [dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', block)) for block in
                re.findall(r'\{[^{}]*\}', lumps(bsp)[0].rstrip(b'\0').decode('cp1252'))]
    numbers = {str(ref['number']) for ref in refs}
    poses = [np.array(ref['position']) * .25 - origin for ref in refs]
    for entity in entities:
        if entity.get('aw_ref') in numbers:
            raise ValueError('Retained BSP already binds selected reference')
        if entity.get('classname') not in ('func_wall', 'aw_static', 'aw_flora'):
            continue
        try:
            pose = np.array([float(v) for v in entity.get('origin', '').split()])
        except ValueError:
            raise ValueError('Malformed retained scenery pose') from None
        if pose.shape == (3,) and any(np.linalg.norm(pose - p) <= .01 for p in poses):
            raise ValueError('Retained BSP has scenery at selected source pose')


def catalogue(context, refs, origin, model_indices, registry):
    def binding(ref):
        pose = (np.array(ref['position']) * .25 - origin).tolist()
        angles = alias_angles(ref)
        entity = dict(model='@' + str(model_indices[ref['model_index']]),
                      representation='external_alias', scale=ref['scale'])
        return entity, pose, angles

    nodes, edges, plants, provenance = prepare_graph(context, refs, binding)
    lines = [f"AWH4 {len(nodes)} {len(edges)} {len(plants)} {len(context['indices'])} {context['catalogue']} {len(registry)}"]
    lines.extend(registry)
    lines += ['{kind} {flags} {chance} {first} {count} {id}'.format(**n) + '\t' + n.get('label', '-') for n in nodes]
    lines += [' '.join(map(str, edge)) for edge in edges]
    for plant, ref in zip(plants, refs):
        lines.append('{key} {slot} {reference} {model} {flags} {first} {count} '.format(**plant) +
                     ' '.join(format(v, '.9g') for v in plant['origin'] + plant['angles'] + [ref['scale']]) +
                     ' ' + plant['label'])
    return ('\n'.join(lines) + '\n').encode('ascii'), provenance


def budget_report(models, maps, budget):
    """Never let unchanged BSP bytes conceal external residency costs.

    Budget source and static delta are independently measured target inputs,
    not constants inferred from host C structure sizes or waived reserves.
    """
    if budget is None:
        return dict(status='unknown', reason='Exact target ABI/static delta and baseline heap receipt required')
    sizes = budget['target_struct_sizes_bytes']
    if not all(type(v) is int and v > 0 for v in sizes.values()):
        raise ValueError('Invalid target ABI sizes')
    if not re.fullmatch('[0-9a-f]{64}', budget['target_measurement_sha256']):
        raise ValueError('Missing target measurement digest')
    static = budget['target_static_delta_bytes']
    if type(static) is not int or static < 0:
        raise ValueError('Invalid target static storage delta')
    if type(budget['heap_budget_bytes']) is not int or budget['heap_budget_bytes'] <= 0:
        raise ValueError('Invalid target heap allowance')
    costs = [alias_cost(raw, sizes) for raw in models]
    cache = sum(c['cache_bytes'] for c in costs)
    fallback = max(c['source_file_hunk_fallback_bytes'] + c['decoded_hunk_bytes'] for c in costs)
    surcharge = cache + fallback + static
    baseline = {r['map']: r for r in budget['maps']}
    if len(baseline) != len(budget['maps']) or set(baseline) != {r['name'] for r in maps}:
        raise ValueError('Heap baseline map set differs')
    rows = []
    for row in maps:
        base = baseline[row['name']]
        if base['bsp_sha256'] != row['sha256'] or base['bsp_bytes'] != row['bytes']:
            raise ValueError('Heap baseline BSP binding differs')
        if type(base['estimated_total_bytes']) is not int or base['estimated_total_bytes'] <= 0:
            raise ValueError('Invalid baseline heap estimate')
        total = base['estimated_total_bytes'] + surcharge
        clearance = budget['heap_budget_bytes'] - total
        rows.append(dict(map=row['name'], baseline_total=base['estimated_total_bytes'],
                         external_surcharge=surcharge, candidate_total=total, clearance=clearance,
                         allowance_pass=clearance >= 0))
    return dict(status='pass' if all(r['allowance_pass'] for r in rows) else 'failed',
                target_measurement_sha256=budget['target_measurement_sha256'],
                unique_cache_bytes=cache, worst_loader_fallback_bytes=fallback,
                static_delta_bytes=static, surcharge_bytes=surcharge, maps=rows,
                native_headroom='not_measured', admission='No inherited or new allowance failure is waived')


def convert_plan(plan, master, index_raw, archive_path, palette, base_root, output,
                 *, legacy_root=None, budget=None, media_payload=None):
    if plan.get('format') != 'AmiWind external harvest plan 1':
        raise ValueError('Unknown external harvest plan')
    for label, raw in (('master', master), ('index', index_raw), ('palette', palette)):
        check_pin(raw, plan['inputs'][label], label)
    # Packets are bounded batches; hashing this source packet does not scan a BSA.
    if Path(archive_path).stat().st_size > 64 * 1024 * 1024:
        raise ValueError('Packet exceeds bounded format')
    packet_raw = Path(archive_path).read_bytes()
    check_pin(packet_raw, plan['inputs']['packet'], 'packet')
    if len(packet_raw) > 64 * 1024 * 1024 or len(palette) != 768:
        raise ValueError('Packet/palette size exceeds bounded format')
    context = source_context(master)
    if context['catalogue'] != plan['global_catalogue_sha256'] or len(context['indices']) != plan['global_slots']:
        raise ValueError('Global original placement index differs')
    index = json.loads(index_raw)
    files, model_raws, model_rows, registry, map_rows, legacy_rows = {}, [], [], [], [], []
    with Path(archive_path).open('rb') as archive:
        refs = validate_references(context, index, archive)
        model_numbers = sorted({ref['model_index'] for ref in refs}, key=lambda i: index['models'][i]['source'])
        if not 1 <= len(model_numbers) <= 8:
            raise ValueError('External model registry exceeds 8 shared models')
        model_indices = {number: i for i, number in enumerate(model_numbers)}
        for number in model_numbers:
            model = index['models'][number]
            raw, report = convert(archive, index, model, palette)
            name = 'progs/harvest/' + digest(raw)[:24] + '.mdl'
            if name in files:
                raise ValueError('Duplicate generated model binding')
            scale = np.array(struct.unpack_from('<3f', raw, 8))
            lo = np.array(struct.unpack_from('<3f', raw, 20)); hi = lo + scale * 255
            registry.append(name + ' ' + digest(raw) + ' ' + ' '.join(format(v, '.9g') for v in (*lo, *hi)))
            files[name] = raw; model_raws.append(raw)
            model_rows.append(dict(path=name, **pin(raw), source=model['source'],
                                   source_sha256=model['source_sha256'], conversion=report))
    maps = plan['maps']; names = [row['name'] for row in maps]
    if not 1 <= len(maps) <= 256 or len(set(names)) != len(names):
        raise ValueError('Map plan duplicate/empty/excessive')
    for row in maps:
        if not re.fullmatch('[a-z0-9_]{1,24}', row['name']):
            raise ValueError('Invalid map name')
        selected = region_references(row, refs)
        bsp = verified_file(base_root, row)
        origin = vector(row['origin'], 3, 'map origin')
        reject_existing_geometry(bsp, selected, origin)
        raw, provenance = catalogue(context, selected, origin, model_indices, registry)
        path = 'harvest-' + row['name'] + '.txt'; files[path] = raw
        map_rows.append(dict(name=row['name'], path=row['path'], **pin(bsp),
                             destination='maps/' + row['name'] + '.bsp', representation='external_alias',
                             catalogue=dict(path=path, **pin(raw)), placements=provenance,
                             retained_bsp='byte_identical', coverage=row['coverage'], origin=row['origin']))
    for row in plan.get('legacy', []):
        if legacy_root is None or not re.fullmatch('[a-z0-9_]{1,24}', row['name']) or row['name'] in names:
            raise ValueError('Legacy map needs a separate valid input and unique name')
        names.append(row['name'])
        bsp = verified_file(legacy_root, row['bsp'])
        report = json.loads(verified_file(legacy_root, row['report']))
        raw = verified_file(legacy_root, row['catalogue'])
        regenerated, receipt = prepare(master, report, bsp, context=context)
        if raw != regenerated:
            raise ValueError('Mixed legacy catalogue differs from original source/BSP binding')
        if receipt['global_catalogue_sha256'] != context['catalogue']:
            raise ValueError('Mixed catalogue index differs')
        name = 'harvest-' + row['name'] + '.txt'; files[name] = raw
        legacy_rows.append(dict(name=row['name'], path=row['bsp']['path'], **pin(bsp),
                                destination='maps/' + row['name'] + '.bsp', representation='brush',
                                catalogue=dict(path=name, **pin(raw))))
    report = dict(format='AmiWind external harvest payload 1', plan_sha256=digest(json.dumps(plan, sort_keys=True).encode()),
                  inputs=plan['inputs'], global_slots=len(context['indices']),
                  global_catalogue_sha256=context['catalogue'], models=model_rows, maps=map_rows,
                  legacy_maps=legacy_rows, original_placements=len(refs), resident_map_copies=sum(len(r['placements']) for r in map_rows),
                  heap=budget_report(model_raws, map_rows + legacy_rows, budget),
                  budget_input_sha256=digest(json.dumps(budget, sort_keys=True).encode()) if budget else None,
                  save_identity='Original master/cell/FRMR keys and global slots; residency is transient',
                  model_limit='Bounded to 8 shared models and 24 local plants; no global activation',
                  lighting_limitation='All MDL vertex normal indices are zero; native appearance remains unaccepted',
                  native_acceptance='not_run', admission='diagnostic_only',
                  existing_geometry_check='Entity source IDs and exact poses checked; anonymous baked geometry requires independent provenance review')
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    for path, raw in sorted(files.items()):
        destination = output / path; destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    model_entries(output, registry)
    report['pickup_sound'] = stage_pickup_sound(media_payload, output)
    report['files'] = [dict(path=p.relative_to(output).as_posix(), **pin(p.read_bytes()))
                       for p in sorted(output.rglob('*')) if p.is_file()]
    (output / 'external-harvest-manifest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def materialize(manifest, payload, base_root, destination, *, legacy_root=None):
    """Fresh-directory adapter; no in-place install, HDF access or gate bypass.

    A source-only payload can be generated despite a failed budget for review.
    A production payload may not be materialized until every map passes.
    """
    if manifest.get('format') != 'AmiWind external harvest payload 1' or manifest['heap']['status'] != 'pass':
        raise ValueError('Production staging requires passing exact heap admission')
    files = {}
    for row in manifest['files']:
        name = str(relative_path(row['path']))
        if name in files:
            raise ValueError('Duplicate payload entry')
        files[name] = (Path(payload), row)
    for rows, root in ((manifest['maps'], base_root), (manifest['legacy_maps'], legacy_root)):
        for row in rows:
            if root is None or row['destination'] in files:
                raise ValueError('Missing/duplicate retained map source')
            files[row['destination']] = (Path(root), row)
    # Validate the whole closure before creating a destination. Streaming copies
    # below are checked again against pins, so changed input cannot pass unnoticed.
    for root, row in files.values():
        verified_file(root, row)
    destination = Path(destination); destination.mkdir(parents=True, exist_ok=False)
    for name, (root, row) in sorted(files.items()):
        target = destination / relative_path(name); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / row['path'], target)
        check_pin(target.read_bytes(), row, name)
    receipt = dict(format='AmiWind external harvest staging 1', files=len(files),
                   byte_identical_bsp_readback=True, native_acceptance='not_run')
    (destination / 'external-harvest-staging.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    build = sub.add_parser('convert')
    for arg in ('plan', 'master', 'index', 'packet', 'palette', 'base-root', 'out'):
        build.add_argument('--' + arg, type=Path, required=True)
    for arg in ('legacy-root', 'budget', 'media-payload'):
        build.add_argument('--' + arg, type=Path)
    stage = sub.add_parser('stage')
    for arg in ('payload', 'base-root', 'out'):
        stage.add_argument('--' + arg, type=Path, required=True)
    stage.add_argument('--legacy-root', type=Path)
    args = parser.parse_args()
    if args.command == 'convert':
        convert_plan(json.loads(args.plan.read_text()), args.master.read_bytes(), args.index.read_bytes(),
                     args.packet, args.palette.read_bytes(), args.base_root, args.out,
                     legacy_root=args.legacy_root, media_payload=args.media_payload,
                     budget=json.loads(args.budget.read_text()) if args.budget else None)
    else:
        materialize(json.loads((args.payload / 'external-harvest-manifest.json').read_text()),
                    args.payload, args.base_root, args.out, legacy_root=args.legacy_root)


if __name__ == '__main__':
    main()
