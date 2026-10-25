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
