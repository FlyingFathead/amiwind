# SPDX-License-Identifier: GPL-3.0-only
"""Routing-priority removal must preserve partial cores and direct dependencies."""
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from world_payload import prune, shadowed, subtract


def fixture(root):
    (root / 'world').mkdir()
    (root / 'maps').mkdir()
    # Town covers map zero; map one crosses its right boundary; map two
    # repeats map one and is shadowed by that earlier region.
    raw = b'AWR2' + struct.pack('<I', 3)
    raw += struct.pack('<7f', 0, 0, 0, 0, 0, 10, 10) * 2
    for i, core in enumerate(((0, 0, 10, 10), (5, 0, 15, 10), (5, 0, 15, 10))):
        raw += struct.pack('<8s11f', ('vf%04d' % i).encode(), 0, 0, 0, *core, -1000, -1000, 1000, 1000)
        data = struct.pack('<iii', 29, 124, 3) + bytes(112) + b'{}\0'
        (root / 'maps' / ('vf%04d.bsp' % i)).write_bytes(data)
    (root / 'world/regions.awr').write_bytes(raw)
    return [{'world_slot': 0}]


class PayloadTests(unittest.TestCase):
    def test_half_open_boundary_and_partial_core(self):
        self.assertEqual(subtract((0, 0, 10, 10), (10, 0, 20, 10)), [(0, 0, 10, 10)])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            towns = fixture(root)
            self.assertEqual(shadowed(root, towns), ['vf0000', 'vf0002'])
            rows = prune(root, root / 'receipt.json', towns)
            self.assertEqual([r['file'] for r in rows], ['maps/vf0000.bsp', 'maps/vf0002.bsp'])
            self.assertTrue((root / 'maps/vf0001.bsp').exists())
            self.assertEqual(len((root / 'world/regions.awr').read_bytes()), 220)

    def test_direct_door_dependency_retained(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            towns = fixture(root)
            (root / 'scene-doors.txt').write_bytes(b'destination vf0000\n')
            prune(root, root / 'receipt.json', towns)
            self.assertTrue((root / 'maps/vf0000.bsp').exists())
            report = json.loads((root / 'receipt.json').read_text())
            self.assertEqual(report['retained_dependencies'][0]['references'], ['scene-doors.txt'])

    def test_invalid_map_fails_before_removal(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            towns = fixture(root)
            (root / 'maps/broken.bsp').write_bytes(b'bad')
            with self.assertRaises(ValueError):
                prune(root, root / 'receipt.json', towns)
            self.assertTrue((root / 'maps/vf0000.bsp').exists())

    def test_entity_reference_and_chim_in_bsp_extension_survive(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            towns = fixture(root)
            for name, entity in [('vf0000', b'{"classname" "worldspawn" "_chim_frame" "0 0"}\0'),
                                 ('vf0001', b'{"classname" "trigger_changelevel" "map" "vf0002"}\0')]:
                (root / 'maps' / (name + '.bsp')).write_bytes(
                    struct.pack('<iii', 29, 124, len(entity)) + bytes(112) + entity)
            self.assertEqual(prune(root, root / 'receipt.json', towns), [])
            self.assertTrue((root / 'maps/vf0000.bsp').exists())
            self.assertTrue((root / 'maps/vf0002.bsp').exists())


if __name__ == '__main__':
    unittest.main()
