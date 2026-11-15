/* SPDX-License-Identifier: GPL-2.0-or-later
 * MAP-MULTI-MARKERS-66 / NAV-HOT-MARKER-COMPASS-66: the player's named map markers and the hot marker
 * (engine/aga/src/aw_mapmarks.c): add, default names, rename, delete, search, the allowance, the hot marker, and the
 * saved block (AWMK) with its pending load and New Game reset. */
#include "aw_mapmarks.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void){
    static unsigned char block[16384];int n,i;float x,y;
    AW_MapMarksReset();
    assert(AW_MapMarksCount()==0 && AW_MapMarksMax()==AW_MAPMARKS_DEFAULT && !AW_MapHotGet(NULL,NULL));
    assert(AW_MapMarksEncode(NULL,0)==0);   /* nothing to save: no block */
    /* add: default name, the cut at 32 characters, control characters become spaces */
    assert(AW_MapMarkAdd(-9104,-72480,NULL)==0 && !strcmp(AW_MapMark(0)->name,"Marker 1"));
    assert(AW_MapMarkAdd(100,200,"Bitter Coast Region")==1);
    assert(AW_MapMarkAdd(5,6,"0123456789012345678901234567890123456789")==2 && strlen(AW_MapMark(2)->name)==AW_MAPMARK_NAME);
    assert(AW_MapMarkAdd(7,8,"Tab\there  ")==3 && !strcmp(AW_MapMark(3)->name,"Tab here"));
    /* rename (an empty name keeps the old one), lookup by number, whole name and part, search */
    assert(AW_MapMarkRename(0,"Seyda Neen dock") && !strcmp(AW_MapMark(0)->name,"Seyda Neen dock"));
    assert(AW_MapMarkRename(0,"   ") && !strcmp(AW_MapMark(0)->name,"Seyda Neen dock"));
    assert(AW_MapMarkLookup("2")==1 && AW_MapMarkLookup("9")==-1 && AW_MapMarkLookup("seyda neen dock")==0);
    assert(AW_MapMarkLookup("bitter")==1 && AW_MapMarkLookup("nothing")==-1);
    assert(AW_MapMarkFind("seydaneen",0)==0 && AW_MapMarkFind("",1)==1 && AW_MapMarkFind("coast",2)==-1);
    assert(AW_MapMarkMatches("Ald-ruhn","aldruhn") && !AW_MapMarkMatches("Balmora","vivec"));
    /* delete: the later markers move up */
    assert(AW_MapMarkDelete(2) && AW_MapMarksCount()==3 && !strcmp(AW_MapMark(2)->name,"Tab here"));
    assert(!AW_MapMarkDelete(7) && AW_MapMark(3)==NULL);
    /* the hot marker: set, moved, off; never in the list */
    AW_MapHotSet(10,20);AW_MapHotSet(30,-40);assert(AW_MapHotGet(&x,&y) && x==30 && y==-40 && AW_MapMarksCount()==3);
    /* the saved block, read back as the pending load; nothing changes until it is taken */
    n=AW_MapMarksEncode(NULL,0);assert(n>8 && AW_MapMarksEncode(block,n-1)==-1 && AW_MapMarksEncode(block,sizeof block)==n);
    assert(!memcmp(block,"AWMK",4) && block[4]==1 && block[6]==3 && block[7]==1);
    assert(AW_MapMarksDecode(block,n,0) && !AW_MapMarksDecode(block,n-1,0) && !AW_MapMarksDecode(block,n+1,0));
    block[0]='X';assert(!AW_MapMarksDecode(block,n,0));block[0]='A';
    assert(AW_MapMarksDecode(block,n,1));
    AW_MapMarksClear();AW_MapHotOff();assert(AW_MapMarksCount()==0);
    AW_MapMarksLoaded();
    assert(AW_MapMarksCount()==3 && AW_MapMark(0)->x==-9104 && AW_MapMark(0)->y==-72480 && !strcmp(AW_MapMark(1)->name,"Bitter Coast Region"));
    assert(AW_MapHotGet(&x,&y) && x==30 && y==-40);
    AW_MapMarksLoaded();assert(AW_MapMarksCount()==3);   /* no pending load: unchanged */
    /* a save without the block: the pending load is empty */
    assert(AW_MapMarksDecode(NULL,0,1));AW_MapMarksLoaded();assert(AW_MapMarksCount()==0 && !AW_MapHotGet(NULL,NULL));
    /* the allowance: lowering it keeps the markers, stops new ones; 256 full is about 10 KB */
    AW_MapMarksSetMax(2);assert(AW_MapMarkAdd(1,1,"a")==0 && AW_MapMarkAdd(2,2,"b")==1 && AW_MapMarkAdd(3,3,"c")==-1);
    AW_MapMarksSetMax(1);assert(AW_MapMarksCount()==2 && AW_MapMarkAdd(4,4,"d")==-1);
    AW_MapMarksSetMax(0);assert(AW_MapMarksMax()==1);AW_MapMarksSetMax(9999);assert(AW_MapMarksMax()==AW_MAPMARKS_MAX);
    AW_MapMarksSetMax(AW_MAPMARKS_DEFAULT);AW_MapMarksClear();
    for(i=0;i<AW_MAPMARKS_DEFAULT;i++)assert(AW_MapMarkAdd((float)i,(float)-i,"0123456789012345678901234567890123")==i);
    assert(AW_MapMarkAdd(0,0,"one too many")==-1);
    AW_MapHotSet(1,2);n=AW_MapMarksEncode(block,sizeof block);
    assert(n==8+8+AW_MAPMARKS_DEFAULT*(9+AW_MAPMARK_NAME) && n<=10*1024+512);
    assert(AW_MapMarksDecode(block,n,1));AW_MapMarksLoaded();assert(AW_MapMarksCount()==AW_MAPMARKS_DEFAULT && AW_MapMark(255)->y==-255);
    /* SAVE-STATE-FIXED-CAPS-66: the allowance can go past the default up to the guard, and a save with more markers than
     * the allowance still loads them all (the allowance stops new ones only) */
    AW_MapMarksSetMax(AW_MAPMARKS_MAX);assert(AW_MapMarkAdd(9,9,"past the default")==AW_MAPMARKS_DEFAULT && AW_MapMarksCount()==AW_MAPMARKS_DEFAULT+1);
    n=AW_MapMarksEncode(block,sizeof block);assert(n>0);
    AW_MapMarksSetMax(AW_MAPMARKS_DEFAULT);assert(AW_MapMarksDecode(block,n,1));AW_MapMarksLoaded();
    assert(AW_MapMarksCount()==AW_MAPMARKS_DEFAULT+1 && AW_MapMarkAdd(1,1,"none")==-1);
    AW_MapMarkDelete(AW_MAPMARKS_DEFAULT);assert(AW_MapMarksCount()==AW_MAPMARKS_DEFAULT);
    /* New Game: nothing left, nothing pending */
    assert(AW_MapMarksDecode(block,n,1));AW_MapMarksReset();AW_MapMarksLoaded();
    assert(AW_MapMarksCount()==0 && !AW_MapHotGet(NULL,NULL));
    printf("map markers: ok\n");
    return 0;
}
