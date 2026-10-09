"""Stair gate regression fixtures for the flights the rule's first build left failing.

Each case is a small synthetic copy of the real geometry (visible faces as the
gate reads them from a map, collision as convex standing-hull solids in origin
space, as hull 1 holds them):

- STAIRS-BALMORA-B01-32 (ex_hlaalu_b_01): the authored collision ramp runs
  through the nosings, above the visible foot, under a low arch lintel; the walk
  must start from the free standing column, not from inside the lintel.
- STAIRS-SEYDA-WAREHOUSE-32 (in_common_tower_thatch): the straight start line
  grazes a wall closer than the collision plates' 0.2 thickness; a start a
  little to the side is open and the flight is walkable.
- STAIRS-BALMORA-WESTSOUTH-32 (in_hlaalu_hall_stairsl): the flight's foot ends
  at a closed hinged door (in_hlaalu_door); the walk through the door is not a
  stair failure (visible geometry in the way).
- STAIRS-ADDAMASARTUS-32 (in_moldcave_09): two tilted cave-floor triangles that
  share an edge are not a step, whatever their mean heights.
And the guard: collision that is solid where nothing visible is near still fails.
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

from player_hull import MINS, MAXS  # noqa: E402

BX, BY, BZ = MAXS[0], MAXS[1], -MINS[2]   # standing box half extents (z: origin to feet)


class Solids:
    """Union of convex solids (planes n.p <= d inside) with the Scene trace API."""

    def __init__(self):
        self.solids = []

    def add(self, planes, ref=1):
        self.solids.append(([(tuple(n), d) for n, d in planes], ref))

    def box(self, lo, hi, ref=1):
        """A visible box (lo..hi) as the standing hull holds it: grown by the box."""
        lo = (lo[0] - BX, lo[1] - BY, lo[2] - MAXS[2])
        hi = (hi[0] + BX, hi[1] + BY, hi[2] + BZ)
        self.add([((1, 0, 0), hi[0]), ((-1, 0, 0), -lo[0]), ((0, 1, 0), hi[1]), ((0, -1, 0), -lo[1]),
                  ((0, 0, 1), hi[2]), ((0, 0, -1), -lo[2])], ref)

    def trace(self, start, end):
        best = None
        d = [end[i] - start[i] for i in range(3)]
        for planes, ref in self.solids:
            t0, t1, normal = 0., 1., None
            ok = True
            for n, dist in planes:
                a = sum(n[i] * start[i] for i in range(3)) - dist
                b = sum(n[i] * d[i] for i in range(3))
                if abs(b) < 1e-12:
                    if a >= 0:
                        ok = False
                        break
                    continue
                t = -a / b
                if b < 0:
                    if t > t0:
                        t0, normal = t, n
                else:
                    t1 = min(t1, t)
                if t0 > t1:
                    ok = False
                    break
            if not ok:
                continue
            if normal is None:  # start inside
                t0, normal = 0., (0., 0., 1.)
            if best is None or t0 < best['fraction']:
                best = dict(fraction=t0, normal=normal, reference=ref)
        return best


def level(x0, x1, z, y0=0., y1=40., ref=100):
    return ([(x0, y0, z), (x0, y1, z), (x1, y1, z), (x1, y0, z)], ref)


def riser(x, z0, z1, y0=0., y1=40., ref=100):
    return ([(x, y0, z0), (x, y0, z1), (x, y1, z1), (x, y1, z0)], ref)


def flight(rise=8., run=8., steps=4, landing=40., floor=-60., ref=100):
    """Visible faces: approach floor (z 0, x < 0) and a flight rising along +x."""
    polys = [level(floor, 0, 0, ref=ref)]
    for k in range(steps):
        polys.append(riser(run * k, rise * k, rise * (k + 1), ref=ref))
        polys.append(level(run * k, run * (k + 1) if k < steps - 1 else run * k + landing, rise * (k + 1), ref=ref))
    return polys


def flight_collision(scene, rise=8., run=8., steps=4, landing=40.):
    scene.box((-90, -30, -20), (90, 70, 0))                       # floor slab
    for k in range(steps):
        scene.box((run * k, 0, 0), (run * (steps - 1) + landing, 40, rise * (k + 1)))


class StairCaseFixtures(unittest.TestCase):
    def gate(self, polys, scene):
        import stair_walk
        rows = stair_walk.check_polys(polys, scene)
        steps = [r for r in rows if r['kind'] == 'step' and r.get('flight')]
        return steps, [r for r in rows if stair_walk._gating(r)]

    def test_b01_ramp_under_a_low_lintel_starts_from_the_free_column(self):
        import stair_walk
        # The authored ramp through the nosings (45 degrees, z = x + 8) as the
        # standing hull holds it, a low arch lintel over the foot (x < -7.5,
        # underside 49.125), the floor.
        s = Solids()
        s.box((-90, -30, -20), (90, 70, 0))
        k = 2 ** -.5
        s.add([((-k, 0, k), k * (BX + 8 + BZ)), ((0, 0, -1), 0.), ((1, 0, 0), 40.)])   # z <= x + BX + 8 + BZ
        s.box((-40, -30, 49.125), (-7.5, 70, 80))
        start = (-3., 20., 8 + BZ + .25)       # the gate's start: 11 before the riser at x 8, on the tread level
        self.assertEqual(s.trace(start, start)['fraction'], 0.)        # inside the ramp
        probe = (start[0], start[1], start[2] + 8)
        self.assertEqual(s.trace(probe, probe)['fraction'], 0.)        # inside the lintel
        result = stair_walk.walk(s, start, (1., 0.), 16.)
        self.assertEqual(result['status'], 'walked', result)
        self.assertGreater(result['at'][2], start[2] + 8)               # it climbed the ramp
        # A start with no free point in its column stays a failure.
        self.assertEqual(stair_walk.walk(s, (-3., 20., 8.), (1., 0.), 4.)['status'], 'start in solid')
        # The whole flight through the gate.
        polys = flight() + [([(-40, -30, 49.125), (-7.5, -30, 49.125), (-7.5, 70, 49.125), (-40, 70, 49.125)], 300)]
        steps, gating = self.gate(polys, s)
        self.assertGreaterEqual(len(steps), 3)
        self.assertFalse(gating, gating)

    def test_warehouse_start_grazing_a_wall_is_retried_to_the_side(self):
        # A wall beside the start line that the standing box touches by 0.1
        # (as the tower wall, 0.12): open to the eye within the gate's 0.5
        # inset, solid for the wall's 0.2-thick collision plate.
        polys = flight(rise=6., run=10.)
        wall_y = 20 - BY + .1
        polys.append(([(-40, wall_y, 0), (-40, wall_y, 60), (-5, wall_y, 60), (-5, wall_y, 0)], 300))
        s = Solids()
        flight_collision(s, rise=6., run=10.)
        s.box((-40, wall_y - 5, 0), (-5, wall_y + .2, 60), ref=300)
        steps, gating = self.gate(polys, s)
        self.assertFalse(gating, gating)
        self.assertTrue([r for r in steps if r['result'] == 'passed' and r['point'][0] == 0.])

    def test_westsouth_closed_door_at_the_foot_is_not_a_stair_failure(self):
        # A closed hinged door (a thin visible plate across the whole approach)
        # just before the first riser: the walk from beyond it is blocked by the
        # door, which the eye sees as well.
        polys = flight()
        door = ([(-9.1, -30, 0), (-9.1, -30, 60), (-9.1, 70, 60), (-9.1, 70, 0)], 400)
        polys.append(door)
        s = Solids()
        flight_collision(s)
        s.box((-9.5, -30, 0), (-8.9, 70, 60), ref=400)
        steps, gating = self.gate(polys, s)
        self.assertFalse(gating, gating)
        first = [r for r in steps if r['point'][0] == 0.]
        self.assertTrue(first)
        self.assertEqual(first[0]['result'], 'untestable')

    def test_collision_solid_where_nothing_visible_is_near_still_fails(self):
        import stair_walk
        polys = flight()
        s = Solids()
        flight_collision(s)
        s.box((-30, 0, 0), (40, 40, 30), ref=500)        # invisible convex fill over the flight
        steps, gating = self.gate(polys, s)
        self.assertTrue(gating)
        self.assertTrue(all(r['detail']['status'] in stair_walk.BLOCKING for r in gating))

    def test_addamasartus_tilted_floor_triangles_are_not_a_step(self):
        import stair_walk
        # Two cave-floor faces tilted about 6 degrees that meet along one edge:
        # their centroids are 1.5 apart in height, the shared edge has no drop.
        a = ([(0, 0, 0), (0, 40, 0), (20, 40, 2), (20, 0, 2)], 100)
        b = ([(20, 0, 2), (20, 40, 2), (40, 40, 3), (40, 0, 3)], 100)
        self.assertGreater(stair_walk._normal(a[0])[2], stair_walk.TREAD_NZ)
        self.assertFalse([c for c in stair_walk.candidates([a, b]) if c['kind'] == 'step'])
        # A real riser of 1.5 between level faces stays a step.
        c = ([(0, 0, 0), (0, 40, 0), (20, 40, 0), (20, 0, 0)], 100)
        d = ([(20, 0, 1.5), (20, 40, 1.5), (40, 40, 1.5), (40, 0, 1.5)], 100)
        found = [x for x in stair_walk.candidates([c, d]) if x['kind'] == 'step']
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['rise'], 1.5)


if __name__ == '__main__':
    unittest.main()
