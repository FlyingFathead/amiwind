# SPDX-License-Identifier: GPL-3.0-only
"""The index of every hand-holdable item (DBG-CYCLEITEMS-67, tools/holdable_items.py): made from the game's records by
the original's rules, read back as written, and written by the image step beside the item catalogue."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))


def item(kind, subtype=-1, name='x', light=None):
    return {'kind': kind, 'subtype': subtype, 'name': name, 'light': light}


ITEMS = {
    'iron dagger': item('WEAP', 0, 'Iron Dagger'),
    'daedric claymore': item('WEAP', 2, 'Daedric Claymore'),
    'steel spear': item('WEAP', 6, 'Steel Spear'),
    'long bow': item('WEAP', 9, 'Long Bow'),
    'iron dart': item('WEAP', 11, 'Iron Dart'),
    'iron arrow': item('WEAP', 12, 'Iron Arrow'),           # ammunition: not held
    'steel_shield': item('ARMO', 8, 'Steel Shield'),
    'iron_helm': item('ARMO', 0, 'Iron Helm'),               # worn, not held
    'light_com_candle_01_64': item('LIGH', 64, 'Candle', light={'radius': 64}),
    'pick_apprentice_01': item('LOCK', -1, "Apprentice's Lockpick"),
    'probe_apprentice_01': item('PROB', -1, "Apprentice's Probe"),
    'hammer_repair': item('REPA', -1, "Apprentice's Armorer's Hammer"),   # used from the inventory
    'common_shirt_01': item('CLOT', 8, 'Common Shirt'),
}
FLAGS = {i: 1 | 4 for i in ITEMS}
FLAGS.update({'pick_apprentice_01': 0, 'probe_apprentice_01': 0, 'daedric claymore': 1})


class HoldableIndex(unittest.TestCase):
    def test_the_original_rules(self):
        import holdable_items as H
        got = {r[1]: r[2:] for r in H.rows(ITEMS, FLAGS)}
        self.assertEqual(got['iron dagger'], ('short blade', 'right', 'shortbladeonehand', 1))
        self.assertEqual(got['daedric claymore'], ('long blade two-handed', 'both', 'weapontwohand', 0))
        self.assertEqual(got['steel spear'], ('spear', 'both', 'weapontwowide', 1))
        self.assertEqual(got['long bow'], ('bow', 'both', 'bowandarrow', 1))
        self.assertEqual(got['iron dart'], ('thrown', 'right', 'throwweapon', 1))
        self.assertEqual(got['steel_shield'], ('shield', 'left', 'block', 1))
        self.assertEqual(got['light_com_candle_01_64'], ('light', 'left', 'none', 1))
        self.assertEqual(got['pick_apprentice_01'], ('lockpick', 'right', 'pickprobe', 0))
        self.assertEqual(got['probe_apprentice_01'], ('probe', 'right', 'pickprobe', 0))
        for not_held in ('iron arrow', 'iron_helm', 'hammer_repair', 'common_shirt_01'):
            self.assertNotIn(not_held, got)
        order = [r[2] for r in H.rows(ITEMS, FLAGS)]
        self.assertEqual(order, sorted(order, key=H.KIND_ORDER.index))       # kind order, then id

    def test_written_and_read_back(self):
        import holdable_items as H
        with tempfile.TemporaryDirectory() as temp:
            report = H.write_index(temp, ITEMS, FLAGS)
            raw = (Path(temp) / H.PATH).read_bytes()
        self.assertTrue(raw.startswith(b'AWHI1\n'))
        back = H.read(raw)
        self.assertEqual(back, H.rows(ITEMS, FLAGS))
        self.assertEqual(report['items'], 9)
        self.assertEqual(report['equip'], 6)
        self.assertEqual(report['kinds']['lockpick'], {'items': 1, 'equip': 0})
        with self.assertRaises(ValueError):
            H.read(b'AWHI2\n')
        with self.assertRaises(ValueError):
            H.text([('a\tb', 'id', 'light', 'left', 'none', 1)])

    def test_the_image_step_writes_it_beside_the_catalogue(self):
        source = (ROOT / 'tools/prepare_inventory.py').read_text(encoding='utf-8')
        self.assertIn("report['holdable']=write_index(id1,items,row_flags)", source)


if __name__ == '__main__':
    unittest.main()
