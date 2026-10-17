"""The icon and HUD-art import (tools/prepare_icons.py) with synthetic pictures only.

No original game texture, icon or icon-derived picture is used or stored here:
every input is drawn by the test. HUD-STATS-29.
"""
import hashlib, io, json, struct, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))
import prepare_icons as icons
import prepare_inventory as inv


def png(size, colour):
    from PIL import Image
    out = io.BytesIO(); Image.new('RGBA', size, colour).save(out, 'PNG'); return out.getvalue()


class Assets:
    """Synthetic stand-in for the game data reader: plain coloured squares."""
    def __init__(self, missing=()):
        self.files = {}; self.reads = []
        for piece in ('top', 'bottom', 'left', 'right', 'top_left_corner', 'top_right_corner',
                      'bottom_left_corner', 'bottom_right_corner'):
            self.files[icons.THIN % piece] = png((2, 2) if 'corner' in piece else (64, 2) if piece in ('top', 'bottom') else (2, 64),
                                                 (200, 180, 120, 255))
        self.files[icons.BAR_TEXTURE] = png((16, 16), (255, 255, 255, 255))
        for piece, size in (('middle', (256, 16)), ('top', (256, 2)), ('bottom', (256, 2)), ('left', (2, 16)),
                            ('right', (2, 16)), ('top_left_corner', (2, 2)), ('top_right_corner', (2, 2)),
                            ('bottom_left_corner', (2, 2)), ('bottom_right_corner', (2, 2))):
            self.files[icons.HEAD % piece] = png(size, (150, 120, 60, 255) if piece == 'middle' else (220, 200, 140, 255))
        self.files[icons.MAGIC_BACKGROUND] = png((64, 64), (0, 0, 255, 255))
        self.files['icons/k/stealth_handtohand.dds'] = png((32, 32), (250, 200, 150, 255))
        self.files['icons/w/test_sword.dds'] = png((32, 32), (0, 255, 0, 255))
        self.files['icons/c/test_ring.dds'] = png((32, 32), (255, 0, 0, 0))   # fully transparent: backdrop shows
        for name in missing: self.files.pop(name, None)

    def read(self, name):
        self.reads.append(name)
        if name not in self.files: raise KeyError(name)
        return self.files[name]


PALETTE = bytes(v for i in range(256) for v in ((i * 37) % 256, (i * 91) % 256, (i * 151) % 256))
COLOURS = {'color_weapon_fill': [200, 60, 30], 'color_magic_fill': [200, 60, 30]}


PACKS = {}


def table(id1):
    raw = (Path(id1) / 'gfx/icons.awl').read_bytes()
    count = struct.unpack_from('<I', raw, 4)[0]
    assert raw[:4] == b'AWL2' and len(raw) == 8 + count * icons.ROW
    pack = (Path(id1) / 'gfx/icons.awp').read_bytes()
    assert pack[:4] == b'AWP1'
    rows = {}
    for i in range(count):
        row = raw[8 + i * icons.ROW:8 + (i + 1) * icons.ROW]
        offset, size = struct.unpack_from('<II', row, 120)
        digest = row[128:160].hex()
        assert hashlib.sha256(pack[offset:offset + size]).hexdigest() == digest   # the row names its picture
        PACKS[(str(id1), digest)] = pack[offset:offset + size]
        rows[row[:64].split(b'\0')[0].decode()] = (row[64:120].split(b'\0')[0].decode(), digest)
    return raw, rows


def picture(id1, digest):
    raw = PACKS[(str(id1), digest)]
    w, h = struct.unpack_from('<HH', raw, 4)
    return raw[:4], w, h, raw[8:]


class IconTableTests(unittest.TestCase):
    def build(self, items, assets=None):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        report = icons.prepare(assets or Assets(), tmp.name, items, PALETTE, COLOURS)
        return tmp.name, report

    def test_one_sorted_table_every_hud_key_and_sizes(self):
        id1, report = self.build({'test sword': {'source_icon': 'w\\test_sword.tga', 'enchanted': False},
                                  'Test_Ring': {'source_icon': 'c\\test_ring.tga', 'enchanted': True}})
        raw, rows = table(id1)
        keys = [raw[8 + i * icons.ROW:8 + i * icons.ROW + 64].split(b'\0')[0] for i in range(len(rows))]
        self.assertEqual(keys, sorted(keys))           # binary-searchable (aw_icons.c)
        self.assertEqual(set(rows), {'hud:box', 'hud:bar', 'hud:track:weapon', 'hud:track:magic', 'skill:26',
                                     'item:test sword', 'item:test_ring', 'ui:head:block', 'ui:head:left',
                                     'ui:head:right'})
        sizes = {key: picture(id1, digest)[1:3] for key, (_, digest) in rows.items()}
        self.assertEqual(sizes['hud:box'], (20, 20)); self.assertEqual(sizes['hud:bar'], (20, 4))
        self.assertEqual(sizes['hud:track:weapon'], (18, 2)); self.assertEqual(sizes['skill:26'], (18, 18))
        self.assertEqual(sizes['item:test sword'], (18, 18))
        # The title bar's head block at 12/20 of the original: the 256 x 16 middle tile -> 154 wide,
        # 1-pixel edges, 12 tall; edge columns 1 x 12 (UI-WINDOW-TITLE-BAR-42).
        self.assertEqual(sizes['ui:head:block'], (154, 12))
        self.assertEqual(sizes['ui:head:left'], (1, 12)); self.assertEqual(sizes['ui:head:right'], (1, 12))
        self.assertEqual(rows['item:test sword'][0], 'icons/w/test_sword.dds')   # the record's ITEX, .dds first
        self.assertEqual(report['held'], {})
        for key, (_, digest) in rows.items():
            self.assertEqual(picture(id1, digest)[0], b'AWI1')
            self.assertNotIn(255, picture(id1, digest)[3])                       # never the transparent index

    def test_pictures_stored_once_by_sha256(self):
        id1, report = self.build({'a': {'source_icon': 'w\\test_sword.tga'}, 'b': {'source_icon': 'w\\test_sword.tga'}})
        _, rows = table(id1)
        self.assertEqual(rows['item:a'][1], rows['item:b'][1])
        self.assertEqual(rows['hud:track:weapon'][1], rows['hud:track:magic'][1])   # same ini colour
        self.assertEqual(report['stored_pictures'], len(set(d for _, d in rows.values())))
        pack = Path(id1, 'gfx/icons.awp').read_bytes()
        self.assertEqual(struct.unpack_from('<I', pack, 4)[0], report['stored_pictures'])   # one file, each picture once
        self.assertFalse(Path(id1, 'gfx/icon').exists())

    def test_enchanted_item_sits_on_the_magic_backdrop(self):
        id1, _ = self.build({'plain': {'source_icon': 'c\\test_ring.tga', 'enchanted': False},
                             'magic': {'source_icon': 'c\\test_ring.tga', 'enchanted': True}})
        _, rows = table(id1)
        plain = picture(id1, rows['item:plain'][1])[3]; magic = picture(id1, rows['item:magic'][1])[3]
        black = min(range(255), key=lambda i: sum(PALETTE[i * 3 + c] ** 2 for c in range(3)))
        blue = min(range(255), key=lambda i: PALETTE[i * 3] ** 2 + PALETTE[i * 3 + 1] ** 2 + (PALETTE[i * 3 + 2] - 255) ** 2)
        self.assertEqual(set(plain), {black}); self.assertEqual(set(magic), {blue})

    def test_inventory_icons_for_every_owned_item_with_equipped_variant(self):
        assets = Assets()
        assets.files[icons.EQUIP_BACKGROUND] = png((64, 64), (0, 255, 0, 255))
        assets.files[icons.MAGIC_EQUIP_BACKGROUND] = png((64, 64), (255, 0, 255, 255))
        inventory = {'sword%02d' % i: {'source_icon': 'w\\test_sword.tga', 'enchanted': False, 'equippable': True}
                     for i in range(70)}
        inventory['ring'] = {'source_icon': 'c\\test_ring.tga', 'enchanted': True, 'equippable': True}
        inventory['glove'] = {'source_icon': 'c/test_ring.tga', 'enchanted': False, 'equippable': True}
        inventory['note'] = {'source_icon': 'c\\test_ring.tga', 'enchanted': False, 'equippable': False}
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        report = icons.prepare(assets, tmp.name, {}, PALETTE, COLOURS, inventory, jobs=2)   # the process pool path
        _, rows = table(tmp.name)
        self.assertEqual(picture(tmp.name, rows['inv:sword00'][1])[1:3], (16, 16))
        self.assertIn('inv:sword69:equip', rows); self.assertNotIn('inv:note:equip', rows)
        self.assertEqual(rows['inv:sword00'][1], rows['inv:sword69'][1])            # one picture for 70 rows
        # The original cell scaled to 16: the opaque 32 x 32 icon becomes 12 x 12 at 2,2 on black.
        cell = picture(tmp.name, rows['inv:sword00'][1])[3]
        black = min(range(255), key=lambda i: sum(PALETTE[i * 3 + c] ** 2 for c in range(3)))
        self.assertEqual({cell[y * 16 + x] for y in range(16) for x in range(16) if not (2 <= x < 14 and 2 <= y < 14)}, {black})
        self.assertNotIn(black, {cell[y * 16 + x] for y in range(3, 13) for x in range(3, 13)})
        plain = set(picture(tmp.name, rows['inv:note'][1])[3]); magic = set(picture(tmp.name, rows['inv:ring'][1])[3])
        equip = set(picture(tmp.name, rows['inv:sword00:equip'][1])[3]); magic_equip = set(picture(tmp.name, rows['inv:ring:equip'][1])[3])
        self.assertEqual(len({frozenset(plain), frozenset(magic), frozenset(magic_equip)}), 3)
        self.assertNotEqual(picture(tmp.name, rows['inv:glove'][1])[3], picture(tmp.name, rows['inv:glove:equip'][1])[3])
        self.assertEqual(report['held'], {})

    def test_track_is_the_grey_bar_tinted_by_the_ini_colour(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        colours = {'color_weapon_fill': [255, 0, 0], 'color_magic_fill': [0, 0, 255]}
        icons.prepare(Assets(), tmp.name, {}, PALETTE, colours)
        _, rows = table(tmp.name)
        red = picture(tmp.name, rows['hud:track:weapon'][1])[3]; blue = picture(tmp.name, rows['hud:track:magic'][1])[3]
        self.assertNotEqual(red, blue)
        r = red[0]; self.assertGreater(PALETTE[r * 3], PALETTE[r * 3 + 2])

    def test_missing_original_is_held_with_its_reason_not_replaced(self):
        id1, report = self.build({'gone': {'source_icon': 'w\\nothing.tga'}},
                                 Assets(missing=['icons/k/stealth_handtohand.dds']))
        _, rows = table(id1)
        self.assertNotIn('item:gone', rows); self.assertNotIn('skill:26', rows)
        self.assertIn('item:gone', report['held']); self.assertIn('skill:26', report['held'])

    def test_ini_colours_and_shipped_value_when_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / 'Data Files'; data.mkdir()
            (Path(tmp) / 'Morrowind.ini').write_bytes(b'[FontColor]\r\ncolor_weapon_fill=1,2,3\r\n')
            colours, info = icons.ini_colours(data)
            self.assertEqual(colours['color_weapon_fill'], [1, 2, 3])
            self.assertEqual(colours['color_magic_fill'], [200, 60, 30]); self.assertTrue(info['notes'])

    def test_recharge_setting_requires_the_gmst(self):
        text, info = icons.hud_settings({'fmagicitemrechargepersecond': .05})
        self.assertEqual(text, 'fMagicItemRechargePerSecond 0.05\n')
        with self.assertRaises(ValueError): icons.hud_settings({})
        text, info = icons.hud_settings({'fmagicitemrechargepersecond': .05, 'sskillhandtohand': 'Hand-to-hand'})
        self.assertEqual(text.splitlines()[1], 'sSkillHandtohand Hand-to-hand')   # the unarmed inventory title


class EnchantmentChargeTests(unittest.TestCase):
    SETTINGS = {'feffectcostmult': .5, 'imagicitemchargeonce': 1, 'imagicitemchargestrike': 10,
                'imagicitemchargeuse': 5, 'imagicitemchargeconst': 1}

    def test_authored_charge_is_kept(self):
        self.assertEqual(inv.max_charge((2, 5, 20, 0), [], {}, self.SETTINGS), 20.0)

    def test_autocalc_charge_follows_the_effect_cost_rule(self):
        # One effect, base cost 10, magnitude 1..5, duration 10, area 0, on self:
        # 0.5*(1+5) * 0.1*10 * 10 = 30, times fEffectCostMult 0.5 = 15; round(15) * iMagicItemChargeUse 5.
        effect = (75, 0, 0, 0, 0, 10, 1, 5)
        self.assertEqual(inv.max_charge((2, 0, 0, 1), [effect], {75: (10., 0)}, self.SETTINGS), 75.0)
        # On target: x1.5; cast-when-strikes multiplier 10.
        target = (75, 0, 0, 2, 0, 10, 1, 5)
        self.assertEqual(inv.max_charge((1, 0, 0, 1), [target], {75: (10., 0)}, self.SETTINGS), 230.0)
        # NoMagnitude (0x8) and NoDuration (0x4): both count as 1.
        self.assertEqual(inv.effect_cost((75, 0, 0, 0, 0, 10, 1, 5), {75: (10., 0xc)}, 1.), 1.0)
        with self.assertRaises(ValueError): inv.effect_cost(effect, {}, 1.)


class ReleaseFilesTests(unittest.TestCase):
    def test_no_icon_derived_or_original_art_file_is_released(self):
        listed = json.loads((ROOT / 'tools/release-files.json').read_text(encoding='utf-8'))
        bad = [p for p in listed if p.startswith(('gfx/', 'id1/', 'icons/', 'textures/')) or '/gfx/icon/' in p
               or p.endswith(('icons.awl', 'hud-settings.txt', '.dds', '.tga', '.awi'))]
        self.assertEqual(bad, [])


if __name__ == '__main__':
    unittest.main()
