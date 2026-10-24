# SPDX-License-Identifier: GPL-3.0-only
"""The three Vivec room residents the v0.0.48 dev2 actor ground check failed (ROOM-PYLON-ROOF-48,
ACTOR-BAKE-CENTRE-SEAM-48).

- A convex piece of one flat floor triangle and a short wall at its edge (ex_stronghold_pylon01's top, where the
  Grand Inquisitor and Tamira Vian stand in the Ministry of Truth's Hall of Processing) has a hull that slopes up to
  the wall's height over the floor; the centre-only closure measure of collision_parts sees none of it. With the room
  roof rule (a listed exterior mesh in a room) the piece becomes its authored plates and a resident stands on the floor.
- An actor placed exactly on the shared edge of two floor pieces (Bradil Elarven, x 4160 on the 256-unit grid of the
  St. Delyn Glassworker's Hall) finds support for the bake from the pieces on either side; every placement whose centre
  has support is fitted exactly as before."""
import json
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

from mesh_geometry import collision_parts, collision_pieces, piece_roof  # noqa: E402
from player_hull import STEP_HEIGHT  # noqa: E402


def pylon_top():
    """Morrowind units: a floor triangle at z 320 reaching 3840 units from a 256-wide, 64-high wall on its y = -1920
    edge, one connected piece (the shape of ex_stronghold_pylon01's collision piece, 0.25 converter scale)."""
    v = np.array([[-128, -1920, 320], [128, -1920, 320], [640, 1920, 320],
                  [-128, -1920, 384], [128, -1920, 384]], float)
    f = np.array([[0, 1, 2, 0], [3, 4, 1, 0], [0, 3, 1, 0]])
    return np.hstack((v, np.zeros((len(v), 2)))), f


def inside(pieces, point):
    return any(np.max(hull.equations[:, :3] @ point + hull.equations[:, 3]) < 0 for _, hull, _, _ in pieces)


class RoomRoofTests(unittest.TestCase):
    FEET = np.array([0., -400., 80.42])   # feet 0.42 over the floor, 20 units from the wall (converter units)

    def test_convex_piece_roofs_the_floor_unseen_by_the_closure_measure(self):
        v, f = pylon_top()
        parts = collision_parts(v, f, 2)
        self.assertEqual(len(parts), 1)
        self.assertLessEqual(parts[0][3], 2)                 # the centre-only measure: nothing closed
        self.assertTrue(inside(parts, self.FEET))           # yet the feet are inside the hull
        tris = v[f[:, :3], :3] * .25
        roof = piece_roof(tris, parts[0][1])
        self.assertAlmostEqual(roof, 16., places=3)         # the wall's height, over the floor at the wall
        self.assertGreater(roof, STEP_HEIGHT)

    def test_rule_makes_the_roofed_piece_authored_plates(self):
        v, f = pylon_top()
        pieces, exact, note = collision_pieces(v, f, {'roof_collision_beyond': STEP_HEIGHT})
        self.assertFalse(inside(pieces, self.FEET))
        self.assertTrue(inside(pieces, np.array([0., -400., 80.1])))   # the floor plate under the feet
        self.assertEqual(exact, frozenset(range(len(pieces))))
        self.assertIn('over a walkable face of their own made authored plates', note)

    def test_without_the_rule_the_pieces_are_unchanged(self):
        v, f = pylon_top()
        before = collision_parts(v, f, 2)
        pieces, exact, note = collision_pieces(v, f, {})
        self.assertEqual([(p[2], p[3]) for p in pieces], [(p[2], p[3]) for p in before])
        self.assertEqual((exact, note), (False, None))

    def test_flat_box_has_no_roof(self):
        v = np.array([[x, y, z] for x in (0, 256) for y in (0, 256) for z in (0, 64)], float)
        f = np.array([[1, 3, 7, 0], [1, 7, 5, 0], [0, 4, 6, 0], [0, 6, 2, 0]])  # top (z 64) and bottom faces
        v = np.hstack((v, np.zeros((len(v), 2))))
        parts = collision_parts(v, f, 2)
        tris = v[f[:, :3], :3] * .25
        # (top and bottom are separate flat pieces: a flat piece is 0.2 units thick each way, collision_parts)
        self.assertLessEqual(max(piece_roof(tris[np.asarray(ids, int)], hull) for _, hull, ids, _ in parts), .2 + 1e-6)
        pieces, exact, note = collision_pieces(v, f, {'roof_collision_beyond': STEP_HEIGHT})
        self.assertEqual([(p[2], p[3]) for p in pieces], [(p[2], p[3]) for p in parts])
        self.assertIsNone(note)


class RoomRoofTableTests(unittest.TestCase):
    def test_table_lists_the_pylon_and_the_profile_takes_it(self):
        from prepare_area import interior_visual_profile, room_roof_meshes
        doc = json.loads((ROOT / 'config/collision-room-roof.json').read_text(encoding='utf-8'))
        self.assertEqual(doc['schema'], 'aw-collision-room-roof-1')
        self.assertIn('meshes/x/ex_stronghold_pylon01.nif', room_roof_meshes())
        self.assertFalse(set(doc['meshes']) & set(doc['measured_not_listed']['meshes']))
        self.assertTrue(all(m.startswith('meshes/x/') for m in doc['meshes'] + doc['measured_not_listed']['meshes']))
        self.assertEqual(interior_visual_profile('meshes/x/ex_stronghold_pylon01.nif'),
                         {'roof_collision_beyond': STEP_HEIGHT})
        # an unlisted exterior mesh keeps the assembly default; interior meshes keep their rule
        self.assertIsNone(interior_visual_profile('meshes/x/ex_vivec_h_01.nif'))
        self.assertNotIn('roof_collision_beyond', interior_visual_profile('meshes/i/in_v_s_int_corner_03.nif'))


class FakeScene:
    """floor(): supported at HEIGHTS[(x, y)] (rounded to 1/64), else unsupported."""

    def __init__(self, heights):
        self.heights = heights
        self.calls = []

    def floor(self, point, drop):
        self.calls.append(tuple(point))
        key = (round(point[0] * 64) / 64, round(point[1] * 64) / 64)
        if key in self.heights:
            return dict(point=list(point), status='supported', height=self.heights[key], reference=str(key),
                        normal=(0., 0., 1.), fraction=(point[2] - self.heights[key]) / drop)
        return dict(point=list(point), status='unsupported')


class CentreSeamTests(unittest.TestCase):
    def test_seam_takes_the_highest_support_beside_it(self):
        from actor_grounding import centre_support, CENTRE_SEAM_NUDGE as n
        scene = FakeScene({(1040 + n, 944.): 3824.2, (1040 - n, 944.): 3824.25})
        hit = centre_support(scene, (1040., 944., 3832.))
        self.assertEqual(hit['status'], 'supported')
        self.assertEqual(hit['height'], 3824.25)
        self.assertEqual(hit['point'], [1040., 944., 3840.])
        self.assertEqual(hit['seam_nudge'], n)

    def test_supported_centre_is_used_as_before(self):
        from actor_grounding import centre_support
        scene = FakeScene({(1040., 944.): 3824.2, (1040.0625, 944.): 3830.})
        hit = centre_support(scene, (1040., 944., 3832.))
        self.assertEqual((hit['height'], len(scene.calls)), (3824.2, 1))
        self.assertNotIn('seam_nudge', hit)

    def test_no_support_anywhere_stays_unsupported(self):
        from actor_grounding import centre_support
        hit = centre_support(FakeScene({}), (0., 0., 0.))
        self.assertEqual(hit['status'], 'unsupported')
        self.assertNotIn('seam_nudge', hit)

    def test_blocked_centre_is_not_nudged(self):
        from actor_grounding import centre_support

        class Blocked(FakeScene):
            def floor(self, point, drop):
                self.calls.append(tuple(point))
                return dict(point=list(point), status='blocked', height=point[2], fraction=0)
        scene = Blocked({})
        self.assertEqual(centre_support(scene, (0., 0., 0.))['status'], 'blocked')
        self.assertEqual(len(scene.calls), 1)


if __name__ == '__main__':
    unittest.main()
