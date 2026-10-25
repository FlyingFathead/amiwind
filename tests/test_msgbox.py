# SPDX-License-Identifier: GPL-3.0-only
"""The scripts' MessageBox (v0.0.51): the rules alone (tests/aga_msgbox_test.c) and the engine's wiring.

The compiler and the interpreter's side (the opcode, the host call, GetButtonPressed read once) are in
tests/test_mwscript.py.
"""
import os
import shutil
import unittest
from pathlib import Path

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']


def code(name):
    return (SRC / name).read_text(encoding='utf-8')


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class RuleTests(unittest.TestCase):
    def test_format_seconds_keys_and_the_choice_once(self):
        native.NativeSourceTests().compile_run('aga_msgbox_test.c', [SRC / 'aw_msgbox_rules.c'], cflags=UBSAN)


class EngineWiringTests(unittest.TestCase):
    def test_hooks_set_at_the_first_box_and_called_beside_the_death_prompt(self):
        box = code('aw_msgbox.c')
        self.assertIn('aw_msgbox_key=AW_MsgBoxGameKey;aw_msgbox_draw=AW_MsgBoxDraw;aw_msgbox_active=AW_MsgBoxActive;',
                      box)
        keys = code('keys.c')
        self.assertLess(keys.index('aw_view_key(key)) return;'), keys.index('aw_msgbox_key(key)) return;'))
        screen = code('screen.c')
        self.assertLess(screen.index('aw_view_draw ();'), screen.index('aw_msgbox_draw ();'))
        # a box with buttons stops the world (MenuMode reads it through AW_ModalWorldFrozen)
        ui = code('aw_ui.c')
        self.assertIn('death_prompt() || message_box()) && modal_world_ready()', ui)
        self.assertIn('AW_GalleryModal() || death_prompt() || message_box();', ui)

    def test_host_reads_the_strings_and_clears_the_box_without_a_game(self):
        host = code('aw_mwhost.c')
        self.assertIn('AW_MsgBoxFormat(shown,sizeof(shown),format,numbers,number);', host)
        self.assertIn('host_object,host_message,\n    host_button};', host)
        self.assertIn('!sv_player){AW_MsgBoxClear();return;}', host)
        # no C library floating-point formatting in the engine (aw_format.c)
        self.assertNotIn('snprintf(', code('aw_msgbox_rules.c').replace('Q_snprintf(', ''))

    def test_built_into_the_engine(self):
        make = (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8')
        self.assertIn('aw_mwhost.c aw_msgbox_rules.c aw_msgbox.c', make)


if __name__ == '__main__':
    unittest.main()
