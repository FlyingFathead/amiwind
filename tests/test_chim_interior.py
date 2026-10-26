# SPDX-License-Identifier: GPL-3.0-only
"""CHIM rooms (tools/chim/interior.py, docs/chim/INTERIOR_STORE.md): the room record and the placement light level
(world format 0.12)."""
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / 'tools', ROOT / 'src'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
from chim import format as F  # noqa: E402
from chim import placed as P  # noqa: E402
from chim import interior as I  # noqa: E402


def record(pid=0, model=3, story_hidden=False, leaves=1):
    return P.placement(pid, 1000 + pid, model, (1.0, 2.0, 3.0), (10.0, 20.0, 30.0), 0, 0, 0,
                       ((-4, -5, -6), (7, 8, 9)), leaves, story_hidden)


class LightLevelTests(unittest.TestCase):
    def test_level_goes_into_the_flags_high_byte_and_keeps_the_low_bits(self):
        rec = I.with_light(record(story_hidden=True, leaves=40), 200)
        flags = struct.unpack_from('>H', rec, I.FLAGS_AT)[0]
        self.assertEqual(flags >> 8, 200)
        self.assertEqual(flags & 0xFF, F.FLAG_OVER_16_LEAVES | F.FLAG_STORY_HIDDEN)
        self.assertEqual(rec[:I.FLAGS_AT], record(story_hidden=True, leaves=40)[:I.FLAGS_AT])
        self.assertEqual(rec[I.FLAGS_AT + 2:], record(story_hidden=True, leaves=40)[I.FLAGS_AT + 2:])

    def test_the_flags_offset_is_the_placed_records(self):
        # chim.format.PLACEMENT: '>IIIffffHbb6hHH': the flags are the last 16 bits of the 48-byte head
        self.assertEqual(I.FLAGS_AT, F.PLACEMENT.size - 2)
        self.assertEqual(struct.unpack_from('>H', record(leaves=40), I.FLAGS_AT)[0], F.FLAG_OVER_16_LEAVES)

    def test_levels_are_clamped_and_never_zero(self):
        self.assertEqual(I.light_level(-5), 1)
        self.assertEqual(I.light_level(0.2), 1)
        self.assertEqual(I.light_level(128.4), 128)
        self.assertEqual(I.light_level(900), 255)
        with self.assertRaises(ValueError):
            I.with_light(record(), 256)


class LightTintTests(unittest.TestCase):
    """World format 0.13 (INTERIOR-SUNLIGHT-COLOUR-51): the light's tint in flags bits 2-4."""

    def test_tint_goes_into_bits_2_to_4_beside_the_level_and_the_low_bits(self):
        rec = I.with_light(record(story_hidden=True, leaves=40), 200, 7)
        flags = struct.unpack_from('>H', rec, I.FLAGS_AT)[0]
        self.assertEqual(flags >> 8, 200)
        self.assertEqual((flags >> 2) & 7, 7)
        self.assertEqual(flags & 3, F.FLAG_OVER_16_LEAVES | F.FLAG_STORY_HIDDEN)
        self.assertEqual(I.with_light(record(), 9), I.with_light(record(), 9, 0))
        for bad in (-1, 8):
            with self.assertRaises(ValueError):
                I.with_light(record(), 9, bad)
        with self.assertRaises(ValueError):
            I.with_light(I.with_light(record(), 0, 2), 0, 1)

    def test_the_room_record_is_0_13_and_reads_its_tints_back(self):
        self.assertEqual(I.FORMAT_VERSION, (0, 13))
        recs = [I.with_light(record(pid=i), 50, t) for i, t in enumerate((0, 2, 6))]
        room = I.read_room_record(I.room_record(((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)), [3], recs))
        self.assertEqual([p['tint'] for p in room['placements']], [0, 2, 6])
        self.assertEqual([p['light'] for p in room['placements']], [50, 50, 50])

    def test_light_colours_map_to_the_engine_tints(self):
        import interior_lighting as il
        # Akulakhan's Chamber sunlight 255,140,140: red; a lantern (aw_light_hue 255,210,140): warm; a fire: orange
        self.assertEqual(il.light_tint((255, 140, 140)), 2)
        self.assertEqual(il.light_tint((255, 210, 140)), 1)
        self.assertEqual(il.light_tint((255, 170, 100)), 3)
        self.assertEqual(il.light_tint((255, 240, 120)), 4)
        self.assertEqual(il.light_tint((120, 255, 120)), 5)
        self.assertEqual(il.light_tint((140, 180, 255)), 6)
        self.assertEqual(il.light_tint((200, 120, 255)), 7)
        # grey or nearly grey light and darkness stay plain
        for grey in ((128, 128, 128), (200, 180, 160), (0, 0, 0)):
            self.assertEqual(il.light_tint(grey), 0)

    def test_the_colour_sum_is_the_light_sum_in_colour(self):
        import numpy as np
        import interior_lighting as il
        lighting = {'ambient': [40, 20, 20], 'sunlight': [255, 140, 140], 'falloff': 'original', 'facing': False,
                    'lights': [{'color': [255, 200, 120], 'radius': 400, 'position': [0, 0, 0], 'flags': 0}],
                    'zones': [{'box': [[-50, -50, -50], [50, 50, 50]], 'scale': 0.5, 'soft': 10}]}
        for point in (np.array([0., 0, 0]), np.array([30., 10, 0]), np.array([300., 0, 0])):
            rgb = il.point_colour(point, lighting)
            self.assertAlmostEqual(float(np.dot(rgb, [.299, .587, .114])), il.point_light(point, lighting), places=6)
        self.assertEqual(il.light_tint(il.point_colour(np.array([300., 0, 0]), lighting)), 2)


class RoomRecordTests(unittest.TestCase):
    def test_round_trip(self):
        recs = [I.with_light(record(pid=i, model=m), lv) for i, (m, lv) in enumerate([(3, 10), (7, 250), (3, 1)])]
        data = I.room_record(((-100.0, -50.0, -8.0), (300.0, 120.0, 96.0)), [3, 7], recs)
        self.assertEqual(data[:4], b'CHIM')
        self.assertEqual(data[4:8], I.ROOM_KIND)
        self.assertEqual(struct.unpack_from('>HH', data, 8), I.FORMAT_VERSION)
        # the engine's reader (chim/chim_room.c): directory = 64 (the model list), data = 64 + 4 x models
        self.assertEqual(struct.unpack_from('>II', data, 20), (64, 64 + 4 * 2))
        self.assertEqual(len(data), 64 + 4 * 2 + 56 * 3)
        room = I.read_room_record(data)
        self.assertEqual(room['models'], [3, 7])
        self.assertEqual([round(v, 3) for v in room['bounds'][0]], [-100.0, -50.0, -8.0])
        self.assertEqual([p['model'] for p in room['placements']], [3, 7, 3])
        self.assertEqual([p['light'] for p in room['placements']], [10, 250, 1])
        self.assertEqual(room['placements'][1]['angles'], (10.0, 20.0, 30.0))

    def test_a_short_or_foreign_file_is_refused(self):
        data = I.room_record(((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)), [1], [I.with_light(record(model=1), 5)])
        with self.assertRaises(ValueError):
            I.read_room_record(data[:-4])
        with self.assertRaises(ValueError):
            I.read_room_record(data[:4] + b'SECT' + data[8:])


if __name__ == '__main__':
    unittest.main()
