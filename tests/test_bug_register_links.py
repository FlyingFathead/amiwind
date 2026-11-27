# SPDX-License-Identifier: GPL-3.0-only
"""Entries that are probably the same fault seen another way, or possibly related, are linked both ways
(TRACK-POSSIBLY-RELATED-LINKS-69).

tools/bug_register.py: "links" {OTHER-ID: {"kind": "variant" | "related", "why": one line}} on both entries, also inside
one family (where "related" is refused), written by `link ID OTHER --kind K --why W`; validate refuses a one-way link,
an unknown ID, a link to itself, an unknown kind and a reason that is not one line; both pages show the links in a
"Possibly related" section of the category block, with the linked entry's state (a fixed or closed one may have come
back), and a page without links is unchanged."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import bug_register as R  # noqa: E402
import doc_toc  # noqa: E402

FACTS = dict(reported_by='test', found_date='2026-11-26', found_in='v0.0.69-dev', where='a test', reproduction='always',
             duplicate_of=None, persists_in=['v0.0.69-dev'], severity='low', severity_reason='A test entry.',
             family='actors-npc', related=[])
ENV = {k: v for k, v in os.environ.items() if k != R.LOCK_TOKEN_ENV}
ENV.update(PYTHONPATH=os.pathsep.join([str(ROOT / 'src'), str(ROOT / 'tools')]), PYTHONDONTWRITEBYTECODE='1')
WHY = 'Both walks snap back to where the step began.'


def entry(bug_id, title, **kw):
    b = dict(id=bug_id, title=title, state='open', fixed_in=None, owner_accepted=None, status='Open.', report=None)
    b.update(FACTS)
    b.update(kw)
    return b


def pair(**second):
    a = entry('TEST-WALK-A-69', 'Residents walk forward and snap back', report='bugs/TEST-WALK-A-69.md')
    b = entry('TEST-WALK-B-69', 'Residents keep falling back to the stuck retry', **second)
    by_id = {x['id']: x for x in (a, b)}
    R.link_entries(by_id, a['id'], b['id'], 'variant', WHY)
    return a, b, by_id


class LinkTest(unittest.TestCase):
    def test_links_are_checked_both_ways(self):
        families = {f['key'] for f in R.load_families()}
        a, b, _ = pair()
        a['report'] = None            # no page file here: validate looks for a named one
        self.assertEqual(a['links'], {'TEST-WALK-B-69': {'kind': 'variant', 'why': WHY}})
        self.assertEqual(b['links'], {'TEST-WALK-A-69': {'kind': 'variant', 'why': WHY}})
        self.assertEqual(R.validate([a, b], families), [], 'a link inside one family is allowed')
        one_way = {k: v for k, v in b.items() if k != 'links'}
        self.assertTrue(any('both ways' in e for e in R.validate([a, one_way], families)))
        other_why = dict(b, links={'TEST-WALK-A-69': {'kind': 'variant', 'why': 'Another reason.'}})
        self.assertTrue(any('both ways' in e for e in R.validate([a, other_why], families)))
        for bad in ({'TEST-NOT-THERE-69': {'kind': 'variant', 'why': 'x'}},
                    {'TEST-WALK-A-69': {'kind': 'variant', 'why': 'x'}},
                    {'TEST-WALK-B-69': {'kind': 'duplicate', 'why': 'x'}},
                    {'TEST-WALK-B-69': {'kind': 'variant', 'why': 'a | b'}},
                    {'TEST-WALK-B-69': {'kind': 'variant'}}, {}):
            self.assertTrue(R.validate([dict(a, links=bad), b], families), 'passed: %r' % (bad,))
        by_id = {a['id']: a, b['id']: b}
        for args in (('TEST-WALK-A-69', 'TEST-WALK-A-69', 'variant', 'x'),
                     ('TEST-WALK-A-69', 'TEST-NOT-THERE-69', 'variant', 'x'),
                     ('TEST-WALK-A-69', 'TEST-WALK-B-69', 'duplicate', 'x'),
                     ('TEST-WALK-A-69', 'TEST-WALK-B-69', 'related', 'a table cell | breaks'),
                     ('TEST-WALK-A-69', 'TEST-WALK-B-69', 'related', '   ')):
            with self.assertRaises(ValueError):
                R.link_entries(by_id, *args)
        R.link_entries(by_id, 'TEST-WALK-B-69', 'TEST-WALK-A-69', 'related', 'They share the walk table.')
        self.assertEqual([x['links'][o]['kind'] for x, o in ((a, b['id']), (b, a['id']))], ['related', 'related'],
                         'linking again changes the kind on both')

    def test_both_pages_show_the_links_with_the_state(self):
        families = {f['key']: f for f in R.load_families()}
        a, b, by_id = pair(state='fixed', fixed_in='v0.0.61', persists_in='fixed in v0.0.61')
        section = R.category_section(a, [a, b], by_id, families)
        self.assertIn('## Possibly related', section)
        self.assertLess(section.index('## Possibly related'), section.index(R.CAT_HEADING))
        self.assertIn('- Probable variant of the same fault: TEST-WALK-B-69 (no report page) (fixed in v0.0.61): '
                      'Residents keep falling back to the stuck retry. Why: ' + WHY, section)
        self.assertIn('[TEST-WALK-A-69](TEST-WALK-A-69.md) (open)', R.category_section(b, [a, b], by_id, families))
        plain = entry('TEST-PLAIN-69', 'A page with no link')
        self.assertNotIn('Possibly related', R.category_section(plain, [a, b, plain], by_id, families),
                         'a page without links changed')
        page = R.rendered_page('# TEST-WALK-A-69: Residents walk forward and snap back\n', a, [a, b], by_id, families)
        page = doc_toc.render(page)
        again = R.rendered_page(page, a, [a, b], by_id, families)
        self.assertEqual(again, page if page.endswith('\n') else page + '\n')
        self.assertEqual(doc_toc.render(again), again, 'the page and its contents list move each other')
        self.assertEqual(again.count(R.CAT_HEADING), 1)
        self.assertTrue(again.rstrip().endswith(R.CAT_END), 'the category block must end the page')

    def test_the_link_command_writes_both_entries_and_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'checkout'
            (root / 'tools').mkdir(parents=True)
            (root / 'docs' / 'bugs').mkdir(parents=True)
            shutil.copyfile(str(ROOT / 'tools' / 'bug_register.py'), str(root / 'tools' / 'bug_register.py'))
            for name in ('VERSION', 'CHIM_VERSION'):
                shutil.copyfile(str(ROOT / name), str(root / name))
            shutil.copyfile(str(ROOT / 'docs' / 'bugs' / 'families.json'), str(root / 'docs' / 'bugs' / 'families.json'))
            (root / 'docs' / 'BUGS.md').write_text('# Bugs\n\n%s\n%s\n' % (R.BEGIN, R.END), encoding='utf-8')
            (root / 'docs' / 'bugs' / 'README.md').write_text('# Bug reports\n\n%s\n%s\n' % (R.FAM_BEGIN, R.FAM_END),
                                                              encoding='utf-8')
            (root / 'docs' / 'bugs' / 'bugs.json').write_text('[]\n', encoding='utf-8')
            (root / 'tools' / 'release-files.json').write_text('[]\n', encoding='utf-8')

            def run(*args):
                return subprocess.run([sys.executable, '-B', str(root / 'tools' / 'bug_register.py')] + list(args),
                                      cwd=str(root), env=ENV, capture_output=True, text=True, encoding='utf-8',
                                      errors='replace', timeout=300)

            def reg():
                return {b['id']: b for b in json.loads((root / 'docs' / 'bugs' / 'bugs.json').read_text(encoding='utf-8'))}
            for bug_id, title in (('TEST-LINK-A-69', 'Residents walk forward and then snap back'),
                                  ('TEST-LINK-B-69', 'Residents keep falling back to the stuck movement retry')):
                r = run('add', bug_id, '--title', title, '--found', 'v0.0.69-dev5', '--reported-by', 'test',
                        '--where', 'a test checkout', '--severity', 'low', '--severity-reason', 'a test entry',
                        '--family', 'tracker-tooling', '--build-name', 'source', '--source-commit', 'abc1234')
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = run('link', 'TEST-LINK-A-69', 'TEST-LINK-B-69', '--kind', 'variant', '--why',
                    'Both are the walk of the same table seen from two places.')
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            got = reg()
            self.assertEqual(got['TEST-LINK-A-69']['links'], {'TEST-LINK-B-69': {
                'kind': 'variant', 'why': 'Both are the walk of the same table seen from two places.'}})
            self.assertEqual(got['TEST-LINK-B-69']['links']['TEST-LINK-A-69']['kind'], 'variant')
            for bug_id in got:
                self.assertIn('## Possibly related', (root / 'docs' / 'bugs' / ('%s.md' % bug_id)).read_text(
                    encoding='utf-8'))
            self.assertEqual(run('check').returncode, 0)
            self.assertNotEqual(run('link', 'TEST-LINK-A-69', 'TEST-NOT-THERE-69', '--kind', 'related', '--why',
                                    'x').returncode, 0)
            self.assertEqual(run('check').returncode, 0)


if __name__ == '__main__':
    unittest.main()
