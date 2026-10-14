/* SPDX-License-Identifier: GPL-2.0-or-later
 * Real aw_anim.c engine glue: Quake reuses model pointers across a same-map
 * server reload but clears its precache bank. Every new bank must register
 * lazy movers again, then wear actual run/attack groups and return to base.
 */
#include "quakedef.h"
#include "aw_anim.h"
#include "aw_combat.h"
#include <assert.h>

server_t sv;server_static_t svs;client_static_t cls;client_state_t cl;
char *pr_strings;double realtime;
void (*aw_combat_voice)(edict_t *,int);
static char strings[256];
static model_t world,base,mover;
static int loaded,freed,layouts;
static const char *standing="idle:0:8:0.3 hit:8:3:0.3 death:11:6:0.3 >progs/resident_m.mdl";
static const char *moving="idle:0:8:0.3 walk:8:4:0.25:48 run:12:4:0.23:70 hit:24:3:0.3 knock:27:4:0.66 death:31:4:0.5 attack:35:5:0.18:0.714";

void Cvar_RegisterVariable(cvar_t *c){c->value=(float)atof(c->string);}
int Hunk_LowMark(void){return 0;}
void Hunk_FreeToLowMark(int m){assert(m==0);}
byte *COM_LoadHunkFile(char *p){
    layouts++;
    if(!strcmp(p,"progs/resident.anm"))return (byte *)standing;
    if(!strcmp(p,"progs/resident_m.anm"))return (byte *)moving;
    return NULL;
}
model_t *Mod_FindName(char *n){assert(!strcmp(n,"progs/resident_m.mdl"));return &mover;}
model_t *Mod_ForName(char *n,qboolean crash){(void)crash;assert(!strcmp(n,"progs/resident_m.mdl"));mover.numframes=51;mover.type=mod_alias;loaded++;return &mover;}
void *Cache_Check(cache_user_t *c){(void)c;return loaded?(void *)&mover:NULL;}
void Cache_Free(cache_user_t *c){(void)c;freed++;}
void Con_Printf(char *f,...){(void)f;}
int AW_CombatHealthPercent(edict_t *e){(void)e;return -1;}
int COM_FOpenFile(char *p,FILE **f){(void)p;*f=NULL;return -1;}
int SV_PointContents(vec3_t p){(void)p;return CONTENTS_EMPTY;}
trace_t SV_Move(vec3_t a,vec3_t mi,vec3_t ma,vec3_t b,int t,edict_t *e){trace_t x;(void)a;(void)mi;(void)ma;(void)b;(void)t;(void)e;memset(&x,0,sizeof(x));x.fraction=1;return x;}
void SV_StartSound(edict_t *e,int c,char *s,int v,float a){(void)e;(void)c;(void)s;(void)v;(void)a;}
void S_StartSound(int e,int c,sfx_t *s,vec3_t o,float v,float a){(void)e;(void)c;(void)s;(void)o;(void)v;(void)a;}
sfx_t *S_PrecacheSound(char *s){(void)s;return NULL;}
sfxcache_t *S_LoadSound(sfx_t *s){(void)s;return NULL;}
edict_t *EDICT_NUM(int n){(void)n;return NULL;}
int NUM_FOR_EDICT(edict_t *e){(void)e;return 0;}

static void spawn(edict_t *e,int reset){
    memset(&sv,0,sizeof(sv));
    if(reset)AW_AnimSceneReset();
    sv.state=ss_loading;sv.worldmodel=&world;sv.models[1]=&world;sv.models[2]=&base;
    sv.model_precache[0]=strings;sv.model_precache[1]=world.name;sv.model_precache[2]=strings+1;
    memset(e,0,sizeof(*e));e->v.modelindex=2;e->v.model=1;
    AW_AnimPrep(e);sv.state=ss_active;
}
static void verify_mover(edict_t *e){
    const aw_anim_t *a;aw_anim_play_t p;int frame;
    assert(sv.model_precache[3] && !strcmp(sv.model_precache[3],"progs/resident_m.mdl"));
    assert(AW_AnimLazy("progs/resident_m.mdl") && !AW_AnimMoving(e));
    assert(AW_AnimMover(e,1) && AW_AnimMoving(e) && e->v.modelindex==3);
    a=AW_AnimOf(e);assert(a->from_layout && a->g[AW_ANIM_RUN].present && a->g[AW_ANIM_ATTACK].present);
    assert(a->g[AW_ANIM_RUN].base==12 && a->g[AW_ANIM_ATTACK].base==35);
    memset(&p,0,sizeof(p));p.group=255;
    frame=AW_AnimAdvance(a,&p,AW_ANIM_RUN,0,1,NULL);assert(frame==12);
    frame=AW_AnimAdvance(a,&p,AW_ANIM_RUN,.24f,1,NULL);assert(frame==13);
    frame=AW_AnimAdvance(a,&p,AW_ANIM_ATTACK,0,1,NULL);assert(frame==35);
    frame=AW_AnimAdvance(a,&p,AW_ANIM_ATTACK,.20f,1,NULL);assert(frame==36);
    assert(AW_AnimMover(e,0) && !AW_AnimMoving(e) && e->v.modelindex==2 && e->v.model==1);
}
int main(void){
    edict_t actor;int before;
    pr_strings=strings;strcpy(strings+1,"progs/resident.mdl");strcpy(world.name,"maps/same.bsp");strcpy(base.name,strings+1);strcpy(mover.name,"progs/resident_m.mdl");
    base.type=mod_alias;base.numframes=17;
    AW_AnimInit();spawn(&actor,1);verify_mover(&actor);assert(layouts==2 && loaded==1 && freed==1);
    /* Reproduce the old pointer-only guard: table/model pointers survive but
     * the new server bank has no mover; activation fails and stays reactive. */
    spawn(&actor,0);assert(!sv.model_precache[3]);assert(!AW_AnimMover(&actor,1));
    assert(actor.v.modelindex==2 && !AW_AnimOf(&actor)->g[AW_ANIM_RUN].present);
    /* The production reset restores registration on exactly the same world,
     * base and mover pointers; no converter change or eager model load. */
    before=loaded;spawn(&actor,1);assert(loaded==before);verify_mover(&actor);
    assert(layouts==4 && loaded==2 && freed==2);
    spawn(&actor,1);verify_mover(&actor);assert(layouts==6 && loaded==3 && freed==3);
    puts("PASS same-world reload: real mover registration, run/attack frames and release");return 0;
}
