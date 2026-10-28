# SPDX-License-Identifier: GPL-3.0-only
"""The docs/ layout (v0.0.55 reorganisation): every document indexed, the index pages generated, no per-version file
at the docs/ root, every release listed, every relative link resolving, and the move record consistent."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import docs_index  # noqa: E402
import docs_move  # noqa: E402

DOCS = ROOT / 'docs'


class DocsLayoutTest(unittest.TestCase):
    def test_every_doc_in_index(self):
        self.assertEqual(docs_index.problems_topics(), [])
        index = (DOCS / 'README.md').read_text(encoding='utf-8')
        for name in docs_index.root_docs():
            self.assertIn('](%s)' % name, index, 'docs/%s is not in docs/README.md' % name)
        for folder in docs_index.doc_folders():
            self.assertIn('](%s/)' % folder, index, 'docs/%s/ is not in docs/README.md' % folder)

    def test_index_pages_are_generated(self):
        for rel, render in docs_index.PAGES.items():
            self.assertEqual((ROOT / rel).read_text(encoding='utf-8'), render(),
                             '%s is stale: run python3 tools/docs_index.py write' % rel)

    def test_no_per_version_file_at_docs_root(self):
        bad = [p.name for p in DOCS.iterdir() if p.is_file() and docs_index.PER_VERSION_ROOT.match(p.name)]
        self.assertEqual(bad, [], 'release notes go to docs/releases/notes/, whitespace baselines to '
                         'docs/releases/patches/, one-off records to docs/history/<kind>/')

    def test_pattern_refuses_the_old_names(self):
        for name in ('RELEASE-v0.0.55.md', 'PATCH-v0.0.55.json', 'CHECKPOINT_018_VALIDATION.md', 'LOCAL-RC11.md',
                     'FEEDBACK-v0.0.55-dev1.md', 'INVESTIGATION-v0.0.55.md', 'VALIDATION-v0.0.55.md',
                     'PLAN-v0.0.55.md', 'MERGE-v0.0.55.md', 'RECONCILE-v0.0.55.md', 'HORSTATORS_MUSINGS_2026-10-28.md'):
            self.assertTrue(docs_index.PER_VERSION_ROOT.match(name), name)
        for name in ('ROADMAP.md', 'RELEASE_WORKFLOW.md', 'PLAYER_MOVEMENT.md', 'WHITESPACE-BASELINE.json'):
            self.assertFalse(docs_index.PER_VERSION_ROOT.match(name), name)

    def test_releases_index_complete(self):
        page = (DOCS / 'releases' / 'README.md').read_text(encoding='utf-8')
        for kind in ('notes', 'patches'):
            for p in (DOCS / 'releases' / kind).iterdir():
                self.assertIn('](%s/%s)' % (kind, p.name), page, 'docs/releases/%s/%s is not listed' % (kind, p.name))

    def test_every_history_record_listed(self):
        page = (DOCS / 'history' / 'README.md').read_text(encoding='utf-8')
        for p in (DOCS / 'history').rglob('*'):
            if p.is_file() and p.parent != DOCS / 'history':
                rel = p.relative_to(DOCS / 'history').as_posix()
                self.assertIn('](%s)' % rel, page, 'docs/history/%s is not listed' % rel)

    def test_no_new_broken_links(self):
        allow = {tuple(r) for r in json.loads((ROOT / 'tests' / 'docs_broken_links_allowlist.json')
                                              .read_text(encoding='utf-8'))['links']}
        found = set(docs_index.broken_links())
        self.assertEqual(sorted(found - allow), [], 'relative links that name no file')
        self.assertEqual(sorted(allow - found), [], 'allowlisted links that resolve now: remove their rows')

    def test_moves_record_consistent(self):
        doc = json.loads((ROOT / docs_move.MOVES_FILE).read_text(encoding='utf-8'))
        for old, new in doc['moves'].items():
            self.assertFalse((ROOT / old).exists(), 'moved file is back at its old path: ' + old)
            self.assertTrue((ROOT / new).is_file(), 'moved file missing: ' + new)
        for old, replacements in doc['superseded'].items():
            self.assertTrue(doc['moves'][old].startswith('docs/history/superseded/'), old)
            text = (ROOT / doc['moves'][old]).read_text(encoding='utf-8')
            self.assertIn(docs_move.superseded_line(doc['moves'][old], replacements), text)
            for r in replacements:
                self.assertTrue((ROOT / r).exists(), 'replacement of %s missing: %s' % (old, r))

    def test_link_rewrite(self):
        moves = {'docs/RELEASE-v1.md': 'docs/releases/notes/RELEASE-v1.md', 'docs/PLAN-v1.md': 'docs/history/plans/PLAN-v1.md'}
        text = 'See [notes](RELEASE-v1.md#known), [bugs](BUGS.md), [plan](PLAN-v1.md), [web](https://x/y.md), [a](#top).'
        self.assertEqual(docs_move.rewrite_links(text, 'docs/RELEASE-v1.md', moves['docs/RELEASE-v1.md'], moves),
                         'See [notes](RELEASE-v1.md#known), [bugs](../../BUGS.md), [plan](../../history/plans/PLAN-v1.md), '
                         '[web](https://x/y.md), [a](#top).')
        self.assertEqual(docs_move.rewrite_links('[n](RELEASE-v1.md) [r](ROADMAP.md)', 'docs/FAQ.md', 'docs/FAQ.md', moves),
                         '[n](releases/notes/RELEASE-v1.md) [r](ROADMAP.md)')
        pattern = docs_move.token_pattern(moves)
        self.assertEqual(docs_move.rewrite_tokens('read docs/PLAN-v1.md, not docs/PLAN-v10.md', moves, pattern),
                         'read docs/history/plans/PLAN-v1.md, not docs/PLAN-v10.md')


if __name__ == '__main__':
    unittest.main()
