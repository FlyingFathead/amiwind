"""Build Timeline (tools/build_profile.py timeline): time conversion, CPU areas that never exceed what was
measured (TEST-PROFILE-TIMELINE-SUM-33, TEST-PROFILE-TIMELINE-BOUND-33), finished and running runs, reused
stages, optional inputs, and a byte-identical PNG from the same inputs."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_profile  # noqa: E402

HAVE_PIL = importlib.util.find_spec('PIL') is not None
UTC_START = '2026-10-10T15:00:00+00:00'     # 18:00 at UTC+03:00
START = 1791644400.0                          # the same moment as epoch seconds
EAST3 = 3 * 3600


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding='utf-8', newline='\n')


def finished_run(root, name='2026_10_10_v9.9.9-dev1_full_abc1234'):
    """A finished run: build-profile.json (container clock in UTC) with a reused stage and a timeline."""
    run = root / name
    stages = [{'name': 'setup', 'number': 1, 'status': 'passed', 'jobs': 1, 'dependencies': [], 'start': 0.0,
               'end': 0.5, 'wall': 0.5, 'cpu': 0.1, 'reused': {'from': 'older', 'fingerprint': 'f'}},
              {'name': 'world', 'number': 2, 'status': 'passed', 'jobs': 4, 'dependencies': ['setup'], 'start': 0.5,
               'end': 600.5, 'wall': 600.0, 'cpu': 1800.0},
              {'name': 'image', 'number': 3, 'status': 'failed', 'jobs': 2, 'dependencies': ['world'], 'start': 600.5,
               'end': 900.5, 'wall': 300.0, 'cpu': 300.0}]
    times = [float(t) for t in range(1, 901)]
    profile = {'schema': build_profile.SCHEMA, 'run': f'/vol/build/{name}', 'version': '9.9.9-dev1', 'status': 'failed',
               'started_at': UTC_START.replace('+00:00', '+0000'), 'wall_seconds': 901.0, 'budget': 4,
               'counters': 'linux-proc', 'overhead': {}, 'stages': stages, 'host_cpus': 8,
               'timeline': {'interval': 1.0, 't': times, 'cores': [3.0 if t <= 600 else 1.0 for t in times],
                            'cgroup_cores': None, 'memory_bytes': None, 'host_cpus': 8,
                            'host_busy': [0.5 for _ in times], 'stages': {}}}
    profile['analysis'] = build_profile.analyse(profile)
    write(run / build_profile.PROFILE_NAME, profile)
    write(run / 'build-state.json', {'build_started_at': '2026-10-10T14:59:40+00:00', 'steps': []})
    return run


def running_run(root, name='2026_10_10_v9.9.9-dev1_full-resume_abc1234'):
    """A run still going: no profile; build-state.json steps on the scheduler clock, build-progress.json."""
    run = root / name
    write(run / 'build-state.json', {
        'build_started_at': '2026-10-10T16:00:00+00:00', 'status': 'running', 'worker_budget': 4,
        'runtime_version': '9.9.9-dev1',
        'steps': [{'name': 'setup', 'status': 'passed', 'jobs': 1, 'started_seconds': 0.1, 'elapsed_seconds': 0.3,
                   'reused': 'reused (fingerprint f) from older', 'profile': {'cpu_seconds': 0.2}},
                  {'name': 'world', 'status': 'running', 'jobs': 4, 'started_seconds': 1.0}]})
    write(run / 'build-progress.json', {
        'schema': 'amiwind-build-progress-v1', 'status': 'running', 'started_at': '2026-10-10T16:00:10+00:00',
        'updated_epoch': START + 3600 + 10 + 1200.0, 'budget': 4, 'host': {'cpus': 8},
        'stages': [{'name': 'setup', 'status': 'passed', 'elapsed_seconds': 0.3},
                   {'name': 'world', 'status': 'running', 'elapsed_seconds': 1199.0},
                   {'name': 'image', 'status': 'pending'}]})
    return run


class TimeConversion(unittest.TestCase):
    def test_utc_records_are_converted_and_naive_times_read_in_the_given_zone(self):
        self.assertEqual(build_profile.to_epoch(UTC_START), START)
        self.assertEqual(build_profile.to_epoch('2026-10-10T15:00:00Z'), START)
        self.assertEqual(build_profile.to_epoch('2026-10-10T18:00:00+0300'), START)   # time.strftime('%z')
        self.assertEqual(build_profile.to_epoch('2026-10-10 18:00', EAST3), START)
        self.assertEqual(build_profile.to_epoch('2026-10-10T18:00:00', EAST3), START)
        # A naive time is never read in this machine's zone by accident: the zone is an argument.
        self.assertEqual(build_profile.to_epoch('2026-10-10 15:00', 0), START)
        self.assertEqual(build_profile.to_epoch(START), START)
        self.assertIsNone(build_profile.to_epoch(None))
        self.assertEqual(build_profile.clock_text(START, EAST3), '18:00')
        self.assertEqual(build_profile.clock_text(START, 0), '15:00')

    def test_utc_offsets(self):
        self.assertEqual(build_profile.parse_utc_offset('+03:00'), EAST3)
        self.assertEqual(build_profile.parse_utc_offset('-0530'), -(5 * 3600 + 30 * 60))
        self.assertEqual(build_profile.parse_utc_offset('+3'), EAST3)
        self.assertEqual(build_profile.parse_utc_offset('UTC'), 0)
        self.assertEqual(build_profile.parse_utc_offset('local'), build_profile.local_utc_offset())
        for bad in ('3:00:00', '+25:00', 'EEST'):
            with self.assertRaises(ValueError):
                build_profile.parse_utc_offset(bad)


class CpuArea(unittest.TestCase):
    def test_a_late_sample_never_spreads_over_time_it_did_not_see(self):
        # TEST-PROFILE-TIMELINE-SUM-33: a stage burns 4 cores; the sampler (1 s) is late once, its sample at
        # t=8 measures only the last second. Multiplying that rate by the whole 5 s gap overstates the CPU
        # (36 core-seconds against 20 measured); the timeline must keep the measured 20.
        points = [(1.0, 4.0), (2.0, 4.0), (3.0, 4.0), (8.0, 4.0), (9.0, 4.0)]
        measured = 20.0
        naive = 4.0 + sum(later[1] * (later[0] - earlier[0]) for earlier, later in zip(points, points[1:]))
        self.assertGreater(naive, measured + 0.2)
        intervals = build_profile.sample_intervals(points, nominal=1.0)
        self.assertAlmostEqual(build_profile.core_seconds(intervals), measured, places=9)
        values, covered = build_profile.bucket_series(intervals, 0.0, 30.0, 1)
        self.assertAlmostEqual(values[0] * 30.0, measured, places=9)
        self.assertAlmostEqual(covered[0], 5.0, places=9)

    def test_rounded_rates_over_jittered_intervals_stay_within_the_bound(self):
        # TEST-PROFILE-TIMELINE-BOUND-33: rates are rounded to three decimals over jittered intervals; the
        # chart's area stays within 0.2 core-seconds of the exact CPU, and bucketing keeps it exactly.
        cpu, at, points = 0.0, 0.0, []
        for index in range(400):
            gap = 1.0 + 0.37 * ((index * 7919) % 11) / 10.0       # deterministic jitter, 1.0-1.37 s
            burned = 2.0 * gap + 0.0007 * (index % 5)
            at += gap
            cpu += burned
            points.append((at, round(burned / gap, 3)))
        # The first sample covers the time since the stage started (t=0).
        intervals = build_profile.sample_intervals(points, nominal=points[0][0], cap=3.0)
        self.assertLess(abs(build_profile.core_seconds(intervals) - cpu), 0.2)
        values, _ = build_profile.bucket_series(intervals, -10.0, 30.0, 30)
        self.assertAlmostEqual(sum(values) * 30.0, build_profile.core_seconds(intervals), places=6)

    def test_buckets_keep_only_the_window(self):
        intervals = [(0.0, 100.0, 2.0)]
        values, _ = build_profile.bucket_series(intervals, 50.0, 30.0, 1)   # window 50-80 s
        self.assertAlmostEqual(values[0] * 30.0, 60.0)


class Runs(unittest.TestCase):
    def test_finished_run_with_reused_stages(self):
        with tempfile.TemporaryDirectory() as temp:
            run = build_profile.timeline_run(finished_run(Path(temp)))
        self.assertEqual(run['origin'], START)
        self.assertEqual(run['started'], START - 20)      # the receipt starts before the first stage
        self.assertEqual(run['end'], START + 901.0)
        names = {row['name']: row for row in run['stages']}
        self.assertTrue(names['setup']['reused'])
        self.assertFalse(names['world']['reused'])
        self.assertEqual(names['world']['start'], START + 0.5)
        self.assertEqual(names['image']['status'], 'failed')
        self.assertIn('world', run['critical_path'])
        self.assertEqual(len(run['cores']), 900)
        self.assertEqual(run['host'][0][1], 4.0)            # host_busy 0.5 of 8 CPUs
        data = build_profile.timeline_data([run], offset=EAST3)
        series = {entry['name']: entry for entry in data['series']}
        # 600 s at 3 cores + 300 s at 1 core, all inside the default window.
        self.assertAlmostEqual(series[run['label']]['core_seconds'], 2100.0, delta=0.5)
        self.assertEqual(data['host']['source'], 'build profiler (/proc/stat)')

    def test_running_run_from_state_and_progress(self):
        with tempfile.TemporaryDirectory() as temp:
            run = build_profile.timeline_run(running_run(Path(temp)), label='resume')
        self.assertTrue(run['running'])
        self.assertEqual(run['label'], 'resume')
        self.assertEqual(run['origin'], START + 3610)       # build-progress.json started_at (UTC) converted
        world = next(row for row in run['stages'] if row['name'] == 'world')
        self.assertTrue(world['running'])
        self.assertEqual(world['start'], START + 3611)
        self.assertEqual(world['end'], START + 3610 + 1200)  # running: elapsed from the progress file
        self.assertEqual(run['pending'], ['image'])
        setup = next(row for row in run['stages'] if row['name'] == 'setup')
        self.assertTrue(setup['reused'])
        self.assertEqual(run['end'], START + 3610 + 1200)

    def test_samples_join_their_run_and_host_lines(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = build_profile.timeline_run(running_run(root))
            samples = root / 'samples.jsonl'
            lines = ['not json', json.dumps({'t': 'x', 'name': 'a', 'cores': 1})]
            for second in range(0, 1200, 30):
                stamp = build_profile.clock_text(START + 3610 + second, EAST3, '%Y-%m-%dT%H:%M:%S')
                lines.append(json.dumps({'t': stamp, 'name': 'aw-build-' + run['name'], 'cores': 4.0}))
                lines.append(json.dumps({'t': stamp, 'name': 'gate-suite-7', 'cores': 1.0, 'group': 'gates'}))
                lines.append(json.dumps({'t': stamp, 'name': 'HOST', 'cpu_pct': 75.0}))
            samples.write_text('\n'.join(lines) + '\n', encoding='utf-8')
            read = build_profile.read_cpu_samples(samples, EAST3, cpus=8)
        self.assertEqual(sorted(read), ['HOST', 'aw-build-' + run['name'], 'gate-suite-7'])
        self.assertEqual(read['HOST'][0][1], 6.0)           # 75 % of 8 CPUs
        self.assertEqual(read['gate-suite-7'][0][0], START + 3610)
        data = build_profile.timeline_data([run], samples=read, offset=EAST3)
        names = [entry['name'] for entry in data['series']]
        self.assertEqual(sorted(names), sorted([run['label'], 'gates']))
        self.assertEqual(data['host']['source'], 'samples')
        build = next(entry for entry in data['series'] if entry['name'] == run['label'])
        self.assertAlmostEqual(build['core_seconds'], 4.0 * 1200, delta=1.0)

    def test_missing_optional_inputs_and_events(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = build_profile.timeline_run(finished_run(root))
            gates = root / 'gates.jsonl'
            gates.write_text('\n'.join([
                json.dumps({'name': '1', 'start': '2026-10-10 18:01', 'end': '2026-10-10 18:04', 'result': 'passed'}),
                json.dumps({'name': '2', 'start': START + 400, 'end': None}),
                '{broken']) + '\n', encoding='utf-8')
            events = build_profile.read_lane_events(gates, EAST3)
            self.assertEqual([item['result'] for item in events], ['passed', 'running'])
            self.assertEqual(events[0]['start'], START + 60)
            data = build_profile.timeline_data([run], events=events, offset=EAST3)
            self.assertEqual(events[1]['end'], data['data_end'])   # still running: drawn to the end of the data
            bare = build_profile.timeline_data([run])
            self.assertEqual(bare['events'], [])
            self.assertEqual(bare['commits'], [])
            out = root / 'chart.json'
            with contextlib.redirect_stdout(io.StringIO()):
                code = build_profile.main(['timeline', str(root / run['name']), '--json', str(out),
                                           '--utc-offset', '+03:00'])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out.read_text(encoding='utf-8'))['schema'], build_profile.TIMELINE_SCHEMA)

    @unittest.skipUnless(HAVE_PIL, 'Pillow is not installed')
    def test_png_is_byte_identical_from_the_same_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runs = [finished_run(root), running_run(root)]
            digests = []
            for attempt in range(2):
                out = root / f'chart-{attempt}.png'
                with contextlib.redirect_stdout(io.StringIO()):
                    code = build_profile.main(['timeline', *map(str, runs), '--png', str(out), '--utc-offset', '+03:00',
                                               '--labels', 'first', 'resume', '--title', 'test'])
                self.assertEqual(code, 0)
                data = out.read_bytes()
                self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
                digests.append(hashlib.sha256(data).hexdigest())
            self.assertEqual(digests[0], digests[1])
            with contextlib.redirect_stdout(io.StringIO()):
                build_profile.main(['timeline', str(runs[0]), '--png', str(root / 'utc.png'), '--utc-offset', 'UTC'])
            self.assertNotEqual(hashlib.sha256((root / 'utc.png').read_bytes()).hexdigest(), digests[0])


class Published(unittest.TestCase):
    def test_documented_and_the_example_is_release_listed(self):
        listed = json.loads((ROOT / 'tools/release-files.json').read_text(encoding='utf-8'))
        image = 'docs/images/amiwind-v0.0.36-build-timeline.png'
        for name in (image, 'tests/test_build_timeline.py', 'tools/build_profile.py'):
            self.assertIn(name, listed)
        self.assertEqual((ROOT / image).read_bytes()[:8], b'\x89PNG\r\n\x1a\n')
        text = (ROOT / 'docs/BUILD_PROFILE.md').read_text(encoding='utf-8')
        self.assertIn('## Build Timeline', text)
        self.assertIn('amiwind-v0.0.36-build-timeline.png', text)


if __name__ == '__main__':
    unittest.main()
