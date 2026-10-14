import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import cell_progress_map as M


def cell(x, y, bucket, land=True, island=1, plan=None, name=''):
    return {'x': x, 'y': y, 'land': land, 'island': island, 'chim': {'bucket': bucket}, 'plan': plan, 'name': name}


class CellProgressMapTest(unittest.TestCase):
    def test_categories(self):
        self.assertEqual(M.category(cell(0, 0, 'audits_passed')), 'done')
        self.assertEqual(M.category(cell(0, 0, 'empty_sea')), 'done')
        self.assertEqual(M.category(cell(0, 0, 'hull_policy_pending')), 'pending')
        self.assertEqual(M.category(cell(0, 0, 'converted_failing')), 'failing')
        self.assertEqual(M.category(cell(0, 0, 'ocean')), 'ocean')
        self.assertEqual(M.category(cell(0, 0, 'not_started')), 'not_started')
        self.assertEqual(M.category({'chim': {}}), 'none')

    def test_summary_counts_the_headline(self):
        data = {'cells': {
            '0,0': cell(0, 0, 'audits_passed'), '1,0': cell(1, 0, 'hull_policy_pending', plan={'state': 'planned'}),
            '2,0': cell(2, 0, 'ocean', land=False), '3,0': cell(3, 0, 'not_started', island=2)}}
        s = M.summarize(data)
        self.assertEqual((s['land'], s['done'], s['planned'], s['ocean'], s['solstheim']), (2, 1, 1, 1, 1))

    def test_reference_keeps_audits_separate_from_release_assignment(self):
        ref = {'format': 'aw-cell-reference-1', 'generated': '2026-10-12T22:32:16+00:00', 'cells': {
            '0,0': {'status': 'audits_passed', 'island': 1, 'release': 'v0.0.38'},
            '1,0': {'status': 'empty_sea', 'island': 1},
            '2,0': {'status': 'ocean', 'island': 1},
            '3,0': {'status': 'not_converted', 'island': 1},
            '4,0': {'status': 'not_started', 'island': 2}}}
        data = M.map_data(ref)
        s = M.summarize(data)
        self.assertEqual((s['land'], s['done'], s['planned'], s['ocean'], s['solstheim']), (3, 2, 0, 1, 1))
        self.assertEqual(data['generated'], ref['generated'])
        self.assertEqual(data['cells']['4,0']['x'], 4)
        self.assertEqual(ref['cells']['0,0']['release'], 'v0.0.38')

    def test_tracker_plan_is_preserved_and_unknown_input_rejected(self):
        data = {'format': 'aw-cell-progress-1', 'cells': {
            '0,0': cell(0, 0, 'converted_failing', plan={'state': 'planned'})}}
        self.assertIs(M.map_data(data), data)
        self.assertEqual(M.summarize(M.map_data(data))['planned'], 1)
        with self.assertRaises(ValueError):
            M.map_data({'format': 'unrecognized', 'cells': {}})


if __name__ == '__main__':
    unittest.main()
