/* SPDX-License-Identifier: GPL-2.0-or-later
 * CELL-CHANGES-59: the player's drops on the world change list (aw_ledger.h: key bit 30 + the inventory serial, the
 * fields DROPPED and CONDITION, the item id, count, position and yaw). The rules of AW_InventoryDrop and
 * AW_InventoryPickup (aw_inventory.c: the old fixed dropped[32] keyed by a map's name, kept for aw_placed ledger off),
 * on the list: the inventory and the list change together or not at all; every drop of the game is kept, map-wide,
 * with no 32-drop ceiling; a drop picked up again leaves no row (OpenMW 0.51 writes no reference that came from no
 * content file and has nothing left). Pure C: the native tests link it with aw_ledger.c, aw_state.c and aw_inventory.c
 * (AW_INVENTORY_RULES_ONLY).
 */
#include <string.h>
#include "aw_state.h"
#include "aw_inventory.h"
#include "aw_ledger.h"
#include "aw_maps.h"
#define drop_item_index AW_ItemIndex
static int drop_id_ok(const char *id){
    int i;
    if(!id || !id[0])return 0;
    for(i=0;i<63 && id[i];i++)if((unsigned char)id[i]<32 || (unsigned char)id[i]>126)return 0;
    return id[i]==0;
}
uint32_t AW_LedgerDrop(aw_state_t *s,aw_ledger_t *l,const aw_inventory_item_t *item,int32_t count,
                       int at,int32_t where,const float position[3],float yaw){
    aw_ledger_row_t *r;aw_ledger_extra_t *x;uint32_t key;int index,j;int32_t old;
    if(!s || !l || !item || !position || !drop_id_ok(item->id) || !(item->flags&AW_INV_DROP) || !item->model[0] ||
       count<1 || at<AW_AT_CELL || at>AW_AT_SCENE)return 0;
    old=AW_StateGet(s,AW_ITEM,item->id);
    if(count>old || s->inventory.next_serial>=AW_LEDGER_ID)return 0;
    /* placed items carry condition but no charge yet: never refill a spent item by dropping it */
    index=drop_item_index(s,item->id);
    if(count==old && AW_ITEM_HAS(s,index,AW_ITEM_CHARGE))return 0;
    for(j=0;j<3;j++)if(!(position[j]>=-1000000 && position[j]<=1000000))return 0;
    if(!(yaw>=-360 && yaw<=360))return 0;
    key=AW_LEDGER_PLAYER|(s->inventory.next_serial+1);
    if(AW_LedgerFind(l,key)>=0 || !(r=AW_LedgerPut(l,key)))return 0;
    if(!(x=AW_LedgerExtra(l,r))){AW_LedgerTidy(l,key);return 0;}
    r->fields=AW_LEDGER_DROPPED;AW_LedgerSetPlace(l,r,at,where);
    memcpy(x->position,position,sizeof(x->position));x->yaw=yaw;x->count=count;
    memset(x->item,0,sizeof(x->item));strcpy(x->item,item->id);
    if(AW_ITEM_HAS(s,index,AW_ITEM_CONDITION)){
        r->fields|=AW_LEDGER_CONDITION;x->condition=AW_ITEM_ROW(s,index)->condition;
    }
    /* AW_ItemAdd is the only fallible change of the inventory: the row goes again when it says no */
    if(!AW_ItemAdd(s,item->id,-count)){r->fields=0;AW_LedgerTidy(l,key);return 0;}
    if(AW_InventoryEquipped(s,item->id)>old-count)AW_InventoryUnequip(s,item->id);
    if(old==count)AW_ItemUnmark(s,index,AW_ITEM_CONDITION);
    s->inventory.initialized=1;s->inventory.next_serial++;
    return key;
}
int AW_LedgerPickup(aw_state_t *s,aw_ledger_t *l,uint32_t key){
    int i,index;aw_ledger_row_t *r;aw_ledger_extra_t *x;int32_t old;float current,incoming;
    if(!s || !l || (i=AW_LedgerFind(l,key))<0)return 0;
    r=&l->row[i];x=r->extra;
    if(!(r->fields&AW_LEDGER_DROPPED) || !x || x->count<1 || !drop_id_ok(x->item))return 0;
    index=drop_item_index(s,x->item);old=AW_StateGet(s,AW_ITEM,x->item);
    current=AW_ITEM_HAS(s,index,AW_ITEM_CONDITION)?AW_ITEM_ROW(s,index)->condition:1;
    incoming=(r->fields&AW_LEDGER_CONDITION)?x->condition:1;
    if(!(incoming>=0 && incoming<=1) || (old>0 && current!=incoming))return 0;
    if(!AW_ItemAdd(s,x->item,x->count))return 0;
    index=drop_item_index(s,x->item);
    if(r->fields&AW_LEDGER_CONDITION)AW_ItemMark(s,index,AW_ITEM_CONDITION,incoming);
    s->inventory.initialized=1;
    r->fields=0;AW_LedgerTidy(l,key);
    return 1;
}
int AW_LedgerAdoptDrops(aw_state_t *s,aw_ledger_t *l){
    int i,moved=0,scene;aw_ledger_row_t *r;aw_ledger_extra_t *x;
    for(i=0;i<AW_INVENTORY_DROPS;i++){
        aw_dropped_item_t *d=&s->inventory.dropped[i];uint32_t key;
        if(d->count<1 || !d->serial || d->serial>AW_LEDGER_ID || !drop_id_ok(d->id) || (scene=AW_MapId(d->scene))<0)continue;
        key=AW_LEDGER_PLAYER|d->serial;
        if(AW_LedgerFind(l,key)>=0 || !(r=AW_LedgerPut(l,key)))continue;
        if(!(x=AW_LedgerExtra(l,r))){AW_LedgerTidy(l,key);continue;}
        r->fields=AW_LEDGER_DROPPED|(d->condition_known?AW_LEDGER_CONDITION:0);
        AW_LedgerSetPlace(l,r,AW_AT_SCENE,scene);
        memcpy(x->position,d->position,sizeof(x->position));x->yaw=d->yaw;x->count=d->count;x->condition=d->condition;
        memset(x->item,0,sizeof(x->item));strcpy(x->item,d->id);
        memset(d,0,sizeof(*d));moved++;
    }
    return moved;
}
