# SPDX-License-Identifier: GPL-3.0-only
"""One bug-tracking system: register, report pages and journal must agree.

See docs/bugs/README.md. docs/bugs/bugs.json lists every bug exactly once and
docs/BUGS.md is generated from it; every report page and every current journal entry
has a register row; register links resolve, including heading anchors.
"""
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import bug_register  # noqa: E402
DOCS = ROOT / 'docs'
REGISTER = DOCS / 'BUGS.md'
JOURNAL = DOCS / 'BUG_JOURNAL.md'
FROZEN = [DOCS / 'journals' / 'BUG_JOURNAL-v0.0.29.md', DOCS / 'journals' / 'BUGS-NOTES-v0.0.29.md',
          DOCS / 'BUGS-v0.0.29-RC1.md', DOCS / 'RC2_ISSUE_CHECKPOINT.md']
FROZEN_BANNER = 'Frozen history:'
LINK = re.compile(r'\]\(([^)\s]+)\)')


def anchor(heading):
    text = re.sub(r'[^\w\- ]', '', heading.strip().lower())
    return text.replace(' ', '-')


def anchors(path):
    seen, out = {}, set()
    in_code = False
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('```'):
            in_code = not in_code
        if in_code:
            continue
        m = re.match(r'#{1,6} (.+)$', line)
        if m:
            a = anchor(m.group(1))
            n = seen.get(a, 0)
            out.add(a if n == 0 else '%s-%d' % (a, n))
            seen[a] = n + 1
    return out


def register_rows():
    """Rows as [id, title, state, fixed_in, status] from docs/bugs/bugs.json."""
    bugs = bug_register.load()
    return [[b['id'], b['title'], b['state'], b['fixed_in'] or '-', b['status'] +
             (' [Report](%s)' % b['report'] if b['report'] else '')] for b in bugs]


def journal_ids():
    ids = []
    for line in JOURNAL.read_text(encoding='utf-8').splitlines():
        m = re.match(r'## ([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+):', line)
        if m:
            ids.append(m.group(1))
    return ids


class BugTrackerTest(unittest.TestCase):
    def test_bugs_json_is_valid(self):
        self.assertEqual(bug_register.validate(bug_register.load()), [])

    def test_register_markdown_is_generated_from_json(self):
        text = REGISTER.read_text(encoding='utf-8')
        self.assertEqual(bug_register.rendered(text, bug_register.load()), text,
                         'docs/BUGS.md is stale: run tools/bug_register.py render')

    def test_report_pages_are_linked_from_json(self):
        for b in bug_register.load():
            page = DOCS / 'bugs' / (b['id'] + '.md')
            self.assertEqual(b['report'], 'bugs/%s.md' % b['id'] if page.is_file() else None, b['id'])

    def test_every_report_page_is_registered(self):
        ids = {r[0] for r in register_rows()}
        pages = sorted(p.stem for p in (DOCS / 'bugs').glob('*.md') if p.name != 'README.md')
        self.assertEqual([p for p in pages if p not in ids], [], 'report pages without a register row')

    def test_every_journal_entry_is_registered(self):
        ids = {r[0] for r in register_rows()}
        self.assertEqual([j for j in journal_ids() if j not in ids], [], 'journal IDs without a register row')

    def test_register_links_resolve(self):
        problems = []
        for r in register_rows():
            for target in LINK.findall(' '.join(r)):
                if target.startswith(('http://', 'https://')):
                    continue
                path, _, frag = target.partition('#')
                dest = (REGISTER.parent / path).resolve() if path else REGISTER
                if not dest.is_file():
                    problems.append('%s: missing %s' % (r[0], target))
                elif frag and dest.suffix == '.md' and frag not in anchors(dest):
                    problems.append('%s: missing anchor %s' % (r[0], target))
        self.assertEqual(problems, [])

    def test_report_pages_link_back_to_register_ids(self):
        for p in (DOCS / 'bugs').glob('*.md'):
            if p.name == 'README.md':
                continue
            first = p.read_text(encoding='utf-8').splitlines()[0]
            self.assertTrue(first.startswith('# %s' % p.stem), 'report title must start with its ID: %s' % p.name)

    def test_fixed_in_is_never_a_development_line(self):
        # ENTITY-TRACKER-HARVEST-32 was once marked fixed in "v0.0.32-dev" (a branch): a fix only
        # in source stays open until a numbered build ships it (docs/bugs/README.md).
        self.assertEqual([b['id'] for b in bug_register.load()
                          if any(b[k] and bug_register.DEV_LINE_RE.match(b[k]) for k in ('fixed_in', 'owner_accepted'))], [])
        base = dict(id='TEST-DEV-32', title='t', state='fixed', fixed_in='v0.0.32-dev', owner_accepted=None,
                    status='s', report=None)
        self.assertTrue(bug_register.validate([base]))
        self.assertTrue(bug_register.validate([dict(base, fixed_in='v0.0.31-dev2', owner_accepted='v0.0.32-dev')]))
        self.assertEqual(bug_register.validate([dict(base, fixed_in='v0.0.31-dev2')]), [])
        self.assertEqual(bug_register.validate([dict(base, fixed_in='v0.0.31')]), [])

    def test_tags_are_checked_and_listed(self):
        base = dict(id='TEST-TAG-31', title='t', state='open', fixed_in=None, owner_accepted=None,
                    status='s', report=None)
        self.assertEqual(bug_register.validate([dict(base, tags=['performance'])]), [])
        for bad in (['perf'], [], ['performance', 'performance'], 'performance'):
            self.assertTrue(bug_register.validate([dict(base, tags=bad)]), bad)
        listed = bug_register.table([dict(base, tags=['performance']), dict(base, id='TEST-NOTAG-31')])
        section = listed.split('### Tagged performance', 1)[1]
        self.assertIn('TEST-TAG-31', section)
        self.assertNotIn('TEST-NOTAG-31', section)

    def test_tracker_files_ship_in_release(self):
        shipped = set(json.loads((ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8')))
        files = [REGISTER, JOURNAL, *FROZEN, *sorted((DOCS / 'bugs').iterdir())]
        missing = [p.relative_to(ROOT).as_posix() for p in files
                   if p.is_file() and p.relative_to(ROOT).as_posix() not in shipped]
        self.assertEqual(missing, [], 'tracker files missing from tools/release-files.json')

    def test_frozen_trackers_are_marked(self):
        for p in FROZEN:
            self.assertTrue(p.is_file(), p)
            head = '\n'.join(p.read_text(encoding='utf-8').splitlines()[:6])
            self.assertIn(FROZEN_BANNER, head, 'frozen tracker lacks banner: %s' % p.name)


if __name__ == '__main__':
    unittest.main()
