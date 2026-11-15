# SPDX-License-Identifier: GPL-3.0-only
"""Small closed parts of a room map's props drawn as boxes (tools/room_map_parts.py, PRISON-SHIP-POLY-COLLISION-65),
and the shell bevels of a classic room map (tools/room_map_collision.py)."""
import os
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import room_map_collision as C  # noqa: E402
import room_map_parts as P  # noqa: E402


def sphere_part(centre, radius, rings=4, segments=6):
    """A closed part of many faces (a faceted sphere), as converter polygons with outward normals and CCW corners."""
    out = []
    c = np.asarray(centre, float)
    for i in range(rings):
        t0, t1 = np.pi * i / rings, np.pi * (i + 1) / rings
        for j in range(segments):
            p0, p1 = 2 * np.pi * j / segments, 2 * np.pi * (j + 1) / segments

            def at(t, p):
                return c + radius * np.array([np.sin(t) * np.cos(p), np.sin(t) * np.sin(p), np.cos(t)])
            quad = [at(t0, p0), at(t1, p0), at(t1, p1), at(t0, p1)]
            pts = [q for k, q in enumerate(quad) if k == 0 or np.linalg.norm(q - quad[k - 1]) > 1e-9]
            if len(pts) > 1 and np.linalg.norm(pts[-1] - pts[0]) < 1e-9:
                pts = pts[:-1]
            pts = np.array(pts)
            n = np.cross(pts[1] - pts[0], pts[2] - pts[0])
            n /= np.linalg.norm(n)
            if n @ (pts.mean(0) - c) < 0:
                pts = pts[::-1].copy()
                n = -n
            out.append((pts, 1, np.array([[.05, 0], [0, .05], [0, 0]]), np.zeros(2), n))
    return out


class SmallParts(unittest.TestCase):
    def setUp(self):
        self.small = sphere_part((0, 0, 0), 2.0)          # 8 converter units across = 2 Quake units at 0.25
        self.large = sphere_part((40, 0, 0), 20.0)        # 40 units across = 10 Quake units
        self.record = (None, None, self.small + self.large, [], {})

    def test_small_part_becomes_its_box(self):
        (_, _, polys, _, lod), receipt = P.box_small_parts(self.record, 2.5, 0.25)
        self.assertEqual(receipt['parts_boxed'], 1)
        self.assertEqual(receipt['faces_after'], len(self.large) + 6)
        self.assertEqual(lod['small_parts'], receipt)
        boxes = polys[len(self.large):]
        pts = np.concatenate([b[0] for b in boxes])
        src = np.concatenate([p[0] for p in self.small])
        np.testing.assert_allclose(pts.min(0), src.min(0))     # the box spans the part exactly
        np.testing.assert_allclose(pts.max(0), src.max(0))
        for quad, material, ax, off, n in boxes:
            self.assertEqual(material, 1)
            self.assertGreater(float(n @ (quad.mean(0) - src.mean(0))), 0)   # outward
            area = sum(np.cross(quad[i], quad[(i + 1) % 4]) for i in range(4))
            self.assertGreater(float(area @ n), 0)                          # the source's winding
        # closed: every edge of the six faces is used twice, once each way
        edges = {}
        for quad, *_ in boxes:
            for i in range(4):
                a, b = tuple(np.round(quad[i], 6)), tuple(np.round(quad[(i + 1) % 4], 6))
                edges[(a, b)] = edges.get((a, b), 0) + 1
        self.assertTrue(all(edges.get((b, a)) == 1 for (a, b) in edges))

    def test_large_and_tiny_parts_stay(self):
        (_, _, polys, _, _), receipt = P.box_small_parts(self.record, 0.9, 0.25)     # the small part is 1.0 across
        self.assertEqual(receipt['parts_boxed'], 0)
        self.assertEqual(len(polys), len(self.small) + len(self.large))
        few = sphere_part((0, 0, 0), 2.0, rings=2, segments=3)     # 6 faces: stays
        (_, _, polys, _, _), receipt = P.box_small_parts((None, None, few, [], {}), 2.5, 0.25)
        self.assertEqual(receipt['parts_boxed'], 0)

    def test_switch(self):
        old = os.environ.pop(P.ROOM_SMALL_PARTS_VARIABLE, None)
        try:
            self.assertEqual(P.room_small_parts(), 'box')
            self.assertEqual(P.export_room_small_parts('off'), 'off')
            self.assertEqual(P.apply_room_small_parts({0: self.record}, {'models': [{'source': 'meshes/f/active_de_bed_30.nif'}]}), {})
            self.assertEqual(P.export_room_small_parts(None), 'box')
            with self.assertRaises(ValueError):
                P.export_room_small_parts('fast')
        finally:
            os.environ.pop(P.ROOM_SMALL_PARTS_VARIABLE, None)
            if old is not None:
                os.environ[P.ROOM_SMALL_PARTS_VARIABLE] = old


class ShellBevels(unittest.TestCase):
    @staticmethod
    def plate(z, tilt=False):
        p = np.array([[0, 0, z], [10, 0, z], [10, 10, z + (10 if tilt else 0)], [0, 10, z + (10 if tilt else 0)]], float)
        return (p, None, [0], 0.)

    def test_walkable_plates_exact(self):
        floor, wall = self.plate(0), (np.array([[0, 0, 0], [10, 0, 0], [10, 0, 10], [0, 0, 10]], float), None, [1], 0.)
        record = (None, None, [], [floor, wall], {'collision_bevels': 'exact standing-box convex sum'})
        receipt = C.set_shell_bevels(record, 1)
        self.assertEqual((receipt['exact_before'], receipt['exact_after']), ('all', 1))
        self.assertEqual(record[4]['collision_bevels_pieces'], [0])
        self.assertNotIn('collision_bevels', record[4])
        record = (None, None, [], [floor, wall], {'collision_bevels': 'exact standing-box convex sum'})
        C.set_shell_bevels(record, 2)
        self.assertNotIn('collision_bevels', record[4])
        self.assertNotIn('collision_bevels_pieces', record[4])
        record = (None, None, [], [floor, wall], {'collision_bevels': 'x'})
        C.set_shell_bevels(record, 0)
        self.assertEqual(record[4], {'collision_bevels': 'x'})

    def test_option(self):
        old = os.environ.pop(C.HOLLOW_BEVELS_VARIABLE, None)
        try:
            self.assertEqual(C.room_map_hollow_bevels(1), 1)
            os.environ[C.HOLLOW_BEVELS_VARIABLE] = '0'
            self.assertEqual(C.room_map_hollow_bevels(1), 0)
            os.environ[C.HOLLOW_BEVELS_VARIABLE] = '7'
            with self.assertRaises(ValueError):
                C.room_map_hollow_bevels(1)
        finally:
            os.environ.pop(C.HOLLOW_BEVELS_VARIABLE, None)
            if old is not None:
                os.environ[C.HOLLOW_BEVELS_VARIABLE] = old


class ChimDrawTiles(unittest.TestCase):
    """--chim-draw-tiles (chim.build.draw_tile_grain, DRAW_TILES_ON): named models only, off when empty."""

    def test_named_models_only(self):
        from chim.build import DRAW_TILES_ON, draw_tile_grain
        self.assertEqual(draw_tile_grain({'name': 'x/ex_de_ship@s1#2'}, DRAW_TILES_ON), 128.0)
        self.assertEqual(draw_tile_grain({'name': 'r/siltstrider@s0.89'}, DRAW_TILES_ON), 128.0)
        for other in ('x/ex_de_ship_door@s1.08', 'x/ex_de_shipwreck@s1', 'x/ex_common_house_addon@s1'):
            self.assertIsNone(draw_tile_grain({'name': other}, DRAW_TILES_ON))
        self.assertIsNone(draw_tile_grain({'name': 'x/ex_de_ship@s1#2', 'over_budget': 'x'}, DRAW_TILES_ON))

    def test_off_by_default(self):
        from chim.build import draw_tile_grain
        self.assertIsNone(draw_tile_grain({'name': 'x/ex_de_ship@s1#2'}, {}))
        self.assertIsNone(draw_tile_grain({'name': 'x/ex_de_ship@s1#2'}, None))


if __name__ == '__main__':
    unittest.main()
