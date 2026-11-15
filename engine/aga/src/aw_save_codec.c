/* SPDX-License-Identifier: GPL-2.0-or-later
 * Explicit little-endian schema; no raw structs, pointers or model caches. */
#include <string.h>
#include <stdlib.h>
#include <math.h>
#include "aw_save.h"
#include "aw_maps.h"
#include "aw_tryalloc.h"	/* a load's rows and sections in buffers of their own sizes (SAVE-ACTOR-ROWS-256-66) */
int aw_save_rows_form;
int (*aw_save_explored_encode)(unsigned char *out,int capacity);
void (*aw_save_explored_import)(const unsigned char *p,int bytes);
static int short_bytes;   /* AW_SaveDecodeShort */
int (*aw_save_changes_export)(aw_changes_t *changes);
void (*aw_save_changes_import)(const aw_changes_t *changes);
int (*aw_save_objects_export)(aw_changes_t *changes);
void (*aw_save_objects_import)(const aw_changes_t *changes);
int (*aw_save_actors_export)(unsigned char *out,int capacity);
void (*aw_save_actors_import)(const unsigned char *data,int bytes);
int (*aw_save_ledger_rows)(const struct aw_ledger_s *ledger);
int (*aw_save_script_export)(struct aw_ledger_s *ledger);
void (*aw_save_script_import)(const struct aw_ledger_s *ledger);
int (*aw_save_ledger_encode)(const struct aw_ledger_s *ledger,unsigned char *out,int capacity);
int (*aw_save_journal_encode)(const struct aw_jhist_s *h,unsigned char *out,int capacity);
int (*aw_save_journal_decode)(const unsigned char *data,int size,struct aw_jhist_s *into);
int (*aw_save_ledger_decode)(const unsigned char *data,int size,struct aw_ledger_s *into);
int (*aw_save_markers_encode)(unsigned char *out,int capacity);
int (*aw_save_markers_decode)(const unsigned char *p,int n,int commit);
void (*aw_save_markers_loaded)(void);
void (*aw_save_markers_reset)(void);
/* AWS4 feature bit 16: the actor record's block, u32 length then its bytes (checked by aw_actorstate.c's import);
 * read straight into the caller's buffer (its contents count only when the decode succeeds) */
static int actor_scratch_bytes;
static unsigned char *writing;
static const unsigned char *reading;
static int at,end,error;
static int row_order(const void *a,const void *b);
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
    /* the player's own class (CHARGEN-CENSUS-57): the slot after the catalogue's, its "~" ID holding its definition
     * (aw_character.c checks it and fills the fields from it) */
    if(type==1 && count>0 && count<32 && aw_classes[count].id[0]=='~')count++;
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
        if(i==count && type==1 && value[0]=='~' && aw_class_count>0 && aw_class_count<32){
            /* a saved own class: into the slot; aw_character.c rejects an invalid definition when it is used */
            memcpy(aw_classes[aw_class_count].id,value,64);*index=aw_class_count;
        }else if(i==count)error=1;else *index=i;
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
    for(i=0;i<2;i++){
        integer(&s->state.count[i],0,AW_STATE_VALUES);if(error)return;
        for(j=0;j<s->state.count[i];j++){
            aw_value_t *v=&s->state.values[i][j];
            string(v->id,64);if(error)return;
            number=writing?(uint32_t)v->value:0;word(&number);
            if(!writing)v->value=(int32_t)number;
            if(!v->id[0])error=1;
            for(k=0;k<j;k++)if(!strcmp(v->id,s->state.values[i][k].id))error=1;
        }
    }
    /* the item rows (INVENTORY-ORIGINAL-LIMITS-61): the same bytes as before (a count, then a 64-byte id and a count
     * per row, in table order); read into the decoded state's own table (aw_state.h OWNERSHIP) */
    n=writing?s->state.items.count:0;integer(&n,0,AW_ITEM_KINDS_MAX);if(error)return;
    for(j=0;j<n;j++){
        char item[64];int32_t value=0;
        memset(item,0,sizeof(item));
        if(writing){strcpy(item,AW_ITEM_ID(&s->state,j));value=AW_ITEM_ROW(&s->state,j)->value;}
        string(item,64);if(error)return;
        number=writing?(uint32_t)value:0;word(&number);
        if(writing)continue;
        value=(int32_t)number;
        if(!item[0] || value<0 || AW_ItemIndex(&s->state,item)>=0 || !AW_ItemAppend(&s->state,item,value)){error=1;return;}
    }
    if(AW_StateGet(&s->state,AW_GLOBAL,"CharGenState")!=-1)error=1;
    if(!error && (aw_parts[c->head].race!=c->race || aw_parts[c->hair].race!=c->race ||
       aw_parts[c->head].female!=c->female || aw_parts[c->hair].female!=c->female ||
       aw_parts[c->head].kind!=0 || aw_parts[c->hair].kind!=1))error=1;
    /* the 48-byte actor rows of the fields (AWS1-4 before v0.0.66, at most 256): a save now writes none here (its rows
     * are packed, feature 8192) unless aw_save_rows_form is 1; read into the decoded save's own rows, sorted */
    n=writing?(aw_save_rows_form==1?s->actor_count:0):0;
    integer(&n,0,AW_SAVE_ACTORS);
    if(error)return;
    if(!writing){s->actor_count=0;if(n && !AW_SaveActorsReserve(s,n)){error=1;return;}s->actor_count=n;}
    for(i=0;i<n;i++){
        aw_saved_actor_t *a=&s->actors[i];int scene=a->scene;
        word(&a->reference);integer(&scene,0,AW_SCENE_COUNT-1);
        if(!writing){a->scene=(unsigned short)scene;a->fields=AW_ROW_ALL;}
        /* The ID range has a gap between interiors and extra towns. */
        if(!a->reference || a->reference>0xffffffU || (!error && !AW_MapName(a->scene)[0]))error=1;
        for(j=0;j<3;j++){floating(&a->position[j],-32767,32767);floating(&a->angles[j],-360,360);}
        floating(&a->health,-10000,100000);
        integer(&a->hello_count,0,10000000);integer(&a->manual_count,0,10000000);integer(&a->hello_done,0,1);
        if(writing)for(j=0;j<i;j++)if(a->reference==s->actors[j].reference && a->scene==s->actors[j].scene)error=1;
        if(error)return;
    }
    if(!writing && n>1){   /* sorted once, a row twice refused (was a search of every earlier row) */
        qsort(s->actors,(size_t)n,sizeof(aw_saved_actor_t),row_order);
        for(i=1;i<n;i++)if(!row_order(&s->actors[i-1],&s->actors[i]))error=1;
    }
}
/* AWS4 feature bit 8192 (SAVE-ACTOR-ROWS-256-66): the saved actor rows, packed. u8 form (1), u16 places; per place
 * (ascending) u16 scene, u16 rows; per row (ascending) a u24 reference, a u8 of what follows (ROW_*), then only that,
 * in bit order. Whole units for the place (the rows' range, +-32767), 360/256 degrees for a facing: a greeted NPC is
 * 4 to 6 bytes, a builder's role 11 to 15, the most any row takes 25 (was 48 for every row). */
#define ROW_POSITION 1U   /* 3 x s16 position, u8 yaw */
#define ROW_TILT 2U       /* u8 pitch, u8 roll (with ROW_POSITION only; written when either is not 0) */
#define ROW_HEALTH16 4U   /* s16 a whole health */
#define ROW_HEALTH32 8U   /* f32 any other health (never with ROW_HEALTH16) */
#define ROW_HELLO 16U     /* the hello count, 7 bits a byte from the low end (1..10,000,000) */
#define ROW_MANUAL 32U    /* the manual greeting count, the same */
#define ROW_DONE 64U      /* the greeting done (no bytes) */
#define ROW_KNOWN 127U
static int row_compare(const aw_saved_actor_t *a,unsigned scene,uint32_t reference)
{
    if(a->scene!=scene)return a->scene<scene?-1:1;
    return a->reference==reference?0:a->reference<reference?-1:1;
}
static int row_order(const void *a,const void *b)
{
    const aw_saved_actor_t *y=(const aw_saved_actor_t *)b;
    return row_compare((const aw_saved_actor_t *)a,y->scene,y->reference);
}
int AW_SaveActorFind(const aw_save_t *s,uint32_t reference,int scene)
{
    int lo=0,hi=s->actor_count-1,mid,c;
    while(lo<=hi){
        mid=(lo+hi)/2;c=row_compare(&s->actors[mid],(unsigned)scene,reference);
        if(!c)return mid;
        if(c<0)lo=mid+1;else hi=mid-1;
    }
    return -1-lo;
}
int AW_SaveActorsReserve(aw_save_t *s,int want)
{
    aw_saved_actor_t *grown;int capacity;
    if(want<=s->actor_capacity)return 1;
    if(want>AW_SAVE_ACTOR_ROWS_MAX)return 0;
    capacity=(want+AW_SAVE_ACTOR_ROW_BLOCK-1)/AW_SAVE_ACTOR_ROW_BLOCK*AW_SAVE_ACTOR_ROW_BLOCK;
    grown=(aw_saved_actor_t *)AW_TryRealloc(s->actors,(unsigned long)sizeof(aw_saved_actor_t)*(unsigned long)capacity);
    if(!grown){short_bytes=(int)sizeof(aw_saved_actor_t)*capacity;return 0;}
    s->actors=grown;s->actor_capacity=capacity;return 1;
}
int AW_SaveActorsCopy(aw_save_t *to,const aw_saved_actor_t *rows,int count)
{
    aw_saved_actor_t *copy=NULL;int capacity=0;
    if(count>0){
        capacity=(count+AW_SAVE_ACTOR_ROW_BLOCK-1)/AW_SAVE_ACTOR_ROW_BLOCK*AW_SAVE_ACTOR_ROW_BLOCK;
        copy=(aw_saved_actor_t *)AW_TryMalloc((unsigned long)sizeof(aw_saved_actor_t)*(unsigned long)capacity);
        if(!copy){short_bytes=(int)sizeof(aw_saved_actor_t)*capacity;return 0;}
        memcpy(copy,rows,sizeof(aw_saved_actor_t)*(size_t)count);
    }
    to->actors=copy;to->actor_count=count;to->actor_capacity=capacity;
    return 1;
}
void AW_SaveActorsFree(aw_save_t *s)
{
    if(!s)return;
    free(s->actors);s->actors=NULL;s->actor_count=s->actor_capacity=0;
}
/* a place's save ID a row may name: one this engine names, or one of an expansion's ranges (named or not: an engine
 * without that expansion's table keeps the row for the save it came from) */
static int scene_known(int s){return s>=0 && s<AW_LAYER_ROOM_END && (AW_MapName(s)[0] || AW_MapLayer(s));}
static int angle_byte(float a){return (int)floorf((a-360.0f*floorf(a/360.0f))*256.0f/360.0f+.5f)&255;}
static int whole16(float h){return h==floorf(h) && h>=-32768.0f && h<=32767.0f;}
/* what a row writes (ROW_*): 0 when it holds nothing */
static unsigned row_mask(const aw_saved_actor_t *a)
{
    unsigned m=0;
    if(a->fields&AW_ROW_PLACE){m|=ROW_POSITION;if(angle_byte(a->angles[0]) || angle_byte(a->angles[2]))m|=ROW_TILT;}
    if(a->fields&AW_ROW_HEALTH)m|=whole16(a->health)?ROW_HEALTH16:ROW_HEALTH32;
    if(a->fields&AW_ROW_GREET){
        if(a->hello_count)m|=ROW_HELLO;
        if(a->manual_count)m|=ROW_MANUAL;
        if(a->hello_done)m|=ROW_DONE;
    }
    return m;
}
static int count_bytes(uint32_t v){int n=1;while(v>=128){v>>=7;n++;}return n;}
static int row_bytes(const aw_saved_actor_t *a,unsigned m)
{
    return 4+((m&ROW_POSITION)?7:0)+((m&ROW_TILT)?2:0)+((m&ROW_HEALTH16)?2:0)+((m&ROW_HEALTH32)?4:0)+
           ((m&ROW_HELLO)?count_bytes((uint32_t)a->hello_count):0)+((m&ROW_MANUAL)?count_bytes((uint32_t)a->manual_count):0);
}
int AW_SaveActorRowsBytes(const aw_save_t *s)
{
    int i,n=0,places=0,scene=-1;unsigned m;
    for(i=0;i<s->actor_count;i++){
        if(!(m=row_mask(&s->actors[i])))continue;
        if(s->actors[i].scene!=scene){scene=s->actors[i].scene;places++;}
        n+=row_bytes(&s->actors[i],m);
    }
    return n?4+3+4*places+n:0;
}
static void put8(unsigned v){unsigned char b=(unsigned char)v;bytes(&b,1);}
static void put16(unsigned v){unsigned char b[2];b[0]=(unsigned char)v;b[1]=(unsigned char)(v>>8);bytes(b,2);}
static unsigned get8(void){unsigned char b=0;bytes(&b,1);return b;}
static unsigned get16(void){unsigned char b[2]={0,0};bytes(b,2);return (unsigned)b[0]|((unsigned)b[1]<<8);}
static void put_count(uint32_t v){do{put8((v&127U)|(v>=128?128U:0U));v>>=7;}while(v);}
static uint32_t get_count(void)
{
    uint32_t v=0,b;int shift=0;
    do{b=get8();if(shift>21){error=1;return 0;}v|=(b&127U)<<shift;shift+=7;}while((b&128U) && !error);
    if(v<1 || v>10000000)error=1;
    return v;
}
static void rows_encode(const aw_save_t *s)
{
    int i,j,k,places_at=0,places=0,count_at=0,rows=0,scene=-1;unsigned m;uint32_t length=0;int length_at=at,start;
    word(&length);start=at;put8(1);places_at=at;put16(0);
    for(i=0;i<s->actor_count && !error;i++){
        const aw_saved_actor_t *a=&s->actors[i];
        if(i && row_order(&s->actors[i-1],a)>=0){error=1;return;}   /* sorted, each once */
        if(!a->reference || a->reference>0xffffffU || !scene_known(a->scene)){error=1;return;}
        if(!(m=row_mask(a)))continue;
        if(a->scene!=scene){
            if(scene>=0){writing[count_at]=(unsigned char)rows;writing[count_at+1]=(unsigned char)(rows>>8);}
            if(places==65535){error=1;return;}
            scene=a->scene;places++;put16((unsigned)scene);count_at=at;put16(0);rows=0;
        }
        put8(a->reference&255U);put8((a->reference>>8)&255U);put8((a->reference>>16)&255U);put8(m);
        if(m&ROW_POSITION){
            for(j=0;j<3;j++){
                float p=floorf(a->position[j]+.5f);
                if(!(p>=-32767 && p<=32767)){error=1;return;}
                k=(int)p;put16((unsigned)k&0xffffU);
            }
            put8((unsigned)angle_byte(a->angles[1]));
            if(m&ROW_TILT){put8((unsigned)angle_byte(a->angles[0]));put8((unsigned)angle_byte(a->angles[2]));}
        }
        if(!(a->health>=-10000 && a->health<=100000) && (m&(ROW_HEALTH16|ROW_HEALTH32))){error=1;return;}
        if(m&ROW_HEALTH16)put16((unsigned)(int)a->health&0xffffU);
        if(m&ROW_HEALTH32){float h=a->health;floating(&h,-10000,100000);}
        if(a->hello_count<0 || a->hello_count>10000000 || a->manual_count<0 || a->manual_count>10000000 ||
           a->hello_done<0 || a->hello_done>1){error=1;return;}
        if(m&ROW_HELLO)put_count((uint32_t)a->hello_count);
        if(m&ROW_MANUAL)put_count((uint32_t)a->manual_count);
        if(++rows>65535){error=1;return;}
    }
    if(error)return;
    if(scene>=0){writing[count_at]=(unsigned char)rows;writing[count_at+1]=(unsigned char)(rows>>8);}
    writing[places_at]=(unsigned char)places;writing[places_at+1]=(unsigned char)(places>>8);
    length=(uint32_t)(at-start);
    writing[length_at]=(unsigned char)length;writing[length_at+1]=(unsigned char)(length>>8);
    writing[length_at+2]=(unsigned char)(length>>16);writing[length_at+3]=(unsigned char)(length>>24);
}
static void rows_decode(aw_save_t *s)
{
    uint32_t length=0,reference;int stop,places,p,rows,r,scene,last_scene=-1,j;unsigned m;
    word(&length);
    if(error || length<3 || at>end-(int)length){error=1;return;}
    stop=at+(int)length;
    if(get8()!=1){error=1;return;}
    places=(int)get16();
    if(error || places<1){error=1;return;}
    for(p=0;p<places && !error;p++){
        uint32_t last_reference=0;
        scene=(int)get16();rows=(int)get16();
        if(error || scene<=last_scene || !scene_known(scene) || rows<1 || stop-at<4*rows ||
           !AW_SaveActorsReserve(s,s->actor_count+rows)){error=1;return;}
        last_scene=scene;
        for(r=0;r<rows && !error;r++){
            aw_saved_actor_t *a=&s->actors[s->actor_count];
            reference=get8();reference|=get8()<<8;reference|=get8()<<16;m=get8();
            if(error || !reference || reference<=last_reference || !m || (m&~ROW_KNOWN) ||
               ((m&ROW_TILT) && !(m&ROW_POSITION)) || ((m&ROW_HEALTH16) && (m&ROW_HEALTH32))){error=1;return;}
            last_reference=reference;
            memset(a,0,sizeof(*a));a->reference=reference;a->scene=(unsigned short)scene;
            if(m&ROW_POSITION){
                for(j=0;j<3;j++)a->position[j]=(float)(int16_t)get16();
                a->angles[1]=get8()*360.0f/256.0f;
                if(m&ROW_TILT){a->angles[0]=get8()*360.0f/256.0f;a->angles[2]=get8()*360.0f/256.0f;}
                a->fields|=AW_ROW_PLACE;
            }
            if(m&ROW_HEALTH16){a->health=(float)(int16_t)get16();a->fields|=AW_ROW_HEALTH;if(a->health<-10000)error=1;}
            if(m&ROW_HEALTH32){floating(&a->health,-10000,100000);a->fields|=AW_ROW_HEALTH;}
            if(m&(ROW_HELLO|ROW_MANUAL|ROW_DONE)){
                a->fields|=AW_ROW_GREET;
                if(m&ROW_HELLO)a->hello_count=(int)get_count();
                if(m&ROW_MANUAL)a->manual_count=(int)get_count();
                a->hello_done=(m&ROW_DONE)?1:0;
            }
            if(at>stop){error=1;return;}
            s->actor_count++;
        }
    }
    if(at!=stop)error=1;
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
/* AWS4 feature bit 256 (COLLECT-CAPACITY-REJECTED-60): more than 32 kinds of item. The item rows themselves need
 * nothing new (a count, then the rows); the condition and charge marks, one word for 32 items before, are followed by
 * AW_ITEM_WORDS-1 more words. Written only when the table holds more than 32 rows, so a save of up to 32 is
 * byte for byte as before; older readers refuse the bit (and the count) instead of losing items. */
/* INVENTORY-ORIGINAL-LIMITS-61, AWS4 feature bit 512: any number of kinds; the marks are ceil(kinds / 32) words. A
 * feature 256 save (the 128-kind table of the v0.0.61 line) has 4 words and up to 128 kinds; neither bit: 1 word,
 * up to 32 kinds (a save of up to 32 kinds is written byte for byte as before). */
static int mark_words;
static int items_marked(const aw_state_t *s,unsigned flag){
    int i;for(i=0;i<s->items.count;i++)if(AW_ITEM_FLAGS(AW_ITEM_ROW(s,i))&flag)return 1;
    return 0;
}
/* the mark words of FLAG, then the value of every marked row (condition 0..1 or charge 0..1000000) */
static void item_marks(aw_state_t *s,unsigned flag){
    int w,b,i;uint32_t bits;
    for(w=0;w<mark_words && !error;w++){
        bits=0;
        if(writing)for(b=0;b<32;b++){i=w*32+b;if(i<s->items.count && (AW_ITEM_FLAGS(AW_ITEM_ROW(s,i))&flag))bits|=1U<<b;}
        word(&bits);
        for(b=0;b<32 && !error;b++)if(bits&(1U<<b)){
            aw_item_row_t *r;i=w*32+b;
            if(i>=s->items.count || (r=AW_ITEM_ROW(s,i))->value<1){error=1;return;}
            if(!writing)AW_ITEM_SET_FLAG(r,flag);
            if(flag==AW_ITEM_CONDITION)floating(&r->condition,0,1);else floating(&r->charge,0,1000000);
        }
    }
}
/* AWS4 feature bit 2 adds bounded equipment and dropped-world identities.
 * Older files remain byte-compatible; older readers reject this feature rather
 * than silently discarding owned items. No pointers or transient edicts persist. */
static int inventory_used(const aw_state_t *s){
    const aw_inventory_state_t *v=&s->inventory;
    int i;if(v->next_serial || v->initialized || items_marked(s,AW_ITEM_CONDITION))return 1;
    for(i=0;i<AW_INVENTORY_SLOTS;i++)if(v->equipped[i][0])return 1;
    for(i=0;i<AW_INVENTORY_DROPS;i++)if(v->dropped[i].count)return 1;
    return 0;
}
static void inventory_fields(aw_state_t *s){
    aw_inventory_state_t *v=&s->inventory;aw_dropped_item_t *d;
    int i,j,k,used=0,index=0,previous=-1,n;
    word(&v->next_serial);
    word(&v->initialized);if(v->initialized>1){error=1;return;}
    item_marks(s,AW_ITEM_CONDITION);if(error)return;

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
static int magic_used(const aw_state_t *s){return s->magic.selected[0] || items_marked(s,AW_ITEM_CHARGE);}
static void magic_fields(aw_state_t *s){
    aw_magic_state_t *m=&s->magic;
    string(m->selected,64);if(error)return;
    if(m->selected[0] && AW_StateGet(s,AW_ITEM,m->selected)<1){error=1;return;}
    item_marks(s,AW_ITEM_CHARGE);
}
/* AWS4 feature bit 64 (LEVEL-UP-58): the player's levelling (aw_levelup.h): each skill's progress, the level
 * progress, the raises per attribute and per specialization. Written only when any of it is set; older saves load
 * with all of it 0, older readers refuse the bit instead of losing it. */
static int levelling_used(const aw_character_t *c){
    int i;if(c->level_progress)return 1;
    for(i=0;i<27;i++)if(c->progress[i]!=0)return 1;
    for(i=0;i<8;i++)if(c->raises[i])return 1;
    for(i=0;i<3;i++)if(c->special[i])return 1;
    return 0;
}
static void levelling_fields(aw_character_t *c){
    int i,n;
    for(i=0;i<27;i++)floating(&c->progress[i],0,1);
    n=c->level_progress;integer(&n,0,10000);c->level_progress=(short)n;
    for(i=0;i<8;i++){n=c->raises[i];integer(&n,0,10000);c->raises[i]=(short)n;}
    for(i=0;i<3;i++){n=c->special[i];integer(&n,0,10000);c->special[i]=(short)n;}
}
/* AWS4 feature bit 1024 (SKILL-BOOKS-MISSING-62): the skill books read, u32 words (1..AW_BOOKS_READ_MAX/32: up to
 * the last word with a bit) then the words; written only when any book is read, older readers refuse the bit. */
static int books_words(const aw_character_t *c){
    int n=AW_BOOKS_READ_MAX/32;
    while(n>0 && !c->books_read[n-1])n--;
    return n;
}
static void books_fields(aw_character_t *c){
    int n=books_words(c),i;
    integer(&n,1,AW_BOOKS_READ_MAX/32);if(error)return;
    for(i=0;i<n && !error;i++){uint32_t w=(uint32_t)c->books_read[i];word(&w);c->books_read[i]=w;}
}
/* AWS4 feature bit 16384 (SAVE-ITEM-INSTANCES-ONE-PER-KIND-66): the item instances (aw_state.h: a copy, or equal
 * copies, of a kind with a condition or charge of its own, or the copy a slot wears), and which copy each slot wears and
 * the magic selection names: u32 instances, each u32 serial, u32 row, i32 count, u32 flags, f32 condition with the
 * condition mark, f32 charge with the charge mark; then AW_INVENTORY_SLOTS x u32 the slots' serials (0 a plain copy),
 * u32 the selected serial. Checked: serials unique and within the drops' allocator, rows of the table, a row's instance
 * copies never more than its count, a slot's or the selection's serial an instance of the kind it holds. Written only
 * when there is an instance or a serial, so a save without them is byte for byte as before; older readers refuse the bit
 * rather than merging the copies. */
static int instances_used(const aw_state_t *s){
    int i;
    if(s->items.inst_count || s->magic.selected_serial)return 1;
    for(i=0;i<AW_INVENTORY_SLOTS;i++)if(s->inventory.equipped_serial[i])return 1;
    return 0;
}
static void instance_fields(aw_state_t *s){
    int n=writing?s->items.inst_count:0,i,k;uint32_t u;
    integer(&n,0,AW_ITEM_INSTANCES_MAX);if(error)return;
    for(i=0;i<n && !error;i++){
        aw_item_inst_t x;int c;
        if(writing)x=s->items.inst[i];else memset(&x,0,sizeof(x));
        word(&x.serial);u=(uint32_t)x.row;word(&u);x.row=(int32_t)u;
        c=x.count;integer(&c,1,2147483647);x.count=c;word(&x.flags);
        if(error)return;
        if(!x.serial || x.serial>s->inventory.next_serial || (x.flags&~(AW_ITEM_CONDITION|AW_ITEM_CHARGE)) ||
           x.row<0 || x.row>=s->items.count){error=1;return;}
        if(x.flags&AW_ITEM_CONDITION)floating(&x.condition,0,1);
        if(x.flags&AW_ITEM_CHARGE)floating(&x.charge,0,1000000);
        if(error)return;
        if(!writing && (AW_ItemInstFind(s,x.serial)>=0 || x.count>AW_ItemPlain(s,x.row) || !AW_ItemInstAppend(s,&x))){error=1;return;}
    }
    for(k=0;k<AW_INVENTORY_SLOTS && !error;k++){
        word(&s->inventory.equipped_serial[k]);
        if(s->inventory.equipped_serial[k]){
            int j=AW_ItemInstFind(s,s->inventory.equipped_serial[k]);
            if(j<0 || !s->inventory.equipped[k][0] || AW_ItemIndex(s,s->inventory.equipped[k])!=AW_ItemInst(s,j)->row)error=1;
        }
    }
    if(error)return;
    word(&s->magic.selected_serial);
    if(s->magic.selected_serial){
        int j=AW_ItemInstFind(s,s->magic.selected_serial);
        if(j<0 || !s->magic.selected[0] || AW_ItemIndex(s,s->magic.selected)!=AW_ItemInst(s,j)->row)error=1;
    }
}
/* AWS4 feature bit 8: the world-state change list (aw_save.h). Entries strictly ascending by key, each checked
 * field by field; 36 bytes each on disk. The sorted copy and the decoder's scratch live here, off the stack. */
static aw_changes_t change_scratch;
static int change_order(const void *a,const void *b)
{
    uint32_t x=((const aw_change_t *)a)->key,y=((const aw_change_t *)b)->key;
    return x<y?-1:x>y;
}
uint32_t AW_SaveChangeKey(uint32_t reference)
{
    return reference>=0x800000U && reference<=0xffffffU?AW_CHANGE_BUILDER|(reference-0x800000U):reference;
}
static void changes_fields(aw_changes_t *c)
{
    int i;uint32_t packed,previous=0,where;
    integer(&c->count,1,AW_SAVE_CHANGES);if(error)return;
    for(i=0;i<c->count;i++){
        aw_change_t *e=&c->entry[i];
        word(&e->key);
        packed=writing?(e->flags&0xffffU)|((e->pick&0xffffU)<<16):0;word(&packed);
        if(!writing){e->flags=packed&0xffffU;e->pick=packed>>16;}
        where=writing?(uint32_t)e->where:0;word(&where);if(!writing)e->where=(int32_t)where;
        floating(&e->position[0],-1000000,1000000);floating(&e->position[1],-1000000,1000000);
        floating(&e->position[2],-1000000,1000000);floating(&e->yaw,-720,720);
        floating(&e->health,-10000,100000);floating(&e->hours,0,10000000);
        if(error)return;
        if(!e->key || (e->key&0x7f000000U) || !(e->key&0xffffffU) || (i && e->key<=previous) ||
           !e->flags || (e->flags&~AW_CHANGE_FLAGS) || e->flags>0xffffU ||
           ((e->flags&AW_CHANGE_LOCK_LEVEL) && !(e->flags&AW_CHANGE_LOCK)) ||
           ((e->flags&AW_CHANGE_LOCK_LEVEL)>>AW_CHANGE_LOCK_SHIFT)>100U ||
           ((e->flags&AW_CHANGE_PICK)?(e->pick<1 || e->pick>0x8001U):e->pick!=0)){error=1;return;}
        if(e->flags&AW_CHANGE_ROOM){
            if((e->flags&AW_CHANGE_SCENE) || e->where<1 || e->where>0xffffff){error=1;return;}}
        else if(e->flags&AW_CHANGE_SCENE){if(e->where<0 || e->where>=AW_SCENE_COUNT || !AW_MapName(e->where)[0]){error=1;return;}}
        else{
            int cx=(int16_t)((uint32_t)e->where>>16),cy=(int16_t)((uint32_t)e->where&0xffffU);
            if(cx<-1024 || cx>1024 || cy<-1024 || cy>1024){error=1;return;}
        }
        previous=e->key;
    }
}
int AW_SaveFoldActors(const aw_save_t *state,aw_changes_t *changes)
{
    int i,j,added=0;uint32_t key;
    for(i=0;i<state->actor_count;i++){
        const aw_saved_actor_t *a=&state->actors[i];
        if(!(a->fields&AW_ROW_PLACE))continue;   /* a row of greetings only: no place to fold */
        key=AW_SaveChangeKey(a->reference);
        for(j=0;j<changes->count;j++)if(changes->entry[j].key==key)break;
        if(j<changes->count || changes->count>=AW_SAVE_CHANGES)continue;
        {
            aw_change_t *e=&changes->entry[changes->count++];
            memset(e,0,sizeof(*e));e->key=key;e->flags=AW_CHANGE_MOVED|AW_CHANGE_SCENE;e->where=a->scene;
            memcpy(e->position,a->position,sizeof(e->position));e->yaw=a->angles[1];e->health=a->health;
            added++;
        }
    }
    return added;
}
int AW_SaveEncode(unsigned char *out,int capacity,const aw_save_t *state)
{
    return AW_SaveEncodeChanges(out,capacity,state,NULL);
}
int AW_SaveEncodeChanges(unsigned char *out,int capacity,const aw_save_t *state,const aw_changes_t *changes)
{
    aw_save_t copy=*state;uint32_t size=0,crc;int listed=changes && changes->count>0;
    int actors=changes && changes->actors && changes->actor_bytes>0;
    int ledgered=changes && changes->ledger && aw_save_ledger_rows && aw_save_ledger_rows(changes->ledger)>0;
    int dated=changes && changes->journal && aw_save_journal_encode && aw_save_journal_encode(changes->journal,NULL,0)>0;
    int marked=changes && changes->markers && aw_save_markers_encode && aw_save_markers_encode(NULL,0)>0;
    int explored=changes && changes->explored && aw_save_explored_encode && aw_save_explored_encode(NULL,0)>0;
    int packed=!aw_save_rows_form && AW_SaveActorRowsBytes(state)>0;
    int instanced=instances_used(&state->state);
    if(capacity<12 || capacity>AW_SAVE_MAX_BYTES)return 0;
    writing=out;reading=NULL;at=12;end=capacity;error=0;
    memset(out,0,capacity);fields(&copy);if(!error)journal_fields(&copy.state);
    mark_words=copy.state.items.count>32?(copy.state.items.count+31)/32:1;
    {uint32_t features=(copy.state.harvest.slots?1U:0U)|(inventory_used(&copy.state)?2U:0U)|
        (magic_used(&copy.state)?4U:0U)|(listed?8U:0U)|(actors?16U:0U)|(ledgered?32U:0U)|
        (levelling_used(&copy.character)?64U:0U)|(dated?128U:0U)|(copy.state.items.count>32?512U:0U)|
        (books_words(&copy.character)?1024U:0U)|(marked?2048U:0U)|(explored?4096U:0U)|(packed?8192U:0U)|
        (instanced?16384U:0U);
     word(&features);}
    if(!error && copy.state.harvest.slots)harvest_fields(&copy.state.harvest);
    if(!copy.state.harvest.slots){
        int i;for(i=0;i<32;i++)if(copy.state.harvest.catalogue[i])error=1;
        for(i=0;i<AW_HARVEST_SLOTS;i++)if(copy.state.harvest.facts[i])error=1;
    }
    word(&copy.equipment);
    if((copy.equipment&~AW_EQUIPMENT_MASK) ||
       ((copy.equipment&AW_EQUIPMENT_TORCH) && !(copy.equipment&AW_EQUIPMENT_DRAWN)))error=1;
    if(!error && inventory_used(&copy.state))inventory_fields(&copy.state);
    if(!error && magic_used(&copy.state))magic_fields(&copy.state);
    if(!error && levelling_used(&copy.character))levelling_fields(&copy.character);
    if(!error && books_words(&copy.character))books_fields(&copy.character);
    if(!error && instanced)instance_fields(&copy.state);   /* feature 16384: the item instances */
    if(!error && packed)rows_encode(&copy);   /* feature 8192: the saved actor rows, packed (SAVE-ACTOR-ROWS-256-66) */
    if(!error && listed){
        if(changes->count>AW_SAVE_CHANGES)return 0;
        change_scratch.count=changes->count;
        memcpy(change_scratch.entry,changes->entry,sizeof(aw_change_t)*changes->count);
        qsort(change_scratch.entry,change_scratch.count,sizeof(aw_change_t),change_order);
        changes_fields(&change_scratch);
    }
    if(!error && actors){
        uint32_t n=(uint32_t)changes->actor_bytes;
        if(n>AW_SAVE_ACTOR_MAX_BYTES || changes->actor_bytes>changes->actor_capacity)return 0;
        word(&n);bytes(changes->actors,(int)n);
    }
    /* feature 128 (JOURNAL-ORIGINAL-VIEW-59): u32 length, then the dated journal history's own form (aw_jhist.c) */
    if(!error && dated){
        int need=aw_save_journal_encode(changes->journal,NULL,0);uint32_t n=(uint32_t)need;
        word(&n);
        if(error || at>end-need || aw_save_journal_encode(changes->journal,out+at,need)!=need)return 0;
        at+=need;
    }
    /* feature 2048 (MAP-MULTI-MARKERS-66): u32 length, then the map markers' own block (aw_mapmarks.c AWMK) */
    if(!error && marked){
        int need=aw_save_markers_encode(NULL,0);uint32_t n=(uint32_t)need;
        word(&n);
        if(error || at>end-need || aw_save_markers_encode(out+at,need)!=need)return 0;
        at+=need;
    }
    /* feature 4096 (MAP-EXPLORED-SAVE-BLOCK-66): u32 length, then the explored map's own form (aw_mapfog.c AWFG) */
    if(!error && explored){
        int need=aw_save_explored_encode(NULL,0);uint32_t n=(uint32_t)need;
        word(&n);
        if(error || at>end-need || aw_save_explored_encode(out+at,need)!=need)return 0;
        at+=need;
    }
    /* feature 32: u32 length, then the world change list's own form (aw_ledger.c), checked row by row */
    if(!error && ledgered){
        int need=aw_save_ledger_encode?aw_save_ledger_encode(changes->ledger,NULL,0):0;uint32_t n=(uint32_t)need;
        if(need<=0)return 0;
        word(&n);
        if(error || at>end-need)return 0;
        if(aw_save_ledger_encode(changes->ledger,out+at,need)!=need)return 0;
        at+=need;
    }
    if(error)return 0;
    size=at;memcpy(out,"AWS4",4);at=4;word(&size);
    crc=crc32(out+12,size-12);word(&crc);return size;
}
int AW_SaveDecode(const unsigned char *data,int size,aw_save_t *out)
{
    return AW_SaveDecodeChanges(data,size,out,NULL);
}
static int decode(const unsigned char *data,int size,aw_save_t *out,aw_changes_t *changes,aw_save_t *candidate);
/* INVENTORY-ORIGINAL-LIMITS-61: the decoded save owns its item table (aw_state.h OWNERSHIP); a refused save gives its
 * rows back here. The candidate lives off the Amiga task stack. */
int AW_SaveDecodeChanges(const unsigned char *data,int size,aw_save_t *out,aw_changes_t *changes)
{
    static aw_save_t candidate;int ok;
    memset(&candidate,0,sizeof(candidate));
    short_bytes=0;
    ok=decode(data,size,out,changes,&candidate);
    if(!ok){AW_ItemsFree(&candidate.state);AW_SaveActorsFree(&candidate);}
    memset(&candidate,0,sizeof(candidate));
    return ok;
}
void AW_SaveRelease(aw_save_t *save){if(save){AW_ItemsFree(&save->state);AW_SaveActorsFree(save);}}
int AW_SaveBlockBytes(float kb)
{
    int k;
    if(kb!=kb)k=AW_SAVE_BLOCK_KB_DEFAULT;          /* NaN */
    else if(kb<AW_SAVE_BLOCK_KB_MIN)k=AW_SAVE_BLOCK_KB_MIN;
    else if(kb>AW_SAVE_BLOCK_KB_MAX)k=AW_SAVE_BLOCK_KB_MAX;
    else k=(int)kb;
    return k*1024;
}
void AW_SaveChangesFree(aw_changes_t *c)
{
    if(!c)return;
    if(c->take){free(c->actors);c->actors=NULL;c->actor_capacity=c->actor_bytes=0;}
    free(c->explored_data);c->explored_data=NULL;c->explored_bytes=0;
}
int AW_SaveDecodeShort(void){return short_bytes;}
/* a kept section's copy in a buffer of its own size; NULL when memory says no (counted in short_bytes) */
static unsigned char *taken(const unsigned char *p,uint32_t n)
{
    unsigned char *b=(unsigned char *)AW_TryMalloc((unsigned long)n);
    if(!b){short_bytes=(int)n;return NULL;}
    memcpy(b,p,n);return b;
}
static int decode(const unsigned char *data,int size,aw_save_t *out,aw_changes_t *changes,aw_save_t *candidate_p)
{
#define candidate (*candidate_p)
    uint32_t length=0,crc=0,features=0,dated_n=0,marks_n=0,explored_n=0;
    const unsigned char *dated=NULL,*marks=NULL,*explored=NULL,*actor_src=NULL;int actor_kept=0;
    if(size<12 || size>AW_SAVE_MAX_BYTES || (memcmp(data,"AWS1",4) && memcmp(data,"AWS2",4) && memcmp(data,"AWS3",4) && memcmp(data,"AWS4",4)))return 0;
    writing=NULL;reading=data;at=4;end=size;error=0;word(&length);word(&crc);
    if(length!=(uint32_t)size || crc!=crc32(data+12,size-12))return 0;
    memset(&candidate,0,sizeof(candidate));fields(&candidate);
    /* Older saves have quest indices but no chronological evidence. Do not
     * fabricate earlier entries or dates when decoding them. */
    if(!error && data[3]!='1')journal_fields(&candidate.state);
    if(!error && data[3]=='4'){word(&features);if(features>0x7fff)error=1;}   /* bits 1..16384 */
    /* more than 32 kinds of item: feature 256 (4 mark words, up to 128 kinds; the v0.0.61 line's 128-kind table) or
     * feature 512 (ceil(kinds / 32) words), never both; 32 or fewer: neither (none before AWS4) */
    if((features&256) && (features&512))error=1;
    if(!error && ((features&768)!=0)!=(candidate.state.items.count>32))error=1;
    if(!error && (features&256) && candidate.state.items.count>128)error=1;
    mark_words=(features&256)?4:(features&512)?(candidate.state.items.count+31)/32:1;
    if(!error && (data[3]=='3' || (data[3]=='4' && (features&1))))harvest_fields(&candidate.state.harvest);
    if(!error && data[3]=='4'){
        word(&candidate.equipment);
        if((candidate.equipment&~AW_EQUIPMENT_MASK) ||
           ((candidate.equipment&AW_EQUIPMENT_TORCH) && !(candidate.equipment&AW_EQUIPMENT_DRAWN)))error=1;
    }
    if(!error && data[3]=='4' && (features&2))inventory_fields(&candidate.state);
    if(!error && data[3]=='4' && (features&4))magic_fields(&candidate.state);
    if(!error && data[3]=='4' && (features&64))levelling_fields(&candidate.character);
    if(!error && data[3]=='4' && (features&1024))books_fields(&candidate.character);
    if(!error && data[3]=='4' && (features&16384))instance_fields(&candidate.state);   /* the item instances */
    /* feature 8192: the packed actor rows, never beside the old form (a writer gives one or the other) */
    if(!error && data[3]=='4' && (features&8192)){
        if(candidate.actor_count)error=1;else rows_decode(&candidate);
    }
    change_scratch.count=0;
    if(!error && data[3]=='4' && (features&8))changes_fields(&change_scratch);
    actor_scratch_bytes=0;
    if(!error && data[3]=='4' && (features&16)){
        uint32_t n=0;word(&n);
        /* MAP-EXPLORED-SAVE-BLOCK-66: up to the largest block the setting gives, so every 32 KB block before it too */
        if(error || n<1 || n>AW_SAVE_ACTOR_MAX_BYTES || at>end-(int)n)error=1;
        else{actor_src=reading+at;actor_scratch_bytes=(int)n;at+=(int)n;}
    }
    /* feature 128: checked here, read into the caller's history only when the whole save is good (below) */
    if(!error && data[3]=='4' && (features&128)){
        word(&dated_n);
        if(error || dated_n<8 || at>end-(int)dated_n || !aw_save_journal_decode ||
           !aw_save_journal_decode(reading+at,(int)dated_n,NULL))error=1;
        else{dated=reading+at;at+=(int)dated_n;}
    }
    /* feature 2048: the map markers, checked here, kept as the pending load only when the whole save is good */
    if(!error && data[3]=='4' && (features&2048)){
        word(&marks_n);
        if(error || marks_n<8 || at>end-(int)marks_n || !aw_save_markers_decode ||
           !aw_save_markers_decode(reading+at,(int)marks_n,0))error=1;
        else{marks=reading+at;at+=(int)marks_n;}
    }
    /* feature 4096: the explored map, framed here (its rows are read at the load's spawn, aw_save_explored_import) */
    if(!error && data[3]=='4' && (features&4096)){
        word(&explored_n);
        if(error || explored_n<6 || at>end-(int)explored_n || memcmp(reading+at,"AWFG",4))error=1;
        else{explored=reading+at;at+=(int)explored_n;}
    }
    /* feature 32 (CELL-CHANGES-59): the world change list, read into the caller's list only when the whole save is
     * good (it is the last section: nothing after it can still refuse); without a list it is checked, not kept */
    if(!error && data[3]=='4' && (features&32)){
        uint32_t n=0;const unsigned char *list;
        word(&n);
        if(error || n<8 || at>end-(int)n)error=1;
        else{
            list=reading+at;at+=(int)n;
            if(at!=size || !aw_save_ledger_decode || !aw_save_ledger_decode(list,(int)n,changes?changes->ledger:NULL))error=1;
        }
    }
    if(error || at!=size)return 0;
    /* the actor block and the explored map: with TAKE (a load) in buffers of their own sizes, taken now that the whole
     * save is good (MAP-EXPLORED-SAVE-BLOCK-66); else into the caller's buffer when it holds the block */
    if(changes && changes->take){
        AW_SaveChangesFree(changes);
        if(actor_scratch_bytes && !(changes->actors=taken(actor_src,(uint32_t)actor_scratch_bytes)))return 0;
        changes->actor_capacity=actor_scratch_bytes;actor_kept=1;
        if(explored && changes->explored){
            if(!(changes->explored_data=taken(explored,explored_n))){AW_SaveChangesFree(changes);return 0;}
            changes->explored_bytes=(int)explored_n;
        }
    }else if(changes && changes->actors && actor_scratch_bytes<=changes->actor_capacity){
        if(actor_scratch_bytes)memcpy(changes->actors,actor_src,(size_t)actor_scratch_bytes);
        actor_kept=1;
    }
    /* the dated journal history (feature 128; none: emptied, an older save's is taken over on load) */
    if(changes && changes->journal){
        if(dated){if(!aw_save_journal_decode(dated,(int)dated_n,changes->journal)){AW_SaveChangesFree(changes);return 0;}}
        else if(aw_save_journal_decode)aw_save_journal_decode(NULL,0,changes->journal);
    }
    if(changes && changes->markers && aw_save_markers_decode && !aw_save_markers_decode(marks,(int)marks_n,1)){
        AW_SaveChangesFree(changes);return 0;}
    *out=candidate;
    if(changes){changes->count=change_scratch.count;
        memcpy(changes->entry,change_scratch.entry,sizeof(aw_change_t)*change_scratch.count);
        changes->actor_bytes=actor_kept?actor_scratch_bytes:0;}
    memset(&candidate.state.items,0,sizeof(candidate.state.items));   /* OUT owns the table now */
    candidate.actors=NULL;candidate.actor_count=candidate.actor_capacity=0;   /* and the actor rows */
    return 1;
#undef candidate
}
