/* SPDX-License-Identifier: GPL-2.0-or-later
 * The journal book's quest pages (engine/aga/src/aw_questbook.c, JOURNAL-BOOK-32-QUESTS-59): every quest with a kept
 * stage on the world change list is listed (no 32-quest ceiling), each name once and sorted, the finished ones only in
 * "Show all"; unnamed quests are not listed; the dated entries read first, then each kept stage without one. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "aw_questbook.h"

static int finished_at_100(const char *id,int32_t stage,void *ctx){(void)ctx;(void)id;return stage>=100;}

/* JOURNAL-ORIGINAL-VIEW-59: the dated journal. A wrap of 10 characters a line (the game's is aw_ui.c AW_UILine). */
static const char *wrap10(const char *p,int width,char *out,int capacity){
    int n=0;(void)width;
    while(*p && *p!='\n' && n<10 && n<capacity-1)out[n++]=*p++;
    out[n]=0;if(*p=='\n')p++;
    return p;
}
static int page_has(const aw_journalview_t *v,int page,const char *s){
    int i,last=page+1<v->pages?v->page[page+1]:v->lines;
    for(i=v->page[page];i<last;i++)
        if(!v->line[i].blank && (int)strlen(s)==v->line[i].len && !memcmp(v->text+v->line[i].start,s,strlen(s)))return 1;
    return 0;
}
static void dated_journal_test(void){
    aw_journalview_t v;char d[64];int i,headings=0,on;
    /* the original's form: day of month, month name, "(Day N)" counted from 1; 0 = 16 Last Seed */
    assert(AW_JournalDate(0,d,sizeof(d)) && !strcmp(d,"16 Last Seed (Day 1)"));
    assert(AW_JournalDate(16,d,sizeof(d)) && !strcmp(d,"1 Heartfire (Day 17)"));
    assert(AW_JournalDate(138,d,sizeof(d)) && !strcmp(d,"1 Morning Star (Day 139)"));   /* the year turns */
    assert(AW_JournalDate(137,d,sizeof(d)) && !strcmp(d,"31 Evening Star (Day 138)"));
    assert(!AW_JournalDate(0,d,8) && !d[0]);
    memset(&v,0,sizeof(v));
    /* empty: no pages, opens at page 0 */
    assert(AW_JournalViewLayout(&v,wrap10,60,11) && !v.pages && !v.lines && AW_JournalViewNewest(&v)==0);
    /* 300 entries (no 32 limit), three a day, an undated one first */
    assert(AW_JournalViewAdd(&v,-1,"undated"));
    for(i=0;i<300;i++){char t[32];sprintf(t,"entry %03d",i);assert(AW_JournalViewAdd(&v,i/3,t));}
    assert(v.entries==301);
    assert(AW_JournalViewLayout(&v,wrap10,60,11));
    for(i=0;i<v.paras;i++)headings+=v.para_kind[i]==1;
    assert(headings==100);   /* one heading a day, not one an entry */
    assert(v.pages>20);
    /* the pages: never a blank line at the top, never a heading at the bottom, at most 11 lines */
    for(i=0;i<v.pages;i++){
        int last=i+1<v.pages?v.page[i+1]:v.lines;
        assert(!v.line[v.page[i]].blank);
        while(last>v.page[i] && v.line[last-1].blank)last--;   /* a blank skipped before the next page */
        on=last-v.page[i];
        assert(on>=1 && on<=11 && !v.line[last-1].heading);
    }
    /* oldest first: the undated entry on page 0, then day 1; the newest spread holds the last entry */
    assert(page_has(&v,0,"undated") && page_has(&v,0,"16 Last Se"));
    assert(AW_JournalViewNewest(&v)%2==0 && AW_JournalViewNewest(&v)+2>=v.pages);
    assert(page_has(&v,v.pages-1,"entry 299"));
    /* a long entry wraps over lines (and pages) */
    AW_JournalViewFree(&v);assert(!v.text && !v.pages);
    assert(AW_JournalViewAdd(&v,5,"aaaaaaaaaabbbbbbbbbbccccccccccdddddddddd"));
    /* "21 Last Seed (Day 6)" wraps to two lines, the text to four; three lines a page */
    assert(AW_JournalViewLayout(&v,wrap10,60,3) && v.lines==6 && v.pages==2);
    AW_JournalViewFree(&v);
}
int main(void){
    static aw_qb_quest_t q[80];
    aw_questbook_t b;aw_ledger_t l;aw_qb_dated_t dated[2];int shown[80],n,i;
    memset(&b,0,sizeof(b));memset(&l,0,sizeof(l));
    for(i=0;i<80;i++){
        snprintf(q[i].id,sizeof(q[i].id),"q%02d_quest",i);
        snprintf(q[i].title,sizeof(q[i].title),"Title %02d",79-i);   /* names sort the other way round */
    }
    q[5].title[0]=0;                                       /* no name: not listed */
    strcpy(q[7].title,"title 08");                         /* q06 and q07 share one name, in any case (and q71's */
    strcpy(q[6].title,"TITLE 08");                         /* "Title 08" is not started: only 70 are) */
    /* 70 quests started: far past the old 32 slots */
    for(i=0;i<70;i++)assert(AW_LedgerValueSet(&l,AW_LEDGER_QUESTS,AW_LedgerNameHash(q[i].id),i==3?100:10));
    assert(AW_QuestBookStage(&l,"Q01_Quest")==10 && AW_QuestBookStage(&l,"q75_quest")==0);
    /* two dated entries: q01 at its kept stage, and an older save's q72 (not on the list) at stage 5 */
    dated[0].id="q01_quest";dated[0].stage=10;dated[0].days=3;dated[0].milliseconds=7;
    dated[1].id="Q72_QUEST";dated[1].stage=5;dated[1].days=4;dated[1].milliseconds=0;
    assert(AW_QuestBookBuild(&b,q,80,&l,dated,2,finished_at_100,NULL));
    assert(b.started==71);
    /* 71 started, q05 unnamed, q06 and q07 one name: 69 names */
    assert(b.groups==69);
    for(i=1;i<b.groups;i++){
        const char *a=q[b.group[i-1].quest].title,*c=q[b.group[i].quest].title;
        int k=0;while(a[k] && (a[k]|32)==(c[k]|32))k++;
        assert((a[k]|32)<(c[k]|32));                       /* sorted by name, case-blind */
    }
    /* the finished one (q03 at 100) only in "show all" */
    n=AW_QuestBookShown(&b,0,shown,80);assert(n==68);
    for(i=0;i<n;i++)assert(b.group[shown[i]].quest!=3);
    assert(AW_QuestBookShown(&b,1,shown,80)==69);
    /* entries: the two dated first, in order, then 69 kept stages without a dated entry (q01's is dated) */
    assert(b.entries==2+69);
    assert(b.entry[0].dated==0 && b.entry[0].quest==1 && b.entry[0].days==3);
    assert(b.entry[1].dated==1 && b.entry[1].quest==72 && b.entry[1].stage==5);
    for(i=2;i<b.entries;i++)assert(b.entry[i].dated==AW_QB_UNDATED && b.entry[i].quest!=1 && b.entry[i].stage>0);
    /* every named entry knows its name's row; q05's has none */
    for(i=0;i<b.entries;i++){
        if(b.entry[i].quest==5)assert(b.entry[i].group<0);
        else assert(b.entry[i].group>=0 && b.group[b.entry[i].group].quest>=0);
    }
    {int g6=-1,g7=-1;for(i=0;i<b.entries;i++){if(b.entry[i].quest==6)g6=b.entry[i].group;if(b.entry[i].quest==7)g7=b.entry[i].group;}
     assert(g6>=0 && g6==g7);}
    /* nothing kept, nothing dated: an empty book; no list at all is the same */
    assert(AW_QuestBookBuild(&b,q,80,NULL,NULL,0,NULL,NULL) && !b.groups && !b.entries && !b.started);
    /* bad arguments */
    assert(!AW_QuestBookBuild(&b,NULL,3,&l,NULL,0,NULL,NULL));
    AW_QuestBookFree(&b);AW_LedgerClear(&l);
    dated_journal_test();
    puts("aga_questbook_test ok");
    return 0;
}
