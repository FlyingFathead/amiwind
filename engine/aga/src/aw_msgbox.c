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
static int mouse_x=-1,mouse_y=-1;   /* the pointer over a box with buttons; -1: the screen's middle at the next draw */

static void hook(void) {
    if(ready)return;
    AW_MsgBoxReset(&box);
    aw_msgbox_key=AW_MsgBoxGameKey;aw_msgbox_draw=AW_MsgBoxDraw;aw_msgbox_active=AW_MsgBoxActive;
    aw_msgbox_mouse=AW_MsgBoxMouse;      /* the pointer over a box with buttons (MSGBOX-NO-CURSOR-62) */
    ready=1;
}
void AW_MsgBoxShow(const char *raw,const char *const *buttons,int count) {
    static char text[1024];
    hook();
    AW_ExpandDialogue(text,sizeof(text),raw);    /* the text defines (BOOK-TEXT-MACROS-58), as OpenMW's message boxes */
    if(count<1){AW_UIPickupNotice(text,AW_MsgBoxSeconds(text));return;}
    AW_MsgBoxOpen(&box,text,buttons,count);
    mouse_x=mouse_y=-1;     /* the pointer starts in the middle of the screen (AW_MsgBoxDraw) */
    Con_DPrintf("MessageBox: %s (%d buttons)\n",text,count);
}
int AW_MsgBoxActive(void) {return ready && box.open;}
/* DIALOGUE-MSGBOX-BEHIND-60: a box raised by a dialogue answer's result script (or under any world window) is shown
 * over that window and takes its keys first (OpenMW: message boxes are the top layer); elsewhere only in play */
static int box_here(void) {return key_dest==key_game || (key_dest==key_menu && AW_WorldUIActive());}
static int button_at(int px,int py);
int AW_MsgBoxPressed(void) {return ready?AW_MsgBoxTake(&box):-1;}
void AW_MsgBoxClear(void) {if(ready)AW_MsgBoxReset(&box);}
int AW_MsgBoxGameKey(int key) {
    int k=0;
    if(!AW_MsgBoxActive() || !box_here())return 0;
    if(key==K_LEFTARROW || key==K_UPARROW || key=='a' || key=='A' || key=='w' || key=='W')k=AW_MSGKEY_PREVIOUS;
    else if(key==K_RIGHTARROW || key==K_DOWNARROW || key==K_TAB || key=='d' || key=='D' || key=='s' || key=='S')
        k=AW_MSGKEY_NEXT;
    else if(key==K_MOUSE1){
        /* a click chooses the button under the pointer; outside the buttons it does nothing (MSGBOX-NO-CURSOR-62) */
        int i=button_at(mouse_x,mouse_y);
        if(i<0)return 1;
        box.selection=i;k=AW_MSGKEY_CHOOSE;
    }
    else if(key==K_ENTER || key==K_SPACE || key=='e' || key=='E')k=AW_MSGKEY_CHOOSE;
    else if(key>='1' && key<='9')k=AW_MSGKEY_DIGIT+(key-'0');
    if(!k)return 0;
    if(AW_MsgBoxKey(&box,k)>=0)Con_DPrintf("MessageBox: button %d\n",box.pressed);
    return 1;
}
/* The box's frame (aw_msgbox_rules.c AW_MsgBoxLayout) with its text's height in this font; the drawing and the
 * pointer's hit test use the same rectangles (MSGBOX-NO-CURSOR-62). Returns the text's height. */
static int box_frame(int frame[4],int *shown) {
    char line[160];const char *rest;int lh,n=0,rows,w=vid.width-16<300?vid.width-16:300;
    lh=AW_UIHeight();if(lh<8)lh=8;
    /* CRIME-RELEASE-LINE-CUT-62: the lines counted at the width they are drawn at (the text area less 16) and every one
     * shown while the box fits the screen (before: the drawing stopped after three, a jail release lost its skills) */
    for(rest=box.text;rest && *rest && n<AW_MSGBOX_LINES;n++)rest=AW_UILine(rest,w-12-16,line,sizeof(line));
    rows=(box.count+AW_MSGBOX_PER_ROW-1)/AW_MSGBOX_PER_ROW;
    n=AW_MsgBoxLinesShown(n,rows,(int)vid.height,lh);
    AW_MsgBoxLayout(box.count,vid.width,vid.height,n*lh,frame);
    if(shown)*shown=n;
    return n*lh;
}
/* the mouse over a box with buttons: the pointer, a button under it is the selection (OpenMW: hover highlights) */
static int button_at(int px,int py) {
    int frame[4];
    if(!box.open || box.count<1)return -1;
    box_frame(frame,NULL);
    return AW_MsgBoxButtonAt(box.count,frame,px,py);
}
int AW_MsgBoxMouse(int dx,int dy) {
    int i;
    if(!AW_MsgBoxActive() || !box_here())return 0;
    if(mouse_x<0){mouse_x=vid.width/2;mouse_y=vid.height/2;}
    mouse_x+=dx;mouse_y+=dy;
    if(mouse_x<0)mouse_x=0;
    if(mouse_x>(int)vid.width-1)mouse_x=(int)vid.width-1;
    if(mouse_y<0)mouse_y=0;
    if(mouse_y>(int)vid.height-1)mouse_y=(int)vid.height-1;
    if((dx || dy) && (i=button_at(mouse_x,mouse_y))>=0)box.selection=i;
    return 1;
}
void AW_MsgBoxDraw(void) {
    int i,f[4],r[4],lines,shown,gold,grey;
    extern int scr_copyeverything;
    if(!AW_MsgBoxActive() || !box_here())return;
    scr_copyeverything=1;
    gold=AW_UIColor(223,199,144);grey=AW_UIColor(150,130,100);
    lines=box_frame(f,&shown);
    AW_UIBox(f[0],f[1],f[2],f[3]);
    AW_UICenteredLinesUpTo(f[0]+6,f[1]+4,f[2]-12,lines+8,box.text,shown);
    for(i=0;i<box.count;i++){
        AW_MsgBoxButtonRect(box.count,i,f,r);
        AW_UIBox(r[0],r[1],r[2],r[3]);
        if(i==box.selection)AW_UIFill(r[0]+3,r[1]+3,r[2]-6,16,AW_UIColor(70,52,30));
        AW_UITextBox(r[0],r[1],r[2],r[3],box.button[i],i==box.selection?gold:grey);
    }
    if(mouse_x<0){mouse_x=vid.width/2;mouse_y=vid.height/2;}
    if(!AW_UICursor(mouse_x,mouse_y)){AW_UIFill(mouse_x,mouse_y,2,6,gold);AW_UIFill(mouse_x,mouse_y,6,2,gold);}
}
