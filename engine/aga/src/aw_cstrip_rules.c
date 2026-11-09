/* SPDX-License-Identifier: GPL-2.0-or-later */
/* CONTAINER-WINDOW-59: the container strip's pure rules (aw_cstrip.h); no engine state, native-tested. */
#include <stddef.h>
#include <stdio.h>
#include "aw_cstrip.h"
int AW_CStripTakeLine(char *out,int size,const char *name,int count,int stolen,const char *from,int total){
    int n;
    if(!out || size<2){return 0;}
    if(from)n=snprintf(out,(size_t)size,"Took %d item%s from %s%s",total,total==1?"":"s",from?from:"",stolen?" (stolen)":"");
    else if(count>1)n=snprintf(out,(size_t)size,"Took %s x %d%s",name?name:"",count,stolen?" (stolen)":"");
    else n=snprintf(out,(size_t)size,"Took %s%s",name?name:"",stolen?" (stolen)":"");
    return n<0?0:n>=size?size-1:n;
}
void AW_CStripClamp(aw_cstrip_list_t *list){
    int s,columns=list->columns>0?list->columns:1;
    for(s=0;s<2;s++){
        int n=list->count[s];
        if(n<0)n=list->count[s]=0;
        if(n>list->cap[s])n=list->count[s]=list->cap[s];
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
/* LOOT-WINDOW-LAYOUT-60: the strip's rows from the bottom of the screen up: the frame, the key help, the properties and
 * the name lines (console font, CHAR_H tall), the cells, the title row with its buttons, each with room around it. The
 * strip starts at the view's bottom, higher when the rows need it. */
void AW_CStripLayout(int width,int height,int view_bottom,int char_w,int char_h,aw_cstrip_layout_t *o){
    int line_h,need;
    if(char_h<4)char_h=8;
    if(char_w<1)char_w=8;
    line_h=char_h+2;
    o->char_h=char_h;o->line_h=line_h;o->left=AW_CSTRIP_FRAME+8;
    /* frame, gap, title row (buttons), gap, cells, gap, three text lines, gap, frame */
    need=AW_CSTRIP_FRAME+AW_CSTRIP_GAP+AW_CSTRIP_TITLE+AW_CSTRIP_GAP+AW_CSTRIP_CELL+AW_CSTRIP_GAP+3*line_h+AW_CSTRIP_GAP+
         AW_CSTRIP_FRAME;
    o->top=view_bottom<height-need?view_bottom:height-need;
    if(o->top<0)o->top=0;
    o->title_y=o->top+AW_CSTRIP_FRAME+AW_CSTRIP_GAP;
    o->cells_y=o->title_y+AW_CSTRIP_TITLE+AW_CSTRIP_GAP;
    o->name_y=o->cells_y+AW_CSTRIP_CELL+AW_CSTRIP_GAP;
    o->props_y=o->name_y+line_h;
    o->keys_y=o->props_y+line_h;
    o->bottom=height;
    o->columns=(width-2*o->left)/AW_CSTRIP_CELL;
    if(o->columns>AW_CSTRIP_COLUMNS)o->columns=AW_CSTRIP_COLUMNS;
    if(o->columns<1)o->columns=1;
    o->char_w=char_w;
    o->text_columns=(width-o->left-AW_CSTRIP_FRAME-4)/char_w;
}
int AW_CStripCell(const aw_cstrip_list_t *list,int x,int y,int left,int top,int w,int h){
    int c,i;
    if(w<=0 || h<=0 || x<left || y<top || y>=top+h)return -1;
    c=(x-left)/w;
    if(c>=list->columns)return -1;
    i=list->first[list->side]+c;
    return i<list->count[list->side]?i:-1;
}
