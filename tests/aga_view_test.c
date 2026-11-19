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
    /* CREATURE-SOUNDS-CLIFFRACER-SILENT-58: no orbit while the combat playground or an Arena fight runs (its full
     * view would stop the playground's clock: the sounds mode went silent 30 s after the last key) */
    assert(AW_ViewVanityAllowed(1,1,0) && !AW_ViewVanityAllowed(1,1,1));
    assert(!AW_ViewVanityAllowed(0,1,0) && !AW_ViewVanityAllowed(1,0,0));
    AW_ViewReset(&v,&r);
    for(i=0;i<400;i++)AW_ViewIdle(&v,&r,0,AW_ViewVanityAllowed(1,1,1),.1f);
    assert(v.mode==AW_VIEW_FIRST);
}
/* VIEW-VANITY-UNDOES-SET-VIEW-67: an orbit holds the view at the player's heading and turns the camera with the mouse;
 * a turn the game makes (a script's SetAngle, an arrival's facing, aw_view, aw_aim) is the player's new heading and
 * stays. A check session waited 45 s after each teleport, the orbit (after 30 s) was running, and its aim at the Hall
 * of Wails chest (yaw -102, pitch 21) was put back to the arrival heading (yaw 90, pitch 0): every aim missed. */
static void orbit_hold(void) {
    aw_view_t v;float view[3]={0,90,0},anchor[3]={0,0,0};int i;
    AW_ViewReset(&v,&r);
    for(i=0;i<301;i++)AW_ViewIdle(&v,&r,0,1,.1f);           /* 30.1 s without input: the orbit runs */
    assert(v.mode==AW_VIEW_VANITY);
    v.orbit_yaw=0;                                           /* its own 3 degrees a second aside */
    AW_ViewOrbitHold(&v,view,anchor,1,0);                    /* the frame it began: the heading is its anchor */
    assert(near(anchor[1],90) && near(view[1],90) && near(v.orbit_yaw,0));
    view[1]=100;AW_ViewOrbitHold(&v,view,anchor,0,0);       /* the mouse: the camera turns, the player does not */
    assert(near(view[1],90) && near(v.orbit_yaw,10));
    /* the game turns the player: kept, the camera starts again from it */
    view[0]=21;view[1]=-102;AW_ViewOrbitHold(&v,view,anchor,0,1);
    assert(near(view[0],21) && near(view[1],-102) && near(anchor[0],21) && near(anchor[1],-102));
    assert(near(v.orbit_yaw,0) && near(v.orbit_pitch,0));
    /* the turn counts as input (AW_ViewFrame: the view moved): the orbit ends, the heading stays */
    AW_ViewIdle(&v,&r,1,1,.1f);
    assert(v.mode==AW_VIEW_FIRST && v.idle==0 && near(view[1],-102) && near(view[0],21));
    /* before: the same turn without the game's mark was taken for the mouse and put back (the bug, kept as the rule
     * for the mouse) */
    view[0]=0;view[1]=90;anchor[0]=0;anchor[1]=90;v.mode=AW_VIEW_VANITY;v.orbit_yaw=0;
    view[0]=21;view[1]=-102;AW_ViewOrbitHold(&v,view,anchor,0,0);
    assert(near(view[1],90) && near(view[0],0));
    /* no orbit running: the engine does not hold the view (AW_ViewFrame asks the hold in an orbit only); the turn is
     * input and the view mode is unchanged */
    AW_ViewReset(&v,&r);view[0]=21;view[1]=-102;
    AW_ViewIdle(&v,&r,1,1,.1f);assert(v.mode==AW_VIEW_FIRST && near(view[1],-102));
    /* the orbit still starts again after the delay */
    for(i=0;i<301;i++)AW_ViewIdle(&v,&r,0,1,.1f);
    assert(v.mode==AW_VIEW_VANITY);
    /* the held Toggle POV orbit (preview) keeps a turn the game makes too, and goes on from it */
    v.mode=AW_VIEW_PREVIEW;v.orbit_yaw=40;anchor[1]=10;view[1]=200;
    AW_ViewOrbitHold(&v,view,anchor,0,1);
    assert(v.mode==AW_VIEW_PREVIEW && near(anchor[1],200) && near(view[1],200) && near(v.orbit_yaw,0));
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
/* PLAYER-TORCH-THIRDPERSON-38: an evicted held torch is loaded again (with room, at
 * most once a second); a cached one never is, and caching resets the clock. */
static void held_torch_readmission(void) {
    double next=0;
    assert(!AW_ViewHeldRetry(1,0,5,&next) && next==0);                     /* cached: nothing to do */
    assert(AW_ViewHeldRetry(0,AW_VIEW_HELD_FREE,5,&next) && near((float)next,6));
    assert(!AW_ViewHeldRetry(0,AW_VIEW_HELD_FREE,5.5,&next));               /* not twice a second */
    assert(AW_ViewHeldRetry(0,AW_VIEW_HELD_FREE,6,&next) && near((float)next,7));
    assert(!AW_ViewHeldRetry(0,AW_VIEW_HELD_FREE-1,7,&next) && near((float)next,8)); /* no room: wait, retry later */
    assert(AW_ViewHeldRetry(0,AW_VIEW_HELD_FREE+1,8,&next));
    assert(!AW_ViewHeldRetry(1,0,8.1,&next) && next==0);                   /* back in the cache */
    assert(AW_ViewHeldRetry(0,AW_VIEW_HELD_FREE,8.2,&next));                /* a new eviction retries at once */
    assert(!AW_ViewHeldRetry(0,AW_VIEW_HELD_FREE,8.2,NULL));
}
/* PLAYER-VANITY-WALK-STUCK-67: every camera or control change restarts the body's animation state as a map load does,
 * and after it the walk and the run play (their frames move on, the group is not restarted every frame) and no jump
 * or landing frame stands in for them. Per path: the idle vanity orbit in and out, first/third person, noclip on and
 * off, swimming in and out, a menu or dialogue over play and back, the body drawn or not, a new map. */
static void walk_frames(const aw_anim_t *a,aw_anim_play_t *play,aw_anim_air_t *air,float speed,int want) {
    int i,frame,last=-1,moved=0,group=-1;float rate=1;
    for(i=0;i<20;i++){
        group=AW_AnimPlayerMoveGroup(a,speed,0,0,&rate);
        frame=AW_AnimPlayerAdvance(a,play,group,.05f,rate);
        assert(AW_AnimAirFrame(a,air,1,0,0,0,.05f)<0);          /* on the ground: no jump or landing frame */
        assert(group==want && play->group==want);
        assert(frame>=a->g[want].base && frame<a->g[want].base+a->g[want].count);
        if(last>=0 && frame!=last)moved++;
        last=frame;
    }
    assert(moved>=5);                                            /* the cycle moves on: never restarted each frame */
}
static void body_restart(void) {
    aw_anim_t a;aw_anim_play_t play;aw_anim_air_t air;aw_view_body_sig_t last,now;aw_view_t v;int i;
    static const struct {int group,base,count;float x;} g[]={{AW_ANIM_IDLE,0,4,0},{AW_ANIM_WALK,4,8,20},
        {AW_ANIM_RUN,12,8,60},{AW_ANIM_JUMP,20,4,0},{AW_ANIM_LAND,24,4,0}};
    memset(&a,0,sizeof(a));
    for(i=0;i<5;i++){a.g[g[i].group].present=1;a.g[g[i].group].base=(short)g[i].base;
        a.g[g[i].group].count=(unsigned char)g[i].count;a.g[g[i].group].step=.1f;a.g[g[i].group].x=g[i].x;}
    memset(&last,0,sizeof(last));memset(&now,0,sizeof(now));
    now.valid=1;now.mode=AW_VIEW_THIRD;now.movetype=3;now.playing=1;now.drawn=1;
    assert(AW_ViewBodySigChanged(&last,&now));                   /* the first frame of a map */
    assert(!AW_ViewBodySigChanged(&last,&now));                  /* nothing changed: nothing restarted */
    AW_ViewBodyRestart(&play,&air);
    assert(play.group==255 && !air.airborne && !air.landing);
    walk_frames(&a,&play,&air,24,AW_ANIM_WALK);
    /* idle into the vanity orbit (the delay passed), then any input ends it: two changes, two restarts */
    memset(&v,0,sizeof(v));v.mode=v.primary=AW_VIEW_THIRD;
    AW_ViewIdle(&v,&r,0,1,r.vanity_delay+1);assert(v.mode==AW_VIEW_VANITY);
    now.mode=v.mode;assert(AW_ViewBodySigChanged(&last,&now));
    /* a stale state as the orbit could leave it: a landing that never ends, the walk's clock in the middle */
    air.landing=1;air.play.group=AW_ANIM_LAND;air.play.index=1;play.group=AW_ANIM_WALK;play.phase=3.5f;
    AW_ViewIdle(&v,&r,1,1,.1f);assert(v.mode==AW_VIEW_THIRD);
    now.mode=v.mode;assert(AW_ViewBodySigChanged(&last,&now));
    AW_ViewBodyRestart(&play,&air);
    walk_frames(&a,&play,&air,24,AW_ANIM_WALK);
    walk_frames(&a,&play,&air,70,AW_ANIM_RUN);
    /* every other path that changes the camera or the control */
    now.mode=AW_VIEW_FIRST;assert(AW_ViewBodySigChanged(&last,&now));now.mode=AW_VIEW_THIRD;assert(AW_ViewBodySigChanged(&last,&now));
    now.movetype=8;assert(AW_ViewBodySigChanged(&last,&now));now.movetype=3;assert(AW_ViewBodySigChanged(&last,&now));
    now.swimming=1;assert(AW_ViewBodySigChanged(&last,&now));now.swimming=0;assert(AW_ViewBodySigChanged(&last,&now));
    now.playing=0;assert(AW_ViewBodySigChanged(&last,&now));now.playing=1;assert(AW_ViewBodySigChanged(&last,&now));
    now.drawn=0;assert(AW_ViewBodySigChanged(&last,&now));now.drawn=1;assert(AW_ViewBodySigChanged(&last,&now));
    last.valid=0;assert(AW_ViewBodySigChanged(&last,&now));     /* a new map (AW_ViewSceneSpawn) */
    assert(!AW_ViewBodySigChanged(&last,&now));
}
int main(void) {
    defaults();toggle();tap();vanity();orbit_hold();zoom();death();body_layers();compact_body_layers();player_torch_emitters();
    held_torch_readmission();body_restart();
    puts("view rules ok");
    return 0;
}
