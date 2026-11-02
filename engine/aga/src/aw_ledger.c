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
aw_ledger_t aw_ledger;
int aw_ledger_on=1;
int AW_LedgerRows(const aw_ledger_t *l){return l->count;}

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
    free(l->row);free(l->place);
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
        (unsigned long)l->extras*sizeof(aw_ledger_extra_t);
}

/* --- the saved form --- */
static unsigned char *put_at;
static const unsigned char *get_at;
static int pos,limit,bad;
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
       !r->fields || (r->fields&~AW_LEDGER_FIELDS) ||
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
int AW_LedgerEncode(const aw_ledger_t *l,unsigned char *out,int capacity){
    uint32_t n=(uint32_t)l->count,previous=0;int i;
    put_at=out;get_at=NULL;pos=0;limit=out?capacity:0x7FFFFFFF;bad=0;
    raw((void *)"AWL1",4);u32(&n);
    for(i=0;i<l->count && !bad;i++){
        aw_ledger_row_t r=l->row[i];aw_ledger_extra_t x;
        if(r.extra)x=*r.extra;else memset(&x,0,sizeof(x));
        row_fields(&r,r.extra?&x:NULL,previous,i==0);previous=r.key;
    }
    put_at=NULL;
    return bad?0:pos;
}
int AW_LedgerDecode(const unsigned char *data,int size,aw_ledger_t *into){
    aw_ledger_t made;uint32_t n=0,previous=0,i;unsigned char magic[4];
    memset(&made,0,sizeof(made));
    put_at=NULL;get_at=data;pos=0;limit=size;bad=0;
    raw(magic,4);u32(&n);
    if(bad || memcmp(magic,"AWL1",4) || n<1 || n>AW_LEDGER_ROWS || (unsigned long)n*12>(unsigned long)size){get_at=NULL;return 0;}
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
    get_at=NULL;
    if(bad || pos!=size){AW_LedgerClear(&made);return 0;}
    if(into)AW_LedgerMove(into,&made);
    return 1;
}
