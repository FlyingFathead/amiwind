# SPDX-License-Identifier: GPL-3.0-only
"""EQUIP-ACTION-REGRESSION-62: every wearable or wieldable record gets the Equip action from its class. A carried item's
script refuses equipping only when it reads OnPCEquip or PCSkipEquip (and dropping only when it reads OnPCDrop); the
census office's dagger (an OnActivate-only script) is equipped and dropped like the iron dagger. The catalogue stage
checks every record of the game and stops on an equippable record refused without a named reason; the inventory window
offers Equip by class (aw_worldui.c inventory_equippable)."""
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import prepare_inventory as inv
from test_weapon_kit import MESH, master, record, text, weapon

EQUIP, DROP, SUPPORTED = 1, 2, 4


def script(name, body):
    return record('SCPT', [('SCHD', name.encode().ljust(32, b'\0') + b'\0' * 20), ('SCTX', body.encode())])


def catalogue(raw):
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / 'Morrowind.esm').write_bytes(raw)
        with patch.object(inv, 'resolve_data_files', return_value=base):
            report = inv.prepare(base, base / 'id1', palette=b'\0' * 768, models=False,
                                 model_table={inv.mesh_key(MESH): 'progs/items/m0000000000000001.mdl'})
        items = (base / 'id1' / 'inventory' / 'items.awi').read_bytes()
    rows = {}
    for i in range(struct.unpack_from('<I', items, 4)[0]):
        row = items[8 + i * 512:8 + (i + 1) * 512]
        rows[row[:64].split(b'\0')[0].decode()] = struct.unpack_from('<I', row, 180)[0]
    return rows, report


class EquipClassTests(unittest.TestCase):
    def test_script_rule(self):
        self.assertTrue(inv.script_allows('', inv.EQUIP_SCRIPT_WORDS))
        on_activate = 'begin CharGenDagger\nif ( OnActivate == 1 )\n MessageBox "x"\n Activate\nendif\nend'
        self.assertTrue(inv.script_allows(on_activate, inv.EQUIP_SCRIPT_WORDS))
        self.assertTrue(inv.script_allows(on_activate, inv.DROP_SCRIPT_WORDS))
        skip = 'begin x\nshort OnPCEquip\nshort PCSkipEquip\nif ( OnPCEquip == 1 )\n set PCSkipEquip to 1\nendif\nend'
        self.assertFalse(inv.script_allows(skip, inv.EQUIP_SCRIPT_WORDS))
        self.assertTrue(inv.script_allows(skip, inv.DROP_SCRIPT_WORDS))
        reacts = 'begin x\nshort OnPCEquip\nif ( OnPCEquip == 1 )\n MessageBox "worn"\nendif\nend'
        self.assertTrue(inv.script_allows(reacts, inv.EQUIP_SCRIPT_WORDS))     # worn; the reaction is listed
        self.assertFalse(inv.script_allows('begin y\nshort OnPCDrop\nend', inv.DROP_SCRIPT_WORDS))
        self.assertTrue(inv.script_allows('begin y\n; PCSkipEquip only in a comment\nend', inv.EQUIP_SCRIPT_WORDS))

    def test_census_dagger_equips_and_drops_like_the_iron_dagger(self):
        raw = master() + script('chargendagger', 'begin CharGenDagger\nshort OnPCEquip\nif ( OnActivate == 1 )\n'
                                ' Activate\nendif\nif ( OnPCEquip == 1 )\n MessageBox "x"\nendif\nend')
        rows, report = catalogue(raw)
        self.assertEqual(rows['chargen dagger'] & 7, EQUIP | DROP | SUPPORTED)
        self.assertEqual(rows['iron dagger'] & 7, EQUIP | DROP | SUPPORTED)
        self.assertNotIn('chargen dagger', report.get('equip_refused', {}))
        self.assertIn('chargen dagger', report['equip_reaction_not_run'])

    def test_skip_equip_script_is_refused_with_its_reason(self):
        raw = master() + weapon('odd dagger', 'Odd Dagger', 0, 5, (1, 2), extra=[('SCRI', text('oddscript'))])
        raw += script('oddscript', 'begin oddscript\nshort PCSkipEquip\nset PCSkipEquip to 1\nend')
        rows, report = catalogue(raw)
        self.assertEqual(rows['odd dagger'] & (EQUIP | SUPPORTED), EQUIP)   # the class stays: Equip shown
        self.assertIn('PCSkipEquip', report['equip_refused']['odd dagger'])

    def test_every_equippable_record_has_a_named_reason_or_equips(self):
        rows, report = catalogue(master())
        refused = report.get('equip_refused', {})
        for ident, flags in rows.items():
            if flags & EQUIP and not flags & SUPPORTED:
                self.assertTrue(refused.get(ident), ident)
        self.assertGreater(report['equip_allowed'], 0)

    def test_unknown_refusal_stops_the_stage(self):
        item = {'kind': 'WEAP', 'subtype': 0, 'enchantment': '', 'raw': b'\0' * 32}
        self.assertIsNone(inv.equip_refusal(item, '', 'progs/items/m1.mdl', {}, True))
        self.assertEqual(inv.equip_refusal(item, '', '', {}, True), 'no world model to hold')

    # The whole game (the original data is not in the gate): every build runs the stage over every item record, and
    # the stage raises on a wearable record refused without a named reason (prepare_inventory.py equip_refusal).
    def test_the_stage_checks_every_record(self):
        source = (ROOT / 'tools/prepare_inventory.py').read_text(encoding='utf-8')
        self.assertIn("refused Equip without a named reason", source)


class EquipClassEngineTests(unittest.TestCase):
    def test_window_offers_equip_by_class(self):
        source = (ROOT / 'engine/aga/src/aw_worldui.c').read_text(encoding='utf-8')
        body = source[source.index('static int inventory_equippable('):source.index('int (*aw_worldui_use)')]
        self.assertIn('item->flags&AW_INV_EQUIP)!=0', body)
        self.assertNotIn('AW_InventoryCanEquip', body)
        action = source[source.index('static void inventory_action('):source.index('static int inventory_list_right(')]
        self.assertIn('This item cannot be equipped now.', action)

    def test_torch_is_a_held_light_with_its_commands(self):
        # TORCH-HIDES-HELM-62: the torch's mesh gets a held file like every carried light (no skip), so the held torch
        # draws on the assembled body; the debug torch is given by dbg torch / give dbgtorch / give debugtorch
        inv = (ROOT / 'tools/prepare_inventory.py').read_text(encoding='utf-8')
        self.assertNotIn('torch_mesh_skipped', inv)
        catalogue = (ROOT / 'config/debug-commands.txt').read_text(encoding='utf-8')
        for words in ('torch', 'give dbgtorch', 'give debugtorch'):
            self.assertIn('PLAYTESTING|%s|aw_inventory|' % words, catalogue)
        torch = (ROOT / 'engine/aga/src/aw_debug_torch.c').read_text(encoding='utf-8')
        give = torch[torch.index('void AW_DebugTorchGive(void)'):torch.index('void AW_DebugTorchInit(')]
        self.assertIn('AW_ItemAdd(&aw_state,AW_DEBUG_TORCH_ID,1)', give)   # exactly one each time
        self.assertIn('AW_UISubtitle(', give)
        self.assertNotIn('Cmd_AddCommand', give)                            # no resident command of its own
        console = (ROOT / 'engine/aga/src/aw_console.c').read_text(encoding='utf-8')
        self.assertIn('strcpy(out+used," give debugtorch");', console)
        self.assertIn('!Q_strcasecmp(Cmd_Argv(2),"debugtorch")){AW_DebugTorchGive();return;}',
                      (ROOT / 'engine/aga/src/aw_inventory.c').read_text(encoding='utf-8'))
        self.assertIn('time=LIGHT_INFINITE', inv)                           # it never burns out

    def test_v_lights_only_an_equipped_light(self):
        torch = (ROOT / 'engine/aga/src/aw_torch.c').read_text(encoding='utf-8')
        toggle = torch[torch.index('static void toggle(void)'):torch.index('void AW_TorchInit(void)')]
        self.assertIn('if(v->_float!=1 && aw_torch_item_lit && !aw_torch_item_lit()){', toggle)
        self.assertLess(toggle.index('aw_torch_item_lit()'), toggle.index('v->_float=v->_float==1?0:1;'))

    def test_books_offer_read(self):
        source = (ROOT / 'engine/aga/src/aw_worldui.c').read_text(encoding='utf-8')
        self.assertIn('item->category==AW_INV_BOOK', source[source.index('static int inventory_readable('):])
        self.assertIn('inventory_readable(item)?4:1', source)
        self.assertIn('"Read"', source)
        reader = (ROOT / 'engine/aga/src/aw_reader.c').read_text(encoding='utf-8')
        self.assertIn('aw_worldui_read=carried_open', reader)
        opened = reader[reader.index('static int carried_open('):reader.index('static void close_reader(int take)\n{')]
        self.assertIn('book_load(id)', opened)
        self.assertIn('action=0', opened)          # Close only: a carried book is not taken again


if __name__ == '__main__':
    unittest.main()
