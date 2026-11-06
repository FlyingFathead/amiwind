"""The two-handed weapons section of docs/COMBAT.md (tools/two_handed_weapons.py): the types the original makes
two-handed, the body group each plays, the rows from synthetic records, and the page's generated section."""
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import two_handed_weapons as thw  # noqa: E402


def weapon(name, subtype, chop, slash, thrust):
    raw = struct.pack('<fih', 1.0, 10, subtype) + b'\0' * 12 + bytes(chop + slash + thrust) + b'\0' * 4
    return {'kind': 'WEAP', 'subtype': subtype, 'name': name, 'raw': raw}


class TwoHandedWeapons(unittest.TestCase):
    def test_types_follow_the_original(self):
        # weapontype.cpp: TwoHanded = long blade 2H, blunt 2 close, blunt 2 wide, spear, axe 2H, bow, crossbow
        self.assertEqual(thw.TWO_HANDED, (2, 4, 5, 6, 8, 9, 10))
        groups = {t: g for t, _, g in thw.TYPES}
        self.assertEqual(groups[5], 'weapontwowide')
        self.assertEqual(groups[6], 'weapontwowide')
        self.assertEqual(groups[8], 'weapontwohand')
        engine = (ROOT / 'engine/aga/src/aw_inventory.h').read_text(encoding='utf-8')
        # the engine's rule (weapon = 1 + type) takes the shield off for the same types
        self.assertIn('#define AW_INV_TWO_HANDED(weapon) ((weapon)==3 || (weapon)==5 || (weapon)==6 || (weapon)==7 || '
                      '(weapon)==9 || \\\n                                   (weapon)==10 || (weapon)==11)', engine)

    def test_rows_and_render(self):
        items = {'a': weapon('Steel Claymore', 2, (1, 30), (1, 25), (1, 6)),
                 'b': weapon('Iron Claymore', 2, (1, 20), (1, 18), (1, 5)),
                 'c': weapon('Iron Dagger', 0, (3, 6), (3, 6), (4, 7)),
                 'd': weapon('Steel Crossbow', 10, (20, 20), (0, 0), (0, 0)),
                 'e': {'kind': 'ARMO', 'subtype': 8, 'name': 'Shield'}}
        rows = thw.rows_of(items)
        self.assertEqual([r[0] for r in rows[2]], ['Iron Claymore', 'Steel Claymore'])
        self.assertEqual(rows[0] if 0 in rows else [], [])
        text = thw.render(rows)
        self.assertIn('| Long blade, two-handed | `weapontwohand` | 2 | 1-30 | 1-25 | 1-6 |', text)
        self.assertIn('| Crossbow | `crossbow` | 1 | 20-20 | - | - |', text)
        self.assertIn('| Spear | `weapontwowide` | 0 | - | - | - |', text)
        self.assertIn('- **Long blade, two-handed** (2): Iron Claymore, Steel Claymore', text)
        self.assertTrue(text.startswith(thw.START) and text.endswith(thw.STOP))
        page = 'x\n' + thw.START + '\nold\n' + thw.STOP + '\ny\n'
        self.assertEqual(thw.replace(page, text), 'x\n' + text + '\ny\n')
        with self.assertRaises(ValueError):
            thw.replace('no markers', text)

    def test_the_page_carries_the_generated_section(self):
        page = (ROOT / 'docs/COMBAT.md').read_text(encoding='utf-8')
        self.assertIn(thw.START, page)
        self.assertIn(thw.STOP, page)
        self.assertIn('| Type | Body group | Weapons | Chop | Slash | Thrust |', page)


if __name__ == '__main__':
    unittest.main()
