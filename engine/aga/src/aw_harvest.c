/* SPDX-License-Identifier: GPL-2.0-or-later
 * Bounded direct pickup. AWH3 facts use dedicated AWS3 placement state; legacy AWH1/2 stays readable.
 * First stage intentionally has no respawn; ordinary scene loads never reset it.
 */
#include <string.h>
#include <math.h>
#include <stdlib.h>
#include "aw_harvest.h"
#include "aw_format.h"
#define DONE 0x40000000U
#define EMPTY 0x80000000U
#define SEED_MASK 0xfffffU
void AW_HarvestInitData(aw_harvest_t *h){memset(h,0,sizeof(*h));}
void AW_HarvestRelease(aw_harvest_t *h)
{
    free(h->storage);free(h->text);AW_HarvestInitData(h);
}
int AW_HarvestReserve(aw_harvest_t *h,int models,int nodes,int edges,int plants)
{
    unsigned bytes;unsigned char *p;
    AW_HarvestRelease(h);
    if(models<0 || models>AW_HARVEST_MODELS || nodes<0 || nodes>AW_HARVEST_NODES ||
       edges<0 || edges>AW_HARVEST_EDGES || plants<0 || plants>AW_HARVEST_PLANTS)return 0;
    bytes=models*sizeof(aw_harvest_model_t)+nodes*sizeof(aw_harvest_node_t)+
        edges*sizeof(aw_harvest_edge_t)+plants*sizeof(aw_harvest_plant_t);
    if(bytes){
        p=(unsigned char *)calloc(1,bytes);if(!p)return 0;
        h->storage=p;h->storage_bytes=bytes;
        h->model=(aw_harvest_model_t *)p;p+=models*sizeof(*h->model);
        h->node=(aw_harvest_node_t *)p;p+=nodes*sizeof(*h->node);
        h->edge=(aw_harvest_edge_t *)p;p+=edges*sizeof(*h->edge);
        h->plant=(aw_harvest_plant_t *)p;
    }
    h->models=h->model_capacity=models;h->nodes=h->node_capacity=nodes;
    h->edges=h->edge_capacity=edges;h->plants=h->plant_capacity=plants;return 1;
}
unsigned short AW_HarvestIntern(aw_harvest_t *h,const char *s)
{
    unsigned at,bytes;char *next,copy[64];
    if(!s)return AW_HARVEST_BAD_TEXT;
    if(!*s)return 0;
    if(strlen(s)>63)return AW_HARVEST_BAD_TEXT;
    /* The caller may pass a slice of an existing interned value. Preserve it
     * before realloc can move the dictionary. Every wire string is <=63 B. */
    strcpy(copy,s);s=copy;
    for(at=1;at<h->text_bytes;at+=(unsigned)strlen(h->text+at)+1)
        if(!strcmp(s,h->text+at))return (unsigned short)at;
    at=h->text_bytes?h->text_bytes:1;bytes=at+(unsigned)strlen(s)+1;
    if(bytes>AW_HARVEST_TEXT_BYTES)return AW_HARVEST_BAD_TEXT;
    next=(char *)realloc(h->text,bytes);if(!next)return AW_HARVEST_BAD_TEXT;
    h->text=next;h->text[0]=0;memcpy(next+at,s,bytes-at);h->text_bytes=bytes;
    return (unsigned short)at;
}
static int text_valid(const aw_harvest_t *h,unsigned short at)
{
    return !at || (h->text && at<h->text_bytes && !h->text[at-1] &&
        memchr(h->text+at,0,h->text_bytes-at)!=NULL);
}
const char *AW_HarvestText(const aw_harvest_t *h,unsigned short at)
{
    return at && text_valid(h,at)?h->text+at:"";
}
unsigned AW_HarvestStorageBytes(const aw_harvest_t *h){return h->storage_bytes+h->text_bytes;}
static int span(int first,int count,int total){return first>=0 && count>=0 && first<=total-count;}
static int identifier(const char *s){int n=0;for(;*s;s++,n++)if((unsigned char)*s<=32 || n>=63)return 0;return n>0;}
static int digest_read(const char *text,unsigned char *out)
{
    int i,c;if(strlen(text)!=64)return 0;memset(out,0,32);
    for(i=0;i<64;i++){
        c=text[i];if(c>='0' && c<='9')c-='0';else if(c>='a' && c<='f')c=c-'a'+10;else return 0;
        out[i/2]=(unsigned char)((out[i/2]<<4)|c);
    }
    return 1;
}
int AW_HarvestModelIndex(const aw_harvest_t *h,int plant)
{
    const char *s;int n;
    if(h->representation!=4 || plant<0 || plant>=h->plants)return -1;
    s=AW_HarvestText(h,h->plant[plant].model);
    if(s[0]!='@' || s[1]<'0' || s[1]>'7' || s[2])return -1;
    n=s[1]-'0';return n<h->models?n:-1;
}
static int walk(const aw_harvest_t *h,int node,unsigned char *active,int depth)
{
    int i;const aw_harvest_node_t *n=&h->node[node];
    if(depth>16 || active[node])return 0;
    if(n->kind!=1)return 1;
    active[node]=1;
    for(i=n->first;i<n->first+n->count;i++)if(!walk(h,h->edge[i].node,active,depth+1))return 0;
    active[node]=0;return 1;
}
int AW_HarvestValidate(const aw_harvest_t *h)
{
    int i,j,k,nonzero=0;unsigned char active[AW_HARVEST_NODES];
    if(h->slots<0 || h->slots>AW_HARVEST_SLOTS || h->text_bytes>AW_HARVEST_TEXT_BYTES)return 0;
    for(k=0;k<32;k++)nonzero|=h->catalogue[k];
    if((h->slots!=0)!=(nonzero!=0))return 0;
    if(h->representation!=0 && h->representation!=4)return 0;
    if(h->models<0 || h->models>AW_HARVEST_MODELS || (!h->representation && h->models) ||
       (h->representation==4 && (!h->slots || !h->models)))return 0;
    if(h->models>h->model_capacity || h->nodes>h->node_capacity || h->edges>h->edge_capacity ||
       h->plants>h->plant_capacity || ((h->models || h->nodes || h->edges || h->plants) && !h->storage))return 0;
    for(i=0;i<h->models;i++){
        const aw_harvest_model_t *m=&h->model[i];const char *path=AW_HarvestText(h,m->path);int n=(int)strlen(path);nonzero=0;
        if(!text_valid(h,m->path) || n<19 || n>63 || strncmp(path,"progs/harvest/",14) || strcmp(path+n-4,".mdl"))return 0;
        for(k=14;k<n-4;k++)if(!((path[k]>='a' && path[k]<='z') || (path[k]>='0' && path[k]<='9') || path[k]=='_'))return 0;
        for(k=0;k<32;k++)nonzero|=m->digest[k];
        if(!nonzero)return 0;
        for(k=0;k<3;k++)if(!isfinite(m->mins[k]) || !isfinite(m->maxs[k]) || m->mins[k]>m->maxs[k] ||
            fabs(m->mins[k])>32768 || fabs(m->maxs[k])>32768)return 0;
        for(j=0;j<i;j++)if(!strcmp(path,AW_HarvestText(h,h->model[j].path)))return 0;
    }
    if(h->nodes<0 || h->nodes>AW_HARVEST_NODES || h->edges<0 || h->edges>AW_HARVEST_EDGES ||
       h->plants<0 || h->plants>AW_HARVEST_PLANTS)return 0;
    for(i=0;i<h->edges;i++)if(h->edge[i].node<0 || h->edge[i].node>=h->nodes ||
       h->edge[i].level<0 || h->edge[i].level>32767 || h->edge[i].count<1 || h->edge[i].count>64)return 0;
    for(i=0;i<h->nodes;i++){
        const aw_harvest_node_t *n=&h->node[i];
        if(n->kind<0 || n->kind>2 || n->flags<0 || n->flags>3 || n->chance<0 || n->chance>100 ||
           !text_valid(h,n->id) || !text_valid(h,n->label) || !identifier(AW_HarvestText(h,n->id)) ||
           !span(n->first,n->count,h->edges) || (n->kind!=1 && n->count))return 0;
    }
    memset(active,0,sizeof(active));
    for(i=0;i<h->nodes;i++)if(!walk(h,i,active,0))return 0;
    for(i=0;i<h->plants;i++){
        const aw_harvest_plant_t *p=&h->plant[i];const char *key=AW_HarvestText(h,p->key);
        if(h->slots && (p->slot<1 || p->slot>h->slots))return 0;
        if(!text_valid(h,p->key) || !text_valid(h,p->label) || !text_valid(h,p->model) ||
           strlen(key)!=57 || strncmp(key,"aw:h:",5) || !span(p->first,p->count,h->edges) ||
           !AW_HarvestText(h,p->label)[0] || !p->reference || p->reference>16777216U || !(p->flags&1))return 0;
        if(h->representation==4){
            if(AW_HarvestModelIndex(h,i)<0 || !isfinite(p->scale) || p->scale<.01f || p->scale>100)return 0;
        }else if(AW_HarvestText(h,p->model)[0]!='*')return 0;
        for(k=5;k<57;k++)if(!((key[k]>='a' && key[k]<='z') || (key[k]>='2' && key[k]<='7')))return 0;
        for(k=0;k<3;k++)if(!isfinite(p->origin[k]) || !isfinite(p->angles[k]))return 0;
        for(j=0;j<i;j++)if((h->slots && p->slot==h->plant[j].slot) || !strcmp(key,AW_HarvestText(h,h->plant[j].key)) ||
            (p->reference==h->plant[j].reference && !strcmp(AW_HarvestText(h,p->model),AW_HarvestText(h,h->plant[j].model))))return 0;
    }
    return 1;
}
int AW_HarvestLoad(FILE *f,int bytes,aw_harvest_t *h)
{
    int i,k,c,nodes,edges,plants,models=0,slots=0,representation=0;
    long start=ftell(f);char magic[8],digest[65],token[64],label[64];unsigned char catalogue[32];
    AW_HarvestRelease(h);memset(catalogue,0,sizeof(catalogue));
    if(start<0 || bytes<0 || bytes>65536)goto bad;
    if(Q_fscanf(f,"%7s %d %d %d",magic,&nodes,&edges,&plants)!=4 || (strcmp(magic,"AWH1") && strcmp(magic,"AWH2") && strcmp(magic,"AWH3") && strcmp(magic,"AWH4")))goto bad;
    if(!strcmp(magic,"AWH3") || !strcmp(magic,"AWH4")){
        if(Q_fscanf(f," %d %64s",&slots,digest)!=2 || slots<1 || slots>AW_HARVEST_SLOTS || !digest_read(digest,catalogue))goto bad;
    }
    if(!strcmp(magic,"AWH4")){
        representation=4;
        if(Q_fscanf(f," %d",&models)!=1 || models<1 || models>AW_HARVEST_MODELS)goto bad;
    }
    if(!AW_HarvestReserve(h,models,nodes,edges,plants))goto bad;
    h->slots=slots;h->representation=representation;memcpy(h->catalogue,catalogue,32);
    if(representation==4){
        for(i=0;i<h->models;i++){
            aw_harvest_model_t *m=&h->model[i];
            if(Q_fscanf(f," %63s %64s",token,digest)!=2 || !digest_read(digest,m->digest))goto bad;
            m->path=AW_HarvestIntern(h,token);if(m->path==AW_HARVEST_BAD_TEXT)goto bad;
            for(k=0;k<3;k++)if(Q_fscanf(f," %f",&m->mins[k])!=1)goto bad;
            for(k=0;k<3;k++)if(Q_fscanf(f," %f",&m->maxs[k])!=1)goto bad;
        }
    }
    for(i=0;i<h->nodes;i++){
        aw_harvest_node_t *n=&h->node[i];
        if(Q_fscanf(f," %d %d %d %d %d %63s",&n->kind,&n->flags,&n->chance,&n->first,&n->count,token)!=6)goto bad;
        n->id=AW_HarvestIntern(h,token);if(n->id==AW_HARVEST_BAD_TEXT)goto bad;
        if(strcmp(magic,"AWH1")){
            if(fgetc(f)!='\t' || Q_fscanf(f,"%63[^\r\n]",label)!=1)goto bad;
            if(n->kind==0 && (!strcmp(label,"-") || !label[0]))goto bad;
            for(k=0;label[k];k++)if((unsigned char)label[k]<32 || (unsigned char)label[k]>126)goto bad;
            n->label=AW_HarvestIntern(h,label);if(n->label==AW_HARVEST_BAD_TEXT)goto bad;
        }
    }
    for(i=0;i<h->edges;i++)if(Q_fscanf(f," %d %d %d",&h->edge[i].node,&h->edge[i].level,&h->edge[i].count)!=3)goto bad;
    for(i=0;i<h->plants;i++){
        aw_harvest_plant_t *p=&h->plant[i];
        if(Q_fscanf(f," %63s",token)!=1)goto bad;
        p->key=AW_HarvestIntern(h,token);if(p->key==AW_HARVEST_BAD_TEXT)goto bad;
        if(h->slots && Q_fscanf(f," %d",&p->slot)!=1)goto bad;
        if(Q_fscanf(f," %u %15s %d %d %d",&p->reference,token,&p->flags,&p->first,&p->count)!=5)goto bad;
        p->model=AW_HarvestIntern(h,token);if(p->model==AW_HARVEST_BAD_TEXT)goto bad;
        for(k=0;k<3;k++)if(Q_fscanf(f," %f",&p->origin[k])!=1)goto bad;
        for(k=0;k<3;k++)if(Q_fscanf(f," %f",&p->angles[k])!=1)goto bad;
        if(h->representation==4 && Q_fscanf(f," %f",&p->scale)!=1)goto bad;
        if(Q_fscanf(f," %63[^\r\n]",label)!=1)goto bad;
        p->label=AW_HarvestIntern(h,label);if(p->label==AW_HARVEST_BAD_TEXT)goto bad;
    }
    if(ftell(f)-start>bytes)goto bad;
    while(ftell(f)-start<bytes){c=fgetc(f);if(c!=' ' && c!='\n' && c!='\r' && c!='\t')goto bad;}
    if(!AW_HarvestValidate(h))goto bad;
    return 1;
bad:AW_HarvestRelease(h);return 0;
}
static uint32_t roll(uint32_t *seed,uint32_t range)
{
    uint32_t r,threshold=(0U-range)%range;
    do{*seed^=*seed<<13;*seed^=*seed>>17;*seed^=*seed<<5;r=*seed;}while(r<threshold);
    return r%range;
}
static int resolve(const aw_harvest_t *h,int index,int level,uint32_t *seed,int depth)
{
    const aw_harvest_node_t *n=&h->node[index];int highest=0,count=0,i,selected;
    if(depth>16)return -2;
    if(n->kind==2)return -1;
    if(n->kind==0)return index;
    if(roll(seed,100)<(unsigned)n->chance)return -1;
    for(i=n->first;i<n->first+n->count;i++)if(h->edge[i].level<=level && h->edge[i].level>highest)highest=h->edge[i].level;
    for(i=n->first;i<n->first+n->count;i++)if(h->edge[i].level<=level && ((n->flags&2) || h->edge[i].level==highest))count++;
    if(!count)return -1;
    selected=(int)roll(seed,(unsigned)count);
    for(i=n->first;i<n->first+n->count;i++)if(h->edge[i].level<=level && ((n->flags&2) || h->edge[i].level==highest))
        if(!selected--)return resolve(h,h->edge[i].node,level,seed,depth+1);
    return -2;
}
/* AWH3 map copies share a catalogue and slot. Mixing incompatible index
 * spaces fails closed; changing a build's catalogue also changes save-content.
 * Legacy saves migrate only exact full placement keys, never FRMR guesses. */
static int compatible(const aw_harvest_t *h,const aw_state_t *s)
{
    if(!h->slots)return !s->harvest.slots;
    return !s->harvest.slots || (s->harvest.slots==(uint32_t)h->slots &&
        !memcmp(s->harvest.catalogue,h->catalogue,32));
}
static uint32_t fact_get(const aw_harvest_t *h,int plant,const aw_state_t *s)
{
    const aw_harvest_plant_t *p=&h->plant[plant];
    if(h->slots && s->harvest.slots && compatible(h,s) && s->harvest.facts[p->slot-1])return s->harvest.facts[p->slot-1];
    return (uint32_t)AW_StateGet(s,AW_GLOBAL,AW_HarvestText(h,p->key));
}
static int fact_set(const aw_harvest_t *h,int plant,aw_state_t *s,uint32_t fact)
{
    if(!h->slots)return AW_StateSet(s,AW_GLOBAL,AW_HarvestText(h,h->plant[plant].key),(int32_t)fact);
    if(!compatible(h,s))return 0;
    if(!s->harvest.slots){s->harvest.slots=h->slots;memcpy(s->harvest.catalogue,h->catalogue,32);}
    s->harvest.facts[h->plant[plant].slot-1]=fact;return 1;
}
static int migrate(const aw_harvest_t *h,int plant,aw_state_t *s)
{
    int i;uint32_t fact,level;const char *key=AW_HarvestText(h,h->plant[plant].key);
    if(!h->slots)return 1;
    for(i=0;i<s->count[AW_GLOBAL];i++)if(!strcmp(s->values[AW_GLOBAL][i].id,key))break;
    if(i==s->count[AW_GLOBAL])return 1;
    fact=(uint32_t)s->values[AW_GLOBAL][i].value;level=(fact>>20)&1023U;
    if(!fact || !(fact&SEED_MASK) || level<1 || level>1000 || (fact&(DONE|EMPTY))==(DONE|EMPTY))return 0;
    if(s->harvest.slots && s->harvest.facts[h->plant[plant].slot-1] &&
       s->harvest.facts[h->plant[plant].slot-1]!=fact)return 0;
    if(!fact_set(h,plant,s,fact))return 0;
    /* Release the old quest/global slot; tracker now counts the dense fact once. */
    s->count[AW_GLOBAL]--;
    memmove(&s->values[AW_GLOBAL][i],&s->values[AW_GLOBAL][i+1],
        (s->count[AW_GLOBAL]-i)*sizeof(aw_value_t));
    memset(&s->values[AW_GLOBAL][s->count[AW_GLOBAL]],0,sizeof(aw_value_t));return 1;
}
int AW_HarvestHidden(const aw_harvest_t *h,int plant,const aw_state_t *state)
{
    return plant>=0 && plant<h->plants && (!h->slots || (h->plant[plant].slot>=1 && h->plant[plant].slot<=h->slots && h->slots<=AW_HARVEST_SLOTS)) && compatible(h,state) &&
        (fact_get(h,plant,state)&(DONE|EMPTY))!=0;
}
int AW_HarvestPickedCount(const aw_state_t *state)
{
    int i,k,count=0;uint32_t fact,level;const char *key;
    if(!state || state->count[AW_GLOBAL]<0 || state->count[AW_GLOBAL]>AW_STATE_VALUES)return 0;
    if(state->harvest.slots>AW_HARVEST_SLOTS)return 0;
    for(i=0;i<(int)state->harvest.slots;i++){
        fact=state->harvest.facts[i];level=(fact>>20)&1023U;
        if((fact&(DONE|EMPTY))==DONE && (fact&SEED_MASK) && level>=1 && level<=1000)count++;
    }
    for(i=0;i<state->count[AW_GLOBAL];i++){
        key=state->values[AW_GLOBAL][i].id;
        if(strlen(key)!=57 || strncmp(key,"aw:h:",5))continue;
        for(k=5;k<57;k++)if(!((key[k]>='a' && key[k]<='z') || (key[k]>='2' && key[k]<='7')))break;
        if(k!=57)continue;
        fact=(uint32_t)state->values[AW_GLOBAL][i].value;level=(fact>>20)&1023U;
        if((fact&(DONE|EMPTY))==DONE && (fact&SEED_MASK) && level>=1 && level<=1000)count++;
    }
    return count;
}
static int contents(const aw_harvest_t *h,const aw_harvest_plant_t *p,int level,uint32_t seed,int *amounts)
{
    const aw_harvest_edge_t *e;int i,k,item,each,amount,total=0;
    memset(amounts,0,AW_HARVEST_NODES*sizeof(*amounts));
    for(i=p->first;i<p->first+p->count;i++){
        e=&h->edge[i];each=h->node[e->node].kind==1 && (h->node[e->node].flags&1);
        amount=each?1:e->count;
        for(k=0;k<(each?e->count:1);k++){
            item=resolve(h,e->node,level,&seed,0);
            if(item==-2)return -1;
            if(item>=0){amounts[item]+=amount;total+=amount;}
        }
    }
    return total;
}
int AW_HarvestPrepare(const aw_harvest_t *h,int plant,aw_state_t *state,int level,uint32_t entropy)
{
    const aw_harvest_plant_t *p;uint32_t fact,seed;int total,amounts[AW_HARVEST_NODES];
    if(plant<0 || plant>=h->plants || !AW_HarvestValidate(h) || level<1 || level>1000)return -1;
    if(!compatible(h,state) || !migrate(h,plant,state))return -1;
    p=&h->plant[plant];fact=fact_get(h,plant,state);
    if(fact&(DONE|EMPTY))return 0;
    if(!fact){
        seed=entropy&SEED_MASK;if(!seed)seed=1;
        fact=((uint32_t)level<<20)|seed;
        /* Save the encounter roll before visibility or retryable insertion. */
        if(!fact_set(h,plant,state,fact))return -1;
    }
    level=(fact>>20)&1023U;seed=fact&SEED_MASK;
    if(!seed || level<1 || level>1000)return -1;
    total=contents(h,p,level,seed,amounts);if(total<0)return -1;
    if(!total){if(!fact_set(h,plant,state,fact|EMPTY))return -1;return 0;}
    return 1;
}
int AW_HarvestTake(const aw_harvest_t *h,int plant,aw_state_t *state,int level,uint32_t entropy)
{
    /* Transaction scratch contains only inventory (2 KiB), not the whole
     * world harvest array. Validate every grant before committing any item. */
    aw_value_t next[AW_STATE_VALUES];int count,j,k;char key[64];
    const aw_harvest_plant_t *p;uint32_t fact;
    int ready,i,amounts[AW_HARVEST_NODES];

    i=AW_HarvestHidden(h,plant,state);
    ready=AW_HarvestPrepare(h,plant,state,level,entropy);
    if(ready<0)return -1;
    if(!ready)return i?0:2;
    p=&h->plant[plant];fact=fact_get(h,plant,state);
    if(contents(h,p,(fact>>20)&1023U,fact&SEED_MASK,amounts)<=0)return -1;
    count=state->count[AW_ITEM];if(count<0 || count>AW_STATE_VALUES)return -1;
    memcpy(next,state->values[AW_ITEM],sizeof(next));
    for(i=0;i<h->nodes;i++)if(amounts[i]){
        strcpy(key,AW_HarvestText(h,h->node[i].id));
        for(k=0;key[k];k++)if(key[k]>='A' && key[k]<='Z')key[k]+='a'-'A';
        for(j=0;j<count;j++)if(!strcmp(next[j].id,key))break;
        if(j==count){if(count==AW_STATE_VALUES)return -1;memset(&next[count],0,sizeof(next[count]));strcpy(next[count++].id,key);}
        if(next[j].value<0 || next[j].value>INT32_MAX-amounts[i])return -1;
        next[j].value+=amounts[i];
    }
    if(!fact_set(h,plant,state,fact|DONE))return -1;
    memcpy(state->values[AW_ITEM],next,sizeof(next));state->count[AW_ITEM]=count;return 1;
}
