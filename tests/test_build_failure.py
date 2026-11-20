# SPDX-License-Identifier: GPL-3.0-only
"""A failed build writes its failure details (tools/build_failure.py, BUILD-FAILURE-NO-DETAILS-66): FAILURE.md and
failure.json beside the logs, with the failed stage, its exit and error line, the traceback, the last 60 lines of its
log, the units it left out, the commit and the command that builds again from the run; the stage's own process prints
the traceback of the error it exits on (the read-trace hook, tools/build_cache.py); the Toolkit Monitor serves the page
as text and shows the failed stage under Progress. Fixture stages only, no game data."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build  # noqa: E402
import build_cache  # noqa: E402
import build_failure  # noqa: E402
import build_profile  # noqa: E402
import monitor_read  # noqa: E402
import toolkit_serve  # noqa: E402
from build_parallel import execute_parallel  # noqa: E402

POSIX = os.name == 'posix'
RUN = '2026_11_14_v0.0.66-dev2_full_abc1234'
# A stage that fails as the CHIM stage of the v0.0.66-dev2 build did: a path outside the data folder, caught and
# reported as one "Error: ..." line by argparse's exit, after its unit lines and the rooms it did not convert.
STAGE = '\n'.join([
    'import argparse',
    'from pathlib import Path',
    '',
    '',
    'def source_name(path):',
    "    return Path(path).relative_to('/owned')",
    '',
    '',
    'def main():',
    '    ap = argparse.ArgumentParser()',
    '    for unit in range(80):',
    "        print('unit %02d converted' % unit, flush=True)",
    "    print('not converted: Sotha Sil, Inner Flooded Halls: no placements', flush=True)",
    "    print('not converted: Mournhold, Royal Palace: an exterior-like cell', flush=True)",
    '    try:',
    "        source_name('/elsewhere/Tribunal.esm')",
    '    except ValueError as exc:',
    "        ap.exit(1, 'Error: %s\\n' % exc)",
    '',
    '',
    'main()',
    ''])
META = {'run_name': {'commit': 'abc1234', 'version': '0.0.66-dev2'},
        'build_argv': ['--stage', 'aga', '--name', RUN, '--jobs', '4', '--reuse-from', '/work/build/older']}


def failed_run(builds, status='failed', with_files=False):
    """A failed run folder as a build leaves it (build-state.json, a stage log with a traceback)."""
    run = Path(builds) / RUN
    (run / 'logs').mkdir(parents=True)
    (run / 'build-progress.json').write_text(json.dumps({'run': RUN, 'status': status, 'percent': 74.3,
                                                        'stages': [{'name': 'chim', 'status': 'failed'}]}))
    (run / 'build-state.json').write_text(json.dumps({
        'status': status, 'run_name': META['run_name'], 'build_argv': META['build_argv'],
        'steps': [{'name': 'census', 'status': 'passed', 'log': '/work/build/%s/logs/03-census.log' % RUN},
                  {'name': 'chim', 'status': 'failed' if status == 'failed' else 'running', 'returncode': 1,
                   'log': '/work/build/%s/logs/27-chim.log' % RUN, 'elapsed_seconds': 2463.0, 'jobs': 12},
                  {'name': 'rooms', 'status': 'cancelled', 'log': '/work/build/%s/logs/28-rooms.log' % RUN}],
        'not_started': ['image']}))
    (run / 'logs' / '27-chim.log').write_text(
        ''.join('CHIM frame %d\n' % i for i in range(100)) +
        "Error: '/elsewhere/Tribunal.esm' is not in the subpath of '/owned'\n"
        '[stage] the traceback of the error above:\n'
        'Traceback (most recent call last):\n'
        '  File "/src/tools/chim_build.py", line 40, in main\n'
        '    receipt = source_receipt(data)\n'
        "ValueError: '/elsewhere/Tribunal.esm' is not in the subpath of '/owned'\n")
    if with_files:
        build_failure.write(run)
    return run


class FixtureBuildTests(unittest.TestCase):
    """A fixture build whose stage fails: the failure files, the traceback, the log tail, the build again command."""

    def build(self, tmp, parallel, script):
        run = Path(tmp) / 'build' / RUN
        # stage names the scheduler does not know: each waits for the one before it
        steps = [('first', [sys.executable, '-c', 'print("first result")']),
                 ('convert', [sys.executable, str(script)]),
                 ('later', [sys.executable, '-c', 'print("must not run")'])]
        build_cache.CLOSURES[str(run)] = {'root': str(ROOT), 'stages': {}}   # the read-trace hook in the run
        try:
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, 'convert failed'):
                if parallel:
                    execute_parallel(steps, run, dict(META, compiler_jobs=2), ROOT)
                else:
                    build.execute(steps, run, dict(META))
        finally:
            build_cache.CLOSURES.pop(str(run), None)
        return run

    @unittest.skipUnless(POSIX, 'the stage wrapper and its read-trace hook run on POSIX')
    def test_a_failed_stage_writes_failure_md_with_the_traceback_and_the_log_tail(self):
        for parallel in (False, True):
            with self.subTest(parallel=parallel), tempfile.TemporaryDirectory() as tmp:
                script = Path(tmp) / 'stage_chim.py'
                script.write_text(STAGE)
                run = self.build(tmp, parallel, script)
                rec = json.loads((run / 'failure.json').read_text())
                self.assertEqual((rec['schema'], rec['source'], rec['stage']), (build_failure.SCHEMA, 'build', 'convert'))
                self.assertIn('Tribunal.esm', rec['error'])
                stage = rec['failed_stages'][0]
                self.assertEqual((stage['name'], stage['number'], stage['returncode'], stage['log']),
                                 ('convert', 2, 1, 'logs/02-convert.log'))
                # the stage printed its error line and, from the hook, the traceback of the error under it
                log = (run / 'logs' / '02-convert.log').read_text()
                self.assertIn("Error: '/elsewhere/Tribunal.esm'", log)
                self.assertIn('[stage] the traceback of the error above:', log)
                self.assertEqual(stage['traceback'][0], build_failure.TRACEBACK_START)
                self.assertTrue(any('in source_name' in line for line in stage['traceback']), stage['traceback'])
                self.assertTrue(stage['traceback'][-1].startswith('ValueError: '), stage['traceback'])
                self.assertTrue(any(line.startswith('Error: ') for line in stage['error_lines']))
                # the last 60 lines of the log, the rooms it did not convert, the commit, the command to build again
                self.assertEqual(len(stage['tail']), 60)
                self.assertNotIn('unit 00 converted', stage['tail'])
                self.assertEqual(stage['tail'], log.splitlines()[-60:])
                self.assertEqual(stage['left_out_count'], 2)
                self.assertIn('not converted: Sotha Sil, Inner Flooded Halls: no placements', stage['left_out'])
                self.assertEqual((rec['commit'], rec['version']), ('abc1234', '0.0.66-dev2'))
                self.assertEqual(rec['resume']['command'], 'python3 tools/build.py --stage aga --jobs 4 --reuse-from '
                                 + str(run))
                if parallel:
                    self.assertEqual(rec['not_started'], ['later'])
                page = (run / 'FAILURE.md').read_text()
                for part in ('# Build failure: ' + RUN, '- **Failed stage:** convert (stage 2, exit 1', '## Traceback',
                             'in source_name', '## Units refused or left out: 2', 'Royal Palace',
                             '## The last 60 lines of logs/02-convert.log', '- **Commit:** abc1234, version 0.0.66-dev2',
                             '--reuse-from ' + str(run)):
                    self.assertIn(part, page)
                self.assertEqual((run / 'logs' / '01-first.log').read_text().strip(), 'first result')

    def test_a_stage_that_dies_of_an_exception_keeps_its_own_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / 'stage_crash.py'
            script.write_text('def load(table):\n    return table["census"]\n\n\nprint("loading")\nload({})\n')
            run = self.build(tmp, False, script)
            rec = json.loads((run / 'failure.json').read_text())
            stage = rec['failed_stages'][0]
            self.assertEqual(rec['error'], "KeyError: 'census'")
            self.assertTrue(any('in load' in line for line in stage['traceback']))
            self.assertEqual(stage['tail'][0], 'loading')


class RecordTests(unittest.TestCase):
    def test_the_builder_s_own_error_outside_the_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / RUN
            (run / 'logs').mkdir(parents=True)
            (run / 'build-state.json').write_text(json.dumps({'status': 'failed', 'run_name': META['run_name'],
                                                              'steps': [{'name': 'census', 'status': 'passed'}]}))

            def refuse():
                raise ValueError('World map collision check refused the plan before any stage')
            try:
                refuse()
            except ValueError as exc:
                rec = build_failure.write(run, exc)
            self.assertEqual((rec['stage'], rec['failed_stages']), (None, []))
            self.assertEqual(rec['error'], 'ValueError: World map collision check refused the plan before any stage')
            self.assertTrue(any('in refuse' in line for line in rec['builder_error']['traceback']))
            page = (run / 'FAILURE.md').read_text()
            self.assertIn('- **Failed:** the build itself, outside its stages', page)
            self.assertIn("## The builder's error", page)
            self.assertIn('did not record its options', page)
            # written again without an error (the command line tool), the builder's error stays
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(build_failure.main([str(run)]), 0)
            self.assertIn('Failure details: ', out.getvalue())
            self.assertIn('builder_error', json.loads((run / 'failure.json').read_text()))

    def test_report_prints_the_page_and_keeps_what_the_stage_wrote(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = failed_run(tmp, with_files=True)
            before = (run / 'failure.json').read_text()
            out = io.StringIO()
            rec = build_failure.report(run, RuntimeError('chim failed. Earlier results are retained.'), out)
            self.assertEqual(rec['stage'], 'chim')
            self.assertEqual((run / 'failure.json').read_text(), before)      # not written again
            text = out.getvalue()
            self.assertTrue(text.startswith('=== FAILURE DETAILS (also in %s) ===' % (run / 'FAILURE.md')))
            self.assertIn('## Traceback', text)
            self.assertTrue(text.rstrip().endswith('=== END OF FAILURE DETAILS ==='))
            self.assertIsNone(build_failure.report(Path(tmp) / 'no-such-run', None, out))

    def test_record_of_a_failed_run_names_the_stopped_stages_and_the_run_as_the_builder_saw_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            rec = build_failure.write(failed_run(tmp))
            self.assertEqual((rec['cancelled_stages'], rec['not_started']), (['rooms'], ['image']))
            self.assertEqual(rec['failed_stages'][0]['number'], 27)
            self.assertIn('--reuse-from /work/build/%s' % RUN, rec['resume']['command'])
            self.assertNotIn('older', rec['resume']['command'])
            page = (Path(tmp) / RUN / 'FAILURE.md').read_text()
            self.assertIn('- **Not completed:** 1 stage not started: image; cancelled with it: rooms', page)
            self.assertIn('after 41 min 3 s, 12 workers', page)

    def test_the_page_carries_the_settings_from_the_run_s_own_files(self):
        # the one page (BUILD-FAILURE-NO-DETAILS-66 with BUILD-FAILURE-REPORT-66): the options as given, the file with
        # every option's value, the builder, its masters, the data folder, the AMIWIND_ settings the failed stage read
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / 'ws'
            run = failed_run(workspace / 'build')
            state = json.loads((run / 'build-state.json').read_text())
            state.update({'builder_options': {'builder': 'chim', 'chim_areas': ['balmora', 'seyda']},
                          'expansion_layers': {'masters': ['Morrowind.esm', 'Tribunal.esm']}, 'data_files': '/owned'})
            (run / 'build-state.json').write_text(json.dumps(state))
            (run / 'build-recipe.json').write_text('{"options": {}}')
            (run / 'profile').mkdir()
            (run / 'profile' / 'fingerprints.json').write_text(json.dumps({
                'chim': {'environment': {'AMIWIND_LAVA': 'quake', 'AMIWIND_HEAP_MB': None,
                                         'AMIWIND_MESH_SEAM_STOP': 'warn'}},
                'census': {'environment': {'AMIWIND_NOT_THIS_STAGE': '1'}}}))
            rec = build_failure.write(run)
            found = rec['settings']
            self.assertEqual(found['command_line'], META['build_argv'])
            self.assertEqual((found['recipe'], found['builder'], found['masters'], found['data_files']),
                             ('build-recipe.json', 'chim (CHIM areas: balmora, seyda)', ['Morrowind.esm', 'Tribunal.esm'],
                              '/owned'))
            self.assertEqual(found['stages'], {'chim': {'AMIWIND_LAVA': 'quake', 'AMIWIND_MESH_SEAM_STOP': 'warn'}})
            self.assertNotIn('report', rec)                                   # no build report written yet
            page = (run / 'FAILURE.md').read_text()
            for part in ('## Build settings', 'tools/build.py --stage aga --name %s --jobs 4' % RUN,
                         '- **Every option with its value:** build-recipe.json in the run folder',
                         '- **Builder:** chim (CHIM areas: balmora, seyda)',
                         '- **Masters, in load order:** Morrowind.esm, Tribunal.esm', '- **Game data:** /owned',
                         'The AMIWIND_ settings the stage chim read', 'AMIWIND_LAVA=quake\nAMIWIND_MESH_SEAM_STOP=warn'):
                self.assertIn(part, page)
            self.assertNotIn('AMIWIND_HEAP_MB', page)                         # not set: left out
            self.assertNotIn('AMIWIND_NOT_THIS_STAGE', page)                  # another stage's settings
            self.assertLess(page.index('## Build settings'), page.index('## Build again from this run'))
            # the build report written next is named in the page, which the build then prints
            report = workspace / 'logs' / ('BUILD-REPORT-%s.txt' % RUN)
            report.parent.mkdir()
            report.write_text('the full report')
            out = io.StringIO()
            build_failure.report(run, None, out)
            self.assertIn('- **Full report:** %s (every option' % report, out.getvalue())
            self.assertEqual(json.loads((run / 'failure.json').read_text())['report'], str(report))
            self.assertEqual(build_failure.last_line(run).split(' (')[0], 'Failure details: %s' % (run / 'FAILURE.md'))

    def test_the_page_of_a_run_on_a_read_only_volume_goes_elsewhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = failed_run(Path(tmp) / 'build')
            before = sorted(p.name for p in run.iterdir())
            out_dir = Path(tmp) / 'pages'
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(build_failure.main([str(run), '--out', str(out_dir)]), 0)
            self.assertEqual(sorted(p.name for p in run.iterdir()), before)  # the run is only read
            self.assertIn('Failure details: %s' % (out_dir / 'FAILURE.md'), out.getvalue())
            self.assertEqual(json.loads((out_dir / 'failure.json').read_text())['source'], 'command')
            self.assertIn('## Build settings', (out_dir / 'FAILURE.md').read_text())

    def test_what_was_not_completed_when_the_build_stopped_before_its_stages(self):
        self.assertEqual(build_failure.not_completed({'failed_stages': [], 'stages_recorded': 0}),
                         'the whole build: it stopped before its stages ran')
        self.assertEqual(build_failure.not_completed({'failed_stages': [{'left_out_count': 2}], 'stages_recorded': 3}),
                         '2 units refused or left out (listed below)')
        self.assertEqual(build_failure.not_completed({'failed_stages': [{}], 'stages_recorded': 3}),
                         'no other stage was stopped or left to run')

    def test_the_command_to_build_again_leaves_the_options_of_the_failed_run_out(self):
        command = build_failure.resume_command(
            ['--data-files', '/owned', '--source-commit', 'c9d30f8', '--name=old', '--jobs', '24',
             '--save-recipe', '/work/build/old/build-recipe.json', '--reuse-from', '/work/build/older',
             '--allow-rebuild', 'chim:a reason'], '/work/build/old')
        self.assertEqual(command, "python3 tools/build.py --data-files /owned --jobs 24 --allow-rebuild 'chim:a reason' "
                                  '--reuse-from /work/build/old')

    def test_the_log_scan_reads_only_the_end_of_a_large_log_and_chained_tracebacks(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / '05-x.log'
            log.write_text('early line\n' * 50000 + 'Traceback (most recent call last):\n  File "a.py", line 1, in f\n'
                           'OSError: disk\n\nDuring handling of the above exception, another exception occurred:\n\n'
                           'Traceback (most recent call last):\n  File "a.py", line 3, in g\nRuntimeError: stage\n'
                           'more\n  details\n')
            scan = build_failure.scan_log(log, max_bytes=4096)
            self.assertGreater(scan['scanned_from'], 0)
            self.assertEqual(scan['traceback'][0], build_failure.TRACEBACK_START)
            self.assertIn('OSError: disk', scan['traceback'])
            self.assertIn(build_failure.CHAINED[0], scan['traceback'])
            self.assertEqual(scan['traceback'][-3:], ['RuntimeError: stage', 'more', '  details'])
            self.assertEqual(build_failure.headline(scan), 'RuntimeError: stage')

    def test_public_text_rules(self):
        # public builder files: "the maintainer" only, and none of the private communication words (the full private
        # word lists are checked by the maintainer's own tooling, not here; this comment avoids the words it forbids)
        with tempfile.TemporaryDirectory() as tmp:
            page = build_failure.render(build_failure.record(failed_run(tmp)))
        for text in (page, (ROOT / 'tools' / 'build_failure.py').read_text(encoding='utf-8'),
                     Path(__file__).read_text(encoding='utf-8')):
            lowered = text.lower()
            for word in ('the ' + 'owner', ' cha' + 't ', 'chann' + 'el'):
                self.assertNotIn(word, lowered)


TRACE = ['Traceback (most recent call last):', '  File "/opt/amiwind/tools/chim_room_batches.py", line 310, in bake',
         '    result = convert(room)']
# Recorded tracebacks of each kind (BUILD-REPORT-MACHINE-ALL-OS-67): a pool worker ended by the system, a numpy array
# Python could not allocate, a write on a full disk, a write past a quota, a read of a shared folder failing with errno 12
BROKEN_POOL = TRACE + [
    '  File "/usr/lib/python3.12/concurrent/futures/_base.py", line 449, in result',
    '    return self.__get_result()',
    'concurrent.futures.process.BrokenProcessPool: A process in the process pool was terminated abruptly while the '
    'future was running or pending.']
ARRAY_MEMORY = TRACE + ['numpy.core._exceptions._ArrayMemoryError: Unable to allocate 64.0 GiB for an array with shape '
                        '(2048, 2048, 2048) and data type float64']
NO_SPACE = TRACE + ["OSError: [Errno 28] No space left on device: '/work/build/r/chim-room-batches/id1/maps/x.bsp'"]
QUOTA = TRACE + ["OSError: [Errno 122] Disk quota exceeded: '/work/cache/asset-pool-v1/ab/cd'"]
SHARED_READ = TRACE + ["OSError: [Errno 12] Cannot allocate memory: '/src/tools/release-files.json'"]


def stage_row(traceback=(), returncode=1, tail=(), error_lines=()):
    return {'name': 'chim-room-batches', 'returncode': returncode, 'traceback': list(traceback), 'tail': list(tail),
            'error_lines': list(error_lines)}


class KindTests(unittest.TestCase):
    """The failure's kind at the top of FAILURE.md and of the build report: out of memory and out of disk by their
    marks, proven or likely, with what was found and what to do (BUILD-REPORT-MACHINE-ALL-OS-67)."""

    def kind(self, *rows, error=None, **options):
        return build_failure.kinds({'failed_stages': list(rows)}, error, **options)

    def test_each_kind_by_its_recorded_traceback(self):
        for name, rows, kind, proof, said in (
                ('pool worker ended', [stage_row(BROKEN_POOL)], build_failure.MEMORY, 'likely, not proven',
                 'a worker process of a pool was ended'),
                ('numpy array', [stage_row(ARRAY_MEMORY)], build_failure.MEMORY, 'proven', 'MemoryError'),
                ('full disk', [stage_row(NO_SPACE)], build_failure.DISK, 'proven', 'errno 28 (ENOSPC)'),
                ('quota', [stage_row(QUOTA)], build_failure.DISK, 'proven', 'errno 122 (EDQUOT)'),
                ('shared read', [stage_row(SHARED_READ)], build_failure.MEMORY, 'likely, not proven',
                 'a read from a shared folder can also end so'),
                ('signal 9', [stage_row(returncode=-9)], build_failure.MEMORY, 'likely, not proven',
                 'was ended by signal 9 (exit -9)'),
                ('shell exit 137', [stage_row(returncode=137)], build_failure.MEMORY, 'likely, not proven',
                 'was ended by signal 9 (exit 137)'),
                ('Killed line', [stage_row(error_lines=['bash: line 1:  4242 Killed    python3 tools/x.py'])],
                 build_failure.MEMORY, 'likely, not proven', 'ended by signal 9 (SIGKILL)')):
            with self.subTest(name):
                found = self.kind(*rows)
                self.assertEqual([(row['kind'], row['proof']) for row in found], [(kind, proof)])
                self.assertIn(said, '; '.join(found[0]['marks']))
                self.assertEqual(found[0]['advice'], build_failure.KIND_ADVICE[kind])
        # no mark: no kind; a mark only in the last log lines is a hint, never a proof
        self.assertEqual(self.kind(stage_row(TRACE + ['ValueError: a seam stop'])), [])
        hint = self.kind(stage_row(TRACE + ['ValueError: a seam stop'], tail=['MemoryError while caching, retried']))
        self.assertEqual((hint[0]['proof'], hint[0]['marks']),
                         ('likely, not proven', ['MemoryError: Python could not get the memory it asked for (in the last '
                                                 'log lines)']))

    def test_the_builder_s_own_error_and_what_it_was_raised_from(self):
        try:
            try:
                raise OSError(28, 'No space left on device')
            except OSError as exc:
                raise RuntimeError('the image step failed') from exc
        except RuntimeError as exc:
            error = exc
        self.assertEqual([(row['kind'], row['proof']) for row in self.kind(error=error)],
                         [(build_failure.DISK, 'proven')])
        self.assertEqual(self.kind(error=MemoryError())[0]['proof'], 'proven')
        self.assertEqual(self.kind(error=ValueError('a seam stop')), [])
        record = build_failure.kinds({'builder_error': {'type': 'OSError', 'message': '[Errno 122] Disk quota exceeded'}})
        self.assertEqual(record[0]['kind'], build_failure.DISK)

    def test_in_the_failing_build_the_kill_counter_proves_it_and_the_free_space_is_shown(self):
        files = {'/proc/self/cgroup': '0::/docker/abc\n', '/sys/fs/cgroup/docker/abc/memory.events':
                 'low 0\nhigh 0\nmax 4\noom 2\noom_kill 1\noom_group_kill 0\n'}
        self.assertEqual(build_failure.oom_kills(files.get), 1)
        # cgroup v1: memory.oom_control; no counter anywhere: None
        self.assertEqual(build_failure.oom_kills({'/sys/fs/cgroup/memory/memory.oom_control':
                                                  'oom_kill_disable 0\nunder_oom 0\noom_kill 3\n'}.get), 3)
        self.assertIsNone(build_failure.oom_kills({}.get))
        saved = dict(build_failure._START)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                build_failure.note_start(tmp, read=files.get)
                files['/sys/fs/cgroup/docker/abc/memory.events'] = 'oom 4\noom_kill 3\n'
                found = self.kind(stage_row(BROKEN_POOL), live=True, read=files.get)
                self.assertEqual(found[0]['proof'], 'proven')
                self.assertEqual(found[0]['found'], ['the memory controller ended 2 processes for memory during the build '
                                                     '(cgroup oom_kill 1 -> 3)'])
                build_failure.note_start(tmp, read=files.get)       # the counter did not rise this time
                found = self.kind(stage_row(BROKEN_POOL), live=True, read=files.get)
                self.assertEqual(found[0]['proof'], 'not proven')
                self.assertIn('stayed at 3', found[0]['found'][0])
                self.assertEqual(self.kind(stage_row(BROKEN_POOL), live=True, read={}.get)[0]['proof'],
                                 'likely, not proven')
                disk = self.kind(stage_row(NO_SPACE), live=True, workspace=tmp)
                self.assertRegex(disk[0]['found'][0], r'^free space at the start and now: workspace \S+ \S+, now \S+ \S+; '
                                                      r'temp folder \S+ \S+, now \S+ \S+$')
        finally:
            build_failure._START.clear()
            build_failure._START.update(saved)

    def test_failure_md_names_the_kind_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = failed_run(tmp)
            (run / 'logs' / '27-chim.log').write_text('\n'.join(['CHIM frame 1'] + NO_SPACE) + '\n')
            rec = build_failure.write(run)
            page = (run / 'FAILURE.md').read_text(encoding='utf-8')
            bullets = [line for line in page.splitlines() if line.startswith('- **')]
            self.assertTrue(bullets[0].startswith('- **Kind:** OUT OF DISK (proven): errno 28 (ENOSPC)'), bullets[0])
            self.assertTrue(bullets[1].startswith('- **Found:** free space at the start and now: '), bullets[1])
            self.assertTrue(bullets[2].startswith('- **What to do:** free space in the workspace'), bullets[2])
            self.assertTrue(bullets[3].startswith('- **Failed stage:** chim'), bullets[3])
            self.assertEqual(json.loads((run / 'failure.json').read_text())['kinds'][0]['kind'], 'OUT OF DISK')
            self.assertEqual(rec['kinds'][0]['proof'], 'proven')
            # the Monitor's reader, later: the marks alone, without the free space of another moment
            derived, text = build_failure.derive(run)
            self.assertEqual(derived['kinds'][0]['found'], [])
            self.assertIn('- **Kind:** OUT OF DISK (proven)', text)
            # a failure without the marks names no kind
            plain = failed_run(Path(tmp) / 'plain', with_files=True)
            self.assertNotIn('**Kind:**', (plain / 'FAILURE.md').read_text(encoding='utf-8'))


class OptionMarkTests(unittest.TestCase):
    """Builder options read from a file written with a byte-order mark (BUILD-FLAGS-MARK-SILENT-REFUSAL-66)."""

    def test_the_builder_removes_a_leading_mark_and_refuses_any_other_by_name(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()), \
                self.assertRaises(SystemExit) as done:
            build.main(['﻿--help'])
        self.assertEqual(done.exception.code, 0)                          # read as --help, not refused
        self.assertIn('--data-files', out.getvalue())
        with self.assertRaises(SystemExit) as done:
            build.main(['--check', '--name﻿', 'x'])
        self.assertIn("option '--name\\ufeff' holds a byte-order mark (U+FEFF)", str(done.exception.code))

    def test_the_refused_check_page(self):
        page = build_failure.render_refusal(RUN, ['build check: build.py: error: unrecognized arguments: x',
                                                  "the build check's own output, its last 2 lines:\n  a\n  b"],
                                            ['usage: build.py', 'build.py: error: unrecognized arguments: x'],
                                            'abc1234', 'v0.0.66-dev2')
        self.assertIn('# Build refused: ' + RUN, page)
        self.assertIn('- **Error:** build check: build.py: error: unrecognized arguments: x', page)
        self.assertIn("## The last 2 lines of the check's own output", page)
        self.assertNotIn("its last 2 lines:\n  a", page)                   # the block is the lines themselves


class HookTests(unittest.TestCase):
    """The read-trace hook prints the traceback of the error the stage's own process exits on, and nothing else."""

    @unittest.skipUnless(POSIX, 'the read-trace hook runs on POSIX')
    def test_only_the_stage_s_own_process_and_only_an_error_exit_print_it(self):
        code = ('import sys\ntry:\n    {}["key"]\nexcept KeyError:\n    sys.exit(int(sys.argv[1]))\n')
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / 'run'
            (run / 'profile').mkdir(parents=True)
            self.assertTrue(build_cache.write_trace_hook(run, ROOT))
            base = dict(os.environ, PYTHONPATH=str(run / 'profile' / build_profile.TRACE_HOOK_FOLDER),
                        **{build_profile.TRACE_ENV: str(run / 'profile' / 'reads.txt')})
            # another process id (none runs as 99999999): the hook is off, as in the stage's workers and tools
            for owner, status, printed in ((os.getpid(), 3, True), (os.getpid(), 0, False), (99999999, 3, False),
                                           (None, 3, False)):
                env = dict(base)
                env.pop(build_profile.STAGE_WRAPPER_ENV, None)
                if owner is not None:
                    env[build_profile.STAGE_WRAPPER_ENV] = str(owner)
                done = subprocess.run([sys.executable, '-c', code, str(status)], env=env, capture_output=True, text=True)
                self.assertEqual(done.returncode, status)                 # how the process ends never changes
                self.assertEqual('Traceback (most recent call last):' in done.stderr, printed, (owner, status, done.stderr))

    def test_the_stage_wrapper_names_itself_to_the_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            stats = Path(tmp) / 'profile' / 'stages' / '01-x.json'
            stats.parent.mkdir(parents=True)
            out = Path(tmp) / 'env.txt'
            code = 'import os, sys; open(sys.argv[1], "w").write(os.environ["%s"])' % build_profile.STAGE_WRAPPER_ENV
            done = subprocess.run([sys.executable, str(ROOT / 'tools' / 'build_profile.py'), '_stage', str(stats),
                                   str(Path(tmp) / 's.jsonl'), '--', sys.executable, '-c', code, str(out)],
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertTrue(out.read_text().isdigit())


class MonitorTests(unittest.TestCase):
    def test_the_reader_serves_the_written_page_and_derives_one_for_an_earlier_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            builds = Path(tmp) / 'build'
            failed_run(builds)
            r = monitor_read.Reader(builds)
            derived = r.answer({'op': 'failure', 'run': RUN})
            self.assertTrue(derived['ok'], derived)
            self.assertEqual((derived['source'], derived['failure']['stage']), ('derived', 'chim'))
            self.assertIn('## Traceback', derived['text'])
            self.assertFalse((builds / RUN / 'FAILURE.md').exists())         # read only: nothing written
            build_failure.write(builds / RUN)
            written = monitor_read.Reader(builds).answer({'op': 'failure', 'run': RUN})
            self.assertEqual((written['source'], written['text']), ('build', (builds / RUN / 'FAILURE.md').read_text()))
            for bad in ('..', '../x', 'a b'):
                self.assertFalse(r.answer({'op': 'failure', 'run': bad})['ok'])

    def test_a_run_that_did_not_fail_has_no_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            builds = Path(tmp) / 'build'
            failed_run(builds, status='running')
            a = monitor_read.Reader(builds).answer({'op': 'failure', 'run': RUN})
            self.assertEqual((a['ok'], a['failure'], a['text']), (True, None, None))

    def test_the_reader_container_loads_the_failure_code_beside_itself(self):
        # the reader container runs monitor_read.py isolated (-I): it finds tools/build_failure.py beside itself
        with tempfile.TemporaryDirectory() as tmp:
            builds = Path(tmp) / 'build'
            failed_run(builds)
            source = toolkit_serve.CommandBuilds([sys.executable, '-I', str(ROOT / 'tools' / 'monitor_read.py'),
                                                  '--root', 'builds=%s' % builds, '--serve'])
            try:
                answer = source.ask({'op': 'failure', 'run': RUN})
            finally:
                source.stop()
            self.assertEqual((answer['ok'], answer['source']), (True, 'derived'), answer)
        argv = toolkit_serve.docker_monitor_command('v')
        self.assertIn('target=/amiwind-monitor/build_failure.py,readonly', ' '.join(argv))
        self.assertEqual(argv[-5:-3], ['-I', '/amiwind-monitor/monitor_read.py'])

    def test_the_server_shows_failure_md_as_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            builds = Path(tmp) / 'build'
            failed_run(builds, with_files=True)
            other = Path(tmp) / 'build' / (RUN + '-running')
            (other / 'logs').mkdir(parents=True)
            (other / 'build-state.json').write_text('{"status": "running", "steps": []}')
            H = toolkit_serve.Handler
            saved = H.builds
            H.builds = toolkit_serve.Cached(toolkit_serve.LocalBuilds(builds))
            server = toolkit_serve.ThreadingHTTPServer(('127.0.0.1', 0), H)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            base = 'http://127.0.0.1:%d' % server.server_address[1]

            def get(path):
                try:
                    with urllib.request.urlopen(base + path, timeout=10) as reply:
                        return reply.status, reply.headers.get('Content-Type'), reply.read().decode('utf-8')
                except urllib.error.HTTPError as e:
                    return e.code, e.headers.get('Content-Type'), e.read().decode('utf-8')
            try:
                code, kind, text = get('/monitor/run/%s/FAILURE.md' % RUN)
                self.assertEqual((code, kind), (200, 'text/plain; charset=utf-8'))
                self.assertEqual(text, (builds / RUN / 'FAILURE.md').read_text())
                code, kind, text = get('/monitor/run/%s/failure.json' % RUN)
                self.assertEqual((code, json.loads(text)['failure']['stage']), (200, 'chim'))
                code, kind, text = get('/monitor/run/%s/FAILURE.md' % other.name)
                self.assertEqual((code, kind), (404, 'text/plain; charset=utf-8'))
                self.assertIn('No failure details', text)
                self.assertEqual(get('/monitor/run/..%2f..%2fx/FAILURE.md')[0], 400)
            finally:
                server.shutdown()
                server.server_close()
                H.builds = saved

    def test_the_page_carries_the_link_under_progress(self):
        html = (ROOT / 'amiwind-toolkit' / 'monitor.html').read_text(encoding='utf-8')
        progress = html.split('<section id="progresspanel">')[1].split('</section>')[0]
        self.assertIn('>Progress</h2>', progress)
        self.assertIn('id="failbox" hidden', progress)
        self.assertIn('>See failure details</a>', progress)
        self.assertLess(progress.index('id="overall"'), progress.index('id="failbox"'))
        self.assertLess(progress.index('id="failbox"'), progress.index('id="facts"'))
        self.assertIn("'/FAILURE.md'", html)
        self.assertIn("'/failure.json'", html)


if __name__ == '__main__':
    unittest.main()
