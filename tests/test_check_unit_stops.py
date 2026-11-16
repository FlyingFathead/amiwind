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

    def test_the_check_plans_the_same_commands_as_the_build(self):
        # the second cause of BUILD-REUSE-STOP-COUNTS-STORED-GROUP-64: the build binds the exterior checklist to
        # world-terrain, world-scenery and world-flora (--exterior-plan) and to the image (--exterior-terrain) before
        # it prepares the steps; the check planned the unbound commands, so those three stages read "changed:
        # command" against every earlier build, were counted as rebuilt, and the unit stop counted their stored units
        # (2064 world-scenery regions, 1931 world-flora regions) while the build reused all three
        self.steps = [('world-terrain', ['python3', 'tools/prepare_world_regions.py']),
                      ('world-scenery', ['python3', 'tools/prepare_world_scenery.py']),
                      ('world-flora', ['python3', 'tools/prepare_world_flora.py']),
                      ('image', ['python3', 'tools/build_aga.py', 'image']),
                      ('music', ['python3', 'tools/prepare_music.py'])]
        self.args.exterior_checklist = {'summary': {'chim-region': 1348}}
        seen = {}

        def prepare(steps, run, *a, **kw):
            seen['steps'] = [(name, list(command)) for name, command in steps]
            seen['run'] = run
            return list(steps)
        run = Path(self.tmp.name) / 'build' / 'run'
        code, _ = self.run_check(prepare)
        self.assertEqual(code, 0)
        import exterior_plan
        self.assertEqual(seen['steps'], [(name, list(command)) for name, command in
                                         exterior_plan.bind_steps(self.steps, run / 'exterior-checklist.json')])
        by_name = dict(seen['steps'])
        for name in ('world-terrain', 'world-scenery', 'world-flora'):
            self.assertEqual(by_name[name][-2:], ['--exterior-plan', str(run / 'exterior-checklist.json')])
        self.assertEqual(by_name['image'][-2:], ['--exterior-terrain', str(run / 'world-terrain')])
        self.assertEqual(by_name['music'], ['python3', 'tools/prepare_music.py'])   # every other stage as it was

    def test_a_check_without_a_checklist_plans_the_commands_as_they_are(self):
        self.args.exterior_checklist = None
        seen = {}

        def prepare(steps, *a, **kw):
            seen['steps'] = list(steps)
            return list(steps)
        code, _ = self.run_check(prepare)
        self.assertEqual(code, 0)
        self.assertEqual(seen['steps'], self.steps)

    def test_the_whole_check_output_is_kept_beside_the_result(self):
        # the refusal carries the check's last 40 lines; the plan line of a stopped stage ("rebuild: why") comes
        # earlier, so aw keeps the whole output in RUN.check.log, refused or passed
        import aw_service
        lines = [f'   stage-{n}: reused from run' for n in range(200)] + ['STOP world-scenery: would bake again 2064',
                                                                         'Check FAILED: the build would stop']

        class Runner:
            def capture(self, command, timeout=None):
                return 1, '\n'.join(lines) + '\n', ''
        log = Path(self.tmp.name) / 'logs' / 'run.check.log'
        notes = []
        with contextlib.redirect_stdout(io.StringIO()):
            step, refusals = aw_service.preflight_check({'options': {}}, {'check': ['x']}, Runner(), notes, {},
                                                        full_log=log)
        self.assertEqual(log.read_text(encoding='utf-8').splitlines(), lines)
        self.assertEqual(step['full_output'], str(log))
        self.assertEqual(len(step['output_tail']), aw_service.CHECK_TAIL_LINES)      # the refusal still shows 40
        self.assertTrue(any(str(log) in note for note in notes))
        self.assertTrue(refusals)
        with contextlib.redirect_stdout(io.StringIO()):
            step, _ = aw_service.preflight_check({'options': {}}, {'check': ['x']}, Runner(), [], {})   # no path
        self.assertNotIn('full_output', step)

    def test_the_check_branch_calls_it_before_completing(self):
        text = (ROOT / 'tools/build.py').read_text(encoding='utf-8')
        call = text.index('code = unit_stop_check(args, tools, run)')
        self.assertLess(call, text.index('Checks completed. No build outputs created.', call))


if __name__ == '__main__':
    unittest.main()
