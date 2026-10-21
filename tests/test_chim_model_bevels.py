# SPDX-License-Identifier: GPL-3.0-only
"""Edge bevels of CHIM model standing hulls (chim.bevels; CHIM-COMPILED-HULL-OVERFILL-46; build setting model_bevels).

Without edge bevels (prepare_mesh_bsp.standing_planes exact=False, the default) an expanded convex piece reaches past
the exact Minkowski sum with the standing box at its edges. The bevel tolerance adds exactly the bevels whose omission
reaches more than the tolerance past the exact expansion. Synthetic shapes, no game data.

The option is reached only through its own unit kinds: a default build's unit keys (tools/code_key.py) do not
contain its code, so adding it rebuilds nothing (the 30-minute rebuild goal).
"""
import shutil
import tempfile
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))

try:
    import numpy as np
    from scipy.spatial import ConvexHull
except ImportError:  # pragma: no cover - the gate image has both
    np = None


def rock(seed=46, radii=(40.0, 25.0, 18.0), n=24):
    rng = np.random.default_rng(seed)
    u = rng.normal(size=(n, 3))
    return u / np.linalg.norm(u, axis=1)[:, None] * np.array(radii)


def wedge():
    """A sharp ridge: two faces meeting at a narrow angle, where the bevel-less expansion overshoots most."""
    w = np.array([[-30, -2, 0], [30, -2, 0], [-30, 2, 0], [30, 2, 0], [-30, 0, 30], [30, 0, 30]], dtype=float)
    a, b = 0.6, 0.4          # turned off the axes, so the axial bounding planes do not cut its ridge
    rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    rx = np.array([[1, 0, 0], [0, np.cos(b), -np.sin(b)], [0, np.sin(b), np.cos(b)]])
    return w @ (rz @ rx).T


def solid(planes, pts):
    return np.all(pts @ planes[:, :3].T + planes[:, 3] < -1e-6, axis=1)


def depth_outside(exact, pts):
    """How far each point lies outside the exact expansion (largest plane distance)."""
    return (pts @ exact[:, :3].T + exact[:, 3]).max(axis=1)


@unittest.skipIf(np is None, 'numpy and scipy are required')
class ModelBevelTests(unittest.TestCase):
    def setUp(self):
        import prepare_mesh_bsp
        from chim import bevels
        self.M = prepare_mesh_bsp
        self.B = bevels

    def planes(self, points, exact=False):
        eq = np.unique(np.round(ConvexHull(points).equations, 5), axis=0)
        return np.asarray(self.M.standing_planes(points, eq, exact=exact))

    def sample(self, points, n=20000, seed=4):
        lo, hi = points.min(axis=0) - 25, points.max(axis=0) + 25
        return lo + np.random.default_rng(seed).random((n, 3)) * (hi - lo)

    def test_default_is_unchanged(self):
        pts = rock()
        before = self.planes(pts)
        original = self.M.standing_planes
        with self.B.bevel_tolerance(None):
            self.assertIs(self.M.standing_planes, original)
            self.assertTrue(np.array_equal(self.planes(pts), before))

    def test_without_bevels_the_hull_overfills_at_edges(self):
        for pts in (rock(), wedge()):
            ax, ex = self.planes(pts), self.planes(pts, exact=True)
            s = self.sample(pts)
            extra = solid(ax, s) & ~solid(ex, s)
            self.assertGreater(int(extra.sum()), 0)
            self.assertEqual(int((solid(ex, s) & ~solid(ax, s)).sum()), 0)   # never less solid

    def test_tolerance_zero_is_the_exact_solid_set(self):
        for pts in (rock(), wedge(), rock(seed=7, radii=(60.0, 10.0, 10.0))):
            ex = self.planes(pts, exact=True)
            with self.B.bevel_tolerance(0):
                t0 = self.planes(pts)
            s = self.sample(pts)
            self.assertTrue(np.array_equal(solid(t0, s), solid(ex, s)))

    def test_tolerance_bounds_the_overfill(self):
        for tol in (1.0, 2.0, 4.0):
            for pts in (rock(), wedge()):
                ex = self.planes(pts, exact=True)
                with self.B.bevel_tolerance(tol):
                    t = self.planes(pts)
                s = self.sample(pts)
                extra = solid(t, s) & ~solid(ex, s)
                if extra.any():
                    self.assertLessEqual(float(depth_outside(ex, s[extra]).max()), tol + 1e-3)
                self.assertEqual(int((solid(ex, s) & ~solid(t, s)).sum()), 0)
                self.assertLessEqual(len(t), len(self.planes(pts)) + len(ex))

    def test_fewer_planes_than_every_bevel(self):
        pts = rock()
        with self.B.bevel_tolerance(4):
            t4 = self.planes(pts)
        self.assertLess(len(t4), len(self.planes(pts)) + len(self.planes(pts, exact=True)))

    def test_setting_parse(self):
        model_bevels_mode = self.B.model_bevels_mode
        self.assertEqual(model_bevels_mode({}), 'profile')
        self.assertEqual(model_bevels_mode({'model_bevels': 'exact'}), 'exact')
        self.assertEqual(model_bevels_mode({'model_bevels': 'tol:2'}), 2.0)
        for bad in ('tol:-1', 'tol:x', 'bevels', 'tol:nan'):
            with self.assertRaises(ValueError):
                model_bevels_mode({'model_bevels': bad})

    def test_context_restores(self):
        original = self.M.standing_planes
        with self.B.bevel_tolerance(3):
            self.assertIsNot(self.M.standing_planes, original)
        self.assertIs(self.M.standing_planes, original)
        with self.assertRaises(ZeroDivisionError):
            with self.B.bevel_tolerance(2):
                1 / 0
        self.assertIs(self.M.standing_planes, original)


DEFAULT_KINDS = ('mesh', 'hull-surface', 'variant', 'texture', 'terrain', 'tiles', 'cut', 'ocean', 'pvs')


class DefaultUnitKeysTests(unittest.TestCase):
    """The default unit kinds' code keys do not hold chim/bevels.py: the same keys with and without the module."""

    def test_default_kinds_do_not_reach_the_bevel_module(self):
        import code_key
        from chim.units import CODE_ENTRIES
        for kind in DEFAULT_KINDS:
            with self.subTest(kind=kind):
                python, data, uncertain, units = code_key.reach(CODE_ENTRIES[kind], ROOT)
                self.assertFalse(uncertain, kind)
                self.assertNotIn('tools/chim/bevels.py', python)
        for kind in ('variant-bevels', 'tiles-bevels'):
            python = code_key.reach(CODE_ENTRIES[kind], ROOT)[0]
            self.assertIn('tools/chim/bevels.py', python)

    def test_default_keys_are_the_same_without_the_module(self):
        import code_key
        from chim.units import CODE_ENTRIES
        with tempfile.TemporaryDirectory(prefix='amiwind-bevel-keys-') as tmp:
            keys = {}
            for label, keep in (('with', True), ('without', False)):
                root = Path(tmp) / label
                for part in ('tools', 'src', 'config'):
                    shutil.copytree(ROOT / part, root / part, ignore=shutil.ignore_patterns('__pycache__'))
                if not keep:
                    (root / 'tools/chim/bevels.py').unlink()
                keys[label] = {kind: code_key.code_key(CODE_ENTRIES[kind], (), root)['digest'] for kind in DEFAULT_KINDS}
            self.assertEqual(keys['with'], keys['without'])

    def test_files_form_of_the_default_kinds_holds_no_bevel_code(self):
        from chim.units import TOOLS
        for kind in DEFAULT_KINDS:
            if kind in TOOLS:
                self.assertNotIn('tools/chim/bevels.py', TOOLS[kind])


if __name__ == '__main__':
    unittest.main()
