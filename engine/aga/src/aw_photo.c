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
/* 1 (default): photo mode's own notice box and hints; 0: none of them (saved; dbg photomode ui; the Halloween scene
 * turns them off while it runs). */
static cvar_t photo_ui={"aw_photomode_ui","1",true};
/* Settings photo mode switches off on entry; restored as text on exit. */
static const char *const saved_names[]={"crosshair","aw_fog","_aw_debug_all","_aw_debug_coords",
    "aw_ui_hud","aw_compass","aw_ui_frame","r_drawviewmodel","aw_noclipwobble"};
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
static void notice(const char *text,float seconds){if(!photo_ui.value)return;pending=text;pending_seconds=seconds;}
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
    if(photo_ui.value)Con_Printf(REMINDER);
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
/* Photo mode without its notice box (dbg halloween: nothing but the greeting in the middle of the screen). */
int AW_PhotoModeSetQuiet(int on) {
    if(on){int r=active?1:enter();pending=NULL;return r;}
    leave(1);
    return 1;
}
/* Ends photo mode before config.cfg is written, so it keeps the player's values. */
void AW_PhotoConfigRestore(void){leave(0);}
/* Gameplay draws only: a notice issued from the console starts when it closes. */
void AW_PhotoDraw(void) {
    if(!pending || key_dest!=key_game)return;
    show(pending,pending_seconds);pending=NULL;
}
void AW_PhotoConsoleReminder(void){if(AW_PhotoModeActive() && photo_ui.value)Con_Printf(REMINDER);}
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
/* Crosshair colour and shape (Options > Prefs, dbg crosshair colour / shape; saved in
 * config.cfg like the crosshair itself). Warm white + Cross is the look of every release
 * before v0.0.48: Quake's '+' of the console font in its ink, palette index 254
 * (238,221,170 in the generated palette), drawn unchanged. The other colours are the
 * palette entries nearest to their targets, resolved by view.c; yellow, green and blue
 * come from the 225..253 bank (the original status-bar colours). The palette has no pure
 * white; warm white (index 254), its brightest entry, is the default and stays as it is,
 * so no palette is rebuilt (maintainer, 22 October 2026; UI-PALETTE-NO-WHITE-48). Red
 * stays the pick mode's colour (dbg companion pick). */
static cvar_t crosshair_colour={"aw_crosshair_colour","0",true};
static cvar_t crosshair_shape={"aw_crosshair_shape","0",true};
static const char *const colour_names[]={"Warm white","Yellow","Green","Blue"};
static const unsigned char colour_rgb[][3]={{238,221,170},{255,186,0},{110,180,60},{150,180,230}};
static const char *const shape_names[]={"Cross","Open cross","Small cross","Dot"};
#define CROSSHAIR_COLOURS ((int)(sizeof(colour_names)/sizeof(colour_names[0])))
#define CROSSHAIR_SHAPES ((int)(sizeof(shape_names)/sizeof(shape_names[0])))
int AW_CrosshairStyleCount(int shape){return shape?CROSSHAIR_SHAPES:CROSSHAIR_COLOURS;}
int AW_CrosshairStyle(int shape) {
    float v=shape?crosshair_shape.value:crosshair_colour.value;
    return v>=0 && v<AW_CrosshairStyleCount(shape)?(int)v:0;
}
const char *AW_CrosshairStyleName(int shape,int value) {
    if(value<0 || value>=AW_CrosshairStyleCount(shape))value=0;
    return shape?shape_names[value]:colour_names[value];
}
/* The target RGB of a crosshair colour; view.c picks the nearest palette entry. */
const unsigned char *AW_CrosshairColourRGB(int value){return colour_rgb[value>=0 && value<CROSSHAIR_COLOURS?value:0];}
void AW_CrosshairStyleSet(int shape,int value) {
    int n=AW_CrosshairStyleCount(shape);
    value=((value%n)+n)%n;
    Cvar_SetValue(shape?crosshair_shape.name:crosshair_colour.name,(float)value);scr_copyeverything=1;
}
/* A name (any case; a unique start is enough) or its number; -1 when unknown. */
static int style_word(int shape,const char *s) {
    int i,n=AW_CrosshairStyleCount(shape),found=-1,length=(int)strlen(s);
    if(s[0]>='0' && s[0]<='9' && !s[1])return s[0]-'0'<n?s[0]-'0':-1;
    for(i=0;i<n && length;i++)if(!Q_strncasecmp((char *)s,(char *)AW_CrosshairStyleName(shape,i),length)){
        if(!AW_CrosshairStyleName(shape,i)[length])return i;
        found=found==-1?i:-2;
    }
    return found>=0?found:-1;
}
static void style_list(int shape,char *out) {
    int i;out[0]=0;
    for(i=0;i<AW_CrosshairStyleCount(shape);i++){if(i)strcat(out,", ");strcat(out,AW_CrosshairStyleName(shape,i));}
}
static int style_kind(const char *s) {
    if(!Q_strcasecmp((char *)s,"colour") || !Q_strcasecmp((char *)s,"color"))return 0;
    if(!Q_strcasecmp((char *)s,"shape"))return 1;
    return -1;
}
static void crosshair_command(void) {
    int on=!AW_CrosshairShown(),shape=Cmd_Argc()>=2?style_kind(Cmd_Argv(1)):-1,value;char list[96];
    if(shape>=0){
        style_list(shape,list);
        if(Cmd_Argc()==2){Con_Printf("Crosshair %s: %s (%s).\n",shape?"shape":"colour",AW_CrosshairStyleName(shape,AW_CrosshairStyle(shape)),list);return;}
        value=Cmd_Argc()==3?style_word(shape,Cmd_Argv(2)):-1;
        if(value<0){Con_Printf("Usage: dbg crosshair %s [%s, or 0 to %ld].\n",shape?"shape":"colour",list,(long)(AW_CrosshairStyleCount(shape)-1));return;}
        AW_CrosshairStyleSet(shape,value);
        Con_Printf("Crosshair %s: %s.\n",shape?"shape":"colour",AW_CrosshairStyleName(shape,value));return;
    }
    if(Cmd_Argc()==2 && !Q_strcasecmp(Cmd_Argv(1),"style")){
        Con_Printf("Crosshair %s, colour %s, shape %s.\n",AW_CrosshairShown()?"on":"off",
            AW_CrosshairStyleName(0,AW_CrosshairStyle(0)),AW_CrosshairStyleName(1,AW_CrosshairStyle(1)));return;
    }
    if(Cmd_Argc()>2 || (Cmd_Argc()==2 && !toggle_word(Cmd_Argv(1),&on))){
        Con_Printf("Usage: dbg crosshair [on/off, true/false or 1/0]; no argument toggles.\n"
                   "dbg crosshair colour [name], dbg crosshair shape [name], dbg crosshair style.\n");return;
    }
    AW_CrosshairSet(on);
    Con_Printf("Crosshair %s%s.\n",on?"on":"off",active?" (applies when photo mode ends)":"");
}
/* Mouse sensitivity: Quake's saved sensitivity cvar (cl_main.c; default 3, the value of
 * every release so far). Options > Controls steps it from 0.5 to 10 by 0.5 (Shift: 0.1);
 * dbg sensitivity takes 0.1 to 20. Kept in tenths here: no float printing. */
int AW_SensitivityTenths(void) {
    float v=Cvar_VariableValue("sensitivity");
    if(!(v>0))return 0;
    if(v>1000)return 10000;
    return (int)(v*10+.5f);
}
void AW_SensitivitySetTenths(int tenths) {
    if(tenths<AW_SENSITIVITY_CONSOLE_MIN)tenths=AW_SENSITIVITY_CONSOLE_MIN;
    if(tenths>AW_SENSITIVITY_CONSOLE_MAX)tenths=AW_SENSITIVITY_CONSOLE_MAX;
    Cvar_SetValue("sensitivity",tenths/10.0f);
}
/* "2.5" -> 25 tenths, "3" -> 30; -1 for anything else (one decimal at most). */
static int tenths_word(const char *s) {
    int whole=0,digits=0,tenth=0;
    while(*s>='0' && *s<='9'){if(++digits>4)return -1;whole=whole*10+*s++-'0';}
    if(*s=='.'){
        s++;
        if(*s>='0' && *s<='9'){tenth=*s++-'0';digits++;}
    }
    if(*s || !digits)return -1;
    return whole*10+tenth;
}
static void sensitivity_command(void) {
    int t=AW_SensitivityTenths(),n;
    if(Cmd_Argc()==1){Con_Printf("Mouse sensitivity: %ld.%ld (default 3.0; also Options > Controls).\n",(long)(t/10),(long)(t%10));return;}
    n=Cmd_Argc()==2?tenths_word(Cmd_Argv(1)):-1;
    if(n<AW_SENSITIVITY_CONSOLE_MIN || n>AW_SENSITIVITY_CONSOLE_MAX){
        Con_Printf("Usage: dbg sensitivity [0.1 to 20]; no argument prints it (default 3).\n");return;
    }
    AW_SensitivitySetTenths(n);
    Con_Printf("Mouse sensitivity: %ld.%ld.\n",(long)(n/10),(long)(n%10));
}
void AW_PhotoInit(void) {
    Cvar_RegisterVariable(&photo_nofog);Cvar_RegisterVariable(&photo_noclip);Cvar_RegisterVariable(&photo_hands);
    Cvar_RegisterVariable(&photo_ui);
    Cvar_RegisterVariable(&crosshair_colour);Cvar_RegisterVariable(&crosshair_shape);
    Cmd_AddCommand("aw_photomode",photo_command);
    Cmd_AddCommand("aw_crosshair",crosshair_command);
    Cmd_AddCommand("aw_sensitivity",sensitivity_command);
}
