"""The visible-tread rule in the shared collision layer (CHIM-STAIR-STEPS-SOLID-43).

A mesh with its own collision mesh (a RootCollisionNode) may run that collision over a visible flight much higher
than its nosings (ex_redoran_steps_02: a ramp 7 to 14 units over the treads), and a convex proxy of a curved deck
closes the space over it (ex_ropebridge_2048_01). Synthetic meshes only (source units; the converter scales by 0.25):
- a ramp plate over the visible flight, higher than a step over the treads: replaced by the visible flight's plates;
- a ramp through the nosings: left as it is (the player steps onto it);
- a sagging deck whose convex proxy closes the space over it: split until it follows the deck;
- collision under a table top (no standing room over the floor) and decorative ledges: left as they are;
- without the visible mesh, or with the stair rule off: unchanged.
"""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
READY = all(importlib.util.find_spec(name) for name in ('numpy', 'scipy'))
if READY:
    import numpy as np


def quad(v, f, corners):
    start = len(v)
    v.extend(corners)
    f.extend([[start, start + 1, start + 2, 0], [start, start + 2, start + 3, 0]])


def mesh(v, f):
    v = np.array(v, float)
    return np.hstack((v, np.zeros((len(v), 2)))), np.array(f)


def flight(rise=32., run=32., steps=6, width=160.):
    """Visible treads and risers along +x (source units: 8 x 8 steps after scaling)."""
    v, f = [], []
    for k in range(steps):
        x0, z0, z1 = k * run, k * rise, (k + 1) * rise
        quad(v, f, [(x0, 0, z0), (x0, width, z0), (x0, width, z1), (x0, 0, z1)])
        quad(v, f, [(x0, 0, z1), (x0 + run, 0, z1), (x0 + run, width, z1), (x0, width, z1)])
    return mesh(v, f)


def ramp(lift, rise=32., run=32., steps=6, width=160.):
    """A collision ramp from the foot of the flight to its top, LIFT source units over the nosing line."""
    v, f = [], []
    quad(v, f, [(0, 0, lift), (steps * run, 0, steps * rise + lift), (steps * run, width, steps * rise + lift),
                (0, width, lift)])
    return mesh(v, f)


def profile():
    return {'stair_plates': True, 'visible_treads': True, 'surface_collision_beyond': 8.5}


def over_treads(pieces, vis_v, vis_f):
    """Tread samples whose open column holds collision more than a step over the tread."""
    from mesh_geometry import visible_tread_samples, _stands_over
    samples = visible_tread_samples(vis_v, vis_f)
    return [k for k, piece in enumerate(pieces) if _stands_over(piece, samples)]


@unittest.skipUnless(READY, 'numpy and scipy required')
class VisibleTreadRuleTests(unittest.TestCase):
    def test_ramp_over_the_flight_becomes_the_visible_flight(self):
        from mesh_geometry import collision_pieces
        vv, vf = flight()
        cv, cf = ramp(lift=64.)       # 16 units over the nosings after scaling: higher than a step
        before, _, _ = collision_pieces(cv, cf, profile(), stairs='on')
        self.assertTrue(over_treads(before, vv, vf))
        pieces, exact, note = collision_pieces(cv, cf, profile(), stairs='on', visible=(vv, vf))
        self.assertEqual(over_treads(pieces, vv, vf), [])
        self.assertIn('visible treads', note)
        # exact standing bevels for the whole mesh (the CHIM model variants read the mesh-wide flag)
        self.assertIs(exact, True)
        # the flight is collision again: a tread centre has a plate under it within its thickness
        tops = [p[0][:, 2].max() for p in pieces]
        self.assertTrue(any(abs(t - 8.2) < .05 for t in tops))

    def test_ramp_through_the_nosings_stays(self):
        from mesh_geometry import collision_pieces
        vv, vf = flight()
        cv, cf = ramp(lift=0.)
        before, ea, na = collision_pieces(cv, cf, profile(), stairs='on')
        after, eb, nb = collision_pieces(cv, cf, profile(), stairs='on', visible=(vv, vf))
        self.assertEqual(len(before), len(after))
        for a, b in zip(before, after):
            np.testing.assert_array_equal(a[0], b[0])
        self.assertEqual(na, nb)

    def test_off_and_without_the_visible_mesh_unchanged(self):
        from mesh_geometry import collision_pieces
        vv, vf = flight()
        cv, cf = ramp(lift=64.)
        plain, _, _ = collision_pieces(cv, cf, profile(), stairs='on')
        off, _, _ = collision_pieces(cv, cf, profile(), stairs='off', visible=(vv, vf))
        offplain, _, _ = collision_pieces(cv, cf, profile(), stairs='off')
        self.assertEqual(len(off), len(offplain))
        self.assertEqual(len(plain), 1)
        # legacy open-world profiles (no stair_plates) never take the rule
        legacy, _, _ = collision_pieces(cv, cf, {'surface_collision_beyond': 8.5}, stairs='on', visible=(vv, vf))
        self.assertEqual(len(legacy), 1)
        # converters that do not opt in (rooms, the legacy towns) keep their collision
        rooms, _, _ = collision_pieces(cv, cf, {'stair_plates': True, 'surface_collision_beyond': 8.5}, stairs='on',
                                       visible=(vv, vf))
        self.assertEqual(len(rooms), 1)

    def test_sagging_deck_proxy_is_split_to_follow_the_deck(self):
        from mesh_geometry import collision_pieces
        # a visible flight of planks rising 6 units (1.5 scaled) each, then the collision: one curved deck under it
        v, f = [], []
        n, run, width = 24, 32., 96.
        heights = [abs(k - n / 2) * 6. for k in range(n + 1)]
        for k in range(n):
            x0, x1, z = k * run, (k + 1) * run, heights[k] + 0.
            quad(v, f, [(x0, 0, z), (x1, 0, z), (x1, width, z), (x0, width, z)])
            z2 = heights[k + 1]
            if abs(z2 - z) > 0:
                lo, hi = sorted((z, z2))
                quad(v, f, [(x1, 0, lo), (x1, width, lo), (x1, width, hi), (x1, 0, hi)])
        vv, vf = mesh(v, f)
        c, cf_ = [], []
        for k in range(n):
            x0, x1 = k * run, (k + 1) * run
            quad(c, cf_, [(x0, 0, heights[k]), (x1, 0, heights[k + 1]), (x1, width, heights[k + 1]), (x0, width, heights[k])])
        cv, cf = mesh(c, cf_)
        plain, _, _ = collision_pieces(cv, cf, profile(), stairs='on')
        self.assertTrue(over_treads(plain, vv, vf))
        pieces, exact, note = collision_pieces(cv, cf, profile(), stairs='on', visible=(vv, vf))
        self.assertEqual(over_treads(pieces, vv, vf), [])
        self.assertIn('split', note)

    def test_walkway_wedge_of_architecture_is_split(self):
        from mesh_geometry import collision_pieces
        # a walkway (z 0) in front of a wall 160 high, one mesh (collision = visible): the convex proxy of the walkway's
        # edge and the wall top invents a 59-degree slope, a wedge over the walkway higher than a step
        v, f = [], []
        quad(v, f, [(0, 0, 0), (96, 0, 0), (96, 160, 0), (0, 160, 0)])               # walkway
        quad(v, f, [(96, 0, 0), (96, 160, 0), (96, 160, 160), (96, 0, 160)])         # wall face
        quad(v, f, [(96, 0, 160), (96, 160, 160), (112, 160, 160), (112, 0, 160)])   # wall top
        quad(v, f, [(0, 0, 0), (0, 0, -16), (0, 160, -16), (0, 160, 0)])             # walkway edge
        vv, vf = mesh(v, f)
        prof = dict(profile(), collision_tolerance=40, visible_walkways=True)        # the proxy stays one piece
        plain, _, _ = collision_pieces(vv, vf, prof, stairs='on')
        self.assertEqual(len(plain), 1)
        pieces, exact, note = collision_pieces(vv, vf, prof, stairs='on', visible=(vv, vf))
        from mesh_geometry import visible_tread_samples, walkway_faces, _stands_over
        samples = visible_tread_samples(vv, vf, faces=walkway_faces(vv, vf))
        self.assertTrue(_stands_over(plain[0], samples, steep=False))
        self.assertFalse(any(_stands_over(p, samples, steep=False) for p in pieces))
        self.assertIn('split', note)
        # without visible_walkways only flights are checked: this mesh has none
        other = dict(prof); other.pop('visible_walkways')
        kept, _, _ = collision_pieces(vv, vf, other, stairs='on', visible=(vv, vf))
        self.assertEqual(len(kept), 1)

    def test_under_a_table_and_small_ledges_stay(self):
        from mesh_geometry import collision_pieces, flight_treads
        # a floor with three low ledges (risers under a unit: trim) and a table top 20 units over the floor
        v, f = [], []
        for k, z in enumerate((0., 2., 4.)):
            quad(v, f, [(k * 64, 0, z), (k * 64 + 64, 0, z), (k * 64 + 64, 64, z), (k * 64, 64, z)])
            quad(v, f, [(k * 64, 0, z - 2), (k * 64, 64, z - 2), (k * 64, 64, z), (k * 64, 0, z)])
        vv, vf = mesh(v, f)
        self.assertEqual(len(flight_treads(vv, vf)), 0)
        cv, cf = mesh([(0, 0, 0), (192, 0, 0), (192, 64, 80), (0, 64, 80)], [[0, 1, 2, 0], [0, 2, 3, 0]])
        prof = {'stair_plates': True, 'visible_treads': True}        # not architecture: flights only
        before, _, nb = collision_pieces(cv, cf, prof, stairs='on')
        after, _, na = collision_pieces(cv, cf, prof, stairs='on', visible=(vv, vf))
        self.assertEqual(len(before), len(after))
        self.assertEqual(nb, na)


if __name__ == '__main__':
    unittest.main()
