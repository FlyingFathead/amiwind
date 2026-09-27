/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
#include <stdarg.h>
extern qboolean AW_FindSafeSpawn(edict_t *,vec3_t,vec3_t);
extern qboolean AW_PlacePlayer(edict_t *,vec3_t);
static int unavailable;
void Con_Printf(char *fmt,...) {}
void SV_LinkEdict(edict_t *p,qboolean touch) {}
/* Synthetic standing-hull space: floor at z=24 and an expanded block around
 * the preferred point. A narrow ledge on its top must fail exit clearance. */
static int solid(vec3_t p) {
 return unavailable || p[2]<24 || (fabs(p[0])<24 && fabs(p[1])<24 && p[2]<72);
}
trace_t SV_Move(vec3_t a,vec3_t mins,vec3_t maxs,vec3_t b,int kind,edict_t *skip) {
 trace_t t;int i;float u,previous=0;vec3_t p;
 memset(&t,0,sizeof t);t.fraction=1;VectorCopy(b,t.endpos);
 t.startsolid=solid(a);t.allsolid=t.startsolid;
 for(i=0;i<=1024;i++) {
  u=i/1024.f;VectorMA(a,u,((float[3]){b[0]-a[0],b[1]-a[1],b[2]-a[2]}),p);
  if(!solid(p))t.allsolid=false;
  else if(i && !t.startsolid) {
   t.fraction=previous;
   t.endpos[0]=a[0]+previous*(b[0]-a[0]);
   t.endpos[1]=a[1]+previous*(b[1]-a[1]);
   t.endpos[2]=a[2]+previous*(b[2]-a[2]);
   t.plane.normal[2]=1;break;
  }
  previous=u;
 }
 if(t.allsolid){t.fraction=0;VectorCopy(a,t.endpos);}
 return t;
}
int main(void) {
 edict_t p;vec3_t preferred={0,0,48},out={999,999,999},saved;memset(&p,0,sizeof p);
 p.v.mins[0]=p.v.mins[1]=-16;p.v.mins[2]=-24;
 p.v.maxs[0]=p.v.maxs[1]=16;p.v.maxs[2]=32;
 assert(AW_FindSafeSpawn(&p,preferred,out));
 assert(out[2]>24 && out[2]<25);assert(fabs(out[0])>=32 || fabs(out[1])>=32);
 assert(!solid(out));assert(AW_PlacePlayer(&p,preferred));
 assert(p.v.origin[2]==p.v.oldorigin[2]);
 VectorCopy(p.v.origin,saved);unavailable=1;
 assert(!AW_PlacePlayer(&p,preferred));assert(!memcmp(saved,p.v.origin,sizeof saved));
 puts("blocked spawn, ledge rejection, grounded recovery and no-solution preservation passed");return 0;
}
