/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
server_static_t svs;
static int obstruct,no_backward,player_blocks;static float wall=1000;static eval_t moving,walkstep;
static float identity(float f){return f;}
float (*LittleFloat)(float)=identity;
void Con_Printf(char *s,...){}
eval_t *GetEdictFieldValue(edict_t *e,char *s){return !strcmp(s,"aw_moving")?&moving:&walkstep;}
qboolean AW_ActorStep(edict_t *e,vec3_t delta,double dt){if(obstruct || (no_backward && delta[0]<0) || e->v.origin[0]+delta[0]>wall)return false;VectorAdd(e->v.origin,delta,e->v.origin);return true;}
trace_t SV_Move(vec3_t a,vec3_t mi,vec3_t ma,vec3_t b,int type,edict_t *e){trace_t t;memset(&t,0,sizeof(t));t.fraction=obstruct || player_blocks?0:1;if(player_blocks)t.ent=svs.clients[0].edict;return t;}
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
    actor.v.origin[0]=8;no_backward=1;assert(AW_NavStart(&actor,goal));
    for(i=0;i<100;i++){result=AW_NavStep(.1,0);if(result)break;}
    assert(result==1 && actor.v.origin[0]>35);no_backward=0;
    actor.v.origin[0]=0;obstruct=1;assert(AW_NavStart(&actor,goal));for(i=0;i<100;i++){result=AW_NavStep(.1,0);if(result)break;}
    assert(result==-1 && actor.v.origin[0]==0 && !moving._float);
    obstruct=0;actor.v.origin[0]=0;player_blocks=1;assert(AW_NavStart(&actor,goal));
    for(i=0;i<200;i++)assert(AW_NavStep(.1,1)==0);
    assert(actor.v.origin[0]==0 && !moving._float);player_blocks=0;
    for(i=0;i<100;i++){result=AW_NavStep(.1,0);if(result)break;}assert(result==1);
    actor.v.origin[0]=0;
    player.v.origin[0]=300;assert(AW_NavStart(&actor,goal));assert(AW_NavStep(.1,1)==0 && actor.v.origin[0]==0);
    assert(AW_NavDecode(grid,sizeof(grid)));goal[0]=0;actor.v.origin[0]=40;assert(!AW_NavStart(&actor,goal));
    return 0;
}
