# SPDX-License-Identifier: GPL-3.0-only
"""Stair candidates found core by core give what the whole map gives (v0.0.42 stair round).

STAIR-FLIGHT-CORE-SPLIT-41: the flight marks of a core's steps are found on the core plus stair_walk.FLIGHT_MARGIN,
so a flight that crosses a core line keeps its mark in both cores (the gate walks core by core).
STAIR-DETECT-POSITION-41: a placement's steps do not depend on where a frame puts it: every edge pair of two
level faces is tested (lossless bins) and the pair with the longest shared edge is taken, whatever the bin order.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import stair_walk  # noqa: E402


def level(x0, x1, z, y0=0., y1=40., ref=100):
    # an upward face winds clockwise seen from above (Quake)
    return ([(x0, y0, z), (x0, y1, z), (x1, y1, z), (x1, y0, z)], ref)


def riser(x, z0, z1, y0=0., y1=40., ref=100):
    return ([(x, y0, z0), (x, y0, z1), (x, y1, z1), (x, y1, z0)], ref)


def flight(steps=6, run=10., rise=4., x0=0., ref=100):
    """A straight flight along +x: approach floor, STEPS risers and treads, a landing."""
    polys = [level(x0 - 60, x0, 0., ref=ref)]
    for k in range(steps):
        polys.append(riser(x0 + run * k, rise * k, rise * (k + 1), ref=ref))
        polys.append(level(x0 + run * k, x0 + run * (k + 1) if k < steps - 1 else x0 + run * k + 60,
                           rise * (k + 1), ref=ref))
    return polys


def moved(polys, dx, dy, dz=0.):
    return [([(x + dx, y + dy, z + dz) for x, y, z in pts], ref) for pts, ref in polys]


def steps_of(items, dx=0., dy=0.):
    """(kind, x, y, z, flight) of each step, back in the placement's own frame, rounded."""
    return sorted((i['kind'], round(i['point'][0] - dx, 2), round(i['point'][1] - dy, 2), round(i['point'][2], 2),
                   bool(i.get('flight'))) for i in items if i['kind'] == 'step')


class FlightAcrossACoreLine(unittest.TestCase):
    def test_both_cores_keep_the_whole_maps_flight_marks(self):
        polys = flight()
        whole = steps_of(stair_walk.candidates(polys, None))
        self.assertEqual(len(whole), 6)
        self.assertTrue(all(s[4] for s in whole))
        # a core line between the second and the third riser (x = 15): two steps left, four right
        left = stair_walk.candidates(polys, (-1e9, -1e9, 15., 1e9))
        right = stair_walk.candidates(polys, (15., -1e9, 1e9, 1e9))
        self.assertEqual(sorted(steps_of(left) + steps_of(right)), whole)

    def test_without_the_margin_the_short_side_loses_its_mark(self):
        # the method before v0.0.42 (margin 0): two steps in a core are no flight of three
        polys = flight()
        left = steps_of(stair_walk.candidates(polys, (-1e9, -1e9, 15., 1e9), margin=0.))
        self.assertEqual(len(left), 2)
        self.assertFalse(any(s[4] for s in left))

    def test_steps_in_the_margin_are_not_returned(self):
        polys = flight()
        right = stair_walk.candidates(polys, (15., -1e9, 1e9, 1e9))
        self.assertTrue(all(i['point'][0] >= 15. for i in right))

    def test_the_frame_walkers_give_candidates_the_wide_polygons(self):
        from chim import collision
        polys = moved(flight(), 900., 0.)       # crosses the core line x = 1024 of the frame's cores
        core = (0., 0., 1024., 1024.)
        near, wide = collision.stair_polys(polys, core)
        self.assertTrue(all(p in wide for p in near))
        # a face past the walk's margin but within the flight margin: for the flight marks only
        far = moved([level(0., 10., 0.)], 1024. + collision.STAIR_MARGIN + 60., 0.)
        self.assertEqual(collision.stair_polys(far, core), ([], far))
        self.assertEqual(steps_of(stair_walk.candidates(wide, core)),
                         [s for s in steps_of(stair_walk.candidates(polys, None)) if s[1] < 1024.])


class SameStepsAtAnyPosition(unittest.TestCase):
    OFFSETS = ((0., 0.), (3000.37, -2711.9), (-4093.5, 4095.25), (0.4999, 0.5001), (1234.5, -0.5))

    def test_a_flight_gives_the_same_steps_wherever_it_lies(self):
        polys = flight(steps=5, run=11.5, rise=4.25)
        base = steps_of(stair_walk.candidates(polys, None))
        for dx, dy in self.OFFSETS:
            with self.subTest(offset=(dx, dy)):
                self.assertEqual(steps_of(stair_walk.candidates(moved(polys, dx, dy), None), dx, dy), base)

    def test_a_turned_flight_gives_the_same_steps_wherever_it_lies(self):
        import math
        a = math.radians(33.)

        def turn(polys):
            return [([(x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a), z) for x, y, z in pts], r)
                    for pts, r in polys]
        polys = turn(flight(steps=4))
        base = steps_of(stair_walk.candidates(polys, None))
        self.assertEqual(len(base), 4)
        for dx, dy in self.OFFSETS:
            with self.subTest(offset=(dx, dy)):
                self.assertEqual(steps_of(stair_walk.candidates(moved(polys, dx, dy), None), dx, dy), base)

    def test_the_longest_shared_edge_is_taken(self):
        # the upper tread is two faces' worth of edge along the riser: the face pair gives one step, at the
        # middle of the longest shared edge, whatever order the edges come in
        polys = [level(-60., 0., 0., y0=0., y1=60.), level(0., 40., 4., y0=0., y1=60.), riser(0., 0., 4., 0., 60.)]
        found = [i for i in stair_walk.candidates(polys, None) if i['kind'] == 'step']
        self.assertEqual(len(found), 1)
        self.assertAlmostEqual(found[0]['point'][1], 30.)
        self.assertAlmostEqual(found[0]['span'], 60.)
        # the same faces with their corners listed from another one (the same winding)
        shifted = [(pts[k % len(pts):] + pts[:k % len(pts)], ref) for k, (pts, ref) in enumerate(polys)]
        again = [i for i in stair_walk.candidates(shifted, None) if i['kind'] == 'step']
        self.assertEqual(len(again), 1)
        self.assertAlmostEqual(again[0]['span'], 60.)


if __name__ == '__main__':
    unittest.main()
