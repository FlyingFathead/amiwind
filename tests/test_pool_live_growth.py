# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-CHIM-SERIAL-SECTIONS-44: the shared worker pools follow the scheduler's live allowance continuously, and the
memory-governed map admits each unit at its own size.

The maintainer (19 October 2026): with --jobs max the pools must keep an eye on how many workers are available: when
the allowance rises (another stage finished) a running pool starts more units at once, not when its next unit
finishes; it shrinks only by not starting new units. And the stair gate's pool sized every unit as its largest frame
(4 of 24 workers at 2,855 MiB for frames of about 300 MiB). Synthetic tasks and memory readings only."""
import contextlib
import io
import os
from pathlib import Path
import sys
import threading
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(Path(__file__).resolve().parent)]
import build_parallel  # noqa: E402
import resource_plan as rp  # noqa: E402
from test_stage_jobs_ceiling import Scheduler  # noqa: E402

GIB = 1 << 30


def timed_sleep(seconds):
    """Worker: (start, end) wall times of a sleep of SECONDS."""
    start = time.time()
    time.sleep(seconds)
    return start, time.time()


def sized_sleep(item):
    """Worker: (start, end) of a sleep; ITEM (seconds, MiB)."""
    return timed_sleep(item[0])


def peak(spans, after=0.0):
    """Most spans running at once at any start time from AFTER on."""
    best = 0
    for start, _ in spans:
        if start >= after:
            best = max(best, sum(1 for s, e in spans if s <= start < e))
    return best


class RaisedAllowance(unittest.TestCase):
    """Two long units hold the launch allowance of 2; the allowance rises to 6 half a second in. The short units must
    start while the long ones still run (before they finish at about 4 s), for every map kind."""

    def run_map(self, kind):
        items = [4.0, 4.0] + [0.5] * 8
        with Scheduler(jobs=2, allowance=2, budget=8) as sched, contextlib.redirect_stdout(io.StringIO()):
            path = Path(sched.env[build_parallel.ALLOWANCE_ENV])
            timer = threading.Timer(0.5, lambda: path.write_text('6\n'))
            began = time.time()
            timer.start()
            try:
                if kind == 'ordered':
                    spans = list(build_parallel.ordered_map(timed_sleep, items, 2))
                elif kind == 'completed':
                    spans = list(build_parallel.completed_map(timed_sleep, items, 2))
                else:
                    reader = lambda: ((64 * GIB, GIB, 0), None)     # noqa: E731
                    gov = lambda planned, unit_mib=None, label='stage', environ=None: rp.MemoryGovernor(  # noqa: E731
                        planned, unit_mib, label, reader=reader, log=lambda line: None)
                    with mock.patch.object(rp, 'governor_for', gov):
                        spans = list(build_parallel.governed_map(sized_sleep, [(s, 100) for s in items], 2,
                                                                 unit_mib=100, label='test',
                                                                 item_mib=lambda item: item[1]))
            finally:
                timer.cancel()
        starts = sorted(s - began for s, _ in spans)
        return starts, spans, began

    def check(self, kind):
        starts, spans, began = self.run_map(kind)
        # the short units start after the raise and well before the long ones end (about 4 s)
        short_starts = starts[2:]
        self.assertLess(short_starts[0], 2.5, '%s map: no unit started after the allowance rose: %s' % (kind, starts))
        self.assertGreaterEqual(peak(spans, began + 0.5), 5, '%s map: the pool did not grow to the raised allowance'
                                % kind)

    def test_ordered_map_grows_at_once(self):
        self.check('ordered')

    def test_completed_map_grows_at_once(self):
        self.check('completed')

    def test_governed_map_grows_at_once(self):
        self.check('governed')


class SizedAdmission(unittest.TestCase):
    """governed_map with item_mib: units admitted at their own sizes, the largest first with its room kept."""

    def governor(self, limit_gib, other_gib, cache_gib=0.0):
        """A governor whose container holds OTHER_GIB besides the units in flight (the reading includes them)."""
        self.flight = 0.0
        reader = lambda: ((int(limit_gib * GIB), int((other_gib + cache_gib) * GIB + self.flight * (1 << 20)),  # noqa: E731
                           int(cache_gib * GIB)), None)
        return rp.MemoryGovernor(24, 2855, 'stair', reader=reader, interval=0, log=lambda line: None)

    def admit(self, gov, mib, n, reserve=0.0):
        ok = gov.admits(self.flight, mib, n, reserve)
        if ok:
            self.flight += mib
        return ok

    def test_small_units_fill_the_room_the_largest_would_take(self):
        # 16 GiB limit, 6 in use: room (16 - 6) x 0.8 = 8 GiB; at 2,855 MiB a unit 2 fit, at 300 MiB 27
        gov = self.governor(16, 6)
        self.assertEqual(gov.limit(0), 2)                    # the method before v0.0.44: every unit at the largest
        n = 0
        while self.admit(gov, 300, n):
            n += 1
        self.assertEqual(n, 27)

    def test_a_waiting_head_keeps_its_room(self):
        gov = self.governor(16, 6)
        self.assertTrue(gov.admits(0, 2855, 0))              # nothing in flight: always starts
        for n in range(16):                                  # 4,800 MiB of small units in flight
            self.assertTrue(self.admit(gov, 300, n))
        # a 300 MiB unit still fits on its own (5,100 of 8,192 MiB) but not beside a waiting 2,855 MiB head (7,955 +)
        self.assertTrue(gov.admits(self.flight, 300, 16))
        self.assertFalse(gov.admits(self.flight + 300, 300, 17, reserve_mib=2855))

    def test_the_file_cache_is_not_in_use(self):
        # 8 GiB of reclaimable file cache beside 6 GiB in use: the room is still (16 - 6) x 0.8 = 8,192 MiB
        gov = self.governor(16, 6, cache_gib=8)
        n = 0
        while self.admit(gov, 300, n):
            n += 1
        self.assertEqual(n, 27)

    def test_sized_map_runs_many_small_units_beside_one_large(self):
        reader = lambda: ((16 * GIB, 6 * GIB, 0), None)     # noqa: E731
        gov = lambda planned, unit_mib=None, label='stage', environ=None: rp.MemoryGovernor(  # noqa: E731
            planned, unit_mib, label, reader=reader, interval=30, log=lambda line: None)
        items = [(1.5, 2855)] + [(0.6, 300)] * 12
        with mock.patch.object(rp, 'governor_for', gov), contextlib.redirect_stdout(io.StringIO()):
            spans = list(build_parallel.governed_map(sized_sleep, items, 8, unit_mib=2855, label='test',
                                                     item_mib=lambda item: item[1]))
        self.assertEqual(len(spans), len(items))
        # 8,192 MiB room: the 2,855 MiB head plus 7 small units (the 8 workers), never 2 at the largest size
        self.assertGreaterEqual(peak(spans), 7)


class StairPoolMemoryRoom(unittest.TestCase):
    def test_inactive_file_cache_is_left_out(self):
        from chim import stair_pool
        values = {'/sys/fs/cgroup/memory.max': str(16 * GIB), '/sys/fs/cgroup/memory.current': str(14 * GIB)}
        with mock.patch.object(stair_pool, '_read_int', lambda path: int(values[path]) if path in values else None), \
                mock.patch.object(stair_pool, '_inactive_file', lambda path: 8 * GIB):
            free, note = stair_pool.memory_room()
        self.assertEqual(free, 10 * GIB)
        self.assertIn('file cache', note)


if __name__ == '__main__':
    unittest.main()
