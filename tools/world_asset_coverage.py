#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Report one build's source-bound world coverage without inventing completeness.

Inputs are normalized converter/map/readback receipts, not original game files.
Reports derived from owned inputs remain private. This module does not load game
catalogues into guest memory, modify images, or equate source assets with copies.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import textwrap

SCHEMA = 'AW-WORLD-COVERAGE-INPUT1'
RESULT = 'AW-WORLD-COVERAGE1'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=True).encode('ascii')).hexdigest()


def _sha(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Invalid SHA-256')
    return value


def _id(value):
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        raise ValueError('Invalid identity/label')
    return value


def _file(row):
    name = _id(row['path'])
    if '\\' in name or ':' in name or PurePosixPath(name).is_absolute() or any(
            part in ('', '.', '..') for part in name.split('/')):
        raise ValueError('File receipt requires a safe relative POSIX path')
    if type(row['bytes']) is not int or row['bytes'] < 0:
        raise ValueError('Invalid file byte count')
    return name.casefold(), (row['bytes'], _sha(row['sha256']))


def _index(rows, label):
    result = {}
    for row in rows:
        key = _id(row['id'])
        if key in result:
            raise ValueError('Duplicate ' + label + ': ' + key)
        result[key] = row
    return result


def _stage(evidence, name, source_digest, categories, build_id=None):
    stage = evidence.get(name)
    if stage is None:
        return None, set()
    if stage.get('status') != 'verified' or stage.get('source_catalogue_sha256') != source_digest:
        raise ValueError(name + ' is not bound to the verified source catalogue')
    covered = stage.get('categories', [])
    if len(covered) != len(set(covered)) or set(covered) - set(categories):
        raise ValueError(name + ' has unknown/duplicate categories')
    if build_id is not None and stage.get('build_id') != build_id:
        raise ValueError(name + ' belongs to another build')
    return stage, set(covered)


def report(evidence=None, build=None):
    """Return explicit nulls for missing evidence; counts describe this build only.

    source catalogue: categories (id/scope/three *_complete booleans), assets
    (id/category/available/sha256), placements (id/asset/space/admission/reason).
    Stage rows are covered only for their explicit categories. A missing stage
    never means zero, and a partial source scope never becomes a total.
    """
    if evidence is None:
        return dict(schema=RESULT, build=build or {}, status='unknown', rows=[],
                    source_catalogue_sha256=None,
                    limits=['World coverage unknown: this build has no source/map/readback coverage evidence.'])
    if evidence.get('schema') != SCHEMA:
        raise ValueError('Unknown world coverage input schema')
    actual_build = evidence['build']
    build_id = _id(actual_build['id'])
    if build is not None and actual_build != build:
        raise ValueError('Coverage belongs to another build')
    source = evidence['source']
    source_digest = digest(source)
    if evidence.get('source_catalogue_sha256') != source_digest:
        raise ValueError('Source catalogue digest differs')
    categories = _index(source['categories'], 'category')
    for row in categories.values():
        _id(row['scope'])
        if any(type(row.get(k)) is not bool for k in
               ('assets_complete', 'exterior_complete', 'interior_complete')):
            raise ValueError('Source scope completeness must be explicit boolean')
    if not source.get('pins'):
        raise ValueError('Source catalogue lacks input pins')
    for pin in source['pins']:
        _sha(pin['sha256']); _id(pin['label'])
    assets = _index(source['assets'], 'source asset')
    placements = _index(source['placements'], 'source placement')
    for a in assets.values():
        if a['category'] not in categories or type(a.get('available')) is not bool:
            raise ValueError('Invalid asset category/availability')
        if a['available']:
            _sha(a['sha256'])
    for p in placements.values():
        if p['asset'] not in assets or p['space'] not in ('exterior', 'interior'):
            raise ValueError('Placement lacks a source asset or valid space')
        if p['admission'] not in ('eligible', 'unsupported', 'unknown'):
            raise ValueError('Invalid source placement admission')
        if p['admission'] != 'eligible':
            _id(p['reason'])
    conversion, conversion_categories = _stage(evidence, 'conversion', source_digest, categories)
    maps_stage, map_categories = _stage(evidence, 'maps', source_digest, categories, build_id)
    installed, installed_categories = _stage(evidence, 'installed', source_digest, categories, build_id)
    routing, routing_categories = _stage(evidence, 'routing', source_digest, categories, build_id)
    converted = {}
    output_files = {}
    for row in conversion.get('records', []) if conversion else []:
        key = row['asset']
        if key not in assets or key in converted:
            raise ValueError('Duplicate or unknown converted source')
        a = assets[key]
        if row['category'] != a['category'] or a['category'] not in conversion_categories:
            raise ValueError('Conversion category mismatch')
        if not a['available'] or row['source_sha256'] != a['sha256']:
            raise ValueError('Conversion source hash/availability mismatch')
        output = [_file(f) for f in row['outputs']]
        if not output or len({p for p, _ in output}) != len(output):
            raise ValueError('Empty or duplicate conversion output closure')
        for path, identity in output:
            if path in output_files and output_files[path] != identity:
                raise ValueError('Conflicting conversion output path')
            output_files[path] = identity
        converted[key] = output
    file_index = {}
    for row in installed.get('files', []) if installed else []:
        path, identity = _file(row)
        if path in file_index:
            raise ValueError('Duplicate installed file path')
        file_index[path] = identity
    map_rows = _index(maps_stage.get('records', []), 'map') if maps_stage else {}
    per_placement = {key: [] for key in placements}
    map_closures = {}
    for key, row in map_rows.items():
        if not re.fullmatch('[a-z0-9_]{1,24}', key):
            raise ValueError('Invalid runtime map identity')
        bsp_path = PurePosixPath(row['bsp']['path'])
        if bsp_path.parent.name.casefold() != 'maps' or bsp_path.name.casefold() != key + '.bsp':
            raise ValueError('BSP filename differs from runtime map identity')
        representation = row.get('representation')
        if representation not in ('embedded', 'external_catalogue'):
            raise ValueError('Map requires an explicit placement representation')
        if representation == 'external_catalogue' and not row.get('catalogue'):
            raise ValueError('External placements require their runtime catalogue')
        if row.get('binding') not in ('verified', 'unknown') or row.get('admission') not in ('passed', 'failed', 'unknown'):
            raise ValueError('Map requires explicit binding and admission')
        files = [_file(row['bsp'])] + ([_file(row['catalogue'])] if row.get('catalogue') else [])
        identities = row['placements']
        if len(identities) != len(set(identities)):
            raise ValueError('Duplicate placement within one map')
        for placement in identities:
            if placement not in placements:
                raise ValueError('Map references unknown original placement')
            p = placements[placement]; category = assets[p['asset']]['category']
            if category not in map_categories or p['space'] != row['space']:
                raise ValueError('Map placement category/space mismatch')
            per_placement[placement].append(key)
        map_closures[key] = files
    reachable = set()
    for row in routing.get('records', []) if routing else []:
        key = row['map']
        if key not in map_rows or key in reachable or row['bsp_sha256'] != map_rows[key]['bsp']['sha256']:
            raise ValueError('Routing is duplicate or not bound to current map bytes')
        reachable.add(key)
    def present(files):
        return all(file_index.get(path) == value for path, value in files)
    def placement_status(key, category):
        p = placements[key]; a = assets[p['asset']]
        if not a['available']: return 'missing_source', [], []
        if p['admission'] != 'eligible': return p['admission'], [], []
        if category not in conversion_categories: return 'conversion_unknown', [], []
        if p['asset'] not in converted: return 'not_converted_for_build', [], []
        if category not in map_categories: return 'map_unknown', [], []
        bound = [m for m in per_placement[key] if map_rows[m]['binding'] == 'verified']
        if not bound: return 'missing_map_binding', [], []
        admitted = [m for m in bound if map_rows[m]['admission'] == 'passed']
        if not admitted: return 'map_not_admitted', [], []
        packaged = [m for m in admitted if present(map_closures[m] + converted[p['asset']])]
        if category not in installed_categories: return 'package_unknown', admitted, []
        if not packaged: return 'missing_or_different_packaged_files', admitted, []
        return 'installed', admitted, packaged
    rows = []
    for category, scope in categories.items():
        selected_assets = {key for key,a in assets.items() if a['category'] == category}
        converted_set = selected_assets & set(converted)
        packaged_assets = {key for key in converted_set if present(converted[key])}
        row = dict(category=category, scope=scope['scope'], assets=dict(
            observed_source=len(selected_assets),
            source_total=len(selected_assets) if scope['assets_complete'] else None,
            converted=len(converted_set) if category in conversion_categories else None,
            still_missing_outputs=len(selected_assets-converted_set) if category in conversion_categories and scope['assets_complete'] else None,
            same_output_installed=len(packaged_assets) if category in conversion_categories & installed_categories else None,
            missing_source=sum(not assets[key]['available'] for key in selected_assets)))
        row['placements'] = {}
        for space in ('exterior', 'interior'):
            chosen={key for key,p in placements.items() if p['asset'] in selected_assets and p['space']==space}
            can_place=set(); in_image=set(); can_reach=set(); copies=0; reasons=Counter()
            for key in chosen:
                reason, admitted, packaged = placement_status(key, category)
                reasons[reason] += 1
                if admitted: can_place.add(key)
                if packaged: in_image.add(key)
                if set(packaged) & reachable: can_reach.add(key)
                copies += len(packaged)
            place_known=category in conversion_categories & map_categories
            image_known=place_known and category in installed_categories
            reach_known=image_known and category in routing_categories
            row['placements'][space]=dict(observed_source=len(chosen),
                source_total=len(chosen) if scope[space+'_complete'] else None,
                can_be_placed=len(can_place) if place_known else None,
                still_missing_from_admitted_maps=len(chosen-can_place) if place_known and scope[space+'_complete'] else None,
                installed_unique=len(in_image) if image_known else None,
                installed_map_copies=copies if image_known else None,
                reachable_verified=len(can_reach) if reach_known else None,
                reasons=dict(sorted(reasons.items())))
        rows.append(row)
    return dict(schema=RESULT, build=actual_build, status='evidence_reported', rows=rows,
        source_catalogue_sha256=source_digest,
        current_source_bytes_reverified=False,
        limits=['Counts describe supplied evidence for this exact build, not all past conversions.',
                'Source totals require explicit complete scope; unknown is not zero.',
                'Can be placed requires original metadata, converted dependencies, map binding and heap admission.',
                'Installed requires byte-identical map/catalogue/model closure; reachable needs separate route evidence.',
                'Recorded source hashes are compared; current original input bytes are not re-read here.',
                'Unique source assets, original placements and overlapping map copies are distinct units.'])


def terminal(result, width=None):
    """Final build footer; width is discovered at print time, fallback 80."""
    if width is None: width=shutil.get_terminal_size(fallback=(80, 24)).columns
    if type(width) is not int or width < 1: raise ValueError('Invalid terminal width')
    lines=['-'*width]
    def add(text):
        lines.extend(textwrap.wrap(text,width=width,break_long_words=True,break_on_hyphens=False) or [''])
    def n(value):return 'unknown' if value is None else f'{value:,}'
    add('World asset coverage')
    if result['status']=='unknown':
        add(result['limits'][0]);return '\n'.join(lines)+'\n'
    add('Build: '+result['build']['id'])
    for row in result['rows']:
        a=row['assets'];add(f"{row['category']}: assets converted {n(a['converted'])}/{n(a['source_total'])}; still missing outputs {n(a['still_missing_outputs'])}; same outputs installed {n(a['same_output_installed'])}; missing source {n(a['missing_source'])}.")
        add('Scope: '+row['scope'])
        for space,p in row['placements'].items():
            add(f"  {space}: can be placed {n(p['can_be_placed'])}/{n(p['source_total'])}; still missing {n(p['still_missing_from_admitted_maps'])}; installed originals {n(p['installed_unique'])}; map copies {n(p['installed_map_copies'])}; reachable verified {n(p['reachable_verified'])}.")
            if p['reasons']:add('    Status: '+', '.join(f'{k}={v}' for k,v in p['reasons'].items()))
    add('Unknown is not zero. Placement counts are unique originals; map copies are separate.')
    return '\n'.join(lines)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,help='Optional normalized source/converter/map/readback evidence')
    parser.add_argument('--build-id',help='Required build identity when checking supplied evidence')
    parser.add_argument('--json-out',type=Path)
    args=parser.parse_args()
    evidence=json.loads(args.input.read_text()) if args.input else None
    if evidence and (not args.build_id or evidence['build']['id']!=args.build_id):
        raise ValueError('Explicit current build ID must match coverage evidence')
    result=report(evidence,build={'id':args.build_id} if not evidence and args.build_id else None)
    if args.json_out:
        with args.json_out.open('x',encoding='utf-8') as output:json.dump(result,output,indent=2);output.write('\n')
    print(terminal(result),end='')


if __name__=='__main__':main()
