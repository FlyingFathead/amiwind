/* SPDX-License-Identifier: GPL-2.0-or-later
 * Every being's stats (ACTOR-STATS-ALL-61, docs/ACTOR_STATE.md "Every being's stats"): the squeezed stat entries the
 * builder writes into each area's record of id1/areas.awa (its AWS1 section, tools/actor_stats.py), decoded into one
 * stat block per being when its area loads, and read by the original's and OpenMW 0.51's rules:
 *   a stat the being's record type stores reads as stored; an auto-calculated NPC's attributes, skills, health,
 *   magicka and fatigue are derived from its race, class and level (OpenMW mwclass/npc.cpp autoCalculateAttributes,
 *   autoCalculateSkills; mwmechanics/creaturestats.cpp; the builder's tools/prepare_combat.py autocalc);
 *   a creature's skill is its combat, magic or stealth value by the skill's specialization (OpenMW mwclass/creature.cpp
 *   getSkill); AIDT missing reads the record defaults (NPC hello, fight, flee 30); anything else a record type lacks
 *   reads 0 (rank: -1 without a faction, OpenMW getFactionRank). Resistances and weaknesses are not stats of the
 *   original: they are the sum of the matching magic effects of the being's abilities and spells (AW_StatSpells, the
 *   ASPT rows the magic code reads).
 * Pure C, no engine headers (native tests: tests/test_actor_stats.py). */
#ifndef AW_STATS_H
#define AW_STATS_H
#include <stdint.h>

/* The stats, 0..45 the same numbers as aw_actorstate.h's AWA_* (44 and 45 there are live states, not stats). */
enum {
    AWS_ATTRIBUTE=0,               /* + 0..7: Strength .. Luck */
    AWS_SKILL=8,                   /* + 0..26: Block .. Hand-to-hand */
    AWS_HEALTH=35,AWS_MAGICKA=36,AWS_FATIGUE=37,
    AWS_LEVEL=38,
    AWS_HELLO=39,AWS_FIGHT=40,AWS_FLEE=41,AWS_ALARM=42,
    AWS_DISPOSITION=43,
    AWS_REPUTATION=46,AWS_RANK=47,AWS_GOLD=48,AWS_SERVICES=49,
    AWS_SOUL=50,AWS_COMBAT=51,AWS_MAGIC=52,AWS_STEALTH=53,
    AWS_ATTACK=54,                 /* + 0..5: chop min, max, slash min, max, thrust min, max */
    AWS_TYPE=60,                   /* a creature's type: 0 creature, 1 daedra, 2 undead, 3 humanoid */
    AWS_BLOOD=61,                  /* FLAG >> 10 */
    AWS_FLAGS=62,                  /* FLAG's low byte, the record's own bits */
    AWS_STATS=63
};
/* Record kinds (the entry's first byte). */
enum {AWS_KIND_STORED=0,AWS_KIND_AUTO=1,AWS_KIND_CREATURE=2};
/* Present mask bits (a storage form only: what a kind has is AW_StatHas's). */
#define AWS_P_BASE 1
#define AWS_P_FLAGS 2
#define AWS_P_AI 4
#define AWS_P_SERVICES 8
#define AWS_P_FACTION 16
#define AWS_P_RACE 32
#define AWS_P_SPELLS 64
#define AWS_P_GOLD 128
#define AWS_SPELLS 96                /* spells kept per block: the record's own, then its race's (OpenMW adds both) */
#define AWS_NO_SPELL 0xFFFF
#define AWS_SECTION_HEAD 66          /* "AWS1" u16 entries, u8 races, u8 classes, f32, 27 x 2 skill bytes */
#define AWS_SLIM_HEAD 8              /* "AWS2" u16 entries, u16 0 (an area's section; the tables are shared) */
#define AWS_SHARED_KEY 0x7FFE0000UL  /* the area pack's key of the shared stats record */

typedef struct aw_stat_block_s {
    unsigned char kind,valid;
    unsigned short mask;
    uint32_t id,faction,race,clas;       /* FNV-1a hashes of the ids (0: none) */
    short level,rank;
    unsigned char attributes[8],skills[27],cms[3];   /* creatures: combat, magic, stealth */
    unsigned char disposition,reputation,flags,blood,type,fight,flee,alarm;
    unsigned short dynamic[3],hello,soul,attacks[6];
    uint32_t services,gold;
    unsigned char skill_spec[27];        /* each skill's specialization (0 combat, 1 magic, 2 stealth; the section's) */
    int nspells,race_spells;             /* spells[0..nspells): own first, then race_spells of the race's */
    uint16_t spells[AWS_SPELLS];
} aw_stat_block_t;

/* The entry of HASH in an AWS1 SECTION of BYTES (binary search), its offset from the section's start; 0 when none. */
long AW_StatSectionFind(const unsigned char *section,long bytes,uint32_t hash);
/* The block of HASH decoded (an auto-calculated NPC's stats derived); 1 found, 0 not in the section or a bad one.
 * A slim AWS2 section (an area's: its entries only) reads the skill table and the race and class rows of SHARED,
 * the shared stats record's whole AWS1 section (DRY: those rows once for the island, not in every area); a whole
 * AWS1 section reads its own (SHARED may be NULL). */
int AW_StatDecode(const unsigned char *section,long bytes,uint32_t hash,const unsigned char *shared,long shared_bytes,
                  aw_stat_block_t *out);
/* The same for the entry at OFFSET (a placed actor's row names it: tools/actor_stats.py mark_row; the direct lookup,
 * no search); the block's id is left 0 for the caller. */
int AW_StatDecodeAt(const unsigned char *section,long bytes,long offset,const unsigned char *shared,long shared_bytes,
                    aw_stat_block_t *out);
/* The entry offset an area record's actor row (96 bytes) carries, 0 none (bytes 92..95: "S", 0, u16). */
long AW_StatRowOffset(const unsigned char *row);
/* The actor table (ACTB) row an actor row carries (bytes 88..91: "R", 0, u16), -1 none. */
long AW_StatRowActb(const unsigned char *row);
/* 1 when the being's record type stores STAT (an auto NPC's derived ones count as its own: OpenMW keeps them). */
int AW_StatHas(const aw_stat_block_t *b,int stat);
/* The value by the read rules above; never fails (0 for a stat the record type lacks). */
int AW_StatRead(const aw_stat_block_t *b,int stat);
/* The being's ability and spell rows (ASPT), own and race's, up to MAX; the count. */
int AW_StatSpells(const aw_stat_block_t *b,int *out,int max);
/* The player's spells at character creation (OpenMW 0.51 mechanicsmanagerimp.cpp: the race's powers and abilities,
 * the birthsign's spells), as ASPT rows from the shared stats record T: of race RACE (id hash), of birthsign BIRTH;
 * up to MAX; the count (0 none or no such row). */
int AW_StatRaceSpells(const unsigned char *t,long tb,uint32_t race,int *out,int max);
int AW_StatBirthSpells(const unsigned char *t,long tb,uint32_t birth,int *out,int max);
/* FNV-1a of an id with A-Z folded, 0 made 1 (AW_LedgerNameHash's rule). */
uint32_t AW_StatIdHash(const char *id);
const char *AW_StatName(int stat);       /* a short name for readouts ("strength", "block", "health" ...) */
#endif
