# SPDX-License-Identifier: GPL-3.0-only
"""CHIMport cell keys and the expansion layers (CHIMPORT-CELL-KEY-LAYERS-65): selecting the layers re-keys only the
cells whose frame they change (their own and neighbours' merged CELL/LAND records, the objects placed there), never
the whole island. Small synthetic masters: no game data."""
import json
import os
import struct
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'tools'))
import chimport  # noqa: E402


def sub(tag, data):
    if isinstance(data, str):
        data = data.encode('cp1252') + b'\0'
    return struct.pack('<4sI', tag.encode(), len(data)) + data


def rec(tag, *subs):
    payload = b''.join(subs)
    return struct.pack('<4sIII', tag.encode(), len(payload), 0, 0) + payload


def tes3(*masters):
    out = [sub('HEDR', struct.pack('<fI', 1.3, 0) + b'\0' * 288 + struct.pack('<I', 0))]
    for m in masters:
        out += [sub('MAST', m), sub('DATA', struct.pack('<Q', 0))]
    return rec('TES3', *out)


def cell(x, y, *refs):
    return rec('CELL', sub('NAME', ''), sub('DATA', struct.pack('<Iii', 2, x, y)), *refs)


def land(x, y):
    return rec('LAND', sub('INTV', struct.pack('<ii', x, y)), sub('DATA', struct.pack('<I', 0)))


def ref(number, ident):
    return sub('FRMR', struct.pack('<I', number)) + sub('NAME', ident) + sub('DATA', struct.pack('<6f', *[0.0] * 6))


BASE = (tes3() + rec('STAT', sub('NAME', 'rock'), sub('MODL', 'rock.nif'))
        + rec('STAT', sub('NAME', 'boat'), sub('MODL', 'boat.nif'))
        + b''.join(cell(x, y, ref(10 * x + y + 100, 'rock')) + land(x, y) for x in range(0, 9) for y in range(0, 3)))
# Bloodmoon: one placement more in island cell (6,1), a changed boat record placed only in (2,1), its own cell
BLOODMOON = (tes3('Morrowind.esm') + rec('STAT', sub('NAME', 'boat'), sub('MODL', 'boat2.nif'))
             + cell(6, 1, ref(1, 'rock')) + cell(-20, 20, ref(2, 'rock')) + land(-20, 20))
BASE = BASE.replace(cell(2, 1, ref(121, 'rock')), cell(2, 1, ref(121, 'rock'), ref(999, 'boat')))


class LayerKeys(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        data = Path(self.tmp.name) / 'Data Files'
        data.mkdir()
        (data / 'Morrowind.esm').write_bytes(BASE)
        (data / 'Bloodmoon.esm').write_bytes(BLOODMOON)
        self.palette = Path(self.tmp.name) / 'palette.lmp'
        self.palette.write_bytes(bytes(768))
        lock = Path(self.tmp.name) / 'lock.json'
        lock.write_text(json.dumps({'files': {str(data / 'Morrowind.esm'): {'sha256': 'a' * 64},
                                              str(data / 'Bloodmoon.esm'): {'sha256': 'b' * 64}}}))
        self.data = data
        self.env = {'AMIWIND_INPUTS_LOCK': str(lock)}
        chimport._TOUCH.clear()

    def tearDown(self):
        self.tmp.cleanup()

    def keys(self, masters):
        env = dict(self.env, AMIWIND_MASTERS=masters)
        with mock.patch.dict(os.environ, env):
            out = {}
            for x in range(0, 9):
                for y in range(0, 3):
                    key, why = chimport.cell_key((x, y), self.data, self.palette)
                    self.assertIsNotNone(key, why)
                    out[(x, y)] = key
            return out

    def test_only_the_cells_a_layer_changes_are_re_keyed(self):
        alone = self.keys('Morrowind.esm')
        layered = self.keys('Morrowind.esm,Bloodmoon.esm')
        moved = {c for c in alone if alone[c] != layered[c]}
        # (6,1) and its 3 x 3 neighbours (its frame reads them); (2,1) places the boat Bloodmoon changes, and so do
        # the frames around it
        expected = {(x, y) for x in (5, 6, 7) for y in (0, 1, 2)} | {(x, y) for x in (1, 2, 3) for y in (0, 1, 2)}
        self.assertEqual(moved, expected)
        self.assertEqual(alone[(0, 0)], layered[(0, 0)])
        self.assertEqual(alone[(8, 2)], layered[(8, 2)])

    def test_no_layer_no_touch(self):
        self.assertIsNone(chimport.layer_touch((6, 1), self.data, ['Morrowind.esm']))
        self.assertIsNotNone(chimport.layer_touch((6, 1), self.data, ['Morrowind.esm', 'Bloodmoon.esm']))
        self.assertIsNone(chimport.layer_touch((0, 0), self.data, ['Morrowind.esm', 'Bloodmoon.esm']))


if __name__ == '__main__':
    unittest.main()
