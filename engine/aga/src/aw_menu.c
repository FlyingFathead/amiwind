/* SPDX-License-Identifier: GPL-2.0-or-later
 * Local menu layout. Original fonts/artwork are private converted inputs.
 */
#include "quakedef.h"
#include "aw_save.h"
#include "aw_maps.h"
#include "aw_region.h"
#include "amiwind_version.h"
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
static int audio_options,audio_drag;
/* Options > Fog distance slider (Morrowind style): drag, arrows, or type. */
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
static int scene_picker,scene_available[AW_MAP_COUNT],scene_top,graphics,interface_options,intro_available;
static keydest_t picker_return;
static int colours[4],ready;
static const char *front_items[]={"New game","Load game","Options","Exit game"};
static const char *items[]={"Return to game","New game","Save game","Load game","Options","Main menu"};

/* Options list rows (Back is OPTION_ROWS-1). Display settings first. */
enum {OPT_FOG,OPT_RESET,OPT_FRAME,OPT_CROSSHAIR,OPT_PHOTO,OPT_INTERFACE,OPT_AUDIO,OPT_CONTROLS,
    OPT_AUTOSAVE,OPT_AREA,OPT_METHOD,OPT_BUFFER,OPT_GRAPHICS};
#define ROW_Y 54
#define ROW_H 19
#if defined(AMIWIND_DEBUG_LUMA) && AMIWIND_DEBUG_LUMA
#define OPTION_ROWS 14
static int brightness_options,brightness_drag;
extern int R_BrightnessStep(int outside);
extern void R_BrightnessSetStep(int outside,int value);
#define BRIGHTNESS_X 60
#define BRIGHTNESS_W 200
static int brightness_active(void){return brightness_options;}
static void brightness_reset(void){brightness_options=brightness_drag=0;}
static void brightness_back(void){brightness_reset();selection=OPT_GRAPHICS;mouse_visible=0;}
static void brightness_pointer(void){R_BrightnessSetStep(brightness_drag-1,10+((mouse_x-BRIGHTNESS_X)*5+BRIGHTNESS_W/2)/BRIGHTNESS_W);}
#else
#define OPTION_ROWS 13
#define brightness_active() 0
#define brightness_reset() ((void)0)
#endif
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
static void audio_back(void){audio_options=audio_drag=0;selection=OPT_AUDIO;mouse_visible=0;}
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
    {"Use","+aw_use"},{"Attack","+attack"},{"Hands","impulse 202"},{"Torch","aw_torch"},
    {"Map","aw_worldmap"},{"Journal","aw_journal"},{"Wait","aw_wait"},
    {"Quick save","aw_quicksave"},{"Quick load","aw_quickload"},
    {"Inventory",NULL,"I"},{"Quick keys",NULL,"1-9"},{"Ready magic",NULL,"R"},{"Cast spell",NULL,NULL}};
#define CONTROL_ACTIONS ((int)(sizeof(controls)/sizeof(controls[0])))
#define CONTROL_ROWS (CONTROL_ACTIONS+2)
#define CONTROL_VISIBLE 6
static int controls_options,controls_top,controls_capture;
static int control_ready(int row){return row>=CONTROL_ACTIONS || controls[row].command!=NULL;}
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
    if(controls_capture && selection==action){strcat(line," ?");return;}
    if(!n)strcat(line," -");
    for(i=0;i<n;i++){key_label(keys[i],name);strcat(line,i?", ":" ");strcat(line,name);}
}
static void control_clear(int action){int keys[2],n=control_keys(action,keys),i;for(i=0;i<n;i++)Key_SetBinding(keys[i],"");}
static void control_capture(int key){
    int keys[2],n;
    controls_capture=0;
    if(key==K_ESCAPE)return;
    if(key==K_BACKSPACE || key==K_DEL){control_clear(selection);return;}
    if(key>='A' && key<='Z')key+='a'-'A';
    if(!controls[selection].command)return;
    if(keybindings[key] && !strcmp(keybindings[key],controls[selection].command))return;
    n=control_keys(selection,keys);
    if(n>=2)control_clear(selection);
    Key_SetBinding(key,(char *)controls[selection].command);
}
static void controls_back(void){controls_options=controls_capture=0;selection=OPT_CONTROLS;mouse_visible=0;}
static void controls_open(void){controls_options=1;controls_capture=controls_top=selection=0;mouse_visible=0;}
/* Setup lists stop at their ends so selection and scrollbar never jump back
 * across the list. This also applies to wheel/W/S input normalized below. */
static void option_step(int key,int rows){
    if(key==K_UPARROW){if(selection>0)selection--;}
    else if(selection<rows-1)selection++;
}
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
static void interface_change(int direction){
    if(selection==0)font_step(direction);
    else if(selection==1)AW_UIVoiceNamesToggle();
    else if(selection==2)AW_UIDialogueCycle(direction);
    else if(selection>=3 && selection<=5)AW_SceneUIOption(selection-3,direction);
}
static void close_menu(void){
    if(frontend)return;
    brightness_reset();
    confirming=scene_picker=graphics=interface_options=audio_options=audio_drag=controls_options=controls_capture=0;key_dest=key_game;IN_AWClearButtons();
}
void M_Menu_Main_f(void){
    FILE *f=NULL;intro_available=COM_FOpenFile("intro/chargenname1.txt",&f)>0 && f!=NULL;if(f)fclose(f);
    brightness_reset();
    IN_AWClearButtons();key_dest=key_menu;selection=confirming=scene_picker=graphics=interface_options=audio_options=audio_drag=controls_options=controls_capture=mouse_visible=graphics_top=scroll_drag=0;
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
    scene_picker=1;graphics=interface_options=audio_options=audio_drag=controls_options=controls_capture=confirming=mouse_visible=0;selection=AW_MAP_COUNT;scene_top=0;
    for(i=0;i<AW_MAP_COUNT;i++)if(scene_available[i]){selection=i;break;}
    mouse_x=160;mouse_y=65+selection*24+12;
}
void M_Init(void){
    Cmd_AddCommand("aw_main_menu",main_menu);Cmd_AddCommand("togglemenu",M_ToggleMenu_f);
    Cmd_AddCommand("menu_main",M_Menu_Main_f);Cmd_AddCommand("menu_quit",M_Menu_Quit_f);
    Cmd_AddCommand("aw_scene_menu",scene_menu);
}
static int mouse_row(void){
    int i;
#if defined(AMIWIND_DEBUG_LUMA) && AMIWIND_DEBUG_LUMA
    if(brightness_options){if(inside(36,34,248,55))return 0;if(inside(36,91,248,55))return 1;if(inside(222,165,86,25))return 2;return -1;}
#endif
    if(confirming){if(inside(48,132,106,25))return 0;if(inside(166,132,106,25))return 1;return -1;}
    if(audio_options){for(i=0;i<4;i++)if(inside(10,AUDIO_Y+i*AUDIO_H,300,AUDIO_H))return i;if(inside(222,165,86,25))return 4;return -1;}
    if(interface_options){for(i=0;i<7;i++)if(inside(44,54+i*19,232,19))return i;return -1;}
    if(controls_options){for(i=0;i<CONTROL_VISIBLE && controls_top+i<CONTROL_ROWS;i++)if(inside(44,54+i*19,230,19))return controls_top+i;return -1;}
    if(graphics){for(i=0;i<7;i++)if(inside(44,54+i*19,230,19))return graphics_top+i;return -1;}
    if(scene_picker){for(i=0;i<6 && scene_top+i<=AW_MAP_COUNT;i++)if(inside(44,55+i*19,230,19))return scene_top+i;return -1;}
    if(frontend){for(i=0;i<4;i++)if(inside(12,front_top()+i*front_height(),front_width()-8,front_height()))return i;return -1;}
    for(i=0;i<6;i++)if(inside(44,ROW_Y+i*ROW_H,232,ROW_H))return i;
    return -1;
}
void AW_MenuMouse(int dx,int dy){
    int row;if(key_dest!=key_menu || (!dx && !dy))return;
    mouse_visible=1;mouse_x+=dx;mouse_y+=dy;
    if(mouse_x<0)mouse_x=0;
    if(mouse_x>319)mouse_x=319;
    if(mouse_y<0)mouse_y=0;
    if(mouse_y>199)mouse_y=199;
    if(!keydown[K_MOUSE1])scroll_drag=audio_drag=fog_drag=0;
    if(fog_slider){if(fog_drag)fog_pointer();return;}
#if defined(AMIWIND_DEBUG_LUMA) && AMIWIND_DEBUG_LUMA
    if(!keydown[K_MOUSE1])brightness_drag=0;
    if(brightness_options && brightness_drag){brightness_pointer();return;}
#endif
    if(audio_options && audio_drag){audio_pointer(audio_drag-1);return;}
    if(controls_capture)return;
    if(scroll_drag && ((graphics && !interface_options && !audio_options && !controls_options && !brightness_active()) || scene_picker)){
        int total=graphics?OPTION_ROWS:AW_MAP_COUNT+1,visible=graphics?7:6;
        row=AW_UIScrollHit(280,mouse_y<55?55:mouse_y>=54+visible*19?53+visible*19:mouse_y,276,54,visible*19,total,visible,graphics?graphics_top:scene_top);
        if(row>=0){if(graphics)graphics_top=row;else scene_top=row;selection=row;}return;
    }
    row=mouse_row();if(row>=0)selection=row;
}
void M_Keydown(int key){
    int direction,row,photo;char command[48];
    if(AW_SaveMenuKey(key)){if(key_dest==key_game){frontend=0;graphics=0;}return;}
    /* Capture the raw key before W/A/S/D and wheel are normalized below. */
    if(controls_options && controls_capture){control_capture(key);return;}
    if(key=='a' || key=='A')key=K_LEFTARROW;
    if(key=='d' || key=='D')key=K_RIGHTARROW;
    if(key=='w' || key=='W')key=K_UPARROW;
    if(key=='s' || key=='S')key=K_DOWNARROW;
    if(key==K_MWHEELUP)key=K_UPARROW;
    if(key==K_MWHEELDOWN)key=K_DOWNARROW;
    if(fog_slider){fog_key(key);return;}
    if(key==K_MOUSE1){
        if((graphics && !interface_options && !audio_options && !controls_options && !brightness_active()) || scene_picker){
            row=AW_UIScrollHit(mouse_x,mouse_y,276,54,graphics?133:114,graphics?OPTION_ROWS:AW_MAP_COUNT+1,graphics?7:6,graphics?graphics_top:scene_top);
            if(row>=0){if(graphics)graphics_top=row;else scene_top=row;selection=row;scroll_drag=mouse_y>=64 && mouse_y<54+(graphics?133:114)-10;return;}
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
    if(audio_options){
        if(key==K_ESCAPE){audio_back();return;}
        if(key==K_UPARROW || key==K_DOWNARROW || key==K_TAB){audio_drag=0;option_step(key,5);}
        if(selection<4){
            if(key==K_LEFTARROW || key==K_RIGHTARROW)audio_set(selection,audio_percent(selection)+(key==K_LEFTARROW?-1:1)*(keydown[K_SHIFT]?1:5));
            if(key==K_HOME || key==K_END)audio_set(selection,key==K_HOME?0:100);
            if(key==K_MOUSE1 && mouse_x>=AUDIO_X-4 && mouse_x<=AUDIO_X+AUDIO_W+4){audio_drag=selection+1;audio_pointer(selection);}
        }else if(key==K_ENTER || key==K_MOUSE1)audio_back();
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
    if(controls_options){
        if(key==K_ESCAPE){controls_back();return;}
        if(key==K_UPARROW || key==K_DOWNARROW || key==K_TAB){
            row=selection;
            do option_step(key,CONTROL_ROWS);while(!control_ready(selection) && selection>0 && selection<CONTROL_ROWS-1);
            if(!control_ready(selection))selection=row;
        }
        if(selection<controls_top)controls_top=selection;
        if(selection>=controls_top+CONTROL_VISIBLE)controls_top=selection-CONTROL_VISIBLE+1;
        if((key==K_BACKSPACE || key==K_DEL) && selection<CONTROL_ACTIONS)control_clear(selection);
        if(key==K_ENTER || key==K_MOUSE1){
            if(selection<CONTROL_ACTIONS){if(control_ready(selection)){controls_capture=1;mouse_visible=0;}}
            else if(selection==CONTROL_ACTIONS)Cbuf_AddText("exec keymaps-default.cfg\n");
            else controls_back();
        }
        return;
    }
    if(interface_options){
        if(key==K_ESCAPE){interface_options=0;selection=OPT_INTERFACE;return;}
        if(key==K_UPARROW || key==K_DOWNARROW || key==K_TAB)option_step(key,7);
        if(key==K_LEFTARROW || key==K_RIGHTARROW)interface_change(key==K_LEFTARROW?-1:1);
        if(key==K_ENTER || key==K_MOUSE1){if(selection==6){interface_options=0;selection=OPT_INTERFACE;}else interface_change(1);}
        return;
    }
    if(graphics){
        if(key==K_ESCAPE){graphics=0;selection=frontend?2:4;return;}
        if(key==K_UPARROW || key==K_DOWNARROW || key==K_TAB)option_step(key,OPTION_ROWS);
        if(selection<graphics_top)graphics_top=selection;
        if(selection>=graphics_top+7)graphics_top=selection-6;
#if defined(AMIWIND_DEBUG_LUMA) && AMIWIND_DEBUG_LUMA
        if(selection==OPT_GRAPHICS && (key==K_LEFTARROW || key==K_RIGHTARROW)){brightness_options=1;brightness_drag=0;selection=0;return;}
#endif
        if(selection==OPT_FOG && (key==K_LEFTARROW || key==K_RIGHTARROW))AW_SetDrawDistance(AW_DrawDistance()+(key==K_LEFTARROW?-1:1)*(keydown[K_SHIFT]?1:10));
        if(selection==OPT_CROSSHAIR && (key==K_LEFTARROW || key==K_RIGHTARROW))AW_CrosshairSet(!AW_CrosshairShown());
        if(selection==OPT_INTERFACE && (key==K_LEFTARROW || key==K_RIGHTARROW)){interface_options=1;selection=0;return;}
        if(selection==OPT_AUDIO && (key==K_LEFTARROW || key==K_RIGHTARROW)){audio_options=1;selection=0;return;}
        if(selection==OPT_CONTROLS && (key==K_LEFTARROW || key==K_RIGHTARROW)){controls_open();return;}
        if(selection==OPT_AUTOSAVE && (key==K_LEFTARROW || key==K_RIGHTARROW))AW_SetAutosaveCount(AW_AutosaveCount()+(key==K_LEFTARROW?-1:1));
        if(selection==OPT_AREA && (key==K_LEFTARROW || key==K_RIGHTARROW))AW_RegionLoadingToggle();
        if(selection==OPT_METHOD && (key==K_LEFTARROW || key==K_RIGHTARROW))AW_StreamOption(0,1);
        if(selection==OPT_BUFFER && AW_CellChangeMethod()==2 && (key==K_LEFTARROW || key==K_RIGHTARROW))AW_StreamOption(1,key==K_LEFTARROW?-1:1);
        if(key==K_ENTER || key==K_MOUSE1){
            if(selection==OPT_FOG){fog_slider=1;fog_drag=fog_typing=0;fog_typed[0]=0;fog_before=fog_value();}
            else if(selection==OPT_RESET)AW_SetDrawDistance(540);
            else if(selection==OPT_FRAME)AW_UIFrameToggle();
            else if(selection==OPT_CROSSHAIR)AW_CrosshairSet(!AW_CrosshairShown());
            /* Photo mode needs the running game; the menu closes first so the
             * notice and then the clean frames follow at once. */
            else if(selection==OPT_PHOTO && photo_ready()){photo=!AW_PhotoModeActive();close_menu();AW_PhotoModeSet(photo);}
            else if(selection==OPT_INTERFACE){interface_options=1;selection=0;}
            else if(selection==OPT_AUDIO){audio_options=1;audio_drag=0;selection=0;}
            else if(selection==OPT_CONTROLS)controls_open();
            else if(selection==OPT_AUTOSAVE)AW_SetAutosaveCount((AW_AutosaveCount()+1)%17);
            else if(selection==OPT_AREA)AW_RegionLoadingToggle();
            else if(selection==OPT_METHOD)AW_StreamOption(0,1);
            else if(selection==OPT_BUFFER && AW_CellChangeMethod()==2)AW_StreamOption(1,1);
#if defined(AMIWIND_DEBUG_LUMA) && AMIWIND_DEBUG_LUMA
            else if(selection==OPT_GRAPHICS){brightness_options=1;brightness_drag=0;selection=0;}
#endif
            else if(selection==OPTION_ROWS-1){graphics=0;selection=frontend?2:4;}
        }
        return;
    }
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
            else if(selection==2){graphics=1;graphics_top=0;selection=0;mouse_x=160;mouse_y=100;}
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
        else if(selection==4){graphics=1;graphics_top=0;selection=0;mouse_x=160;mouse_y=100;}
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
static void cursor(void){
    if(!mouse_visible)return;
    AW_UIFill(mouse_x,mouse_y,2,6,colours[1]);AW_UIFill(mouse_x,mouse_y,6,2,colours[1]);
}
void M_Draw(void){
    int i,xx,yy,value,knob,w;char line[64];
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
        AW_UIBox(8,front_top()-4,front_width(),front_height()*4+8);
        for(i=0;i<4;i++)label(12,front_top()+i*front_height(),front_width()-8,front_height(),front_items[i],i!=0 || intro_available,i==selection);
        strcpy(line,"AmiWind v" AMIWIND_VERSION);w=AW_UIWidth(line);
        AW_UIFill(vid.width-w-10,180,w+8,20,AW_UIColor(0,0,0));
        AW_UITextBox(vid.width-w-6,180,w,20,line,colours[1]);cursor();return;
    }
    if(frontend)AW_UIFill(0,0,vid.width,vid.height,AW_UIColor(0,0,0));
    else for(yy=0;yy<vid.height;yy++)for(xx=0;xx<vid.width;xx++)
        if((xx&3)!=((yy&1)<<1))vid.buffer[yy*vid.rowbytes+xx]=colours[0];
    if(audio_options){
        static const char *names[]={"Master","Music","Effects","Dialogue"};
        AW_UIBox(2,2,316,196);AW_UITextBox(10,8,300,20,"Audio",colours[1]);
        for(i=0;i<4;i++){
            yy=AUDIO_Y+i*AUDIO_H;value=audio_percent(i);
            if(selection==i)AW_UIFill(10,yy,300,AUDIO_H,colours[3]);
            AW_UITextBox(14,yy,110,AUDIO_H,names[i],colours[1]);
            AW_UIFill(AUDIO_X,yy+13,AUDIO_W+1,3,colours[2]);
            AW_UIFill(AUDIO_X,yy+13,value*AUDIO_W/100,3,colours[1]);
            knob=AUDIO_X+value*AUDIO_W/100;
            AW_UIFill(knob-3,yy+8,7,13,colours[1]);AW_UIFill(knob-1,yy+10,3,9,colours[0]);
            sprintf(line,"%ld%%",(long)value);AW_UITextBox(264,yy,44,AUDIO_H,line,colours[1]);
        }
        AW_UISmallBegin();AW_UITextBox(12,166,204,24,"Arrows / drag: volume",colours[1]);AW_UISmallEnd();
        AW_UIBox(222,165,86,25);label(225,168,80,19,"Back",1,selection==4);cursor();return;
    }
#if defined(AMIWIND_DEBUG_LUMA) && AMIWIND_DEBUG_LUMA
    if(brightness_options){
        AW_UIBox(2,2,316,196);AW_UITextBox(10,8,300,20,"Graphics",colours[1]);
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
    AW_UIBox(28,6,264,188);
    if(!AW_UILogo(60,10))AW_UITextBox(44,10,232,40,"AmiWind",colours[1]);
    if(interface_options){
        static const char *places[]={"Below right","Top right","Above bars"};
        value=AW_UIFontSize();if(value)sprintf(line,"UI font: %ld px",(long)value);else strcpy(line,"UI font: fallback");
        label(44,54,232,19,line,1,selection==0);
        label(44,73,232,19,AW_UIVoiceStyle()==2?"Voice identity: Aim only":AW_UIVoiceNames()?"Voice speaker names: On":"Voice speaker names: Off",1,selection==1);
        sprintf(line,"Dialogue style: %ld",(long)AW_UIDialogueMethod());label(44,92,232,19,line,1,selection==2);
        label(44,111,232,19,AW_SceneUIOption(0,0)?"Aimed NPC names: On":"Aimed NPC names: Off",1,selection==3);
        sprintf(line,"NPC: %s",places[AW_SceneUIOption(1,0)-1]);label(44,130,232,19,line,1,selection==4);
        sprintf(line,"Objects: %s",places[AW_SceneUIOption(2,0)-1]);label(44,149,232,19,line,1,selection==5);
        label(44,168,232,19,"Back",1,selection==6);
    }else if(controls_options){
        for(i=controls_top;i<controls_top+CONTROL_VISIBLE && i<CONTROL_ROWS;i++){
            if(i<CONTROL_ACTIONS)control_line(i,line);
            else strcpy(line,i==CONTROL_ACTIONS?"Reset to defaults":"Back");
            label(44,54+(i-controls_top)*19,230,19,line,control_ready(i),selection==i);
        }
        AW_UIScrollbar(276,54,CONTROL_VISIBLE*19,CONTROL_ROWS,CONTROL_VISIBLE,controls_top);
        AW_UISmallBegin();
        AW_UITextBox(36,170,236,17,controls_capture?"Press a key   Esc: cancel":"Enter: set   Del: clear",colours[1]);
        AW_UISmallEnd();
    }else if(graphics && fog_slider){
        int knob=FOG_X+(fog_value()-FOG_MIN)*FOG_W/(FOG_MAX-FOG_MIN);
        AW_UITextBox(40,56,240,20,"Fog distance",colours[1]);
        if(fog_typing)sprintf(line,"%s_",fog_typed);else sprintf(line,"%ld",(long)fog_value());
        AW_UIFill(130,76,60,20,colours[3]);AW_UITextBox(130,76,60,20,line,colours[1]);
        AW_UIFill(FOG_X,FOG_Y,FOG_W+1,3,colours[2]);
        AW_UIFill(FOG_X,FOG_Y,knob-FOG_X,3,colours[1]);
        AW_UIFill(knob-3,FOG_Y-5,7,13,colours[1]);AW_UIFill(knob-1,FOG_Y-3,3,9,colours[0]);
        AW_UISmallBegin();
        sprintf(line,"%ld",(long)FOG_MIN);AW_UITextBox(FOG_X-30,FOG_Y-8,28,17,line,colours[1]);
        sprintf(line,"%ld",(long)FOG_MAX);AW_UITextBox(FOG_X+FOG_W+4,FOG_Y-8,30,17,line,colours[1]);
        if(AW_DrawDistance()!=fog_value()){sprintf(line,"This area draws up to %ld",(long)AW_DrawDistance());AW_UITextBox(40,116,240,17,line,colours[2]);}
        AW_UITextBox(30,132,260,17,"Drag / arrows / type a number   Esc: cancel",colours[1]);
        AW_UISmallEnd();
        AW_UIBox(120,150,80,25);label(122,153,76,19,"OK",1,1);
    }else if(graphics){
        for(i=graphics_top;i<graphics_top+7;i++){
            switch(i){
            case OPT_FOG:sprintf(line,"Fog distance: %ld",(long)AW_DrawDistance());break;
            case OPT_RESET:strcpy(line,"Reset distance: 540");break;
            case OPT_FRAME:strcpy(line,AW_UIFrameEnabled()?"Gold frame: On":"Gold frame: Off");break;
            case OPT_CROSSHAIR:strcpy(line,AW_CrosshairShown()?"Show crosshairs: On":"Show crosshairs: Off");break;
            case OPT_PHOTO:strcpy(line,AW_PhotoModeActive()?"Leave photo mode":"Photo mode");break;
            case OPT_INTERFACE:strcpy(line,"Interface...");break;
            case OPT_AUDIO:strcpy(line,"Audio...");break;
            case OPT_CONTROLS:strcpy(line,"Controls...");break;
            case OPT_AUTOSAVE:sprintf(line,"Autosave history: %ld",(long)AW_AutosaveCount());break;
            case OPT_AREA:strcpy(line,AW_RegionLoadingFrozen()?"Area loading: Freeze frame":"Area loading: Black screen");break;
            case OPT_METHOD:strcpy(line,AW_CellChangeMethod()==1?"Load method: Current":"Load method: Read-ahead (test)");break;
            case OPT_BUFFER:sprintf(line,"Read-ahead buffer: %ld KiB",(long)AW_StreamOption(1,0));break;
#if defined(AMIWIND_DEBUG_LUMA) && AMIWIND_DEBUG_LUMA
            case OPT_GRAPHICS:strcpy(line,"Graphics...");break;
#endif
            default:strcpy(line,"Back");break;
            }
            label(44,54+(i-graphics_top)*19,230,19,line,(i!=OPT_BUFFER || AW_CellChangeMethod()==2) && (i!=OPT_PHOTO || photo_ready()),selection==i);
        }
        AW_UIScrollbar(276,54,133,OPTION_ROWS,7,graphics_top);
    }else if(scene_picker){
        for(i=scene_top;i<=AW_MAP_COUNT && i<scene_top+6;i++)
            label(44,55+(i-scene_top)*19,230,19,AW_MapTitle(i),i==AW_MAP_COUNT || scene_available[i],selection==i);
        AW_UIScrollbar(276,54,114,AW_MAP_COUNT+1,6,scene_top);
    }else if(confirming){
        AW_UITextBox(40,69,240,26,confirming==3?"Start a new game?":confirming==2?"Return to main menu?":"Exit the game?",colours[1]);
        if(sv.active)AW_UITextBox(40,97,240,24,"Current progress will be lost.",colours[2]);
        button(48,132,106,25,"Cancel",1,selection==0);
        button(166,132,106,25,confirming==3?"New game":confirming==2?"Leave":"Exit",1,selection==1);
    }else for(i=0;i<6;i++)label(44,ROW_Y+i*ROW_H,232,ROW_H,items[i],enabled(i),selection==i);
    if(!graphics)AW_UITextBox(36,174,248,17,"Enter / click   Esc: back",colours[1]);
    cursor();
}
