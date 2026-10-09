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

/* Debug-map arrival over water uses the actual contents boundary in this local
 * BSP frame, never an assumed global z=0. Leave movement/state unchanged if the
 * surface or the complete standing hull cannot be checked. */
static qboolean map_water_surface(edict_t *p,vec3_t top,vec3_t point)
{
    vec3_t probe;trace_t t;float low,high,middle;int contents,i;
    VectorCopy(point,probe);probe[2]+=p->v.mins[2];
    contents=SV_PointContents(probe);
    if(contents==CONTENTS_EMPTY)return true;
    if(contents!=CONTENTS_WATER)return false;
    low=probe[2];high=top[2]+p->v.mins[2];probe[2]=high;
    if(high<=low || SV_PointContents(probe)!=CONTENTS_EMPTY)return false;
    for(i=0;i<20;i++) {
        middle=(low+high)*.5f;
        if(middle==low || middle==high)break;
        probe[2]=middle;contents=SV_PointContents(probe);
        if(contents==CONTENTS_WATER)low=middle;
        else if(contents==CONTENTS_EMPTY)high=middle;
        else return false;
    }
    point[2]=high-p->v.mins[2]+.25f;
    if(!isfinite(point[2]))return false;
    t=SV_Move(point,p->v.mins,p->v.maxs,point,MOVE_NORMAL,p);
    probe[2]=point[2]+p->v.mins[2];
    return !t.startsolid && !t.allsolid && SV_PointContents(probe)==CONTENTS_EMPTY;
}

/* Render bounds include the solid ceiling shell; subtracting the player's
 * head height alone can leave the trace seed inside that shell. Find a clear
 * standing-hull seed at the SAME XY, within a bounded 128-unit band. A solid
 * column fails closed; this never relaxes the floor/clearance acceptance. */
static qboolean map_clear_start(edict_t *p,vec3_t top,vec3_t bottom)
{
    trace_t trace;float initial=top[2];int step;
    for(step=0;step<=32;step++){
        top[2]=initial-step*4;
        if(top[2]<=bottom[2])return false;
        trace=SV_Move(top,p->v.mins,p->v.maxs,top,MOVE_NORMAL,p);
        if(!trace.startsolid && !trace.allsolid)return true;
    }
    return false;
}

/* Explicit debug-map arrival: keep the chosen XY, find the highest walkable
 * surface below the scene ceiling (or below a given height), and test the
 * complete standing hull. A failed request must not install unchecked
 * coordinates. */
/* Why the last map placement failed (said by a debug teleport that falls back). */
const char *aw_map_place_failure="";
static qboolean map_place(edict_t *p,const float *xy,float ceiling)
{
    vec3_t top,bottom,point;
    aw_map_place_failure="outside the map";
    if(!p || !sv.worldmodel || !isfinite(xy[0]) || !isfinite(xy[1]) || !isfinite(ceiling) ||
       fabs(xy[0])>=4000 || fabs(xy[1])>=4000)return false;
    top[0]=bottom[0]=xy[0];top[1]=bottom[1]=xy[1];
    top[2]=sv.worldmodel->maxs[2]-p->v.maxs[2]-4;
    if(ceiling<top[2])top[2]=ceiling;
    bottom[2]=sv.worldmodel->mins[2]-p->v.mins[2]+4;
    if(top[2]>3990)top[2]=3990;
    if(bottom[2]<-3990)bottom[2]=-3990;
    if(!isfinite(top[2]) || !isfinite(bottom[2]) || top[2]<=bottom[2])return false;
    aw_map_place_failure="no clear space at the top of the search";
    if(!map_clear_start(p,top,bottom))return false;
    aw_map_place_failure="no walkable floor below";
    if(!floor_at(p,top,bottom,point))return false;
    aw_map_place_failure="water surface not standable";
    if(!map_water_surface(p,top,point))return false;
    aw_map_place_failure="";
    VectorCopy(point,p->v.origin);VectorCopy(point,p->v.oldorigin);
    VectorCopy(vec3_origin,p->v.velocity);
    p->v.flags=(int)p->v.flags & ~FL_ONGROUND;SV_LinkEdict(p,false);
    return true;
}
qboolean AW_MapPlace(edict_t *p,const float *xy)
{
    return map_place(p,xy,4000);
}
/* dbg tp X Y Z: the first walkable surface at or below Z (the player's centre
 * there; a solid start steps down up to 128 units), so a bridge, a roof or an
 * upper floor is kept instead of the highest surface. Checked as AW_MapPlace. */
qboolean AW_MapPlaceBelow(edict_t *p,const float *point)
{
    return point && isfinite(point[2]) && fabs(point[2])<4000 && map_place(p,point,point[2]);
}
