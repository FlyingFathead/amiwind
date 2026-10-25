/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_msgbox_rules.c alone: MWScript's message text (OpenMW formatMessage), how long a box without buttons stays,
 * a box with buttons (keys, the choice read once, a new box replacing a shown one). */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_msgbox.h"

static const char *fmt(const char *format,const float *v,int n) {
    static char out[AW_MSGBOX_TEXT];
    AW_MsgBoxFormat(out,sizeof(out),format,v,n);
    return out;
}

int main(void) {
    float v[3]={1.5f,42.75f,-3.0f};char small[8];aw_msgbox_t m;
    const char *yes_no[2]={"Yes","No"},*many[14]={"1","2","3","4","5","6","7","8","9","10","11","12","13","14"};
    /* the conversions, in order; precision and width; %% a percent sign */
    assert(!strcmp(fmt("%.1f and %d",v,2),"1.5 and 42"));
    assert(!strcmp(fmt("%.0f gold",v+1,1),"43 gold"));
    assert(!strcmp(fmt("%g",v,1),"1.5"));
    assert(!strcmp(fmt("%G|%F",v,2),"1.5|42.750000"));
    assert(!strcmp(fmt("%5.2f",v,1)," 1.50"));
    assert(!strcmp(fmt("%3d",v+1,1)," 42"));
    assert(!strcmp(fmt("%D",v+2,1),"-3"));
    assert(!strcmp(fmt("100%%",v,0),"100%"));
    /* strings are not passed: kept as written; a missing number reads 0; other letters kept */
    assert(!strcmp(fmt("Hello %s, %S",v,0),"Hello %s, %S"));
    assert(!strcmp(fmt("%d %d",v,1),"1 0"));
    assert(!strcmp(fmt("%q",v,1),"%q"));
    assert(!strcmp(fmt("trailing %",v,0),"trailing %"));
    assert(!strcmp(fmt("plain text",NULL,0),"plain text"));
    /* the output is bounded and always ended */
    assert(AW_MsgBoxFormat(small,sizeof(small),"abcdefghij",v,0)==7 && !strcmp(small,"abcdefg"));
    assert(AW_MsgBoxFormat(small,sizeof(small),"%f",v,1)==7 && small[7]==0);
    /* a box without buttons stays its length times 0.1 s, 3 to 10 s */
    assert(AW_MsgBoxSeconds("short")==3);
    {double s=AW_MsgBoxSeconds("0123456789012345678901234567890123456789");assert(s>3.99 && s<4.01);}
    {char text[200];memset(text,'x',199);text[199]=0;assert(AW_MsgBoxSeconds(text)==10);}
    /* a box with buttons: -1 until a choice; keys move and choose; the choice is read once */
    AW_MsgBoxReset(&m);
    assert(AW_MsgBoxTake(&m)==-1);
    AW_MsgBoxOpen(&m,"Pay the toll?",yes_no,2);
    assert(m.open && m.count==2 && m.selection==0 && AW_MsgBoxTake(&m)==-1);
    assert(AW_MsgBoxKey(&m,AW_MSGKEY_NEXT)==-1 && m.selection==1);
    assert(AW_MsgBoxKey(&m,AW_MSGKEY_NEXT)==-1 && m.selection==0);
    assert(AW_MsgBoxKey(&m,AW_MSGKEY_PREVIOUS)==-1 && m.selection==1);
    assert(AW_MsgBoxKey(&m,AW_MSGKEY_CHOOSE)==1 && !m.open);
    assert(AW_MsgBoxTake(&m)==1 && AW_MsgBoxTake(&m)==-1);
    assert(AW_MsgBoxKey(&m,AW_MSGKEY_CHOOSE)==-1);                       /* closed: keys do nothing */
    /* digits choose that button; past the buttons they do nothing */
    AW_MsgBoxOpen(&m,"Pick",yes_no,2);
    assert(AW_MsgBoxKey(&m,AW_MSGKEY_DIGIT+3)==-1 && m.open);
    assert(AW_MsgBoxKey(&m,AW_MSGKEY_DIGIT+2)==1 && AW_MsgBoxTake(&m)==1);
    /* a new box replaces a shown one and forgets the last choice; buttons past the limit are left out */
    AW_MsgBoxOpen(&m,"First",yes_no,2);
    AW_MsgBoxKey(&m,AW_MSGKEY_CHOOSE);
    AW_MsgBoxOpen(&m,"Second",many,14);
    assert(m.open && !strcmp(m.text,"Second") && m.count==AW_MSGBOX_BUTTONS && AW_MsgBoxTake(&m)==-1);
    assert(!strcmp(m.button[11],"12"));
    AW_MsgBoxOpen(&m,"None",yes_no,0);                                    /* no buttons: not a box here */
    assert(!strcmp(m.text,"Second"));
    printf("msgbox rules ok\n");
    return 0;
}
