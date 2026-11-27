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

    def test_headline_counts_only_the_used_scripts(self):
        # the scripts nothing in the original names are listed apart, not in the headline or the per-script tables
        text = F.render(copy.deepcopy(self.doc))
        rows = self.doc['scripts']
        inert = [r for r in rows if r['state'] == 'inert']
        used = len(rows) - len(inert)
        self.assertIn('Of the {:,} scripts the original game uses'.format(used), text)
        self.assertIn('The {:,} scripts not used in the original game (they never run there either'.format(len(inert)),
                      text)
        self.assertIn('are not counted toward completion', text)
        self.assertIn('| Not used in the original game (never runs there either; not counted toward completion) | '
                      '{:,} |'.format(len(inert)), text)
        head, _, tail = text.partition('\n## Not used in the original game')
        self.assertTrue(tail)
        for r in inert:
            self.assertIn('| %s |' % r['id'], tail)
            self.assertNotIn('| %s | %s | %s |' % (r['id'], r['area'], 'Named by nothing'), head)
        self.assertEqual(len(rows), self.doc['measured'].get('scripts', len(rows)))

    def test_main_script_is_own_code_never_unused(self):
        # the game always starts the global script Main (OpenMW GlobalScripts::addStartup), named by nothing or not:
        # it is never "not used". AmiWind's own code does it; it is an adaptation only with every step carried out
        # (tests/test_mwscript_counterparts.py), and today its roll of Random100 is open
        r = {'id': 'Main', 'error': False, 'handwritten': False, 'inert': True, 'notyet': [], 'bound': 0,
             'start': False, 'started_by': [], 'refs': {'records': {}, 'placed': {}, 'levelled': 0,
                                                         'dialogue_starts': 0, 'dialogue_speaker': 0}}
        want = 'carried' if F.is_adaptation(F.counterparts().get('main')) else 'adaptation-gap'
        self.assertEqual(F.state_of(r)[0], want)
        r['id'] = 'main'
        self.assertEqual(F.state_of(r)[0], want)

    def test_not_used_means_nothing_can_bring_it_into_the_game(self):
        """MWSCRIPT-EFFECT-PARITY-69: the "not used in the original game" list holds only scripts nothing can bring
        into the game: no start record, no StartScript, no placed record, no levelled list, no script or dialogue
        result that makes its record, no item a script could hand out. A row that can run is refused there."""
        inert = [r for r in self.doc['scripts'] if r['state'] == 'inert']
        self.assertGreater(len(inert), 100)
        for r in inert:
            self.assertEqual(F.reachable(r), [], r['id'])
            self.assertFalse(set(r['refs']['records']) & set(F.CARRIED), r['id'])
        # none of them is counted toward completion, on the page's counts or in the summary the Toolkit draws
        s = F.script_summary(copy.deepcopy(self.doc))
        self.assertEqual(s['all']['unused'], len(inert))
        self.assertEqual(s['all']['used'], len(self.doc['scripts']) - len(inert))
        self.assertEqual(sum(m['used'] for m in s['masters']), s['all']['used'])
        self.assertEqual(sum(m['unused'] for m in s['masters']), len(inert))
        for m in s['masters'] + [s['all']]:
            self.assertEqual(m['run'] + m['adaptation'] + m['not_yet'], m['used'])
            self.assertEqual(m['done'], m['run'] + m['adaptation'])
        # each way in moves a row out of the list, and the check refuses a row left there
        for change, word in ((lambda r: r['refs'].update(levelled=1), 'a levelled list'),
                             (lambda r: r['refs'].update(made_by=['dialogue']), 'makes its record'),
                             (lambda r: r['refs'].update(placed={'Tribunal.esm': {'ACTI': 1}}), 'a placed record'),
                             (lambda r: r.update(started_by=['x']), 'StartScript'),
                             (lambda r: r.update(start=True), 'a start record')):
            doc = copy.deepcopy(self.doc)
            row = next(r for r in doc['scripts'] if r['state'] == 'inert' and r['refs']['records'])
            change(row)
            self.assertIn(word, ', '.join(F.reachable(row)))
            self.assertNotEqual(F.state_of(row)[0], 'inert', word)
            self.assertTrue(any('listed as not used in the original game, but it can run there' in p
                                for p in F.problems(doc)), word)

    def test_a_script_with_nothing_to_run_counts_where_its_cell_is_in_the_image(self):
        """MWSCRIPT-EFFECT-PARITY-69: two scripts with no function at all, on an add-on merchant and on the soldiers of
        an add-on fort, read "only in an add-on world" although their cells are in the image: the build leaves such a
        script out of the file, so it has no binding, and only bindings told the tracker what the image carries. The
        measurement now counts the placements in cells the image carries (placed_in_image), bound or not."""
        base = {'error': False, 'handwritten': False, 'inert': True, 'notyet': [], 'bound': 0, 'start': False,
                'started_by': [], 'functions': {},
                'refs': {'records': {'NPC_': ['x']}, 'placed': {'Tribunal.esm': {'NPC_': 1}}, 'levelled': 0,
                         'dialogue_starts': 0, 'dialogue_speaker': 11, 'placed_by_scripts': 0, 'made_by': []}}
        old = copy.deepcopy(base)            # measured before the count: as before
        self.assertEqual(F.state_of(old)[0], 'not-in-image')
        r = copy.deepcopy(base)
        r['refs']['placed_in_image'] = {'Tribunal.esm': 1}
        self.assertEqual(F.state_of(r), ('runs', 'nothing to run but its own locals, which the dialogue keeps on the '
                                                 'speaker'))
        r['refs']['placed_in_image'] = {}    # its cell is not in the image
        self.assertEqual(F.state_of(r)[0], 'not-in-image')
        # a script with something to run, placed in cells the image carries and bound nowhere, is a fault of the
        # build, never "only in an add-on world"
        r['inert'], r['functions'] = False, {'getdistance': 1}
        r['refs']['placed_in_image'] = {'Tribunal.esm': 1}
        self.assertEqual(F.state_of(r), ('not-attached', 'placed in cells the image carries, but the build does not '
                                                         'attach it there'))
        # the data: both scripts run, and no script of the game waits for a cell the image has
        by_id = {x['id']: x for x in self.doc['scripts']}
        for sid in ('rerlas', 'fortloreboozeScript'):
            self.assertEqual(by_id[sid]['state'], 'runs', sid)
            self.assertTrue(sum(by_id[sid]['refs']['placed_in_image'].values()), sid)
        self.assertIn("'placed_in_image'", (ROOT / 'tools' / 'mwscript_features.py').read_text(encoding='utf-8'))

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
        refs = {'records', 'placed', 'placed_in_image', 'levelled', 'dialogue_starts', 'dialogue_speaker',
                'placed_by_scripts', 'made_by'}
        for r in self.doc['scripts']:
            self.assertLessEqual(set(r), allowed, r['id'])
            self.assertLessEqual(set(r['refs']), refs, r['id'])
            # made_by holds master names only ('dialogue' for a dialogue result), never script text
            self.assertLessEqual(set(r['refs'].get('made_by', [])), set(F.MASTERS) | {'dialogue'}, r['id'])
            self.assertIsInstance(r['error'], bool)

    def test_every_called_function_has_its_effect_in_play(self):
        """MWSCRIPT-IN-PLAY-PARITY-68: "carried out" is static; config/mwscript-effects.json says per function the
        game's scripts call whether the engine's effect in play is the original's (full, part, none), and the page
        shows it. A called function without a class, or a gap without its line, is refused."""
        eff = F.effects(F.EFFECTS)
        self.assertEqual(F.effect_problems(self.doc, eff), [])
        table = F.function_table(self.doc)
        self.assertLessEqual(set(table), set(eff['functions']))
        # the refusals: no class, a gap with no line, a full row with one, a class outside the list, no basis
        name = sorted(table)[0]
        for change, word in ((lambda e: e['functions'].pop(name), 'has no effect class'),
                             (lambda e: e['functions'][name].update(effect='part', missing=''), 'what is missing'),
                             (lambda e: e['functions'][name].update(effect='full', missing='x'), 'nothing missing'),
                             (lambda e: e['functions'][name].update(effect='mostly'), 'effect must be'),
                             (lambda e: e['functions'][name].update(basis='guess'), 'basis must be'),
                             (lambda e: e['functions'].update(nosuchfunction=dict(e['functions'][name])),
                              'is not in tools/mwscript/functions.py')):
            bad = copy.deepcopy(eff)
            change(bad)
            self.assertTrue(any(word in p for p in F.effect_problems(self.doc, bad)), word)
        # the page: the column, the counts and one row per gap with its line
        page = F.OUT.read_text(encoding='utf-8')
        self.assertIn('| Function | Group | Carried out | Effect in play |', page)
        self.assertIn('### Effect in play', page)
        gaps = [n for n in table if eff['functions'][n]['effect'] != 'full']
        self.assertGreater(len(gaps), 0)
        section = page.split('### Effect in play', 1)[1].split('\n## ', 1)[0]
        for n in gaps:
            e = eff['functions'][n]
            self.assertIn('| %s | %s |' % (n, F.EFFECT_LABELS[e['effect']]), section, n)
            self.assertIn(F._cell(e['missing']), section, n)
        # the static measure alone must not read as parity: a function carried out by the engine can be a gap
        self.assertTrue(any(F.FUNCTIONS[n].run for n in gaps))

    def test_effect_lines_are_public_text(self):
        """The lines of what is missing go on a public page: the file keeps the class, the line, the register IDs and
        the basis only, and a line names no source place (a file with a line number)."""
        eff = F.effects(F.EFFECTS)
        for n, e in eff['functions'].items():
            self.assertLessEqual(set(e), {'effect', 'missing', 'register', 'basis', 'in_play', 'checked'}, n)
            low = (e['missing'] + ' ' + ' '.join(s['what'] for s in e.get('in_play', ()))).casefold()
            for word in ('.c:', '.py:', '.cpp:', '.h:', ':/', ':\\', '.json', '.txt'):
                self.assertNotIn(word, low, n)

    def test_a_row_is_checked_again_when_its_register_entry_is_fixed(self):
        """MWSCRIPT-TRACKER-EFFECT-ROWS-STALE-69: the PlayBink row went on saying every video can be skipped after the
        fix had shipped, because nothing tied a register entry's fix to the row. Now a row names every register entry
        about its function and records, under "checked", the newest fix step of each one it was read against; a new
        step (fixed in source, shipped, confirmed in play, the fixed state) makes the row stale until it is checked."""
        eff = F.effects(F.EFFECTS)
        rows = eff['functions']
        register = F.register_entries()
        self.assertGreater(len(register), 1000)
        self.assertEqual(F.stale_effect_rows(rows, register), [])
        # the origin: PlayBink names its entry, was checked against its fix and is no longer "in part"
        play = rows['playbink']
        self.assertIn('MWSCRIPT-PLAYBINK-SKIP-FLAG-68', play['register'])
        self.assertEqual(play['checked']['MWSCRIPT-PLAYBINK-SKIP-FLAG-68'],
                         F.fix_mark(register['MWSCRIPT-PLAYBINK-SKIP-FLAG-68']))
        self.assertTrue(play['checked']['MWSCRIPT-PLAYBINK-SKIP-FLAG-68'].startswith('fixed in source: v0.0.69-dev3'))
        self.assertEqual((play['effect'], play['missing']), ('full', ''))
        # the old behaviour: the row as it was (no entry named) is refused, by the entry's own id
        old = copy.deepcopy(rows)
        old['playbink'].update(register=[], checked={})
        self.assertTrue(any('playbink: the register entry MWSCRIPT-PLAYBINK-SKIP-FLAG-68 is about this function'
                            in p for p in F.stale_effect_rows(old, register)))
        # an open entry about a function, with no fix step yet, may be filed without touching the rows
        opened = dict(register, **{'MWSCRIPT-PLAYBINK-NEW-FAULT-69': {'id': 'MWSCRIPT-PLAYBINK-NEW-FAULT-69',
                                                                      'state': 'open', 'closure': []}})
        self.assertEqual(F.stale_effect_rows(rows, opened), [])
        opened['MWSCRIPT-PLAYBINK-NEW-FAULT-69']['closure'] = [{'stage': 'fixed in source', 'where': 'v9.9.9 (x)'}]
        self.assertTrue(any('MWSCRIPT-PLAYBINK-NEW-FAULT-69 is about this function and has the fix step' in p
                            for p in F.stale_effect_rows(rows, opened)))
        # a fix step that comes later makes the row stale: a new closure step, and the fixed state with no steps
        name = next(n for n, e in sorted(rows.items()) if e['register'] and not e['checked'])
        rid = rows[name]['register'][0]
        later = copy.deepcopy(register)
        later[rid]['closure'] = [{'stage': 'fixed in source', 'where': 'v9.9.9 (abcdef12)'}]
        self.assertTrue(any('%s names %s, which has the fix step "fixed in source: v9.9.9 (abcdef12)"' % (name, rid)
                            in p for p in F.stale_effect_rows(rows, later)))
        later[rid]['closure'].append({'stage': 'confirmed in play', 'where': 'v9.9.9 (a session)'})
        seen = copy.deepcopy(rows)
        seen[name]['checked'] = {rid: 'fixed in source: v9.9.9 (abcdef12)'}
        self.assertTrue(any('confirmed in play' in p for p in F.stale_effect_rows(seen, later)))
        seen[name]['checked'] = {rid: F.fix_mark(later[rid])}
        self.assertEqual(F.stale_effect_rows(seen, later), [])
        later = copy.deepcopy(register)
        later[rid].update(state='fixed', fixed_in='v9.9.9', closure=[])
        self.assertEqual(F.fix_mark(later[rid]), 'fixed: v9.9.9')
        self.assertTrue(any('fixed: v9.9.9' in p for p in F.stale_effect_rows(rows, later)))
        # a named entry the register does not have, and a checked note for an entry the row does not name
        bad = copy.deepcopy(rows)
        bad[name]['register'] = rows[name]['register'] + ['NO-SUCH-ENTRY-69']
        self.assertTrue(any('NO-SUCH-ENTRY-69, which is not in the register' in p
                            for p in F.stale_effect_rows(bad, register)))
        bad = copy.deepcopy(rows)
        bad[name]['checked'] = {'NO-SUCH-ENTRY-69': 'x'}
        self.assertTrue(any('checked names NO-SUCH-ENTRY-69' in p for p in F.stale_effect_rows(bad, register)))
        # which entries are about a function: MWSCRIPT ids by any word, other ids by their first word, never an
        # everyday word (a JOURNAL entry is about the journal window, not the function Journal)
        some = {'MWSCRIPT-PLAYBINK-SKIP-FLAG-68': {}, 'GETPOS-X-1': {}, 'JOURNAL-PAGE-1': {}, 'UI-GETPOS-1': {},
                'MWSCRIPT-JOURNAL-INDEX-1': {}}
        self.assertEqual(F.entries_about('playbink', some), ['MWSCRIPT-PLAYBINK-SKIP-FLAG-68'])
        self.assertEqual(F.entries_about('getpos', some), ['GETPOS-X-1'])
        self.assertEqual(F.entries_about('journal', some), ['MWSCRIPT-JOURNAL-INDEX-1'])
        # the check command refuses it too (the pregate and this suite run it)
        self.assertTrue(any('MWSCRIPT-PLAYBINK-SKIP-FLAG-68' in p
                            for p in F.effect_problems(self.doc, dict(eff, functions=old), register)))

    def test_the_in_play_column(self):
        """MWSCRIPT-EFFECT-PARITY-69: what a play session has shown of a function's effect is kept per row (what,
        version, date) and drawn in its own column; a class known from play needs such a note, and a note says only
        what was seen."""
        eff = F.effects(F.EFFECTS)
        rows = eff['functions']
        for n, e in rows.items():
            self.assertIsInstance(e['in_play'], list, n)
        seen = {n: e for n, e in rows.items() if e['in_play']}
        self.assertIn('becomewerewolf', seen)
        self.assertIn('undowerewolf', seen)
        for n, e in seen.items():
            for s in e['in_play']:
                self.assertEqual(set(s), {'what', 'version', 'date'}, n)
        self.assertTrue(all(e['in_play'] for e in rows.values() if e['basis'] == 'play'))
        page = F.OUT.read_text(encoding='utf-8')
        section = page.split('### Effect in play', 1)[1].split('\n## ', 1)[0]
        self.assertIn('| Function | Effect | Scripts | Dialogue | What is missing | Known from | Seen in play | '
                      'Register |', section)
        for n, e in seen.items():
            self.assertIn(F._cell(F._seen(e)), section, n)
        self.assertIn('| not yet |', section)
        table = F.function_table(self.doc)
        c = F.effect_counts(table)
        self.assertEqual(c['seen_in_play'], sum(1 for n in table if rows[n]['in_play']))
        self.assertEqual(c['full'] + c['part'] + c['none'], c['called'])
        self.assertIn('%d functions have such a note' % c['seen_in_play'], section)
        # the refusals: a class known from play with no note, a note without its date
        name = next(n for n in sorted(table) if not rows[n]['in_play'])
        bad = copy.deepcopy(eff)
        bad['functions'][name]['basis'] = 'play'
        self.assertTrue(any('a class known from play needs its in_play note' in p
                            for p in F.effect_problems(self.doc, bad)))
        bad = copy.deepcopy(eff)
        bad['functions'][name]['in_play'] = [{'what': 'x', 'version': '0.0.69-dev5'}]
        self.assertTrue(any('in_play is a list of notes' in p for p in F.effect_problems(self.doc, bad)))
        # the werewolf rows say what was seen and keep what is not handled in their line
        wolf = rows['becomewerewolf']
        self.assertEqual(wolf['effect'], 'part')
        for word in ('doubled health', 'witnesses', 'refusal to take', 'camera height', 'silver weapons', 'sounds'):
            self.assertIn(word, wolf['missing'], word)
        self.assertNotIn('to be seen in play', wolf['missing'])
        self.assertIn('werewolf body', F._seen(wolf))


if __name__ == '__main__':
    unittest.main()
