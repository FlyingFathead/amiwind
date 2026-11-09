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
        # MWSCRIPT-UNPLACED-ATTACH-62: named by nothing is its own state (it never runs in the original either)
        self.assertEqual(F.state_of(r), ('inert', 'nothing names it: it never runs in the original either'))
        r['notyet'] = ['placeitem']             # a function it lacks keeps nothing from running
        self.assertEqual(F.state_of(r)[0], 'inert')
        r['notyet'] = []
        r['refs']['records'] = {'ACTI': ['x']}
        r['refs']['placed'] = {'Bloodmoon.esm': {'ACTI': 1}}
        self.assertEqual(F.state_of(r)[0], 'not-in-image')
        r['bound'] = 2
        self.assertEqual(F.state_of(r)[0], 'runs')
        r = copy.deepcopy(base)
        r['start'] = True
        self.assertEqual(F.state_of(r)[0], 'runs')
        r['inert'] = True
        self.assertEqual(F.state_of(r)[0], 'attached-not-run')
        r['handwritten'] = True
        self.assertEqual(F.state_of(r), ('attached-not-run', 'a hand-written rule carries it'))

    def test_records_never_placed_run_where_the_build_attaches_them(self):
        # MWSCRIPT-UNPLACED-ATTACH-62: an item's script runs while carried, an actor's on a levelled list's pick, an
        # object's on what a script places; an activator nothing makes stays not attached; an inert one is not run
        base = {'error': False, 'handwritten': False, 'inert': False, 'notyet': [], 'bound': 0, 'start': False,
                'started_by': [], 'refs': {'records': {}, 'placed': {}, 'levelled': 0, 'dialogue_starts': 0,
                                           'dialogue_speaker': 0, 'placed_by_scripts': 0}}
        item = copy.deepcopy(base)
        item['refs']['records'] = {'WEAP': ['sunder']}
        self.assertEqual(F.state_of(item), ('runs', 'runs while the player carries one of its items'))
        item['inert'] = True
        self.assertEqual(F.state_of(item)[0], 'attached-not-run')
        actor = copy.deepcopy(base)
        actor['refs']['records'] = {'CREA': ['kagouti_diseased']}
        self.assertEqual(F.state_of(actor)[0], 'not-attached')
        actor['refs']['levelled'] = 19
        self.assertEqual(F.state_of(actor), ('runs', 'runs on the actor a levelled list gives'))
        acti = copy.deepcopy(base)
        acti['refs']['records'] = {'ACTI': ['bm_wereeffect']}
        self.assertEqual(F.state_of(acti), ('not-attached', 'its records are never placed, and nothing makes them '
                                                            'at run time yet'))
        acti['refs']['placed_by_scripts'] = 1
        self.assertEqual(F.state_of(acti), ('runs', 'runs on the object a script places'))
        del acti['refs']['placed_by_scripts']      # a measurement before the field: not made
        self.assertEqual(F.state_of(acti)[0], 'not-attached')

    def test_never_made_records_and_scripts_with_no_function(self):
        # MWSCRIPT-COMPLETE-LANDMARK: a record nothing places in any world and no script or dialogue result makes never
        # exists in the original: its script is inert, a function it lacks or not; made only by an add-on's script it
        # waits for that world; a script with no function at all only sets its own locals, which the dialogue keeps on
        # the speaker (parked locals), so it counts as running; one with a function stays attached, not run
        base = {'error': False, 'handwritten': False, 'inert': False, 'notyet': [], 'bound': 0, 'start': False,
                'started_by': [], 'functions': {'rotate': 1},
                'refs': {'records': {'ACTI': ['in_dwrv_crank_akula10']}, 'placed': {}, 'levelled': 0,
                         'dialogue_starts': 0, 'dialogue_speaker': 0, 'placed_by_scripts': 0, 'made_by': []}}
        r = copy.deepcopy(base)
        self.assertEqual(F.state_of(r), ('inert', 'its records are never placed and nothing makes them: it never runs '
                                                  'in the original either'))
        r['notyet'] = ['placeitem']
        self.assertEqual(F.state_of(r)[0], 'inert')
        r['notyet'] = []
        r['refs']['made_by'] = ['Bloodmoon.esm']
        self.assertEqual(F.state_of(r), ('not-in-image', 'made only by a script of an add-on world, not in the image '
                                                         'yet'))
        r['refs']['made_by'] = ['Bloodmoon.esm', 'Morrowind.esm']
        self.assertEqual(F.state_of(r)[0], 'not-attached')
        r = copy.deepcopy(base)
        r['refs']['records'] = {'MISC': ['x']}            # an item: it can be bought, given, held: not "never made"
        self.assertEqual(F.state_of(r)[0], 'runs')
        npc = copy.deepcopy(base)
        npc['refs']['records'] = {'NPC_': ['crassius curio']}
        npc['refs']['placed'] = {'Morrowind.esm': {'NPC_': 1}}
        npc['bound'], npc['inert'], npc['functions'] = 0, True, {}
        self.assertEqual(F.state_of(npc), ('runs', "nothing to run but its own locals, which the dialogue keeps on "
                                                   "the speaker"))
        npc['functions'] = {'getdistance': 1}
        self.assertEqual(F.state_of(npc)[0], 'attached-not-run')

    def test_the_engine_carries_what_the_tracker_counts(self):
        # MWSCRIPT-UNPLACED-ATTACH-62: the rows the tracker calls running at run time have their engine side: PADD
        # for every scripted item, LACT for the levelled lists' actors, the hooks that start and stop them
        from mwscript import awms
        self.assertEqual(F.CARRIED, awms.CARRIED)
        self.assertIn('LACT', awms.RESIDENT)
        src = (ROOT / 'engine/aga/src/aw_mwhost.c').read_text(encoding='utf-8')
        for hook in ('aw_item_removed=item_removed', 'aw_actors_levelled_spawned=levelled_spawned', 'carried_sync();',
                     'removed_flush();', 'levelled_flush();'):
            self.assertIn(hook, src)
        actors = (ROOT / 'engine/aga/src/aw_actors.c').read_text(encoding='utf-8')
        self.assertEqual(actors.count('aw_actors_levelled_spawned (ent, q->levelled)'), 1)
        self.assertIn('q.levelled = b.hash', actors)
        self.assertIn('q->levelled = picked', actors)

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
        allowed = {'id', 'master', 'defined_in', 'area', 'areas', 'refs', 'start', 'started_by', 'bound', 'held',
                   'handwritten', 'inert', 'error', 'functions', 'tests', 'conditions', 'openmw', 'notyet', 'state',
                   'why'}
        refs = {'records', 'placed', 'levelled', 'dialogue_starts', 'dialogue_speaker', 'placed_by_scripts', 'made_by'}
        for r in self.doc['scripts']:
            self.assertLessEqual(set(r), allowed, r['id'])
            self.assertLessEqual(set(r['refs']), refs, r['id'])
            # made_by holds master names only ('dialogue' for a dialogue result), never script text
            self.assertLessEqual(set(r['refs'].get('made_by', [])), set(F.MASTERS) | {'dialogue'}, r['id'])
            self.assertIsInstance(r['error'], bool)


if __name__ == '__main__':
    unittest.main()
