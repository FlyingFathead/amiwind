"""The shared animation table is built once per game data and code, not once per worker process
(RESIDENT-BAKE-VIVEC-COST-59): skeletal_actor.cached_table and prepare_area.table_warmers."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]     # src first: its mwad package, not tools/mwad.py
import pass_cache  # noqa: E402
import skeletal_actor as S  # noqa: E402

CHOICE = {'skeleton': 'meshes/base_anim.nif', 'over': 'meshes/base_anim_female.nif', 'append': 'f:', 'more': ['d:']}
REPORT = {'groups': 2, 'missing': [], 'frames': 3, 'bones': 1, 'bytes': 5, 'names': ['idle', 'walk'],
          'bone_names': ['bip01'], 'keys': 0, 'times': [0.0, 0.125, 0.25], 'over': []}


class CachedTableTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.calls = 0

    def build(self):
        self.calls += 1
        return b'AWSK!', dict(REPORT)

    def env(self, cache='on', identity='a' * 64):
        folder = self.tmp.name if cache == 'on' else 'off'
        return (mock.patch.dict(os.environ, {pass_cache.ENV: folder}),
                mock.patch.object(pass_cache, 'game_data_digest', return_value=identity))

    def test_built_once_then_read(self):
        env, digest = self.env()
        with env, digest:
            first = S.cached_table(CHOICE, self.build)
            second = S.cached_table(CHOICE, self.build)
        self.assertEqual(self.calls, 1)
        self.assertEqual(first, (b'AWSK!', REPORT))
        self.assertEqual(second, first)

    def test_other_game_data_or_table_builds_again(self):
        env, digest = self.env()
        with env, digest:
            S.cached_table(CHOICE, self.build)
        env, digest = self.env(identity='b' * 64)
        with env, digest:
            S.cached_table(CHOICE, self.build)
            S.cached_table(dict(CHOICE, skeleton='meshes/base_animkna.nif', over=None, append=None, more=[]),
                           self.build)
        self.assertEqual(self.calls, 3)

    def test_cache_off_or_no_input_lock_builds_every_time(self):
        for cache, identity in (('off', 'a' * 64), ('on', None)):
            env, digest = self.env(cache, identity)
            with env, digest:
                S.cached_table(CHOICE, self.build)
                S.cached_table(CHOICE, self.build)
        self.assertEqual(self.calls, 4)


class TableWarmersTest(unittest.TestCase):
    def task(self, ident, skeleton='meshes/base_anim.nif', female=False, dead=False):
        return ('/data', b'', {'id': ident, 'skeleton': skeleton, 'female': female, 'initially_dead': dead}, {}, 'ffmpeg')

    def test_one_task_per_table(self):
        import prepare_area
        tasks = [self.task('a'), self.task('b'), self.task('c', female=True), self.task('d', female=True),
                 self.task('e', 'meshes/base_animkna.nif'), self.task('f', 'meshes/base_animkna.nif', dead=True)]
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {pass_cache.ENV: tmp}), \
                mock.patch('npc_anim.anim_type', return_value=2):
            warm = prepare_area.table_warmers(tasks)
        self.assertEqual([t[2]['id'] for t in warm], ['a', 'c', 'e'])

    def test_none_for_baked_actors_or_without_cache(self):
        import prepare_area
        tasks = [self.task('a')]
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {pass_cache.ENV: tmp}), \
                mock.patch('npc_anim.anim_type', return_value=1):
            self.assertEqual(prepare_area.table_warmers(tasks), [])
        with mock.patch.dict(os.environ, {pass_cache.ENV: 'off'}), mock.patch('npc_anim.anim_type', return_value=2):
            self.assertEqual(prepare_area.table_warmers(tasks), [])


if __name__ == '__main__':
    unittest.main()
