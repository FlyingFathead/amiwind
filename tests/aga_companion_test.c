/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_companion.c with a synthetic server: every dbg companion subcommand and
 * alias, the toggle spellings, the distance clamp, pick mode (crosshair
 * state, Escape, the attack picks an NPC and is swallowed), following stops
 * at the distance without overshoot, release restores the picked NPC, the
 * test companion is spawned and removed cleanly, and saves never store it. */
#include "quakedef.h"
#include <assert.h>
#include "aw_anim.h"
#include <stdarg.h>

server_t sv;server_static_t svs;client_static_t cls;client_state_t cl;keydest_t key_dest;
int host_framecount;double host_frametime=.02;char *pr_strings;dprograms_t *progs;byte *host_basepal;
unsigned long aw_sv_move_calls;
/* the hooks live beside their callers (view.c, cl_input.c, aw_scene.c, aw_save.c) */
int (*aw_companion_crosshair)(int,int);int (*aw_companion_buttons)(int);
void (*aw_companion_scene)(edict_t *);int (*aw_companion_home)(edict_t *,vec3_t,vec3_t);
static char strings[64]="\0aw_npc\0Ajira\0";      /* 1: classname, 8: netname */
static edict_t edicts[16];static client_t client;static dprograms_t program;static model_t model;
static byte palette[768];static eval_t fields[16][8];
static int fills,fill_colour,steps,frees,step_cost=3;static edict_t *target;static double clock_now;

edict_t *EDICT_NUM(int n){return &edicts[n];}
eval_t *GetEdictFieldValue(edict_t *e,char *name){
    static const char *names[]={"aw_ref","aw_intro_role","aw_hello_distance","aw_moving","aw_walk_step","aw_idle_step"};
    int i;for(i=0;i<6;i++)if(!strcmp(name,names[i]))return &fields[e-edicts][i];
    return NULL;
}
edict_t *ED_Alloc(void){edict_t *e=&edicts[sv.num_edicts++];memset(e,0,sizeof(*e));return e;}
void ED_Free(edict_t *e){e->free=1;e->v.model=0;e->v.modelindex=0;frees++;}
void SV_LinkEdict(edict_t *e,qboolean touch){(void)e;(void)touch;}
/* Open floor at z 0: hull drops land on it, everything else is clear. */
trace_t SV_Move(vec3_t a,vec3_t mi,vec3_t ma,vec3_t b,int type,edict_t *e){
    trace_t t;(void)mi;(void)ma;(void)type;(void)e;aw_sv_move_calls++;
    memset(&t,0,sizeof(t));t.fraction=1;VectorCopy(b,t.endpos);
    if(b[2]<0 && a[2]>=0){t.fraction=a[2]/(a[2]-b[2]);t.endpos[2]=0;t.plane.normal[2]=1;}
    return t;
}
qboolean AW_ActorStep(edict_t *e,vec3_t move,double dt){(void)dt;e->v.origin[0]+=move[0];e->v.origin[1]+=move[1];aw_sv_move_calls+=step_cost;steps++;return true;}
edict_t *AW_NPCTargetReach(edict_t *p,vec3_t angles,float reach){(void)p;(void)angles;assert(reach>=300);return target;}
void Draw_Fill(int x,int y,int w,int h,int c){(void)x;(void)y;(void)w;(void)h;fills++;fill_colour=c;}
double Sys_FloatTime(void){return clock_now+=.0001;}
/* aw_anim.c engine glue: models here have no layout file (previous frames). */
const aw_anim_t *AW_AnimOf(edict_t *e){
    static aw_anim_t a;int i=(int)e->v.modelindex;AW_AnimDefault(&a,i>0 && i<MAX_MODELS && sv.models[i]?sv.models[i]->numframes:1);return &a;
}
void AW_AnimSounds(edict_t *e,const aw_anim_t *a,int group,unsigned long crossed,int medium){(void)e;(void)a;(void)group;(void)crossed;(void)medium;}
int AW_AnimMedium(edict_t *e){(void)e;return AW_ANIM_DRY;}
int aw_test_mover_on,aw_test_mover_off;static edict_t *aw_test_worn;
int AW_AnimMover(edict_t *e,int on){if(on){if(aw_test_worn)return 0;aw_test_worn=e;aw_test_mover_on++;return 1;}if(aw_test_worn!=e)return 0;aw_test_worn=NULL;aw_test_mover_off++;return 1;}
int AW_AnimMoving(edict_t *e){return e && aw_test_worn==e;}
static char console[4096];
void Con_Printf(char *f,...){va_list v;size_t n=strlen(console);va_start(v,f);
    if(n<sizeof(console)-256){vsnprintf(console+n,sizeof(console)-n,f,v);}
    va_end(v);}
void Sys_Error(char *f,...){(void)f;abort();}
int Q_strcasecmp(char *a,char *b){return strcasecmp(a,b);}
float Q_atof(char *s){return (float)atof(s);}

static struct {char *name;xcommand_t f;} commands[8];static int command_count;
static cvar_t *cvars[8];static int cvar_count;
void Cmd_AddCommand(char *name,xcommand_t f){commands[command_count].name=name;commands[command_count++].f=f;}
void Cvar_RegisterVariable(cvar_t *v){v->value=(float)atof(v->string);cvars[cvar_count++]=v;}
void Cvar_SetValue(char *name,float value){int i;for(i=0;i<cvar_count;i++)if(!strcmp(cvars[i]->name,name))cvars[i]->value=value;}
static char *argv[6];static int argc;
int Cmd_Argc(void){return argc;}
char *Cmd_Argv(int i){return i<argc?argv[i]:"";}
static void run(const char *line){
    static char buffer[128];char *p;int i;
    strcpy(buffer,line);argc=0;
    for(p=strtok(buffer," ");p && argc<6;p=strtok(NULL," "))argv[argc++]=p;
    for(i=0;i<command_count;i++)if(!strcmp(commands[i].name,argv[0])){commands[i].f();return;}
    assert(!"command not registered");
}
static void tick(int n){
    int i;for(i=0;i<n;i++){sv.time+=.1;host_framecount++;AW_CompanionPhysics();}
}
static float gap(edict_t *a,edict_t *p){
    float dx=p->v.origin[0]-a->v.origin[0],dy=p->v.origin[1]-a->v.origin[1];return (float)sqrt(dx*dx+dy*dy);
}

int main(void){
    edict_t *p=&edicts[1],*npc=&edicts[2],*spawned;vec3_t o,a;int i;float g,closest=1e9f;
    setvbuf(stdout,NULL,_IONBF,0);
    pr_strings=strings;progs=&program;program.entityfields=sizeof(entvars_t)/4;host_basepal=palette;
    palette[5*3]=250;                                   /* index 5: the reddest */
    sv.active=1;sv.edicts=edicts;sv.num_edicts=3;sv.models[1]=&model;model.numframes=21;sv.time=1;
    svs.maxclients=1;svs.clients=&client;client.edict=p;cls.state=ca_connected;key_dest=key_game;
    p->v.origin[0]=300;p->v.origin[2]=16.625f;p->v.mins[2]=-16.625f;p->v.view_ofs[2]=13;
    npc->v.classname=1;npc->v.netname=8;npc->v.modelindex=1;npc->v.solid=SOLID_SLIDEBOX;npc->v.nextthink=2;npc->v.think=7;
    npc->v.mins[0]=-7.32f;npc->v.mins[1]=-7.12f;npc->v.maxs[0]=7.32f;npc->v.maxs[1]=7.12f;npc->v.maxs[2]=33.25f;
    AW_CompanionInit();
    assert(aw_companion_crosshair && aw_companion_buttons && aw_companion_scene && aw_companion_home);

    /* toggle spellings */
    assert(AW_CompanionToggleWord("on")==1 && AW_CompanionToggleWord("TRUE")==1 && AW_CompanionToggleWord("1")==1);
    assert(AW_CompanionToggleWord("off")==0 && AW_CompanionToggleWord("False")==0 && AW_CompanionToggleWord("0")==0);
    assert(AW_CompanionToggleWord("maybe")==-1 && AW_CompanionToggleWord("2")==-1);

    /* distance: default 96, clamped to 48..512 */
    assert(AW_CompanionDistance()==96);
    run("aw_companion distance 10");assert(AW_CompanionDistance()==48);
    run("aw_companion distance 1000");assert(AW_CompanionDistance()==512);
    run("aw_companion distance 128");assert(AW_CompanionDistance()==128);
    run("aw_companion distance");assert(AW_CompanionDistance()==128);
    run("aw_companion distance 96");

    /* mimic speed: default on, all six spellings, junk ignored */
    assert(AW_CompanionMimic()==1);
    run("aw_companion mimic speed off");assert(!AW_CompanionMimic());
    run("aw_companion mimic speed true");assert(AW_CompanionMimic());
    run("aw_companion mimic speed 0");assert(!AW_CompanionMimic());
    run("aw_companion mimic speed 1");assert(AW_CompanionMimic());
    run("aw_companion mimic speed false");assert(!AW_CompanionMimic());
    run("aw_companion mimic speed on");assert(AW_CompanionMimic());
    run("aw_companion mimic speed maybe");assert(AW_CompanionMimic());
    run("aw_companion mimic speed");assert(AW_CompanionMimic());

    /* pick mode: off -> no effect on the crosshair or the attack */
    assert(!AW_CompanionPickMode() && AW_CompanionCrosshair(0,0)==0 && AW_CompanionButtons(3)==3);
    assert(AW_CompanionPickAim()==0);          /* the right button (+aw_alt) leaves it to the next context */
    run("aw_companion pick");assert(AW_CompanionPickMode());
    target=NULL;host_framecount++;assert(AW_CompanionCrosshair(0,0)==1 && fills==0);
    assert(AW_CompanionPickAim()==1 && !AW_CompanionEdict(npc));   /* right button in pick mode: handled, nothing aimed at */
    assert(AW_CompanionButtons(1)==0 && !AW_CompanionEdict(npc));   /* swallowed, nothing to pick */
    AW_CompanionButtons(0);
    target=npc;host_framecount++;assert(AW_CompanionCrosshair(10,10)==2 && fills==2 && fill_colour==5);
    assert(AW_CompanionButtons(1|2)==2);                               /* attack swallowed, jump kept */
    assert(AW_CompanionEdict(npc) && npc->v.solid==SOLID_NOT && npc->v.nextthink==0);
    assert(aw_test_mover_on==1 && AW_AnimMoving(npc));      /* it wears its full-kit model while it follows */
    run("aw_companion choose");assert(!AW_CompanionPickMode());
    run("aw_pickcompanion");assert(AW_CompanionPickMode());
    key_dest=key_menu;assert(AW_CompanionCrosshair(0,0)==0 && !AW_CompanionPickMode());   /* Escape */
    key_dest=key_game;

    /* following: approaches, stops at the distance, never overshoots */
    p->v.velocity[0]=150;
    for(i=0;i<80;i++){tick(1);g=gap(npc,p);if(g<closest)closest=g;}
    g=gap(npc,p);
    assert(g>=96-1 && g<=96+96/4+2 && closest>=96-1);
    assert(steps>0);
    /* standing still within the distance costs no traces */
    {unsigned long before=aw_sv_move_calls;tick(10);assert(aw_sv_move_calls==before);}
    /* the player walks off: it follows at the player's speed */
    p->v.origin[0]+=200;{float x0=npc->v.origin[0];tick(10);assert(npc->v.origin[0]-x0>100);}

    /* saves: the picked NPC is written at home, and put back after */
    assert(AW_CompanionHome(npc,o,a) && o[0]==0 && o[1]==0);
    {float x=npc->v.origin[0];AW_CompanionSaveSwap(1);assert(npc->v.origin[0]==0 && npc->v.solid==SOLID_SLIDEBOX && npc->v.nextthink==2);
     AW_CompanionSaveSwap(0);assert(npc->v.origin[0]==x && npc->v.solid==SOLID_NOT && npc->v.nextthink==0);}
    assert(!AW_CompanionSkipSave(npc));

    /* release: home spot, own solid and think again */
    run("aw_companion off");
    assert(!AW_CompanionEdict(npc) && npc->v.origin[0]==0 && npc->v.solid==SOLID_SLIDEBOX && npc->v.think==7 && npc->v.nextthink>sv.time);
    assert(aw_test_mover_off==1 && !AW_AnimMoving(npc));    /* back in its standing model */
    assert(!AW_CompanionHome(npc,o,a));

    /* test companion: a copy of the resident, not an aw_npc, removed cleanly */
    run("aw_companion test");
    spawned=&edicts[3];assert(sv.num_edicts==4 && AW_CompanionEdict(spawned));
    assert(!strcmp(pr_strings+spawned->v.classname,"aw_companion") && spawned->v.modelindex==1);
    assert(spawned->v.solid==SOLID_NOT && spawned->v.think==0 && spawned->v.nextthink==0);
    assert(AW_CompanionSkipSave(spawned) && !AW_CompanionHome(spawned,o,a));
    tick(5);
    /* steps that run the player's unstick search (many traces): two in a row,
     * never a third; the follower is placed beside the player instead */
    p->v.origin[0]+=150;step_cost=60;
    {int s0=steps;tick(12);assert(steps-s0==2);}
    step_cost=3;assert(gap(spawned,p)<64);
    /* stuck responses per actor kind (owner decision): a follower in the
     * player's view waits; once out of view it is placed behind the player */
    p->v.angles[1]=180;                                 /* looking back at it */
    p->v.origin[0]+=150;step_cost=60;console[0]=0;
    {int s0=steps;tick(30);assert(steps-s0==2);}
    assert(gap(spawned,p)>96 && strstr(console,"follower, wait until unseen"));
    p->v.angles[1]=0;tick(30);assert(gap(spawned,p)<64);    /* looks away: placed */
    /* a summon in combat never warps; out of combat it is placed like a follower */
    run("aw_companion kind summon");run("aw_companion combat on");
    p->v.origin[0]+=150;console[0]=0;tick(40);
    assert(gap(spawned,p)>96 && strstr(console,"summon, keep trying") && !strstr(console,"placed"));
    run("aw_companion combat off");tick(40);assert(gap(spawned,p)<64);
    /* a hostile chaser never warps: stuck, it flees and tries again later */
    run("aw_companion kind hostile");
    p->v.origin[0]+=150;console[0]=0;tick(60);
    assert(gap(spawned,p)>96 && strstr(console,"hostile, flee") && !strstr(console,"placed"));
    run("aw_companion kind escort");run("aw_companion kind follower");step_cost=3;
    run("aw_companiontest off");assert(spawned->free && frees==1 && !AW_CompanionEdict(spawned) && !AW_CompanionSkipSave(spawned));
    assert(aw_test_mover_on==2 && aw_test_mover_off==2 && !AW_AnimMoving(spawned));
    run("aw_companiontest on");assert(sv.num_edicts==5 && AW_CompanionEdict(&edicts[4]));
    /* a scene load: the test companion rejoins in the new scene */
    sv.num_edicts=4;memset(&edicts[3],0,2*sizeof(edict_t));
    AW_CompanionSceneSpawn(p);assert(AW_CompanionEdict(&edicts[4]) || AW_CompanionEdict(&edicts[3]));
    run("aw_companion off");assert(!AW_CompanionEdict(&edicts[3]) && !AW_CompanionEdict(&edicts[4]));
    /* a picked NPC stays behind in its scene */
    run("aw_companion pick");target=npc;host_framecount++;AW_CompanionButtons(0);AW_CompanionButtons(1);
    assert(AW_CompanionEdict(npc));AW_CompanionSceneSpawn(p);assert(!AW_CompanionEdict(npc) && !AW_CompanionPickMode());
    run("aw_companion");run("aw_companiontest");
    return 0;
}
