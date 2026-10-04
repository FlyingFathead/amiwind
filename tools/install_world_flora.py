#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Validate private flora output against installed rocks/mushrooms before copying."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_asset(root, name):
    if (not isinstance(name, str) or not re.fullmatch(r'progs/aw_flora/f_[0-9a-f]{16}\.spr', name)
            or len(name.encode('ascii')) >= 64):
        raise ValueError('Unsafe flora asset path')
    root = Path(root).resolve()
    path = root.joinpath(*PurePosixPath(name).parts)
    if not path.resolve().is_relative_to(root) or path.is_symlink():
        raise ValueError('Flora asset escapes its root')
    return path


def install(overlay, id1, scenery_acceptance):
    overlay, id1 = Path(overlay), Path(id1)
    receipt_path = overlay / 'world-flora.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    if (receipt.get('format') != 'AmiWind world flora overlay 1'
            or receipt.get('diagnostic_subset')):
        raise ValueError('Complete production flora overlay required')
    if receipt.get('base_world_scenery_receipt_sha256') != scenery_acceptance.get('receipt_sha256'):
        raise ValueError('Flora overlay does not match installed rock/mushroom receipt')
    if digest(id1 / 'gfx/palette.lmp') != receipt.get('palette_sha256'):
        raise ValueError('Flora palette differs from image palette')
    rows = receipt.get('regions')
    count = scenery_acceptance['regions']
    if not isinstance(rows, list) or [r.get('name') for r in rows] != [f'vf{i:04d}' for i in range(count)]:
        raise ValueError('Flora overlay does not cover every installed region in order')
    replacements = []
    originals = set()
    for row in rows:
        name = row['name']
        target = id1 / 'maps' / (name + '.bsp')
        source = overlay / name / 'scene.bsp'
        if not target.is_file() or digest(target) != row.get('base_sha256'):
            raise ValueError('Flora input differs from installed rock/mushroom map: ' + name)
        if (not source.is_file() or digest(source) != row.get('sha256')
                or source.stat().st_size != row.get('bytes')):
            raise ValueError('Flora output missing or changed: ' + name)
        if row.get('retained_content', {}).get('retained_content') != 'verified':
            raise ValueError('Flora content preservation evidence missing: ' + name)
        local = set()
        references = row.get('source_references')
        if not isinstance(references, list):
            raise ValueError('Flora source coverage missing')
        for reference in references:
            key = json.dumps(reference['source_key'], sort_keys=True, separators=(',', ':'))
            if key in local:
                raise ValueError('Duplicate original flora in one region: ' + name)
            local.add(key)
        originals.update(local)
        replacements.append((source, target))
    if len(originals) != receipt.get('covered_unique_original_refs'):
        raise ValueError('Flora source coverage total differs from receipt')
    assets = receipt.get('assets')
    if not isinstance(assets, list) or not assets:
        raise ValueError('Flora shared sprite assets missing')
    asset_names = set()
    for asset in assets:
        name = asset['sprite_asset_name']
        source, target = safe_asset(overlay, name), safe_asset(id1, name)
        if name in asset_names:
            raise ValueError('Duplicate flora shared sprite path')
        asset_names.add(name)
        if not source.is_file() or digest(source) != asset.get('sha256'):
            raise ValueError('Flora shared sprite missing or changed: ' + name)
        # Validate the actual format, not only receipt hashes. The final map
        # audit uses the exact target ABI and counts only resident dependencies.
        raw = source.read_bytes()
        if len(raw) < 36 or raw[:8] != b'IDSP\x01\x00\x00\x00':
            raise ValueError('Invalid flora sprite format: ' + name)
        if target.exists() and digest(target) != asset['sha256']:
            raise ValueError('Flora sprite would overwrite different content: ' + name)
        replacements.append((source, target))
    # Every validation above precedes mutation, including stale later regions.
    for source, target in replacements:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if digest(target) != digest(source):
            raise ValueError('Flora staging readback failed')
    return {'status': 'staged', 'runtime_validation': 'pending',
            'receipt_sha256': digest(receipt_path), 'regions': count,
            'covered_unique_original_refs': len(originals), 'shared_sprite_types': len(assets),
            'palette_sha256': receipt['palette_sha256'],
            'deferred_references': len(receipt.get('deferred_references', [])),
            'source_selection': receipt.get('source_selection', {}),
            'final_memory_gate': 'pending'}
