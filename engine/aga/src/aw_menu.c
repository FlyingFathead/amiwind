/* SPDX-License-Identifier: GPL-2.0-or-later
 * Local menu layout. Original fonts/artwork are private converted inputs.
 */
#include "quakedef.h"
#include "aw_save.h"
#include "aw_maps.h"
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
static int graphics_top,scroll_drag;
static int scene_picker,scene_available[AW_MAP_COUNT],scene_top,graphics,interface_options,intro_available;
static keydest_t picker_return;
static int colours[4],ready;
static const char *front_items[]={"New game","Load game","Options","Exit game"};
static const char *items[]={"Return to game","New game","Save game","Load game","Options","Main menu"};

#define ROW_Y 54
#define ROW_H 19
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
static void interface_change(int direction){
    if(selection==0)font_step(direction);
    else if(selection==1)AW_UIVoiceNamesToggle();
    else if(selection==2)AW_UIDialogueCycle(direction);
    else if(selection>=3 && selection<=5)AW_SceneUIOption(selection-3,direction);
}
static void close_menu(void){
    if(frontend)return;
    confirming=scene_picker=graphics=interface_options=0;key_dest=key_game;IN_AWClearButtons();
}
void M_Menu_Main_f(void){
    FILE *f=NULL;intro_available=COM_FOpenFile("intro/chargenname1.txt",&f)>0 && f!=NULL;if(f)fclose(f);
    IN_AWClearButtons();key_dest=key_menu;selection=confirming=scene_picker=graphics=interface_options=mouse_visible=graphics_top=scroll_drag=0;
    mouse_x=160;mouse_y=ROW_Y+ROW_H/2;
}
void M_ToggleMenu_f(void){if(key_dest==key_menu)close_menu();else M_Menu_Main_f();}
static void confirm(int action){
    confirmation_return=selection;confirming=action;selection=action==3;
    mouse_visible=0;mouse_x=selection?219:100;mouse_y=144;
}
static void cancel_confirmation(void){confirming=0;selection=confirmation_return;mouse_visible=0;}
void M_Menu_Quit_f(void){M_Menu_Main_f();confirm(1);}
static void main_menu(void){frontend=1;M_Menu_Main_f();AW_MusicTitle();}
static void scene_menu(void){
    FILE *f;int i,size;char path[48];
    if(!sv.active || Cmd_Argc()!=1){Con_Printf("Use dbg scene change during play.\n");return;}
    for(i=0;i<AW_MAP_COUNT;i++){sprintf(path,"maps/%s.bsp",AW_MapName(i));f=NULL;size=COM_FOpenFile(path,&f);scene_available[i]=f && size>=124;if(f)fclose(f);}
    picker_return=key_dest;IN_AWClearButtons();key_dest=key_menu;
    scene_picker=1;graphics=confirming=mouse_visible=0;selection=AW_MAP_COUNT;scene_top=0;
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
    if(confirming){if(inside(48,132,106,25))return 0;if(inside(166,132,106,25))return 1;return -1;}
    if(interface_options){for(i=0;i<7;i++)if(inside(44,54+i*19,232,19))return i;return -1;}
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
    if(!keydown[K_MOUSE1])scroll_drag=0;
    if(scroll_drag && ((graphics && !interface_options) || scene_picker)){
        int total=graphics?9:AW_MAP_COUNT+1,visible=graphics?7:6;
        row=AW_UIScrollHit(280,mouse_y<55?55:mouse_y>=54+visible*19?53+visible*19:mouse_y,276,54,visible*19,total,visible,graphics?graphics_top:scene_top);
        if(row>=0){if(graphics)graphics_top=row;else scene_top=row;selection=row;}return;
    }
    row=mouse_row();if(row>=0)selection=row;
}
void M_Keydown(int key){
    int direction,row;char command[48];
    if(AW_SaveMenuKey(key)){if(key_dest==key_game){frontend=0;graphics=0;}return;}
    if(key=='a' || key=='A')key=K_LEFTARROW;
    if(key=='d' || key=='D')key=K_RIGHTARROW;
    if(key=='w' || key=='W')key=K_UPARROW;
    if(key=='s' || key=='S')key=K_DOWNARROW;
    if(key==K_MWHEELUP)key=K_UPARROW;
    if(key==K_MWHEELDOWN)key=K_DOWNARROW;
    if(key==K_MOUSE1){
        if((graphics && !interface_options) || scene_picker){
            row=AW_UIScrollHit(mouse_x,mouse_y,276,54,graphics?133:114,graphics?9:AW_MAP_COUNT+1,graphics?7:6,graphics?graphics_top:scene_top);
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
    if(interface_options){
        if(key==K_ESCAPE){interface_options=0;selection=3;return;}
        if(key==K_UPARROW || key==K_DOWNARROW || key==K_TAB)selection=(selection+(key==K_UPARROW?6:1))%7;
        if(key==K_LEFTARROW || key==K_RIGHTARROW)interface_change(key==K_LEFTARROW?-1:1);
        if(key==K_ENTER || key==K_MOUSE1){if(selection==6){interface_options=0;selection=3;}else interface_change(1);}
        return;
    }
    if(graphics){
        if(key==K_ESCAPE){graphics=0;selection=frontend?2:4;return;}
        if(key==K_UPARROW || key==K_DOWNARROW || key==K_TAB)selection=(selection+(key==K_UPARROW?8:1))%9;
        if(selection<graphics_top)graphics_top=selection;
        if(selection>=graphics_top+7)graphics_top=selection-6;
        if(selection==0 && (key==K_LEFTARROW || key==K_RIGHTARROW))AW_SetDrawDistance(AW_DrawDistance()+(key==K_LEFTARROW?-1:1)*(keydown[K_SHIFT]?1:10));
        if(selection==3 && (key==K_LEFTARROW || key==K_RIGHTARROW)){interface_options=1;selection=0;return;}
        if(selection==4 && (key==K_LEFTARROW || key==K_RIGHTARROW))AW_SetAutosaveCount(AW_AutosaveCount()+(key==K_LEFTARROW?-1:1));
        if(selection==5 && (key==K_LEFTARROW || key==K_RIGHTARROW))AW_RegionLoadingToggle();
        if(selection==6 && (key==K_LEFTARROW || key==K_RIGHTARROW))AW_StreamOption(0,1);
        if(selection==7 && AW_CellChangeMethod()==2 && (key==K_LEFTARROW || key==K_RIGHTARROW))AW_StreamOption(1,key==K_LEFTARROW?-1:1);
        if(key==K_ENTER || key==K_MOUSE1){
            if(selection==1)AW_SetDrawDistance(540);
            else if(selection==2)AW_UIFrameToggle();
            else if(selection==3){interface_options=1;selection=0;}
            else if(selection==4)AW_SetAutosaveCount((AW_AutosaveCount()+1)%17);
            else if(selection==5)AW_RegionLoadingToggle();
            else if(selection==6)AW_StreamOption(0,1);
            else if(selection==7 && AW_CellChangeMethod()==2)AW_StreamOption(1,1);
            else if(selection==8){graphics=0;selection=frontend?2:4;}
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
static void cursor(void){
    if(!mouse_visible)return;
    AW_UIFill(mouse_x,mouse_y,2,6,colours[1]);AW_UIFill(mouse_x,mouse_y,6,2,colours[1]);
}
void M_Draw(void){
    int i,xx,yy,value,knob,w;char line[64];if(key_dest!=key_menu)return;
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
    }else if(graphics){
        for(i=graphics_top;i<graphics_top+7;i++){
            switch(i){
            case 0:sprintf(line,"Fog distance: %ld",(long)AW_DrawDistance());break;
            case 1:strcpy(line,"Reset distance: 540");break;
            case 2:strcpy(line,AW_UIFrameEnabled()?"Gold frame: On":"Gold frame: Off");break;
            case 3:strcpy(line,"Interface...");break;
            case 4:sprintf(line,"Autosave history: %ld",(long)AW_AutosaveCount());break;
            case 5:strcpy(line,AW_RegionLoadingFrozen()?"Area loading: Freeze frame":"Area loading: Black screen");break;
            case 6:strcpy(line,AW_CellChangeMethod()==1?"Load method: Current":"Load method: Read-ahead (test)");break;
            case 7:sprintf(line,"Read-ahead buffer: %ld KiB",(long)AW_StreamOption(1,0));break;
            default:strcpy(line,"Back");break;
            }
            label(44,54+(i-graphics_top)*19,230,19,line,i!=7 || AW_CellChangeMethod()==2,selection==i);
        }
        AW_UIScrollbar(276,54,133,9,7,graphics_top);
    }else if(scene_picker){
        for(i=scene_top;i<=AW_MAP_COUNT && i<scene_top+6;i++)
            label(44,55+(i-scene_top)*19,230,19,AW_MapTitle(i),i==AW_MAP_COUNT || scene_available[i],selection==i);
        AW_UIScrollbar(276,54,114,AW_MAP_COUNT+1,6,scene_top);
    }else if(confirming){
        AW_UITextBox(40,69,240,26,confirming==3?"Start a new game?":confirming==2?"Return to main menu?":"Exit the game?",colours[1]);
        if(sv.active)AW_UITextBox(40,97,240,24,"Current progress will be lost.",colours[2]);
        label(48,132,106,25,"Cancel",1,selection==0);
        label(166,132,106,25,confirming==3?"New game":confirming==2?"Leave":"Exit",1,selection==1);
    }else for(i=0;i<6;i++)label(44,ROW_Y+i*ROW_H,232,ROW_H,items[i],enabled(i),selection==i);
    if(!graphics)AW_UITextBox(36,174,248,17,"Enter / click   Esc: back",colours[1]);
    cursor();
}
