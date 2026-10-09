/* SPDX-License-Identifier: GPL-2.0-or-later
 * Photo mode (dbg photomode, alias dbg killhud): clean frames for screenshots.
 *
 * Quake mechanisms reused, no new drawing path:
 * - full-screen view: the intermission's view size 120 with no status-bar
 *   lines (SCR_CalcRefdef);
 * - the existing settings for everything drawn over the view: Quake's
 *   crosshair and r_drawviewmodel (hands, weapon, torch model), dbg hud
 *   (amiwind_show_debug: title, coordinates, FPS, console notify lines), the
 *   stat bars (aw_ui_hud), compass and gold frame;
 * - the short notices: AmiWind's own message box (AW_UISubtitle, the box of
 *   the Wait refusal), drawn in photo mode only while a notice lasts;
 * - free camera: noclip (MOVETYPE_NOCLIP + noclip_anglehack, as Host_Noclip_f).
 * Every setting it changes is saved as text on entry and restored exactly on
 * exit. Nothing is saved: game saves need MOVETYPE_WALK, and config.cfg is
 * written with the pre-photo values (Host_WriteConfiguration ends it first).
 */
#include "quakedef.h"
#include "aw_world.h"
extern int scr_copyeverything;

static cvar_t photo_nofog={"aw_photomode_nofog","1",true};
static cvar_t photo_noclip={"aw_photomode_noclip","1",true};
/* 0 (default): first-person hands, weapon and torch hidden (Quake's
 * r_drawviewmodel). The torch's eye light is not part of the model: it stays. */
static cvar_t photo_hands={"aw_photomode_hands","0",true};
/* Settings photo mode switches off on entry; restored as text on exit. */
static const char *const saved_names[]={"crosshair","aw_fog","_aw_debug_all","_aw_debug_coords",
    "aw_ui_hud","aw_compass","aw_ui_frame","r_drawviewmodel"};
#define SAVED ((int)(sizeof(saved_names)/sizeof(saved_names[0])))
#define SAVED_CROSSHAIR 0
#define SAVED_FOG 1
#define SAVED_HANDS 7
static char saved_values[SAVED][32];
static int active,placed,global_valid;
static const char *pending,*shown;static float pending_seconds;static double shown_until;
static vec3_t start_origin,start_view,start_global;
static float start_movetype;
static qboolean start_anglehack;
static char start_map[64];
static model_t *start_world;
static double start_time;

/* Three short lines: the message box shows three rows without paging. */
#define NOTICE "You are in photo mode.\nF10: console, dbg photomode off to return.\nCtrl+F fog, Ctrl+H debug HUD"
#define REMINDER "You are in photo mode. Type dbg photomode off to return to the normal HUD.\nCtrl+F: fog on/off, Ctrl+H: debug HUD (dbg hud).\n"

static edict_t *local_player(void) {
    if(!sv.active || svs.maxclients!=1 || !svs.clients || cls.state!=ca_connected || cls.signon!=SIGNONS)return NULL;
    return svs.clients[0].edict;
}
static int toggle_word(const char *s,int *on) {
    if(!Q_strcasecmp((char *)s,"on") || !Q_strcasecmp((char *)s,"true") || !strcmp(s,"1")){*on=1;return 1;}
    if(!Q_strcasecmp((char *)s,"off") || !Q_strcasecmp((char *)s,"false") || !strcmp(s,"0")){*on=0;return 1;}
    return 0;
}
static void notice(const char *text,float seconds){pending=text;pending_seconds=seconds;}
/* Gameplay only: the box's clock runs while the console is open. */
static void show(const char *text,float seconds) {
    AW_UISubtitle("",text,seconds);shown=text;shown_until=realtime+seconds;scr_copyeverything=1;
}
/* The box is drawn in photo mode only for its own notice, and for a moment
 * after it (the box slides away); never for game speech or prompts. */
int AW_PhotoNoticeShowing(void) {
    return active && shown && realtime<shown_until+1 && AW_UISubtitleIs(shown);
}
static void refresh(void){vid.recalc_refdef=true;scr_copyeverything=1;}
static int enter(void) {
    edict_t *p=local_player();cvar_t *v;int i;
    if(!p){Con_Printf("Photo mode: start the local scene first.\n");return 0;}
    for(i=0;i<SAVED;i++){
        v=Cvar_FindVar((char *)saved_names[i]);saved_values[i][0]=0;
        if(!v)continue;
        strncpy(saved_values[i],v->string,sizeof(saved_values[i])-1);saved_values[i][sizeof(saved_values[i])-1]=0;
        if((i!=SAVED_FOG || photo_nofog.value) && (i!=SAVED_HANDS || !photo_hands.value))
            Cvar_Set((char *)saved_names[i],"0");
    }
    placed=0;
    if(photo_noclip.value){
        VectorCopy(p->v.origin,start_origin);VectorCopy(cl.viewangles,start_view);
        start_movetype=p->v.movetype;start_anglehack=noclip_anglehack;
        strncpy(start_map,sv.name,sizeof(start_map)-1);start_map[sizeof(start_map)-1]=0;
        start_world=sv.worldmodel;start_time=sv.time;
        global_valid=AW_WorldToSource(sv.name,p->v.origin,start_global);
        VectorCopy(vec3_origin,p->v.velocity);
        p->v.movetype=MOVETYPE_NOCLIP;noclip_anglehack=true;placed=1;
    }
    active=1;refresh();notice(NOTICE,4);
    Con_Printf(REMINDER);
    return 1;
}
/* Put the player back where photo mode started: same map, exact pose; after a
 * region crossing, by global coordinate like dbg tp X Y. */
static void return_player(void) {
    edict_t *p=local_player();
    placed=0;
    /* A load, a new game or a scene reset already placed the player. */
    if(!p || p->v.movetype!=MOVETYPE_NOCLIP)return;
    VectorCopy(vec3_origin,p->v.velocity);
    p->v.movetype=start_movetype;noclip_anglehack=start_anglehack;
    if(!strcmp(sv.name,start_map) && sv.worldmodel==start_world && sv.time>=start_time){
        VectorCopy(start_origin,p->v.origin);
        V_StopPitchDrift();VectorCopy(start_view,cl.viewangles);
        p->v.angles[0]=start_view[0];p->v.angles[1]=start_view[1];p->v.angles[2]=0;p->v.fixangle=1;
        SV_LinkEdict(p,false);return;
    }
    if(global_valid && AW_MapTeleport(start_global))return;
    if(start_movetype!=MOVETYPE_NOCLIP && SV_TestEntityPosition(p)){
        p->v.movetype=MOVETYPE_NOCLIP;noclip_anglehack=true;
        Con_Printf("Photo mode start point unavailable; still inside solid: fly clear, then noclip, or dbg recover.\n");
    }
}
static void leave(int restore_player) {
    int i;
    if(!active)return;
    active=0;
    for(i=0;i<SAVED;i++)if(saved_values[i][0] && Cvar_FindVar((char *)saved_names[i]))
        Cvar_Set((char *)saved_names[i],saved_values[i]);
    if(shown && AW_UISubtitleIs(shown))AW_UISubtitle("","",0);
    shown=pending=NULL;refresh();
    if(placed && restore_player)return_player();
    placed=0;
}
int AW_PhotoModeActive(void) {
    /* Disconnecting or the main menu ends it; nothing to put back. */
    if(active && cls.state!=ca_connected)leave(0);
    return active;
}
int AW_PhotoModeAvailable(void){return active || local_player()!=NULL;}
int AW_PhotoModeSet(int on) {
    if(on && active){Con_Printf("Photo mode is already on.\n");return 1;}
    if(!on && !active){Con_Printf("Photo mode is off.\n");return 1;}
    if(on)return enter();
    leave(1);notice("Photo mode off",1.5f);Con_Printf("Photo mode off.\n");
    return 1;
}
/* Ends photo mode before config.cfg is written, so it keeps the player's values. */
void AW_PhotoConfigRestore(void){leave(0);}
/* Gameplay draws only: a notice issued from the console starts when it closes. */
void AW_PhotoDraw(void) {
    if(!pending || key_dest!=key_game)return;
    show(pending,pending_seconds);pending=NULL;
}
void AW_PhotoConsoleReminder(void){if(AW_PhotoModeActive())Con_Printf(REMINDER);}
/* Ctrl+F / Ctrl+H, photo mode only; outside it Ctrl and F keep their bindings. */
int AW_PhotoKey(int key) {
    int on;
    if(!AW_PhotoModeActive() || key_dest!=key_game)return 0;
    if(key=='f' || key=='F'){
        on=!Cvar_VariableValue("aw_fog");Cvar_SetValue("aw_fog",(float)on);
        show(on?"Fog on":"Fog off",1.5f);return 1;
    }
    if(key=='h' || key=='H'){
        on=!AW_DebugOverlaysEnabled();
        Cbuf_AddText(on?"amiwind_show_debug 1\n":"amiwind_show_debug 0\n");
        show(on?"Debug HUD on":"Debug HUD off",1.5f);return 1;
    }
    return 0;
}
/* The crosshair preference (saved in config.cfg; default on from default.cfg).
 * During photo mode a change applies to the value restored on exit. */
int AW_CrosshairShown(void) {
    if(active && saved_values[SAVED_CROSSHAIR][0])return Q_atof(saved_values[SAVED_CROSSHAIR])!=0;
    return Cvar_VariableValue("crosshair")!=0;
}
void AW_CrosshairSet(int on) {
    if(active && saved_values[SAVED_CROSSHAIR][0]){strcpy(saved_values[SAVED_CROSSHAIR],on?"1":"0");return;}
    Cvar_SetValue("crosshair",(float)(on!=0));scr_copyeverything=1;
}
static void photo_command(void) {
    int on=!active;
    if(Cmd_Argc()>2 || (Cmd_Argc()==2 && !toggle_word(Cmd_Argv(1),&on))){
        Con_Printf("Usage: dbg photomode [on/off, true/false or 1/0]; no argument toggles.\n");return;
    }
    AW_PhotoModeSet(on);
}
static void crosshair_command(void) {
    int on=!AW_CrosshairShown();
    if(Cmd_Argc()>2 || (Cmd_Argc()==2 && !toggle_word(Cmd_Argv(1),&on))){
        Con_Printf("Usage: dbg crosshair [on/off, true/false or 1/0]; no argument toggles.\n");return;
    }
    AW_CrosshairSet(on);
    Con_Printf("Crosshair %s%s.\n",on?"on":"off",active?" (applies when photo mode ends)":"");
}
void AW_PhotoInit(void) {
    Cvar_RegisterVariable(&photo_nofog);Cvar_RegisterVariable(&photo_noclip);Cvar_RegisterVariable(&photo_hands);
    Cmd_AddCommand("aw_photomode",photo_command);
    Cmd_AddCommand("aw_crosshair",crosshair_command);
}
