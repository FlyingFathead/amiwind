/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
keydest_t key_dest;qboolean keydown[256];viddef_t vid;server_t sv;int scr_copyeverything;
char *keybindings[256];
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
static int audio_sets,audio_draws;
static int highlight_y,highlight_w,scroll_top,scroll_total;
void Cvar_SetValue(char *name,float value){cvar_t *rows[]={&volume,&bgmvolume,&effectsvolume,&dialoguevolume};int i;assert(value>=0 && value<=1);for(i=0;i<4;i++)if(!strcmp(rows[i]->name,name)){rows[i]->value=value;audio_sets++;return;}assert(0);}
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
void AW_UIFill(int x,int y,int w,int h,int c){if(c==62){highlight_y=y;highlight_w=w;}}
void AW_UIScrollbar(int x,int y,int h,int total,int visible,int top){assert(x>=0 && x+10<=320 && y+h<=200);assert(top>=0 && top+visible<=total);scroll_top=top;scroll_total=total;}
int AW_UIScrollHit(int mx,int my,int x,int y,int h,int total,int visible,int top){return -1;}
static char crosshair_label[64],photo_label[64];static int photo_colour;
void AW_UITextBox(int x,int y,int w,int h,const char *s,int c){assert(y>=0 && y+h<=200);if(!strcmp(s,"Audio"))audio_draws++;
 if(!strncmp(s,"Show crosshairs",15))strcpy(crosshair_label,s);
 if(!strcmp(s,"Photo mode") || !strcmp(s,"Leave photo mode")){strcpy(photo_label,s);photo_colour=c;}}
/* Photo mode and the crosshair preference (aw_photo.c). */
static int crosshair_on=1,photo_on,photo_available=1,photo_sets;
int AW_CrosshairShown(void){return crosshair_on;}
void AW_CrosshairSet(int on){crosshair_on=on;}
int AW_PhotoModeActive(void){return photo_on;}
int AW_PhotoModeAvailable(void){return photo_available;}
int AW_PhotoModeSet(int on){assert(key_dest==key_game);photo_on=on;photo_sets++;return 1;}
void AW_UIBox(int x,int y,int w,int h){assert(x>=0 && y>=0 && x+w<=320 && y+h<=200);}
void AW_MusicTitle(void){}
void AW_MusicTitleAfter(double seconds){(void)seconds;}
void AW_MenuMouse(int,int);
static void open_pause(void){M_Menu_Main_f();mx=160;my=63;}
static void click(int x,int y){AW_MenuMouse(x-mx,y-my);mx=x;my=y;M_Keydown(K_MOUSE1);}
/* Options > Controls: the raw key is captured (W is not turned into Up),
 * a third key replaces both, Escape cancels, Delete clears and the cursor
 * skips planned rows. */
static void check_controls(void){
 int i;
 keybindings['w']="+forward";keybindings[K_UPARROW]="+forward";keybindings[K_F9]="aw_quickload";
 open_pause();click(100,54+4*19+18);mx=160;my=100;M_Draw();
 for(i=0;i<7;i++)M_Keydown(K_DOWNARROW);
 M_Keydown(K_ENTER);M_Draw();assert(highlight_y==54); /* Forward */
 M_Keydown(K_ENTER);M_Draw();M_Keydown('k');
 assert(!strcmp(keybindings['k'],"+forward") && !*keybindings['w'] && !*keybindings[K_UPARROW]);
 M_Keydown(K_ENTER);M_Keydown(K_ESCAPE);assert(key_dest==key_menu && !strcmp(keybindings['k'],"+forward"));
 M_Keydown(K_ENTER);M_Keydown('W');assert(!strcmp(keybindings['w'],"+forward") && !strcmp(keybindings['k'],"+forward"));
 M_Keydown(K_DEL);assert(!*keybindings['w'] && !*keybindings['k']);
 for(i=0;i<40;i++)M_Keydown(K_DOWNARROW);
 M_Draw();assert(highlight_y==149);  /* Back is the last row */
 M_Keydown(K_UPARROW);M_Keydown(K_UPARROW);M_Draw(); /* past Reset, over planned rows */
 M_Keydown(K_ENTER);M_Keydown('q');assert(!strcmp(keybindings['q'],"aw_quickload"));
 M_Keydown(K_ESCAPE);M_Draw();M_Keydown(K_ESCAPE);M_Keydown(K_ESCAPE);M_Keydown(K_ESCAPE);
 for(i=0;i<256;i++)keybindings[i]=NULL;
}
/* Options > Show crosshairs (the saved crosshair preference) and Options >
 * Photo mode: closes the menu first, toggles to Leave photo mode, greyed and
 * inert on the title screen or without a running game. */
static void open_options(void){open_pause();click(100,54+4*19+18);mx=160;my=100;M_Draw();}
static void check_photo_rows(void){
 int i;
 open_options();for(i=0;i<3;i++)M_Keydown(K_DOWNARROW);
 M_Draw();assert(!strcmp(crosshair_label,"Show crosshairs: On") && highlight_y==54+3*19);
 M_Keydown(K_ENTER);assert(!crosshair_on);M_Draw();assert(!strcmp(crosshair_label,"Show crosshairs: Off"));
 M_Keydown(K_RIGHTARROW);assert(crosshair_on);M_Keydown(K_LEFTARROW);assert(!crosshair_on);
 M_Keydown(K_ENTER);assert(crosshair_on && key_dest==key_menu);
 M_Keydown(K_DOWNARROW);photo_available=0;M_Draw();assert(!strcmp(photo_label,"Photo mode") && photo_colour==114);
 M_Keydown(K_ENTER);assert(key_dest==key_menu && !photo_sets);
 photo_available=1;M_Draw();assert(photo_colour==210 && highlight_y==54+4*19);
 M_Keydown(K_ENTER);assert(key_dest==key_game && photo_on && photo_sets==1);
 open_options();for(i=0;i<4;i++)M_Keydown(K_DOWNARROW);
 M_Draw();assert(!strcmp(photo_label,"Leave photo mode"));
 M_Keydown(K_ENTER);assert(key_dest==key_game && !photo_on && photo_sets==2);
 front();M_Keydown(K_DOWNARROW);M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);
 for(i=0;i<4;i++)M_Keydown(K_DOWNARROW);
 M_Draw();assert(photo_colour==114);M_Keydown(K_ENTER);assert(photo_sets==2 && key_dest==key_menu);
 M_Keydown(K_ESCAPE);M_Keydown(K_ESCAPE);
}
static void check_setup_endpoints(void){
 int i,j,down[]={K_DOWNARROW,K_MWHEELDOWN,'s',K_TAB},up[]={K_UPARROW,K_MWHEELUP,'w'};
 front();M_Keydown(K_DOWNARROW);M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);
 for(j=0;j<4;j++){
  for(i=0;i<24;i++)M_Keydown(down[j]);
  M_Draw();assert(scroll_total==13 && scroll_top==6 && highlight_y==168 && highlight_w==230);
  M_Keydown(K_UPARROW);M_Draw();assert(scroll_top==6 && highlight_y==149);
  for(i=0;i<24;i++)M_Keydown(up[j%3]);
  M_Draw();assert(scroll_top==0 && highlight_y==54 && highlight_w==230);
  M_Keydown(K_DOWNARROW);M_Draw();assert(scroll_top==0 && highlight_y==73);
 }
 /* Reversing at either end works; the Interface subpanel shares the rule. */
 M_Keydown(K_DOWNARROW);M_Keydown(K_DOWNARROW);M_Keydown(K_DOWNARROW);M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);
 for(i=0;i<24;i++)M_Keydown(K_MWHEELUP);
 M_Draw();assert(highlight_y==54 && highlight_w==232);
 for(i=0;i<24;i++)M_Keydown(K_DOWNARROW);
 M_Draw();assert(highlight_y==168 && highlight_w==232);
 M_Keydown(K_UPARROW);M_Draw();assert(highlight_y==149);
 for(i=0;i<24;i++)M_Keydown(K_UPARROW);
 M_Keydown(K_DOWNARROW);M_Draw();assert(highlight_y==73);
 M_Keydown(K_ESCAPE);M_Keydown(K_ESCAPE);
}
cvar_t aw_drawdistance={"aw_drawdistance","540",true,false,540};
int main(void){
 vid.width=320;vid.height=200;vid.rowbytes=320;vid.buffer=pixels;sv.active=true;
 M_Init();assert(picker && front);
 key_dest=key_game;open_pause();M_Draw();assert(scr_copyeverything);M_Keydown(K_ESCAPE);assert(key_dest==key_game);
 /* Exact row boundaries are also the click boundaries; unavailable rows do nothing. */
 open_pause();click(100,54+2*19+18);assert(key_dest==key_menu && !changes);
 click(100,54+3*19);assert(key_dest==key_menu && !changes);
 click(100,54+1*19);M_Draw();assert(!changes && key_dest==key_menu);
 /* New Game defaults to acceptance; Esc and explicit Cancel still return. */
 M_Keydown(K_ESCAPE);assert(!changes);M_Keydown(K_ENTER);M_Keydown(K_LEFTARROW);M_Keydown(K_ENTER);assert(!changes);
 M_Keydown(K_ENTER);M_Keydown(K_ENTER);
 assert(changes==1 && !strcmp(queued,"aw_new_game\n") && key_dest==key_game);
 open_pause();click(100,54+4*19+18);mx=160;my=100;M_Draw(); /* last pixel in Options */
 M_Keydown('a');assert(distance==530);keydown[K_SHIFT]=true;M_Keydown('D');assert(distance==531);keydown[K_SHIFT]=false;
 M_Keydown('s');M_Keydown(K_ENTER);assert(distance==540);
 M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);assert(gold_frame);
 M_Keydown(K_ENTER);assert(!gold_frame);
 M_Keydown(K_DOWNARROW);M_Keydown(K_DOWNARROW); /* Show crosshairs, Photo mode: check_photo_rows */
 M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);M_Draw(); /* Interface */
 M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);assert(AW_UIVoiceNames());
 M_Keydown(K_DOWNARROW);M_Keydown(K_RIGHTARROW);assert(AW_UIDialogueMethod()==3);
 M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);assert(!AW_SceneUIOption(0,0));
 M_Keydown(K_DOWNARROW);M_Keydown(K_RIGHTARROW);assert(AW_SceneUIOption(1,0)==3);
 M_Keydown(K_DOWNARROW);M_Keydown(K_RIGHTARROW);assert(AW_SceneUIOption(2,0)==2);
 M_Draw();M_Keydown(K_ESCAPE);
 M_Keydown(K_DOWNARROW);M_Keydown(K_DOWNARROW);M_Keydown(K_DOWNARROW);M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);assert(!frozen_loading);
 M_Keydown(K_LEFTARROW);assert(frozen_loading);M_Keydown(K_RIGHTARROW);assert(!frozen_loading);
 click(100,168+18);assert(frozen_loading); /* final pixel of the loading row */
 M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);M_Draw();assert(AW_CellChangeMethod()==2); /* scrolled loading method */
 M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);assert(AW_StreamOption(1,0)==256);
 M_Keydown(K_RIGHTARROW);assert(AW_StreamOption(1,0)==512);
 M_Keydown(K_DOWNARROW);M_Draw();M_Keydown(K_ENTER); /* scrolled Back */
 M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);M_Draw();M_Keydown(K_ENTER);assert(changes==1);
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
 open_pause();AW_MenuMouse(10000,10000);M_Draw();AW_MenuMouse(-10000,-10000);M_Draw();
 check_controls();
 check_photo_rows();
 check_setup_endpoints();
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

static int voices,dialogue=2,scene_options[]={1,2,1};
int AW_UIVoiceStyle(void){return 1;}
int AW_UIVoiceNames(void){return voices;}void AW_UIVoiceNamesToggle(void){voices=!voices;}
int AW_UIDialogueMethod(void){return dialogue;}void AW_UIDialogueCycle(int step){dialogue=(dialogue-1+step+4)%4+1;}
int AW_SceneUIOption(int n,int change){if(change)scene_options[n]=n?(scene_options[n]-1+change+3)%3+1:!scene_options[n];return scene_options[n];}

int AW_WorldUIDraw(void){return 0;}
