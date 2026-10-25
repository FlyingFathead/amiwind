/* SPDX-License-Identifier: GPL-2.0-or-later
 * The scripts' MessageBox in the game (v0.0.51; the rules: aw_msgbox_rules.c). A box without buttons is a timed
 * notice in the message line; a box with buttons stops the world (as the original's menus do) until the player
 * chooses: Left/Right (A/D, Up/Down) move between the buttons, Enter/Space/E or the mouse choose, 1-9 choose that
 * button. GetButtonPressed (aw_mwhost.c) takes the choice once.
 * The hooks (keys.c, screen.c, aw_ui.c) are set at the first box: builds and tests without scripts never call here.
 */
#include "quakedef.h"
#include "aw_msgbox.h"

extern int (*aw_msgbox_key)(int key);
extern void (*aw_msgbox_draw)(void);
extern int (*aw_msgbox_active)(void);

static aw_msgbox_t box;
static int ready;

static void hook(void) {
    if(ready)return;
    AW_MsgBoxReset(&box);
    aw_msgbox_key=AW_MsgBoxGameKey;aw_msgbox_draw=AW_MsgBoxDraw;aw_msgbox_active=AW_MsgBoxActive;
    ready=1;
}
void AW_MsgBoxShow(const char *text,const char *const *buttons,int count) {
    hook();
    if(count<1){AW_UIPickupNotice(text,AW_MsgBoxSeconds(text));return;}
    AW_MsgBoxOpen(&box,text,buttons,count);
    Con_DPrintf("MessageBox: %s (%d buttons)\n",text,count);
}
int AW_MsgBoxActive(void) {return ready && box.open;}
int AW_MsgBoxPressed(void) {return ready?AW_MsgBoxTake(&box):-1;}
void AW_MsgBoxClear(void) {if(ready)AW_MsgBoxReset(&box);}
int AW_MsgBoxGameKey(int key) {
    int k=0;
    if(!AW_MsgBoxActive() || key_dest!=key_game)return 0;
    if(key==K_LEFTARROW || key==K_UPARROW || key=='a' || key=='A' || key=='w' || key=='W')k=AW_MSGKEY_PREVIOUS;
    else if(key==K_RIGHTARROW || key==K_DOWNARROW || key==K_TAB || key=='d' || key=='D' || key=='s' || key=='S')
        k=AW_MSGKEY_NEXT;
    else if(key==K_ENTER || key==K_MOUSE1 || key==K_SPACE || key=='e' || key=='E')k=AW_MSGKEY_CHOOSE;
    else if(key>='1' && key<='9')k=AW_MSGKEY_DIGIT+(key-'0');
    if(!k)return 0;
    if(AW_MsgBoxKey(&box,k)>=0)Con_DPrintf("MessageBox: button %d\n",box.pressed);
    return 1;
}
#define PER_ROW 3
void AW_MsgBoxDraw(void) {
    char line[160];const char *rest;int i,lines=0,w,x,y,h,lh,rows,bw,gold,grey;
    extern int scr_copyeverything;
    if(!AW_MsgBoxActive() || key_dest!=key_game)return;
    scr_copyeverything=1;
    gold=AW_UIColor(223,199,144);grey=AW_UIColor(150,130,100);
    w=vid.width-16<300?vid.width-16:300;lh=AW_UIHeight();if(lh<8)lh=8;
    for(rest=box.text;rest && *rest && lines<12;lines++)rest=AW_UILine(rest,w-12,line,sizeof(line));
    if(lines<1)lines=1;
    rows=(box.count+PER_ROW-1)/PER_ROW;
    h=8+lines*lh+8+rows*24;
    if(h>(int)vid.height-8)h=vid.height-8;
    x=(vid.width-w)/2;y=(vid.height-h)/2;
    AW_UIBox(x,y,w,h);
    AW_UICenteredLines(x+6,y+4,w-12,lines*lh+8,box.text);
    for(i=0;i<box.count;i++){
        int row=i/PER_ROW,in_row=row==rows-1?box.count-row*PER_ROW:PER_ROW,col=i%PER_ROW,bx,by;
        bw=(w-16-(in_row-1)*8)/in_row;
        bx=x+8+col*(bw+8);by=y+h-rows*24+row*24-2;
        AW_UIBox(bx,by,bw,22);
        if(i==box.selection)AW_UIFill(bx+3,by+3,bw-6,16,AW_UIColor(70,52,30));
        AW_UITextBox(bx,by,bw,22,box.button[i],i==box.selection?gold:grey);
    }
}
