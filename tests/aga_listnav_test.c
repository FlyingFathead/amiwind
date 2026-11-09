/* SPDX-License-Identifier: GPL-2.0-or-later */
/* INVENTORY-ARROWS-SCROLL-62: the shared list rule (aw_listnav.h). */
#include <assert.h>
#include <stdio.h>
typedef int qboolean;
#include "keys.h"
#include "aw_listnav.h"
int main(void){
    int sel=0,top=0;
    assert(AW_ListNavKey(K_DOWNARROW,&sel,&top,10,4) && sel==1 && top==0);
    assert(AW_ListNavKey(K_DOWNARROW,&sel,&top,10,4) && AW_ListNavKey(K_DOWNARROW,&sel,&top,10,4) && sel==3 && top==0);
    assert(AW_ListNavKey(K_DOWNARROW,&sel,&top,10,4) && sel==4 && top==1);            /* the list scrolls */
    assert(AW_ListNavKey(K_END,&sel,&top,10,4) && sel==9 && top==6);
    assert(AW_ListNavKey(K_DOWNARROW,&sel,&top,10,4) && sel==9);                      /* stops at the end */
    assert(AW_ListNavKey(K_PGUP,&sel,&top,10,4) && sel==5 && top==5);
    assert(AW_ListNavKey(K_UPARROW,&sel,&top,10,4) && sel==4 && top==4);
    assert(AW_ListNavKey(K_HOME,&sel,&top,10,4) && sel==0 && top==0);
    assert(AW_ListNavKey(K_UPARROW,&sel,&top,10,4) && sel==0);                        /* stops at the top */
    assert(AW_ListNavKey('s',&sel,&top,10,4) && sel==1);
    assert(AW_ListNavKey(K_MWHEELUP,&sel,&top,10,4) && sel==0);
    assert(!AW_ListNavKey(K_ENTER,&sel,&top,10,4) && !AW_ListNavKey(K_LEFTARROW,&sel,&top,10,4) &&
           !AW_ListNavKey(K_TAB,&sel,&top,10,4));                                      /* the window's own keys */
    sel=3;assert(AW_ListNavKey(K_DOWNARROW,&sel,NULL,0,4) && sel==0);                   /* an empty list */
    puts("listnav ok");return 0;
}
