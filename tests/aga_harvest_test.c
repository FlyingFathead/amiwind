/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <assert.h>
#include <string.h>
#include <limits.h>
#include "aw_harvest.h"
#include "aw_save.h"
aw_race_t aw_races[16];aw_class_t aw_classes[32];aw_birth_t aw_births[16];aw_part_t aw_parts[384];
int aw_race_count=1,aw_class_count=1,aw_birth_count=1,aw_part_count=2;
static aw_harvest_t h;static aw_state_t state,before;
#include "aga_harvest_fixture.h"
static void fixture(void)
{
    harvest_fixture_storage();memset(&state,0,sizeof(state));h.nodes=3;h.edges=3;h.plants=1;
    h.node[0].kind=1;h.node[0].flags=1;h.node[0].count=2;strcpy(HSTR(h.node[0].id),"list");
    strcpy(HSTR(h.node[1].id),"ingredient_a");strcpy(HSTR(h.node[2].id),"ingredient_b");
    h.edge[0].node=1;h.edge[0].level=1;h.edge[0].count=1;
    h.edge[1].node=2;h.edge[1].level=2;h.edge[1].count=1;
    h.edge[2].node=0;h.edge[2].count=2;
    strcpy(HSTR(h.plant[0].key),"aw:h:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
    strcpy(HSTR(h.plant[0].label),"Synthetic mushroom");strcpy(HSTR(h.plant[0].model),"*1");
    h.plant[0].reference=42;h.plant[0].flags=11;h.plant[0].first=2;h.plant[0].count=1;
    assert(AW_HarvestValidate(&h));
}
static void save_roundtrip(void)
{
    static aw_save_t saved,loaded;static unsigned char bytes[AW_SAVE_BYTES];int n;
    memset(&saved,0,sizeof(saved));saved.sequence=1;saved.profile=1;strcpy(saved.scene,"seyda");
    strcpy(saved.story.name,"Synthetic");saved.story.stage=AW_STAGE_RELEASED;saved.story.ship_disabled=1;saved.story.captain=-1;
    saved.character.level=1;saved.character.hair=1;
    strcpy(aw_races[0].id,"race");strcpy(aw_classes[0].id,"class");strcpy(aw_births[0].id,"birth");
    strcpy(aw_parts[0].id,"head");strcpy(aw_parts[1].id,"hair");aw_parts[1].kind=1;
    assert(AW_StateSet(&state,AW_GLOBAL,"chargenstate",-1));saved.state=state;
    n=AW_SaveEncode(bytes,sizeof(bytes),&saved);assert(n>0);assert(AW_SaveDecode(bytes,n,&loaded));
    memset(&state,0,sizeof(state));state=loaded.state;assert(!memcmp(&state,&saved.state,sizeof(state)));
}
int main(int argc,char **argv)
{
    int i,found=0,a,b,result;char id[64];FILE *f;
    fixture();assert(AW_HarvestPrepare(&h,0,&state,1,123)==1);
    assert(!state.count[AW_ITEM] && !AW_HarvestHidden(&h,0,&state));
    before=state;assert(AW_HarvestPrepare(&h,0,&state,999,999)==1 && !memcmp(&state,&before,sizeof(state)));
    assert(AW_HarvestTake(&h,0,&state,999,999)==1); /* encounter level/roll retained */
    assert(AW_StateGet(&state,AW_ITEM,"ingredient_a")==2);assert(AW_HarvestHidden(&h,0,&state));
    assert(AW_HarvestPickedCount(&state)==1);
    save_roundtrip();before=state;assert(AW_HarvestTake(&h,0,&state,20,999)==0);assert(!memcmp(&state,&before,sizeof(state)));
    assert(AW_HarvestPickedCount(&state)==1);
    /* Scene-local model indices change; full source identity does not. */
    strcpy(HSTR(h.plant[0].model),"*19");assert(AW_HarvestHidden(&h,0,&state));
    HSTR(h.plant[0].key)[5]='b';assert(!AW_HarvestHidden(&h,0,&state));
    fixture();assert(AW_HarvestTake(&h,0,&state,2,123)==1);assert(AW_StateGet(&state,AW_ITEM,"ingredient_b")==2);
    fixture();h.node[0].chance=100;assert(AW_HarvestTake(&h,0,&state,2,123)==2);
    assert(!state.count[AW_ITEM] && AW_HarvestHidden(&h,0,&state));
    assert(AW_StateGet(&state,AW_GLOBAL,HSTR(h.plant[0].key))<0); /* EMPTY is bit31, not level bits20..29. */
    save_roundtrip();assert(AW_HarvestHidden(&h,0,&state));before=state;
    assert(AW_HarvestPrepare(&h,0,&state,999,777)==0 && !memcmp(&state,&before,sizeof(state)));
    assert(AW_HarvestTake(&h,0,&state,999,777)==0 && !state.count[AW_ITEM]);
    assert(AW_HarvestPickedCount(&state)==0);
    assert(AW_StateSet(&state,AW_GLOBAL,"ordinary",0x40100001));
    assert(AW_StateSet(&state,AW_GLOBAL,"aw:h:invalid",0x40100001));
    assert(AW_HarvestPickedCount(&state)==0);
    /* Each resolves independently; without Each the selected stack repeats. */
    for(i=1;i<1000;i++){
        fixture();h.node[0].flags=3;assert(AW_HarvestTake(&h,0,&state,2,(uint32_t)i)==1);
        a=AW_StateGet(&state,AW_ITEM,"ingredient_a");b=AW_StateGet(&state,AW_ITEM,"ingredient_b");
        if(a==1 && b==1){found=1;break;}
    }
    assert(found);fixture();h.node[0].flags=2;assert(AW_HarvestTake(&h,0,&state,2,(uint32_t)i)==1);
    assert(AW_StateGet(&state,AW_ITEM,"ingredient_a")==2 || AW_StateGet(&state,AW_ITEM,"ingredient_b")==2);
    /* Capacity/overflow failures leave the plant visible and inventory intact. */
    fixture();for(i=0;i<AW_STATE_VALUES;i++){sprintf(id,"slot%d",i);assert(AW_ItemAdd(&state,id,1));}
    assert(AW_HarvestTake(&h,0,&state,1,12)==-1);assert(!AW_HarvestHidden(&h,0,&state));
    before=state;save_roundtrip();assert(AW_HarvestTake(&h,0,&state,2,999)==-1);
    assert(AW_StateGet(&state,AW_GLOBAL,HSTR(h.plant[0].key))==AW_StateGet(&before,AW_GLOBAL,HSTR(h.plant[0].key)));
    state.count[AW_ITEM]=0;assert(AW_HarvestTake(&h,0,&state,2,999)==1);
    assert(AW_StateGet(&state,AW_ITEM,"ingredient_a")==2 && !AW_StateGet(&state,AW_ITEM,"ingredient_b"));
    fixture();assert(AW_ItemAdd(&state,"ingredient_a",INT32_MAX));assert(AW_HarvestTake(&h,0,&state,1,2)==-1);
    assert(AW_StateGet(&state,AW_ITEM,"ingredient_a")==INT32_MAX && !AW_HarvestHidden(&h,0,&state));
    fixture();for(i=0;i<AW_STATE_VALUES;i++){sprintf(id,"global%d",i);assert(AW_StateSet(&state,AW_GLOBAL,id,1));}
    before=state;assert(AW_HarvestTake(&h,0,&state,1,2)==-1 && !memcmp(&state,&before,sizeof(state)));
    /* A late second-item failure must not commit the first item. */
    fixture();h.edge[2].node=1;h.plant[0].count=2;h.edges=4;h.edge[3].node=2;h.edge[3].count=1;
    assert(AW_ItemAdd(&state,"ingredient_b",INT32_MAX));assert(AW_HarvestTake(&h,0,&state,1,2)==-1);
    assert(!AW_StateGet(&state,AW_ITEM,"ingredient_a") && !AW_HarvestHidden(&h,0,&state));
    /* Nested leveled recursion and invalid graphs are exercised directly. */
    fixture();h.nodes=4;h.node[3]=h.node[0];strcpy(HSTR(h.node[3].id),"nested");h.edge[2].node=3;
    assert(AW_HarvestTake(&h,0,&state,2,3)==1);
    h.edge[1].node=3;assert(!AW_HarvestValidate(&h));
    fixture();h.plants=2;h.plant[1]=h.plant[0];assert(!AW_HarvestValidate(&h));
    fixture();f=tmpfile();assert(f);fputs("AWH1 100000 0 0\n",f);i=(int)ftell(f);rewind(f);assert(!AW_HarvestLoad(f,i,&h));fclose(f);assert(h.plants==0);
    f=tmpfile();assert(f);fputs("AWH1 1 0 0\n0 0 0 0 0 old_item\n",f);i=(int)ftell(f);rewind(f);
    assert(AW_HarvestLoad(f,i,&h) && !HSTR(h.node[0].label)[0]);fclose(f);
    f=tmpfile();assert(f);fputs("AWH2 1 0 0\n0 0 0 0 0 item_id\tOriginal item name\n",f);i=(int)ftell(f);rewind(f);
    assert(AW_HarvestLoad(f,i,&h) && !strcmp(HSTR(h.node[0].label),"Original item name"));fclose(f);
    f=tmpfile();assert(f);fputs("AWH2 1 0 0\n0 0 0 0 0 item_id\t-\n",f);i=(int)ftell(f);rewind(f);
    assert(!AW_HarvestLoad(f,i,&h));fclose(f);
    if(argc==2){
        f=fopen(argv[1],"rb");assert(f);fseek(f,0,SEEK_END);i=(int)ftell(f);rewind(f);assert(AW_HarvestLoad(f,i,&h));fclose(f);assert(h.plants==6);
        memset(&state,0,sizeof(state));for(i=0;i<h.plants;i++){result=AW_HarvestTake(&h,i,&state,1,123+i);assert(result>0);}
        save_roundtrip();for(i=0;i<h.plants;i++)assert(AW_HarvestHidden(&h,i,&state));
    }
    puts("harvest transaction, leveled contents, capacity and AWS2 persistence passed");return 0;
}
