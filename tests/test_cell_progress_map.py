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


if __name__ == '__main__':
    unittest.main()
