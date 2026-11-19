# SPDX-License-Identifier: GPL-3.0-only
"""CHARGEN-ABILITY-DESCRIPTIONS-65: the birthsign window and the race window's View Stats box list every ability,
power and spell with what it does (docs/CHARACTER_CREATION.md "What the abilities do"): the rules natively
(tests/aga_spelllist_test.c), both windows drawn and measured (tests/aga_spelllist_windows_test.c), and the wiring."""
import os
import re
import shutil
import struct
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


class BirthsignSpellRowsTests(unittest.TestCase):
    """CHARGEN-ABILITY-DESCRIPTIONS-STOP-67: every birthsign's spells have their rows in the actor table (the window
    lists a sign's spells by those rows and the new character gets them by the same rows). On the v0.0.67-dev2 image 15
    of the 19 spells of the base game's 13 signs had none (no actor, race or start rule named them), so the window
    showed text for the first two signs only and the character never got those spells."""

    @staticmethod
    def build(extra=b''):
        import tempfile
        import struct as st
        sys_path_tools()
        from mwscript.gamedata import GameData
        from mwscript.compiler import compile_program, bindings
        from mwscript import awms
        import actor_stats
        from test_actorstate import master_bytes, record, sub, npcs
        tmp = Path(tempfile.mkdtemp(prefix='aw-signs-'))
        try:
            signs = b''
            if extra:
                # a sign with an ability no actor names (with its effect), one an NPC names, and an id the masters lack
                signs = (record('SPEL', sub('NAME', 'sign only ability'), sub('FNAM', 'Sign Only'),
                                sub('SPDT', st.pack('<3i', 1, 0, 0)),
                                sub('ENAM', st.pack('<hbbiiiii', 14, -1, -1, 0, 0, 0, 25, 25)))
                         + record('BSGN', sub('NAME', 'Test Sign'), npcs('sign only ability'), npcs('test spell'),
                                  npcs('no such spell')))
            (tmp / 'Morrowind.esm').write_bytes(master_bytes() + signs)
            data = GameData().load(tmp)
            prog, compiled = compile_program(data, handwritten=())
            raw, _ = awms.write(prog, compiled, bindings(prog, compiled))
            return actor_stats.spell_rows(raw), raw
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_every_sign_spell_gets_a_row_after_every_other_row(self):
        before, _ = self.build()
        after, raw = self.build(extra=True)
        self.assertNotIn('sign only ability', before)
        self.assertIn('sign only ability', after)
        # the rows the table had keep their numbers; the sign's spell comes after them
        for spell, row in before.items():
            self.assertEqual(after[spell], row, spell)
        self.assertEqual(after['sign only ability'], max(before.values()) + 1)
        self.assertNotIn('no such spell', after)
        # its effect is the table's too (the window's effect line)
        sys_path_tools()
        from mwscript import awms
        f = awms.read(raw)
        first, count = struct.unpack_from('>HB', f['ASPE'], 4 * after['sign only ability'])
        self.assertEqual(count, 1)
        self.assertEqual(struct.unpack_from('>h', f['AEFF'], 14 * first)[0], 14)

    def test_a_sign_spell_without_a_row_is_named_and_refused(self):
        sys_path_tools()
        import actor_stats
        from test_actor_stats import data
        recs, gmst, rows = data()      # the synthetic masters' sign "Test Sign": test spell, other spell
        voc = actor_stats.read_vocabulary(actor_stats.write_vocabulary(recs, gmst))
        tables = actor_stats.shared_tables(voc)
        _, report = actor_stats.shared_section([], voc, rows, tables)
        self.assertEqual(report['birth_spells_missing'], [])
        rows = {k: v for k, v in rows.items() if k != 'other spell'}
        _, report = actor_stats.shared_section([], voc, rows, tables)
        self.assertEqual(report['birth_spells_missing'], ['test sign: other spell'])
        area = (ROOT / 'tools' / 'prepare_area_tables.py').read_text(encoding='utf-8')
        self.assertIn("if spell_row and shared_report.get('birth_spells_missing'):", area)
        self.assertIn("raise ValueError('birthsign spells without a row in id1/mwscript.awm", area)


def sys_path_tools():
    """src before tools (tools/mwad.py must not shadow the src/mwad package: TEST-WORKER-SYSPATH-32), tests after."""
    import sys
    for p in (ROOT / 'tests', ROOT / 'tools', ROOT / 'src'):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))


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
