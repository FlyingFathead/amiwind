"""A convex collision piece keeps the surface it was built from (CHIM-VIVEC-DOCK-WALKWAY-43).

mesh_geometry.collision_parts builds each piece's hull from its extreme points along 14 fixed directions. On a deck
that runs level and then slopes down (ex_v_dock_01, the Vivec canton docks) those points are the deck's far corners
only: the hull's top cuts the bend as a chord, up to 19 units under the planks, and the player sinks into them. With
surface_loss (the CHIM model builder: profile hull_surface_loss = SURFACE_LOSS) a piece whose reduced hull leaves a
point of its walkable surface more than that outside gets points of that surface added until none is
(mesh_geometry.surface_hull). As first shipped the rule took the hull of ALL the points of such a piece, sides and
undersides included, and grew six v0.0.46-dev1 frames past the CHIM zone (CHIM-HULL-SURFACE-HEAP-46). Synthetic
meshes only (source units; the converter scales by 0.25):
- the bent deck: the reduced hull lies under the bend; with surface_loss no walkable point is more than that outside;
- a round rock (a sphere of 1,154 points): its walkable cap held within surface_loss, from a fraction of the hull
  planes of all its points (CHIM-HULL-SURFACE-HEAP-46);
- a plain box: unchanged either way (the reduction loses nothing there);
- the profile path (collision_pieces with hull_surface_loss) and the mode switch (AMIWIND_COLLISION_HULL_POINTS);
- the collision surface gate (chim.build.hull_surface_gate): the bent deck's reduced pieces fail it (walkable
  collision more than a step under them), its kept surface passes, mode extremes reports without failing;
- the measured table (config/collision-hull-surface.json) holds the Vivec dock.
"""
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
READY = all(importlib.util.find_spec(name) for name in ('numpy', 'scipy'))
if READY:
    import numpy as np


def box_mesh(corners):
    """A closed solid from 8 corners (bottom 4 then top 4, counter-clockwise from above)."""
    v = [list(c) + [0., 0.] for c in corners]
    q = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    f = []
    for a, b, c, d in q:
        f += [[a, b, c, 0], [a, c, d, 0]]
    return v, f


def bent_deck():
    """A deck 160 wide: level for 400 units, then sloping 200 units down over the next 400 (source units),
    8 units thick; one connected solid (two boxes sharing the bend's vertices)."""
    top = [(0., 0., 0.), (160., 0., 0.), (160., 400., 0.), (0., 400., 0.),
           (0., 800., -200.), (160., 800., -200.)]
    v = []
    for x, y, z in top:
        v.append([x, y, z - 8., 0., 0.])
    for x, y, z in top:
        v.append([x, y, z, 0., 0.])
    # bottom 0-5, top 6-11; level box 0,1,2,3 / 6,7,8,9; slope box 3,2,5,4 / 9,8,11,10
    f = []
    def quad(a, b, c, d):
        f.extend([[a, b, c, 0], [a, c, d, 0]])
    quad(6, 7, 8, 9); quad(9, 8, 11, 10)          # tops
    quad(0, 3, 2, 1); quad(3, 4, 5, 2)            # bottoms
    quad(0, 1, 7, 6); quad(4, 10, 11, 5)          # ends
    quad(1, 2, 8, 7); quad(2, 5, 11, 8)           # side x=160
    quad(0, 6, 9, 3); quad(3, 9, 10, 4)           # side x=0
    return np.array(v, float), np.array(f)


def sphere_mesh(radius, rings, segments):
    """A closed round solid (a smooth rock): rings x segments points plus the two poles, source units."""
    v = [[0., 0., radius, 0., 0.], [0., 0., -radius, 0., 0.]]
    for i in range(1, rings + 1):
        t = np.pi * i / (rings + 1)
        for j in range(segments):
            a = 2 * np.pi * j / segments
            v.append([radius * np.sin(t) * np.cos(a), radius * np.sin(t) * np.sin(a), radius * np.cos(t), 0., 0.])
    def at(i, j):
        return 2 + (i - 1) * segments + j % segments
    f = []
    for j in range(segments):
        f.append([0, at(1, j), at(1, j + 1), 0])
        f.append([1, at(rings, j + 1), at(rings, j), 0])
    for i in range(1, rings):
        for j in range(segments):
            f.append([at(i, j), at(i + 1, j), at(i + 1, j + 1), 0])
            f.append([at(i, j), at(i + 1, j + 1), at(i, j + 1), 0])
    return np.array(v, float), np.array(f)


def walkable(v, f):
    """The corners of the walkable faces (converter units): the surface the rule holds."""
    from mesh_geometry import walkable_samples
    return walkable_samples(v[f[:, :3], :3] * .25)


def outside(pieces, points):
    """The largest distance of any point outside every piece (0 when each point is in some piece)."""
    worst = 0.
    for p in points:
        best = min(float((p @ h.equations[:, :3].T + h.equations[:, 3]).max()) for _, h, _, _ in pieces)
        worst = max(worst, best)
    return worst


@unittest.skipUnless(READY, 'needs numpy and scipy')
class HullSurfaceLoss(unittest.TestCase):
    def test_bent_deck_reduced_hull_lies_under_the_bend(self):
        from mesh_geometry import collision_parts
        v, f = bent_deck()
        points = v[:, :3] * .25
        old = collision_parts(v, f)
        self.assertEqual(len(old), 1)
        # the extreme points miss the bend: its corners lie 10 units (40 source units) over the hull's top
        self.assertGreater(outside(old, points), 8.)

    def test_bent_deck_keeps_its_surface_with_surface_loss(self):
        from mesh_geometry import collision_parts, SURFACE_LOSS
        v, f = bent_deck()
        new = collision_parts(v, f, surface_loss=SURFACE_LOSS)
        self.assertLessEqual(outside(new, walkable(v, f)), SURFACE_LOSS)

    def test_round_rock_holds_its_walkable_cap_from_few_planes(self):
        from scipy.spatial import ConvexHull
        from mesh_geometry import collision_parts, surface_loss_depth, SURFACE_LOSS
        v, f = sphere_mesh(256., 24, 48)
        points = v[:, :3] * .25
        cap = walkable(v, f)
        old = collision_parts(v, f)
        self.assertEqual(len(old), 1)
        self.assertGreater(outside(old, cap), 4.)       # the 14 extreme points cut the cap deep
        new = collision_parts(v, f, surface_loss=SURFACE_LOSS)
        self.assertEqual(len(new), 1)
        self.assertLessEqual(outside(new, cap), SURFACE_LOSS)
        self.assertLessEqual(surface_loss_depth(v, f, new), SURFACE_LOSS)
        # the rule as first shipped: the hull of all 1,154 points (2,304 planes); the walkable cap needs a fraction
        whole = ConvexHull(np.unique(np.round(points * 16) / 16, axis=0))
        self.assertEqual(len(whole.equations), 2304)
        self.assertLess(len(new[0][1].equations), len(whole.equations) // 4)

    def test_rule_as_first_shipped(self):
        """surface_points 'all' (mode table-whole, and collision_pieces' last fallback): the hull of all a piece's
        points where its reduced hull leaves any point more than surface_loss outside."""
        from mesh_geometry import collision_parts, deep_walkable_triangles, SURFACE_LOSS
        from player_hull import STEP_HEIGHT
        v, f = sphere_mesh(256., 24, 48)
        whole = collision_parts(v, f, surface_loss=SURFACE_LOSS, surface_points='all')
        self.assertEqual(len(whole[0][1].equations), 2304)
        new = collision_parts(v, f, surface_loss=SURFACE_LOSS)
        self.assertLess(len(new[0][1].equations), 2304 // 4)
        # walkable faces more than half a unit over the 14 extreme points; none more than a step over the new hull
        self.assertTrue(deep_walkable_triangles(v, f, collision_parts(v, f), SURFACE_LOSS))
        self.assertEqual(deep_walkable_triangles(v, f, new, STEP_HEIGHT), set())

    def test_deep_walkable_faces_become_plates(self):
        """collision_pieces: walkable faces the pieces leave more than a step deep become authored plates with exact
        bevels (CHIM-HULL-SURFACE-HEAP-46: the stair rules' slanted-riser cut on ex_dae_ruin_entry)."""
        import mesh_geometry as MG
        from player_hull import STEP_HEIGHT
        v, f = bent_deck()
        profile = {'ratio': 1., 'texture_size': 32, 'stair_plates': True, 'hull_surface_loss': MG.SURFACE_LOSS}
        reduced = MG.collision_parts(v, f)
        with mock.patch.object(MG, '_collision_pieces_visible', return_value=(list(reduced), False, None)):
            pieces, exact, note = MG.collision_pieces(v, f, profile, stairs='on')
        self.assertGreater(len(pieces), len(reduced))
        self.assertEqual(exact, frozenset(range(len(reduced), len(pieces))))
        self.assertIn('authored plates', note)
        self.assertEqual(MG.deep_walkable_triangles(v, f, pieces, STEP_HEIGHT), set())

    def test_surface_hull_holds_only_the_held_points(self):
        from mesh_geometry import surface_hull, SURFACE_LOSS
        rng = np.random.default_rng(46)
        p = rng.normal(size=(2000, 3))
        p = p / np.linalg.norm(p, axis=1)[:, None] * 40.
        choice = np.unique(np.argmax(p @ np.vstack((np.eye(3), -np.eye(3))).T, axis=0))
        top = p[p[:, 2] > 30.]
        q, hull = surface_hull(p[choice], top, SURFACE_LOSS)
        d = p @ hull.equations[:, :3].T + hull.equations[:, 3]
        self.assertLessEqual(float(d[p[:, 2] > 30.].max()), SURFACE_LOSS)
        self.assertGreater(float(d.max()), SURFACE_LOSS)   # the sides are not held
        self.assertLess(len(q), len(top) // 2)
        # nothing held: the extreme points' hull
        q, hull = surface_hull(p[choice], np.zeros((0, 3)), SURFACE_LOSS)
        self.assertEqual(len(q), len(choice))

    def test_box_unchanged(self):
        from mesh_geometry import collision_parts, SURFACE_LOSS
        v, f = box_mesh([(0, 0, 0), (64, 0, 0), (64, 64, 0), (0, 64, 0),
                         (0, 0, 64), (64, 0, 64), (64, 64, 64), (0, 64, 64)])
        v, f = np.array(v, float), np.array(f)
        a = collision_parts(v, f)
        b = collision_parts(v, f, surface_loss=SURFACE_LOSS)
        self.assertEqual(len(a), len(b))
        for (pa, *_), (pb, *_) in zip(a, b):
            self.assertTrue(np.array_equal(pa, pb))

    def test_profile_hull_surface_loss(self):
        from mesh_geometry import collision_pieces, SURFACE_LOSS
        v, f = bent_deck()
        base = {'ratio': 1., 'texture_size': 32, 'stair_plates': True}
        old, _, _ = collision_pieces(v, f, base, stairs='on')
        new, _, _ = collision_pieces(v, f, dict(base, hull_surface_loss=SURFACE_LOSS), stairs='on')
        self.assertGreater(outside(old, v[:, :3] * .25), 8.)
        self.assertLessEqual(outside(new, v[:, :3] * .25), SURFACE_LOSS)

    def test_surface_loss_depth(self):
        from mesh_geometry import collision_parts, surface_loss_depth, SURFACE_LOSS
        from player_hull import STEP_HEIGHT
        v, f = bent_deck()
        self.assertGreater(surface_loss_depth(v, f, collision_parts(v, f)), STEP_HEIGHT)
        self.assertLessEqual(surface_loss_depth(v, f, collision_parts(v, f, surface_loss=SURFACE_LOSS)), SURFACE_LOSS)
        self.assertEqual(surface_loss_depth(v, f, []), 0.)

    def test_gate(self):
        import hashlib
        import tempfile
        from mesh_geometry import collision_parts, SURFACE_LOSS
        from mwad.scene import pack_geometry
        from chim.build import hull_surface_gate
        from chim.units import UnitCache
        v, f = bent_deck()
        packet = bytes(pack_geometry([list(map(float, p[:5])) + [255, 255, 255, 255] for p in v], f.tolist(), 1))
        model = {'source': 'meshes/x/test_deck.nif', 'offset': 0, 'bytes': len(packet),
                 'sha256': hashlib.sha256(packet).hexdigest()}
        def strip(pieces):
            return [(p, None, i, e) for p, _, i, e in pieces]
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / 'scenery.mwpak'
            archive.write_bytes(packet)
            old = {0: (v, f, [], strip(collision_parts(v, f)), {})}
            new = {0: (v, f, [], strip(collision_parts(v, f, surface_loss=SURFACE_LOSS)), {})}
            with self.assertRaises(ValueError) as caught:
                hull_surface_gate('test', [model], old, {0: 'old'}, archive, 'table', 1, UnitCache())
            self.assertIn('test_deck', str(caught.exception))
            self.assertIn('collision-hull-surface.json', str(caught.exception))
            self.assertEqual(hull_surface_gate('test', [model], new, {0: 'new'}, archive, 'table', 1, UnitCache()), [])
            self.assertEqual(len(hull_surface_gate('test', [model], old, {0: 'old2'}, archive, 'extremes', 1,
                                                   UnitCache())), 1)

    def test_table_holds_the_dock(self):
        from chim.build import hull_surface_table
        self.assertIn('meshes/x/ex_v_dock_01.nif', hull_surface_table())

    def test_mode_switch(self):
        from mesh_geometry_env import hull_points_mode, HULL_POINTS_VARIABLE
        with mock.patch.dict(os.environ, {HULL_POINTS_VARIABLE: ''}):
            self.assertEqual(hull_points_mode(), 'table')
        with mock.patch.dict(os.environ, {HULL_POINTS_VARIABLE: 'all'}):
            self.assertEqual(hull_points_mode(), 'all')
        with mock.patch.dict(os.environ, {HULL_POINTS_VARIABLE: 'extremes'}):
            self.assertEqual(hull_points_mode(), 'extremes')
        with mock.patch.dict(os.environ, {HULL_POINTS_VARIABLE: 'table-whole'}):
            self.assertEqual(hull_points_mode(), 'table-whole')
        with mock.patch.dict(os.environ, {HULL_POINTS_VARIABLE: 'bogus'}):
            with self.assertRaises(ValueError):
                hull_points_mode()


@unittest.skipUnless(READY, 'needs numpy and scipy')
class ScaleSnap(unittest.TestCase):
    """CHIM-HULL-SURFACE-HEAP-46: placements of a mesh without collision pieces take the nearest SCALE_SNAP step (one
    model for kelp at 1.20, 1.22 and 1.24); placements of colliding meshes keep their scale exactly."""

    def test_snap(self):
        from chim.build import snap_scales, SCALE_SNAP
        prepared = {0: (None, None, None, [], {}), 1: (None, None, None, ['piece'], {})}
        refs = [{'model_index': 0, 'scale': s} for s in (1.2, 1.22, 1.24, 0.01)] + [{'model_index': 1, 'scale': 1.22}]
        out = snap_scales(refs, prepared, SCALE_SNAP)
        self.assertEqual([r['scale'] for r in out], [1.2, 1.2, 1.2, SCALE_SNAP, 1.22])
        self.assertEqual(refs[1]['scale'], 1.22)                 # the input is not changed
        self.assertIs(snap_scales(refs, prepared, 0.), refs)

    def test_switch(self):
        from chim.build import scale_snap_step, SCALE_SNAP, SCALE_SNAP_VARIABLE
        with mock.patch.dict(os.environ, {SCALE_SNAP_VARIABLE: ''}):
            self.assertEqual(scale_snap_step(), SCALE_SNAP)
        with mock.patch.dict(os.environ, {SCALE_SNAP_VARIABLE: 'off'}):
            self.assertEqual(scale_snap_step(), 0.)
        with mock.patch.dict(os.environ, {SCALE_SNAP_VARIABLE: '0.05'}):
            self.assertEqual(scale_snap_step(), 0.05)
        with mock.patch.dict(os.environ, {SCALE_SNAP_VARIABLE: '2'}):
            with self.assertRaises(ValueError):
                scale_snap_step()


class HeaviestFrames(unittest.TestCase):
    """tools/chim_heaviest_frames.py: the frames closest to the zone and the cells to check a converter change on
    before it is merged (CHIM-HULL-SURFACE-HEAP-46)."""

    def test_frames_and_cells(self):
        from chim_heaviest_frames import heaviest, check_cells
        heap = {'frames': [{'frame': 'frames/x+17/y+04/frame.ccf', 'peak_bytes': 6200000, 'headroom_bytes': 42304},
                           {'frame': 'frames/x-07/y-04/frame.ccf', 'peak_bytes': 6000000, 'headroom_bytes': 242304},
                           {'frame': 'frames/x+00/y+00/frame.ccf', 'peak_bytes': 100000, 'headroom_bytes': 6142304}]}
        rows = heaviest(heap, 256 * 1024, 1)
        self.assertEqual([r[0] for r in rows], ['frames/x+17/y+04/frame.ccf', 'frames/x-07/y-04/frame.ccf'])
        regions = {'cells': {'17,4': {'kind': 'land'}, '18,4': {'kind': 'seabed'}, '-7,-4': {'kind': 'land'},
                             '0,0': {'kind': 'land'}}}
        self.assertEqual(check_cells(rows, regions), '-7,-4:l 17,4:l 18,4:s')
        self.assertEqual(len(heaviest(heap, 0, 3)), 3)


if __name__ == '__main__':
    unittest.main()
