/* SPDX-License-Identifier: GPL-2.0-or-later
 * Budgeted local navigation for follower NPCs (docs/DEBUG_OVERLAYS.md,
 * "NPC companion test").
 *
 * Quake first: SV_movetogoal (sv_move.c) keeps walking its ideal_yaw and,
 * when a step fails, SV_NewChaseDir tries the directions nearest the goal
 * first and keeps the first one that moves. The ladder here is the same
 * idea with the standing hull and a hard trace budget:
 *   1. follow: walk straight at the goal (the owner's step physics climb
 *      stairs like the player); no search at all while that makes progress;
 *   2. ping: when it stalls, a fan of short hull sweeps around the follower,
 *      nearest the goal first; the first clear one that brings it nearer is
 *      walked for a few thinks (a detour), as Quake keeps its chase dir;
 *   3. flood: when detours keep failing, an 8 x 8 step-cell breadth-first
 *      flood fill around the follower; the reached cell nearest the goal is
 *      walked cell by cell.
 * At most AW_PATH_TRACES traces per think: a ping or a flood fill spreads
 * over several thinks with a cursor. Integer only, no allocation: one small
 * state per follower and one shared static scratch for the flood fill.
 */
#include <string.h>
#include "aw_npcpath.h"

/* Heading k points at k * 11.25 degrees, length 64. */
const signed char aw_path_fan[AW_PATH_FAN][2]={
    {64,0},{63,12},{59,24},{53,36},{45,45},{36,53},{24,59},{12,63},
    {0,64},{-12,63},{-24,59},{-36,53},{-45,45},{-53,36},{-59,24},{-63,12},
    {-64,0},{-63,-12},{-59,-24},{-53,-36},{-45,-45},{-36,-53},{-24,-59},{-12,-63},
    {0,-64},{12,-63},{24,-59},{36,-53},{45,-45},{53,-36},{59,-24},{63,-12}};
aw_path_stats_t aw_path_stats;

/* The flood fill's scratch, shared: one follower floods at a time. */
static struct {
    unsigned int open[2], seen[2];          /* 64-cell masks: walkable, classified */
    unsigned char queue[AW_PATH_CELLS];     /* breadth-first queue of cells */
    unsigned char parent[AW_PATH_CELLS];    /* where each cell was reached from */
    signed char height[AW_PATH_CELLS];      /* floor height - gz */
    unsigned char head, tail, best, side;   /* side: next neighbour of queue[head] */
    const aw_path_t *owner;
} scratch;

#define BIT(m,i) (((m)[(i)>>5]>>((i)&31))&1u)
#define SET(m,i) ((m)[(i)>>5]|=1u<<((i)&31))

int AW_PathScratchBytes(void) {return (int)sizeof(scratch);}

static int clamp(int v,int limit) {return v>limit?limit:v<-limit?-limit:v;}
static int absolute(int v) {return v<0?-v:v;}
/* Squared distance with clamped components: fits 32 bits. */
static int distance2(int dx,int dy) {dx=clamp(dx,16384);dy=clamp(dy,16384);return dx*dx+dy*dy;}

int AW_PathHeading(int dx,int dy) {
    int i,best=0,dot,score=-2147483647;
    dx=clamp(dx,16384);dy=clamp(dy,16384);
    for(i=0;i<AW_PATH_FAN;i++){
        dot=dx*aw_path_fan[i][0]+dy*aw_path_fan[i][1];
        if(dot>score){score=dot;best=i;}
    }
    return best;
}

int AW_PathLength(int dx,int dy) {
    dx=absolute(clamp(dx,1<<24));dy=absolute(clamp(dy,1<<24));
    return dx>dy?dx+dy*3/8:dy+dx*3/8;
}

int AW_PathSpeed(int mimic,int player_speed,int gap,int distance) {
    int speed,left=gap-distance,ease=distance/2>16?distance/2:16;
    if(left<=0)return 0;
    if(!mimic)speed=gap>2*distance?AW_PATH_RUN_SPEED:AW_PATH_WALK_SPEED;
    else {
        speed=player_speed<AW_PATH_SPEED_MIN?AW_PATH_WALK_SPEED:player_speed;
        if(gap>2*distance)speed+=speed/4;   /* catch up */
    }
    if(speed>AW_PATH_SPEED_MAX)speed=AW_PATH_SPEED_MAX;
    if(left<ease){speed=speed*left/ease;if(speed<AW_PATH_SPEED_MIN)speed=AW_PATH_SPEED_MIN;}
    return speed;
}

int AW_PathStuckResponse(int kind,int method,int in_combat,int out_of_view) {
    if(kind==AW_ACTOR_HOSTILE)return method==1?AW_STUCK_FLEE:AW_STUCK_RETRY;   /* never warp */
    if(kind==AW_ACTOR_SUMMON && in_combat)return AW_STUCK_RETRY;              /* hold and fight */
    if(method==0)return AW_STUCK_PLACE;
    if(method==1)return out_of_view?AW_STUCK_PLACE:AW_STUCK_WAIT_UNSEEN;
    return AW_STUCK_RETRY;
}
const char *AW_PathStuckName(int response) {
    static const char *const names[AW_STUCK_RESPONSES]={"keep trying","placed","wait until unseen","flee"};
    return response>=0 && response<AW_STUCK_RESPONSES?names[response]:"?";
}
const char *AW_PathKindName(int kind) {
    static const char *const names[AW_ACTOR_KINDS]={"follower","summon","hostile"};
    return kind>=0 && kind<AW_ACTOR_KINDS?names[kind]:"?";
}

static void release(const aw_path_t *s) {if(scratch.owner==s)scratch.owner=NULL;}

void AW_PathReset(aw_path_t *s,int x,int y) {
    release(s);memset(s,0,sizeof(*s));s->x=x;s->y=y;s->mode=AW_PATH_FOLLOW;
}
void AW_PathIdle(aw_path_t *s,int x,int y) {AW_PathReset(s,x,y);}

/* Did the last think's move cover at least a quarter step along its heading? */
static int progress(const aw_path_t *s,const int self[3],int step) {
    int dx=clamp(self[0]-s->x,4096),dy=clamp(self[1]-s->y,4096);
    return (dx*aw_path_fan[s->heading][0]+dy*aw_path_fan[s->heading][1])*4>=step*AW_PATH_FAN_RADIUS;
}

static void begin_flood(aw_path_t *s,const int self[3]) {
    const int start=3*AW_PATH_GRID+3;
    s->mode=AW_PATH_FLOOD;s->cursor=0;
    if(scratch.owner && scratch.owner!=s){s->cursor=1;return;}  /* wait for the scratch */
    /* The follower stands at the centre of cell (3,3). */
    s->gx=self[0]-3*AW_PATH_CELL-AW_PATH_CELL/2;s->gy=self[1]-3*AW_PATH_CELL-AW_PATH_CELL/2;s->gz=self[2];
    memset(&scratch,0,sizeof(scratch));scratch.owner=s;
    SET(scratch.open,start);SET(scratch.seen,start);
    scratch.parent[start]=start;scratch.queue[0]=start;scratch.tail=1;scratch.best=start;
    aw_path_stats.floods++;
}

static void begin_ping(aw_path_t *s,const int self[3],int dx,int dy) {
    s->stall=s->run=0;
    /* Two flood routes that led back into a stall: give up (the owner
     * teleports); the next stall after that floods again. */
    if(++s->pings>AW_PATH_PINGS+2){s->mode=AW_PATH_LOST;s->pings=AW_PATH_PINGS;aw_path_stats.lost++;return;}
    if(s->pings>AW_PATH_PINGS){begin_flood(s,self);return;}
    s->mode=AW_PATH_PING;s->cursor=1;s->fallback=0;s->base=(unsigned char)AW_PathHeading(dx,dy);
    aw_path_stats.pings++;
}

/* Ping slot k: 0, +2, -2, +4, -4 ... +16 headings from the goal (22.5 degree
 * steps). Slot 0, straight at the goal, is what just stalled; it is skipped. */
static int slot_heading(int base,int slot) {
    int m=(slot+1)/2,offset=(slot&1)?2*m:-2*m;
    return (base+offset)&(AW_PATH_FAN-1);
}

static int goal_cell(int v,int corner) {
    int c=v-corner;c=c<0?-1:c/AW_PATH_CELL;
    return c<0?0:c>=AW_PATH_GRID?AW_PATH_GRID-1:c;
}

static int cell_score(int c,int gcx,int gcy) {return absolute((c&7)-gcx)+absolute((c>>3)-gcy);}

/* Route: the first AW_PATH_ROUTE cells from the start to the best cell. */
static void keep_route(aw_path_t *s) {
    int c=scratch.best,length=0,i;
    while(c!=scratch.parent[c]){length++;c=scratch.parent[c];}
    s->steps=(unsigned char)(length<AW_PATH_ROUTE?length:AW_PATH_ROUTE);s->at=0;
    for(c=scratch.best,i=length-1;c!=scratch.parent[c];c=scratch.parent[c],i--)
        if(i<AW_PATH_ROUTE)s->route[i]=(unsigned char)c;
}

static int flood(aw_path_t *s,const aw_path_io_t *io,const int goal[3],int *used) {
    static const signed char side[4][2]={{1,0},{0,1},{-1,0},{0,-1}};
    int gcx=goal_cell(goal[0],s->gx),gcy=goal_cell(goal[1],s->gy),c,n,x,y,z,floor,rise,k;
    while(*used<AW_PATH_TRACES && scratch.head<scratch.tail){
        c=scratch.queue[scratch.head];k=scratch.side++;
        if(scratch.side>=4){scratch.side=0;scratch.head++;}
        x=(c&7)+side[k][0];y=(c>>3)+side[k][1];
        if(x<0 || y<0 || x>=AW_PATH_GRID || y>=AW_PATH_GRID)continue;
        n=y*AW_PATH_GRID+x;
        if(BIT(scratch.seen,n))continue;
        SET(scratch.seen,n);++*used;aw_path_stats.flood_cells++;aw_path_stats.traces++;
        z=s->gz+scratch.height[c];
        if(!io->cell(io->context,s->gx+x*AW_PATH_CELL+AW_PATH_CELL/2,s->gy+y*AW_PATH_CELL+AW_PATH_CELL/2,z,&floor))continue;
        rise=floor-z;if(rise>AW_PATH_STEP || rise<-AW_PATH_STEP)continue;
        rise=floor-s->gz;if(rise>127 || rise<-127)continue;
        SET(scratch.open,n);scratch.parent[n]=(unsigned char)c;scratch.height[n]=(signed char)rise;
        scratch.queue[scratch.tail++]=(unsigned char)n;
        if(cell_score(n,gcx,gcy)<cell_score(scratch.best,gcx,gcy))scratch.best=(unsigned char)n;
        if(n==gcy*AW_PATH_GRID+gcx){scratch.head=scratch.tail;break;}
    }
    return scratch.head>=scratch.tail;
}

int AW_PathThink(aw_path_t *s,const aw_path_io_t *io,const int self[3],const int goal[3],int step,int *heading) {
    int used=0,moving,dx,dy,h,i,tx,ty;
    aw_path_stats.thinks++;
    if(step<1)step=1;
    moving=s->mode==AW_PATH_FOLLOW || s->mode==AW_PATH_DETOUR || s->mode==AW_PATH_WALK;
    i=moving && progress(s,self,step);
    s->x=self[0];s->y=self[1];
    dx=goal[0]-self[0];dy=goal[1]-self[1];
    switch(s->mode){
    case AW_PATH_FOLLOW:
        if(i){s->stall=0;if(s->run<255 && ++s->run>=2*AW_PATH_COMMIT)s->pings=0;}
        else {s->run=0;if(++s->stall>=AW_PATH_STALL){aw_path_stats.stuck++;begin_ping(s,self,dx,dy);break;}}
        *heading=s->heading=(unsigned char)AW_PathHeading(dx,dy);return 1;
    case AW_PATH_DETOUR:
        if(!i){begin_ping(s,self,dx,dy);break;}
        if(--s->commit==0){s->mode=AW_PATH_FOLLOW;s->stall=0;s->heading=(unsigned char)AW_PathHeading(dx,dy);}
        *heading=s->heading;return 1;
    case AW_PATH_WALK:
        if(i)s->stall=0;
        else if(++s->stall>=AW_PATH_STALL){begin_ping(s,self,dx,dy);break;}
        for(;;){
            tx=s->gx+(s->route[s->at]&7)*AW_PATH_CELL+AW_PATH_CELL/2-self[0];
            ty=s->gy+(s->route[s->at]>>3)*AW_PATH_CELL+AW_PATH_CELL/2-self[1];
            if(absolute(tx)+absolute(ty)>(step>4?step:4))break;
            if(++s->at>=s->steps){
                s->mode=AW_PATH_FOLLOW;s->stall=s->run=0;
                *heading=s->heading=(unsigned char)AW_PathHeading(dx,dy);return 1;
            }
        }
        *heading=s->heading=(unsigned char)AW_PathHeading(tx,ty);return 1;
    case AW_PATH_LOST:
        /* Stand; the goal may move somewhere reachable. Retry later. */
        if(++s->stall>=4*AW_PATH_STALL){s->mode=AW_PATH_FOLLOW;s->stall=s->run=s->pings=0;}
        return 0;
    }
    if(s->mode==AW_PATH_PING){
        while(used<AW_PATH_TRACES && s->cursor<AW_PATH_PING_DIRS){
            h=slot_heading(s->base,s->cursor++);used++;aw_path_stats.ping_traces++;aw_path_stats.traces++;
            if(!io->sweep(io->context,aw_path_fan[h][0]*AW_PATH_PROBE/AW_PATH_FAN_RADIUS,
                          aw_path_fan[h][1]*AW_PATH_PROBE/AW_PATH_FAN_RADIUS))continue;
            tx=dx-aw_path_fan[h][0]*AW_PATH_PROBE/AW_PATH_FAN_RADIUS;
            ty=dy-aw_path_fan[h][1]*AW_PATH_PROBE/AW_PATH_FAN_RADIUS;
            if(distance2(tx,ty)<distance2(dx,dy)){s->fallback=(unsigned char)(h+1);s->cursor=AW_PATH_PING_DIRS;break;}
            if(!s->fallback)s->fallback=(unsigned char)(h+1);
        }
        if(s->cursor<AW_PATH_PING_DIRS)return 0;
        if(s->fallback){
            s->mode=AW_PATH_DETOUR;s->commit=AW_PATH_COMMIT;s->heading=(unsigned char)(s->fallback-1);
            aw_path_stats.detours++;*heading=s->heading;return 1;
        }
        begin_flood(s,self);
    }
    if(s->mode==AW_PATH_FLOOD){
        if(s->cursor){if(scratch.owner)return 0;begin_flood(s,self);}  /* waiting for the scratch */
        else if(scratch.owner!=s)begin_flood(s,self);                     /* taken over: start again */
        if(!flood(s,io,goal,&used))return 0;
        release(s);
        if(scratch.best==3*AW_PATH_GRID+3){s->mode=AW_PATH_LOST;s->stall=0;aw_path_stats.lost++;return 0;}
        keep_route(s);s->mode=AW_PATH_WALK;s->stall=0;aw_path_stats.routes++;
    }
    return 0;
}
