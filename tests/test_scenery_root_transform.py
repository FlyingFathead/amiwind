# SPDX-License-Identifier: GPL-3.0-only
"""Fictional meshes only: Morrowind ignores the NIF root node's authored
rotation but keeps its translation and scale (BALMORA-TEMPLE-GEOMETRY-29)."""
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest

sys.path[:0] = [str(Path(__file__).resolve().parents[1]/'src'),
               str(Path(__file__).resolve().parents[1]/'tools')]
import numpy as np
from mwad.scene import unpack_geometry
from prepare_scenery import model_geometry

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


def fixture(root_matrix, child_matrix=None):
    class Node:
        def __init__(self, transform, children=()):
            self.children = children; self.flags = 0; self.name = b'node'; self.properties = []
            self.transform = transform
        def get_transform(self):
            return NS(as_list=lambda: self.transform.tolist())
    class Shape(Node):
        def __init__(self):
            super().__init__(np.eye(4)); self.skin_instance = None
            self.data = NS(num_vertices=3, num_triangles=1, num_uv_sets=0, uv_sets=[],
                           has_vertex_colors=False,
                           vertices=[NS(x=10, y=0, z=0), NS(x=20, y=0, z=0), NS(x=10, y=5, z=0)],
                           get_triangles=lambda: [(0, 1, 2)])
    class Collision(Node): pass
    class Stencil: pass
    class Material: pass
    class Texture: pass
    shape = Shape()
    inner = Node(child_matrix, [shape]) if child_matrix is not None else shape
    root = Node(root_matrix, [inner])
    class Data:
        roots = [root]
        def read(self, stream): pass
    return NS(Data=Data, NiAVObject=Node, NiNode=Node, RootCollisionNode=Collision,
              NiTriShape=Shape, NiStencilProperty=Stencil, NiMaterialProperty=Material,
              NiTexturingProperty=Texture)


def points(N):
    return np.asarray(unpack_geometry(model_geometry(RAW, N)[0])[0])[:, :3]


class RootTransformTests(unittest.TestCase):
    def test_root_rotation_is_ignored(self):
        plain = points(fixture(matrix()))
        rotated = points(fixture(matrix(YAW90)))
        np.testing.assert_allclose(rotated, plain, atol=1e-6)
        np.testing.assert_allclose(plain[0], [10, 0, 0], atol=1e-6)

    def test_root_translation_is_kept(self):
        # A crate root offset of -32 must still put the mesh 32 units lower.
        moved = points(fixture(matrix(YAW90, translation=(0, 0, -32))))
        np.testing.assert_allclose(moved[:, 2], [-32, -32, -32], atol=1e-6)
        np.testing.assert_allclose(moved[:, :2], [[10, 0], [20, 0], [10, 5]], atol=1e-6)

    def test_root_scale_is_kept(self):
        scaled = points(fixture(matrix(YAW90, scale=2.0)))
        np.testing.assert_allclose(scaled[1], [40, 0, 0], atol=1e-6)

    def test_child_rotation_is_unchanged(self):
        # Only the root is special; child node transforms keep the release math.
        child = points(fixture(matrix(), child_matrix=matrix(YAW90)))
        expected = np.array([[10, 0, 0, 1], [20, 0, 0, 1], [10, 5, 0, 1]]) @ matrix(YAW90)
        np.testing.assert_allclose(child, expected[:, :3], atol=1e-6)


if __name__ == '__main__':
    unittest.main()
