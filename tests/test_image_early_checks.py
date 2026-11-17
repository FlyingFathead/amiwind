# SPDX-License-Identifier: GPL-3.0-only
"""The image step's actor frames check on the room batches' own output (tools/image_early_checks.py,
BUILD-IMAGE-CHECKS-EARLY-66): on the stored output before the first stage when the stage is taken from an earlier run,
right after the stage when the build makes it (the scheduler's after-stage checks, tools/build_preflight.py phase
after:STAGE), where a problem stops the build before the stages after it. Fixture runs only; the audit is stood in for
where a payload would be needed."""
import contextlib
import io
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import build  # noqa: E402
import build_preflight  # noqa: E402
import image_early_checks as E  # noqa: E402
from build_parallel import execute_parallel  # noqa: E402

STAGE = 'chim-room-batches'


def stage_output(run, maps=True):
    folder = Path(run) / STAGE / 'id1'
    (folder / 'progs').mkdir(parents=True)
    (folder / 'progs' / 'a_1.mdl').write_bytes(b'room resident model')
    if maps:
        (folder / 'maps').mkdir()
        (folder / 'maps' / 'room.chim').write_bytes(b'room map')
    return folder


class RoomActorFrames(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.lines = []

    def stored(self, reused, steps=(STAGE, 'image')):
        return build_preflight.EarlyContext('stored', run=self.root / 'this', reused=reused, steps=list(steps),
                                            log=self.lines.append)

    def test_a_stored_output_is_checked_before_the_first_stage(self):
        earlier = self.root / '2026_11_17_v0.0.66_full_ad5e9a0'
        output = stage_output(earlier)
        with mock.patch('actor_frames.audit_payload',
                        side_effect=ValueError('1 actor frame layout problem(s): progs/a_1.mdl: idle not at 0')) as audit:
            problems = E.room_actor_frames(self.stored({STAGE: str(earlier)}))
        self.assertEqual(Path(audit.call_args[0][0]), output)
        self.assertEqual(len(problems), 1)
        self.assertIn('fails on the output of %s this build takes from %s' % (STAGE, earlier.name), problems[0])
        self.assertIn('idle not at 0', problems[0])
        with mock.patch('actor_frames.audit_payload', return_value={'actor_models': 1}):
            self.assertEqual(E.room_actor_frames(self.stored({STAGE: str(earlier)})), [])
        self.assertTrue(any('pass' in line for line in self.lines), self.lines)

    def test_a_stage_this_build_makes_is_left_to_the_check_after_it(self):
        with mock.patch('actor_frames.audit_payload') as audit:
            self.assertEqual(E.room_actor_frames(self.stored({})), [])
            self.assertEqual(E.room_actor_frames(self.stored({}, steps=('image',))), [])
        audit.assert_not_called()
        self.assertEqual(len(self.lines), 1)
        self.assertIn('checked the moment it has passed', self.lines[0])

    def test_the_check_after_the_stage_reads_its_output_in_the_run(self):
        run = self.root / 'this'
        output = stage_output(run)
        context = build_preflight.EarlyContext('after:' + STAGE, run=run, steps=[STAGE], log=self.lines.append)
        with mock.patch('actor_frames.audit_payload', side_effect=ValueError('2 problems')) as audit:
            problems = E.room_actor_frames_after(context)
        self.assertEqual(Path(audit.call_args[0][0]), output)
        self.assertEqual(problems, ["the image step's actor frames check (tools/actor_frames.py) fails on the output "
                                    "of %s: 2 problems" % STAGE])
        # an output without room maps: nothing to check
        other = self.root / 'other'
        stage_output(other, maps=False)
        with mock.patch('actor_frames.audit_payload') as audit:
            self.assertEqual(E.room_actor_frames_after(build_preflight.EarlyContext(
                'after:' + STAGE, run=other, steps=[STAGE], log=self.lines.append)), [])
        audit.assert_not_called()

    def test_they_are_registered(self):
        entries = {(name, phase) for name, phase, _ in build_preflight.EARLY_CHECKS}
        self.assertIn(('room-actor-frames', 'stored'), entries)
        self.assertIn(('room-actor-frames', 'after:' + STAGE), entries)
        self.assertEqual(build_preflight.after_stage_problems('music', self.root), [])     # nothing registered


class AfterStageChecks(unittest.TestCase):
    """The scheduler runs the checks registered for a stage the moment it has passed (serial and parallel): a problem
    stops the build before the stages after it, the stage stays passed (a build again takes its output and checks it
    before its first stage) and the failure page is written; a stage taken from an earlier run is not checked again."""
    MODULE = 'aw_test_after_stage_module'

    def setUp(self):
        module = types.ModuleType(self.MODULE)
        module.seen = []

        def check(context):
            module.seen.append((context.phase, Path(context.run).name))
            return ['the output of convert is wrong']
        module.check = check
        sys.modules[self.MODULE] = module
        self.addCleanup(sys.modules.pop, self.MODULE, None)
        self.module = module
        patcher = mock.patch.object(build_preflight, 'EARLY_CHECKS', [('bad-output', 'after:convert',
                                                                       self.MODULE + ':check')])
        patcher.start()
        self.addCleanup(patcher.stop)

    def build(self, tmp, parallel, metadata=None):
        run = Path(tmp) / 'build' / 'run-a'
        steps = [('first', [sys.executable, '-c', 'print("first")']),
                 ('convert', [sys.executable, '-c', 'print("convert")']),
                 ('later', [sys.executable, '-c', 'print("must not run")'])]
        meta = dict(metadata or {}, run_name={'commit': 'abc1234', 'version': '0.0.67-dev1'})
        with contextlib.redirect_stdout(io.StringIO()):
            if parallel:
                execute_parallel(steps, run, dict(meta, compiler_jobs=2), ROOT)
            else:
                build.execute(steps, run, meta)
        return run

    def test_a_problem_after_a_stage_stops_the_build_there(self):
        for parallel in (False, True):
            with self.subTest(parallel=parallel), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(RuntimeError, 'convert passed, but the checks after it found 1 problem'):
                    self.build(tmp, parallel)
                run = Path(tmp) / 'build' / 'run-a'
                state = json.loads((run / 'build-state.json').read_text())
                status = {s['name']: s['status'] for s in state['steps']}
                self.assertEqual(status.get('convert'), 'passed')
                self.assertNotIn('later', status)
                self.assertEqual(state['status'], 'failed')
                self.assertIn('later', state.get('not_started') or [])
                self.assertIn('the output of convert is wrong', (run / 'FAILURE.md').read_text())
                self.assertEqual(self.module.seen[-1], ('after:convert', 'run-a'))

    def test_a_stage_taken_from_an_earlier_run_is_not_checked_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            reused = {'stage_cache': {'reused': {'convert': {'from': '/work/build/older', 'fingerprint': 'f' * 64}}}}
            run = self.build(tmp, True, reused)
            self.assertEqual(json.loads((run / 'build-state.json').read_text())['status'], 'passed')
        self.assertEqual(self.module.seen, [])


if __name__ == '__main__':
    unittest.main()
