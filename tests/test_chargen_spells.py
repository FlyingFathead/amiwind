# SPDX-License-Identifier: GPL-3.0-only
"""CHARGEN-ABILITY-DESCRIPTIONS-65: the birthsign window and the race window's View Stats box list every ability,
power and spell with what it does (docs/CHARACTER_CREATION.md "What the abilities do"): the rules natively
(tests/aga_spelllist_test.c), both windows drawn and measured (tests/aga_spelllist_windows_test.c), and the wiring."""
import os
import re
import shutil
import unittest
from pathlib import Path

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class SpellListNativeTests(unittest.TestCase):
    def test_effect_lines_groups_and_scroll_limits(self):
        native.NativeSourceTests().compile_run('aga_spelllist_test.c',
                                               [SRC / 'aw_spelllist_rules.c', SRC / 'aw_fxrow_rules.c'], cflags=UBSAN)

    def test_both_windows_drawn_and_measured(self):
        native.NativeSourceTests().compile_run('aga_spelllist_windows_test.c', [SRC / n for n in (
            'aw_character.c', 'aw_ui.c','aw_console_glyphs.c', 'aw_spelllist.c', 'aw_spelllist_rules.c',
            'aw_fxrow_rules.c', 'aw_story.c', 'aw_state.c', 'aw_save_codec.c', 'aw_clock.c')], cflags=UBSAN)


class SpellListWiringTests(unittest.TestCase):
    def test_the_windows_use_the_panel_and_keep_the_names_without_it(self):
        ch = code('aw_character.c')
        self.assertIn('if(spell_panel(&px,&py,&pw,&ph))aw_chargen_spells_draw(px,py,pw,ph);', ch)
        self.assertIn('else{\n                for(i=0;i<sign_spell_count;i++){', (SRC / 'aw_character.c').read_text(encoding='utf-8'))
        self.assertIn('if(menu==3 && spell_panel_key(key))return 1;', ch)
        self.assertIn('if(spell_panel_key(key))return 1;', ch)
        self.assertIn('AW_SpellListInit();', code('aw_debug.c'))
        self.assertIn('aw_fxrow.c aw_spelllist_rules.c aw_spelllist.c', (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8'))

    def test_read_once_per_sign_never_while_drawing(self):
        glue = code('aw_spelllist.c')
        draw = glue[glue.index('static void draw_list'):glue.index('static void scroll_list')]
        for call in ('AW_ActorSpell', 'AW_FxSmallIcons', 'COM_FOpenFile', 'AW_StatBirthSpells', 'AW_StatRaceSpells'):
            self.assertNotIn(call, draw)
        self.assertIn('if(race==shown_race && birth==shown_birth && w==shown_w)return list.rows;', glue)

    def test_docs(self):
        doc = (ROOT / 'docs' / 'CHARACTER_CREATION.md').read_text(encoding='utf-8')
        self.assertIn('### What the abilities do (v0.0.66)', doc)
        self.assertIn('MWSpellEffect::updateWidgets', doc)


if __name__ == '__main__':
    unittest.main()
