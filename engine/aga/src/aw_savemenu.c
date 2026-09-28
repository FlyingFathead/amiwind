/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include "aw_save.h"
static int active,load_mode,profile_count,profile_at,row,confirm;
static uint32_t profiles[32];
static char names[32][32],descriptions[21][96],notice[80];
static void refresh(void)
{
    int i;
    for(i=0;i<21;i++){
        descriptions[i][0]=0;
        if(profile_count)AW_SaveDescription(profiles[profile_at],i,descriptions[i],sizeof(descriptions[i]));
    }
}
int AW_SaveMenuOpen(int loading)
{
    int i;
    if(!loading && !AW_SaveAllowed())return 0;
    profile_count=AW_SaveProfiles(profiles,names,32);profile_at=0;
    for(i=0;i<profile_count;i++)if(profiles[i]==AW_SaveProfile())profile_at=i;
    if(!AW_SaveProfile())for(i=0;i<profile_count;i++)if(profiles[i]>profiles[profile_at])profile_at=i;
    if(!loading && !AW_SaveProfile())profile_count=0;
    active=1;load_mode=loading;row=confirm=0;notice[0]=0;refresh();IN_AWClearButtons();return 1;
}
int AW_SaveMenuActive(void){return active;}
int AW_SaveMenuKey(int key)
{
    int slots=load_mode?21:5,ok;
    if(!active)return 0;
    if(key=='a' || key=='A')key=K_LEFTARROW;
    if(key=='d' || key=='D')key=K_RIGHTARROW;
    if(key=='w' || key=='W')key=K_UPARROW;
    if(key=='s' || key=='S')key=K_DOWNARROW;
    if(key==K_ESCAPE){if(confirm)confirm=0;else active=0;return 1;}
    if(confirm){
        if(key=='y' || key==K_ENTER){
            ok=load_mode?AW_SaveRead(profiles[profile_at],row):AW_SaveWrite(row);
            confirm=0;
            if(ok){if(load_mode)active=0;else{strcpy(notice,"Saved.");AW_SaveMenuOpen(0);strcpy(notice,"Saved.");}}
            else strcpy(notice,"Unable to complete. Previous saves retained.");
        }else if(key=='n')confirm=0;
        return 1;
    }
    if(key==K_LEFTARROW || key==K_RIGHTARROW){
        if(load_mode && profile_count){profile_at=(profile_at+(key==K_LEFTARROW?profile_count-1:1))%profile_count;row=0;refresh();}
    }
    if(key==K_UPARROW || key==K_DOWNARROW || key==K_TAB)row=(row+(key==K_UPARROW?slots-1:1))%slots;
    if(key==K_ENTER){
        if(load_mode){if(profile_count && descriptions[row][0])confirm=1;else strcpy(notice,"No valid compatible save in this slot.");}
        else if(profile_count && descriptions[row][0])confirm=1;
        else if(AW_SaveWrite(row)){AW_SaveMenuOpen(0);strcpy(notice,"Saved.");}
        else strcpy(notice,"Save failed. Previous saves retained.");
    }
    return 1;
}
void AW_SaveMenuDraw(void)
{
    int i,start,y,gold=AW_UIColor(223,199,144);char line[128];
    if(!active || key_dest!=key_menu)return;
    AW_UIBox(2,2,316,196);AW_UITextBox(10,8,300,20,load_mode?"Load game":"Save game",gold);
    if(confirm){
        AW_UITextBox(12,67,296,22,load_mode?"Load this saved game?":"Overwrite this manual slot?",gold);
        AW_UITextBox(12,112,296,22,"Enter / Y: yes   Esc / N: cancel",gold);return;
    }
    AW_UITextBox(10,32,300,20,profile_count?names[profile_at]:load_mode?"No saved characters":aw_story.name,gold);
    start=(row/5)*5;
    for(i=start;i<start+5 && i<(load_mode?21:5);i++){
        y=59+(i-start)*21;
        if(i==row)AW_UIFill(10,y,300,20,AW_UIColor(54,47,32));
        if(i==0)strcpy(line,"Quicksave");else sprintf(line,i<5?"Manual %ld":"Autosave %ld",(long)(i<5?i:i-4));
        if(!descriptions[i][0])strcat(line," (empty)");
        AW_UITextBox(13,y,294,20,line,gold);
    }
    AW_UISmallBegin();
    AW_UITextBox(10,165,300,14,notice[0]?notice:descriptions[row],gold);
    AW_UITextBox(10,181,300,14,"Arrows/WASD: Choose  Enter  Esc",gold);
    AW_UISmallEnd();
}
