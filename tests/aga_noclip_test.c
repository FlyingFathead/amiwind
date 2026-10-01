/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
/* Engine vector math uses approximate reciprocal square root; validate the
 * speed envelope to 0.5%, not an unrealistic bit-exact floating-point result. */
static float magnitude(vec3_t v) {return sqrt(v[0]*v[0]+v[1]*v[1]+v[2]*v[2]);}
int main(void) {
 vec3_t view={-60,90,0},out;usercmd_t cmd;
 memset(&cmd,0,sizeof(cmd));cmd.forwardmove=120;
 AW_NoclipVelocity(view,&cmd,320,out);
 assert(out[2]>100 && out[1]>59 && fabs(magnitude(out)-120)<.6);
 view[0]=60;AW_NoclipVelocity(view,&cmd,320,out);assert(out[2]<-100);
 view[0]=0;cmd.sidemove=120;AW_NoclipVelocity(view,&cmd,320,out);
 assert(fabs(magnitude(out)-120)<.6);
 cmd.forwardmove=216;cmd.sidemove=0;AW_NoclipVelocity(view,&cmd,320,out);
 assert(fabs(magnitude(out)-216)<1.08);
 cmd.forwardmove=0;cmd.upmove=200;view[0]=80;
 AW_NoclipVelocity(view,&cmd,320,out);assert(fabs(out[2]-200)<1 && !out[0] && !out[1]);
 cmd.upmove=-200;AW_NoclipVelocity(view,&cmd,320,out);assert(fabs(out[2]+200)<1);
 memset(&cmd,0,sizeof(cmd));AW_NoclipVelocity(view,&cmd,320,out);assert(magnitude(out)==0);
 cmd.forwardmove=2000;AW_NoclipVelocity(view,&cmd,320,out);assert(fabs(magnitude(out)-320)<1.6);
 /* Ctrl equals twice Shift after the ordinary diagonal/cap rules. */
 memset(&cmd,0,sizeof(cmd));view[0]=0;cmd.forwardmove=120;cmd.sidemove=120;
 AW_NoclipDebugVelocity(view,&cmd,320,1,0,1.8,out);assert(fabs(magnitude(out)-432)<2.16);
 cmd.forwardmove=216;cmd.sidemove=216;
 AW_NoclipDebugVelocity(view,&cmd,320,1,1,1.8,out);assert(fabs(magnitude(out)-432)<2.16);
 cmd.forwardmove=cmd.sidemove=0;cmd.upmove=200;
 AW_NoclipDebugVelocity(view,&cmd,320,1,0,1.8,out);assert(fabs(out[2]-640)<3.2);
 AW_NoclipDebugVelocity(view,&cmd,320,0,0,1.8,out);assert(fabs(out[2]-200)<1);
 memset(&cmd,0,sizeof(cmd));AW_NoclipDebugVelocity(view,&cmd,320,1,0,1.8,out);assert(magnitude(out)==0);
 return 0;
}
