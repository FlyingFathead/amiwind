# SPDX-License-Identifier: GPL-3.0-only
"""The rooms' levelled creatures in the room maps (tools/room_levelled.py, TOMB-NO-CREATURES-60).

Before v0.0.61 the room stages wrote no entity for a room's levelled creature reference (the engine half,
CREATURE-ROOM-LEVELLED-54, was in since v0.0.54), so tombs and caves had no creatures. Checked on synthetic data: one
aw_levelled entity per levelled reference with the list's index in the actor table's own list order (the table built
from the same master names that list there), origin and yaw as the residents; placed creatures, deleted references,
scaled references and unknown lists are not written (the last two listed with their reasons); the entities appended
to the room map's entity lump, its other entities kept; off writes nothing; a second write is refused; the residents
report loses the left-out rows of the written references; both room stages call it and the town stages do not.
"""
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from test_chim_levelled import MASTER, LIBRARY  # noqa: E402


def room_map(text):
    from player_hull import pack_lumps
    return pack_lumps([bytearray((text + '\0').encode('cp1252'))] + [bytearray() for _ in range(14)])


def entity_text(raw):
    from player_hull import lumps
    return bytes(lumps(raw)[0]).rstrip(b'\0').decode('cp1252')


REFS = [
    {'number': 31, 'id': 'Unused', 'type': 'LEVC', 'position': [100.0, -200.0, 8.0], 'rotation_radians': [0, 0, 0.5],
     'scale': 1.0},
    {'number': 32, 'id': 'crab', 'type': 'CREA', 'position': [0.0, 0.0, 0.0], 'rotation_radians': [0, 0, 0],
     'scale': 1.0},
    {'number': 33, 'id': 'unused', 'type': 'LEVC', 'position': [0.0, 0.0, 0.0], 'deleted': True, 'scale': 1.0},
    {'number': 34, 'id': 'unused', 'type': 'LEVC', 'position': [0.0, 0.0, 0.0], 'rotation_radians': [0, 0, 0],
     'scale': 1.5},
    {'number': 35, 'id': 'no_such_list', 'type': 'LEVC', 'position': [0.0, 0.0, 0.0], 'rotation_radians': [0, 0, 0],
     'scale': 1.0},
]


class RoomLevelledTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.master = self.dir / 'Morrowind.esm'
        self.master.write_bytes(MASTER)
        os.environ.pop('AMIWIND_ROOM_LEVELLED', None)

    def tearDown(self):
        os.environ.pop('AMIWIND_ROOM_LEVELLED', None)
        self.tmp.cleanup()

    def test_index_is_the_tables_list_order(self):
        import room_levelled as R
        from chim import actors as A
        index = R.list_index(self.master)
        self.assertIn('unused', index)          # a list only a room references
        data, _ = A.build_table(A.exterior_actors(MASTER), {}, A.levelled_lists(MASTER), A.creature_ids(MASTER),
                                LIBRARY, room_roots=A.room_levelled_roots(MASTER))
        _, _, _, bases, _ = A.read_table(data)
        lists = A.read_lists(data)
        self.assertEqual(len(lists), len(index))
        chance, flags, entries = lists[index['unused']]
        self.assertEqual(len(entries), 1)
        self.assertIn('c_crab.mdl', bases[entries[0][1]]['text'])   # the list gives the crab, with its model

    def test_entities(self):
        import room_levelled as R
        fields, left = R.entities(REFS, R.list_index(self.master), 'ri_cave')
        self.assertEqual(len(fields), 1)
        f = fields[0]
        self.assertEqual((f['classname'], f['aw_ref'], f['sounds']), ('aw_levelled', 31, R.list_index(self.master)['unused']))
        self.assertEqual(f['origin'], '25.00000 -50.00000 2.00000')
        self.assertEqual(f['angles'], '0 %.5f 0' % -math.degrees(0.5))
        self.assertEqual({(r['reference'], r['reason']) for r in left},
                         {(34, R.REASON_SCALED), (35, R.REASON_NO_LIST)})

    def test_write_appends_and_refuses_twice(self):
        import room_levelled as R
        maps = self.dir / 'maps'
        maps.mkdir()
        keep = '{\n"classname" "worldspawn"\n}\n{\n"classname" "aw_npc"\n"aw_ref" "7"\n}\n'
        (maps / 'ri_cave.bsp').write_bytes(room_map(keep))
        (maps / 'ri_empty.bsp').write_bytes(room_map(keep))
        rooms = {'ri_cave': {'refs': REFS}, 'ri_empty': {'refs': REFS[1:2]}}
        report = R.write(maps, rooms, self.master)
        self.assertEqual((report['mode'], report['placed'], report['maps']), ('table', 1, {'ri_cave': 1}))
        text = entity_text((maps / 'ri_cave.bsp').read_bytes())
        self.assertTrue(text.startswith(keep.rstrip('\n')))
        self.assertEqual(text.count('"classname" "aw_levelled"'), 1)
        self.assertIn('"aw_ref" "31"', text)
        self.assertEqual(entity_text((maps / 'ri_empty.bsp').read_bytes()), keep)   # nothing to add: untouched
        with self.assertRaises(ValueError):
            R.write(maps, rooms, self.master)
        left = [{'map': 'ri_cave', 'reference': 31, 'type': 'LEVC'}, {'map': 'ri_cave', 'reference': 35, 'type': 'LEVC'},
                {'map': 'ri_cave', 'reference': 32, 'type': 'CREA'}]
        self.assertEqual([r['reference'] for r in R.drop_placed(left, report['maps'], rooms, R.list_index(self.master))],
                         [35, 32])

    def test_off_writes_nothing(self):
        import room_levelled as R
        maps = self.dir / 'maps'
        maps.mkdir()
        raw = room_map('{\n"classname" "worldspawn"\n}\n')
        (maps / 'ri_cave.bsp').write_bytes(raw)
        os.environ['AMIWIND_ROOM_LEVELLED'] = 'off'
        report = R.write(maps, {'ri_cave': {'refs': REFS}}, self.master)
        self.assertEqual((report['mode'], report['placed']), ('off', 0))
        self.assertEqual((maps / 'ri_cave.bsp').read_bytes(), raw)
        os.environ['AMIWIND_ROOM_LEVELLED'] = 'sometimes'
        with self.assertRaises(ValueError):
            R.mode()

    def test_room_stages_call_it_and_town_stages_do_not(self):
        for name in ('chim_room_batches.py', 'chim_rooms.py'):
            self.assertIn('room_levelled.write(', (ROOT / 'tools' / name).read_text())
        for name in ('prepare_area.py', 'import_town.py', 'creature_residents.py'):
            self.assertNotIn('room_levelled', (ROOT / 'tools' / name).read_text())
        build = (ROOT / 'tools/build.py').read_text()
        self.assertIn('room_levelled.add_option(p)', build)
        self.assertIn("os.environ['AMIWIND_ROOM_LEVELLED']", build)


if __name__ == '__main__':
    unittest.main()
