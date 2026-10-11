# SPDX-License-Identifier: GPL-3.0-only
"""Stair-walk records (tools/stair_records.py): a walk's result is reused only when the record is intact and a
passed build of the master builder checked it. BUILD-CHIM-STAIR-WALK-UNCACHED-36."""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import stair_records  # noqa: E402
from pass_cache import PassCache  # noqa: E402

ROWS = [{'map': 'bm019', 'kind': 'step', 'ref': '100', 'result': 'passed', 'detail': {'reference': '205'}},
        {'map': 'bm019', 'kind': 'ramp', 'ref': '101', 'result': 'failed', 'detail': {}}]
FACTS = {'AMIWIND_RUN_NAME': '2026_10_10_v0.0.36-dev3_full_3b5e7a9', 'AMIWIND_RUN_COMMIT': '3b5e7a9',
         'AMIWIND_RUN_VERSION': '0.0.36-dev3', 'AMIWIND_AW_REQUEST': ''}


class StairRecordTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, FACTS)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def cache(self, root=None):
        return PassCache('stair-walk', {'rule': 1}, 'sources-sha', root or self.root / 'cache')

    def run_folder(self, stored, name='2026_10_10_v0.0.36-dev3_full_3b5e7a9'):
        folder = self.root / 'runs' / name / 'chim-world'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'chim-stairs.json').write_text(json.dumps(
            {'pass_cache': {'stored': stored, 'frames': {'balmora': 'walked', 'seyda': 'reused from x (v, c, t)'}}}),
            encoding='utf-8')
        return folder.parent

    def test_a_record_carries_its_provenance_and_its_own_sha256(self):
        record = stair_records.make_record('k' * 64, ROWS, 'walker-sha')
        for field in ('key', 'walker', 'version', 'commit', 'run', 'request', 'time', 'counts', 'rows_sha256'):
            self.assertIn(field, record)
        self.assertEqual((record['run'], record['commit'], record['version']),
                         ('2026_10_10_v0.0.36-dev3_full_3b5e7a9', '3b5e7a9', '0.0.36-dev3'))
        self.assertEqual(record['counts'], {'rows': 2, 'passed': 1, 'failed': 1})
        self.assertTrue(stair_records.intact(record))
        damaged = json.loads(json.dumps(record))
        damaged['counts']['failed'] = 0
        self.assertFalse(stair_records.intact(damaged))
        self.assertFalse(stair_records.intact(None))

    def test_a_candidate_is_reused_only_after_its_run_is_promoted(self):
        cache = self.cache()
        stored = stair_records.store(cache, 'input-a', ROWS)
        record, mark = stair_records.lookup(cache, 'input-a')
        self.assertEqual((record['rows'], mark), (ROWS, None))          # a candidate: walked again
        self.assertEqual(list(record['rows'][0]), list(ROWS[0]))        # the walk's own key order
        run = self.run_folder([stored])
        counts = stair_records.promote(run, 'req-7')
        self.assertEqual((counts['reports'], counts['marked'], counts['walked'], counts['reused']), (1, 1, 1, 1))
        record, mark = stair_records.lookup(cache, 'input-a')
        self.assertEqual((mark['record_sha256'], mark['request']), (record['record_sha256'], 'req-7'))
        self.assertEqual(stair_records.provenance(mark),
                         'reused from 2026_10_10_v0.0.36-dev3_full_3b5e7a9 (0.0.36-dev3, 3b5e7a9, %s)' % record['time'])
        self.assertEqual(stair_records.promote(run, 'req-7')['already'], 1)

    def test_rows_stay_where_an_earlier_builder_reads_them_and_are_bound_to_the_record(self):
        cache = self.cache()
        stored = stair_records.store(cache, 'input-a', ROWS)
        stair_records.promote(self.run_folder([stored]))
        row = cache.load('input-a')[0]
        self.assertEqual(row['rows'], ROWS)                              # a build of an earlier commit reads these
        self.assertNotIn('rows', row['record'])                          # stored once
        cache.store('input-a', dict(row, rows=ROWS[:1]))                 # rows changed under an intact record
        self.assertEqual(stair_records.lookup(cache, 'input-a'), (None, None))

    def test_a_record_written_again_is_not_covered_by_the_old_mark(self):
        cache = self.cache()
        first = stair_records.store(cache, 'input-a', ROWS)
        stair_records.promote(self.run_folder([first]))
        with patch.dict(os.environ, {'AMIWIND_RUN_NAME': 'other-run'}):
            stair_records.store(cache, 'input-a', ROWS)                # a later candidate under the same key
        self.assertIsNone(stair_records.lookup(cache, 'input-a')[1])
        # promoting the first run again cannot mark the newer record
        self.assertEqual(stair_records.promote(self.run_folder([first]))['changed'], 1)

    def test_a_damaged_mark_or_a_missing_entry_is_never_trusted(self):
        cache = self.cache()
        stored = stair_records.store(cache, 'input-a', ROWS)
        stair_records.promote(self.run_folder([stored]))
        path = stair_records.mark_path(cache.root, stored['key'])
        mark = json.loads(path.read_text(encoding='utf-8'))
        mark['run'] = 'someone-else'
        path.write_text(json.dumps(mark), encoding='utf-8', newline='\n')
        self.assertIsNone(stair_records.lookup(cache, 'input-a')[1])
        gone = dict(stored, key='0' * 64)
        self.assertEqual(stair_records.promote(self.run_folder([gone], 'run-2'))['missing'], 1)

    def test_a_record_from_the_reuse_source_brings_its_mark(self):
        source = self.cache(self.root / 'old' / 'image-passes')
        stored = stair_records.store(source, 'input-a', ROWS)
        stair_records.promote(self.run_folder([stored]))
        here = self.cache(self.root / 'new' / 'image-passes')
        with patch.dict(os.environ, {'AMIWIND_CACHE_FALLBACK': str(self.root / 'old')}):
            record, mark = stair_records.lookup(here, 'input-a')
        self.assertIsNotNone(mark)
        self.assertTrue(stair_records.mark_path(here.root, stored['key']).is_file())   # pooled here
        self.assertIsNotNone(stair_records.lookup(here, 'input-a')[1])

    def test_promote_finds_legacy_and_chim_reports_and_prints_counts(self):
        cache = self.cache()
        run = self.root / 'runs' / 'r'
        (run / 'image').mkdir(parents=True)
        (run / 'image' / 'stair-walk.json').write_text(json.dumps(
            {'pass_cache': {'stored': [stair_records.store(cache, 'map-a', ROWS)], 'maps': {'bm019': 'walked'}}}),
            encoding='utf-8')
        (run / 'chim-world').mkdir()
        (run / 'chim-world' / 'chim-stairs.json').write_text(json.dumps(
            {'pass_cache': {'stored': [stair_records.store(cache, 'frame-a', ROWS)], 'frames': {'f': 'walked'}}}),
            encoding='utf-8')
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(stair_records.main(['promote', '--run', str(run), '--request', 'req-2']), 0)
        counts = json.loads(out.getvalue())
        self.assertEqual((counts['reports'], counts['marked'], counts['walked']), (2, 2, 2))


if __name__ == '__main__':
    unittest.main()
