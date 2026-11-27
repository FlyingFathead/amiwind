/* SPDX-License-Identifier: GPL-3.0-only
 * Actual world UI events + actual inventory transactions; synthetic item data
 * and a recorded placement decision isolate host interaction from native I/O. */
#define COM_FOpenFile __wrap_COM_FOpenFile
#define AW_SmallStringColor legacy_inventory_text
#define AW_UITextBox legacy_inventory_textbox
#define AW_UITextCentred legacy_inventory_centred
#define AW_UIScrollbar legacy_inventory_scrollbar
#define AW_UIScrollHit legacy_inventory_scrollhit
#define main map_journal_regressions
#include "aga_worldui_test.c"
#undef main
#undef AW_UIScrollbar
#undef AW_UIScrollHit
#undef AW_SmallStringColor
#undef AW_UITextBox
#undef AW_UITextCentred
#undef COM_FOpenFile
#include "aw_inventory.h"
#include "aw_harvest.h"
static aw_harvest_t h;
#include "aga_harvest_fixture.h"
typedef struct {int x,y,width,color;char value[160];} layout_text_t;
static layout_text_t layout_text[128];   /* the window and the information box over it */
static int layout_capture,layout_count,layout_mode,layout_noactions;
/* INVENTORY-EQUIP-HINTS-67: one carried item of every kind the window tells apart (the catalogue rows as
 * tools/prepare_inventory.py writes them), listed by name in this order */
static int kinds_mode;
static aw_inventory_item_t kinds[7];
static void kinds_fill(void){
    int i;memset(kinds,0,sizeof(kinds));
    for(i=0;i<7;i++)strcpy(kinds[i].model,"progs/inv/fixture.mdl");
    strcpy(kinds[0].id,"a_ring");strcpy(kinds[0].name,"A Ring");kinds[0].category=AW_INV_CLOTHING;
    kinds[0].slots=(1U<<AW_SLOT_LRING)|(1U<<AW_SLOT_RRING);kinds[0].flags=AW_INV_EQUIP|AW_INV_DROP|AW_INV_EQUIP_SUPPORTED;
    kinds[1]=kinds[0];strcpy(kinds[1].id,"b_ring");strcpy(kinds[1].name,"B Ring");
    strcpy(kinds[2].id,"c_potion");strcpy(kinds[2].name,"C Potion");kinds[2].category=AW_INV_POTION;
    kinds[2].flags=AW_INV_ALCHEMY|AW_INV_DROP;kinds[2].alchemy_kind=AW_ALCHEMY_POTION;
    /* a Cast Once scroll (BOOK, the enchantment's kind AW_ENCH_ONCE): Use casts it (SCROLL-CAST-64) */
    strcpy(kinds[3].id,"d_scroll");strcpy(kinds[3].name,"D Scroll");kinds[3].category=AW_INV_BOOK;
    kinds[3].flags=AW_INV_DROP;kinds[3].enchant_kind=AW_ENCH_ONCE;strcpy(kinds[3].enchantment,"d_scroll_en");
    strcpy(kinds[4].id,"e_book");strcpy(kinds[4].name,"E Book");kinds[4].category=AW_INV_BOOK;kinds[4].flags=AW_INV_DROP;
    strcpy(kinds[5].id,"f_rock");strcpy(kinds[5].name,"F Rock");kinds[5].category=AW_INV_MISC;kinds[5].flags=AW_INV_DROP;
    strcpy(kinds[6].id,"g_root");strcpy(kinds[6].name,"G Root");kinds[6].category=AW_INV_INGREDIENT;
    kinds[6].flags=AW_INV_ALCHEMY|AW_INV_DROP;kinds[6].alchemy_kind=AW_ALCHEMY_INGREDIENT;
}
#include "aw_iteminfo.h"
/* INVENTORY-ITEM-INFO-67: a book's text as the reader's hook gives it (a fresh allocation the window frees) */
static int book_calls;
static char *test_book_text(const char *id){
    char *t=(char *)malloc(4000);int k;(void)id;book_calls++;
    if(!t)return NULL;
    strcpy(t,"First words of the book.");
    for(k=0;k<40;k++)strcat(t," And the book goes on for many lines more.");
    return t;
}
static int cast_calls,read_calls;static char cast_id[64],read_id[64];
static int test_cast(const aw_inventory_item_t *it){cast_calls++;strcpy(cast_id,it->id);return 1;}
static int test_read(const char *id){read_calls++;strcpy(read_id,id);return 1;}
extern int (*aw_worldui_cast)(const aw_inventory_item_t *it);
extern int (*aw_worldui_read)(const char *id);
/* Controlled shared-helper results test modal routing, not a duplicate of the
 * scrollbar algorithm. aga_ui_test.c exercises the actual shared helper. */
static int scroll_mode,scroll_target=-1,scroll_calls,scroll_top,scroll_total;
void AW_UIScrollbar(int x,int y,int height,int total,int visible,int top){
    if(scroll_mode){
        assert(x==304 && y==54 && height==96 && visible==6 && total>visible);
        scroll_calls++;scroll_top=top;scroll_total=total;
    }
}
int AW_UIScrollHit(int mx,int my,int x,int y,int height,int total,int visible,int top){
    (void)top;
    if(!scroll_mode || total<=visible || mx<x || mx>=x+10 || my<y || my>=y+height)return -1;
    assert(x==304 && y==54 && height==96 && visible==6);
    assert(scroll_target>=0 && scroll_target<=total-visible);
    return scroll_target;
}
static char layout_title[160];
void AW_SmallStringColor(int x,int y,int width,const char *value,int color){
    legacy_inventory_text(x,y,width,value,color);
    if(layout_capture){
        layout_text_t *entry;assert(layout_count<128);entry=&layout_text[layout_count++];
        entry->x=x;entry->y=y;entry->width=width;entry->color=color;
        strncpy(entry->value,value,sizeof(entry->value)-1);entry->value[sizeof(entry->value)-1]=0;
    }
}
void AW_UITextBox(int x,int y,int w,int h,const char *value,int color){
    legacy_inventory_textbox(x,y,w,h,value,color);
    if(layout_capture && x==6 && y==6){
        strncpy(layout_title,value,sizeof(layout_title)-1);layout_title[sizeof(layout_title)-1]=0;
    }
}
/* The window title (UI-INVENTORY-HEADING-CENTRE-42) is centred by painted bounds; same text record. */
void AW_UITextCentred(int x,int y,int w,int h,const char *s,int c){AW_UITextBox(x,y,w,h,s,c);}
static const layout_text_t *layout_find(const char *value){
    int i;for(i=0;i<layout_count;i++)if(strstr(layout_text[i].value,value))return &layout_text[i];
    return NULL;
}
static void layout_point(int x,int y){AW_WorldUIMouse(-1000,-1000);AW_WorldUIMouse(x,y);}
static void layout_draw(void){
    int i;layout_count=0;layout_title[0]=0;draw();
    for(i=0;i<layout_count;i++){
        const layout_text_t *entry=&layout_text[i];
        assert(entry->x>=128 && entry->x+entry->width<=316);
        if(entry->y>=152){
            assert(entry->x>=132 && entry->x+entry->width<=312);
            assert(entry->y+5<=189); /* at least3clear pixels before border192 */
        }
    }
}
static int placement=1,preview_calls,store_calls,changed_calls;
static aw_inventory_item_t fixture_item;
static int sorting;
int AW_InventoryBootstrap(void){aw_state.inventory.initialized=1;return 1;}
int AW_InventoryRead(const char *id,aw_inventory_item_t *out){
    if(kinds_mode){
        int i;for(i=0;i<7;i++)if(!strcmp(id,kinds[i].id)){*out=kinds[i];return 1;}
        return 0;
    }
    if(scroll_mode){
        int i;char key[32];
        for(i=0;i<12;i++){
            sprintf(key,"scroll_%02d",i);
            if(strcmp(id,key))continue;
            *out=fixture_item;strcpy(out->id,id);sprintf(out->name,"Scroll%02d",i);return 1;
        }
        return 0;
    }
    if(layout_mode){
        int i;char key[32];
        for(i=0;i<6;i++){
            sprintf(key,"layout_item_%d",i);
            if(strcmp(id,key))continue;
            *out=fixture_item;strcpy(out->id,id);
            sprintf(out->name,"%c very long original item name that cannot fit its list column",'A'+i);
            if(layout_noactions && i==5)out->flags=0;
            return 1;
        }
        return 0;
    }
    if(sorting){
        *out=fixture_item;strcpy(out->id,id);
        if(!strcmp(id,"sort_z")){strcpy(out->name,"Zulu");out->value=30;out->weight=1;}
        else if(!strcmp(id,"sort_a")){strcpy(out->name,"alpha");out->value=10;out->weight=2;}
        else if(!strcmp(id,"sort_m")){strcpy(out->name,"Middle");out->value=20;out->weight=3;}
        else return 0;
        return 1;
    }
    if(strcmp(id,fixture_item.id))return 0;*out=fixture_item;return 1;
}
int AW_InventoryCanEquip(const aw_inventory_item_t *item){return item && (item->flags&AW_INV_EQUIP_SUPPORTED)!=0;}
int AW_InventoryDropHere(const aw_inventory_item_t *item,int32_t amount){
    float position[3]={20,30,40};
    if(!placement)return 0;
    return AW_InventoryDrop(&aw_state,item,amount,"seyda",position,0)>=0;
}
const char *AW_InventoryDropReason(void){
    return layout_mode?"Cannot place this item on the chosen floor; choose a clear spot. The carried item was kept.":
        "Cannot place item here; kept.";
}
/* DROP-REFUSED-CENSUS-ROOM-67: the refusal's reason only behind the debug HUD (dbg all; aga_worldui_test.c's
 * debug_overlays, on): the long reason below checks the status line's wrapping, then off for the player's plain line */
void AW_CombatEquipmentStore(void){store_calls++;}
void AW_CombatEquipmentChanged(void){changed_calls++;}
int AW_ViewInventoryBody(model_t **model,int *frame){static model_t body;*model=&body;*frame=7;return 1;}
int AW_InventoryPreviewDraw(model_t *model,int frame,int x,int y,int width,int height,float angle){
    (void)model;(void)angle;assert(frame==7 && x<128 && y==32 && width==116 && height==150);assert(angle>3.14f && angle<3.15f);preview_calls++;return 1;
}
/* INVENTORY-PREVIEW-STALE-61: the assembled body still loading a changed outfit's parts (aw_view.c parts_pending),
 * and the clock the picture's wait is measured by */
static int parts_loading;static double test_clock=100;
static int test_parts_pending(void){return parts_loading;}
extern int (*aw_inventory_preview_pending)(void);
double Sys_FloatTime(void){return test_clock;}
/* ENCUMBRANCE-INCOMPLETE-61: the player's burden as aw_move.c gives it (12.2 of 300) */
static float test_burden(float *capacity){*capacity=300;return 12.2f;}
extern float (*aw_worldui_encumbrance)(float *capacity);
/* INVENTORY-NO-ARMOR-RATING-61: the player's armour rating as aw_combat.c gives it, and how often it is asked */
static float test_armor_value=17.8f;static int armor_calls;
static float test_armor(void){armor_calls++;return test_armor_value;}
extern float (*aw_worldui_armor_rating)(void);
/* INVENTORY-DOUBLECLICK-62: one click (press and release) at the pointer; the potion's use as aw_alchemy.c does it
 * (one taken from the stack), counted */
static void click(void){AW_WorldUIKey(K_MOUSE1,1);AW_WorldUIKey(K_MOUSE1,0);}
static int uses;
static int test_use(const aw_inventory_item_t *it){uses++;return AW_ItemAdd(&aw_state,it->id,-1)?1:0;}
int main(void){
    static client_t client;static edict_t actor;aw_state_t before;int calls;
    {   /* the world UI test whole (its main takes an optional part name since MAP-WORLD-TAB-BLANK-67: none here) */
        static char name[]="aga_worldui_test",*argv[]={name,NULL};
        assert(!map_journal_regressions(1,argv));
    }
    key_dest=key_game;cls.state=ca_connected;sv.active=1;svs.maxclients=1;svs.clients=&client;client.edict=&actor;
    actor.v.health=100;strcpy(sv.name,"seyda");memset(&aw_state,0,sizeof(aw_state));
    memset(&fixture_item,0,sizeof(fixture_item));strcpy(fixture_item.id,"fixture_ring");strcpy(fixture_item.name,"Fixture Ring");
    strcpy(fixture_item.model,"progs/inv/fixture.mdl");fixture_item.category=AW_INV_CLOTHING;
    fixture_item.slots=(1U<<AW_SLOT_LRING)|(1U<<AW_SLOT_RRING);fixture_item.flags=7;
    assert(AW_ItemAdd(&aw_state,fixture_item.id,2));
    /* CHARGEN-INVENTORY-LOCKED-60: during the registration the inventory key opens the window once the papers are
     * activated (story_inventory), the map and journal stay closed until the registration ends */
    story_restricted=1;AW_InventoryOpen();assert(!AW_InventoryActive() && key_dest==key_game);
    story_inventory=1;map_command();assert(!AW_WorldUIActive());journal_command();assert(!AW_WorldUIActive());
    AW_InventoryOpen();assert(AW_InventoryActive() && key_dest==key_menu);
    AW_WorldUIKey('i',1);assert(!AW_InventoryActive() && key_dest==key_game);
    story_restricted=story_inventory=0;preview_calls=0;
    AW_InventoryOpen();assert(AW_InventoryActive() && key_dest==key_menu);draw();assert(preview_calls==1);
    assert(strstr(drawn,"Fixture Ring") && strstr(drawn,"Sort: Name"));
    /* the burden bar above the picture (OpenMW inventorywindow.cpp: ceil(encumbrance) / capacity on the blue bar) */
    assert(!bar_calls);aw_worldui_encumbrance=test_burden;draw();
    assert(bar_calls==1 && bar_colour==1 && bar_x==8 && bar_y==21 && bar_w==114 && bar_h==9 && bar_y+bar_h<=32);
    assert(bar_fraction>13/300.0f-1e-4f && bar_fraction<13/300.0f+1e-4f && strstr(drawn,"13/300"));
    aw_worldui_encumbrance=NULL;
    /* UI-INVENTORY-PREVIEW-STILL-42: a still picture: one render, then the same pose and the
     * front angle frame after frame (the stub asserts the angle); turning keys do nothing. */
    {int i;for(i=0;i<8;i++)draw();}
    assert(preview_calls==1);
    /* The footer offers turning only with the live preview (it is off here). */
    assert(strstr(drawn,"Up/Down select") && !strstr(drawn,"Left/Right turn"));
    AW_WorldUIKey(K_LEFTARROW,1);AW_WorldUIKey(K_RIGHTARROW,1);AW_WorldUIKey(K_RIGHTARROW,1);draw();
    assert(preview_calls==1);
    AW_WorldUIKey('e',1);assert(AW_InventoryEquipped(&aw_state,fixture_item.id)==1);assert(store_calls && changed_calls);
    draw();draw();assert(preview_calls==2);   /* the equipment changed: one new picture */
    /* INVENTORY-PREVIEW-STALE-61: while the new outfit's parts load, the picture waits (the kept one shown) and is
     * rendered once they are all in, never of the previous outfit; a load that never ends waits 5 s at most */
    aw_inventory_preview_pending=test_parts_pending;
    AW_WorldUIKey('e',1);parts_loading=1;draw();draw();draw();assert(preview_calls==2);
    parts_loading=0;draw();draw();assert(preview_calls==3);
    AW_WorldUIKey('e',1);assert(AW_InventoryEquipped(&aw_state,fixture_item.id)==1);
    parts_loading=1;draw();test_clock+=4.9;draw();assert(preview_calls==3);
    test_clock+=.2;draw();assert(preview_calls==4);draw();assert(preview_calls==4);
    parts_loading=0;aw_inventory_preview_pending=NULL;
    /* INVENTORY-NO-ARMOR-RATING-61: "Armor: N" under the picture (OpenMW inventorywindow.cpp updateArmorRating: the
     * whole number), asked once and again only after an action, not every frame */
    aw_worldui_armor_rating=test_armor;armor_calls=0;layout_capture=1;layout_count=0;draw();
    assert(strstr(drawn,"Armor: 17") && armor_calls==1);
    {const layout_text_t *a=NULL;int k,shadow=0;
     for(k=0;k<layout_count;k++)if(strstr(layout_text[k].value,"Armor: 17")){
         if(layout_text[k].y==186)a=&layout_text[k];else if(layout_text[k].y==187)shadow++;
     }
     assert(a && shadow==1);                                                              /* the burden bar's shadow */
     assert(a->x>=7 && a->x+a->width<=123 && a->y+5<=195 && a->y>=32+150);               /* under the picture */
     assert(abs((a->x+a->width/2)-(7+116/2))<=2);}                                       /* centred under it */
    layout_capture=0;draw();draw();assert(armor_calls==1);
    test_armor_value=25.6f;
    AW_WorldUIKey('e',1);assert(!AW_InventoryEquipped(&aw_state,fixture_item.id));
    draw();assert(strstr(drawn,"Armor: 25") && armor_calls==2);
    test_armor_value=-1;AW_WorldUIKey('e',1);draw();assert(!strstr(drawn,"Armor") && armor_calls==3);   /* unavailable */
    draw();assert(armor_calls==3);
    AW_WorldUIKey('e',1);assert(!AW_InventoryEquipped(&aw_state,fixture_item.id));
    aw_worldui_armor_rating=NULL;test_armor_value=17.8f;
    /* INVENTORY-OPEN-WINDOW-NO-REFRESH-61: worn, taken off or given from outside the window while it is open (the
     * console, a script): the picture, the armour rating, the row mark and the list follow at the next frame, without
     * reopening (OpenMW inventorywindow.cpp updateItemView + dirtyPreview on every store change); frames with no
     * change render nothing again */
    /* INVENTORY-EQUIPPED-LABEL-67: the worn row's mark is the word "Equipped" (in the highlight colour), not a "* " */
    draw();calls=preview_calls;draw();draw();assert(preview_calls==calls && !strstr(drawn,"Equipped"));
    aw_worldui_armor_rating=test_armor;armor_calls=0;draw();assert(armor_calls==1);
    assert(AW_InventoryEquip(&aw_state,&fixture_item));
    draw();assert(preview_calls==calls+1 && armor_calls==2 && strstr(drawn,"Equipped") && !strstr(drawn,"* Fixture"));
    draw();draw();assert(preview_calls==calls+1 && armor_calls==2);
    assert(AW_InventoryUnequip(&aw_state,fixture_item.id));
    draw();assert(preview_calls==calls+2 && armor_calls==3 && !strstr(drawn,"Equipped"));
    aw_worldui_armor_rating=NULL;
    assert(!strstr(drawn,"fixture_robe"));
    assert(AW_ItemAdd(&aw_state,"fixture_robe",1));draw();assert(strstr(drawn,"fixture_robe"));
    assert(preview_calls==calls+2);                          /* a new kind alone: the list, not the picture */
    assert(AW_ItemAdd(&aw_state,"fixture_robe",-1));draw();assert(!strstr(drawn,"fixture_robe"));
    /* the window's own Equip renders once, not again for the change it made itself */
    AW_WorldUIKey('e',1);draw();draw();assert(preview_calls==calls+3);
    AW_WorldUIKey('e',1);draw();assert(preview_calls==calls+4 && !AW_InventoryEquipped(&aw_state,fixture_item.id));
    /* Right click selects the actual row; Enter-equivalent action is real. */
    AW_WorldUIMouse(-1000,-1000);AW_WorldUIMouse(160,60);AW_WorldUIKey(K_MOUSE3,1);draw();assert(strstr(drawn,"Equip"));
    AW_WorldUIKey(K_MOUSE1,1);assert(AW_InventoryEquipped(&aw_state,fixture_item.id)==1);
    placement=0;before=aw_state;AW_WorldUIKey('d',1);assert(!memcmp(&before,&aw_state,sizeof(before)));
    draw();assert(strstr(drawn,"kept"));placement=1;AW_WorldUIKey('d',1);
    assert(AW_StateGet(&aw_state,AW_ITEM,fixture_item.id)==1 && aw_state.inventory.dropped[0].count==1);
    AW_WorldUIKey(K_TAB,1);draw();assert(strstr(drawn,"No carried items"));
    AW_WorldUIKey('i',1);assert(!AW_InventoryActive() && key_dest==key_game);
    fixture_item.flags=0;AW_InventoryOpen();AW_WorldUIKey(K_MOUSE3,1);draw();
    assert(!strstr(drawn,"Unequip") && !strstr(drawn,"Drop one"));
    calls=changed_calls;before=aw_state;AW_WorldUIKey('e',1);AW_WorldUIKey('d',1);
    assert(!memcmp(&before,&aw_state,sizeof(before)) && changed_calls==calls);
    assert(!AW_WorldUIKey(K_F10,1));assert(!AW_InventoryActive() && key_dest==key_game);
    /* Insertion order deliberately opposes name order; exercise the rendered
     * modal and real sort keys, not just the comparator in isolation. */
    memset(&aw_state,0,sizeof(aw_state));sorting=1;
    assert(AW_ItemAdd(&aw_state,"sort_z",1));assert(AW_ItemAdd(&aw_state,"sort_a",1));assert(AW_ItemAdd(&aw_state,"sort_m",1));
    AW_InventoryOpen();draw();
    assert(strstr(drawn,"alpha") && strstr(drawn,"Middle") && strstr(drawn,"Zulu"));
    assert(strstr(drawn,"alpha")<strstr(drawn,"Middle") && strstr(drawn,"Middle")<strstr(drawn,"Zulu"));
    AW_WorldUIKey('o',1);draw();
    assert(strstr(drawn,"Zulu")<strstr(drawn,"Middle") && strstr(drawn,"Middle")<strstr(drawn,"alpha"));
    AW_WorldUIKey('o',1);draw();
    assert(strstr(drawn,"Middle")<strstr(drawn,"alpha") && strstr(drawn,"alpha")<strstr(drawn,"Zulu"));
    AW_WorldUIKey('i',1);
    /* An earned harvest award must reach the actual panel, not a second UI
     * inventory. Opening/closing discards panel caches, never ownership. */
    sorting=0;memset(&aw_state,0,sizeof(aw_state));
    memset(&fixture_item,0,sizeof(fixture_item));
    strcpy(fixture_item.id,"fixture_mushroom_ingredient");
    strcpy(fixture_item.name,"Picked Mushroom");fixture_item.category=AW_INV_INGREDIENT;
    AW_InventoryOpen();draw();assert(strstr(drawn,"No carried items"));
    AW_WorldUIKey('i',1);assert(!AW_InventoryActive());
    AW_HarvestInitData(&h);harvest_fixture_storage();h.nodes=h.edges=h.plants=1;
    strcpy(HSTR(h.node[0].id),fixture_item.id);
    strcpy(HSTR(h.node[0].label),fixture_item.name);
    h.edge[0].node=0;h.edge[0].level=1;h.edge[0].count=1;
    strcpy(HSTR(h.plant[0].key),"aw:h:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
    strcpy(HSTR(h.plant[0].label),"Synthetic harvest plant");strcpy(HSTR(h.plant[0].model),"*1");
    h.plant[0].reference=42;h.plant[0].flags=11;h.plant[0].first=0;h.plant[0].count=1;
    assert(AW_HarvestValidate(&h));
    assert(AW_HarvestTake(&h,0,&aw_state,1,123)==1);
    assert(AW_StateGet(&aw_state,AW_ITEM,fixture_item.id)==1 && AW_HarvestPickedCount(&aw_state)==1);
    before=aw_state;
    for(calls=0;calls<3;calls++){
        AW_InventoryOpen();assert(AW_InventoryActive());draw();
        assert(strstr(drawn,"Picked Mushroom1")); /* rendered name then quantity column */
        assert(AW_StateGet(&aw_state,AW_ITEM,fixture_item.id)==1);
        AW_WorldUIKey(calls==1?K_ESCAPE:'i',1);
        assert(!AW_InventoryActive() && key_dest==key_game);
        assert(!memcmp(&before,&aw_state,sizeof(before)));
    }
    assert(AW_HarvestTake(&h,0,&aw_state,1,999)==0);
    assert(!memcmp(&before,&aw_state,sizeof(before))); /* no duplicate award on repeat use */
    AW_HarvestRelease(&h);
    /* Bounded footer/status geometry and actual displayed-action hitboxes.
     * Long names retain the unchanged glyph size and explicit ellipsis. */
    {
        const layout_text_t *label;char id[32];int i,at,x,y;
        sorting=0;layout_mode=layout_noactions=1;layout_capture=1;
        memset(&aw_state,0,sizeof(aw_state));
        memset(&fixture_item,0,sizeof(fixture_item));strcpy(fixture_item.model,"progs/inv/fixture.mdl");
        fixture_item.category=AW_INV_CLOTHING;fixture_item.slots=1U<<AW_SLOT_LRING;fixture_item.flags=7;
        strcpy(aw_story.name,"A deliberately long player name");
        for(i=0;i<6;i++){sprintf(id,"layout_item_%d",i);assert(AW_ItemAdd(&aw_state,id,1));}
        AW_InventoryOpen();layout_draw();
        /* Old footer ends at192 and fails layout_draw's inset assertion. */
        assert(!strcmp(layout_title,"Inventory"));
        label=layout_find("A very long");assert(label && strstr(label->value,"..."));
        assert(label->width==137); /* no smaller font or wider hidden field */
        assert(layout_find("Tab category")->y==176);
        assert(layout_find("Up/Down select")->y==184);
        assert(preview_calls); /* exact 116 x 150 preview bounds under the burden bar checked by its stub */
        layout_point(160,135);AW_WorldUIKey(K_MOUSE1,1);layout_draw();
        label=layout_find("Actions unavailable");assert(label && label->y>=160 && label->y+5<=173);
        layout_point(160,55);AW_WorldUIKey(K_MOUSE1,1);
        placement=0;before=aw_state;AW_WorldUIKey('d',1);layout_draw();
        assert(!memcmp(&before,&aw_state,sizeof(before)));
        label=layout_find("Cannot place");assert(label && label->y==160);
        label=layout_find("choose a clear spot");assert(label && label->y==168 && strstr(label->value,"...")); /* 91-byte synthetic status exceeds two45-column lines; bounded ellipsis is explicit. */
        /* DROP-REFUSED-CENSUS-ROOM-67: without the debug HUD the player reads the plain line, not the check's reason */
        debug_overlays=0;before=aw_state;AW_WorldUIKey('d',1);layout_draw();
        assert(!memcmp(&before,&aw_state,sizeof(before)));
        assert(layout_find("This item cannot be dropped here.") && !layout_find("Cannot place") && !layout_find("kept"));
        debug_overlays=1;
        AW_WorldUIKey('i',1);layout_noactions=0;placement=1;
        AW_InventoryOpen();layout_point(300,149);AW_WorldUIKey(K_MOUSE3,1);layout_draw();
        label=layout_find("Equip");assert(label);x=label->x;y=label->y;
        assert(y>=124 && y+5<172);   /* INVENTORY-ITEM-INFO-67: three rows now (Equip, Drop one, Info) */
        label=layout_find("Info");assert(label && label->y+5<172);
        layout_point(x+2,y+2);AW_WorldUIKey(K_MOUSE1,1);
        assert(AW_InventoryEquipped(&aw_state,"layout_item_5"));
        for(i=0;i<5;i++){sprintf(id,"layout_item_%d",i);assert(!AW_InventoryEquipped(&aw_state,id));}
        layout_point(300,149);AW_WorldUIKey(K_MOUSE3,1);layout_draw();
        assert(layout_find("Unequip"));label=layout_find("Drop one");assert(label && label->y+5<172);
        x=label->x;y=label->y;layout_point(x+2,y+2);AW_WorldUIKey(K_MOUSE1,1);
        assert(!AW_StateGet(&aw_state,AW_ITEM,"layout_item_5"));
        for(i=0;i<5;i++){sprintf(id,"layout_item_%d",i);assert(AW_StateGet(&aw_state,AW_ITEM,id)==1);}
        layout_draw();layout_point(200,188);AW_WorldUIKey(K_MOUSE1,1);
        assert(AW_InventoryActive()); /* navigation row is not a close hitbox */
        layout_draw();label=layout_find("I/Esc close");assert(label);
        x=label->x;y=label->y;layout_point(x+2,y+2);AW_WorldUIKey(K_MOUSE1,1);
        assert(!AW_InventoryActive() && key_dest==key_game);
        layout_capture=layout_mode=0;
        printf("inventory bounds: rows54..149 details153..157 status160..172 controls176..188 context<=171 burden21..29 preview32..181 armour186..191; drawn action clicks equip/drop/close pass\n");
        (void)at;
    }
    /* More than one page: arrows/rail/drag route through the shared helper;
     * selection remains visible, and actual equip affects that selected ID. */
    {
        char id[32];int i,c;
        scroll_mode=layout_capture=1;layout_mode=0;
        memset(&aw_state,0,sizeof(aw_state));
        for(i=0;i<12;i++){sprintf(id,"scroll_%02d",i);assert(AW_ItemAdd(&aw_state,id,1));}
        AW_InventoryOpen();before=aw_state;layout_draw();
        assert(scroll_calls==1 && scroll_top==0 && scroll_total==12);
        assert(strstr(drawn,"Scroll00") && strstr(drawn,"Scroll05") && !strstr(drawn,"Scroll06"));
        assert(layout_find("Scroll00")->width==127); /* quantity also leaves rail clear */
        for(i=0;i<layout_count;i++)if(layout_text[i].y>=54 && layout_text[i].y<150)
            assert(layout_text[i].x+layout_text[i].width<=302);
        scroll_target=1;layout_point(306,145);AW_WorldUIKey(K_MOUSE1,1);layout_draw();
        assert(scroll_top==1 && strstr(drawn,"Scroll01") && strstr(drawn,"Scroll06"));
        scroll_target=6;AW_WorldUIMouse(0,-30);layout_draw();assert(scroll_top==1); /* arrow did not start drag */
        AW_WorldUIKey(K_MOUSE1,1);layout_draw();assert(scroll_top==6 && strstr(drawn,"Scroll11"));
        scroll_target=2;AW_WorldUIMouse(-200,-20);layout_draw();assert(scroll_top==2); /* captured outside rail */
        AW_WorldUIKey(K_MOUSE1,0);scroll_target=4;AW_WorldUIMouse(20,2);layout_draw();assert(scroll_top==2);
        assert(!memcmp(&before,&aw_state,sizeof(before))); /* scrolling is not a transaction */
        AW_WorldUIKey(K_HOME,1);layout_draw();assert(scroll_top==0);
        scroll_target=6;layout_point(306,110);AW_WorldUIKey(K_MOUSE1,1);layout_draw();assert(scroll_top==6);
        AW_WorldUICancelDrag();scroll_target=1;AW_WorldUIMouse(0,-20);layout_draw();assert(scroll_top==6);
        AW_WorldUIKey('e',1);assert(AW_InventoryEquipped(&aw_state,"scroll_06"));
        for(i=0;i<12;i++){sprintf(id,"scroll_%02d",i);if(i!=6)assert(!AW_InventoryEquipped(&aw_state,id));}
        AW_WorldUIKey(K_END,1);AW_WorldUIKey('e',1);assert(AW_InventoryEquipped(&aw_state,"scroll_11"));
        AW_WorldUIKey(K_HOME,1);AW_WorldUIKey(K_PGDN,1);AW_WorldUIKey('e',1);assert(AW_InventoryEquipped(&aw_state,"scroll_06"));
        AW_WorldUIKey(K_HOME,1);
        scroll_target=3;layout_point(306,110);AW_WorldUIKey(K_MOUSE1,1);
        AW_WorldUIKey(K_TAB,1);c=scroll_calls;layout_draw();assert(strstr(drawn,"No carried items") && scroll_calls==c);
        scroll_target=0;AW_WorldUIMouse(0,10);AW_WorldUIKey(K_MOUSE1,1);layout_draw();assert(scroll_calls==c);
        /* Tab reset and pointer movement after a cancelled drag cannot scroll
         * the repopulated category. */
        for(i=0;i<7;i++)AW_WorldUIKey(K_TAB,1);
        scroll_target=6;AW_WorldUIMouse(0,2);layout_draw();assert(scroll_top==0);
        layout_point(306,110);AW_WorldUIKey(K_MOUSE3,1);layout_draw();assert(!strstr(drawn,"Drop one"));
        AW_WorldUIKey(K_MOUSE1,1);AW_WorldUIKey(K_HOME,1);AW_WorldUIMouse(0,2);layout_draw();assert(scroll_top==0);
        AW_WorldUIKey('i',1);AW_InventoryOpen();AW_WorldUIMouse(0,5);layout_draw();assert(scroll_top==0);
        AW_WorldUIKey('i',1);memset(&aw_state,0,sizeof(aw_state));
        for(i=0;i<6;i++){sprintf(id,"scroll_%02d",i);assert(AW_ItemAdd(&aw_state,id,1));}
        AW_InventoryOpen();before=aw_state;c=scroll_calls;layout_draw();
        assert(scroll_calls==c && layout_find("Scroll00")->width==137);
        layout_point(306,110);AW_WorldUIKey(K_MOUSE1,1);AW_WorldUIMouse(0,20);layout_draw();
        assert(scroll_calls==c && !memcmp(&before,&aw_state,sizeof(before)));
        AW_WorldUIKey('i',1);scroll_mode=layout_capture=0;
        puts("inventory scrollbar: visible rows, bounded layout, mouse release/focus/category/keyboard/close cancellation and real equip identity pass");
    }
    /* INVENTORY-DOUBLECLICK-62: a double-click (two clicks on one row within 0.5 s) equips or takes off at once with the
     * notice box (3 s); a potion asks first: OK and Cancel, Esc and I cancel and keep the window, the count by keys,
     * digits, Backspace, the slider (click and drag) and the buttons; one use per count; the last one without a slider */
    {
        int left;
        memset(&aw_state,0,sizeof(aw_state));
        memset(&fixture_item,0,sizeof(fixture_item));strcpy(fixture_item.id,"fixture_ring");strcpy(fixture_item.name,"Fixture Ring");
        strcpy(fixture_item.model,"progs/inv/fixture.mdl");fixture_item.category=AW_INV_CLOTHING;
        fixture_item.slots=(1U<<AW_SLOT_LRING)|(1U<<AW_SLOT_RRING);fixture_item.flags=7;
        assert(AW_ItemAdd(&aw_state,fixture_item.id,1));
        AW_InventoryOpen();draw();layout_point(160,60);
        test_clock=200;click();assert(!AW_InventoryEquipped(&aw_state,fixture_item.id));          /* one click selects */
        test_clock=200.6;click();assert(!AW_InventoryEquipped(&aw_state,fixture_item.id));        /* too slow: a first click */
        test_clock=200.9;click();assert(AW_InventoryEquipped(&aw_state,fixture_item.id)==1);
        draw();assert(strstr(drawn,"Equipped Fixture Ring"));
        test_clock=203.85;draw();assert(strstr(drawn,"Equipped Fixture Ring"));
        test_clock=203.95;draw();assert(!strstr(drawn,"Equipped Fixture Ring"));                  /* gone after 3 s */
        test_clock=205;click();test_clock=205.3;click();assert(!AW_InventoryEquipped(&aw_state,fixture_item.id));
        draw();assert(strstr(drawn,"Unequipped Fixture Ring"));
        test_clock=205.5;click();assert(!AW_InventoryEquipped(&aw_state,fixture_item.id));       /* a third click starts again */
        AW_WorldUIKey('i',1);assert(!AW_InventoryActive());
        memset(&aw_state,0,sizeof(aw_state));
        memset(&fixture_item,0,sizeof(fixture_item));strcpy(fixture_item.id,"fixture_potion");strcpy(fixture_item.name,"Fixture Potion");
        fixture_item.category=AW_INV_POTION;fixture_item.flags=AW_INV_ALCHEMY|AW_INV_DROP;fixture_item.alchemy_kind=AW_ALCHEMY_POTION;
        aw_worldui_use=test_use;uses=0;
        assert(AW_ItemAdd(&aw_state,fixture_item.id,12));
        AW_InventoryOpen();layout_point(160,60);
        test_clock=300;click();test_clock=300.1;click();assert(!uses && AW_StateGet(&aw_state,AW_ITEM,fixture_item.id)==12);
        draw();assert(strstr(drawn,"Drink Fixture Potion?") && strstr(drawn,"How many? 1 to 12") && strstr(drawn,"1_") &&
                      strstr(drawn,"of 12") && strstr(drawn,"OK") && strstr(drawn,"Cancel"));
        AW_WorldUIKey(K_ESCAPE,1);assert(AW_InventoryActive() && !uses);draw();assert(!strstr(drawn,"Drink Fixture"));
        test_clock=301;click();test_clock=301.1;click();
        AW_WorldUIKey(K_RIGHTARROW,1);AW_WorldUIKey(K_RIGHTARROW,1);draw();assert(strstr(drawn,"3_"));
        AW_WorldUIKey(K_END,1);draw();assert(strstr(drawn,"12_"));AW_WorldUIKey(K_PGDN,1);draw();assert(strstr(drawn,"2_"));
        AW_WorldUIKey('i',1);assert(AW_InventoryActive() && !uses);                                  /* I cancels too */
        test_clock=302;click();test_clock=302.1;click();
        AW_WorldUIKey('7',1);draw();assert(strstr(drawn,"7_"));                                       /* a digit replaces */
        AW_WorldUIKey('0',1);draw();assert(strstr(drawn,"12_"));                                      /* 70: the stack */
        AW_WorldUIKey(K_BACKSPACE,1);AW_WorldUIKey(K_BACKSPACE,1);AW_WorldUIKey('4',1);
        AW_WorldUIKey(K_ENTER,1);assert(uses==4 && AW_StateGet(&aw_state,AW_ITEM,fixture_item.id)==8 && AW_InventoryActive());
        draw();assert(strstr(drawn,"Fixture Potion: 4 drunk."));
        test_clock=303;click();test_clock=303.1;click();
        layout_point(140+10+148-1,62+40);AW_WorldUIKey(K_MOUSE1,1);draw();assert(strstr(drawn,"8_"));   /* the rail's end */
        AW_WorldUIMouse(-200,0);draw();assert(strstr(drawn,"1_"));                                    /* dragged to 1 */
        AW_WorldUIMouse(79,0);draw();left=AW_InventorySliderCount(97+79,150,148,8);assert(left>1 && left<8);
        AW_WorldUIKey(K_MOUSE1,0);AW_WorldUIMouse(40,0);draw();
        {char want[8];sprintf(want,"%d_",left);assert(strstr(drawn,want));}                          /* let go: it stays */
        layout_point(160+5,62+82-20+5);AW_WorldUIKey(K_MOUSE1,1);AW_WorldUIKey(K_MOUSE1,0);         /* OK */
        assert(uses==4+left && AW_StateGet(&aw_state,AW_ITEM,fixture_item.id)==8-left);
        assert(AW_StateSet(&aw_state,AW_ITEM,fixture_item.id,1));draw();
        layout_point(160,60);test_clock=304;click();test_clock=304.1;click();
        draw();assert(strstr(drawn,"Drink Fixture Potion?") && strstr(drawn,"The last one.") && !strstr(drawn,"How many"));
        layout_point(140+168-20-52+5,62+82-20+5);AW_WorldUIKey(K_MOUSE1,1);AW_WorldUIKey(K_MOUSE1,0);  /* Cancel */
        assert(uses==4+left && AW_StateGet(&aw_state,AW_ITEM,fixture_item.id)==1);
        layout_point(160,60);test_clock=305;click();test_clock=305.1;click();AW_WorldUIKey(K_ENTER,1);
        assert(uses==5+left && !AW_StateGet(&aw_state,AW_ITEM,fixture_item.id));
        AW_WorldUIKey('i',1);assert(!AW_InventoryActive());aw_worldui_use=NULL;
        /* the rules: the window, the slider ends and the middle, the number field */
        assert(AW_InventoryDoubleClick(3,10,3,10.5) && !AW_InventoryDoubleClick(3,10,3,10.51) && !AW_InventoryDoubleClick(3,10,4,10.1));
        assert(!AW_InventoryDoubleClick(-1,10,-1,10.1) && !AW_InventoryDoubleClick(3,10,3,9.9));
        assert(AW_InventorySliderCount(0,10,101,51)==1 && AW_InventorySliderCount(110,10,101,51)==51 && AW_InventorySliderCount(60,10,101,51)==26);
        assert(AW_InventorySliderX(26,10,101,51)==60 && AW_InventorySliderX(1,10,101,51)==10 && AW_InventorySliderX(99,10,101,51)==110);
        assert(AW_InventoryCountType(1,1,'5',9)==5 && AW_InventoryCountType(5,0,'2',99)==52 && AW_InventoryCountType(5,0,'2',30)==30);
        assert(AW_InventoryCountType(52,0,'\b',99)==5 && AW_InventoryCountType(7,1,'\b',99)==0 && AW_InventoryCountType(7,0,'x',99)==7);
        puts("inventory double-click: equip/unequip with the notice, the potion's box (OK, Cancel, Esc, I, keys, digits, slider, buttons, the last one) pass");
    }
    /* INVENTORY-EQUIP-HINTS-67 (EQUIP-ACTION-REGRESSION-62 seen again on v0.0.67-dev2, INVENTORY-EQUIPPED-LABEL-67) and
     * SCROLL-CAST-64: every kind's action in the key line ("E/Enter equip", "E/Enter unequip", "E/Enter use", "E/Enter
     * read", none for a plain misc item) with the drop key; a worn row says "Equipped" in the highlight colour; an
     * action's result line belongs to its row for a few seconds and never hides another row's hint (after one Equip
     * every other item lost its hint on dev2); Use on a Cast Once scroll closes the window and casts it; Read stays in
     * the right button's menu beside it */
    {
        const layout_text_t *t;int i,gold=AW_UIColor(223,199,144),high=AW_UIColor(150,220,120);
        static const char *const want[7]={"E/Enter equip","E/Enter equip","E/Enter use","E/Enter use","E/Enter read",NULL,"E/Enter use"};
        kinds_fill();kinds_mode=1;layout_capture=1;layout_mode=sorting=scroll_mode=0;test_clock=400;
        memset(&aw_state,0,sizeof(aw_state));
        for(i=0;i<7;i++)assert(AW_ItemAdd(&aw_state,kinds[i].id,1));
        aw_worldui_use=test_use;aw_worldui_read=test_read;aw_worldui_cast=test_cast;uses=cast_calls=read_calls=0;
        /* the pure rule over the same rows */
        assert(AW_InventoryItemAction(&kinds[0],0)==AW_INV_ACT_EQUIP && AW_InventoryItemAction(&kinds[0],1)==AW_INV_ACT_UNEQUIP);
        assert(AW_InventoryItemAction(&kinds[2],0)==AW_INV_ACT_USE && AW_InventoryItemAction(&kinds[3],0)==AW_INV_ACT_CAST);
        assert(AW_InventoryItemAction(&kinds[4],0)==AW_INV_ACT_READ && AW_InventoryItemAction(&kinds[5],0)==AW_INV_ACT_NONE);
        assert(AW_InventoryItemAction(&kinds[6],0)==AW_INV_ACT_USE && AW_InventoryItemAction(NULL,0)==AW_INV_ACT_NONE);
        assert(!strcmp(AW_InventoryActionWord(AW_INV_ACT_EQUIP),"Equip") && !strcmp(AW_InventoryActionWord(AW_INV_ACT_UNEQUIP),"Unequip"));
        assert(!strcmp(AW_InventoryActionWord(AW_INV_ACT_CAST),"Use") && !AW_InventoryActionWord(AW_INV_ACT_NONE));
        AW_InventoryOpen();
        for(i=0;i<7;i++){   /* each row in turn: its own action, the drop key, no other row's action */
            if(i)AW_WorldUIKey(K_DOWNARROW,1);
            layout_draw();t=layout_find("Up/Down select");assert(t && t->y==184 && t->color==gold);
            if(want[i])assert(strstr(t->value,want[i]));else assert(!strstr(t->value,"E/Enter"));
            assert(strstr(t->value,"D drop"));
        }
        AW_WorldUIKey(K_HOME,1);
        AW_WorldUIKey('e',1);assert(AW_InventoryEquipped(&aw_state,"a_ring")==1);
        layout_draw();t=layout_find("Up/Down select");assert(t && strstr(t->value,"E/Enter unequip"));
        t=layout_find("Equipped");assert(t && t->color==high && t->x+t->width<=312-24 && t->y==57);   /* row 0 */
        assert(layout_find("A Ring")->x+layout_find("A Ring")->width<=t->x);         /* the name gives it room */
        assert(layout_find("Equipment updated."));
        AW_WorldUIKey(K_DOWNARROW,1);layout_draw();                                   /* the next ring: its own hint */
        t=layout_find("Up/Down select");assert(t && strstr(t->value,"E/Enter equip") && !strstr(t->value,"unequip"));
        assert(!layout_find("Equipment updated.") && layout_find("RMB actions"));
        AW_WorldUIKey(K_UPARROW,1);layout_draw();assert(layout_find("Equipment updated."));   /* its row, in time */
        test_clock+=4.1;layout_draw();assert(!layout_find("Equipment updated.") && layout_find("RMB actions"));
        /* the scroll: the right button offers Use (its cast) and Read; E casts it and the window closes */
        for(i=0;i<3;i++)AW_WorldUIKey(K_DOWNARROW,1);
        layout_point(160,54+3*16+4);AW_WorldUIKey(K_MOUSE3,1);layout_draw();
        assert(layout_find("Use") && layout_find("Read") && layout_find("Drop one"));
        AW_WorldUIKey('e',1);
        assert(cast_calls==1 && !strcmp(cast_id,"d_scroll") && !read_calls && !AW_InventoryActive() && key_dest==key_game);
        /* without casting in the build (no hook), a scroll is not cast and E does nothing; Read stays */
        aw_worldui_cast=NULL;AW_InventoryOpen();for(i=0;i<3;i++)AW_WorldUIKey(K_DOWNARROW,1);
        layout_draw();t=layout_find("Up/Down select");assert(t && !strstr(t->value,"E/Enter"));
        AW_WorldUIKey('e',1);assert(AW_InventoryActive() && cast_calls==1 && !read_calls);
        aw_worldui_cast=test_cast;
        AW_WorldUIKey(K_DOWNARROW,1);AW_WorldUIKey('e',1);
        assert(read_calls==1 && !strcmp(read_id,"e_book") && !AW_InventoryActive());
        AW_InventoryOpen();for(i=0;i<6;i++)AW_WorldUIKey(K_DOWNARROW,1);
        AW_WorldUIKey('e',1);assert(uses==1 && AW_InventoryActive());                 /* the root is used */
        AW_WorldUIKey('i',1);assert(!AW_InventoryActive());
        aw_worldui_use=NULL;aw_worldui_read=NULL;aw_worldui_cast=NULL;kinds_mode=layout_capture=0;
        puts("inventory hints: equip, unequip with Equipped, use, a scroll's cast, read, none; the result line keeps to its row and time pass");
    }
    /* INVENTORY-ITEM-INFO-67: P (the information key, named in the key line) opens the selected item's box over the
     * window; Esc, I and OK close it and keep the window; the use key in it does the item's action (Equip) and closes
     * it; the right button's Info opens it; a book's box shows its text (the reader's hook, read once) and scrolls
     * without moving the list */
    {
        aw_iteminfo_t fake;aw_layout_t l;int i,t[4],visible;
        kinds_fill();kinds_mode=1;layout_capture=1;layout_mode=sorting=scroll_mode=0;test_clock=500;
        memset(&aw_state,0,sizeof(aw_state));
        for(i=0;i<7;i++)assert(AW_ItemAdd(&aw_state,kinds[i].id,1));
        aw_worldui_read=test_read;aw_worldui_book_text=test_book_text;book_calls=read_calls=0;
        AW_InventoryOpen();layout_draw();assert(layout_find("P info") && layout_find("P info")->y==176);
        AW_WorldUIKey('p',1);layout_count=0;draw();assert(layout_find("Value: 0") && AW_InventoryActive());
        AW_WorldUIKey(K_ESCAPE,1);assert(AW_InventoryActive());layout_count=0;draw();assert(!layout_find("Value: 0"));
        AW_WorldUIKey('p',1);AW_WorldUIKey('i',1);assert(AW_InventoryActive());   /* I in the box: back to the window */
        layout_count=0;draw();assert(!layout_find("Value: 0"));
        AW_WorldUIKey('p',1);AW_WorldUIKey('e',1);                                /* the box's action: Equip */
        assert(AW_InventoryEquipped(&aw_state,"a_ring")==1 && AW_InventoryActive());
        layout_count=0;draw();assert(!layout_find("Value: 0"));
        /* OK, clicked where the helper lays it out for an item with an action (Unequip now) */
        memset(&fake,0,sizeof(fake));strcpy(fake.action,"Unequip");fake.chars=1000;AW_ItemInfoLayout(&fake,&l,t,&visible);
        AW_WorldUIKey('p',1);layout_point(l.button[0][0]+4,l.button[0][1]+4);AW_WorldUIKey(K_MOUSE1,1);AW_WorldUIKey(K_MOUSE1,0);
        assert(AW_InventoryActive() && AW_InventoryEquipped(&aw_state,"a_ring")==1);
        layout_count=0;draw();assert(!layout_find("Value: 0"));
        /* the book: its text in the box, read once; End scrolls the box, not the list */
        for(i=0;i<4;i++)AW_WorldUIKey(K_DOWNARROW,1);
        AW_WorldUIKey('p',1);assert(book_calls==1);layout_count=0;draw();assert(layout_find("First words of the book."));
        AW_WorldUIKey(K_END,1);layout_count=0;draw();assert(!layout_find("First words of the book."));
        AW_WorldUIKey(K_ESCAPE,1);AW_WorldUIKey('e',1);assert(read_calls==1 && !strcmp(read_id,"e_book"));   /* E: Read */
        /* the right button's menu ends in Info */
        AW_InventoryOpen();layout_point(160,54+4);AW_WorldUIKey(K_MOUSE3,1);layout_draw();
        {const layout_text_t *info=layout_find("Info");assert(info);
         layout_point(info->x+2,info->y+2);AW_WorldUIKey(K_MOUSE1,1);AW_WorldUIKey(K_MOUSE1,0);}
        layout_count=0;draw();assert(layout_find("Value: 0"));
        AW_WorldUIKey(K_ESCAPE,1);AW_WorldUIKey('i',1);assert(!AW_InventoryActive());
        aw_worldui_read=NULL;aw_worldui_book_text=NULL;kinds_mode=layout_capture=0;
        puts("inventory information box: P, Esc, I, OK, the use key's action, the right button's Info, a book's text and its scroll pass");
    }
    return 0;
}
