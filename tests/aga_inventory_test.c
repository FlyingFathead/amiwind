/* SPDX-License-Identifier: GPL-3.0-only
 * Real state/rule transactions: no original game data or fabricated inventory. */
#include <assert.h>
#include <string.h>
#include <math.h>
#include <stdio.h>
#include "aw_inventory.h"
static aw_state_t state,prior;
static aw_inventory_item_t ring,other,third;
/* the engine's hand lookup (AW_InventoryEquippedItem), here: what the test says the hands hold */
/* ENCUMBRANCE-INCOMPLETE-61: the weights the engine reads from the records, here by name */
static int fixture_weight(const char *id,float *weight){
    if(!strcmp(id,"heavy")){*weight=10;return 1;}
    if(!strncmp(id,"light",5)){*weight=.5f;return 1;}
    return 0;
}
static aw_state_t *test_hands;static const aw_inventory_item_t *test_right,*test_left;
static int test_hand(int slot,aw_inventory_item_t *out){
    const aw_inventory_item_t *held=slot==AW_SLOT_RIGHT?test_right:slot==AW_SLOT_LEFT?test_left:NULL;
    if(!held || !test_hands || !test_hands->inventory.equipped[slot][0])return 0;
    *out=*held;return 1;
}
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
    /* INVENTORY-ORIGINAL-LIMITS-61: no kind limit: with 400 kinds carried a new kind is taken; a row whose count fell
     * to 0 takes the next new kind in its place, its condition mark gone with the last one */
    for(i=0;i<400;i++){char name[32];sprintf(name,"item%d",i);assert(AW_ItemAdd(&state,name,1));}
    assert(AW_ItemCount(&state)==400 && AW_StateGet(&state,AW_ITEM,"item399")==1 && AW_StateGet(&state,AW_ITEM,"ITEM250")==1);
    assert(AW_ItemRefusal(&state,"unknown_item",1)==AW_ITEM_OK && AW_ItemRoom(&state)>0);
    assert(AW_ItemAdd(&state,"item3",INT32_MAX-1) && AW_ItemRefusal(&state,"item3",1)==AW_ITEM_TOO_MANY);
    AW_ItemMark(&state,100,AW_ITEM_CONDITION,.5f);assert(AW_ITEM_HAS(&state,100,AW_ITEM_CONDITION));
    assert(AW_ItemAdd(&state,"item100",-1) && !AW_ITEM_HAS(&state,100,AW_ITEM_CONDITION));
    assert(!strcmp(AW_ItemRefusalText(&state,AW_ITEM_FULL),"not enough memory for another kind of item (399 kinds carried)"));
    assert(AW_InventoryPickup(&state,0) && !strcmp(AW_ITEM_ID(&state,100),"unknown_item"));
    assert(AW_ItemCount(&state)==400 && AW_StateGet(&state,AW_ITEM,"unknown_item")==1 && !AW_StateGet(&state,AW_ITEM,"item100"));
    assert(AW_ItemAdd(&state,"kind400",1) && AW_ItemCount(&state)==401 && AW_ItemIndex(&state,"kind400")==400);
    assert(AW_ItemAdd(&state,"never_held",0) && AW_ItemCount(&state)==401);   /* none of it: no row */
    /* DBG-GIVE-MONEY-62: the gold limit 999,999,999 (aw_state.h AW_GOLD_MAX): a gain past it is kept up to it, never
     * refused or wrapped; at the limit nothing more; spending works from it; any case of the id; a loaded save's row too;
     * other items keep the 32-bit limit. The count column shows it in four characters (OpenMW getCountString). */
    {
        aw_state_t g;char text[16];
        memset(&g,0,sizeof(g));
        assert(AW_GOLD_MAX==999999999L);
        assert(AW_ItemAdd(&g,"gold_001",1000000) && AW_StateGet(&g,AW_ITEM,"gold_001")==1000000);
        assert(AW_ItemAdd(&g,"Gold_001",999000000) && AW_StateGet(&g,AW_ITEM,"gold_001")==AW_GOLD_MAX);   /* held */
        assert(AW_ItemAdd(&g,"gold_001",65535) && AW_StateGet(&g,AW_ITEM,"gold_001")==AW_GOLD_MAX);      /* at it */
        assert(AW_StateSet(&g,AW_ITEM,"GOLD_001",INT32_MAX) && AW_StateGet(&g,AW_ITEM,"gold_001")==AW_GOLD_MAX);
        assert(AW_ItemAdd(&g,"gold_001",-1) && AW_StateGet(&g,AW_ITEM,"gold_001")==AW_GOLD_MAX-1);
        assert(AW_ItemAdd(&g,"gold_001",AW_GOLD_MAX) && AW_StateGet(&g,AW_ITEM,"gold_001")==AW_GOLD_MAX); /* no wrap */
        assert(AW_ItemAdd(&g,"gold_005",2000000000) && AW_StateGet(&g,AW_ITEM,"gold_005")==2000000000);  /* not gold_001 */
        assert(AW_GoldCap("gold_001",INT32_MAX)==AW_GOLD_MAX && AW_GoldCap("gold_001",5)==5 && AW_GoldCap("arrow",INT32_MAX)==INT32_MAX);
        AW_ItemsFree(&g);memset(&g,0,sizeof(g));
        assert(AW_ItemAppend(&g,"gold_001",INT32_MAX) && AW_StateGet(&g,AW_ITEM,"gold_001")==AW_GOLD_MAX);   /* a save */
        AW_ItemsFree(&g);
        assert(AW_InventoryCountText(1,text,sizeof(text))==1 && !strcmp(text,"1"));
        AW_InventoryCountText(9999,text,sizeof(text));assert(!strcmp(text,"9999"));
        AW_InventoryCountText(10000,text,sizeof(text));assert(!strcmp(text,"10k"));
        AW_InventoryCountText(999999,text,sizeof(text));assert(!strcmp(text,"999k"));
        AW_InventoryCountText(1000000,text,sizeof(text));assert(!strcmp(text,"1m"));
        AW_InventoryCountText(AW_GOLD_MAX,text,sizeof(text));assert(!strcmp(text,"999m"));
        AW_InventoryCountText(2000000000L,text,sizeof(text));assert(!strcmp(text,"2b"));
        assert(AW_InventoryCountText(5,text,5)==-1);
        printf("gold limit %ld: held on add, set and load; count column 1m / 999m pass\n",(long)AW_GOLD_MAX);
    }
    /* the running weight (ENCUMBRANCE-INCOMPLETE-61): no record weight in these fixtures, so the hook gives it */
    {
        aw_state_t w;int k;
        memset(&w,0,sizeof(w));aw_item_weight=fixture_weight;
        assert(AW_ItemAdd(&w,"heavy",3) && AW_ItemsBurden(&w)==30);           /* 3 x 10 */
        assert(AW_ItemAdd(&w,"light",4) && fabsf(AW_ItemsBurden(&w)-32)<1e-4f); /* + 4 x 0.5 */
        assert(AW_ItemAdd(&w,"heavy",-1) && fabsf(AW_ItemsBurden(&w)-22)<1e-4f);
        assert(AW_ItemAdd(&w,"heavy",-2) && fabsf(AW_ItemsBurden(&w)-2)<1e-4f);
        assert(AW_ItemAdd(&w,"unweighed",5) && fabsf(AW_ItemsBurden(&w)-2)<1e-4f);  /* no record: 0 */
        for(k=0;k<400;k++){char name[32];sprintf(name,"light%d",k);assert(AW_ItemAdd(&w,name,2));}
        assert(fabsf(AW_ItemsBurden(&w)-402)<1e-2f);                         /* 2 + 400 x 2 x 0.5 */
        AW_ItemsWeigh(&w);assert(fabsf(AW_ItemsBurden(&w)-402)<1e-3f);     /* summed again: the same */
        aw_item_weight=NULL;AW_ItemsFree(&w);assert(!AW_ItemCount(&w) && AW_ItemsBurden(&w)==0);
    }
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
        assert(AW_MagicCharge(&state,&used)==20 && !AW_ITEM_HAS(&state,AW_ItemIndex(&state,used.id),AW_ITEM_CHARGE));
        assert(AW_MagicSetCharge(&state,&used,7) && AW_MagicCharge(&state,&used)==7);
        assert(!AW_MagicSetCharge(&state,&plain,1) && !AW_MagicSetCharge(&state,&used,NAN));
        assert(AW_MagicRecharge(&state,&used,20,.05f) && fabsf(AW_MagicCharge(&state,&used)-8)<1e-4f);
        assert(AW_MagicRecharge(&state,&used,1000,.05f) && AW_MagicCharge(&state,&used)==20 &&
               !AW_ITEM_HAS(&state,AW_ItemIndex(&state,used.id),AW_ITEM_CHARGE));
        assert(!AW_MagicRecharge(&state,&used,10,.05f));                /* full stays full */
        assert(AW_MagicSetCharge(&state,&strikes,1) && AW_MagicRecharge(&state,&strikes,20,.05f));
        assert(AW_MagicSetCharge(&state,&used,3));
        used.flags|=AW_INV_DROP;prior=state;
        assert(AW_InventoryDrop(&state,&used,1,"seyda",pos,0)<0 && !memcmp(&state,&prior,sizeof(state)));
        assert(AW_ItemAdd(&state,used.id,-1));
        assert(!state.magic.selected[0] && AW_MagicCharge(&state,&used)==20);
        assert(AW_MagicCharge(&state,&plain)==0);
    }
    /* The debug torch (test only): given once (a saved global marks it), never when switched off,
     * and its burn time never runs out; an ordinary light counts down to 0 (OpenMW actors.cpp). */
    {
        aw_inventory_item_t torch,lamp;
        memset(&state,0,sizeof(state));
        prior=state;assert(!AW_DebugTorchGrant(&state,0));assert(!memcmp(&state,&prior,sizeof(state)));
        assert(AW_DebugTorchGrant(&state,1));
        assert(AW_StateGet(&state,AW_ITEM,AW_DEBUG_TORCH_ID)==1 && AW_StateGet(&state,AW_GLOBAL,AW_DEBUG_TORCH_GRANTED)==1);
        prior=state;assert(!AW_DebugTorchGrant(&state,1));assert(!memcmp(&state,&prior,sizeof(state)));  /* second exit, reload */
        assert(AW_ItemAdd(&state,AW_DEBUG_TORCH_ID,-1));assert(!AW_DebugTorchGrant(&state,1));          /* dropped or sold: not again */
        assert(AW_StateGet(&state,AW_ITEM,AW_DEBUG_TORCH_ID)==0);
        memset(&state,0,sizeof(state));
        for(i=0;i<400;i++){char name[32];sprintf(name,"item%d",i);assert(AW_ItemAdd(&state,name,1));}
        assert(AW_DebugTorchGrant(&state,1) && AW_StateGet(&state,AW_ITEM,AW_DEBUG_TORCH_ID)==1);  /* 400 kinds: no limit */
        assert(AW_StateGet(&state,AW_GLOBAL,AW_DEBUG_TORCH_GRANTED)==1 && AW_ItemCount(&state)==401);
        memset(&torch,0,sizeof(torch));strcpy(torch.id,AW_DEBUG_TORCH_ID);torch.flags=AW_INV_LIGHT;
        torch.light_time=AW_LIGHT_INFINITE;lamp=torch;lamp.light_time=210;
        assert(AW_LightBurn(&torch,AW_LIGHT_INFINITE,3600)==AW_LIGHT_INFINITE);
        assert(AW_LightBurn(&torch,AW_LIGHT_INFINITE,1e9f)==AW_LIGHT_INFINITE);
        assert(AW_LightBurn(&lamp,210,10)==200 && AW_LightBurn(&lamp,5,10)==0 && AW_LightBurn(&lamp,0,1)==0);
        lamp.flags=0;assert(AW_LightBurn(&lamp,210,10)==0);   /* not a light */
    }
    {   /* worn armour and the hands (OpenMW armor.cpp getEquipmentSlots and canBeEquipped, weapon.cpp, actionequip.cpp) */
        static aw_inventory_item_t claymore,sword,shield,helm,bracer;
        assert(AW_InventoryArmourSlot(0)==AW_SLOT_HELMET && AW_InventoryArmourSlot(1)==AW_SLOT_CUIRASS &&
               AW_InventoryArmourSlot(4)==AW_SLOT_GREAVES && AW_InventoryArmourSlot(5)==AW_SLOT_BOOTS &&
               AW_InventoryArmourSlot(8)==AW_SLOT_LEFT && AW_InventoryArmourSlot(9)==AW_SLOT_LGAUNTLET &&
               AW_InventoryArmourSlot(10)==AW_SLOT_RGAUNTLET && AW_InventoryArmourSlot(11)==-1 && AW_InventoryArmourSlot(-1)==-1);
        assert(AW_InventoryHitSlot(AW_SLOT_CUIRASS)==0 && AW_InventoryHitSlot(AW_SLOT_HELMET)==1 &&
               AW_InventoryHitSlot(AW_SLOT_LEFT)==8 && AW_InventoryHitSlot(AW_SLOT_RIGHT)==-1 && AW_InventoryHitSlot(AW_SLOT_LRING)==-1);
        memset(&state,0,sizeof(state));
        memset(&claymore,0,sizeof(claymore));strcpy(claymore.id,"steel claymore");claymore.category=AW_INV_WEAPON;
        claymore.weapon=3;claymore.slots=1U<<AW_SLOT_RIGHT;claymore.flags=AW_INV_EQUIP|AW_INV_EQUIP_SUPPORTED;
        sword=claymore;strcpy(sword.id,"steel longsword");sword.weapon=2;
        memset(&shield,0,sizeof(shield));strcpy(shield.id,"steel_shield");shield.category=AW_INV_ARMOUR;shield.subtype=8;
        shield.slots=1U<<AW_SLOT_LEFT;shield.flags=AW_INV_EQUIP|AW_INV_EQUIP_SUPPORTED;
        helm=shield;strcpy(helm.id,"iron_helmet");helm.subtype=0;helm.slots=1U<<AW_SLOT_HELMET;
        bracer=shield;strcpy(bracer.id,"cloth bracer left");bracer.subtype=9;bracer.slots=1U<<AW_SLOT_LGAUNTLET;
        assert(AW_InventoryEquipConflict(&claymore,NULL,&shield)==AW_SLOT_LEFT);
        assert(AW_InventoryEquipConflict(&sword,NULL,&shield)==-1);
        assert(AW_InventoryEquipConflict(&shield,&claymore,NULL)==AW_SLOT_RIGHT);
        assert(AW_InventoryEquipConflict(&shield,&sword,NULL)==-1 && AW_InventoryEquipConflict(&helm,&claymore,&shield)==-1);
        assert(AW_ItemAdd(&state,claymore.id,1) && AW_ItemAdd(&state,shield.id,1) && AW_ItemAdd(&state,helm.id,1) &&
               AW_ItemAdd(&state,bracer.id,1) && AW_ItemAdd(&state,sword.id,1));
        assert(AW_InventoryEquip(&state,&helm) && !strcmp(state.inventory.equipped[AW_SLOT_HELMET],helm.id));
        assert(AW_InventoryEquip(&state,&bracer) && !strcmp(state.inventory.equipped[AW_SLOT_LGAUNTLET],bracer.id));
        /* no hand lookup (the pure fixture): both hands stay as they are */
        assert(AW_InventoryEquip(&state,&shield) && AW_InventoryEquip(&state,&claymore));
        assert(state.inventory.equipped[AW_SLOT_LEFT][0] && state.inventory.equipped[AW_SLOT_RIGHT][0]);
        /* with the hand lookup: the two-handed weapon takes the shield off; the shield takes it out again */
        test_hands=&state;test_right=&claymore;test_left=&shield;aw_inventory_hand_item=test_hand;
        assert(AW_InventoryUnequip(&state,claymore.id)==1);
        test_right=NULL;assert(AW_InventoryEquip(&state,&claymore));
        assert(!strcmp(state.inventory.equipped[AW_SLOT_RIGHT],claymore.id) && !state.inventory.equipped[AW_SLOT_LEFT][0]);
        test_right=&claymore;test_left=NULL;assert(AW_InventoryEquip(&state,&shield));
        assert(!strcmp(state.inventory.equipped[AW_SLOT_LEFT],shield.id) && !state.inventory.equipped[AW_SLOT_RIGHT][0]);
        test_right=NULL;test_left=&shield;assert(AW_InventoryEquip(&state,&sword));       /* one-handed: the shield stays */
        assert(!strcmp(state.inventory.equipped[AW_SLOT_RIGHT],sword.id) && !strcmp(state.inventory.equipped[AW_SLOT_LEFT],shield.id));
        aw_inventory_hand_item=NULL;
    }
    return 0;
}
