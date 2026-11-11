# SPDX-License-Identifier: GPL-3.0-only
"""The tracker headline draws one block element per land and one for the build (TOOLKIT-HEADLINE-ROWS-INLINE-64)."""
from pathlib import Path
import shutil
import subprocess
import unittest


class ChimHeadRowsTests(unittest.TestCase):
    def test_one_block_row_per_land(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node.js unavailable')
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([node, str(root / 'tests/test_chim_head_rows.js')], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PASS chim headline rows', result.stdout)

    def test_no_inline_row_markup_remains(self):
        source = (Path(__file__).resolve().parents[1] / 'amiwind-toolkit' / 'chim-head.js').read_text(encoding='utf-8')
        self.assertNotIn('<span class="chimtitle chimrow"', source)
        self.assertNotIn('<span class="chimrows">', source)


if __name__ == '__main__':
    unittest.main()
