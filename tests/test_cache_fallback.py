# SPDX-License-Identifier: GPL-3.0-only
"""A build on a new workspace reads the --reuse-from workspace's per-file caches read-only
(BUILD-CACHE-PER-WORKSPACE-33): the asset pool and the image pass cache find an entry there,
copy it into their own pool, and never write to the other one."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]
import file_cache  # noqa: E402
import pass_cache  # noqa: E402


def listing(folder):
    return sorted((p.relative_to(folder).as_posix(), p.read_bytes()) for p in Path(folder).rglob('*') if p.is_file())


class CacheFallback(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.addCleanup(__import__('shutil').rmtree, self.tmp)
        self.old = self.tmp / 'old-workspace' / 'cache'
        self.new = self.tmp / 'new-workspace' / 'cache'
        (self.old / 'asset-pool-v1').mkdir(parents=True)
        self.new.mkdir(parents=True)

    def test_asset_pool_reads_the_other_workspace_and_pools_here(self):
        source = self.tmp / 'converted.wav'; source.write_bytes(b'converted bytes')
        old = file_cache.FileCache(self.old / 'asset-pool-v1', 'sound', {'ffmpeg': 1})
        key = old.key('a' * 64, {'rate': 11025})
        self.assertTrue(old.store(key, source, {'frames': 7}))
        before = listing(self.old)
        with patch.dict(os.environ, {file_cache.FALLBACK_ENV: str(self.old)}):
            new = file_cache.FileCache(self.new / 'asset-pool-v1', 'sound', {'ffmpeg': 1})
            target = self.tmp / 'out' / 'x.wav'
            self.assertEqual(new.fetch(key, target), {'frames': 7})
            self.assertEqual(target.read_bytes(), b'converted bytes')
            self.assertEqual(new.fallback_hits, 1)
        self.assertEqual(listing(self.old), before)                 # read-only
        alone = file_cache.FileCache(self.new / 'asset-pool-v1', 'sound', {'ffmpeg': 1})
        self.assertEqual(alone.fetch(key, self.tmp / 'again.wav'), {'frames': 7})   # pooled here now

    def test_no_fallback_without_the_variable_or_for_the_same_folder(self):
        self.assertIsNone(file_cache.fallback_root(self.new / 'asset-pool-v1'))
        with patch.dict(os.environ, {file_cache.FALLBACK_ENV: str(self.old)}):
            self.assertIsNone(file_cache.fallback_root(self.old / 'asset-pool-v1'))
            self.assertIsNone(file_cache.fallback_root(self.new / 'missing-namespace'))

    def test_pass_cache_reads_the_other_workspace(self):
        old = pass_cache.PassCache('stair-walk', {'m': 1}, 'src', self.old / 'image-passes')
        old.store('f' * 64, {'rows': [1, 2]}, b'output')
        before = listing(self.old)
        with patch.dict(os.environ, {file_cache.FALLBACK_ENV: str(self.old)}):
            new = pass_cache.PassCache('stair-walk', {'m': 1}, 'src', self.new / 'image-passes')
            self.assertEqual(new.load('f' * 64), ({'rows': [1, 2]}, b'output'))
        self.assertEqual(listing(self.old), before)
        self.assertEqual(pass_cache.PassCache('stair-walk', {'m': 1}, 'src', self.new / 'image-passes').load('f' * 64),
                         ({'rows': [1, 2]}, b'output'))

    def test_builder_points_at_the_reuse_runs_workspace(self):
        import build
        run = self.old.parent / 'build' / 'rc1c'; run.mkdir(parents=True)
        self.assertEqual(build.reuse_cache_fallback(run, self.new.parent), self.old.resolve())
        self.assertIsNone(build.reuse_cache_fallback(run, self.old.parent))      # its own workspace
        self.assertIsNone(build.reuse_cache_fallback(None, self.new.parent))

    def test_the_variable_never_enters_a_stage_fingerprint(self):
        import build_cache
        self.assertIn(file_cache.FALLBACK_ENV, build_cache.IGNORED_ENV)


if __name__ == '__main__':
    unittest.main()
