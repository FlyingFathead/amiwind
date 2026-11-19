# SPDX-License-Identifier: GPL-3.0-only
"""The placed things of the presented districts, keyed outdoors (MOURNHOLD-EXTERIOR-CELLS-66).

In the game data a district of Mournhold is an interior cell; the build presents it as an exterior cell block of its
own (tools/presented_exterior.py) and the game there is outdoors: it asks the focus table, the areas' levelled
creatures and the placed item list for the exterior cells around the player. The readers keyed a district's rows by
its room number at the original positions, so no container, item, activator or door of a district could be aimed at.
With the build's presented places (tools/prepare_focus.py cells_presented) the rows are under the block's exterior
keys at the moved positions. Held here on small synthetic masters (no game data):

- the rows of a presented cell are under its block's keys at the moved positions, none under its room number;
- a row's position is the presented master's own placement of the same reference;
- the base game alone is byte-identical: without places every reader gives what the code before the change gave
  (that code is kept here as the reference), and cells_of itself is the function before the change;
- the plan: without the module no stage command names the receipt; with it the focus and item-models stages take it
  and wait for the module's data stage;
- the first-minute check passes on a sound master and names a district whose counts differ."""
import hashlib
import inspect
import struct
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import actor_stats  # noqa: E402
import build  # noqa: E402
import build_parallel  # noqa: E402
import build_preflight  # noqa: E402
import expansion_preflight  # noqa: E402
import prepare_focus as pf  # noqa: E402
import prepare_item_models  # noqa: E402
import presented_exterior as pe  # noqa: E402
from mwad.esm import records, string, subrecords  # noqa: E402

CONFIG = {'first_block': [-12, -30], 'spacing': 4, 'max_block': 2}
CELLS = '-12,-30:l -11,-30:l -8,-30:l'


def sub(tag, data):
    if isinstance(data, str):
        data = data.encode('cp1252') + b'\0'
    return struct.pack('<4sI', tag.encode(), len(data)) + data


def rec(tag, *subs, flags=0):
    payload = b''.join(subs)
    return struct.pack('<4sIII', tag.encode(), len(payload), 0, flags) + payload


def ref(number, ident, pos, *extra, angles=(0, 0, 0)):
    return (sub('FRMR', struct.pack('<I', number)) + sub('NAME', ident) + b''.join(extra) +
            sub('DATA', struct.pack('<6f', *pos, *angles)))


def interior(name, flags, *refs):
    return rec('CELL', sub('NAME', name), sub('DATA', struct.pack('<Iff', flags, 0.0, 0.0)), *refs)


def exterior(x, y, *refs):
    return rec('CELL', sub('NAME', ''), sub('DATA', struct.pack('<Iii', 0, x, y)), *refs)


def master(plaza_extra=()):
    """A base exterior cell with a cup, a room with a cup and a door into the plaza, a plaza (flag 0x87) two cells
    wide with a crate, two cups, a merchant, a door back, a levelled creature and a reference without a position,
    and a one-cell yard (flag 0x87) with a crate."""
    parts = [
        rec('TES3', sub('HEDR', struct.pack('<fI32s256sI', 1.3, 1, b'', b'', 0))),
        rec('MISC', sub('NAME', 'cup'), sub('MODL', 'm\\cup.nif'), sub('FNAM', 'Cup'),
            sub('MCDT', struct.pack('<fii', .5, 2, 0))),
        rec('CONT', sub('NAME', 'crate'), sub('MODL', 'o\\crate.nif'), sub('FNAM', 'Crate'),
            sub('CNDT', struct.pack('<f', 100.0)), sub('FLAG', struct.pack('<I', 8)),
            sub('NPCO', struct.pack('<i32s', 2, b'cup'))),
        rec('NPC_', sub('NAME', 'merchant'), sub('FNAM', 'A Merchant')),
        rec('DOOR', sub('NAME', 'door_a'), sub('FNAM', 'Wooden Door')),
        rec('LEVC', sub('NAME', 'lev_rat'), sub('DATA', struct.pack('<I', 0)), sub('NNAM', b'\0'),
            sub('INDX', struct.pack('<I', 0))),
        exterior(0, 0, ref(1, 'cup', (100, 100, 0))),
        interior('Town, Room', 0x01, ref(2, 'door_a', (10, 20, 30), sub('DODT', struct.pack('<6f', -5000, 100, 8, 0, 0, 0)),
                                         sub('DNAM', 'Town, Plaza')),
                 ref(3, 'cup', (5, 6, 7))),
        interior('Town, Plaza', 0x87,
                 ref(4, 'crate', (-5000, -1000, 0), sub('ANAM', 'merchant'), angles=(0, 0, 1.0)),
                 ref(5, 'cup', (5000, 1000, 64)),
                 ref(6, 'door_a', (-5000, 0, 8), sub('DODT', struct.pack('<6f', 10, 30, 30, 0, 0, 0)),
                     sub('DNAM', 'Town, Room')),
                 ref(7, 'merchant', (4000, 0, 8)),
                 ref(8, 'cup', (-100, 50, 20), sub('XSCL', struct.pack('<f', 1.5))),
                 ref(9, 'lev_rat', (4500, 10, 0)),
                 sub('FRMR', struct.pack('<I', 10)) + sub('NAME', 'cup'),
                 *plaza_extra),
        interior('Town, Yard', 0x87, ref(11, 'crate', (0, 0, 3000)), ref(12, 'crate', (200, 200, 3100))),
    ]
    return b''.join(parts)


NUMBERS = {'town, room': 5, 'town, plaza': 6, 'town, yard': 7}


# tools/prepare_focus.py cells_of as it was before the districts' rows were keyed outdoors (v0.0.67-dev2), kept as
# the reference: the readers without presented places must give what they gave through this.
def old_cells_of(raw):
    """Every live CELL record: (name, interior, grid x, grid y, region id, its references)."""
    for tag, flags, payload in records(raw):
        if tag != 'CELL' or flags & 0x20:
            continue
        cell = None; interior = False; grid = (0, 0); region = ''; current = None; refs = []
        for key, value in subrecords(payload):
            if current is None and key == 'NAME' and cell is None:
                cell = string(value, 'NAME', errors='replace')
            elif current is None and key == 'DATA' and len(value) == 12:
                interior = bool(struct.unpack('<I', value[:4])[0] & 1)
                grid = struct.unpack_from('<ii', value, 4)
            elif current is None and key == 'RGNN':
                region = string(value, 'RGNN', errors='replace').casefold()
            elif key == 'FRMR':
                current = {'number': struct.unpack('<I', value)[0]}; refs.append(current)
            elif current is not None:
                current.setdefault(key, value)
        yield cell or '', interior, grid, region, refs


def digest(value):
    return hashlib.sha256(repr(value).encode()).hexdigest()


class Base(unittest.TestCase):
    def setUp(self):
        self.raw = master()
        self.presented, self.receipt = pe.present(self.raw, CONFIG)
        self.places = pe.receipt_places(self.receipt)
        self.objects = pf.objects_of(self.raw, pf.item_lists(self.raw))

    def block_keys(self, name):
        place = self.places[name]
        return [pf.exterior_key(place['block'][0] + dx, place['block'][1] + dy)
                for dx in range(place['size'][0]) for dy in range(place['size'][1])]


class TheRowsOfAPresentedCell(Base):
    def test_the_fixture_is_two_blocks(self):
        self.assertEqual({k: (p['block'], p['size']) for k, p in self.places.items()},
                         {'town, plaza': ([-12, -30], [2, 1]), 'town, yard': ([-8, -30], [1, 1])})

    def test_as_a_room_the_rows_are_under_the_room_number(self):
        # the behaviour before: the game outdoors asks the block's keys and finds nothing there
        rooms = pf.placements(self.raw, self.objects, NUMBERS)
        self.assertEqual(sorted(r[2] for r in rooms[6]), [4, 5, 6, 7, 8])
        for key in self.block_keys('town, plaza') + self.block_keys('town, yard'):
            self.assertNotIn(key, rooms)

    def test_with_the_places_they_are_under_the_blocks_keys_at_the_moved_positions(self):
        rooms = pf.placements(self.raw, self.objects, NUMBERS, presented=self.places)
        self.assertNotIn(6, rooms)
        self.assertNotIn(7, rooms)
        west, east = self.block_keys('town, plaza')
        self.assertEqual(sorted(r[2] for r in rooms[west]), [4, 6, 8])
        self.assertEqual(sorted(r[2] for r in rooms[east]), [5, 7])
        self.assertEqual(sorted(r[2] for r in rooms[self.block_keys('town, yard')[0]]), [11, 12])
        offset = self.places['town, plaza']['offset']
        cup = next(r for r in rooms[east] if r[2] == 5)
        self.assertEqual(cup[3:6], (5000 + offset[0], 1000 + offset[1], 64.0))      # the height is kept
        self.assertEqual((cup[0], cup[8], cup[9]), ('I', 'Cup', 'cup'))
        door = next(r for r in rooms[west] if r[2] == 6)
        self.assertEqual((door[0], door[8]), ('D', 'Town, Room'))
        # the room's own rows and the base cell's are the ones before
        before = pf.placements(self.raw, self.objects, NUMBERS)
        self.assertEqual(rooms[5], before[5])
        self.assertEqual(rooms[pf.exterior_key(0, 0)], before[pf.exterior_key(0, 0)])
        # a door into the district still says the district's name
        self.assertEqual(next(r for r in rooms[5] if r[2] == 2)[8], 'Town, Plaza')

    def test_the_same_rows_by_count_and_kind(self):
        before = pf.placements(self.raw, self.objects, NUMBERS)
        after = pf.placements(self.raw, self.objects, NUMBERS, presented=self.places)
        self.assertEqual(sum(len(v) for v in before.values()), sum(len(v) for v in after.values()))
        counts = pf.presented_counts(after, NUMBERS, self.places)
        self.assertEqual(counts['Town, Plaza'], {'rows': 5, 'kinds': {'A': 1, 'C': 1, 'D': 1, 'I': 2},
                                                 'cells': {'-12,-30': 3, '-11,-30': 2}, 'left_in_room': 0})
        self.assertEqual(pf.presented_counts(before, NUMBERS, self.places)['Town, Plaza']['left_in_room'], 5)

    def test_a_row_stands_where_the_presented_master_places_the_reference(self):
        # the reader and the master cannot drift: the same bytes, reference by reference, cell by cell
        own = {}
        for cell, interior, grid, _region, refs in pf.cells_of(self.presented):
            if not interior:
                for r in refs:
                    own[r['number']] = (tuple(grid), r.get('DATA'))
        seen = 0
        for cell, interior, grid, _region, refs in pf.cells_presented(self.raw, self.places):
            if interior or cell.casefold() not in self.places:
                continue
            for r in refs:
                self.assertEqual(own[r['number']], (tuple(grid), r.get('DATA')), r['number'])
                seen += 1
        self.assertEqual(seen, 9)          # the plaza's seven (one without a position) and the yard's two

    def test_a_reference_without_a_position_stays_with_the_blocks_first_cell(self):
        cells = {tuple(grid): [r['number'] for r in refs]
                 for cell, interior, grid, _r, refs in pf.cells_presented(self.raw, self.places)
                 if cell == 'Town, Plaza'}
        self.assertEqual(cells, {(-12, -30): [4, 6, 8, 10], (-11, -30): [5, 7, 9]})

    def test_the_masters_own_references_are_not_changed(self):
        before = [(cell, [dict(r) for r in refs]) for cell, _i, _g, _r, refs in pf.cells_of(self.raw)]
        list(pf.cells_presented(self.raw, self.places))
        self.assertEqual(before, [(cell, refs) for cell, _i, _g, _r, refs in pf.cells_of(self.raw)])

    def test_a_placement_outside_its_block_is_refused(self):
        places = {'town, yard': dict(self.places['town, yard'], offset=[0.0, 0.0])}
        with self.assertRaisesRegex(ValueError, 'outside its presented block'):
            list(pf.cells_presented(self.raw, places))

    def test_a_containers_box_is_made_from_the_moved_position(self):
        boxes = {'o\\crate.nif': ((-10.0, -20.0, 0.0), (10.0, 20.0, 30.0))}
        with mock.patch.dict(pf.CONTAINER_BOXES, boxes):
            objects = pf.objects_of(self.raw, pf.item_lists(self.raw))
            room = {r[2]: r for r in pf.placements(self.raw, objects, NUMBERS)[6]}
            moved = {r[2]: r for rows in pf.placements(self.raw, objects, NUMBERS, presented=self.places).values()
                     for r in rows}
        offset = self.places['town, plaza']['offset']
        self.assertIsInstance(room[4][9], bytes)
        self.assertEqual(moved[4][9], room[4][9])                    # the same box and rotation
        for axis in (0, 1):
            self.assertAlmostEqual(moved[4][3 + axis], room[4][3 + axis] + offset[axis], places=3)
        self.assertAlmostEqual(moved[4][5], room[4][5], places=5)

    def test_the_levelled_creatures_and_the_placed_items_follow(self):
        east = self.block_keys('town, plaza')[1]
        self.assertEqual(list(actor_stats.levelled_by_area(self.raw, NUMBERS)), [6])
        self.assertEqual(list(actor_stats.levelled_by_area(self.raw, NUMBERS, self.places)), [east])
        items = {'cup': {'source_model': 'm\\cup.nif'}}
        from prepare_inventory import mesh_key
        table = {mesh_key('m\\cup.nif'): 'progs/items/m0123456789abcdef.mdl'}
        before, _ = prepare_item_models.placement_list(self.raw, items, table, NUMBERS)
        after, _ = prepare_item_models.placement_list(self.raw, items, table, NUMBERS, self.places)
        self.assertEqual(sorted(r[0] for r in before[6]), [5, 8])
        west = self.block_keys('town, plaza')[0]
        self.assertNotIn(6, after)
        offset = self.places['town, plaza']['offset']
        self.assertEqual([(r[0], r[3], r[4], r[5], r[9]) for r in after[west]],
                         [(8, -100 + offset[0], 50 + offset[1], 20.0, 1.5)])
        self.assertEqual([r[0] for r in after[east]], [5])
        self.assertEqual(after[5], before[5])
        prepare_item_models.check_placed(after)


class TheBaseGameAloneIsByteIdentical(Base):
    def test_cells_of_is_the_function_before_the_change(self):
        # a unit cache whose code reach holds cells_of keeps its key: the presented cells are a function beside it
        def lines(function):
            return [ln for ln in inspect.getsource(function).splitlines()[1:] if not ln.strip().startswith('"""')]
        self.assertEqual(lines(pf.cells_of), lines(old_cells_of))

    def test_without_places_the_cells_are_cells_ofs_own(self):
        for places in (None, {}):
            self.assertEqual(list(pf.cells_presented(self.raw, places)), list(old_cells_of(self.raw)))
        # and with places that name no cell of the master
        self.assertEqual(list(pf.cells_presented(self.raw, {'elsewhere': self.places['town, yard']})),
                         list(old_cells_of(self.raw)))

    def test_every_reader_gives_what_the_code_before_gave(self):
        items = {'cup': {'source_model': 'm\\cup.nif'}}
        from prepare_inventory import mesh_key
        table = {mesh_key('m\\cup.nif'): 'progs/items/m0123456789abcdef.mdl'}

        def read(places):
            extras = {}
            rooms = pf.placements(self.raw, self.objects, NUMBERS, extras, places)
            return digest([sorted(rooms.items()), sorted(extras.items()),
                           sorted(actor_stats.levelled_by_area(self.raw, NUMBERS, places).items()),
                           sorted(prepare_item_models.placement_list(self.raw, items, table, NUMBERS, places)[0].items()),
                           prepare_item_models.pack_placed(
                               prepare_item_models.placement_list(self.raw, items, table, NUMBERS, places)[0])])
        with mock.patch.object(pf, 'cells_presented', lambda raw, places=None: old_cells_of(raw)):
            reference = read(None)
        self.assertEqual(read(None), reference)
        self.assertEqual(read({}), reference)
        self.assertNotEqual(read(self.places), reference)

    def test_the_stages_without_a_receipt_read_no_places(self):
        self.assertEqual(pf.presented_places(None, CELLS), {})
        for module in (pf, prepare_item_models):
            text = inspect.getsource(module.main)
            self.assertIn("'--presented-receipt'", text)
            self.assertIn('presented_places(a.presented_receipt, a.presented_cells)', text)
        # the focus receipt gains its district counts only with places
        self.assertIn("if presented:\n        # only with presented districts", inspect.getsource(pf.build))

    def test_the_places_of_a_receipt_are_the_districts_the_build_converts_whole(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'presented-data.json'
            path.write_text(json.dumps({'presented_cells': self.receipt['cells']}), encoding='utf-8')
            self.assertEqual(sorted(pf.presented_places(path, CELLS)), ['town, plaza', 'town, yard'])
            self.assertEqual(sorted(pf.presented_places(path, '-12,-30:l -8,-30:l')), ['town, yard'])


def tool(name, *parts):
    return ['python3', name, *[str(p) for p in parts]]


def base_steps():
    return [('census', tool('census.py', '--data-files', '/data')),
            ('mwscript', tool('prepare_mwscript.py', '--data-files', '/data', '--out', '/run/mwscript')),
            ('focus', tool('prepare_focus.py', '--data-files', '/data', '--out', '/run/focus')),
            ('item-models', tool('prepare_item_models.py', '--data-files', '/data', '--out', '/run/item-models')),
            ('books', tool('prepare_books.py', '--data-files', '/data', '--out', '/run/books')),
            ('chim', tool('chim_build.py', '--area', 'seyda', '--data-files', '/data', '--out', '/run/chim-world',
                          '--lighting-type', 'hybrid', '--chim-regions-cells', '1,1:l')),
            ('image', tool('build_aga.py', 'image', '--data-files', '/data'))]


def module_steps(cells=CELLS):
    args = SimpleNamespace(tribunal_mournhold_cells=cells, chim_regions_cells='1,1:l', data_files='/data',
                           workspace=Path('/ws'), sdk='/sdk')
    return build.tribunal_mournhold_commands(args, base_steps(), tool, Path('/run'), {'qbsp': '/tools/qbsp'}, 8)


LEFT_OUT = {'intro', 'world-terrain', 'world-scenery', 'music', 'media', 'engine', 'dialogue-lookup', 'npc-gallery',
            'chargen', 'harvest', 'hand-catalog', 'world-flora', 'chim-interiors', 'chim-room-batches', 'seam-audit'}


class ThePlan(unittest.TestCase):
    def test_without_the_module_no_stage_names_the_receipt(self):
        for cells in (None, ''):
            steps = module_steps(cells)
            self.assertEqual(steps, base_steps())
            self.assertFalse(any('--presented-receipt' in command for _, command in steps))

    def test_with_the_module_the_two_stages_take_the_receipt_after_their_unchanged_command(self):
        commands, before = dict(module_steps()), dict(base_steps())
        receipt = str(Path('/run') / 'tribunal-mournhold-data' / 'presented-data.json')
        self.assertEqual(build.TRIBUNAL_MOURNHOLD_READERS, ('image', 'mwscript', 'focus', 'item-models'))
        for name in build.TRIBUNAL_MOURNHOLD_READERS:
            self.assertEqual(commands[name][:len(before[name])], before[name], name)
            self.assertEqual(commands[name][len(before[name]):],
                             ['--presented-receipt', receipt, '--presented-cells', CELLS], name)
        for name in ('census', 'books', 'chim'):
            self.assertEqual(commands[name], before[name], name)
        build_parallel.require_plan_arguments(module_steps())

    def test_the_two_stages_wait_for_the_modules_data_stage_and_no_one_else_does(self):
        with_module = build_parallel.stage_dependencies(module_steps(), LEFT_OUT)
        without = build_parallel.stage_dependencies(base_steps(), LEFT_OUT)
        for name in ('focus', 'item-models'):
            self.assertEqual(set(with_module[name]) - set(without[name]), {'tribunal-mournhold-data'}, name)
            self.assertNotIn('tribunal-mournhold', with_module[name])        # never for the districts' world
        for name in ('census', 'books', 'chim'):
            self.assertEqual(with_module[name], without[name], name)

    def test_the_stages_parsers_take_the_options(self):
        for module in (pf, prepare_item_models):
            text = inspect.getsource(module.main)
            self.assertIn("'--presented-receipt'", text)
            self.assertIn("'--presented-cells'", text)


class TheFirstMinuteCheck(Base):
    def test_the_check_is_registered_for_the_first_minute(self):
        entry = [e for e in build_preflight.EARLY_CHECKS if e[0] == 'district-tables']
        self.assertEqual(entry, [('district-tables', 'inputs', 'expansion_preflight:district_tables')])

    def test_nothing_to_check_without_the_modules_cells(self):
        said = []
        for args in (None, SimpleNamespace(tribunal_mournhold_cells=None, data_files='/data'),
                     SimpleNamespace(tribunal_mournhold_cells='', data_files='/data')):
            context = build_preflight.EarlyContext('inputs', args, log=said.append)
            self.assertEqual(expansion_preflight.district_tables(context), [])
        self.assertEqual(said, [])

    def test_the_places_before_any_stage_are_the_receipts(self):
        made = expansion_preflight.module_places(self.raw, CELLS, CONFIG)
        self.assertEqual(made, pe.build_places(self.receipt, pe.cells_of_text(CELLS))[0])
        self.assertEqual(sorted(expansion_preflight.module_places(self.raw, '-8,-30:l', CONFIG)), ['town, yard'])

    def test_a_sound_master_passes_and_says_its_counts(self):
        said = []
        self.assertEqual(expansion_preflight.district_table_problems(self.raw, self.places, said.append), [])
        self.assertEqual(len(said), 2)
        self.assertIn('Town, Plaza: 7 references, 5 placed things outdoors', said[0])
        self.assertIn("'-12,-30': 3", said[0])
        self.assertIn('Town, Yard: 2 references, 2 placed things outdoors', said[1])

    def test_a_district_whose_counts_differ_is_named(self):
        # a reader that loses a row on the way (here: the east cell's rows dropped)
        real = pf.cells_presented

        def lossy(raw, places=None):
            for cell, interior, grid, region, refs in real(raw, places):
                yield cell, interior, grid, region, ([] if tuple(grid) == (-11, -30) and not interior else refs)
        with mock.patch.object(pf, 'cells_presented', lossy):
            problems = expansion_preflight.district_table_problems(self.raw, self.places, lambda line: None)
        self.assertEqual(len(problems), 2)
        self.assertIn('Town, Plaza: 7 references in its cell, 4 in the cells of its block', problems[0])
        self.assertIn('Town, Plaza: 5 placed things', problems[1])
        self.assertIn('3 {', problems[1])

    def test_a_placement_outside_its_block_is_one_problem(self):
        places = {'town, yard': dict(self.places['town, yard'], offset=[0.0, 0.0])}
        problems = expansion_preflight.district_table_problems(self.raw, places, lambda line: None)
        self.assertEqual(len(problems), 1)
        self.assertIn('outside its presented block', problems[0])

    def test_a_window_over_the_engines_table_is_named(self):
        with mock.patch.object(pf, 'WINDOW_ROWS', 4):
            problems = expansion_preflight.district_table_problems(self.raw, self.places, lambda line: None)
        self.assertTrue(problems)
        self.assertTrue(all('3 x 3 cells around' in p and 'Town, Plaza' in p for p in problems), problems)


if __name__ == '__main__':
    unittest.main()
