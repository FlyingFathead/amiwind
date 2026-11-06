# SPDX-License-Identifier: GPL-3.0-only
"""dbg kill and the essential-death message (DBG-KILL-60). The engine wiring is checked as source contracts (the
pick mode is the companion pick's, the kill is chim actors kill's call), the builder's data with synthetic records."""
import re
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


def body(text, name):
    start = text.index('{', text.index(name))
    depth = 0
    for i in range(start, len(text)):
        depth += {'{': 1, '}': -1}.get(text[i], 0)
        if depth == 0:
            return text[start:i + 1]
    raise ValueError(name)


class DbgKillTests(unittest.TestCase):
    def test_pick_mode_is_the_companion_pick(self):
        comp = code('aw_companion.c')
        self.assertNotIn('"aw_kill"', comp)                  # no resident command of its own (the registry budget)
        self.assertIn('void AW_CompanionKillMode', comp)
        self.assertIn('"killpick"', code('aw_actors.c'))
        self.assertIn('"chim") && !strcmp(r->words,"kill")', code('aw_console.c'))
        act = body(comp, 'static void pick_act')
        self.assertIn('AW_CombatTestEngage(e,1)', act)      # the call chim actors kill makes
        self.assertIn('pick_npc(e)', act)                   # companion pick unchanged
        # the click handlers go through pick_act, so one red crosshair serves both modes
        self.assertEqual(comp.count('pick_act(t)'), 2)
        self.assertNotIn('pick_npc(t)', comp)
        # a right click and Escape leave the kill mode
        aim = body(comp, 'int AW_CompanionPickAim')
        self.assertIn('pick.kill', aim)
        self.assertIn('pick.kill=0', body(comp, 'static void pick_escape'))
        # dbg kill REF is chim actors kill REF
        self.assertIn('actors kill"', code('aw_console.c'))
        # a body is not a target
        self.assertIn('AW_CombatSlotState(pick.target,NULL)==2', body(comp, 'static edict_t *pick_target'))
        # one console line per kill
        self.assertIn('dbg kill: %s (ref %.0f) is dead', act)

    def test_catalogue_row(self):
        rows = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8').splitlines()
        mine = [r for r in rows if r.startswith('PLAYTESTING|kill|')]
        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0].split('|')[2], 'chim')
        doc = (ROOT / 'docs' / 'AMIWIND_CONSOLE_COMMANDS.md').read_text(encoding='utf-8')
        self.assertIn('`dbg kill`', doc)

    def test_essential_death_is_read_from_the_game_settings(self):
        combat = (SRC / 'aw_combat.c').read_text(encoding='utf-8')
        text = code('aw_combat.c')
        fn = body(text, 'static void essential_death')
        self.assertIn('AWR_ESSENTIAL', body(text, 'int AW_CombatEssentialRecord'))
        self.assertIn('"sKilledEssential "', combat)         # the key; the words are the game's, never typed here
        self.assertIn('view/settings.txt', fn)
        self.assertIn('AW_MsgBoxShow', fn)
        # every death (a fight, the test kill and, v0.0.61 PLAYER-CASTING-59, a spell's damage) calls it
        self.assertEqual(text.count('essential_death(s->e);'), 3)
        self.assertIn('essential_death(s->e);', body(text, 'int AW_CombatSpellHit'))
        self.assertNotIn('thread of prophecy', combat)

    def test_builder_exports_the_message_when_the_master_has_it(self):
        import prepare_player_view as v

        def kinds(with_text):
            gmst = {
                'fvanitydelay': [('NAME', b'fVanityDelay'), ('FLTV', struct.pack('<f', 30.0))],
                'sloadlastsavemsg': [('NAME', b'sLoadLastSaveMsg'), ('STRV', b"Last '%s'. Load it?")],
                'syes': [('NAME', b'sYes'), ('STRV', b'Yes')],
                'sno': [('NAME', b'sNo'), ('STRV', b'No')],
                'snotifymessage2': [('NAME', b'sNotifyMessage2'), ('STRV', b'Enemies near.')],
            }
            if with_text:
                gmst['skilledessential'] = [('NAME', b'sKilledEssential'), ('STRV', b'Test essential text.')]
            return {'GMST': gmst}
        self.assertIn('sKilledEssential', v.OPTIONAL_STRINGS)
        self.assertEqual(v.settings_text(kinds(True)).splitlines()[-1], 'sKilledEssential Test essential text.')
        self.assertNotIn('sKilledEssential', v.settings_text(kinds(False)))   # optional: a master without it still builds


if __name__ == '__main__':
    unittest.main()
