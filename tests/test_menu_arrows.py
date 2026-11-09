# SPDX-License-Identifier: GPL-3.0-only
"""INVENTORY-ARROWS-SCROLL-62:the input guard strips the Amiga qualifier from the cursor keys (and M, N) on the game's
screen even while an Amiga key looks held, so a lost Amiga key-up (a host shortcut on FS-UAE) never turns every menu's
arrow keys into Intuition's keyboard mouse. The rule is evaluated here from the engine's own expression."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYS = (ROOT / 'engine/aga/src/sys_amiga.c').read_text(encoding='utf-8')


def strips(raw):
    body = SYS[SYS.index('int AW_InputGuardKeyStrips(int raw){'):]
    expr = re.search(r'return (.*?);', body).group(1)
    expr = expr.replace('||', ' or ').replace('&&', ' and ')
    return bool(eval(expr, {}, {'raw': raw}))   # noqa: S307 (the engine's own constant expression)


class MenuArrowsGuardTests(unittest.TestCase):
    def test_cursor_keys_and_screen_keys_always_lose_the_amiga_qualifier(self):
        for raw in (0x4C, 0x4D, 0x4E, 0x4F, 0x36, 0x37):
            self.assertTrue(strips(raw), hex(raw))

    def test_other_keys_keep_it_unless_no_amiga_key_is_held(self):
        for raw in (0x10, 0x20, 0x44, 0x45, 0x50, 0x66, 0x67):
            self.assertFalse(strips(raw), hex(raw))

    def test_the_guard_uses_the_rule_on_the_active_game_screen(self):
        events = SYS[SYS.index('struct InputEvent *AW_InputGuardEvents('):SYS.index('struct InputEvent *AW_InputGuardMouse(')]
        self.assertIn('AW_InputGuardKeyStrips(e->ie_Code&0x7f) || !guard_amiga_held', events)
        self.assertIn('(video_window->Flags&WFLG_WINDOWACTIVE)', events)


class ListNavigationRuleTests(unittest.TestCase):
    @unittest.skipIf(__import__('os').name == 'nt', 'native fixtures run on Linux, including the Docker gate')
    def test_the_shared_rule(self):
        import sys
        sys.path.insert(0, str(ROOT / 'tests'))
        from test_aga_native_source import NativeSourceTests
        NativeSourceTests.compile_run(self, 'aga_listnav_test.c', [],
                                      cflags=['-Wall', '-Wextra', '-Werror', '-Wno-unused-function', '-fsanitize=address,undefined',
                                              '-fno-sanitize-recover=all'])

    def test_the_inventory_uses_it(self):
        ui = (ROOT / 'engine/aga/src/aw_worldui.c').read_text(encoding='utf-8')
        self.assertIn('#include "aw_listnav.h"', ui)
        key = ui[ui.index('static void inventory_key(int key){'):]
        self.assertIn('AW_ListNavKey(key,&inventory->selected,&inventory->top,inventory->count,INV_VISIBLE)', key)


if __name__ == '__main__':
    unittest.main()
