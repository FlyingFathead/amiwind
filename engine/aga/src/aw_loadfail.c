/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_loadfail.c: a place that cannot be reached or loaded (SCENE-LOAD-FAIL-FALLBACK-67, DBG-TP-NOT-FOUND-BOX-67;
 * before them HEART-CHAMBER-LOAD-HANG-62). Once the player is back where the load started, or still there after a
 * refusal (aw_scene.c AW_SceneLoadFailed / AW_SceneLoadBoxTake), the game's own centred message box names the error
 * (aw_loaderr.c: "Map <name> was not found.", "... was found but could not be loaded." and the reason, the code, "You
 * are in <place>.") with one button, OK. With no place to stay, the main menu and the load menu with the error on its
 * notice line. Here too: what ends a load instead of the game (an allocation that fails, a broken map file, a load
 * that does not finish within aw_load_timeout seconds), the check before anything is left (the map's header and the
 * memory its world needs), the test aid dbg loadfail N [KIND] (aw_load_fail_test, read by host_cmd.c Host_Map_f) and
 * dbg restartgame (DBG-RESTARTGAME-62). Kept apart from aw_scene.c so the host tests that link the scene code need
 * none of the box, menu, error or shutdown paths.
 */
#include "quakedef.h"
#include "aw_save.h"
#include "aw_msgbox.h"
#include "aw_story.h"
#include "aw_state.h"
#include "aw_ledger.h"
#include "aw_character.h"
#include "aw_reset.h"
#include "aw_move.h"
#include "aw_loaderr.h"
#include "aw_maps.h"
#include "aw_region.h"
#include "amiwind_version.h"
#include "chim_version.h"
#include "aw_fastrelease.h"
#ifdef AMIGA
#include <proto/exec.h>
#include <exec/memory.h>
#endif

/* aw_load_fail_test N (a test setting): the next N map loads fail as a room that cannot load does (Host_Error after the
 * running game is left); 1 tests the way back, 2 a way back that fails too. The kind (dbg loadfail N KIND) makes the
 * load fail inside its real path instead: memory (the first Hunk allocation of the load), lump (the map's first
 * section read gets bad data: the brush loader's own check meets it, the error names that lump), hang (the client
 * never connects: the time limit). */
cvar_t aw_load_fail_test={"aw_load_fail_test","0"};
/* The time limit of a map load without progress (the server's spawn, the client's connection and its sign-on steps),
 * in seconds; 0 off. A load past it ends as a failed load ("The load did not finish."). Not saved. */
static cvar_t aw_load_timeout={"aw_load_timeout","120"};
enum {FAIL_ERROR,FAIL_MEMORY,FAIL_LUMP,FAIL_HANG,FAIL_KINDS};
static const char *const fail_names[FAIL_KINDS]={"error","memory","lump","hang"};
static int box_open,fail_kind,hang_armed;
static double progress_at;static int progress_state;
/* dbg loadfail N lump: the read-ahead's copy (aw_stream.c, model.c's aw_load_prefetch_copy) answers the map's next
 * section read with one byte more than asked, which the brush loader refuses as bad data ("Invalid BSP prefetch
 * length") inside the lump it is decoding. Once, then the real copy again (also when the load ends another way). */
extern size_t (*aw_load_prefetch_copy)(const char *,long,byte *,size_t);
static size_t (*prefetch_saved)(const char *,long,byte *,size_t);
static int prefetch_armed;
static void prefetch_restore(void) {
    if(prefetch_armed){aw_load_prefetch_copy=prefetch_saved;prefetch_saved=NULL;prefetch_armed=0;}
}
static size_t prefetch_bad(const char *name,long offset,byte *out,size_t bytes) {
    (void)offset;(void)out;
    prefetch_restore();
    Con_Printf("dbg loadfail: %s reads bad data.\n",name);
    return bytes+1;
}

/* MEMORY-EMERGENCY-PURGE-64: dbg mempurge test armed (the purge, its switch and the test aid below, after the free RAM) */
static int purge_test_armed;
static void purge_test_fail(void);

/* dbg loadfail N KIND: arm the kind inside this load (Host_Map_f); 0 for the plain error (Host_Map_f says it). */
int AW_LoadFailTestArm(void) {
    aw_scene_error_forced=1;   /* AW-RECOVER: this load's error is a test aid's (the state file's errors_forced) */
    if(purge_test_armed)purge_test_fail();   /* dbg mempurge test (Host_Error: does not return) */
    switch(fail_kind){
    case FAIL_MEMORY:aw_hunk_fail_test=1;break;
    case FAIL_LUMP:
        if(!prefetch_armed){prefetch_saved=aw_load_prefetch_copy;aw_load_prefetch_copy=prefetch_bad;prefetch_armed=1;}
        break;
    case FAIL_HANG:hang_armed=1;break;
    default:return 0;
    }
    Con_Printf("dbg loadfail: this load fails inside its own path (%s).\n",fail_names[fail_kind]);
    return 1;
}
int AW_LoadFailTestHang(void) {int h=hang_armed;hang_armed=0;return h;}
/* A record of KIND for the hooks below (the scene fills the map, the place and the command). */
static void cause(aw_loaderr_t *e,int kind) {
    memset(e,0,sizeof(*e));e->kind=kind;e->lump=-1;e->offset=-1;e->file_bytes=-1;e->fast_free=e->chip_free=-1;
}
/* Host_Map_f, a map that did not spawn: not found (its file is not on this disk) or why it did not spawn. */
void AW_LoadFailSpawn(const char *name) {
    aw_loaderr_t e;char path[MAX_QPATH+24];int size;
    size=AW_SceneMapSize(name,path,sizeof(path));
    cause(&e,size<0?(AW_MapId(name)>=0?AW_LOADERR_NOT_ON_DISK:AW_LOADERR_NOT_FOUND):AW_LOADERR_NO_SPAWN);
    Q_strcpy_bounded(e.file,path,sizeof(e.file));e.file_bytes=size;
    if(size>=0)Q_strcpy_bounded(e.detail,aw_spawn_why[0]?aw_spawn_why:"the server did not spawn the map",sizeof(e.detail));
    AW_SceneLoadNote(&e);
}
/* zone.c: an allocation that failed. During a map load it ends that load (the half-loaded map is dropped by the way
 * back's own load, Host_ClearMemory); in play (AW-RECOVER, no error in play ends the game) it is an error in play that
 * the chain takes, the place loaded again (the allocator checks before it changes anything, so leaving from here leaves
 * the zone, the hunk and the cache whole); with no game in play it returns and the allocator stops as before. */
static void alloc_failed_in_play(const char *arena,const char *name,long need,long have) {
    Host_Error("Not enough memory in play: %s %s needs %ld bytes, %ld free",arena,name?name:"?",need,have);
}
static void alloc_failed(const char *arena,const char *name,long need,long have) {
    aw_loaderr_t e;aw_mapfail_t m;
    if(!AW_SceneLoadInFlight()){
        if(AW_SceneInPlay())alloc_failed_in_play(arena,name,need,have);
        return;
    }
    aw_hunk_fail_test=0;prefetch_restore();
    cause(&e,AW_LOADERR_MEMORY);e.need=need;e.have=have<0?0:have;
    Q_strcpy_bounded(e.arena,arena,sizeof(e.arena));
    snprintf(e.detail,sizeof(e.detail),"%s allocation %s of %ld bytes, %ld free",arena,name?name:"?",need,have);
    /* a map decode it stopped: its file named, the loader left as after a finished load (the file closed) */
    if(AW_MapFailure(&m)){Q_strcpy_bounded(e.file,m.file,sizeof(e.file));e.file_bytes=m.bytes;}
    AW_SceneLoadNote(&e);
    Host_Error("Not enough memory for the load: %s %s needs %ld bytes, %ld free",arena,name?name:"?",need,have);
}
/* zone.c aw_fatal_hook, at the fatal path's heap audit (Sys_Error, after the input guard has left): a map decode the
 * fatal error stopped (model.c AW_MapFailure names it and leaves the loader as after a finished load) ends that load,
 * the input guard back first; anything else, and every fatal error outside a load, returns and the game stops as
 * before. A second fatal error inside Host_Error does not match: AW_MapFailure ends the decode it names. */
extern int hunk_size,hunk_low_used,hunk_high_used,host_hunklevel,hunk_tempmark;
static void fatal(void) {
    aw_mapfail_t m;aw_loaderr_t e;int kind;long have;
    if(!AW_SceneLoadInFlight() || !(kind=AW_MapFailure(&m)))return;
    prefetch_restore();
    AW_InputGuardInit();
    if(kind==AW_MAPFAIL_MEMORY){
        have=(long)hunk_size-hunk_low_used-hunk_high_used;
        cause(&e,AW_LOADERR_MEMORY);e.need=m.need;e.have=have<0?0:have;
        Q_strcpy_bounded(e.arena,"hunk",sizeof(e.arena));
    }else{
        cause(&e,AW_LOADERR_BROKEN);e.lump=m.lump;e.offset=m.offset;
        e.broken=kind==AW_MAPFAIL_HEADER?AW_BROKEN_HEADER:kind==AW_MAPFAIL_SHORT?AW_BROKEN_SHORT:
            kind==AW_MAPFAIL_LUMP?AW_BROKEN_LUMP:AW_BROKEN_DATA;
    }
    Q_strcpy_bounded(e.file,m.file,sizeof(e.file));e.file_bytes=m.bytes;Q_strcpy_bounded(e.detail,m.why,sizeof(e.detail));
    AW_SceneLoadNote(&e);
    Host_Error("%s: %s",kind==AW_MAPFAIL_MEMORY?"Not enough memory for the load":"Broken map file",e.detail);
}
/* The machine's free Fast (0) or Chip (1) RAM in bytes for the console block; -1 off the Amiga. */
static long memory_free(int chip) {
#ifdef AMIGA
    return (long)AvailMem(chip?MEMF_CHIP:MEMF_FAST);
#else
    (void)chip;return -1;
#endif
}
/* MEMORY-EMERGENCY-PURGE-64: the emergency purge (aw_scene.c asks it once a scene load failed for lack of memory, the
 * server and the client already down): every releaser of re-makeable session memory (aw_fastrelease.c: the animation
 * tables and posed frames, the cached area tables of the areas left), each with its own console line, then one line of
 * figures. The Quake cache needs no step: it sits in the Hunk's gap and every Hunk allocation takes it back already;
 * the CHIM banks' unlocked blocks are taken back by the zone on demand. aw_mem_purge 0 (dbg mempurge off) switches the
 * purge and its retry off: the load goes straight to the box and the way back. Not saved. */
static cvar_t aw_mem_purge={"aw_mem_purge","1"};
extern void (*chim_room_short)(const char *room,unsigned long need,unsigned long have);   /* chim/chim_world.c */
static int purges;static unsigned long purged_bytes;
static long fast_largest(void) {
#ifdef AMIGA
    return (long)AvailMem(MEMF_FAST|MEMF_LARGEST);
#else
    return -1;
#endif
}
static long kib(long bytes){return bytes<0?-1:bytes/1024;}
static long memory_purge(const char *map) {
    long free_before,largest_before;unsigned long given;
    if(!aw_mem_purge.value){
        Con_Printf("Memory purge: off (dbg mempurge on); %s goes to the box and the way back.\n",map?map:"?");
        return -1;
    }
    free_before=memory_free(0);largest_before=fast_largest();
    given=AW_FastReleaseAll ("the emergency purge");
    purges++;purged_bytes+=given;
    Con_Printf("Memory purge for %s: %lu KiB of re-makeable memory given back by %d releasers; Fast RAM free %ld -> %ld KiB, "
        "largest block %ld -> %ld KiB.\n",map?map:"?",given/1024,AW_FastReleasers(),kib(free_before),kib(memory_free(0)),
        kib(largest_before),kib(fast_largest()));
    return (long)given;
}
/* dbg mempurge test (Host_Map_f, through aw_load_fail_test): this load is short of Fast RAM once, at its start, through
 * the real path (alloc_failed: the load's memory record, Host_Error); the retry after the purge is not short. */
static void purge_test_fail(void) {
    long have=fast_largest();
    if(have<0)have=0;
    purge_test_armed=0;aw_scene_purge_test=1;
    Con_Printf("dbg mempurge test: this load is short of memory on purpose (%s).\n",aw_mem_purge.value?
        "the purge, then the load once more":"the purge is off: the box, then the way back");
    alloc_failed("fast","dbg mempurge test",have+65536L,have);
}
/* A CHIM room whose record or models found no room after every growth step (chim_world.c RefuseRoom): its load ends as
 * not enough memory with the figures (outside a load alloc_failed returns and the refusal stays as it was). */
static void room_short(const char *room,unsigned long need,unsigned long have) {
    alloc_failed("room",room,(long)need,(long)have);
}
static void mem_purge_command(void) {
    const char *w=Cmd_Argc()>=2?Cmd_Argv(1):"";
    if(!Q_strcasecmp((char *)w,"on") || !strcmp(w,"1"))Cvar_SetValue("aw_mem_purge",1);
    else if(!Q_strcasecmp((char *)w,"off") || !strcmp(w,"0"))Cvar_SetValue("aw_mem_purge",0);
    else if(!Q_strcasecmp((char *)w,"test")){
        purge_test_armed=1;Cvar_SetValue("aw_load_fail_test",1);
        Con_Printf("dbg mempurge test: the next map load is short of memory once (%s).\n",aw_mem_purge.value?
            "the purge and one more try load it":"the purge is off: the box, then the way back");
        return;
    }
    else if(w[0]){Con_Printf("dbg mempurge [on / off / test]\n");return;}
    Con_Printf("Memory purge %s: %d purges, %lu KiB given back; %d loads tried once more, %d of them loaded; "
        "Fast RAM free %ld KiB, largest block %ld KiB.\n",aw_mem_purge.value?"on":"off",purges,purged_bytes/1024,
        aw_scene_mem_retries,aw_scene_mem_retry_loads,kib(memory_free(0)),kib(fast_largest()));
}
/* The check before anything is left (aw_scene.c load_scene): the map file's header against its size (a damaged or
 * truncated file), then the bytes its world needs once decoded (model.c AW_BrushBound, from the header alone) against
 * what the Hunk holds for a map (all of it above the start-up's level, less its permanent top). One file open and 124
 * bytes. 1 = refused, E says why. */
extern qboolean hunk_tempactive;
static int precheck(const char *map,aw_loaderr_t *e) {
    char path[MAX_QPATH+24];FILE *f=NULL;unsigned char raw[sizeof(dheader_t)];dheader_t header;
    long size,n,need,have;int lump,broken,i;
    if((size=AW_SceneMapSize(map,path,sizeof(path)))<0)return 0;   /* not on this disk: its callers say so */
    if(COM_FOpenFile(path,&f)<0 || !f)return 0;
    n=(long)fread(raw,1,sizeof(raw),f);fclose(f);
    cause(e,AW_LOADERR_BROKEN);Q_strcpy_bounded(e->file,path,sizeof(e->file));e->file_bytes=size;
    if((broken=AW_LoadErrMapHeader(raw,n,size,&lump))!=0){
        e->broken=broken;e->lump=lump;e->offset=broken==AW_BROKEN_SHORT?size:0;
        Q_strcpy_bounded(e->detail,broken==AW_BROKEN_SHORT?"a lump runs past the end of the file (checked before leaving)":
            "the map header does not read (checked before leaving)",sizeof(e->detail));
        return 1;
    }
    memcpy(&header,raw,sizeof(header));
    for(i=0;i<(int)(sizeof(header)/4);i++)((int *)&header)[i]=LittleLong(((int *)&header)[i]);
    need=AW_BrushBound(&header,0,0);
    have=(long)hunk_size-host_hunklevel-(hunk_tempactive?hunk_tempmark:hunk_high_used);
    if(need>0 && need>have){
        e->kind=AW_LOADERR_MEMORY;e->need=need;e->have=have<0?0:have;Q_strcpy_bounded(e->arena,"map",sizeof(e->arena));
        snprintf(e->detail,sizeof(e->detail),"its world needs %ld bytes decoded, the map memory holds %ld (checked before leaving)",
            need,have);
        return 1;
    }
    return 0;
}
/* The time limit: a map load whose state (the server, the client's connection and sign-on) has not moved for
 * aw_load_timeout seconds ends as a failed load. A long synchronous step is one frame and counts as progress when it
 * moves the state; the limit only fires on a load that sits still while frames run. */
static void timeout_tick(void) {
    aw_loaderr_t e;int state;double now;
    if(!AW_SceneLoadInFlight() || aw_load_timeout.value<=0){progress_at=0;return;}
    now=Sys_FloatTime();state=(sv.active?1:0)|((int)cls.state<<1)|(cls.signon<<4);
    if(!progress_at || state!=progress_state || now<progress_at){progress_at=now;progress_state=state;return;}
    if(now-progress_at<aw_load_timeout.value)return;
    progress_at=0;
    cause(&e,AW_LOADERR_TIMEOUT);
    snprintf(e.detail,sizeof(e.detail),"no progress for %ld s (sign-on %ld, aw_load_timeout)",(long)aw_load_timeout.value,
        (long)cls.signon);
    AW_SceneLoadNote(&e);
    Host_Error("The load did not finish within %ld s",(long)aw_load_timeout.value);
}
static void tick(void) {
    static const char *const buttons[1]={"OK"};int b,want;
    timeout_tick();
    if(prefetch_armed && !AW_SceneLoadInFlight())prefetch_restore();
    if(!box_open && key_dest==key_game && !AW_MsgBoxActive() && !AW_SaveMenuActive() && (want=AW_SceneLoadBoxTake())!=0){
        if(want==2){
            /* no place to stay: the main menu and the load menu over it, the error on its notice line */
            Con_Printf("Failed load: no place to stay; the load menu.\n");
            Cmd_ExecuteString("aw_main_menu",src_command);
            AW_SaveMenuOpen(1);AW_SaveMenuNotice(AW_SceneLoadNoticeText());return;
        }
        box_open=1;AW_MsgBoxShow(AW_SceneLoadBoxText(),buttons,1);return;
    }
    if(box_open && !AW_MsgBoxActive() && (b=AW_MsgBoxPressed())>=0){
        box_open=0;
        Con_Printf("Failed load box: OK\n");
    }
}
static void load_fail_command(void) {
    int i;
    if(Cmd_Argc()>=2 && !Q_strcasecmp(Cmd_Argv(1),"timeout")){
        if(Cmd_Argc()==3)Cvar_SetValue("aw_load_timeout",(float)Q_atoi(Cmd_Argv(2)));
        Con_Printf("dbg loadfail timeout: a map load without progress for %ld s fails (0 = off).\n",(long)aw_load_timeout.value);
        return;
    }
    if(Cmd_Argc()>=2)Cvar_SetValue("aw_load_fail_test",(float)Q_atoi(Cmd_Argv(1)));
    if(Cmd_Argc()>=3){
        for(i=0;i<FAIL_KINDS;i++)if(!Q_strcasecmp(Cmd_Argv(2),(char *)fail_names[i]))break;
        if(i==FAIL_KINDS){Con_Printf("dbg loadfail N [error/memory/lump/hang]\n");return;}
        fail_kind=i;
    }else if(Cmd_Argc()==2)fail_kind=FAIL_ERROR;
    Con_Printf("dbg loadfail: the next %ld map loads fail on purpose (%s; 0 = off).\n",(long)aw_load_fail_test.value,
        fail_names[fail_kind]);
}
/* AW-RECOVER test aid, dbg hosterror script|client|now: an error in play on purpose, where one comes from: inside the
 * next frame's script step (aw_mwhost.c, the step still counted as running, as a script's own error leaves it for the
 * autosave's queue heal), in the screen side's read of the next server message (cl_parse.c), or at once from the
 * console. In a load: dbg loadfail N. Each ends in play again by aw_scene.c's chain, counted as forced. */
extern void (*aw_mwhost_step_error)(void);
extern void (*cl_parse_force_error)(void);
static void forced_script(void) {
    aw_mwhost_step_error=NULL;aw_scene_error_forced=1;
    Host_Error("forced error in a script step (dbg hosterror script)");
}
static void forced_client(void) {
    cl_parse_force_error=NULL;aw_scene_error_forced=1;
    Host_Error("forced error in the client's read of a server message (dbg hosterror client)");
}
static void hosterror_command(void) {
    char *what=Cmd_Argc()>=2?Cmd_Argv(1):"";
    if(!Q_strcasecmp(what,"script")){
        aw_mwhost_step_error=forced_script;Con_Printf("dbg hosterror: the next script step ends in an error on purpose.\n");
    }else if(!Q_strcasecmp(what,"client")){
        cl_parse_force_error=forced_client;
        Con_Printf("dbg hosterror: the next server message the screen side reads ends in an error on purpose.\n");
    }else if(!Q_strcasecmp(what,"now")){
        Con_Printf("dbg hosterror: an error in play now.\n");aw_scene_error_forced=1;
        Host_Error("forced error in play (dbg hosterror now)");
    }else Con_Printf("dbg hosterror script/client/now: an error in play on purpose (dbg loadfail N for one in a load)\n");
}
/* dbg restartgame: the running game ends cleanly (scene loads, the failed-load box, the story, sounds, the map's
 * memory back to the boot level: Host_ClearMemory gives the Hunk back to host_hunklevel and the models, CHIM's banks
 * with the map), then the startup logo and the main menu, as at boot, without quitting; also from a stranded load. */
/* ---- the game-state reset registry's modules (aw_reset.h; NEWGAME-STATE-RESET-62) ----
 * Each line: a module's reset to what a fresh boot has, and a digest of that state. A module with new game state adds
 * its line here (or registers from its own init); docs/GAME_STATE_RESET.md. */
static void reset_story(int new_game){AW_StoryReset(new_game);}     /* the story, aw_state's globals, journal, items */
static unsigned long digest_story(void){
    unsigned long h=AW_ResetHash(AW_RESET_SEED,&aw_story,sizeof(aw_story));int n=AW_ItemCount(&aw_state);
    h=AW_ResetHash(h,aw_state.count,sizeof(aw_state.count));h=AW_ResetHash(h,aw_state.values,sizeof(aw_state.values));
    h=AW_ResetHash(h,&aw_state.journal_count,sizeof(aw_state.journal_count));
    h=AW_ResetHash(h,aw_state.journal,sizeof(aw_state.journal));h=AW_ResetHash(h,&aw_state.harvest,sizeof(aw_state.harvest));
    h=AW_ResetHash(h,&aw_state.inventory,sizeof(aw_state.inventory));h=AW_ResetHash(h,&aw_state.magic,sizeof(aw_state.magic));
    return AW_ResetHash(h,&n,sizeof(n));
}
static void reset_character(int new_game){AW_CharacterReset();}
static void reset_save(int new_game){AW_SaveReset();}               /* the world change list, the journal history */
static unsigned long digest_ledger(void){
    int c[12];
    c[0]=aw_ledger.count;c[1]=aw_ledger.stolen_count;c[2]=aw_ledger.content_count;c[3]=aw_ledger.rank_count;
    c[4]=aw_ledger.fact_count;c[5]=aw_ledger.local_count;c[6]=aw_ledger.script_count;c[7]=aw_ledger.actor_count;
    c[8]=aw_ledger.records_bytes;c[9]=aw_ledger.stamp_count;c[10]=aw_ledger.ident_count;c[11]=aw_ledger.placed;
    return AW_ResetHash(AW_ResetHash(AW_RESET_SEED,c,sizeof(c)),aw_ledger.value_count,sizeof(aw_ledger.value_count));
}
static void reset_scene(int new_game){AW_SceneLoadReset();purge_test_armed=0;}   /* scene loads, the way back, followers */
static void reset_box(int new_game){box_open=0;AW_MsgBoxClear();}
static unsigned long digest_box(void){return (unsigned long)(AW_MsgBoxActive()*2+box_open);}
static void reset_scripts(int new_game){AW_MwscriptNewGameReset();}
/* DBG-NOBURDEN-62: the no-burden debug mode (aw_move.c) is off after New Game, as at boot */
static void reset_noburden(int new_game){(void)new_game;AW_MoveNoBurdenSet(0);}
static unsigned long digest_noburden(void){return (unsigned long)AW_MoveNoBurdenOn();}
/* PLAYER-SNEAK-NOT-HELD-69: the toggled sneak (the sneak key's state, aw_move.c) is off after New Game, as at boot */
static void reset_sneak(int new_game){(void)new_game;AW_MoveSneakSet(0);}
static unsigned long digest_sneak(void){return (unsigned long)AW_MoveSneakOn();}
static void register_resets(void){
    AW_ResetRegister("story and globals",reset_story,digest_story);
    AW_ResetRegister("character",reset_character,NULL);
    AW_ResetRegister("world change list",reset_save,digest_ledger);
    AW_ResetRegister("scene loads",reset_scene,NULL);
    AW_ResetRegister("message boxes",reset_box,digest_box);
    /* the scripts and everything a save load resets: instances, locals, timers, globals, topics, standing and crime,
     * effects, actor packages and records, merchants, made items, gems, faction reactions, revealed places, forced
     * sneak and fade, the session's object state (aw_mwhost.c AW_MwscriptNewGameReset) */
    AW_ResetRegister("scripts and actors",reset_scripts,AW_MwscriptDigest);
    AW_ResetRegister("no burden (dbg noburden)",reset_noburden,digest_noburden);
    AW_ResetRegister("the toggled sneak",reset_sneak,digest_sneak);
}
/* New Game (aw_intro.c aw_game_reset): every registered reset, then the check that every state with a digest is what
 * a New Game from a fresh boot has (AW_ResetMarkBoot at the end of the start-up, host.c). */
static void game_reset(int new_game){
    char differ[256];int n;
    AW_ResetAll(new_game);
    n=AW_ResetCompareBoot(differ,sizeof(differ));
    if(new_game){
        if(n>0)Con_Printf("New Game reset: %d of %d states differ from a fresh boot: %s\n",n,AW_ResetModules(),differ);
        else Con_Printf("New Game reset: %d states, all as at a fresh boot.\n",AW_ResetModules());
    }
}
/* host.c, at the end of the start-up: the digests a New Game must give: every registered reset in its New Game form,
 * in the registry's order (a later reset may set an earlier module's state), marked, then the boot form again. The
 * world change list's reset would also queue the run-once new-game scripts (aw_save_new_game): not here. */
void AW_ResetBootMark(void){
    void (*queue)(void)=aw_save_new_game;
    aw_save_new_game=NULL;
    /* OPENING-VANITY-CAMERA-64: each module marked right after its own reset, not after the whole run (that compared
     * the registry with itself and kept a later module's overwrite of an earlier one in the reference) */
    AW_ResetMarkBootInterleaved(1);AW_ResetAll(0);
    aw_save_new_game=queue;
}
static void restart_command(void) {
    box_open=0;AW_MsgBoxClear();
    game_reset(0);
    CL_Disconnect();
    if(sv.active)Host_ShutdownServer(false);
    S_StopAllSounds(true);
    Host_ClearMemory();
    Con_Printf("Restart: game ended; Hunk %ld bytes low, %ld high.\n",(long)Hunk_LowMark(),(long)Hunk_HighMark());
    AW_MovieRestartLogo();
}
/* dbg ver / dbg version (DBG-VERSION-62): the AmiWind build version, the build's commit and date as the image records
 * them (id1/build-stamp.txt: one line "COMMIT DATE"; an image without it says so), and the CHIM engine version. */
static void version_command(void) {
    FILE *f=NULL;char line[96];int n;
    Con_Printf("AmiWind %s\n",AMIWIND_VERSION);
    line[0]=0;
    if(COM_FOpenFile("build-stamp.txt",&f)>0 && f){
        if(fgets(line,sizeof(line),f)){n=(int)strlen(line);while(n && (line[n-1]=='\n' || line[n-1]=='\r'))line[--n]=0;}
        fclose(f);
    }else if(f)fclose(f);
    Con_Printf("Build: %s\n",line[0]?line:"commit and date not recorded in this image");
    Con_Printf("CHIM engine %s\n",CHIM_VERSION);
}
void AW_LoadFailInit(void) {
    Cmd_AddCommand("aw_version_info",version_command);
    Cvar_RegisterVariable(&aw_load_fail_test);
    Cvar_RegisterVariable(&aw_load_timeout);
    Cmd_AddCommand("aw_load_fail",load_fail_command);
    Cmd_AddCommand("aw_restart_game",restart_command);
    Cmd_AddCommand("aw_host_error",hosterror_command);   /* AW-RECOVER test aid */
    aw_scene_autosave_load=AW_SaveRecoverAutosave;aw_scene_save_drop=AW_SaveLoadDrop;   /* AW-RECOVER: the chain's saves */
    aw_loadfail_tick=tick;
    /* SCENE-LOAD-FAIL-FALLBACK-67: what ends a load instead of the game, the check before leaving, the free RAM */
    aw_alloc_failed=alloc_failed;aw_fatal_hook=fatal;
    aw_load_precheck=precheck;aw_load_memory_free=memory_free;
    /* MEMORY-EMERGENCY-PURGE-64: the emergency purge and its one retry, a room that does not fit named as memory, and
     * dbg mempurge (status, on, off, test) */
    Cvar_RegisterVariable(&aw_mem_purge);
    Cmd_AddCommand("aw_mempurge",mem_purge_command);
    aw_scene_memory_purge=memory_purge;chim_room_short=room_short;
    register_resets();
    aw_game_reset=game_reset;     /* aw_intro.c: New Game resets through the registry */
}
