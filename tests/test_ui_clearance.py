# SPDX-License-Identifier: GPL-3.0-only
"""UI-TEXT-BOX-CLEARANCE-64: every text box measured in pixel rows (tests/aga_ui_clearance_test.c): the clear rows
between the frame and the first and last lines' ink, and between lines, at the shipped font size."""
import os
import shutil
import unittest
from pathlib import Path

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class TextBoxClearanceTests(unittest.TestCase):
    def test_every_text_box_keeps_its_clear_rows(self):
        native.NativeSourceTests().compile_run('aga_ui_clearance_test.c', [SRC / 'aw_ui.c', SRC / 'aw_msgbox_rules.c', SRC / 'aw_tutorial_rules.c'],
                                               cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'])


class TextPanelWiringTests(unittest.TestCase):
    def test_the_opening_hint_goes_through_the_panel(self):
        intro = (SRC / 'aw_intro.c').read_text(encoding='utf-8')
        self.assertIn('AW_UITextPanel(0,vid.height,vid.width,vid.height-y,', intro)
        header = (SRC / 'quakedef.h').read_text(encoding='utf-8')
        self.assertIn('#define AW_UI_TEXT_CLEAR 4', header)


if __name__ == '__main__':
    unittest.main()
