# SPDX-License-Identifier: GPL-3.0-only
"""Plants that grow on trees (FLORA-FLOATING-DEV1-66): the seat table, the mesh hosts and the audit's geometry."""
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]

import numpy as np                                   # noqa: E402

import flora_support                                 # noqa: E402
from chim import flora_support_audit as audit        # noqa: E402


class FloraSupportTable(unittest.TestCase):
    def test_shipped_table_loads(self):
        data = json.loads(flora_support.CONFIG.read_text(encoding='utf-8'))
        self.assertEqual(data['format'], 'AmiWind flora support 1')
        seats = flora_support.seats()
        self.assertEqual(len(seats), len(data['seats']))
        for shift in seats.values():
            self.assertEqual(len(shift), 3)
            self.assertLess(max(abs(v) for v in shift), 256)
        for number, reason in flora_support.known_floating().items():
            self.assertTrue(reason.strip(), number)

    def test_mesh_host_is_drawn_as_mesh(self):
        from prepare_world_flora import effective_representation
        host = next(iter(flora_support.mesh_hosts()))
        self.assertEqual(effective_representation({'number': host, 'renderer_policy': 'sprite'}), 'mesh')
        self.assertEqual(effective_representation({'number': 1, 'renderer_policy': 'sprite'}), 'sprite')
        self.assertEqual(effective_representation({'renderer_policy': 'sprite'}), 'sprite')

    def test_supported_plants(self):
        self.assertTrue(audit.is_supported_plant('f\\Flora_BC_Shelffungus_03.NIF'))
        self.assertTrue(audit.is_supported_plant('f/flora_t_shelffungus_01.nif'))
        self.assertFalse(audit.is_supported_plant('f/flora_bc_mushroom_01.nif'))


class Geometry(unittest.TestCase):
    def test_point_triangle_distance(self):
        tri = np.array([[[0, 0, 0], [10, 0, 0], [0, 10, 0]]], float)
        d, p, q = audit.point_triangle_closest(np.array([[1, 1, 3.0]]), tri)
        self.assertAlmostEqual(d, 3.0)
        self.assertTrue(np.allclose(q, [1, 1, 0]))
        d, _, q = audit.point_triangle_closest(np.array([[-2, 0, 0.0]]), tri)        # beyond a corner
        self.assertAlmostEqual(d, 2.0)
        self.assertEqual(audit.point_triangle_closest(np.zeros((1, 3)), np.zeros((0, 3, 3)))[0], math.inf)

    def test_placed_triangles_yaw(self):
        tri = np.array([[[1, 0, 0], [0, 0, 0], [0, 0, 1]]], float)
        out = audit.placed_triangles(tri, (10, 0, 0), 90)
        self.assertTrue(np.allclose(out[0, 0], [10, 1, 0]))

    def test_classify(self):
        base = dict(original_gap=0.2, built_gap=8.0, support_gap=8.0, support_moved=0.0, support_built='f/t@s2')
        self.assertEqual(audit.classify(base, 2.0), 'floating: support reduced away')
        self.assertEqual(audit.classify(dict(base, built_gap=1.0), 2.0), 'seated')
        self.assertEqual(audit.classify(dict(base, support_built='f/t.nif#collision_only@s2'), 2.0),
                         'floating: support drawn as a sprite')
        self.assertEqual(audit.classify(dict(base, original_gap=9.0), 2.0), 'unsupported-in-original')


if __name__ == '__main__':
    unittest.main()
