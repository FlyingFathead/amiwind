/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
keydest_t key_dest;qboolean keydown[256];viddef_t vid;server_t sv;int scr_copyeverything;
char *keybindings[256];
int (*aw_menu_fullscreen)(void);
void Key_SetBinding(int keynum,char *binding){keybindings[keynum]=binding;}
char *Key_KeynumToString(int keynum){static char s[2];s[0]=(char)keynum;s[1]=0;return s;}
byte pixels[320*200];int clears,quit,changes,missing,intro_missing;
static int distance=540,gold_frame,frozen_loading=1;
int AW_RegionLoadingFrozen(void){return frozen_loading;}
void AW_RegionLoadingToggle(void){frozen_loading=!frozen_loading;}
static void (*picker)(void),(*front)(void);static char queued[64];
static int mx=160,my=63;
cvar_t volume={"volume","0.7",true,false,.7f},bgmvolume={"bgmvolume","1",true,false,1};
cvar_t effectsvolume={"effectsvolume","0.75",true,false,.75f},dialoguevolume={"dialoguevolume","1",true,false,1};
static int audio_sets;
static int highlight_y,highlight_w,scroll_top,scroll_total;
static int own_cursor;   /* the menu's own (AmiWind) cursor strokes drawn: AW_UICursor below said no */
/* Controls > Combat style / Dice rolls / Blocking (aw_combat.c's saved options). */
static float combat_miss=1,combat_dice=1,combat_block=0;   /* the shipped defaults (COMBAT-BLOCK-DEFAULT-62: automatic block) */
/* Controls > Weapon sway (aw_fp_sway, FP-WEAPON-SWAY-61: 1 AmiWind groove, the default; 2 Morrowind stiff). */
static float fp_sway=1;
/* Video > Far detail (aw_cull, aw_fog.c; the engine default 4 = Strong). */
static float far_detail=4;static int far_sets;
/* Video > Tree crowns (aw_tree_crowns, chim_world.c; default 0 = original). */
static float tree_crowns;
/* Video > Extra RAM (aw_autoram, chim_world.c; default 1 = automatic). */
static float autoram=1;
/* Controls > Invert Y axis: the sign of Quake's m_pitch (default 0.022). */
static float pitch_value=.022f;
/* Audio > Your footsteps (aw_player_footsteps, default off). */
static float player_steps;
/* Prefs > Always use best attack (aw_combat_best_attack, BEST-ATTACK-OPTION-62: on by default, an AmiWind default). */
static float best_attack=1;
/* Video > Fog distance indoors and Fog in large rooms (aw_fog.c, LARGE-ROOM-FOG-SETTING-64: 300 and on by default). */
static float fog_indoors=300,fog_large_rooms=1;
float Cvar_VariableValue(char *name){
    if(!strcmp(name,"aw_fog_distance_interior"))return fog_indoors;
    if(!strcmp(name,"aw_fog_large_rooms"))return fog_large_rooms;
    if(!strcmp(name,"aw_combat_best_attack"))return best_attack;
    if(!strcmp(name,"aw_cull"))return far_detail;
    if(!strcmp(name,"aw_autoram"))return autoram;
    if(!strcmp(name,"aw_combat_miss"))return combat_miss;
    if(!strcmp(name,"aw_combat_dice"))return combat_dice;
    if(!strcmp(name,"aw_combat_block"))return combat_block;
    if(!strcmp(name,"aw_fp_sway"))return fp_sway;
    if(!strcmp(name,"m_pitch"))return pitch_value;
    if(!strcmp(name,"aw_player_footsteps"))return player_steps;
    if(!strcmp(name,"aw_tree_crowns"))return tree_crowns;
    assert(0);return 0;
}
void Cvar_SetValue(char *name,float value){cvar_t *rows[]={&volume,&bgmvolume,&effectsvolume,&dialoguevolume};int i;
    if(!strcmp(name,"aw_cull")){assert(value==1 || value==3 || value==4 || value==6);far_detail=value;far_sets++;return;}
    if(!strcmp(name,"aw_tree_crowns")){assert(value==0 || value==1 || value==2);tree_crowns=value;return;}
    if(!strcmp(name,"m_pitch")){pitch_value=value;return;}
    if(!strcmp(name,"aw_player_footsteps")){assert(value==0 || value==1);player_steps=value;return;}
    if(!strcmp(name,"aw_fp_sway")){assert(value==1 || value==2);fp_sway=value;return;}
    if(!strcmp(name,"aw_fog_distance_interior")){assert(value>=100 && value<=4*1024);fog_indoors=value;return;}
    assert(value>=0 && value<=1);
    if(!strcmp(name,"aw_fog_large_rooms")){fog_large_rooms=value;return;}
    if(!strcmp(name,"aw_combat_miss")){combat_miss=value;return;}
    if(!strcmp(name,"aw_autoram")){autoram=value;return;}
    if(!strcmp(name,"aw_combat_dice")){combat_dice=value;return;}
    if(!strcmp(name,"aw_combat_block")){combat_block=value;return;}
    if(!strcmp(name,"aw_combat_best_attack")){best_attack=value;return;}
    for(i=0;i<4;i++)if(!strcmp(rows[i]->name,name)){rows[i]->value=value;audio_sets++;return;}assert(0);}
void AW_UISmallBegin(void){}void AW_UISmallEnd(void){}
int AW_UIFrameEnabled(void){return gold_frame;}
void AW_UIFrameToggle(void){gold_frame=!gold_frame;}
int AW_DrawDistance(void){return distance;}
void AW_SetDrawDistance(int n){if(n<100)n=100;if(n>1500)n=1500;distance=n;}
int Cmd_Argc(void){return 1;}
void Con_Printf(char *fmt,...){}
int COM_FOpenFile(char *name,FILE **f){if(missing || (intro_missing && !strcmp(name,"intro/chargenname1.txt"))){*f=NULL;return -1;}*f=tmpfile();return 124;}
/* aw_region.c AW_SceneMapSize: the scene's own map (no CHIM frame maps in this test). */
int AW_SceneMapSize(const char *n,char *p,int s){char b[64];FILE *f=NULL;int k;sprintf(b,"maps/%s.bsp",n);k=COM_FOpenFile(b,&f);if(f)fclose(f);else k=-1;if(p && s>0){strncpy(p,b,s-1);p[s-1]=0;}return k;}
void IN_AWClearButtons(void){clears++;}
void Cmd_AddCommand(char *name,void (*fn)(void)){if(!strcmp(name,"aw_scene_menu"))picker=fn;else if(!strcmp(name,"aw_main_menu"))front=fn;}
void Cbuf_AddText(char *s){if(!strcmp(s,"quit\n"))quit++;else{strcpy(queued,s);changes++;}}
int AW_UIBackground(void){return 1;}int AW_UILogo(int x,int y){assert(x==60 && y==10);return 1;}
int AW_UIWidth(const char *s){return strlen(s)*7;}
int AW_UIColor(int r,int g,int b){return r;}
void AW_UIFill(int x,int y,int w,int h,int c){if(c==62){highlight_y=y;highlight_w=w;}if(c==210 && w==2 && h==6)own_cursor++;}
void AW_UIScrollbar(int x,int y,int h,int total,int visible,int top){assert(x>=0 && x+10<=320 && y+h<=200);assert(top>=0 && top+visible<=total);scroll_top=top;scroll_total=total;}
int AW_UIScrollHit(int mx,int my,int x,int y,int h,int total,int visible,int top){return -1;}
/* What the Options page drew: labels by their start, every tab and box. */
static char crosshair_label[64],photo_label[64],far_label[64],colour_label[64],shape_label[64],invert_label[64],cursor_label[64],
            best_label[64],room_fog_label[64],indoor_label[64];
/* The mouse cursor (aw_ui.c, CURSOR-MW-58): aw_cursor_type 2 = Morrowind's pointer (drawn when the image has it), 1 = AmiWind's. */
static int cursor_kind=2,cursor_calls,cursor_art=1;
int AW_UICursorType(void){return cursor_kind;}
void AW_UICursorTypeSet(int type){assert(type==1 || type==2);cursor_kind=type;}
int AW_UICursor(int x,int y){assert(x>=0 && x<320 && y>=0 && y<200);cursor_calls++;return cursor_kind==2 && cursor_art;}
static char sens_value[16],help[64];static int photo_colour,tabs_drawn,audio_draws,boxes,full_box,preview_x,previews;
void AW_UITextBox(int x,int y,int w,int h,const char *s,int c){assert(y>=0 && y+h<=200 && x>=0 && x+w<=320);
 if(!strcmp(s,"Prefs") || !strcmp(s,"Controls") || !strcmp(s,"Video"))tabs_drawn++;
 if(!strcmp(s,"Audio")){tabs_drawn++;audio_draws++;}
 if(!strncmp(s,"Show crosshairs",15))strcpy(crosshair_label,s);
 if(!strncmp(s,"Crosshair colour",16))strcpy(colour_label,s);
 if(!strncmp(s,"Crosshair shape",15))strcpy(shape_label,s);
 if(!strncmp(s,"Mouse cursor",12))strcpy(cursor_label,s);
 if(!strncmp(s,"Always use best attack",22)){strcpy(best_label,s);assert(AW_UIWidth(s)<=w-4);}
 if(!strncmp(s,"Invert Y axis",13))strcpy(invert_label,s);
 if(x==252)strcpy(sens_value,s); /* the value beside the sensitivity rail */
 if(x==10 && y==176)strcpy(help,s);
 if(!strncmp(s,"Far detail",10)){strcpy(far_label,s);assert(AW_UIWidth(s)<=w-4);}
 if(!strncmp(s,"Fog ",4)){if(s[4]=='i')strcpy(room_fog_label,s);else if(!strncmp(s,"Fog distance indoors",20))strcpy(indoor_label,s);}
 if(!strcmp(s,"Photo mode") || !strcmp(s,"Leave photo mode")){strcpy(photo_label,s);photo_colour=c;}}
/* Photo mode and the crosshair preference (aw_photo.c). */
static int crosshair_on=1,photo_on,photo_available=1,photo_sets,crosshair_style[2];
int AW_CrosshairShown(void){return crosshair_on;}
void AW_CrosshairSet(int on){crosshair_on=on;}
int AW_CrosshairStyleCount(int shape){return shape?4:4;}
int AW_CrosshairStyle(int shape){return crosshair_style[shape];}
const char *AW_CrosshairStyleName(int shape,int value){
 static const char *colours_[]={"Warm white","Yellow","Green","Blue"},*shapes[]={"Cross","Open cross","Small cross","Dot"};
 return shape?shapes[value]:colours_[value];}
void AW_CrosshairStyleSet(int shape,int value){int n=AW_CrosshairStyleCount(shape);crosshair_style[shape]=((value%n)+n)%n;}
void AW_CrosshairDraw(int x,int y){preview_x=x;previews++;assert(y>=36 && y+8<=36+7*19);}
/* Quake's sensitivity in tenths (aw_photo.c); the shipped default is 3. */
static int sens_tenths=30;
int AW_SensitivityTenths(void){return sens_tenths;}
void AW_SensitivitySetTenths(int t){assert(t>=1 && t<=200);sens_tenths=t;}
int AW_PhotoModeActive(void){return photo_on;}
int AW_PhotoModeAvailable(void){return photo_available;}
int AW_PhotoModeSet(int on){assert(key_dest==key_game);photo_on=on;photo_sets++;return 1;}
void AW_UIBox(int x,int y,int w,int h){assert(x>=0 && y>=0 && x+w<=320 && y+h<=200);boxes++;if(!x && !y && w==320 && h==200)full_box++;}
void AW_MusicTitle(void){}
void AW_MusicTitleAfter(double seconds){(void)seconds;}
void AW_MenuMouse(int,int);
static void open_pause(void){M_Menu_Main_f();mx=160;my=63;}
static void click(int x,int y){AW_MenuMouse(x-mx,y-my);mx=x;my=y;M_Keydown(K_MOUSE1);}
/* Options opens on the tab row of the page last shown; a click picks a page. */
static void open_options(void){open_pause();click(100,54+4*19+18);mx=160;my=100;M_Draw();}
static void page(int n){click(8+n*76+10,6+5);M_Draw();assert(highlight_y==9 && highlight_w==66);}   /* the tab is highlighted */
static void wiggle(void){AW_MenuMouse(1,0);mx++;}
static void down(int n){while(n--)M_Keydown(K_DOWNARROW);M_Draw();}
static void up(int n){while(n--)M_Keydown(K_UPARROW);M_Draw();}
/* The panel: edge to edge, four framed tabs, one framed group, Back; the world is not drawn. */
static void check_layout(void){
 open_options();assert(aw_menu_fullscreen && aw_menu_fullscreen());
 boxes=full_box=tabs_drawn=0;M_Draw();
 assert(full_box==1 && tabs_drawn==4 && boxes==1+4+1+1);
 assert(!strcmp(help,"Left/Right: page   Down: settings"));
 M_Keydown(K_ESCAPE);assert(!aw_menu_fullscreen() && key_dest==key_menu);
 M_Draw();highlight_y=0;M_Keydown(K_ENTER);M_Draw();assert(aw_menu_fullscreen()); /* Options stays selected */
 M_Keydown(K_ESCAPE);M_Keydown(K_ESCAPE);assert(key_dest==key_game && !aw_menu_fullscreen());
}
/* Prefs: Show crosshairs, crosshair colour and shape (with a preview), then the HUD and
 * interface rows that used to be top level or under Interface... */
static void check_prefs(void){
 int i;
 open_options();page(0);
 down(1);assert(!strcmp(crosshair_label,"Show crosshairs: On") && highlight_y==36 && highlight_w==280);
 M_Keydown(K_ENTER);assert(!crosshair_on);M_Draw();assert(!strcmp(crosshair_label,"Show crosshairs: Off"));
 M_Keydown(K_RIGHTARROW);assert(crosshair_on);M_Keydown(K_LEFTARROW);assert(!crosshair_on);M_Keydown(K_ENTER);assert(crosshair_on);
 previews=0;down(1);assert(!strcmp(colour_label,"Crosshair colour: Warm white") && highlight_y==55);
 assert(previews==2 && preview_x==14+280-16);
 M_Keydown(K_RIGHTARROW);M_Draw();assert(!strcmp(colour_label,"Crosshair colour: Yellow"));
 M_Keydown(K_LEFTARROW);M_Keydown(K_LEFTARROW);M_Draw();assert(!strcmp(colour_label,"Crosshair colour: Blue"));
 M_Keydown(K_ENTER);M_Draw();assert(!strcmp(colour_label,"Crosshair colour: Warm white"));
 down(1);M_Keydown(K_RIGHTARROW);M_Draw();assert(!strcmp(shape_label,"Crosshair shape: Open cross") && highlight_y==74);
 M_Keydown(K_LEFTARROW);
 /* Mouse cursor (CURSOR-MW-58), under the crosshair's rows: Morrowind's by default; Enter and the arrows switch
  * between Morrowind and AmiWind (aw_cursor_type 2 / 1). Morrowind's is drawn by aw_ui.c; with AmiWind's, or when
  * the image has no Morrowind cursor, the menu draws its own. */
 down(1);assert(!strcmp(cursor_label,"Mouse cursor: Morrowind") && highlight_y==93);
 /* A key hides the pointer; a small move over the tab row shows it again without changing the selected row. */
 cursor_calls=own_cursor=0;M_Draw();assert(!cursor_calls && !own_cursor);
 wiggle();M_Draw();assert(cursor_calls==1 && !own_cursor && highlight_y==93);
 M_Keydown(K_ENTER);wiggle();M_Draw();assert(cursor_kind==1 && !strcmp(cursor_label,"Mouse cursor: AmiWind") && own_cursor==1);
 M_Keydown(K_RIGHTARROW);wiggle();M_Draw();assert(cursor_kind==2 && !strcmp(cursor_label,"Mouse cursor: Morrowind") && own_cursor==1);
 M_Keydown(K_LEFTARROW);assert(cursor_kind==1);M_Keydown(K_LEFTARROW);assert(cursor_kind==2);
 cursor_art=0;wiggle();M_Draw();assert(own_cursor==2 && !strcmp(cursor_label,"Mouse cursor: Morrowind"));cursor_art=1;
 assert(highlight_y==93);
 down(1);M_Keydown(K_ENTER);assert(gold_frame);M_Keydown(K_ENTER);assert(!gold_frame);
 down(1); /* UI font */
 down(1);M_Keydown(K_ENTER);assert(AW_UIVoiceNames());
 down(1);M_Keydown(K_RIGHTARROW);assert(AW_UIDialogueMethod()==3);
 /* Text box: type 2 by default (SUBTITLE-BOX-HIDES-STATS-63); Enter or an arrow switches the one saved value */
 down(1);assert(AW_UITextBoxType()==2);M_Keydown(K_ENTER);assert(AW_UITextBoxType()==1);
 M_Keydown(K_RIGHTARROW);assert(AW_UITextBoxType()==2);
 /* Topic colours (TOPIC-COLOURS-62): on by default, Enter switches them */
 down(1);assert(AW_DialTopicColours());M_Keydown(K_ENTER);assert(!AW_DialTopicColours());M_Keydown(K_ENTER);assert(AW_DialTopicColours());
 down(1);M_Keydown(K_ENTER);assert(!AW_SceneUIOption(0,0));
 down(1);assert(scroll_top==5 && highlight_y==36+6*19);M_Keydown(K_RIGHTARROW);assert(AW_SceneUIOption(1,0)==3);
 down(1);M_Keydown(K_RIGHTARROW);assert(AW_SceneUIOption(2,0)==2);
 /* Name labels (INFO-BOX-TEXT-CUT-62): AmiWind by default, Enter or an arrow switches to Morrowind and back */
 down(1);assert(AW_SceneUIOption(3,0)==1);M_Keydown(K_ENTER);assert(AW_SceneUIOption(3,0)==0);M_Keydown(K_RIGHTARROW);assert(AW_SceneUIOption(3,0)==1);
 /* Always use best attack (BEST-ATTACK-OPTION-62): on by default; Enter or an arrow switches the one saved value */
 down(1);assert(!strcmp(best_label,"Always use best attack: On") && best_attack==1);
 M_Keydown(K_ENTER);M_Draw();assert(best_attack==0 && !strcmp(best_label,"Always use best attack: Off"));
 M_Keydown(K_RIGHTARROW);M_Draw();assert(best_attack==1 && !strcmp(best_label,"Always use best attack: On"));
 best_attack=0;M_Draw();assert(!strcmp(best_label,"Always use best attack: Off"));best_attack=1;   /* a console change shows at once */
 down(1);assert(scroll_total==16 && scroll_top==9 && highlight_y==150); /* Autosave history, the last row (16 rows: topic colours, name labels, best attack, text box) */
 /* Past the last row: Back, which holds; Up returns to the last row, Up past the first to the tabs. */
 down(3);assert(highlight_y==179 && highlight_w==74 && !strcmp(help,"Enter: back to the menu"));
 up(1);assert(highlight_y==150 && highlight_w==280);
 for(i=0;i<24;i++)M_Keydown(K_MWHEELUP);
 M_Draw();assert(scroll_top==0 && highlight_y==9 && highlight_w==66);
 M_Keydown(K_ENTER);M_Draw();assert(highlight_y==36); /* Enter on the tabs: the first row */
 click(240,180);assert(key_dest==key_menu && !aw_menu_fullscreen()); /* Back */
 M_Keydown(K_ESCAPE);
}
/* Controls: Mouse sensitivity (default 3.0, 0.5 steps, Shift 0.1, 0.5..10, drag), Invert Y axis,
 * the key bindings: the raw key is captured (W is not turned into Up), a third key replaces both,
 * Escape cancels, Delete clears and the cursor skips planned rows; the combat options. */
static void check_controls(void){
 int i;
 keybindings['w']="+forward";keybindings[K_UPARROW]="+forward";keybindings[K_F9]="aw_quickload";
 open_options();page(2);
 down(1);assert(highlight_y==36 && !strcmp(sens_value,"3.0") && sens_tenths==30);
 assert(!strcmp(help,"Arrows / drag   Shift: fine"));
 M_Keydown(K_RIGHTARROW);assert(sens_tenths==35);M_Keydown(K_LEFTARROW);M_Keydown(K_LEFTARROW);assert(sens_tenths==25);
 keydown[K_SHIFT]=true;M_Keydown(K_RIGHTARROW);keydown[K_SHIFT]=false;assert(sens_tenths==26);
 M_Keydown(K_LEFTARROW);assert(sens_tenths==25);M_Keydown(K_RIGHTARROW);M_Keydown(K_RIGHTARROW);assert(sens_tenths==35);
 M_Keydown(K_HOME);assert(sens_tenths==5);M_Keydown(K_LEFTARROW);assert(sens_tenths==5);
 M_Keydown(K_END);assert(sens_tenths==100);M_Keydown(K_RIGHTARROW);assert(sens_tenths==100);M_Draw();assert(!strcmp(sens_value,"10.0"));
 /* A console value outside the menu's range shows as is; a step brings it back in. */
 sens_tenths=2;M_Draw();assert(!strcmp(sens_value,"0.2"));M_Keydown(K_RIGHTARROW);assert(sens_tenths==5);
 /* The rail: a click sets the nearest 0.5, a drag follows outside the rail, release stops. */
 click(170+38,36+9);assert(sens_tenths==55);keydown[K_MOUSE1]=true;
 AW_MenuMouse(1000,0);mx=319;assert(sens_tenths==100);AW_MenuMouse(-1000,0);mx=0;assert(sens_tenths==5);
 keydown[K_MOUSE1]=false;AW_MenuMouse(100,0);mx=100;assert(sens_tenths==5);
 sens_tenths=30;
 down(1);assert(!strcmp(invert_label,"Invert Y axis: Off"));M_Keydown(K_ENTER);assert(pitch_value<0);M_Draw();
 assert(!strcmp(invert_label,"Invert Y axis: On"));M_Keydown(K_RIGHTARROW);assert(pitch_value>0);
 down(1);assert(highlight_y==74 && !strcmp(help,"Enter: set   Del: clear")); /* Forward */
 M_Keydown(K_ENTER);M_Draw();assert(!strcmp(help,"Press a key   Esc: cancel"));M_Keydown('k');
 assert(!strcmp(keybindings['k'],"+forward") && !*keybindings['w'] && !*keybindings[K_UPARROW]);
 M_Keydown(K_ENTER);M_Keydown(K_ESCAPE);assert(key_dest==key_menu && aw_menu_fullscreen() && !strcmp(keybindings['k'],"+forward"));
 M_Keydown(K_ENTER);M_Keydown('W');assert(!strcmp(keybindings['w'],"+forward") && !strcmp(keybindings['k'],"+forward"));
 M_Keydown(K_DEL);assert(!*keybindings['w'] && !*keybindings['k']);
 for(i=0;i<40;i++)M_Keydown(K_DOWNARROW);
 up(1);assert(highlight_y==150 && scroll_total==32 && scroll_top==25); /* Reset to defaults is the last row (Stats, Magic and Sneak rows included) */
 M_Keydown(K_ENTER);assert(!strcmp(queued,"exec keymaps-default.cfg\n"));changes--;
 /* Weapon sway above it (FP-WEAPON-SWAY-61): Enter and the arrows switch AmiWind groove / Morrowind stiff */
 M_Keydown(K_UPARROW);M_Keydown(K_ENTER);assert(fp_sway==2);M_Draw();M_Keydown(K_RIGHTARROW);assert(fp_sway==1);
 /* Blocking, Dice rolls, Combat style above it: Enter and the arrows switch the three options */
 M_Keydown(K_UPARROW);M_Keydown(K_ENTER);assert(combat_block==1 && combat_dice==1 && combat_miss==1);
 M_Keydown(K_RIGHTARROW);assert(combat_block==0);
 M_Keydown(K_UPARROW);M_Keydown(K_ENTER);assert(combat_dice==0 && combat_miss==1);
 M_Keydown(K_RIGHTARROW);assert(combat_dice==1);
 M_Keydown(K_UPARROW);M_Keydown(K_ENTER);assert(combat_miss==0);M_Draw();M_Keydown(K_LEFTARROW);assert(combat_miss==1);
 M_Keydown(K_UPARROW);M_Draw(); /* the planned rows are skipped: Magic (the placeholder window, O) and Stats (P) are bindable like the inventory */
 M_Keydown(K_ENTER);M_Keydown('o');assert(!strcmp(keybindings['o'],"aw_magicmenu"));
 M_Keydown(K_UPARROW);M_Draw();
 M_Keydown(K_ENTER);M_Keydown('p');assert(!strcmp(keybindings['p'],"aw_stats"));
 M_Keydown(K_UPARROW);M_Draw(); /* Inventory */
 M_Keydown(K_ENTER);M_Keydown('i');assert(!strcmp(keybindings['i'],"aw_inventory"));
 M_Keydown(K_UPARROW);M_Draw(); /* Quick load remains independently bindable. */
 M_Keydown(K_ENTER);M_Keydown('q');assert(!strcmp(keybindings['q'],"aw_quickload"));
 M_Keydown(K_ESCAPE);M_Draw();M_Keydown(K_ESCAPE);M_Keydown(K_ESCAPE);assert(key_dest==key_game);
 for(i=0;i<256;i++)keybindings[i]=NULL;
}
/* Video: fog, reset, far detail, photo mode (closes the menu first, greyed and inert on the title
 * screen or without a running game), area loading, load method, read-ahead buffer, extra RAM. */
static void check_video(void){
 open_options();page(3);
 down(1);M_Keydown('a');assert(distance==530);keydown[K_SHIFT]=true;M_Keydown('D');assert(distance==531);keydown[K_SHIFT]=false;
 M_Keydown('s');M_Keydown(K_ENTER);assert(distance==300);   /* reset = the universal default 300 */
 /* Fog distance indoors (aw_fog_distance_interior, its own value; 300 by default): arrows 10, Enter steps */
 down(1);M_Draw();assert(!strcmp(indoor_label,"Fog distance indoors: 300") && highlight_y==36+2*19);
 M_Keydown(K_RIGHTARROW);assert(fog_indoors==310 && distance==300);M_Keydown(K_ENTER);assert(fog_indoors==540);
 M_Keydown(K_ENTER);M_Keydown(K_ENTER);assert(fog_indoors==150);M_Keydown(K_ENTER);assert(fog_indoors==300);
 /* Fog in large rooms (aw_fog_large_rooms): on by default, Enter or an arrow switches */
 down(1);M_Draw();assert(!strcmp(room_fog_label,"Fog in large rooms: On"));
 M_Keydown(K_ENTER);M_Draw();assert(fog_large_rooms==0 && !strcmp(room_fog_label,"Fog in large rooms: Off"));
 M_Keydown(K_RIGHTARROW);assert(fog_large_rooms==1);
 /* Far detail: plain names, Enter and the arrows step Full, Light, Strong,
  * Strong + small faces (aw_cull 1, 3, 4, 6); a console-only value reads Custom. */
 down(1);assert(!strcmp(far_label,"Far detail: Strong") && highlight_y==36+4*19);
 M_Keydown(K_ENTER);M_Draw();assert(far_detail==6 && !strcmp(far_label,"Far detail: Strong + small faces"));
 M_Keydown(K_ENTER);M_Draw();assert(far_detail==1 && !strcmp(far_label,"Far detail: Full"));
 M_Keydown(K_RIGHTARROW);M_Draw();assert(far_detail==3 && !strcmp(far_label,"Far detail: Light"));
 M_Keydown(K_LEFTARROW);M_Keydown(K_LEFTARROW);assert(far_detail==6);
 far_detail=2;M_Draw();assert(!strcmp(far_label,"Far detail: Custom"));
 M_Keydown(K_RIGHTARROW);assert(far_detail==1);M_Keydown(K_RIGHTARROW);M_Keydown(K_RIGHTARROW);assert(far_detail==4 && far_sets==8);
 down(1);photo_available=0;M_Draw();assert(!strcmp(photo_label,"Photo mode") && photo_colour==114);
 M_Keydown(K_ENTER);assert(key_dest==key_menu && !photo_sets);
 photo_available=1;M_Draw();assert(photo_colour==210 && highlight_y==36+5*19);
 M_Keydown(K_ENTER);assert(key_dest==key_game && photo_on && photo_sets==1 && !aw_menu_fullscreen());
 open_options();down(6);assert(!strcmp(photo_label,"Leave photo mode")); /* the page is kept */
 M_Keydown(K_ENTER);assert(key_dest==key_game && !photo_on && photo_sets==2);
 open_options();down(7);M_Keydown(K_ENTER);assert(!frozen_loading); /* Area loading */
 M_Keydown(K_LEFTARROW);assert(frozen_loading);M_Keydown(K_RIGHTARROW);assert(!frozen_loading);
 click(100,36+6*19+18);assert(frozen_loading); /* final pixel of the loading row */
 down(1);M_Keydown(K_ENTER);M_Draw();assert(AW_CellChangeMethod()==2);
 down(1);M_Keydown(K_ENTER);assert(AW_StreamOption(1,0)==256);
 M_Keydown(K_RIGHTARROW);assert(AW_StreamOption(1,0)==512);
 down(1);M_Keydown(K_ENTER);M_Draw();assert(autoram==0 && scroll_total==11 && scroll_top==3); /* Extra RAM: Off (11 rows: the indoor fog rows and Tree crowns) */
 M_Keydown(K_RIGHTARROW);assert(autoram==1);M_Keydown(K_LEFTARROW);assert(autoram==0);M_Keydown(K_ENTER);assert(autoram==1);
 /* Tree crowns, the last row (TREES-DEPTH-56): original (0, the default), fast (1), sprite (2), round again */
 down(1);assert(tree_crowns==0);M_Keydown(K_ENTER);assert(tree_crowns==1);M_Keydown(K_RIGHTARROW);assert(tree_crowns==2);
 M_Keydown(K_RIGHTARROW);assert(tree_crowns==0);M_Keydown(K_LEFTARROW);assert(tree_crowns==2);M_Keydown(K_ENTER);
 assert(tree_crowns==0);
 M_Keydown(K_ESCAPE);M_Keydown(K_ESCAPE);
}
/* The title screen: the same panel; Photo mode greyed and inert. */
static void check_title_options(void){
 front();M_Keydown(K_DOWNARROW);M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);M_Draw();assert(aw_menu_fullscreen());
 down(4);assert(photo_colour==114);M_Keydown(K_ENTER);assert(photo_sets==2 && key_dest==key_menu);
 M_Keydown(K_ESCAPE);M_Draw();assert(!aw_menu_fullscreen() && key_dest==key_menu);
 M_Keydown(K_ENTER);M_Draw();assert(aw_menu_fullscreen()); /* Options stays selected on the title */
 AW_MenuMouse(10000,10000);M_Draw();AW_MenuMouse(-10000,-10000);M_Draw(); /* the pointer stays on the screen */
 M_Keydown(K_ESCAPE);
}
cvar_t aw_drawdistance={"aw_drawdistance","540",true,false,540};
int main(void){
 vid.width=320;vid.height=200;vid.rowbytes=320;vid.buffer=pixels;sv.active=true;
 M_Init();assert(picker && front && aw_menu_fullscreen && !aw_menu_fullscreen());
 key_dest=key_game;open_pause();M_Draw();assert(scr_copyeverything && !aw_menu_fullscreen());M_Keydown(K_ESCAPE);assert(key_dest==key_game);
 /* Exact row boundaries are also the click boundaries; unavailable rows do nothing. */
 open_pause();click(100,54+2*19+18);assert(key_dest==key_menu && !changes);
 click(100,54+3*19);assert(key_dest==key_menu && !changes);
 click(100,54+1*19);M_Draw();assert(!changes && key_dest==key_menu);
 /* New Game defaults to acceptance; Esc and explicit Cancel still return. */
 M_Keydown(K_ESCAPE);assert(!changes);M_Keydown(K_ENTER);M_Keydown(K_LEFTARROW);M_Keydown(K_ENTER);assert(!changes);
 M_Keydown(K_ENTER);M_Keydown(K_ENTER);
 assert(changes==1 && !strcmp(queued,"aw_new_game\n") && key_dest==key_game);
 check_layout();
 check_prefs();
 check_controls();
 check_video();
 /* Main menu from the pause menu, the front end, the scene picker, quit. */
 open_pause();M_Keydown(K_UPARROW);M_Keydown(K_ENTER);M_Draw();M_Keydown(K_ENTER);
 M_Keydown(K_ENTER);M_Keydown(K_RIGHTARROW);M_Keydown(K_ENTER);
 assert(changes==2 && !strcmp(queued,"disconnect\naw_main_menu\n"));
 front();mx=160;my=63;M_Draw();M_Keydown(K_ESCAPE);assert(key_dest==key_menu);
 click(80,148);assert(changes==2); /* Load opens its own browser */
 click(80,132);assert(changes==2);M_Draw(); /* confirm New Game */
 M_Keydown(K_ESCAPE);M_Keydown(K_ENTER);M_Keydown(K_ENTER);
 assert(changes==3 && !strcmp(queued,"aw_new_game\n") && key_dest==key_game);
 key_dest=key_console;picker();M_Draw();M_Keydown(K_ESCAPE);assert(key_dest==key_console);
 picker();M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);assert(changes==4 && !strcmp(queued,"aw_scene town\n"));
 missing=1;picker();M_Draw();M_Keydown(K_ENTER);assert(changes==4 && key_dest==key_game);missing=0;
 M_Menu_Quit_f();M_Draw();M_Keydown(K_ENTER);assert(!quit);M_Menu_Quit_f();M_Keydown(K_RIGHTARROW);M_Keydown(K_ENTER);assert(quit==1);
 check_title_options();
 open_pause();AW_MenuMouse(10000,10000);M_Draw();AW_MenuMouse(-10000,-10000);M_Draw();
 return 0;
}

int AW_UIFontSize(void){return 14;}
int AW_UISetFontSize(int n){return 1;}
int AW_SaveAllowed(void){return 0;}
int AW_SaveMenuOpen(int n){return 1;}
int AW_SaveMenuKey(int key){return 0;}
int AW_SaveMenuActive(void){return 0;}
void AW_SaveMenuDraw(void){}
int AW_AutosaveCount(void){return 3;}
void AW_SetAutosaveCount(int n){}

int AW_TravelDraw(void){return 0;}
int AW_WaitDraw(void){return 0;}
static int load_method=1,buffer_index;
int AW_CellChangeMethod(void){return load_method;}
int AW_StreamOption(int option,int step){static const int sizes[]={128,256,512};if(!option){if(step)load_method=3-load_method;return load_method;}if(step)buffer_index=(buffer_index+(step>0?1:2))%3;return sizes[buffer_index];}

static int voices,dialogue=2,scene_options[]={1,2,1,1};
int AW_UIVoiceStyle(void){return 1;}
int AW_UIVoiceNames(void){return voices;}void AW_UIVoiceNamesToggle(void){voices=!voices;}
int AW_UIDialogueMethod(void){return dialogue;}void AW_UIDialogueCycle(int step){dialogue=(dialogue-1+step+4)%4+1;}
static int text_box=2;int AW_UITextBoxType(void){return text_box;}void AW_UITextBoxTypeSet(int type){text_box=type==1?1:2;}
static int topic_colours=1;int AW_DialTopicColours(void){return topic_colours;}void AW_DialTopicColoursToggle(void){topic_colours=!topic_colours;}
int AW_SceneUIOption(int n,int change){if(change)scene_options[n]=n && n!=3?(scene_options[n]-1+change+3)%3+1:!scene_options[n];return scene_options[n];}

int AW_WorldUIDraw(void){return 0;}
