# SPDX-License-Identifier: GPL-3.0-only
"""The travel services (TRAVEL-SERVICES-CHIM-51): the builder's table (tools/prepare_travel.py), the engine's rules
(tests/aga_travel_test.c over engine/aga/src/aw_travel_rules.c) and the wiring (aw_scene.c, Makefile, the image step).

Rules from OpenMW file apps/openmw/mwgui/travelwindow.cpp: an interior provider charges fMagesGuildTravel and no time
passes; one outdoors charges the 3D distance / fTravelMult (at least 1) and the ride takes the 2D distance /
fTravelTimeMult hours."""
import os
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
SRC = ROOT / 'engine' / 'aga' / 'src'

import prepare_travel  # noqa: E402

SETTINGS = {'ftravelmult': 4000.0, 'ftraveltimemult': 16000.0, 'fmagesguildtravel': 10.0}


def dodt(x, y, z, rz=0.0):
    return ('DODT', struct.pack('<6f', x, y, z, 0.0, 0.0, rz))


class TableTests(unittest.TestCase):
    def test_destinations_read_dodt_and_the_dnam_after_it(self):
        fields = [('NAME', b'x\0'), dodt(1, 2, 3, 1.5), ('DNAM', b'Balmora, Guild of Mages\0'), dodt(4, 5, 6)]
        out = prepare_travel.destinations(fields)
        self.assertEqual([d['cell'] for d in out], ['Balmora, Guild of Mages', ''])
        self.assertEqual(out[1]['position'], [4.0, 5.0, 6.0])
        with self.assertRaises(ValueError):
            prepare_travel.destinations([('DODT', b'\0' * 12)])

    def test_openmw_price_and_hours(self):
        # outdoors: 3D / fTravelMult truncated, at least 1; hours from the 2D distance
        self.assertEqual(prepare_travel.price_hours([0, 0, 0], [40000, 3000, 0], False, SETTINGS), (10, 2))
        self.assertEqual(prepare_travel.price_hours([0, 0, 0], [10, 0, 0], False, SETTINGS), (1, 0))
        # an interior provider (a guild guide): the guild price, no time
        self.assertEqual(prepare_travel.price_hours([0, 0, 0], [90000, 0, 0], True, SETTINGS), (10, 0))
        # fTravelMult 0: the distance itself (OpenMW's guard)
        self.assertEqual(prepare_travel.price_hours([0, 0, 0], [5000, 0, 0], False, dict(SETTINGS, ftravelmult=0.0)),
                         (5000, 0))

    def provider(self, dests):
        return {'kind': 'NPC_', 'name': 'Test', 'master': 'Morrowind.esm', 'destinations': dests}

    def test_table_resolves_by_the_door_rule_and_lists_what_the_image_lacks(self):
        d_town = {'position': [100.0, 200.0, 300.0], 'rotation_radians': [0, 0, 0], 'cell': ''}
        d_region = {'position': [8192.0 * 3 + 10, 8192.0 * 2 + 10, 50.0], 'rotation_radians': [0, 0, 0], 'cell': ''}
        d_room = {'position': [10.0, 20.0, 30.0], 'rotation_radians': [0, 0, 0], 'cell': 'Some Room'}
        d_gone = {'position': [-200000.0, 150000.0, 0.0], 'rotation_radians': [0, 0, 0], 'cell': ''}
        providers = {'strider': self.provider([d_town, d_region, d_gone]), 'guide': self.provider([d_room])}
        cells = [{'name': '', 'flags': 0, 'x': 0, 'y': 0, 'region': 'ascadian isles region',
                  'refs': [{'id': 'Strider', 'number': 1, 'position': [0.0, 0.0, 0.0]}]},
                 {'name': 'Guild', 'flags': 1, 'x': 0, 'y': 0, 'region': '',
                  'refs': [{'id': 'guide', 'number': 2, 'position': [5.0, 5.0, 5.0]}]},
                 {'name': 'Pelagiad', 'flags': 0, 'x': 3, 'y': 2, 'region': '', 'refs': []}]
        regions = {'ascadian isles region': 'Ascadian Isles Region'}
        towns = [('balmora', (-1000, -1000, 1000, 1000), (0.0, 0.0))]
        frames = {(3, 2): ('vf0007', [6144.0, 4096.0, 0.0])}
        rooms = {'some room': 'ri0123456789'}
        rows, left = prepare_travel.table(providers, SETTINGS, cells, regions, rooms, towns, frames)
        by = {(r['provider'], r['label']): r for r in rows}
        town = by[('strider', 'Ascadian Isles Region')]
        self.assertEqual(town['map'], 'balmora')
        self.assertFalse(town['interior'])
        region = by[('strider', 'Pelagiad')]
        self.assertEqual(region['map'], 'vf0007')
        self.assertEqual(region['price'], int((((8192 * 3 + 10) ** 2 + (8192 * 2 + 10) ** 2 + 50 ** 2) ** .5) / 4000))
        room = by[('guide', 'Some Room')]
        self.assertEqual((room['map'], room['interior'], room['price'], room['hours']), ('ri0123456789', True, 10, 0))
        self.assertEqual([(x['provider'], x['reason'].split(' ')[0]) for x in left], [('strider', 'exterior')])

    def test_text_matches_the_engine_format(self):
        row = {'provider': 'darvame hleran', 'interior': False, 'map': 'balmora', 'arrival': [1.0, 2.0, 3.0],
               'yaw': 90.0, 'source': [4.0, 5.0, 6.0], 'price': 5, 'hours': 1, 'label': 'Balmora'}
        text = prepare_travel.text([row], SETTINGS)
        self.assertEqual(text.splitlines(), ['AWT1|4000.000|16000.000|10',
                                             'D|darvame hleran|0|balmora|1.000|2.000|3.000|90.000|4.0|5.0|6.0|5|1|Balmora'])
        with self.assertRaises(ValueError):
            prepare_travel.text([dict(row, map='a-map-name-too-long')], SETTINGS)
        self.assertEqual(prepare_travel.clean_label('A|B\tC' + 'x' * 80), ('ABC' + 'x' * 80)[:47])

    def test_the_menu_holds_every_provider_of_the_masters(self):
        # the most destinations one provider has in the three masters is 4 (the menu's rows with Cancel)
        self.assertEqual(prepare_travel.ROWS_PER_PROVIDER, 4)
        self.assertIn('#define AW_TRAVEL_ROWS 4', (SRC / 'aw_travel.h').read_text(encoding='utf-8'))


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class RuleTests(unittest.TestCase):
    def test_rows_price_and_hours(self):
        import test_aga_native_source as native
        native.NativeSourceTests().compile_run('aga_travel_test.c', [SRC / 'aw_travel_rules.c'],
                                               cflags=['-fsanitize=undefined', '-fno-sanitize-recover=all'])


class WiringTests(unittest.TestCase):
    def test_engine_opens_the_services_by_record_id_and_keeps_the_town_ride(self):
        scene = (SRC / 'aw_scene.c').read_text(encoding='utf-8')
        self.assertIn('COM_FOpenFile("travel.txt",&f)', scene)
        self.assertIn('GetEdictFieldValue((edict_t *)e,"aw_source_id")', scene)
        # the old two-town ride stays (DON'T DELETE ANY METHOD), checked first
        target = scene[scene.index('static edict_t *travel_target(void)'):scene.index('static int travel_use(void)')]
        self.assertLess(target.index('town->travel_npc'), target.index('travel_service(e)'))
        ride = scene[scene.index('static void travel_ride(int i)'):scene.index('int AW_TravelKey(int key)')]
        # paid only when the ride can start: the map and the Fast RAM check first, then the gold, then the clock
        self.assertLess(ride.index('AW_SceneEntryRefuse'), ride.index('AW_ItemAdd(&aw_state,"gold_001",-travel_price[i])'))
        self.assertLess(ride.index('AW_ItemAdd'), ride.index('AW_ClockAdvance'))
        self.assertIn('load_scene(&r,0);', ride)
        self.assertIn('travel_rows_for=NULL;', scene[scene.index('static void load_scene('):])

    def test_built_into_the_engine_and_the_image(self):
        make = (ROOT / 'engine' / 'aga' / 'Makefile').read_text(encoding='utf-8')
        self.assertIn('aw_travel_rules.c aw_scene.c', make)
        aga = (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8')
        doors = aga[aga.index('def write_world_doors('):aga.index('def write_door_check(')]
        self.assertIn('prepare_travel.write(id1, args.data_files, rooms, towns, regions, room_offsets())', doors)

    def test_write_reads_only_the_masters_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                prepare_travel.read_masters(tmp)


if __name__ == '__main__':
    unittest.main()
