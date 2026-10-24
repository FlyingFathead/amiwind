/* SPDX-License-Identifier: GPL-2.0-or-later */
#define main previous_menu_fixture_main
#include "aga_menu_test.c"
#undef main
/* Options > Audio: the page's four sliders in its framed group. */
static void enter_audio(void){page(1);down(1);}
int main(void){
 int i,sets;
 vid.width=320;vid.height=200;vid.rowbytes=320;vid.buffer=pixels;sv.active=true;M_Init();
 key_dest=key_game;open_options();enter_audio();assert(highlight_y==36 && highlight_w==280);
 M_Keydown(K_HOME);assert(volume.value==0 && bgmvolume.value==1 && effectsvolume.value==.75f && dialoguevolume.value==1);
 M_Keydown(K_END);assert(volume.value==1);M_Keydown(K_LEFTARROW);assert(fabs(volume.value-.95f)<.0001);
 keydown[K_SHIFT]=true;M_Keydown(K_LEFTARROW);keydown[K_SHIFT]=false;assert(fabs(volume.value-.94f)<.0001);
 M_Keydown(K_DOWNARROW);M_Keydown(K_HOME);assert(bgmvolume.value==0 && volume.value>.9f);
 M_Keydown(K_DOWNARROW);M_Keydown(K_HOME);assert(effectsvolume.value==0 && dialoguevolume.value==1);
 M_Keydown(K_DOWNARROW);M_Keydown(K_HOME);assert(dialoguevolume.value==0);
 down(1);assert(highlight_y==179 && highlight_w==74); /* Back */
 M_Keydown(K_ENTER);M_Draw();assert(!aw_menu_fullscreen());
 M_Keydown(K_ENTER);M_Draw();assert(aw_menu_fullscreen() && highlight_y==9 && highlight_w==66); /* Options and its Audio page stay selected */
 mx=160;my=100; /* opening Options centres the pointer */
 /* Absolute click, captured drag outside rail, release, and unrelated row hover. */
 click(193,81);assert(fabs(bgmvolume.value-.5f)<.0001);keydown[K_MOUSE1]=true;
 AW_MenuMouse(1000,0);mx=319;assert(bgmvolume.value==1);
 AW_MenuMouse(-1000,0);mx=0;assert(bgmvolume.value==0);
 keydown[K_MOUSE1]=false;sets=audio_sets;AW_MenuMouse(200,30);mx=200;my=111;assert(audio_sets==sets);
 click(134,111);assert(effectsvolume.value==0);keydown[K_MOUSE1]=true;AW_MenuMouse(118,0);mx=252;assert(effectsvolume.value==1);
 keydown[K_MOUSE1]=false;AW_MenuMouse(0,1);my++;sets=audio_sets;M_Draw();M_Draw();assert(audio_sets==sets);
 M_Keydown(K_ESCAPE);M_Keydown(K_ENTER);M_Draw();assert(aw_menu_fullscreen()); /* Esc also keeps the page */
 M_Keydown(K_ESCAPE);M_Keydown(K_ESCAPE);assert(key_dest==key_game && !changes && !quit);
 /* Front-end uses the same panel and returns to Options without restarting music. */
 front();M_Keydown(K_DOWNARROW);M_Keydown(K_DOWNARROW);M_Keydown(K_ENTER);down(1);
 sets=audio_sets;
 for(i=0;i<24;i++){M_Keydown(K_MWHEELDOWN);M_Draw();}
 assert(highlight_y==179 && highlight_w==74); /* Back stays selected. */
 M_Keydown(K_UPARROW);M_Draw();assert(highlight_y==126 && highlight_w==280);
 for(i=0;i<24;i++)M_Keydown(K_UPARROW);
 M_Draw();assert(highlight_y==9 && highlight_w==66); /* the tab row stays selected */
 M_Keydown(K_DOWNARROW);M_Draw();assert(highlight_y==36 && highlight_w==280);
 M_Keydown(K_DOWNARROW);M_Draw();assert(highlight_y==66 && highlight_w==280);
 assert(audio_sets==sets); /* Navigation cannot change the mix. */
 M_Keydown(K_ESCAPE);M_Draw();assert(!aw_menu_fullscreen());
 assert(key_dest==key_menu && !changes && !quit);return 0;
}
