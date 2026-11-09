# SPDX-License-Identifier: GPL-3.0-only
"""HELD-WEAPON-WRONG-MODEL-62: an actor's held weapon or shield is always drawn with its own item model.

The item tables of aw_items.c keep precache indices of one server. Skipping the opening (`dbg aw hors 0`) reloads
the same world, so sv.worldmodel does not change; the tables used to survive the reload and their indices then named
other models of the new precache (a guard drew an opening NPC as his weapon). These checks keep:
- every new server clearing the tables, the precache names and the light carriers (a normal start and a reload alike);
- the drawing side checking that a held item's slot still names the tag's own item model, an "items/" model."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


class HeldItemModelTests(unittest.TestCase):
    def test_every_new_server_clears_the_item_tables(self):
        sv = code('sv_main.c')
        spawn = sv[sv.index('void SV_SpawnServer'):]
        clear = spawn.index('memset (&sv, 0, sizeof(sv));')
        reset = spawn.index('AW_ItemsSceneReset();')
        world = spawn.index('sv.worldmodel = Mod_ForName')
        # after the old server is gone and before the new world and its actors load (AW_ItemsPrep)
        self.assertLess(clear, reset)
        self.assertLess(reset, world)
        self.assertIn('#include "aw_items.h"', sv)

    def test_scene_reset_leaves_no_stale_slot(self):
        items = code('aw_items.c')
        body = re.search(r'void AW_ItemsSceneReset\(void\) \{(.*?)\n\}', items, re.S).group(1)
        for part in ('used=0', 'named=0', 'memset(table,0,sizeof(table))', 'level_world=NULL',
                     'carrier_count=0', 'memset(carriers,0,sizeof(carriers))', 'carrier_world=NULL'):
            self.assertIn(part, body)

    def test_held_item_drawn_only_from_its_own_item_model(self):
        items = code('aw_items.c')
        show = items[items.index('int AW_ItemsShow('):]
        show = show[:show.index('\n}\n')]
        self.assertLess(show.index('if(!held_item_ok(actor,t,k,i))continue;'), show.index('ED_Alloc()'))
        check = items[items.index('static int held_item_ok('):]
        check = check[:check.index('\n}\n')]
        self.assertIn('AW_ItemsPathHash(name)==table[t].item_hash[k]', check)
        self.assertIn('AW_ItemsIsItemPath(name)', check)
        self.assertIn('not drawn', check)
        # both tag forms record the hash of the path they precached
        self.assertEqual(items.count('item_hash[k]=table[used].item[k]?AW_ItemsPathHash(items[k]):0;'), 2)


if __name__ == '__main__':
    unittest.main()
