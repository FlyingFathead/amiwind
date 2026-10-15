# SPDX-License-Identifier: GPL-3.0-only
"""Keep an included town's declared source dispositions in neighboring aprons.

This never supplies a missing owner to the ownership validator. Only an exact
original reference explicitly deferred by its town can leave a neighboring apron.
Nonsolid flora already drawn by that town remains the same verified sprite.
"""
import hashlib
import json
import re
from pathlib import Path

from chim.cut import source_ref
from chim.ownership import contains, original


def reconcile(specs, sections, out, regional, flora=None):
    out = Path(out)
    owners = []
    for section in sections:
        name = section['town']
        if name in regional:
            continue
        path = out / 'work' / name / 'source-catalogue.json'
        if not path.is_file():
            continue
        raw = path.read_bytes()
        catalogue = json.loads(raw)
        deferred = {r['number']: original(r) for r in catalogue.get('deferred', [])}
        if len(deferred) != len(catalogue.get('deferred', [])):
            raise ValueError('Repeated town deferred reference')
        owners.append((section, deferred, hashlib.sha256(raw).hexdigest()))
    flora_rows, assets = {}, {}
    if flora:
        receipt = json.loads((Path(flora) / 'tree-sprites.json').read_text())
        flora_rows = {r['number']: r for r in receipt['placements']}
        assets = {a['sprite_asset_name']: a for a in receipt['assets']}
    records = []
    # Named towns can share an apron too (for example Vivec and Seyda Neen).
    # The exact owner's catalogue governs every neighboring frame equally.
    for spec, section in zip(specs, sections):
        removed = set()
        dispositions = []
        for row in section['frame_ownership']['references']:
            if row['role'] != 'dependency':
                continue
            ref = row['original']; number = ref['number']
            matches = [(owner, deferred, digest) for owner, deferred, digest in owners
                       if contains(owner['frame_ownership']['core'], ref['position'])]
            if len(matches) != 1:
                continue  # The existing owner guard still diagnoses gaps/overlap.
            owner, deferred, digest = matches[0]
            if any(x['original']['number'] == number for x in owner['frame_ownership']['references']):
                continue
            if number not in deferred:
                continue  # Never infer a deferral to make a missing-owner gate pass.
            if original(ref) != deferred[number]:
                raise ValueError('Apron deferred original differs from its town')
            record = {'original': ref, 'owner': owner['town'],
                      'owner_catalogue_sha256': digest, 'disposition': 'deferred_by_owner'}
            if number in flora_rows:
                from prepare_world_flora import effective_representation, sprite_entity
                source = flora_rows[number]
                if original(source) != original(ref):
                    raise ValueError('Apron sprite original differs from its town')
                if (effective_representation(source) != 'sprite' or
                        source['source_collision']['mode'] != 'nonsolid'):
                    raise ValueError('Missing solid or mesh flora owner cannot be deferred')
                name = source['sprite_asset_name']
                if not re.fullmatch(r'progs/aw_flora/f_[0-9a-f]{16}\.spr', name):
                    raise ValueError('Invalid apron sprite asset path')
                asset = assets[name]
                data = (Path(flora) / name).read_bytes()
                if len(data) != asset['bytes'] or hashlib.sha256(data).hexdigest() != asset['sha256']:
                    raise ValueError('Apron sprite asset checksum mismatch')
                destination = out / 'work' / section['town'] / 'apron-sprites' / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists() and destination.read_bytes() != data:
                    raise ValueError('Conflicting apron sprite output')
                destination.write_bytes(data)
                centre = spec['frame']['centre']
                text = sprite_entity(source, asset, [centre[0]*.25, centre[1]*.25, 0.])
                entity = dict(re.findall(r'"([^"\n]*)"\s+"([^"\n]*)"', text))
                rows = section.setdefault('sprite_entities', [])
                if any(r.get('aw_ref') == str(number) for r in rows):
                    raise ValueError('Duplicate apron sprite reference')
                rows.append(entity)
                bound = dict(path=name, sha256=asset['sha256'], bytes=len(data),
                             file=destination.relative_to(out).as_posix())
                listed = section.setdefault('sprite_assets', [])
                previous = next((a for a in listed if a['path'] == name), None)
                if previous and previous['sha256'] != bound['sha256']:
                    raise ValueError('Conflicting apron sprite asset binding')
                if not previous:
                    listed.append(bound)
                record.update(disposition='existing_nonsolid_sprite', sprite=bound,
                              entity=entity)
            removed.add(number)
            dispositions.append(record)
        if not removed:
            continue
        spec['placements'] = [p for p in spec['placements'] if source_ref(p['ref']) not in removed]
        used = {p['variant'] for p in spec['placements']}
        spec['variants'] = {k: v for k, v in spec['variants'].items() if k in used}
        section['placements'] = [p for p in section['placements'] if p['ref'] not in removed]
        manifest = section['frame_ownership']
        manifest['references'] = [r for r in manifest['references'] if r['original']['number'] not in removed]
        manifest['pieces'] = [p for p in manifest['pieces'] if source_ref(p['ref']) not in removed]
        section['apron_dispositions'] = dispositions
        records.extend(dict(frame=section['town'], **record) for record in dispositions)
    return records


def supplement_seyda(specs, sections):
    """Supply missing Seyda apron meshes from their included logical owner.

    The legacy scenery carrier selects the core. CHIM needs a whole object in
    the neighboring apron too. Reuse the owner's exact compiled render and
    collision model, changing only its frame-local translation. Owned Seyda
    references and existing representations remain unchanged.
    """
    import copy
    from chim.ownership import capture, intersects, manifest, model_digest, source_failures
    from chim.world import f32, placed_box
    errors = source_failures(sections)
    if errors:
        raise ValueError('Cannot supplement invalid ownership: ' + '; '.join(errors[:3]))
    targets = [(spec, section) for spec, section in zip(specs, sections) if section['town'] == 'seyda']
    if not targets:
        return []
    if len(targets) != 1:
        raise ValueError('Repeated Seyda frame')
    target, section = targets[0]
    meta = section['frame_ownership']; coverage = meta['coverage']
    refs = {r['original']['number']: r['original'] for r in meta['references']}
    records = []
    for donor, owner in zip(specs, sections):
        if donor is target:
            continue
        if not intersects(coverage, owner['frame_ownership']['coverage']):
            continue
        owned = {r['original']['number']: r['original'] for r in owner['frame_ownership']['references']
                 if r['role'] == 'owner' and r['original']['number'] not in refs}
        pieces = {}
        for row in donor['placements']:
            number = source_ref(row['ref'])
            if number in owned:
                pieces.setdefault(number, []).append(row)
        dc, tc = donor['frame']['centre'], target['frame']['centre']
        shift = [(dc[k]-tc[k])*.25 for k in range(2)] + [0.]
        for number, rows in sorted(pieces.items()):
            boxes = []
            for row in rows:
                v = donor['variants'][row['variant']]
                lo, hi = placed_box([f32(x) for x in row['origin']], f32(row['yaw']),
                                    [f32(x) for x in v['lo']], [f32(x) for x in v['hi']])
                boxes.append([dc[k]+4*lo[k] for k in range(2)]+[dc[k]+4*hi[k] for k in range(2)])
            if not any(intersects(coverage, box) for box in boxes):
                continue
            hashes = []
            for row in rows:
                key = ('apron-owner', owner['town'], row['variant'])
                if key not in target['variants']:
                    v = copy.deepcopy(donor['variants'][row['variant']])
                    keys = []
                    for texture in v['texture_keys']:
                        mapped = ('apron-owner', owner['town'], texture)
                        target['textures'][mapped] = copy.deepcopy(donor['textures'][texture])
                        keys.append(mapped)
                    v['texture_keys'] = keys
                    target['variants'][key] = v
                target['placements'].append(dict(row, variant=key,
                    origin=tuple(row['origin'][k]+shift[k] for k in range(3))))
                hashes.append(model_digest(donor['variants'][row['variant']]['lumps']))
            ref = owned[number]; refs[number] = ref
            section['placements'].append({'ref': number, 'cell': list(ref['cell'])})
            records.append({'original': ref, 'owner': owner['town'], 'frame': 'seyda',
                            'disposition': 'missing_apron_mesh_from_included_owner',
                            'compiled_footprints': boxes, 'model_sha256': hashes})
    if records:
        section['frame_ownership'] = manifest(target, [capture(r) for r in refs.values()])
        section['apron_owner_supplements'] = records
    return records


def checked_seyda_supplements(section, placed):
    """Only bound dependency meshes may supplement the source-carrier parity."""
    records = section.get('apron_owner_supplements', [])
    if not records:
        return []
    meta = section['frame_ownership']
    refs = {r['original']['number']: r for r in meta['references']}
    pieces = {}
    for p in meta['pieces']:
        pieces.setdefault(source_ref(p['ref']), []).append(p['model_sha256'])
    accepted = []
    for row in records:
        ref = original(row['original']); number = ref['number']
        actual = refs.get(number)
        if (number in accepted or number not in placed or actual is None or
                actual['role'] != 'dependency' or original(actual['original']) != ref or
                row.get('frame') != 'seyda' or row.get('owner') == 'seyda' or
                row.get('disposition') != 'missing_apron_mesh_from_included_owner' or
                sorted(row['model_sha256']) != sorted(pieces.get(number, []))):
            raise ValueError('Unbound Seyda apron supplement')
        accepted.append(number)
    return accepted
