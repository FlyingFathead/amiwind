# SPDX-License-Identifier: GPL-3.0-only
"""CHIM feature tracker: docs/chim/features.json is the source, docs/chim/FEATURES.md is generated.

The page cannot drift from the data, the data follows its schema, every bug ID and link resolves,
and the headline gains of the summary are the ones marked in the data.
"""
import copy
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import chim_features  # noqa: E402

PAGE = ROOT / 'docs' / 'chim' / 'FEATURES.md'


class FeatureTrackerTests(unittest.TestCase):
    def setUp(self):
        self.data = chim_features.load()

    def test_the_data_is_valid(self):
        self.assertEqual(chim_features.problems_of(self.data), [])

    def test_the_page_is_not_stale(self):
        self.assertEqual(PAGE.read_bytes(), chim_features.render(self.data).encode('utf-8'),
                         'docs/chim/FEATURES.md is stale: run tools/chim_features.py render')
        self.assertEqual(chim_features.check(), [])

    def test_files_are_lf_only_without_trailing_whitespace(self):
        for path in (PAGE, chim_features.DATA, ROOT / 'tools' / 'chim_features.py'):
            raw = path.read_bytes()
            self.assertNotIn(b'\r', raw, path.name)
            self.assertTrue(raw.endswith(b'\n') and not raw.endswith(b'\n\n'), path.name)
            for n, line in enumerate(raw.decode('utf-8').split('\n'), 1):
                self.assertEqual(line, line.rstrip(), '%s line %d has trailing whitespace' % (path.name, n))

    def test_every_feature_has_a_section_and_a_row_in_its_status_table(self):
        text = PAGE.read_text(encoding='utf-8')
        for f in self.data['features']:
            self.assertIn('#### %s\n' % f['name'], text)
            self.assertIn('`%s`' % f['id'], text)
            self.assertIn('| [%s](#%s) |' % (f['name'], chim_features.anchor(f['name'])), text)

    def test_every_status_has_a_row_and_the_counts_add_up(self):
        feats = self.data['features']
        text = PAGE.read_text(encoding='utf-8')
        for s in chim_features.STATUSES:
            title = chim_features.status_title(s, self.data['chim_version'])
            n = sum(1 for f in feats if f['status'] == s)
            self.assertIn('| %s | %s | %d |' % (title, chim_features.STATUS_MEANING[s], n), text)
        self.assertIn('%d features' % len(feats), text)

    def test_the_summary_lists_exactly_the_headline_gains(self):
        text = PAGE.read_text(encoding='utf-8')
        summary = text.split('## What CHIM has done so far')[1].split('## Features by status')[0]
        bullets = [l for l in summary.splitlines() if l.startswith('- **')]
        heads = [(f, g) for f in self.data['features'] for g in f['gains'] if g.get('headline')]
        self.assertGreaterEqual(len(heads), 5)
        self.assertEqual(len(bullets), len(heads))
        for line, (f, g) in zip(bullets, heads):
            self.assertIn(g['text'], line)
            self.assertIn('(#%s)' % chim_features.anchor(f['name']), line)

    def test_seeded_headline_figures_are_the_documented_ones(self):
        by_id = {f['id']: f for f in self.data['features']}
        disk = ' '.join(g['text'] for g in by_id['stored-once']['gains'])
        for figure in ('162.1 MB', '21.3 MB', '7.62 times', '190.4 MB', '7.83 MB', '24.3 times'):
            self.assertIn(figure, disk)
        pin = ' '.join(g['text'] for g in by_id['chunk-pinning']['gains'])
        self.assertIn('860 to 0', pin)
        self.assertIn('107 to 0', ' '.join(g['compared'] for g in by_id['chunk-pinning']['gains']))
        self.assertIn('3.7 % to 0 %', ' '.join(g['text'] for g in by_id['logs-in-memory']['gains']))

    def test_emulator_figures_are_labelled_relative_everywhere(self):
        text = PAGE.read_text(encoding='utf-8')
        for f in self.data['features']:
            for g in f['gains']:
                if g['basis'] == 'emulator':
                    self.assertIn(chim_features.figure_label(g), text)
                    self.assertIn('emulator, relative', chim_features.figure_label(g))

    def test_every_feature_without_a_gain_says_not_measured(self):
        text = PAGE.read_text(encoding='utf-8')
        n = sum(1 for f in self.data['features'] if not f['gains'])
        self.assertEqual(len(re.findall(r'\*\*Measured gain:\*\* (?:Not measured|not measured)', text)), n)

    def test_the_chim_version_follows_the_version_file(self):
        self.assertEqual(self.data['chim_version'], (ROOT / 'CHIM_VERSION').read_text().strip())
        self.assertIn('CHIM version: %s.' % self.data['chim_version'], PAGE.read_text(encoding='utf-8'))

    def test_the_page_is_linked_from_the_chim_docs_and_released(self):
        for rel in ('docs/chim/README.md', 'docs/WORLD_STREAMER.md'):
            self.assertIn('FEATURES.md', (ROOT / rel).read_text(encoding='utf-8'), rel)
        listed = json.loads((ROOT / 'tools' / 'release-files.json').read_text(encoding='utf-8'))
        for rel in ('docs/chim/FEATURES.md', 'docs/chim/features.json', 'tools/chim_features.py',
                    'tests/test_chim_features.py'):
            self.assertIn(rel, listed)


class FeatureTrackerChecksTests(unittest.TestCase):
    """The check refuses what the schema forbids."""

    def setUp(self):
        self.data = chim_features.load()

    def problems(self, mutate):
        data = copy.deepcopy(self.data)
        mutate(data)
        return chim_features.problems_of(data)

    def has(self, problems, text):
        self.assertTrue(any(text in p for p in problems), '%r not in %r' % (text, problems))

    def test_unknown_status(self):
        self.has(self.problems(lambda d: d['features'][0].update(status='done')), 'status must be one of')

    def test_in_release_needs_the_current_version(self):
        self.has(self.problems(lambda d: d['features'][0].update(version='0.0.1')), 'current CHIM version')
        self.has(self.problems(lambda d: d['features'][0].update(version=None)), 'needs a version')

    def test_planned_has_no_version_and_no_headline(self):
        def mutate(d):
            f = next(x for x in d['features'] if x['status'] == 'planned')
            f['version'] = '0.1.0'
        self.has(self.problems(mutate), 'version must be null')

        def headline(d):
            f = next(x for x in d['features'] if x['status'] == 'planned')
            f['gains'] = [{'headline': True, 'text': 'x', 'compared': 'y', 'basis': 'estimate',
                           'date': '2026-10-09'}]
            f['gain_short'] = 'x'
        self.has(self.problems(headline), 'cannot have a headline')

    def test_bad_bug_id_missing_bug_and_bad_commit(self):
        self.has(self.problems(lambda d: d['features'][0].update(bugs=['NOT-A-REAL-BUG-99'])),
                 'not in the bug register')
        self.has(self.problems(lambda d: d['features'][0].update(bugs=['lower-case'])), 'bad bug id')
        self.has(self.problems(lambda d: d['features'][0].update(commits=['xyz'])), 'short hash')

    def test_links_must_resolve(self):
        self.has(self.problems(lambda d: d['features'][0].update(
            links=[{'title': 'x', 'path': 'docs/NO_SUCH_FILE.md'}])), 'does not exist')
        self.has(self.problems(lambda d: d['features'][0].update(
            links=[{'title': 'x', 'path': 'docs/WORLD_STREAMER.md#no-such-heading'}])), 'has no heading')
        self.has(self.problems(lambda d: d['features'][0].update(links=[])), 'at least one link')

    def test_gain_rules(self):
        def no_host(d):
            f = next(x for x in d['features'] if any(g['basis'] == 'emulator' for g in x['gains']))
            for g in f['gains']:
                g.pop('host', None)
        self.has(self.problems(no_host), 'quiet, busy or mixed')

        def bad_basis(d):
            d['features'][0]['gains'][0]['basis'] = 'guess'
        self.has(self.problems(bad_basis), 'basis must be one of')

        def bad_date(d):
            d['features'][0]['gains'][0]['date'] = 'yesterday'
        self.has(self.problems(bad_date), 'date must be an ISO date')

        def no_short(d):
            d['features'][0].pop('gain_short')
        self.has(self.problems(no_short), 'gain_short')

        def no_note(d):
            f = next(x for x in d['features'] if not x['gains'])
            f.pop('gain_note')
        self.has(self.problems(no_note), 'needs a gain_note')

    def test_the_vis_story_is_required(self):
        self.has(self.problems(lambda d: d['features'][0].update(vis='')), 'vis must be a non-empty text')

    def test_duplicate_id_and_name(self):
        def dup(d):
            d['features'][1]['id'] = d['features'][0]['id']
        self.has(self.problems(dup), 'duplicate id')

        def same_name(d):
            d['features'][1]['name'] = d['features'][0]['name']
        self.has(self.problems(same_name), 'same heading anchor')

    def test_public_hygiene(self):
        self.has(self.problems(lambda d: d['features'][0].update(summary='see ' + 'C' + ':/x/private')),
                 'must not appear in public docs')
        self.has(self.problems(lambda d: d['features'][0].update(summary='a | b')), 'breaks the tables')

    def test_a_wrong_chim_version_is_refused(self):
        self.has(self.problems(lambda d: d.update(chim_version='9.9.9')), 'does not match CHIM_VERSION')


if __name__ == '__main__':
    unittest.main()
