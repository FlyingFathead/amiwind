# SPDX-License-Identifier: GPL-3.0-only
"""The image step's stair walk on every core (BUILD-IMAGE-STAIR-WALK-SERIAL-36).

tools/stair_parallel.py splits every walked map's steps and ramps into units over the worker pool. The rows,
failures, summary and stored records are the same as the one-map-per-task walk (stair_walk.check), for any
worker count and unit size; a heavy map becomes several units (never one serial tail); the walk asks the pool
for --jobs N workers; the image step uses it.
"""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]
READY = all(importlib.util.find_spec(name) for name in ('numpy', 'scipy'))


def payload(root):
    from test_stair_walk import build
    maps = Path(root) / 'maps'
    maps.mkdir(parents=True)
    (maps / 'room.bsp').write_bytes(build(fill=True))
    (maps / 'hall.bsp').write_bytes(build())
    (maps / 'tall.bsp').write_bytes(build(rise=6.))
    return Path(root)


def without_bookkeeping(report):
    report = dict(report)
    report.pop('pass_cache', None)
    return json.dumps(report, indent=1, sort_keys=False)


@unittest.skipUnless(READY, 'numpy and scipy required')
class StairParallelTests(unittest.TestCase):
    def test_report_equals_the_whole_map_walk_for_any_unit_size_and_workers(self):
        import pass_cache
        import stair_parallel
        import stair_walk
        with tempfile.TemporaryDirectory() as temp, mock.patch.dict(os.environ, {pass_cache.ENV: 'off'}):
            id1 = payload(temp)
            reference = without_bookkeeping(stair_walk.check(id1, jobs=1, exempt=['room']))
            for unit_min, per_worker, jobs in ((1, 1, 1), (1, 64, 3), (2, 16, 2), (16, 16, 4)):
                with mock.patch.object(stair_parallel, 'UNIT_MIN', unit_min), \
                        mock.patch.object(stair_parallel, 'UNITS_PER_WORKER', per_worker):
                    got = without_bookkeeping(stair_parallel.check(id1, jobs=jobs, exempt=['room']))
                self.assertEqual(got, reference, (unit_min, per_worker, jobs))

    def test_a_map_is_split_into_several_units(self):
        import stair_parallel
        self.assertEqual(stair_parallel.split(10, 4), [(0, 4), (4, 8), (8, 10)])
        self.assertEqual(stair_parallel.split(0, 4), [(0, 0)])
        # the Arena Pit's 2,057 candidates on 24 workers: many units, none longer than the unit size
        size = stair_parallel.unit_size(37357, 24)
        self.assertLess(size, 2057 // 4)
        self.assertGreater(len(stair_parallel.split(2057, size)), 4)

    def test_the_walk_asks_the_pool_for_jobs_workers(self):
        # PARALLELIZATION NEVER REGRESSES: the units go to build_parallel.ordered_map with --jobs N workers
        import build_parallel
        import pass_cache
        import stair_parallel
        seen = []
        real = build_parallel.ordered_map

        def spy(function, items, jobs=None, cost=None, timings=None):
            items = list(items)
            seen.append((function.__name__, len(items), jobs, cost is not None))
            return real(function, items, 1, cost)
        with tempfile.TemporaryDirectory() as temp, mock.patch.dict(os.environ, {pass_cache.ENV: 'off'}), \
                mock.patch.object(build_parallel, 'ordered_map', spy), \
                mock.patch.object(stair_parallel, 'UNIT_MIN', 1), mock.patch.object(stair_parallel, 'UNITS_PER_WORKER', 1):
            stair_parallel.check(payload(temp), jobs=6, exempt=['room'])
        walks = [s for s in seen if s[0] == 'walk_unit']
        self.assertEqual(len(walks), 1)
        name, units, jobs, largest_first = walks[0]
        self.assertGreater(units, 3)            # more units than maps: no map is one serial unit
        self.assertEqual(jobs, min(6, units))
        self.assertTrue(largest_first)

    def test_records_are_shared_with_the_whole_map_walk(self):
        # the same pass cache and keys as stair_walk.check: a record stored by one is reused by the other
        import pass_cache
        import stair_parallel
        import stair_records
        import stair_walk
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            id1 = payload(root / 'run')
            (root / 'run' / 'image').mkdir()
            with mock.patch.dict(os.environ, {pass_cache.ENV: str(root / 'cache'), stair_walk.WALK_SAMPLE_ENV: '0'}):
                stair_parallel.require(id1, root / 'run' / 'image' / 'stair-walk.json', jobs=2, exempt=['room'])
                self.assertEqual(stair_records.promote(root / 'run')['marked'], 3)
                with mock.patch.object(stair_walk, 'check_map', side_effect=AssertionError('walked again')):
                    report = stair_walk.check(id1, jobs=1, exempt=['room'])
                self.assertTrue(all(v.startswith('reused') for v in report['pass_cache']['maps'].values()))
                with mock.patch.object(stair_parallel, 'walk_unit', side_effect=AssertionError('walked again')):
                    again = stair_parallel.check(id1, jobs=1, exempt=['room'])
                self.assertEqual(without_bookkeeping(again), without_bookkeeping(report))
            # a sampled reused map is walked again in units and compared
            with mock.patch.dict(os.environ, {pass_cache.ENV: str(root / 'cache'), stair_walk.WALK_SAMPLE_ENV: '1'}):
                sampled = stair_parallel.check(id1, jobs=2, exempt=['room'])
            self.assertEqual(len(sampled['pass_cache']['walked_again']), 1)
            self.assertEqual(without_bookkeeping(sampled), without_bookkeeping(report))

    def test_the_image_step_uses_the_unit_walk(self):
        text = (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8')
        self.assertIn('from stair_parallel import require as require_stairs', text)
        self.assertNotIn('from stair_walk import require as require_stairs', text)

    def test_walk_keys_reach_the_walkers_and_never_the_bookkeeping(self):
        # BUILD-STAIR-KEY-BOOKKEEPING-36: stored walks are keyed by the workers that walk (and what they reach);
        # the orchestration, the progress counter and the records never rekey them
        from build_cache import SourceIndex
        import pass_cache
        import stair_walk
        index = SourceIndex(ROOT, top_format=pass_cache.PASS_KEY_FORM)
        # (the CHIM frame gate's key is the CHIM stair gate worker's: chim/collision.py)
        for script, function in stair_walk.walk_key_sources():
            _, _, uncertain = index.entry_digest(Path(script), function, pass_cache.PASS_KEY_NEUTRAL)
            self.assertFalse(uncertain, (script, function))
            reached = index._reached.get('%s::%s' % (Path(script).resolve(), function)) or set()
            for bookkeeping in ('tools/stair_records.py', 'tools/stair_progress.py', 'tools/progress_line.py'):
                self.assertNotIn(bookkeeping, reached, (script, function))
            self.assertIn('tools/stair_walk.py', reached)
        for path in ('tools/stair_walk.py', 'tools/stair_parallel.py'):
            text = (ROOT / path).read_text(encoding='utf-8')
            self.assertNotIn("PassCache.open('stair-walk', options, __file__)", text)
            self.assertNotIn("PassCache.open('stair-walk', options, sw.__file__)", text)


if __name__ == '__main__':
    unittest.main()
