# SPDX-License-Identifier: GPL-3.0-only
"""OPENING-SHIP-DOCK-SCRIPTS-HAND-ACTED-69: what the clerk's script disables (the ship's two dock-side guards and its
props) is disabled on the world change list, as a script's Disable does it, not only hidden by the opening's own role
rule. Read from the engine's source: the hook, who sets it, who calls it and when."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'


def body(text, head):
    """The text of the function whose definition line starts with HEAD, up to the next line that is a lone brace."""
    at = text.index(head)
    return text[at:text.index('\n}\n', at)]


class OpeningShipDisableTests(unittest.TestCase):
    def setUp(self):
        self.opening = (SRC / 'aw_opening.c').read_text(encoding='latin-1')
        self.host = (SRC / 'aw_mwhost.c').read_text(encoding='latin-1')

    def test_the_hook_is_a_scripts_disable(self):
        self.assertIn('int (*aw_opening_disable)(unsigned reference);', self.opening)
        self.assertIn('extern int (*aw_opening_disable)(unsigned reference);',
                      (SRC / 'quakedef.h').read_text(encoding='latin-1'))
        self.assertIn('aw_opening_disable=opening_disable;', self.host)
        fn = body(self.host, 'static int opening_disable(unsigned reference){')
        # the same operation a script's Disable runs (the change list's DISABLED row, or the older object table)
        self.assertIn('object_op(reference,AWM_DISABLE,0);', fn)

    def test_the_guards_and_the_story_hidden_rows_are_disabled_by_reference(self):
        fn = body(self.opening, 'static void ship_refs_disable(void)')
        self.assertIn('"aw_story_hidden"', fn)
        self.assertIn('AW_IntroRole(4)', fn)
        self.assertIn('AW_IntroRole(5)', fn)
        self.assertIn('"aw_ref"', fn)
        self.assertIn('aw_opening_disable(reference)', fn)
        # only on the dock map, only once the census office has been entered, only with the scripts' hook
        self.assertRegex(fn, r'if\(!aw_opening_disable \|\| strcmp\(sv\.name,"seyda"\) \|\| !aw_story\.ship_disabled\)return;')

    def test_the_spawn_asks_for_it_and_the_first_tick_does_it_also_after_the_opening(self):
        spawn = body(self.opening, 'void AW_OpeningSpawn(void)')
        block = spawn[spawn.index('if(aw_story.ship_disabled && !strcmp(sv.name,"seyda")){'):]
        self.assertIn('ship_refs_pending=1;', block)
        # the hide at the spawn stays: nothing of them is drawn in the map's first frame
        self.assertIn('hide(AW_IntroRole(4));', block)
        self.assertIn('hide(AW_IntroRole(5));', block)
        self.assertIn('ship_refs_pending=0;', spawn[:spawn.index('if(aw_story.stage==AW_STAGE_DEMO)return;')])
        tick = body(self.opening, 'int AW_OpeningTick(void)')
        done = tick.index('if(ship_refs_pending)ship_refs_disable();')
        # before the tick's early returns: a visit to the dock after the opening, or a loaded game, gets the rows too
        self.assertLess(done, tick.index('if(!AW_StoryRestricted())return 0;'))
        self.assertLess(done, tick.index('if(AW_ReaderActive())return 1;'))

    def test_the_status_line_says_how_many(self):
        status = body(self.opening, 'void AW_OpeningDockStatus(void)')
        self.assertTrue(re.search(r'Opening ship references disabled %lu', status))


if __name__ == '__main__':
    unittest.main()
