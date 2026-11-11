"""RELEASE-LINKED-PAGES-CURRENT-64: the pages a version's release notes and CHANGELOG entry link are listed, a page whose
last-updated line alone changed is flagged, and such a page with a stale generated block is refused."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import release_linked_pages as rlp  # noqa: E402

BUMP = '-_Last updated with AmiWind v0.0.63 (9 November 2026)._\n+_Last updated with AmiWind v0.0.64 (10 November 2026)._\n'


def tree(files):
    d = Path(tempfile.mkdtemp())
    for name, text in files.items():
        (d / name).parent.mkdir(parents=True, exist_ok=True)
        (d / name).write_text(text, encoding='utf-8')
    (d / 'VERSION').write_text('0.0.64\n')
    return d


class LinkedPagesTests(unittest.TestCase):
    def setUp(self):
        self.root = tree({
            'docs/releases/notes/RELEASE-v0.0.64.md': 'See [a](../../A.md#x), [b](../../chim/B.md) and [web](https://x.org/c.md).\n',
            'docs/CHANGELOG.md': '## v0.0.65\n[c](C.md)\n\n## v0.0.64 - title\n[d](D.md)\n\n## v0.0.63\n[e](E.md)\n',
            'docs/A.md': '# A\n', 'docs/chim/B.md': '# B\n<!-- BEGIN GENERATED THING -->\n', 'docs/C.md': 'c\n',
            'docs/D.md': 'd\n', 'docs/E.md': 'e\n'})

    def test_links_come_from_the_notes_and_the_changelog_entry_of_the_version(self):
        self.assertEqual(rlp.linked_pages(self.root, '0.0.64'), ['docs/A.md', 'docs/D.md', 'docs/chim/B.md'])

    def test_only_a_bumped_last_updated_line_is_flagged(self):
        self.assertTrue(rlp.bump_only(BUMP, '0.0.64'))
        self.assertFalse(rlp.bump_only(BUMP + '+a new line\n', '0.0.64'))
        self.assertFalse(rlp.bump_only('', '0.0.64'))
        self.assertFalse(rlp.bump_only(BUMP, '0.0.65'))

    def test_a_bump_only_page_with_a_stale_generated_block_is_refused(self):
        saved = dict(rlp.REGISTRY)
        rlp.REGISTRY['docs/chim/B.md'] = ['x']
        try:
            ran = []

            def stale(root, page):
                ran.append(page)
                return False, ['block differs']

            pages, problems = rlp.survey(self.root, {'docs/chim/B.md': BUMP}, '0.0.64', runner=stale)
            self.assertEqual(ran, ['docs/chim/B.md'])
            self.assertEqual(len(problems), 1)
            self.assertIn('differs from a fresh render', problems[0])
            pages, problems = rlp.survey(self.root, {'docs/chim/B.md': BUMP}, '0.0.64', runner=lambda r, p: (True, ['']))
            self.assertEqual(problems, [])
            ran.clear()
            pages, problems = rlp.survey(self.root, {'docs/chim/B.md': BUMP + '+more\n'}, '0.0.64', runner=stale)
            self.assertEqual((ran, problems), ([], []))               # content changed too: not this rule
            self.assertTrue(any(r['bump_only'] for r in rlp.survey(self.root, {'docs/A.md': BUMP}, '0.0.64')[0]))
        finally:
            rlp.REGISTRY.clear()
            rlp.REGISTRY.update(saved)

    def test_the_real_repository_passes_and_its_registered_checks_exist(self):
        version = rlp.version_of()
        pages, problems = rlp.survey(ROOT, {}, version)
        self.assertEqual(problems, [])
        for page, argv in rlp.REGISTRY.items():
            self.assertTrue((ROOT / page).is_file(), page)
            if argv[0].endswith('.py'):
                self.assertTrue((ROOT / argv[0]).is_file(), argv[0])
        ok, last = rlp.run_registered(ROOT, 'docs/chim/PROGRESS_TRACKER.md')
        self.assertTrue(ok, last)


if __name__ == '__main__':
    unittest.main()
