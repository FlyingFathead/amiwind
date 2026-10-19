"""Rock shell audit (CHIM-ROCKS-OPEN-SHELLS-43): synthetic shells, the rotation order, the gate."""
import importlib.util
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

NUMPY = importlib.util.find_spec('numpy') is not None
SCIPY = NUMPY and importlib.util.find_spec('scipy') is not None


def _cup():
    """An open box (no bottom): five quads, outward winding; four open edges at z = 0."""
    import numpy as np
    v = np.array([[0, 0, 0], [4, 0, 0], [4, 4, 0], [0, 4, 0], [0, 0, 4], [4, 0, 4], [4, 4, 4], [0, 4, 4]], float)
    quads = [(4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    f = []
    for a, b, c, d in quads:
        f += [(a, b, c, 0), (a, c, d, 0)]
    return v, np.array(f, int)


def _quat_rotate(q, p):
    w, x, y, z = q
    # p' = q p q*, Hamilton
    qv = (x, y, z)
    t = [2 * (qv[1] * p[2] - qv[2] * p[1]), 2 * (qv[2] * p[0] - qv[0] * p[2]), 2 * (qv[0] * p[1] - qv[1] * p[0])]
    return [p[i] + w * t[i] + (qv[(i + 1) % 3] * t[(i + 2) % 3] - qv[(i + 2) % 3] * t[(i + 1) % 3]) for i in range(3)]


def _quat(angle, axis):
    s = math.sin(angle / 2)
    return (math.cos(angle / 2), axis[0] * s, axis[1] * s, axis[2] * s)


@unittest.skipUnless(NUMPY, 'numpy')
class ShellTests(unittest.TestCase):
    def test_open_cup_has_four_open_edges_and_no_flips(self):
        from rock_shell_audit import shell_edges
        v, f = _cup()
        _, open_edges, nonmanifold, flipped = shell_edges(v, f)
        self.assertEqual((len(open_edges), len(nonmanifold), len(flipped)), (4, 0, 0))

    def test_a_turned_face_is_a_flipped_edge(self):
        from rock_shell_audit import shell_edges
        v, f = _cup()
        f[0, :3] = f[0, [0, 2, 1]]
        self.assertGreater(len(shell_edges(v, f)[3]), 0)

    def test_merged_face_t_junction_is_not_an_open_edge(self):
        # a 2x1 face beside two 1x1 faces: the long edge meets the middle vertex of the other side
        from rock_shell_audit import polygon_open_edges
        long_face = [(0, 0, 0), (2, 0, 0), (2, 1, 0), (0, 1, 0)]
        left = [(0, 1, 0), (1, 1, 0), (1, 2, 0), (0, 2, 0)]
        right = [(1, 1, 0), (2, 1, 0), (2, 2, 0), (1, 2, 0)]
        points, edges = polygon_open_edges([long_face, left, right])
        length = sum(math.dist(points[a], points[b]) for a, b in edges)
        self.assertAlmostEqual(length, 8.0)          # only the outline of the 2x2 square is open

    @unittest.skipUnless(SCIPY, 'scipy')
    def test_coverage_sees_missing_and_turned_faces(self):
        import numpy as np
        from rock_shell_audit import coverage
        v, f = _cup()
        tris = v[f[:, :3]]
        normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
        normals /= np.linalg.norm(normals, axis=1)[:, None]
        same = coverage(tris, tris, normals)
        self.assertEqual((same['same'], same['missing'], same['turned']), (1.0, 0.0, 0.0))
        turned = coverage(tris, tris, -normals)
        self.assertEqual(turned['turned'], 1.0)
        dropped = coverage(tris, tris[2:], normals[2:])
        self.assertAlmostEqual(dropped['missing'], .2, places=3)

    def test_rim_buried_or_exposed(self):
        import numpy as np
        from rock_shell_audit import exposed, rim_samples, shell_edges, triangle_ground
        v, f = _cup()
        points, edges, _, _ = shell_edges(v, f)
        rims = rim_samples(points, edges)
        ground = triangle_ground([[(-10, -10, 1), (10, -10, 1), (10, 10, 1)], [(-10, -10, 1), (10, 10, 1), (-10, 10, 1)]])
        self.assertEqual(exposed(rims, ground, .5), (0, len(rims)))
        self.assertEqual(exposed(rims + np.array([0, 0, 2.]), ground, .5), (len(rims), len(rims)))


@unittest.skipUnless(NUMPY, 'numpy')
class TurnTests(unittest.TestCase):
    def test_converter_turn_is_z_then_y_then_x_as_in_openmw(self):
        # OpenMW places statics with Quat(z, -Z) * Quat(y, -Y) * Quat(x, -X) (osg order: the left one first),
        # i.e. the rotation about -Z by z first, then -Y by y, then -X by x. The rims of the authored rocks
        # stay buried only with this reading (CHIM-ROCKS-OPEN-SHELLS-43).
        import numpy as np
        from rock_shell_audit import CONVERTER_TURN, candidate_rotations
        turn = candidate_rotations()[CONVERTER_TURN]
        for angles in ((0.4, 0.0, 0.0), (0.0, 0.3, 0.0), (0.2, 0.3, 1.1), (6.08, 5.9, 4.3)):
            matrix = turn(angles)
            for p in ((1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 2, 3)):
                q = list(p)
                for angle, axis in ((angles[2], (0, 0, -1)), (angles[1], (0, -1, 0)), (angles[0], (-1, 0, 0))):
                    q = _quat_rotate(_quat(angle, axis), q)
                np.testing.assert_allclose(matrix @ np.array(p, float), q, atol=1e-9)

    def test_other_readings_differ_for_a_tilt(self):
        import numpy as np
        from rock_shell_audit import candidate_rotations
        turns = list(candidate_rotations().values())
        base = turns[0]((0.2, 0.3, 1.1))
        for other in turns[1:]:
            self.assertGreater(np.abs(other((0.2, 0.3, 1.1)) - base).max(), 1e-3)


class GateTests(unittest.TestCase):
    def report(self, **row):
        base = {'model': 'meshes/f/terrain_rock_x.nif', 'triangles': 100, 'variants': [], 'two_sided': False,
                'reduced': False}
        base.update(row)
        return {'rows': [base], 'best_turn_per_mesh': {'converter (Z, then Y, then X)': 3}}

    def test_clean_report_passes(self):
        from rock_shell_audit import check
        self.assertEqual(check(self.report()), [])

    def test_two_sided_source_fails(self):
        from rock_shell_audit import check
        self.assertIn('both sides', check(self.report(two_sided=True))[0]['reason'])

    def test_unreduced_variant_that_loses_faces_fails(self):
        from rock_shell_audit import check
        bad = {'name': 'f/terrain_rock_x@s1', 'faces': 98, 'stored_faces': 98,
               'coverage': {'same': .9, 'turned': 0., 'missing': .1}}
        self.assertEqual(len(check(self.report(variants=[bad]))), 1)
        self.assertEqual(check(self.report(variants=[bad], reduced=True)), [])

    def test_rims_opened_in_conversion_fail_unless_known(self):
        from rock_shell_audit import check
        row = {'rim_exposure': {'compared': 20, 'chim': .2, 'original': .05}}
        self.assertEqual(len(check(self.report(**row))), 1)
        known = {'meshes/f/terrain_rock_x.nif': {'extra': .15, 'bug': 'CHIM-ROCKS-OPEN-SHELLS-43'}}
        self.assertEqual(check(self.report(**row), known), [])
        worse = {'rim_exposure': {'compared': 20, 'chim': .3, 'original': .05}}
        self.assertIn('more than recorded', check(self.report(**worse), known)[0]['reason'])

    def test_wrong_turn_winning_fails(self):
        from rock_shell_audit import check
        report = self.report()
        report['best_turn_per_mesh'] = {'converter (Z, then Y, then X)': 1, 'other sign': 5}
        self.assertEqual(len(check(report)), 1)


if __name__ == '__main__':
    unittest.main()
