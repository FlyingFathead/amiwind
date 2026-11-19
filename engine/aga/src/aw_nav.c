/* SPDX-License-Identifier: GPL-2.0-or-later
 * Bounded original path-grid routes; movement uses the server collision hull.
 * One scripted escort at a time. No teleport or movement through obstacles.
 */
#include "quakedef.h"
#define AW_NODES 128
typedef struct {vec3_t point;unsigned short first,count;} aw_node_t;
static aw_node_t nodes[AW_NODES];
static unsigned short edges[512],route[AW_NODES];
static int node_count,edge_count,route_count,route_at;
static edict_t *walker;
static vec3_t destination;
static double blocked,animation,stalled;
static int player_wait;
static float best_distance;
/* PIER-GUARD-WALKS-INTO-DOOR-65 (seen again in v0.0.66-dev1): the last leg of every walk steers straight at its
 * destination; a round obstacle on that line (the pier pylon at about 407 -268 on the dock guard's walk to the office
 * door) let the +-30..90 degree side steps slide him round it on the spot until the stall timer ended the walk, and the
 * opening retried it into the same pylon. Before the walker steers at the destination, and again whenever he makes no
 * progress for a second and a half, the straight line is swept with his hull; when it is blocked, one detour point
 * beside the obstacle (clear from him, clear to the destination, with floor under it) is walked first. For every
 * scripted walker of this file, not only the dock guard. */
static vec3_t detour;
static int detour_on,detour_plans;
static const int detour_side[8]={32,-32,48,-48,64,-64,96,-96};
/* PIER-GUARD-POST-STUCK-67 (the maintainer's design, 18 November 2026: "walks directly in the center of the pier"): a
 * scripted walk along fixed waypoints measured from the scene's own collision and coordinates (the dock guard: the
 * Seyda Neen pier's centre line, then aside to his post by the census office door; aw_opening.c). No path grid, no
 * detour and no side steps: the points are measured clear of every solid (tests/test_pier_guard_route.py), so a step
 * that does not go through is never steered round (the straight last leg with its detour above ended on whichever
 * side of a pier post the walk began, v0.0.66 to v0.0.67-dev2). A step the player or another actor blocks waits for
 * them on the line; a step the world blocks for 5 s ends the walk (-1) with its place printed. Every tick the walker's
 * box is tested where it stands, and a box inside a solid is counted: the opening journey asserts 0 for his walks. */
#define AW_FIXED_POINTS 8
static vec3_t fixed_point[AW_FIXED_POINTS];
static int fixed_count,fixed_at,fixed_on,fixed_waiting;
static long fixed_solid,fixed_waits,fixed_settled;
static int line_clear(vec3_t from,vec3_t to) {
    trace_t tr=SV_Move(from,walker->v.mins,walker->v.maxs,to,MOVE_NOMONSTERS,walker);
    return !tr.startsolid && !tr.allsolid && tr.fraction==1;
}
static int floor_under(vec3_t at) {
    vec3_t down;trace_t tr;
    VectorCopy(at,down);down[2]-=40;
    tr=SV_Move(at,walker->v.mins,walker->v.maxs,down,MOVE_NOMONSTERS,walker);
    return !tr.startsolid && !tr.allsolid && tr.fraction<1;
}
/* 1 when a detour point was set: the straight line to the destination is blocked and a point beside the obstacle is clear */
static int AW_NavPlanDetour(void) {
    vec3_t goal,dir,perp,candidate;trace_t tr;float length,hit,ahead;int i,j;
    if(!walker || detour_plans>=6)return 0;
    VectorCopy(destination,goal);goal[2]=walker->v.origin[2];
    VectorSubtract(goal,walker->v.origin,dir);dir[2]=0;length=(float)sqrt(dir[0]*dir[0]+dir[1]*dir[1]);
    if(length<8)return 0;
    tr=SV_Move(walker->v.origin,walker->v.mins,walker->v.maxs,goal,MOVE_NOMONSTERS,walker);
    if(!tr.startsolid && !tr.allsolid && tr.fraction==1)return 0;
    detour_plans++;
    dir[0]/=length;dir[1]/=length;perp[0]=-dir[1];perp[1]=dir[0];perp[2]=0;
    hit=tr.fraction*length;
    for(j=0;j<2;j++)for(i=0;i<8;i++){
        ahead=hit+(j?24:0);if(ahead>length)ahead=length;
        candidate[0]=walker->v.origin[0]+dir[0]*ahead+perp[0]*detour_side[i];
        candidate[1]=walker->v.origin[1]+dir[1]*ahead+perp[1]*detour_side[i];
        candidate[2]=walker->v.origin[2];
        if(line_clear(walker->v.origin,candidate) && line_clear(candidate,goal) && floor_under(candidate)){
            VectorCopy(candidate,detour);detour_on=1;best_distance=1e30f;stalled=0;
            Con_Printf("Route detour: line to %ld %ld blocked at %ld %ld; via %ld %ld\n",(long)goal[0],(long)goal[1],
                (long)tr.endpos[0],(long)tr.endpos[1],(long)candidate[0],(long)candidate[1]);
            return 1;
        }
    }
    return 0;
}
static unsigned u16(const byte *p){return p[0]+(p[1]<<8);}
static float f32(const byte *p){float f;memcpy(&f,p,4);return LittleFloat(f);}
int AW_NavDecode(const byte *data,int size) {
    int i,j,at=6,n;float f;
    node_count=edge_count=route_count=0;walker=NULL;fixed_on=0;
    if(size<6 || memcmp(data,"AWN1",4))return 0;
    n=u16(data+4);if(n<1 || n>AW_NODES)return 0;
    for(i=0;i<n;i++) {
        if(at+14>size)return 0;
        for(j=0;j<3;j++){f=f32(data+at+j*4);if(!(fabs(f)<32768))return 0;nodes[i].point[j]=f;}
        nodes[i].first=edge_count;nodes[i].count=u16(data+at+12);at+=14;
        if(nodes[i].count>n || edge_count+nodes[i].count>512 || at+nodes[i].count*2>size)return 0;
        for(j=0;j<nodes[i].count;j++){edges[edge_count]=u16(data+at);if(edges[edge_count++]>=n)return 0;at+=2;}
    }
    if(at!=size)return 0;
    node_count=n;return 1;
}
int AW_NavLoad(const char *map) {
    FILE *f=NULL;byte raw[2822];char path[48];int n;
    node_count=0;walker=NULL;fixed_on=0;
    if(strlen(map)>16 || strstr(map,"..") || strchr(map,'/'))return 0;
    sprintf(path,"intro/%s.awn",map);n=COM_FOpenFile(path,&f);
    if(!f)return 0;
    if(n<6 || n>(int)sizeof(raw) || fread(raw,1,n,f)!=(size_t)n){fclose(f);return 0;}
    fclose(f);return AW_NavDecode(raw,n);
}
static int nearest(vec3_t point) {
    int i,best=0;float d,score=1e30f;vec3_t delta;
    for(i=0;i<node_count;i++){VectorSubtract(point,nodes[i].point,delta);d=DotProduct(delta,delta);
        if(d<score){score=d;best=i;}}
    return best;
}
int AW_NavStart(edict_t *actor,vec3_t goal) {
    int previous[AW_NODES],queue[AW_NODES],head=0,tail=0,a,b,i,start,end;vec3_t entry;trace_t trace;
    walker=NULL;route_count=route_at=0;fixed_on=0;if(!node_count || !actor)return 0;
    start=nearest(actor->v.origin);end=nearest(goal);
    for(i=0;i<node_count;i++)previous[i]=-1;
    queue[tail++]=start;previous[start]=start;
    while(head<tail && previous[end]<0){a=queue[head++];
        for(i=0;i<nodes[a].count;i++){b=edges[nodes[a].first+i];if(previous[b]>=0)continue;previous[b]=a;queue[tail++]=b;}}
    if(previous[end]<0)return 0;
    a=end;while(a!=start){route[route_count++]=a;a=previous[a];}route[route_count++]=start;
    for(i=0;i<route_count/2;i++){a=route[i];route[i]=route[route_count-1-i];route[route_count-1-i]=a;}
    /* Join a clear first leg directly. Returning to the nearest grid point
     * first can make an escort double back into the following player. */
    if(route_count==1)route_at=1;
    else if(fabs(nodes[route[1]].point[2]-actor->v.origin[2])<8.75f){
        VectorCopy(nodes[route[1]].point,entry);entry[2]=actor->v.origin[2];
        trace=SV_Move(actor->v.origin,actor->v.mins,actor->v.maxs,entry,MOVE_NORMAL,actor);
        if(!trace.startsolid && !trace.allsolid && trace.fraction==1)route_at=1;
    }
    VectorCopy(goal,destination);walker=actor;blocked=animation=stalled=0;player_wait=0;best_distance=1e30f;
    detour_on=detour_plans=0;return 1;
}
/* PIER-GUARD-WALKS-INTO-DOOR-65: a walk straight to GOAL with no path grid (route_count 0: AW_NavStep steers to the
 * destination itself), for a short measured leg whose straight line is known clear; the grid's nearest point there can
 * lie where the walker must not go (the census door's corner) */
int AW_NavStartDirect(edict_t *actor,vec3_t goal) {
    walker=NULL;route_count=route_at=0;fixed_on=0;if(!actor)return 0;
    VectorCopy(goal,destination);walker=actor;blocked=animation=stalled=0;player_wait=0;best_distance=1e30f;
    detour_on=detour_plans=0;return 1;
}
/* PIER-GUARD-POST-STUCK-67: a walk through COUNT fixed points (feet points; only x and y are steered, the ground gives
 * the height), the last one the destination. 0 when there is no actor or the count is out of range. */
int AW_NavStartFixed(edict_t *actor,const vec3_t *points,int count) {
    int i;trace_t tr;float z;
    walker=NULL;route_count=route_at=0;fixed_on=0;
    if(!actor || !points || count<1 || count>AW_FIXED_POINTS)return 0;
    for(i=0;i<count;i++)VectorCopy(points[i],fixed_point[i]);
    fixed_count=count;fixed_at=0;fixed_on=1;fixed_waiting=0;
    /* PIER-GUARD-POST-STUCK-67 (the journey on the fixed route, 2026-11-18: "box in solid 1", its one tick at point 0,
     * 366 -210 17): a resident's baked placement fits his rendered soles to the floor, so his standing box can start
     * under it (the dock guard's, 5.75 units into the pier deck, top 22.75); the first step's stuck search
     * (AW_WalkPlayer's SV_CheckStuck) lifted it then. The same search here, before the first tick, so the box-in-solid
     * count is the route's own; the lift is counted apart (AW_NavFixedSettled, aw_intro_status "settled at the start").
     * No clear spot found: he stays, and the first tick counts it as before. */
    tr=SV_Move(actor->v.origin,actor->v.mins,actor->v.maxs,actor->v.origin,MOVE_NOMONSTERS,actor);
    if(tr.startsolid || tr.allsolid){
        z=actor->v.origin[2];
        if(AW_ActorSettle(actor)){
            fixed_settled++;
            Con_Printf("Fixed route: the walker's box started inside a solid at %ld %ld %ld; settled %.2f up\n",
                (long)actor->v.origin[0],(long)actor->v.origin[1],(long)z,actor->v.origin[2]-z);
        }
    }
    VectorCopy(points[count-1],destination);walker=actor;blocked=animation=stalled=0;player_wait=0;best_distance=1e30f;
    detour_on=detour_plans=0;return 1;
}
/* the walk ends where the walker stands (the dock guard meeting the player: the script's AIWander 0) */
void AW_NavStop(void) {
    eval_t *field;
    if(walker){walker->v.frame=0;field=GetEdictFieldValue(walker,"aw_moving");if(field)field->_float=0;}
    walker=NULL;fixed_on=0;
}
/* the fixed walks' check (aw_intro_status): ticks a walker's box stood inside a solid, and the times it waited for
 * someone in its way; cleared when the dock map starts (aw_opening.c AW_OpeningSpawn) */
long AW_NavFixedSolid(void){return fixed_solid;}
long AW_NavFixedWaits(void){return fixed_waits;}
long AW_NavFixedSettled(void){return fixed_settled;}
void AW_NavFixedReset(void){fixed_solid=fixed_waits=fixed_settled=0;fixed_waiting=0;}
static int fixed_stop(int result) {
    eval_t *field;
    walker->v.frame=0;field=GetEdictFieldValue(walker,"aw_moving");if(field)field->_float=0;
    walker=NULL;fixed_on=0;return result;
}
static int fixed_step(double dt) {
    vec3_t delta,move,end;float length=0,step;eval_t *field;trace_t tr;
    tr=SV_Move(walker->v.origin,walker->v.mins,walker->v.maxs,walker->v.origin,MOVE_NOMONSTERS,walker);
    if(tr.startsolid || tr.allsolid){
        if(!fixed_solid)Con_Printf("Fixed route: the walker's box is inside a solid at %ld %ld %ld (point %ld)\n",
            (long)walker->v.origin[0],(long)walker->v.origin[1],(long)walker->v.origin[2],(long)fixed_at);
        fixed_solid++;
    }
    for(;;){
        VectorSubtract(fixed_point[fixed_at],walker->v.origin,delta);delta[2]=0;
        length=(float)sqrt(delta[0]*delta[0]+delta[1]*delta[1]);
        if(length>=1 || fixed_at>=fixed_count-1)break;
        fixed_at++;
    }
    if(length<1)return fixed_stop(1);
    step=22*dt;if(step>length)step=length;
    move[0]=delta[0]*step/length;move[1]=delta[1]*step/length;move[2]=0;
    walker->v.angles[1]=Q_atan2(delta[1],delta[0])*180/M_PI-90;
    if(AW_ActorStep(walker,move,dt)){
        if(fixed_waiting){fixed_waiting=0;Con_Printf("Fixed route: the way is clear; walking on.\n");}
        blocked=0;field=GetEdictFieldValue(walker,"aw_moving");if(field)field->_float=1;
        animation+=dt;field=GetEdictFieldValue(walker,"aw_walk_step");
        walker->v.frame=13+((int)(animation/(field && field->_float>.02?field->_float:.125))%8);
        return 0;
    }
    VectorAdd(walker->v.origin,move,end);
    tr=SV_Move(walker->v.origin,walker->v.mins,walker->v.maxs,end,MOVE_NORMAL,walker);
    if(tr.ent && (tr.ent==svs.clients[0].edict || tr.ent->v.solid==SOLID_SLIDEBOX) && (tr.fraction<1 || tr.startsolid)){
        /* the player or an actor stands on the line: wait for them, never round them */
        if(!fixed_waiting){fixed_waiting=1;fixed_waits++;
            Con_Printf("Fixed route: waiting at %ld %ld for %s in the way.\n",(long)walker->v.origin[0],
                (long)walker->v.origin[1],tr.ent==svs.clients[0].edict?"the player":"an actor");}
        blocked=0;walker->v.frame=0;field=GetEdictFieldValue(walker,"aw_moving");if(field)field->_float=0;return 0;
    }
    if(blocked==0)Con_Printf("Fixed route step blocked at %ld %ld %ld, point %ld of %ld (%ld %ld): solid %ld/%ld, frac %ld\n",
        (long)walker->v.origin[0],(long)walker->v.origin[1],(long)walker->v.origin[2],(long)fixed_at,(long)fixed_count,
        (long)fixed_point[fixed_at][0],(long)fixed_point[fixed_at][1],(long)tr.startsolid,(long)tr.allsolid,
        (long)(tr.fraction*1000));
    blocked+=dt;walker->v.frame=0;
    if(blocked>5){
        Con_Printf("Fixed route blocked at %ld %ld %ld; walk held.\n",(long)walker->v.origin[0],(long)walker->v.origin[1],
            (long)walker->v.origin[2]);
        return fixed_stop(-1);
    }
    return 0;
}
/* NPC-IDLE-TRACK-PLAYER-67 (the dock guard at his post, PIER-GUARD-POST-STUCK-67): ACTOR's yaw turns toward TARGET by at
 * most RATE degrees a second, the short way round. Converted actors face local +Y: the native yaw is the world bearing
 * - 90, as the walks set it. 1 when it faces the target (within 2 degrees). */
int AW_ActorTurnToward(edict_t *actor,const vec3_t target,float rate,double dt) {
    float want,diff,turn;
    if(!actor || dt<=0)return 0;
    want=Q_atan2(target[1]-actor->v.origin[1],target[0]-actor->v.origin[0])*180/M_PI-90;
    diff=want-actor->v.angles[1];
    while(diff>180)diff-=360;
    while(diff<-180)diff+=360;
    turn=rate*(float)dt;
    if(fabs(diff)<=turn)actor->v.angles[1]+=diff;else actor->v.angles[1]+=diff>0?turn:-turn;
    while(actor->v.angles[1]>=360)actor->v.angles[1]-=360;
    while(actor->v.angles[1]<-360)actor->v.angles[1]+=360;
    return fabs(diff)<=2 || fabs(diff)<=turn;
}
int AW_NavStep(double dt,int wait_for_player) {
    vec3_t delta,move,target,side;float length,step,angle;eval_t *field;int i,moved;
    static const int avoid[6]={30,-30,60,-60,90,-90};
    if(!walker)return -1;
    if(dt<=0)return 0;
    if(dt>.1)dt=.1;
    if(fixed_on)return fixed_step(dt);
    if(wait_for_player){VectorSubtract(walker->v.origin,svs.clients[0].edict->v.origin,delta);
        if(Length(delta)>96){walker->v.frame=0;return 0;}}
    /* The final grid node may lie beyond the requested stop (including inside
     * another actor). Arriving at the actual destination on the final leg is
     * sufficient; do not walk past it merely to visit an auxiliary grid node. */
    if(route_at>=route_count-1){
        VectorSubtract(destination,walker->v.origin,delta);
        if(delta[0]*delta[0]+delta[1]*delta[1]<25 && fabs(delta[2])<20){
            walker->v.frame=0;field=GetEdictFieldValue(walker,"aw_moving");if(field)field->_float=0;walker=NULL;return 1;
        }
        /* The nearest final grid node is only a routing aid. If the actual
         * nearby destination is clear, finish there instead of steering into
         * the Census steps beyond it. Actor avoidance still runs below. */
        if(route_at<route_count && delta[0]*delta[0]+delta[1]*delta[1]<64*64 && fabs(delta[2])<20){
            trace_t tr=SV_Move(walker->v.origin,walker->v.mins,walker->v.maxs,destination,MOVE_NOMONSTERS,walker);
            if(!tr.startsolid && !tr.allsolid && tr.fraction==1){
                route_at=route_count;best_distance=1e30f;stalled=0;
            }
        }
    }
    /* the last leg: sweep the straight line first (PIER-GUARD-WALKS-INTO-DOOR-65 detour, above) */
    if(route_at>=route_count && !detour_on && (best_distance>=1e29f || stalled>1.5))AW_NavPlanDetour();
    if(route_at<route_count){VectorCopy(nodes[route[route_at]].point,target);}
    else if(detour_on){VectorCopy(detour,target);}
    else {VectorCopy(destination,target);}
    VectorSubtract(target,walker->v.origin,delta);length=(float)sqrt(delta[0]*delta[0]+delta[1]*delta[1]);
    if(detour_on && route_at>=route_count && length<6){detour_on=0;best_distance=1e30f;stalled=0;return 0;}
    if(length<5 && fabs(delta[2])<20){
        if(route_at<route_count){route_at++;best_distance=1e30f;stalled=0;return 0;}
        walker->v.frame=0;field=GetEdictFieldValue(walker,"aw_moving");if(field)field->_float=0;walker=NULL;return 1;
    }
    if(length<best_distance-.5){best_distance=length;stalled=0;}else stalled+=dt;
    if(length<.1)length=.1;
    step=22*dt;if(step>length)step=length;
    move[0]=delta[0]*step/length;move[1]=delta[1]*step/length;move[2]=0;
    /* An escort (wait_for_player) whose following player overtakes or stands
     * in the aisle waits: not a broken route; same goal, resumed when clear.
     * A plain travel (the script's AITravel, e.g. CharGenRaceNPC's walk to his
     * post beside the Census door) never waits for the player: OpenMW's
     * AiTravel steers round obstacles instead. Waiting there held the dock
     * guard in the doorway for as long as the player stood before him
     * (INTRO-DOCK-GUARD-BLOCKS-DOOR-62). */
    if(wait_for_player){
        trace_t tr;vec3_t ahead;
        VectorAdd(walker->v.origin,move,ahead);
        tr=SV_Move(walker->v.origin,walker->v.mins,walker->v.maxs,ahead,MOVE_NORMAL,walker);
        if(tr.ent==svs.clients[0].edict && (tr.fraction<1 || tr.startsolid)) {
            if(!player_wait)Con_Printf("Escort waiting for player to clear the path.\n");
            player_wait=1;blocked=stalled=0;best_distance=1e30f;walker->v.frame=0;
            field=GetEdictFieldValue(walker,"aw_moving");if(field)field->_float=0;return 0;
        }
        if(player_wait)Con_Printf("Escort path clear; resuming.\n");
        player_wait=0;
    }
    walker->v.angles[1]=Q_atan2(delta[1],delta[0])*180/M_PI-90;
    field=GetEdictFieldValue(walker,"aw_moving");if(field)field->_float=1;
    moved=AW_ActorStep(walker,move,dt);
    /* Small local steering around authored path-grid corners. Each candidate
     * still sweeps the same standing collision hull and requires floor support. */
    if(!moved)for(i=0;i<6;i++){
        angle=Q_atan2(delta[1],delta[0])+avoid[i]*M_PI/180;
        side[0]=Q_CosRad(angle)*step;side[1]=Q_SinRad(angle)*step;side[2]=0;
        /* The side-step keeps the walker facing his travel direction: turning
         * him to each +-30..90 degree candidate spun him on the spot
         * (INTRO-DOCK-GUARD-BLOCKS-DOOR-62). */
        if(AW_ActorStep(walker,side,dt)){moved=1;break;}
    }
    if(moved)blocked=0;else {
        if(blocked==0){trace_t tr;vec3_t end;VectorAdd(walker->v.origin,move,end);
            tr=SV_Move(walker->v.origin,walker->v.mins,walker->v.maxs,end,MOVE_NORMAL,walker);
            Con_Printf("Route step blocked: node %ld, target %ld %ld %ld, solid %ld/%ld, frac %ld, floor %ld\n",
                (long)route_at,(long)target[0],(long)target[1],(long)target[2],(long)tr.startsolid,(long)tr.allsolid,(long)(tr.fraction*1000),(long)walker->v.flags);}
        blocked+=dt;
    }
    animation+=dt;field=GetEdictFieldValue(walker,"aw_walk_step");
    walker->v.frame=13+((int)(animation/(field && field->_float>.02?field->_float:.125))%8);
    if(blocked>5 || stalled>8){Con_Printf("Escort blocked at %ld %ld %ld; route held.\n",(long)walker->v.origin[0],(long)walker->v.origin[1],(long)walker->v.origin[2]);
        Con_Printf("Route target %ld: %ld %ld %ld, distance %ld, height error %ld\n",(long)route_at,(long)target[0],(long)target[1],(long)target[2],(long)length,(long)delta[2]);
        walker->v.frame=0;field=GetEdictFieldValue(walker,"aw_moving");if(field)field->_float=0;walker=NULL;return -1;}
    return 0;
}
