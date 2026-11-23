/* SPDX-License-Identifier: GPL-3.0-only
 * CONTAINER-SCRIPT-ACTIVATE-67: a dead actor's body and the scripts' hold on its use (aw_corpse.c): the real aim-to-
 * search path (corpse_use through aw_corpse_use) and the script's Activate (AW_CorpseActivate), with stand-ins for the
 * aim, the fight state, the strip and the scripts' hold (aw_mwhost.c object_intercept). A body whose script holds the
 * use is not searched by E; the script's Activate searches it; a living actor is left to the caller's talk. */
#include "quakedef.h"
#include "aw_inventory.h"
#include "aw_actors.h"
#include "aw_character.h"
#include <assert.h>
void AW_CorpseInit(void);
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;
static client_t client;
static edict_t entities[4];
char *pr_strings;
static char strings[32]="\0Spriggan";
aw_character_t aw_character;
int (*aw_container_open)(unsigned reference,const char *name,int owned);
int (*aw_scene_intercept)(unsigned reference);
int (*aw_corpse_prompt)(char *line,int size,const char **name);
int (*aw_corpse_use)(void);
int (*aw_levelled_valid)(const unsigned char *s,unsigned long bytes,unsigned items);
int (*aw_levelled_pick)(const unsigned char *s,unsigned index,int level,unsigned *state);
int (*aw_levelled_level)(void);
#define BODY 310222u
static eval_t body_ref;
static int state=2,opens,holds,hold_answer;static unsigned opened_ref,hold_ref;static char opened_name[32];
void Con_Printf(char *format,...){(void)format;}
edict_t *EDICT_NUM(int i){assert(i>=0 && i<4);return &entities[i];}
eval_t *GetEdictFieldValue(edict_t *e,char *field){return e==&entities[2] && !strcmp(field,"aw_ref")?&body_ref:NULL;}
edict_t *AW_ActivateActor(edict_t *player,vec3_t angles){(void)player;(void)angles;return &entities[2];}
edict_t *AW_NPCTarget(edict_t *player,vec3_t angles){(void)player;(void)angles;return &entities[2];}
int AW_CombatSlotState(edict_t *e,float *health){(void)health;return e==&entities[2]?state:0;}
int ChimActors_ListsValid(const unsigned char *s,unsigned long bytes,unsigned bases){(void)s;(void)bytes;(void)bases;return 0;}
int ChimActors_LevelledPick(const unsigned char *s,unsigned index,int level,unsigned *st){(void)s;(void)index;(void)level;(void)st;return -1;}
trace_t SV_Move(vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,int type,edict_t *pass){
    trace_t tr;(void)start;(void)mins;(void)maxs;(void)end;(void)type;(void)pass;memset(&tr,0,sizeof(tr));tr.fraction=1;return tr;
}
void SV_LinkEdict(edict_t *e,qboolean triggers){(void)e;(void)triggers;}
void *Cache_Check(cache_user_t *c){(void)c;return NULL;}
double Sys_FloatTime(void){return 0;}
int Cmd_Argc(void){return 0;}
char *Cmd_Argv(int arg){(void)arg;return "";}
static int open_stand_in(unsigned reference,const char *name,int owned){
    assert(!owned);opened_ref=reference;strncpy(opened_name,name,sizeof(opened_name)-1);opens++;return 1;
}
static int hold_stand_in(unsigned reference){holds++;hold_ref=reference;return hold_answer;}
int main(void){
    char line[48];const char *name=NULL;
    pr_strings=strings;sv.active=1;sv.num_edicts=3;svs.maxclients=1;svs.clients=&client;client.edict=&entities[1];
    entities[2].v.netname=1;body_ref._float=(float)BODY;
    AW_CorpseInit();assert(aw_corpse_use && aw_corpse_prompt);
    /* no strip: nothing to open */
    assert(!aw_corpse_use());
    aw_container_open=open_stand_in;
    /* no script holds the use: E searches the body, as before */
    assert(aw_corpse_prompt(line,sizeof(line),&name) && !strcmp(line,"E: Search") && !strcmp(name,"Spriggan"));
    assert(aw_corpse_use() && opens==1 && opened_ref==BODY && !strcmp(opened_name,"Spriggan"));
    aw_scene_intercept=hold_stand_in;hold_answer=0;
    assert(aw_corpse_use() && opens==2 && holds==1 && hold_ref==BODY);
    /* its script holds the use: E is the script's, the body stays shut */
    hold_answer=1;
    assert(aw_corpse_use() && opens==2 && holds==2);
    /* the script's Activate: the body's own use, the search */
    assert(AW_CorpseActivate(&entities[2],BODY) && opens==3 && opened_ref==BODY);
    /* a living actor (0), one in a fight (1): not the body's use, the caller's talk; and no hold is asked of the living */
    state=0;assert(!AW_CorpseActivate(&entities[2],BODY) && opens==3);
    assert(!aw_corpse_use() && holds==2);
    state=1;assert(!AW_CorpseActivate(&entities[2],BODY) && opens==3);
    /* a freed edict, none: nothing */
    state=2;entities[2].free=true;assert(!AW_CorpseActivate(&entities[2],BODY) && !AW_CorpseActivate(NULL,BODY) && opens==3);
    entities[2].free=false;
    /* dead without a strip: used up, nothing opened */
    aw_container_open=NULL;assert(AW_CorpseActivate(&entities[2],BODY) && opens==3);
    return 0;
}
