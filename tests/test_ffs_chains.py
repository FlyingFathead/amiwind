# SPDX-License-Identifier: GPL-3.0-only
"""The directory hash chains the image step writes (tools/ffs_chains.py, IMAGE-LOADS-SLOWER-66) and the buffers it gives
every partition (BUILD-HDF-BUFFERS-32): a lookup of a file in the sound folder must fit the buffers, also when the
folder shares its chain with many loose files of its parent; the old order (the writer's, every folder at the tail of
its chain) fails that check."""
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]
import ffs_chains as fc  # noqa: E402

TOOLS = Path(sys.executable).parent
XDFTOOL = shutil.which('xdftool') or (TOOLS / 'xdftool' if (TOOLS / 'xdftool').is_file() else None)
RDBTOOL = shutil.which('rdbtool') or (TOOLS / 'rdbtool' if (TOOLS / 'rdbtool').is_file() else None)
AMITOOLS = importlib.util.find_spec('amitools') is not None
SOUND = 'id1/sound/fx/door.wav'


def ffs_hash(name):
    """The chain of NAME in a classic FFS directory (DOS1, no international mode)."""
    value = len(name)
    for char in name.upper().encode('latin-1'):
        value = (value * 13 + char) & 0x7FF
    return value % fc.HASH_SLOTS


def tree(entries):
    """A tree as read_tree gives it, from [(block, path, dir, parent, slot)] in written chain order (head first)."""
    out = dict(blocks=1000, root=500, dirs={500: dict(path='', chains={})}, entries={})
    for block, path, folder, parent, slot in entries:
        out['entries'][block] = dict(name=path.rsplit('/', 1)[-1], path=path, dir=folder, parent=parent, slot=slot,
                                     next=0)
        if folder:
            out['dirs'][block] = dict(path=path, chains={})
        out['dirs'][parent]['chains'].setdefault(slot, []).append(block)
    return out


class OrderTests(unittest.TestCase):
    def test_busiest_first_keeps_the_written_order_among_equals(self):
        t = tree([(1, 'id1', True, 500, 0),
                  (10, 'id1/b.cfg', False, 1, 5), (11, 'id1/empty', True, 1, 5), (12, 'id1/sound', True, 1, 5),
                  (13, 'id1/a.cfg', False, 1, 5), (14, 'id1/progs', True, 1, 5),
                  (20, 'id1/sound/x.wav', False, 12, 1), (21, 'id1/sound/y.wav', False, 12, 2),
                  (30, 'id1/progs/m.mdl', False, 14, 1)])
        chains = fc.ordered_chains(t, 'busiest-first')
        # sound (2 files) first, then progs and the two files (1 each, in their written order), the empty folder last
        self.assertEqual(chains[1][5], [12, 10, 13, 14, 11])
        self.assertEqual(fc.ordered_chains(t, 'as-written')[1][5], [10, 11, 12, 13, 14])
        costs = fc.lookup_blocks(t, chains)
        self.assertEqual(costs['id1/sound/x.wav'], 1 + 1 + 1 + 1)
        self.assertEqual(fc.lookup_blocks(t, fc.ordered_chains(t, 'as-written'))['id1/sound/x.wav'], 1 + 1 + 3 + 1)

    def test_buffers_fit_the_longest_lookup(self):
        self.assertEqual(fc.partition_buffers(0), fc.BUFFERS_FLOOR)
        self.assertEqual(fc.partition_buffers(20), fc.BUFFERS_FLOOR)
        self.assertEqual(fc.partition_buffers(21), 40)
        self.assertEqual(fc.partition_buffers(140), 150)
        self.assertEqual(fc.partition_buffers(10 ** 6), fc.BUFFERS_CAP)

    def test_the_order_comes_from_the_environment_or_the_default(self):
        with patch.dict(os.environ, {fc.ORDER_ENV: ''}):
            self.assertEqual(fc.chain_order(), 'busiest-first')
        with patch.dict(os.environ, {fc.ORDER_ENV: 'as-written'}):
            self.assertEqual(fc.chain_order(), 'as-written')
            self.assertEqual(fc.chain_order('busiest-first'), 'busiest-first')
        with self.assertRaisesRegex(ValueError, 'chain order'):
            fc.chain_order('alphabetical')


@unittest.skipUnless(AMITOOLS and XDFTOOL, 'needs amitools (xdftool)')
class WrittenChainTests(unittest.TestCase):
    def boot(self, root):
        """A boot payload whose id1/sound shares its chain with 40 loose files of id1 (written after it)."""
        boot = root / 'boot'
        files = {SOUND: b'RIFF' * 300, 'id1/sound/fx/step.wav': b'W' * 700, 'id1/progs/m.mdl': b'M' * 2000,
                 'id1/default.cfg': b'bind x y\n', 's/startup-sequence': b'echo\n'}
        slot, n = ffs_hash('sound'), 0
        while sum(1 for p in files if p.count('/') == 1 and p.startswith('id1/')) < 41:
            name = 'x%04d.dat' % n
            if ffs_hash(name) == slot:
                files['id1/' + name] = bytes([n % 256]) * (100 + n)
            n += 1
        for rel, data in files.items():
            (boot / rel).parent.mkdir(parents=True, exist_ok=True)
            (boot / rel).write_bytes(data)
        return boot, files

    def write(self, root, order=None):
        import world_volumes as W
        boot, files = self.boot(root)
        part = root / ('p-%s.hdf' % (order or 'default'))
        part.parent.mkdir(parents=True, exist_ok=True)
        with patch.dict(os.environ, {fc.ORDER_ENV: order or ''}), patch('builtins.print'):
            W.write_boot_partition(XDFTOOL, part, boot, 4)
        return part, files

    def assertSoundLookupFits(self, part):
        t = fc.read_tree(part)
        cost = fc.lookup_blocks(t, fc.ordered_chains(t, 'as-written'))[SOUND]
        self.assertLessEqual(cost, fc.BUFFERS_FLOOR, 'a lookup of %s reads %d header blocks, more than the %d buffers'
                             % (SOUND, cost, fc.BUFFERS_FLOOR))
        return cost

    def test_a_sound_lookup_fits_the_buffers(self):
        with tempfile.TemporaryDirectory() as tmp:
            part, _ = self.write(Path(tmp))
            self.assertEqual(self.assertSoundLookupFits(part), 1 + 1 + 1 + 1 + 1)   # root, id1, sound, fx, door.wav
            old, _ = self.write(Path(tmp) / 'old', 'as-written')
            # the old order: sound behind the 40 loose files of id1 in its chain; the check above fails on it
            with self.assertRaises(AssertionError):
                self.assertSoundLookupFits(old)

    def test_the_relink_moves_no_block_and_changes_no_file(self):
        from amitools.fs.ADFSVolume import ADFSVolume
        from amitools.fs.FSString import FSString
        from amitools.fs.blkdev.BlkDevFactory import BlkDevFactory
        from amiga_fs import check_image

        def blocks(part):
            device = BlkDevFactory().open(str(part), read_only=True)
            try:
                volume = ADFSVolume(device)
                volume.open()
                return {rel: (volume.get_file_path_name(FSString(rel)).get_block_nums(),
                              hashlib.sha256(volume.read_file(FSString(rel))).hexdigest()) for rel in files}
            finally:
                device.close()

        with tempfile.TemporaryDirectory() as tmp:
            old, files = self.write(Path(tmp), 'as-written')
            new = Path(tmp) / 'relinked.hdf'
            shutil.copyfile(old, new)
            receipt = fc.order_partition(new)
            self.assertGreater(receipt['chains_reordered'], 0)
            self.assertLess(receipt['after']['longest'], receipt['before']['longest'])
            self.assertEqual(blocks(new), blocks(old))
            for rel, data in files.items():
                self.assertEqual(blocks(new)[rel][1], hashlib.sha256(data).hexdigest(), rel)
            self.assertFalse(check_image(new)['changed'])   # the legacy root check passes as written
            # only header blocks differ, exactly the ones the receipt rewrote
            a, b = old.read_bytes(), new.read_bytes()
            changed = [k // 512 for k in range(0, len(a), 512) if a[k:k + 512] != b[k:k + 512]]
            t = fc.read_tree(new)
            self.assertEqual(len(changed), receipt['blocks_rewritten'])
            self.assertTrue(set(changed) <= set(t['entries']) | {t['root']})
            # a second pass has nothing to do
            again = fc.order_partition(new)
            self.assertEqual((again['chains_reordered'], again['blocks_rewritten']), (0, 0))

    @unittest.skipUnless(RDBTOOL, 'needs rdbtool')
    def test_every_partition_gets_the_buffers_of_its_longest_lookup(self):
        import world_volumes as W
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            part, files = self.write(root)
            boot_files = [dict(path=rel, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
                          for rel, data in sorted(files.items())]
            mib = part.stat().st_size // W.MIB
            plans = [dict(file='drive.hdf', mib=mib,
                          members=[dict(partition='DH0', volume='AMIWIND', bytes=part.stat().st_size)])]
            out = root / 'out'
            out.mkdir()
            with patch('builtins.print'):
                layout, drives, _ = W.assemble_drives(RDBTOOL, plans, out, part, boot_files)
            want = fc.buffer_plan(part)
            # the 40 loose files of id1 share one chain: its last entry is the longest lookup
            self.assertGreater(want['longest'], fc.BUFFERS_FLOOR)
            self.assertEqual(want['buffers'], fc.partition_buffers(want['longest']))
            self.assertEqual(layout[0]['buffers'], want['buffers'])   # read back from the partition table
            self.assertEqual(layout[0]['lookup_blocks']['longest'], want['longest'])
            self.assertEqual(layout[0]['lookup_blocks']['fit'], len(files))
            # the buffers before (an A/B build): every partition gets the number given
            with patch.dict(os.environ, {fc.BUFFERS_ENV: '30'}):
                (out / 'drive.hdf').unlink()
                with patch('builtins.print'):
                    layout, _, _ = W.assemble_drives(RDBTOOL, plans, out, part, boot_files)
            self.assertEqual((layout[0]['buffers'], layout[0]['lookup_blocks']['sized']), (30, fc.BUFFERS_ENV))
            with patch.dict(os.environ, {fc.BUFFERS_ENV: 'lots'}), self.assertRaisesRegex(ValueError, fc.BUFFERS_ENV):
                fc.buffer_plan(part)


if __name__ == '__main__':
    unittest.main()
