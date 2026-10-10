#!/usr/bin/env python3
"""Run the unittest suite in parallel worker processes, one test module per process.

Discovery is exactly ``python -m unittest discover -s tests -p 'test*.py'``:
the same loader, start directory and pattern, and the same import path
(current directory, then the start directory). Each discovered module then
runs in a fresh interpreter of its own and never shares a process with
another module. The worker reloads the module the way discovery did and
refuses to run if it finds a different set of test IDs.

Longest modules start first, using recorded per-module seconds (the timings
file next to the tests, or --timings) and test counts for modules without a
record. A module whose recorded time exceeds --split-above and that has no
module- or class-level fixtures is split into shards of its own tests, each
shard again in a fresh process, so one long module does not set the wall time.

One merged report follows: tests run, failures, errors, skips (with names and
reasons) and per-module timings. The exit status is nonzero on any failure,
error, unexpected success, crashed or timed-out module, discovery mismatch, or
(with --skip-allowlist) any skip not listed with its exact reason.
"""
import argparse
import collections
import concurrent.futures
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

DEFAULT_PATTERN = 'test*.py'
TIMINGS_NAME = 'module-timings.json'
FAILING = ('failed', 'error', 'unexpected_success')
HERE = os.path.dirname(os.path.abspath(__file__))


# ----------------------------------------------------------------- discovery
def mirror_unittest_path(start_dir):
    """Import path of ``python -m unittest discover -s START`` in this process.

    ``-m`` puts the current directory first where a script would put its own
    folder; discovery then inserts the top-level directory in front.
    """
    cwd = os.getcwd()
    if sys.path and sys.path[0] in ('', HERE):
        sys.path[0] = cwd
    elif cwd not in sys.path:
        sys.path.insert(0, cwd)
    top = os.path.abspath(start_dir)
    if top not in sys.path:
        sys.path.insert(0, top)
    return top


class _ModuleTaggingLoader(unittest.TestLoader):
    """The stock loader, remembering which module produced each suite."""

    def loadTestsFromModule(self, module, *args, **kwargs):
        suite = super().loadTestsFromModule(module, *args, **kwargs)
        suite._run_tests_module = module
        return suite


def iter_tests(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from iter_tests(item)
        else:
            yield item


def _has_fixtures(module, tests):
    """Module or class fixtures would run once per shard: never split those."""
    if module is None or hasattr(module, 'setUpModule') or hasattr(module, 'tearDownModule'):
        return True
    base = unittest.TestCase
    return any(getattr(type(test), name).__func__ is not getattr(base, name).__func__
               for test in tests for name in ('setUpClass', 'tearDownClass'))


def discover_modules(start_dir='tests', pattern=DEFAULT_PATTERN):
    """Return ({module: [test ids]}, {modules that may be split}) in discovery order."""
    mirror_unittest_path(start_dir)
    top = _ModuleTaggingLoader().discover(start_dir, pattern=pattern)
    modules, splittable = collections.OrderedDict(), set()
    for suite in top:
        tests = list(iter_tests(suite))
        module = getattr(suite, '_run_tests_module', None)
        if module is not None:
            name = module.__name__
        elif len(tests) == 1 and type(tests[0]).__module__ == 'unittest.loader':
            # Import failures and module-level SkipTest become one synthetic
            # test (unittest.loader._FailedTest / ModuleSkipped) named after the module.
            name = tests[0]._testMethodName
        else:
            raise RuntimeError('cannot attribute a discovered suite to a module: %r' % tests)
        if name in modules:
            raise RuntimeError('module discovered twice: ' + name)
        modules[name] = [test.id() for test in tests]
        if not _has_fixtures(module, tests):
            splittable.add(name)
    return modules, splittable


def discover(start_dir='tests', pattern=DEFAULT_PATTERN):
    """Return {module name: [test ids]} in discovery order."""
    return discover_modules(start_dir, pattern)[0]


def serial_discovery_ids(start_dir='tests', pattern=DEFAULT_PATTERN):
    """Sorted test IDs exactly as the stock serial loader sees them."""
    mirror_unittest_path(start_dir)
    suite = unittest.TestLoader().discover(start_dir, pattern=pattern)
    return sorted(test.id() for test in iter_tests(suite))


# -------------------------------------------------------------------- worker
class _EventResult(unittest.TextTestResult):
    """Text result that also appends one JSON line per event (crash safe)."""

    def __init__(self, stream, descriptions, verbosity, events=None, **kwargs):
        super().__init__(stream, descriptions, verbosity, **kwargs)
        self._events = events
        self._started = {}

    def _emit(self, **row):
        self._events.write(json.dumps(row) + '\n')
        self._events.flush()

    def _result(self, test, status, detail=None):
        row = dict(event='result', id=test.id(), status=status)
        began = self._started.get(test.id())
        if began is not None:
            row['seconds'] = round(time.monotonic() - began, 4)
        if detail is not None:
            row['detail'] = detail
        self._emit(**row)

    def startTest(self, test):
        super().startTest(test)
        self._started[test.id()] = time.monotonic()
        self._emit(event='start', id=test.id())

    def addSuccess(self, test):
        super().addSuccess(test)
        self._result(test, 'passed')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._result(test, 'failed', self.failures[-1][1])

    def addError(self, test, err):
        super().addError(test, err)
        self._result(test, 'error', self.errors[-1][1])

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._result(test, 'skipped', str(reason))

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._result(test, 'expected_failure')

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._result(test, 'unexpected_success')

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            failed = issubclass(err[0], test.failureException)
            self._result(subtest, 'failed' if failed else 'error',
                         (self.failures if failed else self.errors)[-1][1])


def _keep(suite, wanted, suite_class):
    """Copy of the suite structure (classes intact) holding only wanted tests."""
    kept = suite_class()
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            child = _keep(item, wanted, suite_class)
            if child.countTestCases():
                kept.addTest(child)
        elif item.id() in wanted:
            kept.addTest(item)
    return kept


def _install_env_guard():
    """The suite-wide AMIWIND_* leak guard (tests/env_guard.py) in this worker; one-process discovery gets it from
    tests/test_env_guard.py (TEST-ENV-LEAK-HULL-33)."""
    try:
        import env_guard
    except ImportError:
        return False
    return env_guard.install()


def worker(module, start_dir, pattern, events_path, plan_path):
    """Load one module as discovery does, check its IDs, run (a shard of) it."""
    mirror_unittest_path(start_dir)
    _install_env_guard()
    plan = json.loads(Path(plan_path).read_text(encoding='utf-8'))
    loader = unittest.TestLoader()
    with open(events_path, 'w', encoding='utf-8', newline='\n') as events:
        def emit(**row):
            events.write(json.dumps(row) + '\n')
            events.flush()
        try:
            __import__(module)
            suite = loader.loadTestsFromModule(sys.modules[module], pattern=pattern)
        except unittest.SkipTest as exc:
            suite = unittest.loader._make_skipped_test(module, exc, loader.suiteClass)
        except:  # noqa: E722 - the same bare handler discovery uses for import failures
            suite, message = unittest.loader._make_failed_import_test(module, loader.suiteClass)
            sys.stderr.write(message + '\n')
        ids = sorted(test.id() for test in iter_tests(suite))
        if ids != sorted(plan['module_ids']):
            emit(event='mismatch', loaded=ids, expected=sorted(plan['module_ids']))
            return 3
        if plan['run_ids'] is not None:
            suite = _keep(suite, set(plan['run_ids']), loader.suiteClass)
        emit(event='loaded', count=suite.countTestCases())
        runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=2,
                                         resultclass=lambda *a, **k: _EventResult(*a, events=events, **k))
        result = runner.run(suite)
        emit(event='done', tests_run=result.testsRun)
    return 0


# ---------------------------------------------------------------- scheduling
def load_timings(path):
    if not path:
        return {}
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        raise ValueError('unreadable timings file %s: %s' % (path, exc)) from None
    modules = data.get('modules', data) if isinstance(data, dict) else {}
    return {str(k): float(v) for k, v in modules.items() if isinstance(v, (int, float))}


def plan_tasks(modules, splittable, timings, jobs, split_above):
    """Longest-first list of (module, shard, shards, ids or None, estimate).

    Modules without a record are estimated from their test count at the mean
    recorded rate. Only recorded, fixture-free modules longer than split_above
    seconds are split, into at most ``jobs`` shards of round-robin test IDs.
    """
    known = [(timings[m], len(ids)) for m, ids in modules.items() if m in timings and ids]
    rate = (sum(s for s, _ in known) / max(1, sum(n for _, n in known))) if known else 0.1
    tasks = []
    for module, ids in modules.items():
        if not ids:
            continue  # Nothing to run; a load failure is itself a (synthetic) test.
        estimate = timings.get(module, len(ids) * rate)
        shards = 1
        if split_above and module in timings and module in splittable:
            shards = max(1, min(len(ids), jobs, math.ceil(estimate / split_above)))
        ordered = sorted(ids)
        for shard in range(shards):
            subset = None if shards == 1 else ordered[shard::shards]
            tasks.append((module, shard, shards, subset, estimate / shards))
    tasks.sort(key=lambda t: (-t[4], t[0], t[1]))
    return tasks


# -------------------------------------------------------------------- parent
def read_allowlist(path):
    """Gate format: ``test id | exact skip reason | why it is allowed``."""
    allow = {}
    for number, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        parts = [part.strip() for part in line.split(' | ')]
        if len(parts) != 3 or not all(parts):
            raise ValueError('%s:%d: expected "test id | reason | why"' % (path, number))
        allow[parts[0]] = parts[1]
    return allow


def _run_task(task, module_ids, start_dir, pattern, timeout, scratch, python_flags):
    module, shard, shards, subset, _ = task
    # The worker inherits the caller's environment, TMPDIR included, exactly as
    # a serial run would; only the runner's own files live in scratch.
    folder = Path(tempfile.mkdtemp(prefix='w-', dir=scratch))
    plan, events, log = folder / 'plan.json', folder / 'events.jsonl', folder / 'output.log'
    plan.write_text(json.dumps(dict(module_ids=module_ids, run_ids=subset)),
                    encoding='utf-8', newline='\n')
    command = [sys.executable, *python_flags, os.path.join(HERE, 'run_tests.py'), '--worker', module,
               '--start-dir', os.path.abspath(start_dir), '--pattern', pattern,
               '--events', str(events), '--plan', str(plan)]
    began = time.monotonic()
    timed_out = False
    with log.open('wb') as output:
        process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT)
        try:
            code = process.wait(timeout=timeout or None)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            code = process.wait()
    seconds = time.monotonic() - began
    rows = []
    if events.is_file():
        for line in events.read_text(encoding='utf-8', errors='replace').splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass  # A torn last line after a crash; the crash itself is reported.
    text = log.read_text(encoding='utf-8', errors='replace')
    shutil.rmtree(folder, ignore_errors=True)
    expected = len(module_ids) if subset is None else len(subset)
    return dict(module=module, shard=shard, shards=shards, code=code, seconds=seconds,
                rows=rows, log=text, timed_out=timed_out, expected=expected)


def _label(outcome):
    if outcome['shards'] == 1:
        return outcome['module']
    return '%s [shard %d/%d]' % (outcome['module'], outcome['shard'] + 1, outcome['shards'])


def summarise(outcomes, allow=None):
    """Merge worker outcomes into one deterministic report (sorted by ID)."""
    results, problems = [], []
    module_seconds = collections.defaultdict(float)
    tests_run = 0
    for outcome in sorted(outcomes, key=lambda o: (o['module'], o['shard'])):
        module_seconds[outcome['module']] += outcome['seconds']
        rows = outcome['rows']
        started = [r['id'] for r in rows if r.get('event') == 'start']
        finished = {r['id'] for r in rows if r.get('event') == 'result'}
        tests_run += len(started)
        results += [r for r in rows if r.get('event') == 'result']
        done = any(r.get('event') == 'done' for r in rows)
        mismatch = [r for r in rows if r.get('event') == 'mismatch']
        if mismatch:
            loaded, expected = set(mismatch[0]['loaded']), set(mismatch[0]['expected'])
            problems.append(dict(module=_label(outcome), kind='discovery-mismatch',
                                 detail='only in worker: %s; only in discovery: %s' % (
                                     sorted(loaded - expected), sorted(expected - loaded))))
        elif outcome['timed_out'] or outcome['code'] != 0 or not done:
            running = [t for t in started if t not in finished]
            detail = 'exit status %s' % outcome['code']
            if running:
                detail += '; running %s' % running[-1]
            if outcome['expected'] > len(started):
                detail += '; %d of %d tests never started' % (outcome['expected'] - len(started),
                                                               outcome['expected'])
            problems.append(dict(module=_label(outcome), kind='timeout' if outcome['timed_out'] else 'crash',
                                 detail=detail, log_tail=outcome['log'][-4000:]))
    results.sort(key=lambda r: (r['id'], r['status']))
    by = collections.defaultdict(list)
    for row in results:
        by[row['status']].append(row)
    skips = [dict(test=r['id'], reason=r.get('detail', '')) for r in by['skipped']]
    unexpected, unused = [], []
    if allow is not None:
        for row in skips:
            row['allowed'] = allow.get(row['test']) == row['reason']
        unexpected = [row for row in skips if not row['allowed']]
        unused = sorted(set(allow) - {row['test'] for row in skips})
    successful = not problems and not any(by[s] for s in FAILING) and not unexpected
    return dict(
        tests_run=tests_run, passed=len(by['passed']), failures=len(by['failed']),
        errors=len(by['error']), skipped=len(skips), expected_failures=len(by['expected_failure']),
        unexpected_successes=len(by['unexpected_success']), module_problems=problems,
        unexpected_skips=len(unexpected) if allow is not None else None,
        allowlist_unused=unused, skips=skips,
        failed=[dict(test=r['id'], status=r['status'], detail=r.get('detail', ''))
                for s in FAILING for r in by[s]],
        results=[dict(test=r['id'], status=r['status']) for r in results],
        module_seconds={m: round(s, 3) for m, s in sorted(module_seconds.items())},
        successful=successful)


def print_report(report, outcomes, verbose, stream=None):
    write = (stream or sys.stdout).write
    if verbose:
        for outcome in sorted(outcomes, key=lambda o: (o['module'], o['shard'])):
            write('\n===== %s (%.2f s) =====\n%s' % (_label(outcome), outcome['seconds'], outcome['log']))
    for row in report['failed']:
        write('\n%s: %s\n%s\n' % (row['status'].upper().replace('_', ' '), row['test'], row['detail']))
    for problem in report['module_problems']:
        write('\nMODULE %s: %s (%s)\n' % (problem['kind'].upper(), problem['module'], problem['detail']))
        if problem.get('log_tail') and not verbose:
            write(problem['log_tail'] + '\n')
    write('\nSkipped tests (%d):\n' % report['skipped'])
    for row in report['skips']:
        mark = '' if row.get('allowed', True) else 'SKIP-UNEXPECTED '
        write('  %s%s | %s\n' % (mark, row['test'], row['reason']))
    for name in report['allowlist_unused']:
        write('  ALLOW-UNUSED %s\n' % name)
    slowest = sorted(report['module_seconds'].items(), key=lambda kv: (-kv[1], kv[0]))
    shown = slowest if verbose else slowest[:15]
    split = {o['module']: o['shards'] for o in outcomes if o['shards'] > 1}
    write('\nModule durations (%s of %d, longest first; split modules summed over shards):\n' % (
        'all' if verbose else 'top %d' % len(shown), len(slowest)))
    for module, seconds in shown:
        write('  %8.2f s  %s%s\n' % (seconds, module,
                                     ' (%d shards)' % split[module] if module in split else ''))
    write('\nRan %d tests in %d modules (%d processes) on %d workers in %.1f s; '
          'sum of process time %.1f s\n' % (
              report['tests_run'], report['modules'], len(outcomes), report['jobs'],
              report['seconds'], sum(o['seconds'] for o in outcomes)))
    parts = ['failures=%d' % report['failures'], 'errors=%d' % report['errors'],
             'skipped=%d' % report['skipped']]
    if report['expected_failures']:
        parts.append('expected failures=%d' % report['expected_failures'])
    if report['unexpected_successes']:
        parts.append('unexpected successes=%d' % report['unexpected_successes'])
    if report['module_problems']:
        parts.append('module problems=%d' % len(report['module_problems']))
    if report['unexpected_skips']:
        parts.append('unexpected skips=%d' % report['unexpected_skips'])
    write(('OK' if report['successful'] else 'FAILED') + ' (' + ', '.join(parts) + ')\n')
    (stream or sys.stdout).flush()


def run(start_dir='tests', pattern=DEFAULT_PATTERN, jobs=1, timings=None, split_above=0,
        module_timeout=0, allowlist=None, progress=None):
    """Discover, run in parallel and return (report, outcomes).

    ``timings`` is a path; None reads the timings file in start_dir when present.
    """
    if jobs < 1:
        raise ValueError('jobs must be at least 1')
    began = time.monotonic()
    allow = read_allowlist(allowlist) if allowlist else None
    modules, splittable = discover_modules(start_dir, pattern)
    if timings is None:
        timings = os.path.join(start_dir, TIMINGS_NAME)
    tasks = plan_tasks(modules, splittable, load_timings(timings), jobs, split_above)
    python_flags = ['-B'] if sys.dont_write_bytecode else []
    outcomes = []
    scratch = tempfile.mkdtemp(prefix='amiwind-tests-')
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = [pool.submit(_run_task, task, modules[task[0]], start_dir, pattern,
                                   module_timeout, scratch, python_flags) for task in tasks]
            for future in concurrent.futures.as_completed(futures):
                outcomes.append(future.result())
                if progress:
                    progress(len(outcomes), len(tasks), outcomes[-1])
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    report = summarise(outcomes, allow)
    report.update(jobs=jobs, seconds=round(time.monotonic() - began, 3), modules=len(modules),
                  discovered=sum(len(ids) for ids in modules.values()), processes=len(tasks),
                  split={t[0]: t[2] for t in tasks if t[2] > 1})
    return report, outcomes


def write_timings(path, report):
    timings = load_timings(path)
    timings.update(report['module_seconds'])
    Path(path).write_text(json.dumps(dict(modules=dict(sorted(timings.items()))), indent=1) + '\n',
                          encoding='utf-8', newline='\n')


def _worker_main(argv):
    parser = argparse.ArgumentParser(add_help=False)
    for name in ('--worker', '--start-dir', '--pattern', '--events', '--plan'):
        parser.add_argument(name, required=True)
    args = parser.parse_args(argv)
    return worker(args.worker, args.start_dir, args.pattern, args.events, args.plan)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ['--worker']:
        # Nothing beyond the standard library is imported before the tests.
        return _worker_main(argv)
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('-s', '--start-dir', default='tests')
    parser.add_argument('-p', '--pattern', default=DEFAULT_PATTERN)
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Print every module's full output and all module durations")
    parser.add_argument('--skip-allowlist', type=Path,
                        help='Fail on any skip not listed here with its exact reason')
    parser.add_argument('--timings', type=Path,
                        help='Recorded per-module seconds for scheduling (default: %s in the start '
                             'directory, when present)' % TIMINGS_NAME)
    parser.add_argument('--record-timings', type=Path,
                        help="Merge this run's per-module seconds into this file")
    parser.add_argument('--split-above', type=float, default=10.0, metavar='SECONDS',
                        help='Split recorded, fixture-free modules longer than this (0: never; default 10)')
    parser.add_argument('--json', type=Path, help='Write the merged report as JSON')
    parser.add_argument('--module-timeout', type=float, default=0, metavar='SECONDS',
                        help='Kill a worker process after this long (default: no limit)')
    parser.add_argument('--list', action='store_true', help='Print discovered test IDs and exit')
    sys.path.insert(1, HERE)
    try:
        from build_jobs import add_jobs, resolve_jobs
    finally:
        sys.path.pop(1)
    add_jobs(parser)
    args = parser.parse_args(argv)
    if args.split_above < 0:
        parser.error('--split-above must not be negative')
    if args.list:
        for ids in discover(args.start_dir, args.pattern).values():
            for test in ids:
                print(test)
        return 0
    jobs = resolve_jobs(args.jobs)

    def progress(done, total, outcome):
        bad = any(r.get('event') == 'result' and r['status'] in FAILING for r in outcome['rows'])
        state = 'ok' if outcome['code'] == 0 and not bad else 'FAIL'
        print('[%3d/%d] %-4s %7.2f s  %s' % (done, total, state, outcome['seconds'], _label(outcome)),
              flush=True)

    report, outcomes = run(args.start_dir, args.pattern, jobs, args.timings, args.split_above,
                           args.module_timeout, args.skip_allowlist, progress)
    print_report(report, outcomes, args.verbose)
    if args.json:
        args.json.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')
    if args.record_timings:
        write_timings(args.record_timings, report)
    return 0 if report['successful'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
