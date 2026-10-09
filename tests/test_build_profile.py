"""Build profiler: measured CPU/wall, overhead, critical path, idle warnings, reports, no output change."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build  # noqa: E402
import build_profile  # noqa: E402
from build_parallel import execute_parallel  # noqa: E402

LINUX = build_profile.linux_proc()

# A stage that starts N processes, each burning SECONDS of CPU, and waits for them.
BURN = '''
import json, os, resource, subprocess, sys, time
began = time.monotonic()
n, seconds = int(sys.argv[1]), float(sys.argv[2])
code = "import time\\nend = time.process_time() + %r\\nwhile time.process_time() < end: pass" % seconds
children = [subprocess.Popen([sys.executable, "-c", code]) for _ in range(n)]
assert all(child.wait() == 0 for child in children)
report = os.environ.get('AMIWIND_TEST_BURN_REPORT')
if report:
    own, waited = resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)
    with open(report, "w") as out:
        json.dump({"cpu": own.ru_utime + own.ru_stime + waited.ru_utime + waited.ru_stime,
                   "span": time.monotonic() - began}, out)
print("burned", n, seconds)
'''
# Where a burn stage writes its own CPU (itself plus its waited-for children, from getrusage)
# and the wall span it saw: an independent reading to compare the profiler with.
BURN_REPORT_ENV = 'AMIWIND_TEST_BURN_REPORT'


def burn_stage(n, seconds):
    return [sys.executable, '-c', BURN, str(n), str(seconds)]


def stage(name, start, wall, deps=(), jobs=1, cpu=None, **extra):
    row = {'name': name, 'number': 0, 'status': 'passed', 'jobs': jobs, 'dependencies': list(deps),
           'start': start, 'end': start + wall, 'wall': wall, **extra}
    if cpu is not None:
        row.update(cpu=cpu, cores_avg=round(cpu / wall, 2))
    return row


def fixture_profile(run, walls, wall_seconds=None, fingerprints=None):
    stages, clock = [], 0.0
    previous = ()
    for number, (name, wall) in enumerate(walls.items(), 1):
        row = stage(name, clock, wall, previous, jobs=4, cpu=wall * 2)
        row['number'] = number
        if fingerprints:
            row['fingerprint'] = fingerprints[name]
        stages.append(row)
        clock += wall
        previous = (name,)
    profile = {'schema': build_profile.SCHEMA, 'run': str(run), 'status': 'passed', 'wall_seconds': wall_seconds or clock,
               'budget': 4, 'counters': 'linux-proc', 'overhead': {}, 'stages': stages,
               'timeline': {'interval': 1.0, 't': [0.0, 1.0], 'cores': [2.0, 2.0], 'cgroup_cores': None,
                            'memory_bytes': None, 'stages': {}}}
    profile['analysis'] = build_profile.analyse(profile)
    Path(run).mkdir(parents=True, exist_ok=True)
    (Path(run) / build_profile.PROFILE_NAME).write_text(json.dumps(profile))
    return profile


@unittest.skipUnless(LINUX, 'process counters need Linux /proc')
class MeasuredStageTests(unittest.TestCase):
    def test_cpu_and_wall_of_a_stage_and_all_its_children(self):
        # TEST-PROFILE-STAGE-WALL-32: how much the three children overlap is the host's
        # business (a busy host runs them partly one after another, so wall can exceed CPU).
        # The profiler is checked against independent readings of the same stage instead:
        # its CPU against the stage's own getrusage (itself plus its waited-for children),
        # its wall against the span the stage saw and the time around the run.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = root / 'burn.json'
            with patch.dict(os.environ, {build_profile.INTERVAL_ENV: '0.05', BURN_REPORT_ENV: str(report)}):
                steps = [('media', burn_stage(3, 0.6)), ('music', [sys.executable, '-c', 'import time; time.sleep(.3)'])]
                began = time.monotonic()
                with contextlib.redirect_stdout(io.StringIO()):
                    execute_parallel(steps, root / 'run', {'compiler_jobs': 4}, root)
                elapsed = time.monotonic() - began
            seen = json.loads(report.read_text())
            profile = json.loads((root / 'run' / build_profile.PROFILE_NAME).read_text())
            burn = next(row for row in profile['stages'] if row['name'] == 'media')
            idle = next(row for row in profile['stages'] if row['name'] == 'music')
            # Three children at 0.6 s each plus four interpreter start-ups, all counted.
            self.assertGreater(burn['cpu'], 1.7)
            self.assertLess(burn['cpu'], 2.8)
            self.assertAlmostEqual(burn['cpu'], seen['cpu'], delta=0.1)
            self.assertAlmostEqual(burn['cpu'], burn['cpu_user'] + burn['cpu_system'], places=2)
            # Wall covers the stage's own span and lies within the run; no host-load bound.
            self.assertGreaterEqual(burn['wall'], seen['span'] - 0.01)
            self.assertGreaterEqual(burn['wall'], 0.6)
            self.assertLessEqual(burn['wall'], elapsed + 0.01)
            self.assertAlmostEqual(burn['cores_avg'], burn['cpu'] / burn['wall'], delta=0.006)
            self.assertGreater(burn['peak_process_rss_bytes'], 1024 * 1024)
            self.assertLess(idle['cpu'], 0.3)
            self.assertGreaterEqual(idle['wall'], 0.3)
            # The sampled timeline follows the whole process tree: summed over the samples it
            # sees most of the children's CPU, far more than the waiting stage process uses,
            # and sees it while the children run: a sampler blind to live children sees their
            # CPU only in one jump, when the stage process reaps them.
            timeline = profile['timeline']
            self.assertGreater(len(timeline['t']), 5)
            times = timeline['t']
            seconds = [cores * (times[i] - times[i - 1]) for i, cores in timeline['stages']['media'] if i > 0]
            self.assertGreater(sum(seconds), 1.0)
            # Samples are rounded cores over jittered intervals: allow 0.2 s over the exact CPU
            # (TEST-PROFILE-TIMELINE-BOUND-33: 0.1 failed by 0.00006 s on a busy host).
            self.assertLess(sum(seconds), burn['cpu'] + 0.2)
            self.assertLess(max(seconds), 0.5 * sum(seconds))
            self.assertGreater(burn['peak_tree_rss_bytes'], 3 * 1024 * 1024)
            state = json.loads((root / 'run' / 'build-state.json').read_text())
            entry = next(step for step in state['steps'] if step['name'] == 'media')
            self.assertEqual(entry['command'], burn_stage(3, 0.6))  # the recorded command is the stage's own
            self.assertAlmostEqual(entry['profile']['cpu_seconds'], burn['cpu'], places=3)

    def test_serial_builder_profiles_too(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'run'
            with contextlib.redirect_stdout(io.StringIO()):
                build.execute([('first', burn_stage(2, 0.3)), ('second', burn_stage(1, 0.2))], run, {})
            profile = json.loads((run / build_profile.PROFILE_NAME).read_text())
            first, second = profile['stages']
            self.assertGreater(first['cpu'], 0.55)
            self.assertGreater(second['cpu'], 0.18)
            self.assertGreaterEqual(second['start'], first['end'] - 0.01)
            self.assertEqual(profile['analysis']['critical_path']['path'], ['first', 'second'])

    def test_profiler_overhead_is_bounded(self):
        # A sampler at 20 Hz over a tree of eight processes; the build default is 1 Hz.
        sleepers = [subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(3)']) for _ in range(8)]
        root = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(3)'])
        try:
            sampler = build_profile.Sampler(0.05, time.monotonic())
            sampler.add('root', root.pid)
            for index, process in enumerate(sleepers):
                sampler.add(f'sleeper{index}', process.pid)
            sampler.start()
            time.sleep(2)
            sampler.stop()
        finally:
            for process in (*sleepers, root):
                process.wait()
        per_sample = sampler.cpu_seconds / max(1, sampler.samples)
        print(f'\n[profiler overhead] {sampler.samples} samples, {sampler.cpu_seconds * 1000:.1f} ms CPU, '
              f'{per_sample * 1000:.3f} ms per sample of 9 process trees; at 1 s: '
              f'{per_sample * 100:.4f} % of one core', file=sys.stderr)
        self.assertGreater(sampler.samples, 20)
        self.assertLess(per_sample, 0.01)          # under 10 ms per sample of nine trees
        self.assertLess(per_sample / 1.0, 0.01)    # under 1 % of one core at the 1 s default

    def test_wrapper_costs_little_wall_time(self):
        with tempfile.TemporaryDirectory() as temp:
            command = [sys.executable, '-c', 'pass']
            def timed(cmd):
                best = 9.0
                for _ in range(3):
                    start = time.monotonic()
                    subprocess.run(cmd, check=True)
                    best = min(best, time.monotonic() - start)
                return best
            plain = timed(command)
            wrapped = timed([sys.executable, str(ROOT / 'tools/build_profile.py'), '_stage',
                             str(Path(temp) / 's.json'), str(Path(temp) / 's.jsonl'), '--', *command])
            print(f'\n[wrapper overhead] plain {plain * 1000:.0f} ms, wrapped {wrapped * 1000:.0f} ms', file=sys.stderr)
            self.assertLess(wrapped - plain, 0.5)
            stats = json.loads((Path(temp) / 's.json').read_text())
            self.assertEqual(stats['returncode'], 0)


class OutputsUnchangedTests(unittest.TestCase):
    STAGE = '''
import json, os, sys
from pathlib import Path
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
keep = ('AMIWIND_BUILD_JOBS', 'PYTHONUNBUFFERED', 'OMP_NUM_THREADS')
(out / 'result.json').write_text(json.dumps({'argv': sys.argv[1:], 'cwd': os.getcwd(),
    'env': {k: os.environ.get(k) for k in keep}}, sort_keys=True))
(out / 'data.bin').write_bytes(bytes(range(256)) * 64)
print('stage output line', sys.argv[2])
'''

    def run_build(self, root, profile, parallel):
        run = root / ('profiled' if profile else 'plain') / 'run'
        steps = [('media', [sys.executable, '-c', self.STAGE, str(root / 'out' / ('p' if profile else 'n') / 'media'), 'x']),
                 ('music', [sys.executable, '-c', self.STAGE, str(root / 'out' / ('p' if profile else 'n') / 'music'), 'y'])]
        metadata = {'compiler_jobs': 2 if parallel else 1, 'profile': profile}
        with contextlib.redirect_stdout(io.StringIO()):
            if parallel:
                execute_parallel(steps, run, metadata, root)
            else:
                build.execute(steps, run, metadata)
        return run

    def test_profiling_never_changes_stage_outputs(self):
        for parallel in (False, True):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                profiled = self.run_build(root, True, parallel)
                plain = self.run_build(root, False, parallel)
                for name in ('media', 'music'):
                    for item in ('result.json', 'data.bin'):
                        self.assertEqual((root / 'out/p' / name / item).read_bytes().replace(b'/out/p/', b'/out/n/'),
                                         (root / 'out/n' / name / item).read_bytes())
                for log in sorted((plain / 'logs').iterdir()):
                    self.assertEqual((profiled / 'logs' / log.name).read_text().replace('/out/p/', '/out/n/'),
                                     log.read_text())
                self.assertFalse((plain / build_profile.PROFILE_NAME).exists())
                if LINUX:
                    self.assertTrue((profiled / build_profile.PROFILE_NAME).is_file())

    def test_switch_and_stage_failure_status(self):
        self.assertFalse(build_profile.enabled({'profile': False}))
        with patch.dict(os.environ, {build_profile.SWITCH_ENV: 'off'}):
            self.assertFalse(build_profile.enabled({}))
            self.assertIsInstance(build_profile.start(Path('unused'), [], {}), build_profile.NullSession)
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'run'
            steps = [('first', [sys.executable, '-c', 'raise SystemExit(7)']), ('never', ['does-not-exist'])]
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, 'first failed'):
                build.execute(steps, run, {})
            state = json.loads((run / 'build-state.json').read_text())
            self.assertEqual([s['status'] for s in state['steps']], ['failed'])
            if LINUX:
                profile = json.loads((run / build_profile.PROFILE_NAME).read_text())
                self.assertEqual(profile['status'], 'failed')
                self.assertEqual(profile['stages'][0]['status'], 'failed')
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'run'
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, 'missing failed'):
                build.execute([('missing', ['does-not-exist-anywhere'])], run, {})
            if os.name == 'posix':
                self.assertIn('does-not-exist-anywhere', (run / 'logs/01-missing.log').read_text())


class SectionTests(unittest.TestCase):
    def test_sections_are_free_without_the_builder_and_recorded_with_it(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(build_profile.SECTIONS_ENV, None)
            with build_profile.section('nothing'):
                pass
            self.assertEqual(build_profile.instrument('census', {}), [])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'sections.jsonl'
            with patch.dict(os.environ, {build_profile.SECTIONS_ENV: str(path)}):
                @build_profile.section('decorated')
                def work(seconds):
                    end = time.process_time() + seconds
                    while time.process_time() < end:
                        pass
                    return 'done'
                with build_profile.section('outer'):
                    self.assertEqual(work(0.05), 'done')
                    self.assertEqual(work(0.05), 'done')
                    subprocess.run(burn_stage(1, 0.1), check=True, stdout=subprocess.DEVNULL)
                with self.assertRaises(ValueError), build_profile.section('failing'):
                    raise ValueError('kept')
            rows = {row['name']: row for row in build_profile.read_sections(path)}
            self.assertEqual(rows['decorated']['calls'], 2)
            # os.times() counts whole clock ticks and the kernel splits CPU time into user and
            # system time lazily, so two 0.05 s calls can read 0.08 s on a loaded host
            # (TEST-PROFILE-SECTION-CPU-32); the section must record the work, not be tick exact.
            self.assertGreaterEqual(rows['decorated']['cpu_self'], 0.05)
            self.assertEqual(rows['decorated']['min_depth'], 1)
            self.assertEqual(rows['outer']['min_depth'], 0)
            self.assertGreaterEqual(rows['outer']['wall'], rows['decorated']['wall'])
            self.assertGreater(rows['outer']['cpu_children'], 0)
            self.assertEqual(rows['failing']['errors'], 1)

    def test_instrument_patches_listed_functions_and_maps(self):
        def heavy(value):
            return value * 2

        def ordered_map(function, items, jobs=None):
            return map(function, items)
        namespace = {'heavy': heavy, 'ordered_map': ordered_map}
        table = {'unit': ('heavy', 'ordered_map', 'absent', 'textwrap:dedent')}
        original_run = subprocess.run
        with tempfile.TemporaryDirectory() as temp, patch.dict(build_profile.INSTRUMENT, table), \
                patch.dict(os.environ, {build_profile.SECTIONS_ENV: str(Path(temp) / 's.jsonl')}), \
                patch.object(subprocess, 'run', original_run), patch.object(textwrap, 'dedent', textwrap.dedent):
            missing = build_profile.instrument('unit', namespace)
            self.assertEqual(missing, ['absent'])
            self.assertEqual(namespace['heavy'](3), 6)
            self.assertEqual(list(namespace['ordered_map'](heavy, [1, 2, 3], 2)), [2, 4, 6])
            self.assertTrue(getattr(subprocess.run, '__amiwind_section__', None))
            self.assertEqual(build_profile.instrument('unit', namespace), ['absent'])  # idempotent
            rows = {row['name']: row for row in build_profile.read_sections(Path(temp) / 's.jsonl')}
        self.assertIs(subprocess.run, original_run)
        self.assertEqual(rows['heavy']['calls'], 1)
        self.assertEqual(rows['parallel map: heavy']['items'], 3)
        self.assertTrue(rows['instrumentation missing: absent']['missing'])

    def test_every_instrument_target_exists(self):
        """A renamed function shows here, not as a silently missing section."""
        import importlib
        for stage, targets in build_profile.INSTRUMENT.items():
            script = importlib.import_module(build_profile.INSTRUMENT_SCRIPTS[stage])
            for target in targets:
                holder, attribute = build_profile.resolve_target(target, vars(script))
                found = holder.get(attribute) if isinstance(holder, dict) else getattr(holder, attribute, None)
                self.assertTrue(callable(found), f'{stage}: {target} not found')


class AnalysisTests(unittest.TestCase):
    def test_critical_path_on_a_synthetic_dag(self):
        stages = [stage('a', 0, 10), stage('b', 10, 5, ['a']), stage('c', 10, 20, ['a']),
                  stage('d', 30, 1, ['b', 'c']), stage('e', 0, 3)]
        result = build_profile.critical_path(stages)
        self.assertEqual(result['path'], ['a', 'c', 'd'])
        self.assertEqual(result['ideal_seconds'], 31)
        self.assertEqual(result['actual_path'], ['a', 'c', 'd'])
        self.assertEqual(result['slack'], {'a': 0, 'e': 28, 'b': 15, 'c': 0, 'd': 0})
        # The build waited for the job slot of b: the waited-on chain differs from the ideal one.
        late = [stage('a', 0, 10), stage('b', 25, 5, ['a']), stage('c', 10, 10, ['a']), stage('d', 30, 1, ['b', 'c'])]
        self.assertEqual(build_profile.critical_path(late)['actual_path'], ['a', 'b', 'd'])
        self.assertEqual(build_profile.critical_path(late)['path'], ['a', 'c', 'd'])
        with self.assertRaises(ValueError):
            build_profile.critical_path([stage('x', 0, 1, ['y']), stage('y', 0, 1, ['x'])])

    def test_idle_warning_fires_and_does_not(self):
        timeline = {'interval': 1.0, 't': [float(i) for i in range(200)], 'stages': {
            'serial': [[i, 1.0] for i in range(120)],
            'busy': [[i, 6.0] for i in range(120)],
            'short': [[i, 1.0] for i in range(30)] + [[i, 7.5] for i in range(30, 120)],
            'gap': [[i, 1.0] for i in range(50)] + [[50, 8.0]] + [[i, 1.0] for i in range(51, 101)]}}
        serial = build_profile.idle_periods(stage('serial', 0, 120, jobs=8), timeline)
        self.assertEqual(serial['seconds'], 120.0)
        self.assertEqual(serial['cores_while_idle'], 1.0)
        self.assertIsNone(build_profile.idle_periods(stage('busy', 0, 120, jobs=8), timeline))
        self.assertIsNone(build_profile.idle_periods(stage('short', 0, 120, jobs=8), timeline))
        self.assertIsNone(build_profile.idle_periods(stage('gap', 0, 101, jobs=8), timeline))
        # Without a timeline the stage average decides.
        self.assertEqual(build_profile.idle_periods(stage('avg', 0, 300, jobs=16, cpu=310), None)['source'], 'average')
        self.assertIsNone(build_profile.idle_periods(stage('avg', 0, 300, jobs=16, cpu=3000), None))
        self.assertIsNone(build_profile.idle_periods(stage('avg', 0, 50, jobs=16, cpu=50), None))
        profile = {'stages': [stage('image', 0, 1380, jobs=16, cpu=1360)], 'budget': 16, 'wall_seconds': 1380,
                   'timeline': None}
        analysis = build_profile.analyse(profile)
        self.assertEqual([w['stage'] for w in analysis['idle_warnings']], ['image'])
        self.assertTrue(any('image: used 0.99 of 16 cores' in text for text in analysis['suggestions']))

    def test_report_compare_and_html(self):
        with tempfile.TemporaryDirectory() as temp:
            old = fixture_profile(Path(temp) / 'old', {'setup': 10, 'scene': 100, 'image': 200},
                                  fingerprints={'setup': 'f1', 'scene': 'f2', 'image': 'f3'})
            fixture_profile(Path(temp) / 'new', {'setup': 10.5, 'scene': 60, 'image': 260},
                            fingerprints={'setup': 'f1', 'scene': 'f9', 'image': 'f3'})
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = build_profile.main(['report', str(Path(temp) / 'new'), '--compare', str(Path(temp) / 'old'),
                                           '--html', str(Path(temp) / 'chart.html'), '--fail-on-regression'])
            text = output.getvalue()
            self.assertEqual(code, 3)
            self.assertIn('REGRESSION: slower stages: image', text)
            self.assertRegex(text, r'scene .*faster')
            self.assertRegex(text, r'setup .*same \(same fingerprint: reusable\)')
            self.assertIn('Critical path', text)
            page = (Path(temp) / 'chart.html').read_text()
            self.assertIn(build_profile.CHART_JS, page)
            self.assertIn('"labels": ["setup", "scene", "image"]', page)
            self.assertIn('<title>Build profile</title>', page)
            self.assertEqual(page.count('\r'), 0)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(build_profile.main(['report', str(Path(temp) / 'old'), '--compare',
                                                     str(Path(temp) / 'old'), '--fail-on-regression']), 0)
            lines = build_profile.summary_lines(old)
            self.assertTrue(lines[0].startswith('Build profile: '))
            self.assertTrue(any(line.startswith('Critical path') for line in lines))
            record = build_profile.summary_record(Path(temp) / 'old')
            self.assertEqual(record['critical_path'], ['setup', 'scene', 'image'])
            self.assertIsNone(build_profile.summary_record(Path(temp)))

    def test_host_load_is_recorded_flagged_and_never_compared_silently(self):
        # Owner note: a busy host skews timings. 8 CPUs; this build uses 2 cores.
        def timeline(busy):
            return {'interval': 1.0, 't': [float(i) for i in range(100)], 'cores': [2.0] * 100,
                    'cgroup_cores': [2.0] * 100, 'memory_bytes': None, 'stages': {},
                    'host_cpus': 8, 'host_busy': [busy] * 100}
        quiet = build_profile.host_load(stage('image', 10, 50), timeline(.30))
        self.assertEqual((quiet['cpus'], quiet['busy_percent'], quiet['build_cores']), (8, 30.0, 2.0))
        self.assertEqual(quiet['other_percent'], 5.0)
        self.assertFalse(quiet['host_busy'])
        busy = build_profile.host_load(stage('image', 10, 50), timeline(.75))
        self.assertEqual(busy['other_percent'], 50.0)
        self.assertTrue(busy['host_busy'])
        self.assertIsNone(build_profile.host_load(stage('image', 10, 50), None))
        self.assertIsNone(build_profile.host_load(stage('late', 500, 10), timeline(.75)))
        with tempfile.TemporaryDirectory() as temp:
            runs = {}
            for name, value in (('quiet', .30), ('busy', .75)):
                profile = fixture_profile(Path(temp) / name, {'setup': 10, 'image': 60})
                profile['timeline'] = timeline(value)
                for row in profile['stages']:
                    row['host'] = build_profile.host_load(row, profile['timeline'])
                profile['analysis'] = build_profile.analyse(profile)
                (Path(temp) / name / build_profile.PROFILE_NAME).write_text(json.dumps(profile))
                runs[name] = profile
            self.assertEqual([w['stage'] for w in runs['busy']['analysis']['host_busy']], ['setup', 'image'])
            self.assertEqual(runs['quiet']['analysis']['host_busy'], [])
            self.assertEqual(build_profile.summary_record(Path(temp) / 'busy')['host_busy'], ['setup', 'image'])
            self.assertTrue(any('[host busy] image: other work used 50.0 %' in line
                                for line in build_profile.summary_lines(runs['busy'])))
            comparison = build_profile.compare(runs['busy'], runs['quiet'])
            self.assertEqual(comparison['host_mismatch'], ['setup', 'image'])
            self.assertEqual(comparison['busy_host'], {'new': True, 'old': False})
            self.assertEqual(build_profile.compare(runs['quiet'], runs['quiet'])['host_mismatch'], [])
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                build_profile.main(['report', str(Path(temp) / 'busy'), '--compare', str(Path(temp) / 'quiet')])
            text = output.getvalue()
        self.assertIn('HOST BUSY', text)
        self.assertIn('Host busy (other work used more than 25 %', text)
        self.assertIn('WARNING: busy host in one run and quiet in the other, not comparable: setup, image', text)
        self.assertIn('[host quiet -> busy]', text)

    def test_sampler_reads_the_machine_cpu(self):
        if not build_profile.linux_proc():
            self.skipTest('needs /proc/stat')
        busy, total = build_profile.read_host_cpu()
        self.assertGreater(total, 0)
        self.assertLessEqual(busy, total)
        sampler = build_profile.Sampler(.01, time.monotonic())
        sampler.sample(); time.sleep(.2); sampler.sample()
        line = sampler.timeline()
        self.assertEqual(line['host_cpus'], os.cpu_count())
        self.assertTrue(0 <= line['host_busy'][-1] <= 1)

    def test_sections_report_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'census.jsonl'
            path.write_text(json.dumps({'name': 'scan', 'wall': 2.0, 'cpu_self': 1, 'cpu_children': 7, 'start': 1, 'depth': 0}) + '\n')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(build_profile.main(['report', str(path)]), 0)
            self.assertIn('scan', output.getvalue())
            self.assertIn('4.0', output.getvalue())


if __name__ == '__main__':
    unittest.main()
