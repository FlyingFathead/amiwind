/* SPDX-License-Identifier: GPL-2.0-or-later */
/* CONTAINER-WINDOW-59: the container strip's pure rules (aw_cstrip.h); no engine state, native-tested. */
#include <stddef.h>
#include "aw_cstrip.h"
void AW_CStripClamp(aw_cstrip_list_t *list){
    int s,columns=list->columns>0?list->columns:1;
    for(s=0;s<2;s++){
        int n=list->count[s];
        if(n<0)n=list->count[s]=0;
        if(n>AW_CSTRIP_ROWS)n=list->count[s]=AW_CSTRIP_ROWS;
        if(list->selected[s]>=n)list->selected[s]=n-1;
        if(list->selected[s]<0)list->selected[s]=0;
        if(list->first[s]>list->selected[s])list->first[s]=list->selected[s];
        if(list->selected[s]>=list->first[s]+columns)list->first[s]=list->selected[s]-columns+1;
        if(list->first[s]>n-columns)list->first[s]=n-columns;
        if(list->first[s]<0)list->first[s]=0;
    }
    if(list->side!=AW_CSTRIP_INVENTORY)list->side=AW_CSTRIP_CONTAINER;
}
void AW_CStripMove(aw_cstrip_list_t *list,int delta){
    list->selected[list->side]+=delta;
    AW_CStripClamp(list);
}
void AW_CStripSide(aw_cstrip_list_t *list,int side){
    list->side=side==AW_CSTRIP_CONTAINER || side==AW_CSTRIP_INVENTORY?side:!list->side;
    AW_CStripClamp(list);
}
const aw_cstrip_entry_t *AW_CStripSelected(const aw_cstrip_list_t *list){
    int s=list->side;
    return list->count[s]>0 && list->selected[s]>=0 && list->selected[s]<list->count[s]?&list->row[s][list->selected[s]]:NULL;
}
int AW_CStripCell(const aw_cstrip_list_t *list,int x,int y,int left,int top,int w,int h){
    int c,i;
    if(w<=0 || h<=0 || x<left || y<top || y>=top+h)return -1;
    c=(x-left)/w;
    if(c>=list->columns)return -1;
    i=list->first[list->side]+c;
    return i<list->count[list->side]?i:-1;
}
