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


def worker_allowance(item):
    """Worker: the allowance it sees and the pids of a nested one-worker map."""
    from build_parallel import ALLOWANCE_ENV, BUDGET_ENV
    nested = list(ordered_map(nested_pid, range(3), 1))
    time.sleep(.4)  # items overlap, so the stage pool starts more than one worker
    return (os.environ.get(ALLOWANCE_ENV), os.environ.get(BUDGET_ENV), os.getpid(), nested)


def nested_pid(item):
    return os.getpid()


def timed_task(item):
    start = time.monotonic()
    time.sleep(.5)
    return item, start, time.monotonic()


def peak_overlap(rows):
    events = sorted([(start, 1) for _, start, _ in rows] + [(end, -1) for _, _, end in rows])
    running = peak = 0
    for _, delta in events:
        running += delta
        peak = max(peak, running)
    return peak


def noisy(item):
    import subprocess
    print('python', item, flush=True)
    subprocess.run([sys.executable, '-c', 'print("tool %d")' % item], check=True)
    return item * 2


def captured_noisy(item):
    from build_parallel import captured
    return captured(noisy, item)


def sleep_for(item):
    name, seconds = item
    start = time.monotonic()
    time.sleep(seconds)
    return name, start


def head_of_line(item):
    # Item 0 is slow; the others are quick: with a narrow window they waited behind it.
    time.sleep(2.5 if item == 0 else .05)
    return item, time.monotonic()


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

    def test_pool_workers_do_not_follow_the_stage_allowance(self):
        # BUILD-NESTED-POOL-ALLOWANCE-33: a worker's own one-worker map must stay
        # serial; following the stage allowance made each of N workers open N more.
        with tempfile.TemporaryDirectory() as temp:
            allowance = Path(temp) / 'allowance'
            allowance.write_text('3' + chr(10))
            with patch.dict(os.environ, AMIWIND_BUILD_JOBS='1', AMIWIND_BUILD_JOBS_FILE=str(allowance),
                            AMIWIND_BUILD_BUDGET='3'):
                rows = list(ordered_map(worker_allowance, range(4), 1))
        self.assertTrue(all(row[0] is None and row[1] is None for row in rows))
        self.assertTrue(all(set(row[3]) == {row[2]} for row in rows))  # nested map ran in the worker itself
        self.assertGreater(len({row[2] for row in rows}), 1)          # the stage pool itself followed 3

    def test_pool_worker_puts_the_mwad_package_before_the_tools_launcher(self):
        # TEST-WORKER-SYSPATH-32: with tools/ ahead of src/ on the caller's path, a spawned
        # worker imported tools/mwad.py as `mwad` and died unpickling its task.
        import build_parallel
        root = Path(build_parallel.__file__).resolve().parents[1]
        src, tools = str(root / 'src'), str(root / 'tools')
        with patch.object(sys, 'path', [tools, src, *sys.path]), patch.dict(os.environ):
            build_parallel._pool_worker_init()
            resolved = [Path(entry or '.').resolve() for entry in sys.path]
            self.assertEqual(resolved[0], Path(src).resolve())
            self.assertEqual(resolved.count(Path(src).resolve()), 1)
            self.assertLess(0, resolved.index(Path(tools).resolve()))

    def test_running_pool_grows_when_its_allowance_grows(self):
        # BUILD-SCHEDULER-JOBSHARE-32: a stage that started with one worker and is
        # later left alone takes the freed workers mid-run (the NPC gallery case).
        for mapper in (ordered_map, completed_map):
            with self.subTest(mapper=mapper.__name__), tempfile.TemporaryDirectory() as temp:
                allowance = Path(temp) / 'allowance'
                allowance.write_text('1' + chr(10))
                with patch.dict(os.environ, AMIWIND_BUILD_JOBS='1', AMIWIND_BUILD_JOBS_FILE=str(allowance),
                                AMIWIND_BUILD_BUDGET='4'):
                    rows = []
                    for row in mapper(timed_task, range(24), 1):
                        rows.append(row)
                        if len(rows) == 2:
                            allowance.write_text('4' + chr(10))
                early = [r for r in rows if r[0] < 2]
                self.assertEqual(peak_overlap(early), 1)       # one worker while the allowance is 1
                self.assertGreaterEqual(peak_overlap(rows), 3)  # then the freed workers are used
                self.assertLessEqual(peak_overlap(rows), 4)     # never more than the allowance
                self.assertCountEqual([r[0] for r in rows], range(24))
                if mapper is ordered_map:
                    self.assertEqual([r[0] for r in rows], list(range(24)))

    def test_captured_output_comes_back_in_item_order(self):
        # Region workers return their own and their tools' output; the stage prints it in order.
        rows = list(ordered_map(captured_noisy, range(5), 3))
        self.assertEqual([result for result, _ in rows], [0, 2, 4, 6, 8])
        self.assertEqual([text for _, text in rows],
                         ['python %d\ntool %d\n' % (n, n) for n in range(5)])

    def test_cost_order_starts_the_longest_first_and_keeps_input_order(self):
        # BUILD-ORDERED-WINDOW-33 cost model: the long items start first, results stay in input order.
        # The dispatch order is checked, not start times on a shared host (TEST-COST-ORDER-LOAD-33).
        from concurrent.futures import ThreadPoolExecutor
        import build_parallel
        items = [('a', .05), ('b', .05), ('c', .6), ('d', .05), ('e', .4), ('f', .05)]
        submitted = []

        class Recording(ThreadPoolExecutor):
            def submit(self, function, *args):
                submitted.append(args[-1][0])
                return super().submit(function, *args)
        timings = []
        with patch.object(build_parallel, 'process_pool', side_effect=lambda count: Recording(max_workers=count)):
            rows = list(ordered_map(sleep_for, items, 2, cost=lambda item: item[1], timings=timings))
        self.assertEqual([name for name, _ in rows], list('abcdef'))
        self.assertEqual(submitted[:2], ['c', 'e'])          # longest first
        self.assertEqual(sorted(submitted), list('abcdef'))   # every item once
        self.assertEqual(len(timings), 6)
        self.assertGreater(timings[2], timings[0])          # timings follow input order
        serial = list(ordered_map(sleep_for, items, 1, cost=lambda item: item[1]))
        self.assertEqual([name for name, _ in serial], list('abcdef'))  # one worker: input order

    def test_one_slow_head_does_not_idle_the_other_workers(self):
        # BUILD-ORDERED-WINDOW-33: with two results held per worker, quick items behind
        # a slow head stopped being submitted; four keep the workers busy.
        rows = list(ordered_map(head_of_line, range(40), 4))
        self.assertEqual([item for item, _ in rows], list(range(40)))
        head_done = rows[0][1]
        finished_before = sum(1 for item, at in rows[1:] if at < head_done)
        self.assertGreater(finished_before, 8)  # more than the old window of 2 x 4 minus the head

    def test_cost_history_round_trip_and_fallback_scaling(self):
        import build_costs
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {build_costs.ENV: temp}):
            self.assertEqual(build_costs.load('pool'), {})
            self.assertIsNone(build_costs.estimator('pool', ['a', 'b']))
            build_costs.record('pool', ['a', 'b'], [2.0, 4.0])
            self.assertEqual(build_costs.load('pool'), {'a': 2.0, 'b': 4.0})
            cost = build_costs.estimator('pool', ['a', 'b', 'c'], fallback={'a': 1, 'b': 2, 'c': 10}.get)
            self.assertEqual((cost('a'), cost('b'), cost('c')), (2.0, 4.0, 20.0))  # c scaled by seconds per unit
            items = [('a', .01), ('b', .01), ('c', .01)]
            first = list(build_costs.costed_map('pool2', sleep_for, items, ['a', 'b', 'c'], 2))
            self.assertEqual([name for name, _ in first], ['a', 'b', 'c'])
            self.assertEqual(sorted(build_costs.load('pool2')), ['a', 'b', 'c'])
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(build_costs.ENV, None)
            build_costs.record('pool', ['a'], [1.0])  # no history folder: nothing written, no error
            self.assertEqual(build_costs.load('pool'), {})

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

    def test_more_ready_branches_than_the_budget_still_run(self):
        """BUILD-SCHEDULER-LOWBUDGET-33: with a budget of 2 and five ready pooled branches the scheduler
        reserved a slot for every other branch before starting any, and started none (a busy loop)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code = 'import time, sys; time.sleep(.1)'
            steps = [('setup', [sys.executable, '-c', code])] + [
                (name, [sys.executable, '-c', code, '--jobs', '4']) for name in ('music', 'engine', 'media',
                                                                                  'world-survey', 'dialogue-lookup')]
            with contextlib.redirect_stdout(io.StringIO()):
                execute_parallel(steps, root / 'run', {'compiler_jobs': 2}, root)
            state = json.loads((root / 'run/build-state.json').read_text())
            self.assertEqual(state['status'], 'passed')
            self.assertEqual(len(state['steps']), 6)
            used = peak = 0
            for _, delta in sorted(held_events(state)):
                used += delta
                peak = max(peak, used)
            self.assertLessEqual(peak, 2)
            # one stage per free worker: two branches overlap (not one at a time)
            starts = sorted((st['started_seconds'], st['started_seconds'] + st['elapsed_seconds'])
                            for st in state['steps'] if st['name'] != 'setup')
            self.assertTrue(any(b[0] < a[1] for a, b in zip(starts, starts[1:])), starts)

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
        # BUILD-STAGE-START-SHARE-33: terrain starts with its fair share, not
        # the one worker that was free (its tool threads keep the start value).
        self.assertEqual(by_name['terrain']['jobs'], 4)
        self.assertEqual(engine[:2], [7, 4])      # shrinks when terrain starts
        self.assertEqual(terrain[0], 4)          # starts with a fair share
        self.assertEqual(terrain[-1], 8)         # and takes the freed budget
        shrink = next(at for at, value in by_name['engine']['worker_changes'] if value == 4)
        self.assertLessEqual(shrink, by_name['terrain']['started_seconds'])  # shrink first, then start
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
