# SPDX-License-Identifier: GPL-3.0-only
"""Coverage survives exact duplicate corners introduced by float32 placement."""
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from chim.validate import inside_convex_xy  # noqa: E402


def placed(points, offset):
    return [struct.unpack('<2f', struct.pack('<2f', x + offset[0], y + offset[1]))
            for x, y in points]


class PolygonCoverageTests(unittest.TestCase):
    def test_float32_translation_collapses_an_edge_without_losing_the_face(self):
        poly = placed([(224.00005, 223.99995), (224.00005, 224),
                       (256, 224), (256, 192)], (-128, 1408))
        self.assertEqual(poly[0], poly[1])
        for points in (poly, poly[::-1]):
            self.assertTrue(inside_convex_xy(points, 116.48, 1620.297))
            self.assertFalse(inside_convex_xy(points, 90, 1620.297))
            self.assertIsNone(inside_convex_xy(points, 128, 1620))

    def test_repeated_closing_vertex_does_not_create_a_boundary(self):
        triangle = [(0, 0), (32, 0), (0, 32)]
        self.assertTrue(inside_convex_xy(triangle + [triangle[0]], 7, 11))
        self.assertIsNone(inside_convex_xy(triangle + [triangle[0]], 7, 25))
        self.assertFalse(inside_convex_xy(triangle + [triangle[0]], 30, 30))

    def test_degenerate_polygons_never_cover_a_sample(self):
        for poly in ([], [(1, 1)], [(1, 1)] * 4, [(0, 0), (8, 8), (16, 16)]):
            self.assertFalse(inside_convex_xy(poly, 3, 5), poly)


if __name__ == '__main__':
    unittest.main()
