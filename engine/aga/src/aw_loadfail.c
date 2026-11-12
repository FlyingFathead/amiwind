/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_loadfail.c: after a failed load (HEART-CHAMBER-LOAD-HANG-62), the game's own message box once the player is back
 * where the load started (aw_scene.c AW_SceneLoadFailed / AW_SceneLoadBoxTake): "OK" stays, "Load Game" opens the
 * load menu; when there was no way back, the load menu at once. The test aid dbg loadfail N (aw_load_fail_test, read
 * by host_cmd.c Host_Map_f) and dbg restartgame (DBG-RESTARTGAME-62). Kept apart from aw_scene.c so the host tests
 * that link the scene code need none of the box, menu or shutdown paths.
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
#include "amiwind_version.h"
#include "chim_version.h"

/* aw_load_fail_test N (a test setting): the next N map loads fail as a room that cannot load does (Host_Error after the
 * running game is left); 1 tests the way back, 2 a way back that fails too. */
cvar_t aw_load_fail_test={"aw_load_fail_test","0"};
static int box_open;

static void tick(void) {
    static const char *const buttons[2]={"OK","Load Game"};int b,want;
    if(!box_open && key_dest==key_game && !AW_MsgBoxActive() && (want=AW_SceneLoadBoxTake())!=0){
        if(want==2){Con_Printf("Failed load: no way back; the load menu.\n");AW_SaveMenuOpen(1);return;}
        box_open=1;AW_MsgBoxShow(AW_SceneLoadBoxText(),buttons,2);return;
    }
    if(box_open && !AW_MsgBoxActive() && (b=AW_MsgBoxPressed())>=0){
        box_open=0;
        Con_Printf("Failed load box: %s\n",b==1?"Load Game":"OK");
        if(b==1)AW_SaveMenuOpen(1);
    }
}
static void load_fail_command(void) {
    if(Cmd_Argc()==2)Cvar_SetValue("aw_load_fail_test",(float)Q_atoi(Cmd_Argv(1)));
    Con_Printf("dbg loadfail: the next %ld map loads fail on purpose (0 = off).\n",(long)aw_load_fail_test.value);
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
static void reset_scene(int new_game){AW_SceneLoadReset();}       /* scene loads, the way back, followers */
static void reset_box(int new_game){box_open=0;AW_MsgBoxClear();}
static unsigned long digest_box(void){return (unsigned long)(AW_MsgBoxActive()*2+box_open);}
static void reset_scripts(int new_game){AW_MwscriptNewGameReset();}
/* DBG-NOBURDEN-62: the no-burden debug mode (aw_move.c) is off after New Game, as at boot */
static void reset_noburden(int new_game){(void)new_game;AW_MoveNoBurdenSet(0);}
static unsigned long digest_noburden(void){return (unsigned long)AW_MoveNoBurdenOn();}
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
    Cmd_AddCommand("aw_load_fail",load_fail_command);
    Cmd_AddCommand("aw_restart_game",restart_command);
    aw_loadfail_tick=tick;
    register_resets();
    aw_game_reset=game_reset;     /* aw_intro.c: New Game resets through the registry */
}
