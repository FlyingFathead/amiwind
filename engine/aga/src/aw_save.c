/* SPDX-License-Identifier: GPL-2.0-or-later
 * Character folders, bounded slots and two validated generations per slot.
 * Writing the inactive generation never renames or truncates the active one. */
#include "quakedef.h"
#include "aw_save.h"
#include "aw_combat.h"
#include "aw_saved_equipment.h"
#include "aw_region.h"
#include "aw_maps.h"
#include "aw_tryalloc.h"	/* the 256 KB save buffers: malloc would trap on a full machine (SDK-MALLOC-TRAPS-52) */
#include "aw_ledger.h"
#include "aw_jhist.h"	/* the dated journal history, feature 128 (JOURNAL-ORIGINAL-VIEW-59) */
/* CELL-CHANGES-59 slice 7: 1 while a save of other game data is loaded (aw_mwhost.c leaves out what names another
 * build's table rows: the known-topic bits by row); the hooks (aw_mwhost.c binds them; NULL: a save of other game
 * data is refused as before, nothing is migrated) */
int aw_save_migrating;
int (*aw_save_other_ok)(void);
void (*aw_save_ident_refresh)(struct aw_ledger_s *ledger);
long (*aw_save_migrate)(struct aw_ledger_s *ledger,void *dropped);
int (*aw_save_drop_actor_records)(void);
void (*aw_save_notice)(const char *line);
static int pending_other;
#ifdef AMIGA
#include <proto/dos.h>
#else
#include <dirent.h>
#endif
#include <sys/stat.h>
#include <time.h>
#include <errno.h>
static aw_save_t world,pending;
/* The world-state change list of a save (feature 8): written from aw_actors.c's export, read back at a load and
 * handed to its import before the window spawns (static: off the Amiga task stack). */
static aw_changes_t save_changes,pending_changes;
/* a loaded save's world change list (feature 32, CELL-CHANGES-59), handed to the session's list at the load */
static aw_ledger_t pending_ledger;
static aw_jhist_t pending_jhist;
/* the actor record's block (feature 16), one buffer for a save and one for a loaded save */
static unsigned char save_actor_block[AW_SAVE_ACTOR_BYTES],pending_actor_block[AW_SAVE_ACTOR_BYTES];
static int loading,scheduled,content_ready;
static double last_auto,settle;
static byte content_id[32];
static cvar_t autosaves={"aw_autosaves","5",true};
static const char *actor_fields[]={"aw_hello_count","aw_manual_count","aw_hello_done"};
static int make_directory(const char *directory)
{
#ifdef AMIGA
    BPTR lock=CreateDir((char *)directory);
    if(lock){UnLock(lock);return 0;}
    errno=IoErr()==ERROR_OBJECT_EXISTS?EEXIST:EIO;return -1;
#else
    return mkdir(directory,0777);
#endif
}

static int content(void)
{
    FILE *f=NULL;int n,ok;
    if(content_ready)return 1;
    n=COM_FOpenFile("save-content.bin",&f);if(!f)return 0;
    ok=n==32 && fread(content_id,1,32,f)==32;fclose(f);
    content_ready=ok;return ok;
}
static int path(char *out,int capacity,uint32_t profile,int slot,int generation)
{
    int n;
    if(!profile || slot<0 || slot>20 || generation<0 || generation>1)return 0;
    n=snprintf(out,capacity,"%s/saves/p%08lx/%c%02ld%c.aws",com_gamedir,(unsigned long)profile,
               slot<5?'m':'a',(long)(slot<5?slot:slot-4),generation?'b':'a');
    return n>0 && n<capacity;
}
static int read_file_changes(uint32_t profile,int slot,int generation,aw_save_t *state,aw_changes_t *changes);
static int read_file(uint32_t profile,int slot,int generation,aw_save_t *state)
{
    return read_file_changes(profile,slot,generation,state,NULL);
}
/* A save file's bytes in a buffer of its own size (CELL-CHANGES-59: a save with the world change list may be larger
 * than AW_SAVE_BYTES, up to AW_SAVE_MAX_BYTES); NULL when it is larger, unreadable or memory says no. The caller
 * frees it. */
static byte *read_whole(FILE *f,int *size)
{
    /* the same reads as before the list for a save of up to AW_SAVE_BYTES (one fread, one fgetc; no seek: the
     * emulator's disk handler is where CHIM-SEYDA-BALMORA-LOAD-HANG-43 stalls); a larger save grows the buffer */
    unsigned long n=AW_SAVE_BYTES;byte *raw=(byte *)AW_TryMalloc(n),*grown;int extra;
    if(!raw)return NULL;
    *size=(int)fread(raw,1,n,f);
    while(*size==(int)n && !ferror(f) && (extra=fgetc(f))!=EOF){
        if(n*2>AW_SAVE_MAX_BYTES || !(grown=(byte *)AW_TryRealloc(raw,n*2))){free(raw);return NULL;}
        raw=grown;raw[n]=(byte)extra;
        *size=(int)n+1+(int)fread(raw+n+1,1,n-1,f);n*=2;
    }
    if(ferror(f) || *size<12){free(raw);return NULL;}
    return raw;
}
/* CELL-CHANGES-59 slice 7: a save of other game data or another build's tables (its content fingerprint is not this
 * build's) loads, migrated (AW_SaveSpawn), when this build has the reference identity table to check it against
 * (aw_inventory.c AW_PlacedRefs); without the table it is refused as before. */
static int other_content_ok(const aw_save_t *state)
{
    return content() && (!memcmp(state->content,content_id,32) || (aw_save_other_ok && aw_save_other_ok()));
}
static int read_file_changes(uint32_t profile,int slot,int generation,aw_save_t *state,aw_changes_t *changes)
{
    char filename[384];byte *raw;FILE *f;int n=0,ok;
    if(!path(filename,sizeof(filename),profile,slot,generation))return 0;
    f=fopen(filename,"rb");if(!f)return 0;
    raw=read_whole(f,&n);ok=raw!=NULL;
    fclose(f);if(!raw)return 0;
    ok=ok && AW_SaveDecodeChanges(raw,n,state,changes) && state->profile==profile && other_content_ok(state);
    free(raw);return ok;
}
static int newest(uint32_t profile,int slot,aw_save_t *state)
{
    /* both generations' item tables are their own (aw_state.h OWNERSHIP): the one not kept is given back */
    static aw_save_t other;int a=read_file(profile,slot,0,state),b=read_file(profile,slot,1,&other);
    if(b && (!a || other.sequence>state->sequence)){if(a)AW_SaveRelease(state);*state=other;return 1;}
    if(b)AW_SaveRelease(&other);
    return a?0:-1;
}
/* newest() for its facts only (sequence, label, scene): its item table given back at once */
static int newest_info(uint32_t profile,int slot,aw_save_t *state)
{
    int r=newest(profile,slot,state);
    if(r>=0)AW_SaveRelease(state);
    return r;
}
static int scene_id(void){return AW_MapLogicalId(sv.name);}
static uint32_t actor_id(edict_t *e)
{
    eval_t *v=GetEdictFieldValue(e,"aw_ref");
    if(v && v->_float>0)return (uint32_t)v->_float;
    v=GetEdictFieldValue(e,"aw_intro_role");
    return v && v->_float>0?0x800000U+(uint32_t)v->_float:0;
}
/* CELL-CHANGES-59 slice 7: the loaded list of a save of other game data, migrated; and what the load says. */
static void migrate_loaded(void)
{
    aw_ledger_dropped_t d;long n;
    memset(&d,0,sizeof(d));
    n=aw_save_migrate?aw_save_migrate(&aw_ledger,&d):-1;
    aw_ledger_events.migrations++;aw_ledger_events.migrated=d;aw_ledger_events.migrated_all=n>0?(unsigned long)n:0;
}
static void migrate_report(void)
{
    const aw_ledger_events_t *v=&aw_ledger_events;char line[160];
    Con_Printf("This save was made with other game data or another build: %lu changes of things this game no longer has, "
               "or that are now other things, were left out (objects %lu, containers %lu, ranks %lu, dispositions %lu, "
               "script locals %lu, actors %lu, levelled rolls %lu, drops %lu, stolen marks %lu; content files missing %lu); "
               "%lu actor records and dead counts of the other actor table were left out.\n",v->migrated_all,
               v->migrated.objects,v->migrated.containers,v->migrated.ranks,v->migrated.dispositions,v->migrated.locals,
               v->migrated.actors,v->migrated.picks,v->migrated.drops,v->migrated.stolen,v->migrated.files,v->records);
    snprintf(line,sizeof(line),"Save of other game data: %lu changes left out (things no longer in the game).",
             v->migrated_all+v->records);
    if(aw_save_notice)aw_save_notice(line);
}
int (*aw_companion_home)(edict_t *,vec3_t,vec3_t);   /* aw_companion.c */
int (*aw_save_entry_refuse)(const char *scene,const float *position);   /* aw_scene.c, bound in aw_debug.c */
void AW_SaveCapture(void)
{
    int i,j,k,scene;uint32_t ref;edict_t *e;eval_t *v;aw_saved_actor_t *a;
    if(!sv.active || (scene=scene_id())<0)return;
    AW_CombatEquipmentStore();
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);
        if(e->free || strcmp(pr_strings+e->v.classname,"aw_npc"))continue;
        ref=actor_id(e);if(!ref)continue;
        for(j=0;j<world.actor_count;j++)if(world.actors[j].reference==ref && world.actors[j].scene==scene)break;
        if(j==world.actor_count){if(j==AW_SAVE_ACTORS){Con_Printf("Save actor limit reached.\n");return;}world.actor_count++;}
        a=&world.actors[j];a->reference=ref;a->scene=scene;
        VectorCopy(e->v.origin,a->position);VectorCopy(e->v.angles,a->angles);
        if(aw_companion_home)aw_companion_home(e,a->position,a->angles);  /* a picked companion saves at home */
        a->angles[1]=anglemod(a->angles[1]);a->health=e->v.health;
        for(k=0;k<3;k++){
            v=GetEdictFieldValue(e,(char *)actor_fields[k]);
            if(k==0)a->hello_count=v?(int)v->_float:0;
            else if(k==1)a->manual_count=v?(int)v->_float:0;
            else a->hello_done=v?(int)v->_float:0;
        }
    }
}
/* Temporary debug excursions use the same persistent state as normal saves,
 * without touching a profile, manual slot or autosave generation. */
int AW_SaveSnapshot(aw_save_t *snapshot)
{
    edict_t *p;uint32_t equipment;
    if(!snapshot || !sv.active || scene_id()<0 || loading || svs.maxclients!=1 ||
       !svs.clients || !(p=svs.clients[0].edict))return 0;
    if(!AW_SavedEquipmentCapture(&equipment,p,sv.time))return 0;
    AW_SaveCapture();*snapshot=world;snapshot->equipment=equipment;
    snapshot->story=aw_story;snapshot->state=aw_state;snapshot->character=aw_character;
    /* the snapshot's own copy of the item table (aw_state.h OWNERSHIP); the caller gives it back (AW_SaveRelease) */
    if(!AW_ItemsClone(&snapshot->state.items,&aw_state.items))return 0;
    VectorCopy(p->v.origin,snapshot->position);VectorCopy(cl.viewangles,snapshot->angles);
    strcpy(snapshot->scene,sv.name);return 1;
}
void AW_SaveSnapshotRestore(const aw_save_t *snapshot)
{
    aw_items_t items;
    if(!snapshot)return;
    /* the snapshot keeps its table (it may be restored again); the game takes a copy, or keeps its own when memory
     * says no (said so) */
    if(!AW_ItemsClone(&items,&snapshot->state.items)){
        Con_Printf("Snapshot restore: not enough memory for the item table; the items stay as they are.\n");
        items=aw_state.items;
    }else AW_ItemsFree(&aw_state);
    world=*snapshot;aw_story=world.story;aw_state=world.state;aw_character=world.character;
    aw_state.items=items;memset(&world.state.items,0,sizeof(world.state.items));
    loading=scheduled=0;last_auto=realtime;
}
void AW_SaveSpawn(void)
{
    int i,j,k,scene=scene_id();edict_t *e;eval_t *v;uint32_t ref;aw_saved_actor_t *a;
    if(loading){
        if(strcmp(sv.name,pending.scene)){loading=0;Con_Printf("Saved scene could not be loaded.\n");return;}
        /* the loaded save's item table becomes the game's (the old one given back; aw_state.h OWNERSHIP) */
        if(pending.state.items.block!=aw_state.items.block)AW_ItemsFree(&aw_state);
        world=pending;aw_story=world.story;aw_character=world.character;aw_state=world.state;
        memset(&pending.state.items,0,sizeof(pending.state.items));memset(&world.state.items,0,sizeof(world.state.items));
        /* its rows weighed now, at the load (aw_inventory.c: one pass over the item file for many kinds;
         * ENCUMBRANCE-INCOMPLETE-61): the place's area load may already have run for this map */
        if(aw_save_items_loaded)aw_save_items_loaded();
        /* the change list: an old save's actor rows read as "moved + health" entries; aw_actors.c takes the
         * entries it can place (cells) before the window spawns its actors */
        if(!pending_changes.count)AW_SaveFoldActors(&world,&pending_changes);
        if(aw_save_changes_import)aw_save_changes_import(&pending_changes);
        /* the world change list of the save (empty for an older save): the session's from now on; then an older
         * save's object entries and dropped items join it (aw_mwhost.c, aw_inventory.c) */
        AW_LedgerMove(&aw_ledger,&pending_ledger);
        if(aw_save_objects_import)aw_save_objects_import(&pending_changes);
        /* slice 7: a save of other game data: every change of a reference this game no longer has, or that now names
         * another record, is dropped and counted (aw_ledger.h AW_LedgerMigrate), before anything reads the list */
        aw_save_migrating=pending_other;
        if(pending_other)migrate_loaded();
        if(aw_save_actors_import)aw_save_actors_import(pending_changes.actors,pending_changes.actor_bytes);
        /* slice 4: the scripts' globals, quest stages and known topics as saved (an older save: the data's start,
         * its 32-slot journal folded in), after the actor block's topic bits */
        if(aw_save_script_import)aw_save_script_import(&aw_ledger);
        /* the dated journal history as saved; an older save's 32-slot history taken over (JOURNAL-ORIGINAL-VIEW-59) */
        AW_JHistMove(&aw_jhist,&pending_jhist);
        if(!aw_jhist.count)AW_JHistTakeOver(&aw_jhist,&aw_state);
        if(pending_other){
            /* the actor records and dead counts name another build's actor table rows: they go, counted */
            aw_ledger_events.records=aw_save_drop_actor_records?(unsigned long)aw_save_drop_actor_records():0;
            migrate_report();
        }
        aw_save_migrating=pending_other=0;
        AW_BarrierLoad();AW_OpeningSpawn();
    }
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);if(e->free || strcmp(pr_strings+e->v.classname,"aw_npc"))continue;
        ref=actor_id(e);if(!ref)continue;
        for(j=0;j<world.actor_count;j++){
            a=&world.actors[j];if(a->reference!=ref || a->scene!=scene)continue;
            VectorCopy(a->position,e->v.origin);VectorCopy(a->angles,e->v.angles);e->v.health=a->health;
            for(k=0;k<3;k++){
                v=GetEdictFieldValue(e,(char *)actor_fields[k]);
                if(v)v->_float=k==0?a->hello_count:k==1?a->manual_count:a->hello_done;
            }
            /* Restore identity/state, then revalidate feet in the current
             * sub-cell. Persisted source-height errors must not undo settling. */
            AW_NPCFloor(e);SV_LinkEdict(e,false);break;
        }
        if(!AW_RegionContains(e->v.origin))ED_Free(e);
    }
    if(loading){
        e=svs.clients[0].edict;
        VectorCopy(world.position,e->v.origin);VectorCopy(world.position,e->v.oldorigin);
        VectorCopy(world.angles,e->v.angles);VectorCopy(world.angles,cl.viewangles);e->v.fixangle=1;
        VectorCopy(vec3_origin,e->v.velocity);e->v.health=aw_character.current[0];SV_LinkEdict(e,false);
        if(!AW_SavedEquipmentRestore(world.equipment,e,sv.time))
            Con_Printf("Saved equipment unavailable in this scene; hands remain hidden.\n");
        loading=0;scheduled=0;last_auto=realtime;Con_Printf("Game restored: %s.\n",aw_story.name);
    }else AW_SaveSchedule();
}
/* A new game: no saved state, and the world as in the game data (the world change list emptied, CELL-CHANGES-59). */
void AW_SaveReset(void){memset(&world,0,sizeof(world));loading=scheduled=0;last_auto=realtime;AW_LedgerClear(&aw_ledger);AW_JHistClear(&aw_jhist);}
int AW_SaveAllowed(void)
{
    return sv.active && svs.maxclients==1 && aw_story.stage==AW_STAGE_RELEASED && aw_character.valid &&
        svs.clients && svs.clients[0].edict && svs.clients[0].edict->v.health>0 &&
        svs.clients[0].edict->v.movetype==MOVETYPE_WALK &&
        !AW_CharacterActive() && !AW_ReaderActive() && !loading && scene_id()>=0;
}
uint32_t AW_SaveProfile(void){return world.profile;}
int AW_AutosaveCount(void)
{
    int n=(int)autosaves.value;if(n<0)n=0;if(n>16)n=16;return n;
}
void AW_SetAutosaveCount(int n)
{
    if(n<0)n=0;
    if(n>16)n=16;
    Cvar_SetValue(autosaves.name,n);
}
static int make_profile(void)
{
    char directory[384],info[400];uint32_t id;int i,n;FILE *f;
    n=snprintf(directory,sizeof(directory),"%s/saves",com_gamedir);
    if(n<1 || n>=(int)sizeof(directory))return 0;
    if(make_directory(directory)<0 && errno!=EEXIST)return 0;
    if(world.profile)return 1;
#ifdef AMIGA
    {
        struct DateStamp stamp;
        DateStamp(&stamp);
        id=(uint32_t)stamp.ds_Days*86400U+(uint32_t)stamp.ds_Minute*60U+(uint32_t)stamp.ds_Tick/50U;
    }
#else
    id=(uint32_t)time(NULL);
#endif
    if(!id)id=1;
    for(i=0;i<100;i++,id++){
        snprintf(directory,sizeof(directory),"%s/saves/p%08lx",com_gamedir,(unsigned long)id);
        if(make_directory(directory)==0)break;
        if(errno!=EEXIST)return 0;
    }
    if(i==100)return 0;
    world.profile=id;
    /* Advisory browser label only. It is never trusted as saved gameplay data. */
    snprintf(info,sizeof(info),"%s/name.txt",directory);f=fopen(info,"wb");
    if(f){fwrite(aw_story.name,1,strlen(aw_story.name),f);fclose(f);}
    return 1;
}
/* The game as it is now, encoded (AW_SaveWrite's and the recorder's part, GAME-RECORDER-61): the bytes (the caller
 * frees them) and their count in *SIZE; NULL when it cannot be (said why). BUMP: the next generation (a save file);
 * 0 keeps the sequence (the recorder's starting save is no generation of the character's). */
static byte *encode_world(const char *label,int bump,int *size)
{
    byte *raw;int n,capacity;edict_t *p;uint32_t equipment;
    p=svs.clients[0].edict;
    if(!AW_SavedEquipmentCapture(&equipment,p,sv.time)){
        Con_Printf("Save equipment validation failed; previous saves retained.\n");return NULL;
    }
    AW_SaveCapture();world.equipment=equipment;
    world.story=aw_story;world.state=aw_state;world.character=aw_character;world.character.current[0]=p->v.health;
    VectorCopy(p->v.origin,world.position);VectorCopy(cl.viewangles,world.angles);world.angles[1]=anglemod(world.angles[1]);strcpy(world.scene,sv.name);
    memcpy(world.content,content_id,32);
    if(bump){
        if(world.sequence==0xffffffffU)return NULL;
        world.sequence++;
    }
    memset(world.label,0,sizeof(world.label));strcpy(world.label,label);
    /* Keep larger serialized storage off the fixed Amiga task stack. The world change list (CELL-CHANGES-59) adds
     * its own bytes to the buffer: a save is never refused because the list is long. */
    capacity=AW_SAVE_BYTES;
    /* slice 4: the scripts' globals, quest stages and known topics join the list as they are now (aw_mwhost.c) */
    if(aw_save_script_export)aw_save_script_export(&aw_ledger);
    /* slice 7: the record hash of every reference the list names and the content files, so a later build of other
     * game data can tell what still names the same thing (only when there is a list to save) */
    if(AW_LedgerRows(&aw_ledger)>0 && aw_save_ident_refresh)aw_save_ident_refresh(&aw_ledger);
    if(AW_LedgerRows(&aw_ledger)>0){      /* its rows, or its stolen pairs alone (slice 2) */
        int need=AW_LedgerEncode(&aw_ledger,NULL,0);
        if(need<=0 || need>AW_SAVE_MAX_BYTES-AW_SAVE_BYTES-8){
            Con_Printf("Save world change list invalid (%d rows); previous saves retained.\n",aw_ledger.count);return NULL;}
        capacity+=need+8;
    }
    if(aw_jhist.count)capacity+=AW_JHistEncode(&aw_jhist,NULL,0)+8;   /* the dated journal history (feature 128) */
    raw=(byte *)AW_TryMalloc((unsigned long)capacity);
    if(!raw){AW_LedgerRecordsSet(&aw_ledger,NULL,0);
        Con_Printf("Save skipped: not enough free memory for its buffer; previous saves retained.\n");return NULL;}
    save_changes.count=0;save_changes.ledger=&aw_ledger;save_changes.journal=&aw_jhist;
    if((aw_save_changes_export && aw_save_changes_export(&save_changes)<0) ||
       (aw_save_objects_export && aw_save_objects_export(&save_changes)<0)){
        free(raw);Con_Printf("Save change list incomplete; previous saves retained.\n");return NULL;
    }
    save_changes.actors=save_actor_block;save_changes.actor_capacity=AW_SAVE_ACTOR_BYTES;save_changes.actor_bytes=0;
    if(aw_save_actors_export && (save_changes.actor_bytes=aw_save_actors_export(save_actor_block,AW_SAVE_ACTOR_BYTES))<0){
        free(raw);Con_Printf("Save actor records too large; previous saves retained.\n");return NULL;
    }
    n=AW_SaveEncodeChanges(raw,capacity,&world,&save_changes);
    /* world shared the game's item table for the write only (aw_state.h OWNERSHIP) */
    memset(&world.state.items,0,sizeof(world.state.items));
    AW_LedgerRecordsSet(&aw_ledger,NULL,0);   /* slice 6: the actor records' copy is only for this write */
    if(!n){free(raw);Con_Printf("Save state validation failed; previous saves retained.\n");return NULL;}
    *size=n;return raw;
}
int AW_SaveWrite(int slot)
{
    byte *raw;aw_save_t check;char filename[384],label[32];
    FILE *f;int n,side,ok,i;
    if(!AW_SaveAllowed() || slot<0 || slot>20 || !content() || !make_profile()){
        Con_Printf("Save unavailable: complete registration and release first, and check the writable save folder.\n");return 0;
    }
    sprintf(label,slot>=5?"Autosave %ld":slot?"Manual %ld":"Quicksave",(long)(slot>=5?slot-4:slot));
    if(!(raw=encode_world(label,1,&n)))return 0;
    side=newest_info(world.profile,slot,&check);side=side==0?1:0;
    if(!path(filename,sizeof(filename),world.profile,slot,side)){free(raw);return 0;}
    f=fopen(filename,"wb");if(!f){free(raw);return 0;}
    ok=fwrite(raw,1,n,f)==(size_t)n;free(raw);
    if(fflush(f))ok=0;
    if(fclose(f))ok=0;
    if(ok && read_file(world.profile,slot,side,&check)){ok=check.sequence==world.sequence;AW_SaveRelease(&check);}
    else ok=0;
    if(!ok){
        Con_Printf("Save write/readback failed; previous generation retained.\n");return 0;
    }
    /* Retention reduction only follows a successful new autosave. Manual and
     * other character files are never pruned by the autosave quota. */
    if(slot>=5)for(i=AW_AutosaveCount()+5;i<=20;i++){
        if(path(filename,sizeof(filename),world.profile,i,0))remove(filename);
        if(path(filename,sizeof(filename),world.profile,i,1))remove(filename);
    }
    Con_Printf("Saved %s (%ld bytes, generation %lu).\n",label,(long)n,(unsigned long)world.sequence);
    return 1;
}
/* a load's decode targets: the actor block, the world change list and the journal history of the pending load */
static void pending_targets(void)
{
    pending_changes.actors=pending_actor_block;pending_changes.actor_capacity=AW_SAVE_ACTOR_BYTES;
    pending_changes.actor_bytes=0;
    AW_LedgerClear(&pending_ledger);pending_changes.ledger=&pending_ledger;
    AW_JHistClear(&pending_jhist);pending_changes.journal=&pending_jhist;
}
/* the end of a load (AW_SaveRead, AW_SaveLoadBytes): the decoded CANDIDATE (its item table owned; given back on a
 * refusal) becomes the pending load and its scene's map is queued. 1 queued, 2 refused with the refusal screen up, 0
 * refused. */
static int load_decoded(aw_save_t *candidate)
{
    char map[40];
    /* A save in a room or frame marked for more Fast RAM than this start has: nothing is left or loaded, the
     * refusal screen is up and ENTER goes to the main menu (CHIM-32MB-SAVE-ENTRY-48). 2: refused, handled. */
    if(aw_save_entry_refuse && aw_save_entry_refuse(candidate->scene,candidate->position)){AW_SaveRelease(candidate);return 2;}
    if(!AW_RegionSelect(candidate->scene,candidate->position,0)){AW_SaveRelease(candidate);return 0;}
    /* a load still pending (its spawn never came) gives its table back first */
    if(pending.state.items.block!=aw_state.items.block)AW_SaveRelease(&pending);
    pending=*candidate;loading=1;scheduled=0;
    pending_other=memcmp(candidate->content,content_id,32)!=0;    /* slice 7: migrated at the spawn */
    IN_AWClearButtons();key_dest=key_game;
    /* Restore before later console commands can replace the pending scene. */
    snprintf(map,sizeof(map),"map %s\n",candidate->scene);Cbuf_InsertText(map);return 1;
}
/* GAME-RECORDER-61: the recorder's starting save, encoded from the game as it is now (no file, no generation); the
 * character's own profile and sequence in *PROFILE and *SEQUENCE (0 when it has none yet: the bytes then carry 1,
 * which the codec needs, and the load puts the real values back). The caller frees the bytes. */
unsigned char *AW_SaveEncodeNow(int *size,uint32_t *profile,uint32_t *sequence)
{
    byte *raw;uint32_t keep_profile=world.profile,keep_sequence=world.sequence;
    if(!AW_SaveAllowed() || !content()){
        Con_Printf("Recorder: the game cannot be saved here (registration and release first, alive, walking).\n");return NULL;
    }
    *profile=keep_profile;*sequence=keep_sequence;
    if(!world.profile)world.profile=1;
    if(!world.sequence)world.sequence=1;
    raw=encode_world("Recording",0,size);
    world.profile=keep_profile;world.sequence=keep_sequence;
    return raw;
}
/* GAME-RECORDER-61: load a save from bytes in memory (the recorder's starting save), as a load from a slot does, with
 * the character's PROFILE and SEQUENCE as they were when the bytes were taken. Returns as load_decoded. */
int AW_SaveLoadBytes(const unsigned char *raw,int size,uint32_t profile,uint32_t sequence)
{
    static aw_save_t candidate;char map[40];
    pending_targets();
    if(!AW_CharacterLoad() || !content() || !AW_SaveDecodeChanges(raw,size,&candidate,&pending_changes)){
        Con_Printf("Recorder: the recording's save does not decode; current game retained.\n");return 0;
    }
    if(!other_content_ok(&candidate)){
        AW_SaveRelease(&candidate);Con_Printf("Recorder: the recording's save is of other game data; current game retained.\n");return 0;
    }
    if(AW_SceneMapSize(candidate.scene,map,sizeof(map))<124){
        AW_SaveRelease(&candidate);Con_Printf("Recorder: the recording's scene is not in this build; current game retained.\n");return 0;
    }
    candidate.profile=profile;candidate.sequence=sequence;
    return load_decoded(&candidate);
}
/* 1 while a load waits for its map's spawn */
int AW_SaveLoadPending(void){return loading;}
int AW_SaveRead(uint32_t profile,int slot)
{
    aw_save_t candidate,other;char map[40];int n,i,generation;
    pending_targets();
    /* every decoded generation owns its item table (aw_state.h OWNERSHIP): all but the one loaded are given back */
    if(!AW_CharacterLoad() || !content() || (generation=newest(profile,slot,&candidate))<0){
        Con_Printf("No valid compatible save generation; current game retained.\n");return 0;
    }
    AW_SaveRelease(&candidate);
    if(!read_file_changes(profile,slot,generation,&candidate,&pending_changes)){
        Con_Printf("No valid compatible save generation; current game retained.\n");return 0;
    }
    /* The scene's own map, or its CHIM frame map in a pure-CHIM image. */
    n=AW_SceneMapSize(candidate.scene,map,sizeof(map));
    if(n<124){AW_SaveRelease(&candidate);Con_Printf("Saved scene unavailable; current game retained.\n");return 0;}
    /* Loading an older manual save must still produce newer generations than
     * every existing autosave of this character. */
    for(i=0;i<=20;i++)if(newest_info(profile,i,&other)>=0 && other.sequence>candidate.sequence)
        candidate.sequence=other.sequence;
    return load_decoded(&candidate);
}
void AW_SaveSchedule(void){if(aw_story.stage==AW_STAGE_RELEASED){scheduled=1;settle=realtime+3;}}
int AW_PlayerInCombat(void);
static int autosave_safe(void)
{
    edict_t *p;
    if(!AW_SaveAllowed() || cls.state!=ca_connected || cls.signon!=SIGNONS ||
       key_dest!=key_game || sv.paused || AW_ModalWorldFrozen() || AW_LoadingScreen() ||
       AW_PhotoModeActive() || AW_PlayerInCombat())return 0;
    p=svs.clients[0].edict;
    /* Use the same ground/liquid state maintained by Quake's player physics.
     * Being alive is insufficient: a falling or burning save can be lethal
     * on every reload. Keep the previous safe generation in those states. */
    return ((int)p->v.flags&FL_ONGROUND) && p->v.waterlevel<2 &&
        (p->v.waterlevel==0 || p->v.watertype==CONTENTS_WATER) &&
        fabs(p->v.velocity[2])<1;
}
void AW_SaveTick(void)
{
    int n,slot;aw_save_t info;uint32_t oldest=0xffffffffU;
    /* GAME-RECORDER-61: no autosave while the recorder records or plays back: a save changes the change list's
     * tables (the scripts' export) and would happen in one run and not the other; and no disk write during play */
    if(!AW_AutosaveCount() || AW_RecorderActive())return;
    if(!scheduled && realtime-last_auto<300)return;
    if(!autosave_safe()){
        /* Loading/menu time and time spent falling into danger do not count
         * towards the three seconds of settled arrival needed for a save. */
        if(scheduled)settle=realtime+3;
        return;
    }
    if(!scheduled && realtime-last_auto>=300)AW_SaveSchedule();
    if(!scheduled || realtime<settle || AW_SpeechRemaining()>0)return;
    slot=5;
    for(n=5;n<5+AW_AutosaveCount();n++){
        if(!world.profile || newest_info(world.profile,n,&info)<0){slot=n;break;}
        if(info.sequence<oldest){oldest=info.sequence;slot=n;}
    }
    scheduled=0;last_auto=realtime;
    if(!AW_SaveWrite(slot))AW_UISubtitle("","Autosave failed. Previous saves retained.",6);
}
int AW_SaveDescription(uint32_t profile,int slot,char *out,int capacity)
{
    aw_save_t info;
    if(capacity<1)return 0;
    /* Load stable character IDs before AWS1/2/3/4 decoding resolves save IDs. */
    if(!AW_CharacterLoad() || newest_info(profile,slot,&info)<0){out[0]=0;return 0;}
    snprintf(out,capacity,"%s / %s / L%ld%s",info.story.name,info.scene,(long)info.character.level,
             memcmp(info.content,content_id,32)?" / other game data":"");return 1;
}
/* The best state of a slot's two generations: no file, a file that does not decode (damaged, or a format this build
 * cannot read), a save of other game data or another build's content, or a loadable save. */
int AW_SaveSlotState(uint32_t profile,int slot)
{
    char filename[384];byte *raw;FILE *f;int n=0,generation,best=AW_SLOT_EMPTY,state;aw_save_t *info;
    info=(aw_save_t *)AW_TryMalloc(sizeof(aw_save_t));
    if(!info)return AW_SLOT_EMPTY;
    for(generation=0;generation<2;generation++){
        if(!path(filename,sizeof(filename),profile,slot,generation) || !(f=fopen(filename,"rb")))continue;
        raw=read_whole(f,&n);fclose(f);
        if(!raw || !AW_SaveDecodeChanges(raw,n,info,NULL))state=AW_SLOT_UNREADABLE;
        else{
            AW_SaveRelease(info);   /* only its facts are read here */
            if(info->profile!=profile)state=AW_SLOT_UNREADABLE;
            else state=other_content_ok(info)?AW_SLOT_OK:AW_SLOT_OTHER_DATA;   /* slice 7: migrated when it can be */
        }
        free(raw);
        if(state>best)best=state;
    }
    free(info);return best;
}
static int profile_entry(const char *directory,const char *entry,uint32_t *id,char name[32])
{
    char filename[420],*endp;FILE *f;int n,i;unsigned long value;
    if(strlen(entry)!=9 || entry[0]!='p')return 0;
    for(i=1;i<9;i++)if(!((entry[i]>='0' && entry[i]<='9') || (entry[i]>='a' && entry[i]<='f')))return 0;
    value=strtoul(entry+1,&endp,16);if(*endp || !value || value>0xffffffffUL)return 0;
    *id=(uint32_t)value;memset(name,0,32);
    snprintf(filename,sizeof(filename),"%s/%.9s/name.txt",directory,entry);f=fopen(filename,"rb");
    if(f){n=fread(name,1,31,f);name[n]=0;fclose(f);}
    for(i=0;name[i];i++)if((unsigned char)name[i]<32)name[i]=' ';
    if(!name[0])strcpy(name,"Unnamed character");
    return 1;
}
int AW_SaveProfiles(uint32_t *ids,char names[][32],int capacity)
{
    char directory[384];int count=0;
#ifdef AMIGA
    BPTR lock;struct FileInfoBlock info;
#else
    DIR *dir;struct dirent *entry;
#endif
    snprintf(directory,sizeof(directory),"%s/saves",com_gamedir);
#ifdef AMIGA
    lock=Lock(directory,ACCESS_READ);if(!lock)return 0;
    if(Examine(lock,&info))while(count<capacity && ExNext(lock,&info)){
        if(info.fib_DirEntryType>0 && profile_entry(directory,(const char *)info.fib_FileName,&ids[count],names[count]))count++;
    }
    UnLock(lock);
#else
    dir=opendir(directory);if(!dir)return 0;
    while(count<capacity && (entry=readdir(dir))!=NULL){
        if(profile_entry(directory,entry->d_name,&ids[count],names[count]))count++;
    }
    closedir(dir);
#endif
    return count;
}
/* The most recent save of a character (the highest generation of every slot), as the original's
 * "Load your last save" after death (OpenMW StateManager::askLoadRecent); label = its description.
 * Returns the slot or -1. */
int AW_SaveLatest(uint32_t profile,char *label,int capacity)
{
    aw_save_t info;int slot,best=-1;uint32_t sequence=0;
    if(capacity>0)label[0]=0;
    if(!profile || !AW_CharacterLoad())return -1;
    for(slot=0;slot<=20;slot++)if(newest_info(profile,slot,&info)>=0 && (best<0 || info.sequence>sequence)){best=slot;sequence=info.sequence;}
    if(best>=0 && capacity>0)AW_SaveDescription(profile,best,label,capacity);
    return best;
}
static void quicksave(void){   /* without a profile no save is written: say so, as quickload does (QUICKSAVE-NO-PROFILE-SILENT-57) */
    if(!world.profile){Con_Printf("Choose a character in Load game first: no save without one.\n");return;}
    AW_SaveWrite(0);}
/* aw_quickload [PROFILE [SLOT]]: the quicksave of this character; with a profile (its folder's hex number, p0000abcd
 * or 0000abcd) that character's quicksave, or its SLOT (0 quicksave, 1-4 manual, 5-20 autosaves): test sessions load
 * a save another engine wrote (INVENTORY-ORIGINAL-LIMITS-61: the older save formats in game) */
static void quickload(void){
    uint32_t profile=world.profile;int slot=0;const char *p;
    if(Cmd_Argc()>=2){
        p=Cmd_Argv(1);if(*p=='p' || *p=='P')p++;
        profile=(uint32_t)strtoul(p,NULL,16);
        if(Cmd_Argc()>=3)slot=Q_atoi(Cmd_Argv(2));
        if(!profile || slot<0 || slot>20){Con_Printf("aw_quickload [PROFILE [SLOT]]: a profile folder's number, slot 0-20.\n");return;}
    }
    if(profile)AW_SaveRead(profile,slot);else Con_Printf("Choose a character in Load game first.\n");
}
void AW_SaveInit(void)
{
    Cvar_RegisterVariable(&autosaves);Cmd_AddCommand("aw_quicksave",quicksave);Cmd_AddCommand("aw_quickload",quickload);
    aw_save_ledger_rows=AW_LedgerRows;aw_save_ledger_encode=AW_LedgerEncode;aw_save_ledger_decode=AW_LedgerDecode;
    aw_save_journal_encode=AW_JHistEncode;aw_save_journal_decode=AW_JHistDecode;
}
