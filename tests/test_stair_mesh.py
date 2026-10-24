"""Stair collision method 1 and the geometric stair check (CHIM-STAIR-COLLISION-MESH-47).

Synthetic meshes only (source units; the converter scales by 0.25, so a 32-unit riser is an 8-unit step). No walk:
every check here is plane arithmetic on the collision pieces (tools/stair_mesh.py).
- a mesh with no flight: method 1 gives exactly method 0's collision;
- a flight whose collision already passes (a proxy or an authored ramp through the nosings): kept;
- an authored ramp a step and more over the treads (the ex_redoran_steps_02 case): replaced by one ramp that passes;
- a flight too steep for one ramp, a spiral stair, slanted risers, a flight with a landing: tread blocks or a ramp,
  and the check passes on the result;
- the check names what is wrong: solid over the tread, no floor, a too-steep standing surface, a rise over a step.
"""
import importlib.util
import math
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


def flight(rise=32., run=32., steps=6, width=160., lean=0., landing=None):
    """Visible treads and risers along +x. lean: a riser's top set back by this much (a slanted riser).
    landing: (after step k, length) a landing of that length after step k."""
    v, f = [], []
    x = 0.
    for k in range(steps):
        z0, z1 = k * rise, (k + 1) * rise
        quad(v, f, [(x, 0, z0), (x, width, z0), (x + lean, width, z1), (x + lean, 0, z1)])
        depth = run + (landing[1] if landing and k == landing[0] else 0.)
        quad(v, f, [(x + lean, 0, z1), (x + lean + depth, 0, z1), (x + lean + depth, width, z1), (x + lean, width, z1)])
        x += lean + depth
    return mesh(v, f)


def spiral(steps=12, rise=24., inner=40., outer=200., turn=270.):
    """A spiral stair around the z axis: wedge treads and their risers."""
    v, f = [], []
    a = math.radians(turn) / steps
    for k in range(steps):
        a0, a1 = k * a, (k + 1) * a
        z0, z1 = k * rise, (k + 1) * rise
        p = lambda r, t, z: (r * math.cos(t), r * math.sin(t), z)
        quad(v, f, [p(inner, a0, z0), p(outer, a0, z0), p(outer, a0, z1), p(inner, a0, z1)])
        quad(v, f, [p(inner, a0, z1), p(outer, a0, z1), p(outer, a1, z1), p(inner, a1, z1)])
    return mesh(v, f)


def planks(boards=12, depth=16., gap=4., width=160., sag=5.):
    """A sagging plank bridge along +x (source units): boards with gaps, down to the middle and up again, each a
    little higher or lower than the next (about 1.2 units after scaling)."""
    v, f = [], []
    for k in range(boards):
        x0 = k * (depth + gap)
        z = sag * abs(k - (boards - 1) / 2.)
        quad(v, f, [(x0, 0, z), (x0 + depth, 0, z), (x0 + depth, width, z), (x0, width, z)])
    return mesh(v, f)


def ramp(lift, rise=32., run=32., steps=6, width=160.):
    """A collision ramp from the foot of the flight to its top, LIFT source units over the nosing line."""
    v, f = [], []
    quad(v, f, [(0, 0, lift), (steps * run, 0, steps * rise + lift), (steps * run, width, steps * rise + lift),
                (0, width, lift)])
    return mesh(v, f)


def box(lo, hi):
    """A closed box (source units)."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    v, f = [], []
    quad(v, f, [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)])
    quad(v, f, [(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)])
    quad(v, f, [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)])
    quad(v, f, [(x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0)])
    quad(v, f, [(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)])
    quad(v, f, [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)])
    return mesh(v, f)


def profile(method=None):
    p = {'stair_plates': True, 'visible_treads': True, 'surface_collision_beyond': 8.5}
    if method:
        p['stair_collision'] = method
    return p


def failures(pieces, vis):
    from stair_mesh import check_flights
    return [x for _, found in check_flights(pieces, *vis) for x in found]


def same(a, b):
    if len(a) != len(b):
        return False
    return all(np.array_equal(np.asarray(p[0]), np.asarray(q[0])) for p, q in zip(a, b))


@unittest.skipUnless(READY, 'numpy and scipy required')
class StairMeshTests(unittest.TestCase):
    def test_flights_are_grouped_per_staircase(self):
        from stair_mesh import flights
        from mesh_geometry import flight_treads
        v1, f1 = flight()
        v2, f2 = flight()
        v2 = v2.copy()
        v2[:, 1] += 1000.
        v = np.vstack((v1, v2))
        f = np.vstack((f1, f2 + [len(v1), len(v1), len(v1), 0]))
        groups = flights(v, f)
        self.assertEqual(len(groups), 2)
        self.assertEqual(sorted(int(t) for g in groups for t in g), flight_treads(v, f).tolist())

    def test_no_flight_is_method_0(self):
        from stair_mesh import collision_pieces
        v, f = box((0, 0, 0), (64, 64, 64))
        a = collision_pieces(v, f, profile(), stairs='on', visible=(v, f))
        b = collision_pieces(v, f, profile('mesh'), stairs='on', visible=(v, f))
        self.assertTrue(same(a[0], b[0]))
        self.assertEqual(a[1:], b[1:])

    def test_without_the_switch_nothing_changes(self):
        from stair_mesh import collision_pieces
        vv, vf = flight()
        cv, cf = ramp(lift=64.)
        a = collision_pieces(cv, cf, profile(), stairs='on', visible=(vv, vf))
        b = collision_pieces(cv, cf, dict(profile(), stair_collision=None), stairs='on', visible=(vv, vf))
        self.assertTrue(same(a[0], b[0]))

    def test_walkable_proxy_is_kept(self):
        from stair_mesh import collision_pieces
        vv, vf = flight()
        pieces, exact, note = collision_pieces(vv, vf, profile('mesh'), stairs='on', visible=(vv, vf))
        self.assertIn('already passes the stair check', note)
        self.assertEqual(failures(pieces, (vv, vf)), [])

    def test_authored_ramp_through_the_nosings_is_kept(self):
        from stair_mesh import collision_pieces
        vv, vf = flight()
        cv, cf = ramp(lift=0.)
        pieces, _, note = collision_pieces(cv, cf, profile('mesh'), stairs='on', visible=(vv, vf))
        self.assertIn('already passes', note)
        self.assertEqual(failures(pieces, (vv, vf)), [])

    def test_authored_ramp_over_the_steps_is_replaced_by_one_ramp(self):
        from stair_mesh import collision_pieces
        vv, vf = flight()
        cv, cf = ramp(lift=64.)       # 16 units over the nosings after scaling: higher than a step
        base, _, _ = collision_pieces(cv, cf, profile(), stairs='on')
        self.assertTrue(failures(base, (vv, vf)))
        record = {}
        pieces, exact, note = collision_pieces(cv, cf, profile('mesh'), stairs='on', visible=(vv, vf), record=record)
        # the replaced flight's collision triangles, for the collision surface gate (CHIM-HULL-SURFACE-RESURVEY-48)
        self.assertTrue(record['removed'])
        self.assertIn('%d collision triangles of the flights removed' % len(record['removed']), note)
        self.assertTrue(all(0 <= i < len(cf) for i in record['removed']))
        self.assertIn('1 ramps, 0 tread blocks', note)
        self.assertIn('check: passed', note)
        self.assertIs(exact, True)
        self.assertEqual(failures(pieces, (vv, vf)), [])
        # one piece holds the whole flight, its top through the nosings: 45 degrees, walkable
        tops = [p for p in pieces if p[0][:, 2].max() >= 48 - 1e-6]
        self.assertEqual(len(tops), 1)

    def test_too_steep_flight_gets_tread_blocks(self):
        from stair_mesh import collision_pieces
        vv, vf = flight(rise=32., run=16.)      # 63 degrees: no walkable ramp
        cv, cf = ramp(lift=64., run=16.)         # an authored ramp over the flight, too steep and too high
        pieces, _, note = collision_pieces(cv, cf, profile('mesh'), stairs='on', visible=(vv, vf))
        self.assertIn('tread blocks', note)
        self.assertEqual(failures(pieces, (vv, vf)), [], note)

    def test_spiral_stair_gets_tread_blocks(self):
        from stair_mesh import flights, flight_ramp, tread_blocks, check_flight, _tris
        v, f = spiral()
        groups = flights(v, f)
        self.assertEqual(len(groups), 1)
        tris = _tris(v, f)
        piece, why = flight_ramp(tris, groups[0], np.zeros((0, 3)))
        self.assertIsNone(piece)
        self.assertIn('over a tread', why)
        blocks = tread_blocks(tris, groups[0])
        self.assertEqual(len(blocks), 12)
        self.assertEqual(check_flight(blocks, tris, groups[0]), [])

    def test_slanted_risers_and_a_landing(self):
        from stair_mesh import collision_pieces
        # (a riser leaning back more than mesh_geometry.RISER_NZ, 9 degrees, is not a riser: no flight is found there)
        for vis in (flight(lean=4.), flight(landing=(2, 96.))):
            vv, vf = vis
            cv, cf = ramp(lift=64., steps=6, run=40.)
            pieces, _, note = collision_pieces(cv, cf, profile('mesh'), stairs='on', visible=(vv, vf))
            self.assertIn('replaced', note)
            self.assertEqual(failures(pieces, (vv, vf)), [], note)

    def test_a_flight_it_cannot_fix_keeps_method_0(self):
        from stair_mesh import collision_pieces
        vv, vf = flight()
        cv, cf = ramp(lift=64.)
        roof_v, roof_f = box((-32, -32, 220), (256, 192, 236))   # a slab 6 units over the top tread: no standing room
        cv2 = np.vstack((cv, roof_v))
        cf2 = np.vstack((cf, roof_f + [len(cv), len(cv), len(cv), 0]))
        a = collision_pieces(cv2, cf2, profile(), stairs='on', visible=(vv, vf))
        record = {}
        b = collision_pieces(cv2, cf2, profile('mesh'), stairs='on', visible=(vv, vf), record=record)
        self.assertIn('method 0 kept', b[2])
        self.assertNotIn('removed', record)      # method 0's collision: nothing removed
        self.assertTrue(same(a[0], b[0]))

    def test_one_ramp_per_run(self):
        from stair_mesh import flights, run_ramps, check_flight, _tris
        v, f = flight(steps=8, landing=(3, 96.))
        tris = _tris(v, f)
        ids = flights(v, f)[0]
        pieces, ramps, blocks = run_ramps(tris, ids, np.zeros((0, 3)))
        self.assertEqual(ramps, 2)          # the runs below and above the landing
        self.assertEqual(blocks, 1)         # the landing
        self.assertEqual(check_flight(pieces, tris, ids), [])
        v, f = spiral(rise=12.)             # a gentle spiral (3 units a step): ramps over short stretches of it
        tris = _tris(v, f)
        ids = flights(v, f)[0]
        pieces, ramps, blocks = run_ramps(tris, ids, np.zeros((0, 3)))
        self.assertGreater(ramps, 1)
        self.assertEqual(check_flight(pieces, tris, ids), [])

    def test_rope_bridge_is_a_walkway_of_plates(self):
        from stair_mesh import collision_pieces
        from stair_mesh import flights, is_walkway, _tris
        vv, vf = planks()
        groups = flights(vv, vf)
        self.assertGreaterEqual(len(groups), 1)
        self.assertTrue(all(is_walkway(_tris(vv, vf), g) for g in groups))
        cv, cf = box((0, 0, -40), (12 * 20, 160, 40))       # a convex proxy burying the boards
        pieces, _, note = collision_pieces(cv, cf, profile('mesh'), stairs='on', visible=(vv, vf))
        self.assertIn('check: passed', note)
        self.assertEqual(failures(pieces, (vv, vf)), [], note)
        # the whole bridge is one walkway (its two level middle boards join the halves): sloped plates over it, not
        # a block per board (the rest: the proxy's sides as plates)
        self.assertEqual(len(flights(vv, vf)), 1)
        self.assertIn('1 ramps, 0 tread blocks', note)
        self.assertLessEqual(len(pieces), 8, note)

    def test_seam_with_a_lip_over_a_step_fails(self):
        from mesh_geometry import shell_collision_parts
        from stair_mesh import check_flight, flights, _tris
        vv, vf = flight(steps=6, run=96.)       # treads 24 units deep: the box stands on each
        tris = _tris(vv, vf)
        ids = flights(vv, vf)[0]
        from stair_mesh import tread_blocks, _hull_piece
        blocks = tread_blocks(tris, ids)
        # the blocks from the fourth tread up stand 6 units higher: a lip of 14 at that riser, over the step
        moved = [_hull_piece(p[0] + [0., 0., 6.]) if p[0][:, 2].max() > 3 * 8. + 1. else p for p in blocks]
        found = check_flight(moved, tris, ids)
        self.assertIn('no passage to the next tread within the step rule (lip)', {x['check'] for x in found})
        self.assertEqual(check_flight(blocks, tris, ids), [])

    def test_ramp_to_landing_seams_pass(self):
        from stair_mesh import flights, run_ramps, check_flight, _tris
        for landing in ((2, 96.), (3, 64.), (1, 160.)):
            v, f = flight(steps=8, landing=landing)
            tris = _tris(v, f)
            ids = flights(v, f)[0]
            pieces, ramps, blocks = run_ramps(tris, ids, np.zeros((0, 3)))
            self.assertEqual(check_flight(pieces, tris, ids), [], landing)

    def test_clip_cuts_the_standing_space_out_of_a_piece(self):
        from stair_mesh import _clip_out, _hull_piece, column_intervals
        ring = np.array([[0., 0.], [10., 0.], [10., 10.], [0., 10.]])
        region = (ring, 0., 33.)
        corners = np.array([[x, y, z] for x in (-5., 15.) for y in (-5., 15.) for z in (10., 20.)])
        slab = _hull_piece(corners)
        parts = _clip_out(slab, region, np.zeros((0, 3)))
        self.assertTrue(parts)
        inner = np.array([[5., 5., 15.], [2., 8., 12.]])
        outer = np.array([[-3., 5., 15.], [12., 12., 15.]])
        lows, highs, _ = column_intervals(parts, np.vstack((inner, outer)))
        solid = (lows < highs) & (lows <= 15.) & (highs >= 15.)
        self.assertFalse(solid[:, :2].any())        # nothing left over the footprint inside the band
        self.assertTrue(solid[:, 2:].any(axis=0).all())   # the parts outside stay
        # drawn geometry inside the part that would go (a pillar): the piece stays as it was
        self.assertEqual(len(_clip_out(slab, region, np.array([[5., 5., 15.]]))), 1)

    def test_landing_flight_falls_back_to_blocks(self):
        from stair_mesh import flights, flight_ramp, _tris
        v, f = flight(landing=(2, 96.))
        tris = _tris(v, f)
        piece, why = flight_ramp(tris, flights(v, f)[0], np.zeros((0, 3)))
        self.assertIsNone(piece)

    def test_ramp_refused_where_it_cuts_through_drawn_geometry(self):
        from stair_mesh import flights, flight_ramp, _tris
        v, f = flight()
        tris = _tris(v, f)
        post = np.array([[30., 20., 20.]])     # a drawn point inside the ramp, off the flight (a post)
        piece, why = flight_ramp(tris, flights(v, f)[0], post)
        self.assertIsNone(piece)
        self.assertIn('cuts through', why)

    def test_check_names_what_is_wrong(self):
        from stair_mesh import check_flight, flights, _tris
        from mesh_geometry import shell_collision_parts
        vv, vf = flight()
        tris = _tris(vv, vf)
        ids = flights(vv, vf)[0]
        # nothing at all: no floor
        found = check_flight([], tris, ids)
        self.assertTrue(found and all(x['check'] == 'no floor under the drawn tread' for x in found))
        # a box over the whole flight: over a step
        bv, bf = box((0, 0, 0), (192, 160, 192))
        from mesh_geometry import collision_parts
        found = check_flight(collision_parts(bv, bf), tris, ids)
        self.assertIn('no place on the tread for the standing box', {x['check'] for x in found})
        found = check_flight(collision_parts(bv, bf), tris, ids, form='point')     # the first form, kept
        self.assertIn('over a step above the drawn tread', {x['check'] for x in found})
        # a steep plate a little over the treads: too steep to stand on
        sv, sf = mesh([(0, 0, 0), (96, 0, 190), (96, 160, 190), (0, 160, 0)],   # 63 degrees
                      [[0, 1, 2, 0], [0, 2, 3, 0]])
        found = check_flight(shell_collision_parts(sv, sf), tris, ids)
        self.assertIn('standing surface too steep (normal z)', {x['check'] for x in found})
        # the visible flight as plates: every check passes (the step rule climbs each riser)
        self.assertEqual(check_flight(shell_collision_parts(vv, vf), tris, ids), [])
        # a step (its riser and tread) missing from the collision: the rise from the tread below is two steps (with
        # only the tread gone the box still climbs on the riser plates' top edges, as the engine's box would)
        keep = np.array([i for i in range(len(vf)) if i not in (4, 5, 6, 7)])
        found = check_flight(shell_collision_parts(vv, vf[keep]), tris, ids)
        self.assertTrue(found)
        for x in found:
            self.assertIn('level', x)
            self.assertEqual(len(x['point']), 3)

    def test_a_wall_beside_the_tread_is_not_a_fault_for_the_box_form(self):
        from stair_mesh import check_flight, flights, _tris
        from mesh_geometry import shell_collision_parts
        vv, vf = flight()
        tris = _tris(vv, vf)
        ids = flights(vv, vf)[0]
        wv, wf = box((-32, -40, 0), (224, -8, 400))        # a wall touching the flight's side: the box overlaps it there
        wall = shell_collision_parts(*box((-32, -40, 0), (224, -8, 400)))
        pieces = shell_collision_parts(vv, vf)
        self.assertEqual(check_flight(pieces + wall, tris, ids), [])

    def test_failures_name_the_level(self):
        from stair_mesh import check_flight, flights, _tris
        vv, vf = flight()
        tris = _tris(vv, vf)
        found = check_flight([], tris, flights(vv, vf)[0])
        self.assertEqual(sorted({x['level'] for x in found}), list(range(6)))

    def test_check_runs_in_milliseconds(self):
        import time
        from stair_mesh import check_flight, flights, _tris
        from mesh_geometry import shell_collision_parts
        vv, vf = flight(steps=20)
        tris = _tris(vv, vf)
        pieces = shell_collision_parts(vv, vf)
        t = time.perf_counter()
        self.assertEqual(check_flight(pieces, tris, flights(vv, vf)[0]), [])
        self.assertLess(time.perf_counter() - t, 2.)


@unittest.skipUnless(READY, 'numpy and scipy required')
class StairCheckReportTests(unittest.TestCase):
    def test_mesh_report_and_the_stage_gate(self):
        import json
        import tempfile
        from stair_mesh import collision_pieces
        import stair_mesh
        import build_summary
        vv, vf = flight()
        cv, cf = ramp(lift=64.)
        pieces, _, note = collision_pieces(cv, cf, profile('mesh'), stairs='on', visible=(vv, vf))
        good = stair_mesh.mesh_report(pieces, vv, vf, note)
        self.assertEqual((good['flights'], good['ships_method'], good['failed']), (1, 1, []))
        bad = stair_mesh.mesh_report([], vv, vf, 'stair mesh: 1 flights; ... method 0 kept')
        self.assertEqual((bad['ships_method'], bad['how']), (0, 'method 0 kept'))
        self.assertEqual(bad['failed'][0]['flight'], 0)
        bv, bf = box((0, 0, 0), (64, 64, 64))
        self.assertIsNone(stair_mesh.mesh_report([], bv, bf))
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'chim-world'
            for name, rows in (('rca', [dict(good, mesh='a.nif')]), ('rcb', [dict(good, mesh='a.nif')])):
                (out / 'work' / name).mkdir(parents=True)
                (out / 'work' / name / stair_mesh.REPORT_NAME).write_text(json.dumps({'meshes': rows}))
            report = stair_mesh.require(out)
            self.assertEqual((report['status'], report['meshes'], report['ships_method_1']), ('passed', 1, ['a.nif']))
            (out / 'work' / 'rcb' / stair_mesh.REPORT_NAME).write_text(json.dumps({'meshes': [dict(bad, mesh='b.nif')]}))
            with self.assertRaisesRegex(ValueError, 'b.nif .method 0, method 0 kept.: flight 0'):
                stair_mesh.require(out)
            summary = build_summary.read_stair_check(Path(tmp))
            self.assertEqual(summary['status'], 'failed')
            self.assertIn('b.nif (method 0)', build_summary.stair_check_line(summary))
            # a method 0 build writes no report: nothing in the summary
            self.assertIsNone(build_summary.read_stair_check(Path(tmp) / 'nothing'))


@unittest.skipUnless(READY, 'numpy and scipy required')
class AuthoredRampTests(unittest.TestCase):
    """An authored 45-degree ramp (a RootCollisionNode over 32-unit risers, as the Hlaalu stairs) stays walkable after
    conversion: every upward collision face over it has normal z at least 0.69 (tools/authored_ramps.py)."""

    def top_faces_over(self, pieces, cv, cf):
        from authored_ramps import ramp_faces, ramp_samples, _columns
        pts, _ = ramp_samples(cv, cf, ramp_faces(cv, cf))
        lows, highs, tops = _columns(pieces, pts)
        out = []
        for i in range(len(pts)):
            near = np.flatnonzero((highs[:, i] > pts[i, 2] - .5) & (highs[:, i] < pts[i, 2] + 8.5))
            if len(near):
                out.append(float(tops[near[np.argmax(highs[near, i])], i]))
        return out

    def test_45_degree_ramp_stays_walkable(self):
        import mesh_geometry as mg
        from authored_ramps import ramp_faces, invented_ramp_faults
        from prepare_area import interior_visual_profile
        vv, vf = flight()
        cv, cf = ramp(lift=0.)
        self.assertEqual(len(ramp_faces(cv, cf)), 2)        # the authored ramp: 45 degrees, nz 0.707
        for name, prof in (('CHIM', profile()), ('CHIM method 1', profile('mesh')), ('room i/', interior_visual_profile(
                'meshes/i/in_hlaalu_hall_stairsl.nif', 'balmora')), ('room other', {})):
            with self.subTest(profile=name):
                from stair_mesh import collision_pieces
                pieces, _, _ = collision_pieces(cv, cf, prof, stairs='on', visible=(vv, vf))
                tops = self.top_faces_over(pieces, cv, cf)
                self.assertTrue(tops)
                self.assertGreaterEqual(min(tops), 0.69)
                self.assertEqual(invented_ramp_faults(pieces, cv, cf), [])
                if prof.get('stair_collision'):
                    self.assertEqual(failures(pieces, (vv, vf)), [])

    def test_a_convex_piece_over_the_ramp_becomes_plates(self):
        from scipy.spatial import ConvexHull
        from authored_ramps import keep_authored_ramps, invented_ramp_faults, stair_ramp_faces
        vv, vf = flight()
        # the ramp and a 64-unit parapet at its top edge in one collision mesh
        v, f = [], []
        quad(v, f, [(0, 0, 0), (192, 0, 192), (192, 160, 192), (0, 160, 0)])
        quad(v, f, [(192, 0, 192), (192, 0, 256), (192, 160, 256), (192, 160, 192)])
        cv, cf = mesh(v, f)
        pts = cv[:, :3] * .25
        hull = ConvexHull(np.vstack((pts, pts + [-.2, 0, 0])))
        bad = [(np.vstack((pts, pts + [-.2, 0, 0])), hull, list(range(len(cf))), 0.)]   # one piece over both
        ids = stair_ramp_faces(cv, cf, vv, vf)
        self.assertEqual(len(ids), 2)
        faults = invented_ramp_faults(bad, cv, cf, ids)
        self.assertTrue(faults)
        self.assertIn('steep', {x['kind'] for x in faults})
        kept, exact, note = keep_authored_ramps(cv, cf, bad, False, ids)
        self.assertIn('authored plates', note)
        self.assertEqual(invented_ramp_faults(kept, cv, cf, ids), [])
        self.assertTrue(exact)
        self.assertGreaterEqual(min(self.top_faces_over(kept, cv, cf)), 0.69)

    def test_slopes_off_a_flight_are_not_stair_ramps(self):
        from authored_ramps import stair_ramp_faces
        vv, vf = flight()
        v, f = [], []
        quad(v, f, [(1000, 0, 0), (1192, 0, 192), (1192, 160, 192), (1000, 160, 0)])   # far from the flight
        cv, cf = mesh(v, f)
        self.assertEqual(len(stair_ramp_faces(cv, cf, vv, vf)), 0)


@unittest.skipUnless(READY, 'numpy and scipy required')
class KnownMeshTests(unittest.TestCase):
    """The meshes method 1 cannot fix yet are listed as one class (config/stair-check-known.json), never dropped."""

    def test_listed_meshes_are_reported_not_stopped(self):
        import json
        import tempfile
        import stair_mesh
        failed = {'flights': 1, 'ships_method': 0, 'how': 'method 0 kept',
                  'failed': [{'flight': 0, 'checks': {'floor': 1}, 'first': {'check': 'floor', 'point': [0, 0, 0]}}]}
        good = {'flights': 1, 'ships_method': 1, 'how': 'replaced', 'failed': []}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / 'work' / 'rca').mkdir(parents=True)
            (out / 'work' / 'rca' / stair_mesh.REPORT_NAME).write_text(json.dumps({'meshes': [
                dict(failed, mesh='meshes/x/ex_de_ship.nif'), dict(good, mesh='meshes/x/ok.nif'),
                dict(good, mesh='meshes/r/siltstrider.nif')]}))
            report = stair_mesh.require(out)
            self.assertEqual(report['status'], 'known')
            self.assertEqual([x['mesh'] for x in report['known']], ['meshes/x/ex_de_ship.nif'])
            self.assertEqual(report['known_passing'], ['meshes/r/siltstrider.nif'])
            self.assertEqual(report['known_class'], 'CHIM-STAIR-METHOD1-UNFIXED-48')
            with self.assertRaises(ValueError):
                stair_mesh.require(out, known={})

    def test_known_list_is_the_registered_class(self):
        import json
        data = json.loads((ROOT / 'config/stair-check-known.json').read_text(encoding='utf-8'))
        # 11 measured on 22 October; the 2 the dev2 verify run found pass since (CHIM-STAIR-METHOD1-UNFIXED-48)
        self.assertEqual(len(data['meshes']), 11)
        self.assertNotIn('meshes/f/flora_tree_gl_06.nif', data['meshes'])
        self.assertNotIn('meshes/x/ex_t_slavemarket.nif', data['meshes'])
        self.assertTrue((ROOT / 'docs/bugs' / (data['class'] + '.md')).is_file())

    def test_flight_unit_finds_the_drawn_flights(self):
        import tempfile
        import stair_mesh
        from mwad.scene import pack_geometry
        vv, vf = flight()
        packet = pack_geometry([[*map(float, p[:3]), 0., 0., 255, 255, 255, 255] for p in vv],
                               [tuple(map(int, t)) for t in vf], 1)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'a.mwpak'
            path.write_bytes(packet)
            model = {'offset': 0, 'bytes': len(packet), 'sha256': __import__('hashlib').sha256(packet).hexdigest()}
            self.assertEqual(stair_mesh.flight_unit((model, str(path))), 1)
            bv, bf = box((0, 0, 0), (64, 64, 64))
            packet = pack_geometry([[*map(float, p[:3]), 0., 0., 255, 255, 255, 255] for p in bv],
                                   [tuple(map(int, t)) for t in bf], 1)
            path.write_bytes(packet)
            model = {'offset': 0, 'bytes': len(packet), 'sha256': __import__('hashlib').sha256(packet).hexdigest()}
            self.assertEqual(stair_mesh.flight_unit((model, str(path))), 0)


@unittest.skipUnless(READY, 'numpy and scipy required')
class AuthoredCollisionFlightTests(unittest.TestCase):
    """CHIM-STAIR-METHOD1-UNFIXED-48: a drawn level face the mesh's own RootCollisionNode holds nothing under is no
    tread (the original stands nobody there: OpenMW collides with the RootCollisionNode alone)."""

    def test_treads_need_the_authored_collision_under_them(self):
        from stair_mesh import flights
        v, f = flight()
        self.assertEqual(len(flights(v, f)), 1)
        self.assertEqual(len(flights(v, f, collision=(v, f))), 1)              # the drawn mesh collides
        self.assertEqual(len(flights(v, f, collision=box((0, 0, 0), (192, 160, 192)))), 1)   # a block under it
        self.assertEqual(flights(v, f, collision=box((-400, -400, 0), (-300, -300, 400))), [])  # a trunk beside it
        # collision under the first two treads only: two levels, no flight
        self.assertEqual(flights(v, f, collision=box((0, 0, -10), (64, 160, 64))), [])

    def test_tree_roots_are_no_flight(self):
        """The four root faces of flora_tree_gl_06 (converter units x 4: source units) read as a flight of three
        levels; its RootCollisionNode (the trunk) holds nothing under them."""
        from stair_mesh import flights
        roots = [[(8.75, 136.39, 86.68), (-5.86, 147.76, 85.87), (-1.0, 110.45, 89.67)],
                 [(22.42, 124.4, 85.22), (8.75, 136.39, 86.68), (-1.0, 110.45, 89.67)],
                 [(-13.06, 88.05, 82.14), (-0.22, 135.31, 86.35), (-4.94, 135.43, 85.96)],
                 [(-13.06, 88.05, 82.14), (-6.87, 87.25, 82.56), (-0.22, 135.31, 86.35)]]
        v = [tuple(4. * c for c in p) for t in roots for p in t]
        f = [[3 * k, 3 * k + 1, 3 * k + 2, 0] for k in range(4)]
        v, f = mesh(v, f)
        self.assertEqual(len(flights(v, f)), 1)
        self.assertEqual(flights(v, f, collision=box((-40, 600, 0), (40, 680, 800))), [])

    def test_method_1_takes_the_flights_and_proof_from_the_drawn_mesh(self):
        """A visual recipe's reduced mesh (here the drawn steps 20 units higher) is what method 0's visible-tread rule
        sees; the flights, their stairway mesh and the check come from the mesh as drawn, as the build's stair check
        (mesh_report) reads it: built on the reduced mesh, the slave market's ramp left a drawn tread 18.8 units over
        its floor."""
        from stair_mesh import collision_pieces_mesh
        v, f = flight()
        up = v.copy()
        up[:, 2] += 80.
        reduced = (up, f)
        pieces, _, note = collision_pieces_mesh(v, f, profile('mesh'), visible=reduced, drawn=(v, f), authored=True)
        self.assertEqual(failures(pieces, (v, f)), [], note)
        old, _, _ = collision_pieces_mesh(v, f, profile('mesh'), visible=reduced)
        self.assertNotEqual(failures(old, (v, f)), [])


@unittest.skipUnless(READY, 'numpy and scipy required')
class StairCollisionSwitchTests(unittest.TestCase):
    def test_switch_defaults_to_method_1_and_refuses_unknown(self):
        # method 1 is the default since v0.0.48-dev2 (decided for the project 22 October 2026); 0 stays selectable
        import os
        from unittest.mock import patch
        from stair_collision_env import (stair_collision_method, export_stair_collision_method,
                                         STAIR_COLLISION_VARIABLE)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(STAIR_COLLISION_VARIABLE, None)
            self.assertEqual(stair_collision_method(), '1')
            export_stair_collision_method('0')
            self.assertEqual(os.environ[STAIR_COLLISION_VARIABLE], '0')
            self.assertEqual(stair_collision_method(), '0')
            export_stair_collision_method('1')
            self.assertNotIn(STAIR_COLLISION_VARIABLE, os.environ)
        with patch.dict(os.environ, {STAIR_COLLISION_VARIABLE: '0'}):
            self.assertEqual(stair_collision_method(), '0')
        with patch.dict(os.environ, {STAIR_COLLISION_VARIABLE: 'walk'}):
            with self.assertRaises(ValueError):
                stair_collision_method()


if __name__ == '__main__':
    unittest.main()
