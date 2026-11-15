# SPDX-License-Identifier: GPL-3.0-only
"""tools/container_census.py: the world-wide container table and the box count (OUTDOOR-CONTAINER-AIM-66)."""
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]


class ContainerCensusTests(unittest.TestCase):
    def test_box_field_is_told_from_a_record_id(self):
        import container_census as cc
        box = struct.pack('<7f', 30, 20, 10, 1, 0, 0, 0) + bytes(4)
        self.assertTrue(cc.is_box(box))
        self.assertFalse(cc.is_box(b'contain_com_sack_01'.ljust(32, b'\0')))
        self.assertFalse(cc.is_box(bytes(32)))

    def test_window_counts_boards_and_boxed_containers(self):
        import container_census as cc
        import prepare_focus as pf
        box = struct.pack('<7f', 30, 20, 10, 1, 0, 0, 0) + bytes(4)

        def row(kind, action, field):
            return bytes([ord(kind), 0, action, 0]) + bytes(60) + field

        cells = [(pf.exterior_key(0, 0), [row('C', 1, box), row('N', 0, box), row('C', 1, b'odd'.ljust(32, b'\0'))]),
                 (pf.exterior_key(5, 5), [row('C', 1, box)])]
        index, body, at = [], [], 0
        for key, rows in cells:
            index.append(struct.pack('<III', key, at, len(rows))); body += rows; at += len(rows)
        payload = b'AWF3' + struct.pack('<I', len(cells)) + b''.join(index) + b''.join(body)
        got = cc.window_boxes(payload)
        self.assertEqual((got['exterior_containers_boxed'], got['exterior_containers_unboxed']), (2, 1))
        self.assertEqual(got['most_boxes_in_a_window'], 2)

    def test_engine_holds_the_most_boxes_counted(self):
        # the census of the original data (13 November 2026): at most 154 boards and boxed containers in a 3 x 3 window
        inventory = (ROOT / 'engine/aga/src/aw_inventory.c').read_text(encoding='utf-8')
        self.assertIn('#define FOCUS_BOARDS 256', inventory)


if __name__ == '__main__':
    unittest.main()
