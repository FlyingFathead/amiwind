# SPDX-License-Identifier: GPL-3.0-only
"""The "?" in the Toolkit header is a button with a help panel on every page (TOOLKIT-HELP-BUTTON-INERT-64)."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ToolkitHelpTests(unittest.TestCase):
    def test_help_panel_and_every_page_has_a_target(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node.js unavailable')
        r = subprocess.run([node, str(ROOT / 'tests/test_toolkit_help.js')], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('PASS toolkit help', r.stdout)

    def test_no_inert_question_mark_left(self):
        for name in ('header.js', 'index.html'):
            text = (ROOT / 'amiwind-toolkit' / name).read_text(encoding='utf-8')
            self.assertNotIn('<span class="awnote"', text)
            self.assertNotIn('<span class="note"', text)


if __name__ == '__main__':
    unittest.main()
