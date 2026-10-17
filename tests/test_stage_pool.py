# SPDX-License-Identifier: GPL-3.0-only
"""One worker pool for a whole stage (build_parallel.stage_pool, BUILD-CHIM-STAGE-SERIAL-TAIL-36): every map of
the stage runs on the same warm workers, results equal to the per-map pools (the batch method), largest first."""
import contextlib
import io
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import build_parallel  # noqa: E402
from build_parallel import completed_map, ordered_map, stage_pool  # noqa: E402


def square_pid(item):
    return item * item, os.getpid()


def env_value(item):
    return os.environ.get('AW_TEST_STAGE_POOL'), os.getpid()


class StagePoolTests(unittest.TestCase):
    def test_maps_share_one_pool_and_results_match_batch(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with stage_pool(3, 'test') as pool:
                self.assertIsNotNone(pool)
                first = list(ordered_map(square_pid, range(12), 3))
                second = list(ordered_map(square_pid, range(12), 3, cost=lambda i: i))
                third = sorted(completed_map(square_pid, range(12), 3))
                self.assertIs(build_parallel.active_stage_pool(), pool)
                summary = pool.summary()
        self.assertIsNone(build_parallel.active_stage_pool())
        batch = list(ordered_map(square_pid, range(12), 3))
        self.assertEqual([r for r, _ in first], [r for r, _ in batch])
        self.assertEqual([r for r, _ in second], [r for r, _ in batch])
        self.assertEqual(sorted(r for r, _ in third), sorted(r for r, _ in batch))
        # one start for the three maps: the same worker processes served them all
        self.assertEqual(summary['pool_starts'], 1)
        self.assertEqual(summary['maps'], 3)
        self.assertEqual(summary['tasks'], 36)
        pids = {p for _, p in first + second + third}
        self.assertLessEqual(len(pids), 3)
        self.assertIn('one worker pool of 3 workers for the whole step: started 1 time(s), 3 maps, 36 tasks',
                      out.getvalue())

    def test_batch_mode_is_the_previous_method(self):
        made = []
        real = build_parallel.process_pool

        def recording(count):
            made.append(count)
            return real(count)
        with patch.object(build_parallel, 'process_pool', side_effect=recording):
            with stage_pool(2, 'test', mode='batch') as pool:
                self.assertIsNone(pool)
                list(ordered_map(square_pid, range(4), 2))
                list(ordered_map(square_pid, range(4), 2))
        self.assertEqual(made, [2, 2])            # a pool per map
        with self.assertRaises(ValueError):
            with stage_pool(2, 'test', mode='other'):
                pass

    def test_pool_starts_again_when_the_environment_changes(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), patch.dict(os.environ, {'AW_TEST_STAGE_POOL': 'a'}):
            with stage_pool(2, 'test') as pool:
                before = list(ordered_map(env_value, range(4), 2))
                os.environ['AW_TEST_STAGE_POOL'] = 'b'
                after = list(ordered_map(env_value, range(4), 2))
                starts = pool.summary()['pool_starts']
        self.assertEqual({v for v, _ in before}, {'a'})
        self.assertEqual({v for v, _ in after}, {'b'})       # never a stale worker environment
        self.assertEqual(starts, 2)
        self.assertIn('environment changed: AW_TEST_STAGE_POOL', out.getvalue())

    def test_recycle_at_a_phase_boundary(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with stage_pool(2, 'test') as pool:
                first = list(ordered_map(square_pid, range(4), 2))
                pool.recycle('phase done')
                second = list(ordered_map(square_pid, range(4), 2))
                summary = pool.summary()
        self.assertEqual([r for r, _ in first], [r for r, _ in second])
        self.assertEqual(summary['pool_starts'], 2)
        self.assertEqual(summary['restarts'], ['phase done'])
        self.assertIn('workers stopped (phase done)', out.getvalue())

    def test_one_worker_and_nested_blocks(self):
        with stage_pool(1, 'test') as pool:
            self.assertIsNone(pool)
            self.assertEqual([r for r, _ in ordered_map(square_pid, range(3), 1)], [0, 1, 4])
        with contextlib.redirect_stdout(io.StringIO()):
            with stage_pool(2, 'outer') as outer:
                with stage_pool(2, 'inner') as inner:
                    self.assertIs(inner, outer)

    def test_live_worker_label_in_the_heartbeat(self):
        # fixlist B9: the scheduler's heartbeat names the stage's workers now (its allowance), not its start share
        text = Path(build_parallel.__file__).read_text(encoding='utf-8')
        self.assertIn('({held(s)} workers)', text)
        self.assertNotIn("({s['entry']['jobs']} workers)", text)


if __name__ == '__main__':
    unittest.main()
