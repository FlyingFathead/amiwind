"""The dock guard's walk after the race form goes in two fixed legs (PIER-GUARD-WALKS-INTO-DOOR-65).

After the race form he walks to one point in front of the census office door, then steps aside to a post beside the door
and faces the sea, the pier and the ship. Before, he walked a straight line from wherever he met the player to his post;
from further down the pier that line ran into the door frame, and the blocked walk was tried again every 2 s, so he
pushed against the door for about half a minute. The points are measured from the built door table (doors-seyda.txt, the
row "seyda census 113893": box x 308.86..332.61, y -173.38..-149.62 in the dock map's units); this test keeps them clear
of that box and of the doorway the player walks through.
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src' / 'aw_opening.c'
DOOR_X = (308.86, 332.61)
DOOR_Y = (-173.38, -149.62)
HALF = 16.0   # the guard's and the player's half width


def constants():
    text = SRC.read_text(encoding='utf-8', errors='replace')
    found = dict(re.findall(r'#define AW_PIER_GUARD_(\w+) (-?[0-9.]+)f', text))
    return {k: float(v) for k, v in found.items()}, text


class PierGuardRoute(unittest.TestCase):
    def test_front_point_is_in_front_of_the_door(self):
        c, _ = constants()
        self.assertTrue(DOOR_X[0] < c['FRONT_X'] < DOOR_X[1], 'the front point is not before the door')
        self.assertLessEqual(c['FRONT_Y'] + HALF, DOOR_Y[0] - 8, 'the front point is not clear of the door face')

    def test_post_is_beside_the_door_and_leaves_the_doorway_clear(self):
        c, _ = constants()
        middle = (DOOR_X[0] + DOOR_X[1]) / 2
        # a player walking up the door's middle passes beside him: his box and the player's box side by side
        self.assertLessEqual(c['POST_X'] + HALF + HALF, middle - 2, 'the post stands in the way to the door')
        self.assertLess(c['POST_X'], DOOR_X[0], 'the post is not to the side of the door')
        self.assertLessEqual(c['POST_Y'] + HALF, DOOR_Y[0], 'the post is inside the wall')
        # a step aside: about the front point's distance from the wall, not a walk away from the door
        self.assertLess(abs(c['POST_Y'] - c['FRONT_Y']), HALF, 'the post is not a step aside from the front point')
        self.assertLess(abs(c['POST_X'] - c['FRONT_X']), 4 * HALF, 'the post is not beside the door')

    def test_second_walk_takes_both_legs(self):
        _, text = constants()
        route = text[text.index('static int dock_route('):]
        route = route[:route.index('\n}\n')]
        self.assertIn('AW_PIER_GUARD_FRONT_X', route)
        self.assertIn('AW_PIER_GUARD_POST_X', route)
        self.assertRegex(text, r'if\(result>0 && !post_leg\)\{[^}]*post_leg=1', 'the front leg does not hand over to the step aside')


if __name__ == '__main__':
    unittest.main()
