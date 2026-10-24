/* SPDX-License-Identifier: GPL-2.0-or-later
 * The NPC voice and greeting table (AWGL1, id1/npc-voices.lut, tools/greeting_lut.py; docs/NPC_VOICE_TABLE.md):
 * every NPC record's voice lines (Hello, Idle, Intruder, Thief, Hit, Attack, Flee, ...) and conversation greeting,
 * with the original's static filters decided at build time and the run-time ones as fixed 8-byte condition
 * records. Read once (the part before the texts stays in memory; a text is read when its line is said), looked up
 * by record id with a binary search (cached per edict), a topic walked as the merge of the NPC's few shared lists
 * in the original's order, first entry whose conditions hold (OpenMW Filter::search). No allocation after the load.
 */
#ifndef AW_GLUT_H
#define AW_GLUT_H

/* Topics the engine asks for (the file names its topics; the known ones are matched by name at load). */
enum {AW_GLUT_HELLO, AW_GLUT_IDLE, AW_GLUT_INTRUDER, AW_GLUT_THIEF, AW_GLUT_HIT, AW_GLUT_ATTACK, AW_GLUT_FLEE,
      AW_GLUT_GREETING, AW_GLUT_TOPICS};
/* Condition opcodes (tools/greeting_lut.py OP_*; the opcode table of docs/NPC_VOICE_TABLE.md). */
enum {AW_GLUT_OP_FUNC=1, AW_GLUT_OP_GLOBAL, AW_GLUT_OP_LOCAL, AW_GLUT_OP_NOTLOCAL, AW_GLUT_OP_JOURNAL,
      AW_GLUT_OP_ITEM, AW_GLUT_OP_DEAD, AW_GLUT_OP_CELL, AW_GLUT_OP_DISP, AW_GLUT_OP_PCFACTION,
      AW_GLUT_OP_RANDOM100};
/* SCVR function numbers the engine reads live (mwad.dialogue FUNCTIONS order). */
#define AW_GLUT_FN_HEALTH_PERCENT 4
#define AW_GLUT_FN_PC_HEALTH_PERCENT 7
#define AW_GLUT_FN_FACTION_RANK_DIFFERENCE 47
#define AW_GLUT_FN_TALKED_TO_PC 63
#define AW_GLUT_FN_PC_HEALTH 64
#define AW_GLUT_HEADER 72
#define AW_GLUT_NPC_ROW 24
#define AW_GLUT_MAX_LISTS 32       /* lists merged per topic and NPC (the data: at most 21) */
#define AW_GLUT_MAX_PICKS 64       /* entries kept for the random-pick option */

typedef struct {
    const unsigned char *data;     /* the resident part: header .. strings */
    long size, text_base, text_bytes;
    int topics, functions;
    long npcs, sets, listsets, listset_items, lists, list_items, entries, conds, sounds, globals, names, string_bytes;
    const unsigned char *topic_table, *fixture, *known, *npc, *set, *listset, *listset_item, *list, *list_item,
        *entry, *cond, *sound, *global, *name, *strings;
    int topic_of[AW_GLUT_TOPICS];  /* the file's topic index, -1 when the data has none */
} aw_glut_t;

/* The run-time values a pick reads (the engine fills them when it asks). */
typedef struct {
    int speaker_health_percent, player_health_percent, player_health;
    int talked;                    /* TalkedToPc: the player has talked to this NPC */
    int random100;                 /* Random100: 0..100, rolled per pick */
} aw_glut_state_t;

/* Pure parts (host-tested, tests/aga_glut_test.c): */
/* The resident size an AWGL1 header asks for (everything before the texts), or -1. */
long AW_GlutResidentSize(const unsigned char *header,long file_size);
/* Index the resident part: 1 = usable. */
int AW_GlutOpen(aw_glut_t *g,const unsigned char *data,long size,long file_size);
/* The NPC row of a record id (case-insensitive ASCII), binary search; -1 when absent. */
int AW_GlutFind(const aw_glut_t *g,const char *id);
const char *AW_GlutId(const aw_glut_t *g,int npc);
int AW_GlutHelloDistance(const aw_glut_t *g,int npc);
int AW_GlutResetDistance(const aw_glut_t *g);
int AW_GlutDuration(const aw_glut_t *g);
/* The entry an NPC says for a topic: the first, in the original's order, whose conditions hold (pick_random: a
 * random one of those that hold up to the list's end, an AmiWind option; roll picks it); -1 when none. */
int AW_GlutPick(const aw_glut_t *g,int npc,int topic,const aw_glut_state_t *s,int pick_random,int roll);
/* One condition record (8 bytes) for an NPC: 1 holds, 0 not (or not known to the engine). */
int AW_GlutHolds(const aw_glut_t *g,int npc,const unsigned char *cond,const aw_glut_state_t *s);
/* An entry's sound (8-byte pool hash, sound/pool/a<16 hex>.wav): 1 and hash, 0 when it has none. */
int AW_GlutSound(const aw_glut_t *g,int entry,unsigned char hash[8]);
/* An entry's text offset in the text block, -1 when it has none. */
long AW_GlutTextOffset(const aw_glut_t *g,int entry);
/* The speaker's text defines (%Name = name, %Class, %Race, %Faction, %Rank, %Cell from the NPC row) filled in;
 * the player's (%PCName, %PCRace, %PCClass) kept for AW_ExpandDialogue. */
void AW_GlutExpand(const aw_glut_t *g,int npc,const char *name,const char *source,char *out,int capacity);

/* Engine part (aw_glut.c without AW_GLUT_HOST_TEST): */
struct edict_s;
void AW_GlutInit(void);
/* Spawn (#84 aw_glut_prep): the edict's record in the table (its aw_source_id); an NPC placed without its own
 * greeting (aw_voice empty, hello distance 0: library, region and batch-room actors) takes the hello distance,
 * reset distance and greet duration from the table; 1 when the record is there (a cached lookup after the first). */
int AW_GlutPrep(struct edict_s *e);
/* The table row of an edict, -1 when none (or the table is off: aw_npc_voice_lut 0). */
int AW_GlutNpcOf(struct edict_s *e);
/* Say a topic (#85 aw_glut_say): pick, play its voice (silent when the file is missing from the build's voice
 * pool) and keep its text (speaker and player defines filled) for AW_GlutText; 1 when an entry was picked. */
int AW_GlutSay(struct edict_s *e,int topic,int talked);
const char *AW_GlutText(void);
/* The pick only (barks: aw_anim.c AW_VoiceSay): the entry's sound hash; -1 none, 0 picked without a sound, 1. */
int AW_GlutBark(struct edict_s *e,int npc,int topic,int pick_random,unsigned char hash[8]);
/* The conversation greeting text of a manual talk for an NPC without its own (aw_converse): 1 and the text. */
int AW_GlutConverse(struct edict_s *e,int again,char *out,int capacity);
#endif
