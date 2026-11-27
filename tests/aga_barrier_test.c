/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_story.h"
#include <assert.h>
server_t sv;server_static_t svs;
static float identity(float f){return f;}
float (*LittleFloat)(float)=identity;
/* OPENING-BARRIERS-PER-BOX-68: the world change list's answer, the map transform and the image's world-barriers.txt
 * (aw_barrier.c world_read_file), as the engine gives them */
static unsigned int disabled_ref;
int AW_ObjectDisabled(unsigned int reference){return disabled_ref && reference==disabled_ref;}
int AW_SourceToWorld(const char *name,const float *world,float *local){
    int i;if(strcmp(name,"seyda") && strcmp(name,"mh"))return 0;
    for(i=0;i<3;i++)local[i]=world[i]*.25f;
    return 1;
}
static const char *file_text;
int COM_FOpenFile(char *name,FILE **file){
    FILE *f;(void)name;
    *file=NULL;
    if(!file_text || !(f=tmpfile()))return -1;
    fputs(file_text,f);rewind(f);*file=f;
    return (int)strlen(file_text);
}
void AW_BarrierServerReset(void);
int AW_BarrierTouching(unsigned int reference);
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
    /* OPENING-BARRIERS-PER-BOX-68: the opening's box with its reference from world-barriers.txt traces exactly as
     * without it while no script touched it (the same sweep: the same fraction and normal as at the top), and stops
     * clipping in the server frame after a script's Disable of that reference; its story gate is unchanged */
    { trace_t before,after;
      put(raw,3,1);put(raw,4,0);put(raw,6,0);put(raw,7,1);assert(AW_BarrierDecode(raw,sizeof(raw)));
      a[0]=-10;a[1]=a[2]=0;b[0]=10;b[1]=b[2]=0;AW_StoryReset(1);strcpy(sv.name,"seyda");sv.time=1;
      before=check(a,b,&p);
      file_text="AWWB1\nopening 1 445155\nship 0\n";AW_BarrierServerReset();sv.time=2;
      after=check(a,b,&p);
      assert(before.fraction>.36 && before.fraction<.38);
      assert(after.fraction==before.fraction && after.plane.normal[0]==before.plane.normal[0] &&
             after.startsolid==before.startsolid && after.endpos[0]==before.endpos[0]);
      disabled_ref=445155;after=check(a,b,&p);assert(after.fraction<1);   /* the bits are read once a server frame */
      sv.time=3;after=check(a,b,&p);assert(after.fraction==1);
      disabled_ref=0;sv.time=4;after=check(a,b,&p);assert(after.fraction==before.fraction);
      /* a count that is not the table's: the references are left out, the box stays on */
      file_text="AWWB1\nopening 2 445155 445156\nship 0\n";AW_BarrierServerReset();disabled_ref=445155;sv.time=5;
      after=check(a,b,&p);assert(after.fraction==before.fraction);
      disabled_ref=0;
    }
    /* INVISIBLE-WALLS-NOT-BUILT-68: a world box (Mournhold's lid kind: no story gate, walking or levitating) on the map
     * that holds it, swept as the opening's; met, it answers GetCollidingPC; disabled, it is gone; on another map none */
    { vec3_t lo={-.5,-.5,-.5},hi={.5,.5,.5};
      file_text="AWWB1\nopening 0\nship 0\nbox 4218700 400.000 0.000 0.000 1 0 0 0 1 0 0 0 1 4.000 4.000 4.000\n";
      AW_BarrierServerReset();AW_StateSet(&aw_state,AW_GLOBAL,"CharGenState",-1);strcpy(sv.name,"mh");sv.time=6;
      a[0]=90;a[1]=a[2]=0;b[0]=110;b[1]=b[2]=0;
      t=check(a,b,&p);assert(t.fraction>.40 && t.fraction<.45 && t.plane.normal[0]==-1);
      assert(AW_BarrierTouching(4218700) && !AW_BarrierTouching(4218701));
      p.v.movetype=MOVETYPE_FLY;memset(&t,0,sizeof(t));t.fraction=1;AW_BarrierClip(a,lo,hi,b,&p,&t);assert(t.fraction<.45);
      p.v.movetype=MOVETYPE_WALK;sv.time=6.5;assert(!AW_BarrierTouching(4218700));   /* a tenth of a second at most */
      disabled_ref=4218700;sv.time=7;t=check(a,b,&p);assert(t.fraction==1);
      disabled_ref=0;strcpy(sv.name,"prison2");sv.time=8;t=check(a,b,&p);assert(t.fraction==1);   /* not on this map */
      file_text=NULL;AW_BarrierServerReset();strcpy(sv.name,"mh");sv.time=9;t=check(a,b,&p);assert(t.fraction==1);
    }
    /* DROP-REFUSED-CENSUS-ROOM-67: a drop's point path (AW_BarrierPointBlocked, the inventory's drop ahead) meets the
     * boxes the walking player meets, which AW_BarrierClip leaves alone for a point: the world's on their own map, the
     * opening's while the story holds; it marks no box as met (GetCollidingPC is the player's own touch) */
    { vec3_t c={90,0,0},d={110,0,0},e={90,20,0},f={110,20,0},g={-10,0,0},h={10,0,0};
      sv.active=1;
      file_text="AWWB1\nopening 0\nship 0\nbox 4218700 400.000 0.000 0.000 1 0 0 0 1 0 0 0 1 4.000 4.000 4.000\n";
      AW_BarrierServerReset();AW_StateSet(&aw_state,AW_GLOBAL,"CharGenState",-1);strcpy(sv.name,"mh");sv.time=10;
      assert(AW_BarrierPointBlocked(c,d) && !AW_BarrierPointBlocked(e,f) && !AW_BarrierTouching(4218700));
      strcpy(sv.name,"prison2");sv.time=11;assert(!AW_BarrierPointBlocked(c,d));
      /* the opening's box on the dock (the decoded table above, at the map's origin): while the story holds only */
      AW_StoryReset(1);strcpy(sv.name,"seyda");sv.time=12;assert(AW_BarrierPointBlocked(g,h));
      AW_StateSet(&aw_state,AW_GLOBAL,"CharGenState",-1);sv.time=13;assert(!AW_BarrierPointBlocked(g,h));
      sv.active=0;assert(!AW_BarrierPointBlocked(g,h));
      file_text=NULL;AW_BarrierServerReset();
    }
    return 0;
}
