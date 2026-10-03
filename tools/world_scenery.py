#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Inventory base-master rocks and giant mushrooms; outputs remain private.

This records source ownership, not runtime region membership or a coverage claim.
Mesh bounds must subsequently determine intersection with runtime regions.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.audit import cell_data, normpath, records, string, subrecords
from mwad.paths import child_ci, ensure_external, resolve_data_files


def scenery_kind(object_id, obj):
    """Static formations only; harvestable/ingredient mushrooms are excluded."""
    if obj['type'] != 'STAT' or not obj.get('model'):
        return None
    stem = normpath(obj['model']).rsplit('/', 1)[-1]
    if stem.startswith(('flora_emp_parasol_', 'flora_t_mushroom_')):
        return 'giant_mushroom'
    if 'rock' in stem or 'boulder' in stem or stem in ('terrain_ma_20.nif', 'terrain_ma_30.nif'):
        return 'rock'
    return None


def inventory(master):
    objects, cells = {}, []
    for tag, flags, payload in records(master):
        if tag == 'CELL':
            cell = cell_data(list(subrecords(payload)))
            if not flags & 0x20:
                cells.append(cell)
        elif tag in ('STAT', 'ACTI', 'INGR', 'CONT'):
            fields = dict(subrecords(payload))
            if 'NAME' in fields and 'DELE' not in fields:
                object_id = string(fields['NAME']).casefold()
                objects[object_id] = {'type': tag, 'model': string(fields.get('MODL', b''))}
    references, interiors = [], []
    identities = set()
    for cell in cells:
        is_interior = bool(cell['flags'] & 1)
        cell_key = cell['name'] if is_interior else [cell['x'], cell['y']]
        for ref in cell['refs']:
            if ref.get('deleted'):
                continue
            object_id = ref.get('id', '').casefold()
            obj = objects.get(object_id)
            kind = scenery_kind(object_id, obj) if obj else None
            if kind is None:
                continue
            if 'position' not in ref or 'rotation_radians' not in ref or ref['scale'] <= 0:
                raise ValueError('Invalid scenery reference transform: ' + str(ref['number']))
            identity = ('interior' if is_interior else 'exterior', str(cell_key), ref['number'])
            if identity in identities:
                raise ValueError('Duplicate source reference identity: ' + str(identity))
            identities.add(identity)
            item = {**ref, **obj, 'kind': kind, 'cell': cell_key,
                    'cell_name': cell['name'], 'region': cell['region']}
            (interiors if is_interior else references).append(item)
    return {'format': 'AmiWind world scenery census 1',
            'master_sha256': hashlib.sha256(master).hexdigest(),
            'scope': 'Base-master exterior rocks and giant mushrooms; interior occurrences recorded separately.',
            'runtime_coverage': 'Not established by this source census.',
            'references': references, 'interior_references': interiors,
            'counts': {'exterior': dict(Counter(r['kind'] for r in references)),
                       'interior': dict(Counter(r['kind'] for r in interiors)),
                       'exterior_cells': len({tuple(r['cell']) for r in references}),
                       'exterior_models': len({normpath(r['model']) for r in references})}}


def region_references(index, entry, scale=0.25):
    """Select by transformed bounds; shift Z into the retained terrain frame."""
    import math
    if scale <= 0:
        raise ValueError('Invalid world scale')
    origin = entry['origin']
    low, high = entry['coverage']
    bounds = [[(origin[k] + edge[k]) / scale for k in range(2)] for edge in (low, high)]
    candidates = set()
    chunk = index['chunk_size']
    for y in range(math.floor(bounds[0][1] / chunk), math.floor(bounds[1][1] / chunk) + 1):
        for x in range(math.floor(bounds[0][0] / chunk), math.floor(bounds[1][0] / chunk) + 1):
            candidates.update(index['chunks'].get(f'{x},{y}', []))
    result = []
    for number in sorted(candidates):
        ref = index['references'][number]
        if not all(ref['bounds'][1][k] >= bounds[0][k] and ref['bounds'][0][k] <= bounds[1][k] for k in range(2)):
            continue
        shifted = dict(ref)
        shifted['position'] = [*ref['position'][:2], ref['position'][2] - origin[2] / scale]
        shifted['bounds'] = [[*edge[:2], edge[2] - origin[2] / scale] for edge in ref['bounds']]
        result.append(shifted)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-files', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--export-meshes', action='store_true')
    parser.add_argument('--jobs', type=int, default=1)
    args = parser.parse_args()
    data = resolve_data_files(args.data_files)
    out = ensure_external(args.out, 'private world scenery census')
    out.mkdir(parents=True, exist_ok=False)
    result = inventory(child_ci(data, 'Morrowind.esm').read_bytes())
    (out / 'source-census.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result['counts'], indent=2), flush=True)
    if args.export_meshes:
        from prepare_scenery import export_refs
        refs = result['references']
        profiles = {normpath('meshes/' + r['model']): {'collision_source': 'root_node_or_visual'} for r in refs}
        report = export_refs(data, out / 'scenery', refs,
                             {'world_scenery': {'references': [], 'visual_profiles': profiles}}, [0, 0, 0],
                             metadata={'scope': result['scope'], 'master_sha256': result['master_sha256']}, jobs=args.jobs)
        if report['errors'] or report['converted_references'] != len(refs):
            raise ValueError('Incomplete world scenery export; inspect private conversion errors.')
        print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
