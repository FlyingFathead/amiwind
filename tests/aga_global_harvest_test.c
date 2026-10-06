/* SPDX-License-Identifier: GPL-2.0-or-later
 * Real harvest/save routines: global capacity, migration and rejection safety. */
#define main legacy_harvest_main
#include "aga_harvest_test.c"
#undef main
static void indexed(void)
{
    fixture();h.slots=AW_HARVEST_SLOTS;memset(h.catalogue,0x36,32);h.plant[0].slot=1;
}
static void placement(int index)
{
    int k;h.plant[0].slot=index+1;
    for(k=0;k<4;k++)HSTR(h.plant[0].key)[5+k]="abcdefghijklmnopqrstuvwxyz234567"[(index>>(5*k))&31];
}
static unsigned crc(const unsigned char *p,int n)
{
    unsigned x=~0U;int j;while(n--){x^=*p++;for(j=0;j<8;j++)x=(x>>1)^((x&1)?0xedb88320U:0);}return ~x;
}
static void put(unsigned char *p,unsigned x){p[0]=x;p[1]=x>>8;p[2]=x>>16;p[3]=x>>24;}
static void encoding(void)
{
    static aw_save_t source,decoded,sentinel;static unsigned char raw[AW_SAVE_BYTES],copy[AW_SAVE_BYTES];
    int n,at,i;char id[64];memset(&source,0,sizeof(source));source.sequence=1;source.profile=2;
    strcpy(source.scene,"seyda");strcpy(source.story.name,"Synthetic");
    source.story.stage=AW_STAGE_RELEASED;source.story.ship_disabled=1;source.story.captain=-1;
    source.character.level=1;source.character.hair=1;source.state=state;
    source.actor_count=AW_SAVE_ACTORS;
    for(i=0;i<AW_SAVE_ACTORS;i++){source.actors[i].reference=i+1;source.actors[i].scene=0;}
    assert(AW_StateSet(&source.state,AW_JOURNAL,"quest",256));
    for(i=1;i<AW_STATE_VALUES;i++){
        sprintf(id,"quest%d",i);assert(AW_StateSet(&source.state,AW_JOURNAL,id,i));
        sprintf(id,"item%d",i);assert(AW_ItemAdd(&source.state,id,i));
    }
    source.state.journal_count=AW_JOURNAL_ENTRIES;
    for(i=0;i<AW_JOURNAL_ENTRIES;i++){source.state.journal[i].quest=0;source.state.journal[i].stage=i+1;}
    n=AW_SaveEncode(raw,sizeof(raw),&source);assert(n>32768 && n<AW_SAVE_BYTES && !memcmp(raw,"AWS4",4));
    assert(AW_SaveDecode(raw,n,&decoded));assert(!memcmp(&source.state,&decoded.state,sizeof(state)));
    /* Remove only the two AWS4 words to retain a genuine old-layout
     * sparse save reader check; this fixture contains all 4096 facts. */
    at=n-4-(40+AW_HARVEST_SLOTS*8)-4;
    memcpy(copy,raw,at);memcpy(copy+at,raw+at+4,n-at-8);
    memcpy(copy,"AWS3",4);put(copy+4,n-8);put(copy+8,crc(copy+12,n-20));
    assert(AW_SaveDecode(copy,n-8,&decoded) && !decoded.equipment);
    assert(!memcmp(&source.state,&decoded.state,sizeof(state)));
    printf("maximum-state save bytes=%d, state bytes=%lu, saved-state bytes=%lu\n",n,(unsigned long)sizeof(state),(unsigned long)sizeof(source));
    memset(&sentinel,0x5a,sizeof(sentinel));decoded=sentinel;
    for(i=0;i<16;i++){assert(!AW_SaveDecode(raw,n-i-1,&decoded));assert(!memcmp(&decoded,&sentinel,sizeof(decoded)));}
    /* Sparse extension has 40 header bytes then 4096 ascending (slot,fact) pairs. */
    at=n-4-AW_HARVEST_SLOTS*8; /* Equipment follows sparse pairs. */
    memcpy(copy,raw,n);put(copy+at+8,1);put(copy+8,crc(copy+12,n-12));
    assert(!AW_SaveDecode(copy,n,&decoded) && !memcmp(&decoded,&sentinel,sizeof(decoded)));
    memcpy(copy,raw,n);put(copy+at+4,0xc0100001U);put(copy+8,crc(copy+12,n-12));
    assert(!AW_SaveDecode(copy,n,&decoded) && !memcmp(&decoded,&sentinel,sizeof(decoded)));
    memcpy(copy,raw,n);put(copy+at,AW_HARVEST_SLOTS+1);put(copy+8,crc(copy+12,n-12));
    assert(!AW_SaveDecode(copy,n,&decoded));
    source.state.harvest.slots=AW_HARVEST_SLOTS-1;assert(!AW_SaveEncode(copy,sizeof(copy),&source));
    source.state.harvest.slots=AW_HARVEST_SLOTS;source.state.harvest.facts[0]=0x40100000U;
    assert(!AW_SaveEncode(copy,sizeof(copy),&source));
    source.state=state;memset(source.state.harvest.catalogue,0,32);assert(!AW_SaveEncode(copy,sizeof(copy),&source));
}
int main(int argc,char **argv)
{
    int i;char id[64];uint32_t fact;
    legacy_harvest_main(1,argv); /* Includes AWS1/AWH1/2-era transaction semantics. */
    indexed();assert(AW_StateSet(&state,AW_GLOBAL,"chargenstate",-1));
    for(i=1;i<AW_STATE_VALUES;i++){sprintf(id,"ordinary%d",i);assert(AW_StateSet(&state,AW_GLOBAL,id,i));}
    for(i=0;i<AW_HARVEST_SLOTS;i++){
        placement(i);assert(AW_HarvestPrepare(&h,0,&state,1,i+1)==1);
        assert(AW_HarvestTake(&h,0,&state,999,17)==1);assert(AW_HarvestHidden(&h,0,&state));
    }
    assert(state.count[AW_GLOBAL]==AW_STATE_VALUES && AW_HarvestPickedCount(&state)==AW_HARVEST_SLOTS);
    assert(AW_StateGet(&state,AW_ITEM,"ingredient_a")==AW_HARVEST_SLOTS*2);
    save_roundtrip();encoding();
    placement(2000);strcpy(HSTR(h.plant[0].model),"*73");before=state;
    assert(AW_HarvestTake(&h,0,&state,1,1)==0 && !memcmp(&state,&before,sizeof(state)));
    h.catalogue[0]^=1;assert(AW_HarvestPrepare(&h,0,&state,1,1)==-1 && !memcmp(&state,&before,sizeof(state)));
    h.catalogue[0]^=1;h.plant[0].slot=AW_HARVEST_SLOTS+1;assert(!AW_HarvestValidate(&h));
    indexed();h.node[0].chance=100;assert(AW_HarvestPrepare(&h,0,&state,1,9)==0);
    fact=state.harvest.facts[0];assert(fact&0x80000000U);save_roundtrip();
    h.node[0].chance=0;assert(AW_HarvestPrepare(&h,0,&state,99,33)==0 && state.harvest.facts[0]==fact);
    assert(AW_HarvestPickedCount(&state)==0 && !state.count[AW_ITEM]);
    /* Exact-key legacy migration preserves the chosen roll, not just a boolean. */
    fixture();assert(AW_HarvestTake(&h,0,&state,1,17)==1);save_roundtrip();
    h.slots=AW_HARVEST_SLOTS;memset(h.catalogue,0x36,32);h.plant[0].slot=99;
    assert(AW_HarvestPrepare(&h,0,&state,99,88)==0);
    assert(!AW_StateGet(&state,AW_GLOBAL,HSTR(h.plant[0].key)) && (state.harvest.facts[98]&0x40000000U));
    assert(AW_HarvestPickedCount(&state)==1);save_roundtrip();
    indexed();h.edge[2].node=1;h.plant[0].count=2;h.edges=4;h.edge[3].node=2;h.edge[3].count=1;
    assert(AW_ItemAdd(&state,"ingredient_b",INT32_MAX));
    assert(AW_HarvestTake(&h,0,&state,1,7)==-1 && !AW_StateGet(&state,AW_ITEM,"ingredient_a"));
    assert(!AW_HarvestHidden(&h,0,&state));
    puts("4096 placement states, AWS4 maximum save and AWS3 compatibility, exact-key migration and atomic rejection passed");return 0;
}
