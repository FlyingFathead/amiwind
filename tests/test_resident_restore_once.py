"""ROOM-RESIDENTS-KEY-SERIAL-49: the resident bakes' unit cache is opened once per stage, not once per resident.

The room residents step spent 233 s on one core for 1,769 residents before the first restore: every resident opened
the unit cache (which analyses the repository's sources for its environment) and read the build's input lock (about
7 MB of JSON) for the game data identity. prepare_area.open_residents() opens both once; resident_unit and
restore_resident take that open. The keys must be the same whichever way the cache was opened, and restores on
threads must give the same records and the same files (SHA-256) as one by one."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]


def fake_bake(task):
    ident = task[2]['id']
    return ident, b'mdl ' + ident.encode() * 50, b'wav ' + ident.encode(), {
        'appearance': task[2], 'greeting': task[3], 'step': 0.25, 'triangles': 3, 'frames': 8,
        'bounds': ((0, 0, 0), (1, 1, 1)), 'sha256': 'x', 'voice_seconds': 1.0}


class ResidentsOpenOnce(unittest.TestCase):

    def setUp(self):
        import known_inputs
        self.tmp = tempfile.TemporaryDirectory()
        tmp = self.tmp_path = Path(self.tmp.name)
        lock = tmp / 'inputs.json'
        lock.write_text(json.dumps({'schema': known_inputs.LOCK_SCHEMA,
                                    'files': {'Morrowind.esm': {'sha256': '0' * 64}}}))
        ffmpeg = tmp / 'ffmpeg'
        ffmpeg.write_bytes(b'not a real program')
        levels = tmp / 'levels.json'
        levels.write_text('{"near": 1}')
        self.env = {'AMIWIND_PASS_CACHE': str(tmp / 'cache'), known_inputs.LOCK_ENV: str(lock)}
        self.tasks = [('data', b'p' * 768, {'id': 'npc%02d' % i, 'parts': [], 'skeleton': 's'},
                       {'text': 'Hi %d' % i, 'voice': 'v.mp3'}, str(ffmpeg),
                       {'mode': 'on', 'pool': '/somewhere/%d' % i, 'list': str(levels)})
                      for i in range(24)]

    def tearDown(self):
        self.tmp.cleanup()

    def test_shared_open_gives_the_same_keys(self):
        import prepare_area as P
        from pass_cache import input_digest
        with patch.dict(os.environ, self.env):
            opened = P.open_residents()
            self.assertIsNotNone(opened[0])
            digests = {}
            for task in self.tasks:
                alone, inputs_alone = P.resident_unit(task)
                shared, inputs_shared = P.resident_unit(task, opened, digests)
                self.assertEqual(inputs_alone, inputs_shared)
                self.assertEqual(alone.key(input_digest(inputs_alone)), shared.key(input_digest(inputs_shared)))
                self.assertEqual((alone.name, alone.options, alone.sources), (shared.name, shared.options,
                                                                              shared.sources))
            self.assertEqual(len(digests), 1)            # the level list hashed once for every resident

    def test_threaded_restores_open_nothing_and_match_one_by_one(self):
        import pass_cache
        import prepare_area as P
        tmp = self.tmp_path
        with patch.dict(os.environ, self.env), patch.object(P, 'build_resident', fake_bake):
            for task in self.tasks:                      # bake and store every resident once
                P.build_resident_cached((task, str(tmp / 'bake' / task[2]['id'])))
            serial = {}
            for task in self.tasks:
                folder = tmp / 'serial' / task[2]['id']
                cache, inputs, record = P.restore_resident(task, folder)
                self.assertIsNotNone(record)
                serial[task[2]['id']] = (record, {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes())
                                                  .hexdigest() for p in folder.rglob('*') if p.is_file()})
            opened = P.open_residents()
            calls = {'open': 0, 'identity': 0}
            real_open, real_identity = pass_cache.UnitCache.open, pass_cache.game_data_digest

            def counted_open(*args, **kwargs):
                calls['open'] += 1
                return real_open(*args, **kwargs)

            def counted_identity():
                calls['identity'] += 1
                return real_identity()
            digests = {}
            with patch.object(pass_cache.UnitCache, 'open', counted_open), \
                    patch.object(pass_cache, 'game_data_digest', counted_identity):
                with ThreadPoolExecutor(8) as pool:
                    rows = list(pool.map(lambda t: P.restore_resident(t, tmp / 'threads' / t[2]['id'], opened,
                                                                      digests), self.tasks))
            self.assertEqual(calls, {'open': 0, 'identity': 0})
            for task, (cache, inputs, record) in zip(self.tasks, rows):
                folder = tmp / 'threads' / task[2]['id']
                files = {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in folder.rglob('*') if p.is_file()}
                self.assertEqual((record, files), serial[task[2]['id']])

    def test_cache_off_restores_nothing(self):
        import prepare_area as P
        with patch.dict(os.environ, {'AMIWIND_PASS_CACHE': 'off'}):
            self.assertEqual(P.open_residents(), (None, None))
            self.assertEqual(P.restore_resident(self.tasks[0], self.tmp_path / 'x', (None, None), {}),
                             (None, None, None))


if __name__ == '__main__':
    unittest.main()
