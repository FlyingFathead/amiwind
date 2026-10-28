# SPDX-License-Identifier: GPL-3.0-only
"""tools/door_engine_check.py (DOOR-ENTRANCE-AUDIT-51, DOOR-BANK-STREAMED-FRAME-51): the engine's own door code over a
small image of two region frames and one room. A door of the second frame, walked into from the first: its prompt, the
use key and a script's Activate lead into the room, and the room's exit back out. The same image through a scene code
that reads the running map's door bank only (the v0.0.52 engine's rule) uses no door after walking in: the check finds
the bug the maintainer's five dead entrances came from."""
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]
import door_audit  # noqa: E402
import door_engine_check  # noqa: E402
from chim.frame_map import world_directory  # noqa: E402

SRC = ROOT / 'engine/aga/src'
NAMES = door_audit.engine_map_names((SRC / 'aw_maps.h').read_text(encoding='utf-8'),
                                    (SRC / 'aw_town_table.h').read_text(encoding='utf-8'))
ROOM = sorted(NAMES['room_batch'])[0]      # a room map the engine knows (a room batch's, aw_town_table.h)


def chim_map(text):
    """A map file the engine sizes and reads the worldspawn of: the BSP29 header, then the entity lump."""
    data = text.encode('ascii')
    header = bytearray(124)
    struct.pack_into('<iii', header, 0, 29, 124, len(data))
    return bytes(header) + data


def directory(rows):
    """world/regions.awr (AWR2): two town slots far away, then the region rows (name, origin, core, cover)."""
    raw = bytearray(b'AWR2' + struct.pack('<I', len(rows)))
    for _ in range(2):
        raw += struct.pack('<7f', 500000, 500000, 0, -1024, -1024, 1024, 1024)
    for i, (origin, core) in enumerate(rows):
        cover = (core[0] - 1024, core[1] - 1024, core[2] + 1024, core[3] + 1024)
        raw += ('vf%04d' % i).encode('ascii') + b'\0\0' + struct.pack('<3f4f4f', *origin, *core, *cover)
    return bytes(raw)


def image(tmp):
    id1 = Path(tmp) / 'id1'
    (id1 / 'maps').mkdir(parents=True)
    (id1 / 'world').mkdir()
    # vf0000 at the origin, vf0001 2048 units east: one core each, 2048 wide
    (id1 / 'world/regions.awr').write_bytes(directory([((0, 0, 0), (-1024, -1024, 1024, 1024)),
                                                       ((2048, 0, 0), (-1024, -1024, 1024, 1024))]))
    for name in ('vf0000', 'vf0001'):
        (id1 / 'maps' / (name + '.chim')).write_bytes(chim_map('{\n"classname" "worldspawn"\n}\n'))
    (id1 / 'maps' / (ROOM + '.chim')).write_bytes(chim_map(
        '{\n"classname" "worldspawn"\n"message" "Test Tomb"\n}\n'
        '{\n"classname" "info_player_start"\n"origin" "0 0 30"\n}\n'))
    # vf0001's door at its (0, 0), the room's exit at (0, 100) leading back in front of the door
    (id1 / 'doors-vf0001.txt').write_bytes(('AWD3\nvf0001 %s 10 -5 -5 0 5 5 50 0 0 30 0\tTest Tomb\n' % ROOM)
                                           .encode('cp1252'))
    (id1 / ('doors-%s.txt' % ROOM)).write_bytes(('AWD3\n%s vf0001 11 -5 95 0 5 105 50 -40 0 30 0\tExit\n' % ROOM)
                                                .encode('cp1252'))
    return id1


def rows():
    """The door audit's row of the door (the fields the check reads)."""
    return [{'reference': 10, 'id': 'ex_test_door', 'cell': [1, 0], 'region': 'Test Region',
             'destination_cell': 'Test Tomb', 'holder': 'vf0001', 'holder_kind': 'region', 'locked': 'no',
             'lock_level': 0, 'key': '', 'exit_reference': 11, 'checks': {'placed': 'yes'},
             'bank': {'box': [[-5, -5, 0], [5, 5, 50]], 'target': ROOM, 'arrival': [0, 0, 30]}}]


@unittest.skipUnless(shutil.which(os.environ.get('CC', 'cc')), 'a host C compiler builds the engine check')
class DoorEngineCheck(unittest.TestCase):
    def check(self, scene_source=None):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = image(tmp)
            source = None
            if scene_source:
                source = Path(tmp) / 'aw_scene.c'
                source.write_text(scene_source, encoding='utf-8')
            return door_engine_check.check(rows(), id1, SRC, world_directory(id1), NAMES, jobs=1,
                                           scene_source=source)

    def test_a_door_after_walking_into_its_frame_leads_in_and_back_out(self):
        report = self.check()
        entry = report['entries'][0]
        self.assertTrue(entry['job'].startswith('D 10 vf0001 ') and ' W vf0000 ' in entry['job'], entry['job'])
        self.assertEqual(entry['result']['scene_after_crossing'], 'vf0001', entry)
        self.assertEqual(entry['result']['prompt'], '(Enter: E)', entry)
        self.assertEqual(entry['result']['name'], 'Test Tomb')
        self.assertEqual((entry['result']['use'], entry['result']['activate']), (ROOM, ROOM))
        self.assertEqual(entry['result']['back'], 'vf0001')
        self.assertEqual((entry['usable'], entry['both_ways']), ('yes', 'yes'), entry['reasons'])
        self.assertEqual(report['counts']['usable_after_crossing'], 1)

    def test_the_running_maps_bank_only_uses_no_door_after_walking_in(self):
        # the v0.0.52 rule (DOOR-BANK-STREAMED-FRAME-51): the door bank and the eye of the running map, not of the
        # frame the player stands in
        text = (SRC / 'aw_scene.c').read_text(encoding='utf-8')
        old = text.replace('static const char *door_scene(void){return logical_map[0]?logical_map:sv.name;}',
                           'static const char *door_scene(void){return sv.name;}')
        old = old.replace('if(logical_map[0]){VectorCopy(logical_offset,shift);}', 'if(0){}')
        self.assertNotEqual(old, text)
        entry = self.check(old)['entries'][0]
        self.assertEqual(entry['result']['scene_after_crossing'], 'vf0001')   # the crossing itself streams
        self.assertEqual(entry['usable'], 'no')
        self.assertIn("the prompt is '-'", entry['reasons'])

    def test_the_use_box_hit_is_the_engines(self):
        # aw_scene.c door_hit: the slab entry within the 56-unit reach, None past it or beside the box
        box = ([-5, 30, 0], [5, 40, 50])
        self.assertEqual(door_engine_check.door_hit(*box, [0, 0, 25], [0, 1, 0]), [0, 30, 25])
        self.assertIsNone(door_engine_check.door_hit(*box, [0, -30, 25], [0, 1, 0]))      # 60 units: out of reach
        self.assertIsNone(door_engine_check.door_hit(*box, [20, 0, 25], [0, 1, 0]))       # beside it
        self.assertEqual(door_engine_check.door_hit(*box, [0, 35, 25], [0, 1, 0]), [0, 35, 25])   # inside it
        # the engine's own reach and wall slack, as the check uses them
        scene = (SRC / 'aw_scene.c').read_text(encoding='utf-8')
        self.assertIn('float near=0,far=56', scene)
        self.assertIn('(1-tr.fraction)*distance>(links[i].bounds?DOOR_USE_SLACK:12.0f)', scene)
        # DOOR-USE-BLOCKED-53: the doorway a door is set in may close it up to 11 units in front; the check reads the
        # engine's own value
        self.assertEqual(door_engine_check.use_slack(SRC), 16.0)

    def test_a_baseline_only_lets_the_usable_count_go_up(self):
        report = {'counts': {'doors': 1102, 'usable_after_crossing': 1101, 'both_ways': 1101}}
        baseline = {'format': door_engine_check.BASELINE_FORMAT, 'doors': 1102, 'usable_after_crossing': 1102,
                    'both_ways': 1101}
        self.assertIn('usable_after_crossing 1101 < 1102', door_engine_check.baseline_problem(report, baseline))
        report['counts']['usable_after_crossing'] = 1102
        self.assertIsNone(door_engine_check.baseline_problem(report, baseline))
        # a partial-area image (fewer entrances) is not compared
        self.assertIsNone(door_engine_check.baseline_problem({'counts': {'doors': 40, 'usable_after_crossing': 3,
                                                                          'both_ways': 3}}, baseline))
        # every door of the original is checked, but a MiniWind image's frames hold only a few of them
        self.assertIsNone(door_engine_check.baseline_problem({'counts': {'doors': 1102, 'held': 40,
                                                                          'usable_after_crossing': 3,
                                                                          'both_ways': 3}}, baseline))
        report['counts']['held'] = 1102
        report['counts']['usable_after_crossing'] = 1101
        self.assertIsNotNone(door_engine_check.baseline_problem(report, baseline))
        # the repository's baseline is the format the check reads
        saved = json.loads((ROOT / 'config/door-check-baseline.json').read_text(encoding='utf-8'))
        self.assertEqual(saved['format'], door_engine_check.BASELINE_FORMAT)
        self.assertLessEqual(saved['both_ways'], saved['usable_after_crossing'])
        self.assertLessEqual(saved['usable_after_crossing'], saved['doors'])


class KnownEntrances(unittest.TestCase):
    """config/door-check-known.json (DOOR-USE-COLLISION-FILLED-53): over all entrances of a whole-world image, every
    entrance the wall check cannot reach must be listed with its reason and class; no compiler needed."""

    @staticmethod
    def report(reach, held=1102):
        entries = [{'reference': ref, 'id': 'ex_test_door', 'destination_cell': 'Test Tomb %d' % ref,
                    'checks': {'reach': r}, 'reach': {'reach': r, 'why': 'test'}} for ref, r in reach.items()]
        return {'counts': {'doors': 1102, 'held': held, 'reach_traced': len(reach), 'usable_after_crossing': 1102,
                           'both_ways': 1102, 'reachable': 1102}, 'entries': entries}

    BASELINE = {'format': door_engine_check.BASELINE_FORMAT, 'doors': 1102}

    def test_an_unlisted_unreachable_entrance_fails_a_whole_world_image(self):
        known = {7: {'reason': 'measured', 'class': 'TEST-1'}}
        report = self.report({5: 'no', 6: 'yes', 7: 'no', 8: 'yes'})
        self.assertEqual(door_engine_check.known_split(report, known),
                         {'known': [7], 'new': [5], 'known_passing': []})
        problem = door_engine_check.known_problem(report, self.BASELINE, known)
        self.assertIn('1 exterior entrances cannot be reached', problem)
        self.assertIn('5 ex_test_door -> Test Tomb 5', problem)
        # listed: no problem; a listed entrance reached again is named, never a failure
        known[5] = {'reason': 'measured', 'class': 'TEST-1'}
        known[8] = {'reason': 'measured', 'class': 'TEST-1'}
        self.assertIsNone(door_engine_check.known_problem(report, self.BASELINE, known))
        self.assertEqual(door_engine_check.known_split(report, known)['known_passing'], [8])

    def test_partial_images_and_untraced_walls_are_not_compared(self):
        report = self.report({5: 'no'}, held=40)
        self.assertIsNone(door_engine_check.known_problem(report, self.BASELINE, {}))
        report = self.report({5: 'no'})
        report['counts']['reach_traced'] = 0
        self.assertIsNone(door_engine_check.known_problem(report, self.BASELINE, {}))
        # no known list given: the baseline alone decides (the check before v0.0.54)
        self.assertIsNone(door_engine_check.known_problem(self.report({5: 'no'}), self.BASELINE, None))

    def test_the_repository_list_is_the_format_the_check_reads(self):
        path = ROOT / 'config/door-check-known.json'
        known = door_engine_check.load_known(path)
        for ref, row in known.items():
            self.assertIsInstance(ref, int)
            self.assertTrue(row['reason'] and row['class'] and row.get('place'), ref)
        baseline = json.loads((ROOT / 'config/door-check-baseline.json').read_text(encoding='utf-8'))
        self.assertLessEqual(baseline['reachable'] + len(known), baseline['doors'])
        # the image step passes the list to the check (tools/build_aga.py write_door_check)
        text = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn("known = ROOT/'config'/'door-check-known.json'", text)
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / 'known.json'
            bad.write_text(json.dumps({'format': door_engine_check.KNOWN_FORMAT,
                                       'entrances': {'12': {'class': 'TEST-1'}}}), encoding='utf-8')
            with self.assertRaises(ValueError):
                door_engine_check.load_known(bad)


if __name__ == '__main__':
    unittest.main()
