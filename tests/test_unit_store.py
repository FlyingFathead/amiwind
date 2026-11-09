"""Every finished unit goes into the unit cache the moment it comes back, and a unit cache whose key changes form keeps
the units stored under its old key (UNIT-STORED-AT-MAP-END-62, incident INC-20261108-V062BUILD: the player view
stored its bodies only when its whole pool map ended, so a stage stopped mid-map kept nothing and every resume of the
v0.0.62 release build baked every player body again)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))


def serial_map(function, items, jobs=None, cost=None):
    for item in items:
        yield function(item)


def bake(task):
    if task == 'bad':
        raise ValueError('no body fits')
    return 'made ' + task


class RunEach(unittest.TestCase):
    def setUp(self):
        os.environ.pop('AMIWIND_COST_HISTORY', None)

    def test_each_unit_is_kept_before_the_next_comes_back(self):
        import unit_store
        kept = []

        def watching(function, items, jobs=None, cost=None):
            for number, item in enumerate(items):
                self.assertEqual(len(kept), number, 'a unit was handed back before the one before it was kept')
                yield function(item)
        with mock.patch('build_parallel.completed_map', side_effect=watching):
            failed = unit_store.run_each('test-units', bake, [(0, 'a'), (1, 'b'), (2, 'c')], ['a', 'b', 'c'], 2,
                                         lambda index, result: kept.append((index, result)))
        self.assertEqual(failed, [])
        self.assertEqual(kept, [(0, 'made a'), (1, 'made b'), (2, 'made c')])

    def test_a_failing_unit_is_named_and_the_rest_are_kept(self):
        import unit_store
        kept = []
        with mock.patch('build_parallel.completed_map', side_effect=serial_map):
            failed = unit_store.run_each('test-units', bake, [(0, 'a'), (1, 'bad'), (2, 'c')], ['a', 'bad', 'c'], 2,
                                         lambda index, result: kept.append(index))
        self.assertEqual(kept, [0, 2])
        self.assertEqual(len(failed), 1)
        self.assertIn('bad: ValueError: no body fits', failed[0])

    def test_a_map_stopped_midway_keeps_every_unit_that_came_back(self):
        """The gate test of the maintainer's order: a stage stopped in the middle of its map (a lost pool, a stopped
        container) finds every unit that came back in the cache, and their times in the cost history."""
        import unit_store
        kept, recorded = [], []

        def stops_after_two(function, items, jobs=None, cost=None):
            for number, item in enumerate(items):
                if number == 2:
                    raise RuntimeError('pool lost')
                yield function(item)
        with mock.patch('build_parallel.completed_map', side_effect=stops_after_two), \
                mock.patch('build_costs.record', side_effect=lambda name, keys, seconds: recorded.append(list(keys))):
            with self.assertRaisesRegex(RuntimeError, 'pool lost'):
                unit_store.run_each('test-units', bake, [(i, t) for i, t in enumerate('abcd')], list('abcd'), 2,
                                    lambda index, result: kept.append(index))
        self.assertEqual(kept, [0, 1])
        self.assertEqual(recorded, [['a', 'b']])

    def test_every_unit_prints_done_of_total_as_it_comes_back(self):
        import unit_store
        lines = []
        with mock.patch('build_parallel.completed_map', side_effect=serial_map):
            unit_store.run_each('test-units', bake, [(0, 'a'), (1, 'bad'), (2, 'c')], ['a', 'bad', 'c'], 2,
                                lambda index, result: None, label='Player view', already=5,
                                log=lambda text, flush=False: lines.append(text))
        self.assertEqual(lines[0], 'Player view [5/8] cached, 3 to make')
        self.assertRegex(lines[1], r'^Player view \[6/8\] a \d+s$')
        self.assertRegex(lines[2], r'^Player view \[7/8\] bad FAILED \d+s$')
        self.assertRegex(lines[3], r'^Player view \[8/8\] c \d+s$')
        self.assertEqual(unit_store.progress_line('X', 3, 9, 'body a', 2472.4), 'X [3/9] body a 41m12s')

    def test_one_name_per_item(self):
        import unit_store
        with self.assertRaises(ValueError):
            unit_store.run_each('test-units', bake, [(0, 'a')], [], 1, lambda index, result: None)


class LegacyKeys(unittest.TestCase):
    def test_the_old_whole_file_key_is_used_only_for_unchanged_bake_code(self):
        import unit_store
        with mock.patch.dict(unit_store.LEGACY_SOURCES, {('cache', 'bake-now'): ('whole-file-then',)}, clear=True):
            self.assertEqual(unit_store.legacy_sources('cache', 'bake-now'), ('whole-file-then',))
            self.assertEqual(unit_store.legacy_sources('cache', 'bake-changed'), ())
            self.assertEqual(unit_store.legacy_sources('other', 'bake-now'), ())

    def test_a_unit_stored_under_the_old_key_is_found_under_the_new_one(self):
        """Backwards compatible: a unit stored by UnitCache.open (whole-file key) is found by the bake-keyed cache
        of the same files while the bake digest is in LEGACY_SOURCES, and stored again under the new key."""
        import pass_cache
        import unit_store
        script = str(ROOT / 'tools' / 'unit_store.py')
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, {pass_cache.ENV: folder}):
            old = pass_cache.UnitCache.open('legacy-test', {'game_data': 'g'}, script)
            old.store_files({'entry': {'name': 'body a'}}, {'report': 1}, {'0': b'bytes'})
            with mock.patch.dict(unit_store.LEGACY_SOURCES, {('legacy-test', 'bake-digest'): (old.sources,)}):
                new = unit_store.bake_keyed_cache('legacy-test', {'game_data': 'g'}, 'bake-digest', (), (script,))
                self.assertEqual(new.options, old.options)
                self.assertEqual(new.load_unit({'entry': {'name': 'body a'}}), ({'report': 1}, {'0': b'bytes'}))
            plain = unit_store.bake_keyed_cache('legacy-test', {'game_data': 'g'}, 'bake-digest', (), (script,))
            self.assertEqual(plain.load_unit({'entry': {'name': 'body a'}}), ({'report': 1}, {'0': b'bytes'}),
                             'the hit under the old key was not stored under the new key')
            changed = unit_store.bake_keyed_cache('legacy-test', {'game_data': 'g'}, 'other-digest', (), (script,))
            self.assertIsNone(changed.load_unit({'entry': {'name': 'body a'}}))

    def test_cache_off(self):
        import pass_cache
        import unit_store
        with mock.patch.dict(os.environ, {pass_cache.ENV: 'off'}):
            self.assertIsNone(unit_store.bake_keyed_cache('x', {}, 'd', (), ()))


class PlayerViewKey(unittest.TestCase):
    def test_the_player_view_keys_on_its_bake_code(self):
        """The player view's unit key covers what its bake runs (bake_unit, bake_body), so a change to how its units
        are scheduled or stored (run_units) keeps every stored unit."""
        import inspect
        import prepare_player_view
        source = inspect.getsource(prepare_player_view._unit_cache)
        self.assertIn("(__file__, 'bake_unit'), (player_inventory_pose.__file__, 'bake_body')", source)
        self.assertNotIn('UnitCache.open(', source)
        self.assertIn('unit_store.run_each(', inspect.getsource(prepare_player_view.run_units))


if __name__ == '__main__':
    unittest.main()
