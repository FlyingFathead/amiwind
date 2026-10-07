# SPDX-License-Identifier: GPL-3.0-only
"""POI checklist on a synthetic master (no game data)."""
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import poi_checklist  # noqa: E402


def sub(tag, data):
    return struct.pack('<4sI', tag.encode(), len(data)) + data


def record(tag, *subs):
    body = b''.join(subs)
    return struct.pack('<4sIII', tag.encode(), len(body), 0, 0) + body


def z(text):
    return text.encode('cp1252') + b'\0'


def ref(number, ident, position=(0, 0, 0), target=None):
    out = sub('FRMR', struct.pack('<I', number)) + sub('NAME', z(ident))
    out += sub('DATA', struct.pack('<6f', *position, 0, 0, 0))
    if target:
        out += sub('DODT', struct.pack('<6f', 0, 0, 0, 0, 0, 0)) + sub('DNAM', z(target))
    return out


def cell(name, interior, x=0, y=0, region='', refs=b''):
    subs = [sub('NAME', z(name)), sub('DATA', struct.pack('<Iii', 1 if interior else 0, x, y))]
    if region:
        subs.append(sub('RGNN', z(region)))
    return record('CELL', *subs, refs)


MASTER = b''.join([
    record('STAT', sub('NAME', z('in_dwrv_hall00'))),
    record('DOOR', sub('NAME', z('door_a'))),
    cell('Testville', False, 3, 4, 'Test Region', ref(1, 'door_a', (10, 20, 30), 'Testville, Old House')),
    cell('Testville', False, 3, 5, 'Test Region'),
    cell('Testville, Old House', True, refs=ref(2, 'door_a', target='Testville, Old House, Cellar')),
    cell('Testville, Old House, Cellar', True),
    cell('Nchardahrk', True, refs=ref(3, 'in_dwrv_hall00') + ref(4, 'in_dwrv_hall00')),
])


class PoiChecklistTests(unittest.TestCase):
    def setUp(self):
        self.places = {p['name']: p for p in poi_checklist.build(MASTER, {'testville, old house'})}

    def test_exterior_place_groups_its_cells(self):
        place = self.places['Testville']
        self.assertEqual(place['kind'], 'exterior place')
        self.assertEqual(place['grids'], [[3, 4], [3, 5]])
        self.assertEqual(place['region'], 'Test Region')

    def test_interior_entrance_and_conversion_status(self):
        house = self.places['Testville, Old House']
        self.assertEqual(house['kind'], 'house')
        self.assertTrue(house['converted'])
        self.assertEqual(house['entrances'][0]['grid'], [3, 4])
        self.assertEqual(house['settlement'], 'Testville')

    def test_nested_interior_inherits_parent(self):
        cellar = self.places['Testville, Old House, Cellar']
        self.assertEqual(cellar['reached_through'], 'Testville, Old House')
        self.assertEqual(cellar['region'], 'Test Region')
        self.assertFalse(cellar['unreachable'])

    def test_kit_type_and_unreachable(self):
        ruin = self.places['Nchardahrk']
        self.assertEqual(ruin['kind'], 'Dwemer ruin')
        self.assertTrue(ruin['unreachable'])

    def test_markdown_has_checkboxes(self):
        text = poi_checklist.markdown(list(self.places.values()))
        self.assertIn('## Test Region', text)
        self.assertIn('- [x] converted  [ ] auto-checked  [ ] inspected - Testville, Old House (house)', text)


if __name__ == '__main__':
    unittest.main()
