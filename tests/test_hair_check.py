"""The universal hair check's pass/fail core (tools/hair_check.py, NPC-HAIR-BACK-MISSING-53), on synthetic meshes only:
open edges and pieces after welding by position, the head-through-hair count, and the verdict rule (no open edge
the original lacks; head through hair in at most PASS_HEAD_THROUGH of the original's hair directions)."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]

from test_npc_head_detail import needs_numpy  # noqa: E402


def ball(radius, rows=12, cols=24, top_only=False):
    """A UV sphere around (0, 0, 30), outward winding; top_only: the cap above the equator (an open shell)."""
    import numpy as np
    phi = np.linspace(.05, np.pi / 2 if top_only else np.pi - .05, rows + 1)
    theta = np.linspace(0, 2 * np.pi, cols + 1)[:-1]
    points = np.array([(radius * np.sin(p) * np.cos(t), radius * np.sin(p) * np.sin(t), 30 + radius * np.cos(p))
                       for p in phi for t in theta])
    faces = []
    for j in range(rows):
        for i in range(cols):
            a, b = j * cols + i, j * cols + (i + 1) % cols
            faces += [(a, b, a + cols), (b, b + cols, a + cols)]
    faces = np.array(faces)
    n = np.cross(points[faces[:, 1]] - points[faces[:, 0]], points[faces[:, 2]] - points[faces[:, 0]])
    inward = np.einsum('ij,ij->i', n, points[faces].mean(1) - [0, 0, 30]) < 0
    faces[inward] = faces[inward][:, [0, 2, 1]]
    return points, faces


def join(head, hair):
    import numpy as np
    (hp, hf), (cp, cf) = head, hair
    return (np.concatenate((hp, cp)), np.concatenate((hf, cf + len(hp))),
            np.array([0] * len(hf) + [1] * len(cf)))


class HairCheck(unittest.TestCase):
    @needs_numpy
    def test_open_edges_and_pieces(self):
        import numpy as np
        from hair_check import open_edges, pieces
        p, f = ball(4, top_only=True)
        self.assertEqual(open_edges(p, f), 24 + 24)          # the rim, and the small hole at the pole
        self.assertEqual(pieces(p, f), 1)
        # the same cap with split vertices (a UV seam duplicated): welding by position keeps it closed
        split = np.concatenate((p, p))
        self.assertEqual(open_edges(split, np.concatenate((f[:10], f[10:] + len(p)))), 48)
        self.assertEqual(pieces(np.concatenate((p, p + 100)), np.concatenate((f, f + len(p)))), 2)

    @needs_numpy
    def test_head_through_hair(self):
        from hair_check import head_through_hair, sphere_dirs
        dirs = sphere_dirs(400)
        original = join(ball(4), ball(4.3, top_only=True))
        same, hair_dirs = head_through_hair(original, original, dirs)
        self.assertEqual(same, 0)
        self.assertGreater(hair_dirs, 100)
        sunk = join(ball(4), ball(3.7, top_only=True))         # the cap inside the head: the head shows
        through, _ = head_through_hair(original, sunk, dirs)
        self.assertGreater(through, .9 * hair_dirs)

    def test_verdict(self):
        from hair_check import verdict, PASS_HEAD_THROUGH
        row = {'orig_open_edges': 10, 'ours_open_edges': 10, 'head_through_hair': 0, 'hair_dirs': 1000,
               'model_vertices': 1878, 'vertex_limit': 3072}
        self.assertEqual(verdict(row), 'pass')
        self.assertIn('open edges', verdict(dict(row, ours_open_edges=11)))
        self.assertEqual(verdict(dict(row, head_through_hair=int(PASS_HEAD_THROUGH * 1000))), 'pass')
        self.assertIn('head through hair', verdict(dict(row, head_through_hair=int(PASS_HEAD_THROUGH * 1000) + 1)))
        self.assertIn('vertices', verdict(dict(row, model_vertices=3073)))
        self.assertTrue(verdict({'error': 'x'}).startswith('error'))


if __name__ == '__main__':
    unittest.main()
