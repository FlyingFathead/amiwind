# SPDX-License-Identifier: GPL-3.0-only
"""Irregular ground (format 0.5): chunk terrain from the converter's own triangles.

Seyda Neen's ground has shoreline samples inserted into 128-unit tiles and a
32-unit patch at the port (prepare_world_regions.terrain_triangles,
prepare_quake.town_ground_triangles). A synthetic frame mixes the three kinds
of tiles (two coarse triangles, a refined fan, a 4 x 4 fine patch) across
chunk borders; the validator checks every ground sample is covered once and
lies on the source triangles, water where the ground dips below 0, and the
standing hull's seams against the triangles. Heights and the highest ground
over a rectangle are checked against brute force.
"""
import math
import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import format as F  # noqa: E402
from chim.collision import FrameScene, stand_height  # noqa: E402
from chim.ground import TriangleGround, clip_convex_xy  # noqa: E402
from chim.validate import validate  # noqa: E402
from player_hull import MINS  # noqa: E402
from test_chim_format import LOW, SPAN, STEP, ROWS, fixture, height, material  # noqa: E402


def z(x, y):
    # not planar anywhere, dips below the water level in part of the frame
    return height(x, y) + 6.0 * math.cos(y / 90.0)


def fine(i, j):
    return i in (1, 2) and j in (1, 2)


def tile_triangles(tx, ty):
    """The three kinds of tiles, watertight as the converter makes them: a fine 32-unit patch
    (2 x 2 tiles); tiles next to it with the patch's edge samples (a fan around an inner point,
    like shoreline insertion); two coarse triangles elsewhere, a fan on every third tile."""
    i, j = int((tx - LOW[0]) // STEP), int((ty - LOW[1]) // STEP)
    m = material(tx + STEP / 2, ty + STEP / 2)
    p = lambda x, y: [float(x), float(y), float(z(x, y))]  # noqa: E731
    out = []
    if fine(i, j):
        for yy in range(int(ty), int(ty) + STEP, 32):
            for xx in range(int(tx), int(tx) + STEP, 32):
                c = [p(xx, yy), p(xx + 32, yy), p(xx + 32, yy + 32), p(xx, yy + 32)]
                out += [([c[0], c[1], c[2]], m), ([c[0], c[2], c[3]], m)]
        return out
    # edges S, E, N, W next to the fine patch carry its samples
    need = [fine(i, j - 1), fine(i + 1, j), fine(i, j + 1), fine(i - 1, j)]
    if not any(need) and (i + 2 * j) % 3:
        c = [p(tx, ty), p(tx + STEP, ty), p(tx + STEP, ty + STEP), p(tx, ty + STEP)]
        return [([c[0], c[1], c[2]], m), ([c[0], c[2], c[3]], m)]
    corners = [(tx, ty), (tx + STEP, ty), (tx + STEP, ty + STEP), (tx, ty + STEP)]
    ring = []
    for e in range(4):
        (ax, ay), (bx, by) = corners[e], corners[(e + 1) % 4]
        ring.append(p(ax, ay))
        if need[e]:
            ring += [p(ax + (bx - ax) * k / 4, ay + (by - ay) * k / 4) for k in (1, 2, 3)]
    centre = p(tx + 61, ty + 70)
    return [([ring[k], ring[(k + 1) % len(ring)], centre], m) for k in range(len(ring))]


def ground():
    nx, ny = SPAN[0] // STEP, SPAN[1] // STEP
    tris = [t for j in range(ny) for i in range(nx) for t in tile_triangles(LOW[0] + i * STEP, LOW[1] + j * STEP)]
    return TriangleGround(tris, STEP, LOW, (nx, ny))


class TriangleGroundTests(unittest.TestCase):
    def test_height_and_highest_ground_match_brute_force(self):
        g = ground()
        rnd = random.Random(5)
        for _ in range(200):
            x, y = rnd.uniform(LOW[0], LOW[0] + SPAN[0] - 1), rnd.uniform(LOW[1], LOW[1] + SPAN[1] - 1)
            tri = next(t for t, _ in g.tile_list(*g.clamp_tile(x, y)) if clip_convex_xy(t, x - 1e-4, y - 1e-4,
                                                                                         x + 1e-4, y + 1e-4))
            self.assertAlmostEqual(g.height(x, y), float(g(x, y)), places=5)
            self.assertIsNotNone(tri)
        for _ in range(40):
            x, y = rnd.uniform(LOW[0], LOW[0] + SPAN[0] - 40), rnd.uniform(LOW[1], LOW[1] + SPAN[1] - 40)
            w, h = rnd.uniform(1, 40), rnd.uniform(1, 40)
            brute = max(g.height(x + w * a / 40, y + h * b / 40) for a in range(41) for b in range(41))
            self.assertGreaterEqual(g.max_over(x, y, x + w, y + h) + 1e-6, brute)
            self.assertLess(g.max_over(x, y, x + w, y + h) - brute, 0.6)

    def test_rows_round_trip_through_the_source_manifest(self):
        g = ground()
        h = TriangleGround.from_source({'terrain_triangles': g.rows(), 'terrain_step': STEP,
                                        'terrain_low': list(LOW), 'terrain_size': list(g.size)})
        self.assertEqual(h.rows(), g.rows())


class IrregularChunkTerrainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.ground = ground()
        cls.receipt, cls.source = fixture(Path(cls.tmp.name), placements=ROWS, ground=cls.ground)
        cls.fails, cls.world = validate(cls.tmp.name, cls.source)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_validator_passes_coverage_heights_water_and_seams(self):
        self.assertEqual(self.fails, [])
        self.assertGreater(self.world['seam_samples'], 0)

    def test_the_box_stands_on_the_triangles_across_chunk_borders(self):
        scene = FrameScene(self.world)
        for x, y in ((-256.2, -400.0), (-255.8, -400.0), (0.1, -350.0), (255.9, -330.0), (-100.0, 0.2),
                     (-100.0, -0.2), (-450.0, 300.0), (-330.0, -330.0)):
            with self.subTest(x=x, y=y):
                zz = stand_height(scene, x, y)
                want = self.ground.max_over(x + MINS[0], y + MINS[1], x - MINS[0], y - MINS[1]) - MINS[2]
                self.assertIsNotNone(zz)
                self.assertLess(abs(zz - want), 0.3, (zz, want))

    def test_refined_tiles_make_more_faces_than_coarse_ones(self):
        tiles = self.receipt['terrain']['tiles']
        self.assertEqual(tiles, (SPAN[0] // STEP) * (SPAN[1] // STEP))
        self.assertGreater(self.receipt['terrain']['faces'], 2 * tiles)



class GroundLookupTests(unittest.TestCase):
    def test_fast_cells_agree_with_the_exact_triangles(self):
        import numpy as np
        g = ground()
        rnd = np.random.default_rng(3)
        x = rnd.uniform(LOW[0], LOW[0] + SPAN[0], 4000)
        y = rnd.uniform(LOW[1], LOW[1] + SPAN[1], 4000)
        self.assertLess(float(np.abs(g(x, y) - g._exact(x, y)).max()), 1e-6)
        planes, _ = g._cells
        self.assertGreater(float(np.isfinite(planes[..., 0]).mean()), 0.5)    # most cells take the fast path

    def test_caches_are_not_pickled(self):
        import pickle
        g = ground()
        g(0.0, 0.0)
        h = pickle.loads(pickle.dumps(g))
        self.assertFalse(hasattr(h, '_cells'))
        self.assertAlmostEqual(float(h(10.0, 20.0)), float(g(10.0, 20.0)), places=9)


class GroundFingerprintTests(unittest.TestCase):
    def test_visibility_units_change_with_the_ground_lookup(self):
        # the sight lines read the ground through chim.ground (CHIM-PVS-SLOW-33): its source is part of them
        from chim.units import TOOLS
        self.assertIn('tools/chim/ground.py', TOOLS['pvs'])

@unittest.skipUnless(__import__('os').environ.get('AMIWIND_TEST_QBSP'), 'requires external qbsp')
class CompiledTerrainHullTests(unittest.TestCase):
    """CHIM-SEYDA-MEMORY-33: the chunk's standing hull compiled by qbsp holds the same ground as the
    routed chains (the validator's exact seam check and standing heights) in far fewer clipnodes."""

    def test_compiled_hull_is_exact_and_smaller(self):
        import os
        results = {}
        for hull in ('routed', 'compiled'):
            tmp = tempfile.mkdtemp()
            receipt, source = fixture(Path(tmp), placements=ROWS, ground=ground(),
                                      settings={'grain': 256, 'sector_chunks': 2, 'terrain_hull': hull},
                                      qbsp=os.environ['AMIWIND_TEST_QBSP'], collision_cache=Path(tmp) / 'cc')
            fails, world = validate(tmp, source)
            self.assertEqual(fails, [], hull)
            self.assertGreater(world['seam_samples'], 0)
            scene = FrameScene(world)
            heights = [stand_height(scene, x, y) for x, y in ((-256.2, -400.0), (-255.8, -400.0), (0.1, -350.0),
                                                                (-100.0, 0.2), (-450.0, 300.0), (-330.0, -330.0))]
            clip = sum(len(F.read_brush_image(c['image'])[9]) // 8 for _, _, chunks in world['frames'] for c in chunks)
            results[hull] = (heights, clip)
        for a, b in zip(results['routed'][0], results['compiled'][0]):
            self.assertLess(abs(a - b), 0.05)
        self.assertLess(results['compiled'][1], results['routed'][1])


if __name__ == '__main__':
    unittest.main()
