/* SPDX-License-Identifier: GPL-2.0-or-later
 * The dialogue table (AWDL1, id1/dialogue.lut, tools/dialogue_lut.py; docs/DIALOGUE_DESIGN.md): every NPC record's
 * conversation topics with their answers in the original's order, the run-time conditions as the voice table's
 * 8-byte condition records (evaluated by aw_glut.c AW_GlutCond, the evaluator greetings and voice lines use), the
 * answers' result scripts and hyperlinks, and every quest's journal entries.
 * Only the index stays in memory for the session (the topic rows, the NPC row offsets and the fixture, about 25 KB on
 * Morrowind.esm); a conversation reads its NPC's row and candidates into a buffer the caller gives and frees it when
 * it ends. The NPC rows are the voice table's (the same order; the builder checks it), so an edict's row comes from
 * AW_GlutNpcOf.
 */
#ifndef AW_DIAL_H
#define AW_DIAL_H
#include "aw_glut.h"

#define AW_DIAL_VERSION 1
#define AW_DIAL_HEADER 96
#define AW_DIAL_TOPIC_ROW 8        /* u32 name offset (topic strings), u8 name length, u8 kind, u16 0 */
#define AW_DIAL_ENTRY_ROW 20       /* u32 text, u32 first condition, u32 script, u32 first link, u16 links, u8 conditions, u8 flags */
#define AW_DIAL_LIST_ROW 8         /* u32 first item, u16 items, u16 0 */
#define AW_DIAL_QUEST_ROW 12       /* u32 quest id (topic strings), u32 first journal entry, u16 entries, u16 0 */
#define AW_DIAL_JOURNAL_ROW 8      /* u16 index, u8 flags, u8 0, u32 text */
#define AW_DIAL_ENTRY_LAST 1       /* no run-time condition: nothing after it can be said */
#define AW_DIAL_KIND_TOPIC 0
#define AW_DIAL_KIND_PERSUASION 3
#define AW_DIAL_MAX_TOPICS 512     /* one NPC's topics (Morrowind.esm: at most 258) */
#define AW_DIAL_MAX_MERGE 64       /* lists merged per topic and NPC */
#define AW_DIAL_NONE32 0xFFFFFFFFul
#define AW_DIAL_BUFFER 81920       /* one open conversation (tools/dialogue_lut.py BUFFER_BUDGET; Morrowind.esm: 53.6 KB at most) */

typedef struct {
    const unsigned char *data;     /* the resident part: header, topic rows, NPC row offsets, fixture */
    long size, file_size;
    long topics, npcs, functions;
    long row_bytes, listsets, listset_items, lists, list_items, entries, conds, globals, names, links, quests,
        journal, string_bytes, tstring_bytes, script_bytes, text_bytes;
    int info_refusal;              /* the topic "Info Refusal", -1 none */
    /* file offsets of the sections after the resident part */
    long at_conversation, conversation_bytes, at_rows, at_listsets, at_listset_items, at_lists, at_list_items,
        at_entries, at_conds, at_links, at_quests, at_journal, at_ranks, at_tstrings, at_scripts, at_texts;
    const unsigned char *topic, *npc_offset, *fixture, *known, *start;
    int starts;                    /* the topics a new character knows (the census captain's AddTopic) */
    const unsigned char *settings, *faction, *reaction;   /* the game settings, faction ids, faction reactions */
    int factions, reactions;
} aw_dial_t;

/* The game settings of the disposition (tools/dialogue_lut.py SETTINGS, same order). */
enum {AW_DIAL_SET_RACE, AW_DIAL_SET_PERSONALITY_MULT, AW_DIAL_SET_PERSONALITY_BASE, AW_DIAL_SET_FACTION_RANK_MULT,
      AW_DIAL_SET_FACTION_RANK_BASE, AW_DIAL_SET_FACTION_MOD, AW_DIAL_SET_CRIME, AW_DIAL_SET_DISEASE,
      AW_DIAL_SET_WEAPON_DRAWN, AW_DIAL_SETTINGS};
#define AW_DIAL_FACTION_ID 32
#define AW_DIAL_RANKS 10           /* a faction's rank names on disk, AW_DIAL_FACTION_ID bytes each */
/* The file offset of faction FACTION's rank RANK name (0..9), -1 when the table has no such faction. */
long AW_DialRankAt(const aw_dial_t *d,const char *faction,int rank);
/* The rank defines (OpenMW's rule, our own code): %PCRank is the player's rank name in the speaker's faction (rank 0
 * when not a member), %NextPCRank the one after it (at most the tenth), "%" when the speaker has no faction; %Cell
 * the player's cell. Replaces them (any case) in SOURCE, the other defines kept for AW_GlutExpand. */
void AW_DialFillDefines(const char *source,char *out,int capacity,const char *pc_rank,const char *next_rank,
                        const char *cell);
/* What the disposition reads of the game (the engine fills it; the rule: OpenMW's
 * MechanicsManager::getDerivedDisposition, our own code). */
typedef struct {
    int base;                      /* the NPC's own disposition (its record, with the scripts' changes) */
    int same_race;                 /* the player is of the NPC's race */
    float personality;             /* the player's Personality */
    int bounty;                    /* the player's crime level */
    int diseased, weapon_drawn;
    const char *faction;           /* the NPC's faction id (folded), NULL none */
    /* the player's rank in a faction (-1 not a member) and whether expelled */
    int (*rank)(const char *faction,int *expelled);
} aw_dial_facts_t;
/* The NPC's disposition toward the player, clamped to 0..100 when CLAMP. */
int AW_DialDisposition(const aw_dial_t *d,const aw_dial_facts_t *f,int clamp);
float AW_DialSetting(const aw_dial_t *d,int setting);

/* Reads BYTES at a file OFFSET into OUT: 1 done, 0 failed (the engine: the open file; the host test: memory). */
typedef int (*aw_dial_read_t)(void *user,long offset,void *out,long bytes);

typedef struct {
    unsigned long entry;           /* the file's entry index (the same INFO as some NPCs see it) */
    unsigned long text, script, link;   /* offsets in the text and script blocks, first link; AW_DIAL_NONE32 none */
    unsigned short links;
    unsigned char conditions, flags;
    const unsigned char *cond;     /* its condition records, in the conversation buffer */
} aw_dial_answer_t;

typedef struct {
    const aw_dial_t *d;
    int npc, topics;
    struct {unsigned short topic, first, count;} topic[AW_DIAL_MAX_TOPICS];
    aw_dial_answer_t *answer;      /* every candidate of every topic, in the buffer */
    long answers;
    aw_glut_cond_t cond;           /* the evaluator's context: the table's globals and names, the speaker */
} aw_dial_conv_t;

/* Pure parts (host-tested, tests/aga_dial_test.c): */
/* The resident size an AWDL1 header asks for, or -1. */
long AW_DialResidentSize(const unsigned char *header,long file_size);
/* Index the resident part: 1 = usable (every section's size checked against the file's). */
int AW_DialOpen(aw_dial_t *d,const unsigned char *data,long size,long file_size);
/* The I-th topic a new character knows, -1 past them. */
int AW_DialStartTopic(const aw_dial_t *d,int i);
/* The known-topic set (one bit per topic, AW_DialKnownBytes bytes, the caller's): seed with the start topics;
 * mark a topic; test one. */
#define AW_DialKnownBytes(d) (((d)->topics+7)/8)
void AW_DialKnownStart(const aw_dial_t *d,unsigned char *known);
void AW_DialKnow(const aw_dial_t *d,unsigned char *known,int topic);
int AW_DialKnows(const aw_dial_t *d,const unsigned char *known,int topic);
/* The topic list of an open conversation (OpenMW getAvailableTopics: known AND this actor has an answer, a refusal
 * counting; Topic kind only), in the table's order (by name): the count, topic numbers into OUT (at most MAX). */
int AW_DialTopicList(const aw_dial_conv_t *c,const unsigned char *known,const aw_glut_state_t *s,int *out,int max);
/* A topic's kind (AW_DIAL_KIND_*) and its name's place in the file (for the window's list), -1 for a bad topic. */
int AW_DialTopicKind(const aw_dial_t *d,int topic);
long AW_DialTopicName(const aw_dial_t *d,int topic,int *length);
/* Open a conversation with NPC row NPC: read its row, the globals and names, and every candidate of every topic it
 * has into BUFFER (BYTES); SPEAKER: the voice table's context of the same row (rank, disposition, home cell; this
 * table's globals and names replace the voice table's). 1 done, 0 when the buffer is short or a read fails. */
int AW_DialConverse(aw_dial_conv_t *c,const aw_dial_t *d,int npc,const aw_glut_cond_t *speaker,
                    aw_dial_read_t read,void *user,unsigned char *buffer,long bytes);
/* The NPC's place of a topic, -1 when it has none. */
int AW_DialFind(const aw_dial_conv_t *c,int topic);
/* The answer to a topic (OpenMW Filter::search): its candidates in order, the first whose conditions all hold; when
 * none holds but one failed only on its disposition test, *refused = 1 (the answer then comes from Info Refusal).
 * The index into c->answer, or -1. */
int AW_DialPick(const aw_dial_conv_t *c,int topic,const aw_glut_state_t *s,int *refused);
/* The topic's answer with the refusal rule applied (Info Refusal's answer when only disposition failed), -1 none. */
int AW_DialAnswer(const aw_dial_conv_t *c,int topic,const aw_glut_state_t *s);
/* File offsets of an answer's text and result script, -1 when it has none. */
long AW_DialTextAt(const aw_dial_conv_t *c,int answer);
long AW_DialScriptAt(const aw_dial_conv_t *c,int answer);
/* An answer's links (topics its text names), read with READ; the count, at most MAX. */
int AW_DialLinks(const aw_dial_conv_t *c,int answer,aw_dial_read_t read,void *user,unsigned short *out,int max);
/* The next line of *TEXT wrapped at COLS characters (at the last space that fits, else cut; a line end ends a line):
 * 1 and the line in OUT (CAPACITY > COLS), *TEXT moved past it; 0 at the end. */
int AW_DialWrapNext(const char **text,int cols,char *out,int capacity);

/* The dialogue window (aw_dialwin.c, engine only): opened by Talk (pr_cmds.c PF_aw_converse) with the greeting
 * already chosen; 1 when it opened (the NPC has a dialogue row; otherwise the greeting stays a subtitle). */
struct edict_s;
void AW_DialWindowInit(void);
int AW_DialWindowOpen(struct edict_s *e,const char *greeting,int talked);
/* dbg npcs talk [ID]: Talk with the nearest NPC that can be talked to (or record ID), the player turned to it. */
void AW_DialWindowTalk(const char *id);
/* aw_mwhost.c: a speaker's disposition facts from the actor record, the character and the player's standing */
void AW_MwscriptDispositionFacts(const char *record,unsigned long reference,int base,const char *faction,
                                 aw_dial_facts_t *f);
int AW_DialWindowActive(void);
#endif
