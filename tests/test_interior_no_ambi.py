"""INTERIOR-NO-AMBI-66: an interior cell without AMBI. The reference engine lights a plain interior without AMBI with
its default mood (ambient, sunlight and fog black, fog density 0: lit by its own lights only); a cell flagged "behave
like exterior" is an exterior (sky, region weather, moving sun), so the room stages leave it out and list it. A really
invalid AMBI still refuses, naming the cell, and every bad cell of one read is listed together. A cell with AMBI reads
exactly as before."""
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
from mwad import interior  # noqa: E402
from mwad.esm import FormatError  # noqa: E402
import chim_room_batches  # noqa: E402
import interior_lighting  # noqa: E402

AMBI = bytes([10, 20, 30, 0, 100, 90, 80, 0, 1, 2, 3, 0]) + struct.pack('<f', 0.5)


def record(tag, *subs):
    data = b''.join(struct.pack('<4sI', t, len(d)) + d for t, d in subs)
    return struct.pack('<4sIII', tag, len(data), 0, 0) + data


def room(name, flags=1, ambi=AMBI):
    subs = [(b'NAME', name.encode() + b'\0'), (b'DATA', struct.pack('<Iii', flags, 0, 0))]
    if ambi is not None:
        subs.append((b'AMBI', ambi))
    return record(b'CELL', *subs)


class NoAmbiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.base = self.root / 'Morrowind.esm'
        self.base.write_bytes(room('Lit Room') + room('Dark Room', ambi=None) + room('Bad Room', ambi=b'\0' * 12)
                              + room('Worse Room', ambi=b'\0' * 4))
        self.plugin = self.root / 'Tribunal.esm'
        self.plugin.write_bytes(room('Mournhold, Plaza', flags=1 | 0x80, ambi=None) + room('Mournhold, Shop'))

    def tearDown(self):
        self.temp.cleanup()

    def test_with_ambi_unchanged(self):
        cell = interior.read_interior(self.base, 'Lit Room')
        self.assertEqual(cell['lighting'], {'ambient': [10, 20, 30], 'sunlight': [100, 90, 80], 'fog': [1, 2, 3],
                                            'fog_density': 0.5})

    def test_plain_interior_without_ambi_is_the_reference_default(self):
        cell = interior.read_interior(self.base, 'Dark Room')
        lighting = cell['lighting']
        self.assertTrue(lighting['no_ambi'])
        self.assertEqual((lighting['ambient'], lighting['sunlight'], lighting['fog'], lighting['fog_density']),
                         ([0, 0, 0], [0, 0, 0], [0, 0, 0], 0.))
        # lit by its own lights only: no ambient and no sunlight in the bake
        self.assertEqual(interior_lighting.sun_light(lighting, [0., 0., 1.]), 0.)
        self.assertEqual(interior_lighting.sun_light(lighting, None), 0.)

    def test_behave_like_exterior_reads_and_is_flagged(self):
        cell = interior.read_interior(self.base, 'Mournhold, Plaza', layers=[self.plugin])
        self.assertTrue(cell['lighting']['no_ambi'])
        self.assertEqual(interior.exterior_like_cells(self.plugin.read_bytes()), {'mournhold, plaza': 'Mournhold, Plaza'})
        self.assertEqual(interior.exterior_like_cells(self.base.read_bytes()), {})

    def test_invalid_ambi_refuses_naming_every_cell(self):
        with self.assertRaises(FormatError) as caught:
            interior.read_interiors(self.base, ['Lit Room', 'Bad Room', 'Worse Room'])
        text = str(caught.exception)
        self.assertIn('2 interior cells refused', text)
        self.assertIn('Bad Room', text)
        self.assertIn('Worse Room', text)

    def test_room_stage_sets_exterior_like_cells_aside(self):
        rows = [{'room': 'Mournhold, Plaza'}, {'room': 'Mournhold, Shop'}]
        merged = self.root / 'merged.esm'
        merged.write_bytes(self.base.read_bytes() + self.plugin.read_bytes())
        with mock.patch.dict(os.environ, {'AMIWIND_MASTERS': 'Morrowind.esm,Tribunal.esm'}), \
                mock.patch('mwad.masters.master_path', return_value=merged):
            keep, left = chim_room_batches.exterior_like_rooms(self.root, rows)
        self.assertEqual(keep, [{'room': 'Mournhold, Shop'}])
        # a district is built as open terrain by the district module (ROOMS-SET-ASIDE-NOT-BUILT-67), never "waiting"
        self.assertEqual(left, [{'cell': 'Mournhold, Plaza', 'master': 'Tribunal.esm',
                                 'state': 'a district, built as open terrain by the district module '
                                          '(tribunal-mournhold), not as a room'}])

    def test_room_stage_base_game_alone_untouched(self):
        rows = [{'room': 'Lit Room'}]
        with mock.patch.dict(os.environ, {'AMIWIND_MASTERS': ''}):
            self.assertEqual(chim_room_batches.exterior_like_rooms(self.root, rows), (rows, []))


if __name__ == '__main__':
    unittest.main()
