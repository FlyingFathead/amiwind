/* Host fixture (tests/test_held_item_table_full.py, HELD-ITEM-TABLE-FULL-69): a full level's item tag tables give the
 * entry of a model nobody uses to the next armed model.
 *
 * The engine keeps one tag table per armed actor model, 64 a level. A session on the joined world is one level: the
 * island and every room it joins. The tables were filled once and never given back, so every armed actor met after
 * the level's 64th distinct armed model drew no weapon, shield or torch until the next load. Now a spawn that finds
 * the table full takes the first skeletal entry that no live actor uses (aw_items.c AW_ItemsTableSlot, fed by
 * table_slot); a row table keeps its entry (its rows are on the level's memory), and an entry in use is never taken.
 * The walk below is the game data's own size: 354 armed actor models in the actor table, a dozen in view at a time. */
#define AW_ITEMS_HOST_TEST
#include "aw_items.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

float Q_SinRad(float r) {(void)r;return 0;}
float Q_CosRad(float r) {(void)r;return 1;}
int AW_ItemsTableSlot(int used,int size,const unsigned char *flags);
#define SKEL 1
#define BUSY 2
#define SIZE 64
#define MODELS 354
#define IN_VIEW 12

/* the rule before: a full table takes no new model */
static int old_slot(int used,int size) {return used<size?used:-1;}

int main(void) {
    unsigned char flags[SIZE];
    int owner[SIZE];            /* the model whose table an entry holds */
    int used=0,m,k,at,drawn=0,old_used=0,old_drawn=0,given_on=0;
    memset(flags,0,sizeof(flags));
    /* a free entry first, in order, whatever the flags say */
    for(k=0;k<SIZE;k++)assert(AW_ItemsTableSlot(k,SIZE,flags)==k);
    /* THE SESSION: armed models met one after another; the last IN_VIEW of them are still on the map */
    for(m=0;m<MODELS;m++){
        if(old_slot(old_used,SIZE)>=0){old_used++;old_drawn++;}
        for(k=0;k<used;k++)flags[k]=(unsigned char)(SKEL|(owner[k]>m-IN_VIEW?BUSY:0));   /* the scan of the live actors */
        at=AW_ItemsTableSlot(used,SIZE,flags);
        assert(at>=0);                                  /* BEFORE: -1 from the 65th model on */
        if(at==used)used++;
        else{assert(owner[at]<=m-IN_VIEW);given_on++;}  /* only ever an entry nobody uses */
        owner[at]=m;drawn++;
    }
    printf("session of %d armed models, %d on the map at once: before %d drew their items and %d drew none; now %d "
           "draw them, %d entries given on\n",MODELS,IN_VIEW,old_drawn,MODELS-old_drawn,drawn,given_on);
    assert(old_drawn==SIZE && MODELS-old_drawn==290);
    assert(drawn==MODELS && used==SIZE && given_on==MODELS-SIZE);
    /* the 65th model of a level, exactly: the old rule refuses it, the new one gives it the first unused entry */
    for(k=0;k<SIZE;k++)flags[k]=SKEL|BUSY;
    flags[7]=SKEL;flags[20]=SKEL;
    assert(old_slot(SIZE,SIZE)<0);
    assert(AW_ItemsTableSlot(SIZE,SIZE,flags)==7);
    /* every entry in use by a live actor: none (the engine says so once a level and counts it) */
    flags[7]=flags[20]=SKEL|BUSY;
    assert(AW_ItemsTableSlot(SIZE,SIZE,flags)<0);
    /* a row table is never given on, used or not: its rows stay on the level's memory */
    flags[3]=0;flags[4]=BUSY;
    assert(AW_ItemsTableSlot(SIZE,SIZE,flags)<0);
    flags[40]=SKEL;
    assert(AW_ItemsTableSlot(SIZE,SIZE,flags)==40);
    /* bad counts: nothing */
    assert(AW_ItemsTableSlot(-1,SIZE,flags)<0 && AW_ItemsTableSlot(SIZE+1,SIZE,flags)<0 && AW_ItemsTableSlot(0,0,flags)<0);
    printf("item tag table slot ok\n");
    return 0;
}
