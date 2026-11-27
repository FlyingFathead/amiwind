# SPDX-License-Identifier: GPL-3.0-only
"""HELD-ITEM-TABLE-FULL-69: an armed actor met after the level's 64th armed model still draws its items.

The engine keeps one item tag table per armed actor model, 64 a level (engine/aga/src/aw_items.c). A session on the
joined world is one level, and the tables were never given back, so from the 65th distinct armed model on every armed
actor drew no weapon, shield or carried torch until the next load (the actor table names 354 armed models). Now a
spawn that finds the table full takes the entry of a skeletal model no live actor stands on, wears, may wear or
carries a light for (AW_ItemsTableSlot, table_slot), as the animation layouts already do (aw_anim.c reclaim)."""
import os
import re
import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'engine' / 'aga' / 'src'
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(1, str(ROOT / 'tools'))

import test_aga_native_source as native  # noqa: E402

UBSAN = ['-fsanitize=undefined', '-fno-sanitize-recover=all']


def code(name):
    return re.sub(r'/\*.*?\*/', '', (SRC / name).read_text(encoding='utf-8'), flags=re.S)


def body(text, head):
    start = text.index(head)
    return text[start:text.index('\n}\n', start)]


@unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a host C compiler is required')
class TableSlotNativeTests(unittest.TestCase):
    def test_a_session_of_354_armed_models_draws_every_one(self):
        # the old rule left 290 of the 354 without their items; the 65th model takes an unused skeletal entry; an
        # entry in use and a row table are never taken
        native.NativeSourceTests().compile_run('aga_items_table_slot_test.c', [SRC / 'aw_items.c'],
                                               defines=('AW_ITEMS_HOST_TEST',), cflags=UBSAN)


class TableSlotWiringTests(unittest.TestCase):
    def setUp(self):
        self.items = code('aw_items.c')
        self.prep = body(self.items, 'static void prep(model_t *m,const char *name,int numframes,int load) {')
        self.slot = body(self.items, 'static int table_slot(void) {')

    def test_a_full_table_no_longer_refuses_by_its_count_alone(self):
        self.assertNotIn('if(used>=TABLE){', self.prep)
        self.assertIn('if((at=table_slot())<0){', self.prep)
        self.assertIn('if(declared && !full_spawns++)', self.prep)
        self.assertIn('return AW_ItemsTableSlot(used,TABLE,flags);', self.slot)
        # the rule is in the half the fixture compiles
        host = self.items[:self.items.index('#ifndef AW_ITEMS_HOST_TEST')]
        self.assertIn('int AW_ItemsTableSlot(int used,int size,const unsigned char *flags) {', host)

    def test_the_scan_keeps_every_entry_a_live_actor_uses(self):
        # its own model, the model under a worn mover, the mover its layout names, the light it carries
        self.assertIn('if(e->free || !(m=model_of(e)) || m==sv.worldmodel)continue;', self.slot)
        self.assertIn('if(table[k].model==m)flags[k]|=AW_ITEMS_SLOT_BUSY;', self.slot)
        self.assertIn('(base=AW_AnimWornBase(e))>0', self.slot)
        self.assertIn('if(table[k].model==sv.models[base])flags[k]|=AW_ITEMS_SLOT_BUSY;', self.slot)
        self.assertIn('if(!strcmp(table[k].model->name,a->mover))flags[k]|=AW_ITEMS_SLOT_BUSY;', self.slot)
        self.assertIn('flags[carriers[i].table]|=AW_ITEMS_SLOT_BUSY;', self.slot)
        # only a skeletal entry can be given on: a row table's rows live on the level's memory
        self.assertIn('table[k].skel && !table[k].rows?AW_ITEMS_SLOT_SKEL:0', self.slot)
        self.assertIn('int AW_AnimWornBase(edict_t *e) {', code('aw_anim.c'))

    def test_one_scan_serves_the_spawns_of_one_server_time(self):
        self.assertIn('if(slot_scan_time==sv.time)return AW_ItemsTableSlot(used,TABLE,flags);', self.slot)
        # a model already in the table that spawns again is in use for a scan made just before
        self.assertIn('if((k=entry_of(m))>=0){slot_flags[k]|=AW_ITEMS_SLOT_BUSY;return;}', self.prep)
        taken = body(self.items, 'static void table_taken(int at,const aw_items_entry_t *fresh) {')
        self.assertIn('|AW_ITEMS_SLOT_BUSY);', taken)

    def test_an_entry_in_use_is_written_only_by_a_tag_that_holds_an_item(self):
        # the new table is built beside the table: a refused tag, or one naming nothing, takes no entry
        self.assertNotIn('table[used].', self.prep)
        self.assertNotIn('table[at]', self.prep)
        self.assertEqual(self.prep.count('if(any)table_taken(at,&fresh);'), 2)
        taken = body(self.items, 'static void table_taken(int at,const aw_items_entry_t *fresh) {')
        self.assertIn('if(at==used)used++;', taken)
        self.assertIn('table[at]=*fresh;', taken)
        # a carrier slot that still names a given-on entry is freed with its light
        self.assertIn('for(i=0;i<carrier_count;i++)if(carriers[i].table==at){', taken)
        self.assertIn('carriers[i].actor=NULL;carriers[i].light=NULL;', taken)

    def test_a_carrier_slot_whose_actor_is_gone_is_used_again(self):
        prep = body(self.items, 'void AW_ItemsPrep(edict_t *actor) {')
        self.assertIn('for(i=0;i<carrier_count && carriers[i].actor && !carriers[i].actor->free;i++);', prep)
        self.assertIn('if(i<carrier_count || carrier_count<CARRIERS){', prep)

    def test_the_counts_start_clean_and_are_shown(self):
        for head in ('void AW_ItemsSceneReset(void) {', 'static void level_check(void) {'):
            self.assertIn('reclaims=slot_scans=0;slot_scan_time=-1;', body(self.items, head))
        self.assertIn('counts[4]=reclaims;counts[5]=slot_scans;', self.items)
        kit = code('aw_animkit.c')
        self.assertIn('int counts[11],info[3];', kit)
        self.assertIn('given on', kit)


if __name__ == '__main__':
    unittest.main()
