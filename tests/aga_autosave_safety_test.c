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
void Con_Printf(char *s,...){va_list args;va_start(args,s);vfprintf(stderr,s,args);va_end(args);}
void Cvar_RegisterVariable(cvar_t *c){c->value=atof(c->string);}
void Cmd_AddCommand(char *s,void(*f)(void)){}
eval_t *GetEdictFieldValue(edict_t *e,char *name){static eval_t hidden;return &hidden;}
edict_t *EDICT_NUM(int n){assert(0);return NULL;}
int AW_SceneMapSize(const char *name,char *map,int capacity){assert(0);return 0;}
int AW_RegionSelect(const char *name,const float *position,int variant){assert(0);return 0;}
void IN_AWClearButtons(void){assert(0);}
void Cbuf_InsertText(char *text){assert(0);}
static int latest(void){char label[96];return AW_SaveLatest(2,label,sizeof(label));}
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
    puts("unsafe autosaves preserve the prior checkpoint; safe arrival saves after settling");
    return 0;
}
