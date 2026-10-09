"""Per-file converter cache: byte-identical outputs against a cold run, verified hits, counts (BUILD-CACHE-OVERBROAD-33)."""
import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import build  # noqa: E402
import build_summary  # noqa: E402
from file_cache import FileCache, write_report  # noqa: E402
import prepare_media_assets  # noqa: E402
from prepare_video import cached_prepare_video, video_cache_identity  # noqa: E402

FFMPEG = shutil.which('ffmpeg') and shutil.which('ffprobe')


def tree(folder):
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(Path(folder).rglob('*')) if p.is_file()}


def write_tone(path, frequency, rate=22050):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as audio:
        audio.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        audio.writeframes(b''.join(struct.pack('<h', (i * frequency) % 6000 - 3000) for i in range(rate // 10)))


class FileCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_store_fetch_verify_and_keys(self):
        cache = FileCache(self.root / 'cache', 'sound', {'ffmpeg': 'x', 'code': 'y'})
        output = self.root / 'converted.bin'
        output.write_bytes(b'converted bytes')
        key = cache.key('a' * 64, {'rate': 11025})
        self.assertIsNone(cache.fetch(key, self.root / 'out' / 'one.bin'))
        self.assertTrue(cache.store(key, output, {'frames': 7, 'order': 1}))
        self.assertEqual(cache.fetch(key, self.root / 'out' / 'one.bin'), {'frames': 7, 'order': 1})
        self.assertEqual((self.root / 'out' / 'one.bin').read_bytes(), b'converted bytes')
        # Every part of the key counts: source, settings, programs and code.
        self.assertNotEqual(key, cache.key('b' * 64, {'rate': 11025}))
        self.assertNotEqual(key, cache.key('a' * 64, {'rate': 22050}))
        self.assertNotEqual(key, FileCache(self.root / 'cache', 'sound', {'ffmpeg': 'z', 'code': 'y'}).key('a' * 64, {'rate': 11025}))
        self.assertNotEqual(key, FileCache(self.root / 'cache', 'sound', {'ffmpeg': 'x', 'code': 'w'}).key('a' * 64, {'rate': 11025}))
        # Another key with the same output bytes points at the same pool object (stored once).
        other = cache.key('c' * 64, {'rate': 11025})
        self.assertTrue(cache.store(other, output, {'frames': 7}))
        self.assertEqual(len([p for p in (self.root / 'cache' / 'objects').rglob('*') if p.is_file()]), 1)
        cache.counts['stored'] -= 1
        # A damaged entry is never used.
        blob = next(p for p in (self.root / 'cache' / 'objects').rglob('*') if p.is_file())
        self.assertEqual(blob.name, __import__('hashlib').sha256(b'converted bytes').hexdigest())  # stored by content
        blob.write_bytes(b'damaged bytes!!')
        self.assertIsNone(cache.fetch(key, self.root / 'out' / 'two.bin'))
        self.assertFalse((self.root / 'out' / 'two.bin').exists())
        self.assertEqual(cache.counts, {'hits': 1, 'misses': 1, 'stored': 1, 'rejected': 1})
        off = FileCache(None, 'sound', None)
        self.assertFalse(off.enabled)
        self.assertIsNone(off.fetch(key, self.root / 'x'))
        self.assertFalse(off.store(key, output))

    def test_builder_passes_the_cache_to_development_builds_only(self):
        args = argparse.Namespace(workspace=Path('/w'), no_media_cache=False, allow_release_reuse=False)
        run = Path('/w/build/dev-a')
        with patch.object(build, 'VERSION', '0.0.33-dev1'):
            self.assertEqual(build.media_file_cache(args, run, 'media'),
                             ['--cache', Path('/w/cache/asset-pool-v1'), '--cache-report', run / 'profile' / 'file-cache' / 'media.json'])
            self.assertEqual(build.media_file_cache(argparse.Namespace(**dict(vars(args), no_media_cache=True)), run, 'media'), [])
        with patch.object(build, 'VERSION', '0.0.33'):
            self.assertEqual(build.media_file_cache(args, run, 'intro'), [])
            self.assertTrue(build.media_file_cache(argparse.Namespace(**dict(vars(args), allow_release_reuse=True)), run, 'intro'))

    def test_build_summary_reports_hits_and_misses(self):
        run = self.root / 'run'
        write_report(run / 'profile' / 'file-cache' / 'media.json', 'media',
                     {'sounds': {'hit': 7180, 'miss': 5, 'enabled': True}, 'videos': {'hit': 17, 'miss': 0, 'enabled': True}})
        record = build_summary.read_file_cache(run)
        self.assertEqual(record['media']['sounds']['hit'], 7180)
        self.assertEqual(build_summary.file_cache_lines(record),
                         ['Per-file cache (media): sounds 7180 reused, 5 converted; videos 17 reused, 0 converted'])
        self.assertEqual(build_summary.read_file_cache(self.root / 'none'), {})


@unittest.skipUnless(FFMPEG, 'requires ffmpeg and ffprobe')
class ConverterCacheTests(unittest.TestCase):
    """A warm run (every file from the cache) writes the same bytes as a cold run and as a run without cache."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / 'data'
        self.data.mkdir()
        (self.data / 'Morrowind.esm').write_bytes(b'')
        (self.data / 'Morrowind.bsa').write_bytes(struct.pack('<III', 0x100, 0, 0))
        for index, name in enumerate(('Sound/Fx/punch.wav', 'Sound/Vo/r/m/hello.wav', 'Sound/Cr/howl.wav')):
            write_tone(self.data / name, 300 + 100 * index)
        (self.data / 'Video').mkdir()
        subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-f', 'lavfi', '-i', 'testsrc2=size=320x180:rate=10',
                        '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=11025', '-t', '0.4', '-c:v', 'ffv1',
                        '-c:a', 'pcm_s16le', '-f', 'matroska', str(self.data / 'Video' / 'mw_logo.bik')], check=True)
        self.cache = self.root / 'cache'

    def tearDown(self):
        self.temp.cleanup()

    def media(self, name, cache=None, jobs=2):
        out = self.root / name
        report = self.root / 'reports' / f'{name}.json'
        prepare_media_assets.prepare(self.data, out, 'ffmpeg', jobs, cache=cache, cache_report=report)
        return out, json.loads(report.read_text())['groups']

    def test_media_warm_run_is_byte_identical_to_cold_runs(self):
        plain, counts = self.media('plain')
        self.assertEqual(counts['sounds'], {'hit': 0, 'miss': 3, 'enabled': False})
        cold, counts = self.media('cold', self.cache)
        self.assertEqual((counts['sounds']['miss'], counts['videos']['miss']), (3, 1))
        warm, counts = self.media('warm', self.cache, jobs=1)
        self.assertEqual(counts, {'sounds': {'hit': 3, 'miss': 0, 'enabled': True},
                                  'videos': {'hit': 1, 'miss': 0, 'enabled': True}})
        self.assertEqual(tree(warm), tree(cold))
        self.assertEqual(tree(warm), tree(plain))
        catalogue = json.loads((warm / 'id1' / 'media' / 'catalogue.json').read_text())
        self.assertEqual(catalogue['categories']['voices']['included'], 1)
        self.assertEqual([row['status'] for row in catalogue['entries'] if row['category'] == 'videos' and 'id' in row
                          and row['name'] == 'mw_logo'], ['included'])
        # A damaged cache entry is converted again (and replaced), never copied.
        sounds = [json.loads(p.read_text())['sha256'] for p in (self.cache / 'keys' / 'sound').rglob('*.json')]
        for blob in [self.cache / 'objects' / digest[:2] / digest for digest in sounds]:
            blob.write_bytes(b'damaged')
            break
        again, counts = self.media('again', self.cache)
        self.assertEqual(counts['sounds'], {'hit': 2, 'miss': 1, 'enabled': True})
        self.assertEqual(tree(again), tree(cold))
        # A changed source is a new key: converted, not taken from the cache.
        write_tone(self.data / 'Sound/Fx/punch.wav', 999)
        changed, counts = self.media('changed', self.cache)
        self.assertEqual(counts['sounds'], {'hit': 2, 'miss': 1, 'enabled': True})
        self.assertNotEqual(tree(changed), tree(cold))

    def test_intro_movie_folder_is_byte_identical(self):
        source = self.data / 'Video' / 'mw_logo.bik'
        cache = (str(self.cache), video_cache_identity('ffmpeg'))
        plain, outcome = cached_prepare_video(source, self.root / 'plain', 'ffmpeg')
        self.assertEqual(outcome, 'off')
        cold, outcome = cached_prepare_video(source, self.root / 'cold', 'ffmpeg', cache=cache)
        self.assertEqual(outcome, 'miss')
        warm, outcome = cached_prepare_video(source, self.root / 'warm', 'ffmpeg', cache=cache)
        self.assertEqual(outcome, 'hit')
        self.assertEqual(warm, cold)
        self.assertEqual(tree(self.root / 'warm'), tree(self.root / 'cold'))
        self.assertEqual(tree(self.root / 'warm'), tree(self.root / 'plain'))
        # Another size is another key.
        _, outcome = cached_prepare_video(source, self.root / 'small', 'ffmpeg', size=(160, 100), cache=cache)
        self.assertEqual(outcome, 'miss')


if __name__ == '__main__':
    unittest.main()
