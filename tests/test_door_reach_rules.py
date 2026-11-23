# SPDX-License-Identifier: GPL-3.0-only
"""The door check's reach rules for the entrances the expansions brought (DOOR-USE-COLLISION-EXPANSIONS-68,
DOOR-CHECK-NO-SWIM-CASE-68): tools/door_engine_check.py _reach_unit on small made-up frames (a flat ground, a water
level, solid boxes for placements; the standing hull and the point hull as the engine's), and tools/script_stages.py
on scripts of the stage form. Each rule is a door the check could not reach before:
  - a door set into a slope (its box reaches deep under the ground in front of it): used from the floor its own way
    out leads onto, the spot the game puts a player walking out of the room, inside the frame's core and within the
    original's reach (the rule play has shown, on by default);
  - a trapdoor: the use box is the engine's own (the box as the bank holds it), stood at from its top;
  - an entrance under water (the threshold far under the water, the ground in front over every spot near it): the
    player swims to it and uses it from the water (the rule 'swim', off until play shows it);
  - a placement a script hides while the door is shown (a colony's earlier stage, a quest's plug): left out of that
    door's way, at a moment the door's own stage allows; a placement shown with the door stays in the way (the rule
    'stages', off until play shows it)."""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
if str(ROOT / 'tests') not in sys.path:
    sys.path.append(str(ROOT / 'tests'))     # the engine check's own fixture (test_door_engine_check)
import door_engine_check as D  # noqa: E402
import script_stages as S  # noqa: E402

HALF = (7.32, 7.12, 16.625)     # tools/player_hull.py MAXS: the standing hull's half size


class FakeScene:
    """A frame of a flat ground (solid under GROUND), the terrain's water up to WATER, and solid boxes (placements),
    traced as chim.collision.FrameScene traces: hull 1 grows every solid by the standing hull, hull 0 does not."""

    def __init__(self, world, index, hull=1):
        _path, frame, chunks = world['frames'][index]
        grow = HALF if hull == 1 else (0.0, 0.0, 0.0)
        self.ground = frame['ground'] + grow[2]
        self.water = frame['water']
        self.raw_ground = frame['ground']
        self.boxes = [(r['ref'], [r['box'][0][k] - grow[k] for k in range(3)],
                       [r['box'][1][k] + grow[k] for k in range(3)]) for c in chunks for r in c['owned']]

    def contents(self, p):
        return -2 if p[2] < self.raw_ground else D.CONTENTS_WATER if p[2] < self.water else -1

    def trace(self, start, end):
        best = None
        if start[2] < self.ground:
            best = {'fraction': 0.0, 'normal': (0.0, 0.0, 1.0), 'reference': 'chunk 0,0'}
        elif end[2] < self.ground:
            best = {'fraction': (start[2] - self.ground) / (start[2] - end[2]), 'normal': (0.0, 0.0, 1.0),
                    'reference': 'chunk 0,0'}
        for ref, lo, hi in self.boxes:
            near, far, normal = 0.0, 1.0, None
            for k in range(3):
                d = end[k] - start[k]
                if abs(d) < 1e-9:
                    if not lo[k] <= start[k] <= hi[k]:
                        near = 2.0
                        break
                    continue
                a, b = (lo[k] - start[k]) / d, (hi[k] - start[k]) / d
                n = [0.0, 0.0, 0.0]
                n[k] = -1.0 if d > 0 else 1.0
                if a > b:
                    a, b = b, a
                if a > near:
                    near, normal = a, tuple(n)
                far = min(far, b)
            if near <= far and near <= 1.0 and (best is None or near < best['fraction']):
                best = {'fraction': near, 'normal': normal or (0.0, 0.0, 1.0), 'reference': ref}
        return best


def run_unit(doors, ground, water=-4096.0, boxes=(), rules=D.ALL_RULES):
    """_reach_unit over one made-up frame, judged by RULES."""
    row = ('fake', {'ground': ground, 'water': water}, [{'owned': [{'ref': ref, 'box': box} for ref, box in boxes]}])
    with mock.patch('chim.collision.FrameScene', FakeScene), \
            mock.patch('chim.validate.load_frame', lambda world_dir, index: (row, {})):
        return D._reach_unit(('fake', 0, doors, 16.0, tuple(rules)))


class Rules(unittest.TestCase):
    def test_only_the_rules_play_has_shown_are_on_by_default(self):
        # the walk-out arrival: six entrances of Solstheim entered in play on the v0.0.68-dev8 image; the swim rule: the
        # three doors under water entered by swimming on the same image (gated engine of 4974f47ac); the stage and
        # doorway rules wait for play
        self.assertEqual(D.RULES, ('walk_out', 'swim'))
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('AMIWIND_DOOR_CHECK_RULES', None)
            self.assertEqual(D.active_rules(), ('walk_out', 'swim'))
            os.environ['AMIWIND_DOOR_CHECK_RULES'] = 'walk_out'
            self.assertEqual(D.active_rules(), ('walk_out',))
            os.environ['AMIWIND_DOOR_CHECK_RULES'] = ''
            self.assertEqual(D.active_rules(), ())
            os.environ['AMIWIND_DOOR_CHECK_RULES'] = 'fly'
            with self.assertRaises(ValueError):
                D.active_rules()
        self.assertEqual(D.active_rules(('stages',)), ('stages',))

    def test_a_door_under_water_is_used_swimming_by_default(self):
        # DOOR-CHECK-NO-SWIM-CASE-68: on by default since play showed it; without the rule the door has no spot
        box = [[-24.0, -40.0, -600.0], [24.0, 40.0, -460.0]]
        got = run_unit([(1, box, (40.0, 0.0))], ground=-515.0, water=0.0, rules=D.RULES)[1]
        self.assertEqual((got['reach'], got.get('swimming')), ('yes', 'yes'), got)
        got = run_unit([(1, box, (40.0, 0.0))], ground=-515.0, water=0.0, rules=('walk_out',))[1]
        self.assertEqual(got['reach'], 'no', got)


# a door 134 units high whose thin side faces +x, the use reach out from its face at +x
CAVE = [[-24.0, -40.0, 0.0], [24.0, 40.0, 134.0]]


class SwimRule(unittest.TestCase):
    def test_an_entrance_under_water_is_used_swimming(self):
        # the threshold 600 under the water, the ground 85 over it: no spot within 80 over the threshold is open
        box = [[-24.0, -40.0, -600.0], [24.0, 40.0, -460.0]]
        got = run_unit([(1, box, (40.0, 0.0))], ground=-515.0, water=0.0)[1]
        self.assertEqual(got['reach'], 'yes', got)
        self.assertEqual(got.get('swimming'), 'yes', got)
        # the same door on dry land: no water to swim in, no spot
        got = run_unit([(1, box, (40.0, 0.0))], ground=-515.0, water=-4096.0)[1]
        self.assertEqual(got['reach'], 'no', got)
        self.assertIn('no standing spot', got['why'])

    def test_a_player_in_the_water_floats_where_it_is(self):
        # stand_at: a start whose origin is in the terrain's water is where the swimmer stays (sv_phys.c
        # SV_CheckWater waterlevel 2: no gravity), not dropped onto the bottom far below
        box = [[-5.0, -24.0, -300.0], [5.0, 24.0, -250.0]]
        got = run_unit([(1, box, (40.0, 0.0))], ground=-1000.0, water=0.0)[1]
        self.assertEqual((got['reach'], got.get('swimming')), ('yes', 'yes'), got)


class WalkOutRule(unittest.TestCase):
    def test_a_door_set_into_a_slope_is_used_from_its_walk_out_arrival(self):
        # the ground in front lies 110 over the box floor: the door's lower part is in the rock
        door = (1, CAVE, (40.0, 20.0), [40.0, 20.0, 150.0])
        got = run_unit([door], ground=110.0)[1]
        self.assertEqual((got['reach'], got.get('stands')), ('yes', 'at the walk-out arrival'), got)
        self.assertGreater(got['ground_over_threshold'], 80)
        # without the arrival (the check before): no spot
        got = run_unit([door[:3]], ground=110.0)[1]
        self.assertEqual(got['reach'], 'no', got)
        self.assertIn('no standing spot', got['why'])

    def test_an_arrival_too_far_from_the_door_reaches_it_on_its_way_in(self):
        door = (1, CAVE, (40.0, 20.0), [110.0, 50.0, 150.0])
        got = run_unit([door], ground=110.0)[1]
        self.assertEqual((got['reach'], got.get('stands')), ('yes', 'on the way from the walk-out arrival'), got)

    def test_an_arrival_inside_a_wall_is_named(self):
        wall = (7, [[30.0, -80.0, 100.0], [80.0, 80.0, 400.0]])
        door = (1, CAVE, (40.0, 20.0), [40.0, 20.0, 150.0])
        got = run_unit([door], ground=110.0, boxes=[wall])[1]
        self.assertEqual(got['reach'], 'no', got)
        self.assertEqual(got['walk_out'], 'the walk-out arrival has no floor a player stands on')

    def test_a_walk_out_spot_outside_the_frames_core_does_not_count(self):
        # the engine reads the door bank of the frame the player stands in (Mournhold's ladder: its arrival lies across
        # the frame edge, and in play the use key did nothing there)
        door = (1, CAVE, (40.0, 20.0), [40.0, 20.0, 150.0], None, (-1024.0, -1024.0, 10.0, 1024.0))
        got = run_unit([door], ground=110.0, rules=D.RULES)[1]
        self.assertEqual(got['reach'], 'no', got)
        self.assertIn('outside the frame\'s core', got['walk_out'])
        door = door[:5] + ((-1024.0, -1024.0, 1024.0, 1024.0),)
        got = run_unit([door], ground=110.0, rules=D.RULES)[1]
        self.assertEqual(got['reach'], 'yes', got)

    def test_a_door_in_the_neighbours_bank_is_used_from_the_neighbours_core(self):
        # DOOR-USE-ACROSS-FRAME-EDGE-68: Mournhold's ladder (mh0005) is written into mh0004's bank too (a border copy);
        # the engine reads the bank of the frame the player stands in, so its walk-out arrival in mh0004 counts, as play
        # on the v0.0.68-dev8 image showed (entered from there, 48.8 units off). Before: refused as outside the core.
        frames = {'mh0004': (-7168.0, -60416.0, 0.0), 'mh0005': (-5120.0, -60416.0, 0.0),
                  'mh0006': (-3072.0, -60416.0, 0.0), 'sl0001': (-41984.0, 52224.0, 0.0)}
        cores = {n: (-1024.0, -1024.0, 1024.0, 1024.0) for n in frames}
        banks = {'mh0004': {'links': [{'reference': 4218838}]}, 'mh0006': {'links': [{'reference': 7}]},
                 'sl0001': {'links': [{'reference': 4218838}]}}
        got = D.copy_cores(4218838, 'mh0005', frames, cores, banks.get)
        self.assertEqual(got, [(-3072.0, -1024.0, -1024.0, 1024.0)])        # mh0004 in mh0005's coordinates only
        self.assertEqual(D.copy_cores(4218838, 'mh0006', frames, cores, banks.get), [])    # two frames away
        self.assertEqual(D.door_cores((-1.0, -2.0, 3.0, 4.0)), ((-1.0, -2.0, 3.0, 4.0),))
        self.assertEqual(D.door_cores([(-1.0, -2.0, 3.0, 4.0), (5.0, 6.0, 7.0, 8.0)]),
                         ((-1.0, -2.0, 3.0, 4.0), (5.0, 6.0, 7.0, 8.0)))
        self.assertEqual(D.door_cores(None), ())
        # the walk-out spot outside the door frame's core but inside the core of a frame holding the copy: used
        door = (1, CAVE, (40.0, 20.0), [40.0, 20.0, 150.0], None,
                [(-1024.0, -1024.0, 10.0, 1024.0), (10.0, -1024.0, 2058.0, 1024.0)])
        got = run_unit([door], ground=110.0, rules=D.RULES)[1]
        self.assertEqual((got['reach'], got.get('stands')), ('yes', 'at the walk-out arrival'), got)

    def test_the_arrival_across_the_frame_edge_is_moved_into_the_doors_frame(self):
        origins = {'mh0004': (2048.0, 0.0, 0.0), 'mh0005': (0.0, 0.0, 0.0)}
        self.assertEqual(D.walk_out_spot({'target': 'mh0004', 'arrival': [1005.25, -69.0, 138.25]}, 'mh0005',
                                         origins), [3053.25, -69.0, 138.25])
        self.assertEqual(D.walk_out_spot({'target': 'mh0005', 'arrival': [1.0, 2.0, 3.0]}, 'mh0005', origins),
                         [1.0, 2.0, 3.0])
        self.assertIsNone(D.walk_out_spot({'target': 'ri0000', 'arrival': [1.0, 2.0, 3.0]}, 'mh0005', origins))


class TrapdoorBox(unittest.TestCase):
    def test_a_trapdoor_is_used_through_the_engines_own_box(self):
        # the trapdoor's box as the bank holds it, 2.8 high; the arrival on the ground 24 under it, 66 away
        box = [[-11.3, -11.3, 0.0], [11.3, 11.3, 2.8]]
        eye = [-29.0, 60.0, -24.0 + D.HULL_FEET + D.VIEW]
        aim = [0.0, 0.0, 1.4]
        d = [aim[k] - eye[k] for k in range(3)]
        n = sum(v * v for v in d) ** .5
        forward = [v / n for v in d]
        # the engine's box: met within its reach; the box flattened to its top (the check before) is not met
        self.assertIsNotNone(D.door_hit(box[0], box[1], eye, forward))
        self.assertIsNone(D.door_hit([box[0][0], box[0][1], box[1][2]], box[1], eye, forward))
        # but not within the original's reach from a spot the player is put at: Rimhull's trapdoor, 54 from its
        # walk-out arrival, showed no prompt there in play; the way in from it, 28 nearer, serves
        self.assertIsNone(D.door_hit(box[0], box[1], eye, forward, D.WALK_OUT_REACH))
        got = run_unit([(1, box, (-29.0, 60.0), [-29.0, 60.0, -6.0])], ground=-24.0, rules=D.RULES)[1]
        self.assertEqual((got['reach'], got.get('stands')), ('yes', 'on the way from the walk-out arrival'), got)


DOOR_STAGE = ('colonystate', frozenset({35.0}), frozenset({0.0, 34.0, 36.0}))


class StageRule(unittest.TestCase):
    # a block filling the room in front of the door (and its arrival)
    BLOCK = [[6.0, -80.0, 0.0], [120.0, 80.0, 90.0]]

    def door(self, switched):
        return (1, [[-5.0, -24.0, 0.0], [5.0, 24.0, 50.0]], (40.0, 0.0), [40.0, 0.0, 20.0], (DOOR_STAGE, switched))

    def test_a_placement_hidden_while_the_door_is_shown_is_left_out(self):
        tree = ('colonystate', frozenset({0.0, 34.0}), frozenset({0.0, 34.0, 35.0, 36.0}))
        got = run_unit([self.door({9: tree})], ground=0.0, boxes=[(9, self.BLOCK)])[1]
        self.assertEqual(got['reach'], 'yes', got)
        self.assertIn('colonystate at 35', got['stage'])
        self.assertIn('9 left out', got['stage'])
        # without the stages (the check before): the block is in the way
        got = run_unit([self.door({9: tree})[:4]], ground=0.0, boxes=[(9, self.BLOCK)])[1]
        self.assertEqual(got['reach'], 'no', got)

    def test_a_placement_shown_with_the_door_stays_in_its_way(self):
        house = ('colonystate', frozenset({35.0, 36.0}), frozenset({0.0, 34.0}))
        got = run_unit([self.door({9: house})], ground=0.0, boxes=[(9, self.BLOCK)])[1]
        self.assertEqual(got['reach'], 'no', got)
        self.assertNotIn('stage', got)
        # never switched by a script: never left out
        got = run_unit([self.door({})], ground=0.0, boxes=[(9, self.BLOCK)])[1]
        self.assertEqual(got['reach'], 'no', got)

    def test_a_plug_whose_stage_is_not_read_is_left_out_alone(self):
        got = run_unit([self.door({9: None, 10: None})], ground=0.0,
                       boxes=[(9, self.BLOCK), (10, [[300.0, 300.0, 0.0], [320.0, 320.0, 10.0]])])[1]
        self.assertEqual(got['reach'], 'yes', got)
        self.assertEqual(got['stage'], 'placement 9 alone, which a script hides at some point: 9 left out')


# scripts of the stage form, written for these tests
STAGE_SCRIPT = '''Begin test_stage_house
short once
if ( GetDisabled == 0 )
    if ( TestState < 3 )
        Disable
    endif
endif
if ( GetDisabled == 1 )
    if ( TestState >= 3 )
        Enable
    endif
endif
if ( once == 0 )
    if ( GetJournalIndex "TEST_Q" >= 10 )
        Lock 50
        set once to 1
    endif
endif
End'''
STAGE_ONCE = '''Begin test_stage_site
if ( GetDisabled == 0 )
    if ( TestState == 2 )
        Disable
    elseif ( TestState == 5 )
        Disable
    endif
endif
End'''
PLUG = '''Begin test_plug
if ( GetDisabled == 0 )
    if ( GetJournalIndex "TEST_Q" >= 20 )
        Disable
    endif
endif
End'''


class ScriptStages(unittest.TestCase):
    GLOBALS = {'teststate'}

    def stage(self, text, domain=(0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0)):
        return S.stage_of(S.program(text, self.GLOBALS), domain)

    def test_the_stage_form_gives_the_values_a_placement_is_shown_and_hidden_at(self):
        name, shown, hidden = self.stage(STAGE_SCRIPT)
        self.assertEqual(name, 'teststate')
        self.assertEqual(sorted(shown), [3.0, 4.0, 5.0, 6.0])
        self.assertEqual(sorted(hidden), [0.0, 1.0, 2.0])
        # a placement its script hides for good at 2 or 5 (never shown again once hidden)
        name, shown, hidden = self.stage(STAGE_ONCE)
        self.assertEqual(sorted(shown), [0.0, 1.0, 3.0, 4.0, 6.0])
        self.assertEqual(sorted(hidden), [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0])

    def test_a_toggle_under_a_condition_not_read_has_no_stage(self):
        with self.assertRaises(S.Unknown):
            S.program(PLUG, self.GLOBALS)
        # and a script that never switches its own object is always shown
        self.assertIs(S.program('Begin x\nMessageBox "hello"\nEnd', self.GLOBALS), S.ALWAYS)
        # a local the toggles read, set under a condition not read: no stage
        with self.assertRaises(S.Unknown):
            S.program('Begin x\nshort ok\nif ( GetJournalIndex "Q" >= 5 )\nset ok to 1\nendif\n'
                      'if ( ok == 1 )\nDisable\nendif\nEnd', self.GLOBALS)

    def test_the_moments_a_door_is_tried_at(self):
        door = ('teststate', frozenset({3.0, 4.0}), frozenset({0.0}))
        near = {7: ('teststate', frozenset({0.0, 1.0}), frozenset({3.0, 4.0})),
                8: ('teststate', frozenset({4.0}), frozenset({3.0})), 9: None, 10: S.ALWAYS}
        got = S.moments(door, near)
        self.assertEqual(got[0], ('with teststate at 3, the placements its scripts hide then', [7, 8]))
        self.assertEqual(got[1], ('with teststate at 4, the placements its scripts hide then', [7]))
        self.assertEqual(got[2], ('placement 9 alone, which a script hides at some point', [9]))
        self.assertTrue(all(10 not in refs for _, refs in got))
        # a door always shown: every value at which one of them is hidden
        got = S.moments(S.ALWAYS, {7: near[7]})
        self.assertEqual([refs for _, refs in got], [[7]])


class FakeStages:
    def __init__(self, switched):
        self.switched = switched

    def of_record(self, ident):
        return S.ALWAYS


@unittest.skipUnless(shutil.which(os.environ.get('CC', 'cc')), 'a host C compiler builds the engine check')
class OneDoorwayTwoDoors(unittest.TestCase):
    """Two load doors in one doorway, one per stage (Raven Rock's colony houses, a Skaal hut that becomes another
    house): the engine takes the one that is on (DOOR-LOAD-DISABLED-STILL-USED-68); the check's engine run switches
    the other off for each door's own job, else the doorway's first door answers for both."""

    def check(self, stages):
        import test_door_engine_check as T
        rooms = sorted(T.NAMES['room_batch'])[:2]
        with tempfile.TemporaryDirectory() as tmp:
            id1 = T.image(tmp)
            (id1 / 'maps' / (rooms[1] + '.chim')).write_bytes(T.chim_map(
                '{\n"classname" "worldspawn"\n"message" "Test Hall"\n}\n'
                '{\n"classname" "info_player_start"\n"origin" "0 0 30"\n}\n'))
            (id1 / 'doors-vf0001.txt').write_bytes((
                'AWD3\nvf0001 %s 10 -5 -5 0 5 5 50 0 0 30 0\tTest Tomb\n'
                'vf0001 %s 12 -5 -5 0 5 5 50 0 0 30 0\tTest Hall\n' % tuple(rooms)).encode('cp1252'))
            (id1 / ('doors-%s.txt' % rooms[1])).write_bytes(
                ('AWD3\n%s vf0001 13 -5 95 0 5 105 50 -40 0 30 0\tExit\n' % rooms[1]).encode('cp1252'))
            row = dict(T.rows()[0], reference=12, exit_reference=13, destination_cell='Test Hall',
                       bank={'box': [[-5, -5, 0], [5, 5, 50]], 'target': rooms[1], 'arrival': [0, 0, 30]})
            from chim.frame_map import world_directory
            report = D.check([row], id1, T.SRC, world_directory(id1), T.NAMES, jobs=1, stages=stages,
                             rules=D.ALL_RULES)
        return report['entries'][0], rooms

    def test_each_door_of_a_doorway_is_run_with_the_others_off(self):
        entry, rooms = self.check(FakeStages({10: ('g', frozenset({1.0}), frozenset({0.0, 2.0})),
                                              12: ('g', frozenset({2.0}), frozenset({0.0, 1.0}))}))
        self.assertIn(' X 10', entry['job'])
        self.assertEqual(entry['result']['use'], rooms[1], entry)
        self.assertEqual(entry['usable'], 'yes', entry['reasons'])
        # without the stages (the check before): the doorway's first door answers
        entry, rooms = self.check(None)
        self.assertNotIn(' X ', entry['job'])
        self.assertEqual(entry['result']['use'], rooms[0], entry)
        # a door no script switches is in no such doorway
        entry, _ = self.check(FakeStages({10: ('g', frozenset({1.0}), frozenset({0.0, 2.0}))}))
        self.assertNotIn(' X ', entry['job'])

    def test_the_doorway_rule(self):
        here = {'reference': 1, 'mins': [0, 0, 0], 'maxs': [10, 10, 50]}
        links = [here, dict(here, reference=2), dict(here, reference=3, mins=[100, 0, 0], maxs=[110, 10, 50]),
                 dict(here, reference=4), dict(here, reference=5)]
        stages = FakeStages({1: ('g', frozenset({3.0}), frozenset({1.0})), 2: ('g', frozenset({1.0}),
                                                                             frozenset({3.0})),
                             3: None, 4: None, 5: ('g', frozenset({3.0}), frozenset({1.0}))})
        # 2: hidden when 1 is shown; 3: not in the doorway; 4: a stage not read; 5: shown with it
        self.assertEqual(D.doorway_off(here, links, stages), [2, 4])
        self.assertEqual(D.doorway_off(dict(here, reference=9), links, stages), [])


class KnownList(unittest.TestCase):
    # the six entrances walked up to and entered in play on the v0.0.68-dev8 image (five ice caves, the Caverns of
    # Karstaag), and the two the dive session entered on the same image with the swim fix's engine (Rimhull's well with
    # its key, Mournhold's ladder at its quest stage, from inside mh0005 and from its walk-out arrival in mh0004), and
    # the three doors under water the swimmer entered with the gated engine of 4974f47ac (the Unmarked Shipwreck's
    # trapdoor, the Caves of Fjalding, Stahlman's Gorge): off the list; every other entrance of the expansions listed
    # there carries its play result
    PLAYED = (8406659, 8407976, 8409052, 8416809, 8416813, 8418105, 8396936, 4218838, 225480, 8409047, 8420566)

    def test_the_expansions_entrances_carry_their_play_result(self):
        known = D.load_known(ROOT / 'config/door-check-known.json')
        for ref in self.PLAYED:
            self.assertNotIn(ref, known)
        mine = {ref: row for ref, row in known.items()
                if row['class'] in ('DOOR-USE-COLLISION-EXPANSIONS-68', 'DOOR-CHECK-NO-SWIM-CASE-68')}
        self.assertEqual(sorted(mine), [8399605, 8399658, 8402954, 8412721])
        for ref, row in mine.items():
            self.assertIn('in play on the v0.0.68-dev8 image', row['reason'].lower(), ref)

    def test_a_locked_door_is_judged_as_opened_with_its_key(self):
        # play on the v0.0.68-dev8 image (the dive session): Rimhull's well, locked at 100 with key_Lassnr_well as in
        # the original, entered with its key. The check judges a locked entrance as the player with its key (or a pick
        # or a spell) uses it: the harness never sets the engine's lock hook (aw_scene.c aw_load_door_lock, NULL there),
        # and each entry keeps the lock and its key for the play session that proves it
        harness = (ROOT / 'tools/door_engine_check.c').read_text(encoding='utf-8')
        self.assertNotIn('aw_load_door_lock', harness)
        text = (ROOT / 'tools/door_engine_check.py').read_text(encoding='utf-8')
        self.assertIn("'holder_kind', 'locked', 'lock_level', 'key')}", text)

    def test_the_image_step_gives_the_check_the_masters_stages(self):
        text = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        body = text[text.index('def write_door_check('):text.index('def write_room_batch_links(')]
        self.assertIn('script_stages.read(args.data_files)', body)
        self.assertIn('stages=stages', body)


if __name__ == '__main__':
    unittest.main()
