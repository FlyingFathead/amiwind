/*
Copyright (C) 1996-1997 Id Software, Inc.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

*/
// r_sky.c

#include "quakedef.h"
#include "r_local.h"
#include "d_local.h"
#include "aw_sky.h"
#include "aw_state.h"
#include "aw_clock.h"


int		iskyspeed = 8;
int		iskyspeed2 = 2;
float	skyspeed, skyspeed2;

float		skytime;

byte		*r_skysource;
float r_sky_texture_scale=378;

int r_skymade;
int r_backgroundsky;
int r_skydirect;		// not used?


// TODO: clean up these routines

byte	bottomsky[128*131];
byte	bottommask[128*131];
byte	newsky[128*256];	// newsky and topsky both pack in here, 128 bytes
							//  of newsky on the left of each scan, 128 bytes
							//  of topsky on the right, because the low-level
							//  drawers need 256-byte scan widths


/* Explicit worldspawn metadata owns scene selection; pixels own no map memory. */
static int sky_initialized,sky_shared,sky_exterior;
static cvar_t sky_starsky={"aw_starsky","1",true},sky_nightsky={"aw_nightsky","1",true};
static cvar_t sky_daynight={"aw_daynight","1",true};
static cvar_t sky_type={"aw_sky_type","3",true};
static cvar_t sky_cloud_speed={"aw_skyspeed","0.00333333333",true};
static cvar_t sky_sun_enabled={"aw_sun","1",true},sky_clouds={"aw_clouds","1",true};
static cvar_t sky_cloud_type={"aw_cloud_type","1",true};
static cvar_t sky_night_clouds={"aw_night_clouds","0",true};
static cvar_t sky_cloud_control={"aw_cloud_control","1",true};
static cvar_t sky_day_clouds={"aw_day_clouds","100",true};
static cvar_t sky_nightsky_mode={"aw_nightsky_mode","1",true};
static int sky_frame_type=3,sky_table_type=-1,sky_made_type=-1,sky_made_clouds=-1,sky_made_cloud_type=-1,sky_made_night=-1,sky_made_cloud_density=-1;
static int sky_night_cloud_density=16,sky_made_coverage_roles=-1;
/* V2/V3 use indexed cloud roles/luminance. The world-direction remap and
 * two small ramps use 8192 static bytes, plus 256 bytes for cloud roles. */
static byte sky_gradient[16*256],sky_glow[8*256],sun_halo[8*256];
/* Palette-bank signature and disjoint source layers are the version marker.
 * Legacy assets retain their old indexed interpretation. No inferred alpha. */
static byte sky_cloud_role[256];
/* Night-only roles preserve the legacy day/twilight validator and scale. */
static byte sky_night_cloud_role[256];
static int sky_cloud_roles,sky_night_cloud_roles,sky_night_roles_active,sky_coverage_roles_active,sky_bank_ready;
static const byte sky_bank_indices[7]={222,133,95,156,140,83,221};
static const byte sky_bank_rgb[7][3]={{100,69,138},{52,73,110},{210,50,34},
    {250,104,45},{255,174,66},{255,232,160},{153,38,79}};
static int R_SkyPaletteBank(void)
{
    int i;
    if(!host_basepal)return 0;
    for(i=0;i<7;i++)if(memcmp(host_basepal+3*sky_bank_indices[i],sky_bank_rgb[i],3))return 0;
    return 1;
}
/* Match the offline pixel remap for procedural legacy particle colors only.
 * RGB-selected UI ink and converted texture pixels already use the new bank. */
unsigned char R_SkyLegacyColour(unsigned char index)
{
    if(!sky_bank_ready)return index;
    switch(index){
    case 222:case 221:return 223;case 133:return 113;case 95:return 94;
    case 156:return 158;case 140:return 138;case 83:return 82;
    default:return index;
    }
}
static void R_SkyCloudRoles(const byte *src)
{
    int x,y,i,layer,cloud=0,base=0;byte c;
    sky_cloud_roles=0;memset(sky_cloud_role,0,sizeof sky_cloud_role);
    if(!host_basepal)return;
    for(y=0;y<128;y++)for(x=0;x<128;x++)for(layer=0;layer<2;layer++){
        c=src[y*256+x+layer*128];
        if(!c){if(layer)return;continue;}
        if(c==224){if(!layer)return;base=1;continue;}
        if(c>=225)return; /* preserved UI bank and transparent sprite index */
        for(i=0;i<7;i++)if(c==sky_bank_indices[i])return;
        if(layer){if(c!=2 && c!=4 && c!=5)return;sky_cloud_role[c]=2;}
        else{if(c==2 || c==4 || c==5)return;sky_cloud_role[c]=1;}
        cloud=1;
    }
    sky_cloud_roles=cloud && base;
}
/* Separate validator for the deep-night coverage controllers. The owned
 * shared sky uses 254 as an opaque left-layer cloud color; legacy daytime
 * validation intentionally continues to reject it, preserving its fallback.
 * This map only gates night overlays and deep-night veil removal. */
static void R_SkyNightCloudRoles(const byte *src)
{
    int x,y,layer,cloud=0,base=0;byte c;
    sky_night_cloud_roles=0;memset(sky_night_cloud_role,0,sizeof sky_night_cloud_role);
    if(!host_basepal || !src)return;
    for(y=0;y<128;y++)for(x=0;x<128;x++)for(layer=0;layer<2;layer++){
        c=src[y*256+x+layer*128];
        if(!c){if(layer)return;continue;}
        if(c==224){if(!layer)return;base=1;continue;}
        if(c==255 || (c>=225 && c!=254))return;
        if(c==254 && layer)return;
        if(c==222 || c==133 || c==95 || c==156 || c==140 || c==83 || c==221)return;
        if(layer){if(c!=2 && c!=4 && c!=5)return;sky_night_cloud_role[c]=2;}
        else{if(c==2 || c==4 || c==5)return;sky_night_cloud_role[c]=1;}
        cloud=1;
    }
    sky_night_cloud_roles=cloud && base;
}

static float sky_sun[3];
static int sky_sun_visible,sky_sun_ms=-1,sky_sun_colour=-1,sky_glow_strength,sky_warm_side;
static int R_SkyType(void){return sky_type.value==1?1:sky_type.value==2?2:3;}
static int R_SkyCloudType(void);
static int R_SkyDayCloudPercent(void);
static int R_SkyCloudControl(void){return sky_cloud_control.value==2?2:1;}
static int R_SkyNightCloudTarget(int days)
{
    float mode=sky_night_clouds.value;int day;
    if(mode==1)return 0;
    if(mode==2)return 8;
    if(mode==3)return 16;
    if(days<0 || days>365000)return 16; /* Invalid/unavailable date fails closed to overcast. */
    day=days%8;
    switch(day){
    case 0:case 1:case 3:case 4:return 0;
    case 2:case 5:case 7:return 8;
    default:return 16;
    }
}
static int R_SkyStoredDay(void)
{
    int i;
    for(i=0;i<aw_state.count[AW_GLOBAL];i++)
        if(!strcmp(aw_state.values[AW_GLOBAL][i].id,"amiwind:clock:days"))
            return aw_state.values[AW_GLOBAL][i].value;
    return -1;
}
static int R_SkyBaselineCloudDensity(int milliseconds,int days,int active)
{
    int daytime=R_SkyCloudType()==2?4:16,target,factor=0,minute,policy_day,dayfactor,daytarget;
    if(R_SkyCloudControl()!=2)return daytime;
    if(!active || milliseconds<0 || milliseconds>=86400000)return daytime;
    minute=milliseconds/60000;
    if(minute>=540 && minute<600)dayfactor=minute-540;
    else if(minute>=600 && minute<=840)dayfactor=60;
    else if(minute>840 && minute<900)dayfactor=900-minute;
    else dayfactor=0;
    if(dayfactor){
        daytarget=(daytime*R_SkyDayCloudPercent()+50)/100;
        return (daytime*(60-dayfactor)+daytarget*dayfactor+30)/60;
    }
    if(minute>=1320 && minute<1335)factor=minute-1320;
    else if(minute>=1335 || minute<225)factor=15;
    else if(minute>=225 && minute<240)factor=240-minute;
    else return daytime; /* Preserve the complete 04:00..22:00 day/twilight coverage. */
    policy_day=days;
    if(minute<240 && days>0)policy_day=days-1; /* Keep one weather choice across midnight. */
    target=R_SkyNightCloudTarget(policy_day);
    return (daytime*(15-factor)+target*factor+7)/15;
}
/* The midnight clearing window is an AmiWind presentation policy, independent
 * of the legacy/V2 selectors. Invalid direct writes use the shipped default. */
static int R_SkyNightMode(void){return sky_nightsky_mode.value==0?0:1;}
static int R_SkyNightClearFactor(int milliseconds,int active)
{
    int minute;
    if(!R_SkyNightMode() || !active || milliseconds<0 || milliseconds>=86400000)return 0;
    minute=milliseconds/60000;
    if(minute>=1380)return minute-1380;
    if(minute<=180)return 60;
    if(minute<240)return 240-minute;
    return 0;
}
static int R_SkyClockCloudDensity(int milliseconds,int days,int active)
{
    int baseline=R_SkyBaselineCloudDensity(milliseconds,days,active);
    int factor=R_SkyNightClearFactor(milliseconds,active);
    return (baseline*(60-factor)+30)/60;
}
static void R_SkyNightModeCommand(void)
{
    char *s=Cmd_Argv(1);
    if(Cmd_Argc()==2){
        if(!strcmp(s,"legacy") || !strcmp(s,"0"))Cvar_SetValue(sky_nightsky_mode.name,0);
        else if(!strcmp(s,"clear") || !strcmp(s,"1"))Cvar_SetValue(sky_nightsky_mode.name,1);
        else{Con_Printf("Usage: dbg nightskymode legacy/clear or 0/1\n");return;}
    }else if(Cmd_Argc()!=1){Con_Printf("Usage: dbg nightskymode legacy/clear or 0/1\n");return;}
    Con_Printf("Night sky mode: %s\n",R_SkyNightMode()?"midnight clear; fade 23:00..00:00, clear until 03:00, return by 04:00":"retained cloud coverage policy");
}
static void R_SkyNightCloudCommand(void)
{
    char *s=Cmd_Argv(1);
    if(Cmd_Argc()==2){
        if(!strcmp(s,"auto"))Cvar_SetValue(sky_night_clouds.name,0);
        else if(!strcmp(s,"clear"))Cvar_SetValue(sky_night_clouds.name,1);
        else if(!strcmp(s,"partial"))Cvar_SetValue(sky_night_clouds.name,2);
        else if(!strcmp(s,"overcast"))Cvar_SetValue(sky_night_clouds.name,3);
        else{Con_Printf("Usage: dbg nightclouds auto/clear/partial/overcast\n");return;}
    }else if(Cmd_Argc()!=1){Con_Printf("Usage: dbg nightclouds auto/clear/partial/overcast\n");return;}
    Con_Printf("Night clouds: %s (%s)\n",sky_night_clouds.value==1?"clear":sky_night_clouds.value==2?"partial":sky_night_clouds.value==3?"overcast":"auto",R_SkyCloudControl()==2?"active":"inactive under legacy cloud control");
}
static int R_SkyDayCloudPercent(void)
{
    float value=sky_day_clouds.value;
    return value>=0 && value<=100 && value==(int)value?(int)value:100;
}
static void R_SkyDayCloudCommand(void)
{
    char *s=Cmd_Argv(1),*end;long value;
    if(Cmd_Argc()==2){
        value=strtol(s,&end,10);
        if(end==s || *end || value<0 || value>100){Con_Printf("Usage: dbg dayclouds 0..100 (core 10:00..14:00; dawn/sunset protected)\n");return;}
        Cvar_SetValue(sky_day_clouds.name,(float)value);
    }else if(Cmd_Argc()!=1){Con_Printf("Usage: dbg dayclouds 0..100 (core 10:00..14:00; dawn/sunset protected)\n");return;}
    Con_Printf("Day cloud coverage: %ld%% (%s; 10:00..14:00 core, 09:00..10:00/14:00..15:00 fade; dawn/sunset protected)\n",(long)R_SkyDayCloudPercent(),R_SkyCloudControl()==2?"active":"inactive under legacy cloud control");
}
static void R_SkyCloudControlCommand(void)
{
    char *s=Cmd_Argv(1);
    if(Cmd_Argc()==2){
        if(!strcmp(s,"legacy") || !strcmp(s,"1")){Cvar_SetValue(sky_cloud_control.name,1);Cvar_SetValue(sky_nightsky_mode.name,0);}
        else if(!strcmp(s,"new") || !strcmp(s,"2"))Cvar_SetValue(sky_cloud_control.name,2);
        else{Con_Printf("Usage: dbg cloudcontrol legacy/new or 1/2\n");return;}
    }else if(Cmd_Argc()!=1){Con_Printf("Usage: dbg cloudcontrol legacy/new or 1/2\n");return;}
    Con_Printf("Cloud control V%ld: %s\n",(long)R_SkyCloudControl(),R_SkyCloudControl()==1?"legacy V0.0.28 base; night/day selectors inactive":"new prototype; night/day selectors active");
    Con_Printf("Midnight clearing: %s (dbg nightskymode legacy/clear)\n",R_SkyNightMode()?"on":"off");
}
static void R_SkyCloudTypeCommand(void)
{
    char *s=Cmd_Argv(1);
    if(Cmd_Argc()==2){
        if(!strcmp(s,"classic") || !strcmp(s,"1"))Cvar_SetValue(sky_cloud_type.name,1);
        else if(!strcmp(s,"veil") || !strcmp(s,"2"))Cvar_SetValue(sky_cloud_type.name,2);
        else{Con_Printf("Usage: dbg cloudtype classic/veil or 1/2\n");return;}
    }else if(Cmd_Argc()!=1){Con_Printf("Usage: dbg cloudtype classic/veil or 1/2\n");return;}
    Con_Printf("Cloud type: %s\n",R_SkyCloudType()==2?"veil":"classic");
}
static void R_SkyTypeCommand(void)
{
    char *s=Cmd_Argv(1);
    if(Cmd_Argc()==2){
        if(*s=='v' || *s=='V')s++;
        if((s[0]!='1' && s[0]!='2' && s[0]!='3') || s[1]){Con_Printf("Usage: dbg skytype 1/2/3 or V1/V2/V3\n");return;}
        Cvar_SetValue(sky_type.name,s[0]-'0');
    }else if(Cmd_Argc()!=1){Con_Printf("Usage: dbg skytype 1/2/3 or V1/V2/V3\n");return;}
    Con_Printf("Sky V%ld: %s\n",(long)R_SkyType(),R_SkyType()==1?"Clear reference":R_SkyType()==3?"extra stronk twilight":"red/gold twilight and blue hour");
}
/* Invalid direct cvar writes cannot feed NaN/overflow into the sky sampler. */
static double R_SkyCloudSpeed(void)
{
    return sky_cloud_speed.value>=0 && sky_cloud_speed.value<=100?
        (double)sky_cloud_speed.value:0.00333333333;
}
static int R_SkyCloudType(void){return sky_cloud_type.value==2?2:1;}
static int R_SkyVeilKeep(int x,int y,int density)
{
    static const byte ordered[16]={0,8,2,10,12,4,14,6,3,11,1,9,15,7,13,5};
    return ordered[((y&3)<<2)|(x&3)]<density;
}
/* The source sky has no alpha channel. A bounded ordered mask drops opaque
 * cloud samples so the original sky beneath shows at the selected density. */
static byte R_SkyVeilComposite(byte base,int ofs,int x,int y,int density)
{
    int bx=(x+((int)(skytime*skyspeed)))&SKYMASK;
    int by=(y+((int)(skytime*skyspeed)))&SKYMASK;
    if((sky_coverage_roles_active && sky_night_cloud_roles?sky_night_cloud_role[base]:
        (sky_cloud_roles?sky_cloud_role[base]:0))==2 &&
       !R_SkyVeilKeep(bx+2,by+1,density))base=224;
    if(bottommask[ofs]==0 && !R_SkyVeilKeep(bx,by,density))return base;
    return (byte)((base&bottommask[ofs])|bottomsky[ofs]);
}
static void R_SkySpeedCommand(void)
{
    char *text,*end;double value;
    if(Cmd_Argc()==2){
        text=Cmd_Argv(1);value=Q_strtod(text,&end);
        if(end==text || *end || !(value>=0 && value<=100))goto invalid;
        Cvar_SetValue(sky_cloud_speed.name,(float)value);
    }else if(Cmd_Argc()!=1)goto invalid;
    Con_Printf("Cloud speed: %g (0=frozen, 0.00333333333=default, 1=old speed)\n",R_SkyCloudSpeed());
    return;
invalid:
    Con_Printf("Usage: dbg skyspeed 0..100 (default 0.00333333333)\n");
}
/* A 4-bit/channel RGB lookup is built once. The current 256-byte sky remap
 * and 4096-byte fog ramp supplement the V2 tables above. Phase changes use bounded integer
 * lookup work; no texture-space dither or per-frame palette search. */
static byte sky_rgb[4096],sky_tint[256],sky_fog[4096];
static int sky_tints_ready,sky_phase=-1,sky_phase_last=-2,sky_table_phase=-2;
/* Light-space night (BALMORA-LAMPS-DIM-31, DLIGHT-WALLS-31): 1 (default) moves
 * the night's brightness into the light (r_daylight) and keeps only its hue, at
 * aw_night_tint percent strength, so torches, lamps and glows keep their light;
 * 0 restores the whole-frame remap, which darkened their light too. */
static cvar_t sky_night_light={"aw_night_light","1",true};
static cvar_t sky_night_tint={"aw_night_tint","100",true};
/* Horizon veil (HORIZON-HOLES-31): the lowest sky bands fade into the far fog
 * colour, so gaps in fully fogged distant silhouettes read as haze. 0 = off,
 * 1..15 = veil height in sky bands (one table lookup per veiled sky pixel). */
static cvar_t sky_horizon_veil={"aw_horizon_veil","0",true};
/* Light hue (aw_light_hue "R G B"): the colour torch, lamp and window light
 * leans toward. R_BuildWarmLight makes the per-surface warm table from it:
 * dark rows copied from the game's own colormap, brighter rows tinted and
 * matched through the palette grid; 16,384 lookups, only when the hue changes. */
static cvar_t sky_light_hue={"aw_light_hue","255 210 140",true};
static byte warm_table[64*256];
static char warm_built[32];
static void R_LightHueCommand(void);
static int sky_table_daylight=256,sky_table_night=-1,sky_table_tint=-1;
static byte sky_shade[256];
/* Clear-weather RGB stops from the reference configuration. Timing below is a
 * compact approximation; clouds retain their existing texture luminance and
 * ordinary daytime preserves the original indexed sky. No weather simulation. */
static const byte sky_rgb_stops[4][3]={{95,135,203},{117,141,164},{56,89,129},{9,10,11}};
static const byte fog_rgb_stops[4][3]={{206,227,255},{255,189,157},{255,189,157},{9,10,11}};
static int R_SkySpread(int r,int g,int b)
{
    int high=r>g?r:g,low=r<g?r:g;
    if(b>high)high=b;
    if(b<low)low=b;
    return high-low;
}
/* Nearest palette entry through the 16x16x16 grid. Near black the 17-step grid
 * can round one channel up and the others down, turning a near-grey into rust
 * (NIGHT-RUST-31: (9,8,8) -> grid (17,0,0) -> palette (23,7,3)). A dark colour
 * whose grid answer is clearly more saturated is searched exactly instead; on
 * the shipped palette that is 6 of 256 colours at deep night, once per table
 * build, never per pixel. */
byte R_SkyNearest(int r,int g,int b);
byte R_SkyNearest(int r,int g,int b)
{
    const byte *p;int i,best,distance,best_distance,dr,dg,db;byte grid;
    if(r>255)r=255;
    if(g>255)g=255;
    if(b>255)b=255;
    grid=sky_rgb[(((r+8)/17)<<8)|(((g+8)/17)<<4)|((b+8)/17)];
    if(!host_basepal || r>=64 || g>=64 || b>=64)return grid;
    p=host_basepal+3*grid;
    if(R_SkySpread(p[0],p[1],p[2])<=R_SkySpread(r,g,b)+12)return grid;
    best=grid;best_distance=0x7fffffff;
    for(i=0;i<256;i++){
        dr=r-host_basepal[3*i];dg=g-host_basepal[3*i+1];db=b-host_basepal[3*i+2];
        distance=dr*dr+dg*dg+db*db;
        if(distance<best_distance){best=i;best_distance=distance;}
    }
    return (byte)best;
}
/* Shared reduced owned bitmaps: 25,600 pixels + 2,048 star-role mask bytes
 * and 4,096 fade-table bytes.
 * No map hunk, geometry, frame-sized buffer or per-frame allocation. */
static byte sky_night_pixels[AW_NIGHT_SKY_PAYLOAD],sky_night_fade[16*256],sky_night_blue[256];
static int sky_night_loaded,sky_night_attempted,sky_night_strength,sky_moon_phase[2],sky_night_step,sky_night_points;
static float sky_moon[2][3],sky_moon_right[2][3],sky_moon_up[2][3];
static unsigned int R_NightHash(const byte *bytes,int length)
{
    unsigned int hash=2166136261U;int i;
    for(i=0;i<length;i++)hash=(hash^bytes[i])*16777619U;
    return hash;
}
static unsigned int R_NightWord(const byte *p)
{
    return (unsigned int)p[0]|((unsigned int)p[1]<<8)|((unsigned int)p[2]<<16)|((unsigned int)p[3]<<24);
}
static void R_LoadNightSky(void)
{
    FILE *file=NULL;byte header[16];int size,payload;
    if(sky_night_attempted)return;
    sky_night_attempted=1;
    size=COM_FOpenFile(AW_NIGHT_SKY_PATH,&file);
    if(!file)return; /* Optional owned input; cloud sky remains functional. */
    if(!host_basepal || fread(header,1,16,file)!=16){fclose(file);return;}
    sky_night_points=!memcmp(header,"AWN2\200\200\030\010",8);
    payload=sky_night_points?AW_NIGHT_SKY_PAYLOAD:AW_NIGHT_SKY_ART_BYTES;
    if(size!=16+payload || (!sky_night_points && memcmp(header,"AWN1\200\200\030\010",8)) ||
       R_NightWord(header+8)!=R_NightHash(host_basepal,768) ||
       fread(sky_night_pixels,1,payload,file)!=(size_t)payload ||
       R_NightWord(header+12)!=R_NightHash(sky_night_pixels,payload)){
        fclose(file);Con_Printf("Night sky unavailable: invalid atlas/palette contract.\n");return;
    }
    fclose(file);sky_night_loaded=1;
    Con_Printf("Owned night sky: %ld bitmap bytes, stars/nebula + Masser/Secunda, no map hunk.\n",(long)payload);
}
static void R_NightTables(void)
{
    int i,k,level,rgb[3],base=sky_frame_type>=2?sky_gradient[15*256+224]:sky_tint[224];
    if(!sky_night_loaded)return;
    for(i=0;i<256;i++)sky_night_blue[i]=R_SkyNearest(host_basepal[3*i]*3/4,host_basepal[3*i+1]*7/8,host_basepal[3*i+2]);
    for(level=0;level<16;level++)for(i=0;i<256;i++){
        for(k=0;k<3;k++)rgb[k]=(host_basepal[3*i+k]*level+host_basepal[3*base+k]*(15-level))/15;
        sky_night_fade[level*256+i]=level==15?i:R_SkyNearest(rgb[0],rgb[1],rgb[2]);
    }
}
int R_NightMoonOrbit(int moon,int milliseconds,int days,float direction[3],int *phase)
{
    int orbit_day;double hour,rise,travel,angle,axis;
    direction[0]=direction[1]=0;direction[2]=-1;if(phase)*phase=0;
    if(moon<0 || moon>1 || milliseconds<0 || milliseconds>=86400000)return 0;
    if(days<0)days=0;
    hour=milliseconds/3600000.0;
    rise=fmod(17.0+(days%24)*(moon?1.2:1.0)+(moon?3.4:0),24.0);
    orbit_day=days;
    if(hour<rise){
        orbit_day=days-1;
        rise=fmod(17.0+(orbit_day%24)*(moon?1.2:1.0)+(moon?3.4:0)+24.0,24.0);
        travel=hour+24.0-rise;
    }else travel=hour-rise;
    if(phase)*phase=(orbit_day<0?0:orbit_day%24)/3;
    angle=travel*(M_PI/(moon?20.0:23.0));axis=(moon?50.0:35.0)*(M_PI/180.0);
    if(angle>=M_PI)return 0;
    direction[0]=(float)Q_CosRad(angle);
    direction[1]=(float)(-Q_SinRad(angle)*Q_SinRad(axis));
    direction[2]=(float)(Q_SinRad(angle)*Q_CosRad(axis));
    return direction[2]>0;
}
static void R_NightFrame(int milliseconds,int days)
{
    int a=sky_phase>>10,b=(sky_phase>>6)&15,mix=sky_phase&63,m,k;
    double hour=milliseconds/3600000.0,horizontal;
    int midnight=R_SkyNightClearFactor(milliseconds,1)>0;
    sky_night_cloud_density=R_SkyClockCloudDensity(milliseconds,days,1);
    /* The independent midnight mode validates opaque 254 as well. Outside
     * its window, preserve the existing V1/V2 role policy byte for byte. */
    sky_night_roles_active=midnight || (R_SkyCloudControl()==2 &&
        (milliseconds>=22*3600000 || milliseconds<4*3600000));
    sky_coverage_roles_active=(midnight || (R_SkyCloudControl()==2 &&
        ((milliseconds>=9*3600000 && milliseconds<15*3600000) ||
         milliseconds>=22*3600000 || milliseconds<4*3600000))) &&
        sky_night_cloud_density<(R_SkyCloudType()==2?4:16);
    sky_night_strength=sky_night_loaded && sky_nightsky.value>0?((a==3?32-mix:0)+(b==3?mix:0))*15/32:0;
    if(hour>=5 && hour<20.5)sky_night_strength=0;
    if(!sky_night_strength)return;
    /* Original eight phases on a 24-day cycle, starting full. The orbit is
     * deliberately reduced: source relative sizes and 35/50 degree axes,
     * bounded daily rise drift; no weather-dependent early-shadow model. */
    sky_night_step=(milliseconds/30000)&15;
    for(m=0;m<2;m++){
        if(!R_NightMoonOrbit(m,milliseconds,days,sky_moon[m],&sky_moon_phase[m]))continue;
        horizontal=sqrt((double)sky_moon[m][0]*sky_moon[m][0]+(double)sky_moon[m][1]*sky_moon[m][1]);
        sky_moon_right[m][0]=(float)(-sky_moon[m][1]/horizontal);
        sky_moon_right[m][1]=(float)(sky_moon[m][0]/horizontal);sky_moon_right[m][2]=0;
        for(k=0;k<2;k++)sky_moon_up[m][k]=(float)(-sky_moon[m][k]*sky_moon[m][2]/horizontal);
        sky_moon_up[m][2]=(float)horizontal;
    }
}
const float *R_DayNightMoonDirection(int moon)
{
    return moon>=0 && moon<2 && R_DayNightFogColours() && sky_night_strength && sky_moon[moon][2]>0?sky_moon[moon]:NULL;
}
/* One native pixel at a fixed source-cell direction, using the same camera
 * projection as AW_FogDraw. No screen-space random overlay or star-list scan.
 * Only marked source texels enter this bounded projection test. */
static int R_NightStarPoint(int ix,int iy,float x,float y,float z)
{
    float star[3],extent,forward,rayforward,sx,sy,rx,ry;
    int px,py;
    extent=r_refdef.vrect.width>r_refdef.vrect.height?r_refdef.vrect.width:r_refdef.vrect.height;
    if(extent<=0)return 1; /* Direction-only lookup outside an active viewport. */
    star[0]=(ix-63)/63.0f;star[1]=(63-iy)/63.0f;
    star[2]=1-fabs(star[0])-fabs(star[1]);
    if(star[2]<=0)return 0;
    forward=DotProduct(star,vpn);rayforward=x*vpn[0]+y*vpn[1]+z*vpn[2];
    if(forward<=0 || rayforward<=0)return 0;
    extent*=.5f;
    sx=((int)vid.width>>1)+DotProduct(star,vright)*extent/forward;
    sy=((int)vid.height>>1)-DotProduct(star,vup)*extent/forward;
    rx=((int)vid.width>>1)+(x*vright[0]+y*vright[1]+z*vright[2])*extent/rayforward;
    ry=((int)vid.height>>1)-(x*vup[0]+y*vup[1]+z*vup[2])*extent/rayforward;
    if(!isfinite(sx) || !isfinite(sy) || sx<r_refdef.vrect.x-.5f || sy<r_refdef.vrect.y-.5f ||
       sx>=r_refdef.vrect.x+r_refdef.vrect.width-.5f || sy>=r_refdef.vrect.y+r_refdef.vrect.height-.5f)return 0;
    if(!isfinite(rx) || !isfinite(ry) || rx<r_refdef.vrect.x-.5f || ry<r_refdef.vrect.y-.5f ||
       rx>=r_refdef.vrect.x+r_refdef.vrect.width-.5f || ry>=r_refdef.vrect.y+r_refdef.vrect.height-.5f)return 0;
    px=(int)floor(sx+.5f);py=(int)floor(sy+.5f);
    return px==(int)floor(rx+.5f) && py==(int)floor(ry+.5f);
}
static byte R_NightPixel(byte base,byte source,float x,float y,float z)
{
    float length,dot,u,v,radius;int ix,iy,m,level,twinkle,starlevel,point;byte pixel,back=base;
    if(!sky_night_strength || z<=0)return base;
    /* Validated cloud-role indices are opaque. Sky samples never cross the
     * terrain/sprite semantic depth boundary, even with geometry fog disabled. */
    if(sky_clouds.value>0){
        if(sky_night_roles_active){
            if(!sky_night_cloud_roles || sky_night_cloud_role[source])return base;
        }else if(!sky_cloud_roles || sky_cloud_role[source])return base;
    }
    length=fabs(x)+fabs(y)+z;if(!(length>0) || !isfinite(length))return base;
    ix=(int)(63.5f+63.0f*x/length);iy=(int)(63.5f-63.0f*y/length);
    level=(int)(z/length*96);if(level>sky_night_strength)level=sky_night_strength;
    if(level<=0)return base;
    pixel=sky_night_pixels[iy*128+ix];
    /* AWN2 marks only stars placed behind the owned nebula in empty black
     * space. The rest of each coarse cell is transparent, never a large dot. */
    point=sky_night_points?(sky_night_pixels[AW_NIGHT_SKY_ART_BYTES+(iy*128+ix)/8] & (1<<((iy*128+ix)&7))):
        (pixel!=255 && host_basepal[3*pixel]>160 && host_basepal[3*pixel+1]>160 && host_basepal[3*pixel+2]>160);
    /* Legacy composites have no role mask; shrink only unmistakably bright
     * neutral star texels. Explicit AWN2 roles keep nebula highlights intact. */
    if(point && !R_NightStarPoint(ix,iy,x,y,z))pixel=255;
    if(sky_starsky.value>0 && pixel!=255){
        starlevel=level;
        /* The original bright point stays in place. Only one in five bright
         * texels cools and gently pulses over sixteen slow world-clock steps;
         * nebula luminance and cloud time are not animated by this effect. */
        if(point && host_basepal[3*pixel]>160 && host_basepal[3*pixel+1]>160 &&
           host_basepal[3*pixel+2]>160 && (ix*17+iy*13)%5==0){
            twinkle=(sky_night_step+ix+iy)&15;if(twinkle>8)twinkle=16-twinkle;
            starlevel-=twinkle/2;if(starlevel<1)starlevel=1;
            pixel=sky_night_blue[pixel];
        }
        base=sky_night_fade[starlevel*256+pixel];
    }
    for(m=0;m<2;m++){
        if(sky_moon[m][2]<=0)continue;
        dot=x*sky_moon[m][0]+y*sky_moon[m][1]+z*sky_moon[m][2];
        if(dot<=0)continue;
        radius=m?.04680851f:.11f;
        u=(x*sky_moon_right[m][0]+y*sky_moon_right[m][1])/(dot*radius);
        if(u<=-1 || u>=1)continue;
        v=(x*sky_moon_up[m][0]+y*sky_moon_up[m][1]+z*sky_moon_up[m][2])/(dot*radius);
        if(v<=-1 || v>=1 || u*u+v*v>=1)continue;
        /* A transparent unlit phase is still a solid moon silhouette. Do not
         * leave the already sampled star/nebula visible through its dark limb. */
        base=back;
        ix=(int)((u+1)*12);iy=(int)((1-v)*12);
        pixel=sky_night_pixels[16384+(m*8+sky_moon_phase[m])*576+iy*24+ix];
        if(pixel!=255)base=sky_night_fade[level*256+pixel];
    }
    return base;
}

void R_InitDayNight(void)
{
    int i,j,r,g,b,dr,dg,db,best,distance,best_distance;
    Cvar_RegisterVariable(&sky_daynight);Cvar_RegisterVariable(&sky_type);
    Cvar_RegisterVariable(&sky_sun_enabled);Cvar_RegisterVariable(&sky_clouds);
    Cvar_RegisterVariable(&sky_cloud_speed);Cvar_RegisterVariable(&sky_cloud_type);
    Cvar_RegisterVariable(&sky_night_clouds);Cvar_RegisterVariable(&sky_cloud_control);
    Cvar_RegisterVariable(&sky_day_clouds);Cvar_RegisterVariable(&sky_nightsky_mode);
    Cvar_RegisterVariable(&sky_starsky);Cvar_RegisterVariable(&sky_nightsky);
    Cvar_RegisterVariable(&sky_night_light);Cvar_RegisterVariable(&sky_night_tint);
    Cvar_RegisterVariable(&sky_horizon_veil);Cvar_RegisterVariable(&sky_light_hue);
    Cmd_AddCommand("aw_light_hue_set",R_LightHueCommand);
    Cmd_AddCommand("aw_sky_type_set",R_SkyTypeCommand);
    Cmd_AddCommand("aw_skyspeed_set",R_SkySpeedCommand);
    Cmd_AddCommand("aw_cloud_type_set",R_SkyCloudTypeCommand);
    Cmd_AddCommand("aw_night_clouds_set",R_SkyNightCloudCommand);
    Cmd_AddCommand("aw_cloud_control_set",R_SkyCloudControlCommand);
    Cmd_AddCommand("aw_day_clouds_set",R_SkyDayCloudCommand);
    Cmd_AddCommand("aw_nightsky_mode_set",R_SkyNightModeCommand);
    sky_bank_ready=R_SkyPaletteBank();
    if(!host_basepal)return;
    for(i=0;i<4096;i++){
        r=(i>>8)*17;g=((i>>4)&15)*17;b=(i&15)*17;
        best=0;best_distance=0x7fffffff;
        for(j=0;j<256;j++){
            dr=r-host_basepal[3*j];dg=g-host_basepal[3*j+1];db=b-host_basepal[3*j+2];
            distance=dr*dr+dg*dg+db*db;
            if(distance<best_distance){best=j;best_distance=distance;}
        }
        sky_rgb[i]=(byte)best;
    }
    sky_tints_ready=1;sky_phase_last=sky_table_phase=-2;sky_table_type=sky_made_type=-1;sky_sun_colour=-1;
}
/* Cache 32 colour steps per transition. No pixel chooses between endpoints:
 * interpolate RGB first, then map each source colour once for the entire tile. */
static int R_SkyDayPhase(int milliseconds)
{
    int minute=milliseconds/60000,a,b,blend;
    if(minute<300 || minute>=1200)return 3<<10;
    if(minute<360){a=3;b=1;blend=(minute-300)*32/60;}
    else if(minute<480){a=1;b=0;blend=(minute-360)*32/120;}
    else if(minute<960)return 0;
    else if(minute<1080){a=0;b=2;blend=(minute-960)*32/120;}
    else{a=2;b=3;blend=(minute-1080)*32/120;}
    return (a<<10)|(b<<6)|blend;
}
/* Artistic Type2 keys. Source-clock sunrise/sunset anchors are retained;
 * late sunset is cool by 20:00, and predawn reverses the same cool/warm order. */
static int R_SkyType2Phase(int milliseconds)
{
    static const short minutes[]={240,270,360,420,480,960,1020,1080,1140,1185,1230,1260};
    static const byte stops[]={3,4,2,1,0,0,1,2,2,4,4,3};
    int minute=milliseconds/60000,i,mix;
    if(minute<minutes[0] || minute>=minutes[11])return 3<<10;
    for(i=0;i<11;i++)if(minute<minutes[i+1]){
        if(stops[i]==stops[i+1])return stops[i]<<10;
        mix=(minute-minutes[i])*32/(minutes[i+1]-minutes[i]);
        return (stops[i]<<10)|(stops[i+1]<<6)|mix;
    }
    return 3<<10;
}
/* Gold, red and blue-hour endpoints: low sky, cloud belt, upper sky. Each
 * endpoint retains dark-clear / bright-cloud contrast from source luminance. */
static const byte type2_sky[3][3][2][3]={
    {{{100,69,138},{255,232,160}},{{100,69,138},{255,174,66}},{{52,73,110},{250,104,45}}},
    {{{100,69,138},{255,174,66}},{{100,69,138},{250,104,45}},{{52,73,110},{210,50,34}}},
    {{{52,73,110},{153,38,79}},{{52,73,110},{100,69,138}},{{52,73,110},{100,69,138}}}
};
/* Separate opaque cloud-body colors: dark clouds stay red over the cool
 * atmosphere instead of being mistaken for holes in the masked layer. */
static const byte type2_cloud_body[3][3][3]={
    {{153,38,79},{153,38,79},{100,69,138}},
    {{153,38,79},{153,38,79},{100,69,138}},
    {{52,73,110},{52,73,110},{52,73,110}}
};
static const byte type2_fog[5][3]={{206,227,255},{181,94,40},{105,35,37},{9,10,11},{52,73,110}};
static const byte type2_glow[5][3]={{206,227,255},{255,177,54},{237,81,27},{9,10,11},{104,52,63}};
static const byte type2_strength[5]={0,7,5,0,2};
static const byte type2_ambient[5][3]={{255,255,255},{255,225,198},{255,188,178},{110,132,168},{145,166,220}};
static void R_SkyEndpoint(int stop,int band,int index,int *rgb)
{
    int k,luma=(host_basepal[3*index]+2*host_basepal[3*index+1]+host_basepal[3*index+2])/4;
    int t=stop==1?0:stop==2?1:2,low=band<6?0:1,weight=band<6?band*32/6:(band-6)*32/9;
    int a,b,value,night,cloud=sky_cloud_role[index];
    if(sky_cloud_roles && !cloud)luma=0;
    if(sky_cloud_roles && cloud==1 && sky_frame_type==3 && stop==2){luma+=64;if(luma>255)luma=255;}
    night=R_SkyNearest(sky_rgb_stops[3][0]*(128+luma)/256,
        sky_rgb_stops[3][1]*(128+luma)/256,sky_rgb_stops[3][2]*(128+luma)/256);
    for(k=0;k<3;k++){
        if(stop==0 || stop==3)value=(host_basepal[3*(stop?night:index)+k]*band+
            type2_fog[stop][k]*(15-band))/15;
        else{
            a=sky_cloud_roles && cloud?type2_cloud_body[t][low][k]:type2_sky[t][low][0][k];
            b=sky_cloud_roles && cloud?type2_cloud_body[t][low+1][k]:type2_sky[t][low+1][0][k];
            a=(a*(255-luma)+type2_sky[t][low][1][k]*luma)/255;
            b=(b*(255-luma)+type2_sky[t][low+1][1][k]*luma)/255;
            value=(a*(32-weight)+b*weight)/32;
            if(sky_cloud_roles && cloud==2){
                if(sky_frame_type==3 && band<7)value=8+luma/40+band;
                else value=(sky_bank_rgb[1][k]*(255-luma)+sky_bank_rgb[0][k]*luma)/255;
            }
        }
        /* The very horizon meets geometry fog. A narrow blend above it keeps
         * cloud contrast, unlike applying full haze to the whole lower sky. */
        if(stop!=0 && stop!=3 && band<3 && !(sky_cloud_roles && cloud==2 && sky_frame_type==3 && band>0))value=(value*band+type2_fog[stop][k]*(3-band))/3;
        rgb[k]=value;
    }
}
static void R_SkyType2Tables(int phase)
{
    int a=phase>>10,b=(phase>>6)&15,mix=phase&63,i,k,band,level,left[3],right[3],rgb[3],glow[3];
    sky_glow_strength=(type2_strength[a]*(32-mix)+type2_strength[b]*mix)/32;
    if(sky_frame_type==3 && sky_glow_strength>2){sky_glow_strength+=2;if(sky_glow_strength>7)sky_glow_strength=7;}
    for(k=0;k<3;k++)glow[k]=(type2_glow[a][k]*(32-mix)+type2_glow[b][k]*mix)/32;
    for(i=0;i<256;i++){
        for(band=0;band<16;band++){
            /* Exact stable daytime/nighttime compatibility with Type1 haze. */
            if(phase==0 || phase==(3<<10)){
                if(band==15)sky_gradient[band*256+i]=sky_tint[i];
                else{
                    for(k=0;k<3;k++)rgb[k]=(host_basepal[3*sky_tint[i]+k]*band+type2_fog[a][k]*(15-band))/15;
                    sky_gradient[band*256+i]=R_SkyNearest(rgb[0],rgb[1],rgb[2]);
                }
            }
            else{
                R_SkyEndpoint(a,band,i,left);R_SkyEndpoint(b,band,i,right);
                for(k=0;k<3;k++)rgb[k]=(left[k]*(32-mix)+right[k]*mix)/32;
                sky_gradient[band*256+i]=R_SkyNearest(rgb[0],rgb[1],rgb[2]);
            }
        }
        sky_glow[i]=i;
        for(level=1;level<8;level++){
            for(k=0;k<3;k++)rgb[k]=(host_basepal[3*i+k]*(32-3*level)+glow[k]*3*level)/32;
            sky_glow[level*256+i]=R_SkyNearest(rgb[0],rgb[1],rgb[2]);
        }
    }
}
/* Source visible-position orbit, not the distinct directional-light vector:
 * 06:00..20:00, east +X to west -X, slightly south (-Y), peak at 13:00.
 * The original piecewise position is normalised once per changed clock sample. */
static void R_SkySunFrame(int milliseconds)
{
    double hour=milliseconds/3600000.0,t,length;int level,i,k,j,rgb[3],target[3],core[3],tone[3],amount,red=0,key;
    sky_sun_visible=hour>6 && hour<20 && sky_sun_enabled.value>0;
    sky_warm_side=hour<13?1:-1;
    if(milliseconds!=sky_sun_ms){
        t=(hour-6)/14;sky_sun[0]=(float)(400*(1-2*t));sky_sun[1]=-75;
        sky_sun[2]=400-fabs(sky_sun[0]);
        length=sqrt((double)sky_sun[0]*sky_sun[0]+5625+(double)sky_sun[2]*sky_sun[2]);
        for(k=0;k<3;k++)sky_sun[k]/=(float)length;
        sky_sun_ms=milliseconds;
    }
    if(!sky_sun_visible)return;
    level=(int)(sky_sun[2]*15);if(level<0)level=0;if(level>15)level=15;
    if(sky_frame_type>=2){
        if((sky_phase>>10)==2)red+=32-(sky_phase&63);
        if(((sky_phase>>6)&15)==2)red+=sky_phase&63;
        red/=4;
    }
    key=level+red*16;if(key==sky_sun_colour)return;
    sky_sun_colour=key;target[0]=255;target[1]=32+14*level-red*8;target[2]=8+13*level-red*4;
    if(target[1]<32)target[1]=32;
    if(target[2]<8)target[2]=8;
    core[0]=255;core[1]=level>=4?232:level>=2?174:level?104:50;
    core[2]=level>=4?160:level>=2?66:level?45:34;
    for(i=0;i<256;i++)for(k=0;k<8;k++){
        amount=(k+1)*(level<3?24:28);
        if(k==7)amount=256;
        for(j=0;j<3;j++){
            tone[j]=k<5?target[j]:(target[j]*(7-k)+core[j]*(k-4))/3;
            rgb[j]=(host_basepal[3*i+j]*(256-amount)+tone[j]*amount)/256;
        }
        sun_halo[k*256+i]=R_SkyNearest(rgb[0],rgb[1],rgb[2]);
    }
}
const float *R_DayNightSunDirection(void)
{
    return R_DayNightFogColours() && sky_sun_visible?sky_sun:NULL;
}
/* Called ONLY for sky-marked pixels after opaque/masked depth writes. Rays are
 * unnormalised world directions. Squared cosine tests avoid a per-pixel sqrt. */
unsigned char R_DayNightSkyPixel(unsigned char colour,float x,float y,float z,int fog)
{
    static const float threshold[8]={.96984631f,.97552826f,.98163085f,.98718503f,
        .99240388f,.99513403f,.99726095f,.99878203f}; /* 10..2 degree soft halo */
    int band,level;float dot,length,forward;byte source=colour;
    if(!R_DayNightFogColours())return colour;
    if(!isfinite(x) || !isfinite(y) || !isfinite(z))return colour;
    band=z<=0?0:z>=.35f?15:(int)(z*(15.0f/.35f));
    if(sky_frame_type>=2){
        colour=sky_gradient[band*256+colour];
        forward=x*sky_warm_side;
        if(band>0 && band<12 && forward>0 && sky_glow_strength){
            level=forward>=1?sky_glow_strength:(int)(forward*sky_glow_strength);
            level=level*(15-band)/15;
            colour=sky_glow[level*256+colour];
        }
        if(fog && sky_horizon_veil.value>=1){
            int veil=sky_horizon_veil.value>15?15:(int)sky_horizon_veil.value;
            if(band<veil)colour=sky_fog[(15-band*15/veil)*256+colour];
        }
    }else{
        if(sky_night_strength)colour=sky_tint[colour];
        if(fog)colour=sky_fog[(15-band)*256+colour];
    }
    if(sky_sun_visible && z>=0){
        dot=x*sky_sun[0]+y*sky_sun[1]+z*sky_sun[2];
        length=x*x+y*y+z*z;
        if(dot>0 && dot*dot>length*threshold[0]){
            dot*=dot;level=0;
            while(level<7 && dot>length*threshold[level+1])level++;
            colour=sun_halo[level*256+colour];
        }
    }
    return R_NightPixel(colour,source,x,y,z);
}

static int R_SkyNightLightOn(void){return sky_night_light.value>0;}
static int R_SkyNightTint(void)
{
    float tint=sky_night_tint.value;
    return !(tint>=0)?0:tint>100?100:(int)tint;
}
/* Split the scene ambient: its brightness becomes the daylight factor applied
 * to the light (quantised to steps of 8 so the surface cache rebuilds only
 * when it changes), its hue stays in the table at the chosen strength. */
static void R_SkyNightLight(int *ambient)
{
    int k,brightness,tint,i;
    sky_table_daylight=256;
    if(!R_SkyNightLightOn() || (ambient[0]>=255 && ambient[1]>=255 && ambient[2]>=255))return;
    brightness=(ambient[0]*299+ambient[1]*587+ambient[2]*114)/1000;
    if(brightness<8)brightness=8;
    tint=R_SkyNightTint();
    for(k=0;k<3;k++)ambient[k]=255+(ambient[k]*255/brightness-255)*tint/100;
    sky_table_daylight=(brightness*256/255+4)&~7;
    if(sky_table_daylight<8)sky_table_daylight=8;
    if(sky_table_daylight>256)sky_table_daylight=256;
    for(i=0;i<256;i++)
        sky_shade[i]=R_SkyNearest(host_basepal[3*i]*sky_table_daylight>>8,
            host_basepal[3*i+1]*sky_table_daylight>>8,host_basepal[3*i+2]*sky_table_daylight>>8);
}
static void R_LightHue(int *hue)
{
    int k;
    hue[0]=255;hue[1]=210;hue[2]=140;
    if(Q_sscanf(sky_light_hue.string,"%d %d %d",&hue[0],&hue[1],&hue[2])!=3){hue[0]=255;hue[1]=210;hue[2]=140;}
    for(k=0;k<3;k++)hue[k]=hue[k]<0?0:hue[k]>255?255:hue[k];
}
static void R_BuildWarmLight(void)
{
    int hue[3],level,i,k,rgb[3];float lum,t[3],b,w;const byte *plain=(const byte *)vid.colormap;
    if(!host_basepal || !sky_tints_ready || !plain)return;
    R_LightHue(hue);
    lum=(hue[0]*299+hue[1]*587+hue[2]*114)/1000.0f;if(lum<1)lum=1;
    for(k=0;k<3;k++)t[k]=hue[k]/lum;
    for(level=0;level<64;level++){
        b=1-level/63.0f;if(b<.15f)b=.15f;
        w=(b-.4f)/.6f;
        if(!(w>0)){memcpy(warm_table+level*256,plain+level*256,256);continue;}
        if(w>1)w=1;
        for(i=0;i<256;i++){
            for(k=0;k<3;k++){rgb[k]=(int)(host_basepal[3*i+k]*b*(1+w*(t[k]-1))+.5f);if(rgb[k]>255)rgb[k]=255;if(rgb[k]<0)rgb[k]=0;}
            warm_table[level*256+i]=R_SkyNearest(rgb[0],rgb[1],rgb[2]);
        }
    }
    snprintf(warm_built,sizeof warm_built,"%s",sky_light_hue.string);
    r_warm_colormap=warm_table;
}
static void R_LightHueCommand(void)
{
    int hue[3],k;char text[32];
    if(Cmd_Argc()==4){
        for(k=0;k<3;k++){hue[k]=atoi(Cmd_Argv(k+1));hue[k]=hue[k]<0?0:hue[k]>255?255:hue[k];}
        snprintf(text,sizeof text,"%ld %ld %ld",(long)hue[0],(long)hue[1],(long)hue[2]);
        Cvar_Set(sky_light_hue.name,text);
    }else if(Cmd_Argc()!=1){Con_Printf("Usage: dbg light hue [R G B 0..255] (default 255 210 140)\n");return;}
    R_LightHue(hue);
    Con_Printf("Light hue %ld %ld %ld (torch, lamp and window light; aw_warm_light %s).\n",
        (long)hue[0],(long)hue[1],(long)hue[2],r_warm_colormap?"on":"waiting for the palette");
}
static void R_SkyColourTables(int phase)
{
    int a=phase>>10,b=(phase>>6)&15,mix=phase&63,i,k,level,luma,rgb[3],fog[3],ambient[3],source[3],left,right,aa,bb;
    for(k=0;k<3;k++)fog[k]=sky_frame_type>=2?
        (type2_fog[a][k]*(32-mix)+type2_fog[b][k]*mix)/32:
        (fog_rgb_stops[a][k]*(32-mix)+fog_rgb_stops[b][k]*mix)/32;
    for(k=0;k<3;k++)ambient[k]=sky_frame_type>=2?
        (type2_ambient[a][k]*(32-mix)+type2_ambient[b][k]*mix)/32:255;
    R_SkyNightLight(ambient);
    aa=a==4?3:a;bb=b==4?3:b;
    for(i=0;i<256;i++){
        luma=(host_basepal[3*i]+2*host_basepal[3*i+1]+host_basepal[3*i+2])/4;
        for(k=0;k<3;k++){
            left=aa?sky_rgb_stops[aa][k]*(128+luma)/256:host_basepal[3*i+k];
            right=bb?sky_rgb_stops[bb][k]*(128+luma)/256:host_basepal[3*i+k];
            if(sky_cloud_roles && (sky_frame_type>=2 || sky_bank_ready)){
                left=sky_cloud_role[i]?fog_rgb_stops[aa][k]*(128+luma)/256:sky_rgb_stops[aa][k];
                right=sky_cloud_role[i]?fog_rgb_stops[bb][k]*(128+luma)/256:sky_rgb_stops[bb][k];
            }
            rgb[k]=(left*(32-mix)+right*mix)/32;
        }
        sky_tint[i]=(phase || (sky_cloud_roles && (sky_frame_type>=2 || sky_bank_ready)))?R_SkyNearest(rgb[0],rgb[1],rgb[2]):i;
        for(k=0;k<3;k++)source[k]=host_basepal[3*i+k]*ambient[k]/255;
        /* Scene tone is built into the existing geometry LUT. Daytime and V1
         * retain exact near indices; sky/UI do not consume the ambient tone. */
        sky_fog[i]=(sky_frame_type==1 || phase==0)?i:R_SkyNearest(source[0],source[1],source[2]);
        for(level=1;level<16;level++){
            for(k=0;k<3;k++)rgb[k]=(source[k]*(15-level)+fog[k]*level)/15;
            sky_fog[level*256+i]=R_SkyNearest(rgb[0],rgb[1],rgb[2]);
        }
    }
    if(sky_frame_type>=2)R_SkyType2Tables(phase);
    R_NightTables();
    sky_table_phase=phase;sky_table_type=sky_frame_type;
    sky_table_night=R_SkyNightLightOn();sky_table_tint=R_SkyNightTint();
}
const unsigned char *R_DayNightFogColours(void)
{
    if(sky_exterior && sky_daynight.value>0 && sky_tints_ready && sky_phase>=0)return sky_fog;
    return NULL;
}
static int sky_xlast=-1,sky_ylast=-1;
static void R_InitSkyPixels(const byte *src);
/* Bounded first-entity reader: no shared/unbounded COM_Parse token buffer. */
static char *R_SkyToken(char *data,char *token,int capacity)
{
    int n=0,quoted=0;
    if(!data)return NULL;
    for(;;){
        while(*data && (unsigned char)*data<=32)data++;
        if(data[0]=='/' && data[1]=='/'){while(*data && *data!='\n')data++;continue;}
        break;
    }
    if(!*data)return NULL;
    if(*data=='{' || *data=='}'){token[0]=*data++;token[1]=0;return data;}
    if(*data=='"'){quoted=1;data++;}
    while(*data){
        if(quoted && *data=='"'){token[n]=0;return data+1;}
        if(!quoted && ((unsigned char)*data<=32 || *data=='{' || *data=='}'))break;
        if(n>=capacity-1)return NULL;
        token[n++]=*data++;
    }
    if(quoted)return NULL;
    token[n]=0;return data;
}
static int R_SkySceneMode(model_t *model)
{
    char *data,key[1024],value[1024];int mode=0,world=0,pairs=0,seen=0;
    if(!model || !(data=model->entities))return 0;
    data=R_SkyToken(data,value,sizeof value);if(!data || strcmp(value,"{"))return -2;
    while((data=R_SkyToken(data,key,sizeof key))!=NULL && strcmp(key,"}")){
        if(++pairs>256)return -2;
        data=R_SkyToken(data,value,sizeof value);if(!data || !strcmp(value,"{") || !strcmp(value,"}"))return -2;
        if(!strcmp(key,"classname"))world=!strcmp(value,"worldspawn");
        if(!strcmp(key,"_aw_sky_mode")){
            if(seen++)return -2;
            if(!strcmp(value,"exterior"))mode=1;
            else if(!strcmp(value,"interior"))mode=-1;
            else return -2;
        }
        if(!strcmp(key,"_aw_sky_asset") && strcmp(value,AW_SHARED_SKY_PATH))return -2;
    }
    return data&&world?mode:-2;
}
static int R_LoadSharedSky(void)
{
    FILE *file=NULL;int size;
    if(sky_shared)return 1;
    size=COM_FOpenFile(AW_SHARED_SKY_PATH,&file);
    if(size!=AW_SHARED_SKY_BYTES || !file){if(file)fclose(file);return 0;}
    /* Stage in the existing static image, not a Hunk allocation or map pointer. */
    sky_initialized=0;r_skysource=NULL;
    if(fread(newsky,1,AW_SHARED_SKY_BYTES,file)!=AW_SHARED_SKY_BYTES){fclose(file);return 0;}
    fclose(file);R_InitSkyPixels(newsky);sky_shared=1;return 1;
}
int R_SkyExterior(void){return sky_exterior;}
void R_SetSkyBackground(model_t *model)
{
    int i,mode;r_backgroundsky=0;sky_exterior=0;if(!model)return;
    mode=R_SkySceneMode(model);
    if(mode<0)return; /* Explicit interiors and invalid metadata fail closed. */
    if(mode==1){
        if(R_LoadSharedSky()){R_LoadNightSky();r_backgroundsky=1;sky_exterior=1;}
        else Con_Printf("Exterior sky unavailable: expected %s (%d indexed bytes).\n",AW_SHARED_SKY_PATH,AW_SHARED_SKY_BYTES);
        return;
    }
    /* Compatibility for old maps. New exterior output must emit explicit mode. */
    if(!sky_initialized || !model->textures)return;
    for(i=0;i<model->numtextures;i++)if(model->textures[i] && !strncmp(model->textures[i]->name,"sky",3)){r_backgroundsky=1;return;}
}


/*
=============
R_InitSky

A sky texture is 256*128: left masked scrolling clouds, right opaque base
==============
*/
static void R_InitSkyPixels(const byte *src)
{
	int i,j;

    R_SkyCloudRoles(src);R_SkyNightCloudRoles(src);
    r_sky_texture_scale=sky_cloud_roles?128:378;
    sky_table_phase=-2;sky_table_type=-1;

	for (i=0 ; i<128 ; i++)
	{
		for (j=0 ; j<128 ; j++)
		{
			newsky[(i*256) + j + 128] = src[i*256 + j + 128];
		}
	}

	for (i=0 ; i<128 ; i++)
	{
		for (j=0 ; j<131 ; j++)
		{
			if (src[i*256 + (j & 0x7F)])
			{
				bottomsky[(i*131) + j] = src[i*256 + (j & 0x7F)];
				bottommask[(i*131) + j] = 0;
			}
			else
			{
				bottomsky[(i*131) + j] = 0;
				bottommask[(i*131) + j] = 0xff;
			}
		}
	}

	r_skysource = newsky;sky_initialized=1;sky_xlast=sky_ylast=-1;sky_phase_last=-2;r_skymade=0;
}


void R_InitSky(texture_t *mt)
{
    if(sky_shared || !mt)return;
    if(mt->width!=256 || mt->height!=128){Con_Printf("Invalid legacy sky dimensions.\n");return;}
    R_InitSkyPixels((byte *)mt+mt->offsets[0]);
}

/*
=================
R_MakeSky
=================
*/
void R_MakeSky (void)
{
	int			x, y;
	int			ofs, baseofs;
	int			xshift, yshift;
	unsigned	*pnewsky;
    int clouds=!sky_exterior || sky_clouds.value>0;


	xshift = skytime*skyspeed;
	yshift = skytime*skyspeed;

	if ((xshift == sky_xlast) && (yshift == sky_ylast) && sky_phase==sky_phase_last && sky_made_type==sky_frame_type && sky_made_clouds==clouds && sky_made_cloud_type==R_SkyCloudType() && sky_made_cloud_density==sky_night_cloud_density && sky_made_night==(sky_night_strength>0) && sky_made_coverage_roles==sky_coverage_roles_active){r_skymade=1;return;}
    sky_phase_last=sky_phase;sky_made_type=sky_frame_type;sky_made_clouds=clouds;sky_made_cloud_type=R_SkyCloudType();sky_made_cloud_density=sky_night_cloud_density;sky_made_night=sky_night_strength>0;sky_made_coverage_roles=sky_coverage_roles_active;

	sky_xlast = xshift;
	sky_ylast = yshift;

    if(!clouds){
        int colour=sky_phase>=0 && sky_frame_type==1 && !sky_night_strength?sky_tint[224]:224;
        for(y=0;y<SKYSIZE;y++)memset(newsky+y*256,colour,SKYSIZE);
        r_skymade=1;return;
    }

    if(R_SkyCloudType()==2 || sky_night_cloud_density<16){
        int tint=sky_phase>=0 && (sky_phase>0 || (sky_cloud_roles && sky_bank_ready)) && sky_frame_type==1 && !sky_night_strength;
        for(y=0;y<SKYSIZE;y++){
            baseofs=((y+yshift)&SKYMASK)*131;
            for(x=0;x<SKYSIZE;x++){
                ofs=baseofs+((x+xshift)&SKYMASK);
                newsky[y*256+x]=R_SkyVeilComposite(newsky[y*256+x+128],ofs,x,y,sky_night_cloud_density);
                if(tint)newsky[y*256+x]=sky_tint[newsky[y*256+x]];
            }
        }
        r_skymade=1;return;
    }

    if(sky_phase>=0 && (sky_phase>0 || (sky_cloud_roles && sky_bank_ready)) && sky_frame_type==1 && !sky_night_strength){
        for(y=0;y<SKYSIZE;y++){
            baseofs=((y+yshift)&SKYMASK)*131;
            for(x=0;x<SKYSIZE;x++){
                ofs=baseofs+((x+xshift)&SKYMASK);
                newsky[y*256+x]=sky_tint[(newsky[y*256+x+128]&bottommask[ofs])|bottomsky[ofs]];
            }
        }
        r_skymade=1;return;
    }
	pnewsky = (unsigned *)&newsky[0];

	for (y=0 ; y<SKYSIZE ; y++)
	{
		baseofs = ((y+yshift) & SKYMASK) * 131;

// FIXME: clean this up
#if UNALIGNED_OK

		for (x=0 ; x<SKYSIZE ; x += 4)
		{
			ofs = baseofs + ((x+xshift) & SKYMASK);

		// PORT: unaligned dword access to bottommask and bottomsky

			*pnewsky = (*(pnewsky + (128 / sizeof (unsigned))) &
						*(unsigned *)&bottommask[ofs]) |
						*(unsigned *)&bottomsky[ofs];
			pnewsky++;
		}

#else

		for (x=0 ; x<SKYSIZE ; x++)
		{
			ofs = baseofs + ((x+xshift) & SKYMASK);

			*(byte *)pnewsky = (*((byte *)pnewsky + 128) &
						*(byte *)&bottommask[ofs]) |
						*(byte *)&bottomsky[ofs];
			pnewsky = (unsigned *)((byte *)pnewsky + 1);
		}

#endif

		pnewsky += 128 / sizeof (unsigned);
	}

	r_skymade = 1;
}


/*
=================
R_GenSkyTile
=================
*/
void R_GenSkyTile (void *pdest)
{
    int y;byte *out=(byte *)pdest;
    R_MakeSky();
    for(y=0;y<SKYSIZE;y++)memcpy(out+y*SKYSIZE,newsky+y*256,SKYSIZE);
}

void R_GenSkyTile16 (void *pdest)
{
    int x,y;unsigned short *out=(unsigned short *)pdest;
    R_MakeSky();
    for(y=0;y<SKYSIZE;y++)for(x=0;x<SKYSIZE;x++)
        out[y*SKYSIZE+x]=d_8to16table[newsky[y*256+x]];
}


/*
=============
R_SetSkyFrame
==============
*/
void R_SetSkyFrame (void)
{
	int		g, s1, s2;
	float	temp;double environment_time;int clock_ready,clock_ms=0,clock_days=-1;

	skyspeed = iskyspeed;
	skyspeed2 = iskyspeed2;

	g = GreatestCommonDivisor (iskyspeed, iskyspeed2);
	s1 = iskyspeed / g;
	s2 = iskyspeed2 / g;
	temp = SKYSIZE * s1 * s2;

    /* Persisted world-clock phase survives map-local cl.time resets. */
    environment_time=realtime;
    clock_ready=AW_ClockEnsure();
    if(clock_ready){
        clock_days=R_SkyStoredDay();
        clock_ms=AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:ms");
        environment_time=(double)(clock_days<0?0:clock_days)*86400.0+clock_ms/1000.0;
    }
    clock_ms=AW_DayGalleryClock(clock_ms);
    sky_frame_type=R_SkyType();
    sky_phase=sky_exterior && sky_daynight.value>0 && sky_tints_ready && clock_ready?
        (sky_frame_type>=2?R_SkyType2Phase(clock_ms):R_SkyDayPhase(clock_ms)):-1;
    if(sky_phase>=0){
        if(sky_phase!=sky_table_phase || sky_frame_type!=sky_table_type ||
           R_SkyNightLightOn()!=sky_table_night || R_SkyNightTint()!=sky_table_tint)R_SkyColourTables(sky_phase);
        R_SkySunFrame(clock_ms);
        R_NightFrame(clock_ms,clock_days);
    }else{
        sky_table_daylight=256;
        sky_sun_visible=0;sky_night_strength=0;sky_night_roles_active=0;sky_coverage_roles_active=0;
        sky_night_cloud_density=!clock_ready && sky_exterior && sky_daynight.value>0?16:(R_SkyCloudType()==2?4:16);
    }
    /* The warm light table follows aw_light_hue; rebuilt only when it changes. */
    if(sky_tints_ready && strcmp(warm_built,sky_light_hue.string)){R_BuildWarmLight();D_FlushCaches();}
    /* Daylight reaches the light only where the day/night tables are in use;
     * a change rebuilds the surface cache once (quantised steps). */
    {
        int daylight=sky_phase>=0 && R_DayNightFogColours()?sky_table_daylight:256;
        if(daylight!=r_daylight){r_daylight=daylight;D_FlushCaches();}
        d_nightshade=daylight<256?sky_shade:NULL;
    }
    /* At default clock scale, legacy travel is 240 texels per real second.
     * The cloud-only multiplier defaults to 1/300 (0.8 texels/sec). It never
     * affects sun/colour timing, and gallery previews leave cloud time alone.
     * Scale before wrapping so midnight, save restore and map changes agree. */
    skytime=(float)fmod(environment_time*R_SkyCloudSpeed(),temp);


	r_skymade = 0;
}
