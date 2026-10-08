"""Synthetic checks for --texinfo-snap and --scenery-reduce; no game data."""
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
READY = all(importlib.util.find_spec(name) for name in ("numpy", "scipy"))
SIMPLIFY = READY and importlib.util.find_spec("fast_simplification") is not None
if READY:
    import numpy as np
    from mesh_geometry import mapping_deviation, surface_polygons
    import scenery_reduce


def grid_mesh(n=8, size=256., uv=lambda x, y: (x/128., y/128.), noise=0., shift=None, seed=1):
    """Planar n x n quad grid in source units (z=0) with per-triangle UVs."""
    rng = np.random.default_rng(seed)
    v = []; f = []
    step = size/n
    for i in range(n):
        for j in range(n):
            quad = [(i*step, j*step), ((i+1)*step, j*step), ((i+1)*step, (j+1)*step), (i*step, (j+1)*step)]
            for tri in ((0, 1, 2), (0, 2, 3)):
                k = len(v)
                du = rng.uniform(-noise, noise, 2) if noise else np.zeros(2)
                extra = np.zeros(2) if shift is None else np.array(shift(i, j))
                for c in tri:
                    x, y = quad[c]
                    v.append([x, y, 0., *(np.array(uv(x, y))+du+extra)])
                f.append([k, k+1, k+2, 0])
    return np.array(v), np.array(f)


@unittest.skipUnless(READY, "numpy/scipy required")
class TexinfoSnapTests(unittest.TestCase):
    def test_options_are_off_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(scenery_reduce.texinfo_snap())
            self.assertIsNone(scenery_reduce.scenery_reduce())
        with mock.patch.dict(os.environ, {'AMIWIND_TEXINFO_SNAP': '1/16', 'AMIWIND_SCENERY_REDUCE': '0.5'}):
            self.assertEqual(scenery_reduce.texinfo_snap(), 1/16)
            self.assertEqual(scenery_reduce.scenery_reduce(), (0.5, 1/8))

    def test_deviation_is_exact_at_vertices_and_ignores_whole_repeats(self):
        p = np.array([[0., 0, 0], [10, 0, 0], [0, 10, 0]])
        ax = np.array([[.1, 0], [0, .1], [0, 0]]); off = np.array([.2, .3])
        self.assertAlmostEqual(mapping_deviation(p, ax, off, ax, off+[3, -2]), 0)
        self.assertAlmostEqual(mapping_deviation(p, ax, off, ax+[[.001, 0], [0, 0], [0, 0]], off), .01)
        stack = mapping_deviation(p, ax, off, np.array([ax, ax]), np.array([off, off+.5]))
        self.assertEqual(stack.shape, (2,))
        self.assertAlmostEqual(stack[1], .5)

    def test_noisy_mappings_merge_into_one_face_within_tolerance(self):
        size = 64
        # Noise up to 1/100 texel and whole-texture shifts on some triangles.
        v, f = grid_mesh(noise=.03/size, shift=lambda i, j: (1 if i > 3 else 0, -2 if j % 3 == 0 else 0))
        exact = surface_polygons(v, f)
        self.assertGreater(len(exact), 8)
        stats = {}
        snapped = surface_polygons(v, f, snap=(1/16)/size, stats=stats)
        self.assertEqual(len(snapped), 1)
        self.assertEqual(stats['mapping_clusters'], 1)
        self.assertLessEqual(stats['max_deviation']*size, 1/16)
        poly, material, axes, off, normal = snapped[0]
        self.assertEqual(len(poly), 4)
        # Every source vertex keeps its texels (modulo repeats) within tolerance.
        for face in f:
            p = v[face[:3], :3]*.25
            uv = v[face[:3], 3:5]
            d = p@axes+off-uv
            d -= np.round(d.mean(axis=0))
            self.assertLessEqual(np.abs(d).max()*size, 1/16+1e-9)

    def test_distinct_mappings_stay_separate(self):
        size = 64
        # Half the grid is offset by one whole texel: never within 1/16.
        v, f = grid_mesh(shift=lambda i, j: (1/size if i >= 4 else 0, 0))
        snapped = surface_polygons(v, f, snap=(1/16)/size)
        self.assertEqual(len(snapped), 2)
        self.assertEqual(len({tuple(np.round(s[3], 6)) for s in snapped}), 2)

    def test_projected_mapping_is_shared_across_planes(self):
        # A folded strip textured by one planar projection (u from x, v
        # from y): one texinfo can serve both planes exactly.
        pts = np.array([[0, 0, 0], [64, 0, 0], [64, 64, 0], [0, 64, 0],
                        [64, 0, 0], [128, 0, 40], [128, 64, 40], [64, 64, 0]], float)
        v = np.column_stack((pts, pts[:, 0]/128., pts[:, 1]/128.))
        f = np.array([[0, 1, 2, 0], [0, 2, 3, 0], [4, 5, 6, 0], [4, 6, 7, 0]])
        stats = {}
        out = surface_polygons(v, f, snap=(1/16)/32, stats=stats)
        self.assertEqual(stats['mapping_clusters'], 1)
        self.assertEqual(len(out), 2)
        np.testing.assert_array_equal(out[0][2], out[1][2])
        for poly, _, axes, off, _ in out:
            uv = poly@axes+off
            self.assertTrue(np.allclose(uv[:, 0], poly[:, 0]*4/128.))
        self.assertEqual(len(surface_polygons(v, f)), 2)

    def test_mip_factor_follows_engine_thresholds(self):
        from prepare_mesh_bsp import mipadjust
        self.assertEqual(mipadjust(np.array([[.3, 0], [0, .3], [0, 0]])), 4)
        self.assertEqual(mipadjust(np.array([[.4, 0], [0, .4], [0, 0]])), 3)
        self.assertEqual(mipadjust(np.array([[.9, 0], [0, .9], [0, 0]])), 2)
        self.assertEqual(mipadjust(np.array([[.9, 0], [0, .9], [.7, 0]])), 1)

    def test_snap_planes_survive_collinear_leading_vertices(self):
        # A merged wall polygon may start with three collinear vertices.
        from prepare_mesh_bsp import _prepare_placement
        poly = np.array([[10., 0, 16], [10, 0, 0], [10, 0, -16], [10, 20, -16], [10, 20, 16]])
        axes = np.array([[0, 0], [1/64., 0], [0, -1/64.]]); off = np.zeros(2)
        data = (np.zeros((3, 5)), np.zeros((1, 4), int), [(poly, 0, axes, off, np.array([1., 0, 0]))], [], {})
        ref = {'position': [0., 0, 0], 'rotation_radians': [0., 0, 0], 'scale': 1., 'number': 1}
        with mock.patch.dict(os.environ, {'AMIWIND_TEXINFO_SNAP': '1/16'}):
            surfaces, _, _, _ = _prepare_placement((ref, data, 32, [0., 0], None, False))
        q, n = surfaces[0][0], surfaces[0][1]
        np.testing.assert_allclose(abs(n), [1, 0, 0], atol=1e-9)
        self.assertLess(np.abs(q@n-n@q[0]).max(), 1e-9)

    def test_default_path_is_unchanged(self):
        v, f = grid_mesh()
        a = surface_polygons(v, f)
        b = surface_polygons(v, f, snap=None)
        self.assertEqual(len(a), len(b))
        for x, y in zip(a, b):
            np.testing.assert_array_equal(x[0], y[0])


def curved_mesh(n=24, radius=200.):
    """Open cylinder patch with one continuous UV chart (source units)."""
    v = []; f = []
    for i in range(n):
        for j in range(n):
            def point(a, b):
                t = a/n*np.pi/2; z = b/n*256
                return [radius*np.cos(t), radius*np.sin(t), z, a/n, b/n]
            quad = [point(i, j), point(i+1, j), point(i+1, j+1), point(i, j+1)]
            for tri in ((0, 1, 2), (0, 2, 3)):
                k = len(v); v.extend(quad[c] for c in tri); f.append([k, k+1, k+2, 0])
    return np.array(v, float), np.array(f)


@unittest.skipUnless(SIMPLIFY, "fast_simplification required")
class SceneryReduceTests(unittest.TestCase):
    def test_flat_chart_is_reduced_with_locked_border(self):
        v, f = grid_mesh(n=10)
        nv, nf, details = scenery_reduce.reduce_scenery(v, f, .25, (1/16)/64)
        self.assertLess(len(nf), len(f)//2)
        self.assertLessEqual(details['max_surface_distance'], .25)
        self.assertLessEqual(details['max_uv_deviation'], (1/16)/64)
        border = {tuple(np.round(p, 3)) for p in v[:, :2] if p[0] in (0, 256) or p[1] in (0, 256)}
        kept = {tuple(np.round(p, 3)) for p in nv[nf[:, :3].reshape(-1), :2]}
        self.assertTrue(border <= kept)

    def test_error_bound_holds_on_curved_chart(self):
        v, f = curved_mesh()
        nv, nf, details = scenery_reduce.reduce_scenery(v, f, .5, (1/8)/64)
        self.assertLessEqual(details['max_surface_distance'], .5)
        self.assertLess(len(nf), len(f))
        # A tighter bound keeps more triangles.
        _, tight, _ = scenery_reduce.reduce_scenery(v, f, .05, (1/8)/64)
        self.assertGreaterEqual(len(tight), len(nf))

    def test_uv_seam_vertices_are_locked(self):
        v, f = grid_mesh(n=10, shift=lambda i, j: (.5 if i >= 5 else 0, 0))
        nv, nf, details = scenery_reduce.reduce_scenery(v, f, .25, (1/16)/64)
        self.assertEqual(details['charts'], 2)
        seam = {(128., y) for y in np.round(np.linspace(0, 256, 11), 3)}
        kept = {tuple(np.round(p, 3)) for p in nv[nf[:, :3].reshape(-1), :2]}
        self.assertTrue(seam <= kept)

    def test_small_or_ineligible_meshes_are_untouched(self):
        v, f = grid_mesh(n=1)
        nv, nf, details = scenery_reduce.reduce_scenery(v, f, 1., 1.)
        np.testing.assert_array_equal(nf, f)
        self.assertFalse(scenery_reduce.eligible({'ratio': .5}))
        self.assertFalse(scenery_reduce.eligible({'flatten': {}}))
        self.assertTrue(scenery_reduce.eligible({'texture_size': 64}))
        self.assertTrue(scenery_reduce.eligible({'ratio': 1., 'texture_size': 32}))


if __name__ == "__main__":
    unittest.main()
