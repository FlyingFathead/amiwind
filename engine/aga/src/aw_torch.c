/* SPDX-License-Identifier: GPL-2.0-or-later
 * Temporary carried torch: one bounded, monochrome software dynamic light and
 * owned source model, grip and emitter-aligned flame. No inventory or fuel.
 */
#include "quakedef.h"
#include "r_local.h"
#include <stdint.h>
#ifndef AMIWIND_SPRITE_HANDS
#define AMIWIND_SPRITE_HANDS 0
#endif
static byte *torch_assets;
static model_t *torch_model;
static unsigned int torch_duration;
static unsigned long read32(const byte *p){return ((unsigned long)p[0]<<24)|((unsigned long)p[1]<<16)|((unsigned long)p[2]<<8)|p[3];}
int AW_TorchAssetsValidate(const byte *p,int size)
{
    int i;unsigned long duration;int32_t value;
    if(!p || size!=716 || memcmp(p,"AWT1",4) || p[4] || p[5]!=8 || p[6] || p[7]!=16)return 0;
    duration=read32(p+8);if(duration<100 || duration>60000)return 0;
    for(i=0;i<48;i++){value=(int32_t)(uint32_t)read32(p+12+i*4);if(value< -8388608 || value>8388608)return 0;}
    return 1;
}
void AW_TorchLoadAssets(void)
{
    extern int com_filesize;
    int source_size;
    torch_assets=COM_LoadHunkFile("gfx/torch.awt");torch_model=NULL;torch_duration=0;source_size=com_filesize;
    AW_GuardTorchLoadAssets(AW_TorchAssetsValidate(torch_assets,source_size)?torch_assets:NULL);
    if(!AW_TorchAssetsValidate(torch_assets,source_size)){torch_assets=NULL;Con_Printf("Original torch assets unavailable; rebuild the image.\n");return;}
    torch_duration=(unsigned int)read32(torch_assets+8);
}
#define AW_TORCH_LIGHT (-0x415754)
extern cvar_t r_drawviewmodel, chase_active;
extern qboolean r_fov_greater_than_90;

static edict_t *torch_player(void)
{
    if(cls.state!=ca_connected || !sv.active || svs.maxclients!=1 ||
       !svs.clients || !svs.clients[0].edict || cl.intermission || AW_GalleryActive())return NULL;
    if(svs.clients[0].edict->v.health<=0)return NULL;
    return svs.clients[0].edict;
}
static int hand_state(edict_t *p)
{
    eval_t *v=GetEdictFieldValue(p,"aw_hand_goal");
    if(!v || v->_float!=1)return 0;
    v=GetEdictFieldValue(p,"aw_hand_state");
    return v && (v->_float==1 || v->_float==2)?(int)v->_float:0;
}
int AW_TorchEquipped(void)
{
    edict_t *p=torch_player();eval_t *v;
    if(!p || !torch_assets || hand_state(p)!=2)return 0;
    v=GetEdictFieldValue(p,"aw_torch");
    return v && v->_float==1;
}
static void extinguish(void)
{
    int i;
    for(i=0;i<MAX_DLIGHTS;i++)if(cl_dlights[i].key==AW_TORCH_LIGHT){
        cl_dlights[i].radius=0;cl_dlights[i].die=-1;
    }
}
static void toggle(void)
{
    edict_t *p=torch_player();eval_t *v;
    if(!p || sv.paused || cl.paused || AW_IntroImpulse(202)!=202 ||
       (key_dest!=key_game && key_dest!=key_console))return;
    if(!torch_assets){Con_Printf("Original torch assets unavailable; rebuild the image.\n");return;}
    if(!hand_state(p)){
        Con_Printf("Raise hands with F before equipping the torch.\n");return;
    }
    v=GetEdictFieldValue(p,"aw_torch");
    if(!v){Con_Printf("Torch requires matching AmiWind game rules.\n");return;}
    v->_float=v->_float==1?0:1;
    if(!v->_float)extinguish();
    Con_Printf("Torch %s.\n",v->_float?"on":"off");
}
void AW_TorchInit(void){Cmd_AddCommand("aw_torch",toggle);AW_GuardTorchInit();}
static int phase(void)
{
    if(!isfinite(cl.time) || cl.time<0)return 0;
    return (int)floor(fmod(cl.time,1.0)*8);
}
void AW_TorchUpdate(void)
{
    static const float radius[8]={144,147,142,146,143,148,144,141};
    dlight_t *light;
    AW_GuardTorchUpdate();
    if(!AW_TorchEquipped()){extinguish();return;}
    light=CL_AllocDlight(AW_TORCH_LIGHT);
    /* Eye position stays inside the player's clear view volume. Offsetting a
     * point light toward a drawn hand could put it through a nearby wall. */
    VectorCopy(r_refdef.vieworg,light->origin);
    light->radius=radius[phase()];light->minlight=16;
    light->die=cl.time+.1;light->decay=0;
}
int AW_TorchFrame(void)
{
    double cycle;
    if(!torch_duration || !isfinite(cl.time) || cl.time<0)return 0;
    cycle=torch_duration*.001;
    return (int)(fmod(cl.time,cycle)*8/cycle)%8;
}
void AW_TorchViewModel(void)
{
    if(!AW_TorchEquipped() || !torch_assets)return;
#if !AMIWIND_SPRITE_HANDS
    if(!torch_model)torch_model=Mod_ForName("progs/v_torch.mdl",false);
    if(!torch_model || torch_model->type!=mod_alias)return;
    cl.viewent.model=torch_model;
#endif
    cl.viewent.frame=AW_TorchFrame();
}
static void pixel(int x,int y,int scale,byte color)
{
    int xx,yy;
    for(yy=y;yy<y+scale;yy++){
        if(yy<0 || yy>=vid.height || yy<r_refdef.vrect.y ||
           yy>=r_refdef.vrect.y+r_refdef.vrect.height)continue;
        for(xx=x;xx<x+scale;xx++){
            if(xx<0 || xx>=vid.width || xx<r_refdef.vrect.x ||
               xx>=r_refdef.vrect.x+r_refdef.vrect.width)continue;
            vid.buffer[yy*vid.rowbytes+xx]=color;
        }
    }
}
/* Project the authored emitter with the SAME pose/camera as the viewmodel.
 * Six small textured billboards approximate additive fire with ordered alpha.
 * The shaft is exclusively source geometry; no independent screen-space grip. */
void AW_TorchDraw(void)
{
    static const int threshold[16]={0,8,2,10,12,4,14,6,3,11,1,9,15,7,13,5};
    vec3_t anchor,forward,right,up,angles,world,delta;
    float depth,cx,cy,scale,size,age,drift,rise;
    int frame,i,j,k,x,y,xx,yy,n,alpha;const byte *tex,*p;
    if(!AW_TorchEquipped() || !torch_assets || !vid.buffer || !r_drawviewmodel.value ||
       chase_active.value || r_fov_greater_than_90 || (cl.items&IT_INVISIBILITY))return;
    frame=AW_TorchFrame();p=torch_assets+12+frame*24;
    for(i=0;i<3;i++)anchor[i]=(int32_t)(uint32_t)read32(p+i*4)/65536.0f;
    tex=torch_assets+204;
    VectorCopy(cl.viewent.angles,angles);angles[PITCH]=-angles[PITCH];
    AngleVectors(angles,forward,right,up);
    for(i=0;i<3;i++)world[i]=cl.viewent.origin[i]+anchor[0]*forward[i]-anchor[1]*right[i]+anchor[2]*up[i];
    for(k=0;k<6;k++){
        age=(float)fmod(cl.time*.833333+k/6.0,1.0);if(age<0)age=0;
        drift=(float)sin(k*2.4+cl.time*4)*.25f;rise=age*2.7f;
#if AMIWIND_SPRITE_HANDS
        if(anchor[0]<=.5f)continue;
        scale=r_refdef.vrect.width>=320?2:1;
        cx=r_refdef.vrect.x+(r_refdef.vrect.width-160*scale)/2+scale*(80-(anchor[1]+drift)/anchor[0]*80);
        cy=r_refdef.vrect.y+r_refdef.vrect.height-100*scale+scale*(50-(anchor[2]+rise)/anchor[0]*80);
        size=80*scale/anchor[0]*1.5f*(1-age*.3f);
#else
        for(i=0;i<3;i++)delta[i]=world[i]-r_refdef.vieworg[i]+right[i]*drift;
        delta[2]+=rise;depth=DotProduct(delta,vpn);if(depth<1)continue;
        cx=aliasxcenter+DotProduct(delta,vright)*aliasxscale/depth;
        cy=aliasycenter-DotProduct(delta,vup)*aliasyscale/depth;
        size=aliasyscale/depth*1.5f*(1-age*.3f);
#endif
        if(!isfinite(cx) || !isfinite(cy) || !isfinite(size) || size<1)continue;
        if(cx<r_refdef.vrect.x-64 || cx>r_refdef.vrect.x+r_refdef.vrect.width+64 ||
           cy<r_refdef.vrect.y-64 || cy>r_refdef.vrect.y+r_refdef.vrect.height+64)continue;
        n=(int)size;if(n>32)n=32;if(n<2)n=2;x=(int)cx-n/2;y=(int)cy-n/2;
        for(yy=0;yy<n;yy++)for(xx=0;xx<n;xx++){
            j=((yy*16/n)*16+xx*16/n)*2;alpha=(int)(tex[j+1]*(1-age*.6f));
            if(alpha>threshold[((y+yy)&3)*4+((x+xx)&3)]*16+7)pixel(x+xx,y+yy,1,tex[j]);
        }
    }
}
