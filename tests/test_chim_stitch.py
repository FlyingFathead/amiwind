# SPDX-License-Identifier: GPL-3.0-only
"""CHIM/legacy border audit (tools/chim/stitch.py): sampler, BSP readers, status rules and the
aw-stitch-report-1 layout, on synthetic inputs only (no game data)."""
import json
import math
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import stitch as S  # noqa: E402


def tile_faces(x0, y0, z, kind='ground', ccw=True):
    """The two triangles (0-1-2, 0-2-3) of a 128-unit tile with corner heights z[0..3]."""
    c = [(x0, y0, z[0]), (x0 + 128, y0, z[1]), (x0 + 128, y0 + 128, z[2]), (x0, y0 + 128, z[3])]
    tris = [[c[0], c[1], c[2]], [c[0], c[2], c[3]]]
    return [(t if ccw else t[::-1], kind) for t in tris]


class Plain:
    """A flat or planar ground both sides agree on, with a standing hull 24 units above it."""

    def __init__(self, z=lambda x, y: 0.0, liquid=None):
        self.z = z
        self.liquid = liquid

    def height(self, x, y):
        return self.z(x, y), self.liquid


class StubLegacyMap:
    def __init__(self, name, ground, objects=()):
        self.name = name
        self.ground = ground
        self.sha256 = '0' * 64
        self._objects = list(objects)

    def contents(self, p):
        return S.SOLID if p[2] < self.ground.height(p[0], p[1])[0] else S.EMPTY

    def hull(self, p):
        return S.SOLID if p[2] < self.ground.height(p[0], p[1])[0] + 24 else S.EMPTY

    def objects(self):
        return self._objects


class StubLegacy:
    def __init__(self, m):
        self.m = m
        self.regions = [{'name': m.name}]
        self.maps = {m.name: (m, 'world-terrain')}

    def at(self, x, y):
        return self.m

    def get(self, region):
        return self.m

    def regions_touching(self, *box):
        return self.regions


class StubChim:
    def __init__(self, ground, extent=(-3072, -3072, 3072, 3072), origin=(0.0, 0.0), placements=()):
        self.ground = ground
        self.extent = extent
        self.origin = (origin[0], origin[1], 0.0)
        self.placements = list(placements)

    def contents(self, p):
        return S.SOLID if p[2] < self.ground.height(p[0], p[1])[0] else S.EMPTY

    def hull(self, p):
        return S.SOLID if p[2] < self.ground.height(p[0], p[1])[0] + 24 else S.EMPTY


ROW = {'id': 'test_area', 'origin': [0.0, 0.0, 0.0], 'core': [[-2976, -2976], [2976, 2976]], 'draw_distance': 540}
CFG = {'source_cell': [0, 0]}


class GroundTest(unittest.TestCase):
    def test_height_on_tilted_tile_both_windings(self):
        for ccw in (True, False):
            faces = tile_faces(0, 0, [0, 128, 256, 128], ccw=ccw)
            # Quake winding (clockwise from above) needs the plane normal: give it explicitly
            if not ccw:
                faces = [(pts, kind, S._normal(pts[::-1])) for pts, kind in faces]
            g = S.Ground(faces)
            self.assertAlmostEqual(g.height(64, 32)[0], 96.0, places=6)
            self.assertAlmostEqual(g.height(32, 64)[0], 96.0, places=6)
            self.assertIsNone(g.height(200, 64)[0])

    def test_downward_faces_are_ignored(self):
        down = [(t[::-1], k) for t, k in tile_faces(0, 0, [5, 5, 5, 5])]
        self.assertIsNone(S.Ground(down).height(10, 20)[0])

    def test_liquid_and_ground_kept_apart(self):
        g = S.Ground(tile_faces(0, 0, [-40] * 4) + tile_faces(0, 0, [0] * 4, kind='liquid'))
        self.assertEqual(g.height(30, 70), (-40.0, 0.0))

    def test_edges_count_as_inside(self):
        g = S.Ground(tile_faces(0, 0, [7] * 4))
        self.assertEqual(g.height(0, 64)[0], 7.0)
        self.assertEqual(g.height(64, 64)[0], 7.0)       # on the diagonal


class StandingTest(unittest.TestCase):
    def test_bisection_finds_the_hull_top(self):
        z = S.standing(lambda p: S.SOLID if p[2] < 33.3 else S.EMPTY, 0, 0, 9.3)
        self.assertLessEqual(abs(z - 33.3), 1.0 / 32)

    def test_no_floor_is_not_measured(self):
        self.assertIsNone(S.standing(lambda p: S.EMPTY, 0, 0, 0))

    def test_buried_start_rises(self):
        z = S.standing(lambda p: S.SOLID if p[2] < 150 else S.EMPTY, 0, 0, 0)
        self.assertLessEqual(abs(z - 150), 1.0 / 32)


class RefinementTest(unittest.TestCase):
    def test_plain_grid_is_not_refined(self):
        g = S.Ground(tile_faces(0, 0, [-10, 20, 30, -5]))
        h = lambda x, y: g.height(x, y)[0]
        self.assertEqual(S.refined(h, 40, 90)[0], False)
        self.assertAlmostEqual(S.tile_grid_height(h, 40, 90), h(40, 90))

    def test_inserted_sample_is_refined(self):
        corners = [-10, 20, 30, -5]
        g = S.Ground(tile_faces(0, 0, corners))
        bump = lambda x, y: g.height(x, y)[0] + (12.0 if 32 <= x <= 96 and 32 <= y <= 96 else 0.0)
        flag, grid = S.refined(bump, 64, 50)
        self.assertTrue(flag)
        self.assertAlmostEqual(grid, g.height(64, 50)[0])


class EdgeTest(unittest.TestCase):
    def test_points_and_coords_round_trip(self):
        core = ROW['core']
        for edge in S.EDGES:
            for t, off in ((-100.0, 0.0), (2000.0, 32.0), (5.0, -896.0)):
                x, y = S.edge_point(core, edge, t, off)
                self.assertEqual(S.edge_coords(core, edge, x, y), (t, off))
            # outward is away from the centre
            x, y = S.edge_point(core, edge, 0.0, 10.0)
            self.assertGreater(max(abs(x), abs(y)), 2976)

    def test_samples_never_on_the_tile_grid(self):
        for edge in S.EDGES:
            ts = S.along(ROW['core'], edge)
            self.assertEqual(len(ts), 5952 // S.STEP)
            self.assertTrue(all((t % S.TILE) not in (0, 0.0) for t in ts))
            self.assertTrue(all(b - a == S.STEP for a, b in zip(ts, ts[1:])))

    def test_yaw_box(self):
        lo, hi = S.yaw_box((-10, -2, 0), (10, 2, 5), 90)
        self.assertAlmostEqual(lo[0], -2)
        self.assertAlmostEqual(hi[1], 10)


class StatusTest(unittest.TestCase):
    def cell(self, h=0.0, arrival=0.0, mismatch=0):
        return {'heights': {'max': h}, 'arrival': {'enter': {'max': arrival}, 'leave': {'max': None}},
                'contents_mismatch': mismatch}

    def test_limits(self):
        self.assertEqual(S.cell_status(self.cell())[0], 'ok')
        self.assertEqual(S.cell_status(self.cell(h=1.5))[0], 'warn')
        self.assertEqual(S.cell_status(self.cell(h=4.5))[0], 'warn')    # the limit itself passes
        self.assertEqual(S.cell_status(self.cell(h=4.51))[0], 'fail')
        self.assertEqual(S.cell_status(self.cell(arrival=5))[0], 'fail')
        self.assertEqual(S.cell_status(self.cell(mismatch=1))[0], 'warn')
        self.assertEqual(S.judge(None, 1, 2), 'ok')
        self.assertEqual(S.worst(['ok', 'fail', 'warn']), 'fail')

    def test_limits_are_written_in_the_report(self):
        self.assertEqual(S.LIMITS['height_fail'], 4.5)
        self.assertIsNone(S.LIMITS['far_step'])


class AuditAreaTest(unittest.TestCase):
    def run_area(self, legacy_z, chim_z, objects=(), placements=()):
        legacy = StubLegacy(StubLegacyMap('vf0000', Plain(legacy_z), objects))
        chim = StubChim(Plain(chim_z), placements=placements)
        area = S.audit_area(ROW, CFG, chim, legacy)
        json.dumps(area)            # the report is plain JSON
        return area

    def test_matching_ground_is_ok_but_the_far_gap_warns(self):
        area = self.run_area(lambda x, y: 0.01 * x, lambda x, y: 0.01 * x)
        self.assertEqual(set(area['edges']), set(S.EDGES))
        for e in area['edges'].values():
            self.assertEqual(e['heights']['max'], 0.0)
            self.assertEqual(e['arrival']['enter']['max'], 0.0)
            self.assertEqual(e['arrival']['leave']['not_measured'], 0)
            self.assertEqual(e['far_band_gap']['frame_edge_beyond_core'], 96)
            self.assertEqual(e['far_band_gap']['gap_at_leave'], 540 - 64)
            self.assertEqual(e['status'], 'warn')
            self.assertEqual([c['status'] for c in e['cells']], ['ok'] * len(e['cells']))
            self.assertEqual(e['offsets'], [-896, -512, -256, -128, -64, -32, 0, 32, 64])
        self.assertEqual(area['status'], 'warn')

    def test_a_step_fails_its_cells(self):
        area = self.run_area(lambda x, y: 0.0, lambda x, y: 6.0 if x > 0 else 0.0)
        e = area['edges']['E']
        self.assertEqual(e['heights']['max'], 6.0)
        self.assertEqual(e['status'], 'fail')
        self.assertAlmostEqual(e['arrival']['leave']['max'], 6.0, delta=1.0 / 16)
        self.assertEqual(area['edges']['W']['heights']['max'], 0.0)
        self.assertEqual(area['status'], 'fail')

    def test_objects_matched_by_reference(self):
        box = lambda x, y: ((x - 8, y - 8, 0), (x + 8, y + 8, 50))
        objects = [('1', '*1', (2900.0, 0.0, 0.0), box(2900, 0)),        # both
                   ('2', '*2', (3500.0, 0.0, 0.0), box(3500, 0))]        # legacy only, outside
        placements = [('1', 'x/a', (2900.0, 0.0, 0.0), box(2900, 0)),
                      ('3', 'x/shack_01', (2800.0, 10.0, 0.0), box(2800, 10)),   # chim only, inside
                      ('4', 'x/b', (2976.0, 20.0, 0.0), box(2976, 20))]          # cut by the handover line
        area = self.run_area(lambda x, y: 0.0, lambda x, y: 0.0, objects, placements)
        o = area['edges']['E']['objects']
        self.assertEqual((o['legacy'], o['chim'], o['both']), (2, 3, 1))
        self.assertEqual([r['ref'] for r in o['chim_only']], ['3', '4'])
        self.assertEqual(o['chim_only_inside_core'], 1)
        self.assertEqual([r['ref'] for r in o['cut_by_handover_line']], ['4'])
        census = area['objects']
        self.assertEqual((census['chim_inside_core'], census['drawn_by_legacy'], census['chim_only']), (2, 1, 1))
        self.assertIn('x/shack', census['chim_only_by_class'])


def bsp_lumps_one_face(side):
    """Minimal BSP29 lumps: one quad on the plane z = 5 (normal +z), one node splitting at it,
    leaves empty above and solid below, one clipnode doing the same."""
    planes = struct.pack('<4fi', 0, 0, 1, 5, 2)
    verts = b''.join(struct.pack('<3f', *v) for v in ((0, 0, 5), (0, 64, 5), (64, 64, 5), (64, 0, 5)))
    edges = struct.pack('<HH', 0, 0) + b''.join(struct.pack('<HH', a, b) for a, b in ((0, 1), (1, 2), (2, 3), (3, 0)))
    surfedges = struct.pack('<4i', 1, 2, 3, 4)
    texinfo = struct.pack('<8fii', 1, 0, 0, 0, 0, 1, 0, 0, 0, 0)
    faces = struct.pack('<HhihH4Bi', 0, side, 0, 4, 0, 0, 0, 0, 0, -1)
    nodes = struct.pack('<ihh6hHH', 0, -1, -2, 0, 0, 0, 0, 0, 0, 0, 1)
    leafs = struct.pack('<ii6hHH4B', -1, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0) + \
        struct.pack('<ii6hHH4B', -2, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    clips = struct.pack('<iHH', 0, 0xFFFF, 0xFFFE)
    lumps = [b''] * 15
    lumps[1], lumps[3], lumps[5], lumps[6], lumps[7] = planes, verts, nodes, texinfo, faces
    lumps[9], lumps[10], lumps[12], lumps[13] = clips, leafs, edges, surfedges
    return lumps


class BspReaderTest(unittest.TestCase):
    def test_face_normal_from_plane_and_side(self):
        (pts, name, n), = S.faces_of(bsp_lumps_one_face(0), ['g7'])
        self.assertEqual(name, 'g7')
        self.assertEqual(n, (0.0, 0.0, 1.0))
        g = S.Ground([(pts, S.face_kind(name), n)])
        self.assertEqual(g.height(10, 10)[0], 5.0)
        (_, _, n), = S.faces_of(bsp_lumps_one_face(1), ['g7'], shift=(100, 0, 0))
        self.assertEqual(n, (-0.0, -0.0, -1.0))

    def test_contents(self):
        lumps = bsp_lumps_one_face(0)
        self.assertEqual(S.node_contents(lumps, 0, (1, 1, 6)), S.EMPTY)
        self.assertEqual(S.node_contents(lumps, 0, (1, 1, 4)), S.SOLID)
        self.assertEqual(S.clip_contents(lumps, 0, (1, 1, 6)), S.EMPTY)
        self.assertEqual(S.clip_contents(lumps, 0, (1, 1, 4)), S.SOLID)

    def test_face_kinds_and_entities(self):
        self.assertEqual(S.face_kind('g12'), 'ground')
        self.assertEqual(S.face_kind('*water'), 'liquid')
        self.assertIsNone(S.face_kind('sky'))
        self.assertIsNone(S.face_kind('surface12'))
        ents = S.entities('{\n"classname" "worldspawn"\n}\n{\n"aw_ref" "5"\n"origin" "1 2 3"\n}\n')
        self.assertEqual(ents[1], {'aw_ref': '5', 'origin': '1 2 3'})


class RegionFramesTest(unittest.TestCase):
    """--regions: CHIM region frames (one cell each, a divided cell included) are audited like town areas; every
    region frame is a neighbour of the others, so an edge between two CHIM frames is never a legacy border."""

    def test_rows_of_the_ownership_table(self):
        import tempfile
        from unittest import mock
        from chim import regions as R
        from chim import validate as V
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / 'chim-world/chim').mkdir(parents=True)
            (run / 'chim-world/chim/world.cwi').write_bytes(b'')
            table = R.ownership({(-7, 2): 'land', (-6, 2): 'land', (-8, 2): 'seabed'})
            (run / 'chim-world' / R.TABLE_FILE).write_text(R.dumps(table), encoding='utf-8')
            frames = [('f', {'cell': list(c)}, []) for c in ((-7, 2), (-6, 2), (-8, 2))]
            with mock.patch.object(V, 'load_world', lambda world_dir, fails: (None, None, None, [], [], frames)), \
                    mock.patch.object(S, 'ChimFrame', lambda frame, chunks, t, m, origin: ('frame', tuple(frame['cell']))):
                found, rows = S.load_region_areas(run, {(-7, 2)})
                every, _ = S.load_region_areas(run)
        self.assertEqual([r['id'] for r in rows], ['rcm8_p2', 'rcm7_p2', 'rcm6_p2'])
        self.assertEqual(len(found), 1)
        row, cfg, frame = found[0]
        self.assertEqual((row['id'], row['core'], cfg['source_cell'], frame), ('rcm7_p2', [[-1024, -1024], [1024, 1024]],
                                                                            [-7, 2], ('frame', (-7, 2))))
        self.assertEqual(row['origin'][:2], [-7 * 2048 + 1024, 2 * 2048 + 1024])
        self.assertEqual(row['draw_distance'], S.REGION_DRAW_DISTANCE)
        self.assertEqual(len(every), 3)


class FormatDocTest(unittest.TestCase):
    def test_documented(self):
        doc = (ROOT / 'docs/chim/STITCH_AUDIT.md').read_text(encoding='utf-8')
        self.assertIn(S.FORMAT, doc)
        for key in ('heights_unrefined', 'chim_vs_legacy_grid', 'far_band_gap', 'cut_by_handover_line',
                    'chim_only_by_class', 'arrival_unrefined'):
            self.assertIn(key, doc)
        files = json.loads((ROOT / 'tools/release-files.json').read_text(encoding='utf-8'))
        for f in ('tools/chim/stitch.py', 'docs/chim/STITCH_AUDIT.md', 'tests/test_chim_stitch.py'):
            self.assertIn(f, files)


if __name__ == '__main__':
    unittest.main()
