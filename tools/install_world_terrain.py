#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Validate and stage a complete private terrain directory before scenery."""
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def install(terrain, id1):
    terrain, id1 = Path(terrain), Path(id1)
    receipt_path = terrain/'world-regions.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    if (receipt.get('format') != 'AmiWind playable terrain regions 1'
            or receipt.get('diagnostic_subset')):
        raise ValueError('Complete playable terrain receipt required')
    rows = receipt.get('regions', [])
    if not 1 <= len(rows) <= 8192:
        raise ValueError('Terrain count outside runtime bounds')
    packet = (terrain/'regions.awr').read_bytes()
    if packet[:4] != b'AWR2' or len(packet) != 64+52*len(rows) or struct.unpack_from('<I',packet,4)[0] != len(rows):
        raise ValueError('Terrain runtime directory/count mismatch')
    current = (id1/'world/regions.awr').read_bytes()
    refinement = receipt.get('refinement', {})
    baseline = {}
    if packet != current:
        if (hashlib.sha256(current).hexdigest() != refinement.get('base_directory_sha256')
                or packet[8:64] != current[8:64]
                or hashlib.sha256(packet).hexdigest() != refinement.get('directory_sha256')):
            raise ValueError('Terrain refinement differs from source scene directory')
        base_receipt = terrain/'base-world-regions.json'
        if digest(base_receipt) != refinement.get('base_regions_receipt_sha256'):
            raise ValueError('Terrain baseline receipt differs')
        baseline = {r['name']:r for r in json.loads(base_receipt.read_text(encoding='utf-8'))['regions']}
    replacements = []
    changed = set(refinement.get('children', []))
    for i,row in enumerate(rows):
        name = f'vf{i:04d}'
        if row.get('name') != name:
            raise ValueError('Terrain names must match runtime sequence')
        values = [*row['origin'],*row['core'][0],*row['core'][1],*row['coverage'][0],*row['coverage'][1]]
        if not all(math.isfinite(v) for v in values):
            raise ValueError('Nonfinite terrain coordinates')
        expected = struct.pack('<8s11f', name.encode('ascii'), *row['origin'],
                               *row['core'][0], *row['core'][1],
                               *row['coverage'][0], *row['coverage'][1])
        if packet[64+i*52:64+(i+1)*52] != expected:
            raise ValueError('Terrain row differs from runtime directory: '+name)
        source = terrain/name/'scene.bsp'
        if (not source.is_file() or source.is_symlink()
                or digest(source) != row['converted']['sha256']
                or source.stat().st_size != row['converted']['bytes']):
            raise ValueError('Terrain payload missing or changed: '+name)
        target = id1/'maps'/(name+'.bsp')
        if target.exists() and digest(target) == row['converted']['sha256']:
            continue
        if name not in changed:
            raise ValueError('Unchanged terrain differs from source scene: '+name)
        if packet == current:
            raise ValueError('Already refined terrain payload differs: '+name)
        if name in baseline:
            if not target.is_file() or digest(target) != baseline[name]['converted']['sha256']:
                raise ValueError('Source parent terrain changed: '+name)
        elif target.exists():
            raise ValueError('Unexpected existing child terrain: '+name)
        replacements.append((source,target))
    # No staging until every directory row and payload has passed.
    for source,target in replacements:
        shutil.copyfile(source,target)
        if digest(source) != digest(target):
            raise ValueError('Terrain read-back failed')
    (id1/'world/regions.awr').write_bytes(packet)
    return {'regions':len(rows),'replaced_maps':len(replacements),
            'directory_sha256':hashlib.sha256(packet).hexdigest(),
            'terrain_receipt_sha256':digest(receipt_path),
            'target_validation':'pending'}
