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
int AW_LedgerRows(const aw_ledger_t *l){return l->count+l->stolen_count+l->content_count+l->rank_count;}

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
    free(l->row);free(l->place);free(l->stolen);free(l->content);free(l->rank);
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
        (unsigned long)l->content_capacity*sizeof(aw_ledger_content_t)+(unsigned long)l->rank_capacity*sizeof(aw_ledger_rank_t);
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

/* --- the saved form --- */
static unsigned char *put_at;
static const unsigned char *get_at;
static int pos,limit,bad,form;        /* form: 1 "AWL1", 2 "AWL2" (OPEN and the stolen pairs) */
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
int AW_LedgerEncode(const aw_ledger_t *l,unsigned char *out,int capacity){
    uint32_t n=(uint32_t)l->count,previous=0,m=(uint32_t)l->stolen_count;int i;
    put_at=out;get_at=NULL;pos=0;limit=out?capacity:0x7FFFFFFF;bad=0;
    /* the first form while nothing of the second is there: such a save loads in an engine of slice 1 too */
    form=l->stolen_count?2:1;
    for(i=0;i<l->count && form==1;i++)if(l->row[i].fields&AW_LEDGER_OPEN)form=2;
    if(l->content_count || l->rank_count)form=3;       /* slice 3: only then, so slice 1 and 2 engines read the rest */
    raw((void *)(form==3?"AWL3":form==2?"AWL2":"AWL1"),4);u32(&n);
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
    if(form==3 && !bad){
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
    put_at=NULL;
    return bad?0:pos;
}
int AW_LedgerDecode(const unsigned char *data,int size,aw_ledger_t *into){
    aw_ledger_t made;uint32_t n=0,previous=0,i;unsigned char magic[4];
    memset(&made,0,sizeof(made));
    put_at=NULL;get_at=data;pos=0;limit=size;bad=0;
    raw(magic,4);u32(&n);
    form=bad?0:!memcmp(magic,"AWL1",4)?1:!memcmp(magic,"AWL2",4)?2:!memcmp(magic,"AWL3",4)?3:0;
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
    if(form==3 && !bad){
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
        if(!bad && (k>AW_LEDGER_RANKS_MAX || (unsigned long)k*5>(unsigned long)size || (!c && !k)))bad=1;
        for(i=0;i<k && !bad;i++){
            aw_ledger_rank_t x;
            memset(&x,0,sizeof(x));
            rank_fields(&x,i?&lr:NULL);
            if(bad)break;
            lr=x;
            if(into && !AW_LedgerRankSet(&made,x.key,x.rank))bad=1;
        }
    }
    get_at=NULL;
    if(bad || pos!=size){AW_LedgerClear(&made);return 0;}
    if(into)AW_LedgerMove(into,&made);
    return 1;
}
