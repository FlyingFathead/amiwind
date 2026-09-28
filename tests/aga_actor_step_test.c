/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
server_t sv;static edict_t edicts[2];static float raised;
extern qboolean SV_movestep(edict_t *,vec3_t,qboolean);
void SV_LinkEdict(edict_t *e,qboolean touch){}
int SV_PointContents(vec3_t p){return p[2]<(p[0]>=10?raised:0)?CONTENTS_SOLID:CONTENTS_EMPTY;}
trace_t SV_Move(vec3_t a,vec3_t mi,vec3_t ma,vec3_t b,int type,edict_t *e){
    float floor=b[0]>=10?raised:0;trace_t t;memset(&t,0,sizeof(t));t.fraction=1;t.ent=&edicts[0];VectorCopy(b,t.endpos);
    if(a[2]<floor){t.allsolid=t.startsolid=true;t.fraction=0;return t;}
    if(b[2]<floor){t.fraction=(a[2]-floor)/(a[2]-b[2]);t.endpos[2]=floor;t.plane.normal[2]=1;}
    return t;
}
int main(void){
    edict_t *e=&edicts[1];vec3_t move={2,0,0};sv.edicts=edicts;
    e->v.mins[0]=e->v.mins[1]=-.25;e->v.maxs[0]=e->v.maxs[1]=.25;e->v.maxs[2]=33.25;
    e->v.origin[0]=9;raised=8;assert(SV_movestep(e,move,true));assert(e->v.origin[0]==11 && e->v.origin[2]==8);
    e->v.origin[0]=9;e->v.origin[2]=0;raised=9;assert(!SV_movestep(e,move,true));assert(e->v.origin[0]==9 && e->v.origin[2]==0);
    return 0;
}
