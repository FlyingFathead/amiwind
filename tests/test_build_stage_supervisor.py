# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-STAGE-ALLOWANCE-STUCK-43 and BUILD-CHIM-REGION-FRAMES-TAIL-43: the scheduler gives free cores to queued work,
names a stage that still runs under half its share, and pools hand their heavy units out first.

- the memory guard decides from the memory the workers really hold: the v0.0.43-dev3 chim stage was cut 20 -> 1 while
  its main process held the memory, and never grew back (synthetic numbers of that state);
- a lone running stage holds the whole budget, and the workers of a stage with nothing queued go to a stage with
  queued units (the free-core checker);
- an underused stage with queued units writes one warning and one RUN/underused.jsonl line per occurrence, after a
  minute, never a failure;
- largest first: ordered_map by its cost history, completed_map by cost, the CHIM region frames by their references;
- the build summary's digest: per stage, 'Needs attention' keys, the comparison, a short page."""
import contextlib
import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import build_digest  # noqa: E402
import build_parallel  # noqa: E402
import pool_status  # noqa: E402
import resource_plan as rp  # noqa: E402
import stage_watch  # noqa: E402

GIB = 1 << 30


class Memory:
    def __init__(self, limit_gb, used_gb):
        self.limit, self.used, self.t = int(limit_gb * GIB), int(used_gb * GIB), 0.0

    def read(self):
        return (self.limit, self.used, 0), None

    def clock(self):
        return self.t


def guard(memory, lines, tree):
    g = rp.SchedulerGuard(20, {'chim': 2842.0}, reader=memory.read, clock=memory.clock, interval=30,
                          log=lines.append, parents={'chim': 20823.0}, stage_reader=lambda pid: tree())
    g.track('chim', 4242)
    return g


class MeasuredMemoryGuard(unittest.TestCase):
    def test_memory_held_by_the_main_process_cuts_no_workers(self):
        # dev3 at 14:34Z: 36.3 of 40 GiB in use, 20 visibility-row workers of about 120 MiB beside a 34 GiB main
        memory, lines = Memory(40, 36.3), []
        g = guard(memory, lines, lambda: {'main_mib': 34800.0, 'workers_mib': [110.0] * 10 + [130.0] * 10})
        for t in range(0, 600, 30):
            memory.t = t
            g.tick({'chim': g.cap('chim', 20)}, {'chim': 20})
        self.assertEqual(g.cap('chim', 20), 20)
        holds = [l for l in lines if 'fewer workers would not free it' in l]
        self.assertEqual(len(holds), 1, lines)            # said once per episode
        self.assertIn("chim's main process holds 34.0 GiB", holds[0])

    def test_below_the_critical_line_the_stage_keeps_its_jobs(self):
        # 37.0 of 40 GiB (92.5 %): the old guard cut 9 -> 7 here, and because the pool's worker processes stay alive and
        # keep their memory, every cut only ratcheted down (one worker for an hour, BUILD-SCHEDULER-MEMORY-STARVED-42).
        # --jobs keeps its level until the critical line (maintainer 2026-10-21).
        memory, lines = Memory(40, 37.0), []
        g = guard(memory, lines, lambda: {'main_mib': 28000.0, 'workers_mib': [100.0] + [1000.0] * 8})
        g.tick({'chim': 9}, {'chim': 20})
        self.assertEqual(g.cap('chim', 20), 20)

    def test_a_stage_cut_above_the_critical_line_gets_its_jobs_back_below_it(self):
        # the dev3 clean public build: cut to 1 of 24, then 39.5 of 44 GiB (90 %) for an hour with no way back
        memory, lines = Memory(44, 43.0), []
        g = guard(memory, lines, lambda: {'main_mib': 14000.0, 'workers_mib': [900.0] * 26})
        for t in range(0, 300, 30):
            memory.t = t
            g.tick({'chim': g.cap('chim', 24)}, {'chim': 24})
        self.assertLess(g.cap('chim', 24), 24)
        memory.used, memory.t = int(39.5 * GIB), 330
        g.tick({'chim': g.cap('chim', 24)}, {'chim': 24})
        self.assertEqual(g.cap('chim', 24), 24)
        self.assertTrue(any('back to its full share' in line for line in lines))

    def test_above_the_critical_share_the_guard_cuts_anyway(self):
        memory, lines = Memory(40, 39.0), []
        g = guard(memory, lines, lambda: {'main_mib': 38000.0, 'workers_mib': [100.0] * 20})
        g.tick({'chim': 20}, {'chim': 20})
        self.assertLess(g.cap('chim', 20), 20)

    def test_a_held_stage_grows_back_by_its_measured_workers(self):
        # cut to 1 by the planned 2,842 MiB unit, then measured: 150 MiB workers; 33 GiB in use of 40
        memory, lines = Memory(40, 38.5), []
        state = {'tree': None}
        g = guard(memory, lines, lambda: state['tree'])
        for t in range(0, 300, 30):
            memory.t = t
            g.tick({'chim': g.cap('chim', 20)}, {'chim': 20})
        self.assertEqual(g.cap('chim', 20), 1)               # the old path, no measurement: 20 -> 1
        state['tree'] = {'main_mib': 33000.0, 'workers_mib': [150.0] * 20}
        memory.used, memory.t = 33 * GIB, 400
        g.tick({'chim': 1}, {'chim': 20})
        # 82.5 %: below the critical line the whole share comes back at once (before: 16 now, the rest later)
        self.assertEqual(g.cap('chim', 20), 20)

    def test_without_a_measurement_the_planned_unit_rules_stay(self):
        memory, lines = Memory(28, 26.5), []
        g = rp.SchedulerGuard(12, {'chim': 1200.0}, reader=memory.read, clock=memory.clock, interval=30,
                              log=lines.append, stage_reader=lambda pid: None)
        g.track('chim', 1)
        g.tick({'chim': 6}, {'chim': 6})
        self.assertEqual(g.cap('chim', 6), 6)                # 94.6 %: below the critical line, --jobs kept
        memory.used, memory.t = int(27.5 * GIB), 60          # 98 %: above it, three quarters, as before
        g.tick({'chim': 6}, {'chim': 6})
        self.assertEqual(g.cap('chim', 6), 4)

    def test_stage_memory_reads_this_process_tree(self):
        if not Path('/proc/self/stat').is_file():
            self.skipTest('no /proc')
        reading = rp.stage_memory(os.getpid())
        self.assertIsNotNone(reading)
        self.assertGreater(reading['main_mib'], 0)


class FreeCores(unittest.TestCase):
    def test_a_stage_with_nothing_queued_lends_what_it_does_not_run(self):
        shares = {'chim': 10, 'world-terrain': 10}
        demand = {'chim': {'more': True, 'running': 10}, 'world-terrain': {'more': False, 'running': 2}}
        lent = stage_watch.lend_shares(shares, demand)
        self.assertEqual(lent, {'chim': 18, 'world-terrain': 10})   # the idle stage keeps its share (live_jobs)

    def test_unknown_demand_neither_lends_nor_borrows(self):
        shares = {'a': 5, 'b': 5}
        self.assertEqual(stage_watch.lend_shares(shares, {'a': None, 'b': {'more': True}}), shares)
        self.assertEqual(stage_watch.lend_shares(shares, {}), shares)

    def test_a_lone_running_stage_gets_the_whole_budget(self):
        # two pooled stages; when the first ends, the second's allowance file reaches the whole budget at once
        script = '\n'.join([
            'import json, os, sys, time',
            'from pathlib import Path',
            'seen = []; end = time.time() + {}; stop = {}',
            'while time.time() < end:',
            '    v = int(Path(os.environ["AMIWIND_BUILD_JOBS_FILE"]).read_text())',
            '    seen.append(v) if not seen or seen[-1] != v else None',
            '    if v == stop: break',
            '    time.sleep(.02)',
            'Path({!r}).write_text(json.dumps(seen))'])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            steps = [('engine', [sys.executable, '-c', script.format(1.0, None, str(root / 'a.json')), '--jobs', '1']),
                     ('media', [sys.executable, '-c', script.format(20.0, 12, str(root / 'b.json')), '--jobs', '1'])]
            with contextlib.redirect_stdout(io.StringIO()):
                build_parallel.execute_parallel(steps, root / 'run', {'compiler_jobs': 12}, root)
            seen = json.loads((root / 'b.json').read_text())
            self.assertEqual(seen[0], 6)
            self.assertEqual(seen[-1], 12)
            self.assertTrue((root / 'run' / 'build-summary.md').is_file())
            summary = json.loads((root / 'run' / 'build-summary.json').read_text())
            self.assertEqual(summary['schema'], 'amiwind-build-summary-v2')
            self.assertEqual([s['name'] for s in summary['digest']['stages']], ['engine', 'media'])


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class Supervisor(unittest.TestCase):
    def watch(self, run, cpu, demand, lines):
        clock = Clock()
        w = stage_watch.StageWatch(run, clock=clock, cpu=lambda pid: cpu['seconds'], status=lambda path: demand,
                                   log=lines.append, wall=lambda: 1000.0 + clock.t)
        w.started('chim', 1, run / 'jobs' / '33-chim', 0.0)
        return w, clock

    def test_under_half_with_queued_units_for_a_minute_writes_one_occurrence(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            cpu, lines = {'seconds': 0.0}, []
            demand = {'queued': 400, 'more': True, 'running': 1, 'slowest': ['rcp16_p11', 42.0]}
            w, clock = self.watch(run, cpu, demand, lines)
            for step in range(1, 30):                  # 145 s at 1 core of a 20-worker share
                clock.t, cpu['seconds'] = step * 5.0, step * 5.0
                w.sample({'chim': (1, 20)})
            rows = [json.loads(l) for l in (run / stage_watch.FILE).read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['stage'], 'chim')
            self.assertEqual(rows[0]['allowed'], 1)
            self.assertEqual(rows[0]['share'], 20)
            self.assertEqual(rows[0]['slowest'], {'unit': 'rcp16_p11', 'seconds': 42.0})
            self.assertEqual(rows[0]['held_by'], 'memory guard')
            self.assertEqual(rows[0]['key'], 'underused:chim')
            self.assertEqual(len([l for l in lines if l.startswith('[underused] WARNING: chim')]), 1)
            # back at its share: the occurrence ends; under again for a minute: a second one
            for step in range(30, 40):
                clock.t, cpu['seconds'] = step * 5.0, cpu['seconds'] + 5.0 * 20
                w.sample({'chim': (20, 20)})
            for step in range(40, 60):
                clock.t, cpu['seconds'] = step * 5.0, cpu['seconds'] + 5.0
                w.sample({'chim': (20, 20)})
            self.assertEqual(len((run / stage_watch.FILE).read_text().splitlines()), 2)
            summary = w.summary('chim')
            self.assertGreater(summary['under_half_longest_seconds'], 60)
            self.assertEqual(len(summary['underused']), 2)

    def test_nothing_queued_is_no_occurrence(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            cpu, lines = {'seconds': 0.0}, []
            w, clock = self.watch(run, cpu, {'queued': 0, 'more': False, 'running': 1, 'slowest': None}, lines)
            for step in range(1, 40):
                clock.t, cpu['seconds'] = step * 5.0, step * 5.0
                w.sample({'chim': (20, 20)})
            self.assertFalse((run / stage_watch.FILE).exists())
            self.assertFalse(lines)

    def test_not_before_a_minute(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            cpu, lines = {'seconds': 0.0}, []
            w, clock = self.watch(run, cpu, {'queued': 5, 'more': True, 'running': 1, 'slowest': None}, lines)
            for step in range(1, 12):                  # 55 s
                clock.t, cpu['seconds'] = step * 5.0, step * 5.0
                w.sample({'chim': (20, 20)})
            self.assertFalse(lines)

    def test_the_occurrence_names_the_phase_running_now(self):
        # BUILD-IMAGE-FINALIZE-UNDERUSED-48: the record and the warning name the stage's current phase
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            sections = run / 'profile' / 'sections'
            sections.mkdir(parents=True)
            (sections / '33-chim.jsonl.now').write_text(json.dumps({'name': 'Image: payload preflight',
                                                                    'started_at': 1010.0}))
            cpu, lines = {'seconds': 0.0}, []
            w, clock = self.watch(run, cpu, {'queued': 9, 'more': True, 'running': 1, 'slowest': None}, lines)
            for step in range(1, 16):
                clock.t, cpu['seconds'] = step * 5.0, step * 5.0
                w.sample({'chim': (20, 20)})
            row = json.loads((run / stage_watch.FILE).read_text().splitlines()[0])
            self.assertEqual(row['phase'], 'Image: payload preflight')
            self.assertEqual(row['phase_seconds'], round(row['time'] - 1010.0, 1))
            self.assertGreater(row['phase_seconds'], 0)
            self.assertIn('phase now: Image: payload preflight', lines[0])
        with tempfile.TemporaryDirectory() as tmp:          # no phase file: named as none
            run = Path(tmp)
            cpu, lines = {'seconds': 0.0}, []
            w, clock = self.watch(run, cpu, {'queued': 9, 'more': True, 'running': 1, 'slowest': None}, lines)
            for step in range(1, 16):
                clock.t, cpu['seconds'] = step * 5.0, step * 5.0
                w.sample({'chim': (20, 20)})
            self.assertIsNone(json.loads((run / stage_watch.FILE).read_text().splitlines()[0])['phase'])
            self.assertIn('phase now: none named', lines[0])


def slow_square(item):
    time.sleep(0.05)
    return item * item


class PoolStatus(unittest.TestCase):
    def test_a_map_under_the_scheduler_reports_queued_and_running_units(self):
        with tempfile.TemporaryDirectory() as tmp:
            allowance = Path(tmp) / '33-chim'
            allowance.write_text('2\n')
            with patch.dict(os.environ, {pool_status.ALLOWANCE_ENV: str(allowance)}):
                w = pool_status.watch('frames', ['a', 'b', 'c'])
                w.submit(0, ('rcp1_p2', 3))
                w.flush(force=True)            # the file is written at most every WRITE_SECONDS
                status = pool_status.read(allowance)
                self.assertEqual(status['queued'], 2)
                self.assertTrue(status['more'])
                self.assertEqual(status['running'], 1)
                self.assertEqual(status['slowest'][0], 'rcp1_p2')
                w.finish(0)
                w.close()
                w.flush(force=True)
                status = pool_status.read(allowance)
                self.assertFalse(status['more'])
                self.assertEqual(status['running'], 0)

    def test_outside_the_scheduler_nothing_is_written(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(pool_status.ALLOWANCE_ENV, None)
            self.assertIsNone(pool_status.watch('x', [1]))

    def test_unit_names(self):
        self.assertEqual(pool_status.unit_name('bm019', 0), 'bm019')
        self.assertEqual(pool_status.unit_name((b'x', 'rcp2_p3', 4), 1), 'rcp2_p3')
        self.assertEqual(pool_status.unit_name({'name': 'sn12'}, 2), 'sn12')
        self.assertEqual(pool_status.unit_name(object(), 7), '#7')

    def test_the_results_stay_the_same_and_in_order_with_a_status_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            allowance = Path(tmp) / '05-x'
            allowance.write_text('3\n')
            with patch.dict(os.environ, {pool_status.ALLOWANCE_ENV: str(allowance), 'AMIWIND_BUILD_JOBS': '3',
                                         'AMIWIND_BUILD_BUDGET': '3'}):
                ordered = list(build_parallel.ordered_map(slow_square, list(range(12)), 3))
                done = sorted(build_parallel.completed_map(slow_square, list(range(12)), 3))
            self.assertEqual(ordered, [i * i for i in range(12)])
            self.assertEqual(done, sorted(i * i for i in range(12)))
            self.assertFalse(pool_status.read(allowance)['more'])


def started_at(item):
    name, seconds = item
    began = time.monotonic()
    time.sleep(seconds)
    return name, began


def called_in_order(item):
    name, seconds, log = item
    with open(log, 'a', encoding='utf-8') as handle:
        handle.write(name + '\n')
    time.sleep(seconds)
    return name


class LargestFirst(unittest.TestCase):
    def test_ordered_map_takes_its_cost_history_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            items = [('light', .05), ('mid', .05), ('heavy', .05)]
            with patch.dict(os.environ, {'AMIWIND_COST_HISTORY': tmp}):
                Path(tmp, 'test-frames.json').write_text(json.dumps(
                    {'seconds': {'light': 1.0, 'mid': 5.0, 'heavy': 90.0}}))
                rows = list(build_parallel.ordered_map(started_at, items, 2, history='test-frames',
                                                       key=lambda item: item[0]))
                self.assertEqual([r[0] for r in rows], ['light', 'mid', 'heavy'])     # input order back
                began = {name: at for name, at in rows}
                self.assertLess(began['heavy'], began['light'])                         # heaviest started first
                recorded = json.loads(Path(tmp, 'test-frames.json').read_text())['seconds']
                self.assertLess(recorded['light'], 1.0)                                # this run's times recorded

    def test_completed_map_submits_by_cost(self):
        # The order of the calls, not their clock readings: with two workers 'c' cannot be called before
        # 'b' or 'd' has returned, while a worker delayed on a loaded host can read its clock late
        # (TESTS-SUPERVISOR-START-CLOCK-46). The workers are processes, so each call appends to a file.
        weight = {'a': 1, 'b': 4, 'c': 2, 'd': 3}
        with tempfile.TemporaryDirectory() as tmp:
            log = str(Path(tmp, 'calls'))
            items = [(name, .2, log) for name in 'abcd']
            rows = list(build_parallel.completed_map(called_in_order, items, 2, cost=lambda item: weight[item[0]]))
            calls = Path(log).read_text().split()
        self.assertEqual(sorted(rows), ['a', 'b', 'c', 'd'])
        self.assertEqual(set(calls[:2]), {'b', 'd'})

    def test_region_frames_weigh_their_source_cells(self):
        from chim import build as chim_build

        def cell(x, y, refs, interior=False):
            body = b'NAME' + struct.pack('<I', 1) + b'\0' + b'DATA' + struct.pack('<Iiii', 12, int(interior), x, y)
            body += b''.join(b'FRMR' + struct.pack('<II', 4, n) for n in range(refs))
            return b'CELL' + struct.pack('<III', len(body), 0, 0) + body
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'Morrowind.esm').write_bytes(cell(0, 0, 3) + cell(1, 0, 40) + cell(5, 5, 7, interior=True))
            counts = chim_build.cell_reference_counts(Path(tmp))
            self.assertEqual(counts, {(0, 0): 3, (1, 0): 40})
            generated = {'rcp0_p0': {'source_cell': [-1, 0], 'source_radius': 1},
                         'rcp2_p0': {'source_cell': [3, 0], 'source_radius': 1}}
            weights = chim_build.area_weights(['balmora', 'rcp0_p0', 'rcp2_p0'], generated, Path(tmp))
            self.assertEqual(weights['rcp0_p0'], 1 + 3)        # (0, 0) is in its 3 x 3; (1, 0) is not
            self.assertEqual(weights['rcp2_p0'], 1)
            self.assertEqual(weights['balmora'], 40)            # a town: ten times the heaviest frame


class Digest(unittest.TestCase):
    def run_folder(self, root, name, steps, status='passed'):
        run = root / name
        run.mkdir()
        (run / 'build-state.json').write_text(json.dumps({'status': status, 'worker_budget': 20, 'steps': steps}))
        return run

    def test_needs_attention_keys_and_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = self.run_folder(root, '2026_10_18_v0.0.43-dev2_full-batch3_b55a5ce', [
                {'name': 'chim', 'status': 'passed', 'elapsed_seconds': 3000.0},
                {'name': 'image', 'status': 'passed', 'elapsed_seconds': 1000.0}])
            os.utime(old / 'build-state.json', (1, 1))
            run = self.run_folder(root, '2026_10_18_v0.0.43-dev3_full-batch5_ef7e464', [
                {'name': 'chim', 'status': 'passed', 'elapsed_seconds': 6500.0, 'jobs': 4,
                 'cores': {'cores_mean': 3.1, 'allowed_mean': 4.2, 'under_half_longest_seconds': 2400.0}},
                {'name': 'image', 'status': 'passed', 'elapsed_seconds': 700.0}])
            (run / 'underused.jsonl').write_text(json.dumps({'stage': 'chim', 'cores_used': 1.0, 'allowed': 1,
                                                             'share': 20, 'seconds': 2400,
                                                             'slowest': {'unit': 'vivec_city', 'seconds': 9.0}}) + '\n')
            (run / 'perf-guard.json').write_text(json.dumps({'rows': [
                {'stage': 'chim', 'section': 'CHIM world: visibility rows', 'verdict': 'FAIL', 'reasons': ['cores']}]}))
            record = build_digest.update(run)
            keys = [row['key'] for row in record['needs_attention']]
            self.assertEqual(keys, ['underused:chim', 'perf-guard:chim:CHIM world: visibility rows', 'slower:chim'])
            self.assertEqual(record['compared_with'], old.name)
            self.assertEqual({row['stage'] for row in record['stage_changes']}, {'chim', 'image'})
            page = (run / 'build-summary.md').read_text()
            self.assertLessEqual(len(page.splitlines()), 60)
            self.assertIn('`underused:chim`', page)
            # the rest of build-summary.json is kept when the digest is written again
            summary = json.loads((run / 'build-summary.json').read_text())
            summary['output'] = {'sha256': 'x'}
            (run / 'build-summary.json').write_text(json.dumps(summary))
            build_digest.update(run)
            again = json.loads((run / 'build-summary.json').read_text())
            self.assertEqual(again['output'], {'sha256': 'x'})
            self.assertEqual(again['schema'], 'amiwind-build-summary-v2')

    def test_all_well_is_an_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.run_folder(Path(tmp), '2026_10_18_v0.0.43-dev4_full_abcdef0', [
                {'name': 'setup', 'status': 'passed', 'elapsed_seconds': 0.3}])
            record = build_digest.update(run)
            self.assertEqual(record['needs_attention'], [])
            self.assertIn('Nothing: all is well.', (run / 'build-summary.md').read_text())

    def test_kind_from_the_run_name(self):
        self.assertEqual(build_digest.kind('2026_10_18_v0.0.43-dev3_full-batch5_ef7e464'), 'full')
        self.assertEqual(build_digest.kind('2026_10_10_v0.0.35-dev1_miniwind-animkit-companion-run_853d9b2'),
                         'miniwind')
        self.assertIsNone(build_digest.kind('rc1c'))


if __name__ == '__main__':
    unittest.main()
