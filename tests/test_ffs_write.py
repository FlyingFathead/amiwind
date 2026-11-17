# SPDX-License-Identifier: GPL-3.0-only
"""The partition writer of the image step (tools/ffs_write.py, BUILD-IMAGE-LAYOUT-WRITE-SLOWER-66): the direct writer
makes the same partition, byte for byte, as the xdftool command queue it replaces (the method before), with the clock
held still (every write of either method dates its blocks with the moment it ran); also when the queue is cut into many
small batches (each opens the image again), when the allocation wraps past the end of the partition, and for files
that need extension blocks."""
import hashlib
import importlib.util
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
import ffs_write  # noqa: E402

TOOLS = Path(sys.executable).parent
XDFTOOL = shutil.which('xdftool') or (TOOLS / 'xdftool' if (TOOLS / 'xdftool').is_file() else None)
AMITOOLS = importlib.util.find_spec('amitools') is not None
_LOCALTIME = time.localtime
STILL = time.mktime((2026, 11, 16, 12, 0, 0, 0, 0, -1))


def still_clock(*args):
    """time.localtime with the clock held at STILL when asked for now (amitools dates every block it writes)."""
    return _LOCALTIME(STILL) if not args or args[0] is None else _LOCALTIME(*args)


def in_process(limit=None):
    """An xdftool runner for write_volume: amitools' own xdftool main in this process (the same code the command
    runs), on the queue cut by build_windows_xdftool.batches (LIMIT bytes of arguments a batch, small = many)."""
    from amitools.tools.xdftool import main
    from build_windows_xdftool import MAX_POSIX_BYTES, batches, posix_bytes

    def run(command):
        for batch in batches(command, limit or MAX_POSIX_BYTES, posix_bytes):
            code = main([str(part) for part in batch[1:]])
            if code:
                raise RuntimeError('xdftool exit %s' % code)
    return run


def payload(root, files=220, big=True):
    """A tree like a small boot payload: nested folders, a folder past its 72 hash chains, mixed-case names, files of
    0, 1, 512 and 513 bytes, one that needs an extension block (more than 72 data blocks) and one with several."""
    tree = {'S/startup-sequence': b'echo boot\n', 'AmiWind': bytes(range(256)) * 40, 'id1/default.cfg': b'',
            'id1/One.cfg': b'1', 'id1/progs/block.mdl': b'B' * 512, 'id1/progs/blockplus.mdl': b'P' * 513,
            'id1/sound/fx/door.wav': b'RIFF' * 300, 'id1/maps/start.bsp': b'\x1d' * 9000}
    if big:
        tree['id1/progs/ext.mdl'] = bytes((i * 7) % 251 for i in range(72 * 512 + 1))
        tree['id1/progs/long.mdl'] = bytes((i * 13) % 253 for i in range(300 * 512 + 77))
    for n in range(files):
        tree['id1/progs/a_%04x.mdl' % (n * 37)] = bytes([n % 256]) * (64 + 97 * n % 3000)
    for n in range(40):
        tree['id1/sound/pool/S%03d.wav' % n] = bytes([255 - n]) * (n * 31 + 5)
    for rel, data in tree.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(data)
    return tree


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@unittest.skipUnless(AMITOOLS, 'needs amitools')
class DirectWriterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def both(self, boot, mib, volume='AMIWIND', limit=4096, threads=3, chunk=None, is_boot=True):
        """The partition written by the queue (in batches of LIMIT bytes) and directly, with the clock held still."""
        ops = ffs_write.tree_ops(boot)
        out = {}
        with patch('time.localtime', side_effect=still_clock), patch('builtins.print'), \
                patch.object(ffs_write, 'DATA_CHUNK_BYTES', chunk or ffs_write.DATA_CHUNK_BYTES):
            for method in ffs_write.METHODS:
                part = self.tmp / ('%s.hdf' % method)
                receipt = ffs_write.write_volume('xdftool', part, mib, volume, ops, boot=is_boot, method=method,
                                                 threads=threads, run=in_process(limit if method == 'xdftool' else None))
                out[method] = part, receipt
        return out

    def test_direct_writes_the_same_partition_as_the_queue(self):
        boot = self.tmp / 'boot'
        payload(boot)
        out = self.both(boot, 4, chunk=4096)
        (direct, receipt), (queue, _) = out['direct'], out['xdftool']
        self.assertEqual(digest(direct), digest(queue))
        self.assertEqual(receipt['method'], 'direct')
        self.assertEqual(receipt['files'], sum(1 for p in boot.rglob('*') if p.is_file()))
        self.assertEqual(receipt['bytes'], sum(p.stat().st_size for p in boot.rglob('*') if p.is_file()))
        self.assertGreater(receipt['threads'], 1)
        # the comparison sees the layout: the same files written in another order make another partition
        ops = ffs_write.tree_ops(boot)
        folders = [op for op in ops if op[0] == 'dir']
        with patch('time.localtime', side_effect=still_clock), patch('builtins.print'):
            other = self.tmp / 'other.hdf'
            ffs_write.write_volume('xdftool', other, 4, 'AMIWIND', folders + [op for op in ops if op[0] == 'file'][::-1],
                                   boot=True, run=in_process())
        self.assertNotEqual(digest(other), digest(direct))
        # and every file reads back as it was (amitools' own reader)
        from amitools.fs.ADFSVolume import ADFSVolume
        from amitools.fs.FSString import FSString
        from amitools.fs.blkdev.BlkDevFactory import BlkDevFactory
        device = BlkDevFactory().open(str(direct), read_only=True)
        try:
            volume = ADFSVolume(device)
            volume.open()
            for path in (p for p in boot.rglob('*') if p.is_file()):
                rel = path.relative_to(boot).as_posix()
                self.assertEqual(bytes(volume.read_file(FSString(rel))), path.read_bytes(), rel)
        finally:
            device.close()

    def test_the_same_when_the_allocation_wraps_past_the_end(self):
        # 1 MiB for about 0.7 MiB of blocks: the root block sits in the middle, the files fill the upper half and go
        # on from the start, so the data runs of a file split where the allocation wraps
        boot = self.tmp / 'boot'
        payload(boot)
        out = self.both(boot, 1, volume='AW_WORLD0', limit=2048, threads=2, chunk=1024, is_boot=False)
        self.assertEqual(digest(out['direct'][0]), digest(out['xdftool'][0]))
        with patch('time.localtime', side_effect=still_clock), patch('builtins.print'):
            part = self.tmp / 'plan.hdf'
            ffs_write.write_volume('xdftool', part, 1, 'AW_WORLD0', [], run=in_process(), method='xdftool')
            plan = ffs_write._create_entries(part, ffs_write.tree_ops(boot))
        self.assertTrue(any(len(ffs_write._runs(blocks)) > 1 for _, _, blocks in plan),
                        'no file wraps; the test partition must be fuller')

    def test_a_file_into_a_folder_not_made_before_it_is_refused(self):
        source = self.tmp / 'a.bin'
        source.write_bytes(b'a')
        with patch('builtins.print'):
            for ops, words in (([('file', source, 'id1/a.bin')], 'not made before it'),
                               ([('dir', 'id1'), ('file', source, 'ID1')], 'is a folder already')):
                part = self.tmp / ('refused-%d.hdf' % len(ops))
                with self.assertRaisesRegex(ValueError, words):
                    ffs_write.write_volume('xdftool', part, 1, 'X', ops, run=in_process())

    def test_a_file_that_changes_while_it_is_written_is_refused(self):
        source = self.tmp / 'a.bin'
        source.write_bytes(b'a' * 1000)
        part = self.tmp / 'changed.hdf'
        with patch('builtins.print'):
            ffs_write.write_volume('xdftool', part, 1, 'X', [], run=in_process(), method='xdftool')
            plan = ffs_write._create_entries(part, [('file', source, 'a.bin')])
        source.write_bytes(b'a' * 1001)
        with self.assertRaisesRegex(ValueError, 'when its blocks were allocated'):
            ffs_write._write_data(part, plan, 1)


class MethodTests(unittest.TestCase):
    def test_the_method_comes_from_the_environment_or_the_default(self):
        with patch.dict(os.environ, {ffs_write.METHOD_ENV: ''}):
            self.assertEqual(ffs_write.writer_method(), 'direct')
        with patch.dict(os.environ, {ffs_write.METHOD_ENV: 'xdftool'}):
            self.assertEqual(ffs_write.writer_method(), 'xdftool')
            self.assertEqual(ffs_write.writer_method('direct'), 'direct')
        with self.assertRaisesRegex(ValueError, ffs_write.METHOD_ENV):
            ffs_write.writer_method('fast')

    def test_the_method_before_runs_the_whole_queue(self):
        ran = []
        ops = [('dir', 'id1'), ('file', '/src/a b.bin', 'id1/a b.bin')]
        receipt = ffs_write.write_volume('xdftool', 'p.hdf', 128, 'AMIWIND', ops, boot=True, method='xdftool',
                                         run=ran.append)
        self.assertEqual(ran, [['xdftool', 'p.hdf', 'create', 'size=128Mi', '+', 'format', 'AMIWIND', 'ffs',
                                '+', 'boot', 'install', '+', 'makedir', 'id1', '+', 'write', '/src/a b.bin',
                                'id1/a b.bin']])
        self.assertEqual((receipt['method'], receipt['folders'], receipt['files']), ('xdftool', 1, 1))

    def test_runs_of_consecutive_blocks(self):
        self.assertEqual(ffs_write._runs([]), [])
        self.assertEqual(ffs_write._runs([5, 6, 7, 9, 10, 2]), [[5, 3], [9, 2], [2, 1]])

    def test_the_image_writers_use_it(self):
        tools = ROOT / 'tools'
        volumes = (tools / 'world_volumes.py').read_text(encoding='utf-8')
        boot = volumes[volumes.index('def write_boot_partition('):]
        self.assertIn('ffs_write.write_volume(', boot[:boot.index('\ndef ')])
        batch = volumes[volumes.index('def _pack_batch('):]
        self.assertIn('ffs_write.write_volume(', batch[:batch.index('\ndef ')])
        chim = (tools / 'chim' / 'disk.py').read_text(encoding='utf-8')
        pack = chim[chim.index('def pack_partition('):]
        self.assertIn('ffs_write.write_volume(', pack[:pack.index('\ndef ')])
        # the xdftool commands stay bounded (tools/build_windows_xdftool.py)
        writer = (tools / 'ffs_write.py').read_text(encoding='utf-8')
        self.assertIn('from build_windows_xdftool import run_any as run', writer)


if __name__ == '__main__':
    unittest.main()
