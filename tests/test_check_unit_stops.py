# SPDX-License-Identifier: GPL-3.0-only
"""build.py --check runs the build's own reuse stop (PLAN-CHECK-UNIT-STOPS-66): the v0.0.66-dev2 check said 0 unexpected
stages while the build stopped in its first minute on unit-cache STOP lines. With --reuse-from or
--reuse-all-available the check now plans the stages as the build does (build_cache.prepare) and fails with the same
STOP lines when a stage would bake its unit cache again."""
import argparse
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import build  # noqa: E402
import build_cache  # noqa: E402
import reuse_all as RA  # noqa: E402


class CheckRunsTheUnitStop(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.args = argparse.Namespace(reuse_from=None, reuse_all_available=True, reuse_mode='pool', allow_rebuild_map={},
                                       workspace=Path(self.tmp.name), fingerprint_scope='units', rebuild_stage='',
                                       accept_rebuild=False, expansion_layers=None, _input_lock=None, _argv=['--check'])
        self.steps = [('area', ['python3', 'tools/prepare_area.py'])]

    def tearDown(self):
        self.tmp.cleanup()

    def run_check(self, prepare):
        import os
        out = io.StringIO()
        with mock.patch.dict(os.environ), mock.patch.object(build, 'commands', return_value=self.steps), \
                mock.patch.object(build, 'provenance', return_value={}), \
                mock.patch.object(build, 'storage_pool_dir', return_value=Path(self.tmp.name) / 'pool'), \
                mock.patch.object(build_cache, 'prepare', side_effect=prepare), contextlib.redirect_stdout(out):
            code = build.unit_stop_check(self.args, {}, Path(self.tmp.name) / 'build' / 'run')
        return code, out.getvalue()

    def test_a_rekeyed_unit_cache_fails_the_check(self):
        seen = {}

        def prepare(steps, run, metadata, reuse_from=None, mode='copy', reuse_all=None, **kw):
            seen.update(reuse_all=reuse_all, check_only=build_cache.CHECK_ONLY)
            # the build's own minute-one stop, with a unit cache whose stored units this key no longer finds
            build_cache.PLANS[str(run)] = {}
            build_cache.CLOSURES[str(run)] = {'stages': {'area': {'tools/prepare_area.py'}}, 'units': {}}
            with mock.patch.object(RA, 'unit_report', return_value={'area': [('resident-bake', 0, 2147)]}), \
                    mock.patch.object(RA, 'uncached_bakes', return_value=set()):
                build_cache.minute_one(steps, run, metadata, {}, {'area': 'changed: sources'},
                                       mock.Mock(root=ROOT), reuse_all)
        code, out = self.run_check(prepare)
        self.assertEqual(code, build.UNIT_STOP_EXIT)
        self.assertIn('STOP area: would bake again 2147 of the 2147 units its unit cache resident-bake holds', out)
        self.assertIn('Check FAILED', out)
        self.assertTrue(seen['check_only'])                   # no stage index written by a check
        self.assertFalse(build_cache.CHECK_ONLY)
        self.assertEqual(seen['reuse_all']['workspace'], str(Path(self.tmp.name).resolve()))

    def test_no_stop_passes(self):
        code, out = self.run_check(lambda *a, **kw: list(a[0]))
        self.assertEqual(code, 0)
        self.assertIn('passed (no reuse stop)', out)

    def test_the_build_server_reports_the_stop_lines(self):
        # aw's check step (aw_service.parse_check) hands every STOP line and the verdict back to the requester
        import aw_service
        found = aw_service.parse_check('Stage plan\nSTOP area: would bake again 2147 of the 2147 units its unit cache '
                                       'resident-bake holds (100 %, over 5 %)\nSTOP chim: would run the whole stage '
                                       'again\nCheck FAILED: the build would stop before its first stage: Reuse stop')
        self.assertEqual(len(found['stops']), 2)
        self.assertIn('the build would stop', found['error'])
        self.assertFalse(found['completed'])

    def test_the_check_branch_calls_it_before_completing(self):
        text = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        call = text.index('code = unit_stop_check(args, tools, run)')
        self.assertLess(call, text.index('Checks completed. No build outputs created.', call))


if __name__ == '__main__':
    unittest.main()
