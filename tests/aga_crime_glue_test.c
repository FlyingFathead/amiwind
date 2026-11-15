/* SPDX-License-Identifier: GPL-2.0-or-later
 * CRIME-KILL-BOUNTY-65: the crime layer's engine side (aw_crime.c) on a small street of NPCs, with the real rules
 * (aw_crime_rules.c) and the real bounty (aw_pcstanding.c): a test per crime kind and the guard's kill.
 * The settings are Morrowind.esm's own (iCrimeAttack 40, iCrimeKilling 1000, ...). The host's hooks (aw_mwhost.c in
 * the game: an NPC's facts, the fight, the arrest talk) are the table below; nothing else of the game runs. */
#include "quakedef.h"
#include "aw_crime.h"
#include "aw_combat.h"
#include "aw_pcstanding.h"
#include "aw_glut.h"
#include "aw_msgbox.h"
#include "aw_inventory.h"
#include "aw_harvest_runtime.h"
#include "aw_placed.h"
#include "aw_ledger.h"
#include "aw_state.h"
#include "aw_world.h"
#include "aw_dial.h"
#include "aw_character.h"
#include "aw_levelup.h"
#include "aw_rest.h"
#include "aw_statswin.h"
#include "aw_mwvm.h"
#include "aw_actors.h"
#include "aw_torch.h"
#include <assert.h>
#include <stdarg.h>

/* --- the game around it --- */
server_t sv;server_static_t svs;client_state_t cl;client_static_t cls;
double realtime;keydest_t key_dest=key_game;
aw_combat_ai_t aw_combat_ai;aw_class_t aw_classes[32];aw_character_t aw_character;aw_state_t aw_state;aw_ledger_t aw_ledger;
int aw_ledger_on;aw_levelup_rules_t aw_levelup_rules;cvar_t aw_torch_strength;
void (*aw_combat_assault)(struct edict_s *victim);void (*aw_combat_killed)(struct edict_s *victim);
void (*aw_harvest_theft)(const char *owner,const char *id,int count);
void (*aw_inventory_theft)(const char *owner,int faction,const char *id,int count,int value);
void (*aw_placed_crime)(void);int (*aw_rest_bed_crime)(unsigned long reference,const char *owner,int faction);
int (*aw_door_is_marker)(unsigned long ref);
static client_t client;
#define EDICTS 48
static edict_t ents[EDICTS];
char *pr_strings;static char pool[4096];static int pool_used=1;
static int str(const char *s){int at=pool_used;strcpy(pool+at,s);pool_used+=(int)strlen(s)+1;return at;}
edict_t *EDICT_NUM(int i){assert(i>=0 && i<EDICTS);return &ents[i];}
int NUM_FOR_EDICT(edict_t *e){return (int)(e-ents);}
/* the edicts' fields: aw_ref and aw_source_id */
static eval_t refs[EDICTS],ids[EDICTS];
eval_t *GetEdictFieldValue(edict_t *e,char *field){
    int i=NUM_FOR_EDICT(e);
    if(!strcmp(field,"aw_ref"))return &refs[i];
    if(!strcmp(field,"aw_source_id"))return &ids[i];
    return NULL;
}
static int verbose;
void Con_Printf(char *format,...){va_list a;if(!verbose)return;va_start(a,format);vprintf(format,a);va_end(a);}
void Con_DPrintf(char *format,...){(void)format;}
void Sys_Error(char *error,...){(void)error;assert(0);}
double Sys_FloatTime(void){return realtime;}
trace_t SV_Move(vec3_t start,vec3_t mins,vec3_t maxs,vec3_t end,int type,edict_t *pass){
    trace_t tr;(void)start;(void)mins;(void)maxs;(void)type;(void)pass;
    memset(&tr,0,sizeof(tr));tr.fraction=1;VectorCopy(end,tr.endpos);return tr;
}
void SV_LinkEdict(edict_t *e,qboolean t){(void)e;(void)t;}
static char settings_text[2048];
int COM_FOpenFile(char *name,FILE **file){
    *file=NULL;
    if(strcmp(name,"combat/settings.txt"))return -1;
    *file=tmpfile();fputs(settings_text,*file);rewind(*file);return (int)strlen(settings_text);
}
int Q_strncasecmp(char *a,char *b,int n){return strncasecmp(a,b,(size_t)n);}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
int AW_InventoryRead(const char *id,aw_inventory_item_t *out){(void)id;(void)out;return 0;}
int Cmd_Argc(void){return 0;}
char *Cmd_Argv(int i){(void)i;return "";}
int AW_CharacterClassCount(void){return 0;}
static int fighting[EDICTS];static aw_fighter_t fighters[EDICTS];
const aw_fighter_t *AW_CombatFighter(struct edict_s *e){int i=NUM_FOR_EDICT(e);return fighting[i]?&fighters[i]:NULL;}
int AW_CombatTestEngage(edict_t *t,int dead){(void)t;(void)dead;return 0;}
void AW_CombatEquipmentChanged(void){}
int AW_ContainerChange(unsigned reference,const char *id,int count,int owner_mark){(void)reference;(void)id;(void)count;(void)owner_mark;return 0;}
int AW_DialWindowActive(void){return 0;}
int AW_GlutSay(struct edict_s *e,int topic,int talked){(void)e;(void)topic;(void)talked;return 0;}
const char *AW_GlutText(void){return "";}
int AW_Interior(void){return 0;}
int AW_LedgerStolenAdd(aw_ledger_t *l,const char *item,const char *owner,int faction,int count){(void)l;(void)item;(void)owner;(void)faction;(void)count;return 0;}
int AW_LevelupGameText(const char *key,char *out,int size){(void)key;(void)size;out[0]=0;return 0;}
int AW_LevelupLoad(void){return 0;}
int AW_LevelupSkillRaise(const aw_levelup_rules_t *r,const aw_class_t *k,aw_character_t *c,int skill,int source){(void)r;(void)k;(void)c;(void)skill;(void)source;return 0;}
int AW_MapTeleportAt(const float *at,int n){(void)at;(void)n;return 0;}
int AW_MsgBoxActive(void){return 0;}
static int boxes;
void AW_MsgBoxShow(const char *text,const char *const *buttons,int count){(void)text;(void)buttons;(void)count;boxes++;}
void AW_MwvmStateChanged(void){}
int AW_PlacedTake(unsigned reference){(void)reference;return 0;}
void AW_RestPass(int hours,int sleeping){(void)hours;(void)sleeping;}
int AW_SceneStarting(void){return 0;}
int32_t AW_StateGet(const aw_state_t *state,int kind,const char *id){(void)state;(void)kind;(void)id;return 0;}
int AW_StateSet(aw_state_t *state,int kind,const char *id,int32_t value){(void)state;(void)kind;(void)id;(void)value;return 0;}
const char *AW_StatsSkillName(int i){(void)i;return "";}
void AW_UISubtitle(const char *a,const char *b,double d){(void)a;(void)b;(void)d;}
int AW_WorldToSource(const char *name,const float *local,float *out){(void)name;(void)local;(void)out;return 0;}
int AW_SourceToWorld(const char *name,const float *in,float *local){(void)name;(void)in;(void)local;return 0;}

/* --- the street: the host's facts of each NPC (aw_mwhost.c crime_witness in the game) --- */
typedef struct {int used,alarm,fight,guard,dead,engaged;unsigned long ref;} npc_t;
static npc_t npcs[EDICTS];
static int pursuing[EDICTS],attacked[EDICTS],greets;
static int witness(edict_t *e,aw_crime_witness_t *w){
    npc_t *n=&npcs[NUM_FOR_EDICT(e)];
    if(!n->used)return 0;
    w->alarm=n->alarm;w->fight=n->fight;w->guard=n->guard;w->can_report=!n->dead;
    w->engaged=n->engaged && !n->dead;w->aggressive=w->engaged;w->disposition=50;w->reference=n->ref;
    w->observer.fatigue_term=1;w->observer.sneak=5;w->observer.agility=40;w->observer.luck=40;
    return 1;
}
static int attack(edict_t *e,int fight){(void)fight;attacked[NUM_FOR_EDICT(e)]=1;npcs[NUM_FOR_EDICT(e)].engaged=1;return 1;}
static int pursue(edict_t *e,int on){pursuing[NUM_FOR_EDICT(e)]=on;return 1;}
static int greet(edict_t *e){(void)e;greets++;return 1;}
static int guard_of(edict_t *e){return npcs[NUM_FOR_EDICT(e)].guard;}
static void calm(edict_t *e){npcs[NUM_FOR_EDICT(e)].engaged=0;}

static edict_t *player;
/* an NPC at X units east of the player (the alarm radius is fAlarmRadius 2000 original units) */
static edict_t *npc(const char *name,unsigned long ref,int alarm,int guard,float x){
    int i=sv.num_edicts++;edict_t *e=&ents[i];npc_t *n=&npcs[i];
    assert(i<EDICTS);memset(e,0,sizeof(*e));
    e->v.classname=str("aw_npc");e->v.netname=str(name);e->v.origin[0]=x;e->v.maxs[2]=64;e->v.modelindex=1;
    e->v.angles[1]=180;           /* facing the player */
    refs[i]._float=(float)ref;ids[i].string=str(name);
    memset(n,0,sizeof(*n));n->used=1;n->alarm=alarm;n->guard=guard;n->ref=ref;n->fight=30;
    return e;
}
static void street(void){
    int i;
    memset(&sv,0,sizeof(sv));memset(&svs,0,sizeof(svs));memset(ents,0,sizeof(ents));memset(npcs,0,sizeof(npcs));
    memset(pursuing,0,sizeof(pursuing));memset(attacked,0,sizeof(attacked));memset(fighting,0,sizeof(fighting));
    for(i=0;i<EDICTS;i++){refs[i]._float=0;ids[i].string=0;}
    pr_strings=pool;sv.active=1;sv.num_edicts=2;svs.maxclients=1;svs.clients=&client;
    player=&ents[1];client.edict=player;player->v.classname=str("player");player->v.view_ofs[2]=22;
    player->v.maxs[0]=16;player->v.mins[2]=-24;
    AW_StandingReset();AW_CrimeActorsReset();greets=boxes=0;realtime+=10;
}
static void dies(edict_t *e){npcs[NUM_FOR_EDICT(e)].dead=1;fighting[NUM_FOR_EDICT(e)]=1;fighters[NUM_FOR_EDICT(e)].dead=1;}

int main(void){
    static const char *const values[AW_CRIME_SETTING_COUNT]={"2000","1","-0.5","50","1","-1","0.5","0.002","0.5","1.5","1000",
        "40","1000","5","25","-50","-10","-50","-20","-25","100","50","50","25","25","100","10","0.5","0.9"};
    int i,o=0;
    setvbuf(stdout,NULL,_IONBF,0);
    for(i=0;i<AW_CRIME_SETTING_COUNT;i++)
        o+=sprintf(settings_text+o,"crime %s %s\n",AW_CrimeSettingName(i),values[i]);
    o+=sprintf(settings_text+o,"text sCrimeMessage Your crime has been reported.\n");
    aw_crime_witness=witness;aw_crime_attack=attack;aw_crime_pursue=pursue;aw_crime_greet=greet;aw_crime_guard=guard_of;
    aw_crime_calm=calm;
    aw_combat_ai.fFightDispMult=.2f;aw_combat_ai.iFightDistanceBase=20;aw_combat_ai.fFightDistanceMultiplier=.005f;

    /* THEFT: an owner's thing worth 30 taken in front of a guard (Alarm 100): bounty 30 (fCrimeStealing 1) */
    street();npc("Guard",101,100,1,100);npc("Shopkeeper",102,0,0,120);
    assert(AW_CrimeTheft("shopkeeper",0,30)>0 && AW_StandingCrime()==30);

    /* TRESPASS and an owned BED: iCrimeTresspass 5 each */
    street();npc("Guard",101,100,1,100);npc("Owner",102,0,0,120);
    assert(AW_CrimeTrespass("owner",0,0) && AW_StandingCrime()==5);
    assert(AW_CrimeTrespass("owner",0,1) && AW_StandingCrime()==10);

    /* ASSAULT on a commoner seen by a guard: iCrimeAttack 40, the guard pursues to arrest */
    {edict_t *g,*c;
     street();g=npc("Guard",101,100,1,100);c=npc("Commoner",102,0,0,60);
     assert(AW_CrimeAssault(c) && AW_StandingCrime()==40 && pursuing[NUM_FOR_EDICT(g)]);
     /* MURDER of that commoner, now fighting back (no fair target any more): the assault gave him the crime's
      * number, so his death is a murder (actorKilled): iCrimeKilling 1000 on top */
     npcs[NUM_FOR_EDICT(c)].engaged=1;
     dies(c);assert(AW_CrimeKilled(c,-1) && AW_StandingCrime()==1040);
     assert(AW_CrimeOnMurder(102) && !AW_CrimeOnMurder(102));}

    /* MURDER of a commoner never attacked before (a fair target at the blow) heard by the guard: 1000 */
    {edict_t *c;
     street();npc("Guard",101,100,1,300);c=npc("Commoner",102,0,0,60);
     dies(c);assert(AW_CrimeKilled(c,1) && AW_StandingCrime()==1000);}

    /* THE MAINTAINER'S CASE, a guard killed in a Balmora street with people around: the first blow is an assault the
     * guard reports himself (40) and he pursues; then he fights (the arrest refused); his death is a murder: another
     * guard and the people in the street hear it: 1040 */
    {edict_t *g,*g2;
     street();g=npc("Guard",101,100,1,60);g2=npc("Guard",103,100,1,500);npc("Commoner",102,0,0,200);
     npc("Commoner",104,30,0,300);
     assert(AW_CrimeAssault(g) && AW_StandingCrime()==40);
     npcs[NUM_FOR_EDICT(g)].engaged=1;
     assert(!AW_CrimeAssault(g) && AW_StandingCrime()==40);            /* in the fight: no new assault */
     dies(g);assert(AW_CrimeKilled(g,-1));
     if(AW_StandingCrime()!=1040){printf("guard murder: bounty %d, expected 1040\n",AW_StandingCrime());assert(0);}
     (void)g2;}

    /* (a) the original's rule: a guard killed with nobody else in the radius able to report it adds no murder bounty
     * (OpenMW 0.51 reportCrime: a witness with Alarm 100; the dead victim cannot report) */
    {edict_t *g;
     street();g=npc("Guard",101,100,1,60);npc("Commoner",102,0,0,200);
     assert(AW_CrimeAssault(g) && AW_StandingCrime()==40);
     npcs[NUM_FOR_EDICT(g)].engaged=1;dies(g);AW_CrimeKilled(g,-1);
     assert(AW_StandingCrime()==40);}

    /* (b) the arrest talk ends the pursuit; a blow before the fight starts is a new assault (canCommitCrimeAgainst:
     * not aggressive, not in combat, not pursuing: OpenMW the same), but the kill after it is still a murder */
    {edict_t *g;
     street();g=npc("Guard",101,100,1,10);npc("Guard",103,100,1,500);
     player->v.origin[2]=0;g->v.mins[2]=-24;
     assert(AW_CrimeAssault(g) && AW_StandingCrime()==40 && pursuing[NUM_FOR_EDICT(g)]);
     realtime+=1;AW_CrimeTick(.1f);
     assert(greets==1 && !pursuing[NUM_FOR_EDICT(g)]);
     assert(AW_CrimeAssault(g) && AW_StandingCrime()==80);
     npcs[NUM_FOR_EDICT(g)].engaged=1;dies(g);assert(AW_CrimeKilled(g,-1));
     if(AW_StandingCrime()!=1080){printf("(b) bounty %d, expected 1080\n",AW_StandingCrime());assert(0);}}

    /* (c) an NPC without a placed reference (a story actor) keeps no crime row: the assault is reported, but his
     * death once he fights is no murder (no crime number to remember) */
    {edict_t *n;
     street();n=npc("Stranger",0,0,0,60);npc("Guard",103,100,1,300);
     assert(AW_CrimeAssault(n) && AW_StandingCrime()==40);
     npcs[NUM_FOR_EDICT(n)].engaged=1;dies(n);
     if(!AW_CrimeKilled(n,-1) || AW_StandingCrime()!=1040){printf("(c) refless victim: bounty %d, expected 1040\n",AW_StandingCrime());assert(0);}}

    /* (d) the crime rows fill up: after many crimes in one street (every witness keeps a row) and the fine paid, a
     * new guard's assault and kill are still a murder */
    {edict_t *g;int k;
     street();
     for(k=0;k<40;k++)npc("Commoner",200+k,50,0,100+k);   /* Alarm 50: each keeps the theft's disposition change */
     npc("Guard",103,100,1,500);
     assert(AW_CrimeTheft("commoner",0,20)>0 && AW_StandingCrime()==20);
     g=npc("Guard",101,100,1,60);
     assert(AW_CrimeAssault(g) && AW_StandingCrime()==60);
     npcs[NUM_FOR_EDICT(g)].engaged=1;dies(g);AW_CrimeKilled(g,-1);
     if(AW_StandingCrime()!=1060){printf("(d) full rows: bounty %d, expected 1060\n",AW_StandingCrime());assert(0);}}

    puts("Crime glue: theft, trespass, owned bed, assault, murder; the guard's kill in a street (1040), alone (40, the "
         "original's rule), after the arrest talk (1080), a refless victim and full rows (1040).");
    return 0;
}
