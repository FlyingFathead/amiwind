# SPDX-License-Identifier: GPL-3.0-only
"""The expansions census (tools/expansions_census.py) on a synthetic Tribunal plugin generated at test time:
invented cells, objects and archive entries; no game data."""
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools'), str(ROOT / 'tests')]
import expansions_census as X  # noqa: E402
from test_world_estimate import bsa, box_nif, cell, land, record, ref, sub, synthetic_install, zstr  # noqa: E402


def tribunal(path, size):
    objects = [record('STAT', sub('NAME', zstr('fx_tri_hall')) + sub('MODL', zstr('x\\fx_tri.nif'))),
               record('STAT', sub('NAME', zstr('fx_tri_reuse')) + sub('MODL', zstr('x\\fx_box.nif'))),
               record('STAT', sub('NAME', zstr('fx_spruce')) + sub('MODL', zstr('f\\flora_tree_fx_spruce.nif'))),
               record('STAT', sub('NAME', zstr('fx_nowhere')) + sub('MODL', zstr('x\\fx_nowhere.nif')))]
    cells = [
        # a new interior that behaves like an exterior (flag 0x80), three new placements
        cell('Fixture Mournhold Square', 1 | 0x80, 0, 0, [ref(1, 'fx_tri_hall', (0, 0, 0)),
                                                         ref(2, 'fx_tri_reuse', (10, 0, 0)),
                                                         ref(3, 'fx_nowhere', (20, 0, 0))]),
        # a base interior: one edit of base reference 7 (master index 1) and one new placement
        cell('Fixture Room A', 1, 0, 0, [ref(0x01000007, 'fx_door', (600, 0, 0)), ref(4, 'fx_tri_hall', (5, 5, 5))]),
        # a base exterior cell: one new placement, one deleted placement, one moved reference
        record('CELL', sub('NAME', zstr('Fixtown')) + sub('DATA', struct.pack('<Iii', 0, 0, 0)) +
               sub('MVRF', struct.pack('<I', 5)) + sub('CNDT', struct.pack('<ii', 1, 0)) +
               ref(5, 'fx_tri_hall', (1, 1, 1)) + ref(6, 'fx_tri_hall', (2, 2, 2)) + sub('DELE', b'\0\0\0\0')),
        # new ground: a land cell with two trees and a sea cell with nothing
        cell('', 0, 5, 5, [ref(7, 'fx_spruce', (0, 0, 0)), ref(8, 'fx_spruce', (9, 9, 0))]),
        cell('', 0, 6, 5, []),
    ]
    body = objects + cells + [land(5, 5)]
    head = struct.pack('<fI32s256sI', 1.3, 1, b'Synthetic Tribunal', b'Census test', len(body))
    mast = sub('MAST', zstr('Morrowind.esm')) + sub('DATA', struct.pack('<Q', size))
    (path / 'Tribunal.esm').write_bytes(record('TES3', sub('HEDR', head) + mast) + b''.join(body))
    files = {'meshes\\x\\fx_tri.nif': box_nif(), 'meshes\\x\\fx_box.nif': box_nif(),
             'meshes\\f\\flora_tree_fx_spruce.nif': box_nif()}
    (path / 'Tribunal.bsa').write_bytes(bsa(files))


class ExpansionsCensusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data = synthetic_install(Path(cls.tmp.name) / 'Data Files')
        tribunal(cls.data, (cls.data / 'Morrowind.esm').stat().st_size)
        cls.result = X.census_expansions(cls.data)
        cls.t = cls.result['expansions']['tribunal']

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_only_present_expansions_are_counted(self):
        self.assertEqual(list(self.result['expansions']), ['tribunal'])
        self.assertEqual(self.t['master_list'], ['Morrowind.esm'])

    def test_cells_split_into_land_sea_and_interiors(self):
        t = self.t
        self.assertEqual(t['exterior_cells'], 3)
        self.assertEqual((t['exterior_new'], t['exterior_new_land'], t['exterior_new_sea']), (2, 1, 1))
        self.assertEqual(t['exterior_land'], 2)             # Fixtown has a base LAND record, the new cell its own
        self.assertEqual(t['exterior_sea'], 1)
        self.assertEqual(t['land_records_own'], 1)
        self.assertEqual(t['interior_cells'], 2)
        self.assertEqual(t['interiors_behaving_like_exterior'], 1)
        self.assertEqual(t['interiors_behaving_like_exterior_cells'],
                         [{'cell': 'Fixture Mournhold Square', 'placements': 3}])

    def test_placements_per_cell(self):
        self.assertEqual(self.t['placements_interior'], {'cells_with_placements': 2, 'max': 3, 'median': 2.5,
                                                         'total': 5})
        self.assertEqual(self.t['placements_exterior_new'], {'cells_with_placements': 1, 'max': 2, 'median': 2,
                                                             'total': 2})

    def test_base_cells_and_master_index(self):
        t = self.t
        self.assertEqual((t['exterior_in_base_game'], t['interior_in_base_game']), (1, 1))
        self.assertEqual(t['reference_master_index'], {'0': 7, '1': 1})
        self.assertEqual(t['moved_references_total'], 1)
        self.assertEqual(t['base_cells_edited'], 1)
        edited = t['base_cells_edited_top'][0]
        self.assertEqual((edited['cell'], edited['edited_placements'], edited['edits_of']),
                         ('Fixture Room A', 1, {'Morrowind.esm': 1}))
        rows = {r['cell']: r for r in t['base_cells_with_new_placements_top']}
        self.assertEqual(rows['Fixtown (0,0)']['new_placements'], 1)
        self.assertEqual(rows['Fixtown (0,0)']['deleted_references'], 1)    # the second placement carries a DELE
        self.assertEqual(rows['Fixtown (0,0)']['moved_references'], 1)

    def test_models_only_in_the_expansion_archive(self):
        t = self.t
        # fx_tri and the spruce are new; fx_box is in Morrowind.bsa; fx_nowhere is in no archive
        self.assertEqual(t['models_not_in_base_archive'], 2)
        self.assertEqual(t['models_only_in_own_archive'], 2)
        self.assertEqual(t['models_missing_everywhere'], 1)
        loose = self.data / 'Meshes' / 'x'
        loose.mkdir(parents=True)
        (loose / 'fx_tri.nif').write_bytes(b'x')
        again = X.census_expansions(self.data)['expansions']['tribunal']
        (loose / 'fx_tri.nif').unlink()
        self.assertEqual((again['models_not_in_base_archive'], again['models_only_in_own_archive']), (2, 1))

    def test_tree_references_by_model(self):
        self.assertEqual(len(self.t['tree_models']), 1)
        tree = self.t['tree_models'][0]
        self.assertEqual((tree['model'], tree['placements'], tree['cells'], tree['only_in_own_archive']),
                         ('meshes/f/flora_tree_fx_spruce.nif', 2, 1, True))
        self.assertEqual(self.t['tree_placements'], 2)
        self.assertEqual(self.t['tree_placements_per_cell'],
                         {'cells_with_placements': 1, 'max': 2, 'median': 2, 'total': 2})

    def test_output_files_and_markdown(self):
        with tempfile.TemporaryDirectory() as out:
            self.assertEqual(X.main(['--data-files', str(self.data), '--out', out]), 0)
            stored = json.loads((Path(out) / 'census.json').read_text())
            self.assertEqual(stored['expansions']['tribunal']['interior_cells'], 2)
            md = (Path(out) / 'census.md').read_text()
        self.assertIn('Mournhold (Tribunal.esm)', md)
        self.assertIn('meshes/f/flora_tree_fx_spruce.nif', md)


if __name__ == '__main__':
    unittest.main()
