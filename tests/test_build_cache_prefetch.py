"""The reuse check's speed-ups give the same answers (BUILD-REUSE-CHECK-ONE-CORE-59): the stage source selections
worked out in worker processes equal the serial ones (tools/fingerprint_prefetch.py, opt-in), and the check's second
identical reuse preflight is a copy of the first only while build.py --check / --plan says so.

The build's pre-flight (BUILD-PREFLIGHT-SERIAL-REPEATED-66): the stage source analysis on the pool gives the serial
path's answers, the analysis kept for a source tree is taken by the next check or build of the same tree with the
same answers, a changed file or index form is worked out again, and an environment switch still changes the stage
keys when the analysis is taken."""
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import build_cache  # noqa: E402
import fingerprint_prefetch  # noqa: E402

SCRIPTS = [ROOT / 'tools' / name for name in ('size_ledger.py', 'ide_cylinders.py', 'perf_guard.py')]


class PreflightOnceTests(unittest.TestCase):
    def run_twice(self, once):
        calls = []

        def fake_predict(*args, **kwargs):
            calls.append(1)
            return {'b': 'changed'}, {}
        build_cache._PREFLIGHT_DONE.clear()
        with patch.object(build_cache, 'PREFLIGHT_ONCE', once), \
                patch.object(build_cache, 'old_run_steps', return_value=([('a', []), ('b', [])], {})), \
                patch.object(build_cache, 'SourceIndex'), \
                patch.object(build_cache, 'predict', side_effect=fake_predict), \
                patch.object(build_cache, 'run_preflight', side_effect=lambda *a, **k: {'rows': [{'stage': 'b'}]}):
            first = build_cache.predict_preflight('/no/run', 'units', root=ROOT)
            first['rows'].append('changed by a caller')
            second = build_cache.predict_preflight('/no/run', 'units', root=ROOT)
            with patch.dict(os.environ, {'AMIWIND_NPC_ROOT_RULE': 'another'}):
                build_cache.predict_preflight('/no/run', 'units', root=ROOT)
        build_cache._PREFLIGHT_DONE.clear()
        self.assertEqual(second, {'rows': [{'stage': 'b'}]})
        return len(calls)

    def test_a_check_asks_once_per_environment(self):
        self.assertEqual(self.run_twice(True), 2)

    def test_everything_else_asks_every_time(self):
        self.assertFalse(build_cache.PREFLIGHT_ONCE)
        self.assertEqual(self.run_twice(False), 3)


@unittest.skipUnless(hasattr(os, 'fork'), 'worker processes are forked (Linux)')
class PrefetchTests(unittest.TestCase):
    def index(self):
        return build_cache.SourceIndex(ROOT, top_format=build_cache.STAGE_TOP_FORMAT)

    def test_parallel_selections_equal_the_serial_ones(self):
        serial = self.index()
        expected = {s: (serial.selection(s), serial.previous_selections(s)) for s in SCRIPTS}
        parallel = self.index()
        self.assertEqual(fingerprint_prefetch.prefetch_selections(parallel, SCRIPTS, workers=3, log=lambda _: None), 3)
        for script in SCRIPTS:
            self.assertEqual((parallel.selection(script), parallel.previous_selections(script)), expected[script])

    def test_serial_unless_asked(self):
        index = self.index()
        with patch.dict(os.environ, {fingerprint_prefetch.PREFETCH_ENV: ''}):
            self.assertEqual(fingerprint_prefetch.prefetch_selections(index, SCRIPTS), 0)
        self.assertNotIn('_prefetched', index.__dict__)
        self.assertIn(fingerprint_prefetch.PREFETCH_ENV, build_cache.IGNORED_ENV)

    def test_refresh_forgets_the_prefetched_selections(self):
        index = self.index()
        fingerprint_prefetch.prefetch_selections(index, SCRIPTS[:2], workers=2, log=lambda _: None)
        self.assertTrue(index.__dict__.get('_prefetched'))
        index.refresh([])
        self.assertNotIn('_prefetched', index.__dict__)


# a stage script that reaches engine C files too (engine_facts.narrow)
POOL_SCRIPTS = SCRIPTS + [ROOT / 'tools' / 'map_engine_limits.py']


def answers(index, scripts):
    """Every answer a stage key and the stage plan ask the index for, per script."""
    found = {}
    for script in scripts:
        companion = index.companion()
        found[str(script)] = (index.selection(script), index.previous_selections(script),
                              index.environment_names(script), companion.environment_names(script),
                              index.reached_units(script), index.closure(script))
    return found


def worked_out_again(*_, **__):
    raise AssertionError('worked out again although the analysis was taken')


NO_WORK = (patch.object(build_cache.SourceIndex, '_closure_symbols', worked_out_again),
           patch.object(build_cache.SourceIndex, '_selection', worked_out_again))


@unittest.skipUnless(hasattr(os, 'fork'), 'worker processes are forked (Linux)')
class PreflightPoolTests(unittest.TestCase):
    """BUILD-PREFLIGHT-SERIAL-REPEATED-66, on this checkout: the analysis on the pool is the serial path's, and the
    analysis kept in the store gives the same answers again, nothing worked out twice."""

    @classmethod
    def setUpClass(cls):
        fingerprint_prefetch.forget()
        cls.expected = answers(cls.index(), POOL_SCRIPTS)
        cls.pooled = cls.index()
        cls.read = fingerprint_prefetch.analyse(cls.pooled, POOL_SCRIPTS, workers=4)

    @classmethod
    def index(cls):
        return build_cache.SourceIndex(ROOT, top_format=build_cache.STAGE_TOP_FORMAT)

    def setUp(self):
        fingerprint_prefetch.forget()
        self.addCleanup(fingerprint_prefetch.forget)

    def test_the_pool_gives_the_serial_answers(self):
        self.assertGreater(self.read, 0)
        with NO_WORK[0], NO_WORK[1]:
            self.assertEqual(answers(self.pooled, POOL_SCRIPTS), self.expected)

    def test_the_kept_analysis_gives_the_same_answers(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(build_cache, 'ANALYSIS_STORE', Path(folder)):
            key = fingerprint_prefetch.index_key(self.pooled)
            fingerprint_prefetch.Store(folder).save(key, {
                'schema': fingerprint_prefetch.STORE_SCHEMA, 'key': key, 'origin': {'kind': 'check', 'run': 'r'},
                'states': [fingerprint_prefetch.memo_state(ix) for ix in fingerprint_prefetch.pair(self.pooled)]})
            taken = self.index()
            fingerprint_prefetch.use_memo(taken)
            self.assertEqual(fingerprint_prefetch.index_key(taken), key)
            self.assertEqual(fingerprint_prefetch.attach(taken, key), {'kind': 'check', 'run': 'r'})
            with NO_WORK[0], NO_WORK[1]:
                self.assertEqual(answers(taken, POOL_SCRIPTS), self.expected)

    def test_the_memo_is_off_unless_the_pre_flight_turns_it_on(self):
        index = self.index()
        index.selection(SCRIPTS[0])
        self.assertIsNone(index._selections)              # a test that edits index.files still gets a new selection
        fingerprint_prefetch.use_memo(index)
        index.selection(SCRIPTS[0])
        self.assertEqual(len(index._selections), 1)
        index.refresh([])
        self.assertEqual(index._selections, {})

    def test_the_pre_flight_workers_follow_jobs_and_the_cores(self):
        cores = fingerprint_prefetch.usable_cores()
        with patch.dict(os.environ, {fingerprint_prefetch.PREFLIGHT_ENV: ''}):
            self.assertEqual(fingerprint_prefetch.preflight_workers(1), 1)
            self.assertEqual(fingerprint_prefetch.preflight_workers(10 ** 6), cores)
            self.assertEqual(fingerprint_prefetch.preflight_workers(None), cores)
        with patch.dict(os.environ, {fingerprint_prefetch.PREFLIGHT_ENV: '1'}):
            self.assertEqual(fingerprint_prefetch.preflight_workers(24), 1)
        self.assertIn(fingerprint_prefetch.PREFLIGHT_ENV, build_cache.IGNORED_ENV)


@unittest.skipUnless(hasattr(os, 'fork'), 'worker processes are forked (Linux)')
class PreflightStoreTests(unittest.TestCase):
    """BUILD-PREFLIGHT-SERIAL-REPEATED-66: once per source tree; any difference in the key is worked out again."""

    def setUp(self):
        fingerprint_prefetch.forget()
        self.addCleanup(fingerprint_prefetch.forget)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Path(self.temp.name) / 'store'
        for name, value in (('ANALYSIS_STORE', self.store), ('PREFLIGHT_WORKERS', 2),
                            ('ANALYSIS_ORIGIN', {'kind': 'check', 'run': 'the-check-run'})):
            patcher = patch.object(build_cache, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.lines = []

    def prepared(self, root, scripts, **options):
        index = build_cache.SourceIndex(root, top_format=build_cache.STAGE_TOP_FORMAT, **options)
        fingerprint_prefetch.prepare_index(index, scripts, log=self.lines.append)
        return index

    def keep(self):
        written = fingerprint_prefetch.save_analyses(log=self.lines.append)
        fingerprint_prefetch.forget()          # the next check or build is another process
        return written

    def repository(self):
        from test_build_cache import make_repository
        repository = Path(self.temp.name) / 'repo'
        make_repository(repository)
        return repository, [repository / 'tools' / name for name in ('stage_a.py', 'stage_b.py', 'stage_e.py')]

    def test_the_kept_analysis_is_taken_with_the_same_answers(self):
        repository, scripts = self.repository()
        expected = answers(self.prepared(repository, scripts), scripts)
        self.assertIn('computed', self.lines[-1])
        self.assertEqual(len(self.keep()), 1)
        with NO_WORK[0], NO_WORK[1]:
            taken = self.prepared(repository, scripts)
            self.assertEqual(answers(taken, scripts), expected)
        self.assertIn('taken from the check of', self.lines[-1])
        self.assertIn('the-check-run', self.lines[-1])
        self.assertEqual(self.keep(), [])     # nothing new: nothing written again

    def test_a_damaged_entry_is_worked_out_again(self):
        repository, scripts = self.repository()
        self.prepared(repository, scripts)
        path, = self.keep()
        path.write_bytes(path.read_bytes()[:-10] + b'0123456789')
        self.prepared(repository, scripts)
        self.assertIn('computed', self.lines[-1])
        self.assertNotIn('taken', self.lines[-1])

    def test_a_changed_file_or_form_is_a_new_key(self):
        repository, scripts = self.repository()
        scripts = scripts[:1]
        first = self.prepared(repository, scripts)
        key = fingerprint_prefetch.index_key(first)
        before = first.digest(scripts[0])
        self.keep()
        self.assertEqual(fingerprint_prefetch.index_key(build_cache.SourceIndex(
            repository, top_format=build_cache.STAGE_TOP_FORMAT)), key)
        for options in ({'scope': 'symbols'}, {'engine_facts': False}, {'content_keyed': False}):
            self.assertNotEqual(fingerprint_prefetch.index_key(build_cache.SourceIndex(
                repository, top_format=build_cache.STAGE_TOP_FORMAT, **options)), key, options)
        (repository / 'tools' / 'helper.py').write_text((repository / 'tools' / 'helper.py').read_text()
                                                       .replace("name + ':'", "name + '='"))
        again = self.prepared(repository, scripts)
        self.assertNotEqual(fingerprint_prefetch.index_key(again), key)
        self.assertNotIn('taken', self.lines[-1])
        self.assertNotEqual(again.digest(scripts[0]), before)

    def test_an_environment_switch_still_changes_the_stage_key(self):
        from test_build_cache import make_repository, metadata
        repository = Path(self.temp.name) / 'repo'
        make_repository(repository)
        run = Path(self.temp.name) / 'run'
        steps = [('alpha', [sys.executable, str(repository / 'tools' / 'stage_a.py'), '--out', str(run / 'a')]),
                 ('epsilon', [sys.executable, str(repository / 'tools' / 'stage_e.py'), '--out', str(run / 'e')])]

        def keys(value):
            index = build_cache.SourceIndex(repository, top_format=build_cache.STAGE_TOP_FORMAT)
            log = io.StringIO()
            with patch.dict(os.environ, {'AMIWIND_STAIR_MITIGATION': value}), contextlib.redirect_stderr(log):
                return build_cache.fingerprint_steps(steps, run, metadata(), index)[0], log.getvalue()
        on, log = keys('on')
        self.assertIn('Pre-flight: stage source analysis computed', log)
        self.keep()
        off, log = keys('off')
        self.assertIn('Pre-flight: stage source analysis taken from the check of', log)
        self.assertNotEqual(on['epsilon'], off['epsilon'])     # the switch's value counts in the key, as before
        self.assertEqual(on['alpha'], off['alpha'])
        with patch.object(build_cache, 'ANALYSIS_STORE', None), patch.object(build_cache, 'PREFLIGHT_WORKERS', None):
            fingerprint_prefetch.forget()
            self.assertEqual(keys('off'), (off, ''))     # the serial path without any store: the same keys


if __name__ == '__main__':
    unittest.main()
