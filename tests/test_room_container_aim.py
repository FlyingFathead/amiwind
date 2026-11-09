# SPDX-License-Identifier: GPL-3.0-only
"""ROOM-OBJECTS-MISSING-62: every room container can be aimed at by its placement box (tools/room_container_aim.py),
and the engine aims a room's container by that box (aw_inventory.c placed_target, chim_room.c ChimRoom_RayRef)."""
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import room_container_aim as aim  # noqa: E402

SRC = ROOT / 'engine/aga/src'
URN = [[-29.0, -29.0, -28.4], [29.0, 29.0, 28.4]]      # urn_ash00: 7.1 map units half-height about its point


def focus_file(rooms):
    index, rows = [], []
    for key in sorted(rooms):
        index.append(struct.pack('<III', key, len(rows), len(rooms[key])))
        for kind, ref in rooms[key]:
            row = bytearray(96)
            row[0] = ord(kind)
            struct.pack_into('<I', row, 4, ref)
            rows.append(bytes(row))
    return b'AWF3' + struct.pack('<I', len(index)) + b''.join(index) + b''.join(rows)


class RoomContainerAim(unittest.TestCase):
    def test_focus_containers_keeps_only_container_rows(self):
        raw = focus_file({126: [('D', 1), ('C', 379641), ('I', 376619), ('C', 379656)], 7: [('A', 2)]})
        self.assertEqual(aim.focus_containers(raw), {126: [379641, 379656]})

    def test_an_urn_from_a_standing_eye_is_hit_within_reach(self):
        self.assertIsNone(aim.aim_problem(URN))
        flat = [[0, 0, 0], [10, 10, 0]]
        self.assertEqual(aim.aim_problem(flat), 'its box has no size')

    def test_check_names_a_container_the_room_does_not_draw(self):
        focus = {126: [379641, 379642]}
        cells = {'ri8c361151ce': ({379641: URN, 379642: URN}, {379641})}
        rows, found = aim.check(focus, cells, {'ri8c361151ce': 126})
        self.assertEqual(rows, 2)
        self.assertEqual(found, [{'room': 'ri8c361151ce', 'reference': 379642, 'why': 'no drawn placement in the room'}])

    def test_engine_aims_room_containers_by_their_box(self):
        inventory = (SRC / 'aw_inventory.c').read_text(encoding='utf-8')
        target = inventory[inventory.index('static int placed_target(void){'):]
        target = target[:target.index('\n}\n')]
        self.assertIn("row->kind=='C' && !focus_outdoor && aw_room_ray", target)
        self.assertIn('(hit=aw_room_ray(row->reference,eye,f))>=0', target)
        self.assertIn('aw_room_ray=ChimRoom_RayRef;', (SRC / 'aw_placed.c').read_text(encoding='utf-8'))
        room = (SRC / 'chim/chim_room.c').read_text(encoding='utf-8')
        self.assertIn('float ChimRoom_RayRef (unsigned reference, const float *eye, const float *dir)', room)
        self.assertIn('AW_RayBox (eye, dir, p->mins, p->maxs, &lo, &hi)', room)


if __name__ == '__main__':
    unittest.main()
