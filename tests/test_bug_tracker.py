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
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import bug_register  # noqa: E402
DOCS = ROOT / 'docs'
REGISTER = DOCS / 'BUGS.md'
JOURNAL = DOCS / 'BUG_JOURNAL.md'
FROZEN = [DOCS / 'journals' / 'BUG_JOURNAL-v0.0.29.md', DOCS / 'journals' / 'BUG_JOURNAL-v0.0.31.md',
          DOCS / 'journals' / 'BUG_JOURNAL-v0.0.34.md', DOCS / 'journals' / 'BUGS-NOTES-v0.0.29.md',
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


FACTS = dict(reported_by='owner', found_date='2026-10-08', found_in='v0.0.32-dev3', where='Vivec Arena preview',
             reproduction='always', duplicate_of=None, persists_in=['v0.0.32-dev3'], severity='medium',
             severity_reason='Visible at the frame edge only.', family='vivec-frame-edge', related=[])
# The build a bug was found in (required for bugs found in a numbered build and for CHIM bugs).
LEGACY_BUILD = dict(name='v0.0.32-dev3', source_commit='91a7eebeaff7ed09d1f248817e9652a2feec9916',
                    engine_commit='91a7eebeaff7ed09d1f248817e9652a2feec9916', world_commit=None, chim_version=None,
                    chim_format=None)
CHIM_BUILD = dict(name='CHIM Preview 1', source_commit='0f467e4b907e28930e323b31a9db2fcfc17c1c47',
                  engine_commit='0d8bf4feacbf6563485e712ffd1ca4201391c25d', world_commit='unknown',
                  chim_version='0.1.0', chim_format='0.4', unknown_reason='the CHIM world receipt records no commit')


def bug(**kw):
    """A complete register entry for unit checks (facts included)."""
    b = dict(id='TEST-BUG-32', title='t', state='open', fixed_in=None, owner_accepted=None, status='s', report=None)
    b.update(FACTS)
    b['build'] = dict(LEGACY_BUILD)
    b.update(kw)
    return b


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
        pages = sorted(p.stem for p in (DOCS / 'bugs').glob('*.md') if p.name not in bug_register.GENERATED_PAGES)
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
            if p.name in bug_register.GENERATED_PAGES:
                continue
            first = p.read_text(encoding='utf-8').splitlines()[0]
            self.assertTrue(first.startswith('# %s' % p.stem), 'report title must start with its ID: %s' % p.name)

    def test_fixed_in_is_never_a_development_line(self):
        # ENTITY-TRACKER-HARVEST-32 was once marked fixed in "v0.0.32-dev" (a branch): a fix only
        # in source stays open until a numbered build ships it (docs/bugs/README.md).
        self.assertEqual([b['id'] for b in bug_register.load()
                          if any(b[k] and bug_register.DEV_LINE_RE.match(b[k]) for k in ('fixed_in', 'owner_accepted'))], [])
        base = bug(id='TEST-DEV-32', state='fixed', fixed_in='v0.0.32-dev', persists_in='fixed in v0.0.32-dev')
        self.assertTrue(bug_register.validate([base]))
        self.assertTrue(bug_register.validate([dict(base, fixed_in='v0.0.31-dev2', owner_accepted='v0.0.32-dev')]))
        self.assertEqual(bug_register.validate([dict(base, fixed_in='v0.0.31-dev2',
                                                     persists_in='fixed in v0.0.31-dev2')]), [])
        self.assertEqual(bug_register.validate([dict(base, fixed_in='v0.0.31', persists_in='fixed in v0.0.31')]), [])

    def test_tags_are_checked_and_listed(self):
        base = bug(id='TEST-TAG-31')
        self.assertEqual(bug_register.validate([dict(base, tags=['performance'])]), [])
        for bad in (['perf'], [], ['performance', 'performance'], 'performance'):
            self.assertTrue(bug_register.validate([dict(base, tags=bad)]), bad)
        listed = bug_register.table([dict(base, tags=['performance']), dict(base, id='TEST-NOTAG-31')])
        section = listed.split('### Tagged performance', 1)[1]
        self.assertIn('TEST-TAG-31', section)
        self.assertNotIn('TEST-NOTAG-31', section)

    # Owner requirement, 9 October 2026: who, what, when, where, how, which version, reproduction,
    # duplicate, persistence, severity, and links between bugs of the same kind.
    def test_bugs_from_v0030_must_carry_every_fact(self):
        bare = {k: v for k, v in bug().items() if k not in bug_register.FACTS}
        for missing in bug_register.FACTS:
            errors = bug_register.validate([{k: v for k, v in bug().items() if k != missing}])
            self.assertTrue(any(missing in e for e in errors), missing)
        self.assertTrue(bug_register.validate([dict(bare, id='NEW-BUG-30')]), 'a v0.0.30 bug without facts passed')
        self.assertTrue(bug_register.validate([dict(bare, id='NEW-BUG-33')]), 'a v0.0.33 bug without facts passed')
        for old in ('OLD-BUG-29', 'AW-20260928-01', 'AW25-01', 'ENTITY-EXHAUSTION-007', 'CFG-01'):
            self.assertEqual(bug_register.validate([dict(bare, id=old)]), [], old)
        self.assertEqual(bug_register.validate([bug()]), [])
        missing = [b['id'] for b in bug_register.load()
                   if bug_register.needs_facts(b) and any(k not in b for k in bug_register.FACTS)]
        self.assertEqual(missing, [], 'bugs found from v0.0.30 on without every fact')

    def test_fact_values_are_checked(self):
        bad = dict(reported_by=['someone', 'gate:', 'Owner', ''], found_date=['8 October 2026', '2026-13-01', ''],
                   found_in=['0.0.32', 'dev3', ''], where=['', 'a|b', 'x' * 101, 'two\nlines'],
                   reproduction=['often', None], persists_in=[[], ['v0.0.32 dev3'], 'fixed in v0.0.31', 'v0.0.31'],
                   severity=['blocker', 'unknown', None], severity_reason=['', 'a|b'], family=['nope', None],
                   related=['TEST-BUG-32', ['ZZZ-NOPE-32'], ['TEST-BUG-32']])
        for key, values in bad.items():
            for v in values:
                self.assertTrue(bug_register.validate([bug(**{key: v})]), '%s=%r passed' % (key, v))
        for good in (dict(reported_by='gate:stair-walk'), dict(found_date='unknown', found_in='unknown'),
                     dict(found_in='v0.0.32-dev'), dict(persists_in='unknown'),
                     dict(persists_in=['v0.0.31', 'v0.0.32-dev3']), dict(reproduction='once'),
                     dict(state='fixed', fixed_in='v0.0.31', persists_in='fixed in v0.0.31')):
            self.assertEqual(bug_register.validate([bug(**good)]), [], good)
        self.assertTrue(bug_register.validate([bug(state='fixed', fixed_in='v0.0.31', persists_in=['v0.0.31'])]))

    def test_duplicate_of_names_a_registered_bug_and_closes_it(self):
        orig = bug(id='TEST-ORIG-32')
        self.assertEqual(bug_register.validate([orig, bug(state='closed', duplicate_of='TEST-ORIG-32')]), [])
        self.assertTrue(bug_register.validate([orig, bug(duplicate_of='TEST-ORIG-32')]), 'open duplicate passed')
        self.assertTrue(bug_register.validate([bug(state='closed', duplicate_of='TEST-NONE-32')]))
        self.assertTrue(bug_register.validate([bug(state='closed', duplicate_of='TEST-BUG-32')]))
        bugs = bug_register.load()
        ids = {b['id'] for b in bugs}
        self.assertEqual([b['id'] for b in bugs if b.get('duplicate_of') not in ids | {None}], [])

    def test_related_links_are_both_ways_and_outside_the_family(self):
        a = bug(id='TEST-A-32', related=['TEST-B-32'])
        b = bug(id='TEST-B-32', family='audio', related=['TEST-A-32'])
        self.assertEqual(bug_register.validate([a, b]), [])
        self.assertTrue(bug_register.validate([a, dict(b, related=[])]), 'one-way link passed')
        self.assertTrue(bug_register.validate([a, dict(b, family=a['family'])]), 'same-family link passed')
        fixed = [dict(a), dict(b, related=[])]
        bug_register.symmetric(fixed)
        self.assertEqual(fixed[1]['related'], ['TEST-A-32'])
        same = [dict(a), dict(b, family=a['family'])]
        bug_register.symmetric(same)
        self.assertEqual([x['related'] for x in same], [[], []])

    def test_families_are_defined_and_used(self):
        families = bug_register.load_families()
        self.assertEqual(bug_register.validate_families(families), [])
        keys = {f['key'] for f in families}
        self.assertEqual([b['id'] for b in bug_register.load()
                          if bug_register.needs_facts(b) and b.get('family') not in keys], [])
        for name in ('vivec-frame-edge', 'stairs-collision', 'distance-drawing', 'seyda-recorded', 'console-input',
                     'build-speed', 'heap-memory', 'lighting-night', 'audio', 'tracker-tooling'):
            self.assertIn(name, keys)
        self.assertTrue(bug_register.validate_families(families + [families[0]]), 'duplicate family key passed')

    def test_generated_parts_are_in_sync(self):
        bugs, families = bug_register.load(), bug_register.load_families()
        stale = [p.relative_to(ROOT).as_posix() for p, text in bug_register.outputs(bugs, families).items()
                 if p.read_text(encoding='utf-8') != text]
        self.assertEqual(stale, [], 'stale generated parts: run tools/bug_register.py render')

    def test_pages_carry_fact_table_and_category_section(self):
        by_id = {b['id']: b for b in bug_register.load()}
        for b in by_id.values():
            if not (b['report'] and bug_register.needs_facts(b)):
                continue
            text = (DOCS / b['report']).read_text(encoding='utf-8')
            lines = text.split('\n')
            self.assertEqual(lines[2], bug_register.FACTS_BEGIN, '%s: fact table must sit under the title' % b['id'])
            rows = bug_register.parse_fact_table(text)
            build = b.get('build') or {}
            expected = ['Fact', 'Reported by', 'First noticed', 'Where', 'Reproduction', 'Duplicate of', 'Persists in',
                        'Severity', 'Family'] + (['CHIM'] if 'chim' in b else [])
            if build:
                expected += ['Playtest version', 'From commit', 'CHIM engine version']
                expected += ['Unknown because'] if build.get('unknown_reason') else []
                expected += ['Build note'] if build.get('note') else []
            self.assertEqual(list(rows), expected, b['id'])
            self.assertTrue(rows['Severity'].startswith(b['severity'] + ':'), b['id'])
            self.assertEqual(text.count(bug_register.CAT_HEADING), 1, b['id'])
            self.assertTrue(text.rstrip().endswith(bug_register.CAT_END),
                            '%s: the category section must end the page' % b['id'])
            section = text[text.index(bug_register.CAT_HEADING):]
            for other in by_id.values():
                if other['id'] != b['id'] and (other.get('family') == b['family'] or other['id'] in b['related']):
                    self.assertIn(other['id'], section, '%s does not list %s' % (b['id'], other['id']))

    def test_page_render_replaces_a_hand_table_and_is_stable(self):
        families = {f['key']: f for f in bug_register.load_families()}
        a = bug(id='TEST-A-32', report='bugs/TEST-A-32.md', title='First')
        b = bug(id='TEST-B-32', report='bugs/TEST-B-32.md', title='Second', reproduction='sometimes')
        by_id = {'TEST-A-32': a, 'TEST-B-32': b}
        hand = ('# TEST-A-32: First\n\n| | |\n| --- | --- |\n| Reported by | owner |\n| Severity | high |\n\n'
                '## Status: 8 October 2026\n\nOpen.\n\n## Prevention\n\nNone.\n')
        once = bug_register.rendered_page(hand, a, [a, b], by_id, families)
        self.assertEqual(bug_register.rendered_page(once, a, [a, b], by_id, families), once)
        self.assertEqual(once.count('| Reported by |'), 1)
        self.assertNotIn('| Severity | high |', once)
        self.assertIn('| First noticed | 8 October 2026, in v0.0.32-dev3 |', once)
        self.assertIn('- [TEST-B-32](TEST-B-32.md): Second', once)
        self.assertLess(once.index('## Prevention'), once.index(bug_register.CAT_HEADING))
        self.assertEqual(bug_register.parse_fact_table(hand)['Severity'], 'high')

    def test_hand_written_fact_table_is_imported(self):
        # The v0.0.32 release wrote fact tables by hand (free text); backfill --pages reads them.
        rows = bug_register.parse_fact_table(
            '# TEST-A-32: t\n\n| | |\n| --- | --- |\n| Reported by | stair walkability gate (branch) |\n'
            '| First noticed | 8 October 2026, v0.0.32-dev2 maps |\n| Where | Addamasartus cave |\n'
            '| Reproduction | always (gate) |\n| Duplicate of | none (family: TEST-B-32) |\n'
            '| Persists in | v0.0.32 (shipped as is) |\n| Severity | low (a 1-unit step) |\n\n## Status\n')
        got = bug_register.facts_from_table(rows, bug(id='TEST-A-32', reported_by='gate:stair-walk'),
                                            {'TEST-A-32', 'TEST-B-32'})
        self.assertEqual(got, dict(reported_by='gate:stair-walk', found_date='2026-10-08', found_in='v0.0.32-dev2',
                                   where='Addamasartus cave', reproduction='always', duplicate_of=None,
                                   persists_in=['v0.0.32-dev2', 'v0.0.32'], severity='low',
                                   severity_reason='A 1-unit step.', related=['TEST-B-32']))
        owner = bug_register.facts_from_table({'Reported by': 'Harry (owner playtest)',
                                               'Persists in': 'unknown (not reproduced)'}, bug(), set())
        self.assertEqual((owner['reported_by'], owner['persists_in']), ('owner', 'unknown'))

    def test_generated_links_resolve(self):
        problems = []
        readme = DOCS / 'bugs' / 'README.md'
        text = readme.read_text(encoding='utf-8')
        block = text[text.index(bug_register.FAM_BEGIN):text.index(bug_register.FAM_END)]
        pages = [(readme, block)]
        for b in bug_register.load():
            if b['report']:
                page = DOCS / b['report']
                t = page.read_text(encoding='utf-8')
                for begin, end in ((bug_register.FACTS_BEGIN, bug_register.FACTS_END),
                                   (bug_register.CAT_BEGIN, bug_register.CAT_END)):
                    if begin in t:
                        pages.append((page, t[t.index(begin):t.index(end)]))
        for page, part in pages:
            for target in LINK.findall(part):
                path, _, frag = target.partition('#')
                dest = (page.parent / path).resolve() if path else page
                if not dest.is_file():
                    problems.append('%s: missing %s' % (page.name, target))
                elif frag and frag not in anchors(dest):
                    problems.append('%s: missing anchor %s' % (page.name, target))
        self.assertEqual(problems, [])

    def test_register_shows_severity_found_in_and_families(self):
        text = REGISTER.read_text(encoding='utf-8')
        self.assertIn('| ID | Issue | Severity | Found in | State |', text)
        self.assertIn('### Bugs by family', text)
        readme = (DOCS / 'bugs' / 'README.md').read_text(encoding='utf-8')
        bugs = bug_register.load()
        for f in bug_register.load_families():
            if any(b.get('family') == f['key'] for b in bugs):
                self.assertIn('`%s`' % f['key'], readme)
        self.assertNotIn('Current families:', readme, 'the hand-written families table is back')

    def test_tracker_files_fit_the_release_size_limits(self):
        # The register outgrew the 256 KiB text limit when the facts were added (gate preflight,
        # 9 October 2026): warn at 75 % of each file's limit, before the release preflight fails.
        sys.path.insert(0, str(ROOT / 'tools'))
        import release
        self.assertEqual(release.TEXT_LIMIT, 262144)
        files = [REGISTER, JOURNAL, *sorted((DOCS / 'bugs').iterdir())]
        files += sorted(DOCS.glob('PATCH-v*.json'))  # whitespace baselines (RELEASE-PATCH-SIZE-33)
        big = ['%s %d of %d' % (p.name, p.stat().st_size, release.text_limit(p.relative_to(ROOT).as_posix()))
               for p in files if p.stat().st_size > 0.75 * release.text_limit(p.relative_to(ROOT).as_posix())]
        self.assertEqual(big, [], 'tracker files near the release text limit (tools/release.py)')

    def test_whitespace_baselines_get_the_named_limit(self):
        # RELEASE-PATCH-SIZE-33: docs/PATCH-v<version>.json lists every file of the published base
        # release; the v0.0.33-dev1 baseline (1,811 files) passed 256 KiB.
        sys.path.insert(0, str(ROOT / 'tools'))
        import release
        self.assertEqual(release.text_limit('docs/PATCH-v0.0.33-dev1.json'), 1048576)
        self.assertEqual(release.text_limit('docs/PATCH-v0.0.32.json'), 1048576)
        self.assertEqual(release.text_limit('docs/bugs/bugs.json'), 1048576)
        self.assertEqual(release.text_limit('docs/PATCH-NOTES.md'), release.TEXT_LIMIT)
        self.assertEqual(release.text_limit('tools/PATCH-v0.0.33.json'), release.TEXT_LIMIT)
        self.assertEqual(release.text_limit('README.md'), release.TEXT_LIMIT)

    def test_tracker_files_ship_in_release(self):
        shipped = set(json.loads((ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8')))
        files = [REGISTER, JOURNAL, *FROZEN, *sorted((DOCS / 'bugs').iterdir())]
        missing = [p.relative_to(ROOT).as_posix() for p in files
                   if p.is_file() and p.relative_to(ROOT).as_posix() not in shipped]
        self.assertEqual(missing, [], 'tracker files missing from tools/release-files.json')

    # CHIM Engine tracker (owner request, 9 October 2026): docs/bugs/CHIM_TRACKER.md, generated with
    # the register; every CHIM bug on it, CHIM- IDs always marked.
    def test_chim_tracker_is_generated_and_lists_every_chim_bug(self):
        bugs = bug_register.load()
        page = DOCS / 'bugs' / 'CHIM_TRACKER.md'
        self.assertTrue(page.is_file(), 'docs/bugs/CHIM_TRACKER.md missing: run tools/bug_register.py render')
        text = page.read_text(encoding='utf-8')
        want = bug_register.chim_tracker(bugs, JOURNAL.read_text(encoding='utf-8'), bug_register.chim_version())
        self.assertEqual(text, want, 'docs/bugs/CHIM_TRACKER.md is stale: run tools/bug_register.py render')
        chim = [b for b in bugs if 'chim' in b]
        self.assertTrue(chim)
        missing = [b['id'] for b in chim if '[%s](%s.md)' % (b['id'], b['id']) not in text and
                   '| %s |' % b['id'] not in text]
        self.assertEqual(missing, [], 'CHIM bugs missing from the CHIM Engine tracker')
        unmarked = [b['id'] for b in bugs if bug_register.must_be_chim(b) and 'chim' not in b]
        self.assertEqual(unmarked, [], 'CHIM- IDs or chim-streamer bugs without their CHIM part')
        for key, title in bug_register.CHIM_PARTS:
            self.assertIn('\n## %s\n' % title, text)
        self.assertIn('[CHIM Engine tracker](bugs/CHIM_TRACKER.md)', REGISTER.read_text(encoding='utf-8'))
        self.assertIn('bugs/CHIM_TRACKER.md', (DOCS / 'WORLD_STREAMER.md').read_text(encoding='utf-8'))
        outputs = bug_register.outputs(bugs, bug_register.load_families())
        self.assertIn('docs/bugs/CHIM_TRACKER.md', [p.relative_to(ROOT).as_posix() for p in outputs],
                      'render does not write the CHIM tracker with the register')

    def test_chim_ids_must_carry_their_part(self):
        chim = bug(id='CHIM-TEST-33', family='chim-streamer', build=dict(CHIM_BUILD))
        self.assertTrue(any('carries "chim"' in e for e in bug_register.validate([chim])), 'unmarked CHIM- ID passed')
        self.assertTrue(bug_register.validate([dict(chim, id='CHIMNEY-TEST-33', family='chim-streamer')]),
                        'unmarked chim-streamer bug passed')
        self.assertEqual(bug_register.validate([dict(chim, chim='streaming')]), [])
        self.assertTrue(bug_register.validate([dict(chim, chim='physics')]), 'unknown CHIM part passed')
        self.assertEqual(bug_register.validate([dict(chim, id='STAIRS-TEST-33', family='stairs-collision',
                                                     chim='stairs')]), [], 'an opted-in bug failed')
        self.assertTrue(bug_register.validate([dict(chim, chim='builder', build=dict(LEGACY_BUILD))]),
                        'a CHIM bug without a CHIM version passed')

    def test_bugs_merged_from_other_branches_appear_on_the_chim_tracker(self):
        # A branch registers CHIM-ZONE-FULL-33 before this mechanism existed (no chim, no build): after the
        # merge, render marks it and the page lists it; the build record is still demanded.
        merged = bug(id='CHIM-ZONE-FULL-33', title='Chunk loads fail when the CHIM zone is full', family='heap-memory',
                     where='CHIM engine zone cache, chunk loads', found_in='v0.0.33-dev', persists_in=['v0.0.33-dev'],
                     report='bugs/CHIM-ZONE-FULL-33.md')
        del merged['build']
        stairs = bug(id='CHIM-STAIRGATE-SLOW-33', title='The stair gate is slow on CHIM worlds', family='build-speed',
                     where='stair walkability gate on CHIM worlds', found_in='v0.0.33-dev', tags=['performance'])
        del stairs['build']
        bugs = [bug(), merged, stairs]
        self.assertEqual(bug_register.mark_chim(bugs), ['CHIM-ZONE-FULL-33', 'CHIM-STAIRGATE-SLOW-33'])
        self.assertEqual((merged['chim'], stairs['chim']), ('streaming', 'performance'))
        self.assertEqual(bug_register.mark_chim(bugs), [], 'marking is not idempotent')
        errors = bug_register.validate(bugs)
        self.assertTrue(any('CHIM-ZONE-FULL-33: missing build' in e for e in errors), errors)
        merged['build'] = dict(CHIM_BUILD, name=bug_register.BUILD_SOURCE, source_commit='f95cf75',
                               engine_commit='f95cf75', world_commit='f95cf75', chim_format='0.5')
        del merged['build']['unknown_reason']
        stairs['build'] = dict(merged['build'])
        page = bug_register.chim_tracker(bugs, '# Bug journal\n\n## CHIM-ZONE-FULL-33: found, 9 October 2026\n\nx\n',
                                         '0.1.0', pages=Path(tempfile.gettempdir()) / 'no-such-pages')
        part = page.split('\n## Engine streaming and memory\n', 1)[1].split('\n## ', 1)[0]
        self.assertIn('[CHIM-ZONE-FULL-33](CHIM-ZONE-FULL-33.md)', part)
        self.assertIn('source: CHIM 0.1.0, format 0.5, engine f95cf75', part)
        self.assertIn('CHIM-STAIRGATE-SLOW-33', page.split('\n## Performance\n', 1)[1])
        self.assertIn('(../BUG_JOURNAL.md#chim-zone-full-33-found-9-october-2026): CHIM-ZONE-FULL-33', page)
        self.assertIn('2 CHIM bugs: 2 open, 0 fixed, 0 closed.', page)
        self.assertNotIn('TEST-BUG-32', page)

    # Owner requirement, 9 October 2026: every bug says which build it was found in.
    def test_playtest_bugs_must_name_their_build(self):
        bare = bug(id='TEST-PLAY-33', found_in='v0.0.33-dev1', persists_in=['v0.0.33-dev1'])
        del bare['build']
        self.assertTrue(any('missing build' in e for e in bug_register.validate([bare])), 'playtest bug without build')
        for v in ('v0.0.32', 'v0.0.30-rc1', 'v0.0.33-dev2'):
            self.assertTrue(bug_register.validate([dict(bare, found_in=v, persists_in=[v])]), v)
        self.assertEqual(bug_register.validate([dict(bare, found_in='v0.0.33-dev', persists_in=['v0.0.33-dev'])]), [],
                         'a finding on a development line needs no build record')
        self.assertEqual(bug_register.validate([dict(bare, id='OLD-PLAY-29', found_in='v0.0.29-dev2')]), [])
        good = dict(bare, build=dict(LEGACY_BUILD, name='v0.0.33-dev1'))
        self.assertEqual(bug_register.validate([good]), [])
        self.assertEqual(bug_register.validate([dict(bare, build=dict(CHIM_BUILD))]), [])
        bad = [dict(LEGACY_BUILD, source_commit='unknown'),                       # unknown without a reason
               dict(LEGACY_BUILD, unknown_reason='no reason needed'),             # a reason without an unknown
               dict(LEGACY_BUILD, world_commit='0d8bf4f'),                        # a world in a legacy build
               dict(CHIM_BUILD, chim_format=None),                                # half a CHIM build
               dict(LEGACY_BUILD, source_commit='HEAD'), dict(LEGACY_BUILD, name=''),
               dict(CHIM_BUILD, chim_version='0.1'), dict(CHIM_BUILD, chim_format='v0.4'),
               dict(LEGACY_BUILD, path='/private/where'), {k: v for k, v in LEGACY_BUILD.items() if k != 'engine_commit'}]
        for b in bad:
            self.assertTrue(bug_register.validate([dict(bare, build=b)]), b)
        self.assertEqual([b['id'] for b in bug_register.load() if bug_register.needs_build(b) and 'build' not in b], [])

    def test_build_record_comes_from_the_receipt(self):
        preview = {'version': '0.0.32', 'source_commit': '0f467e4b907e28930e323b31a9db2fcfc17c1c47',
                   'chim_preview': {'name': 'AmiWind CHIM Preview 1 (v0.0.32 + CHIM Balmora)', 'chim_version': '0.1.0',
                                    'chim_world_format': '0.4', 'base_image': 'v0.0.32 release image (private place)',
                                    'engine': {'branch': 'v0.0.33-chim-engine',
                                               'commit': '0d8bf4feacbf6563485e712ffd1ca4201391c25d'},
                                    'chim_world': {'source': 'a private container run'}}}
        got = bug_register.build_from_receipt(preview, {'chim_version': '0.1.0'})
        self.assertEqual(got, dict(CHIM_BUILD, unknown_reason='the build receipt does not record world commit'))
        self.assertNotIn('private', json.dumps(got))
        dev = {'version': '0.0.32-dev3', 'source_commit': '91a7eebeaff7ed09d1f248817e9652a2feec9916'}
        self.assertEqual(bug_register.build_from_receipt(dev), LEGACY_BUILD)
        mini = {'version': '0.0.33-dev1', 'miniwind': {'description': 'x'}, 'source_commit': 'abcdef1',
                'builder': 'chim', 'chim_version': '0.1.0', 'world_format': '0.5'}
        self.assertEqual(bug_register.build_from_receipt(mini),
                         dict(name='MiniWind v0.0.33-dev1', source_commit='abcdef1', engine_commit='abcdef1',
                              world_commit='abcdef1', chim_version='0.1.0', chim_format='0.5'))
        old = bug_register.build_from_receipt({'version': '0.0.31'})
        self.assertEqual((old['name'], old['source_commit'], old['chim_version']), ('v0.0.31', 'unknown', None))
        self.assertIn('source commit', old['unknown_reason'])
        b = bug(build=got)
        self.assertEqual(bug_register.validate([b]), [])
        rows = dict(bug_register.build_rows(b))
        self.assertEqual(rows['CHIM engine version'], 'CHIM 0.1.0, engine 0d8bf4f, world format 0.4')
        self.assertEqual(rows['From commit'], 'source 0f467e4, engine 0d8bf4f, CHIM world unknown')
        self.assertEqual(bug_register.found_in_cell(dict(b, found_in='v0.0.33-dev')), 'v0.0.33-dev (CHIM Preview 1)')

    # Frames on bug pages follow the documentation image convention (docs/images, release-listed).
    def test_frames_on_bug_pages_are_listed_public_images(self):
        self.assertEqual(bug_register.image_problems(bug_register.load()), [])
        with tempfile.TemporaryDirectory() as tmp:
            pages, images = Path(tmp) / 'bugs', Path(tmp) / 'images'
            pages.mkdir()
            images.mkdir()
            good = 'amiwind-v0.0.33-chim-specks-bridge.png'
            (images / good).write_bytes(bug_register.IMAGE_MAGIC['.png'][0] + b'x' * 100)
            (images / 'amiwind-v0.0.33-big.png').write_bytes(bug_register.IMAGE_MAGIC['.png'][0] + b'x' * 1048577)
            (images / 'amiwind-v0.0.33-fake.png').write_bytes(b'not a png')
            text = ('# TEST-BUG-32: t\n\n![Specks, CHIM Preview 1, Balmora bridge](../images/%s)\n\n'
                    '```markdown\n![example](images/x.png)\n```\n' % good)
            (pages / 'TEST-BUG-32.md').write_text(text, encoding='utf-8')
            b = bug(report='bugs/TEST-BUG-32.md')
            rel = 'docs/images/' + good
            listed = ({rel}, set(), {rel}, {rel})
            self.assertEqual(bug_register.image_problems([b], pages, images, listed), [])
            self.assertEqual(bug_register.bug_images(b, pages), [good])
            for media, word in (((set(), set(), {rel}, {rel}), 'DOCUMENTATION_IMAGES'),
                                (({rel}, set(), set(), {rel}), 'release-files.json'),
                                (({rel}, set(), {rel}, set()), '.gitignore')):
                problems = bug_register.image_problems([b], pages, images, media)
                self.assertTrue(problems and word in problems[0], (word, problems))
            for ref, word in (('images/TEST-BUG-32/a.png', 'live in docs/images'), ('../images/Bad_Name.png', 'name'),
                              ('../images/amiwind-v0.0.33-gone.png', 'missing'),
                              ('../images/amiwind-v0.0.33-big.png', 'limit'),
                              ('../images/amiwind-v0.0.33-fake.png', 'not a PNG')):
                (pages / 'TEST-BUG-32.md').write_text('# TEST-BUG-32: t\n\n![f](%s)\n' % ref, encoding='utf-8')
                problems = bug_register.image_problems([b], pages, images, listed)
                self.assertTrue(any(word in p for p in problems), (ref, problems))
            (pages / 'TEST-BUG-32.md').write_text(text, encoding='utf-8')
            page = bug_register.chim_tracker([dict(b, id='TEST-BUG-32', chim='rendering')], '# Bug journal\n', '0.1.0',
                                             pages=pages)
            self.assertIn('[TEST-BUG-32](TEST-BUG-32.md) ([1 frame](../images/%s))' % good, page)

    def test_journal_changes_are_newest_first_and_capped(self):
        bugs = [bug(id='CHIM-A-33', chim='format'), bug(id='TEST-B-32')]
        journal = '# Bug journal\n\n<!-- contents start -->\n## Contents\n\n- CHIM-A-33\n\n<!-- contents end -->\n\n'
        journal += ''.join('## Entry %d, 9 October 2026\n\n%s\n\n' % (i, 'CHIM-A-33' if i % 2 else 'TEST-B-32')
                           for i in range(30))
        got = bug_register.journal_changes(bugs, journal)
        self.assertEqual(len(got), 10)
        self.assertEqual([g[0] for g in got[:2]], ['Entry 1, 9 October 2026', 'Entry 3, 9 October 2026'])
        self.assertEqual(got[0][1:], ('entry-1-9-october-2026', ['CHIM-A-33']))

    def test_frozen_trackers_are_marked(self):
        for p in FROZEN:
            self.assertTrue(p.is_file(), p)
            head = '\n'.join(p.read_text(encoding='utf-8').splitlines()[:6])
            self.assertIn(FROZEN_BANNER, head, 'frozen tracker lacks banner: %s' % p.name)


if __name__ == '__main__':
    unittest.main()
