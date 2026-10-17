"""The build ETA follows the work (fixlist B6): unit counts x per-unit cost history, corrected while a stage
runs from its units done of total. Origin: v0.0.41-dev5, the chim stage expected at 43 min (history of
364-frame runs scaled to 726 frames) ran 85 min; the ETA said 23 minutes at 12:40 and 25 at 13:07."""
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build_profile  # noqa: E402
import build_progress  # noqa: E402


def history_run(workspace, name, wall, units=None, phases=None):
    """An earlier run: build-profile.json (chim stage, its outermost phases) and build-progress.json units_seen."""
    run = workspace / name
    run.mkdir(parents=True)
    sections = [{'name': phase, 'phase': True, 'min_depth': 0, 'start': start, 'wall': seconds}
                for phase, start, seconds in phases or ()]
    stages = [{'name': 'chim', 'number': 1, 'status': 'passed', 'jobs': 8, 'wall': wall, 'cpu': wall,
               'sections': sections}]
    (run / build_profile.PROFILE_NAME).write_text(json.dumps({'budget': 8, 'stages': stages}), encoding='utf-8')
    if units:
        (run / build_progress.PROGRESS_NAME).write_text(json.dumps(
            {'stages': [{'name': 'chim', 'units_seen': units}]}), encoding='utf-8')
    return run


class CorrectionTests(unittest.TestCase):
    def test_converges_to_the_measured_rate(self):
        # history says 2,600 s; the work really costs 6.4 s a frame over 723 frames (4,627 s)
        total, each, prior_total = 723, 6.4, 2600.0
        previous = None
        for done in (10, 100, 300, 500, 700, 723):
            elapsed = done * each
            result = build_progress.corrected_remaining(max(0.0, prior_total - elapsed), elapsed, elapsed, done,
                                                        done, total, overrun=elapsed >= prior_total)
            truth = (total - done) * each
            error = abs(result['remaining'] - truth)
            if previous is not None:
                self.assertLessEqual(error, previous + 1e-6)   # never further from the truth than before
            previous = error
        self.assertEqual(result['remaining'], 0.0)
        self.assertEqual(result['weight'], 1.0)
        # once the history estimate is overrun the measured rate alone counts
        overrun = build_progress.corrected_remaining(0.0, 3000, 3000, 400, 400, 723, overrun=True)
        self.assertAlmostEqual(overrun['remaining'], 323 * 7.5, delta=0.5)

    def test_no_rate_yet_and_unknown_history(self):
        self.assertIsNone(build_progress.corrected_remaining(100, 10, 10, 0, 5, 50))
        self.assertIsNone(build_progress.corrected_remaining(100, 10, 0, 3, 5, 50))
        result = build_progress.corrected_remaining(None, 60, 60, 10, 10, 100, tail=30)
        self.assertEqual(result['weight'], 1.0)
        self.assertAlmostEqual(result['remaining'], 90 * 6 + 30)

    def test_log_counter_reads_the_last_counted_line(self):
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / 'chim.log'
            log.write_text('CHIM regions: 723 cells\n[+9.0s] CHIM world conversion: started, 726 areas\n'
                           '[1/723 frames] CHIM region frames: rcm19_p14: prepared\n{\n "cells": 9\n}\n'
                           '[12034/15415 stairs | 246/273 frames] CHIM stair gate: rcm1: walked\n'
                           '[+1h17m] CHIM validation: started, 726 frames\n', encoding='utf-8')
            counter = build_progress.log_counter(log)
            self.assertEqual(counter, {'name': 'CHIM stair gate', 'done': 12034, 'total': 15415, 'unit': 'stairs'})
            self.assertIsNone(build_progress.log_counter(Path(temp) / 'missing.log'))

    def test_estimate_scales_with_the_unit_count(self):
        rows = [{'wall': 3600.0, 'cpu': None, 'jobs': 8, 'budget': 8, 'units': {'frames': 600}},
                {'wall': 1800.0, 'cpu': None, 'jobs': 8, 'budget': 8, 'units': {'frames': 300}}]
        small = build_progress.per_unit_expected(rows, 'frames', 100, 8)
        large = build_progress.per_unit_expected(rows, 'frames', 1000, 8)
        self.assertAlmostEqual(small[0], 600.0)
        self.assertAlmostEqual(large[0], 6000.0)
        self.assertEqual(small[2], 2)
        self.assertIsNone(build_progress.per_unit_expected(rows, 'cells', 100, 8))   # another unit: unknown

    def test_phase_history_tail(self):
        rows = [{'phases': [{'name': 'conversion', 'start': 0, 'wall': 100},
                            {'name': 'validation', 'start': 100, 'wall': 20},
                            {'name': 'stair gate', 'start': 120, 'wall': 30}], 'work': 10}]
        self.assertEqual(build_progress.phase_history(rows, 'conversion'), (100, 50))
        self.assertEqual(build_progress.phase_history(rows, 'conversion', lambda row: 20 / row['work']), (200, 100))
        self.assertEqual(build_progress.phase_history(rows, 'unknown'), (None, None))


class TrackerTests(unittest.TestCase):
    def test_running_stage_is_corrected_from_its_log_and_keeps_its_units(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            history_run(workspace, 'old', 1000.0, units={'frames': 200},
                        phases=[('CHIM world conversion', 0, 800), ('CHIM stair gate', 800, 200)])
            run = workspace / 'now'
            (run / 'logs').mkdir(parents=True)
            log = run / 'logs' / '01-chim.log'
            clock = [1000.0]
            with patch.object(build_progress.time, 'time', lambda: clock[0]):
                tracker = build_progress.Tracker(run, ['chim'], {}, {'compiler_jobs': 8}, interval=3600)
                try:
                    tracker.stage_started('chim', 1, 8)
                    with patch.object(tracker, '_phase_now',
                                      lambda name, stage, row: row.update(phase={'name': 'CHIM world conversion',
                                                                                 'elapsed_seconds': 300})):
                        log.write_text('[10/400 frames] CHIM region frames: a: prepared\n', encoding='utf-8')
                        tracker.snapshot()                   # first sighting: no rate yet
                        clock[0] += 300.0
                        log.write_text('[60/400 frames] CHIM region frames: b: prepared\n', encoding='utf-8')
                        data = tracker.snapshot()
                finally:
                    tracker.close('cancelled')
        row = data['stages'][0]
        self.assertEqual(row['counter']['done'], 60)
        self.assertEqual(row['units_seen'], {'frames': 400})
        # per-unit history: 5 s a frame x 400 frames = 2,000 s
        self.assertEqual(row['expected_per_unit']['seconds'], 2000.0)
        live = row['live']
        self.assertEqual(live['each'], 6.0)                  # 50 frames in 300 s here
        self.assertEqual(live['tail'], 400.0)                # the stair gate after it, scaled 400 / 200 frames
        measured = 340 * 6.0 + 400
        self.assertEqual(live['measured'], measured)
        self.assertGreater(live['weight'], 0)
        self.assertIn('60/400 frames done', live['basis'])
        self.assertIn('corrected from the work done: chim (log counter, 60/400 frames)', data['eta_basis'])
        self.assertIn('[eta]', build_progress.eta_line(dict(data, status='running')))
        text = '\n'.join(build_progress.status_lines(dict(data, status='running'), now=time.time()))
        self.assertIn('live: 60/400 frames done', text)

    def test_units_seen_become_the_next_builds_history(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            history_run(workspace, 'old', 900.0, units={'frames': 300})
            (workspace / 'now').mkdir()
            samples, _ = build_progress.history_samples(workspace / 'now')
        self.assertEqual(samples['chim'][0]['units'], {'frames': 300})

    def test_unknown_history_falls_back_labelled(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'now'
            (run / 'logs').mkdir(parents=True)
            clock = [50.0]
            with patch.object(build_progress.time, 'time', lambda: clock[0]):
                tracker = build_progress.Tracker(run, ['odd'], {}, {'compiler_jobs': 4}, interval=3600)
                try:
                    tracker.stage_started('odd', 1, 4)
                    first = tracker.snapshot()['stages'][0]
                    (run / 'logs' / '01-odd.log').write_text('[5/50 maps] Odd maps: x\n', encoding='utf-8')
                    tracker.snapshot()
                    clock[0] += 100.0
                    (run / 'logs' / '01-odd.log').write_text('[15/50 maps] Odd maps: y\n', encoding='utf-8')
                    row = tracker.snapshot()['stages'][0]
                finally:
                    tracker.close('cancelled')
        self.assertEqual(first['expected_source'], 'none')
        self.assertNotIn('live', first)
        self.assertEqual(row['live']['weight'], 1.0)
        self.assertEqual(row['live']['remaining'], 350.0)    # 35 maps at 10 s each
        self.assertIn('against no history', row['live']['basis'])


if __name__ == '__main__':
    unittest.main()
