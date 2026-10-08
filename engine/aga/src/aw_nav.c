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
static unsigned u16(const byte *p){return p[0]+(p[1]<<8);}
static float f32(const byte *p){float f;memcpy(&f,p,4);return LittleFloat(f);}
int AW_NavDecode(const byte *data,int size) {
    int i,j,at=6,n;float f;
    node_count=edge_count=route_count=0;walker=NULL;
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
    node_count=0;walker=NULL;
    if(strlen(map)>16 || strstr(map,"..") || strchr(map,'/'))return 0;
    sprintf(path,"intro/%s.awn",map);n=COM_FOpenFile(path,&f);
    if(!f)return 0;
    if(n<6 || n>sizeof(raw) || fread(raw,1,n,f)!=n){fclose(f);return 0;}
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
    walker=NULL;route_count=route_at=0;if(!node_count || !actor)return 0;
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
    VectorCopy(goal,destination);walker=actor;blocked=animation=stalled=0;player_wait=0;best_distance=1e30f;return 1;
}
int AW_NavStep(double dt,int wait_for_player) {
    vec3_t delta,move,target,side;float length,step,angle;eval_t *field;int i,moved;
    static const int avoid[6]={30,-30,60,-60,90,-90};
    if(!walker)return -1;
    if(dt<=0)return 0;
    if(dt>.1)dt=.1;
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
    if(route_at<route_count){VectorCopy(nodes[route[route_at]].point,target);}
    else {VectorCopy(destination,target);}
    VectorSubtract(target,walker->v.origin,delta);length=(float)sqrt(delta[0]*delta[0]+delta[1]*delta[1]);
    if(length<5 && fabs(delta[2])<20){
        if(route_at<route_count){route_at++;best_distance=1e30f;stalled=0;return 0;}
        walker->v.frame=0;field=GetEdictFieldValue(walker,"aw_moving");if(field)field->_float=0;walker=NULL;return 1;
    }
    if(length<best_distance-.5){best_distance=length;stalled=0;}else stalled+=dt;
    if(length<.1)length=.1;
    step=22*dt;if(step>length)step=length;
    move[0]=delta[0]*step/length;move[1]=delta[1]*step/length;move[2]=0;
    /* A following player can overtake or stand in the aisle. This is a wait,
     * not a broken path-grid route. Keep the same goal and resume when clear. */
    {
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
        if(AW_ActorStep(walker,side,dt)){moved=1;walker->v.angles[1]=angle*180/M_PI-90;break;}
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
