# SPDX-License-Identifier: GPL-3.0-only
"""Explicit scenery assemblies, independent of per-frame visibility.

Assembly membership permits only named visible activators. It does not execute
scripts or expose editor markers. The legacy origin selection for unrelated
scenery is retained until the broader starting-area coverage audit is accepted.
"""
import json
import math
from pathlib import Path


def load_groups():
    return json.loads((Path(__file__).resolve().parents[1] /
                       'config/scenery_groups.json').read_text())


def select_source_refs(placements, centre, radius, groups):
    """Keep complete, uniquely resolved assemblies when any member is in scope."""
    memberships = {}
    active = {}
    for name, group in groups.items():
        members = {key.casefold(): kind for key, kind in group['members'].items()}
        found = {}
        for ref in placements:
            key = ref['id'].casefold()
            if key not in members or ref.get('deleted'):
                continue
            if key in found:
                raise ValueError('Ambiguous assembly member: ' + key)
            if ref.get('type') != members[key] or not ref.get('model'):
                raise ValueError('Invalid assembly member: ' + key)
            found[key] = ref
        if not any(math.hypot(r['position'][0]-centre[0],
                              r['position'][1]-centre[1]) <= radius
                   for r in found.values()):
            continue
        missing = sorted(set(members)-set(found))
        if missing:
            raise ValueError('Incomplete assembly ' + name + ': ' + ', '.join(missing))
        active[name] = {**group, 'references': [r['number'] for r in found.values()]}
        for ref in found.values():
            memberships.setdefault(ref['number'], []).append(name)
    selected = []
    for ref in placements:
        if ref.get('deleted') or not ref.get('model'):
            continue
        member = memberships.get(ref['number'], [])
        ordinary = ref.get('type') in ('STAT', 'DOOR') and math.hypot(
            ref['position'][0]-centre[0], ref['position'][1]-centre[1]) <= radius
        if member or ordinary:
            selected.append({**ref, 'scene_groups': member})
    return selected, active


def validate_groups(references, groups):
    present = {r['number'] for r in references}
    for name, group in groups.items():
        missing = set(group['references'])-present
        if missing:
            raise ValueError('Converted assembly is incomplete: ' + name)


def select_runtime_refs(index, centre, scale, extent):
    """Intersect whole assembly bounds; preserve all of its attachments."""
    bounds = index.get('runtime_bounds', [[-extent, -extent], [extent, extent]])
    def intersects(low, high):
        return all((high[a]-centre[a])*scale >= bounds[0][a] and
                   (low[a]-centre[a])*scale <= bounds[1][a] for a in range(2))
    references = index['references']
    groups = index.get('groups', {})
    validate_groups(references, groups)
    enabled = set()
    for name, group in groups.items():
        members = [r for r in references if r['number'] in group['references']]
        low = [min(r['bounds'][0][a] for r in members) for a in range(2)]
        high = [max(r['bounds'][1][a] for r in members) for a in range(2)]
        if intersects(low, high):
            enabled.add(name)
    selected, rejected = [], []
    for ref in references:
        member = set(ref.get('scene_groups', []))
        inside = intersects(*ref['bounds']) if 'runtime_bounds' in index else all(
            abs((ref['position'][a]-centre[a])*scale) <= extent for a in range(2))
        # A group is selected as a whole, never partially by an origin fallback.
        accepted = bool(member & enabled) if member else inside
        if accepted:
            selected.append(ref)
        else:
            rejected.append({'reference': ref['number'], 'id': ref['id'],
                             'reason': 'outside assembly bounds' if member else
                                       'outside runtime coverage'})
    return selected, {'selected_groups': sorted(enabled), 'omitted': rejected}
