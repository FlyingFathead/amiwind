# SPDX-License-Identifier: GPL-3.0-only
"""The world-wide check of the dialogue choices (tools/dialogue_choices.py, DIALOGUE-CHOICES-62): every Choice of the
masters, branch by branch, with whether its answer is one the engine's runner can pick. Synthetic records for the
rules; the measured file (docs/dialogue-choices.json, from the game data) for its counts and the engine's limits."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import dialogue_choices as C  # noqa: E402
from mwad.dialogue import FUNCTIONS  # noqa: E402
from test_greeting_lut import f, info  # noqa: E402


def fn(name, op, value):
    """An SCVR function condition (kind 1, its number, the comparison)."""
    return ('01%02d%d' % (FUNCTIONS.index(name), op), value)


CHOICE1, CHOICE2 = fn('Choice', 0, 1), fn('Choice', 0, 2)
GOLD_AT_LEAST, GOLD_UNDER = ('05IX3gold_001', 50), ('05IX4gold_001', 50)


def said(fields, script):
    return fields + [f('BNAM', script)]


TOPICS = {
    # the roadside robber's shape: both branches reachable (the gold is read live)
    'proposition': [info('p1', 'Steel, then.', kind=0, ONAM='robber', scvr=[CHOICE2]),
                    info('p2', 'Wise.', kind=0, ONAM='robber', scvr=[CHOICE1, GOLD_AT_LEAST]),
                    info('p3', 'No gold?', kind=0, ONAM='robber', scvr=[CHOICE1, GOLD_UNDER]),
                    said(info('p4', 'Pay up.', kind=0, ONAM='robber'),
                         '; the demand\nChoice "Fine." 1, "Never!" 2 ; pay or fight')],
    # answers that read a function only by its start value (PcVampire) and one the runner never reads (Weather)
    'night talk': [info('v1', 'Kin.', kind=0, ONAM='lady', scvr=[CHOICE1, fn('PcVampire', 0, 1)]),
                   info('v2', 'Rain.', kind=0, ONAM='lady', scvr=[CHOICE2, fn('Weather', 0, 4)]),
                   said(info('v3', 'Well?', kind=0, ONAM='lady'), 'Choice "Yes" 1 "No" 2')],
    # an answer that always passes before the branch answers (the original's data has a few)
    'stay': [info('s0', 'I follow.', kind=0, ONAM='guard'),
             info('s1', 'Here.', kind=0, ONAM='guard', scvr=[CHOICE1]),
             said(info('s2', 'Stay?', kind=0, ONAM='guard', scvr=[('03sX0waiting', 1)]), 'Choice "Stay" 1')],
    # no answer with a Choice filter: the topic's first answer is said again (plain); another speaker's answer
    # is not this speaker's
    'tale': [info('t0', 'Other.', kind=0, ONAM='bard', scvr=[CHOICE1]),
             said(info('t1', 'Once upon a time.', kind=0, ONAM='sage', scvr=[('04JX3a_quest', 10)]),
                  'CHOICE "Continue" 1')],
    # nothing answers it: the offer itself needs a function the runner never reads
    'storm': [said(info('w1', 'Storm.', kind=0, ONAM='sage', scvr=[fn('Weather', 0, 4)]), 'Choice "Go on" 7')],
}


class Rules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        got = C.audit(TOPICS, 'test.esm')
        cls.counts = got['counts']
        cls.by = {(r['topic'], r['choice']): r for r in got['branches']}

    def test_calls_are_parsed_with_comments_and_commas(self):
        self.assertEqual(C.choice_calls('; Choice "x" 9\nChoice "Fine." 1, "Never!" 2 ; pay or fight\n'
                                        'if ( x == 1 )\n  choice "A;B" 3 "C" 4\nendif'),
                         [[('Fine.', 1), ('Never!', 2)], [('A;B', 3), ('C', 4)]])
        self.assertEqual(C.choice_calls('Journal "x" 10\nGoodbye'), [])

    def test_each_branch_by_number(self):
        self.assertEqual(self.by[('proposition', 1)]['status'], 'reachable')
        self.assertEqual(self.by[('proposition', 1)]['answer'], 'p2')       # the first that can pass: with the gold
        self.assertEqual(self.by[('proposition', 2)]['status'], 'reachable')
        self.assertEqual(self.by[('proposition', 2)]['answer'], 'p1')
        self.assertEqual(self.by[('night talk', 1)]['status'], 'start_value')
        self.assertEqual(self.by[('night talk', 1)]['why'], ['PcVampire'])
        self.assertEqual(self.by[('night talk', 2)]['status'], 'unread')
        self.assertEqual(self.by[('night talk', 2)]['why'], ['Weather'])
        self.assertEqual(self.by[('stay', 1)]['status'], 'shadowed')
        self.assertEqual(self.by[('stay', 1)]['answer'], 's0')
        self.assertEqual(self.by[('tale', 1)]['status'], 'plain')
        self.assertEqual(self.by[('tale', 1)]['answer'], 't1')
        self.assertEqual(self.by[('storm', 7)]['status'], 'none')

    def test_counts_add_up(self):
        c = self.counts
        self.assertEqual((c['infos_with_choice'], c['calls'], c['branches'], c['max_options']), (5, 5, 7, 2))
        self.assertEqual(sum(c['status'].values()), c['branches'])
        self.assertEqual(c['max_text'], len('Continue'))

    def test_runner_reads_what_the_table_reads(self):
        import dialogue_lut as D
        for name in D.LIVE_FUNCTIONS:
            self.assertEqual(C.classify(name), 'read')
        self.assertEqual(C.classify('PcVampire'), 'start')
        self.assertEqual(C.classify('Weather'), 'never')
        self.assertEqual(C.classify('Item'), 'read')


class Measured(unittest.TestCase):
    def test_file_valid_and_engine_limits_hold(self):
        doc = json.loads(C.OUT.read_text(encoding='utf-8'))
        self.assertEqual(C.problems(doc), [])
        self.assertTrue(doc['masters'][C.TABLE_MASTER]['in_table'])
        win = (ROOT / 'engine/aga/src/aw_dialwin.c').read_text(encoding='utf-8')
        choices = int(re.search(r'#define CHOICES (\d+)', win).group(1))
        chars = int(re.search(r'#define CHOICE_CHARS (\d+)', win).group(1))
        for master, c in doc['masters'].items():
            self.assertLessEqual(c['max_options'], choices, master)
            self.assertLess(c['max_text'], chars, master)
        # no game text in the public file: ids, numbers and states only
        for row in doc['not_reachable']:
            self.assertEqual(set(row), {'master', 'topic', 'info', 'speaker', 'choice', 'status', 'answer', 'why'})


if __name__ == '__main__':
    unittest.main()
