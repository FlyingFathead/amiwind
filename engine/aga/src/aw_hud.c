/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "amiwind_version.h"
#include "aw_world.h"
#include "aw_clock.h"
int sb_lines;
static cvar_t coords = {"_aw_debug_coords", "0", true};
static cvar_t overlays = {"_aw_debug_all", "0", true};
static cvar_t fps = {"_aw_debug_fps", "0", true};
static cvar_t show_compass = {"aw_compass", "0", true};
static cvar_t hud_type = {"_aw_debug_hud_type", "2", true};
extern int AW_FpsTenths(void);
/* Exterior water at source Z=0; visibility only, not water physics. */
static cvar_t sealevel = {"_aw_debug_sealevel", "1", true};
extern cvar_t scr_showram;
extern int scr_copyeverything;
int AW_DebugOverlaysEnabled(void) {return overlays.value != 0;}
int AW_DebugCoordsEnabled(void) {return overlays.value != 0 && coords.value != 0;}
int AW_SeaLevelEnabled(void) {return sealevel.value != 0;}
static int debug_toggle(cvar_t *setting,char *name) {
    char *value;
    if(Cmd_Argc()==1) {
        Con_Printf("%s %s\n", name,setting->value?"on":"off");return 0;
    }
    value=Cmd_Argv(1);
    if(Cmd_Argc()!=2 || (Q_strcasecmp(value,"true") && Q_strcasecmp(value,"false") &&
       Q_strcasecmp(value,"on") && Q_strcasecmp(value,"off") && strcmp(value,"1") && strcmp(value,"0"))) {
        Con_Printf("Usage: %s on/off, true/false, or 1/0\n",name);return 0;
    }
    Cvar_SetValue(setting->name, !Q_strcasecmp(value,"true") || !Q_strcasecmp(value,"on") || !strcmp(value,"1"));
    vid.recalc_refdef=true;
    return 1;
}
static void debug_coords(void) {debug_toggle(&coords,"amiwind_debug_coords");}
static void debug_all(void) {
    if(debug_toggle(&overlays,"amiwind_show_debug"))
        Cvar_SetValue(coords.name,overlays.value!=0);
}
static void debug_compass(void) {
    if(debug_toggle(&show_compass,"dbg compass"))scr_copyeverything=1;
}
static void debug_fps(void) {debug_toggle(&fps,"amiwind_debug_fps");}
static void debug_showfps(void) {if(Cmd_Argc()==1)Cvar_SetValue(fps.name,1);else debug_fps();}
static void debug_ram(void) {debug_toggle(&scr_showram,"amiwind_debug_showram");}
static void debug_sea(void) {debug_toggle(&sealevel,"amiwind_debug_sealevel");}
static void debug_hud_type(void) {
    if(Cmd_Argc()==1){Con_Printf("Debug HUD type %ld\n",(long)hud_type.value);return;}
    if(Cmd_Argc()!=2 || (strcmp(Cmd_Argv(1),"1") && strcmp(Cmd_Argv(1),"2"))){
        Con_Printf("Usage: dbg hud type 1/2\n");return;
    }
    Cvar_SetValue(hud_type.name,atoi(Cmd_Argv(1)));scr_copyeverything=1;
}
void Sbar_Init(void) {
    Cvar_RegisterVariable(&coords);Cvar_RegisterVariable(&overlays);
    Cvar_RegisterVariable(&sealevel);
    Cvar_RegisterVariable(&fps);
    Cvar_RegisterVariable(&hud_type);
    Cvar_RegisterVariable(&show_compass);
    Cmd_AddCommand("amiwind_debug_compass",debug_compass);
    Cmd_AddCommand("aw_debug_hud_type",debug_hud_type);
    Cmd_AddCommand("amiwind_debug_coords",debug_coords);Cmd_AddCommand("amiwind_debug_all",debug_all);
    Cmd_AddCommand("amiwind_show_debug",debug_all);
    Cmd_AddCommand("amiwind_debug_showram",debug_ram);
    Cmd_AddCommand("amiwind_debug_sealevel",debug_sea);
    Cmd_AddCommand("amiwind_debug_fps",debug_fps);Cmd_AddCommand("amiwind_debug_showfps",debug_showfps);
}
void Sbar_Changed(void) {}
static int current_region(const char **region) {
    vec3_t source;*region=NULL;
    if(cls.state!=ca_connected || !sv.active || svs.maxclients!=1 ||
       !svs.clients || !svs.clients[0].edict ||
       !AW_WorldToSource(sv.name,svs.clients[0].edict->v.origin,source))return 0;
    *region=AW_RegionNameAt(source);return 1;
}
static const char *directions[]={"N","NE","E","SE","S","SW","W","NW"};
static int compass_heading(void) {
    /* Runtime +Y is source north; engine yaw zero points east. */
    return (int)anglemod(90-cl.viewangles[YAW]+360);
}
static void coordinate_line(char *line,int y) {
    int limit=(vid.width-96)/4;
    if(limit<=0)return;
    if((int)strlen(line)>limit){line[limit]=0;if(limit>=3)memcpy(line+limit-3,"...",3);}
    AW_SmallString(vid.width-8-(int)strlen(line)*4,y,line);
}
static void compass(void) {
    char line[96];int heading,limit;const char *region=NULL;
    if(!show_compass.value || cls.state!=ca_connected || key_dest!=key_game || AW_GalleryActive())return;
    heading=compass_heading();
    current_region(&region);
    snprintf(line,sizeof(line),"%s %03ld / REGION: %s",directions[((heading+22)/45)&7],
             (long)heading,region?region:"unavailable");
    limit=(vid.width-96)/4;if(limit<0)limit=0;if(limit>95)limit=95;
    if((int)strlen(line)>limit){line[limit]=0;if(limit>=3)memcpy(line+limit-3,"...",3);}
    AW_SmallString(vid.width-8-(int)strlen(line)*4,vid.height-26,line);
    scr_copyeverything=1;
}
void Sbar_Draw(void) {
    char title[128];const char *region;int limit,width=hud_type.value==1?8:4;
    if(key_dest==key_console)return;
    AW_UIHud();
    compass();
    /* Its strip replaces the bottom HUD. Photo mode hides it like everything
     * else over the view; Ctrl+H (dbg hud) brings it back with the debug HUD.
     * Its keys keep working while hidden (AW_WaitKey). */
    if((!AW_PhotoModeActive() || AW_DebugOverlaysEnabled()) && AW_LightGalleryDraw())return;
    if(!AW_DebugOverlaysEnabled())return;
    if(current_region(&region))
        snprintf(title,sizeof(title),"AmiWind v" AMIWIND_VERSION " Vvardenfell / %s",region?region:"Region unavailable");
    else
        snprintf(title,sizeof(title),"AmiWind v" AMIWIND_VERSION " / %s",cl.levelname[0]?cl.levelname:"Location unavailable");
    limit=(vid.width-16)/width;if(limit<0)limit=0;if(limit>127)limit=127;
    if((int)strlen(title)>limit){title[limit]=0;if(limit>=3)memcpy(title+limit-3,"...",3);}
    if(width==8)Draw_String(8,8,title);else AW_SmallString(8,8,title);
    if(fps.value){
        char line[32];int n=AW_FpsTenths(),x=8;
        sprintf(line,"FPS:%ld.%ld",(long)(n/10),(long)(n%10));
        Draw_Fill(x,19,80,10,255);Draw_String(x+4,20,line);
    }
    if(AW_DebugCoordsEnabled() && cls.state==ca_connected && cl.viewentity>0 && cl.viewentity<MAX_EDICTS) {
        char line[80],clock[16];vec_t *p=cl_entities[cl.viewentity].origin;vec3_t global;
        int year,month,day,hour,minute,heading;
        /* Report the simulated player in local play, before view interpolation. */
        if(sv.active && svs.maxclients==1 && svs.clients && svs.clients[0].edict)
            p=svs.clients[0].edict->v.origin;
        /* Two compact console-font rows beside the health/magicka/fatigue bars.
         * Photo mode has no bars and a full-screen view: the strip spans the
         * whole width (PHOTO-DEBUG-STRIP-33). */
        if(AW_PhotoModeActive())Draw_Fill(0,vid.height-18,vid.width,18,255);
        else Draw_Fill(88,vid.height-18,vid.width-88,18,255);
        if(sv.active && AW_WorldToSource(sv.name,p,global))
            snprintf(line,sizeof(line),"GLOBAL XYZ: %ld %ld %ld",(long)global[0],(long)global[1],(long)global[2]);
        else strcpy(line,"GLOBAL XYZ: unavailable (interior)");
        if(hud_type.value!=1){
            strcpy(clock," TIME --:--");
            if(AW_ClockEnsure()){
                AW_ClockDate(&year,&month,&day,&hour,&minute);
                snprintf(clock,sizeof(clock)," TIME %02d:%02d",hour,minute);
            }
            strncat(line,clock,sizeof(line)-strlen(line)-1);
        }
        coordinate_line(line,vid.height-16);
        if(hud_type.value==1)
            snprintf(line,sizeof(line),"LOCAL XYZ: %ld %ld %ld DEG:%ld P:%ld",(long)p[0],(long)p[1],(long)p[2],
                (long)anglemod(cl.viewangles[YAW]),(long)cl.viewangles[PITCH]);
        else {
            heading=compass_heading();
            snprintf(line,sizeof(line),"LOCAL XYZ: %ld %ld %ld %s %03ld P:%ld",(long)p[0],(long)p[1],(long)p[2],
                directions[((heading+22)/45)&7],(long)heading,(long)cl.viewangles[PITCH]);
        }
        coordinate_line(line,vid.height-8);
        /* This strip is outside scr_vrect; the normal viewport-only update
         * would leave its old pixels on the Amiga screen. */
        scr_copyeverything=1;
    } else if(!AW_PhotoModeActive())AW_SmallString(92,vid.height-8,"WASD / F10 console");
}
void Sbar_IntermissionOverlay(void) {}
void Sbar_FinaleOverlay(void) {}
void Sbar_DeathmatchOverlay(void) {}
