# SPDX-License-Identifier: GPL-3.0-only
"""The resource plan (tools/resource_plan.py): per-stage memory and thread estimates from synthetic plans and
measurements, the checklist states (OK / WILL THROTTLE / WILL NOT FIT), the advisory, the schema, the refusal before
any stage (tools/build.py), estimate-vs-actual after a build, and the running half: the memory governor of a pool and
the scheduler's memory guard grow and shrink with the memory the container has."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import resource_plan as rp  # noqa: E402

GIB = 1 << 30
MIB = 1 << 20


def measured(largest, total, jobs, wall=100.0, cores=4.0, run='/vol/ws8/build/r1'):
    return {'jobs': jobs, 'largest_mib': float(largest), 'total_mib': float(total),
            'worker_mib': max(0.0, total - largest) / jobs, 'wall': wall, 'cores': cores, 'run': run}


def got(memory_gb, threads, machine_gb=64):
    return {'memory_bytes': int(memory_gb * GIB), 'memory_source': 'test', 'used_bytes': 0, 'threads': threads,
            'threads_source': 'test', 'machine_bytes': int(machine_gb * GIB), 'machine_threads': 24}


STEPS = [('setup', ['python3', 'tools/setup.py']),
         ('scene', ['python3', 'tools/prepare_scene.py', '--jobs', '8']),
         ('chim', ['python3', 'tools/chim_build.py', '--jobs', '8'])]


class PlanTests(unittest.TestCase):
    def gathered(self, stair=None, **stages):
        return {'stages': stages, 'stair': stair, 'runs': ['/vol/ws8/build/r1']}

    def test_ok_when_everything_fits(self):
        doc = rp.plan(STEPS, {'setup', 'scene'}, 8, got(30, 24),
                      self.gathered(scene=[measured(300, 1100, 8)]))
        self.assertEqual(doc['verdict'], 'ok')
        rows = {r['stage']: r for r in doc['stages']}
        self.assertEqual(set(rows), {'setup', 'scene'})          # only the stages that will run
        self.assertEqual(rows['setup']['planned_workers'], 1)     # no --jobs: one process
        self.assertEqual(rows['setup']['model'], 'estimated, no data yet')
        self.assertEqual(rows['scene']['workers'], 8)
        self.assertEqual(rows['scene']['worker_mib'], 100.0)
        self.assertEqual(rows['scene']['model'], 'measured (1 run)')
        self.assertIsNone(doc['advisory'])
        self.assertEqual(rp.validate(doc), [])

    def test_memory_throttle_names_the_number_and_the_reason_with_an_advisory(self):
        # the stair model: 2,643 MiB a walk worker (whole-city Vivec) beside a 1,700 MiB parent in 30 GiB
        doc = rp.plan(STEPS, {'chim'}, 11, got(30, 24),
                      self.gathered(stair=('x+04/y-12', 2643.0, 'measured: the stair gate of r1'),
                                    chim=[measured(1700, 30000, 11, wall=600, cores=8)]))
        row = doc['stages'][0]
        self.assertEqual(row['status'], 'WILL THROTTLE')
        self.assertEqual(row['workers'], int((30 * 1024 * 0.8 - 1700) // 2643))
        self.assertIn('memory holds', row['reasons'][0])
        self.assertIn('stair walk of frame x+04/y-12', row['largest_unit'])
        self.assertEqual(row['stair']['worker_mib'], 2643.0)
        self.assertEqual(doc['verdict'], 'throttled')
        self.assertIsNotNone(doc['advisory'])
        self.assertIn('the lease to ask for: --threads', doc['advisory']['text'])
        self.assertGreater(doc['advisory']['memory_gb'], 30)
        self.assertEqual(rp.validate(doc), [])
        lines = rp.checklist(doc)
        self.assertTrue(any(line.strip().startswith('WILL THROTTLE') for line in lines))
        self.assertTrue(lines[-2].startswith('ADVISORY: '))

    def test_thread_throttle(self):
        doc = rp.plan(STEPS, {'scene'}, 16, got(64, 6), self.gathered(scene=[measured(300, 1100, 8)]))
        row = doc['stages'][0]
        self.assertEqual((row['status'], row['workers']), ('WILL THROTTLE', 6))
        self.assertIn('6 threads', row['reasons'][0])

    def test_a_unit_larger_than_the_memory_will_not_fit(self):
        doc = rp.plan(STEPS, {'chim'}, 8, got(2, 24),
                      self.gathered(stair=('x+04/y-12', 2643.0, 'measured'), chim=[measured(1700, 4000, 8)]))
        row = doc['stages'][0]
        self.assertEqual(row['status'], 'WILL NOT FIT')
        self.assertEqual(doc['verdict'], 'refused')
        self.assertIn('x+04/y-12', doc['refusals'][0])
        self.assertIn('2643 MiB', doc['refusals'][0])
        self.assertEqual(rp.validate(doc), [])

    def test_the_advisory_never_asks_for_more_than_the_machine(self):
        doc = rp.plan(STEPS, {'chim'}, 24, got(44, 24, machine_gb=47),
                      self.gathered(stair=('f', 2349.0, 'estimated'), chim=[measured(12750, 34000, 8, 2888, 13.6)]))
        self.assertLessEqual(doc['advisory']['memory_gb'], 47)
        self.assertIn('more than the machine has', doc['advisory']['text'])

    def test_schema_refuses_a_broken_plan(self):
        doc = rp.plan(STEPS, {'scene'}, 8, got(30, 24), self.gathered())
        broken = dict(doc)
        del broken['verdict']
        self.assertTrue(rp.validate(broken))
        broken = json.loads(json.dumps(doc))
        broken['stages'][0]['status'] = 'MAYBE'
        self.assertTrue(rp.validate(broken))
        with self.assertRaises(ValueError):
            rp.text(broken)


class MeasurementTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def run_folder(self, name, stages, reuse_from=None, log=None, timeline=None):
        run = self.base / 'build' / name
        (run / 'logs').mkdir(parents=True)
        (run / 'build-profile.json').write_text(json.dumps({'stages': stages, 'reuse_from': reuse_from,
                                                            'timeline': timeline}), encoding='utf-8')
        if log:
            (run / 'logs' / '22-chim.log').write_text(log, encoding='utf-8')
        return run

    def test_measure_bounds_the_tree_by_the_container_and_skips_reused(self):
        row = {'name': 'chim', 'status': 'failed', 'jobs': 11, 'jobs_max': 11, 'wall': 627.0, 'cores_avg': 3.4,
               'peak_process_rss_bytes': 1700 * MIB, 'peak_tree_rss_bytes': 31070 * MIB, 'start': 0, 'end': 700}
        timeline = {'t': [10, 20], 'memory_bytes': [10 * GIB, 30 * GIB], 'stages': {'chim': [[0, 4.0], [1, 6.0]]}}
        found = rp.measure(row, timeline)
        self.assertEqual(found['total_mib'], 30 * 1024)
        self.assertTrue(found['failed'])           # memory counts, its time does not
        self.assertIsNone(found['wall'])
        self.assertIsNone(rp.measure(dict(row, reused={'from': 'x'}), timeline))

    def test_gather_walks_the_reuse_chain_and_reads_the_stair_line(self):
        old = self.run_folder('old', [{'name': 'scene', 'status': 'passed', 'jobs': 8, 'wall': 50.0,
                                       'cores_avg': 6.0, 'peak_process_rss_bytes': 300 * MIB,
                                       'peak_tree_rss_bytes': 1100 * MIB}],
                              log='CHIM stair gate: workers: 8 workers by memory (cores allow 11; about 2643 MiB '
                                  'each; cgroup v2 ...); largest frame x+04/y-12 about 2643 MiB a worker\n')
        new = self.run_folder('new', [{'name': 'scene', 'status': 'passed', 'jobs': 8, 'reused': {'from': str(old)},
                                       'peak_process_rss_bytes': MIB}], reuse_from=str(old))
        found = rp.gather(new, self.base)
        self.assertEqual(found['runs'], [str(new), str(old)])
        self.assertEqual(len(found['stages']['scene']), 1)         # the reused row is not a measurement
        self.assertEqual(found['stair'][:2], ('x+04/y-12', 2643.0))

    def test_after_build_flags_over_estimate_and_feeds_the_history(self):
        run = self.run_folder('r', [{'name': 'scene', 'status': 'passed', 'jobs': 8, 'jobs_max': 8, 'wall': 40.0,
                                     'cores_avg': 7.0, 'peak_process_rss_bytes': 400 * MIB,
                                     'peak_tree_rss_bytes': 4000 * MIB}])
        doc = rp.plan(STEPS, {'scene'}, 8, got(30, 24),
                      {'stages': {'scene': [measured(300, 1100, 8)]}, 'stair': None, 'runs': []})
        rp.write(run, doc)
        lines = []
        flagged = rp.after_build(run, self.base, log=lines.append)
        self.assertEqual(flagged, ['scene'])
        saved = json.loads((run / rp.FILE).read_text(encoding='utf-8'))
        self.assertTrue(saved['stages'][0]['actual']['over_estimate'])
        self.assertEqual(rp.validate(saved), [])
        self.assertTrue(any('more than 25 %' in line for line in lines))
        history = rp.read_history(self.base)
        self.assertEqual(history['scene'][0]['total_mib'], 4000.0)
        # the next plan uses it: the model calibrates itself
        again = rp.plan(STEPS, {'scene'}, 8, got(30, 24), rp.gather(None, self.base))
        self.assertGreaterEqual(again['stages'][0]['peak_total_mib'], 4000.0)

    def test_limits_from_the_cgroup(self):
        cg = self.base / 'cg'
        cg.mkdir()
        (cg / 'memory.max').write_text('%d\n' % (30 * GIB))
        (cg / 'memory.current').write_text('%d\n' % (5 * GIB))
        (cg / 'memory.stat').write_text('anon 1\ninactive_file %d\n' % GIB)
        (cg / 'cpu.max').write_text('1200000 100000\n')
        self.assertEqual(rp.cgroup_memory(cg), (30 * GIB, 5 * GIB, GIB))
        self.assertEqual(rp.cgroup_threads(cg), 12)
        found = rp.limits(root=cg)
        self.assertEqual(found['memory_bytes'], 30 * GIB)
        self.assertLessEqual(found['threads'], 12)
        asked = rp.limits(16, 6, root=cg)
        self.assertEqual((asked['memory_bytes'], asked['threads']), (16 * GIB, 6))
        (cg / 'cpu.max').write_text('max 100000\n')
        self.assertIsNone(rp.cgroup_threads(cg))


class FakeMemory:
    def __init__(self, limit_gb, used_gb, quota=None):
        self.limit, self.used, self.quota, self.t = limit_gb * GIB, used_gb * GIB, quota, 0.0

    def read(self):
        return (self.limit, self.used, 0), self.quota

    def clock(self):
        return self.t


class GovernorTests(unittest.TestCase):
    def test_starts_throttled_grows_when_memory_frees_and_shrinks_when_tight(self):
        memory = FakeMemory(30, 2)
        lines = []
        gov = rp.MemoryGovernor(11, 2643, 'stair', reader=memory.read, clock=memory.clock, interval=30,
                                log=lines.append)
        first = gov.limit(0)
        self.assertEqual(first, int((30 * 1024 - 2 * 1024) * 0.8 // 2643))
        self.assertIn('to start', lines[0])
        memory.limit = 44 * GIB          # a raised lease (docker update --memory)
        memory.used = 2 * GIB + first * 2643 * MIB
        self.assertEqual(gov.limit(first), first)        # no re-read before the interval
        memory.t = 31
        grown = gov.limit(first)
        self.assertEqual(grown, 11)
        self.assertIn('freed up', lines[-1])
        memory.limit, memory.t = 20 * GIB, 62            # memory tight: no new units, running ones go on
        shrunk = gov.limit(grown)
        self.assertLess(shrunk, grown)
        self.assertIn('memory tight', lines[-1])
        self.assertEqual(len(gov.changes), 3)

    def test_cpu_quota_caps_and_the_environment_names_the_unit(self):
        memory = FakeMemory(64, 1, quota=4)
        gov = rp.MemoryGovernor(12, 100, reader=memory.read, clock=memory.clock, interval=30, log=lambda line: None)
        self.assertEqual(gov.limit(0), 12)                 # --jobs exact above the start quota
        memory.quota, memory.t = 2, 31
        self.assertEqual(gov.limit(0), 6)                  # a lowered quota shrinks the pool in proportion
        self.assertIsNone(rp.governor_for(8, None, environ={}))
        self.assertIsNone(rp.governor_for(1, 500))
        self.assertIsNotNone(rp.governor_for(8, None, environ={rp.UNIT_MIB_ENV: '512'}))

    def test_scheduler_guard_caps_the_largest_stage_and_gives_it_back(self):
        memory = FakeMemory(30, 29)
        lines = []
        guard = rp.SchedulerGuard(24, {'chim': 2643}, reader=memory.read, clock=memory.clock, interval=30,
                                  log=lines.append)
        guard.tick({'chim': 12, 'scene': 4}, {'chim': 12, 'scene': 4})
        self.assertEqual(guard.cap('chim', 12), 9)
        self.assertEqual(guard.cap('scene', 4), 4)
        memory.used, memory.t = 5 * GIB, 31
        guard.tick({'chim': 9, 'scene': 4}, {'chim': 12, 'scene': 4})
        self.assertEqual(guard.cap('chim', 12), 12)
        self.assertIn('freed up', lines[-1])
        self.assertEqual(guard.effective_budget(), 24)     # no quota at the start: --jobs exact
        memory.quota, memory.t = 8, 62
        guard.tick({'chim': 12}, {'chim': 12})
        self.assertEqual(guard.effective_budget(), 24)     # a quota that was not there at the start: --jobs exact

    def test_a_lowered_quota_shrinks_the_shares_and_a_raised_one_gives_them_back(self):
        memory = FakeMemory(30, 5, quota=24)
        guard = rp.SchedulerGuard(24, reader=memory.read, clock=memory.clock, interval=30, log=lambda line: None)
        guard.tick({'a': 12}, {'a': 12})
        self.assertEqual(guard.effective_budget(), 24)
        memory.quota, memory.t = 12, 31
        guard.tick({'a': 12}, {'a': 12})
        self.assertEqual(guard.effective_budget(), 12)
        memory.quota, memory.t = 24, 62
        guard.tick({'a': 6}, {'a': 6})
        self.assertEqual(guard.effective_budget(), 24)

    def test_jobs_above_the_start_quota_stay_exact(self):
        memory = FakeMemory(30, 5, quota=4)
        guard = rp.SchedulerGuard(16, reader=memory.read, clock=memory.clock, log=lambda line: None)
        guard.tick({'a': 16}, {'a': 16})
        self.assertEqual(guard.effective_budget(), 16)


class GovernedMapTests(unittest.TestCase):
    def test_governed_map_returns_what_the_serial_map_returns(self):
        import build_parallel
        items = list(range(-20, 20))
        with mock.patch.object(rp, 'cgroup_memory', lambda root='/sys/fs/cgroup': (4 * GIB, GIB, 0)), \
                contextlib.redirect_stdout(io.StringIO()):
            governed = sorted(build_parallel.governed_map(abs, items, 4, unit_mib=1024, label='test'))
        self.assertEqual(governed, sorted(map(abs, items)))


class BuildPreflightTests(unittest.TestCase):
    def args(self, **change):
        values = dict(resource_check='fail', dry_run=False, reuse_from=None, workspace=Path(tempfile.gettempdir()),
                      jobs=8, resource_memory_gb=2, resource_threads=8)
        values.update(change)
        return types.SimpleNamespace(**values)

    def test_will_not_fit_refuses_before_any_stage(self):
        import build
        steps = [('chim', ['python3', 'tools/chim_build.py', '--jobs', '8'])]
        stair = {'stages': {}, 'stair': ('x+04/y-12', 2643.0, 'measured'), 'runs': []}
        metadata = {'stage_cache': {'reused': {}}}
        with mock.patch.object(rp, 'gather', lambda *a, **k: stair), \
                mock.patch.object(rp, 'state_line', lambda *a, **k: ('Machine at start: test', {})), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            with self.assertRaisesRegex(ValueError, 'WILL NOT FIT'):
                build.resource_preflight(self.args(), steps, metadata)
            self.assertIn('WILL NOT FIT', out.getvalue())
            warned = build.resource_preflight(self.args(resource_check='warn'), steps, {'stage_cache': {}})
            self.assertEqual(warned['verdict'], 'refused')
            ok = {'stage_cache': {'reused': {}}}
            build.resource_preflight(self.args(resource_memory_gb=30), steps, ok)
        self.assertIn(rp.FILE, ok['_run_files'])
        self.assertEqual(ok['resource_plan_units'], {'chim': 2643.0})
        self.assertEqual(json.loads(ok['_run_files'][rp.FILE])['schema'], rp.SCHEMA)
        self.assertIsNone(build.resource_preflight(self.args(resource_check='off'), steps, {}))

    def test_reused_stages_do_not_count(self):
        import build
        steps = [('chim', ['python3', 'tools/chim_build.py', '--jobs', '8'])]
        stair = {'stages': {}, 'stair': ('x+04/y-12', 2643.0, 'measured'), 'runs': []}
        metadata = {'stage_cache': {'reused': {'chim': {}}}}
        with mock.patch.object(rp, 'gather', lambda *a, **k: stair), \
                mock.patch.object(rp, 'state_line', lambda *a, **k: ('Machine at start: test', {})), \
                contextlib.redirect_stdout(io.StringIO()):
            doc = build.resource_preflight(self.args(), steps, metadata)
        self.assertEqual(doc['stages'], [])
        self.assertEqual(doc['verdict'], 'ok')


if __name__ == '__main__':
    unittest.main()
