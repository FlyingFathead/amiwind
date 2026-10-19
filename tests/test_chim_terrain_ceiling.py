# SPDX-License-Identifier: GPL-3.0-only
"""CHIM terrain over the terrain ceiling: raised ceilings, bounds that hold the faces, the height audit
(CHIM-RED-MOUNTAIN-SOLID-SKY-43)."""
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import format as F  # noqa: E402
from chim.build import frame_ground_zmax  # noqa: E402
from chim.frame_map import frame_top  # noqa: E402
from chim.terrain import (CHUNK_HEADROOM, FLIGHT_BAND, FRAME_HEADROOM, TERRAIN_CEILING, chunk_ceiling,  # noqa: E402
                          chunk_terrain, covering_ceiling, frame_ceiling)
from chim.validate import Failures, world_tree  # noqa: E402

STEP = 128
BASE = 4600.0                   # Red Mountain's ground: up to 4,730 frame-local units


def height(x, y):
    return BASE + 0.05 * x + 0.03 * y


def build(ceiling):
    return chunk_terrain((0, 0, 256, 256), STEP, height, lambda x, y: 1, -1024, lambda m: 0, 1, ceiling=ceiling)


class CeilingTest(unittest.TestCase):
    def test_low_ground_keeps_the_ceiling(self):
        # every frame under the ceiling keeps its bytes: the same ceiling as before
        self.assertEqual(covering_ceiling(1000, FRAME_HEADROOM), TERRAIN_CEILING)
        self.assertEqual(covering_ceiling(TERRAIN_CEILING - FRAME_HEADROOM, FRAME_HEADROOM), TERRAIN_CEILING)
        self.assertEqual(chunk_ceiling({'heights': [[0, 10], [1900, 20]]}), TERRAIN_CEILING)

    def test_high_ground_gets_a_flight_band(self):
        # Red Mountain's 4,730 gets 9,216: the ground plus the flight band, rounded up to 1,024
        self.assertEqual(covering_ceiling(4730, FRAME_HEADROOM), 9216)
        self.assertGreaterEqual(covering_ceiling(4730, FRAME_HEADROOM) - 4730, FLIGHT_BAND)
        # near the ceiling (eye and jump over 2,048) is raised too
        self.assertGreater(covering_ceiling(TERRAIN_CEILING - FRAME_HEADROOM + 1, FRAME_HEADROOM), TERRAIN_CEILING)
        self.assertGreater(chunk_ceiling({'heights': [[TERRAIN_CEILING - CHUNK_HEADROOM + 1]]}), TERRAIN_CEILING)
        # triangles and lava tops count
        self.assertGreater(chunk_ceiling({'heights': None, 'triangles': [[0, 0, [[0, 0, 3000, 1, 0, 0, 0, 1, 0, 1]]]]}),
                           TERRAIN_CEILING)
        self.assertGreater(chunk_ceiling({'heights': [[0]], 'liquids': [{'top': 2500.0, 'hull': []}]}), TERRAIN_CEILING)

    def test_frame_ground_zmax(self):
        self.assertEqual(frame_ground_zmax([[1, 2], [4730, 3]], None, None, 0.0), 4730.0)
        self.assertEqual(frame_ground_zmax([[-50, -20]], None, None, 0.0), 0.0)

    def test_tall_placement_raises_the_frame(self):
        # dev2: a tower on ground of 1,392 reached 2,116, over its chunk's 2,048 box
        self.assertEqual(frame_ceiling(1392, None), TERRAIN_CEILING)
        self.assertEqual(frame_ceiling(1392, 1900), TERRAIN_CEILING)
        self.assertEqual(frame_ceiling(1392, 2116), 7168)
        self.assertEqual(frame_ceiling(4730, 4858), 9216)
        self.assertEqual(frame_top([{'zmax': 1392, 'owned': [{'box': ((0, 0, 1300), (10, 10, 2116))}]}]), 7168.0)

    def test_frame_top(self):
        self.assertEqual(frame_top([{'zmax': 300}, {'zmax': 1200}]), float(TERRAIN_CEILING))
        self.assertEqual(frame_top([{'zmax': 4730}, {'zmax': 2000}]), 9216.0)

    def test_player_start_traced_from_over_the_ground(self):
        # the region frame map's start: traced down from over the frame's highest ground, never from inside the
        # mountain (dev2 traced from 2,048 into ground at 2,890-4,700: the start was inside solid)
        from unittest import mock
        from chim import frame_map as FM
        world = {'frames': [('frames/x+02/y+09/frame.ccf', {'cell': [2, 9]}, [{'zmin': 2890, 'zmax': 4700}])]}
        seen = {}

        def trace(scene, point, top, bottom):
            seen['top'], seen['bottom'] = top, bottom
            return 4000.0
        with mock.patch('chim.collision.FrameScene', lambda *a, **k: None), mock.patch.object(FM, 'ground_trace', trace):
            self.assertEqual(FM.frame_ground(world, (2, 9)), 4000.0)
        self.assertGreaterEqual(seen['top'], 4700 + FLIGHT_BAND)
        self.assertLess(seen['bottom'], 2890)

    def test_ground_over_the_ceiling_is_refused(self):
        # the old fixed ceiling under Red Mountain's ground: faces would lie outside their node boxes
        with self.assertRaises(ValueError):
            build(TERRAIN_CEILING)

    def test_raised_ceiling_holds_every_face(self):
        lumps, info = build(chunk_ceiling({'heights': [[height(x, y) for x in (0, 256)] for y in (0, 256)]}))
        fails = Failures()
        world_tree(lumps, 'chunk', fails)
        self.assertEqual(list(fails), [])
        nodes = list(struct.iter_unpack('<ihh6h2H', lumps[5]))
        self.assertGreaterEqual(nodes[0][8], info.get('zmax', BASE))

    def test_raised_ceiling_costs_no_bytes(self):
        # a taller box is only other bound values: the same nodes, leaves, planes, clipnodes, faces and bytes
        def low(x, y):
            return 100.0 + 0.05 * x
        a, ia = chunk_terrain((0, 0, 256, 256), STEP, low, lambda x, y: 1, -1024, lambda m: 0, 1,
                              ceiling=TERRAIN_CEILING)
        b, ib = chunk_terrain((0, 0, 256, 256), STEP, low, lambda x, y: 1, -1024, lambda m: 0, 1, ceiling=9216)
        self.assertEqual([len(x) for x in a], [len(x) for x in b])
        self.assertEqual(len(F.brush_image(a)[0]), len(F.brush_image(b)[0]))
        for k in (1, 3, 7, 9, 11, 12, 13):        # planes, vertexes, faces, clipnodes, marks, edges, surfedges
            self.assertEqual(bytes(a[k]), bytes(b[k]), k)

    def test_validator_names_faces_over_their_node(self):
        lumps, _ = build(9216)
        lumps = list(lumps)
        nodes = bytearray(lumps[5])
        for k in range(len(nodes) // 24):          # every node box closed at the old ceiling
            struct.pack_into('<h', nodes, 24 * k + 18, TERRAIN_CEILING)
        lumps[5] = bytes(nodes)
        fails = Failures()
        world_tree(lumps, 'chunk 0,0', fails)
        self.assertTrue(any('outside their node bounds' in f for f in fails), list(fails))


if __name__ == '__main__':
    unittest.main()
