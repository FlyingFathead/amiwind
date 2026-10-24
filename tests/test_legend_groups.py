# SPDX-License-Identifier: GPL-3.0-only
"""The CHIM Progress Tracker legend in three groups (TOOLKIT-LEGEND-STATES-UNCLEAR-48): every cell is "in the game" (what the
newest ingested build ships), "not in the game yet" (work left) or "beyond the world's edge: settled" (no cell record in the
original game data, on no build). tools/cell_progress.py classify derives chim.group / chim.state and the headline figures; the
World Map, the index headline and the Markdown tracker draw them. Every fixture is synthetic."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import cell_progress as cp  # noqa: E402
import test_cell_progress as tcp  # noqa: E402

KIT = ROOT / 'amiwind-toolkit'
CENSUS = {'source': 'census', 'refs_total': 0}
METRICS = {'source': 'metrics (regions split over their cells)', 'refs_total': 2}


def cell(x, y, bucket, land=False, builds=(), island=1, contents=CENSUS, **extra):
    c = {'x': x, 'y': y, 'land': land, 'island': island, 'contents': contents,
         'chim': {'bucket': bucket, 'on_chim_builds': list(builds)}}
    c.update(extra)
    return c


def sample():
    return {
        '0,0': cell(0, 0, 'terrain_complete_unlit', land=True, builds=['v47']),
        '1,0': cell(1, 0, 'audits_passed', land=True, builds=['v46']),               # converted, not in the newest build
        '2,0': cell(2, 0, 'empty_sea', land=True, builds=['v47']),                   # seabed with a LAND record, in the build
        '-15,-8': cell(-15, -8, 'ocean', builds=['v47']),                           # empty game record an old run called ocean
        '-19,-5': cell(-19, -5, 'ocean', contents=None),                            # no game record, on no build
        '13,23': cell(13, 23, 'ocean', contents=METRICS),                           # only an estimator region row: no record
        '5,5': cell(5, 5, 'ocean'),                                                 # open sea the game defines, not built
        '3,0': cell(3, 0, 'converted_failing', land=True, builds=['v47']),           # a problem stays a problem
        '-20,20': cell(-20, 20, 'not_started', land=True, island=2),                 # Solstheim
        '-20,22': cell(-20, 22, 'not_started', island=None),                         # sea off Solstheim, no island of its own
        '4,0': cell(4, 0, 'not_started', land=True),                                 # Vvardenfell, not started
    }


class ClassifyTests(unittest.TestCase):
    def test_every_cell_gets_one_group_and_state(self):
        cells = sample()
        f = cp.classify(cells, 'v47')
        st = {k: c['chim']['state'] for k, c in cells.items()}
        self.assertEqual(st, {'0,0': 'terrain_complete_unlit', '1,0': 'not_in_build', '2,0': 'sea_in_game',
                              '-15,-8': 'sea_in_game', '-19,-5': 'settled', '13,23': 'settled', '5,5': 'ocean',
                              '3,0': 'converted_failing', '-20,20': 'solstheim', '-20,22': 'solstheim', '4,0': 'not_started'})
        for c in cells.values():
            self.assertEqual(c['chim']['group'], cp.STATE_GROUP[c['chim']['state']])
        self.assertEqual(f['groups'], {'in_game': 3, 'not_in_game': 6, 'settled': 2, 'accounted_for': 5, 'cells': 11})
        self.assertEqual(sum(f['states'].values()), 11)
        self.assertEqual(set(f['states']), set(cp.STATES))                  # every state listed, zeros included
        self.assertEqual(cells['-15,-8']['chim']['bucket'], 'ocean')         # buckets and the done figures do not move

    def test_settled_counts_toward_accounted_for_never_toward_in_the_game(self):
        cells = {'a': cell(9, 9, 'ocean', contents=None), 'b': cell(0, 0, 'audits_passed', land=True, builds=['v47'])}
        g = cp.classify(cells, 'v47')['groups']
        self.assertEqual((g['in_game'], g['settled'], g['accounted_for']), (1, 1, 2))

    def test_no_build_ingested_puts_nothing_in_the_game(self):
        cells = sample()
        g = cp.classify(cells, None)['groups']
        self.assertEqual(g['in_game'], 0)
        self.assertEqual(cells['0,0']['chim']['state'], 'not_in_build')
        self.assertEqual(cells['-19,-5']['chim']['state'], 'settled')

    def test_game_record_field_wins_and_data_without_a_census_trusts_the_estimator(self):
        c = cell(1, 1, 'ocean', contents=None, game_record=True)
        self.assertEqual(cp.cell_state(c, 'v47'), 'ocean')
        c = cell(1, 1, 'ocean', contents=CENSUS, game_record=False)
        self.assertEqual(cp.cell_state(c, 'v47'), 'settled')
        self.assertEqual(cp.cell_state(cell(1, 1, 'ocean', contents=METRICS), 'v47'), 'settled')
        self.assertEqual(cp.cell_state(cell(1, 1, 'ocean', contents=METRICS), 'v47', census=False), 'ocean')

    def test_group_figures_of_older_data_are_derived_without_changing_it(self):
        cells = sample()
        doc = {'headline': {'on_chim': {'build': 'v47'}}, 'cells': cells, 'sources': {'census': True}}
        f = cp.group_figures(doc)
        self.assertEqual((f['groups']['in_game'], f['groups']['settled'], f['build']), (3, 2, 'v47'))
        self.assertNotIn('state', cells['0,0']['chim'])                      # the document is untouched
        doc['headline'].update(groups={'in_game': 7}, states={'settled': 1}, in_game_build='x')
        self.assertEqual(cp.group_figures(doc)['groups'], {'in_game': 7})    # ingest's own figures win
        self.assertIn('In the game 3 | not in the game yet 6 | settled 2 | accounted for 5 of 11 cells (newest build v47)',
                      cp.group_line(f))

    def test_state_lists_match_the_page_and_the_headline_script(self):
        legend = (KIT / 'chim-legend.js').read_text(encoding='utf-8')
        head = (KIT / 'chim-head.js').read_text(encoding='utf-8')
        for gid, states in cp.GROUP_STATES.items():
            listed = '[' + ', '.join("'%s'" % s for s in states) + ']'
            self.assertIn(listed, legend, gid)
            self.assertIn(listed, head, gid)
        for text in (legend, head):
            self.assertIn(cp.SETTLED_TEXT, text)
            self.assertIn("Beyond the world's edge: settled", text)
        block = (KIT / 'world-map.html').read_text(encoding='utf-8').split('const CHIM_BUCKETS')[1].split('const CHIM_GRADES')[0]
        for s in cp.STATES:
            self.assertRegex(block, r'\b%s: \[' % s)                         # every state has a colour and a text on the map


class IngestTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.out = self.root / 'out'

    def doc(self):
        census = tcp.census_doc()
        census['cells']['5,5'] = {'counts': {}, 'placements': 0, 'flora': 0, 'meshes': [], 'doors': []}   # an empty game record
        census['cells']['6,6'] = {'counts': {}, 'placements': 0, 'flora': 0, 'meshes': [], 'doors': []}
        cp.record_result(self.out, {'format': cp.RESULT_FORMAT, 'build': 'chimport-ocean-old', 'generated': '2020-01-01T00:00:00+00:00',
                                    'cells': {'5,5': {'converted': True, 'status': 'ocean', 'ocean': True},     # in the build below
                                              '6,6': {'converted': True, 'status': 'ocean', 'ocean': True},     # a record, not built
                                              '8,8': {'converted': True, 'status': 'ocean', 'ocean': True}}})   # no record at all
        tcp.multi_run(self.root / 'v47', [c for c in tcp.LAND if c != (4, 4)] + [(5, 5)])
        return tcp.ingest(self.out, ['v47=%s' % (self.root / 'v47')], census=census, labels={'v47': 'Synthetic release'})

    def test_ingest_writes_groups_states_and_the_game_record(self):
        d = self.doc()
        c = d['cells']
        self.assertEqual((c['5,5']['chim']['bucket'], c['5,5']['chim']['state']), ('ocean', 'sea_in_game'))
        self.assertEqual((c['6,6']['chim']['state'], c['6,6']['chim']['group']), ('ocean', 'not_in_game'))
        self.assertEqual((c['8,8']['chim']['state'], c['8,8']['game_record']), ('settled', False))
        self.assertTrue(c['0,0']['game_record'])
        self.assertEqual(c['4,4']['chim']['state'], 'not_started')
        h = d['headline']
        self.assertEqual(h['groups'], {'in_game': 25, 'not_in_game': 2, 'settled': 1, 'accounted_for': 26, 'cells': 28})
        self.assertEqual((h['states']['sea_in_game'], h['states']['settled']), (1, 1))
        self.assertEqual((h['in_game_build'], h['in_game_label']), ('v47', 'Synthetic release'))
        self.assertEqual(h['sea_in_game'], 1)
        self.assertEqual(cp.group_figures(d)['groups'], h['groups'])

    def test_markdown_tracker_says_the_same(self):
        import cell_progress_md as md
        d = self.doc()
        page = md.render(d, '2026-10-22 12:00 +0300')
        self.assertIn('- **In the game: 25**', page)
        self.assertIn('Sea, in the game 1', page)
        self.assertIn('- **Not in the game yet: 2** (Not started 1, Open sea, not in the newest build 1)', page)
        self.assertIn("- **Beyond the world's edge: settled: 1** (Settled 1)", page)
        self.assertIn('Accounted for: 26 of 28 cells (in the game + settled)', page)
        self.assertIn(cp.SETTLED_TEXT, page)
        self.assertEqual(md.check(page), [])
        # older data without the fields: the page derives the same figures
        for x in d['cells'].values():
            for k in ('state', 'group'):
                x['chim'].pop(k, None)
            x.pop('game_record', None)
        for k in ('groups', 'states'):
            d['headline'].pop(k)
        self.assertIn('Accounted for: 26 of 28 cells', md.render(d, '2026-10-22 12:00 +0300'))

    def test_status_prints_the_groups(self):
        import contextlib
        import io
        self.doc()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(cp.main(['status', '--out', str(self.out)]), 0)
        self.assertIn('In the game 25 | not in the game yet 2 | settled 1 | accounted for 26 of 28 cells (newest build v47)', buf.getvalue())

    def test_page_and_headline_in_node(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node.js unavailable; the legend checks need an existing interpreter')
        self.doc()
        r = subprocess.run([node, str(ROOT / 'tests' / 'test_legend_groups.js'), str(KIT), str(self.out / cp.OUT_FILES['progress'])],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('legend groups ok', r.stdout)
        r = subprocess.run([node, str(ROOT / 'tests' / 'test_cell_progress_page_run.js'), str(KIT), str(self.out / cp.OUT_FILES['progress'])],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('grouped legend rows ok', r.stdout)


class PageTextTests(unittest.TestCase):
    def test_page_keeps_old_data_drawing(self):
        page = (KIT / 'world-map.html').read_text(encoding='utf-8')
        self.assertIn("function chimCls(c) { return c.chim.state || (c.chim.sea_in_game ? 'sea_in_game' : c.chim.bucket); }", page)
        self.assertIn("if (m === 'status' && chim.headline && chim.headline.groups && chim.headline.states)", page)
        self.assertIn("Object.entries(CHIM_BUCKETS).filter(([k]) => !CHIM_GROUPED_ONLY.has(k))", page)   # old data: flat rows
        self.assertIn('CHIM_SETTLED_ALPHA', page)                                                         # settled: faint grey
        self.assertNotIn('shared ocean chunk made, not yet placed', page)
        head = (KIT / 'chim-head.js').read_text(encoding='utf-8')
        self.assertIn("const grouped = !!(h.groups && h.states);", head)
        self.assertNotIn('not counted as done (shared ocean chunk made, not yet placed)', head.split('const STATE_PARTS')[1])

    def test_no_release_version_written_in_the_tracker_code(self):
        src = (ROOT / 'tools' / 'cell_progress.py').read_text(encoding='utf-8')
        self.assertNotIn("ELIGIBLE_RELEASE = 'v", src)
        self.assertIn("eligible_release(PL.next_release(plan_doc), working_version())", src)
        self.assertTrue(os.path.isfile(cp.VERSION_FILE))


if __name__ == '__main__':
    unittest.main()
