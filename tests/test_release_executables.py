# SPDX-License-Identifier: GPL-3.0-only
"""Every file committed executable is one the release tool ships as executable, and the other way round.

tools/release.py writes the source ZIP with mode 0755 for the files in EXECUTABLES and 0644 for every other
file. tools/engine_smoke.py was committed executable without being listed and broke the source ZIP only at kit
time (BUILD-EXECUTABLES-LIST-UNGATED-36). The master builder refuses such a commit before a gate starts
(tools/aw.py executable_mode_refusals, on the checkout); this test checks the same wherever the tree has git (CI).
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools')]

import release  # noqa: E402


class ExecutablesListTests(unittest.TestCase):
    def test_the_tree_matches_the_list(self):
        # Needs the git index (CI, a checkout); the gate's staged source has none, and the master builder runs the
        # same check on the checkout before the gate starts (tools/aw.py executable_mode_refusals).
        found = release.executable_mismatches(ROOT)
        if found is not None:
            self.assertEqual(found, ([], []))

    def test_the_list_is_read_from_the_tree_itself(self):
        self.assertEqual(release.listed_executables(ROOT), release.EXECUTABLES)

    def test_an_unlisted_executable_and_a_listed_plain_file_are_found(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'tools').mkdir()
            (root / 'tools/release.py').write_text('EXECUTABLES = {"build.sh", "tools/run.py"}\n', encoding='utf-8')
            found = {'build.sh', 'tools/engine_smoke.py'}
            self.assertEqual(release.executable_mismatches(root, found), (['tools/engine_smoke.py'], ['tools/run.py']))
            self.assertEqual(release.executable_mismatches(root, {'build.sh', 'tools/run.py'}), ([], []))
            import aw
            with patch.object(release, 'executable_mismatches', lambda repo: (['tools/engine_smoke.py'], ['tools/run.py'])):
                refusals = aw.executable_mode_refusals(root)
            self.assertEqual(len(refusals), 2)
            self.assertIn('tools/engine_smoke.py', refusals[0])
            self.assertIn('tools/run.py', refusals[1])

    def test_the_index_modes_are_read_from_git(self):
        if shutil.which('git') is None:
            return  # no git in the gate image; CI runs this
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ('a.sh', 'b.txt'):
                (root / name).write_text('x\n', encoding='utf-8')
            for args in (('init', '-q'), ('add', '.'), ('update-index', '--chmod=+x', 'a.sh')):
                subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True)
            self.assertEqual(release.committed_executables(root), {'a.sh'})


if __name__ == '__main__':
    unittest.main()
