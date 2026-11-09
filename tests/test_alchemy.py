# SPDX-License-Identifier: GPL-3.0-only
"""Alchemy (ALCHEMY-61, docs/ALCHEMY.md): the rules in host C, the catalogue's alchemy block and alchemy/settings.txt
from a synthetic master, the engine's reading of the block, and the source contracts that wire the use, the window
and the made potion in."""
import os
import re
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_aga_native_source as native

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src'))


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


def record(kind, fields):
    data = b''.join(k.encode() + struct.pack('<I', len(v)) + v for k, v in fields)
    return kind.encode() + struct.pack('<III', len(data), 0, 0) + data


def text(value):
    return value.encode() + b'\0'


def gmst(name, value):
    if name[0] == 'f':
        return record('GMST', [('NAME', text(name)), ('FLTV', struct.pack('<f', value))])
    if name[0] == 'i':
        return record('GMST', [('NAME', text(name)), ('INTV', struct.pack('<i', value))])
    return record('GMST', [('NAME', text(name)), ('STRV', value.encode('cp1252'))])


def master():
    """Two ingredients, two potions (one in a standard bottle), a calcinator, a plain Misc item, the settings."""
    raw = b''
    irdt = struct.pack('<fi4i4i4i', .5, 3, 17, 77, -1, -1, 5, 4, 0, 0, 3, 1, 0, 0)
    raw += record('INGR', [('NAME', text('ingred_test_01')), ('FNAM', text('Test Root')), ('IRDT', irdt)])
    raw += record('INGR', [('NAME', text('ingred_test_02')), ('FNAM', text('Test Leaf')),
                           ('IRDT', struct.pack('<fi4i4i4i', 1., 2, 77, 1, -1, -1, 0, 0, 0, 0, 0, 0, 0, 0))])
    enam = struct.pack('<hbbiiiii', 75, -1, -1, 0, 0, 1, 10, 10) + b''
    raw += record('ALCH', [('NAME', text('p_test_b')), ('MODL', text('m\\Misc_Potion_Bargain_01.nif')),
                           ('FNAM', text('Bargain Test')), ('ALDT', struct.pack('<fii', .5, 5, 0)),
                           ('ENAM', enam), ('ENAM', struct.pack('<hbbiiiii', 83, 16, -1, 0, 0, 30, 5, 5))])
    raw += record('ALCH', [('NAME', text('p_test_s')), ('MODL', text('m\\misc_potion_standard_01.nif')),
                           ('FNAM', text('Standard Test')), ('ALDT', struct.pack('<fii', 1., 15, 0)),
                           ('ENAM', struct.pack('<hbbiiiii', 77, -1, -1, 0, 0, 10, 5, 5))])
    raw += record('APPA', [('NAME', text('apparatus_test_calc')), ('FNAM', text('Test Calcinator')),
                           ('AADT', struct.pack('<iffi', 2, 1.2, 5., 40))])
    raw += record('MISC', [('NAME', text('misc_test')), ('MCDT', struct.pack('<fii', .1, 1, 0))])
    for name, value in (('fWortChanceValue', 15.), ('fPotionStrengthMult', .5), ('iAlchemyMod', 2),
                        ('fPotionT1MagMult', 1.5), ('fPotionT1DurMult', .5), ('sPotionSuccess', 'You created a potion'),
                        ('sNotifyMessage50', '%s has no effect on you.'), ('sFortify', 'Fortify')):
        raw += gmst(name, value)
    return raw


def build(tmp):
    import prepare_inventory as inv
    base = Path(tmp)
    (base / 'Morrowind.esm').write_bytes(master())
    with patch.object(inv, 'resolve_data_files', return_value=base):
        report = inv.prepare(base, base / 'id1', palette=b'\0' * 768, models=False)
    return base / 'id1', report


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class AlchemyNativeTests(unittest.TestCase):
    def test_rules_visibility_shared_effects_brew_tools_checks_eating(self):
        native.NativeSourceTests().compile_run('aga_alchemy_rules_test.c', [SRC / 'aw_alchemy_rules.c'],
                                               cflags=UBSAN)

    def test_catalogue_block_read_by_the_engine_and_the_made_potion(self):
        with tempfile.TemporaryDirectory() as tmp:
            id1, _ = build(tmp)
            native.NativeSourceTests().compile_run('aga_alchemy_catalogue_test.c', [SRC / n for n in
                ('aw_inventory.c', 'aw_state.c', 'aw_ledger.c', 'aw_ledger_drops.c', 'mathlib.c')],
                arguments=[str(id1)], cflags=['-fsanitize=address,undefined', '-fno-sanitize-recover=all'])


class AlchemyBuilderTests(unittest.TestCase):
    def test_blocks_flags_and_settings_from_the_master(self):
        import prepare_alchemy as alc
        with tempfile.TemporaryDirectory() as tmp:
            id1, report = build(tmp)
            items = (id1 / 'inventory/items.awi').read_bytes()
            settings = (id1 / 'alchemy/settings.txt').read_text(encoding='cp1252')
        count = struct.unpack_from('<I', items, 4)[0]
        rows = {items[8 + i * 512:8 + i * 512 + 64].split(b'\0')[0].decode(): items[8 + i * 512:8 + (i + 1) * 512]
                for i in range(count)}
        flags = {k: struct.unpack_from('<I', r, 180)[0] for k, r in rows.items()}
        self.assertEqual({k for k, f in flags.items() if f & alc.FLAG_ALCHEMY},
                         {'ingred_test_01', 'ingred_test_02', 'p_test_b', 'p_test_s', 'apparatus_test_calc'})
        root = rows['ingred_test_01']
        self.assertEqual(struct.unpack_from('<BBHf', root, 440), (1, 4, 0, 0.))
        # Drain Attribute keeps its attribute (Agility), Restore Fatigue drops the stray skill; empty slots 255
        self.assertEqual([struct.unpack_from('<BBHH', root, 448 + 6 * i) for i in range(4)],
                         [(17, 3, 0, 0), (77, 255, 0, 0), (255, 255, 0, 0), (255, 255, 0, 0)])
        potion = rows['p_test_b']
        self.assertEqual(struct.unpack_from('<BB', potion, 440), (2, 2))
        self.assertEqual(struct.unpack_from('<BBHH', potion, 448), (75, 255, 1, 10))
        self.assertEqual(struct.unpack_from('<BBHH', potion, 454), (83, 16, 30, 5))
        self.assertEqual(potion[460:496], b'\0' * 36)
        calc = rows['apparatus_test_calc']
        self.assertEqual(struct.unpack_from('<iii', calc, 160), (7, 2, 40))
        kind, n, _, quality = struct.unpack_from('<BBHf', calc, 440)
        self.assertEqual((kind, n), (3, 0))
        self.assertAlmostEqual(quality, 1.2, places=5)
        self.assertFalse(flags['misc_test'] & alc.FLAG_ALCHEMY)
        lines = settings.splitlines()
        self.assertEqual(lines[0], 'AWAL1')
        self.assertIn('set fWortChanceValue 15', lines)
        self.assertIn('set iAlchemyMod 2', lines)
        self.assertIn('set fPotionT1MagMult 1.5', lines)
        self.assertIn('text sPotionSuccess You created a potion', lines)
        self.assertIn('text sNotifyMessage50 %s has no effect on you.', lines)
        self.assertIn('tier standard p_test_s', lines)
        self.assertIn('tier bargain p_test_b', lines)
        self.assertEqual(report['alchemy']['missing_settings'], [])
        self.assertEqual(report['alchemy']['tiers'], {'bargain': 'p_test_b', 'standard': 'p_test_s'})

    def test_block_layout_and_refusals(self):
        import prepare_alchemy as alc
        self.assertEqual(len(alc.pack(alc.KIND_POTION, [(1, 255, 2, 3)] * 8)), alc.BLOCK)
        with self.assertRaises(ValueError):
            alc.pack(alc.KIND_POTION, [(1, 255, 2, 3)] * 9)
        with self.assertRaises(ValueError):
            alc.apparatus_block(struct.pack('<iffi', 4, 1., 1., 1))
        with self.assertRaises(ValueError):
            alc.ingredient_block(b'\0' * 40)
        # a skill effect keeps its skill, an attribute effect its attribute, any other neither
        self.assertEqual(alc.effect_argument(83, 16, 3), 16)
        self.assertEqual(alc.effect_argument(79, 16, 3), 3)
        self.assertEqual(alc.effect_argument(77, 16, 3), 255)

    def test_settings_without_the_masters_settings_are_left_out(self):
        import prepare_alchemy as alc
        out = alc.settings_text({'GMST': {}, 'SKIL': {}, 'SOUN': {}}, {}, {'drink': 'alchemy/drink.wav'})
        self.assertEqual(out, 'AWAL1\nsound drink alchemy/drink.wav\n')


class AlchemySourceContracts(unittest.TestCase):
    def test_engine_files_are_built_and_initialised(self):
        make = (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8')
        self.assertIn('aw_alchemy_rules.c aw_alchemy.c', make)
        self.assertIn('AW_AlchemyInit();', code('aw_debug.c'))

    def test_inventory_window_uses_drinks_eats_and_opens_through_the_hooks(self):
        ui = code('aw_worldui.c')
        self.assertIn('ok=aw_worldui_use(item);', ui)
        self.assertIn('if(ok==2){close_panel();if(aw_worldui_alchemy_open)aw_worldui_alchemy_open();return;}', ui)
        self.assertIn('inventory_action(inventory_usable(item)?3:', ui)   # then Read for books (4), else Equip
        # MADE-ITEM-NO-PICTURE-62: a made item's row shows its base item's picture
        self.assertIn('aw_worldui_icon_id?aw_worldui_icon_id(it->id):it->id', ui)
        self.assertIn('aw_worldui_icon_id=icon_id;', code('aw_alchemy.c'))
        inv = code('aw_inventory.c')
        self.assertIn('if(aw_inventory_command && aw_inventory_command())return;', inv)
        self.assertIn('(value.flags&~(127U|AW_INV_BEAST_HEAD|AW_INV_BEAST_FEET))', inv)   # flags 128/256 since v0.0.62

    def test_glue_follows_the_rules(self):
        glue = code('aw_alchemy.c')
        # a potion acts on the drinker, used up first; an ingredient's meal and a made potion train Alchemy
        self.assertIn('AW_MwscriptLand(NULL,e,m,n,AW_RANGE_SELF,AW_EFFECT_SOURCE_ITEM)', glue)
        self.assertLess(glue.index('if(!AW_ItemAdd(&aw_state,it->id,-1))return 0;'), glue.index('landed=AW_MwscriptLand'))
        self.assertIn('AW_LevelupUse(SKILL_ALCHEMY,USE_INGREDIENT,1)', glue)
        self.assertIn('AW_LevelupUse(SKILL_ALCHEMY,USE_CREATE_POTION,1)', glue)
        self.assertIn('m.cast_type=AW_MADE_POTION', glue)
        # nothing resident while closed: the window's state is freed on close
        self.assertIn('free(win->list);free(win->d);free(win);win=NULL;', glue)


if __name__ == '__main__':
    unittest.main()
