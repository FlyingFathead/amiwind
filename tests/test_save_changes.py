# SPDX-License-Identifier: GPL-3.0-only
"""The world-state change list in saves (AWS4 feature bit 8; engine aw_save.h, aw_save_codec.c, aw_save.c and
aw_actors.c): native round trips of the codec (tests/aga_save_changes_test.c), the bytes of a save without a change
list pinned to the codec before the change list existed (the dev line 723d6bb9: same input, same SHA-256), and the
engine wiring (aw_actors.c exports and imports the list; island positions; the intro roles under bit 31).
"""
import os
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

# aga_save_changes_test.c's "base" and "rows" saves made with the dev line's codec (723d6bb9, -DPIN_ONLY): a save
# without a change list must stay these bytes
BASE = '4d0b3e9fd087e710fc69fc3a72173ee5f0ba25f40b8338da9eb9d79149ae7c8b'
ROWS = 'd6e53fe2078b453d8a85cbdc154d0da37414be2b47bb9dfb9fd5d0dc397fde53'


class ChangeListCodecTests(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
    @unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
    def test_codec(self):
        from test_aga_native_source import NativeSourceTests
        with tempfile.TemporaryDirectory(prefix='amiwind-save-changes-') as tmp:
            out = Path(tmp) / 'out.txt'
            NativeSourceTests.compile_run(self, 'aga_save_changes_test.c',
                                          [SRC / n for n in ('aw_save_codec.c', 'aw_story.c', 'aw_state.c',
                                                             'aw_inventory.c', 'aw_mapfog.c')],
                                          defines=['AW_INVENTORY_RULES_ONLY'],
                                          cflags=['-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                                                  '-Wno-unused-parameter', '-fsanitize=undefined',
                                                  '-fno-sanitize-recover=all',
                                                  # every allocation counted to the byte (heap_cycles)
                                                  '-Wl,--wrap=malloc,--wrap=calloc,--wrap=realloc,--wrap=free'],
                                          arguments=[str(out)])
            text = out.read_text(encoding='ascii')
            lines = dict(line.split(' ', 1) for line in text.splitlines())
        # the rows line is the 48-byte rows of saves before v0.0.66 (aw_save_rows_form 1): still the same bytes
        self.assertEqual(lines['base'].split()[0], BASE)
        self.assertEqual(lines['rows'].split()[0], ROWS)
        self.assertIn('refusals', lines)
        # MAP-EXPLORED-SAVE-BLOCK-66: the setting's clamp, blocks of 32, 64 and 256 KB, the explored map's section
        # beside a full 64 KB block; SAVE-ACTOR-ROWS-256-66: 2,720 packed rows; the heap the same after every cycle
        for key in ('block', 'blocks', 'explored', 'packed', 'fresh', 'heap'):
            self.assertIn(key, lines, text)
        self.assertIn('section ok', text)
        self.assertIn('packed rows 2720 (2700 greeted NPCs, 20 builder roles)', text)
        print('\n' + text)   # the measured sizes, for the record


class WiringTests(unittest.TestCase):
    def test_engine_wiring(self):
        actors = (SRC / 'aw_actors.c').read_text(encoding='utf-8')
        save = (SRC / 'aw_save.c').read_text(encoding='utf-8')
        self.assertIn('aw_save_changes_export = SaveExport;', actors)
        self.assertIn('aw_save_changes_import = SaveImport;', actors)
        # positions in the change list are island positions (a recentre does not move them)
        self.assertIn('VectorAdd (e->v.origin, d, c->origin);', actors)
        self.assertIn('VectorSubtract (c->origin, d, ent->v.origin);', actors)
        # a load hands the list over before the window spawns, folding an old save's actor rows
        self.assertLess(save.index('AW_SaveFoldActors(&world,&pending_changes)'),
                        save.index('AW_BarrierLoad();AW_OpeningSpawn();'))
        # the buffer is AW_SAVE_BYTES plus the world change list's own bytes (CELL-CHANGES-59)
        self.assertIn('AW_SaveEncodeChanges(raw,capacity,&world,&save_changes)', save)
        self.assertIn('capacity+=need+8;', save)
        # object state (v0.0.51, the scripts' Disable and Lock): merged after the actors' export, read after their
        # import, set by the script host
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        self.assertLess(save.index('aw_save_changes_export(&save_changes)'), save.index('aw_save_objects_export(&save_changes)'))
        self.assertLess(save.index('aw_save_changes_import(&pending_changes)'),
                        save.index('aw_save_objects_import(&pending_changes)'))
        self.assertIn('aw_save_objects_export=objects_export;aw_save_objects_import=objects_import;', host)
        # death stays (no respawn yet), also for an actor a level change spawned again from its map; a load's (or a
        # new map's) changes reach the scene's own actors at the next window tick, after the combat set-up
        self.assertIn('c->dead = c->dead || state == 2;', actors)
        self.assertLess(actors.index('if (apply_pending)\n\t\tApplyLoaded ();'), actors.index('SpawnQueued ();\n\tif (++n % 10)'))

    def test_unload_rows_only_for_actors_whose_state_differs(self):
        # the save contract, rule 2 (14 November 2026): at a place's unload an actor without a change-list row gets one
        # only when dead, in a fight, following, or hurt below its record's base health; the host answers "hurt" from
        # the live record; the block grows before a save is refused; the explored land's bound is a guard above the game
        actors = (SRC / 'aw_actors.c').read_text(encoding='utf-8')
        capture = actors[actors.index('void AW_ActorsCapture (edict_t *e)'):actors.index('void AW_ActorsReset (unsigned reference)')]
        self.assertIn('if (!(c = Change (RefOf (e), 0)))', capture)
        self.assertIn('if (state != 1 && state != 2 && !AW_CompanionEdict (e) &&', capture)
        self.assertIn('aw_actor_hurt_record ((unsigned)RefOf (e), h)', capture)
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        self.assertIn('return a && health<a->dyn_base[0]-0.5f?1:0;', host)
        self.assertIn('aw_actor_hurt_record=actor_hurt_record;', host)
        save = (SRC / 'aw_save.c').read_text(encoding='utf-8')
        self.assertIn('while((save_changes.actor_bytes=aw_save_actors_export(save_changes.actors,block))<0){', save)
        self.assertIn('int grown=block<AW_SAVE_ACTOR_MAX_BYTES?', save)
        fog = (SRC / 'aw_mapfog.h').read_text(encoding='utf-8')
        self.assertIn('#define AW_MAPFOG_MAX 8192', fog)

    def test_item_instances_wired_into_combat_and_equipment(self):
        # SAVE-ITEM-INSTANCES-ONE-PER-KIND-66: a blow's condition goes to the worn copy's own instance, the fighter sheet
        # reads the worn copies' conditions by slot, and a weapon or shield can be equipped when several are carried
        inventory = (SRC / 'aw_inventory.c').read_text(encoding='utf-8')
        self.assertIn('AW_InventorySlotSetCondition(&aw_state,slot,value);', inventory)
        self.assertIn('sheet->weapon_health=item.health*AW_InventorySlotCondition(&aw_state,AW_SLOT_RIGHT);', inventory)
        self.assertIn('rating*=AW_InventorySlotCondition(&aw_state,worn[k].slot);', inventory)
        self.assertIn('sheet->shield_health=item.health*AW_InventorySlotCondition(&aw_state,AW_SLOT_LEFT);', inventory)
        self.assertNotIn('if((count!=1 && !(item->category==AW_INV_WEAPON && item->weapon==12 && count>1))', inventory)
        self.assertIn('s->inventory.equipped_serial[slot]=slot_wear(s,item->id);', inventory)
        codec = (SRC / 'aw_save_codec.c').read_text(encoding='utf-8')
        self.assertIn('(instanced?16384U:0U)', codec)
        self.assertIn("if(!error && data[3]=='4' && (features&16384))instance_fields(&candidate.state);", codec)

    def test_journal_copy_of_256_entries_is_not_a_cap(self):
        # SAVE-STATE-FIXED-CAPS-66: a script's Journal is dated in the history first (no quest or entry limit), and the
        # 32-quest, 256-entry copy of aw_state.h is written afterwards for older readers only, its refusal ignored
        host = (SRC / 'aw_mwhost.c').read_text(encoding='utf-8')
        journal = host[host.index('static void host_journal_set('):host.index('static void host_journal_set(') + 2000]
        self.assertLess(journal.index('AW_JHistJournal(&aw_jhist,'), journal.index('AW_JournalAdd(&aw_state,name,index);'))
        self.assertIn('if(r&AW_JH_RAISE){topic_values[topic]=index;AW_JournalAdd(&aw_state,name,index);}', journal)
        # the loader prefers the dated history; the copy is taken over only when the save has none
        save = (SRC / 'aw_save.c').read_text(encoding='utf-8')
        self.assertIn('AW_JHistMove(&aw_jhist,&pending_jhist);\n        if(!aw_jhist.count)AW_JHistTakeOver(&aw_jhist,&aw_state);', save)

    def test_load_menu_says_why_a_slot_cannot_load(self):
        # AW25-06: absent, unreadable and other-data saves were all "(empty)"; the slot state is read once at the
        # menu's refresh (not every frame) and only for a slot without a loadable save
        menu = (SRC / 'aw_savemenu.c').read_text(encoding='utf-8')
        save = (SRC / 'aw_save.c').read_text(encoding='utf-8')
        self.assertIn('int AW_SaveSlotState(uint32_t profile,int slot)', save)
        for reason in ('" (unreadable)"', '" (other game data or build)"', '" (empty)"'):
            self.assertIn(reason, menu)
        refresh = menu[menu.index('static void refresh(void)'):menu.index('static const char *slot_reason')]
        self.assertIn('AW_SaveSlotState(', refresh)
        draw = menu[menu.index('void AW_SaveMenuDraw(void)'):]
        self.assertNotIn('AW_SaveSlotState(', draw)


if __name__ == '__main__':
    unittest.main()
