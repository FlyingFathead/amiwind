/* SPDX-License-Identifier: GPL-2.0-or-later */
#define main previous_menu_fixture_main
#include "aga_menu_test.c"
#undef main
static int steps[2]={12,10},sets;
int R_BrightnessStep(int outside){assert(outside==0 || outside==1);return steps[outside];}
void R_BrightnessSetStep(int outside,int value){assert(outside==0 || outside==1);if(value<10)value=10;if(value>15)value=15;steps[outside]=value;sets++;}
static void enter_brightness(void){int i;for(i=0;i<9;i++)M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);M_Draw();}
int main(void){int i,old;
 vid.width=320;vid.height=200;vid.rowbytes=320;vid.buffer=pixels;sv.active=true;M_Init();
 key_dest=key_game;open_pause();click(100,140);mx=160;my=100;enter_brightness();
 M_Keydown(K_HOME);assert(steps[0]==10 && steps[1]==10);
 for(i=11;i<=15;i++){M_Keydown(K_RIGHTARROW);assert(steps[0]==i);}
 M_Keydown(K_RIGHTARROW);assert(steps[0]==15);
 keydown[K_SHIFT]=true;M_Keydown(K_LEFTARROW);keydown[K_SHIFT]=false;assert(steps[0]==14);
 M_Keydown(K_END);assert(steps[0]==15);M_Keydown(K_DOWNARROW);M_Keydown(K_END);assert(steps[1]==15);
 M_Keydown(K_HOME);assert(steps[1]==10 && steps[0]==15);
 old=sets;for(i=0;i<24;i++)M_Keydown(K_DOWNARROW);M_Draw();assert(sets==old);
 M_Keydown(K_ENTER);M_Draw();assert(scroll_total==11); /* Back */
 M_Keydown(K_ENTER);M_Draw(); /* Graphics remains selected. */
 M_Keydown(K_HOME);assert(steps[0]==10);
 /* Drag capture stays with its starting slider even across the other row. */
 click(140,65);assert(steps[0]==12 && steps[1]==10);keydown[K_MOUSE1]=true;
 AW_MenuMouse(1000,57);mx=319;my=122;assert(steps[0]==15 && steps[1]==10);
 AW_MenuMouse(-1000,0);mx=0;assert(steps[0]==10 && steps[1]==10);
 keydown[K_MOUSE1]=false;old=sets;AW_MenuMouse(200,0);mx=200;assert(sets==old);
 click(260,122);assert(steps[1]==15 && steps[0]==10);
 old=sets;M_Draw();M_Draw();assert(sets==old);
 M_Keydown(K_ESCAPE);M_Keydown(K_ENTER);M_Keydown(K_END);assert(steps[0]==15);
 M_Keydown(K_ESCAPE);M_Keydown(K_ESCAPE);M_Keydown(K_ESCAPE);assert(key_dest==key_game);
 assert(!changes && !quit);return 0;
}
