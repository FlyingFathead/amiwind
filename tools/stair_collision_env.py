# SPDX-License-Identifier: GPL-3.0-only
"""The stair collision method setting (CHIM-STAIR-COLLISION-MESH-47), apart from the shared converter modules.

How a flight of stairs gets its collision (tools/build.py and tools/chim_build.py --stair-collision-method):
0 (default) the convex pieces with the stair rules and the visible-tread rule (mesh_geometry.collision_pieces as
before); 1 a stairway collision mesh per flight that fails the geometric stair check (tools/stair_mesh.py). The CHIM
model builder resolves it into each mesh's profile (stair_collision 'mesh') and converts those meshes with the stair
worker (stair_mesh.mesh_unit_stair, unit kind 'mesh-stair'). Kept in its own module, so the default mesh units'
code keys (tools/code_key.py: what mesh_geometry and prepare_mesh_bsp reach) hold none of method 1's code: a change
to method 1 never rekeys a default build. Free of numpy/scipy.
"""
import os

STAIR_COLLISION_METHODS = ('0', '1')
STAIR_COLLISION_VARIABLE = 'AMIWIND_STAIR_COLLISION_METHOD'


def stair_collision_method():
    mode = os.environ.get(STAIR_COLLISION_VARIABLE, '').strip() or '0'
    if mode not in STAIR_COLLISION_METHODS:
        raise ValueError(STAIR_COLLISION_VARIABLE + ' must be 0 or 1, not %r' % mode)
    return mode


def export_stair_collision_method(method):
    """Export the resolved stair collision method for every converter worker (0 removes the variable)."""
    method = str(method)
    if method not in STAIR_COLLISION_METHODS:
        raise ValueError('stair collision method must be 0 or 1, not %r' % method)
    if method == '0':
        os.environ.pop(STAIR_COLLISION_VARIABLE, None)
    else:
        os.environ[STAIR_COLLISION_VARIABLE] = method
    return method
