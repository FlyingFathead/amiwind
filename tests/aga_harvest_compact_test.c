/* SPDX-License-Identifier: GPL-2.0-or-later
 * Real parser, harvest, AWS3 codec and proxy routines with synthetic records.
 * Allocation wrappers force moving realloc and inject each allocation failure.
 */
#include "quakedef.h"
#include "aw_harvest.h"
#include "aw_harvest_proxy.h"
#define main original_harvest_main
#include "aga_harvest_test.c"
#undef main
server_t sv;server_static_t svs;client_static_t cls;viddef_t vid;
int cl_numvisedicts,mod_numknown;entity_t *cl_visedicts[MAX_VISEDICTS];model_t mod_known[256];
static model_t fake[8];static byte colormap[16384];static int loads,missing,diagnostics;
static entity_t unrelated;
typedef struct {void *pointer;size_t bytes;} allocation_t;
static allocation_t allocation[16];static size_t live_bytes,peak_bytes;
static int allocation_calls,fail_on,moves;
void *__real_calloc(size_t,size_t);void *__real_realloc(void *,size_t);void __real_free(void *);
static void remember(void *p,size_t bytes)
{
    int i;if(!p)return;
    for(i=0;i<16;i++)if(!allocation[i].pointer)break;assert(i<16);
    allocation[i].pointer=p;allocation[i].bytes=bytes;live_bytes+=bytes;
    if(live_bytes>peak_bytes)peak_bytes=live_bytes;
}
void *__wrap_calloc(size_t count,size_t bytes)
{
    void *p;if(++allocation_calls==fail_on)return NULL;
    p=__real_calloc(count,bytes);remember(p,count*bytes);return p;
}
void __wrap_free(void *p)
{
    int i;if(!p)return;
    for(i=0;i<16;i++)if(allocation[i].pointer==p)break;assert(i<16);
    live_bytes-=allocation[i].bytes;allocation[i].pointer=NULL;allocation[i].bytes=0;__real_free(p);
}
void *__wrap_realloc(void *p,size_t bytes)
{
    void *next;int i;size_t old=0;
    if(++allocation_calls==fail_on)return NULL;
    if(p){for(i=0;i<16;i++)if(allocation[i].pointer==p)break;assert(i<16);old=allocation[i].bytes;}
    next=__real_calloc(1,bytes);if(!next)return NULL;remember(next,bytes);
    if(p){memcpy(next,p,old<bytes?old:bytes);__wrap_free(p);moves++;}return next;
}
void Con_Printf(char *fmt,...){(void)fmt;diagnostics++;}
qboolean Mod_CanFindName(const char *name){(void)name;return mod_numknown<256;}
model_t *Mod_ForName(char *name,qboolean crash)
{
    int index=name[15]-'0';(void)crash;assert(index>=0 && index<8);loads++;
    return missing==index+1?NULL:&fake[index];
}
static void source_key_text(int index,char *key)
{
    int k;strcpy(key,"aw:h:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
    for(k=0;k<4;k++)key[5+k]="abcdefghijklmnopqrstuvwxyz234567"[(index>>(k*5))&31];
}
static FILE *catalogue_file(int count,int reverse,int version,int *bytes)
{
    FILE *f=tmpfile();int i,index;char key[64];assert(f);
    if(!count){fputs("AWH1 0 0 0\n",f);*bytes=(int)ftell(f);rewind(f);return f;}
    fprintf(f,"AWH%d 2 2 %d 4096 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa%s\n",version,count,version==4?" 8":"");
    if(version==4)for(i=0;i<8;i++)fprintf(f,"progs/harvest/a%d.mdl bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb -3 -2 -1 4 5 6\n",i);
    fputs("0 0 0 0 0 ingredient\tOriginal ingredient\n2 0 0 0 0 missing\t-\n0 0 2\n1 0 1\n",f);
    for(i=0;i<count;i++){
        index=reverse?count-1-i:i;source_key_text(index,key);
        fprintf(f,"%s %d %d ",key,index+1,index+100);
        if(version==4)fprintf(f,"@%d",index%8);else fprintf(f,"*%d",index+1);
        fprintf(f," 11 %d 1 %.9g %.9g %.9g %.9g %.9g %.9g",index==count-1?1:0,
            (float)(index*.25-reverse*100),(float)(index*-.5),1.125,-15.5,(float)(index*1.25),21.5);
        if(version==4)fprintf(f," %.9g",(float)(1.125+index*.001));
        fputs(" Original mushroom\n",f);
    }
    *bytes=(int)ftell(f);rewind(f);return f;
}
static int load_catalogue(int count,int reverse,int version)
{
    int bytes,result;FILE *f=catalogue_file(count,reverse,version,&bytes);
    result=AW_HarvestLoad(f,bytes,&h);fclose(f);return result;
}
static void dense(int count)
{
    int i,k,call_count;unsigned short saved;size_t table,loader_peak,with_proxies;char key[64];
    AW_HarvestProxyClear();AW_HarvestRelease(&h);assert(!live_bytes);
    peak_bytes=0;allocation_calls=0;assert(load_catalogue(count,0,4));call_count=allocation_calls;
    assert(h.plants==count && h.plant_capacity==count && h.nodes==2 && h.models==8);
    assert(h.plant[0].label==h.plant[count-1].label && h.plant[0].model==h.plant[8].model);
    table=live_bytes;loader_peak=peak_bytes;assert(table==AW_HarvestStorageBytes(&h));
    for(i=0;i<count;i++){
        source_key_text(i,key);assert(!strcmp(AW_HarvestText(&h,h.plant[i].key),key));
        assert(h.plant[i].slot==i+1 && h.plant[i].reference==(unsigned)i+100);
        assert(h.plant[i].origin[0]==(float)(i*.25) && h.plant[i].origin[1]==(float)(i*-.5));
        assert(h.plant[i].origin[2]==1.125f && h.plant[i].angles[0]==-15.5f && h.plant[i].angles[1]==(float)(i*1.25));
        assert(h.plant[i].angles[2]==21.5f && h.plant[i].scale==(float)(1.125+i*.001));
    }
    memset(&state,0,sizeof(state));loads=0;
    assert(AW_HarvestProxySpawn(&h,&state,7,123)==count-1 && loads==8);
    assert(!state.count[AW_ITEM] && AW_HarvestHidden(&h,count-1,&state));with_proxies=live_bytes;
    assert(AW_HarvestProxyBytes()==(count-1)*sizeof(entity_t)+count*3U);
    cl_numvisedicts=1;cl_visedicts[0]=&unrelated;AW_HarvestProxyLink();assert(cl_numvisedicts==count);
    for(i=0;i<count-1;i++){
        entity_t *e=AW_HarvestProxyEntity(i);assert(e && !memcmp(e->origin,h.plant[i].origin,sizeof(e->origin)));
        assert(!memcmp(e->angles,h.plant[i].angles,sizeof(e->angles)) && e->aw_sprite_scale==h.plant[i].scale);
        assert(e->model==&fake[i%8]);
    }
    before=state;AW_HarvestProxyClear();assert(cl_numvisedicts==1 && cl_visedicts[0]==&unrelated && live_bytes==table);
    /* Every proxy allocation failure is visible and leaves persistent facts. */
    fail_on=allocation_calls+1;k=diagnostics;assert(!AW_HarvestProxySpawn(&h,&state,999,999));fail_on=0;
    assert(diagnostics>k && live_bytes==table && !memcmp(&before,&state,sizeof(state)));
    missing=8;k=diagnostics;assert(!AW_HarvestProxySpawn(&h,&state,999,999));missing=0;
    assert(diagnostics>k && live_bytes==table && !memcmp(&before,&state,sizeof(state)));
    assert(AW_HarvestProxySpawn(&h,&state,999,999)==count-1);
    cl_numvisedicts=MAX_VISEDICTS-(count-2);k=cl_numvisedicts;
    AW_HarvestProxyLink();assert(cl_numvisedicts==k);for(i=0;i<count;i++)assert(!AW_HarvestProxyEntity(i));
    cl_numvisedicts=0;AW_HarvestProxyLink();assert(cl_numvisedicts==count-1);
    for(i=0;i<count-1;i++)assert(AW_HarvestTake(&h,i,&state,999,777)==1);
    assert(AW_StateGet(&state,AW_ITEM,"ingredient")==2*(count-1));assert(AW_HarvestPickedCount(&state)==count-1);
    save_roundtrip();before=state;AW_HarvestProxyClear();
    for(k=0;k<6;k++){
        assert(load_catalogue(count,1,k&1?3:4));
        for(i=0;i<count;i++)assert(AW_HarvestPrepare(&h,i,&state,1,888)==0 && AW_HarvestTake(&h,i,&state,1,999)==0);
        save_roundtrip();assert(!memcmp(&state,&before,sizeof(state)));
    }
    assert(load_catalogue(count,0,4));h.catalogue[0]^=1;
    assert(AW_HarvestPrepare(&h,0,&state,1,1)==-1 && !memcmp(&before,&state,sizeof(state)));h.catalogue[0]^=1;
    saved=h.plant[0].key;h.plant[0].key++;assert(!AW_HarvestValidate(&h));h.plant[0].key=saved;
    h.plant[1].slot=h.plant[0].slot;assert(!AW_HarvestValidate(&h));
    AW_HarvestRelease(&h);assert(!live_bytes);
    /* Force failure at every parser allocation, including moving dictionary
     * growth. Reject cleanup always empties the owner and releases all bytes. */
    for(k=1;k<=call_count;k++){
        allocation_calls=0;fail_on=k;assert(!load_catalogue(count,0,4));
        assert(!live_bytes && !h.storage && !h.text && !h.plants);fail_on=0;
    }
    printf("COMPACT count=%d table=%lu forced_moving_loader_peak=%lu with_proxies=%lu parser_allocations=%d\n",
        count,(unsigned long)table,(unsigned long)loader_peak,(unsigned long)with_proxies,call_count);
}
int main(void)
{
    int i,bytes;FILE *f;
    /* Initialization itself never inspects/frees dirty stack-like contents. */
    memset(&h,0xa5,sizeof(h));AW_HarvestInitData(&h);assert(!live_bytes && !h.storage);
    assert(load_catalogue(0,0,1));assert(!live_bytes && !AW_HarvestStorageBytes(&h));
    sv.active=true;svs.maxclients=1;cls.state=ca_connected;vid.colormap=colormap;
    for(i=0;i<8;i++){fake[i].type=mod_alias;fake[i].numframes=1;}
    strcpy(aw_races[0].id,"race");strcpy(aw_classes[0].id,"class");strcpy(aw_births[0].id,"birth");
    strcpy(aw_parts[0].id,"head");strcpy(aw_parts[1].id,"hair");aw_parts[1].kind=1;
    dense(77);dense(80);dense(256);assert(!load_catalogue(257,0,4) && !live_bytes);
    assert(load_catalogue(77,0,4));f=catalogue_file(77,0,4,&bytes);
    assert(!AW_HarvestLoad(f,bytes-2,&h));fclose(f);assert(!live_bytes);
    AW_HarvestRelease(&h);AW_HarvestRelease(&h);assert(!live_bytes && moves>0);
    puts("Dense full admission, exact poses/keys, AWS3 overlap, all allocation failures and empty teardown passed");return 0;
}
