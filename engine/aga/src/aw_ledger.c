/* SPDX-License-Identifier: GPL-2.0-or-later
 * The world change list (CELL-CHANGES-59): see aw_ledger.h. The rules follow the original's saves and OpenMW 0.51's
 * cell store (only changed references are kept, each field only when it differs from the game data); the code is
 * our own.
 */
#include <string.h>
#include <stdlib.h>
#include "aw_ledger.h"
#include "aw_tryalloc.h"
#define LEDGER_STEP 256                 /* the row array grows by this many rows */
#define AW_LEDGER_ROW_BYTES 20          /* a row and its place in the place order */
#define AW_LEDGER_EXTRA_BYTES 96        /* an extra block and its allocation's own bytes */
typedef char ledger_row_fits[(sizeof(aw_ledger_row_t)+sizeof(int)<=AW_LEDGER_ROW_BYTES || sizeof(void *)>4)?1:-1];
typedef char ledger_extra_fits[(sizeof(aw_ledger_extra_t)+8<=AW_LEDGER_EXTRA_BYTES)?1:-1];
AW_RESIDENT_GROWS("world change list rows (CELL-CHANGES-59)",AW_LEDGER_ROWS,AW_LEDGER_ROW_BYTES);
AW_RESIDENT_GROWS("world change list positions and drops (CELL-CHANGES-59)",AW_LEDGER_EXTRAS,AW_LEDGER_EXTRA_BYTES);
typedef char ledger_stolen_fits[(sizeof(aw_ledger_stolen_t)<=AW_LEDGER_STOLEN_BYTES)?1:-1];
AW_RESIDENT_GROWS("stolen items by owner (CELL-CHANGES-59)",AW_LEDGER_STOLEN_MAX,AW_LEDGER_STOLEN_BYTES);
#define STOLEN_STEP 32                  /* the stolen pairs grow by this many */
typedef char ledger_content_fits[(sizeof(aw_ledger_content_t)<=AW_LEDGER_CONTENT_BYTES)?1:-1];
typedef char ledger_rank_fits[(sizeof(aw_ledger_rank_t)<=AW_LEDGER_RANK_BYTES)?1:-1];
AW_RESIDENT_GROWS("container deltas (CELL-CHANGES-59)",AW_LEDGER_CONTENTS_MAX,AW_LEDGER_CONTENT_BYTES);
AW_RESIDENT_GROWS("NPC faction ranks (CELL-CHANGES-59)",AW_LEDGER_RANKS_MAX,AW_LEDGER_RANK_BYTES);
#define CONTENT_STEP 32                 /* the container deltas and the ranks grow by this many */
aw_ledger_t aw_ledger;
int aw_ledger_on=1;
aw_ledger_events_t aw_ledger_events;
typedef char ledger_value_fits[(sizeof(aw_ledger_value_t)<=AW_LEDGER_VALUE_BYTES)?1:-1];
typedef char ledger_fact_fits[(sizeof(aw_ledger_fact_t)<=AW_LEDGER_FACT_BYTES)?1:-1];
AW_RESIDENT_GROWS("script globals, quest stages, known topics, dispositions (CELL-CHANGES-59)",AW_LEDGER_VALUES_ALL,AW_LEDGER_VALUE_BYTES);
AW_RESIDENT_GROWS("engine named facts past 32 (CELL-CHANGES-59)",AW_LEDGER_FACTS_MAX,AW_LEDGER_FACT_BYTES);
typedef char ledger_local_fits[(sizeof(aw_ledger_local_t)<=AW_LEDGER_LOCAL_BYTES)?1:-1];
typedef char ledger_script_fits[(sizeof(aw_ledger_script_t)<=AW_LEDGER_SCRIPT_BYTES)?1:-1];
AW_RESIDENT_GROWS("script locals (CELL-CHANGES-59)",AW_LEDGER_LOCALS_MAX,AW_LEDGER_LOCAL_BYTES);
AW_RESIDENT_GROWS("running global scripts (CELL-CHANGES-59)",AW_LEDGER_SCRIPTS_MAX,AW_LEDGER_SCRIPT_BYTES);
static int slice4(const aw_ledger_t *l){
    int t,n=l->fact_count;
    for(t=0;t<AW_LEDGER_TABLES;t++)n+=l->value_count[t];
    return n;
}
static int slice5(const aw_ledger_t *l){return l->local_count+l->script_count;}
typedef char ledger_actor_fits[(sizeof(aw_ledger_actor_t)<=AW_LEDGER_ACTOR_BYTES)?1:-1];
AW_RESIDENT_GROWS("changed actors: death, place, health, hostility (CELL-CHANGES-59 slice 6)",AW_LEDGER_ACTORS_MAX,AW_LEDGER_ACTOR_BYTES);
AW_RESIDENT_GROWS("changed actor records kept for the save (CELL-CHANGES-59 slice 6)",1,AW_LEDGER_RECORDS_MAX);
static unsigned actor_fields(const aw_ledger_actor_t *a){
    return (a->dead?AW_LEDGER_ACTOR_DEAD:0U)|(a->moved?AW_LEDGER_ACTOR_MOVED:0U)|(a->fight?AW_LEDGER_ACTOR_FIGHT:0U)|
           (a->follow?AW_LEDGER_ACTOR_FOLLOW:0U)|(a->pick?AW_LEDGER_ACTOR_PICK:0U);
}
static int actors_kept(const aw_ledger_t *l){
    int i,n=0;
    for(i=0;i<l->actor_count;i++)if(actor_fields(&l->actor[i]))n++;
    return n;
}
static int slice6(const aw_ledger_t *l){return actors_kept(l)+(l->records_bytes>0);}
/* slice 7: what only the seventh form can hold (the files and idents describe the rest; alone they make no save) */
typedef char ledger_stamp_fits[(sizeof(aw_ledger_stamp_t)<=AW_LEDGER_STAMP_BYTES)?1:-1];
typedef char ledger_ident_fits[(sizeof(aw_ledger_ident_t)<=AW_LEDGER_IDENT_BYTES)?1:-1];
AW_RESIDENT_GROWS("places' container refill times (CELL-CHANGES-59 slice 7)",AW_LEDGER_STAMPS_MAX,AW_LEDGER_STAMP_BYTES);
AW_RESIDENT_GROWS("record hashes of the references the list names (CELL-CHANGES-59 slice 7)",AW_LEDGER_IDENTS_MAX,AW_LEDGER_IDENT_BYTES);
static int died_kept(const aw_ledger_t *l){
    int i;
    for(i=0;i<l->actor_count;i++)if(l->actor[i].dead && l->actor[i].died>0)return 1;
    return 0;
}
static int slice7(const aw_ledger_t *l){return l->file_count+l->ident_count+l->stamp_count+died_kept(l);}
int AW_LedgerRows(const aw_ledger_t *l){return l->count+l->stolen_count+l->content_count+l->rank_count+slice4(l)+slice5(l)+slice6(l)+
                                               l->stamp_count;}

int AW_LedgerFind(const aw_ledger_t *l,uint32_t key){
    int lo=0,hi=l->count-1,mid;
    while(lo<=hi){
        mid=(lo+hi)/2;
        if(l->row[mid].key==key)return mid;
        if(l->row[mid].key<key)lo=mid+1;else hi=mid-1;
    }
    return -1;
}
int AW_LedgerFrom(const aw_ledger_t *l,uint32_t key){
    int lo=0,hi=l->count;
    while(lo<hi){int mid=(lo+hi)/2;if(l->row[mid].key<key)lo=mid+1;else hi=mid;}
    return lo;
}
aw_ledger_row_t *AW_LedgerPut(aw_ledger_t *l,uint32_t key){
    int at=AW_LedgerFrom(l,key);
    if(at<l->count && l->row[at].key==key)return &l->row[at];
    if(l->count>=AW_LEDGER_ROWS){l->refused++;return NULL;}
    if(l->count==l->capacity){
        int want=l->capacity+LEDGER_STEP;aw_ledger_row_t *grown;
        if(want>AW_LEDGER_ROWS)want=AW_LEDGER_ROWS;
        grown=(aw_ledger_row_t *)AW_TryRealloc(l->row,(unsigned long)want*sizeof(aw_ledger_row_t));
        if(!grown){l->refused++;return NULL;}
        l->row=grown;l->capacity=want;
    }
    memmove(&l->row[at+1],&l->row[at],(size_t)(l->count-at)*sizeof(aw_ledger_row_t));
    memset(&l->row[at],0,sizeof(aw_ledger_row_t));l->row[at].key=key;
    l->count++;l->placed=0;
    return &l->row[at];
}
aw_ledger_extra_t *AW_LedgerExtra(aw_ledger_t *l,aw_ledger_row_t *row){
    if(row->extra)return row->extra;
    if(l->extras>=AW_LEDGER_EXTRAS){l->refused++;return NULL;}
    row->extra=(aw_ledger_extra_t *)AW_TryMalloc(sizeof(aw_ledger_extra_t));
    if(!row->extra){l->refused++;return NULL;}
    memset(row->extra,0,sizeof(aw_ledger_extra_t));l->extras++;
    return row->extra;
}
void AW_LedgerSetPlace(aw_ledger_t *l,aw_ledger_row_t *row,int at,int32_t where){
    if(row->at!=at || row->where!=where){row->at=(uint8_t)at;row->where=where;l->placed=0;}
}
void AW_LedgerTidy(aw_ledger_t *l,uint32_t key){
    int i=AW_LedgerFind(l,key);
    if(i<0 || l->row[i].fields)return;
    if(l->row[i].extra){free(l->row[i].extra);l->extras--;}
    memmove(&l->row[i],&l->row[i+1],(size_t)(l->count-i-1)*sizeof(aw_ledger_row_t));
    l->count--;l->placed=0;
}
void AW_LedgerClear(aw_ledger_t *l){
    int i;
    for(i=0;i<l->count;i++)free(l->row[i].extra);
    free(l->row);free(l->place);free(l->stolen);free(l->content);free(l->rank);free(l->fact);free(l->local);free(l->script);
    free(l->actor);free(l->records);free(l->stamp);free(l->ident);
    for(i=0;i<AW_LEDGER_TABLES;i++)free(l->value[i]);
    memset(l,0,sizeof(*l));
}
void AW_LedgerMove(aw_ledger_t *to,aw_ledger_t *from){
    if(to==from)return;
    AW_LedgerClear(to);*to=*from;memset(from,0,sizeof(*from));
}
/* the place order: (at, where, key) */
static const aw_ledger_t *sorting;
static int place_order(const void *a,const void *b){
    const aw_ledger_row_t *x=&sorting->row[*(const int *)a],*y=&sorting->row[*(const int *)b];
    if(x->at!=y->at)return x->at<y->at?-1:1;
    if(x->where!=y->where)return x->where<y->where?-1:1;
    return x->key<y->key?-1:x->key>y->key;
}
static int make_places(aw_ledger_t *l){
    int i;
    if(l->placed)return 1;
    if(l->place_capacity<l->count){
        int *grown=(int *)AW_TryRealloc(l->place,(unsigned long)l->capacity*sizeof(int));
        if(!grown)return 0;
        l->place=grown;l->place_capacity=l->capacity;
    }
    for(i=0;i<l->count;i++)l->place[i]=i;
    sorting=l;qsort(l->place,(size_t)l->count,sizeof(int),place_order);sorting=NULL;
    l->placed=1;
    return 1;
}
int AW_LedgerPlace(aw_ledger_t *l,int at,int32_t where,int *first){
    int lo=0,hi,n=0;
    *first=0;
    if(!l->count || !make_places(l))return 0;
    hi=l->count;
    while(lo<hi){
        int mid=(lo+hi)/2;const aw_ledger_row_t *r=&l->row[l->place[mid]];
        if(r->at<at || (r->at==at && r->where<where))lo=mid+1;else hi=mid;
    }
    *first=lo;
    while(lo+n<l->count && l->row[l->place[lo+n]].at==at && l->row[l->place[lo+n]].where==where)n++;
    return n;
}
aw_ledger_row_t *AW_LedgerPlaceRow(aw_ledger_t *l,int position){
    return position>=0 && position<l->count && l->placed?&l->row[l->place[position]]:NULL;
}
unsigned long AW_LedgerResident(const aw_ledger_t *l){
    return (unsigned long)l->capacity*sizeof(aw_ledger_row_t)+(unsigned long)l->place_capacity*sizeof(int)+
        (unsigned long)l->extras*sizeof(aw_ledger_extra_t)+(unsigned long)l->stolen_capacity*sizeof(aw_ledger_stolen_t)+
        (unsigned long)l->content_capacity*sizeof(aw_ledger_content_t)+(unsigned long)l->rank_capacity*sizeof(aw_ledger_rank_t)+
        (unsigned long)(l->value_capacity[0]+l->value_capacity[1]+l->value_capacity[2]+l->value_capacity[3])*
        sizeof(aw_ledger_value_t)+(unsigned long)l->fact_capacity*sizeof(aw_ledger_fact_t)+
        (unsigned long)l->local_capacity*sizeof(aw_ledger_local_t)+(unsigned long)l->script_capacity*sizeof(aw_ledger_script_t)+
        (unsigned long)l->actor_capacity*sizeof(aw_ledger_actor_t)+(unsigned long)l->records_bytes+
        (unsigned long)l->stamp_capacity*sizeof(aw_ledger_stamp_t)+(unsigned long)l->ident_capacity*sizeof(aw_ledger_ident_t);
}

/* --- the stolen pairs (aw_ledger.h) --- */
/* ID folded to lower case into OUT; 0 when empty, longer than AW_LEDGER_STOLEN_ID or not printable */
static int fold_id(char *out,const char *in){
    int i;
    if(!in || !in[0])return 0;
    for(i=0;in[i];i++){
        unsigned char c=(unsigned char)in[i];
        if(i>=AW_LEDGER_STOLEN_ID || c<32 || c>126)return 0;
        out[i]=(char)(c>='A' && c<='Z'?c+32:c);
    }
    out[i]=0;
    return 1;
}
/* the gold pieces (OpenMW 0.51 isGold: the five gold records); taking gold is theft but never marks it */
static int is_gold(const char *id){
    return !strcmp(id,"gold_001") || !strcmp(id,"gold_005") || !strcmp(id,"gold_010") || !strcmp(id,"gold_025") ||
           !strcmp(id,"gold_100");
}
static int stolen_order(const char *item,const char *owner,int faction,const aw_ledger_stolen_t *s){
    int c=strcmp(item,s->item);
    if(c)return c;
    if((c=strcmp(owner,s->owner))!=0)return c;
    return faction-(int)s->faction;
}
/* the first pair not below (ITEM, OWNER, FACTION) */
static int stolen_from(const aw_ledger_t *l,const char *item,const char *owner,int faction){
    int lo=0,hi=l->stolen_count;
    while(lo<hi){int mid=(lo+hi)/2;if(stolen_order(item,owner,faction,&l->stolen[mid])>0)lo=mid+1;else hi=mid;}
    return lo;
}
int AW_LedgerStolenAdd(aw_ledger_t *l,const char *item,const char *owner,int faction,int count){
    char i[AW_LEDGER_STOLEN_ID+1],o[AW_LEDGER_STOLEN_ID+1];int at;aw_ledger_stolen_t *s;
    faction=faction?1:0;
    if(!count || !fold_id(i,item) || !fold_id(o,owner) || is_gold(i))return 0;
    at=stolen_from(l,i,o,faction);
    if(at<l->stolen_count && !stolen_order(i,o,faction,&l->stolen[at])){
        s=&l->stolen[at];
        if(count>0 && count>AW_LEDGER_STOLEN_COUNT-s->count)s->count=AW_LEDGER_STOLEN_COUNT;else s->count+=count;
        if(s->count>0)return s->count;
        memmove(s,s+1,(size_t)(l->stolen_count-at-1)*sizeof(*s));l->stolen_count--;   /* all of it given back */
        return 0;
    }
    if(count<0)return 0;
    if(l->stolen_count>=AW_LEDGER_STOLEN_MAX){l->refused++;return 0;}
    if(l->stolen_count==l->stolen_capacity){
        int want=l->stolen_capacity+STOLEN_STEP;aw_ledger_stolen_t *grown;
        if(want>AW_LEDGER_STOLEN_MAX)want=AW_LEDGER_STOLEN_MAX;
        grown=(aw_ledger_stolen_t *)AW_TryRealloc(l->stolen,(unsigned long)want*sizeof(aw_ledger_stolen_t));
        if(!grown){l->refused++;return 0;}
        l->stolen=grown;l->stolen_capacity=want;
    }
    s=&l->stolen[at];
    memmove(s+1,s,(size_t)(l->stolen_count-at)*sizeof(*s));
    memset(s,0,sizeof(*s));strcpy(s->item,i);strcpy(s->owner,o);s->faction=(uint8_t)faction;
    s->count=count>AW_LEDGER_STOLEN_COUNT?AW_LEDGER_STOLEN_COUNT:count;
    l->stolen_count++;
    return s->count;
}
int AW_LedgerStolenCount(const aw_ledger_t *l,const char *item,const char *owner,int faction){
    char i[AW_LEDGER_STOLEN_ID+1],o[AW_LEDGER_STOLEN_ID+1];int at,n=0;
    faction=faction?1:0;
    if(!fold_id(i,item))return 0;
    if(owner){
        if(!fold_id(o,owner))return 0;
        at=stolen_from(l,i,o,faction);
        return at<l->stolen_count && !stolen_order(i,o,faction,&l->stolen[at])?l->stolen[at].count:0;
    }
    for(at=stolen_from(l,i,"",0);at<l->stolen_count && !strcmp(l->stolen[at].item,i);at++)n+=l->stolen[at].count;
    return n;
}

/* --- slice 3: the container deltas and the NPC ranks (aw_ledger.h) --- */
static int content_key_ok(uint32_t key){
    return (key&AW_LEDGER_ID) && !(key&0x3F000000U) && !(key&AW_LEDGER_PLAYER);
}
static int content_order(uint32_t key,const char *item,const aw_ledger_content_t *c){
    if(key!=c->key)return key<c->key?-1:1;
    return strcmp(item,c->item);
}
static int content_from(const aw_ledger_t *l,uint32_t key,const char *item){
    int lo=0,hi=l->content_count;
    while(lo<hi){int mid=(lo+hi)/2;if(content_order(key,item,&l->content[mid])>0)lo=mid+1;else hi=mid;}
    return lo;
}
int AW_LedgerContentAdd(aw_ledger_t *l,uint32_t key,const char *item,int delta){
    char i[AW_LEDGER_STOLEN_ID+1];int at;aw_ledger_content_t *c;long sum;
    if(!delta || !content_key_ok(key) || !fold_id(i,item))return 0;
    at=content_from(l,key,i);
    if(at<l->content_count && !content_order(key,i,&l->content[at])){
        c=&l->content[at];sum=(long)c->count+delta;
        if(sum>AW_LEDGER_STOLEN_COUNT)sum=AW_LEDGER_STOLEN_COUNT;
        if(sum<-AW_LEDGER_STOLEN_COUNT)sum=-AW_LEDGER_STOLEN_COUNT;
        if(sum){c->count=(int32_t)sum;return c->count;}
        memmove(c,c+1,(size_t)(l->content_count-at-1)*sizeof(*c));l->content_count--;   /* back as in the data */
        return 0;
    }
    if(l->content_count>=AW_LEDGER_CONTENTS_MAX){l->refused++;return 0;}
    if(l->content_count==l->content_capacity){
        int want=l->content_capacity+CONTENT_STEP;aw_ledger_content_t *grown;
        if(want>AW_LEDGER_CONTENTS_MAX)want=AW_LEDGER_CONTENTS_MAX;
        grown=(aw_ledger_content_t *)AW_TryRealloc(l->content,(unsigned long)want*sizeof(aw_ledger_content_t));
        if(!grown){l->refused++;return 0;}
        l->content=grown;l->content_capacity=want;
    }
    c=&l->content[at];
    memmove(c+1,c,(size_t)(l->content_count-at)*sizeof(*c));
    memset(c,0,sizeof(*c));c->key=key;strcpy(c->item,i);
    c->count=delta>AW_LEDGER_STOLEN_COUNT?AW_LEDGER_STOLEN_COUNT:delta<-AW_LEDGER_STOLEN_COUNT?-AW_LEDGER_STOLEN_COUNT:delta;
    l->content_count++;
    return c->count;
}
int AW_LedgerContentDelta(const aw_ledger_t *l,uint32_t key,const char *item){
    char i[AW_LEDGER_STOLEN_ID+1];int at;
    if(!fold_id(i,item))return 0;
    at=content_from(l,key,i);
    return at<l->content_count && !content_order(key,i,&l->content[at])?l->content[at].count:0;
}
int AW_LedgerContentOf(const aw_ledger_t *l,uint32_t key,int *first){
    int at=content_from(l,key,""),n=0;
    *first=at;
    while(at+n<l->content_count && l->content[at+n].key==key)n++;
    return n;
}
static int rank_from(const aw_ledger_t *l,uint32_t key){
    int lo=0,hi=l->rank_count;
    while(lo<hi){int mid=(lo+hi)/2;if(l->rank[mid].key<key)lo=mid+1;else hi=mid;}
    return lo;
}
int AW_LedgerRank(const aw_ledger_t *l,uint32_t key){
    int at=rank_from(l,key);
    return at<l->rank_count && l->rank[at].key==key?l->rank[at].rank:-1;
}
int AW_LedgerRankSet(aw_ledger_t *l,uint32_t key,int rank){
    int at;
    if(!content_key_ok(key) || rank<0 || rank>AW_LEDGER_RANK_TOP)return 0;
    at=rank_from(l,key);
    if(at<l->rank_count && l->rank[at].key==key){l->rank[at].rank=(int16_t)rank;return 1;}
    if(l->rank_count>=AW_LEDGER_RANKS_MAX){l->refused++;return 0;}
    if(l->rank_count==l->rank_capacity){
        int want=l->rank_capacity+CONTENT_STEP;aw_ledger_rank_t *grown;
        if(want>AW_LEDGER_RANKS_MAX)want=AW_LEDGER_RANKS_MAX;
        grown=(aw_ledger_rank_t *)AW_TryRealloc(l->rank,(unsigned long)want*sizeof(aw_ledger_rank_t));
        if(!grown){l->refused++;return 0;}
        l->rank=grown;l->rank_capacity=want;
    }
    memmove(&l->rank[at+1],&l->rank[at],(size_t)(l->rank_count-at)*sizeof(aw_ledger_rank_t));
    l->rank[at].key=key;l->rank[at].rank=(int16_t)rank;l->rank_count++;
    return 1;
}

/* --- slice 4: the script and dialogue tables and the named facts (aw_ledger.h) --- */
uint32_t AW_LedgerNameHash(const char *id){
    uint32_t h=2166136261u;
    for(;id && *id;id++){
        unsigned char c=(unsigned char)*id;
        if(c>='A' && c<='Z')c=(unsigned char)(c+32);
        h=(h^c)*16777619u;
    }
    return h?h:1;
}
/* a key and a value TABLE can keep */
static int value_ok(int table,uint32_t key,int32_t value){
    if(table<0 || table>=AW_LEDGER_TABLES || !key)return 0;
    if(table==AW_LEDGER_QUESTS)return value!=0;
    if(table==AW_LEDGER_TOPICS)return value==1;
    if(table==AW_LEDGER_DISPOSITIONS)return content_key_ok(key) && value>=-32768 && value<=32767;
    return 1;
}
static int value_from(const aw_ledger_t *l,int table,uint32_t key){
    int lo=0,hi=l->value_count[table];const aw_ledger_value_t *v=l->value[table];
    while(lo<hi){int mid=(lo+hi)/2;if(v[mid].key<key)lo=mid+1;else hi=mid;}
    return lo;
}
int AW_LedgerValue(const aw_ledger_t *l,int table,uint32_t key,int32_t *out){
    int at;
    if(table<0 || table>=AW_LEDGER_TABLES)return 0;
    at=value_from(l,table,key);
    if(at>=l->value_count[table] || l->value[table][at].key!=key)return 0;
    if(out)*out=l->value[table][at].value;
    return 1;
}
void AW_LedgerValueDrop(aw_ledger_t *l,int table,uint32_t key){
    int at;aw_ledger_value_t *v;
    if(table<0 || table>=AW_LEDGER_TABLES)return;
    at=value_from(l,table,key);v=l->value[table];
    if(at>=l->value_count[table] || v[at].key!=key)return;
    memmove(&v[at],&v[at+1],(size_t)(l->value_count[table]-at-1)*sizeof(*v));l->value_count[table]--;
}
int AW_LedgerValueSet(aw_ledger_t *l,int table,uint32_t key,int32_t value){
    int at;aw_ledger_value_t *v;
    if(table==AW_LEDGER_QUESTS && key && !value){AW_LedgerValueDrop(l,table,key);return 1;}   /* back at the start */
    if(!value_ok(table,key,value))return 0;
    at=value_from(l,table,key);
    if(at<l->value_count[table] && l->value[table][at].key==key){l->value[table][at].value=value;return 1;}
    if(l->value_count[table]>=AW_LEDGER_VALUES_MAX){l->refused++;return 0;}
    if(l->value_count[table]==l->value_capacity[table]){
        int want=l->value_capacity[table]?l->value_capacity[table]*2:CONTENT_STEP;
        if(want>AW_LEDGER_VALUES_MAX)want=AW_LEDGER_VALUES_MAX;
        v=(aw_ledger_value_t *)AW_TryRealloc(l->value[table],(unsigned long)want*sizeof(aw_ledger_value_t));
        if(!v){l->refused++;return 0;}
        l->value[table]=v;l->value_capacity[table]=want;
    }
    v=l->value[table];
    memmove(&v[at+1],&v[at],(size_t)(l->value_count[table]-at)*sizeof(*v));
    v[at].key=key;v[at].value=value;l->value_count[table]++;
    return 1;
}
void AW_LedgerValueClear(aw_ledger_t *l,int table){
    if(table<0 || table>=AW_LEDGER_TABLES)return;
    free(l->value[table]);l->value[table]=NULL;l->value_count[table]=l->value_capacity[table]=0;
}
/* a fact's id folded into OUT (printable, 1 .. AW_LEDGER_FACT_ID characters) */
static int fact_id(char *out,const char *in){
    int i;
    if(!in || !in[0])return 0;
    for(i=0;in[i];i++){
        unsigned char c=(unsigned char)in[i];
        if(i>=AW_LEDGER_FACT_ID || c<32 || c>126)return 0;
        out[i]=(char)(c>='A' && c<='Z'?c+32:c);
    }
    out[i]=0;
    return 1;
}
static int fact_from(const aw_ledger_t *l,const char *id){
    int lo=0,hi=l->fact_count;
    while(lo<hi){int mid=(lo+hi)/2;if(strcmp(l->fact[mid].id,id)<0)lo=mid+1;else hi=mid;}
    return lo;
}
int AW_LedgerFact(const aw_ledger_t *l,const char *id,int32_t *out){
    char f[AW_LEDGER_FACT_ID+1];int at;
    if(!fact_id(f,id))return 0;
    at=fact_from(l,f);
    if(at>=l->fact_count || strcmp(l->fact[at].id,f))return 0;
    if(out)*out=l->fact[at].value;
    return 1;
}
int AW_LedgerFactSet(aw_ledger_t *l,const char *id,int32_t value){
    char f[AW_LEDGER_FACT_ID+1];int at;aw_ledger_fact_t *x;
    if(!fact_id(f,id))return 0;
    at=fact_from(l,f);
    if(at<l->fact_count && !strcmp(l->fact[at].id,f)){l->fact[at].value=value;return 1;}
    if(l->fact_count>=AW_LEDGER_FACTS_MAX){l->refused++;return 0;}
    if(l->fact_count==l->fact_capacity){
        int want=l->fact_capacity+CONTENT_STEP;
        if(want>AW_LEDGER_FACTS_MAX)want=AW_LEDGER_FACTS_MAX;
        x=(aw_ledger_fact_t *)AW_TryRealloc(l->fact,(unsigned long)want*sizeof(aw_ledger_fact_t));
        if(!x){l->refused++;return 0;}
        l->fact=x;l->fact_capacity=want;
    }
    x=&l->fact[at];
    memmove(x+1,x,(size_t)(l->fact_count-at)*sizeof(*x));
    memset(x,0,sizeof(*x));strcpy(x->id,f);x->value=value;l->fact_count++;
    return 1;
}

/* --- slice 5: the scripts' locals and the running global scripts (aw_ledger.h) --- */
static int local_ok(int global,uint32_t key,uint32_t script,int hint,int slot){
    if(!script || hint<0 || hint>0xFFFF || slot<0 || slot>255 || (global!=0 && global!=1))return 0;
    return global?key==script:content_key_ok(key);
}
static int local_order(int global,uint32_t key,int slot,const aw_ledger_local_t *x){
    if(global!=(int)x->global)return global<(int)x->global?-1:1;
    if(key!=x->key)return key<x->key?-1:1;
    return slot-(int)x->slot;
}
static int local_from(const aw_ledger_t *l,int global,uint32_t key,int slot){
    int lo=0,hi=l->local_count;
    while(lo<hi){int mid=(lo+hi)/2;if(local_order(global,key,slot,&l->local[mid])>0)lo=mid+1;else hi=mid;}
    return lo;
}
int AW_LedgerLocal(const aw_ledger_t *l,int global,uint32_t key,int slot,int32_t *out){
    int at=local_from(l,global,key,slot);
    if(at>=l->local_count || local_order(global,key,slot,&l->local[at]))return 0;
    if(out)*out=l->local[at].value;
    return 1;
}
int AW_LedgerLocalSet(aw_ledger_t *l,int global,uint32_t key,uint32_t script,int hint,int slot,int32_t value){
    int at;aw_ledger_local_t *x;
    if(!local_ok(global,key,script,hint,slot)){l->refused++;return 0;}
    at=local_from(l,global,key,slot);x=l->local;
    if(at<l->local_count && !local_order(global,key,slot,&x[at])){
        if(value){x[at].value=value;x[at].script=script;x[at].hint=(uint16_t)hint;return 1;}
        memmove(&x[at],&x[at+1],(size_t)(l->local_count-at-1)*sizeof(*x));l->local_count--;   /* back at its start */
        return 1;
    }
    if(!value)return 1;
    if(l->local_count>=AW_LEDGER_LOCALS_MAX){l->refused++;return 0;}
    if(l->local_count==l->local_capacity){
        int want=l->local_capacity?l->local_capacity*2:CONTENT_STEP;
        if(want>AW_LEDGER_LOCALS_MAX)want=AW_LEDGER_LOCALS_MAX;
        x=(aw_ledger_local_t *)AW_TryRealloc(l->local,(unsigned long)want*sizeof(aw_ledger_local_t));
        if(!x){l->refused++;return 0;}
        l->local=x;l->local_capacity=want;
    }
    x=&l->local[at];
    memmove(x+1,x,(size_t)(l->local_count-at)*sizeof(*x));
    memset(x,0,sizeof(*x));x->global=(uint8_t)global;x->key=key;x->script=script;x->hint=(uint16_t)hint;
    x->slot=(uint8_t)slot;x->value=value;l->local_count++;
    return 1;
}
static int script_from(const aw_ledger_t *l,uint32_t script){
    int lo=0,hi=l->script_count;
    while(lo<hi){int mid=(lo+hi)/2;if(l->script[mid].script<script)lo=mid+1;else hi=mid;}
    return lo;
}
int AW_LedgerScriptSet(aw_ledger_t *l,uint32_t script,int hint,int running){
    int at;aw_ledger_script_t *x;
    if(!script || hint<0 || hint>0xFFFF || (running!=0 && running!=1)){l->refused++;return 0;}
    at=script_from(l,script);
    if(at<l->script_count && l->script[at].script==script){
        l->script[at].hint=(uint16_t)hint;l->script[at].running=(uint8_t)running;return 1;}
    if(l->script_count>=AW_LEDGER_SCRIPTS_MAX){l->refused++;return 0;}
    if(l->script_count==l->script_capacity){
        int want=l->script_capacity+CONTENT_STEP;
        if(want>AW_LEDGER_SCRIPTS_MAX)want=AW_LEDGER_SCRIPTS_MAX;
        x=(aw_ledger_script_t *)AW_TryRealloc(l->script,(unsigned long)want*sizeof(aw_ledger_script_t));
        if(!x){l->refused++;return 0;}
        l->script=x;l->script_capacity=want;
    }
    x=&l->script[at];
    memmove(x+1,x,(size_t)(l->script_count-at)*sizeof(*x));
    memset(x,0,sizeof(*x));x->script=script;x->hint=(uint16_t)hint;x->running=(uint8_t)running;l->script_count++;
    return 1;
}
void AW_LedgerLocalsClear(aw_ledger_t *l){
    free(l->local);free(l->script);l->local=NULL;l->script=NULL;
    l->local_count=l->local_capacity=l->script_count=l->script_capacity=0;
}

/* --- slice 6: the actors (aw_ledger.h) --- */
#define ACTOR_KEY_OK(k) ((k)!=0 && !((k)&0xFF000000U))
aw_ledger_actor_t *AW_LedgerActor(aw_ledger_t *l,uint32_t key,int make){
    int lo=0,hi=l->actor_count;aw_ledger_actor_t *x;
    if(!ACTOR_KEY_OK(key)){if(make)l->refused++;return NULL;}
    while(lo<hi){int mid=(lo+hi)/2;if(l->actor[mid].key<key)lo=mid+1;else hi=mid;}
    if(lo<l->actor_count && l->actor[lo].key==key)return &l->actor[lo];
    if(!make)return NULL;
    if(l->actor_count>=AW_LEDGER_ACTORS_MAX){l->refused++;return NULL;}
    if(l->actor_count==l->actor_capacity){
        int want=l->actor_capacity?l->actor_capacity*2:64;
        if(want>AW_LEDGER_ACTORS_MAX)want=AW_LEDGER_ACTORS_MAX;
        x=(aw_ledger_actor_t *)AW_TryRealloc(l->actor,(unsigned long)want*sizeof(aw_ledger_actor_t));
        if(!x){l->refused++;return NULL;}
        l->actor=x;l->actor_capacity=want;
    }
    x=&l->actor[lo];
    memmove(x+1,x,(size_t)(l->actor_count-lo)*sizeof(*x));
    memset(x,0,sizeof(*x));x->key=key;l->actor_count++;
    return x;
}
int AW_LedgerRecordsSet(aw_ledger_t *l,const unsigned char *bytes,int count){
    unsigned char *copy=NULL;
    if(count<0 || count>AW_LEDGER_RECORDS_MAX || (count && (!bytes || count<8 || memcmp(bytes,"AWAR",4)))){l->refused++;return 0;}
    if(count && !(copy=(unsigned char *)AW_TryMalloc((unsigned long)count))){l->refused++;return 0;}
    if(count)memcpy(copy,bytes,(size_t)count);
    free(l->records);l->records=copy;l->records_bytes=count;
    return 1;
}
void AW_LedgerActorsClear(aw_ledger_t *l){
    free(l->actor);free(l->records);l->actor=NULL;l->records=NULL;
    l->actor_count=l->actor_capacity=l->records_bytes=0;
}

/* --- slice 7: respawn (aw_ledger.h) --- */
int AW_LedgerActorRespawns(const aw_ledger_actor_t *a,int respawns,float now,const aw_ledger_respawn_t *r){
    float delay,died;
    if(!a || !r || !a->dead || (!respawns && !a->pick))return 0;
    delay=r->respawn_delay<r->clear_delay?r->respawn_delay:r->clear_delay;   /* the body was not cleared away */
    died=a->died>0?a->died:a->hours;
    return died+delay<=now;
}
void AW_LedgerActorReset(aw_ledger_actor_t *a){
    uint32_t key=a->key;
    memset(a,0,sizeof(*a));a->key=key;
}
static int stamp_order(int at,int32_t where,const aw_ledger_stamp_t *s){
    if(at!=(int)s->at)return at<(int)s->at?-1:1;
    return where<s->where?-1:where>s->where;
}
static int stamp_from(const aw_ledger_t *l,int at,int32_t where){
    int lo=0,hi=l->stamp_count;
    while(lo<hi){int mid=(lo+hi)/2;if(stamp_order(at,where,&l->stamp[mid])>0)lo=mid+1;else hi=mid;}
    return lo;
}
float AW_LedgerPlaceStamp(const aw_ledger_t *l,int at,int32_t where){
    int i=stamp_from(l,at,where);
    return i<l->stamp_count && !stamp_order(at,where,&l->stamp[i])?l->stamp[i].hours:0;
}
static int stamp_ok(int at,int32_t where,float hours){
    if(!(hours>0 && hours<=10000000))return 0;
    if(at==AW_AT_CELL){
        int cx=(int16_t)((uint32_t)where>>16),cy=(int16_t)((uint32_t)where&0xffffU);
        return cx>=-1024 && cx<=1024 && cy>=-1024 && cy<=1024;
    }
    return at==AW_AT_ROOM && where>=1 && where<=0xFFFFFF;
}
static int stamp_set(aw_ledger_t *l,int at,int32_t where,float hours){
    int i;aw_ledger_stamp_t *s;
    if(!stamp_ok(at,where,hours)){l->refused++;return 0;}
    i=stamp_from(l,at,where);
    if(i<l->stamp_count && !stamp_order(at,where,&l->stamp[i])){l->stamp[i].hours=hours;return 1;}
    if(l->stamp_count>=AW_LEDGER_STAMPS_MAX){l->refused++;return 0;}
    if(l->stamp_count==l->stamp_capacity){
        int want=l->stamp_capacity?l->stamp_capacity*2:CONTENT_STEP;
        if(want>AW_LEDGER_STAMPS_MAX)want=AW_LEDGER_STAMPS_MAX;
        s=(aw_ledger_stamp_t *)AW_TryRealloc(l->stamp,(unsigned long)want*sizeof(aw_ledger_stamp_t));
        if(!s){l->refused++;return 0;}
        l->stamp=s;l->stamp_capacity=want;
    }
    s=&l->stamp[i];
    memmove(s+1,s,(size_t)(l->stamp_count-i)*sizeof(*s));
    memset(s,0,sizeof(*s));s->at=(uint8_t)at;s->where=where;s->hours=hours;l->stamp_count++;
    return 1;
}
int AW_LedgerRespawnPlace(aw_ledger_t *l,int at,int32_t where,float now,int months){
    if(months<1 || !(now>0) || (at!=AW_AT_CELL && at!=AW_AT_ROOM))return 0;
    if(now-AW_LedgerPlaceStamp(l,at,where)<=24.0f*30.0f*(float)months)return 0;
    stamp_set(l,at,where,now);      /* refused (memory): the refill still happens, the next one comes as for a new place */
    return 1;
}
int AW_LedgerContentDrop(aw_ledger_t *l,uint32_t key){
    int first,n=AW_LedgerContentOf(l,key,&first);
    if(n<=0)return 0;
    memmove(&l->content[first],&l->content[first+n],(size_t)(l->content_count-first-n)*sizeof(aw_ledger_content_t));
    l->content_count-=n;
    return n;
}

/* --- slice 7: identity (aw_ledger.h) --- */
#define IDENT_KEY_OK(k) (((k)&AW_LEDGER_ID) && !((k)&0xFF000000U))
static int ident_from(const aw_ledger_t *l,uint32_t key){
    int lo=0,hi=l->ident_count;
    while(lo<hi){int mid=(lo+hi)/2;if(l->ident[mid].key<key)lo=mid+1;else hi=mid;}
    return lo;
}
int AW_LedgerIdent(const aw_ledger_t *l,uint32_t key,uint32_t *record){
    int i=ident_from(l,key);
    if(i>=l->ident_count || l->ident[i].key!=key)return 0;
    if(record)*record=l->ident[i].record;
    return 1;
}
int AW_LedgerIdentSet(aw_ledger_t *l,uint32_t key,uint32_t record){
    int i;aw_ledger_ident_t *x;
    if(!IDENT_KEY_OK(key) || !record){l->refused++;return 0;}
    i=ident_from(l,key);
    if(i<l->ident_count && l->ident[i].key==key){l->ident[i].record=record;return 1;}
    if(l->ident_count>=AW_LEDGER_IDENTS_MAX){l->refused++;return 0;}
    if(l->ident_count==l->ident_capacity){
        int want=l->ident_capacity?l->ident_capacity*2:64;
        if(want>AW_LEDGER_IDENTS_MAX)want=AW_LEDGER_IDENTS_MAX;
        x=(aw_ledger_ident_t *)AW_TryRealloc(l->ident,(unsigned long)want*sizeof(aw_ledger_ident_t));
        if(!x){l->refused++;return 0;}
        l->ident=x;l->ident_capacity=want;
    }
    x=&l->ident[i];
    memmove(x+1,x,(size_t)(l->ident_count-i)*sizeof(*x));
    x->key=key;x->record=record;l->ident_count++;
    return 1;
}
static int key_order(const void *a,const void *b){
    uint32_t x=*(const uint32_t *)a,y=*(const uint32_t *)b;
    return x<y?-1:x>y;
}
/* every reference key the list names (placed references only: no drop, no builder-made key), sorted, once each; the
 * count, -1 no memory. *OUT is the caller's to free. */
static int named_keys(const aw_ledger_t *l,uint32_t **out){
    int i,t,n=0,m=0;uint32_t *k;
    n=l->count+l->content_count+l->rank_count+l->value_count[AW_LEDGER_DISPOSITIONS]+l->local_count+l->actor_count;
    *out=NULL;
    if(!n)return 0;
    if(!(k=(uint32_t *)AW_TryMalloc((unsigned long)n*sizeof(uint32_t))))return -1;
    for(i=0;i<l->count;i++)if(IDENT_KEY_OK(l->row[i].key))k[m++]=l->row[i].key;
    for(i=0;i<l->content_count;i++)k[m++]=l->content[i].key;
    for(i=0;i<l->rank_count;i++)k[m++]=l->rank[i].key;
    t=AW_LEDGER_DISPOSITIONS;
    for(i=0;i<l->value_count[t];i++)k[m++]=l->value[t][i].key;
    for(i=0;i<l->local_count;i++)if(!l->local[i].global)k[m++]=l->local[i].key;
    for(i=0;i<l->actor_count;i++)if(actor_fields(&l->actor[i]))k[m++]=l->actor[i].key;
    for(i=n=0;i<m;i++)if(IDENT_KEY_OK(k[i]))k[n++]=k[i];
    qsort(k,(size_t)n,sizeof(uint32_t),key_order);
    for(i=m=0;i<n;i++)if(!m || k[i]!=k[m-1])k[m++]=k[i];
    *out=k;
    return m;
}
int AW_LedgerIdentRefresh(aw_ledger_t *l,aw_ledger_lookup_t lookup,void *context){
    uint32_t *keys,record;int n=named_keys(l,&keys),i,m=0;aw_ledger_ident_t *made;
    if(n<0)return 0;
    if(!n){free(l->ident);l->ident=NULL;l->ident_count=l->ident_capacity=0;return 1;}
    if(!(made=(aw_ledger_ident_t *)AW_TryMalloc((unsigned long)n*sizeof(aw_ledger_ident_t)))){free(keys);return 0;}
    for(i=0;i<n;i++){
        if(!AW_LedgerIdent(l,keys[i],&record) && !(lookup && lookup(context,keys[i],&record) && record))continue;
        made[m].key=keys[i];made[m].record=record;m++;
    }
    free(keys);free(l->ident);
    l->ident=made;l->ident_count=m;l->ident_capacity=n;
    return 1;
}
static int file_name_ok(const char *s){
    int i;
    for(i=0;s[i];i++)if((unsigned char)s[i]<32 || (unsigned char)s[i]>126 || i>=AW_LEDGER_FILE_NAME)return 0;
    return i>0;
}
void AW_LedgerFilesSet(aw_ledger_t *l,const aw_ledger_file_t *files,int count){
    int i,n=0;
    memset(l->file,0,sizeof(l->file));
    for(i=0;files && i<count && n<AW_LEDGER_FILES_MAX;i++){
        if(files[i].index>31 || !file_name_ok(files[i].name) || (n && files[i].index<=l->file[n-1].index))continue;
        l->file[n++]=files[i];
    }
    l->file_count=n;
}

/* --- slice 7: migration (aw_ledger.h) --- */
static int same_name(const char *a,const char *b){
    for(;*a && *b;a++,b++){
        int x=(unsigned char)*a,y=(unsigned char)*b;
        if(x>='A' && x<='Z')x+=32;
        if(y>='A' && y<='Z')y+=32;
        if(x!=y)return 0;
    }
    return *a==*b;
}
typedef struct {
    const aw_ledger_t *saved;     /* the save's idents and files, as loaded */
    const aw_ledger_file_t *now;int now_count;
    aw_ledger_lookup_t lookup;void *context;
    uint32_t missing;             /* bit per saved file index this game lacks */
} migrate_t;
/* KEY of the save still names the same thing in this game */
static int still_there(const migrate_t *m,uint32_t key){
    uint32_t index=(key&AW_LEDGER_ID)>>20,record=0,saved;
    if(!IDENT_KEY_OK(key) || index>31 || (m->missing&(1U<<index)))return 0;
    if(!m->lookup || !m->lookup(m->context,key,&record))return 0;
    return !AW_LedgerIdent(m->saved,key,&saved) || saved==record;
}
unsigned long AW_LedgerMigrate(aw_ledger_t *l,const aw_ledger_file_t *now,int now_count,aw_ledger_lookup_t lookup,
                               void *context,int (*item_ok)(void *context,const char *id),aw_ledger_dropped_t *out){
    migrate_t m;aw_ledger_dropped_t d;int i,j,k,t;unsigned long all;aw_ledger_t old;
    memset(&d,0,sizeof(d));memset(&m,0,sizeof(m));
    old=*l;                        /* the save's idents and files, read while L changes (only rows move below) */
    m.saved=&old;m.now=now;m.now_count=now_count;m.lookup=lookup;m.context=context;
    /* the save's content files by name: one this game lacks drops every change of it; a save without a list was made
     * with the files of the fixed indices (tools/ref_identity.py): the same name at the same index */
    for(i=0;i<l->file_count;i++){
        for(j=0;j<now_count && !same_name(now[j].name,l->file[i].name);j++);
        if(j==now_count || now[j].index!=l->file[i].index){m.missing|=1U<<l->file[i].index;d.files++;}
    }
    for(i=k=0;i<l->count;i++){
        aw_ledger_row_t *r=&l->row[i];int keep;
        if(r->key&AW_LEDGER_BUILDER)keep=1;
        else if(r->key&AW_LEDGER_PLAYER)keep=!item_ok || !r->extra || item_ok(context,r->extra->item);
        else keep=still_there(&m,r->key);
        if(!keep){
            if(r->key&AW_LEDGER_PLAYER)d.drops++;else d.objects++;
            if(r->extra){free(r->extra);l->extras--;}
            continue;
        }
        l->row[k++]=*r;
    }
    if(k!=l->count){l->count=k;l->placed=0;}
    for(i=k=0;i<l->content_count;i++){
        if(!still_there(&m,l->content[i].key) || (item_ok && !item_ok(context,l->content[i].item))){d.containers++;continue;}
        l->content[k++]=l->content[i];
    }
    l->content_count=k;
    for(i=k=0;i<l->stolen_count;i++){
        if(item_ok && !item_ok(context,l->stolen[i].item)){d.stolen++;continue;}
        l->stolen[k++]=l->stolen[i];
    }
    l->stolen_count=k;
    for(i=k=0;i<l->rank_count;i++){
        if(!still_there(&m,l->rank[i].key)){d.ranks++;continue;}
        l->rank[k++]=l->rank[i];
    }
    l->rank_count=k;
    t=AW_LEDGER_DISPOSITIONS;
    for(i=k=0;i<l->value_count[t];i++){
        if(!still_there(&m,l->value[t][i].key)){d.dispositions++;continue;}
        l->value[t][k++]=l->value[t][i];
    }
    l->value_count[t]=k;
    for(i=k=0;i<l->local_count;i++){
        if(!l->local[i].global && !still_there(&m,l->local[i].key)){d.locals++;continue;}
        l->local[k++]=l->local[i];
    }
    l->local_count=k;
    for(i=k=0;i<l->actor_count;i++){
        aw_ledger_actor_t *a=&l->actor[i];
        if(!actor_fields(a))continue;
        if(!still_there(&m,a->key)){d.actors++;continue;}
        if(a->pick){a->pick=0;d.picks++;}   /* a base row of the save's actor table: rolled again here */
        if(actor_fields(a))l->actor[k++]=*a;
    }
    l->actor_count=k;
    /* the idents of what stays are this game's; the files are this game's */
    free(l->ident);l->ident=NULL;l->ident_count=l->ident_capacity=0;
    AW_LedgerIdentRefresh(l,lookup,context);
    AW_LedgerFilesSet(l,now,now_count);
    all=d.objects+d.containers+d.ranks+d.dispositions+d.locals+d.actors+d.picks+d.drops+d.stolen;
    if(out)*out=d;
    return all;
}

/* --- the saved form --- */
static unsigned char *put_at;
static const unsigned char *get_at;
static int pos,limit,bad,form;        /* form: 1 "AWL1", 2 "AWL2" (OPEN and the stolen pairs) */
static int died_rows;                 /* slice 7: actor rows read with DIED */
static void raw(void *value,int n){
    if(n<0 || pos>limit-n){bad=1;pos=limit;return;}
    if(put_at)memcpy(put_at+pos,value,(size_t)n);
    else if(get_at)memcpy(value,get_at+pos,(size_t)n);
    pos+=n;
}
static void u32(uint32_t *v){
    unsigned char b[4];
    b[0]=(unsigned char)*v;b[1]=(unsigned char)(*v>>8);b[2]=(unsigned char)(*v>>16);b[3]=(unsigned char)(*v>>24);
    raw(b,4);
    if(get_at && !bad)*v=(uint32_t)b[0]|((uint32_t)b[1]<<8)|((uint32_t)b[2]<<16)|((uint32_t)b[3]<<24);
}
static void f32(float *v,float low,float high){
    uint32_t n=0;
    if(!get_at)memcpy(&n,v,4);
    u32(&n);
    if(get_at)memcpy(v,&n,4);
    if(!(*v>=low && *v<=high))bad=1;
}
static int id_ok(const char *s){
    int i;
    if(!s[0])return 0;
    for(i=0;s[i];i++)if((unsigned char)s[i]<32 || (unsigned char)s[i]>126 || i>=63)return 0;
    return 1;
}
/* One row both ways; the checks are the same for writing and reading. */
static void row_fields(aw_ledger_row_t *r,aw_ledger_extra_t *x,uint32_t previous,int first){
    unsigned char b[4];uint32_t where;int moved;
    u32(&r->key);
    b[0]=r->fields;b[1]=r->at;b[2]=r->lock;b[3]=r->last_lock;raw(b,4);
    if(get_at){r->fields=b[0];r->at=b[1];r->lock=b[2];r->last_lock=b[3];}
    where=(uint32_t)r->where;u32(&where);r->where=(int32_t)where;
    if(bad)return;
    if(!(r->key&AW_LEDGER_ID) || (r->key&0x3F000000U) || (!first && r->key<=previous) ||
       ((r->key&AW_LEDGER_PLAYER) && (r->key&AW_LEDGER_BUILDER)) ||
       !r->fields || (r->fields&~(form>=2?AW_LEDGER_FIELDS:AW_LEDGER_FIELDS1)) ||
       ((r->fields&AW_LEDGER_OPEN) && (r->fields&AW_LEDGER_DROPPED)) ||
       (!(r->key&AW_LEDGER_PLAYER))!=(!(r->fields&AW_LEDGER_DROPPED)) ||
       ((r->fields&AW_LEDGER_CONDITION) && !(r->fields&AW_LEDGER_DROPPED)) ||
       ((r->fields&AW_LEDGER_LOCK)?(r->lock>100 || r->last_lock>100):(r->lock || r->last_lock)) ||
       r->at>AW_AT_SCENE){bad=1;return;}
    if(r->at==AW_AT_ANY){
        if(r->where)bad=1;
    }else if(r->at==AW_AT_CELL){
        int cx=(int16_t)((uint32_t)r->where>>16),cy=(int16_t)((uint32_t)r->where&0xffffU);
        if(cx<-1024 || cx>1024 || cy<-1024 || cy>1024)bad=1;
    }else if(r->at==AW_AT_ROOM){
        if(r->where<1 || r->where>0xFFFFFF)bad=1;
    }else if(r->where<0 || r->where>0xFFFF)bad=1;
    moved=(r->fields&(AW_LEDGER_MOVED|AW_LEDGER_DROPPED))!=0;
    if(!moved || bad)return;
    if(!x){bad=1;return;}
    f32(&x->position[0],-1000000,1000000);f32(&x->position[1],-1000000,1000000);f32(&x->position[2],-1000000,1000000);
    f32(&x->yaw,-720,720);
    if(r->fields&AW_LEDGER_DROPPED){
        uint32_t count=(uint32_t)x->count;unsigned char n=0;
        u32(&count);x->count=(int32_t)count;
        if(x->count<1){bad=1;return;}
        if(!get_at){if(!id_ok(x->item)){bad=1;return;}n=(unsigned char)strlen(x->item);}
        raw(&n,1);
        if(bad || n<1 || n>63){bad=1;return;}
        if(get_at)memset(x->item,0,sizeof(x->item));
        raw(x->item,n);
        if(get_at && !bad && !id_ok(x->item))bad=1;
    }
    if(r->fields&AW_LEDGER_CONDITION)f32(&x->condition,0,1);
}
/* a stolen pair's id both ways: u8 length and the folded id */
static void id_field(char *s){
    unsigned char n=0;char folded[AW_LEDGER_STOLEN_ID+1];
    if(!get_at){if(!fold_id(folded,s) || strcmp(folded,s)){bad=1;return;}n=(unsigned char)strlen(s);}
    raw(&n,1);
    if(bad || n<1 || n>AW_LEDGER_STOLEN_ID){bad=1;return;}
    if(get_at)memset(s,0,AW_LEDGER_STOLEN_ID+1);
    raw(s,n);
    if(get_at && !bad && (!fold_id(folded,s) || strcmp(folded,s)))bad=1;
}
/* one stolen pair both ways; PREVIOUS the pair before it (strictly ascending), NULL for the first */
static void pair_fields(aw_ledger_stolen_t *s,const aw_ledger_stolen_t *previous){
    uint32_t count=(uint32_t)s->count;
    id_field(s->item);id_field(s->owner);raw(&s->faction,1);u32(&count);s->count=(int32_t)count;
    if(bad)return;
    if(s->faction>1 || s->count<1 || s->count>AW_LEDGER_STOLEN_COUNT || is_gold(s->item) ||
       (previous && stolen_order(s->item,s->owner,s->faction,previous)<=0))bad=1;
}
/* slice 3: one container delta both ways (PREVIOUS as above), one rank both ways */
static void content_fields(aw_ledger_content_t *c,const aw_ledger_content_t *previous){
    uint32_t count=(uint32_t)c->count;
    u32(&c->key);id_field(c->item);u32(&count);c->count=(int32_t)count;
    if(bad)return;
    if(!content_key_ok(c->key) || !c->count || c->count>AW_LEDGER_STOLEN_COUNT || c->count<-AW_LEDGER_STOLEN_COUNT ||
       (previous && content_order(c->key,c->item,previous)<=0))bad=1;
}
static void rank_fields(aw_ledger_rank_t *r,const aw_ledger_rank_t *previous){
    unsigned char b=(unsigned char)r->rank;
    u32(&r->key);raw(&b,1);r->rank=(int16_t)b;
    if(bad)return;
    if(!content_key_ok(r->key) || (previous && r->key<=previous->key))bad=1;
}
/* slice 4: one table entry both ways (TOPICS: the key alone), one named fact both ways */
static void value_fields(int table,aw_ledger_value_t *v,const aw_ledger_value_t *previous){
    uint32_t value=(uint32_t)v->value;
    u32(&v->key);
    if(table!=AW_LEDGER_TOPICS){u32(&value);v->value=(int32_t)value;}else v->value=1;
    if(bad)return;
    if(!value_ok(table,v->key,v->value) || (previous && v->key<=previous->key))bad=1;
}
static void fact_fields(aw_ledger_fact_t *x,const aw_ledger_fact_t *previous){
    unsigned char n=0;char folded[AW_LEDGER_FACT_ID+1];uint32_t value=(uint32_t)x->value;
    if(!get_at){if(!fact_id(folded,x->id) || strcmp(folded,x->id)){bad=1;return;}n=(unsigned char)strlen(x->id);}
    raw(&n,1);
    if(bad || n<1 || n>AW_LEDGER_FACT_ID){bad=1;return;}
    if(get_at)memset(x->id,0,sizeof(x->id));
    raw(x->id,n);u32(&value);x->value=(int32_t)value;
    if(bad)return;
    if((get_at && (!fact_id(folded,x->id) || strcmp(folded,x->id))) || (previous && strcmp(x->id,previous->id)<=0))bad=1;
}
/* slice 5: a u16 both ways; one running global script both ways; one local both ways (PREVIOUS as above) */
static void u16(uint16_t *v){
    unsigned char b[2];
    b[0]=(unsigned char)*v;b[1]=(unsigned char)(*v>>8);raw(b,2);
    if(get_at && !bad)*v=(uint16_t)(b[0]|(b[1]<<8));
}
static void script_fields(aw_ledger_script_t *x,const aw_ledger_script_t *previous){
    u32(&x->script);u16(&x->hint);raw(&x->running,1);
    if(bad)return;
    if(!x->script || x->running>1 || (previous && x->script<=previous->script))bad=1;
}
static void local_fields(aw_ledger_local_t *x,const aw_ledger_local_t *previous){
    uint32_t value=(uint32_t)x->value;
    raw(&x->global,1);u32(&x->key);u32(&x->script);u16(&x->hint);raw(&x->slot,1);u32(&value);x->value=(int32_t)value;
    if(bad)return;
    if(x->global>1 || !local_ok(x->global,x->key,x->script,x->hint,x->slot) || !x->value ||
       (previous && local_order(x->global,x->key,x->slot,previous)<=0))bad=1;
}
/* slice 6: one actor row both ways (PREVIOUS the key before it, 0 for the first) */
static void actor_row_fields(aw_ledger_actor_t *a,uint32_t previous){
    unsigned char f=(unsigned char)(actor_fields(a)|(form>=7 && a->dead && a->died>0?AW_LEDGER_ACTOR_DIED:0U));
    uint32_t room=(uint32_t)a->room;
    u32(&a->key);raw(&f,1);
    if(bad)return;
    if(!ACTOR_KEY_OK(a->key) || a->key<=previous || !(f&AW_LEDGER_ACTOR_FIELDS) ||
       (f&~(form>=7?(AW_LEDGER_ACTOR_FIELDS|AW_LEDGER_ACTOR_DIED):AW_LEDGER_ACTOR_FIELDS)) ||
       ((f&AW_LEDGER_ACTOR_DIED) && !(f&AW_LEDGER_ACTOR_DEAD))){bad=1;return;}
    if(get_at){a->dead=(f&AW_LEDGER_ACTOR_DEAD)?1:0;a->moved=(f&AW_LEDGER_ACTOR_MOVED)?1:0;
        a->fight=(f&AW_LEDGER_ACTOR_FIGHT)?1:0;a->follow=(f&AW_LEDGER_ACTOR_FOLLOW)?1:0;}
    if(f&AW_LEDGER_ACTOR_PICK){
        u16(&a->pick);
        if(!bad && (a->pick<1 || a->pick>0x8001U))bad=1;
    }else if(get_at)a->pick=0;
    if(bad)return;
    if(f&AW_LEDGER_ACTOR_MOVED){
        f32(&a->origin[0],-1000000,1000000);f32(&a->origin[1],-1000000,1000000);f32(&a->origin[2],-1000000,1000000);
        f32(&a->angles[1],-720,720);f32(&a->health,-10000,100000);f32(&a->hours,0,10000000);
        u32(&room);a->room=(int32_t)room;
        if(!bad && (a->room<0 || a->room>0xFFFFFF))bad=1;
    }
    if(f&AW_LEDGER_ACTOR_DIED){
        f32(&a->died,0,10000000);
        if(!bad && !(a->died>0))bad=1;
    }else if(get_at)a->died=0;
}
/* slice 7: one content file, one ident, one place's refill time, each both ways (PREVIOUS as above) */
static void file_fields(aw_ledger_file_t *x,const aw_ledger_file_t *previous){
    unsigned char n=0;uint32_t refs=x->references;
    raw(&x->index,1);
    if(!get_at){if(!file_name_ok(x->name)){bad=1;return;}n=(unsigned char)strlen(x->name);}
    raw(&n,1);
    if(bad || n<1 || n>AW_LEDGER_FILE_NAME){bad=1;return;}
    if(get_at)memset(x->name,0,sizeof(x->name));
    raw(x->name,n);u32(&refs);x->references=refs;raw(x->digest,8);
    if(bad)return;
    if(x->index>31 || !file_name_ok(x->name) || (previous && x->index<=previous->index))bad=1;
}
static void ident_fields(aw_ledger_ident_t *x,const aw_ledger_ident_t *previous){
    u32(&x->key);u32(&x->record);
    if(bad)return;
    if(!IDENT_KEY_OK(x->key) || !x->record || (previous && x->key<=previous->key))bad=1;
}
static void stamp_fields(aw_ledger_stamp_t *x,const aw_ledger_stamp_t *previous){
    uint32_t where=(uint32_t)x->where;
    raw(&x->at,1);u32(&where);x->where=(int32_t)where;f32(&x->hours,0,10000000);
    if(bad)return;
    if(!stamp_ok(x->at,x->where,x->hours) || (previous && stamp_order(x->at,x->where,previous)<=0))bad=1;
}
int AW_LedgerEncode(const aw_ledger_t *l,unsigned char *out,int capacity){
    uint32_t n=(uint32_t)l->count,previous=0,m=(uint32_t)l->stolen_count;int i;
    put_at=out;get_at=NULL;pos=0;limit=out?capacity:0x7FFFFFFF;bad=0;
    /* the first form while nothing of the second is there: such a save loads in an engine of slice 1 too */
    form=l->stolen_count?2:1;
    for(i=0;i<l->count && form==1;i++)if(l->row[i].fields&AW_LEDGER_OPEN)form=2;
    if(l->content_count || l->rank_count)form=3;       /* slice 3: only then, so slice 1 and 2 engines read the rest */
    if(slice4(l))form=4;                               /* slice 4: the same rule */
    if(slice5(l))form=5;                               /* slice 5: the same rule */
    if(slice6(l))form=6;                               /* slice 6: the same rule */
    if(slice7(l))form=7;                               /* slice 7: the same rule */
    raw((void *)(form==7?"AWL7":form==6?"AWL6":form==5?"AWL5":form==4?"AWL4":form==3?"AWL3":form==2?"AWL2":"AWL1"),4);u32(&n);
    for(i=0;i<l->count && !bad;i++){
        aw_ledger_row_t r=l->row[i];aw_ledger_extra_t x;
        if(r.extra)x=*r.extra;else memset(&x,0,sizeof(x));
        row_fields(&r,r.extra?&x:NULL,previous,i==0);previous=r.key;
    }
    if(form>=2 && !bad){
        u32(&m);
        for(i=0;i<l->stolen_count && !bad;i++){
            aw_ledger_stolen_t s=l->stolen[i];
            pair_fields(&s,i?&l->stolen[i-1]:NULL);
        }
    }
    if(form>=3 && !bad){
        uint32_t c=(uint32_t)l->content_count,k=(uint32_t)l->rank_count;
        u32(&c);
        for(i=0;i<l->content_count && !bad;i++){
            aw_ledger_content_t x=l->content[i];
            content_fields(&x,i?&l->content[i-1]:NULL);
        }
        u32(&k);
        for(i=0;i<l->rank_count && !bad;i++){
            aw_ledger_rank_t x=l->rank[i];
            if(x.rank<0 || x.rank>AW_LEDGER_RANK_TOP){bad=1;break;}
            rank_fields(&x,i?&l->rank[i-1]:NULL);
        }
    }
    if(form>=4 && !bad){
        int t;uint32_t k;
        for(t=0;t<AW_LEDGER_TABLES && !bad;t++){
            k=(uint32_t)l->value_count[t];u32(&k);
            for(i=0;i<l->value_count[t] && !bad;i++){
                aw_ledger_value_t x=l->value[t][i];
                value_fields(t,&x,i?&l->value[t][i-1]:NULL);
            }
        }
        k=(uint32_t)l->fact_count;
        if(!bad)u32(&k);
        for(i=0;i<l->fact_count && !bad;i++){
            aw_ledger_fact_t x=l->fact[i];
            fact_fields(&x,i?&l->fact[i-1]:NULL);
        }
    }
    if(form>=5 && !bad){
        uint32_t k=(uint32_t)l->script_count;
        u32(&k);
        for(i=0;i<l->script_count && !bad;i++){
            aw_ledger_script_t x=l->script[i];
            script_fields(&x,i?&l->script[i-1]:NULL);
        }
        k=(uint32_t)l->local_count;
        if(!bad)u32(&k);
        for(i=0;i<l->local_count && !bad;i++){
            aw_ledger_local_t x=l->local[i];
            local_fields(&x,i?&l->local[i-1]:NULL);
        }
    }
    if(form>=6 && !bad){
        uint32_t k=(uint32_t)actors_kept(l),last=0,b=(uint32_t)l->records_bytes;
        u32(&k);
        for(i=0;i<l->actor_count && !bad;i++){
            aw_ledger_actor_t x=l->actor[i];
            if(!actor_fields(&x))continue;            /* nothing kept on it: not saved */
            actor_row_fields(&x,last);last=x.key;
        }
        if(!bad)u32(&b);
        if(!bad && b){
            if(b>AW_LEDGER_RECORDS_MAX || b<8 || memcmp(l->records,"AWAR",4))bad=1;
            else raw(l->records,(int)b);
        }
    }
    if(form==7 && !bad){
        unsigned char f=(unsigned char)l->file_count;uint32_t k;
        raw(&f,1);
        for(i=0;i<l->file_count && !bad;i++){
            aw_ledger_file_t x=l->file[i];
            file_fields(&x,i?&l->file[i-1]:NULL);
        }
        k=(uint32_t)l->ident_count;
        if(!bad)u32(&k);
        for(i=0;i<l->ident_count && !bad;i++){
            aw_ledger_ident_t x=l->ident[i];
            ident_fields(&x,i?&l->ident[i-1]:NULL);
        }
        k=(uint32_t)l->stamp_count;
        if(!bad)u32(&k);
        for(i=0;i<l->stamp_count && !bad;i++){
            aw_ledger_stamp_t x=l->stamp[i];
            stamp_fields(&x,i?&l->stamp[i-1]:NULL);
        }
    }
    put_at=NULL;
    return bad?0:pos;
}
int AW_LedgerDecode(const unsigned char *data,int size,aw_ledger_t *into){
    aw_ledger_t made;uint32_t n=0,previous=0,i;unsigned char magic[4];
    memset(&made,0,sizeof(made));
    put_at=NULL;get_at=data;pos=0;limit=size;bad=0;died_rows=0;
    raw(magic,4);u32(&n);
    form=bad?0:!memcmp(magic,"AWL1",4)?1:!memcmp(magic,"AWL2",4)?2:!memcmp(magic,"AWL3",4)?3:!memcmp(magic,"AWL4",4)?4:
         !memcmp(magic,"AWL5",4)?5:!memcmp(magic,"AWL6",4)?6:!memcmp(magic,"AWL7",4)?7:0;
    if(!form || (form==1 && n<1) || n>AW_LEDGER_ROWS || (unsigned long)n*12>(unsigned long)size){get_at=NULL;return 0;}
    for(i=0;i<n && !bad;i++){
        aw_ledger_row_t r;aw_ledger_extra_t x,*keep;
        memset(&r,0,sizeof(r));memset(&x,0,sizeof(x));
        row_fields(&r,&x,previous,i==0);     /* the fields byte decides whether a position follows */
        if(bad)break;
        previous=r.key;
        if(!into)continue;
        {aw_ledger_row_t *row=AW_LedgerPut(&made,r.key);
         if(!row){bad=1;break;}
         row->fields=r.fields;row->at=r.at;row->where=r.where;row->lock=r.lock;row->last_lock=r.last_lock;
         if(r.fields&(AW_LEDGER_MOVED|AW_LEDGER_DROPPED)){
             if(!(keep=AW_LedgerExtra(&made,row))){bad=1;break;}
             *keep=x;
         }}
    }
    if(form>=2 && !bad){
        uint32_t m=0;aw_ledger_stolen_t last;
        memset(&last,0,sizeof(last));u32(&m);
        if(!bad && (m>AW_LEDGER_STOLEN_MAX || (unsigned long)m*8>(unsigned long)size || (form==2 && !n && !m)))bad=1;
        for(i=0;i<m && !bad;i++){
            aw_ledger_stolen_t s;
            memset(&s,0,sizeof(s));
            pair_fields(&s,i?&last:NULL);
            if(bad)break;
            last=s;
            if(into && AW_LedgerStolenAdd(&made,s.item,s.owner,s.faction,s.count)!=s.count)bad=1;
        }
    }
    if(form>=3 && !bad){
        uint32_t c=0,k=0;aw_ledger_content_t lc;aw_ledger_rank_t lr;
        memset(&lc,0,sizeof(lc));memset(&lr,0,sizeof(lr));
        u32(&c);
        if(!bad && (c>AW_LEDGER_CONTENTS_MAX || (unsigned long)c*10>(unsigned long)size))bad=1;
        for(i=0;i<c && !bad;i++){
            aw_ledger_content_t x;
            memset(&x,0,sizeof(x));
            content_fields(&x,i?&lc:NULL);
            if(bad)break;
            lc=x;
            if(into && AW_LedgerContentAdd(&made,x.key,x.item,x.count)!=x.count)bad=1;
        }
        if(!bad)u32(&k);
        if(!bad && (k>AW_LEDGER_RANKS_MAX || (unsigned long)k*5>(unsigned long)size || (form==3 && !c && !k)))bad=1;
        for(i=0;i<k && !bad;i++){
            aw_ledger_rank_t x;
            memset(&x,0,sizeof(x));
            rank_fields(&x,i?&lr:NULL);
            if(bad)break;
            lr=x;
            if(into && !AW_LedgerRankSet(&made,x.key,x.rank))bad=1;
        }
    }
    if(form>=4 && !bad){
        int t;uint32_t k=0,any=0;
        for(t=0;t<AW_LEDGER_TABLES && !bad;t++){
            aw_ledger_value_t last;
            memset(&last,0,sizeof(last));k=0;u32(&k);
            if(!bad && (k>AW_LEDGER_VALUES_MAX || (unsigned long)k*4>(unsigned long)size))bad=1;
            any+=k;
            for(i=0;i<k && !bad;i++){
                aw_ledger_value_t x;
                memset(&x,0,sizeof(x));
                value_fields(t,&x,i?&last:NULL);
                if(bad)break;
                last=x;
                if(into && !AW_LedgerValueSet(&made,t,x.key,x.value))bad=1;
            }
        }
        k=0;
        if(!bad)u32(&k);
        if(!bad && (k>AW_LEDGER_FACTS_MAX || (unsigned long)k*6>(unsigned long)size || (form==4 && !(any+k))))bad=1;
        {aw_ledger_fact_t last;
         memset(&last,0,sizeof(last));
         for(i=0;i<k && !bad;i++){
             aw_ledger_fact_t x;
             memset(&x,0,sizeof(x));
             fact_fields(&x,i?&last:NULL);
             if(bad)break;
             last=x;
             if(into && !AW_LedgerFactSet(&made,x.id,x.value))bad=1;
         }}
    }
    if(form>=5 && !bad){
        uint32_t k=0,m=0;aw_ledger_script_t ls;aw_ledger_local_t ll;
        memset(&ls,0,sizeof(ls));memset(&ll,0,sizeof(ll));
        u32(&k);
        if(!bad && (k>AW_LEDGER_SCRIPTS_MAX || (unsigned long)k*7>(unsigned long)size))bad=1;
        for(i=0;i<k && !bad;i++){
            aw_ledger_script_t x;
            memset(&x,0,sizeof(x));
            script_fields(&x,i?&ls:NULL);
            if(bad)break;
            ls=x;
            if(into && !AW_LedgerScriptSet(&made,x.script,x.hint,x.running))bad=1;
        }
        if(!bad)u32(&m);
        if(!bad && (m>AW_LEDGER_LOCALS_MAX || (unsigned long)m*16>(unsigned long)size || (form==5 && !(k+m))))bad=1;
        for(i=0;i<m && !bad;i++){
            aw_ledger_local_t x;
            memset(&x,0,sizeof(x));
            local_fields(&x,i?&ll:NULL);
            if(bad)break;
            ll=x;
            if(into && !AW_LedgerLocalSet(&made,x.global,x.key,x.script,x.hint,x.slot,x.value))bad=1;
        }
    }
    if(form>=6 && !bad){
        uint32_t k=0,b=0,last=0;
        u32(&k);
        if(!bad && (k>AW_LEDGER_ACTORS_MAX || (unsigned long)k*5>(unsigned long)size))bad=1;
        for(i=0;i<k && !bad;i++){
            aw_ledger_actor_t x,*row;
            memset(&x,0,sizeof(x));
            actor_row_fields(&x,last);
            if(bad)break;
            last=x.key;
            if(x.died>0)died_rows++;
            if(into){
                if(!(row=AW_LedgerActor(&made,x.key,1))){bad=1;break;}
                *row=x;
            }
        }
        if(!bad)u32(&b);
        if(!bad && (b>AW_LEDGER_RECORDS_MAX || (b && b<8) || b>(uint32_t)(size-pos) || (form==6 && !(k+b))))bad=1;
        if(!bad && b){
            if(memcmp(data+pos,"AWAR",4))bad=1;
            else{
                if(into && !AW_LedgerRecordsSet(&made,data+pos,(int)b))bad=1;
                pos+=(int)b;
            }
        }
    }
    if(form==7 && !bad){
        unsigned char f=0;uint32_t k=0,s=0;aw_ledger_file_t lf;aw_ledger_ident_t li;aw_ledger_stamp_t ls;int died=0;
        memset(&lf,0,sizeof(lf));memset(&li,0,sizeof(li));memset(&ls,0,sizeof(ls));
        raw(&f,1);
        if(!bad && f>AW_LEDGER_FILES_MAX)bad=1;
        for(i=0;i<f && !bad;i++){
            aw_ledger_file_t x;
            memset(&x,0,sizeof(x));
            file_fields(&x,i?&lf:NULL);
            if(bad)break;
            lf=x;
            if(into)made.file[made.file_count++]=x;
        }
        if(!bad)u32(&k);
        if(!bad && (k>AW_LEDGER_IDENTS_MAX || (unsigned long)k*8>(unsigned long)size))bad=1;
        for(i=0;i<k && !bad;i++){
            aw_ledger_ident_t x;
            memset(&x,0,sizeof(x));
            ident_fields(&x,i?&li:NULL);
            if(bad)break;
            li=x;
            if(into && !AW_LedgerIdentSet(&made,x.key,x.record))bad=1;
        }
        if(!bad)u32(&s);
        if(!bad && (s>AW_LEDGER_STAMPS_MAX || (unsigned long)s*9>(unsigned long)size))bad=1;
        for(i=0;i<s && !bad;i++){
            aw_ledger_stamp_t x;
            memset(&x,0,sizeof(x));
            stamp_fields(&x,i?&ls:NULL);
            if(bad)break;
            ls=x;
            if(into && !stamp_set(&made,x.at,x.where,x.hours))bad=1;
        }
        /* a seventh form holds something only it can (else it would have been written as an earlier one) */
        died=died_rows;
        if(!bad && !(f+k+s) && !died)bad=1;
    }
    get_at=NULL;
    if(bad || pos!=size){AW_LedgerClear(&made);return 0;}
    if(into)AW_LedgerMove(into,&made);
    return 1;
}

/* --- slice 7: the build's reference identity table (aw_ledger.h) --- */
AW_RESIDENT_GROWS("reference identity table's block index (CELL-CHANGES-59 slice 7)",AW_REFS_BLOCKS_MAX,4);
AW_RESIDENT_GROWS("reference identity table's one block of rows (CELL-CHANGES-59 slice 7)",1,AW_REFS_BLOCK_BYTES);
static uint32_t le32(const unsigned char *p){
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
void AW_RefsClose(aw_refs_t *r){
    free(r->first);free(r->block);
    memset(r,0,sizeof(*r));
}
int AW_RefsOpen(aw_refs_t *r,int (*read)(void *context,long at,void *out,long bytes),void *context,long at,long end){
    unsigned char b[48];int i,n;float f;
    memset(r,0,sizeof(*r));
    if(!read || at<0 || end-at<9 || read(context,at,b,5) || memcmp(b,"AWI1",4) || b[4]>AW_LEDGER_FILES_MAX)return 0;
    n=b[4];at+=5;
    for(i=0;i<n;i++){
        aw_ledger_file_t *x=&r->file[i];
        if(end-at<2 || read(context,at,b,2) || b[1]<1 || b[1]>AW_LEDGER_FILE_NAME)goto bad;
        x->index=b[0];
        if(end-at<2+b[1]+12 || read(context,at+2,x->name,b[1]))goto bad;
        x->name[b[1]]=0;at+=2+b[1];
        if(read(context,at,b,12))goto bad;
        x->references=le32(b);memcpy(x->digest,b+4,8);at+=12;
        if(!file_name_ok(x->name) || x->index>31 || (i && x->index<=r->file[i-1].index))goto bad;
    }
    r->file_count=n;
    if(end-at<24 || read(context,at,b,24))goto bad;
    r->respawn.months=(int)le32(b);
    {uint32_t u=le32(b+4);memcpy(&f,&u,4);r->respawn.respawn_delay=f;u=le32(b+8);memcpy(&f,&u,4);r->respawn.clear_delay=f;}
    r->rows=le32(b+12);r->step=le32(b+16);r->blocks=le32(b+20);at+=24;
    if(r->respawn.months<1 || r->respawn.months>1000 || !(r->respawn.respawn_delay>=0 && r->respawn.respawn_delay<100000) ||
       !(r->respawn.clear_delay>=0 && r->respawn.clear_delay<100000) || r->rows>AW_REFS_ROWS_MAX || r->step<1 ||
       r->step>AW_REFS_STEP_MAX || r->blocks!=(r->rows+r->step-1)/r->step || r->blocks>AW_REFS_BLOCKS_MAX ||
       end-at<(long)r->blocks*4+(long)r->rows*8)goto bad;
    if(r->blocks){
        if(!(r->first=(uint32_t *)AW_TryMalloc((unsigned long)r->blocks*4)) ||
           read(context,at,r->first,(long)r->blocks*4))goto bad;
        for(i=0;i<(int)r->blocks;i++){
            r->first[i]=le32((unsigned char *)&r->first[i]);
            if(i && r->first[i]<=r->first[i-1])goto bad;
        }
    }
    r->rows_at=at+(long)r->blocks*4;r->read=read;r->context=context;r->cached=-1;
    return 1;
bad:
    AW_RefsClose(r);
    return 0;
}
int AW_RefsFind(aw_refs_t *r,uint32_t key,uint32_t *record,uint32_t *flags){
    int lo=0,hi,mid;uint32_t n,k;long block;
    if(!r || !r->first || !key || (key&0xFF000000U))return 0;
    r->lookups++;
    hi=(int)r->blocks-1;
    if(key<r->first[0])return 0;
    while(lo<hi){mid=(lo+hi+1)/2;if(r->first[mid]<=key)lo=mid;else hi=mid-1;}
    block=lo;
    n=(uint32_t)block+1==r->blocks?r->rows-(uint32_t)block*r->step:r->step;
    if(r->cached!=block){
        if(!r->block && !(r->block=(unsigned char *)AW_TryMalloc((unsigned long)r->step*8)))return 0;
        r->reads++;
        if(r->read(r->context,r->rows_at+block*(long)r->step*8,r->block,(long)n*8)){r->cached=-1;return 0;}
        r->cached=block;
    }
    for(lo=0,hi=(int)n-1;lo<=hi;){
        mid=(lo+hi)/2;k=le32(r->block+mid*8)&0xFFFFFFU;
        if(k==key){
            if(record)*record=le32(r->block+mid*8+4);
            if(flags)*flags=le32(r->block+mid*8)&0xFF000000U;
            return 1;
        }
        if(k<key)lo=mid+1;else hi=mid-1;
    }
    return 0;
}
