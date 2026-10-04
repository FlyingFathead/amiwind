#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Staged source-placement policy; this module does not activate a sprite overlay.

One original reference has one renderer decision across all loading copies.
Source transforms remain exact; geometry and collision are separate consumers.
"""
import copy
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _finite(values, label):
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or
           not math.isfinite(v) for v in values):
        raise ValueError('Invalid ' + label)


def _bounds(bounds, dimensions, label):
    if len(bounds) != 2 or any(len(edge) != dimensions for edge in bounds):
        raise ValueError('Invalid ' + label)
    _finite([v for edge in bounds for v in edge], label)
    if any(bounds[0][k] > bounds[1][k] for k in range(dimensions)):
        raise ValueError('Reversed ' + label)


def balmora_source_zone(settings):
    """The 64-core outer rectangle, not the per-core drawing/loading apron."""
    centre, scale, bounds = settings['centre'], settings['scale'], settings['bounds']
    if len(centre) != 2:
        raise ValueError('Invalid Balmora centre')
    _finite(centre + [scale], 'Balmora coordinate conversion')
    _bounds(bounds, 2, 'Balmora local core bounds')
    if scale <= 0:
        raise ValueError('Invalid Balmora world scale')
    return [[centre[k] + edge[k] / scale for k in range(2)] for edge in bounds]


def load_policy(path=None, balmora_settings=None):
    policy = json.loads(Path(path or ROOT / 'config/world-flora.json').read_text(encoding='utf-8'))
    if policy.get('format') != 1 or policy.get('stage') != 'selection_only':
        raise ValueError('Unsupported world flora policy')
    exclusion = policy['mesh_exclusion']
    if type(exclusion.get('enabled')) is not bool:
        raise ValueError('Mesh exclusion enabled must be boolean')
    if exclusion.get('coordinate_space') != 'tes3_source_xy' or exclusion.get('z') != 'unbounded':
        raise ValueError('Unsupported flora exclusion coordinates')
    if exclusion.get('selection') != 'transformed_bounds_intersect':
        raise ValueError('Flora exclusion must preserve whole footprints')
    if exclusion.get('zone_source') == 'balmora_core':
        settings = balmora_settings or json.loads((ROOT / 'config/balmora.json').read_text(encoding='utf-8'))
        zone = balmora_source_zone(settings)
        # An auditable assertion prevents a later town-boundary change from
        # silently changing the agreed performance-comparison exclusion.
        if exclusion.get('source_bounds') != zone:
            raise ValueError('Flora exclusion differs from current Balmora core')
    elif exclusion.get('zone_source') == 'explicit':
        zone = exclusion['source_bounds']
    else:
        raise ValueError('Unsupported flora exclusion source')
    _bounds(zone, 2, 'flora source exclusion')
    policy['mesh_exclusion']['source_bounds'] = zone
    return policy


def source_key(reference, master_sha256):
    if len(master_sha256) != 64 or any(c not in '0123456789abcdef' for c in master_sha256):
        raise ValueError('Invalid source master hash')
    cell, number = reference['cell'], reference['number']
    if len(cell) != 2 or any(type(v) is not int for v in cell) or type(number) is not int or not 0 <= number <= 0xffffffff:
        raise ValueError('Invalid exterior source identity')
    return (master_sha256, 'exterior', tuple(cell), number)


def stable_sprite_name(model):
    normalized = model.replace('\\', '/').casefold().removeprefix('meshes/')
    if not normalized or '..' in normalized.split('/'):
        raise ValueError('Invalid flora model path')
    return 'progs/aw_flora/f_' + hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16] + '.spr'


def transformed_bounds(model_bounds, reference):
    """TES3 clockwise Z, then Y, then X; scale before rotate and translate."""
    _bounds(model_bounds, 3, 'flora model bounds')
    position, rotation, scale = reference['position'], reference['rotation_radians'], reference['scale']
    if len(position) != 3 or len(rotation) != 3:
        raise ValueError('Invalid flora transform dimensions')
    _finite(list(position) + list(rotation) + [scale], 'flora source transform')
    if scale <= 0:
        raise ValueError('Flora source scale must be positive')
    ax, ay, az = [-a for a in rotation]
    cx, sx, cy, sy, cz, sz = math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay), math.cos(az), math.sin(az)
    points = []
    for x in (model_bounds[0][0], model_bounds[1][0]):
        for y in (model_bounds[0][1], model_bounds[1][1]):
            for z in (model_bounds[0][2], model_bounds[1][2]):
                xx, yy, zz = x * scale, y * scale, z * scale
                xx, yy = cz * xx - sz * yy, sz * xx + cz * yy
                xx, zz = cy * xx + sy * zz, -sy * xx + cy * zz
                yy, zz = cx * yy - sx * zz, sx * yy + cx * zz
                points.append([xx + position[0], yy + position[1], zz + position[2]])
    return [[min(p[k] for p in points) for k in range(3)],
            [max(p[k] for p in points) for k in range(3)]]


def placement(reference, model_bounds, policy, master_sha256):
    """Retain every exact source transform; never discard large or tilted trees."""
    key = source_key(reference, master_sha256)
    bounds = transformed_bounds(model_bounds, reference)
    exclusion = policy['mesh_exclusion']
    zone = exclusion['source_bounds']
    touches = exclusion['enabled'] and all(bounds[1][k] >= zone[0][k] and bounds[0][k] <= zone[1][k] for k in range(2))
    crossing = touches and not all(zone[0][k] <= bounds[0][k] and bounds[1][k] <= zone[1][k] for k in range(2))
    return {**copy.deepcopy(reference), 'source_key': key, 'bounds': bounds,
            'renderer_policy': 'mesh' if touches else 'sprite',
            'exclusion_boundary_crossing': crossing,
            'sprite_asset_name': stable_sprite_name(reference['model']) if not touches else None,
            'sprite_selected': not touches,
            'requires_interaction': reference.get('type') != 'STAT' or bool(reference.get('script')),
            'runtime_activation': False}


def selection_receipt(placements):
    keys = [p['source_key'] for p in placements]
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate original flora source reference')
    mesh = sum(p['renderer_policy'] == 'mesh' for p in placements)
    return {'format': 'AmiWind staged flora selection 1', 'runtime_activation': False,
            'original_instances': len(keys), 'mesh_instances': mesh,
            'sprite_instances': len(keys) - mesh,
            'nonunit_scale_instances': sum(p['scale'] != 1 for p in placements),
            'tilted_instances': sum(any(a != 0 for a in p['rotation_radians'][:2]) for p in placements),
            'boundary_crossing_instances': sum(p['exclusion_boundary_crossing'] for p in placements),
            'interactive_instances': sum(p['requires_interaction'] for p in placements)}
