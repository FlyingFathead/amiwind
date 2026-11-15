/* SPDX-License-Identifier: GPL-2.0-or-later
 * CAST-EGG-SYNC-62: the look of a cast starts with the cast animation and leaves with the spell. The frame walk below
 * follows aw_magic.c's update (t0 = t1 - dt, -1 on a look's first frame) and aw_cast.c's release (sv.time >=
 * release_at): the cast sound, the hand glow and the shell start on the press frame, and the look's bolt, touch or
 * self hit starts on the frame the spell leaves, for every kind of spell (self, touch, target, summon). Built with
 * aw_magic_rules.c only. */
#include <stdio.h>
#include "../engine/aga/src/aw_magic.h"

static int failures;
#define CHECK(c) do{if(!(c)){printf("FAIL %s:%d %s\n",__FILE__,__LINE__,#c);failures++;}}while(0)

/* one cast whose spell leaves DELAY seconds after the press, frames of DT seconds; the press on frame PRESS */
static void walk(const char *kind,float delay,float dt,int press) {
    int frame,anim=0,sound=0,shell=0,glow=0,spell=0,look=0,started=0;float now=0,release_at=0,start=0,
        release=AW_MAGIC_HELD_RELEASE,t0,t1;
    for(frame=1;frame<200;frame++){
        now+=dt;
        if(frame==press){anim=frame;start=now;release_at=now+delay;started=1;}   /* cast_now: animation + look start */
        if(started && !spell && now>=release_at){spell=frame;release=AW_MagicCastRelease(now-start);}   /* cast_release */
        if(started){   /* AW_MagicUpdate, later in the same host frame */
            t1=now-start;t0=t1-dt;if(t0<0)t0=-1;
            (void)t0;
            if(AW_MagicStartDue(sound!=0,t1)){sound=frame;shell=frame;glow=frame;}
            if(!look && t1>=release)look=frame;
        }
        if(look)break;
    }
    CHECK(AW_MagicInSync(anim,sound,shell));
    CHECK(glow==anim);
    CHECK(look==spell && spell>anim);
    if(failures)printf("  %s: anim %d sound %d shell %d spell %d look %d\n",kind,anim,sound,shell,spell,look);
}

int main(void) {
    int fps[3]={50,25,12},i;
    /* a frame takes everything due in it, once */
    CHECK(AW_MagicDue(-1,0,0) && AW_MagicDue(-1,.02f,0) && !AW_MagicDue(.02f,.04f,0) && AW_MagicDue(.5f,.6f,.6f));
    CHECK(!AW_MagicDue(.6f,.7f,.6f));
    CHECK(AW_MagicCastRelease(-.1f)==0 && AW_MagicCastRelease(.6f)==.6f);
    CHECK(!AW_MagicInSync(0,0,0) && !AW_MagicInSync(3,3,4) && AW_MagicInSync(7,7,7));
    CHECK(AW_MAGIC_HELD_RELEASE>AW_MAGIC_HELD_MAX);
    /* the start phases once: never again on a later frame whose age rounds around 0 */
    CHECK(AW_MagicStartDue(0,0) && !AW_MagicStartDue(1,0) && !AW_MagicStartDue(1,.02f) && !AW_MagicStartDue(0,-.01f));
    /* the hands' cast release (6 of 10 frames of the cast clip) and the spellcast groups' self / touch / target /
     * summon (self) releases, at 50, 25 and 12 frames a second */
    for(i=0;i<3;i++){
        float dt=1.0f/fps[i];
        walk("self",.6f,dt,3);walk("touch",.45f,dt,4);walk("target",.6f,dt,5);walk("summon",.6f,dt,6);
    }
    if(failures)return 1;
    printf("cast sync: 6 rule checks and 12 walks passed\n");
    return 0;
}
