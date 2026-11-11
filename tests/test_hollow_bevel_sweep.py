# SPDX-License-Identifier: GPL-3.0-only
"""tools/hollow_bevel_sweep.py (COLLISION-WORLDWIDE-REDUCTION-64): the standing-box sweep of a hollow model's
plates, exact bevels against the approximate default. A plate's approximate standing hull is never smaller than its
exact one (no point pushes through), and the approximate form takes fewer planes."""
import unittest

import numpy as np

import hollow_bevel_sweep as S


def plate(corners, thick=1.0):
    """One collision plate as mesh_geometry.shell_collision_parts makes it: the triangle and its copy behind it."""
    c = np.asarray(corners, float)
    n = np.cross(c[1] - c[0], c[2] - c[0])
    n /= np.linalg.norm(n)
    return (np.vstack([c, c - thick * n]), None, [], 0.)


class HollowBevelSweep(unittest.TestCase):
    def test_no_push_through_and_fewer_bytes(self):
        parts = [plate([[0, 0, 0], [256, 0, 0], [0, 256, 0]]),                       # a floor
                 plate([[0, 0, 0], [0, 256, 128], [0, 0, 128]]),                      # a sloped wall
                 plate([[128, 0, 0], [128, 64, 200], [128, 128, 0]])]                 # a leaning wall
        out = S.model_sweep(parts, 2)
        self.assertEqual(out['pushed'], 0)
        self.assertEqual(out['walkable'], 1)
        self.assertGreater(out['points'], 0)
        self.assertLessEqual(out['bytes_default'], out['bytes_exact'])
        same = S.model_sweep(parts, 0)
        self.assertEqual((same['pushed'], same['early'], same['bytes_default']), (0, 0, same['bytes_exact']))


if __name__ == '__main__':
    unittest.main()
