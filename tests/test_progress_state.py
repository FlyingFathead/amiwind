"""The CHIM Progress Tracker page leads with a generated current state (PROGRESS-TRACKER-STALE-64): the page's block must
equal a fresh render of the tracker snapshot and the MWScript tracker, so the page cannot fall behind VERSION again."""
import copy
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import cell_progress_state as cps  # noqa: E402


def load():
    page = cps.PAGE.read_text(encoding='utf-8')
    state = json.loads(cps.STATE.read_text(encoding='utf-8'))
    scripts = json.loads(cps.MWSCRIPT.read_text(encoding='utf-8'))
    version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
    return page, state, scripts, version


class CurrentStateBlockTests(unittest.TestCase):
    def test_block_is_a_fresh_render(self):
        page, state, scripts, version = load()
        self.assertEqual(cps.problems(page, state, scripts, version), [])

    def test_block_says_which_build_it_was_counted_from(self):
        page, state, scripts, version = load()
        block = cps.split_page(page)[1]
        newest = state['builds'][0]
        self.assertIn(state['in_game_label'], block)
        self.assertIn(str(newest['built_at'])[:10], block)
        label_version = state['in_game_label'].lstrip('v').split(' ')[0]
        if cps.release_of(label_version) != cps.release_of(version):
            self.assertIn('has no ingested build yet', block)     # a newer release in development says so
        else:
            # a dev or release-candidate build of the release in development is its ingested build
            self.assertNotIn('has no ingested build yet', block)
        # the data is stamped for this release line (the newest ingested build may still be of the release before, until
        # the first build of a new line is ingested: the block then says so, above)
        self.assertEqual(state['version_stamp']['release'], cps.release_of(version))

    def test_a_build_of_the_release_in_development_is_its_ingested_build(self):
        # TRACKERS-MOURNHOLD-NOT-COUNTED-67 (docs review H7): the page called v0.0.67 in development with no ingested
        # build while its dev3 build was ingested; only a newest build of an earlier release says so
        self.assertEqual(cps.building_note('v0.0.67-dev3 (a375b13f)', '0.0.67'), '')
        self.assertEqual(cps.building_note('v0.0.67-dev3 (a375b13f)', '0.0.67-dev4'), '')
        self.assertEqual(cps.building_note('v0.0.67 (abc)', '0.0.67'), '')
        self.assertIn('0.0.67, has no ingested build yet', cps.building_note('v0.0.66 (ad5e9a0a)', '0.0.67'))
        self.assertIn('has no ingested build yet', cps.building_note('v0.0.66-dev12 (ac37e80b)', '0.0.67-dev1'))
        # the whole block follows
        _, state, scripts, _ = load()
        state = copy.deepcopy(state)
        state['in_game_label'] = 'v0.0.67-dev3 (a375b13f)'
        self.assertNotIn('has no ingested build yet', cps.render_block(state, scripts, '0.0.67'))
        state['in_game_label'] = 'v0.0.66 (ad5e9a0a)'
        self.assertIn('has no ingested build yet', cps.render_block(state, scripts, '0.0.67'))

    def test_later_rooms_that_are_in_the_game_are_not_called_later(self):
        # the Mournhold rooms were listed as waiting for a batch while 87 of 93 were in the game
        _, state, scripts, _ = load()
        state = copy.deepcopy(state)
        ir = state['interiors']
        ir['later'] = [{'batch': 'later: Mournhold', 'island': 'Mournhold', 'master': 'Tribunal.esm',
                        'waits_for': 'it waits for a batch'}]
        ir['headline']['Mournhold'].update({'on_chim_rooms': 87, 'total': 93, 'not_started': 5})
        text = '\n'.join(cps.interior_block(state))
        self.assertIn('87 of its 93 rooms are in the game on CHIM rooms; 5 not started yet', text)
        self.assertNotIn('it waits for a batch', text)
        ir['headline']['Mournhold'].update({'on_chim_rooms': 0})
        self.assertIn('it waits for a batch', '\n'.join(cps.interior_block(state)))

    def test_mournhold_is_counted_on_chim_when_its_world_is_in_the_newest_build(self):
        # the exterior table's Mournhold line carries its land cells whenever the data has them, never "not in the build"
        # beside "11 of 11" done
        _, state, scripts, version = load()
        # the builds table adds up: its Mournhold column is beside the other two, so the row's total is their sum
        block = cps.render_block(state, scripts, version)
        self.assertIn('| Build | Built | Vvardenfell | Solstheim | Mournhold | All cells on CHIM |', block)
        for line in block.splitlines():
            m = re.match(r'^\| v0\.0\.\d+[^|]* \| \d{4}-\d\d-\d\d \| ([\d,]+) \+ ([\d,]+) \| ([\d,]+) \+ ([\d,]+) \| '
                         r'([\d,]+) \+ ([\d,]+) \| ([\d,]+) \|$', line)
            if m and line.startswith('| ' + state['builds'][0]['label']):
                parts = [int(x.replace(',', '')) for x in m.groups()]
                self.assertEqual(sum(parts[:6]), parts[6], line)
        rows = {r[0]: r for r in cps.exterior_rows(state)[1]}
        mh = rows['Mournhold (Tribunal)']
        done = next(i for i in state['islands'] if i['name'] == 'Mournhold')
        if done['done']:
            self.assertNotEqual(mh[1], 'not in the build', 'Mournhold has done cells but no cell on CHIM in the newest build')
            self.assertRegex(mh[1], r'^\d+ land')
            self.assertNotEqual(mh[1], '0 land + 0 sea cells')

    def test_a_hand_edited_or_stale_block_is_refused(self):
        page, state, scripts, version = load()
        self.assertTrue(cps.problems(page.replace('1,409', '1,408', 1), state, scripts, version))
        self.assertTrue(cps.problems(page, state, scripts, '0.0.99-dev1'))        # a newer VERSION: restamp and render
        old = copy.deepcopy(state)
        old['version_stamp'] = {'release': 'v0.0.48'}
        self.assertTrue(any('stamped v0.0.48' in p for p in cps.problems(page, old, scripts, version)))
        self.assertTrue(cps.problems(page.replace(cps.BEGIN, ''), state, scripts, version))
        changed = copy.deepcopy(scripts)
        changed['scripts'][0]['state'] = 'missing-function' if changed['scripts'][0]['state'] != 'missing-function' else 'runs'
        self.assertTrue(cps.problems(page, state, changed, version))             # the scripting numbers follow their tracker

    def test_the_page_leads_with_the_state_and_runs_newest_first(self):
        page, state, scripts, version = load()
        headings = re.findall(r'^## (.+)$', page, re.M)
        self.assertEqual(headings[0], 'Contents')
        self.assertEqual(headings[1], 'Current state')
        self.assertLess(page.index(cps.BEGIN), page.index('## Why it exists'))
        dates = [str(b['built_at'])[:10] for b in state['builds']]
        self.assertEqual(dates, sorted(dates, reverse=True))                      # the data and so the table: newest first
        rows = re.findall(r'^\| (v0\.0\.\d+[^|]*) \| (\d{4}-\d{2}-\d{2}) \|', cps.split_page(page)[1], re.M)
        self.assertEqual([d for _, d in rows], sorted((d for _, d in rows), reverse=True))
        old = page[page.index('## History: current state as written 24 October 2026'):]
        versions = [tuple(int(x) for x in m.groups()) for m in re.finditer(r'^\| v0\.(0)\.(\d+)', old, re.M)]
        self.assertEqual(versions, sorted(versions, reverse=True))                # the old table, newest row first
        self.assertIn('## History: v0.0.41 preparation notes, 15 October 2026', page)   # history is kept

    def test_public_wording(self):
        page = load()[0]
        prose = re.sub(r'`[^`]*`', '', page)
        self.assertNotRegex(prose, r'(?i)\bthe owner\b|\bowner apron\b')
        self.assertIn('Apron ownership follow-up, 15 October 2026', page)
        self.assertRegex(page, r'(?m)^_Last updated with AmiWind v[0-9.]+(?:-[a-z]+\d+)? \(\d+ \w+ \d{4}\)\._$')


if __name__ == '__main__':
    unittest.main()
