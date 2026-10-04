# SPDX-License-Identifier: GPL-3.0-only
"""Run the canonical inspector JavaScript suite; DOM/WebGL stubs are not GPU proof."""
from pathlib import Path
import shutil
import subprocess
import unittest


class PolycountPreviewTests(unittest.TestCase):
    def test_preview_planning_session_and_gizmo(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node.js unavailable; JavaScript preview checks require an existing interpreter')
        root = Path(__file__).resolve().parents[1]
        # Share the standalone entry point instead of retaining an older copy
        # of its DOM fixtures and assertions inside a Python string.
        result = subprocess.run(
            [node, str(root / 'tests/test_polycount_markup.js'),
             str(root / 'tools/polycount_inspector.html')],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for milestone in ('PASS terrain preview', 'PASS019 whole-placement selection', 'PASS session copy'):
            self.assertIn(milestone, result.stdout)


if __name__ == '__main__':
    unittest.main()
