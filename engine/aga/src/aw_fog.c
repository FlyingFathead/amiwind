/* SPDX-License-Identifier: GPL-2.0-or-later
 * Palette fog applied to the rendered viewport using the inverse-depth buffer.
 * 4 KiB colour table baked on the host; 32 KiB depth table rebuilt on setting changes.
 */
#include "quakedef.h"
#include "aw_maps.h"
#include "aw_town.h"
#include "aw_sky.h"
#include "aw_horizon.h"
#include "aw_rcount.h"
extern short *d_pzbuffer;
extern unsigned int d_zwidth;
extern cvar_t aw_drawdistance;
extern vec3_t modelorg;
extern float xcenter,ycenter,xscale,yscale;
static cvar_t aw_fog={"aw_fog","1",true};
/* Land Fill Independence v1: disabling colour fog must not disable an
 * enabled geometric LAND pass. 0 disables LAND fill for a measured A/B. */
static cvar_t aw_land_fill={"aw_land_fill","1",true};
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
void AW_FogInit(void) { Cvar_RegisterVariable(&aw_land_fill);Cvar_RegisterVariable(&aw_terrain_horizon);Cvar_RegisterVariable(&aw_skyline_fill);Cvar_RegisterVariable(&aw_horizon_defaults);Cmd_AddCommand("aw_horizon_migrate",horizon_migrate);Cmd_AddCommand("aw_horizon_stats",AW_HorizonReport);Cvar_RegisterVariable(&aw_fog);Cvar_RegisterVariable(&aw_cull);Cmd_AddCommand("aw_fog_distance",distance_command);Cmd_AddCommand("aw_viewdistance_cycle",cycle_distance);colours=COM_LoadHunkFile("gfx/fog.lmp"); }
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
    if(!ramp || (!fog && !environment && !aw_land_fill.value))return;
    distance=AW_DrawDistance();
    if(fog && distance!=old_distance){old_distance=distance;AW_FogDepths(depths,distance);}
    w=r_refdef.vrect.width;h=r_refdef.vrect.height;extent=w>h?w:h;
    if(extent<=0)return;
    step=2.0f/extent;for(k=0;k<3;k++)delta[k]=vright[k]*step;
    fill=fog && aw_skyline_fill.value>0 && w<=SKYLINE_MAX;
    if(fill)memset(skyline,0,w);
    if(fog || environment)for(y=r_refdef.vrect.y;y<r_refdef.vrect.y+h;y++){
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
    /* aw_cull 7 (debug): mark where the sky ray crosses the horizon. */
    if((int)aw_cull.value==7)for(x=0;x<w;x++)for(y=r_refdef.vrect.y+1;y<r_refdef.vrect.y+h;y++){
        u=(r_refdef.vrect.x+x-((int)vid.width>>1))*step;v=(((int)vid.height>>1)-y)*step;
        if(vpn[2]+u*vright[2]+v*vup[2]<0 && vpn[2]+u*vright[2]+(v+step)*vup[2]>=0)
            vid.buffer[y*vid.rowbytes+r_refdef.vrect.x+x]^=0x80;
    }
    if(aw_land_fill.value){
        if(aw_terrain_horizon.value==1)AW_HorizonDraw(ramp[15<<8],distance);
        if(aw_chim_far_draw)aw_chim_far_draw(ramp[15<<8],distance);
    }
}

/* Far clipping uses the same forward depth as palette fog. Radial/cubic
 * cutoffs removed visible edge-of-screen ground before it reached the fog.
 * aw_cull (dbg cull, Options > Far detail; saved in config.cfg): 0 no far
 * test; 1 the far plane alone (the method from v0.0.31 to v0.0.41, "Full"
 * in the menu); 2: 1 plus the fog-exact test below (the same picture, fewer
 * faces; measured 2026-10-17 at the five Balmora benchmark cameras: -3.2 %
 * view time at one, +0.4..+0.8 % at the others; docs/performance/FAR-TEST.md);
 * 3 and 4 add a size-scaled cut-off ("Light", "Strong"), 5 a far detail
 * step, 6 both 4 and 5 ("Strong + small faces"). 4 is the default from
 * v0.0.42 (owner decision 2026-10-17: -17..-27 % view time); a config.cfg
 * saved before aw_cull was saved keeps 1 (AW_FarDetailSavedBefore). 7 is a
 * debug view: the fog-exact test without its colour checks (works with fog
 * off, to see what it leaves out) and the sky ray's horizon marked. */
static cvar_t aw_cull={"aw_cull","4",true};
static float far_normal[3],far_distance;
/* Brush polygons revisit the same world nodes many times in a frame.
 * Cache only the far-plane decision; PVS and brush sort keys remain untouched. */
typedef struct {short *bounds;unsigned frame;int visible;} aw_far_cache_t;
static aw_far_cache_t far_cache[2048];
static unsigned far_frame;
/* Fog-exact far test (aw_cull 2 and up; render speed plan E1). A brush model,
 * or one of its faces, is left out only where drawing it changes no pixel:
 * - every pixel it would cover takes the full fog colour: its z-buffer value
 *   (32768/depth, D_DrawZSpans) is at most the last value the fog table maps
 *   to level 15, and level 15 of the colour table maps every colour to one;
 * - whatever it would hide takes that colour too: anything behind it is
 *   deeper (level 15 as well); sky behind it lies strictly below the horizon
 *   of the fog pass's sky ray (ray z < 0), where the sky pass maps every
 *   colour to that same colour (checked each frame for all 256 colours: no
 *   sun, moon, stars or glow there); the distant land layers draw it as well;
 * - it hides no flame drawn after the fog pass (static fires, guard and
 *   player torches, aw_guard_torch.c): its z-buffer value is at most the
 *   smallest any flame particle can have this frame.
 * Both conditions are half-spaces in view space (1/z and the sky ray's z are
 * affine in screen position on a plane, and every covered pixel sample lies
 * in the projected polygon), so a polygon passes when all its vertices do and
 * a box when all its corners do. The object-silhouetting horizon
 * (aw_skyline_fill 1) marks columns from fogged scenery: no test then. */
#define FOG_HORIZON_MARGIN 1e-3f    /* sky ray z the fog pass's float stepping cannot reach from below 0 */
int (*aw_flame_depth_limit)(void);
static int fog_exact;               /* the test applies this frame */
static float fog_exact_depth;       /* view depth from which a point is full fog and hides no flame */
static float fog_down_k[3];         /* below-horizon form: k0*vpn + kx*vright + ky*vup */
static float fog_down[3];
static int size_cut;                /* aw_cull 3/4: size-scaled cut-off preset */
static int detail_step;             /* aw_cull 5/6: far detail step */
static float cut_distance;
/* r_bsp.c face tests of the current pass, in model space (x, y, z, dist):
 * aw_far_faces bit 0 = fog-exact test, bit 1 = detail step. */
float aw_far_depth[4],aw_far_down[4],aw_far_view[4];
int aw_far_faces;
/* The last z-buffer value the fog table maps to level 15 (AW_FogDepths). */
int AW_FogFullDepthValue(int distance) {
    int last;
    if(distance<100)distance=100;
    if(distance>4096)distance=4096;
    last=819200/(distance*25);
    return last>32767?32767:last;
}
/* Why the test is off this frame (dbg rcount "ft" third figure): 1 no fog or no
 * day/night tables, 2 the skyline fill, 3 level 15 not one colour, 4 the sky
 * below the horizon not that colour, 5 a flame nearer than the full fog
 * depth behind which nothing can be proved (z-buffer limit under 1). */
static int fog_exact_begin(int distance) {
    const byte *environment=R_DayNightFogColours();
    int i,w=r_refdef.vrect.width,h=r_refdef.vrect.height,extent=w>h?w:h,limit,flames;byte full;float step;
    if((int)aw_cull.value==7 && extent>0)goto geometry; /* debug view: the colour checks skipped */
    if(!colours || !aw_fog.value || !environment || extent<=0){AW_RC_ADD(RC_FAR_FOG_WHY,1);return 0;}
    if(aw_skyline_fill.value>0 && w<=SKYLINE_MAX){AW_RC_ADD(RC_FAR_FOG_WHY,2);return 0;}
    full=environment[15<<8];
    for(i=0;i<256;i++){
        if(environment[(15<<8)+i]!=full){AW_RC_ADD(RC_FAR_FOG_WHY,3);return 0;}
        if(R_DayNightSkyPixel((unsigned char)i,0,0,-1,1)!=full){AW_RC_ADD(RC_FAR_FOG_WHY,4);return 0;}
    }
geometry:
    limit=AW_FogFullDepthValue(distance);
    if(aw_flame_depth_limit && (flames=aw_flame_depth_limit())<limit)limit=flames;
    if(limit<1){AW_RC_ADD(RC_FAR_FOG_WHY,5);return 0;}
    fog_exact_depth=32768.0f/(limit+.5f);
    /* The fog pass's sky ray at screen (col,row) has z = vpn.z + (col-W/2)*step*vright.z
     * + (H/2-row)*step*vup.z; with col = xcenter + xscale*x/z and row = ycenter - yscale*y/z
     * (R_EmitEdge) that times the view depth z is k0*z + kx*x + ky*y. */
    step=2.0f/extent;
    fog_down_k[0]=vpn[2]+(xcenter-(float)((int)vid.width>>1))*step*vright[2]+
        ((float)((int)vid.height>>1)-ycenter)*step*vup[2]+FOG_HORIZON_MARGIN;
    fog_down_k[1]=xscale*step*vright[2];
    fog_down_k[2]=yscale*step*vup[2];
    for(i=0;i<3;i++)fog_down[i]=fog_down_k[0]*vpn[i]+fog_down_k[1]*vright[i]+fog_down_k[2]*vup[i];
    AW_RC_ADD(RC_FAR_FOG_ON,100);AW_RC_ADD(RC_FAR_FOG_DEPTH,(long)fog_exact_depth);
    return 1;
}
void AW_CullBegin(void) {
    float distance=AW_Interior()?4096:AW_DrawDistance();int mode=(int)aw_cull.value;
    if(!++far_frame){memset(far_cache,0,sizeof(far_cache));far_frame=1;}
    VectorCopy(vpn,far_normal);
    far_distance=DotProduct(r_origin,far_normal)+distance+16;
    fog_exact=mode>=2 && !AW_Interior() && fog_exact_begin((int)distance);
    size_cut=AW_Interior()?0:mode==3?1:mode==4 || mode==6?2:0;
    detail_step=!AW_Interior() && (mode==5 || mode==6);
    cut_distance=distance;
}
/* R_Init, before AW_FogInit: a config.cfg saved before aw_cull was saved (up to
 * v0.0.41) holds the picture that player had: Full (1). A fresh install has no
 * config.cfg and starts at the default, Strong (4); every later save keeps the
 * player's choice. */
void AW_FarDetailSavedBefore(int config_without_setting) {
    if(config_without_setting)aw_cull.string="1";
}
/* 1 when a saved config.cfg exists and never sets the named variable
 * (a configuration saved before that variable was saved). */
int AW_ConfigWithout (const char *name)
{
	FILE	*f = NULL;
	int		size, c, n, at_line = 1, length = (int)strlen (name);

	size = COM_FOpenFile ("config.cfg", &f);
	if (size < 0 || !f)
		return 0;
	for (n = -1; size-- > 0 && (c = fgetc (f)) != EOF; )
	{
		if (n < 0 && at_line && c == name[0])
			n = 1;
		else if (n > 0 && n < length && c == name[n])
			n++;
		else if (n == length && (c == ' ' || c == '\t' || c == '"'))
		{
			fclose (f);
			return 0;
		}
		else
			n = -1;
		at_line = c == '\n';
	}
	fclose (f);
	return 1;
}

int AW_FogExactActive(void) {return fog_exact;}
float AW_FogExactDepth(void) {return fog_exact_depth;}
/* Size-scaled cut-off presets (aw_cull 3, 4): a placement whose near side
 * (centre depth less its radius) lies past this share of the draw distance is
 * left out; the size classes are those of dbg rcount 3 (radius under 32,
 * 32-128, 128-512, 512 and over). */
static const float size_cut_share[2][4]={{.50f,.75f,1,1},{.40f,.60f,.85f,1}};
float AW_SizeCutShare(int preset,float radius) {
    int k=radius<32?0:radius<128?1:radius<512?2:3;
    return preset<1 || preset>2?1:size_cut_share[preset-1][k];
}
/* A brush model pass with world box minmaxs (the box R_DrawBEntitiesOnList
 * gives the frustum test; a rotated model's is the cube of its radius):
 * AW_FAR_DRAW, AW_FAR_SKIP (nothing of it drawn) or AW_FAR_FACES plus the
 * face tests (<<4) to give AW_FarPassBegin after R_RotateBmodel. */
int AW_BrushPassFar(vec3_t origin,float radius,const float *minmaxs) {
    float eye,depth,nearest=0,farthest=0,down=0,top=0;int i,faces=0;
    if(!aw_cull.value)return AW_FAR_DRAW;
    eye=DotProduct(r_origin,far_normal);
    depth=DotProduct(origin,far_normal)-eye;
    if(size_cut && depth-radius>cut_distance*AW_SizeCutShare(size_cut,radius))return AW_FAR_SIZE;
    if(fog_exact){
        for(i=0;i<3;i++){
            nearest+=far_normal[i]*minmaxs[i+(far_normal[i]<0?3:0)];
            farthest+=far_normal[i]*minmaxs[i+(far_normal[i]<0?0:3)];
            top+=fog_down[i]*minmaxs[i+(fog_down[i]<0?0:3)];
            down+=fog_down[i]*minmaxs[i+(fog_down[i]<0?3:0)];
        }
        nearest-=eye;farthest-=eye;
        top-=DotProduct(r_origin,fog_down);down-=DotProduct(r_origin,fog_down);
        if(nearest>=fog_exact_depth && top<0)return AW_FAR_SKIP;
        if(farthest>=fog_exact_depth && down<0)faces|=1;
    }
    if(detail_step && radius>=32 && depth>cut_distance*.5f)faces|=2;
    return faces?AW_FAR_FACES|faces<<4:AW_FAR_DRAW;
}
/* After R_RotateBmodel (vpn, vright, vup and modelorg in model space): the
 * model-space planes of the face tests AW_BrushPassFar asked for. */
void AW_FarPassBegin(int result) {
    int i;float d[3];
    aw_far_faces=result>>4;
    for(i=0;i<3;i++){
        aw_far_depth[i]=aw_far_view[i]=vpn[i];
        d[i]=aw_far_down[i]=fog_down_k[0]*vpn[i]+fog_down_k[1]*vright[i]+fog_down_k[2]*vup[i];
    }
    aw_far_view[3]=DotProduct(modelorg,vpn);
    aw_far_depth[3]=aw_far_view[3]+fog_exact_depth;
    aw_far_down[3]=DotProduct(modelorg,d);
}
/* r_bsp.c, aw_cull 5/6: a front face of a far model (AW_BrushPassFar) whose
 * largest model-space extent covers fewer than this many pixels at its
 * nearest vertex is left out. */
float aw_far_detail_pixels=2;
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
