/* SPDX-License-Identifier: GPL-2.0-or-later
 * Explicit little-endian schema; no raw structs, pointers or model caches. */
#include <string.h>
#include <math.h>
#include "aw_save.h"
#include "aw_maps.h"
static unsigned char *writing;
static const unsigned char *reading;
static int at,end,error;
static uint32_t crc32(const unsigned char *p,int n)
{
    uint32_t crc=0xffffffffU;int i;
    while(n--){crc^=*p++;for(i=0;i<8;i++)crc=(crc>>1)^((crc&1)?0xedb88320U:0);}
    return crc^0xffffffffU;
}
static void bytes(void *value,int size)
{
    if(size<0 || at>end-size){error=1;return;}
    if(writing)memcpy(writing+at,value,size);else memcpy(value,reading+at,size);
    at+=size;
}
static void word(uint32_t *value)
{
    unsigned char raw[4];
    if(writing){raw[0]=*value;raw[1]=*value>>8;raw[2]=*value>>16;raw[3]=*value>>24;}
    else memset(raw,0,sizeof(raw));
    bytes(raw,4);
    if(!writing)*value=(uint32_t)raw[0]|((uint32_t)raw[1]<<8)|((uint32_t)raw[2]<<16)|((uint32_t)raw[3]<<24);
}
static void integer(int *v,int low,int high)
{
    uint32_t n=writing?(uint32_t)*v:0;word(&n);
    if(!writing)*v=(int)(int32_t)n;
    if(*v<low || *v>high)error=1;
}
static void floating(float *v,float low,float high)
{
    uint32_t n=0;
    if(writing)memcpy(&n,v,4);
    word(&n);
    if(!writing)memcpy(v,&n,4);
    if(!(*v>=low && *v<=high))error=1;
}
static void string(char *s,int size)
{
    int i;bytes(s,size);
    if(!memchr(s,0,size)){error=1;return;}
    for(i=0;s[i];i++)if((unsigned char)s[i]<32){error=1;break;}
}
static void id(int *index,int type)
{
    char value[64];int i,count=type==0?aw_race_count:type==1?aw_class_count:type==2?aw_birth_count:aw_part_count;
    memset(value,0,sizeof(value));
    if(writing){
        if(*index<0 || *index>=count){error=1;return;}
        memset(value,0,sizeof(value));
        strcpy(value,type==0?aw_races[*index].id:type==1?aw_classes[*index].id:type==2?aw_births[*index].id:aw_parts[*index].id);
    }
    string(value,64);
    if(error)return;
    if(!writing){
        for(i=0;i<count;i++)if(!strcmp(value,type==0?aw_races[i].id:type==1?aw_classes[i].id:type==2?aw_births[i].id:aw_parts[i].id))break;
        if(i==count)error=1;else *index=i;
    }
}
static void fields(aw_save_t *s)
{
    int i,j,k,n;uint32_t number;aw_character_t *c=&s->character;aw_story_t *q=&s->story;
    word(&s->sequence);word(&s->profile);bytes(s->content,32);
    if(!s->sequence || !s->profile)error=1;
    string(s->scene,16);string(s->label,32);string(q->name,32);
    if(error)return;
    if(AW_MapId(s->scene)<0)error=1;
    for(i=0;i<3;i++){floating(&s->position[i],-32767,32767);floating(&s->angles[i],-360,360);}
    id(&c->race,0);id(&c->clas,1);id(&c->birth,2);id(&c->head,3);id(&c->hair,3);
    integer(&c->female,0,1);integer(&c->level,1,1000);c->valid=1;
    for(i=0;i<8;i++){
        n=c->attributes[i];integer(&n,0,1000);c->attributes[i]=n;
        n=c->modifiers[i];integer(&n,-1000,1000);c->modifiers[i]=n;
        n=c->damage[i];integer(&n,0,1000);c->damage[i]=n;
    }
    for(i=0;i<27;i++){n=c->skills[i];integer(&n,0,1000);c->skills[i]=n;}
    for(i=0;i<3;i++){
        floating(&c->maximum[i],0,100000);floating(&c->current[i],-100000,100000);
        if(c->current[i]>c->maximum[i])error=1;
    }
    integer(&q->stage,AW_STAGE_RELEASED,AW_STAGE_RELEASED);
    integer(&q->dock,-1,50);integer(&q->census,-1,30);integer(&q->hall,0,1);integer(&q->captain,-1,0);
    integer(&q->ship_disabled,0,1);integer(&q->captain_hint,0,1);integer(&q->hall_open,0,1);
    floating(&q->dock_timer,0,100000);floating(&q->census_timer,0,100000);floating(&q->hall_timer,0,100000);
    if(!q->ship_disabled || q->captain!=-1 || !q->name[0])error=1;
    for(i=0;i<3;i++){
        integer(&s->state.count[i],0,AW_STATE_VALUES);if(error)return;
        for(j=0;j<s->state.count[i];j++){
            aw_value_t *v=&s->state.values[i][j];
            string(v->id,64);if(error)return;
            number=writing?(uint32_t)v->value:0;word(&number);
            if(!writing)v->value=(int32_t)number;
            if(!v->id[0] || (i==AW_ITEM && v->value<0))error=1;
            for(k=0;k<j;k++)if(!strcmp(v->id,s->state.values[i][k].id))error=1;
        }
    }
    if(AW_StateGet(&s->state,AW_GLOBAL,"CharGenState")!=-1)error=1;
    if(!error && (aw_parts[c->head].race!=c->race || aw_parts[c->hair].race!=c->race ||
       aw_parts[c->head].female!=c->female || aw_parts[c->hair].female!=c->female ||
       aw_parts[c->head].kind!=0 || aw_parts[c->hair].kind!=1))error=1;
    integer(&s->actor_count,0,AW_SAVE_ACTORS);
    if(error)return;
    for(i=0;i<s->actor_count;i++){
        aw_saved_actor_t *a=&s->actors[i];
        word(&a->reference);integer(&a->scene,0,AW_SCENE_COUNT-1);
        /* The ID range has a gap between interiors and extra towns. */
        if(!a->reference || a->reference>0xffffffU || (!error && !AW_MapName(a->scene)[0]))error=1;
        for(j=0;j<3;j++){floating(&a->position[j],-32767,32767);floating(&a->angles[j],-360,360);}
        floating(&a->health,-10000,100000);
        integer(&a->hello_count,0,10000000);integer(&a->manual_count,0,10000000);integer(&a->hello_done,0,1);
        for(j=0;j<i;j++)if(a->reference==s->actors[j].reference && a->scene==s->actors[j].scene)error=1;
    }
}
static void journal_fields(aw_state_t *s)
{
    int i,j,n;aw_journal_entry_t *e;
    integer(&s->journal_count,0,AW_JOURNAL_ENTRIES);if(error)return;
    for(i=0;i<s->journal_count;i++){
        e=&s->journal[i];integer(&e->quest,0,s->count[AW_JOURNAL]-1);
        n=e->stage;integer(&n,1,2147483647);e->stage=n;
        n=e->days;integer(&n,0,365000);e->days=n;
        n=e->milliseconds;integer(&n,0,86399999);e->milliseconds=n;
        for(j=0;j<i;j++)if(e->quest==s->journal[j].quest && e->stage==s->journal[j].stage)error=1;
        if(error)return;
    }
}
/* Dense state in RAM; only encountered slots on disk. Reject malformed
 * facts, duplicate/unordered indices and nonzero unused storage atomically. */
static void harvest_fields(aw_harvest_state_t *h)
{
    uint32_t used=0,index=0,fact=0,previous=0,level;int i,nonzero=0;
    word(&h->slots);bytes(h->catalogue,32);
    if(h->slots<1 || h->slots>AW_HARVEST_SLOTS){error=1;return;}
    for(i=0;i<32;i++)nonzero|=h->catalogue[i];
    if(!nonzero){error=1;return;}
    if(writing){
        for(i=0;i<(int)h->slots;i++)if(h->facts[i])used++;
        for(i=(int)h->slots;i<AW_HARVEST_SLOTS;i++)if(h->facts[i])error=1;
    }
    word(&used);if(used>h->slots){error=1;return;}
    index=0;
    for(i=0;i<(int)used;i++){
        if(writing){while(index<h->slots && !h->facts[index])index++;fact=h->facts[index++];}
        word(&index);word(&fact);level=(fact>>20)&1023U;
        if(index<=previous || index>h->slots || !(fact&0xfffffU) || level<1 || level>1000 ||
           (fact&0xc0000000U)==0xc0000000U){error=1;return;}
        previous=index;if(!writing)h->facts[index-1]=fact;
    }
}
/* AWS4 feature bit 2 adds bounded equipment and dropped-world identities.
 * Older files remain byte-compatible; older readers reject this feature rather
 * than silently discarding owned items. No pointers or transient edicts persist. */
static int inventory_used(const aw_inventory_state_t *v){
    int i;if(v->next_serial || v->initialized || v->condition_known)return 1;
    for(i=0;i<AW_INVENTORY_SLOTS;i++)if(v->equipped[i][0])return 1;
    for(i=0;i<AW_INVENTORY_DROPS;i++)if(v->dropped[i].count)return 1;
    return 0;
}
static void inventory_fields(aw_state_t *s){
    aw_inventory_state_t *v=&s->inventory;aw_dropped_item_t *d;
    int i,j,k,used=0,index=0,previous=-1,n;
    word(&v->next_serial);
    word(&v->initialized);if(v->initialized>1){error=1;return;}
    word(&v->condition_known);
    for(i=0;i<AW_STATE_VALUES;i++){
        if(v->condition_known&(1U<<i)){
            if(i>=s->count[AW_ITEM] || s->values[AW_ITEM][i].value<1){error=1;return;}
            floating(&v->condition[i],0,1);
        }else if(writing && v->condition[i]!=0){error=1;return;}
    }

    for(i=0;i<AW_INVENTORY_SLOTS;i++){
        string(v->equipped[i],64);if(error)return;
        if(v->equipped[i][0]){
            n=0;for(j=0;j<AW_INVENTORY_SLOTS;j++)if(!strcmp(v->equipped[i],v->equipped[j]))n++;
            if(n>AW_StateGet(s,AW_ITEM,v->equipped[i]))error=1;
        }
    }
    if(writing)for(i=0;i<AW_INVENTORY_DROPS;i++)if(v->dropped[i].count)used++;
    integer(&used,0,AW_INVENTORY_DROPS);if(error)return;
    for(i=0;i<used;i++){
        if(writing)while(index<AW_INVENTORY_DROPS && !v->dropped[index].count)index++;
        integer(&index,0,AW_INVENTORY_DROPS-1);
        if(error || index<=previous){error=1;return;}
        previous=index;d=&v->dropped[index];index++;
        word(&d->serial);string(d->id,64);string(d->scene,16);
        n=d->count;integer(&n,1,2147483647);d->count=n;
        for(j=0;j<3;j++)floating(&d->position[j],-32767,32767);
        floating(&d->yaw,-360,360);
        word(&d->condition_known);if(d->condition_known>1){error=1;return;}
        floating(&d->condition,0,1);
        if(!d->id[0] || !d->serial || d->serial>v->next_serial || AW_MapId(d->scene)<0)error=1;
        for(k=0;k<previous;k++)if(v->dropped[k].count && v->dropped[k].serial==d->serial)error=1;
        if(error)return;
    }
}
/* AWS4 feature bit 4: the selected magic item and current enchantment charges
 * (HUD-STATS-29). Older readers reject the bit instead of losing the charge. */
static int magic_used(const aw_magic_state_t *m){return m->selected[0] || m->charge_known;}
static void magic_fields(aw_state_t *s){
    aw_magic_state_t *m=&s->magic;int i;
    string(m->selected,64);if(error)return;
    if(m->selected[0] && AW_StateGet(s,AW_ITEM,m->selected)<1){error=1;return;}
    word(&m->charge_known);
    for(i=0;i<AW_STATE_VALUES;i++){
        if(m->charge_known&(1U<<i)){
            if(i>=s->count[AW_ITEM] || s->values[AW_ITEM][i].value<1){error=1;return;}
            floating(&m->charge[i],0,1000000);
        }else if(writing && m->charge[i]!=0){error=1;return;}
    }
}
int AW_SaveEncode(unsigned char *out,int capacity,const aw_save_t *state)
{
    aw_save_t copy=*state;uint32_t size=0,crc;
    if(capacity<12 || capacity>AW_SAVE_BYTES)return 0;
    writing=out;reading=NULL;at=12;end=capacity;error=0;
    memset(out,0,capacity);fields(&copy);if(!error)journal_fields(&copy.state);
    {uint32_t features=(copy.state.harvest.slots?1U:0U)|(inventory_used(&copy.state.inventory)?2U:0U)|
        (magic_used(&copy.state.magic)?4U:0U);word(&features);}
    if(!error && copy.state.harvest.slots)harvest_fields(&copy.state.harvest);
    if(!copy.state.harvest.slots){
        int i;for(i=0;i<32;i++)if(copy.state.harvest.catalogue[i])error=1;
        for(i=0;i<AW_HARVEST_SLOTS;i++)if(copy.state.harvest.facts[i])error=1;
    }
    word(&copy.equipment);
    if((copy.equipment&~AW_EQUIPMENT_MASK) ||
       ((copy.equipment&AW_EQUIPMENT_TORCH) && !(copy.equipment&AW_EQUIPMENT_DRAWN)))error=1;
    if(!error && inventory_used(&copy.state.inventory))inventory_fields(&copy.state);
    if(!error && magic_used(&copy.state.magic))magic_fields(&copy.state);
    if(error)return 0;
    size=at;memcpy(out,"AWS4",4);at=4;word(&size);
    crc=crc32(out+12,size-12);word(&crc);return size;
}
int AW_SaveDecode(const unsigned char *data,int size,aw_save_t *out)
{
    aw_save_t candidate;uint32_t length=0,crc=0,features=0;
    if(size<12 || size>AW_SAVE_BYTES || (memcmp(data,"AWS1",4) && memcmp(data,"AWS2",4) && memcmp(data,"AWS3",4) && memcmp(data,"AWS4",4)))return 0;
    writing=NULL;reading=data;at=4;end=size;error=0;word(&length);word(&crc);
    if(length!=(uint32_t)size || crc!=crc32(data+12,size-12))return 0;
    memset(&candidate,0,sizeof(candidate));fields(&candidate);
    /* Older saves have quest indices but no chronological evidence. Do not
     * fabricate earlier entries or dates when decoding them. */
    if(!error && data[3]!='1')journal_fields(&candidate.state);
    if(!error && data[3]=='4'){word(&features);if(features>7)error=1;}
    if(!error && (data[3]=='3' || (data[3]=='4' && (features&1))))harvest_fields(&candidate.state.harvest);
    if(!error && data[3]=='4'){
        word(&candidate.equipment);
        if((candidate.equipment&~AW_EQUIPMENT_MASK) ||
           ((candidate.equipment&AW_EQUIPMENT_TORCH) && !(candidate.equipment&AW_EQUIPMENT_DRAWN)))error=1;
    }
    if(!error && data[3]=='4' && (features&2))inventory_fields(&candidate.state);
    if(!error && data[3]=='4' && (features&4))magic_fields(&candidate.state);
    if(error || at!=size)return 0;
    *out=candidate;return 1;
}
