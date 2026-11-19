# SPDX-License-Identifier: GPL-3.0-only
"""SCROLL-CAST-64: a Cast Once scroll is cast as in OpenMW 0.51. The Magic window lists it under Magic Items with every
carried Cast When Used item (mwgui/spellmodel.cpp), a selection casts it with the cast button: the enchantment's
effects, no success roll, the scroll used up (mwmechanics/spellcasting.cpp CastSpell::cast(item)). A scroll's
enchantment may have charge 0 in the masters: Cast Once needs no charge, so it is selectable all the same.
v0.0.67 (the maintainer's decision, 18 November 2026, after the dev2 inventory offered only "E/Enter read"): Use in the
inventory casts it at once (the original reads it there, mwclass/book.cpp ActionRead; Read stays in the right button's
menu). The window's behaviour is proven in tests/aga_inventory_ui_test.c and the kind table in
tests/test_inventory_actions.py; the wiring below."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine/aga/src'


def body(text, start, end):
    return text[text.index(start):text.index(end, text.index(start))]


class ScrollCast(unittest.TestCase):
    def setUp(self):
        self.cast = (SRC / 'aw_cast.c').read_text(encoding='utf-8')
        self.inv = (SRC / 'aw_inventory.c').read_text(encoding='utf-8')

    def test_cast_once_needs_no_charge(self):
        sel = body(self.inv, 'int AW_MagicSelectable(', 'int AW_MagicSelect(')
        self.assertIn('item->enchant_kind==AW_ENCH_ONCE && item->enchantment[0]', sel)
        self.assertIn('item->enchant_kind==AW_ENCH_USED && item->charge_max>0', sel)
        # the HUD's bar never divides by a charge of 0
        icons = (SRC / 'aw_icons.c').read_text(encoding='utf-8')
        self.assertIn("item.enchant_kind==AW_ENCH_ONCE || !(item.charge_max>0)?1.0f:", icons)

    def test_the_magic_window_lists_the_items(self):
        castables = body(self.cast, 'static int window_castables(', 'static void window_select(')
        self.assertIn('AW_InventoryCarried(window_item,out);', castables)
        item = body(self.cast, 'static void window_item(', 'static int window_castables(')
        self.assertIn('AW_MagicSelectable(it)', item)
        self.assertIn('out->power[out->count]=2;out->kind[out->count]=2;out->index[out->count]=state_row;', item)
        select = body(self.cast, 'static void window_select(', 'static int window_status(')
        self.assertIn('AW_MagicSelect(&aw_state,&it)', select)
        self.assertIn('sel_kind=-1;sel_index=-1;', select)   # an item or a spell, never both
        draw = (SRC / 'aw_statswin.c').read_text(encoding='utf-8')
        self.assertIn('if(list->power[i]!=(section==0?1:section==1?0:2))continue;', draw)

    def test_the_cast_is_the_items_rule(self):
        # the cast button with an item selected and no spell: the item's cast; a Cast Once item: no roll, used up
        now = body(self.cast, 'static void cast_now(void){', 'if(!(p=AW_MwscriptPlayerRecord()))')
        self.assertIn('if(AW_MagicSelectedItem(&it)){use_item(&it);return;}', now)
        cast = body(self.cast, 'static int item_cast(', 'static int use_item(')
        self.assertIn('else if(mg->type==AW_ENCH_ONCE-1 && !god)AW_ItemAdd(&aw_state,it->id,-1);', cast)
        self.assertNotIn('AW_CastChance', cast)
        self.assertFalse(re.search(r'\broll\b', cast))

    def test_the_inventory_casts_it_and_still_reads_it(self):
        ui = (SRC / 'aw_worldui.c').read_text(encoding='utf-8')
        self.assertIn('item->category==AW_INV_BOOK', ui)   # OpenMW Book::use: ActionRead, kept in the menu
        rule = body(self.inv, 'int AW_InventoryItemAction(', 'const char *AW_InventoryActionWord(')
        # worn classes first, then a Cast Once item is cast, then usables, then books are read
        self.assertLess(rule.index('AW_INV_EQUIP'), rule.index('AW_ENCH_ONCE'))
        self.assertLess(rule.index('AW_ENCH_ONCE'), rule.index('AW_INV_BOOK'))
        action = body(ui, 'static void inventory_action(int action){', 'static void inventory_double(')
        self.assertIn('if(action==5 && inventory_castable(item)){', action)
        self.assertLess(action.index('close_panel();'), action.index('aw_worldui_cast(&cast);'))   # a copy, then closed
        # the cast's own refusals and the shared cast path (use_item: no roll, the scroll used up)
        self.assertIn('aw_worldui_cast=inventory_cast;', self.cast)
        cast = body(self.cast, 'static int inventory_cast(', '/* one carried item of AW_InventoryCarried')
        self.assertIn('AW_ControlAllowed(AW_CONTROL_PLAYER|AW_CONTROL_MAGIC)', cast)
        self.assertIn('if(sv.time<lock_until || pending)return 0;', cast)
        self.assertIn('return use_item(it);', cast)


if __name__ == '__main__':
    unittest.main()
