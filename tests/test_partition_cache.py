# SPDX-License-Identifier: GPL-3.0-only
"""Finished partitions taken from an earlier build (tools/partition_cache.py, BUILD-IMAGE-LAYOUT-WRITE-SLOWER-66): the
same inputs give the stored partition, byte for byte, without writing it again (the boot partition, and the CHIM world
volume of the compact layout); one changed file, or a changed writer setting, gives a fresh write; a damaged entry is a
miss; the cache of the --reuse-from workspace is only read; with the image pass cache off nothing is hashed or kept;
a partition name keeps its KEEP most recently used entries."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]    # src before tools (TEST-WORKER-SYSPATH-32)
if str(ROOT / 'tests') not in sys.path:
    sys.path.append(str(ROOT / 'tests'))                    # the CHIM world and region fixtures of two test modules
import ffs_write  # noqa: E402
import partition_cache as pc  # noqa: E402
import world_volumes as W  # noqa: E402

TOOLS = Path(sys.executable).parent
XDFTOOL = shutil.which('xdftool') or (TOOLS / 'xdftool' if (TOOLS / 'xdftool').is_file() else None)
AMITOOLS = importlib.util.find_spec('amitools') is not None


def boot_tree(root):
    files = {'S/startup-sequence': b'echo\n', 'AmiWind': b'E' * 7000, 'id1/default.cfg': b'bind x y\n',
             'id1/progs/m.mdl': b'M' * 2000, 'id1/sound/fx/door.wav': b'RIFF' * 300}
    for n in range(90):
        files['id1/progs/a%03d.mdl' % n] = bytes([n]) * (100 + 13 * n)
    for rel, data in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(data)
    return root


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@unittest.skipUnless(AMITOOLS and XDFTOOL, 'needs amitools (xdftool)')
class PartitionCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cache = self.tmp / 'cache' / 'image-passes'
        self.boot = boot_tree(self.tmp / 'boot')

    def write(self, name, cache=None, fallback='', extra=None):
        part = self.tmp / name
        env = {'AMIWIND_PASS_CACHE': str(cache or self.cache), 'AMIWIND_CACHE_FALLBACK': fallback}
        env.update(extra or {})
        with patch.dict(os.environ, env), patch('builtins.print'):
            return part, W.write_boot_partition(XDFTOOL, part, self.boot, 2)

    def entries(self, cache=None):
        return sorted((Path(cache or self.cache) / pc.NAME / 'DH0').glob('*.json'))

    def test_unchanged_inputs_take_the_stored_partition(self):
        first, result = self.write('a.hdf')
        self.assertEqual(len(self.entries()), 1)
        with patch.object(ffs_write, 'write_volume', side_effect=AssertionError('written again')):
            second, again = self.write('b.hdf')
        self.assertEqual(sha(second), sha(first))
        self.assertEqual(again, result)
        self.assertEqual(len(self.entries()), 1)

    def test_one_changed_file_is_written_again(self):
        first, _ = self.write('a.hdf')
        (self.boot / 'id1/progs/a007.mdl').write_bytes(b'X' * (100 + 13 * 7))      # same size, other bytes
        with patch.object(ffs_write, 'write_volume', wraps=ffs_write.write_volume) as writer:
            second, _ = self.write('b.hdf')
        self.assertEqual(writer.call_count, 1)
        self.assertNotEqual(sha(second), sha(first))
        self.assertEqual(len(self.entries()), 2)

    def test_a_changed_writer_setting_is_another_key(self):
        self.write('a.hdf')
        with patch.object(ffs_write, 'write_volume', wraps=ffs_write.write_volume) as writer:
            self.write('b.hdf', extra={'AMIWIND_CHAIN_ORDER': 'as-written'})
        self.assertEqual(writer.call_count, 1)

    def test_a_damaged_entry_is_a_miss(self):
        self.write('a.hdf')
        blob = self.entries()[0].with_suffix('.hdf')
        with open(blob, 'r+b') as stream:
            stream.seek(4096)
            byte = stream.read(1)
            stream.seek(4096)
            stream.write(bytes([byte[0] ^ 0xFF]))
        with patch.object(ffs_write, 'write_volume', wraps=ffs_write.write_volume) as writer:
            second, _ = self.write('b.hdf')
        self.assertEqual(writer.call_count, 1)
        meta = json.loads(self.entries()[0].read_text(encoding='utf-8'))
        self.assertEqual(sha(second), meta['sha256'])          # stored again from the fresh write

    def test_the_reuse_from_cache_is_only_read(self):
        other = self.tmp / 'other' / 'image-passes'
        first, result = self.write('a.hdf', cache=other)
        before = {p.name: (p.stat().st_mtime_ns, sha(p)) for p in (other / pc.NAME / 'DH0').iterdir()}
        with patch.object(ffs_write, 'write_volume', side_effect=AssertionError('written again')):
            second, again = self.write('b.hdf', fallback=str(other))
        self.assertEqual((sha(second), again), (sha(first), result))
        self.assertEqual({p.name: (p.stat().st_mtime_ns, sha(p)) for p in (other / pc.NAME / 'DH0').iterdir()},
                         before)
        self.assertEqual(len(self.entries()), 1)                 # and kept in this workspace's cache

    def test_nothing_is_kept_with_the_cache_off(self):
        with patch.object(ffs_write, 'write_volume', wraps=ffs_write.write_volume) as writer, \
                patch.object(pc, 'inputs', side_effect=AssertionError('hashed')):
            self.write('a.hdf', cache='off')
            self.write('b.hdf', cache='off')
        self.assertEqual(writer.call_count, 2)
        self.assertFalse(self.cache.exists())

    def test_a_partition_name_keeps_its_most_recently_used_entries(self):
        base = self.tmp / 'prune'
        (base / 'DH0').mkdir(parents=True)
        for n, key in enumerate('abcd'):
            for suffix in ('.json', '.hdf'):
                path = base / 'DH0' / (key + suffix)
                path.write_text(key)
                os.utime(path, (1000 + n, 1000 + n))
        self.assertEqual(sorted(pc.prune(base, 'DH0', keep_key='a')), ['b', 'c'])
        self.assertEqual(sorted(p.name for p in (base / 'DH0').iterdir()), ['a.hdf', 'a.json', 'd.hdf', 'd.json'])


@unittest.skipUnless(AMITOOLS and XDFTOOL, 'needs amitools (xdftool)')
class CompactLayoutReuseTests(unittest.TestCase):
    def test_the_second_build_takes_both_partitions(self):
        import layout_plan as L
        from test_chim_format import fixture
        from test_layout_plan import awr
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            world = tmp / 'chimworld'
            fixture(world)
            cache = tmp / 'cache' / 'image-passes'
            outs = []
            for run, writer_patch in (('one', None), ('two', AssertionError('written again'))):
                boot = tmp / run / 'boot'
                for i in range(5):
                    path = boot / ('id1/progs/p%d.mdl' % i)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(bytes([i]) * (3000 + i))
                (boot / 'id1/world').mkdir(parents=True)
                (boot / 'id1/world/regions.awr').write_bytes(awr(6))
                (boot / 'id1/maps').mkdir(parents=True)
                for i in range(6):
                    (boot / ('id1/maps/vf%04d.chim' % i)).write_bytes(b'C' * (700 + i))
                maps = W.region_map_paths(boot / 'id1')
                rows = {p.relative_to(boot).as_posix(): p.stat().st_size for p in boot.rglob('*')
                        if p.is_file() and p not in set(maps)}
                plan = L.plan_compact(rows, [(p.relative_to(boot).as_posix(), p.stat().st_size) for p in maps],
                                      L.walk(world / 'chim'), headroom_mib=1)
                out = tmp / run / 'out'
                out.mkdir()
                env = {'AMIWIND_PASS_CACHE': str(cache), 'AMIWIND_CACHE_FALLBACK': ''}
                with patch.dict(os.environ, env), patch('builtins.print'), \
                        patch.object(ffs_write, 'write_volume',
                                     **({'side_effect': writer_patch} if writer_patch else
                                        {'wraps': ffs_write.write_volume})):
                    boot_check, worlds, _ = W.write_layout(plan, boot, out, XDFTOOL, out / 'partition.hdf',
                                                           world / 'chim', jobs=1, log=lambda line: None)
                outs.append((boot_check, worlds, [sha(out / 'partition.hdf')] + [sha(out / w['file']) for w in worlds]))
        self.assertEqual(outs[1], outs[0])
        self.assertEqual(len(outs[0][2]), 2)


if __name__ == '__main__':
    unittest.main()
