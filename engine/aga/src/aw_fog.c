/* SPDX-License-Identifier: GPL-2.0-or-later
 * Palette fog applied to the rendered viewport using the inverse-depth buffer.
 * 4 KiB colour table baked on the host; 32 KiB depth table rebuilt on setting changes.
 */
#include "quakedef.h"
#include "aw_maps.h"
extern short *d_pzbuffer;
extern unsigned int d_zwidth;
extern cvar_t aw_drawdistance;
static cvar_t aw_fog={"aw_fog","1",true};
static byte *colours;
static byte depths[32768];
static int old_distance;
static cvar_t aw_cull;
int AW_DrawDistance(void) {
    /* This exterior's converted overlap is certified for the default range.
     * Keep the user's larger setting available to other scenes. */
    if(sv.active && (!strcmp(sv.name,"balmora") || !strcmp(sv.name,"seyda") || AW_TerrainId(sv.name)>=0) && aw_drawdistance.value>540)return 540;
    if(!(aw_drawdistance.value>=128))return 128;
    if(aw_drawdistance.value>4096)return 4096;
    return (int)aw_drawdistance.value;
}
void AW_SetDrawDistance(int value) {
    if(value<128)value=128;if(value>1400)value=1400;
    Cvar_SetValue("aw_drawdistance",value);
}
static void distance_command(void) {
    char *s;int value=0;
    if(Cmd_Argc()==1){Con_Printf("Fog/draw distance: %ld local units (default 540).\n",(long)AW_DrawDistance());return;}
    if(Cmd_Argc()!=2)goto invalid;
    s=Cmd_Argv(1);if(!*s)goto invalid;
    while(*s){if(*s<'0'||*s>'9')goto invalid;value=value*10+*s++-'0';if(value>1400)goto invalid;}
    if(value<128)goto invalid;
    AW_SetDrawDistance(value);
    Con_Printf("Fog/draw distance: %ld local units = %ld source units.\n",(long)value,(long)value*4);
    if(AW_Interior())Con_Printf("Exterior setting; indoor visibility is unchanged.\n");
    return;
invalid:
    Con_Printf("Usage: dbg fog distance 128..1400 (default 540)\n");
}
static void cycle_distance(void) {
    int value=aw_drawdistance.value<540?540:aw_drawdistance.value<1000?1000:450;
    AW_SetDrawDistance(value);
    Con_Printf("View distance: %ld (effective %ld).\n",(long)value,(long)AW_DrawDistance());
}
void AW_FogInit(void) { Cvar_RegisterVariable(&aw_fog);Cvar_RegisterVariable(&aw_cull);Cmd_AddCommand("aw_fog_distance",distance_command);Cmd_AddCommand("aw_viewdistance_cycle",cycle_distance);colours=COM_LoadHunkFile("gfx/fog.lmp"); }
/* Fill inverse-depth bands with 15 integer divisions, not 32767 floating-point
 * divisions on each live adjustment. Same 40%-to-100% linear fog profile. */
void AW_FogDepths(byte *table,int distance) {
    int level,first=1,last;
    if(distance<128)distance=128;if(distance>4096)distance=4096;
    memset(table,0,32768);table[0]=15;
    for(level=15;level>=1;level--){
        last=819200/(distance*(10+level));if(last>32767)last=32767;
        if(last>=first){memset(table+first,level,last-first+1);first=last+1;}
    }
}
void AW_FogDraw(void) {
    int distance,i,x,y,w,h;byte *pixels;short *z;
    if(!colours || !aw_fog.value || AW_Interior())return;
    distance=AW_DrawDistance();
    if(distance!=old_distance) {
        old_distance=distance;AW_FogDepths(depths,distance);
    }
    w=r_refdef.vrect.width;h=r_refdef.vrect.height;
    for(y=r_refdef.vrect.y;y<r_refdef.vrect.y+h;y++) {
        pixels=vid.buffer+y*vid.rowbytes+r_refdef.vrect.x;
        z=d_pzbuffer+y*d_zwidth+r_refdef.vrect.x;
        for(x=0;x<w;x++) {i=z[x];if(i<0)i=0;pixels[x]=colours[(depths[i]<<8)+pixels[x]];}
    }
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
