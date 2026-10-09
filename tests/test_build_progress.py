"""Live build progress and ETA (build-progress.json, build.py status) and the profiler's compare/optimize commands."""
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build  # noqa: E402
import build_profile  # noqa: E402
import build_progress  # noqa: E402
from build_parallel import execute_parallel  # noqa: E402

LINUX = build_profile.linux_proc()


def write_profile(run, rows, budget=8, wall=None, timeline=None):
    """A build-profile.json with rows (name, wall, cpu, jobs[, deps])."""
    stages, clock = [], 0.0
    for number, row in enumerate(rows, 1):
        name, seconds, cpu, jobs = row[:4]
        deps = list(row[4]) if len(row) > 4 else []
        stages.append({'name': name, 'number': number, 'status': 'passed', 'jobs': jobs, 'dependencies': deps,
                       'start': clock, 'end': clock + seconds, 'wall': seconds, 'cpu': cpu,
                       'cores_avg': round(cpu / seconds, 2)})
        clock += seconds
    profile = {'schema': build_profile.SCHEMA, 'run': str(run), 'status': 'passed', 'wall_seconds': wall or clock,
               'budget': budget, 'counters': 'linux-proc', 'overhead': {}, 'stages': stages,
               'timeline': timeline}
    Path(run).mkdir(parents=True, exist_ok=True)
    (Path(run) / build_profile.PROFILE_NAME).write_text(json.dumps(profile))
    return profile


class ExpectedDurationTests(unittest.TestCase):
    def test_scaling_follows_the_parallel_share(self):
        # Same budget: unchanged. A serial stage never scales.
        self.assertEqual(build_progress.scaled_seconds(100, 400, 8, 8, 8), 100)
        self.assertEqual(build_progress.scaled_seconds(100, 100, 1, 8, 16), 100)
        self.assertEqual(build_progress.scaled_seconds(100, None, 8, 8, 16), 100)
        # Perfectly parallel on 8 workers: twice the budget halves it, half doubles it.
        self.assertAlmostEqual(build_progress.scaled_seconds(100, 800, 8, 8, 16), 50.0, places=3)
        self.assertAlmostEqual(build_progress.scaled_seconds(100, 800, 8, 8, 4), 200.0, places=3)
        # Half parallel (Amdahl): 4 cores on 8 workers -> share 6/7; 16 workers: 100 * (1/7 + 6/7/2) / (1/7 + 6/7/8)
        share = build_progress.amdahl_share(4, 8)
        self.assertAlmostEqual(share, 6 / 7, places=6)
        serial = 100 / ((1 - share) + share / 8)
        self.assertAlmostEqual(build_progress.scaled_seconds(100, 400, 8, 8, 16), serial * ((1 - share) + share / 16), places=3)
        # A stage that got more workers later (the scheduler rebalances) scales from what it used.
        self.assertLess(build_progress.scaled_seconds(100, 400, 1, 8, 16), 100)
        self.assertEqual(build_progress.amdahl_share(1.0, 8), 0.0)
        self.assertEqual(build_progress.amdahl_share(12.0, 8), 1.0)

    def test_history_from_sibling_runs_defaults_and_no_history(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            write_profile(workspace / 'a', [('scene', 100, 100, 1), ('image', 200, 1600, 8)])
            write_profile(workspace / 'b', [('scene', 120, 120, 1), ('image', 300, 2400, 8)])
            write_profile(workspace / 'c', [('scene', 110, 110, 1), ('image', 250, 2000, 8)])
            current = workspace / 'now'
            current.mkdir()
            (current / build_profile.PROFILE_NAME).write_text('{"stages": [{"name": "scene", "wall": 9999}]}')
            samples, runs = build_progress.history_samples(current)
            self.assertEqual(sorted(runs), ['a', 'b', 'c'])  # never the run itself
            defaults = (24, {'music': {'wall': 30, 'cpu': 30, 'jobs': 1}})
            expected = build_progress.expected_durations(['scene', 'image', 'music', 'town-new', 'engine'], 16, samples,
                                                         defaults, reused={'engine'})
            self.assertEqual(expected['scene'], {'seconds': 110.0, 'cores': 1.0, 'source': 'history', 'samples': 3})
            self.assertEqual(expected['image']['seconds'], 125.0)  # median 250 s on 8, perfectly parallel, now 16
            self.assertEqual(expected['music']['source'], 'default')
            self.assertEqual(expected['music']['seconds'], 30.0)
            self.assertEqual(expected['town-new'], {'seconds': None, 'cores': None, 'source': 'none', 'samples': 0})
            self.assertEqual(expected['engine']['source'], 'reused')

    def test_shipped_default_table_covers_the_default_build(self):
        budget, stages = build_progress.load_defaults()
        self.assertGreater(budget, 0)
        for name in ('setup', 'scene', 'npc-gallery', 'world-terrain', 'world-flora', 'image', 'engine'):
            self.assertIn(name, stages)
            self.assertGreater(stages[name]['wall'], 0)
        text = build_progress.DEFAULTS.read_text(encoding='utf-8')
        self.assertNotIn('\r', text)
        self.assertNotRegex(text, r'[A-Za-z]:[\\/]|/home/|/vol/')


class EstimateTests(unittest.TestCase):
    ORDER = ['a', 'b', 'c', 'd']
    DEPS = {'a': [], 'b': ['a'], 'c': ['a'], 'd': ['b', 'c']}

    def expected(self, **seconds):
        return {name: {'seconds': value, 'cores': 1.0, 'source': 'history' if value else 'none'}
                for name, value in seconds.items()}

    def test_weighting_eta_and_critical_path(self):
        expected = self.expected(a=100, b=300, c=100, d=100)
        # Nothing started: 0 %, ETA = longest chain a > b > d.
        start = build_progress.estimate(self.ORDER, self.DEPS, {}, expected, budget=8)
        self.assertEqual(start['percent'], 0.0)
        self.assertEqual(start['eta_seconds'], 500.0)
        self.assertEqual(start['critical_path'], ['a', 'b', 'd'])
        self.assertEqual(start['eta_basis'], 'critical path')
        # a done, b 150 s into 300, c done: weights 100+150+100 of 600.
        stages = {'a': {'status': 'passed', 'elapsed': 90}, 'b': {'status': 'running', 'elapsed': 150},
                  'c': {'status': 'passed', 'elapsed': 100}}
        middle = build_progress.estimate(self.ORDER, self.DEPS, stages, expected, budget=8)
        self.assertEqual(middle['percent'], round(100 * 350 / 600, 1))
        self.assertEqual(middle['eta_seconds'], 250.0)  # 150 left of b, then d
        self.assertEqual(middle['critical_path'], ['b', 'd'])
        # Finished: 100 %, ETA 0.
        done = {name: {'status': 'passed', 'elapsed': 1} for name in self.ORDER}
        final = build_progress.estimate(self.ORDER, self.DEPS, done, expected, budget=8)
        self.assertEqual((final['percent'], final['eta_seconds'], final['critical_path']), (100.0, 0.0, []))

    def test_overrun_unknown_stages_cpu_bound_and_failure(self):
        expected = self.expected(a=100, b=None, c=100, d=100)
        stages = {'a': {'status': 'running', 'elapsed': 300}}
        result = build_progress.estimate(self.ORDER, self.DEPS, stages, expected, budget=8)
        # a overran: counted 95 %, 10 % of its elapsed time more assumed; b weighs the median of known stages.
        self.assertEqual(result['overrun'], ['a'])
        self.assertEqual(result['remaining']['a'], 30.0)
        self.assertEqual(result['no_history'], ['b'])
        self.assertEqual(result['fallback_seconds'], 100.0)
        self.assertEqual(result['percent'], round(100 * 95 / 400, 1))
        self.assertEqual(result['eta_seconds'], 230.0)
        # Many parallel stages on a small budget: the CPU work, not the chain, sets the ETA.
        wide = ['s%d' % i for i in range(8)]
        expected = {name: {'seconds': 100, 'cores': 4.0, 'source': 'history'} for name in wide}
        result = build_progress.estimate(wide, {name: [] for name in wide}, {}, expected, budget=4)
        self.assertEqual((result['eta_seconds'], result['eta_basis']), (800.0, 'CPU budget'))
        # A failed stage: no ETA.
        stopped = build_progress.estimate(self.ORDER, self.DEPS, {'a': {'status': 'failed', 'elapsed': 5}},
                                          self.expected(a=100, b=100, c=100, d=100), budget=8)
        self.assertIsNone(stopped['eta_seconds'])

    def test_idle_core_warning_needs_more_than_a_minute(self):
        busy_then_idle = [(float(t), 7.0) for t in range(100)] + [(float(t), 1.0) for t in range(100, 170)]
        self.assertEqual(build_progress.trailing_idle(busy_then_idle, 4.0), 70.0)
        self.assertEqual(build_progress.trailing_idle(busy_then_idle[:150], 4.0), 50.0)
        self.assertEqual(build_progress.trailing_idle([(0.0, 6.0), (1.0, 6.0)], 4.0), 0.0)
        self.assertEqual(build_progress.trailing_idle([], 4.0), 0.0)

    def test_tracker_flags_idle_running_stage_and_whole_build(self):
        class FakeSampler:
            interval = 1.0

            def __init__(self):
                import threading
                self.lock = threading.Lock()
                self.times = [float(t) for t in range(120)]
                self.total = [1.0] * 120
                self.stages = {'image': [[i, 1.0, 0, 1] for i in range(120)]}

            def timeline(self):
                return {'t': self.times, 'cores': self.total, 'cgroup_cores': None, 'host_cpus': 8,
                        'host_busy': [0.2] * 120, 'interval': 1.0, 'stages': {}}
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'run'
            run.mkdir()
            origin = time.monotonic() - 120
            tracker = build_progress.Tracker(run, ['image'], {'image': []}, {'compiler_jobs': 8}, FakeSampler(),
                                             origin=origin, interval=3600)
            tracker.stage_started('image', 1, 8)
            with tracker.lock:
                tracker.stages['image']['start'] = 0.0
            tracker.write()
            progress = json.loads((run / build_progress.PROGRESS_NAME).read_text())
            self.assertEqual(progress['idle_warnings'][0]['stage'], 'image')
            self.assertEqual(progress['idle_warnings'][0]['jobs'], 8)
            self.assertGreater(progress['idle_warnings'][0]['seconds'], 60)
            self.assertEqual(progress['build_idle']['jobs'], 8)
            self.assertEqual(progress['stages'][0]['cores_now'], 1.0)
            self.assertEqual(progress['host']['cpus'], 8)
            tracker.close('passed')
            final = json.loads((run / build_progress.PROGRESS_NAME).read_text())
            self.assertEqual(final['status'], 'passed')
            self.assertIsNone(final['build_idle'])

    def test_tracker_never_raises(self):
        with tempfile.TemporaryDirectory() as temp:
            tracker = build_progress.Tracker(Path(temp) / 'missing', ['x'], {}, {}, interval=3600)
            tracker.stage_started('x', 1, 1)
            tracker.stage_finished('x', 'passed')
            tracker.stage_finished('unknown', 'passed')
            tracker.close('passed')
            self.assertFalse((Path(temp) / 'missing').exists())


FIXTURE = {
    'schema': build_progress.SCHEMA, 'run': 'dev-7', 'status': 'running', 'started_at': '2026-10-08T20:00:00+03:00',
    'updated_at': '2026-10-08T20:23:10+03:00', 'updated_epoch': 0, 'interval': 10.0, 'elapsed_seconds': 1390.0,
    'budget': 24, 'percent': 47.3, 'eta_seconds': 1540.0, 'eta_basis': 'critical path',
    'eta_at': '2026-10-08T20:48:50+03:00', 'critical_path': ['world-terrain', 'world-scenery', 'image'],
    'critical_path_seconds': 1540.0, 'counts': {'passed': 20, 'running': 2, 'pending': 12, 'failed': 0, 'total': 34},
    'stages': [
        {'name': 'world-terrain', 'status': 'running', 'elapsed_seconds': 723.0, 'expected_seconds': 780.0,
         'expected_source': 'history', 'jobs': 20, 'cores_now': 14.2, 'idle_seconds': 0.0, 'overrun': False},
        {'name': 'town-new', 'status': 'running', 'elapsed_seconds': 130.0, 'expected_seconds': None,
         'expected_source': 'none', 'jobs': 4, 'cores_now': 1.0, 'idle_seconds': 125.0, 'overrun': False},
        {'name': 'image', 'status': 'pending', 'expected_seconds': 1200.0, 'expected_source': 'default'}],
    'idle_warnings': [{'stage': 'town-new', 'cores': 1.0, 'jobs': 4, 'seconds': 125.0}], 'build_idle': None,
    'host': {'cpus': 24, 'busy_percent': 71.0, 'build_cores': 15.2, 'other_percent': 7.7, 'samples': 10,
             'host_busy': False},
    'no_history': ['town-new'], 'fallback_seconds': 120.0, 'history': {'runs': ['dev-6', 'dev-5'], 'defaults': True}}


class StatusTests(unittest.TestCase):
    def status(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = build.main(['status', *map(str, args)])
        return code, output.getvalue()

    def test_status_screen_and_json_on_a_fixture_run(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'dev-7'
            run.mkdir()
            record = dict(FIXTURE, updated_epoch=time.time() - 4)
            (run / build_progress.PROGRESS_NAME).write_text(json.dumps(record))
            code, text = self.status(run)
            self.assertEqual(code, 0)
            lines = text.splitlines()
            self.assertTrue(lines[0].startswith('Build dev-7: running, 47.3 %, elapsed 23m10s, ETA 25m40s (at 20:48:50'))
            self.assertIn('Stages: 20 done, 2 running, 12 pending, 0 failed/cancelled (of 34)', text)
            self.assertRegex(text, r'world-terrain\s+12m03s\s+~13m00s\s+14\.2\s+20')
            self.assertRegex(text, r'town-new\s+2m10s\s+no history\s+1\.0\s+4\s+no history, idle 2m05s')
            self.assertIn('ETA waits on (25m40s): world-terrain > world-scenery > image', text)
            self.assertIn('[idle] town-new: 1.0 of 4 cores for 2m05s', text)
            self.assertIn('Host: 24 CPUs, 71.0 % busy, this build 15.2 cores, other work 7.7 %', text)
            self.assertIn('Expected durations from 2 earlier run(s) + the default table', text)
            self.assertNotIn('STALE', text)
            self.assertLess(len(lines), 25)  # one screen
            code, text = self.status(run, '--json')
            data = json.loads(text)
            self.assertEqual((data['percent'], data['stale_seconds']), (47.3, None))
            # A running build that stopped writing is stale.
            (run / build_progress.PROGRESS_NAME).write_text(json.dumps(dict(FIXTURE, updated_epoch=time.time() - 600)))
            self.assertIn('STALE: no update for 10m', self.status(run)[1])

    def test_status_without_progress_file_reads_build_state(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'old'
            run.mkdir()
            (run / 'build-state.json').write_text(json.dumps({'status': 'failed', 'steps': [
                {'name': 'setup', 'status': 'passed', 'elapsed_seconds': 1.0},
                {'name': 'scene', 'status': 'failed', 'elapsed_seconds': 5.0}], 'not_started': ['image']}))
            code, text = self.status(run)
            self.assertEqual(code, 0)
            self.assertIn('Build old: failed', text)
            self.assertIn('1 done, 0 running, 1 pending, 1 failed/cancelled (of 3)', text)
            self.assertIn('Failed/cancelled: scene', text)
            self.assertIn('no build-progress.json', text)
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                build.main(['status', str(Path(temp) / 'nothing')])


class BuilderProgressTests(unittest.TestCase):
    def test_parallel_and_serial_builders_write_progress_and_keep_outputs(self):
        for parallel in (True, False):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                write_profile(root / 'earlier', [('first', 0.5, 0.5, 1), ('second', 0.5, 0.5, 1)], budget=2)
                out = root / 'outputs'
                steps = [('first', [sys.executable, '-c', f"open({str(out / 'a.txt')!r}, 'w').write('a')"]),
                         ('second', [sys.executable, '-c', f"import time; time.sleep(.4); open({str(out / 'b.txt')!r}, 'w').write('b')"])]
                out.mkdir()
                run = root / 'now'
                with patch.dict(os.environ, {build_progress.INTERVAL_ENV: '0.1'}), \
                        contextlib.redirect_stdout(io.StringIO()):
                    if parallel:
                        execute_parallel(steps, run, {'compiler_jobs': 2}, root)
                    else:
                        build.execute(steps, run, {})
                progress = json.loads((run / build_progress.PROGRESS_NAME).read_text())
                self.assertEqual(progress['schema'], build_progress.SCHEMA)
                self.assertEqual(progress['status'], 'passed')
                self.assertEqual(progress['percent'], 100.0)
                self.assertEqual(progress['eta_seconds'], 0.0)
                self.assertEqual([row['status'] for row in progress['stages']], ['passed', 'passed'])
                self.assertEqual(progress['history']['runs'], ['earlier'])
                self.assertEqual([row['expected_source'] for row in progress['stages']], ['history', 'history'])
                self.assertGreaterEqual(progress['writes'], 4)  # start, two stage starts and ends, close
                self.assertEqual((out / 'a.txt').read_text() + (out / 'b.txt').read_text(), 'ab')
                self.assertFalse((run / (build_progress.PROGRESS_NAME + '.tmp')).exists())
                self.assertEqual((run / build_progress.PROGRESS_NAME).read_bytes().count(b'\r'), 0)

    def test_no_profile_writes_no_progress(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'run'
            with contextlib.redirect_stdout(io.StringIO()):
                build.execute([('only', [sys.executable, '-c', 'pass'])], run, {'profile': False})
            self.assertFalse((run / build_progress.PROGRESS_NAME).exists())


class ProfileCommandTests(unittest.TestCase):
    def run_cli(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = build.main(['profile', *map(str, args)])
        return code, output.getvalue()

    def test_report_and_compare_through_build_py(self):
        with tempfile.TemporaryDirectory() as temp:
            write_profile(Path(temp) / 'old', [('setup', 10, 10, 1), ('image', 200, 800, 8, ['setup'])])
            write_profile(Path(temp) / 'new', [('setup', 10, 10, 1), ('image', 260, 800, 8, ['setup'])])
            code, text = self.run_cli('report', Path(temp) / 'new')
            self.assertEqual(code, 0)
            self.assertIn('Critical path', text)
            code, text = self.run_cli('compare', Path(temp) / 'new', Path(temp) / 'old', '--fail-on-regression')
            self.assertEqual(code, 3)
            self.assertTrue(text.startswith('Compared with '))
            self.assertIn('REGRESSION: slower stages: image', text)
            code, text = self.run_cli('compare', Path(temp) / 'old', Path(temp) / 'old', '--json')
            self.assertEqual((code, json.loads(text)['regressions']), (0, []))

    def test_optimize_lists_idle_stages_tails_serial_stages_and_slot_waits(self):
        times = [float(i) for i in range(400)]
        timeline = {'interval': 1.0, 't': times, 'cores': [1.0] * 400, 'stages': {
            # 'scan': 150 s at one core of 8 (idle); 'pack': 8 cores, then a 90 s tail on one core.
            'scan': [[i, 1.0] for i in range(0, 150)],
            'pack': [[i, 7.8] for i in range(150, 250)] + [[i, 1.0] for i in range(250, 340)],
            'quick': [[i, 7.9] for i in range(340, 400)]}}
        with tempfile.TemporaryDirectory() as temp:
            first = write_profile(Path(temp) / 'one', [('scan', 150, 150, 8), ('pack', 190, 870, 8, ['scan']),
                                                       ('quick', 60, 474, 8, ['pack']), ('link', 90, 90, 1, ['quick'])],
                                  timeline=timeline, wall=700)
            write_profile(Path(temp) / 'two', [('scan', 150, 150, 8)], timeline={
                'interval': 1.0, 't': times[:150], 'cores': [1.0] * 150, 'stages': {'scan': [[i, 1.0] for i in range(150)]}})
            items = {(item['stage'], item['kind']): item for item in build_profile.optimize(first)}
            self.assertEqual(set(items), {('scan', 'idle'), ('pack', 'tail'), ('link', 'serial-critical'),
                                          ('(whole build)', 'slot-wait')})
            self.assertEqual(items['scan', 'idle']['seconds'], 150.0)
            self.assertEqual(items['scan', 'idle']['potential_seconds'], round(150 * (1 - 1 / 8), 1))
            self.assertEqual(items['pack', 'tail']['seconds'], 90.0)
            self.assertEqual(items['pack', 'tail']['peak_cores_before'], 7.8)
            self.assertIn('largest items first', items['pack', 'tail']['suggestion'])
            self.assertIn('critical path', items['link', 'serial-critical']['suggestion'])
            self.assertEqual(items['(whole build)', 'slot-wait']['seconds'], 210.0)
            code, text = self.run_cli('optimize', Path(temp) / 'one', Path(temp) / 'two')
            self.assertEqual(code, 0)
            self.assertIn('Optimizer: 2 run(s): one, two', text)
            self.assertRegex(text, r'scan\s+idle\s+2/2\s+2m30s\s+1\.0/8')
            self.assertRegex(text, r'pack\s+tail\s+1/2\s+1m30s')
            self.assertNotRegex(text, r'quick\s')  # busy stages are not listed
            code, text = self.run_cli('optimize', Path(temp) / 'two', '--json')
            self.assertEqual([(row['stage'], row['kind']) for row in json.loads(text)['items']], [('scan', 'idle')])

    def test_optimize_on_a_clean_run_and_short_tails(self):
        self.assertIsNone(build_profile.single_core_tail(
            {'name': 's', 'wall': 100}, {'interval': 1.0, 't': [float(i) for i in range(100)],
                                         'stages': {'s': [[i, 6.0] for i in range(80)] + [[i, 1.0] for i in range(80, 100)]}}))
        self.assertIsNone(build_profile.single_core_tail(  # never parallel: an idle stage, not a tail
            {'name': 's', 'wall': 100}, {'interval': 1.0, 't': [float(i) for i in range(100)],
                                         'stages': {'s': [[i, 1.0] for i in range(100)]}}))
        self.assertEqual(build_profile.optimize_lines([], ['clean'])[-1],
                         'Nothing to optimize: no idle cores, tails or slot waits found.')


if __name__ == '__main__':
    unittest.main()


class WorkerAllowanceTests(unittest.TestCase):
    """BUILD-PROFILE-JOBS-START-ONLY-33: cores are compared with the workers a stage held over time,
    not with the value it started with. Numbers from the v0.0.32 from-scratch build: balmora started
    with 1 worker and held 12 from 0.13 s on, using 2.84 cores for 510 s; actor-contact 1 -> 12,
    1.39 cores for 256 s; dialogue-lookup 1 worker throughout, 0.56 cores."""

    BALMORA = {'name': 'balmora', 'number': 15, 'status': 'passed', 'jobs': 1, 'dependencies': [],
               'start': 589.87, 'end': 1099.9, 'wall': 510.03, 'cpu': 1448.9, 'cores_avg': 2.84,
               'worker_changes': [[590.0, 12]]}
    ACTOR = {'name': 'actor-contact', 'number': 30, 'status': 'passed', 'jobs': 1, 'dependencies': ['balmora'],
             'start': 1823.65, 'end': 2079.64, 'wall': 255.99, 'cpu': 356.6, 'cores_avg': 1.39,
             'worker_changes': [[1823.88, 12]]}
    LOOKUP = {'name': 'dialogue-lookup', 'number': 2, 'status': 'passed', 'jobs': 1, 'dependencies': [],
              'start': 0.0, 'end': 7.9, 'wall': 7.9, 'cpu': 4.4, 'cores_avg': 0.56}

    def test_allowance_summary_and_the_old_blind_spot(self):
        self.assertEqual(build_profile.allowance_summary(self.BALMORA), (1, 12, 12.0))
        media = {'start': 0.0, 'end': 100.0, 'jobs': 4, 'worker_changes': [[50.0, 12], [75.0, 23]]}
        self.assertEqual(build_profile.allowance_summary(media), (4, 23, round((4 * 50 + 12 * 25 + 23 * 25) / 100, 2)))
        self.assertEqual(build_profile.allowance_at(build_profile.allowance_steps(media), 60.0), 12)
        self.assertEqual(build_profile.jobs_text(dict(self.BALMORA, jobs_min=1, jobs_max=12)), '1-12')
        self.assertEqual(build_profile.jobs_text(self.LOOKUP), '1')
        # The start value alone (the old rule) never flags these stages.
        old = {key: value for key, value in self.BALMORA.items() if key != 'worker_changes'}
        self.assertIsNone(build_profile.idle_periods(old, None))

    def test_idle_warning_against_the_allowance_average_and_timeline(self):
        idle = build_profile.idle_periods(self.BALMORA, None)
        self.assertEqual((idle['jobs'], idle['jobs_start'], idle['cores_while_idle'], idle['source']),
                         (12, 1, 2.84, 'average'))
        self.assertIsNone(build_profile.idle_periods(self.LOOKUP, None))
        start = self.ACTOR['start']
        times = [round(start + i, 3) for i in range(257)]
        timeline = {'interval': 1.0, 't': times, 'stages': {'actor-contact': [[i, 1.39] for i in range(257)]}}
        idle = build_profile.idle_periods(self.ACTOR, timeline)
        self.assertEqual((idle['jobs'], idle['jobs_start'], idle['source']), (12, 1, 'timeline'))
        self.assertGreater(idle['seconds'], 250)
        # Before the rebalance (one worker) 1.39 cores is not idle.
        early = dict(self.ACTOR, worker_changes=[[start + 200, 12]])
        self.assertIsNone(build_profile.idle_periods(early, timeline))  # 56 s at 12 workers: under a minute

    def test_report_and_optimize_use_the_allowance(self):
        with tempfile.TemporaryDirectory() as temp:
            stages = []
            for row in (self.LOOKUP, self.BALMORA, self.ACTOR):
                row = dict(row)
                row['jobs_min'], row['jobs_max'], row['jobs_mean'] = build_profile.allowance_summary(row)
                stages.append(row)
            profile = {'schema': build_profile.SCHEMA, 'run': str(Path(temp) / 'rel'), 'status': 'passed',
                       'wall_seconds': 2080.0, 'budget': 24, 'counters': 'linux-proc', 'overhead': {},
                       'stages': stages, 'timeline': None}
            (Path(temp) / 'rel').mkdir()
            (Path(temp) / 'rel' / build_profile.PROFILE_NAME).write_text(json.dumps(profile))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                build.main(['profile', 'report', str(Path(temp) / 'rel')])
            text = output.getvalue()
            self.assertRegex(text, r'balmora\s.*\s1-12\s')
            self.assertIn('balmora: 2.84 of 12 cores', text)
            self.assertIn('actor-contact: 1.39 of 12 cores', text)
            items = {(item['stage'], item['kind']): item for item in build_profile.optimize(profile)}
            self.assertEqual(items['balmora', 'idle']['jobs'], 12)
            self.assertEqual(items['balmora', 'idle']['jobs_start'], 1)
            self.assertNotIn(('dialogue-lookup', 'idle'), items)
            # Scaling history from the workers really held: balmora on 12 of 24, now on 48.
            seconds = build_progress.scaled_seconds(510.03, 1448.9, 12, 24, 48)
            self.assertLess(seconds, 510.03)

    @unittest.skipUnless(LINUX, 'profile counters need Linux /proc')
    def test_scheduler_rebalances_reach_the_profile_and_build_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            # media and music have no dependencies: they start together and share the budget.
            steps = [('music', [sys.executable, '-c', 'import time; time.sleep(.3)', '--jobs', '1']),
                     ('media', [sys.executable, '-c', 'import time; time.sleep(1.5)', '--jobs', '1'])]
            with contextlib.redirect_stdout(io.StringIO()):
                execute_parallel(steps, root / 'run', {'compiler_jobs': 4}, root)
            profile = json.loads((root / 'run' / build_profile.PROFILE_NAME).read_text())
            long_row = next(row for row in profile['stages'] if row['name'] == 'media')
            self.assertEqual(long_row['jobs'], 2)          # started with half the budget
            self.assertEqual(long_row['jobs_max'], 4)      # got all of it once 'music' ended
            self.assertGreater(long_row['jobs_mean'], 2)
            self.assertLessEqual(long_row['worker_changes'][0][0], long_row['end'])
            self.assertGreaterEqual(long_row['worker_changes'][0][0], long_row['start'])
            state = json.loads((root / 'run' / 'build-state.json').read_text())
            entry = next(step for step in state['steps'] if step['name'] == 'media')
            self.assertEqual(entry['profile']['jobs_max'], 4)
