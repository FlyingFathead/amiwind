"""BUILD-POOL-TINY-UNITS-48: completed_map hands many small units out in guided chunks, one pool task each.

The v0.0.48-dev2 chim stage ran 579 queued units of 0.1 s at 3.75 of 24 cores and the heap gate's 1,392 position
slices (each pickled with its frame's whole arrays) at 4.5 of 24: the parent could not keep the pool fed. Each unit
must still run its function on its item and give the same result (byte for byte), a failing unit must still end the
map with its error, few or slow units must still go out one by one, and AMIWIND_POOL_CHUNKS=off keeps one task per
unit (the method before v0.0.48)."""
import hashlib
import os
from pathlib import Path
import pickle
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import build_parallel  # noqa: E402


def tiny(item):
    return item, hashlib.sha256(str(item).encode()).hexdigest()


def slow(item):
    time.sleep(0.3)
    return item


def shared_payload(unit):
    """A unit that carries a large shared input, as the heap gate's slices carry their frame's arrays."""
    arrays, start, end = unit
    return start, hashlib.sha256(bytes(arrays['P'][start:end])).hexdigest()


def fails_at_7(item):
    if item == 7:
        raise ValueError('unit 7 is broken')
    return item


class Chunks(unittest.TestCase):

    def run_map(self, function, items, jobs, cost=None):
        with build_parallel.stage_pool(jobs, 'test') as stage:
            got = list(build_parallel.completed_map(function, items, jobs, cost=cost))
            return got, stage.tasks

    def test_small_units_go_out_in_chunks_with_the_same_results(self):
        items = list(range(600))
        got, tasks = self.run_map(tiny, items, 4)
        self.assertEqual(sorted(got), sorted(map(tiny, items)))
        self.assertLess(tasks, len(items) // 3, tasks)
        with patch.dict(os.environ, {'AMIWIND_POOL_CHUNKS': 'off'}):
            again, one_by_one = self.run_map(tiny, items, 4)
        self.assertEqual(one_by_one, len(items))
        self.assertEqual(pickle.dumps(sorted(again)), pickle.dumps(sorted(got)))

    def test_shared_inputs_go_once_per_chunk(self):
        arrays = {'P': bytes(range(256)) * 4096}         # 1 MiB shared by every slice
        units = [(arrays, k, k + 512) for k in range(0, 200 * 512, 512)]
        got, tasks = self.run_map(shared_payload, units, 4, cost=lambda u: 1)
        self.assertEqual(sorted(got), sorted(map(shared_payload, units)))
        self.assertLess(tasks, len(units) // 2)
        # one chunk of slices pickles the shared arrays once
        chunk = pickle.dumps([u for u in units[:10]])
        self.assertLess(len(chunk), 2 * len(pickle.dumps(units[0])))

    def test_few_or_slow_units_stay_one_by_one(self):
        got, tasks = self.run_map(tiny, list(range(12)), 4)        # fewer than 4 tasks per worker
        self.assertEqual(tasks, 12)
        with patch.object(build_parallel, '_chunk_seconds', lambda: 0.2):
            got, tasks = self.run_map(slow, list(range(40)), 4)    # 0.3 s units over a 0.2 s chunk cap
        self.assertEqual(sorted(got), list(range(40)))
        self.assertEqual(tasks, 40)

    def test_a_failing_unit_still_ends_the_map(self):
        with build_parallel.stage_pool(4, 'test'):
            seen = []
            with self.assertRaises(ValueError) as caught:
                for value in build_parallel.completed_map(fails_at_7, list(range(400)), 4):
                    seen.append(value)
        self.assertIn('unit 7 is broken', str(caught.exception))
        self.assertNotIn(7, seen)

    def test_generators_are_never_chunked(self):
        with build_parallel.stage_pool(4, 'test') as stage:
            got = list(build_parallel.completed_map(tiny, (i for i in range(300)), 4))
            self.assertEqual(stage.tasks, 300)
        self.assertEqual(sorted(got), sorted(map(tiny, range(300))))

    def test_chunk_size_is_guided(self):
        state = build_parallel._chunk_plan(1000)
        self.assertEqual(build_parallel._chunk_size(state, 8), 1)          # nothing measured yet
        state.update(units=8, seconds=0.4)                                  # 0.05 s a unit
        self.assertEqual(build_parallel._chunk_size(state, 8), 32)         # ceil(1000 / (4 x 8))
        state.update(left=40)
        self.assertEqual(build_parallel._chunk_size(state, 8), 2)          # the tail shrinks to single units
        state.update(left=1000, seconds=8 * 0.5)                            # 0.5 s a unit: 2 s cap -> 4
        self.assertEqual(build_parallel._chunk_size(state, 8), 4)
        state.update(on=False)
        self.assertEqual(build_parallel._chunk_size(state, 8), 1)


if __name__ == '__main__':
    unittest.main()
