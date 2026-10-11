# SPDX-License-Identifier: GPL-3.0-only
"""The three stair findings of the whole-city Vivec build, fixed at the shared layers.

STAIRS-VIVEC-ROOMS-JOINT-36: the Velothi stair pieces end each authored ramp with a 50-degree lip 2.9 units tall;
where two pieces meet, a standing box stepping up came down on the lip. mesh_geometry.plate_toes cuts such a toe
plate to a vertical step.
STAIRS-EBONHEART-CHIM-36: a flat authored wall plate around an arch became one convex piece that filled the
opening. mesh_geometry.collision_parts keeps a flat piece whose hull covers open area as authored plates.
VIVEC-TEMPLE-STAIRS-33: three triangles over the palace steps made a convex piece that invented a 67-degree
face (it closed more than the tolerance and could not be split); on meshes with stairs such a piece becomes
authored plates. The High Fane quarters' authored collision closes part of the visible flight's width, as in
the original; stair_walk.other_lines walks the flight along the other lines across the riser.
Synthetic meshes only.
"""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]
READY = all(importlib.util.find_spec(name) for name in ('numpy', 'scipy'))
if READY:
    import numpy as np


def mesh(quads, tris=()):
    """(v, f) in source units (x4) from quads/triangles given in quarter units, counter-clockwise from outside."""
    v, f = [], []
    for poly in list(quads) + list(tris):
        start = len(v)
        v.extend(poly)
        for i in range(1, len(poly) - 1):
            f.append([start, start + i, start + i + 1, 0])
    v = np.array(v, float) * 4
    return np.hstack((v, np.zeros((len(v), 2)))), np.array(f)


def velothi_piece(dx=0., dz=0.):
    """The authored collision of one stair piece (quarter units): a landing at the top, a 26.8-degree ramp down,
    a 50-degree toe 2.9 units tall at the foot (in_velothismall_stairs_01's shape, 64 long, 32 high)."""
    w = 29.

    def q(x0, z0, x1, z1):
        return [(x0 + dx, -w, z0 + dz), (x1 + dx, -w, z1 + dz), (x1 + dx, w, z1 + dz), (x0 + dx, w, z0 + dz)]
    return [q(-31.8, 32., -27.9, 32.), q(-27.9, 32., 29.8, 2.9), q(29.8, 2.9, 32.2, 0.)]


@unittest.skipUnless(READY, 'numpy and scipy required')
class ToeTests(unittest.TestCase):
    def test_a_toe_plate_becomes_a_vertical_step_at_its_top_edge(self):
        from mesh_geometry import collision_pieces
        v, f = mesh(velothi_piece())
        on, exact, note = collision_pieces(v, f, {'hollow_collision': True, 'exact_collision_bevels': True, 'stair_plates': True}, stairs='on')
        off, _, _ = collision_pieces(v, f, {'hollow_collision': True, 'exact_collision_bevels': True, 'stair_plates': True}, stairs='off')
        self.assertIn('steep toes cut to vertical steps', note)
        toe = [p for p, _, _, _ in on if p[:, 2].max() < 3.5 and p[:, 0].min() > 29]
        self.assertEqual(len(toe), 1)
        self.assertLess(np.ptp(toe[0][:, 0]), .41)                        # vertical
        self.assertLess(abs(float(toe[0][:, 0].mean()) - 29.8), .3)       # at the ramp's foot
        self.assertEqual(len(on), len(off))                               # one plate for one plate

    def test_two_chained_pieces_walk_up_with_the_rule_and_not_without(self):
        from test_stair_slanted_risers import _Hull
        from chim.models import BrushLumps, hull_pieces
        from mesh_geometry import collision_pieces
        from stair_walk import walk, MINS
        quads = velothi_piece() + velothi_piece(64., -32.)
        quads += [[(96., -40, -32.), (96., 40, -32.), (160., 40, -32.), (160., -40, -32.)]]      # floor below
        v, f = mesh(quads)
        results = {}
        for mode in ('on', 'off'):
            pieces, exact, _ = collision_pieces(v, f, {'hollow_collision': True, 'exact_collision_bevels': True, 'stair_plates': True}, stairs=mode)
            w = BrushLumps()
            nroot, croot = w.collider(hull_pieces(pieces), exact)
            lo = np.min([p.min(axis=0) for p, *_ in pieces], axis=0)
            hi = np.max([p.max(axis=0) for p, *_ in pieces], axis=0)
            scene = _Hull(w.finish(lo, hi, nroot, croot, 0, 0), 1)
            # up the lower piece's ramp, over the joint onto the upper piece
            start = (60., 0., -14. - MINS[2] + .25)
            results[mode] = walk(scene, start, (-1., 0.), 40.)['status']
        self.assertEqual(results['on'], 'walked')
        self.assertEqual(results['off'], 'blocked')


@unittest.skipUnless(READY, 'numpy and scipy required')
class PlateHoleTests(unittest.TestCase):
    def wall(self):
        # a wall plate 128 wide, 96 high, with a 48 x 64 opening at the bottom (an arch), in the plane y = 0
        def q(x0, z0, x1, z1):
            return [(x0, 0, z0), (x1, 0, z0), (x1, 0, z1), (x0, 0, z1)]
        return mesh([q(-64, 0, -24, 96), q(24, 0, 64, 96), q(-24, 64, 24, 96)])

    def test_a_flat_plate_around_an_opening_keeps_the_opening(self):
        from mesh_geometry import collision_parts
        v, f = self.wall()
        plates = []
        pieces = collision_parts(v, f, 2, plates=plates)
        self.assertTrue(plates)
        centre = np.array([0., 0., 20.])
        for p, hull, _, _ in pieces:
            self.assertGreater((hull.equations[:, :3] @ centre + hull.equations[:, 3]).max(), 0.)   # outside

    def test_without_the_plate_list_the_proxy_is_unchanged(self):
        # the older form (no plates collected) fills the opening: the mechanism of STAIRS-EBONHEART-CHIM-36
        from mesh_geometry import collision_parts
        v, f = self.wall()
        pieces = collision_parts(v, f, 2)
        centre = np.array([0., 0., 20.])
        self.assertTrue(any((h.equations[:, :3] @ centre + h.equations[:, 3]).max() <= 0. for _, h, _, _ in pieces))

    def test_collision_pieces_marks_the_plates_for_exact_bevels(self):
        from mesh_geometry import collision_pieces
        v, f = self.wall()
        pieces, exact, note = collision_pieces(v, f, {'stair_plates': True}, stairs='on')
        self.assertIn('authored plates where the convex proxy filled open space', note)
        self.assertTrue(exact)
        self.assertLessEqual(set(exact), set(range(len(pieces))))


    def test_plates_keep_exact_bevels_on_a_mesh_with_stairs(self):
        # the stair rule rebuilds every piece (vertical_risers); the plates must still be marked for exact
        # standing bevels (without them a thin tilted plate's axial standing hull grows over the flight: the
        # first whole-city build on the fix failed six Vivec palace steps, 'start in solid')
        from mesh_geometry import collision_pieces, stair_treads
        wall_v, wall_f = self.wall()

        def q(x0, x1, z0, z1, flat):
            return ([(x0, 0, z0), (x1, 0, z0), (x1, 30, z0), (x0, 30, z0)] if flat
                    else [(x0, 0, z0), (x0, 30, z0), (x0, 30, z1), (x0, 0, z1)])
        steps_v, steps_f = mesh([q(100, 110, 0, 0, True), q(110, 110, 0, 4, False), q(110, 120, 4, 4, True),
                                 q(120, 120, 4, 8, False), q(120, 130, 8, 8, True)])
        v = np.vstack((wall_v, steps_v)); f = np.vstack((wall_f, steps_f + [len(wall_v), len(wall_v), len(wall_v), 0]))
        self.assertTrue(len(stair_treads(v, f)))
        pieces, exact, note = collision_pieces(v, f, {'stair_plates': True}, stairs='on')
        self.assertIn('authored plates where the convex proxy filled open space', note)
        plates = {k for k, (p, *_) in enumerate(pieces) if np.ptp(p[:, 1]) < .41 and p[:, 0].max() <= 64.5}
        self.assertTrue(plates)
        self.assertTrue(exact is True or plates <= set(exact), (sorted(plates), exact))


@unittest.skipUnless(READY, 'numpy and scipy required')
class FillPlateTests(unittest.TestCase):
    def test_an_unsplittable_piece_that_closes_space_becomes_plates_only_with_fill_plates(self):
        from mesh_geometry import collision_parts
        # three connected triangles (never split: at most four); a tolerance below their closing depth makes the
        # piece one that closes more than the tolerance and cannot be split, as the palace steps' three
        # triangles at the build's tolerance 2 (4.96 units closed)
        v, f = mesh([], [[(0, 0, 0), (20, 0, -12), (0, 20, 0)], [(20, 0, -12), (40, 0, 0), (20, 20, -12)],
                         [(0, 20, 0), (20, 0, -12), (20, 20, -12)]])
        plates = []
        self.assertEqual(len(collision_parts(v, f, -.5, plates=plates)), 1)
        self.assertFalse(plates)
        filled = collision_parts(v, f, -.5, plates=plates, fill_plates=True)
        self.assertEqual(len(plates), len(filled))
        self.assertGreater(len(filled), 1)
        # at the build's tolerance the same open valley closes nothing and stays one convex piece
        self.assertEqual(len(collision_parts(v, f, 2, plates=[], fill_plates=True)), 1)


    def test_deep_fill_is_measured_before_the_plates(self):
        # the plates must not hide the fill that makes a mesh keep all its authored surfaces: with the fill
        # measured after plating, the Vivec palace stairs (ex_vivec_ps_01, 9.05 units closed) lost their authored
        # surfaces and six flight steps started in solid (first whole-city build on the fix)
        from unittest import mock
        import mesh_geometry
        v, f = PlateHoleTests.wall(self)
        real = mesh_geometry.collision_parts

        def parts(v_, f_, tolerance=2, plates=None, fill_plates=False):
            out = real(v_, f_, tolerance, plates=plates, fill_plates=fill_plates)
            # the plain proxy closes 9 units somewhere; the plated one shows none of it
            return [(p, h, ids, 9. if plates is None else 0.) for p, h, ids, _ in out]
        with mock.patch.object(mesh_geometry, 'collision_parts', parts):
            pieces, exact, note = mesh_geometry.collision_pieces(v, f, {'surface_collision_beyond': 8.5, 'stair_plates': True}, stairs='on')
        self.assertTrue(note.startswith('authored collision surfaces'), note)
        self.assertIs(exact, True)


@unittest.skipUnless(READY, 'numpy and scipy required')
class OtherLinesTests(unittest.TestCase):
    def rows(self, raw):
        import shutil
        import tempfile
        import stair_walk
        tmp = tempfile.mkdtemp(); self.addCleanup(lambda: shutil.rmtree(tmp))
        (Path(tmp) / 'maps').mkdir()
        path = Path(tmp) / 'maps' / 'room.bsp'
        path.write_bytes(raw)
        return [r for r in stair_walk.check_map((str(path), None, {}))[1] if r['kind'] == 'step']

    def test_a_flight_closed_on_half_its_width_passes_along_the_open_half(self):
        import stair_walk
        from test_stair_walk import build
        rows = self.rows(build(fill=True, fill_box=((-5, 0, 0), (40, 20, 30))))
        self.assertTrue(rows)
        self.assertFalse([r for r in rows if stair_walk._gating(r)])
        lined = [r for r in rows if 'line' in r]
        self.assertTrue(lined)
        self.assertTrue(all(r['line'] > 0 for r in lined))           # the open half (y 20..40)
        self.assertTrue(all(r['point'][1] == 20.0 for r in lined))   # the row keeps the riser's middle

    def test_a_flight_closed_on_its_whole_width_still_fails(self):
        import stair_walk
        from test_stair_walk import build
        self.assertTrue([r for r in self.rows(build(fill=True)) if stair_walk._gating(r)])

    def test_an_open_flight_keeps_its_rows(self):
        from test_stair_walk import build
        self.assertFalse([r for r in self.rows(build()) if 'line' in r or 'span' in r])


@unittest.skipUnless(READY, 'numpy and scipy required')
class LegacyMapsUnchangedTests(unittest.TestCase):
    """BUILD-FLORA-STAIR-PLATES-BUDGET-36: the stair-plate rules raised a legacy open-world map's clip nodes past the
    BSP limit (vf0779: 32,614 -> 33,172 > 32,767 aggregate, the world-flora stage failed). Only converters that
    opt in (stair_plates: CHIM models, rooms) take them; every other profile gets the classic proxies, unchanged."""

    def meshes(self):
        yield PlateHoleTests.wall(self)
        yield mesh(velothi_piece() + velothi_piece(64., -32.))
        yield mesh([], [[(0, 0, 0), (20, 0, -12), (0, 20, 0)], [(20, 0, -12), (40, 0, 0), (20, 20, -12)],
                        [(0, 20, 0), (20, 0, -12), (20, 20, -12)]])

    def test_without_the_opt_in_the_proxies_are_the_classic_ones(self):
        from mesh_geometry import collision_pieces, collision_pieces_classic
        for v, f in self.meshes():
            for profile in ({}, {'surface_collision_beyond': 8.5}, {'hollow_collision': True},
                            {'hollow_collision': True, 'exact_collision_bevels': True}):
                a = collision_pieces(v, f, profile, stairs='on')
                b = collision_pieces_classic(v, f, profile, stairs='on')
                self.assertEqual(len(a[0]), len(b[0]))
                self.assertTrue(all(np.array_equal(x[0], y[0]) for x, y in zip(a[0], b[0])))
                self.assertEqual((a[1], a[2]), (b[1], b[2]))

    def test_only_chim_models_and_rooms_opt_in(self):
        from prepare_area import interior_visual_profile
        from town_regions import town_model_profile, visual_profile
        self.assertTrue(interior_visual_profile('meshes/i/in_velothismall_stairs_01.nif')['stair_plates'])
        for source in ('meshes/x/ex_hlaalu_b_01.nif', 'meshes/x/ex_imp_wall_arch_01.nif', 'meshes/f/flora_tree_01.nif'):
            self.assertNotIn('stair_plates', visual_profile(source, 100))
            self.assertNotIn('stair_plates', town_model_profile({}, source, 100))
        text = (ROOT / 'tools' / 'chim' / 'build.py').read_text(encoding='utf-8')
        self.assertIn("profile['stair_plates'] = True", text)


if __name__ == '__main__':
    unittest.main()
