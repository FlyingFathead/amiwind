"""Real worker/process tests for build ordering, limits, and failure isolation."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from build_parallel import completed_map, ordered_map, execute_parallel, THREAD_LIMITS
from build_jobs import resolve_jobs


def work(item):
    time.sleep(.02 * (3 - item % 3))
    return item * item, os.getpid(), {k: os.environ.get(k) for k in THREAD_LIMITS}


def fail(item):
    if item == 2:
        raise ValueError('worker failed')
    return item


def wait_for_later_job(task):
    number, marker = task
    marker = Path(marker)
    if number == 0:
        deadline = time.monotonic() + 10
        while not marker.exists():
            if time.monotonic() >= deadline:
                raise RuntimeError('Later job was starved behind first task')
            time.sleep(.01)
    elif number == 8:
        marker.write_text('later task ran')
    return number


class ParallelBuildTests(unittest.TestCase):
    def test_completion_queue_refills_past_blocked_first_task(self):
        # Two workers submit four initial tasks. Job 0 only unblocks after job 8,
        # which must be submitted despite job 0 still running. ordered_map would
        # stall until the timeout; merely reordering printed lines cannot pass.
        with tempfile.TemporaryDirectory() as temp:
            tasks = [(i, str(Path(temp)/'release')) for i in range(12)]
            actual = list(completed_map(wait_for_later_job, tasks, 2))
        self.assertCountEqual(actual, range(12))
        self.assertNotEqual(actual[0], 0)

    def test_completed_work_limits_workers_threads_and_stream_submission(self):
        submitted = []
        def items():
            for i in range(30):
                submitted.append(i)
                yield i
        stream = completed_map(work, items(), 3)
        first = next(stream)
        # A bounded pending window plus one completed batch, never the full list.
        self.assertLessEqual(len(submitted), 12)
        actual = [first, *stream]
        self.assertCountEqual([r[0] for r in actual], [i*i for i in range(30)])
        self.assertGreater(len({r[1] for r in actual}), 1)
        self.assertLessEqual(len({r[1] for r in actual}), 3)
        self.assertTrue(all(r[1] != os.getpid() and r[2] == THREAD_LIMITS for r in actual))
        self.assertEqual(list(completed_map(abs, [-2, -1], 1)), [2, 1])
        self.assertEqual(list(completed_map(abs, [], 2)), [])
        with self.assertRaisesRegex(ValueError, 'worker failed'):
            list(completed_map(fail, range(5), 2))

    def test_processes_keep_order_and_limit_nested_threads(self):
        result = list(ordered_map(work, range(9), 3))
        self.assertEqual([r[0] for r in result], [n*n for n in range(9)])
        self.assertGreater(len({r[1] for r in result}), 1)
        self.assertLessEqual(len({r[1] for r in result}), 3)
        self.assertTrue(all(r[1] != os.getpid() and r[2] == THREAD_LIMITS for r in result))
        self.assertEqual(list(ordered_map(abs, [-2, -1], 1)), [2, 1])
        with self.assertRaisesRegex(ValueError, 'worker failed'):
            list(ordered_map(fail, range(5), 2))

    def test_inherited_stage_budget(self):
        with patch.dict(os.environ, AMIWIND_BUILD_JOBS='2'):
            self.assertEqual(resolve_jobs(), 2)
            self.assertEqual(resolve_jobs(1), 1)
        with patch.dict(os.environ, AMIWIND_BUILD_JOBS='0'):
            with self.assertRaises(ValueError):
                resolve_jobs()

    def test_stage_overlap_dependencies_and_global_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def command(name, required=(), jobs=False):
                code = ('from pathlib import Path; import time; '
                        f'assert all(Path(x).exists() for x in {list(required)!r}); '
                        'time.sleep(.25); ' + f'Path({name!r}).write_text("done")')
                return [sys.executable, '-c', code] + (['--jobs', '99'] if jobs else [])
            steps = [('setup', command('setup')),
                     ('terrain', command('terrain', ['setup'])),
                     ('music', command('music', jobs=True)),
                     ('engine', command('engine', jobs=True)),
                     ('dry-run-image', command('image', ['engine']))]
            with contextlib.redirect_stdout(io.StringIO()):
                execute_parallel(steps, root/'run', {'compiler_jobs': 3}, root)
            state = json.loads((root/'run/build-state.json').read_text())
            self.assertEqual(state['status'], 'passed')
            events = []
            by_name = {s['name']: s for s in state['steps']}
            for s in state['steps']:
                start = s['started_seconds']
                events += [(start, s['jobs']), (start + s['elapsed_seconds'], -s['jobs'])]
                for dep in s['dependencies']:
                    before = by_name[dep]
                    self.assertGreaterEqual(start + .005, before['started_seconds'] + before['elapsed_seconds'])
            used = peak = 0
            for _, delta in sorted(events):
                used += delta
                peak = max(peak, used)
            self.assertGreater(peak, 1)
            self.assertLessEqual(peak, 3)

    def test_failure_cancels_siblings_and_blocks_dependents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            steps = [('setup', [sys.executable, '-c', 'import time; time.sleep(.1); raise SystemExit(7)']),
                     ('terrain', [sys.executable, '-c', 'raise AssertionError("must not run")']),
                     ('engine', [sys.executable, '-c', 'import time; time.sleep(30)'])]
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, 'setup failed'):
                execute_parallel(steps, root/'run', {'compiler_jobs': 2}, root)
            state = json.loads((root/'run/build-state.json').read_text())
            self.assertEqual(state['status'], 'failed')
            self.assertEqual(state['not_started'], ['terrain'])
            self.assertEqual({s['name']: s['status'] for s in state['steps']},
                             {'setup': 'failed', 'engine': 'cancelled'})


if __name__ == '__main__':
    unittest.main()
