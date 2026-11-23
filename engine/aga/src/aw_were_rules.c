/* SPDX-License-Identifier: GPL-2.0-or-later
 * The player's change of form into the werewolf and back, on the game state alone: aw_were_rules.h. */
#include <string.h>
#include "aw_were_rules.h"
#include "aw_effects.h"

int AW_WereItemShown(const char *id,int own,int form){
    if(!AW_PartsWerewolfWorn(id))return 1;
    return own && !form;
}

int AW_WereChange(aw_were_t *w,int set,aw_state_t *s,const aw_inventory_item_t *robe,aw_actor_t *player,
                  const int32_t *numbers,int count,aw_were_report_t *out){
    aw_were_report_t r;int i,had[AW_INVENTORY_SLOTS];
    memset(&r,0,sizeof(r));
    set=set!=0;
    if(!w || !s || (w->player!=0)==set){if(out)*out=r;return 0;}   /* 1884-1886: already so */
    r.changed=1;
    w->player=set;                                                     /* 1894 */
    if(set){
        /* 1900, inventorystore.cpp unequipAll: every slot; a worn item's constant effects end with it at once (the
         * worn effects' frame would end them a frame later, after the stats below were kept) */
        for(i=0;i<AW_INVENTORY_SLOTS;i++)had[i]=s->inventory.equipped[i][0]!=0;
        for(i=0;i<AW_INVENTORY_SLOTS;i++)if(s->inventory.equipped[i][0]){
            char id[64];memcpy(id,s->inventory.equipped[i],sizeof(id));id[sizeof(id)-1]=0;
            AW_InventoryUnequip(s,id);
        }
        for(i=0;i<AW_INVENTORY_SLOTS;i++)if(had[i]){
            r.taken_off++;
            if(player)AW_EffectsRemoveSource(player,AW_EFFECT_SOURCE_CONSTANT+i);
        }
        /* 1901-1902: the werewolf robe added and worn in the robe slot */
        if(robe && AW_PartsWerewolfWorn(robe->id) && AW_ItemAdd(s,robe->id,1)){
            r.robe_added=1;
            r.robe_worn=AW_InventoryEquipSlot(s,robe,AW_SLOT_ROBE);
        }
    }else{
        /* 1906-1907: the robe slot emptied, one werewolf robe taken away; the other items stay as they are (the
         * original puts nothing back on) */
        if(s->inventory.equipped[AW_SLOT_ROBE][0]){
            char id[64];memcpy(id,s->inventory.equipped[AW_SLOT_ROBE],sizeof(id));id[sizeof(id)-1]=0;
            AW_InventoryUnequip(s,id);
            if(player)AW_EffectsRemoveSource(player,AW_EFFECT_SOURCE_CONSTANT+AW_SLOT_ROBE);
        }
        if(AW_StateGet(s,AW_ITEM,AW_WERE_ROBE)>0 && AW_ItemAdd(s,AW_WERE_ROBE,-1))r.robe_removed=1;
    }
    /* 1917-1919: the temporary effects end, both ways */
    if(player)r.purged=AW_EffectsPurgeTemporary(player);
    /* 1922-1931, player.cpp setWerewolfStats / restoreStats */
    if(player && set){
        for(i=0;i<8;i++)w->attr[i]=player->attr_base[i];
        for(i=0;i<27;i++)w->skill[i]=player->skill_base[i];
        w->kept=1;
        for(i=0;i<8+27;i++){
            int v=numbers && count>i/4?(int)(((uint32_t)numbers[i/4]>>(8*(3-i%4)))&255):255;
            if(v==255 || i==8+20)continue;   /* no setting; Acrobatics stays (SetWerewolfAcrobatics) */
            if(i<8)player->attr_base[i]=(short)v;else player->skill_base[i-8]=(short)v;
        }
        r.stats=1;
    }else if(player && w->kept){
        for(i=0;i<8;i++)player->attr_base[i]=w->attr[i];
        for(i=0;i<27;i++)player->skill_base[i]=w->skill[i];
        w->kept=0;r.stats=2;
    }
    if(out)*out=r;
    return 1;
}
