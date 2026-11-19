/* SPDX-License-Identifier: GPL-2.0-or-later
 * UI-NO-SHARED-LAYOUT-67: the shared layout and its check (aw_layout.h). No engine dependencies: host tested by
 * tests/aga_ui_layout_test.c, which also lays out the screens that use it and measures what they draw. */
#include <stdio.h>
#include <string.h>
#include "aw_layout.h"

/* Every number of the layout. The frame's edge and the text's clear rows are the measured ones of the box pipeline
 * (UI-TEXT-BOX-CLEARANCE-64); the button row's bottom margin is new (the maintainer's pictures of v0.0.67-dev1: OK
 * buttons against the bottom edge). */
const aw_layout_metrics_t aw_layout_metrics={
    4,      /* edge */
    4,      /* pad */
    22,     /* button_h */
    8,      /* button_gap */
    12,     /* button_pad */
    48,     /* button_min */
    6,      /* bottom_margin */
    4,      /* content_gap */
    4       /* button_edge */
};
#define M aw_layout_metrics

static void set(int r[4],int x,int y,int w,int h){r[0]=x;r[1]=y;r[2]=w<0?0:w;r[3]=h<0?0:h;}
static int sized(int label){int w=label+2*M.button_pad;return w<M.button_min?M.button_min:w;}
void AW_LayoutBox(aw_layout_t *l,int x,int y,int w,int h,int title_h,int count,const int *label_w,int button_h) {
    int in=M.edge+M.pad,i,total=0,row_y,top,bottom,width[AW_LAYOUT_BUTTONS],bx;
    memset(l,0,sizeof(*l));
    if(count<0)count=0;
    if(count>AW_LAYOUT_BUTTONS)count=AW_LAYOUT_BUTTONS;
    if(button_h<=0)button_h=M.button_h;
    set(l->box,x,y,w,h);set(l->inner,x+in,y+in,w-2*in,h-2*in);
    top=l->inner[1];
    if(title_h>0){set(l->title,l->inner[0],top,l->inner[2],title_h);top+=title_h+M.content_gap;}
    bottom=l->inner[1]+l->inner[3];
    l->buttons=count;
    if(count){
        row_y=y+h-M.edge-M.bottom_margin-button_h;
        for(i=0;i<count;i++){width[i]=sized(label_w?label_w[i]:0);total+=width[i];}
        total+=(count-1)*M.button_gap;
        /* a row wider than the box: every button gets an equal share */
        if(total>l->inner[2]){
            int share=(l->inner[2]-(count-1)*M.button_gap)/count;
            for(i=0;i<count;i++)width[i]=share;
            total=share*count+(count-1)*M.button_gap;
        }
        bx=x+(w-total)/2;
        for(i=0;i<count;i++){set(l->button[i],bx,row_y,width[i],button_h);bx+=width[i]+M.button_gap;}
        bottom=row_y-M.content_gap;
    }
    set(l->content,l->inner[0],top,l->inner[2],bottom-top);
}
int AW_LayoutBoxHeight(int content_h,int title_h,int buttons,int button_h) {
    int h=2*M.edge+M.pad+content_h;
    if(button_h<=0)button_h=M.button_h;
    if(title_h>0)h+=title_h+M.content_gap;
    h+=buttons?M.content_gap+button_h+M.bottom_margin:M.pad;
    return h;
}
int AW_LayoutButtonAt(const aw_layout_t *l,int px,int py) {
    int i;
    for(i=0;i<l->buttons;i++){
        const int *r=l->button[i];
        if(px>=r[0] && px<r[0]+r[2] && py>=r[1] && py<r[1]+r[3])return i;
    }
    return -1;
}

/* the recorder: aw_ui.c calls it for every box, button and line of text while a check records a screen */
aw_layout_record_t *AW_LayoutRecording;
void AW_LayoutRecord(int kind,int x,int y,int w,int h,const char *label) {
    aw_layout_rect_t *r;
    if(!AW_LayoutRecording || w<=0 || h<=0)return;
    if(AW_LayoutRecording->count>=AW_LAYOUT_RECORDS){AW_LayoutRecording->dropped++;return;}
    r=&AW_LayoutRecording->rect[AW_LayoutRecording->count++];
    r->kind=kind;r->x=x;r->y=y;r->w=w;r->h=h;
    strncpy(r->label,label?label:"",sizeof(r->label)-1);r->label[sizeof(r->label)-1]=0;
}
static int is_frame(int kind){return kind==AW_LAYOUT_BOX || kind==AW_LAYOUT_BUTTON || kind==AW_LAYOUT_THIN_BOX;}
static int frame_edge(int kind){return kind==AW_LAYOUT_THIN_BOX?1:kind==AW_LAYOUT_BUTTON?M.button_edge:M.edge;}
static int holds(const aw_layout_rect_t *f,int x,int y){return x>=f->x && x<f->x+f->w && y>=f->y && y<f->y+f->h;}
static int covers(const aw_layout_rect_t *f,int x0,int y0,int x1,int y1){return x0>=f->x && y0>=f->y && x1<=f->x+f->w && y1<=f->y+f->h;}
static const char *kind_name(int kind){
    return kind==AW_LAYOUT_BOX?"box":kind==AW_LAYOUT_BUTTON?"button":kind==AW_LAYOUT_THIN_BOX?"thin box":"text";
}
static void say(char *why,int size,int *used,const char *line) {
    int n=(int)strlen(line);
    if(!why || size<=0 || *used>=size-1)return;
    if(n>size-1-*used)n=size-1-*used;
    memcpy(why+*used,line,n);*used+=n;why[*used]=0;
}
int AW_LayoutCheck(const aw_layout_record_t *record,char *why,int size) {
    int i,j,k,faults=0,used=0;char line[200];
    if(why && size>0)why[0]=0;
    if(!record)return 0;
    if(record->dropped){
        snprintf(line,sizeof(line),"%d drawn rectangles past the record's %d were not checked\n",record->dropped,AW_LAYOUT_RECORDS);
        say(why,size,&used,line);faults++;
    }
    for(i=0;i<record->count;i++){
        const aw_layout_rect_t *r=&record->rect[i],*parent=NULL;int e,clear;
        if(r->kind!=AW_LAYOUT_TEXT && r->kind!=AW_LAYOUT_BUTTON)continue;
        /* its box: the last frame drawn before it that holds its top left corner (a button's box is never a button) */
        for(k=i-1;k>=0 && !parent;k--){
            const aw_layout_rect_t *f=&record->rect[k];
            if(!is_frame(f->kind) || !holds(f,r->x,r->y))continue;
            if(r->kind==AW_LAYOUT_BUTTON && f->kind!=AW_LAYOUT_BOX)continue;
            parent=f;
        }
        if(!parent)continue;   /* over the view (a HUD line): only the overlap rule below */
        /* a text keeps a clear pixel from a box's or a thin box's frame; a button's label may meet the inner edge of the
         * thick button frame (22 rows hold the 14-row inner area and a 13-row label) but never lie on the frame */
        e=frame_edge(parent->kind);clear=r->kind==AW_LAYOUT_TEXT && parent->kind!=AW_LAYOUT_BUTTON?1:0;
        if(r->x<parent->x+e+clear || r->y<parent->y+e+clear || r->x+r->w>parent->x+parent->w-e-clear ||
           r->y+r->h>parent->y+parent->h-e-clear){
            snprintf(line,sizeof(line),"%s \"%s\" at %d,%d %dx%d touches or leaves its %s at %d,%d %dx%d\n",kind_name(r->kind),
                     r->label,r->x,r->y,r->w,r->h,kind_name(parent->kind),parent->x,parent->y,parent->w,parent->h);
            say(why,size,&used,line);faults++;
        }
        if(r->kind==AW_LAYOUT_BUTTON && parent->y+parent->h-e-(r->y+r->h)<M.bottom_margin){
            snprintf(line,sizeof(line),"button \"%s\" stands %d rows above its box's bottom edge (at least %d)\n",r->label,
                     parent->y+parent->h-e-(r->y+r->h),M.bottom_margin);
            say(why,size,&used,line);faults++;
        }
    }
    /* two texts on top of one another: never, unless a frame drawn between them covers the first one there */
    for(i=0;i<record->count;i++){
        const aw_layout_rect_t *a=&record->rect[i];
        if(a->kind!=AW_LAYOUT_TEXT)continue;
        for(j=i+1;j<record->count;j++){
            const aw_layout_rect_t *b=&record->rect[j];int x0,y0,x1,y1,hidden=0;
            if(b->kind!=AW_LAYOUT_TEXT)continue;
            x0=a->x>b->x?a->x:b->x;y0=a->y>b->y?a->y:b->y;
            x1=a->x+a->w<b->x+b->w?a->x+a->w:b->x+b->w;y1=a->y+a->h<b->y+b->h?a->y+a->h:b->y+b->h;
            if(x0>=x1 || y0>=y1)continue;
            for(k=i+1;k<j && !hidden;k++)hidden=is_frame(record->rect[k].kind) && covers(&record->rect[k],x0,y0,x1,y1);
            if(hidden)continue;
            snprintf(line,sizeof(line),"text \"%s\" at %d,%d %dx%d and text \"%s\" at %d,%d %dx%d are on top of one another\n",
                     a->label,a->x,a->y,a->w,a->h,b->label,b->x,b->y,b->w,b->h);
            say(why,size,&used,line);faults++;
        }
    }
    return faults;
}
