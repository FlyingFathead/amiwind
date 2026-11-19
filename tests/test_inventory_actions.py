# SPDX-License-Identifier: GPL-3.0-only
"""INVENTORY-EQUIP-HINTS-67 (EQUIP-ACTION-REGRESSION-62, seen again on the v0.0.67-dev2 image; SCROLL-CAST-64): the
inventory window offers one action per item kind, and a table over every kind decides it, so the Equip hint cannot go
missing again unseen. The real builder stage (tools/prepare_inventory.py) writes the catalogue from a synthetic master
with one record of every item kind and subtype the catalogue takes; the real engine reader and rule
(tests/aga_inventory_actions_test.c: aw_inventory.c AW_InventoryScan, AW_InventoryItemAction) judge every row against
the table below. A kind the original equips or uses but this engine cannot yet is in the table with its named reason
and its register entry; a new kind in the catalogue without a row here fails."""
import os
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'tests', ROOT / 'tools', ROOT / 'src'):   # src first (TEST-WORKER-SYSPATH-32)
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import prepare_inventory as inv  # noqa: E402
from test_weapon_kit import MESH, gmst, master, record, text, weapon  # noqa: E402

# The original's armour type weights (prepare_combat.ARMOR_TYPE_GMST): every armour piece is classed by them.
ARMOUR_WEIGHTS = (('iHelmWeight', 5), ('iCuirassWeight', 30), ('iPauldronWeight', 10), ('iGreavesWeight', 15),
                  ('iBootsWeight', 20), ('iGauntletWeight', 5))
WEAPON_TYPES = range(14)      # WPDT 0..13: short blade ... thrown, arrow, bolt
ARMOUR_TYPES = range(11)      # AODT 0..10: helmet ... right bracer
CLOTHING_TYPES = range(10)    # CTDT 0..9: pants ... amulet

# What the original does with each kind (OpenMW 0.53 mwclass/*.cpp getEquipmentSlots and use), and what the inventory
# window here offers. Where they differ, the reason and its register entry.
NOT_YET = {
    'arrow': 'arrows and bolts are equipped in the ammunition slot in the original; carried here until the player '
             'shoots (ACTOR-RANGED-COMBAT-MISSING-66, INVENTORY-EQUIP-KINDS-NOT-YET-67)',
    'lockpick': 'equipped in the right hand in the original (mwclass/lockpick.cpp, probe.cpp); carried here until '
                'lockpicking and probing land (LOCKED-CONTAINERS-NEVER-OPEN-67, INVENTORY-EQUIP-KINDS-NOT-YET-67)',
    'repair': 'used in the original (mwclass/repair.cpp: the repair window); carried here until repairing lands '
              '(INVENTORY-EQUIP-KINDS-NOT-YET-67)',
}


def clothing(ident, kind):
    return record('CLOT', [('NAME', text(ident)), ('FNAM', text(ident.title())), ('MODL', text(MESH)),
                           ('ITEX', text('c\\tx.tga')), ('CTDT', struct.pack('<ifHH', kind, 1., 5, 10))])


def armour(ident, kind):
    return record('ARMO', [('NAME', text(ident)), ('FNAM', text(ident.title())), ('MODL', text(MESH)),
                           ('ITEX', text('a\\tx.tga')), ('AODT', struct.pack('<ifiiii', kind, 3., 20, 100, 30, 8))])


def book(ident, scroll, enchantment=None):
    fields = [('NAME', text(ident)), ('FNAM', text(ident.title())), ('MODL', text(MESH)), ('ITEX', text('b\\tx.tga')),
              ('BKDT', struct.pack('<fiiii', 1., 10, scroll, -1, 50))]
    if enchantment:
        fields.append(('ENAM', text(enchantment)))
    return record('BOOK', fields + [('TEXT', text('<DIV>The text.'))])


def enchantment(ident, kind):
    effect = struct.pack('<hbbiiiii', 9, -1, -1, 0, 0, 30, 10, 10)   # Jump on self, as a scroll of Icarian Flight
    return record('ENCH', [('NAME', text(ident)), ('ENDT', struct.pack('<4i', kind, 5, 0, 0)), ('ENAM', effect)])


def misc(ident):
    return record('MISC', [('NAME', text(ident)), ('FNAM', text(ident.title())), ('MODL', text(MESH)),
                           ('ITEX', text('m\\tx.tga')), ('MCDT', struct.pack('<fii', 1., 2, 0))])


def light(ident, carried):
    lhdt = struct.pack('<fiii4BI', 1., 3, 600, 128, 255, 200, 100, 0, 2 if carried else 0)
    return record('LIGH', [('NAME', text(ident)), ('FNAM', text(ident.title())), ('MODL', text(MESH)),
                           ('ITEX', text('l\\tx.tga')), ('LHDT', lhdt)])


def potion(ident):
    effect = struct.pack('<hbbiiiii', 75, -1, -1, 0, 0, 1, 10, 10)    # Restore Health
    return record('ALCH', [('NAME', text(ident)), ('FNAM', text(ident.title())), ('MODL', text(MESH)),
                           ('TEXT', text('p\\tx.tga')), ('ALDT', struct.pack('<fii', 1., 15, 0)), ('ENAM', effect)])


def ingredient(ident):
    irdt = struct.pack('<fi4i4i4i', .1, 1, 75, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1)
    return record('INGR', [('NAME', text(ident)), ('FNAM', text(ident.title())), ('MODL', text(MESH)),
                           ('ITEX', text('i\\tx.tga')), ('IRDT', irdt)])


def tool(kind, ident):
    data = {'APPA': ('AADT', struct.pack('<iffi', 0, .5, 1., 10)), 'LOCK': ('LKDT', struct.pack('<fifi', .25, 6, 1., 25)),
            'PROB': ('PBDT', struct.pack('<fifi', .25, 6, 1., 25)), 'REPA': ('RIDT', struct.pack('<fiif', 2., 6, 10, 1.))}
    return record(kind, [('NAME', text(ident)), ('FNAM', text(ident.title())), ('MODL', text(MESH)),
                         ('ITEX', text('t\\tx.tga')), data[kind]])


def every_kind():
    """The synthetic master and {id: the action the window must offer}: test_weapon_kit's master (its weapons, an arrow,
    a shield) and one record of every kind and subtype the catalogue takes."""
    raw = master() + b''.join(gmst(*g) for g in ARMOUR_WEIGHTS)
    want = {'iron dagger': 'equip', 'iron fork': 'equip', 'chitin dagger': 'equip', 'glass dagger': 'equip',
            'firebite dagger': 'equip', 'chargen dagger': 'equip', 'vfx_bolt': 'none', 'chitin short bow': 'equip',
            'iron arrow': 'none', 'chitin_shield': 'equip'}
    for kind in WEAPON_TYPES:
        ident = 'weapon type %d' % kind
        raw += weapon(ident, ident.title(), kind, 5, (1, 2))
        want[ident] = 'none' if kind >= 12 else 'equip'          # NOT_YET['arrow']
    for kind in ARMOUR_TYPES:
        raw += armour('armour type %d' % kind, kind)
        want['armour type %d' % kind] = 'equip'
    for kind in CLOTHING_TYPES:
        raw += clothing('clothing type %d' % kind, kind)
        want['clothing type %d' % kind] = 'equip'
    raw += enchantment('scroll_jump_en', 0) + enchantment('amulet_used_en', 2)
    raw += book('plain book', 0) + book('plain note', 1) + book('magic scroll', 1, 'scroll_jump_en')
    want.update({'plain book': 'read', 'plain note': 'read', 'magic scroll': 'cast'})
    raw += record('CLOT', [('NAME', text('used amulet')), ('FNAM', text('Used Amulet')), ('MODL', text(MESH)),
                           ('ITEX', text('c\\tx.tga')), ('CTDT', struct.pack('<ifHH', 9, 1., 5, 10)),
                           ('ENAM', text('amulet_used_en'))])
    want['used amulet'] = 'equip'     # a Cast When Used amulet is worn first; cast from the magic window
    raw += misc('plain misc') + light('carried light', True) + light('fixed light', False)
    want.update({'plain misc': 'none', 'carried light': 'equip'})   # a fixed light is scenery: no catalogue row
    raw += potion('plain potion') + ingredient('plain ingredient') + tool('APPA', 'plain apparatus')
    want.update({'plain potion': 'use', 'plain ingredient': 'use', 'plain apparatus': 'use'})
    raw += tool('LOCK', 'plain lockpick') + tool('PROB', 'plain probe') + tool('REPA', 'plain repair')
    want.update({'plain lockpick': 'none', 'plain probe': 'none', 'plain repair': 'none'})   # NOT_YET
    return raw, want


def catalogue(tmp, raw):
    base = Path(tmp)
    (base / 'Morrowind.esm').write_bytes(raw)
    with patch.object(inv, 'resolve_data_files', return_value=base):
        inv.prepare(base, base / 'id1', palette=b'\0' * 768, models=False,
                    model_table={inv.mesh_key(MESH): 'progs/items/m0000000000000001.mdl'})
    return base / 'id1'


class InventoryActionTableTests(unittest.TestCase):
    def test_every_catalogue_kind_has_a_row(self):
        # a new record kind taken into the catalogue needs its row (and its action decided) here
        covered = {'WEAP', 'ARMO', 'CLOT', 'ALCH', 'INGR', 'BOOK', 'MISC', 'LIGH', 'APPA', 'LOCK', 'PROB', 'REPA'}
        self.assertEqual(set(inv.KINDS), covered)
        self.assertEqual(set(inv.CLOTHING_SLOTS), set(CLOTHING_TYPES))
        self.assertEqual(set(inv.ARMOUR_SLOTS), set(ARMOUR_TYPES))
        self.assertEqual(set(inv.HELD_WEAPONS) | {12, 13}, set(WEAPON_TYPES))

    @unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
    @unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
    def test_the_window_offers_each_kinds_action(self):
        import test_aga_native_source as native
        raw, want = every_kind()
        with tempfile.TemporaryDirectory() as tmp:
            id1 = catalogue(tmp, raw)
            table = Path(tmp) / 'actions.txt'
            table.write_text(''.join('%s\t%s\n' % (k, v) for k, v in sorted(want.items())), encoding='ascii')
            src = ROOT / 'engine' / 'aga' / 'src'
            native.NativeSourceTests().compile_run(
                'aga_inventory_actions_test.c',
                [src / n for n in ('aw_inventory.c', 'aw_state.c', 'aw_ledger.c', 'aw_ledger_drops.c', 'mathlib.c')],
                arguments=[str(id1), str(table)], cflags=['-fsanitize=address,undefined', '-fno-sanitize-recover=all'])

    def test_the_magic_scroll_row_is_cast_once(self):
        # SCROLL-CAST-64: the catalogue keeps a scroll's enchantment and its kind (Cast Once = ENDT type 0, stored + 1)
        raw, _ = every_kind()
        with tempfile.TemporaryDirectory() as tmp:
            items = (catalogue(tmp, raw) / 'inventory' / 'items.awi').read_bytes()
        rows = {}
        for i in range(struct.unpack_from('<I', items, 4)[0]):
            row = items[8 + i * 512:8 + (i + 1) * 512]
            rows[row[:64].split(b'\0')[0].decode()] = row
        scroll = rows['magic scroll']
        self.assertEqual(scroll[312:376].split(b'\0')[0], b'scroll_jump_en')   # the enchantment's id
        self.assertEqual(scroll[496], 1)                                         # AW_ENCH_ONCE
        self.assertEqual(rows['plain note'][496], 0)

    def test_the_not_yet_kinds_name_their_entries(self):
        for reason in NOT_YET.values():
            self.assertIn('INVENTORY-EQUIP-KINDS-NOT-YET-67', reason)


if __name__ == '__main__':
    unittest.main()
