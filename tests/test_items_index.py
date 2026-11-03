"""The items index (tools/items_index.py, ITEMS-INDEX-57) on a small hand-made master: placed items by kind, cell
and owner, the summary and the public page, the content key."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import items_index as ii  # noqa: E402


def sub(tag, data):
    if isinstance(data, str):
        data = data.encode('ascii') + b'\0'
    return tag.encode('ascii') + struct.pack('<I', len(data)) + data


def rec(tag, *subs, flags=0):
    body = b''.join(subs)
    return tag.encode('ascii') + struct.pack('<III', len(body), 0, flags) + body


def item(tag, ident, name, data):
    return rec(tag, sub('NAME', ident), sub('FNAM', name), sub(data[0], data[1]))


def ref(number, ident, x, y, z=0.0, owner=None, faction=None):
    out = sub('FRMR', struct.pack('<I', number)) + sub('NAME', ident)
    if owner:
        out += sub('ANAM', owner)
    if faction:
        out += sub('CNAM', faction)
    return out + sub('DATA', struct.pack('<6f', x, y, z, 0, 0, 0))


def cell(name, interior, grid, region, *refs):
    data = struct.pack('<Iii', 1 if interior else 0, *grid)
    return rec('CELL', sub('NAME', name), sub('DATA', data), *((sub('RGNN', region),) if region else ()), *refs)


def master():
    return b''.join((
        rec('TES3', sub('HEDR', bytes(300))),
        rec('REGN', sub('NAME', 'bitter coast region'), sub('FNAM', 'Bitter Coast Region')),
        item('WEAP', 'iron shardaxe', 'Iron Shardaxe', ('WPDT', struct.pack('<fi', 20.0, 25) + bytes(24))),
        item('WEAP', 'keening', 'Keening', ('WPDT', struct.pack('<fi', 5.0, 400000) + bytes(24))),
        item('MISC', 'misc_plate', 'Plate', ('MCDT', struct.pack('<fii', 3.0, 17, 0))),
        item('MISC', 'key_door', 'Door Key', ('MCDT', struct.pack('<fii', 0.1, 0, 1))),
        item('MISC', 'gold_001', 'Gold', ('MCDT', struct.pack('<fii', 0.0, 1, 0))),
        # a light that cannot be carried is scenery, not an item
        item('LIGH', 'fixed_lamp', 'Lamp', ('LHDT', struct.pack('<fiiiI', 1.0, 5, 0, 0, 0) + bytes(4))),
        rec('ACTI', sub('NAME', 'sign'), sub('FNAM', 'Sign')),
        cell('Seyda Neen', False, (-2, -10), 'bitter coast region',
             ref(1, 'iron shardaxe', -13088, -74893), ref(2, 'gold_001', -13000, -74800),
             ref(3, 'fixed_lamp', -13010, -74810), ref(4, 'sign', 0, 0)),
        cell('', False, (-8, 2), 'bitter coast region', ref(5, 'misc_plate', -63400, 24352, owner='fargoth')),
        cell('Odrosal, Tower', True, (0, 0), None, ref(6, 'keening', 1, 2, 3), ref(7, 'key_door', 4, 5, 6),
             ref(8, 'misc_plate', 1, 1, faction='temple')),
        # developer cells: one named as a test, one no door leads to; both left out
        cell('ToddTest', True, (0, 0), None, ref(10, 'keening', 0, 0), ref(11, 'misc_plate', 0, 0)),
        cell('Hidden Vault', True, (0, 0), None, ref(12, 'iron shardaxe', 0, 0)),
        # the doors into the tower and into the test cell (a door does not make a 'test' cell reachable)
        cell('Odai Plateau', False, (-5, -5), None, ref(20, 'door_a', 0, 0) + sub('DNAM', 'Odrosal, Tower'),
             ref(21, 'door_b', 0, 0) + sub('DNAM', 'ToddTest')),
    ))


class ItemsIndexTests(unittest.TestCase):
    def setUp(self):
        self.idx = ii.index(master())
        self.idx['summary'] = self.summary = ii.summary(self.idx)

    def test_only_pickable_items_with_kind_cell_and_owner(self):
        rows = {e[5]: e for e in self.idx['items']}
        self.assertEqual(len(self.idx['items']), 6)          # not the fixed lamp, not the sign
        self.assertNotIn('fixed_lamp', rows)
        kinds = {e[5]: self.idx['kinds'][e[6]] for e in self.idx['items']}
        self.assertEqual((kinds['key_door'], kinds['gold_001'], kinds['iron shardaxe']), ('key', 'gold', 'weapon'))
        axe = rows['iron shardaxe']
        self.assertEqual(self.idx['cells'][axe[1]], ['Seyda Neen (-2, -10)', 'Bitter Coast Region', 0])
        self.assertEqual(axe[2:5], [-13088, -74893, 0])
        owners = sorted((e[7], e[8]) for e in self.idx['items'] if e[7])
        self.assertEqual(owners, [('fargoth', 0), ('temple', 1)])
        self.assertIn('Bitter Coast Region (-8, 2)', [c[0] for c in self.idx['cells']])

    def test_test_cells_and_cells_without_a_door_are_left_out_and_counted(self):
        self.assertEqual(self.idx['dropped'], {'Hidden Vault': 1, 'ToddTest': 2})
        self.assertNotIn('ToddTest', [c[0] for c in self.idx['cells']])
        self.assertEqual((self.summary['dropped_cells'], self.summary['dropped_items']), (2, 3))

    def test_page_dates_come_from_the_index_not_the_clock(self):
        page = ii.render(self.summary, '0.0.0-test', '2026-11-03')
        self.assertIn('_Last updated with AmiWind v0.0.0-test (3 November 2026)._', page.splitlines()[2])
        self.assertEqual(page, ii.render(self.summary, '0.0.0-test', '2026-11-03'))
        self.assertIn('1 weapons lie outdoors with no owner, free to take; the 1 most valuable:', page)

    def test_summary_totals_and_notables(self):
        s = self.summary
        self.assertEqual((s['placed'], s['owned'], s['distinct_items']), (6, 2, 5))
        self.assertEqual(s['by_kind']['misc'], [2, 2])
        self.assertEqual(s['by_region'], {'Bitter Coast Region': [3, 1], 'Interiors': [3, 1]})
        self.assertEqual([r['id'] for r in s['notable_singles']], ['keening', 'iron shardaxe'])
        self.assertEqual([r['id'] for r in s['notable_lone_weapons']], ['iron shardaxe'])

    def test_page_is_small_and_has_no_entry_dump(self):
        page = ii.render(self.summary, '0.0.0-test', '2026-11-03')
        self.assertIn('| weapon | 2 | 0 | 0 % |', page)
        self.assertIn('Iron Shardaxe (`iron shardaxe`)', page)
        self.assertNotIn('-13088', page)                       # positions stay in the private index
        self.assertLess(len(page.encode('utf-8')), 16000)

    def test_content_key_follows_the_master(self):
        self.assertEqual(ii.content_key('a' * 64), ii.content_key('a' * 64))
        self.assertNotEqual(ii.content_key('a' * 64), ii.content_key('b' * 64))

    def test_build_reuses_an_index_of_the_same_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / 'Data Files'
            data.mkdir()
            (data / 'Morrowind.esm').write_bytes(master())
            (data / 'Morrowind.bsa').write_bytes(b'')          # the data folder check looks for the archive too
            out = Path(tmp) / 'out'
            first, reused = ii.build(data, out)
            self.assertFalse(reused)
            again, reused = ii.build(data, out)
            self.assertTrue(reused)
            self.assertEqual(again['key'], first['key'])


if __name__ == '__main__':
    unittest.main()
