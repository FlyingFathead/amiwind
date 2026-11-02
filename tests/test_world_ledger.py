# SPDX-License-Identifier: GPL-3.0-only
"""The world change list (CELL-CHANGES-59): one sorted list of what the player and the scripts changed on placed
objects, for the whole world, kept for the session and saved (engine aw_ledger.h, aw_ledger.c, aw_ledger_drops.c,
AWS4 feature 32 in aw_save_codec.c). Native round trips of every field and place (tests/aga_world_ledger_test.c), and
the engine wiring: the object state, the take, the drops and the placed items read and write the one list; the old
fixed tables stay selectable; old saves keep loading."""
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools', ROOT / 'tests'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
SRC = ROOT / 'engine/aga/src'


def code(name):
    return (SRC / name).read_text(encoding='utf-8')


def body(text, head):
    """The body of the C function that starts with HEAD (to its closing brace at column 0)."""
    start = text.index(head)
    return text[start:text.index('\n}\n', start) + 2]


class LedgerNativeTests(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
    @unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
    def test_round_trips(self):
        from test_aga_native_source import NativeSourceTests
        with tempfile.TemporaryDirectory(prefix='amiwind-world-ledger-') as tmp:
            out = Path(tmp) / 'out.txt'
            NativeSourceTests.compile_run(self, 'aga_world_ledger_test.c',
                                          [SRC / n for n in ('aw_ledger.c', 'aw_ledger_drops.c', 'aw_save_codec.c',
                                                             'aw_story.c', 'aw_state.c', 'aw_inventory.c')],
                                          defines=['AW_INVENTORY_RULES_ONLY'],
                                          cflags=['-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                                                  '-Wno-unused-parameter', '-fsanitize=undefined,address',
                                                  '-fno-sanitize-recover=all'],
                                          arguments=[str(out)])
            lines = out.read_text(encoding='ascii').splitlines()
        for part in ('rows ok', 'places ok', 'fields ok', 'refusals ok', 'versions ok', 'done'):
            self.assertIn(part, lines)
        big = next(line for line in lines if line.startswith('big '))
        self.assertTrue(big.startswith('big 20000 rows'), big)
        self.assertTrue(any(line.startswith('drops ') for line in lines))


class LedgerWiringTests(unittest.TestCase):
    def test_one_list_with_its_ceiling_declared(self):
        header = code('aw_ledger.h')
        self.assertIn('#define AW_LEDGER_ROWS 32768', header)
        ledger = code('aw_ledger.c')
        # grows in steps, never a fixed table; its worst case is declared for the resident registry
        self.assertIn('AW_TryRealloc(l->row', ledger)
        self.assertIn('AW_RESIDENT_GROWS("world change list rows (CELL-CHANGES-59)",AW_LEDGER_ROWS,', ledger)
        self.assertNotRegex(ledger, r'static\s+aw_ledger_row_t\s+\w+\s*\[')
        make = (ROOT / 'engine/aga/Makefile').read_text(encoding='utf-8')
        self.assertIn('aw_ledger.c aw_ledger_drops.c aw_save_codec.c', make)

    def test_save_writes_and_reads_the_list(self):
        save = code('aw_save.c')
        self.assertIn('save_changes.ledger=&aw_ledger;', save)
        self.assertIn('aw_save_ledger_encode=AW_LedgerEncode;aw_save_ledger_decode=AW_LedgerDecode;', save)
        # the buffer grows with the list: a long list never refuses the save
        self.assertIn('capacity+=need+8;', save)
        # the loaded list becomes the session's before an older save's object entries join it
        self.assertLess(save.index('AW_LedgerMove(&aw_ledger,&pending_ledger);'),
                        save.index('aw_save_objects_import(&pending_changes)'))
        self.assertIn('AW_LedgerClear(&aw_ledger);', body(save, 'void AW_SaveReset(void)'))
        codec = code('aw_save_codec.c')
        self.assertIn('(ledgered?32U:0U)', codec)
        self.assertIn('if(features>63)error=1;', codec)

    def test_objects_take_and_hide_through_the_list(self):
        host = code('aw_mwhost.c')
        self.assertIn('if(aw_ledger_on)return ledger_take(reference,stolen);',
                      body(host, 'int AW_ObjectTake(unsigned int reference,int stolen)'))
        take = body(host, 'static int ledger_take(uint32_t reference,int stolen)')
        self.assertIn('AW_LEDGER_TAKEN', take)
        self.assertNotIn('AW_LEDGER_DISABLED|', take.split('AW_LedgerPut')[1])
        # Enable clears only DISABLED: a taken item stays taken (SAVE-TAKEN-DISABLED-ONE-FLAG-59)
        objects = body(host, 'static int32_t ledger_object(uint32_t ref,int op,int32_t value)')
        self.assertIn('if(!(r->fields&AW_LEDGER_TAKEN))ledger_show(ref);', objects)
        # nothing of the objects goes into the 2,048-entry list: it never fills and refuses the save
        self.assertIn('if(aw_ledger_on)return out->count;', body(host, 'static int objects_export(aw_changes_t *out)'))
        # a map reads only its own rows: its edicts by reference, the rows of its room, scene and of no place
        attach = body(host, 'static void ledger_attach(void)')
        self.assertIn('AW_LedgerFind(&aw_ledger,edict_refs[i].ref)', attach)
        self.assertIn('AW_LedgerPlace(&aw_ledger,kinds[j],places[j],&first)', attach)
        self.assertIn('if(aw_ledger_on){ledger_attach();return;}', body(host, 'static void attach_objects(void)'))
        # the old method stays (DON'T DELETE ANY METHOD): the fixed table and its export are still there
        self.assertIn('static object_t objects[OBJECTS];', host)
        self.assertIn('object_hide(&objects[i])', body(host, 'static void attach_objects(void)'))

    def test_drops_and_placed_items_read_the_list(self):
        inventory = code('aw_inventory.c')
        drop = body(inventory, 'int AW_InventoryDropHere(const aw_inventory_item_t *item,int32_t count)')
        self.assertIn('AW_LedgerDrop(&aw_state,&aw_ledger,item,count,at,where,game,yaw)', drop)
        self.assertIn('inv_trace_support(position,mins,maxs,p)', drop)
        self.assertIn('(chim && !aw_ledger_on)', drop)
        self.assertIn('AW_LedgerPickup(&aw_state,&aw_ledger,map_drops[i].key)', body(inventory, 'int AW_InventoryUse(void)'))
        spawn = body(inventory, 'void AW_InventorySpawn(void)')
        self.assertIn('AW_LedgerAdoptDrops(&aw_state,&aw_ledger)', spawn)
        self.assertIn('ledger_spawn();', body(inventory, 'static void focus_load(void)'))
        self.assertIn('AW_LEDGER_MOVED', body(inventory, 'static int placed_read_key('))
        placed = code('aw_placed.c')
        self.assertIn('if(!strcmp(a,"ledger")){ledger_command();return;}', placed)

    def test_ids_come_from_the_table(self):
        self.assertIn('stable_ref(MASTER, ref[\'number\'])', (ROOT / 'tools/prepare_focus.py').read_text(encoding='utf-8'))
        self.assertIn("stable_ref('Morrowind.esm', ref['number'])",
                      (ROOT / 'tools/prepare_item_models.py').read_text(encoding='utf-8'))
        self.assertTrue(re.search(r'AW_LEDGER_PLAYER 0x40000000U', code('aw_ledger.h')))


if __name__ == '__main__':
    unittest.main()
