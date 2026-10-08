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


def held_events(state):
    """Workers held over time: start share, allowance changes, release at the end."""
    events = []
    for s in state['steps']:
        held = s['jobs']
        events.append((s['started_seconds'], held))
        for at, value in s.get('worker_changes', []):
            events.append((at, value - held))
            held = value
        events.append((s['started_seconds'] + s['elapsed_seconds'], -held))
    return events


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
            events = held_events(state)
            by_name = {s['name']: s for s in state['steps']}
            for s in state['steps']:
                start = s['started_seconds']
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


    def test_late_stage_gets_a_fair_share_and_shares_follow_the_budget(self):
        # BUILD-SCHEDULER-JOBSHARE-32: a stage that becomes ready while another
        # holds most of the budget must not keep one worker for its whole run.
        watch = '\n'.join([
            'import json, os, sys, time',
            'from pathlib import Path',
            'seen = []; end = time.time() + {}',
            'while time.time() < end:',
            '    v = int(Path(os.environ["AMIWIND_BUILD_JOBS_FILE"]).read_text())',
            '    seen.append(v) if not seen or seen[-1] != v else None',
            '    time.sleep(.02)',
            'Path({!r}).write_text(json.dumps(seen))'])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            steps = [('engine', [sys.executable, '-c', watch.format(2.5, str(root / 'engine.json')), '--jobs', '1']),
                     ('setup', [sys.executable, '-c', 'import time; time.sleep(.4)']),
                     ('terrain', [sys.executable, '-c', watch.format(4.0, str(root / 'terrain.json')), '--jobs', '1'])]
            with contextlib.redirect_stdout(io.StringIO()):
                execute_parallel(steps, root / 'run', {'compiler_jobs': 8}, root)
            state = json.loads((root / 'run/build-state.json').read_text())
            engine = json.loads((root / 'engine.json').read_text())
            terrain = json.loads((root / 'terrain.json').read_text())
        by_name = {s['name']: s for s in state['steps']}
        self.assertEqual(by_name['engine']['jobs'], 7)
        self.assertEqual(by_name['terrain']['jobs'], 1)
        self.assertEqual(engine[:2], [7, 4])      # shrinks when terrain starts
        self.assertIn(terrain[0], (1, 4))        # starts with what was free
        self.assertIn(4, terrain)                # grows to a fair share
        self.assertEqual(terrain[-1], 8)         # and takes the freed budget
        used = peak = 0
        for _, delta in sorted(held_events(state)):
            used += delta
            peak = max(peak, used)
        self.assertLessEqual(peak, 8)


    def test_palette_readers_wait_for_the_census_rewrite(self):
        # BUILD-PALETTE-RACE-32: census rewrites intro-scene/id1/gfx/palette.lmp in
        # place; no stage may read it while census can still be running.
        import build
        from build_parallel import stage_dependencies
        args = build.parser().parse_args(['--jobs', '4', '--tree-sprites'])
        args.data_files = Path('/owned'); args.sdk = Path('/sdk')
        tools = {k: '/tools/' + k for k in ('qbsp', 'vis', 'light', 'qcc', 'ffmpeg', 'xdftool', 'rdbtool')}
        steps = build.commands(args, tools, Path('/private/run'))
        dependencies = stage_dependencies(steps)

        def ancestors(name):
            seen, todo = set(), list(dependencies[name])
            while todo:
                item = todo.pop()
                if item not in seen:
                    seen.add(item); todo.extend(dependencies[item])
            return seen
        readers = [name for name, command in steps
                   if any(str(part).endswith('intro-scene/id1/gfx/palette.lmp') for part in command)]
        self.assertIn('world-flora-assets', readers)
        for name in readers:
            if name != 'census' and 'census' not in ancestors(name):
                self.assertIn(name, ancestors('census'), name + ' may read the palette while census rewrites it')

    def test_in_place_rewrites_are_whole_files(self):
        from ui_palette import replace_bytes
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'palette.lmp'; path.write_bytes(bytes(768))
            replace_bytes(path, bytes(range(256)) * 3)
            self.assertEqual(path.read_bytes(), bytes(range(256)) * 3)
            self.assertEqual([p.name for p in Path(tmp).iterdir()], ['palette.lmp'])
        source = (Path(__file__).resolve().parents[1] / 'tools/ui_palette.py').read_text(encoding='utf-8')
        self.assertNotIn('.write_bytes(new)', source)
        self.assertNotIn('marker.write_text', source)


if __name__ == '__main__':
    unittest.main()
