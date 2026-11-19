# SPDX-License-Identifier: GPL-3.0-only
"""The room arrival check (tools/tp_arrivals.py, TP-BEING-TRIBUNAL-FALLS-THROUGH-67) and the rule it guards: a teleport
to a being in a room arrives as a door does, lifted over the being's feet, so the engine's arrival search
(arrival_spot.standing_spot = aw_scene.c standing_spot) stands the player on the being's floor. Handed the feet, the
search's first standing box stood in the floor and it took the next floor under the room: on the v0.0.67-dev1 image
1,302 of 3,623 being arrivals landed under their floor (103 of 281 in Tribunal, 'Ten-Tongues' Weerhat 64 units under
the pawnbroker's floor); lifted, none did (tools/tp_arrivals.py over that image's 6,182 room arrivals)."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import tp_arrivals as A  # noqa: E402
import tp_places_lut as T  # noqa: E402
from player_hull import MINS, MAXS  # noqa: E402
from town_interiors import FEET  # noqa: E402

SRC = ROOT / 'engine' / 'aga' / 'src'


class Slabs:
    """A room's collision as horizontal solid slabs (bottom, top), endless in x and y: the arrival_spot.Collision
    calls standing_spot makes (ground, solid, dry), for the standing box MINS..MAXS."""

    def __init__(self, *slabs):
        self.slabs = slabs

    def solid(self, p):
        low, high = p[2] + MINS[2], p[2] + MAXS[2]
        return any(low < top and high > bottom for bottom, top in self.slabs)

    def ground(self, p, depth):
        if self.solid(p):
            return None
        feet = p[2] + MINS[2]
        tops = [top for _, top in self.slabs if top <= feet and feet - top <= depth]
        return max(tops) - MINS[2] if tops else None

    def dry(self, p):
        return True


# the pawnbroker's floor: a 4-unit slab whose top is at -96, a cellar floor 64 under it (the room's numbers, rounded)
ROOM = Slabs((-100, -96), (-1000, -160))
FEET_Z = -96


class Rule(unittest.TestCase):
    def test_the_lift_is_a_door_arrivals(self):
        self.assertAlmostEqual(A.LIFT, FEET)
        self.assertAlmostEqual(A.LIFT, -MINS[2] + .25)

    def test_from_the_feet_the_search_lands_under_the_floor(self):
        got = A.judge(ROOM, (0, 0, FEET_Z), FEET_Z)
        self.assertEqual(got['verdict'], 'below-floor')
        self.assertAlmostEqual(got['floor'], -96)
        self.assertGreater(got['under'], 60)

    def test_lifted_the_search_stands_on_the_floor(self):
        got = A.judge(ROOM, (0, 0, FEET_Z + A.LIFT), FEET_Z)
        self.assertEqual(got['verdict'], 'on-floor')
        self.assertAlmostEqual(got['spot'][2] + MINS[2], -96 + .25, places=2)

    def test_a_step_down_beside_is_no_fall(self):
        # the search steps 16 units aside: a floor 8 under the being's (a stair step) is still on the floor
        self.assertEqual(A.judge(Slabs((-1000, -8)), (0, 0, A.LIFT), 0)['verdict'], 'on-floor')

    def test_no_floor_at_all_is_blocked(self):
        self.assertEqual(A.judge(Slabs(), (0, 0, A.LIFT), 0)['verdict'], 'blocked')


class Rows(unittest.TestCase):
    """The arrivals of a small image: a being row, a common kind's placements file, a room row and a door bank."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        id1 = cls.id1 = Path(cls.tmp.name)
        rows = [{'name': 'Mournhold, Pawnbroker (Tribunal) (interior)', 'x': 0, 'y': 0, 'z': 0, 'flags': T.F_ROOM,
                 'cells': 0, 'map': 'rpawn'},
                {'name': "'Ten-Tongues' Weerhat (Tribunal)", 'x': -7, 'y': 76, 'z': -91,
                 'flags': T.F_BEING | T.F_HAS_Z | T.F_ROOM, 'cells': 0, 'map': 'rpawn', 'id': 'Ten-Tongues_Weerhat'},
                {'name': 'Assassin (Tribunal)', 'x': 0, 'y': 0, 'z': 0, 'flags': T.F_BEING | T.F_NEAREST | T.F_HAS_Z,
                 'cells': 0, 'map': T.kind_file_name('Assassin (Tribunal)')},
                {'name': 'Seyda Neen', 'x': 1, 'y': 2, 'z': 3, 'flags': T.F_HAS_Z, 'cells': 1, 'map': ''}]
        (id1 / T.NAME).write_bytes(T.encode_table(rows))
        (id1 / T.KIND_DIR).mkdir()
        (id1 / T.KIND_DIR / (rows[2]['map'] + '.tpk')).write_bytes(T.encode_kind(
            [{'id': 'hels_assassin1', 'map': 'rpawn', 'x': 303, 'y': -1, 'z': -29},
             {'id': 'db_assassin1', 'map': '', 'x': 9000, 'y': 9000, 'z': 100}]))
        (id1 / 'doors-gbazaar.txt').write_text(
            'AWD3\ngbazaar rpawn 14 -4 -4 -4 4 4 4 10.0 20.0 -79.125 90.0\tMournhold, Pawnbroker\n'
            'gbazaar - 15 -4 -4 -4 4 4 4 1.0 2.0 3.0 0.0\tOutside\n', encoding='cp1252')
        cls.found = A.arrivals(id1)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_room_arrival_is_listed_with_its_layer(self):
        rows = self.found['rpawn']
        kinds = sorted((r['kind'], r['id']) for r in rows)
        self.assertEqual(kinds, [('being', 'Ten-Tongues_Weerhat'), ('being', 'hels_assassin1'), ('door', '14'),
                                 ('room', '')])
        self.assertEqual({r['layer'] for r in rows}, {'Tribunal'})
        self.assertEqual(list(self.found), ['rpawn'])          # outdoors (no map) and a way out ('-') are not rooms

    def test_points_are_kept_as_stored(self):
        by = {r['id']: r for r in self.found['rpawn']}
        self.assertEqual(by['Ten-Tongues_Weerhat']['point'], [-7, 76, -91])      # the feet: the engine lifts it
        self.assertEqual(by['hels_assassin1']['common'], T.kind_file_name('Assassin (Tribunal)'))
        self.assertEqual(by['14']['point'], [10.0, 20.0, -79.125])              # a door's arrival: stored lifted

    def test_read_kind(self):
        data = T.encode_kind([{'id': 'a', 'map': 'm', 'x': 1, 'y': -2, 'z': 3}])
        self.assertEqual(A.read_kind(data), [('a', 'm', 1, -2, 3)])
        with self.assertRaises(ValueError):
            A.read_kind(b'AWTP' + data[4:])


class Engine(unittest.TestCase):
    def test_the_being_teleport_lifts_its_room_arrival(self):
        text = (SRC / 'aw_tpplaces.c').read_text(encoding='utf-8')
        go = text[text.index('void AW_TpBeingGo('):text.index('static void reset_being(')]
        self.assertIn('AW_TpBeingArrival(point,p->v.mins[2],arrival);', go)
        self.assertIn('AW_SceneLoadRoom(r.map,arrival,0)', go)
        self.assertNotIn('AW_SceneLoadRoom(r.map,point', go)
        rules = (SRC / 'aw_listbox_rules.c').read_text(encoding='utf-8')
        self.assertIn('out[2]=feet[2]-box_bottom+.25f;', rules)



if __name__ == '__main__':
    unittest.main()
