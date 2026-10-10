/* SPDX-License-Identifier: GPL-2.0-or-later
 * Supported walking for the scaled town. Camera bob remains in view.c.
 */
#include "quakedef.h"
#include "chim/chim.h"
/* CHIM ring loading and actor freezing (chim/chim_world.c sets them only
 * when its data exists). */
void (*aw_chim_player)(vec3_t);
int (*aw_chim_frozen)(edict_t *);
/* CHIM terrain floor (chim/chim_far.c; CHIM-GRAFT-REPACK-EMPTY-33): where the
 * frame's resident far terrain covers a point, the lowest height a body may
 * reach there and the ground to lift it onto. NULL or 0: no floor (legacy maps,
 * outside the layer, chim_terrain_floor 0). */
int (*aw_chim_floor)(const vec3_t origin, float *lowest, float *surface);
static int floor_held;  /* the player stands on the terrain floor: the world has no ground under it */
static int actor_step;  /* AW_ActorStep is walking an actor through AW_WalkPlayer */
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
    if(limit>maximum)limit=maximum;
    if(limit<0)limit=0;
    for(i=0;i<3;i++)out[i]=forward[i]*cmd->forwardmove+right[i]*cmd->sidemove;
    out[2]+=cmd->upmove;
    speed=VectorNormalize(out);if(speed>limit)speed=limit;
    VectorScale(out,speed,out);
}

void AW_NoclipDebugVelocity(vec3_t view,usercmd_t *cmd,float maximum,
                           int fast,int shifted,float shift_scale,vec3_t out)
{
    usercmd_t flight=*cmd;
    if(fast){
        float factor=shifted?1:shift_scale;
        flight.forwardmove*=factor;flight.sidemove*=factor;flight.upmove*=factor;
    }
    AW_NoclipVelocity(view,&flight,maximum,out);
    if(fast){VectorScale(out,2,out);}
}

static qboolean support(edict_t *p, float depth, trace_t *t)
{
    vec3_t end;
    VectorCopy(p->v.origin,end);end[2]-=depth;
    *t=SV_Move(p->v.origin,p->v.mins,p->v.maxs,end,MOVE_NORMAL,p);
    return !t->startsolid && !t->allsolid && t->fraction<1 &&
           t->plane.normal[2]>=AW_WALKABLE_Z && t->ent && t->ent->v.solid==SOLID_BSP;
}

/* Anything of the world (not bodies) within depth below the box. */
static qboolean world_below(edict_t *p, float depth)
{
    vec3_t end;trace_t t;
    VectorCopy(p->v.origin,end);end[2]-=depth;
    t=SV_Move(p->v.origin,p->v.mins,p->v.maxs,end,MOVE_NOMONSTERS,p);
    return t.startsolid || t.allsolid || t.fraction<1;
}

static qboolean box_clear(edict_t *p)
{
    trace_t t=SV_Move(p->v.origin,p->v.mins,p->v.maxs,p->v.origin,MOVE_NOMONSTERS,p);
    return !t.startsolid && !t.allsolid;
}

/* The terrain floor (owner rule: with noclip off the terrain is the lowest
 * height). A body whose feet are below the lowest height at its X/Y (the world
 * under it is missing: the streamer emptied its frame world, or it fell through
 * a seam) is lifted onto the terrain surface with one console line; never while
 * anything of the world lies below it (its own ground, however low, wins). The player
 * is then held on that surface while the world has no ground under it, so it
 * walks on the terrain instead of falling and being lifted again; the world's
 * own ground or water ends the hold. Noclip and flight never come here
 * (SV_Physics_Client calls AW_WalkPlayer only for MOVETYPE_WALK, SV_Physics_Step
 * only in free fall); the movetype test keeps it so. Returns 1 when it moved e. */
int AW_TerrainFloor(edict_t *e, int player)
{
    float lowest,surface,feet;int k;
    if(!aw_chim_floor || e->v.movetype==MOVETYPE_NOCLIP || e->v.movetype==MOVETYPE_FLY ||
       !aw_chim_floor(e->v.origin,&lowest,&surface)) {
        if(player)floor_held=0;
        return 0;
    }
    feet=e->v.origin[2]+e->v.mins[2];
    if(player && floor_held) {
        if(feet>surface)return 0;                       /* above it: a jump, a step down */
        if(world_below(e,64)){floor_held=0;return 0;}   /* the world's ground is back */
        e->v.origin[2]=surface-e->v.mins[2];
    } else {
        if(feet>=lowest || world_below(e,4096))return 0; /* the world has ground below */
        Con_Printf("Terrain floor: %s %ld units below the ground at %ld %ld, lifted onto it\n",
                   player?"the player":"a body",(long)(surface-feet),(long)e->v.origin[0],(long)e->v.origin[1]);
        e->v.origin[2]=surface-e->v.mins[2]+1;
        for(k=0;k<8 && !box_clear(e);k++)e->v.origin[2]+=8;
        if(player)floor_held=1;
    }
    if(e->v.velocity[2]<0)e->v.velocity[2]=0;
    e->v.flags=(int)e->v.flags | FL_ONGROUND;
    e->v.groundentity=EDICT_TO_PROG(sv.edicts);
    return 1;
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
    qboolean swimming, held=false, waterjump;
    /* CHIM: load the chunk ring around the player before moving it. */
    if(aw_chim_player)aw_chim_player(p->v.origin);
    swimming=SV_CheckWater(p);
    waterjump=((int)p->v.flags & FL_WATERJUMP)!=0;
    SV_CheckStuck(p);
    if(!swimming && !waterjump && p->v.velocity[2]<=0 && support(p,0.5f,&floor)) {
        held=true;ground(p,&floor);
        if(!actor_step)floor_held=0;
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
    /* Never below the terrain (the player; an actor's trial step is atomic). */
    if(!actor_step){if(swimming)floor_held=0;else AW_TerrainFloor(p,1);}
}

/* Use the same stair/slide behavior for scripted humanoids. The old monster
 * corner-support test rejects parts of the ship that the player can walk.
 * A failed trial restores every movement field and cannot step off a ledge. */
/* Feet in lava (CONTENTS_LAVA, docs/LAVA.md): the point SV_CheckWater tests first. */
static int feet_in_lava(edict_t *p,const vec3_t at)
{
    vec3_t feet;
    feet[0]=at[0];feet[1]=at[1];feet[2]=at[2]+p->v.mins[2]+1;
    return SV_PointContents(feet)==CONTENTS_LAVA;
}
qboolean AW_ActorStep(edict_t *p,vec3_t move,double dt)
{
    vec3_t origin,oldorigin,velocity,delta;float flags,groundentity,movetype;trace_t floor;int i;
    void (*ring)(vec3_t)=aw_chim_player;
    if(dt<=0)return false;
    VectorCopy(p->v.origin,origin);VectorCopy(p->v.oldorigin,oldorigin);VectorCopy(p->v.velocity,velocity);
    flags=p->v.flags;groundentity=p->v.groundentity;movetype=p->v.movetype;
    VectorCopy(origin,p->v.oldorigin);
    for(i=0;i<2;i++)p->v.velocity[i]=move[i]/dt;
    /* Only the player moves the CHIM chunk ring (CHIM-ACTOR-RING-33): an
     * actor stepping first in a frame would centre it on the actor. */
    aw_chim_player=NULL;actor_step=1;
    p->v.velocity[2]=0;p->v.movetype=MOVETYPE_WALK;AW_WalkPlayer(p);p->v.movetype=movetype;
    aw_chim_player=ring;actor_step=0;
    VectorSubtract(p->v.origin,origin,delta);
    /* Actors keep out of lava as Morrowind's AvoidNode on the pools makes them path around it: a step into lava
     * fails, so the navigation ladder (aw_npcpath.c) takes another way; an actor already in lava may step out. */
    if(delta[0]*delta[0]+delta[1]*delta[1]>.00001f && fabs(delta[2])<=8.75f && support(p,8.75f,&floor) &&
       !(feet_in_lava(p,p->v.origin) && !feet_in_lava(p,origin))) {
        ground(p,&floor);VectorCopy(vec3_origin,p->v.velocity);SV_LinkEdict(p,true);return true;
    }
    VectorCopy(origin,p->v.origin);VectorCopy(oldorigin,p->v.oldorigin);VectorCopy(velocity,p->v.velocity);
    p->v.flags=flags;p->v.groundentity=groundentity;SV_LinkEdict(p,false);return false;
}
