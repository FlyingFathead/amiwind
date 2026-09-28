"""Placed-wall rotations use fictional ESM records, never owned game data."""
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from prepare_character import barriers
from prepare_quake import CENTRE


def sub(tag, data):
    return tag.encode() + struct.pack('<I', len(data)) + data


class BarrierConversionTests(unittest.TestCase):
    def test_combined_rotation_preserves_diagonal_corridor(self):
        # A flat marker becomes a vertical wall at 45 degrees. Its thickness
        # normal must have both X and Y components, not point along world X.
        cell = sub('DATA', struct.pack('<3i', 0, 0, 0))
        cell += sub('FRMR', struct.pack('<I', 123))
        cell += sub('NAME', b'CharGenCollision - extra\0')
        cell += sub('DATA', struct.pack('<6f', CENTRE[0]+40, CENTRE[1]+80, 120,
                                      1.5*math.pi, .75*math.pi, .5*math.pi))
        with tempfile.TemporaryDirectory() as tmp:
            master = Path(tmp)/'fixture.esm'
            master.write_bytes(b'CELL'+struct.pack('<3I', len(cell), 0, 0)+cell)
            raw, refs = barriers(master)
        self.assertEqual(refs, [123])
        self.assertEqual(raw[:6], b'AWB1\x01\0')
        values = struct.unpack('<15f', raw[6:])
        self.assertEqual(values[:3], (10., 20., 30.))
        self.assertEqual(values[12:], (32., 32., 8.))
        n = values[9:12]
        self.assertAlmostEqual(n[0], -math.sqrt(.5), places=6)
        self.assertAlmostEqual(n[1], math.sqrt(.5), places=6)
        self.assertAlmostEqual(n[2], 0, places=6)
        # Translation along the corridor is tangent to the wall. The wrong
        # multiplication order crosses its thickness instead.
        self.assertAlmostEqual(n[0]*30+n[1]*30, 0, places=5)

