"""Parallel test runner: same discovery and outcomes as the serial unittest run."""
import collections
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'tools/run_tests.py'
sys.path.insert(0, str(ROOT / 'tools'))
import run_tests  # noqa: E402

# Serial reference: the stock loader and runner in one process, outcomes as JSON.
SERIAL = textwrap.dedent('''
    import json, sys, unittest
    class Result(unittest.TestResult):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.rows = []
        def addSuccess(self, test):
            super().addSuccess(test); self.rows.append([test.id(), 'passed'])
        def addFailure(self, test, err):
            super().addFailure(test, err); self.rows.append([test.id(), 'failed'])
        def addError(self, test, err):
            super().addError(test, err); self.rows.append([test.id(), 'error'])
        def addSkip(self, test, reason):
            super().addSkip(test, reason); self.rows.append([test.id(), 'skipped'])
        def addExpectedFailure(self, test, err):
            super().addExpectedFailure(test, err); self.rows.append([test.id(), 'expected_failure'])
        def addUnexpectedSuccess(self, test):
            super().addUnexpectedSuccess(test); self.rows.append([test.id(), 'unexpected_success'])
        def addSubTest(self, test, subtest, err):
            super().addSubTest(test, subtest, err)
            if err is not None:
                failed = issubclass(err[0], test.failureException)
                self.rows.append([subtest.id(), 'failed' if failed else 'error'])
    suite = unittest.TestLoader().discover(sys.argv[1])
    result = Result()
    suite.run(result)
    print(json.dumps(dict(rows=sorted(result.rows), tests_run=result.testsRun)))
''')

MODULES = {
    'test_fx_pass.py': '''
        import unittest
        class PassTests(unittest.TestCase):
            def test_one(self):
                self.assertTrue(True)
            def test_two(self):
                for i in range(3):
                    with self.subTest(i=i):
                        self.assertLess(i, 3)
    ''',
    'test_fx_mixed.py': '''
        import unittest
        class MixedTests(unittest.TestCase):
            def test_fails(self):
                self.assertEqual(1, 2)
            def test_errors(self):
                raise RuntimeError('boom')
            def test_subtests(self):
                for i in range(4):
                    with self.subTest(i=i):
                        self.assertEqual(i % 2, 0)
            @unittest.expectedFailure
            def test_expected(self):
                self.fail('known')
            @unittest.expectedFailure
            def test_unexpected(self):
                pass
            def test_skip(self):
                self.skipTest('needs a thing')
        @unittest.skip('whole class')
        class SkippedClass(unittest.TestCase):
            def test_never(self):
                pass
    ''',
    'test_fx_import_error.py': '''
        raise ImportError('missing dependency')
    ''',
    'test_fx_module_skip.py': '''
        import unittest
        raise unittest.SkipTest('module needs a tool')
    ''',
    'test_fx_imports_class.py': '''
        from test_fx_pass import PassTests
    ''',
    'test_fx_class_fixture.py': '''
        import unittest
        class Broken(unittest.TestCase):
            @classmethod
            def setUpClass(cls):
                raise RuntimeError('fixture failed')
            def test_a(self):
                pass
    ''',
    'fxpkg/__init__.py': '',
    'fxpkg/test_fx_inner.py': '''
        import unittest
        class InnerTests(unittest.TestCase):
            def test_inner(self):
                pass
    ''',
    'helper_not_a_test.py': '''
        raise SystemExit('never imported by discovery')
    ''',
}


def write_tree(root, files):
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text), encoding='utf-8', newline='\n')
    return root


class RunnerCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix='amiwind-run-tests-')
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def tree(self, name, files):
        return write_tree(self.tmp / name, files)

    def runner(self, start, *options, env=None):
        report = self.tmp / ('report-%d.json' % len(list(self.tmp.glob('report-*.json'))))
        command = [sys.executable, str(RUNNER), '-s', str(start), '--json', str(report), *options]
        result = subprocess.run(command, cwd=self.tmp, capture_output=True, text=True,
                                env=dict(os.environ, **(env or {})), timeout=300)
        data = json.loads(report.read_text(encoding='utf-8')) if report.is_file() else None
        return result, data

    def serial(self, start):
        result = subprocess.run([sys.executable, '-c', SERIAL, str(start)], cwd=self.tmp,
                                capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout.strip().splitlines()[-1])


class DiscoveryTests(RunnerCase):
    def discovered(self, start):
        """Both discoveries in a fresh interpreter: fixture modules never enter this process."""
        script = ('import json, sys; sys.path.insert(0, sys.argv[1]); import run_tests; '
                  'print(json.dumps(dict(modules=run_tests.discover(sys.argv[2]), '
                  'serial=run_tests.serial_discovery_ids(sys.argv[2]))))')
        result = subprocess.run([sys.executable, '-c', script, str(ROOT / 'tools'), str(start)],
                                cwd=self.tmp, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout.strip().splitlines()[-1])

    def test_repository_suite_discovery_matches_serial_loader(self):
        found = self.discovered(ROOT / 'tests')
        parallel = sorted(i for ids in found['modules'].values() for i in ids)
        self.assertEqual(parallel, found['serial'])
        self.assertGreater(len(found['modules']), 100)
        self.assertIn('test_run_tests.DiscoveryTests.test_repository_suite_discovery_matches_serial_loader',
                      parallel)

    def test_fixture_discovery_keeps_failures_skips_packages_and_imported_classes(self):
        found = self.discovered(self.tree('fx', MODULES))
        modules = found['modules']
        self.assertEqual(sorted(i for ids in modules.values() for i in ids), found['serial'])
        self.assertEqual(modules['test_fx_import_error'], ['unittest.loader._FailedTest.test_fx_import_error'])
        self.assertEqual(modules['test_fx_module_skip'], ['unittest.loader.ModuleSkipped.test_fx_module_skip'])
        # An imported TestCase runs again under the importing module, as in serial runs.
        self.assertEqual(sorted(modules['test_fx_imports_class']), sorted(modules['test_fx_pass']))
        self.assertIn('fxpkg.test_fx_inner', modules)
        self.assertNotIn('helper_not_a_test', modules)

    def test_list_prints_the_discovered_ids(self):
        start = self.tree('fx', MODULES)
        result = subprocess.run([sys.executable, str(RUNNER), '-s', str(start), '--list'], cwd=self.tmp,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(result.stdout.split()), self.discovered(start)['serial'])


class OutcomeTests(RunnerCase):
    def test_outcomes_and_counts_match_a_serial_run(self):
        start = self.tree('fx', MODULES)
        serial = self.serial(start)
        result, report = self.runner(start, '--jobs', '3')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        rows = sorted([r['test'], r['status']] for r in report['results'])
        self.assertEqual(rows, serial['rows'])
        self.assertEqual(report['tests_run'], serial['tests_run'])
        counts = collections.Counter(status for _, status in serial['rows'])
        self.assertEqual(report['failures'], counts['failed'])
        self.assertEqual(report['errors'], counts['error'])
        self.assertEqual(report['skipped'], counts['skipped'])
        self.assertEqual(report['expected_failures'], counts['expected_failure'])
        self.assertEqual(report['unexpected_successes'], counts['unexpected_success'])
        self.assertEqual(report['module_problems'], [])
        self.assertIn('FAILED', result.stdout)
        self.assertIn('test_fx_mixed.MixedTests.test_fails', result.stdout)

    def test_results_are_deterministic_across_job_counts(self):
        start = self.tree('fx', MODULES)
        _, one = self.runner(start, '--jobs', '1')
        _, many = self.runner(start, '--jobs', '4')
        for key in ('results', 'failed', 'skips', 'tests_run', 'failures', 'errors', 'skipped'):
            self.assertEqual(one[key], many[key], key)
        self.assertEqual(sorted(one['module_seconds']), sorted(many['module_seconds']))

    def test_passing_suite_exits_zero_and_one_failure_exits_nonzero(self):
        passing = {'test_fx_pass.py': MODULES['test_fx_pass.py'],
                   'fxpkg/__init__.py': '', 'fxpkg/test_fx_inner.py': MODULES['fxpkg/test_fx_inner.py']}
        result, report = self.runner(self.tree('ok', passing), '--jobs', '2')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(report['successful'])
        self.assertEqual((report['tests_run'], report['failures'], report['errors']), (3, 0, 0))
        failing = dict(passing, **{'test_fx_one_failure.py': '''
            import unittest
            class One(unittest.TestCase):
                def test_bad(self):
                    self.assertEqual('a', 'b')
        '''})
        result, report = self.runner(self.tree('bad', failing), '--jobs', '2')
        self.assertEqual(result.returncode, 1)
        self.assertEqual([row['test'] for row in report['failed']], ['test_fx_one_failure.One.test_bad'])

    def test_import_error_alone_fails_the_run(self):
        result, report = self.runner(self.tree('imp', {
            'test_fx_import_error.py': MODULES['test_fx_import_error.py']}))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report['errors'], 1)
        self.assertIn('missing dependency', report['failed'][0]['detail'])


class CrashTests(RunnerCase):
    def test_crashing_module_is_reported_and_other_modules_still_run(self):
        start = self.tree('crash', {
            'test_fx_pass.py': MODULES['test_fx_pass.py'],
            'test_fx_crash.py': '''
                import os, unittest
                class Crash(unittest.TestCase):
                    def test_a_first(self):
                        pass
                    def test_b_exits(self):
                        os._exit(7)
                    def test_c_never(self):
                        pass
            '''})
        result, report = self.runner(start, '--jobs', '2')
        self.assertEqual(result.returncode, 1)
        [problem] = report['module_problems']
        self.assertEqual((problem['module'], problem['kind']), ('test_fx_crash', 'crash'))
        self.assertIn('exit status 7', problem['detail'])
        self.assertIn('running test_fx_crash.Crash.test_b_exits', problem['detail'])
        self.assertIn('1 of 3 tests never started', problem['detail'])
        self.assertIn(['test_fx_crash.Crash.test_a_first', 'passed'],
                      [[r['test'], r['status']] for r in report['results']])
        self.assertIn('test_fx_pass.PassTests.test_one',
                      [r['test'] for r in report['results'] if r['status'] == 'passed'])
        self.assertIn('MODULE CRASH: test_fx_crash', result.stdout)

    def test_hanging_module_is_killed_at_the_timeout(self):
        start = self.tree('hang', {'test_fx_hang.py': '''
            import time, unittest
            class Hang(unittest.TestCase):
                def test_sleeps(self):
                    time.sleep(60)
        '''})
        result, report = self.runner(start, '--module-timeout', '2')
        self.assertEqual(result.returncode, 1)
        [problem] = report['module_problems']
        self.assertEqual(problem['kind'], 'timeout')
        self.assertIn('running test_fx_hang.Hang.test_sleeps', problem['detail'])

    def test_worker_refuses_a_module_whose_tests_differ_from_discovery(self):
        start = self.tree('drift', {'test_fx_drift.py': '''
            import os, unittest
            from pathlib import Path
            counter = Path(os.environ['FX_COUNTER'])
            count = int(counter.read_text()) + 1 if counter.exists() else 1
            counter.write_text(str(count))
            class Drift(unittest.TestCase):
                pass
            setattr(Drift, 'test_load_%d' % count, lambda self: None)
        '''})
        result, report = self.runner(start, env={'FX_COUNTER': str(self.tmp / 'counter')})
        self.assertEqual(result.returncode, 1)
        [problem] = report['module_problems']
        self.assertEqual(problem['kind'], 'discovery-mismatch')
        self.assertIn('test_load_2', problem['detail'])
        self.assertEqual(report['tests_run'], 0)


class SkipTests(RunnerCase):
    FILES = {'test_fx_skips.py': '''
        import unittest
        class Skips(unittest.TestCase):
            def test_tool(self):
                self.skipTest('no tool')
            @unittest.skipIf(True, 'not this host')
            def test_host(self):
                pass
            def test_runs(self):
                pass
    '''}

    def allowlist(self, *lines):
        path = self.tmp / ('allow-%d.txt' % len(list(self.tmp.glob('allow-*.txt'))))
        path.write_text('# comment\n\n' + ''.join(line + '\n' for line in lines), encoding='utf-8')
        return path

    def test_skips_are_counted_and_named(self):
        result, report = self.runner(self.tree('skip', self.FILES))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((report['tests_run'], report['skipped']), (3, 2))
        self.assertEqual(report['skips'], [
            dict(test='test_fx_skips.Skips.test_host', reason='not this host'),
            dict(test='test_fx_skips.Skips.test_tool', reason='no tool')])
        self.assertIn('test_fx_skips.Skips.test_tool | no tool', result.stdout)

    def test_allowlist_fails_unlisted_or_changed_skips(self):
        start = self.tree('skip', self.FILES)
        both = self.allowlist('test_fx_skips.Skips.test_tool | no tool | fixture',
                              'test_fx_skips.Skips.test_host | not this host | fixture')
        result, report = self.runner(start, '--skip-allowlist', str(both))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(report['unexpected_skips'], 0)
        one = self.allowlist('test_fx_skips.Skips.test_tool | no tool | fixture')
        result, report = self.runner(start, '--skip-allowlist', str(one))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report['unexpected_skips'], 1)
        self.assertIn('SKIP-UNEXPECTED test_fx_skips.Skips.test_host', result.stdout)
        changed = self.allowlist('test_fx_skips.Skips.test_tool | another reason | fixture',
                                 'test_fx_skips.Skips.test_host | not this host | fixture',
                                 'test_fx_skips.Skips.test_gone | gone | fixture')
        result, report = self.runner(start, '--skip-allowlist', str(changed))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report['unexpected_skips'], 1)
        self.assertEqual(report['allowlist_unused'], ['test_fx_skips.Skips.test_gone'])

    def test_malformed_allowlist_is_rejected(self):
        with self.assertRaises(ValueError):
            run_tests.read_allowlist(self.allowlist('test_only_an_id'))


class JobsTests(RunnerCase):
    def test_jobs_value_is_used_exactly_and_bounds_concurrency(self):
        files = {'test_fx_slow_%d.py' % n: '''
            import os, time, unittest
            from pathlib import Path
            class Slow(unittest.TestCase):
                def test_sleep(self):
                    began = time.time()
                    time.sleep(0.4)
                    log = Path(os.environ['FX_SPANS']) / ('%d-%s' % (os.getpid(), __name__))
                    log.write_text('%r %r' % (began, time.time()))
        ''' for n in range(6)}
        start = self.tree('slow', files)
        for jobs in (1, 2):
            spans = self.tmp / ('spans-%d' % jobs)
            spans.mkdir()
            result, report = self.runner(start, '--jobs', str(jobs), env={'FX_SPANS': str(spans)})
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(report['jobs'], jobs)
            times = [tuple(map(float, p.read_text().split())) for p in spans.iterdir()]
            self.assertEqual(len(times), 6)
            overlap = max(sum(1 for b, e in times if b <= t < e) for t, _ in times)
            self.assertLessEqual(overlap, jobs)
            if jobs == 1:
                self.assertEqual(overlap, 1)
        self.assertIn('on 2 workers', result.stdout)

    def test_invalid_job_counts_are_refused(self):
        start = self.tree('fx', {'test_fx_pass.py': MODULES['test_fx_pass.py']})
        for value in ('0', '-1', 'many'):
            result, _ = self.runner(start, '--jobs', value)
            self.assertEqual(result.returncode, 2, value)
        with self.assertRaises(ValueError):
            run_tests.run(str(start), jobs=0)


class SchedulingTests(RunnerCase):
    def test_longest_first_from_records_then_test_counts(self):
        modules = {'a': ['a.T.t1'], 'b': ['b.T.t1', 'b.T.t2'], 'c': ['c.T.t1'], 'empty': []}
        tasks = run_tests.plan_tasks(modules, set(), {'a': 1.0, 'c': 5.0}, jobs=4, split_above=0)
        # Unrecorded b: 2 tests at the mean recorded rate (6 s over 2 tests) = 6 s.
        self.assertEqual([(t[0], t[4]) for t in tasks], [('b', 6.0), ('c', 5.0), ('a', 1.0)])
        self.assertTrue(all(t[2] == 1 and t[3] is None for t in tasks))

    def test_only_recorded_fixture_free_long_modules_are_split(self):
        ids = ['m.T.test_%d' % n for n in range(5)]
        modules = {'m': ids, 'fixtures': ['fixtures.T.t'] * 1, 'unrecorded': ids[:1]}
        tasks = run_tests.plan_tasks(modules, {'m', 'unrecorded'}, {'m': 40.0, 'fixtures': 40.0},
                                     jobs=3, split_above=10)
        shards = [t for t in tasks if t[0] == 'm']
        self.assertEqual(len(shards), 3)
        self.assertEqual(sorted(i for t in shards for i in t[3]), sorted(ids))
        self.assertEqual([t[2] for t in tasks if t[0] == 'fixtures'], [1])
        self.assertEqual([t[2] for t in tasks if t[0] == 'unrecorded'], [1])
        self.assertEqual(len(run_tests.plan_tasks(modules, {'m'}, {'m': 40.0}, 3, 0)), 3)

    def test_split_module_gives_the_same_outcomes_and_class_fixtures_stay_whole(self):
        files = {
            'test_fx_many.py': 'import unittest\nclass Many(unittest.TestCase):\n' + ''.join(
                '    def test_%02d(self):\n        self.assertNotEqual(%d, 3)\n' % (n, n) for n in range(8)),
            'test_fx_fixture.py': '''
                import os, unittest
                from pathlib import Path
                class Fixture(unittest.TestCase):
                    @classmethod
                    def setUpClass(cls):
                        marker = Path(os.environ['FX_MARK']) / str(os.getpid())
                        marker.write_text('x')
                    def test_a(self):
                        pass
                    def test_b(self):
                        pass
            '''}
        start = self.tree('split', files)
        timings = self.tmp / 'timings.json'
        timings.write_text(json.dumps({'modules': {'test_fx_many': 60, 'test_fx_fixture': 60}}))
        marks = self.tmp / 'marks'
        marks.mkdir()
        env = {'FX_MARK': str(marks)}
        _, whole = self.runner(start, '--split-above', '0', '--timings', str(timings), env=env)
        _, split = self.runner(start, '--jobs', '4', '--timings', str(timings), env=env)
        self.assertEqual(split['split'], {'test_fx_many': 4})
        self.assertEqual(whole['split'], {})
        self.assertEqual(split['results'], whole['results'])
        self.assertEqual([r['test'] for r in split['failed']], ['test_fx_many.Many.test_03'])
        self.assertEqual(len(list(marks.iterdir())), 2)  # One fixture process per run.
        recorded = self.tmp / 'recorded.json'
        self.runner(start, '--record-timings', str(recorded))
        self.assertEqual(sorted(json.loads(recorded.read_text())['modules']),
                         ['test_fx_fixture', 'test_fx_many'])

    def test_repository_timings_file_is_readable(self):
        timings = run_tests.load_timings(ROOT / 'tests' / run_tests.TIMINGS_NAME)
        self.assertTrue(timings)
        self.assertTrue(all(value >= 0 for value in timings.values()))


if __name__ == '__main__':
    unittest.main()
