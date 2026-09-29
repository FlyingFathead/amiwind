/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
keydest_t key_dest;qboolean keydown[256];viddef_t vid;server_t sv;int scr_copyeverything;
byte pixels[320*200];int clears,quit,changes,missing,intro_missing;
static int distance=540,gold_frame;
static void (*picker)(void),(*front)(void);static char queued[64];
static int mx=160,my=63;
int AW_UIFrameEnabled(void){return gold_frame;}
void AW_UIFrameToggle(void){gold_frame=!gold_frame;}
int AW_DrawDistance(void){return distance;}
void AW_SetDrawDistance(int n){if(n<128)n=128;if(n>1400)n=1400;distance=n;}
int Cmd_Argc(void){return 1;}
void Con_Printf(char *fmt,...){}
int COM_FOpenFile(char *name,FILE **f){if(missing || (intro_missing && !strcmp(name,"intro/chargenname1.txt"))){*f=NULL;return -1;}*f=tmpfile();return 124;}
void IN_AWClearButtons(void){clears++;}
void Cmd_AddCommand(char *name,void (*fn)(void)){if(!strcmp(name,"aw_scene_menu"))picker=fn;else if(!strcmp(name,"aw_main_menu"))front=fn;}
void Cbuf_AddText(char *s){if(!strcmp(s,"quit\n"))quit++;else{strcpy(queued,s);changes++;}}
int AW_UIBackground(void){return 1;}int AW_UILogo(int x,int y){assert(x==60 && y==10);return 1;}
int AW_UIWidth(const char *s){return strlen(s)*7;}
int AW_UIColor(int r,int g,int b){return 0;}
void AW_UIFill(int x,int y,int w,int h,int c){}
void AW_UITextBox(int x,int y,int w,int h,const char *s,int c){assert(y>=0 && y+h<=200);}
void AW_UIBox(int x,int y,int w,int h){assert(x>=0 && y>=0 && x+w<=320 && y+h<=200);}
void AW_MusicTitle(void){}
void AW_MenuMouse(int,int);
static void open_pause(void){M_Menu_Main_f();mx=160;my=63;}
static void click(int x,int y){AW_MenuMouse(x-mx,y-my);mx=x;my=y;M_Keydown(K_MOUSE1);}
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
 open_pause();click(100,54+4*19+18);M_Draw(); /* last pixel in Options */
 M_Keydown('a');assert(distance==530);keydown[K_SHIFT]=true;M_Keydown('D');assert(distance==531);keydown[K_SHIFT]=false;
 M_Keydown('s');M_Keydown(K_ENTER);assert(distance==540);
 M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);assert(gold_frame);
 M_Keydown(K_ENTER);assert(!gold_frame);
 M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);M_Draw(); /* Interface */
 M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);assert(AW_UIVoiceNames());
 M_Keydown(K_DOWNARROW);M_Keydown(K_RIGHTARROW);assert(AW_UIDialogueMethod()==3);
 M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);assert(!AW_SceneUIOption(0,0));
 M_Keydown(K_DOWNARROW);M_Keydown(K_RIGHTARROW);assert(AW_SceneUIOption(1,0)==3);
 M_Keydown(K_DOWNARROW);M_Keydown(K_RIGHTARROW);assert(AW_SceneUIOption(2,0)==2);
 M_Draw();M_Keydown(K_ESCAPE);M_Keydown(K_UPARROW);M_Keydown(K_ESCAPE);
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

int AW_WaitDraw(void){return 0;}

static int voices,dialogue=2,scene_options[]={1,2,1};
int AW_UIVoiceStyle(void){return 1;}
int AW_UIVoiceNames(void){return voices;}void AW_UIVoiceNamesToggle(void){voices=!voices;}
int AW_UIDialogueMethod(void){return dialogue;}void AW_UIDialogueCycle(int step){dialogue=(dialogue-1+step+4)%4+1;}
int AW_SceneUIOption(int n,int change){if(change)scene_options[n]=n?(scene_options[n]-1+change+3)%3+1:!scene_options[n];return scene_options[n];}
