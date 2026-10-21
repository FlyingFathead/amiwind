# SPDX-License-Identifier: GPL-3.0-only
"""BUILD-SCHEDULER-MEMORY-STARVED-42: the scheduler's memory guard held the v0.0.42 final's chim stage on one of its
workers for over an hour while nothing said so. Three checks (tools/resource_plan.py):
- before a pooled stage starts, its parent plus its workers are compared with what the container holds beside it,
  and a stage that will not fit at full speed is named with the lease that fits it;
- a stage held below half its share for ALARM_SECONDS prints a [scheduler] ALARM line (stage, workers, memory, lease),
  again every ALARM_SECONDS while it lasts, never before;
- the plan counts the memory the stages beside a stage held at its measured peak (the container's peak less the
  stage's own tree), so a stage planned alone no longer looks as if it fits.

Every number is synthetic."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import resource_plan as rp  # noqa: E402

GIB = 1 << 30
MIB = 1 << 20


class Memory:
    def __init__(self, limit_gb, used_gb):
        self.limit, self.used, self.t = limit_gb * GIB, used_gb * GIB, 0.0

    def read(self):
        return (self.limit, self.used, 0), None

    def clock(self):
        return self.t


def guard(memory, lines, **kw):
    return rp.SchedulerGuard(12, {'chim': 1200.0}, reader=memory.read, clock=memory.clock, interval=30,
                             log=lines.append, parents={'chim': 13000.0}, **kw)


class StartCheck(unittest.TestCase):
    def test_a_stage_that_does_not_fit_beside_the_running_ones_is_named_with_its_lease(self):
        memory, lines = Memory(28, 10), []
        g = guard(memory, lines)
        line = g.start_check('chim', 12, running=['npc-gallery', 'world-terrain'])
        self.assertIsNotNone(line)
        self.assertIn('WILL NOT FIT AT FULL SPEED: chim', line)
        self.assertIn('running: npc-gallery, world-terrain', line)
        # 10 GiB in use + 13,000 MiB parent + 12 x 1,200 MiB = 37,640 MiB; under 90 %: 41,822 MiB -> 41 GB
        self.assertIn('a lease of 41 GB fits it', line)
        self.assertEqual(lines, [line])

    def test_a_stage_that_fits_or_has_no_size_says_nothing(self):
        memory, lines = Memory(64, 4), []
        g = guard(memory, lines)
        self.assertIsNone(g.start_check('chim', 12))
        self.assertIsNone(g.start_check('scene', 8))          # no measured worker size: nothing to compare
        self.assertEqual(lines, [])


class Alarm(unittest.TestCase):
    def test_held_below_half_for_five_minutes_raises_one_alarm_then_repeats(self):
        memory, lines = Memory(28, 26.5), []
        g = guard(memory, lines, alarm_seconds=300)
        g.tick({'chim': 6}, {'chim': 6})                      # above 90 %: capped 6 -> 4
        for t in range(30, 300, 30):                          # held below half (1-2 of 6) for under five minutes
            memory.t = t
            g.tick({'chim': 1}, {'chim': 6})
        self.assertFalse([l for l in lines if 'ALARM' in l])
        memory.t = 330
        g.tick({'chim': 1}, {'chim': 6})
        alarms = [l for l in lines if 'ALARM' in l]
        self.assertEqual(len(alarms), 1)
        self.assertIn('[scheduler] ALARM: chim held at 1 of 6 workers', alarms[0])
        self.assertIn('26.5 of 28.0 GiB in use', alarms[0])
        # 26.5 GiB + 5 x 1,200 MiB under 80 %: 41,420 MiB -> 41 GB
        self.assertIn('a lease of 41 GB would let it run at 6', alarms[0])
        memory.t = 360
        g.tick({'chim': 1}, {'chim': 6})
        self.assertEqual(len([l for l in lines if 'ALARM' in l]), 1)   # not again within five minutes
        memory.t = 640
        g.tick({'chim': 1}, {'chim': 6})
        self.assertEqual(len([l for l in lines if 'ALARM' in l]), 2)
        self.assertEqual(g.alarms[0]['lease_gb'], 41)

    def test_a_stage_given_its_workers_back_clears_the_alarm_clock(self):
        memory, lines = Memory(28, 26.5), []
        g = guard(memory, lines, alarm_seconds=300)
        g.tick({'chim': 1}, {'chim': 6})
        memory.t, memory.used = 200, 10 * GIB
        g.tick({'chim': 6}, {'chim': 6})                      # back at its share
        memory.used = int(26.5 * GIB)
        for t in (230, 260, 290, 320, 350, 380, 410, 440):
            memory.t = t
            g.tick({'chim': 1}, {'chim': 6})
        self.assertFalse([l for l in lines if 'ALARM' in l])  # the five minutes count again from 230
        self.assertNotIn('chim', [a['stage'] for a in g.alarms])


class GrowBack(unittest.TestCase):
    def capped(self, memory, lines, units=None):
        g = rp.SchedulerGuard(12, units or {'chim': 1200.0}, reader=memory.read, clock=memory.clock, interval=30,
                              log=lines.append)
        used = memory.used
        memory.used = int(0.97 * memory.limit)
        for t in range(0, 300, 30):                           # above the critical line: cut to one worker
            memory.t = t
            g.tick({n: g.cap(n, 6) for n in g.units}, {n: 6 for n in g.units})
        memory.used = used
        return g

    def test_below_the_critical_line_a_cut_stage_gets_its_full_share_back_at_once(self):
        # try2's kind of state (72 %) and the dev3 clean public build's (84-90 %): the old grow-back waited for room
        # under 80/88 % for planned units and left the stage on one worker; the rule now is --jobs below 96 %
        for used in (23, 27, 30.5):
            memory, lines = Memory(32, used), []
            g = self.capped(memory, lines)
            self.assertEqual(g.cap('chim', 6), 1)
            memory.t = 400
            g.tick({'chim': 1}, {'chim': 6})
            self.assertEqual(g.cap('chim', 6), 6, used)
            self.assertIn('back to its full share', lines[-1])

    def test_above_the_critical_line_a_cut_stage_stays_cut(self):
        memory, lines = Memory(32, 31.5), []
        g = self.capped(memory, lines)
        memory.t = 400
        g.tick({'chim': 1}, {'chim': 6})
        self.assertEqual(g.cap('chim', 6), 1)


class PlanBeside(unittest.TestCase):
    STEPS = [('chim', ['python3', 'tools/chim_build.py', '--jobs', '12'])]

    def got(self, gb):
        return {'memory_bytes': int(gb * GIB), 'memory_source': 'test', 'used_bytes': 0, 'threads': 12,
                'threads_source': 'test', 'machine_bytes': 64 * GIB, 'machine_threads': 24}

    def measured(self, container=None):
        row = {'jobs': 6, 'largest_mib': 13000.0, 'total_mib': 20200.0, 'worker_mib': 1200.0, 'wall': 3000.0,
               'cores': 2.0, 'run': '/vol/ws8/build/r1'}
        if container:
            row['container_mib'] = container
        return row

    def test_the_memory_beside_a_stage_at_its_measured_peak_counts(self):
        alone = rp.plan(self.STEPS, {'chim'}, 12, self.got(32), {'stages': {'chim': [self.measured()]}, 'stair': None,
                                                                 'runs': []})
        beside = rp.plan(self.STEPS, {'chim'}, 12, self.got(32),
                         {'stages': {'chim': [self.measured(container=27000.0)]}, 'stair': None, 'runs': []})
        a, b = alone['stages'][0], beside['stages'][0]
        self.assertEqual(a['beside_mib'], 0.0)
        self.assertEqual(b['beside_mib'], 6800.0)
        self.assertLess(b['workers'], a['workers'])
        self.assertEqual(b['status'], 'WILL THROTTLE')
        self.assertTrue(any('the stages beside it held' in r for r in b['reasons']))
        # full speed: 13,000 + 12 x 1,200 + 6,800 = 34,200 MiB at 80 % -> 42,750 MiB -> 42 GB
        self.assertEqual(b['lease_gb_full_speed'], 42)
        self.assertTrue(any('a lease of 42 GB runs it at its 12 planned workers' in r for r in b['reasons']))
        self.assertEqual(rp.validate(beside), [])

    def test_measure_records_the_container_peak_while_the_stage_ran(self):
        row = {'name': 'chim', 'status': 'passed', 'jobs': 6, 'jobs_max': 6, 'wall': 3000.0, 'cores_avg': 2.0,
               'peak_process_rss_bytes': 13000 * MIB, 'peak_tree_rss_bytes': 20200 * MIB, 'start': 0, 'end': 100}
        timeline = {'t': [10, 50], 'memory_bytes': [20 * GIB, 27 * GIB], 'stages': {'chim': [[0, 2.0], [1, 2.0]]}}
        found = rp.measure(row, timeline)
        self.assertEqual(found['container_mib'], 27 * 1024)
        self.assertEqual(found['total_mib'], 20200.0)


if __name__ == '__main__':
    unittest.main()
