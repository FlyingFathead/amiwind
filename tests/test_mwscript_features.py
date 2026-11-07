# SPDX-License-Identifier: GPL-3.0-only
"""The MWScript feature tracker (tools/mwscript_features.py, MWSCRIPT-COVERAGE-62): the JSON is valid, every row's
state agrees with the interpreter's function table of today (a function carried out later makes the data stale until
it is rendered again), the generated page is current (a stale page fails here), and the public data holds record ids,
counts and states only, never the game's script text."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import mwscript_features as F  # noqa: E402


class Tracker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = F.load()

    def test_json_valid_and_page_current(self):
        self.assertEqual(F.problems(copy.deepcopy(self.doc)), [])
        self.assertEqual(F.OUT.read_text(encoding='utf-8'), F.render(copy.deepcopy(self.doc)),
                         'docs/MWSCRIPT_FEATURES.md is stale: run tools/mwscript_features.py render')

    def test_json_as_written_and_within_the_release_limit(self):
        import release
        text = F.DATA.read_text(encoding='utf-8')
        self.assertEqual(text, F.dumps(self.doc), 'docs/mwscript-features.json: run tools/mwscript_features.py render')
        self.assertLess(len(text.encode('utf-8')), release.text_limit('docs/mwscript-features.json'))
        self.assertLess(len(F.OUT.read_text(encoding='utf-8').encode('utf-8')),
                        release.text_limit('docs/MWSCRIPT_FEATURES.md'))

    def test_every_script_of_the_three_masters(self):
        rows = self.doc['scripts']
        self.assertGreaterEqual(len(rows), 1200)
        self.assertEqual({r['master'] for r in rows}, set(F.MASTERS))
        self.assertEqual(sum(1 for r in rows if r['start']), self.doc['measured']['start_scripts'])
        self.assertGreater(self.doc['dialogue_results']['total'], 1000)

    def test_states_follow_the_function_table(self):
        doc = copy.deepcopy(self.doc)
        row = next(r for r in doc['scripts'] if r['state'] == 'runs' and r['bound'])
        row['notyet'] = ['placeitem']          # a function the interpreter does not carry out
        self.assertTrue(any('stale' in p for p in F.problems(doc)))
        F.apply_states(doc)
        self.assertEqual(row['state'], 'missing-function')
        row['notyet'] = ['enable']              # carried out today: drops out at render
        F.apply_states(doc)
        self.assertEqual(row['state'], 'runs')
        row['error'] = True
        self.assertEqual(F.state_of(row)[0], 'not-converted')

    def test_state_rules(self):
        base = {'error': False, 'handwritten': False, 'inert': False, 'notyet': [], 'bound': 0, 'start': False,
                'started_by': [], 'refs': {'records': {}, 'placed': {}, 'levelled': 0, 'dialogue_starts': 0,
                                           'dialogue_speaker': 0}}
        r = copy.deepcopy(base)
        self.assertEqual(F.state_of(r), ('not-attached', 'nothing names it'))
        r['refs']['placed'] = {'Bloodmoon.esm': {'ACTI': 1}}
        self.assertEqual(F.state_of(r)[0], 'not-attached')
        r['bound'] = 2
        self.assertEqual(F.state_of(r)[0], 'runs')
        r = copy.deepcopy(base)
        r['start'] = True
        self.assertEqual(F.state_of(r)[0], 'runs')
        r['inert'] = True
        self.assertEqual(F.state_of(r)[0], 'attached-not-run')
        r['handwritten'] = True
        self.assertEqual(F.state_of(r), ('attached-not-run', 'a hand-written rule carries it'))

    def test_openmw_fixes(self):
        from mwscript.parser import Parser
        tree = Parser('Begin t\n"dagoth_ur_1"->ModHealth -100\nDontSaveObject\nShowMap "Vivec"\nEnd t\n', {}).script()
        self.assertEqual(F.openmw_fixes(tree), ['dagoth-ur-remote-change', 'dontsaveobject-ignored'])
        for fix in F.OPENMW_FIXES:
            self.assertTrue(fix['original'] and fix['openmw'] and fix['amiwind'])
            self.assertIn('apps/openmw/', fix['openmw'])
        ids = {f['id'] for f in F.OPENMW_FIXES}
        self.assertTrue(all(set(r['openmw']) <= ids for r in self.doc['scripts']))
        self.assertGreater(sum(1 for r in self.doc['scripts'] if r['openmw']), 0)

    def test_public_data_has_no_script_text(self):
        text = F.DATA.read_text(encoding='utf-8').casefold()
        page = F.OUT.read_text(encoding='utf-8').casefold()
        for word in ('begin ', 'endif', 'messagebox "', '"text"', '"source"'):
            self.assertNotIn(word, text)
        self.assertNotIn('endif', page)
        allowed = {'id', 'master', 'defined_in', 'area', 'areas', 'refs', 'start', 'started_by', 'bound',
                   'handwritten', 'inert', 'error', 'functions', 'tests', 'conditions', 'openmw', 'notyet', 'state',
                   'why'}
        for r in self.doc['scripts']:
            self.assertLessEqual(set(r), allowed, r['id'])
            self.assertIsInstance(r['error'], bool)


if __name__ == '__main__':
    unittest.main()
