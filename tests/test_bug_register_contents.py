# SPDX-License-Identifier: GPL-3.0-only
"""The register's render writes each page's contents list itself (REGISTER-ADD-NO-RELEASE-ROW-48).

A new bug in a family changes the family's pages; their contents lists were left stale until tools/doc_toc.py write
ran, and the gate failed on it twice in v0.0.55 (gates 4462 and 4477). render now leaves every public page as doc_toc
write would, so `bug_register.py add` followed by the gate passes without a doc_toc step."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import bug_register as R  # noqa: E402
import doc_toc  # noqa: E402

PAGE = ROOT / 'docs/bugs/BUILD-NOT-FROM-SCRATCH-32.md'


class ContentsListTests(unittest.TestCase):
    def test_a_stale_list_is_refreshed(self):
        current = PAGE.read_text(encoding='utf-8')
        self.assertIn(doc_toc.START, current)
        stale = doc_toc.strip_block(current)
        out = R.with_contents_lists({PAGE: stale})[PAGE]
        self.assertEqual(out, doc_toc.render(stale))
        self.assertIn(doc_toc.START, out)

    def test_a_current_page_is_left_as_it_is(self):
        current = PAGE.read_text(encoding='utf-8')
        self.assertEqual(R.with_contents_lists({PAGE: current})[PAGE], current)

    def test_a_file_outside_the_public_list_is_not_touched(self):
        path = ROOT / 'docs/bugs/not-a-public-page.md'
        text = '# Title\n\nbody\n'
        self.assertEqual(R.with_contents_lists({path: text})[path], text)


if __name__ == '__main__':
    unittest.main()
