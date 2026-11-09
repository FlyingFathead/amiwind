/* SPDX-License-Identifier: GPL-2.0-or-later */
/* INVENTORY-ARROWS-SCROLL-62: the one keyboard rule of every list window (inventory, containers, barter, dialogue
 * topics, spell lists, menus): Up/W/wheel up and Down/S/wheel down move the selection by one, Page Up/Down by a page,
 * Home/End to the ends; the list scrolls so the selection stays shown. Enter acts and Left/Right or Tab change column
 * or tab: those stay the window's own. Header only, no state: SEL and TOP are the window's. */
#ifndef AW_LISTNAV_H
#define AW_LISTNAV_H
/* the key numbers come from keys.h, included by the caller (through quakedef.h) */
/* 1 when KEY is a list key and SEL/TOP were moved (clamped to 0..COUNT-1, TOP keeping SEL in VISIBLE rows). */
static inline int AW_ListNavKey(int key,int *sel,int *top,int count,int visible){
    int s=*sel;
    if(key==K_UPARROW || key=='w' || key=='W' || key==K_MWHEELUP)s--;
    else if(key==K_DOWNARROW || key=='s' || key=='S' || key==K_MWHEELDOWN)s++;
    else if(key==K_PGUP)s-=visible>1?visible:1;
    else if(key==K_PGDN)s+=visible>1?visible:1;
    else if(key==K_HOME)s=0;
    else if(key==K_END)s=count-1;
    else return 0;
    if(s>count-1)s=count-1;
    if(s<0)s=0;
    *sel=s;
    if(top){
        if(visible<1)visible=1;
        if(*top>s)*top=s;
        if(s>=*top+visible)*top=s-visible+1;
        if(*top<0)*top=0;
    }
    return 1;
}
#endif
