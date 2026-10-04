import unittest
import numpy as np

from canonical_point_tree import build_point_tree, EMPTY, SOLID, TRACE_EPSILON


class Land:
    origin = [0, 0, 0]

    def triangles(self, bounds):
        return iter([[[0, 0, -4], [32, 0, 4], [32, 32, 12]],
                     [[0, 0, -4], [32, 32, 12], [0, 32, 20]]])


def contents(tree, point, native=False):
    planes, nodes, root, _ = tree
    while root >= 0:
        index, front, back = nodes[root]
        plane = planes[index]
        if native:
            q, p = np.asarray(point, np.float32), np.asarray(plane[:4], np.float32)
            distance = np.float32(np.float32(np.float32(q[0]*p[0]+q[1]*p[1])+q[2]*p[2])-p[3])
        else:
            distance = sum(point[k]*plane[k] for k in range(3))-plane[3]
        root = front if distance >= 0 else back
    return root


class CanonicalPointTests(unittest.TestCase):
    def test_diagonal_seams_nextafter_and_source_height(self):
        tree = build_point_tree(Land(), [[0, 0], [32, 32]])
        for x in [0., 8., 16., np.nextafter(np.float32(32), np.float32(0))]:
            for y in [0., float(x), float(np.nextafter(np.float32(x), np.float32(32))), 24.]:
                if y >= 32:
                    continue
                z = -4+.25*x+.25*y if y <= x else -4-.25*x+.75*y
                for native in (False, True):
                    self.assertEqual(contents(tree, [x, y, z-TRACE_EPSILON], native), SOLID)
                    self.assertEqual(contents(tree, [x, y, z+TRACE_EPSILON], native), EMPTY)
        self.assertLess(tree[3]['maximum_native_float32_vertical_error_bound'], TRACE_EPSILON)

    def test_ridge_and_valley_minmax_over_complete_tile(self):
        for corner_d in (-12., 20.):
            class Tile(Land):
                def triangles(self, bounds):
                    return iter([[[0, 0, -4], [32, 0, 4], [32, 32, 12]],
                                 [[0, 0, -4], [32, 32, 12], [0, 32, corner_d]]])
            tree = build_point_tree(Tile(), [[0, 0], [32, 32]])
            for x in np.linspace(0, 31.999, 13):
                for y in np.linspace(0, 31.999, 13):
                    if y <= x:
                        z = -4+.25*x+.25*y
                    else:
                        z = -4+(12-corner_d)*x/32+(corner_d+4)*y/32
                    for native in (False, True):
                        self.assertEqual(contents(tree, [x, y, z-TRACE_EPSILON], native), SOLID)
                        self.assertEqual(contents(tree, [x, y, z+TRACE_EPSILON], native), EMPTY)

    def test_unrepresentable_native_precision_blocks(self):
        class Distant(Land):
            def triangles(self, bounds):
                return iter([[[x+2**20, y, z] for x, y, z in q]
                             for q in super().triangles(bounds)])
        with self.assertRaisesRegex(ValueError, 'precision'):
            build_point_tree(Distant(), [[2**20, 0], [2**20+32, 32]])

    def test_half_open_envelope_bottom_and_exact_flat_roof(self):
        class Flat(Land):
            def triangles(self, bounds):
                return iter([[[0, 0, -4], [32, 0, -4], [32, 32, -4]],
                             [[0, 0, -4], [32, 32, -4], [0, 32, -4]]])
        tree = build_point_tree(Flat(), [[0, 0], [32, 32]], bottom=-20)
        self.assertEqual(contents(tree, [0, 0, -20]), SOLID)
        self.assertEqual(contents(tree, [0, 0, -4]), EMPTY)
        self.assertEqual(contents(tree, [0, 0, np.nextafter(-4., -20.)]), SOLID)
        self.assertEqual(contents(tree, [32, 0, -10]), EMPTY)
        self.assertEqual(contents(tree, [0, 32, -10]), EMPTY)
        self.assertEqual(contents(tree, [-1, 0, -10]), EMPTY)
        self.assertEqual(contents(tree, [0, 0, -21]), EMPTY)

    def test_forward_dag_and_repeat_determinism(self):
        a = build_point_tree(Land(), [[0, 0], [32, 32]])
        b = build_point_tree(Land(), [[0, 0], [32, 32]])
        self.assertEqual(a, b)
        for parent, (_, front, back) in enumerate(a[1]):
            for child in (front, back):
                self.assertTrue(child in (EMPTY, SOLID) or child > parent)

    def test_native_node_limit_blocks_large_unshared_surface(self):
        class Many(Land):
            def triangles(self, bounds):
                def point(x, y):
                    z = ((x*2654435761 ^ y*805459861) & 1023)/1024
                    return [x*32, y*32, z]
                for y in range(128):
                    for x in range(128):
                        a, b, c, d = point(x, y), point(x+1, y), point(x+1, y+1), point(x, y+1)
                        yield [a, b, c]
                        yield [a, c, d]
        with self.assertRaisesRegex(ValueError, 'node index limit'):
            build_point_tree(Many(), [[0, 0], [4096, 4096]])

    def test_invalid_bounds_origin_and_bottom(self):
        for bounds in ([[0, 0], [31, 32]], [[0, 0], [float('inf'), 32]], [[0, 0], [0, 32]]):
            with self.assertRaises(ValueError):
                build_point_tree(Land(), bounds)
        class Shifted(Land):
            origin = [.5, 0, 0]
        with self.assertRaisesRegex(ValueError, 'lattice'):
            build_point_tree(Shifted(), [[0, 0], [32, 32]])
        with self.assertRaisesRegex(ValueError, 'bottom'):
            build_point_tree(Land(), [[0, 0], [32, 32]], bottom=-4)

    def test_missing_duplicate_and_wrong_diagonal_rejected(self):
        with self.assertRaisesRegex(ValueError, 'coverage'):
            build_point_tree(Land(), [[0, 0], [64, 32]])
        class Duplicate(Land):
            def triangles(self, bounds):
                q = next(super().triangles(bounds))
                return iter([q, q])
        with self.assertRaisesRegex(ValueError, 'diagonal'):
            build_point_tree(Duplicate(), [[0, 0], [32, 32]])

    def test_discontinuous_grid_rejected(self):
        class Broken(Land):
            def triangles(self, bounds):
                q = list(super().triangles(bounds))
                q[1][0][2] += 1
                return iter(q)
        with self.assertRaisesRegex(ValueError, 'Discontinuous'):
            build_point_tree(Broken(), [[0, 0], [32, 32]])


if __name__ == '__main__':
    unittest.main()
