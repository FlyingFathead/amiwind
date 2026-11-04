"""The reuse check's speed-ups give the same answers (BUILD-REUSE-CHECK-ONE-CORE-59): the stage source selections
worked out in worker processes equal the serial ones (tools/fingerprint_prefetch.py, opt-in), and the check's second
identical reuse preflight is a copy of the first only while build.py --check / --plan says so."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
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


if __name__ == '__main__':
    unittest.main()
