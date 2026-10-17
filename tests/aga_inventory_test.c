/* SPDX-License-Identifier: GPL-3.0-only
 * Real state/rule transactions: no original game data or fabricated inventory. */
#include <assert.h>
#include <string.h>
#include <math.h>
#include <stdio.h>
#include "aw_inventory.h"
static aw_state_t state,prior;
static aw_inventory_item_t ring,other,third;
int main(void){
    int drop,i;float pos[3]={1,2,3};
    memset(&ring,0,sizeof(ring));strcpy(ring.id,"ring_a");
    strcpy(ring.model,"progs/inventory/test.mdl");
    ring.flags=AW_INV_EQUIP|AW_INV_EQUIP_SUPPORTED|AW_INV_DROP;
    ring.slots=(1U<<AW_SLOT_LRING)|(1U<<AW_SLOT_RRING);
    other=third=ring;strcpy(other.id,"ring_b");strcpy(third.id,"ring_c");
    prior=state;assert(!AW_InventoryEquip(&state,&ring));assert(!memcmp(&state,&prior,sizeof(state)));
    assert(AW_ItemAdd(&state,ring.id,2));assert(AW_ItemAdd(&state,other.id,1));assert(AW_ItemAdd(&state,third.id,1));
    assert(AW_InventoryEquip(&state,&ring));assert(!strcmp(state.inventory.equipped[AW_SLOT_LRING],ring.id));
    assert(AW_InventoryEquip(&state,&other));assert(AW_InventoryEquip(&state,&third));
    assert(!strcmp(state.inventory.equipped[AW_SLOT_LRING],other.id));
    assert(!strcmp(state.inventory.equipped[AW_SLOT_RRING],third.id));
    prior=state;assert(!AW_InventoryEquipSlot(&state,&ring,99));assert(!memcmp(&state,&prior,sizeof(state)));
    ring.flags&=~AW_INV_EQUIP_SUPPORTED;assert(!AW_InventoryEquip(&state,&ring));ring.flags|=AW_INV_EQUIP_SUPPORTED;
    assert(AW_InventoryEquip(&state,&ring));assert(AW_InventoryEquipped(&state,ring.id)==1);
    prior=state;pos[2]=NAN;assert(AW_InventoryDrop(&state,&ring,1,"seyda",pos,0)<0);
    assert(!memcmp(&state,&prior,sizeof(state)));pos[2]=3;
    assert(AW_InventoryDrop(&state,&ring,3,"seyda",pos,0)<0);
    drop=AW_InventoryDrop(&state,&ring,1,"seyda",pos,0);assert(drop>=0);
    assert(AW_StateGet(&state,AW_ITEM,ring.id)==1 && state.inventory.dropped[drop].count==1);
    assert(AW_InventoryEquipped(&state,ring.id)==1);
    assert(AW_InventoryPickup(&state,drop));assert(AW_StateGet(&state,AW_ITEM,ring.id)==2);
    assert(!AW_InventoryPickup(&state,drop));
    drop=AW_InventoryDrop(&state,&ring,2,"seyda",pos,0);assert(drop>=0);
    assert(!AW_InventoryEquipped(&state,ring.id));assert(AW_StateGet(&state,AW_ITEM,ring.id)==0);
    for(i=0;i<AW_INVENTORY_DROPS;i++)if(!state.inventory.dropped[i].count)state.inventory.dropped[i]=state.inventory.dropped[drop];
    prior=state;assert(AW_InventoryDrop(&state,&other,1,"seyda",pos,0)<0);assert(!memcmp(&state,&prior,sizeof(state)));
    memset(&state,0,sizeof(state));strcpy(state.inventory.dropped[0].id,"unknown_item");state.inventory.dropped[0].count=1;state.inventory.dropped[0].serial=1;
    for(i=0;i<AW_STATE_VALUES;i++){char name[32];sprintf(name,"item%d",i);assert(AW_ItemAdd(&state,name,1));}
    prior=state;assert(!AW_InventoryPickup(&state,0));assert(!memcmp(&state,&prior,sizeof(state)));
    /* Magic items (HUD-STATS-29): select only an owned Cast Once / When Used item;
     * charge full unless recorded; recharge capped; a spent stack is never dropped
     * (drops do not carry charge yet); losing the item clears the selection. */
    {
        aw_inventory_item_t used=ring,strikes=ring,plain=ring;
        memset(&state,0,sizeof(state));
        strcpy(used.id,"magic_ring");used.enchant_kind=AW_ENCH_USED;used.charge_max=20;strcpy(used.enchantment,"e");
        strcpy(strikes.id,"magic_sword");strikes.enchant_kind=AW_ENCH_STRIKES;strikes.charge_max=100;strcpy(strikes.enchantment,"s");
        strcpy(plain.id,"plain_ring");
        assert(!AW_MagicSelect(&state,&used));                       /* not owned */
        assert(AW_ItemAdd(&state,used.id,1) && AW_ItemAdd(&state,strikes.id,1) && AW_ItemAdd(&state,plain.id,1));
        assert(!AW_MagicSelect(&state,&plain) && !AW_MagicSelect(&state,&strikes));
        assert(AW_MagicSelect(&state,&used) && !strcmp(state.magic.selected,"magic_ring"));
        assert(AW_MagicCharge(&state,&used)==20 && !state.magic.charge_known);
        assert(AW_MagicSetCharge(&state,&used,7) && AW_MagicCharge(&state,&used)==7);
        assert(!AW_MagicSetCharge(&state,&plain,1) && !AW_MagicSetCharge(&state,&used,NAN));
        assert(AW_MagicRecharge(&state,&used,20,.05f) && fabsf(AW_MagicCharge(&state,&used)-8)<1e-4f);
        assert(AW_MagicRecharge(&state,&used,1000,.05f) && AW_MagicCharge(&state,&used)==20 && !state.magic.charge_known);
        assert(!AW_MagicRecharge(&state,&used,10,.05f));                /* full stays full */
        assert(AW_MagicSetCharge(&state,&strikes,1) && AW_MagicRecharge(&state,&strikes,20,.05f));
        assert(AW_MagicSetCharge(&state,&used,3));
        used.flags|=AW_INV_DROP;prior=state;
        assert(AW_InventoryDrop(&state,&used,1,"seyda",pos,0)<0 && !memcmp(&state,&prior,sizeof(state)));
        assert(AW_ItemAdd(&state,used.id,-1));
        assert(!state.magic.selected[0] && AW_MagicCharge(&state,&used)==20);
        assert(AW_MagicCharge(&state,&plain)==0);
    }
    return 0;
}
