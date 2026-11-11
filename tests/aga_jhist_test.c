/* SPDX-License-Identifier: GPL-2.0-or-later
 * The dated journal history on the world change list (engine/aga/src/aw_jhist.c, JOURNAL-ORIGINAL-VIEW-59,
 * AW-STATE-32-SLOTS-48): entries past 32 quests and 256 entries kept in order, never twice; its saved form both ways
 * and refused when damaged; the save's feature 128 written only when the history has an entry and read back only
 * into a good save; an older save's 32-slot history taken over. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_jhist.h"
#include "aw_ledger.h"
#include "aw_save.h"
#include "aw_questbook.h"
aw_race_t aw_races[16];aw_class_t aw_classes[32];aw_birth_t aw_births[16];aw_part_t aw_parts[384];
int aw_race_count=1,aw_class_count=1,aw_birth_count=1,aw_part_count=2;

static void saved_fixture(aw_save_t *saved){
    memset(saved,0,sizeof(*saved));saved->sequence=1;saved->profile=1;strcpy(saved->scene,"seyda");
    strcpy(saved->story.name,"Synthetic");saved->story.stage=AW_STAGE_RELEASED;saved->story.ship_disabled=1;saved->story.captain=-1;
    saved->character.level=1;saved->character.hair=1;
    strcpy(aw_races[0].id,"race");strcpy(aw_classes[0].id,"class");strcpy(aw_births[0].id,"birth");
    strcpy(aw_parts[0].id,"head");strcpy(aw_parts[1].id,"hair");aw_parts[1].kind=1;
    assert(AW_StateSet(&saved->state,AW_GLOBAL,"chargenstate",-1));
}
/* JOURNAL-LOWER-INDEX-ENTRY-64: the journal table's marks of the quest (10 start, 100 success, 60 the failure outcome
 * with a lower index, finished; 70 a restart) */
static int marks(const char *id,int32_t stage,void *ctx){(void)id;(void)ctx;return stage==100 || stage==60?AW_QB_FINISHED:stage==70?AW_QB_RESTART:0;}
static int replayed_finished(const aw_jhist_t *h,int32_t kept){
    static aw_qb_quest_t q[1];aw_qb_dated_t d[8];aw_questbook_t b;aw_ledger_t l;int i,fin;
    memset(&b,0,sizeof(b));memset(&l,0,sizeof(l));strcpy(q[0].id,"lower_quest");strcpy(q[0].title,"Lower");
    assert(h->count<=8);
    for(i=0;i<h->count;i++){d[i].id="lower_quest";d[i].stage=h->entry[i].stage;d[i].days=h->entry[i].days;d[i].milliseconds=0;}
    assert(AW_LedgerValueSet(&l,AW_LEDGER_QUESTS,AW_LedgerNameHash("lower_quest"),kept));
    assert(AW_QuestBookBuild(&b,q,1,&l,d,h->count,marks,NULL));
    fin=b.finished;AW_QuestBookFree(&b);AW_LedgerClear(&l);
    return fin;
}
static void lower_index_test(void){
    static aw_jhist_t h;uint32_t q=AW_LedgerNameHash("lower_quest");int32_t kept=0;int r,notices=0;
    memset(&h,0,sizeof(h));
#define JOURNAL(i,exists) do{r=AW_JHistJournal(&h,q,kept,(i),(exists),1,0);if(r&AW_JH_RAISE)kept=(i);if(r&AW_JH_NOTICE)notices++;}while(0)
    JOURNAL(10,1);assert(kept==10 && notices==1 && h.count==1);
    JOURNAL(100,1);assert(kept==100 && notices==2 && h.count==2 && replayed_finished(&h,kept));
    /* a restart at a lower index: dated, the kept index stays 100, the box once; the quest is active again */
    JOURNAL(70,1);assert(kept==100 && notices==3 && h.count==3 && !replayed_finished(&h,kept));
    /* the lower-index failure outcome after it: added, its mark applied, the box owed once */
    JOURNAL(60,1);assert(kept==100 && notices==4 && h.count==4 && replayed_finished(&h,kept));
    /* the same Journal again: nothing */
    JOURNAL(60,1);assert(kept==100 && notices==4 && h.count==4);
    /* an index at or below without an entry in the table: nothing */
    JOURNAL(55,0);assert(kept==100 && notices==4 && h.count==4);
    /* a higher index: the kept index rises, with the box; the last mark (60, finished) still holds */
    JOURNAL(120,1);assert(kept==120 && notices==5 && replayed_finished(&h,kept));
#undef JOURNAL
    AW_JHistClear(&h);
}
int main(void){
    static aw_jhist_t h,back;static aw_save_t saved,loaded;static unsigned char bytes[AW_SAVE_BYTES+65536],form[2048];
    static aw_changes_t changes;static aw_state_t old;
    int i,n,plain;char id[32];
    /* 100 quests, 3 stages each over the days: 300 entries, far past 32 quests and 256 entries */
    for(i=0;i<300;i++){
        sprintf(id,"quest_%03d",i/3);
        assert(AW_JHistAdd(&h,AW_LedgerNameHash(id),10*(i%3+1),i/7,1000*i)==2);
    }
    assert(h.count==300 && AW_JHistHasQuest(&h,AW_LedgerNameHash("QUEST_099")) && !AW_JHistHasQuest(&h,AW_LedgerNameHash("quest_100")));
    /* never twice; bad values refused */
    assert(AW_JHistAdd(&h,AW_LedgerNameHash("quest_005"),20,99,0)==1 && h.count==300);
    assert(!AW_JHistAdd(&h,0,1,0,0) && !AW_JHistAdd(&h,5,0,0,0) && !AW_JHistAdd(&h,5,1,-1,0) && !AW_JHistAdd(&h,5,1,0,86400000));
    assert(h.count==300 && h.entry[299].days==299/7 && h.entry[0].stage==10);
    /* the saved form both ways */
    n=AW_JHistEncode(&h,NULL,0);assert(n==8+300*AW_JHIST_ENTRY_BYTES);
    {static unsigned char big[8+300*16];assert(AW_JHistEncode(&h,big,n)==n);
     assert(AW_JHistDecode(big,n,NULL) && AW_JHistDecode(big,n,&back) && back.count==300);
     assert(!memcmp(back.entry,h.entry,300*sizeof(aw_jhist_entry_t)));
     /* damaged: a short form, a twice entry, a bad tag: refused, the target left empty */
     assert(!AW_JHistDecode(big,n-1,&back) && !back.count);
     memcpy(big+8+16,big+8,16);assert(!AW_JHistDecode(big,n,NULL));
     big[0]='X';assert(!AW_JHistDecode(big,n,NULL));}
    { aw_jhist_t empty;memset(&empty,0,sizeof(empty));assert(!AW_JHistEncode(&empty,NULL,0) && !AW_JHistEncode(&h,form,16)); }
    /* the save: feature 128 only with an entry; without the codec's functions nothing is written */
    saved_fixture(&saved);
    plain=AW_SaveEncode(bytes,AW_SAVE_BYTES,&saved);assert(plain>0);
    memset(&changes,0,sizeof(changes));changes.journal=&h;
    assert(AW_SaveEncodeChanges(bytes,sizeof(bytes),&saved,&changes)==plain);    /* not linked: not written */
    aw_save_journal_encode=AW_JHistEncode;aw_save_journal_decode=AW_JHistDecode;
    n=AW_SaveEncodeChanges(bytes,sizeof(bytes),&saved,&changes);assert(n==plain+4+8+300*16);
    assert(AW_SaveDecode(bytes,n,&loaded));                                       /* checked, not kept */
    memset(&changes,0,sizeof(changes));changes.journal=&back;
    assert(AW_SaveDecodeChanges(bytes,n,&loaded,&changes) && back.count==300 && !memcmp(back.entry,h.entry,300*sizeof(aw_jhist_entry_t)));
    /* a save without the history empties the target (an older save: taken over on load instead) */
    assert(AW_SaveEncode(bytes,AW_SAVE_BYTES,&saved)==plain && AW_SaveDecodeChanges(bytes,plain,&loaded,&changes) && !back.count);
    /* an older save's 32-slot history taken over in its order, by the quests' ids */
    memset(&old,0,sizeof(old));
    assert(AW_JournalAdd(&old,"A1_1_FindSpymaster",1) && AW_JournalAdd(&old,"MS_FargothRing",10) && AW_JournalAdd(&old,"A1_1_FindSpymaster",10));
    assert(AW_JHistTakeOver(&back,&old)==3 && back.count==3);
    assert(back.entry[0].quest==AW_LedgerNameHash("a1_1_findspymaster") && back.entry[1].quest==AW_LedgerNameHash("ms_fargothring") && back.entry[2].stage==10);
    assert(!AW_JHistTakeOver(&back,&old) && back.count==3);                       /* never twice */
    AW_JHistMove(&h,&back);assert(h.count==3 && !back.count && !back.entry);
    AW_JHistClear(&h);AW_JHistClear(&back);
    lower_index_test();
    puts("aga_jhist_test ok");
    return 0;
}
