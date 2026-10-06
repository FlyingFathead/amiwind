/* SPDX-License-Identifier: GPL-2.0-or-later
 * Temporary carried torch: one bounded, monochrome software dynamic light and
 * owned source model, grip and emitter-aligned flame. No inventory or fuel.
 */
#include "quakedef.h"
#include "r_local.h"
#include "aw_torch.h"
#include <stdint.h>
#ifndef AMIWIND_SPRITE_HANDS
#define AMIWIND_SPRITE_HANDS 0
#endif
static cvar_t torch_radius={"aw_torch_radius","192",true};
static cvar_t torch_flame_style={"aw_torch_flame_style","2",true};
cvar_t aw_torch_strength={"aw_torch_strength","0.7",true,false,.7f};
float AW_TorchLightRadius(void) {
    float radius=torch_radius.value;
    if(!isfinite(radius))return 192;
    if(radius<32)return 32;
    if(radius>288)return 288;
    return radius;
}
int AW_TorchFlameCoreColor(void) {
    return torch_flame_style.value==2 || torch_flame_style.value==3?AW_UIColor(255,244,214):-1;
}
/* Only recolour the opaque lower centre of young flame particles. Preserve
 * the owned texture, transparency, warm tips, geometry and legacy style. */
byte AW_TorchFlameColor(byte original,int texel,float age,int core) {
    int x=(texel/2)%16,y=texel/32;
    return core>=0 && age>=0 && age<.25f && x>=5 && x<=10 && y>=8?(byte)core:original;
}
static void radius_command(void) {
    char *end,*text=Cmd_Argv(1);double value;
    if(Cmd_Argc()==1){Con_Printf("Torch light radius %g (32..288; classic 144, default 192).\n",AW_TorchLightRadius());return;}
    value=strtod(text,&end);
    if(Cmd_Argc()!=2 || end==text || *end || !isfinite(value) || value<32 || value>288){
        Con_Printf("Usage: dbg torch radius 32..288 (player and admitted guard lights).\n");return;}
    Cvar_SetValue(torch_radius.name,(float)value);
    Con_Printf("Torch light radius %g; flame size and light count unchanged.\n",AW_TorchLightRadius());
}
static void flame_command(void) {
    char *text=Cmd_Argv(1);int value;
    if(Cmd_Argc()==1){Con_Printf("Torch flame style %ld (1 classic, 2 brightbase, 3 sparks).\n",(long)(torch_flame_style.value==3?3:torch_flame_style.value==2?2:1));return;}
    if(!Q_strcasecmp(text,"classic") || !strcmp(text,"1"))value=1;
    else if(!Q_strcasecmp(text,"brightbase") || !strcmp(text,"2"))value=2;
    else if(!Q_strcasecmp(text,"sparks") || !strcmp(text,"3"))value=3;
    else value=0;
    if(Cmd_Argc()!=2 || !value){Con_Printf("Usage: dbg torch flame classic/brightbase/sparks or 1/2/3.\n");return;}
    Cvar_SetValue(torch_flame_style.name,value);
    Con_Printf("Torch flame style %ld (%s).\n",(long)value,value==3?"sparks":value==2?"brightbase":"classic");
}
static void strength_command(void) {
    char *end,*text=Cmd_Argv(1);double value;
    if(Cmd_Argc()==1){Con_Printf("Torch strength %g (0..1, default 0.7; renderer-relative intensity).\n",aw_torch_strength.value);return;}
    value=strtod(text,&end);
    if(Cmd_Argc()!=2 || end==text || *end || !isfinite(value) || value<0 || value>1){
        Con_Printf("Usage: dbg torch strength 0..1 (player and admitted guard lights).\n");return;}
    Cvar_SetValue(aw_torch_strength.name,(float)value);
    Con_Printf("Torch strength %g; radius and light count unchanged.\n",aw_torch_strength.value);
}
static byte *torch_assets,*hand_torch_assets;
static int use_hand_torch_assets;
static model_t *torch_model;
static unsigned int torch_duration;
static double torch_animation_offset;
double AW_TorchAnimationTime(void)
{
    double now=cl.time+torch_animation_offset;
    return isfinite(now) && now>=0?now:0;
}
void AW_TorchRestoreAnimation(double time)
{
    torch_model=NULL; /* Model table slots can be reused by a new map. */
    torch_animation_offset=isfinite(time) && time>=0 && isfinite(cl.time)?time-cl.time:0;
}
void AW_TorchResetAnimation(void){torch_animation_offset=0;torch_model=NULL;}

static unsigned long read32(const byte *p){return ((unsigned long)p[0]<<24)|((unsigned long)p[1]<<16)|((unsigned long)p[2]<<8)|p[3];}
int AW_TorchAssetsValidate(const byte *p,int size)
{
    int i;unsigned long duration;int32_t value;
    if(!p || size!=716 || memcmp(p,"AWT1",4) || p[4] || p[5]!=8 || p[6] || p[7]!=16)return 0;
    duration=read32(p+8);if(duration<100 || duration>60000)return 0;
    for(i=0;i<48;i++){value=(int32_t)(uint32_t)read32(p+12+i*4);if(value< -8388608 || value>8388608)return 0;}
    return 1;
}
void AW_TorchUseHandAssets(int enabled)
{
    use_hand_torch_assets=enabled && hand_torch_assets;
}
int AW_TorchLoadHandAssets(void)
{
    extern int com_filesize;
    AW_TorchUseHandAssets(0);
    hand_torch_assets=COM_LoadHunkFile("gfx/hand-torch.awt");
    if(!AW_TorchAssetsValidate(hand_torch_assets,com_filesize))hand_torch_assets=NULL;
    return hand_torch_assets!=NULL;
}
void AW_TorchLoadAssets(void)
{
    extern int com_filesize;
    int source_size;
    use_hand_torch_assets=0;hand_torch_assets=NULL;
    torch_assets=COM_LoadHunkFile("gfx/torch.awt");torch_model=NULL;torch_duration=0;source_size=com_filesize;
    AW_GuardTorchLoadAssets(AW_TorchAssetsValidate(torch_assets,source_size)?torch_assets:NULL);
    if(!AW_TorchAssetsValidate(torch_assets,source_size)){torch_assets=NULL;Con_Printf("Original torch assets unavailable; rebuild the image.\n");return;}
    torch_duration=(unsigned int)read32(torch_assets+8);
}
#define AW_TORCH_LIGHT AW_TORCH_LIGHT_KEY
extern cvar_t r_drawviewmodel, chase_active;
extern qboolean r_fov_greater_than_90;

static edict_t *torch_player(void)
{
    if(cls.state!=ca_connected || !sv.active || svs.maxclients!=1 ||
       !svs.clients || !svs.clients[0].edict || cl.intermission || (AW_GalleryActive() && !AW_TorchTestActive()))return NULL;
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
void AW_TorchInit(void){
    Cvar_RegisterVariable(&torch_radius);Cvar_RegisterVariable(&torch_flame_style);Cvar_RegisterVariable(&aw_torch_strength);
    Cmd_AddCommand("aw_torch_radius_set",radius_command);Cmd_AddCommand("aw_torch_flame_set",flame_command);
    Cmd_AddCommand("aw_torch_strength_set",strength_command);
    Cmd_AddCommand("aw_torch",toggle);AW_GuardTorchInit();
}
static int phase(void)
{
    return (int)floor(fmod(AW_TorchAnimationTime(),1.0)*8);
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
    light->radius=AW_TorchLightRadius()+radius[phase()]-144;light->minlight=16;
    light->die=cl.time+.1;light->decay=0;
}
int AW_TorchFrame(void)
{
    double cycle;
    unsigned int duration=use_hand_torch_assets?(unsigned int)read32(hand_torch_assets+8):torch_duration;
    if(!duration)return 0;
    cycle=duration*.001;
    return (int)(fmod(AW_TorchAnimationTime(),cycle)*8/cycle)%8;
}
/* Only the superseded local-view payload is retired. Model metadata remains
 * valid for fallback/reload; never free the model currently being drawn. */
void AW_TorchReleaseLegacyCache(void)
{
    if(torch_model && torch_model!=cl.viewent.model &&
       torch_model->type==mod_alias &&
       !strcmp(torch_model->name,"progs/v_torch.mdl") && torch_model->cache.data)
        Cache_Free(&torch_model->cache);
}
void AW_TorchViewModel(void)
{
    AW_TorchUseHandAssets(0); /* Establish the legacy model/metadata pair first. */
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
/* Quake-style bounded point particles: lifetime, rising motion and a colour
 * ramp, mapped through the active palette rather than Quake palette indices.
 * These are near-field first-person embers, sharing the flame's authored
 * emitter and overlay clipping. No global RNG, allocations or extra lights.
 * Four phase slots keep cost bounded even after a long pause or a cell load. */
static void draw_sparks(const vec3_t emitter,double animation_time)
{
    static const float side[4]={-.7f,.45f,-.3f,.8f};
    vec3_t delta;
    float age,depth,cx,cy;int k,j,colour;
    if(torch_flame_style.value!=3 || !isfinite(animation_time))return;
    for(k=0;k<4;k++){
        age=(float)fmod(animation_time*.8+k*.37,1.0);
        if(age<0 || age>=.48f)continue;
        for(j=0;j<3;j++)delta[j]=emitter[j]-r_refdef.vieworg[j]+vright[j]*side[k]*age*3;
        delta[2]+=1.5f+age*10;
        depth=DotProduct(delta,vpn);if(!(depth>1))continue;
        cx=aliasxcenter+DotProduct(delta,vright)*aliasxscale/depth;
        cy=aliasycenter-DotProduct(delta,vup)*aliasyscale/depth;
        if(!isfinite(cx) || !isfinite(cy) || cx<r_refdef.vrect.x || cy<r_refdef.vrect.y ||
           cx>=r_refdef.vrect.x+r_refdef.vrect.width || cy>=r_refdef.vrect.y+r_refdef.vrect.height)continue;
        colour=age<.10f?AW_UIColor(255,255,232):age<.30f?AW_UIColor(255,232,112):AW_UIColor(248,154,48);
        pixel((int)cx,(int)cy,1,(byte)colour);
    }
}
/* Project the authored emitter with the SAME pose/camera as the viewmodel.
 * Six small textured billboards approximate additive fire with ordered alpha.
 * The shaft is exclusively source geometry; no independent screen-space grip. */
void AW_TorchDraw(void)
{
    static const int threshold[16]={0,8,2,10,12,4,14,6,3,11,1,9,15,7,13,5};
    vec3_t anchor,forward,right,up,angles,world,delta;
    float depth,cx,cy,scale,size,age,drift,rise;double animation_time;
    int frame,i,j,k,x,y,xx,yy,n,alpha,core;const byte *tex,*p,*assets;
    if(!AW_TorchEquipped() || !torch_assets || !vid.buffer || !r_drawviewmodel.value ||
       chase_active.value || r_fov_greater_than_90 || (cl.items&IT_INVISIBILITY))return;
    assets=use_hand_torch_assets?hand_torch_assets:torch_assets;
    core=AW_TorchFlameCoreColor();frame=AW_TorchFrame();p=assets+12+frame*24;
    for(i=0;i<3;i++)anchor[i]=(int32_t)(uint32_t)read32(p+i*4)/65536.0f;
    tex=assets+204;
    VectorCopy(cl.viewent.angles,angles);angles[PITCH]=-angles[PITCH];
    AngleVectors(angles,forward,right,up);
    for(i=0;i<3;i++)world[i]=cl.viewent.origin[i]+anchor[0]*forward[i]-anchor[1]*right[i]+anchor[2]*up[i];
    animation_time=AW_TorchAnimationTime();
    for(k=0;k<6;k++){
        age=(float)fmod(animation_time*.833333+k/6.0,1.0);if(age<0)age=0;
        drift=(float)sin(k*2.4+animation_time*4)*.25f;rise=age*2.7f;
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
            if(alpha>threshold[((y+yy)&3)*4+((x+xx)&3)]*16+7)pixel(x+xx,y+yy,1,AW_TorchFlameColor(tex[j],j,age,core));
        }
    }
#if !AMIWIND_SPRITE_HANDS
    draw_sparks(world,animation_time);
#endif
}
