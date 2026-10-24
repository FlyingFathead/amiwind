# SPDX-License-Identifier: GPL-3.0-only
"""tools/bug_lookup.py: the register search (24 October 2026). Synthetic registers only."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools')]
import bug_lookup  # noqa: E402


def bug(**kw):
    return dict({'id': 'TEST-BUG-48', 'title': 'A collision union fails', 'state': 'open', 'severity': 'medium',
                 'family': 'build-speed', 'chim': 'builder', 'found_in': 'v0.0.48-rc1', 'persists_in': ['v0.0.48-rc1'],
                 'where': 'tools/build_cache.py check_calls', 'status': 'Open.'}, **kw)


class LookupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'docs/bugs/archive').mkdir(parents=True)
        live = [bug(), bug(id='CHIM-CAVE21-NONCONVEX-FACE-48', title='A cave piece has a non-convex face',
                           family='converter-geometry', where='collision union', severity='low')]
        old = [bug(id='OLD-FIXED-40', state='fixed', found_in='v0.0.40', persists_in=['v0.0.40', 'v0.0.41'],
                   status='PERSISTING in v0.0.41'), bug()]
        (self.root / 'docs/bugs/bugs.json').write_text(json.dumps(live), encoding='utf-8')
        (self.root / 'docs/bugs/archive/bugs-v0.0.40.json').write_text(json.dumps(old), encoding='utf-8')
        (self.root / 'docs/bugs/TEST-BUG-48.md').write_text('# TEST-BUG-48 page\n', encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def run_lookup(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = bug_lookup.main(['--root', str(self.root), *argv])
        return code, out.getvalue(), err.getvalue()

    def test_loads_live_and_archived_once(self):
        ids = [b['id'] for b in bug_lookup.load(self.root)]
        self.assertEqual(ids, ['TEST-BUG-48', 'CHIM-CAVE21-NONCONVEX-FACE-48', 'OLD-FIXED-40'])

    def test_words_all_match_id_or_text(self):
        code, out, err = self.run_lookup('cave', 'non-convex')
        self.assertEqual(code, 0)
        self.assertIn('CHIM-CAVE21-NONCONVEX-FACE-48', out)
        self.assertNotIn('TEST-BUG-48', out)
        self.assertEqual(self.run_lookup('cave', 'nothing-like-this')[0], 1)

    def test_filters(self):
        self.assertIn('OLD-FIXED-40', self.run_lookup('--state', 'fixed')[1])
        self.assertNotIn('OLD-FIXED-40', self.run_lookup('--state', 'fixed', '--no-archived')[1])
        self.assertIn('OLD-FIXED-40', self.run_lookup('--persists')[1])
        out = self.run_lookup('--file', 'tools/build_cache.py')[1]
        self.assertIn('TEST-BUG-48', out)
        self.assertNotIn('CHIM-CAVE21', out)
        self.assertIn('CHIM-CAVE21', self.run_lookup('--found', 'v0.0.48', '--severity', 'low')[1])

    def test_json_and_page(self):
        records = json.loads(self.run_lookup('TEST-BUG-48', '--json')[1])
        self.assertEqual([r['id'] for r in records], ['TEST-BUG-48'])
        self.assertIn('# TEST-BUG-48 page', self.run_lookup('TEST-BUG-48', '--page')[1])

    def test_reads_the_real_register(self):
        # the repository's own register loads and every record has an id and a state
        bugs = bug_lookup.load()
        self.assertGreater(len(bugs), 1000)
        self.assertTrue(all(b.get('id') and b.get('state') for b in bugs))


if __name__ == '__main__':
    unittest.main()
