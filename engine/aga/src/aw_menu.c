/* SPDX-License-Identifier: GPL-2.0-or-later
 * Local menu layout. Original fonts/artwork are private converted inputs.
 */
#include "quakedef.h"
#include "amiwind_version.h"
extern qboolean keydown[256];
extern int scr_copyeverything;
extern int AW_DrawDistance(void);
extern void AW_SetDrawDistance(int value);
int m_activenet,m_state,m_return_state;
qboolean m_return_onerror;
char m_return_reason[32];
static int frontend,selection,confirming,confirmation_return;
static int mouse_x=160,mouse_y=63,mouse_visible;
static int scene_picker,scene_available[2],graphics,intro_available;
static keydest_t picker_return;
static int colours[4],ready;
static const char *front_items[]={"New game","Load game","Options","Exit game"};
static const char *items[]={"Return to game","New game","Save game","Load game","Options","Main menu"};
static const char *scene_items[]={"Prison ship interior","Seyda Neen exterior","Cancel"};
#define ROW_Y 54
#define ROW_H 19
static int inside(int x,int y,int w,int h){return mouse_x>=x && mouse_x<x+w && mouse_y>=y && mouse_y<y+h;}
static int enabled(int row){return row==0 || (row==1 && intro_available) || row==4 || row==5;}
int AW_MenuFrontEnd(void){return frontend && !graphics && !confirming && key_dest==key_menu;}
static void close_menu(void){
    if(frontend)return;
    confirming=scene_picker=graphics=0;key_dest=key_game;IN_AWClearButtons();
}
void M_Menu_Main_f(void){
    FILE *f=NULL;intro_available=COM_FOpenFile("intro/chargenname1.txt",&f)>0 && f!=NULL;if(f)fclose(f);
    IN_AWClearButtons();key_dest=key_menu;selection=confirming=scene_picker=graphics=mouse_visible=0;
    mouse_x=160;mouse_y=ROW_Y+ROW_H/2;
}
void M_ToggleMenu_f(void){if(key_dest==key_menu)close_menu();else M_Menu_Main_f();}
static void confirm(int action){confirmation_return=selection;confirming=action;selection=0;mouse_visible=0;mouse_x=100;mouse_y=144;}
static void cancel_confirmation(void){confirming=0;selection=confirmation_return;mouse_visible=0;}
void M_Menu_Quit_f(void){M_Menu_Main_f();confirm(1);}
static void main_menu(void){frontend=1;M_Menu_Main_f();AW_MusicTitle();}
static void scene_menu(void){
    FILE *f;int i,size;char *paths[]={"maps/prison.bsp","maps/seyda.bsp"};
    if(!sv.active || Cmd_Argc()!=1){Con_Printf("Use dbg scene change during play.\n");return;}
    for(i=0;i<2;i++){f=NULL;size=COM_FOpenFile(paths[i],&f);scene_available[i]=f && size>=124;if(f)fclose(f);}
    picker_return=key_dest;IN_AWClearButtons();key_dest=key_menu;
    scene_picker=1;graphics=confirming=mouse_visible=0;selection=scene_available[0]?0:scene_available[1]?1:2;
    mouse_x=160;mouse_y=65+selection*24+12;
}
void M_Init(void){
    Cmd_AddCommand("aw_main_menu",main_menu);Cmd_AddCommand("togglemenu",M_ToggleMenu_f);
    Cmd_AddCommand("menu_main",M_Menu_Main_f);Cmd_AddCommand("menu_quit",M_Menu_Quit_f);
    Cmd_AddCommand("aw_scene_menu",scene_menu);
}
static int mouse_row(void){
    int i;
    if(confirming){if(inside(48,132,106,25))return 0;if(inside(166,132,106,25))return 1;return -1;}
    if(graphics){if(inside(72,77,176,32))return 0;for(i=1;i<4;i++)if(inside(44,93+i*22,232,20))return i;return -1;}
    if(scene_picker){for(i=0;i<3;i++)if(inside(44,65+i*24,232,24))return i;return -1;}
    if(frontend){for(i=0;i<4;i++)if(inside(12,92+i*20,137,20))return i;return -1;}
    for(i=0;i<6;i++)if(inside(44,ROW_Y+i*ROW_H,232,ROW_H))return i;
    return -1;
}
void AW_MenuMouse(int dx,int dy){
    int row;if(key_dest!=key_menu || (!dx && !dy))return;
    mouse_visible=1;mouse_x+=dx;mouse_y+=dy;
    if(mouse_x<0)mouse_x=0;if(mouse_x>319)mouse_x=319;
    if(mouse_y<0)mouse_y=0;if(mouse_y>199)mouse_y=199;
    row=mouse_row();if(row>=0)selection=row;
}
void M_Keydown(int key){
    int direction,row;
    if(key==K_MOUSE1){row=mouse_row();if(row<0)return;selection=row;}
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
    if(graphics){
        if(key==K_ESCAPE){graphics=0;selection=frontend?2:4;return;}
        if(key==K_UPARROW || key==K_DOWNARROW || key==K_TAB)selection=(selection+(key==K_UPARROW?3:1))%4;
        if(selection==0 && (key==K_LEFTARROW || key==K_RIGHTARROW))AW_SetDrawDistance(AW_DrawDistance()+(key==K_LEFTARROW?-1:1)*(keydown[K_SHIFT]?1:10));
        if(key==K_MOUSE1 && selection==0 && inside(80,93,161,16))AW_SetDrawDistance(128+(mouse_x-80)*(1400-128)/160);
        if(key==K_ENTER || key==K_MOUSE1){
            if(selection==1)AW_SetDrawDistance(540);
            else if(selection==2)AW_UIFrameToggle();
            else if(selection==3){graphics=0;selection=frontend?2:4;}
        }
        return;
    }
    if(scene_picker){
        if(key==K_ESCAPE){scene_picker=0;key_dest=picker_return;IN_AWClearButtons();return;}
        if(key==K_UPARROW || key==K_DOWNARROW || key==K_TAB){
            direction=key==K_UPARROW?-1:1;do{selection=(selection+direction+3)%3;}while(selection<2 && !scene_available[selection]);
        }
        if(key==K_ENTER || key==K_MOUSE1){
            if(selection==2){scene_picker=0;key_dest=picker_return;IN_AWClearButtons();}
            else if(scene_available[selection]){direction=selection;close_menu();Cbuf_AddText(direction?"aw_scene town\n":"aw_scene ship\n");}
        }
        return;
    }
    if(frontend){
        if(key==K_UPARROW || key==K_DOWNARROW || key==K_TAB){do{selection=(selection+(key==K_UPARROW?3:1))%4;}while(selection==1 || (selection==0 && !intro_available));}
        if(key==K_ENTER || key==K_MOUSE1){
            if(selection==0 && intro_available)confirm(3);
            else if(selection==2){graphics=1;selection=0;mouse_x=160;mouse_y=100;}
            else if(selection==3)confirm(1);
        }
        return;
    }
    if(key==K_ESCAPE){close_menu();return;}
    if(key==K_UPARROW || key==K_DOWNARROW || key==K_TAB){direction=key==K_UPARROW?-1:1;do{selection=(selection+direction+6)%6;}while(!enabled(selection));}
    if(key==K_ENTER || key==K_MOUSE1){
        if(selection==0)close_menu();
        else if(selection==1 && intro_available)confirm(3);
        else if(selection==4){graphics=1;selection=0;mouse_x=160;mouse_y=100;}
        else if(selection==5)confirm(2);
    }
}
static void label(int x,int y,int w,int h,const char *s,int active,int selected){
    if(active && selected)AW_UIFill(x,y,w,h,colours[3]);
    AW_UITextBox(x,y,w,h,s,active?colours[1]:colours[2]);
}
static void cursor(void){
    if(!mouse_visible)return;
    AW_UIFill(mouse_x,mouse_y,2,6,colours[1]);AW_UIFill(mouse_x,mouse_y,6,2,colours[1]);
}
void M_Draw(void){
    int i,xx,yy,value,knob,w;char line[64];if(key_dest!=key_menu)return;
    scr_copyeverything=1;
    if(!ready){colours[0]=AW_UIColor(22,20,18);colours[1]=AW_UIColor(210,184,121);colours[2]=AW_UIColor(114,114,114);colours[3]=AW_UIColor(62,53,36);ready=1;}
    if(AW_MenuFrontEnd()){
        if(!AW_UIBackground())AW_UIFill(0,0,vid.width,vid.height,AW_UIColor(0,0,0));
        AW_UIBox(8,88,145,90);
        for(i=0;i<4;i++)label(12,92+i*20,137,20,front_items[i],i!=1 && (i!=0 || intro_available),i==selection);
        strcpy(line,"AmiWind v" AMIWIND_VERSION);w=AW_UIWidth(line);
        AW_UIFill(vid.width-w-10,180,w+8,20,AW_UIColor(0,0,0));
        AW_UITextBox(vid.width-w-6,180,w,20,line,colours[1]);cursor();return;
    }
    if(frontend)AW_UIFill(0,0,vid.width,vid.height,AW_UIColor(0,0,0));
    else for(yy=0;yy<vid.height;yy++)for(xx=0;xx<vid.width;xx++)
        if((xx&3)!=((yy&1)<<1))vid.buffer[yy*vid.rowbytes+xx]=colours[0];
    AW_UIBox(28,6,264,188);
    if(!AW_UILogo(60,10))AW_UITextBox(44,10,232,40,"AmiWind",colours[1]);
    if(graphics){
        AW_UITextBox(44,54,232,20,"Options",colours[1]);
        value=AW_DrawDistance();sprintf(line,"Fog distance: %ld",(long)value);AW_UITextBox(44,77,232,19,line,selection==0?colours[1]:colours[2]);
        AW_UIFill(80,100,161,3,colours[2]);knob=(value-128)*160/(1400-128);if(knob<0)knob=0;if(knob>160)knob=160;AW_UIFill(78+knob,95,5,13,colours[1]);
        label(44,115,232,20,"Default: 540",1,selection==1);
        label(44,137,232,20,AW_UIFrameEnabled()?"Gold frame: On":"Gold frame: Off",1,selection==2);
        label(44,159,232,20,"Back",1,selection==3);
    }else if(scene_picker){
        for(i=0;i<3;i++)label(44,65+i*24,232,24,scene_items[i],i==2 || scene_available[i],selection==i);
    }else if(confirming){
        AW_UITextBox(40,69,240,26,confirming==3?"Start a new game?":confirming==2?"Return to main menu?":"Exit the game?",colours[1]);
        if(sv.active)AW_UITextBox(40,97,240,24,"Current progress will be lost.",colours[2]);
        label(48,132,106,25,"Cancel",1,selection==0);
        label(166,132,106,25,confirming==3?"New game":confirming==2?"Leave":"Exit",1,selection==1);
    }else for(i=0;i<6;i++)label(44,ROW_Y+i*ROW_H,232,ROW_H,items[i],enabled(i),selection==i);
    if(!graphics)AW_UITextBox(36,174,248,17,"Enter / click   Esc: back",colours[1]);
    cursor();
}
