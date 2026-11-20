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
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import build  # noqa: E402
import build_cache  # noqa: E402
import build_report  # noqa: E402
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
        self.last = (done.exception, metadata, steps)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            path = build.write_build_report(fixture.args, 'failed', done.exception, metadata, steps)
        return path, out.getvalue()

    @unittest.skipUnless(POSIX, 'the stage wrapper and its read-trace hook run on POSIX')
    def test_one_failure_page_names_the_report_and_the_last_line_names_the_page(self):
        # the build's failure path (build.failure_details): RUN/FAILURE.md with the settings and the report's name,
        # printed; the line it returns is the build's last line (BUILD-FAILURE-NO-DETAILS-66)
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp, environment(tmp):
            build_report.note_start()
            fixture = Fixture(tmp)
            self.build(fixture, False)
            error, metadata, steps = self.last
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                line = build.failure_details(fixture.args, SimpleNamespace(run=fixture.run), error, metadata, steps)
            self.assertTrue(line.startswith('Failure details: %s (' % (fixture.run / 'FAILURE.md')), line)
            self.assertEqual(build.FAILURE_LINE, line)
            printed = out.getvalue()
            self.assertIn('Build report: %s' % fixture.report(), printed)
            self.assertIn('=== FAILURE DETAILS (also in %s) ===' % (fixture.run / 'FAILURE.md'), printed)
            page = (fixture.run / 'FAILURE.md').read_text(encoding='utf-8')
            for part in ('- **Failed stage:** convert (stage 2', '- **Not completed:** ', '## Traceback',
                         '- **Full report:** %s' % fixture.report(), '## Build settings',
                         '--name %s' % RUN, '## Build again from this run'):
                self.assertIn(part, page)
            # the report names the page in turn (it was written first)
            self.assertIn('Short form: build/%s/FAILURE.md' % RUN, fixture.report().read_text(encoding='utf-8'))

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
            # the line that names the one page there is (no run folder: the report), then, as the build's last lines,
            # what to do now (BUILD-OOM-HELP-AND-TIP-68)
            import build_failure
            lines = err.strip().splitlines()
            named = lines.index('Failure details: %s (the build stopped before it made its run folder)' % reports[0])
            self.assertEqual((lines[named + 1], lines[-1]), (build_failure.TIP_RULE, build_failure.TIP_RULE))
            self.assertEqual(lines[named + 2], 'THE BUILD STOPPED before its first stage, on its own error:')
            self.assertIn('Build report (the one file to send when you ask for help): %s' % reports[0], lines)
            text = reports[0].read_text(encoding='utf-8')
            self.assertIn('Run: not named yet', text)
            self.assertIn('The builder stopped outside its stages: ValueError: --prerendered takes one store folder',
                          text)
            self.assertIn('--prerendered = ["one", "two"]   [command line', text)
            self.assertIn('No stage plan: the build stopped before it planned its stages.', text)
            self.assertNotIn(SECRET, text)
            self.assertFalse((fixture.workspace / 'build' / '.startup').exists())   # no --name: no live files yet
            reports[0].unlink()
            # a check creates no files: no report, unless --report asks for one
            self.main(fixture, '--check')
            self.assertEqual(list((fixture.workspace / 'logs').iterdir()), [])
            self.main(fixture, '--check', '--report')
            self.assertEqual(len(list((fixture.workspace / 'logs').iterdir())), 1)


class StartupWatchTests(unittest.TestCase):
    """The build's live numbers from its first second (BUILDER-STALL-METRICS-66): a build started with --name writes
    build/.startup/<run>/ (progress and status folder) as soon as its options are read, before any check of seconds,
    and a build that stops in its start-up leaves status "failed" there for the monitor and any stall catcher."""

    def test_a_named_build_refused_in_its_start_up_leaves_its_live_numbers(self):
        import json
        with tempfile.TemporaryDirectory() as tmp, environment(tmp):
            fixture = Fixture(tmp)
            argv = ['--stage', 'terrain', '--workspace', str(fixture.workspace), '--data-files', str(fixture.data),
                    '--name', RUN, '--jobs', '2', '--prerendered', 'one', 'two']
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), \
                    self.assertRaises(SystemExit) as done:
                build.main(argv)
            self.assertEqual(done.exception.code, 1)
            folder = fixture.workspace / 'build' / '.startup' / RUN
            progress = json.loads((folder / 'build-progress.json').read_text(encoding='utf-8'))
            self.assertEqual(progress['status'], 'starting')
            self.assertIn('stall', progress)
            beat = json.loads((folder / 'status' / 'heartbeat.json').read_text(encoding='utf-8'))
            self.assertEqual(beat['status'], 'failed')
            self.assertEqual(beat['cores_planned'], 2)                        # --jobs 2 of the fixture's options
            self.assertIsNone(build._STARTUP_WATCH)                           # its thread and tee ended with main()
            self.assertNotIsInstance(sys.stdout, __import__('build_stall')._Tee)

    def test_the_watch_begins_before_the_start_up_checks(self):
        text = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
        start = text.index('def _main(')
        first = text.index('begin_startup_watch(args)', start)
        for later in ("__import__('disk_need').entry(args, p, storage_pool_dir)", 'build_preflight.run(args.workspace',
                      'args.run_name_record = run_name.record('):
            self.assertLess(first, text.index(later, start), later)


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


class EnvironmentTests(unittest.TestCase):
    """The environment summary under the result and the machine on every operating system
    (BUILD-REPORT-MACHINE-ALL-OS-67): the memory through each system's own readers, "Not available" only where nothing
    answers; the container line as what was checked and what each check found, our own mark first."""

    MAC = {'sysctl': '%d\n' % (32 << 30),
           'vm_stat': 'Mach Virtual Memory Statistics: (page size of 16384 bytes)\nPages free:      100000.\n'
                      'Pages active:   5.\nPages inactive:   50000.\nPages speculative:   10000.\n'}

    def mac(self, asked):
        def run(command, **options):
            asked.append((command, options.get('timeout'), options.get('stdin')))
            return SimpleNamespace(returncode=0, stdout=self.MAC[command[0]])
        return run

    def test_memory_on_each_operating_system(self):
        meminfo = 'MemTotal:       65536000 kB\nMemFree:            1000 kB\nMemAvailable:   32768000 kB\n'
        with mock.patch.object(build_report.platform, 'system', return_value='Linux'):
            self.assertEqual(build_report.memory(read=lambda path: meminfo if path == '/proc/meminfo' else None),
                             (65536000 * 1024, 32768000 * 1024, '/proc/meminfo'))
            self.assertEqual(build_report.memory(read=lambda path: None), (None, None, '/proc/meminfo did not answer'))
        # macOS: sysctl hw.memsize and vm_stat (free, inactive and speculative pages), each with a time limit, no input
        asked = []
        with mock.patch.object(build_report.platform, 'system', return_value='Darwin'):
            total, available, how = build_report.memory(run=self.mac(asked))
            self.assertEqual((total, available), (32 << 30, 160000 * 16384))
            self.assertIn('vm_stat', how)
            self.assertEqual([command[0] for command, _, _ in asked], ['sysctl', 'vm_stat'])
            self.assertTrue(all(limit and stdin == subprocess.DEVNULL for _, limit, stdin in asked))

            def missing(command, **options):
                raise FileNotFoundError(command[0])
            self.assertEqual(build_report.memory(run=missing), (None, None, 'sysctl hw.memsize did not answer'))
            self.assertTrue(build_report.memory_text(run=self.mac([])).startswith('32.0 GiB total, 2.4 GiB available'))

        # Windows: GlobalMemoryStatusEx through ctypes (a stand-in kernel fills the structure it is handed)
        class Kernel:
            def __init__(self, answer):
                self.answer = answer

            def GlobalMemoryStatusEx(self, ref):
                ref._obj.ullTotalPhys, ref._obj.ullAvailPhys = 16 << 30, 9 << 30
                return self.answer
        with mock.patch.object(build_report.platform, 'system', return_value='Windows'):
            self.assertEqual(build_report.memory(kernel32=Kernel(1)), (16 << 30, 9 << 30, 'GlobalMemoryStatusEx'))
            self.assertEqual(build_report.memory(kernel32=Kernel(0)), (None, None, 'GlobalMemoryStatusEx did not answer'))
            self.assertEqual(build_report.memory_text(kernel32=Kernel(1)),
                             '16.0 GiB total, 9.0 GiB available (GlobalMemoryStatusEx)')
            self.assertEqual(build_report.memory_text(kernel32=Kernel(0)),
                             'Not available (GlobalMemoryStatusEx did not answer)')
        # elsewhere: Not available, saying why
        with mock.patch.object(build_report.platform, 'system', return_value='FreeBSD'):
            self.assertEqual(build_report.memory_text(), 'Not available (no memory reader for FreeBSD)')

    def test_the_operating_system_line_on_each_system(self):
        with mock.patch.object(build_report.platform, 'system', return_value='Darwin'), \
                mock.patch.object(build_report.platform, 'mac_ver', return_value=('14.5', ('', '', ''), 'arm64')):
            self.assertIn(', macOS 14.5', build_report.system_text())
        with mock.patch.object(build_report.platform, 'system', return_value='Windows'), \
                mock.patch.object(build_report.platform, 'version', return_value='10.0.26100'), \
                mock.patch.object(build_report.platform, 'win32_edition', return_value='Professional', create=True):
            self.assertIn(', version 10.0.26100 (Professional)', build_report.system_text())
        with mock.patch.object(build_report.platform, 'system', return_value='Linux'):
            self.assertTrue(build_report.system_text().startswith('Linux '))
        reference = json.loads((ROOT / 'tools' / 'build-reference.json').read_text(encoding='utf-8'))['python']
        with mock.patch.object(build_report.platform, 'python_version', return_value=reference):
            self.assertTrue(build_report.python_text().endswith(', the recorded reference %s: matching' % reference))
        with mock.patch.object(build_report.platform, 'python_version', return_value='3.9.1'):
            self.assertTrue(build_report.python_text().endswith(', the recorded reference %s: older' % reference))

    def test_the_container_line_says_what_was_checked_and_what_each_found(self):
        files = {}

        def check(environ):
            return build_report.container(environ, lambda path: path in files, files.get)
        nothing = check({})
        self.assertTrue(nothing.startswith('no container signal found (checked: our builder image mark (AW_RUNTIME), '
                                           '/.dockerenv, /run/.containerenv, the container variable, /proc/1/cgroup'),
                        nothing)
        self.assertIn('finding none does not prove there is none', nothing)
        # our own mark first, with the image's tag
        self.assertEqual(check({'AW_RUNTIME': 'docker-builder', 'AW_RUNTIME_IMAGE': 'amiwind-builder:local'}),
                         'yes (our builder image amiwind-builder:local)')
        self.assertEqual(check({'AW_RUNTIME': 'master-builder', 'AW_RUNTIME_IMAGE': 'amiwind-builder:v1'}),
                         'yes (our builder image amiwind-builder:v1, started by the master builder)')
        self.assertEqual(check({'AW_RUNTIME': 'elsewhere'}), 'yes (marked AW_RUNTIME=elsewhere)')
        # each signal by itself
        for name, found, environ, said in (
                ('Docker', {'/.dockerenv': ''}, {}, '/.dockerenv (Docker)'),
                ('Podman', {'/run/.containerenv': ''}, {}, '/run/.containerenv (Podman)'),
                ('variable', {}, {'container': 'systemd-nspawn'}, 'container=systemd-nspawn (the container variable)'),
                ('cgroup v1', {'/proc/1/cgroup': '12:memory:/docker/0123abcd\n'}, {}, '/proc/1/cgroup names docker'),
                ('overlay root', {'/proc/self/mountinfo': '24 30 8:1 / /mnt rw - ext4 /dev/sdb rw\n'
                                                          '25 1 0:23 / / rw,relatime - overlay overlay rw,lowerdir=/l\n'},
                 {}, 'an overlay root (/proc/self/mountinfo)')):
            with self.subTest(name):
                files.clear()
                files.update(found)
                self.assertEqual(check(environ), 'yes (signals: %s)' % said)
        # cgroup v2 names nothing inside a container and an ext4 root is no signal: not "not in a container"
        files.clear()
        files.update({'/proc/1/cgroup': '0::/\n', '/proc/self/mountinfo': '25 1 8:1 / / rw - ext4 /dev/sdc rw\n'})
        self.assertTrue(check({}).startswith('no container signal found (checked: '))
        # the mark with a signal beside it, and the image's own builder copy
        files.clear()
        files.update({'/.dockerenv': '', '/opt/amiwind/VERSION': '0.0.67-dev1\n'})
        self.assertEqual(check({'AW_RUNTIME': 'docker-builder', 'AW_RUNTIME_IMAGE': 'amiwind-builder:local'}),
                         'yes (our builder image amiwind-builder:local); signals: /.dockerenv (Docker); the image\'s '
                         'own builder copy (/opt/amiwind) is v0.0.67-dev1')
        for text in (nothing, build_report.__doc__, build_report.container.__doc__):
            self.assertNotIn('not in a container.', text)

    def test_the_routes_set_the_mark_and_no_stage_key_reads_it(self):
        import build_docker
        import run_docker
        self.assertEqual((build_docker.RUNTIME_ENV, build_docker.RUNTIME_IMAGE_ENV),
                         (build_report.RUNTIME_ENV, build_report.RUNTIME_IMAGE_ENV))
        self.assertIn(build_docker.RUNTIME, build_report.RUNTIMES)
        # no AMIWIND_ name: every AMIWIND_ setting a stage can read is part of its key (tools/build_cache.py)
        for name in (build_report.RUNTIME_ENV, build_report.RUNTIME_IMAGE_ENV):
            self.assertIsNone(build_cache.ENV_NAME.search(name), name)
        lines = build_docker.DOCKERFILE.splitlines()
        install = next(at for at, line in enumerate(lines) if '--install-dependencies' in line)
        mark = next(at for at, line in enumerate(lines) if line.startswith('ENV AW_RUNTIME=docker-builder '))
        self.assertGreater(mark, install)              # after the install layer: the layers before it stay cached
        self.assertIn('AW_RUNTIME_IMAGE="${BUILDER_IMAGE}"', lines[mark])
        self.assertIn('ARG BUILDER_IMAGE=amiwind-builder:local', lines)
        # the image is built with its own tag as the mark
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(build_docker, 'prepare_context', return_value={}), \
                mock.patch('disk_need.docker_root', return_value='/var/lib/docker'), \
                mock.patch('disk_need.docker_problems', return_value=([], 1 << 30, 2 << 30)), \
                mock.patch.object(build_docker, 'logged') as logged, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(build_docker.main(['build', '--context', str(Path(tmp) / 'context'), '--output',
                                                str(Path(tmp) / 'results'), '--image', 'amiwind-builder:t1']), 0)
        command = logged.call_args_list[0][0][0]
        self.assertEqual(command[command.index('--build-arg') + 1], 'BUILDER_IMAGE=amiwind-builder:t1')
        # the Docker route passes it to the build too (an image built before the mark)
        command = run_docker.create_command(['docker'], 'amiwind-r', 'type=bind,source=/d,target=/input,readonly',
                                            'vol', 'amiwind-builder:local', 'r', 4, 'abc1234')
        at = command.index('amiwind-builder:local')
        self.assertEqual(command[at - 4:at], ['-e', 'AW_RUNTIME=docker-builder',
                                              '-e', 'AW_RUNTIME_IMAGE=amiwind-builder:local'])
        self.assertEqual(command[at + 1:at + 3], ['python', 'tools/build.py'])

    def test_the_docker_route_copies_a_failed_build_s_report_out(self):
        import run_docker
        with tempfile.TemporaryDirectory() as tmp:
            def copied(command, **options):
                Path(command[-1]).write_text('report', encoding='utf-8')
                return SimpleNamespace(returncode=0)
            with mock.patch.object(run_docker.subprocess, 'run', side_effect=copied) as ran:
                self.assertEqual(run_docker.copy_report(['docker'], 'amiwind-r', 'r', tmp),
                                 Path(tmp) / 'BUILD-REPORT-r.txt')
            self.assertEqual(ran.call_args[0][0][:3], ['docker', 'cp', 'amiwind-r:/work/logs/BUILD-REPORT-r.txt'])
            with mock.patch.object(run_docker.subprocess, 'run', return_value=SimpleNamespace(returncode=1)):
                self.assertIsNone(run_docker.copy_report(['docker'], 'amiwind-x', 'x', tmp))

    def test_the_summary_sits_under_the_result(self):
        with tempfile.TemporaryDirectory() as tmp, environment(tmp):
            fixture = Fixture(tmp, '--report')
            with contextlib.redirect_stdout(io.StringIO()), \
                    mock.patch.dict(os.environ, {'AW_RUNTIME': 'docker-builder',
                                                 'AW_RUNTIME_IMAGE': 'amiwind-builder:local'}):
                text = build.write_build_report(fixture.args, 'passed').read_text(encoding='utf-8')
        head = text.split('\n1. Result\n')[0]
        block = head.split('\nEnvironment (parts 3 and 5 have the details):\n')[1].split('\n\n')[0].splitlines()
        self.assertEqual([row.split(':')[0].strip() for row in block],
                         ['Operating system', 'Container', 'Python', 'Cores', 'Memory', 'Swap', 'Memory peak',
                          'Free space'])
        self.assertTrue(block[1].startswith('  Container: yes (our builder image amiwind-builder:local)'), block[1])
        self.assertRegex(block[2], r'^  Python: \S+ \(\w+\), the recorded reference \S+: (matching|newer|older|unknown)$')
        self.assertEqual(block[6], '  Memory peak: not recorded (the build kept no memory figures)')
        self.assertRegex(block[7], r'^  Free space: .+ in the workspace, .+ in the temp folder$')
        self.assertIn('\nFree space in the temp folder (', text)
        self.assertLess(text.index('\nResult: passed\n'), text.index('\nEnvironment ('))


class KindTests(unittest.TestCase):
    """The failure's kind right under the result line (tools/build_failure.py kinds, BUILD-REPORT-MACHINE-ALL-OS-67)."""

    def test_an_out_of_disk_stage_is_named_under_the_result(self):
        with tempfile.TemporaryDirectory() as tmp, environment(tmp):
            fixture = Fixture(tmp)
            (fixture.run / 'logs').mkdir(parents=True)
            (fixture.run / 'build-state.json').write_text(json.dumps({
                'build_started_at': 'start', 'status': 'failed',
                'steps': [{'name': 'chim-room-batches', 'status': 'failed', 'returncode': 1, 'jobs': 2,
                           'log': str(fixture.run / 'logs' / '05-chim-room-batches.log')}]}), encoding='utf-8')
            (fixture.run / 'logs' / '05-chim-room-batches.log').write_text(
                'room 1 converted\nTraceback (most recent call last):\n  File "x.py", line 3, in write\n'
                "OSError: [Errno 28] No space left on device: '/work/build/r/x.bsp'\n", encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()):
                text = build.write_build_report(fixture.args, 'failed', RuntimeError('chim-room-batches failed'),
                                                {'build_started_at': 'start'}).read_text(encoding='utf-8')
            head = text.split('\nWritten: ')[0].splitlines()
            self.assertEqual(head[-4], 'Result: FAILED')
            self.assertEqual(head[-3], 'Kind: OUT OF DISK (proven): errno 28 (ENOSPC): no space left on the device')
            self.assertTrue(head[-2].startswith('  Found: free space at the start and now: workspace '), head[-2])
            self.assertTrue(head[-1].startswith('  What to do: free space in the workspace'), head[-1])
            # a passed build names no kind
            asked = Fixture(Path(tmp) / 'asked', '--report')
            with contextlib.redirect_stdout(io.StringIO()):
                passed = build.write_build_report(asked.args, 'passed').read_text(encoding='utf-8')
            self.assertNotIn('\nKind: ', passed)


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
            # the full private word lists are checked by the maintainer's own tooling, not here
            for word in ('the ' + 'owner', ' cha' + 't ', 'chann' + 'el'):
                self.assertNotIn(word, lowered)


if __name__ == '__main__':
    unittest.main()
