/* SPDX-License-Identifier: GPL-2.0-or-later
 * FLORA-FAUNA-COVERAGE-62: a new harvest kind joins the global placement index as a new generation. A save made with
 * the earlier index keeps every pick fact (its slots are the first slots of the new one) and is taken over in place;
 * a save of an unrelated index still fails closed. Catalogues may name up to 16 shared models ('@0'..'@15'). */
#define main original_harvest_main
#include "aga_harvest_test.c"
#undef main
#define OLD "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
#define NEW "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
static int load(const char *text)
{
    FILE *f=tmpfile();int n,ok;assert(f);fputs(text,f);n=(int)ftell(f);rewind(f);
    ok=AW_HarvestLoad(f,n,&h);fclose(f);return ok;
}
/* the first index: two mushrooms in slots 1 and 2; the next: the same two and a trunk fungus in slot 3 */
static void older(void)
{
    assert(load("AWH4 1 1 2 2 " OLD " 1\n"
                "progs/harvest/mushroom.mdl bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb -1 -1 -1 1 1 1\n"
                "0 0 0 0 0 ingredient\tOriginal ingredient\n0 0 1\n"
                "aw:h:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 1 42 @0 11 0 1 0 0 0 0 0 0 1 Mushroom\n"
                "aw:h:baaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 2 43 @0 11 0 1 20 0 0 0 0 0 1 Mushroom\n"));
    assert(h.slots==2 && !h.bases);
}
static void newer(const char *bases)
{
    char text[2048];
    snprintf(text,sizeof(text),"AWH4 1 1 3 3 " NEW " 2%s\n"
             "progs/harvest/mushroom.mdl bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb -1 -1 -1 1 1 1\n"
             "progs/harvest/fungus.mdl dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd -1 -1 -1 1 1 1\n"
             "0 0 0 0 0 ingredient\tOriginal ingredient\n0 0 1\n"
             "aw:h:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 1 42 @0 11 0 1 0 0 0 0 0 0 1 Mushroom\n"
             "aw:h:baaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 2 43 @0 11 0 1 20 0 0 0 0 0 1 Mushroom\n"
             "aw:h:caaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 3 44 @1 11 0 1 40 0 30 0 90 0 1 Bracket fungus\n",
             bases);
    assert(load(text));
}
static void many_models(int models,const char *pick,int expect)
{
    char text[8192];int at,i;
    at=snprintf(text,sizeof(text),"AWH4 1 1 1 3 " NEW " %d bases 1 2 " OLD "\n",models);
    for(i=0;i<models;i++)
        at+=snprintf(text+at,sizeof(text)-at,"progs/harvest/m%02d.mdl bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb -1 -1 -1 1 1 1\n",i);
    snprintf(text+at,sizeof(text)-at,"0 0 0 0 0 ingredient\tOriginal ingredient\n0 0 1\n"
             "aw:h:caaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 3 44 %s 11 0 1 40 0 30 0 90 0 1 Bracket fungus\n",pick);
    assert(load(text)==expect);
}
int main(int argc,char **argv)
{
    aw_state_t kept;(void)argc;original_harvest_main(1,argv);
    /* a game played with the first index: one mushroom picked, saved */
    memset(&state,0,sizeof(state));older();
    assert(AW_HarvestPrepare(&h,0,&state,1,123)==1 && AW_HarvestTake(&h,0,&state,1,123)==1);
    assert(AW_HarvestPrepare(&h,1,&state,1,456)==1);
    save_roundtrip();kept=state;
    /* the next build: its catalogues name the first index as their base */
    newer(" bases 1 2 " OLD);
    assert(h.bases==1 && h.base_slots[0]==2 && AW_HarvestValidate(&h));
    /* nothing is written by looking: the picked mushroom stays picked, the other keeps its first roll */
    assert(AW_HarvestHidden(&h,0,&state) && !AW_HarvestHidden(&h,1,&state) && !AW_HarvestHidden(&h,2,&state));
    assert(AW_HarvestPrepare(&h,0,&state,999,999)==0 && AW_HarvestTake(&h,0,&state,999,999)==0);
    assert(!memcmp(&state,&kept,sizeof(state)));
    /* the trunk fungus is new: its first roll takes the save over to the new index; the earlier facts stay */
    assert(AW_HarvestPrepare(&h,2,&state,1,789)==1);
    assert(state.harvest.slots==3 && !memcmp(state.harvest.catalogue,h.catalogue,32));
    assert(state.harvest.facts[0]==kept.harvest.facts[0] && state.harvest.facts[1]==kept.harvest.facts[1]);
    assert(AW_HarvestTake(&h,2,&state,1,789)==1 && AW_HarvestHidden(&h,2,&state));
    assert(AW_StateGet(&state,AW_ITEM,"ingredient")==2 && AW_HarvestPickedCount(&state)==2);
    save_roundtrip();
    assert(AW_HarvestHidden(&h,0,&state) && AW_HarvestHidden(&h,2,&state) && AW_HarvestPrepare(&h,1,&state,1,1)==1);
    /* the earlier catalogue no longer reads the newer save: mixing index spaces still fails closed */
    older();assert(AW_HarvestPrepare(&h,1,&state,1,1)==-1);
    /* a save of an index that is no base of this one: refused, unchanged */
    memset(&state,0,sizeof(state));older();assert(AW_HarvestPrepare(&h,0,&state,1,1)==1);
    state.harvest.catalogue[0]^=1;kept=state;newer(" bases 1 2 " OLD);
    assert(AW_HarvestPrepare(&h,2,&state,1,1)==-1 && !memcmp(&state,&kept,sizeof(state)));
    /* without bases the earlier save is refused, as before */
    memset(&state,0,sizeof(state));older();assert(AW_HarvestPrepare(&h,0,&state,1,1)==1);
    newer("");assert(!h.bases && AW_HarvestPrepare(&h,2,&state,1,1)==-1);
    /* bases are checked: below this index's slots, rising, nonzero and unlike its own digest, at most 4 */
    assert(!load("AWH4 1 1 0 3 " NEW " 1 bases 1 3 " OLD "\nprogs/harvest/m.mdl bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb -1 -1 -1 1 1 1\n0 0 0 0 0 i\tI\n0 0 1\n"));
    assert(!load("AWH4 1 1 0 3 " NEW " 1 bases 1 2 " NEW "\nprogs/harvest/m.mdl bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb -1 -1 -1 1 1 1\n0 0 0 0 0 i\tI\n0 0 1\n"));
    assert(!load("AWH4 1 1 0 9 " NEW " 1 bases 2 2 " OLD " 2 bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\nprogs/harvest/m.mdl bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb -1 -1 -1 1 1 1\n0 0 0 0 0 i\tI\n0 0 1\n"));
    assert(!load("AWH4 1 1 0 9 " NEW " 1 bases 5 1 " OLD " 2 " OLD " 3 " OLD " 4 " OLD " 5 " OLD "\n"));
    assert(!load("AWH4 1 1 0 3 " NEW " 1 bases 0\nprogs/harvest/m.mdl bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb -1 -1 -1 1 1 1\n0 0 0 0 0 i\tI\n0 0 1\n"));
    /* up to 16 shared models, two-digit indices without a leading zero */
    many_models(12,"@11",1);assert(AW_HarvestModelIndex(&h,0)==11);
    many_models(16,"@15",1);assert(AW_HarvestModelIndex(&h,0)==15);
    many_models(12,"@12",0);many_models(12,"@011",0);many_models(12,"@1a",0);many_models(16,"@16",0);
    many_models(1,"@0",1);many_models(17,"@0",0);
    puts("Harvest index generations: earlier saves keep their facts and are taken over, unrelated ones refused; 16 models");
    return 0;
}
