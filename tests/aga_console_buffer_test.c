/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "quakedef.h"
#include <assert.h>
extern int con_current,con_x,con_linewidth,con_totallines,con_backscroll,con_vislines;
extern char *con_text;
extern void Con_Print(char *),Con_Linefeed(void);
viddef_t vid;double realtime;
static int small=1;
int AW_ConsoleCharWidth(void){return small?4:8;}
int AW_ConsoleCharHeight(void){return small?6:8;}
void S_LocalSound(char *s){}
void Q_memset(void *p,int v,int n){memset(p,v,n);}
int main(void){
 static char buffer[16384];int old;char *last;
 con_text=buffer;con_linewidth=-1;vid.width=320;con_vislines=100;
 Con_CheckResize();assert(con_linewidth==78);
 Con_Print("first line\n0123456789012345678901234567890123456789KEEP_RIGHT_EDGE\n");
 small=0;Con_CheckResize();assert(con_linewidth==38);
 last=con_text+(con_current%con_totallines)*con_linewidth;
 assert(!memcmp(last,"89KEEP_RIGHT_EDGE",17));
 Con_Print("partial");small=1;Con_CheckResize();Con_Print("-continued\n");
 last=con_text+(con_current%con_totallines)*con_linewidth;
 assert(!memcmp(last,"partial-continued",17));
 Con_Print("newest\n");con_backscroll=2;old=con_backscroll;
 Con_Print("background log\n");assert(con_backscroll==old+1);
 assert(Con_ScrollPage()==13);assert(Con_ScrollMax()>0);
 return 0;
}
