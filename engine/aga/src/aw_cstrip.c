/* SPDX-License-Identifier: GPL-2.0-or-later */
/* CONTAINER-WINDOW-59: the container strip in the game (aw_cstrip.h). E on an unlocked container opens it; the strip
 * is a box along the bottom of the screen, up to the view, with one row of cells (picture and count), the selected
 * entry's name below and the keys. Its second side lists what the player carries, to put in. Keys: A / D or the
 * arrows select, E or Enter takes (or puts) one, Q the whole stack, T takes everything, Tab / W / S the other side,
 * Esc closes. Mouse: a cell selects, the selected cell again takes (or puts) one; the title row's side names, Take
 * All and Close. All of it is allocated on open and freed on close (no resident cost while closed). */
#include "quakedef.h"
#include "aw_inventory.h"
#include "aw_icons.h"
#include "aw_tryalloc.h"
#include "aw_cstrip.h"
#define STRIP_H 76           /* the strip's height at the least (320 x 200: from y 124) */
#define STRIP_CELL 36        /* a cell: the 32 x 32 picture, its frame and a gap */
#define STRIP_COLUMNS 16     /* cells in view at most (a 640-wide screen) */
#define STRIP_TITLE 14
#define STRIP_BUTTON_W 56
typedef struct {
    aw_cstrip_list_t list;
    aw_icon_t icon[STRIP_COLUMNS];
    unsigned reference;
    int owned;
    char title[40];
} strip_t;
static strip_t *strip;
static int mouse_x=160,mouse_y=160;
/* CONTAINER-STRIP-REDRAW-COST-59: the whole screen is copied out only for a few frames after the strip changed (open,
 * a key, the mouse, a take or a put); in between only the view is (the strip is drawn into the buffer every frame) */
#define STRIP_DIRTY_FRAMES 2
static int strip_dirty;
static int strip_pictures_pending;   /* AREA-TABLES-59: the next drawn frame's picture loads are measured */
extern int scr_copyeverything;
int AW_CStripActive(void){return strip!=NULL;}
static int strip_open(unsigned reference,const char *name,int owned);
/* aw_placed.c AW_PlacedInit: E on containers opens the strip; the input, drawing and prompt reach it (hooks only, no
 * command, no variable, nothing allocated) */
void AW_CStripInit(void){
    aw_container_open=strip_open;aw_container_lock=AW_ObjectLockLevel;
    aw_cstrip_mouse=AW_CStripMouse;aw_cstrip_key=AW_CStripKey;aw_cstrip_draw=AW_CStripDraw;aw_cstrip_open_now=AW_CStripActive;
}
static void strip_close(void){
    if(strip){free(strip);strip=NULL;}
    AW_ContainerRelease();      /* CONTAINER-STRIP-TAKE-STALL-59 */
    strip_dirty=STRIP_DIRTY_FRAMES;   /* the frames after it closed show the view without it */
    IN_AWClearButtons();
}
/* the name an entry already had on either side (no disk read for it again after a take or a put) */
static const aw_cstrip_entry_t *strip_known(const aw_cstrip_list_t *old,const char *id){
    int s,i;
    if(!old)return NULL;
    for(s=0;s<2;s++)for(i=0;i<old->count[s];i++)if(!Q_strcasecmp((char *)old->row[s][i].id,(char *)id))return &old->row[s][i];
    return NULL;
}
/* the two sides from the container's contents now (data + deltas) and the player's items; names already known are
 * kept, so a take or a put reads only the contents again, never every item's catalogue row */
static void strip_fill(void){
    aw_container_item_t items[AW_CONTAINER_ITEMS];aw_inventory_item_t item;aw_cstrip_list_t *l=&strip->list,*old;
    const aw_cstrip_entry_t *known;int n,i,k;
    old=(aw_cstrip_list_t *)AW_TryMalloc(sizeof(*old));
    if(old)memcpy(old,l,sizeof(*old));
    AW_InventoryBatchBegin();   /* the names below share one open of the item file (TRADEHOUSE-LONG-FRAME-59) */
    n=AW_ContainerContents(strip->reference,items,AW_CONTAINER_ITEMS,NULL);
    for(i=k=0;i<n && k<AW_CSTRIP_ROWS;i++){
        aw_cstrip_entry_t *e=&l->row[AW_CSTRIP_CONTAINER][k];
        if(items[i].count<=0)continue;
        if((known=strip_known(old,items[i].id))!=NULL){
            Q_strcpy_bounded(e->id,known->id,sizeof(e->id));Q_strcpy_bounded(e->name,known->name,sizeof(e->name));
        }else if(AW_InventoryRead(items[i].id,&item)){
            Q_strcpy_bounded(e->id,item.id,sizeof(e->id));Q_strcpy_bounded(e->name,item.name,sizeof(e->name));
        }else{Q_strcpy_bounded(e->id,items[i].id,sizeof(e->id));Q_strcpy_bounded(e->name,items[i].id,sizeof(e->name));}
        e->count=items[i].count;k++;
    }
    l->count[AW_CSTRIP_CONTAINER]=k;
    for(i=k=0;i<aw_state.count[AW_ITEM] && k<AW_CSTRIP_ROWS;i++){
        const aw_value_t *v=&aw_state.values[AW_ITEM][i];aw_cstrip_entry_t *e=&l->row[AW_CSTRIP_INVENTORY][k];
        if(v->value<=0)continue;
        if((known=strip_known(old,v->id))!=NULL){
            Q_strcpy_bounded(e->id,known->id,sizeof(e->id));Q_strcpy_bounded(e->name,known->name,sizeof(e->name));
        }else if(AW_InventoryRead(v->id,&item)){
            Q_strcpy_bounded(e->id,item.id,sizeof(e->id));Q_strcpy_bounded(e->name,item.name,sizeof(e->name));
        }else continue;
        e->count=v->value;k++;
    }
    l->count[AW_CSTRIP_INVENTORY]=k;
    AW_InventoryBatchEnd();
    if(old)free(old);
    AW_CStripClamp(l);
}
/* the hook E reaches (aw_inventory.c container_open): an unlocked container that opens */
static int strip_open(unsigned reference,const char *name,int owned){
    if(strip || key_dest!=key_game || !sv.active)return 0;
    if(!(strip=(strip_t *)AW_TryMalloc(sizeof(strip_t)))){AW_UISubtitle(name,"Not enough memory to open it.",3);return 1;}
    memset(strip,0,sizeof(*strip));
    strip->reference=reference;strip->owned=owned;Q_strcpy_bounded(strip->title,name,sizeof(strip->title));
    strip->list.columns=1;
    {   /* CONTAINER-STRIP-TAKE-STALL-59: the container's data read once here, not again on every take or put;
         * TRADEHOUSE-LONG-FRAME-59: an open of 100 ms or more says so */
        double t0=Sys_FloatTime(),t1;
        AW_ContainerHold(reference);
        t1=Sys_FloatTime();
        strip_fill();
        if(Sys_FloatTime()-t0>=.1)Con_Printf("Container strip: the open held the frame %d ms (contents and owner %d ms, names %d ms).\n",
            (int)((Sys_FloatTime()-t0)*1000),(int)((t1-t0)*1000),(int)((Sys_FloatTime()-t1)*1000));
        /* AREA-TABLES-59: every open measured with developer 1 (the pictures follow in the first drawn frame) */
        else Con_DPrintf("Container strip: open %d ms (contents and owner %d ms, names %d ms).\n",
            (int)((Sys_FloatTime()-t0)*1000),(int)((t1-t0)*1000),(int)((Sys_FloatTime()-t1)*1000));
        strip_pictures_pending=1;
    }
    strip_dirty=STRIP_DIRTY_FRAMES;
    IN_AWClearButtons();
    return 1;
}
static void layout(int *top,int *left,int *columns){
    int y=r_refdef.vrect.y+r_refdef.vrect.height;
    if(y>(int)vid.height-STRIP_H)y=(int)vid.height-STRIP_H;
    if(y<0)y=0;
    *top=y;*left=12;
    *columns=((int)vid.width-24)/STRIP_CELL;
    if(*columns>STRIP_COLUMNS)*columns=STRIP_COLUMNS;
    if(*columns<1)*columns=1;
}
/* HOW: 0 one, 1 the stack, 2 everything in the container */
static void strip_act(int how){
    aw_cstrip_list_t *l=&strip->list;const aw_cstrip_entry_t *e=AW_CStripSelected(l);const char *why="";
    char line[96];int moved=0,i;
    strip_dirty=STRIP_DIRTY_FRAMES;
    if(how==2){
        if(l->side!=AW_CSTRIP_CONTAINER)return;
        for(i=0;i<l->count[AW_CSTRIP_CONTAINER];i++){
            const aw_cstrip_entry_t *t=&l->row[AW_CSTRIP_CONTAINER][i];
            int n=AW_ContainerTake(strip->reference,t->id,t->count,strip->owned,&why);
            if(!n && !strcmp(why,"capacity"))break;
            moved+=n;
        }
        if(!strcmp(why,"capacity"))AW_UISubtitle(strip->title,"Cannot collect: inventory capacity.",3);
        if(moved){
            Q_snprintf(line,sizeof(line),"%s: %d taken%s",strip->title,moved,strip->owned?" (stolen)":"");
            AW_UIPickupNotice(line,3);
        }
        strip_fill();return;
    }
    if(!e)return;
    if(l->side==AW_CSTRIP_CONTAINER){
        moved=AW_ContainerTake(strip->reference,e->id,how?e->count:1,strip->owned,&why);
        if(moved){Q_snprintf(line,sizeof(line),"%s%s%s",e->name,moved>1?va(" x %d",moved):"",strip->owned?" (stolen)":"");AW_UIPickupNotice(line,3);}
        else if(!strcmp(why,"capacity"))AW_UISubtitle(strip->title,"Cannot collect: inventory capacity.",3);
    }else{
        moved=AW_ContainerPut(strip->reference,e->id,how?e->count:1,&why);
        if(!moved)AW_UISubtitle(strip->title,"Cannot put it here.",3);
    }
    strip_fill();
}
/* CONTAINER-STRIP-TAKE-STALL-59: a take or a put that holds the frame for long says so in the console (and the
 * remote console log), so a slow one is measured, never mistaken for a hang */
static void strip_act_timed(int how){
    double start=Sys_FloatTime(),took;
    strip_act(how);
    if((took=Sys_FloatTime()-start)>=.1)Con_Printf("Container strip: the %s held the frame %d ms.\n",
        strip && strip->list.side==AW_CSTRIP_INVENTORY?"put":"take",(int)(took*1000));
    else Con_DPrintf("Container strip: %s %d ms.\n",strip && strip->list.side==AW_CSTRIP_INVENTORY?"put":"take",(int)(took*1000));
    strip_pictures_pending=1;
}
int AW_CStripMouse(int dx,int dy){
    if(!strip)return 0;
    if(dx || dy)strip_dirty=STRIP_DIRTY_FRAMES;
    mouse_x+=dx;mouse_y+=dy;
    if(mouse_x<0)mouse_x=0;
    if(mouse_x>(int)vid.width-1)mouse_x=(int)vid.width-1;
    if(mouse_y<0)mouse_y=0;
    if(mouse_y>(int)vid.height-1)mouse_y=(int)vid.height-1;
    return 1;
}
/* the title row's targets: the two side names, Take All, Close */
static int click(void){
    int top,left,columns,i,right=(int)vid.width-6;aw_cstrip_list_t *l=&strip->list;
    layout(&top,&left,&columns);
    if(mouse_y>=top+2 && mouse_y<top+2+STRIP_TITLE){
        if(mouse_x>=right-STRIP_BUTTON_W)return K_ESCAPE;
        if(mouse_x>=right-2*STRIP_BUTTON_W-4)return 't';
        return mouse_x<left+120?'1':'2';
    }
    i=AW_CStripCell(l,mouse_x,mouse_y,left,top+STRIP_TITLE+4,STRIP_CELL,STRIP_CELL);
    if(i<0)return 0;
    if(i==l->selected[l->side])return 'e';
    l->selected[l->side]=i;AW_CStripClamp(l);
    return 0;
}
int AW_CStripKey(int key){
    aw_cstrip_list_t *l;
    if(!strip)return 0;
    if(key_dest!=key_game || !sv.active){strip_close();return 0;}
    l=&strip->list;
    strip_dirty=STRIP_DIRTY_FRAMES;
    if(key==K_MOUSE1 && !(key=click()))return 1;
    switch(key){
    case K_ESCAPE:strip_close();return 1;
    case K_LEFTARROW:case 'a':case 'A':AW_CStripMove(l,-1);return 1;
    case K_RIGHTARROW:case 'd':case 'D':AW_CStripMove(l,1);return 1;
    case K_PGUP:AW_CStripMove(l,-l->columns);return 1;
    case K_PGDN:AW_CStripMove(l,l->columns);return 1;
    case K_TAB:case K_UPARROW:case K_DOWNARROW:case 'w':case 'W':case 's':case 'S':AW_CStripSide(l,-1);return 1;
    case '1':AW_CStripSide(l,AW_CSTRIP_CONTAINER);return 1;
    case '2':AW_CStripSide(l,AW_CSTRIP_INVENTORY);return 1;
    case 'e':case 'E':case K_ENTER:strip_act_timed(0);return 1;
    case 'q':case 'Q':strip_act_timed(1);return 1;
    case 't':case 'T':strip_act_timed(2);return 1;
    }
    return 1;   /* every other key waits while the strip is open */
}
void AW_CStripDraw(void){
    static int white=-1,red,grey,dark,gold;
    int top,left,columns,c,y,right=(int)vid.width-6;aw_cstrip_list_t *l;const aw_cstrip_entry_t *e;char line[96];
    if(!strip)return;
    if(!sv.active || cls.state!=ca_connected || key_dest!=key_game){strip_close();return;}
    if(white<0){white=AW_UIColor(255,255,255);red=AW_UIColor(220,40,40);grey=AW_UIColor(150,140,120);
                dark=AW_UIColor(24,20,16);gold=AW_UIColor(223,199,144);}
    l=&strip->list;
    layout(&top,&left,&columns);
    if(l->columns!=columns){l->columns=columns;AW_CStripClamp(l);}
    AW_UIBox(0,top,(int)vid.width,(int)vid.height-top);
    AW_UISmallBegin();
    /* the title row: the container (red when owned: taking is theft), the inventory side, Take All, Close */
    AW_UIText(left,top+4,strip->title,l->side==AW_CSTRIP_CONTAINER?(strip->owned?red:gold):grey);
    AW_UIText(left+124,top+4,"Inventory",l->side==AW_CSTRIP_INVENTORY?gold:grey);
    AW_UIBox(right-2*STRIP_BUTTON_W-4,top+2,STRIP_BUTTON_W,STRIP_TITLE);
    AW_UITextBox(right-2*STRIP_BUTTON_W-4,top+2,STRIP_BUTTON_W,STRIP_TITLE,"Take All",strip->owned?red:white);
    AW_UIBox(right-STRIP_BUTTON_W,top+2,STRIP_BUTTON_W,STRIP_TITLE);
    AW_UITextBox(right-STRIP_BUTTON_W,top+2,STRIP_BUTTON_W,STRIP_TITLE,"Close",white);
    /* the cells: picture, count, the selected one framed */
    y=top+STRIP_TITLE+4;
    {double t0=Sys_FloatTime();int loaded=0;
     for(c=0;c<columns;c++){
        int i=l->first[l->side]+c;char key[48];
        if(i>=l->count[l->side])break;
        Q_snprintf(key,sizeof(key),"item:%s",l->row[l->side][i].id);
        if(strcmp(strip->icon[c].key,key))loaded++;
        AW_IconLoad(&strip->icon[c],key);
     }
     /* the pictures' share of an open or a change (aw_magic stats: how many came from the area tables) */
     if(strip_pictures_pending && loaded)
        Con_DPrintf("Container strip: %d pictures in %d ms.\n",loaded,(int)((Sys_FloatTime()-t0)*1000));
     strip_pictures_pending=0;}
    if(l->first[l->side]>0)AW_UIText(2,y+12,"<",white);
    if(l->first[l->side]+columns<l->count[l->side])AW_UIText((int)vid.width-9,y+12,">",white);
    for(c=0;c<columns;c++){
        int i=l->first[l->side]+c,x=left+c*STRIP_CELL;char key[48];
        AW_UIFill(x,y,STRIP_CELL-2,STRIP_CELL-2,dark);
        if(i>=l->count[l->side])continue;
        e=&l->row[l->side][i];
        if(i==l->selected[l->side]){AW_UIFill(x-1,y-1,STRIP_CELL,1,gold);AW_UIFill(x-1,y+STRIP_CELL-2,STRIP_CELL,1,gold);
                                    AW_UIFill(x-1,y-1,1,STRIP_CELL,gold);AW_UIFill(x+STRIP_CELL-2,y-1,1,STRIP_CELL,gold);}
        Q_snprintf(key,sizeof(key),"item:%s",e->id);
        if(AW_IconLoad(&strip->icon[c],key))AW_IconDraw(&strip->icon[c],x+1,y+1);
        else{Q_strcpy_bounded(line,e->name,5);AW_UIText(x+2,y+4,line,grey);}
        if(e->count>1){Q_snprintf(line,sizeof(line),"%d",e->count);AW_UIText(x+STRIP_CELL-3-AW_UIWidth(line),y+STRIP_CELL-12,line,white);}
    }
    /* the selected entry and the keys */
    y+=STRIP_CELL+2;
    if((e=AW_CStripSelected(l))!=NULL){
        Q_snprintf(line,sizeof(line),"%s%s",e->name,e->count>1?va(" (%d)",e->count):"");
        AW_UIText(left,y,line,l->side==AW_CSTRIP_CONTAINER && strip->owned?red:white);
    }else AW_UIText(left,y,l->side==AW_CSTRIP_CONTAINER?"Empty.":"You carry nothing to put in.",grey);
    AW_UIText(left,y+11,l->side==AW_CSTRIP_CONTAINER?(strip->owned?"E: Steal  Q: stack  Tab: put":"E: Take  Q: stack  Tab: put"):
                                                     "E: Put  Q: stack  Tab: back",grey);
    AW_UISmallEnd();
    if(!AW_UICursor(mouse_x,mouse_y)){AW_UIFill(mouse_x,mouse_y,2,6,white);AW_UIFill(mouse_x,mouse_y,6,2,white);}
    if(strip_dirty>0){scr_copyeverything=1;strip_dirty--;}
}
/* CONTAINER-STRIP-REDRAW-COST-59: frames left that copy the whole screen (the native test reads it) */
int AW_CStripDirty(void){return strip_dirty;}
