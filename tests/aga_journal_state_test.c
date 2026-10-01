/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "aw_state.h"
#include <assert.h>
#include <string.h>
int main(void)
{
    int i;aw_state_t before;
    AW_StateReset();
    assert(AW_JournalAdd(&aw_state,"Test_Quest",1));
    assert(aw_state.journal_count==1 && aw_state.journal[0].quest==0);
    assert(aw_state.journal[0].days==0 && aw_state.journal[0].milliseconds==32400000);
    assert(AW_JournalAdd(&aw_state,"TEST_QUEST",1) && aw_state.journal_count==1);
    assert(AW_StateSet(&aw_state,AW_GLOBAL,"amiwind:clock:ready",1));
    assert(AW_StateSet(&aw_state,AW_GLOBAL,"amiwind:clock:days",9));
    assert(AW_StateSet(&aw_state,AW_GLOBAL,"amiwind:clock:ms",12345));
    assert(AW_JournalAdd(&aw_state,"test_quest",5));
    assert(aw_state.journal[1].days==9 && aw_state.journal[1].milliseconds==12345);
    assert(AW_StateSet(&aw_state,AW_JOURNAL,"test_quest",0));
    assert(AW_JournalAdd(&aw_state,"test_quest",1) && aw_state.journal_count==2);
    assert(AW_StateGet(&aw_state,AW_JOURNAL,"test_quest")==1);
    for(i=6;aw_state.journal_count<AW_JOURNAL_ENTRIES;i++)assert(AW_JournalAdd(&aw_state,"test_quest",i));
    before=aw_state;assert(!AW_JournalAdd(&aw_state,"other",1));
    assert(!memcmp(&before,&aw_state,sizeof(before)));
    assert(AW_JournalAdd(&aw_state,"test_quest",1));
    AW_StateReset();
    for(i=0;i<AW_STATE_VALUES;i++){char id[64];id[0]='a'+i/26;id[1]='a'+i%26;id[2]=0;assert(AW_JournalAdd(&aw_state,id,1));}
    before=aw_state;assert(!AW_JournalAdd(&aw_state,"one-too-many",1));
    assert(!memcmp(&before,&aw_state,sizeof(before)));
    return 0;
}
