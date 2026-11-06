/* SPDX-License-Identifier: GPL-2.0-or-later
 * On-demand island map and dated, earned journal entries. Closed panels retain
 * no map pixels/text cache. The single-player menu pause captures all input.
 */
#include "quakedef.h"
#include "aw_state.h"
#include "aw_story.h"
#include "aw_character.h"
#include "aw_inventory.h"
#include "aw_combat.h"
#include "aw_maps.h"
#include "aw_world.h"
#include "aw_statswin.h"
#include "aw_tryalloc.h"
#include "aw_textdef.h"
#include "aw_questbook.h"
#include "aw_jhist.h"
#include "aw_save.h"
#include <stdint.h>
/* AWM1: header, areas, pixels. AWM2 adds the LAVA section (docs/WORLD_MAP_AND_JOURNAL.md "Map file formats"). */
#define LAVA_POOLS_MAX 2048
#define LAVA_POINTS 16
#define MAP_MAX (512*512+32+8*60+16+LAVA_POOLS_MAX*(24+LAVA_POINTS*8))
#define BOOK_PAGES 256
#define BOOK_LINES 9
#define BOOK_WIDTH 132
static int modal,mouse_x=160,mouse_y=100,drag,grid,zoom;
static int marker_click;
static float marker_drag_x,marker_drag_y;
static const char *marker_message;
/* Existing global codec persists these three bounded facts without a schema change. */
static const char *const marker_keys[3]={"amiwind:map:marker:x","amiwind:map:marker:y","amiwind:map:marker:ready"};
#define TELEPORT_X 244
#define TELEPORT_W 72
#define TELEPORT_H 15
#define CLEAR_X 244
#define CLEAR_Y 174
#define CLEAR_W 72
#define CLEAR_H 10
#define INV_VISIBLE 6
#define INV_LIST_Y 54
#define INV_ROW_H 16
#define INV_SCROLL_X 304
#define INV_SCROLL_H (INV_VISIBLE*INV_ROW_H)
#define INV_DETAILS_Y 152
#define INV_STATUS_Y 160
#define INV_CONTROLS_Y 176
#define INV_CLOSE_X 132
#define INV_CLOSE_W 44
#define INV_PREVIEW_X 7
/* the picture starts under the burden bar (ENCUMBRANCE-INCOMPLETE-61: OpenMW openmw_inventory_window.layout puts the
 * EncumbranceBar above the Avatar) */
#define INV_PREVIEW_Y 32
#define INV_PREVIEW_W 116
#define INV_PREVIEW_H 158
#define INV_BURDEN_Y 21
#define INV_BURDEN_H 9
/* INVENTORY-ORIGINAL-LIMITS-61: the window lists every kind carried (no fixed limit) and keeps little per kind: a
 * 40-byte sort key for each (its item row, value, weight, category and the first 23 letters of its name, read when the
 * window opens or the list changes); the whole record (about 520 bytes) only for the rows in view and one page either
 * side (INV_PAGE), read again when the view leaves them. */
#define INV_PAGE (3*INV_VISIBLE)
typedef struct {int state_row,value,file_row;float weight;unsigned char category,known;char name[24];} inv_key_t;
typedef struct {
    inv_key_t *keys;int nkeys;                 /* every kind carried (heap) */
    int *rows;                                 /* list row -> key (the category's, sorted; heap) */
    aw_inventory_item_t page[INV_PAGE];unsigned char page_known[INV_PAGE];int page_first;   /* -1: none read */
    aw_inventory_item_t one;int one_row;       /* a row outside the page (the selection out of view) */
    int count,selected,top,category,sort,context,context_x,context_y;
    int icon_row[INV_VISIBLE],icon_ok[INV_VISIBLE];
    byte icons[INV_VISIBLE][1024];
    char message[96];float angle;
    /* The still character picture (UI-INVENTORY-PREVIEW-STILL-42): rendered once when the
     * window opens and after each equipment change, then only copied. 0 = render next frame,
     * 1 = picture ready, -1 = unavailable. */
    int preview_state,preview_renders;
    unsigned preview_frames;double preview_seconds,preview_render_seconds;
    byte preview[INV_PREVIEW_W*INV_PREVIEW_H];
} inventory_panel_t;
static inventory_panel_t *inventory;
int AW_InventoryActive(void){return modal==3;}
static const char *const inventory_categories[]={"All","Weapons","Armour","Clothing","Potions","Ingredients","Books","Misc"};
static void inventory_refresh(void);
static void inventory_filter(void);
static void inventory_key(int key);
static void inventory_draw(void);
static byte *map_data,*map_pixels;
static int map_w,map_h,map_bounds[4],area_count,marker,map_ocean;
static float map_x,map_y,player_x,player_y,player_z,map_step;
static int map_view_ready,teleport_mode,teleport_selected;
static cvar_t aw_map_mode={"aw_map_mode","0",true}; /* 0=Debug, 1=In-Game */
static cvar_t aw_map_debug_available={"aw_map_debug_available","1",true};
/* v2 map layers: lava pools on by default; aw_map_format 1 draws a v2 file as v1. */
static cvar_t aw_map_lava={"aw_map_lava","1",true};
static cvar_t aw_map_format={"aw_map_format","2",true};
static const byte *lava_pools,*lava_points;
static int lava_count,lava_colour,lava_painted;
static float teleport_point[3];
static const char *teleport_message;
static char teleport_region[64];
#define BOOK_TOPICS 256       /* the topics the reader lists (sorted by name) */
#define BOOK_LINKS 512        /* the links one topic page holds (its text is 16 KB; the spans are a few per entry) */
#define BOOK_HITS 96          /* the link pieces drawn on one spread */
static char opened_scene[64];
static struct {char id[16],title[32];float x,y,scale;} areas[8];
/* The quest pages (JOURNAL-BOOK-32-QUESTS-59, aw_questbook.h): every started quest, from the stages kept on the world
 * change list, built when the book opens and freed when it closes (the catalogue rows of the started quests only).
 * filter: a name's row in qb (-1 all entries); entry: a row of qb.entry; selection and index_*: rows of shown. */
typedef struct {
    char raw[8192],text[16384];unsigned short pages[BOOK_PAGES];
    int count,spread,entry,filter,index_mode,index_top,selection,title_rows,index_end;
    aw_questbook_t qb;aw_qb_quest_t *quests;int nquests;
    int *shown,nshown,all;              /* the names listed (rows of qb.group); all: "Show all" (finished ones too) */
    int *index_x,*index_y,*index_rows;  /* per row of shown */
    /* the topic pages (OpenMW's journal Topics): the topics heard, by name; the one being read */
    int topics,topic_top,topic_sel,topic_open;short topic_id[BOOK_TOPICS];char topic_name[BOOK_TOPICS][40];
    /* the page's links (OpenMW JournalWindow): the topic of the n-th link mark in text, and where the drawn ones are */
    int links,hits;unsigned short link_topic[BOOK_LINKS];
    struct {short x,y,w;short link;} hit[BOOK_HITS];
    /* the dated journal (JOURNAL-ORIGINAL-VIEW-59): the first view, every entry under its day; shown while entry is
     * BOOK_DATED, spread = its left page */
    aw_journalview_t jv;
} book_t;
#define BOOK_DATED (-3)
#define BOOK_DATED_LINES 11   /* rows of a dated page, from y 12 to the button row */
static book_t *book;
extern int scr_copyeverything;

static uint32_t u32(const byte *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static float f32(const byte *p){uint32_t n=u32(p);float value;memcpy(&value,&n,4);return value;}
static int minmax(int v,int lo,int hi){return v<lo?lo:v>hi?hi:v;}
static void text(int x,int y,const char *s,int right){
    int w=AW_ConsoleCharWidth();
    for(;*s && x+w<=right;s++,x+=w)AW_ConsoleCharacter(x,y,(unsigned char)*s);
}
static void cursor(void){
    int x=minmax(mouse_x,0,312),y=minmax(mouse_y,0,192),c,dark;
    if(AW_UICursor(x,y))return;   /* Morrowind's own pointer (CURSOR-MW-58); else AmiWind's below */
    c=AW_UIColor(255,245,190);dark=AW_UIColor(0,0,0);
    AW_UIFill(x,y,3,8,dark);AW_UIFill(x,y,8,3,dark);
    AW_UIFill(x+1,y+1,1,6,c);AW_UIFill(x+1,y+1,6,1,c);
}
/* Modal 4: a window drawn by another file (aw_statswin.c: Stats on P, the Magic placeholder on O)
 * with the inventory's input handling: the pause, Escape, F10/console, closing on a scene change. */
static void (*panel_draw)(void);
static int (*panel_key)(int key,int mouse_x,int mouse_y);
static void (*panel_closed)(void);
static void book_free(void){
    if(book){AW_QuestBookFree(&book->qb);AW_JournalViewFree(&book->jv);free(book->quests);free(book->shown);free(book->index_x);free(book->index_y);free(book->index_rows);}
    free(book);book=NULL;
}
int aw_worldui_panel_holds_escape;   /* set by the panel's opener after AW_WorldUIOpenPanel; cleared on every close */
static void close_panel(void){
    aw_worldui_panel_holds_escape=0;
    if(modal==4 && panel_closed)panel_closed();
    panel_draw=NULL;panel_key=NULL;panel_closed=NULL;
    if(inventory && inventory->preview_frames)
        Con_Printf("Inventory preview (%s): %d renders, last %d ms; %u frames, %d us per frame; picture %d bytes kept, pose model freed after each render.\n",
            AW_ViewInventoryLive()?"live":"still",inventory->preview_renders,(int)(inventory->preview_render_seconds*1000),
            inventory->preview_frames,(int)(inventory->preview_seconds*1e6/inventory->preview_frames),INV_PREVIEW_W*INV_PREVIEW_H);
    if(inventory){free(inventory->keys);free(inventory->rows);}
    free(inventory);inventory=NULL;AW_InventoryPreviewClear();
    free(map_data);map_data=map_pixels=NULL;lava_pools=lava_points=NULL;lava_count=0;
    book_free();
    if(modal && key_dest==key_menu)key_dest=key_game;
    modal=drag=marker_click=teleport_mode=teleport_selected=0;teleport_message=marker_message=NULL;IN_AWClearButtons();
}
int AW_WorldUIActive(void){return modal!=0;}
/* The open window for the remote state file (LOAD-STALL-SESSIONS-59): a panel of another file
 * (stats, the container strip, ...) is a generic "window". */
const char *AW_WorldUIName(void){
    static const char *const names[]={"","map","journal","inventory","window"};
    return modal>=0 && modal<=4?names[modal]:"window";
}/* A button released outside the window must not leave a modal drag held. */
void AW_WorldUICancelDrag(void){drag=marker_click=0;}
static int allowed_in_play(void){
    return !modal && key_dest==key_game && sv.active && svs.maxclients==1 && svs.clients &&
        svs.clients[0].edict && cls.state==ca_connected &&
        !AW_ReaderActive() && !AW_CharacterActive() && !AW_GalleryActive();
}
static int allowed(void){return allowed_in_play() && !AW_StoryRestricted();}
static void opened(int kind){
    strncpy(opened_scene,sv.name,sizeof(opened_scene)-1);opened_scene[sizeof(opened_scene)-1]=0;
    modal=kind;key_dest=key_menu;IN_AWClearButtons();
}
int AW_WorldUIOpenPanel(void (*draw)(void),int (*key)(int key,int mouse_x,int mouse_y),void (*closed)(void)){
    if(!draw || !key || !allowed())return 0;
    panel_draw=draw;panel_key=key;panel_closed=closed;opened(4);return 1;
}
void AW_InventoryOpen(void){
    int i;
    /* the inventory opens during the registration from the papers on, as in the original (aw_story.c
     * AW_StoryInventoryAllowed, CHARGEN-INVENTORY-LOCKED-60); the map and journal keep the released-game rule */
    if(!allowed_in_play() || !AW_StoryInventoryAllowed() || svs.clients[0].edict->v.health<=0)return;
    inventory=(inventory_panel_t *)AW_TryCalloc(1,sizeof(*inventory));
    if(!inventory){Con_Printf("Inventory: not enough memory.\n");return;}
    for(i=0;i<INV_VISIBLE;i++)inventory->icon_row[i]=-1;
    inventory->angle=(float)M_PI;opened(3);
    if(!AW_InventoryBootstrap())strcpy(inventory->message,"Initial item catalogue unavailable.");
    inventory_refresh();
}
/* a kind's record, or its id as the name (category Misc) when the catalogue has no row for it */
static int inventory_read(int state_row,aw_inventory_item_t *out){
    char id[64];
    strcpy(id,AW_ITEM_ID(&aw_state,state_row));memset(out,0,sizeof(*out));
    if(AW_InventoryRead(id,out))return 1;
    memset(out,0,sizeof(*out));strcpy(out->id,id);Q_strcpy_bounded(out->name,id,sizeof(out->name));
    out->category=AW_INV_MISC;return 0;
}
/* a key's record: by its row in the item file when the pass gave one (one read, no search), else by its id */
static int inventory_read_key(const inv_key_t *k,aw_inventory_item_t *out){
    if(k->file_row>=0 && aw_inventory_read_row && aw_inventory_read_row(k->file_row,out))return 1;
    return inventory_read(k->state_row,out);
}
static int inventory_sort_mode;
static int inventory_order(const void *a,const void *b){
    const inv_key_t *x=&inventory->keys[*(const int *)a],*y=&inventory->keys[*(const int *)b];int cmp;
    if(inventory_sort_mode==1)cmp=x->value<y->value?1:x->value>y->value?-1:0;
    else if(inventory_sort_mode==2)cmp=x->weight<y->weight?1:x->weight>y->weight?-1:0;
    else cmp=AW_InventoryCompare(x->name,y->name);
    return cmp?cmp:x->state_row-y->state_row;   /* the same order every time */
}
/* one carried kind's sort key from its record (NULL: the id as the name, Misc) */
static void inventory_key_row(void *ctx,int state_row,const aw_inventory_item_t *it,int file_row){
    inv_key_t *k=&inventory->keys[inventory->nkeys++];aw_inventory_item_t item;(void)ctx;
    k->file_row=file_row;
    if(it){item=*it;k->known=1;}
    else{memset(&item,0,sizeof(item));Q_strcpy_bounded(item.name,AW_ITEM_ID(&aw_state,state_row),sizeof(item.name));
         item.category=AW_INV_MISC;k->known=0;}
    k->state_row=state_row;k->value=item.value;k->weight=item.weight;
    k->category=(unsigned char)item.category;Q_strcpy_bounded(k->name,item.name,sizeof(k->name));
}
static void inventory_refresh(void){
    int i,kinds=AW_ItemCount(&aw_state);aw_inventory_item_t item;
    if(!inventory)return;
    free(inventory->keys);free(inventory->rows);inventory->keys=NULL;inventory->rows=NULL;inventory->nkeys=0;
    inventory->count=0;inventory->page_first=-1;inventory->one_row=-1;
    if(kinds>0){
        inventory->keys=(inv_key_t *)AW_TryMalloc(sizeof(inv_key_t)*kinds);
        inventory->rows=(int *)AW_TryMalloc(sizeof(int)*kinds);
        if(!inventory->keys || !inventory->rows){
            free(inventory->keys);free(inventory->rows);inventory->keys=NULL;inventory->rows=NULL;
            strcpy(inventory->message,"Inventory: not enough memory for the list.");kinds=0;
        }
    }
    /* the engine: every kind's record at once (one pass over the item file for more than 8 kinds, keeping each
     * kind's file row for the page reads; one search per kind opened the window with 400 kinds in 7 to 13 s); the
     * fixtures: one read per kind */
    if(kinds>0 && aw_inventory_carried && aw_inventory_carried(inventory_key_row,NULL)>=0){}
    else{
        inventory->nkeys=0;
        AW_InventoryBatchBegin();   /* the reads below share one open of the item file */
        for(i=0;i<kinds;i++){
            if(AW_ITEM_ROW(&aw_state,i)->value<=0)continue;
            inventory_key_row(NULL,i,inventory_read(i,&item)?&item:NULL,-1);
        }
        AW_InventoryBatchEnd();
    }
    inventory_filter();
}
/* the category's rows of the keys, sorted (Tab, the sort key and the category tabs: no record read again) */
static void inventory_filter(void){
    int i,n;
    if(!inventory)return;
    inventory->page_first=-1;inventory->one_row=-1;
    for(i=n=0;i<inventory->nkeys;i++)
        if(!inventory->category || inventory->keys[i].category==inventory->category)inventory->rows[n++]=i;
    inventory_sort_mode=inventory->sort;
    if(n>1)qsort(inventory->rows,n,sizeof(int),inventory_order);
    inventory->count=n;
    inventory->selected=minmax(inventory->selected,0,n?n-1:0);
    inventory->top=minmax(inventory->top,0,n>INV_VISIBLE?n-INV_VISIBLE:0);
    for(i=0;i<INV_VISIBLE;i++)inventory->icon_row[i]=-1;
}
/* the record of list row ROW: from the page (the rows in view and a page either side, read again when the view has
 * left it), else read into the one spare */
static aw_inventory_item_t *inventory_item(int row,int *known){
    int i,first;
    if(!inventory || row<0 || row>=inventory->count)return NULL;
    first=inventory->top-INV_VISIBLE;if(first<0)first=0;
    if(inventory->page_first<0 || inventory->top<inventory->page_first ||
       inventory->top+INV_VISIBLE>inventory->page_first+INV_PAGE){   /* the view left the page */
        AW_InventoryBatchBegin();
        for(i=0;i<INV_PAGE && first+i<inventory->count;i++)
            inventory->page_known[i]=(unsigned char)inventory_read_key(&inventory->keys[inventory->rows[first+i]],&inventory->page[i]);
        AW_InventoryBatchEnd();
        inventory->page_first=first;
    }
    if(row>=inventory->page_first && row<inventory->page_first+INV_PAGE){
        if(known)*known=inventory->page_known[row-inventory->page_first];
        return &inventory->page[row-inventory->page_first];
    }
    if(inventory->one_row!=row){inventory_read_key(&inventory->keys[inventory->rows[row]],&inventory->one);inventory->one_row=row;}
    if(known)*known=inventory->keys[inventory->rows[row]].known;
    return &inventory->one;
}
static aw_inventory_item_t *inventory_selected(void){
    return inventory && inventory->count?inventory_item(inventory->selected,NULL):NULL;
}
static int inventory_equippable(const aw_inventory_item_t *item){
    if(item && AW_InventoryEquipped(&aw_state,item->id) && (item->flags&AW_INV_EQUIP_SUPPORTED))return 1;
    return AW_InventoryCanEquip(item);
}
static int inventory_droppable(const aw_inventory_item_t *item){
    return item && (item->flags&AW_INV_DROP) &&
        (!AW_InventoryEquipped(&aw_state,item->id) || inventory_equippable(item));
}
static void inventory_action(int action){
    aw_inventory_item_t *item=inventory_selected();int ok=0;
    if(!item)return;
    inventory->preview_state=0;   /* equipment may change: one new still picture */
    if(action==1 && inventory_equippable(item)){
        AW_CombatEquipmentStore();
        if(AW_InventoryEquipped(&aw_state,item->id))ok=AW_InventoryUnequip(&aw_state,item->id);
        else ok=AW_InventoryEquip(&aw_state,item);
        if(ok)AW_CombatEquipmentChanged();
        strcpy(inventory->message,ok?"Equipment updated.":"Cannot equip this item.");
    }else if(action==2 && inventory_droppable(item)){
        /* First stage drops one real item; repeated actions preserve stack count.
         * No deletion occurs when the world placement/model/entity is refused. */
        ok=AW_InventoryDropHere(item,1);
        strcpy(inventory->message,ok?"Dropped one item.":AW_InventoryDropReason());
    }
    inventory->context=0;inventory_refresh();
}
/* Use the same bounded scrollbar as the journal. Keep a visible selection so
 * Equip/Drop still act on a displayed row; scrolling never changes ownership. */
static int inventory_list_right(void){
    return inventory->count>INV_VISIBLE?INV_SCROLL_X-2:312;
}
static void inventory_scroll(int top){
    inventory->top=minmax(top,0,inventory->count>INV_VISIBLE?inventory->count-INV_VISIBLE:0);
    inventory->selected=minmax(inventory->selected,inventory->top,
        minmax(inventory->top+INV_VISIBLE-1,0,inventory->count?inventory->count-1:0));
    inventory->context=0;
}
static void inventory_key(int key){
    int i,x,y,row,top;aw_inventory_item_t *item=inventory_selected();
    if(!inventory)return;
    drag=0;
    /* The original picture does not turn; turning is the live preview's (aw_inventory_preview_live 1). */
    if(key==K_LEFTARROW){if(AW_ViewInventoryLive())inventory->angle-=.25f;return;}
    if(key==K_RIGHTARROW){if(AW_ViewInventoryLive())inventory->angle+=.25f;return;}
    if(key==K_UPARROW || key=='w' || key==K_MWHEELUP)inventory->selected--;
    if(key==K_DOWNARROW || key=='s' || key==K_MWHEELDOWN)inventory->selected++;
    if(key==K_PGUP)inventory->selected-=INV_VISIBLE;
    if(key==K_PGDN)inventory->selected+=INV_VISIBLE;
    if(key==K_HOME)inventory->selected=0;
    if(key==K_END)inventory->selected=inventory->count-1;
    if(key==K_TAB){inventory->category=(inventory->category+1)%8;inventory->selected=inventory->top=0;inventory_filter();}
    if(key=='o'){inventory->sort=(inventory->sort+1)%3;inventory_filter();}
    if(key==K_ENTER || key=='e'){inventory_action(1);return;}
    if(key=='d'){inventory_action(2);return;}
    if(key==K_MOUSE3 || key==K_MOUSE2){
        if(mouse_x<128 || mouse_x>=inventory_list_right() || mouse_y<INV_LIST_Y || mouse_y>=INV_LIST_Y+INV_VISIBLE*INV_ROW_H)return;
        row=inventory->top+(mouse_y-INV_LIST_Y)/INV_ROW_H;if(row>=inventory->count)return;
        inventory->selected=row;
        inventory->context=inventory->count!=0;
        inventory->context_x=minmax(mouse_x,128,206);inventory->context_y=minmax(mouse_y,50,INV_CONTROLS_Y-2*16-4);
        return;
    }
    if(key==K_MOUSE1){
        if(inventory->context){
            x=inventory->context_x;y=inventory->context_y;row=0;
            if(inventory_equippable(item)){
                if(mouse_x>=x && mouse_x<x+110 && mouse_y>=y+row*16 && mouse_y<y+(row+1)*16){inventory_action(1);return;}
                row++;
            }
            if(inventory_droppable(item)){
                if(mouse_x>=x && mouse_x<x+110 && mouse_y>=y+row*16 && mouse_y<y+(row+1)*16){inventory_action(2);return;}
            }
            inventory->context=0;return;
        }
        top=AW_UIScrollHit(mouse_x,mouse_y,INV_SCROLL_X,INV_LIST_Y,
            INV_SCROLL_H,inventory->count,INV_VISIBLE,inventory->top);
        if(top>=0){
            inventory_scroll(top);
            /* Arrow clicks step once; only the inner rail starts a drag. */
            if(mouse_y>=INV_LIST_Y+10 && mouse_y<INV_LIST_Y+INV_SCROLL_H-10)drag=K_MOUSE1;
            return;
        }
        if(mouse_y>=20 && mouse_y<44 && mouse_x>=128){
            row=(mouse_y-20)/12;x=130;
            for(i=row*4;i<row*4+4;i++){
                int width=i==0?28:i==1?48:i==2?48:i==3?60:i==4?44:i==5?66:i==6?40:30;
                if(mouse_x>=x && mouse_x<x+width){inventory->category=i;inventory->selected=inventory->top=0;inventory_filter();return;}x+=width;
            }
        }
        if(mouse_x>=128 && mouse_x<inventory_list_right() && mouse_y>=INV_LIST_Y && mouse_y<INV_LIST_Y+INV_VISIBLE*INV_ROW_H){
            row=inventory->top+(mouse_y-INV_LIST_Y)/INV_ROW_H;
            if(row<inventory->count)inventory->selected=row;
        }
        /* Close only over its displayed hint; the lower navigation row is
         * no longer an invisible full-width close target. */
        if(mouse_x>=INV_CLOSE_X && mouse_x<INV_CLOSE_X+INV_CLOSE_W &&
           mouse_y>=INV_CONTROLS_Y && mouse_y<INV_CONTROLS_Y+8){close_panel();return;}
    }
    inventory->selected=minmax(inventory->selected,0,inventory->count?inventory->count-1:0);
    if(inventory->selected<inventory->top)inventory->top=inventory->selected;
    if(inventory->selected>=inventory->top+INV_VISIBLE)inventory->top=inventory->selected-INV_VISIBLE+1;
}
/* aw_icons.c: the original 16 x 16 inventory icon (UI-ICONS-INVENTORY-42); 0 = draw the old way. */
int (*aw_inventory_row_icon)(int slot,const char *id,int equipped,int x,int y);
/* INDEX: the list row */
static void inventory_icon(int slot,int index,int x,int y){
    FILE *f=NULL;int size,xx,yy;byte raw[1028];const aw_inventory_item_t *it=inventory_item(index,NULL);
    if(!it)return;
    if(aw_inventory_row_icon && aw_inventory_row_icon(slot,it->id,AW_InventoryEquipped(&aw_state,it->id)>0,x,y))return;
    if(inventory->icon_row[slot]!=index){
        inventory->icon_row[slot]=index;inventory->icon_ok[slot]=0;
        if(it->icon[0]){
            size=COM_FOpenFile((char *)it->icon,&f);
            if(f){if(size==1028 && fread(raw,1,sizeof(raw),f)==sizeof(raw) && !memcmp(raw,"AWIC",4)){
                memcpy(inventory->icons[slot],raw+4,1024);inventory->icon_ok[slot]=1;
            }fclose(f);}
        }
    }
    AW_UIBox(x,y,16,16);
    if(inventory->icon_ok[slot])for(yy=0;yy<14;yy++)for(xx=0;xx<14;xx++)
        vid.buffer[(y+1+yy)*vid.rowbytes+x+1+xx]=inventory->icons[slot][(yy*32/14)*32+xx*32/14];
}
/* Fixed console-derived glyphs fit the 320x200 fields. Menu TextBox centres
 * but does not clip: using it for long item names painted across other panels. */
static void inventory_text(int x,int y,int width,int height,const char *value,int color){
    char clipped[160];int n=(int)strlen(value),limit=width/4;
    if(limit<1)return;
    if(limit>(int)sizeof(clipped)-1)limit=sizeof(clipped)-1;
    if(n>limit)n=limit;
    memcpy(clipped,value,n);clipped[n]=0;
    if(value[n] && n>=3)memcpy(clipped+n-3,"...",3);
    AW_SmallStringColor(x,y+(height-5)/2,width,clipped,color);
}
/* Two fixed-size status lines share the existing 3x5 glyph helper. Prefer a
 * word boundary, with the second line retaining the helper's bounded ellipsis. */
static void inventory_status(const char *value,int color){
    char first[46];int n=(int)strlen(value),split,i;
    if(n<=45){inventory_text(132,INV_STATUS_Y,180,5,value,color);return;}
    split=45;
    for(i=44;i>0;i--)if(value[i]==' '){split=i;break;}
    memcpy(first,value,split);first[split]=0;
    inventory_text(132,INV_STATUS_Y,180,5,first,color);
    value+=split;while(*value==' ')value++;
    inventory_text(132,INV_STATUS_Y+8,180,5,value,color);
}
/* The character picture (UI-INVENTORY-PREVIEW-STILL-42). The original shows a still picture of
 * the character in the inventory pose of the equipped weapon type, facing the viewer; OpenMW
 * renders it once into a texture (mwrender/characterpreview.cpp: DrawOnceCallback,
 * CharacterPreview::redraw; InventoryPreview::update picks the pose) and redraws it only when the
 * equipment changes (mwgui/inventorywindow.cpp dirtyPreview). Here: one render into the window,
 * copied into a 116 x 168 picture, the pose model and depth buffer freed at once; every later
 * frame only copies the picture back. aw_inventory_preview_live 1: the old live, turnable preview. */
static void inventory_preview(int muted){
    model_t *model=NULL;int frame,y,ok;double t0=Sys_FloatTime(),t1;byte *row;
    if(AW_ViewInventoryLive()){
        if(!AW_ViewInventoryBody(&model,&frame) || !AW_InventoryPreviewDraw(model,frame,INV_PREVIEW_X,INV_PREVIEW_Y,
                                                                            INV_PREVIEW_W,INV_PREVIEW_H,inventory->angle))
            inventory_text(10,80,108,40,"Character preview unavailable",muted);
    }else{
        if(!inventory->preview_state){
            ok=AW_ViewInventoryBody(&model,&frame) &&
               AW_InventoryPreviewDraw(model,frame,INV_PREVIEW_X,INV_PREVIEW_Y,INV_PREVIEW_W,INV_PREVIEW_H,(float)M_PI);
            if(ok)for(y=0;y<INV_PREVIEW_H;y++)
                memcpy(inventory->preview+y*INV_PREVIEW_W,vid.buffer+(INV_PREVIEW_Y+y)*vid.rowbytes+INV_PREVIEW_X,INV_PREVIEW_W);
            AW_InventoryPreviewClear();      /* pose model and depth buffer are not kept */
            inventory->preview_state=ok?1:-1;inventory->preview_renders++;
            t1=Sys_FloatTime();inventory->preview_render_seconds=t1-t0;t0=t1;
        }else if(inventory->preview_state>0){
            for(y=0;y<INV_PREVIEW_H;y++){
                row=vid.buffer+(INV_PREVIEW_Y+y)*vid.rowbytes+INV_PREVIEW_X;memcpy(row,inventory->preview+y*INV_PREVIEW_W,INV_PREVIEW_W);
            }
        }
        if(inventory->preview_state<0)inventory_text(10,80,108,40,"Character preview unavailable",muted);
    }
    inventory->preview_seconds+=Sys_FloatTime()-t0;inventory->preview_frames++;
}
/* The original window title bar (UI-WINDOW-TITLE-BAR-42), drawn by aw_icons.c from the
 * imported art; without it the title is centred alone in the same band. */
int (*aw_title_bar)(int x,int y,int w,const char *title);
const char *(*aw_hand_to_hand_name)(void);
/* The original inventory window's title is the equipped weapon's name, or the hand-to-hand skill's
 * name when unarmed (OpenMW mwgui/windowmanagerimp.cpp setSelectedWeapon / hud.cpp
 * unsetSelectedWeapon set the inventory window title). */
static const char *inventory_title(void){
    static aw_inventory_item_t item;const char *name;
    if(AW_InventoryEquippedItem(AW_SLOT_RIGHT,&item) && item.category==AW_INV_WEAPON && item.name[0])return item.name;
    name=aw_hand_to_hand_name?aw_hand_to_hand_name():NULL;
    return name && *name?name:"Inventory";
}
static void window_title(int x,int y,int w,const char *title,int color){
    if(!aw_title_bar || !aw_title_bar(x,y,w,title))AW_UITextCentred(x,y,w,12,title,color);
}
/* The burden bar (ENCUMBRANCE-INCOMPLETE-61): OpenMW mwgui/inventorywindow.cpp updateEncumbranceBar, every frame the
 * window is open: ceil(encumbrance) over the capacity, as "N/M" on the blue bar (MW_ChargeBar_Blue; here the original
 * bar art of the magicka bar, AW_UIBar colour 1). The encumbrance is the running total (aw_move.h), nothing summed. */
float (*aw_worldui_encumbrance)(float *capacity);
static void inventory_burden(void){
    char line[32];float capacity=0,load;int shown,max;
    if(!aw_worldui_encumbrance)return;
    load=aw_worldui_encumbrance(&capacity);
    shown=(int)load;if((float)shown<load)shown++;     /* std::ceil */
    max=(int)capacity;
    AW_UIBar(8,INV_BURDEN_Y,114,INV_BURDEN_H,1,max>0?(float)shown/(float)max:shown>0?1.0f:0.0f);
    sprintf(line,"%d/%d",shown,max);
    AW_UISmallBegin();AW_UITextCentred(8,INV_BURDEN_Y,114,INV_BURDEN_H,line,AW_UIColor(223,199,144));AW_UISmallEnd();
}
static void inventory_draw(void){
    int i,j,x,row,index,right=inventory_list_right();aw_inventory_item_t *item;char line[160];
    int gold=AW_UIColor(223,199,144),muted=AW_UIColor(150,135,104);
    AW_UIFill(0,0,320,200,AW_UIColor(0,0,0));AW_UIBox(2,2,316,196);
    AW_UIBox(4,18,122,178);AW_UIBox(128,18,188,178);
    AW_UISmallBegin();
    window_title(6,6,308,inventory_title(),gold);
    AW_UISmallEnd();
    inventory_preview(muted);
    inventory_burden();
    for(row=0;row<2;row++){
        x=130;
        for(i=row*4;i<row*4+4;i++){
            int width=i==0?28:i==1?48:i==2?48:i==3?60:i==4?44:i==5?66:i==6?40:30;
            if(i==inventory->category)AW_UIFill(x,20+row*12,width,11,AW_UIColor(48,39,22));
            inventory_text(x+1,20+row*12,width-2,11,inventory_categories[i],gold);x+=width;
        }
    }
    sprintf(line,"Sort: %s (O)",inventory->sort==1?"Value":inventory->sort==2?"Weight":"Name");
    inventory_text(132,44,180,10,line,muted);
    if(!inventory->count)inventory_text(134,73,174,38,"No carried items in this category.",muted);
    for(i=0;i<INV_VISIBLE && (row=inventory->top+i)<inventory->count;i++){
        item=inventory_item(row,NULL);if(!item)break;
        if(row==inventory->selected)AW_UIFill(130,INV_LIST_Y+i*INV_ROW_H,right-130,INV_ROW_H,AW_UIColor(44,36,20));
        inventory_icon(i,row,132,INV_LIST_Y+i*INV_ROW_H);
        sprintf(line,"%s%s",AW_InventoryEquipped(&aw_state,item->id)?"* ":"",item->name);
        inventory_text(151,INV_LIST_Y+i*INV_ROW_H,right-24-151,11,line,gold);
        sprintf(line,"%ld",(long)AW_StateGet(&aw_state,AW_ITEM,item->id));inventory_text(right-22,INV_LIST_Y+i*INV_ROW_H,22,11,line,gold);
    }
    if(inventory->count>INV_VISIBLE)
        AW_UIScrollbar(INV_SCROLL_X,INV_LIST_Y,INV_SCROLL_H,inventory->count,INV_VISIBLE,inventory->top);
    index=0;item=inventory->count?inventory_item(inventory->selected,&index):NULL;
    if(item){
        if(index)sprintf(line,"Weight %.2f  Value %ld",item->weight,(long)item->value);
        else strcpy(line,"Item details unavailable");
        inventory_text(132,INV_DETAILS_Y,180,8,line,muted);
        inventory_status(inventory->message[0]?inventory->message:
            inventory_equippable(item)?"E/Enter equip  D drop  RMB actions":
            inventory_droppable(item)?"D drop  RMB actions":"Actions unavailable for this item",muted);
    }
    if(inventory->context && item){
        x=inventory->context_x;j=inventory->context_y;row=0;
        if(inventory_equippable(item))row++;
        if(inventory_droppable(item))row++;
        if(row){
            AW_UIFill(x,j,110,row*16,AW_UIColor(10,9,7));AW_UIBox(x,j,110,row*16);row=0;
            if(inventory_equippable(item)){inventory_text(x+4,j+row*16+2,102,13,AW_InventoryEquipped(&aw_state,item->id)?"Unequip":"Equip",gold);row++;}
            if(inventory_droppable(item))inventory_text(x+4,j+row*16+2,102,13,"Drop one",gold);
        }else inventory->context=0;
    }
    /* Frame bottom pixels are 192..195: all footer glyphs finish by188. */
    AW_UIFill(132,INV_CONTROLS_Y-2,180,1,muted);
    inventory_text(INV_CLOSE_X,INV_CONTROLS_Y,INV_CLOSE_W,5,"I/Esc close",gold);
    inventory_text(192,INV_CONTROLS_Y,120,5,"Tab category",gold);
    /* Turning belongs to the old live preview only (UI-INVENTORY-PREVIEW-STILL-42). */
    inventory_text(132,INV_CONTROLS_Y+8,180,5,AW_ViewInventoryLive()?"Up/Down select   Left/Right turn":"Up/Down select",gold);
}
static void map_fit(void){
    float sx=(float)map_w/310,sy=(float)map_h/150;
    map_step=(sx>sy?sx:sy)/(1<<zoom);
}
static void map_home(void){zoom=0;map_x=map_w*.5f;map_y=map_h*.5f;map_fit();}
static void update_player(void){
    int i;float world[3];edict_t *e;
    marker=0;
    if(!sv.active || !svs.clients || !(e=svs.clients[0].edict))return;
    if(AW_WorldToSource(sv.name,e->v.origin,world)){
        player_x=world[0];player_y=world[1];player_z=world[2];marker=1;return;
    }
    /* Legacy converted payloads predate AWR2. Their AWM1 transform is explicit. */
    for(i=0;i<area_count;i++)if(!strcmp(sv.name,areas[i].id)){
        player_x=e->v.origin[0]/areas[i].scale+areas[i].x;
        player_y=e->v.origin[1]/areas[i].scale+areas[i].y;
        player_z=e->v.origin[2]/areas[i].scale;marker=1;return;
    }
}
static void map_player(void){
    if(!marker)return;
    update_player();
    map_x=(player_x-map_bounds[0])*map_w/(map_bounds[2]-map_bounds[0]);
    map_y=(map_bounds[3]-player_y)*map_h/(map_bounds[3]-map_bounds[1]);
}
/* Hiding the HUD diagnostics must not disable explicit map commands/tabs. */
static int map_debug_enabled(void){return aw_map_debug_available.value!=0;}
static int map_in_game(void){
    if(aw_map_mode.value<0 || aw_map_mode.value>1)Cvar_SetValue(aw_map_mode.name,0);
    if(!map_debug_enabled() && aw_map_mode.value<1)Cvar_SetValue(aw_map_mode.name,1);
    return aw_map_mode.value>=1;
}
/* LAVA section: "LAVA", pools, points, colour; per pool <hhHH4i> cell, point count, 0,
 * bounds; then <ii> points. Source units, the same transform as the AWM1 pixels. */
static int lava_section(const byte *p,int size){
    int pools,points,i,j,n,total=0;const byte *q,*pt;int32_t b[4],x,y;
    lava_count=0;lava_pools=lava_points=NULL;
    if(size<16 || memcmp(p,"LAVA",4))return 0;
    pools=(int)u32(p+4);points=(int)u32(p+8);lava_colour=(int)u32(p+12);
    if(pools<0 || pools>LAVA_POOLS_MAX || points<0 || points>pools*LAVA_POINTS || lava_colour<0 || lava_colour>255)return 0;
    if(size!=16+pools*24+points*8)return 0;
    pt=p+16+pools*24;
    for(i=0;i<pools;i++){
        q=p+16+i*24;n=q[4]|(q[5]<<8);
        if(n<1 || n>LAVA_POINTS || q[6] || q[7] || total+n>points)return 0;
        for(j=0;j<4;j++){b[j]=(int32_t)u32(q+8+j*4);if(b[j]<-2000000 || b[j]>2000000)return 0;}
        if(b[2]<b[0] || b[3]<b[1])return 0;
        for(j=0;j<n;j++){
            x=(int32_t)u32(pt+(total+j)*8);y=(int32_t)u32(pt+(total+j)*8+4);
            if(x<b[0] || x>b[2] || y<b[1] || y>b[3])return 0;
        }
        total+=n;
    }
    if(total!=points)return 0;
    lava_pools=p+16;lava_points=pt;lava_count=pools;return 1;
}
static void open_map(void){
    FILE *f=NULL;int size,i,off,version;byte *p;
    if(!allowed())return;
    map_in_game();
    size=COM_FOpenFile("world/map.awm",&f);
    if(!f || size<32 || size>MAP_MAX)goto bad;
    map_data=(byte *)AW_TryMalloc(size);if(!map_data)goto bad;
    if(fread(map_data,1,size,f)!=(size_t)size)goto bad;
    fclose(f);f=NULL;p=map_data;
    if(!memcmp(p,"AWM1",4))version=1;else if(!memcmp(p,"AWM2",4))version=2;else goto bad;
    lava_count=0;lava_pools=lava_points=NULL;
    map_w=p[4]+(p[5]<<8);map_h=p[6]+(p[7]<<8);area_count=(int)u32(p+24);
    if(map_w<1 || map_w>512 || map_h<1 || map_h>512 || area_count<0 || area_count>8)goto bad;
    off=32+area_count*60;map_ocean=(int)u32(p+28);if(map_ocean<0 || map_ocean>255)goto bad;
    if(version==1?size!=off+map_w*map_h:
       (size<off+map_w*map_h || !lava_section(map_data+off+map_w*map_h,size-off-map_w*map_h)))goto bad;
    for(i=0;i<4;i++){map_bounds[i]=(int32_t)u32(p+8+i*4);if(map_bounds[i]<-2000000 || map_bounds[i]>2000000)goto bad;}
    if(map_bounds[2]<=map_bounds[0] || map_bounds[3]<=map_bounds[1])goto bad;
    marker=0;
    for(i=0;i<area_count;i++){
        p=map_data+32+i*60;if(!memchr(p,0,16) || !memchr(p+16,0,32))goto bad;
        memcpy(areas[i].id,p,16);memcpy(areas[i].title,p+16,32);areas[i].x=f32(p+48);areas[i].y=f32(p+52);areas[i].scale=f32(p+56);
        if(!(areas[i].scale>=.0009765625f && areas[i].scale<=100 && areas[i].x>=-2000000 && areas[i].x<=2000000 &&
             areas[i].y>=-2000000 && areas[i].y<=2000000))goto bad;
    }
    update_player();map_pixels=map_data+off;
    if(!map_view_ready){map_home();map_view_ready=1;}else map_fit();
    opened(1);
    if(marker)Con_Printf("World map position: %ld %ld %ld (%s).\n",(long)player_x,(long)player_y,(long)player_z,sv.name);
    Con_Printf("World map: %ld bytes on demand; %s position.\n",(long)size,marker?"exterior":"no exterior");
    if(version==2)Con_Printf("World map v2: %d lava pools.\n",lava_count);
    return;
 bad:
    if(f)fclose(f);
    free(map_data);map_data=map_pixels=NULL;lava_pools=lava_points=NULL;lava_count=0;
    Con_Printf("World map missing, invalid, or not enough memory.\n");
}
/* M follows the current HUD preference; explicit teleport remains independent. */
static void open_normal_map(void){
    if(!allowed())return;
    Cvar_SetValue(aw_map_mode.name,AW_DebugOverlaysEnabled() && map_debug_enabled()?0:1);
    open_map();
}
static int normal_teleport_enabled(void){
    return !teleport_mode && map_debug_enabled() && !map_in_game() && AW_DebugOverlaysEnabled();
}
static int teleport_button_y(void){return teleport_mode?184:156;}
static int teleport_button_hit(void){
    int y=teleport_button_y();
    return teleport_selected && (teleport_mode || normal_teleport_enabled()) &&
        mouse_x>=TELEPORT_X && mouse_x<TELEPORT_X+TELEPORT_W && mouse_y>=y && mouse_y<y+TELEPORT_H;
}
static int clear_button_hit(void){
    return mouse_x>=CLEAR_X && mouse_x<CLEAR_X+CLEAR_W && mouse_y>=CLEAR_Y && mouse_y<CLEAR_Y+CLEAR_H;
}
/* Both picks use the exact AWM1 texture-to-original-source transform. */
static int map_source_at(float point[3]){
    float px=map_x-156*map_step+(mouse_x-4)*map_step;
    float py=map_y-77*map_step+(mouse_y-19)*map_step;
    if(mouse_x<4 || mouse_x>=316 || mouse_y<19 || mouse_y>=173 ||
       px<0 || px>=map_w || py<0 || py>=map_h)return 0;
    point[0]=map_bounds[0]+px*(map_bounds[2]-map_bounds[0])/map_w;
    point[1]=map_bounds[3]-py*(map_bounds[3]-map_bounds[1])/map_h;
    point[2]=0;return 1;
}
static int custom_marker(float point[3]){
    if(AW_StateGet(&aw_state,AW_GLOBAL,marker_keys[2])!=1)return 0;
    point[0]=AW_StateGet(&aw_state,AW_GLOBAL,marker_keys[0]);
    point[1]=AW_StateGet(&aw_state,AW_GLOBAL,marker_keys[1]);point[2]=0;
    return point[0]>=map_bounds[0] && point[0]<map_bounds[2] && point[1]>map_bounds[1] && point[1]<=map_bounds[3];
}
static void place_marker(void){
    float point[3];int i,j,missing=0;int32_t x,y;
    if(!map_source_at(point)){marker_message="Outside map bounds";return;}
    /* Preflight all keys: a full global table must not partially move a marker. */
    for(i=0;i<3;i++){
        for(j=0;j<aw_state.count[AW_GLOBAL];j++)if(!strcmp(aw_state.values[AW_GLOBAL][j].id,marker_keys[i]))break;
        if(j==aw_state.count[AW_GLOBAL])missing++;
    }
    if(missing>AW_STATE_VALUES-aw_state.count[AW_GLOBAL]){
        marker_message="Marker not saved: globals full";Con_Printf("Map marker: global state capacity exhausted.\n");return;
    }
    x=minmax((int)floor(point[0]+.5f),map_bounds[0],map_bounds[2]-1);
    y=minmax((int)floor(point[1]+.5f),map_bounds[1]+1,map_bounds[3]);
    AW_StateSet(&aw_state,AW_GLOBAL,marker_keys[0],x);
    AW_StateSet(&aw_state,AW_GLOBAL,marker_keys[1],y);
    AW_StateSet(&aw_state,AW_GLOBAL,marker_keys[2],1);marker_message=NULL;
}
static void clear_marker(void){
    /* Clearing an absent marker must not consume another global slot. */
    if(AW_StateGet(&aw_state,AW_GLOBAL,marker_keys[2]))AW_StateSet(&aw_state,AW_GLOBAL,marker_keys[2],0);
    marker_message="Marker cleared";marker_click=0;
}
static void open_teleport_map(void){
    keydest_t previous=key_dest;
    if(Cmd_Argc()!=1){Con_Printf("Usage: dbg tp map / dbg map tp\n");return;}
    if(!map_debug_enabled()){
        Con_Printf("Debug map disabled by aw_map_debug_available.\n");return;
    }
    if(modal || (key_dest!=key_game && key_dest!=key_console)){
        Con_Printf("Close the current panel before opening the teleport map.\n");return;
    }
    key_dest=key_game;
    if(!allowed()){
        key_dest=previous;
        Con_Printf("Teleport map requires active single-player gameplay outside story/reader/gallery panels.\n");return;
    }
    open_map();
    if(modal!=1){key_dest=previous;return;}
    teleport_mode=1;teleport_selected=0;teleport_message=NULL;
    mouse_x=160;mouse_y=100;
}
static void select_teleport_point(void){
    const char *region;
    teleport_selected=0;marker_message=NULL;
    if(!map_source_at(teleport_point)){teleport_message="Outside map bounds";return;}
    region=AW_RegionNameAt(teleport_point);
    strncpy(teleport_region,region?region:"Region unavailable",sizeof(teleport_region)-1);
    teleport_region[sizeof(teleport_region)-1]=0;
    teleport_selected=1;teleport_message=NULL;
}
static void confirm_teleport(void){
    if(!teleport_selected)return;
    if(AW_MapTeleport(teleport_point))close_panel();
    else teleport_message="Destination unavailable";
}
/* Sorted fixed records permit bounded disk lookups. Offset includes a possible
 * pak member start; no assumption that COM_FOpenFile starts at byte zero. */
/* The index row of (ID, STAGE): 1 and its text's place and its quest status flags (AWJ2: 1 finished, 2 restart,
 * 4 name; AWJ1 rows have none). JOURNAL-BOOK-32-QUESTS-59. */
static int journal_row(const char *id,int stage,uint32_t *offset,uint32_t *length,uint32_t *flags){
    FILE *f=NULL;byte header[8],row[80];int size,count,lo,hi,mid,cmp,found=0,width;long base;
    size=COM_FOpenFile("world/journal.awj",&f);if(!f)return 0;
    base=ftell(f);
    if(size<8 || fread(header,1,8,f)!=8)goto end_index;
    if(!memcmp(header,"AWJ2",4))width=80;else if(!memcmp(header,"AWJ1",4))width=76;else goto end_index;
    count=(int)u32(header+4);if(count<0 || count>10000 || size!=8+count*width)goto end_index;
    lo=0;hi=count;
    while(lo<hi){
        mid=lo+(hi-lo)/2;
        if(fseek(f,base+8+(long)mid*width,SEEK_SET) || fread(row,1,width,f)!=(size_t)width || !memchr(row,0,64))break;
        cmp=strcmp(id,(char *)row);
        if(!cmp){int value=(int32_t)u32(row+64);cmp=stage<value?-1:stage>value?1:0;}
        if(!cmp){*offset=u32(row+68);*length=u32(row+72);*flags=width==80?u32(row+76):0;found=1;break;}
        if(cmp<0)hi=mid;else lo=mid+1;
    }
 end_index:
    fclose(f);
    return found;
}
static int entry_text(const char *id,int stage,char *out,int capacity){
    FILE *f=NULL;int size,found;uint32_t offset=0,length=0,flags;long base;
    found=journal_row(id,stage,&offset,&length,&flags);
    if(!found || length<1 || length>(uint32_t)capacity)return 0;
    size=COM_FOpenFile("world/entries.dat",&f);if(!f)return 0;base=ftell(f);
    found=size>0 && offset<=(uint32_t)size && length<=(uint32_t)size-offset &&
        !fseek(f,base+offset,SEEK_SET) && fread(out,1,length,f)==length;
    fclose(f);
    return found && !out[length-1] && !memchr(out,0,length-1);
}
/* The entry's text defines through the one getter table (aw_textdef.c, BOOK-TEXT-MACROS-58); 0 when the filled
 * text would not fit (as before: the entry is not shown cut). */
static int expand_entry(void){
    aw_textdef_values_t v;int n;
    AW_TextDefinesPlayer(&v);
    n=AW_TextDefines(book->text,(int)sizeof(book->text),book->raw,&v);
    return n<(int)sizeof(book->text)-1;
}
static int eligible(int i){return i>=0 && i<book->qb.entries && (book->filter<0 || book->qb.entry[i].group==book->filter);}
static int next_entry(int i,int step){for(i+=step;i>=0 && i<book->qb.entries;i+=step)if(eligible(i))return i;return -1;}
/* An entry's quest id: its catalogue row's, else the dated entry's own (a quest the catalogue lacks). */
static const char *entry_id(int i){
    const aw_qb_entry_t *e=&book->qb.entry[i];
    return e->quest>=0?book->quests[e->quest].id:"";
}
/* An entry's heading: its quest's name, else its id with spaces (as the book did before names were read) */
static const char *entry_title(int i){
    static char derived[AW_QB_TITLE];const aw_qb_entry_t *e=&book->qb.entry[i];int j;
    if(e->quest>=0 && book->quests[e->quest].title[0])return book->quests[e->quest].title;
    snprintf(derived,sizeof(derived),"%s",entry_id(i));
    for(j=0;derived[j];j++)if(derived[j]=='_')derived[j]=' ';
    return derived;
}
static const char *shown_title(int row){return book->quests[book->qb.group[book->shown[row]].quest].title;}
/* Centre only already-wrapped lines: AW_UITextBox does not clip. */
static int title_rows(const char *p){
    char line[160];int rows=0;
    do {p=AW_UILine(p,BOOK_WIDTH,line,sizeof(line));rows++;}while(*p);
    return rows;
}
static int page_lines(int page){return BOOK_LINES-((page&1)?0:book->title_rows-1);}
static void index_layout(void){
    int i,col=0,row=0,lines;
    for(i=book->index_top;i<book->nshown;i++){
        lines=title_rows(shown_title(i));
        if(row+lines>BOOK_LINES){col++;row=0;}
        if(col>=2)break;
        book->index_x[i]=14+col*156;book->index_y[i]=40+row*14;book->index_rows[i]=lines;
        row+=lines+1;
    }
    book->index_end=i;
}
static void load_entry(int index){
    int i;const char *p,*before;char line[160];
    book->entry=index;book->spread=0;book->count=0;
    if(index<0){strcpy(book->text,"No dated journal entries have been recorded yet. Entries appear here as you earn them during play.");}
    else {
        if(!entry_text(entry_id(index),book->qb.entry[index].stage,book->raw,sizeof(book->raw)))
            strcpy(book->text,"This earned entry has no matching text in the installed journal catalogue. Its quest stage and date remain saved.");
        else if(!expand_entry())strcpy(book->text,"This entry exceeds the reader's text capacity. Its saved history remains intact.");
    }
    AW_UIBookBegin();book->title_rows=1;
    if(index>=0){
        book->title_rows=title_rows(entry_title(index));
    }
    p=book->text;
    while(*p && book->count<BOOK_PAGES){
        book->pages[book->count++]=(unsigned short)(p-book->text);before=p;
        for(i=0;i<page_lines(book->count-1) && *p;i++){before=p;p=AW_UILine(p,BOOK_WIDTH,line,sizeof(line));if(p==before)break;}
        if(page_lines(book->count-1)>0 && p==before && *p)break;
    }
    AW_UIBookEnd();
    if(*p){strcpy(book->text,"This entry exceeds the reader's page capacity. Its saved history remains intact.");book->count=1;book->pages[0]=0;}
    if(!book->count){book->count=1;book->pages[0]=0;}
}
/* the dialogue's journal pages (aw_dialwin.c sets these at start; none in the tools' native tests) */
int (*aw_journal_heard_count)(void);
int (*aw_journal_heard_at)(int i,int *entry,int *topic,const char **speaker);
int (*aw_journal_topic_name)(int topic,char *out,int capacity);
int (*aw_journal_entry_text)(int entry,char *out,int capacity);
int (*aw_journal_entry_marked)(int entry,char *out,int capacity,unsigned short *topics,int max);
/* the topics the journal's pages hold (aw_dial.c AW_DialHeard*), by name (any case), each once */
static void topic_list(void){
    int i,j,entry,topic;const char *speaker;
    book->topics=0;
    if(!aw_journal_heard_count || !aw_journal_heard_at || !aw_journal_topic_name)return;
    for(i=0;i<aw_journal_heard_count() && book->topics<BOOK_TOPICS;i++){
        aw_journal_heard_at(i,&entry,&topic,&speaker);
        for(j=0;j<book->topics && book->topic_id[j]!=topic;j++);
        if(j<book->topics)continue;
        if(!aw_journal_topic_name(topic,book->topic_name[book->topics],sizeof(book->topic_name[0])))
            sprintf(book->topic_name[book->topics],"Topic %d",topic);
        for(j=book->topics;j>0 && Q_strcasecmp(book->topic_name[j-1],book->topic_name[book->topics])>0;j--);
        if(j<book->topics){   /* insert sorted */
            char name[40];strcpy(name,book->topic_name[book->topics]);
            memmove(book->topic_name+j+1,book->topic_name+j,sizeof(book->topic_name[0])*(size_t)(book->topics-j));
            memmove(book->topic_id+j+1,book->topic_id+j,sizeof(book->topic_id[0])*(size_t)(book->topics-j));
            strcpy(book->topic_name[j],name);
        }
        book->topic_id[j]=(short)topic;book->topics++;
    }
}
/* the topic list's row of TOPIC, -1 when the journal has no page for it (then its name is not a link) */
static int topic_row(int topic){
    int j;
    for(j=0;j<book->topics;j++)if(book->topic_id[j]==topic)return j;
    return -1;
}
/* One line of a topic page with its links: a link's words in the link colour and kept as a hit box (the marks give the
 * link's number in the page, *OPENS counts the marks before, *INSIDE whether a link runs on from the line before). */
static void linked_line(int x,int y,const char *line,int *opens,int *inside,int ink,int link_ink){
    char one[2];int start=x,c,row;
    one[1]=0;
    for(;;line++){
        c=(unsigned char)*line;
        row=*inside && *opens>0 && *opens-1<book->links?topic_row(book->link_topic[*opens-1]):-1;
        if((!c || c==3) && row>=0 && x>start && book->hits<BOOK_HITS){   /* the piece of the link that ends here */
            book->hit[book->hits].x=(short)start;book->hit[book->hits].y=(short)y;book->hit[book->hits].w=(short)(x-start);
            book->hit[book->hits].link=(short)(*opens-1);book->hits++;
        }
        if(!c)break;
        if(c==2){*inside=1;(*opens)++;start=x;continue;}
        if(c==3){*inside=0;start=x;continue;}
        one[0]=(char)c;AW_UIText(x,y,one,row>=0?link_ink:ink);x+=AW_UIWidth(one);
    }
}
/* a topic's page: every entry heard, "Speaker: text", in the order heard (the defines filled as they read now) */
static void load_topic(int k){
    int i,n=0,entry,topic;const char *speaker,*p,*before;char line[160],said[1024],filled[1100];
    book->topic_open=k;book->entry=-2;book->spread=0;book->count=0;book->text[0]=0;book->links=0;
    for(i=0;aw_journal_heard_count && aw_journal_entry_text && i<aw_journal_heard_count();i++){
        aw_journal_heard_at(i,&entry,&topic,&speaker);
        if(topic!=book->topic_id[k])continue;
        if(aw_journal_entry_marked){   /* the text with its links marked, their topics kept in mark order */
            int got=aw_journal_entry_marked(entry,said,sizeof(said),book->link_topic+book->links,BOOK_LINKS-book->links);
            if(got<0)continue;
            if(book->links+got<=BOOK_LINKS)book->links+=got;
        }else if(!aw_journal_entry_text(entry,said,sizeof(said)))continue;
        Q_snprintf(filled,sizeof(filled),"%s",said);   /* the readers give the text with its %-values filled */
        n+=Q_snprintf(book->text+n,sizeof(book->text)-(size_t)n,"%s%s: %s",n?"\n\n":"",speaker,filled);
        if(n>=(int)sizeof(book->text)-1)break;
    }
    AW_UIBookBegin();book->title_rows=1;
    p=book->text;
    while(*p && book->count<BOOK_PAGES){
        book->pages[book->count++]=(unsigned short)(p-book->text);before=p;
        for(i=0;i<page_lines(book->count-1) && *p;i++){before=p;p=AW_UILine(p,BOOK_WIDTH,line,sizeof(line));if(p==before)break;}
        if(page_lines(book->count-1)>0 && p==before && *p)break;
    }
    AW_UIBookEnd();
    if(!book->count){book->count=1;book->pages[0]=0;}
}
/* ---- the quest pages (JOURNAL-BOOK-32-QUESTS-59, aw_questbook.h) ----
 * Built when the book opens: the world change list is brought up to the scripts' live stages first (the same export
 * a save runs, aw_save.h aw_save_script_export), then world/quests.awq is read once and only the rows of started
 * quests are kept (a stage on the list, or a dated entry), with their names. A quest finished at its kept stage is
 * read from the journal index's flags (AWJ2). Freed with the book. */
static int dated_quest(const char *id){return AW_JHistHasQuest(&aw_jhist,AW_LedgerNameHash(id));}
static int quest_finished(const char *id,int32_t stage,void *ctx){
    uint32_t offset,length,flags=0;(void)ctx;
    return journal_row(id,stage,&offset,&length,&flags) && (flags&1);
}
static int book_quests(void){
    FILE *f=NULL;byte header[8],row[160];int i,j,count=0,size,kept=0,ok;aw_qb_dated_t *dated=NULL;
    if(aw_save_script_export)aw_save_script_export(&aw_ledger);
    size=COM_FOpenFile("world/quests.awq",&f);
    if(f && (size<8 || fread(header,1,8,f)!=8 || memcmp(header,"AWQ1",4) ||
             (count=(int)u32(header+4))<0 || count>AW_QB_QUESTS || size!=8+count*160))count=0;
    book->quests=(aw_qb_quest_t *)AW_TryMalloc((unsigned long)(count+aw_jhist.count+1)*sizeof(aw_qb_quest_t));
    dated=(aw_qb_dated_t *)AW_TryMalloc((unsigned long)(aw_jhist.count+1)*sizeof(aw_qb_dated_t));
    if(!book->quests || !dated){if(f)fclose(f);free(dated);return 0;}
    for(i=0;f && i<count;i++){
        if(fread(row,1,160,f)!=160 || !memchr(row,0,64) || !memchr(row+64,0,96))break;
        if(!AW_QuestBookStage(&aw_ledger,(char *)row) && !dated_quest((char *)row))continue;
        memcpy(book->quests[kept].id,row,64);memcpy(book->quests[kept].title,row+64,96);kept++;
    }
    if(f)fclose(f);
    /* the dated history (aw_jhist.h) by its quests' name hashes: the catalogue's id, else (no world/quests.awq, an
     * older image) the id the 32-slot table holds, named as before */
    {uint32_t *hash=(uint32_t *)AW_TryMalloc((unsigned long)(kept+1)*sizeof(uint32_t));int catalogued=kept;
    if(!hash){free(dated);return 0;}
    for(i=0;i<catalogued;i++)hash[i]=AW_LedgerNameHash(book->quests[i].id);
    for(j=0;j<aw_jhist.count;j++){
        const aw_jhist_entry_t *h=&aw_jhist.entry[j];int q;
        dated[j].id=NULL;
        for(i=0;i<catalogued && !dated[j].id;i++)if(hash[i]==h->quest)dated[j].id=book->quests[i].id;
        for(q=0;q<aw_state.count[AW_JOURNAL] && !dated[j].id;q++)
            if(AW_LedgerNameHash(aw_state.values[AW_JOURNAL][q].id)==h->quest)dated[j].id=aw_state.values[AW_JOURNAL][q].id;
        dated[j].stage=h->stage;dated[j].days=h->days;dated[j].milliseconds=h->milliseconds;
        if(!dated[j].id || (dated[j].id>=book->quests[0].id && dated[j].id<book->quests[catalogued].id))continue;
        for(i=catalogued;i<kept && Q_strcasecmp(book->quests[i].id,(char *)dated[j].id);i++);
        if(i<kept){dated[j].id=book->quests[i].id;continue;}
        snprintf(book->quests[kept].id,sizeof(book->quests[kept].id),"%s",dated[j].id);
        strcpy(book->quests[kept].title,book->quests[kept].id);
        for(i=0;book->quests[kept].title[i];i++)if(book->quests[kept].title[i]=='_')book->quests[kept].title[i]=' ';
        kept++;
    }
    free(hash);}
    book->nquests=kept;
    ok=AW_QuestBookBuild(&book->qb,book->quests,kept,&aw_ledger,dated,aw_jhist.count,quest_finished,NULL);
    free(dated);
    return ok;
}
/* the names listed: the active ones, or all of them ("Show all", OpenMW's journal window) */
static void book_shown(void){
    book->nshown=AW_QuestBookShown(&book->qb,book->all,book->shown,book->qb.groups);
    book->index_top=book->selection=0;
}
/* The dated journal (JOURNAL-ORIGINAL-VIEW-59): every entry's text read once here, the kept stages without a date
 * first (an older save's, no heading), then the dated ones as earned, each day under its heading; laid out with the
 * book's font. 0 out of memory. */
static int book_dated(void){
    int pass,i,ok=1;const char *t;
    for(pass=0;pass<2 && ok;pass++)
        for(i=0;i<book->qb.entries && ok;i++){
            const aw_qb_entry_t *e=&book->qb.entry[i];
            if((e->dated==AW_QB_UNDATED)!=(pass==0))continue;
            if(!entry_text(entry_id(i),e->stage,book->raw,sizeof(book->raw)))
                t="This earned entry has no matching text in the installed journal catalogue. Its quest stage and date remain saved.";
            else if(!expand_entry())t="This entry exceeds the reader's text capacity. Its saved history remains intact.";
            else t=book->text;
            ok=AW_JournalViewAdd(&book->jv,e->dated==AW_QB_UNDATED?-1:e->days,t);
        }
    AW_UIBookBegin();
    if(ok)ok=AW_JournalViewLayout(&book->jv,AW_UILine,BOOK_WIDTH,BOOK_DATED_LINES);
    AW_UIBookEnd();
    return ok;
}
/* back to the dated journal at its newest spread */
static void show_dated(void){
    book->index_mode=0;book->filter=-1;book->entry=BOOK_DATED;book->hits=0;
    book->spread=AW_JournalViewNewest(&book->jv);
}
static void open_journal(void){
    int n;
    if(!allowed())return;
    book=(book_t *)AW_TryCalloc(1,sizeof(*book));if(!book){Con_Printf("Journal reader: not enough memory.\n");return;}
    n=0;
    if(book_quests()){
        n=book->qb.groups?book->qb.groups:1;
        book->shown=(int *)AW_TryMalloc((unsigned long)n*sizeof(int));
        book->index_x=(int *)AW_TryMalloc((unsigned long)n*sizeof(int));
        book->index_y=(int *)AW_TryMalloc((unsigned long)n*sizeof(int));
        book->index_rows=(int *)AW_TryMalloc((unsigned long)n*sizeof(int));
    }
    if(!n || !book->shown || !book->index_x || !book->index_y || !book->index_rows || !book_dated()){
        Con_Printf("Journal reader: not enough memory.\n");
        book_free();return;
    }
    book_shown();show_dated();opened(2);
    Con_Printf("Journal: %ld entries (%ld dated), %ld quests started, %ld names listed; %ld pages; reader %ld bytes.\n",
        (long)book->qb.entries,(long)aw_jhist.count,(long)book->qb.started,(long)book->nshown,(long)book->jv.pages,
        (long)(sizeof(*book)+book->jv.cap+(unsigned long)book->jv.line_cap*sizeof(aw_jv_line_t)+(unsigned long)book->nquests*sizeof(aw_qb_quest_t)+
               (unsigned long)book->qb.entries*sizeof(aw_qb_entry_t)+(unsigned long)n*(4*sizeof(int)+sizeof(aw_qb_group_t))));
}
static void inventory_command(void){
    if(Cmd_Argc()==1)AW_InventoryOpen();else AW_InventoryGrantCommand();
}
void AW_WorldUIInit(void){AW_InventoryInit();Cvar_RegisterVariable(&aw_map_mode);Cvar_RegisterVariable(&aw_map_debug_available);
    Cvar_RegisterVariable(&aw_map_lava);Cvar_RegisterVariable(&aw_map_format);Cmd_AddCommand("aw_teleport_map",open_teleport_map);Cmd_AddCommand("aw_worldmap",open_normal_map);Cmd_AddCommand("aw_journal",open_journal);Cmd_AddCommand("aw_inventory",inventory_command);}
void AW_WorldUIMouse(int dx,int dy){
    int top;
    if(!modal || key_dest!=key_menu)return;
    if(modal==1 && drag){
        if(marker_click){
            marker_drag_x+=dx;marker_drag_y+=dy;
            if(marker_drag_x*marker_drag_x+marker_drag_y*marker_drag_y>9){
                map_x-=marker_drag_x*map_step;map_y-=marker_drag_y*map_step;marker_click=0;
            }
        }else{map_x-=dx*map_step;map_y-=dy*map_step;}
    }
    mouse_x=minmax(mouse_x+dx,0,319);mouse_y=minmax(mouse_y+dy,0,199);
    if(modal==3 && inventory && drag==K_MOUSE1){
        top=AW_UIScrollHit(INV_SCROLL_X+2,minmax(mouse_y,INV_LIST_Y+10,INV_LIST_Y+INV_SCROLL_H-11),
            INV_SCROLL_X,INV_LIST_Y,INV_SCROLL_H,inventory->count,INV_VISIBLE,inventory->top);
        if(top>=0)inventory_scroll(top);
    }
    if(modal==2 && book->index_mode && drag){
        top=AW_UIScrollHit(306,minmax(mouse_y,40,165),304,40,126,book->nshown,(book->index_end-book->index_top),book->index_top);
        if(top>=0){book->index_top=top;book->selection=top;AW_UIBookBegin();index_layout();AW_UIBookEnd();}
    }
}
static void flip(int direction){
    int entry;
    if(direction>0 && book->spread+2<book->count){book->spread+=2;return;}
    if(direction<0 && book->spread>0){book->spread-=2;return;}
    entry=next_entry(book->entry,direction);
    if(entry>=0){load_entry(entry);if(direction<0)book->spread=((book->count-1)/2)*2;}
}
int AW_WorldUIKey(int key,int down){
    int n;
    if(!modal)return 0;
    if(key_dest!=key_menu){close_panel();return 0;}
    if(!down){
        if(modal==1 && key==K_MOUSE1 && marker_click){
            marker_click=0;if(!teleport_mode && !teleport_button_hit())place_marker();
        }
        if((modal==1 && key==drag) || (modal==2 && (key==K_MOUSE1 || key==K_MOUSE2)) || (modal==3 && key==K_MOUSE1))drag=0;
        return 1;
    }
    if(key==K_F10 || key=='`'){close_panel();return 0;}
    /* a panel that must be finished (the level-up box, LEVEL-UP-58: the original's box has no cancel) takes Esc itself */
    if(key==K_ESCAPE && modal==4 && aw_worldui_panel_holds_escape){if(!panel_key(key,mouse_x,mouse_y))close_panel();return 1;}
    if(key==K_ESCAPE || (modal==1 && (key=='m' || key=='M')) || (modal==2 && (key=='j' || key=='J')) || (modal==3 && (key=='i' || key=='I'))){close_panel();return 1;}
    if(modal==3){inventory_key(key);return 1;}
    if(modal==4){if(!panel_key(key,mouse_x,mouse_y))close_panel();return 1;}
    if(modal==1){
        if(key!=K_MOUSE1 && key!=K_MOUSE2 && key!=K_MOUSE3)marker_click=0;
        if(key==K_MOUSE1 && !teleport_mode && mouse_y>=1 && mouse_y<16){
            marker_click=drag=teleport_selected=0;teleport_message=NULL;
            if(mouse_x>=4 && mouse_x<66 && map_debug_enabled())Cvar_SetValue(aw_map_mode.name,0);
            else if(mouse_x>=250 && mouse_x<316)Cvar_SetValue(aw_map_mode.name,1);
            return 1;
        }
        if(key==K_MWHEELUP || key=='+' || key=='='){zoom=minmax(zoom+1,0,5);map_fit();}
        if(key==K_MWHEELDOWN || key=='-'){zoom=minmax(zoom-1,0,5);map_fit();}
        if(key==K_LEFTARROW || key=='a')map_x-=24*map_step;
        if(key==K_RIGHTARROW || key=='d')map_x+=24*map_step;
        if(key==K_UPARROW || key=='w')map_y-=24*map_step;
        if(key==K_DOWNARROW || key=='s')map_y+=24*map_step;
        if(key==K_HOME)map_home();
        if(key=='p')map_player();
        if(key=='g' && !map_in_game())grid=!grid;
        if(teleport_mode){
            /* Amiga sends right as MOUSE3 and middle as MOUSE2. Keep both
             * secondary buttons usable here without changing global bindings. */
            if((key==K_MOUSE2 || key==K_MOUSE3) && mouse_x>=4 && mouse_x<316 && mouse_y>=19 && mouse_y<173)drag=key;
            if(key==K_ENTER)confirm_teleport();
            if(key==K_MOUSE1){
                if(mouse_x>=4 && mouse_x<316 && mouse_y>=19 && mouse_y<173)select_teleport_point();
                else if(teleport_button_hit())confirm_teleport();
            }
        }else{
            if(key=='c' || key=='C')clear_marker();
            if(normal_teleport_enabled()){
                if(key==K_MOUSE3 && !drag && !teleport_button_hit())select_teleport_point();
                if(key==K_ENTER)confirm_teleport();
            }
            if(key==K_MOUSE1){
                marker_click=drag=0;
                if(teleport_button_hit())confirm_teleport();
                else if(clear_button_hit())clear_marker();
                else if(mouse_x>=4 && mouse_x<316 && mouse_y>=19 && mouse_y<173){
                    drag=K_MOUSE1;marker_click=1;marker_drag_x=marker_drag_y=0;
                }else if(mouse_y>=184)close_panel();
            }
        }
    }else if(book->index_mode==2){
        if(key==K_TAB || key=='t' || key=='T' || (key==K_MOUSE1 && mouse_y>=174 && mouse_x<60)){show_dated();return 1;}
        if(key=='q' || key=='Q'){book->index_mode=1;book->selection=book->index_top=0;return 1;}
        if(key==K_UPARROW || key==K_MWHEELUP)book->topic_sel--;
        if(key==K_DOWNARROW || key==K_MWHEELDOWN)book->topic_sel++;
        if(key==K_PGUP)book->topic_sel-=22;
        if(key==K_PGDN)book->topic_sel+=22;
        if(key==K_MOUSE1 && mouse_y>=40 && mouse_y<172){
            int k=book->topic_top+(mouse_x>=170?11:0)+(mouse_y-40)/12;
            if(k<book->topics){book->topic_sel=k;key=K_ENTER;}
        }
        book->topic_sel=minmax(book->topic_sel,0,book->topics?book->topics-1:0);
        if(book->topic_sel<book->topic_top)book->topic_top=book->topic_sel;
        if(book->topic_sel>=book->topic_top+22)book->topic_top=book->topic_sel-21;
        if(key==K_ENTER && book->topics){book->index_mode=0;load_topic(book->topic_sel);}
        return 1;
    }else if(book->index_mode){
        n=book->nshown;
        AW_UIBookBegin();index_layout();AW_UIBookEnd();
        /* the view by subject: Back (Tab, Q) returns to the dated journal, T the topics */
        if(key==K_TAB || key=='q' || key=='Q' || (key==K_MOUSE1 && mouse_y>=174 && mouse_x<60)){show_dated();return 1;}
        if(key=='t' || key=='T'){book->index_mode=2;topic_list();book->topic_sel=book->topic_top=0;return 1;}
        /* "Show all" / "Show active" (OpenMW's journal window: the finished quests listed too, or not) */
        if(key=='a' || key=='A' || (key==K_MOUSE1 && mouse_y>=176 && mouse_x>=84 && mouse_x<160)){
            book->all=!book->all;book_shown();AW_UIBookBegin();index_layout();AW_UIBookEnd();return 1;
        }
        if(key==K_UPARROW || key==K_MWHEELUP)book->selection--;
        if(key==K_DOWNARROW || key==K_MWHEELDOWN)book->selection++;
        if(key==K_PGUP)book->selection-=(book->index_end-book->index_top);
        if(key==K_PGDN)book->selection+=(book->index_end-book->index_top);
        if(key==K_HOME)book->selection=0;
        if(key==K_END)book->selection=n-1;
        if(key==K_MOUSE1 && mouse_x>=304 && mouse_y>=40 && mouse_y<166){
            drag=1;AW_WorldUIMouse(0,0);return 1;
        }
        if(key==K_MOUSE1 && mouse_y>=40 && mouse_y<166){
            if(!((mouse_x>=14 && mouse_x<146) || (mouse_x>=170 && mouse_x<302)))return 1;
            for(n=book->index_top;n<book->index_end;n++)
                if(mouse_x>=book->index_x[n] && mouse_x<book->index_x[n]+BOOK_WIDTH &&
                   mouse_y>=book->index_y[n] && mouse_y<book->index_y[n]+book->index_rows[n]*14)break;
            if(n==book->index_end)return 1;
            book->selection=n;n=book->nshown;key=K_ENTER;
        }
        book->selection=minmax(book->selection,0,n?n-1:0);
        if(book->selection<book->index_top)book->index_top=book->selection;
        AW_UIBookBegin();index_layout();
        while(book->selection>=book->index_end && book->index_top<book->selection){book->index_top++;index_layout();}
        AW_UIBookEnd();
        if(key==K_ENTER && n){book->filter=book->shown[book->selection];book->index_mode=0;load_entry(next_entry(book->qb.entries,-1));}
        if(key==K_MOUSE1 && mouse_y>=174 && mouse_x>=170){book->index_mode=0;book->filter=-1;load_entry(book->qb.entries-1);}
    }else if(book->entry==BOOK_DATED){
        /* the original journal: Prev / Topics / Quests (the view by subject) / Close / Next */
        if(key==K_MOUSE1 && mouse_y>=174 && mouse_y<190){
            if(mouse_x>=14 && mouse_x<50)key=K_LEFTARROW;
            else if(mouse_x>=60 && mouse_x<100)key='t';
            else if(mouse_x>=104 && mouse_x<146)key='q';
            else if(mouse_x>=196 && mouse_x<232){close_panel();return 1;}
            else if(mouse_x>=270 && mouse_x<302)key=K_RIGHTARROW;
        }
        if(key=='q' || key=='Q' || key==K_TAB){book->index_mode=1;book->selection=book->index_top=0;return 1;}
        if(key=='t' || key=='T'){book->index_mode=2;topic_list();book->topic_sel=book->topic_top=0;return 1;}
        if((key==K_LEFTARROW || key==K_PGUP || key==K_MWHEELUP) && book->spread>=2)book->spread-=2;
        if((key==K_RIGHTARROW || key==K_PGDN || key==K_MWHEELDOWN || key==K_SPACE) && book->spread+2<book->jv.pages)book->spread+=2;
        if(key==K_HOME)book->spread=0;
        if(key==K_END)book->spread=AW_JournalViewNewest(&book->jv);
    }else{
        if(key==K_TAB){
            if(book->entry==-2){book->index_mode=2;return 1;}   /* a topic page: back to the topics */
            book->index_mode=1;book->selection=book->index_top=0;return 1;
        }
        if(key==K_BACKSPACE || key=='q' || key=='Q'){show_dated();return 1;}
        if(key==K_MOUSE1 && book->entry==-2){   /* a link on a topic page opens that topic's page */
            int h,row;
            for(h=0;h<book->hits;h++)
                if(mouse_x>=book->hit[h].x && mouse_x<book->hit[h].x+book->hit[h].w && mouse_y>=book->hit[h].y && mouse_y<book->hit[h].y+14 &&
                   book->hit[h].link<book->links && (row=topic_row(book->link_topic[book->hit[h].link]))>=0){
                    book->hits=0;load_topic(row);return 1;
                }
        }
        if(key==K_MOUSE1){
            if(mouse_y>=26 && mouse_y<26+book->title_rows*14 && mouse_x>=14 && mouse_x<146 && book->entry>=0 &&
               book->qb.entry[book->entry].group>=0){
                book->filter=book->qb.entry[book->entry].group;load_entry(next_entry(book->qb.entries,-1));return 1;
            }
            if(mouse_y>=174 && mouse_y<188){
                if(mouse_x>=14 && mouse_x<90)key=K_LEFTARROW;
                else if(mouse_x>=230 && mouse_x<302)key=K_RIGHTARROW;
                else if(mouse_x>=102 && mouse_x<146){book->index_mode=1;return 1;}
            }
        }
        if(key==K_LEFTARROW || key==K_PGUP || key==K_MWHEELUP)flip(-1);
        if(key==K_RIGHTARROW || key==K_PGDN || key==K_MWHEELDOWN || key==K_SPACE)flip(1);
        if(key==K_HOME)load_entry(next_entry(-1,1));
        if(key==K_END)load_entry(next_entry(book->qb.entries,-1));
    }
    return 1;
}
static void map_line(int x0,int y0,int x1,int y1,int color){
    int dx=abs(x1-x0),sx=x0<x1?1:-1,dy=-abs(y1-y0),sy=y0<y1?1:-1,error=dx+dy,e2;
    for(;;){AW_UIFill(x0,y0,1,1,color);if(x0==x1 && y0==y1)break;e2=2*error;if(e2>=dy){error+=dy;x0+=sx;}if(e2<=dx){error+=dx;y0+=sy;}}
}
static void map_mode_button(int x,int width,const char *label,int active,int enabled){
    int fill=active?AW_UIColor(248,225,136):(enabled?AW_UIColor(35,43,47):AW_UIColor(24,28,30));
    AW_UIFill(x,1,width,14,fill);
    /* Keep light console glyphs on a dark interior; highlight with a border. */
    if(active)AW_UIFill(x+1,2,width-2,12,AW_UIColor(35,43,47));
    text(x+3,4,label,x+width-2);
}
static void teleport_button_draw(int gold){
    int y=teleport_button_y();
    AW_UIFill(TELEPORT_X,y,TELEPORT_W,TELEPORT_H,gold);
    AW_UIFill(TELEPORT_X+1,y+1,TELEPORT_W-2,TELEPORT_H-2,AW_UIColor(29,23,17));
    text(TELEPORT_X+(TELEPORT_W-8*AW_ConsoleCharWidth())/2,y+4,"TELEPORT",TELEPORT_X+TELEPORT_W-1);
}
/* v2 lava layer: each pool's outline (at most 16 points, inside the pool) is filled
 * where a pixel centre lies inside it; a pool too small to cover a pixel centre marks
 * the one pixel holding its centre. Rejected by its bounds first; drawn only while the
 * map is open, straight into the frame like the terrain pixels. */
static int lava_visible(void){return lava_count>0 && aw_map_lava.value!=0 && aw_map_format.value>=2;}
static void lava_draw(float left,float top){
    int i,j,n,k,r,r0,r1,c,c0,c1,painted,mx,my;const byte *q,*pt=lava_points;byte *dst;
    float kx=map_w/((float)(map_bounds[2]-map_bounds[0])*map_step),ky=map_h/((float)(map_bounds[3]-map_bounds[1])*map_step);
    float ox=4-left/map_step-map_bounds[0]*kx,oy=19-top/map_step+map_bounds[3]*ky;
    float sx[LAVA_POINTS],sy[LAVA_POINTS],x0,x1,y0,y1,yc,xl,xr,xi,ax,ay,bx,by,cx,cy;
    lava_painted=0;
    for(i=0;i<lava_count;i++,pt+=n*8){
        q=lava_pools+i*24;n=q[4]|(q[5]<<8);
        x0=(int32_t)u32(q+8)*kx+ox;x1=(int32_t)u32(q+16)*kx+ox;
        y0=oy-(int32_t)u32(q+20)*ky;y1=oy-(int32_t)u32(q+12)*ky;
        if(x1<4 || x0>=316 || y1<19 || y0>=173)continue;
        cx=cy=0;
        for(j=0;j<n;j++){sx[j]=(int32_t)u32(pt+j*8)*kx+ox;sy[j]=oy-(int32_t)u32(pt+j*8+4)*ky;cx+=sx[j];cy+=sy[j];}
        painted=0;
        if(n>=3){
            r0=(int)ceil(y0-.5f);r1=(int)floor(y1-.5f);if(r0<19)r0=19;if(r1>172)r1=172;
            for(r=r0;r<=r1;r++){
                yc=r+.5f;xl=1e9f;xr=-1e9f;
                for(j=0,k=n-1;j<n;k=j++){
                    ax=sx[k];ay=sy[k];bx=sx[j];by=sy[j];
                    if((ay<=yc && yc<by) || (by<=yc && yc<ay)){
                        xi=ax+(yc-ay)*(bx-ax)/(by-ay);if(xi<xl)xl=xi;if(xi>xr)xr=xi;
                    }
                }
                if(xl>xr)continue;
                c0=(int)ceil(xl-.5f);c1=(int)floor(xr-.5f);if(c0<4)c0=4;if(c1>315)c1=315;
                if(c0>c1)continue;
                dst=vid.buffer+r*vid.rowbytes;for(c=c0;c<=c1;c++)dst[c]=(byte)lava_colour;
                painted+=c1-c0+1;
            }
        }
        if(!painted){
            mx=(int)floor(cx/n);my=(int)floor(cy/n);
            if(mx>=4 && mx<316 && my>=19 && my<173){vid.buffer[my*vid.rowbytes+mx]=(byte)lava_colour;painted=1;}
        }
        lava_painted+=painted;
    }
}
/* UI-MAP-PLAYER-ARROW-51 (the maintainer, 25 October 2026: the map's player marker as the original's arrow that
 * turns with the player, "USE THE ARROW BITMAP AS A SOURCE FROM THE ORIGINAL MORROWIND FILES"): the arrow of
 * textures/compass.dds (aw_ui.c AW_UIMapArrow, 16x16, 255 clear) centred at CX,CY, pointing along YAW (Quake degrees:
 * 0 east, 90 north = up on the map), turned by the nearest source pixel (no new colours), clipped to the map view
 * (x 4..315, y 19..172). 0 when the image has no arrow: the old marker is drawn. */
static int map_arrow(int cx,int cy,float yaw){
    const byte *a=AW_UIMapArrow();int x,y,sx,sy;float c,s,u,v,turn;byte p;
    if(!a)return 0;
    turn=(90.0f-yaw)*(3.14159265f/180.0f);   /* clockwise from up */
    c=Q_CosRad(turn);s=Q_SinRad(turn);
    for(y=-12;y<=12;y++){
        if(cy+y<19 || cy+y>=173)continue;
        for(x=-12;x<=12;x++){
            if(cx+x<4 || cx+x>=316)continue;
            /* the screen pixel turned back onto the arrow (y down: a clockwise turn) */
            u=x*c+y*s;v=y*c-x*s;
            sx=(int)floor(u+8.0f);sy=(int)floor(v+8.0f);
            if(sx<0 || sy<0 || sx>=16 || sy>=16 || (p=a[sy*64+sx])==255)continue;
            vid.buffer[(cy+y)*vid.rowbytes+cx+x]=p;
        }
    }
    return 1;
}
static void map_draw(void){
    int x,y,sx,sy,cols[312],ocean=map_ocean,gold=AW_UIColor(248,225,136),i,mx,my,in_game=map_in_game();
    float left=map_x-156*map_step,top=map_y-77*map_step,px,py,angle,dx,dy;byte *dst;char line[96];
    const char *region;float source[3];int width,limit;
    update_player();
    AW_UIFill(0,0,320,200,AW_UIColor(15,20,23));
    for(x=0;x<312;x++)cols[x]=(int)floor(left+x*map_step);
    for(y=0;y<154;y++){
        sy=(int)floor(top+y*map_step);dst=vid.buffer+(y+19)*vid.rowbytes+4;
        for(x=0;x<312;x++){sx=cols[x];dst[x]=(sx>=0 && sx<map_w && sy>=0 && sy<map_h)?map_pixels[sy*map_w+sx]:ocean;}
    }
    if(lava_visible())lava_draw(left,top);
    if(grid && !in_game){
        for(i=map_bounds[0]/8192;i<=map_bounds[2]/8192;i++){
            px=(i*8192.0f-map_bounds[0])*map_w/(map_bounds[2]-map_bounds[0]);mx=4+(int)((px-left)/map_step);
            if(mx>=4 && mx<316)for(y=19;y<173;y+=4)AW_UIFill(mx,y,1,1,gold);
        }
        for(i=map_bounds[1]/8192;i<=map_bounds[3]/8192;i++){
            py=(map_bounds[3]-i*8192.0f)*map_h/(map_bounds[3]-map_bounds[1]);my=19+(int)((py-top)/map_step);
            if(my>=19 && my<173)for(x=4;x<316;x+=4)AW_UIFill(x,my,1,1,gold);
        }
    }
    if(lava_visible()){
        /* Legend in the map's lower left corner, in both views. */
        width=AW_ConsoleCharWidth();
        AW_UIFill(5,161,15+4*width,11,AW_UIColor(15,20,23));AW_UIFill(7,163,7,7,lava_colour);text(16,163,"LAVA",17+4*width);
    }
    /* Settlement landmarks are shared by both views; only diagnostics differ. */
    for(i=0;i<area_count;i++){
        px=(areas[i].x-map_bounds[0])*map_w/(map_bounds[2]-map_bounds[0]);py=(map_bounds[3]-areas[i].y)*map_h/(map_bounds[3]-map_bounds[1]);
        mx=4+(int)((px-left)/map_step);my=19+(int)((py-top)/map_step);
        if(mx>=6 && mx<313 && my>=22 && my<161){AW_UIFill(mx-1,my-1,3,3,gold);text(mx+4,my,areas[i].title,314);}
    }
    if(marker){
        px=(player_x-map_bounds[0])*map_w/(map_bounds[2]-map_bounds[0]);py=(map_bounds[3]-player_y)*map_h/(map_bounds[3]-map_bounds[1]);
        mx=4+(int)((px-left)/map_step);my=19+(int)((py-top)/map_step);
        if(mx>=9 && mx<311 && my>=24 && my<168){
            /* UI-MAP-PLAYER-ARROW-51: the original game's arrow, turned with the view, in both maps */
            if(map_arrow(mx,my,cl.viewangles[YAW])){}
            else if(in_game){edict_t *e=svs.clients[0].edict;angle=e->v.angles[1]*(3.14159265f/180.0f);dx=Q_CosRad(angle);dy=-Q_SinRad(angle);
                map_line(mx,my,mx+(int)(dx*7),my+(int)(dy*7),AW_UIColor(255,255,255));
                map_line(mx+(int)(dx*7),my+(int)(dy*7),mx+(int)(dx*4-dy*2),my+(int)(dy*4+dx*2),AW_UIColor(255,255,255));
                map_line(mx+(int)(dx*7),my+(int)(dy*7),mx+(int)(dx*4+dy*2),my+(int)(dy*4-dx*2),AW_UIColor(255,255,255));
            }else{AW_UIFill(mx-4,my,9,1,AW_UIColor(255,255,255));AW_UIFill(mx,my-4,1,9,AW_UIColor(255,255,255));}
        }
        if(in_game)strcpy(line,"Terrain overview prototype");
        else sprintf(line,"Cell %ld,%ld XYZ %ld %ld %ld",(long)floor(player_x/8192),(long)floor(player_y/8192),
            (long)player_x,(long)player_y,(long)player_z);
    }else strcpy(line,in_game?"No exterior position fix":"Interior: no exterior position fix");
    if(custom_marker(source)){
        int cyan=AW_UIColor(48,240,240),ox,oy;
        px=(source[0]-map_bounds[0])*map_w/(map_bounds[2]-map_bounds[0]);
        py=(map_bounds[3]-source[1])*map_h/(map_bounds[3]-map_bounds[1]);
        mx=4+(int)((px-left)/map_step);my=19+(int)((py-top)/map_step);
        /* A clipped cyan diamond remains distinct from the red teleport cross. */
        for(oy=-4;oy<=4;oy++)for(ox=-4;ox<=4;ox++)if(abs(ox)+abs(oy)==4 || (!ox && !oy))
            if(mx+ox>=4 && mx+ox<316 && my+oy>=19 && my+oy<173)AW_UIFill(mx+ox,my+oy,1,1,cyan);
    }
    if(teleport_selected && (teleport_mode || normal_teleport_enabled())){
        px=(teleport_point[0]-map_bounds[0])*map_w/(map_bounds[2]-map_bounds[0]);
        py=(map_bounds[3]-teleport_point[1])*map_h/(map_bounds[3]-map_bounds[1]);
        mx=4+(int)((px-left)/map_step);my=19+(int)((py-top)/map_step);
        for(i=-5;i<=5;i++){
            if(mx+i>=4 && mx+i<316 && my>=19 && my<173)AW_UIFill(mx+i,my,1,1,AW_UIColor(255,32,32));
            if(mx>=4 && mx<316 && my+i>=19 && my+i<173)AW_UIFill(mx,my+i,1,1,AW_UIColor(255,32,32));
        }
    }
    if(teleport_mode){
        text(8,1,"DEBUG TELEPORT",315);
        text(8,10,"CLICK ON TARGET TO TELEPORT",315);
        if(teleport_selected){
            sprintf(line,"XY %ld %ld / %s",(long)teleport_point[0],(long)teleport_point[1],teleport_region);
            text(8,176,teleport_message?teleport_message:line,315);
            teleport_button_draw(gold);
        }else if(teleport_message)text(8,176,teleport_message,315);
        text(8,188,"R-drag/arrows pan +/- zoom Esc close",240);
    }else{
        if(in_game){text(77,5,"IN-GAME MAP PROTOTYPE",315);
            text(8,188,"Pan/zoom  P player  M/Esc close",315);}
        else{text(77,5,"DEBUG MAP",315);text(116,5,line,315);}
        map_mode_button(4,62,"DEBUG",!in_game,map_debug_enabled());
        map_mode_button(250,66,"IN-GAME",in_game,1);
        if(!in_game){
            width=AW_ConsoleCharWidth();
            text(8,188,width<=4?"Home fit M/Esc close":"P/G/Home",88);
            /* The player's original CELL determines the region, never map pan or
             * the pointer. Interiors have no exterior coordinate fix. */
            source[0]=player_x;source[1]=player_y;source[2]=player_z;
            region=marker?AW_RegionNameAt(source):NULL;
            snprintf(line,sizeof(line),"REGION: %s",region?region:"unavailable");
            limit=(315-96)/width;
            if((int)strlen(line)>limit){line[limit]=0;memcpy(line+limit-3,"...",3);}
            text(315-(int)strlen(line)*width,188,line,315);
        }
        text(8,176,marker_message?marker_message:
            (normal_teleport_enabled() && teleport_message?teleport_message:
             AW_ConsoleCharWidth()<=4?(normal_teleport_enabled()?"Click mark / R-click target / drag pan / +/- zoom":"Click mark / drag pan / +/- zoom / P player"):
             (normal_teleport_enabled()?"L mark / drag / R target":"Click mark / drag pan / +/-")),240);
        AW_UIFill(CLEAR_X,CLEAR_Y,CLEAR_W,CLEAR_H,AW_UIColor(35,43,47));
        text(CLEAR_X+4,CLEAR_Y+1,"C CLEAR",CLEAR_X+CLEAR_W-1);
        if(normal_teleport_enabled() && teleport_selected)teleport_button_draw(gold);
    }
}
static void journal_draw(void){
    int i,j,x,y,entry=book->entry,page,ink=AW_UIColor(38,29,20),gold=AW_UIColor(103,65,27);
    char line[160];const char *p;const aw_qb_entry_t *e;
    AW_UIFill(0,0,320,200,AW_UIColor(29,23,17));
    AW_UIFill(5,5,153,190,AW_UIColor(223,207,166));AW_UIFill(162,5,153,190,AW_UIColor(232,217,180));
    AW_UIFill(158,5,4,190,AW_UIColor(92,70,43));
    AW_UIBookBegin();
    if(!book->index_mode && entry==BOOK_DATED){
        /* the original journal: two facing pages of dated entries, the day headings in the heading colour */
        const aw_journalview_t *v=&book->jv;int first,last,row;
        for(j=0;j<2;j++){
            page=book->spread+j;if(page>=v->pages)continue;
            first=v->page[page];last=page+1<v->pages?v->page[page+1]:v->lines;
            for(i=first,row=0;i<last && row<BOOK_DATED_LINES;i++,row++){
                int n=v->line[i].len<(int)sizeof(line)-1?v->line[i].len:(int)sizeof(line)-1;
                if(v->line[i].blank || !n)continue;
                memcpy(line,v->text+v->line[i].start,(size_t)n);line[n]=0;
                AW_UIText(14+j*156,12+row*14,line,v->line[i].heading?gold:ink);
            }
        }
        if(!v->lines)AW_UITextBox(14,26,BOOK_WIDTH,14,"No entries yet.",ink);
        if(book->spread>0)AW_UIText(14,176,"Prev",gold);
        AW_UIText(60,176,"Topics",gold);AW_UIText(104,176,"Quests",gold);AW_UIText(196,176,"Close",gold);
        if(book->spread+2<v->pages)AW_UIText(270,176,"Next",gold);
    }else if(book->index_mode==2){
        AW_UITextBox(14,12,BOOK_WIDTH,14,"Topics",ink);
        for(j=0;j<22 && book->topic_top+j<book->topics;j++){
            i=book->topic_top+j;x=j<11?14:170;y=40+(j%11)*12;
            if(i==book->topic_sel)AW_UIFill(x-4,y,140,12,AW_UIColor(203,186,145));
            AW_UITextBox(x,y,BOOK_WIDTH,12,book->topic_name[i],gold);
        }
        if(!book->topics)AW_UITextBox(14,42,BOOK_WIDTH,14,"No topics yet.",ink);
        AW_UIText(14,176,"Back",gold);
    }else if(book->index_mode){
        AW_UITextBox(14,12,BOOK_WIDTH,14,"Quests",ink);
        AW_UITextBox(170,12,BOOK_WIDTH,14,"By subject",ink);
        index_layout();
        for(j=book->index_top;j<book->index_end;j++){
            x=book->index_x[j];y=book->index_y[j];
            if(j==book->selection)AW_UIFill(x-4,y,140,book->index_rows[j]*14,AW_UIColor(203,186,145));
            p=shown_title(j);
            for(i=0;i<book->index_rows[j];i++){
                p=AW_UILine(p,BOOK_WIDTH,line,sizeof(line));
                AW_UITextBox(x,y+i*14,BOOK_WIDTH,14,line,book->qb.group[book->shown[j]].finished?ink:gold);
            }
        }
        AW_UIScrollbar(304,40,126,book->nshown,(book->index_end-book->index_top),book->index_top);
        if(!book->nshown)AW_UITextBox(14,42,BOOK_WIDTH,14,book->qb.groups?"No active quests.":"No quests yet.",ink);
        AW_UIText(14,176,"Back",gold);
        AW_UIText(84,176,book->all?"Show active":"Show all",gold);
        AW_UITextBox(170,176,BOOK_WIDTH,12,"All entries",gold);
    }else{
        if(entry>=0){
            e=&book->qb.entry[entry];
            /* a kept stage without a date shows none; the date in the original's form (AW_JournalDate) */
            if(e->dated>=0 && AW_JournalDate(e->days,line,sizeof(line)))AW_UIText(14,10,line,ink);
            AW_UITextBox(170,10,132,14,"Journal",ink);
            p=entry_title(entry);
            for(i=0;i<book->title_rows;i++){
                p=AW_UILine(p,BOOK_WIDTH,line,sizeof(line));
                AW_UITextBox(14,26+i*14,BOOK_WIDTH,14,line,gold);
            }
        }else if(entry==-2 && book->topic_open>=0 && book->topic_open<book->topics){
            AW_UIText(14,12,book->topic_name[book->topic_open],gold);
        }else AW_UIText(14,12,"Journal",ink);
        book->hits=0;
        for(j=0;j<2;j++){
            page=book->spread+j;if(page>=book->count)continue;p=book->text+book->pages[page];
            y=44+(j?0:(book->title_rows-1)*14);
            if(entry==-2){   /* a topic page: its links (the marks before this page say where the count stands) */
                int opens=0,inside=0;const char *q;
                for(q=book->text;q<p;q++){if(*q==2){opens++;inside=1;}else if(*q==3)inside=0;}
                for(i=0;i<page_lines(page) && *p;i++){
                    p=AW_UILine(p,BOOK_WIDTH,line,sizeof(line));
                    linked_line(14+j*156,y+i*14,line,&opens,&inside,ink,AW_UIColor(112,126,207));
                }
            }else for(i=0;i<page_lines(page) && *p;i++){p=AW_UILine(p,BOOK_WIDTH,line,sizeof(line));AW_UIText(14+j*156,y+i*14,line,ink);}
        }
        AW_UIText(14,176,"< Previous",gold);AW_UIText(239,176,"Next >",gold);
        AW_UITextBox(102,174,44,14,"Quests",gold);
    }
    AW_UIBookEnd();
    if(!book->index_mode && entry==BOOK_DATED)
        sprintf(line,"Page %ld/%ld  Q quests T topics J close",(long)(book->jv.pages?book->spread+1:0),(long)book->jv.pages);
    else if(book->index_mode==2)strcpy(line,"T/Tab journal  Q quests  J close");
    else if(book->index_mode)strcpy(line,"Q/Tab journal  T topics  J close");
    else sprintf(line,"%ld/%ld  Tab list Q journal J close",(long)(entry+1),(long)book->qb.entries);
    AW_UIFill(5,188,310,12,AW_UIColor(29,23,17));
    text(8,190,line,314);
}
int AW_WorldUIDraw(void){
    if(!modal)return 0;
    if(!sv.active || strcmp(opened_scene,sv.name) || key_dest!=key_menu){close_panel();return 0;}
    if(modal==1){
        /* Bounded ocean margin also keeps float-to-pixel casts in range. */
        if(map_x<-map_w)map_x=-map_w;
        if(map_x>2*map_w)map_x=2*map_w;
        if(map_y<-map_h)map_y=-map_h;
        if(map_y>2*map_h)map_y=2*map_h;
        map_draw();
    }else if(modal==3)inventory_draw();else if(modal==4)panel_draw();else journal_draw();cursor();scr_copyeverything=1;return 1;
}
