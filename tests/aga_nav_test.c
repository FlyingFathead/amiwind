/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
server_static_t svs;
static int obstruct,no_backward,player_blocks,straight_blocked;static float wall=1000,highest_y;static eval_t moving,walkstep;
static float identity(float f){return f;}
float (*LittleFloat)(float)=identity;
void Con_Printf(char *s,...){}
eval_t *GetEdictFieldValue(edict_t *e,char *s){return !strcmp(s,"aw_moving")?&moving:&walkstep;}
/* PIER-GUARD-WALKS-INTO-DOOR-65: a round pylon (centre PX PY, radius PR) on the straight line, the walker's half width 4 */
static int pylon;static float PX=20,PY=0,PR=10;
static float segment_distance(vec3_t a,vec3_t b){float dx=b[0]-a[0],dy=b[1]-a[1],l=dx*dx+dy*dy,t=l>0?((PX-a[0])*dx+(PY-a[1])*dy)/l:0;
    if(t<0)t=0;if(t>1)t=1;dx=a[0]+t*dx-PX;dy=a[1]+t*dy-PY;return (float)sqrt(dx*dx+dy*dy);}
/* PIER-GUARD-POST-STUCK-67: the player standing on a fixed route's line (the step fails, the trace names the player),
 * and a walker whose box stands inside a solid (the zero-length trace starts solid) */
static int player_on_line,inside;
/* the journey's "box in solid 1" (2026-11-18): a walker whose box starts under the floor at his placement (the dock
 * guard's, 5.75 into the pier deck), lifted by the stuck search (aw_walk.c AW_ActorSettle) unless it finds no spot */
static int start_inside,settle_fails;
qboolean AW_ActorSettle(edict_t *e){if(!start_inside || settle_fails)return false;start_inside=0;e->v.origin[2]+=5.75f;return true;}
qboolean AW_ActorStep(edict_t *e,vec3_t delta,double dt){
    if(player_on_line)return false;
    if(pylon){vec3_t end;VectorAdd(e->v.origin,delta,end);if(segment_distance(e->v.origin,end)<PR+4)return false;}
    if(obstruct || (straight_blocked && fabs(delta[1])<1e-4f) || (no_backward && delta[0]<0) || e->v.origin[0]+delta[0]>wall)return false;VectorAdd(e->v.origin,delta,e->v.origin);if(e->v.origin[1]>highest_y)highest_y=e->v.origin[1];return true;}
trace_t SV_Move(vec3_t a,vec3_t mi,vec3_t ma,vec3_t b,int type,edict_t *e){trace_t t;memset(&t,0,sizeof(t));t.fraction=obstruct || player_blocks?0:1;
    if(pylon){if(a[2]!=b[2])t.fraction=.5f;   /* the floor under every point */
        else if(segment_distance(a,b)<PR+4){t.fraction=.5f;VectorAdd(a,b,t.endpos);VectorScale(t.endpos,.5f,t.endpos);}}if(player_blocks)t.ent=svs.clients[0].edict;
    if((inside || start_inside) && a==b){t.startsolid=t.allsolid=1;t.fraction=0;}
    if(player_on_line && a!=b){t.fraction=0;t.ent=svs.clients[0].edict;}
    return t;}
static void node(byte *p,float x,int degree,int next){float y=0;memcpy(p,&x,4);memcpy(p+4,&y,4);memcpy(p+8,&y,4);p[12]=degree;p[14]=next;}
int main(void){
    byte grid[54];edict_t actor,player;client_t client;vec3_t goal={40,0,0};int i,result;
    memset(grid,0,sizeof(grid));memcpy(grid,"AWN1",4);grid[4]=3;
    node(grid+6,0,1,1);node(grid+22,20,1,2);node(grid+38,40,1,2);
    assert(AW_NavDecode(grid,sizeof(grid)));grid[52]=3;assert(!AW_NavDecode(grid,sizeof(grid)));grid[52]=2;
    assert(!AW_NavDecode(grid,sizeof(grid)-1));assert(AW_NavDecode(grid,sizeof(grid)));
    memset(&actor,0,sizeof(actor));memset(&player,0,sizeof(player));client.edict=&player;svs.clients=&client;
    assert(AW_NavStart(&actor,goal));for(i=0;i<100;i++){result=AW_NavStep(.1,0);if(result)break;}
    assert(result==1 && actor.v.origin[0]>35 && actor.v.origin[0]<=40 && !moving._float);
    /* Goal is before the last graph node. A wall beyond it must not prevent arrival. */
    actor.v.origin[0]=0;goal[0]=35;wall=36;assert(AW_NavStart(&actor,goal));
    for(i=0;i<100;i++){result=AW_NavStep(.1,0);if(result)break;}
    assert(result==1 && actor.v.origin[0]>30 && actor.v.origin[0]<=36);goal[0]=40;wall=1000;
    /* An auxiliary endpoint beyond a clear nearby stop must not pull the
     * escort sideways onto the steps. Preserve the route until its last leg. */
    {float y=18;memcpy(grid+42,&y,4);assert(AW_NavDecode(grid,sizeof(grid)));}
    memset(&actor,0,sizeof(actor));highest_y=0;goal[0]=35;
    assert(AW_NavStart(&actor,goal));
    for(i=0;i<100;i++){result=AW_NavStep(.1,0);if(result)break;}
    assert(result==1 && highest_y<.01f);
    node(grid+38,40,1,2);assert(AW_NavDecode(grid,sizeof(grid)));goal[0]=40;
    actor.v.origin[0]=8;no_backward=1;assert(AW_NavStart(&actor,goal));
    for(i=0;i<100;i++){result=AW_NavStep(.1,0);if(result)break;}
    assert(result==1 && actor.v.origin[0]>35);no_backward=0;
    actor.v.origin[0]=0;obstruct=1;assert(AW_NavStart(&actor,goal));for(i=0;i<100;i++){result=AW_NavStep(.1,0);if(result)break;}
    assert(result==-1 && actor.v.origin[0]==0 && !moving._float);
    obstruct=0;actor.v.origin[0]=0;player_blocks=1;assert(AW_NavStart(&actor,goal));
    for(i=0;i<200;i++)assert(AW_NavStep(.1,1)==0);
    assert(actor.v.origin[0]==0 && !moving._float);player_blocks=0;
    for(i=0;i<100;i++){result=AW_NavStep(.1,0);if(result)break;}assert(result==1);
    /* INTRO-DOCK-GUARD-BLOCKS-DOOR-62: a plain travel (AITravel, the dock
     * guard's walk to his post) never waits for a player in his way; he
     * steps round and arrives. */
    actor.v.origin[0]=0;actor.v.origin[1]=0;player_blocks=1;assert(AW_NavStart(&actor,goal));
    for(i=0;i<100;i++){result=AW_NavStep(.1,0);if(result)break;}
    assert(result==1 && actor.v.origin[0]>35);player_blocks=0;
    /* Side-steps round a blocked straight step keep him facing his travel
     * direction (+X = yaw -90): never turned to each candidate (the spin). */
    actor.v.origin[0]=0;actor.v.origin[1]=0;straight_blocked=1;assert(AW_NavStart(&actor,goal));
    for(i=0;i<5;i++){assert(AW_NavStep(.1,0)==0);assert(fabs(actor.v.angles[1]+90)<15);}
    assert(actor.v.origin[0]>0);straight_blocked=0;
    actor.v.origin[0]=0;actor.v.origin[1]=0;
    player.v.origin[0]=300;assert(AW_NavStart(&actor,goal));assert(AW_NavStep(.1,1)==0 && actor.v.origin[0]==0);
    assert(AW_NavDecode(grid,sizeof(grid)));goal[0]=0;actor.v.origin[0]=40;assert(!AW_NavStart(&actor,goal));
    /* PIER-GUARD-WALKS-INTO-DOOR-65 (v0.0.66-dev1): a direct walk whose straight line runs into a round pylon goes
     * round it by a detour point and arrives; before, the side steps slid him round the pylon until the walk failed */
    {vec3_t far_goal={60,0.5f,0};player.v.origin[0]=1000;
    memset(&actor,0,sizeof(actor));actor.v.origin[0]=-20;pylon=1;assert(AW_NavStartDirect(&actor,far_goal));
    for(i=0;i<1000;i++){result=AW_NavStep(.1,0);if(result)break;}
    assert(result==1 && fabs(actor.v.origin[0]-60)<6 && fabs(actor.v.origin[1]-.5f)<6);
    /* a clear line takes no detour: the walk keeps the straight line */
    memset(&actor,0,sizeof(actor));actor.v.origin[0]=-20;actor.v.origin[1]=40;far_goal[1]=40;highest_y=0;
    assert(AW_NavStartDirect(&actor,far_goal));for(i=0;i<1000;i++){result=AW_NavStep(.1,0);if(result)break;}
    assert(result==1 && highest_y<40.5f);pylon=0;}
    /* PIER-GUARD-POST-STUCK-67: a fixed route goes through its points in order and stops on the last one */
    {vec3_t points[3]={{20,0,0},{20,30,0},{-10,30,0}};
    memset(&actor,0,sizeof(actor));player.v.origin[0]=1000;highest_y=0;AW_NavFixedReset();
    assert(!AW_NavStartFixed(&actor,(const vec3_t *)points,0) && !AW_NavStartFixed(NULL,(const vec3_t *)points,3));
    assert(AW_NavStartFixed(&actor,(const vec3_t *)points,3));
    for(i=0;i<1000;i++){result=AW_NavStep(.1,0);if(result)break;
        assert(actor.v.origin[1]<.01f || fabs(actor.v.origin[0]-20)<1.01f || actor.v.origin[1]>29.9f);}   /* the corners kept */
    assert(result==1 && fabs(actor.v.origin[0]+10)<1 && fabs(actor.v.origin[1]-30)<1 && !moving._float && actor.v.frame==0);
    assert(AW_NavFixedSolid()==0 && AW_NavFixedWaits()==0);
    /* no detour and no side step round an obstacle on the line: the world blocks him, he stands, and after 5 s the walk
     * ends (-1) where he stood, on the line */
    memset(&actor,0,sizeof(actor));actor.v.origin[0]=-20;pylon=1;
    {vec3_t line[1]={{60,0,0}};assert(AW_NavStartFixed(&actor,(const vec3_t *)line,1));}
    for(i=0;i<1000;i++){result=AW_NavStep(.1,0);if(result)break;assert(fabs(actor.v.origin[1])<1e-4f);}
    assert(result==-1 && actor.v.origin[0]<PX-PR && fabs(actor.v.origin[1])<1e-4f && i>=55 && i<=70 && !moving._float);
    pylon=0;
    /* the player on the line: he waits there (counted once), never round; walks on when the way is clear */
    memset(&actor,0,sizeof(actor));
    {vec3_t line[1]={{40,0,0}};assert(AW_NavStartFixed(&actor,(const vec3_t *)line,1));}
    player_on_line=1;for(i=0;i<200;i++)assert(AW_NavStep(.1,0)==0);
    assert(actor.v.origin[0]==0 && AW_NavFixedWaits()==1 && !moving._float);
    player_on_line=0;for(i=0;i<100;i++){result=AW_NavStep(.1,0);if(result)break;}
    assert(result==1 && fabs(actor.v.origin[0]-40)<1 && AW_NavFixedWaits()==1);
    /* a box inside a solid is counted on every tick it stands there: the opening journey's check */
    memset(&actor,0,sizeof(actor));
    {vec3_t line[1]={{40,0,0}};assert(AW_NavStartFixed(&actor,(const vec3_t *)line,1));}
    inside=1;for(i=0;i<3;i++)AW_NavStep(.1,0);inside=0;
    assert(AW_NavFixedSolid()==3);AW_NavFixedReset();assert(AW_NavFixedSolid()==0 && AW_NavFixedWaits()==0);
    /* a box under the floor at the walk's start is lifted out before the first tick and counted apart: the route's own
     * count stays 0; when the stuck search finds no clear spot he stays and the first tick counts it, as before */
    memset(&actor,0,sizeof(actor));
    {vec3_t line[1]={{40,0,0}};start_inside=1;assert(AW_NavStartFixed(&actor,(const vec3_t *)line,1));}
    assert(AW_NavFixedSettled()==1 && fabs(actor.v.origin[2]-5.75f)<.01f && !start_inside);
    for(i=0;i<100;i++){result=AW_NavStep(.1,0);if(result)break;}
    assert(result==1 && fabs(actor.v.origin[0]-40)<1 && AW_NavFixedSolid()==0);
    memset(&actor,0,sizeof(actor));AW_NavFixedReset();assert(AW_NavFixedSettled()==0);settle_fails=1;
    {vec3_t line[1]={{40,0,0}};start_inside=1;assert(AW_NavStartFixed(&actor,(const vec3_t *)line,1));}
    assert(AW_NavFixedSettled()==0 && actor.v.origin[2]==0);AW_NavStep(.1,0);assert(AW_NavFixedSolid()==1);
    start_inside=settle_fails=0;AW_NavFixedReset();
    /* a grid walk started after a fixed one is the grid's again */
    assert(AW_NavDecode(grid,sizeof(grid)));memset(&actor,0,sizeof(actor));goal[0]=40;goal[1]=0;
    assert(AW_NavStart(&actor,goal));for(i=0;i<100;i++){result=AW_NavStep(.1,0);if(result)break;}
    assert(result==1 && actor.v.origin[0]>35);
    /* the stop ends a walk where the walker stands */
    memset(&actor,0,sizeof(actor));{vec3_t line[1]={{40,0,0}};assert(AW_NavStartFixed(&actor,(const vec3_t *)line,1));}
    assert(AW_NavStep(.1,0)==0 && actor.v.origin[0]>0 && actor.v.frame>=13);AW_NavStop();
    assert(actor.v.frame==0 && !moving._float && AW_NavStep(.1,0)==-1);}
    /* NPC-IDLE-TRACK-PLAYER-67: the slow turn: at most RATE degrees a second, the short way round, then facing it
     * (native yaw = world bearing - 90: a target on +X is yaw -90) */
    {vec3_t target={10,0,0};
    memset(&actor,0,sizeof(actor));
    assert(!AW_ActorTurnToward(&actor,target,90,.1) && fabs(actor.v.angles[1]+9)<.01f);
    for(i=0;i<8;i++)assert(!AW_ActorTurnToward(&actor,target,90,.1));
    assert(AW_ActorTurnToward(&actor,target,90,.1) && fabs(actor.v.angles[1]+90)<.01f);
    actor.v.angles[1]=170;target[0]=-10;   /* bearing 180, yaw 90: from 170 the short way down */
    assert(!AW_ActorTurnToward(&actor,target,90,.1) && fabs(actor.v.angles[1]-161)<.01f);}
    return 0;
}
