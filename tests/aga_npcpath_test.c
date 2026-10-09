/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_npcpath.c on synthetic layouts: the ping picks the open direction that
 * brings the follower nearer, the flood fill finds the way out of a pocket,
 * no think spends more than AW_PATH_TRACES traces, follow speed tracks the
 * player, caps and eases, and the state stays small. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_npcpath.h"

typedef struct {int x0,y0,x1,y1;} box_t;
static box_t walls[8];static int wall_count;
static int calls,think_calls,max_calls,ledge_x=100000;
static int pos[3];

/* The follower is a point; walls are inflated by the hull's half width. */
static int blocked(int x,int y) {
    int i;
    for(i=0;i<wall_count;i++)
        if(x>walls[i].x0-7 && x<walls[i].x1+7 && y>walls[i].y0-7 && y<walls[i].y1+7)return 1;
    return 0;
}
static int segment_clear(int x,int y,int dx,int dy) {
    int i,n=(dx<0?-dx:dx)+(dy<0?-dy:dy);
    if(n<1)n=1;
    for(i=1;i<=n;i++)if(blocked(x+dx*i/n,y+dy*i/n))return 0;
    return 1;
}
static int sweep(void *context,int dx,int dy) {
    (void)context;calls++;think_calls++;return segment_clear(pos[0],pos[1],dx,dy);
}
static int cell(void *context,int x,int y,int z,int *floor) {
    (void)context;(void)z;calls++;think_calls++;
    if(blocked(x,y))return 0;
    *floor=x>=ledge_x?12:0;return 1;
}
static const aw_path_io_t io={NULL,sweep,cell};
static void wall(int x0,int y0,int x1,int y1) {box_t b={x0,y0,x1,y1};walls[wall_count++]=b;}

/* One think plus the owner's step: walk the heading if the way is clear. */
static int think(aw_path_t *s,const int goal[3],int step,int *heading) {
    int r,dx,dy;
    think_calls=0;r=AW_PathThink(s,&io,pos,goal,step,heading);
    assert(think_calls<=AW_PATH_TRACES);
    if(think_calls>max_calls)max_calls=think_calls;
    if(r){
        dx=aw_path_fan[*heading][0]*step/AW_PATH_FAN_RADIUS;dy=aw_path_fan[*heading][1]*step/AW_PATH_FAN_RADIUS;
        if(segment_clear(pos[0],pos[1],dx,dy)){pos[0]+=dx;pos[1]+=dy;}
    }
    return r;
}
static int near_goal(const int goal[3],int range) {
    int dx=goal[0]-pos[0],dy=goal[1]-pos[1];return dx*dx+dy*dy<=range*range;
}

static void headings(void) {
    assert(AW_PathHeading(10,0)==0 && AW_PathHeading(0,10)==8 && AW_PathHeading(-10,0)==16 && AW_PathHeading(0,-10)==24);
    assert(AW_PathHeading(10,10)==4 && AW_PathHeading(100000,1)==0);
    assert(AW_PathLength(300,0)==300 && AW_PathLength(0,-80)==80);
    assert(AW_PathLength(100,100)>=137 && AW_PathLength(100,100)<=145);   /* true 141 */
}

/* A wall across the straight line to a diagonal goal: the ping's first clear
 * sweep that brings the follower nearer is straight up (+Y), found over two
 * thinks (3 sweeps: 2 in the think that stalled, 1 in the next), then the
 * follower gets round. */
static void ping_picks_nearer_direction(void) {
    aw_path_t s;int goal[3]={300,300,0},h,i,ping_thinks=0;
    wall_count=0;wall(16,-200,24,200);
    pos[0]=pos[1]=pos[2]=0;AW_PathReset(&s,0,0);memset(&aw_path_stats,0,sizeof(aw_path_stats));
    for(i=0;i<20 && s.mode==AW_PATH_FOLLOW;i++)think(&s,goal,12,&h);
    assert(s.mode==AW_PATH_PING && aw_path_stats.stuck==1 && pos[0]<10);
    for(i=0;i<8 && s.mode==AW_PATH_PING;i++){think(&s,goal,12,&h);ping_thinks++;}
    assert(s.mode==AW_PATH_DETOUR && h==8 && ping_thinks==1);   /* stall think: 2 sweeps, next: 1 */
    assert(aw_path_stats.ping_traces>=3 && aw_path_stats.ping_traces<=4);
    for(i=0;i<400 && !near_goal(goal,24);i++)think(&s,goal,12,&h);
    assert(near_goal(goal,24));
    printf("ping: %lu pings, %lu sweeps, %lu floods\n",aw_path_stats.pings,aw_path_stats.ping_traces,aw_path_stats.floods);
}

/* A blocked corner, only +Y open: the first ping takes a clear heading on the
 * open side (none brings it nearer: the fallback) and never a blocked one. */
static void ping_takes_open_side(void) {
    aw_path_t s;int goal[3]={300,0,0},h,i;
    wall_count=0;wall(16,-200,24,40);wall(-200,-24,24,-16);
    pos[0]=pos[1]=pos[2]=0;AW_PathReset(&s,0,0);memset(&aw_path_stats,0,sizeof(aw_path_stats));
    for(i=0;i<40 && s.mode!=AW_PATH_DETOUR;i++)think(&s,goal,12,&h);
    assert(s.mode==AW_PATH_DETOUR && aw_path_fan[h][1]>0);
    assert(segment_clear(0,0,aw_path_fan[h][0]/2,aw_path_fan[h][1]/2));
    for(i=0;i<600 && !near_goal(goal,24);i++)think(&s,goal,12,&h);
    assert(near_goal(goal,24));
}

/* A pocket closed toward the goal: pings fail, the flood fill (8 x 8 cells)
 * finds the way out west and round, at most two cells a think. */
static void flood_finds_exit(void) {
    aw_path_t s;int goal[3]={400,0,0},h,i,flooded=0,first=-1;
    wall_count=0;wall(24,-40,32,40);wall(-10,24,32,32);wall(-10,-32,32,-24);
    pos[0]=pos[1]=pos[2]=0;AW_PathReset(&s,0,0);memset(&aw_path_stats,0,sizeof(aw_path_stats));
    for(i=0;i<300 && !flooded;i++){think(&s,goal,12,&h);if(s.mode==AW_PATH_WALK){flooded=1;first=s.route[0];}}
    assert(flooded && aw_path_stats.floods>=1 && aw_path_stats.routes>=1);
    assert(first==3*AW_PATH_GRID+2);     /* first step: the west neighbour, away from the goal */
    assert(s.steps>=8);                   /* out west, north, east and down round the pocket */
    for(i=0;i<1500 && !near_goal(goal,40);i++)think(&s,goal,12,&h);
    assert(near_goal(goal,40));
    printf("flood: %lu floods, %lu cells, %lu routes, max %d traces a think\n",
        aw_path_stats.floods,aw_path_stats.flood_cells,aw_path_stats.routes,max_calls);
}

/* Fully boxed in: the flood fill reports lost (the owner teleports). */
static void flood_lost_when_enclosed(void) {
    aw_path_t s;int goal[3]={400,0,0},h,i;
    wall_count=0;wall(24,-40,32,40);wall(-40,24,32,32);wall(-40,-32,32,-24);wall(-40,-40,-32,40);
    pos[0]=pos[1]=pos[2]=0;AW_PathReset(&s,0,0);memset(&aw_path_stats,0,sizeof(aw_path_stats));
    for(i=0;i<400 && s.mode!=AW_PATH_LOST;i++)think(&s,goal,12,&h);
    assert(s.mode==AW_PATH_LOST && aw_path_stats.lost==1);
    assert(!think(&s,goal,12,&h));
}

/* A floor 12 units up (more than a step) is not a flood cell. */
static void flood_refuses_ledge(void) {
    aw_path_t s;int goal[3]={400,0,0},h,i;
    wall_count=0;wall(24,-40,32,40);wall(-10,24,32,32);wall(-10,-32,32,-24);
    ledge_x=-12;   /* everything west of the pocket is a ledge */
    pos[0]=pos[1]=pos[2]=0;AW_PathReset(&s,0,0);memset(&aw_path_stats,0,sizeof(aw_path_stats));
    for(i=0;i<400 && s.mode!=AW_PATH_LOST && s.mode!=AW_PATH_WALK;i++)think(&s,goal,12,&h);
    assert(s.mode==AW_PATH_LOST);
    ledge_x=100000;
}

/* Idle: no traces at all. */
static void idle_costs_nothing(void) {
    aw_path_t s;
    AW_PathReset(&s,0,0);calls=0;AW_PathIdle(&s,5,5);assert(calls==0 && s.mode==AW_PATH_FOLLOW);
}

static void speeds(void) {
    /* mimic: tracks the player's speed; standing player -> walking pace */
    assert(AW_PathSpeed(1,150,180,96)==150);
    assert(AW_PathSpeed(1,0,180,96)==AW_PATH_WALK_SPEED);
    /* catch-up: a quarter more beyond twice the distance, capped */
    assert(AW_PathSpeed(1,150,250,96)==187);
    assert(AW_PathSpeed(1,320,600,96)==AW_PATH_SPEED_MAX);
    assert(AW_PathSpeed(1,1000,180,96)==AW_PATH_SPEED_MAX);
    /* easing over the last half distance, never below the minimum, 0 inside */
    assert(AW_PathSpeed(1,200,96+24,96)==200*24/48);
    assert(AW_PathSpeed(1,200,97,96)==AW_PATH_SPEED_MIN);
    assert(AW_PathSpeed(1,200,96,96)==0 && AW_PathSpeed(0,200,50,96)==0);
    assert(AW_PathSpeed(1,200,96+30,96)<AW_PathSpeed(1,200,96+40,96));
    /* mimic off: walk, run beyond twice the distance */
    assert(AW_PathSpeed(0,300,180,96)==AW_PATH_WALK_SPEED && AW_PathSpeed(0,0,250,96)==AW_PATH_RUN_SPEED);
}

int main(void) {
    setvbuf(stdout,NULL,_IONBF,0);
    assert(sizeof(aw_path_t)<64);
    assert(AW_PathScratchBytes()<512);
    headings();speeds();idle_costs_nothing();
    ping_picks_nearer_direction();ping_takes_open_side();
    flood_finds_exit();flood_lost_when_enclosed();flood_refuses_ledge();
    assert(max_calls<=AW_PATH_TRACES);
    printf("state %d bytes, scratch %d bytes\n",(int)sizeof(aw_path_t),AW_PathScratchBytes());
    return 0;
}
