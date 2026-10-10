# SPDX-License-Identifier: GPL-3.0-only
"""Shared NIF node rules used by every walker (scenery, flames, NPC parts).

Morrowind ignores a NIF root node's authored ROTATION (e.g. the 90-degree yaw on
Velothi interior kit pieces) but keeps its translation and scale
(BALMORA-TEMPLE-GEOMETRY-29). One implementation, so scenery and NPC assembly
cannot disagree. The previous NPC behaviour (full root transform) stays
selectable as the "legacy" rule (DON'T DELETE ANY METHOD).
"""
import numpy as np

ROOT_RULES = ('morrowind', 'legacy')
DEFAULT_ROOT_RULE = 'morrowind'


def check_root_rule(rule):
    if rule not in ROOT_RULES:
        raise ValueError('Unknown NPC root rule %r (expected one of %s)' % (rule, ', '.join(ROOT_RULES)))
    return rule


def root_local(local, rule=DEFAULT_ROOT_RULE):
    """Local 4x4 (row-vector convention) of a ROOT node under the given rule.

    morrowind: rotation dropped, translation kept, scale kept (rounded: a rotated
    unit-scale root gives e.g. 0.99999994, which breaks exact vertex sharing).
    legacy: the full transform unchanged."""
    check_root_rule(rule)
    local = np.array(local, dtype=float)
    if rule == 'morrowind':
        local[:3, :3] = np.eye(3) * round(float(np.linalg.norm(local[0, :3])), 6)
    return local


def has_root_rotation(local, tolerance=1e-4):
    """True when the root's rotation part (scale removed) is not the identity."""
    m = np.array(local, dtype=float)[:3, :3]
    scale = float(np.linalg.norm(m[0]))
    if scale == 0:
        return False
    return not np.allclose(m / scale, np.eye(3), atol=tolerance)
