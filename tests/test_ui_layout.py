# SPDX-License-Identifier: GPL-3.0-only
"""UI-NO-SHARED-LAYOUT-67: the shared layout helper (engine/aga/src/aw_layout.c) and the check that fails the gate on a
text or button out of its box, a button too close to its box's bottom edge, or two texts on top of one another (the HUD
included). The host C fixture tests/aga_ui_layout_test.c draws through the real aw_ui.c and measures what it records:
the faults seen in v0.0.67-dev1 are caught, the screens on the helper show none. Seconds."""
import os
import re
import shutil
import unittest
from pathlib import Path

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class LayoutCheckNativeTests(unittest.TestCase):
    def test_the_check_catches_the_faults_and_the_helper_shows_none(self):
        # INVENTORY-ITEM-INFO-67: the item information box is measured too (aw_iteminfo.c, its lines in the console font)
        native.NativeSourceTests().compile_run('aga_ui_layout_test.c',
                                               [SRC / 'aw_ui.c', SRC / 'aw_layout.c', SRC / 'aw_msgbox_rules.c',
                                                SRC / 'aw_iteminfo.c', SRC / 'aw_console_glyphs.c'],
                                               cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'])


class LayoutSourceTests(unittest.TestCase):
    def test_every_number_is_in_the_one_table(self):
        layout = code('aw_layout.c')
        self.assertIn('const aw_layout_metrics_t aw_layout_metrics={', layout)
        # the message box's button rows stand the table's bottom margin above the frame's inner edge
        rules = code('aw_msgbox_rules.c')
        self.assertIn('#define MSGBOX_FOOT (aw_layout_metrics.edge+aw_layout_metrics.bottom_margin-4)', rules)
        self.assertIn('rect[1]=frame[1]+frame[3]-rows*24+row*24-2-MSGBOX_FOOT;', rules)

    def test_what_is_drawn_is_recorded_for_the_check(self):
        ui = code('aw_ui.c')
        self.assertIn('if(AW_LayoutRecording)record_text(x,y,text);', ui)
        self.assertIn('if(!recording_button)AW_LayoutRecord(AW_LAYOUT_BOX,x,y,w,h,NULL);', ui)
        self.assertIn('AW_LayoutRecord(AW_LAYOUT_BUTTON,x,y,w,h,text);', ui)

    def test_the_regular_thick_button_frame_is_the_default(self):
        # UI-OK-BUTTON-THIN-FRAME-67: the thin outline (UI-THIN-BUTTON-62) stays as a saved setting
        self.assertIn('static cvar_t button_frame={"aw_ui_button_frame","1",true};', code('aw_ui.c'))
        self.assertIn('Cvar_RegisterVariable(&button_frame);', code('aw_ui.c'))

    def test_the_helper_is_built(self):
        self.assertIn('aw_layout.c', (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
