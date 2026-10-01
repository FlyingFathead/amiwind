/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <stdarg.h>
#include <assert.h>
#include <sys/resource.h>
extern qboolean SV_RecursiveHullCheck(hull_t *,int,float,float,vec3_t,vec3_t,trace_t *);
server_t sv;
extern void AW_MergeCollisionTrace(trace_t *,trace_t *,edict_t *);
extern trace_t SV_ClipMoveToEntity(edict_t *,vec3_t,vec3_t,vec3_t,vec3_t);
void Sys_Error(char *fmt,...) {va_list ap;va_start(ap,fmt);vfprintf(stderr,fmt,ap);va_end(ap);exit(1);}
void Con_DPrintf(char *fmt,...) {}
int main(void) {
 model_t model;edict_t ent;mplane_t planes[6];dclipnode_t nodes[6];
 vec3_t mins={-16,-16,-24},maxs={16,16,32},a={0,80,80},b={0,80,-40};trace_t hit;int i;
 memset(&model,0,sizeof model);memset(&ent,0,sizeof ent);memset(planes,0,sizeof planes);
 /* Thin platform from local x=40..120, y=-5..5, z=0..4, expanded for player. */
 for(i=0;i<6;i++) {
  planes[i].normal[i/2]=(i&1)?-1:1;planes[i].type=3;
  nodes[i].planenum=i;nodes[i].children[0]=CONTENTS_EMPTY;
  nodes[i].children[1]=i==5?CONTENTS_SOLID:i+1;
 }
 planes[0].dist=136;planes[1].dist=-24;planes[2].dist=21;planes[3].dist=21;
 planes[4].dist=28;planes[5].dist=32;
 model.type=mod_brush;model.hulls[1].planes=planes;model.hulls[1].clipnodes=nodes;
 model.hulls[1].firstclipnode=0;model.hulls[1].lastclipnode=5;VectorCopy(mins,model.hulls[1].clip_mins);
 sv.models[1]=&model;ent.v.modelindex=1;ent.v.solid=SOLID_BSP;ent.v.movetype=MOVETYPE_PUSH;
 ent.v.angles[1]=90;
 hit=SV_ClipMoveToEntity(&ent,a,mins,maxs,b);
 if(hit.fraction==1 || fabs(hit.endpos[2]-28)>.1 || hit.plane.normal[2]<.99) {
  fprintf(stderr,"rotated platform missed: fraction=%f z=%f\n",hit.fraction,hit.endpos[2]);return 1;
 }
 /* A fully blocked move must not return a destination below the start. */
 a[0]=0;a[1]=80;a[2]=0;b[0]=0;b[1]=80;b[2]=-10;
 hit=SV_ClipMoveToEntity(&ent,a,mins,maxs,b);
 assert(hit.allsolid && hit.startsolid && hit.fraction==0);
 assert(hit.endpos[0]==a[0] && hit.endpos[1]==a[1] && hit.endpos[2]==a[2]);
 a[2]=80;b[2]=-40;
 a[0]=80;a[1]=0;b[0]=80;b[1]=0;hit=SV_ClipMoveToEntity(&ent,a,mins,maxs,b);
 assert(hit.fraction==1); /* Former invisible collider must no longer exist. */
 {
  /* Overlapping translated brush partitions used to spend the contact margin
   * on the inner split, returning a point inside the outer platform. The next
   * frame's stuck recovery then silently undid otherwise successful walking. */
  trace_t standing;
  memset(&ent,0,sizeof(ent));ent.v.modelindex=1;ent.v.solid=SOLID_BSP;ent.v.movetype=MOVETYPE_PUSH;
  ent.v.origin[2]=37.59418f;
  for(i=0;i<2;i++){
   memset(&planes[i],0,sizeof(planes[i]));planes[i].type=2;planes[i].normal[2]=1;
   nodes[i].planenum=i;nodes[i].children[1]=CONTENTS_SOLID;
  }
  planes[0].dist=50.828125f;planes[1].dist=50.859375f;
  nodes[0].children[0]=1;nodes[1].children[0]=CONTENTS_EMPTY;
  model.hulls[1].lastclipnode=1;
  a[0]=b[0]=0;a[1]=b[1]=0;a[2]=89;b[2]=87;
  hit=SV_ClipMoveToEntity(&ent,a,mins,maxs,b);
  assert(!hit.startsolid && hit.fraction>0 && hit.fraction<1);
  assert(hit.endpos[2]>88.47f && hit.endpos[2]<88.50f && hit.plane.normal[2]>.99f);
  standing=SV_ClipMoveToEntity(&ent,hit.endpos,mins,maxs,hit.endpos);
  assert(!standing.startsolid && !standing.allsolid);
  /* A sweep starting inside may exit the union; never fabricate a surface. */
  standing=SV_ClipMoveToEntity(&ent,b,mins,maxs,a);
  assert(standing.startsolid && !standing.allsolid && standing.fraction==1);
 }
 {
  trace_t floor,exit;
  memset(&floor,0,sizeof floor);memset(&exit,0,sizeof exit);
  floor.fraction=.4;floor.endpos[2]=24;floor.plane.normal[2]=1;
  exit.fraction=1;exit.startsolid=true;exit.endpos[2]=-505;
  AW_MergeCollisionTrace(&floor,&exit,&ent);
  assert(floor.fraction==.4f && floor.endpos[2]==24 && floor.startsolid);
  exit.fraction=.2;exit.endpos[2]=100;
  AW_MergeCollisionTrace(&floor,&exit,&ent);
  assert(floor.fraction==.2f && floor.endpos[2]==100 && floor.startsolid);
 }
 {
  static dclipnode_t chain[50000];hull_t hull;trace_t tr;mplane_t plane;vec3_t p={1,0,0},q={2,0,0};
  struct rlimit limit;getrlimit(RLIMIT_STACK,&limit);limit.rlim_cur=262144;assert(!setrlimit(RLIMIT_STACK,&limit));
  memset(&hull,0,sizeof(hull));memset(&tr,0,sizeof(tr));memset(&plane,0,sizeof(plane));
  plane.normal[0]=1;plane.type=0;
  for(i=0;i<50000;i++){chain[i].planenum=0;chain[i].children[0]=i==49999?CONTENTS_EMPTY:i+1;chain[i].children[1]=CONTENTS_SOLID;}
  hull.clipnodes=chain;hull.planes=&plane;hull.lastclipnode=49999;tr.allsolid=true;tr.fraction=1;
  assert(SV_RecursiveHullCheck(&hull,0,0,1,p,q,&tr));assert(!tr.allsolid && !tr.startsolid);
 }
 {
  /* Resident slideboxes must block the scaled player's swept volume in every
   * horizontal direction, but leave a route around the actor. */
  extern void SV_InitBoxHull(void);
  vec3_t pmin={-7.32f,-7.12f,-16.625f},pmax={7.32f,7.12f,16.625f};
  int axis,sign;
  SV_InitBoxHull();memset(&ent,0,sizeof(ent));ent.v.solid=SOLID_SLIDEBOX;
  ent.v.mins[0]=-7.32f;ent.v.mins[1]=-7.12f;
  ent.v.maxs[0]=7.32f;ent.v.maxs[1]=7.12f;ent.v.maxs[2]=33.25f;
  for(axis=0;axis<2;axis++)for(sign=-1;sign<=1;sign+=2){
   VectorCopy(vec3_origin,a);VectorCopy(vec3_origin,b);a[2]=b[2]=16.875f;
   a[axis]=sign*40;b[axis]=-sign*40;
   hit=SV_ClipMoveToEntity(&ent,a,pmin,pmax,b);
   assert(!hit.startsolid && hit.fraction>0 && hit.fraction<.5f);
   assert(fabs(hit.endpos[axis])>=14.2f);
   a[1-axis]=b[1-axis]=24;
   hit=SV_ClipMoveToEntity(&ent,a,pmin,pmax,b);assert(hit.fraction==1);
  }
 }
 puts("rotated platform hit and vacated-space sweep passed");return 0;
}
