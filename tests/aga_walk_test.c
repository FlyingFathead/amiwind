/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
extern void AW_WalkPlayer(edict_t *);
server_t sv;
int pr_edict_size=sizeof(edict_t);
static edict_t ground_entity;
static float slope, step, floor_z;
static int water, gravity_calls, walk_calls, absent;
float frame_time=0.05f;
qboolean SV_CheckWater(edict_t *p) {return water;}
void SV_CheckStuck(edict_t *p) {}
void SV_AddGravity(edict_t *p) {p->v.velocity[2]-=800*frame_time;gravity_calls++;}
void SV_WalkMove(edict_t *p) {
 walk_calls++;VectorMA(p->v.origin,frame_time,p->v.velocity,p->v.origin);
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
 puts("idle slope, uphill speed, descending step, cliff, jump and swimming passed");return 0;
}
