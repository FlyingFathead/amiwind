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
/* a carried light's catalogue byte 511 (aw_inventory.h AW_LIGHT_FLAGS_SET, AW_LIGHT_FLICKER) */
#define AW_HELD_FLAGS_SET 0x80
#define AW_HELD_FLICKER 1
static cvar_t torch_radius={"aw_torch_radius","192",true};
static cvar_t torch_flame_style={"aw_torch_flame_style","2",true};
cvar_t aw_torch_strength={"aw_torch_strength","0.7",true,false,.7f};
/* Guard torch light radius relative to the player's torch (dbg guardtorch 0.33):
 * the same brightness at the flame, the original's reach: the guards carry
 * torch_infinite_time, LHDT radius 256 original units = 64 map units at the
 * world scale 0.25, a third of the player torch's 192 (GUARD-TORCHES-57). It was
 * 0.5 (96 units, GUARD-TORCH-BRIGHT-31), 1.0 before that: a full torch's reach on
 * every guard read as over-bright in the light-space night. */
cvar_t aw_guard_torch_radius={"aw_guard_torch_radius",".33",true,false,.33f};   /* 63 units: never past the original */
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
    value=Q_strtod(text,&end);
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
/* Debug headlamp: the torch's eye light without holding a torch. Not saved. */
static cvar_t aw_headlamp={"aw_headlamp","0"};
static void headlamp_command(void) {
    char *text=Cmd_Argv(1);
    if(Cmd_Argc()==1){Con_Printf("Headlamp %s (torch light without a torch).\n",aw_headlamp.value?"on":"off");return;}
    if(Cmd_Argc()!=2 || (Q_strcasecmp(text,"on") && Q_strcasecmp(text,"off") && Q_strcasecmp(text,"true") &&
       Q_strcasecmp(text,"false") && strcmp(text,"1") && strcmp(text,"0"))){
        Con_Printf("Usage: dbg headlamp on/off, true/false or 1/0.\n");return;}
    Cvar_SetValue(aw_headlamp.name,!Q_strcasecmp(text,"on") || !Q_strcasecmp(text,"true") || !strcmp(text,"1"));
    Con_Printf("Headlamp %s.\n",aw_headlamp.value?"on":"off");
}
static void strength_command(void) {
    char *end,*text=Cmd_Argv(1);double value;
    if(Cmd_Argc()==1){Con_Printf("Torch strength %g (0..1, default 0.7; renderer-relative intensity).\n",aw_torch_strength.value);return;}
    value=Q_strtod(text,&end);
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
int (*aw_view_torch_emitter)(vec3_t out);
/* aw_debug_torch.c: 1 while a carried light from the inventory (the debug torch) is equipped. */
int (*aw_torch_item_lit)(void);
/* aw_debug_torch.c (DEBUG-TORCH-64): with no light equipped, equips the debug torch (given first while aw_debug_torch
 * is 1); 1 when a light is equipped now. */
int (*aw_torch_debug_equip)(void);
int (*aw_view_torch_light)(vec3_t out);
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
    AW_NpcPartsReset();      /* a new map: the residents' parts assembled again (their tables are the new map's) */
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
    /* TORCH-HAND-TO-HAND-64: punching (3) is hands up too: the torch stays lit while the fists strike */
    return v && (v->_float==1 || v->_float==2 || v->_float==3)?(int)v->_float:0;
}
static int held_own(void);
/* the carried light is lit (V or the equip) with the hands raised */
static int light_lit(void)
{
    edict_t *p=torch_player();eval_t *v;
    if(!p || hand_state(p)<2)return 0;
    v=GetEdictFieldValue(p,"aw_torch");
    /* TORCH-INVENTORY-PICTURE-64: the torch follows the equip state at once: with no light in the left hand nothing is
     * lit (before, the inventory's picture re-rendered on an unequip while the lit flag still waited for the next update,
     * and the old baked torch showed in the hand); the torch test room sets the flag itself */
    if(aw_torch_item_lit && !aw_torch_item_lit() && !AW_TorchTestActive())return 0;
    return v && v->_float==1;
}
/* the torch: lit, and the left hand holds no light of its own (HELD-LIGHT-OWN-MODEL-61) */
int AW_TorchEquipped(void)
{
    return torch_assets && light_lit() && !held_own();
}
static int held_lit(void){return light_lit() && held_own();}
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
    /* TORCH-HIDES-HELM-62: as in the original, only an equipped light is carried (OpenMW: a light in the carried-left
     * slot); V with no light equipped lights nothing, so the old baked torch body is no longer reached that way */
    /* DEBUG-TORCH-64: the debug torch (test only) is equipped by V as its grant message says; the original's rule holds
     * for every other case */
    if(v->_float!=1 && aw_torch_item_lit && !aw_torch_item_lit() && !(aw_torch_debug_equip && aw_torch_debug_equip())){
        Con_Printf("No light equipped: equip a torch or another light in the inventory (dbg torch gives one).\n");return;
    }
    v->_float=v->_float==1?0:1;
    if(!v->_float)extinguish();
    Con_Printf("Torch %s.\n",v->_float?"on":"off");
}
void AW_TorchInit(void){
    Cvar_RegisterVariable(&torch_radius);Cvar_RegisterVariable(&torch_flame_style);Cvar_RegisterVariable(&aw_torch_strength);Cvar_RegisterVariable(&aw_guard_torch_radius);
    Cmd_AddCommand("aw_torch_radius_set",radius_command);Cmd_AddCommand("aw_torch_flame_set",flame_command);
    Cmd_AddCommand("aw_torch_strength_set",strength_command);
    Cvar_RegisterVariable(&aw_headlamp);Cmd_AddCommand("aw_headlamp_set",headlamp_command);
    Cmd_AddCommand("aw_torch",toggle);AW_GuardTorchInit();AW_LampInit();
    aw_held_light_now=AW_HeldLight;     /* the flame drawer's view of the held light (HELD-LIGHT-OWN-MODEL-61) */
}
float AW_LightFlicker(unsigned seed)
{
    int n,k;
    if(torch_flame_style.value<2 || AW_FLICKER_STYLE>=MAX_LIGHTSTYLES)return 1;
    n=cl_lightstyle[AW_FLICKER_STYLE].length;
    if(n<=0 || !isfinite(cl.time) || cl.time<0)return 1;
    k=(int)((unsigned)(cl.time*10)%(unsigned)n);
    k=cl_lightstyle[AW_FLICKER_STYLE].map[(k+(int)(seed*7u%(unsigned)n))%n]-'a';   /* 'm' (12) = steady */
    if(k<0)k=0;
    if(k>12)k=12;
    return .8f+.2f*(float)k/12.f;
}
static int phase(void)
{
    return (int)floor(fmod(AW_TorchAnimationTime(),1.0)*8);
}
/* ---- HELD-LIGHT-OWN-MODEL-61: a held light that is not the torch (aw_torch.h) ---- */
/* A decimal "-12.3456" (held_lights.text's %.4f); no library float parsing (it pulls in FPU-emulated code). */
static int held_number(const char **pp,const char *end,float *out)
{
    const char *s=*pp;float v=0,scale=1;int neg=0,digits=0;
    while(s<end && *s==' ')s++;
    if(s<end && *s=='-'){neg=1;s++;}
    while(s<end && *s>='0' && *s<='9'){v=v*10+(float)(*s-'0');s++;digits++;}
    if(s<end && *s=='.'){s++;while(s<end && *s>='0' && *s<='9'){scale*=.1f;v+=(float)(*s-'0')*scale;s++;digits++;}}
    if(!digits || v>100000.f)return 0;
    *out=neg?-v:v;*pp=s;return 1;
}
static int held_line(const char **pp,const char *end,const char *word,float *values,int n)
{
    const char *p=*pp;int k,len=(int)strlen(word);
    if(end-p<len || memcmp(p,word,len))return 0;
    p+=len;
    for(k=0;k<n;k++)if(!held_number(&p,end,&values[k]) || !isfinite(values[k]))return 0;
    while(p<end && (*p==' ' || *p=='\r'))p++;
    if(p<end && *p!='\n')return 0;
    *pp=p<end?p+1:p;return 1;
}
int AW_HeldLightParse(const char *text,int size,const char *model,aw_held_light_t *out)
{
    const char *p=text,*end;int k;
    if(!text || !out || !model || size<6 || strlen(model)>=sizeof(out->model))return 0;
    end=text+size;memset(out,0,sizeof(*out));
    if(memcmp(p,"AWHL1",5) || (p[5]!='\n' && p[5]!='\r'))return 0;
    p+=5;while(p<end && (*p=='\r' || *p=='\n'))p++;
    if(!held_line(&p,end,"offset ",out->offset,6))return 0;
    for(k=0;k<3;k++)if(out->offset[k]< -64 || out->offset[k]>64)return 0;
    while(p<end && out->flames<AW_HELD_FLAMES+1){
        float *f;
        if(*p=='\n' || *p=='\r'){p++;continue;}
        if(out->flames==AW_HELD_FLAMES)return 0;
        f=out->flame[out->flames];
        if(!held_line(&p,end,"flame ",f,7))return 0;
        for(k=0;k<3;k++)if(f[k]< -128 || f[k]>128)return 0;
        if(!(f[3]>0 && f[3]<=16) || f[4]<0 || f[4]>=64 || f[5]<0 || f[5]>=128 || f[6]<0 || f[6]>=64)return 0;
        out->flames++;
    }
    strcpy(out->model,model);
    return 1;
}
float AW_HeldLightRadius(float torch_light,int item_radius,int torch_record)
{
    float r;
    if(!(torch_light>0) || !isfinite(torch_light))return 1;
    if(torch_record<=0 || item_radius<=0)return torch_light;
    r=torch_light*(float)item_radius/(float)torch_record;
    if(r>torch_light)r=torch_light;
    return r<1?1:r;
}
int (*aw_held_light_item)(char id[64],char model[64],int *radius,int *flags,int *torch_radius);
int (*aw_view_held_light)(vec3_t out);
int (*aw_hand_held_light)(float origin[3],float angles[3]);
static aw_held_light_t held;
static char held_id[64];
static int held_ok,held_radius,held_torch_radius;
/* The light in the left hand: its file read once when the item there changes (an equip, a load); 1 = it is a light
 * with its own held file (not the torch). */
static int held_own(void)
{
    char id[64],model[64];int radius=0,flags=0,torch_record=0;
    if(!aw_held_light_item || !aw_held_light_item(id,model,&radius,&flags,&torch_record)){held_id[0]=0;held_ok=0;return 0;}
    if(strcmp(id,held_id)){
        FILE *f=NULL;char path[64],text[1024];int size,n=(int)strlen(model);
        strncpy(held_id,id,63);held_id[63]=0;held_ok=0;
        if(n>4 && n<(int)sizeof(path) && !strcmp(model+n-4,".mdl")){
            memcpy(path,model,n-4);strcpy(path+n-4,".hld");
            size=COM_FOpenFile(path,&f);
            if(f){
                if(size>0 && size<(int)sizeof(text) && fread(text,1,size,f)==(size_t)size)
                    held_ok=AW_HeldLightParse(text,size,model,&held);
                fclose(f);
                if(!held_ok)Con_Printf("Held light %s: invalid %s; the torch is shown.\n",id,path);
            }
        }
        held.flicker=!(flags&AW_HELD_FLAGS_SET) || (flags&AW_HELD_FLICKER);
        held_radius=radius;held_torch_radius=torch_record;
        /* one line per new item in the hand (the in-game checks read it) */
        if(held_ok)Con_Printf("Held light %s: %s, %d flame%s, radius %d against the torch's %d: light %.0f (torch %.0f), %s.\n",
            id,model,held.flames,held.flames==1?"":"s",radius,torch_record,
            AW_HeldLightRadius(AW_TorchLightRadius(),radius,torch_record),AW_TorchLightRadius(),
            held.flicker?"flickering":"steady");
    }
    return held_ok;
}
const aw_held_light_t *AW_HeldLight(void)
{
    if(!held_lit())return NULL;
    held.radius=AW_HeldLightRadius(AW_TorchLightRadius(),held_radius,held_torch_radius);
    return &held;
}
/* Equipping the inventory light lights the carried torch and unequipping puts it out, as a
 * torch in the left hand; V still toggles it. The game rules put the torch out whenever the
 * hands are down (world.qc), so it is lit again when the hands come up. Only changes (equip,
 * hands, a new scene) write the field, so V keeps working while it is equipped. */
static void item_torch(void)
{
    static int was_lit,was_raised;static model_t *world;
    edict_t *p=torch_player();eval_t *v;int lit,raised;
    if(!aw_torch_item_lit || !p)return;
    lit=aw_torch_item_lit()!=0;raised=hand_state(p)!=0;
    if(lit==was_lit && raised==was_raised && world==sv.worldmodel)return;
    v=GetEdictFieldValue(p,"aw_torch");
    /* TORCH-HAND-TO-HAND-64: only equipping (with the hands up) lights it and only unequipping puts it out; raising the
     * hands no longer lights it again, so F raises the fists or the weapon and V alone switches the torch (before, every
     * change of the hands, a punch among them, lit it again: the fists showed for a moment, then the torch, and V could
     * not put it away) */
    if(v){if(lit && !was_lit && raised)v->_float=1;else if(!lit && was_lit)v->_float=0;}
    was_lit=lit;was_raised=raised;world=sv.worldmodel;
}
void AW_TorchUpdate(void)
{
    static const float radius[8]={144,147,142,146,143,148,144,141};
    dlight_t *light;
    int torch;const aw_held_light_t *own;
    AW_GuardTorchUpdate();
    AW_NpcPartsUpdate();     /* residents drawn from parts (aw_npc_parts.c) */
    AW_LampUpdate();
    item_torch();
    torch=AW_TorchEquipped();own=torch?NULL:AW_HeldLight();
    if(!torch && !own && !aw_headlamp.value){extinguish();return;}
    light=CL_AllocDlight(AW_TORCH_LIGHT);
    /* Eye position stays inside the player's clear view volume. Offsetting a
     * point light toward a drawn hand could put it through a nearby wall.
     * The headlamp alone is the same light without the flame's flicker. */
    VectorCopy(r_refdef.vieworg,light->origin);
    if(torch && aw_view_torch_light){vec3_t emitter;
        if(aw_view_torch_light(emitter))VectorCopy(emitter,light->origin);}
    if(own){
        /* a held candle, candlestick or lantern: its record's reach against the torch's, the torch's flicker only
         * where its record flickers (HELD-LIGHT-OWN-MODEL-61); in third person from its flame */
        vec3_t emitter;
        if(aw_view_held_light && aw_view_held_light(emitter))VectorCopy(emitter,light->origin);
        light->radius=own->radius*(own->flicker?radius[phase()]/144.f:1);
    }else light->radius=AW_TorchLightRadius()+(torch?radius[phase()]-144:0);
    light->minlight=16;
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
        if(yy<0 || yy>=(int)vid.height || yy<r_refdef.vrect.y ||
           yy>=r_refdef.vrect.y+r_refdef.vrect.height)continue;
        for(xx=x;xx<x+scale;xx++){
            if(xx<0 || xx>=(int)vid.width || xx<r_refdef.vrect.x ||
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
    float depth,cx,cy,size,age,drift,rise;double animation_time;
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
    /* Real embers (Quake particles, world space): white-hot to red, about
     * five per second, trailing as the player moves. Classic style: none. */
    if(torch_flame_style.value>=2 && (rand()&1023)<(int)(host_frametime*8*1024))
        AW_EmberSpawn(world,.8f,18);
    for(k=0;k<6;k++){
        age=(float)fmod(animation_time*.833333+k/6.0,1.0);if(age<0)age=0;
        drift=(float)Q_SinRad(k*2.4+animation_time*4)*.25f;rise=age*2.7f;
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
/* The first-person held light's flames (HELD-LIGHT-OWN-MODEL-61): each of its flame points carried through the place
 * its item model is drawn at this frame (aw_hand_models.c), drawn as the placed copy's flames are, over the view. */
void AW_HeldLightDraw(void)
{
    const aw_held_light_t *own;float origin[3],angles[3],shape[4];vec3_t forward,right,up,at;int i,j;
    if(!vid.buffer || !r_drawviewmodel.value || chase_active.value || r_fov_greater_than_90 ||
       (cl.items&IT_INVISIBILITY) || !(own=AW_HeldLight()) || !own->flames || !aw_hand_held_light ||
       !aw_hand_held_light(origin,angles))return;
    angles[PITCH]=-angles[PITCH];         /* alias angles: the renderer negates the pitch */
    AngleVectors(angles,forward,right,up);
    for(i=0;i<own->flames;i++){
        const float *f=own->flame[i];
        for(j=0;j<3;j++)at[j]=origin[j]+f[0]*forward[j]-f[1]*right[j]+f[2]*up[j];
        shape[0]=f[3];shape[1]=f[4];shape[2]=f[5];shape[3]=f[6];
        AW_HeldFlameDraw(at,shape,1);
    }
}
