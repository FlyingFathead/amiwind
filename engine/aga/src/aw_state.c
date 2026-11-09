/* SPDX-License-Identifier: GPL-2.0-or-later
 * Persistent game facts: numeric globals/journal indices and inventory counts.
 * UI stage order is not a quest model. Conditions query these independent facts;
 * SetJournalIndex may move either way, while Journal only advances its index.
 *
 * INVENTORY-ORIGINAL-LIMITS-61: the item table has no fixed number of kinds (aw_state.h): 24-byte rows in blocks of
 * AW_ITEM_BLOCK from the game heap, the ids once each in a name pool, the carried weight as a running total. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "aw_state.h"
#include "aw_tryalloc.h"
aw_state_t aw_state;
/* the worst case (resident registry): every kind of item in the game carried at once (the v0.0.61-dev1 catalogue has
 * 2,930 records, plus up to 64 items the player enchants; rounded up), a 24-byte row and an id of at most 31 letters */
#define AW_ITEM_KINDS_WORST 3000
#define AW_ITEM_KIND_BYTES 56
AW_RESIDENT_GROWS("the item table: kinds carried (INVENTORY-ORIGINAL-LIMITS-61)",AW_ITEM_KINDS_WORST,AW_ITEM_KIND_BYTES);
void (*aw_magic_frame)(float seconds);
int (*aw_item_weight)(const char *id,float *weight);
void (*aw_save_items_loaded)(void);
static int key(char out[64],const char *id)
{
    unsigned char c;int n=0;
    while((c=(unsigned char)*id++)!=0){
        if(n>=63 || c<32)return 0;
        out[n++]=c>='A' && c<='Z'?c+32:c;
    }
    out[n]=0;return n>0;
}
/* FNV-1a over the bytes of a folded id */
static uint32_t item_hash(const char *s)
{
    uint32_t h=2166136261U;
    while(*s){h^=(unsigned char)*s++;h*=16777619U;}
    return h;
}
int (*aw_state_fact_get)(const char *id,int32_t *out);
int (*aw_state_fact_set)(const char *id,int32_t value);
/* ---- the item table ---- */
static int item_find(const aw_state_t *s,const char *name,uint32_t hash)
{
    int i;const aw_items_t *t=&s->items;
    for(i=0;i<t->count;i++){
        const aw_item_row_t *r=&t->block[i/AW_ITEM_BLOCK][i%AW_ITEM_BLOCK];
        if(r->hash==hash && !strcmp(t->names+(r->name&0xffffffU),name))return i;
    }
    return -1;
}
int AW_ItemCount(const aw_state_t *s){return s?s->items.count:0;}
int AW_ItemIndex(const aw_state_t *s,const char *id)
{
    char name[64];
    if(!s || !id || !key(name,id))return -1;
    return item_find(s,name,item_hash(name));
}
/* the pool holds BYTES more: dead names (rows given a new kind) dropped first, then a larger pool */
static int names_room(aw_items_t *t,uint32_t bytes)
{
    uint32_t live=0,size,at=0;int i;char *pool;
    if(t->names_size-t->names_used>=bytes)return 1;
    for(i=0;i<t->count;i++)live+=(uint32_t)strlen(t->names+(t->block[i/AW_ITEM_BLOCK][i%AW_ITEM_BLOCK].name&0xffffffU))+1;
    size=t->names_size?t->names_size:512;
    while(size<live+bytes || size<(live+bytes)+(live+bytes)/2)size*=2;
    if(size>0xffffffU)return 0;
    if(!(pool=(char *)AW_TryMalloc(size)))return 0;
    for(i=0;i<t->count;i++){
        aw_item_row_t *r=&t->block[i/AW_ITEM_BLOCK][i%AW_ITEM_BLOCK];
        const char *name=t->names+(r->name&0xffffffU);uint32_t n=(uint32_t)strlen(name)+1;
        memcpy(pool+at,name,n);r->name=(r->name&0xff000000U)|at;at+=n;
    }
    free(t->names);t->names=pool;t->names_used=at;t->names_size=size;
    return 1;
}
static uint32_t names_add(aw_items_t *t,const char *name)
{
    uint32_t n=(uint32_t)strlen(name)+1,at=t->names_used;
    memcpy(t->names+at,name,n);t->names_used+=n;return at;
}
/* blocks for ROWS rows in all */
static int rows_room(aw_items_t *t,int rows)
{
    int need=(rows+AW_ITEM_BLOCK-1)/AW_ITEM_BLOCK,i;aw_item_row_t **dir;
    if(rows>AW_ITEM_KINDS_MAX)return 0;
    if(need<=t->blocks)return 1;
    if(!(dir=(aw_item_row_t **)AW_TryMalloc(sizeof(*dir)*need)))return 0;
    for(i=0;i<t->blocks;i++)dir[i]=t->block[i];
    for(;i<need;i++)if(!(dir[i]=(aw_item_row_t *)AW_TryMalloc(sizeof(aw_item_row_t)*AW_ITEM_BLOCK))){
        while(--i>=t->blocks)free(dir[i]);
        free(dir);return 0;
    }
    free(t->block);t->block=dir;t->blocks=need;
    return 1;
}
static int zero_rows(const aw_items_t *t)
{
    int i,n=0;
    for(i=0;i<t->count;i++)if(!t->block[i/AW_ITEM_BLOCK][i%AW_ITEM_BLOCK].value)n++;
    return n;
}
int AW_ItemReserve(aw_state_t *s,int kinds)
{
    aw_items_t *t=&s->items;int fresh;
    if(kinds<=0)return 1;
    fresh=kinds-zero_rows(t);
    if(fresh>0 && !rows_room(t,t->count+fresh))return 0;
    return names_room(t,(uint32_t)kinds*64U);
}
/* DBG-GIVE-MONEY-62 (aw_state.h): VALUE for the folded id, gold held at AW_GOLD_MAX */
int32_t AW_GoldCap(const char *folded_id,int32_t value)
{
    return folded_id && value>(int32_t)AW_GOLD_MAX && !strcmp(folded_id,AW_GOLD_ID)?(int32_t)AW_GOLD_MAX:value;
}
int AW_ItemAppend(aw_state_t *s,const char *id,int32_t value)
{
    aw_items_t *t=&s->items;aw_item_row_t *r;uint32_t n;
    if(!id || !id[0] || (n=(uint32_t)strlen(id))>63 || !rows_room(t,t->count+1) || !names_room(t,n+1))return 0;
    value=AW_GoldCap(id,value);
    r=&t->block[t->count/AW_ITEM_BLOCK][t->count%AW_ITEM_BLOCK];t->count++;
    memset(r,0,sizeof(*r));r->hash=item_hash(id);r->value=value;r->name=names_add(t,id);
    return 1;
}
void AW_ItemsFree(aw_state_t *s)
{
    int i;aw_items_t *t=&s->items;
    for(i=0;i<t->blocks;i++)free(t->block[i]);
    free(t->block);free(t->names);memset(t,0,sizeof(*t));
}
int AW_ItemsClone(aw_items_t *out,const aw_items_t *in)
{
    aw_state_t copy;int i;
    memset(&copy,0,sizeof(copy));memset(out,0,sizeof(*out));
    if(in->count && (!rows_room(&copy.items,in->count) ||
       !(copy.items.names=(char *)AW_TryMalloc(in->names_size)))){AW_ItemsFree(&copy);return 0;}
    for(i=0;i<in->count;i++)copy.items.block[i/AW_ITEM_BLOCK][i%AW_ITEM_BLOCK]=in->block[i/AW_ITEM_BLOCK][i%AW_ITEM_BLOCK];
    if(in->count){memcpy(copy.items.names,in->names,in->names_used);copy.items.names_size=in->names_size;}
    copy.items.names_used=in->count?in->names_used:0;copy.items.count=in->count;copy.items.burden=in->burden;
    *out=copy.items;return 1;
}
void AW_ItemMark(aw_state_t *s,int i,unsigned flag,float value)
{
    aw_item_row_t *r;
    if(!s || i<0 || i>=s->items.count)return;
    r=AW_ITEM_ROW(s,i);AW_ITEM_SET_FLAG(r,flag);
    if(flag&AW_ITEM_CONDITION)r->condition=value;
    if(flag&AW_ITEM_CHARGE)r->charge=value;
}
void AW_ItemUnmark(aw_state_t *s,int i,unsigned flag)
{
    aw_item_row_t *r;
    if(!s || i<0 || i>=s->items.count)return;
    r=AW_ITEM_ROW(s,i);AW_ITEM_CLEAR_FLAG(r,flag);
    if(flag&AW_ITEM_CONDITION)r->condition=0;
    if(flag&AW_ITEM_CHARGE)r->charge=0;
}
float AW_ItemsBurden(const aw_state_t *s)
{
    return s && s->items.burden>0?s->items.burden:0;
}
void AW_ItemsWeigh(aw_state_t *s)
{
    aw_items_t *t=&s->items;int i;float total=0,w;
    for(i=0;i<t->count;i++){
        aw_item_row_t *r=&t->block[i/AW_ITEM_BLOCK][i%AW_ITEM_BLOCK];
        if(!(AW_ITEM_FLAGS(r)&AW_ITEM_WEIGHED) && r->value>0 && aw_item_weight &&
           aw_item_weight(t->names+(r->name&0xffffffU),&w) && w>=0){r->weight=w;AW_ITEM_SET_FLAG(r,AW_ITEM_WEIGHED);}
        if(AW_ITEM_FLAGS(r)&AW_ITEM_WEIGHED)total+=r->weight*(float)r->value;
    }
    t->burden=total;
}
/* a count change of row R: the running total follows (a new or reused row is weighed by its record when it can be) */
static void row_value(aw_items_t *t,aw_item_row_t *r,int32_t value)
{
    float w;
    if(!(AW_ITEM_FLAGS(r)&AW_ITEM_WEIGHED) && value>0 && aw_item_weight &&
       aw_item_weight(t->names+(r->name&0xffffffU),&w) && w>=0){r->weight=w;AW_ITEM_SET_FLAG(r,AW_ITEM_WEIGHED);
        t->burden+=w*(float)r->value;}
    if(AW_ITEM_FLAGS(r)&AW_ITEM_WEIGHED)t->burden+=r->weight*((float)value-(float)r->value);
    r->value=value;
    if(t->burden<0)t->burden=0;
}
static int item_set(aw_state_t *s,const char *name,int32_t value)
{
    aw_items_t *t=&s->items;uint32_t hash=item_hash(name);int i=item_find(s,name,hash);aw_item_row_t *r;
    if(value<0)return 0;
    value=AW_GoldCap(name,value);   /* DBG-GIVE-MONEY-62 */
    if(i<0){
        if(!value)return 1;                  /* none of an item not carried: nothing to keep */
        /* a row whose count fell to 0 first (its condition and charge went with the last one), then a new row */
        for(i=0;i<t->count && t->block[i/AW_ITEM_BLOCK][i%AW_ITEM_BLOCK].value;i++);
        if(!names_room(t,(uint32_t)strlen(name)+1))return 0;
        if(i==t->count && !rows_room(t,t->count+1))return 0;
        r=&t->block[i/AW_ITEM_BLOCK][i%AW_ITEM_BLOCK];
        memset(r,0,sizeof(*r));r->hash=hash;r->name=names_add(t,name);
        if(i==t->count)t->count++;
    }else r=&t->block[i/AW_ITEM_BLOCK][i%AW_ITEM_BLOCK];
    row_value(t,r,value);
    return 1;
}
void AW_StateReset(void){AW_ItemsFree(&aw_state);memset(&aw_state,0,sizeof(aw_state));}
int32_t AW_StateGet(const aw_state_t *state,int kind,const char *id)
{
    char name[64];int i;int32_t fact=0;
    if(kind<0 || kind>2 || !key(name,id))return 0;
    if(kind==AW_ITEM){i=item_find(state,name,item_hash(name));return i<0?0:AW_ITEM_ROW(state,i)->value;}
    for(i=0;i<state->count[kind];i++)if(!strcmp(state->values[kind][i].id,name))return state->values[kind][i].value;
    if(kind==AW_GLOBAL && aw_state_fact_get && aw_state_fact_get(name,&fact))return fact;
    return 0;
}
int AW_StateSet(aw_state_t *state,int kind,const char *id,int32_t value)
{
    char name[64];int i;
    if(kind<0 || kind>2 || !key(name,id))return 0;
    if(kind==AW_ITEM)return item_set(state,name,value);
    for(i=0;i<state->count[kind];i++)if(!strcmp(state->values[kind][i].id,name))break;
    if(i==state->count[kind]){
        /* a named global past the 32 slots: the world change list's named facts (slice 4) */
        if(kind==AW_GLOBAL && aw_state_fact_set && aw_state_fact_get &&
           (i==AW_STATE_VALUES || aw_state_fact_get(name,NULL)))return aw_state_fact_set(name,value);
        if(i>=AW_STATE_VALUES)return 0;
        memset(&state->values[kind][i],0,sizeof(aw_value_t));strcpy(state->values[kind][i].id,name);state->count[kind]++;
    }
    state->values[kind][i].value=value;return 1;
}
int AW_ItemRoom(const aw_state_t *state)
{
    const aw_items_t *t=&state->items;int room=t->blocks*AW_ITEM_BLOCK-t->count+zero_rows(t);
    if(room>0)return room;
    /* a full block: room as soon as one more block can be had (taken now; nothing else changes) */
    return AW_ItemReserve((aw_state_t *)state,1)?t->blocks*AW_ITEM_BLOCK-t->count:0;
}
int AW_ItemRefusal(const aw_state_t *state,const char *id,int32_t count)
{
    char name[64];int i;int32_t old;
    if(!key(name,id))return AW_ITEM_BAD_ID;
    i=item_find(state,name,item_hash(name));
    old=i>=0?AW_ITEM_ROW(state,i)->value:0;
    if((count>0 && old>INT32_MAX-count) || (count<0 && count< -old))return AW_ITEM_TOO_MANY;
    if(count>0 && i<0 && !AW_ItemReserve((aw_state_t *)state,1))return AW_ITEM_FULL;
    return AW_ITEM_OK;
}
const char *AW_ItemRefusalText(const aw_state_t *state,int reason)
{
    static char text[96];int i,used=0;
    for(i=0;i<state->items.count;i++)if(AW_ITEM_ROW(state,i)->value>0)used++;
    switch(reason){
    case AW_ITEM_FULL:
        snprintf(text,sizeof(text),"not enough memory for another kind of item (%d kinds carried)",used);return text;
    case AW_ITEM_TOO_MANY:return "too many of this item";
    case AW_ITEM_BAD_ID:return "the item's name was refused";
    }
    return "refused";
}
int AW_StateTest(const aw_state_t *state,int kind,const char *id,int comparison,int32_t value)
{
    int32_t actual=AW_StateGet(state,kind,id);
    switch(comparison){
        case AW_EQ:return actual==value;case AW_NE:return actual!=value;
        case AW_GT:return actual>value;case AW_GE:return actual>=value;
        case AW_LT:return actual<value;case AW_LE:return actual<=value;
    }
    return 0;
}
/* The journal-updated notices owed (OpenMW Journal::addEntry: sJournalEntry whenever a quest's index rises, a new
 * entry or one heard before; nothing for a repeat or a lower index). The caller compares the count around a call. */
static unsigned journal_notices;
unsigned AW_JournalNotices(void){return journal_notices;}
int AW_JournalAdd(aw_state_t *state,const char *id,int32_t index)
{
    char name[64];int i,quest,known=0;int32_t days,ms;aw_journal_entry_t *entry;
    if(!key(name,id))return 0;
    if(index<=AW_StateGet(state,AW_JOURNAL,id))return 1;
    for(quest=0;quest<state->count[AW_JOURNAL];quest++)
        if(!strcmp(state->values[AW_JOURNAL][quest].id,name))break;
    for(i=0;i<state->journal_count;i++)
        if(state->journal[i].quest==quest && state->journal[i].stage==index)known=1;
    /* Never advance a quest while silently dropping its new history entry. */
    if(!known && state->journal_count>=AW_JOURNAL_ENTRIES)return 0;
    days=AW_StateGet(state,AW_GLOBAL,"amiwind:clock:days");
    ms=AW_StateGet(state,AW_GLOBAL,"amiwind:clock:ms");
    if(!AW_StateGet(state,AW_GLOBAL,"amiwind:clock:ready"))ms=32400000;
    if(days<0 || days>365000 || ms<0 || ms>=86400000)return 0;
    if(!AW_StateSet(state,AW_JOURNAL,id,index))return 0;
    journal_notices++;
    if(!known){
        entry=&state->journal[state->journal_count++];
        entry->quest=quest;entry->stage=index;entry->days=days;entry->milliseconds=ms;
    }
    return 1;
}
/* an item entered the player's inventory (aw_mwhost.c: its script's OnPCAdd, CENSUS-INTRO-SCRIPTS-62); NULL: none */
void (*aw_item_added)(const char *id,int32_t count);
/* the last of an item left the player's inventory (aw_mwhost.c: its carried script stops, MWSCRIPT-UNPLACED-ATTACH-62) */
void (*aw_item_removed)(const char *id);
int AW_ItemAdd(aw_state_t *state,const char *id,int32_t count)
{
    char normalized[64];int32_t old;
    if(!key(normalized,id))return 0;
    id=normalized;
    old=AW_StateGet(state,AW_ITEM,id);
    if(count>0 && old>INT32_MAX-count)return 0;
    if(count<0 && count < -old)return 0;
    if(!AW_StateSet(state,AW_ITEM,id,old+count))return 0;
    if(count>0 && state==&aw_state && aw_item_added)aw_item_added(id,count);
    if(count<0){
        int i,index=AW_ItemIndex(state,id),used=0;
        for(i=0;i<AW_INVENTORY_SLOTS;i++)if(!strcmp(state->inventory.equipped[i],id)){
            if(++used>old+count)memset(state->inventory.equipped[i],0,64);
        }
        if(old+count==0 && index>=0){
            aw_item_row_t *r=AW_ITEM_ROW(state,index);
            AW_ITEM_CLEAR_FLAG(r,AW_ITEM_CONDITION|AW_ITEM_CHARGE);r->condition=r->charge=0;
            /* A selected item that leaves the inventory is no longer selected. */
            if(!strcmp(state->magic.selected,id))memset(state->magic.selected,0,64);
        }
        if(old+count==0 && state==&aw_state && aw_item_removed)aw_item_removed(id);
    }
    return 1;
}
/* The transactions below change items only after everything that can refuse has been checked: the item table is
 * shared by a copy of the state (aw_state.h OWNERSHIP), so the copy carries only the globals and quest stages. */
static int items_fit(const char *const *ids,const int32_t *counts,int n)
{
    int i;
    for(i=0;i<n;i++)if(AW_ItemRefusal(&aw_state,ids[i],counts[i])!=AW_ITEM_OK)return 0;
    return AW_ItemReserve(&aw_state,n);
}
int AW_CaptainDuties(void)
{
    static const char *const ids[]={"bk_a1_1_directionscaiuscosades","bk_a1_1_caiuspackage","gold_001"};
    static const int32_t counts[]={1,1,87};
    aw_state_t next;int i;
    /* The original INFO branch tests journal == 0. Possessing/losing a package
     * is a different condition and must never reset reward eligibility. */
    if(!AW_StateTest(&aw_state,AW_JOURNAL,"A1_1_FindSpymaster",AW_EQ,0) || !items_fit(ids,counts,3))return 0;
    next=aw_state;
    if(!AW_JournalAdd(&next,"A1_1_FindSpymaster",1))return 0;
    aw_state=next;
    for(i=0;i<3;i++)AW_ItemAdd(&aw_state,ids[i],counts[i]);   /* cannot refuse after items_fit */
    return 1;
}

int AW_CourtyardRingAvailable(void)
{
    /* Runtime-owned placed-container fact, not a TES3 global or a quest stage.
     * Losing/returning the inventory item must not restock this container. */
    return !AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:ref:172851:ring_taken");
}
int AW_CourtyardTakeRing(void)
{
    static const char *const ids[]={"ring_keley"};static const int32_t counts[]={1};
    aw_state_t next;
    if(!AW_CourtyardRingAvailable() || !items_fit(ids,counts,1))return 0;
    next=aw_state;
    if(!AW_StateSet(&next,AW_GLOBAL,"amiwind:ref:172851:ring_taken",1))return 0;
    aw_state=next;AW_ItemAdd(&aw_state,ids[0],1);return 1;
}
