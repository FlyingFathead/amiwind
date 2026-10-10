# SPDX-License-Identifier: GPL-3.0-only
"""Fictional meshes only: the NIF root-node rule for NPC parts (selectable) and its
agreement with the scenery walkers (tools/nif_common.py)."""
from collections import OrderedDict
from pathlib import Path
import os
import sys
from types import SimpleNamespace as NS
import unittest

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1]/'src'),
               str(Path(__file__).resolve().parents[1]/'tools')]
import numpy as np
from mwad.scene import unpack_geometry
import nif_common
import npc_geometry
from prepare_scenery import model_geometry
from test_scenery_root_transform import fixture as scenery_fixture, matrix, YAW90, RAW


def npc_fixture(root_matrix):
    class Node:
        def __init__(self, transform, children=()):
            self.children = children; self.flags = 0; self.name = b'node'; self.properties = []
            self.transform = transform
        def get_transform(self):
            return NS(as_list=lambda: self.transform.tolist())
    class Shape(Node):
        def __init__(self):
            super().__init__(np.eye(4)); self.skin_instance = None; self.name = b'Tri Part'
            self.data = NS(num_vertices=3, num_triangles=1, num_uv_sets=0, uv_sets=[],
                           has_vertex_colors=False,
                           vertices=[NS(as_list=lambda v=v: list(v)) for v in ((10, 0, 0), (20, 0, 0), (10, 5, 0))],
                           get_triangles=lambda: [(0, 1, 2)])
    class Material: pass
    class Texture: pass
    root = Node(root_matrix, [Shape()])
    class Data:
        roots = [root]
        def read(self, stream): pass
    return NS(Data=Data, NiAVObject=Node, NiNode=Node, NiTriShape=Shape,
              NiMaterialProperty=Material, NiTexturingProperty=Texture)


def assemble_points(root_matrix, rule):
    N = npc_fixture(root_matrix)
    assets = NS(models=OrderedDict(), read=lambda name: RAW, texture=lambda n: None)
    skeleton = NS(N=N, pose=lambda t: (lambda name: np.eye(4)))
    part = {'mesh': 'fixture.nif', 'slot': 5, 'attach': 'Chest', 'filter': ''}
    appearance = {'parts': [part], 'weight': 4., 'height': 4., 'root_rule': rule}
    shapes, _, _ = npc_geometry.assemble(assets, appearance, skeleton, [0.])
    return shapes[0]['positions'][0] / 1.0  # weight*height*.25 == 4 for 4,4,4


class NifCommon(unittest.TestCase):
    def test_rules(self):
        m = matrix(YAW90, (1, 2, 3), 2.0)
        mw = nif_common.root_local(m, 'morrowind')
        self.assertTrue(np.allclose(mw[:3, :3], np.eye(3) * 2.0))
        self.assertTrue(np.allclose(mw[3, :3], (1, 2, 3)))
        self.assertTrue(np.allclose(nif_common.root_local(m, 'legacy'), m))
        with self.assertRaises(ValueError): nif_common.root_local(m, 'bogus')

    def test_rotation_detector(self):
        self.assertTrue(nif_common.has_root_rotation(matrix(YAW90)))
        self.assertFalse(nif_common.has_root_rotation(matrix(None, (5, 0, 0), 3.0)))


class NpcRule(unittest.TestCase):
    def test_default_is_the_measured_legacy_rule(self):
        self.assertEqual(npc_geometry.NPC_DEFAULT_ROOT_RULE, 'legacy')

    def test_yaw_root_dropped_by_morrowind_kept_by_legacy(self):
        root = matrix(YAW90)
        legacy = assemble_points(root, 'legacy')
        morrowind = assemble_points(root, 'morrowind')
        plain = assemble_points(matrix(None), 'legacy')
        self.assertTrue(np.allclose(morrowind, plain))
        self.assertFalse(np.allclose(legacy, plain))

    def test_no_root_rotation_is_identical_under_both_rules(self):
        root = matrix(None, (0, 0, -3), 1.0)
        self.assertTrue(np.array_equal(assemble_points(root, 'legacy'), assemble_points(root, 'morrowind')))

    def test_scenery_and_npc_paths_agree_for_morrowind(self):
        root = matrix(YAW90, (0, 0, -3))
        scenery = np.asarray(unpack_geometry(model_geometry(RAW, scenery_fixture(root))[0])[0])[:, :3]
        npc = assemble_points(root, 'morrowind')
        # the dropped rotation: x spread and y spread stay those of the unrotated triangle in both paths
        self.assertAlmostEqual(float(np.ptp(npc[:, 0])), 10.0, places=3)
        self.assertAlmostEqual(float(np.ptp(scenery[:, 0])), 10.0, places=3)

    def test_rule_is_in_the_cache_key_environment(self):
        self.assertIn('AMIWIND_NPC_ROOT_RULE', Path(npc_geometry.__file__).read_text())

    def test_set_rule_exports_for_workers(self):
        old = npc_geometry.get_root_rule()
        had = npc_geometry.ROOT_RULE_ENV in os.environ
        saved = os.environ.get(npc_geometry.ROOT_RULE_ENV)
        try:
            npc_geometry.set_root_rule('morrowind')
            self.assertEqual(os.environ[npc_geometry.ROOT_RULE_ENV], 'morrowind')
        finally:
            npc_geometry.set_root_rule(old)
            if had:
                os.environ[npc_geometry.ROOT_RULE_ENV] = saved
            else:
                os.environ.pop(npc_geometry.ROOT_RULE_ENV, None)


if __name__ == '__main__':
    unittest.main()
