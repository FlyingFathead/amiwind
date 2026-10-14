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
#include <string.h>
#include "aw_anim.h"
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
static void body_layers(void) {
    const char *text="idle:0:8:0.25 $1:0:8:20:2 $1:8:4:36:2 $1:12:4:44:2 $1:16:2:52:2 $1:18:2:56:2 "
        "$4:0:8:60:2 $4:8:4:76:2 $4:12:4:84:2 $4:16:2:92:2 $4:18:2:96:2";
    aw_view_layers_t layers;int i,j,k;char bad[512],*p;
    assert(AW_ViewLayersParse(&layers,text,100) && layers.count==10);
    for(i=0;i<layers.count;i++){
        const aw_view_layer_t *r=&layers.rows[i];
        for(j=0;j<r->count;j++)for(k=0;k<2;k++)
            assert(AW_ViewLayerFrame(&layers,r->action,r->motion+j,(float)k)==r->base+k*r->count+j);
    }
    assert(AW_ViewLayerFrame(&layers,2,0,0)==-1);
    assert(AW_ViewLayerFrame(&layers,1,20,0)==-1); /* no recursive overlay */
    assert(AW_ViewLayerFrame(&layers,1,0,-.1f)==-1);
    assert(AW_ViewLayerFrame(&layers,1,0,1.1f)==-1);
    assert(AW_ViewLayerFrame(&layers,1,0,NAN)==-1);
    assert(!AW_ViewLayersParse(&layers,text,99) && layers.count==0);
    assert(!AW_ViewLayersParse(&layers,"idle:0:8:0.25",100) && layers.count==0);
    assert(!AW_ViewLayersParse(&layers,NULL,100) && layers.count==0);
    strcpy(bad,text);p=strstr(bad,"$1:8:4:36:2");p[7]='2';p[8]='0'; /* overlap first grid */
    assert(!AW_ViewLayersParse(&layers,bad,100) && layers.count==0);
    strcpy(bad,text);p=strstr(bad,"$4:18:2:96:2");p[3]='0'; /* unpaired movement */
    assert(!AW_ViewLayersParse(&layers,bad,100) && layers.count==0);
    strcpy(bad,text);strcat(bad," $1:0:8:20:2");
    assert(!AW_ViewLayersParse(&layers,bad,100) && layers.count==0);
    strcpy(bad,text);strcat(bad," $9999:0:8:20:2");
    assert(!AW_ViewLayersParse(&layers,bad,100) && layers.count==0);
    assert(AW_ViewLayersParse(&layers,text,100)); /* failure cannot poison a later valid load */
}
static void compact_body_layers(void) {
    const char *text="idle:0:8:0.25 walk:8:4:0.1:20 run:12:4:0.1:60 jump:16:2:0.2 land:18:2:0.2 "
        "ready:20:8:0.25 readywalk:28:4:0.1:20 readyrun:32:4:0.1:60 "
        "readyjump:36:2:0.2 readyland:38:2:0.2 "
        "$1:0:8:40:2:1 $1:8:4:42:2:2 $1:12:4:46:2:2 $1:16:2:50:2:1 $1:18:2:52:2:1 "
        "$4:0:8:54:2:1 $4:8:4:56:2:2 $4:12:4:60:2:2 $4:16:2:64:2:1 $4:18:2:66:2:1 "
        "$3:20:8:68:3:1:600 $3:28:4:71:3:2:600 $3:32:4:77:3:2:600 "
        "$3:36:2:83:3:1:600 $3:38:2:86:3:1:600";
    aw_view_layers_t layers;aw_anim_t anim;aw_anim_play_t play={0};aw_anim_air_t air={0};
    char bad[1024],*p;float rate;int group,frame;
    assert(AW_AnimParse(&anim,text,89));
    assert(AW_ViewLayersParse(&layers,text,89) && layers.count==15);
    assert(AW_ViewLayersBind(&layers,&anim));
    assert(AW_ViewLayerFrame(&layers,1,8,0)==42);
    assert(AW_ViewLayerFrame(&layers,1,11,1)==45);
    assert(AW_ViewLayerFrame(&layers,3,28,0)==71);
    assert(AW_ViewLayerFrame(&layers,3,31,.29f)==72);
    assert(AW_ViewLayerFrame(&layers,3,31,.3f)==74); /* source hit at 60% of punch */
    assert(AW_ViewLayerFrame(&layers,3,31,.8f)==76);
    group=AW_AnimPlayerMoveGroup(&anim,0,0,1,&rate);
    assert(group==AW_ANIM_READY);
    frame=AW_AnimPlayerAdvance(&anim,&play,group,0,rate);
    assert(AW_ViewLayerFrame(&layers,3,frame,.6f)>=68);
    group=AW_AnimPlayerMoveGroup(&anim,55,0,1,&rate);
    assert(group==AW_ANIM_READYRUN);
    frame=AW_AnimPlayerAdvance(&anim,&play,group,.1f,rate);
    assert(frame>=32 && frame<36 && AW_ViewLayerFrame(&layers,3,frame,.6f)>=77);
    frame=AW_AnimAirFrame(&anim,&air,1,1,1,1,.1f);
    assert(frame>=36 && frame<38 && AW_ViewLayerFrame(&layers,3,frame,.6f)>=83);
    assert(!AW_ViewLayersParse(&layers,text,88));
    strcpy(bad,text);p=strstr(bad,"$3:28:4:71:3:2:600");p[15]='0';
    assert(!AW_ViewLayersParse(&layers,bad,89)); /* hit is strictly between endpoints */
    assert(AW_ViewLayersParse(&layers,text,89));
    anim.g[AW_ANIM_READYRUN].base++;
    assert(!AW_ViewLayersBind(&layers,&anim)); /* bound to the ready run, not normal run */
}
static void player_torch_emitters(void) {
    unsigned char p[33]={ 'A','W','B','T',0,2,0,0 };aw_view_torch_t out;
    /* Two actual signed 16.16 positions, including both allowed endpoints. */
    p[8]=255;p[9]=254;p[10]=128; /* -1.5 */
    p[17]=128;                 /* frame0 Z +128 */
    p[20]=255;p[21]=128;       /* frame1 X -128 */
    assert(AW_ViewTorchParse(&out,p,32,2) && out.count==2);
    assert(out.point[0][0]==-1.5f && out.point[0][2]==128 && out.point[1][0]==-128);
    assert(!AW_ViewTorchParse(&out,p,31,2) && !out.count);
    assert(!AW_ViewTorchParse(&out,p,33,2) && !out.count);
    assert(!AW_ViewTorchParse(&out,p,32,3) && !out.count);
    p[7]=1;assert(!AW_ViewTorchParse(&out,p,32,2));p[7]=0;
    p[0]='X';assert(!AW_ViewTorchParse(&out,p,32,2));p[0]='A';
    p[4]=1;p[5]=1;assert(!AW_ViewTorchParse(&out,p,32,257));p[4]=0;p[5]=2;
    p[19]=1;assert(!AW_ViewTorchParse(&out,p,32,2) && !out.count && out.point[0][0]==0);
    assert(!AW_ViewTorchParse(&out,NULL,0,0));
}
int main(void) {
    defaults();toggle();tap();vanity();zoom();death();body_layers();compact_body_layers();player_torch_emitters();
    puts("view rules ok");
    return 0;
}
