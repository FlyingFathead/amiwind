/* SPDX-License-Identifier: GPL-2.0-or-later
 * Original item identities and bounded persistent equipment/drop transactions.
 * UI selection never fabricates inventory and never directly deletes an item. */
#ifndef AW_INVENTORY_RULES_ONLY
#include "quakedef.h"
#include "aw_combat.h"
#include "aw_character.h"
#include "aw_story.h"
#include "chim/chim.h"
extern int AW_SceneryCount(void);
#endif
#include <string.h>
#include <math.h>
#include <limits.h>
#include "aw_inventory.h"
#if AW_STATE_VALUES > 32
#error Inventory condition bitset requires AW_STATE_VALUES <= 32
#endif
/* Catalogue binary search and UI sorting need ordering, while AmiQuake's
 * Q_strcasecmp deliberately returns -1 for every unequal pair. Catalogue IDs
 * are original case-folded IDs; compare ASCII letters without changing Quake. */
int AW_InventoryCompare(const char *a,const char *b){
    unsigned int x,y;
    do{
        x=(unsigned char)*a++;y=(unsigned char)*b++;
        if(x>='A' && x<='Z')x+='a'-'A';
        if(y>='A' && y<='Z')y+='a'-'A';
        if(x!=y)return x<y?-1:1;
    }while(x);
    return 0;
}
static int inv_id(const char *s,int limit){
    int n=0;if(!s)return 0;
    while(*s){if((unsigned char)*s<32 || ++n>=limit)return 0;s++;}
    return n>0;
}
int AW_InventoryEquipped(const aw_state_t *s,const char *id){
    int i,n=0;if(!s || !inv_id(id,64))return 0;
    for(i=0;i<AW_INVENTORY_SLOTS;i++)if(!strcmp(s->inventory.equipped[i],id))n++;
    return n;
}
int AW_InventoryEquipSlot(aw_state_t *s,const aw_inventory_item_t *item,int slot){
    int i,used=0;
    if(!s || !item || !inv_id(item->id,64) || slot<0 || slot>=AW_INVENTORY_SLOTS ||
       !(item->slots&(1U<<slot)) || (item->flags&(AW_INV_EQUIP|AW_INV_EQUIP_SUPPORTED))!=(AW_INV_EQUIP|AW_INV_EQUIP_SUPPORTED) ||
       AW_StateGet(s,AW_ITEM,item->id)<1)return 0;
    if(!strcmp(s->inventory.equipped[slot],item->id))return 1;
    for(i=0;i<AW_INVENTORY_SLOTS;i++)if(i!=slot && !strcmp(s->inventory.equipped[i],item->id))used++;
    if(used>=AW_StateGet(s,AW_ITEM,item->id))return 0;
    strcpy(s->inventory.equipped[slot],item->id);s->inventory.initialized=1;return 1;
}
int AW_InventoryEquip(aw_state_t *s,const aw_inventory_item_t *item){
    int i,first=-1;
    if(!s || !item || !inv_id(item->id,64))return 0;
    if(AW_InventoryEquipped(s,item->id))return 1;
    for(i=0;i<AW_INVENTORY_SLOTS;i++)if(item->slots&(1U<<i)){
        if(first<0)first=i;
        if(!s->inventory.equipped[i][0])return AW_InventoryEquipSlot(s,item,i);
    }
    /* Ring rotation matches ActionEquip: old right moves left, new goes right. */
    if(item->slots==((1U<<AW_SLOT_LRING)|(1U<<AW_SLOT_RRING))){
        char right[64];
        strcpy(right,s->inventory.equipped[AW_SLOT_RRING]);
        if((item->flags&(AW_INV_EQUIP|AW_INV_EQUIP_SUPPORTED))!=(AW_INV_EQUIP|AW_INV_EQUIP_SUPPORTED) ||
           AW_StateGet(s,AW_ITEM,item->id)<1 || !inv_id(item->id,64))return 0;
        strcpy(s->inventory.equipped[AW_SLOT_LRING],right);
        strcpy(s->inventory.equipped[AW_SLOT_RRING],item->id);
        s->inventory.initialized=1;return 1;
    }
    return first>=0?AW_InventoryEquipSlot(s,item,first):0;
}
int AW_InventoryUnequip(aw_state_t *s,const char *id){
    int i,n=0;if(!s || !inv_id(id,64))return 0;
    for(i=0;i<AW_INVENTORY_SLOTS;i++)if(!strcmp(s->inventory.equipped[i],id)){
        memset(s->inventory.equipped[i],0,64);n++;
    }
    return n;
}
static int inv_item_index(const aw_state_t *s,const char *id){
    int i;for(i=0;i<s->count[AW_ITEM];i++)if(!strcmp(s->values[AW_ITEM][i].id,id))return i;
    return -1;
}
int AW_InventoryDrop(aw_state_t *s,const aw_inventory_item_t *item,int32_t count,
                     const char *scene,const float position[3],float yaw){
    aw_dropped_item_t drop;int i,j,item_index;int32_t old;
    if(!s || !item || !position || !inv_id(item->id,64) || !inv_id(scene,16) ||
       !(item->flags&AW_INV_DROP) || !item->model[0] || count<1)return -1;
    old=AW_StateGet(s,AW_ITEM,item->id);if(count>old || s->inventory.next_serial==UINT32_MAX)return -1;
    for(j=0;j<3;j++)if(!(position[j]>=-32767 && position[j]<=32767))return -1;
    if(!(yaw>=-360 && yaw<=360))return -1;
    for(i=0;i<AW_INVENTORY_DROPS && s->inventory.dropped[i].count;i++);
    if(i==AW_INVENTORY_DROPS)return -1;
    memset(&drop,0,sizeof(drop));strcpy(drop.id,item->id);strcpy(drop.scene,scene);
    drop.count=count;drop.serial=s->inventory.next_serial+1;drop.yaw=yaw;
    item_index=inv_item_index(s,item->id);
    if(item_index>=0 && (s->inventory.condition_known&(1U<<item_index))){
        drop.condition_known=1;drop.condition=s->inventory.condition[item_index];
    }
    memcpy(drop.position,position,sizeof(drop.position));
    /* AW_ItemAdd is the only fallible mutation. All placement/admission checks
     * precede it; inventory and world ownership commit together afterwards. */
    if(!AW_ItemAdd(s,item->id,-count))return -1;
    if(AW_InventoryEquipped(s,item->id)>old-count)AW_InventoryUnequip(s,item->id);
    if(old==count && item_index>=0){s->inventory.condition_known&=~(1U<<item_index);s->inventory.condition[item_index]=0;}
    s->inventory.initialized=1;
    s->inventory.dropped[i]=drop;s->inventory.next_serial=drop.serial;return i;
}
int AW_InventoryPickup(aw_state_t *s,int index){
    aw_dropped_item_t *d;int item_index;int32_t old;float current,incoming;
    if(!s || index<0 || index>=AW_INVENTORY_DROPS)return 0;
    d=&s->inventory.dropped[index];
    if(d->count<1 || !d->serial || !inv_id(d->id,64))return 0;
    item_index=inv_item_index(s,d->id);old=AW_StateGet(s,AW_ITEM,d->id);
    current=item_index>=0 && (s->inventory.condition_known&(1U<<item_index))?s->inventory.condition[item_index]:1;
    incoming=d->condition_known?d->condition:1;
    if(!(incoming>=0 && incoming<=1) || (old>0 && current!=incoming))return 0;
    if(!AW_ItemAdd(s,d->id,d->count))return 0;
    item_index=inv_item_index(s,d->id);
    if(d->condition_known){s->inventory.condition_known|=1U<<item_index;s->inventory.condition[item_index]=incoming;}
    s->inventory.initialized=1;memset(d,0,sizeof(*d));return 1;
}

#ifndef AW_INVENTORY_RULES_ONLY
#define INV_ROW 512
static edict_t *drop_entity[AW_INVENTORY_DROPS];
static char drop_label[AW_INVENTORY_DROPS][96];
static model_t *inventory_world;
static char model_names[AW_INVENTORY_MODELS][64];
static int model_names_used;
static const char *drop_reason="Cannot place item here; kept.";
const char *AW_InventoryDropReason(void){return drop_reason;}
static unsigned long inv_u32(const byte *p){return (unsigned long)p[0]|((unsigned long)p[1]<<8)|((unsigned long)p[2]<<16)|((unsigned long)p[3]<<24);}
static int inv_field(char *out,const byte *raw,int n){
    int i;if(!memchr(raw,0,n))return 0;
    for(i=0;raw[i];i++)if(raw[i]<32)return 0;
    memcpy(out,raw,n);return 1;
}
int AW_InventoryRead(const char *id,aw_inventory_item_t *out){
    FILE *f=NULL;byte head[8],row[INV_ROW];int size,lo=0,hi,mid,cmp;long base;uint32_t bits;
    aw_inventory_item_t value;
    if(!out || !inv_id(id,64))return 0;
    size=COM_FOpenFile("inventory/items.awi",&f);if(!f)return 0;base=ftell(f);
    if(size<8 || fread(head,1,8,f)!=8 || memcmp(head,"AWI2",4))goto bad;
    hi=(int)inv_u32(head+4);if(hi<1 || hi>65536 || size!=8+hi*INV_ROW)goto bad;
    hi--;
    while(lo<=hi){
        mid=lo+(hi-lo)/2;
        if(fseek(f,base+8+(long)mid*INV_ROW,SEEK_SET) || fread(row,1,INV_ROW,f)!=INV_ROW)goto bad;
        if(!memchr(row,0,64))goto bad;
        cmp=AW_InventoryCompare((char *)row,id);
        if(cmp<0)lo=mid+1;else if(cmp>0)hi=mid-1;else{
            memset(&value,0,sizeof(value));
            if(!inv_field(value.id,row,64) || !inv_field(value.name,row+64,96) ||
               !inv_field(value.model,row+184,64) || !inv_field(value.icon,row+248,64) ||
               !inv_field(value.enchantment,row+312,64) || !inv_field(value.script,row+376,64))goto bad;
            value.category=(int)inv_u32(row+160);value.subtype=(int)(int32_t)inv_u32(row+164);
            value.value=(int)inv_u32(row+168);bits=(uint32_t)inv_u32(row+172);memcpy(&value.weight,&bits,4);
            value.slots=(uint32_t)inv_u32(row+176);value.flags=(uint32_t)inv_u32(row+180);
            value.weapon=(int)inv_u32(row+440);value.weapon_skill=(int)inv_u32(row+444);
            {int n;for(n=0;n<6;n++)value.damage[n]=(int)inv_u32(row+448+n*4);}
            bits=(uint32_t)inv_u32(row+472);memcpy(&value.reach,&bits,4);
            bits=(uint32_t)inv_u32(row+476);memcpy(&value.speed,&bits,4);
            bits=(uint32_t)inv_u32(row+480);memcpy(&value.health,&bits,4);
            bits=(uint32_t)inv_u32(row+484);memcpy(&value.armor,&bits,4);
            value.shield_class=(int)inv_u32(row+488);value.armor_skill_base=(int)inv_u32(row+492);
            if(value.category<1 || value.category>7 || value.value<0 ||
               !(value.weight>=0 && value.weight<=1000000) ||
               (value.slots&~((1U<<AW_INVENTORY_SLOTS)-1)) ||
               (value.flags&~31U) ||
               value.weapon<0 || value.weapon>9 ||
               value.weapon_skill<0 || value.weapon_skill>=27 ||
               !(value.reach>=0 && value.reach<=100) ||
               !(value.speed>=0 && value.speed<=100) ||
               !(value.health>=0 && value.health<=65535) ||
               !(value.armor>=0 && value.armor<=65535) ||
               value.shield_class<0 || value.shield_class>2 ||
               value.armor_skill_base<0 || value.armor_skill_base>10000)goto bad;
            {int n;for(n=0;n<6;n++)if(value.damage[n]<0 || value.damage[n]>255)goto bad;}
            if(value.damage[0]>value.damage[1] || value.damage[2]>value.damage[3] ||
               value.damage[4]>value.damage[5])goto bad;
            if(value.flags&AW_INV_EQUIP_SUPPORTED){
                if(!(value.flags&AW_INV_EQUIP) || !value.slots)goto bad;
                if(value.category==AW_INV_WEAPON &&
                   (value.slots!=(1U<<AW_SLOT_RIGHT) || value.weapon<1 ||
                    !(value.health>0 && value.reach>0 && value.speed>0)))goto bad;
                if(value.category==AW_INV_ARMOUR &&
                   (value.subtype!=8 || value.slots!=(1U<<AW_SLOT_LEFT) ||
                    !(value.health>0) || value.armor_skill_base<1))goto bad;
            }
            if((value.model[0] && (strncmp(value.model,"progs/inv/",10) || strstr(value.model,".."))) ||
               (value.icon[0] && (strncmp(value.icon,"gfx/inv/",8) || strstr(value.icon,".."))))goto bad;
            fclose(f);*out=value;return 1;
        }
        CDAudio_Update();S_ExtraUpdate();
    }
 bad: fclose(f);return 0;
}
int AW_InventoryBootstrap(void){
    FILE *f=NULL;byte head[8],row[72];int size,n,i,j,slot,amount;aw_state_t *next;
    if(aw_state.inventory.initialized)return 1;
    size=COM_FOpenFile("inventory/initial.awi",&f);if(!f)return 0;
    if(size<8 || fread(head,1,8,f)!=8 || memcmp(head,"AWST",4)){fclose(f);return 0;}
    n=(int)inv_u32(head+4);
    if(n<0 || n>AW_STATE_VALUES || size!=8+n*72){fclose(f);return 0;}
    next=(aw_state_t *)malloc(sizeof(*next));if(!next){fclose(f);return 0;}*next=aw_state;
    for(i=0;i<n;i++){
        aw_inventory_item_t item;
        if(fread(row,1,72,f)!=72 || !memchr(row,0,64))goto failed;
        amount=(int)inv_u32(row+64);slot=(int)(int32_t)inv_u32(row+68);
        if(amount<1 || amount>999 || slot< -1 || slot>=AW_INVENTORY_SLOTS ||
           !AW_InventoryRead((char *)row,&item))goto failed;
        j=AW_StateGet(next,AW_ITEM,item.id);
        /* Builds before inventory retained the original NPC-player outfit in
         * the body bake but had no mutable clothing ownership. Reconstruct that
         * known initial possession once; never grant quest loot/gold or regrant
         * an item after its first persistent drop. Existing counts win. */
        if(j<amount && !AW_ItemAdd(next,item.id,amount-j))goto failed;
        if(slot>=0 && !next->inventory.equipped[slot][0])strcpy(next->inventory.equipped[slot],item.id);
    }
    fclose(f);next->inventory.initialized=1;aw_state=*next;free(next);AW_CombatEquipmentChanged();return 1;
 failed:
    fclose(f);free(next);return 0;
}
int AW_InventoryEquippedItem(int slot,aw_inventory_item_t *out){
    static char ids[2][64];static aw_inventory_item_t values[2];int index;
    const char *id;
    if(!out || slot<0 || slot>=AW_INVENTORY_SLOTS)return 0;
    id=aw_state.inventory.equipped[slot];
    if(!id[0] || AW_StateGet(&aw_state,AW_ITEM,id)<1)return 0;
    index=slot==AW_SLOT_RIGHT?0:slot==AW_SLOT_LEFT?1:-1;
    if(index<0)return AW_InventoryRead(id,out);
    if(strcmp(ids[index],id)){
        ids[index][0]=0;
        if(!AW_InventoryRead(id,&values[index]))return 0;
        strcpy(ids[index],id);
    }
    if((values[index].flags&(AW_INV_EQUIP|AW_INV_EQUIP_SUPPORTED))!=(AW_INV_EQUIP|AW_INV_EQUIP_SUPPORTED) ||
       !(values[index].slots&(1U<<slot)))return 0;
    *out=values[index];return 1;
}
int AW_InventoryCanEquip(const aw_inventory_item_t *item){
    if(!item || (item->flags&(AW_INV_EQUIP|AW_INV_EQUIP_SUPPORTED))!=(AW_INV_EQUIP|AW_INV_EQUIP_SUPPORTED))return 0;
    if(item->category==AW_INV_WEAPON || (item->category==AW_INV_ARMOUR && item->subtype==8)){
        int index=inv_item_index(&aw_state,item->id);
        if(AW_StateGet(&aw_state,AW_ITEM,item->id)!=1 || item->health<=0 ||
           (index>=0 && (aw_state.inventory.condition_known&(1U<<index)) && aw_state.inventory.condition[index]<=0))return 0;
        return AW_ViewEquipmentReady();
    }
    return 1;
}
static int inv_block_item(char id[64],char model[64]){
    aw_inventory_item_t item;
    if(!AW_InventoryEquippedItem(AW_SLOT_LEFT,&item) || item.category!=AW_INV_ARMOUR ||
       item.subtype!=8 || !item.model[0])return 0;
    strcpy(id,item.id);strcpy(model,item.model);return 1;
}
static float inv_condition(const char *id){
    int index=inv_item_index(&aw_state,id);
    return index>=0 && (aw_state.inventory.condition_known&(1U<<index))?aw_state.inventory.condition[index]:1;
}
static void inv_store(const aw_fighter_t *sheet){
    int kind,index,slot;float current,maximum,value;aw_inventory_item_t item;
    for(kind=0;kind<2;kind++){
        slot=kind?AW_SLOT_LEFT:AW_SLOT_RIGHT;
        if(!AW_InventoryEquippedItem(slot,&item))continue;
        if((!kind && (item.category!=AW_INV_WEAPON || sheet->weapon!=item.weapon)) ||
           (kind && (item.category!=AW_INV_ARMOUR || item.subtype!=8 || !sheet->shield)))continue;
        index=inv_item_index(&aw_state,item.id);if(index<0)continue;
        current=kind?sheet->shield_health:sheet->weapon_health;
        maximum=kind?sheet->shield_health_max:sheet->weapon_health_max;
        if(!(maximum>0 && current>=0))continue;
        value=current/maximum;if(value>1)value=1;
        aw_state.inventory.condition_known|=1U<<index;aw_state.inventory.condition[index]=value;
    }
}
static void inv_combat(aw_fighter_t *sheet){
    aw_inventory_item_t item;int i;float base;
    if(!aw_state.inventory.initialized)return;
    /* Replace the held fields with actual owned inventory. No passive ring
     * spell is applied: CastWhenUsed is not a wearing effect. */
    sheet->weapon=0;sheet->weapon_skill=AW_SK_H2H;sheet->shield=0;
    sheet->reach=sheet->speed=sheet->weight=0;
    sheet->weapon_health=sheet->weapon_health_max=sheet->shield_health=sheet->shield_health_max=0;
    memset(sheet->damage,0,sizeof(sheet->damage));
    base=AW_CombatUnarmoredRating(&aw_combat_settings,sheet);sheet->armor=base;
    if(AW_InventoryEquippedItem(AW_SLOT_RIGHT,&item) && item.category==AW_INV_WEAPON &&
       item.weapon>=1 && item.weapon<=9 && item.weapon_skill>=0 && item.weapon_skill<27){
        sheet->weapon=(unsigned char)item.weapon;sheet->weapon_skill=(unsigned char)item.weapon_skill;
        for(i=0;i<6;i++)sheet->damage[i/2][i%2]=(unsigned char)item.damage[i];
        sheet->reach=item.reach;sheet->speed=item.speed;sheet->weight=item.weight;
        sheet->weapon_health_max=item.health;sheet->weapon_health=item.health*inv_condition(item.id);
    }
    if(AW_InventoryEquippedItem(AW_SLOT_LEFT,&item) && item.category==AW_INV_ARMOUR &&
       item.subtype==8 && item.shield_class>=0 && item.shield_class<=2 && item.armor_skill_base>0){
        static const int skills[3]={AW_SK_LIGHT,AW_SK_MEDIUM,AW_SK_HEAVY};
        sheet->shield=1;sheet->shield_class=(unsigned char)item.shield_class;
        sheet->shield_health_max=item.health;sheet->shield_health=item.health*inv_condition(item.id);
        sheet->armor+=.1f*(item.armor*sheet->skills[skills[item.shield_class]]/item.armor_skill_base-base);
    }
}
void AW_InventoryGrantCommand(void){
    aw_inventory_item_t item;int n;
    if(cmd_source!=src_command || !sv.active || svs.maxclients!=1 || Cmd_Argc()!=4 || Q_strcasecmp(Cmd_Argv(1),"grant"))return;
    n=Q_atoi(Cmd_Argv(3));
    if(n<1 || n>999 || !AW_InventoryRead(Cmd_Argv(2),&item) || !AW_ItemAdd(&aw_state,item.id,n)){
        Con_Printf("Diagnostic inventory grant refused.\n");return;
    }
    Con_Printf("DIAGNOSTIC inventory grant: %s +%d, now %ld.\n",item.id,n,(long)AW_StateGet(&aw_state,AW_ITEM,item.id));
}
void AW_InventoryInit(void){
    aw_combat_equipment=inv_combat;aw_combat_equipment_store=inv_store;aw_hand_block_item=inv_block_item;
}
static void inv_level(void){
    if(inventory_world!=sv.worldmodel){
        inventory_world=sv.worldmodel;model_names_used=0;
        memset(drop_entity,0,sizeof(drop_entity));memset(drop_label,0,sizeof(drop_label));
    }
}
/* Inventory is local single-player only. AmiQuake's alias loader/cache and
 * existing precache tables are reused; the local client gets the identical
 * newly admitted model slot before its first entity update. No remote protocol
 * or late server-only model index is invented. */
static int inv_model(const aw_inventory_item_t *item){
    int i;model_t *m;
    inv_level();if(!item->model[0] || svs.maxclients!=1)return 0;
    for(i=1;i<MAX_MODELS && sv.model_precache[i];i++)if(!strcmp(sv.model_precache[i],item->model))return i;
    if(i>=MAX_MODELS){drop_reason="World model table full; kept.";return 0;}
    if(model_names_used>=AW_INVENTORY_MODELS){drop_reason="Scene item model limit (16); kept.";return 0;}
    m=Mod_ForName((char *)item->model,false);
    if(!m || m->type!=mod_alias || !Cache_Check(&m->cache)){
        drop_reason="Item model unavailable; kept.";return 0;
    }
    strcpy(model_names[model_names_used],item->model);
    sv.model_precache[i]=model_names[model_names_used++];sv.models[i]=m;
    if(cls.state==ca_connected)cl.model_precache[i]=m;
    return i;
}
static int inv_edict_available(void){
    int i;edict_t *e;
    for(i=svs.maxclients+1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);
        if(e->free && (e->freetime<2 || sv.time-e->freetime>.5))return 1;
    }
    return sv.num_edicts<MAX_EDICTS;
}
static void inv_entity(edict_t *e,int index,int model){
    aw_dropped_item_t *d=&aw_state.inventory.dropped[index];
    e->v.classname=ED_NewString("aw_inventory_drop")-pr_strings;
    e->v.model=sv.model_precache[model]-pr_strings;e->v.modelindex=model;
    e->v.movetype=MOVETYPE_NONE;e->v.solid=SOLID_NOT;
    VectorCopy(d->position,e->v.origin);VectorCopy(d->position,e->v.oldorigin);
    e->v.angles[0]=e->v.angles[2]=0;e->v.angles[1]=d->yaw;
    drop_entity[index]=e;SV_LinkEdict(e,false);
}
void AW_InventorySpawn(void){
    int i,model;aw_inventory_item_t item;
    /* Called after a fresh server/map restore. Old edict addresses can now
     * belong to unrelated actors, even when the cached worldmodel is equal. */
    inventory_world=sv.worldmodel;model_names_used=0;
    memset(drop_entity,0,sizeof(drop_entity));memset(drop_label,0,sizeof(drop_label));
    for(i=0;i<AW_INVENTORY_DROPS;i++){
        aw_dropped_item_t *d=&aw_state.inventory.dropped[i];
        if(d->count<1 || strcmp(d->scene,sv.name))continue;
        if(!AW_InventoryRead(d->id,&item) || !(model=inv_model(&item)) || !inv_edict_available()){
            Con_Printf("Inventory: dropped item %s retained in state; model/entity unavailable.\n",d->id);continue;
        }
        strcpy(drop_label[i],item.name);inv_entity(ED_Alloc(),i,model);
    }
}
/* A placement-only conservative region query over AmiQuake's existing hull0
 * BSP planes. Every leaf reached by the box must have the requested contents.
 * An enclosing swept box may reject a clear diagonal path, but cannot accept a
 * thin solid missed by point/corner samples. Bounded stack/work; never per frame.
 * SV_Move itself remains unchanged and receives point traces only. */
static int inv_hull_region(model_t *model,const float low[3],const float high[3],int wanted){
    hull_t *h;dclipnode_t *node;mplane_t *plane;
    int pending[128],top=1,work=8192,n,k;float near,far,a,b;
    if(!model || model->type!=mod_brush)return 0;
    h=&model->hulls[0];
    if(!h->clipnodes || !h->planes || h->firstclipnode<0 || h->lastclipnode<h->firstclipnode)return 0;
    pending[0]=h->firstclipnode;
    while(top){
        n=pending[--top];if(--work<0)return 0;
        if(n<0){if(n!=wanted)return 0;continue;}
        if(n<h->firstclipnode || n>h->lastclipnode)return 0;
        node=&h->clipnodes[n];
        if(node->planenum<0 || node->planenum>=model->numplanes)return 0;
        plane=&h->planes[node->planenum];near=far=-plane->dist;
        for(k=0;k<3;k++){
            a=plane->normal[k]*low[k];b=plane->normal[k]*high[k];
            near+=a<b?a:b;far+=a>b?a:b;
        }
        if(!(near<=far))return 0;
        if(top>125)return 0;
        if(near>=0)pending[top++]=node->children[0];
        else if(far<0)pending[top++]=node->children[1];
        else{pending[top++]=node->children[0];pending[top++]=node->children[1];}
    }
    return 1;
}
static void inv_local_bounds(edict_t *entity,const float low[3],const float high[3],float local_low[3],float local_high[3]){
    vec3_t forward,right,up,point,delta;int corner,k;
    AngleVectors(entity->v.angles,forward,right,up);
    for(k=0;k<3;k++){local_low[k]=32768;local_high[k]=-32768;}
    for(corner=0;corner<8;corner++){
        for(k=0;k<3;k++)point[k]=(corner&(1<<k))?high[k]:low[k];
        VectorSubtract(point,entity->v.origin,delta);
        point[0]=DotProduct(delta,forward);point[1]=-DotProduct(delta,right);point[2]=DotProduct(delta,up);
        for(k=0;k<3;k++){if(point[k]<local_low[k])local_low[k]=point[k];if(point[k]>local_high[k])local_high[k]=point[k];}
    }
}
static int inv_space_clear(const float low[3],const float high[3],edict_t *player){
    int i,k,index,overlap;edict_t *e;vec3_t local_low,local_high;
    if(!inv_hull_region(sv.worldmodel,low,high,CONTENTS_EMPTY))return 0;
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);if(e->free || e==player || e->v.solid==SOLID_NOT || e->v.solid==SOLID_TRIGGER)continue;
        if(e->v.solid==SOLID_BSP){
            index=(int)e->v.modelindex;if(index<=0 || index>=MAX_MODELS || !sv.models[index])return 0;
            inv_local_bounds(e,low,high,local_low,local_high);
            if(!inv_hull_region(sv.models[index],local_low,local_high,CONTENTS_EMPTY))return 0;
        }else{
            overlap=1;
            for(k=0;k<3;k++)if(high[k]<=e->v.origin[k]+e->v.mins[k] || low[k]>=e->v.origin[k]+e->v.maxs[k])overlap=0;
            if(overlap)return 0;
        }
    }
    return 1;
}
static int inv_support(const float low[3],const float high[3]){
    int i,index;edict_t *e;vec3_t local_low,local_high;
    if(inv_hull_region(sv.worldmodel,low,high,CONTENTS_SOLID))return 1;
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);if(e->free || e->v.solid!=SOLID_BSP)continue;
        index=(int)e->v.modelindex;if(index<=0 || index>=MAX_MODELS || !sv.models[index])continue;
        inv_local_bounds(e,low,high,local_low,local_high);
        if(inv_hull_region(sv.models[index],local_low,local_high,CONTENTS_SOLID))return 1;
    }
    return 0;
}
int AW_InventoryDropHere(const aw_inventory_item_t *item,int32_t count){
    edict_t *p,*e;trace_t tr;vec3_t forward,right,up,eye,start,end,position,mins,maxs,low,high,swept_low,swept_high,point;
    int model,index,j,corner;float yaw;
    drop_reason="Cannot drop this item here; kept.";
    if(!item || !(item->flags&AW_INV_DROP) || !sv.active || svs.maxclients!=1 ||
       !svs.clients || !(p=svs.clients[0].edict) || p->v.health<=0 ||
       p->v.movetype!=MOVETYPE_WALK || p->v.waterlevel>=2)return 0;
    /* Point traces include streamed/scenery/barrier collision, but the full
     * footprint query below currently certifies only BSP world/brush volumes.
     * Refuse that unsupported context before model/entity/ownership admission. */
    if(Chim_Active() || AW_SceneryCount()>0 || AW_StoryRestricted()){
        drop_reason="Cannot place items in this area yet; kept.";return 0;
    }
    for(j=0;j<AW_INVENTORY_DROPS && aw_state.inventory.dropped[j].count;j++);
    if(j==AW_INVENTORY_DROPS){drop_reason="Ground item limit (32); kept.";return 0;}
    if(!inv_edict_available()){drop_reason="No available world entity; kept.";return 0;}
    model=inv_model(item);if(!model)return 0;
    VectorCopy(p->v.origin,eye);eye[2]+=p->v.view_ofs[2];
    AngleVectors(p->v.v_angle,forward,right,up);
    for(j=0;j<3;j++)start[j]=eye[j]+forward[j]*24;
    start[2]=eye[2];
    /* The forward start must not teleport the drop beyond an intervening wall. */
    tr=SV_Move(eye,vec3_origin,vec3_origin,start,MOVE_NORMAL,p);
    if(tr.startsolid || tr.allsolid || tr.fraction<1){drop_reason="Drop path obstructed; kept.";return 0;}
    VectorCopy(start,end);end[2]-=256;
    tr=SV_Move(start,vec3_origin,vec3_origin,end,MOVE_NORMAL,p);
    if(tr.startsolid || tr.allsolid || tr.fraction>=1 || tr.plane.normal[2]<.69f ||
       SV_PointContents(tr.endpos)<=CONTENTS_WATER){drop_reason="No dry floor for item; kept.";return 0;}
    yaw=p->v.v_angle[1];point[0]=point[2]=0;point[1]=yaw;AngleVectors(point,forward,right,up);
    for(j=0;j<3;j++){mins[j]=32768;maxs[j]=-32768;}
    for(corner=0;corner<8;corner++){
        for(j=0;j<3;j++){
            float value=(corner&(1<<j))?sv.models[model]->maxs[j]:sv.models[model]->mins[j];
            if(!(value>=-512 && value<=512))return 0;
            start[j]=value;
        }
        for(j=0;j<3;j++){
            float value=start[0]*forward[j]-start[1]*right[j]+start[2]*up[j];
            if(value<mins[j])mins[j]=value;
            if(value>maxs[j])maxs[j]=value;
        }
    }
    VectorCopy(tr.endpos,position);position[2]-=mins[2];position[2]+=.0625f;
    for(j=0;j<3;j++){
        low[j]=position[j]+mins[j];high[j]=position[j]+maxs[j];
        swept_low[j]=low[j]<eye[j]+mins[j]?low[j]:eye[j]+mins[j];
        swept_high[j]=high[j]>eye[j]+maxs[j]?high[j]:eye[j]+maxs[j];
    }
    drop_reason="Item path or footprint obstructed; kept.";
    if(!inv_space_clear(swept_low,swept_high,p) || !inv_space_clear(low,high,p))return 0;
    /* Require the whole footprint's shallow support slab inside one dry solid
     * world/brush volume. This deliberately refuses bridging holes and ledges. */
    high[2]=low[2]-.125f;low[2]-=.25f;
    drop_reason="Item footprint unsupported; kept.";
    if(!inv_support(low,high))return 0;
    AW_CombatEquipmentStore();
    e=ED_Alloc();index=AW_InventoryDrop(&aw_state,item,count,sv.name,position,yaw);
    if(index<0){ED_Free(e);drop_reason="Inventory transfer refused; kept.";return 0;}
    strcpy(drop_label[index],item->name);inv_entity(e,index,model);AW_CombatEquipmentChanged();
    AW_UIPickupNotice(item->name,2);return 1;
}

static int inv_target(void){
    int i,best=-1;float distance=50,along,side;edict_t *p;vec3_t f,r,u,eye,delta;trace_t tr;
    if(!sv.active || svs.maxclients!=1 || !svs.clients || !(p=svs.clients[0].edict))return -1;
    inv_level();VectorCopy(p->v.origin,eye);eye[2]+=p->v.view_ofs[2];
    AngleVectors(p->v.v_angle,f,r,u);
    for(i=0;i<AW_INVENTORY_DROPS;i++)if(drop_entity[i] && !drop_entity[i]->free && aw_state.inventory.dropped[i].count>0){
        VectorSubtract(drop_entity[i]->v.origin,eye,delta);along=DotProduct(delta,f);
        if(along<0 || along>distance)continue;
        side=DotProduct(delta,delta)-along*along;if(side>64)continue;
        tr=SV_Move(eye,vec3_origin,vec3_origin,drop_entity[i]->v.origin,MOVE_NOMONSTERS,p);
        if(tr.fraction<1)continue;
        distance=along;best=i;
    }
    return best;
}
const char *AW_InventoryHint(void){int i=inv_target();return i<0?NULL:drop_label[i];}
int AW_InventoryUse(void){
    int i=inv_target();if(i<0)return 0;
    if(!AW_InventoryPickup(&aw_state,i)){AW_UISubtitle(drop_label[i],"Cannot collect: inventory capacity.",3);return 1;}
    AW_UIPickupNotice(drop_label[i],3);AW_CombatEquipmentChanged();ED_Free(drop_entity[i]);drop_entity[i]=NULL;return 1;
}
#endif
