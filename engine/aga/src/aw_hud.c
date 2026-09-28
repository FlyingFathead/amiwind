/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "amiwind_version.h"
int sb_lines;
static cvar_t coords = {"_aw_debug_coords", "0", true};
static cvar_t overlays = {"_aw_debug_all", "0", true};
static cvar_t fps = {"_aw_debug_fps", "0", true};
extern int AW_FpsTenths(void);
/* Temporary demo water at Z=0; visibility only, not water physics. */
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
static void debug_fps(void) {debug_toggle(&fps,"amiwind_debug_fps");}
static void debug_showfps(void) {if(Cmd_Argc()==1)Cvar_SetValue(fps.name,1);else debug_fps();}
static void debug_ram(void) {debug_toggle(&scr_showram,"amiwind_debug_showram");}
static void debug_sea(void) {debug_toggle(&sealevel,"amiwind_debug_sealevel");}
void Sbar_Init(void) {
    Cvar_RegisterVariable(&coords);Cvar_RegisterVariable(&overlays);
    Cvar_RegisterVariable(&sealevel);
    Cvar_RegisterVariable(&fps);
    Cmd_AddCommand("amiwind_debug_coords",debug_coords);Cmd_AddCommand("amiwind_debug_all",debug_all);
    Cmd_AddCommand("amiwind_show_debug",debug_all);
    Cmd_AddCommand("amiwind_debug_showram",debug_ram);
    Cmd_AddCommand("amiwind_debug_sealevel",debug_sea);
    Cmd_AddCommand("amiwind_debug_fps",debug_fps);Cmd_AddCommand("amiwind_debug_showfps",debug_showfps);
}
void Sbar_Changed(void) {}
void Sbar_Draw(void) {
    if(key_dest==key_console)return;
    AW_UIHud();
    if(!AW_DebugOverlaysEnabled())return;
    Draw_String(8,8,!strcmp(sv.name,"census")?"AMIWIND v" AMIWIND_VERSION " / CENSUS OFFICE":AW_Interior()?"AMIWIND v" AMIWIND_VERSION " / PRISON SHIP":"AMIWIND v" AMIWIND_VERSION " / SEYDA NEEN");
    if(fps.value){
        char line[16];int n=AW_FpsTenths(),x=8;
        sprintf(line,"FPS:%ld.%ld",(long)(n/10),(long)(n%10));
        Draw_Fill(x,19,80,10,255);Draw_String(x+4,20,line);
    }
    if(AW_DebugCoordsEnabled() && cls.state==ca_connected && cl.viewentity>0 && cl.viewentity<MAX_EDICTS) {
        char line[64];vec_t *p=cl_entities[cl.viewentity].origin;int x;
        /* Report the simulated player in local play, before view interpolation. */
        if(sv.active && svs.maxclients==1 && svs.clients && svs.clients[0].edict)
            p=svs.clients[0].edict->v.origin;
        sprintf(line,"XYZ:%ld %ld %ld DEG:%ld P:%ld",(long)p[0],(long)p[1],(long)p[2],
            (long)anglemod(cl.viewangles[YAW]),(long)cl.viewangles[PITCH]);
        x=vid.width-8-(int)strlen(line)*8;if(x<0)x=0;
        Draw_Fill(0,vid.height-12,vid.width,12,255);
        Draw_String(x,vid.height-10,line);
        /* This strip is outside scr_vrect; the normal viewport-only update
         * would leave its old pixels on the Amiga screen. */
        scr_copyeverything=1;
    } else Draw_String(92,vid.height-12,"WASD / F10 console");
}
void Sbar_IntermissionOverlay(void) {}
void Sbar_FinaleOverlay(void) {}
void Sbar_DeathmatchOverlay(void) {}
