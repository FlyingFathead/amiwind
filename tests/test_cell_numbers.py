# SPDX-License-Identifier: GPL-3.0-only
"""Interior cell numbers for the debug HUD: stable order, ESM scan, map stamping."""
import json
from pathlib import Path
import re
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import cell_numbers
from cell_numbers import cell_fields, exterior_cell, interior_cell_ids, number_cells, stamp_staged_cells
from player_hull import lumps, pack_lumps


def sub(tag, body):
    return tag + struct.pack('<I', len(body)) + body


def cell(name, interior=True, x=0, y=0, deleted=False, record_flags=0, refs=b''):
    body = sub(b'NAME', name.encode('cp1252') + b'\0') + sub(b'DATA', struct.pack('<Iii', 1 if interior else 0, x, y))
    if deleted:
        body += sub(b'DELE', b'\0\0\0\0')
    body += refs
    return b'CELL' + struct.pack('<III', len(body), 0, record_flags) + body


def other(tag=b'GLOB'):
    body = sub(b'NAME', b'x\0')
    return tag + struct.pack('<III', len(body), 0, 0) + body


class CellNumbers(unittest.TestCase):
    def test_master_scan_keeps_interiors_only(self):
        ref = sub(b'FRMR', struct.pack('<I', 1)) + sub(b'NAME', b'door\0') + \
            sub(b'DATA', struct.pack('<6f', 0, 0, 0, 0, 0, 0))
        raw = b''.join([other(b'TES3'), cell('Balmora, Guild', refs=ref), cell('Balmora', False, -3, -2),
                        cell('Gone', deleted=True), cell('Ignored', record_flags=0x20), other(),
                        cell('Abaelun Mine')])
        self.assertEqual(interior_cell_ids(raw), ['Balmora, Guild', 'Abaelun Mine'])
        with self.assertRaises(ValueError):
            interior_cell_ids(raw[:-3])

    def test_numbers_are_sorted_per_master_and_expansions_append(self):
        base = ['zeta', 'Alpha', 'beta']
        rows = number_cells([('Morrowind.esm', base), ('Tribunal.esm', ['BETA', 'Mournhold']),
                             ('Bloodmoon.esm', ['Aaa'])])
        self.assertEqual([(r['number'], r['cell'], r['master']) for r in rows],
                         [(1, 'Alpha', 'Morrowind.esm'), (2, 'beta', 'Morrowind.esm'), (3, 'zeta', 'Morrowind.esm'),
                          (4, 'Mournhold', 'Tribunal.esm'), (5, 'Aaa', 'Bloodmoon.esm')])
        # File order and a missing expansion never move the numbers before it.
        again = number_cells([('Morrowind.esm', list(reversed(base))), ('Bloodmoon.esm', ['Aaa'])])
        self.assertEqual([r['number'] for r in again[:3]], [1, 2, 3])
        with self.assertRaises(ValueError):
            number_cells([('Morrowind.esm', ['Same', 'same'])])

    def test_fields_and_rejections(self):
        self.assertEqual(cell_fields({'number': 187, 'cell': "Balmora, Caius Cosades' House"}),
                         {'_aw_cell_int': '187', '_aw_cell_id': "Balmora, Caius Cosades' House"})
        for bad in ('a"b', 'tab\there', 'x' * 64, 'café'):
            with self.assertRaises(ValueError):
                cell_fields({'number': 1, 'cell': bad})

    def test_exterior_grid_floor_on_both_sides_of_zero_and_edges(self):
        cases = {(0, 0): (0, 0), (8191.9, 8191.9): (0, 0), (8192, 8192): (1, 1), (-0.1, -1): (-1, -1),
                 (-8192, -8192): (-1, -1), (-8192.1, -8193): (-2, -2),
                 (-20480, -12288): (-3, -2),   # Balmora frame centre (config/balmora.json) = ESM cell -3,-2
                 (-11264, -71680): (-2, -9)}   # Seyda Neen frame centre (config/seyda_area.json) = ESM cell -2,-9
        for (x, y), want in cases.items():
            self.assertEqual(exterior_cell(x, y), want, (x, y))

    def test_town_centres_match_their_source_cells(self):
        balmora = json.loads((ROOT / 'config/balmora.json').read_text(encoding='utf-8'))
        self.assertEqual(list(exterior_cell(*balmora['centre'])), balmora['source_cell'])

    def test_builder_stamps_staged_interiors_and_writes_the_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            data = tmp / 'Data Files'; data.mkdir()
            (data / 'Morrowind.esm').write_bytes(b''.join([other(b'TES3'), cell('Seyda Neen, Census and Excise Office'),
                                                           cell('Imperial Prison Ship'), cell('Seyda Neen', False, -2, -9)]))
            maps = tmp / 'id1' / 'maps'; maps.mkdir(parents=True)
            raw = pack_lumps([b'{\n"classname" "worldspawn"\n"message" "Census"\n}\n\0'] + [bytes([n]) * n for n in range(1, 15)])
            (maps / 'census.bsp').write_bytes(raw)
            (maps / 'prison.bsp').write_bytes(raw)
            report = stamp_staged_cells(tmp / 'id1', data, {'census', 'prison'}, tmp / 'cell-numbers.json')
            census = bytes(lumps((maps / 'census.bsp').read_bytes())[0])
            self.assertIn(b'"_aw_cell_int" "2"', census)
            self.assertIn(b'"_aw_cell_id" "Seyda Neen, Census and Excise Office"', census)
            self.assertIn(b'"_aw_cell_int" "1"', bytes(lumps((maps / 'prison.bsp').read_bytes())[0]))
            self.assertEqual(lumps((maps / 'census.bsp').read_bytes())[1:], lumps(raw)[1:])
            table = json.loads((tmp / 'cell-numbers.json').read_text(encoding='utf-8'))
            self.assertEqual([(r['number'], r['cell']) for r in table['table']],
                             [(1, 'Imperial Prison Ship'), (2, 'Seyda Neen, Census and Excise Office')])
            self.assertEqual(report['maps'], [{'map': 'census', 'number': 2, 'cell': 'Seyda Neen, Census and Excise Office'},
                                              {'map': 'prison', 'number': 1, 'cell': 'Imperial Prison Ship'}])
            # Idempotent: a second pass changes nothing.
            again = stamp_staged_cells(tmp / 'id1', data, {'census', 'prison'}, tmp / 'cell-numbers.json')
            self.assertEqual(again['changed_maps'], [])
            # A map naming a cell the masters lack stops the build.
            (data / 'Morrowind.esm').write_bytes(b''.join([other(b'TES3'), cell('Imperial Prison Ship')]))
            with self.assertRaises(ValueError):
                stamp_staged_cells(tmp / 'id1', data, {'census'}, tmp / 'cell-numbers.json')

    def test_every_catalogued_interior_fits_a_worldspawn_key(self):
        cells = cell_numbers.interior_map_cells(
            [s['map'] for s in __import__('area_config').SCENES if s.get('interior')] +
            [r['map'] for r in __import__('town_config').town_interiors()])
        self.assertGreater(len(cells), 100)
        for name, cell_id in cells.items():
            cell_fields({'number': 1, 'cell': cell_id})

    def test_image_step_stamps_after_hand_metadata_and_records_the_table(self):
        text = (ROOT / 'tools/build_aga.py').read_text(encoding='utf-8')
        hands = text.index("'first-person hand metadata', jobs=jobs)")
        cells = text.index('stamp_staged_cells(boot/')
        self.assertLess(hands, cells)
        self.assertLess(cells, text.index('optimize_maps(boot/'))
        self.assertIn("'interior cell numbers', jobs=jobs)", text)
        self.assertTrue(re.search(r"'cell_numbers':\{'report':'cell-numbers.json'", text))

    def test_engine_reads_the_same_keys(self):
        hud = (ROOT / 'engine/aga/src/aw_hud.c').read_text(encoding='utf-8')
        for key in (cell_numbers.NUMBER_KEY, cell_numbers.ID_KEY):
            self.assertIn('"' + key + '"', hud)
        self.assertIn('static char cell_id[%d]' % (cell_numbers.ID_LIMIT + 1), hud)


if __name__ == '__main__':
    unittest.main()
