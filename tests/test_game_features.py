# SPDX-License-Identifier: GPL-3.0-only
"""The game parity tracker (tools/game_features.py, GAME-PARITY-TRACKER-60): the JSON is valid, every proof path and
register ID exists, the generated page is current (a stale page fails here), and the MWScript counts that the page
shows still match the compiler's own table."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import game_features as F  # noqa: E402


class Tracker(unittest.TestCase):
    def test_json_valid_and_page_current(self):
        doc = F.load()
        self.assertEqual(F.problems(doc, F.register_ids()), [])
        self.assertEqual(F.OUT.read_text(encoding='utf-8'), F.render(doc),
                         'docs/GAME_FEATURES.md is stale: run tools/game_features.py render')

    def test_every_system_of_the_brief_has_a_row(self):
        ids = {f['id'] for f in F.load()['features']}
        for part in ('exterior-world', 'interiors', 'doors-travel', 'npc-ai', 'melee-ranged', 'spell-effects',
                     'alchemy', 'enchanting', 'spellmaking', 'stats-skills', 'levelling', 'rest-wait', 'inventory',
                     'containers', 'barter', 'training', 'factions', 'dialogue', 'journal-quests', 'crime', 'saves',
                     'mwscript-functions', 'music', 'hud'):
            self.assertIn(part, ids)

    def test_validation_catches_mistakes(self):
        doc = F.load()
        row = doc['features'][0]
        self.assertTrue(any('state' in p for p in F.problems(dict(doc, features=[dict(row, state='finished')]))))
        self.assertTrue(any('proof' in p for p in F.problems(dict(doc, features=[dict(row, proof='')]))))
        self.assertTrue(any('does not exist' in p for p in
                            F.problems(dict(doc, features=[dict(row, proof='tests/no_such_file.py')]))))
        self.assertTrue(any('NO-SUCH-BUG-99' in p for p in
                            F.problems(dict(doc, features=[dict(row, bugs=['NO-SUCH-BUG-99'])]), F.register_ids())))
        partial = dict(row, state='partial', missing='')
        self.assertTrue(any('what is missing' in p for p in F.problems(dict(doc, features=[partial]))))

    def test_mwscript_counts_are_the_compilers(self):
        text = (ROOT / 'tools' / 'mwscript' / 'functions.py').read_text(encoding='utf-8')
        table = text.split("_TABLE = r'''", 1)[1].split("'''", 1)[0]
        rows = [ln for ln in table.splitlines() if ln.strip() and not ln.startswith('#')]
        self.assertGreaterEqual(len(rows), 1)
        sys.path.insert(0, str(ROOT / 'tools'))
        import mwscript.functions as fn
        m = F.load()['mwscript']
        self.assertEqual(len(fn.FUNCTIONS), m['table_functions'])
        self.assertEqual(sum(1 for f in fn.FUNCTIONS.values() if f.run), m['carried_out'])
        self.assertTrue(re.search(r'\bused: pending\b', F.render(F.load())) or m['used_and_carried_out'] is not None)


if __name__ == '__main__':
    unittest.main()
