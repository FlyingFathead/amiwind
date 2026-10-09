# SPDX-License-Identifier: GPL-3.0-only
"""Occluders from closed building meshes for the CHIM visibility rows (synthetic meshes only)."""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim.occluders import enclosed_grid, erode, place_columns, solid_columns, unpack  # noqa: E402


def box_faces(lo, hi, skip=()):
    """Quads of an axis-aligned box; skip names faces to leave out ('bottom', 'top', '-x', '+x', '-y', '+y')."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    faces = {'bottom': [(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)],
             'top': [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
             '-x': [(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)],
             '+x': [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
             '-y': [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
             '+y': [(x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0)]}
    return [np.array(q, float) for k, q in faces.items() if k not in skip]


class EnclosureTests(unittest.TestCase):
    def test_closed_and_open_bottomed_houses_enclose_their_rooms(self):
        for skip in ((), ('bottom',)):
            with self.subTest(skip=skip):
                origin, v, grid = enclosed_grid(box_faces((-100, -60, 0), (100, 60, 120), skip))
                self.assertTrue(grid.all())          # every voxel centre inside the box is enclosed

    def test_awning_and_courtyard_enclose_nothing(self):
        awning = [np.array([(-50, -50, 80), (50, -50, 80), (50, 50, 80), (-50, 50, 80)], float)]
        self.assertFalse(enclosed_grid(awning + box_faces((-50, -50, 0), (50, 50, 1)))[2].any())
        courtyard = box_faces((-100, -100, 0), (100, 100, 100), skip=('top',))
        self.assertFalse(enclosed_grid(courtyard)[2].any())

    def test_a_passage_through_the_house_stays_open(self):
        # a house with a 40-unit wide passage along x through its middle (walls of the passage
        # and the house's outer box; the passage's ends are open)
        faces = box_faces((-100, -100, 0), (100, 100, 120), skip=('-x', '+x'))
        faces += [np.array(q, float) for q in (
            [(-100, -100, 0), (-100, -100, 120), (-100, -20, 120), (-100, -20, 0)],
            [(-100, 20, 0), (-100, 20, 120), (-100, 100, 120), (-100, 100, 0)],
            [(100, -100, 0), (100, -20, 0), (100, -20, 120), (100, -100, 120)],
            [(100, 20, 0), (100, 100, 0), (100, 100, 120), (100, 20, 120)],
            [(-100, -20, 0), (100, -20, 0), (100, -20, 120), (-100, -20, 120)],
            [(-100, 20, 0), (-100, 20, 120), (100, 20, 120), (100, 20, 0)])]
        origin, v, grid = enclosed_grid(faces)
        ys = origin[1] + np.arange(grid.shape[1]) * v
        passage = np.abs(ys) < 20
        self.assertFalse(grid[:, passage, :].any())
        self.assertTrue(grid[:, ys < -30, :].any() and grid[:, ys > 30, :].any())

    def test_erosion_keeps_only_the_core(self):
        g = np.ones((10, 10, 6), bool)
        e = erode(g, 3, 1)
        self.assertEqual(e.sum(), 4 * 4 * 4)
        self.assertFalse(erode(np.ones((6, 6, 6), bool), 3, 1).any())


class PlacementTests(unittest.TestCase):
    def test_columns_follow_origin_and_yaw(self):
        occ = solid_columns(box_faces((-120, -40, 0), (120, 40, 100)))
        self.assertIsNotNone(occ)
        grid = unpack(occ)
        self.assertTrue(grid.any())
        for yaw, long_axis in ((0.0, 0), (90.0, 1)):
            cells = list(place_columns(occ, (512.0, 512.0, 10.0), yaw, 16.0, (0.0, 0.0), 64, 64))
            self.assertTrue(cells)
            xs = [i for i, _, _, _ in cells]
            ys = [j for _, j, _, _ in cells]
            spans = (max(xs) - min(xs), max(ys) - min(ys))
            self.assertGreater(spans[long_axis], spans[1 - long_axis])
            for i, j, z0, z1 in cells:
                cx, cy = (i + 0.5) * 16 - 512, (j + 0.5) * 16 - 512
                if yaw:
                    cx, cy = cy, -cx
                # every cell lies wholly inside the box (16-unit cell around its centre)
                self.assertTrue(abs(cx) + 8 <= 120 and abs(cy) + 8 <= 40, (i, j, cx, cy))
                self.assertTrue(10 < z0 < z1 < 110)

    def test_closed_house_blocks_sight_where_its_hollow_shell_does_not(self):
        from chim.visibility import Ground, Occluders, cluster_pvs
        offsets = [(dx, 0) for dx in range(-6, 7)]
        flat = Ground([[0.0] * 13, [0.0] * 13], 128, (0, 0))
        tops = {(i, 0): 8.0 for i in range(6)}
        occ = Occluders((0, 0), (1536, 256))
        house = solid_columns(box_faces((-60, -200, -20), (60, 200, 400)))
        for i, j, z0, z1 in place_columns(house, (768.0, 128.0, 0.0), 0.0, 16.0, (0.0, 0.0), occ.nx, occ.ny):
            occ.add_interval(i, j, z0, z1)
        self.assertGreater(occ.cells(), 0)
        seen, stats = cluster_pvs(6, 1, 256, (0, 0), flat, occ, tops, offsets)
        self.assertNotIn((5, 0), seen[(0, 0)])
        seen, _ = cluster_pvs(6, 1, 256, (0, 0), flat, Occluders((0, 0), (1536, 256)), tops, offsets)
        self.assertIn((5, 0), seen[(0, 0)])


if __name__ == '__main__':
    unittest.main()
