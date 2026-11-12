/* SPDX-License-Identifier: GPL-2.0-or-later
 * The scripts' MessageBox rules (aw_msgbox.h): no engine dependencies, host-tested (tests/aga_msgbox_test.c).
 *
 * Sources (OpenMW 0.51, the original game as OpenMW reproduces it):
 * - interpreter/miscopcodes.hpp formatMessage: '%' then an optional width and ".precision", then the conversion:
 *   S s a string, d D a whole number, f F g G e E a number with a fraction; "%%" is a percent sign.
 * - windowmanagerimp.cpp messageBox: a box without buttons is a timed message (messageboxmanager: its length times
 *   fMessageTimePerChar); with buttons it is interactive: createInteractiveMessageBox replaces a shown one, and
 *   readPressedButton returns the button once, then -1.
 * Numbers are formatted by Q_snprintf (aw_format.c), not the C library's floating-point code.
 */
#include <string.h>
#include "aw_msgbox.h"
#include "aw_format.h"

static void put(char *out,int capacity,int *n,const char *text,int length) {
    while(length-- > 0 && *n < capacity-1)out[(*n)++]=*text++;
}
int AW_MsgBoxFormat(char *out,int capacity,const char *format,const float *numbers,int number) {
    int n=0,next=0;const char *p=format;
    if(capacity<=0)return 0;
    if(!format){out[0]=0;return 0;}
    while(*p && n<capacity-1){
        const char *start=p;char spec[16],piece[64];int width=-1,precision=-1,k;
        if(*p!='%'){out[n++]=*p++;continue;}
        p++;
        if(*p=='%'){out[n++]='%';p++;continue;}
        if(*p>='0' && *p<='9'){width=0;while(*p>='0' && *p<='9'){if(width<99)width=width*10+(*p-'0');p++;}}
        if(*p=='.'){p++;precision=0;while(*p>='0' && *p<='9'){if(precision<20)precision=precision*10+(*p-'0');p++;}}
        if(width>40)width=40;
        if(*p=='d' || *p=='D' || *p=='f' || *p=='F' || *p=='g' || *p=='G' || *p=='e' || *p=='E'){
            float v=next<number && numbers?numbers[next]:0.0f;char c=*p;
            next++;p++;
            if(c=='d' || c=='D'){
                long whole=v>=2147483647.0f?2147483647L:v<=-2147483647.0f?-2147483647L:(long)v;
                if(width>=0)Q_snprintf(spec,sizeof(spec),"%%%dld",width);else strcpy(spec,"%ld");
                k=Q_snprintf(piece,sizeof(piece),spec,whole);
            }else{
                char conversion=c=='F'?'f':c=='G'?'g':c=='E'?'e':c;
                if(width>=0 && precision>=0)Q_snprintf(spec,sizeof(spec),"%%%d.%d%c",width,precision,conversion);
                else if(precision>=0)Q_snprintf(spec,sizeof(spec),"%%.%d%c",precision,conversion);
                else if(width>=0)Q_snprintf(spec,sizeof(spec),"%%%d%c",width,conversion);
                else Q_snprintf(spec,sizeof(spec),"%%%c",conversion);
                k=Q_snprintf(piece,sizeof(piece),spec,(double)v);
            }
            if(k>(int)sizeof(piece)-1)k=(int)sizeof(piece)-1;
            if(k>0)put(out,capacity,&n,piece,k);
            continue;
        }
        /* %s, %S and anything else: kept as written */
        if(*p)p++;
        put(out,capacity,&n,start,(int)(p-start));
    }
    out[n]=0;
    return n;
}
double AW_MsgBoxSeconds(const char *text) {
    double s=text?strlen(text)*0.1:0;
    return s<3?3:s>10?10:s;
}
void AW_MsgBoxReset(aw_msgbox_t *m) {memset(m,0,sizeof(*m));m->pressed=-1;}
static void copy(char *out,int capacity,const char *text) {
    strncpy(out,text?text:"",capacity-1);out[capacity-1]=0;
}
void AW_MsgBoxOpen(aw_msgbox_t *m,const char *text,const char *const *buttons,int count) {
    int i;
    if(count<1)return;
    if(count>AW_MSGBOX_BUTTONS)count=AW_MSGBOX_BUTTONS;
    copy(m->text,sizeof(m->text),text);
    for(i=0;i<count;i++)copy(m->button[i],sizeof(m->button[i]),buttons?buttons[i]:"");
    m->count=count;m->selection=0;m->open=1;m->pressed=-1;
}
int AW_MsgBoxLinesShown(int lines,int rows,int screen,int line) {
    int room;
    if(lines<1)lines=1;
    if(line<1)line=1;
    room=(screen-8-16-rows*24)/line;
    if(room<1)room=1;
    if(lines>room)lines=room;
    return lines>AW_MSGBOX_LINES?AW_MSGBOX_LINES:lines;
}
int AW_MsgBoxKey(aw_msgbox_t *m,int key) {
    int chosen=-1;
    if(!m->open || m->count<1)return -1;
    if(key==AW_MSGKEY_PREVIOUS)m->selection=(m->selection+m->count-1)%m->count;
    else if(key==AW_MSGKEY_NEXT)m->selection=(m->selection+1)%m->count;
    else if(key==AW_MSGKEY_CHOOSE)chosen=m->selection;
    else if(key>AW_MSGKEY_DIGIT && key<=AW_MSGKEY_DIGIT+9 && key-AW_MSGKEY_DIGIT<=m->count)chosen=key-AW_MSGKEY_DIGIT-1;
    if(chosen>=0){m->open=0;m->pressed=chosen;}
    return chosen;
}
int AW_MsgBoxTake(aw_msgbox_t *m) {int b=m->pressed;m->pressed=-1;return b;}

/* Where a box and its buttons are on the screen (MSGBOX-NO-CURSOR-62): the pointer's hit test and the drawing use
 * the same rectangles. A script's box (and the failed-load box): at most 300 wide, centred, TEXT_PX of text, its
 * buttons in rows of AW_MSGBOX_PER_ROW, 22 high. FRAME and RECT: x, y, w, h. */
void AW_MsgBoxLayout(int count,int vw,int vh,int text_px,int frame[4]) {
    int rows=(count+AW_MSGBOX_PER_ROW-1)/AW_MSGBOX_PER_ROW;
    frame[2]=vw-16<300?vw-16:300;
    frame[3]=8+text_px+8+rows*24;
    if(frame[3]>vh-8)frame[3]=vh-8;
    frame[0]=(vw-frame[2])/2;frame[1]=(vh-frame[3])/2;
}
void AW_MsgBoxButtonRect(int count,int i,const int frame[4],int rect[4]) {
    int rows=(count+AW_MSGBOX_PER_ROW-1)/AW_MSGBOX_PER_ROW,row=i/AW_MSGBOX_PER_ROW,col=i%AW_MSGBOX_PER_ROW;
    int in_row=row==rows-1?count-row*AW_MSGBOX_PER_ROW:AW_MSGBOX_PER_ROW;
    rect[2]=(frame[2]-16-(in_row-1)*8)/in_row;rect[3]=22;
    rect[0]=frame[0]+8+col*(rect[2]+8);rect[1]=frame[1]+frame[3]-rows*24+row*24-2;
}
/* UI-TEXT-BOX-CLEARANCE-64: a button as wide as its label (LABEL_W pixels) and its padding, at least
 * AW_MSGBOX_BUTTON_MIN and never wider than its share of the row; the row's buttons centred with 8 pixels between them
 * (the original's message box: buttons sized to their text, not stretched across the box). LABEL_W NULL: the shares. */
static int sized(int share,int label){int w=label+2*AW_MSGBOX_BUTTON_PAD;if(w<AW_MSGBOX_BUTTON_MIN)w=AW_MSGBOX_BUTTON_MIN;return w<share?w:share;}
void AW_MsgBoxButtonRectSized(int count,int i,const int frame[4],const int *label_w,int rect[4]) {
    int rows=(count+AW_MSGBOX_PER_ROW-1)/AW_MSGBOX_PER_ROW,row=i/AW_MSGBOX_PER_ROW,first=row*AW_MSGBOX_PER_ROW,k,total=0,x;
    int in_row=row==rows-1?count-first:AW_MSGBOX_PER_ROW;
    AW_MsgBoxButtonRect(count,i,frame,rect);
    if(!label_w)return;
    for(k=0;k<in_row;k++)total+=sized(rect[2],label_w[first+k]);
    total+=(in_row-1)*8;
    x=frame[0]+(frame[2]-total)/2;
    for(k=first;k<i;k++)x+=sized(rect[2],label_w[k])+8;
    rect[0]=x;rect[2]=sized(rect[2],label_w[i]);
}
int AW_MsgBoxButtonAtSized(int count,const int frame[4],const int *label_w,int px,int py) {
    int i,r[4];
    for(i=0;i<count && i<AW_MSGBOX_BUTTONS;i++){
        AW_MsgBoxButtonRectSized(count,i,frame,label_w,r);
        if(px>=r[0] && px<r[0]+r[2] && py>=r[1] && py<r[1]+r[3])return i;
    }
    return -1;
}
int AW_MsgBoxButtonAt(int count,const int frame[4],int px,int py) {
    int i,r[4];
    for(i=0;i<count && i<AW_MSGBOX_BUTTONS;i++){
        AW_MsgBoxButtonRect(count,i,frame,r);
        if(px>=r[0] && px<r[0]+r[2] && py>=r[1] && py<r[1]+r[3])return i;
    }
    return -1;
}
/* The death box (aw_view.c AW_ViewDraw): 280 x 96, centred, COUNT buttons in one row, 24 high, 32 above its foot. */
void AW_DeathBoxButtonRect(int count,int i,int vw,int vh,int rect[4]) {
    int x=(vw-AW_DEATHBOX_W)/2,y=(vh-AW_DEATHBOX_H)/2;
    rect[2]=(AW_DEATHBOX_W-16-(count-1)*8)/count;rect[3]=24;
    rect[0]=x+8+i*(rect[2]+8);rect[1]=y+AW_DEATHBOX_H-32;
}
int AW_DeathBoxButtonAt(int count,int vw,int vh,int px,int py) {
    int i,r[4];
    for(i=0;i<count;i++){
        AW_DeathBoxButtonRect(count,i,vw,vh,r);
        if(px>=r[0] && px<r[0]+r[2] && py>=r[1] && py<r[1]+r[3])return i;
    }
    return -1;
}
