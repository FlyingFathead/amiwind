#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Read-only base-master flora census; records and outputs remain private.

Only original placements are used. Stateful/harvestable records are inventoried
separately; the decoration converter never substitutes away their semantics.
"""
from collections import Counter
import hashlib
import math
from pathlib import Path
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.audit import cell_data, normpath, records, string, subrecords

CATEGORIES = ('tree', 'grass', 'reeds', 'fern', 'bush', 'flora_log', 'stateful_flora')


def flora_kind(model):
    stem = normpath(model).rsplit('/', 1)[-1]
    if 'street' in stem or not stem.endswith('.nif'):
        return None
    if 'ivy' in stem:
        return 'ivy'
    if 'lilypad' in stem:
        return 'lilypad'
    if stem.startswith('flora_') and '_log_' in stem:
        return 'flora_log'
    if 'weed' in stem:
        return 'stateful_flora'
    if any(token in stem for token in ('treestump', 'tree', 'trunk')):
        return 'tree'
    for kind, tokens in (('grass', ('grass',)), ('reeds', ('reed',)),
                         ('fern', ('fern',)), ('bush', ('bush', 'shrub'))):
        if any(token in stem for token in tokens):
            return kind
    return None


def inventory(master, categories=('tree',)):
    categories = tuple(categories)
    if not categories or set(categories) - set(CATEGORIES):
        raise ValueError('Unsupported source flora categories')
    objects, cells = {}, []
    for tag, flags, payload in records(master):
        if tag == 'CELL':
            if not flags & 0x20:
                cells.append(cell_data(list(subrecords(payload))))
        elif tag in ('STAT', 'CONT', 'ACTI'):
            subs = list(subrecords(payload)); fields = dict(subs)
            if 'NAME' not in fields or 'DELE' in fields:
                continue
            model = string(fields.get('MODL', b''))
            kind = flora_kind(model)
            if kind not in categories and kind not in ('ivy', 'lilypad'):
                continue
            obj = {'type': tag, 'model': normpath(model), 'kind': kind,
                   'script': string(fields.get('SCRI', b''))}
            if tag == 'CONT':
                items = []
                for key, value in subs:
                    if key == 'NPCO':
                        if len(value) != 36:
                            raise ValueError('Invalid flora container inventory entry')
                        count, item = struct.unpack('<i32s', value)
                        items.append({'id': string(item), 'count': count})
                obj['container_state'] = {'items': items,
                    'flags': struct.unpack('<I', fields['FLAG'])[0] if len(fields.get('FLAG', b'')) == 4 else None,
                    'weight': struct.unpack('<f', fields['CNDT'])[0] if len(fields.get('CNDT', b'')) == 4 else None}
            objects[string(fields['NAME']).casefold()] = obj
    refs, interiors, deferred, seen = [], [], [], set()
    for cell in cells:
        is_interior = bool(cell['flags'] & 1)
        cell_key = cell['name'] if is_interior else [cell['x'], cell['y']]
        for ref in cell['refs']:
            obj = objects.get(ref.get('id', '').casefold())
            if obj is None or ref.get('deleted'):
                continue
            if 'position' not in ref or 'rotation_radians' not in ref or ref['scale'] <= 0:
                raise ValueError('Invalid flora source transform')
            if not all(math.isfinite(v) for v in ref['position'] + ref['rotation_radians'] + [ref['scale']]):
                raise ValueError('Nonfinite flora source transform')
            key = ('interior' if is_interior else 'exterior', str(cell_key), ref['number'])
            if key in seen:
                raise ValueError('Duplicate original flora reference')
            seen.add(key)
            item = {**ref, **obj, 'cell': cell_key, 'cell_name': cell['name'], 'region': cell['region'],
                    'requires_interaction': obj['type'] != 'STAT' or bool(obj['script'])}
            if is_interior:
                interiors.append(item)
            elif obj['kind'] in ('ivy', 'lilypad'):
                deferred.append({**item, 'reason': 'wall/horizontal orientation bake profile not implemented'})
            elif obj['type'] == 'ACTI':
                deferred.append({**item, 'reason': 'harvestable/activator semantics require an interaction converter'})
            else:
                refs.append(item)
    return {'format': 'AmiWind source flora census 1', 'master_sha256': hashlib.sha256(master).hexdigest(),
            'categories': list(categories), 'references': refs, 'interior_references': interiors,
            'deferred_references': deferred, 'runtime_activation': False,
            'counts': {'exterior': dict(Counter(r['kind'] for r in refs)),
                       'interior': dict(Counter(r['kind'] for r in interiors)),
                       'deferred_stateful': sum(r['type'] == 'ACTI' for r in deferred),
                       'deferred_orientation': sum(r['kind'] in ('ivy', 'lilypad') for r in deferred),
                       'deferred_total': len(deferred), 'original_exterior_instances': len(refs)}}
