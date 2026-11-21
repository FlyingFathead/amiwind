# SPDX-License-Identifier: GPL-3.0-only
"""The outer-hull check of a reduced actor model (tools/outer_hull.py; MESH-SEAM-METHOD-62, MESH-REDUCTION-SEAMS-62,
ACTOR-PACK-GUAR-MESH-BROKEN-64): a reduced model keeps the original's outer measures (extent, girth, hull, no new
open edge, every seam closed). Synthetic shapes, no game files; the last class holds the rows the check measured on
the v0.0.67 release library (numbers only), so the verdict on those models is kept."""
import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import outer_hull as H  # noqa: E402

GEOMETRY = all(importlib.util.find_spec(n) for n in ('scipy',))


def tube(radius, z0, z1, around=16, rings=6, bottom=False, top=False, centre=(0.0, 0.0)):
    """(points, faces) of a tube along z, wound outward, with optional flat caps."""
    pts = []
    for k in range(rings + 1):
        z = z0 + (z1 - z0) * k / rings
        for i in range(around):
            a = 2 * np.pi * i / around
            pts.append((centre[0] + radius * np.cos(a), centre[1] + radius * np.sin(a), z))
    faces = []
    for k in range(rings):
        for i in range(around):
            a, b = k * around + i, k * around + (i + 1) % around
            c, d = a + around, b + around
            faces += [(a, b, d), (a, d, c)]
    if bottom:
        pts.append((centre[0], centre[1], z0))
        m = len(pts) - 1
        faces += [(m, (i + 1) % around, i) for i in range(around)]
    if top:
        pts.append((centre[0], centre[1], z1))
        m = len(pts) - 1
        base = rings * around
        faces += [(m, base + i, base + (i + 1) % around) for i in range(around)]
    return np.array(pts, float), np.array(faces, int)


def shape(name, pts, faces, part=0):
    return {'name': name, 'part': part, 'positions': np.asarray(pts, float)[None], 'faces': np.asarray(faces, int)}


def whole(shapes):
    """The source shapes as one reduced model would carry them (every triangle kept)."""
    return H.source_whole(shapes)


def body():
    """A body tube (closed at the bottom) and a head tube (closed at the top) that meet at the ring z = 8."""
    b = tube(3.0, 0.0, 8.0, bottom=True)
    h = tube(3.0, 8.0, 12.0, top=True)
    return [shape('Tri Body', *b), shape('Tri Head', *h)]


@unittest.skipUnless(GEOMETRY, 'scipy is needed for the surface and seam measures')
class MeasureTests(unittest.TestCase):
    def test_whole_model_keeps_every_measure(self):
        shapes = body()
        pts, faces = whole(shapes)
        row = H.measure(shapes, pts, faces)
        self.assertEqual(row['extent'], [1.0, 1.0, 1.0])
        self.assertEqual(row['open'], 0)
        self.assertEqual(row['seam_gap'], 0.0)
        self.assertGreaterEqual(row['hull'], 0.999)
        self.assertGreaterEqual(row['least_girth'], 0.99)
        self.assertEqual(H.problems(row), [])

    def test_a_part_pulled_off_a_welded_seam_fails(self):
        # the old behaviour on a creature: each shape reduced alone, its rim pulled back from the shape it shares the
        # seam with (the guar's plates apart, ACTOR-PACK-GUAR-MESH-BROKEN-64): new open edges in the welded hull
        shapes = body()
        pts, faces = whole(shapes)
        moved = pts.copy()
        head = np.arange(len(shapes[0]['positions'][0]), len(pts))
        moved[head, 2] += 1.5
        row = H.measure(shapes, moved, faces)
        self.assertGreater(row['open'], 0)
        self.assertIn('new open edge', '; '.join(H.problems(row)))

    def test_a_part_standing_apart_from_the_part_it_rests_on_fails(self):
        # an NPC's neck rests on the chest without sharing its points (a join, not a welded seam): pulled up off it,
        # the head and neck stand apart from the body (NPC-JOINT-GAPS-33); the open edges cannot see it, the join can
        torso = tube(4.0, 0.0, 8.0, bottom=True, top=True)
        neck = tube(1.5, 8.0, 10.0, around=10, rings=3, top=True)
        shapes = [shape('Tri Chest', *torso, part=3), shape('Tri Neck', *neck, part=2)]
        pts, faces = whole(shapes)
        self.assertEqual(H.problems(H.measure(shapes, pts, faces)), [])
        moved = pts.copy()
        moved[len(torso[0]):, 2] += 1.0
        row = H.measure(shapes, moved, faces)
        # the gap is read half a unit in from the rim (npc_seam_audit.INSET), so one intact side bounds it; the share
        # of the joins' length left open sees the whole rim pulled away
        self.assertGreater(row['seam_open'], H.SEAM_OPEN_MAX)
        self.assertEqual(row['seam_gap_at'], 'Tri Neck / Tri Chest')
        self.assertIn('seam open', '; '.join(H.problems(row)))

    def test_a_hole_in_the_hull_fails(self):
        shapes = body()
        pts, faces = whole(shapes)
        row = H.measure(shapes, pts, np.delete(faces, [10, 11, 26, 27], axis=0))
        self.assertGreater(row['open'], 0)
        self.assertTrue(any('new open edge' in p for p in H.problems(row)))

    def test_a_stick_limb_fails_on_its_girth(self):
        limb = [shape('Tri Arm', *tube(2.0, 0.0, 10.0, rings=8))]
        thin = tube(0.6, 0.0, 10.0, rings=8)
        row = H.measure(limb, thin[0], thin[1])
        self.assertLess(row['least_girth'], H.GIRTH_KEEP)
        self.assertTrue(any(p.startswith('girth under') for p in H.problems(row)))

    def test_a_narrowed_body_fails_on_its_extent(self):
        shapes = body()
        pts, faces = whole(shapes)
        narrow = pts * [0.9, 1.0, 1.0]
        row = H.measure(shapes, narrow, faces)
        self.assertAlmostEqual(row['extent'][0], 0.9, places=2)
        self.assertTrue(any(p.startswith('extent x') for p in H.problems(row)))

    def test_lost_surface_lowers_the_hull(self):
        shapes = body()
        pts, faces = whole(shapes)
        keep = faces[: len(faces) // 2]
        row = H.measure(shapes, pts, keep)
        self.assertLess(row['hull'], H.HULL_KEEP)


class LabelTests(unittest.TestCase):
    def test_face_label_takes_the_majority(self):
        labels = np.array(['a', 'b', 'b', 'c'], dtype=object)
        faces = np.array([[0, 1, 2], [0, 0, 3], [3, 1, 1], [0, 1, 3]])
        self.assertEqual(H._face_label(labels, faces).tolist(), ['b', 'a', 'b', 'a'])

    @unittest.skipUnless(GEOMETRY, 'scipy is needed for the cross-sections')
    def test_girth_reads_each_bone_on_its_own(self):
        arm_p, arm_f = tube(2.0, 0.0, 10.0, rings=8)
        leg_p, leg_f = tube(2.0, 0.0, 10.0, rings=8, centre=(20.0, 0.0))
        shapes = [shape('Tri Arm', arm_p, arm_f, 13), shape('Tri Leg', leg_p, leg_f, 21)]
        shapes[0]['bone_name'] = np.array(['bip01 r upperarm'] * len(arm_p), dtype=object)
        shapes[1]['bone_name'] = np.array(['bip01 r thigh'] * len(leg_p), dtype=object)
        groups = H.body_groups(shapes)
        self.assertEqual(sorted(groups), ['bip01 r thigh', 'bip01 r upperarm'])
        sp, sf = H.source_whole(shapes)
        thin_leg = leg_p.copy()
        thin_leg[:, :2] = (thin_leg[:, :2] - [20.0, 0.0]) * 0.25 + [20.0, 0.0]
        g = H.girth(sp, sf, np.concatenate((arm_p, thin_leg)), sf, groups)
        self.assertGreaterEqual(g['bip01 r upperarm'], 0.99)
        self.assertLess(g['bip01 r thigh'], 0.3)

    @unittest.skipUnless(GEOMETRY, 'scipy is needed for the cross-sections')
    def test_girth_does_not_depend_on_which_faces_carry_the_part(self):
        # a whole-model reduction may carry a limb on faces of a neighbouring shape: the cut reads the surface
        arm = [shape('Tri Arm', *tube(2.0, 0.0, 10.0, rings=8))]
        sp, sf = H.source_whole(arm)
        coarse = tube(2.0, 0.0, 10.0, around=8, rings=2)
        self.assertGreaterEqual(H.girth(sp, sf, coarse[0], coarse[1], H.creature_groups(arm))['Tri Arm'], 0.9)


class ReleaseLibraryRows(unittest.TestCase):
    """The rows tools/outer_hull.py measured on the v0.0.67 release build's library (the guar family, the Dagoth ash
    vampires' mesh, the Alit and residents of the NPC gallery the maintainer pictured): every one fails, the cliff
    racer (confirmed whole, CREATURE-RACER-MESH-SPIKE-58) passes. A change to the limits that let one of the broken
    rows pass, or failed the racer, fails here."""
    ROWS = {
        'r/guar.nif': {'extent': [1.0, 1.0, 0.99], 'girth': {'Tri Creature_Guar 1': 0.0, 'Tri Creature_Guar 5': 0.13},
                       'hull': 0.904, 'open': 134, 'seam_gap': 0.37, 'seam_open': 0.37, 'lost': []},
        'r/guar_withpack.nif': {'extent': [0.98, 1.0, 0.99], 'girth': {'Tri Feralalguar 1': 0.0}, 'hull': 0.696,
                                'open': 241, 'seam_gap': 0.0, 'seam_open': 0.0,
                                'lost': ['Tri Guar_tent 1 #2', 'Tri Feralalguar 17 #3']},
        'r/ascendedsleeper.nif': {'extent': [1.0, 0.96, 0.99], 'girth': {'Tri body 6': 0.0, 'Tri body 5': 0.3},
                                  'hull': 0.914, 'open': 133, 'seam_gap': 0.0, 'seam_open': 0.0, 'lost': []},
        'r/duskyalit.nif': {'extent': [1.01, 1.0, 0.96], 'girth': {'Tri DuskyAlit 9 #3': 0.48}, 'hull': 0.951,
                            'open': 161, 'seam_gap': 0.0, 'seam_open': 0.0, 'lost': []},
        'ten-tongues_weerhat': {'extent': [0.91, 0.87, 0.98], 'girth': {'bip01 r upperarm': 0.7, 'bip01 neck': 0.82},
                                'hull': 0.987, 'open': 0, 'seam_gap': 0.0, 'seam_open': 0.0, 'lost': []},
        'ah-meesei': {'extent': [0.95, 0.9, 0.99], 'girth': {'bip01 l forearm': 0.21, 'bip01 r upperarm': 0.24},
                      'hull': 0.994, 'open': 5, 'seam_gap': 0.76, 'seam_open': 0.87, 'lost': []},
        'fargoth': {'extent': [0.97, 1.02, 1.0], 'girth': {'bip01 l forearm': 0.23, 'bip01 r forearm': 0.23},
                    'hull': 0.998, 'open': 8, 'seam_gap': 0.0, 'seam_open': 0.0, 'lost': []},
    }
    RACER = {'extent': [1.0, 0.99, 1.0], 'girth': {'Tri CliffRacer 2': 0.87, 'Tri CliffRacer 1': 0.94}, 'hull': 1.0,
             'open': 0, 'seam_gap': 0.0, 'seam_open': 0.0, 'lost': []}

    def test_every_broken_row_fails(self):
        for key, row in self.ROWS.items():
            with self.subTest(model=key):
                self.assertTrue(H.problems(row), key)

    def test_the_whole_cliff_racer_passes(self):
        self.assertEqual(H.problems(self.RACER), [])


if __name__ == '__main__':
    unittest.main()
