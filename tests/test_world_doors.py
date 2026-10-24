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
