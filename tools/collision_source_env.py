# SPDX-License-Identifier: GPL-3.0-only
"""The collision source setting (COLLISION-RCN-SCOPE-32, COLLISION-NC-FLAGS-32), apart from the converter modules.

Which triangles of a Morrowind model collide (tools/build.py and tools/chim_build.py --collision-source):

- authored (the default since v0.0.48-dev2): one rule for every mesh converter (tools/collision_source.py): the
  model's root RootCollisionNode when it has one, else its drawn triangles; NC* and NCC models are nonsolid for the
  player, MRK editor-marker shapes and AvoidNode subtrees never collide;
- profile: the rule before v0.0.48-dev2, kept for A/B: each converter's profile opts into the RootCollisionNode
  (collision_source root_node or root_node_or_visual; without it the drawn triangles collide), and only the exact
  strings NC and NCO, anywhere in the model, make it nonsolid.

Free of numpy, PyFFI and the converter modules.
"""
import os

COLLISION_SOURCES = ('authored', 'profile')
COLLISION_SOURCE_VARIABLE = 'AMIWIND_COLLISION_SOURCE'
DEFAULT_COLLISION_SOURCE = 'authored'


def collision_source_mode():
    mode = os.environ.get(COLLISION_SOURCE_VARIABLE, '').strip() or DEFAULT_COLLISION_SOURCE
    if mode not in COLLISION_SOURCES:
        raise ValueError(COLLISION_SOURCE_VARIABLE + ' must be authored or profile, not %r' % mode)
    return mode


def export_collision_source(mode):
    """Export the resolved collision source rule for every converter worker (the default removes the variable)."""
    mode = str(mode)
    if mode not in COLLISION_SOURCES:
        raise ValueError('collision source must be authored or profile, not %r' % mode)
    if mode == DEFAULT_COLLISION_SOURCE:
        os.environ.pop(COLLISION_SOURCE_VARIABLE, None)
    else:
        os.environ[COLLISION_SOURCE_VARIABLE] = mode
    return mode
