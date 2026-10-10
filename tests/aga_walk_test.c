/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
#include <stdarg.h>
extern void AW_WalkPlayer(edict_t *);
extern int AW_TerrainFloor(edict_t *e,int player);
extern int (*aw_chim_floor)(const vec3_t origin,float *lowest,float *surface);
server_t sv;
int pr_edict_size=sizeof(edict_t);
static edict_t ground_entity;
static float slope, step, floor_z;
static int water, gravity_calls, walk_calls, absent,walk_movetype,land;
float frame_time=0.05f;
/* The CHIM terrain floor (chim_far.c) as the walk sees it: a ground plane
 * z = terrain_z + terrain_slope x, lowest height 64 below it. */
static int floor_on;static float terrain_z,terrain_slope;
static int fake_floor(const vec3_t o,float *lowest,float *surface){
 if(!floor_on)return 0;*surface=terrain_z+terrain_slope*o[0];*lowest=*surface-64;return 1;
}
static char console[2048];static int lines;
void Con_Printf(char *fmt,...){va_list ap;size_t n=strlen(console);va_start(ap,fmt);vsnprintf(console+n,sizeof console-n,fmt,ap);va_end(ap);lines++;}
qboolean SV_CheckWater(edict_t *p) {return water;}
void SV_CheckStuck(edict_t *p) {}
int SV_PointContents(vec3_t p) {return CONTENTS_EMPTY;}   /* no lava here (aw_walk.c feet_in_lava) */
void SV_LinkEdict(edict_t *p,qboolean touch){}
void SV_AddGravity(edict_t *p) {p->v.velocity[2]-=800*frame_time;gravity_calls++;}
void SV_WalkMove(edict_t *p) {
 walk_calls++;walk_movetype=p->v.movetype;VectorMA(p->v.origin,frame_time,p->v.velocity,p->v.origin);
 p->v.flags=(int)p->v.flags & ~FL_ONGROUND;
 /* land: a fall stops on the ground (only the terrain floor tests ask it) */
 if(land && !absent){float f=floor_z+slope*p->v.origin[0]+(p->v.origin[0]>1?step:0);
  if(p->v.origin[2]<f){p->v.origin[2]=f+0.03125f;p->v.velocity[2]=0;}}
}
trace_t SV_Move(vec3_t a,vec3_t mins,vec3_t maxs,vec3_t b,int kind,edict_t *skip) {
 trace_t t;float floor;memset(&t,0,sizeof t);t.fraction=1;VectorCopy(b,t.endpos);
 floor=floor_z+slope*a[0]+(a[0]>1?step:0);
 if(!absent && a[2]+0.0001f>=floor && b[2]<floor) {
  t.fraction=(a[2]-floor)/(a[2]-b[2]);VectorCopy(a,t.endpos);t.endpos[2]=floor+0.03125f;
  t.plane.normal[0]=-slope;t.plane.normal[2]=1;VectorNormalize(t.plane.normal);t.ent=&ground_entity;
 }
 return t;
}
/* CHIM terrain floor (CHIM-GRAFT-REPACK-EMPTY-33, second layer): with noclip
 * off the terrain is the lowest height. */
static void walk20(edict_t *p,float vx){int i;for(i=0;i<20;i++){p->v.velocity[0]=vx;AW_WalkPlayer(p);}}
static void terrain_floor(void){
 edict_t p,q;int i;float z;
 /* Normal walking is unchanged: the same uphill walk, cliff and jump with the
  * floor on (its ground exactly the world's) as with no floor. */
 water=0;absent=0;step=0;slope=.15f;floor_z=16.625f;
 memset(&p,0,sizeof p);p.v.movetype=MOVETYPE_WALK;p.v.origin[2]=floor_z;aw_chim_floor=NULL;walk20(&p,20);
 memset(&q,0,sizeof q);q.v.movetype=MOVETYPE_WALK;q.v.origin[2]=floor_z;
 aw_chim_floor=fake_floor;floor_on=1;terrain_z=floor_z;terrain_slope=slope;walk20(&q,20);
 assert(!memcmp(p.v.origin,q.v.origin,sizeof p.v.origin) && p.v.flags==q.v.flags && lines==0);
 slope=0;step=-20;
 memset(&p,0,sizeof p);p.v.movetype=MOVETYPE_WALK;p.v.origin[2]=floor_z;aw_chim_floor=NULL;walk20(&p,40);
 memset(&q,0,sizeof q);q.v.movetype=MOVETYPE_WALK;q.v.origin[2]=floor_z;terrain_slope=0;aw_chim_floor=fake_floor;walk20(&q,40);
 assert(!memcmp(p.v.origin,q.v.origin,sizeof p.v.origin) && lines==0);
 step=0;
 memset(&p,0,sizeof p);p.v.movetype=MOVETYPE_WALK;p.v.origin[2]=floor_z;p.v.velocity[2]=150;
 for(i=0;i<3;i++)AW_WalkPlayer(&p);assert(p.v.origin[2]>floor_z+5 && lines==0);
 /* The world is emptied under a standing player (the streamer lost its frame
  * world): one console line, lifted onto the terrain, then held there. */
 memset(&p,0,sizeof p);p.v.movetype=MOVETYPE_WALK;p.v.origin[2]=floor_z;terrain_z=floor_z;terrain_slope=0;
 AW_WalkPlayer(&p);assert((int)p.v.flags & FL_ONGROUND);
 absent=1;
 for(i=0;i<8;i++)AW_WalkPlayer(&p);
 assert(lines==1 && fabs(p.v.origin[2]-(terrain_z+1))<.001f && p.v.velocity[2]==0 && ((int)p.v.flags & FL_ONGROUND));
 assert(strstr(console,"Terrain floor: the player ") && strstr(console," units below the ground at ") &&
        strstr(console,", lifted onto it\n"));
 for(i=0;i<200;i++)AW_WalkPlayer(&p);
 assert(lines==1 && fabs(p.v.origin[2]-terrain_z)<.001f && ((int)p.v.flags & FL_ONGROUND) && p.v.groundentity==0);
 /* It walks on the terrain while the world is gone: uphill follows the ground. */
 terrain_slope=.1f;walk20(&p,20);
 assert(fabs(p.v.origin[0]-20)<.001f && fabs(p.v.origin[2]-(terrain_z+terrain_slope*p.v.origin[0]))<.01f && lines==1);
 /* A jump leaves it and comes back down onto it, without a new line. */
 terrain_slope=0;p.v.origin[2]=terrain_z;p.v.velocity[0]=0;p.v.velocity[2]=150;AW_WalkPlayer(&p);
 assert(p.v.origin[2]>terrain_z+5);
 for(i=0;i<40;i++){p.v.velocity[0]=0;AW_WalkPlayer(&p);}
 assert(fabs(p.v.origin[2]-terrain_z)<.001f && lines==1);
 /* The world comes back 20 units lower: the hold ends and it lands on the world. */
 absent=0;land=1;floor_z=terrain_z-20;
 for(i=0;i<40;i++){p.v.velocity[0]=0;AW_WalkPlayer(&p);}
 assert(fabs(p.v.origin[2]-(floor_z+0.03125f))<.04f && ((int)p.v.flags & FL_ONGROUND) && lines==1);
 floor_z=16.625f;land=0;
 /* The world's own ground wins, however low: standing or landing 100 below
  * the layer's ground is never lifted. */
 absent=0;land=1;floor_z=terrain_z-100;terrain_slope=0;
 memset(&p,0,sizeof p);p.v.movetype=MOVETYPE_WALK;p.v.origin[2]=terrain_z+10;
 for(i=0;i<60;i++){p.v.velocity[0]=0;AW_WalkPlayer(&p);}
 assert(fabs(p.v.origin[2]-(floor_z+0.03125f))<.04f && ((int)p.v.flags & FL_ONGROUND) && lines==1);
 floor_z=16.625f;land=0;
 /* Noclip and flight pass below the terrain. */
 memset(&p,0,sizeof p);p.v.movetype=MOVETYPE_NOCLIP;p.v.origin[2]=terrain_z-500;
 assert(!AW_TerrainFloor(&p,1) && p.v.origin[2]==terrain_z-500);
 p.v.movetype=MOVETYPE_FLY;assert(!AW_TerrainFloor(&p,1) && p.v.origin[2]==terrain_z-500 && lines==1);
 /* An actor's trial step never uses it (atomic: restored). */
 {
  vec3_t move={2,0,0};absent=1;memset(&p,0,sizeof p);p.v.origin[2]=terrain_z-100;p.v.flags=FL_ONGROUND;
  assert(!AW_ActorStep(&p,move,frame_time) && p.v.origin[2]==terrain_z-100 && p.v.origin[0]==0 && lines==1);
 }
 /* A body in free fall (SV_Physics_Step) is lifted too, with its own line. */
 memset(&p,0,sizeof p);p.v.movetype=MOVETYPE_STEP;p.v.origin[2]=terrain_z-100;p.v.velocity[2]=-300;
 assert(AW_TerrainFloor(&p,0) && fabs(p.v.origin[2]-(terrain_z+1))<.001f && p.v.velocity[2]==0);
 assert(((int)p.v.flags & FL_ONGROUND) && lines==2 && strstr(console,"Terrain floor: a body "));
 /* chim_terrain_floor 0 (no floor): the previous behaviour, a fall without end. */
 floor_on=0;memset(&p,0,sizeof p);p.v.movetype=MOVETYPE_WALK;p.v.origin[2]=terrain_z;
 for(i=0;i<60;i++)AW_WalkPlayer(&p);
 z=p.v.origin[2];assert(z<terrain_z-500 && lines==2);
 aw_chim_floor=NULL;absent=0;
}
int main(void) {
 edict_t p;int i;float start;memset(&p,0,sizeof p);sv.edicts=&ground_entity;
 ground_entity.v.solid=SOLID_BSP;slope=.15f;p.v.origin[2]=16.625f;floor_z=16.625f;
 for(i=0;i<300;i++)AW_WalkPlayer(&p);
 assert(p.v.origin[0]==0 && fabs(p.v.origin[2]-16.625f)<.04f);assert(!gravity_calls && !walk_calls);
 assert((int)p.v.flags & FL_ONGROUND);
 for(i=0;i<20;i++){p.v.velocity[0]=20;AW_WalkPlayer(&p);}
 assert(fabs(p.v.origin[0]-20)<.001f);assert(fabs(p.v.origin[2]-19.625f)<.04f);
 assert(p.v.velocity[2]==0 && !gravity_calls);
 /* Descending step follows ground; larger cliff must be free fall. */
 memset(&p,0,sizeof p);p.v.origin[2]=floor_z;slope=0;step=-4;p.v.velocity[0]=40;
 AW_WalkPlayer(&p);assert(fabs(p.v.origin[2]-(floor_z-4))<.04f);
 memset(&p,0,sizeof p);p.v.origin[2]=floor_z;step=-20;p.v.velocity[0]=40;
 AW_WalkPlayer(&p);assert(!((int)p.v.flags & FL_ONGROUND));start=p.v.origin[2];
 AW_WalkPlayer(&p);assert(p.v.origin[2]<start && gravity_calls==1);
 /* Jump is never snapped back, even directly over the floor. */
 memset(&p,0,sizeof p);p.v.origin[2]=floor_z;step=0;p.v.velocity[2]=150;
 AW_WalkPlayer(&p);assert(p.v.origin[2]>floor_z+5 && gravity_calls==2);
 water=1;p.v.velocity[2]=0;AW_WalkPlayer(&p);assert(gravity_calls==2);
 /* Scripted actors share walking but must reject unsupported drops atomically. */
 {
  vec3_t move={2,0,0};water=0;step=-20;memset(&p,0,sizeof(p));p.v.origin[2]=floor_z;p.v.oldorigin[0]=7;p.v.velocity[0]=9;p.v.flags=FL_ONGROUND;
  assert(!AW_ActorStep(&p,move,frame_time));assert(p.v.origin[0]==0 && p.v.origin[2]==floor_z && p.v.oldorigin[0]==7 && p.v.velocity[0]==9 && p.v.flags==FL_ONGROUND);
  step=-4;assert(AW_ActorStep(&p,move,frame_time));assert(fabs(p.v.origin[0]-2)<.001f && fabs(p.v.origin[2]-(floor_z-4))<.04f);
  assert(walk_movetype==MOVETYPE_WALK && p.v.movetype==MOVETYPE_NONE);
 }
 /* Hlaalu's authored stair ramp is just steeper than Quake's old .7 cutoff.
  * It must hold an idle walker and preserve uphill speed in both directions. */
 water=0;step=0;slope=1.02669f;gravity_calls=0;
 memset(&p,0,sizeof p);p.v.origin[2]=floor_z;p.v.movetype=MOVETYPE_WALK;
 for(i=0;i<30;i++)AW_WalkPlayer(&p);
 assert(!gravity_calls && ((int)p.v.flags & FL_ONGROUND));
 for(i=0;i<20;i++){p.v.velocity[0]=20;AW_WalkPlayer(&p);}
 assert(fabs(p.v.origin[0]-20)<.001f && fabs(p.v.origin[2]-(floor_z+20*slope))<.04f);
 for(i=0;i<20;i++){p.v.velocity[0]=-20;AW_WalkPlayer(&p);}
 assert(fabs(p.v.origin[0])<.001f && fabs(p.v.origin[2]-floor_z)<.04f);
 slope=1.2f;memset(&p,0,sizeof p);p.v.origin[2]=floor_z;gravity_calls=0;
 AW_WalkPlayer(&p);assert(gravity_calls==1 && !((int)p.v.flags & FL_ONGROUND));
 terrain_floor();
 puts("idle slope, uphill speed, descending step, cliff, jump, swimming and terrain floor passed");return 0;
}
