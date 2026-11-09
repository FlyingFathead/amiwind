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
        for part in ('rows ok', 'places ok', 'fields ok', 'refusals ok', 'versions ok', 'doors and locks ok', 'done'):
            self.assertIn(part, lines)
        big = next(line for line in lines if line.startswith('big '))
        self.assertTrue(big.startswith('big 20000 rows'), big)
        self.assertTrue(any(line.startswith('drops ') for line in lines))
        # slice 2: the stolen pairs round trip, survive a drop, a pickup and a save, and are given back
        self.assertTrue(any(line.startswith('stolen 3 pairs') for line in lines), lines)
        # slice 3: container deltas (3,000, past any small table) and NPC ranks round trip and save
        self.assertTrue(any(line.startswith('containers 3000 deltas') for line in lines), lines)
        # slice 4: globals, quests, topics, dispositions and named facts at and past the game's full counts
        self.assertTrue(any(line.startswith('script state 512 globals 1024 quests 3000 topics 2673 dispositions 64 facts')
                            for line in lines), lines)
        # slice 5: script locals and running global scripts at the game's counts (7,388 values) and to the ceiling
        self.assertTrue(any(line.startswith('script locals 8188 values 604 scripts') for line in lines), lines)
        # slice 6: actor rows at the game's counts (3,437 actor bases, past the old 2,048 entries) and to the ceiling
        self.assertTrue(any(line.startswith('actors 3437 rows') for line in lines), lines)


class ActorStateWiringTests(unittest.TestCase):
    """CELL-CHANGES-59 slice 6 (ACTOR-STATE-POOL-LIMITS-54): an actor killed or hurt is a row of the one world change
    list, kept across map changes (the window and the rooms read and write it) and through a save and a load; the
    changed actor records go with the list; earlier saves' entries and records are migrated."""

    def test_actor_rows_are_on_the_list(self):
        actors = code('aw_actors.c')
        self.assertNotIn('MAX_CHANGES', actors)
        self.assertIn('typedef aw_ledger_actor_t change_t;', actors)
        self.assertIn('return AW_LedgerActor (&aw_ledger, (uint32_t)ref, make);', body(actors, 'static change_t *Change (float ref, int make)'))
        # killed or hurt and let go: captured into its row (dead, moved, health) when it leaves, read at the next spawn
        release = body(actors, 'static void Release (edict_t *e)')
        self.assertIn('Change (RefOf (e), 1)', release)
        self.assertIn('Capture (e, c);', release)
        self.assertIn('c->dead = 1;', body(actors, 'static void Died (edict_t *e)'))

    def test_save_and_load(self):
        actors = code('aw_actors.c')
        export = body(actors, 'static int SaveExport (aw_changes_t *out)')
        self.assertNotIn('ToEntry (&changes[i]', export)        # the rows go in the list's sixth form, not 2,048 entries
        load = body(actors, 'static void SaveImport (const aw_changes_t *in)')
        self.assertIn('aw_ledger_t *into = in->ledger ? in->ledger : &aw_ledger;', load)
        self.assertIn('AW_LedgerActor (into, e->key, 1)', load)  # an older save's entries migrate onto the list
        save = code('aw_save.c')
        # the session list is the save's after a load: the actor rows the import put in come with it
        self.assertLess(save.index('aw_save_changes_import(&pending_changes);'), save.index('AW_LedgerMove(&aw_ledger,&pending_ledger);'))
        self.assertIn('AW_LedgerRecordsSet(&aw_ledger,NULL,0);   /* slice 6', save)
        host = code('aw_mwhost.c')
        self.assertIn('actor_records_export(l);', body(host, 'static void script_export(aw_ledger_t *l)'))
        self.assertIn('AW_ActorStateImportRecords(l->records,l->records_bytes)', body(host, 'static void script_import(const aw_ledger_t *l){'))
        self.assertIn('AW_ActorStateExportCounts(out,capacity)', body(host, 'static int actors_export(unsigned char *out,int capacity)'))
        # an older save's actor block with records (AWAS1) still loads: migrated into the pool
        self.assertIn('AW_ActorStateImport(data,actors)', host)

    def test_respawn_at_the_cells_load(self):
        # slice 7: a dead actor comes back only by the respawn rules, checked where its cell loads: a joining frame's
        # spawn, a levelled reference's roll (outdoors and in a room), a new map's own actors
        actors = code('aw_actors.c')
        respawned = body(actors, 'static int Respawned (change_t *c)')
        self.assertIn('AW_LedgerActorRespawns (c, (flags & (AW_REFS_RESPAWN | AW_REFS_LEVELLED)) != 0, GameHours (), &rule)',
                      respawned)
        self.assertIn('aw_actors_forget (c->key);', respawned)   # it comes back as the game data has it
        self.assertIn('aw_actors_ref_flags=actors_ref_flags;aw_actors_forget=AW_ActorForget;', code('aw_mwhost.c'))
        self.assertIn('AW_LedgerActorReset (c);', respawned)
        spawn = body(actors, 'static int SpawnOne (pending_t *q)')
        self.assertLess(spawn.index('Respawned (c);'), spawn.index('if (c && c->dead)'))
        join = body(actors, 'static void TableJoin (int cx, int cy, const float *offset)')
        self.assertLess(join.index('Respawned (c);'), join.index('if (c && c->pick)'))
        self.assertIn('Respawned (c);', body(actors, 'static void LevelledEntity (edict_t *ent)'))
        self.assertIn('if (Respawned (c))', body(actors, 'static void ApplyLoaded (void)\n{'))
        # ACTORS-TOWN-ROOM-RETURN-59: the town map entered again from a room applies the list to its own residents
        self.assertIn('tick_map[0] = 0;', body(actors, 'void AW_ActorsRoomTick (void)'))
        self.assertIn('if (strncmp (tick_map, sv.name, sizeof(tick_map) - 1))', body(actors, 'static void Tick (void)'))
        # the time of death: the first time the row is kept dead
        self.assertIn('c->died = GameHours ()', body(actors, 'static void Capture (edict_t *e, change_t *c)'))
        self.assertIn('c->died = GameHours ()', body(actors, 'static void Died (edict_t *e)'))

    def test_fight_stays_behind_a_load_door(self):
        # ROOM-CREATURES-NO-AGGRO-62, the original's rule: a hostile actor never follows the player through a load
        # door; it stays hostile and fights again when the player comes back. Only followers and escorts go through.
        actors = code('aw_actors.c')
        room = body(actors, 'void AW_ActorsRoomTick (void)')
        # a fighter in a room is captured every tick (the room's map goes without a leave), as outdoors
        self.assertIn('(((int)sv.time * 2 + i) % 64 && AW_CombatSlotState (e, NULL) == 0)', room)
        self.assertIn('if (IsActor (e) && AW_CombatSlotState (e, NULL) != 0)', body(actors, 'static void Tick (void)'))
        self.assertIn('c->fight = state == 1;', body(actors, 'static void Capture (edict_t *e, change_t *c)'))
        # coming back: the row's fight is taken up again with the health it had
        self.assertIn('else if (c->fight && AW_CombatTestEngage (e, 0))', body(actors, 'static void ApplyLoaded (void)\n{'))
        # never through the door: the followers handed to the door are AIFollow ones, a fighting one is left
        followers = body(code('aw_ambient.c'), 'int AW_AmbientFollowersOf(edict_t *p,edict_t **out,int max) {')
        self.assertIn('(s->travel!=3 && s->travel!=4)', followers)
        self.assertIn('if(AW_CombatSlotState(s->e,NULL))continue;', followers)


class ScriptLocalsWiringTests(unittest.TestCase):
    """CELL-CHANGES-59 slice 5: every object's script locals and the running global scripts reach the one world change
    list at a save and come back at a load (MWSCRIPT-STATE-NOT-SAVED-48)."""

    def test_export_and_import(self):
        host = code('aw_mwhost.c')
        self.assertIn('locals_export(l);', body(host, 'static void script_export(aw_ledger_t *l)'))
        self.assertIn('locals_import(l);', body(host, 'static void script_import(const aw_ledger_t *l){'))
        put = body(host, 'static void locals_put(')
        self.assertIn('if(!cells[i].i)continue;', put)                        # only what differs from the start
        self.assertIn('running!=AW_MwvmStartsAtLoad(script)', put)           # running state only when it changed
        imp = body(host, 'static void locals_import(const aw_ledger_t *l){')
        self.assertLess(imp.index('AW_MwvmLocalsReset();'), imp.index('AW_MwvmLocalSet('))
        self.assertIn('AW_MwvmGlobalScriptSet(s,x->running)', imp)
        # a script by its name hash, its row only a hint checked against the name
        self.assertIn('return script_hash(hint)==hash?hint:-1;', host)
        self.assertIn('AW_RESIDENT_GROWS("script name hashes met (CELL-CHANGES-59)",SCRIPT_NAMES,8);', host)

    def test_the_fifth_form_only_when_needed(self):
        ledger = code('aw_ledger.c')
        self.assertIn('if(slice5(l))form=5;', ledger)
        self.assertIn('(form==4 && !(any+k))', ledger)                       # a fifth form may have empty slice 4 parts
        self.assertIn('AW_RESIDENT_GROWS("script locals (CELL-CHANGES-59)",AW_LEDGER_LOCALS_MAX,', ledger)
        self.assertNotRegex(ledger, r'static\s+aw_ledger_local_t\s+\w+\s*\[')

    def test_the_parking_store_holds_a_whole_game(self):
        # the game places 2,115 references whose script has locals, 7,388 values (v0.0.59-dev5's compiled scripts)
        header = code('aw_mwvm.h')
        parked = int(re.search(r'#define AW_MWVM_PARKED (\d+)', header).group(1))
        cells = int(re.search(r'#define AW_MWVM_PARK_CELLS (\d+)', header).group(1))
        self.assertGreaterEqual(parked, 2115)
        self.assertGreaterEqual(cells, 7388)
        self.assertLessEqual(cells, 0xFFFF)                                  # parked_t.at is 16 bits


class ScriptStateWiringTests(unittest.TestCase):
    """CELL-CHANGES-59 slice 4: the MWScript host's Journal / SetJournalIndex / GetJournalIndex, the globals' Set and
    Get, AddTopic and ModDisposition / SetDisposition reach the one world change list and the save."""

    def test_save_and_load_carry_the_script_tables(self):
        save = code('aw_save.c')
        self.assertLess(save.index('aw_save_script_export(&aw_ledger);'), save.index('AW_LedgerEncode(&aw_ledger,NULL,0)'))
        self.assertLess(save.index('aw_save_actors_import(pending_changes.actors'),
                        save.index('aw_save_script_import(&aw_ledger);'))
        host = code('aw_mwhost.c')
        self.assertIn('aw_state_fact_get=fact_get;aw_state_fact_set=fact_set;', host)
        self.assertIn('aw_save_script_export=script_export;aw_save_script_import=script_import;', host)
        self.assertIn('script_import(&aw_ledger);', body(host, 'static int load(void)'))

    def test_journal_globals_topics(self):
        host = code('aw_mwhost.c')
        export = body(host, 'static void script_export(aw_ledger_t *l)')
        # every quest's stage (GetJournalIndex = host_journal_get, after Journal / SetJournalIndex), no 32 ceiling
        self.assertIn('host_journal_get(i)', export)
        self.assertIn('AW_LEDGER_QUESTS', export)
        # globals only when they differ from the data's start, by the record id's name hash
        self.assertIn('if(now==AW_MwvmGlobalStart(g))continue;', export)
        self.assertIn('AW_LedgerNameHash(global_names+global_offsets[g])', export)
        # topics by name hash (AddTopic sets the bit)
        self.assertIn('AW_LEDGER_TOPICS,h[i],1', export)
        # the topic names' hashes are read from disk once and kept, never at every save
        self.assertIn('if(topic_hash_cache && topic_hash_rows==topic_rows)return topic_hash_cache;', host)
        imp = body(host, 'static void script_import(const aw_ledger_t *l){')
        self.assertIn('AW_MwvmGlobalSetBits(g,bits);', imp)
        # the old 32-slot journal is migrated on load
        self.assertIn('if(story>topic_values[i])topic_values[i]=story;', imp)
        self.assertIn('AW_MwscriptTopicLearn(i)', imp)
        # the globals' names come from one table (the clash of two global_names layouts is gone)
        self.assertEqual(host.count('static char *global_names;'), 1)

    def test_disposition_on_the_list(self):
        host = code('aw_mwhost.c')
        self.assertIn('if(stat==AWA_DISPOSITION)disposition_keep(a);', body(host, 'static aw_mwcell_t host_actor('))
        self.assertIn('disposition_keep(a);', body(host, 'void AW_MwscriptSetSpeaker('))
        self.assertIn('disposition_restore(AW_ActorGet(ref,row,1))', host)
        self.assertIn('disposition_kept(reference,f->base)', body(host, 'void AW_MwscriptDispositionNow('))

    def test_state_table_overflow(self):
        state = code('aw_state.c')
        self.assertIn('return aw_state_fact_set(name,value);', body(state, 'int AW_StateSet('))
        self.assertIn('aw_state_fact_get(name,&fact)', body(state, 'int32_t AW_StateGet('))


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
        # bit 64: the levelling (LEVEL-UP-58), 128: the dated journal, 256: up to 128 kinds of item (COLLECT-CAPACITY-
        # REJECTED-60), 512: any number of kinds (INVENTORY-ORIGINAL-LIMITS-61), 1024: the skill books read
        # (SKILL-BOOKS-MISSING-62)
        self.assertIn('if(features>2047)error=1;', codec)

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
        # DROP-ROOM-BRUSH-ENTITY-59 (v0.0.63): an uneven room floor never refuses the drop: only the centre needs
        # ground, and a failed spot ahead falls back to the floor under the player (OpenMW dropObjectOnGround)
        self.assertIn('!inv_feet_drop(p,mins,maxs,position)', drop)
        support = body(inventory, 'static int inv_trace_support(')
        self.assertNotIn('corner', support)
        self.assertIn('SV_Move(start,vec3_origin,vec3_origin,end,MOVE_NORMAL,p)', body(inventory, 'static int inv_feet_drop('))
        self.assertIn('(chim && !aw_ledger_on)', drop)
        self.assertIn('AW_LedgerPickup(&aw_state,&aw_ledger,map_drops[i].key)', body(inventory, 'int AW_InventoryUse(void)'))
        spawn = body(inventory, 'void AW_InventorySpawn(void)')
        self.assertIn('AW_LedgerAdoptDrops(&aw_state,&aw_ledger)', spawn)
        self.assertIn('ledger_spawn();', body(inventory, 'static void focus_load(void)'))
        self.assertIn('AW_LEDGER_MOVED', body(inventory, 'static int placed_read_key('))
        placed = code('aw_placed.c')
        self.assertIn('if(!strcmp(a,"ledger")){ledger_command();return;}', placed)

    def test_slice2_doors_locks_and_the_stolen_mark(self):
        """Slice 2: door poses, the player's and the console's lock changes, the stolen pairs: all on the one list."""
        header = code('aw_ledger.h')
        self.assertIn('#define AW_LEDGER_OPEN 0x80U', header)
        self.assertIn('#define AW_LEDGER_FIELDS1 0x7FU', header)
        ledger = code('aw_ledger.c')
        # the second form only when it carries something the first cannot: an older reader keeps loading the rest
        self.assertIn('form=l->stolen_count?2:1;', ledger)
        self.assertIn('AW_RESIDENT_GROWS("stolen items by owner (CELL-CHANGES-59)",AW_LEDGER_STOLEN_MAX,', ledger)
        self.assertNotRegex(ledger, r'static\s+aw_ledger_stolen_t\s+\w+\s*\[')
        host = code('aw_mwhost.c')
        door = body(host, 'static int door_open(unsigned reference,int set)')
        self.assertIn('AW_LEDGER_OPEN', door)
        self.assertIn('if(!aw_ledger_on', door)               # the old method keeps no door pose
        # the key and the console go the scripts' way, so their lock is kept and saved the same way
        self.assertIn('object_op(reference,lock?AWM_LOCK:AWM_UNLOCK,lock?level:0);',
                      body(host, 'int AW_ObjectLock(unsigned reference,int lock,int level)'))
        self.assertIn('aw_object_lock=AW_ObjectLock;aw_door_open=door_open;', host)
        hinged = code('aw_hinged_door.c')
        self.assertIn('if(aw_door_open)aw_door_open(d->ref,d->dir>0);', body(hinged, 'static int use_door(hd_door_t *d,int force){'))
        self.assertIn('if(aw_object_lock)aw_object_lock(reference,0,0);', body(hinged, 'static int lock_pass(unsigned reference)'))
        self.assertIn('!saved_open(d->ref)', body(hinged, 'void AW_HingedDoorSpawn(void)'))
        self.assertIn('if(saved_open(reference))', body(hinged, 'int AW_HingedDoorPlacement('))
        # the census hall door's story pose is folded in: the list or the story (an older save) opens it
        self.assertIn('story(reference,AW_HINGE_STORY_SPAWN)==1', body(hinged, 'static int saved_open(unsigned reference)'))
        inventory = code('aw_inventory.c')
        take = body(inventory, 'static int take_row(focus_row_t *row)')
        self.assertIn('AW_LedgerStolenAdd(&aw_ledger,item.id,owner,faction,1)', take)
        # STEAL-WITNESSED-NO-CRIME-61: the owned take is the stolen pair and the crime (one owner lookup for both)
        self.assertIn('stolen=row->owned && container_owner(row->reference,owner,&faction);', take)
        self.assertIn('if(stolen && aw_ledger_on)AW_LedgerStolenAdd', take)
        # a save is written when the list has rows or stolen pairs alone
        self.assertIn('if(AW_LedgerRows(&aw_ledger)>0)', code('aw_save.c'))

    def test_slice3_containers_and_npc_ranks(self):
        """Slice 3: container deltas and NPC ranks on the one list; the scripts, the console and the dialogue use it."""
        ledger = code('aw_ledger.c')
        self.assertIn('if(l->content_count || l->rank_count)form=3;', ledger)
        self.assertIn('AW_RESIDENT_GROWS("container deltas (CELL-CHANGES-59)",AW_LEDGER_CONTENTS_MAX,', ledger)
        self.assertNotRegex(ledger, r'static\s+aw_ledger_content_t\s+\w+\s*\[')
        host = code('aw_mwhost.c')
        item = body(host, 'static int32_t host_item(int instance,int target,int verb,int item,int32_t count)')
        self.assertIn('AW_ContainerChange(ref,id,verb==1?count:-count,0)', item)
        self.assertIn('AW_ContainerCount(ref,id)', item)
        rank = body(host, 'static int npc_rank_change(aw_actor_t *a,int raise)')
        self.assertIn('AW_LedgerRankSet(&aw_ledger,a->reference,rank)', rank)
        self.assertIn('else if(now==0)return -1;', rank)          # LowerRank stops at 0 (OpenMW)
        self.assertIn('case AWF_RAISERANK:case AWF_LOWERRANK:', host)
        self.assertIn('(kept=AW_MwscriptNpcRank(e))>=0)c->rank=kept;', code('aw_glut.c'))
        inventory = code('aw_inventory.c')
        change = body(inventory, 'int AW_ContainerChange(unsigned reference,const char *id,int count,int owner_mark)')
        self.assertIn('AW_LedgerContentAdd(&aw_ledger,reference,id,count);', change)
        self.assertIn('AW_LedgerStolenAdd(&aw_ledger,id,owner,faction,-count)', change)
        self.assertIn('if(!strcmp(a,"container")){AW_ContainerCommand();return;}', code('aw_placed.c'))

    def test_ids_come_from_the_table(self):
        self.assertIn('stable_ref(MASTER, ref[\'number\'])', (ROOT / 'tools/prepare_focus.py').read_text(encoding='utf-8'))
        self.assertIn("stable_ref('Morrowind.esm', ref['number'])",
                      (ROOT / 'tools/prepare_item_models.py').read_text(encoding='utf-8'))
        self.assertTrue(re.search(r'AW_LEDGER_PLAYER 0x40000000U', code('aw_ledger.h')))


def _sub(tag, data):
    import struct
    return tag.encode() + struct.pack('<I', len(data)) + data


def _rec(tag, *subs):
    import struct
    body_ = b''.join(subs)
    return tag.encode() + struct.pack('<III', len(body_), 0, 0) + body_


def _z(text):
    return text.encode('cp1252') + b'\0'


def _ref(number, ident):
    import struct
    return (_sub('FRMR', struct.pack('<I', number)) + _sub('NAME', _z(ident)) +
            _sub('DATA', struct.pack('<6f', 0, 0, 0, 0, 0, 0)))


def _master(refs, months=4):
    """A hand-made master: GMSTs, a respawning and a plain container, a respawning creature, a plain NPC, a levelled
    creature list, and one exterior cell holding REFS [(number, record id)]."""
    import struct
    flag = lambda v: _sub('FLAG', struct.pack('<I', v))
    return b''.join([
        _rec('GMST', _sub('NAME', _z('iMonthsToRespawn')), _sub('INTV', struct.pack('<i', months))),
        _rec('GMST', _sub('NAME', _z('fCorpseRespawnDelay')), _sub('FLTV', struct.pack('<f', 72))),
        _rec('GMST', _sub('NAME', _z('fCorpseClearDelay')), _sub('FLTV', struct.pack('<f', 48))),
        _rec('CONT', _sub('NAME', _z('flora_kreshweed')), _sub('FNAM', _z('Kresh')), flag(1 | 2)),
        _rec('CONT', _sub('NAME', _z('com_chest')), _sub('FNAM', _z('Chest')), flag(8)),
        _rec('CREA', _sub('NAME', _z('rat_respawn')), flag(2)),
        _rec('NPC_', _sub('NAME', _z('guard')), _sub('FNAM', _z('Guard')), flag(0)),
        _rec('NPC_', _sub('NAME', _z('fisher')), _sub('FNAM', _z('Fisher')), flag(4)),
        _rec('LEVC', _sub('NAME', _z('ex_mudcrab_lev'))),
        _rec('CELL', _sub('NAME', _z('')), _sub('DATA', struct.pack('<Iii', 0, -2, -9)),
             *[_ref(n, ident) for n, ident in refs]),
    ])


OLD = [(1, 'flora_kreshweed'), (2, 'com_chest'), (3, 'rat_respawn'), (4, 'guard'), (5, 'fisher'),
       (6, 'ex_mudcrab_lev'), (7, 'com_chest'), (8, 'guard')]
# the content changed: reference 3 removed, 5 now names another record, 9 added
NEW = [(1, 'flora_kreshweed'), (2, 'com_chest'), (4, 'guard'), (5, 'guard'), (6, 'ex_mudcrab_lev'),
       (7, 'com_chest'), (8, 'guard'), (9, 'fisher')]


class RespawnAndMigrationTests(unittest.TestCase):
    """CELL-CHANGES-59 slice 7: the builder's reference identity table (focus.awf AWI1: every placed reference's record
    hash and respawn flags, the master's respawn GMSTs) and the engine's respawn and migration wiring; with the table of
    a changed content list, a save made with the old one loads with exactly the changed references' changes dropped."""

    def test_identity_table_flags_and_settings(self):
        import struct
        import prepare_focus as focus
        raw, rows, respawn = focus.reference_table(_master(OLD), 'ab' * 32)
        self.assertEqual((rows, respawn), (8, (4, 72.0, 48.0)))
        self.assertEqual(raw[:4], b'AWI1')
        n, index, length = struct.unpack_from('<BBB', raw, 4)
        self.assertEqual((n, index, raw[7:7 + length]), (1, 0, b'Morrowind.esm'))
        at = 7 + length
        refs, digest = struct.unpack_from('<I8s', raw, at)
        self.assertEqual((refs, digest), (8, bytes.fromhex('ab' * 8)))
        months, rd, cd, count, step, blocks = struct.unpack_from('<iffIII', raw, at + 12)
        self.assertEqual((months, rd, cd, count, step, blocks), (4, 72.0, 48.0, 8, focus.REFS_STEP, 1))
        at += 12 + 24 + 4 * blocks
        table = [struct.unpack_from('<II', raw, at + 8 * i) for i in range(count)]
        self.assertEqual(len(raw), at + 8 * count)
        keys = {k & 0xFFFFFF: (k >> 24, h) for k, h in table}
        self.assertEqual(sorted(keys), list(range(1, 9)))
        # respawn: the container flagged 2, the creature flagged 2, the NPC flagged 4; levelled: the list
        self.assertEqual({k: f for k, (f, _) in keys.items() if f},
                         {1: focus.REFS_RESPAWN, 3: focus.REFS_RESPAWN, 5: focus.REFS_RESPAWN, 6: focus.REFS_LEVELLED})
        self.assertEqual(keys[2][1], keys[7][1])                         # the same record, the same hash
        self.assertEqual(keys[2][1], focus.name_hash('COM_Chest'))       # folded like the engine's AW_LedgerNameHash
        # absent GMSTs: Morrowind.esm's own values
        self.assertEqual(focus.respawn_settings(_rec('CELL')), (4, 72.0, 72.0))

    def test_the_table_is_after_the_contents_list(self):
        source = (ROOT / 'tools/prepare_focus.py').read_text(encoding='utf-8')
        # CONTAINER-LEVELLED-CONTENTS-60: the builder-only levelled lists follow the identity table
        self.assertIn('contents_list(containers) + identities + levelled_section(levelled))', source)
        inventory = code('aw_inventory.c')
        refs = body(inventory, 'aw_refs_t *AW_PlacedRefs(void){')
        self.assertLess(refs.index('"AWC1"'), refs.index('AW_RefsOpen(&refs,refs_read,NULL,at-base,end-base)'))
        # each place read is a place loaded: its respawning containers refill when due (OpenMW CellStore::respawn)
        respawn = body(inventory, 'static void focus_respawn(unsigned long key,int first,int last){')
        self.assertIn('AW_LedgerRespawnPlace(&aw_ledger,at,where,AW_LedgerGameHours(),r->respawn.months)', respawn)
        self.assertIn('(flags&AW_REFS_RESPAWN)', respawn)
        self.assertIn('AW_LedgerContentDrop(&aw_ledger,focus_rows[i].reference)', respawn)
        self.assertIn('focus_respawn(key,was,focus_count);', body(inventory, 'static void focus_load(void){'))

    def test_save_keeps_identity_and_a_save_of_other_data_is_migrated(self):
        save = code('aw_save.c')
        # the save's encoding (AW_SaveWrite's and the recorder's, GAME-RECORDER-61)
        write = body(save, 'static byte *encode_world(const char *label,int bump,int *size)')
        self.assertLess(write.index('aw_save_ident_refresh(&aw_ledger)'), write.index('AW_LedgerEncode(&aw_ledger,NULL,0)'))
        spawn = body(save, 'void AW_SaveSpawn(void)')
        # migrated before anything reads the list; the other actor table's records and dead counts go
        self.assertLess(spawn.index('if(pending_other)migrate_loaded();'), spawn.index('aw_save_actors_import('))
        self.assertLess(spawn.index('aw_save_script_import(&aw_ledger);'), spawn.index('aw_save_drop_actor_records()'))
        self.assertIn('migrate_report();', spawn)
        # without the identity table here a save of other game data is refused as before
        self.assertIn('(aw_save_other_ok && aw_save_other_ok())', save)
        self.assertIn('aw_save_migrate=save_migrate;', code('aw_mwhost.c'))
        self.assertIn('if(aw_save_migrating)', code('aw_mwhost.c'))   # the topic bits by row are left out

    @unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
    @unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
    def test_changed_content_list(self):
        """Two builds' tables from two masters: a save of the old one migrated against the new one."""
        import prepare_focus as focus
        from test_aga_native_source import NativeSourceTests
        with tempfile.TemporaryDirectory(prefix='amiwind-ledger-migrate-') as tmp:
            old, new, out = Path(tmp) / 'old.awf', Path(tmp) / 'new.awf', Path(tmp) / 'out.txt'
            old.write_bytes(b'AWF3....' + focus.reference_table(_master(OLD), '11' * 32)[0])
            new.write_bytes(b'AWF3....' + focus.reference_table(_master(NEW), '22' * 32)[0])
            NativeSourceTests.compile_run(self, 'aga_world_ledger_test.c',
                                          [SRC / n for n in ('aw_ledger.c', 'aw_ledger_drops.c', 'aw_save_codec.c',
                                                             'aw_story.c', 'aw_state.c', 'aw_inventory.c')],
                                          defines=['AW_INVENTORY_RULES_ONLY'],
                                          cflags=['-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                                                  '-Wno-unused-parameter', '-fsanitize=undefined,address',
                                                  '-fno-sanitize-recover=all'],
                                          arguments=[str(out), str(old), str(new)])
            lines = out.read_text(encoding='ascii').splitlines()
        # 3 is gone and 5 names another record: their taken rows, their container deltas and (both among the first
        # ten) their dead actors are dropped; the six others stay, each with this game's record hash
        self.assertIn('host old 8 new 8: migrated 6 dropped, objects 2 containers 2 actors 2 files 0; kept 6 rows, '
                      '6 idents', lines)
        self.assertIn('done', lines)

    def test_native_migration_counts(self):
        ledger = code('aw_ledger.c')
        self.assertIn('if(slice7(l))form=7;', ledger)
        self.assertIn('return !AW_LedgerIdent(m->saved,key,&saved) || saved==record;', ledger)
        self.assertIn('AW_RESIDENT_GROWS("places\' container refill times (CELL-CHANGES-59 slice 7)",AW_LEDGER_STAMPS_MAX,',
                      ledger)


class RespawnNativeLineTests(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt', 'native fixtures run on Linux, including the Docker gate')
    @unittest.skipUnless(shutil.which('cc'), 'a C compiler is required')
    def test_migration_line(self):
        from test_aga_native_source import NativeSourceTests
        with tempfile.TemporaryDirectory(prefix='amiwind-world-ledger7-') as tmp:
            out = Path(tmp) / 'out.txt'
            NativeSourceTests.compile_run(self, 'aga_world_ledger_test.c',
                                          [SRC / n for n in ('aw_ledger.c', 'aw_ledger_drops.c', 'aw_save_codec.c',
                                                             'aw_story.c', 'aw_state.c', 'aw_inventory.c')],
                                          defines=['AW_INVENTORY_RULES_ONLY'],
                                          cflags=['-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                                                  '-Wno-unused-parameter'],
                                          arguments=[str(out)])
            lines = out.read_text(encoding='ascii').splitlines()
        # the save's changes of references gone, changed, or of a missing content file: dropped and counted
        self.assertIn('migration: 12 dropped (objects 3, drops 1, containers 2, ranks 1, dispositions 1, locals 1, '
                      'actors 1, rolls 1, stolen 1, files 1), 3 rows kept', lines)


if __name__ == '__main__':
    unittest.main()
