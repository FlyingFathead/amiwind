# SPDX-License-Identifier: GPL-3.0-only
"""Interior cells that behave like an exterior, presented as exterior cell blocks (tools/presented_exterior.py).
Small synthetic masters: no game data."""
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import presented_exterior as pe  # noqa: E402
from mwad.esm import records, subrecords  # noqa: E402

CONFIG = {'first_block': [-12, -30], 'spacing': 4, 'max_block': 2}


def sub(tag, data):
    if isinstance(data, str):
        data = data.encode('cp1252') + b'\0'
    return struct.pack('<4sI', tag.encode(), len(data)) + data


def rec(tag, *subs, unused=0, flags=0):
    payload = b''.join(subs)
    return struct.pack('<4sIII', tag.encode(), len(payload), unused, flags) + payload


def header(count):
    return rec('TES3', sub('HEDR', struct.pack('<fI32s256sI', 1.3, 1, b'', b'', count)))


def ref(number, ident, pos, door=None):
    out = sub('FRMR', struct.pack('<I', number)) + sub('NAME', ident)
    if door is not None:
        cell, spot = door
        out += sub('DODT', struct.pack('<6f', *spot, 0, 0, 0))
        if cell:
            out += sub('DNAM', cell)
    return out + sub('DATA', struct.pack('<6f', *pos, 0, 0, 0))


def interior(name, flags, *refs, extra=b''):
    return rec('CELL', sub('NAME', name), sub('DATA', struct.pack('<Iff', flags, 0.0, 0.0)), extra, *refs)


def exterior(x, y, *refs):
    return rec('CELL', sub('NAME', ''), sub('DATA', struct.pack('<Iii', 0, x, y)), *refs)


def master():
    """A base cell, a room with a door into the plaza, a plaza (flag 0x87) spanning two cells along x with a door back
    into the room and a door to the yard, and a small yard (flag 0x87)."""
    parts = [
        rec('STAT', sub('NAME', 'wall'), sub('MODL', 'x\\wall.nif'), unused=7),
        exterior(0, 0, ref(1, 'wall', (100, 100, 0))),
        interior('Town, Room', 0x01, ref(2, 'door_a', (10, 20, 30), door=('Town, Plaza', (-5000, 100, 8))),
                 ref(3, 'wall', (0, 0, 0))),
        interior('Town, Plaza', 0x87, sub('RGNN', 'Town Region'), sub('AMBI', b'\0' * 16),
                 ref(4, 'wall', (-5000, -1000, 0)), ref(5, 'wall', (5000, 1000, 64)),
                 ref(6, 'door_b', (-5000, 0, 8), door=('Town, Room', (10, 30, 30))),
                 ref(7, 'door_c', (4000, 0, 8), door=('Town, Yard', (100, 100, 3000)))),
        interior('Town, Yard', 0x87, sub('RGNN', 'Town Region'), ref(8, 'wall', (0, 0, 3000)),
                 ref(9, 'wall', (200, 200, 3100))),
    ]
    return header(len(parts)) + b''.join(parts)


def cells(raw):
    out = {}
    for tag, flags, payload in records(raw):
        if tag != 'CELL':
            continue
        head, groups = pe._split(payload)
        data = pe._field(head, 'DATA')
        bits, x, y = struct.unpack('<Iii', data)
        key = pe._text(pe._field(head, 'NAME')) if bits & 1 else (x, y)
        out.setdefault(key, []).append((bits, head, groups))
    return out


def spot(group, tag='DATA'):
    return struct.unpack('<6f', pe._field(group, tag))[:3]


class Presented(unittest.TestCase):
    def setUp(self):
        self.raw = master()
        self.out, self.receipt = pe.present(self.raw, CONFIG)
        self.cells = cells(self.out)
        self.rows = {r['cell']: r for r in self.receipt['cells']}

    def test_no_flagged_cell_is_the_same_bytes(self):
        raw = header(1) + exterior(0, 0, ref(1, 'wall', (1, 2, 3)))
        out, receipt = pe.present(raw, CONFIG)
        self.assertIs(out, raw)
        self.assertEqual(receipt['cells'], [])
        self.assertEqual(receipt['presented_sha256'], receipt['source_sha256'])

    def test_blocks_by_sorted_name_and_centred(self):
        plaza, yard = self.rows['Town, Plaza'], self.rows['Town, Yard']
        self.assertEqual((plaza['block'], plaza['size']), ([-12, -30], [2, 1]))
        self.assertEqual((yard['block'], yard['size']), ([-8, -30], [1, 1]))
        # the plaza's box centre (0, 0) lands on its block's centre
        self.assertEqual(plaza['offset'], [(-12 + 1) * 8192.0, (-30 + .5) * 8192.0])

    def test_interior_records_gone_and_exterior_cells_written(self):
        self.assertNotIn('Town, Plaza', self.cells)
        self.assertNotIn('Town, Yard', self.cells)
        for key in ((-12, -30), (-11, -30), (-8, -30)):
            self.assertIn(key, self.cells)
            bits, head, _ = self.cells[key][0]
            self.assertEqual(bits & 0x81, 0)                       # exterior, no longer flagged
            self.assertEqual(pe._text(pe._field(head, 'RGNN')), 'Town Region')
            self.assertIsNone(pe._field(head, 'AMBI'))
        self.assertEqual(self.receipt['exterior_cells_written'], 3)

    def test_placements_moved_split_by_grid_cell_and_heights_kept(self):
        ox, oy = self.rows['Town, Plaza']['offset']
        west = {struct.unpack('<I', pe._field(g, 'FRMR'))[0]: g for g in self.cells[(-12, -30)][0][2]}
        east = {struct.unpack('<I', pe._field(g, 'FRMR'))[0]: g for g in self.cells[(-11, -30)][0][2]}
        self.assertEqual(sorted(west), [4, 6])
        self.assertEqual(sorted(east), [5, 7])
        self.assertEqual(spot(west[4]), (-5000 + ox, -1000 + oy, 0))
        self.assertEqual(spot(east[5]), (5000 + ox, 1000 + oy, 64))
        yard = self.cells[(-8, -30)][0][2]
        self.assertEqual(sorted(spot(g)[2] for g in yard), [3000, 3100])

    def test_door_into_a_presented_cell_becomes_an_exterior_destination(self):
        ox, oy = self.rows['Town, Plaza']['offset']
        room = {struct.unpack('<I', pe._field(g, 'FRMR'))[0]: g for g in self.cells['Town, Room'][0][2]}
        self.assertIsNone(pe._field(room[2], 'DNAM'))
        self.assertEqual(spot(room[2], 'DODT'), (-5000 + ox, 100 + oy, 8))
        self.assertEqual(spot(room[2]), (10, 20, 30))                # the door itself stays in its room

    def test_doors_inside_a_presented_cell(self):
        yx, yy = self.rows['Town, Yard']['offset']
        west = {struct.unpack('<I', pe._field(g, 'FRMR'))[0]: g for g in self.cells[(-12, -30)][0][2]}
        east = {struct.unpack('<I', pe._field(g, 'FRMR'))[0]: g for g in self.cells[(-11, -30)][0][2]}
        self.assertEqual(pe._text(pe._field(west[6], 'DNAM')), 'Town, Room')     # into a room: unchanged
        self.assertEqual(spot(west[6], 'DODT'), (10, 30, 30))
        self.assertIsNone(pe._field(east[7], 'DNAM'))                            # to the other presented cell
        self.assertEqual(spot(east[7], 'DODT'), (100 + yx, 100 + yy, 3000))
        self.assertEqual(self.receipt['destinations_rewritten'], 2)

    def test_untouched_records_keep_their_bytes_and_the_count_is_right(self):
        stat = rec('STAT', sub('NAME', 'wall'), sub('MODL', 'x\\wall.nif'), unused=7)
        self.assertIn(stat, self.out)
        self.assertIn(exterior(0, 0, ref(1, 'wall', (100, 100, 0))), self.out)
        count = sum(1 for _ in records(self.out)) - 1
        hedr = next(d for t, f, p in records(self.out) if t == 'TES3' for k, d in subrecords(p) if k == 'HEDR')
        self.assertEqual(struct.unpack_from('<I', hedr, 296)[0], count)

    def test_same_input_same_output(self):
        again, receipt = pe.present(master(), CONFIG)
        self.assertEqual(again, self.out)
        self.assertEqual(receipt, self.receipt)

    def test_block_on_a_game_cell_is_refused(self):
        raw = self.raw + exterior(-12, -31)
        with self.assertRaisesRegex(ValueError, 'touches the game'):
            pe.present(raw, CONFIG)

    def test_cell_larger_than_the_largest_block_is_refused(self):
        raw = header(1) + interior('Big', 0x81, ref(1, 'wall', (0, 0, 0)), ref(2, 'wall', (30000, 0, 0)))
        with self.assertRaisesRegex(ValueError, 'largest block'):
            pe.present(raw, CONFIG)

    def test_shipped_config_loads_and_keeps_blocks_apart(self):
        config = pe.load_config()
        self.assertGreater(config['spacing'], config['max_block'])

    def test_the_districts_recipe_names_only_cells_of_the_presented_row(self):
        """config/visual-recipes.json gives the presented districts' cells the recipe mournhold-v1 (rows of measured
        tables that apply there only): each such cell lies in the row config/presented-exteriors.json lays out, in
        one of its five blocks, and the collision surface table lists that recipe under the Tribunal layer."""
        import json
        config = pe.load_config()
        recipes = json.loads((ROOT / 'config' / 'visual-recipes.json').read_text(encoding='utf-8'))
        cells = [tuple(int(v) for v in key.split(',')) for key, row in recipes['cell_settings'].items()
                 if row.get('visual_recipe') == 'mournhold-v1']
        self.assertTrue(cells)
        self.assertEqual(recipes['recipes']['mournhold-v1']['models'], {})
        x0, y0 = config['first_block']
        for x, y in cells:
            self.assertTrue(y0 <= y < y0 + config['max_block'], (x, y))
            self.assertTrue(0 <= x - x0 < 5 * config['spacing'], (x, y))
            self.assertLess((x - x0) % config['spacing'], config['max_block'], (x, y))
        table = json.loads((ROOT / 'config' / 'collision-hull-surface.json').read_text(encoding='utf-8'))
        self.assertIn('mournhold-v1', table['layer_recipes']['tribunal'])
        self.assertIn('mournhold-v1', table['recipe_meshes'])


if __name__ == '__main__':
    unittest.main()
