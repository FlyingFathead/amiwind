"""BUILD-POOL-MEMORY-PEAK-48: a stage's idle worker processes end when its allowance falls, and their memory comes back.

The v0.0.48-dev2 build held chim and chim-room-batches at one worker each for over ten minutes at 42 of 44 GiB: a cut
of the allowance stopped new units, but the idle workers stayed alive with what they held (about 0.75 GiB each).
Under the scheduler each worker pool now has a watcher (build_parallel._watch_idle_workers) that ends the idle workers
above the allowance; new ones start when the allowance grows again. These tests measure the memory of the workers
before and after a cut, check that the pool keeps working (no broken pool, more workers again after a raise) for the
completed maps and for the ordered maps of a stage pool, and that the new functions key no stage."""
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import build_cache  # noqa: E402
import build_parallel  # noqa: E402

HOLD_MIB = 96
_HELD = []


def hold(item):
    """Pool worker: keep about HOLD_MIB in this process (as a module memo does) and return its pid."""
    if not _HELD:
        _HELD.append(bytearray(os.urandom(1024)) * (HOLD_MIB * 1024))
    time.sleep(0.4)
    return item, os.getpid()


def rss_mib(pids):
    total = 0
    for pid in pids:
        try:
            for line in Path('/proc/%d/status' % pid).read_text().splitlines():
                if line.startswith('VmRSS:'):
                    total += int(line.split()[1]) // 1024
        except OSError:
            pass
    return total


@unittest.skipUnless(sys.platform.startswith('linux'), 'reads /proc')
class IdleWorkersEnd(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.allowance = Path(self.temp.name) / '01-stage'
        self.allowance.write_text('8\n')
        self.env = patch.dict(os.environ, {build_parallel.ALLOWANCE_ENV: str(self.allowance),
                                           build_parallel.BUDGET_ENV: '8', 'AMIWIND_BUILD_JOBS': '8'})
        self.env.start()
        self.fast = [patch.object(build_parallel, '_trim_after_seconds', lambda: 0.6),
                     patch.object(build_parallel, '_trim_poll_seconds', lambda: 0.2)]
        for p in self.fast:
            p.start()

    def tearDown(self):
        for p in self.fast:
            p.stop()
        self.env.stop()
        self.temp.cleanup()

    def wait_for(self, condition, seconds=20.0):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if condition():
                return True
            time.sleep(0.1)
        return condition()

    def check_cut_frees_memory(self, run_map):
        with build_parallel.stage_pool(8, 'test') as stage:
            self.assertIsNotNone(stage)
            got = run_map()
            self.assertEqual(sorted(i for i, _ in got), list(range(8)))
            pool = stage.executor
            pids = list(pool._processes)
            self.assertGreaterEqual(len({pid for _, pid in got}), 4)
            before = rss_mib(pids)
            self.allowance.write_text('1\n')
            self.assertTrue(self.wait_for(lambda: len(pool._processes) <= 1), len(pool._processes))
            after = rss_mib(list(pool._processes))
            # the ended workers' memory is back: at least most of HOLD_MIB for every worker that ended
            ended = len(pids) - len(pool._processes)
            self.assertGreaterEqual(before - after, ended * HOLD_MIB * 0.8, (before, after, ended))
            print('\n[measure] %d workers %d MiB -> %d workers %d MiB after the cut to 1'
                  % (len(pids), before, len(pool._processes), after))
            # the pool works on: the allowance grows back and units spread over new workers again
            self.allowance.write_text('8\n')
            again = run_map()
            self.assertEqual(sorted(i for i, _ in again), list(range(8)))
            self.assertGreaterEqual(len({pid for _, pid in again}), 4)
            self.assertFalse(pool._broken)

    def test_completed_map_workers_end(self):
        self.check_cut_frees_memory(lambda: list(build_parallel.completed_map(hold, range(8), 8)))

    def test_ordered_map_workers_end(self):
        # ordered_map is not edited (its text keys every stage): the supervisor's status starts the watcher
        self.check_cut_frees_memory(lambda: list(build_parallel.ordered_map(hold, list(range(8)), 8)))

    def test_no_watcher_outside_the_scheduler(self):
        os.environ.pop(build_parallel.ALLOWANCE_ENV)
        with build_parallel.stage_pool(4, 'test') as stage:
            got = list(build_parallel.completed_map(hold, range(4), 4))
            self.assertEqual(sorted(i for i, _ in got), list(range(4)))
            pool = stage.executor
            self.assertIsNone(getattr(pool, '_aw_idle_watch', None))


class WatcherKeysNothing(unittest.TestCase):
    """The watcher functions are scheduling units (build_cache.SCHEDULING_UNITS): removing them and their one call
    gives the same key for a stage that reaches every pool map (rule: a rebuild explained only by scheduling code is a
    hold-level builder bug)."""

    STAGE = ('from build_parallel import ordered_map, completed_map, governed_map, spread_map\n'
             'ordered_map(print, [])\ncompleted_map(print, [])\ngoverned_map(print, [])\nspread_map(print, [])\n')
    FUNCTIONS = ('_trim_after_seconds', '_trim_poll_seconds', '_watch_stage_pool', '_watch_idle_workers',
                 '_can_retire', '_trim_idle_loop', '_retire_idle', '_retire_worker')

    def key(self, root, source, top_format):
        (root / 'tools' / 'build_parallel.py').write_text(source, encoding='utf-8', newline='\n')
        index = build_cache.SourceIndex(root, scope='units', top_format=top_format)
        selected, uncertain = index.selection(root / 'tools' / 'stage.py')
        self.assertFalse(uncertain)
        return selected['tools/build_parallel.py']

    def test_without_the_watcher_the_same_key(self):
        source = (ROOT / 'tools' / 'build_parallel.py').read_text(encoding='utf-8')
        for name in self.FUNCTIONS:
            self.assertIn(('tools/build_parallel.py', name), build_cache.SCHEDULING_UNITS, name)
        start = source.index('\n# Idle workers end when a stage')
        end = source.index('\ndef governed_map(')
        older = source[:start] + '\n\n' + source[end:]
        older = older.replace('    _watch_idle_workers(pool)\n', '', 1)
        self.assertNotEqual(older, source)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'tools').mkdir()
            (root / 'tools' / 'stage.py').write_text(self.STAGE, encoding='utf-8')
            for top_format in build_cache.TOP_FORMATS:
                self.assertEqual(self.key(root, older, top_format), self.key(root, source, top_format),
                                 'top format %d' % top_format)


if __name__ == '__main__':
    unittest.main()
