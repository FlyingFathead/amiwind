"""A failing player-view unit does not throw away the finished ones: run_units stores every finished unit in the unit
cache, then fails naming every failed unit (incident INC-20261108-V062BUILD, cause C4: each resume of the v0.0.62
final build baked every player body again because one failing body ended the map before anything was stored)."""
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))


class FakeCache:
    def __init__(self):
        self.stored = []

    def load_unit(self, inputs):
        return None

    def store_files(self, inputs, *packed):
        self.stored.append(inputs)


def fake_map(fn, items, jobs=None, cost=None):
    for item in items:
        yield fn(item)


class KeepsFinishedUnits(unittest.TestCase):
    def test_a_failing_unit_keeps_the_finished_ones(self):
        import prepare_player_view as view
        units =[('body', ('d', b'', race, False)) for race in ('A', 'B', 'C')]

        def bake(unit):
            if unit[1][2] == 'B':
                raise ValueError('player body B male: no body fits the existing budgets (x)')
            return ('result', unit[1][2])

        cache = FakeCache()
        with mock.patch.object(view, 'bake_unit', side_effect=bake), \
             mock.patch('build_parallel.completed_map', side_effect=fake_map), \
             mock.patch('build_jobs.resolve_jobs', return_value=2), \
             mock.patch.object(view, 'pack_result', side_effect=lambda r: ('row', {})), \
             mock.patch.object(view, 'unit_inputs', side_effect=lambda u: u[1][2]), \
             mock.patch('pass_cache.forced', return_value=False):
            with self.assertRaisesRegex(ValueError, r'body B male.*1 of 3 units failed; the 2 finished ones are kept'):
                view.run_units(units, cache, 2)
        self.assertEqual(cache.stored, ['A', 'C'])

    def test_all_units_pass_as_before(self):
        import prepare_player_view as view
        units =[('body', ('d', b'', race, True)) for race in ('A', 'B')]
        cache = FakeCache()
        with mock.patch.object(view, 'bake_unit', side_effect=lambda u: ('result', u[1][2])), \
             mock.patch('build_parallel.completed_map', side_effect=fake_map), \
             mock.patch('build_jobs.resolve_jobs', return_value=2), \
             mock.patch.object(view, 'pack_result', side_effect=lambda r: ('row', {})), \
             mock.patch.object(view, 'unit_inputs', side_effect=lambda u: u[1][2]), \
             mock.patch('pass_cache.forced', return_value=False):
            results, reused = view.run_units(units, cache, 2)
        self.assertEqual(results, [('result', 'A'), ('result', 'B')])
        self.assertEqual(reused, 0)
        self.assertEqual(cache.stored, ['A', 'B'])


if __name__ == '__main__':
    unittest.main()
