"""BUILD-OOM-DEGRADE-NOT-DIE-54, BUILD-GUARD-BLIND-NO-CGROUP-55, TOOLKIT-MONITOR-NO-MEMORY-55.

A tester's public build on a plain Linux machine (no container) ran its chim stage 38 h at 0.4 cores and then died
with a bare BrokenProcessPool when the kernel killed a worker for memory. The memory guards read only a container's
cgroup limit, so on that machine they saw nothing; a lost worker ended the whole stage. These tests check that
completed_map sends a lost worker's units out again at half the units in flight and gives up after _pool_loss_retries(),
that the guards read the machine without a container limit, and that the build's memory reaches the Toolkit monitor."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import build_cache  # noqa: E402
import build_parallel  # noqa: E402
import resource_plan as rp  # noqa: E402

GIB = 1 << 30


def die_once(item):
    """Pool worker: the unit VALUE == 3 kills its own worker the first time (MARKER does not exist yet)."""
    marker, value = item
    if value == 3 and not os.path.exists(marker):
        Path(marker).write_text('lost')
        os._exit(9)
    return value * 2


def die_always(item):
    """Pool worker: the unit 3 kills its worker every time."""
    if item == 3:
        os._exit(9)
    return item


class LostWorker(unittest.TestCase):
    def test_a_lost_worker_costs_a_retry_not_the_map(self):
        with tempfile.TemporaryDirectory() as temp:
            marker = str(Path(temp) / 'marker')
            out = io.StringIO()
            with contextlib.redirect_stdout(out), mock.patch.dict(os.environ, {'AMIWIND_POOL_CHUNKS': 'off'}):
                got = sorted(build_parallel.completed_map(die_once, [(marker, v) for v in range(12)], 4))
        self.assertEqual(got, [v * 2 for v in range(12)])          # every unit handed back once
        self.assertIn('[pool] WARNING: RAM exhausted?', out.getvalue())
        self.assertIn('retry 1 of %d' % build_parallel._pool_loss_retries(), out.getvalue())

    def test_a_unit_that_always_kills_its_worker_ends_the_map(self):
        from concurrent.futures.process import BrokenProcessPool
        out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch.dict(os.environ, {'AMIWIND_POOL_CHUNKS': 'off'}):
            with self.assertRaises(BrokenProcessPool):
                list(build_parallel.completed_map(die_always, list(range(8)), 4))
        self.assertEqual(out.getvalue().count('[pool] WARNING: RAM exhausted?'), build_parallel._pool_loss_retries())

    def test_the_new_pool_code_is_scheduling_only(self):
        for name in ('completed_map', '_submit_chunk', '_oom_kills', '_pool_lost', '_pool_loss_retries'):
            self.assertIn(('tools/build_parallel.py', name), build_cache.SCHEDULING_UNITS, name)


class MachineMemory(unittest.TestCase):
    def test_without_a_container_limit_the_guards_read_the_machine(self):
        with mock.patch.object(rp, 'cgroup_memory', lambda root='/sys/fs/cgroup': (None, None, 0)), \
                mock.patch.object(rp, 'host_memory', lambda: (32 * GIB, 8 * GIB)):
            self.assertEqual(rp.build_memory(), (32 * GIB, 24 * GIB, 0))

    def test_a_container_limit_wins(self):
        with mock.patch.object(rp, 'cgroup_memory', lambda root='/sys/fs/cgroup': (30 * GIB, 5 * GIB, GIB)), \
                mock.patch.object(rp, 'host_memory', lambda: (64 * GIB, 60 * GIB)):
            self.assertEqual(rp.build_memory(), (30 * GIB, 5 * GIB, GIB))

    def test_the_scheduler_alarm_fires_on_a_plain_machine(self):
        lines = []
        clock = {'t': 0.0}
        with mock.patch.object(rp, 'cgroup_memory', lambda root='/sys/fs/cgroup': (None, None, 0)), \
                mock.patch.object(rp, 'host_memory', lambda: (16 * GIB, GIB // 2)), \
                mock.patch.object(rp, 'cgroup_threads', lambda root='/sys/fs/cgroup': None):
            guard = rp.SchedulerGuard(8, {'chim': 900}, clock=lambda: clock['t'], interval=0, log=lines.append,
                                      alarm_seconds=60, stage_reader=lambda pid: None)
            for t in (0.0, 61.0, 122.0):
                clock['t'] = t
                guard.tick({'chim': 8}, {'chim': 8})
        self.assertTrue(any('memory tight' in line for line in lines), lines)


class MonitorMemory(unittest.TestCase):
    def test_progress_reports_ram_and_warns_when_nearly_out(self):
        import build_progress
        progress = build_progress.Tracker.__new__(build_progress.Tracker)
        out = io.StringIO()
        with mock.patch.object(rp, 'cgroup_memory', lambda root='/sys/fs/cgroup': (None, None, 0)), \
                mock.patch.object(rp, 'host_memory', lambda: (16 * GIB, GIB)), contextlib.redirect_stdout(out):
            got = progress.memory_reading(100.0, ['chim'])
        self.assertEqual((got['source'], got['used_gib'], got['available_gib'], got['low']), ('machine', 15.0, 1.0, True))
        self.assertEqual((got['peak_gib'], got['peak_stages']), (15.0, ['chim']))
        self.assertIn('[memory] WARNING: RAM nearly exhausted', out.getvalue())
        self.assertIn('[memory] new peak', out.getvalue())

    def test_the_monitor_timeline_carries_the_memory_curve(self):
        import monitor_read
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'run1'
            run.mkdir(parents=True)
            profile = {'status': 'passed', 'wall_seconds': 30, 'budget': 4, 'stages': [],
                       'timeline': {'t': [0, 10, 20, 30], 'cores': [1, 4, 4, 2],
                                    'memory_bytes': [GIB, 6 * GIB, 3 * GIB, None], 'memory_limit_bytes': 8 * GIB}}
            (run / 'build-profile.json').write_text(json.dumps(profile), encoding='utf-8')
            reader = monitor_read.Reader(Path(temp))
            got = reader.timeline('run1')['timeline']
        self.assertEqual(got['memory'], [[0, 1.0], [10, 6.0], [20, 3.0]])
        self.assertEqual((got['memory_limit_gib'], got['memory_peak']), (8.0, [10, 6.0]))


if __name__ == '__main__':
    unittest.main()
