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
#include <stdint.h>
#include "aw_view.h"

#define SCALE .25f

int AW_ViewTorchParse(aw_view_torch_t *out,const unsigned char *p,int size,int frames) {
    int count,i,k;uint32_t value;int32_t signed_value;
    if(!out)return 0;
    memset(out,0,sizeof(*out));
    if(!p || size<8 || memcmp(p,"AWBT",4) || p[6] || p[7])return 0;
    count=((int)p[4]<<8)|p[5];
    if(count<1 || count>AW_VIEW_TORCH_FRAMES || count!=frames || size!=8+12*count)return 0;
    p+=8;
    for(i=0;i<count;i++)for(k=0;k<3;k++,p+=4){
        value=((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];
        signed_value=(int32_t)value;
        if(signed_value < -8388608 || signed_value>8388608){memset(out,0,sizeof(*out));return 0;}
        out->point[i][k]=signed_value/65536.0f;
    }
    out->count=count;return 1;
}

static int layer_number(const char **text,int *out) {
    const char *p=*text;int v=0,n=0;
    while(*p>='0' && *p<='9'){
        if(++n>3)return 0;
        v=v*10+(*p++-'0');
    }
    if(!n)return 0;
    *out=v;*text=p;return 1;
}
static int layer_space(char c){return c==' ' || c=='\t' || c=='\n' || c=='\r';}
int AW_ViewLayersParse(aw_view_layers_t *out,const char *p,int frames) {
    aw_view_layers_t t;int v[7],i,j,lo=256,seen,actions[5]={0};
    memset(out,0,sizeof(*out));memset(&t,0,sizeof(t));
    if(!p || frames<1 || frames>256)return 0;
    while(*p){
        while(layer_space(*p))p++;
        if(!*p)break;
        if(*p!='$'){while(*p && !layer_space(*p))p++;continue;}
        p++;
        for(i=0;i<5;i++){
            if(!layer_number(&p,&v[i]))return 0;
            if(i<4){if(*p!=':')return 0;p++;}
        }
        v[5]=v[2];
        if(*p==':'){p++;if(!layer_number(&p,&v[5]))return 0;}
        v[6]=0;
        if(*p==':'){p++;if(!layer_number(&p,&v[6]))return 0;}
        if((*p && !layer_space(*p)) || t.count==AW_VIEW_LAYER_ROWS ||
           (v[0]!=1 && v[0]!=3 && v[0]!=4) || v[1]>255 || v[2]<1 || v[2]>16 ||
           v[3]>255 || v[4]<2 || v[4]>8 || v[5]<1 || v[5]>v[2] ||
           (v[0]==3 ? (v[4]!=3 || v[6]<1 || v[6]>999) : v[6]!=0) ||
           v[1]+v[2]>v[3] || v[3]+v[5]*v[4]>frames)return 0;
        t.rows[t.count].action=(unsigned char)v[0];t.rows[t.count].motion=(short)v[1];
        t.rows[t.count].count=(unsigned char)v[2];t.rows[t.count].base=(short)v[3];
        t.rows[t.count].phases=(unsigned char)v[4];
        t.rows[t.count].hit_permille=(unsigned short)v[6];
        t.rows[t.count++].grid_count=(unsigned char)v[5];if(v[3]<lo)lo=v[3];
    }
    if(t.count!=10 && t.count!=AW_VIEW_LAYER_ROWS)return 0;
    for(i=0;i<t.count;i++)actions[t.rows[i].action]++;
    if(actions[1]!=5 || actions[4]!=5 || actions[3]!=(t.count==15?5:0))return 0;
    for(i=0;i<t.count;i++){
        const aw_view_layer_t *a=&t.rows[i];
        if(a->motion+a->count>lo)return 0; /* never sample another overlay as legs */
        seen=0;
        for(j=0;j<t.count;j++){
            const aw_view_layer_t *b=&t.rows[j];
            if(i==j)continue;
            if(a->base<b->base+b->grid_count*b->phases && b->base<a->base+a->grid_count*a->phases)return 0;
            if(a->action==b->action && a->motion<b->motion+b->count && b->motion<a->motion+a->count)return 0;
            if(a->action!=b->action && a->motion==b->motion && a->count==b->count){
                if(a->action==3 || b->action==3)return 0; /* punch follows ready gait */
                seen++;
            }
        }
        if(seen!=(a->action==3?0:1))return 0;
    }
    *out=t;return 1;
}
int AW_ViewLayerFrame(const aw_view_layers_t *layers,int action,int motion_frame,float fraction) {
    int i,phase;
    if(!layers || layers->count<1 || layers->count>AW_VIEW_LAYER_ROWS ||
       (action!=1 && action!=3 && action!=4) || !(fraction>=0 && fraction<=1))return -1;
    for(i=0;i<layers->count;i++){
        const aw_view_layer_t *r=&layers->rows[i];
        if(r->action!=action || motion_frame<r->motion || motion_frame>=r->motion+r->count)continue;
        if(action==3){
            float hit=r->hit_permille*.001f;
            phase=fraction<(hit*.5f)?0:fraction<((hit+1)*.5f)?1:2;
        }else phase=(int)(fraction*(r->phases-1)+.5f);
        return r->base+phase*r->grid_count+(motion_frame-r->motion)*r->grid_count/r->count;
    }
    return -1;
}

int AW_ViewLayersBind(const aw_view_layers_t *layers,const aw_anim_t *anim) {
    static const int normal[5]={AW_ANIM_IDLE,AW_ANIM_WALK,AW_ANIM_RUN,AW_ANIM_JUMP,AW_ANIM_LAND};
    static const int ready[5]={AW_ANIM_READY,AW_ANIM_READYWALK,AW_ANIM_READYRUN,
                               AW_ANIM_READYJUMP,AW_ANIM_READYLAND};
    int i,j;
    if(!layers || !anim || (layers->count!=10 && layers->count!=15))return 0;
    for(i=0;i<layers->count;i++){
        const aw_view_layer_t *row=&layers->rows[i];
        const int *groups=row->action==3?ready:normal;
        for(j=0;j<5;j++){
            const aw_anim_group_t *g=&anim->g[groups[j]];
            if(g->present && g->base==row->motion && g->count==row->count)break;
        }
        if(j==5)return 0;
    }
    return 1;
}

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
