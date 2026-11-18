/* SPDX-License-Identifier: GPL-2.0-or-later
 * Reuse the valid, real AWS4 front-menu fixture, then drive the real autosave
 * tick and disk writer through unsafe arrival and recovery transitions. */
#define main frontmenu_main
#include "aga_save_frontmenu_test.c"
#undef main
#include <stdarg.h>

server_t sv;server_static_t svs;client_static_t cls;client_state_t cl;
double realtime;keydest_t key_dest=key_game;
static client_t client;static edict_t player;
static int combat,modal,loading_screen,photo;
char *pr_strings="";
int AW_MapLogicalId(const char *name){return !strcmp(name,"seyda")?0:-1;}
int AW_CharacterActive(void){return 0;}
int AW_ReaderActive(void){return 0;}
int AW_ModalWorldFrozen(void){return modal;}
int AW_LoadingScreen(void){return loading_screen;}
int AW_PhotoModeActive(void){return photo;}
int AW_PlayerInCombat(void){return combat;}
double AW_SpeechRemaining(void){return 0;}
void AW_UISubtitle(const char *a,const char *b,double t){fprintf(stderr,"%s\n",b);assert(0);}
/* SAVE-AUTOSAVE-REGRESSED-67: the console's lines kept, so dbg save status can be read back */
static char said[8192];
void Con_Printf(char *s,...){
    va_list args;size_t n=strlen(said);
    va_start(args,s);vfprintf(stderr,s,args);va_end(args);
    if(n<sizeof(said)-1){va_start(args,s);vsnprintf(said+n,sizeof(said)-n,s,args);va_end(args);}
}
void Cvar_RegisterVariable(cvar_t *c){c->value=atof(c->string);}
static void (*save_status)(void);   /* aw_save_status, as AW_SaveInit registers it */
void Cmd_AddCommand(char *s,void(*f)(void)){if(!strcmp(s,"aw_save_status"))save_status=f;}
/* the status's answer: 1 when it holds TEXT */
static int status_says(const char *text){said[0]=0;assert(save_status);save_status();return strstr(said,text)!=NULL;}
/* aw_quickload's optional profile and slot (no console arguments here) */
int Cmd_Argc(void){return 1;}
char *Cmd_Argv(int i){(void)i;return "";}
int Q_atoi(char *s){return atoi(s);}
eval_t *GetEdictFieldValue(edict_t *e,char *name){static eval_t hidden;return &hidden;}
edict_t *EDICT_NUM(int n){assert(0);return NULL;}
int AW_SceneMapSize(const char *name,char *map,int capacity){assert(0);return 0;}
int AW_RegionSelect(const char *name,const float *position,int variant){assert(0);return 0;}
void IN_AWClearButtons(void){assert(0);}
void Cbuf_InsertText(char *text){assert(0);}
static int latest(void){char label[96];return AW_SaveLatest(2,label,sizeof(label));}
/* SAVE-AUTOSAVE-REGRESSED-67: the script host's step count as aw_mwhost.c keeps it, and a step an error ended (Host_Error
 * longjmps out of the step: the count is never brought down) */
static int step_depth;
static int steps_busy(void){return step_depth>0;}
static void steps_clear(void){step_depth=0;}
int main(int argc,char **argv)
{
    unsigned char raw[AW_SAVE_BYTES];aw_save_t save;FILE *f;int i;
    frontmenu_main(argc,argv);
    f=fopen("saves/p00000002/m00a.aws","rb");assert(f);
    i=fread(raw,1,sizeof(raw),f);fclose(f);assert(AW_SaveDecode(raw,i,&save));
    save.character.maximum[0]=save.character.current[0]=100;
    AW_SaveSnapshotRestore(&save);AW_SaveInit();
    sv.active=true;sv.num_edicts=1;strcpy(sv.name,"seyda");
    svs.maxclients=1;svs.clients=&client;client.edict=&player;
    cls.state=ca_connected;cls.signon=SIGNONS;
    player.v.health=100;player.v.movetype=MOVETYPE_WALK;
    player.v.flags=FL_ONGROUND;player.v.watertype=CONTENTS_EMPTY;
    AW_SaveSchedule();assert(latest()==0);
    /* A teleport can take longer than its original three-second delay.
     * Neither loading, the airborne fall, nor live lava contact may save. */
    realtime=10;cls.signon=3;AW_SaveTick();assert(latest()==0);
    realtime=14;cls.signon=SIGNONS;player.v.flags=0;AW_SaveTick();assert(latest()==0);
    realtime=18;player.v.flags=FL_ONGROUND;player.v.waterlevel=1;
    player.v.watertype=CONTENTS_LAVA;player.v.health=10;AW_SaveTick();assert(latest()==0);
    realtime=22;player.v.health=0;AW_SaveTick();assert(latest()==0);
    /* On safe recovery, settle again; retain the pending teleport checkpoint. */
    realtime=23;player.v.health=100;player.v.waterlevel=0;AW_SaveTick();assert(latest()==0);
    realtime=25.1;AW_SaveTick();assert(latest()==5);
    AW_SaveSchedule();realtime=30;player.v.waterlevel=1;player.v.watertype=CONTENTS_SLIME;
    AW_SaveTick();assert(latest()==5);
    realtime=34;player.v.watertype=CONTENTS_WATER;player.v.waterlevel=3;
    AW_SaveTick();assert(latest()==5);
    realtime=38;player.v.waterlevel=0;combat=1;AW_SaveTick();assert(latest()==5);
    realtime=42;combat=0;modal=1;AW_SaveTick();assert(latest()==5);
    realtime=46;modal=0;loading_screen=1;AW_SaveTick();assert(latest()==5);
    realtime=50;loading_screen=0;photo=1;AW_SaveTick();assert(latest()==5);
    realtime=54;photo=0;player.v.velocity[2]=-100;AW_SaveTick();assert(latest()==5);
    realtime=58;player.v.velocity[2]=0;AW_SaveTick();assert(latest()==6);
    /* dbg save status (SAVE-AUTOSAVE-REGRESSED-67): the character's autosaves counted from its folder, the last save,
     * and what holds the next one back, named by the tick's own conditions */
    assert(status_says("autosaves -> 2\n") && status_says("Held by: nothing\n"));
    assert(status_says("Last save: Autosave 2 written"));
    combat=1;assert(status_says("Held by: a fight is on\n"));combat=0;
    player.v.flags=0;assert(status_says("Held by: the player is not on the ground\n"));player.v.flags=FL_ONGROUND;
    key_dest=key_console;assert(status_says("Held by: nothing\n"));   /* the console it is typed in does not count */
    key_dest=key_menu;assert(status_says("Held by: a menu or the console is open\n"));key_dest=key_game;
    player.v.health=0;assert(status_says("Held by: the player is dead\n"));player.v.health=100;
    /* SAVE-AUTOSAVE-REGRESSED-67: a Host_Error inside a script step (its longjmp skipped the count down, so the host
     * still reads a step running), then a map change: the autosave is written, and the manual save asked for while
     * the step ran too. Before, every later save waited for that step for good and no autosave was ever written. */
    aw_save_busy=steps_busy;aw_save_busy_clear=steps_clear;
    step_depth=1;                                   /* the step the error ended */
    assert(AW_SaveWrite(1)==2 && AW_SaveQueued()==1);   /* asked for "inside" it: queued (SAVE-INSIDE-SCRIPT-STEP-66) */
    realtime=70;AW_SaveSchedule();                  /* the next map spawns (AW_SaveSpawn): an autosave due 3 s settled */
    realtime=74;AW_SaveTick();
    assert(step_depth==0 && AW_SaveQueued()<0);     /* the dead step let go, the queued manual save written */
    assert(AW_SaveSlotState(2,1)==AW_SLOT_OK);
    assert(latest()==7);                            /* and the autosave: Autosave 3 in the next free slot */
    assert(status_says("autosaves -> 3\n") && status_says("Last save: Autosave 3 written"));
    /* a script step that really runs still makes a save wait, and only for it */
    step_depth=1;assert(AW_SaveWrite(2)==2);step_depth=0;
    realtime=75;AW_SaveTick();assert(AW_SaveQueued()<0 && AW_SaveSlotState(2,2)==AW_SLOT_OK);
    puts("unsafe autosaves preserve the prior checkpoint; safe arrival saves after settling");
    puts("a script step an error ended no longer holds every later save: the autosave after the next map change is written");
    return 0;
}
