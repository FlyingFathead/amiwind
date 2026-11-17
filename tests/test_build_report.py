# SPDX-License-Identifier: GPL-3.0-only
"""The one-file build report (tools/build_report.py, BUILD-FAILURE-REPORT-66): a failed build writes
logs/BUILD-REPORT-<run>.txt in the workspace with what failed (the stage, its error, the traceback, the last 200 lines
of its log), every setting, the versions, the game data's sizes and SHA-256, the machine, the stage plan and the reuse
state; a passed build writes none unless --report; the report holds no environment value outside the AMIWIND_
settings and the build options, and no absolute path of the workspace, the checkout or the home folder. Fixture stages
and fixture game files only, no game data."""
import contextlib
import hashlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import build  # noqa: E402
import build_cache  # noqa: E402
import build_report  # noqa: E402
import bug_register  # noqa: E402
from build_parallel import execute_parallel  # noqa: E402

POSIX = os.name == 'posix'
RUN = '2026_11_16_v0.0.66-dev12_full_abc1234'
SECRET = 'not-an-amiwind-value-5e1f0c'
# A stage that converts 300 units, names the one it stops on, and exits with an error as argparse's exit does
STAGE = '\n'.join([
    'import argparse',
    '',
    '',
    'def bake(unit):',
    "    raise ValueError('seam stop (worse): npc chargen class: 14 uncovered new openings')",
    '',
    '',
    'def main():',
    '    ap = argparse.ArgumentParser()',
    '    for unit in range(300):',
    "        print('unit %03d converted' % unit, flush=True)",
    "    print('not converted: npc chargen class: its seam check', flush=True)",
    '    try:',
    "        bake('npc chargen class')",
    '    except ValueError as exc:',
    "        ap.exit(1, 'Error: %s\\n' % exc)",
    '',
    '',
    'main()',
    ''])
MORROWIND_ESM, MORROWIND_BSA = b'TES3 fixture master, not a game file\n', b'fixture archive, not a game file\n'


class Fixture:
    """A home folder with the fixture game files, a workspace and the build's options, in a temporary folder."""

    def __init__(self, tmp, *extra):
        self.tmp = Path(tmp).resolve()
        self.home = self.tmp / 'home' / 'player'
        self.data = self.home / 'games' / 'Morrowind' / 'Data Files'
        self.data.mkdir(parents=True)
        (self.data / 'Morrowind.esm').write_bytes(MORROWIND_ESM)
        (self.data / 'Morrowind.bsa').write_bytes(MORROWIND_BSA)
        self.workspace = self.tmp / 'workspace'
        self.argv = ['--workspace', str(self.workspace), '--name', RUN, '--data-files', str(self.data), '--jobs', '2',
                     *extra]
        self.args = build.parser().parse_args(self.argv)
        self.args._argv = list(self.argv)
        self.run = self.workspace / 'build' / RUN

    def report(self):
        return self.workspace / 'logs' / ('BUILD-REPORT-%s.txt' % RUN)


@contextlib.contextmanager
def environment(tmp):
    """The test's environment, restored afterwards: a home folder in TMP, one AMIWIND_ setting from the shell and no
    other (the shipped bake settings are then the builder's defaults), one value that is not a build setting."""
    home = Path(tmp).resolve() / 'home' / 'player'
    with mock.patch.dict(os.environ, {'HOME': str(home), 'AMIWIND_REPORT_SHELL_TEST': 'from-the-shell',
                                      'AW_REPORT_PRIVATE_TEST': SECRET}):
        for key in [key for key in os.environ if key.startswith('AMIWIND_') and key != 'AMIWIND_REPORT_SHELL_TEST']:
            del os.environ[key]
        yield home


class FailedStageTests(unittest.TestCase):
    """A fixture build whose second stage fails: the report and each of its parts."""

    def build(self, fixture, parallel):
        scripts = fixture.home / 'stages'
        scripts.mkdir()
        (scripts / 'convert.py').write_text(STAGE)
        steps = [('first', [sys.executable, '-c', 'print("first result")']),
                 ('convert', [sys.executable, str(scripts / 'convert.py')]),
                 ('later', [sys.executable, '-c', 'print("must not run")'])]
        older = fixture.workspace / 'build' / '2026_11_15_v0.0.66-dev11_full_def5678'
        metadata = {'run_name': {'commit': 'abc1234', 'version': '0.0.66-dev12'}, 'build_argv': fixture.argv,
                    'tools': {'qbsp': str(fixture.home / 'tools' / 'qbsp')}, 'tool_sha256': {'qbsp': 'ab' * 32},
                    'stage_cache': {'reuse_from': str(older), 'reuse_mode': 'copy',
                                    'fingerprints': {'first': '1' * 64, 'convert': '2' * 64, 'later': '3' * 64},
                                    'reused': {'first': {'from': str(older), 'fingerprint': '1' * 64, 'files': 3,
                                                         'bytes': 4096}},
                                    'not_reused': {'convert': 'its sources changed: tools/npc_geometry.py',
                                                   'later': 'a stage before it is rebuilt'}}}
        if parallel:
            metadata['compiler_jobs'] = 2
        build_cache.CLOSURES[str(fixture.run)] = {'root': str(ROOT), 'stages': {}}   # the read-trace hook in the run
        try:
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, 'convert failed') as done:
                if parallel:
                    execute_parallel(steps, fixture.run, metadata, ROOT)
                else:
                    build.execute(steps, fixture.run, metadata)
        finally:
            build_cache.CLOSURES.pop(str(fixture.run), None)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            path = build.write_build_report(fixture.args, 'failed', done.exception, metadata, steps)
        return path, out.getvalue()

    @unittest.skipUnless(POSIX, 'the stage wrapper and its read-trace hook run on POSIX')
    def test_a_failed_stage_writes_the_report_with_each_part(self):
        for parallel in (False, True):
            with self.subTest(parallel=parallel), tempfile.TemporaryDirectory() as tmp, environment(tmp):
                build_report.note_start()
                build.apply_shipped_bake_defaults()
                fixture = Fixture(tmp)
                path, printed = self.build(fixture, parallel)
                self.assertEqual(path, fixture.report())
                self.assertIn('Build report: %s' % path, printed)                 # the console says where it is
                text = path.read_text(encoding='utf-8')

                def has(part):
                    if part not in text:
                        self.fail('the report lacks %r' % part)
                for part in ('1. What failed', '2. Build settings', '3. Versions', '4. Game data', '5. Machine',
                             '6. Stage plan', '7. Reuse', 'End of the build report.'):
                    has('\n' + part + '\n')
                # what failed: the stage, its error naming the unit, the traceback, the units it refused, its log
                has('Stage: convert (stage 2 of 3, exit 1')
                self.assertRegex(text, r'\nError: (ValueError: )?seam stop \(worse\): npc chargen class: 14 uncovered '
                                       r'new openings\n')
                has('Traceback:\n  Traceback (most recent call last):')
                has(', in bake')
                has('Units the stage refused or left out: 1\n  not converted: npc chargen class')
                has('Stage command: %s ~/stages/convert.py' % sys.executable)
                has('Stage log: build/%s/logs/02-convert.log' % RUN)
                tail = text.split('The last 200 lines of the stage log:\n')[1].split('\n\n')[0].splitlines()
                self.assertEqual(len(tail), 200)
                log = (fixture.run / 'logs' / '02-convert.log').read_text().splitlines()
                shown = build_report.Paths(fixture.workspace, ROOT)
                self.assertEqual(tail, ['  ' + shown.text(line) for line in log[-200:]])
                self.assertNotIn('unit 000 converted', text)
                # the settings: the options and where each came from, the AMIWIND_ settings and theirs
                has('--name = %s   [command line' % RUN)
                has('--workspace = .   [command line')
                has('--data-files = ~/games/Morrowind/Data Files   [command line')
                has('--jobs/--single-thread = 2   [command line')
                has('\n  --report = off\n')                                      # at its default
                has('AMIWIND_REPORT_SHELL_TEST=from-the-shell   [set before the build started]')
                has("AMIWIND_MESH_SEAM_STOP=warn   [the builder's default (a shipped NPC bake setting)]")
                # the versions, the game data by size and SHA-256, the machine
                has('AmiWind: %s (VERSION)' % build.VERSION)
                has('Python: ')
                has('  qbsp: ~/tools/qbsp  SHA-256 ' + 'ab' * 32)
                has('Data folder: ~/games/Morrowind/Data Files')
                for name, raw in (('Morrowind.esm', MORROWIND_ESM), ('Morrowind.bsa', MORROWIND_BSA)):
                    has('  %s  %d bytes  SHA-256 %s' % (name, len(raw), hashlib.sha256(raw).hexdigest()))
                has('Not present: Tribunal.esm, Tribunal.bsa, Bloodmoon.esm, Bloodmoon.bsa')
                has('Cores: ')
                # the stage plan with each stage's state, and the reuse state
                plan = text.split('6. Stage plan\n')[1].split('7. Reuse\n')[0]
                self.assertRegex(plan, r'\n +1  first +passed, reused ')
                self.assertRegex(plan, r'\n +2  convert +failed +\S')
                self.assertRegex(plan, r'\n +3  later +not started ')
                has('Reuse source: build/2026_11_15_v0.0.66-dev11_full_def5678')
                has('  convert: its sources changed: tools/npc_geometry.py')
                # privacy: no other environment value, no absolute path of the temporary folders or the checkout
                for private in (SECRET, str(fixture.tmp), str(ROOT)):
                    if private in text:
                        self.fail('the report holds %r' % private)


class EarlyFailureTests(unittest.TestCase):
    """The builder's own refusal before any stage: the report through build.main, and when it is written."""

    def main(self, fixture, *extra):
        argv = ['--stage', 'terrain', '--workspace', str(fixture.workspace), '--data-files', str(fixture.data),
                '--prerendered', 'one', 'two', *extra]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as done:
            build.main(argv)
        return done.exception.code, out.getvalue(), err.getvalue()

    def test_a_refused_start_writes_the_report_and_a_check_only_with_report(self):
        with tempfile.TemporaryDirectory() as tmp, environment(tmp):
            fixture = Fixture(tmp)
            code, out, err = self.main(fixture)
            self.assertEqual(code, 1)
            self.assertIn('--prerendered takes one store folder', err)
            reports = sorted((fixture.workspace / 'logs').glob('BUILD-REPORT-*_v%s_before-the-run-name.txt'
                                                              % build.VERSION))
            self.assertEqual(len(reports), 1, out)
            self.assertIn('Build report: %s' % reports[0], out)
            text = reports[0].read_text(encoding='utf-8')
            self.assertIn('Run: not named yet', text)
            self.assertIn('The builder stopped outside its stages: ValueError: --prerendered takes one store folder',
                          text)
            self.assertIn('--prerendered = ["one", "two"]   [command line', text)
            self.assertIn('No stage plan: the build stopped before it planned its stages.', text)
            self.assertNotIn(SECRET, text)
            reports[0].unlink()
            # a check creates no files: no report, unless --report asks for one
            self.main(fixture, '--check')
            self.assertEqual(list((fixture.workspace / 'logs').iterdir()), [])
            self.main(fixture, '--check', '--report')
            self.assertEqual(len(list((fixture.workspace / 'logs').iterdir())), 1)


class WhenTests(unittest.TestCase):
    def test_a_passed_build_writes_none_unless_report(self):
        with tempfile.TemporaryDirectory() as tmp, environment(tmp):
            fixture = Fixture(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertIsNone(build.write_build_report(fixture.args, 'passed'))
                self.assertIsNone(build.write_build_report(fixture.args, 'cancelled', KeyboardInterrupt()))
            self.assertFalse((fixture.workspace / 'logs').exists())
            asked = Fixture(Path(tmp) / 'asked', '--report')
            with contextlib.redirect_stdout(io.StringIO()):
                path = build.write_build_report(asked.args, 'passed', code=0)
            text = path.read_text(encoding='utf-8')
            self.assertIn('Result: passed', text)
            self.assertIn('1. Result\n', text)
            self.assertIn('Nothing failed: the build passed.', text)
            self.assertIn('--report = on   [command line', text)

    def test_an_earlier_run_of_the_same_name_is_not_reported_as_this_build(self):
        with tempfile.TemporaryDirectory() as tmp, environment(tmp):
            fixture = Fixture(tmp)
            (fixture.run / 'logs').mkdir(parents=True)
            (fixture.run / 'build-state.json').write_text(
                '{"build_started_at": "earlier", "status": "failed", "steps": [{"name": "older-stage", '
                '"status": "failed", "log": "/x/logs/01-older-stage.log"}]}', encoding='utf-8')
            for metadata in (None, {'build_started_at': 'now'}):
                with self.subTest(metadata=metadata), contextlib.redirect_stdout(io.StringIO()):
                    path = build.write_build_report(fixture.args, 'failed', ValueError('Build already exists'), metadata)
                    text = path.read_text(encoding='utf-8')
                self.assertIn("(an earlier run of the same name: not this build's)", text)
                self.assertNotIn('older-stage', text)
                self.assertIn('The builder stopped outside its stages: ValueError: Build already exists', text)

    def test_which_runs_want_a_report(self):
        parse = build.parser().parse_args
        self.assertTrue(build_report.wanted(parse([]), 'failed'))
        self.assertFalse(build_report.wanted(parse([]), 'passed'))
        self.assertFalse(build_report.wanted(parse([]), 'cancelled'))
        self.assertFalse(build_report.wanted(parse(['--check']), 'failed'))
        self.assertFalse(build_report.wanted(parse(['--plan']), 'failed'))
        for argv in (['--report'], ['--check', '--report']):
            for status in ('failed', 'passed', 'cancelled'):
                self.assertTrue(build_report.wanted(parse(argv), status), (argv, status))


class PathTests(unittest.TestCase):
    def test_paths_are_shortened_only_where_they_start(self):
        paths = build_report.Paths('/vol/ws8', '/vol/src/abc', home='/home/u')
        self.assertEqual(paths.text('File "/vol/src/abc/tools/x.py", /vol/ws8/build/r/logs, /vol/ws8 and /vol/ws80/x'),
                         'File "<source>/tools/x.py", build/r/logs, . and /vol/ws80/x')
        self.assertEqual(paths.text('--data-files=/home/u/games /home/user/x /other/home/u/y'),
                         '--data-files=~/games /home/user/x /other/home/u/y')
        inside = build_report.Paths('/home/u/out', '/home/u/src', home='/home/u')
        self.assertEqual(inside.text('/home/u/out/build/r /home/u/src/tools /home/u/x'), 'build/r <source>/tools ~/x')
        # a relative workspace is never matched as a word
        self.assertEqual(build_report.Paths('out', None, home='').text('without output'), 'without output')


class PublicTextTests(unittest.TestCase):
    def test_public_text_rules(self):
        with tempfile.TemporaryDirectory() as tmp, environment(tmp):
            fixture = Fixture(tmp, '--report')
            with contextlib.redirect_stdout(io.StringIO()):
                page = build.write_build_report(fixture.args, 'passed').read_text(encoding='utf-8')
        for text in (page, (ROOT / 'tools' / 'build_report.py').read_text(encoding='utf-8'),
                     Path(__file__).read_text(encoding='utf-8')):
            lowered = text.lower()
            self.assertEqual([w for w in bug_register.PRIVATE_WORDS if w in lowered], [])
            for word in ('tele' + 'gram', 'the ' + 'owner', ' cha' + 't ', 'chann' + 'el'):
                self.assertNotIn(word, lowered)


if __name__ == '__main__':
    unittest.main()
