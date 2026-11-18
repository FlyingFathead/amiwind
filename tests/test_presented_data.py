# SPDX-License-Identifier: GPL-3.0-only
"""The presented data folder (tools/presented_data.py). Small synthetic masters: no game data."""
import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import presented_data as pd  # noqa: E402
import presented_exterior as pe  # noqa: E402
from mwad.esm import records, subrecords  # noqa: E402
from mwad.masters import master_bytes  # noqa: E402

CONFIG = {'first_block': [-12, -30], 'spacing': 4, 'max_block': 2}
THREE = ['Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm']


def sub(tag, data):
    if isinstance(data, str):
        data = data.encode('cp1252') + b'\0'
    return struct.pack('<4sI', tag.encode(), len(data)) + data


def rec(tag, *subs):
    payload = b''.join(subs)
    return struct.pack('<4sIII', tag.encode(), len(payload), 0, 0) + payload


def master(count, *parts, masters=()):
    head = sub('HEDR', struct.pack('<fI32s256sI', 1.3, 1, b'', b'', count))
    for name in masters:
        head += sub('MAST', name) + sub('DATA', struct.pack('<Q', 1))
    return rec('TES3', head) + b''.join(parts)


def ref(number, ident, pos):
    return (sub('FRMR', struct.pack('<I', number)) + sub('NAME', ident)
            + sub('DATA', struct.pack('<6f', *pos, 0, 0, 0)))


def exterior(x, y, *refs):
    return rec('CELL', sub('NAME', ''), sub('DATA', struct.pack('<Iii', 0, x, y)), *refs)


def interior(name, flags, *refs):
    return rec('CELL', sub('NAME', name), sub('DATA', struct.pack('<Iff', flags, 0.0, 0.0)), *refs)


class Folder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / 'Data Files'
        self.data.mkdir()
        wall = rec('STAT', sub('NAME', 'wall'), sub('MODL', 'x\\wall.nif'))
        (self.data / 'Morrowind.esm').write_bytes(master(2, wall, exterior(0, 0, ref(1, 'wall', (100, 100, 0)))))
        (self.data / 'Tribunal.esm').write_bytes(master(
            1, interior('Town, Yard', 0x87, sub('RGNN', 'Town Region'), ref(1, 'wall', (0, 0, 3000))),
            masters=('Morrowind.esm',)))
        (self.data / 'Bloodmoon.esm').write_bytes(master(1, exterior(-20, 20, ref(1, 'wall', (-160000, 165000, 5))),
                                                         masters=('Morrowind.esm',)))
        (self.data / 'Morrowind.bsa').write_bytes(b'archive')
        (self.data / 'Tribunal.bsa').write_bytes(b'archive two')
        (self.data / 'Meshes').mkdir()
        (self.data / 'Meshes' / 'loose.nif').write_bytes(b'mesh')
        self.out = Path(self.tmp.name) / 'presented'
        probe = Path(self.tmp.name) / 'probe'
        try:
            os.symlink(self.data, probe, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.tmp.cleanup()
            self.skipTest('this system cannot make symbolic links here')
        probe.unlink()

    def tearDown(self):
        self.tmp.cleanup()

    def make(self, masters=THREE):
        return pd.make(self.data, self.out, masters, CONFIG)

    def cells(self, raw):
        out = {}
        for tag, flags, payload in records(raw):
            if tag == 'CELL':
                head, groups = pe._split(payload)
                bits, x, y = struct.unpack('<Iii', pe._field(head, 'DATA'))
                out[pe._text(pe._field(head, 'NAME')) if bits & 1 else (x, y)] = groups
        return out

    def test_base_game_alone_makes_no_folder(self):
        folder, receipt = self.make(['Morrowind.esm'])
        self.assertEqual(folder, self.data)
        self.assertIsNone(receipt)
        self.assertFalse(self.out.exists())

    def test_the_folder(self):
        folder, receipt = self.make()
        self.assertEqual(folder, self.out)
        cells = self.cells((self.out / 'Morrowind.esm').read_bytes())
        self.assertIn((0, 0), cells)                          # the base cell
        self.assertIn((-20, 20), cells)                       # the cell only Bloodmoon adds
        self.assertIn((-12, -30), cells)                      # the presented yard
        self.assertNotIn('Town, Yard', cells)
        for name in ('Tribunal.esm', 'Bloodmoon.esm'):
            self.assertEqual((self.out / name).read_bytes(), pd.header_only_master())
        for name in ('Morrowind.bsa', 'Tribunal.bsa', 'Meshes'):
            self.assertTrue((self.out / name).is_symlink())
        self.assertEqual((self.out / 'Meshes' / 'loose.nif').read_bytes(), b'mesh')
        self.assertEqual(receipt['header_only'], ['Tribunal.esm', 'Bloodmoon.esm'])
        self.assertEqual(sorted(receipt['linked']), ['Meshes', 'Morrowind.bsa', 'Tribunal.bsa'])
        self.assertEqual(receipt['presented_cells'][0]['cell'], 'Town, Yard')
        self.assertEqual(json.loads((self.out / pd.RECEIPT).read_text()), receipt)

    def test_reading_the_folder_with_the_same_masters_gives_the_presented_cells(self):
        """The folder is read with the same masters selected: merging the presented master with the header-only
        masters gives its cells and reference numbers back unchanged."""
        self.make()
        direct = self.cells((self.out / 'Morrowind.esm').read_bytes())
        again = self.cells(master_bytes(self.out, THREE))
        self.assertEqual(sorted(map(str, again)), sorted(map(str, direct)))
        for key, groups in direct.items():
            self.assertEqual(again[key], groups)

    def test_same_inputs_take_the_folder_other_inputs_are_refused(self):
        self.make()
        stamp = os.stat(self.out / 'Morrowind.esm').st_mtime_ns
        folder, receipt = self.make()
        self.assertEqual(os.stat(self.out / 'Morrowind.esm').st_mtime_ns, stamp)
        with self.assertRaisesRegex(ValueError, 'other inputs'):
            pd.make(self.data, self.out, ['Morrowind.esm', 'Tribunal.esm'], CONFIG)

    def test_a_folder_without_a_receipt_is_refused(self):
        self.out.mkdir()
        (self.out / 'x').write_bytes(b'')
        with self.assertRaisesRegex(ValueError, 'no receipt'):
            self.make()


if __name__ == '__main__':
    unittest.main()
