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


# Scenery, flames and creature models (prepare_scenery.model_geometry): 'node' is the game's rule (rule from OpenMW
# file components/nif/node.cpp, NiNode::read): a Morrowind NIF's root NiNode, the file's first record, named anything
# but Bip01, loses its WHOLE transform (rotation, translation and scale); any other root (a NiTriShape root such as
# contain_crate_01, root offset z -32) keeps its whole transform. 'morrowind' is the rule before v0.0.46 (rotation
# dropped, translation and scale kept), which lifted the Ebonheart dragon statue 327 units off its plaza
# (MESH-EBONHEART-DRAGON-PEDESTAL-42); 'legacy' the full transform. Both stay selectable (DON'T DELETE ANY METHOD).
SCENERY_ROOT_RULES = ('node', 'morrowind', 'legacy')
DEFAULT_SCENERY_ROOT_RULE = 'node'


def first_record(data, node):
    """True when node is the NIF's first record (pyffi Data.blocks; a reader without blocks: the first root)."""
    blocks = getattr(data, 'blocks', None)
    if blocks:
        return blocks[0] is node
    roots = getattr(data, 'roots', None) or []
    return bool(roots) and roots[0] is node


def scenery_root_local(local, node, N, is_first, rule=DEFAULT_SCENERY_ROOT_RULE):
    """Local 4x4 of a ROOT node for scenery under the given SCENERY_ROOT_RULES rule (see above)."""
    if rule not in SCENERY_ROOT_RULES:
        raise ValueError('Unknown scenery root rule %r (expected one of %s)' % (rule, ', '.join(SCENERY_ROOT_RULES)))
    if rule != 'node':
        return root_local(local, rule)
    name = node.name.decode('cp1252', 'replace') if isinstance(node.name, bytes) else str(node.name)
    if is_first and isinstance(node, N.NiNode) and name.casefold() != 'bip01':
        return np.eye(4)
    return np.array(local, dtype=float)


def has_root_rotation(local, tolerance=1e-4):
    """True when the root's rotation part (scale removed) is not the identity."""
    m = np.array(local, dtype=float)[:3, :3]
    scale = float(np.linalg.norm(m[0]))
    if scale == 0:
        return False
    return not np.allclose(m / scale, np.eye(3), atol=tolerance)
