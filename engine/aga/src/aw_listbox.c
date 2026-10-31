/* SPDX-License-Identifier: GPL-2.0-or-later
 * The console-font list box in the game (aw_listbox.h; the rules: aw_listbox_rules.c). One box at a time, on the
 * world windows' modal (aw_worldui.c AW_WorldUIOpenPanel), drawn in the CONSOLE font over the game:
 *   +------------------------------------+
 *   |               title                |
 *   | Find: seyda_                       |
 *   |  Seyda Neen                     |# |
 *   |  ...                            |  |
 *   | 1 of 214    Enter: go   Esc: close |
 *   +------------------------------------+
 * Typing filters (letters and digits; Backspace), Up/Down/PgUp/PgDn/Home/End and the wheel move, Enter or a click
 * on a row chooses, the scroll bar scrolls, Escape / F10 close. While open it holds only the shown-row list (one
 * int per row, freed on close); the rows themselves stay with the caller.
 */
#include "quakedef.h"
#include "aw_listbox.h"
#include "aw_statswin.h"
#include "aw_format.h"
#include "aw_tryalloc.h"

#define BOX_X 24
#define BOX_Y 10
#define BOX_W 272
#define BOX_H 180
#define PAD 6
#define SCROLL_W 10

static aw_listbox_t box;
static aw_listbox_spec_t spec;
static int *shown,active;

int AW_ListBoxActive(void){return active;}
/* The view behind the box (aw_ui.c AW_ModalWorldHidden, screen.c; set at the first box). The world waits while a
 * box is open, so its view does not change: the first frame renders it and the box keeps a copy (one byte per
 * pixel, only while open); every later frame restores the copy instead of rendering the world again
 * (TP-PICKER-OPEN-FRAME-COST-57: the live view behind the box cost 100 ms a frame against 16 closed). Without
 * the memory for the copy the view is rendered every frame, as before. */
extern int (*aw_listbox_over_world)(void);   /* 0 closed, 1 render the view, 2 the copy is kept */
extern int (*aw_listbox_restore)(void);      /* 1 when the kept copy was put back */
static byte *backdrop;
static long backdrop_bytes;
static int backdrop_held,backdrop_w,backdrop_h;
static int over_world(void){
    if(!active)return 0;
    if(backdrop_held && (backdrop_w!=(int)vid.width || backdrop_h!=(int)vid.height))backdrop_held=0;
    return backdrop_held?2:1;
}
static int restore(void){
    int y;
    if(!active || !backdrop_held || backdrop_w!=(int)vid.width || backdrop_h!=(int)vid.height || !vid.buffer)return 0;
    for(y=0;y<backdrop_h;y++)memcpy(vid.buffer+y*vid.rowbytes,backdrop+(long)y*backdrop_w,(size_t)backdrop_w);
    return 1;
}
static void keep(void){
    int y;
    if(backdrop_held || !backdrop || !vid.buffer || (long)vid.width*(long)vid.height>backdrop_bytes)return;
    backdrop_w=(int)vid.width;backdrop_h=(int)vid.height;
    for(y=0;y<backdrop_h;y++)memcpy(backdrop+(long)y*backdrop_w,vid.buffer+y*vid.rowbytes,(size_t)backdrop_w);
    backdrop_held=1;
}

static int char_w(void){int w=AW_ConsoleCharWidth();return w<1?8:w;}
static int char_h(void){int h=AW_ConsoleCharHeight();return h<1?8:h;}
static int row_h(void){return char_h()+2;}
static int search_y(void){return BOX_Y+PAD+char_h()+4;}
static int list_y(void){return search_y()+char_h()+8;}
static int footer_y(void){return BOX_Y+BOX_H-PAD-char_h();}
static int list_h(void){int h=footer_y()-4-list_y();return h<row_h()?row_h():h;}
static int list_rows(void){return list_h()/row_h();}
static int scroll_x(void){return BOX_X+BOX_W-PAD-SCROLL_W;}

static void text(int x,int y,const char *s,int right){
    int w=char_w();
    for(;s && *s && x+w<=right;s++,x+=w)AW_ConsoleCharacter(x,y,(unsigned char)*s);
}
static void centred(int y,const char *s){
    int w=(int)strlen(s)*char_w(),x=BOX_X+(BOX_W-w)/2;
    if(x<BOX_X+PAD)x=BOX_X+PAD;
    text(x,y,s,BOX_X+BOX_W-PAD);
}
static void release(void){
    free(shown);shown=NULL;active=0;
    free(backdrop);backdrop=NULL;backdrop_bytes=0;backdrop_held=0;
    memset(&box,0,sizeof(box));
}
static void closed(void){
    aw_listbox_spec_t was=spec;
    release();memset(&spec,0,sizeof(spec));
    if(was.closed)was.closed(was.ctx);
}
static void draw(void){
    char line[80];int i,y,rows,right,bar,dark=AW_UIColor(29,23,17),pick=AW_UIColor(62,53,36);
    keep();                                    /* the first frame's rendered view, before the box covers it */
    AW_ListBoxSetVisible(&box,rows=list_rows());
    AW_UIBox(BOX_X,BOX_Y,BOX_W,BOX_H);
    centred(BOX_Y+PAD,spec.title?spec.title:"");
    AW_UIFill(BOX_X+PAD,search_y()-2,BOX_W-2*PAD,char_h()+4,dark);
    Q_snprintf(line,sizeof(line),"Find: %s_",box.search);
    text(BOX_X+PAD+2,search_y(),line,BOX_X+BOX_W-PAD-2);
    bar=box.shown_count>rows;
    right=bar?scroll_x()-2:BOX_X+BOX_W-PAD;
    for(i=0;i<rows && box.top+i<box.shown_count;i++){
        y=list_y()+i*row_h();
        if(box.top+i==box.selection)AW_UIFill(BOX_X+PAD,y-1,right-(BOX_X+PAD),row_h(),pick);
        text(BOX_X+PAD+char_w(),y,spec.label(spec.ctx,box.shown[box.top+i]),right-2);
    }
    if(!box.shown_count)centred(list_y(),"No match");
    if(bar)AW_UIScrollbar(scroll_x(),list_y()-1,rows*row_h(),box.shown_count,rows,box.top);
    Q_snprintf(line,sizeof(line),"%d of %d  Enter: go  Esc: close",box.shown_count?box.selection+1:0,box.shown_count);
    text(BOX_X+PAD,footer_y(),line,BOX_X+BOX_W-PAD);
}
static int choose(void){
    int row=AW_ListBoxSelected(&box);
    if(row>=0 && spec.chosen)spec.chosen(spec.ctx,row);
    return 0;                                   /* the modal closes the box (closed() runs) */
}
static int key(int k,int mouse_x,int mouse_y){
    int r=AW_LB_NONE,top;
    switch(k){
    case K_UPARROW:case K_MWHEELUP:r=AW_ListBoxKey(&box,AW_LBKEY_UP);break;
    case K_DOWNARROW:case K_MWHEELDOWN:case K_TAB:r=AW_ListBoxKey(&box,AW_LBKEY_DOWN);break;
    case K_PGUP:r=AW_ListBoxKey(&box,AW_LBKEY_PAGEUP);break;
    case K_PGDN:r=AW_ListBoxKey(&box,AW_LBKEY_PAGEDOWN);break;
    case K_HOME:r=AW_ListBoxKey(&box,AW_LBKEY_HOME);break;
    case K_END:r=AW_ListBoxKey(&box,AW_LBKEY_END);break;
    case K_BACKSPACE:case K_DEL:r=AW_ListBoxKey(&box,AW_LBKEY_BACKSPACE);break;
    case K_ENTER:r=AW_ListBoxKey(&box,AW_LBKEY_CHOOSE);break;
    case K_MOUSE1:
        if(box.shown_count>box.visible){
            top=AW_UIScrollHit(mouse_x,mouse_y,scroll_x(),list_y()-1,box.visible*row_h(),box.shown_count,box.visible,box.top);
            if(top>=0){AW_ListBoxScroll(&box,top);return 1;}
        }
        if(mouse_x>=BOX_X+PAD && mouse_x<BOX_X+BOX_W-PAD && mouse_y>=list_y()-1)
            r=AW_ListBoxClick(&box,(mouse_y-(list_y()-1))/row_h());
        else if(mouse_x<BOX_X || mouse_x>=BOX_X+BOX_W || mouse_y<BOX_Y || mouse_y>=BOX_Y+BOX_H)r=AW_LB_CLOSED;
        break;
    default:
        if(k>=32 && k<127)AW_ListBoxType(&box,k);
        break;
    }
    if(r==AW_LB_CHOSEN)return choose();
    return r!=AW_LB_CLOSED;
}
int AW_ListBoxOpen(const aw_listbox_spec_t *s){
    keydest_t was=key_dest;
    if(active || !s || !s->label || s->count<1)return 0;
    if(!(shown=(int *)AW_TryCalloc((size_t)s->count,sizeof(int)))){Con_Printf("List: not enough memory.\n");return 0;}
    spec=*s;active=1;aw_listbox_over_world=over_world;aw_listbox_restore=restore;
    backdrop_bytes=(long)vid.width*(long)vid.height;backdrop_held=0;
    if(!(backdrop=(byte *)AW_TryMalloc((unsigned long)backdrop_bytes)))backdrop_bytes=0;
    AW_ListBoxReset(&box,s->count,s->label,s->ctx,shown,list_rows());
    /* typed in the console: the box replaces it (as the scene picker does) */
    if(key_dest==key_console)key_dest=key_game;
    if(!AW_WorldUIOpenPanel(draw,key,closed)){
        key_dest=was;release();memset(&spec,0,sizeof(spec));
        return 0;
    }
    return 1;
}
