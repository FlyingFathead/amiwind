# SPDX-License-Identifier: GPL-3.0-only
"""The dialogue feature tracker (tools/dialogue_features.py, DIALOGUE-COMPLETE-58): the JSON is valid, every register
ID exists, the generated page is current, the measured counts add up, and the table tool's list of the functions the
engine reads live is the engine's own (aw_glut.c builtins plus aw_mwhost.c's live hooks), so the counts the page shows
are the engine's."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import dialogue_features as F  # noqa: E402
import dialogue_lut as D  # noqa: E402
from mwad.dialogue import FUNCTIONS  # noqa: E402


class Tracker(unittest.TestCase):
    def test_json_valid_and_page_current(self):
        doc = F.load()
        self.assertEqual(F.problems(doc, F.register_ids()), [])
        self.assertEqual(F.OUT.read_text(encoding='utf-8'), F.render(doc),
                         'docs/DIALOGUE_FEATURES.md is stale: run tools/dialogue_features.py render')

    def test_every_part_of_the_mandate_has_a_row(self):
        ids = {f['id'] for f in F.load()['features']}
        for part in ('greeting', 'topic-list', 'first-match', 'info-refusal', 'conditions', 'disposition',
                     'disposition-bar', 'links-known', 'links-explicit', 'choices', 'goodbye', 'result-scripts',
                     'exhausted', 'journal-topics', 'journal-quests', 'known-topics', 'defines', 'persuasion', 'fight',
                     'services', 'creatures', 'addons', 'answer-voice', 'greeting-voice', 'openmw-ab'):
            self.assertIn(part, ids)

    def test_validation_catches_mistakes(self):
        doc = F.load()
        bad = dict(doc, features=[dict(doc['features'][0], state='finished')])
        self.assertTrue(any('state' in p for p in F.problems(bad)))
        bad = dict(doc, measured=dict(doc['measured'], conditions=dict(doc['measured']['conditions'], live=1)))
        self.assertTrue(any('total' in p for p in F.problems(bad)))
        bad = dict(doc, features=[dict(doc['features'][0], bugs=['NO-SUCH-BUG-99'])])
        self.assertTrue(any('NO-SUCH-BUG-99' in p for p in F.problems(bad, F.register_ids())))
        deferred = dict(doc, features=[dict(f, deferral={'words': 'later', 'date': '2026-11-01'})
                                       for f in doc['features']])
        self.assertEqual(F.blocking(deferred), [])
        self.assertTrue(F.blocking(doc))

    def test_live_functions_are_the_engines(self):
        glut = (ROOT / 'engine/aga/src/aw_glut.c').read_text(encoding='utf-8')
        host = (ROOT / 'engine/aga/src/aw_mwhost.c').read_text(encoding='utf-8')
        header = (ROOT / 'engine/aga/src/aw_glut.h').read_text(encoding='utf-8')
        defines = {k: int(v) for k, v in re.findall(r'#define (AW_GLUT_FN_\w+) (\d+)', header)}
        builtins = {defines[name] for name in re.findall(r'case (AW_GLUT_FN_\w+):', glut)}
        body = host.split('static int live_function', 1)[1].split('\n}\n', 1)[0]
        hooked = {int(n) for n in re.findall(r'fn==(\d+)', body)}
        for low, high in re.findall(r'fn>=(\d+) && fn<=(\d+)', body):
            hooked |= set(range(int(low), int(high) + 1))
        self.assertEqual({FUNCTIONS[i] for i in builtins | hooked}, set(D.LIVE_FUNCTIONS))

    def test_coverage_counts_add_up(self):
        sys.path.insert(0, str(ROOT / 'tests'))
        from test_dialogue_lut import DIALS, TOPICS, kinds
        raw, report = D.build(kinds(), TOPICS, DIALS)
        cov = report['coverage']
        self.assertEqual(sum(cov['conditions'].values()), len(D.read(raw)['conds']))
        a = cov['answers']
        self.assertEqual(a['reachable'] + a['unreachable'], a['total'])
        self.assertEqual(cov['conditions']['never'], 0)        # the synthetic data names no unread function

    def test_engage_tick_reads_no_file(self):
        # DIALOGUE-FIGHT-DISPOSITION-57: a disk read in a fight stutters on the Amiga. The aggro's facts (the record's
        # Fight, an NPC's own disposition facts and its actor row) are read when the slot is made; the engage tick up
        # to the rating test reads nothing. The sheet read after it is the start of the fight itself.
        src = ROOT / 'engine/aga/src'

        def body(path, head):
            text = (src / path).read_text(encoding='utf-8')
            return text.split(head, 1)[1].split('\n}\n', 1)[0]
        reads = ('fread', 'fseek', 'COM_FOpenFile', 'AW_ActorFind', 'read_string', 'AW_ActorBase', 'AW_GlutSpeaker',
                 'AW_MwscriptDispositionFacts', 'AW_DialNpcPrepare', 'AW_CombatActorLoad', 'load()', 'aggro_facts(')
        tick = body('aw_ambient.c', 'static void aggro(slot_t *s) {').split('AW_CombatHostiles()', 1)[0]
        for part in (tick, body('aw_dialwin.c', 'int AW_DialNpcDisposition(edict_t *e,const aw_dial_npc_cache_t *c){'),
                     body('aw_mwhost.c', 'void AW_MwscriptDispositionNow(int actor_row,')):
            for word in reads:
                self.assertNotIn(word, part)
        self.assertIn('if(aggro_on)aggro_facts(s);', body('aw_ambient.c', 'static slot_t *start('))
        self.assertIn('AW_DialNpcPrepare(s->e,&s->disp);', body('aw_ambient.c', 'static void aggro_facts(slot_t *s) {'))

    def test_window_words_match_the_table(self):
        # aw_dial.h's AW_DIAL_TEXT_* are tools/dialogue_lut.py UI_TEXTS in order (the skills last)
        header = (ROOT / 'engine/aga/src/aw_dial.h').read_text(encoding='utf-8')
        enum = header.split('enum {AW_DIAL_TEXT_PERSUASION', 1)[1].split('};', 1)[0]
        named = ['PERSUASION'] + re.findall(r'AW_DIAL_TEXT_(\w+)', enum)
        self.assertEqual(named.index('SKILL0') + 27, len(D.UI_TEXTS))
        self.assertEqual([n for n, _ in D.UI_TEXTS][named.index('SKILL0')], 'sSkillBlock')
        self.assertEqual(D.UI_TEXTS[named.index('TRAINING_WORDS')][0], 'sServiceTrainingWords')

    def test_training_waits_for_level_up(self):
        # the tracker's note: a trained skill counts toward level progress once LEVEL-UP-58 lands
        window = (ROOT / 'engine/aga/src/aw_dialwin.c').read_text(encoding='utf-8')
        train = window.split('static void train(int k){', 1)[1].split('\n}\n', 1)[0]
        self.assertIn('LEVEL-UP-58', train)

    def test_use_key_talks_to_a_travel_provider(self):
        # OpenMW: using a travel provider opens the conversation; Travel is chosen there (services row). The use key
        # opens the menu straight away only for a provider without a dialogue row.
        scene = (ROOT / 'engine/aga/src/aw_scene.c').read_text(encoding='utf-8')
        use = scene.split('int AW_SceneUse(void) {', 1)[1].split('\n}\n', 1)[0]
        self.assertIn('!travel_by_talk() && travel_use()', use)
        talk = scene.split('static int travel_by_talk(void) {', 1)[1].split('\n}\n', 1)[0]
        self.assertIn('AW_GlutNpcOf(e)>=0', talk)
        window = (ROOT / 'engine/aga/src/aw_dialwin.c').read_text(encoding='utf-8')
        self.assertIn('AW_SceneTravelOffers(speaker)', window)
        self.assertIn('AW_SceneTravelWith(e)', window)

    def test_script_strings_read_once(self):
        # DIALOGUE-CLOSE-FRAME-FREEZE-59: a conversation's greeting reads the speaker's race for every SameRace /
        # SameSex test; each read_string opened id1/mwscript.awm, so opening a talk stood still ~14 s. The short
        # strings are kept after the first read: the cache is looked up before the file is opened, a cut string is
        # never kept, the cache is reset when the file loads, and the window's open time is in the console.
        host = (ROOT / 'engine/aga/src/aw_mwhost.c').read_text(encoding='utf-8')
        body = host.split('static int read_string(int index,char *out,int capacity){', 1)[1].split('\n}\n', 1)[0]
        self.assertLess(body.index('str_cache[i].index==index'), body.index('COM_FOpenFile'))
        self.assertIn('n<capacity-1', body.split('COM_FOpenFile', 1)[1])
        load = host.split('static int load(void){', 1)[1].split('\n}\n', 1)[0]
        self.assertIn('string_cache_clear();', load)
        window = (ROOT / 'engine/aga/src/aw_dialwin.c').read_text(encoding='utf-8')
        opened = window.split('int AW_DialWindowOpen(edict_t *e,const char *greeting,int again){', 1)[1]
        self.assertIn('Dialogue: window open in %d ms', opened.split('\n}\n', 1)[0])


if __name__ == '__main__':
    unittest.main()
