# SPDX-License-Identifier: GPL-3.0-only
"""Remove only complete mesh faces outside the existing visible apron.

World terrain/PVS and all retained model collision trees stay unchanged. No
triangle reduction or new collision approximation is introduced here.
"""
from compact_bsp import compact
from player_hull import lumps
from replace_bsp_world import rows, verify_collision


def bound_visuals(raw, coverage):
    candidate, report = compact(raw, visual_bounds=coverage)
    source, target = lumps(raw), lumps(candidate)
    parsed = rows(source), rows(target)
    for new, old in enumerate(report['retained_models']):
        for hull in (0, 1, 2, 3):
            verify_collision(source, target, old, new, hull, parsed)
    if source[4] != target[4]:
        raise ValueError('Visual coverage compaction changed world PVS')
    report['collision_trees_verified'] = 4*len(report['retained_models'])
    report['acceptance'] = 'whole off-apron faces removed; target playtest pending'
    return candidate, report
