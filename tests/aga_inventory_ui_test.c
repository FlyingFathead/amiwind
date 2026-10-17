/* SPDX-License-Identifier: GPL-3.0-only
 * Actual world UI events + actual inventory transactions; synthetic item data
 * and a recorded placement decision isolate host interaction from native I/O. */
#define COM_FOpenFile __wrap_COM_FOpenFile
#define AW_SmallStringColor legacy_inventory_text
#define AW_UITextBox legacy_inventory_textbox
#define AW_UIScrollbar legacy_inventory_scrollbar
#define AW_UIScrollHit legacy_inventory_scrollhit
#define main map_journal_regressions
#include "aga_worldui_test.c"
#undef main
#undef AW_UIScrollbar
#undef AW_UIScrollHit
#undef AW_SmallStringColor
#undef AW_UITextBox
#undef COM_FOpenFile
#include "aw_inventory.h"
#include "aw_harvest.h"
static aw_harvest_t h;
#include "aga_harvest_fixture.h"
typedef struct {int x,y,width;char value[160];} layout_text_t;
static layout_text_t layout_text[64];
static int layout_capture,layout_count,layout_mode,layout_noactions;
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
        layout_text_t *entry;assert(layout_count<64);entry=&layout_text[layout_count++];
        entry->x=x;entry->y=y;entry->width=width;
        strncpy(entry->value,value,sizeof(entry->value)-1);entry->value[sizeof(entry->value)-1]=0;
    }
}
void AW_UITextBox(int x,int y,int w,int h,const char *value,int color){
    legacy_inventory_textbox(x,y,w,h,value,color);
    if(layout_capture && x==6 && y==4){
        strncpy(layout_title,value,sizeof(layout_title)-1);layout_title[sizeof(layout_title)-1]=0;
    }
}
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
void AW_CombatEquipmentStore(void){store_calls++;}
void AW_CombatEquipmentChanged(void){changed_calls++;}
int AW_ViewInventoryBody(model_t **model,int *frame){static model_t body;*model=&body;*frame=7;return 1;}
int AW_InventoryPreviewDraw(model_t *model,int frame,int x,int y,int width,int height,float angle){
    (void)model;(void)angle;assert(frame==7 && x<128 && y==22 && width==116 && height==168);assert(angle>3.14f && angle<3.15f);preview_calls++;return 1;
}
int main(void){
    static client_t client;static edict_t actor;aw_state_t before;int calls;
    assert(!map_journal_regressions());
    key_dest=key_game;cls.state=ca_connected;sv.active=1;svs.maxclients=1;svs.clients=&client;client.edict=&actor;
    actor.v.health=100;strcpy(sv.name,"seyda");memset(&aw_state,0,sizeof(aw_state));
    memset(&fixture_item,0,sizeof(fixture_item));strcpy(fixture_item.id,"fixture_ring");strcpy(fixture_item.name,"Fixture Ring");
    strcpy(fixture_item.model,"progs/inv/fixture.mdl");fixture_item.category=AW_INV_CLOTHING;
    fixture_item.slots=(1U<<AW_SLOT_LRING)|(1U<<AW_SLOT_RRING);fixture_item.flags=7;
    assert(AW_ItemAdd(&aw_state,fixture_item.id,2));
    AW_InventoryOpen();assert(AW_InventoryActive() && key_dest==key_menu);draw();assert(preview_calls==1);
    assert(strstr(drawn,"Fixture Ring") && strstr(drawn,"Sort: Name"));
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
    AW_WorldUIKey('e',1);assert(!AW_InventoryEquipped(&aw_state,fixture_item.id));
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
        assert(preview_calls); /* exact168px preview bounds checked by its stub */
        layout_point(160,135);AW_WorldUIKey(K_MOUSE1,1);layout_draw();
        label=layout_find("Actions unavailable");assert(label && label->y>=160 && label->y+5<=173);
        layout_point(160,55);AW_WorldUIKey(K_MOUSE1,1);
        placement=0;before=aw_state;AW_WorldUIKey('d',1);layout_draw();
        assert(!memcmp(&before,&aw_state,sizeof(before)));
        label=layout_find("Cannot place");assert(label && label->y==160);
        label=layout_find("choose a clear spot");assert(label && label->y==168 && strstr(label->value,"...")); /* 91-byte synthetic status exceeds two45-column lines; bounded ellipsis is explicit. */
        AW_WorldUIKey('i',1);layout_noactions=0;placement=1;
        AW_InventoryOpen();layout_point(300,149);AW_WorldUIKey(K_MOUSE3,1);layout_draw();
        label=layout_find("Equip");assert(label);x=label->x;y=label->y;
        assert(y>=140 && y+5<172);
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
        printf("inventory bounds: rows54..149 details153..157 status160..172 controls176..188 context<=171 preview22..189; drawn action clicks equip/drop/close pass\n");
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
    return 0;
}
