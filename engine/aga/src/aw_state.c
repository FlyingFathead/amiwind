/* SPDX-License-Identifier: GPL-2.0-or-later
 * Persistent game facts: numeric globals/journal indices and inventory counts.
 * UI stage order is not a quest model. Conditions query these independent facts;
 * SetJournalIndex may move either way, while Journal only advances its index. */
#include <string.h>
#include "aw_state.h"
aw_state_t aw_state;
static int key(char out[64],const char *id)
{
    unsigned char c;int n=0;
    while((c=(unsigned char)*id++)!=0){
        if(n>=63 || c<32)return 0;
        out[n++]=c>='A' && c<='Z'?c+32:c;
    }
    out[n]=0;return n>0;
}
void AW_StateReset(void){memset(&aw_state,0,sizeof(aw_state));}
int32_t AW_StateGet(const aw_state_t *state,int kind,const char *id)
{
    char name[64];int i;
    if(kind<0 || kind>2 || !key(name,id))return 0;
    for(i=0;i<state->count[kind];i++)if(!strcmp(state->values[kind][i].id,name))return state->values[kind][i].value;
    return 0;
}
int AW_StateSet(aw_state_t *state,int kind,const char *id,int32_t value)
{
    char name[64];int i;
    if(kind<0 || kind>2 || !key(name,id) || (kind==AW_ITEM && value<0))return 0;
    for(i=0;i<state->count[kind];i++)if(!strcmp(state->values[kind][i].id,name))break;
    if(i==state->count[kind]){
        if(i==AW_STATE_VALUES)return 0;
        memset(&state->values[kind][i],0,sizeof(aw_value_t));strcpy(state->values[kind][i].id,name);state->count[kind]++;
    }
    state->values[kind][i].value=value;return 1;
}
int AW_StateTest(const aw_state_t *state,int kind,const char *id,int comparison,int32_t value)
{
    int32_t actual=AW_StateGet(state,kind,id);
    switch(comparison){
        case AW_EQ:return actual==value;case AW_NE:return actual!=value;
        case AW_GT:return actual>value;case AW_GE:return actual>=value;
        case AW_LT:return actual<value;case AW_LE:return actual<=value;
    }
    return 0;
}
int AW_JournalAdd(aw_state_t *state,const char *id,int32_t index)
{
    char name[64];int i,quest,known=0;int32_t days,ms;aw_journal_entry_t *entry;
    if(!key(name,id))return 0;
    if(index<=AW_StateGet(state,AW_JOURNAL,id))return 1;
    for(quest=0;quest<state->count[AW_JOURNAL];quest++)
        if(!strcmp(state->values[AW_JOURNAL][quest].id,name))break;
    for(i=0;i<state->journal_count;i++)
        if(state->journal[i].quest==quest && state->journal[i].stage==index)known=1;
    /* Never advance a quest while silently dropping its new history entry. */
    if(!known && state->journal_count>=AW_JOURNAL_ENTRIES)return 0;
    days=AW_StateGet(state,AW_GLOBAL,"amiwind:clock:days");
    ms=AW_StateGet(state,AW_GLOBAL,"amiwind:clock:ms");
    if(!AW_StateGet(state,AW_GLOBAL,"amiwind:clock:ready"))ms=32400000;
    if(days<0 || days>365000 || ms<0 || ms>=86400000)return 0;
    if(!AW_StateSet(state,AW_JOURNAL,id,index))return 0;
    if(!known){
        entry=&state->journal[state->journal_count++];
        entry->quest=quest;entry->stage=index;entry->days=days;entry->milliseconds=ms;
    }
    return 1;
}
int AW_ItemAdd(aw_state_t *state,const char *id,int32_t count)
{
    int32_t old=AW_StateGet(state,AW_ITEM,id);
    if(count>0 && old>INT32_MAX-count)return 0;
    if(count<0 && count < -old)return 0;
    return AW_StateSet(state,AW_ITEM,id,old+count);
}
int AW_CaptainDuties(void)
{
    aw_state_t next=aw_state;
    /* The original INFO branch tests journal == 0. Possessing/losing a package
     * is a different condition and must never reset reward eligibility. */
    if(!AW_StateTest(&next,AW_JOURNAL,"A1_1_FindSpymaster",AW_EQ,0))return 0;
    if(!AW_JournalAdd(&next,"A1_1_FindSpymaster",1) ||
       !AW_ItemAdd(&next,"bk_a1_1_directionscaiuscosades",1) ||
       !AW_ItemAdd(&next,"bk_a1_1_caiuspackage",1) || !AW_ItemAdd(&next,"gold_001",87))return 0;
    aw_state=next;return 1;
}

int AW_CourtyardRingAvailable(void)
{
    /* Runtime-owned placed-container fact, not a TES3 global or a quest stage.
     * Losing/returning the inventory item must not restock this container. */
    return !AW_StateGet(&aw_state,AW_GLOBAL,"amiwind:ref:172851:ring_taken");
}
int AW_CourtyardTakeRing(void)
{
    aw_state_t next=aw_state;
    if(!AW_CourtyardRingAvailable() ||
       !AW_ItemAdd(&next,"ring_keley",1) ||
       !AW_StateSet(&next,AW_GLOBAL,"amiwind:ref:172851:ring_taken",1))return 0;
    aw_state=next;return 1;
}
