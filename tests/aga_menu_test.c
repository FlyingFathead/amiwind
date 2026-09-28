/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
keydest_t key_dest;
qboolean keydown[256];
viddef_t vid;
byte palette[768],glyphs[16384],pixels[320*200];
byte *host_basepal=palette,*draw_chars=glyphs;
int clears,quit,scene_changes,missing;
static int distance=700;
int AW_DrawDistance(void){return distance;}
void AW_SetDrawDistance(int n){if(n<128)n=128;if(n>1400)n=1400;distance=n;}
server_t sv;
static void (*picker)(void);
static char queued[64];
int Cmd_Argc(void){return 1;}
void Con_Printf(char *fmt,...){}
int COM_FOpenFile(char *name,FILE **f){if(missing){*f=NULL;return -1;}*f=tmpfile();return 124;}
void IN_AWClearButtons(void) {clears++;}
void Cmd_AddCommand(char *name,void (*fn)(void)) {if(!strcmp(name,"aw_scene_menu"))picker=fn;}
void Cbuf_AddText(char *s) {if(!strcmp(s,"quit\n"))quit++;else{strcpy(queued,s);scene_changes++;}}
void AW_UIText(int x,int y,const char *s,int c){}
void AW_UIBox(int x,int y,int w,int h){}
void Draw_String(int x,int y,char *s){}
void Draw_FadeScreen(void) {}
void Draw_Fill(int x,int y,int w,int h,int c) {
 assert(x>=0 && y>=0 && w>0 && h>0 && x+w<=320 && y+h<=200);
}
void AW_MenuMouse(int,int);
int main(void) {
 vid.width=320;vid.height=200;vid.rowbytes=320;vid.buffer=pixels;
 key_dest=key_game;M_ToggleMenu_f();assert(key_dest==key_menu && clears==1);
 M_Draw();M_Keydown(K_ESCAPE);assert(key_dest==key_game && !quit);
 M_ToggleMenu_f();AW_MenuMouse(0,20);M_Keydown(K_MOUSE1);
 assert(key_dest==key_menu && !quit); /* Disabled New game. */
 M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);M_Draw(); /* Options / Graphics. */
 M_Keydown(K_LEFTARROW);assert(distance==690);M_Keydown(K_RIGHTARROW);assert(distance==700);
 keydown[K_SHIFT]=true;M_Keydown(K_LEFTARROW);assert(distance==699);M_Keydown(K_RIGHTARROW);assert(distance==700);keydown[K_SHIFT]=false;
 AW_MenuMouse(-80,0);M_Keydown(K_MOUSE1);assert(distance==128);M_Draw();
 M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);assert(distance==540); /* default */
 M_Keydown(K_ESCAPE);assert(key_dest==key_menu);
 M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);M_Draw(); /* Exit confirmation. */
 M_Keydown(K_ENTER);assert(key_dest==key_menu && !quit); /* Cancel default. */
 M_Keydown(K_ENTER);M_Keydown(K_ESCAPE);assert(key_dest==key_menu && !quit);
 M_Keydown(K_ESCAPE);assert(key_dest==key_game);
 M_Menu_Quit_f();M_Keydown(K_RIGHTARROW);M_Keydown(K_ENTER);
 assert(quit==1 && key_dest==key_console);
 M_ToggleMenu_f();AW_MenuMouse(10000,10000);M_Draw();
 AW_MenuMouse(-10000,-10000);M_Draw();
 M_Init();assert(picker);sv.active=true;key_dest=key_console;
 picker();assert(key_dest==key_menu);M_Draw();M_Keydown(K_ESCAPE);assert(key_dest==key_console);
 picker();M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);
 assert(key_dest==key_game && scene_changes==1 && !strcmp(queued,"aw_scene town\n"));
 picker();M_Keydown(K_ENTER);assert(scene_changes==2 && !strcmp(queued,"aw_scene ship\n"));
 missing=1;picker();M_Draw();M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);
 assert(scene_changes==2 && key_dest==key_game); /* only Cancel is enabled */
 return 0;
}
