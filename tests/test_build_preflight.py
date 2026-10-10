"""Build preflight (BUILD-CACHE-OWNER-FAILS-STAGE-34): seconds-long checks before any stage, each with its fix."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_preflight  # noqa: E402


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name) / 'workspace'
        (self.workspace / 'cache' / 'chim-units' / 'frame').mkdir(parents=True)
        (self.workspace / 'cache' / 'chim-units' / 'frame' / 'x.pickle').write_bytes(b'x')
        self.data = Path(self.temp.name) / 'Data Files'
        self.data.mkdir()
        (self.data / 'Morrowind.esm').write_bytes(b'TES3')

    @unittest.skipUnless(hasattr(os, 'geteuid') and os.geteuid() != 0, 'POSIX owners, not root')
    def test_clean_workspace_passes(self):
        self.assertEqual(build_preflight.run(self.workspace, self.data, minimum_gib=0), [])

    @unittest.skipUnless(hasattr(os, 'geteuid'), 'POSIX owners')
    def test_entries_of_another_user_fail_with_the_chown_fix(self):
        problems = build_preflight.cache_problems(self.workspace / 'cache', uid=os.geteuid() + 4242)
        self.assertEqual(len(problems), 1)
        self.assertIn('owned by another user', problems[0])
        self.assertIn(f'chown -R {os.geteuid() + 4242}:', problems[0])

    def test_free_space_minimum(self):
        problems = build_preflight.free_space_problems(self.workspace, minimum_gib=10 ** 9)
        self.assertEqual(len(problems), 1)
        self.assertIn('GiB needed', problems[0])
        self.assertEqual(build_preflight.free_space_problems(self.workspace / 'not-yet', minimum_gib=0), [])

    def test_game_data_checked(self):
        self.assertEqual(build_preflight.data_problems(self.data), [])
        self.assertIn('does not exist', build_preflight.data_problems(self.data / 'missing')[0])
        (self.data / 'Morrowind.esm').unlink()
        self.assertIn('no Morrowind.esm', build_preflight.data_problems(self.data)[0])

    def test_image_builds_run_it_before_any_stage(self):
        text = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
        check = text.index('build_preflight.run(args.workspace')
        self.assertLess(text.index('require_previous_release(ROOT, VERSION)'), check)
        self.assertLess(check, text.index("        if getattr(args, 'accept_known_stair_findings', None):\n"))


if __name__ == '__main__':
    unittest.main()
