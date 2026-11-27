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


MEASUREMENT = ROOT / 'docs' / 'performance' / 'WORLD_ITEMS.json'


def row(kind, reference, action=1, owned=0, name=b'Bowl'):
    """A 96-byte use-table row (tools/prepare_focus.py layout): kind, owned, action, lock, reference, x y z, weight,
    value, name, id."""
    return (bytes([ord(kind), owned, action | (4 if owned else 0), 0]) + struct.pack('<I', reference) +
            struct.pack('<iiifi', 0, 0, 0, 1.0, 5) + name.ljust(36, b'\0') + bytes(32))


def place(reference, key, interior=True, owner=None, name='Bowl', position=(10.0, 20.0, 30.0)):
    return {'reference': reference, 'master': 'Morrowind.esm', 'cell': 'Room' if interior else '', 'grid':
            None if interior else [0, 0], 'interior': interior, 'presented': False, 'key': key, 'id': 'misc_bowl',
            'name': name, 'category': 'misc', 'tag': 'MISC', 'position': list(position), 'owner': owner,
            'script': ''}


def sources(**over):
    out = {'rows': {}, 'owners': {}, 'hides': {}, 'placed': {}, 'rooms': {}, 'room_placements': {}, 'outdoors': {},
           'pieces': set(), 'masters_built': {0}, 'table': 'areas.awa', 'stores': [], 'args': {}}
    out.update(over)
    return out


class WorldItemCensusTests(unittest.TestCase):
    """The world census (WORLD-OBJECT-PLACEMENT-59): every placed takeable item judged by the engine's rules."""

    def test_a_room_draws_its_item_by_entity_room_placement_or_placed_list(self):
        import prepare_focus as pf
        outdoor = pf.exterior_key(0, 0)
        items = [place(11, 7), place(12, 7), place(13, 7), place(14, 7), place(15, 7, owner=('arrille', 0))]
        src = sources(rows={7: [row('I', r) for r in (11, 12, 13, 15)] + [row('I', 15, owned=1)]},
                      rooms={7: {'map': 'r.chim', 'kind': 'chim', 'record': ('chimi', 'r'), 'entities': {11: ['func_wall']}}},
                      room_placements={7: {12}}, placed={7: {13: (10.0, 20.0, 30.0), 14: (10.0, 20.0, 30.0)},
                                                         outdoor: {}})
        census.judge_world(items, src)
        by = {p['reference']: p['build'] for p in items}
        self.assertEqual(by[11]['copies'], ['entity'])
        self.assertEqual(by[12]['copies'], ['room placement'])
        self.assertEqual(by[13]['copies'], ['placed list'])
        for ref in (11, 12, 13):
            self.assertTrue(by[ref]['takeable'] and by[ref]['owner_kept'], (ref, by[ref]))
        # on the placed list but no use-table row: the engine never offers the row, so it is not drawn
        self.assertFalse(by[14]['drawn'])
        self.assertIn('not drawn: on the placed list, but it has no use-table row', by[14]['gaps'])
        # owned in the original, the first row of that reference free to take: the steal is lost
        self.assertIn('owned in the original, free to take in the row: taking it is not theft', by[15]['gaps'])

    def test_outdoors_a_chim_piece_needs_its_hide_row(self):
        # OUTDOOR-ITEM-CHIM-COPY-STAYS-69: the placed list and a CHIM piece both draw it; the take removes the placed
        # copy only, the piece goes only through a 'P' effect link row
        import prepare_focus as pf
        key = pf.exterior_key(17, 4)
        items = [place(48018, key, interior=False), place(48019, key, interior=False), place(480636, key, interior=False)]
        src = sources(rows={key: [row('I', r) for r in (48018, 48019, 480636)]},
                      placed={key: {r: (10.0, 20.0, 30.0) for r in (48018, 48019, 480636)}},
                      pieces={48018, 48019}, hides={key: {48019}})
        census.judge_world(items, src)
        by = {p['reference']: p['build'] for p in items}
        self.assertEqual(by[48018]['copies'], ['CHIM piece', 'placed list'])
        self.assertFalse(by[48018]['takeable'])
        self.assertIn('taken, but its CHIM piece stays drawn: no hide row', by[48018]['gaps'])
        self.assertIn('drawn twice outdoors: the placed list and a CHIM piece at the same spot', by[48018]['gaps'])
        self.assertTrue(by[48019]['takeable'])
        self.assertEqual((by[480636]['copies'], by[480636]['gaps'], by[480636]['takeable']), (['placed list'], [], True))

    def test_a_listed_hide_row_leaves_the_placed_model_the_one_copy(self):
        # OUTDOOR-ITEM-CHIM-COPY-STAYS-69, the fix: the piece of an item the placed list draws has a 'P' row with aux
        # PLACE_LISTED (tools/effect_links.py), gone whenever its area is applied: drawn once, taken whole; a listed
        # piece whose item has no use row (the list never offers it) is not drawn at all, and named
        import prepare_focus as pf
        PLACE_LISTED = census.PLACE_LISTED
        key = pf.exterior_key(17, 4)
        items = [place(48018, key, interior=False), place(48020, key, interior=False)]
        src = sources(rows={key: [row('I', 48018)]}, placed={key: {48018: (10.0, 20.0, 30.0), 48020: (1.0, 1.0, 1.0)}},
                      pieces={48018, 48020}, hides={key: {48018: PLACE_LISTED, 48020: PLACE_LISTED}})
        census.judge_world(items, src)
        by = {p['reference']: p['build'] for p in items}
        self.assertEqual((by[48018]['copies'], by[48018]['gaps'], by[48018]['takeable']), (['placed list'], [], True))
        self.assertFalse(by[48020]['drawn'])
        self.assertIn('not drawn: its CHIM piece is hidden for the placed list, which does not draw it',
                      by[48020]['gaps'])

    def test_items_with_no_row_and_rooms_not_in_the_image_are_named(self):
        import prepare_focus as pf
        items = [place(21, 9, name=''), place(22, 404), place(23, None),
                 place(24, pf.exterior_key(1, 1), interior=False)]
        src = sources(rooms={9: {'map': 'r.chim', 'kind': 'chim', 'record': None, 'entities': {}}},
                      room_placements={9: {21}})
        census.judge_world(items, src)
        by = {p['reference']: p['build'] for p in items}
        self.assertIn('no use-table row: the record has no name', by[21]['gaps'])
        self.assertIn('not built: its room map is not in the image', by[22]['gaps'])
        self.assertTrue(by[23]['gaps'][0].startswith('no place key'))
        self.assertIn('not drawn: no placed list row, frame map entity or CHIM piece', by[24]['gaps'])
        t = census.world_tally(('Morrowind.esm',), items)
        self.assertEqual(t['totals']['all']['interior']['all']['placed'], 3)
        self.assertEqual(t['gaps']['no use-table row: the record has no name']['items'], 1)
        self.assertIn('| interior | misc | 3 |', census.world_md(t))

    def test_the_window_counts_rows_in_the_engines_order(self):
        # a room alone; outdoors the 3 x 3 cells, dx outer, dy inner (aw_inventory.c focus_load)
        import prepare_focus as pf
        self.assertEqual(census.window_keys(763), [763])
        keys = census.window_keys(pf.exterior_key(0, 0))
        self.assertEqual(keys[0], pf.exterior_key(-1, -1))
        self.assertEqual(keys[1], pf.exterior_key(-1, 0))
        self.assertEqual(len(keys), 9)
        rows = {763: [row('A', 1)] * census.FOCUS_ROWS + [row('I', 2)]}
        self.assertNotIn(2, census.item_slots(rows, 763))

    def test_the_rules_judged_by_are_the_engines(self):
        inventory = (ROOT / 'engine/aga/src/aw_inventory.c').read_text(encoding='utf-8')
        self.assertTrue(census.PLACED_INDOORS_UNDRAWN_ONLY)
        self.assertIn('if(focus_rows[j].drawn || focus_rows[j].live || (!focus_outdoor && !focus_rows[j].edict))'
                      '{placed_seen[3]++;continue;}', inventory)
        self.assertTrue(census.PIECES_HIDDEN_BY_ROW)
        self.assertIn("if(r[0]=='P' && ref_stable((unsigned)focus_u32(r+8))==stable){", inventory)
        self.assertIn('ChimChunks_GonePid((unsigned)focus_u32(r+4),hide);n++;', inventory)
        self.assertIn('#define FOCUS_ROWS 1536', inventory)
        self.assertEqual(census.FOCUS_ROWS, 1536)
        self.assertEqual(census.stable_of_merged((1 << 22) | 1003), (1 << 20) | 1003)

    def test_the_verdict_is_a_ratchet(self):
        known = {'a gap': ('OUTDOOR-ITEM-CHIM-COPY-STAYS-69', 10)}
        self.assertEqual(census.world_verdict({'gaps': {'a gap': {'items': 10}}}, known), [])
        self.assertEqual(len(census.world_verdict({'gaps': {'a gap': {'items': 11}}}, known)), 1)
        self.assertEqual(len(census.world_verdict({'gaps': {'new': {'items': 1}}}, known)), 1)

    def test_the_image_step_arguments_are_read_from_the_build_state(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            state = {'steps': [{'command': ['python3', '/src/tools/build_aga.py', 'engine', '--out', '/x']},
                               {'command': ['python3', '/src/tools/build_aga.py', 'image', '--chim-layer-world',
                                            'chimsol=/run/sol', '--chim-layer-world', 'chimmh=/run/mh',
                                            '--presented-cells', '-12,-30:l -12,-29:l', '--jobs', '24']}]}
            (Path(tmp) / 'build-state.json').write_text(json.dumps(state), encoding='utf-8')
            args = census.image_step_args(tmp)
        self.assertEqual(args['--chim-layer-world'], ['chimsol=/run/sol', 'chimmh=/run/mh'])
        self.assertEqual(args['--presented-cells'], ['-12,-30:l -12,-29:l'])
        self.assertNotIn('--out', args)

    def test_committed_measurement_holds(self):
        # the newest measurement of docs/performance/WORLD_ITEMS.json: every gap has its register entry and stays
        # within its count (an item that stops being drawn, aimed at or taken, or a new reason, fails the gate)
        import json
        data = json.loads(MEASUREMENT.read_text(encoding='utf-8'))
        newest = data['measurements'][-1]
        self.assertEqual(newest['schema'], census.WORLD_SCHEMA)
        self.assertEqual(census.world_verdict(newest), [])
        bugs = {b['id'] for b in json.loads((ROOT / 'docs/bugs/bugs.json').read_text(encoding='utf-8'))}
        for reason, (ids, _count) in census.KNOWN_GAPS.items():
            for ident in ids.split():
                self.assertIn(ident, bugs, reason)
        for master, sides in newest['totals'].items():
            for side, cats in sides.items():
                for cat, v in cats.items():
                    self.assertTrue(v['takeable'] <= v['aimable'] <= v['drawn'] <= v['in_build'] <= v['placed'],
                                    (master, side, cat))
                    self.assertLessEqual(v['owner_kept'], v['owned'])


if __name__ == '__main__':
    unittest.main()
