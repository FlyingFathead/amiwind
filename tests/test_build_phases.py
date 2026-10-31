"""Phases and the heartbeat (BUILD-PROFILE-SECTIONS-MISSING-36): every phase says when it starts and ends with
its time and cores, a silent stage still gets heartbeat lines from the builder, --quiet drops only per-unit
progress lines, none of it changes a stage output or key; the CHIM stats reuse the build's validation
(BUILD-CHIM-STATS-SERIAL-TAIL-36)."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import textwrap
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
import build  # noqa: E402
import build_cache  # noqa: E402
import build_profile  # noqa: E402
from build_parallel import execute_parallel  # noqa: E402

LINUX = build_profile.linux_proc()

# A stage that opens a phase with a counter, prints a progress line, then works silently, then writes its output.
SILENT_STAGE = textwrap.dedent('''
    import sys, time
    sys.path.insert(0, %r)
    import build_profile
    with build_profile.phase('Fake phase', '3 items', total=3, unit='items') as timer:
        timer.step(label='first', line=True)
        time.sleep(%r)
        timer.done('Fake phase: passed')
    open(sys.argv[1], 'w').write('result 42\\n')
''')


def silent_stage(out, seconds):
    return [sys.executable, '-c', SILENT_STAGE % (str(ROOT / 'tools'), seconds), str(out)]


class SideBySidePhaseTests(unittest.TestCase):
    def test_a_phase_that_ends_first_beside_another_leaves_the_stack(self):
        # BUILD-CHIM-STAGE-SERIAL-TAIL-36: the CHIM stats run in a thread beside the zone walk and can end first
        stream = io.StringIO()
        outer = build_profile.phase('CHIM stats', stream=stream).__enter__()
        inner = build_profile.phase('CHIM zone walk gate', stream=stream).__enter__()
        outer.__exit__(None, None, None)
        self.assertNotIn(outer, build_profile._phases)
        self.assertIs(build_profile._phases[-1], inner)
        inner.__exit__(None, None, None)
        self.assertNotIn(inner, build_profile._phases)

    def test_the_validation_key_is_worked_out_ahead_with_the_same_calls(self):
        # BUILD-CHIM-STAGE-SERIAL-TAIL-36: the validation's pass-cache key (about 20 s on one core) in a thread
        # beside the world build: the very calls PassCache.open makes for chim/validate.py, memoized per process
        import chim_build
        import pass_cache
        import chim.validate as V
        calls = []
        with patch.object(pass_cache, 'folder', return_value='/somewhere'), \
                patch.object(pass_cache, 'source_digest', side_effect=lambda *s, **k: calls.append(('d', s, k))), \
                patch.object(pass_cache, 'previous_digests', side_effect=lambda *s: calls.append(('p', s))), \
                patch.object(pass_cache, 'covered_lines', side_effect=lambda *s: calls.append(('c', s))):
            chim_build.warm_validation_key()
        self.assertEqual(calls, [('d', (V.__file__,), {}), ('p', (V.__file__,)), ('c', (V.__file__,))])
        source = (ROOT / 'tools/pass_cache.py').read_text(encoding='utf-8')
        self.assertIn('return cls(name, options, source_digest(*scripts), root, tally, previous_digests(*scripts),\n'
                      '                   covered=covered_lines(*scripts))', source)

    def test_the_chim_stats_run_beside_the_zone_walk_after_the_heap_gate(self):
        text = (ROOT / 'tools/chim_build.py').read_text(encoding='utf-8')
        submit = text.index('stats_job = stats_pool.submit(write_stats')
        self.assertLess(text.index("build_profile.phase('CHIM heap gate'"), submit)
        self.assertLess(submit, text.index('walk = require_zone_walk('))


class PhaseTests(unittest.TestCase):
    def run_phase(self, sections, env=None, fail=False):
        stream = io.StringIO()
        with patch.dict(os.environ, dict({build_profile.SECTIONS_ENV: str(sections)}, **(env or {}))):
            try:
                with build_profile.phase('CHIM stats', '273 frames', total=2, unit='frames', stream=stream) as timer:
                    timer.step(label='frames/x-01/y-01/frame.ccf', line=True)
                    now = build_profile.read_now(sections)
                    timer.step(label='frames/x-02/y-01/frame.ccf', line=True)
                    if fail:
                        raise ValueError('boom')
                    timer.done('CHIM stats: 2768 models')
            except ValueError:
                pass
        return stream.getvalue().splitlines(), now

    def test_start_progress_and_end_lines_with_time_and_cores(self):
        with tempfile.TemporaryDirectory() as temp:
            sections = Path(temp) / '32-chim.jsonl'
            lines, now = self.run_phase(sections)
            self.assertRegex(lines[0], r'^\[\+[0-9.hms]+\] CHIM stats: started, 273 frames$')
            self.assertEqual(lines[1], '[1/2 frames] CHIM stats: frames/x-01/y-01/frame.ccf')
            self.assertRegex(lines[-1], r'^\[\+[0-9.hms]+\] CHIM stats: 2768 models - took \d+\.\ds, \d+\.\d cores$')
            self.assertEqual((now['name'], now['done'], now['total'], now['unit']), ('CHIM stats', 1, 2, 'frames'))
            self.assertFalse(Path(str(sections) + build_profile.NOW_SUFFIX).exists())   # gone after the phase
            records = [json.loads(line) for line in sections.read_text().splitlines()]
            self.assertEqual([r.get('event') for r in records], ['start', None])
            self.assertTrue(records[1]['phase'] and records[1]['end_at'] >= records[1]['at'])
            self.assertEqual((records[1]['done'], records[1]['total']), (2, 2))
            rows = build_profile.read_sections(sections)          # the start event is not a second call
            self.assertEqual([(r['name'], r['calls'], r.get('phase')) for r in rows], [('CHIM stats', 1, True)])

    def test_failure_and_quiet(self):
        with tempfile.TemporaryDirectory() as temp:
            lines, _ = self.run_phase(Path(temp) / 'a.jsonl', fail=True)
            self.assertRegex(lines[-1], r'CHIM stats: FAILED \(ValueError\) - took ')
            quiet, _ = self.run_phase(Path(temp) / 'b.jsonl', env={build_profile.LOG_LEVEL_ENV: 'quiet'})
        # quiet drops the per-unit lines only: start and end with timing stay
        self.assertEqual(len(quiet), 2)
        self.assertTrue(quiet[0].endswith('CHIM stats: started, 273 frames'))
        self.assertIn(' - took ', quiet[1])

    def test_phase_works_without_the_profiler(self):
        stream = io.StringIO()
        with patch.dict(os.environ, {build_profile.SECTIONS_ENV: ''}):
            with build_profile.phase('Image: finalize', stream=stream):
                pass
        with patch.dict(os.environ, {build_profile.BUILD_EPOCH_ENV: str(time.time() - 125)}):
            self.assertTrue(build_profile.stamp().startswith('[+2m0'))
        self.assertTrue(stream.getvalue().splitlines()[0].endswith('Image: finalize: started'))
        self.assertRegex(stream.getvalue().splitlines()[1], r'^\[\+[0-9.hms]+\] Image: finalize: done - took ')

    def test_phase_table_targets_are_instrumented(self):
        for (stage, target), label in build_profile.PHASES.items():
            self.assertIn(target, build_profile.INSTRUMENT[stage], (stage, target))
            self.assertTrue(label)

    def test_logs_only_never_a_key(self):
        self.assertIn('tools/build_profile.py', build_cache.INSTRUMENTATION_MODULES)
        for name in (build_profile.LOG_LEVEL_ENV, build_profile.HEARTBEAT_ENV):
            self.assertIn(name, build_cache.IGNORED_ENV)
        # the local clock of the progress lines: a summer-time change must not rebuild a stage
        self.assertIn('AMIWIND_LOCAL_UTC_OFFSET', build_cache.IGNORED_ENV)

    def test_local_utc_offset_is_no_stage_input(self):
        script = Path(build_cache.ROOT) / 'tools' / 'chim_build.py'
        index = build_cache.SourceIndex(build_cache.ROOT)
        keys = []
        for value in ('+0300', '+0200', None):
            env = {k: v for k, v in os.environ.items() if k != 'AMIWIND_LOCAL_UTC_OFFSET'}
            if value is not None:
                env['AMIWIND_LOCAL_UTC_OFFSET'] = value
            with patch.dict(os.environ, env, clear=True):
                keys.append(build_cache.stage_environment(script, index))
        self.assertEqual(keys[0], keys[1])
        self.assertEqual(keys[0], keys[2])

    def test_build_log_level_option(self):
        class Args:
            quiet, log_level = False, None
        args = Args()
        with patch.dict(os.environ, {'AMIWIND_LOG_LEVEL': ''}):
            self.assertEqual(build.resolve_log_level(args), {'level': 'normal', 'selected_by': 'default'})
        args.quiet = True
        self.assertEqual(build.resolve_log_level(args)['level'], 'quiet')
        args.log_level = 'verbose'
        with self.assertRaises(SystemExit):
            build.resolve_log_level(args)
        args.quiet, args.log_level = False, 'verbose'
        self.assertEqual(build.resolve_log_level(args), {'level': 'verbose', 'selected_by': '--log-level'})
        args.log_level = None
        with patch.dict(os.environ, {'AMIWIND_LOG_LEVEL': 'quiet'}):
            self.assertEqual(build.resolve_log_level(args), {'level': 'quiet', 'selected_by': 'AMIWIND_LOG_LEVEL'})


@unittest.skipUnless(LINUX, 'the profiled builder (stage wrapper) needs Linux /proc')
class HeartbeatTests(unittest.TestCase):
    def build(self, root, env):
        out = root / 'out.txt'
        stream = io.StringIO()
        with patch.dict(os.environ, env), contextlib.redirect_stdout(stream):
            execute_parallel([('silent', silent_stage(out, 1.6))], root / 'run', {'compiler_jobs': 2}, root)
        log = (root / 'run' / 'logs' / '01-silent.log').read_text()
        return stream.getvalue(), log, hashlib.sha256(out.read_bytes()).hexdigest()

    def test_a_silent_stage_gets_heartbeat_lines_from_the_builder(self):
        with tempfile.TemporaryDirectory() as temp:
            output, log, digest = self.build(Path(temp), {build_profile.HEARTBEAT_ENV: '0.4'})
        beats = [line for line in output.splitlines() if '[heartbeat] silent:' in line]
        self.assertGreaterEqual(len(beats), 2, output)
        # the first beats may come before the stage printed anything; then the phase and its counter are named
        named = [line for line in beats if '[1/3 items] Fake phase: first: still working' in line]
        self.assertTrue(named, beats)
        self.assertRegex(named[0], r'no output for \d')
        self.assertIn('Fake phase: started, 3 items', log)
        self.assertIn('[1/3 items] Fake phase: first', log)
        self.assertRegex(log, r'Fake phase: passed - took \d+\.\ds')
        self.assertEqual(digest, hashlib.sha256(b'result 42\n').hexdigest())

    def test_quiet_keeps_start_end_and_heartbeat_and_outputs_are_identical(self):
        with tempfile.TemporaryDirectory() as temp:
            loud = self.build(Path(temp) / 'a', {build_profile.HEARTBEAT_ENV: '0.4',
                                                build_profile.LOG_LEVEL_ENV: 'normal'})
        with tempfile.TemporaryDirectory() as temp:
            quiet = self.build(Path(temp) / 'b', {build_profile.HEARTBEAT_ENV: '0.4',
                                                 build_profile.LOG_LEVEL_ENV: 'quiet'})
        with tempfile.TemporaryDirectory() as temp:
            off = self.build(Path(temp) / 'c', {build_profile.HEARTBEAT_ENV: 'off',
                                               build_profile.LOG_LEVEL_ENV: 'verbose'})
        self.assertNotIn('[1/3 items]', quiet[1])                  # the per-unit line is dropped ...
        self.assertIn('Fake phase: started', quiet[1])             # ... start and end are not
        self.assertIn('Fake phase: passed - took', quiet[1])
        self.assertIn('[heartbeat] silent:', quiet[0])
        self.assertRegex(quiet[0], r'\[\+[0-9.hms]+\] \[heartbeat\] silent:')
        self.assertNotIn('[heartbeat]', off[0])
        self.assertEqual({loud[2], quiet[2], off[2]}, {hashlib.sha256(b'result 42\n').hexdigest()})


class TimelinePhaseTests(unittest.TestCase):
    def test_stage_phases_from_the_sections_file(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            sections = folder / 'profile' / 'sections'
            sections.mkdir(parents=True)
            rows = [{'name': 'CHIM validation', 'event': 'start', 'phase': True, 'pid': 7, 'depth': 0, 'at': 100.0},
                    {'name': 'CHIM validation', 'phase': True, 'pid': 7, 'depth': 0, 'at': 100.0, 'end_at': 618.0,
                     'wall': 518.0, 'cores': 1.0},
                    {'name': 'inner', 'phase': True, 'pid': 7, 'depth': 1, 'at': 110.0, 'end_at': 120.0, 'cores': 1},
                    {'name': 'parallel map: x', 'pid': 7, 'depth': 0, 'start': 5.0, 'wall': 1.0},
                    {'name': 'CHIM stair gate', 'event': 'start', 'phase': True, 'pid': 7, 'depth': 0, 'at': 700.0}]
            (sections / '32-chim.jsonl').write_text('\n'.join(json.dumps(r) for r in rows) + '\n')
            (sections / '33-chim-town.jsonl').write_text('')
            phases = build_profile.stage_phases(folder, 'chim', 900.0)
        self.assertEqual([(p['name'], p['start'], p['end'], p['running']) for p in phases],
                         [('CHIM validation', 100.0, 618.0, False), ('CHIM stair gate', 700.0, 900.0, True)])


    @unittest.skipUnless(__import__('importlib').util.find_spec('PIL') is not None, 'Pillow is not installed')
    def test_the_timeline_draws_phase_strips(self):
        from test_build_timeline import START, finished_run
        with tempfile.TemporaryDirectory() as temp:
            run = finished_run(Path(temp))
            sections = run / 'profile' / 'sections'
            sections.mkdir(parents=True)
            rows = [{'name': 'World: convert', 'phase': True, 'pid': 1, 'depth': 0, 'at': START + 1, 'end_at': START + 400,
                     'wall': 399, 'cores': 3.0},
                    {'name': 'World: check', 'event': 'start', 'phase': True, 'pid': 1, 'depth': 0, 'at': START + 400}]
            (sections / '02-world.jsonl').write_text('\n'.join(json.dumps(r) for r in rows) + '\n')
            data = build_profile.timeline_data([build_profile.timeline_run(run)], offset=3 * 3600)
            world = next(row for row in data['runs'][0]['stages'] if row['name'] == 'world')
            self.assertEqual([p['name'] for p in world['phases']], ['World: convert', 'World: check'])
            self.assertTrue(world['phases'][1]['running'])
            png = build_profile.render_timeline(data)
        self.assertEqual(png[:8], b'\x89PNG\r\n\x1a\n')


class UnderuseTests(unittest.TestCase):
    """BUILD-UNDERUSE-GATE-36: any stage or phase over 30 s on under half of its stage's workers is a fix item."""

    def profile(self):
        sections = [{'name': 'CHIM statistics', 'phase': True, 'calls': 1, 'wall': 464.0, 'cores_avg': 1.0, 'min_depth': 0},
                    {'name': 'CHIM heap gate', 'phase': True, 'calls': 1, 'wall': 21.0, 'cores_avg': 1.0, 'min_depth': 0},
                    {'name': 'CHIM world conversion', 'phase': True, 'calls': 1, 'wall': 990.0, 'cores_avg': 17.8,
                     'min_depth': 0},
                    {'name': 'parallel map: inner', 'calls': 1, 'wall': 300.0, 'cores_avg': 1.0, 'min_depth': 2},
                    {'name': 'exec qbsp', 'calls': 9, 'wall': 90.0, 'cores_avg': 1.0, 'min_depth': 0}]
        stages = [{'name': 'chim', 'number': 1, 'status': 'passed', 'jobs': 8, 'jobs_mean': 24.0, 'jobs_max': 24,
                   'dependencies': [], 'start': 0.0, 'end': 4710.0, 'wall': 4710.0, 'cpu': 61768.0, 'cores_avg': 13.11,
                   'sections': sections},
                  {'name': 'world-flora-assets', 'number': 2, 'status': 'passed', 'jobs': 6, 'jobs_mean': 6.0,
                   'dependencies': [], 'start': 0.0, 'end': 43.5, 'wall': 43.5, 'cpu': 64.3, 'cores_avg': 1.48},
                  {'name': 'harvest', 'number': 3, 'status': 'passed', 'jobs': 6, 'dependencies': [], 'start': 0.0,
                   'end': 14.0, 'wall': 14.0, 'cpu': 15.8, 'cores_avg': 1.13},
                  {'name': 'setup', 'number': 4, 'status': 'passed', 'jobs': 1, 'dependencies': [], 'start': 0.0,
                   'end': 60.0, 'wall': 60.0, 'cpu': 60.0, 'cores_avg': 1.0}]
        return {'schema': build_profile.SCHEMA, 'run': '/x/run', 'status': 'passed', 'wall_seconds': 4710.0,
                'budget': 24, 'stages': stages, 'timeline': None}

    def test_flags_long_underused_phases_and_stages_only(self):
        found = build_profile.underused(self.profile())
        self.assertEqual([(i['stage'], i['phase']) for i in found],
                         [('chim', 'CHIM statistics'), ('world-flora-assets', None)])
        self.assertIn('one core', found[0]['why'])
        analysis = build_profile.analyse(self.profile())
        self.assertEqual(len(analysis['underused']), 2)
        profile = dict(self.profile(), analysis=analysis)
        text = '\n'.join(build_profile.summary_lines(profile))
        self.assertIn('[underused] chim: CHIM statistics: 7m44s at 1.0 of 24.0 cores', text)
        items = build_profile.optimize(profile)
        phase = [i for i in items if i['kind'] == 'underused-phase']
        self.assertEqual([i['stage'] for i in phase], ['chim: CHIM statistics'])
        self.assertIn('shared worker pool', phase[0]['suggestion'])


class LedgerTests(unittest.TestCase):
    """optimize --ledger: per-stage statistics over many builds (folded in from the private stage_stats)."""

    def test_ledger_statistics_rank_underused_time(self):
        rows = [{'stage': 'chim', 'build': 'a', 'wall_s': 600, 'cores_avg': 2.0, 'jobs_max': 24, 'status': 'passed'},
                {'stage': 'chim', 'build': 'b', 'wall_s': 6500, 'cores_avg': 11.7, 'jobs_max': 24, 'status': 'failed'},
                {'stage': 'setup', 'build': 'a', 'wall_s': 0.2, 'cores_avg': 1.0, 'jobs_max': 1, 'status': 'passed'},
                {'stage': 'bsp', 'build': 'a', 'wall_s': 40, 'cores_avg': 8.0, 'jobs_max': 12, 'status': 'passed'},
                {'stage': 'gone', 'build': 'a', 'wall_s': 99, 'status': 'cancelled'}]
        table = build_profile.ledger_stats(rows)
        self.assertEqual([r['stage'] for r in table], ['chim', 'bsp', 'setup'])
        chim = table[0]
        self.assertEqual((chim['runs'], chim['underused_runs'], chim['underused_seconds']), (2, 2, 7100.0))
        self.assertEqual(chim['slowest_build'], 'b')
        self.assertEqual(table[1]['underused_runs'], 0)
        with tempfile.TemporaryDirectory() as temp:
            ledger = Path(temp) / 'ledger.jsonl'
            ledger.write_text(''.join(json.dumps(r) + chr(10) for r in rows), encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(build_profile.main(['optimize', '--ledger', str(ledger)]), 0)
        self.assertIn('chim', out.getvalue().splitlines()[1])


class StatsReuseTests(unittest.TestCase):
    """chim_build validates once and hands the world to the stats: the same chim-stats.json byte for byte."""

    def test_stats_from_the_build_validation_equal_stats_that_validate_again(self):
        from chim import stats as S
        from chim.validate import main as validate_main, report_text, report_world
        from test_chim_format import CENTRE, fixture
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'w'
            receipt, _ = fixture(out)
            source_path = out / 'chim-source.json'      # what chim_build and stats.py read
            source = json.loads(source_path.read_text(encoding='utf-8')) if source_path.is_file() else None
            camera = ['--camera', 'west', str(CENTRE[0] - 460 * 4), str(CENTRE[1] + 40 * 4)]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(S.main([str(out), '--json', str(Path(temp) / 'again.json')] + camera), 0)
                report, world, _ = report_world(out, source)
                self.assertTrue(report['ok'])
                self.assertEqual(S.main([str(out), '--json', str(Path(temp) / 'reused.json')] + camera,
                                        world, report['measured']), 0)
                self.assertEqual(validate_main([str(out), '--json', str(Path(temp) / 'v.json')]), 0)
            again = (Path(temp) / 'again.json').read_bytes()
            self.assertEqual(hashlib.sha256((Path(temp) / 'reused.json').read_bytes()).hexdigest(),
                             hashlib.sha256(again).hexdigest())
            self.assertIn(b'"cameras"', again)
            # validate.py's own report is unchanged by the refactor
            self.assertEqual((Path(temp) / 'v.json').read_text(encoding='utf-8'), report_text(report))


if __name__ == '__main__':
    unittest.main()
