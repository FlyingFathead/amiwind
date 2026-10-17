# SPDX-License-Identifier: GPL-3.0-only
"""The docs quick check (tools/docs_quick_check.py) picks the right checks for the changed files and catches the
whitespace rule of the gate preflight."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import docs_quick_check as q  # noqa: E402


def names(paths):
    return [name for name, _ in q.plan(paths)]


class DocsQuickCheck(unittest.TestCase):
    def test_a_public_document_gets_the_doc_checks(self):
        self.assertEqual(names(['docs/DEVELOPMENT.md']), ['whitespace', 'doc-toc', 'debug-help'])

    def test_a_bug_page_also_gets_the_register_check(self):
        self.assertIn('register', names(['docs/bugs/SOME-BUG-42.md']))
        self.assertIn('register', names(['docs/bugs/bugs.json']))
        self.assertIn('register', names(['docs/BUGS.md']))

    def test_the_command_catalogue_gets_the_help_and_page_checks(self):
        self.assertEqual(names(['config/debug-commands.txt']), ['whitespace', 'debug-help', 'console-page'])

    def test_engine_sources_get_the_debug_help_check(self):
        self.assertEqual(names(['engine/aga/src/aw_console.c']), ['whitespace', 'debug-help'])

    def test_binary_files_get_no_check(self):
        self.assertEqual(names(['docs/images/a.png']), [])
        self.assertEqual(names([]), [])

    def test_whitespace_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'good.md').write_bytes(b'# Title\n\nText.\n')
            (root / 'bad.md').write_bytes(b'# Title \n\r\nText.\t\n')
            (root / 'pic.png').write_bytes(b'\r\n ')
            problems = q.whitespace_problems(['good.md', 'bad.md', 'pic.png', 'missing.md'], root)
        self.assertEqual(problems, ['bad.md: CR bytes (convert to LF)', 'bad.md:1: trailing whitespace',
                                    'bad.md:3: trailing whitespace'])

    def test_named_files_run_and_report(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = q.main(['--files', 'tools/release-files.json'])
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn('PASS whitespace', out.getvalue())
        self.assertIn('docs quick check: PASS', out.getvalue())

    def test_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(q.main(['--nonsense']), 2)
            self.assertEqual(q.main(['install-hook', '--nonsense']), 2)

    def test_hook_runs_the_staged_check(self):
        self.assertTrue(q.HOOK.startswith('#!/bin/sh\n'))
        self.assertIn('tools/docs_quick_check.py --staged', q.HOOK)
        self.assertIn(q.HOOK_MARK, q.HOOK)


if __name__ == '__main__':
    unittest.main()
