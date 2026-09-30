/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_story.h"
#include <assert.h>
server_t sv;server_static_t svs;
static float identity(float f){return f;}
float (*LittleFloat)(float)=identity;
static void put(byte *raw,int index,float value){memcpy(raw+6+index*4,&value,4);}
static trace_t check(vec3_t a,vec3_t b,edict_t *p)
{
    vec3_t lo={-.5,-.5,-.5},hi={.5,.5,.5};trace_t t;
    memset(&t,0,sizeof(t));t.fraction=1;VectorCopy(b,t.endpos);AW_BarrierClip(a,lo,hi,b,p,&t);return t;
}
int main(void)
{
    byte raw[66];edict_t p,w;client_t client;trace_t t;int stage;vec3_t a={-10,0,0},b={10,0,0};
    memset(raw,0,sizeof(raw));memcpy(raw,"AWB1",4);raw[4]=1;
    put(raw,3,1);put(raw,7,1);put(raw,11,1);put(raw,12,2);put(raw,13,2);put(raw,14,2);
    assert(AW_BarrierDecode(raw,sizeof(raw)));assert(!AW_BarrierDecode(raw,sizeof(raw)-1));assert(AW_BarrierDecode(raw,sizeof(raw)));
    memset(&p,0,sizeof(p));client.edict=&p;svs.clients=&client;sv.edicts=&w;strcpy(sv.name,"seyda");p.v.movetype=MOVETYPE_WALK;
    AW_StoryReset(1);t=check(a,b,&p);assert(t.fraction>.36 && t.fraction<.38 && t.plane.normal[0]==-1);
    /* A new map/menu stage does not release the authored enclosure. The
     * global condition survives race, office, courtyard and captain stages. */
    for(stage=AW_STAGE_DOCK;stage<=AW_STAGE_CAPTAIN;stage++){
        aw_story.stage=stage;t=check(a,b,&p);assert(t.fraction<1);
    }
    AW_StoryReset(1);
    a[1]=b[1]=4;t=check(a,b,&p);assert(t.fraction==1);
    put(raw,3,.70710678);put(raw,4,.70710678);put(raw,6,-.70710678);put(raw,7,.70710678);
    assert(AW_BarrierDecode(raw,sizeof(raw)));a[1]=b[1]=0;t=check(a,b,&p);assert(t.fraction>.32 && t.fraction<.34);
    a[0]=a[1]=a[2]=0;t=check(a,b,&p);assert(t.startsolid && !t.allsolid);
    b[0]=0;t=check(a,b,&p);assert(t.startsolid && t.allsolid && t.fraction==0);
    AW_StateSet(&aw_state,AW_GLOBAL,"CharGenState",-1);t=check(a,b,&p);assert(t.fraction==1 && !t.startsolid);
    AW_StoryReset(1);p.v.movetype=MOVETYPE_NOCLIP;t=check(a,b,&p);assert(t.fraction==1);
    /* Continuous pier sides, shore end and stage release; use the real hull. */
    AW_StoryReset(1);aw_story.stage=AW_STAGE_DOCK;p.v.movetype=MOVETYPE_WALK;
    { vec3_t lo={-7.32,-7.12,-16.625},hi={7.32,7.12,16.625};int side;
      for(side=-1;side<=1;side+=2){
        a[0]=474.29012;a[1]=-293.06688;a[2]=50;
        b[0]=a[0]+side*100*.5403344;b[1]=a[1]+side*100*.8414506;b[2]=50;
        memset(&t,0,sizeof(t));t.fraction=1;AW_BarrierClip(a,lo,hi,b,&p,&t);
        assert(!t.startsolid && t.fraction>0 && t.fraction<.3);
      }
      a[0]=587.5;a[1]=-353.25;b[0]=330;b[1]=-200.25;
      memset(&t,0,sizeof(t));t.fraction=1;AW_BarrierClip(a,lo,hi,b,&p,&t);
      assert(t.fraction==1 && !t.startsolid);
      b[0]=280;b[1]=-166;
      memset(&t,0,sizeof(t));t.fraction=1;AW_BarrierClip(a,lo,hi,b,&p,&t);assert(t.fraction<1);
      aw_story.ship_disabled=1;
      memset(&t,0,sizeof(t));t.fraction=1;AW_BarrierClip(a,lo,hi,b,&p,&t);assert(t.fraction==1);
    }
    put(raw,3,NAN);assert(!AW_BarrierDecode(raw,sizeof(raw)));p.v.movetype=MOVETYPE_WALK;t=check(a,b,&p);assert(t.fraction==1);
    return 0;
}
