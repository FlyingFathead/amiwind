/* SPDX-License-Identifier: GPL-2.0-or-later
 * The player's view and death scene rules (aw_view.h): no engine
 * dependencies, host-tested (tests/aga_view_test.c).
 *
 * Sources (OpenMW 0.51, the original game as OpenMW reproduces it):
 * - camera.lua updatePOV: Toggle POV pressed and released within switchLimit
 *   0.25 s switches first/third person; held longer, the camera orbits the
 *   player (Preview) until release. In third person the orbit starts at once.
 * - camera.lua updateIdleTimer/updateVanity: no input for fVanityDelay seconds
 *   (a game setting, 30 in Morrowind.esm) starts Vanity: the camera turns
 *   3 degrees a second around the player until any input.
 * - camera.lua zoom: the wheel moves the third-person distance between
 *   minDistance 30 and maxDistance 800; zooming in at the minimum goes to
 *   first person, zooming out in first person goes to third person at the
 *   minimum. third_person.lua baseDistance 192. actionbindings.lua: 10 per
 *   wheel click. camera.cpp: the focal point 124 above the feet, the camera
 *   kept 5 in front of an obstacle. All lengths x 0.25 (game units).
 * - character.cpp playRandomDeath -> World::useDeathCamera: the player's death
 *   switches to the third-person camera and plays the body's death animation;
 *   actors.cpp: when it has finished, StateManager::askLoadRecent asks to load
 *   the most recent save (Yes) or opens the main menu (No); with no save it
 *   opens the main menu at once.
 */
#include <string.h>
#include "aw_view.h"

#define SCALE .25f

void AW_ViewRulesDefault(aw_view_rules_t *r) {
    r->switch_limit=.25f;
    r->vanity_delay=30;           /* fVanityDelay; the engine reads the image's value */
    r->vanity_rate=3;
    r->base_distance=192*SCALE;
    r->min_distance=30*SCALE;
    r->max_distance=800*SCALE;
    r->zoom_step=10*SCALE;
    r->height=124*SCALE;
    r->obstacle=5*SCALE;
}
void AW_ViewReset(aw_view_t *v,const aw_view_rules_t *r) {
    memset(v,0,sizeof(*v));
    v->mode=v->primary=AW_VIEW_FIRST;     /* the original starts in first person */
    v->distance=r->base_distance;
}
void AW_ViewPOV(aw_view_t *v,const aw_view_rules_t *r,int held,float dt) {
    if(v->mode==AW_VIEW_DEATH)return;
    if(held){
        v->pov_held+=dt;
        if((v->primary==AW_VIEW_THIRD || v->pov_held>=r->switch_limit) && v->mode!=AW_VIEW_PREVIEW){
            v->mode=AW_VIEW_PREVIEW;v->orbit_yaw=v->orbit_pitch=0;
        }
    }else if(v->pov_held>0){
        if(v->pov_held<=r->switch_limit)v->primary=v->primary==AW_VIEW_FIRST?AW_VIEW_THIRD:AW_VIEW_FIRST;
        v->mode=v->primary;v->pov_held=0;
    }
}
/* A tap shorter than a frame (a quick key press, or a slow frame on the Amiga) never showed as held:
 * it counts as the shortest press, so it switches the view like any short press. */
void AW_ViewPOVTap(aw_view_t *v,const aw_view_rules_t *r) {
    AW_ViewPOV(v,r,1,.001f);AW_ViewPOV(v,r,0,0);
}
void AW_ViewIdle(aw_view_t *v,const aw_view_rules_t *r,int input,int allowed,float dt) {
    if(v->mode==AW_VIEW_DEATH)return;
    if(input)v->idle=0;else v->idle+=dt;
    if(allowed && v->idle>r->vanity_delay && v->mode!=AW_VIEW_VANITY){
        v->mode=AW_VIEW_VANITY;v->orbit_yaw=v->orbit_pitch=0;
    }
    if(v->mode==AW_VIEW_VANITY){
        if(!allowed || v->idle==0){v->mode=v->primary;v->orbit_yaw=v->orbit_pitch=0;}
        else{
            v->orbit_yaw+=r->vanity_rate*dt;
            if(v->orbit_yaw>=360)v->orbit_yaw-=360;
        }
    }
}
void AW_ViewZoom(aw_view_t *v,const aw_view_rules_t *r,float delta) {
    if(v->mode==AW_VIEW_DEATH || !delta)return;
    if(v->mode!=AW_VIEW_FIRST){
        if(delta>0 && v->distance<=r->min_distance && v->mode!=AW_VIEW_PREVIEW){
            v->primary=v->mode=AW_VIEW_FIRST;return;
        }
        v->distance-=delta;
        if(v->distance<r->min_distance)v->distance=r->min_distance;
        if(v->distance>r->max_distance)v->distance=r->max_distance;
    }else if(delta<0){
        v->primary=v->mode=AW_VIEW_THIRD;v->distance=r->min_distance;
    }
}
int AW_ViewBehind(const aw_view_t *v) {return v->mode!=AW_VIEW_FIRST;}
float AW_ViewObstacle(float preferred,float fraction,float obstacle) {
    float d;
    if(!(fraction<1))return preferred;
    if(fraction<0)fraction=0;
    d=preferred*fraction-obstacle;
    return d<0?0:d;
}

void AW_DeathBegin(aw_death_t *d,float fall,int retry,int saved) {
    memset(d,0,sizeof(*d));
    d->stage=AW_DEATH_FALLING;d->fall=fall>0?fall:0;
    if(saved){d->choice[d->count++]=AW_DEATH_LOAD;d->choice[d->count++]=AW_DEATH_MENU;}
    if(retry){
        if(!saved){d->choice[d->count++]=AW_DEATH_RETRY;d->choice[d->count++]=AW_DEATH_MENU;}
        else d->choice[d->count++]=AW_DEATH_RETRY;
    }
}
int AW_DeathStep(aw_death_t *d,float dt) {
    if(d->stage==AW_DEATH_NONE)return d->stage;
    if(dt>0)d->time+=dt;
    if(d->stage==AW_DEATH_FALLING && d->time>=d->fall)d->stage=d->count?AW_DEATH_ASK:AW_DEATH_MAIN_MENU;
    return d->stage;
}
int AW_DeathKey(aw_death_t *d,int key) {
    int i;
    if(d->stage!=AW_DEATH_ASK || d->count<1)return -1;
    if(key==1)d->selection=(d->selection+d->count-1)%d->count;
    else if(key==2)d->selection=(d->selection+1)%d->count;
    else if(key==3)return d->choice[d->selection];
    else if(key==4)return d->choice[0];
    else if(key==5){for(i=0;i<d->count;i++)if(d->choice[i]==AW_DEATH_MENU)return AW_DEATH_MENU;}
    return -1;
}
void AW_DeathEnd(aw_death_t *d) {memset(d,0,sizeof(*d));}
