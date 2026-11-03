/* SPDX-License-Identifier: GPL-2.0-or-later
 * The dated journal history on the world change list (aw_jhist.h, JOURNAL-ORIGINAL-VIEW-59). */
#include <string.h>
#include <stdlib.h>
#include "aw_jhist.h"
#include "aw_ledger.h"
#include "aw_tryalloc.h"

AW_RESIDENT_GROWS("dated journal history (JOURNAL-ORIGINAL-VIEW-59)",AW_JHIST_MAX,AW_JHIST_ENTRY_BYTES);
aw_jhist_t aw_jhist;

static int valid(uint32_t quest,int32_t stage,int32_t days,int32_t ms){
    return quest && stage>0 && days>=0 && days<=365000 && ms>=0 && ms<86400000;
}
int AW_JHistAdd(aw_jhist_t *h,uint32_t quest,int32_t stage,int32_t days,int32_t milliseconds){
    int i;
    if(!h || !valid(quest,stage,days,milliseconds))return 0;
    for(i=0;i<h->count;i++)if(h->entry[i].quest==quest && h->entry[i].stage==stage)return 1;
    if(h->count>=AW_JHIST_MAX){h->refused++;return 0;}
    if(h->count==h->capacity){
        int want=h->capacity?h->capacity*2:64;aw_jhist_entry_t *grown;
        if(want>AW_JHIST_MAX)want=AW_JHIST_MAX;
        grown=(aw_jhist_entry_t *)AW_TryRealloc(h->entry,(unsigned long)want*sizeof(aw_jhist_entry_t));
        if(!grown){h->refused++;return 0;}
        h->entry=grown;h->capacity=want;
    }
    h->entry[h->count].quest=quest;h->entry[h->count].stage=stage;
    h->entry[h->count].days=days;h->entry[h->count].milliseconds=milliseconds;
    h->count++;
    return 2;
}
int AW_JHistHasQuest(const aw_jhist_t *h,uint32_t quest){
    int i;
    for(i=0;h && i<h->count;i++)if(h->entry[i].quest==quest)return 1;
    return 0;
}
void AW_JHistClear(aw_jhist_t *h){
    if(!h)return;
    free(h->entry);memset(h,0,sizeof(*h));
}
void AW_JHistMove(aw_jhist_t *to,aw_jhist_t *from){
    if(to==from)return;
    AW_JHistClear(to);*to=*from;memset(from,0,sizeof(*from));
}
int AW_JHistTakeOver(aw_jhist_t *h,const aw_state_t *s){
    int i,q,n=0;
    if(!h || !s)return 0;
    for(i=0;i<s->journal_count && i<AW_JOURNAL_ENTRIES;i++){
        q=s->journal[i].quest;
        if(q<0 || q>=s->count[AW_JOURNAL])continue;
        if(AW_JHistAdd(h,AW_LedgerNameHash(s->values[AW_JOURNAL][q].id),s->journal[i].stage,
                       s->journal[i].days,s->journal[i].milliseconds)==2)n++;
    }
    return n;
}
static void put(unsigned char *p,uint32_t v){p[0]=(unsigned char)v;p[1]=(unsigned char)(v>>8);p[2]=(unsigned char)(v>>16);p[3]=(unsigned char)(v>>24);}
static uint32_t get(const unsigned char *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
int AW_JHistEncode(const aw_jhist_t *h,unsigned char *out,int capacity){
    int i,need;
    if(!h || h->count<1 || h->count>AW_JHIST_MAX)return 0;
    need=8+h->count*AW_JHIST_ENTRY_BYTES;
    if(!out)return need;
    if(capacity<need)return 0;
    memcpy(out,"AWH1",4);put(out+4,(uint32_t)h->count);
    for(i=0;i<h->count;i++){
        unsigned char *p=out+8+i*AW_JHIST_ENTRY_BYTES;
        put(p,h->entry[i].quest);put(p+4,(uint32_t)h->entry[i].stage);
        put(p+8,(uint32_t)h->entry[i].days);put(p+12,(uint32_t)h->entry[i].milliseconds);
    }
    return need;
}
int AW_JHistDecode(const unsigned char *data,int size,aw_jhist_t *into){
    uint32_t n;int i,j;aw_jhist_t scratch;
    if(into)AW_JHistClear(into);
    if(!data || size<8 || memcmp(data,"AWH1",4))return 0;
    n=get(data+4);
    if(n<1 || n>AW_JHIST_MAX || (uint32_t)size!=8+n*AW_JHIST_ENTRY_BYTES)return 0;
    for(i=0;i<(int)n;i++){
        const unsigned char *p=data+8+i*AW_JHIST_ENTRY_BYTES;
        if(!valid(get(p),(int32_t)get(p+4),(int32_t)get(p+8),(int32_t)get(p+12)))return 0;
        for(j=0;j<i;j++){
            const unsigned char *o=data+8+j*AW_JHIST_ENTRY_BYTES;
            if(get(o)==get(p) && get(o+4)==get(p+4))return 0;   /* never twice */
        }
    }
    if(!into)return 1;
    memset(&scratch,0,sizeof(scratch));
    scratch.entry=(aw_jhist_entry_t *)AW_TryMalloc((unsigned long)n*sizeof(aw_jhist_entry_t));
    if(!scratch.entry)return 0;
    scratch.capacity=scratch.count=(int)n;
    for(i=0;i<(int)n;i++){
        const unsigned char *p=data+8+i*AW_JHIST_ENTRY_BYTES;
        scratch.entry[i].quest=get(p);scratch.entry[i].stage=(int32_t)get(p+4);
        scratch.entry[i].days=(int32_t)get(p+8);scratch.entry[i].milliseconds=(int32_t)get(p+12);
    }
    *into=scratch;
    return 1;
}
