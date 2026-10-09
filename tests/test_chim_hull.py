# SPDX-License-Identifier: GPL-3.0-only
"""Seamless standing hull of CHIM terrain chunks (format 0.4), on synthetic ground."""
import random
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from scipy.spatial import ConvexHull

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import format as F  # noqa: E402
from chim.models import BrushLumps, hull_pieces  # noqa: E402
from chim.terrain import chunk_terrain, tile_polygons  # noqa: E402
from chim.validate import Failures, hull_contents, hull_seams, validate  # noqa: E402
from test_chim_format import fixture  # noqa: E402

STEP = 128
SPAN = 768                       # 6 x 6 tiles: a 2 x 2-tile chunk in the middle has a full ring
LOW = 0.0


def ground(x, y):
    # not separable; the ring (outside the middle chunk) rises 150 units, so across every chunk
    # edge the neighbour's ground under the box is higher than the chunk's own
    ring = 150.0 if not (256 <= x <= 512 and 256 <= y <= 512) else 0.0
    return 20.0 * ((x / 97.0) % 3) - 0.1 * y + 0.0004 * x * y + ring


SOURCE = {'terrain_step': STEP, 'terrain_low': [LOW, LOW],
          'terrain_heights': [[ground(LOW + i * STEP, LOW + j * STEP) for i in range(SPAN // STEP + 1)]
                              for j in range(SPAN // STEP + 1)]}


def height(x, y):
    return SOURCE['terrain_heights'][int(round((y - LOW) / STEP))][int(round((x - LOW) / STEP))]


def chunk(box, collision_box):
    lumps, info = chunk_terrain(box, STEP, height, lambda x, y: 1, -1024, lambda m: 0, 1,
                                collision_box=collision_box)
    return {'image': F.brush_image(lumps)[0], 'cx': 1, 'cy': 1}, info


def ring_pieces():
    """The tile prisms of the middle chunk and its ring, as chunk_terrain makes them."""
    pieces = []
    for ty in range(128, 640, STEP):
        for tx in range(128, 640, STEP):
            corners = [[tx + dx, ty + dy, height(tx + dx, ty + dy)] for dx, dy in ((0, 0), (STEP, 0), (STEP, STEP), (0, STEP))]
            for poly in tile_polygons(corners):
                bottom = poly.copy()
                bottom[:, 2] = -1024
                pts = np.vstack([poly, bottom])
                pieces.append((pts, SimpleNamespace(equations=ConvexHull(pts).equations), [], 0.))
    return pieces


BOX = (256, 256, 512, 512)
RING = (128, 128, 640, 640)


class SeamlessHullTests(unittest.TestCase):
    def test_ring_makes_the_border_seamless(self):
        c, info = chunk(BOX, RING)
        self.assertEqual(info['ring_tiles'], 12)
        self.assertEqual(info['pieces'], 32)
        fails = Failures()
        self.assertGreater(hull_seams(c, BOX, SOURCE, fails), 0)
        self.assertEqual(list(fails), [])

    def test_without_edge_bevels_the_box_rests_above_ridges(self):
        # CHIM-TERRAIN-HULL-BEVELS-33: face-offset planes alone (no edge bevels) leave the
        # hull too big over convex ridges; the tightened seam check catches it.
        from unittest.mock import patch
        plain = BrushLumps.routed_hull
        with patch.object(BrushLumps, 'routed_hull',
                          lambda self, pieces, region, leaf_pieces=None: plain(self, pieces, region, leaf_pieces, False)):
            c, _ = chunk(BOX, RING)
        fails = Failures()
        hull_seams(c, BOX, SOURCE, fails)
        self.assertTrue(any('rest above' in f for f in fails), list(fails))

    def test_without_the_ring_the_neighbour_ground_is_not_felt(self):
        # format 0.3: the chunk's own tiles only. The validator must catch the seam.
        c, info = chunk(BOX, None)
        self.assertEqual(info['ring_tiles'], 0)
        fails = Failures()
        hull_seams(c, BOX, SOURCE, fails)
        self.assertTrue(any('hull 1 seam' in f for f in fails), list(fails))

    def test_routing_keeps_chains_short(self):
        _, info = chunk(BOX, RING)
        # inside a tile two pieces; at a chunk corner at most four tiles (eight pieces)
        self.assertLessEqual(info['hull_chain_max'], 8)
        lumps = BrushLumps()
        lumps.routed_hull(hull_pieces(ring_pieces()), BOX, leaf_pieces=2)
        chains = sorted(lumps.hull_chains)
        self.assertEqual(chains[0], 2)                  # a tile's own two pieces inside it
        self.assertEqual(chains.count(8), 9)            # the 3 x 3 corner squares where four tiles meet

    def test_routed_hull_classifies_like_the_plain_chain(self):
        pieces = ring_pieces()
        for leaf in (2, 8):
            self._same_as_chain(pieces, leaf)

    def _same_as_chain(self, pieces, leaf):
        routed, chained = BrushLumps(), BrushLumps()
        r_root = routed.routed_hull(hull_pieces(pieces), BOX, leaf_pieces=leaf)
        _, c_root = chained.collider(hull_pieces(pieces), True, point_hull=False)
        rng = random.Random(7)
        for _ in range(3000):
            x, y = rng.uniform(BOX[0], BOX[2]), rng.uniform(BOX[1], BOX[3])
            z = ground(x, y) + rng.uniform(-30, 40)
            self.assertEqual(hull_contents(routed.lumps, r_root, (x, y, z)),
                             hull_contents(chained.lumps, c_root, (x, y, z)), (x, y, z))

    def test_fixture_world_is_checked_for_seams(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, source = fixture(Path(tmp))
            fails, world = validate(tmp, source)
        self.assertEqual(list(fails), [])
        self.assertGreater(world['seam_samples'], 16 * 4 * 6)


if __name__ == '__main__':
    unittest.main()
