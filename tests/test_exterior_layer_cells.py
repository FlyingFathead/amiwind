# SPDX-License-Identifier: GPL-3.0-only
"""Layer cells: CHIM region cells outside the base game's exterior grid (an expansion's own cells; the cells an
interior that behaves like an exterior is presented as). The exterior checklist plans each as a row of its own and
the world terrain planner appends its directory row after every existing row; without such a cell everything is
exactly as before. Small synthetic data: no game data."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tests'))
import exterior_plan as ep  # noqa: E402
from chim.ocean_runtime import append_layer_rows  # noqa: E402
from test_presented_exterior import exterior, header, ref  # noqa: E402

BASE = [(0, 0), (1, 0)]
DISTRICT = [(0, -30), (4, -30)]


def entry(index, cell):
    x, y = cell
    return {'name': 'vf%04d' % index, 'cell': [x, y], 'origin': [x * 2048 + 1024, y * 2048 + 1024, 12.0],
            'core': [[-1024, -1024], [1024, 1024]], 'coverage': [[-1920, -1920], [1920, 1920]], 'divisions': 1}


class Checklist(unittest.TestCase):
    def test_without_a_layer_cell_the_checklist_is_the_one_before(self):
        plain = ep.make(BASE, [(0, 0)], (), 'sha')
        self.assertEqual(ep.make(BASE, [(0, 0)], (), 'sha', layer_cells=()), plain)
        self.assertNotIn('layer_cells', plain)

    def test_a_layer_cell_is_a_chim_region_row_of_its_own(self):
        plan = ep.make(BASE, [(0, 0)] + DISTRICT, (), 'sha', layer_cells=DISTRICT)
        rows = {tuple(r['cell']): r['format'] for r in plan['cells']}
        self.assertEqual(rows, {(0, 0): 'chim-region', (1, 0): 'bsp', (0, -30): 'chim-region',
                                (4, -30): 'chim-region'})
        self.assertEqual(plan['layer_cells'], [[0, -30], [4, -30]])
        self.assertEqual(plan['summary'], {'bsp': 1, 'chim-region': 3, 'chim-town': 0})
        self.assertEqual(ep.validate(plan), plan)

    def test_a_cell_off_the_grid_that_is_no_layer_cell_is_still_refused(self):
        with self.assertRaisesRegex(ValueError, 'without an open-world map'):
            ep.make(BASE, [(0, 0)] + DISTRICT, (), 'sha', layer_cells=DISTRICT[:1])
        with self.assertRaisesRegex(ValueError, 'not selected for CHIM'):
            ep.make(BASE, [(0, 0)], (), 'sha', layer_cells=DISTRICT)
        with self.assertRaisesRegex(ValueError, 'also taken as ocean'):
            ep.make(BASE, [(0, 0)] + DISTRICT, (), 'sha', ocean_cells=DISTRICT[:1], layer_cells=DISTRICT)

    def test_the_survey_does_not_hold_layer_cells_before_the_rows_are_appended(self):
        plan = ep.make(BASE, [(0, 0)] + DISTRICT, (), 'sha', layer_cells=DISTRICT)
        survey = [entry(i, cell) for i, cell in enumerate(BASE)]
        kinds = ep.classify_regions(plan, survey, 'sha', [(0, 0)] + DISTRICT, before_ocean_routing=True)
        self.assertEqual(kinds, {'vf0000': 'chim-region', 'vf0001': 'bsp'})
        with self.assertRaisesRegex(ValueError, 'differ from the exterior checklist'):
            ep.classify_regions(plan, survey, 'sha', [(0, 0)] + DISTRICT)
        entries, added = append_layer_rows(survey, DISTRICT)
        rows = [dict(e, chim_region=True) if tuple(e['cell']) in {(0, 0), *DISTRICT} else e for e in entries]
        after = ep.classify_regions(plan, rows, 'sha', [(0, 0)] + DISTRICT)
        self.assertEqual(after['vf0002'], 'chim-region')
        self.assertEqual(after['vf0003'], 'chim-region')


class Rows(unittest.TestCase):
    def test_rows_come_after_every_existing_row_which_stays_as_it_is(self):
        survey = [entry(i, cell) for i, cell in enumerate(BASE)]
        before = [dict(e) for e in survey]
        entries, added = append_layer_rows(survey, reversed(DISTRICT))
        self.assertEqual(entries[:2], before)
        self.assertEqual([e['name'] for e in added], ['vf0002', 'vf0003'])
        self.assertEqual([e['cell'] for e in added], [[0, -30], [4, -30]])       # by cell, whatever the order given
        row = added[0]
        self.assertEqual((row['origin'], row['core'], row['chim_region'], row['layer_cell'], row['converted']),
                         ([1024, -30 * 2048 + 1024, 0.0], [[-1024, -1024], [1024, 1024]], True, True, None))
        self.assertNotIn('ocean_runtime', row)
        self.assertEqual(append_layer_rows(survey, ()), (before, []))

    def test_a_mournhold_row_added_or_changed_moves_no_vvardenfell_region(self):
        """Mournhold is its own small map, not connected to Vvardenfell's: a world scenery or world flora region unit
        is keyed by its own directory row (tools/prepare_world_scenery.py convert_region_cached: inputs 'entry' and
        the shared export), so the rows of the island must be the same objects' worth of data whatever layer rows
        follow them, and a layer row is never a region these stages convert (it is a CHIM region row)."""
        from exterior_plan import no_legacy_map
        survey = [entry(i, cell) for i, cell in enumerate(BASE)]
        before = json.dumps(survey, sort_keys=True)
        for cells in (DISTRICT, DISTRICT[:1], [(9, -30)], ()):
            entries, added = append_layer_rows([dict(e) for e in survey], cells)
            self.assertEqual(json.dumps(entries[:len(survey)], sort_keys=True), before, cells)
            self.assertTrue(all(no_legacy_map(row) for row in added), cells)

    def test_a_cell_that_has_a_row_or_a_broken_directory_is_refused(self):
        survey = [entry(i, cell) for i, cell in enumerate(BASE)]
        with self.assertRaisesRegex(ValueError, 'already has a core owner vf0001'):
            append_layer_rows(survey, [(1, 0)])
        with self.assertRaisesRegex(ValueError, 'complete sequential'):
            append_layer_rows(survey[1:], DISTRICT)


class LayerCells(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        raw = header(2) + exterior(0, 0, ref(1, 'wall', (1, 2, 3))) + exterior(1, 0)
        (self.data / 'Morrowind.esm').write_bytes(raw)
        ep._GRIDS.clear()

    def tearDown(self):
        ep._GRIDS.clear()
        self.tmp.cleanup()

    def test_the_cells_off_the_base_grid_that_are_no_ocean(self):
        kinds = {(0, 0): 'land', (0, -30): 'land', (-20, 25): 'seabed', (9, 9): 'ocean'}
        masters = ['Morrowind.esm', 'Tribunal.esm']
        self.assertEqual(ep.layer_cells(kinds, self.data, masters), [(-20, 25), (0, -30)])
        self.assertEqual(ep.layer_cells({(0, 0): 'land', (1, 0): 'land'}, self.data, masters), [])

    def test_the_base_game_alone_has_none_and_reads_nothing(self):
        self.assertEqual(ep.layer_cells({(0, -30): 'land'}, self.data / 'missing', ['Morrowind.esm']), [])
        self.assertEqual(ep.layer_cells({}, self.data / 'missing', ['Morrowind.esm', 'Tribunal.esm']), [])


if __name__ == '__main__':
    unittest.main()
