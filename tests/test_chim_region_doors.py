# SPDX-License-Identifier: GPL-3.0-only
"""CHIM region frames carry a door bank (CHIM-REGION-DOORS-NO-PROMPT-42): every load door of the frame's own cell
gets a row of doors-<map>.txt (AWD3, engine aw_scene.c read_links_for), "-" when its room is not converted, so the
engine shows "Interior unavailable" instead of nothing.

Every fixture is synthetic: made-up references, names and numbers. No game data.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tools', ROOT / 'src'):
    sys.path.insert(0, str(p))
from chim import frame_map as FM  # noqa: E402

CELL = [-3, 5]
CENTRE = [(CELL[0] * 8192 + 4096), (CELL[1] * 8192 + 4096)]


def door(number, cell, offset, destination=True, label='Test Shack'):
    x, y = CENTRE[0] + offset[0], CENTRE[1] + offset[1]
    ref = {'cell': cell, 'number': number, 'type': 'DOOR', 'id': 'test_door',
           'position': [x, y, 400.0], 'bounds': [[x - 40, y - 8, 380.0], [x + 40, y + 8, 560.0]]}
    if destination:
        ref['destination'] = {'position': [10.0, 20.0, 30.0], 'rotation_radians': [0, 0, 1.5]}
        if label:
            ref['destination_cell'] = label
    return ref


class RegionDoorBank(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.frame = {'id': 'rcm3_p5', 'cell': CELL, 'origin': [CENTRE[0] * 0.25, CENTRE[1] * 0.25, 100.0]}
        refs = [door(12, CELL, (100, -200)), door(7, CELL, (0, 0), label=None),
                door(30, [-2, 5], (5000, 0)),                    # a neighbour's door in the apron: not this frame's
                door(40, CELL, (10, 10), destination=False),     # an ordinary door: no load, no prompt
                {'cell': CELL, 'number': 3, 'type': 'STAT', 'position': [0, 0, 0], 'bounds': [[0, 0, 0], [1, 1, 1]]}]
        index = self.tmp / 'work' / 'rcm3_p5' / 'scenery'
        index.mkdir(parents=True)
        (index / 'scenery-index.json').write_text(json.dumps({'references': refs}))

    def test_rows_hold_the_cells_own_load_doors_frame_local(self):
        rows = FM.region_door_rows(self.tmp, self.frame)
        self.assertEqual([r['reference'] for r in rows], [7, 12])
        self.assertEqual({r['target'] for r in rows}, {'-'})
        r12 = rows[1]
        self.assertEqual(r12['label'], 'Test Shack')
        self.assertEqual(rows[0]['label'], FM.DOOR_LABEL_DEFAULT)
        # frame-local: (Morrowind - frame centre) x 0.25, z x 0.25 less the frame origin z
        self.assertAlmostEqual(r12['box'][0][0], (100 - 40) * 0.25)
        self.assertAlmostEqual(r12['box'][1][1], (-200 + 8) * 0.25)
        self.assertAlmostEqual(r12['box'][0][2], 380 * 0.25 - 100.0)

    def test_the_bank_is_what_the_engine_reads(self):
        rows = FM.region_door_rows(self.tmp, self.frame)
        text = FM.door_bank_text('vf0123', rows)
        lines = text.splitlines()
        self.assertEqual(lines[0], 'AWD3')
        fields = lines[2].split(' ')
        # source target reference, 6 box values, arrival xyz and yaw, then the label (engine: 14 fields)
        self.assertEqual(fields[:3], ['vf0123', '-', '12'])
        self.assertEqual(len(fields[3:13]), 10)
        self.assertEqual(' '.join(fields[13:]), 'Test Shack')
        for v in fields[3:9]:
            self.assertLess(abs(float(v)), 32768)
        box = [float(v) for v in fields[3:9]]
        self.assertTrue(all(0 <= box[k + 3] - box[k] <= 256 for k in range(3)))

    def test_install_writes_the_bank_once_and_only_with_doors(self):
        id1 = self.tmp / 'id1'
        id1.mkdir()
        record = FM.install_region_doors(id1, 'vf0123', FM.region_door_rows(self.tmp, self.frame))
        self.assertEqual((record['doors'], record['unavailable'], record['file']), (2, 2, 'doors-vf0123.txt'))
        self.assertTrue((id1 / 'doors-vf0123.txt').read_bytes().startswith(b'AWD3\n'))
        self.assertIsNone(FM.install_region_doors(id1, 'vf0124', []))
        self.assertFalse((id1 / 'doors-vf0124.txt').exists())
        (id1 / 'doors-vf0125.txt').write_text('other')
        with self.assertRaisesRegex(ValueError, 'already present'):
            FM.install_region_doors(id1, 'vf0125', FM.region_door_rows(self.tmp, self.frame))

    def test_a_frame_without_its_scenery_index_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'rcm9_p9: no scenery index'):
            FM.region_door_rows(self.tmp, {'id': 'rcm9_p9', 'cell': [9, 9], 'origin': [0, 0, 0]})
        with self.assertRaisesRegex(ValueError, 'rcm9_p9: no scenery index'):
            FM.region_door_rows(self.tmp, {'id': 'rcm9_p9', 'cell': [9, 9], 'origin': [0, 0, 0]}, placed=[5])
        # a frame that places nothing (open sea, an empty seabed) has no doors to list
        self.assertEqual(FM.region_door_rows(self.tmp, {'id': 'rcm9_p9', 'cell': [9, 9], 'origin': [0, 0, 0]},
                                             placed=[]), [])


if __name__ == '__main__':
    unittest.main()
