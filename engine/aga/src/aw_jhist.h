/* SPDX-License-Identifier: GPL-2.0-or-later
 * The dated journal history on the world change list (JOURNAL-ORIGINAL-VIEW-59, AW-STATE-32-SLOTS-48): every journal
 * entry the player earned, in the order earned, with its game date: the quest's name hash (aw_ledger.h
 * AW_LedgerNameHash of its id), the stage, the days since the game's start and the milliseconds into that day. It
 * replaces the 256-entry, 32-quest history of aw_state.h as the book's source: no quest limit, and only what was
 * written is kept and saved. OpenMW 0.51 mwdialogue/journalimp.cpp (read, not copied) keeps the same: an entry per
 * (quest, stage) added, never twice, with its day. Saved as AWS4 feature 128 (aw_save.h), written only when the
 * history has an entry; an older save's 32-slot history is taken over on load (AW_JHistTakeOver).
 * Saved form: "AWH1", u32 count, then each entry: u32 quest, i32 stage, i32 days, i32 milliseconds (little-endian).
 * Pure C: no engine headers, so the native test compiles it as it is. */
#ifndef AW_JHIST_H
#define AW_JHIST_H
#include <stdint.h>
#include "aw_state.h"

#define AW_JHIST_MAX 8192         /* entries at most: above every journal entry the data has (2,489 in the GOTY
                                   * master; one entry per entry, never twice), so a bound for a damaged file only */
#define AW_JHIST_ENTRY_BYTES 16
typedef struct {uint32_t quest;int32_t stage,days,milliseconds;} aw_jhist_entry_t;
typedef struct aw_jhist_s {
    aw_jhist_entry_t *entry;int count,capacity;
    unsigned long refused;        /* entries refused for memory (the stage is still kept on the change list) */
} aw_jhist_t;
/* the session's history */
extern aw_jhist_t aw_jhist;
/* Adds (QUEST, STAGE) dated DAYS, MS: 2 added, 1 already there (never twice), 0 refused (a bad value, memory). */
int AW_JHistAdd(aw_jhist_t *h,uint32_t quest,int32_t stage,int32_t days,int32_t milliseconds);
/* JOURNAL-LOWER-INDEX-ENTRY-64: a Journal command for QUEST at INDEX, its kept index CURRENT (OpenMW 0.53
 * mwdialogue/journalimp.cpp Journal::addEntry and quest.cpp Quest::addEntry, read, not copied). INDEX above CURRENT:
 * the entry is dated (once) and the kept index rises, with the notice. INDEX at or below CURRENT: the kept index stays;
 * an entry not heard before (EXISTS: the journal table has a row for it) is dated, so the book applies its finished or
 * restart mark, with the notice; an entry already heard, or one without a row, does nothing. Returns AW_JH_RAISE
 * (the caller raises the kept index) and AW_JH_NOTICE ("Your journal has been updated."). SetJournalIndex does not
 * come here: it sets the index without an entry or a notice. */
#define AW_JH_RAISE 1
#define AW_JH_NOTICE 2
/* 1 when the journal table has quest ID's entry at INDEX (aw_worldui.c sets it at start; NULL: none known, so a
 * Journal at or below the kept index adds nothing) */
extern int (*aw_journal_entry_exists)(const char *id,int32_t index);
int AW_JHistJournal(aw_jhist_t *h,uint32_t quest,int32_t current,int32_t index,int exists,int32_t days,int32_t milliseconds);
/* 1 when QUEST has an entry (any stage). */
int AW_JHistHasQuest(const aw_jhist_t *h,uint32_t quest);
void AW_JHistClear(aw_jhist_t *h);
/* TO becomes FROM (TO freed first); FROM is left empty. */
void AW_JHistMove(aw_jhist_t *to,aw_jhist_t *from);
/* An older save's history (aw_state.h journal, its quests by id) appended to H in its order; the number taken. */
int AW_JHistTakeOver(aw_jhist_t *h,const aw_state_t *s);
/* The saved form into OUT (CAPACITY bytes); OUT NULL: the bytes it needs. 0 when empty or it does not fit. */
int AW_JHistEncode(const aw_jhist_t *h,unsigned char *out,int capacity);
/* Reads a saved form (all SIZE bytes) into INTO (emptied first; NULL: checked only). 1 good, 0 refused (INTO empty). */
int AW_JHistDecode(const unsigned char *data,int size,aw_jhist_t *into);
#endif
