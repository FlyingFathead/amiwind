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
#include "aw_listnav.h"
#include "aw_actorstate.h"
#include "aw_mapfog.h"
#include "aw_links.h"
#include "aw_mapmarks.h"
#include "aw_listbox.h"
#include "aw_msgbox.h"
#include "aw_iteminfo.h"
#include "aw_layout.h"
#include <stdint.h>
#include <ctype.h>
static void mm_close_all(void);   /* the map markers' boxes and menu (MAP-MULTI-MARKERS-66) */
static void mm_max(void);
static void mm_migrate(void);
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
/* The old single marker (MAP-MARKER-29): read once into the marker list (aw_mapmarks.c, mm_migrate), then cleared. */
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
/* the armour rating's line under the picture (INVENTORY-NO-ARMOR-RATING-61: OpenMW openmw_inventory_window.layout puts
 * ArmorRating at the bottom of the Avatar box, under the AvatarImage) */
#define INV_PREVIEW_H 150
#define INV_ARMOR_Y 186
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
    /* INVENTORY-PREVIEW-STALE-61: preview_have = the kept picture is valid (shown while a new outfit's parts load);
     * preview_wait = when the wait for those parts began (while preview_waiting) */
    int preview_have,preview_waiting;double preview_wait;
    unsigned preview_frames;double preview_seconds,preview_render_seconds;
    /* INVENTORY-NO-ARMOR-RATING-61: the armour rating shown, worked out when the window opens and after each action
     * (armor_state 0 = work it out at the next draw, 1 = armor holds it, -1 = unavailable) */
    int armor_state,armor;
    /* INVENTORY-OPEN-WINDOW-NO-REFRESH-61: what the window last showed of the worn set and the carried kinds; a change
     * made outside the window (the console, a script, a trade, a pick-up) redraws it at the next frame */
    char seen_worn[AW_INVENTORY_SLOTS][64];
    uint32_t seen_kinds,seen_kinds_sum;
    /* INVENTORY-DOUBLECLICK-62: the last click on a row (for the double-click), the consumable's confirmation box
     * (its item copied when it opens, the count 1..confirm_max, fresh until the first digit, the slider held), and the
     * short "Equipped <name>" notice box until notice_until */
    int click_row;double click_time;
    int confirm,confirm_count,confirm_max,confirm_fresh,confirm_drag;aw_inventory_item_t confirm_item;
    char notice[96];double notice_until;
    /* INVENTORY-EQUIP-HINTS-67: MESSAGE (an action's result) is shown for the row it was said for (message_row; -1 any
     * row) until message_until; then the row's own hint is back. Before, the message stayed for every row until the
     * next action, so after one Equip no other item showed its key hint. */
    double message_until;int message_row;
    /* INVENTORY-ITEM-INFO-67: the item information box over the window (aw_iteminfo.c), NULL while closed */
    aw_iteminfo_t *info;
    byte preview[INV_PREVIEW_W*INV_PREVIEW_H];
} inventory_panel_t;
#define INV_CONFIRM_X 140
#define INV_CONFIRM_Y 62
#define INV_CONFIRM_W 168
#define INV_CONFIRM_H 82
#define INV_CONFIRM_RAIL_X (INV_CONFIRM_X+10)
#define INV_CONFIRM_RAIL_W (INV_CONFIRM_W-20)
#define INV_CONFIRM_RAIL_Y (INV_CONFIRM_Y+40)
#define INV_CONFIRM_BUTTON_Y (INV_CONFIRM_Y+INV_CONFIRM_H-20)
#define INV_CONFIRM_BUTTON_W 52
#define INV_CONFIRM_OK_X (INV_CONFIRM_X+20)
#define INV_CONFIRM_CANCEL_X (INV_CONFIRM_X+INV_CONFIRM_W-20-INV_CONFIRM_BUTTON_W)
#define INV_NOTICE_SECONDS 3.0
/* INVENTORY-EQUIPPED-LABEL-67: the "Equipped" mark at the end of a worn item's row (8 glyphs and a gap), in the
 * highlight colour */
#define INV_EQUIPPED_W 36
#define INV_EQUIPPED_COLOUR AW_UIColor(150,220,120)
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
/* MAP-WORLD-TAB-BLANK-67: 1 once the in-game World view has been placed on the player in this game (map_world_place);
 * 0 again on New Game and after a load (mm_reset, mm_loaded) */
static int map_world_placed;
static cvar_t aw_map_mode={"aw_map_mode","0",true}; /* 0=Debug, 1=In-Game */
static cvar_t aw_map_debug_available={"aw_map_debug_available","1",true};
/* MAP-VERSION-2-DEFAULT-68 (the maintainer, 20 November 2026: map version 2 is the default, the map before it stays as
 * version 1 with dbg dbgmap and dbg maptype): aw_map_version 2 (the default, saved) is the original's map in the frame
 * of the attributes, inventory and magic views, the place's name in its title, no debug buttons, no lava colour; 1 is
 * the map before it (its Debug and In-Game views, buttons and lava legend). Read when the map opens (map_v2); the
 * debug teleport map (dbg tp map) is always the version 1 screen. VIEW_*: the map picture on the screen for the version
 * open (version 1: 4,19 312 x 154, as before). */
static cvar_t aw_map_version={"aw_map_version","2",true};
static int map_v2,teleport_opening,view_x=4,view_y=19,view_w=312,view_h=154;
#define VIEW_MAX_W 312
/* version 2's layout, the shared menu layout's places (aw_statswin.c window_frame, aw_worldui.c inventory_draw): the
 * window box and its title bar, the map's box (its picture 304 x 142 inside the 4-pixel frame) and the footer's box
 * (two lines of console glyphs: the close keys, a hint and the World / Local / Markers tabs in the inventory's tab
 * style; then the zoom and pan keys) */
#define MAPV2_MAP_BOX_Y 18
#define MAPV2_MAP_BOX_H 150
#define MAPV2_FOOT_BOX_Y 170
#define MAPV2_FOOT_BOX_H 26
#define MAPV2_FOOT_Y 176      /* the footer's first line: the close keys, a hint or message, the tabs */
#define MAPV2_FOOT_Y2 184     /* its second: zoom and pan (the maintainer, 22 November 2026: the zoom keys said) */
#define MAPV2_CLOSE_X 10
#define MAPV2_HINT_END 212
/* the close key's words as drawn ("M/Esc close": the key bound to the map's command, else "Esc close"), their width */
static int mapv2_close_w=36;
static const struct {const char *label;int x,w;} mapv2_tabs[3]={{"World",216,24},{"Local",242,24},{"K markers",268,40}};
/* the title: the original's name of the cell the player is in, worked out when the map opens, and its font */
static char map_name[64];static aw_layout_title_t map_name_fit;
/* v2 map layers: lava pools on by default; aw_map_format 1 draws a v2 file as v1. */
static cvar_t aw_map_lava={"aw_map_lava","1",true};
static cvar_t aw_map_format={"aw_map_format","2",true};
static const byte *lava_pools,*lava_points;
static int lava_count,lava_colour,lava_painted;
static float teleport_point[3];
static const char *teleport_message;
static char teleport_region[64];
/* MAP-ORIGINAL-POI-66: the original's place markers (OpenMW MapWindow: a square per named exterior cell, its cells
 * grouped by the name before the first comma, placed at their average, named on mouse-over). Read from
 * world/region-names.awn (the cells' original names) when the map opens, freed when it closes; known = entered by
 * the player or revealed by ShowMap (aw_actorstate.c, saved); the debug view shows them all. */
#define MAP_PLACES_MAX 128
typedef struct {char name[32];float x,y;int cells,known;} map_place_t;
static map_place_t *map_places;static int map_place_count,map_place_hover=-1;
/* Stage 2: the explored land (aw_mapfog.c) as one bit per fog square (1024 source units) over the map's bounds, built
 * when the map opens from the explored cells' rows and freed on close; the in-game view hides the rest. */
static byte *fog_mask;static int fog_gx0,fog_gy0,fog_w,fog_h;
/* MAP-WORLD-TAB-BLANK-67: the explored squares' bounds in the mask (fog_x1 < fog_x0: nothing explored) */
static int fog_x0,fog_y0,fog_x1=-1,fog_y1=-1;
static const char *map_hover_name;
/* Stage 3, the local map (local_build): local_room = the plan of the loaded room is in local_pixels */
static int map_local,map_local_choice,local_room;
static byte *local_pixels;static float local_min[2],local_max[2],local_scale,local_ox,local_oy;
static char local_name[16];
static void local_free(void){free(local_pixels);local_pixels=NULL;local_room=0;}
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
void (*aw_worldui_panel_drag)(int mouse_x,int mouse_y);   /* set by the opener; called while the left button is held */
static void close_panel(void){
    aw_worldui_panel_holds_escape=0;aw_worldui_panel_drag=NULL;
    if(modal==4 && panel_closed)panel_closed();
    panel_draw=NULL;panel_key=NULL;panel_closed=NULL;
    if(inventory && inventory->preview_frames)
        Con_Printf("Inventory preview (%s): %d renders, last %d ms; %u frames, %d us per frame; picture %d bytes kept, pose model freed after each render.\n",
            AW_ViewInventoryLive()?"live":"still",inventory->preview_renders,(int)(inventory->preview_render_seconds*1000),
            inventory->preview_frames,(int)(inventory->preview_seconds*1e6/inventory->preview_frames),INV_PREVIEW_W*INV_PREVIEW_H);
    if(inventory){free(inventory->keys);free(inventory->rows);AW_ItemInfoClose(inventory->info);}
    free(inventory);inventory=NULL;AW_InventoryPreviewClear();
    free(map_data);map_data=map_pixels=NULL;lava_pools=lava_points=NULL;lava_count=0;
    free(map_places);map_places=NULL;map_place_count=0;map_place_hover=-1;
    free(fog_mask);fog_mask=NULL;local_free();map_local=0;mm_close_all();
    book_free();
    if(modal && key_dest==key_menu)key_dest=key_game;
    modal=drag=marker_click=teleport_mode=teleport_selected=0;teleport_message=marker_message=NULL;IN_AWClearButtons();
}
int AW_WorldUIActive(void){return modal!=0;}
/* ALCHEMY-61: the open window closed from a command (aw_inventory alchemy close), as Esc closes it */
void AW_WorldUIClose(void){if(modal)close_panel();}
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
/* MAP-MENU-BLOCKED-COURTYARD-65: a window the opening's scripts switched on (EnableMapMenu, EnableStatsMenu,
 * EnableMagicMenu: CharGenFatigueBarrel, the census office) opens while the opening still restricts the rest, as the
 * inventory does (aw_story.c AW_StoryInventoryAllowed); before, M stayed shut after "You now have a map menu". */
/* WEREWOLF-BODY-63 (v0.0.68, aw_inventory.h): the player is a werewolf: the inventory and magic windows stay shut */
int (*aw_worldui_werewolf)(void);
static int werewolf_now(void){return aw_worldui_werewolf && aw_worldui_werewolf();}
static int menu_allowed(int menu){
    if(menu==AW_MENU_MAGIC && werewolf_now())return 0;
    return allowed_in_play() && (!AW_StoryRestricted() || (AW_StoryMenus()&menu));
}
static void opened(int kind){
    strncpy(opened_scene,sv.name,sizeof(opened_scene)-1);opened_scene[sizeof(opened_scene)-1]=0;
    modal=kind;key_dest=key_menu;IN_AWClearButtons();
}
int AW_WorldUIOpenPanel(void (*draw)(void),int (*key)(int key,int mouse_x,int mouse_y),void (*closed)(void)){
    if(!draw || !key || !allowed())return 0;
    panel_draw=draw;panel_key=key;panel_closed=closed;opened(4);return 1;
}
/* RC2-SELLUS-NO-TALK-65: the dialogue window (OpenMW: the use key on a person is ActionTalk, GM_Dialogue) is never one
 * of the menus the opening keeps shut until a script switches it on; it opens whenever the game is in play, so Sellus
 * Gravius, the clerk and the door guard talk in it during the registration, as in the original. Before, it went through
 * AW_WorldUIOpenPanel, whose AW_StoryRestricted refused every window until the registration ended, silently. */
int AW_WorldUIOpenDialoguePanel(void (*draw)(void),int (*key)(int key,int mouse_x,int mouse_y),void (*closed)(void)){
    /* the order of the registration (the maintainer, 12 November 2026: the character sheet FIRST, and the talk unlocked
     * the same way as taking things from the tables): the census office's one rule, aw_census_take_refused
     * (aw_opening.c AW_OpeningTakeRefused: census type amiwind, before the papers' stage), shuts the window as it shuts
     * the takes; from the papers on the table the clerk, the hall guard and Sellus Gravius talk in it, and Sellus takes
     * the papers in it */
    if(!draw || !key || !allowed_in_play() || (aw_census_take_refused && aw_census_take_refused()))return 0;
    panel_draw=draw;panel_key=key;panel_closed=closed;opened(4);return 1;
}
/* the same for a window a script can switch on in the opening (MENU: AW_MENU_STATS, AW_MENU_MAGIC) */
int AW_WorldUIOpenMenuPanel(void (*draw)(void),int (*key)(int key,int mouse_x,int mouse_y),void (*closed)(void),int menu){
    if(!draw || !key || !menu_allowed(menu))return 0;
    panel_draw=draw;panel_key=key;panel_closed=closed;opened(4);return 1;
}
void AW_InventoryOpen(void){
    int i;
    /* the inventory opens during the registration from the papers on, as in the original (aw_story.c
     * AW_StoryInventoryAllowed, CHARGEN-INVENTORY-LOCKED-60); the map and journal keep the released-game rule */
    if(!allowed_in_play() || !AW_StoryInventoryAllowed() || !AW_ControlAllowed(AW_CONTROL_PLAYER) ||
       svs.clients[0].edict->v.health<=0 || werewolf_now())return;
    inventory=(inventory_panel_t *)AW_TryCalloc(1,sizeof(*inventory));
    if(!inventory){Con_Printf("Inventory: not enough memory.\n");return;}
    for(i=0;i<INV_VISIBLE;i++)inventory->icon_row[i]=-1;
    inventory->click_row=-1;   /* INVENTORY-DOUBLECLICK-62: no click yet */
    inventory->angle=(float)M_PI;opened(3);
    inventory->message_row=-1;inventory->message_until=1e30;   /* the window's own faults stay said */
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
/* INVENTORY-OPEN-WINDOW-NO-REFRESH-61: the carried kinds in two numbers (how many rows have a count, and the sum of
 * their id hashes): one pass over the item rows, no record read */
static void inventory_kinds(uint32_t *kinds,uint32_t *sum){
    int i,n=AW_ItemCount(&aw_state);const aw_item_row_t *r;
    *kinds=0;*sum=0;
    for(i=0;i<n;i++){r=AW_ITEM_ROW(&aw_state,i);if(r->value>0){(*kinds)++;*sum+=r->hash*2654435761U+1U;}}
}
static void inventory_seen(void){
    memcpy(inventory->seen_worn,aw_state.inventory.equipped,sizeof(inventory->seen_worn));
    inventory_kinds(&inventory->seen_kinds,&inventory->seen_kinds_sum);
}
/* every frame the window is open: a worn set changed elsewhere renders the picture and the armour rating again (the
 * list's marks are read at each draw), a carried kind gained or lost elsewhere reads the list again. OpenMW redraws
 * its preview and list on any change of the container store (mwgui/inventorywindow.cpp updateItemView and
 * dirtyPreview, called by the InventoryStore listener); the original's window follows the same. */
static void inventory_watch(void){
    uint32_t kinds,sum;
    if(memcmp(inventory->seen_worn,aw_state.inventory.equipped,sizeof(inventory->seen_worn))){
        memcpy(inventory->seen_worn,aw_state.inventory.equipped,sizeof(inventory->seen_worn));
        inventory->preview_state=0;inventory->armor_state=0;
    }
    inventory_kinds(&kinds,&sum);
    if(kinds!=inventory->seen_kinds || sum!=inventory->seen_kinds_sum)inventory_refresh();
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
            inventory->message_row=-1;inventory->message_until=1e30;
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
    inventory_seen();
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
    inventory->click_row=-1;   /* INVENTORY-DOUBLECLICK-62: the rows may have moved: a new click starts again */
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
/* EQUIP-ACTION-REGRESSION-62: the actions come from the item's class, read from its record (the catalogue's flag 1:
 * weapons, armour, clothing, rings and amulets, carried lights), as in the original: such an item always offers Equip
 * (Unequip when worn). Whether it can be put on now (one of it, its condition, the hands free) is decided when the
 * action is taken, with a message, never by hiding the action (the census dagger showed no action at all). */
static int inventory_equippable(const aw_inventory_item_t *item){
    return item && (item->flags&AW_INV_EQUIP)!=0;
}
/* ALCHEMY-61 (aw_inventory.h; aw_alchemy.c sets them, NULL in the fixtures): a potion drunk, an ingredient eaten, an
 * apparatus opening the alchemy window */
int (*aw_worldui_use)(const aw_inventory_item_t *it);
void (*aw_worldui_alchemy_open)(void);
/* MWSCRIPT-GAP-FUNCTIONS-62 (aw_mwhost.c sets it, NULL in the fixtures): the item's script around its equipping:
 * phase 0 before (1: its PCSkipEquip takes it, nothing is worn), phase 1 after it was worn (OnPCEquip set) */
int (*aw_worldui_equip_script)(const aw_inventory_item_t *it,int phase);
static int inventory_usable(const aw_inventory_item_t *item){return item && aw_worldui_use && AW_INV_USABLE_KIND(item);}
/* EQUIP-ACTION-REGRESSION-62 (item classes): a book or scroll offers Read (OpenMW mwclass/book.cpp: ActionRead) */
int (*aw_worldui_read)(const char *id);
/* the game's own lines by key (aw_levelup.c AW_LevelupGameText; NULL in the fixtures) */
int (*aw_worldui_game_text)(const char *key,char *out,int size);
static int inventory_readable(const aw_inventory_item_t *item){return item && aw_worldui_read && item->category==AW_INV_BOOK;}
static int inventory_droppable(const aw_inventory_item_t *item){
    return item && (item->flags&AW_INV_DROP) &&
        (!AW_InventoryEquipped(&aw_state,item->id) || inventory_equippable(item));
}
/* SCROLL-CAST-64 (aw_inventory.h): a Cast Once item's Use (aw_cast.c sets it; NULL in the fixtures) */
int (*aw_worldui_cast)(const aw_inventory_item_t *it);
/* INVENTORY-EQUIP-HINTS-67: the item's one action (aw_inventory.c AW_InventoryItemAction, by its kind), and the
 * inventory_action code that does it here (0 when this window cannot do it: no reader, no alchemy, no casting) */
static int inventory_act(const aw_inventory_item_t *item){
    return item?AW_InventoryItemAction(item,AW_InventoryEquipped(&aw_state,item->id)>0):AW_INV_ACT_NONE;
}
static int inventory_castable(const aw_inventory_item_t *item){
    return aw_worldui_cast && inventory_act(item)==AW_INV_ACT_CAST;
}
static int inventory_primary(const aw_inventory_item_t *item){
    switch(inventory_act(item)){
    case AW_INV_ACT_EQUIP:case AW_INV_ACT_UNEQUIP:return 1;
    case AW_INV_ACT_USE:return inventory_usable(item)?3:0;
    case AW_INV_ACT_CAST:return inventory_castable(item)?5:0;
    case AW_INV_ACT_READ:return inventory_readable(item)?4:0;
    }
    return 0;
}
#define INV_MESSAGE_SECONDS 4.0
/* an action's result line: for the selected row, a few seconds (the row's hint comes back after it) */
static void inventory_said(void){
    inventory->message_row=inventory->selected;inventory->message_until=Sys_FloatTime()+INV_MESSAGE_SECONDS;
}
static const char *inventory_message(void){
    if(!inventory->message[0] || Sys_FloatTime()>=inventory->message_until ||
       (inventory->message_row>=0 && inventory->message_row!=inventory->selected))return NULL;
    return inventory->message;
}
/* INVENTORY-ITEM-INFO-67 (aw_iteminfo.h): the sources of what the box shows beyond the catalogue row (NULL in the
 * fixtures) and the information key, bindable and saved like the use and drop keys (OPENING-TUTORIAL-KEYS-65): P, as
 * I closes the window */
int (*aw_worldui_condition)(const char *id,float *condition);
int (*aw_worldui_enchant_lines)(const aw_inventory_item_t *it,char *out,int size);
int (*aw_worldui_alchemy_lines)(const aw_inventory_item_t *it,char *out,int size);
char *(*aw_worldui_book_text)(const char *id);
cvar_t aw_key_inv_info={"aw_key_inv_info","P",true};
#define INV_INFO_MAGIC 1024
/* the box for the selected item: its condition and charge now, its effect lines, a book's text, its action's word; the
 * text and the effect lines are read once, here, and freed when it closes */
static void inventory_info_open(void){
    aw_inventory_item_t *item=inventory_selected();aw_iteminfo_extra_t x;char *magic=NULL,*body=NULL;
    const char *word;int act;
    if(!item || inventory->info)return;
    memset(&x,0,sizeof(x));
    if(aw_worldui_condition)x.condition_known=aw_worldui_condition(item->id,&x.condition);
    if(item->enchant_kind!=AW_ENCH_NONE && item->charge_max>0){x.charge_known=1;x.charge=AW_MagicCharge(&aw_state,item);}
    if((aw_worldui_enchant_lines || aw_worldui_alchemy_lines) && (magic=(char *)AW_TryMalloc(INV_INFO_MAGIC))!=NULL){
        magic[0]=0;
        if(item->enchant_kind!=AW_ENCH_NONE && aw_worldui_enchant_lines)aw_worldui_enchant_lines(item,magic,INV_INFO_MAGIC);
        else if((item->flags&AW_INV_ALCHEMY) && aw_worldui_alchemy_lines)aw_worldui_alchemy_lines(item,magic,INV_INFO_MAGIC);
        x.magic=magic;
    }
    if(item->category==AW_INV_BOOK && aw_worldui_book_text)x.body=body=aw_worldui_book_text(item->id);
    act=inventory_act(item);word=inventory_primary(item)?AW_InventoryActionWord(act):NULL;
    inventory->info=AW_ItemInfoOpen(item,&x,word);
    free(magic);free(body);
    if(!inventory->info){strcpy(inventory->message,"Not enough memory for the item's information.");inventory_said();}
    inventory->context=0;
}
static void inventory_info_close(void){AW_ItemInfoClose(inventory->info);inventory->info=NULL;drag=0;}
static void inventory_action(int action){
    aw_inventory_item_t *item=inventory_selected();int ok=0;
    if(!item)return;
    if(action==5 && inventory_castable(item)){
        /* SCROLL-CAST-64: E/Use casts a Cast Once item (the maintainer's decision of 18 November 2026; the original
         * casts it from the magic menu, which stays: Magic Items). The window closes first so the spell is seen; the
         * cast says its own refusal. */
        aw_inventory_item_t cast=*item;
        close_panel();
        aw_worldui_cast(&cast);
        return;
    }
    if(action==6){inventory_info_open();return;}   /* INVENTORY-ITEM-INFO-67: the right button's Info */
    inventory->preview_state=0;   /* equipment may change: one new still picture */
    inventory->armor_state=0;     /* and the armour rating again */
    if(action==1 && inventory_equippable(item)){
        int worn=AW_InventoryEquipped(&aw_state,item->id);
        if(!worn && !AW_InventoryCanEquip(item)){
            /* the original's own line when it has one (a beast race: sNotifyMessage13/14/15) */
            const char *key=AW_InventoryEquipRefusal();
            if(!key || !aw_worldui_game_text || !aw_worldui_game_text(key,inventory->message,sizeof(inventory->message)))
                strcpy(inventory->message,"This item cannot be equipped now.");
            inventory->context=0;inventory_refresh();inventory_said();return;
        }
        AW_CombatEquipmentStore();
        if(worn){
            ok=AW_InventoryUnequip(&aw_state,item->id);
            if(ok && aw_worldui_equip_script)aw_worldui_equip_script(item,2);   /* taken off: OnPCEquip 0 */
        }else if(aw_worldui_equip_script && aw_worldui_equip_script(item,0)){
            /* its script took the equipping (PCSkipEquip): nothing is worn, the script says what happens */
            inventory->message[0]=0;inventory->context=0;inventory_refresh();return;
        }else{
            ok=AW_InventoryEquip(&aw_state,item);
            if(ok && aw_worldui_equip_script)aw_worldui_equip_script(item,1);
        }
        if(ok)AW_CombatEquipmentChanged();
        strcpy(inventory->message,ok?"Equipment updated.":"Cannot equip this item.");
    }else if(action==3 && inventory_usable(item)){
        /* ALCHEMY-61: a potion drunk, an ingredient eaten (aw_alchemy.c), an apparatus opens the alchemy window once
         * this window has closed (OpenMW mwclass/apparatus.cpp use: ActionAlchemy) */
        ok=aw_worldui_use(item);
        if(ok==2){close_panel();if(aw_worldui_alchemy_open)aw_worldui_alchemy_open();return;}
        if(!ok)strcpy(inventory->message,"Cannot use this item now.");
        else inventory->message[0]=0;
    }else if(action==4 && inventory_readable(item)){
        char id[sizeof(item->id)];strcpy(id,item->id);
        close_panel();
        if(!aw_worldui_read(id))Con_Printf("%s cannot be read.\n",id);
        return;
    }else if(action==2 && inventory_droppable(item)){
        /* First stage drops one real item; repeated actions preserve stack count.
         * No deletion occurs when the world placement/model/entity is refused. */
        ok=AW_InventoryDropHere(item,1);
        /* DROP-REFUSED-CENSUS-ROOM-67: the refusal's reason (which check, "kept.") only with the debug HUD on (dbg all);
         * the player reads a plain line (the console's aw_inventory drop always prints the reason) */
        strcpy(inventory->message,ok?"Dropped one item.":AW_DebugOverlaysEnabled()?AW_InventoryDropReason():
               "This item cannot be dropped here.");
    }
    inventory->context=0;inventory_refresh();inventory_said();
}
/* INVENTORY-DOUBLECLICK-62 (aw_inventory.h): a double-click on a row does what dropping the item on the character
 * picture does in the original and OpenMW 0.51 (inventorywindow.cpp onAvatarClicked, useItem): what can be worn goes
 * on or comes off at once, with a short notice box "Equipped <name>" / "Unequipped <name>" (the refusal's own line when
 * it cannot); a book is read; an apparatus opens the alchemy window; a potion or an ingredient asks first, in a box
 * with OK and Cancel (Enter / Esc), the count slider and number field in it for a stack. */
static void inventory_text(int x,int y,int width,int height,const char *value,int color);
static int inventory_consumable(const aw_inventory_item_t *item){
    return inventory_usable(item) && item->alchemy_kind!=AW_ALCHEMY_APPARATUS;
}
static void inventory_notice(const char *text){
    Q_strcpy_bounded(inventory->notice,text,sizeof(inventory->notice));
    inventory->notice_until=Sys_FloatTime()+INV_NOTICE_SECONDS;
}
static void inventory_confirm_close(void){inventory->confirm=inventory->confirm_drag=0;}
static void inventory_confirm_open(const aw_inventory_item_t *item){
    int have=AW_StateGet(&aw_state,AW_ITEM,item->id);
    if(have<1)return;
    inventory->confirm_item=*item;inventory->confirm=1;inventory->confirm_max=have;inventory->confirm_count=1;
    inventory->confirm_fresh=1;inventory->confirm_drag=0;inventory->context=0;inventory->notice_until=0;
}
static const char *inventory_use_verb(const aw_inventory_item_t *it,int past){
    if(it->alchemy_kind==AW_ALCHEMY_POTION)return past?"drunk":"Drink";
    if(it->alchemy_kind==AW_ALCHEMY_INGREDIENT)return past?"eaten":"Eat";
    return past?"used":"Use";
}
/* OK: the count, one use after the other (OpenMW drinks a dragged stack one potion per use), stopping at the first
 * refusal; the list and the picture follow */
static void inventory_confirm_ok(void){
    aw_inventory_item_t item=inventory->confirm_item;int n=inventory->confirm_count<1?1:inventory->confirm_count,used=0;
    inventory_confirm_close();
    inventory->preview_state=0;inventory->armor_state=0;
    while(used<n && AW_StateGet(&aw_state,AW_ITEM,item.id)>0 && aw_worldui_use && aw_worldui_use(&item)==1)used++;
    if(!used)strcpy(inventory->message,"Cannot use this item now.");
    else Q_snprintf(inventory->message,sizeof(inventory->message),"%s: %d %s.",item.name[0]?item.name:item.id,used,
                    inventory_use_verb(&item,1));
    inventory_refresh();inventory_said();
}
static void inventory_confirm_key(int key){
    int max=inventory->confirm_max,count=inventory->confirm_count,stack=max>1;
    if(key==K_ENTER){inventory_confirm_ok();return;}
    if(key==K_MOUSE1){
        if(mouse_y>=INV_CONFIRM_BUTTON_Y && mouse_y<INV_CONFIRM_BUTTON_Y+12){
            if(mouse_x>=INV_CONFIRM_OK_X && mouse_x<INV_CONFIRM_OK_X+INV_CONFIRM_BUTTON_W){inventory_confirm_ok();return;}
            if(mouse_x>=INV_CONFIRM_CANCEL_X && mouse_x<INV_CONFIRM_CANCEL_X+INV_CONFIRM_BUTTON_W){inventory_confirm_close();return;}
        }
        if(stack && mouse_y>=INV_CONFIRM_RAIL_Y-4 && mouse_y<INV_CONFIRM_RAIL_Y+8 &&
           mouse_x>=INV_CONFIRM_RAIL_X-2 && mouse_x<INV_CONFIRM_RAIL_X+INV_CONFIRM_RAIL_W+2){
            inventory->confirm_count=AW_InventorySliderCount(mouse_x,INV_CONFIRM_RAIL_X,INV_CONFIRM_RAIL_W,max);
            inventory->confirm_fresh=0;inventory->confirm_drag=1;drag=K_MOUSE1;
        }
        return;                                   /* the box holds the window until OK or Cancel */
    }
    if(!stack)return;
    if(key==K_RIGHTARROW || key==K_UPARROW || key==K_MWHEELUP)count++;
    else if(key==K_LEFTARROW || key==K_DOWNARROW || key==K_MWHEELDOWN)count--;
    else if(key==K_PGUP)count+=10;
    else if(key==K_PGDN)count-=10;
    else if(key==K_HOME)count=1;
    else if(key==K_END)count=max;
    else if((key>='0' && key<='9') || key==K_BACKSPACE){
        inventory->confirm_count=AW_InventoryCountType(count,inventory->confirm_fresh,key==K_BACKSPACE?'\b':key,max);
        inventory->confirm_fresh=0;return;
    }else return;
    inventory->confirm_count=minmax(count,1,max);inventory->confirm_fresh=0;
}
static void inventory_double(int row){
    aw_inventory_item_t *item=inventory_item(row,NULL);char id[64],name[96],line[112];int worn;
    if(!item)return;
    inventory->selected=row;
    if(inventory_equippable(item)){
        Q_strcpy_bounded(id,item->id,sizeof(id));Q_strcpy_bounded(name,item->name[0]?item->name:item->id,sizeof(name));
        worn=AW_InventoryEquipped(&aw_state,id)>0;
        inventory_action(1);
        if((AW_InventoryEquipped(&aw_state,id)>0)!=worn){
            Q_snprintf(line,sizeof(line),"%s %s",worn?"Unequipped":"Equipped",name);inventory_notice(line);
        }else inventory_notice(inventory->message);
        return;
    }
    if(inventory_consumable(item)){inventory_confirm_open(item);return;}
    if(inventory_usable(item)){inventory_action(3);return;}     /* an apparatus: the alchemy window */
    if(inventory_castable(item)){inventory_action(5);return;}   /* SCROLL-CAST-64: a Cast Once scroll is cast */
    if(inventory_readable(item)){inventory_action(4);return;}
}
/* The right button's menu (INVENTORY-EQUIP-HINTS-67), one list for its drawing and its clicks: the item's action (a
 * potion's Drink, an ingredient's Eat), Read for any book or scroll (the original's ActionRead, kept beside a scroll's
 * cast), Drop one. WHAT: the inventory_action codes, WORDS: the labels; the number of entries. */
#define INV_MENU 4
static int inventory_menu(const aw_inventory_item_t *item,int what[INV_MENU],const char *words[INV_MENU]){
    int n=0,act=inventory_act(item),primary=inventory_primary(item);
    if(primary==3){what[n]=3;words[n++]=item->alchemy_kind==AW_ALCHEMY_POTION?"Drink":
                                       item->alchemy_kind==AW_ALCHEMY_INGREDIENT?"Eat":"Use";}
    else if(primary==1 || primary==5){what[n]=primary;words[n++]=AW_InventoryActionWord(act);}
    if(inventory_readable(item)){what[n]=4;words[n++]="Read";}
    if(inventory_droppable(item)){what[n]=2;words[n++]="Drop one";}
    what[n]=6;words[n++]="Info";   /* INVENTORY-ITEM-INFO-67: the item information box (the original's sInfo) */
    return n;
}
static void inventory_confirm_draw(int gold,int muted){
    char line[128];const aw_inventory_item_t *it=&inventory->confirm_item;int max=inventory->confirm_max,x,y=INV_CONFIRM_Y;
    AW_UIFill(INV_CONFIRM_X,y,INV_CONFIRM_W,INV_CONFIRM_H,AW_UIColor(10,9,7));AW_UIBox(INV_CONFIRM_X,y,INV_CONFIRM_W,INV_CONFIRM_H);
    Q_snprintf(line,sizeof(line),"%s %s?",inventory_use_verb(it,0),it->name[0]?it->name:it->id);
    inventory_text(INV_CONFIRM_X+6,y+6,INV_CONFIRM_W-12,8,line,gold);
    if(max>1){
        Q_snprintf(line,sizeof(line),"How many? 1 to %d",max);
        inventory_text(INV_CONFIRM_X+6,y+16,INV_CONFIRM_W-12,8,line,muted);
        AW_UIFill(INV_CONFIRM_X+6,y+26,48,10,AW_UIColor(29,23,17));
        if(inventory->confirm_count>0)Q_snprintf(line,sizeof(line),"%d_",inventory->confirm_count);else strcpy(line,"_");
        inventory_text(INV_CONFIRM_X+8,y+26,44,10,line,gold);
        Q_snprintf(line,sizeof(line),"of %d",max);inventory_text(INV_CONFIRM_X+58,y+26,60,10,line,muted);
        AW_UIFill(INV_CONFIRM_RAIL_X,INV_CONFIRM_RAIL_Y+1,INV_CONFIRM_RAIL_W,2,muted);
        x=AW_InventorySliderX(inventory->confirm_count<1?1:inventory->confirm_count,INV_CONFIRM_RAIL_X,INV_CONFIRM_RAIL_W,max);
        AW_UIFill(x-1,INV_CONFIRM_RAIL_Y-2,3,8,gold);
    }else inventory_text(INV_CONFIRM_X+6,y+20,INV_CONFIRM_W-12,8,"The last one.",muted);
    AW_UIFill(INV_CONFIRM_OK_X,INV_CONFIRM_BUTTON_Y,INV_CONFIRM_BUTTON_W,12,AW_UIColor(44,36,20));
    AW_UIFill(INV_CONFIRM_CANCEL_X,INV_CONFIRM_BUTTON_Y,INV_CONFIRM_BUTTON_W,12,AW_UIColor(44,36,20));
    inventory_text(INV_CONFIRM_OK_X+(INV_CONFIRM_BUTTON_W-8)/2,INV_CONFIRM_BUTTON_Y,12,12,"OK",gold);
    inventory_text(INV_CONFIRM_CANCEL_X+(INV_CONFIRM_BUTTON_W-24)/2,INV_CONFIRM_BUTTON_Y,28,12,"Cancel",gold);
}
static void inventory_notice_draw(int gold){
    int w;
    if(inventory->confirm || !inventory->notice[0] || Sys_FloatTime()>=inventory->notice_until)return;
    w=(int)strlen(inventory->notice)*4+12;if(w>164)w=164;if(w<60)w=60;
    AW_UIFill(224-w/2,94,w,16,AW_UIColor(10,9,7));AW_UIBox(224-w/2,94,w,16);
    inventory_text(224-w/2+6,94,w-12,16,inventory->notice,gold);
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
/* OPENING-TUTORIAL-KEYS-65: the inventory window's own action keys, bindable and saved (the maintainer: the window's
 * keys too, so a hint names what the player bound): a list of key names, a letter or ENTER, TAB, SPACE, BACKSPACE, DEL.
 * The defaults are the keys of before (use/equip E and Enter, drop D). The hints read the same lists (aw_textdef.c
 * {key:winkey:...}). Sort (O) and the category (Tab) keep their fixed keys for now (listed for v0.0.66). */
cvar_t aw_key_inv_use={"aw_key_inv_use","E ENTER",true};
cvar_t aw_key_inv_drop={"aw_key_inv_drop","D",true};
static int win_key(const char *list,int key){
    static const struct {const char *name;int key;} named[]={{"ENTER",K_ENTER},{"TAB",K_TAB},{"SPACE",K_SPACE},
        {"BACKSPACE",K_BACKSPACE},{"DEL",K_DEL}};
    const char *p=list;int n,i,c;
    while(p && *p){
        while(*p==' ')p++;
        for(n=0;p[n] && p[n]!=' ';n++);
        if(n==1){c=(unsigned char)p[0];if(c>='A' && c<='Z')c+='a'-'A';if(c==key)return 1;}
        else if(n>1)for(i=0;i<(int)(sizeof(named)/sizeof(named[0]));i++){
            int j;
            if((int)strlen(named[i].name)!=n || named[i].key!=key)continue;
            for(j=0;j<n;j++){c=(unsigned char)p[j];if(c>='a' && c<='z')c-='a'-'A';if(c!=named[i].name[j])break;}
            if(j==n)return 1;
        }
        p+=n;
    }
    return 0;
}
/* a key list as the footer shows it: "E ENTER" -> "E/Enter" */
static void win_key_words(const char *list,char *out,int capacity){
    const char *p=list;int n,k=0,i,c;
    if(capacity<1)return;
    while(p && *p){
        while(*p==' ')p++;
        for(n=0;p[n] && p[n]!=' ';n++);
        if(!n)break;
        if(k && k<capacity-1)out[k++]='/';
        for(i=0;i<n && k<capacity-1;i++){c=(unsigned char)p[i];
            if(i==0 && c>='a' && c<='z')c-='a'-'A';else if(i>0 && n>1 && c>='A' && c<='Z')c+='a'-'A';out[k++]=(char)c;}
        p+=n;
    }
    out[k]=0;
}
static void inventory_key(int key){
    int i,x,y,row,top;aw_inventory_item_t *item=inventory_selected();
    if(!inventory)return;
    drag=0;
    if(inventory->confirm){inventory_confirm_key(key);return;}   /* INVENTORY-DOUBLECLICK-62: the box answers first */
    if(inventory->info){   /* INVENTORY-ITEM-INFO-67: the information box answers first; its action is the window's */
        int r=AW_ItemInfoKey(inventory->info,key,mouse_x,mouse_y,win_key(aw_key_inv_use.string,key),
                             win_key(aw_key_inv_info.string,key));
        if(r==AW_ITEMINFO_CLOSE)inventory_info_close();
        else if(r==AW_ITEMINFO_ACTION){int a=inventory_primary(item);inventory_info_close();if(a)inventory_action(a);}
        else if(inventory->info->drag)drag=K_MOUSE1;
        return;
    }
    /* The original picture does not turn; turning is the live preview's (aw_inventory_preview_live 1). */
    if(key==K_LEFTARROW){if(AW_ViewInventoryLive())inventory->angle-=.25f;return;}
    if(key==K_RIGHTARROW){if(AW_ViewInventoryLive())inventory->angle+=.25f;return;}
    /* the one list rule (aw_listnav.h, INVENTORY-ARROWS-SCROLL-62): Up/Down, pages, ends; the list follows */
    if(AW_ListNavKey(key,&inventory->selected,&inventory->top,inventory->count,INV_VISIBLE)){inventory->context=0;return;}
    if(key==K_TAB){inventory->category=(inventory->category+1)%8;inventory->selected=inventory->top=0;inventory_filter();}
    if(key=='o'){inventory->sort=(inventory->sort+1)%3;inventory_filter();}
    /* INVENTORY-EQUIP-HINTS-67: the use key does the item's one action (Equip, Unequip, Use, a scroll's cast, Read) */
    if(win_key(aw_key_inv_use.string,key)){int a=inventory_primary(item);if(a)inventory_action(a);return;}
    if(win_key(aw_key_inv_drop.string,key)){inventory_action(2);return;}
    if(win_key(aw_key_inv_info.string,key)){inventory_info_open();return;}   /* INVENTORY-ITEM-INFO-67 */
    if(key==K_MOUSE3 || key==K_MOUSE2){
        int what[INV_MENU];const char *words[INV_MENU];
        if(mouse_x<128 || mouse_x>=inventory_list_right() || mouse_y<INV_LIST_Y || mouse_y>=INV_LIST_Y+INV_VISIBLE*INV_ROW_H)return;
        row=inventory->top+(mouse_y-INV_LIST_Y)/INV_ROW_H;if(row>=inventory->count)return;
        inventory->selected=row;
        inventory->context=inventory->count!=0;
        /* room for its entries above the footer (ALCHEMY-61: up to three) */
        item=inventory_item(row,NULL);
        inventory->context_x=minmax(mouse_x,128,206);
        inventory->context_y=minmax(mouse_y,50,INV_CONTROLS_Y-(item?inventory_menu(item,what,words):0)*16-4);
        return;
    }
    if(key==K_MOUSE1){
        if(inventory->context){
            int what[INV_MENU],n;const char *words[INV_MENU];
            x=inventory->context_x;y=inventory->context_y;
            n=item?inventory_menu(item,what,words):0;
            for(row=0;row<n;row++)
                if(mouse_x>=x && mouse_x<x+110 && mouse_y>=y+row*16 && mouse_y<y+(row+1)*16){inventory_action(what[row]);return;}
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
            if(row<inventory->count){
                /* INVENTORY-DOUBLECLICK-62: the second click on the same row within half a second */
                double now=Sys_FloatTime();
                if(AW_InventoryDoubleClick(inventory->click_row,inventory->click_time,row,now)){
                    inventory->click_row=-1;inventory_double(row);return;
                }
                inventory->click_row=row;inventory->click_time=now;
                inventory->selected=row;
            }
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
/* the id whose picture a row shows (aw_alchemy.c: a made item's base; NULL in the fixtures: the row's own) */
const char *(*aw_worldui_icon_id)(const char *id);
/* INDEX: the list row */
static void inventory_icon(int slot,int index,int x,int y){
    FILE *f=NULL;int size,xx,yy;byte raw[1028];const aw_inventory_item_t *it=inventory_item(index,NULL);
    if(!it)return;
    /* MADE-ITEM-NO-PICTURE-62: a made item (aw_made_N: a made potion, an enchanted item) shows its base item's picture */
    if(aw_inventory_row_icon && aw_inventory_row_icon(slot,aw_worldui_icon_id?aw_worldui_icon_id(it->id):it->id,
                                                      AW_InventoryEquipped(&aw_state,it->id)>0,x,y))return;
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
 * frame only copies the picture back. aw_inventory_preview_live 1: the old live, turnable preview.
 * INVENTORY-PREVIEW-STALE-61: a changed outfit's parts load over several frames (aw_view.c parts_ready,
 * ARRIVAL-LONG-FRAME-DEV6-59) and the body keeps the previous outfit until they are all in; a picture rendered then
 * showed the previous outfit and was kept. Now the picture waits for them (OpenMW redraws the preview once the new
 * parts are attached, characterpreview.cpp rebuild + redraw), the kept picture shown meanwhile, at most
 * INV_PREVIEW_WAIT seconds. aw_inventory_preview_pending (aw_view.c): 1 while such an assembly is under way. */
int (*aw_inventory_preview_pending)(void);
#define INV_PREVIEW_WAIT 5.0
static void inventory_preview_copy(void){
    int y;
    for(y=0;y<INV_PREVIEW_H;y++)
        memcpy(vid.buffer+(INV_PREVIEW_Y+y)*vid.rowbytes+INV_PREVIEW_X,inventory->preview+y*INV_PREVIEW_W,INV_PREVIEW_W);
}
static void inventory_preview(int muted){
    model_t *model=NULL;int frame,y,ok;double t0=Sys_FloatTime(),t1;
    if(AW_ViewInventoryLive()){
        if(!AW_ViewInventoryBody(&model,&frame) || !AW_InventoryPreviewDraw(model,frame,INV_PREVIEW_X,INV_PREVIEW_Y,
                                                                            INV_PREVIEW_W,INV_PREVIEW_H,inventory->angle))
            inventory_text(10,80,108,40,"Character preview unavailable",muted);
    }else{
        if(!inventory->preview_state){
            ok=AW_ViewInventoryBody(&model,&frame);     /* also loads the next of a new outfit's parts */
            if(aw_inventory_preview_pending && aw_inventory_preview_pending()){
                if(!inventory->preview_waiting){inventory->preview_waiting=1;inventory->preview_wait=t0;}
                if(t0-inventory->preview_wait<INV_PREVIEW_WAIT){
                    if(inventory->preview_have)inventory_preview_copy();
                    inventory->preview_seconds+=Sys_FloatTime()-t0;inventory->preview_frames++;
                    return;
                }
            }
            inventory->preview_waiting=0;
            ok=ok &&AW_InventoryPreviewDraw(model,frame,INV_PREVIEW_X,INV_PREVIEW_Y,INV_PREVIEW_W,INV_PREVIEW_H,(float)M_PI);
            if(ok)for(y=0;y<INV_PREVIEW_H;y++)
                memcpy(inventory->preview+y*INV_PREVIEW_W,vid.buffer+(INV_PREVIEW_Y+y)*vid.rowbytes+INV_PREVIEW_X,INV_PREVIEW_W);
            AW_InventoryPreviewClear();      /* pose model and depth buffer are not kept */
            inventory->preview_state=ok?1:-1;inventory->preview_have=ok;inventory->preview_renders++;
            t1=Sys_FloatTime();inventory->preview_render_seconds=t1-t0;t0=t1;
        }else if(inventory->preview_state>0)inventory_preview_copy();
        if(inventory->preview_state<0)inventory_text(10,80,108,40,"Character preview unavailable",muted);
    }
    inventory->preview_seconds+=Sys_FloatTime()-t0;inventory->preview_frames++;
}
/* The original window title bar (UI-WINDOW-TITLE-BAR-42), drawn by aw_icons.c from the
 * imported art; without it the title is centred alone in the same band. */
int (*aw_title_bar)(int x,int y,int w,const char *title);
int (*aw_title_plaque)(int x,int y,int w,int *plaque_x,int *plaque_w);   /* MAP-VERSION-2-DEFAULT-68 (aw_icons.c) */
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
 * bar art of the magicka bar, AW_UIBar colour 1). The encumbrance is the running total (aw_move.h), nothing summed.
 * The numbers are the console-derived glyphs of the item list (4 px a character, 5 rows), centred, with a black
 * shadow one pixel down and right: the ornate menu font over the blue fill could not be read at any fill
 * (INVENTORY-BURDEN-TEXT-UNREADABLE-61). */
float (*aw_worldui_encumbrance)(float *capacity);
static void inventory_burden(void){
    char line[32];float capacity=0,load;int shown,max,w,x,y;
    if(!aw_worldui_encumbrance)return;
    load=aw_worldui_encumbrance(&capacity);
    shown=(int)load;if((float)shown<load)shown++;     /* std::ceil */
    max=(int)capacity;
    AW_UIBar(8,INV_BURDEN_Y,114,INV_BURDEN_H,1,max>0?(float)shown/(float)max:shown>0?1.0f:0.0f);
    sprintf(line,"%d/%d",shown,max);
    w=(int)strlen(line)*4;if(w>114)w=114;
    x=8+(114-w)/2;y=INV_BURDEN_Y+(INV_BURDEN_H-5)/2;
    AW_SmallStringColor(x+1,y+1,w,line,AW_UIColor(0,0,0));
    AW_SmallStringColor(x,y,w,line,AW_UIColor(255,255,255));
}
/* The armour rating under the picture (INVENTORY-NO-ARMOR-RATING-61): OpenMW mwgui/inventorywindow.cpp
 * updateArmorRating, "#{sArmor}: N" (the game's sArmor, "Armor"), N the whole number of the player's rating
 * (aw_combat.c AW_CombatPlayerArmorRating: the worn pieces, the skills, the unarmored skill, a Shield effect), worked
 * out when the window opens and after each action, not every frame (it reads the worn pieces' records). In the burden
 * bar's console-derived glyphs, centred under the picture, with the same shadow. */
float (*aw_worldui_armor_rating)(void);
static void inventory_armor(void){
    char line[32];int w,x;float rating;
    if(!aw_worldui_armor_rating)return;
    if(!inventory->armor_state){
        rating=aw_worldui_armor_rating();
        inventory->armor_state=rating>=0 && rating<100000?1:-1;inventory->armor=inventory->armor_state>0?(int)rating:0;
    }
    if(inventory->armor_state<0)return;
    sprintf(line,"Armor: %d",inventory->armor);
    w=(int)strlen(line)*4;if(w>INV_PREVIEW_W)w=INV_PREVIEW_W;
    x=INV_PREVIEW_X+(INV_PREVIEW_W-w)/2;
    AW_SmallStringColor(x+1,INV_ARMOR_Y+1,w,line,AW_UIColor(0,0,0));
    AW_SmallStringColor(x,INV_ARMOR_Y,w,line,AW_UIColor(255,255,255));
}
/* INVENTORY-EQUIP-HINTS-67: the key line's second row: the list keys, then the selected item's action with the use key
 * as it is bound now ("E/Enter equip", "E/Enter unequip", "E/Enter use", "E/Enter read"; the maintainer, 18 November
 * 2026: the action in the key line when there is one) and the drop key. The live preview's turning goes on the first
 * row after the category key. A token that would not fit its row is left out, never cut. */
#define INV_KEYLINE_CHARS 45
static void keyline_add(char *row,int size,const char *token){
    int n=(int)strlen(row),t=(int)strlen(token);
    if(!t || n+(n?3:0)+t>INV_KEYLINE_CHARS || n+3+t>=size)return;
    if(n)strcat(row,"   ");
    strcat(row,token);
}
static void inventory_keyline(const aw_inventory_item_t *item,int gold){
    char row[96],keys[32],token[64];int a=item?inventory_primary(item):0,i;const char *word;
    row[0]=0;keyline_add(row,sizeof(row),"Up/Down select");
    if(a && (word=AW_InventoryActionWord(inventory_act(item)))!=NULL){
        win_key_words(aw_key_inv_use.string,keys,sizeof(keys));
        Q_snprintf(token,sizeof(token),"%s %s",keys,word);
        for(i=(int)strlen(keys)+1;token[i];i++)if(token[i]>='A' && token[i]<='Z')token[i]+='a'-'A';
        keyline_add(row,sizeof(row),token);
    }
    if(item && inventory_droppable(item)){
        win_key_words(aw_key_inv_drop.string,keys,sizeof(keys));
        Q_snprintf(token,sizeof(token),"%s drop",keys);keyline_add(row,sizeof(row),token);
    }
    /* Turning belongs to the old live preview only (UI-INVENTORY-PREVIEW-STILL-42). */
    if(AW_ViewInventoryLive())keyline_add(row,sizeof(row),"Left/Right turn");
    inventory_text(132,INV_CONTROLS_Y+8,180,5,row,gold);
    /* INVENTORY-ITEM-INFO-67: the information key on the first row, after the category key, while an item is chosen */
    if(item){
        win_key_words(aw_key_inv_info.string,keys,sizeof(keys));
        Q_snprintf(token,sizeof(token),"%s info",keys);inventory_text(252,INV_CONTROLS_Y,60,5,token,gold);
    }
}
static void inventory_draw(void){
    int i,j,x,row,index,right=inventory_list_right();aw_inventory_item_t *item;char line[160];
    int gold=AW_UIColor(223,199,144),muted=AW_UIColor(150,135,104);
    inventory_watch();
    right=inventory_list_right();   /* the list may have changed its length */
    AW_UIFill(0,0,320,200,AW_UIColor(0,0,0));AW_UIBox(2,2,316,196);
    AW_UIBox(4,18,122,178);AW_UIBox(128,18,188,178);
    AW_UISmallBegin();
    window_title(6,6,308,inventory_title(),gold);
    AW_UISmallEnd();
    inventory_preview(muted);
    inventory_burden();
    inventory_armor();
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
        int worn;
        item=inventory_item(row,NULL);if(!item)break;
        worn=AW_InventoryEquipped(&aw_state,item->id)>0;
        if(row==inventory->selected)AW_UIFill(130,INV_LIST_Y+i*INV_ROW_H,right-130,INV_ROW_H,AW_UIColor(44,36,20));
        inventory_icon(i,row,132,INV_LIST_Y+i*INV_ROW_H);
        /* INVENTORY-EQUIPPED-LABEL-67: a worn or held item says "Equipped" in the highlight colour at the end of its
         * name's column (the name gives it the room; it was a "* " before the name) */
        inventory_text(151,INV_LIST_Y+i*INV_ROW_H,right-24-151-(worn?INV_EQUIPPED_W:0),11,item->name,gold);
        if(worn)inventory_text(right-24-INV_EQUIPPED_W+4,INV_LIST_Y+i*INV_ROW_H,INV_EQUIPPED_W-4,11,"Equipped",
                               INV_EQUIPPED_COLOUR);
        /* DBG-GIVE-MONEY-62: four characters at most (1000000 gold: "1m"), the column holds five */
        AW_InventoryCountText((long)AW_StateGet(&aw_state,AW_ITEM,item->id),line,sizeof(line));
        inventory_text(right-22,INV_LIST_Y+i*INV_ROW_H,22,11,line,gold);
    }
    if(inventory->count>INV_VISIBLE)
        AW_UIScrollbar(INV_SCROLL_X,INV_LIST_Y,INV_SCROLL_H,inventory->count,INV_VISIBLE,inventory->top);
    index=0;item=inventory->count?inventory_item(inventory->selected,&index):NULL;
    if(item){
        if(index)sprintf(line,"Weight %.2f  Value %ld",item->weight,(long)item->value);
        else strcpy(line,"Item details unavailable");
        inventory_text(132,INV_DETAILS_Y,180,8,line,muted);
        {   /* the status line: an action's result for a few seconds (INVENTORY-EQUIP-HINTS-67), else whether the right
             * button has anything to offer; the action itself is in the key line below */
            int what[INV_MENU];const char *words[INV_MENU],*said=inventory_message();
            inventory_status(said?said:inventory_menu(item,what,words)>1?"RMB actions":"Actions unavailable for this item",muted);
        }
    }else if(inventory_message())inventory_status(inventory_message(),muted);
    if(inventory->context && item){
        int what[INV_MENU],n;const char *words[INV_MENU];
        n=inventory_menu(item,what,words);
        x=inventory->context_x;j=inventory->context_y;
        if(n){
            AW_UIFill(x,j,110,n*16,AW_UIColor(10,9,7));AW_UIBox(x,j,110,n*16);
            for(row=0;row<n;row++)inventory_text(x+4,j+row*16+2,102,13,words[row],gold);
        }else inventory->context=0;
    }
    /* Frame bottom pixels are 192..195: all footer glyphs finish by188. */
    AW_UIFill(132,INV_CONTROLS_Y-2,180,1,muted);
    inventory_text(INV_CLOSE_X,INV_CONTROLS_Y,INV_CLOSE_W,5,"I/Esc close",gold);
    inventory_text(192,INV_CONTROLS_Y,120,5,"Tab category",gold);
    inventory_keyline(item,gold);
    /* INVENTORY-DOUBLECLICK-62: the consumable's box over the list, else the short equip notice */
    if(inventory->confirm)inventory_confirm_draw(gold,muted);else inventory_notice_draw(gold);
    if(inventory->info)AW_ItemInfoDraw(inventory->info,mouse_x,mouse_y);   /* INVENTORY-ITEM-INFO-67: over it all */
}
static void map_fit(void){
    float sx=(float)map_w/(view_w-2),sy=(float)map_h/(view_h-4);   /* version 1: 310 x 150 */
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
    if(map_v2)return 1;   /* MAP-VERSION-2-DEFAULT-68: version 2 is the in-game view only; aw_map_mode is version 1's */
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
/* case-insensitive: does the cell name TEXT start with PART (ShowMap's rule: OpenMW guiextensions.cpp OpShowMap,
 * Misc::StringUtils::ciStartsWith; "Vivec" reveals "Vivec" and "Vivec, Arena"). MAP-PLACES-SHOWN-UNVISITED-67: it used to
 * match a name that holds PART anywhere, so ShowMap Vos revealed Tel Vos as well (the one such case in Morrowind.esm). */
static int ci_starts(const char *text,const char *part){
    int j;
    if(!*part)return 0;
    for(j=0;part[j] && text[j] && tolower((unsigned char)text[j])==tolower((unsigned char)part[j]);j++){}
    return !part[j];
}
/* The place markers from world/region-names.awn (ARN2: names, places, cells; 64-byte labels; rows <iiII> x, y,
 * region, place). Bounded: 128 groups; a missing or bad file leaves the map without markers. */
/* MAP-PLACE-HIDDEN-IN-ITS-OWN-CELL-68: a place is known on the map as soon as any one of its own cells holds explored
 * land, as the original shows a place once the player has been in it; before, only the explored state of the place's
 * averaged marker spot counted, so a place whose cells spread (Raven Rock) stayed hidden while the player stood in it.
 * The explored mask is built before the places when the map opens (below), so the cells are tested as they are read. */
static int fog_open(int gx,int gy);
static int place_cell_explored(int32_t cx,int32_t cy){
    int gx0,gy0,gx,gy;
    if(!fog_mask)return 0;
    gx0=(int)cx*AW_MAPFOG_GRID-fog_gx0;gy0=(int)cy*AW_MAPFOG_GRID-fog_gy0;
    for(gy=0;gy<AW_MAPFOG_GRID;gy++)for(gx=0;gx<AW_MAPFOG_GRID;gx++)if(fog_open(gx0+gx,gy0+gy))return 1;
    return 0;
}
static void map_places_load(void){
    FILE *f=NULL;byte head[16],row[16];char *labels=NULL;short *group=NULL;long base;
    int size,i,j,k,n;unsigned names,places,cells,where;const char *cut;map_place_t *m;
    free(map_places);map_places=NULL;map_place_count=0;map_place_hover=-1;
    size=COM_FOpenFile("world/region-names.awn",&f);
    if(!f)return;
    base=ftell(f);
    if(base<0 || size<16 || fread(head,1,16,f)!=16 || memcmp(head,"ARN2",4))goto done;
    names=u32(head+4);places=u32(head+8);cells=u32(head+12);
    if(names>1024 || places<1 || places>1024 || cells>65536 || size!=16+(long)(names+places)*64+(long)cells*16)goto done;
    labels=(char *)AW_TryMalloc((unsigned long)places*64);group=(short *)AW_TryMalloc((unsigned long)places*sizeof(short));
    map_places=(map_place_t *)AW_TryMalloc(sizeof(map_place_t)*MAP_PLACES_MAX);
    if(!labels || !group || !map_places)goto fail;
    memset(map_places,0,sizeof(map_place_t)*MAP_PLACES_MAX);
    if(fseek(f,base+16+(long)names*64,SEEK_SET) || fread(labels,64,places,f)!=places)goto fail;
    for(i=0;i<(int)places;i++){
        char *label=labels+i*64;
        if(!memchr(label,0,64))goto fail;
        cut=strchr(label,',');n=cut?(int)(cut-label):(int)strlen(label);
        while(n>0 && label[n-1]==' ')n--;
        if(n>31)n=31;
        group[i]=-1;if(n<1)continue;
        for(j=0;j<map_place_count;j++)if(!strncmp(map_places[j].name,label,(size_t)n) && !map_places[j].name[n])break;
        if(j==map_place_count){
            if(map_place_count>=MAP_PLACES_MAX)continue;   /* past the bound: that place has no marker */
            memcpy(map_places[j].name,label,(size_t)n);map_places[j].name[n]=0;map_place_count++;
        }
        group[i]=(short)j;
        for(k=0;k<AW_RevealedCount();k++){const char *r=AW_RevealedAt(k);if(r && ci_starts(label,r)){map_places[j].known=1;break;}}
    }
    for(i=0;i<(int)cells;i++){
        if(fread(row,1,16,f)!=16)goto fail;
        where=u32(row+12);if(where==0xFFFFFFFFu)continue;
        if(where>=places)goto fail;
        if(group[where]<0)continue;
        m=&map_places[group[where]];
        m->x+=((int32_t)u32(row)+.5f)*8192.0f;m->y+=((int32_t)u32(row+4)+.5f)*8192.0f;m->cells++;
        if(!m->known && place_cell_explored((int32_t)u32(row),(int32_t)u32(row+4)))m->known=1;
    }
    for(i=j=0;i<map_place_count;i++){
        if(!map_places[i].cells)continue;
        map_places[j]=map_places[i];map_places[j].x/=map_places[j].cells;map_places[j].y/=map_places[j].cells;j++;
    }
    map_place_count=j;
    goto done;
 fail:
    free(map_places);map_places=NULL;map_place_count=0;
 done:
    free(labels);free(group);
    fclose(f);
}
static void map_fog_build(void){
    const float square=AW_MAPFOG_CELL/AW_MAPFOG_GRID;int i,j,k,x,y,gx,gy,gx1,gy1;const unsigned char *bits;
    free(fog_mask);fog_mask=NULL;fog_x0=fog_y0=0;fog_x1=fog_y1=-1;
    fog_gx0=(int)floor(map_bounds[0]/square);gx1=(int)floor((map_bounds[2]-1)/square);
    fog_gy0=(int)floor(map_bounds[1]/square);gy1=(int)floor((map_bounds[3]-1)/square);
    fog_w=gx1-fog_gx0+1;fog_h=gy1-fog_gy0+1;
    if(fog_w<1 || fog_h<1 || fog_w>2048 || fog_h>2048)return;
    if(!(fog_mask=(byte *)AW_TryMalloc((unsigned long)(fog_w*fog_h+7)/8)))return;   /* no mask: nothing explored */
    memset(fog_mask,0,(size_t)(fog_w*fog_h+7)/8);
    for(i=0;AW_MapFogRow(i,&x,&y,&bits);i++)
        for(j=0;j<AW_MAPFOG_GRID;j++)for(k=0;k<AW_MAPFOG_GRID;k++){
            int bit=j*AW_MAPFOG_GRID+k;
            if(!((bits[bit>>3]>>(bit&7))&1))continue;
            gx=x*AW_MAPFOG_GRID+k-fog_gx0;gy=y*AW_MAPFOG_GRID+j-fog_gy0;
            if(gx<0 || gy<0 || gx>=fog_w || gy>=fog_h)continue;
            bit=gy*fog_w+gx;fog_mask[bit>>3]|=(byte)(1<<(bit&7));
            if(fog_x1<fog_x0){fog_x0=fog_x1=gx;fog_y0=fog_y1=gy;}
            else{if(gx<fog_x0)fog_x0=gx;if(gx>fog_x1)fog_x1=gx;if(gy<fog_y0)fog_y0=gy;if(gy>fog_y1)fog_y1=gy;}
        }
}
/* 1 when the fog square (mask column GX, row GY) is explored */
static int fog_open(int gx,int gy){
    int bit;
    if(!fog_mask || gx<0 || gy<0 || gx>=fog_w || gy>=fog_h)return 0;
    bit=gy*fog_w+gx;return (fog_mask[bit>>3]>>(bit&7))&1;
}
static int fog_open_at(float x,float y){
    const float square=AW_MAPFOG_CELL/AW_MAPFOG_GRID;
    return fog_open((int)floor(x/square)-fog_gx0,(int)floor(y/square)-fog_gy0);
}
/* MAP-ORIGINAL-POI-66 stage 3: the local map (OpenMW's map window: a Local and a World view; inside, the local view is
 * the room's own map). Outdoors the local view is the world map at the zoom where about the 3 x 3 cells around the
 * player fill the window, with the doors of the loaded scene. Inside, the room's top-down plan is drawn once when the
 * map opens from the loaded map's own faces (walls bright, floors dim, ceilings left out) into a 312 x 154 picture
 * (48,048 bytes, freed on close; no file read), under the room's own fog (aw_mapfog.c AW_MapFogRoom*), with the
 * room's doors named on mouse-over after where they lead (docs/WORLD_MAP_AND_JOURNAL.md "Local map"). */
/* MAP-VERSION-2-DEFAULT-68: the plan is the map picture's size of the version open (version 1 312 x 154, version 2
 * 304 x 148), set when it is built */
static int local_w=312,local_h=154;
#define LOCAL_W local_w
#define LOCAL_H local_h
#define LOCALBTN_WORLD_X 168
#define LOCALBTN_LOCAL_X 208
#define LOCALBTN_W 38
static void local_line(int x0,int y0,int x1,int y1,int color){
    int dx=abs(x1-x0),sx=x0<x1?1:-1,dy=-abs(y1-y0),sy=y0<y1?1:-1,error=dx+dy,e2,n=0;
    for(;n<2048;n++){
        if(x0>=0 && x0<LOCAL_W && y0>=0 && y0<LOCAL_H)local_pixels[y0*LOCAL_W+x0]=(byte)color;
        if(x0==x1 && y0==y1)break;
        e2=2*error;if(e2>=dy){error+=dy;x0+=sx;}if(e2<=dx){error+=dx;y0+=sy;}
    }
}
/* the room's point X, Y (engine units) on the screen */
static void local_to_screen(float x,float y,int *mx,int *my){
    *mx=view_x+(int)floor(local_ox+(x-local_min[0])*local_scale);*my=view_y+(int)floor(local_oy+(local_max[1]-y)*local_scale);
}
static void local_build(void){
    model_t *m=sv.worldmodel;int i,j,edges=0,faces=0,wall=AW_UIColor(232,214,160),floorc=AW_UIColor(110,92,58);
    float w,h,nz;double t0=Sys_FloatTime();
    local_free();
    local_w=view_w;local_h=view_h;   /* MAP-VERSION-2-DEFAULT-68: the picture of the version open */
    if(!sv.active || !m || m->type!=mod_brush || m->numsurfaces<1 || !AW_Interior())return;
    local_min[0]=m->mins[0];local_min[1]=m->mins[1];local_max[0]=m->maxs[0];local_max[1]=m->maxs[1];
    w=local_max[0]-local_min[0];h=local_max[1]-local_min[1];
    if(!(w>=1 && h>=1 && w<1e6f && h<1e6f))return;
    if(!(local_pixels=(byte *)AW_TryMalloc(LOCAL_W*LOCAL_H)))return;
    memset(local_pixels,AW_UIColor(15,20,23),LOCAL_W*LOCAL_H);
    local_scale=(LOCAL_W-8)/w<(LOCAL_H-8)/h?(LOCAL_W-8)/w:(LOCAL_H-8)/h;
    local_ox=(LOCAL_W-w*local_scale)*.5f;local_oy=(LOCAL_H-h*local_scale)*.5f;
    for(i=0;i<m->numsurfaces;i++){
        msurface_t *s=&m->surfaces[i];int color,x0=0,y0=0,first=1,fx=0,fy=0;
        if(!s->plane || s->numedges<2)continue;
        nz=s->plane->normal[2];if(s->flags&SURF_PLANEBACK)nz=-nz;
        if(nz<-.7f)continue;                                  /* a ceiling: not on a plan */
        color=nz>.7f?floorc:nz>-.3f && nz<.3f?wall:floorc;
        faces++;
        for(j=0;j<s->numedges;j++){
            int e=m->surfedges[s->firstedge+j];const float *v;int x,y;
            v=m->vertexes[m->edges[e<0?-e:e].v[e<0?1:0]].position;
            x=(int)floor(local_ox+(v[0]-local_min[0])*local_scale);y=(int)floor(local_oy+(local_max[1]-v[1])*local_scale);
            if(first){fx=x;fy=y;first=0;}else{local_line(x0,y0,x,y,color);edges++;}
            x0=x;y0=y;
        }
        local_line(x0,y0,fx,fy,color);edges++;
    }
    local_room=1;strncpy(local_name,sv.name,sizeof(local_name)-1);local_name[sizeof(local_name)-1]=0;
    Con_Printf("Local map: %s, %d faces, %d edges, %d bytes, %d ms.\n",sv.name,faces,edges,LOCAL_W*LOCAL_H,
        (int)((Sys_FloatTime()-t0)*1000));
}
/* outdoors: the zoom where about 3 x 3 cells fill the window, centred on the player */
static void local_zoom(void){
    float cells=map_w*(3*AW_MAPFOG_CELL)/(float)(map_bounds[2]-map_bounds[0]),want=cells/(view_w-2),base;int z;
    zoom=0;map_fit();base=map_step;
    for(z=0;z<5 && base/(1<<(z+1))>=want*.75f;z++){}
    zoom=z;map_fit();map_player();
}
/* MAP-WORLD-TAB-BLANK-67: the in-game World view, the first time it shows the player in a game, is centred on the player
 * (OpenMW centres its world map on the player: mapwindow.cpp MapWindow::centerView) at the closest zoom, at most the
 * Local view's, that still holds all the explored land around the player. It used to open at the whole-island fit
 * (zoom 0: about 3 pixels a cell), where a new game's explored land is a few pixels wide and lies under the player's
 * 16-pixel arrow: the World tab looked empty until the Local view had changed the zoom (v0.0.66-dev2 to v0.0.67-dev1,
 * since the explored land hides the rest). Later showings keep the player's zoom and only centre on the player. */
static void map_explored_view(void){
    const float square=AW_MAPFOG_CELL/AW_MAPFOG_GRID;float kx,ky,rx,ry,base;int z,top;
    local_zoom();top=zoom;                     /* about 3 x 3 cells, on the player: nothing explored yet stays here */
    if(fog_x1<fog_x0)return;
    kx=map_w/(float)(map_bounds[2]-map_bounds[0]);ky=map_h/(float)(map_bounds[3]-map_bounds[1]);
    /* map pixels from the player to the farthest explored edge, across and up or down */
    rx=player_x-(fog_gx0+fog_x0)*square;if((fog_gx0+fog_x1+1)*square-player_x>rx)rx=(fog_gx0+fog_x1+1)*square-player_x;
    ry=player_y-(fog_gy0+fog_y0)*square;if((fog_gy0+fog_y1+1)*square-player_y>ry)ry=(fog_gy0+fog_y1+1)*square-player_y;
    rx*=kx;ry*=ky;
    zoom=0;map_fit();base=map_step;
    /* half the view less a margin (version 1: 156 x 77 pixels, so 150 x 74) */
    for(z=top;z>0;z--)if(rx*(1<<z)<=(view_w/2-6)*base && ry*(1<<z)<=(view_h/2-3)*base)break;
    zoom=z;map_fit();map_player();
}
/* the in-game World view placed on the player once a game (open_map, the World tab, the IN-GAME button all lead here:
 * AW_WorldUIDraw calls it before the view is drawn); afterwards centred on the player at each open (open_map) */
static void map_world_place(void){
    if(map_world_placed || teleport_mode || !marker || map_local || !map_in_game())return;
    map_explored_view();map_world_placed=1;
}
static void map_set_local(int local){
    map_local=local && !teleport_mode;
    if(!AW_Interior())map_local_choice=map_local;
    if(map_local && !local_room && !AW_Interior() && marker)local_zoom();
    else if(!map_local && !marker)map_home();
}
/* MAP-VERSION-2-DEFAULT-68: the version this opening shows and its picture's rectangle */
static void map_view_set(void){
    map_v2=aw_map_version.value!=1 && !teleport_opening;
    if(map_v2){
        view_x=4+AW_UI_FRAME_EDGE;view_y=MAPV2_MAP_BOX_Y+AW_UI_FRAME_EDGE;
        view_w=312-2*AW_UI_FRAME_EDGE;view_h=MAPV2_MAP_BOX_H-2*AW_UI_FRAME_EDGE;
    }else{view_x=4;view_y=19;view_w=312;view_h=154;}
}
/* MAP-VERSION-2-DEFAULT-68: the title, as the original names the cell the player is in (OpenMW mwworld/worldimp.cpp
 * World::getCellName, the map window's caption through mwgui/windowmanagerimp.cpp changeCell): a room's own name (its
 * map's _aw_cell_id, aw_hud.c AW_HudPlayerCell), outdoors the cell's own name, else its region's name exactly as the
 * game data has it (aw_world.c AW_CellNameAt: no expansion tag), else the GMST sDefaultCellname's value, "Wilderness";
 * "Map" (the GMST sMap) when neither the room nor an outdoor position is known. Then its font: the game's own (the
 * inventory title's) when it fits the plaque, else the console glyphs (aw_layout.c AW_LayoutTitle). Once an opening. */
static void map_title_set(void){
    long x=0,y=0;char id[64];const char *region,*name;float p[3];int game_w;
    switch(AW_HudPlayerCell(&x,&y,id,sizeof(id),&region)){
    case 2:name=id;break;
    case 1:p[0]=(x+.5f)*8192.0f;p[1]=(y+.5f)*8192.0f;p[2]=0;name=AW_CellNameAt(p);if(!name || !*name)name="Wilderness";break;
    default:name="Map";
    }
    strncpy(map_name,name,sizeof(map_name)-1);map_name[sizeof(map_name)-1]=0;
    AW_UISmallBegin();game_w=AW_UIWidth(map_name);AW_UISmallEnd();
    AW_LayoutTitle(&map_name_fit,308,game_w,(int)strlen(map_name));
}
static void open_map(void){
    FILE *f=NULL;int size,i,off,version;byte *p;
    if(!menu_allowed(AW_MENU_MAP))return;   /* the teleport map checked the full rule before calling */
    map_view_set();
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
    map_fog_build();map_places_load();local_build();   /* the mask first: the places test their cells against it */
    if(!map_view_ready){map_home();map_view_ready=1;}else map_fit();
    /* stage 3: inside, always the room's own map; outdoors the view last chosen there */
    if(local_room){
        map_local=1;
        AW_MapFogRoomReveal(sv.name,svs.clients[0].edict->v.origin[0],svs.clients[0].edict->v.origin[1],local_min,local_max);
    }else{map_local=0;if(map_local_choice && marker)map_set_local(1);}
    /* MAP-WORLD-TAB-BLANK-67: the World view, once placed in this game, opens centred on the player at the zoom kept
     * (OpenMW MapWindow::centerView); its first placement waits for the first draw (map_world_place) */
    if(map_world_placed && !map_local && marker && map_in_game())map_player();
    if(map_v2)map_title_set();
    mm_close_all();mm_max();mm_migrate();
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
    /* a script's DisablePlayerControls keeps the player's own windows shut (OpenMW playercontrols.lua uiAllowed) */
    if(!menu_allowed(AW_MENU_MAP) || !AW_ControlAllowed(AW_CONTROL_PLAYER))return;
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
static int clear_button_hit(void){   /* version 1's MARKERS button (version 2: its footer tab) */
    return !map_v2 && mouse_x>=CLEAR_X && mouse_x<CLEAR_X+CLEAR_W && mouse_y>=CLEAR_Y && mouse_y<CLEAR_Y+CLEAR_H;
}
/* the pointer over the map picture (MAP-VERSION-2-DEFAULT-68: the version open's rectangle) */
static int in_view(void){return mouse_x>=view_x && mouse_x<view_x+view_w && mouse_y>=view_y && mouse_y<view_y+view_h;}
/* Both picks use the exact AWM1 texture-to-original-source transform. */
static int map_source_at(float point[3]){
    float px=map_x-(view_w/2)*map_step+(mouse_x-view_x)*map_step;
    float py=map_y-(view_h/2)*map_step+(mouse_y-view_y)*map_step;
    if(!in_view() || px<0 || px>=map_w || py<0 || py>=map_h)return 0;
    point[0]=map_bounds[0]+px*(map_bounds[2]-map_bounds[0])/map_w;
    point[1]=map_bounds[3]-py*(map_bounds[3]-map_bounds[1])/map_h;
    point[2]=0;return 1;
}
/* MAP-MULTI-MARKERS-66 and NAV-HOT-MARKER-COMPASS-66: the player's named markers (up to aw_map_markers_max, 256 by
 * default) and the one hot marker, kept by aw_mapmarks.c and saved in their own block (AWMK). On the map: right click
 * on the map sets a named marker at once (named after the region, else the nearest place); left click on a marker
 * opens its box (the name, OK / Cancel / Delete); left drag pans; H sets the hot marker at the pointer (H on it
 * clears it); K (or the MARKERS button) opens the Markers menu. The old single marker (globals
 * amiwind:map:marker:x/y/ready) becomes marker 1 once. Every box is laid out by the box pipeline (AW_MsgBoxLayout). */
static cvar_t aw_map_markers_max={"aw_map_markers_max","256",true};
static cvar_t aw_compass={"aw_compass","0",true};
#define MM_ROWS 10
static int mm_edit=-1,mm_edit_len,mm_menu,mm_sort,mm_confirm;
static char mm_text[AW_MAPMARK_NAME+1];
static aw_listbox_t mm_box;
/* while the menu is open (one block of 3 KB, taken when it opens, freed when it closes): the rows' sorted order, the
 * rows the Find line keeps, and the region names looked up when it opens or changes */
static int *mm_order,*mm_shown;
static const char **mm_regions;
static void *mm_block;
static const char *const mm_edit_buttons[3]={"OK","Cancel","Delete"};
static const char *const mm_menu_buttons[6]={"Centre","Rename","Follow","Delete","Remove all","Close"};
static const char *const mm_yes_no[2]={"Yes","No"};
static void mm_max(void){AW_MapMarksSetMax((int)aw_map_markers_max.value);}
static void source_to_screen(float x,float y,int *mx,int *my){
    float left=map_x-(view_w/2)*map_step,top=map_y-(view_h/2)*map_step;
    float px=(x-map_bounds[0])*map_w/(map_bounds[2]-map_bounds[0]),py=(map_bounds[3]-y)*map_h/(map_bounds[3]-map_bounds[1]);
    *mx=view_x+(int)((px-left)/map_step);*my=view_y+(int)((py-top)/map_step);
}
static int map_point_inside(float x,float y){
    return x>=map_bounds[0] && x<map_bounds[2] && y>map_bounds[1] && y<=map_bounds[3];
}
/* the default name: the region at the point, else the nearest known place of the open map, else "Marker N" */
static const char *mm_default_name(const float *point){
    const char *r=AW_RegionNameAt(point);int i,best=-1;float bd=0,d;
    if(r && *r)return r;
    for(i=0;i<map_place_count;i++){
        d=(map_places[i].x-point[0])*(map_places[i].x-point[0])+(map_places[i].y-point[1])*(map_places[i].y-point[1]);
        if(best<0 || d<bd){best=i;bd=d;}
    }
    return best>=0?map_places[best].name:NULL;
}
/* the old single marker (MAP-MARKER-29, globals) carried into the list once */
static void mm_migrate(void){
    float p[3];
    if(AW_StateGet(&aw_state,AW_GLOBAL,marker_keys[2])!=1)return;
    p[0]=(float)AW_StateGet(&aw_state,AW_GLOBAL,marker_keys[0]);p[1]=(float)AW_StateGet(&aw_state,AW_GLOBAL,marker_keys[1]);p[2]=0;
    if(AW_MapMarkAdd(p[0],p[1],mm_default_name(p))>=0){
        AW_StateSet(&aw_state,AW_GLOBAL,marker_keys[2],0);Con_Printf("Map marker: the old marker is marker %d now.\n",AW_MapMarksCount());
    }
}
/* MAP-WORLD-TAB-BLANK-67: a loaded or a new game places the in-game World view on the player again (map_world_place) */
static void mm_loaded(void){AW_MapMarksLoaded();mm_max();mm_migrate();map_world_placed=0;}
static void mm_reset(void){mm_close_all();AW_MapMarksReset();map_world_placed=0;}
static int mm_at_pointer(void){
    int i,mx,my,d,best=17,hit=-1;const aw_mapmark_t *m;
    for(i=0;(m=AW_MapMark(i))!=NULL;i++){
        if(!map_point_inside(m->x,m->y))continue;
        source_to_screen(m->x,m->y,&mx,&my);d=(mx-mouse_x)*(mx-mouse_x)+(my-mouse_y)*(my-mouse_y);
        if(d<best){best=d;hit=i;}
    }
    return hit;
}
static int mm_hot_at_pointer(void){
    float x,y;int mx,my;
    if(!AW_MapHotGet(&x,&y))return 0;
    source_to_screen(x,y,&mx,&my);return (mx-mouse_x)*(mx-mouse_x)+(my-mouse_y)*(my-mouse_y)<17;
}
static void place_marker(void){
    float point[3];int i;
    mm_max();
    if(!map_source_at(point)){marker_message="Outside map bounds";return;}
    point[0]=(float)minmax((int)floor(point[0]+.5f),map_bounds[0],map_bounds[2]-1);
    point[1]=(float)minmax((int)floor(point[1]+.5f),map_bounds[1]+1,map_bounds[3]);
    i=AW_MapMarkAdd(point[0],point[1],mm_default_name(point));
    if(i==-1){marker_message="Markers full (aw_map_markers_max)";return;}
    if(i<0){marker_message="Marker not set: not enough memory";return;}
    marker_message=NULL;
    Con_Printf("Map marker %d: %s at %ld %ld.\n",i+1,AW_MapMark(i)->name,(long)point[0],(long)point[1]);
}
static void mm_hot_key(void){
    float point[3];
    if(mm_hot_at_pointer()){AW_MapHotOff();marker_message="Hot marker cleared";return;}
    if(!map_source_at(point)){marker_message="Outside map bounds";return;}
    AW_MapHotSet((float)floor(point[0]+.5f),(float)floor(point[1]+.5f));marker_message="Hot marker set";
}
static void mm_centre(int i){
    const aw_mapmark_t *m=AW_MapMark(i);
    if(!m)return;
    if(map_local)map_set_local(0);
    map_x=(m->x-map_bounds[0])*map_w/(map_bounds[2]-map_bounds[0]);
    map_y=(map_bounds[3]-m->y)*map_h/(map_bounds[3]-map_bounds[1]);
}
/* the Markers menu's rows: sorted by name or by region; the Find line filters on both (aw_listbox_rules.c) */
static int mm_casecmp(const char *a,const char *b){
    for(;*a || *b;a++,b++){int x=tolower((unsigned char)*a),y=tolower((unsigned char)*b);if(x!=y)return x-y;}
    return 0;
}
static const char *mm_region(int i){return mm_regions && mm_regions[i]?mm_regions[i]:"";}
static int mm_cmp(const void *a,const void *b){
    int i=*(const int *)a,j=*(const int *)b,c=0;
    if(mm_sort)c=mm_casecmp(mm_region(i),mm_region(j));
    if(!c)c=mm_casecmp(AW_MapMark(i)->name,AW_MapMark(j)->name);
    return c?c:i-j;
}
static const char *mm_label(void *ctx,int row){
    static char s[AW_MAPMARK_NAME+80];const aw_mapmark_t *m=AW_MapMark(mm_order[row]);
    (void)ctx;
    if(!m)return "";
    snprintf(s,sizeof(s),"%s %s",m->name,mm_region(mm_order[row]));return s;
}
static void mm_refresh(void){
    int i,n=AW_MapMarksCount(),keep=AW_ListBoxSelected(&mm_box);char search[AW_LISTBOX_SEARCH+1];
    float p[3];
    strcpy(search,mm_box.search);
    for(i=0;i<n;i++){
        mm_order[i]=i;
        if(mm_regions){p[0]=AW_MapMark(i)->x;p[1]=AW_MapMark(i)->y;p[2]=0;mm_regions[i]=AW_RegionNameAt(p);}
    }
    qsort(mm_order,(size_t)n,sizeof(int),mm_cmp);
    AW_ListBoxReset(&mm_box,n,mm_label,NULL,mm_shown,MM_ROWS);
    strcpy(mm_box.search,search);AW_ListBoxFilter(&mm_box);
    if(keep>=0 && keep<mm_box.shown_count)mm_box.selection=keep;
}
static void mm_menu_open(void){
    /* the tables hold the allowance (3 KB at the default 256), or the markers now when a lowered allowance left more */
    int room=AW_MapMarksMax()>AW_MapMarksCount()?AW_MapMarksMax():AW_MapMarksCount();
    if(mm_menu)return;
    if(room<1)room=1;
    mm_block=AW_TryMalloc((unsigned long)room*(2*sizeof(int)+sizeof(*mm_regions)));
    if(!mm_block){marker_message="Markers menu: not enough memory";return;}
    mm_regions=(const char **)mm_block;mm_order=(int *)(mm_regions+room);mm_shown=mm_order+room;
    mm_menu=1;mm_confirm=0;mm_edit=-1;drag=marker_click=0;mm_box.search[0]=0;mm_box.selection=0;
    AW_ListBoxReset(&mm_box,0,mm_label,NULL,mm_shown,MM_ROWS);mm_refresh();
}
static void mm_menu_close(void){free(mm_block);mm_block=NULL;mm_regions=NULL;mm_order=mm_shown=NULL;mm_menu=mm_confirm=0;}
static void mm_close_all(void){mm_menu_close();mm_edit=-1;}
static int mm_selected(void){int r=AW_ListBoxSelected(&mm_box);return r>=0?mm_order[r]:-1;}
static void mm_edit_open(int i){
    const aw_mapmark_t *m=AW_MapMark(i);
    if(!m)return;
    mm_edit=i;strcpy(mm_text,m->name);mm_edit_len=(int)strlen(mm_text);drag=marker_click=0;
}
static void mm_edit_close(int button){   /* 0 OK, 1 Cancel, 2 Delete */
    if(button==0)AW_MapMarkRename(mm_edit,mm_text);
    else if(button==2)AW_MapMarkDelete(mm_edit);
    mm_edit=-1;
    if(mm_menu)mm_refresh();
}
static void mm_delete(int i){if(AW_MapMarkDelete(i) && mm_menu)mm_refresh();}
/* the box pipeline: the frame of a box of COUNT buttons and LINES console lines, its buttons sized to their labels */
static void mm_frame(int count,int lines,int frame[4]){AW_MsgBoxLayout(count,320,200,lines*10,frame);}
static void mm_widths(const char *const *labels,int count,int *w){
    int i;for(i=0;i<count;i++)w[i]=(int)strlen(labels[i])*AW_ConsoleCharWidth();
}
static int mm_button_at(const char *const *labels,int count,int lines){
    int frame[4],w[AW_MSGBOX_BUTTONS];
    mm_frame(count,lines,frame);mm_widths(labels,count,w);return AW_MsgBoxButtonAtSized(count,frame,w,mouse_x,mouse_y);
}
static void mm_box_draw(const char *const *labels,int count,int lines,int frame[4]){
    int i,r[4],w[AW_MSGBOX_BUTTONS],edge=AW_UIColor(202,165,96);
    mm_frame(count,lines,frame);mm_widths(labels,count,w);
    AW_UIFill(frame[0],frame[1],frame[2],frame[3],edge);AW_UIFill(frame[0]+1,frame[1]+1,frame[2]-2,frame[3]-2,AW_UIColor(15,20,23));
    for(i=0;i<count;i++){
        AW_MsgBoxButtonRectSized(count,i,frame,w,r);
        AW_UIFill(r[0],r[1]+5,r[2],12,AW_UIColor(44,36,20));
        text(r[0]+(r[2]-w[i])/2,r[1]+7,labels[i],r[0]+r[2]-1);
    }
}
static void mm_draw(void){
    int frame[4],i,y,cw=AW_ConsoleCharWidth();char line[AW_MAPMARK_NAME+80];
    if(mm_menu){
        mm_box_draw(mm_menu_buttons,6,MM_ROWS+2,frame);
        snprintf(line,sizeof(line),"MARKERS %d/%d  Sort: %s (Tab)",AW_MapMarksCount(),AW_MapMarksMax(),mm_sort?"region":"name");
        text(frame[0]+8,frame[1]+8,line,frame[0]+frame[2]-8);
        snprintf(line,sizeof(line),"Find: %s_",mm_box.search);text(frame[0]+8,frame[1]+18,line,frame[0]+frame[2]-8);
        for(i=0;i<MM_ROWS && mm_box.top+i<mm_box.shown_count;i++){
            int k=mm_order[mm_shown[mm_box.top+i]],right=frame[0]+frame[2]-8,rw;const char *reg=mm_region(k);
            y=frame[1]+28+i*10;
            if(mm_box.top+i==mm_box.selection)AW_UIFill(frame[0]+6,y-1,frame[2]-12,10,AW_UIColor(44,36,20));
            text(right-3*cw,y,"Del",right);
            rw=(int)strlen(reg)*cw;if(rw>(frame[2]-16)/2)rw=(frame[2]-16)/2;
            text(right-4*cw-rw,y,reg,right-4*cw);
            text(frame[0]+8,y,AW_MapMark(k)->name,right-5*cw-rw);
        }
        if(!mm_box.shown_count)text(frame[0]+8,frame[1]+28,AW_MapMarksCount()?"No marker matches":"No markers: right click on the map",frame[0]+frame[2]-8);
    }
    if(mm_confirm){
        mm_box_draw(mm_yes_no,2,1,frame);
        snprintf(line,sizeof(line),"Remove all %d markers?",AW_MapMarksCount());text(frame[0]+8,frame[1]+8,line,frame[0]+frame[2]-8);
    }
    if(mm_edit>=0){
        mm_box_draw(mm_edit_buttons,3,2,frame);
        text(frame[0]+8,frame[1]+8,"Marker name:",frame[0]+frame[2]-8);
        snprintf(line,sizeof(line),"%s_",mm_text);text(frame[0]+8,frame[1]+18,line,frame[0]+frame[2]-8);
    }
}
static void mm_remove_all(void){AW_MapMarksClear();mm_confirm=0;if(mm_menu)mm_refresh();marker_message="Markers removed";}
/* a key while a marker box or the menu is up: 1 when it took the key (every key, so the map under it rests) */
static int mm_key(int key){
    int b,frame[4];
    if(mm_edit>=0){
        if(key==K_ENTER)mm_edit_close(0);
        else if(key==K_ESCAPE)mm_edit_close(1);
        else if(key==K_BACKSPACE){if(mm_edit_len)mm_text[--mm_edit_len]=0;}
        else if(key==K_MOUSE1){if((b=mm_button_at(mm_edit_buttons,3,2))>=0)mm_edit_close(b);}
        else if(key>=32 && key<127 && mm_edit_len<AW_MAPMARK_NAME){mm_text[mm_edit_len++]=(char)key;mm_text[mm_edit_len]=0;}
        return 1;
    }
    if(mm_confirm){
        if(key==K_ENTER || key=='y' || key=='Y')mm_remove_all();
        else if(key==K_ESCAPE || key=='n' || key=='N')mm_confirm=0;
        else if(key==K_MOUSE1 && (b=mm_button_at(mm_yes_no,2,1))>=0){if(b==0)mm_remove_all();else mm_confirm=0;}
        return 1;
    }
    if(!mm_menu)return 0;
    if(key==K_ESCAPE){mm_menu_close();return 1;}
    if(key==K_TAB){mm_sort=!mm_sort;mm_refresh();return 1;}
    if(key==K_ENTER){if((b=mm_selected())>=0){mm_centre(b);mm_menu_close();}return 1;}
    if(key==K_DEL || (key==K_BACKSPACE && !mm_box.search[0])){if((b=mm_selected())>=0)mm_delete(b);return 1;}
    if(key==K_UPARROW)AW_ListBoxKey(&mm_box,AW_LBKEY_UP);
    else if(key==K_DOWNARROW)AW_ListBoxKey(&mm_box,AW_LBKEY_DOWN);
    else if(key==K_PGUP || key==K_MWHEELUP)AW_ListBoxKey(&mm_box,AW_LBKEY_PAGEUP);
    else if(key==K_PGDN || key==K_MWHEELDOWN)AW_ListBoxKey(&mm_box,AW_LBKEY_PAGEDOWN);
    else if(key==K_HOME)AW_ListBoxKey(&mm_box,AW_LBKEY_HOME);
    else if(key==K_END)AW_ListBoxKey(&mm_box,AW_LBKEY_END);
    else if(key==K_BACKSPACE)AW_ListBoxKey(&mm_box,AW_LBKEY_BACKSPACE);
    else if(key==K_MOUSE1){
        mm_frame(6,MM_ROWS+2,frame);
        if((b=mm_button_at(mm_menu_buttons,6,MM_ROWS+2))>=0){
            int i=mm_selected();
            if(b==5)mm_menu_close();
            else if(b==4){if(AW_MapMarksCount())mm_confirm=1;}
            else if(i>=0){
                if(b==0){mm_centre(i);mm_menu_close();}
                else if(b==1)mm_edit_open(i);
                else if(b==2){AW_MapHotSet(AW_MapMark(i)->x,AW_MapMark(i)->y);marker_message="Hot marker follows the marker";}
                else mm_delete(i);
            }
        }else if(mouse_y>=frame[1]+6 && mouse_y<frame[1]+16){mm_sort=!mm_sort;mm_refresh();}
        else if(mouse_y>=frame[1]+27 && mouse_y<frame[1]+27+MM_ROWS*10){
            int line=(mouse_y-frame[1]-27)/10,right=frame[0]+frame[2]-8;
            if(AW_ListBoxClick(&mm_box,line)==AW_LB_CHOSEN && mouse_x>=right-3*AW_ConsoleCharWidth()-2)mm_delete(mm_selected());
        }
    }else if(key>=32 && key<127)AW_ListBoxType(&mm_box,key);
    return 1;
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
    teleport_opening=1;open_map();teleport_opening=0;   /* MAP-VERSION-2-DEFAULT-68: the version 1 screen */
    if(modal!=1){key_dest=previous;return;}
    teleport_mode=1;teleport_selected=0;teleport_message=NULL;map_local=0;
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
/* the entry's quest status marks (AWJ2 1 finished, 2 restart: aw_questbook.h AW_QB_FINISHED / AW_QB_RESTART) */
static int quest_status(const char *id,int32_t stage,void *ctx){
    uint32_t offset,length,flags=0;(void)ctx;
    return journal_row(id,stage,&offset,&length,&flags)?(int)(flags&(AW_QB_FINISHED|AW_QB_RESTART)):0;
}
static int book_quests(void){
    FILE *f=NULL;byte header[8],row[160];int i,j,count=0,size,kept=0,ok;aw_qb_dated_t *dated=NULL;
    if(aw_save_script_export)(void)aw_save_script_export(&aw_ledger);   /* the book reads the tables only */
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
    ok=AW_QuestBookBuild(&book->qb,book->quests,kept,&aw_ledger,dated,aw_jhist.count,quest_status,NULL);
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
    if(!allowed() || !AW_ControlAllowed(AW_CONTROL_PLAYER))return;
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
/* aw_dial.h aw_journal_entry_exists: the journal table has (ID, INDEX) (JOURNAL-LOWER-INDEX-ENTRY-64) */
static int journal_entry_exists(const char *id,int32_t index){
    uint32_t offset,length,flags;char low[AW_QB_ID];int i;
    for(i=0;i<AW_QB_ID-1 && id[i];i++)low[i]=(char)(id[i]>='A' && id[i]<='Z'?id[i]-'A'+'a':id[i]);
    low[i]=0;
    return journal_row(low,(int)index,&offset,&length,&flags);
}
/* the console's marker commands (MAP-MULTI-MARKERS-66), in the style of dbg tp and dbg item's searches */
static int mm_player_point(float *point){
    edict_t *e;
    if(!sv.active || !svs.clients || !(e=svs.clients[0].edict))return 0;
    return AW_WorldToSource(sv.name,e->v.origin,point);
}
static int mm_open_map(void){
    keydest_t previous=key_dest;
    if(modal==1)return 1;
    if(modal){Con_Printf("Close the current panel first.\n");return 0;}
    key_dest=key_game;open_normal_map();
    if(modal!=1){key_dest=previous;Con_Printf("The map cannot open now.\n");return 0;}
    return 1;
}
static void mm_command(void){
    const char *sub=Cmd_Argc()>1?Cmd_Argv(1):"";char arg[96];int i,k,n=0;float p[3];const aw_mapmark_t *m;
    arg[0]=0;
    for(i=2;i<Cmd_Argc();i++){
        if(arg[0] && strlen(arg)+1<sizeof(arg))strcat(arg," ");
        strncat(arg,Cmd_Argv(i),sizeof(arg)-strlen(arg)-1);
    }
    mm_max();mm_migrate();
    if(!*sub || !strcmp(sub,"find") || !strcmp(sub,"list")){
        for(k=0;(k=AW_MapMarkFind(arg,k))>=0;k++){
            m=AW_MapMark(k);p[0]=m->x;p[1]=m->y;p[2]=0;
            Con_Printf("%3d %s (%s) %ld %ld\n",k+1,m->name,AW_RegionNameAt(p)?AW_RegionNameAt(p):"no region",(long)m->x,(long)m->y);n++;
        }
        Con_Printf("%d of %d markers (at most %d)%s%s.\n",n,AW_MapMarksCount(),AW_MapMarksMax(),arg[0]?" match ":"",arg);
        if(!*sub)Con_Printf("Usage: marker find|show|add|del|clear|hot [text]\n");
    }else if(!strcmp(sub,"show")){
        if((i=AW_MapMarkLookup(arg))<0){Con_Printf("No marker %s.\n",arg);return;}
        if(mm_open_map())mm_centre(i);
    }else if(!strcmp(sub,"add")){
        if(!mm_player_point(p)){Con_Printf("Marker not set: no outdoor position here.\n");return;}
        i=AW_MapMarkAdd(p[0],p[1],arg[0]?arg:mm_default_name(p));
        if(i==-1)Con_Printf("Markers full: %d (aw_map_markers_max).\n",AW_MapMarksMax());
        else if(i<0)Con_Printf("Marker not set: not enough memory.\n");
        else Con_Printf("Map marker %d: %s at %ld %ld.\n",i+1,AW_MapMark(i)->name,(long)p[0],(long)p[1]);
    }else if(!strcmp(sub,"del")){
        if((i=AW_MapMarkLookup(arg))<0){Con_Printf("No marker %s.\n",arg);return;}
        Con_Printf("Map marker %d (%s) removed.\n",i+1,AW_MapMark(i)->name);mm_delete(i);
    }else if(!strcmp(sub,"clear")){
        if(!AW_MapMarksCount()){Con_Printf("No markers.\n");return;}
        if(mm_open_map()){mm_menu_open();mm_confirm=1;}   /* the Yes/No box on the map */
    }else if(!strcmp(sub,"hot")){
        if(!strcmp(arg,"off")){AW_MapHotOff();Con_Printf("Hot marker off.\n");return;}
        if(arg[0]){
            if((i=AW_MapMarkLookup(arg))<0){Con_Printf("No marker %s.\n",arg);return;}
            AW_MapHotSet(AW_MapMark(i)->x,AW_MapMark(i)->y);Con_Printf("Hot marker follows %s.\n",AW_MapMark(i)->name);return;
        }
        if(!mm_player_point(p)){Con_Printf("Hot marker not set: no outdoor position here.\n");return;}
        AW_MapHotSet((float)floor(p[0]+.5f),(float)floor(p[1]+.5f));Con_Printf("Hot marker at %ld %ld.\n",(long)p[0],(long)p[1]);
    }else Con_Printf("Usage: marker find|show|add|del|clear|hot [text]\n");
}
/* NAV-HOT-MARKER-COMPASS-66: a thin strip at the top of the view (aw_compass 1, off by default): north (N) and the
 * hot marker (an orange mark; at the strip's end when behind), with its distance in rough steps. 120 x 7 pixels. */
static void compass_draw(void){
    float here[3],hx,hy,yaw=cl.viewangles[YAW],rel,dist;int w=120,x0,y,cx,x;edict_t *e;const char *how;
    if(!aw_compass.value || modal || !sv.active || !svs.clients || !(e=svs.clients[0].edict))return;
    cx=r_refdef.vrect.x+r_refdef.vrect.width/2;x0=cx-w/2;y=r_refdef.vrect.y+1;
    if(x0<0)return;
    AW_UIFill(x0,y,w,7,AW_UIColor(15,20,23));AW_UIFill(x0,y+7,w,1,AW_UIColor(202,165,96));
    AW_UIFill(cx,y,1,2,AW_UIColor(202,165,96));
    /* a bearing B (degrees, 90 = north as the map shows it) left of the view is left on the strip; 90 degrees a side */
    rel=90-yaw;while(rel>180)rel-=360;while(rel<-180)rel+=360;
    if(rel>=-90 && rel<=90)AW_UIText(cx-(int)(rel*(w/2-4)/90)-2,y,"N",-1);
    if(!AW_MapHotGet(&hx,&hy) || !AW_WorldToSource(sv.name,e->v.origin,here))return;
    rel=(float)(atan2(hy-here[1],hx-here[0])*180/M_PI)-yaw;while(rel>180)rel-=360;while(rel<-180)rel+=360;
    x=cx-(int)((rel<-90?-90:rel>90?90:rel)*(w/2-4)/90);
    AW_UIFill(x-1,y+1,3,5,AW_UIColor(255,140,0));
    dist=(float)sqrt((hx-here[0])*(hx-here[0])+(hy-here[1])*(hy-here[1]));
    how=dist<AW_MAPFOG_CELL/16?"here":dist<AW_MAPFOG_CELL*2?"near":"far";
    AW_UIText(x0+w+3,y,how,-1);
}
/* MAP-VERSION-2-DEFAULT-68: dbg dbgmap on/off (true/false, 1/0; bare: the other way) shows map version 1, the debug map,
 * or version 2; dbg maptype 1/2 sets the version (bare: prints it). One saved value, aw_map_version, read when the map
 * opens (the console closes the map, so the next opening shows it). */
static void map_version_said(void){
    Con_Printf("Map version %d%s, from the next opening of the map.\n",aw_map_version.value==1?1:2,
               aw_map_version.value==1?" (the debug map)":" (the default)");
}
static void map_debug_command(void){
    const char *s=Cmd_Argv(1);int on;
    if(Cmd_Argc()<2)on=aw_map_version.value!=1;
    else if(Cmd_Argc()==2 && (!Q_strcasecmp((char *)s,"on") || !Q_strcasecmp((char *)s,"true") || !strcmp(s,"1")))on=1;
    else if(Cmd_Argc()==2 && (!Q_strcasecmp((char *)s,"off") || !Q_strcasecmp((char *)s,"false") || !strcmp(s,"0")))on=0;
    else{Con_Printf("Usage: dbg dbgmap on/off, true/false or 1/0 (no argument toggles)\n");return;}
    Cvar_SetValue(aw_map_version.name,on?1:2);map_version_said();
}
static void map_type_command(void){
    const char *s=Cmd_Argv(1);
    if(Cmd_Argc()<2){map_version_said();return;}
    if(Cmd_Argc()!=2 || (strcmp(s,"1") && strcmp(s,"2"))){Con_Printf("Usage: dbg maptype 1/2 (1 the debug map, 2 the default)\n");return;}
    Cvar_SetValue(aw_map_version.name,s[0]=='1'?1:2);map_version_said();
}
void AW_WorldUIInit(void){aw_journal_entry_exists=journal_entry_exists;AW_InventoryInit();Cvar_RegisterVariable(&aw_map_mode);
    Cmd_AddCommand("marker",mm_command);
    aw_save_markers_encode=AW_MapMarksEncode;aw_save_markers_decode=AW_MapMarksDecode;
    aw_save_markers_loaded=mm_loaded;aw_save_markers_reset=mm_reset;aw_hud_compass_draw=compass_draw;
    Cvar_RegisterVariable(&aw_map_debug_available);
    Cvar_RegisterVariable(&aw_map_lava);Cvar_RegisterVariable(&aw_map_format);
    Cvar_RegisterVariable(&aw_key_inv_use);Cvar_RegisterVariable(&aw_key_inv_drop);   /* OPENING-TUTORIAL-KEYS-65 */
    Cvar_RegisterVariable(&aw_key_inv_info);   /* INVENTORY-ITEM-INFO-67 */
    Cvar_RegisterVariable(&aw_map_markers_max);Cvar_RegisterVariable(&aw_compass);    /* MAP-MULTI-MARKERS-66 */
    Cvar_RegisterVariable(&aw_map_version);   /* MAP-VERSION-2-DEFAULT-68 */
    Cmd_AddCommand("aw_map_debug",map_debug_command);Cmd_AddCommand("aw_map_type",map_type_command);
    Cmd_AddCommand("aw_teleport_map",open_teleport_map);Cmd_AddCommand("aw_worldmap",open_normal_map);Cmd_AddCommand("aw_journal",open_journal);Cmd_AddCommand("aw_inventory",inventory_command);}
void AW_WorldUIMouse(int dx,int dy){
    int top;
    if(!modal || key_dest!=key_menu)return;
    if(modal==1 && drag){
        map_world_placed=1;   /* MAP-WORLD-TAB-BLANK-67: a pan the player makes is kept */
        if(marker_click){
            marker_drag_x+=dx;marker_drag_y+=dy;
            if(marker_drag_x*marker_drag_x+marker_drag_y*marker_drag_y>9){
                map_x-=marker_drag_x*map_step;map_y-=marker_drag_y*map_step;marker_click=0;
            }
        }else{map_x-=dx*map_step;map_y-=dy*map_step;}
    }
    mouse_x=minmax(mouse_x+dx,0,319);mouse_y=minmax(mouse_y+dy,0,199);
    if(modal==4 && drag==K_MOUSE1 && aw_worldui_panel_drag)aw_worldui_panel_drag(mouse_x,mouse_y);   /* a scroll bar */
    if(modal==3 && inventory && inventory->info){      /* INVENTORY-ITEM-INFO-67: the box's scroll bar held */
        if(drag==K_MOUSE1)AW_ItemInfoDrag(inventory->info,mouse_y);
    }else if(modal==3 && inventory && inventory->confirm){   /* INVENTORY-DOUBLECLICK-62: the count slider held */
        if(drag==K_MOUSE1 && inventory->confirm_drag)
            inventory->confirm_count=AW_InventorySliderCount(mouse_x,INV_CONFIRM_RAIL_X,INV_CONFIRM_RAIL_W,inventory->confirm_max);
    }else if(modal==3 && inventory && drag==K_MOUSE1){
        top=AW_UIScrollHit(INV_SCROLL_X+2,minmax(mouse_y,INV_LIST_Y+10,INV_LIST_Y+INV_SCROLL_H-11),
            INV_SCROLL_X,INV_LIST_Y,INV_SCROLL_H,inventory->count,INV_VISIBLE,inventory->top);
        if(top>=0)inventory_scroll(top);
    }
    if(modal==2 && book->index_mode && drag){
        top=AW_UIScrollHit(306,minmax(mouse_y,40,165),304,40,126,book->nshown,(book->index_end-book->index_top),book->index_top);
        if(top>=0){book->index_top=top;book->selection=top;AW_UIBookBegin();index_layout();AW_UIBookEnd();}
    }
}
/* MAP-VERSION-2-DEFAULT-68: the key the player bound to the map's command closes it too (as the stats window's own key),
 * and version 2's footer names that key (aw_textdef.c AW_TextBoundKeyForCommand), never a fixed letter */
static int map_own_key(int key){return key>=0 && key<256 && keybindings[key] && !Q_strcasecmp(keybindings[key],"aw_worldmap");}
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
        /* a left click without a drag no longer places a marker (the right button does, MAP-MULTI-MARKERS-66) */
        if(modal==1 && key==K_MOUSE1 && marker_click)marker_click=0;
        if((modal==1 && key==drag) || (modal==4 && key==K_MOUSE1) || (modal==2 && (key==K_MOUSE1 || key==K_MOUSE2)) || (modal==3 && key==K_MOUSE1))drag=0;
        if(modal==3 && key==K_MOUSE1 && inventory && inventory->info)inventory->info->drag=0;
        return 1;
    }
    if(key==K_F10 || key=='`'){close_panel();return 0;}
    if(modal==1 && mm_key(key))return 1;   /* a marker's box, the Yes/No box or the Markers menu takes every key */
    /* a panel that must be finished (the level-up box, LEVEL-UP-58: the original's box has no cancel) takes Esc itself */
    if(key==K_ESCAPE && modal==4 && aw_worldui_panel_holds_escape){if(!panel_key(key,mouse_x,mouse_y))close_panel();return 1;}
    /* INVENTORY-DOUBLECLICK-62: Esc (or I) in the consumable's box is its Cancel, the window stays */
    if(modal==3 && inventory && inventory->confirm && (key==K_ESCAPE || key=='i' || key=='I')){inventory_confirm_close();return 1;}
    /* INVENTORY-ITEM-INFO-67: Esc (or I) in the information box is its OK: back to the window */
    if(modal==3 && inventory && inventory->info && (key==K_ESCAPE || key=='i' || key=='I')){inventory_info_close();return 1;}
    if(key==K_ESCAPE || (modal==1 && (key=='m' || key=='M' || map_own_key(key))) || (modal==2 && (key=='j' || key=='J')) || (modal==3 && (key=='i' || key=='I'))){close_panel();return 1;}
    if(modal==3){inventory_key(key);return 1;}
    if(modal==4){if(key==K_MOUSE1)drag=K_MOUSE1;if(!panel_key(key,mouse_x,mouse_y))close_panel();return 1;}
    if(modal==1){
        if(key!=K_MOUSE1 && key!=K_MOUSE2 && key!=K_MOUSE3)marker_click=0;
        /* MAP-VERSION-2-DEFAULT-68: version 2's footer: the close key's words close, the tabs switch the view or open
         * the Markers menu (the footer box's inner rows) */
        if(key==K_MOUSE1 && map_v2 && mouse_y>=MAPV2_FOOT_BOX_Y+AW_UI_FRAME_EDGE &&
           mouse_y<MAPV2_FOOT_BOX_Y+MAPV2_FOOT_BOX_H-AW_UI_FRAME_EDGE){
            marker_click=drag=0;
            if(mouse_x>=MAPV2_CLOSE_X-2 && mouse_x<MAPV2_CLOSE_X+mapv2_close_w)close_panel();
            else if(mouse_x>=mapv2_tabs[0].x && mouse_x<mapv2_tabs[0].x+mapv2_tabs[0].w)map_set_local(0);
            else if(mouse_x>=mapv2_tabs[1].x && mouse_x<mapv2_tabs[1].x+mapv2_tabs[1].w && (marker || local_room))map_set_local(1);
            else if(mouse_x>=mapv2_tabs[2].x && mouse_x<mapv2_tabs[2].x+mapv2_tabs[2].w)mm_menu_open();
            return 1;
        }
        if(key==K_MOUSE1 && !teleport_mode && !map_v2 && mouse_y>=1 && mouse_y<16){
            marker_click=drag=teleport_selected=0;teleport_message=NULL;
            if(mouse_x>=4 && mouse_x<66 && map_debug_enabled())Cvar_SetValue(aw_map_mode.name,0);
            else if(mouse_x>=250 && mouse_x<316)Cvar_SetValue(aw_map_mode.name,1);
            else if(map_in_game() && mouse_x>=LOCALBTN_WORLD_X && mouse_x<LOCALBTN_WORLD_X+LOCALBTN_W)map_set_local(0);
            else if(map_in_game() && mouse_x>=LOCALBTN_LOCAL_X && mouse_x<LOCALBTN_LOCAL_X+LOCALBTN_W && (marker || local_room))map_set_local(1);
            return 1;
        }
        if(key==K_TAB && !teleport_mode && (map_local || marker || local_room)){map_set_local(!map_local);return 1;}
        /* the room's plan has no pan, zoom or marker: the pointer only names doors */
        if(map_local && local_room && key==K_MOUSE1 && in_view())return 1;
        /* MAP-WORLD-TAB-BLANK-67: a view the player sets (zoom, pan, Home, P) is kept: no first placement over it */
        if(key==K_MWHEELUP || key==K_MWHEELDOWN || key=='+' || key=='=' || key=='-' || key==K_HOME || key=='p' ||
           key==K_LEFTARROW || key==K_RIGHTARROW || key==K_UPARROW || key==K_DOWNARROW ||
           key=='a' || key=='d' || key=='w' || key=='s')map_world_placed=1;
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
            if((key==K_MOUSE2 || key==K_MOUSE3) && in_view())drag=key;
            if(key==K_ENTER)confirm_teleport();
            if(key==K_MOUSE1){
                if(in_view())select_teleport_point();
                else if(teleport_button_hit())confirm_teleport();
            }
        }else{
            int on_map=in_view() && !(map_local && local_room);
            if(key=='k' || key=='K'){mm_menu_open();return 1;}
            if((key=='h' || key=='H') && !(map_local && local_room))mm_hot_key();
            if(normal_teleport_enabled()){
                if(key==K_MOUSE3 && !drag && !teleport_button_hit())select_teleport_point();
                if(key==K_ENTER)confirm_teleport();
            }
            /* MAP-MULTI-MARKERS-66: the right button sets a named marker (in the debug view with teleport, the middle
             * button; the right one picks the teleport target there) */
            if(on_map && !drag && (key==K_MOUSE2 || (key==K_MOUSE3 && !normal_teleport_enabled())))place_marker();
            if(key==K_MOUSE1){
                int hit;
                marker_click=drag=0;
                if(teleport_button_hit())confirm_teleport();
                else if(clear_button_hit())mm_menu_open();
                else if(on_map && (hit=mm_at_pointer())>=0)mm_edit_open(hit);
                else if(in_view()){
                    drag=K_MOUSE1;marker_click=1;marker_drag_x=marker_drag_y=0;
                }else if(!map_v2 && mouse_y>=184)close_panel();
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
/* MAP-VERSION-2-DEFAULT-68: version 2 marks no lava (the original's map has no lava colour); version 1 as before */
static int lava_visible(void){return !map_v2 && lava_count>0 && aw_map_lava.value!=0 && aw_map_format.value>=2;}
static void lava_draw(float left,float top){
    int i,j,n,k,r,r0,r1,c,c0,c1,painted,mx,my,x1v=view_x+view_w,y1v=view_y+view_h;const byte *q,*pt=lava_points;byte *dst;
    float kx=map_w/((float)(map_bounds[2]-map_bounds[0])*map_step),ky=map_h/((float)(map_bounds[3]-map_bounds[1])*map_step);
    float ox=view_x-left/map_step-map_bounds[0]*kx,oy=view_y-top/map_step+map_bounds[3]*ky;
    float sx[LAVA_POINTS],sy[LAVA_POINTS],x0,x1,y0,y1,yc,xl,xr,xi,ax,ay,bx,by,cx,cy;
    lava_painted=0;
    for(i=0;i<lava_count;i++,pt+=n*8){
        q=lava_pools+i*24;n=q[4]|(q[5]<<8);
        x0=(int32_t)u32(q+8)*kx+ox;x1=(int32_t)u32(q+16)*kx+ox;
        y0=oy-(int32_t)u32(q+20)*ky;y1=oy-(int32_t)u32(q+12)*ky;
        if(x1<view_x || x0>=x1v || y1<view_y || y0>=y1v)continue;
        cx=cy=0;
        for(j=0;j<n;j++){sx[j]=(int32_t)u32(pt+j*8)*kx+ox;sy[j]=oy-(int32_t)u32(pt+j*8+4)*ky;cx+=sx[j];cy+=sy[j];}
        painted=0;
        if(n>=3){
            r0=(int)ceil(y0-.5f);r1=(int)floor(y1-.5f);if(r0<view_y)r0=view_y;if(r1>y1v-1)r1=y1v-1;
            for(r=r0;r<=r1;r++){
                yc=r+.5f;xl=1e9f;xr=-1e9f;
                for(j=0,k=n-1;j<n;k=j++){
                    ax=sx[k];ay=sy[k];bx=sx[j];by=sy[j];
                    if((ay<=yc && yc<by) || (by<=yc && yc<ay)){
                        xi=ax+(yc-ay)*(bx-ax)/(by-ay);if(xi<xl)xl=xi;if(xi>xr)xr=xi;
                    }
                }
                if(xl>xr)continue;
                c0=(int)ceil(xl-.5f);c1=(int)floor(xr-.5f);if(c0<view_x)c0=view_x;if(c1>x1v-1)c1=x1v-1;
                if(c0>c1)continue;
                dst=vid.buffer+r*vid.rowbytes;for(c=c0;c<=c1;c++)dst[c]=(byte)lava_colour;
                painted+=c1-c0+1;
            }
        }
        if(!painted){
            mx=(int)floor(cx/n);my=(int)floor(cy/n);
            if(mx>=view_x && mx<x1v && my>=view_y && my<y1v){vid.buffer[my*vid.rowbytes+mx]=(byte)lava_colour;painted=1;}
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
        if(cy+y<view_y || cy+y>=view_y+view_h)continue;
        for(x=-12;x<=12;x++){
            if(cx+x<view_x || cx+x>=view_x+view_w)continue;
            /* the screen pixel turned back onto the arrow (y down: a clockwise turn) */
            u=x*c+y*s;v=y*c-x*s;
            sx=(int)floor(u+8.0f);sy=(int)floor(v+8.0f);
            if(sx<0 || sy<0 || sx>=16 || sy>=16 || (p=a[sy*64+sx])==255)continue;
            vid.buffer[(cy+y)*vid.rowbytes+cx+x]=p;
        }
    }
    return 1;
}
/* a door marker (3 x 3, OpenMW draws a door icon) at MX, MY; the nearest within 4 pixels of the pointer is named */
static void door_marker(int mx,int my,const char *name,int *best){
    int d;
    if(mx<view_x+1 || mx>=view_x+view_w-1 || my<view_y+1 || my>=view_y+view_h-1)return;
    AW_UIFill(mx-1,my-1,3,3,AW_UIColor(214,96,64));
    d=(mx-mouse_x)*(mx-mouse_x)+(my-mouse_y)*(my-mouse_y);
    if(d<*best){*best=d;map_hover_name=name;}
}
/* the room's plan under its fog, its doors and the player (stage 3, inside) */
static void local_draw(int in_game,int *best){
    int x,y,gx,gy,fog=AW_UIColor(20,18,14),i,mx,my;byte seen[AW_MAPFOG_ROOM_GRID*AW_MAPFOG_ROOM_GRID],*dst;
    int cols[VIEW_MAX_W];float w=(local_max[0]-local_min[0])/AW_MAPFOG_ROOM_GRID,h=(local_max[1]-local_min[1])/AW_MAPFOG_ROOM_GRID;
    float point[3];const char *name;
    /* MAP-EXPLORED-ROOMS-CAP-66: the room's bits looked up once a frame (was 256 searches by name) */
    const unsigned char *bits=in_game?AW_MapFogRoomBits(local_name):NULL;
    for(gy=0;gy<AW_MAPFOG_ROOM_GRID;gy++)for(gx=0;gx<AW_MAPFOG_ROOM_GRID;gx++){
        int bit=gy*AW_MAPFOG_ROOM_GRID+gx;
        seen[bit]=!in_game || (bits && ((bits[bit>>3]>>(bit&7))&1));
    }
    for(x=0;x<LOCAL_W;x++){
        gx=(int)floor(((x+.5f-local_ox)/local_scale)/w);cols[x]=gx<0?0:gx>=AW_MAPFOG_ROOM_GRID?AW_MAPFOG_ROOM_GRID-1:gx;
    }
    for(y=0;y<LOCAL_H;y++){
        const byte *row=local_pixels+y*LOCAL_W,*s;
        gy=(int)floor((local_max[1]-local_min[1]-(y+.5f-local_oy)/local_scale)/h);
        gy=gy<0?0:gy>=AW_MAPFOG_ROOM_GRID?AW_MAPFOG_ROOM_GRID-1:gy;
        s=seen+gy*AW_MAPFOG_ROOM_GRID;dst=vid.buffer+(y+view_y)*vid.rowbytes+view_x;
        for(x=0;x<LOCAL_W;x++)dst[x]=s[cols[x]]?row[x]:(byte)fog;
    }
    for(i=0;(x=AW_SceneMapDoor(i,point,&name))>=0;i++){
        if(!x || (in_game && !AW_MapFogRoomSeen(local_name,point[0],point[1],local_min,local_max)))continue;
        local_to_screen(point[0],point[1],&mx,&my);door_marker(mx,my,name,best);
    }
    if(svs.clients && svs.clients[0].edict){
        edict_t *e=svs.clients[0].edict;
        local_to_screen(e->v.origin[0],e->v.origin[1],&mx,&my);
        if(mx>=view_x+5 && mx<view_x+view_w-5 && my>=view_y+5 && my<view_y+view_h-5 && !map_arrow(mx,my,cl.viewangles[YAW])){
            AW_UIFill(mx-4,my,9,1,AW_UIColor(255,255,255));AW_UIFill(mx,my-4,1,9,AW_UIColor(255,255,255));
        }
    }
}
/* MAP-VERSION-2-DEFAULT-68: version 2 in the shared menu layout, the same calls at the same places as the attributes,
 * inventory and magic views (aw_statswin.c window_frame, inventory_draw above): black, the window's box (its title bar
 * comes with the chrome), then the map's box and the footer's box inside it */
static void mapv2_frame(void){
    AW_UIFill(0,0,320,200,AW_UIColor(0,0,0));AW_UIBox(2,2,316,196);
    AW_UIBox(4,MAPV2_MAP_BOX_Y,312,MAPV2_MAP_BOX_H);AW_UIBox(4,MAPV2_FOOT_BOX_Y,312,MAPV2_FOOT_BOX_H);
}
/* a line of console glyphs in WIDTH pixels, ending in "..." when cut (as aw_statswin.c small) */
static void mapv2_small(int x,int y,int width,const char *value,int color){
    char clipped[96];int n=(int)strlen(value),limit=width/4;
    if(limit<1)return;
    if(limit>(int)sizeof(clipped)-1)limit=sizeof(clipped)-1;
    if(n>limit)n=limit;
    memcpy(clipped,value,n);clipped[n]=0;
    if(value[n] && n>=3)memcpy(clipped+n-3,"...",3);
    if(n>0)AW_SmallStringColor(x,y,n*4,clipped,color);
}
/* the title (the place's name in the title bar's plaque: the game's font, as the inventory's title, when it fits, else
 * the console glyphs in the same plaque, aw_layout.c AW_LayoutTitle) and the footer (the close key, a hint or the
 * markers' message, the World / Local / Markers tabs; the one lit is filled as the inventory's chosen category) */
static void mapv2_chrome(void){
    int gold=AW_UIColor(223,199,144),muted=AW_UIColor(150,135,104),tab=AW_UIColor(48,39,22),i,on,lit;
    if(map_name_fit.font==AW_TITLE_GAME_FONT){AW_UISmallBegin();window_title(6,6,308,map_name,gold);AW_UISmallEnd();}
    else{
        char cut[80];int n=map_name_fit.chars,left=6,plaque=map_name_fit.plaque;
        if(n>(int)sizeof(cut)-1)n=sizeof(cut)-1;
        memcpy(cut,map_name,(size_t)n);cut[n]=0;
        if(map_name_fit.font==AW_TITLE_CONSOLE_CUT && n>=3)memcpy(cut+n-3,"...",3);
        if(!aw_title_plaque || !aw_title_plaque(6,6,308,&left,&plaque)){left=6;plaque=308;}
        if(n>0)AW_SmallStringColor(left+(plaque-(n*4-1))/2,9,n*4,cut,gold);
    }
    {   char close[40];const char *key=AW_TextBoundKeyForCommand("aw_worldmap");int hint_x;
        if(key && *key && strlen(key)<16)snprintf(close,sizeof(close),"%s/Esc close",key);else strcpy(close,"Esc close");
        mapv2_close_w=(int)strlen(close)*4;
        mapv2_small(MAPV2_CLOSE_X,MAPV2_FOOT_Y,mapv2_close_w,close,gold);
        hint_x=MAPV2_CLOSE_X+mapv2_close_w+8;
        mapv2_small(hint_x,MAPV2_FOOT_Y,MAPV2_HINT_END-hint_x,marker_message?marker_message:
                    map_local && local_room?"Tab view":"Tab view  R-click mark  H hot",muted);
    }
    /* the view's own keys (AW_WorldUIKey): zoom 0..5 by +/- or the wheel, pan by a drag, the arrows or WASD, Home fits the
     * island, P centres the player; a room's plan has none of them */
    if(!(map_local && local_room))
        mapv2_small(MAPV2_CLOSE_X,MAPV2_FOOT_Y2,300,"+/- wheel zoom  drag/arrows/WASD pan  Home fit  P player",muted);
    for(i=0;i<3;i++){
        on=i==0?!map_local:i==1?map_local:mm_menu;
        lit=i==1?(marker || local_room):1;
        if(on)AW_UIFill(mapv2_tabs[i].x,MAPV2_FOOT_Y-2,mapv2_tabs[i].w,9,tab);
        mapv2_small(mapv2_tabs[i].x+2,MAPV2_FOOT_Y,mapv2_tabs[i].w-4,mapv2_tabs[i].label,lit?gold:muted);
    }
}
static void map_draw(void){
    int x,y,sx,sy,cols[VIEW_MAX_W],fog_cols[VIEW_MAX_W],ocean=map_ocean,gold=AW_UIColor(248,225,136),i,mx,my,in_game=map_in_game();
    int fog=AW_UIColor(20,18,14),best=17,edge=AW_UIColor(202,165,96),inner=AW_UIColor(15,20,23),d;
    float left=map_x-(view_w/2)*map_step,top=map_y-(view_h/2)*map_step,px,py,angle,dx,dy;byte *dst;char line[96];
    const char *region;float source[3];int width,limit,vx1=view_x+view_w,vy1=view_y+view_h;
    update_player();map_hover_name=NULL;
    if(map_v2)mapv2_frame();   /* MAP-VERSION-2-DEFAULT-68: the menus' frame, the map's and the footer's boxes */
    else AW_UIFill(0,0,320,200,AW_UIColor(15,20,23));
    if(map_local && local_pixels){
        local_draw(in_game,&best);snprintf(line,sizeof(line),"Local map: %s",local_name);goto chrome;
    }
    for(x=0;x<view_w;x++)cols[x]=(int)floor(left+x*map_step);
    if(in_game){   /* MAP-ORIGINAL-POI-66 stage 2: the fog square of each column, once per frame */
        const float square=AW_MAPFOG_CELL/AW_MAPFOG_GRID;
        for(x=0;x<view_w;x++)fog_cols[x]=(int)floor((map_bounds[0]+(cols[x]+.5f)*(map_bounds[2]-map_bounds[0])/map_w)/square)-fog_gx0;
    }
    for(y=0;y<view_h;y++){
        sy=(int)floor(top+y*map_step);dst=vid.buffer+(y+view_y)*vid.rowbytes+view_x;
        for(x=0;x<view_w;x++){sx=cols[x];dst[x]=(sx>=0 && sx<map_w && sy>=0 && sy<map_h)?map_pixels[sy*map_w+sx]:ocean;}
    }
    if(lava_visible())lava_draw(left,top);
    if(in_game)for(y=0;y<view_h;y++){   /* the unexplored land, sea and lava in the fog colour */
        int gy;
        sy=(int)floor(top+y*map_step);dst=vid.buffer+(y+view_y)*vid.rowbytes+view_x;
        gy=(int)floor((map_bounds[3]-(sy+.5f)*(map_bounds[3]-map_bounds[1])/map_h)/(AW_MAPFOG_CELL/AW_MAPFOG_GRID))-fog_gy0;
        for(x=0;x<view_w;x++)if(!fog_open(fog_cols[x],gy))dst[x]=(byte)fog;
    }
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
        int known=0,k;
        px=(areas[i].x-map_bounds[0])*map_w/(map_bounds[2]-map_bounds[0]);py=(map_bounds[3]-areas[i].y)*map_h/(map_bounds[3]-map_bounds[1]);
        mx=view_x+(int)((px-left)/map_step);my=view_y+(int)((py-top)/map_step);
        /* MAP-PLACES-SHOWN-UNVISITED-67: a settlement a script's ShowMap revealed shows like any other place (the
         * opening's Sellus Gravius reveals Balmora with Pelagiad and Moonmoth Legion Fort; it stayed hidden before) */
        for(k=0;k<map_place_count;k++)if(!strcmp(map_places[k].name,areas[i].title)){known=map_places[k].known;break;}
        if(!in_game){if(mx>=6 && mx<313 && my>=22 && my<161){AW_UIFill(mx-1,my-1,3,3,gold);text(mx+4,my,areas[i].title,314);}}
        else if(mx>=view_x+2 && mx<vx1-2 && my>=view_y+2 && my<vy1-2 && (known || fog_open_at(areas[i].x,areas[i].y))){
            /* in play a settlement is a place square like the others, named only on mouse-over */
            AW_UIFill(mx-2,my-2,5,5,edge);AW_UIFill(mx-1,my-1,3,3,inner);
            d=(mx-mouse_x)*(mx-mouse_x)+(my-mouse_y)*(my-mouse_y);
            if(d<best){best=d;map_hover_name=areas[i].title;}
        }
    }
    /* MAP-ORIGINAL-POI-66: the known places as small squares (all of them in the debug view); the one nearest the
     * pointer (within 4 pixels) is named in a box after the player's marker is drawn */
    {   int k;
        for(i=0;i<map_place_count;i++){
            if(in_game && !map_places[i].known && !fog_open_at(map_places[i].x,map_places[i].y))continue;
            for(k=0;k<area_count && strcmp(areas[k].title,map_places[i].name);k++){}
            if(k<area_count)continue;                      /* a settlement already drawn above */
            px=(map_places[i].x-map_bounds[0])*map_w/(map_bounds[2]-map_bounds[0]);
            py=(map_bounds[3]-map_places[i].y)*map_h/(map_bounds[3]-map_bounds[1]);
            mx=view_x+(int)((px-left)/map_step);my=view_y+(int)((py-top)/map_step);
            if(mx<view_x+2 || mx>=vx1-2 || my<view_y+2 || my>=vy1-2)continue;
            AW_UIFill(mx-2,my-2,5,5,edge);AW_UIFill(mx-1,my-1,3,3,inner);
            d=(mx-mouse_x)*(mx-mouse_x)+(my-mouse_y)*(my-mouse_y);
            if(d<best){best=d;map_hover_name=map_places[i].name;}
        }
    }
    if(map_local){   /* stage 3, outdoors: the doors of the loaded scene, on explored land */
        float point[3],world[3];const char *name;int n;
        for(i=0;(n=AW_SceneMapDoor(i,point,&name))>=0;i++){
            if(!n || !AW_WorldToSource(sv.name,point,world) || (in_game && !fog_open_at(world[0],world[1])))continue;
            px=(world[0]-map_bounds[0])*map_w/(map_bounds[2]-map_bounds[0]);py=(map_bounds[3]-world[1])*map_h/(map_bounds[3]-map_bounds[1]);
            door_marker(view_x+(int)((px-left)/map_step),view_y+(int)((py-top)/map_step),name,&best);
        }
    }
    if(marker){
        px=(player_x-map_bounds[0])*map_w/(map_bounds[2]-map_bounds[0]);py=(map_bounds[3]-player_y)*map_h/(map_bounds[3]-map_bounds[1]);
        mx=view_x+(int)((px-left)/map_step);my=view_y+(int)((py-top)/map_step);
        if(mx>=view_x+5 && mx<vx1-5 && my>=view_y+5 && my<vy1-5){
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
    {   /* MAP-MULTI-MARKERS-66: the player's named markers (cyan diamonds) and the hot marker (an orange diamond with
         * a centre square), above the fog; the hovered one is named */
        int cyan=AW_UIColor(48,240,240),orange=AW_UIColor(255,140,0),ox,oy,k,r;const aw_mapmark_t *m;float hx,hy;
        for(k=-1;k<AW_MapMarksCount();k++){
            if(k<0){if(!AW_MapHotGet(&hx,&hy))continue;source[0]=hx;source[1]=hy;}
            else{m=AW_MapMark(k);source[0]=m->x;source[1]=m->y;}
            if(!map_point_inside(source[0],source[1]))continue;
            source_to_screen(source[0],source[1],&mx,&my);
            r=k<0?5:4;
            /* A clipped diamond remains distinct from the red teleport cross. */
            for(oy=-r;oy<=r;oy++)for(ox=-r;ox<=r;ox++)if(abs(ox)+abs(oy)==r || (!ox && !oy) || (k<0 && abs(ox)<=1 && abs(oy)<=1))
                if(mx+ox>=view_x && mx+ox<vx1 && my+oy>=view_y && my+oy<vy1)AW_UIFill(mx+ox,my+oy,1,1,k<0?orange:cyan);
            d=(mx-mouse_x)*(mx-mouse_x)+(my-mouse_y)*(my-mouse_y);
            if(d<=best){best=d;map_hover_name=k<0?"Hot marker":AW_MapMark(k)->name;}
        }
    }
    if(teleport_selected && (teleport_mode || normal_teleport_enabled())){
        px=(teleport_point[0]-map_bounds[0])*map_w/(map_bounds[2]-map_bounds[0]);
        py=(map_bounds[3]-teleport_point[1])*map_h/(map_bounds[3]-map_bounds[1]);
        mx=view_x+(int)((px-left)/map_step);my=view_y+(int)((py-top)/map_step);
        for(i=-5;i<=5;i++){
            if(mx+i>=view_x && mx+i<vx1 && my>=view_y && my<vy1)AW_UIFill(mx+i,my,1,1,AW_UIColor(255,32,32));
            if(mx>=view_x && mx<vx1 && my+i>=view_y && my+i<vy1)AW_UIFill(mx,my+i,1,1,AW_UIColor(255,32,32));
        }
    }
 chrome:
    if(map_hover_name){   /* the hovered place's name, in a box beside the pointer, kept inside the map view */
        const char *name=map_hover_name;
        int bw=(int)strlen(name)*AW_ConsoleCharWidth()+6,bx=mouse_x+10,by=mouse_y-14;
        if(bw>view_w)bw=view_w;
        if(bx+bw>vx1)bx=mouse_x-10-bw;
        if(bx<view_x)bx=view_x;
        if(by<view_y)by=mouse_y+12;
        if(by+11>vy1)by=vy1-11;
        AW_UIFill(bx,by,bw,11,AW_UIColor(202,165,96));AW_UIFill(bx+1,by+1,bw-2,9,AW_UIColor(15,20,23));
        text(bx+3,by+2,name,bx+bw-2);
    }
    if(map_v2){mapv2_chrome();mm_draw();return;}   /* MAP-VERSION-2-DEFAULT-68: the title and the footer */
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
        if(in_game){text(77,5,"IN-GAME MAP PROTOTYPE",LOCALBTN_WORLD_X-2);
            text(8,188,"Pan/zoom  P player  M/Esc close",315);}
        else{text(77,5,"DEBUG MAP",315);text(116,5,line,315);}
        map_mode_button(4,62,"DEBUG",!in_game,map_debug_enabled());
        map_mode_button(250,66,"IN-GAME",in_game,1);
        if(in_game){   /* stage 3: the World / Local switch (Tab), as OpenMW's map window has it */
            map_mode_button(LOCALBTN_WORLD_X,LOCALBTN_W,"WORLD",!map_local,1);
            map_mode_button(LOCALBTN_LOCAL_X,LOCALBTN_W,"LOCAL",map_local,marker || local_room);
        }
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
             AW_ConsoleCharWidth()<=4?(normal_teleport_enabled()?"Mid-click mark / R-click target / click edit / H hot":"R-click mark / click edit / H hot / drag pan"):
             (normal_teleport_enabled()?"Mid mark / R target / H hot":"R-click mark / H hot")),240);
        AW_UIFill(CLEAR_X,CLEAR_Y,CLEAR_W,CLEAR_H,AW_UIColor(35,43,47));
        text(CLEAR_X+4,CLEAR_Y+1,"K MARKERS",CLEAR_X+CLEAR_W-1);
        if(normal_teleport_enabled() && teleport_selected)teleport_button_draw(gold);
    }
    mm_draw();
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
        map_world_place();   /* MAP-WORLD-TAB-BLANK-67: the in-game World view's first placement in a game */
        /* Bounded ocean margin also keeps float-to-pixel casts in range. */
        if(map_x<-map_w)map_x=-map_w;
        if(map_x>2*map_w)map_x=2*map_w;
        if(map_y<-map_h)map_y=-map_h;
        if(map_y>2*map_h)map_y=2*map_h;
        map_draw();
    }else if(modal==3)inventory_draw();else if(modal==4)panel_draw();else journal_draw();cursor();scr_copyeverything=1;return 1;
}
