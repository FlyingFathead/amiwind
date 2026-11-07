# SPDX-License-Identifier: GPL-3.0-only
"""The sweep (aw_sweep.c, dbg sweep) and actors hidden on purpose (SCRIPT-ENABLED-ACTOR-NOT-DRAWN-62, v0.0.62).

An actor a script disabled (the world change list: Startup's story characters, the falling mage before his journal
enables him) or one the opening hides (the ship's guards once the player is ashore) has its model taken off and its
model name kept. The sweep counted them as "actor without a model", so every new game at Seyda Neen reported five
false failures and hid real ones. Now: such an actor is counted as hidden on purpose; a script-disabled actor that is
still drawn is a failure; an actor enabled again without its model stays a failure ("without a model"), so the
sweep catches an Enable that does not bring the actor back. The Enable path itself (aw_mwhost.c ledger_object
AWM_ENABLE: the hidden edict's model and solidity back, the row's disabled flag cleared) is checked here too."""
from pathlib import Path
import re
import unittest

SRC = Path(__file__).resolve().parents[1] / 'engine/aga/src'


def body(name, head):
    """The text of the C function in NAME starting at HEAD, to its closing brace at column 0."""
    text = (SRC / name).read_text(encoding='utf-8')
    at = text.index(head)
    end = text.index('\n}\n', at)
    return text[at:end + 2]


class SweepHiddenTests(unittest.TestCase):
    def test_hidden_reasons(self):
        why = body('aw_sweep.c', 'static int hidden_reason(edict_t *e)')
        self.assertIn('AW_ObjectDisabled', why)             # the world change list's answer for the reference
        self.assertIn('aw_story_hidden', why)               # the opening's story-hidden placements
        self.assertIn('AW_IntroRole(4)', why)
        self.assertIn('AW_IntroRole(5)', why)

    def test_actors_counts_hidden_apart(self):
        actors = body('aw_sweep.c', 'static void actors(const int *map)')
        # disabled and still drawn: a failure of its own
        self.assertIn('fail("disabled by a script but drawn"', actors)
        # hidden on purpose (no model, a model name kept): counted, not failed, before the "without a model" failure
        hidden = actors.index('if(!m && why && e->v.model && pr_strings[e->v.model])')
        failed = actors.index('fail("actor without a model"')
        self.assertLess(hidden, failed)
        self.assertIn('hidden on purpose: %ld disabled by a script, %ld by the opening', actors)

    def test_enable_shows_the_edict_and_clears_the_row(self):
        ledger = body('aw_mwhost.c', 'static int32_t ledger_object(uint32_t ref,int op,int32_t value)')
        enable = ledger[ledger.index('case AWM_ENABLE:'):ledger.index('case AWM_DISABLE:')]
        self.assertIn('r->fields&=~AW_LEDGER_DISABLED', enable)
        self.assertIn('ledger_show(ref)', enable)
        self.assertIn('AW_LedgerTidy(&aw_ledger,ref)', enable)
        show = body('aw_mwhost.c', 'static void ledger_show(uint32_t ref)')
        self.assertTrue(re.search(r'e->v\.modelindex=h->model;e->v\.solid=h->solid;SV_LinkEdict\(e,false\);', show))

    def test_say_is_counted(self):
        # a script's Say (the falling mage's two screams through the player) leaves a trace in aw_mwscript_status
        say = body('aw_mwhost.c', 'static void host_say(int instance,int target,int voice,int text)')
        self.assertIn('says_missed++;return;', say)
        self.assertIn('says_started++', say)
        status = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        self.assertIn('"Say: %lu started, %lu not started (no actor, voice or sample); last on entity %d, %.1f s\\n"',
                      status)


if __name__ == '__main__':
    unittest.main()
