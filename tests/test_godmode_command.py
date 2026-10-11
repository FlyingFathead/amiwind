# SPDX-License-Identifier: GPL-3.0-only
"""dbg god / dbg godmode: catalogue rows, one shared handler on Quake's god state, docs."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GodmodeCommandTests(unittest.TestCase):
    def test_both_words_route_to_one_handler(self):
        catalogue = (ROOT / 'config' / 'debug-commands.txt').read_text(encoding='utf-8')
        for words in ('god', 'godmode'):
            self.assertRegex(catalogue, r'\n[A-Z /]+\|%s\|aw_godmode\|' % words)
        self.assertIn('true/false or 1/0', re.search(r'\|god\|aw_godmode\|(.*)', catalogue).group(1))

    def test_handler_reuses_quakes_god_state(self):
        text = (ROOT / 'engine' / 'aga' / 'src' / 'aw_debug.c').read_text(encoding='utf-8')
        self.assertIn('Cmd_AddCommand("aw_godmode",godmode_command)', text)
        body = text[text.index('static void godmode_command'):text.index('void AW_DebugInit')]
        self.assertIn('FL_GODMODE', body)
        self.assertIn(r'Cbuf_AddText("god\n")', body)   # the C escape, not a newline (TEST-GODMODE-UNLISTED-36)
        self.assertNotIn('Cvar_', body)   # no second copy of the state, nothing saved

    def test_generated_page_lists_both(self):
        page = (ROOT / 'docs' / 'AMIWIND_CONSOLE_COMMANDS.md').read_text(encoding='utf-8')
        self.assertIn('`dbg god` | `dbg godmode`', page)


if __name__ == '__main__':
    unittest.main()
