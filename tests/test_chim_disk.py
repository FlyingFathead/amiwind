# SPDX-License-Identifier: GPL-3.0-only
"""The CHIM world on the image: pack order, readback, the FFS disk-layout gate, the world volume."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from chim import format as F  # noqa: E402
from chim.disk import IMAGE_BASE, layout_gate, name_rules, pack_order, pack_partition  # noqa: E402
from test_chim_format import fixture  # noqa: E402

XDFTOOL = shutil.which('xdftool')


def xdf(part, *steps):
    command = [XDFTOOL, str(part), 'create', 'size=8Mi', '+', 'format', 'T', 'ffs']
    for step in steps:
        command += ['+', *step]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL)


@unittest.skipUnless(XDFTOOL, 'xdftool (amitools) not installed')
class ChimDiskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / 'w'
        cls.receipt, cls.source = fixture(cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_partition_written_in_pack_order_and_gated(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = pack_partition(self.out / 'chim', Path(tmp) / 'p.hdf', 'AW_WORLD3', 8, XDFTOOL, IMAGE_BASE)
        order = pack_order(self.out / 'chim')
        self.assertEqual([f['path'] for f in r['files']], [IMAGE_BASE + '/' + p for p in order])
        self.assertEqual(r['files'][0]['path'], 'id1/chim/world.cwi')
        self.assertEqual((r['volume'], r['readback']), ('AW_WORLD3', 'passed'))
        gate = r['layout']
        self.assertTrue(gate['ok'], gate['failures'])
        self.assertEqual(gate['files'], len(order))
        self.assertLessEqual(gate['longest_name_chars'], F.FFS_NAME_CHARS)
        self.assertLessEqual(gate['most_directory_entries'], F.FFS_MAX_DIRECTORY_ENTRIES)

    def test_written_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            part = Path(tmp) / 'p.hdf'
            part.write_bytes(b'')
            with self.assertRaisesRegex(ValueError, 'written once'):
                pack_partition(self.out / 'chim', part, 'AW_WORLD0', 8, XDFTOOL)

    def test_gate_refuses_files_out_of_pack_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / 'a.bin', Path(tmp) / 'b.bin'
            a.write_bytes(b'a' * 5000)
            b.write_bytes(b'b' * 5000)
            part = Path(tmp) / 'p.hdf'
            xdf(part, ('write', str(b), 'b'), ('write', str(a), 'a'))
            gate = layout_gate(part, ['a', 'b'])
            self.assertFalse(gate['ok'])
            self.assertIn('pack order', ' '.join(gate['failures']))
            self.assertTrue(layout_gate(part, ['b', 'a'])['ok'])

    def test_gate_refuses_a_file_split_around_another(self):
        with tempfile.TemporaryDirectory() as tmp:
            small, mid, big = Path(tmp) / 's', Path(tmp) / 'm', Path(tmp) / 'b'
            small.write_bytes(b's' * 3000)
            mid.write_bytes(b'm' * 3000)
            big.write_bytes(b'b' * 20000)
            part = Path(tmp) / 'p.hdf'
            # big fills the hole small left and continues after mid
            xdf(part, ('write', str(small), 's'), ('write', str(mid), 'm'), ('delete', 's'),
                ('write', str(big), 'b'))
            gate = layout_gate(part, ['m', 'b'])
            self.assertFalse(gate['ok'])
            self.assertIn('not whole', ' '.join(gate['failures']))
            self.assertGreaterEqual(gate['fragmented_files'], 1)

    def test_name_and_directory_rules(self):
        self.assertEqual(name_rules(['id1/chim/world.cwi']), [])
        self.assertTrue(name_rules(['id1/chim/' + 'x' * 31]))
        self.assertEqual(name_rules(['d/' + 'x' * 30]), [])
        crowded = ['d/f%03d' % i for i in range(F.FFS_MAX_DIRECTORY_ENTRIES + 1)]
        self.assertIn('directory d holds', ' '.join(name_rules(crowded)))
        self.assertEqual(name_rules(crowded[:-1]), [])

    def test_image_adds_the_world_as_the_next_world_volume(self):
        import build_aga
        from chim.validate import main as validate
        from chim.stats import main as stats
        with tempfile.TemporaryDirectory() as tmp:
            world = Path(tmp) / 'chim-world'
            shutil.copytree(self.out / 'chim', world / 'chim')
            (world / 'chim-source.json').write_text(json.dumps(self.source))
            # no town: no frame map (tests/test_chim_frame_map.py covers it)
            (world / 'chim-receipt.json').write_text(json.dumps(self.receipt))
            import contextlib
            import io
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(validate([str(world), '--json', str(world / 'chim-validate.json')]), 0)
                self.assertEqual(stats([str(world)]), 0)
            id1, out = Path(tmp) / 'boot/id1', Path(tmp) / 'out'
            out.mkdir()
            entry, record = build_aga.add_chim_volume(world, id1, out, 2, XDFTOOL, mib=8)
            self.assertEqual((id1 / 'world/volumes.awv').read_bytes(), b'AWV1\x03')
            self.assertEqual((entry['volume'], entry['partition']), ('AW_WORLD2', 'DW2'))
            self.assertTrue((out / entry['file']).is_file())
            self.assertEqual(entry['files'][0]['path'], 'id1/chim/world.cwi')
            self.assertEqual((record['builder'], record['chim_version'], record['world_format']),
                             ('chim', self.receipt['chim_version'], self.receipt['world_format']))
            self.assertTrue(record['layout_gate']['ok'])
            self.assertEqual((record['areas'], record['frame_maps']), ([], []))
            for name in ('chim-receipt.json', 'chim-validate.json', 'chim-stats.json'):
                self.assertTrue((out / name).is_file(), name)
            with self.assertRaisesRegex(ValueError, 'eight-volume'):
                build_aga.add_chim_volume(world, id1, out, 8, XDFTOOL, mib=8)
            report = json.loads((world / 'chim-validate.json').read_text())
            (world / 'chim-validate.json').write_text(json.dumps(dict(report, ok=False)))
            with self.assertRaisesRegex(ValueError, 'validation'):
                build_aga.add_chim_volume(world, id1, out, 3, XDFTOOL, mib=8)
            (world / 'chim-stats.json').unlink()
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                build_aga.add_chim_volume(world, id1, out, 3, XDFTOOL, mib=8)


if __name__ == '__main__':
    unittest.main()
