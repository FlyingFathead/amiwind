# SPDX-License-Identifier: GPL-3.0-only
"""Long public documents carry an up-to-date contents list (tools/doc_toc.py)."""
import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import doc_toc  # noqa: E402

LINK = re.compile(r'^\s*- \[.*\]\(#([^)]+)\)$')


def doc(title='# Title', intro='Intro text.', sections=6, body=30, sub=0):
    lines = [title, '']
    if intro:
        lines += [intro, '']
    for n in range(sections):
        lines += ['## Section %d' % n, '']
        for k in range(sub):
            lines += ['### Part %d.%d' % (n, k), '', 'text', '']
        lines += ['line %d' % i for i in range(body)] + ['']
    return '\n'.join(lines)


def block_links(text):
    lines = text.split('\n')
    a, b = lines.index(doc_toc.START), lines.index(doc_toc.END)
    return [LINK.match(l).group(1) for l in lines[a:b] if LINK.match(l)]


def heading_anchors(text):
    s = doc_toc.Slugger()
    return {s(raw) for _, _, raw in doc_toc.headings(text.split('\n'))}


class AnchorTests(unittest.TestCase):
    def test_punctuation_is_removed_and_spaces_become_hyphens(self):
        cases = {
            'Hello, World!': 'hello-world',
            'v0.0.28 — Trees and Grass, Day and Night': 'v0028--trees-and-grass-day-and-night',
            'J011 — incomplete terrain/rock formation (open)': 'j011--incomplete-terrainrock-formation-open',
            'What does "CHIM" mean? (FAQ)': 'what-does-chim-mean-faq',
            'Step 1: build & test': 'step-1-build--test',
            'C# and C++': 'c-and-c',
            'a _ b': 'a-_-b',
        }
        for heading, anchor in cases.items():
            self.assertEqual(doc_toc.slug(heading), anchor, heading)

    def test_code_spans_links_and_emphasis(self):
        cases = {
            'The `dbg tp` command': 'the-dbg-tp-command',
            '`aw_skyline_fill` and _emphasis_': 'aw_skyline_fill-and-emphasis',
            '`--jobs N` is exact': '--jobs-n-is-exact',
            '**Bold** and *it* and snake_case': 'bold-and-it-and-snake_case',
            'See [the map](WORLD.md#x) now': 'see-the-map-now',
            'Use \\_underscores\\_ literally': 'use-_underscores_-literally',
            'Tags <kbd>F12</kbd> &amp; more': 'tags-f12--more',
            '``code with ` tick``': 'code-with--tick',
        }
        for heading, anchor in cases.items():
            self.assertEqual(doc_toc.slug(heading), anchor, heading)

    def test_non_ascii_letters_stay_and_symbols_go(self):
        self.assertEqual(doc_toc.slug('Ääkköset ja Ünïcödé'), 'ääkköset-ja-ünïcödé')
        self.assertEqual(doc_toc.slug('Fire 🔥 and ice'), 'fire--and-ice')
        self.assertEqual(doc_toc.slug('Squared ² half ½ µ'), 'squared--half--µ')

    def test_duplicates_are_numbered_like_github(self):
        s = doc_toc.Slugger()
        self.assertEqual([s(h) for h in ('Notes', 'Notes', 'Notes-1', 'Notes', 'Other')],
                         ['notes', 'notes-1', 'notes-1-1', 'notes-2', 'other'])

    def test_heading_parsing_skips_fences_comments_and_closing_hashes(self):
        text = '\n'.join(['# T', '## One ##', '## C#', '```sh', '## not a heading', '```',
                          '~~~~', '```', '## still code', '~~~~', '<!--', '## commented', '-->',
                          '    ## indented code', '#hashtag', '### Three'])
        self.assertEqual([(lvl, raw) for _, lvl, raw in doc_toc.headings(text.split('\n'))],
                         [(1, 'T'), (2, 'One'), (2, 'C#'), (3, 'Three')])


class RenderTests(unittest.TestCase):
    def test_short_documents_are_untouched(self):
        text = doc(sections=2, body=5)
        self.assertEqual(doc_toc.render(text), text)

    def test_list_goes_after_title_and_intro(self):
        out = doc_toc.render(doc())
        lines = out.split('\n')
        self.assertEqual(lines[:5], ['# Title', '', 'Intro text.', '', doc_toc.START])
        self.assertEqual(lines[5], '## Contents')
        self.assertEqual(block_links(out), ['section-%d' % n for n in range(6)])

    def test_list_goes_right_after_title_without_intro(self):
        out = doc_toc.render(doc(intro=''))
        self.assertEqual(out.split('\n')[:3], ['# Title', '', doc_toc.START])
        table = doc(intro='| a | b |\n| --- | --- |')
        lines = doc_toc.render(table).split('\n')
        self.assertEqual(lines[2], doc_toc.START)
        self.assertIn('| a | b |', lines[lines.index(doc_toc.END) + 2])

    def test_intro_ending_with_colon_stays_with_what_follows(self):
        lines = doc_toc.render(doc(intro='Three kinds:\n\n| a | b |\n| --- | --- |')).split('\n')
        self.assertEqual(lines[2], doc_toc.START)
        self.assertEqual(lines[lines.index(doc_toc.END) + 2:lines.index(doc_toc.END) + 5],
                         ['Three kinds:', '', '| a | b |'])

    def test_generated_block_under_title_stays_with_title(self):
        # DOCS-TOC-RENDER-FIGHT-33: a bug page's generated fact table sits right under the title
        # (tools/bug_register.py render); the list must go after it, or the two generators move
        # each other's blocks on every run.
        facts = ['<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->',
                 '', '| Fact | Value |', '| --- | --- |', '| Reported by | test |', '',
                 '<!-- END GENERATED FACTS -->']
        lines = doc(intro=None).split('\n')
        text = '\n'.join(lines[:2] + facts + [''] + lines[2:])
        out = doc_toc.render(text)
        got = out.split('\n')
        self.assertEqual(got[2:2 + len(facts)], facts)
        self.assertGreater(got.index(doc_toc.START), got.index(facts[-1]))
        self.assertEqual(doc_toc.render(out), out)
        self.assertEqual(doc_toc.strip_block(out), text)

    def test_bug_page_render_and_contents_list_agree(self):
        import bug_register
        bug = {'id': 'TEST-PAGE-33', 'title': 'T', 'state': 'open', 'fixed_in': None, 'owner_accepted': None,
               'status': 'Open', 'report': 'bugs/TEST-PAGE-33.md', 'reported_by': 'test',
               'found_date': '2026-10-08', 'found_in': 'v0.0.33-dev', 'where': 'here', 'reproduction': 'always',
               'duplicate_of': None, 'persists_in': ['v0.0.33-dev'], 'severity': 'low', 'severity_reason': 'Test.',
               'family': 'tests-ci', 'related': []}
        families = {f['key']: f for f in bug_register.load_families()}
        body = doc(title='# TEST-PAGE-33: T', intro=None)
        page = bug_register.rendered_page(body, bug, [bug], {bug['id']: bug}, families)
        page = doc_toc.render(page)
        again = bug_register.rendered_page(page, bug, [bug], {bug['id']: bug}, families)
        self.assertEqual(again, page if page.endswith('\n') else page + '\n')
        self.assertEqual(doc_toc.render(again), again)

    def test_rerun_is_idempotent_and_strip_restores(self):
        text = doc(sub=2, body=40)
        once = doc_toc.render(text)
        self.assertEqual(doc_toc.render(once), once)
        self.assertEqual(doc_toc.strip_block(once), text)

    def test_stale_list_is_replaced(self):
        old = doc_toc.render(doc())
        edited = old.replace('## Section 3', '## Renamed section')
        new = doc_toc.render(edited)
        self.assertIn('renamed-section', block_links(new))
        self.assertNotIn('section-3', block_links(new))
        self.assertEqual(new.count(doc_toc.START), 1)

    def test_document_that_shrinks_loses_its_list(self):
        text = doc_toc.render(doc())
        short = '\n'.join(l for l in text.split('\n') if not l.startswith('line '))
        out = doc_toc.render(short)
        self.assertNotIn(doc_toc.START, out)
        self.assertEqual(out, doc_toc.strip_block(short))

    def test_third_level_only_in_long_documents(self):
        medium = doc_toc.render(doc(sections=6, body=20, sub=1))
        self.assertLess(len(medium.splitlines()), doc_toc.NESTED_LINES)
        self.assertFalse(any('part-' in a for a in block_links(medium)))
        long = doc_toc.render(doc(sections=6, body=50, sub=2))
        self.assertIn('  - [Part 0.0](#part-00)', long.split('\n'))
        self.assertIn('- [Section 0](#section-0)', long.split('\n'))

    def test_contents_heading_takes_its_anchor_first(self):
        text = doc() + '\n## Contents\n\nmore\n'
        out = doc_toc.render(text)
        self.assertEqual(block_links(out)[-1], 'contents-1')

    def test_every_link_resolves_and_body_is_unchanged(self):
        text = doc(body=40).replace('## Section 2', '## Section 2: `code` & [link](x.md)')
        text = text.replace('line 3\n', '```\n## fenced\n| x |\n```\n', 1)
        out = doc_toc.render(text)
        anchors = heading_anchors(out)
        for a in block_links(out):
            self.assertIn(a, anchors)
        self.assertIn('- [Section 2: `code` & link](#section-2-code--link)', out.split('\n'))
        self.assertEqual(doc_toc.strip_block(out), text)

    def test_broken_markers_are_refused(self):
        with self.assertRaises(ValueError):
            doc_toc.render(doc() + '\n' + doc_toc.START + '\n')


class AnchorLinkTests(unittest.TestCase):
    """DOCS-DEAD-ANCHORS-32: a #anchor link must name a heading or anchor of its target."""

    def test_dead_anchors_are_reported_and_live_ones_pass(self):
        target = '\n'.join(['# A', '', '## Real heading', '', '## Façade', '', '<a id="manual"></a>', 'text', ''])
        source = '\n'.join([
            '# B', '', '## Local', '',
            '[ok](a.md#real-heading) [local](#local) [encoded](a.md#fa%C3%A7ade) [id](a.md#manual)',
            '[wrapped link',
            'text](a.md#wrapped-gone)',
            '[gone](a.md#renamed-heading "title")',
            '`[in code](a.md#code-gone)` ![image](a.md#image-gone) [web](https://example.com/x.md#gone)',
            '[file missing](missing.md#gone) [not markdown](tool.py#L1)',
            '', '```', '[fenced](a.md#fenced-gone)', '```', '',
            '[ref]: a.md#reference-gone', ''])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'docs' / 'journals').mkdir(parents=True)
            (root / 'docs' / 'a.md').write_bytes(target.encode('utf-8'))
            (root / 'docs' / 'b.md').write_bytes(source.encode('utf-8'))
            (root / 'docs' / 'tool.py').write_bytes(b'')
            (root / 'docs' / 'journals' / 'old.md').write_bytes(b'# Old\n\n[gone](../a.md#gone)\n')
            dead = doc_toc.dead_anchors(['docs/a.md', 'docs/b.md', 'docs/journals/old.md'], root=root)
        self.assertEqual(dead, ['docs/b.md:7: a.md#wrapped-gone', 'docs/b.md:8: a.md#renamed-heading',
                                'docs/b.md:16: a.md#reference-gone'])

    def test_contents_lists_count_as_links(self):
        out = doc_toc.render(doc())
        self.assertEqual(len(doc_toc.anchor_links(out)), 6)


class ScopeTests(unittest.TestCase):
    def test_readme_frozen_generated_and_licences_are_excluded(self):
        for rel in ('README.md', 'docs/journals/BUG_JOURNAL-v0.0.29.md', 'docs/RELEASE-v0.0.31.md',
                    'docs/BUGS-v0.0.29-RC1.md', 'docs/RC2_ISSUE_CHECKPOINT.md', 'docs/PATCH-v0.0.20.md',
                    'docs/BUGS.md', 'docs/AMIWIND_CONSOLE_COMMANDS.md', 'LICENSE.md', 'engine/COPYING.md'):
            self.assertTrue(doc_toc.excluded(rel), rel)
        for rel in ('docs/ROADMAP.md', 'docs/bugs/README.md', 'docs/LICENSING_AND_CREDITS.md'):
            self.assertIsNone(doc_toc.excluded(rel), rel)

    def test_excluded_files_carry_no_list(self):
        for rel in doc_toc.public_docs():
            if doc_toc.excluded(rel):
                text = (ROOT / rel).read_bytes().decode('utf-8')
                self.assertNotIn(doc_toc.START, text, rel)
                self.assertNotIn(doc_toc.END, text, rel)

    def test_readme_stays_as_is(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            doc_toc.main(['list', 'README.md'])
        self.assertIn('skip  README.md', out.getvalue())

    def test_tool_and_test_are_public_files(self):
        shipped = json.loads((ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8'))
        self.assertIn('tools/doc_toc.py', shipped)
        self.assertIn('tests/test_doc_toc.py', shipped)


class RepositoryTests(unittest.TestCase):
    def test_long_documents_have_current_lists(self):
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = doc_toc.main(['check'])
        self.assertEqual(code, 0, 'run tools/doc_toc.py write\n' + err.getvalue())

    def test_generated_links_resolve(self):
        lists = 0
        for rel in doc_toc.public_docs():
            text = (ROOT / rel).read_bytes().decode('utf-8')
            if doc_toc.START not in text:
                continue
            lists += 1
            anchors = heading_anchors(text)
            for a in block_links(text):
                self.assertIn(a, anchors, '%s #%s' % (rel, a))
        self.assertGreater(lists, 50)

    def test_every_anchor_link_resolves(self):
        # DOCS-DEAD-ANCHORS-32: seven links pointed at renamed or removed headings.
        self.assertEqual(doc_toc.dead_anchors(doc_toc.public_docs()), [])


if __name__ == '__main__':
    unittest.main()
