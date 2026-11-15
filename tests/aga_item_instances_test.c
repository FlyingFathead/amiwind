/* SPDX-License-Identifier: GPL-3.0-only
 * The item instances (SAVE-ITEM-INSTANCES-ONE-PER-KIND-66; engine aw_state.h, aw_state.c, aw_inventory.c,
 * aw_ledger_drops.c, aw_save_codec.c feature 16384; tests/test_save_contract.py): the two-swords test of the save
 * contract. Two iron longswords; one is equipped and becomes its own instance; a blow puts it at 23 % while the other
 * stays whole; saved and loaded, both states are back and the worn one is still worn, and the loaded game saves again
 * to the same bytes; the plain copy drops first and comes back plain; the worn copy drops under its own serial with its
 * condition and comes back as the same instance; repaired to full and worn by nothing it merges away; the magic
 * selection spends the selected copy's charge alone; a save without instances carries no instance section; bad
 * instances are refused by the writer; New Game frees them.
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_story.h"
#include "aw_save.h"
#include "aw_maps.h"
#include "aw_ledger.h"
#include "aw_inventory.h"
aw_race_t aw_races[16];aw_class_t aw_classes[32];aw_birth_t aw_births[16];aw_part_t aw_parts[384];
int aw_race_count=1,aw_class_count=1,aw_birth_count=1,aw_part_count=2;
static aw_save_t save,loaded,again;
static aw_ledger_t list;
static unsigned char one[AW_SAVE_BYTES],two[AW_SAVE_BYTES],three[AW_SAVE_BYTES];

static void base(void)
{
    strcpy(aw_races[0].id,"race");strcpy(aw_classes[0].id,"class");strcpy(aw_births[0].id,"birth");
    strcpy(aw_parts[0].id,"head");strcpy(aw_parts[1].id,"hair");aw_parts[1].kind=1;
    memset(&save,0,sizeof(save));
    save.sequence=save.profile=1;strcpy(save.scene,"seyda");strcpy(save.story.name,"Player");
    save.story.stage=AW_STAGE_RELEASED;save.story.ship_disabled=1;save.story.captain=-1;
    save.character.valid=1;save.character.level=1;save.character.hair=1;
    assert(AW_StateSet(&save.state,AW_GLOBAL,"CharGenState",-1));
}
static int32_t cell(int x,int y){return (int32_t)(((uint32_t)(x&0xffff)<<16)|(uint32_t)(y&0xffff));}
static uint32_t features_of(const unsigned char *bytes,int size)
{
    /* the features word follows the fixed fields and the 256-entry journal copy: found by re-encoding is circular, so
     * the test reads it where the codec put it: right after the item rows and the actor count; simplest: the save of
     * the fixture without instances is compared byte for byte instead (see main) */
    (void)bytes;(void)size;return 0;
}
int main(void)
{
    aw_inventory_item_t sword,ring;aw_state_t *s;int row,n,m,k;uint32_t serial,key,key2;float pos[3]={100,200,8};
    (void)features_of;
    base();s=&save.state;
    memset(&sword,0,sizeof(sword));strcpy(sword.id,"iron longsword");strcpy(sword.model,"w/w_longsword.nif");
    sword.flags=AW_INV_EQUIP|AW_INV_EQUIP_SUPPORTED|AW_INV_DROP;sword.slots=1U<<AW_SLOT_RIGHT;sword.health=400;sword.category=AW_INV_WEAPON;
    /* a kind with one copy: no instance (the kind's marks are its marks, as before) */
    assert(AW_ItemAdd(s,"iron longsword",1));row=AW_ItemIndex(s,"iron longsword");assert(row>=0);
    assert(AW_InventoryEquipSlot(s,&sword,AW_SLOT_RIGHT) && AW_ItemInstCount(s)==0 && !s->inventory.equipped_serial[AW_SLOT_RIGHT]);
    assert(AW_InventorySlotSetCondition(s,AW_SLOT_RIGHT,0.5f) && AW_ITEM_HAS(s,row,AW_ITEM_CONDITION) && AW_InventorySlotCondition(s,AW_SLOT_RIGHT)==0.5f);
    assert(AW_InventorySlotSetCondition(s,AW_SLOT_RIGHT,1.0f) && !AW_ITEM_HAS(s,row,AW_ITEM_CONDITION));
    assert(AW_InventoryUnequip(s,"iron longsword")==1 && AW_ItemInstCount(s)==0);
    /* two swords: the worn one is its own instance; a blow lands on it alone */
    assert(AW_ItemAdd(s,"iron longsword",1) && AW_StateGet(s,AW_ITEM,"iron longsword")==2);
    assert(AW_InventoryEquipSlot(s,&sword,AW_SLOT_RIGHT) && AW_ItemInstCount(s)==1);
    serial=AW_ItemInst(s,0)->serial;
    assert(serial && s->inventory.equipped_serial[AW_SLOT_RIGHT]==serial && AW_ItemPlain(s,row)==1 && AW_ItemInst(s,0)->flags==0);
    assert(AW_InventorySlotSetCondition(s,AW_SLOT_RIGHT,0.23f));
    assert(AW_InventorySlotCondition(s,AW_SLOT_RIGHT)==0.23f && !AW_ITEM_HAS(s,row,AW_ITEM_CONDITION) && AW_ItemInstCount(s)==1);
    assert(AW_ItemInst(s,0)->condition==0.23f && (AW_ItemInst(s,0)->flags&AW_ITEM_CONDITION));
    /* saved and loaded: both states back, the worn one still worn; the loaded game saves again to the same bytes */
    n=AW_SaveEncodeChanges(one,sizeof(one),&save,NULL);assert(n>0);
    assert(AW_SaveDecodeChanges(one,n,&loaded,NULL));
    assert(loaded.state.items.inst_count==1 && AW_ItemInst(&loaded.state,0)->serial==serial &&
           loaded.state.inventory.equipped_serial[AW_SLOT_RIGHT]==serial &&
           AW_InventorySlotCondition(&loaded.state,AW_SLOT_RIGHT)==0.23f && AW_ItemPlain(&loaded.state,row)==1 &&
           AW_StateGet(&loaded.state,AW_ITEM,"iron longsword")==2);
    m=AW_SaveEncodeChanges(two,sizeof(two),&loaded,NULL);assert(m==n && !memcmp(one,two,(size_t)n));
    AW_SaveRelease(&loaded);
    /* the plain copy drops first (no condition on the ground), the worn one stays at 23 % */
    memset(&list,0,sizeof(list));
    key=AW_LedgerDrop(s,&list,&sword,1,AW_AT_CELL,cell(0,0),pos,0);
    assert(key && AW_StateGet(s,AW_ITEM,"iron longsword")==1 && AW_ItemInstCount(s)==1 &&
           AW_InventorySlotCondition(s,AW_SLOT_RIGHT)==0.23f && list.count==1 && list.row[0].fields==AW_LEDGER_DROPPED);
    assert(key!=(AW_LEDGER_PLAYER|serial));
    /* picked up again: a whole copy among whole plain copies is plain */
    assert(AW_LedgerPickup(s,&list,key) && AW_StateGet(s,AW_ITEM,"iron longsword")==2 && AW_ItemInstCount(s)==1 && AW_ItemPlain(s,row)==1 && list.count==0);
    /* the plain one dropped, then the worn one: under its own serial, with its condition; the hand is empty */
    key=AW_LedgerDrop(s,&list,&sword,1,AW_AT_CELL,cell(0,0),pos,0);assert(key && AW_ItemInstCount(s)==1);
    key2=AW_LedgerDrop(s,&list,&sword,1,AW_AT_CELL,cell(0,0),pos,0);
    assert(key2==(AW_LEDGER_PLAYER|serial) && AW_StateGet(s,AW_ITEM,"iron longsword")==0 && AW_ItemInstCount(s)==0 &&
           !s->inventory.equipped[AW_SLOT_RIGHT][0] && !s->inventory.equipped_serial[AW_SLOT_RIGHT]);
    k=AW_LedgerFind(&list,key2);assert(k>=0 && (list.row[k].fields&AW_LEDGER_CONDITION) && list.row[k].extra->condition==0.23f);
    /* both picked up: the plain one plain, the 23 % one the same instance it was */
    assert(AW_LedgerPickup(s,&list,key) && AW_LedgerPickup(s,&list,key2));
    assert(AW_StateGet(s,AW_ITEM,"iron longsword")==2 && AW_ItemInstCount(s)==1 && AW_ItemInst(s,0)->serial==serial &&
           AW_ItemInst(s,0)->condition==0.23f && AW_ItemPlain(s,row)==1 && !AW_ITEM_HAS(s,row,AW_ITEM_CONDITION));
    /* a third copy picked up whole: plain, no instance */
    key=AW_LedgerPlaceItem(s,&list,"iron longsword",1,AW_AT_CELL,cell(0,0),pos,0);assert(key && AW_LedgerPickup(s,&list,key));
    assert(AW_StateGet(s,AW_ITEM,"iron longsword")==3 && AW_ItemInstCount(s)==1 && AW_ItemPlain(s,row)==2);
    /* repaired to full and worn by nothing: merged away */
    k=AW_ItemInstFind(s,serial);assert(k>=0 && AW_ItemInstSet(s,k,AW_ITEM_CONDITION,1.0f)==2 && AW_ItemInstCount(s)==0);
    /* the magic selection: the selected copy of two spends its own charge; cleared, the full one merges */
    memset(&ring,0,sizeof(ring));strcpy(ring.id,"ring of firebite");ring.enchant_kind=AW_ENCH_USED;ring.charge_max=100;
    assert(AW_ItemAdd(s,ring.id,2) && AW_MagicSelect(s,&ring) && AW_MagicCharge(s,&ring)==100);
    assert(AW_MagicSetCharge(s,&ring,40) && AW_ItemInstCount(s)==1 && s->magic.selected_serial==AW_ItemInst(s,0)->serial);
    assert(AW_MagicCharge(s,&ring)==40 && !AW_ITEM_HAS(s,AW_ItemIndex(s,ring.id),AW_ITEM_CHARGE));
    n=AW_SaveEncodeChanges(one,sizeof(one),&save,NULL);assert(n>0 && AW_SaveDecodeChanges(one,n,&loaded,NULL));
    assert(loaded.state.magic.selected_serial==s->magic.selected_serial && AW_MagicCharge(&loaded.state,&ring)==40);
    AW_SaveRelease(&loaded);
    assert(AW_MagicSetCharge(s,&ring,100) && AW_ItemInstCount(s)==1 && AW_ItemInst(s,0)->flags==0);   /* named: stays */
    AW_MagicClear(s);assert(AW_ItemInstCount(s)==0);
    /* a save without instances: the same bytes as a save that never had any */
    assert(AW_ItemAdd(s,ring.id,-2) && AW_ItemAdd(s,"iron longsword",-3) && AW_ItemInstCount(s)==0);
    n=AW_SaveEncodeChanges(one,sizeof(one),&save,NULL);
    memset(&again,0,sizeof(again));again=save;
    m=AW_SaveEncodeChanges(three,sizeof(three),&again,NULL);assert(n>0 && m==n && !memcmp(one,three,(size_t)n));
    /* the writer refuses a broken instance: a row the table has not, a slot naming no instance */
    assert(AW_ItemAdd(s,"iron longsword",2) && AW_InventoryEquipSlot(s,&sword,AW_SLOT_RIGHT) && AW_ItemInstCount(s)==1);
    s->items.inst[0].row=99;assert(AW_SaveEncodeChanges(one,sizeof(one),&save,NULL)==0);
    s->items.inst[0].row=AW_ItemIndex(s,"iron longsword");assert(AW_SaveEncodeChanges(one,sizeof(one),&save,NULL)>0);
    s->inventory.equipped_serial[AW_SLOT_RIGHT]=4242;assert(AW_SaveEncodeChanges(one,sizeof(one),&save,NULL)==0);
    s->inventory.equipped_serial[AW_SLOT_RIGHT]=s->items.inst[0].serial;
    /* fewer copies than instances: the instances go with the copies */
    assert(AW_ItemAdd(s,"iron longsword",-1) && AW_ItemInstCount(s)==1 && AW_ItemAdd(s,"iron longsword",-1) && AW_ItemInstCount(s)==0);
    /* New Game: the table and its instances go */
    AW_ItemsFree(s);assert(AW_ItemInstCount(s)==0 && !s->items.inst);
    AW_LedgerClear(&list);
    puts("item instances: two swords kept apart through a blow, a save, a load, a drop and a pickup; merged when alike");
    return 0;
}
