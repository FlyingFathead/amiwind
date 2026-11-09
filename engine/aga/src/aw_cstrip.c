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
/* LOOT-WINDOW-LAYOUT-60: the rows and their room (aw_cstrip_rules.c AW_CStripLayout, native-tested) */
#define STRIP_CELL AW_CSTRIP_CELL
#define STRIP_COLUMNS AW_CSTRIP_COLUMNS
#define STRIP_TITLE AW_CSTRIP_TITLE
#define STRIP_BUTTON_W AW_CSTRIP_BUTTON_W
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
const aw_cstrip_list_t *AW_CStripList(void){return strip?&strip->list:NULL;}
static int strip_open(unsigned reference,const char *name,int owned);
/* aw_placed.c AW_PlacedInit: E on containers opens the strip; the input, drawing and prompt reach it (hooks only, no
 * command, no variable, nothing allocated) */
void AW_CStripInit(void){
    aw_container_open=strip_open;aw_container_lock=AW_ObjectLockLevel;
    aw_cstrip_mouse=AW_CStripMouse;aw_cstrip_key=AW_CStripKey;aw_cstrip_draw=AW_CStripDraw;aw_cstrip_open_now=AW_CStripActive;
}
static void strip_close(void){
    if(strip){free(strip->list.row[0]);free(strip->list.row[1]);free(strip);strip=NULL;}
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
/* CONTAINER-STRIP-OPEN-MANY-KINDS-61: the inventory side, every carried kind in the item table's order. Names come
 * from the old list first: both lists are in that order, so a cursor finds them in one walk (a full search only when
 * the cursor misses: 415 kinds x 415 string compares per take otherwise). The kinds still unnamed are read the way the
 * inventory window reads them (aw_inventory.c AW_InventoryCarried): above STRIP_SEARCHES of them one pass over
 * items.awi in file order, else one search each. One binary search per kind held the open of a body 10.3 s with 415
 * kinds on FS-UAE (about 25 ms each). A kind the catalogue has no row for is left out, as before. */
#define STRIP_SEARCHES 8
typedef struct {aw_cstrip_entry_t *row;const int *at;unsigned char *named;int named_now;} strip_pass_t;
static void strip_pass_row(void *ctx,int state_row,const aw_inventory_item_t *it,int file_row){
    strip_pass_t *p=(strip_pass_t *)ctx;int k=p->at[state_row];aw_cstrip_entry_t *e;(void)file_row;
    if(k<0 || p->named[k] || !it)return;
    e=&p->row[k];
    Q_strcpy_bounded(e->id,it->id,sizeof(e->id));Q_strcpy_bounded(e->name,it->name,sizeof(e->name));
    p->named[k]=1;p->named_now++;
}
static void strip_fill_inventory(aw_cstrip_list_t *l,const aw_cstrip_list_t *old,int kinds){
    aw_cstrip_entry_t *row=l->row[AW_CSTRIP_INVENTORY];const aw_cstrip_entry_t *known;aw_inventory_item_t item;
    int *at=NULL;unsigned char *named=NULL;int i,k,n=0,missing=0,cursor=0,oldn=old?old->count[AW_CSTRIP_INVENTORY]:0;
    l->count[AW_CSTRIP_INVENTORY]=0;
    if(kinds<1)return;
    at=(int *)AW_TryMalloc(sizeof(int)*kinds);named=(unsigned char *)AW_TryCalloc((unsigned long)kinds,1);
    if(!at || !named){free(at);free(named);return;}
    for(i=0;i<kinds;i++){
        aw_cstrip_entry_t *e;const char *id;
        at[i]=-1;
        if(AW_ITEM_ROW(&aw_state,i)->value<=0)continue;
        id=AW_ITEM_ID(&aw_state,i);e=&row[n];
        e->count=AW_ITEM_ROW(&aw_state,i)->value;
        Q_strcpy_bounded(e->id,id,sizeof(e->id));e->name[0]=0;
        known=NULL;
        if(cursor<oldn && !Q_strcasecmp((char *)old->row[AW_CSTRIP_INVENTORY][cursor].id,(char *)id))
            known=&old->row[AW_CSTRIP_INVENTORY][cursor++];
        else if(oldn || (old && old->count[AW_CSTRIP_CONTAINER])){
            known=strip_known(old,id);
            /* found further on the old inventory side (a kind before it is gone): the cursor follows it */
            if(known && known>=old->row[AW_CSTRIP_INVENTORY] && known<old->row[AW_CSTRIP_INVENTORY]+oldn)
                cursor=(int)(known-old->row[AW_CSTRIP_INVENTORY])+1;
        }
        if(known){Q_strcpy_bounded(e->id,known->id,sizeof(e->id));Q_strcpy_bounded(e->name,known->name,sizeof(e->name));named[n]=1;}
        else missing++;
        at[i]=n++;
    }
    if(missing>STRIP_SEARCHES){
        strip_pass_t p;p.row=row;p.at=at;p.named=named;p.named_now=0;
        AW_InventoryCarried(strip_pass_row,&p);   /* every carried kind; the named ones are skipped */
    }else if(missing){
        for(i=0;i<kinds;i++){
            if(at[i]<0 || named[at[i]])continue;
            if(AW_InventoryRead(row[at[i]].id,&item)){
                Q_strcpy_bounded(row[at[i]].id,item.id,sizeof(row[at[i]].id));
                Q_strcpy_bounded(row[at[i]].name,item.name,sizeof(row[at[i]].name));named[at[i]]=1;
            }
        }
    }
    for(i=k=0;i<n;i++)if(named[i]){if(k!=i)row[k]=row[i];k++;}   /* the kinds without a catalogue row left out */
    l->count[AW_CSTRIP_INVENTORY]=k;
    free(at);free(named);
}
/* the two sides from the container's contents now (data + deltas) and the player's items; names already known are
 * kept, so a take or a put reads only the contents again, never every item's catalogue row */
static void strip_fill(void){
    aw_container_item_t items[AW_CONTAINER_ITEMS];aw_inventory_item_t item;aw_cstrip_list_t *l=&strip->list,oldl,*old=&oldl;
    const aw_cstrip_entry_t *known;int n,i,k,kinds=AW_ItemCount(&aw_state);aw_cstrip_entry_t *side[2];
    /* new arrays for both sides (the inventory side as long as the kinds carried); the old ones lend their names */
    side[0]=(aw_cstrip_entry_t *)AW_TryMalloc(sizeof(aw_cstrip_entry_t)*AW_CSTRIP_ROWS);
    side[1]=(aw_cstrip_entry_t *)AW_TryMalloc(sizeof(aw_cstrip_entry_t)*(kinds>0?kinds:1));
    if(!side[0] || !side[1]){free(side[0]);free(side[1]);return;}   /* the lists stay as they were */
    oldl=*l;l->row[0]=side[0];l->row[1]=side[1];l->cap[0]=AW_CSTRIP_ROWS;l->cap[1]=kinds;
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
    strip_fill_inventory(l,old,kinds);
    AW_InventoryBatchEnd();
    free(oldl.row[0]);free(oldl.row[1]);
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
static void layout(aw_cstrip_layout_t *o){
    AW_CStripLayout((int)vid.width,(int)vid.height,r_refdef.vrect.y+r_refdef.vrect.height,AW_ConsoleCharWidth(),
                    AW_ConsoleCharHeight(),o);
}
/* LOOT-WINDOW-LAYOUT-60: a line in the console font (the key help, the name and the properties), clipped at RIGHT;
 * RED (a palette index) for an owned container's entries, -1 the console's own colour */
static void ctext(int x,int y,const char *s,int right,int red){
    int w=AW_ConsoleCharWidth();
    if(w<1)w=8;
    for(;s && *s && x+w<=right;s++,x+=w){
        if(red>=0)AW_ConsoleCharacterRed(x,y,(unsigned char)*s,red);
        else AW_ConsoleCharacter(x,y,(unsigned char)*s);
    }
}
/* HOW: 0 one, 1 the stack, 2 everything in the container */
static void strip_act(int how){
    aw_cstrip_list_t *l=&strip->list;const aw_cstrip_entry_t *e=AW_CStripSelected(l);const char *why="";
    char line[96];int moved=0,i,refused=-1;
    strip_dirty=STRIP_DIRTY_FRAMES;
    if(how==2){
        if(l->side!=AW_CSTRIP_CONTAINER)return;
        for(i=0;i<l->count[AW_CSTRIP_CONTAINER];i++){
            const aw_cstrip_entry_t *t=&l->row[AW_CSTRIP_CONTAINER][i];
            int n=AW_ContainerTake(strip->reference,t->id,t->count,strip->owned,&why);
            if(!n && !strcmp(why,"capacity")){refused=i;break;}
            moved+=n;
        }
        if(refused>=0)AW_InventoryRefused(strip->title,l->row[AW_CSTRIP_CONTAINER][refused].id,
                                          l->row[AW_CSTRIP_CONTAINER][refused].count);
        if(moved && AW_SceneNameLabelsAmiWind()){   /* the AmiWind style says it; the Morrowind style shows no text */
            AW_CStripTakeLine(line,sizeof(line),NULL,0,strip->owned,strip->title,moved);
            AW_UIPickupNotice(line,3);
        }
        strip_fill();return;
    }
    if(!e)return;
    if(l->side==AW_CSTRIP_CONTAINER){
        moved=AW_ContainerTake(strip->reference,e->id,how?e->count:1,strip->owned,&why);
        if(moved && AW_SceneNameLabelsAmiWind()){AW_CStripTakeLine(line,sizeof(line),e->name,moved,strip->owned,NULL,0);AW_UIPickupNotice(line,3);}
        else if(!strcmp(why,"capacity"))AW_InventoryRefused(strip->title,e->id,how?e->count:1);
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
    int i,right=(int)vid.width-AW_CSTRIP_FRAME-4;aw_cstrip_list_t *l=&strip->list;aw_cstrip_layout_t o;
    layout(&o);
    if(mouse_y>=o.title_y && mouse_y<o.title_y+STRIP_TITLE){
        if(mouse_x>=right-STRIP_BUTTON_W)return K_ESCAPE;
        if(mouse_x>=right-2*STRIP_BUTTON_W-4)return 't';
        return mouse_x<o.left+120?'1':'2';
    }
    i=AW_CStripCell(l,mouse_x,mouse_y,o.left,o.cells_y,STRIP_CELL,STRIP_CELL);
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
    static int white=-1,red,grey,gold;
    int left,columns,c,y,right=(int)vid.width-AW_CSTRIP_FRAME-4;aw_cstrip_list_t *l;const aw_cstrip_entry_t *e;char line[96];
    aw_cstrip_layout_t o;
    if(!strip)return;
    if(!sv.active || cls.state!=ca_connected || key_dest!=key_game){strip_close();return;}
    if(white<0){white=AW_UIColor(255,255,255);red=AW_UIColor(220,40,40);grey=AW_UIColor(150,140,120);
                gold=AW_UIColor(223,199,144);}
    l=&strip->list;
    layout(&o);left=o.left;columns=o.columns;
    if(l->columns!=columns){l->columns=columns;AW_CStripClamp(l);}
    AW_UIBox(0,o.top,(int)vid.width,o.bottom-o.top);
    AW_UISmallBegin();
    /* the title row: the container (red when owned: taking is theft), the inventory side, Take All, Close; the
     * buttons with room above and below (LOOT-WINDOW-LAYOUT-60) */
    AW_UITextBox(left,o.title_y,AW_UIWidth(strip->title),STRIP_TITLE,strip->title,
                 l->side==AW_CSTRIP_CONTAINER?(strip->owned?red:gold):grey);
    AW_UITextBox(left+124,o.title_y,AW_UIWidth("Inventory"),STRIP_TITLE,"Inventory",l->side==AW_CSTRIP_INVENTORY?gold:grey);
    /* the house button style: a 1 pixel line, the text centred in the whole 56 x 14 (UI-THIN-BUTTON-62) */
    AW_UIButton(right-2*STRIP_BUTTON_W-4,o.title_y,STRIP_BUTTON_W,STRIP_TITLE,"Take All",0,strip->owned?red:white);
    AW_UIButton(right-STRIP_BUTTON_W,o.title_y,STRIP_BUTTON_W,STRIP_TITLE,"Close",0,white);
    AW_UISmallEnd();
    /* the cells: picture, count, the selected one framed */
    y=o.cells_y;
    {double t0=Sys_FloatTime();int loaded=0;
     for(c=0;c<columns;c++){
        int i=l->first[l->side]+c;char key[64];
        if(i>=l->count[l->side])break;
        /* ITEM-ICONS-MISSING-62: the item's own picture, the one the inventory window shows ("big:" then "inv:") */
        Q_snprintf(key,sizeof(key),"item*%s",l->row[l->side][i].id);
        if(strcmp(strip->icon[c].key,key))loaded++;
        AW_IconLoadItem(&strip->icon[c],l->row[l->side][i].id);
     }
     /* the pictures' share of an open or a change (aw_magic stats: how many came from the area tables) */
     if(strip_pictures_pending && loaded)
        Con_DPrintf("Container strip: %d pictures in %d ms.\n",loaded,(int)((Sys_FloatTime()-t0)*1000));
     strip_pictures_pending=0;}
    if(l->first[l->side]>0)ctext(left-o.char_w-2,y+(STRIP_CELL-o.char_h)/2,"<",left,-1);
    if(l->first[l->side]+columns<l->count[l->side])
        ctext(left+columns*STRIP_CELL,y+(STRIP_CELL-o.char_h)/2,">",(int)vid.width-AW_CSTRIP_FRAME,-1);
    for(c=0;c<columns;c++){
        int i=l->first[l->side]+c,x=left+c*STRIP_CELL;
        AW_UIFill(x,y,STRIP_CELL-2,STRIP_CELL-2,AW_UIColor(0,0,0));   /* the item slots are black (ITEM-ICONS-MISSING-62) */
        if(i>=l->count[l->side])continue;
        e=&l->row[l->side][i];
        if(i==l->selected[l->side]){AW_UIFill(x-1,y-1,STRIP_CELL,1,gold);AW_UIFill(x-1,y+STRIP_CELL-2,STRIP_CELL,1,gold);
                                    AW_UIFill(x-1,y-1,1,STRIP_CELL,gold);AW_UIFill(x+STRIP_CELL-2,y-1,1,STRIP_CELL,gold);}
        /* the picture fills its cell, centred with an even margin (the shared slot fit, aw_icons.c AW_IconDrawFit,
         * ITEM-ICONS-MISSING-62); only an item that truly has no picture shows its name in the console font, wrapped
         * over the cell's lines (never cut to a few letters) */
        if(AW_IconLoadItem(&strip->icon[c],e->id)){
            AW_IconDrawFit(&strip->icon[c],x,y,STRIP_CELL-2,STRIP_CELL-2,AW_UIColor(0,0,0));
        }else{
            int cols=(STRIP_CELL-4)/o.char_w,rows=(STRIP_CELL-4)/o.char_h,r;const char *p=e->name;
            for(r=0;r<rows && p && *p;r++){
                int n,cut;
                while(*p==' ')p++;
                n=(int)strlen(p);cut=n>cols?cols:n;
                if(n>cols){int b=cut;while(b>0 && p[b]!=' ')b--;if(b>0)cut=b;}
                Q_strcpy_bounded(line,p,cut+1<(int)sizeof(line)?cut+1:(int)sizeof(line));
                ctext(x+2,y+2+r*o.char_h,line,x+STRIP_CELL-2,-1);
                p+=cut;
            }
        }
        if(e->count>1){Q_snprintf(line,sizeof(line),"%d",e->count);AW_UISmallBegin();
                       AW_UIText(x+STRIP_CELL-3-AW_UIWidth(line),y+STRIP_CELL-12,line,white);AW_UISmallEnd();}
    }
    /* the selected entry, its properties (LOOT-WINDOW-ITEM-PROPERTIES-60: as the original's item tooltip) and the keys,
     * in the console font */
    if((e=AW_CStripSelected(l))!=NULL){
        Q_snprintf(line,sizeof(line),"%s%s",e->name,e->count>1?va(" (%d)",e->count):"");
        ctext(left,o.name_y,line,right,l->side==AW_CSTRIP_CONTAINER && strip->owned?red:-1);
        if(AW_InventoryPropertiesLine(e->id,o.text_columns,line,sizeof(line)))ctext(left,o.props_y,line,right,-1);
    }else ctext(left,o.name_y,l->side==AW_CSTRIP_CONTAINER?"Empty.":"You carry nothing to put in.",right,-1);
    ctext(left,o.keys_y,l->side==AW_CSTRIP_CONTAINER?(strip->owned?"E: Steal  Q: stack  T: all  Tab: put":
                                                     "E: Take  Q: stack  T: all  Tab: put"):"E: Put  Q: stack  Tab: back",right,-1);
    if(!AW_UICursor(mouse_x,mouse_y)){AW_UIFill(mouse_x,mouse_y,2,6,white);AW_UIFill(mouse_x,mouse_y,6,2,white);}
    if(strip_dirty>0){scr_copyeverything=1;strip_dirty--;}
}
/* CONTAINER-STRIP-REDRAW-COST-59: frames left that copy the whole screen (the native test reads it) */
int AW_CStripDirty(void){return strip_dirty;}
