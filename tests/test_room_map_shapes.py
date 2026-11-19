# SPDX-License-Identifier: GPL-3.0-only
"""The listed source shapes of a room map's models drawn as the original draws them (tools/room_map_shapes.py) and the
check that every collision piece the original draws keeps drawn faces at its place (tools/drawn_collision.py);
PRISON-SHIP-FLOOR-STUCK-67, PRISON-SHIP-TABLE-DARK-TRIANGLE-67. Synthetic geometry, no game data."""
import importlib.util
import os
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import room_map_shapes as S  # noqa: E402

GEOMETRY = all(importlib.util.find_spec(n) for n in ('scipy', 'fast_simplification'))


def plates(count=3):
    """COUNT curved open plates side by side, plate k in material k (each one part of 162 triangles)."""
    vv, ff = [], []
    for material in range(count):
        base = len(vv)
        for y in range(10):
            for x in range(10):
                yy = 12 * material + y
                vv.append([x, yy, 3 * np.sin(x / 3) + 2 * np.cos(yy / 4), x / 9, y / 9, 255, 255, 255, 255])
        for y in range(9):
            for x in range(9):
                a = base + y * 10 + x
                ff.extend([[a, a + 1, a + 11, material], [a, a + 11, a + 10, material]])
    return np.array(vv, float), np.array(ff)


def model_of(names):
    return {'source': 'meshes/x/fixture.nif',
            'materials': [{'source_shape': name, 'source_face_range': {'start': 162 * k, 'count': 162}}
                          for k, name in enumerate(names)]}


class WholeShapes(unittest.TestCase):
    PROFILE = {'ratio': .3, 'preserve_shape_prefixes': ['Tri floor']}

    @unittest.skipUnless(GEOMETRY, 'optional geometry dependencies')
    def test_exact_name_kept_whole_its_prefix_neighbour_reduced(self):
        from static_lod import profile_reduction, reduce_for_profile, reduce_mesh
        v, f = plates()
        model = model_of(['Tri mast', 'Tri mast01', 'Tri floor 0'])
        view, profile, receipt = S.whole_shape_view(model, self.PROFILE, ['tri MAST'])
        self.assertEqual(receipt, {'shapes': ['tri MAST'], 'materials': [0], 'source_faces': 162})
        out_v, out_f, details = reduce_for_profile(v, f, profile, view['materials'], 'fixture')
        counts = [int((out_f[:, 3] == k).sum()) for k in range(3)]
        self.assertEqual(counts[0], 162)            # the mast whole
        self.assertLess(counts[1], 162)             # 'Tri mast01' still reduced: a prefix would have kept it
        self.assertEqual(counts[2], 162)            # the profile's own prefix keep is untouched
        self.assertEqual(details['preserved_materials'], [0, 2])
        # the same as an exact-name keep in the shared reducer
        ref_v, ref_f, _ = reduce_mesh(v, f, .3, {0, 2}, **profile_reduction(self.PROFILE))
        np.testing.assert_array_equal(out_f, ref_f)
        np.testing.assert_array_equal(out_v, ref_v)
        # the scenery index's record and the profile are not changed
        self.assertEqual(model['materials'][0]['source_shape'], 'Tri mast')
        self.assertEqual(self.PROFILE['preserve_shape_prefixes'], ['Tri floor'])

    def test_missing_shape_refused_and_nothing_to_do(self):
        model = model_of(['Tri mast', 'Tri mast01'])
        with self.assertRaises(ValueError):
            S.whole_shape_view(model, self.PROFILE, ['Tri mast02'])
        self.assertEqual(S.whole_shape_view(model, self.PROFILE, ()), (model, self.PROFILE, {}))
        self.assertEqual(S.whole_shape_view(model, {}, ['Tri mast']), (model, {}, {}))

    def test_switch_and_tables(self):
        old = os.environ.pop(S.ROOM_SHAPES_VARIABLE, None)
        try:
            shell = 'meshes/i/in_prison_ship.nif'
            self.assertEqual(S.room_shapes(), 'on')
            self.assertIn('Tri mast', S.whole_shapes(shell))
            self.assertIn('Tri LLmast', S.whole_shapes(shell))
            self.assertNotIn('Tri mast01', S.whole_shapes(shell))
            for name in S.box_shapes(shell):
                self.assertIn(name, S.whole_shapes(shell))    # boxed shapes are kept whole first
            self.assertEqual(S.whole_shapes('meshes/f/other.nif'), ())
            self.assertEqual(S.export_room_shapes('off'), 'off')
            self.assertEqual((S.whole_shapes(shell), S.box_shapes(shell)), ((), ()))
            self.assertEqual(S.export_room_shapes(None), 'on')
            with self.assertRaises(ValueError):
                S.export_room_shapes('box')
        finally:
            os.environ.pop(S.ROOM_SHAPES_VARIABLE, None)
            if old is not None:
                os.environ[S.ROOM_SHAPES_VARIABLE] = old


class BoxShapes(unittest.TestCase):
    def test_band_drawn_as_its_box(self):
        from room_map_parts import box_polygons
        top = box_polygons(np.array([0., 0, 0]), np.array([40., 30, 2]), 0, .05, 1)
        # a band of two joined halves (12 faces, one part) in material 1, raised to the slanted 'tent' it must not be
        band = (box_polygons(np.array([10., -1, -.5]), np.array([14., 15, 2.5]), 1, .1, 1) +
                box_polygons(np.array([10., 15, -.5]), np.array([14., 31, 2.5]), 1, .1, 1))
        record = (None, None, top + band, ['piece'], {'x': 1})
        model = {'source': 'meshes/x/table.nif', 'materials': [{'source_shape': 'Tri top 0'}, {'source_shape': 'Tri band 1'}]}
        (_, _, polys, parts, lod), receipt = S.box_shape_parts(record, model, ['Tri band 1'])
        self.assertEqual(receipt, {'shapes': ['Tri band 1'], 'parts_boxed': 1, 'faces_before': 12, 'faces_after': 6})
        self.assertEqual(lod['box_shapes'], receipt)
        self.assertEqual(parts, ['piece'])
        self.assertEqual(len(polys), 12)
        self.assertTrue(all(a is b for a, b in zip(polys[:6], top)))       # other shapes untouched
        pts = np.concatenate([p[0] for p in polys[6:]])
        np.testing.assert_allclose(pts.min(0), [10, -1, -.5])               # spans the band exactly
        np.testing.assert_allclose(pts.max(0), [14, 31, 2.5])
        self.assertTrue(all(p[1] == 1 for p in polys[6:]))
        same, receipt = S.box_shape_parts(record, model, ())
        self.assertIs(same, record)
        self.assertEqual(receipt, {})


def column(lo, hi):
    """The six faces of the box lo..hi as triangles (12 x 3 x 3)."""
    from room_map_parts import box_polygons
    from drawn_collision import polygon_triangles
    return np.array([t for p in box_polygons(np.asarray(lo, float), np.asarray(hi, float), 0, 1., 1)
                     for t in polygon_triangles(p[0])])


def corners(lo, hi):
    return np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])], float)


def as_record(drawn_tris, source_tris, pieces):
    """A prepared model record from source triangles (the record's v, f), drawn triangles (its polygons) and the
    collision boxes PIECES."""
    src = np.asarray(source_tris, float).reshape(-1, 3)
    v = np.column_stack((src, np.zeros((len(src), 6))))
    f = np.column_stack((np.arange(len(src)).reshape(-1, 3), np.zeros(len(src) // 3, int)))
    polys = [(t, 0, np.zeros((3, 2)), np.zeros(2), np.array([0., 0, 1])) for t in drawn_tris]
    return (v, f, polys, [(corners(lo, hi), None, [], 0.) for lo, hi in pieces], {})


@unittest.skipUnless(GEOMETRY, 'optional geometry dependencies')
class DrawnCollision(unittest.TestCase):
    FLOOR = ([0, 0, -.5], [40, 40, 0])
    POST = ([18, 18, 0], [22, 22, 40])       # 40 units: over the step height
    BLOCK = ([30, 5, 0], [34, 9, 8])          # 8 units: under it
    HIDDEN = ([5, 30, 0], [9, 34, 40])        # an authored blocker the original does not draw either

    def setUp(self):
        import drawn_collision as D
        self.D = D
        self.source = np.concatenate([column(*self.FLOOR), column(*self.POST), column(*self.BLOCK)])
        self.pieces = [self.FLOOR, self.POST, self.BLOCK, self.HIDDEN]

    def lost(self, drawn):
        return self.D.lost_pieces(as_record(drawn, self.source, self.pieces), source_scale=1.)

    def test_invisible_post_is_lost_and_standing(self):
        receipt = self.lost(column(*self.FLOOR))
        self.assertEqual(receipt['source_drawn'], 3)                         # the hidden blocker is not counted
        self.assertEqual([(row['piece'], row['standing']) for row in receipt['lost']], [(1, True), (2, False)])
        self.assertEqual(receipt['standing'], 1)
        self.assertGreater(receipt['lost'][0]['source_share'], .9)
        self.assertLess(receipt['lost'][0]['drawn_share'], .3)

    def test_drawn_post_is_kept(self):
        receipt = self.lost(np.concatenate([column(*self.FLOOR), column(*self.POST), column(*self.BLOCK)]))
        self.assertEqual((receipt['lost'], receipt['standing']), ([], 0))

    def test_room_check_message_only_when_a_piece_stands(self):
        index = {'models': [{'source': 'meshes/x/hold.nif', 'materials': [{'source_shape': 'Tri post'}]}],
                 'references': [{'model_index': 0, 'position': [400., 0, 0]}]}
        # the source in its own units (4 to a map unit), the pieces and the drawn faces in map units, as prepared
        record = as_record(column(*self.FLOOR), self.source * 4, self.pieces)
        receipt, message = self.D.check_room({0: record}, index)
        self.assertEqual((receipt['lost'], receipt['standing']), (2, 1))
        self.assertIn('meshes/x/hold.nif', receipt['by_model'])
        self.assertIn('standing piece 1 at [118.0, 18.0, 0.0]', message)   # map units at the placement
        self.assertIn('low piece 2 at', message)
        drawn = np.concatenate([column(*self.FLOOR), column(*self.POST)])
        record = as_record(drawn, self.source * 4, self.pieces)
        receipt, message = self.D.check_room({0: record}, index)
        self.assertEqual((receipt['lost'], receipt['standing'], message), (1, 0, ''))

    def test_collision_only_and_empty(self):
        self.assertEqual(self.D.lost_pieces((None, None, [], [], {}))['lost'], [])
        record = as_record([], self.source, self.pieces)
        record[4]['representation'] = 'collision_only'
        self.assertEqual(self.D.lost_pieces(record)['lost'], [])


class Wiring(unittest.TestCase):
    def test_the_hold_stage_checks_and_refuses(self):
        text = (ROOT / 'tools' / 'prepare_interior.py').read_text(encoding='utf-8')
        self.assertIn('check_room(prepared,index)', text)
        self.assertIn("if message and room_shapes_mode()=='on':raise ValueError", text)
        self.assertLess(text.index('check_room(prepared,index)'), text.index('report=append_meshes('))
        text = (ROOT / 'tools' / 'room_map_collision.py').read_text(encoding='utf-8')
        self.assertIn('whole_shape_view(', text)
        self.assertIn('box_shape_parts(', text)


if __name__ == '__main__':
    unittest.main()
