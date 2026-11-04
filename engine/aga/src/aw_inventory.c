/* SPDX-License-Identifier: GPL-2.0-or-later
 * Original item identities and bounded persistent equipment/drop transactions.
 * UI selection never fabricates inventory and never directly deletes an item. */
#ifndef AW_INVENTORY_RULES_ONLY
#include "quakedef.h"
#include "aw_links.h"
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
#include "aw_tryalloc.h"
#include "aw_actorstate.h"
/* aw_world.h (its other prototypes need the full server headers, which the native tests replace) */
int AW_WorldToSource(const char *,const float *,float *);
int AW_SourceToWorld(const char *,const float *,float *);
/* PLACED-ITEMS-OUTDOORS-FIRST-FRAME-59: a CHIM frame map (Seyda Neen, the towns, the regions) has no entry in the
 * open-world region table, so the region table alone said no there and its focus rows and placed items were never
 * read outdoors. Since CHIM-FRAME-SOURCE-CONVERSION-59 AW_WorldToSource / AW_SourceToWorld themselves ask the loaded
 * CHIM frame after the region table (aw_world.c), for every caller; this file's own frame hooks went into that. */
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
float AW_LightBurn(const aw_inventory_item_t *item,float remaining,float seconds){
    if(!item || !(item->flags&AW_INV_LIGHT))return 0;
    if(item->light_time==AW_LIGHT_INFINITE)return AW_LIGHT_INFINITE;
    if(!(remaining>0))return 0;
    if(!(seconds>0))return remaining;
    remaining-=seconds;return remaining>0?remaining:0;
}
int AW_DebugTorchGrant(aw_state_t *s,int enabled){
    aw_state_t next;
    if(!s || !enabled || AW_StateGet(s,AW_GLOBAL,AW_DEBUG_TORCH_GRANTED))return 0;
    /* One transaction: the item and the "given" mark together, or nothing. The mark is a saved
     * global, so a reload or a second census exit never gives it again. */
    next=*s;
    if(!AW_ItemAdd(&next,AW_DEBUG_TORCH_ID,1) || !AW_StateSet(&next,AW_GLOBAL,AW_DEBUG_TORCH_GRANTED,1))return 0;
    *s=next;return 1;
}
/* An armour type's slot (OpenMW mwclass/armor.cpp getEquipmentSlots), -1 for an unknown type. */
int AW_InventoryArmourSlot(int type){
    static const signed char slot[11]={AW_SLOT_HELMET,AW_SLOT_CUIRASS,AW_SLOT_LPAULDRON,AW_SLOT_RPAULDRON,AW_SLOT_GREAVES,
        AW_SLOT_BOOTS,AW_SLOT_LGAUNTLET,AW_SLOT_RGAUNTLET,AW_SLOT_LEFT,AW_SLOT_LGAUNTLET,AW_SLOT_RGAUNTLET};
    return type>=0 && type<11?slot[type]:-1;
}
/* The slot a new item clears (OpenMW mwclass/weapon.cpp and armor.cpp canBeEquipped with mwworld/actionequip.cpp):
 * a two-handed weapon takes the shield off the left hand; a shield takes a two-handed weapon out of the right hand.
 * RIGHT and LEFT: what those hands hold (NULL empty). -1 when nothing has to go. */
int AW_InventoryEquipConflict(const aw_inventory_item_t *item,const aw_inventory_item_t *right,
                              const aw_inventory_item_t *left){
    if(!item)return -1;
    if(item->category==AW_INV_WEAPON && item->weapon>0 && AW_INV_TWO_HANDED(item->weapon) &&
       left && left->category==AW_INV_ARMOUR && left->subtype==8)return AW_SLOT_LEFT;
    if(item->category==AW_INV_ARMOUR && item->subtype==8 && right && right->category==AW_INV_WEAPON &&
       right->weapon>0 && AW_INV_TWO_HANDED(right->weapon))return AW_SLOT_RIGHT;
    return -1;
}
/* The armour slot a blow can land on (aw_combat.h AW_CombatArmorHitSlot order: cuirass, helmet, greaves, boots, left
 * and right pauldron, left and right gauntlet, shield) of an equipment slot, -1 for the others. */
int AW_InventoryHitSlot(int slot){
    switch(slot){
    case AW_SLOT_CUIRASS:return 0;case AW_SLOT_HELMET:return 1;case AW_SLOT_GREAVES:return 2;case AW_SLOT_BOOTS:return 3;
    case AW_SLOT_LPAULDRON:return 4;case AW_SLOT_RPAULDRON:return 5;case AW_SLOT_LGAUNTLET:return 6;
    case AW_SLOT_RGAUNTLET:return 7;case AW_SLOT_LEFT:return 8;
    }
    return -1;
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
int (*aw_inventory_hand_item)(int slot,aw_inventory_item_t *out);
static int equip_into(aw_state_t *s,const aw_inventory_item_t *item);
int AW_InventoryEquip(aw_state_t *s,const aw_inventory_item_t *item){
    aw_inventory_item_t right,left;int clear=-1;
    if(!s || !item || !inv_id(item->id,64))return 0;
    if(AW_InventoryEquipped(s,item->id))return 1;
    if(aw_inventory_hand_item)
        clear=AW_InventoryEquipConflict(item,aw_inventory_hand_item(AW_SLOT_RIGHT,&right)?&right:NULL,
                                        aw_inventory_hand_item(AW_SLOT_LEFT,&left)?&left:NULL);
    if(!equip_into(s,item))return 0;
    /* actionequip.cpp: the new item is worn, then the hand it conflicts with is emptied (back to the pack) */
    if(clear>=0 && strcmp(s->inventory.equipped[clear],item->id))memset(s->inventory.equipped[clear],0,64);
    return 1;
}
static int equip_into(aw_state_t *s,const aw_inventory_item_t *item){
    int i,first=-1;
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
    /* Placed items carry condition but no charge yet: never refill a spent item by dropping it. */
    item_index=inv_item_index(s,item->id);
    if(count==old && item_index>=0 && (s->magic.charge_known&(1U<<item_index)))return -1;
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
int AW_MagicSelectable(const aw_inventory_item_t *item){
    return item && (item->enchant_kind==AW_ENCH_ONCE || item->enchant_kind==AW_ENCH_USED) && item->charge_max>0;
}
int AW_MagicSelect(aw_state_t *s,const aw_inventory_item_t *item){
    if(!s || !AW_MagicSelectable(item) || !inv_id(item->id,64) || AW_StateGet(s,AW_ITEM,item->id)<1)return 0;
    memset(s->magic.selected,0,64);strcpy(s->magic.selected,item->id);return 1;
}
void AW_MagicClear(aw_state_t *s){if(s)memset(s->magic.selected,0,64);}
float AW_MagicCharge(const aw_state_t *s,const aw_inventory_item_t *item){
    int index;
    if(!s || !item || item->enchant_kind==AW_ENCH_NONE || !(item->charge_max>0))return 0;
    index=inv_item_index(s,item->id);
    if(index>=0 && (s->magic.charge_known&(1U<<index)))return s->magic.charge[index];
    return item->charge_max;
}
int AW_MagicSetCharge(aw_state_t *s,const aw_inventory_item_t *item,float value){
    int index;
    if(!s || !item || item->enchant_kind==AW_ENCH_NONE || !(item->charge_max>0) ||
       !(value>=0) || AW_StateGet(s,AW_ITEM,item->id)<1)return 0;
    index=inv_item_index(s,item->id);if(index<0)return 0;
    if(value>=item->charge_max){s->magic.charge_known&=~(1U<<index);s->magic.charge[index]=0;}
    else{s->magic.charge_known|=1U<<index;s->magic.charge[index]=value;}
    return 1;
}
/* MWMechanics::rechargeItem: min(charge + rate * seconds, maximum); full stays full. */
int AW_MagicRecharge(aw_state_t *s,const aw_inventory_item_t *item,float seconds,float rate){
    int index;
    if(!s || !item || !(seconds>0) || !(rate>=0) ||
       (item->enchant_kind!=AW_ENCH_USED && item->enchant_kind!=AW_ENCH_STRIKES))return 0;
    index=inv_item_index(s,item->id);
    if(index<0 || !(s->magic.charge_known&(1U<<index)))return 0;
    return AW_MagicSetCharge(s,item,s->magic.charge[index]+rate*seconds);
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
/* dbg give weapons (DBG-GIVE-WEAPONS-59): the builder's weapon kit table (aw_inventory.h). Text the builder wrote,
 * checked field by field; the engine formats nothing of its own, it only lines the fields up for the console. */
static int kit_field(char *out,const char *s,int n,int size,int spaces){
    int i;unsigned char c;
    if(n<1 || n>=size)return 0;
    for(i=0;i<n;i++){
        c=(unsigned char)s[i];
        if(c<32 || c>126 || c=='|' || c=='"' || (!spaces && c==' '))return 0;
    }
    memcpy(out,s,n);out[n]=0;return 1;
}
int AW_WeaponKitParse(const char *text,int length,aw_kit_row_t *rows,int max){
    const char *p,*end,*line,*eol,*q,*f[15];int k,i,j,n=0,header=0,len[15];aw_kit_row_t *r;
    if(!text || length<6 || !rows || max<1)return -1;
    for(p=text,end=text+length;p<end;){
        line=p;eol=(const char *)memchr(p,'\n',end-p);if(!eol)eol=end;
        p=eol<end?eol+1:end;k=(int)(eol-line);if(k>0 && line[k-1]=='\r')k--;
        if(!header){if(k!=6 || memcmp(line,"AWKIT1",6))return -1;header=1;continue;}
        if(!k || line[0]=='#')continue;
        if(n>=max)return -1;
        f[0]=line;i=1;
        for(q=line;q<line+k;q++)if(*q=='|'){if(i>=15)return -1;f[i++]=q+1;}
        if(i!=15)return -1;
        for(j=0;j<15;j++)len[j]=(int)((j<14?f[j+1]-1:line+k)-f[j]);
        r=&rows[n];memset(r,0,sizeof(*r));
        if(!kit_field(r->id,f[0],len[0],64,1) || !kit_field(r->type,f[3],len[3],sizeof(r->type),1) ||
           !kit_field(r->name,f[4],len[4],sizeof(r->name),1))return -1;
        for(j=0;r->id[j];j++)if(r->id[j]>='A' && r->id[j]<='Z')return -1;   /* catalogue ids are lower case */
        if(len[1]<1 || len[1]>3)return -1;
        for(j=0;j<len[1];j++){if(f[1][j]<'0' || f[1][j]>'9')return -1;r->count=r->count*10+f[1][j]-'0';}
        if(r->count<1 || len[2]!=1 || !strchr("WRTAS",f[2][0]))return -1;
        r->kind=f[2][0];
        for(j=0;j<AW_WEAPON_KIT_STATS;j++)if(!kit_field(r->stat[j],f[5+j],len[5+j],12,0))return -1;
        for(j=0;j<n;j++)if(!strcmp(rows[j].id,r->id))return -1;
        n++;
    }
    return header && n>0?n:-1;
}
/* how many new item kinds (AW_ITEM entries) the kit needs; -1 when a count would overflow */
int AW_WeaponKitNeeds(const aw_state_t *s,const aw_kit_row_t *rows,int n){
    int i,need=0;
    if(!s || !rows || n<1)return -1;
    for(i=0;i<n;i++){
        if(AW_StateGet(s,AW_ITEM,rows[i].id)>INT32_MAX-rows[i].count)return -1;
        if(inv_item_index(s,rows[i].id)<0)need++;
    }
    return need;
}
/* The whole kit or nothing: the room is checked first (AW_STATE_VALUES item kinds), then every row is added as
 * dbg inventory grant adds one; saved like any grant (the AW_ITEM counts are the save's). */
int AW_WeaponKitGrant(aw_state_t *s,const aw_kit_row_t *rows,int n){
    int i,need=AW_WeaponKitNeeds(s,rows,n);
    if(need<0 || need>AW_STATE_VALUES-s->count[AW_ITEM])return 0;
    for(i=0;i<n;i++)if(!AW_ItemAdd(s,rows[i].id,rows[i].count)){
        while(--i>=0)AW_ItemAdd(s,rows[i].id,-rows[i].count);   /* not reached after the room check */
        return 0;
    }
    return 1;
}
/* one "label value" token onto the row's lines: a new line (indented two) when it would pass WIDTH */
static int kit_token(char *out,int size,int *used,int *column,int width,const char *a,const char *b){
    int na=(int)strlen(a),nb=b?(int)strlen(b):0,n=na+(nb?nb+1:0),gap=*column>0;
    if(gap && *column+1+n>width){
        if(*used+3>=size)return 0;
        out[(*used)++]='\n';out[(*used)++]=' ';out[(*used)++]=' ';*column=2;gap=0;
    }
    if(*used+gap+n>=size)return 0;
    if(gap)out[(*used)++]=' ';
    memcpy(out+*used,a,na);*used+=na;
    if(nb){out[(*used)++]=' ';memcpy(out+*used,b,nb);*used+=nb;}
    *column+=gap+n;out[*used]=0;return 1;
}
int AW_WeaponKitLines(const aw_kit_row_t *row,int equippable,int width,char *out,int size){
    static const char *labels[AW_WEAPON_KIT_STATS]={"chop","slash","thrust","speed","reach","weight","value","health",
        "ench","armour"};
    char head[64],type[28],id[68];int used=0,column=0,j,lines=1;
    if(!row || !out || size<2)return -1;
    if(width<20)width=20;
    out[0]=0;strcpy(head,row->name);
    if(row->count>1){
        int n=(int)strlen(head),c=row->count;char digits[4];int d=0;
        do{digits[d++]=(char)('0'+c%10);c/=10;}while(c && d<3);
        head[n++]=' ';head[n++]='x';while(d)head[n++]=digits[--d];head[n]=0;
    }
    strcpy(type,"(");strcat(type,row->type);strcat(type,")");
    strcpy(id,"\"");strcat(id,row->id);strcat(id,"\"");
    if(!kit_token(out,size,&used,&column,width,head,NULL) || !kit_token(out,size,&used,&column,width,type,NULL))return -1;
    for(j=0;j<AW_WEAPON_KIT_STATS;j++){
        if(!strcmp(row->stat[j],"-"))continue;
        if(!kit_token(out,size,&used,&column,width,!j && row->kind!='W'?"damage":labels[j],row->stat[j]))return -1;
    }
    if(!kit_token(out,size,&used,&column,width,equippable?"equip":"carry",id))return -1;
    for(j=0;out[j];j++)if(out[j]=='\n')lines++;
    return lines;
}

#ifndef AW_INVENTORY_RULES_ONLY
#include "aw_ledger.h"
#include "aw_maps.h"
#define INV_ROW 512
extern int com_fopen_buffer;   /* aw_fopenbuf.c: the buffer of the next COM_FOpenFile (0: 16 KiB) */
static edict_t *drop_entity[AW_INVENTORY_DROPS];
static char drop_label[AW_INVENTORY_DROPS][96];
static model_t *inventory_world;
static char model_names[AW_INVENTORY_MODELS][64];
static int model_names_used;
static const char *drop_reason="Cannot place item here; kept.";
const char *AW_InventoryDropReason(void){return drop_reason;}
/* CELL-CHANGES-59: the drops of the world change list this map shows (aw_ledger_drops.c keeps the rows, map-wide,
 * with no ceiling; these edicts are this map's: made at every map and again when the outdoor cell is read again).
 * One map shows at most AW_INVENTORY_DROPS of them at once: the edicts every map keeps for drops
 * (tools/map_engine_limits.py runtime_edicts). */
typedef struct {uint32_t key;edict_t *e;char label[96];} map_drop_t;
#define MAP_DROP_BYTES 104
AW_RESIDENT_GROWS("drops shown on the loaded map (CELL-CHANGES-59)",AW_INVENTORY_DROPS,MAP_DROP_BYTES);
static map_drop_t *map_drops;static int map_drop_count;
/* room for one more entry; 0 when the map's drop edicts are used up or memory says no */
static int map_drop_room(void){
    if(map_drop_count>=AW_INVENTORY_DROPS)return 0;
    if(!map_drops && !(map_drops=(map_drop_t *)AW_TryMalloc(AW_INVENTORY_DROPS*sizeof(map_drop_t))))return 0;
    return 1;
}
static void map_drop_add(uint32_t key,edict_t *e,const char *label){
    map_drop_t *d=&map_drops[map_drop_count++];
    d->key=key;d->e=e;Q_strcpy_bounded(d->label,label,sizeof(d->label));
}
static void ledger_drop_entity(edict_t *e,int model,const float *at,float yaw){
    e->v.classname=ED_NewString("aw_inventory_drop")-pr_strings;
    e->v.model=sv.model_precache[model]-pr_strings;e->v.modelindex=model;
    e->v.movetype=MOVETYPE_NONE;e->v.solid=SOLID_NOT;
    VectorCopy(at,e->v.origin);VectorCopy(at,e->v.oldorigin);
    e->v.angles[0]=e->v.angles[2]=0;e->v.angles[1]=yaw;
    SV_LinkEdict(e,false);
}
static unsigned long inv_u32(const byte *p){return (unsigned long)p[0]|((unsigned long)p[1]<<8)|((unsigned long)p[2]<<16)|((unsigned long)p[3]<<24);}
static int inv_field(char *out,const byte *raw,int n){
    int i;if(!memchr(raw,0,n))return 0;
    for(i=0;raw[i];i++)if(raw[i]<32)return 0;
    memcpy(out,raw,n);return 1;
}
/* the made items' store (aw_actorstate.c AW_MadeItemAt), set by the script host when it starts; none in the tools' tests */
const aw_made_item_t *(*aw_inventory_made_item)(int index);
static FILE *inv_batch_file;static int inv_batch_size;static long inv_batch_base,inv_batch_wanted;   /* AW_InventoryBatchBegin */
/* One items.awi row (512 bytes) into OUT; 0 when it is not a row this engine reads. Shared by the file's search and the
 * area tables' item records (AREA-TABLES-59, area_item). */
static int inv_parse_row(const byte *row,aw_inventory_item_t *out){
    aw_inventory_item_t value;uint32_t bits;
            if(!memchr(row,0,64))return 0;
            memset(&value,0,sizeof(value));
            if(!inv_field(value.id,row,64) || !inv_field(value.name,row+64,96) ||
               !inv_field(value.model,row+184,64) || !inv_field(value.icon,row+248,64) ||
               !inv_field(value.enchantment,row+312,64) || !inv_field(value.script,row+376,64))return 0;
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
            value.enchant_kind=row[496];bits=(uint32_t)inv_u32(row+500);memcpy(&value.charge_max,&bits,4);
            if(value.enchant_kind>AW_ENCH_CONSTANT || row[497] || row[498] || row[499] ||
               !(value.charge_max>=0 && value.charge_max<=1000000) ||
               (!value.enchant_kind && value.charge_max!=0) || (value.enchant_kind && !value.enchantment[0]))return 0;
            if(value.flags&AW_INV_LIGHT){
                /* A carried light: burn time (AW_LIGHT_INFINITE or 1..), colour, radius in subtype. */
                value.light_time=(int)(int32_t)inv_u32(row+504);value.light_radius=value.subtype;
                memcpy(value.light_colour,row+508,3);
                if(row[511] || value.category!=AW_INV_MISC || value.light_radius<1 || value.light_radius>65535 ||
                   (value.light_time!=AW_LIGHT_INFINITE && (value.light_time<1 || value.light_time>1000000)))return 0;
            }else{int n;value.enchant_capacity=row[504]|(row[505]<<8);   /* the record's enchantment points */
                  for(n=506;n<512;n++)if(row[n])return 0;}
            if(value.category<1 || value.category>7 || value.value<0 ||
               !(value.weight>=0 && value.weight<=1000000) ||
               (value.slots&~((1U<<AW_INVENTORY_SLOTS)-1)) ||
               (value.flags&~63U) ||
               value.weapon<0 || value.weapon>9 ||
               value.weapon_skill<0 || value.weapon_skill>=27 ||
               !(value.reach>=0 && value.reach<=100) ||
               !(value.speed>=0 && value.speed<=100) ||
               !(value.health>=0 && value.health<=65535) ||
               !(value.armor>=0 && value.armor<=65535) ||
               value.shield_class<0 || value.shield_class>2 ||
               value.armor_skill_base<0 || value.armor_skill_base>10000)return 0;
            {int n;for(n=0;n<6;n++)if(value.damage[n]<0 || value.damage[n]>255)return 0;}
            if(value.damage[0]>value.damage[1] || value.damage[2]>value.damage[3] ||
               value.damage[4]>value.damage[5])return 0;
            if(value.flags&AW_INV_EQUIP_SUPPORTED){
                if(!(value.flags&AW_INV_EQUIP) || !value.slots)return 0;
                if(value.category==AW_INV_WEAPON &&
                   (value.slots!=(1U<<AW_SLOT_RIGHT) || value.weapon<1 ||
                    !(value.health>0 && value.reach>0 && value.speed>0)))return 0;
                if(value.category==AW_INV_ARMOUR &&
                   (AW_InventoryArmourSlot(value.subtype)<0 || value.slots!=(1U<<AW_InventoryArmourSlot(value.subtype)) ||
                    !(value.health>0) || value.armor_skill_base<1))return 0;
            }
            /* a world model from the item model table (progs/items/, ITEM-WORLD-MODELS-58) or a tool run's own (progs/inv/) */
            if((value.model[0] && ((strncmp(value.model,"progs/inv/",10) && strncmp(value.model,"progs/items/",12)) ||
                                   strstr(value.model,".."))) ||
               (value.icon[0] && (strncmp(value.icon,"gfx/inv/",8) || strstr(value.icon,".."))))return 0;
    *out=value;return 1;
}
/* AREA-TABLES-59: the item records already read (from the area tables, or from items.awi while an area loads): the
 * carried items and the area's, so the inventory, the strip and a take read no file in play. Kept across areas (the
 * records never change), the oldest replaced; INV_CACHE entries (about 520 bytes each). */
#define INV_CACHE 256
static aw_inventory_item_t *inv_cache;static int inv_cache_used,inv_cache_next;
static int inv_cache_find(const char *id,aw_inventory_item_t *out){
    int i;
    for(i=0;i<inv_cache_used;i++)if(!AW_InventoryCompare(inv_cache[i].id,id)){*out=inv_cache[i];return 1;}
    return 0;
}
static void inv_cache_put(const aw_inventory_item_t *item){
    if(!inv_cache && !(inv_cache=(aw_inventory_item_t *)AW_TryMalloc(INV_CACHE*sizeof(*inv_cache))))return;
    if(inv_cache_used<INV_CACHE)inv_cache[inv_cache_used++]=*item;
    else{inv_cache[inv_cache_next]=*item;inv_cache_next=(inv_cache_next+1)%INV_CACHE;}
}
static int area_item(const char *id,aw_inventory_item_t *out);
static int inv_batch_open(void);
static int area_loading;
static unsigned long area_fallback[4];     /* disk searches in play: items.awi, focus.awf contents/owner, placed id, icons */
int AW_InventoryRead(const char *id,aw_inventory_item_t *out){
    FILE *f=NULL;byte head[8],row[INV_ROW];int size,lo=0,hi,mid,cmp;long base;
    aw_inventory_item_t value;
    if(!out || !inv_id(id,64))return 0;
    /* AREA-TABLES-59: the records in memory first, then the loaded areas' items; a miss searches items.awi */
    if(strncmp(id,AW_MADE_ITEM_PREFIX,sizeof(AW_MADE_ITEM_PREFIX)-1)){
        if(inv_cache && inv_cache_find(id,out))return 1;
        if(area_item(id,out)){inv_cache_put(out);return 1;}
        if(!area_loading)area_fallback[0]++;
    }
    if(!strncmp(id,AW_MADE_ITEM_PREFIX,sizeof(AW_MADE_ITEM_PREFIX)-1)){
        /* an item the player had enchanted (Enchanting; aw_actorstate.c): its base item with the made name, cast
         * type and charge; its effects are the made item's own */
        const aw_made_item_t *m=aw_inventory_made_item?aw_inventory_made_item(atoi(id+sizeof(AW_MADE_ITEM_PREFIX)-1)):NULL;
        if(!m || !strncmp(m->base,AW_MADE_ITEM_PREFIX,sizeof(AW_MADE_ITEM_PREFIX)-1) || !AW_InventoryRead(m->base,out))return 0;
        Q_snprintf(out->id,sizeof(out->id),"%s",id);Q_snprintf(out->name,sizeof(out->name),"%s",m->name);
        Q_snprintf(out->enchantment,sizeof(out->enchantment),"%s",id);
        out->enchant_kind=m->cast_type+1;out->charge_max=m->charge_max;out->enchant_capacity=0;
        return 1;
    }
    /* a binary search of whole rows: one row per step through a row-sized buffer, not 16 KiB (TRADEHOUSE-LONG-FRAME-59:
     * the strip's names for one basket took about 1 s); inside AW_InventoryBatchBegin/End the file stays open */
    if(inv_batch_wanted)inv_batch_open();
    if(inv_batch_file){f=inv_batch_file;size=inv_batch_size;base=inv_batch_base;}
    else{
        com_fopen_buffer=INV_ROW;size=COM_FOpenFile("inventory/items.awi",&f);com_fopen_buffer=0;
        if(!f)return 0;
        base=ftell(f);
    }
    if(fseek(f,base,SEEK_SET))goto bad;
    if(size<8 || fread(head,1,8,f)!=8 || memcmp(head,"AWI2",4))goto bad;
    hi=(int)inv_u32(head+4);if(hi<1 || hi>65536 || size!=8+hi*INV_ROW)goto bad;
    hi--;
    while(lo<=hi){
        mid=lo+(hi-lo)/2;
        if(fseek(f,base+8+(long)mid*INV_ROW,SEEK_SET) || fread(row,1,INV_ROW,f)!=INV_ROW)goto bad;
        if(!memchr(row,0,64))goto bad;
        cmp=AW_InventoryCompare((char *)row,id);
        if(cmp<0)lo=mid+1;else if(cmp>0)hi=mid-1;else{
            if(!inv_parse_row(row,&value))goto bad;
            if(f!=inv_batch_file)fclose(f);
            if(area_loading)inv_cache_put(&value);   /* the carried items read with an area load */
            *out=value;return 1;
        }
        CDAudio_Update();S_ExtraUpdate();
    }
 bad: if(f!=inv_batch_file)fclose(f);
    return 0;
}
/* TRADEHOUSE-LONG-FRAME-59: several item reads in a row (the strip's names) share one open of items.awi.
 * AREA-TABLES-59: the open happens only when a read needs the file (the area tables and the records in memory answer
 * most of them: then no open at all). */
static int inv_batch_open(void){
    FILE *f=NULL;int size;
    if(inv_batch_file)return 1;
    com_fopen_buffer=INV_ROW;size=COM_FOpenFile("inventory/items.awi",&f);com_fopen_buffer=0;
    if(!f)return 0;
    inv_batch_file=f;inv_batch_size=size;inv_batch_base=ftell(f);
    return 1;
}
void AW_InventoryBatchBegin(void){inv_batch_wanted=1;}
void AW_InventoryBatchEnd(void){
    inv_batch_wanted=0;
    if(inv_batch_file){fclose(inv_batch_file);inv_batch_file=NULL;}
}
int AW_InventoryBootstrap(void){
    FILE *f=NULL;byte head[8],row[72];int size,n,i,j,slot,amount;aw_state_t *next;
    if(aw_state.inventory.initialized)return 1;
    size=COM_FOpenFile("inventory/initial.awi",&f);if(!f)return 0;
    if(size<8 || fread(head,1,8,f)!=8 || memcmp(head,"AWST",4)){fclose(f);return 0;}
    n=(int)inv_u32(head+4);
    if(n<0 || n>AW_STATE_VALUES || size!=8+n*72){fclose(f);return 0;}
    next=(aw_state_t *)AW_TryMalloc(sizeof(*next));if(!next){fclose(f);return 0;}*next=aw_state;
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
int AW_InventoryEquippedWeaponType(void){
    aw_inventory_item_t item;
    if(!AW_InventoryEquippedItem(AW_SLOT_RIGHT,&item) || item.category!=AW_INV_WEAPON || item.weapon<1)return -1;
    return item.weapon-1;
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
/* The right-hand weapon for the first-person arms (aw_hand_models.c, PLAYER-GEAR-VISUAL-59). */
static int inv_weapon_item(int *weapon,char model[64]){
    aw_inventory_item_t item;
    if(!AW_InventoryEquippedItem(AW_SLOT_RIGHT,&item) || item.category!=AW_INV_WEAPON || item.weapon<=0 ||
       !item.model[0])return 0;
    *weapon=item.weapon;strcpy(model,item.model);return 1;
}
static float inv_condition(const char *id){
    int index=inv_item_index(&aw_state,id);
    return index>=0 && (aw_state.inventory.condition_known&(1U<<index))?aw_state.inventory.condition[index]:1;
}
float AW_InventoryCondition(const char *id){return inv_condition(id);}
/* A carried thing's condition (0..1 of its record's health) set, the dialogue's Repair service; 0 when not carried */
int AW_InventorySetCondition(const char *id,float condition){
    int index=inv_item_index(&aw_state,id);
    if(index<0)return 0;
    aw_state.inventory.condition[index]=condition<0?0:condition>1?1:condition;
    aw_state.inventory.condition_known|=1U<<index;
    return 1;
}
/* The selected magic item, read once per selection change (no per-frame I/O). */
int AW_MagicSelectedItem(aw_inventory_item_t *out){
    static char id[64];static aw_inventory_item_t value;static int ok;
    if(!out || !aw_state.magic.selected[0] || AW_StateGet(&aw_state,AW_ITEM,aw_state.magic.selected)<1)return 0;
    if(strcmp(id,aw_state.magic.selected)){
        strcpy(id,aw_state.magic.selected);ok=AW_InventoryRead(id,&value) && AW_MagicSelectable(&value);
    }
    if(ok)*out=value;
    return ok;
}
/* gfx/hud-settings.txt (tools/prepare_icons.py): the GMST, read once. */
static float recharge_rate=-1;
float AW_MagicRechargeRate(void){
    FILE *f=NULL;char text[256];int n;float value;
    if(recharge_rate>=0)return recharge_rate;
    recharge_rate=0;
    n=COM_FOpenFile("gfx/hud-settings.txt",&f);if(!f)return 0;
    if(n>0 && n<(int)sizeof(text) && fread(text,1,n,f)==(size_t)n){
        char *p;text[n]=0;p=strstr(text,"fMagicItemRechargePerSecond ");
        if(p){value=(float)Q_atof(p+28);if(value>=0 && value<=1000)recharge_rate=value;}
    }
    fclose(f);return recharge_rate;
}
/* Unpaused single-player time (SV_Physics) and waiting/resting: only items with
 * a recorded (below full) charge do any work; their catalogue rows are cached. */
void AW_MagicFrame(float seconds){
    static char ids[AW_STATE_VALUES][64];static aw_inventory_item_t rows[AW_STATE_VALUES];static int ok[AW_STATE_VALUES];
    int i;float rate;
    if(!aw_state.magic.charge_known || !(seconds>0) || (rate=AW_MagicRechargeRate())<=0)return;
    for(i=0;i<aw_state.count[AW_ITEM] && i<AW_STATE_VALUES;i++){
        if(!(aw_state.magic.charge_known&(1U<<i)))continue;
        if(strcmp(ids[i],aw_state.values[AW_ITEM][i].id)){
            strcpy(ids[i],aw_state.values[AW_ITEM][i].id);ok[i]=AW_InventoryRead(ids[i],&rows[i]);
        }
        if(ok[i])AW_MagicRecharge(&aw_state,&rows[i],seconds,rate);
    }
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
    /* Every worn armour piece (OpenMW mwclass/npc.cpp getArmorRating): cuirass 0.3; shield, helmet, greaves, boots and
     * each pauldron 0.1; each gauntlet or bracer 0.05; an empty slot the unarmoured rating. A piece rates its armour x
     * its class's skill / iBaseArmorSkill (its own armour when it weighs nothing; armor.cpp getSkillAdjustedArmorRating)
     * x its condition. Its class is also the hit sound of a blow landing on it (hit_classes, local.lua applyArmor). */
    {
        static const int skills[3]={AW_SK_LIGHT,AW_SK_MEDIUM,AW_SK_HEAVY};
        static const struct {unsigned char slot;float weight;} worn[10]={{AW_SLOT_CUIRASS,.3f},{AW_SLOT_LEFT,.1f},
            {AW_SLOT_HELMET,.1f},{AW_SLOT_GREAVES,.1f},{AW_SLOT_BOOTS,.1f},{AW_SLOT_LPAULDRON,.1f},
            {AW_SLOT_RPAULDRON,.1f},{AW_SLOT_LGAUNTLET,.05f},{AW_SLOT_RGAUNTLET,.05f}};
        int k,hit;float rating;
        sheet->hit_classes=0;
        for(k=0;k<9;k++){
            if(!AW_InventoryEquippedItem(worn[k].slot,&item) || item.category!=AW_INV_ARMOUR ||
               AW_InventoryArmourSlot(item.subtype)!=worn[k].slot || item.shield_class<0 || item.shield_class>2 ||
               item.armor_skill_base<=0)continue;
            rating=item.weight>0?item.armor*sheet->skills[skills[item.shield_class]]/item.armor_skill_base:item.armor;
            rating*=inv_condition(item.id);
            sheet->armor+=worn[k].weight*(rating-base);
            hit=AW_InventoryHitSlot(worn[k].slot);
            if(hit>=0)sheet->hit_classes|=(unsigned int)(item.shield_class+1)<<(2*hit);
            if(worn[k].slot==AW_SLOT_LEFT){
                sheet->shield=1;sheet->shield_class=(unsigned char)item.shield_class;
                sheet->shield_health_max=item.health;sheet->shield_health=item.health*inv_condition(item.id);
            }
        }
    }
}
/* dbg give weapons [stats] (DBG-GIVE-WEAPONS-59): the builder's kit (inventory/weapon-kit.txt), read on the command
 * and freed after it; every row must be a catalogue item. GIVE: all of it at once or nothing, saved like any grant.
 * Then the table, from the records' own numbers, lined up to the console width. */
#define WEAPON_KIT_FILE "inventory/weapon-kit.txt"
#define WEAPON_KIT_BYTES 8192
static void weapon_kit(int give){
    FILE *f=NULL;char *text=NULL,lines[512];aw_kit_row_t *rows=NULL;aw_inventory_item_t item;
    /* one less than the console's width: a line that fills it exactly is followed by an empty one (Con_Print wraps
     * at the width, then the line's own new line) */
    int size,n,i,need,width=AW_ConsoleWidth()-1,equippable[AW_WEAPON_KIT_ROWS];
    size=COM_FOpenFile(WEAPON_KIT_FILE,&f);
    if(!f){Con_Printf("No weapon kit in this build's data (%s).\n",WEAPON_KIT_FILE);return;}
    if(size<6 || size>WEAPON_KIT_BYTES || !(text=(char *)AW_TryMalloc(size)) ||
       !(rows=(aw_kit_row_t *)AW_TryMalloc(AW_WEAPON_KIT_ROWS*sizeof(*rows))) || fread(text,1,size,f)!=(size_t)size){
        fclose(f);free(text);free(rows);Con_Printf("Weapon kit unreadable (%s); nothing given.\n",WEAPON_KIT_FILE);return;
    }
    fclose(f);n=AW_WeaponKitParse(text,size,rows,AW_WEAPON_KIT_ROWS);free(text);
    if(n<1){free(rows);Con_Printf("Weapon kit malformed (%s); nothing given.\n",WEAPON_KIT_FILE);return;}
    for(i=0;i<n;i++){
        if(!AW_InventoryRead(rows[i].id,&item)){
            Con_Printf("Weapon kit refused: \"%s\" is not in the item catalogue; nothing given.\n",rows[i].id);free(rows);return;
        }
        equippable[i]=(item.flags&(AW_INV_EQUIP|AW_INV_EQUIP_SUPPORTED))==(AW_INV_EQUIP|AW_INV_EQUIP_SUPPORTED);
    }
    if(give){
        if(!sv.active || svs.maxclients!=1){free(rows);Con_Printf("Weapon kit: start or load a game first.\n");return;}
        need=AW_WeaponKitNeeds(&aw_state,rows,n);
        if(!AW_WeaponKitGrant(&aw_state,rows,n)){
            Con_Printf("Weapon kit refused: it needs %d more kinds of item, %d free of %d; nothing given.\n",
                       need,AW_STATE_VALUES-aw_state.count[AW_ITEM],AW_STATE_VALUES);
            free(rows);return;
        }
        Con_Printf("DIAGNOSTIC weapon kit given: %d items (dbg give weapons stats shows this again).\n",n);
    }
    Con_Printf("Weapon kit, stats from the game's records:\n");
    for(i=0;i<n;i++){
        if(AW_WeaponKitLines(&rows[i],equippable[i],width,lines,sizeof(lines))<1)continue;
        Con_Printf("%s\n",lines);
    }
    Con_Printf("equip: aw_inventory equip \"ID\" or I; carry: not equippable yet\n");
    free(rows);
}
/* MWSCRIPT-TRAY-SMOKE-58: what the last refused space check met (the map, or an entity's number and model), for
 * the test route's refusal line (aw_inventory drop) */
static char space_blocker[80];
void AW_InventoryGrantCommand(void){
    aw_inventory_item_t item;int n;
    if(cmd_source==src_command && (Cmd_Argc()==3 || Cmd_Argc()==4) && !Q_strcasecmp(Cmd_Argv(1),"give") &&
       !Q_strcasecmp(Cmd_Argv(2),"weapons")){
        if(Cmd_Argc()==4 && Q_strcasecmp(Cmd_Argv(3),"stats")){Con_Printf("dbg give weapons [stats]\n");return;}
        weapon_kit(Cmd_Argc()==3);return;
    }
    /* dbg inventory equip "<id>": equip a carried item as the inventory window's E does (tests of first- and
     * third-person gear, PLAYER-GEAR-VISUAL-59); the same rules, refused when the window would refuse it. */
    if(cmd_source==src_command && sv.active && svs.maxclients==1 && Cmd_Argc()==3 && !Q_strcasecmp(Cmd_Argv(1),"equip")){
        if(!AW_InventoryRead(Cmd_Argv(2),&item) || AW_StateGet(&aw_state,AW_ITEM,item.id)<1 || !AW_InventoryCanEquip(&item)){
            Con_Printf("Diagnostic inventory equip refused.\n");return;
        }
        AW_CombatEquipmentStore();
        if(!AW_InventoryEquipped(&aw_state,item.id) && !AW_InventoryEquip(&aw_state,&item)){
            Con_Printf("Diagnostic inventory equip refused.\n");return;
        }
        AW_CombatEquipmentChanged();Con_Printf("DIAGNOSTIC inventory equip: %s.\n",item.id);return;
    }
    /* dbg inventory unequip "<id>" | worn (ARRIVAL-LONG-FRAME-DEV6-59, the gear swap check of the cached body): take
     * off a worn item as the inventory window does; "worn" lists the clothing and armour slots */
    if(cmd_source==src_command && sv.active && svs.maxclients==1 && Cmd_Argc()==2 && !Q_strcasecmp(Cmd_Argv(1),"worn")){
        int s;
        for(s=AW_SLOT_HELMET;s<=AW_SLOT_ROBE;s++)if(aw_state.inventory.equipped[s][0])
            Con_Printf("  worn slot %d: %s\n",s,aw_state.inventory.equipped[s]);
        return;
    }
    /* dbg inventory wear "<id>": one of it given (test only) and worn, as the window's E */
    if(cmd_source==src_command && sv.active && svs.maxclients==1 && Cmd_Argc()==3 && !Q_strcasecmp(Cmd_Argv(1),"wear")){
        if(!AW_InventoryRead(Cmd_Argv(2),&item) || !AW_InventoryCanEquip(&item)){Con_Printf("Diagnostic inventory wear refused.\n");return;}
        AW_StateSet(&aw_state,AW_ITEM,item.id,AW_StateGet(&aw_state,AW_ITEM,item.id)+1);
        AW_CombatEquipmentStore();
        if(!AW_InventoryEquipped(&aw_state,item.id) && !AW_InventoryEquip(&aw_state,&item)){Con_Printf("Diagnostic inventory wear refused.\n");return;}
        AW_CombatEquipmentChanged();Con_Printf("DIAGNOSTIC inventory wear: %s at %.0f ms.\n",item.id,Sys_FloatTime()*1000);return;
    }
    if(cmd_source==src_command && sv.active && svs.maxclients==1 && Cmd_Argc()==3 && !Q_strcasecmp(Cmd_Argv(1),"unequip")){
        AW_CombatEquipmentStore();
        if(!AW_InventoryEquipped(&aw_state,Cmd_Argv(2)) || !AW_InventoryUnequip(&aw_state,Cmd_Argv(2))){
            Con_Printf("Diagnostic inventory unequip refused: not worn.\n");return;
        }
        AW_CombatEquipmentChanged();Con_Printf("DIAGNOSTIC inventory unequip: %s.\n",Cmd_Argv(2));return;
    }
    /* aw_inventory drop "<id>" [N] (CELL-CHANGES-59 slice 2, test sessions): drop a carried item in front of the
     * player through the inventory window's own drop (AW_InventoryDropHere: its checks, the world change list) */
    if(cmd_source==src_command && sv.active && svs.maxclients==1 && (Cmd_Argc()==3 || Cmd_Argc()==4) &&
       !Q_strcasecmp(Cmd_Argv(1),"drop")){
        n=Cmd_Argc()==4?Q_atoi(Cmd_Argv(3)):1;
        if(n<1 || !AW_InventoryRead(Cmd_Argv(2),&item) || AW_StateGet(&aw_state,AW_ITEM,item.id)<n){
            Con_Printf("Diagnostic inventory drop refused: not carried.\n");return;
        }
        space_blocker[0]=0;
        if(!AW_InventoryDropHere(&item,n)){
            /* MWSCRIPT-TRAY-SMOKE-58: the window's own reason, and what the space check met */
            Con_Printf("Diagnostic inventory drop refused: %s%s%s\n",AW_InventoryDropReason(),
                       space_blocker[0]?" Met: ":"",space_blocker);
            return;
        }
        Con_Printf("DIAGNOSTIC inventory drop: %s -%d, now %ld.\n",item.id,n,(long)AW_StateGet(&aw_state,AW_ITEM,item.id));
        return;
    }
    if(cmd_source!=src_command || !sv.active || svs.maxclients!=1 || Cmd_Argc()!=4 || Q_strcasecmp(Cmd_Argv(1),"grant"))return;
    n=Q_atoi(Cmd_Argv(3));
    if(n<1 || n>999 || !AW_InventoryRead(Cmd_Argv(2),&item) || !AW_ItemAdd(&aw_state,item.id,n)){
        Con_Printf("Diagnostic inventory grant refused.\n");return;
    }
    Con_Printf("DIAGNOSTIC inventory grant: %s +%d, now %ld.\n",item.id,n,(long)AW_StateGet(&aw_state,AW_ITEM,item.id));
}
void AW_InventoryInit(void){
    aw_combat_equipment=inv_combat;aw_combat_equipment_store=inv_store;aw_hand_block_item=inv_block_item;aw_hand_weapon_item=inv_weapon_item;
    aw_inventory_hand_item=AW_InventoryEquippedItem;
    aw_magic_frame=AW_MagicFrame;
}
static void inv_level(void){
    if(inventory_world!=sv.worldmodel){
        inventory_world=sv.worldmodel;model_names_used=0;
        memset(drop_entity,0,sizeof(drop_entity));memset(drop_label,0,sizeof(drop_label));
        map_drop_count=0;
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
    if(i>=MAX_MODELS-AW_INVENTORY_KEEP_MODELS){drop_reason="World model table full; kept.";return 0;}
    if(model_names_used>=AW_INVENTORY_MODELS){drop_reason="Scene item model limit reached; kept.";return 0;}
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
/* CELL-CHANGES-59: the list's drops this map shows and does not show yet (outdoors: any map that converts the drop's
 * game units to a spot inside its world, a CHIM frame or an open-world region; in a room: the room of its number). */
static void ledger_spawn(void){
    int i,j,model;aw_inventory_item_t item;vec3_t local;
    if(!aw_ledger_on || !sv.active || svs.maxclients!=1)return;
    for(i=AW_LedgerFrom(&aw_ledger,AW_LEDGER_PLAYER);i<aw_ledger.count && !(aw_ledger.row[i].key&AW_LEDGER_BUILDER);i++){
        aw_ledger_row_t *r=&aw_ledger.row[i];aw_ledger_extra_t *x=r->extra;edict_t *e;
        if(!(r->fields&AW_LEDGER_DROPPED) || !x)continue;
        for(j=0;j<map_drop_count && map_drops[j].key!=r->key;j++);
        if(j<map_drop_count || !AW_PlacedLocal(r->at,r->where,x->position,local))continue;
        if(!AW_InventoryRead(x->item,&item) || !(model=inv_model(&item)) || !inv_edict_available() || !map_drop_room()){
            Con_Printf("Inventory: dropped item %s kept in the world change list; model/entity unavailable.\n",x->item);continue;
        }
        e=ED_Alloc();map_drop_add(r->key,e,item.name);ledger_drop_entity(e,model,local,x->yaw);
    }
}
void AW_InventorySpawn(void){
    int i,model;aw_inventory_item_t item;
    /* Called after a fresh server/map restore. Old edict addresses can now
     * belong to unrelated actors, even when the cached worldmodel is equal. */
    inventory_world=sv.worldmodel;model_names_used=0;
    memset(drop_entity,0,sizeof(drop_entity));memset(drop_label,0,sizeof(drop_label));
    map_drop_count=0;
    if(aw_ledger_on){
        /* an older save's drops (keyed by map name) join the list once; then the list's drops of this map */
        if((i=AW_LedgerAdoptDrops(&aw_state,&aw_ledger))>0)Con_Printf("Inventory: %d dropped items of the save moved to the world change list.\n",i);
        ledger_spawn();return;
    }
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
/* E's linked box (absmin/absmax) meets the box LOW..HIGH */
static int inv_box_meets(const edict_t *e,const float low[3],const float high[3]){
    int k;
    for(k=0;k<3;k++)if(high[k]<=e->v.absmin[k] || low[k]>=e->v.absmax[k])return 0;
    return 1;
}
static int inv_space_blocked(const edict_t *e,int number){
    if(!e)Q_strcpy_bounded(space_blocker,"the map",sizeof(space_blocker));
    else Q_snprintf(space_blocker,sizeof(space_blocker),"entity %d (%s, solid %d)",number,
                    e->v.model?pr_strings+e->v.model:"no model",(int)e->v.solid);
    return 0;
}
static int inv_space_clear(const float low[3],const float high[3],edict_t *player){
    int i,k,index,overlap;edict_t *e;vec3_t local_low,local_high;
    if(!inv_hull_region(sv.worldmodel,low,high,CONTENTS_EMPTY))return inv_space_blocked(NULL,0);
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);if(e->free || e==player || e->v.solid==SOLID_NOT || e->v.solid==SOLID_TRIGGER)continue;
        /* DROP-ROOM-BRUSH-ENTITY-59: only an entity whose linked box meets the region can be in the way; a brush
         * entity's hull 0 reads solid everywhere outside its own faces (Quake's submodels have no empty leaves), so
         * every brush entity of a room refused every drop there */
        if(!inv_box_meets(e,low,high))continue;
        if(e->v.solid==SOLID_BSP){
            index=(int)e->v.modelindex;if(index<=0 || index>=MAX_MODELS || !sv.models[index])return inv_space_blocked(e,i);
            inv_local_bounds(e,low,high,local_low,local_high);
            if(!inv_hull_region(sv.models[index],local_low,local_high,CONTENTS_EMPTY))return inv_space_blocked(e,i);
        }else{
            overlap=1;
            for(k=0;k<3;k++)if(high[k]<=e->v.origin[k]+e->v.mins[k] || low[k]>=e->v.origin[k]+e->v.maxs[k])overlap=0;
            if(overlap)return inv_space_blocked(e,i);
        }
    }
    return 1;
}
static int inv_support(const float low[3],const float high[3]){
    int i,index;edict_t *e;vec3_t local_low,local_high;
    if(inv_hull_region(sv.worldmodel,low,high,CONTENTS_SOLID))return 1;
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);if(e->free || e->v.solid!=SOLID_BSP || !inv_box_meets(e,low,high))continue;   /* as above */
        index=(int)e->v.modelindex;if(index<=0 || index>=MAX_MODELS || !sv.models[index])continue;
        inv_local_bounds(e,low,high,local_low,local_high);
        if(inv_hull_region(sv.models[index],local_low,local_high,CONTENTS_SOLID))return 1;
    }
    return 0;
}
/* CELL-CHANGES-59: on a streamed (CHIM) map the hull query below sees only the frame's own BSP, not the streamed
 * ground and models (DROP-CHIM-REFUSED-59); there the footprint is checked with point traces, which see all of it
 * (SV_Move): under each bottom corner of the item and its centre dry, walkable ground within a few units, and no
 * corner starting inside something solid (a wall, a crate). */
static int inv_trace_support(const float position[3],const float mins[3],const float maxs[3],edict_t *p){
    int corner;vec3_t start,end;trace_t tr;float bottom=position[2]+mins[2];
    for(corner=0;corner<5;corner++){
        start[0]=position[0]+(corner==4?0:(corner&1)?maxs[0]:mins[0]);
        start[1]=position[1]+(corner==4?0:(corner&2)?maxs[1]:mins[1]);
        start[2]=bottom+8;VectorCopy(start,end);end[2]=bottom-6;
        tr=SV_Move(start,vec3_origin,vec3_origin,end,MOVE_NORMAL,p);
        if(tr.startsolid || tr.allsolid || tr.fraction>=1 || tr.plane.normal[2]<.69f ||
           SV_PointContents(tr.endpos)<=CONTENTS_WATER)return 0;
    }
    return 1;
}
int AW_InventoryDropHere(const aw_inventory_item_t *item,int32_t count){
    edict_t *p,*e;trace_t tr;vec3_t forward,right,up,eye,start,end,position,mins,maxs,low,high,swept_low,swept_high,point;
    int model,index,j,corner,chim;float yaw;
    drop_reason="Cannot drop this item here; kept.";
    if(!item || !(item->flags&AW_INV_DROP) || !sv.active || svs.maxclients!=1 ||
       !svs.clients || !(p=svs.clients[0].edict) || p->v.health<=0 ||
       p->v.movetype!=MOVETYPE_WALK || p->v.waterlevel>=2)return 0;
    /* Point traces include streamed/scenery/barrier collision, but the full
     * footprint query below currently certifies only BSP world/brush volumes.
     * Refuse that unsupported context before model/entity/ownership admission.
     * CELL-CHANGES-59: with the world change list a CHIM map's drop is checked by point traces (inv_trace_support). */
    chim=Chim_Active();
    if((chim && !aw_ledger_on) || AW_SceneryCount()>0 || AW_StoryRestricted()){
        drop_reason="Cannot place items in this area yet; kept.";return 0;
    }
    if(!aw_ledger_on){     /* the old fixed table: 32 drops (the world change list has no such ceiling) */
        for(j=0;j<AW_INVENTORY_DROPS && aw_state.inventory.dropped[j].count;j++);
        if(j==AW_INVENTORY_DROPS){drop_reason="Ground item limit (32); kept.";return 0;}
    }else if(!map_drop_room()){drop_reason="Ground item limit (32) on this map; kept.";return 0;}
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
    /* DROP-ROOM-BRUSH-ENTITY-59: a converted room stands on model collision the hull query below does not see (the
     * Census Office floor), so with the world change list a room is checked by the same point traces */
    if(chim || aw_ledger_on){
        drop_reason="Item footprint unsupported; kept.";
        if(!inv_trace_support(position,mins,maxs,p))return 0;
    }else{
    drop_reason="Item path or footprint obstructed; kept.";
    if(!inv_space_clear(swept_low,swept_high,p) || !inv_space_clear(low,high,p))return 0;
    /* Require the whole footprint's shallow support slab inside one dry solid
     * world/brush volume. This deliberately refuses bridging holes and ledges. */
    high[2]=low[2]-.125f;low[2]-=.25f;
    drop_reason="Item footprint unsupported; kept.";
    if(!inv_support(low,high))return 0;
    }
    AW_CombatEquipmentStore();
    if(aw_ledger_on){
        /* CELL-CHANGES-59: the drop is a row of the world change list at this place (aw_ledger_drops.c) */
        int at;int32_t where;float game[3];uint32_t key;
        drop_reason="Cannot place items here; kept.";
        if(!AW_PlacedWhere(position,&at,&where,game))return 0;
        e=ED_Alloc();
        if(!(key=AW_LedgerDrop(&aw_state,&aw_ledger,item,count,at,where,game,yaw))){
            ED_Free(e);drop_reason="Inventory transfer refused; kept.";return 0;}
        map_drop_add(key,e,item->name);ledger_drop_entity(e,model,position,yaw);AW_CombatEquipmentChanged();
        AW_UIPickupNotice(item->name,2);return 1;
    }
    e=ED_Alloc();index=AW_InventoryDrop(&aw_state,item,count,sv.name,position,yaw);
    if(index<0){ED_Free(e);drop_reason="Inventory transfer refused; kept.";return 0;}
    strcpy(drop_label[index],item->name);inv_entity(e,index,model);AW_CombatEquipmentChanged();
    AW_UIPickupNotice(item->name,2);return 1;
}

/* gfx/hud-settings.txt lines "<GMST> <value>" (tools/prepare_icons.py hud_settings), the file read once. */
static int hud_setting(const char *key,char *out,int size){
    static char text[512];static int loaded;
    FILE *f=NULL;int n;const char *p;size_t k=strlen(key);
    if(!loaded){
        loaded=1;text[0]=0;n=COM_FOpenFile("gfx/hud-settings.txt",&f);
        if(f){if(n>0 && n<(int)sizeof(text) && fread(text,1,n,f)==(size_t)n)text[n]=0;else text[0]=0;fclose(f);}
    }
    for(p=text;*p;){
        if(!strncmp(p,key,k) && p[k]==' '){
            p+=k+1;for(n=0;n<size-1 && p[n] && p[n]!='\n' && p[n]!='\r';n++)out[n]=p[n];
            out[n]=0;return n>0;
        }
        p=strchr(p,'\n');if(!p)break;p++;
    }
    return 0;
}
/* The activation distance (GMST iMaxActivateDist, game units) in map units (a quarter scale, aw_mwhost.c
 * to_game_units). Data built before FOCUS-BOX-58 lacks the line: the original's own setting, 192, said once. */
float AW_ActivateDistance(void){
    static float reach=-1;char value[32];int n;
    if(reach>0)return reach;
    n=hud_setting("iMaxActivateDist",value,sizeof(value))?atoi(value):0;
    if(n<1 || n>100000){Con_Printf("Activation distance not in this build's data; the original's 192 used.\n");n=192;}
    reach=n*0.25f;return reach;
}
/* OpenMW 0.51 shows weights with up to two decimals, trailing zeros dropped (mwgui/tooltips.cpp toString). */
static void weight_text(float weight,char *out,int size){
    int n;Q_snprintf(out,size,"%.2f",weight);n=strlen(out);
    while(n>0 && out[n-1]=='0')out[--n]=0;
    if(n>0 && out[n-1]=='.')out[--n]=0;
}
static int inv_target(void){
    int i,best=-1;float distance=AW_ActivateDistance(),along,side;edict_t *p;vec3_t f,r,u,eye,delta;trace_t tr;
    if(!sv.active || svs.maxclients!=1 || !svs.clients || !(p=svs.clients[0].edict))return -1;
    inv_level();VectorCopy(p->v.origin,eye);eye[2]+=p->v.view_ofs[2];
    AngleVectors(p->v.v_angle,f,r,u);
    for(i=0;i<AW_INVENTORY_DROPS;i++)if(drop_entity[i] && !drop_entity[i]->free && aw_state.inventory.dropped[i].count>0){
        VectorSubtract(drop_entity[i]->v.origin,eye,delta);along=DotProduct(delta,f);
        /* within the activation distance from the eye (not only along the view) */
        if(along<0 || along>distance || DotProduct(delta,delta)>distance*distance)continue;
        side=DotProduct(delta,delta)-along*along;if(side>64)continue;
        tr=SV_Move(eye,vec3_origin,vec3_origin,drop_entity[i]->v.origin,MOVE_NOMONSTERS,p);
        if(tr.fraction<1)continue;
        distance=along;best=i;
    }
    return best;
}
/* CELL-CHANGES-59: the same aim over the drops of the world change list this map shows */
static int ledger_target(void){
    int i,best=-1;float distance=AW_ActivateDistance(),along,side;edict_t *p,*e;vec3_t f,r,u,eye,delta;trace_t tr;
    if(!sv.active || svs.maxclients!=1 || !svs.clients || !(p=svs.clients[0].edict))return -1;
    inv_level();VectorCopy(p->v.origin,eye);eye[2]+=p->v.view_ofs[2];
    AngleVectors(p->v.v_angle,f,r,u);
    for(i=0;i<map_drop_count;i++){
        if(!map_drops[i].key || !(e=map_drops[i].e) || e->free)continue;
        VectorSubtract(e->v.origin,eye,delta);along=DotProduct(delta,f);
        if(along<0 || along>distance || DotProduct(delta,delta)>distance*distance)continue;
        side=DotProduct(delta,delta)-along*along;if(side>64)continue;
        tr=SV_Move(eye,vec3_origin,vec3_origin,e->v.origin,MOVE_NOMONSTERS,p);
        if(tr.fraction<1)continue;
        distance=along;best=i;
    }
    return best;
}
/* the aimed drop of either store, -1 none */
static int drop_aimed(void){return aw_ledger_on?ledger_target():inv_target();}
const char *AW_InventoryHint(void){
    int i=drop_aimed();
    return i<0?NULL:aw_ledger_on?map_drops[i].label:drop_label[i];
}
int AW_InventoryFocus(const char **name,char *weight_line,char *value_line,int line_size,int *owned){
    static char cached_id[64],label_weight[32],label_value[32];static aw_inventory_item_t item;static int cached_ok,labels;
    char number[24];int i=drop_aimed();const char *id=NULL,*label=NULL;
    if(i>=0 && aw_ledger_on){
        int k=AW_LedgerFind(&aw_ledger,map_drops[i].key);
        if(k>=0 && aw_ledger.row[k].extra){id=aw_ledger.row[k].extra->item;label=map_drops[i].label;}
    }else if(i>=0){id=aw_state.inventory.dropped[i].id;label=drop_label[i];}
    if(!id || !name || !weight_line || !value_line || line_size<2)return 0;
    if(!labels){
        labels=1;
        if(!hud_setting("sWeight",label_weight,sizeof(label_weight)))strcpy(label_weight,"Weight");
        if(!hud_setting("sValue",label_value,sizeof(label_value)))strcpy(label_value,"Value");
    }
    /* one catalogue read per newly aimed item, not per frame */
    if(strcmp(cached_id,id)){
        Q_strcpy_bounded(cached_id,id,sizeof(cached_id));
        cached_ok=AW_InventoryRead(cached_id,&item);
    }
    *name=label;weight_line[0]=value_line[0]=0;
    if(cached_ok){
        weight_text(item.weight,number,sizeof(number));
        Q_snprintf(weight_line,line_size,"%s: %s",label_weight,number);
        Q_snprintf(value_line,line_size,"%s: %d",label_value,item.value);
    }
    /* the player's own dropped items are never theft */
    if(owned)*owned=0;
    return 1;
}
/* Placed things (FOCUS-BOX-58): id1/focus.awf (tools/prepare_focus.py), the loaded room's rows read once per map,
 * outdoors the rows of the player's exterior cell and its neighbours (focus_load).
 * Positions are game units; the room map is a quarter scale plus its shift (aw_mwhost.c AW_MwscriptRoomShift, the
 * same shift the scripts' placements use). Rows whose reference has an edict here (aw_ref: actors, doors) are left
 * to that edict's own targeting; an object a script disabled shows no box. */
#define FOCUS_ROWS 1024
#define FOCUS_ROW 64
#define FOCUS_ROW2 96          /* AWF2 (PICKUP-PLACED-58): the AWF1 row, then the item's record id (32 bytes) */
#define FOCUS_ID 32
/* The row's action code (byte 2, tools/prepare_focus.py ACT_*): bits 0-1 the kind, bit 2 owned, bit 3 magic scroll. */
#define FOCUS_ACT_TAKE 1
#define FOCUS_ACT_READ 2
#define FOCUS_ACT_TALK 3
#define FOCUS_ACT_OWNED 4
#define FOCUS_ACT_MAGIC_SCROLL 8
static int focus_stride=FOCUS_ROW;
/* lock: a container's lock level in the data (CONTAINER-WINDOW-59, row byte 3; 0 for everything else) */
typedef struct {vec3_t at;float weight;int value;unsigned reference;char kind,owned,edict,live,action,name[37];short drawn;unsigned char lock;} focus_row_t;
static focus_row_t *focus_rows;
static int focus_count;
static model_t *focus_world;
static unsigned long focus_u32(const byte *p){return (unsigned long)p[0]|((unsigned long)p[1]<<8)|((unsigned long)p[2]<<16)|((unsigned long)p[3]<<24);}
static long focus_room(void){
    const char *p=sv.worldmodel?sv.worldmodel->entities:NULL,*key,*end;long n=0;
    if(!p)return 0;
    key=strstr(p,"\"_aw_cell_int\"");end=strchr(p,'}');
    if(!key || !end || key>end)return 0;
    key+=14;while(*key==' ' || *key=='\t')key++;
    if(*key!='"')return 0;
    for(key++;*key>='0' && *key<='9' && n<100000;key++)n=n*10+(*key-'0');
    return *key=='"'?n:0;
}
/* Outdoors (an open-world or CHIM frame map, AW_SourceToWorld): the rows of the exterior cell the player stands in
 * and its eight neighbours (the activation distance is far below a cell), read again when the player's cell
 * changes. The key is tools/prepare_focus.py exterior_key. */
#define FOCUS_CELL 8192.0f
#define FOCUS_GRID_BIAS 2048
static int focus_outdoor,focus_gx,focus_gy;
static unsigned long focus_exterior_key(int gx,int gy){
    return 0x80000000ul|((unsigned long)((gx+FOCUS_GRID_BIAS)&0xFFF)<<12)|(unsigned long)((gy+FOCUS_GRID_BIAS)&0xFFF);
}
/* One focus.awf row (game units) onto the table, when it is one this engine shows (also the area tables' rows,
 * AREA-TABLES-59: the same 96 bytes). */
static void focus_add_row(const byte *row){
    focus_row_t *r;unsigned long bits;int j;
    if(focus_count>=FOCUS_ROWS)return;
    if(row[0]!='I' && row[0]!='A' && row[0]!='D' && row[0]!='C')return;   /* 'C' a container (slice 3) */
    r=&focus_rows[focus_count];
    r->kind=(char)row[0];r->owned=row[1]?1:0;r->edict=0;r->reference=(unsigned)focus_u32(row+4);
    /* STEAL-PROMPT-58: the builder's action code (prepare_focus.py); an older file has 0: an item is taken */
    r->action=(char)(row[2]?row[2]:row[0]=='I'?FOCUS_ACT_TAKE|(row[1]?FOCUS_ACT_OWNED:0):0);
    /* CONTAINER-WINDOW-59: a container's action 1 opens it (0: organic, harvested; an older file: none) */
    r->lock=(unsigned char)(row[0]=='C' && row[3]<=100?row[3]:0);
    for(j=0;j<3;j++)r->at[j]=(float)(int32_t)focus_u32(row+8+4*j);
    bits=focus_u32(row+20);memcpy(&r->weight,&bits,4);r->value=(int)(int32_t)focus_u32(row+24);
    memcpy(r->name,row+28,36);r->name[36]=0;
    for(j=0;r->name[j];j++)if((unsigned char)r->name[j]<32)r->name[j]=' ';
    if(!r->name[0] || !(r->weight>=0 && r->weight<1000000))return;
    focus_count++;
}
/* Append one key's rows (game units) to the table; 0 on a bad file. With WANT set nothing is appended: the record
 * id of item row WANT goes to ID (AWF2 only; ID stays empty when the row is not there). */
static int focus_read_key_id(FILE *f,long base,unsigned long rooms,unsigned long key,unsigned want,char *id){
    byte head[12],row[FOCUS_ROW2];int lo,hi,mid,i,j;unsigned long number,first=0,rows=0;
    for(lo=0,hi=(int)rooms-1;lo<=hi;){
        mid=(lo+hi)/2;
        if(fseek(f,base+8+mid*12L,SEEK_SET) || fread(head,1,12,f)!=12)return 0;
        number=focus_u32(head);
        if(number==key){first=focus_u32(head+4);rows=focus_u32(head+8);break;}
        if(number<key)lo=mid+1;else hi=mid-1;
    }
    if(!rows)return 1;
    if(rows>FOCUS_ROWS || fseek(f,base+8+(long)rooms*12+(long)first*focus_stride,SEEK_SET))return 0;
    for(i=0;i<(int)rows && (want || focus_count<FOCUS_ROWS);i++){
        if(fread(row,1,focus_stride,f)!=(size_t)focus_stride)break;
        if(want){
            if(row[0]!='I' || focus_u32(row+4)!=want || focus_stride!=FOCUS_ROW2)continue;
            memcpy(id,row+FOCUS_ROW,FOCUS_ID);id[FOCUS_ID]=0;
            for(j=0;id[j];j++)if((unsigned char)id[j]<32 || (unsigned char)id[j]>126)id[0]=0;
            return 1;
        }
        focus_add_row(row);
    }
    return 1;
}
static int focus_read_key(FILE *f,long base,unsigned long rooms,unsigned long key){
    return focus_read_key_id(f,base,rooms,key,0,NULL);
}
/* Open focus.awf at its index: the file, its base and room count; NULL on a file this engine does not read. */
/* AWF3 (CELL-CHANGES-59 slice 2): the AWF2 rows, then the owner list (placed_owner); its length for the owner list */
static int focus_owners;static long focus_length;
/* TRADEHOUSE-LONG-FRAME-59: a lookup (a binary search: a seek and a few bytes per step) reads through a small buffer.
 * The game's files read through 16 KiB (common.c), so every step of a search refilled 16 KiB from the game disk: one
 * container's contents and owner took about 3 s on FS-UAE (measured in the tradehouse, 3 November 2026). */
#define FOCUS_LOOKUP_BUFFER 256
static FILE *focus_open_buffered(long *base,unsigned long *rooms,int lookup);
static FILE *focus_open(long *base,unsigned long *rooms){return focus_open_buffered(base,rooms,0);}
static FILE *focus_open_buffered(long *base,unsigned long *rooms,int lookup){
    FILE *f=NULL;byte head[8];int length;
    com_fopen_buffer=lookup?FOCUS_LOOKUP_BUFFER:0;
    length=COM_FOpenFile("focus.awf",&f);
    com_fopen_buffer=0;
    if(!f)return NULL;
    *base=ftell(f);
    if(length<8 || fread(head,1,8,f)!=8 ||
       (memcmp(head,"AWF1",4) && memcmp(head,"AWF2",4) && memcmp(head,"AWF3",4))){fclose(f);return NULL;}
    focus_stride=head[3]=='2' || head[3]=='3'?FOCUS_ROW2:FOCUS_ROW;
    focus_owners=head[3]=='3';focus_length=length;
    *rooms=focus_u32(head+4);
    if(*rooms>65535 || 8+*rooms*12>(unsigned long)length){fclose(f);return NULL;}
    return f;
}
/* AREA-TABLES-59: the per-area lookup tables (id1/areas.awa, tools/prepare_area_tables.py). One pack with its index
 * of keys at its head, held in memory (12 bytes an area); an area costs one seek and one read when its room or exterior
 * cell is loaded (focus_load: the room, or outdoors the player's cell and its eight neighbours) and is freed when the
 * place changes. Every lookup during play (a container's contents, lock and trap, an owner, a placed item's record, an
 * item's catalogue row and its strip picture) reads the loaded areas first; a miss searches the island-wide file as
 * before and counts as a fallback (aw_placed areas; zero in the proof sessions). */
#define AREA_MAX 9
#define AREA_HEAD 16
#define AREA_OWNER 32
typedef struct {
    unsigned long key;byte *blob;long bytes;
    int rows,owners,owned,conts,contents,items;
    const byte *row,*owner,*own,*cont,*content,*itemoff,*pic;
    const byte *lev;      /* CONTAINER-LEVELLED-CONTENTS-60: the levelled lists (CHIM actor table list layout), or NULL */
    const byte *pool;int pool_ids;   /* and the ids their entries name (u8 length, the id) */
} area_t;
/* slots 0..AREA_MAX-1: the place's areas; the last AREA_NARROW: the cache (KEEP WHAT YOU CAN AFFORD): the areas the
 * player left lately and those narrow-loaded for one answer outside the place (a carried item from elsewhere, a
 * container a script names). Coming back to a cached area reads nothing; the least recently used one goes when the
 * slots or AREA_CACHE_BYTES are used up (at 32 MB Fast a fixed size; above it the budget grows with the free memory). */
#define AREA_NARROW 16
#define AREA_CACHE_BYTES (256*1024L)
#define AREA_SLOTS (AREA_MAX+AREA_NARROW)
#define AREA_DIR_BLOCK 256
static area_t areas[AREA_SLOTS];static int area_count;static unsigned long area_narrow_used[AREA_NARROW],area_clock;
static byte *area_index,*area_item_dir;static unsigned long area_keys,area_dir_items,area_dir_conts,area_cont_at;
static byte *area_cont_heads;static unsigned long area_cont_blocks;
static FILE *area_file;static long area_base,area_length;
static int area_tried;
static unsigned long area_loads,area_load_bytes,area_hits,area_narrow_loads;static double area_load_seconds,area_last_seconds;
static unsigned long area_last_bytes;static int area_last_count;
static int area_ready(void){
    byte head[24];int length;unsigned long item_at;
    if(area_tried)return area_index!=NULL;
    area_tried=1;
    length=COM_FOpenFile("areas.awa",&area_file);
    if(!area_file)return 0;
    area_base=ftell(area_file);area_length=length;
    if(length<24 || fread(head,1,24,area_file)!=24 || memcmp(head,"AWA1",4) || (area_keys=focus_u32(head+4))>65535 ||
       (area_dir_items=focus_u32(head+12))>65535 || (area_dir_conts=focus_u32(head+20))>1048576 ||
       24+area_keys*12>(unsigned long)length)goto bad;
    item_at=focus_u32(head+8);area_cont_at=focus_u32(head+16);
    area_cont_blocks=(area_dir_conts+AREA_DIR_BLOCK-1)/AREA_DIR_BLOCK;
    if(item_at+area_dir_items*8>(unsigned long)length ||
       area_cont_at+area_dir_conts*8+area_cont_blocks*4>(unsigned long)length)goto bad;
    /* in memory: the area index (12 bytes an area), the item directory (8 bytes an item), the container directory's
     * block heads (4 bytes every 256 containers) */
    if(!(area_index=(byte *)AW_TryMalloc((int)(area_keys*12+1))) ||
       !(area_item_dir=(byte *)AW_TryMalloc((int)(area_dir_items*8+1))) ||
       !(area_cont_heads=(byte *)AW_TryMalloc((int)(area_cont_blocks*4+1))) ||
       fread(area_index,1,area_keys*12,area_file)!=area_keys*12 ||
       fseek(area_file,area_base+(long)item_at,SEEK_SET) ||
       fread(area_item_dir,1,area_dir_items*8,area_file)!=area_dir_items*8 ||
       fseek(area_file,area_base+(long)(area_cont_at+area_dir_conts*8),SEEK_SET) ||
       fread(area_cont_heads,1,area_cont_blocks*4,area_file)!=area_cont_blocks*4)goto bad;
    Con_Printf("Area tables: %lu areas; in memory the index %lu bytes, the item directory %lu bytes, the container "
               "directory's heads %lu bytes\n",area_keys,area_keys*12,area_dir_items*8,area_cont_blocks*4);
    return 1;
 bad:
    if(area_index){free(area_index);area_index=NULL;}
    if(area_item_dir){free(area_item_dir);area_item_dir=NULL;}
    if(area_cont_heads){free(area_cont_heads);area_cont_heads=NULL;}
    fclose(area_file);area_file=NULL;
    Con_Printf("Area tables: areas.awa is not a pack this engine reads; lookups search the game files.\n");
    return 0;
}
static void area_free(area_t *a){if(a->blob)free(a->blob);memset(a,0,sizeof(*a));}
/* the record of KEY read and its sections checked; 0 when the pack has none or it does not read */
static int area_read_at(unsigned long n,area_t *a);
static int area_read(unsigned long key,area_t *a){
    int lo=0,hi=(int)area_keys-1,mid;
    memset(a,0,sizeof(*a));
    if(!area_index)return 0;
    while(lo<=hi){
        mid=(lo+hi)/2;
        if(focus_u32(area_index+mid*12)==key)return area_read_at((unsigned long)mid,a);
        if(focus_u32(area_index+mid*12)<key)lo=mid+1;else hi=mid-1;
    }
    return 0;
}
/* area N of the index read */
static int area_read_at(unsigned long n,area_t *a){
    unsigned long key,offset,bytes;const byte *b;long need;
    memset(a,0,sizeof(*a));
    if(n>=area_keys)return 0;
    b=area_index+n*12;key=focus_u32(b);offset=focus_u32(b+4);bytes=focus_u32(b+8);
    if(!bytes || bytes<AREA_HEAD || offset+bytes>(unsigned long)area_length || bytes>4*1024*1024)return 0;
    /* no room: the cached tables of areas left go first (AW_AreaCacheTrim), then once more */
    if(!(a->blob=(byte *)AW_TryMalloc((int)bytes)) &&
       (AW_AreaCacheTrim((long)bytes)<=0 || !(a->blob=(byte *)AW_TryMalloc((int)bytes))))return 0;
    if(fseek(area_file,area_base+(long)offset,SEEK_SET) || fread(a->blob,1,bytes,area_file)!=bytes ||
       memcmp(a->blob,"AWB1",4)){area_free(a);return 0;}
    b=a->blob;a->key=key;a->bytes=(long)bytes;
    a->rows=b[4]|(b[5]<<8);a->owners=b[6]|(b[7]<<8);a->owned=b[8]|(b[9]<<8);a->conts=b[10]|(b[11]<<8);
    a->contents=b[12]|(b[13]<<8);a->items=b[14]|(b[15]<<8);
    need=AREA_HEAD+(long)a->rows*FOCUS_ROW2+(long)a->owners*AREA_OWNER+(long)a->owned*8+(long)a->conts*12+
         (long)a->contents*8+(long)a->items*4;
    if(need+(long)a->items*8>a->bytes || a->rows>FOCUS_ROWS){area_free(a);return 0;}
    a->row=b+AREA_HEAD;a->owner=a->row+a->rows*FOCUS_ROW2;a->own=a->owner+a->owners*AREA_OWNER;
    a->cont=a->own+a->owned*8;a->content=a->cont+a->conts*12;a->itemoff=a->content+a->contents*8;
    /* the pictures' table follows the last item record */
    {long end=need;int i;
     for(i=0;i<a->items;i++){unsigned long o=focus_u32(a->itemoff+i*4);if(o<(unsigned long)need || o+96+6>(unsigned long)a->bytes){area_free(a);return 0;}}
     if(a->items){const byte *p=a->blob+focus_u32(a->itemoff+(a->items-1)*4)+96;int s;
        for(s=0;s<6;s++){p+=1+*p;if(p>a->blob+a->bytes){area_free(a);return 0;}}
        end=p-a->blob;}
     if(end+(long)a->items*8>a->bytes){area_free(a);return 0;}
     a->pic=a->blob+end;
     /* CONTAINER-LEVELLED-CONTENTS-60: the levelled lists after the pictures, named by the record's last 8 bytes
      * (u32 their offset, "AWL1"; tools/prepare_area_tables.py); a record without them has none */
     if(a->bytes>=end+(long)a->items*8+16 && !memcmp(b+a->bytes-4,"AWL1",4)){
        unsigned long o=focus_u32(b+a->bytes-8),stop=(unsigned long)(a->bytes-8),lists,lb,total=0;
        const byte *s=b+o+4;
        if(o>=(unsigned long)(end+(long)a->items*8) && o+8<=stop && !memcmp(b+o,"AWL1",4)){
            /* the lists' bytes: the heads, then the entries up to the last head's (tools/prepare_area_tables.py
             * levelled_block), then the id pool "AWN1" u16 ids, ids x {u8 length, id} */
            lists=(unsigned long)s[0]<<24|(unsigned long)s[1]<<16|(unsigned long)s[2]<<8|s[3];
            if(lists && lists<0x8000 && o+8+lists*8<=stop){
                const byte *h=s+4+(lists-1)*8;
                total=((unsigned long)h[0]<<24|(unsigned long)h[1]<<16|(unsigned long)h[2]<<8|h[3])+(unsigned long)(h[4]<<8|h[5]);
            }
            lb=4+lists*8+total*4;
            if(lists && total<0x100000 && o+4+lb+6<=stop && !memcmp(s+lb,"AWN1",4) && aw_levelled_valid &&
               aw_levelled_valid(s,lb,0x8000u)){
                const byte *p=s+lb+6;int k,ids=s[lb+4]|(s[lb+5]<<8);
                for(k=0;k<ids && p<b+stop;k++)p+=1+*p;
                if(k==ids && p<=b+stop){a->lev=s;a->pool=s+lb+6;a->pool_ids=ids;}
            }
        }
     }}
    return 1;
}
/* a cache slot for an area of NEED bytes: the least recently used ones freed until the cache's bytes allow it */
static int area_cache_slot(long need){
    int i,slot;long bytes;
    for(;;){
        for(bytes=0,i=AREA_MAX;i<AREA_SLOTS;i++)bytes+=areas[i].blob?areas[i].bytes:0;
        for(slot=-1,i=AREA_MAX;i<AREA_SLOTS;i++){
            if(!areas[i].blob){if(slot<0 || areas[slot].blob)slot=i;continue;}
            if(slot<0 || (areas[slot].blob && area_narrow_used[i-AREA_MAX]<area_narrow_used[slot-AREA_MAX]))slot=i;
        }
        if(!areas[slot].blob && bytes+need<=AREA_CACHE_BYTES)return slot;
        /* evict the least recently used one */
        for(slot=-1,i=AREA_MAX;i<AREA_SLOTS;i++)
            if(areas[i].blob && (slot<0 || area_narrow_used[i-AREA_MAX]<area_narrow_used[slot-AREA_MAX]))slot=i;
        if(slot<0)return -1;          /* nothing cached and still too big: not kept */
        area_free(&areas[slot]);
    }
}
static unsigned long area_kept,area_reused;
/* KEEP WHAT YOU CAN AFFORD / A GRADIENT: the memory policy's call when it needs room: cached area tables (the
 * "tables" tier: areas left or narrow-loaded, never the place's own) freed, least recently used first, until WANTED
 * bytes are free or none is left; the bytes freed. The world change list is never touched. */
long AW_AreaCacheTrim(long wanted){
    long freed=0;int i,slot;
    while(freed<wanted){
        for(slot=-1,i=AREA_MAX;i<AREA_SLOTS;i++)
            if(areas[i].blob && (slot<0 || area_narrow_used[i-AREA_MAX]<area_narrow_used[slot-AREA_MAX]))slot=i;
        if(slot<0)break;
        freed+=areas[slot].bytes;area_free(&areas[slot]);
    }
    return freed;
}
/* an area the player left: into the cache (KEEP WHAT YOU CAN AFFORD), else freed */
static void area_keep(area_t *a){
    int slot=a->bytes<=AREA_CACHE_BYTES?area_cache_slot(a->bytes):-1;
    if(slot<0){area_free(a);return;}
    areas[slot]=*a;memset(a,0,sizeof(*a));area_narrow_used[slot-AREA_MAX]=++area_clock;area_kept++;
}
/* the areas of KEYS loaded (those already in memory kept, the others freed); the time and bytes read */
static void area_set(const unsigned long *keys,int n){
    area_t next[AREA_MAX];int i,j,count=0;double t0=Sys_FloatTime();unsigned long bytes=0;
    if(n>AREA_MAX)n=AREA_MAX;
    for(i=0;i<n;i++){
        /* already in memory (a place area, or one narrow-loaded): kept, not read again */
        for(j=0;j<AREA_SLOTS;j++)if(areas[j].blob && areas[j].key==keys[i])break;
        if(j<AREA_SLOTS){next[count++]=areas[j];memset(&areas[j],0,sizeof(area_t));if(j>=AREA_MAX)area_reused++;continue;}
        if(area_read(keys[i],&next[count])){bytes+=(unsigned long)next[count].bytes;count++;area_loads++;}
    }
    /* the areas left: into the cache, not freed (area_keep) */
    for(j=0;j<AREA_MAX;j++)if(areas[j].blob)area_keep(&areas[j]);
    memcpy(areas,next,(size_t)count*sizeof(area_t));area_count=count;
    area_last_seconds=Sys_FloatTime()-t0;area_load_seconds+=area_last_seconds;area_last_bytes=bytes;area_load_bytes+=bytes;
    area_last_count=count;
}
static const area_t *area_of_key(unsigned long key){
    int i;for(i=0;i<area_count;i++)if(areas[i].key==key)return &areas[i];
    return NULL;
}
/* NARROW-LOAD: area N of the index into a narrow slot (the least recently used one replaced); the slot, NULL on a
 * failed read. A place area or a narrow one already in memory is used as it is. */
static const area_t *area_narrow(unsigned long n){
    int i,slot=AREA_MAX;unsigned long key;
    if(!area_index || n>=area_keys)return NULL;
    key=focus_u32(area_index+n*12);
    for(i=0;i<AREA_SLOTS;i++)if(areas[i].blob && areas[i].key==key){
        if(i>=AREA_MAX)area_narrow_used[i-AREA_MAX]=++area_clock;
        return &areas[i];
    }
    {area_t got;
     if(!area_read_at(n,&got))return NULL;
     if((slot=area_cache_slot(got.bytes))<0){area_free(&got);return NULL;}
     areas[slot]=got;}
    area_narrow_used[slot-AREA_MAX]=++area_clock;area_narrow_loads++;area_load_bytes+=(unsigned long)areas[slot].bytes;
    return &areas[slot];
}
static unsigned long area_name_hash(const char *s){
    unsigned long h=2166136261ul;
    for(;*s;s++){unsigned c=(unsigned char)*s;if(c>='A' && c<='Z')c+=32;h=((h^c)*16777619ul)&0xFFFFFFFFul;}
    return h?h:1;
}
static int area_item_find(const area_t *a,const char *id);
/* the directory's area for item ID narrow-loaded: the area, NULL when the directory has none */
static const area_t *area_item_narrow(const char *id){
    unsigned long h=area_name_hash(id);int lo=0,hi=(int)area_dir_items-1,mid;
    if(!area_item_dir)return NULL;
    while(lo<=hi){
        mid=(lo+hi)/2;
        if(focus_u32(area_item_dir+mid*8)<h)lo=mid+1;else hi=mid-1;
    }
    /* every entry of this hash (two ids may share one): the first area that has the id */
    for(;lo<(int)area_dir_items && focus_u32(area_item_dir+lo*8)==h;lo++){
        const byte *e=area_item_dir+lo*8;const area_t *a=area_narrow((unsigned long)(e[4]|(e[5]<<8)));
        if(a && area_item_find(a,id)>=0)return a;
    }
    return NULL;
}
/* the directory's area for container REFERENCE narrow-loaded (one block of the directory read: 2 KiB) */
static const area_t *area_container_narrow(unsigned reference){
    int lo=0,hi=(int)area_cont_blocks-1,mid,block=-1,n;byte rows[AREA_DIR_BLOCK*8];
    if(!area_cont_heads)return NULL;
    while(lo<=hi){
        mid=(lo+hi)/2;
        if(focus_u32(area_cont_heads+mid*4)<=reference){block=mid;lo=mid+1;}else hi=mid-1;
    }
    if(block<0)return NULL;
    n=(int)(area_dir_conts-(unsigned long)block*AREA_DIR_BLOCK);if(n>AREA_DIR_BLOCK)n=AREA_DIR_BLOCK;
    if(fseek(area_file,area_base+(long)area_cont_at+(long)block*AREA_DIR_BLOCK*8,SEEK_SET) ||
       fread(rows,1,(size_t)n*8,area_file)!=(size_t)n*8)return NULL;
    for(lo=0,hi=n-1;lo<=hi;){
        const byte *e=rows+(mid=(lo+hi)/2)*8;unsigned long r=focus_u32(e);
        if(r==reference)return area_narrow((unsigned long)(e[4]|(e[5]<<8)));
        if(r<reference)lo=mid+1;else hi=mid-1;
    }
    return NULL;
}
/* a loaded area's container REFERENCE: its area and record; NULL when no loaded area has it */
static const byte *area_container_in(const area_t *a,unsigned reference){
    int lo,hi,mid;
    for(lo=0,hi=a->conts-1;lo<=hi;){
        const byte *c=a->cont+(mid=(lo+hi)/2)*12;unsigned long r=focus_u32(c);
        if(r==reference)return c;
        if(r<reference)lo=mid+1;else hi=mid-1;
    }
    return NULL;
}
static const byte *area_container_loaded(unsigned reference,const area_t **in);
static const byte *area_container(unsigned reference,const area_t **in){
    const area_t *n;const byte *c;
    /* not in memory: the container directory's area, narrow-loaded */
    if(!(c=area_container_loaded(reference,in)) && (n=area_container_narrow(reference))!=NULL &&
       (c=area_container_in(n,reference))!=NULL)*in=n;
    return c;
}
static const byte *area_container_loaded(unsigned reference,const area_t **in){
    int i,lo,hi,mid;
    for(i=0;i<AREA_SLOTS;i++){
        const area_t *a=&areas[i];
        if(!a->blob)continue;
        for(lo=0,hi=a->conts-1;lo<=hi;){
            const byte *c=a->cont+(mid=(lo+hi)/2)*12;unsigned long r=focus_u32(c);
            if(r==reference){*in=a;return c;}
            if(r<reference)lo=mid+1;else hi=mid-1;
        }
    }
    return NULL;
}
/* the item record K of area A expanded into its items.awi row (prepare_area_tables.py compact_item) */
static int area_item_row(const area_t *a,int k,byte row[INV_ROW]){
    static const short strings[6][2]={{0,64},{64,96},{184,64},{248,64},{312,64},{376,64}};
    const byte *p;int s;
    if(k<0 || k>=a->items)return 0;
    p=a->blob+focus_u32(a->itemoff+k*4);
    memset(row,0,INV_ROW);memcpy(row+160,p,24);memcpy(row+440,p+24,72);p+=96;
    for(s=0;s<6;s++){
        int n=*p++;
        if(n>=strings[s][1] || p+n>a->blob+a->bytes)return 0;
        memcpy(row+strings[s][0],p,(size_t)n);p+=n;
    }
    return 1;
}
/* the folded record id of area A's item K into OUT (at most SIZE bytes with its NUL) */
static int area_item_id(const area_t *a,int k,char *out,int size){
    const byte *p;int n,i;
    if(k<0 || k>=a->items)return 0;
    p=a->blob+focus_u32(a->itemoff+k*4)+96;n=*p++;
    if(n<1 || n>=size)return 0;
    for(i=0;i<n;i++){int c=p[i];if(c<32 || c>126)return 0;out[i]=(char)(c>='A' && c<='Z'?c+32:c);}
    out[n]=0;return 1;
}
/* area item index of ID in area A (its records are in items.awi's order), -1 none */
static int area_item_find(const area_t *a,const char *id){
    int lo=0,hi=a->items-1,mid,cmp;char key[65];
    while(lo<=hi){
        mid=(lo+hi)/2;
        if(!area_item_id(a,mid,key,sizeof(key)))return -1;
        cmp=AW_InventoryCompare(key,id);
        if(!cmp)return mid;
        if(cmp<0)lo=mid+1;else hi=mid-1;
    }
    return -1;
}
/* the area (loaded, else the item directory's, narrow-loaded) that holds item ID's record, and its index there */
static const area_t *area_item_loaded(const char *id,int *k){
    int i;
    if(!area_index)return NULL;
    for(i=0;i<AREA_SLOTS;i++)if(areas[i].blob && (*k=area_item_find(&areas[i],id))>=0)return &areas[i];
    return NULL;
}
static const area_t *area_item_area(const char *id,int *k){
    const area_t *a;
    if(!area_index)return NULL;
    if((a=area_item_loaded(id,k))!=NULL)return a;
    if((a=area_item_narrow(id))!=NULL && (*k=area_item_find(a,id))>=0)return a;
    return NULL;
}
static int area_item(const char *id,aw_inventory_item_t *out){
    int k;byte row[INV_ROW];const area_t *a=area_item_area(id,&k);
    if(a && area_item_row(a,k,row) && inv_parse_row(row,out)){area_hits++;return 1;}
    return 0;
}
/* the strip's picture of an item ("item:<id>") from the loaded areas (aw_icons.c); 0 when none has it */
static int pic_answer(const char *id,int *w,int *h,byte *pixels,int maxw,int maxh);
int AW_AreaIcon(const char *key,int *w,int *h,byte *pixels,int maxw,int maxh){
    int k;
    if(!key || strncmp(key,"item:",5))return 0;
    {
        /* the loaded areas, then the carried items' pictures, then the item directory's area (narrow) */
        const area_t *a=area_item_loaded(key+5,&k);unsigned long o,n;const byte *p;
        if(!a && (k=pic_answer(key+5,w,h,pixels,maxw,maxh))!=0)return k;
        if(!a && !(a=area_item_area(key+5,&k)))return 0;
        o=focus_u32(a->pic+k*8);n=focus_u32(a->pic+k*8+4);
        if(!n){area_hits++;return -1;}        /* the build has no picture of it: known, nothing to search */
        if(o+n>(unsigned long)a->bytes || n<8)return 0;
        p=a->blob+o;
        if(memcmp(p,"AWI1",4))return 0;
        *w=p[4]|(p[5]<<8);*h=p[6]|(p[7]<<8);
        if(*w<1 || *h<1 || *w>maxw || *h>maxh || n!=8+(unsigned long)(*w)*(unsigned long)(*h))return 0;
        memcpy(pixels,p+8,(size_t)(*w)*(size_t)(*h));area_hits++;
        return 1;
    }
    return 0;
}
/* The carried items' strip pictures (the strip's Inventory side): read from the icon pack while an area loads
 * (aw_icons.c's reader through aw_area_picture_read, set by AW_IconsInit), when no loaded area has them, so Tab in
 * the strip searches no file in play. PIC_CACHE entries of at most 32 x 32 (about 1 KiB each), allocated on first
 * use; an item without a picture is kept as known-none. */
#define PIC_CACHE 64
#define PIC_MAX 32
typedef struct {char id[64];short w,h;byte px[PIC_MAX*PIC_MAX];} pic_t;
static pic_t *pic_cache;static int pic_used;
int (*aw_area_picture_read)(const char *key,int *w,int *h,byte *pixels,int maxw,int maxh);
static int pic_find(const char *id){
    int i;for(i=0;i<pic_used;i++)if(!AW_InventoryCompare(pic_cache[i].id,id))return i;
    return -1;
}
static void pic_warm(const char *id){
    char key[72];pic_t *p;int w=0,h=0,k;
    if(!aw_area_picture_read || strlen(id)>=sizeof(p->id) || pic_find(id)>=0)return;
    Q_snprintf(key,sizeof(key),"item:%s",id);
    /* the place's own areas have it (the cache of areas left is not counted on: it may be trimmed) */
    {int i;for(i=0;i<area_count;i++)if((k=area_item_find(&areas[i],id))>=0 && focus_u32(areas[i].pic+k*8+4))return;}
    if(!pic_cache && !(pic_cache=(pic_t *)AW_TryMalloc(PIC_CACHE*sizeof(pic_t))))return;
    if(pic_used>=PIC_CACHE)return;
    p=&pic_cache[pic_used];
    if(!aw_area_picture_read(key,&w,&h,p->px,PIC_MAX,PIC_MAX))w=h=0;
    Q_strcpy_bounded(p->id,id,sizeof(p->id));p->w=(short)w;p->h=(short)h;pic_used++;
}
/* a carried item's picture from the cache: 1 found, -1 known to have none, 0 not cached */
static int pic_answer(const char *id,int *w,int *h,byte *pixels,int maxw,int maxh){
    int i=pic_cache?pic_find(id):-1;const pic_t *p;
    if(i<0)return 0;
    p=&pic_cache[i];
    if(!p->w)return -1;
    if(p->w>maxw || p->h>maxh)return 0;
    *w=p->w;*h=p->h;memcpy(pixels,p->px,(size_t)p->w*(size_t)p->h);area_hits++;
    return 1;
}
/* the icon lookups that had to search gfx/icons.awl in play (aw_icons.c counts them here) */
void AW_AreaIconFallback(const char *key){if(key && !strncmp(key,"item:",5) && !area_loading)area_fallback[3]++;}
/* the owner of REFERENCE in a loaded area: 1 found, 0 not owned there, -1 no loaded area has the reference */
static int area_owner(unsigned reference,char *owner,int *faction){
    int i,j,lo,hi,mid;
    for(i=0;i<AREA_SLOTS;i++){
        const area_t *a=&areas[i];
        if(!a->blob)continue;
        for(lo=0,hi=a->owned-1;lo<=hi;){
            const byte *o=a->own+(mid=(lo+hi)/2)*8;unsigned long r=focus_u32(o);
            if(r==reference){
                if(o[4]>=a->owners)return 0;
                memcpy(owner,a->owner+o[4]*AREA_OWNER,AREA_OWNER);owner[AW_LEDGER_STOLEN_ID]=0;*faction=o[5]&1;
                for(j=0;owner[j];j++)if((unsigned char)owner[j]<32 || (unsigned char)owner[j]>126)return 0;
                return owner[0]!=0;
            }
            if(r<reference)lo=mid+1;else hi=mid-1;
        }
        for(j=0;j<a->rows;j++)if(focus_u32(a->row+j*FOCUS_ROW2+4)==reference)return 0;   /* here, owned by no one */
    }
    /* a container outside the loaded areas: its area narrow-loaded, then asked again (it is in memory now) */
    {static int again;int k;
     if(again || !area_container_narrow(reference))return -1;
     again=1;k=area_owner(reference,owner,faction);again=0;
     return k;}
}
/* the record id of placed item REFERENCE from a loaded area's rows; -1 when no loaded area has it */
static int area_placed_id(unsigned reference,char *id){
    int i,j,k;
    for(i=0;i<AREA_SLOTS;i++)for(j=0;j<areas[i].rows;j++){
        const byte *row=areas[i].row+j*FOCUS_ROW2;
        if(row[0]!='I' || focus_u32(row+4)!=reference)continue;
        memcpy(id,row+FOCUS_ROW,FOCUS_ID);id[FOCUS_ID]=0;
        for(k=0;id[k];k++)if((unsigned char)id[k]<32 || (unsigned char)id[k]>126)id[0]=0;
        return id[0]!=0;
    }
    return -1;
}
/* CONTAINER-LEVELLED-CONTENTS-60: a container's (or a body's) levelled entries are rolled once, on its first open,
 * by the game's rule (OpenMW 0.51 mwmechanics/levelledlist.cpp getLevelledItem and mwworld/containerstore.cpp
 * addInitialItem: the player's level now; chance none; the highest level at or below it, or every level when the
 * list says so; a list inside a list rolled again; "Each" a roll per one of the count, else one roll for the whole
 * count; our own code, the same pick as the levelled creatures, ChimActors_LevelledPick). What it gave goes onto the
 * world change list as put-in items, with the mark LEVELLED_MARK, so it stays across maps and saves; a respawn refill
 * (AW_LedgerContentDrop) drops both and the next open rolls again, as OpenMW's restock does. */
#define LEVELLED_MARK "*levelled"
#define LEVELLED_LIST_BYTES 8         /* chim_actor_table.h CHIM_ACTOR_LIST_BYTES */
unsigned aw_levelled_seed;            /* 0: from the clock at the first roll (tests set it) */
unsigned long aw_levelled_rolls,aw_levelled_items;
/* the CHIM actor table's list code (aw_corpse.c AW_CorpseInit sets them; NULL in the tools' tests: no list is read,
 * levelled entries give nothing) */
int (*aw_levelled_valid)(const unsigned char *s,unsigned long bytes,unsigned items);
int (*aw_levelled_pick)(const unsigned char *s,unsigned index,int level,unsigned *state);
int (*aw_levelled_level)(void);       /* the player's level now (NULL or below 1: 1) */
static void levelled_roll(const area_t *a,unsigned reference,int list,int count,int *rolled){
    unsigned state;int level=aw_levelled_level?aw_levelled_level():1,each,times,i;
    const byte *l;char id[sizeof(((aw_container_item_t *)0)->id)];
    if(level<1)level=1;
    if(!aw_ledger_on || !a->lev || !aw_levelled_pick || count<1)return;
    if(!*rolled){
        if(AW_LedgerContentDelta(&aw_ledger,reference,LEVELLED_MARK)>0){*rolled=-1;return;}
        AW_LedgerContentAdd(&aw_ledger,reference,LEVELLED_MARK,1);*rolled=1;
    }
    if(*rolled<0)return;
    if(!aw_levelled_seed)aw_levelled_seed=(unsigned)(Sys_FloatTime()*1000.0)|1u;
    /* the roll state (as ChimActors_RollSeed): the reference and list mixed with the session's seed */
    state=(unsigned)((((unsigned long)reference^(unsigned long)list<<20^aw_levelled_seed++)*2654435761UL)&0xFFFFFFFFUL);
    if(!state)state=0x9E3779B9u;
    l=a->lev+4+(unsigned long)list*LEVELLED_LIST_BYTES;
    each=(l[7]&2)!=0;times=each?count:1;
    if(times>256)times=256;
    for(i=0;i<times;i++){
        int got=aw_levelled_pick(a->lev,(unsigned)list,level,&state);
        aw_levelled_rolls++;
        if(got<0)continue;
        if(got&0x4000){       /* an id of the pool (its record through the item directory when the strip names it) */
            const byte *p=a->pool;int k=got&0x3FFF,j;
            if(k>=a->pool_ids)continue;
            while(k--)p+=1+*p;
            if(!*p || *p>=(int)sizeof(id))continue;
            for(j=0;j<*p;j++){int c=p[1+j];id[j]=(char)(c>='A' && c<='Z'?c+32:c);}
            id[j]=0;
        }else if(!area_item_id(a,got,id,sizeof(id)))continue;
        if(AW_LedgerContentAdd(&aw_ledger,reference,id,each?1:count))aw_levelled_items+=each?1:(unsigned long)count;
    }
}
/* a loaded area's container contents (as container_base_read): -2 when no loaded area has REFERENCE */
static int area_contents(unsigned reference,aw_container_item_t *out,int max,int *flags,int *lock){
    const area_t *a;const byte *c=area_container(reference,&a);int first,n,i,k,rolled=0;
    if(!c)return -2;
    first=c[4]|(c[5]<<8);n=c[6]|(c[7]<<8);
    if(flags)*flags=c[8]&7;
    if(lock)*lock=c[9];
    if(first+n>a->contents)return -1;
    for(i=k=0;i<n && k<max;i++){
        const byte *e=a->content+(first+i)*8;
        if(e[2]&1){        /* a levelled list's entry: rolled on the first open, its items on the change list */
            if(a->lev && (unsigned long)(e[0]|(e[1]<<8))<((unsigned long)a->lev[0]<<24|(unsigned long)a->lev[1]<<16|
                                                         (unsigned long)a->lev[2]<<8|a->lev[3]))
                levelled_roll(a,reference,e[0]|(e[1]<<8),(int)(int32_t)focus_u32(e+4),&rolled);
            continue;
        }
        if(!area_item_id(a,e[0]|(e[1]<<8),out[k].id,sizeof(out[k].id)))continue;
        out[k].count=(int)(int32_t)focus_u32(e+4);k++;
    }
    return k;
}
/* the container record's own flags (8 trapped, 16 its record respawns); -1 when no loaded area has it */
int AW_AreaContainerFlags(unsigned reference){
    const area_t *a;const byte *c=area_container(reference,&a);
    return c?c[8]:-1;
}
/* aw_placed areas: what is loaded, what it cost, the fallbacks */
void AW_AreaStatus(void){
    int i;unsigned long bytes=0;
    for(i=0;i<area_count;i++)bytes+=(unsigned long)areas[i].bytes;
    Con_Printf("Area tables: %s, %d loaded now (%lu bytes), last load %d areas %lu bytes %d ms; %lu loads, %lu bytes, %d ms in all; "
               "%lu answers from them\n",area_index?"on":"off (no areas.awa)",area_count,bytes,area_last_count,area_last_bytes,
               (int)(area_last_seconds*1000),area_loads,area_load_bytes,(int)(area_load_seconds*1000),area_hits);
    for(i=0;i<area_count;i++)
        Con_Printf("  area %08lx: %d rows, %d containers, %d contents, %d items, %ld bytes\n",areas[i].key,areas[i].rows,
                   areas[i].conts,areas[i].contents,areas[i].items,areas[i].bytes);
    {long cached=0;int n=0;
     for(i=AREA_MAX;i<AREA_SLOTS;i++)if(areas[i].blob){cached+=areas[i].bytes;n++;}
     Con_Printf("Area cache: %d of %d slots, %ld of %ld bytes; %lu areas kept on leaving, %lu taken back without a read, "
                "%lu narrow loads\n",n,AREA_NARROW,cached,AREA_CACHE_BYTES,area_kept,area_reused,area_narrow_loads);}
    Con_Printf("Item records in memory: %d of %d (%d bytes)\n",inv_cache_used,INV_CACHE,(int)(INV_CACHE*sizeof(aw_inventory_item_t)));
    Con_Printf("Fallback searches in play: items.awi %lu, focus.awf containers and owners %lu, placed ids %lu, item pictures %lu\n",
               area_fallback[0],area_fallback[1],area_fallback[2],area_fallback[3]);
}
void AW_AreaStats(unsigned long out[6]){
    out[0]=area_loads;out[1]=area_kept;out[2]=area_reused;out[3]=area_narrow_loads;out[4]=area_load_bytes;
    out[5]=(unsigned long)area_count;
}
unsigned long AW_AreaFallbacks(void){return area_fallback[0]+area_fallback[1]+area_fallback[2]+area_fallback[3];}
/* CELL-CHANGES-59 slice 2: the owner of the placed item REFERENCE, from focus.awf's owner list (AWF3,
 * tools/prepare_focus.py): after the rows, "AWO1" u32 n, n x {u32 reference, u16 name offset, u8 flags (bit 0: a
 * faction), u8 0} ascending, u32 pool bytes, the pool of NUL-ended ids. OWNER gets AW_LEDGER_STOLEN_ID+1 bytes at most;
 * 0 when the file has no list (AWF1/AWF2) or does not name the reference. Read on the take only, nothing resident. */
static int placed_owner(unsigned reference,char *owner,int *faction){
    FILE *f;long base,at,end;unsigned long rooms,n,pool;byte b[12];int lo,hi,mid,i,found=0;
    owner[0]=0;*faction=0;
    if(!(f=focus_open_buffered(&base,&rooms,1)))return 0;
    end=base+focus_length;
    if(!focus_owners || !rooms || fseek(f,base+8+(long)(rooms-1)*12,SEEK_SET) || fread(b,1,12,f)!=12){fclose(f);return 0;}
    at=base+8+(long)rooms*12+(long)(focus_u32(b+4)+focus_u32(b+8))*FOCUS_ROW2;
    if(at+8>end || fseek(f,at,SEEK_SET) || fread(b,1,8,f)!=8 || memcmp(b,"AWO1",4) || (n=focus_u32(b+4))>1048576 ||
       at+8+(long)n*8+4>end){fclose(f);return 0;}
    for(lo=0,hi=(int)n-1;lo<=hi && !found;){
        mid=(lo+hi)/2;
        if(fseek(f,at+8+mid*8L,SEEK_SET) || fread(b,1,8,f)!=8)break;
        if(focus_u32(b)==reference)found=1;else if(focus_u32(b)<reference)lo=mid+1;else hi=mid-1;
    }
    if(found){
        unsigned offset=(unsigned)(b[4]|(b[5]<<8));char name[AW_LEDGER_STOLEN_ID+2];
        *faction=b[6]&1;found=0;
        if(!fseek(f,at+8+(long)n*8,SEEK_SET) && fread(b,1,4,f)==4 && (pool=focus_u32(b))<=65536 &&
           at+12+(long)n*8+(long)pool<=end && offset<pool && !fseek(f,at+12+(long)n*8+offset,SEEK_SET)){
            memset(name,0,sizeof(name));
            if(fread(name,1,sizeof(name)-1,f)>0){
                for(i=0;i<=AW_LEDGER_STOLEN_ID && name[i] && (unsigned char)name[i]>=32 && (unsigned char)name[i]<=126;i++);
                if(i>0 && i<=AW_LEDGER_STOLEN_ID && !name[i]){memcpy(owner,name,(size_t)i+1);found=1;}
            }
        }
    }
    fclose(f);
    return found;
}
/* CELL-CHANGES-59 slice 3: a placed container's contents in the game data, from focus.awf's contents list (after the
 * owners list; tools/prepare_focus.py "AWC1": n x {u32 reference, u32 first, u16 items, u8 flags, u8 0} ascending,
 * u32 items, items x {char id[32], i32 count}). Read on demand (nothing resident); -1 when the file has no list or
 * does not name REFERENCE (not a container), else the entries (at most MAX) in OUT. */
static int container_base_read(unsigned reference,aw_container_item_t *out,int max,int *flags){
    FILE *f;long base,at,end;unsigned long rooms,n,pool,items,first=0;byte b[12];int lo,hi,mid,found=0,k=-1,i,j;
    if(flags)*flags=0;
    if(!(f=focus_open_buffered(&base,&rooms,1)))return -1;
    end=base+focus_length;
    if(!focus_owners || !rooms || fseek(f,base+8+(long)(rooms-1)*12,SEEK_SET) || fread(b,1,12,f)!=12)goto done;
    at=base+8+(long)rooms*12+(long)(focus_u32(b+4)+focus_u32(b+8))*FOCUS_ROW2;
    if(at+8>end || fseek(f,at,SEEK_SET) || fread(b,1,8,f)!=8 || memcmp(b,"AWO1",4) || (n=focus_u32(b+4))>1048576 ||
       at+12+(long)n*8>end || fseek(f,at+8+(long)n*8,SEEK_SET) || fread(b,1,4,f)!=4 || (pool=focus_u32(b))>65536)goto done;
    at+=12+(long)n*8+(long)pool;
    if(at+8>end || fseek(f,at,SEEK_SET) || fread(b,1,8,f)!=8 || memcmp(b,"AWC1",4) || (n=focus_u32(b+4))>1048576 ||
       at+12+(long)n*12>end)goto done;
    for(lo=0,hi=(int)n-1;lo<=hi && !found;){
        mid=(lo+hi)/2;
        if(fseek(f,at+8+mid*12L,SEEK_SET) || fread(b,1,12,f)!=12)goto done;
        if(focus_u32(b)==reference)found=1;else if(focus_u32(b)<reference)lo=mid+1;else hi=mid-1;
    }
    if(!found)goto done;
    first=focus_u32(b+4);k=b[8]|(b[9]<<8);if(flags)*flags=b[10];
    if(fseek(f,at+8+(long)n*12,SEEK_SET) || fread(b,1,4,f)!=4 || first+k>(items=focus_u32(b)) ||
       at+12+(long)n*12+(long)items*36>end){k=-1;goto done;}
    if(k>max)k=max;
    for(i=0;i<k;i++){
        byte row[FOCUS_ID+4];
        if(fseek(f,at+12+(long)n*12+(long)(first+i)*36,SEEK_SET) || fread(row,1,sizeof(row),f)!=sizeof(row)){k=i;break;}
        memcpy(out[i].id,row,FOCUS_ID);out[i].id[FOCUS_ID]=0;
        for(j=0;out[i].id[j];j++)if((unsigned char)out[i].id[j]<32 || (unsigned char)out[i].id[j]>126)out[i].id[0]=0;
        out[i].count=(int)(int32_t)focus_u32(row+FOCUS_ID);
    }
done:
    fclose(f);
    return k;
}
/* CONTAINER-STRIP-TAKE-STALL-59: while the strip holds a container open, the data's contents and its owner are read
 * once (AW_ContainerHold) and kept until it closes (AW_ContainerRelease; a new map releases it too). Before, every take
 * or put read focus.awf five times by binary search (each step a seek and a buffer refill on the game disk) and the
 * strip's fill once more: a take could hold the frame for seconds on a busy disk. Nothing is resident while closed. */
typedef struct {
    unsigned reference;const model_t *world;int n,flags,owner_found,faction;
    char owner[AW_LEDGER_STOLEN_ID+1];aw_container_item_t items[AW_CONTAINER_ITEMS];
} container_hold_t;
static container_hold_t *container_held;
static unsigned long container_file_reads;   /* focus.awf container reads (the native test counts them) */
unsigned long AW_ContainerFileReads(void){return container_file_reads;}
static const container_hold_t *container_hold_of(unsigned reference){
    return container_held && container_held->reference==reference && container_held->world==sv.worldmodel?container_held:NULL;
}
static int container_base(unsigned reference,aw_container_item_t *out,int max,int *flags){
    const container_hold_t *h=container_hold_of(reference);int k;
    if(!h){
        /* AREA-TABLES-59: the loaded area's record; a container no loaded area has searches focus.awf */
        if((k=area_contents(reference,out,max,flags,NULL))!=-2)return k;
        if(!area_loading)area_fallback[1]++;
        container_file_reads++;return container_base_read(reference,out,max,flags);
    }
    if(flags)*flags=h->flags;
    if(h->n<0)return -1;
    k=h->n<max?h->n:max;
    if(k>0)memcpy(out,h->items,(size_t)k*sizeof(*out));
    return k;
}
static int container_owner(unsigned reference,char *owner,int *faction){
    const container_hold_t *h=container_hold_of(reference);int k;
    if(!h){
        if((k=area_owner(reference,owner,faction))>=0)return k;
        if(!area_loading)area_fallback[1]++;
        container_file_reads++;return placed_owner(reference,owner,faction);
    }
    memcpy(owner,h->owner,sizeof(h->owner));*faction=h->faction;
    return h->owner_found;
}
void AW_ContainerRelease(void){
    if(container_held){free(container_held);container_held=NULL;}
}
int AW_ContainerHold(unsigned reference){
    container_hold_t *h;
    AW_ContainerRelease();
    if(!(h=(container_hold_t *)AW_TryMalloc(sizeof(*h))))return 0;     /* no room: the reads stay per take */
    memset(h,0,sizeof(*h));
    h->reference=reference;h->world=sv.worldmodel;
    /* AREA-TABLES-59: from the loaded area (no file read); else focus.awf as before, counted as a fallback */
    if((h->n=area_contents(reference,h->items,AW_CONTAINER_ITEMS,&h->flags,NULL))!=-2 &&
       (h->owner_found=area_owner(reference,h->owner,&h->faction))>=0){container_held=h;return 1;}
    if(!area_loading)area_fallback[1]++;
    container_file_reads+=2;
    h->n=container_base_read(reference,h->items,AW_CONTAINER_ITEMS,&h->flags);
    h->owner_found=placed_owner(reference,h->owner,&h->faction);
    container_held=h;
    return 1;
}
/* the game's ids are case-blind */
static int same_id_ci(const char *a,const char *b){
    for(;*a && *b;a++,b++){
        int x=(unsigned char)*a,y=(unsigned char)*b;
        if(x>='A' && x<='Z')x+=32;
        if(y>='A' && y<='Z')y+=32;
        if(x!=y)return 0;
    }
    return *a==*b;
}
/* The contents now: the data's list with the world change list's deltas (an entry at 0 or below is gone), then what
 * was put in that the data has none of. -1 when REFERENCE is no container of focus.awf. */
int AW_ContainerContents(unsigned reference,aw_container_item_t *out,int max,int *flags){
    int n=container_base(reference,out,max,flags),i,k,first,m;
    if(n<0)return -1;
    for(i=k=0;i<n;i++){
        if(!out[i].id[0])continue;
        out[i].count+=aw_ledger_on?AW_LedgerContentDelta(&aw_ledger,reference,out[i].id):0;
        if(out[i].count>0)out[k++]=out[i];
    }
    if(!aw_ledger_on)return k;
    m=AW_LedgerContentOf(&aw_ledger,reference,&first);
    for(i=first;i<first+m && k<max;i++){
        int j;const aw_ledger_content_t *c=&aw_ledger.content[i];
        if(c->count<=0 || c->item[0]=='*')continue;     /* LEVELLED_MARK: the rolled mark, no item */
        for(j=0;j<n;j++)if(same_id_ci(out[j].id,c->item))break;
        if(j<n)continue;            /* a data entry: counted above */
        Q_strcpy_bounded(out[k].id,c->item,sizeof(out[k].id));out[k].count=c->count;k++;
    }
    return k;
}
int AW_ContainerCount(unsigned reference,const char *id){
    aw_container_item_t items[AW_CONTAINER_ITEMS];int n=AW_ContainerContents(reference,items,AW_CONTAINER_ITEMS,NULL),i;
    for(i=0;i<n;i++)if(same_id_ci(items[i].id,id))return items[i].count;
    return n<0?-1:0;
}
/* COUNT (> 0 put in, < 0 taken out) of ID into container REFERENCE on the world change list; what was moved (taking
 * stops at what it holds). OWNER_MARK: a take from an owned container is stolen from its owner (slice 2's pairs).
 * The player's inventory is not touched here (the console's take and put do that). */
int AW_ContainerChange(unsigned reference,const char *id,int count,int owner_mark){
    int have=AW_ContainerCount(reference,id);
    if(have<0 || !aw_ledger_on || !count || !id || !id[0])return 0;
    if(count<0 && -count>have)count=-have;
    if(!count)return 0;
    AW_LedgerContentAdd(&aw_ledger,reference,id,count);
    if(count<0 && owner_mark){
        char owner[AW_LEDGER_STOLEN_ID+1];int faction;
        if(container_owner(reference,owner,&faction))AW_LedgerStolenAdd(&aw_ledger,id,owner,faction,-count);
    }
    return count<0?-count:count;
}
/* CONTAINER-WINDOW-59: COUNT of ID out of container REFERENCE into the player's inventory (OWNED: stolen from its
 * owner, the pair on the change list), or from the inventory into it; what moved, 0 when refused with nothing changed
 * (*why: "capacity", "none", "item", "carry", "kept"). Shared by the strip and the console. */
int AW_ContainerTake(unsigned reference,const char *id,int count,int owned,const char **why){
    aw_inventory_item_t item;int have,moved;
#ifdef AMIGA
    /* TRADEHOUSE-LONG-FRAME-59: the parts of a take timed; one console line when it passes 100 ms */
    double t[6];t[0]=Sys_FloatTime();
#define TAKE_MARK(k) (t[k]=Sys_FloatTime())
#else
#define TAKE_MARK(k) ((void)0)
#endif
    if(why)*why="item";
    if(count<1 || !id || !AW_InventoryRead(id,&item))return 0;
    TAKE_MARK(1);
    have=AW_ContainerCount(reference,item.id);if(count>have)count=have;
    TAKE_MARK(2);
    if(count<1){if(why)*why="none";return 0;}
    if(!AW_ItemAdd(&aw_state,item.id,count)){if(why)*why="capacity";return 0;}
    TAKE_MARK(3);
    moved=AW_ContainerChange(reference,item.id,-count,owned);
    TAKE_MARK(4);
    if(moved<count)AW_ItemAdd(&aw_state,item.id,moved-count);
    if(!moved){if(why)*why="kept";return 0;}
    aw_state.inventory.initialized=1;AW_CombatEquipmentChanged();
    TAKE_MARK(5);
#ifdef AMIGA
    if(t[5]-t[0]>=.1)Con_Printf("Slow take: %ld ms (item %ld, count %ld, add %ld, change %ld, equipment %ld)\n",
        (long)((t[5]-t[0])*1000),(long)((t[1]-t[0])*1000),(long)((t[2]-t[1])*1000),(long)((t[3]-t[2])*1000),
        (long)((t[4]-t[3])*1000),(long)((t[5]-t[4])*1000));
#endif
#undef TAKE_MARK
    return moved;
}
int AW_ContainerPut(unsigned reference,const char *id,int count,const char **why){
    aw_inventory_item_t item;int32_t carried;
    if(why)*why="item";
    if(count<1 || !id || !AW_InventoryRead(id,&item))return 0;
    carried=AW_StateGet(&aw_state,AW_ITEM,item.id);
    if(carried<count){if(why)*why="carry";return 0;}
    if(!AW_ContainerChange(reference,item.id,count,0)){if(why)*why="kept";return 0;}
    AW_ItemAdd(&aw_state,item.id,-count);
    /* the last one put away is no longer worn or held */
    if(carried==count)AW_InventoryUnequip(&aw_state,item.id);
    AW_CombatEquipmentChanged();
    return count;
}
static int placed_target(void);
static void focus_refresh(const edict_t *p);
/* The container the console acts on: the aimed one, else the nearest container row of this room or cell. */
static focus_row_t *container_row(void){
    int i,best=placed_target();float d,nearest=1e30f,shift[3];vec3_t at,delta;edict_t *p;
    if(best>=0 && focus_rows[best].kind=='C')return &focus_rows[best];
    if(!sv.active || !svs.clients || !(p=svs.clients[0].edict))return NULL;
    focus_refresh(p);
    if(focus_outdoor)shift[0]=shift[1]=shift[2]=0;else AW_MwscriptRoomShift(shift);
    for(best=-1,i=0;i<focus_count;i++){
        if(focus_rows[i].kind!='C')continue;
        VectorAdd(focus_rows[i].at,shift,at);VectorSubtract(at,p->v.origin,delta);d=DotProduct(delta,delta);
        if(d<nearest){nearest=d;best=i;}
    }
    return best<0?NULL:&focus_rows[best];
}
/* CONTAINER-WINDOW-59: the strip (aw_cstrip.c sets these; NULL as in the tools' tests: E opens nothing, the data's
 * lock level stands). */
int (*aw_container_open)(unsigned reference,const char *name,int owned);
int (*aw_container_lock)(unsigned reference,int original);
/* the lock level now: a script's Lock / Unlock on the world change list (slice 2), else the data's */
static int container_lock(const focus_row_t *row){
    return aw_container_lock?aw_container_lock(row->reference,row->lock):row->lock;
}
/* a container that opens (not organic): its strip, or the locked line; 1 when E was used here */
static int container_open(const focus_row_t *row){
    static char line[64];
    if(row->kind!='C' || (row->action&3)!=FOCUS_ACT_TAKE)return 0;
    if(container_lock(row)>0){
        if(!line[0] && !hud_setting("sLocked",line,sizeof(line)))strcpy(line,"Locked");
        AW_UISubtitle(row->name,line,3);return 1;
    }
    return aw_container_open && aw_container_open(row->reference,row->name,row->owned!=0);
}
/* aw_placed container [open | aim [N] | take ID [N] | put ID [N] | all] (CELL-CHANGES-59 slice 3,
 * CONTAINER-WINDOW-59): the aimed or nearest container's contents now, its strip opened, the view put in front of it
 * (or the N-th of the room), a take into the inventory (owned: stolen), a put from it; all: every container delta on
 * the world change list. */
void AW_ContainerCommand(void){
    const char *a=Cmd_Argc()>2?Cmd_Argv(2):"";focus_row_t *row;aw_container_item_t items[AW_CONTAINER_ITEMS];
    int n,i,flags,o=0,count;
    /* slice 7: aw_placed container REF ... acts on the container of that reference among this place's rows */
    if(a[0]>='0' && a[0]<='9'){
        unsigned want=(unsigned)strtoul(a,NULL,10);row=NULL;
        if(sv.active && svs.clients && svs.clients[0].edict)focus_refresh(svs.clients[0].edict);
        for(i=0;i<focus_count;i++)if(focus_rows[i].kind=='C' && focus_rows[i].reference==want)row=&focus_rows[i];
        if(!row){Con_Printf("aw_placed container: no container %u in this room or cell.\n",want);return;}
        o=1;a=Cmd_Argc()>3?Cmd_Argv(3):"";
    }else row=NULL;
    count=Cmd_Argc()>4+o?atoi(Cmd_Argv(4+o)):1;
    if(!strcmp(a,"all")){
        Con_Printf("Container deltas on the world change list: %d\n",aw_ledger.content_count);
        for(i=0;i<aw_ledger.content_count;i++)
            Con_Printf("  container %u: %s %+d\n",(unsigned)aw_ledger.content[i].key,aw_ledger.content[i].item,
                       (int)aw_ledger.content[i].count);
        return;
    }
    if(!row && !(row=container_row())){Con_Printf("aw_placed container: no container in this room or cell.\n");return;}
    /* CONTAINER-WINDOW-59: open the strip on it (as E would, locks and all) */
    if(!strcmp(a,"open")){
        if(!container_open(row))Con_Printf("aw_placed container: %s does not open here.\n",row->name);
        return;
    }
    /* aim (for in-game checks; noclip on): stand 36 units from it on the player's side, at the player's height,
     * looking at it, as aw_view would place the camera */
    if(!strcmp(a,"aim")){
        edict_t *p=svs.clients?svs.clients[0].edict:NULL;vec3_t at,shift,d;float yaw,pitch;
        if(!p || p->v.movetype!=MOVETYPE_NOCLIP){Con_Printf("Enable noclip, then aw_placed container aim [N]\n");return;}
        if(Cmd_Argc()>3+o){   /* the N-th container of the room or cell (0 first), in the table's order */
            int want=atoi(Cmd_Argv(3+o)),k;
            for(i=k=0;i<focus_count;i++)if(focus_rows[i].kind=='C' && k++==want){row=&focus_rows[i];break;}
            if(i==focus_count){Con_Printf("aw_placed container aim: %d containers here.\n",k);return;}
        }
        if(focus_outdoor)shift[0]=shift[1]=shift[2]=0;else AW_MwscriptRoomShift(shift);
        VectorAdd(row->at,shift,at);
        /* a clear standing spot 40 units away (its feet on the container's floor), the side towards the player first,
         * then round it, from where the container is in view */
        {
            /* sixteen directions, a sixteenth of a turn apart (no sin/cos: the 68040 lacks them) */
            float dx=p->v.origin[0]-at[0],dy=p->v.origin[1]-at[1],len=(float)sqrt(dx*dx+dy*dy),t;int k;vec3_t spot,eye;trace_t tr;
            if(len<1){dx=1;dy=0;len=1;}
            dx/=len;dy/=len;
            for(k=0;k<16;k++,t=dx*0.92388f-dy*0.38268f,dy=dx*0.38268f+dy*0.92388f,dx=t){
                int up;
                spot[0]=at[0]+dx*40;spot[1]=at[1]+dy*40;
                /* the lowest height the player's box fits at (under a low ceiling too) */
                for(up=8;up<=48;up+=4){
                    spot[2]=at[2]+(float)up;
                    tr=SV_Move(spot,p->v.mins,p->v.maxs,spot,MOVE_NOMONSTERS,p);
                    if(!tr.startsolid && !tr.allsolid)break;
                }
                if(up>48)continue;
                VectorCopy(spot,eye);eye[2]+=p->v.view_ofs[2];
                tr=SV_Move(eye,vec3_origin,vec3_origin,at,MOVE_NOMONSTERS,p);
                if(tr.fraction<1 && (1-tr.fraction)*40>6)continue;
                break;
            }
            if(k==16){
                /* DBG-CONTAINER-AIM-NO-SPOT-59: no spot the room collision accepts (a basket against a counter): stay
                 * in noclip 40 units from it on the player's side, at eye height over it, still looking at it, so E
                 * on it can be checked; leaving noclip there may need dbg unstuck */
                dx=p->v.origin[0]-at[0];dy=p->v.origin[1]-at[1];len=(float)sqrt(dx*dx+dy*dy);
                if(len<1){dx=1;dy=0;len=1;}
                spot[0]=at[0]+dx/len*40;spot[1]=at[1]+dy/len*40;spot[2]=at[2]+8;
                Con_Printf("aw_placed container aim: no clear spot round %s; placed in noclip.\n",row->name);
            }
            VectorCopy(spot,p->v.origin);d[0]=at[0]-spot[0];d[1]=at[1]-spot[1];
            yaw=(float)(atan2(d[1],d[0])*180/M_PI);
            /* the crosshair on the container's own point when placed in noclip (the aim takes it within 6 units) */
            pitch=(float)(atan2(spot[2]+p->v.view_ofs[2]-(at[2]+(k==16?0:8)),40)*180/M_PI);
        }
        Con_Printf("container at %d %d %d (room shift %d %d %d)\n",(int)at[0],(int)at[1],(int)at[2],(int)shift[0],
                   (int)shift[1],(int)shift[2]);
        if(pitch>70)pitch=70;
        VectorCopy(vec3_origin,p->v.velocity);p->v.angles[0]=pitch;p->v.angles[1]=yaw;p->v.angles[2]=0;
        p->v.fixangle=1;SV_LinkEdict(p,false);
        Con_Printf("Aimed at %s (container %u): aw_view %d %d %d %d %d\n",row->name,row->reference,(int)p->v.origin[0],
                   (int)p->v.origin[1],(int)p->v.origin[2],(int)yaw,(int)pitch);
        return;
    }
    if((!strcmp(a,"take") || !strcmp(a,"put")) && Cmd_Argc()>3+o){
        const char *id=Cmd_Argv(3+o),*why="";int moved;
        if(!strcmp(a,"take")){
            if(!(moved=AW_ContainerTake(row->reference,id,count,row->owned,&why))){
                Con_Printf("aw_placed container: %s not taken (%s).\n",id,why);return;}
            Con_Printf("Took %d %s from %s (container %u)%s.\n",moved,id,row->name,row->reference,row->owned?", stolen":"");
        }else{
            if(!AW_ContainerPut(row->reference,id,count,&why)){Con_Printf("aw_placed container: %s not put (%s).\n",id,why);return;}
            Con_Printf("Put %d %s into %s (container %u).\n",count,id,row->name,row->reference);
        }
    }
    n=AW_ContainerContents(row->reference,items,AW_CONTAINER_ITEMS,&flags);
    Con_Printf("Container %u, %s%s: %d kinds of item%s%s%s, lock %d\n",row->reference,row->name,row->owned?" (owned)":"",
               n<0?0:n,flags&1?", a merchant's restocking entry":"",flags&2?", a levelled list left as the data has it":"",
               flags&4?", organic (harvested)":"",container_lock(row));
    for(i=0;i<n;i++)Con_Printf("  %s %d (change %+d)\n",items[i].id,items[i].count,
                               AW_LedgerContentDelta(&aw_ledger,row->reference,items[i].id));
    if(n>=0){
        aw_refs_t *r=AW_PlacedRefs();uint32_t refs_flags=0;
        if(r && AW_RefsFind(r,row->reference,NULL,&refs_flags))
            Con_Printf("  %s; game hours now %.1f\n",refs_flags&AW_REFS_RESPAWN?
                       "its record is flagged Respawn: it refills when its place is entered iMonthsToRespawn months after the place's last refill":
                       "its record does not respawn: it never refills",AW_LedgerGameHours());
    }
}
/* CELL-CHANGES-59 slice 7: the build's reference identity table, focus.awf's last section (aw_ledger.h AWI1, after
 * the AWC1 contents list); opened on first use and kept open (one file handle; the block index resident, one block
 * of rows read per lookup outside the block in hand). */
static aw_refs_t refs;
static int refs_tried;
static FILE *refs_file;
static long refs_base;
static int refs_read(void *context,long at,void *out,long bytes){
    (void)context;
    return !refs_file || fseek(refs_file,refs_base+at,SEEK_SET) || fread(out,1,(size_t)bytes,refs_file)!=(size_t)bytes;
}
aw_refs_t *AW_PlacedRefs(void){
    long base,at,end;unsigned long rooms,n,pool,items;byte b[12];
    if(refs_tried)return refs.read?&refs:NULL;
    refs_tried=1;
    if(!(refs_file=focus_open_buffered(&base,&rooms,1)))return NULL;   /* random reads only (refs_read) */
    end=base+focus_length;refs_base=base;
    /* after the rows: the owners list (AWO1), the contents list (AWC1), then the table */
    if(!focus_owners || !rooms || fseek(refs_file,base+8+(long)(rooms-1)*12,SEEK_SET) || fread(b,1,12,refs_file)!=12)goto none;
    at=base+8+(long)rooms*12+(long)(focus_u32(b+4)+focus_u32(b+8))*FOCUS_ROW2;
    if(at+8>end || fseek(refs_file,at,SEEK_SET) || fread(b,1,8,refs_file)!=8 || memcmp(b,"AWO1",4) || (n=focus_u32(b+4))>1048576 ||
       at+12+(long)n*8>end || fseek(refs_file,at+8+(long)n*8,SEEK_SET) || fread(b,1,4,refs_file)!=4 || (pool=focus_u32(b))>65536)goto none;
    at+=12+(long)n*8+(long)pool;
    if(at+8>end || fseek(refs_file,at,SEEK_SET) || fread(b,1,8,refs_file)!=8 || memcmp(b,"AWC1",4) || (n=focus_u32(b+4))>1048576 ||
       at+12+(long)n*12>end || fseek(refs_file,at+8+(long)n*12,SEEK_SET) || fread(b,1,4,refs_file)!=4 ||
       (items=focus_u32(b))>4194304)goto none;
    at+=12+(long)n*12+(long)items*36;
    if(at<end && AW_RefsOpen(&refs,refs_read,NULL,at-base,end-base)){
        Con_Printf("Reference identity table: %lu references of %d content files (respawn: %d months, corpses %.0f / %.0f hours)\n",
                   (unsigned long)refs.rows,refs.file_count,refs.respawn.months,refs.respawn.respawn_delay,refs.respawn.clear_delay);
        return &refs;
    }
none:
    Con_Printf("No reference identity table in focus.awf: no respawn by record flags, a save of other game data is refused.\n");
    fclose(refs_file);refs_file=NULL;memset(&refs,0,sizeof(refs));
    return NULL;
}
/* the game hours now: the clock's saved globals (aw_clock.c), 0 before it runs */
float AW_LedgerGameHours(void){
    if(AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:ready")!=1)return 0;
    return AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:days")*24.0f+
           AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:clock:ms")/3600000.0f;
}
static int refs_lookup(void *context,uint32_t key,uint32_t *record){
    return AW_RefsFind((aw_refs_t *)context,key,record,NULL);
}
static int item_known(void *context,const char *id){
    aw_inventory_item_t item;(void)context;
    return id && id[0] && (id[0]=='*' || AW_InventoryRead(id,&item));   /* '*': LEVELLED_MARK */
}
/* A save is written: the record hash of every reference the list names, and the content files (aw_save.c). */
void AW_PlacedIdentRefresh(aw_ledger_t *l){
    aw_refs_t *r=AW_PlacedRefs();
    if(!r)return;
    AW_LedgerIdentRefresh(l,refs_lookup,r);
    AW_LedgerFilesSet(l,r->file,r->file_count);
}
/* A save of other game data is loaded (aw_save.c): its list migrated (aw_ledger.h AW_LedgerMigrate); -1 no table here
 * (the save is refused), else the changes dropped. */
long AW_PlacedMigrate(aw_ledger_t *l,void *dropped){
    aw_refs_t *r=AW_PlacedRefs();
    if(!r)return -1;
    return (long)AW_LedgerMigrate(l,r->file,r->file_count,refs_lookup,r,item_known,(aw_ledger_dropped_t *)dropped);
}
/* The refill flag of a placed reference (AW_REFS_RESPAWN, AW_REFS_LEVELLED; 0 none or unknown) for aw_actors.c. */
uint32_t AW_PlacedRefFlags(uint32_t key){
    aw_refs_t *r=AW_PlacedRefs();uint32_t flags=0;
    return r && AW_RefsFind(r,key,NULL,&flags)?flags:0;
}
/* A place's rows were read (rows FIRST .. LAST-1 of focus_rows, the table KEY): when its respawning containers are
 * due (aw_ledger.h AW_LedgerRespawnPlace), the deltas of each container of the place whose record is flagged Respawn
 * go: it holds what the game data gives it again (OpenMW 0.51 CellStore::respawn, Container::respawn). */
static void focus_respawn(unsigned long key,int first,int last){
    aw_refs_t *r;int at,i,k;int32_t where;uint32_t flags;
    if(!aw_ledger_on || !(r=AW_PlacedRefs()))return;
    if(key&0x80000000ul){
        int gx=(int)((key>>12)&0xFFF)-FOCUS_GRID_BIAS,gy=(int)(key&0xFFF)-FOCUS_GRID_BIAS;
        at=AW_AT_CELL;where=(int32_t)(((uint32_t)(gx&0xFFFF)<<16)|(uint32_t)(gy&0xFFFF));
    }else{at=AW_AT_ROOM;where=(int32_t)key;}
    if(!AW_LedgerRespawnPlace(&aw_ledger,at,where,AW_LedgerGameHours(),r->respawn.months))return;
    aw_ledger_events.places++;
    for(i=first;i<last;i++){
        if(focus_rows[i].kind!='C' || !AW_LedgerContentOf(&aw_ledger,focus_rows[i].reference,&k))continue;
        flags=0;
        /* AREA-TABLES-59: the area's container record says whether its record respawns (no table search) */
        {int c=AW_AreaContainerFlags(focus_rows[i].reference);
         if(c>=0){if(!(c&16))continue;}
         else if(!AW_RefsFind(r,focus_rows[i].reference,NULL,&flags) || !(flags&AW_REFS_RESPAWN))continue;}
        if(AW_LedgerContentDrop(&aw_ledger,focus_rows[i].reference)){
            aw_ledger_events.containers++;
            Con_Printf("Respawn: %s (container %u) holds its game-data contents again.\n",focus_rows[i].name,
                       focus_rows[i].reference);
        }
    }
}
/* WORLD-OBJECT-PLACEMENT-59: the items the original placed in a room or an exterior cell, drawn by reference to the
 * shared item model table (progs/items/placed.awp, tools/prepare_item_models.py pack_placed). Only focus rows the map
 * does not draw itself get one (a CHIM room's own placement or a compiled room's edict stay theirs), so the aim box,
 * E and the object state (taken or disabled: not drawn) work on them as on any placed item. The list is read here
 * with the focus rows; the drawing (client entities, the per-level model room) is aw_placed.c, reached through
 * aw_placed_admit (NULL: nothing drawn, as in the tools' tests). */
/* Map units <-> the original game's coordinates outdoors: an open-world region map, else the loaded CHIM frame (the
 * shared conversion, aw_world.c: the region table first, then the frame; CHIM-FRAME-SOURCE-CONVERSION-59). */
static int focus_to_source(const float *local,float *game){
    return AW_WorldToSource(sv.name,local,game);
}
static int focus_to_local(const float *game,float *local){
    return AW_SourceToWorld(sv.name,game,local);
}
/* CELL-CHANGES-59 (aw_ledger.h): the place of a map position for the world change list. Outdoors (an open-world
 * region or the loaded CHIM frame: one rule for every frame) the exterior cell and the original's game units, so any
 * map that shows the spot finds it; in a numbered room the room and the room's own game units (the map's quarter
 * scale and shift taken off, the scripts' rule); else the scene id and map units. */
int AW_PlacedWhere(const float *local,int *at,int32_t *where,float *game){
    float g[3];long room;int scene,i;vec3_t shift;
    if(focus_to_source(local,g)){
        int cx=(int)floor(g[0]/FOCUS_CELL),cy=(int)floor(g[1]/FOCUS_CELL);
        if(cx<-1024 || cx>1024 || cy<-1024 || cy>1024)return 0;
        *at=AW_AT_CELL;*where=(int32_t)(((uint32_t)(cx&0xffff)<<16)|(uint32_t)(cy&0xffff));
        if(game)VectorCopy(g,game);
        return 1;
    }
    if((room=focus_room())>0){
        AW_MwscriptRoomShift(shift);
        *at=AW_AT_ROOM;*where=(int32_t)room;
        if(game)for(i=0;i<3;i++)game[i]=(local[i]-shift[i])*4;
        return 1;
    }
    if((scene=AW_MapId(sv.name))>=0 && scene<=0xFFFF){*at=AW_AT_SCENE;*where=scene;if(game)VectorCopy(local,game);return 1;}
    return 0;
}
/* The other way: a row's position on this map, 0 when its place is not on this map (outdoors: the spot converts and
 * lies inside this map's world, not in its solid outside). */
int AW_PlacedLocal(int at,int32_t where,const float *game,float *local){
    long room;vec3_t shift;int i;
    switch(at){
    case AW_AT_CELL:
        if(!focus_to_local(game,local))return 0;
        for(i=0;i<3;i++)if(!(local[i]>-32000 && local[i]<32000))return 0;
        return SV_PointContents(local)!=CONTENTS_SOLID;
    case AW_AT_ROOM:
        if((room=focus_room())<=0 || room!=where)return 0;
        AW_MwscriptRoomShift(shift);
        for(i=0;i<3;i++)local[i]=game[i]*.25f+shift[i];
        return 1;
    case AW_AT_SCENE:
        if(where!=AW_MapId(sv.name))return 0;
        VectorCopy(game,local);
        return 1;
    }
    return 0;
}
#define PLACED_ROW 48
#define PLACED_FILE "progs/items/placed.awp"
int (*aw_placed_begin)(void);
int (*aw_placed_admit)(unsigned reference,const char *stem,const float local[3],const float angles[3],float scale);
/* What the last read of the list saw (aw_placed status): keys read, rows, rows without an item row in the focus table,
 * rows the map draws itself, rows outside this map, rows offered. */
static int placed_seen[6];
void AW_PlacedReadStats(int out[6]){memcpy(out,placed_seen,sizeof(placed_seen));out[0]=focus_outdoor?-out[0]:out[0];}
/* One key's rows: each row whose reference is an item row of the focus table that nothing draws is offered. */
static int placed_read_key(FILE *f,long base,unsigned long keys,long length,unsigned long key){
    byte head[16],row[PLACED_ROW];int lo,hi,mid,i,j,k,refused=0;unsigned long number,first=0,rows=0,bits;
    for(lo=0,hi=(int)keys-1;lo<=hi;){
        mid=(lo+hi)/2;
        if(fseek(f,base+8+mid*16L,SEEK_SET) || fread(head,1,16,f)!=16)return 0;
        number=focus_u32(head);
        if(number==key){first=focus_u32(head+4);rows=focus_u32(head+8);break;}
        if(number<key)lo=mid+1;else hi=mid-1;
    }
    if(!rows || rows>FOCUS_ROWS || 8+keys*16+(first+rows)*PLACED_ROW>(unsigned long)length ||
       fseek(f,base+8+(long)keys*16+(long)first*PLACED_ROW,SEEK_SET))return 0;
    placed_seen[0]++;placed_seen[1]+=(int)rows;
    for(i=0;i<(int)rows;i++){
        unsigned reference;float v[6],scale;vec3_t local;char stem[17];
        if(fread(row,1,PLACED_ROW,f)!=PLACED_ROW)break;
        reference=(unsigned)focus_u32(row);
        for(j=0;j<focus_count;j++)if(focus_rows[j].kind=='I' && focus_rows[j].reference==reference)break;
        /* indoors only an item the room does not draw (edict set by focus_load); outdoors every item row */
        if(j==focus_count){placed_seen[2]++;continue;}
        if(focus_rows[j].drawn || focus_rows[j].live || (!focus_outdoor && !focus_rows[j].edict)){placed_seen[3]++;continue;}
        for(k=0;k<6;k++){bits=focus_u32(row+8+4*k);memcpy(&v[k],&bits,4);}
        /* CELL-CHANGES-59: a placed item the world change list says was moved lies where it was left */
        if(aw_ledger_on && (k=AW_LedgerFind(&aw_ledger,reference))>=0 &&
           (aw_ledger.row[k].fields&AW_LEDGER_MOVED) && aw_ledger.row[k].extra){
            VectorCopy(aw_ledger.row[k].extra->position,v);v[4]=aw_ledger.row[k].extra->yaw;
        }
        scale=(float)(row[6]|(row[7]<<8))/(float)(1<<12);       /* twelve fraction bits (pack_placed) */
        if(!(scale>0) || !(v[0]==v[0] && v[1]==v[1] && v[2]==v[2]))continue;
        if(!focus_outdoor)VectorScale(v,.25f,local);
        else if(!focus_to_local(v,local)){placed_seen[4]++;continue;}
        placed_seen[5]++;
        memcpy(stem,row+32,16);stem[16]=0;
        if((k=aw_placed_admit(reference,stem,local,v+3,scale))<=0){refused++;continue;}
        focus_rows[j].drawn=(short)k;focus_rows[j].edict=0;
    }
    return refused;
}
/* After focus_load (the rows in this map's units): the placed items of the room, or of the 3 x 3 exterior cells. */
static void placed_load(void){
    FILE *f=NULL;byte head[8];long base,room;unsigned long keys;int length,dx,dy,j,refused=0;
    for(j=0;j<focus_count;j++)focus_rows[j].drawn=0;
    memset(placed_seen,0,sizeof(placed_seen));
    if(!aw_placed_begin || !aw_placed_admit || !aw_placed_begin() || !focus_count)return;
    length=COM_FOpenFile(PLACED_FILE,&f);
    if(!f)return;
    base=ftell(f);
    if(length<8 || fread(head,1,8,f)!=8 || memcmp(head,"AWP1",4) || (keys=focus_u32(head+4))>65535 ||
       8+keys*16>(unsigned long)length){fclose(f);Con_Printf("Placed items: %s is not a list this engine reads.\n",PLACED_FILE);return;}
    if(!focus_outdoor){if((room=focus_room())!=0)refused=placed_read_key(f,base,keys,length,(unsigned long)room);}
    else for(dx=-1;dx<=1;dx++)for(dy=-1;dy<=1;dy++)
        refused+=placed_read_key(f,base,keys,length,focus_exterior_key(focus_gx+dx,focus_gy+dy));
    fclose(f);
    if(refused)Con_Printf("Placed items: %d not drawn (their models do not fit the level's room of %d).\n",refused,AW_PLACED_MODELS);
}
static void focus_refresh(const edict_t *p);
/* aw_placed.c, once per client frame: the focus table (and with it the placed list) read again on a new map or a new
 * exterior cell; 1 outdoors (no room shift). */
int AW_PlacedRefresh(void){
    if(sv.active && svs.maxclients==1 && svs.clients && svs.clients[0].edict)focus_refresh(svs.clients[0].edict);
    return focus_outdoor;
}
/* AMBIENT-WALK-PER-AREA-60: the place's area keys (the room, or the 3 x 3 exterior cells), for the other per-area
 * tables (aw_ambient.c); the generation moves with every place read */
static unsigned long place_keys[AREA_MAX],place_gen;static int place_n;static model_t *place_world;
int AW_AreaPlaceKeys(unsigned long *keys,int max,unsigned long *generation){
    int i;
    if(place_world!=sv.worldmodel || !place_world)return -1;     /* this map's place not read yet */
    for(i=0;i<place_n && i<max;i++)keys[i]=place_keys[i];
    *generation=place_gen;
    return i;
}
static void focus_load(void){
    FILE *f=NULL;long base,room=0;int i,j,dx,dy,ok=1;
    unsigned long rooms;edict_t *e;eval_t *v;vec3_t game,local;
    focus_world=sv.worldmodel;focus_count=0;focus_outdoor=0;
    AW_ContainerRelease();     /* CONTAINER-STRIP-TAKE-STALL-59: a held container belongs to the place it was read in */
    if(aw_placed_begin)aw_placed_begin();      /* a new map or cell: nothing drawn until the list is read again */
    if(svs.clients && svs.clients[0].edict && focus_to_source(svs.clients[0].edict->v.origin,game)){
        focus_outdoor=1;focus_gx=(int)floor(game[0]/FOCUS_CELL);focus_gy=(int)floor(game[1]/FOCUS_CELL);
    }else if(!(room=focus_room()))return;
    place_n=0;place_gen++;place_world=sv.worldmodel;
    if(!focus_outdoor)place_keys[place_n++]=(unsigned long)room;
    else for(dx=-1;dx<=1;dx++)for(dy=-1;dy<=1;dy++)place_keys[place_n++]=focus_exterior_key(focus_gx+dx,focus_gy+dy);
    if(!focus_rows && !(focus_rows=(focus_row_t *)AW_TryMalloc(FOCUS_ROWS*sizeof(focus_row_t))))return;
    if(area_ready()){
        /* AREA-TABLES-59: the place's area tables (the room, or the 3 x 3 exterior cells) loaded with it: one seek and
         * one read an area (already loaded ones kept), the rows taken from them; then every lookup in play reads them */
        unsigned long keys[AREA_MAX];int n=0,k;
        if(!focus_outdoor)keys[n++]=(unsigned long)room;
        else for(dx=-1;dx<=1;dx++)for(dy=-1;dy<=1;dy++)keys[n++]=focus_exterior_key(focus_gx+dx,focus_gy+dy);
        area_loading=1;
        area_set(keys,n);
        for(k=0;k<n;k++){
            const area_t *a=area_of_key(keys[k]);int was=focus_count;
            if(!a)continue;
            for(j=0;j<a->rows;j++)focus_add_row(a->row+j*FOCUS_ROW2);
            focus_respawn(keys[k],was,focus_count);
        }
        /* the carried items' records into memory now (the inventory, the strip's other side, the HUD): read at the
         * load, never in play */
        for(j=0;j<aw_state.count[AW_ITEM];j++)
            if(aw_state.values[AW_ITEM][j].value>0){aw_inventory_item_t item;AW_InventoryRead(aw_state.values[AW_ITEM][j].id,&item);
                                                     pic_warm(aw_state.values[AW_ITEM][j].id);}
        area_loading=0;
        Con_Printf("Area tables: %d areas, %lu bytes read in %d ms (%d rows)\n",area_last_count,area_last_bytes,
                   (int)(area_last_seconds*1000),focus_count);
    }else{
        if(!(f=focus_open(&base,&rooms)))return;
        /* CELL-CHANGES-59 slice 7: each place read is a place loaded: its respawning containers refill when due */
        if(!focus_outdoor){int was=focus_count;ok=focus_read_key(f,base,rooms,(unsigned long)room);
            if(ok)focus_respawn((unsigned long)room,was,focus_count);}
        else for(dx=-1;dx<=1 && ok;dx++)for(dy=-1;dy<=1 && ok;dy++){
            unsigned long key=focus_exterior_key(focus_gx+dx,focus_gy+dy);int was=focus_count;
            ok=focus_read_key(f,base,rooms,key);
            if(ok)focus_respawn(key,was,focus_count);
        }
        fclose(f);
    }
    if(!ok){focus_count=0;return;}
    /* to this map's units: outdoors the map's own origin, a room a quarter scale (its shift is added when aimed) */
    for(j=0;j<focus_count;j++){
        if(!focus_outdoor)VectorScale(focus_rows[j].at,.25f,focus_rows[j].at);
        else if(focus_to_local(focus_rows[j].at,local)){VectorCopy(local,focus_rows[j].at);}
        else focus_rows[j].edict=1;
    }
    /* the actors and doors that have an edict of their own (an item's edict, a compiled room's placed static, has no
     * targeting of its own: its row stays) */
    for(j=0;j<focus_count;j++)focus_rows[j].live=0;
    for(i=1;i<sv.num_edicts;i++){
        e=EDICT_NUM(i);if(e->free)continue;
        v=GetEdictFieldValue(e,"aw_ref");if(!v || v->_float<=0)continue;
        for(j=0;j<focus_count;j++)if(focus_rows[j].reference==(unsigned)v->_float){
            if(focus_rows[j].kind!='I')focus_rows[j].edict=1;else focus_rows[j].live=1;
        }
    }
    /* In a room an item row counts only when the room draws the item: an edict that carries its reference or a
     * placement of the CHIM room. A compiled Quake room (the opening's Census Office) leaves the small items out
     * (INTERIOR-PLACED-ITEMS-47): their rows showed the box over an empty table and E had nothing to take. */
    if(!focus_outdoor)for(j=0;j<focus_count;j++)
        if(focus_rows[j].kind=='I' && !focus_rows[j].live && !ChimRoom_Has(focus_rows[j].reference))focus_rows[j].edict=1;
    placed_load();
    ledger_spawn();    /* CELL-CHANGES-59: a drop whose spot this map could not place at its start (outdoors, first frame) */
}
/* Read again on a new map, or outdoors when the player has walked into another cell. */
static void focus_refresh(const edict_t *p){
    vec3_t game;
    if(focus_world!=sv.worldmodel){focus_load();return;}
    /* PLACED-ITEMS-OUTDOORS-FIRST-FRAME-59: read in the first frame after a map change, before the player stands at
     * the arrival, an outdoor map could look like a room without a number and was never read again: read it again
     * as soon as the player's spot says outdoors */
    if(!focus_outdoor && focus_to_source(p->v.origin,game)){focus_load();return;}
    if(focus_outdoor && focus_to_source(p->v.origin,game) &&
       ((int)floor(game[0]/FOCUS_CELL)!=focus_gx || (int)floor(game[1]/FOCUS_CELL)!=focus_gy))focus_load();
}
/* The placed row aimed at within reach, -1 none. */
static int placed_target(void){
    int i,best=-1;float reach=AW_ActivateDistance(),nearest,along,side,length,shift[3];edict_t *p;vec3_t f,r,u,eye,delta,at;
    trace_t tr;
    if(!sv.active || svs.maxclients!=1 || !svs.clients || !(p=svs.clients[0].edict))return -1;
    focus_refresh(p);
    if(!focus_count)return -1;
    VectorCopy(p->v.origin,eye);eye[2]+=p->v.view_ofs[2];AngleVectors(p->v.v_angle,f,r,u);
    if(focus_outdoor)shift[0]=shift[1]=shift[2]=0;else AW_MwscriptRoomShift(shift);
    nearest=reach;
    for(i=0;i<focus_count;i++){
        focus_row_t *row=&focus_rows[i];
        if(row->edict || AW_ObjectDisabled(row->reference))continue;
        VectorAdd(row->at,shift,at);VectorSubtract(at,eye,delta);along=DotProduct(delta,f);length=DotProduct(delta,delta);
        if(along<=0 || along>nearest || length>reach*reach)continue;
        side=length-along*along;
        if(side>(row->kind=='I'?16.0f:36.0f))continue;     /* close to the crosshair line (map units squared) */
        tr=SV_Move(eye,vec3_origin,vec3_origin,at,MOVE_NOMONSTERS,p);
        if(tr.fraction<1 && (1-tr.fraction)*sqrt(length)>6)continue;      /* a wall between: not in view */
        nearest=along;best=i;
    }
    return best;
}
int AW_PlacedFocus(const char **name,char *weight_line,char *value_line,int line_size,int *owned){
    static char label_weight[32],label_value[32];static int labels;
    int best,level;char number[24];
    if(!name || !weight_line || !value_line || line_size<2 || (best=placed_target())<0)return 0;
    if(focus_rows[best].kind=='A')return 0;   /* FOCUS-BOX-NO-ACTORS-58: items and doors only */
    if(!labels){
        labels=1;
        if(!hud_setting("sWeight",label_weight,sizeof(label_weight)))strcpy(label_weight,"Weight");
        if(!hud_setting("sValue",label_value,sizeof(label_value)))strcpy(label_value,"Value");
    }
    *name=focus_rows[best].name;weight_line[0]=value_line[0]=0;
    if(focus_rows[best].kind=='I'){
        weight_text(focus_rows[best].weight,number,sizeof(number));
        Q_snprintf(weight_line,line_size,"%s: %s",label_weight,number);
        Q_snprintf(value_line,line_size,"%s: %d",label_value,focus_rows[best].value);
    }
    /* CONTAINER-WINDOW-59: a locked container's box says its lock level, as the original's tooltip does */
    if(focus_rows[best].kind=='C' && (level=container_lock(&focus_rows[best]))>0){
        static char label_lock[32];
        if(!label_lock[0] && !hud_setting("sLockLevel",label_lock,sizeof(label_lock)))strcpy(label_lock,"Lock Level");
        Q_snprintf(weight_line,line_size,"%s: %d",label_lock,level);
    }
    if(owned)*owned=focus_rows[best].owned;
    return 1;
}
/* STEAL-PROMPT-58: the action line under an aimed item that the activate key takes: "E: Take" for a dropped item or
 * an unowned placed item, "E: Steal" (*steal 1, drawn red) when taking it would be theft. The word "Take" is the
 * game's GMST sTake (gfx/hud-settings.txt); the original has no GMST for the steal prompt. 0 for no takeable item. */
/* The prompt is decided at build time: the row's action code (kind and owned bits) indexes this table once built;
 * nothing is looked up per frame. A readable book reads "E: Read" (red when owned: it belongs to someone) once the
 * book reader is there (aw_book_reader); until then E takes it, so it prompts like any item. */
int (*aw_book_reader)(unsigned reference);
static char prompts[8][40];
/* CONTAINER-WINDOW-59: a container that opens reads "E: Open", "E: Steal" (red) when it is owned (opening it is
 * free, taking from it is theft), "Locked" while locked (red when owned); organic ones (flora) none: E picks them. */
static int container_prompt(const focus_row_t *row,char *line,int size,int *steal){
    static char open[40],locked[40];
    if((row->action&3)!=FOCUS_ACT_TAKE)return 0;
    if(!open[0]){
        char word[32];
        if(!hud_setting("sOpen",word,sizeof(word)))strcpy(word,"Open");
        Q_snprintf(open,sizeof(open),"E: %s",word);
        if(!hud_setting("sLocked",locked,sizeof(locked)))strcpy(locked,"Locked");
    }
    *steal=row->owned!=0;
    Q_strcpy_bounded(line,container_lock(row)>0?locked:row->owned?"E: Steal":open,(size_t)size);
    return 1;
}
int AW_ItemPrompt(char *line,int size,int *steal){
    static int labels;int best,code;
    if(!line || size<2 || !steal)return 0;
    if(!labels){
        char take[32];labels=1;
        if(!hud_setting("sTake",take,sizeof(take)))strcpy(take,"Take");
        Q_snprintf(prompts[FOCUS_ACT_TAKE],sizeof(prompts[0]),"E: %s",take);
        strcpy(prompts[FOCUS_ACT_TAKE|FOCUS_ACT_OWNED],"E: Steal");
        strcpy(prompts[FOCUS_ACT_READ],"E: Read");strcpy(prompts[FOCUS_ACT_READ|FOCUS_ACT_OWNED],"E: Read");
    }
    code=FOCUS_ACT_TAKE;
    if(drop_aimed()<0){
        if((best=placed_target())>=0 && focus_rows[best].kind=='C')return container_prompt(&focus_rows[best],line,size,steal);
        if(best<0 || focus_rows[best].kind!='I')return 0;
        code=focus_rows[best].action&7;
        if((code&3)==FOCUS_ACT_READ && !aw_book_reader)code=FOCUS_ACT_TAKE|(code&FOCUS_ACT_OWNED);
    }
    if(!prompts[code][0])return 0;
    *steal=(code&FOCUS_ACT_OWNED)!=0;
    Q_strcpy_bounded(line,prompts[code],(size_t)size);
    return 1;
}
/* PICKUP-PLACED-58: the activate key on a placed item in reach takes it, as the original and OpenMW 0.51 do: its
 * record id from focus.awf (AWF2), one into the inventory, the placement disabled and hidden through the object state
 * (aw_mwhost.c AW_ObjectTake: saved, hidden again on every map). An owned item is marked stolen there (CRIME-59).
 * 1 when the key was used here (taken, or refused with a line). */
static int placed_id(unsigned reference,char *id){
    FILE *f;long base;unsigned long rooms;int dx,dy,k;long room;
    id[0]=0;
    if((k=area_placed_id(reference,id))>=0)return k;     /* AREA-TABLES-59: the loaded area's row */
    if(!area_loading)area_fallback[2]++;
    if(!(f=focus_open(&base,&rooms)))return 0;
    if(!focus_outdoor){if((room=focus_room())!=0)focus_read_key_id(f,base,rooms,(unsigned long)room,reference,id);}
    else for(dx=-1;dx<=1 && !id[0];dx++)for(dy=-1;dy<=1 && !id[0];dy++)
        focus_read_key_id(f,base,rooms,focus_exterior_key(focus_gx+dx,focus_gy+dy),reference,id);
    fclose(f);
    return id[0]!=0;
}
static focus_row_t *placed_row(unsigned reference){
    int i;
    for(i=0;i<focus_count;i++)if(focus_rows[i].kind=='I' && focus_rows[i].reference==reference)return &focus_rows[i];
    return NULL;
}
static int take_row(focus_row_t *);
/* BOOK-READER-58: the record id and ownership of the placed book REFERENCE in the current focus table (the reader
 * asks when it opens); 0 when it is not there. */
int AW_PlacedBook(unsigned reference,char *id,int *owned){
    focus_row_t *row=placed_row(reference);
    if(!id)return 0;
    id[0]=0;
    if(!row || !placed_id(reference,id))return 0;
    if(owned)*owned=row->owned!=0;
    return 1;
}
/* BOOK-READER-58: the reader's Take: the same path as E on the item (owned taking marked for CRIME-59). */
int AW_PlacedTake(unsigned reference){
    focus_row_t *row=placed_row(reference);
    return row && !AW_ObjectDisabled(reference)?take_row(row):0;
}
static int placed_use(void){
    int best=placed_target();focus_row_t *row;
    if(best>=0 && focus_rows[best].kind=='C')return container_open(&focus_rows[best]);   /* CONTAINER-WINDOW-59 */
    if(best<0 || (row=&focus_rows[best])->kind!='I')return 0;
    /* a readable book opens the reader (reading is free); Take or Steal is inside it */
    if((row->action&3)==FOCUS_ACT_READ && aw_book_reader && aw_book_reader(row->reference))return 1;
    return take_row(row);
}
static int take_row(focus_row_t *row){
    aw_inventory_item_t item;char id[FOCUS_ID+1];
    if(!placed_id(row->reference,id) || !AW_InventoryRead(id,&item))return 0;
    if(!AW_ItemAdd(&aw_state,item.id,1)){AW_UISubtitle(row->name,"Cannot collect: inventory capacity.",3);return 1;}
    if(!AW_ObjectTake(row->reference,row->owned)){AW_ItemAdd(&aw_state,item.id,-1);return 0;}
    /* CELL-CHANGES-59 slice 2: an owned item is stolen from its owner (the reference's owner, else its faction): the
     * pair (item, owner) on the world change list, kept wherever the item goes; the crime itself is CRIME-59 */
    if(row->owned && aw_ledger_on){
        char owner[AW_LEDGER_STOLEN_ID+1];int faction;
        if(container_owner(row->reference,owner,&faction))AW_LedgerStolenAdd(&aw_ledger,item.id,owner,faction,1);
    }
    aw_state.inventory.initialized=1;
    AW_UIPickupNotice(row->name,3);AW_CombatEquipmentChanged();
    return 1;
}
int AW_InventoryUse(void){
    int i;
    if(aw_ledger_on){
        /* CELL-CHANGES-59: a drop of the world change list comes back and its row goes */
        if((i=ledger_target())<0)return placed_use();
        if(!AW_LedgerPickup(&aw_state,&aw_ledger,map_drops[i].key)){
            AW_UISubtitle(map_drops[i].label,"Cannot collect: inventory capacity.",3);return 1;}
        AW_UIPickupNotice(map_drops[i].label,3);AW_CombatEquipmentChanged();    /* the notice keeps its own copy */
        ED_Free(map_drops[i].e);map_drops[i]=map_drops[--map_drop_count];
        return 1;
    }
    i=inv_target();if(i<0)return placed_use();
    if(!AW_InventoryPickup(&aw_state,i)){AW_UISubtitle(drop_label[i],"Cannot collect: inventory capacity.",3);return 1;}
    AW_UIPickupNotice(drop_label[i],3);AW_CombatEquipmentChanged();ED_Free(drop_entity[i]);drop_entity[i]=NULL;return 1;
}
#endif
