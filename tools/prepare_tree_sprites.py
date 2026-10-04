#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Bake shared model sprites from an owned exterior census into private output.

This creates base-model images and exact source-placement metadata. It does not
activate a runtime overlay or imply the scale-aware renderer has been installed.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.paths import child_ci, ensure_external, resolve_data_files
from build_jobs import add_jobs, resolve_jobs
from build_parallel import ordered_map
from world_flora_policy import load_policy, placement, selection_receipt, stable_sprite_name


def normalized_model(model):
    model = model.replace('\\', '/').casefold().removeprefix('meshes/')
    stem = model.rsplit('/', 1)[-1]
    if not model.endswith('.nif') or 'street' in stem or not any(t in stem for t in ('tree', 'trunk', 'stump', 'grass', 'reed', 'fern', 'bush', 'shrub', 'weed', 'log')):
        raise ValueError('Expected tree/trunk/stump NIF model: ' + model)
    stable_sprite_name(model)  # reject unsafe paths
    return model


def select_census(census, models=None):
    """A requested subset is explicit; missing models and bad refs fail."""
    master_hash = census.get('master_sha256') or census.get('source_sha256')
    references = census.get('references', census.get('placements'))
    if not master_hash or not isinstance(references, list) or not references:
        raise ValueError('Expected a hashed nonempty exterior reference census')
    requested = {normalized_model(m) for m in models} if models else None
    result = []
    for ref in references:
        model = normalized_model(ref['model'])
        if requested is not None and model not in requested:
            continue
        if ref.get('deleted'):
            raise ValueError('Deleted reference in active flora census')
        if ref.get('type') not in ('STAT', 'CONT'):
            raise ValueError('Unsupported flora source record type')
        result.append({**ref, 'model': model})
    available = {r['model'] for r in result}
    if not result or requested is not None and requested != available:
        raise ValueError('Requested flora models are absent from source census')
    return master_hash, result


def collision_metadata(raw, N, kind):
    """Honor TES3 NC/NCO markers; never invent solid ground-plant hulls."""
    import io
    data = N.Data(); data.read(io.BytesIO(raw))
    blocks = list(data.get_global_iterator())
    markers = sorted({bytes(b.string_data).decode('ascii', errors='replace').strip().upper()
                      for b in blocks if isinstance(b, N.NiStringExtraData)})
    authored = any(isinstance(b, N.RootCollisionNode) for b in blocks)
    disabled = any(m in ('NC', 'NCO') for m in markers)
    if disabled:
        mode, reason = 'nonsolid', 'authored NC/NCO marker'
    elif authored:
        mode, reason = 'authored', 'authored RootCollisionNode; approximate convex conversion'
    elif kind in ('grass', 'reeds', 'fern', 'bush', 'stateful_flora'):
        mode, reason = 'nonsolid', 'explicit ground-vegetation policy; no authored collision node'
    else:
        mode, reason = 'visual_fallback', 'tree/log without authored node; existing approximate visual convex fallback'
    return {'mode': mode, 'reason': reason, 'authored_root_collision': authored,
            'no_collision_markers': [m for m in markers if m in ('NC', 'NCO')]}


def unique_reference_numbers(refs):
    """The existing indexed export addresses FRMR globally; reject collisions."""
    numbers = [r['number'] for r in refs]
    if len(numbers) != len(set(numbers)):
        raise ValueError('Duplicate global flora FRMR number; cannot export ambiguously')


def validate_sprite(raw):
    """Validate the single-frame sprite bytes produced by the existing bake."""
    if len(raw) < 56:
        raise ValueError('Truncated tree sprite')
    magic, version, kind, radius, width, height, frames, beam, sync = struct.unpack_from('<4siifiiifi', raw)
    frame_type, left, top, fw, fh = struct.unpack_from('<5i', raw, 36)
    if magic != b'IDSP' or version != 1 or kind != 2 or frames != 1 or frame_type != 0:
        raise ValueError('Unsupported tree sprite representation')
    if width <= 0 or height <= 0 or (width, height) != (fw, fh) or len(raw) != 56 + width * height:
        raise ValueError('Invalid tree sprite dimensions or length')
    if not math.isfinite(radius) or radius <= 0:
        raise ValueError('Invalid tree sprite radius')
    return {'sprite_type': kind, 'pixel_dimensions': [width, height],
            'frame_origin': [left, top], 'pixel_bytes': width * height,
            'bytes': len(raw)}


def prepare(data_files, census_path, palette_path, out, jobs=None, models=None, policy_path=None):
    import numpy as np
    from mwad.scene import read_asset
    from prepare_scenery import export_refs
    from prepare_quake import _preview_model
    data = resolve_data_files(Path(data_files))
    out = ensure_external(Path(out), 'private shared tree sprite output')
    policy = load_policy(policy_path)
    if census_path is None:
        from world_flora import inventory
        census = inventory(child_ci(data, 'Morrowind.esm').read_bytes(), policy.get('source_categories', ['tree']))
        census_raw = (json.dumps(census, indent=2) + '\n').encode('utf-8')
    else:
        census_raw = Path(census_path).read_bytes()
        census = json.loads(census_raw.decode('utf-8-sig'))
    master_hash, refs = select_census(census, models)
    unique_reference_numbers(refs)
    master = child_ci(data, 'Morrowind.esm')
    if hashlib.sha256(master.read_bytes()).hexdigest() != master_hash:
        raise ValueError('Flora census and owned base master differ')
    palette = Path(palette_path).read_bytes()
    if len(palette) != 768:
        raise ValueError('Expected 256-colour RGB palette')
    out.mkdir(parents=True, exist_ok=False)
    (out / 'source-census.json').write_bytes(census_raw)
    started = time.monotonic()
    budget = resolve_jobs(jobs)
    source = out / 'source'
    from prepare_scenery import bsa_read, nif_reader
    from mwad.audit import BSA
    from world_flora import flora_kind
    bsa = BSA(child_ci(data, 'Morrowind.bsa')); N = nif_reader()
    collision_by_model = {m: collision_metadata(bsa_read(bsa, 'meshes/' + m), N, flora_kind(m))
                          for m in sorted({r['model'] for r in refs})}
    profiles = {'meshes/' + r['model']: {'collision_source': 'root_node_or_visual'} for r in refs}
    groups = {'world_flora': {'references': [], 'visual_profiles': profiles}}
    source_report = export_refs(data, source, refs, groups, [0, 0, 0],
                                metadata={'master_sha256': master_hash}, jobs=budget)
    if source_report['errors'] or source_report['converted_references'] != len(refs):
        raise ValueError('Incomplete tree model export; inspect private source receipt')
    index = json.loads((source / 'scenery-index.json').read_text(encoding='utf-8'))
    expected_models = {'meshes/' + r['model'] for r in refs}
    if {m['source'] for m in index['models']} != expected_models:
        raise ValueError('Tree model export loses or invents source models')
    bounds = {m['source'].removeprefix('meshes/'): m['bounds'] for m in index['models']}
    placements = [placement(r, bounds[r['model']], policy, master_hash) for r in refs]
    for p in placements:
        p['source_collision'] = collision_by_model[p['model']]
    selection = selection_receipt(placements)
    required_sprite_models = {'meshes/' + p['model'] for p in placements if p['sprite_selected'] and not p['requires_interaction']}
    textures = {}
    with (source / 'scenery.mwpak').open('rb') as archive:
        for ti, texture in enumerate(index['textures']):
            raw = read_asset(archive, texture)
            magic, width, height = struct.unpack_from('>4sHH', raw)
            if magic != b'MWT1' or width <= 0 or height <= 0 or len(raw) != 8 + width * height * 4:
                raise ValueError('Invalid exported tree texture')
            textures[ti] = np.frombuffer(raw[8:], np.uint8).reshape(height, width, 4)
    def tasks():
        with (source / 'scenery.mwpak').open('rb') as archive:
            for mi, model in enumerate(index['models']):
                if model['source'] not in required_sprite_models:
                    continue
                used = {m['texture_index'] for m in model['materials'] if m['texture_index'] is not None}
                # The existing alpha bake selects flora by source-name marker.
                # Preserve the real model identity in the index/receipt, and
                # explicitly select that representation for eligible static props.
                bake_model = {**model, 'source': 'flora_' + model['source']}
                yield mi, bake_model, read_asset(archive, model), {i: textures[i] for i in used}, list(palette), set()
    workers = min(budget, max(1, len(required_sprite_models)))
    assets = []
    for mi, raw, generated, report in ordered_map(_preview_model, tasks(), workers):
        model = index['models'][mi]
        if generated is None or report['kind'] != 'sprite':
            raise ValueError('Tree source did not generate a sprite: ' + model['source'])
        stats = validate_sprite(raw)
        name = stable_sprite_name(model['source'])
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        original_model = model['source'].removeprefix('meshes/')
        assets.append({'model': original_model, 'sprite_asset_name': name,
                       'sha256': hashlib.sha256(raw).hexdigest(),
                       'source_geometry_sha256': model['sha256'],
                       'source_bounds': model['bounds'], 'source_xy_bake_center': generated[1],
                       'original_instances': sum(r['model'] == original_model for r in refs), **stats})
        print('TREE SPRITE', len(assets), '/', len(required_sprite_models), original_model, stats['bytes'], flush=True)
    if len(assets) != len(required_sprite_models) or len({a['sprite_asset_name'] for a in assets}) != len(assets):
        raise ValueError('Tree sprite coverage or stable asset identity mismatch')
    receipt = {'format': 'AmiWind shared tree sprite bake 1', 'runtime_activation': False,
               'runtime_instance_scale_support': 'pending engine integration and target validation',
               'diagnostic_subset': models is not None, 'master_sha256': master_hash,
               'census_sha256': hashlib.sha256(census_raw).hexdigest(),
               'palette_sha256': hashlib.sha256(palette).hexdigest(),
               'policy': policy, 'source_counts': census.get('counts', {}),
               'deferred_references': census.get('deferred_references', []), 'scale': .25, 'bake_source_azimuth': 0,
               'image_representation': 'type2 view-parallel billboard; original instance rotation retained in metadata',
               'collision': 'NC/NCO and ground-vegetation nonsolid policy honored; authored tree/log hulls retained separately',
               'model_collision': collision_by_model,
               'selection': selection,
               'effective_selection': {'sprite_instances': sum(p['sprite_selected'] and not p['requires_interaction'] for p in placements),
                                       'mesh_instances': sum(not p['sprite_selected'] or p['requires_interaction'] for p in placements),
                                       'stateful_mesh_pending_instances': sum(p['requires_interaction'] for p in placements)},
               'unique_models': len(assets),
               'exported_geometry_models': len(index['models']),
               'resident_pixel_bytes_all_types': sum(a['pixel_bytes'] for a in assets),
               'workers': workers, 'seconds': round(time.monotonic() - started, 3),
               'assets': assets, 'placements': placements}
    (out / 'tree-sprites.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8', newline='\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('data-files', 'palette', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--census', type=Path, help='Optional private diagnostic census; normal builds inventory --data-files automatically')
    parser.add_argument('--model', action='append', help='Explicit diagnostic model subset, repeatable')
    parser.add_argument('--policy', type=Path)
    add_jobs(parser)
    args = parser.parse_args()
    receipt = prepare(args.data_files, args.census, args.palette, args.out, args.jobs, args.model, args.policy)
    print('SHARED TREE SPRITES', receipt['unique_models'], 'models;', receipt['selection']['original_instances'],
          'original placements; runtime activation pending', flush=True)

if __name__ == '__main__':
    main()
