# SPDX-License-Identifier: GPL-3.0-only
"""The item sweep of a compiled room (tools/room_item_census.py; CENSUS-SHELF-PLATE-BAKED-67): every placed reference
of the original cell counted by category against what the room's map holds (an entity carrying its reference, the
engine's placed item list, the room's bake, left out with the converter's rule), and the check that refuses a room
whose takeable item or container could not be aimed at, taken or opened. Synthetic maps; the dev5 opening rooms'
tables are kept with the job's logs."""
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

import room_item_census as census  # noqa: E402


def bsp(entities):
    """A map's bytes with only its entity lump: the header (version, 15 lumps) and the text."""
    text = ''.join('{\n' + ''.join('"%s" "%s"\n' % kv for kv in fields.items()) + '}\n' for fields in entities)
    body = text.encode('latin-1') + b'\0'
    head = struct.pack('<i', 29) + struct.pack('<ii', 4 + 15 * 8, len(body)) + b'\0' * (14 * 8)
    return head + body


def ref(number, kind, ident, **more):
    return dict({'number': number, 'type': kind, 'id': ident, 'model': 'm\\%s.nif' % ident}, **more)


ROOM = [
    {'classname': 'worldspawn', '_aw_cell_int': '763', 'message': 'Census and Excise Office'},
    {'classname': 'func_wall', 'aw_ref': '119541', 'model': '*38'},      # the bookshelf
    {'classname': 'func_wall', 'aw_ref': '119554', 'model': '*148'},     # the Limeware Platter standing in it
    {'classname': 'func_wall', 'aw_ref': '119577', 'model': '*154'},     # the Iron Dagger
    {'classname': 'aw_npc', 'aw_ref': '119636', 'model': 'progs/np_census.mdl'},
    {'classname': 'aw_flame', 'aw_ref': '119537'}, {'classname': 'func_wall', 'aw_ref': '119537', 'model': '*3'},
    {'classname': 'func_wall', 'aw_ref': '119600', 'model': '*60'},      # a basket (a container)
    {'classname': 'info_player_start'},
]
REFS = [
    ref(119541, 'STAT', 'furn_com_r_bookshelf_01'), ref(119554, 'MISC', 'misc_lw_platter'),
    ref(119577, 'WEAP', 'iron dagger'), ref(119636, 'NPC_', 'chargen class'),
    ref(119537, 'LIGH', 'light_com_candle_06', light={'flags': 0x2}),
    ref(119600, 'CONT', 'com_basket_01'), ref(172862, 'STAT', 'NorthMarker'),
    ref(119999, 'MISC', 'misc_old', deleted=True),
]


def omission(r):
    return 'editor marker' if 'marker' in r['id'].casefold() else None


class RoomItemCensusTests(unittest.TestCase):
    def test_the_map_side_by_reference_and_room(self):
        raw = bsp(ROOM)
        self.assertEqual(census.map_room(raw), 763)
        held = census.map_references(raw)
        self.assertEqual(held[119537], ['aw_flame', 'func_wall'])     # a lit candle: its flame and its brush
        self.assertEqual(held[119636], ['aw_npc'])
        self.assertNotIn(0, held)
        with self.assertRaises(ValueError):
            census.map_references(b'IBSP')

    def test_every_takeable_item_an_entity_passes_and_is_counted_by_category(self):
        result = census.census(REFS, census.map_references(bsp(ROOM)), omission=omission)
        self.assertEqual(result['problems'], [])
        cats = result['categories']
        self.assertEqual((cats['misc']['placed'], cats['misc']['entity'], cats['misc']['deleted']), (1, 1, 1))
        self.assertEqual((cats['light']['entity'], cats['light']['takeable']), (1, 1))
        self.assertEqual((cats['static']['placed'], cats['static']['entity'], cats['static']['left out']), (2, 1, 1))
        marker = next(r for r in result['rows'] if r['reference'] == 172862)
        self.assertEqual((marker['state'], marker['reason']), ('left out', 'editor marker'))
        md = census.render_md('Seyda Neen, Census and Excise Office', result)
        self.assertIn('| misc | 1 | 1 | 0 | 0 | 0 | 1 | 1 |', md)
        self.assertIn('| all | 7 | 6 | 0 | 0 | 1 | 1 | 3 |', md)
        self.assertIn('- static `NorthMarker` (reference 172862): left out (editor marker)', md)

    def test_an_item_baked_into_the_room_or_left_out_is_refused(self):
        # the platter merged into the room's geometry (no entity carries it): it could not be aimed at or taken
        room = [e for e in ROOM if e.get('aw_ref') != '119554']
        result = census.census(REFS, census.map_references(bsp(room)), baked={119554}, omission=omission)
        self.assertEqual(len(result['problems']), 1)
        self.assertIn('misc_lw_platter', result['problems'][0])
        self.assertIn('is baked', result['problems'][0])
        # not in the map at all, and a container without its brush: both named
        room = [e for e in ROOM if e.get('aw_ref') not in ('119554', '119600')]
        result = census.census(REFS, census.map_references(bsp(room)), omission=omission)
        self.assertEqual(len(result['problems']), 2)
        self.assertTrue(any('com_basket_01' in p and 'opened' in p for p in result['problems']))

    def test_the_placed_list_draws_items_a_room_map_leaves_out(self):
        # the Imperial Prison Ship's dishes: drawn from the engine's placed item list by reference, taken by their row
        room = [e for e in ROOM if e.get('aw_ref') != '119554']
        result = census.census(REFS, census.map_references(bsp(room)), omission=omission, placed={119554})
        self.assertEqual(result['problems'], [])
        self.assertEqual(result['categories']['misc']['placed list'], 1)
        # a light the player can carry counts as takeable; one fixed to the room does not
        self.assertTrue(census.takeable(REFS[4]))
        self.assertFalse(census.takeable(ref(1, 'LIGH', 'light_de_lantern_01', light={'flags': 0})))

    def test_the_image_step_sweeps_the_opening_rooms_it_holds(self):
        # build_aga.py write_opening_item_sweep: the two opening rooms of an image's id1 (their maps and the placed
        # item list), the master read once; a room whose map the image does not hold is listed as absent
        import tempfile
        from unittest import mock
        from prepare_item_models import pack_placed
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            (id1 / 'maps').mkdir(parents=True)
            (id1 / 'progs/items').mkdir(parents=True)
            (id1 / 'maps/census.bsp').write_bytes(bsp([e for e in ROOM if e.get('aw_ref') != '119554']))
            (id1 / 'progs/items/placed.awp').write_bytes(pack_placed(
                {763: [(119554, 0, 'progs/items/m0123456789abcdef.mdl', 0, 0, 0, 0, 0, 0, 1.0)]}))
            cell = {'name': 'Seyda Neen, Census and Excise Office', 'refs': REFS}
            with mock.patch('mwad.interior.read_interiors', return_value=[cell]) as reader, \
                    mock.patch('mwad.interior.omission_reason', side_effect=omission):
                sweep = census.opening_sweep(Path(tmp) / 'Morrowind.esm', id1)
            reader.assert_called_once()
            self.assertEqual(sweep['absent'], ['Imperial Prison Ship'])
            self.assertEqual(sweep['problems'], [])
            room = sweep['rooms']['Seyda Neen, Census and Excise Office']
            self.assertEqual((room['room'], room['categories']['misc']['placed list']), (763, 1))
            self.assertIn('# Item sweep: Seyda Neen, Census and Excise Office', room['md'])
            # an image without the placed list: the platter is not drawn, the sweep names it
            bare = Path(tmp) / 'bare'
            (bare / 'maps').mkdir(parents=True)
            (bare / 'maps/census.bsp').write_bytes((id1 / 'maps/census.bsp').read_bytes())
            with mock.patch('mwad.interior.read_interiors', return_value=[cell]), \
                    mock.patch('mwad.interior.omission_reason', side_effect=omission):
                sweep = census.opening_sweep(Path(tmp) / 'Morrowind.esm', bare)
            self.assertEqual(len(sweep['problems']), 1)
            self.assertTrue(sweep['problems'][0].startswith('Seyda Neen, Census and Excise Office: '))
        aga = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn('write_opening_item_sweep(args,boot/\'id1\',out)', aga)
        self.assertIn("raise ValueError('Opening item sweep: %d takeable item(s) or container(s) cannot be used", aga)

    def test_the_sweep_reads_the_placed_list_under_the_tables_room_number_before_the_maps_are_stamped(self):
        # OPENING-SWEEP-BEFORE-STAMP-69: the image step sweeps the opening rooms long before it stamps each interior
        # map's room number into its worldspawn (cell_numbers.stamp_staged_cells): on the dev6 build's maps there was
        # no _aw_cell_int yet, the sweep read room 0, and the prison ship's 79 items on the placed list (room 471)
        # stopped the image as "left out". The room number comes from the same table the stamp writes
        import tempfile
        from unittest import mock
        from prepare_item_models import pack_placed
        prison = [{'classname': 'worldspawn', 'message': 'AmiWind / Prison Ship'},           # not stamped yet
                  {'classname': 'func_wall', 'aw_ref': '421300', 'model': '*1'}]
        refs = [ref(421335, 'MISC', 'misc_com_wood_cup_01'), ref(421300, 'CONT', 'com_chest_02')]
        cell = {'name': 'Imperial Prison Ship', 'refs': refs}
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            (id1 / 'maps').mkdir(parents=True)
            (id1 / 'progs/items').mkdir(parents=True)
            (id1 / 'maps/prison.bsp').write_bytes(bsp(prison))
            (id1 / 'progs/items/placed.awp').write_bytes(pack_placed(
                {471: [(421335, 0, 'progs/items/m0123456789abcdef.mdl', 0, 0, 0, 0, 0, 0, 1.0)]}))
            rooms = (('Imperial Prison Ship', 'prison'),)
            with mock.patch('mwad.interior.read_interiors', return_value=[cell]), \
                    mock.patch('mwad.interior.omission_reason', return_value='small item or actor deferred'):
                sweep = census.opening_sweep(Path(tmp) / 'Morrowind.esm', id1, rooms,
                                             numbers={'imperial prison ship': 471})
                self.assertEqual(sweep['problems'], [])
                room = sweep['rooms']['Imperial Prison Ship']
                self.assertEqual((room['room'], room['categories']['misc']['placed list']), (471, 1))
                # without the table (the old sweep): room 0, the cup refused although the engine draws and takes it
                old = census.opening_sweep(Path(tmp) / 'Morrowind.esm', id1, rooms)
                self.assertEqual(len(old['problems']), 1)
                self.assertIn('misc_com_wood_cup_01', old['problems'][0])
                # a stamped map whose number is not the table's is named
                (id1 / 'maps/prison.bsp').write_bytes(bsp([dict(prison[0], _aw_cell_int='472')] + prison[1:]))
                other = census.opening_sweep(Path(tmp) / 'Morrowind.esm', id1, rooms,
                                             numbers={'imperial prison ship': 471})
                self.assertTrue(any('the map says room 472, the cell number table 471' in p for p in other['problems']))

    def test_a_new_unusable_item_in_the_census_office_still_refuses(self):
        # the table's number does not hide a real gap: a takeable item neither an entity nor on the placed list
        import tempfile
        from unittest import mock
        from prepare_item_models import pack_placed
        census_room = [dict(e) for e in ROOM if e.get('aw_ref') != '119554']
        census_room[0].pop('_aw_cell_int')
        with tempfile.TemporaryDirectory() as tmp:
            id1 = Path(tmp) / 'id1'
            (id1 / 'maps').mkdir(parents=True)
            (id1 / 'progs/items').mkdir(parents=True)
            (id1 / 'maps/census.bsp').write_bytes(bsp(census_room))
            (id1 / 'progs/items/placed.awp').write_bytes(pack_placed({763: []}))
            cell = {'name': 'Seyda Neen, Census and Excise Office', 'refs': REFS}
            with mock.patch('mwad.interior.read_interiors', return_value=[cell]), \
                    mock.patch('mwad.interior.omission_reason', side_effect=omission):
                sweep = census.opening_sweep(Path(tmp) / 'Morrowind.esm', id1,
                                             (('Seyda Neen, Census and Excise Office', 'census'),),
                                             numbers={'seyda neen, census and excise office': 763})
            self.assertEqual(len(sweep['problems']), 1)
            self.assertIn('misc_lw_platter', sweep['problems'][0])
        aga = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        self.assertIn('numbers=room_numbers(load_table(resolve_data_files(Path(args.data_files)))[0]))', aga)

    def test_the_command_line_check_exit_code(self):
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            good, bad = Path(tmp) / 'good.bsp', Path(tmp) / 'bad.bsp'
            good.write_bytes(bsp(ROOM))
            bad.write_bytes(bsp([e for e in ROOM if e.get('aw_ref') != '119554']))
            cell = {'name': 'Seyda Neen, Census and Excise Office', 'refs': REFS, 'master_sha256': '0' * 64}
            with mock.patch('mwad.interior.read_interior', return_value=cell), \
                    mock.patch('mwad.interior.omission_reason', side_effect=omission), \
                    mock.patch('sys.stdout'):
                args = ['--master', str(Path(tmp) / 'Morrowind.esm'), '--cell', cell['name'], '--check',
                        '--out', str(Path(tmp) / 'out.json')]
                self.assertEqual(census.main(args + ['--map', str(good)]), 0)
                self.assertEqual(census.main(args + ['--map', str(bad)]), 1)


if __name__ == '__main__':
    unittest.main()
