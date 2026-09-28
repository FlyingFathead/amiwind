/* SPDX-License-Identifier: GPL-2.0-or-later
 * Supported walking for the scaled town. Camera bob remains in view.c.
 */
#include "quakedef.h"
extern qboolean SV_CheckWater(edict_t *ent);
extern void SV_CheckStuck(edict_t *ent);
extern void SV_AddGravity(edict_t *ent);
extern void SV_WalkMove(edict_t *ent);

/* Debug flight follows full camera pitch, not the model's reduced pitch.
 * E/Q remains world-vertical. No inertia: released input produces zero speed. */
void AW_NoclipVelocity(vec3_t view, usercmd_t *cmd, float maximum, vec3_t out)
{
    vec3_t forward,right,up;float speed,limit;int i;
    AngleVectors(view,forward,right,up);
    limit=fabs(cmd->forwardmove);
    if(fabs(cmd->sidemove)>limit)limit=fabs(cmd->sidemove);
    if(fabs(cmd->upmove)>limit)limit=fabs(cmd->upmove);
    if(limit>maximum)limit=maximum;if(limit<0)limit=0;
    for(i=0;i<3;i++)out[i]=forward[i]*cmd->forwardmove+right[i]*cmd->sidemove;
    out[2]+=cmd->upmove;
    speed=VectorNormalize(out);if(speed>limit)speed=limit;
    VectorScale(out,speed,out);
}

static qboolean support(edict_t *p, float depth, trace_t *t)
{
    vec3_t end;
    VectorCopy(p->v.origin,end);end[2]-=depth;
    *t=SV_Move(p->v.origin,p->v.mins,p->v.maxs,end,MOVE_NORMAL,p);
    return !t->startsolid && !t->allsolid && t->fraction<1 &&
           t->plane.normal[2]>0.7f && t->ent && t->ent->v.solid==SOLID_BSP;
}

static void ground(edict_t *p, trace_t *t)
{
    VectorCopy(t->endpos,p->v.origin);
    p->v.flags=(int)p->v.flags | FL_ONGROUND;
    p->v.groundentity=EDICT_TO_PROG(t->ent);
}

void AW_WalkPlayer(edict_t *p)
{
    trace_t floor;
    qboolean swimming=SV_CheckWater(p), held=false;
    qboolean waterjump=((int)p->v.flags & FL_WATERJUMP)!=0;
    SV_CheckStuck(p);
    if(!swimming && !waterjump && p->v.velocity[2]<=0 && support(p,0.5f,&floor)) {
        held=true;ground(p,&floor);
        /* Follow an uphill tangent without converting gravity to sideways
         * motion. Keep the commanded horizontal speed on walkable slopes. */
        p->v.velocity[2]=-(floor.plane.normal[0]*p->v.velocity[0]+
                           floor.plane.normal[1]*p->v.velocity[1])/floor.plane.normal[2];
        if(!p->v.velocity[0] && !p->v.velocity[1]) {
            p->v.velocity[2]=0;return;
        }
    } else {
        p->v.flags=(int)p->v.flags & ~FL_ONGROUND;
        if(!swimming && !waterjump)SV_AddGravity(p);
    }
    SV_WalkMove(p);
    /* Only a previously supported walker follows downward steps. Jumping,
     * free fall, swimming and noclip must never be glued to nearby ground. */
    if(held && support(p,8.75f,&floor)) {
        ground(p,&floor);p->v.velocity[2]=0;
    }
}

/* Use the same stair/slide behavior for scripted humanoids. The old monster
 * corner-support test rejects parts of the ship that the player can walk.
 * A failed trial restores every movement field and cannot step off a ledge. */
qboolean AW_ActorStep(edict_t *p,vec3_t move,double dt)
{
    vec3_t origin,oldorigin,velocity,delta;float flags,groundentity,movetype;trace_t floor;int i;
    if(dt<=0)return false;
    VectorCopy(p->v.origin,origin);VectorCopy(p->v.oldorigin,oldorigin);VectorCopy(p->v.velocity,velocity);
    flags=p->v.flags;groundentity=p->v.groundentity;movetype=p->v.movetype;
    VectorCopy(origin,p->v.oldorigin);
    for(i=0;i<2;i++)p->v.velocity[i]=move[i]/dt;
    p->v.velocity[2]=0;p->v.movetype=MOVETYPE_WALK;AW_WalkPlayer(p);p->v.movetype=movetype;
    VectorSubtract(p->v.origin,origin,delta);
    if(delta[0]*delta[0]+delta[1]*delta[1]>.00001f && fabs(delta[2])<=8.75f && support(p,8.75f,&floor)) {
        ground(p,&floor);VectorCopy(vec3_origin,p->v.velocity);SV_LinkEdict(p,true);return true;
    }
    VectorCopy(origin,p->v.origin);VectorCopy(oldorigin,p->v.oldorigin);VectorCopy(velocity,p->v.velocity);
    p->v.flags=flags;p->v.groundentity=groundentity;SV_LinkEdict(p,false);return false;
}
