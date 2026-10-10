# SPDX-License-Identifier: GPL-3.0-only
"""Run names (tools/run_name.py): YYYY_MM_DD_vX.Y.Z[-suffix]_<purpose>[-tryN]_<gitshort>."""
from datetime import datetime
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import run_name  # noqa: E402


class RunNameTests(unittest.TestCase):
    def test_default_name_and_tries(self):
        day = datetime(2026, 10, 10, 3, 30)
        self.assertEqual(run_name.default_name('0.0.35-dev1', 'full', '901f8e9', today=day),
                         '2026_10_10_v0.0.35-dev1_full_901f8e9')
        taken = {'2026_10_10_v0.0.35_miniwind-balmora_abc1234', '2026_10_10_v0.0.35_miniwind-balmora-try2_abc1234'}
        self.assertEqual(run_name.default_name('0.0.35', 'miniwind-balmora', 'abc1234', exists=taken.__contains__,
                                               today=day), '2026_10_10_v0.0.35_miniwind-balmora-try3_abc1234')
        self.assertTrue(run_name.NAME.fullmatch(run_name.default_name('0.0.35-dev12', 'miniwind-sadrith-mora-debug-quick',
                                                                      'nogit', today=day)))
        self.assertEqual(run_name.split_version('0.0.35-dev1'), ('0.0.35', 'dev1'))
        self.assertEqual(run_name.split_version('0.0.35'), ('0.0.35', None))
        self.assertEqual(run_name.purpose('aga'), 'full')
        self.assertEqual(run_name.purpose('aga', dry_run=True), 'dry-run')
        self.assertEqual(run_name.purpose('aga', miniwind_label='-balmora-quick'), 'miniwind-balmora-quick')

    def test_explicit_names_need_the_version_unless_overridden(self):
        self.assertIsNone(run_name.check_explicit('2026_10_10_v0.0.35-dev1_full-try2_901f8e9', '0.0.35-dev1'))
        with self.assertRaisesRegex(ValueError, 'does not contain the source version 0.0.35-dev1'):
            run_name.check_explicit('final34b-3707069', '0.0.35-dev1')
        self.assertIn('WARNING', run_name.check_explicit('fixture', '0.0.35-dev1', allow_any=True))

    def test_commit_from_git_option_environment_or_nogit(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {}, clear=False):
            os.environ.pop(run_name.ENV, None)
            self.assertEqual(run_name.source_commit(temp), ('nogit', 'unknown'))
            self.assertEqual(run_name.source_commit(temp, 'ABCDEF0123'), ('abcdef0', '--source-commit'))
            os.environ[run_name.ENV] = '901f8e9'
            self.assertEqual(run_name.source_commit(temp), ('901f8e9', run_name.ENV))
            with self.assertRaisesRegex(ValueError, 'commit hash'):
                run_name.source_commit(temp, 'not-a-hash')
        if (ROOT / '.git').exists():
            commit, origin = run_name.source_commit(ROOT)
            self.assertIn(origin, ('git', run_name.ENV, 'unknown'))

    def test_record(self):
        row = run_name.record('2026_10_10_v0.0.35-dev1_full_901f8e9', '0.0.35-dev1', '901f8e9', 'git', 'full', False)
        self.assertEqual((row['base_version'], row['suffix'], row['commit'], row['purpose']),
                         ('0.0.35', 'dev1', '901f8e9', 'full'))


if __name__ == '__main__':
    unittest.main()
