# SPDX-License-Identifier: GPL-3.0-only
"""Private placed-object audit; no rendering, script execution or respawn policy."""
from collections import Counter
import hashlib
import struct
from .audit import records, subrecords, cell_data, require
from .npc import first, text, behavior_record
from .dialogue_lookup import build_lookup

BASE_TYPES = ('NPC_', 'CREA', 'CONT', 'DOOR', 'LEVC', 'LIGH', 'ACTI')


def cell_key(cell):
    return ('interior:' + cell['name'].casefold() if cell['flags'] & 1
            else 'exterior:%d,%d' % (cell['x'], cell['y']))


def region_audit(raw, centre=(-2, -9), radius=1):
    require(0 <= radius <= 4, 'Audit radius must be 0..4 cells')
    bases = {}; cells = []; topics = {}; topic = None
    for tag, flags, payload in records(raw):
        if tag not in (*BASE_TYPES, 'CELL', 'DIAL', 'INFO'):continue
        fields = list(subrecords(payload))
        # A CELL may contain DELE on a placed reference. Only its header can
        # delete the cell itself; individual reference deletion is handled below.
        header = fields[:next((i for i, (k, _) in enumerate(fields) if k == 'FRMR'), len(fields))] if tag == 'CELL' else fields
        deleted = bool(flags & 0x20) or any(k == 'DELE' for k, _ in header)
        if tag in BASE_TYPES:
            identifier = text(fields, 'NAME').casefold()
            require(identifier not in bases, 'Duplicate base record: ' + identifier)
            bases[identifier] = (tag, fields, deleted)
        elif tag == 'CELL' and not deleted:
            cell = cell_data(fields)
            # Retain all placed metadata, including unsupported ownership/lock fields.
            references = []; current = None
            for kind, data in fields:
                if kind == 'FRMR':
                    current = []; references.append(current)
                if current is not None:current.append([kind, data.hex()])
            for ref, original in zip(cell['refs'], references):ref['raw_subrecords'] = original
            cells.append(cell)
        elif tag == 'DIAL':
            topic = text(fields, 'NAME').casefold();topics.setdefault(topic, [])
        elif tag == 'INFO' and topic is not None:topics[topic].append(fields)
    keys = [cell_key(c) for c in cells]
    require(len(keys) == len(set(keys)), 'Duplicate CELL identity; mod merge unsupported')
    exterior = [c for c in cells if not c['flags'] & 1 and
                abs(c['x'] - centre[0]) <= radius and abs(c['y'] - centre[1]) <= radius]
    destinations = {r.get('destination_cell', '').casefold() for c in exterior
                    for r in c['refs'] if not r.get('deleted') and 'destination' in r}
    selected = exterior + [c for c in cells if c['flags'] & 1 and c['name'].casefold() in destinations]
    items = []; actors = {}; warnings = []; base_table = {}
    for cell in selected:
        key = cell_key(cell); numbers = [r['number'] for r in cell['refs']]
        require(len(numbers) == len(set(numbers)), 'Duplicate placed reference in ' + key)
        for ref in cell['refs']:
            identifier = ref.get('id', '').casefold()
            if ref.get('deleted') or identifier not in bases:continue
            tag, fields, deleted = bases[identifier]
            if deleted:continue
            row = {**ref, 'cell_key': key, 'cell_name': cell['name'], 'interior': bool(cell['flags'] & 1),
                   'type': tag, 'name': text(fields, 'FNAM'), 'base_id': identifier,
                   'placed_key': key + ':' + str(ref['number']), 'model': text(fields, 'MODL')}
            if tag == 'NPC_':
                flags = first(fields, 'FLAG');require(len(flags) == 4, 'Malformed NPC FLAG')
                identity = {'id': identifier, 'race': text(fields, 'RNAM'), 'class': text(fields, 'CNAM'),
                            'faction': text(fields, 'ANAM'), 'female': bool(struct.unpack('<I', flags)[0] & 1)}
                actors[identifier] = identity;row['identity'] = identity
                row['behavior'] = behavior_record(fields)
            elif tag == 'CREA' and first(fields, 'AIDT'):
                row['behavior'] = behavior_record(fields)
            if tag == 'DOOR':
                row['target_cell_key'] = ('interior:' + ref['destination_cell'].casefold()
                    if ref.get('destination_cell') else 'exterior-world') if 'destination' in ref else None
                row['destination_status'] = ('unresolved' if ref.get('destination_cell') and
                    'interior:' + ref['destination_cell'].casefold() not in keys else
                    'source-coordinate-only') if 'destination' in ref else 'no-teleport-record'
                # No guessed reciprocal door: multiple doors can share a destination cell.
            items.append(row)
            base_table[identifier] = {'type': tag, 'name': row['name'], 'model': row['model'],
                'script': text(fields, 'SCRI'), 'raw_subrecords': [[k, b.hex()] for k, b in fields]}
    voices = build_lookup(topics, list(actors.values()))
    for row in items:
        if row['type'] == 'NPC_':
            row['voice_static_candidates'] = {k: len(v) for k, v in voices['actors'][row['base_id']]['topics'].items()}
    known = {cell_key(c) for c in selected}
    for name in sorted(destinations - {''}):
        if 'interior:' + name not in known:warnings.append('Missing direct interior: ' + name)
    return {'schema': 'amiwind-vicinity-audit-v1', 'master_sha256': hashlib.sha256(raw).hexdigest(),
        'scope': {'centre': list(centre), 'radius_cells': radius,
                  'interiors': 'direct door destinations only; no recursive expansion',
                  'runtime_residency': 'audit only; no new objects loaded into the game'},
        'cells': [{'key': cell_key(c), 'name': c['name'], 'interior': bool(c['flags'] & 1)} for c in selected],
        'placements': items, 'bases': base_table, 'voices': voices, 'warnings': warnings,
        'counts': {kind: dict(Counter(r['type'] for r in items if r['interior'] == inside))
                   for kind, inside in [('exterior', False), ('interior', True)]}}


def roster_markdown(report):
    def safe(value):return str(value).replace('|', '/').replace('\n', ' ')
    lines = ['# Private Seyda Neen vicinity cast and object audit', '',
             'Generated from user-owned base data. Do not include this output in public source.', '',
             'Audit covers the configured exterior cells and their directly linked interiors.',
             'Interior actors are catalogued separately and are not exterior residents.',
             'Static voice candidates still require full condition/order/context evaluation.', '']
    for inside, label in [(False, 'Exterior cast'), (True, 'Interior cast (load only with that interior)')]:
        lines += ['## ' + label, '', '| Cell | NPC | Base ID | Reference | Race / sex | Hello / idle candidates |',
                  '| --- | --- | --- | --- | --- | --- |']
        rows = [r for r in report['placements'] if r['type'] == 'NPC_' and r['interior'] == inside]
        for r in sorted(rows, key=lambda r: (r['cell_key'], r['name'], r['number'])):
            a = r['identity'];v = r['voice_static_candidates']
            lines.append('| ' + ' | '.join(map(safe, [r['cell_name'] or r['cell_key'], r['name'], r['base_id'],
                r['number'], a['race'] + (' / female' if a['female'] else ' / male'),
                '%d / %d' % (v['hello'], v['idle'])])) + ' |')
        lines.append('')
    lines += ['## Object coverage', '', '| Space | Type | References |', '| --- | --- | ---: |']
    for where, counts in report['counts'].items():
        for kind, count in sorted(counts.items()):lines.append(f'| {where} | {kind} | {count} |')
    lines += ['', 'Door destinations, placed IDs, actor packages, container source fields and ordered',
              'voice records are in `vicinity-audit.json`. Reciprocal door IDs are not guessed.',
              'The broader audit area includes peripheral actors; it is not the selected native scene.', '']
    return '\n'.join(lines)
