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
    /* CRIME-RELEASE-LINE-CUT-62: the box shows every line while it fits. The 15-day jail of session s9: the release
     * line and 12 changed skills = 13 lines, one OK row, 10-pixel lines: 8+130+8+24 = 170 of a 200 screen: all 13
     * (the drawing stopped after 3 before). Too many for the screen: as many as fit, (200-8-16-24)/10 = 15. */
    assert(AW_MsgBoxLinesShown(13,1,200,10)==13);
    assert(AW_MsgBoxLinesShown(3,1,200,10)==3);
    assert(AW_MsgBoxLinesShown(40,1,200,10)==15);
    assert(AW_MsgBoxLinesShown(40,0,480,8)==AW_MSGBOX_LINES);             /* the drawing's own limit */
    assert(AW_MsgBoxLinesShown(0,1,200,10)==1 && AW_MsgBoxLinesShown(5,8,200,10)==1);   /* never below one line */
    /* the text holds a long release whole: 13 lines of up to 60 characters */
    {
        char text[13*61+1];int i;
        for(i=0;i<13;i++){memset(text+i*61,'x',60);text[i*61+60]='\n';}
        text[13*61]=0;
        AW_MsgBoxOpen(&m,text,yes_no,1);
        assert(strlen(m.text)==13*61);
    }
    /* MSGBOX-NO-CURSOR-62: the pointer's hit test, per box kind, on the 320 x 200 screen; the centre of every
     * button picks that button, a point beside the buttons or in the text picks none */
    {
        int f[4],r[4],i,k,counts[4]={1,2,3,5};
        /* a script's box (1, 2, 3 buttons in a row; 5 in two rows) and the failed-load box (OK / Load Game) */
        for(k=0;k<4;k++){
            AW_MsgBoxLayout(counts[k],320,200,24,f);
            assert(f[2]==300 && f[0]==10 && f[1]+f[3]<=200);
            for(i=0;i<counts[k];i++){
                AW_MsgBoxButtonRect(counts[k],i,f,r);
                assert(r[0]>=f[0] && r[0]+r[2]<=f[0]+f[2] && r[1]+r[3]<=f[1]+f[3]+2 && r[3]==22);
                assert(AW_MsgBoxButtonAt(counts[k],f,r[0]+r[2]/2,r[1]+r[3]/2)==i);
                assert(AW_MsgBoxButtonAt(counts[k],f,r[0]-1,r[1])!=i);              /* just left of it: not this one */
            }
            assert(AW_MsgBoxButtonAt(counts[k],f,f[0]+f[2]/2,f[1]+6)==-1);         /* the text */
            assert(AW_MsgBoxButtonAt(counts[k],f,0,0)==-1);                          /* outside the box */
        }
        /* the failed-load box: OK left, Load Game right */
        AW_MsgBoxLayout(2,320,200,16,f);AW_MsgBoxButtonRect(2,1,f,r);
        assert(AW_MsgBoxButtonAt(2,f,r[0]+4,r[1]+4)==1);
        AW_MsgBoxButtonRect(2,0,f,r);assert(AW_MsgBoxButtonAt(2,f,r[0]+4,r[1]+4)==0);
        /* the death box: Yes / No, and Yes / No / Retry fight */
        for(k=2;k<=3;k++)for(i=0;i<k;i++){
            AW_DeathBoxButtonRect(k,i,320,200,r);
            assert(r[3]==24 && r[0]>=(320-AW_DEATHBOX_W)/2 && r[0]+r[2]<=(320+AW_DEATHBOX_W)/2);
            assert(AW_DeathBoxButtonAt(k,320,200,r[0]+r[2]/2,r[1]+12)==i);
            assert(AW_DeathBoxButtonAt(k,320,200,r[0]+r[2]/2,r[1]-1)==-1);
        }
        assert(AW_DeathBoxButtonAt(3,320,200,160,100-AW_DEATHBOX_H/2+8)==-1);       /* the question */
    }
    printf("msgbox rules ok\n");
    return 0;
}
