# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-IMAGE-QUEUE-STALL-62: a queued unit with a free worker always starts, and units start longest first.

completed_map and spread_map handed a whole batch of finished units to their caller before they looked at the pool
again: a caller that does real work per result (unit_store.run_each stores and reads back every unit) left the
workers idle with units still queued (the v0.0.62-dev1 image step: 4 queued, 0 running, 6.3 of 24 cores for 81 s).
They now hand back one result at a time and, between two, collect what finished and start the next units."""
import os
import time
import unittest
from unittest.mock import patch

import build_parallel

UNIT_SECONDS = 0.1
CALLER_SECONDS = 1.0


def started_at(item):
    """Pool worker: (item, the wall time it started), after UNIT_SECONDS of work."""
    began = time.time()
    time.sleep(UNIT_SECONDS)
    return item, began


def slow_wait(*args, **kwargs):
    """build_parallel.wait that lets every task in flight finish first: the batch case, every time."""
    time.sleep(0.3)
    return _REAL_WAIT(*args, **kwargs)


_REAL_WAIT = build_parallel.wait


class QueueRefill(unittest.TestCase):
    def setUp(self):
        patcher = patch.dict(os.environ, {'AMIWIND_POOL_CHUNKS': 'off'})
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in (build_parallel.ALLOWANCE_ENV,):
            os.environ.pop(name, None)

    def _run(self, mapper, **kwargs):
        starts, handed = {}, []
        with patch.object(build_parallel, 'wait', slow_wait):
            for item, began in mapper(started_at, list(range(12)), 2, **kwargs):
                starts[item] = began
                handed.append(time.time())
                time.sleep(CALLER_SECONDS)       # the caller's own work on one result (a store, a write)
        return starts, handed

    def _check_no_stall(self, starts, handed, unit, bound):
        self.assertEqual(sorted(starts), list(range(12)))
        # the UNIT-th unit to start must start right after the caller's first result, never only after the caller
        # worked through the whole first batch of finished units
        began = sorted(starts.values())[unit]
        self.assertLess(began - handed[0], bound,
                        'units waited in the queue with free workers while the caller worked through a batch')

    def test_completed_map_starts_queued_units_between_results(self):
        # 2 workers, 4 in flight: the first batch is 4 units; the 9th starts after one caller step (old: after 4)
        self._check_no_stall(*self._run(build_parallel.completed_map), unit=8, bound=2 * CALLER_SECONDS + 0.5)

    def test_spread_map_starts_queued_units_between_results(self):
        # 2 cores, 2 in flight: the 5th starts after one caller step (old: after 2)
        self._check_no_stall(*self._run(build_parallel.spread_map, spread=lambda item, offered: (item, 1)),
                             unit=4, bound=CALLER_SECONDS + 0.8)

    def test_longest_first(self):
        costs = {i: (i * 7) % 12 for i in range(12)}
        starts = {}
        for item, began in build_parallel.completed_map(started_at, list(range(12)), 2, cost=lambda i: costs[i]):
            starts[item] = began
        by_start = sorted(starts, key=lambda i: starts[i])
        # the first two to start are the two most expensive units; the last two the cheapest
        self.assertEqual(set(by_start[:2]), set(sorted(costs, key=lambda i: -costs[i])[:2]))
        self.assertEqual(set(by_start[-2:]), set(sorted(costs, key=lambda i: costs[i])[:2]))

    def test_every_result_once_after_a_failure_free_run(self):
        out = sorted(item for item, _ in build_parallel.completed_map(started_at, list(range(30)), 3))
        self.assertEqual(out, list(range(30)))


if __name__ == '__main__':
    unittest.main()
