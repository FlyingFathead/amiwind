# SPDX-License-Identifier: GPL-3.0-only
"""CHIMport order by weight (tools/chim_weight_table.py): classes from data, towns kept whole, provenance shown.

Every fixture is synthetic: made-up cells, names and numbers. No game data.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import chim_weight_table as W  # noqa: E402

CLASSES = {
    'format': W.CLASSES_FORMAT, 'status': 'test',
    'classes': [{'id': 'feather', 'label': 'Feather', 'min_headroom_bytes': 3000000, 'max_placed_faces': 'median_shipped'},
                {'id': 'light', 'label': 'Light', 'min_headroom_bytes': 2000000},
                {'id': 'middle', 'label': 'Middle', 'min_headroom_bytes': 1000000},
                {'id': 'heavy', 'label': 'Heavy', 'min_headroom_bytes': 0}],
    'over': {'id': 'over', 'label': 'Over'}, 'unmeasured': {'id': 'unmeasured', 'label': 'Unmeasured'},
    'seabed': {'id': 'seabed', 'label': 'Seabed'}, 'easy_batch': ['feather', 'light']}


def cell(headroom=None, faces=1000, name='', region='Synthetic Region', converted=True, ok=True, build='old-run',
         land=True, placements=10):
    audits = {}
    if headroom is not None:
        audits['memory_fit'] = {'status': 'passed', 'build': build, 'numbers': {'least_headroom': headroom}}
    if converted and not ok:
        audits['stair_walk'] = {'status': 'failed', 'build': build}
    return {'island': 1, 'land': land, 'name': name, 'region': region, 'ring': 3,
            'chim': {'converted': converted, 'successful': converted and ok,
                     'bucket': 'audits_passed' if converted and ok else ('converted_failing' if converted else 'not_started')},
            'audits': audits, 'stats': {'faces': {'chim_placed': faces}},
            'provenance': {'build': build, 'built_at': '2026-10-11T10:00:00+00:00'},
            'contents': {'placements': placements}}


def progress(**cells):
    return {'cells': {k.replace('_', ',').replace('m', '-'): v for k, v in cells.items()}}


class ClassTests(unittest.TestCase):
    def test_classes_follow_the_config_thresholds_and_the_shipped_median(self):
        p = progress(**{'0_0': cell(5000000, faces=100), '1_0': cell(5000000, faces=900), '2_0': cell(2500000),
                        '3_0': cell(1500000), '4_0': cell(10), '5_0': cell(-5), '6_0': cell(4000000, ok=False),
                        '7_0': cell(None, converted=False), '9_9': cell(100, faces=500)})
        doc = W.make(p, {'9,9'}, CLASSES)
        got = {r['cell']: r['class'] for r in doc['rows']}
        self.assertEqual(doc['median_shipped_placed_faces'], 500)
        self.assertEqual(got, {'0,0': 'feather', '1,0': 'light', '2,0': 'light', '3,0': 'middle', '4,0': 'heavy',
                               '5,0': 'over', '6,0': 'over', '7,0': 'unmeasured'})
        self.assertEqual([r['cell'] for r in doc['rows']][:2], ['0,0', '1,0'], 'lightest first')
        self.assertEqual(doc['batch'], ['0,0', '1,0', '2,0'])

    def test_thresholds_are_data_a_bad_config_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = dict(CLASSES, classes=[{'id': 'a', 'min_headroom_bytes': 1}, {'id': 'b', 'min_headroom_bytes': 5}])
            path = Path(tmp) / 'c.json'
            path.write_text(json.dumps(bad), encoding='utf-8')
            with self.assertRaises(ValueError):
                W.load_classes(path)
            path.write_text(json.dumps(dict(CLASSES, easy_batch=['nope'])), encoding='utf-8')
            with self.assertRaises(ValueError):
                W.load_classes(path)

    def test_the_shipped_config_loads(self):
        doc = W.load_classes(ROOT / 'config' / 'chim-weight-classes.json')
        self.assertEqual(doc['easy_batch'], ['featherweight', 'lightweight'])


class TownTests(unittest.TestCase):
    def test_a_town_and_its_neighbours_wait_for_a_heavy_cell_together(self):
        p = progress(**{'0_0': cell(4000000, name='Townville'), '1_0': cell(4000000, name='Townville, Harbour'),
                        '2_0': cell(4000000), '0_1': cell(500000), '5_5': cell(4000000)})
        doc = W.make(p, set(), CLASSES)
        self.assertEqual(doc['batch'], ['5,5'])
        town = doc['towns'][0]
        self.assertEqual((town['town'], town['joins']), ('Townville', False))
        self.assertEqual([b['cell'] for b in town['blockers']], ['0,1'])
        rows = {r['cell']: r for r in doc['rows']}
        self.assertIn('town Townville waits for 0,1 (heavy)', rows['2,0']['held'][0])

    def test_a_town_already_on_chim_lets_its_light_neighbours_join(self):
        p = progress(**{'0_0': cell(10, name='Townville'), '1_0': cell(4000000)})
        doc = W.make(p, {'0,0'}, CLASSES)
        self.assertEqual(doc['batch'], ['1,0'])
        self.assertTrue(doc['towns'][0]['joins'])

    def test_a_held_cell_stays_out_with_its_reason_and_holds_its_town(self):
        p = progress(**{'0_0': cell(4000000, name='Lavaton'), '1_0': cell(4000000)})
        doc = W.make(p, set(), CLASSES, hold={'1,0': 'lava method first'})
        self.assertEqual(doc['batch'], [])
        rows = {r['cell']: r for r in doc['rows']}
        self.assertIn('lava method first', rows['1,0']['held'])


class ProvenanceTests(unittest.TestCase):
    def test_every_figure_names_its_build_and_old_builders_are_marked(self):
        p = progress(**{'0_0': cell(4000000, build='old-run'), '1_0': cell(4000000, build='new-run')})
        doc = W.make(p, set(), CLASSES, current=['new-run'])
        rows = {r['cell']: r for r in doc['rows']}
        self.assertEqual(rows['0,0']['headroom_by']['build'], 'old-run')
        self.assertFalse(rows['0,0']['headroom_by']['current'])
        self.assertTrue(rows['1,0']['headroom_by']['current'])
        self.assertEqual(doc['totals']['batch_figures_from_older_builds'], {'old-run': 1})
        self.assertIn('(older builder)', W.render_md(doc, 'now'))

    def test_a_current_run_replaces_the_trackers_headroom(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / 'chim-heap.json').write_text(json.dumps({'frames': [
                {'frame': W.frame_path((0, 0)), 'headroom_bytes': 1500000, 'budget_bytes': 6000000, 'ok': True}]}))
            (run / 'chim-regions.json').write_text(json.dumps({'frames': [{'cell': [0, 0], 'cells': [[0, 0]],
                                                                           'kind': 'land'}]}))
            figures = W.run_headroom('fresh', run)
        doc = W.make(progress(**{'0_0': cell(4000000)}), set(), CLASSES, runs=[('fresh', figures)])
        row = doc['rows'][0]
        self.assertEqual((row['headroom_bytes'], row['class'], row['headroom_by']['build']), (1500000, 'middle', 'fresh'))
        self.assertTrue(row['headroom_by']['current'])

    def test_seabed_cells_are_planned_and_join_once_converted(self):
        p = progress(**{'0_0': cell(None, converted=False, land=False), '1_0': cell(None, land=False)})
        doc = W.make(p, set(), CLASSES, seabed={'0,0', '1,0'})
        rows = {r['cell']: r for r in doc['rows']}
        self.assertEqual((rows['0,0']['class'], rows['1,0']['class']), ('seabed', 'seabed'))
        self.assertEqual(doc['batch'], ['1,0'])

    def test_a_measured_empty_seabed_cell_without_an_island_joins(self):
        # a seabed cell has no census row, so its tracker record names no island; a CHIMport run measured it as
        # empty sea (nothing placed, nothing converted): it is listed and joins the batch
        rec = cell(None, converted=False, land=False)
        rec.pop('island')
        rec['chim'] = {'converted': False, 'bucket': 'empty_sea', 'status': 'empty_sea', 'empty': True}
        doc = W.make(progress(**{'2_0': rec}), set(), CLASSES, seabed={'2,0'})
        self.assertEqual([r['class'] for r in doc['rows']], ['seabed'])
        self.assertEqual(doc['batch'], ['2,0'])


class OutputTests(unittest.TestCase):
    def test_cli_writes_the_batch_the_page_and_the_guide_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'p.json').write_text(json.dumps(progress(**{'0_0': cell(4000000), '1_0': cell(10)})))
            (tmp / 'kept.json').write_text(json.dumps({'format': 'aw-chim-cells-1', 'cells': [[9, 9]]}))
            (tmp / 'c.json').write_text(json.dumps(CLASSES))
            guide = tmp / 'GUIDE.md'
            guide.write_text('# Guide\n\n%s\nSTALE-SECTION\n%s\n\nafter\n' % (W.GUIDE_START, W.GUIDE_END))
            out = subprocess.run([sys.executable, str(ROOT / 'tools' / 'chim_weight_table.py'), '--progress',
                                  str(tmp / 'p.json'), '--kept', str(tmp / 'kept.json'), '--classes', str(tmp / 'c.json'),
                                  '--now', '2026-10-17 02:00 +0300', '--json', str(tmp / 'w.json'), '--cells-out',
                                  str(tmp / 'cells.json'), '--md', str(tmp / 'W.md'), '--guide', str(guide)],
                                 capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(json.loads((tmp / 'cells.json').read_text())['cells'], [[0, 0]])
            text = guide.read_text()
            self.assertNotIn('STALE-SECTION', text)
            self.assertTrue(text.endswith('after\n'))
            self.assertIn('| Synthetic Region | 2 | 1 |', text)
            self.assertIn('| 0,0 |', (tmp / 'W.md').read_text())
            self.assertNotIn(b'\r', (tmp / 'W.md').read_bytes())


if __name__ == '__main__':
    unittest.main()
