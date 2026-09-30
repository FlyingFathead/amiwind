# SPDX-License-Identifier: GPL-3.0-only
"""Deterministic exterior sub-cells with complete intersecting placements.

All coordinates are shared local world coordinates, including across regions.
Overlap is measured from the whole object bounds, never just its origin.
"""
import json
import math
from pathlib import Path


def visual_profile(source, triangles):
    """Reduce organic props only; open architectural shells must stay intact.

    Global triangle quotas collapse the boundaries of Hlaalu facade panels.
    Their original triangles are already modest and are merged into coplanar
    BSP surfaces by the subsequent conversion stage.
    """
    stem = source.replace('\\', '/').rsplit('/', 1)[-1].casefold()
    target = triangles
    texture_size = 32
    if stem.startswith('flora_'):
        target = 120
    elif stem == 'siltstrider.nif':
        # Share the inspected Seyda Neen profile. A separate 400-triangle target
        # collapses the Strider's open leg/body components into disconnected strips.
        from scenery_selection import load_groups
        return dict(load_groups()['silt_strider']['visual_profiles']['meshes/r/siltstrider.nif'])
    elif stem.startswith('terrain_rock_'):
        target = 64
        texture_size = 64
    profile = {'ratio': min(1., target / max(1, triangles)), 'texture_size': texture_size}
    # Convex approximation closes these authored underpasses. Keep each
    # collision surface instead, independent of visible mesh reduction.
    if stem in ('ex_hlaalu_bridge_05.nif', 'ex_hlaalu_bridge_06.nif', 'ex_hlaalu_bridge_07.nif', 'ex_velothi_temple_02.nif',
                'ex_hlaalu_b_02.nif', 'ex_hlaalu_b_04.nif', 'ex_hlaalu_b_13.nif', 'ex_hlaalu_b_15.nif',
                'ex_hlaalu_b_17.nif', 'ex_hlaalu_dsteps_03.nif'):
        profile['hollow_collision'] = True
        profile['exact_collision_bevels'] = True
    return profile


def config():
    return json.loads((Path(__file__).resolve().parents[1] / 'config/balmora.json').read_text())


def intersects(a, b):
    return all(a[1][i] >= b[0][i] and a[0][i] <= b[1][i] for i in range(2))


def local_bounds(reference, centre, scale):
    return [[(point[i] - centre[i]) * scale for i in range(2)]
            for point in reference['bounds']]


def regions(settings):
    size = settings['core_size']
    low, high = settings['bounds']
    if size <= 0 or any((high[i] - low[i]) % size for i in range(2)):
        raise ValueError('Sub-cell bounds must contain complete cores')
    if settings['overlap'] < math.sqrt(2) * settings['draw_distance'] + settings['hysteresis'] + 32:
        raise ValueError('Overlap must cover visibility, hysteresis and collision margin')
    out = []
    for y in range(low[1], high[1], size):
        for x in range(low[0], high[0], size):
            core = [[x, y], [x + size, y + size]]
            margin = settings['overlap']
            coverage = [[max(low[i], core[0][i] - margin) for i in range(2)],
                        [min(high[i], core[1][i] + margin) for i in range(2)]]
            out.append({'name': f'bm{len(out):03d}', 'core': core, 'coverage': coverage})
    if len(out) > 64:
        raise ValueError('Region directory exceeds native capacity')
    return out


def owner(point, entries, current=None, hysteresis=0):
    if not all(math.isfinite(v) for v in point[:2]):
        raise ValueError('Nonfinite region position')
    if current is not None:
        a, b = entries[current]['core']
        if all(a[i] - hysteresis <= point[i] <= b[i] + hysteresis for i in range(2)):
            return current
    for i, entry in enumerate(entries):
        a, b = entry['core']
        if all(a[k] <= point[k] < b[k] for k in range(2)):
            return i
    # The outermost east/north edge belongs to its final core.
    for i, entry in enumerate(entries):
        a, b = entry['core']
        if all(a[k] <= point[k] <= b[k] for k in range(2)):
            return i
    return None


def select_references(index, entry, settings):
    return [r['number'] for r in index['references']
            if intersects(local_bounds(r, settings['centre'], settings['scale']), entry['coverage'])]


def audit_coverage(index, entries, settings):
    selected = [set(select_references(index, e, settings)) for e in entries]
    expected = {r['number'] for r in index['references']
                if intersects(local_bounds(r, settings['centre'], settings['scale']), settings['bounds'])}
    present = set().union(*selected)
    if present != expected:
        raise ValueError('Sub-cell union loses or invents references')
    return {'source_references': len(index['references']), 'covered_references': len(present),
            'lost_references': sorted(expected - present), 'region_count': len(entries),
            'max_region_references': max(map(len, selected), default=0),
            'overlap': settings['overlap'], 'hysteresis': settings['hysteresis'],
            'draw_distance': settings['draw_distance']}
