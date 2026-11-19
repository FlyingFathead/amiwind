# SPDX-License-Identifier: GPL-3.0-only
"""The creature library's whole route (tools/creature_whole.py) and the surface check of its models
(tools/creature_surface.py); CREATURE-RACER-HOLES-67. Synthetic data, no game files."""
import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import creature_surface as C  # noqa: E402
import creature_whole as W  # noqa: E402

GEOMETRY = all(importlib.util.find_spec(n) for n in ('scipy', 'PIL'))


class Travel:
    """A kept skeleton whose root travels 100 units a second along x and y and bobs in z; 'body' rides it."""
    keys = [(0.0, 'walkforward: start'), (1.0, 'walkforward: stop'), (2.0, 'idle: start'), (3.0, 'idle: stop'),
            (4.0, 'runforward: start'), (5.0, 'runforward: stop')]
    parents = {'root bone': None, 'body': 'root bone'}
    nodes = {'root bone': None, 'body': None}
    scaled = {}

    def pose(self, time):
        return None

    def local(self, name, time):
        m = np.eye(4)
        if name == 'root bone':
            m[3, :3] = (100 * time, 50 * time, 10 + time)
        else:
            m[3, :3] = (1, 2, 3)
        return m


class HeldRootTests(unittest.TestCase):
    def test_moving_windows(self):
        self.assertEqual(W.moving_windows(Travel.keys), {'walkforward': (0.0, 1.0), 'runforward': (4.0, 5.0)})

    def test_root_held_in_moving_groups_only(self):
        held = W.HeldRoot(Travel(), 'root bone')
        m = held.local('root bone', 0.5)
        np.testing.assert_allclose(m[3, :3], (0, 0, 10.5))          # x, y at the walk's start, the bob kept
        np.testing.assert_allclose(held.local('root bone', 4.75)[3, :3], (400, 200, 14.75))
        np.testing.assert_allclose(held.local('root bone', 2.5)[3, :3], (250, 125, 12.5))   # idle: as authored
        np.testing.assert_allclose(held.local('body', 0.5)[3, :3], (1, 2, 3))
        self.assertEqual(W.HeldRoot(Travel(), 'bip01').local('root bone', 0.5)[3, 0], 50)  # another root: untouched

    def test_whole_profile_meshes(self):
        self.assertEqual(W.whole_meshes({'r/cliffracer.nif': ['cliff racer'], 'r/scamp_fetch.nif': ['scamp']}),
                         {'r/cliffracer.nif'})
        self.assertEqual(W.METHOD, 'skeletal-whole')


def cube(lo=0.0, hi=8.0):
    p = np.array([[x, y, z] for x in (lo, hi) for y in (lo, hi) for z in (lo, hi)], float)
    f = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
                  [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    return p, f


@unittest.skipUnless(GEOMETRY, 'optional geometry dependencies')
class SurfaceCheckTests(unittest.TestCase):
    def test_alias_model_read_back(self):
        from PIL import Image
        from npc_geometry import animated_mdl
        p, f = cube()
        skin = Image.new('P', (8, 8))
        raw = animated_mdl(p[None], f, np.zeros((len(p), 2), int), skin)
        pos, faces, size, _ = C.read_alias(raw)
        self.assertEqual(size, (8, 8))
        np.testing.assert_array_equal(faces, f)
        np.testing.assert_allclose(pos, p, atol=8 / 255 + 1e-6)

    def test_coverage_counts_lost_surface(self):
        p, f = cube()
        source = p[f]
        self.assertGreater(C.coverage(source, p, f), .999)
        self.assertLess(C.coverage(source, p, f[:6]), .75)        # half the faces gone
        self.assertEqual(C.coverage(source, p, f[:0]), 0.0)

    def test_only_a_whole_profile_model_stops(self):
        row = {'triangles': 474, 'source_triangles': 965, 'coverage': .66, 'lost_shapes': ['Tri tail'],
               'whole': True}
        self.assertEqual(len(C.problems(row)), 3)
        self.assertEqual(C.problems(dict(row, whole=False)), [])
        self.assertEqual(C.problems(dict(row, triangles=965, coverage=1.0, lost_shapes=[])), [])


class Wiring(unittest.TestCase):
    def test_library_routes_whole_meshes_and_checks(self):
        text = (ROOT / 'tools' / 'creature_library.py').read_text(encoding='utf-8')
        self.assertIn('creature_whole.whole_meshes(meshes)', text)
        self.assertIn('worker=creature_whole.unit', text)
        self.assertIn('check_library(data, done, out_id1, bipedal, whole, jobs)', text)
        # the whole route is its own worker: the library's own worker does not name it (its code key stays)
        start = text.index('def _unit(task):')
        body = text[start:text.index('\ndef ', start + 1)]
        self.assertNotIn('creature_whole', body)


if __name__ == '__main__':
    unittest.main()
