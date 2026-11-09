/* SPDX-License-Identifier: GPL-2.0-or-later
 * The journal book's quest pages (JOURNAL-BOOK-32-QUESTS-59, docs/WORLD_MAP_AND_JOURNAL.md "Quests"): which quests
 * the book lists and which entries it reads, built when the book opens from the quests' kept stages on the world
 * change list (aw_ledger.h QUESTS, by the name hash of the quest id: every quest, no 32-quest ceiling) and the dated
 * entries the game recorded (aw_state.h journal). Rules from OpenMW 0.51 mwgui/journalviewmodel.cpp (read, not
 * copied): the book lists quest NAMES, each name once (several quest ids can share one), sorted by name; a quest
 * without a name is not listed (its entries still read under "All entries"); a name is finished when any of its
 * quests is finished, and the default list shows the active ones only ("Show all" adds the finished). A quest is
 * finished when the entry of its kept stage finishes it (QSTF; mwdialogue/quest.cpp addEntry), as only the stage is
 * kept. Entries: the dated ones in the order recorded, then, for every started quest whose kept stage has no dated
 * entry (a quest past the old 32 slots, or a save's stages without their dates), that stage's entry, undated, in
 * the catalogue's order. Pure C: no engine headers, so the native test compiles it as it is. */
#ifndef AW_QUESTBOOK_H
#define AW_QUESTBOOK_H
#include <stdint.h>
#include "aw_ledger.h"

#define AW_QB_ID 64          /* a quest id with its NUL (world/quests.awq, world/journal.awj) */
#define AW_QB_TITLE 96       /* a quest name with its NUL (world/quests.awq) */
#define AW_QB_QUESTS 10000   /* catalogue rows at most (the files' own bound) */
#define AW_QB_UNDATED (-1)

/* A catalogue row: the quest's id (lower case) and its name ("" = none). */
typedef struct {char id[AW_QB_ID],title[AW_QB_TITLE];} aw_qb_quest_t;
/* A dated entry as the game recorded it: the quest's id, the stage, its date. */
typedef struct {const char *id;int32_t stage,days,milliseconds;} aw_qb_dated_t;
typedef struct {
    int quest;                   /* its catalogue row, -1 when the catalogue has none */
    int group;                   /* its name's row in the list, -1 when unnamed */
    int dated;                   /* the dated entry's index, AW_QB_UNDATED for a kept stage without a date */
    int32_t stage,days,milliseconds;
} aw_qb_entry_t;
typedef struct {
    int quest;                   /* the name's first quest (catalogue row) */
    int finished;                /* 1 when any quest of the name is finished */
} aw_qb_group_t;
typedef struct {
    aw_qb_group_t *group;int groups;      /* by name (case-blind), sorted */
    aw_qb_entry_t *entry;int entries;     /* in reading order */
    int started;                          /* quests with a stage */
} aw_questbook_t;
/* 1 when quest ID's entry at STAGE finishes it (the journal index's flags); CTX the caller's. NULL: none finishes. */
typedef int (*aw_qb_finished_fn)(const char *id,int32_t stage,void *ctx);

/* Builds B (emptied first) from the catalogue (QUESTS, N rows, any order), the kept stages L (NULL: none) and the dated
 * entries (DATED, ND). 1 built; 0 out of memory (B left empty). */
int AW_QuestBookBuild(aw_questbook_t *b,const aw_qb_quest_t *quests,int n,const aw_ledger_t *l,
                      const aw_qb_dated_t *dated,int nd,aw_qb_finished_fn finished,void *ctx);
void AW_QuestBookFree(aw_questbook_t *b);
/* The rows of the list shown: ALL 0 = the active names only, 1 = every name. Into OUT (up to MAX) the group rows in
 * order; returns their count. */
int AW_QuestBookShown(const aw_questbook_t *b,int all,int *out,int max);
/* The kept stage of quest ID (0: not started). */
int32_t AW_QuestBookStage(const aw_ledger_t *l,const char *id);

/* ---- The dated journal (JOURNAL-ORIGINAL-VIEW-59): the book's first view, as the original game's ----
 * Every entry in the order earned, each day under its date heading in the original form, "16 Last Seed (Day 1)":
 * the day of the month, the month's name (the game data's GMSTs sMonthMorningstar .. sMonthEveningstar, English
 * values) and sDay ("Day") with the days passed counted from 1 (OpenMW 0.51 mwgui/journalviewmodel.cpp, read, not
 * copied). DAYS is the game's day count since the start, 0 = 16 Last Seed 3E 427 (the calendar's day 227 of 365).
 * Laid out into lines and pages by the caller's wrap (aw_ui.c AW_UILine in the game), so the native test pages it
 * with its own. No entry or page limit: the text, lines and pages grow as needed. */
typedef const char *(*aw_jv_wrap_fn)(const char *text,int width,char *out,int capacity);
typedef struct {uint32_t start;uint16_t len;uint8_t heading,blank;} aw_jv_line_t;
typedef struct {
    char *text;uint32_t used,cap;          /* paragraphs, each ending with a NUL */
    uint32_t *para;uint8_t *para_kind;int paras,para_cap;   /* kind 0 text, 1 heading, 2 blank */
    aw_jv_line_t *line;int lines,line_cap;
    int *page;int pages;                   /* the first line of each page */
    int32_t last_day;int entries;
} aw_journalview_t;
/* The original's date heading of DAYS into OUT; the length, 0 when it does not fit. */
int AW_JournalDate(int32_t days,char *out,int capacity);
/* LORE-DATE-FORMAT-62: the one date layout of every window (OpenMW 0.51, read, not copied: mwgui/journalbooks.cpp,
 * waitdialog.cpp, savegamedialog.cpp; the hour on a 12-hour clock with a.m./p.m. as OpenMW's Calendar strings):
 *   JOURNAL  "18 Last Seed (Day 3)"            the journal's day heading
 *   REST     "18 Last Seed (Day 3) 9 a.m."     the rest and wait window
 *   SAVE     "18 Last Seed 9 a.m."             a saved game's line
 *   LORE     "18 Last Seed, 3E 427"            the date with the era year (dbg date)
 *   NUMERIC  "18/08/427"                       day/month/year (dbg date)
 * DAYS: days since the start (0 = 16 Last Seed 3E 427). The original shows no weekday anywhere, and its data has no
 * weekday names, so none is shown. Names: the game data's GMSTs through AW_DateNameSet (KEY sMonth... or sDay),
 * else their English values. Returns the length, 0 when it does not fit. */
#define AW_DATE_JOURNAL 0
#define AW_DATE_REST 1
#define AW_DATE_SAVE 2
#define AW_DATE_LORE 3
#define AW_DATE_NUMERIC 4
int AW_DateText(int form,int32_t days,int hour,int minute,char *out,int capacity);
int AW_DateNameSet(const char *key,const char *text);
const char *AW_DateMonthName(int month);
void AW_DateNamesEnsure(void);   /* the game's (aw_wait.c): the image's names, read once a session */
/* Adds one entry (DAYS < 0: a kept stage without a date, no heading) with its text; 1 added, 0 out of memory. */
int AW_JournalViewAdd(aw_journalview_t *v,int32_t days,const char *text);
/* Wraps every paragraph to WIDTH and pages the lines, PAGE_LINES a page: a page never starts with a blank line and a
 * heading never ends one. 1 laid out, 0 out of memory. */
int AW_JournalViewLayout(aw_journalview_t *v,aw_jv_wrap_fn wrap,int width,int page_lines);
/* The left page of the last spread (the book opens there), 0 when empty. */
int AW_JournalViewNewest(const aw_journalview_t *v);
void AW_JournalViewFree(aw_journalview_t *v);
#endif
