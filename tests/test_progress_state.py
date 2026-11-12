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
        if label_version != version:
            self.assertIn('has no ingested build yet', block)     # a newer VERSION says so
        # the data is stamped for this release line (the newest ingested build may still be of the release before, until
        # the first build of a new line is ingested: the block then says so, above)
        self.assertEqual(state['version_stamp']['release'], cps.release_of(version))

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
