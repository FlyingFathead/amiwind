/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Actor light grid (NPC-LIGHT-COHERENCE-32) and the warm lightstyle
 * (OPENING-JIUB-LANTERN-32): the real r_light.c parser, trilinear sample,
 * fallbacks to the floor light, and style 31 shown like style 0. */
#include "quakedef.h"
#include "r_local.h"
#include "aw_sky.h"
#include <assert.h>
client_state_t cl;
lightstyle_t cl_lightstyle[MAX_LIGHTSTYLES];
dlight_t cl_dlights[MAX_DLIGHTS];
entity_t cl_entities[MAX_EDICTS], *currententity;
refdef_t r_refdef;
int r_framecount=10, d_lightstylevalue[256];
char com_token[1024];
static int exterior;
extern cvar_t aw_actor_light_grid;
int R_SkyExterior(void){return exterior;}
cvar_t aw_torch_strength={"aw_torch_strength","1",true,false,1};cvar_t aw_guard_torch_radius={"aw_guard_torch_radius","1",true,false,1};
void Con_Printf(char *format,...){}
void Con_DPrintf(char *format,...){}
void Sys_Error(char *format,...){fprintf(stderr,"Unexpected renderer error: %s\n",format);abort();}
static byte hunk[8192];static int hunk_used;
void *Hunk_AllocName(int size,char *name){void *p=hunk+hunk_used;(void)name;assert(hunk_used+size<=(int)sizeof hunk);memset(p,0,size);hunk_used+=(size+7)&~7;return p;}
/* Quake's COM_Parse (common.c) for quoted keys, values and braces. */
char *COM_Parse(char *data)
{
    int len=0,c;com_token[0]=0;if(!data)return NULL;
    while((c=*data)<=' '){if(!c)return NULL;data++;}
    if(c=='"'){data++;for(;;){c=*data++;if(c=='"'||!c){com_token[len]=0;return data;}com_token[len++]=c;}}
    if(c=='{'||c=='}'){com_token[0]=c;com_token[1]=0;return data+1;}
    do{com_token[len++]=c;data++;c=*data;}while(c>32 && c!='{' && c!='}');
    com_token[len]=0;return data;
}
static model_t world, actor;
static char entities[4096];
static void map(const char *text){strcpy(entities,text);world.entities=entities;cl.worldmodel=&world;R_LightGridNewMap();}
int main(void)
{
    entity_t e;int i;
    aw_actor_light_grid.value=1;   /* as registered (default 1) */
    /* 2 x 2 x 2 points, step 16 from (0,0,0): 0 at x=0, 160 at x=16, +40 at z=16 */
    map("{\n\"classname\" \"worldspawn\"\n\"_aw_lightgrid\" \"16 2 2 2 0 0 0\"\n"
        "\"_aw_lightgrid0\" \"00a000a028c828c8\"\n}\n{\n\"classname\" \"light\"\n}\n");
    memset(&e,0,sizeof e);e.model=&actor;actor.mins[2]=0;actor.maxs[2]=16;
    world.lightdata=NULL;exterior=0;     /* the floor light here would be 255 */
    assert(R_ActorLight(&e,0)==0);
    e.origin[0]=8;assert(R_ActorLight(&e,0)==80);
    e.origin[0]=16;assert(R_ActorLight(&e,0)==160);
    assert(R_ActorLight(&e,1)==180);     /* body centre 8 up: half of +40 */
    e.origin[0]=99;e.origin[1]=-5;e.origin[2]=99;assert(R_ActorLight(&e,0)==200);  /* clamped to the grid */
    r_refdef.ambientlight=190;assert(R_ActorLight(&e,0)==200);e.origin[0]=0;e.origin[2]=0;
    assert(R_ActorLight(&e,0)==190);r_refdef.ambientlight=0;
    aw_actor_light_grid.value=0;assert(R_ActorLight(&e,0)==255);aw_actor_light_grid.value=1;
    /* incomplete, malformed or absent grids fall back to the floor light */
    map("{\n\"_aw_lightgrid\" \"16 2 2 2 0 0 0\"\n\"_aw_lightgrid0\" \"00a000a0\"\n}\n");
    assert(R_ActorLight(&e,0)==255);
    map("{\n\"_aw_lightgrid\" \"16 2 2 2 0 0 0\"\n\"_aw_lightgrid0\" \"00a000a028c828zz\"\n}\n");
    assert(R_ActorLight(&e,0)==255);
    map("{\n\"_aw_lightgrid\" \"0 2 2 2 0 0 0\"\n\"_aw_lightgrid0\" \"00a000a028c828c8\"\n}\n");
    assert(R_ActorLight(&e,0)==255);
    map("{\n\"classname\" \"worldspawn\"\n}\n");assert(R_ActorLight(&e,0)==255);
    /* a second chunk key continues at point 480 */
    {
        static char big[4096];char *p=big;
        p+=sprintf(p,"{\n\"_aw_lightgrid\" \"16 482 1 1 0 0 0\"\n\"_aw_lightgrid0\" \"");
        for(i=0;i<480;i++)p+=sprintf(p,"%02x",i&255);
        p+=sprintf(p,"\"\n\"_aw_lightgrid1\" \"7f80\"\n}\n");
        map(big);e.origin[1]=e.origin[2]=0;
        e.origin[0]=16*479;assert(R_ActorLight(&e,0)==479-256);
        e.origin[0]=16*480;assert(R_ActorLight(&e,0)==0x7f);
        e.origin[0]=16*481;assert(R_ActorLight(&e,0)==0x80);
    }
    /* warm faces: style AW_WARM_STYLE follows style 0 unless set by the game */
    cl.time=0;cl_lightstyle[0].length=1;strcpy(cl_lightstyle[0].map,"m");R_AnimateLight();
    assert(d_lightstylevalue[0]==264 && d_lightstylevalue[AW_WARM_STYLE]==264);
    assert(AW_WARM_STYLE<AW_LAMP_STYLE);
    cl_lightstyle[AW_WARM_STYLE].length=1;strcpy(cl_lightstyle[AW_WARM_STYLE].map,"a");R_AnimateLight();
    assert(d_lightstylevalue[AW_WARM_STYLE]==0);
    puts("light grid: trilinear, centre, clamp, ambient floor, cvar, malformed fallbacks, chunks; warm style = style 0");
    return 0;
}
