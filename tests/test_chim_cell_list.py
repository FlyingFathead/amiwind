# SPDX-License-Identifier: GPL-3.0-only
"""tools/chim_cell_list.py: cell lists from the tracker's rings; kept CHIM cells never dropped silently."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import chim_cell_list as L  # noqa: E402


class ChimCellListTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        cells = {'1,1': dict(ring=1, island=1), '2,2': dict(ring=2, island=1), '3,3': dict(ring=3, island=1),
                 '9,0': dict(ring=9, island=1), '1,30': dict(ring=1, island=2)}
        (self.tmp / 'progress.json').write_text(json.dumps({'cells': cells}))
        (self.tmp / 'prev.json').write_text(json.dumps({'format': 'aw-chim-cells-1', 'cells': [[9, 0], [1, 1]]}))
        (self.tmp / 'scenery.json').write_text(json.dumps({'chim_region_cells': [[9, 0]]}))

    def test_rings_plus_kept_cells(self):
        doc, lines = L.make(self.tmp / 'progress.json', '1-2', keep=[self.tmp / 'prev.json'], reason='r')
        self.assertEqual(doc['cells'], [[1, 1], [2, 2], [9, 0]])
        self.assertEqual(doc['format'], 'aw-chim-cells-1')
        self.assertIn('keep prev.json: 2 cells already on CHIM, 1 outside the rings', lines)

    def test_regions_select_every_cell_of_a_region(self):
        cells = {'1,1': dict(ring=1, island=1, region='Bitter Coast Region'),
                 '5,5': dict(ring=6, island=1, region={'name': 'Bitter Coast Region'}),
                 '2,2': dict(ring=2, island=1, region='West Gash Region'),
                 '1,30': dict(ring=1, island=2, region='Bitter Coast Region')}
        (self.tmp / 'regions.json').write_text(json.dumps({'cells': cells}))
        doc, lines = L.make(self.tmp / 'regions.json', None, regions=['Bitter Coast Region'])
        self.assertEqual(doc['cells'], [[1, 1], [5, 5]])
        self.assertIn('region Bitter Coast Region: 2 cells, 2 new', lines)
        with self.assertRaises(ValueError):
            L.make(self.tmp / 'regions.json', None, regions=['Nowhere Region'])
        with self.assertRaises(ValueError):
            L.make(self.tmp / 'regions.json', None)

    def test_a_batch_file_alone_with_the_kept_cells(self):
        # the easy CHIMport batch: tools/chim_weight_table.py --cells-out, no rings or regions
        (self.tmp / 'batch.json').write_text(json.dumps({'format': 'aw-chim-cells-1', 'cells': [[3, 3]]}))
        doc, lines = L.make(self.tmp / 'progress.json', None, include=[self.tmp / 'batch.json'],
                            keep=[self.tmp / 'prev.json'])
        self.assertEqual(doc['cells'], [[1, 1], [3, 3], [9, 0]])
        self.assertIn('include batch.json: 1 cells, 1 new', lines)

    def test_run_receipt_as_keep_source(self):
        doc, _ = L.make(self.tmp / 'progress.json', '1', keep=[self.tmp / 'scenery.json'])
        self.assertEqual(doc['cells'], [[1, 1], [9, 0]])

    def test_drop_needs_a_reason_and_a_kept_cell(self):
        with self.assertRaisesRegex(ValueError, 'needs a reason'):
            L.make(self.tmp / 'progress.json', '1-2', keep=[self.tmp / 'prev.json'], drop={'9,0': ''})
        with self.assertRaisesRegex(ValueError, 'not kept cells'):
            L.make(self.tmp / 'progress.json', '1-2', keep=[self.tmp / 'prev.json'], drop={'3,3': 'x'})
        doc, lines = L.make(self.tmp / 'progress.json', '1-2', keep=[self.tmp / 'prev.json'], drop={'9,0': 'test'})
        self.assertNotIn([9, 0], doc['cells'])
        self.assertIn('DROPPED 9,0 from CHIM: test', lines)

    def test_leave_out_names_unfinished_ring_cells_only(self):
        doc, lines = L.make(self.tmp / 'progress.json', '1-3', keep=[self.tmp / 'prev.json'],
                            leave_out={'3,3': 'failing audits (memory_fit)'})
        self.assertEqual(doc['cells'], [[1, 1], [2, 2], [9, 0]])
        self.assertIn('left out 3,3: failing audits (memory_fit)', lines)
        with self.assertRaisesRegex(ValueError, 'already on CHIM'):
            L.make(self.tmp / 'progress.json', '1-3', keep=[self.tmp / 'prev.json'], leave_out={'9,0': 'x'})
        with self.assertRaisesRegex(ValueError, 'needs a reason'):
            L.make(self.tmp / 'progress.json', '1-3', leave_out={'3,3': ''})

    def test_open_pockets_leaves_out_the_outermost_neighbour(self):
        from chim.regions import holes
        cells = {'%d,%d' % (x, y): dict(ring=(2 if x == 1 else 1), island=1) for x in range(-1, 2) for y in range(-1, 2)}
        (self.tmp / 'grid.json').write_text(json.dumps({'cells': cells}))
        doc, lines = L.make(self.tmp / 'grid.json', '1-2', leave_out={'0,0': 'failing audits'}, open_pockets=True)
        left = [l for l in lines if 'opens the legacy pocket 0,0' in l]
        self.assertEqual(len(left), 1)
        self.assertTrue(left[0].startswith('left out 1,'))     # ring 2 goes first
        self.assertEqual(holes([tuple(c) for c in doc['cells']]), [])

    def test_town_cells_count_as_chim_in_the_pocket_test(self):
        # CHIM-REGION-POCKET-TOWN-CELLS-42: (0,0) lies wholly inside a town frame; the ring round it opens nothing
        cells = {'%d,%d' % (x, y): dict(ring=1, island=1) for x in range(-1, 2) for y in range(-1, 2) if (x, y) != (0, 0)}
        (self.tmp / 'grid.json').write_text(json.dumps({'cells': cells}))
        (self.tmp / 'town.json').write_text(json.dumps({'format': 'aw-chim-cells-1', 'cells': [[0, 0]]}))
        doc, lines = L.make(self.tmp / 'grid.json', '1', open_pockets=True, covered=[self.tmp / 'town.json'])
        self.assertFalse([l for l in lines if 'opens the legacy pocket' in l])
        self.assertEqual(len(doc['cells']), 8)
        self.assertNotIn([0, 0], doc['cells'])
        doc, lines = L.make(self.tmp / 'grid.json', '1', open_pockets=True)
        self.assertTrue([l for l in lines if 'opens the legacy pocket 0,0' in l])

    def test_cli_refuses_with_exit_2(self):
        out = self.tmp / 'out.json'
        self.assertEqual(L.main(['--progress', str(self.tmp / 'progress.json'), '--rings', '1-2', '--keep',
                                 str(self.tmp / 'prev.json'), '--drop', '9,0=', '--out', str(out)]), 2)
        self.assertFalse(out.exists())

    def test_classic_cells_name_open_sea_cells_with_a_cell_record(self):
        """CHIM-OCEAN-CELL-RECORD-CLASSIC-43: cells left classic are counted by tracker status; ocean cells
        that the master still lists (a CELL record, no LAND) are named apart, town-covered cells are not left."""
        cells = {'1,1': dict(island=1, status='terrain_complete_unlit'), '2,2': dict(island=1, status='ocean'),
                 '3,3': dict(island=1, status='converted_failing'), '4,4': dict(island=1, status='audits_passed'),
                 '1,30': dict(island=2, status='not_started')}
        (self.tmp / 'status.json').write_text(json.dumps({'cells': cells}))
        lines = L.classic_cells([(1, 1), (2, 2), (3, 3), (4, 4), (1, 30)], {'1,1'}, {'4,4'},
                                self.tmp / 'status.json')
        self.assertEqual(lines[0], 'classic: 2 exterior cell(s) of island 1 stay on the classic open world with '
                                   'this list; converted_failing 1; ocean 1')
        self.assertIn('classic converted_failing: 3,3', lines)
        self.assertTrue(any(line.startswith('classic ocean: 2,2 (open sea with a CELL record') for line in lines))


if __name__ == '__main__':
    unittest.main()
