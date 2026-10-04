/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
#include <setjmp.h>
extern void Mod_LoadSpriteModel(model_t *,void *);
extern void CL_ParseStatic(qboolean);
client_state_t cl;
entity_t cl_entities[MAX_EDICTS],cl_static_entities[MAX_STATIC_ENTITIES];
viddef_t vid;
sizebuf_t net_message;
int msg_readcount,r_pixbytes=1,aw_efrags_used,aw_efrags_peak;
qboolean msg_badread;
unsigned short d_8to16table[256];
static jmp_buf failure;
static int expect_error;
static int identity_long(int n){return n;}
static float identity_float(float n){return n;}
int (*LittleLong)(int)=identity_long;
float (*LittleFloat)(float)=identity_float;
void *Hunk_AllocName(int n,char *name){assert(n>0);return calloc(1,n);}
void Q_memset(void *p,int n,int sz){memset(p,n,sz);}
void Q_memcpy(void *p,void *q,int sz){memcpy(p,q,sz);}
void Sys_Error(char *fmt,...){assert(expect_error);longjmp(failure,1);}
void Host_Error(char *fmt,...){assert(expect_error);longjmp(failure,1);}
void Con_Printf(char *fmt,...){assert(0 && "unexpected efrag exhaustion");}
int MSG_ReadByte(void){if(msg_readcount>=net_message.cursize){msg_badread=true;return -1;}return net_message.data[msg_readcount++];}
float MSG_ReadCoord(void){int a=MSG_ReadByte(),b=MSG_ReadByte();return (short)(a|(b<<8))/8.0f;}
float MSG_ReadAngle(void){return MSG_ReadByte()*360.0f/256;}
float MSG_ReadFloat(void){float f;assert(msg_readcount+4<=net_message.cursize);memcpy(&f,net_message.data+msg_readcount,4);msg_readcount+=4;return f;}
static void free_efrags(efrag_t *pool,int n){int i;memset(pool,0,n*sizeof(*pool));for(i=0;i<n-1;i++)pool[i].entnext=&pool[i+1];cl.free_efrags=pool;}
static void parse_scale(model_t *sprite,float scale,qboolean custom,int bytes){
    static byte msg[32];static efrag_t pool[8];static mleaf_t leaf;static model_t world;
    memset(msg,0,sizeof(msg));msg[0]=1;
    if(custom){float x=6000;memcpy(msg+4,&x,4);memcpy(msg+28,&scale,4);}
    memset(&cl,0,sizeof(cl));memset(&leaf,0,sizeof(leaf));leaf.contents=CONTENTS_EMPTY;
    world.nodes=(mnode_t *)&leaf;cl.worldmodel=&world;cl.model_precache[1]=sprite;
    free_efrags(pool,8);net_message.data=msg;net_message.cursize=bytes;msg_readcount=0;msg_badread=false;
    CL_ParseStatic(custom);
    assert(cl.num_statics==1);assert(cl_static_entities[0].origin[0]==(custom?6000:0));assert(cl_static_entities[0].aw_sprite_scale==(custom?scale:1));
    assert(leaf.efrags && leaf.efrags->entity==&cl_static_entities[0]);
}
int main(void){
    byte raw[36+4+16+600]={0};dsprite_t *header=(dsprite_t *)raw;
    dspriteframe_t *frame=(dspriteframe_t *)(raw+40);
    model_t sprite={0},world={0};entity_t ent={0};mnode_t node={0};mleaf_t left={0},right={0};mplane_t plane={0};efrag_t pool[8];
    header->version=SPRITE_VERSION;header->type=SPR_VP_PARALLEL;header->width=20;header->height=30;header->numframes=1;
    frame->origin[0]=-10;frame->origin[1]=90;frame->width=20;frame->height=30;
    Mod_LoadSpriteModel(&sprite,raw);
    assert(fabs(sprite.radius-sqrt(8200.0))<0.01);assert(sprite.maxs[2]>=90);
    ent.model=&sprite;assert(R_SpriteEntityScale(&ent)==1);ent.aw_sprite_scale=.5f;assert(R_SpriteEntityScale(&ent)==.5f);
    /* At x=60, half-size occupies only the positive leaf; double-size spans both. */
    plane.type=0;plane.normal[0]=1;node.plane=&plane;node.children[0]=(mnode_t *)&right;node.children[1]=(mnode_t *)&left;
    left.contents=right.contents=CONTENTS_EMPTY;world.nodes=&node;cl.worldmodel=&world;ent.origin[0]=60;
    free_efrags(pool,8);R_AddEfrags(&ent);assert(right.efrags && !left.efrags);
    ent.efrag=NULL;right.efrags=NULL;ent.aw_sprite_scale=2;free_efrags(pool,8);R_AddEfrags(&ent);assert(right.efrags && left.efrags);
    parse_scale(&sprite,.25f,true,32);parse_scale(&sprite,3.5f,true,32);parse_scale(&sprite,0,false,13);
    expect_error=1;
    if(!setjmp(failure)){parse_scale(&sprite,2,true,31);assert(0);}
    if(!setjmp(failure)){parse_scale(&sprite,0,true,32);assert(0);}
    if(!setjmp(failure)){parse_scale(&sprite,-2,true,32);assert(0);}
    if(!setjmp(failure)){parse_scale(&sprite,NAN,true,32);assert(0);}
    if(!setjmp(failure)){parse_scale(&sprite,INFINITY,true,32);assert(0);}
    if(!setjmp(failure)){parse_scale(&sprite,1,true,3);assert(0);}
    sprite.type=mod_alias;
    if(!setjmp(failure)){parse_scale(&sprite,1,true,32);assert(0);}
    return 0;
}
