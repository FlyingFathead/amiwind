# SPDX-License-Identifier: GPL-3.0-only
"""The collision mesh setting (AMIWIND_COLLISION_MESH; COLLISION-WORLDWIDE-REDUCTION-64).

A module of its own (BUILD-UNIT-KEYS-REACH-64): in tools/collision_source_env.py its top-level constants were
import-time code of that module, so they re-keyed every unit cache that imports it (the residents, the CHIM room
shells) and put the setting among their keyed settings, although only reduced_collision_mesh reads it.

Which mesh a model WITHOUT authored collision (source 'visual') collides with:
- original: its drawn triangles at full source detail, while the image draws the reduced mesh (the rule up to v0.0.64);
- reduced: the reduced drawn mesh (the visual reduction keeps every closed edge), with the ORIGINAL walkable faces
  (normal z at least player_hull.WALKABLE_Z) in place of the reduced ones, so floors, treads and walkways stay exact;
- reduced-all: the reduced drawn mesh alone (a measurement variant).
Only a geometric reduction counts (a profile ratio, the scenery reduction); flattened panels, visual primitives and
exterior visibility selections keep the original triangles. RootCollisionNode models keep their authored collision.
"""
import os

COLLISION_MESHES = ('original', 'reduced', 'reduced-all')
COLLISION_MESH_VARIABLE = 'AMIWIND_COLLISION_MESH'
DEFAULT_COLLISION_MESH = 'original'


def collision_mesh_mode():
    mode = os.environ.get(COLLISION_MESH_VARIABLE, '').strip() or DEFAULT_COLLISION_MESH
    if mode not in COLLISION_MESHES:
        raise ValueError(COLLISION_MESH_VARIABLE + ' must be original, reduced or reduced-all, not %r' % mode)
    return mode
