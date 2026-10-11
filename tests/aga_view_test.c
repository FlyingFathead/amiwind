/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_view_rules.c alone: the first/third-person toggle and the held orbit
 * (camera.lua updatePOV), the idle clock and the vanity orbit (updateIdleTimer,
 * updateVanity, fVanityDelay), the wheel zoom (zoom), the obstacle pull-in
 * (camera.cpp updatePosition) and the death scene (useDeathCamera, then
 * askLoadRecent after the death animation; the AmiWind quick retry). */
#define AW_VIEW_HOST_TEST 1
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include "aw_view.h"

static int near(float a,float b){return fabsf(a-b)<.001f;}
static aw_view_rules_t r;

static void defaults(void) {
    AW_ViewRulesDefault(&r);
    /* OpenMW 0.51 values x 0.25 (game units) */
    assert(near(r.switch_limit,.25f) && near(r.vanity_delay,30) && near(r.vanity_rate,3));
    assert(near(r.base_distance,48) && near(r.min_distance,7.5f) && near(r.max_distance,200));
    assert(near(r.zoom_step,2.5f) && near(r.height,31) && near(r.obstacle,1.25f));
}
static void toggle(void) {
    aw_view_t v;int i;
    AW_ViewReset(&v,&r);
    assert(v.mode==AW_VIEW_FIRST && v.primary==AW_VIEW_FIRST && near(v.distance,48));   /* first person at start */
    /* a short press (0.1 s) switches to third person on release */
    AW_ViewPOV(&v,&r,1,.05f);AW_ViewPOV(&v,&r,1,.05f);
    assert(v.mode==AW_VIEW_FIRST);
    AW_ViewPOV(&v,&r,0,.05f);
    assert(v.mode==AW_VIEW_THIRD && v.primary==AW_VIEW_THIRD && v.pov_held==0);
    /* in third person a held key orbits at once; a short press switches back on release */
    AW_ViewPOV(&v,&r,1,.05f);assert(v.mode==AW_VIEW_PREVIEW);
    AW_ViewPOV(&v,&r,0,.05f);assert(v.mode==AW_VIEW_FIRST && v.primary==AW_VIEW_FIRST);
    /* in first person a long hold (over 0.25 s) orbits, and the release keeps first person */
    for(i=0;i<4;i++)AW_ViewPOV(&v,&r,1,.05f);
    assert(v.mode==AW_VIEW_FIRST);
    for(i=0;i<3;i++)AW_ViewPOV(&v,&r,1,.05f);
    assert(v.mode==AW_VIEW_PREVIEW);
    v.orbit_yaw=40;
    AW_ViewPOV(&v,&r,0,.05f);
    assert(v.mode==AW_VIEW_FIRST && v.primary==AW_VIEW_FIRST);
    /* the death camera ignores the key */
    v.mode=AW_VIEW_DEATH;AW_ViewPOV(&v,&r,1,1);AW_ViewPOV(&v,&r,0,1);assert(v.mode==AW_VIEW_DEATH);
}
static void vanity(void) {
    aw_view_t v;int i;
    AW_ViewReset(&v,&r);
    AW_ViewIdle(&v,&r,0,1,30);                               /* exactly 30 s: not yet (idleTimer > delay) */
    assert(v.mode==AW_VIEW_FIRST && near(v.idle,30));
    AW_ViewIdle(&v,&r,0,1,.5f);
    assert(v.mode==AW_VIEW_VANITY && near(v.orbit_yaw,1.5f)); /* from first person too, as the original */
    AW_ViewIdle(&v,&r,0,1,1);
    assert(near(v.orbit_yaw,4.5f));                          /* 3 degrees a second */
    AW_ViewIdle(&v,&r,1,1,.1f);                              /* any input ends it */
    assert(v.mode==AW_VIEW_FIRST && v.idle==0 && v.orbit_yaw==0);
    /* not allowed (dead, in a menu, switched off): the clock runs, no orbit */
    for(i=0;i<400;i++)AW_ViewIdle(&v,&r,0,0,.1f);
    assert(v.mode==AW_VIEW_FIRST);
    AW_ViewIdle(&v,&r,0,1,.1f);assert(v.mode==AW_VIEW_VANITY);
    AW_ViewIdle(&v,&r,0,0,.1f);assert(v.mode==AW_VIEW_FIRST);   /* disallowed while orbiting: back */
    /* from third person it returns to third person */
    AW_ViewReset(&v,&r);v.mode=v.primary=AW_VIEW_THIRD;
    AW_ViewIdle(&v,&r,0,1,31);
    assert(v.mode==AW_VIEW_VANITY);
    AW_ViewIdle(&v,&r,1,1,.1f);assert(v.mode==AW_VIEW_THIRD);
    /* the death camera keeps its mode */
    v.mode=AW_VIEW_DEATH;for(i=0;i<400;i++)AW_ViewIdle(&v,&r,0,1,.1f);assert(v.mode==AW_VIEW_DEATH);
}
static void zoom(void) {
    aw_view_t v;
    AW_ViewReset(&v,&r);
    AW_ViewZoom(&v,&r,2.5f);assert(v.mode==AW_VIEW_FIRST);             /* zoom in, first person: nothing */
    AW_ViewZoom(&v,&r,-2.5f);                                           /* zoom out: third person at the minimum */
    assert(v.mode==AW_VIEW_THIRD && v.primary==AW_VIEW_THIRD && near(v.distance,7.5f));
    AW_ViewZoom(&v,&r,-10);assert(near(v.distance,17.5f));
    AW_ViewZoom(&v,&r,-1000);assert(near(v.distance,200));              /* maxDistance 800 x 0.25 */
    AW_ViewZoom(&v,&r,1000);assert(near(v.distance,7.5f) && v.mode==AW_VIEW_THIRD);
    AW_ViewZoom(&v,&r,2.5f);assert(v.mode==AW_VIEW_FIRST && v.primary==AW_VIEW_FIRST);   /* in past the minimum */
    v.mode=AW_VIEW_PREVIEW;v.distance=7.5f;AW_ViewZoom(&v,&r,2.5f);assert(v.mode==AW_VIEW_PREVIEW);
    assert(AW_ViewBehind(&v));v.mode=AW_VIEW_FIRST;assert(!AW_ViewBehind(&v));
    /* the obstacle: the camera stops 1.25 in front of a wall */
    assert(near(AW_ViewObstacle(48,1,1.25f),48));
    assert(near(AW_ViewObstacle(48,.5f,1.25f),22.75f));
    assert(near(AW_ViewObstacle(48,0,1.25f),0) && near(AW_ViewObstacle(48,.01f,1.25f),0));
}
static void death(void) {
    aw_death_t d;
    /* a save and the retry: Yes (load) / No (main menu) / Retry fight, after the death animation */
    AW_DeathBegin(&d,1.2f,1,1);
    assert(d.stage==AW_DEATH_FALLING && d.count==3 && d.choice[0]==AW_DEATH_LOAD && d.choice[1]==AW_DEATH_MENU &&
           d.choice[2]==AW_DEATH_RETRY && d.selection==0);
    assert(AW_DeathKey(&d,3)==-1);                         /* no choice while falling */
    assert(AW_DeathStep(&d,1)==AW_DEATH_FALLING);
    assert(AW_DeathStep(&d,.3f)==AW_DEATH_ASK);
    assert(AW_DeathKey(&d,2)==-1 && d.selection==1);
    assert(AW_DeathKey(&d,2)==-1 && d.selection==2);
    assert(AW_DeathKey(&d,2)==-1 && d.selection==0);       /* wraps */
    assert(AW_DeathKey(&d,1)==-1 && d.selection==2);
    assert(AW_DeathKey(&d,3)==AW_DEATH_RETRY);
    assert(AW_DeathKey(&d,4)==AW_DEATH_LOAD && AW_DeathKey(&d,5)==AW_DEATH_MENU);
    /* the original alone (retry off): Yes / No */
    AW_DeathBegin(&d,0,0,1);
    assert(d.count==2 && AW_DeathStep(&d,0)==AW_DEATH_ASK && AW_DeathKey(&d,3)==AW_DEATH_LOAD);
    /* no save, retry on: "Try the fight again?" Yes (retry) / No (main menu) */
    AW_DeathBegin(&d,.5f,1,0);
    assert(d.count==2 && d.choice[0]==AW_DEATH_RETRY && d.choice[1]==AW_DEATH_MENU);
    AW_DeathStep(&d,.5f);assert(d.stage==AW_DEATH_ASK && AW_DeathKey(&d,4)==AW_DEATH_RETRY && AW_DeathKey(&d,5)==AW_DEATH_MENU);
    /* no save, no retry: straight to the main menu when the animation ends (askLoadRecent) */
    AW_DeathBegin(&d,.5f,0,0);
    assert(d.count==0 && AW_DeathStep(&d,.4f)==AW_DEATH_FALLING && AW_DeathStep(&d,.2f)==AW_DEATH_MAIN_MENU);
    assert(AW_DeathKey(&d,3)==-1);
    AW_DeathEnd(&d);assert(d.stage==AW_DEATH_NONE && AW_DeathStep(&d,1)==AW_DEATH_NONE);
}
/* CAMERA-POV-TAP-LOST-36: a press released before the next frame still switches, both ways */
static void tap(void) {
    aw_view_t v;
    AW_ViewReset(&v,&r);
    AW_ViewPOVTap(&v,&r);
    assert(v.mode==AW_VIEW_THIRD && v.primary==AW_VIEW_THIRD && v.pov_held==0);
    AW_ViewPOVTap(&v,&r);
    assert(v.mode==AW_VIEW_FIRST && v.primary==AW_VIEW_FIRST && v.pov_held==0);
    v.mode=AW_VIEW_DEATH;AW_ViewPOVTap(&v,&r);assert(v.mode==AW_VIEW_DEATH);
}
int main(void) {
    defaults();toggle();tap();vanity();zoom();death();
    puts("view rules ok");
    return 0;
}
