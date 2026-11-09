"""MESH-SEAM-METHOD-62: the seam check's join map, limb thickness at 25 / 50 / 75 % and the bake stop."""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]

import numpy as np  # noqa: E402
import mesh_seam_check as msc  # noqa: E402
import npc_geometry as ng  # noqa: E402
from test_npc_body_share import box  # noqa: E402


def whole(shapes):
    frame = np.concatenate([s['positions'][0] for s in shapes])
    offs = np.cumsum([0] + [len(s['positions'][0]) for s in shapes])
    faces = np.concatenate([s['faces'] + offs[i] for i, s in enumerate(shapes)])
    owner = np.concatenate([[i] * len(s['faces']) for i, s in enumerate(shapes)])
    return frame, faces, owner


class JoinMap(unittest.TestCase):
    def setUp(self):
        self.shapes = [box(21, (-1, -1, 10), (1, 1, 20), 'upper', 4, caps=False),
                       box(19, (-1, -1, 0), (1, 1, 10), 'lower', 4, caps=False)]

    def test_every_join_listed_closed(self):
        frame, faces, _ = whole(self.shapes)
        joins = msc.join_map(self.shapes, frame, faces)
        self.assertEqual({(j['a'], j['b']) for j in joins}, {('upper', 'lower'), ('lower', 'upper')})
        self.assertTrue(all(j['length'] > 7 and j['open_length'] == 0 for j in joins))

    def test_pulled_part_opens_its_join(self):
        frame, faces, _ = whole(self.shapes)
        n = len(self.shapes[0]['positions'][0])
        frame = frame.copy(); frame[n:, 2] -= 2.0
        joins = msc.join_map(self.shapes, frame, faces)
        # the gap is measured at the inset point (a lower bound: the upper part's rim is 0.5 from it)
        self.assertTrue(any(j['a'] == 'lower' and j['open_length'] == j['length'] and j['max_gap'] > 0.25
                            for j in joins))


class Thickness(unittest.TestCase):
    def setUp(self):
        self.leg = box(21, (-1, -1, 0), (1, 1, 20), 'leg', 6, caps=False)

    def test_whole_limb_keeps_one(self):
        frame, faces, owner = whole([self.leg])
        prof = msc.limb_thickness([self.leg], frame, faces, owner)
        self.assertEqual(set(prof['leg']), set(msc.STATIONS))
        self.assertTrue(all(abs(v - 1.0) < 0.05 for v in prof['leg'].values()))

    def test_pinched_middle_is_caught(self):
        frame, faces, owner = whole([self.leg])
        frame = frame.copy()
        mid = np.abs(frame[:, 2] - 10) < 4
        frame[mid, :2] *= 0.3                 # the middle third squeezed to 0.3 of its width
        prof = msc.limb_thickness([self.leg], frame, faces, owner)['leg']
        self.assertLess(prof[50], 0.5)
        self.assertGreater(prof[25], 0.5)
        self.assertLess(msc.least_thickness({'leg': prof}), 0.5)

    def test_audit_receipt(self):
        frame, faces, owner = whole([self.leg])
        rep = msc.audit([self.leg], frame, faces)
        self.assertEqual(rep['new'], 0)
        self.assertIn('leg', rep['thickness'])
        self.assertGreaterEqual(rep['least_thickness'], 0.95)


class ToolkitPage(unittest.TestCase):
    """amiwind-toolkit/seam-check.html shows the receipt the tool and the NPC bake write."""
    def test_page_reads_the_receipt_fields(self):
        page = (ROOT / 'amiwind-toolkit' / 'seam-check.html').read_text(encoding='utf-8')
        self.assertIn('header.js', page)
        leg = box(21, (-1, -1, 0), (1, 1, 20), 'leg', 6, caps=False)
        frame, faces, _ = whole([leg])
        for key in msc.audit([leg], frame, faces):
            if key in ('reduced_open', 'source_open', 'new', 'new_at', 'joins', 'thickness', 'least_thickness'):
                self.assertIn('r.' + key, page, key)
        for key in ('uncovered_openings', 'covered_openings', 'uncovered_at', 'limb_thickness', 'least_width'):
            self.assertIn('r.' + key, page, key)
        files = (ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8')
        self.assertIn('"amiwind-toolkit/seam-check.html"', files)


class WornMerge(unittest.TestCase):
    """Armoured outfits: the worn pieces of one limb slot are one shape before reducing, faces keep their materials."""
    def test_merge(self):
        a = dict(box(13, (0, 0, 0), (1, 1, 1), 'Tri A_Pauldron 0', 2), material=3, uv=np.zeros((54, 2)),
                 colours=np.ones((54, 4)))
        b = dict(box(13, (0, 0, 1), (1, 1, 2), 'Tri A_Pauldron 1', 2), material=4, uv=np.zeros((54, 2)),
                 colours=np.ones((54, 4)))
        skin = dict(box(13, (0, 0, 0), (1, 1, 2), 'B_N_Nord_M_Upper Arm', 2), material=1, uv=np.zeros((54, 2)),
                    colours=np.ones((54, 4)))
        other = dict(box(3, (0, 0, 0), (1, 1, 1), 'Tri A_Cuirass 0', 2), material=5, uv=np.zeros((54, 2)),
                     colours=np.ones((54, 4)))
        out, merged = ng.merge_worn_pieces([a, skin, b, other])
        self.assertEqual(len(out), 3)
        m = [s for s in out if 'merged' in s['name']][0]
        self.assertEqual(len(m['faces']), len(a['faces']) + len(b['faces']))
        self.assertEqual(sorted(set(m['face_material'].tolist())), [3, 4])
        self.assertEqual(merged[m['name']], ['Tri A_Pauldron 0', 'Tri A_Pauldron 1'])
        self.assertTrue(any(s['name'] == 'B_N_Nord_M_Upper Arm' for s in out))
        self.assertTrue(any(s['name'] == 'Tri A_Cuirass 0' for s in out))   # not a limb slot: unchanged
        verts, faces = ng.combined(out)
        self.assertEqual(sorted(set(faces[:, 3].tolist())), [1, 3, 4, 5])


class HeadFloors(unittest.TestCase):
    """config/model-head-floors.json: a lower head trim floor per body, as data, only from a passing measurement."""
    def test_shipped_file_is_valid(self):
        import model_face_overrides as mfo
        floors = mfo.load_head_floors()
        for name, e in floors.items():
            self.assertLess(e['head_floor'], ng.HEAD_TRIM_FLOOR)
            self.assertLessEqual(e['cost']['total'], e['cost']['before'])
        self.assertIsNone(mfo.head_floor('a body without an entry'))

    def test_failing_measurement_refused(self):
        import json, tempfile
        import model_face_overrides as mfo
        bad = {'schema': 1, 'entries': [{'body': 'h|r', 'head_floor': 90, 'reason': 'r',
                                         'cost': {'before': 500, 'total': 498},
                                         'measured': {'uncovered_openings': 2, 'least_width': 0.7}}]}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'f.json'
            p.write_text(json.dumps(bad))
            with self.assertRaises(ValueError):
                mfo.load_head_floors(p)
            bad['entries'][0]['measured']['uncovered_openings'] = 0
            bad['entries'][0]['cost']['total'] = 510          # added faces: refused
            p.write_text(json.dumps(bad)); mfo._cache.clear()
            with self.assertRaises(ValueError):
                mfo.load_head_floors(p)
        mfo._cache.clear()


class BakeStop(unittest.TestCase):
    def setUp(self):
        self.old = os.environ.get('AMIWIND_MESH_SEAM_STOP')

    def tearDown(self):
        if self.old is None:
            os.environ.pop('AMIWIND_MESH_SEAM_STOP', None)
        else:
            os.environ['AMIWIND_MESH_SEAM_STOP'] = self.old

    def test_pass_is_silent(self):
        os.environ.pop('AMIWIND_MESH_SEAM_STOP', None)
        self.assertEqual(ng.seam_stop('jiub', 0, 0.6, False, baseline={}), 'passing')

    def test_opening_stops(self):
        os.environ.pop('AMIWIND_MESH_SEAM_STOP', None)
        with self.assertRaises(ng.BakeStop):
            ng.seam_stop('x', 1, 0.9, False, baseline={})

    def test_thin_limb_stops(self):
        os.environ.pop('AMIWIND_MESH_SEAM_STOP', None)
        with self.assertRaises(ng.BakeStop):
            ng.seam_stop('x', 0, 0.49, False, baseline={})

    def test_stop_is_not_a_value_error(self):
        # the budget ladders catch ValueError for a rung that does not fit; the stop must never be taken for one
        self.assertFalse(issubclass(ng.BakeStop, ValueError))

    def test_entry_passes(self):
        os.environ.pop('AMIWIND_MESH_SEAM_STOP', None)
        self.assertEqual(ng.seam_stop('nels llendo', 3, 0.3, True, baseline={}), 'entry')

    def test_head_rims_setting(self):
        old = os.environ.pop('AMIWIND_NPC_HEAD_RIMS', None)
        try:
            self.assertTrue(ng.head_rims_locked())
            os.environ['AMIWIND_NPC_HEAD_RIMS'] = 'pushed'
            self.assertFalse(ng.head_rims_locked())
            os.environ['AMIWIND_NPC_HEAD_RIMS'] = 'loose'
            with self.assertRaises(ValueError):
                ng.head_rims_locked()
        finally:
            os.environ.pop('AMIWIND_NPC_HEAD_RIMS', None)
            if old is not None:
                os.environ['AMIWIND_NPC_HEAD_RIMS'] = old

    def test_warn_mode(self):
        os.environ['AMIWIND_MESH_SEAM_STOP'] = 'warn'
        self.assertEqual(ng.seam_stop('x', 2, 0.9, False, baseline={}), 'new')

    def test_ratchet(self):
        os.environ.pop('AMIWIND_MESH_SEAM_STOP', None)
        base = {'npc:x': {'uncovered': 3, 'least_width': 0.45, 'date': '2026-11-07'}}
        self.assertEqual(ng.seam_stop('x', 3, 0.45, False, baseline=base), 'baselined')
        self.assertEqual(ng.seam_stop('x', 1, 0.6, False, baseline=base), 'baselined')
        self.assertEqual(ng.seam_stop('x', 0, 0.6, False, baseline=base), 'passing')
        with self.assertRaises(ng.BakeStop):
            ng.seam_stop('x', 4, 0.45, False, baseline=base)          # more openings: worse
        with self.assertRaises(ng.BakeStop):
            ng.seam_stop('x', 3, 0.40, False, baseline=base)          # thinner: worse
        with self.assertRaises(ng.BakeStop):
            ng.seam_stop('y', 1, 0.9, False, baseline=base)           # not in the baseline: new
        os.environ['AMIWIND_MESH_SEAM_STOP'] = 'fail'
        with self.assertRaises(ng.BakeStop):
            ng.seam_stop('x', 3, 0.45, False, baseline=base)          # fail mode stops a baselined model too

    def test_baseline_tool_only_shrinks(self):
        import mesh_seam_baseline as msb
        old = msb.lines_from([{'kind': 'npc', 'model': 'a', 'uncovered': 2, 'least_width': 0.7}])
        self.assertEqual(msb.ratchet(old, msb.lines_from([{'kind': 'npc', 'model': 'a', 'uncovered': 1,
                                                            'least_width': 0.7}])), [])
        self.assertTrue(msb.ratchet(old, msb.lines_from([{'kind': 'npc', 'model': 'b', 'uncovered': 1,
                                                           'least_width': 0.7}])))
        self.assertEqual(msb.lines_from([{'kind': 'npc', 'model': 'a', 'uncovered': 0, 'least_width': 0.7}]), {})

    def test_shipped_baseline_is_valid(self):
        import model_face_overrides as mfo
        for key, line in mfo.load_seam_baseline().items():
            self.assertIn(key.split(':', 1)[0], ('npc', 'creature'))


if __name__ == '__main__':
    unittest.main()
