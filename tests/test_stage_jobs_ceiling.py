# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-CHIM-STAIR-JOBS-AT-LAUNCH-42: a stage's in-stage pools take their ceiling from the scheduler's live allowance
(the build budget), not from the --jobs the stage was launched with. The v0.0.42 final's chim stage started with
--jobs 2 (the scheduler's share at that moment); its stair gate planned 2 workers and its memory governor never let
the pool past them although the allowance was 12 and the memory held 4 walks. Synthetic numbers only."""
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import build_parallel  # noqa: E402
import resource_plan as rp  # noqa: E402

GIB = 1 << 30


class Scheduler:
    """The environment a pooled stage gets from the scheduler: launched with JOBS, allowance file ALLOWANCE."""

    def __init__(self, jobs, allowance, budget):
        self.tmp = tempfile.TemporaryDirectory()
        path = Path(self.tmp.name) / 'allowance'
        path.write_text('%d\n' % allowance)
        self.env = {build_parallel.ALLOWANCE_ENV: str(path), build_parallel.BUDGET_ENV: str(budget),
                    'AMIWIND_BUILD_JOBS': str(jobs)}

    def __enter__(self):
        self.patch = mock.patch.dict(os.environ, self.env)
        self.patch.start()
        return self

    def __exit__(self, *exc):
        self.patch.stop()
        self.tmp.cleanup()


class StageCeiling(unittest.TestCase):
    def test_under_the_scheduler_the_ceiling_is_the_budget(self):
        with Scheduler(jobs=2, allowance=12, budget=12):
            self.assertEqual(build_parallel.stage_ceiling(2), 12)
            self.assertEqual(build_parallel.stage_ceiling(16), 16)     # never less than an explicit count

    def test_outside_the_scheduler_the_count_is_unchanged(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(build_parallel.ALLOWANCE_ENV, None)
            self.assertEqual(build_parallel.stage_ceiling(3), 3)


class GovernedCeiling(unittest.TestCase):
    def test_the_memory_governor_plans_for_the_ceiling_not_the_launch_count(self):
        planned = []

        def capture(count, unit_mib=None, label='stage', environ=None):
            planned.append(count)
            return None                       # then governed_map runs as completed_map: same results
        with Scheduler(jobs=2, allowance=12, budget=12), mock.patch.object(rp, 'governor_for', capture), \
                contextlib.redirect_stdout(io.StringIO()):
            out = sorted(build_parallel.governed_map(abs, list(range(-6, 6)), 2, unit_mib=2842, label='test'))
        self.assertEqual(out, sorted(map(abs, range(-6, 6))))
        self.assertEqual(planned, [12])

    def test_the_stair_walks_grow_to_the_memory_fit(self):
        # 2,842 MiB a walk; the container's memory holds 4 of them: launched with --jobs 2, the walks reach 4
        reader = lambda: ((16 * GIB, int(1.5 * GIB), 0), None)     # noqa: E731
        launch = rp.MemoryGovernor(2, 2842, reader=reader, log=lambda line: None)
        ceiling = rp.MemoryGovernor(12, 2842, reader=reader, log=lambda line: None)
        self.assertEqual(launch.limit(0), 2)
        self.assertEqual(ceiling.limit(0), 4)


if __name__ == '__main__':
    unittest.main()
