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


class ResidentAndRoomKeys(unittest.TestCase):
    """UNIT-KEY-WHOLE-FILE-63: the resident and room unit caches keyed every unit on the whole of
    tools/prepare_area.py (and tools/chim_room_batches.py), so the v0.0.63 edits elsewhere in that file (the residents'
    own scratch folder, the [d/t] lines) re-keyed all 1,769 residents and every room; the dev1 build baked them again."""

    def test_the_caches_key_on_the_code_that_makes_a_unit(self):
        import inspect
        import chim_room_batches
        import prepare_area
        for function, reach in ((prepare_area.open_residents,
                                 "source_digest((__file__, 'build_resident'), (__file__, 'publish_resident'))"),
                                (prepare_area.room_unit, "source_digest((__file__, 'build_room'))"),
                                (chim_room_batches.open_units, "source_digest((__file__, 'build_shell'))")):
            source = inspect.getsource(function)
            # the digest call written in the module, so the stage's own key covers what the cache key reads
            self.assertIn(reach, source)
            self.assertIn('bake_keyed_cache(', source)
            self.assertIn('neutral=WORK_PLACE_SETTINGS', source)
            self.assertNotIn('UnitCache.open(', source)

    def test_unit_store_names_no_files(self):
        """tools/unit_store.py is reached by the room tools: a file name written in it counts as a file their code
        reads, which widened their AMIWIND_* environment (part of every unit key) and missed every stored unit."""
        text = (ROOT / 'tools' / 'unit_store.py').read_text(encoding='utf-8')
        import ast
        tree = ast.parse(text)
        docstrings = {id(node.value) for node in ast.walk(tree) if isinstance(node, ast.Expr)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
                self.assertNotRegex(node.value, r'\.(py|json)\b', node.value[:80])

    def test_the_units_of_the_v062_release_build_are_kept(self):
        """The bake-reach digests of fe90f8ed (equal on v0.0.63-integ) map to the whole-file digests its units were
        stored under; measured in the container on both trees."""
        import unit_store
        self.assertEqual(unit_store.legacy_sources(
            'resident-bake', '4318d4be491911a8a2867bb8873f23a052a1616df08f4151d7344705a13ec576'),
            ('9e0e915fef811882a5c341a96549762b7fb07ea768a876fa0f0c9411ce8d1786',))
        self.assertEqual(unit_store.legacy_sources(
            'interior-room', '4a4ff8d268a2b8030c1bd8b294aa61c888f734bf66edbbb91e040b370a2c45a2'),
            ('9e0e915fef811882a5c341a96549762b7fb07ea768a876fa0f0c9411ce8d1786',))
        self.assertEqual(unit_store.legacy_sources(
            'interior-room-chim', '02b87fd3252e52456b3e2688fcc2ce3172853ef735ae43d159ef43f1a9983d49'),
            ('115d5e69098e1c5ffd0cf15e11c4431f326b8767ea01d5f650b0885fa1604b0a',))

    def test_where_the_work_runs_is_not_in_the_key(self):
        import pass_cache
        import unit_store
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, {pass_cache.ENV: folder}), \
                mock.patch('pass_cache.environment', return_value={'AMIWIND_RESIDENT_WORK': None, 'AMIWIND_X': '1'}):
            cache = unit_store.bake_keyed_cache('n', {}, 'd', (), ('f',), neutral=unit_store.WORK_PLACE_SETTINGS)
        self.assertEqual(cache.options, {'environment': {'AMIWIND_X': '1'}})

    def test_every_whole_file_unit_key_is_listed(self):
        """A unit cache keyed on whole files re-keys every unit on any edit of those files: each one left is listed
        in WHOLE_FILE_KEYS, so a new one is seen (and keyed on its bake code instead)."""
        import ast
        found = set()
        for path in sorted((ROOT / 'tools').rglob('*.py')):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'open' \
                        and isinstance(node.func.value, ast.Name) and node.func.value.id == 'UnitCache' and node.args:
                    found.add((path.name, ast.unparse(node.args[0])))
        self.assertEqual(found - WHOLE_FILE_KEYS, set(), 'new whole-file unit keys')
        self.assertEqual(WHOLE_FILE_KEYS - found, set(), 'listed but no longer whole-file keyed')


# Every unit cache in tools/ that still keys its units on whole files (UnitCache.open): (module, cache name as
# written in the call). Kept here, not in tools/unit_store.py (file names there would count in its users' keys).
WHOLE_FILE_KEYS = frozenset({
    ('ambient_lut.py', "'npc-ambient-table'"),
    ('import_town.py', "'town-region'"),
    ('prepare_player_fp_parts.py', 'UNIT_CACHE'),
    ('prepare_player_parts.py', 'UNIT_CACHE'),
    ('prepare_world_flora.py', "'world-flora-region'"),
    ('prepare_world_scenery.py', "'world-scenery-region'"),
    ('skeletal_actor.py', 'TABLE_UNIT'),
    ('tp_places_lut.py', "'tp-places-table'"),
})


def chim_unit(task):
    if task == 'bad':
        raise ValueError('mesh does not convert')
    return 'unit ' + task


class ChimUnitsStoreEach(unittest.TestCase):
    """tools/chim/units.py run_units stores each CHIM unit as it comes back, so a map stopped by a failing unit keeps
    every unit made before it."""

    def test_units_made_before_a_failure_are_kept(self):
        import io
        import contextlib
        from chim import units
        with tempfile.TemporaryDirectory() as tmp:
            cache = units.UnitCache(Path(tmp) / 'chim-units')
            items = [('a' * 64, 'one'), ('b' * 64, 'two'), ('c' * 64, 'bad'), ('d' * 64, 'four')]
            output = io.StringIO()
            with mock.patch('build_parallel.completed_map', serial_map), contextlib.redirect_stdout(output):
                with self.assertRaises(ValueError):
                    units.run_units('frame', items, chim_unit, 2, cache)
            self.assertEqual(cache.get('frame', 'a' * 64), 'unit one')
            self.assertEqual(cache.get('frame', 'b' * 64), 'unit two')
            self.assertIsNone(cache.get('frame', 'd' * 64))
            self.assertIn('CHIM frame units [0/4] cached, 4 to make', output.getvalue())
            self.assertIn('CHIM frame units [2/4] ', output.getvalue())
            output = io.StringIO()
            with mock.patch('build_parallel.completed_map', serial_map), contextlib.redirect_stdout(output):
                results = units.run_units('frame', items[:2] + items[3:], chim_unit, 2, cache)
            self.assertEqual(results, ['unit one', 'unit two', 'unit four'])
            self.assertIn('CHIM frame units [2/3] cached, 1 to make', output.getvalue())


if __name__ == '__main__':
    unittest.main()
