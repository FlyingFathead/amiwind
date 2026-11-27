# SPDX-License-Identifier: GPL-3.0-only
"""The world door table (tools/world_doors.py, v0.0.50 The Doors, CHIM-REGION-DOORS-NO-ROOMS-48).

The maintainer, 2026-10-24: "ALL EXTERIOR ENTRANCES THAT ARE AVAILABLE IN THE GAME MUST BE LINKED TO THEIR
CORRESPONDING INTERIORS." The v0.0.49 image left 106 of 3,133 doors unlinked: exits into cells a town frame holds
(the linker checked a town's map by its own name, while a town on CHIM runs as <name>-chim) and doors in cells inside
the old town frames' boxes that no bank carried. These tests hold the one holder rule, the coordinates of each holder
kind, the bank writing (a row added with the bank's own padding, a "-" row filled, markers never in a bank) and the
build check (every door and marker resolves)."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import map_files  # noqa: E402
import world_doors  # noqa: E402
from room_batches import parse_row  # noqa: E402

TOWN = ('seyda', (-10000.0, -10000.0, 10000.0, 10000.0), (1000.0, 2000.0))
REGIONS = {(3, 0): ('vf0042', [24576.0, 0.0, 0.0])}


def door(number, source_cell, position, destination_cell, destination, ident='ex_door', interior=False):
    return {'number': number, 'id': ident, 'source_cell': source_cell, 'source_interior': interior,
            'position': position, 'destination_cell': destination_cell, 'destination_interior': bool(destination_cell),
            'destination': {'position': destination, 'rotation_radians': [0.0, 0.0, 0.0]}}


class HolderRule(unittest.TestCase):
    def test_town_box_wins_over_region(self):
        self.assertEqual(world_doors.holder([500.0, 500.0, 0.0], [TOWN], {(0, 0): ('vf0001', [0, 0, 0])})[:2],
                         ('seyda', 'town'))

    def test_region_frame_of_the_cell_outside_every_town(self):
        found = world_doors.holder([3 * 8192 + 100.0, 50.0, 0.0], [TOWN], REGIONS)
        self.assertEqual(found[:2], ('vf0042', 'region'))

    def test_no_holder(self):
        self.assertIsNone(world_doors.holder([90000.0, 90000.0, 0.0], [TOWN], REGIONS))

    def test_local_points(self):
        self.assertEqual(world_doors.local_point([1400.0, 2400.0, 80.0], 'town', (1000.0, 2000.0)), [100.0, 100.0, 20.0])
        self.assertEqual(world_doors.local_point([24676.0, 40.0, 80.0], 'region', [24576.0, 0.0, 0.0]),
                         [24676.0 * .25 - 24576.0, 10.0, 20.0])
        self.assertEqual(world_doors.local_point([40.0, 40.0, 40.0], 'room', [20.0, 0.0, 0.0]), [5.0, 10.0, 10.0])


class Table(unittest.TestCase):
    def rows(self):
        doors = [
            door(1, 'Seyda Neen', [500.0, 500.0, 0.0], 'Seyda Neen, Some House', [10.0, 10.0, 0.0]),
            door(2, 'Seyda Neen, Some House', [0.0, 0.0, 0.0], '', [600.0, 600.0, 0.0], interior=True),
            door(3, '', [3 * 8192 + 100.0, 50.0, 0.0], 'Far Cave', [0.0, 0.0, 0.0]),
            door(4, 'Seyda Neen', [700.0, 700.0, 0.0], 'Missing Room', [0.0, 0.0, 0.0]),
            door(5, 'Seyda Neen', [800.0, 800.0, 0.0], 'Seyda Neen, Some House', [5.0, 5.0, 0.0], ident='PrisonMarker'),
        ]
        rooms = {'seyda neen, some house': 'ri0001', 'far cave': 'ri0002'}
        return {r['reference']: r for r in world_doors.table(doors, rooms, [TOWN], REGIONS)}

    def test_resolution_both_ways(self):
        rows = self.rows()
        self.assertEqual((rows[1]['source'], rows[1]['target']), ('seyda', 'ri0001'))
        self.assertEqual((rows[2]['source'], rows[2]['target'], rows[2]['holder']), ('ri0001', 'seyda', 'room'))
        self.assertEqual((rows[3]['source'], rows[3]['target']), ('vf0042', 'ri0002'))

    def test_marker_is_its_own_kind_and_resolves(self):
        rows = self.rows()
        self.assertEqual(rows[5]['kind'], 'marker')
        self.assertNotIn('problem', rows[5])

    def test_the_doors_of_a_presented_district_resolve_through_its_blocks_frames(self):
        # MOURNHOLD-EXTERIOR-CELLS-66: a district the build presents as exterior cells (its block the region frame's
        # cell 3,0) and converts: its doors read as the presented world has them (tools/presented_exterior.py
        # present_doors) resolve through that frame, the way in from a room, the way out into it, and its jail marker;
        # without the presentation they are held back as today
        import presented_exterior as P
        doors = [door(10, 'Some Room', [0.0, 0.0, 0.0], 'Town, Plaza', [100.0, 50.0, 8.0], interior=True),
                 door(11, 'Town, Plaza', [200.0, 60.0, 8.0], 'Some Room', [5.0, 5.0, 0.0], interior=True),
                 door(12, 'Town, Plaza', [210.0, 60.0, 8.0], 'Some Room', [5.0, 5.0, 0.0], ident='PrisonMarker',
                      interior=True)]
        rooms, held_back = {'some room': 'ri0003'}, {'town, plaza': 'an exterior-like cell'}
        plain = world_doors.table(doors, rooms, [TOWN], REGIONS, held_back=held_back)
        self.assertEqual([('held_back' in r, 'problem' in r) for r in plain], [(True, False)] * 3)
        places = {'town, plaza': {'cell': 'Town, Plaza', 'block': [3, 0], 'size': [1, 1], 'offset': [3 * 8192.0, 0.0]}}
        rows = {r['reference']: r for r in world_doors.table(P.present_doors(places, doors), rooms, [TOWN], REGIONS,
                                                              held_back=held_back)}
        self.assertEqual((rows[10]['source'], rows[10]['target'], rows[10]['direction']),
                         ('ri0003', 'vf0042', 'room_to_exterior'))
        self.assertEqual(rows[10]['destination_cell'], 'Town, Plaza')       # the label the bank row shows
        self.assertEqual(rows[10]['arrival'][:2], [(100.0 + 24576.0) * .25 - 24576.0, 50.0 * .25])
        self.assertEqual((rows[11]['source'], rows[11]['holder'], rows[11]['target'], rows[11]['direction']),
                         ('vf0042', 'region', 'ri0003', 'exterior_to_room'))
        self.assertEqual((rows[12]['kind'], rows[12]['source']), ('marker', 'vf0042'))
        self.assertFalse(any('held_back' in r or 'problem' in r for r in rows.values()))
        # without places: the same doors, so the same rows
        self.assertEqual(world_doors.table(P.present_doors({}, doors), rooms, [TOWN], REGIONS, held_back=held_back),
                         plain)

    def test_build_check_lists_every_unresolved_row(self):
        problems = world_doors.unresolved_problems(list(self.rows().values()))
        self.assertEqual(len(problems), 1)
        self.assertIn('door 4', problems[0])
        self.assertIn('Missing Room', problems[0])


class Apply(unittest.TestCase):
    def test_rows_added_with_the_bank_pad_filled_and_markers_kept_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp)
            # an existing town bank row of door 9 with half a unit of pad, and door 1's row still "-"
            pad_box = ' '.join('%.5f' % v for v in (-0.5, -0.5, -0.5, 10.5, 10.5, 10.5))
            (id1 / 'doors-seyda.txt').write_text(
                'AWD3\n'
                'seyda ri0009 9 %s 0.00000 0.00000 0.00000 0.00000\tOld Room\n'
                'seyda - 1 %s 0.00000 0.00000 0.00000 0.00000\tSeyda Neen, Some House\n' % (pad_box, pad_box),
                encoding='cp1252')
            rows = [
                {'reference': 9, 'kind': 'door', 'direction': 'exterior_to_room', 'source': 'seyda', 'holder': 'town',
                 'frame': [1000.0, 2000.0], 'target': 'ri0009', 'arrival': [0, 0, 0], 'yaw': 0,
                 'destination_cell': 'Old Room', 'source_cell': 'Seyda Neen'},
                {'reference': 1, 'kind': 'door', 'direction': 'exterior_to_room', 'source': 'seyda', 'holder': 'town',
                 'frame': [1000.0, 2000.0], 'target': 'ri0001', 'arrival': [1.0, 2.0, 3.0], 'yaw': 90.0,
                 'destination_cell': 'Seyda Neen, Some House', 'source_cell': 'Seyda Neen'},
                {'reference': 7, 'kind': 'door', 'direction': 'exterior_to_room', 'source': 'seyda', 'holder': 'town',
                 'frame': [1000.0, 2000.0], 'target': 'ri0007', 'arrival': [4.0, 5.0, 6.0], 'yaw': 0.0,
                 'destination_cell': 'Far House', 'source_cell': 'Seyda Neen'},
                {'reference': 5, 'kind': 'marker', 'direction': 'exterior_to_room', 'source': 'seyda', 'holder': 'town',
                 'frame': [1000.0, 2000.0], 'target': 'ri0001', 'arrival': [0, 0, 0], 'yaw': 0,
                 'destination_cell': 'Seyda Neen, Some House', 'source_cell': 'Seyda Neen'},
            ]
            # door 9's mesh bounds give the box (0..10) before the pad; door 7 is new
            bounds = {9: [[1000.0, 2000.0, 0.0], [1040.0, 2040.0, 40.0]],
                      1: [[1000.0, 2000.0, 0.0], [1040.0, 2040.0, 40.0]],
                      7: [[1400.0, 2400.0, 80.0], [1440.0, 2440.0, 120.0]]}
            result = world_doors.apply(id1, rows, bounds)
            self.assertEqual((result['added'], result['filled']), (1, 1))
            lines = (id1 / 'doors-seyda.txt').read_text(encoding='cp1252').split('\n')
            parsed = {int(p[0][2]): p for p in map(parse_row, lines) if p}
            self.assertEqual(sorted(parsed), [1, 7, 9])
            self.assertEqual(parsed[1][0][1], 'ri0001')
            self.assertEqual([float(v) for v in parsed[1][0][4:8]], [1.0, 2.0, 3.0, 90.0])
            box = [float(v) for v in parsed[7][0][3].split()]
            self.assertEqual(box, [99.5, 99.5, 19.5, 110.5, 110.5, 30.5])     # (1400-1000)*.25 = 100, less the pad
            self.assertNotIn(5, parsed)


class BorderCopies(unittest.TestCase):
    """DISTRICT-GATE-ON-CELL-BORDER-67: Godsreach (cells -12,-30 and -12,-29, frames mh0000 and mh0001, centred origins)
    as the v0.0.67-dev3 image's banks have it: its gate to the Plaza (4219376) stands on the border, its row only in
    mh0000's bank, while the gate from the Plaza sets the player at -690 -1018 in mh0001."""
    FRAMES = {(-12, -30): ('mh0000', [-23552.0, -60416.0, 0.0]), (-12, -29): ('mh0001', [-23552.0, -58368.0, 0.0])}

    @staticmethod
    def bounds(origin, low, high):
        # mesh bounds in original units that give the bank's box in the frame of ORIGIN (door_box: x .25 - origin)
        return [[(low[k] + origin[k]) * 4 for k in range(3)], [(high[k] + origin[k]) * 4 for k in range(3)]]

    def setUp(self):
        south, north = self.FRAMES[(-12, -30)][1], self.FRAMES[(-12, -29)][1]
        self.door_bounds = {
            4219376: self.bounds(south, (-729.96893, 995.73703, 19.87399), (-714.24203, 1042.74357, 90.05164)),
            4215142: self.bounds(south, (-247.64070, 834.30724, 58.09289), (-236.24391, 875.27305, 108.01289)),
            4219377: self.bounds(north, (595.71791, -1046.21854, 19.87834), (611.44483, -999.21200, 90.05598))}
        row = {'kind': 'door', 'direction': 'exterior_to_exterior', 'holder': 'region', 'yaw': 315.0}
        self.rows = [
            dict(row, reference=4219376, source='mh0000', frame=list(south), target='mh0004', arrival=[256.0, 401.0, 86.875],
                 destination_cell='Mournhold, Plaza Brindisi Dorom', source_cell='Mournhold, Godsreach'),
            dict(row, reference=4215142, source='mh0000', frame=list(south), target='ri53c6526d53',
                 arrival=[-0.40105, 32.81609, 5.35036], direction='exterior_to_room',
                 destination_cell='Mournhold, Museum of Artifacts', source_cell='Mournhold, Godsreach'),
            dict(row, reference=4219377, source='mh0001', frame=list(north), target='mh0007', arrival=[-71.5, 352.25, 70.875],
                 destination_cell='Mournhold, Temple Courtyard', source_cell='Mournhold, Godsreach', yaw=60.0)]

    def test_the_gates_on_the_inner_border_get_a_row_in_the_bank_beside(self):
        copies = world_doors.border_copies(self.rows, self.door_bounds, self.FRAMES)
        self.assertEqual(sorted((c['reference'], c['border_copy_of'], c['source']) for c in copies),
                         [(4219376, 'mh0000', 'mh0001'), (4219377, 'mh0001', 'mh0000')])   # not the museum door
        self.assertEqual(world_doors.border_copies(self.rows, self.door_bounds, {}), [])      # the base game: none
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp)
            for name in ('mh0000', 'mh0001'):
                (id1 / ('doors-%s.txt' % name)).write_text('AWD3\n', encoding='cp1252')
            world_doors.apply(id1, self.rows + copies, self.door_bounds)
            north = {int(p[0][2]): p for p in map(parse_row, (id1 / 'doors-mh0001.txt').read_text(
                encoding='cp1252').split('\n')) if p}
            south = {int(p[0][2]): p for p in map(parse_row, (id1 / 'doors-mh0000.txt').read_text(
                encoding='cp1252').split('\n')) if p}
        self.assertEqual(sorted(north), [4219376, 4219377])
        self.assertEqual(sorted(south), [4215142, 4219376, 4219377])
        gate = north[4219376][0]
        self.assertEqual((gate[0], gate[1]), ('mh0001', 'mh0004'))
        box = [float(v) for v in gate[3].split()]
        # the same box 2048 units over: the southern frame's 995.7 .. 1042.7 is -1052.3 .. -1005.3 in the northern one
        for got, want in zip(box, (-729.96893, 995.73703 - 2048, 19.87399, -714.24203, 1042.74357 - 2048, 90.05164)):
            self.assertAlmostEqual(got, want, places=3)
        self.assertEqual([float(v) for v in gate[4:8]], [256.0, 401.0, 86.875, 315.0])     # the same way to the Plaza
        # the player set down by the gate from the Plaza (-690 -1018 in mh0001) has the gate within the use reach
        self.assertLess(max(box[0] - (-690.0), -690.0 - box[3], 0.0) ** 2 +
                        max(box[1] - (-1018.0), -1018.0 - box[4], 0.0) ** 2, 56.0 ** 2)


class OpeningDoors(unittest.TestCase):
    def test_the_opening_scene_keeps_its_own_doors(self):
        # the prison ship, the pier, the census office and the courtyard: no leaving the census office before the
        # papers, and then by one door only (engine aw_opening.c); the table never writes a row from or into them
        self.assertEqual(world_doors.OPENING_MAPS, {'prison', 'census', 'intro_docks', 'sncourt'})
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp)
            before = 'AWD3\ncensus - 119513 0 0 0 1 1 1 0.00000 0.00000 0.00000 0.00000\tSeyda Neen\n'
            (id1 / 'doors-census.txt').write_text(before, encoding='cp1252', newline='\n')
            rows = [{'reference': 119513, 'kind': 'door', 'direction': 'room_to_exterior', 'source': 'census',
                     'holder': 'room', 'frame': None, 'target': 'seyda', 'arrival': [1, 2, 3], 'yaw': 0,
                     'destination_cell': 'Exterior world', 'source_cell': 'Seyda Neen, Census and Excise Office'},
                    {'reference': 113833, 'kind': 'door', 'direction': 'exterior_to_room', 'source': 'seyda',
                     'holder': 'town', 'frame': [0.0, 0.0], 'target': 'census', 'arrival': [1, 2, 3], 'yaw': 0,
                     'destination_cell': 'Seyda Neen, Census and Excise Office', 'source_cell': 'Seyda Neen'}]
            result = world_doors.apply(id1, rows, {})
            self.assertEqual((result['added'], result['filled']), (0, 0))
            self.assertEqual((id1 / 'doors-census.txt').read_text(encoding='cp1252'), before)
            self.assertFalse((id1 / 'doors-seyda.txt').exists())


class TeleportNames(unittest.TestCase):
    def test_the_shipped_file_parses_and_names_the_heart_chamber(self):
        names = world_doors.teleport_names((ROOT / 'config' / world_doors.TELEPORT_NAMES).read_bytes())
        self.assertEqual(names['heartchamber'][0], 'rifa4ef181ed')      # Akulakhan's Chamber (config/room-batches.json)

    def test_suran_and_ald_ruhn_names(self):
        names = world_doors.teleport_names((ROOT / 'config' / world_doors.TELEPORT_NAMES).read_bytes())
        # Desele's House of Earthly Delights: a room map of config/room-batches.json, the street door's arrival
        self.assertEqual(names['suranclub'][0], 'ric5e9a38a4d')
        # the Arena Pit: the arena's own room map, where the canton door from the Arena puts the player
        self.assertEqual(names['arenapit'][0], 'vai000')
        self.assertIn('ric5e9a38a4d', (ROOT / 'config' / 'room-batches.json').read_text(encoding='utf-8'))
        # the towns: outdoor places in original global coordinates (Suran cell 6,-7; Ald-ruhn cells -2,6; Khuul -9,17)
        for name, (cx, cy) in (('suran', (6, -7)), ('aldruhn', (-2, 6)), ('khuul', (-9, 17))):
            self.assertEqual(names[name][0], world_doors.GLOBAL_PLACE)
            x, y, z = names[name][1]
            self.assertEqual((int(x // 8192), int(y // 8192)), (cx, cy))
        self.assertEqual(world_doors.teleport_name_problems(names, {'x': 'ric5e9a38a4d', 'y': 'rifa4ef181ed',
                                                                    'vivec, arena pit': 'vai000'},
                                                            {'vivec_god': 1}), [])

    def test_lordvivec_is_vivec_himself(self):
        # DBG-TP-LORDVIVEC-69: a being place, the label Vivec's record id (the v0.0.69-dev6 image's teleport list has
        # one being row of it: "Vivec", flags 25, room map vpi015)
        names = world_doors.teleport_names((ROOT / 'config' / world_doors.TELEPORT_NAMES).read_bytes())
        self.assertEqual(names['lordvivec'][0], world_doors.BEING_PLACE)
        self.assertEqual(names['lordvivec'][3], 'vivec_god')
        self.assertNotIn('vivec', names)          # dbg tp vivec stays the city

    def test_a_being_place_needs_one_being_row_of_the_list(self):
        names = {'lordvivec': (world_doors.BEING_PLACE, [0, 0, 0], 0.0, 'vivec_god')}
        self.assertEqual(world_doors.teleport_name_problems(names, {}, {'vivec_god': 1}), [])
        self.assertEqual(world_doors.teleport_name_problems(names, {}, {'VIVEC_GOD'.casefold(): 1}), [])
        # the id not in the list (a missing id, an image without the room, an image without a list): refused, named
        for beings in ({'fargoth': 1}, {}, None):
            problems = world_doors.teleport_name_problems(names, {}, beings)
            self.assertEqual(problems, ['named place lordvivec: being vivec_god is not in the teleport list'])
        # on two rows (a being placed in two places): which one would be a guess, so refused
        self.assertEqual(world_doors.teleport_name_problems(names, {}, {'vivec_god': 2}),
                         ['named place lordvivec: being vivec_god is on 2 rows of the teleport list'])
        # a being place is never checked as a room map, and a room place never as a being
        self.assertEqual(world_doors.teleport_name_problems(
            dict(names, heartchamber=('rifa4ef181ed', [0, 0, 0], 0.0, 'x')), {'c': 'rifa4ef181ed'},
            {'vivec_god': 1}), [])

    def test_the_image_step_checks_being_places_against_its_own_list(self):
        build = (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8')
        doors = build[build.index('def write_world_doors('):build.index('def write_door_check(')]
        # the list with its being rows is written first (tp_places_rooms), then the named places are checked against it
        self.assertLess(doors.index('tp_places_rooms(id1, rooms, master_raw, out)'),
                        doors.index('beings = being_ids((id1/TP_PLACES_NAME).read_bytes())'))
        self.assertIn("world_doors.teleport_names((ROOT/'config'/'teleport-names.txt').read_bytes()), rooms, beings)",
                      doors)

    def test_bad_lines_are_refused(self):
        for raw in (b'AWTN0\n', b'AWTN1\nname|map|1 2|90|label\n', b'AWTN1\nn|m|1 2 3|0|x\nN|m|1 2 3|0|y\n',
                    b'AWTN1\n%s|m|1 2 3|0|x\n' % (b'n' * 24)):
            with self.assertRaises(ValueError, msg=raw):
                world_doors.teleport_names(raw)

    def test_a_named_place_must_lead_into_a_room_of_the_image(self):
        names = {'heartchamber': ('rifa4ef181ed', [0, 0, 0], 0.0, 'x')}
        self.assertEqual(world_doors.teleport_name_problems(names, {"akulakhan's chamber": 'rifa4ef181ed'}), [])
        self.assertEqual(len(world_doors.teleport_name_problems(names, {})), 1)


class TownMapPresent(unittest.TestCase):
    def test_a_town_on_chim_runs_as_its_chim_frame_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            maps = Path(tmp)
            (maps / 'vivec_city-chim.chim').write_bytes(b'x')
            self.assertTrue(map_files.town_map_present(maps, 'vivec_city'))
            self.assertFalse(map_files.map_file(maps, 'vivec_city').is_file())
            self.assertFalse(map_files.town_map_present(maps, 'balmora'))


if __name__ == '__main__':
    unittest.main()
