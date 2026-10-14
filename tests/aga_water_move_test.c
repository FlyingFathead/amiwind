/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>

extern edict_t *sv_player;
extern float *velocity;
extern usercmd_t cmd;
extern void SV_WaterMove(void);
cvar_t sv_friction={"sv_friction","4"};
extern cvar_t sv_maxspeed,sv_accelerate;
double host_frametime;

int main(void) {
    edict_t player;int i;
    memset(&player,0,sizeof player);memset(&cmd,0,sizeof cmd);
    sv_player=&player;velocity=player.v.velocity;
    sv_friction.value=4;sv_maxspeed.value=320;sv_accelerate.value=10;
    host_frametime=.05;
    /* No input means no invented descent, including after entering water. */
    for(i=0;i<160;i++)SV_WaterMove();
    assert(velocity[0]==0 && velocity[1]==0 && velocity[2]==0);
    velocity[2]=-42;
    for(i=0;i<80;i++)SV_WaterMove();
    assert(fabs(velocity[2])<.001);
    /* Existing level, pitched and explicit up/down controls retain motion. */
    VectorCopy(vec3_origin,velocity);cmd.forwardmove=200;
    for(i=0;i<20;i++)SV_WaterMove();
    assert(velocity[0]>100 && fabs(velocity[2])<.001);
    VectorCopy(vec3_origin,velocity);player.v.v_angle[PITCH]=45;
    for(i=0;i<20;i++)SV_WaterMove();
    assert(velocity[0]>50 && velocity[2]<-50);
    VectorCopy(vec3_origin,velocity);player.v.v_angle[PITCH]=-45;
    for(i=0;i<20;i++)SV_WaterMove();
    assert(velocity[0]>50 && velocity[2]>50);
    VectorCopy(vec3_origin,velocity);cmd.forwardmove=0;cmd.upmove=200;
    for(i=0;i<20;i++)SV_WaterMove();
    assert(velocity[2]>100);
    VectorCopy(vec3_origin,velocity);cmd.upmove=-200;
    for(i=0;i<20;i++)SV_WaterMove();
    assert(velocity[2]<-100);
    return 0;
}
