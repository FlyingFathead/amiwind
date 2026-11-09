/* SPDX-License-Identifier: GPL-3.0-only
 * ROBE-PART-NOT-BAKED-62 / EQUIP-ACTION-REGRESSION-62: the original's slot rules in a sequence (OpenMW 0.51
 * mwworld/inventorystore.cpp equip, mwclass/clothing.cpp and armor.cpp getEquipmentSlots, mwworld/actionequip.cpp):
 * one item per slot, a robe in its own slot over the shirt and pants (they stay worn, hidden by part priority), the
 * two-handed weapon and the shield excluding each other, rings rotating; then the drawn parts of that outfit from a
 * small recipe (aw_player_parts.c): the robe's chest drawn, the shirt's chest and the pants' legs covered. */
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include "aw_inventory.h"
#include "aw_player_parts.h"
static aw_state_t state;
static aw_inventory_item_t shirt,shirt2,pants,robe,cuirass,shield,claymore,ring1,ring2,ring3;
static const aw_inventory_item_t *held_right,*held_left;
static int hand(int slot,aw_inventory_item_t *out){
    const aw_inventory_item_t *h=slot==AW_SLOT_RIGHT?held_right:slot==AW_SLOT_LEFT?held_left:NULL;
    if(!h || !state.inventory.equipped[slot][0])return 0;
    *out=*h;return 1;
}
static void item(aw_inventory_item_t *it,const char *id,int category,int subtype,unsigned slots){
    memset(it,0,sizeof(*it));strcpy(it->id,id);it->category=category;it->subtype=subtype;it->slots=slots;
    it->flags=AW_INV_EQUIP|AW_INV_EQUIP_SUPPORTED;it->health=100;
    assert(AW_ItemAdd(&state,id,1));
}
static int worn(int slot,const char *id){return !strcmp(state.inventory.equipped[slot],id);}
static int count_worn(void){int i,n=0;for(i=0;i<AW_INVENTORY_SLOTS;i++)n+=state.inventory.equipped[i][0]!=0;return n;}
int main(void){
    memset(&state,0,sizeof(state));
    item(&shirt,"common_shirt_01",AW_INV_CLOTHING,5,1U<<AW_SLOT_SHIRT);
    item(&shirt2,"common_shirt_02",AW_INV_CLOTHING,5,1U<<AW_SLOT_SHIRT);
    item(&pants,"common_pants_01",AW_INV_CLOTHING,0,1U<<AW_SLOT_PANTS);
    item(&robe,"extravagant_robe_01_t",AW_INV_CLOTHING,4,1U<<AW_SLOT_ROBE);
    item(&cuirass,"chitin cuirass",AW_INV_ARMOUR,1,1U<<AW_SLOT_CUIRASS);
    item(&shield,"chitin_shield",AW_INV_ARMOUR,8,1U<<AW_SLOT_LEFT);
    item(&claymore,"iron claymore",AW_INV_WEAPON,0,1U<<AW_SLOT_RIGHT);claymore.weapon=3;
    item(&ring1,"ring_1",AW_INV_CLOTHING,8,(1U<<AW_SLOT_LRING)|(1U<<AW_SLOT_RRING));
    item(&ring2,"ring_2",AW_INV_CLOTHING,8,(1U<<AW_SLOT_LRING)|(1U<<AW_SLOT_RRING));
    item(&ring3,"ring_3",AW_INV_CLOTHING,8,(1U<<AW_SLOT_LRING)|(1U<<AW_SLOT_RRING));
    aw_inventory_hand_item=hand;
    /* 1 shirt, 2 pants: one each */
    assert(AW_InventoryEquip(&state,&shirt) && worn(AW_SLOT_SHIRT,shirt.id) && count_worn()==1);
    assert(AW_InventoryEquip(&state,&pants) && worn(AW_SLOT_PANTS,pants.id) && count_worn()==2);
    /* 3 robe: its own slot; shirt and pants stay worn (clothing.cpp: Slot_Robe only) */
    assert(AW_InventoryEquip(&state,&robe) && worn(AW_SLOT_ROBE,robe.id) && worn(AW_SLOT_SHIRT,shirt.id) &&
           worn(AW_SLOT_PANTS,pants.id) && count_worn()==3);
    /* 4 another shirt: replaces the first in the one shirt slot */
    assert(AW_InventoryEquip(&state,&shirt2) && worn(AW_SLOT_SHIRT,shirt2.id) && !AW_InventoryEquipped(&state,shirt.id) &&
           count_worn()==3);
    /* 5 cuirass: its own slot */
    assert(AW_InventoryEquip(&state,&cuirass) && worn(AW_SLOT_CUIRASS,cuirass.id) && count_worn()==4);
    /* 6 shield, then a two-handed weapon: the shield goes back to the pack */
    assert(AW_InventoryEquip(&state,&shield) && worn(AW_SLOT_LEFT,shield.id) && count_worn()==5);
    held_left=&shield;
    assert(AW_InventoryEquip(&state,&claymore) && worn(AW_SLOT_RIGHT,claymore.id) && !state.inventory.equipped[AW_SLOT_LEFT][0] &&
           count_worn()==5);
    /* 7 the shield again: the two-handed weapon goes */
    held_left=NULL;held_right=&claymore;
    assert(AW_InventoryEquip(&state,&shield) && worn(AW_SLOT_LEFT,shield.id) && !state.inventory.equipped[AW_SLOT_RIGHT][0] &&
           count_worn()==5);
    held_right=NULL;
    /* 8 three rings: left, right, then the right moves left and the new one goes right */
    assert(AW_InventoryEquip(&state,&ring1) && worn(AW_SLOT_LRING,ring1.id));
    assert(AW_InventoryEquip(&state,&ring2) && worn(AW_SLOT_RRING,ring2.id));
    assert(AW_InventoryEquip(&state,&ring3) && worn(AW_SLOT_LRING,ring2.id) && worn(AW_SLOT_RRING,ring3.id) &&
           !AW_InventoryEquipped(&state,ring1.id) && count_worn()==7);
    {   /* 9 a skirt with pants: both worn (Slot_Skirt and Slot_Pants) */
        aw_inventory_item_t skirt;
        item(&skirt,"common_skirt_01",AW_INV_CLOTHING,7,1U<<AW_SLOT_SKIRT);
        assert(AW_InventoryEquip(&state,&skirt) && worn(AW_SLOT_SKIRT,skirt.id) && worn(AW_SLOT_PANTS,pants.id));
        assert(AW_InventoryUnequip(&state,skirt.id)==1);
    }
    {   /* 10 boots, then shoes: one boots slot (clothing.cpp gives shoes Slot_Boots), the shoes take it */
        aw_inventory_item_t boots,shoes;
        item(&boots,"chitin boots",AW_INV_ARMOUR,5,1U<<AW_SLOT_BOOTS);boots.flags|=AW_INV_BEAST_FEET;
        item(&shoes,"common_shoes_01",AW_INV_CLOTHING,1,1U<<AW_SLOT_BOOTS);shoes.flags|=AW_INV_BEAST_FEET;
        assert(AW_InventoryEquip(&state,&boots) && worn(AW_SLOT_BOOTS,boots.id));
        assert(AW_InventoryEquip(&state,&shoes) && worn(AW_SLOT_BOOTS,shoes.id) && !AW_InventoryEquipped(&state,boots.id));
        /* 11 a beast race: the game's own lines (armor.cpp / clothing.cpp canBeEquipped) */
        {
            aw_inventory_item_t helm,hood;
            item(&helm,"iron_helmet",AW_INV_ARMOUR,0,1U<<AW_SLOT_HELMET);helm.flags|=AW_INV_BEAST_HEAD;
            item(&hood,"fur_colovian_helm",AW_INV_ARMOUR,0,1U<<AW_SLOT_HELMET);   /* no Head part: a beast wears it */
            assert(!strcmp(AW_InventoryBeastRefusal(&helm,1),"sNotifyMessage13"));
            assert(!strcmp(AW_InventoryBeastRefusal(&boots,1),"sNotifyMessage14"));
            assert(!strcmp(AW_InventoryBeastRefusal(&shoes,1),"sNotifyMessage15"));
            assert(!AW_InventoryBeastRefusal(&hood,1) && !AW_InventoryBeastRefusal(&helm,0) && !AW_InventoryBeastRefusal(&robe,1));
        }
    }
    {   /* 12 TORCH-HIDES-HELM-62: a slot of every kind worn, then the torch: it takes the carried-left slot only (the
         * shield goes back to the pack, as in OpenMW 0.51 inventorystore.cpp), every other slot stays; put away, it
         * changes nothing else */
        aw_inventory_item_t helm,pl,pr,gl,gr,amulet,torch;char before[AW_INVENTORY_SLOTS][64];int s;
        item(&helm,"fur_colovian_helm",AW_INV_ARMOUR,0,1U<<AW_SLOT_HELMET);
        item(&pl,"chitin pauldron - left",AW_INV_ARMOUR,2,1U<<AW_SLOT_LPAULDRON);
        item(&pr,"chitin pauldron - right",AW_INV_ARMOUR,3,1U<<AW_SLOT_RPAULDRON);
        item(&gl,"chitin guantlet - left",AW_INV_ARMOUR,6,1U<<AW_SLOT_LGAUNTLET);
        item(&gr,"chitin guantlet - right",AW_INV_ARMOUR,7,1U<<AW_SLOT_RGAUNTLET);
        item(&amulet,"amulet_1",AW_INV_CLOTHING,9,1U<<AW_SLOT_AMULET);
        item(&torch,"aw_debug_torch",AW_INV_MISC,0,1U<<AW_SLOT_LEFT);torch.flags|=AW_INV_LIGHT;
        assert(AW_InventoryEquip(&state,&helm) && AW_InventoryEquip(&state,&pl) && AW_InventoryEquip(&state,&pr) &&
               AW_InventoryEquip(&state,&gl) && AW_InventoryEquip(&state,&gr) && AW_InventoryEquip(&state,&amulet) &&
               AW_InventoryEquip(&state,&robe));
        assert(worn(AW_SLOT_LEFT,shield.id));
        memcpy(before,state.inventory.equipped,sizeof(before));
        held_left=&shield;
        assert(AW_InventoryEquip(&state,&torch) && worn(AW_SLOT_LEFT,torch.id));
        for(s=0;s<AW_INVENTORY_SLOTS;s++)if(s!=AW_SLOT_LEFT)assert(!strcmp(state.inventory.equipped[s],before[s]));
        held_left=NULL;
        assert(AW_InventoryUnequip(&state,torch.id)==1);
        for(s=0;s<AW_INVENTORY_SLOTS;s++)if(s!=AW_SLOT_LEFT)assert(!strcmp(state.inventory.equipped[s],before[s]));
        assert(!state.inventory.equipped[AW_SLOT_LEFT][0]);
    }
    {   /* the drawn parts: chest 3 and legs 4 of the race, the shirt over the chest, the pants over the legs, the
         * robe (rank 24) over the chest with its own model and covering the legs */
        static const char recipe[]=
            "AWPP1\n"
            "T h progs/humanoid.awsk 20 21\n"
            "A h 0 view/parts_hm.txt\n"
            "R dark|elf 0 h 1.0000 1.0000\n"
            "S dark|elf 0 3 aaaaaaaaaaaa\n"
            "S dark|elf 0 4 bbbbbbbbbbbb\n"
            "I common_shirt_02 2 3=cccccccccccc/-,cccccccccccc/-\n"
            "I common_pants_01 2 4=dddddddddddd/-,dddddddddddd/-\n"
            "I extravagant_robe_01_t 24 3=eeeeeeeeeeee/-,eeeeeeeeeeee/- 4=-,-\n";
        const char *items[AW_INVENTORY_SLOTS];aw_parts_body_t body;int n=0,i,s3=-1,s4=-1;
        for(i=AW_SLOT_HELMET;i<=AW_SLOT_ROBE;i++)if(state.inventory.equipped[i][0])items[n++]=state.inventory.equipped[i];
        assert(AW_PartsAssemble(recipe,(long)strlen(recipe),"dark elf",0,NULL,NULL,items,n,&body));
        for(i=0;i<body.count;i++){if(body.slot[i]==3)s3=i;if(body.slot[i]==4)s4=i;}
        assert(body.count==1 && s3==0 && s4<0);
        assert(!strcmp(body.model[s3],"progs/parts/ee/eeeeeeeeee.mdl"));
        /* the robe off: the shirt and the pants show again */
        assert(AW_InventoryUnequip(&state,robe.id)==1);
        for(n=0,i=AW_SLOT_HELMET;i<=AW_SLOT_ROBE;i++)if(state.inventory.equipped[i][0])items[n++]=state.inventory.equipped[i];
        assert(AW_PartsAssemble(recipe,(long)strlen(recipe),"dark elf",0,NULL,NULL,items,n,&body));
        assert(body.count==2 && !strcmp(body.model[0],"progs/parts/cc/cccccccccc.mdl") &&
               !strcmp(body.model[1],"progs/parts/dd/dddddddddd.mdl"));
    }
    puts("equip slots ok");return 0;
}
