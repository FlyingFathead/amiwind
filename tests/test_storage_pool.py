"""Shared storage pool: store once by SHA-256, read-only hard links, verified placement, duplicate scan."""
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
import unittest.mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import storage_pool  # noqa: E402

LINKS = os.name == 'posix' and hasattr(os, 'geteuid') and os.geteuid() != 0


class StoragePoolTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.pool = self.root / 'cache' / 'asset-pool-v1'
        self.payload = bytes(range(256)) * 1024  # 256 KiB, above the pooling limit

    def tearDown(self):
        for here, directories, names in os.walk(self.root):
            for name in directories + names:
                os.chmod(Path(here) / name, 0o755)
        self.temp.cleanup()

    def write(self, relative, data=None):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.payload if data is None else data)
        return path

    def test_object_layout_is_the_asset_pool_layout(self):
        import file_cache
        digest = 'ab' + '0' * 62
        cache = file_cache.FileCache(self.pool, 'media', {})
        self.assertEqual(storage_pool.object_path(self.pool, digest), cache.object_path(digest))

    def test_kinds(self):
        self.assertEqual(storage_pool.kind_of('v/ws8/build/rc1/image/AmiWind.hdf'), 'image')
        self.assertEqual(storage_pool.kind_of('v/pkg/AmiWind.zip'), 'package')
        self.assertEqual(storage_pool.kind_of('v/ws8/cache/asset-pool-v1/objects/ab/x'), 'cache')
        self.assertEqual(storage_pool.kind_of('v/ws8/build/rc1/chim/world.pak'), 'stage-output')

    @unittest.skipUnless(LINKS, 'hard links need a non-root POSIX user')
    def test_put_stores_once_and_links_read_only(self):
        first = self.write('ws/build/a/image/game.hdf')
        second = self.write('ws/build/b/image/game.hdf')
        digest = storage_pool.sha256_file(first)
        outcome, got, saved = storage_pool.put(self.pool, first)
        self.assertEqual((outcome, got, saved), ('linked', digest, 0))  # first copy: moved by a link, nothing freed
        outcome, _, saved = storage_pool.put(self.pool, second)
        self.assertEqual((outcome, saved), ('linked', len(self.payload)))
        blob = storage_pool.object_path(self.pool, digest)
        self.assertEqual(os.stat(first).st_ino, os.stat(blob).st_ino)
        self.assertEqual(os.stat(second).st_ino, os.stat(blob).st_ino)
        self.assertEqual(os.stat(blob).st_nlink, 3)
        self.assertEqual(first.read_bytes(), self.payload)
        with self.assertRaises(PermissionError):
            first.open('r+b')
        self.assertEqual(storage_pool.put(self.pool, first)[0], 'already')
        self.assertFalse(list(self.root.rglob('*' + storage_pool.TEMPORARY)))

    @unittest.skipUnless(LINKS, 'hard links need a non-root POSIX user')
    def test_writers_replace_never_edit_shared_files(self):
        first = self.write('ws/build/a/x.bin')
        second = self.write('ws/build/b/x.bin')
        storage_pool.put(self.pool, first)
        storage_pool.put(self.pool, second)
        # A later build replaces its own file (temporary + rename): the pooled object and the other run keep their bytes.
        temporary = second.with_name('x.bin.new')
        temporary.write_bytes(b'changed')
        os.replace(temporary, second)
        self.assertEqual(first.read_bytes(), self.payload)
        digest = storage_pool.sha256_file(first)
        self.assertEqual(storage_pool.object_path(self.pool, digest).read_bytes(), self.payload)

    @unittest.skipUnless(LINKS, 'hard links need a non-root POSIX user')
    def test_place_verifies_and_never_links_a_damaged_object(self):
        source = self.write('ws/build/a/x.bin')
        _, digest, _ = storage_pool.put(self.pool, source)
        target = self.root / 'ws/build/c/x.bin'
        self.assertTrue(storage_pool.place(self.pool, digest, target))
        self.assertEqual(os.stat(target).st_ino, os.stat(source).st_ino)
        copy = self.root / 'play/x.bin'
        self.assertTrue(storage_pool.place(self.pool, digest, copy, link=False, mode=0o644))
        self.assertNotEqual(os.stat(copy).st_ino, os.stat(source).st_ino)  # a played copy is a real copy
        copy.write_bytes(b'played')
        self.assertEqual(source.read_bytes(), self.payload)
        self.assertFalse(storage_pool.place(self.pool, 'f' * 64, self.root / 'missing.bin'))
        # Damage the object: it is never linked again; ensure() replaces it from a good copy.
        blob = storage_pool.object_path(self.pool, digest)
        good = self.write('elsewhere/x.bin')
        os.chmod(blob, 0o644)
        with open(blob, 'r+b') as handle:
            handle.write(b'X')
        self.assertFalse(storage_pool.place(self.pool, digest, self.root / 'ws/build/d/x.bin'))
        fixed = storage_pool.ensure(self.pool, good, digest)
        self.assertEqual(storage_pool.sha256_file(fixed), digest)
        self.assertTrue(storage_pool.place(self.pool, digest, self.root / 'ws/build/d/x.bin'))

    @unittest.skipUnless(LINKS, 'hard links need a non-root POSIX user')
    def test_adopt_is_a_dry_run_by_default(self):
        first = self.write('ws/build/a/x.bin')
        self.write('ws/build/b/x.bin')
        self.write('ws/build/b/small.txt', b'small')
        summary = storage_pool.adopt(self.pool, [self.root / 'ws/build'], log=lambda line: None)
        self.assertFalse(summary['apply'])
        self.assertEqual(summary['files'], 2)
        self.assertEqual(summary['duplicate_bytes'], len(self.payload))
        self.assertFalse(self.pool.exists())
        self.assertEqual(os.stat(first).st_nlink, 1)
        summary = storage_pool.adopt(self.pool, [self.root / 'ws/build'], apply=True, log=lambda line: None)
        self.assertEqual((summary['linked'], summary['saved_bytes']), (2, len(self.payload)))
        self.assertEqual(os.stat(first).st_nlink, 3)
        self.assertEqual(storage_pool.stats(self.pool)['linked_objects'], 1)

    def test_put_never_adds_a_copy_when_links_cannot_be_protected(self):
        path = self.write('ws/build/a/x.bin')
        original = storage_pool._can_protect
        storage_pool._can_protect = lambda: False
        try:
            self.assertEqual(storage_pool.put(self.pool, path)[0], 'skipped')
        finally:
            storage_pool._can_protect = original
        self.assertFalse(self.pool.exists())

    def test_scan_counts_duplicates_by_content_and_hard_links_once(self):
        self.write('v/ws/build/a/image/game.hdf')
        self.write('v/ws/build/b/image/game.hdf')
        self.write('v/pkg/game.zip', self.payload[::-1])
        self.write('v/pkg2/game.zip', self.payload[::-1])
        self.write('v/ws/build/a/same-size.bin', b'\1' * len(self.payload))
        linked = self.root / 'v/ws/build/c/image/game.hdf'
        linked.parent.mkdir(parents=True)
        try:
            os.link(self.root / 'v/ws/build/a/image/game.hdf', linked)
        except OSError:
            linked = None
        report = storage_pool.scan([self.root / 'v'], min_size=1024, log=lambda line: None)
        self.assertEqual(report['by_kind']['image']['bytes'], len(self.payload))
        self.assertEqual(report['by_kind']['package']['bytes'], len(self.payload))
        self.assertEqual(report['duplicate_bytes'], 2 * len(self.payload))
        if linked:
            self.assertEqual(report['totals']['hardlinked_bytes'], len(self.payload))
        digests = {row['sha256'] for row in report['groups']}
        self.assertIn(storage_pool.sha256_file(self.root / 'v/pkg/game.zip'), digests)


class BuilderPoolTest(unittest.TestCase):
    setUp = StoragePoolTest.setUp
    tearDown = StoragePoolTest.tearDown
    write = StoragePoolTest.write

    def args(self, setting='auto'):
        import argparse
        return argparse.Namespace(workspace=self.root / 'ws', storage_pool=setting, dry_run=False)

    def test_setting(self):
        import build
        self.assertTrue(build.storage_pool_enabled(self.args(), '0.0.34-dev1'))
        self.assertFalse(build.storage_pool_enabled(self.args(), '0.0.34-rc1'))
        self.assertFalse(build.storage_pool_enabled(self.args(), '0.0.34'))
        self.assertTrue(build.storage_pool_enabled(self.args('on'), '0.0.34'))
        self.assertFalse(build.storage_pool_enabled(self.args('off'), '0.0.34-dev1'))
        self.assertIn('--storage-pool', build.parser().format_help())
        self.assertEqual(build.parser().parse_args([]).storage_pool, 'auto')  # store once: on by default

    @unittest.skipUnless(LINKS, 'hard links need a non-root POSIX user')
    def test_passed_build_is_pooled_except_bookkeeping_and_a_played_image(self):
        import build
        run = self.root / 'ws/build/r1'
        image = self.write('ws/build/r1/image/game.hdf')
        world = self.write('ws/build/r1/chim/world.pak', self.payload[::-1])
        log = self.write('ws/build/r1/logs/01-chim.log')
        (run / 'profile').mkdir()
        with unittest.mock.patch.object(build, 'storage_pool_enabled', return_value=True), \
                contextlib.redirect_stdout(io.StringIO()):
            summary = build.pool_outputs(self.args('on'), run, played=True)
        self.assertEqual(summary['linked'], 1)
        self.assertEqual(os.stat(world).st_nlink, 2)
        self.assertEqual(os.stat(image).st_nlink, 1)  # the emulator played it: never shared
        self.assertEqual(os.stat(log).st_nlink, 1)
        self.assertTrue((run / 'profile' / 'storage-pool.json').is_file())


if __name__ == '__main__':
    unittest.main()
