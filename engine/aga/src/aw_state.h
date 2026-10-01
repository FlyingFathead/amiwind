/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_STATE_H
#define AW_STATE_H
#include <stdint.h>
#define AW_STATE_VALUES 32
#define AW_JOURNAL_ENTRIES 256
enum aw_value_kind { AW_GLOBAL, AW_JOURNAL, AW_ITEM };
enum aw_compare { AW_EQ, AW_NE, AW_GT, AW_GE, AW_LT, AW_LE };
typedef struct {char id[64];int32_t value;} aw_value_t;
typedef struct {int quest;int32_t stage,days,milliseconds;} aw_journal_entry_t;
typedef struct {
    int count[3];aw_value_t values[3][AW_STATE_VALUES];
    int journal_count;aw_journal_entry_t journal[AW_JOURNAL_ENTRIES];
} aw_state_t;
extern aw_state_t aw_state;
void AW_StateReset(void);
int32_t AW_StateGet(const aw_state_t *state,int kind,const char *id);
int AW_StateSet(aw_state_t *state,int kind,const char *id,int32_t value);
int AW_StateTest(const aw_state_t *state,int kind,const char *id,int comparison,int32_t value);
int AW_JournalAdd(aw_state_t *state,const char *id,int32_t index);
int AW_ItemAdd(aw_state_t *state,const char *id,int32_t count);
int AW_CaptainDuties(void);
int AW_CourtyardRingAvailable(void);
int AW_CourtyardTakeRing(void);
#define AW_Papers() AW_StateGet(&aw_state,AW_ITEM,"chargen statssheet")
#define AW_Ring() AW_StateGet(&aw_state,AW_ITEM,"ring_keley")
#define AW_Package() AW_StateGet(&aw_state,AW_ITEM,"bk_a1_1_caiuspackage")
#endif
