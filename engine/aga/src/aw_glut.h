/* SPDX-License-Identifier: GPL-2.0-or-later
 * The NPC voice and greeting table (AWGL2, id1/npc-voices.lut, tools/greeting_lut.py; docs/NPC_VOICE_TABLE.md):
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
#define AW_GLUT_VERSION 2          /* 2: the creature sound rows and the named sound slots (27 October 2026) */
#define AW_GLUT_HEADER 80
#define AW_GLUT_NPC_ROW 24
#define AW_GLUT_SOUND_ROW 12       /* the pool file's 8 bytes, u16 length (1/100 s), u16 flags (AW_GLUT_MAPPED) */
#define AW_GLUT_CREATURE_ROW 20    /* u32 id string offset, 8 x u16 sound (AW_SNDG_* order; 0xFFFF none) */
#define AW_GLUT_SOUN_ROW 16        /* pool 8 bytes, u16 length, u8 volume, u8 flags, u16 near, u16 far */
#define AW_GLUT_MAPPED 1           /* the build has the converted file */

/* THE SOUND TABLE CONTRACT (docs/NPC_DEFAULTS.md "How AmiWind stores them"; the writer is tools/greeting_lut.py,
 * whose SNDG_MOMENTS and SOUND_SLOTS tests/test_greeting_lut.py checks against these two enums, name by name).
 * Every sound is an index into the file's Sounds table (u16; 0xFFFF none); index i is the pool file
 * sound/pool/a<16 hex>.wav whose 16 hex digits are the table's 8 bytes (AW_GlutPoolPath).
 * Creature rows: one per creature record of the three masters, sorted by the folded id like the NPC rows; each
 * moment holds the creature's own sound generator, else its original's, else one of a creature with the same model,
 * else the generic one (OpenMW mwclass/creature.cpp getSoundIdFromSndGen; resolved by the builder, the engine only
 * reads). Named slots: the sounds the engine plays by name (OpenMW mwmechanics/combat.cpp, character.cpp,
 * the mwclass item classes' getUpSoundId/getDownSoundId), one u16 each in this order. */
enum {AW_SNDG_LEFT_FOOT, AW_SNDG_RIGHT_FOOT, AW_SNDG_SWIM_LEFT, AW_SNDG_SWIM_RIGHT, AW_SNDG_MOAN, AW_SNDG_ROAR,
      AW_SNDG_SCREAM, AW_SNDG_LAND, AW_SNDG_MOMENTS};
enum {
    AW_SLOT_WEAPON_SWISH, AW_SLOT_MISS, AW_SLOT_LIGHT_ARMOR_HIT, AW_SLOT_MEDIUM_ARMOR_HIT, AW_SLOT_HEAVY_ARMOR_HIT,
    AW_SLOT_HAND_TO_HAND_HIT, AW_SLOT_HAND_TO_HAND_HIT_2, AW_SLOT_HEALTH_DAMAGE,
    AW_SLOT_BOW_PULL, AW_SLOT_BOW_SHOOT, AW_SLOT_CROSSBOW_PULL, AW_SLOT_CROSSBOW_SHOOT,
    AW_SLOT_DEFAULT_LAND, AW_SLOT_DEFAULT_LAND_WATER, AW_SLOT_BODY_FALL_SMALL, AW_SLOT_BODY_FALL_MEDIUM,
    AW_SLOT_BODY_FALL_LARGE,
    AW_SLOT_FOOT_BARE_LEFT, AW_SLOT_FOOT_BARE_RIGHT, AW_SLOT_FOOT_LIGHT_LEFT, AW_SLOT_FOOT_LIGHT_RIGHT,
    AW_SLOT_FOOT_MED_LEFT, AW_SLOT_FOOT_MED_RIGHT, AW_SLOT_FOOT_HEAVY_LEFT, AW_SLOT_FOOT_HEAVY_RIGHT,
    AW_SLOT_FOOT_WATER_LEFT, AW_SLOT_FOOT_WATER_RIGHT, AW_SLOT_SWIM_LEFT, AW_SLOT_SWIM_RIGHT,
    /* an item's pick-up (UP) and put-down (DOWN) sound by its kind */
    AW_SLOT_ITEM_AMMO_UP, AW_SLOT_ITEM_AMMO_DOWN, AW_SLOT_ITEM_APPARATUS_UP, AW_SLOT_ITEM_APPARATUS_DOWN,
    AW_SLOT_ITEM_ARMOR_LIGHT_UP, AW_SLOT_ITEM_ARMOR_LIGHT_DOWN, AW_SLOT_ITEM_ARMOR_MEDIUM_UP,
    AW_SLOT_ITEM_ARMOR_MEDIUM_DOWN, AW_SLOT_ITEM_ARMOR_HEAVY_UP, AW_SLOT_ITEM_ARMOR_HEAVY_DOWN,
    AW_SLOT_ITEM_BODYPART_UP, AW_SLOT_ITEM_BODYPART_DOWN, AW_SLOT_ITEM_BOOK_UP, AW_SLOT_ITEM_BOOK_DOWN,
    AW_SLOT_ITEM_CLOTHES_UP, AW_SLOT_ITEM_CLOTHES_DOWN, AW_SLOT_ITEM_GOLD_UP, AW_SLOT_ITEM_GOLD_DOWN,
    AW_SLOT_ITEM_INGREDIENT_UP, AW_SLOT_ITEM_INGREDIENT_DOWN, AW_SLOT_ITEM_LOCKPICK_UP, AW_SLOT_ITEM_LOCKPICK_DOWN,
    AW_SLOT_ITEM_MISC_UP, AW_SLOT_ITEM_MISC_DOWN, AW_SLOT_ITEM_POTION_UP, AW_SLOT_ITEM_POTION_DOWN,
    AW_SLOT_ITEM_PROBE_UP, AW_SLOT_ITEM_PROBE_DOWN, AW_SLOT_ITEM_REPAIR_UP, AW_SLOT_ITEM_REPAIR_DOWN,
    AW_SLOT_ITEM_RING_UP, AW_SLOT_ITEM_RING_DOWN, AW_SLOT_ITEM_WEAPON_BLUNT_UP, AW_SLOT_ITEM_WEAPON_BLUNT_DOWN,
    AW_SLOT_ITEM_WEAPON_BOW_UP, AW_SLOT_ITEM_WEAPON_BOW_DOWN, AW_SLOT_ITEM_WEAPON_CROSSBOW_UP,
    AW_SLOT_ITEM_WEAPON_CROSSBOW_DOWN, AW_SLOT_ITEM_WEAPON_LONGBLADE_UP, AW_SLOT_ITEM_WEAPON_LONGBLADE_DOWN,
    AW_SLOT_ITEM_WEAPON_SHORTBLADE_UP, AW_SLOT_ITEM_WEAPON_SHORTBLADE_DOWN, AW_SLOT_ITEM_WEAPON_SPEAR_UP,
    AW_SLOT_ITEM_WEAPON_SPEAR_DOWN,
    AW_SLOTS
};
#define AW_GLUT_MAX_LISTS 32       /* lists merged per topic and NPC (the data: at most 21) */
#define AW_GLUT_MAX_PICKS 64       /* entries kept for the random-pick option */

typedef struct {
    const unsigned char *data;     /* the resident part: header .. strings */
    long size, text_base, text_bytes;
    int topics, functions;
    long npcs, sets, listsets, listset_items, lists, list_items, entries, conds, sounds, globals, names, string_bytes;
    long creatures, slots, souns;  /* version 2: creature sound rows, named sound slots (>= AW_SLOTS), SOUN rows */
    const unsigned char *topic_table, *fixture, *known, *npc, *set, *listset, *listset_item, *list, *list_item,
        *entry, *cond, *sound, *global, *name, *creature, *slot, *soun, *strings;
    int topic_of[AW_GLUT_TOPICS];  /* the file's topic index, -1 when the data has none */
} aw_glut_t;

/* The run-time values a pick reads (the engine fills them when it asks). */
typedef struct {
    int speaker_health_percent, player_health_percent, player_health;
    int talked;                    /* TalkedToPc: the player has talked to this NPC */
    int random100;                 /* Random100: 0..100, rolled per pick */
} aw_glut_state_t;

/* Pure parts (host-tested, tests/aga_glut_test.c): */
/* The resident size an AWGL2 header asks for (everything before the texts), or -1. */
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
/* THE SHARED CONDITION EVALUATOR (greetings, voice lines and the dialogue table's topics, aw_dial.c): what a
 * condition record reads beside the run-time state, from whichever table holds it. */
#define AW_GLUT_FN_CHOICE 50
typedef struct {
    const unsigned char *global;   /* rows of 8 bytes: u32 name string offset, f32 value */
    long globals;
    const unsigned char *name;     /* rows of 4 bytes: u32 string offset */
    long names;
    const unsigned char *strings;
    const unsigned char *fixture,*known;   /* the start-of-game function values and which are known */
    int functions;
    int rank;                      /* the speaker's faction rank, -1 none */
    int disposition;               /* the speaker's disposition the Disposition test reads */
    const char *cell;              /* the speaker's home cell name, NULL when not one cell */
    int choice;                    /* the player's pick of the open Choice, -1 none */
    const char *faction;           /* the speaker's faction id (folded), NULL none: PcFaction tests without a faction */
    int speaker;                   /* the speaker's edict number for the live hooks, -1 none */
    int local_slots;               /* 1: a Local / NotLocal operand is the slot in the speaker's script (the dialogue
                                    * table; AW_GLUT_LOCAL_FLOAT marks a float), 0: a name (the voice table) */
} aw_glut_cond_t;
#define AW_GLUT_LOCAL_FLOAT 0x4000
/* The game's live state for the conditions (aw_mwhost.c sets it when the scripts are on; NULL: the start-of-game
 * values, as before). Each returns 1 with *OUT set, or 0 when it does not know (then the start value). Names are the
 * condition's own (folded ids). */
typedef struct {
    int (*journal)(const char *quest,long *out);                  /* the quest's journal index */
    int (*dead)(const char *actor,long *out);                     /* GetDeadCount of an actor id */
    int (*item)(const char *item,long *out);                      /* the player's count of an item id */
    int (*pc_rank)(const char *faction,long *out);                /* the player's rank, -1 not a member */
    int (*global)(const char *name,float *out);                   /* a global's value */
    int (*function)(const aw_glut_cond_t *c,unsigned fn,long *out);   /* an SCVR function the fixture would read */
    int (*local)(const aw_glut_cond_t *c,int slot,int is_float,float *out);  /* the speaker's script local */
} aw_glut_live_t;
extern const aw_glut_live_t *aw_glut_live;
int AW_GlutCond(const aw_glut_cond_t *c,const unsigned char *cond,const aw_glut_state_t *s);
/* The context of an NPC row of the voice table (its rank, base disposition and home cell; no choice open). */
void AW_GlutCondOf(const aw_glut_t *g,int npc,aw_glut_cond_t *c);
/* An entry's sound (8-byte pool hash, sound/pool/a<16 hex>.wav): 1 and hash, 0 when it has none. */
int AW_GlutSound(const aw_glut_t *g,int entry,unsigned char hash[8]);
/* The sound table (version 2; every index was bounded at open):
 * a creature record's row by its id (case-insensitive, binary search), -1 when absent; */
int AW_GlutCreatureFind(const aw_glut_t *g,const char *id);
/* the Sounds index of a creature row's moment (AW_SNDG_*), -1 when none; */
int AW_GlutCreatureSound(const aw_glut_t *g,int row,int moment);
/* the Sounds index of a named slot (AW_SLOT_*), -1 when none; */
int AW_GlutSlotSound(const aw_glut_t *g,int slot);
/* a Sounds index as its pool path, "sound/pool/a<16 hex>.wav" (capacity >= AW_GLUT_POOL_PATH, the 32 characters
 * and the NUL): 1, or 0 for a bad index. */
#define AW_GLUT_POOL_PATH 33
int AW_GlutPoolPath(const aw_glut_t *g,int sound,char *out,int capacity);
/* a Sounds index's length in 1/100 s (0 unknown) and whether the build has the file (AW_GLUT_MAPPED); -1 bad index */
int AW_GlutSoundLength(const aw_glut_t *g,int sound);
int AW_GlutSoundMapped(const aw_glut_t *g,int sound);
/* A SOUN record's row (the compiled scripts' sounds index them: SOUN records of the three masters sorted by folded
 * id, tools/greeting_lut.py soun_order): 1 and the row, 0 for a bad index. hash is all zero when not mapped. */
typedef struct {
    unsigned char hash[8];
    unsigned short centis, near_units, far_units;   /* hearing distances: min/max x fAudioMin/MaxDistanceMult */
    unsigned char volume, mapped;
} aw_glut_soun_t;
int AW_GlutSoun(const aw_glut_t *g,int index,aw_glut_soun_t *out);
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
/* For the dialogue window (aw_dialwin.c): the edict's row (-1 none) with its condition context and run-time state;
 * a text with the speaker's and the player's defines filled. */
int AW_GlutSpeaker(struct edict_s *e,int talked,aw_glut_cond_t *c,aw_glut_state_t *s);
void AW_GlutFill(struct edict_s *e,int row,const char *raw,char *out,int capacity);
/* The conversation greeting text of a manual talk for an NPC without its own (aw_converse): 1 and the text. */
int AW_GlutConverse(struct edict_s *e,int again,char *out,int capacity);
#endif
