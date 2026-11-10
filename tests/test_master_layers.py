"""The cell readers take a master list (DLC-BUILD-LATER): Morrowind.esm plus the masters of the expansion layers a
build uses. On a synthetic plugin, a cell the plugin adds appears only when its master is in the list, and without
layers every result (and its digest) is exactly the single-master one."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import exterior_plan  # noqa: E402
from mwad import interior  # noqa: E402


def record(tag, *subs):
    data = b''.join(struct.pack('<4sI', t, len(d)) + d for t, d in subs)
    return struct.pack('<4sIII', tag, len(data), 0, 0) + data


def land(x, y):
    return record(b'LAND', (b'INTV', struct.pack('<ii', x, y)), (b'VHGT', b''))


def room(name, ref_id=None):
    subs = [(b'NAME', name.encode() + b'\0'), (b'DATA', struct.pack('<Iii', 1, 0, 0)), (b'AMBI', bytes(12) + struct.pack('<f', 0.5))]
    if ref_id:
        subs += [(b'FRMR', struct.pack('<I', 1)), (b'NAME', ref_id.encode() + b'\0'),
                 (b'DATA', struct.pack('<6f', 1, 2, 3, 0, 0, 0))]
    return record(b'CELL', *subs)


def static(name, model):
    return record(b'STAT', (b'NAME', name.encode() + b'\0'), (b'MODL', model.encode() + b'\0'))


class MasterLayerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.base, self.plugin = root / 'Morrowind.esm', root / 'Tribunal.esm'
        self.base.write_bytes(land(0, 0) + land(1, 0) + static('rock', 'r.nif') + room('Base Room', 'rock'))
        # the plugin edits a base cell (1, 0), adds an exterior cell (5, 5) and a room with a base record of its own
        self.plugin.write_bytes(land(1, 0) + land(5, 5) + static('stone', 's.nif') + room('Mournhold Room', 'stone'))

    def tearDown(self):
        self.temp.cleanup()

    def test_exterior_cells(self):
        alone = exterior_plan.source_cells(self.base)
        self.assertEqual(alone, exterior_plan.source_cells(self.base, ()))   # default unchanged
        self.assertEqual(alone[0], [(0, 0), (1, 0)])
        cells, digest = exterior_plan.source_cells(self.base, [self.plugin])
        self.assertEqual(cells, [(0, 0), (1, 0), (5, 5)])                     # the added cell, the edited one once
        self.assertNotEqual(digest, alone[1])

    def test_interior_cells(self):
        base = interior.read_interior(self.base, 'Base Room')
        self.assertEqual(base, interior.read_interior(self.base, 'Base Room', layers=()))
        with self.assertRaises(ValueError):
            interior.read_interior(self.base, 'Mournhold Room')               # not without its master
        added = interior.read_interior(self.base, 'Mournhold Room', layers=[self.plugin])
        self.assertEqual(added['refs'][0]['model'], 's.nif')
        both = interior.read_interiors(self.base, ['Base Room', 'Mournhold Room'], layers=[self.plugin])
        self.assertEqual([c['name'] for c in both], ['Base Room', 'Mournhold Room'])
        self.assertNotEqual(both[0]['master_sha256'], base['master_sha256'])  # keyed by every master read


if __name__ == '__main__':
    unittest.main()
