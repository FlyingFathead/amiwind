/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
extern void AW_WalkPlayer(edict_t *);
server_t sv;
int pr_edict_size=sizeof(edict_t);
static edict_t ground_entity;
static float slope, step, floor_z;
static int water, gravity_calls, walk_calls, absent,walk_movetype;
float frame_time=0.05f;
qboolean SV_CheckWater(edict_t *p) {return water;}
void SV_CheckStuck(edict_t *p) {}
void SV_LinkEdict(edict_t *p,qboolean touch){}
void SV_AddGravity(edict_t *p) {p->v.velocity[2]-=800*frame_time;gravity_calls++;}
void SV_WalkMove(edict_t *p) {
 walk_calls++;walk_movetype=p->v.movetype;VectorMA(p->v.origin,frame_time,p->v.velocity,p->v.origin);
 p->v.flags=(int)p->v.flags & ~FL_ONGROUND;
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
 puts("idle slope, uphill speed, descending step, cliff, jump and swimming passed");return 0;
}
