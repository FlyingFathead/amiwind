# SPDX-License-Identifier: GPL-3.0-only
"""A failed build ends with a block for whoever ran it (tools/build_failure.py tip_lines, BUILD-OOM-HELP-AND-TIP-68):
why it stopped, that the finished work is kept with the exact command that continues it (the same command, from the
same folder), and what to try for that cause; out of memory, the advice follows where the stage's memory was (one
process: fewer workers do not help; its workers: about half of them). The build report carries the swap and the
memory peaks, and a build prints its machine at its start. Fixture run folders only, no game data, no stage."""
import contextlib
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
import build_failure  # noqa: E402
import build_report  # noqa: E402

GIB = 1 << 30
RUN = '2026_11_20_v0.0.68-dev1_full_abc1234'
ARGV = ['--data-files', '/games/Morrowind', '--workspace', '../amiwind-local', '--name', 'first-try', '--jobs', '12']
# where the memory was, as the v0.0.66 from-scratch build measured it (config/build-memory.json)
CHIM = {'name': 'chim', 'peak_tree_rss_bytes': int(25.1 * GIB), 'peak_process_rss_bytes': int(24.1 * GIB),
        'jobs': 3, 'jobs_max': 10, 'status': 'failed'}
ROOMS = {'name': 'chim-room-batches', 'peak_tree_rss_bytes': int(17.4 * GIB),
         'peak_process_rss_bytes': int(1.8 * GIB), 'jobs': 2, 'jobs_max': 20, 'status': 'failed'}
BROKEN_POOL = ['Traceback (most recent call last):', '  File "/src/tools/chim_room_batches.py", line 310, in bake',
               'concurrent.futures.process.BrokenProcessPool: A process in the process pool was terminated abruptly '
               'while the future was running or pending.']


def stopped_run(workspace, stage_row, returncode=-9, log=(), argv=ARGV, memory=True, profile=True):
    """A run folder as a build leaves it when STAGE_ROW's stage stopped: build-state.json, its log, the profile's row,
    the memory the build saw (build-progress.json)."""
    name = stage_row['name']
    run = Path(workspace) / 'build' / RUN
    (run / 'logs').mkdir(parents=True)
    (run / 'build-state.json').write_text(json.dumps({
        'status': 'failed', 'run_name': {'commit': 'abc1234', 'version': '0.0.68-dev1'}, 'build_argv': list(argv),
        'compiler_jobs': 12, 'build_started_at': 'start',
        'steps': [{'name': 'census', 'status': 'passed', 'log': str(run / 'logs' / '03-census.log')},
                  {'name': name, 'status': 'failed', 'returncode': returncode, 'elapsed_seconds': 23455.0, 'jobs': 3,
                   'log': str(run / 'logs' / ('27-%s.log' % name))}],
        'not_started': ['image']}), encoding='utf-8')
    (run / 'logs' / ('27-%s.log' % name)).write_text('\n'.join(['unit 1 stored'] + list(log)) + '\n', encoding='utf-8')
    if profile:
        (run / 'build-profile.json').write_text(json.dumps({'stages': [stage_row]}), encoding='utf-8')
    if memory:
        (run / 'build-progress.json').write_text(json.dumps({'memory': {
            'limit_gib': 32.0, 'source': 'container', 'peak_gib': 31.6, 'peak_stages': ['chim', 'chim-room-batches']}}),
            encoding='utf-8')
    return run


def flat(lines):
    """The tip's words as one line: its text lines are wrapped for a terminal."""
    return ' '.join(' '.join(str(line).split()) for line in lines)


@contextlib.contextmanager
def no_swap_read():
    """No swap on the fixture machine, and no build start noted (the kill counter of the test's own machine stays out
    of the kind's proof)."""
    with mock.patch.object(build_failure, 'swap_now', return_value=(0, 0, '/proc/meminfo')), \
            mock.patch.dict(build_failure._START, clear=True):
        yield


class AdviceByStageTests(unittest.TestCase):
    """A stop of the CHIM world's main process and a stop of a pool stage's workers give different advice."""

    def tip(self, stage_row, **options):
        with tempfile.TemporaryDirectory() as tmp, no_swap_read():
            run = stopped_run(tmp, stage_row, **options)
            rec = build_failure.write(run)
            page = (run / 'FAILURE.md').read_text(encoding='utf-8')
            return rec, rec['tip'], page, run

    def test_the_chim_main_process_stop_says_fewer_workers_do_not_help(self):
        rec, tip, page, run = self.tip(CHIM)
        text = flat(tip)
        self.assertEqual(rec['kinds'][0]['kind'], build_failure.MEMORY)
        self.assertEqual(tip[1], 'THE BUILD STOPPED in the stage chim, after 6 h 30 min: OUT OF MEMORY (likely, not '
                                 'proven).')
        self.assertIn('The stage reached 25.1 GiB; one process of it (its main process, as a rule) held 24.1 GiB of '
                      'that (measured in this build).', text)
        self.assertIn('This build had 32.0 GiB of memory (the container\'s limit) and no swap; its peak: 31.6 GiB, with '
                      'chim, chim-room-batches running.', text)
        self.assertIn('Fewer workers (-j) do not help in this stage: one process holds most of its memory.', text)
        # the swap advised: the reference build's peak (43.7 GiB) + 2 GiB less the 32 GiB it had, in steps of 4
        self.assertIn('Add swap (about 16 GiB or more), or give the build more memory', text)
        self.assertNotIn('Use about half the workers', text)
        self.assertNotIn('-j 6', text)
        self.assertTrue(all(len(line) <= build_failure.TIP_WIDTH for line in tip if not line.lstrip().startswith(
            ('./build.sh', 'Build report', 'Help:'))), tip)

    def test_a_pool_stage_stop_says_half_the_workers_with_the_command(self):
        rec, tip, page, run = self.tip(ROOMS, returncode=1, log=BROKEN_POOL)
        text = flat(tip)
        self.assertIn('The stage reached 17.4 GiB, most of it in its workers (its largest process: 1.8 GiB; measured in '
                      'this build).', text)
        self.assertIn('Use about half the workers (this build had 12): the same command with -j 6:', text)
        self.assertIn('      ./build.sh --data-files /games/Morrowind --workspace ../amiwind-local -j 6', tip)
        self.assertIn('If it stops again: add swap (about 16 GiB or more)', text)
        self.assertNotIn('do not help', text)

    def test_without_a_measurement_the_reference_build_decides(self):
        # no profile row in this build and no earlier build: config/build-memory.json says where the memory was
        rec, tip, _, _ = self.tip(CHIM, profile=False)
        text = flat(tip)
        self.assertIn('(measured in the v0.0.66 from-scratch build).', text)
        self.assertIn('Fewer workers (-j) do not help', text)
        rec, tip, _, _ = self.tip(dict(ROOMS, name='actor-library'), profile=False, returncode=-9)
        self.assertIn('Use about half the workers', flat(tip))

    def test_the_reference_table_holds_the_measured_stages(self):
        ref = build_failure.reference_memory()
        self.assertEqual(ref['schema'], build_failure.MEMORY_SCHEMA)
        for stage in ('chim', 'chim-room-batches', 'actor-library', 'image'):
            self.assertIn(stage, ref['stages'])
        shape = {name: build_failure.stage_memory(None, name, None, ref)['one_process']
                 for name in ('chim', 'chim-room-batches', 'actor-library', 'image')}
        self.assertEqual(shape, {'chim': True, 'chim-room-batches': False, 'actor-library': False, 'image': False})
        for row in ref['stages'].values():
            self.assertLessEqual(row['largest_process_bytes'], row['peak_bytes'])
        self.assertGreater(ref['build_peak_bytes'], max(row['peak_bytes'] for row in ref['stages'].values()))

    def test_an_earlier_build_of_the_workspace_is_the_second_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'cache').mkdir()
            (Path(tmp) / 'cache' / 'resource-history.jsonl').write_text('\n'.join(json.dumps(row) for row in (
                {'stage': 'chim', 'measured': {'largest_mib': 100.0, 'total_mib': 9000.0, 'jobs': 8}},
                {'stage': 'chim', 'scope': 'miniwind', 'measured': {'largest_mib': 9.0, 'total_mib': 10.0, 'jobs': 1}},
                {'stage': 'other', 'measured': {'largest_mib': 1.0, 'total_mib': 2.0, 'jobs': 1}})) + '\n')
            found = build_failure.stage_memory(None, 'chim', tmp, {})
        self.assertEqual((found['peak'], found['largest'], found['workers'], found['one_process']),
                         (9000 << 20, 100 << 20, 8, False))
        self.assertEqual(found['source'], 'measured in an earlier build of this build folder')
        self.assertIsNone(build_failure.stage_memory(None, 'unknown-stage', None, {}))

    def test_the_swap_advised(self):
        ref = {'build_peak_bytes': int(43.7 * GIB)}
        self.assertEqual(build_failure.advised_swap_gib(32 * GIB, ref), 16)
        self.assertEqual(build_failure.advised_swap_gib(24 * GIB, ref), 24)
        self.assertEqual(build_failure.advised_swap_gib(48 * GIB, ref), build_failure.MIN_SWAP_GIB)
        self.assertEqual(build_failure.advised_swap_gib(None, ref), build_failure.MIN_SWAP_GIB)


class TheCommandThatContinues(unittest.TestCase):
    def test_the_same_command_without_the_run_s_own_options(self):
        options, notes = build_failure.continue_options(
            ['--data-files', '/owned', '--name', 'x', '--save-recipe', 'r.json', '--source-commit=c9d30f8',
             '--name=y', '--clean', '--no-reuse', '--release-from-scratch', '--jobs', '24', '--report'])
        self.assertEqual(options, ['--data-files', '/owned', '--jobs', '24', '--report'])
        self.assertEqual(len([note for note in notes if note.startswith('--name is left out')]), 1)
        for option in build_failure.FROM_SCRATCH_OPTIONS:
            self.assertTrue(any(note.startswith(option + ' is left out') for note in notes), option)

    def test_a_reuse_source_becomes_the_failed_run_and_the_workers_are_replaced(self):
        argv = ['--reuse-from', '/w/build/older', '-j8', '--data-files', '/owned', '--reuse-from=/w/x', '--single-thread']
        self.assertEqual(build_failure.continue_options(argv, '/w/build/failed')[0],
                         ['--reuse-from', '/w/build/failed', '-j8', '--data-files', '/owned', '--reuse-from',
                          '/w/build/failed', '--single-thread'])
        self.assertEqual(build_failure.continue_options(argv, '/w/build/failed', jobs=4)[0],
                         ['--reuse-from', '/w/build/failed', '--data-files', '/owned', '--reuse-from', '/w/build/failed',
                          '-j', '4'])
        for argv, jobs in ((['-j', '6'], 3), (['--jobs=6'], 3), (['--j', '6'], 3), (['-j=6'], 3)):
            self.assertEqual(build_failure.continue_options(argv, jobs=jobs)[0], ['-j', '3'], argv)
        # without a run folder (a stop before it), an earlier reuse source stays as given
        self.assertEqual(build_failure.continue_options(['--reuse-from', '/w/build/older'])[0],
                         ['--reuse-from', '/w/build/older'])

    def test_the_command_as_the_player_types_it(self):
        self.assertEqual(build_failure.command_line(['--data-files', '/games/My Morrowind'], 'Linux'),
                         "./build.sh --data-files '/games/My Morrowind'")
        self.assertEqual(build_failure.command_line(['--data-files', r'..\Games\My Morrowind'], 'Windows'),
                         r'.\build.cmd --data-files "..\Games\My Morrowind"')
        self.assertEqual(build_failure.command_line([], 'Darwin'), './build.sh')

    def test_the_tip_is_the_build_s_last_lines(self):
        with tempfile.TemporaryDirectory() as tmp, no_swap_read():
            run = stopped_run(tmp, CHIM)
            args = build.parser().parse_args(ARGV)
            args._argv = list(ARGV)
            args.workspace, args.name = Path(tmp), RUN
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                line = build.failure_details(args, SimpleNamespace(run=run), RuntimeError('chim failed'),
                                             {'build_started_at': 'start'})
            lines = line.splitlines()
            self.assertTrue(lines[0].startswith('Failure details: %s (' % (run / 'FAILURE.md')), lines[0])
            self.assertEqual(lines[1], build_failure.TIP_RULE)
            self.assertEqual(lines[-1], build_failure.TIP_RULE)
            self.assertIn('Your finished work is kept: do not delete the build folder. Run the same command again, '
                          'from the same folder; every stage and unit that finished is taken back', flat(lines))
            self.assertIn('  ./build.sh --data-files /games/Morrowind --workspace ../amiwind-local --jobs 12', lines)
            self.assertIn('  (--name is left out: a run name is used once (add --name NEW to choose one))', lines)
            self.assertIn('Help: ' + build_failure.HELP_SECTION, lines)
            report = Path(tmp) / 'logs' / ('BUILD-REPORT-%s.txt' % RUN)
            self.assertIn('Build report (the one file to send when you ask for help): %s' % report, lines)
            # FAILURE.md opens with the same block, before the kind and the failed stage
            page = (run / 'FAILURE.md').read_text(encoding='utf-8')
            self.assertLess(page.index('## What to do now'), page.index('- **Kind:** OUT OF MEMORY'))
            self.assertIn('Fewer workers (-j) do not help', flat(page.split('- **Kind:**')[0].splitlines()))
            # and so does the build report, under its result
            text = report.read_text(encoding='utf-8')
            self.assertLess(text.index('\nResult: FAILED\n'), text.index(build_failure.TIP_RULE))
            self.assertLess(text.index('THE BUILD STOPPED in the stage chim'), text.index('\nEnvironment ('))
            self.assertIn('--workspace ../amiwind-local --jobs 12', text)

    def test_a_disk_stop_and_a_stage_error_say_their_own_cause(self):
        with tempfile.TemporaryDirectory() as tmp, no_swap_read():
            run = stopped_run(tmp, ROOMS, returncode=1, log=[
                'Traceback (most recent call last):', '  File "/src/tools/x.py", line 3, in write',
                "OSError: [Errno 28] No space left on device: '/w/x.bsp'"])
            tip = flat(build_failure.write(run)['tip'])
            self.assertIn('OUT OF DISK (proven)', tip)
            self.assertIn('python3 tools/build_gc.py plan %s lists what can go' % Path(tmp), tip)
            self.assertIn('point TMPDIR at a folder with room', tip)
            self.assertNotIn('-j ', tip)
        with tempfile.TemporaryDirectory() as tmp, no_swap_read():
            run = stopped_run(tmp, ROOMS, returncode=1, log=['Error: seam stop (worse): npc chargen class'])
            tip = build_failure.write(run)['tip']
            self.assertEqual(tip[1:3], ['THE BUILD STOPPED in the stage chim-room-batches, after 6 h 30 min, on its own '
                                        'error:', '  Error: seam stop (worse): npc chargen class'])
            self.assertIn('- Fix what the error line names (the failure page has its traceback and the stage\'s last '
                          'log lines).', flat(tip))
            self.assertIn('Your finished work is kept: do not delete the build folder. Run the same command again, '
                          'from the same folder; every stage and unit that finished is taken back', flat(tip))

    def test_a_stop_before_the_run_folder(self):
        rec = build_failure.bare_record(ValueError('--prerendered takes one store folder'), ['--prerendered', 'a', 'b'])
        tip = build_failure.tip_lines(rec, None, '/w', live=True, system='Linux')
        self.assertEqual(tip[1:3], ['THE BUILD STOPPED before its first stage, on its own error:',
                                    '  ValueError: --prerendered takes one store folder'])
        self.assertIn('Nothing of this build was made yet; earlier builds in the build folder are kept and taken back.',
                      tip)
        self.assertIn('  ./build.sh --prerendered a b', tip)
        refused = build_failure.bare_record(SystemExit('Build refused before its first stage: a focus box'))
        self.assertEqual(refused['error'], 'Build refused before its first stage: a focus box')

    def test_the_docker_builder_says_how_to_run_it_again(self):
        with tempfile.TemporaryDirectory() as tmp, no_swap_read():
            run = stopped_run(tmp, CHIM)
            tip = build_failure.tip_lines(build_failure.record(run), run, environ={'AW_RUNTIME': 'docker-builder'})
        self.assertIn('This build ran in the AmiWind Docker builder: run the same docker builder command again',
                      flat(tip))

    def test_a_cancelled_build_says_its_work_is_kept(self):
        args = SimpleNamespace(_argv=['--data-files', '/owned', '--name', 'x', '--reuse-from', '/w/build/older'])
        with tempfile.TemporaryDirectory() as tmp:
            hint = build.cancel_hint(args, Path(tmp))
            self.assertIn('Your finished work is kept: run the same command again, from the same folder, to continue:',
                          hint)
            self.assertIn('--reuse-from %s' % tmp, hint)
        self.assertIn('--reuse-from /w/build/older', build.cancel_hint(args, Path('/no/such/run')))

    def test_the_monitor_s_reader_reads_no_file_of_the_run_for_the_tip(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = stopped_run(tmp, CHIM)
            with mock.patch.object(build_failure, 'build_memory_seen', side_effect=AssertionError('read')), \
                    mock.patch.object(build_failure, '_history_row', side_effect=AssertionError('read')):
                rec, text = build_failure.derive(run, path=lambda *parts: run.joinpath(*parts))
            self.assertIn('## What to do now', text)
            self.assertIn('(measured in the v0.0.66 from-scratch build)', flat(text.splitlines()))


class SwapTests(unittest.TestCase):
    """The swap on each operating system, through stand-ins for the files, sysctl and the Windows kernel."""

    def test_linux(self):
        meminfo = 'MemTotal: 32768000 kB\nSwapTotal:       16777216 kB\nSwapFree:        12582912 kB\n'
        self.assertEqual(build_report.swap('Linux', read=lambda path: meminfo if path == '/proc/meminfo' else None),
                         (16 << 30, 12 << 30, '/proc/meminfo'))
        self.assertEqual(build_report.swap('Linux', read=lambda path: None), (None, None, '/proc/meminfo did not answer'))
        text = build_report.swap_text('Linux', read=lambda path: meminfo, cgroup=lambda path: '0')
        self.assertEqual(text, '16.0 GiB total, 12.0 GiB free (/proc/meminfo); the container allows no swap (cgroup '
                               'memory.swap.max 0)')
        none = 'SwapTotal: 0 kB\nSwapFree: 0 kB\n'
        self.assertEqual(build_report.swap_text('Linux', read=lambda path: none, cgroup=lambda path: str(4 << 30)),
                         'none (/proc/meminfo); container swap limit 4.0 GiB')

    def test_macos(self):
        asked = []

        def run(command, **options):
            asked.append((command, options.get('timeout'), options.get('stdin')))
            return SimpleNamespace(returncode=0, stdout='total = 2048.00M  used = 512.00M  free = 1536.00M  (encrypted)\n')
        self.assertEqual(build_report.swap('Darwin', run=run), (2 << 30, 1536 << 20, 'sysctl vm.swapusage'))
        self.assertEqual(asked[0][0], ['sysctl', '-n', 'vm.swapusage'])
        self.assertTrue(asked[0][1] and asked[0][2] == subprocess.DEVNULL)

        def missing(command, **options):
            raise FileNotFoundError(command[0])
        self.assertEqual(build_report.swap('Darwin', run=missing), (None, None, 'sysctl vm.swapusage did not answer'))

    def test_windows(self):
        class Kernel:
            def __init__(self, answer):
                self.answer = answer

            def GlobalMemoryStatusEx(self, ref):
                status = ref._obj
                status.ullTotalPhys, status.ullAvailPhys = 16 << 30, 9 << 30
                status.ullTotalPageFile, status.ullAvailPageFile = 40 << 30, 30 << 30
                return self.answer
        self.assertEqual(build_report.swap('Windows', kernel32=Kernel(1)),
                         (24 << 30, 21 << 30, 'GlobalMemoryStatusEx: the commit limit less the physical memory'))
        self.assertEqual(build_report.swap('Windows', kernel32=Kernel(0)),
                         (None, None, 'GlobalMemoryStatusEx did not answer'))
        # the memory reader shares the call and still answers as before
        self.assertEqual(build_report.memory('Windows', kernel32=Kernel(1)), (16 << 30, 9 << 30, 'GlobalMemoryStatusEx'))
        self.assertEqual(build_report.swap_text('FreeBSD'), 'Not available (no swap reader for FreeBSD)')


class MachineLinesTests(unittest.TestCase):
    def test_the_build_prints_its_machine_at_its_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = build.parser().parse_args(['--workspace', tmp, '--jobs', '2'])
            lines = build_report.start_lines(args, ROOT)
        self.assertEqual(lines[0], 'Machine at the start of the build (a failed build\'s report has it again):')
        self.assertEqual([row.split(':')[0].strip() for row in lines[1:]],
                         ['Operating system', 'Container', 'Python', 'Cores', 'Memory', 'Swap', 'Free space'])
        text = (ROOT / 'tools' / 'build.py').read_text(encoding='utf-8')
        start = text.index('def _main(')
        # printed before the build records its inputs, the first long step of a build
        self.assertLess(text.index('build_report.start_lines(args, ROOT)', start),
                        text.index('Recording input, tool and source checksums', start))

    def test_the_report_names_the_peaks_beside_the_memory_the_build_saw(self):
        with tempfile.TemporaryDirectory() as tmp, no_swap_read():
            run = stopped_run(tmp, CHIM)
            build_failure.write(run)
            ctx = SimpleNamespace(run=run, workspace=Path(tmp),
                                  failed_stages=lambda: [{'name': 'chim', 'status': 'failed'}])
            text = build_report.memory_peak_text(ctx)
        self.assertEqual(text, '31.6 GiB of the 32.0 GiB the build saw (the container\'s limit), with chim, '
                               'chim-room-batches running; the failed stage chim reached 25.1 GiB, its largest process '
                               '24.1 GiB (measured in this build)')


class PublicTextTests(unittest.TestCase):
    def test_public_text_rules(self):
        with tempfile.TemporaryDirectory() as tmp, no_swap_read():
            tip = '\n'.join(build_failure.write(stopped_run(tmp, CHIM))['tip'])
        # "the maintainer" only, no private messaging, no machine words (the private words are checked by the
        # maintainer's own tooling, not here)
        for text in (tip, Path(__file__).read_text(encoding='utf-8'),
                     (ROOT / 'config' / 'build-memory.json').read_text(encoding='utf-8')):
            lowered = text.lower()
            for word in ('the ' + 'owner', ' cha' + 't ', 'chann' + 'el', 'work' + 'station'):
                self.assertNotIn(word, lowered)


if __name__ == '__main__':
    unittest.main()
