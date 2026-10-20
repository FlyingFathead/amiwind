# SPDX-License-Identifier: GPL-3.0-only
"""Fictional meshes only: the NIF root rule of the scenery converter. The game's rule (rule from OpenMW file
components/nif/node.cpp, NiNode::read): a root NiNode, the file's first record, named anything but Bip01, loses
its whole transform; any other root (a NiTriShape root such as contain_crate_01) keeps it
(BALMORA-TEMPLE-GEOMETRY-29 for the rotation, MESH-EBONHEART-DRAGON-PEDESTAL-42 for the translation and scale)."""
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest

sys.path[:0] = [str(Path(__file__).resolve().parents[1]/'src'),
               str(Path(__file__).resolve().parents[1]/'tools')]
import numpy as np
from mwad.scene import unpack_geometry
from prepare_scenery import model_geometry
import nif_common

RAW = b'NetImmerse File Format, Version 4.0.0.2\n'
# pyffi row-vector layout of a 90-degree yaw, as stored on Velothi kit roots.
YAW90 = [[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]]


def matrix(rotation=None, translation=(0, 0, 0), scale=1.0):
    m = np.eye(4)
    if rotation is not None:
        m[:3, :3] = np.array(rotation) * scale
    else:
        m[:3, :3] *= scale
    m[3, :3] = translation
    return m


def fixture(root_matrix, child_matrix=None, shape_root=False, root_name=b'node', blocks_first_root=True):
    """A one-triangle model. Default: a root NiNode holding the shape (or a child node holding it);
    shape_root: the NiTriShape itself is the root (as contain_crate_01)."""
    class AVObject:
        def __init__(self, transform, children=()):
            self.children = children; self.flags = 0; self.name = b'node'; self.properties = []
            self.transform = transform
        def get_transform(self):
            return NS(as_list=lambda: self.transform.tolist())
    class Node(AVObject): pass
    class Shape(AVObject):
        def __init__(self, transform=None):
            super().__init__(np.eye(4) if transform is None else transform); self.skin_instance = None
            self.data = NS(num_vertices=3, num_triangles=1, num_uv_sets=0, uv_sets=[],
                           has_vertex_colors=False,
                           vertices=[NS(x=10, y=0, z=0), NS(x=20, y=0, z=0), NS(x=10, y=5, z=0)],
                           get_triangles=lambda: [(0, 1, 2)])
    class Collision(Node): pass
    class Stencil: pass
    class Material: pass
    class Texture: pass
    if shape_root:
        root = Shape(root_matrix)
    else:
        shape = Shape()
        inner = Node(child_matrix, [shape]) if child_matrix is not None else shape
        root = Node(root_matrix, [inner])
    root.name = root_name
    other = Node(np.eye(4))

    class Data:
        roots = [root]
        blocks = [root] if blocks_first_root else [other, root]
        def read(self, stream): pass
    return NS(Data=Data, NiAVObject=AVObject, NiNode=Node, RootCollisionNode=Collision,
              NiTriShape=Shape, NiStencilProperty=Stencil, NiMaterialProperty=Material,
              NiTexturingProperty=Texture)


def points(N, **options):
    return np.asarray(unpack_geometry(model_geometry(RAW, N, **options)[0])[0])[:, :3]


PLAIN = [[10, 0, 0], [20, 0, 0], [10, 5, 0]]


class RootTransformTests(unittest.TestCase):
    def test_root_rotation_is_ignored(self):
        plain = points(fixture(matrix()))
        rotated = points(fixture(matrix(YAW90)))
        np.testing.assert_allclose(rotated, plain, atol=1e-6)
        np.testing.assert_allclose(plain[0], [10, 0, 0], atol=1e-6)

    def test_root_node_translation_is_dropped(self):
        # MESH-EBONHEART-DRAGON-PEDESTAL-42: ex_imp_dragonstatue's root NiNode carries z 327.1; kept, it lifted the
        # statue and its pedestal 327 units above the plaza.
        moved = points(fixture(matrix(None, translation=(0, 0, 327.1))))
        np.testing.assert_allclose(moved, PLAIN, atol=1e-6)

    def test_root_node_scale_is_dropped(self):
        scaled = points(fixture(matrix(YAW90, scale=2.0)))
        np.testing.assert_allclose(scaled, PLAIN, atol=1e-6)

    def test_shape_root_keeps_its_whole_transform(self):
        # contain_crate_01: the root is the NiTriShape itself, offset z -32: the crate rests on the floor.
        moved = points(fixture(matrix(None, translation=(0, 0, -32)), shape_root=True))
        np.testing.assert_allclose(moved[:, 2], [-32, -32, -32], atol=1e-6)
        np.testing.assert_allclose(moved[:, :2], [[10, 0], [20, 0], [10, 5]], atol=1e-6)

    def test_bip01_and_later_record_roots_keep_their_transform(self):
        for N in (fixture(matrix(None, translation=(0, 0, 5)), root_name=b'Bip01'),
                  fixture(matrix(None, translation=(0, 0, 5)), blocks_first_root=False)):
            np.testing.assert_allclose(points(N)[:, 2], [5, 5, 5], atol=1e-6)

    def test_previous_rules_stay_selectable(self):
        N = fixture(matrix(YAW90, translation=(0, 0, 327.1)))
        before = points(N, root_rule='morrowind')
        np.testing.assert_allclose(before[:, 2], [327.1] * 3, atol=1e-4)
        np.testing.assert_allclose(before[:, :2], [[10, 0], [20, 0], [10, 5]], atol=1e-6)
        legacy = points(N, root_rule='legacy')
        np.testing.assert_allclose(legacy[0], [0, -10, 327.1], atol=1e-4)
        with self.assertRaises(ValueError):
            points(N, root_rule='bogus')
        self.assertEqual(nif_common.DEFAULT_SCENERY_ROOT_RULE, 'node')

    def test_child_rotation_is_unchanged(self):
        # Only the root is special; child node transforms keep the release math.
        child = points(fixture(matrix(), child_matrix=matrix(YAW90)))
        expected = np.array([[10, 0, 0, 1], [20, 0, 0, 1], [10, 5, 0, 1]]) @ matrix(YAW90)
        np.testing.assert_allclose(child, expected[:, :3], atol=1e-6)

    def test_audit_lists_the_models_the_repair_moves(self):
        from nif_root_audit import root_change
        statue = root_change(RAW, fixture(matrix(None, translation=(0, 0, 327.1))))
        self.assertEqual(statue['shift'], [0.0, 0.0, 327.1])
        self.assertEqual(statue['type'], 'Node')
        self.assertIsNone(root_change(RAW, fixture(matrix(None, translation=(0, 0, -32)), shape_root=True)))  # crate
        self.assertIsNone(root_change(RAW, fixture(matrix(YAW90))))   # rotation only: dropped by both rules

    def test_chim_units_are_keyed_on_the_root_rule(self):
        # The CHIM model units read geometry through prepare_scenery and nif_common: both are in their keys.
        import chim.units as units
        for kind in ('variant', 'tiles', 'cut'):
            self.assertIn('tools/nif_common.py', units.TOOLS[kind])
            self.assertIn('tools/prepare_scenery.py', units.TOOLS[kind])


if __name__ == '__main__':
    unittest.main()
