# SPDX-License-Identifier: GPL-3.0-only
"""The compiled terrain standing hull is checked against the exact union of its pieces and falls back to the routed
hull when it is short (CHIM-COMPILED-HULL-SHORT-36); a frame's terrain is checked as soon as it is built, and
failures name the frame (BUILD-CHIM-VALIDATE-LATE-36)."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src'), str(ROOT / 'tests')]

from chim.terrain import terrain_unit  # noqa: E402
from collision_bsp import StandingHullInexact, check_samples, patch_holes, standing_check  # noqa: E402
from chim.validate import early_frame_failures  # noqa: E402
from player_hull import MINS  # noqa: E402


def prism(x0, y0, x1, y1, top, floor=-1024.0):
    from scipy.spatial import ConvexHull
    pts = np.array([(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (floor, top)], dtype=float)
    return (pts, SimpleNamespace(equations=ConvexHull(pts).equations), [], 0.)


def flat_hull(stand):
    """A compiled-hull form (collision_bsp.compile_standing): solid below z = stand."""
    return [((0.0, 0.0, 1.0, stand), -1, -2)], 0


def flat_task(x0, y0, z, grain=256, step=128):
    n = grain // step + 2
    return {'box': (x0, y0, x0 + grain, y0 + grain), 'step': step,
            'heights': [[z] * (n + 1) for _ in range(n + 1)], 'materials': [[1, 1], [1, 1]], 'floor': -1024,
            'ceiling': 2048, 'water': 0.0, 'light': 12,
            'collision_box': (x0 - step, y0 - step, x0 + grain + step, y0 + grain + step)}


class CompiledHullCheckTests(unittest.TestCase):
    def test_an_exact_hull_passes_and_a_sunken_or_floating_one_is_measured(self):
        pieces = [prism(-128, -128, 384, 384, 20.0)]
        stand = 20.0 - MINS[2]
        check = standing_check(flat_hull(stand), pieces, (0, 0, 256, 256))
        self.assertEqual((check['short'], check['over']), (0.0, 0.0))
        self.assertGreater(check['columns'], 1000)
        check = standing_check(flat_hull(stand - 3.0), pieces, (0, 0, 256, 256))
        self.assertAlmostEqual(check['short'], 3.0, delta=0.1)     # the judged top lies CHECK_SIDE inside
        self.assertEqual(len(check['worst_at']), 3)
        self.assertGreater(standing_check(flat_hull(stand + 2.0), pieces, (0, 0, 256, 256))['over'], 0)

    def test_a_lost_piece_is_found_and_patched_with_the_piece_itself(self):
        # the compiled hull holds piece A only (as qbsp sometimes drops a thin piece): the check names B, and the
        # patched hull (B's exact chain behind every empty leaf) passes without growing past the pieces
        a, b = prism(-128, -128, 384, 128, 20.0), prism(-128, 128, 384, 384, 60.0)
        holds_a = [((0.0, 1.0, 0.0, 128.0 - MINS[1]), -1, 1), ((0.0, 0.0, 1.0, 20.0 - MINS[2]), -1, -2)], 0
        found = set()
        check = standing_check(holds_a, [a, b], (0, 0, 256, 256), implicated=found)
        self.assertGreater(check['short'], 30)
        self.assertEqual(found, {1})
        patched = patch_holes(holds_a, [a, b], found)
        self.assertGreater(len(patched[0]), len(holds_a[0]))
        check = standing_check(patched, [a, b], (0, 0, 256, 256))
        self.assertEqual((check['short'], check['over']), (0.0, 0.0))

    def test_a_steep_face_is_not_judged(self):
        # a 60-degree ramp: its top is not walkable, so a hull a few units off it vertically is not "short"
        from scipy.spatial import ConvexHull
        pts = np.array([(0, 0, 0), (100, 0, 0), (0, 100, 0), (100, 100, 0),
                        (0, 0, -1024), (100, 0, -1024), (0, 100, -1024), (100, 100, -1024),
                        (100, 0, 173.2), (100, 100, 173.2)], dtype=float)
        ramp = [(pts, SimpleNamespace(equations=ConvexHull(pts).equations), [], 0.)]
        check = standing_check(flat_hull(-2000.0), ramp, (10, 10, 90, 90))
        self.assertEqual(check['short'], 0.0)

    def test_a_short_compiled_hull_falls_back_to_the_routed_hull(self):
        def short(pieces, qbsp, cache, grid=64, check_box=None, patch=True):
            return flat_hull(0.0), {'short': 3.0, 'over': 0.0, 'columns': 1}
        task = dict(flat_task(0, 0, 30.0), hull='compiled', qbsp='qbsp', collision_cache='cache')
        with mock.patch('collision_bsp.compile_standing_checked', short):
            info = terrain_unit(task)['info']
            lumps = terrain_unit(task)['lumps']
        self.assertEqual(info['hull'], 'routed')
        self.assertEqual(info['hull_check']['fallback'], 'routed')
        self.assertEqual(info['hull_check']['short'], 3.0)
        self.assertEqual(lumps, terrain_unit(dict(flat_task(0, 0, 30.0), hull='routed'))['lumps'])

    def test_an_inexact_hull_is_a_value_error_for_every_caller(self):
        # models (chim.models.variant_unit) and legacy maps (prepare_mesh_bsp collider) fall back on ValueError
        error = StandingHullInexact({'short': 1.5, 'over': 0.0, 'columns': 9})
        self.assertIsInstance(error, ValueError)
        self.assertIn('short 1.5', str(error))

    def test_the_lattice_covers_the_box_and_its_seams(self):
        pieces = [prism(-128, -128, 384, 384, 20.0)]
        xy = check_samples(pieces, (0, 0, 256, 256))
        self.assertTrue(((xy[:, 0] > 0) & (xy[:, 0] < 256) & (xy[:, 1] > 0) & (xy[:, 1] < 256)).all())
        self.assertIn(0.25, set(np.round(xy[:, 0], 2)))
        self.assertIn(255.75, set(np.round(xy[:, 1], 2)))
        self.assertLessEqual(len(check_samples(pieces, (0, 0, 4096, 4096))), 4096 + 2000)


class EarlyFrameCheckTests(unittest.TestCase):
    def frame(self, bad=False):
        z = 30.0
        heights = [[z] * 5 for _ in range(5)]          # a 2 x 2 chunk frame, tiles of 128, corner grid
        section = {'terrain_step': 128, 'terrain_low': [0, 0], 'terrain_heights': heights, 'water_level': 0.0}
        terrain = {}
        for cx in (0, 1):
            for cy in (0, 1):
                task = flat_task(cx * 256, cy * 256, z + (10.0 if bad and (cx, cy) == (1, 0) else 0.0))
                task['collision_box'] = (max(0, cx * 256 - 128), max(0, cy * 256 - 128),
                                         min(512, cx * 256 + 384), min(512, cy * 256 + 384))
                i0, j0 = int(task['collision_box'][0] // 128), int(task['collision_box'][1] // 128)
                i1, j1 = int(task['collision_box'][2] // 128), int(task['collision_box'][3] // 128)
                task['heights'] = [[task['heights'][0][0]] * (i1 - i0 + 1) for _ in range(j1 - j0 + 1)]
                terrain[(cx, cy)] = terrain_unit(task)
        return {'frame': {'cell': (3, -4), 'low': (0.0, 0.0), 'span': (512, 512)}, 'terrain': terrain}, section

    def test_a_good_frame_passes(self):
        spec, section = self.frame()
        self.assertEqual(early_frame_failures(spec, section, 'rcp3_m4'), [])

    def test_a_bad_chunk_stops_at_its_frame_and_names_it(self):
        spec, section = self.frame(bad=True)
        found = early_frame_failures(spec, section, 'rcp3_m4', jobs=2)
        self.assertTrue(found)
        self.assertTrue(all(f.startswith('frame of rcp3_m4 (cell 3,-4): chunk 1,0') for f in found), found)


if __name__ == '__main__':
    unittest.main()
