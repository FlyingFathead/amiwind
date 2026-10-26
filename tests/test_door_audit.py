# SPDX-License-Identifier: GPL-3.0-only
"""The door entrance audit (tools/door_audit.py, DOOR-ENTRANCE-AUDIT-51).

The maintainer, 25 October 2026: a mapping tool, per entrance door: is it on the map, does it lead to its place and
back, is it locked. The v0.0.51 image's door table said every door resolves, yet five entrances could not be entered,
so the audit follows the engine's path (aw_scene.c read_links_for, aimed_door; the type 1 crossing window). These
tests hold the engine's bank rules, the map name rule, the lock fields, each check of a door row and the explanation
of a door that cannot be used after a streamed crossing. Synthetic data only."""
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import door_audit  # noqa: E402

MAPS_H = '''
static __inline__ const char *AW_InteriorMapName(int n)
{
    static const char *const names[AW_INTERIOR_MAP_COUNT]={"mi000000000001"};
    return names[n];
}
static __inline__ int AW_MapId(const char *name)
{
    static const char *const names[AW_MAP_COUNT] = {"prison","seyda","census"};
    return -1;
}
'''
TABLE_H = '''
#define AW_TOWN_EXTRA_NAMES {"vivec_city","bcoast_x7y2"}
#define AW_TOWN_INTERIOR_NAMES {\\
    "bmhouse",""\\
}
#define AW_ROOM_BATCH_NAMES {\\
    "ri0123456789","",\\
    "riaaaaaaaaaa"\\
}
'''
NAMES = door_audit.engine_map_names(MAPS_H, TABLE_H)


def row(source, target, ref, mins, maxs, arrival=(0, 0, 0), yaw=90.0, label='A Tomb', sep='\t'):
    return '%s %s %d %s%s%s' % (source, target, ref, ' '.join('%.5f' % v for v in (*mins, *maxs, *arrival, yaw)),
                                sep, label)


class EngineNames(unittest.TestCase):
    def test_every_list_and_the_terrain_rule(self):
        for name in ('seyda', 'mi000000000001', 'vivec_city', 'bmhouse', 'ri0123456789', 'vf0042', 'vf8191'):
            self.assertTrue(door_audit.map_valid(name, NAMES), name)
        for name in ('', 'vf8192', 'vf42', 'ri0000000000', 'nowhere', 'riaaaaaaaaa'):
            self.assertFalse(door_audit.map_valid(name, NAMES), name)


class EngineBank(unittest.TestCase):
    def test_a_good_row_is_kept_with_its_fields(self):
        bank = door_audit.parse_bank('AWD3\n' + row('vf0042', 'ri0123456789', 77, (1, 2, 3), (9, 10, 30)) + '\n',
                                     NAMES)
        self.assertEqual(len(bank['links']), 1)
        link = bank['links'][0]
        self.assertEqual((link['source'], link['target'], link['reference'], link['label']),
                         ('vf0042', 'ri0123456789', 77, 'A Tomb'))
        self.assertEqual(link['maxs'], [9.0, 10.0, 30.0])

    def test_the_rows_the_engine_drops(self):
        text = '\n'.join(['AWD3',
                          row('vf0042', 'nowhere', 1, (0, 0, 0), (8, 8, 8)),
                          row('nowhere', 'ri0123456789', 2, (0, 0, 0), (8, 8, 8)),
                          row('vf0042', 'ri0123456789', 3, (0, 0, 0), (300, 8, 8)),
                          row('vf0042', 'ri0123456789', 4, (0, 0, 0), (8, 8, 8), yaw=360.0),
                          row('vf0042', 'ri0123456789', 5, (0, 0, 0), (8, 8, 8), label='bad\x01label'),
                          'vf0042 ri0123456789 6 1 2 3',
                          row('vf0042', '-', 7, (0, 0, 0), (8, 8, 8))]) + '\n'
        bank = door_audit.parse_bank(text, NAMES)
        self.assertEqual([l['reference'] for l in bank['links']], [7])          # "-": shown, leads nowhere
        reasons = {d['reference']: d['reason'] for d in bank['dropped']}
        self.assertIn('target map nowhere', reasons[1])
        self.assertIn('source map nowhere', reasons[2])
        self.assertIn('side over 256', reasons[3])
        self.assertIn('yaw', reasons[4])
        self.assertIn('control character', reasons[5])
        self.assertIn('14 fields', reasons[6])

    def test_only_the_first_256_rows_are_kept(self):
        rows = [row('vf0042', 'ri0123456789', n, (0, 0, 0), (8, 8, 8)) for n in range(1, 259)]
        bank = door_audit.parse_bank('AWD3\n' + '\n'.join(rows) + '\n', NAMES)
        self.assertEqual(len(bank['links']), 256)
        self.assertEqual([d['reference'] for d in bank['dropped']], [257, 258])

    def test_another_version_keeps_nothing(self):
        self.assertEqual(door_audit.parse_bank('AWD2\n' + row('vf0042', 'seyda', 1, (0, 0, 0), (8, 8, 8)),
                                               NAMES)['links'], [])


class SmallRules(unittest.TestCase):
    def test_crossing_mode_takes_the_last_line(self):
        self.assertEqual(door_audit.crossing_mode('// chim crossing 1 is the default\nchim crossing 1\n'), 1)
        self.assertEqual(door_audit.crossing_mode('chim crossing 1\nchim crossing 0\n'), 0)
        self.assertEqual(door_audit.crossing_mode('bind x y\n'), 0)

    def test_lock_level_and_key(self):
        door = {'original_subrecords': [{'tag': 'FLTV', 'hex': struct.pack('<i', 50).hex()},
                                        {'tag': 'KNAM', 'hex': b'key_tomb\0'.hex()}]}
        self.assertEqual(door_audit.lock_of(door), (50, 'key_tomb'))
        self.assertEqual(door_audit.lock_of({'original_subrecords': []}), (0, ''))

    def test_directory_frame_takes_the_first_row_holding_the_point(self):
        directory = [('vf0001', (1024.0, 1024.0, 0.0), (-1024.0, -1024.0, 1024.0, 1024.0)),
                     ('vf0002', (1024.0, 1024.0, 0.0), (-1024.0, -1024.0, 1024.0, 1024.0)),
                     ('vf0003', (3072.0, 1024.0, 0.0), (-1024.0, -1024.0, 1024.0, 1024.0))]
        self.assertEqual(door_audit.directory_frame(directory, [100, 100])[0], 'vf0001')
        self.assertEqual(door_audit.directory_frame(directory, [3000, 100])[0], 'vf0003')
        self.assertIsNone(door_audit.directory_frame(directory, [9000, 100]))

    def test_room_record_bounds(self):
        from chim.interior import room_record
        data = room_record(((-10.0, -20.0, -30.0), (40.0, 50.0, 60.0)), [], [])
        self.assertEqual(door_audit.room_record_bounds(data), ((-10.0, -20.0, -30.0), (40.0, 50.0, 60.0)))
        with self.assertRaises(ValueError):
            door_audit.room_record_bounds(b'\0' * len(data))

    def test_running_origin(self):
        self.assertEqual(door_audit.running_origin([8192.0, 4096.0, 400.0], [-1024.0, 0.0, 100.0]),
                         [3072.0, 1024.0, 0.0])


# A world of two region frames a cell apart: vf0001 (cell 0,0) and vf0002 (cell 1,0); a door in cell 1,0 into room
# ri0123456789, the room's way out back to it.
DIRECTORY = [('vf0001', (1024.0, 1024.0, 0.0), (-1024.0, -1024.0, 1024.0, 1024.0)),
             ('vf0002', (3072.0, 1024.0, 0.0), (-1024.0, -1024.0, 1024.0, 1024.0))]
DOOR_POS = [12288.0 + 400.0, 4096.0, 800.0]          # cell 1,0; local (100 + 400 / 4 ... ) below
LOCAL = [DOOR_POS[0] * .25 - 3072.0, DOOR_POS[1] * .25 - 1024.0, DOOR_POS[2] * .25]


def original(number, cell, position, destination_cell, destination, interior=False, ident='ex_tomb_door'):
    return {'number': number, 'id': ident, 'model': 'd\\ex_tomb_door.nif', 'source_cell': cell,
            'source_interior': interior, 'source_grid': [1, 0] if not interior else [0, 0], 'position': position,
            'destination_cell': destination_cell, 'destination_interior': bool(destination_cell),
            'destination': {'position': destination, 'rotation_radians': [0, 0, 0]}, 'original_subrecords': []}


class FakeImage:
    def __init__(self, banks, frames, crossing=1, runs=None, rooms=None):
        self.names = NAMES
        self.crossing = crossing
        self.directory = DIRECTORY
        self.frames = frames
        self.leave_margin = 0
        self.banks = banks
        self.runs = runs if runs is not None else {'vf0001', 'vf0002', 'ri0123456789'}
        self.rooms = rooms if rooms is not None else {'ri0123456789': ((-512, -512, -256), (512, 512, 256))}

    def bank(self, name):
        text = self.banks.get(name)
        return (None, None) if text is None else ('doors-%s.txt' % name, door_audit.parse_bank(text, NAMES))

    def map_runs(self, name):
        return name in self.runs and door_audit.map_valid(name, NAMES)

    def room_bounds(self, name):
        return self.rooms.get(name)


def world():
    entrance = original(10, '', DOOR_POS, 'Test Tomb', [0, 0, 0])
    way_out = original(11, 'Test Tomb', [0, 0, 0], '', [DOOR_POS[0] + 200, DOOR_POS[1], DOOR_POS[2]], interior=True)
    rows = [{'reference': 10, 'kind': 'door', 'direction': 'exterior_to_room', 'source': 'vf0002', 'holder': 'region',
             'frame': [3072.0, 1024.0, 0.0], 'target': 'ri0123456789', 'arrival': [0, 0, 20]},
            {'reference': 11, 'kind': 'door', 'direction': 'room_to_exterior', 'source': 'ri0123456789',
             'holder': 'room', 'frame': None, 'target': 'vf0002',
             'arrival': [LOCAL[0] + 50, LOCAL[1], LOCAL[2]]}]
    box = ([LOCAL[0] - 4, LOCAL[1] - 16, LOCAL[2] - 8], [LOCAL[0] + 4, LOCAL[1] + 16, LOCAL[2] + 40])
    banks = {'vf0002': 'AWD3\n' + row('vf0002', 'ri0123456789', 10, *box, arrival=(0, 0, 20)) + '\n',
             'ri0123456789': 'AWD3\n' + row('ri0123456789', 'vf0002', 11, (-8, -8, 0), (8, 8, 40),
                                            arrival=(LOCAL[0] + 50, LOCAL[1], LOCAL[2]), label='Exterior world') + '\n'}
    frames = [{'cell': (1, 0), 'town': None, 'selected': {10}, 'owned': {10: {'origin': list(LOCAL)}},
               'hidden': set()},
              {'cell': (0, 0), 'town': None, 'selected': set(), 'owned': {}, 'hidden': set()}]
    return [entrance, way_out], rows, banks, frames


class DoorRows(unittest.TestCase):
    def test_a_sound_door_is_usable_on_arrival_but_not_after_a_streamed_crossing(self):
        doors, rows, banks, frames = world()
        report = door_audit.audit(doors, rows, FakeImage(banks, frames), {(1, 0): 'Test Region'})
        self.assertEqual(report['counts']['doors'], 1)
        door = report['rows'][0]
        self.assertEqual(door['problems'], [])
        self.assertTrue(all(v == 'yes' for v in door['checks'].values()), door['checks'])
        self.assertEqual(door['usable_on_arrival'], 'yes')
        self.assertEqual(door['walk_in'], door_audit.LEVEL_CHANGE_ONLY)
        self.assertEqual(report['regions']['Test Region']['doors'], 1)
        # type 0 crossings: every crossing is a level change, the door's own bank is the one read
        report = door_audit.audit(doors, rows, FakeImage(banks, frames, crossing=0))
        self.assertEqual(report['rows'][0]['walk_in'], door_audit.WALK_IN)

    def test_each_missing_piece_is_named(self):
        doors, rows, banks, frames = world()
        frames[0]['selected'], frames[0]['owned'] = set(), {}
        banks['vf0002'] = 'AWD3\n' + row('vf0002', 'ri0123456789', 10, (0, 0, 0), (300, 8, 8)) + '\n'
        door = door_audit.audit(doors, rows, FakeImage(banks, frames))['rows'][0]
        self.assertEqual(door['checks']['placed'], 'no')
        self.assertEqual(door['checks']['bank_row'], 'no')
        self.assertTrue(any('does not place the door' in p for p in door['problems']))
        self.assertTrue(any('dropped by the engine' in p for p in door['problems']))
        self.assertEqual(door['usable_on_arrival'], 'no')

    def test_a_box_away_from_the_door_and_a_story_hidden_door(self):
        doors, rows, banks, frames = world()
        frames[0]['hidden'] = {10}
        banks['vf0002'] = 'AWD3\n' + row('vf0002', 'ri0123456789', 10, (0, 0, 0), (8, 8, 8)) + '\n'
        door = door_audit.audit(doors, rows, FakeImage(banks, frames))['rows'][0]
        self.assertEqual(door['checks']['placed'], 'not checked')      # hidden as the original hides it
        self.assertIn('story hidden', door['note'])
        self.assertEqual(door['checks']['use_box'], 'no')

    def test_a_door_placed_away_from_its_original_place(self):
        doors, rows, banks, frames = world()
        frames[0]['owned'][10]['origin'] = [LOCAL[0] + 20, LOCAL[1], LOCAL[2]]
        door = door_audit.audit(doors, rows, FakeImage(banks, frames))['rows'][0]
        self.assertEqual(door['checks']['use_box'], 'no')
        self.assertIn('from its original place', ' '.join(door['problems']))

    def test_a_dead_room_and_a_wrong_way_back(self):
        doors, rows, banks, frames = world()
        image = FakeImage(banks, frames, runs={'vf0001', 'vf0002'})
        door = door_audit.audit(doors, rows, image)['rows'][0]
        self.assertEqual(door['checks']['target_room'], 'no')
        doors, rows, banks, frames = world()
        banks['ri0123456789'] = 'AWD3\n' + row('ri0123456789', 'vf0001', 11, (-8, -8, 0), (8, 8, 40)) + '\n'
        door = door_audit.audit(doors, rows, FakeImage(banks, frames))['rows'][0]
        self.assertEqual(door['checks']['way_back'], 'no')
        self.assertTrue(any('arrives' in p for p in door['problems']))

    def test_arrival_outside_the_room(self):
        doors, rows, banks, frames = world()
        image = FakeImage(banks, frames, rooms={'ri0123456789': ((100, 100, 100), (200, 200, 200))})
        door = door_audit.audit(doors, rows, image)['rows'][0]
        self.assertEqual(door['checks']['arrival_inside'], 'no')

    def test_no_holder(self):
        doors, rows, banks, frames = world()
        rows[0] = {'reference': 10, 'kind': 'door', 'problem': 'its own place is in no frame or room of this image'}
        door = door_audit.audit(doors, rows, FakeImage(banks, frames))['rows'][0]
        self.assertEqual(door['checks']['holder'], 'no')
        self.assertEqual(door['usable_on_arrival'], 'no')

    def test_a_spot_in_a_streamed_frame_is_explained(self):
        doors, rows, banks, frames = world()
        # the player started on vf0001 (cell 0,0) and walked into cell 1,0: the running map keeps vf0001's coordinates
        player_global = [DOOR_POS[0] - 100, DOOR_POS[1], DOOR_POS[2]]
        player_local = [player_global[0] * .25 - 1024.0, player_global[1] * .25 - 1024.0, player_global[2] * .25]
        report = door_audit.audit(doors, rows, FakeImage(banks, frames), spots=[player_global + player_local])
        spot = report['spots'][0]
        self.assertEqual((spot['reference'], spot['running_map'], spot['holder']), (10, 'vf0001', 'vf0002'))
        self.assertIn('streamed frame', spot['reasons'][0])
        self.assertIn('does not exist', spot['reasons'][0])
        self.assertLess(spot['player_to_box'], door_audit.REACH)      # the player stood at the door


class SourceFrames(unittest.TestCase):
    def test_the_frames_of_a_manifest_as_dumps_writes_it(self):
        doc = {'areas': ['seyda', 'rcp1_p0'], 'frames': [
            {'cell': [-2, -9], 'town': 'seyda', 'placements': [{'cell': [-2, -9], 'ref': 5}],
             'frame_ownership': {'pieces': [{'cell': [-2, -9], 'origin': [1.5, 2.5, 3.5], 'ref': 5,
                                             'story_hidden': True, 'yaw': 0.0}]}},
            {'cell': [1, 0], 'placements': [{'cell': [1, 0], 'ref': 10}, {'cell': [1, 0], 'ref': 11 | (3 << 24)}],
             'frame_ownership': {'pieces': [{'cell': [1, 0], 'origin': [-7.0, 8.0, 9.0], 'ref': 10,
                                             'story_hidden': False, 'yaw': 90.0}]},
             'story_hidden': [12], 'town': 'rcp1_p0'}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'chim-source.json'
            path.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n', encoding='utf-8')
            frames = door_audit.source_frames(path, jobs=2)
        self.assertEqual([(f['cell'], f['town']) for f in frames], [((-2, -9), 'seyda'), ((1, 0), 'rcp1_p0')])
        self.assertTrue(frames[0]['owned'][5]['story_hidden'])
        self.assertEqual(frames[1]['owned'][10]['origin'], [-7.0, 8.0, 9.0])
        self.assertNotIn('story_hidden', frames[1]['owned'][10])
        self.assertEqual(frames[1]['selected'], {10, 11})        # a cut piece counts as its source reference
        self.assertEqual(frames[1]['hidden'], {12})
        # a region frame's "town" field is its frame id (chim-regions.json)
        self.assertIs(door_audit.holder_frame(frames, 'region', None, [1, 0], {(1, 0): 'rcp1_p0'}), frames[1])
        self.assertIsNone(door_audit.holder_frame(frames, 'region', None, [1, 0], {(1, 0): 'rcp9_p9'}))
        self.assertIs(door_audit.holder_frame(frames, 'town', 'seyda', [-2, -9]), frames[0])


if __name__ == '__main__':
    unittest.main()
