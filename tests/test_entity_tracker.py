# SPDX-License-Identifier: GPL-3.0-only
"""Entity tracker on a synthetic master and synthetic maps (no game data)."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import entity_tracker as et  # noqa: E402


def sub(tag, data):
    return struct.pack('<4sI', tag.encode(), len(data)) + data


def record(tag, *subs):
    body = b''.join(subs)
    return struct.pack('<4sIII', tag.encode(), len(body), 0, 0) + body


def z(text):
    return text.encode('cp1252') + b'\0'


def base(tag, ident, model=''):
    return record(tag, sub('NAME', z(ident)), *([sub('MODL', z(model))] if model else []))


def ref(number, ident, deleted=False):
    out = sub('FRMR', struct.pack('<I', number)) + sub('NAME', z(ident))
    out += sub('DATA', struct.pack('<6f', 0, 0, 0, 0, 0, 0))
    return out + (sub('DELE', b'\0\0\0\0') if deleted else b'')


def cell(name, interior, x=0, y=0, refs=b''):
    return record('CELL', sub('NAME', z(name)), sub('DATA', struct.pack('<Iii', 1 if interior else 0, x, y)), refs)


def bsp(*numbers, version=29):
    text = '{\n"classname" "worldspawn"\n}\n' + ''.join(
        '{\n"classname" "func_wall"\n"aw_ref" "%d"\n"model" "*1"\n}\n' % n for n in numbers)
    data = text.encode('ascii')
    header = struct.pack('<i', version) + struct.pack('<ii', 4 + 15 * 8, len(data)) + b'\0' * (14 * 8)
    return header + data


BASES = [
    base('STAT', 'rock_a', 'x\\terrain_rock_ai_01.nif'),
    base('STAT', 'parasol', 'f\\flora_emp_parasol_01.nif'),
    base('STAT', 'tree', 'f\\flora_tree_bc_01.nif'),
    base('STAT', 'grass', 'f\\flora_grass_01.nif'),
    base('STAT', 'wall', 'x\\ex_common_wall.nif'),
    base('CONT', 'plant_c', 'o\\flora_marshmerrow_01.nif'),
    base('CONT', 'barrel', 'o\\contain_barrel_01.nif'),
    base('NPC_', 'villager'), base('CREA', 'mudcrab'), base('LEVC', 'random_crab'),
    base('MISC', 'cup'), base('LIGH', 'lamp'), base('DOOR', 'door'), base('ACTI', 'sign', 'x\\sign_01.nif'),
    base('STAT', 'hook', 'f\\furn_de_shack_hook.nif'), base('CREA', 'rat', 'r\\rat.nif'),
    # A dialogue topic sharing an object's name must not change its category.
    record('DIAL', sub('NAME', z('rock_a'))),
]
MASTER = b''.join(BASES + [
    cell('Town', False, 0, 0, ref(1, 'rock_a') + ref(2, 'rock_a') + ref(3, 'parasol') + ref(4, 'tree')
         + ref(5, 'grass') + ref(6, 'wall') + ref(7, 'plant_c') + ref(8, 'barrel') + ref(9, 'villager')
         + ref(10, 'mudcrab') + ref(11, 'door') + ref(12, 'cup', deleted=True)),
    cell('', False, 1, 0, ref(20, 'rock_a') + ref(21, 'random_crab') + ref(22, 'wall') + ref(23, 'rock_a')),
    cell('Town, Shop', True, refs=ref(30, 'cup') + ref(31, 'lamp') + ref(32, 'sign') + ref(33, 'barrel')
         + ref(34, 'hook') + ref(35, 'rat')),
])


class CategoryTests(unittest.TestCase):
    def test_converter_classifiers_decide_categories(self):
        rows, unresolved = et.census(MASTER)
        cats = {number: cat for number, cat, _, _ in rows}
        self.assertEqual(unresolved, 0)
        self.assertEqual([cats[n] for n in (1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 21, 30, 31, 32)],
                         ['rock', 'giant_mushroom', 'tree', 'plant', 'static', 'harvest_plant', 'container',
                          'npc', 'creature', 'door', 'creature', 'item', 'light', 'activator'])

    def test_exterior_references_carry_no_interior_rule(self):
        rows, _ = et.census(MASTER)
        self.assertEqual({r[3] for r in rows if r[2].startswith('exterior:')}, {None})

    def test_deleted_references_are_not_counted(self):
        rows, _ = et.census(MASTER)
        self.assertNotIn(12, {r[0] for r in rows})

    def test_repeated_reference_numbers_are_rejected(self):
        master = b''.join(BASES + [cell('A', True, refs=ref(1, 'wall')), cell('B', True, refs=ref(1, 'wall'))])
        with self.assertRaisesRegex(ValueError, 'not unique'):
            et.census(master)


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.rows, _ = et.census(MASTER)
        # Town converted except rock 2; the (1,0) cell has no map; the shop has its door-less items.
        self.placed = {1, 3, 4, 5, 6, 7, 8, 9, 11, 30, 31, 999}
        self.result = et.report(self.rows, self.placed, 2, 'sha')

    def test_counts_and_reasons(self):
        t = self.result['totals']
        self.assertEqual(t['rock']['exterior'], dict(original=4, placed=1, cell_not_converted=2,
                                                    outside_world_scope=0, deliberately_skipped=0,
                                                    category_not_implemented=0, not_placed=1))
        self.assertEqual(t['creature']['exterior']['category_not_implemented'], 1)
        self.assertEqual(t['creature']['exterior']['cell_not_converted'], 1)
        self.assertEqual(t['activator']['interior'], dict(original=1, placed=0, cell_not_converted=0,
                                                         outside_world_scope=0, deliberately_skipped=1,
                                                         category_not_implemented=0, not_placed=0))
        self.assertEqual(t['container']['interior']['not_placed'], 1)
        self.assertEqual(t['static']['interior']['deliberately_skipped'], 1)
        # The interior rule outranks "category not implemented" (no creature is placed anywhere).
        self.assertEqual(t['creature']['interior']['deliberately_skipped'], 1)
        self.assertEqual(self.result['skipped'], {'fine dressing deferred': 1, 'small item or actor deferred': 1,
                                                  'unsupported activator': 1})
        self.assertEqual(self.result['placed_numbers_not_in_master'], 1)
        self.assertEqual(self.result['converted_cells'], ['exterior:0,0', 'interior:Town, Shop'])
        self.assertEqual(self.result['cells']['exterior:0,0']['rock'], [2, 1])

    def test_every_original_placement_has_one_outcome(self):
        for cat, spaces in self.result['totals'].items():
            for space, row in spaces.items():
                self.assertEqual(row['original'], row['placed'] + sum(row[r] for r in et.REASONS), (cat, space))

    def test_maps_are_read_from_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'maps').mkdir()
            (Path(tmp) / 'maps' / 'a.bsp').write_bytes(bsp(1, 3))
            (Path(tmp) / 'maps' / 'B.BSP').write_bytes(bsp(3, 9))
            (Path(tmp) / 'maps' / 'vf0012.bsp').write_bytes(bsp(9, 20))
            (Path(tmp) / 'maps' / 'notes.txt').write_text('"aw_ref" "4"')
            self.assertEqual(et.placed_from_dirs([tmp]), ({1, 3, 9, 20}, {1, 3, 9}, 3))

    def test_world_maps_only_answer_for_their_categories(self):
        # Cell (1,0) is reached only by a world map, which carries rocks.
        result = et.report(self.rows, self.placed | {20}, 3, 'sha', full=self.placed)
        t = result['totals']
        self.assertEqual(t['static']['exterior']['outside_world_scope'], 1)
        self.assertEqual(t['creature']['exterior']['outside_world_scope'], 1)
        self.assertEqual(t['rock']['exterior']['not_placed'], 2)
        self.assertEqual(result['world_only_cells'], 1)
        self.assertEqual(result['full_cells'], ['exterior:0,0', 'interior:Town, Shop'])

    def test_non_bsp29_maps_are_rejected(self):
        with self.assertRaises(ValueError):
            et.bsp_refs(bsp(1, version=30))


class CompareTests(unittest.TestCase):
    def setUp(self):
        self.rows, _ = et.census(MASTER)
        self.old = et.report(self.rows, {1, 3, 4, 9, 30}, 1, 'sha')

    def test_unchanged_build_passes(self):
        self.assertEqual(et.compare(self.old, et.report(self.rows, {1, 3, 4, 9, 30}, 1, 'sha')), [])

    def test_vanished_category_fails(self):
        problems = et.compare(self.old, et.report(self.rows, {1, 3, 4, 30}, 1, 'sha'))
        self.assertEqual(problems, ['exterior npc: 1 placed before, none now'])

    def test_large_loss_fails_and_small_loss_passes(self):
        old = {'totals': {'rock': {'exterior': {'placed': 1000}}}}
        new = {'totals': {c: {s: {'placed': 0} for s in ('exterior', 'interior')} for c in et.CATEGORIES}}
        new['totals']['rock']['exterior']['placed'] = 991
        self.assertEqual(et.compare(old, new), [])
        new['totals']['rock']['exterior']['placed'] = 900
        self.assertEqual(et.compare(old, new), ['exterior rock: 1000 -> 900 placed (-100)'])

    def test_build_gate_stops_unexplained_loss(self):
        with tempfile.TemporaryDirectory() as tmp:
            import json
            tmp = Path(tmp); (tmp / 'maps').mkdir(); (tmp / 'out').mkdir()
            master = tmp / 'master.esm'; master.write_bytes(MASTER)
            (tmp / 'maps' / 'town.bsp').write_bytes(bsp(1, 9, 30))
            first = et.build_gate(tmp / 'out', tmp / 'maps', master)
            self.assertEqual(first['losses'], [])
            baseline = tmp / 'baseline.json'
            baseline.write_bytes((tmp / 'out' / 'entity-tracker.json').read_bytes())
            self.assertEqual(json.loads(baseline.read_text())['totals']['npc']['exterior']['placed'], 1)
            (tmp / 'maps' / 'town.bsp').write_bytes(bsp(1, 30))
            with self.assertRaisesRegex(ValueError, 'exterior npc: 1 placed before, none now'):
                et.build_gate(tmp / 'out', tmp / 'maps', master, baseline)
            accepted = et.build_gate(tmp / 'out', tmp / 'maps', master, baseline, 'villager moved to an interior')
            self.assertEqual(accepted['losses'], ['exterior npc: 1 placed before, none now'])
            self.assertEqual(accepted['accepted_loss'], 'villager moved to an interior')

    def test_image_build_runs_the_gate_on_final_maps_before_any_disk(self):
        source = (ROOT / 'tools' / 'build_aga.py').read_text(encoding='utf-8')
        finalize = source[source.index('def finalize_image(args):'):source.index('\ndef main():')]
        gate = finalize.index('entity_gate(out, boot/')
        self.assertLess(finalize.index('require_actor_ground('), gate)
        self.assertLess(gate, finalize.index("part=out/'partition.hdf'"))
        self.assertIn("build_record['entity_tracker'] = entity_tracker", finalize)

    def test_cli_compare_exit_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            import json
            a, b = Path(tmp) / 'a.json', Path(tmp) / 'b.json'
            a.write_text(json.dumps(self.old))
            b.write_text(json.dumps(et.report(self.rows, set(), 1, 'sha')))
            self.assertEqual(et.main(['compare', str(a), str(a)]), 0)
            self.assertEqual(et.main(['compare', str(a), str(b)]), 1)


if __name__ == '__main__':
    unittest.main()
