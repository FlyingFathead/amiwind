/* SPDX-License-Identifier: GPL-2.0-or-later
 * Independent in-game menu. No game art or original menu implementation.
 */
#include "quakedef.h"
extern byte *draw_chars;
extern qboolean keydown[256];
extern int AW_DrawDistance(void);
extern void AW_SetDrawDistance(int value);
int m_activenet;
/* Retained network error ABI; this local prototype exposes no network menu. */
int m_state, m_return_state;
qboolean m_return_onerror;
char m_return_reason[32];
static int selection, confirming, mouse_x=160, mouse_y=56;
static int scene_picker, scene_available[2], graphics;
static keydest_t picker_return;
static const char *scene_items[]={"Prison ship interior","Seyda Neen exterior","Cancel"};
static const char *items[]={"Return to game","New game","Save game","Load game","Options","Exit game"};
static int colours[4], ready;
static int enabled(int row) {return row==0 || row==4 || row==5;}
static void scene_menu(void) {
    FILE *f;int i,size;char *paths[]={"maps/prison.bsp","maps/seyda.bsp"};
    if(!sv.active || Cmd_Argc()!=1){Con_Printf("Use dbg scene change during play.\n");return;}
    for(i=0;i<2;i++){f=NULL;size=COM_FOpenFile(paths[i],&f);scene_available[i]=f && size>=124;if(f)fclose(f);}
    picker_return=key_dest;IN_AWClearButtons();key_dest=key_menu;
    scene_picker=1;graphics=0;confirming=0;selection=scene_available[0]?0:scene_available[1]?1:2;
    mouse_x=160;mouse_y=57+selection*19;
}
static int nearest(int r,int g,int b) {
    int i,best=0,score=999999,d,dr,dg,db;
    for(i=0;i<256;i++){dr=host_basepal[i*3]-r;dg=host_basepal[i*3+1]-g;db=host_basepal[i*3+2]-b;
        d=dr*dr+dg*dg+db*db;if(d<score){score=d;best=i;}}
    return best;
}
static void text(int x,int y,const char *s,int colour) {
    AW_UIText(x,y,s,colour);
}
static void close_menu(void) {confirming=0;scene_picker=0;graphics=0;key_dest=key_game;IN_AWClearButtons();}
void M_Menu_Main_f(void) {IN_AWClearButtons();key_dest=key_menu;selection=0;confirming=0;scene_picker=0;graphics=0;mouse_x=160;mouse_y=57;}
void M_ToggleMenu_f(void) {if(key_dest==key_menu)close_menu();else M_Menu_Main_f();}
void M_Menu_Quit_f(void) {M_Menu_Main_f();confirming=1;selection=0;}
void M_Init(void) {Cmd_AddCommand("togglemenu",M_ToggleMenu_f);Cmd_AddCommand("menu_main",M_Menu_Main_f);Cmd_AddCommand("menu_quit",M_Menu_Quit_f);Cmd_AddCommand("aw_scene_menu",scene_menu);}
void AW_MenuMouse(int dx,int dy) {
    int row;if(key_dest!=key_menu)return;
    mouse_x+=dx;mouse_y+=dy;
    if(mouse_x<0)mouse_x=0;if(mouse_x>319)mouse_x=319;
    if(mouse_y<0)mouse_y=0;if(mouse_y>199)mouse_y=199;
    if(mouse_x<65 || mouse_x>=255)return;
    if(graphics){
        if(mouse_y>=68 && mouse_y<108)selection=0;
        else if(mouse_y>=113 && mouse_y<133)selection=1;
        else if(mouse_y>=137 && mouse_y<157)selection=2;
    }else if(scene_picker){row=(mouse_y-49)/19;if(mouse_y>=49 && row<3)selection=row;}
    else if(confirming){if(mouse_y>=92 && mouse_y<120)selection=mouse_x<160?0:1;}
    else {row=(mouse_y-49)/19;if(mouse_y>=49 && row<6)selection=row;}
}
void M_Keydown(int key) {
    int direction;
    if(graphics){
        if(key==K_ESCAPE){graphics=0;selection=4;return;}
        if(key==K_UPARROW || key==K_DOWNARROW || key==K_TAB)selection=(selection+(key==K_UPARROW?2:1))%3;
        if(selection==0 && (key==K_LEFTARROW || key==K_RIGHTARROW))AW_SetDrawDistance(AW_DrawDistance()+(key==K_LEFTARROW?-1:1)*(keydown[K_SHIFT]?1:10));
        if(key==K_MOUSE1 && selection==0 && mouse_x>=80 && mouse_x<=240 && mouse_y>=88 && mouse_y<108)
            AW_SetDrawDistance(128+(mouse_x-80)*(1400-128)/160);
        if(key==K_ENTER || (key==K_MOUSE1 && mouse_x>=65 && mouse_x<255 &&
           ((selection==1 && mouse_y>=113 && mouse_y<133)||(selection==2 && mouse_y>=137 && mouse_y<157)))){
            if(selection==1)AW_SetDrawDistance(540);
            else if(selection==2){graphics=0;selection=4;}
        }
        return;
    }
    if(scene_picker){
        if(key==K_ESCAPE){scene_picker=0;key_dest=picker_return;IN_AWClearButtons();return;}
        if(key==K_UPARROW || key==K_DOWNARROW || key==K_TAB){
            direction=key==K_UPARROW?-1:1;
            do {selection=(selection+direction+3)%3;}while(selection<2 && !scene_available[selection]);
        }
        if(key==K_ENTER || (key==K_MOUSE1 && mouse_x>=65 && mouse_x<255 && mouse_y>=49 && mouse_y<106)){
            if(selection==2){scene_picker=0;key_dest=picker_return;IN_AWClearButtons();}
            else if(scene_available[selection]){
                direction=selection;close_menu();Cbuf_AddText(direction?"aw_scene town\n":"aw_scene ship\n");
            }
        }
        return;
    }
    if(key==K_ESCAPE){if(confirming){confirming=0;selection=5;}else close_menu();return;}
    if(confirming){
        if(key==K_LEFTARROW || key==K_RIGHTARROW || key==K_TAB)selection=1-selection;
        if(key=='n'){confirming=0;selection=5;return;}
        if(key==K_ENTER || key=='y' || (key==K_MOUSE1 && mouse_x>=65 && mouse_x<255 && mouse_y>=92 && mouse_y<120)){
            if(selection==1 || key=='y'){IN_AWClearButtons();key_dest=key_console;Cbuf_AddText("quit\n");}
            else {confirming=0;selection=5;}
        }
        return;
    }
    if(key==K_UPARROW || key==K_DOWNARROW || key==K_TAB){
        direction=key==K_UPARROW?-1:1;
        do {selection=(selection+direction+6)%6;}while(!enabled(selection));
    }
    if(key==K_ENTER || (key==K_MOUSE1 && mouse_x>=65 && mouse_x<255 && mouse_y>=49 && mouse_y<163)){
        if(selection==0)close_menu();
        else if(selection==4){graphics=1;selection=0;mouse_x=160;mouse_y=98;}
        else if(selection==5){confirming=1;selection=0;}
    }
}
void M_Draw(void) {
    int i,xx,yy,value,knob,x=52,y=25;char line[32];if(key_dest!=key_menu)return;
    if(!ready){colours[0]=nearest(22,20,18);colours[1]=nearest(210,184,121);colours[2]=nearest(114,114,114);colours[3]=nearest(62,53,36);ready=1;}
    /* The generated palette does not reserve index zero for black. */
    for(yy=0;yy<vid.height;yy++)for(xx=0;xx<vid.width;xx++)
        if((xx&3)!=((yy&1)<<1))vid.buffer[yy*vid.rowbytes+xx]=colours[0];
    AW_UIBox(x-1,y-1,218,152);
    text(132,31,"AMIWIND",colours[1]);
    if(graphics){
        text(80,48,"Options",colours[1]);Draw_Fill(164,45,84,14,colours[3]);text(168,48,"Graphics",colours[1]);
        value=AW_DrawDistance();sprintf(line,"Fog distance: %ld",(long)value);text(72,72,line,selection==0?colours[1]:colours[2]);
        Draw_Fill(80,96,161,3,colours[2]);knob=(value-128)*160/(1400-128);if(knob<0)knob=0;if(knob>160)knob=160;
        Draw_Fill(78+knob,91,5,13,colours[1]);
        if(selection>0)Draw_Fill(65,selection==1?113:137,190,17,colours[3]);
        text(80,118,"Medium/default: 540",colours[1]);text(80,142,"Back",colours[1]);
        Draw_String(64,166,"128..1400 local units");
    }else if(scene_picker){
        for(i=0;i<3;i++){
            if(i==selection && (i==2 || scene_available[i]))Draw_Fill(65,49+i*19,190,17,colours[3]);
            text(80,54+i*19,scene_items[i],(i==2 || scene_available[i])?colours[1]:colours[2]);
        }
        text(72,137,"Debug scene change",colours[1]);
    }else if(confirming){
        text(96,66,"Exit the game?",colours[1]);
        Draw_Fill(selection?160:65,92,95,28,colours[3]);
        text(88,102,"Cancel",colours[1]);text(185,102,"Exit",colours[1]);
    }else for(i=0;i<6;i++){
        if(i==selection && enabled(i))Draw_Fill(65,49+i*19,190,17,colours[3]);
        text(80,54+i*19,items[i],enabled(i)?colours[1]:colours[2]);
    }
    Draw_String(24,188,graphics?"L/R:10  Shift:1  Click / Esc":"Arrows / Enter / Mouse / Esc");
    Draw_Fill(mouse_x,mouse_y,mouse_x<319?2:1,mouse_y<194?6:200-mouse_y,colours[1]);
    Draw_Fill(mouse_x,mouse_y,mouse_x<314?6:320-mouse_x,mouse_y<199?2:1,colours[1]);
}
