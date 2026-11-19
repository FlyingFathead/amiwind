# SPDX-License-Identifier: GPL-3.0-only
"""Every register entry has its report page, made by the tool (TRACKER-ENTRIES-WITHOUT-PAGES-67).

tools/bug_register.py: `add` and `render` create docs/bugs/<ID>.md for every live entry that lacks one (the title line;
the facts, the timeline and the category are rendered from bugs.json) and list it in tools/release-files.json;
`check` fails every live entry without a page and every page missing from that list."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import bug_register as R  # noqa: E402


def entry(identifier, title='A title', report=None, found='v0.0.67-dev3', **extra):
    b = {'id': identifier, 'title': title, 'state': 'open', 'fixed_in': None, 'owner_accepted': None,
         'status': 'Reported.', 'report': report, 'found_in': found}
    b.update(extra)
    return b


class PageTests(unittest.TestCase):
    def test_check_names_every_live_entry_without_a_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            pages = Path(tmp)
            (pages / 'HAS-PAGE-67.md').write_text('# HAS-PAGE-67: t\n', encoding='utf-8')
            bugs = [entry('HAS-PAGE-67', report='bugs/HAS-PAGE-67.md'), entry('NO-PAGE-67'),
                    entry('LOST-PAGE-67', report='bugs/LOST-PAGE-67.md')]
            problems = R.page_problems(bugs, pages)
            self.assertEqual(len(problems), 2)
            self.assertTrue(problems[0].startswith('NO-PAGE-67: no report page'))
            self.assertTrue(problems[1].startswith('LOST-PAGE-67: report page missing'))
            (pages / 'NO-PAGE-67.md').write_text('# NO-PAGE-67: t\n', encoding='utf-8')
            self.assertIn('the file exists', R.page_problems(bugs, pages)[0])

    def test_archived_entries_are_not_listed(self):
        old = entry('OLD-FIXED-32', found='v0.0.32', state='fixed', fixed_in='v0.0.33')
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(R.page_problems([old], Path(tmp)), [])
            self.assertEqual(R.ensure_pages([old], Path(tmp)), [])
            self.assertIsNone(old['report'])

    def test_ensure_pages_makes_the_page_and_links_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            pages = Path(tmp)
            bugs = [entry('NEW-ONE-67', title='Something broke'), entry('KEEP-ONE-67')]
            (pages / 'KEEP-ONE-67.md').write_text('# KEEP-ONE-67: A title\n\nHand text.\n', encoding='utf-8')
            self.assertEqual(R.ensure_pages(bugs, pages), ['NEW-ONE-67'])
            self.assertEqual((pages / 'NEW-ONE-67.md').read_text(encoding='utf-8'), '# NEW-ONE-67: Something broke\n')
            self.assertEqual([b['report'] for b in bugs], ['bugs/NEW-ONE-67.md', 'bugs/KEEP-ONE-67.md'])
            self.assertIn('Hand text.', (pages / 'KEEP-ONE-67.md').read_text(encoding='utf-8'))
            self.assertEqual(R.page_problems(bugs, pages), [])
            self.assertEqual(R.ensure_pages(bugs, pages), [], 'a second run made pages again')

    def test_render_fills_a_made_page(self):
        b = entry('FILL-IT-67', title='Page to fill', reproduction='always', reported_by='owner',
                  found_date='2026-11-19', where='somewhere', duplicate_of=None, persists_in=['v0.0.67-dev3'],
                  severity='low', severity_reason='Cosmetic.', family=None, related=[],
                  history=[{'at': '2026-11-19', 'note': 'The cause was found.'}])
        with tempfile.TemporaryDirectory() as tmp:
            R.ensure_pages([b], Path(tmp))
            text = (Path(tmp) / 'FILL-IT-67.md').read_text(encoding='utf-8')
            out = R.rendered_page(text, b, [b], {b['id']: b}, {})
            self.assertTrue(out.startswith('# FILL-IT-67: Page to fill\n'))
            self.assertIn(R.FACTS_BEGIN, out)
            self.assertIn('## Timeline', out)
            self.assertEqual(R.rendered_page(out, b, [b], {b['id']: b}, {}), out)

    def test_list_pages_puts_each_page_in_its_sorted_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'tools').mkdir()
            start = ['README.md', 'docs/bugs/A-1.md', 'docs/bugs/C-3.md', 'docs/bugs/archive/x.json', 'tools/y.py']
            (root / 'tools' / 'release-files.json').write_text(json.dumps(start, indent=2) + '\n', encoding='utf-8')
            bugs = [entry('B-2', report='bugs/B-2.md'), entry('D-4', report='bugs/D-4.md'),
                    entry('A-1', report='bugs/A-1.md'), entry('E-5')]
            self.assertEqual(R.list_pages(bugs, root), ['docs/bugs/B-2.md', 'docs/bugs/D-4.md'])
            got = json.loads((root / 'tools' / 'release-files.json').read_text(encoding='utf-8'))
            self.assertEqual(got, ['README.md', 'docs/bugs/A-1.md', 'docs/bugs/B-2.md', 'docs/bugs/C-3.md',
                                   'docs/bugs/D-4.md', 'docs/bugs/archive/x.json', 'tools/y.py'])
            self.assertEqual(R.unshipped_pages(bugs, root), [])
            self.assertEqual(R.list_pages(bugs, root), [], 'a second run listed again')

    def test_the_commands_wire_it_in(self):
        source = (ROOT / 'tools' / 'bug_register.py').read_text(encoding='utf-8')
        self.assertIn('made = ensure_pages(bugs)', source)
        self.assertIn('for path in list_pages(bugs):', source)
        self.assertIn("missing = page_problems(bugs) + ", source)

    def test_every_live_entry_of_the_register_has_its_page(self):
        bugs = R.load()
        self.assertEqual(R.page_problems(bugs), [])
        self.assertEqual(R.unshipped_pages(bugs), [])


if __name__ == '__main__':
    unittest.main()
