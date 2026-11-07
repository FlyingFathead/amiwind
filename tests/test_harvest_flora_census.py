# SPDX-License-Identifier: GPL-3.0-only
"""The world-wide flora check (FLORA-FAUNA-COVERAGE-62): every organic container record of the masters is known, and
every placement of a harvest kind is placed by the harvest source or listed with its reason. Synthetic records only."""
import copy
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import harvest_flora_census as C
from test_prepare_harvest import source
from test_tree_fungus_harvest import fungus
from test_world_flora_integration import record, sub


def organic(name, model, number, cell=(1, 1), flags=11, fnam=b'Thing'):
    raw = record('CONT', sub('NAME', name + b'\0') + sub('FNAM', fnam + b'\0') + sub('MODL', model + b'\0') +
                 sub('FLAG', struct.pack('<I', flags)))
    raw += record('CELL', sub('DATA', struct.pack('<Iii', 0, *cell)) + sub('FRMR', struct.pack('<I', number)) +
                  sub('NAME', name + b'\0') + sub('DATA', struct.pack('<6f', 1, 2, 3, 0, 0, 0)))
    return raw


def master(extra=b''):
    return source(extra=fungus() + organic(b'flora_heather_01', b'o/flora_heather_01.nif', 90) +
                  organic(b'egg_kwama00', b'o/contain_kwama_egg.nif', 91) +
                  organic(b'not_organic_box', b'o/box.nif', 92, flags=8) + extra)


class FloraCensusTests(unittest.TestCase):
    def group(self, report, name):
        return next(g for g in report['groups'] if g['name'] == name)

    def test_the_shipped_config_names_every_harvest_kind_and_the_masters(self):
        config = C.load_config()
        self.assertEqual([m['name'] for m in config['masters']], ['Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm'])
        self.assertEqual({g['kind'] for g in config['groups'] if g['status'] == 'harvestable'},
                         {'small_mushroom', 'tree_fungus'})

    def test_every_record_is_classified_and_counted(self):
        report = C.census([('Morrowind.esm', master())],
                          harvest=dict(numbers={42, 77}, refused={}))
        self.assertEqual(C.check(report), [])
        self.assertEqual(self.group(report, 'Small mushrooms')['placements'], 1)
        fungi = self.group(report, 'Bracket fungi on the tree trunks')
        self.assertEqual((fungi['placements'], fungi['harvestable_placements']), (1, 1))
        self.assertEqual(fungi['records'][0]['name'], "Bungler's Bane")
        self.assertEqual(self.group(report, 'Other plants')['register'], 'HARVEST-ORGANIC-PLANTS-47')
        self.assertEqual(self.group(report, 'Kwama egg sacks, kollops and spore pods')['placements'], 1)
        self.assertEqual(report['totals'], dict(records=4, placements=4, harvestable=2, pending=2, not_flora=0,
                                                expansion_harvest_kind=0))

    def test_an_unknown_organic_record_stops_the_build(self):
        report = C.census([('Morrowind.esm', master(organic(b'mystery_pod', b'o/pod.nif', 93)))],
                          harvest=dict(numbers={42, 77}, refused={}))
        problems = C.check(report)
        self.assertEqual(len(problems), 1)
        self.assertIn('mystery_pod', problems[0])
        self.assertIn('register it', problems[0])

    def test_a_harvestable_placement_neither_placed_nor_listed_stops_the_build(self):
        report = C.census([('Morrowind.esm', master())], harvest=dict(numbers={42}, refused={}))
        self.assertEqual([p['number'] for p in report['not_placed']], [77])
        self.assertIn('neither placed', C.check(report)[0])
        listed = C.census([('Morrowind.esm', master())], harvest=dict(numbers={42}, refused={77: 'owned'}))
        self.assertEqual(C.check(listed), [])

    def test_expansion_placements_count_apart_and_an_unnamed_master_is_named(self):
        expansion = organic(b'flora_bc_mushroom_01', b'f/flora_bc_mushroom_01.nif', 5, fnam=b'Luminous Russula')
        report = C.census([('Morrowind.esm', master()), ('Tribunal.esm', expansion)],
                          harvest=dict(numbers={42, 77}, refused={}))
        self.assertEqual(C.check(report), [])
        self.assertEqual(report['totals']['expansion_harvest_kind'], 1)
        self.assertEqual(report['masters'][1]['register'], 'HARVEST-EXPANSION-FLORA-62')
        odd = C.census([('Morrowind.esm', master()), ('Other.esm', expansion)], harvest=None)
        self.assertEqual(odd['masters_not_in_config'], ['Other.esm'])
        self.assertTrue(any('Other.esm' in p for p in C.check(odd)))

    def test_config_rules(self):
        config = json.loads(C.CONFIG.read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'c.json'
            for change in (lambda c: c['groups'].pop(1),                                   # a harvest kind without group
                           lambda c: c['groups'][2].pop('register'),                       # pending without register
                           lambda c: c['groups'].append(copy.deepcopy(c['groups'][2])),   # duplicate group
                           lambda c: c['masters'].reverse()):                              # base master not first
                bad = copy.deepcopy(config); change(bad)
                path.write_text(json.dumps(bad))
                with self.assertRaises(ValueError):
                    C.load_config(path)


if __name__ == '__main__':
    unittest.main()
