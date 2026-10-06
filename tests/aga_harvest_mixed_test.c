/* SPDX-License-Identifier: GPL-2.0-or-later */
#define main original_harvest_main
#include "aga_harvest_test.c"
#undef main
static void catalogue(int version)
{
    FILE *f=tmpfile();int i,n;assert(f);
    fprintf(f,"AWH%d 2 2 2 2 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa%s\n",
            version,version==4?" 1":"");
    if(version==4)fputs("progs/harvest/test.mdl bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb -1 -1 -1 1 1 1\n",f);
    fputs("0 0 0 0 0 ingredient\tOriginal ingredient\n2 0 0 0 0 missing\t-\n0 0 2\n1 0 1\n",f);
    for(i=0;i<2;i++){
        char key[64];strcpy(key,"aw:h:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");key[5]='a'+i;
        fprintf(f,"%s %d %d %s 11 %d 1 %d 0 0 0 0 0%s Synthetic plant\n",
                key,i+1,42+i,version==4?"@0":(i?"*2":"*1"),i,i*20,version==4?" 1.25":"");
    }
    n=(int)ftell(f);rewind(f);assert(AW_HarvestRead(f,n,&h));fclose(f);
    assert(h.slots==2 && h.plants==2 && h.representation==(version==4?4:0));
}
int main(int argc,char **argv)
{
    int first,next,k;original_harvest_main(1,argv);
    for(first=3;first<=4;first++){
        memset(&state,0,sizeof(state));catalogue(first);
        assert(AW_HarvestPrepare(&h,0,&state,1,123)==1);
        assert(AW_HarvestPrepare(&h,1,&state,1,456)==0);
        assert(AW_HarvestTake(&h,0,&state,999,999)==1);
        assert(AW_StateGet(&state,AW_ITEM,"ingredient")==2);
        assert(AW_HarvestPickedCount(&state)==1);save_roundtrip();before=state;
        for(k=0;k<6;k++){
            next=(k&1)?first:7-first;catalogue(next);
            assert(AW_HarvestHidden(&h,0,&state) && AW_HarvestHidden(&h,1,&state));
            assert(AW_HarvestPrepare(&h,0,&state,999,999)==0);
            assert(AW_HarvestPrepare(&h,1,&state,999,999)==0);
            assert(AW_HarvestTake(&h,0,&state,999,999)==0);
            assert(AW_HarvestTake(&h,1,&state,999,999)==0);
            save_roundtrip();assert(!memcmp(&state,&before,sizeof(state)));
        }
        h.catalogue[0]^=1;assert(AW_HarvestPrepare(&h,0,&state,1,1)==-1);
        assert(!memcmp(&state,&before,sizeof(state)));
        catalogue(4);h.plant[0].scale=0;assert(!AW_HarvestValidate(&h));
        catalogue(4);strcpy(h.plant[0].model,"@8");assert(!AW_HarvestValidate(&h));
        catalogue(4);memset(h.model[0].digest,0,32);assert(!AW_HarvestValidate(&h));
        catalogue(4);strcpy(h.model[0].path,"progs/harvest/../bad.mdl");assert(!AW_HarvestValidate(&h));
    }
    puts("AWH3/AWH4 picked and empty original facts survive bidirectional save/load/return without reroll");
    return 0;
}
