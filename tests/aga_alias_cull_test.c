/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "r_local.h"
#include <assert.h>
clipplane_t view_clipplanes[4];
extern qboolean AW_AliasSphereVisible(vec3_t,float);
int main(void) {
 vec3_t p={0,0,0};int i;
 memset(view_clipplanes,0,sizeof(view_clipplanes));
 for(i=0;i<4;i++)view_clipplanes[i].dist=-10;
 view_clipplanes[0].normal[0]=1;view_clipplanes[1].normal[0]=-1;
 view_clipplanes[2].normal[1]=1;view_clipplanes[3].normal[1]=-1;
 assert(AW_AliasSphereVisible(p,2));
 for(i=0;i<2;i++){
  p[i]=12;assert(AW_AliasSphereVisible(p,2));
  p[i]=12.01;assert(!AW_AliasSphereVisible(p,2));
  p[i]=-12;assert(AW_AliasSphereVisible(p,2));
  p[i]=-12.01;assert(!AW_AliasSphereVisible(p,2));p[i]=0;
 }
 p[0]=100;assert(AW_AliasSphereVisible(p,0)); /* Unknown bound cannot cull. */
 return 0;
}
