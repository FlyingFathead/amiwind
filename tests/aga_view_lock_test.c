/* SPDX-License-Identifier: GPL-2.0-or-later */
/* dbg setpov (aw_view_rules.c AW_ViewLock; FP-TORCH-HAND-REGRESSION-67): a locked view survives the idle vanity timer,
 * Toggle POV and the wheel; a locked vanity orbit keeps turning; off gives the rules back (the idle orbit starts again). */
#include <assert.h>
#include <stdio.h>
#include "aw_view.h"

int main(void) {
    aw_view_rules_t r;aw_view_t v;int i;
    AW_ViewRulesDefault(&r);AW_ViewReset(&v,&r);
    assert(AW_ViewLockedMode(&v)==-1 && v.mode==AW_VIEW_FIRST);
    /* the rules as they are: idle past fVanityDelay starts the orbit */
    for(i=0;i<(int)(r.vanity_delay*10)+20;i++)AW_ViewIdle(&v,&r,0,1,.1f);
    assert(v.mode==AW_VIEW_VANITY);
    AW_ViewIdle(&v,&r,1,1,.1f);assert(v.mode==AW_VIEW_FIRST);
    /* setpov 1: first person, held through ten times the idle delay, a Toggle POV tap, a long press and the wheel */
    AW_ViewLock(&v,AW_VIEW_FIRST);assert(AW_ViewLockedMode(&v)==AW_VIEW_FIRST);
    for(i=0;i<(int)(r.vanity_delay*100);i++)AW_ViewIdle(&v,&r,0,1,.1f);
    assert(v.mode==AW_VIEW_FIRST && v.idle==0);
    AW_ViewPOVTap(&v,&r);assert(v.mode==AW_VIEW_FIRST && v.primary==AW_VIEW_FIRST);
    for(i=0;i<50;i++)AW_ViewPOV(&v,&r,1,.1f);
    AW_ViewPOV(&v,&r,0,0);assert(v.mode==AW_VIEW_FIRST);
    AW_ViewZoom(&v,&r,-40);assert(v.mode==AW_VIEW_FIRST);
    v.mode=AW_VIEW_THIRD;AW_ViewIdle(&v,&r,0,1,.1f);assert(v.mode==AW_VIEW_FIRST);   /* a stray change is undone */
    /* setpov 3: third person, held likewise; the wheel does not zoom into first person */
    AW_ViewLock(&v,AW_VIEW_THIRD);
    for(i=0;i<(int)(r.vanity_delay*100);i++)AW_ViewIdle(&v,&r,0,1,.1f);
    assert(v.mode==AW_VIEW_THIRD && v.primary==AW_VIEW_THIRD);
    for(i=0;i<40;i++)AW_ViewZoom(&v,&r,50);
    assert(v.mode==AW_VIEW_THIRD);
    AW_ViewPOVTap(&v,&r);assert(v.mode==AW_VIEW_THIRD);
    /* setpov 2: the vanity orbit, kept whatever the input, and turning */
    AW_ViewLock(&v,AW_VIEW_VANITY);
    for(i=0;i<20;i++)AW_ViewIdle(&v,&r,1,1,.5f);
    assert(v.mode==AW_VIEW_VANITY && v.orbit_yaw>0);
    /* off: the rules are back; the primary mode stays and the idle orbit starts after its delay again */
    AW_ViewLock(&v,-1);v.mode=v.primary;assert(AW_ViewLockedMode(&v)==-1 && v.mode==AW_VIEW_THIRD);
    for(i=0;i<(int)(r.vanity_delay*10)+20;i++)AW_ViewIdle(&v,&r,0,1,.1f);
    assert(v.mode==AW_VIEW_VANITY);
    AW_ViewLock(&v,AW_VIEW_PREVIEW);assert(AW_ViewLockedMode(&v)==-1);                /* only 1, 2 and 3 lock */
    puts("dbg setpov: the lock holds through the idle orbit's timer, Toggle POV and the wheel; off restores the rules.");
    return 0;
}
