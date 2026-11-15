# SPDX-License-Identifier: GPL-3.0-only
"""New work first (NEW-WORK-FIRST-66): a stage with no history (new content) starts before the known ones, the units
of a unit stage with no recorded time go out before the ones with one, and the resource plan's wall of a stage with a
unit cache comes from the units it bakes, not from its full-rebuild history (BUILD-REBUILD-FORECAST-65)."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

GIB = 1 << 30


def got(memory_gb, threads):
    return {'memory_bytes': int(memory_gb * GIB), 'memory_source': 'test', 'used_bytes': 0, 'threads': threads,
            'threads_source': 'test', 'machine_bytes': int(64 * GIB), 'machine_threads': 24}


def measured(wall, jobs=8, cores=8.0):
    return {'jobs': jobs, 'largest_mib': 300.0, 'total_mib': 1100.0, 'worker_mib': 100.0, 'wall': wall,
            'cores': cores, 'run': '/vol/ws8/build/r1'}


class SchedulerOrder(unittest.TestCase):
    def test_a_new_content_stage_starts_before_a_known_one(self):
        from build_parallel import risk_first
        ready = [(1, ('chim', [])), (2, ('player-view', [])), (3, ('chim-town-mournhold', [])), (4, ('books', []))]
        order = [s[0] for _, s in risk_first(ready, ['chim-town-mournhold'])]
        self.assertEqual(order, ['chim-town-mournhold', 'player-view', 'chim', 'books'])

    def test_without_new_work_the_order_is_the_risk_first_order(self):
        from build_parallel import risk_first
        ready = [(1, ('a', [])), (2, ('player-view', [])), (3, ('b', []))]
        self.assertEqual(risk_first(ready), risk_first(ready, ()))
        self.assertEqual([s[0] for _, s in risk_first(ready, None)], ['player-view', 'a', 'b'])


class UnitOrder(unittest.TestCase):
    def test_units_without_a_recorded_time_go_first_then_longest_first(self):
        import build_costs
        import unit_store
        seen = {}

        def capture(function, items, jobs=None, cost=None):
            items = list(items)
            seen['order'] = [items[i][2] for i in sorted(range(len(items)), key=lambda i: -cost(items[i]))]
            for item in items:
                yield function(item)
        with tempfile.TemporaryDirectory() as temp, mock.patch.dict(os.environ, {build_costs.ENV: temp}):
            build_costs.record('pool', ['old-short', 'old-long'], [1.0, 50.0])
            with mock.patch('build_parallel.completed_map', side_effect=capture):
                failed = unit_store.run_each('pool', lambda task: task,
                                             [(0, 'old-short'), (1, 'new-a'), (2, 'old-long'), (3, 'new-b')],
                                             ['old-short', 'new-a', 'old-long', 'new-b'], 2, lambda i, r: None)
        self.assertEqual(failed, [])
        self.assertEqual(seen['order'][:2], ['new-a', 'new-b'])
        self.assertEqual(seen['order'][2:], ['old-long', 'old-short'])

    def test_every_failure_is_collected(self):
        import unit_store

        def serial(function, items, jobs=None, cost=None):
            for item in items:
                yield function(item)

        def bake(task):
            if task.startswith('bad'):
                raise ValueError('broken ' + task)
            return task
        with mock.patch('build_parallel.completed_map', side_effect=serial):
            failed = unit_store.run_each('pool', bake, [(0, 'bad-1'), (1, 'ok'), (2, 'bad-2')],
                                         ['bad-1', 'ok', 'bad-2'], 2, lambda i, r: None)
        self.assertEqual(len(failed), 2)


class PlanCountsUnits(unittest.TestCase):
    STEPS = [('chim-room-batches', ['python3', 'tools/chim_room_batches.py', '--jobs', '8']),
             ('chim-town-mournhold', ['python3', 'tools/chim_town.py', '--jobs', '8'])]

    def test_the_wall_comes_from_the_units_to_bake(self):
        import resource_plan as rp
        gathered = {'stages': {'chim-room-batches': [measured(25000.0)]}, 'stair': None, 'runs': ['/r1']}
        units = {'chim-room-batches': [['room-residents', 950, 1000], ['rooms', 100, 100]]}
        full = rp.plan(self.STEPS, {'chim-room-batches', 'chim-town-mournhold'}, 8, got(30, 24), gathered)
        doc = rp.plan(self.STEPS, {'chim-room-batches', 'chim-town-mournhold'}, 8, got(30, 24), gathered,
                      units=units)
        rows = {r['stage']: r for r in doc['stages']}
        before = {r['stage']: r for r in full['stages']}['chim-room-batches']['wall_s']
        row = rows['chim-room-batches']
        self.assertEqual(row['units'], {'reused': 1050, 'to_bake': 50, 'held': 1100, 'new': None,
                                        'caches': ['room-residents', 'rooms']})
        self.assertAlmostEqual(row['wall_s'], round(before * 50 / 1100.0, 1), places=1)
        self.assertNotIn('new_work', row)
        self.assertTrue(rows['chim-town-mournhold']['new_work'])
        self.assertEqual(doc['new_work'], ['chim-town-mournhold'])
        self.assertEqual(rp.validate(doc), [])
        lines = rp.checklist(doc)
        self.assertTrue(any('1050 reused, 50 to bake' in line for line in lines))
        self.assertTrue(any(line.startswith('Resource plan: new work first') and 'chim-town-mournhold' in line
                            for line in lines))

    def test_unreadable_keys_count_every_held_unit_to_bake(self):
        import resource_plan as rp
        self.assertEqual(rp.unit_forecast([['c', None, 40]])['to_bake'], 40)
        self.assertIsNone(rp.unit_forecast([['c', 0, 0]]))
        self.assertIsNone(rp.unit_forecast(None))


if __name__ == '__main__':
    unittest.main()
