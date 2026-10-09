/* SPDX-License-Identifier: GPL-2.0-or-later
 * Palette fog applied to the rendered viewport using the inverse-depth buffer.
 * 4 KiB colour table baked on the host; 32 KiB depth table rebuilt on setting changes.
 */
#include "quakedef.h"
#include "aw_maps.h"
#include "aw_town.h"
#include "aw_sky.h"
#include "aw_horizon.h"
extern short *d_pzbuffer;
extern unsigned int d_zwidth;
extern cvar_t aw_drawdistance;
static cvar_t aw_fog={"aw_fog","1",true};
/* Source candidate: retain classic rendering until target cost/visual acceptance. */
static cvar_t aw_terrain_horizon={"aw_terrain_horizon","0",true};
/* Skyline fill: in each column, sky below far scenery (fog level at least
 * SKYLINE_LEVEL) is a hole left by the far cut-off and takes the full fog
 * colour, so a short fog distance leaves a fogged skyline, not cut-outs.
 * Alternative horizon method ("object silhouetting"): experimental and buggy
 * (sprites need their shapes from the alpha channel); tested but subpar
 * results; kept for future improvement. The game config (config/game.cfg)
 * selects 0, the land-outline horizon (HORIZON-FLORA-SPRITES-32). */
static cvar_t aw_skyline_fill={"aw_skyline_fill","1",true};
/* Once per saved configuration, after config.cfg (quake.rc), as aw_gallery_migrate:
 * a save from before the land-outline default (v0.0.31, dev builds) still holds
 * aw_skyline_fill 1. Later explicit choices stay effective. */
static cvar_t aw_horizon_defaults={"aw_horizon_defaults","0",true};
static void horizon_migrate(void) {
    if(aw_horizon_defaults.value>=1)return;
    Cvar_SetValue("aw_skyline_fill",0);
    Cvar_SetValue("aw_horizon_defaults",1);
}
#define SKYLINE_LEVEL 12
#define SKYLINE_MAX 1600
static byte skyline[SKYLINE_MAX];
static byte *colours;
static byte depths[32768];
static int old_distance;
static cvar_t aw_cull;
/* Location fog (aw_fog_location.c) shortens the distance in listed places;
 * NULL until that module is initialised. */
int (*aw_fog_location_hook)(int);
/* CHIM (chim_world.c): on a CHIM map, the farthest its world's visibility
 * data reaches (the builder's draw distance + hysteresis); 0 or NULL on any
 * other map. */
int (*aw_chim_view_reach)(void);
/* CHIM (chim/chim_far.c): the frame's far terrain beyond the fog plane, in the
 * full fog colour, after the fog pass; NULL on legacy data. */
void (*aw_chim_far_draw)(byte colour,int distance);
/* Why the effective distance differs from the setting, for the command. */
static const char *limit_reason;
int AW_DrawDistance(void) {
    int d,reach=aw_chim_view_reach?aw_chim_view_reach():0,town=sv.active?AW_TownFind(sv.name):-1;
    int limit=reach>0?reach:town>=0?AW_Town(town)->draw_distance:540;
    /* A legacy exterior's converted overlap is certified for its town table
     * range (540 for every converted town and the open world): its region
     * maps hold their neighbours that far. A CHIM map has no such cap: the
     * chunk ring follows the view distance, and the only limit is how far
     * its world's visibility data reaches. Other scenes keep the user's
     * setting up to Quake's coordinate range. */
    limit_reason=NULL;
    if(sv.active && (reach>0 || town>=0 || AW_TerrainId(sv.name)>=0) && aw_drawdistance.value>limit){
        d=limit;
        limit_reason=reach>0?"this CHIM world's visibility data (the draw distance + hysteresis it was built with)":
            "this exterior's region maps (the town table's range)";
    }
    else if(!(aw_drawdistance.value>=100))d=100;
    else if(aw_drawdistance.value>4096){d=4096;limit_reason="Quake's coordinate range";}
    else d=(int)aw_drawdistance.value;
    return aw_fog_location_hook?aw_fog_location_hook(d):d;
}
void AW_SetDrawDistance(int value) {
    if(value<100)value=100;
    if(value>4096)value=4096;
    Cvar_SetValue("aw_drawdistance",value);
}
/* Said, never silent: what limits the distance here when it is not the
 * setting. */
static void distance_report(void) {
    int effective=AW_DrawDistance();
    if(effective!=(int)aw_drawdistance.value)
        Con_Printf("Here: %ld local units, limited by %s.\n",(long)effective,limit_reason?limit_reason:"location fog");
}
static void distance_command(void) {
    char *s;int value=0;
    if(Cmd_Argc()==1){Con_Printf("Fog/draw distance: %ld local units (default 540).\n",(long)aw_drawdistance.value);distance_report();return;}
    if(Cmd_Argc()!=2)goto invalid;
    s=Cmd_Argv(1);if(!*s)goto invalid;
    while(*s){if(*s<'0'||*s>'9')goto invalid;value=value*10+*s++-'0';if(value>4096)goto invalid;}
    if(value<100)goto invalid;
    AW_SetDrawDistance(value);
    Con_Printf("Fog/draw distance: %ld local units = %ld source units.\n",(long)value,(long)value*4);
    distance_report();
    if(AW_Interior())Con_Printf("Exterior setting; indoor visibility is unchanged.\n");
    return;
invalid:
    Con_Printf("Usage: dbg fog distance 100..4096 (default 540)\n");
}
static void cycle_distance(void) {
    int value=aw_drawdistance.value<540?540:aw_drawdistance.value<1000?1000:450;
    AW_SetDrawDistance(value);
    Con_Printf("View distance: %ld (effective %ld).\n",(long)value,(long)AW_DrawDistance());
}
void AW_FogInit(void) { Cvar_RegisterVariable(&aw_terrain_horizon);Cvar_RegisterVariable(&aw_skyline_fill);Cvar_RegisterVariable(&aw_horizon_defaults);Cmd_AddCommand("aw_horizon_migrate",horizon_migrate);Cmd_AddCommand("aw_horizon_stats",AW_HorizonReport);Cvar_RegisterVariable(&aw_fog);Cvar_RegisterVariable(&aw_cull);Cmd_AddCommand("aw_fog_distance",distance_command);Cmd_AddCommand("aw_viewdistance_cycle",cycle_distance);colours=COM_LoadHunkFile("gfx/fog.lmp"); }
/* Fill inverse-depth bands with 15 integer divisions, not 32767 floating-point
 * divisions on each live adjustment. Same 40%-to-100% linear fog profile. */
void AW_FogDepths(byte *table,int distance) {
    int level,first=1,last;
    if(distance<100)distance=100;
    if(distance>4096)distance=4096;
    memset(table,0,32768);table[0]=15;
    for(level=15;level>=1;level--){
        last=819200/(distance*(10+level));if(last>32767)last=32767;
        if(last>=first){memset(table+first,level,last-first+1);first=last+1;}
    }
}
void AW_FogDraw(void) {
    int distance,i,x,y,w,h,level,fog,fill;byte *pixels;short *z;
    const byte *environment,*ramp;
    float extent,u,v,step,ray[3],delta[3];int k;
    if(AW_Interior())return;
    environment=R_DayNightFogColours();ramp=environment?environment:colours;
    fog=colours && aw_fog.value;
    if(!fog && !environment)return;
    distance=AW_DrawDistance();
    if(fog && distance!=old_distance){old_distance=distance;AW_FogDepths(depths,distance);}
    w=r_refdef.vrect.width;h=r_refdef.vrect.height;extent=w>h?w:h;
    if(extent<=0)return;
    step=2.0f/extent;for(k=0;k<3;k++)delta[k]=vright[k]*step;
    fill=fog && aw_skyline_fill.value>0 && w<=SKYLINE_MAX;
    if(fill)memset(skyline,0,w);
    for(y=r_refdef.vrect.y;y<r_refdef.vrect.y+h;y++){
        pixels=vid.buffer+y*vid.rowbytes+r_refdef.vrect.x;
        z=d_pzbuffer+y*d_zwidth+r_refdef.vrect.x;
        u=(r_refdef.vrect.x-((int)vid.width>>1))*step;
        v=(((int)vid.height>>1)-y)*step;
        for(k=0;k<3;k++)ray[k]=vpn[k]+u*vright[k]+v*vup[k];
        for(x=0;x<w;x++){
            i=z[x];
            if(i==AW_SKY_BACKGROUND_DEPTH){
                if(fill && skyline[x])pixels[x]=ramp[(15<<8)+pixels[x]];
                else if(environment)pixels[x]=R_DayNightSkyPixel(pixels[x],ray[0],ray[1],ray[2],fog);
            }else if(fog){
                if(i<0)i=0;
                level=depths[i];pixels[x]=ramp[(level<<8)+pixels[x]];
                if(fill && level>=SKYLINE_LEVEL)skyline[x]=1;
            }
            for(k=0;k<3;k++)ray[k]+=delta[k];
        }
    }
    if(fog && aw_terrain_horizon.value==1)AW_HorizonDraw(ramp[15<<8],distance);
    if(fog && aw_chim_far_draw)aw_chim_far_draw(ramp[15<<8],distance);
}

/* Far clipping uses the same forward depth as palette fog. Radial/cubic
 * cutoffs removed visible edge-of-screen ground before it reached the fog. */
static cvar_t aw_cull={"aw_cull","1"};
static float far_normal[3],far_distance;
/* Brush polygons revisit the same world nodes many times in a frame.
 * Cache only the far-plane decision; PVS and brush sort keys remain untouched. */
typedef struct {short *bounds;unsigned frame;int visible;} aw_far_cache_t;
static aw_far_cache_t far_cache[2048];
static unsigned far_frame;
void AW_CullBegin(void) {
    float distance=AW_Interior()?4096:AW_DrawDistance();
    if(!++far_frame){memset(far_cache,0,sizeof(far_cache));far_frame=1;}
    VectorCopy(vpn,far_normal);
    far_distance=DotProduct(r_origin,far_normal)+distance+16;
}
int AW_NodeVisible(short *bounds) {
    float nearest=0;int i;aw_far_cache_t *cached;
    if(!aw_cull.value)return 1;
    cached=&far_cache[((size_t)bounds>>4)&2047];
    if(cached->bounds==bounds && cached->frame==far_frame)return cached->visible;
    for(i=0;i<3;i++)nearest+=far_normal[i]*bounds[i+(far_normal[i]<0?3:0)];
    cached->bounds=bounds;cached->frame=far_frame;
    return cached->visible=nearest<=far_distance;
}
int AW_ModelVisible(vec3_t origin,float radius) {
    return !aw_cull.value || DotProduct(origin,far_normal)-radius<=far_distance;
}
