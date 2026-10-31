/* SPDX-License-Identifier: GPL-2.0-or-later
 * Local menu layout. Original fonts/artwork are private converted inputs.
 */
#include "quakedef.h"
#include "aw_links.h"
#include "aw_save.h"
#include "aw_maps.h"
#include "aw_region.h"
#include "amiwind_version.h"
#include "aw_miniwind.h"
extern qboolean keydown[256];
extern int scr_copyeverything;
extern int AW_DrawDistance(void);
extern char *Key_KeynumToString(int keynum);
extern void AW_SetDrawDistance(int value);
int m_activenet,m_state,m_return_state;
qboolean m_return_onerror;
char m_return_reason[32];
static int frontend,selection,confirming,confirmation_return;
static int mouse_x=160,mouse_y=63,mouse_visible;
static int graphics_top,scroll_drag;
static int audio_drag,sens_drag;
/* Options > Video > Fog distance slider (Morrowind style): drag, arrows, or type. */
#define FOG_MIN 100
#define FOG_MAX 1500
#define FOG_X 60
#define FOG_W 200
#define FOG_Y 104
extern cvar_t aw_drawdistance;
static int fog_slider,fog_drag,fog_before,fog_typing;static char fog_typed[6];
static int fog_value(void){int v=(int)aw_drawdistance.value;return v<FOG_MIN?FOG_MIN:v>FOG_MAX?FOG_MAX:v;}
static void fog_pointer(void){fog_typing=0;AW_SetDrawDistance(FOG_MIN+((mouse_x-FOG_X)*(FOG_MAX-FOG_MIN)+FOG_W/2)/FOG_W);}
static void fog_close(int keep){
    if(!keep)AW_SetDrawDistance(fog_before);
    else if(fog_typing && fog_typed[0])AW_SetDrawDistance(atoi(fog_typed));
    fog_slider=fog_drag=fog_typing=0;mouse_visible=0;
}
static void fog_key(int key){
    int n=(int)strlen(fog_typed);
    if(key==K_ESCAPE){fog_close(0);return;}
    if(key==K_ENTER){fog_close(1);return;}
    if(key>='0' && key<='9'){if(!fog_typing){fog_typing=1;n=0;}if(n<4){fog_typed[n]=(char)key;fog_typed[n+1]=0;}return;}
    if(key==K_BACKSPACE){if(fog_typing && n)fog_typed[n-1]=0;return;}
    if(key==K_LEFTARROW || key==K_RIGHTARROW){fog_typing=0;AW_SetDrawDistance(fog_value()+(key==K_LEFTARROW?-1:1)*(keydown[K_SHIFT]?1:10));}
    if(key==K_HOME || key==K_END){fog_typing=0;AW_SetDrawDistance(key==K_HOME?FOG_MIN:FOG_MAX);}
    if(key==K_MOUSE1){
        if(mouse_x>=FOG_X-6 && mouse_x<=FOG_X+FOG_W+6 && mouse_y>=FOG_Y-10 && mouse_y<=FOG_Y+14){fog_drag=1;fog_pointer();}
        else if(mouse_x>=122 && mouse_x<198 && mouse_y>=150 && mouse_y<175)fog_close(1);
    }
}
static int scene_picker,scene_available[AW_MAP_COUNT],scene_top,graphics,intro_available;
static keydest_t picker_return;
static int colours[4],ready;
static const char *front_items[]={"New game","Load game","Options","Exit game"};
static const char *items[]={"Return to game","New game","Save game","Load game","Options","Main menu"};
#define ROW_Y 54
#define ROW_H 19

/* Options: one full-screen panel (maintainer 2026-10-22: categories like the original
 * game, framed like its menus, edge to edge with nothing of the 3D view behind it).
 * The four pages are the original's own (Morrowind.exe MenuPrefs / MenuAudio /
 * MenuCtrls / MenuVideo; GMSTs sPrefs, sAudio, sControls, sVideo) in the order of
 * OpenMW's settings window:
 *   [ Prefs ][ Audio ][ Controls ][ Video ]    tab row, each tab framed
 *   +--------------------------------------+
 *   | the page's settings, 7 rows, scroll  |   one framed group
 *   +--------------------------------------+
 *   help line                       [ Back ]
 * Focus is on the tab row, the page's rows or Back. Up/Down move between them (the
 * row list stops at its ends: Up from the first row reaches the tabs, Down from the
 * last reaches Back); Left/Right switch pages on the tab row and change values on a
 * row; Enter/click acts; Esc returns to the menu. The world is not drawn behind it
 * (aw_menu_fullscreen, aw_ui.c AW_ModalWorldHidden). */
enum {TAB_PREFS,TAB_AUDIO,TAB_CONTROLS,TAB_VIDEO,TABS};
static const char *const tab_names[TABS]={"Prefs","Audio","Controls","Video"};
enum {FOCUS_TABS,FOCUS_ROWS,FOCUS_BACK};
static int tab,focus;
#define TAB_X 8
#define TAB_STEP 76
#define TAB_W 72
#define TAB_Y 6
#define TAB_H 22
#define GROUP_X 8
#define GROUP_Y 30
#define GROUP_W 304
#define GROUP_H 144
#define LIST_X 14
#define LIST_Y 36
#define LIST_W 280
#define VISIBLE 7
#define SCROLL_X 296
#define BACK_X 232
#define BACK_Y 176
#define BACK_W 80
#define BACK_H 20
/* Prefs and Video rows (Prefs: the HUD and gameplay; Video: view, loading, memory). */
enum {ROW_CROSSHAIR,ROW_COLOUR,ROW_SHAPE,ROW_FRAME,ROW_FONT,ROW_VOICE,ROW_DIALOGUE,ROW_AIMED,ROW_NPC,ROW_OBJECTS,
    ROW_AUTOSAVE,ROW_FOG,ROW_RESET,ROW_FAR,ROW_PHOTO,ROW_AREA,ROW_METHOD,ROW_BUFFER,ROW_MEMORY,ROW_GRAPHICS};
static const unsigned char prefs_rows[]={ROW_CROSSHAIR,ROW_COLOUR,ROW_SHAPE,ROW_FRAME,ROW_FONT,ROW_VOICE,ROW_DIALOGUE,
    ROW_AIMED,ROW_NPC,ROW_OBJECTS,ROW_AUTOSAVE};
static const unsigned char video_rows[]={ROW_FOG,ROW_RESET,ROW_FAR,ROW_PHOTO,ROW_AREA,ROW_METHOD,ROW_BUFFER,ROW_MEMORY
#if defined(AMIWIND_DEBUG_LUMA) && AMIWIND_DEBUG_LUMA
    ,ROW_GRAPHICS
#endif
};
#define PREFS_ROWS ((int)sizeof(prefs_rows))
#define VIDEO_ROWS ((int)sizeof(video_rows))
#if defined(AMIWIND_DEBUG_LUMA) && AMIWIND_DEBUG_LUMA
static int brightness_options,brightness_drag;
extern int R_BrightnessStep(int outside);
extern void R_BrightnessSetStep(int outside,int value);
#define BRIGHTNESS_X 60
#define BRIGHTNESS_W 200
static int brightness_active(void){return brightness_options;}
static void brightness_reset(void){brightness_options=brightness_drag=0;}
static void brightness_back(void){brightness_reset();tab=TAB_VIDEO;focus=FOCUS_ROWS;selection=VIDEO_ROWS-1;mouse_visible=0;}
static void brightness_pointer(void){R_BrightnessSetStep(brightness_drag-1,10+((mouse_x-BRIGHTNESS_X)*5+BRIGHTNESS_W/2)/BRIGHTNESS_W);}
#else
#define brightness_active() 0
#define brightness_reset() ((void)0)
#endif
/* Options > Audio: four sliders in the page's group. */
#define AUDIO_Y 36
#define AUDIO_H 30
#define AUDIO_X 134
#define AUDIO_W 118
static cvar_t *audio_levels[]={&volume,&bgmvolume,&effectsvolume,&dialoguevolume};
static int audio_percent(int row){
    float value=audio_levels[row]->value;
    if(!(value>=0))return 0;
    if(value>=1)return 100;
    return (int)(value*100+.5f);
}
static void audio_set(int row,int percent){
    if(percent<0)percent=0;
    if(percent>100)percent=100;
    if(audio_levels[row]->value!=percent*.01f)Cvar_SetValue(audio_levels[row]->name,percent*.01f);
}
static void audio_pointer(int row){audio_set(row,((mouse_x-AUDIO_X)*100+AUDIO_W/2)/AUDIO_W);}
/* Options > Controls > Mouse sensitivity: Quake's saved sensitivity (default 3.0, unchanged),
 * 0.5 to 10 in steps of 0.5 (Shift: 0.1); arrows, Home/End, or drag the rail. Invert Y axis:
 * Quake's own invert, the sign of the saved m_pitch (the original's "Invert Y Axis", sMouseFlip). */
#define SENS_X 170
#define SENS_W 76
static int sens_clamp(int t){return t<AW_SENSITIVITY_MENU_MIN?AW_SENSITIVITY_MENU_MIN:t>AW_SENSITIVITY_MENU_MAX?AW_SENSITIVITY_MENU_MAX:t;}
static void sens_step(int direction){
    int t=AW_SensitivityTenths();
    if(keydown[K_SHIFT])t+=direction;
    else t=direction>0?(t/5+1)*5:((t+4)/5-1)*5;
    AW_SensitivitySetTenths(sens_clamp(t));
}
static void sens_pointer(void){
    int range=AW_SENSITIVITY_MENU_MAX-AW_SENSITIVITY_MENU_MIN,t;
    if(mouse_x<=SENS_X)t=AW_SENSITIVITY_MENU_MIN;
    else if(mouse_x>=SENS_X+SENS_W)t=AW_SENSITIVITY_MENU_MAX;
    else t=AW_SENSITIVITY_MENU_MIN+((mouse_x-SENS_X)*range+SENS_W/2)/SENS_W;
    AW_SensitivitySetTenths(sens_clamp((t+2)/5*5));
}
static int invert_on(void){return Cvar_VariableValue("m_pitch")<0;}
static void invert_toggle(void){Cvar_SetValue("m_pitch",-Cvar_VariableValue("m_pitch"));}
/* Options > Controls edits the same bindings as bind/unbind and keymaps.cfg.
 * Each action shows up to two keys; a third key replaces both.
 *
 * Adding or activating an action (e.g. a planned row below):
 *  1. Set its console command here (a "+name" button or a plain command).
 *     A NULL command is a planned action: greyed, skipped by the cursor and
 *     never bound; planned_keys is only display text for the intended keys.
 *  2. Add its default binding to config/keymaps.cfg (new installs and
 *     "Reset to defaults").
 *  3. If existing players should get it too, add an "only if unbound" line to
 *     AW_ControlsMigrate() in keys.c; saved keymaps.cfg files are not rewritten.
 *  4. Update docs/KEYMAPS.md.
 * Keys handled before the menu (F1-F12, the console keys) cannot be captured
 * here; bind those with the console. */
typedef struct {const char *name,*command,*planned_keys;} control_t;
static const control_t controls[]={
    {"Forward","+forward"},{"Back","+back"},{"Strafe left","+moveleft"},{"Strafe right","+moveright"},
    {"Turn left","+left"},{"Turn right","+right"},{"Jump","+jump"},{"Run","+speed"},
    {"Use","+aw_use"},{"Attack","+attack"},{"Block","+aw_alt"},{"Hands","impulse 202"},{"Torch","aw_torch"},
    {"Map","aw_worldmap"},{"Journal","aw_journal"},{"Wait","aw_wait"},
    {"Quick save","aw_quicksave"},{"Quick load","aw_quickload"},
    {"Inventory","aw_inventory"},{"Stats","aw_stats"},{"Magic","aw_magicmenu"},{"Quick keys",NULL,"1-9"},{"Ready magic",NULL,"R"},{"Cast spell",NULL,NULL}};
#define CONTROL_ACTIONS ((int)(sizeof(controls)/sizeof(controls[0])))
/* The Controls page: the mouse rows, the actions, then the combat options (docs/COMBAT.md;
 * saved with the game config):
 * Combat style: AmiWind (aw_combat_miss 1, AmiWind extension: a failed roll shows
 * the defender's dodge or block) / Original Morrowind (0: the swish);
 * Dice rolls: On (aw_combat_dice 1, the original rolls) / Off (no dice, extension);
 * Blocking: Hold to block (aw_combat_block 1, AmiWind extension: the block button raises the
 * shield, the original formula decides each blow) / Automatic (0: the original). */
#define CONTROL_SENS 0
#define CONTROL_INVERT 1
#define CONTROL_FIRST 2
#define CONTROL_STYLE (CONTROL_FIRST+CONTROL_ACTIONS)
#define CONTROL_DICE (CONTROL_STYLE+1)
#define CONTROL_BLOCK (CONTROL_STYLE+2)
#define CONTROL_RESET (CONTROL_STYLE+3)
#define CONTROL_ROWS (CONTROL_RESET+1)
#define CONTROL_ACTION(row) ((row)>=CONTROL_FIRST && (row)<CONTROL_STYLE)
#define CONTROL_COMBAT(row) ((row)==CONTROL_STYLE || (row)==CONTROL_DICE || (row)==CONTROL_BLOCK)
static void combat_toggle(int row){
    if(row==CONTROL_STYLE)Cvar_SetValue("aw_combat_miss",Cvar_VariableValue("aw_combat_miss")?0:1);
    else if(row==CONTROL_DICE)Cvar_SetValue("aw_combat_dice",Cvar_VariableValue("aw_combat_dice")?0:1);
    else if(row==CONTROL_BLOCK)Cvar_SetValue("aw_combat_block",Cvar_VariableValue("aw_combat_block")?0:1);
}
static void combat_line(int row,char *line){
    if(row==CONTROL_STYLE){
        strcpy(line,Cvar_VariableValue("aw_combat_miss")?"Combat style: AmiWind":"Combat style: Original Morrowind");
        if(AW_UIWidth(line)>LIST_W-4)strcpy(line,Cvar_VariableValue("aw_combat_miss")?"Combat: AmiWind":"Combat: Original Morrowind");
    }else if(row==CONTROL_BLOCK)strcpy(line,Cvar_VariableValue("aw_combat_block")?"Blocking: Hold to block":"Blocking: Automatic");
    else strcpy(line,Cvar_VariableValue("aw_combat_dice")?"Dice rolls: On":"Dice rolls: Off");
}
static int controls_capture;
static int control_ready(int row){return !CONTROL_ACTION(row) || controls[row-CONTROL_FIRST].command!=NULL;}
static int control_keys(int action,int *keys){
    int key,n=0;
    if(!controls[action].command)return 0;
    for(key=0;key<256 && n<2;key++)
        if(keybindings[key] && !strcmp(keybindings[key],controls[action].command))keys[n++]=key;
    return n;
}
static void key_label(int key,char *out){
    const char *name;int i;
    if(key==K_UPARROW)name="Up";else if(key==K_DOWNARROW)name="Down";
    else if(key==K_LEFTARROW)name="Left";else if(key==K_RIGHTARROW)name="Right";
    else name=Key_KeynumToString(key);
    for(i=0;name[i] && i<15;i++){
        out[i]=name[i];
        if(i && out[i]>='A' && out[i]<='Z')out[i]+='a'-'A';
        if(!i && out[i]>='a' && out[i]<='z')out[i]-='a'-'A';
    }
    out[i]=0;
}
static void control_line(int action,char *line){
    int keys[2],n=control_keys(action,keys),i;char name[16];
    sprintf(line,"%s:",controls[action].name);
    if(!controls[action].command){
        if(controls[action].planned_keys){strcat(line," ");strcat(line,controls[action].planned_keys);}
        strcat(line," (planned)");return;
    }
    if(controls_capture && selection==action+CONTROL_FIRST){strcat(line," ?");return;}
    if(!n)strcat(line," -");
    for(i=0;i<n;i++){key_label(keys[i],name);strcat(line,i?", ":" ");strcat(line,name);}
}
static void control_clear(int action){int keys[2],n=control_keys(action,keys),i;for(i=0;i<n;i++)Key_SetBinding(keys[i],"");}
static void control_capture(int key){
    int keys[2],n,action=selection-CONTROL_FIRST;
    controls_capture=0;
    if(key==K_ESCAPE)return;
    if(key==K_BACKSPACE || key==K_DEL){control_clear(action);return;}
    if(key>='A' && key<='Z')key+='a'-'A';
    if(!controls[action].command)return;
    if(keybindings[key] && !strcmp(keybindings[key],controls[action].command))return;
    n=control_keys(action,keys);
    if(n>=2)control_clear(action);
    Key_SetBinding(key,(char *)controls[action].command);
}
/* The brightness panel stops at its ends so the selection never jumps back across it;
 * the Options rows stop the same way (rows_step). This also applies to wheel/W/S input
 * normalized below. */
#if defined(AMIWIND_DEBUG_LUMA) && AMIWIND_DEBUG_LUMA
static void option_step(int key,int rows){
    if(key==K_UPARROW){if(selection>0)selection--;}
    else if(selection<rows-1)selection++;
}
#endif
/* Options > Video > Extra RAM: aw_autoram (chim_world.c; saved in config.cfg). Automatic:
 * free Fast RAM beyond a margin becomes CHIM cache at the next start; Off: the
 * standard memory always. Takes effect at the next start. */
static void memory_toggle(void){Cvar_SetValue("aw_autoram",Cvar_VariableValue("aw_autoram")?0:1);}
/* Options > Video > Far detail: the far test (aw_cull, aw_fog.c; saved in config.cfg).
 * Full draws everything to the fog; the others leave out distant models
 * (docs/performance/FAR-TEST.md). Other aw_cull values (console) read Custom. */
static const int far_values[4]={1,3,4,6};
static const char *const far_names[4]={"Full","Light","Strong","Strong + small faces"};
/* The far test is aw_cull's low bits; the fog rule and whole-structure switches
 * above them (quakedef.h AW_CULL_*) stay as they are. */
static int far_index(void){int i,v=(int)Cvar_VariableValue("aw_cull")&AW_CULL_TEST;for(i=0;i<4;i++)if(far_values[i]==v)return i;return -1;}
static void far_step(int direction){int i=far_index();i=i<0?0:(i+direction+4)%4;Cvar_SetValue("aw_cull",far_values[i]|((int)Cvar_VariableValue("aw_cull")&~AW_CULL_TEST));}
static int front_height(void){int size=AW_UIFontSize();return size>=16?18:16;}
static int front_top(void){return 192-4*front_height();}
static int front_width(void){int i,w=96,n;for(i=0;i<4;i++){n=AW_UIWidth(front_items[i])+16;if(n>w)w=n;}return w;}
static void font_step(int direction){
    int sizes[4]={0,12,14,16},i,current=AW_UIFontSize();
    for(i=0;i<4;i++)if(sizes[i]==current)break;
    AW_UISetFontSize(sizes[(i+direction+4)%4]);
}
static int inside(int x,int y,int w,int h){return mouse_x>=x && mouse_x<x+w && mouse_y>=y && mouse_y<y+h;}
static int enabled(int row){return row==3 || (row==2 && AW_SaveAllowed()) || row==0 || (row==1 && intro_available) || row==4 || row==5;}
int AW_MenuFrontEnd(void){return frontend && !graphics && !confirming && key_dest==key_menu;}
/* Photo mode is offered from the pause menu's Options, not the title screen. */
static int photo_ready(void){return !frontend && AW_PhotoModeAvailable();}

/* ---- Options pages ---- */
static void close_menu(void);
static int tab_rows(int t){return t==TAB_PREFS?PREFS_ROWS:t==TAB_AUDIO?4:t==TAB_CONTROLS?CONTROL_ROWS:VIDEO_ROWS;}
static int row_id(int row){return tab==TAB_PREFS?prefs_rows[row]:video_rows[row];}
static int row_active(int row){
    if(tab==TAB_CONTROLS)return control_ready(row);
    if(tab==TAB_VIDEO && row_id(row)==ROW_BUFFER)return AW_CellChangeMethod()==2;
    if(tab==TAB_VIDEO && row_id(row)==ROW_PHOTO)return photo_ready();
    return 1;
}
static void keep_visible(void){
    if(selection<graphics_top)graphics_top=selection;
    if(selection>=graphics_top+VISIBLE)graphics_top=selection-VISIBLE+1;
}
static void set_tab(int t){
    tab=(t+TABS)%TABS;selection=graphics_top=0;audio_drag=sens_drag=controls_capture=0;
}
static void options_open(void){graphics=1;focus=FOCUS_TABS;selection=graphics_top=0;mouse_x=160;mouse_y=100;}
static void options_close(void){
    brightness_reset();
    graphics=fog_slider=audio_drag=sens_drag=controls_capture=scroll_drag=0;selection=frontend?2:4;mouse_visible=0;
}
static int fullscreen(void){return key_dest==key_menu && graphics && !AW_SaveMenuActive();}
/* Up/Down on the page's rows: planned controls are skipped; past the ends the
 * focus moves to the tab row (up) or Back (down) and stays there. */
static void rows_step(int key){
    int row=selection,n=tab_rows(tab);
    if(key==K_UPARROW){
        do row--;while(row>=0 && !control_ready(row) && tab==TAB_CONTROLS);
        if(row<0){focus=FOCUS_TABS;return;}
    }else{
        do row++;while(row<n && !control_ready(row) && tab==TAB_CONTROLS);
        if(row>=n){focus=FOCUS_BACK;return;}
    }
    selection=row;keep_visible();
}
static void prefs_video_change(int id,int direction,int enter){
    int photo;
    switch(id){
    case ROW_CROSSHAIR:AW_CrosshairSet(!AW_CrosshairShown());break;
    case ROW_COLOUR:AW_CrosshairStyleSet(0,AW_CrosshairStyle(0)+direction);break;
    case ROW_SHAPE:AW_CrosshairStyleSet(1,AW_CrosshairStyle(1)+direction);break;
    case ROW_FRAME:AW_UIFrameToggle();break;
    case ROW_FONT:font_step(direction);break;
    case ROW_VOICE:AW_UIVoiceNamesToggle();break;
    case ROW_DIALOGUE:AW_UIDialogueCycle(direction);break;
    case ROW_AIMED:AW_SceneUIOption(0,direction);break;
    case ROW_NPC:AW_SceneUIOption(1,direction);break;
    case ROW_OBJECTS:AW_SceneUIOption(2,direction);break;
    case ROW_AUTOSAVE:if(enter)AW_SetAutosaveCount((AW_AutosaveCount()+1)%17);else AW_SetAutosaveCount(AW_AutosaveCount()+direction);break;
    case ROW_FOG:
        if(enter){fog_slider=1;fog_drag=fog_typing=0;fog_typed[0]=0;fog_before=fog_value();}
        else AW_SetDrawDistance(AW_DrawDistance()+direction*(keydown[K_SHIFT]?1:10));
        break;
    case ROW_RESET:if(enter)AW_SetDrawDistance(300);break;
    case ROW_FAR:far_step(direction);break;
    /* Photo mode needs the running game; the menu closes first so the
     * notice and then the clean frames follow at once. */
    case ROW_PHOTO:if(enter && photo_ready()){photo=!AW_PhotoModeActive();options_close();close_menu();AW_PhotoModeSet(photo);}break;
    case ROW_AREA:AW_RegionLoadingToggle();break;
    case ROW_METHOD:AW_StreamOption(0,1);break;
    case ROW_BUFFER:if(AW_CellChangeMethod()==2)AW_StreamOption(1,direction);break;
    case ROW_MEMORY:memory_toggle();break;
#if defined(AMIWIND_DEBUG_LUMA) && AMIWIND_DEBUG_LUMA
    case ROW_GRAPHICS:brightness_options=1;brightness_drag=0;selection=0;break;
#endif
    }
}
static void row_key(int key){
    int direction=key==K_LEFTARROW?-1:key==K_RIGHTARROW?1:0,enter=key==K_ENTER || key==K_MOUSE1;
    if(tab==TAB_AUDIO){
        if(direction)audio_set(selection,audio_percent(selection)+direction*(keydown[K_SHIFT]?1:5));
        if(key==K_HOME || key==K_END)audio_set(selection,key==K_HOME?0:100);
        if(key==K_MOUSE1 && mouse_x>=AUDIO_X-4 && mouse_x<=AUDIO_X+AUDIO_W+4){audio_drag=selection+1;audio_pointer(selection);}
        return;
    }
    if(tab==TAB_CONTROLS){
        if(selection==CONTROL_SENS){
            if(direction)sens_step(direction);
            if(key==K_HOME || key==K_END)AW_SensitivitySetTenths(key==K_HOME?AW_SENSITIVITY_MENU_MIN:AW_SENSITIVITY_MENU_MAX);
            if(key==K_MOUSE1 && mouse_x>=SENS_X-4 && mouse_x<=SENS_X+SENS_W+4){sens_drag=1;sens_pointer();}
        }else if(selection==CONTROL_INVERT){if(direction || enter)invert_toggle();}
        else if(CONTROL_ACTION(selection)){
            if(key==K_BACKSPACE || key==K_DEL)control_clear(selection-CONTROL_FIRST);
            else if(enter && control_ready(selection)){controls_capture=1;mouse_visible=0;}
        }else if(CONTROL_COMBAT(selection)){if(direction || enter)combat_toggle(selection);}
        else if(selection==CONTROL_RESET && enter)Cbuf_AddText("exec keymaps-default.cfg\n");
        return;
    }
    if(direction || enter)prefs_video_change(row_id(selection),direction?direction:1,enter);
}
/* What the pointer is over on the Options page: 0 nothing, 1 a tab, 2 a row, 3 Back. */
static int options_hit(int *index){
    int i,n=tab_rows(tab);
    for(i=0;i<TABS;i++)if(inside(TAB_X+i*TAB_STEP,TAB_Y,TAB_W,TAB_H)){*index=i;return 1;}
    if(inside(BACK_X,BACK_Y,BACK_W,BACK_H))return 3;
    if(tab==TAB_AUDIO){for(i=0;i<4;i++)if(inside(LIST_X,AUDIO_Y+i*AUDIO_H,LIST_W,AUDIO_H)){*index=i;return 2;}return 0;}
    for(i=0;i<VISIBLE && graphics_top+i<n;i++)if(inside(LIST_X,LIST_Y+i*ROW_H,LIST_W,ROW_H)){*index=graphics_top+i;return 2;}
    return 0;
}
static void options_key(int key){
    int index=0,hit,row;
    if(key==K_ESCAPE){options_close();return;}
    if(key==K_MOUSE1){
        if(tab!=TAB_AUDIO){
            row=AW_UIScrollHit(mouse_x,mouse_y,SCROLL_X,LIST_Y,VISIBLE*ROW_H,tab_rows(tab),VISIBLE,graphics_top);
            if(row>=0){graphics_top=row;selection=row;focus=FOCUS_ROWS;scroll_drag=mouse_y>=LIST_Y+10 && mouse_y<LIST_Y+VISIBLE*ROW_H-10;return;}
        }
        hit=options_hit(&index);
        if(hit==1){if(index!=tab)set_tab(index);focus=FOCUS_TABS;return;}
        if(hit==3){options_close();return;}
        if(hit!=2)return;
        focus=FOCUS_ROWS;selection=index;
    }else mouse_visible=0;
    if(focus==FOCUS_TABS){
        if(key==K_LEFTARROW || key==K_RIGHTARROW)set_tab(tab+(key==K_LEFTARROW?-1:1));
        else if(key==K_DOWNARROW || key==K_TAB || key==K_ENTER){focus=FOCUS_ROWS;selection=graphics_top=0;}
        return;
    }
    if(focus==FOCUS_BACK){
        if(key==K_UPARROW){
            focus=FOCUS_ROWS;selection=tab_rows(tab)-1;
            while(selection>0 && !control_ready(selection) && tab==TAB_CONTROLS)selection--;
            keep_visible();
        }else if(key==K_ENTER)options_close();
        return;
    }
    if(key==K_UPARROW || key==K_DOWNARROW || key==K_TAB){audio_drag=sens_drag=0;rows_step(key==K_UPARROW?K_UPARROW:K_DOWNARROW);return;}
    row_key(key);
}
static void close_menu(void){
    if(frontend)return;
    brightness_reset();
    confirming=scene_picker=graphics=fog_slider=audio_drag=sens_drag=controls_capture=0;key_dest=key_game;IN_AWClearButtons();
}
void M_Menu_Main_f(void){
    FILE *f=NULL;intro_available=COM_FOpenFile("intro/chargenname1.txt",&f)>0 && f!=NULL;if(f)fclose(f);
    brightness_reset();
    IN_AWClearButtons();key_dest=key_menu;selection=confirming=scene_picker=graphics=fog_slider=audio_drag=sens_drag=controls_capture=mouse_visible=graphics_top=scroll_drag=0;
    mouse_x=160;mouse_y=ROW_Y+ROW_H/2;
}
void M_ToggleMenu_f(void){if(key_dest==key_menu)close_menu();else M_Menu_Main_f();}
static void confirm(int action){
    confirmation_return=selection;confirming=action;selection=action==3;
    mouse_visible=0;mouse_x=selection?219:100;mouse_y=144;
}
static void cancel_confirmation(void){confirming=0;selection=confirmation_return;mouse_visible=0;}
void M_Menu_Quit_f(void){M_Menu_Main_f();confirm(1);}
static void main_menu(void){frontend=1;M_Menu_Main_f();AW_MusicTitleAfter(.5);}
static void scene_menu(void){
    int i,size;char path[48];
    if(!sv.active || Cmd_Argc()!=1){Con_Printf("Use dbg scene change during play.\n");return;}
    for(i=0;i<AW_MAP_COUNT;i++){size=AW_SceneMapSize(AW_MapName(i),path,sizeof(path));scene_available[i]=size>=124;}
    brightness_reset();
    picker_return=key_dest;IN_AWClearButtons();key_dest=key_menu;
    scene_picker=1;graphics=fog_slider=audio_drag=sens_drag=controls_capture=confirming=mouse_visible=0;selection=AW_MAP_COUNT;scene_top=0;
    for(i=0;i<AW_MAP_COUNT;i++)if(scene_available[i]){selection=i;break;}
    mouse_x=160;mouse_y=65+selection*24+12;
}
void M_Init(void){
    Cmd_AddCommand("aw_main_menu",main_menu);Cmd_AddCommand("togglemenu",M_ToggleMenu_f);
    Cmd_AddCommand("menu_main",M_Menu_Main_f);Cmd_AddCommand("menu_quit",M_Menu_Quit_f);
    Cmd_AddCommand("aw_scene_menu",scene_menu);
    aw_menu_fullscreen=fullscreen;
}
static int mouse_row(void){
    int i;
#if defined(AMIWIND_DEBUG_LUMA) && AMIWIND_DEBUG_LUMA
    if(brightness_options){if(inside(36,34,248,55))return 0;if(inside(36,91,248,55))return 1;if(inside(222,165,86,25))return 2;return -1;}
#endif
    if(confirming){if(inside(48,132,106,25))return 0;if(inside(166,132,106,25))return 1;return -1;}
    if(scene_picker){for(i=0;i<6 && scene_top+i<=AW_MAP_COUNT;i++)if(inside(44,55+i*19,230,19))return scene_top+i;return -1;}
    if(frontend){for(i=0;i<4;i++)if(inside(12,front_top()+i*front_height(),front_width()-8,front_height()))return i;return -1;}
    for(i=0;i<6;i++)if(inside(44,ROW_Y+i*ROW_H,232,ROW_H))return i;
    return -1;
}
void AW_MenuMouse(int dx,int dy){
    int row,index=0;if(key_dest!=key_menu || (!dx && !dy))return;
    mouse_visible=1;mouse_x+=dx;mouse_y+=dy;
    if(mouse_x<0)mouse_x=0;
    if(mouse_x>319)mouse_x=319;
    if(mouse_y<0)mouse_y=0;
    if(mouse_y>199)mouse_y=199;
    if(!keydown[K_MOUSE1])scroll_drag=audio_drag=sens_drag=fog_drag=0;
    if(fog_slider){if(fog_drag)fog_pointer();return;}
#if defined(AMIWIND_DEBUG_LUMA) && AMIWIND_DEBUG_LUMA
    if(!keydown[K_MOUSE1])brightness_drag=0;
    if(brightness_options && brightness_drag){brightness_pointer();return;}
    if(brightness_options){row=mouse_row();if(row>=0)selection=row;return;}
#endif
    if(graphics){
        if(audio_drag){audio_pointer(audio_drag-1);return;}
        if(sens_drag){sens_pointer();return;}
        if(controls_capture)return;
        if(scroll_drag && tab!=TAB_AUDIO){
            row=AW_UIScrollHit(SCROLL_X,mouse_y<LIST_Y+1?LIST_Y+1:mouse_y>=LIST_Y+VISIBLE*ROW_H?LIST_Y-1+VISIBLE*ROW_H:mouse_y,
                SCROLL_X,LIST_Y,VISIBLE*ROW_H,tab_rows(tab),VISIBLE,graphics_top);
            if(row>=0){graphics_top=row;selection=row;focus=FOCUS_ROWS;}return;
        }
        row=options_hit(&index);
        if(row==2){focus=FOCUS_ROWS;selection=index;}
        else if(row==3)focus=FOCUS_BACK;
        return;
    }
    if(scroll_drag && scene_picker){
        row=AW_UIScrollHit(280,mouse_y<55?55:mouse_y>=54+6*19?53+6*19:mouse_y,276,54,6*19,AW_MAP_COUNT+1,6,scene_top);
        if(row>=0){scene_top=row;selection=row;}return;
    }
    row=mouse_row();if(row>=0)selection=row;
}
void M_Keydown(int key){
    int direction,row;char command[48];
    if(AW_SaveMenuKey(key)){if(key_dest==key_game){frontend=0;graphics=0;}return;}
    /* Capture the raw key before W/A/S/D and wheel are normalized below. */
    if(graphics && tab==TAB_CONTROLS && controls_capture){control_capture(key);return;}
    if(key=='a' || key=='A')key=K_LEFTARROW;
    if(key=='d' || key=='D')key=K_RIGHTARROW;
    if(key=='w' || key=='W')key=K_UPARROW;
    if(key=='s' || key=='S')key=K_DOWNARROW;
    if(key==K_MWHEELUP)key=K_UPARROW;
    if(key==K_MWHEELDOWN)key=K_DOWNARROW;
    if(fog_slider){fog_key(key);return;}
    if(graphics && !brightness_active()){options_key(key);return;}
    if(key==K_MOUSE1){
        if(scene_picker){
            row=AW_UIScrollHit(mouse_x,mouse_y,276,54,114,AW_MAP_COUNT+1,6,scene_top);
            if(row>=0){scene_top=row;selection=row;scroll_drag=mouse_y>=64 && mouse_y<54+114-10;return;}
        }
        row=mouse_row();if(row<0)return;selection=row;
    }
    else mouse_visible=0;
    if(confirming){
        if(key==K_ESCAPE || key=='n'){cancel_confirmation();return;}
        if(key==K_LEFTARROW || key==K_RIGHTARROW || key==K_TAB)selection=1-selection;
        if(key==K_ENTER || key==K_MOUSE1 || key=='y'){
            if(!selection && key!='y'){cancel_confirmation();return;}
            direction=confirming;confirming=0;IN_AWClearButtons();
            if(direction==3){frontend=0;close_menu();Cbuf_AddText("aw_new_game\n");}
            else if(direction==2){key_dest=key_game;Cbuf_AddText("disconnect\naw_main_menu\n");}
            else {key_dest=key_console;Cbuf_AddText("quit\n");}
        }
        return;
    }
#if defined(AMIWIND_DEBUG_LUMA) && AMIWIND_DEBUG_LUMA
    if(brightness_options){
        if(key==K_ESCAPE){brightness_back();return;}
        if(key==K_UPARROW || key==K_DOWNARROW || key==K_TAB){brightness_drag=0;option_step(key,3);}
        if(selection<2){
            if(key==K_LEFTARROW || key==K_RIGHTARROW)R_BrightnessSetStep(selection,R_BrightnessStep(selection)+(key==K_LEFTARROW?-1:1));
            if(key==K_HOME || key==K_END)R_BrightnessSetStep(selection,key==K_HOME?10:15);
            if(key==K_MOUSE1){brightness_drag=selection+1;brightness_pointer();}
        }else if(key==K_ENTER || key==K_MOUSE1)brightness_back();
        return;
    }
#endif
    if(scene_picker){
        if(key==K_ESCAPE){scene_picker=0;key_dest=picker_return;IN_AWClearButtons();return;}
        if(key==K_UPARROW || key==K_DOWNARROW || key==K_TAB){
            direction=key==K_UPARROW?-1:1;do{selection=(selection+direction+AW_MAP_COUNT+1)%(AW_MAP_COUNT+1);}
            while(selection<AW_MAP_COUNT && !scene_available[selection]);
            if(selection<scene_top)scene_top=selection;
            if(selection>=scene_top+6)scene_top=selection-5;
        }
        if(key==K_ENTER || key==K_MOUSE1){
            if(selection==AW_MAP_COUNT){scene_picker=0;key_dest=picker_return;IN_AWClearButtons();}
            else if(scene_available[selection]){direction=selection;close_menu();sprintf(command,"aw_scene %s\n",direction==0?"ship":direction==1?"town":AW_MapName(direction));Cbuf_AddText(command);}
        }
        return;
    }
    if(frontend){
        if(key==K_UPARROW || key==K_DOWNARROW || key==K_TAB){do{selection=(selection+(key==K_UPARROW?3:1))%4;}while(selection==0 && !intro_available);}
        if(key==K_ENTER || key==K_MOUSE1){
            if(selection==0 && intro_available)confirm(3);
            else if(selection==1)AW_SaveMenuOpen(1);
            else if(selection==2)options_open();
            else if(selection==3)confirm(1);
        }
        return;
    }
    if(key==K_ESCAPE){close_menu();return;}
    if(key==K_UPARROW || key==K_DOWNARROW || key==K_TAB){direction=key==K_UPARROW?-1:1;do{selection=(selection+direction+6)%6;}while(!enabled(selection));}
    if(key==K_ENTER || key==K_MOUSE1){
        if(selection==0)close_menu();
        else if(selection==1 && intro_available)confirm(3);
        else if(selection==2)AW_SaveMenuOpen(0);
        else if(selection==3)AW_SaveMenuOpen(1);
        else if(selection==4)options_open();
        else if(selection==5)confirm(2);
    }
}
static void label(int x,int y,int w,int h,const char *s,int active,int selected){
    if(active && selected)AW_UIFill(x,y,w,h,colours[3]);
    AW_UITextBox(x,y,w,h,s,active?colours[1]:colours[2]);
}
/* Match the framed action controls used by character confirmation. */
static void button(int x,int y,int w,int h,const char *s,int active,int selected){
    AW_UIBox(x,y,w,h);
    if(active && selected)AW_UIFill(x+3,y+3,w-6,h-6,colours[3]);
    AW_UITextBox(x,y,w,h,s,active?colours[1]:colours[2]);
}
static void header(void){
    char lines[2][AW_MINIWIND_HEADER];int n,i,h=AW_UIFontSize();
    if(!AW_MiniwindActive() || !AW_Miniwind()->header[0])return;
    if(h<10)h=10;
    n=AW_MenuHeaderLines(AW_Miniwind()->header,300,lines);
    AW_UIFill(4,2,312,n*(h+4)+6,AW_UIColor(0,0,0));
    for(i=0;i<n;i++)AW_UITextBox(10,5+i*(h+4),300,h+4,lines[i],colours[1]);
}
static void cursor(void){
    if(!mouse_visible)return;
    AW_UIFill(mouse_x,mouse_y,2,6,colours[1]);AW_UIFill(mouse_x,mouse_y,6,2,colours[1]);
}
static void rail(int x,int y,int w,int filled){
    AW_UIFill(x,y,w+1,3,colours[2]);AW_UIFill(x,y,filled,3,colours[1]);
    AW_UIFill(x+filled-3,y-5,7,13,colours[1]);AW_UIFill(x+filled-1,y-3,3,9,colours[0]);
}
static void prefs_video_line(int id,char *line){
    static const char *places[]={"Below right","Top right","Above bars"};int value;
    switch(id){
    case ROW_CROSSHAIR:strcpy(line,AW_CrosshairShown()?"Show crosshairs: On":"Show crosshairs: Off");break;
    case ROW_COLOUR:sprintf(line,"Crosshair colour: %s",AW_CrosshairStyleName(0,AW_CrosshairStyle(0)));break;
    case ROW_SHAPE:sprintf(line,"Crosshair shape: %s",AW_CrosshairStyleName(1,AW_CrosshairStyle(1)));break;
    case ROW_FRAME:strcpy(line,AW_UIFrameEnabled()?"Gold frame: On":"Gold frame: Off");break;
    case ROW_FONT:value=AW_UIFontSize();if(value)sprintf(line,"UI font: %ld px",(long)value);else strcpy(line,"UI font: fallback");break;
    case ROW_VOICE:strcpy(line,AW_UIVoiceStyle()==2?"Voice identity: Aim only":AW_UIVoiceNames()?"Voice speaker names: On":"Voice speaker names: Off");break;
    case ROW_DIALOGUE:sprintf(line,"Dialogue style: %ld",(long)AW_UIDialogueMethod());break;
    case ROW_AIMED:strcpy(line,AW_SceneUIOption(0,0)?"Aimed NPC names: On":"Aimed NPC names: Off");break;
    case ROW_NPC:sprintf(line,"NPC: %s",places[AW_SceneUIOption(1,0)-1]);break;
    case ROW_OBJECTS:sprintf(line,"Objects: %s",places[AW_SceneUIOption(2,0)-1]);break;
    case ROW_AUTOSAVE:sprintf(line,"Autosave history: %ld",(long)AW_AutosaveCount());break;
    case ROW_FOG:sprintf(line,"Fog distance: %ld",(long)AW_DrawDistance());break;
    case ROW_RESET:strcpy(line,"Reset distance: 300");break;
    case ROW_FAR:if(far_index()<0)strcpy(line,"Far detail: Custom");else sprintf(line,"Far detail: %s",far_names[far_index()]);break;
    case ROW_PHOTO:strcpy(line,AW_PhotoModeActive()?"Leave photo mode":"Photo mode");break;
    case ROW_AREA:strcpy(line,AW_RegionLoadingFrozen()?"Area loading: Freeze frame":"Area loading: Black screen");break;
    case ROW_METHOD:strcpy(line,AW_CellChangeMethod()==1?"Load method: Current":"Load method: Read-ahead (test)");break;
    case ROW_BUFFER:sprintf(line,"Read-ahead buffer: %ld KiB",(long)AW_StreamOption(1,0));break;
    case ROW_MEMORY:strcpy(line,Cvar_VariableValue("aw_autoram")?"Extra RAM: Automatic":"Extra RAM: Off");break;
    default:strcpy(line,"Graphics...");break;
    }
}
static void options_draw(void){
    int i,yy,value,n=tab_rows(tab),selected;char line[64];const char *help;
    AW_UIBox(0,0,vid.width,vid.height);
    for(i=0;i<TABS;i++)button(TAB_X+i*TAB_STEP,TAB_Y,TAB_W,TAB_H,tab_names[i],1,tab==i);
    AW_UIBox(GROUP_X,GROUP_Y,GROUP_W,GROUP_H);
    if(tab==TAB_AUDIO){
        static const char *names[]={"Master","Music","Effects","Dialogue"};
        for(i=0;i<4;i++){
            yy=AUDIO_Y+i*AUDIO_H;value=audio_percent(i);
            if(focus==FOCUS_ROWS && selection==i)AW_UIFill(LIST_X,yy,LIST_W,AUDIO_H,colours[3]);
            AW_UITextBox(18,yy,110,AUDIO_H,names[i],colours[1]);
            rail(AUDIO_X,yy+13,AUDIO_W,value*AUDIO_W/100);
            sprintf(line,"%ld%%",(long)value);AW_UITextBox(256,yy,38,AUDIO_H,line,colours[1]);
        }
    }else{
        for(i=graphics_top;i<graphics_top+VISIBLE && i<n;i++){
            yy=LIST_Y+(i-graphics_top)*ROW_H;selected=focus==FOCUS_ROWS && selection==i;
            if(tab==TAB_CONTROLS && i==CONTROL_SENS){
                value=AW_SensitivityTenths();
                if(selected)AW_UIFill(LIST_X,yy,LIST_W,ROW_H,colours[3]);
                strcpy(line,"Mouse sensitivity");if(AW_UIWidth(line)>SENS_X-LIST_X-8)strcpy(line,"Sensitivity");
                AW_UITextBox(LIST_X+2,yy,SENS_X-LIST_X-8,ROW_H,line,colours[1]);
                rail(SENS_X,yy+8,SENS_W,(sens_clamp(value)-AW_SENSITIVITY_MENU_MIN)*SENS_W/(AW_SENSITIVITY_MENU_MAX-AW_SENSITIVITY_MENU_MIN));
                sprintf(line,"%ld.%ld",(long)(value/10),(long)(value%10));AW_UITextBox(SENS_X+SENS_W+6,yy,LIST_W-(SENS_X-LIST_X)-SENS_W-6,ROW_H,line,colours[1]);
                continue;
            }
            if(tab==TAB_CONTROLS){
                if(i==CONTROL_INVERT)strcpy(line,invert_on()?"Invert Y axis: On":"Invert Y axis: Off");
                else if(CONTROL_ACTION(i))control_line(i-CONTROL_FIRST,line);
                else if(CONTROL_COMBAT(i))combat_line(i,line);
                else strcpy(line,"Reset to defaults");
            }else prefs_video_line(row_id(i),line);
            label(LIST_X,yy,LIST_W,ROW_H,line,row_active(i),selected);
            /* A live preview of the chosen crosshair beside its colour and shape. */
            if(tab==TAB_PREFS && (row_id(i)==ROW_COLOUR || row_id(i)==ROW_SHAPE))AW_CrosshairDraw(LIST_X+LIST_W-16,yy+6);
        }
        AW_UIScrollbar(SCROLL_X,LIST_Y,VISIBLE*ROW_H,n,VISIBLE,graphics_top);
    }
    if(focus==FOCUS_TABS)help="Left/Right: page   Down: settings";
    else if(focus==FOCUS_BACK)help="Enter: back to the menu";
    else if(tab==TAB_AUDIO)help="Arrows / drag: volume";
    else if(tab==TAB_CONTROLS && controls_capture)help="Press a key   Esc: cancel";
    else if(tab==TAB_CONTROLS && CONTROL_ACTION(selection))help="Enter: set   Del: clear";
    else if(tab==TAB_CONTROLS && selection==CONTROL_SENS)help="Arrows / drag   Shift: fine";
    else help="Left/Right: change   Esc: back";
    AW_UISmallBegin();AW_UITextBox(10,BACK_Y,BACK_X-16,BACK_H,help,colours[1]);AW_UISmallEnd();
    button(BACK_X,BACK_Y,BACK_W,BACK_H,"Back",1,focus==FOCUS_BACK);
}
void M_Draw(void){
    int i,xx,yy,w;char line[64];
    /* A queued console/menu command may have changed destination without a
     * key event. Let the on-demand panels release their state in that case. */
    if(AW_WorldUIDraw())return;
    if(key_dest!=key_menu)return;
    scr_copyeverything=1;
    if(AW_TravelDraw())return;
    if(AW_WaitDraw())return;
    if(!ready){colours[0]=AW_UIColor(22,20,18);colours[1]=AW_UIColor(210,184,121);colours[2]=AW_UIColor(114,114,114);colours[3]=AW_UIColor(62,53,36);ready=1;}
    if(AW_SaveMenuActive()){AW_SaveMenuDraw();return;}
    if(AW_MenuFrontEnd()){
        if(!AW_UIBackground())AW_UIFill(0,0,vid.width,vid.height,AW_UIColor(0,0,0));
        header();
        AW_UIBox(8,front_top()-4,front_width(),front_height()*4+8);
        for(i=0;i<4;i++)label(12,front_top()+i*front_height(),front_width()-8,front_height(),front_items[i],i!=0 || intro_available,i==selection);
        strcpy(line,"AmiWind v" AMIWIND_VERSION);w=AW_UIWidth(line);
        AW_UIFill(vid.width-w-10,180,w+8,20,AW_UIColor(0,0,0));
        AW_UITextBox(vid.width-w-6,180,w,20,line,colours[1]);cursor();return;
    }
#if defined(AMIWIND_DEBUG_LUMA) && AMIWIND_DEBUG_LUMA
    if(brightness_options){
        int value,knob;
        AW_UIBox(0,0,vid.width,vid.height);AW_UITextBox(10,8,300,20,"Graphics",colours[1]);
        for(i=0;i<2;i++){
            yy=34+i*57;value=R_BrightnessStep(i);
            if(selection==i)AW_UIFill(36,yy,248,55,colours[3]);
            sprintf(line,"%s brightness: %ld.%ldx",i?"Exterior":"Interior",(long)(value/10),(long)(value%10));
            AW_UITextBox(14,yy,292,22,line,colours[1]);
            AW_UIFill(BRIGHTNESS_X,yy+32,BRIGHTNESS_W+1,3,colours[2]);
            AW_UIFill(BRIGHTNESS_X,yy+32,(value-10)*BRIGHTNESS_W/5,3,colours[1]);
            for(xx=0;xx<6;xx++)AW_UIFill(BRIGHTNESS_X+xx*BRIGHTNESS_W/5,yy+34,1,5,colours[2]);
            knob=BRIGHTNESS_X+(value-10)*BRIGHTNESS_W/5;
            AW_UIFill(knob-3,yy+26,7,13,colours[1]);AW_UIFill(knob-1,yy+28,3,9,colours[0]);
            AW_UISmallBegin();AW_UITextBox(44,yy+40,40,14,"1.0",colours[1]);AW_UITextBox(244,yy+40,40,14,"1.5",colours[1]);AW_UISmallEnd();
        }
        AW_UISmallBegin();AW_UITextBox(12,166,204,24,"Arrows / drag: brightness",colours[1]);AW_UISmallEnd();
        AW_UIBox(222,165,86,25);label(225,168,80,19,"Back",1,selection==2);cursor();return;
    }
#endif
    if(graphics && fog_slider){
        int fog_knob=FOG_X+(fog_value()-FOG_MIN)*FOG_W/(FOG_MAX-FOG_MIN);
        AW_UIBox(0,0,vid.width,vid.height);
        AW_UITextBox(40,56,240,20,"Fog distance",colours[1]);
        if(fog_typing)sprintf(line,"%s_",fog_typed);else sprintf(line,"%ld",(long)fog_value());
        AW_UIFill(130,76,60,20,colours[3]);AW_UITextBox(130,76,60,20,line,colours[1]);
        AW_UIFill(FOG_X,FOG_Y,FOG_W+1,3,colours[2]);
        AW_UIFill(FOG_X,FOG_Y,fog_knob-FOG_X,3,colours[1]);
        AW_UIFill(fog_knob-3,FOG_Y-5,7,13,colours[1]);AW_UIFill(fog_knob-1,FOG_Y-3,3,9,colours[0]);
        AW_UISmallBegin();
        sprintf(line,"%ld",(long)FOG_MIN);AW_UITextBox(FOG_X-30,FOG_Y-8,28,17,line,colours[1]);
        sprintf(line,"%ld",(long)FOG_MAX);AW_UITextBox(FOG_X+FOG_W+4,FOG_Y-8,30,17,line,colours[1]);
        if(AW_DrawDistance()!=fog_value()){sprintf(line,"This area draws up to %ld",(long)AW_DrawDistance());AW_UITextBox(40,116,240,17,line,colours[2]);}
        AW_UITextBox(30,132,260,17,"Drag / arrows / type a number   Esc: cancel",colours[1]);
        AW_UISmallEnd();
        AW_UIBox(120,150,80,25);label(122,153,76,19,"OK",1,1);cursor();return;
    }
    if(graphics){options_draw();cursor();return;}
    if(frontend)AW_UIFill(0,0,vid.width,vid.height,AW_UIColor(0,0,0));
    else for(yy=0;yy<(int)vid.height;yy++)for(xx=0;xx<(int)vid.width;xx++)
        if((xx&3)!=((yy&1)<<1))vid.buffer[yy*vid.rowbytes+xx]=colours[0];
    AW_UIBox(28,6,264,188);
    if(!AW_UILogo(60,10))AW_UITextBox(44,10,232,40,"AmiWind",colours[1]);
    if(scene_picker){
        for(i=scene_top;i<=AW_MAP_COUNT && i<scene_top+6;i++)
            label(44,55+(i-scene_top)*19,230,19,AW_MapTitle(i),i==AW_MAP_COUNT || scene_available[i],selection==i);
        AW_UIScrollbar(276,54,114,AW_MAP_COUNT+1,6,scene_top);
    }else if(confirming){
        AW_UITextBox(40,69,240,26,confirming==3?"Start a new game?":confirming==2?"Return to main menu?":"Exit the game?",colours[1]);
        if(sv.active)AW_UITextBox(40,97,240,24,"Current progress will be lost.",colours[2]);
        button(48,132,106,25,"Cancel",1,selection==0);
        button(166,132,106,25,confirming==3?"New game":confirming==2?"Leave":"Exit",1,selection==1);
    }else for(i=0;i<6;i++)label(44,ROW_Y+i*ROW_H,232,ROW_H,items[i],enabled(i),selection==i);
    AW_UITextBox(36,174,248,17,"Enter / click   Esc: back",colours[1]);
    cursor();
}
