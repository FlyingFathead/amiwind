/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_listbox_rules.c alone (TP-PICKER-57): the search (letters and digits, case ignored, as you type), the filter
 * keeping the selected row, Up/Down/PgUp/PgDn/Home/End and the scroll position, clicks, Backspace, Enter only on a
 * row; the settlements table reader (AWTP1 header and size checks, signed coordinates) and the teleport line it
 * makes (the existing dbg tp X Y [Z] path). */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_listbox.h"

static const char *const places[]={"Ald-ruhn","Balmora","Caldera","Gnisis","Khuul","Seyda Neen","Suran",
    "Tel Aruhn","Tel Branora","Tel Mora","Vivec","Vivec, Arena","Vivec, Foreign Quarter"};
#define PLACES ((int)(sizeof(places)/sizeof(places[0])))
static int label_calls;
static const char *label(void *ctx,int row){(void)ctx;label_calls++;return row>=0 && row<PLACES?places[row]:"";}
static void type(aw_listbox_t *b,const char *s){for(;*s;s++)assert(AW_ListBoxType(b,(unsigned char)*s));}

static void put32(unsigned char *p,long v){unsigned long u=(unsigned long)v;p[0]=(unsigned char)(u>>24);p[1]=(unsigned char)(u>>16);p[2]=(unsigned char)(u>>8);p[3]=(unsigned char)u;}

int main(void){
    aw_listbox_t b;int shown[PLACES],i;char line[64];
    unsigned char table[AW_TP_HEADER+2*AW_TP_ROW];aw_tp_place_t p;

    /* matching: letters and digits only, case ignored, anywhere in the label */
    assert(AW_ListBoxMatches("Ald-ruhn","aldruhn") && AW_ListBoxMatches("Ald-ruhn","ALD RU") && AW_ListBoxMatches("Seyda Neen","neen"));
    assert(AW_ListBoxMatches("Vivec, Arena","vivecar") && !AW_ListBoxMatches("Vivec","vivecar"));
    assert(AW_ListBoxMatches("Balmora","") && AW_ListBoxMatches("Balmora","  -") && !AW_ListBoxMatches("Balmora","x"));
    assert(!AW_ListBoxMatches(NULL,"a") && AW_ListBoxMatches(NULL,NULL));

    /* everything shown at first, the first row selected */
    AW_ListBoxReset(&b,PLACES,label,NULL,shown,5);
    assert(b.shown_count==PLACES && b.selection==0 && b.top==0 && AW_ListBoxSelected(&b)==0);
    /* moving keeps the selection on screen; the ends stop */
    assert(AW_ListBoxKey(&b,AW_LBKEY_UP)==AW_LB_NONE && b.selection==0);
    for(i=0;i<6;i++)AW_ListBoxKey(&b,AW_LBKEY_DOWN);
    assert(b.selection==6 && b.top==2);
    AW_ListBoxKey(&b,AW_LBKEY_PAGEDOWN);assert(b.selection==11 && b.top==7);
    AW_ListBoxKey(&b,AW_LBKEY_END);assert(b.selection==PLACES-1 && b.top==PLACES-5);
    AW_ListBoxKey(&b,AW_LBKEY_PAGEDOWN);assert(b.selection==PLACES-1);
    AW_ListBoxKey(&b,AW_LBKEY_HOME);assert(b.selection==0 && b.top==0);
    AW_ListBoxKey(&b,AW_LBKEY_PAGEUP);assert(b.selection==0);

    /* typing filters as you type; the selected row stays selected while it is shown */
    AW_ListBoxKey(&b,AW_LBKEY_DOWN);AW_ListBoxKey(&b,AW_LBKEY_DOWN);              /* Caldera */
    type(&b,"a");assert(AW_ListBoxSelected(&b)==2);                            /* every place with an a */
    type(&b,"r");assert(b.shown_count==3 && AW_ListBoxSelected(&b)==7);        /* ar: Tel Aruhn, Vivec, Arena, Vivec, Foreign Quarter */
    assert(!strcmp(b.search,"ar"));
    type(&b,"en");assert(b.shown_count==1 && AW_ListBoxSelected(&b)==11);      /* aren: Vivec, Arena */
    assert(AW_ListBoxKey(&b,AW_LBKEY_CHOOSE)==AW_LB_CHOSEN);
    type(&b,"q");assert(b.shown_count==0 && AW_ListBoxSelected(&b)==-1);
    assert(AW_ListBoxKey(&b,AW_LBKEY_CHOOSE)==AW_LB_NONE);                       /* nothing to choose */
    assert(AW_ListBoxKey(&b,AW_LBKEY_DOWN)==AW_LB_NONE && AW_ListBoxSelected(&b)==-1);
    assert(AW_ListBoxKey(&b,AW_LBKEY_BACKSPACE)==AW_LB_NONE && b.shown_count==1);
    for(i=0;i<4;i++)AW_ListBoxKey(&b,AW_LBKEY_BACKSPACE);
    assert(!b.search[0] && b.shown_count==PLACES && AW_ListBoxSelected(&b)==11);  /* still Vivec, Arena */
    assert(AW_ListBoxKey(&b,AW_LBKEY_BACKSPACE)==AW_LB_NONE && b.shown_count==PLACES);
    /* spaces: none first, never two; control characters are not typed; the field has a limit */
    assert(AW_ListBoxType(&b,' ') && !b.search[0]);
    type(&b,"tel  m");assert(!strcmp(b.search,"tel m") && b.shown_count==1 && AW_ListBoxSelected(&b)==9);
    assert(!AW_ListBoxType(&b,'\n') && !AW_ListBoxType(&b,200));
    for(i=0;i<40;i++)AW_ListBoxType(&b,'z');
    assert(strlen(b.search)==AW_LISTBOX_SEARCH);
    for(i=0;i<40;i++)AW_ListBoxKey(&b,AW_LBKEY_BACKSPACE);
    assert(AW_ListBoxKey(&b,AW_LBKEY_CLOSE)==AW_LB_CLOSED);

    /* clicks: a row on screen chooses it, below the rows nothing; the scroll bar moves the window */
    AW_ListBoxReset(&b,PLACES,label,NULL,shown,5);
    AW_ListBoxScroll(&b,4);assert(b.top==4 && b.selection==4);
    assert(AW_ListBoxClick(&b,2)==AW_LB_CHOSEN && AW_ListBoxSelected(&b)==6);
    assert(AW_ListBoxClick(&b,5)==AW_LB_NONE && AW_ListBoxClick(&b,-1)==AW_LB_NONE);
    AW_ListBoxScroll(&b,99);assert(b.top==PLACES-5 && b.selection==PLACES-5);
    AW_ListBoxScroll(&b,-3);assert(b.top==0 && b.selection==4);
    type(&b,"khuul");assert(AW_ListBoxClick(&b,1)==AW_LB_NONE && AW_ListBoxClick(&b,0)==AW_LB_CHOSEN && AW_ListBoxSelected(&b)==4);
    /* a smaller window keeps the selection on it */
    AW_ListBoxReset(&b,PLACES,label,NULL,shown,8);AW_ListBoxKey(&b,AW_LBKEY_END);
    AW_ListBoxSetVisible(&b,3);assert(b.top==PLACES-3 && b.selection==PLACES-1);
    /* labels are asked for only when filtering (and drawing, in the game) */
    label_calls=0;AW_ListBoxKey(&b,AW_LBKEY_UP);assert(!label_calls);

    /* the settlements table */
    memset(table,0,sizeof(table));
    memcpy(table,"AWTP",4);table[5]=1;table[7]=AW_TP_ROW;put32(table+8,2);
    memcpy(table+AW_TP_HEADER,"Balmora",7);put32(table+AW_TP_HEADER+32,-20536);put32(table+AW_TP_HEADER+36,-13960);
    put32(table+AW_TP_HEADER+40,378);table[AW_TP_HEADER+44]=AW_TP_HAS_Z|AW_TP_DOOR;table[AW_TP_HEADER+45]=4;
    memset(table+AW_TP_HEADER+AW_TP_ROW,'x',AW_TP_NAME);                         /* no NUL: cut at 31 */
    put32(table+AW_TP_HEADER+AW_TP_ROW+32,12288);put32(table+AW_TP_HEADER+AW_TP_ROW+36,-36864);
    assert(AW_TpPlacesRows(table,sizeof(table))==2);
    assert(AW_TpPlacesRows(table,sizeof(table)-1)==-1 && AW_TpPlacesRows(table,8)==-1 && AW_TpPlacesRows(NULL,64)==-1);
    table[5]=2;assert(AW_TpPlacesRows(table,sizeof(table))==-1);table[5]=1;
    table[7]=40;assert(AW_TpPlacesRows(table,sizeof(table))==-1);table[7]=AW_TP_ROW;
    table[0]='X';assert(AW_TpPlacesRows(table,sizeof(table))==-1);table[0]='A';
    AW_TpPlacesRow(table,0,&p);
    assert(!strcmp(p.name,"Balmora") && p.x==-20536 && p.y==-13960 && p.z==378 && p.flags==3 && p.cells==4);
    assert(AW_TpPlacesCommand(&p,line,sizeof(line))>0 && !strcmp(line,"aw_teleport -20536 -13960 378\n"));
    AW_TpPlacesRow(table,1,&p);
    assert(strlen(p.name)==AW_TP_NAME-1 && p.x==12288 && p.y==-36864 && p.flags==0);
    assert(AW_TpPlacesCommand(&p,line,sizeof(line))>0 && !strcmp(line,"aw_teleport 12288 -36864\n"));  /* no z: the floor below */
    assert(AW_TpPlacesCommand(&p,line,20)==-1 && AW_TpPlacesCommand(NULL,line,sizeof(line))==-1);
    p.x=-2147483647L;p.y=2147483647L;p.z=-1;p.flags=AW_TP_HAS_Z;
    assert(AW_TpPlacesCommand(&p,line,sizeof(line))>0 && !strcmp(line,"aw_teleport -2147483647 2147483647 -1\n"));
    puts("listbox rules ok");
    return 0;
}
