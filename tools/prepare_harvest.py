#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Prepare a bounded direct-harvest catalogue from original inputs (private).

Base-master small mushroom CONT/INGR/LEVI only. Never drops unsupported script,
ownership, restock or placement state to make a container seem collectible.
"""
import argparse
import base64
import hashlib
import io
import json
import math
from pathlib import Path
import re
import struct
import sys
import wave
from mwad.audit import records, subrecords, string, cell_data
from player_hull import lumps
from world_flora import inventory
from world_flora_policy import source_key

PICKUP_SOURCE = 'sound/fx/item/item.wav'
PICKUP_PATH = 'sound/pool/a031af0520e9edfa2.wav'


def stage_pickup_sound(media_payload, output):
    """Reuse one verified conversion; missing optional audio stays a warning.

    The caller passes an id1-style payload directory, never a guest runtime
    catalogue reader. Existing output files are not overwritten.
    """
    report = dict(source=PICKUP_SOURCE, path=PICKUP_PATH, status='missing_output',
                  packaged='not_verified', native_acceptance='not_run')
    try:
        if media_payload is None:
            raise ValueError('No complete-media payload supplied')
        media_payload = Path(media_payload)
        catalogue = json.loads((media_payload / 'media/catalogue.json').read_text(encoding='utf-8'))
        rows = [r for r in catalogue['entries'] if r.get('source') == PICKUP_SOURCE]
        if len(rows) != 1:
            raise ValueError('Pickup sound requires one exact source entry')
        row = rows[0]
        if row.get('category') != 'effects' or row.get('status') != 'included' or row.get('path') != PICKUP_PATH:
            raise ValueError('Pickup sound source/category/output binding is invalid')
        if not re.fullmatch('[0-9a-f]{64}', row.get('source_sha256', '')):
            raise ValueError('Pickup sound source digest is missing')
        raw = (media_payload / PICKUP_PATH).read_bytes()
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Pickup sound output digest/size differs')
        with wave.open(io.BytesIO(raw)) as wav:
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 1, 11025):
                raise ValueError('Pickup sound PCM format is invalid')
            frames = wav.getnframes()
            if not 0 < frames <= 11025 * 5 or row.get('frames') != frames or row.get('rate') != 11025 or len(wav.readframes(frames)) != frames:
                raise ValueError('Pickup sound frame count/bound is invalid')
    except (OSError, ValueError, KeyError, TypeError, wave.Error) as error:
        report['warning'] = 'Harvest pickup sound unavailable: ' + str(error)
        return report
    target = Path(output) / PICKUP_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(raw)
    report.update(status='staged_verified', bytes=len(raw), sha256=row['sha256'],
                  source_sha256=row['source_sha256'], frames=frames, rate=11025,
                  source_verification='recorded conversion source digest; original input not reopened here')
    return report


def identity_key(value):
    digest = hashlib.sha256(json.dumps(value, separators=(',', ':'), ensure_ascii=True).encode()).digest()
    return 'aw:h:' + base64.b32encode(digest).decode().lower().rstrip('=')


def identifier(value):
    if not re.fullmatch(r'[!-~]{1,63}', value):
        raise ValueError('Runtime item identifier must be printable ASCII without spaces')
    return value.casefold()


def placement_source_key(ref, master_sha256):
    """Preserve the already-indexed interior namespace and exact cell spelling."""
    if not isinstance(master_sha256, str) or not re.fullmatch('[0-9a-f]{64}', master_sha256):
        raise ValueError('Invalid source master digest')
    if isinstance(ref['cell'], str):
        if not ref['cell'] or '\0' in ref['cell'] or type(ref['number']) is not int or not 0 <= ref['number'] <= 0xffffffff:
            raise ValueError('Invalid interior source identity')
        return (master_sha256, 'interior', ref['cell'], ref['number'])
    return source_key(ref, master_sha256)


def placement_locator(ref):
    return ('interior', ref['cell'], ref['number']) if isinstance(ref['cell'], str) else (*ref['cell'], ref['number'])


def source_records(master, reference_metadata=None):
    objects, reference_fields = {}, {}
    for tag, flags, payload in records(master):
        subs = list(subrecords(payload)); fields = dict(subs)
        if tag == 'TES3' and any(k == 'MAST' for k, _ in subs):
            raise ValueError('Only a standalone base master is supported')
        if tag == 'CELL':
            cell = cell_data(subs); current = None
            if flags & 0x20:
                continue
            for key, value in subs:
                if key == 'FRMR':
                    number = struct.unpack('<I', value)[0]
                    current = ('interior', cell['name'], number) if cell['flags'] & 1 else (cell['x'], cell['y'], number)
                    if current in reference_fields:
                        raise ValueError('Duplicate original placement')
                    reference_fields[current] = []
                elif current:
                    reference_fields[current].append(key)
                    if reference_metadata is not None and key in ('ANAM', 'INTV', 'NAM9'):
                        reference_metadata.setdefault(current, []).append((key, value))
        elif tag in ('CONT', 'INGR', 'LEVI', 'LEVC', 'MISC', 'ALCH', 'WEAP', 'ARMO', 'CLOT',
                     'BOOK', 'APPA', 'LOCK', 'PROB', 'REPA', 'LIGH', 'ACTI', 'STAT', 'CREA', 'NPC_') and 'NAME' in fields:
            name = string(fields['NAME']).casefold()
            if name in objects:
                raise ValueError('Duplicate source record; load-order resolution is not implemented')
            if 'DELE' not in fields and not flags & 0x20:
                objects[name] = (tag, subs, fields)
    return objects, reference_fields


def placement_index(census):
    """Stable across map subsets; reserve known interior identities as well.

    This indexes the supported numeric mushroom taxonomy, not all GOTY flora.
    Unsupported placements remain indexed but are never silently activated.
    """
    keys = []
    for group in ('references', 'interior_references', 'deferred_references'):
        for ref in census[group]:
            if ref['kind'] != 'small_mushroom':
                continue
            if group == 'interior_references':
                identity = (census['master_sha256'], 'interior', ref['cell'], ref['number'])
            else:
                identity = source_key(ref, census['master_sha256'])
            keys.append(identity_key(identity))
    if len(keys) != len(set(keys)) or not 1 <= len(keys) <= 4096:
        raise ValueError('Global harvest placement index is duplicate, empty or exceeds 4096')
    keys.sort()
    digest = hashlib.sha256(('AmiWind harvest index 1\n' + '\n'.join(keys) + '\n').encode('ascii')).hexdigest()
    return {key: i + 1 for i, key in enumerate(keys)}, digest


def source_context(master, *, max_plants=24, intern_root_spans=False):
    """Parse original identity and contents once for a bounded map batch."""
    full = inventory(master, ('small_mushroom',))
    indices, catalogue = placement_index(full)
    if type(max_plants) is not int or not 1 <= max_plants <= 256 or type(intern_root_spans) is not bool:
        raise ValueError('Explicit runtime plant admission must be 1..256')
    original = {identity_key(placement_source_key(r, full['master_sha256'])): r
                for group in ('references', 'interior_references', 'deferred_references') for r in full[group]
                if r['kind'] == 'small_mushroom'}
    reference_metadata = {}
    objects, placement_fields = source_records(master, reference_metadata)
    return dict(full=full, indices=indices, catalogue=catalogue,
                original=original, objects=objects, placement_fields=placement_fields,
                max_plants=max_plants, intern_root_spans=intern_root_spans, reference_metadata=reference_metadata)


def placement_metadata(context, ref):
    """Retain source CellRef data; never interpret charge/gold as plant yield.

    OpenMW 0.48 components/esm3/cellref.cpp maps ANAM to owner, INTV to
    charge and NAM9 to gold value. The optional source defaults below have
    no active CONT charge/gold behavior. Ownership still requires crime and
    stolen-inventory semantics unavailable in the current runtime.
    """
    locator = placement_locator(ref)
    fields = context['placement_fields'].get(locator)
    if fields is None or set(fields) - {'NAME', 'DATA', 'XSCL', 'ANAM', 'INTV', 'NAM9'}:
        raise ValueError('Placement has ownership, lock, deletion or other unsupported state')
    values = context.get('reference_metadata', {}).get(locator, [])
    result = dict(owner='', charge=-1, gold_value=1, original_subrecords=[])
    seen = set()
    for tag, raw in values:
        if tag in seen:
            raise ValueError('Duplicate source placement field: ' + tag)
        seen.add(tag)
        result['original_subrecords'].append(dict(tag=tag, bytes=len(raw), hex=raw.hex()))
        if tag == 'ANAM':
            if not raw or raw[-1:] != b'\0' or b'\0' in raw[:-1]:
                raise ValueError('Malformed source placement owner')
            result['owner'] = string(raw)
        else:
            if len(raw) != 4:
                raise ValueError('Invalid source placement field length: ' + tag)
            result['charge' if tag == 'INTV' else 'gold_value'] = struct.unpack('<i', raw)[0]
    # Presence must agree with the independently collected original field list.
    if seen != set(fields) & {'ANAM', 'INTV', 'NAM9'}:
        raise ValueError('Source placement metadata is incomplete')
    result['admission'] = ('requires_ownership_and_theft' if result['owner'] else
                           'unsupported_nondefault_charge_or_gold' if result['charge'] not in (-1, 0) or result['gold_value'] != 1 else
                           'supported_neutral_container_metadata')
    return result


def prepare_graph(context, references, binding):
    """Validate source records and resolve graph structure without granting loot.

    A representation supplies only its verified runtime pose/model binding.
    Original identity, placement metadata, contents and display names retain
    exactly the same checks for brush and external-model representations.
    """
    full = context['full']; indices = context['indices']
    original = context['original']; objects = context['objects']
    placement_fields = context['placement_fields']
    nodes, edges, plants, provenance, node_ids, active, used_keys = [], [], [], [], {}, set(), set()

    root_spans = {}

    def node(name):
        name = identifier(name)
        if name in active:
            raise ValueError('Cyclic leveled item list')
        if name in node_ids:
            return node_ids[name]
        if len(active) >= 16:
            raise ValueError('Leveled item nesting exceeds runtime bound')
        active.add(name)
        index = len(nodes); node_ids[name] = index; nodes.append(None)
        record = objects.get(name)
        if record is None:
            result = dict(kind=2, flags=0, chance=0, first=0, count=0, id=name)
        else:
            tag, subs, fields = record
            if string(fields.get('SCRI', b'')):
                raise ValueError('Scripted contents require script execution support')
            if tag == 'INGR':
                label = string(fields.get('FNAM', b''))
                if not re.fullmatch(r'[ -~]{1,63}', label) or label == '-':
                    raise ValueError('Ingredient requires its original supported display name')
                result = dict(kind=0, flags=0, chance=0, first=0, count=0, id=name, label=label)
            elif tag == 'LEVI':
                flags = struct.unpack('<I', fields['DATA'])[0]
                chance = fields['NNAM'][0]
                if flags & ~3 or len(fields['NNAM']) != 1 or chance > 100:
                    raise ValueError('Unsupported leveled list flags/chance')
                pending = None; entries = []
                for key, value in subs:
                    if key == 'INAM':
                        if pending is not None:
                            raise ValueError('Leveled entry lacks a level')
                        pending = string(value)
                    elif key == 'INTV':
                        if pending is None or len(value) != 2:
                            raise ValueError('Invalid leveled entry')
                        level = struct.unpack('<H', value)[0]
                        if level > 32767:
                            raise ValueError('Unsupported leveled entry level')
                        entries.append((node(pending), level, 1)); pending = None
                if pending or len(entries) != struct.unpack('<I', fields['INDX'])[0]:
                    raise ValueError('Leveled entry count mismatch')
                result = dict(kind=1, flags=flags, chance=chance, first=len(edges), count=len(entries), id=name)
                edges.extend(entries)
            else:
                raise ValueError('Only original ingredients and LEVI contents are supported')
        nodes[index] = result; active.remove(name); return index

    for ref in references:
        if ref.get('kind') != 'small_mushroom':
            continue
        key = identity_key(ref['source_key'])
        if key in used_keys or key not in original:
            raise ValueError('Duplicate or unbound master/cell/FRMR identity')
        used_keys.add(key); source = original[key]
        for field, value in source.items():
            if ref.get(field) != value:
                raise ValueError('Source placement metadata mismatch: ' + field)
        if ref['type'] != 'CONT' or ref.get('script') or not ref['container_state']['flags'] & 1:
            raise ValueError('Only unscripted organic container mushrooms are supported')
        metadata = placement_metadata(context, ref)
        if metadata['admission'] != 'supported_neutral_container_metadata':
            raise ValueError('Source placement requires ownership/theft or nondefault charge/gold handling: ' + metadata['admission'])
        if not 0 < ref['number'] <= 16777216:
            raise ValueError('Reference cannot be represented exactly by current QC field')
        entity, origin, angles = binding(ref)
        contents = []
        for item in ref['container_state']['items']:
            if not 1 <= item['count'] <= 64:
                raise ValueError('Restocking/nonpositive or excessive inventory counts are not supported')
            contents.append((node(item['id']), 0, item['count']))
        span = tuple(contents)
        if context.get('intern_root_spans', False) and span in root_spans:
            first = root_spans[span]
        else:
            first = len(edges); edges.extend(contents)
            if context.get('intern_root_spans', False):
                root_spans[span] = first
        fields = objects[ref['id'].casefold()][2]
        label = string(fields.get('FNAM', b''))
        if not re.fullmatch(r'[ -~]{1,63}', label):
            raise ValueError('Unsupported runtime display name encoding/length')
        plants.append(dict(key=key, slot=indices[key], reference=ref['number'], model=entity['model'], flags=ref['container_state']['flags'],
                           first=first, count=len(contents), origin=origin, angles=angles, label=label))
        provenance.append(dict(key=key, slot=indices[key], source_key=ref['source_key'], source_id=ref['id'],
                               container_state=ref['container_state'], script=ref['script'], placement_metadata=metadata, entity=entity))
    if len(nodes) > 64 or len(edges) > 256 or len(plants) > context.get('max_plants', 24):
        raise ValueError('Harvest catalogue exceeds bounded runtime capacity')
    return nodes, edges, plants, provenance


def prepare(master, region, bsp, *, context=None):
    if hashlib.sha256(bsp).hexdigest() != region['sha256']:
        raise ValueError('Region receipt does not match BSP')
    if context is None:
        context = source_context(master)
    elif hashlib.sha256(master).hexdigest() != context['full']['master_sha256']:
        raise ValueError('Source context does not match master')
    full = context['full']; indices = context['indices']; catalogue = context['catalogue']
    entities = [dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', b)) for b in
                re.findall(r'\{[^{}]*\}', lumps(bsp)[0].rstrip(b'\0').decode('cp1252'))]

    def binding(ref):
        matches = [e for e in entities if e.get('classname') == 'func_wall' and e.get('aw_ref') == str(ref['number'])]
        if len(matches) != 1 or not re.fullmatch(r'\*[1-9][0-9]*', matches[0].get('model', '')):
            raise ValueError('Harvest placement requires one exact dynamic brush entity')
        entity = matches[0]
        origin = list(map(float, entity['origin'].split())); angles = list(map(float, entity['angles'].split()))
        if len(origin) != 3 or len(angles) != 3 or not all(math.isfinite(v) for v in origin + angles):
            raise ValueError('Invalid runtime brush pose')
        return entity, origin, angles

    nodes, edges, plants, provenance = prepare_graph(context, region['source_references'], binding)
    rows = [f'AWH3 {len(nodes)} {len(edges)} {len(plants)} {len(indices)} {catalogue}']
    rows += ['{kind} {flags} {chance} {first} {count} {id}'.format(**n) + '\t' + n.get('label', '-') for n in nodes]
    rows += [' '.join(map(str, e)) for e in edges]
    for p in plants:
        rows.append('{key} {slot} {reference} {model} {flags} {first} {count} '.format(**p) +
                    ' '.join(format(v, '.9g') for v in p['origin'] + p['angles']) + ' ' + p['label'])
    payload = ('\n'.join(rows) + '\n').encode('ascii')
    if len(payload) > 65536:
        raise ValueError('Harvest catalogue exceeds 65536-byte runtime input bound')
    receipt = dict(format='AmiWind direct harvest 3', global_slots=len(indices), global_catalogue_sha256=catalogue, master_sha256=full['master_sha256'], bsp_sha256=region['sha256'],
                   catalogue_sha256=hashlib.sha256(payload).hexdigest(), source_placements=len(plants),
                   nodes=nodes, edges=edges, placements=provenance, respawn='disabled_first_stage',
                   leveled_resolution='first_encounter_persisted_seed_and_level_before_visibility',
                   scope='bounded catalogue; content admission and native acceptance remain required', native_acceptance='not_run')
    return payload, receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--master', type=Path, required=True); p.add_argument('--region-report', type=Path, required=True)
    p.add_argument('--bsp', type=Path, required=True); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--media-payload', type=Path, help='Optional complete-media id1 payload; verify and stage selected pickup cue')
    a = p.parse_args()
    region = json.loads(a.region_report.read_text())
    if not re.fullmatch('[a-z0-9_]{1,24}', region['name']):
        raise ValueError('Invalid map name')
    payload, receipt = prepare(a.master.read_bytes(), region, a.bsp.read_bytes())
    a.out.mkdir(parents=True, exist_ok=False)
    (a.out / ('harvest-' + region['name'] + '.txt')).write_bytes(payload)
    receipt['pickup_sound'] = stage_pickup_sound(a.media_payload, a.out)
    receipt['warnings'] = [receipt['pickup_sound']['warning']] if 'warning' in receipt['pickup_sound'] else []
    for warning in receipt['warnings']:
        print('[warning] ' + warning, file=sys.stderr)
    (a.out / 'harvest-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
