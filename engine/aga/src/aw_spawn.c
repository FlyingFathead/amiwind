/* SPDX-License-Identifier: GPL-2.0-or-later
 * One-time spawn clearance search against the actual standing collision hull.
 * The scene's nominal point can intersect an approximate architectural proxy.
 */
#include "quakedef.h"

static qboolean floor_at(edict_t *p, vec3_t top, vec3_t bottom, vec3_t result)
{
    trace_t t = SV_Move(top,p->v.mins,p->v.maxs,bottom,MOVE_NORMAL,p);
    if(t.startsolid || t.allsolid || t.fraction >= 1 || t.plane.normal[2] < AW_WALKABLE_Z)
        return false;
    VectorCopy(t.endpos,result);
    result[2] += 0.25f;
    t = SV_Move(result,p->v.mins,p->v.maxs,result,MOVE_NORMAL,p);
    return !t.startsolid && !t.allsolid;
}

static qboolean exits_clear(edict_t *p, vec3_t point)
{
    static int dirs[4][2]={{1,0},{-1,0},{0,1},{0,-1}};
    vec3_t top,end,bottom,ground;trace_t t;int i;
    /* Check a short step in each direction, including support at its end.
     * A free point on a thin wall or roof edge is not a useful town spawn. */
    for(i=0;i<4;i++) {
        VectorCopy(point,top);top[2]+=8.5f;
        t=SV_Move(point,p->v.mins,p->v.maxs,top,MOVE_NORMAL,p);
        if(t.startsolid || t.allsolid || t.fraction<1)return false;
        VectorCopy(top,end);end[0]+=dirs[i][0]*32;end[1]+=dirs[i][1]*32;
        t=SV_Move(top,p->v.mins,p->v.maxs,end,MOVE_NORMAL,p);
        if(t.startsolid || t.allsolid || t.fraction<1)return false;
        VectorCopy(end,bottom);bottom[2]-=17;
        if(!floor_at(p,end,bottom,ground) || fabs(ground[2]-point[2])>8.5f)
            return false;
    }
    return true;
}

qboolean AW_FindSafeSpawn(edict_t *p, vec3_t preferred, vec3_t result)
{
    vec3_t top,bottom,point;float score,best=1e30f;int x,y; qboolean found=false;
    /* Bounded startup-only work, no extra per-frame collision polling. */
    for(y=-4;y<=4;y++)for(x=-4;x<=4;x++) {
        VectorCopy(preferred,top);top[0]+=x*32;top[1]+=y*32;top[2]+=64;
        VectorCopy(top,bottom);bottom[2]=preferred[2]-128;
        if(!floor_at(p,top,bottom,point))continue;
        score=(x*x+y*y)*1024+4*(point[2]-preferred[2])*(point[2]-preferred[2]);
        if(score>=best || !exits_clear(p,point))continue;
        best=score;found=true;VectorCopy(point,result);
    }
    return found;
}

qboolean AW_PlacePlayer(edict_t *p, vec3_t preferred)
{
    vec3_t point;
    if(!AW_FindSafeSpawn(p,preferred,point)) {
        Con_Printf("No clear town spawn found; use F10, noclip.\n");
        return false;
    }
    VectorCopy(point,p->v.origin);VectorCopy(point,p->v.oldorigin);
    VectorCopy(vec3_origin,p->v.velocity);
    p->v.flags=(int)p->v.flags & ~FL_ONGROUND;
    SV_LinkEdict(p,false);
    Con_Printf("Town spawn: %ld %ld %ld (standing hull checked).\n",
        (long)point[0],(long)point[1],(long)point[2]);
    return true;
}

/* Explicit debug-map arrival: keep the chosen XY, find the highest walkable
 * surface below the scene ceiling, and test the complete standing hull. A failed
 * request must not install unchecked coordinates. */
qboolean AW_MapPlace(edict_t *p,const float *xy)
{
    vec3_t top,bottom,point;
    if(!p || !sv.worldmodel || !isfinite(xy[0]) || !isfinite(xy[1]) ||
       fabs(xy[0])>=4000 || fabs(xy[1])>=4000)return false;
    top[0]=bottom[0]=xy[0];top[1]=bottom[1]=xy[1];
    top[2]=sv.worldmodel->maxs[2]-p->v.maxs[2]-4;
    bottom[2]=sv.worldmodel->mins[2]-p->v.mins[2]+4;
    if(top[2]>3990)top[2]=3990;
    if(bottom[2]<-3990)bottom[2]=-3990;
    if(!isfinite(top[2]) || !isfinite(bottom[2]) || top[2]<=bottom[2] ||
       !floor_at(p,top,bottom,point))return false;
    VectorCopy(point,p->v.origin);VectorCopy(point,p->v.oldorigin);
    VectorCopy(vec3_origin,p->v.velocity);
    p->v.flags=(int)p->v.flags & ~FL_ONGROUND;SV_LinkEdict(p,false);
    return true;
}
