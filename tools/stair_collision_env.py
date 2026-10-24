# SPDX-License-Identifier: GPL-3.0-only
"""The stair collision method setting (CHIM-STAIR-COLLISION-MESH-47), apart from the shared converter modules.

How a flight of stairs gets its collision (tools/build.py and tools/chim_build.py --stair-collision-method):
1 (the default since v0.0.48-dev2, decided for the project 22 October 2026) a stairway collision mesh per flight that
fails the geometric stair check (tools/stair_mesh.py); 0 the convex pieces with the stair rules and the visible-tread
rule (mesh_geometry.collision_pieces as before), kept for A/B. The CHIM model builder resolves it per mesh: a mesh
whose drawn triangles hold a flight (stair_mesh.flight_unit, unit kind 'stair-flights') gets stair_collision 'mesh'
in its profile and is converted by the stair worker (stair_mesh.mesh_unit_stair, unit kind 'mesh-stair'); every
other mesh keeps the default worker, profile and key (method 1 is method 0 exactly on a mesh without a flight). Kept
in its own module, so the default mesh units' code keys (tools/code_key.py: what mesh_geometry and prepare_mesh_bsp
reach) hold none of method 1's code. Free of numpy/scipy.
"""
import os

STAIR_COLLISION_METHODS = ('0', '1')
STAIR_COLLISION_VARIABLE = 'AMIWIND_STAIR_COLLISION_METHOD'
DEFAULT_STAIR_COLLISION_METHOD = '1'


def stair_collision_method():
    mode = os.environ.get(STAIR_COLLISION_VARIABLE, '').strip() or DEFAULT_STAIR_COLLISION_METHOD
    if mode not in STAIR_COLLISION_METHODS:
        raise ValueError(STAIR_COLLISION_VARIABLE + ' must be 0 or 1, not %r' % mode)
    return mode


def export_stair_collision_method(method):
    """Export the resolved stair collision method for every converter worker (the default removes the variable)."""
    method = str(method)
    if method not in STAIR_COLLISION_METHODS:
        raise ValueError('stair collision method must be 0 or 1, not %r' % method)
    if method == DEFAULT_STAIR_COLLISION_METHOD:
        os.environ.pop(STAIR_COLLISION_VARIABLE, None)
    else:
        os.environ[STAIR_COLLISION_VARIABLE] = method
    return method
