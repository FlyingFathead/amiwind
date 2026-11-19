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


def line_constants():
    """The pier's centre line of the fixed route (aw_opening.c AW_PIER_LINE_*, AW_PIER_END_T, AW_PIER_PLANK_T)."""
    text = SRC.read_text(encoding='utf-8', errors='replace')
    return {k: float(v) for k, v in re.findall(r'#define AW_PIER_(LINE_\w+|END_T|PLANK_T) (-?[0-9.]+)f', text)}


# PIER-GUARD-POST-STUCK-67: where the dock guard's centre may not be on the Seyda Neen pier, measured from the built
# world's own collision (the v0.0.67-dev2 world, 18 November 2026: hull 1 of every placed model on and beside the pier,
# tested where the engine tests it for his box -7.32 -7.12 0 .. 7.32 7.12 33.25, feet on the deck at 23.25, on a 1-unit
# grid within 45 units of the centre line; each region is a post or a group of them, already grown by his box). In the
# line's own units: T along the line from A (the dock end by the door) toward B (the plank end), L to its left (north
# side). The regions: the dock end's posts with the two pilings and the dry-stone wall's end (south), the railing and
# the dock end's posts (north), the posts in pairs at the middle of each dock piece, and the plank's end with the far
# dock end's posts.
POSTS = (   # (T from, T to, L from, L to)
    (-20.8, 32.9, -45.6, -19.1),
    (-9.8, 16.1, 19.6, 45.5),
    (54.9, 73.9, -38.2, -19.5), (54.9, 73.8, 19.1, 37.9),
    (118.3, 137.2, -37.6, -19.0), (118.2, 137.1, 19.7, 38.3),
    (181.4, 200.3, -37.7, -19.0), (181.4, 200.2, 19.7, 38.3),
    (246.0, 261.6, -38.2, 37.9),
)
MARGIN = 4.0   # the least room kept between his centre and a region (on the line itself it is 19)


def line_frame():
    c = line_constants()
    ax, ay, bx, by = c['LINE_AX'], c['LINE_AY'], c['LINE_BX'], c['LINE_BY']
    n = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
    u = ((bx - ax) / n, (by - ay) / n)
    return c, (ax, ay), u, (-u[1], u[0])


def to_line(p, a, u, v):
    dx, dy = p[0] - a[0], p[1] - a[1]
    return dx * u[0] + dy * u[1], dx * v[0] + dy * v[1]


def at_t(t, a, u):
    return a[0] + u[0] * t, a[1] + u[1] * t


def box_distance(t, l, box):
    dt = max(box[0] - t, 0.0, t - box[1])
    dl = max(box[2] - l, 0.0, l - box[3])
    return (dt * dt + dl * dl) ** 0.5


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
        # the earlier walk (dbg opening dock direct) keeps its hand-over; the fixed route never takes it
        self.assertRegex(text, r'if\(result>0 && !post_leg && !aw_dock_route_fixed\)\{[^}]*post_leg=1',
                         'the front leg does not hand over to the step aside')


class PierCentreLine(unittest.TestCase):
    """PIER-GUARD-POST-STUCK-67 (the maintainer's design, 18 November 2026): both of the dock guard's walks follow the
    pier's centre line, measured from the built world's collision, and only near the door go aside to his post; no
    detour. These keep the route's points clear of every measured post, with room to spare."""

    def route(self, start_t, second):
        """The fixed points as aw_opening.c AW_OpeningPierRoute makes them from a point of the line at START_T."""
        c, a, u, _ = line_frame()
        guard, _ = constants()
        t = min(max(start_t, c['END_T']), c['PLANK_T'])
        points = [at_t(t, a, u), at_t(c['END_T'] if second else c['PLANK_T'], a, u)]
        if second:
            points += [(guard['FRONT_X'], guard['FRONT_Y']), (guard['POST_X'], guard['POST_Y'])]
        return points

    def least_room(self, points):
        _, a, u, v = line_frame()
        least = None
        for (sx, sy), (ex, ey) in zip(points, points[1:]):
            steps = max(1, int(((ex - sx) ** 2 + (ey - sy) ** 2) ** 0.5 * 2))
            for i in range(steps + 1):
                t, l = to_line((sx + (ex - sx) * i / steps, sy + (ey - sy) * i / steps), a, u, v)
                room = min(box_distance(t, l, box) for box in POSTS)
                least = room if least is None or room < least else least
        return least

    def test_the_line_is_the_dock_pieces_line_and_his_placement_is_on_it(self):
        _, a, u, v = line_frame()
        # the dock pieces' centres (ex_de_docks_center 321248, 397560, 321249) lie on the line, 64 units apart
        for t_expected, piece in ((64.0, (438.2, -258.4)), (128.1, (492.1, -293.0)), (191.1, (545.1, -327.1))):
            t, l = to_line(piece, a, u, v)
            self.assertLess(abs(l), 0.5, piece)
            self.assertLess(abs(t - t_expected), 0.5, piece)
        t, l = to_line((366.5, -210.7), a, u, v)       # the original's placement of the dock guard (172852)
        self.assertLess(abs(l), 2.0)
        self.assertTrue(-32 < t < 0)

    def test_the_plank_point_is_the_originals_first_travel_point_on_the_line(self):
        c, a, u, v = line_frame()
        t, l = to_line(((-8914 + 11264) * .25, (-73093 + 71680) * .25), a, u, v)
        self.assertLess(abs(l), 1.5)
        self.assertLess(abs(t - c['PLANK_T']), 0.5)

    def test_the_deck_end_is_short_of_the_door(self):
        c, a, u, v = line_frame()
        guard, _ = constants()
        t, _ = to_line((guard['FRONT_X'], guard['FRONT_Y']), a, u, v)
        self.assertLess(t, c['END_T'], 'the front point is not past the end of the deck')
        self.assertGreaterEqual(c['END_T'], -40)

    def test_every_walk_keeps_clear_of_every_post(self):
        c = line_constants()
        for start in (c['END_T'], -22.1, 0.0, 64.0, 100.0, 191.0, 220.0, c['PLANK_T']):
            for second in (False, True):
                room = self.least_room(self.route(start, second))
                self.assertGreaterEqual(room, MARGIN, 'from T %.1f, %s walk: %.1f units of room'
                                        % (start, 'second' if second else 'first', room))

    def test_on_the_line_the_room_is_the_measured_nineteen_units(self):
        c = line_constants()
        _, a, u, _ = line_frame()
        room = self.least_room([at_t(c['END_T'], a, u), at_t(200.0, a, u)])
        self.assertGreaterEqual(room, 18.5)

    def test_the_old_straight_walk_from_the_pier_ran_along_the_posts(self):
        """Why: the earlier second walk went straight from where he met the player to the front point; from the plank
        end of the pier that line passes the south posts and the pilings with no room (the detour then decided on
        which side he went)."""
        guard, _ = constants()
        room = self.least_room([(560.0, -336.0), (guard['FRONT_X'], guard['FRONT_Y'])])
        self.assertLess(room, MARGIN)

    def test_the_engine_walks_the_route_without_a_detour(self):
        _, text = constants()
        route = text[text.index('static int dock_route('):]
        route = route[:route.index('\n}\n')]
        self.assertIn('AW_NavStartFixed(guard,', route)
        self.assertIn('AW_OpeningPierRoute(guard->v.origin,second,points)', route)
        nav = (ROOT / 'engine' / 'aga' / 'src' / 'aw_nav.c').read_text(encoding='utf-8', errors='replace')
        fixed = nav[nav.index('static int fixed_step('):]
        fixed = fixed[:fixed.index('\n}\n')]
        self.assertNotIn('AW_NavPlanDetour', fixed)
        self.assertNotIn('avoid[', fixed)
        self.assertIn('if(fixed_on)return fixed_step(dt);', nav)


class OpeningWalkCheck(unittest.TestCase):
    """The opening walk's early check (tools/opening_walk_check.py): the dock guard must reach his post (v0.0.66-dev1:
    he stood against the pier pylon at about 407 -268 and the walk still passed)."""

    def check(self, text):
        import sys
        sys.path.insert(0, str(ROOT / 'tools'))
        import opening_walk_check
        return opening_walk_check.check(text)

    def test_reached_post_passes(self):
        log = ('Dock guard at 560 -340 31 / leg 0 / route started 1 failed 0 done 0 / retries 0\n'
               'Dock guard at 286 -214 31 / leg 1 / route started 0 failed 0 done 1 / retries 0\n')
        self.assertEqual(self.check(log)[0], 0)

    def test_stuck_on_the_pylon_fails(self):
        line = 'Dock guard at 407 -268 39 / leg 1 / route started 0 failed 1 done 0 / retries %d\n'
        self.assertEqual(self.check(''.join(line % i for i in range(16)))[0], 1)

    def test_box_in_a_solid_fails_even_at_the_post(self):
        """PIER-GUARD-POST-STUCK-67: the walk's own check; a status line of an earlier engine reads as 0."""
        line = ('Dock guard at 286 -214 31 / leg 1 / route started 0 failed 0 done 1 / retries 0 / from the post 0 / '
                'box in solid %d / waits 0 / route fixed\n')
        self.assertEqual(self.check(line % 0)[0], 0)
        code, message = self.check(line % 4)
        self.assertEqual(code, 1)
        self.assertIn('inside a solid on 4 ticks', message)

    def test_status_prints_the_walks_check(self):
        text = (ROOT / 'engine' / 'aga' / 'src' / 'aw_opening.c').read_text(encoding='utf-8', errors='replace')
        status = text[text.index('void AW_OpeningDockStatus(void)'):]
        status = status[:status.index('\n}\n')]
        self.assertIn('" / from the post %ld / box in solid %ld / waits %ld / route %s / settled at the start %ld\\n"',
                      status)
        self.assertIn('AW_NavFixedSolid()', status)
        self.assertIn('AW_NavFixedSettled()', status)

    def test_fixed_walk_settles_a_box_that_starts_under_the_floor(self):
        """The journey's "box in solid 1" (2026-11-18): the one tick was the walk's start at his placement (366 -210 17,
        5.75 under the deck); the walk now runs the stuck search before its first tick and counts the lift apart."""
        text = (ROOT / 'engine' / 'aga' / 'src' / 'aw_nav.c').read_text(encoding='utf-8', errors='replace')
        start = text[text.index('int AW_NavStartFixed('):]
        start = start[:start.index('\n}\n')]
        self.assertIn('AW_ActorSettle(actor)', start)
        self.assertIn('fixed_settled++', start)
        self.assertLess(start.index('fixed_on=1'), start.index('AW_ActorSettle(actor)'))

    def test_no_status_line_is_its_own_failure(self):
        self.assertEqual(self.check('Opening 3 / dock -1\n')[0], 2)

    def test_status_prints_the_guard(self):
        text = (ROOT / 'engine' / 'aga' / 'src' / 'aw_intro.c').read_text(encoding='utf-8', errors='replace')
        self.assertIn('AW_OpeningDockStatus();', text[text.index('static void status(void)'):])

    def test_last_leg_sweeps_the_line(self):
        text = (ROOT / 'engine' / 'aga' / 'src' / 'aw_nav.c').read_text(encoding='utf-8', errors='replace')
        step = text[text.index('int AW_NavStep('):]
        self.assertIn('AW_NavPlanDetour()', step, 'the last leg does not plan a detour round an obstacle')


if __name__ == '__main__':
    unittest.main()
