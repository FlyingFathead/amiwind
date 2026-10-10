# SPDX-License-Identifier: GPL-3.0-only
"""Interior rooms, town regions and character head previews resume from their finished units
(BUILD-IMAGE-NO-RESUME-33, tools/pass_cache.py): a warm run converts nothing, a changed input converts
again, nothing is cached without a known game data identity, and rows that do not survive JSON are never
cached."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import pass_cache  # noqa: E402
from known_inputs import LOCK_ENV, LOCK_SCHEMA  # noqa: E402


def tree(folder):
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(Path(folder).rglob('*')) if p.is_file()}


class Env:
    """A cache folder and an input lock in a temporary folder."""

    def __init__(self, root, data_sha='a' * 64):
        self.root = Path(root)
        self.lock = self.root / 'inputs.lock'
        self.write_lock(data_sha)

    def write_lock(self, data_sha):
        self.lock.write_text(json.dumps({'schema': LOCK_SCHEMA, 'files': {'Morrowind.esm': {'sha256': data_sha}}}))

    def patch(self):
        return patch.dict(os.environ, {pass_cache.ENV: str(self.root / 'cache'), LOCK_ENV: str(self.lock)})


class GameDataTests(unittest.TestCase):
    def test_identity_follows_the_lock_and_is_none_without_one(self):
        with tempfile.TemporaryDirectory() as temp:
            env = Env(temp)
            with env.patch():
                first = pass_cache.game_data_digest()
                env.write_lock('b' * 64)
                self.assertNotEqual(first, pass_cache.game_data_digest())
            with patch.dict(os.environ, {LOCK_ENV: ''}):
                self.assertIsNone(pass_cache.game_data_digest())

    def test_json_exact(self):
        self.assertTrue(pass_cache.json_exact({'a': [1, 'x']}))
        self.assertFalse(pass_cache.json_exact({'a': (1, 2)}))
        self.assertFalse(pass_cache.json_exact({'a': object()}))


class RoomUnitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.scene = self.root / 'scene'
        (self.scene / 'id1/gfx').mkdir(parents=True)
        (self.scene / 'id1/gfx/palette.lmp').write_bytes(bytes(768))
        self.tool = self.root / 'qbsp'
        self.tool.write_bytes(b'tool')
        self.calls = []

    def tearDown(self):
        self.temp.cleanup()

    def task(self, scene=None):
        entry = {'map': 'room1', 'cell': 'Balmora, Room'}
        return ('/data', scene or self.scene, entry, self.tool, self.tool, self.tool, 'timings', 2, 'fast')

    def fake_build(self, task):
        self.calls.append(task[2]['map'])
        folder = Path(task[1]) / 'area-work' / task[2]['map']
        folder.mkdir(parents=True)
        (folder / 'room.bsp').write_bytes(b'room bytes')
        return {'map': task[2]['map'], 'bytes': 10}, {'name': 'Balmora, Room', 'entrances': []}

    def test_warm_run_restores_the_room_and_a_changed_input_builds_again(self):
        import prepare_area
        env = Env(self.root)
        with env.patch(), patch.object(prepare_area, 'build_room', side_effect=self.fake_build):
            first = prepare_area.build_room_cached(self.task())
            other = self.root / 'other'
            (other / 'id1/gfx').mkdir(parents=True)
            (other / 'id1/gfx/palette.lmp').write_bytes(bytes(768))
            second = prepare_area.build_room_cached(self.task(other))
            self.assertEqual(first, second)
            self.assertEqual(self.calls, ['room1'])
            self.assertEqual(tree(other / 'area-work'), tree(self.scene / 'area-work'))
            env.write_lock('c' * 64)                      # other game data: built again
            third = self.root / 'third'
            (third / 'id1/gfx').mkdir(parents=True)
            (third / 'id1/gfx/palette.lmp').write_bytes(bytes(768))
            prepare_area.build_room_cached(self.task(third))
            self.assertEqual(self.calls, ['room1', 'room1'])

    def test_no_lock_means_no_cache(self):
        import prepare_area
        with patch.dict(os.environ, {pass_cache.ENV: str(self.root / 'cache'), LOCK_ENV: ''}), \
                patch.object(prepare_area, 'build_room', side_effect=self.fake_build):
            prepare_area.build_room_cached(self.task())
        self.assertFalse((self.root / 'cache').exists())

    def test_rows_that_change_in_json_are_not_cached(self):
        import prepare_area
        env = Env(self.root)

        def tuple_build(task):
            report, cell = self.fake_build(task)
            return report, dict(cell, position=(1, 2, 3))
        with env.patch(), patch.object(prepare_area, 'build_room', side_effect=tuple_build):
            prepare_area.build_room_cached(self.task())
        self.assertEqual(list((self.root / 'cache').rglob('*.json')), [])


class HeadUnitTests(unittest.TestCase):
    def test_heads_come_from_the_cache_by_part_and_palette(self):
        import prepare_character
        calls = []

        def head(task):
            calls.append(task[1]['id'])
            return b'AWH1' + task[1]['id'].encode()
        with tempfile.TemporaryDirectory() as temp:
            env = Env(temp)
            with env.patch(), patch.object(prepare_character, '_head', side_effect=head):
                cache = prepare_character.head_cache()
                part = {'id': 'b_n_nord_m_head_01', 'race': 1, 'female': 0, 'kind': 0, 'model': 'x.nif'}
                one = prepare_character._head_cached(('/data', part, bytes(768), cache))
                two = prepare_character._head_cached(('/data', part, bytes(768), cache))
                prepare_character._head_cached(('/data', part, bytes([1]) * 768, cache))
            self.assertEqual(one, two)
            self.assertEqual(calls, ['b_n_nord_m_head_01', 'b_n_nord_m_head_01'])


class TownRegionUnitTests(unittest.TestCase):
    def test_a_finished_region_is_restored_with_its_log_text(self):
        import import_town
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            calls = []

            def compile_region(task):
                calls.append(task[1])
                folder = root / 'out' / 'bm000'
                folder.mkdir(parents=True)
                (folder / 'scene.bsp').write_bytes(b'region')
                return ({'name': 'bm000', 'instances': 3}, []), 'compiled bm000\n'
            cache = pass_cache.UnitCache('town-region', {'environment': {}}, 's', root / 'cache')
            inputs = {'entry': {'name': 'bm000'}, 'game_data': 'g'}
            context = {'out': root / 'out'}
            with patch.object(import_town, '_compile_region', side_effect=compile_region), \
                    patch.object(import_town, '_region_context', return_value=context):
                first = import_town._compile_region_cached(('ctx', 0, 1, cache, inputs))
                saved = tree(root / 'out')
                import shutil
                shutil.rmtree(root / 'out')
                second = import_town._compile_region_cached(('ctx', 0, 1, cache, inputs))
            self.assertEqual(first, second)
            self.assertEqual(calls, [0])
            self.assertEqual(tree(root / 'out'), saved)


class RebuildUnitTests(unittest.TestCase):
    def test_a_named_unit_is_built_again_and_listed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / 'f'
            folder.mkdir()
            (folder / 'room.bsp').write_bytes(b'x')
            cache = pass_cache.UnitCache('interior-room', {'environment': {}}, 's', root / 'cache')
            inputs = {'entry': {'map': 'bmtemple'}}
            cache.store_unit(inputs, {'ok': 1}, folder)
            self.assertEqual(cache.restore_unit(inputs, root / 'a'), {'ok': 1})
            for value in ('interior-room:bmtemple', 'interior-room:*'):
                with patch.dict(os.environ, {pass_cache.REBUILD_ENV: value}):
                    self.assertIsNone(cache.restore_unit(inputs, root / 'b'))
            with patch.dict(os.environ, {pass_cache.REBUILD_ENV: 'interior-room:other,town-region:bmtemple'}):
                self.assertEqual(cache.restore_unit(inputs, root / 'c'), {'ok': 1})
            rows = pass_cache.list_units(root / 'cache')
            self.assertEqual([(r[0], r[1], r[3], r[4]) for r in rows], [('interior-room', 'bmtemple', 1, 1)])


if __name__ == '__main__':
    unittest.main()
