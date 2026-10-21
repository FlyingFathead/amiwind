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
#define INV_PREVIEW_Y 22
#define INV_PREVIEW_W 116
#define INV_PREVIEW_H 168
typedef struct {
    aw_inventory_item_t item[AW_STATE_VALUES];
    unsigned char known[AW_STATE_VALUES];
    int rows[AW_STATE_VALUES],count,selected,top,category,sort,context,context_x,context_y;
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
static char opened_scene[64];
static struct {char id[16],title[32];float x,y,scale;} areas[8];
typedef struct {
    char raw[8192],text[16384],titles[AW_STATE_VALUES][96];unsigned short pages[BOOK_PAGES];
    int count,spread,entry,filter,index_mode,index_top,selection,title_rows,index_end;
    int index_x[AW_STATE_VALUES],index_y[AW_STATE_VALUES],index_rows[AW_STATE_VALUES];
} book_t;
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
    int x=minmax(mouse_x,0,312),y=minmax(mouse_y,0,192),c=AW_UIColor(255,245,190),dark=AW_UIColor(0,0,0);
    AW_UIFill(x,y,3,8,dark);AW_UIFill(x,y,8,3,dark);
    AW_UIFill(x+1,y+1,1,6,c);AW_UIFill(x+1,y+1,6,1,c);
}
static void close_panel(void){
    if(inventory && inventory->preview_frames)
        Con_Printf("Inventory preview (%s): %d renders, last %d ms; %u frames, %d us per frame; picture %d bytes kept, pose model freed after each render.\n",
            AW_ViewInventoryLive()?"live":"still",inventory->preview_renders,(int)(inventory->preview_render_seconds*1000),
            inventory->preview_frames,(int)(inventory->preview_seconds*1e6/inventory->preview_frames),INV_PREVIEW_W*INV_PREVIEW_H);
    free(inventory);inventory=NULL;AW_InventoryPreviewClear();
    free(map_data);map_data=map_pixels=NULL;lava_pools=lava_points=NULL;lava_count=0;free(book);book=NULL;
    if(modal && key_dest==key_menu)key_dest=key_game;
    modal=drag=marker_click=teleport_mode=teleport_selected=0;teleport_message=marker_message=NULL;IN_AWClearButtons();
}
int AW_WorldUIActive(void){return modal!=0;}
/* A button released outside the window must not leave a modal drag held. */
void AW_WorldUICancelDrag(void){drag=marker_click=0;}
static int allowed(void){
    return !modal && key_dest==key_game && sv.active && svs.maxclients==1 && svs.clients &&
        svs.clients[0].edict && cls.state==ca_connected && !AW_StoryRestricted() &&
        !AW_ReaderActive() && !AW_CharacterActive() && !AW_GalleryActive();
}
static void opened(int kind){
    strncpy(opened_scene,sv.name,sizeof(opened_scene)-1);opened_scene[sizeof(opened_scene)-1]=0;
    modal=kind;key_dest=key_menu;IN_AWClearButtons();
}
void AW_InventoryOpen(void){
    int i;
    if(!allowed() || svs.clients[0].edict->v.health<=0)return;
    inventory=(inventory_panel_t *)calloc(1,sizeof(*inventory));
    if(!inventory){Con_Printf("Inventory: not enough memory.\n");return;}
    for(i=0;i<INV_VISIBLE;i++)inventory->icon_row[i]=-1;
    inventory->angle=(float)M_PI;opened(3);
    if(!AW_InventoryBootstrap())strcpy(inventory->message,"Initial item catalogue unavailable.");
    inventory_refresh();
}
static void inventory_refresh(void){
    int i,j,n,order[AW_STATE_VALUES];
    if(!inventory)return;
    n=0;memset(inventory->known,0,sizeof(inventory->known));
    for(i=0;i<aw_state.count[AW_ITEM] && i<AW_STATE_VALUES;i++){
        aw_value_t *v=&aw_state.values[AW_ITEM][i];
        if(v->value<=0)continue;
        memset(&inventory->item[i],0,sizeof(inventory->item[i]));
        inventory->known[i]=AW_InventoryRead(v->id,&inventory->item[i]);
        if(!inventory->known[i]){
            strcpy(inventory->item[i].id,v->id);strcpy(inventory->item[i].name,v->id);
            inventory->item[i].category=AW_INV_MISC;
        }
        if(!inventory->category || inventory->item[i].category==inventory->category)order[n++]=i;
    }
    for(i=1;i<n;i++){
        int value=order[i];j=i;
        while(j>0){
            int previous=order[j-1],cmp;
            if(inventory->sort==1)cmp=inventory->item[previous].value<inventory->item[value].value?1:inventory->item[previous].value>inventory->item[value].value?-1:0;
            else if(inventory->sort==2)cmp=inventory->item[previous].weight<inventory->item[value].weight?1:inventory->item[previous].weight>inventory->item[value].weight?-1:0;
            else cmp=AW_InventoryCompare(inventory->item[previous].name,inventory->item[value].name);
            if(cmp<=0)break;
            order[j]=order[j-1];j--;
        }
        order[j]=value;
    }
    inventory->count=n;
    for(i=0;i<n;i++)inventory->rows[i]=order[i];
    inventory->selected=minmax(inventory->selected,0,n?n-1:0);
    inventory->top=minmax(inventory->top,0,n>INV_VISIBLE?n-INV_VISIBLE:0);
    for(i=0;i<INV_VISIBLE;i++)inventory->icon_row[i]=-1;
}
static aw_inventory_item_t *inventory_selected(void){
    return inventory && inventory->count?&inventory->item[inventory->rows[inventory->selected]]:NULL;
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
    if(key==K_TAB){inventory->category=(inventory->category+1)%8;inventory->selected=inventory->top=0;inventory_refresh();}
    if(key=='o'){inventory->sort=(inventory->sort+1)%3;inventory_refresh();}
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
                if(mouse_x>=x && mouse_x<x+width){inventory->category=i;inventory->selected=inventory->top=0;inventory_refresh();return;}x+=width;
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
static void inventory_icon(int slot,int index,int x,int y){
    FILE *f=NULL;int size,xx,yy;byte raw[1028];
    if(aw_inventory_row_icon && aw_inventory_row_icon(slot,inventory->item[index].id,
        AW_InventoryEquipped(&aw_state,inventory->item[index].id)>0,x,y))return;
    if(inventory->icon_row[slot]!=index){
        inventory->icon_row[slot]=index;inventory->icon_ok[slot]=0;
        if(inventory->item[index].icon[0]){
            size=COM_FOpenFile(inventory->item[index].icon,&f);
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
static void inventory_draw(void){
    int i,j,x,row,index,right=inventory_list_right();aw_inventory_item_t *item;char line[160];
    int gold=AW_UIColor(223,199,144),muted=AW_UIColor(150,135,104);
    AW_UIFill(0,0,320,200,AW_UIColor(0,0,0));AW_UIBox(2,2,316,196);
    AW_UIBox(4,18,122,178);AW_UIBox(128,18,188,178);
    AW_UISmallBegin();
    window_title(6,6,308,inventory_title(),gold);
    AW_UISmallEnd();
    inventory_preview(muted);
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
        index=inventory->rows[row];item=&inventory->item[index];
        if(row==inventory->selected)AW_UIFill(130,INV_LIST_Y+i*INV_ROW_H,right-130,INV_ROW_H,AW_UIColor(44,36,20));
        inventory_icon(i,index,132,INV_LIST_Y+i*INV_ROW_H);
        sprintf(line,"%s%s",AW_InventoryEquipped(&aw_state,item->id)?"* ":"",item->name);
        inventory_text(151,INV_LIST_Y+i*INV_ROW_H,right-24-151,11,line,gold);
        sprintf(line,"%ld",(long)AW_StateGet(&aw_state,AW_ITEM,item->id));inventory_text(right-22,INV_LIST_Y+i*INV_ROW_H,22,11,line,gold);
    }
    if(inventory->count>INV_VISIBLE)
        AW_UIScrollbar(INV_SCROLL_X,INV_LIST_Y,INV_SCROLL_H,inventory->count,INV_VISIBLE,inventory->top);
    item=inventory_selected();
    if(item){
        index=inventory->rows[inventory->selected];
        if(inventory->known[index])sprintf(line,"Weight %.2f  Value %ld",item->weight,(long)item->value);
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
    map_data=(byte *)malloc(size);if(!map_data)goto bad;
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
static int entry_text(const char *id,int stage,char *out,int capacity){
    FILE *f=NULL;byte header[8],row[76];int size,count,lo,hi,mid,cmp,found=0;uint32_t offset=0,length=0;long base;
    size=COM_FOpenFile("world/journal.awj",&f);if(!f)return 0;
    base=ftell(f);
    if(size<8 || fread(header,1,8,f)!=8 || memcmp(header,"AWJ1",4))goto end_index;
    count=(int)u32(header+4);if(count<0 || count>10000 || size!=8+count*76)goto end_index;
    lo=0;hi=count;
    while(lo<hi){
        mid=lo+(hi-lo)/2;
        if(fseek(f,base+8+(long)mid*76,SEEK_SET) || fread(row,1,76,f)!=76 || !memchr(row,0,64))break;
        cmp=strcmp(id,(char *)row);
        if(!cmp){int value=(int32_t)u32(row+64);cmp=stage<value?-1:stage>value?1:0;}
        if(!cmp){offset=u32(row+68);length=u32(row+72);found=1;break;}
        if(cmp<0)hi=mid;else lo=mid+1;
    }
 end_index:
    fclose(f);f=NULL;if(!found || length<1 || length>(uint32_t)capacity)return 0;
    size=COM_FOpenFile("world/entries.dat",&f);if(!f)return 0;base=ftell(f);
    found=size>0 && offset<=(uint32_t)size && length<=(uint32_t)size-offset &&
        !fseek(f,base+offset,SEEK_SET) && fread(out,1,length,f)==length;
    fclose(f);
    return found && !out[length-1] && !memchr(out,0,length-1);
}
static int expand_entry(void){
    const char *p=book->raw,*value;int n=0,skip;
    while(*p){
        value=NULL;skip=0;
        if(!strncmp(p,"%PCName",7)){value=aw_story.name;skip=7;}
        else if(aw_character.valid && !strncmp(p,"%PCRace",7)){value=aw_races[aw_character.race].name;skip=7;}
        else if(aw_character.valid && !strncmp(p,"%PCClass",8)){value=aw_classes[aw_character.clas].name;skip=8;}
        if(value){while(*value){if(n>=(int)sizeof(book->text)-1)return 0;book->text[n++]=*value++;}p+=skip;}
        else {if(n>=(int)sizeof(book->text)-1)return 0;book->text[n++]=*p++;}
    }
    book->text[n]=0;return 1;
}
static int eligible(int i){return i>=0 && i<aw_state.journal_count && (book->filter<0 || aw_state.journal[i].quest==book->filter);}
static int next_entry(int i,int step){for(i+=step;i>=0 && i<aw_state.journal_count;i+=step)if(eligible(i))return i;return -1;}
/* Centre only already-wrapped lines: AW_UITextBox does not clip. */
static int title_rows(const char *p){
    char line[160];int rows=0;
    do {p=AW_UILine(p,BOOK_WIDTH,line,sizeof(line));rows++;}while(*p);
    return rows;
}
static int page_lines(int page){return BOOK_LINES-((page&1)?0:book->title_rows-1);}
static void index_layout(void){
    int i,col=0,row=0,lines;
    for(i=book->index_top;i<aw_state.count[AW_JOURNAL];i++){
        lines=title_rows(book->titles[i]);
        if(row+lines>BOOK_LINES){col++;row=0;}
        if(col>=2)break;
        book->index_x[i]=14+col*156;book->index_y[i]=40+row*14;book->index_rows[i]=lines;
        row+=lines+1;
    }
    book->index_end=i;
}
static void load_entry(int index){
    int i;const char *p,*before;char line[160];aw_journal_entry_t *entry;
    book->entry=index;book->spread=0;book->count=0;
    if(index<0){strcpy(book->text,"No dated journal entries have been recorded yet. Entries appear here as you earn them during play.");}
    else {
        entry=&aw_state.journal[index];
        if(!entry_text(aw_state.values[AW_JOURNAL][entry->quest].id,entry->stage,book->raw,sizeof(book->raw)))
            strcpy(book->text,"This earned entry has no matching text in the installed journal catalogue. Its quest stage and date remain saved.");
        else if(!expand_entry())strcpy(book->text,"This entry exceeds the reader's text capacity. Its saved history remains intact.");
    }
    AW_UIBookBegin();book->title_rows=1;
    if(index>=0){
        book->title_rows=title_rows(book->titles[aw_state.journal[index].quest]);
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
static void quest_titles(void){
    FILE *f=NULL;byte header[8],row[160];int i,j,count,size;
    for(i=0;i<aw_state.count[AW_JOURNAL];i++){
        strcpy(book->titles[i],aw_state.values[AW_JOURNAL][i].id);
        for(j=0;book->titles[i][j];j++)if(book->titles[i][j]=='_')book->titles[i][j]=' ';
    }
    if(!aw_state.count[AW_JOURNAL])return;
    size=COM_FOpenFile("world/quests.awq",&f);if(!f)return;
    if(size<8 || fread(header,1,8,f)!=8 || memcmp(header,"AWQ1",4)){fclose(f);return;}
    count=(int)u32(header+4);
    if(count<0 || count>10000 || size!=8+count*160){fclose(f);return;}
    for(i=0;i<count;i++){
        if(fread(row,1,160,f)!=160 || !memchr(row,0,64) || !memchr(row+64,0,96))break;
        for(j=0;j<aw_state.count[AW_JOURNAL];j++)if(!strcmp((char *)row,aw_state.values[AW_JOURNAL][j].id))
            memcpy(book->titles[j],row+64,96);
    }
    fclose(f);
}
static void open_journal(void){
    if(!allowed())return;
    book=(book_t *)calloc(1,sizeof(*book));if(!book){Con_Printf("Journal reader: not enough memory.\n");return;}
    quest_titles();book->filter=-1;load_entry(aw_state.journal_count-1);opened(2);
    Con_Printf("Journal: %ld earned entries; reader %ld bytes.\n",(long)aw_state.journal_count,(long)sizeof(*book));
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
        top=AW_UIScrollHit(306,minmax(mouse_y,40,165),304,40,126,aw_state.count[AW_JOURNAL],(book->index_end-book->index_top),book->index_top);
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
    if(key==K_ESCAPE || (modal==1 && (key=='m' || key=='M')) || (modal==2 && (key=='j' || key=='J')) || (modal==3 && (key=='i' || key=='I'))){close_panel();return 1;}
    if(modal==3){inventory_key(key);return 1;}
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
    }else if(book->index_mode){
        n=aw_state.count[AW_JOURNAL];
        AW_UIBookBegin();index_layout();AW_UIBookEnd();
        if(key==K_TAB){book->index_mode=0;return 1;}
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
            book->selection=n;n=aw_state.count[AW_JOURNAL];key=K_ENTER;
        }
        book->selection=minmax(book->selection,0,n?n-1:0);
        if(book->selection<book->index_top)book->index_top=book->selection;
        AW_UIBookBegin();index_layout();
        while(book->selection>=book->index_end && book->index_top<book->selection){book->index_top++;index_layout();}
        AW_UIBookEnd();
        if(key==K_ENTER && n){book->filter=book->selection;book->index_mode=0;load_entry(next_entry(aw_state.journal_count,-1));}
        if(key==K_MOUSE1 && mouse_y>=176){book->index_mode=0;book->filter=-1;load_entry(aw_state.journal_count-1);}
    }else{
        if(key==K_TAB){book->index_mode=1;book->selection=book->index_top=0;return 1;}
        if(key==K_BACKSPACE){book->filter=-1;load_entry(aw_state.journal_count-1);return 1;}
        if(key==K_MOUSE1){
            if(mouse_y>=26 && mouse_y<26+book->title_rows*14 && mouse_x>=14 && mouse_x<146 && book->entry>=0){
                book->filter=aw_state.journal[book->entry].quest;load_entry(next_entry(aw_state.journal_count,-1));return 1;
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
        if(key==K_END)load_entry(next_entry(aw_state.journal_count,-1));
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
            if(in_game){edict_t *e=svs.clients[0].edict;angle=e->v.angles[1]*(3.14159265f/180.0f);dx=Q_CosRad(angle);dy=-Q_SinRad(angle);
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
    static const int month_days[12]={31,28,31,30,31,30,31,31,30,31,30,31};
    int i,j,x,y,entry=book->entry,page,ink=AW_UIColor(38,29,20),gold=AW_UIColor(103,65,27),d,m,year;
    char line[160];const char *p;aw_journal_entry_t *e;
    AW_UIFill(0,0,320,200,AW_UIColor(29,23,17));
    AW_UIFill(5,5,153,190,AW_UIColor(223,207,166));AW_UIFill(162,5,153,190,AW_UIColor(232,217,180));
    AW_UIFill(158,5,4,190,AW_UIColor(92,70,43));
    AW_UIBookBegin();
    if(book->index_mode){
        AW_UITextBox(14,12,BOOK_WIDTH,14,"Quests",ink);
        AW_UITextBox(170,12,BOOK_WIDTH,14,"Journal",ink);
        index_layout();
        for(j=book->index_top;j<book->index_end;j++){
            x=book->index_x[j];y=book->index_y[j];
            if(j==book->selection)AW_UIFill(x-4,y,140,book->index_rows[j]*14,AW_UIColor(203,186,145));
            p=book->titles[j];
            for(i=0;i<book->index_rows[j];i++){
                p=AW_UILine(p,BOOK_WIDTH,line,sizeof(line));
                AW_UITextBox(x,y+i*14,BOOK_WIDTH,14,line,gold);
            }
        }
        AW_UIScrollbar(304,40,126,aw_state.count[AW_JOURNAL],(book->index_end-book->index_top),book->index_top);
        if(!aw_state.count[AW_JOURNAL])AW_UITextBox(14,42,BOOK_WIDTH,14,"No quests yet.",ink);
        AW_UITextBox(14,176,BOOK_WIDTH,12,"Tab: return",ink);
        AW_UITextBox(170,176,BOOK_WIDTH,12,"All entries",gold);
    }else{
        if(entry>=0){
            e=&aw_state.journal[entry];d=e->days+227;year=427+d/365;d%=365;m=0;
            while(d>=month_days[m])d-=month_days[m++];
            sprintf(line,"%02ld/%02ld/%ld",(long)d+1,(long)m+1,(long)year);AW_UIText(14,10,line,ink);
            AW_UITextBox(170,10,132,14,"Journal",ink);
            p=book->titles[e->quest];
            for(i=0;i<book->title_rows;i++){
                p=AW_UILine(p,BOOK_WIDTH,line,sizeof(line));
                AW_UITextBox(14,26+i*14,BOOK_WIDTH,14,line,gold);
            }
        }else AW_UIText(14,12,"Journal",ink);
        for(j=0;j<2;j++){
            page=book->spread+j;if(page>=book->count)continue;p=book->text+book->pages[page];
            y=44+(j?0:(book->title_rows-1)*14);
            for(i=0;i<page_lines(page) && *p;i++){p=AW_UILine(p,BOOK_WIDTH,line,sizeof(line));AW_UIText(14+j*156,y+i*14,line,ink);}
        }
        AW_UIText(14,176,"< Previous",gold);AW_UIText(239,176,"Next >",gold);
        AW_UITextBox(102,174,44,14,"Quests",gold);
    }
    AW_UIBookEnd();
    sprintf(line,"%ld/%ld  Tab quests Backspace all J close",(long)(entry+1),(long)aw_state.journal_count);
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
    }else if(modal==3)inventory_draw();else journal_draw();cursor();scr_copyeverything=1;return 1;
}
