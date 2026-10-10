# SPDX-License-Identifier: GPL-3.0-only
"""CHIM lighting measurements (tools/chim/lighting.py): lightmap sizes, the original's attenuation, the light reach
test and the frame light selection. Synthetic geometry and lights only; no game data."""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from chim import lighting as L  # noqa: E402


def square_lumps(size=64.0, special=False):
    """BSP29 lumps of one upward square face of size x size at z = 0, texture axes 1:1."""
    import struct
    v = [(0, 0, 0), (size, 0, 0), (size, size, 0), (0, size, 0)]
    lumps = [bytearray() for _ in range(15)]
    lumps[1] = bytearray(struct.pack('<4fi', 0, 0, 1, 0, 2))
    lumps[3] = bytearray(b''.join(struct.pack('<3f', *p) for p in v))
    lumps[6] = bytearray(struct.pack('<8fii', 1, 0, 0, 0, 0, 1, 0, 0, 0, 1 if special else 0))
    lumps[12] = bytearray(struct.pack('<HH', 0, 0) + b''.join(struct.pack('<HH', i, (i + 1) % 4) for i in range(4)))
    lumps[13] = bytearray(struct.pack('<4i', 1, 2, 3, 4))
    lumps[7] = bytearray(struct.pack('<HhihH4Bi', 0, 0, 0, 4, 0, 0, 255, 255, 255, 0))
    return lumps


class LightingMeasureTests(unittest.TestCase):
    def test_face_samples_follow_the_engine_grid_and_skip_special_faces(self):
        self.assertEqual(list(L.face_samples(square_lumps(64.0))), [25])       # (64 / 16 + 1) squared
        self.assertEqual(list(L.face_samples(square_lumps(64.0, special=True))), [0])
        pts = L.face_sample_points(square_lumps(64.0))
        self.assertEqual(len(pts), 1)
        self.assertEqual(pts[0][2].shape, (25, 3))
        self.assertTrue(np.allclose(pts[0][2][:, 2], 0))

    def test_attenuation_is_the_originals_and_negative_lights_subtract(self):
        light = {'origin': (0, 0, 0), 'qradius': 10.0, 'colour': (255, 255, 255), 'class': 'pure_light', 'style': 0}
        pts = np.array([[0, 0, -1.0], [0, 0, -10.0], [0, 0, -15.0], [0, 0, -20.0], [0, 0, -25.0]])
        up = np.array([0, 0, 1.0])
        steady, moving = L.illumination(pts, up, [light])
        self.assertAlmostEqual(steady[0], 1.0)                 # clamped near the source
        self.assertAlmostEqual(steady[1], 1 / 3, places=6)     # 1 / (3 d / r) at the radius
        self.assertTrue(0 < steady[2] < 1 / 4.5)               # fading between r and 2 r
        self.assertEqual(steady[3], 0.0)                       # nothing at twice the radius
        self.assertEqual(steady[4], 0.0)
        self.assertFalse(moving.any())
        dark = dict(light, **{'class': 'negative'})
        s, _ = L.illumination(pts[:2], up, [light, dark])
        self.assertTrue(np.allclose(s, 0))
        flick = dict(light, style=1)
        s, m = L.illumination(pts[:1], up, [flick])
        self.assertEqual((s[0], m[0]), (0.0, 1.0))             # animated lights go to their own style
        back, _ = L.illumination(pts[:1], np.array([0, 0, -1.0]), [light])
        self.assertEqual(back[0], 0.0)                         # faces turned away get nothing

    def test_reach_and_frame_selection(self):
        rec = {'origin': (100.0, 0.0, 0.0), 'box': ((-8, -8, 0), (8, 8, 16))}
        self.assertTrue(L.reached(rec, np.array([[80.0, 0, 8, 15]])))
        self.assertFalse(L.reached(rec, np.array([[50.0, 0, 8, 15]])))
        self.assertFalse(L.reached(rec, np.zeros((0, 4))))
        frame = {'centre': (4096.0, 4096.0), 'low': (-1024.0, -1024.0), 'grain': 256, 'nx': 8, 'ny': 8}
        lights = [{'pos': (4096.0, 4096.0, 400.0), 'radius': 256, 'class': 'lamp'},
                  {'pos': (4096.0 + 4 * 1300, 4096.0, 0.0), 'radius': 256, 'class': 'lamp'},     # too far
                  {'pos': (4096.0, 4096.0, 0.0), 'radius': 256, 'class': 'off'},                # gives no light
                  {'pos': (4096.0, 4096.0, 0.0), 'radius': 4, 'class': 'pure_light'}]           # radius at least 16
        got = L.frame_lights(lights, frame)
        self.assertEqual(len(got), 2)
        self.assertEqual(got[0]['origin'], (0.0, 0.0, 100.0))
        self.assertEqual((got[0]['qradius'], got[1]['qradius']), (64.0, 4.0))
        self.assertEqual(L.OPTIONS, ('none', 'a', 'b', 'c', 'd', 'e'))


if __name__ == '__main__':
    unittest.main()
