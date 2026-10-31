/* SPDX-License-Identifier: GPL-2.0-or-later
 * The actor record: one per NPC and creature the game touches, owned by the engine from load (docs/ACTOR_STATE.md).
 *
 * The base of every actor is a row of the actor table the builder writes into id1/mwscript.awm (tools/mwscript/
 * actors.py: ACTB, AINV, AITM, ASPT, ASPL, OACT); the rows stay on disk and are read through the host's read
 * function when an actor is first needed. What play changes lives in a live record per placed reference (a fixed
 * pool, no allocation after AW_ActorStateOpen), saved with the game (AW_ActorStateExport/Import) and found again by
 * the reference. Combat, behaviour and the scripts all read and write the same record through these calls; the scripts'
 * semantics are OpenMW's (apps/openmw/mwscript/statsextensions.cpp, aiextensions.cpp, containerextensions.cpp),
 * written independently.
 *
 * Pure C, no engine headers (native tests: tests/test_actorstate.py). */
#ifndef AW_ACTORSTATE_H
#define AW_ACTORSTATE_H
#include <stdint.h>

#define AW_ACTOR_NONE 0xFFFF
#define AW_ACTOR_POOL 128          /* live records (268 bytes each on the host build) */
#define AW_ACTOR_ITEMS 12          /* inventory changes kept per actor (item, count change) */
#define AW_ACTOR_SPELLS 8          /* spell changes kept per actor (spell, added or removed) */
#define AW_ACTOR_PLAYER_REF 0xFFFFFFFFu   /* the player's own record (its sheet: aw_character, by the host) */

/* Stats (the STAT of the calls below and of the scripts' ACTOR opcode). */
enum {
    AWA_ATTRIBUTE=0,               /* + 0..7: Strength .. Luck (the original's order) */
    AWA_SKILL=8,                   /* + 0..26: Block .. Hand-to-hand */
    AWA_HEALTH=35,AWA_MAGICKA=36,AWA_FATIGUE=37,  /* dynamic: current (get), base and current (set, mod) */
    AWA_LEVEL=38,
    AWA_HELLO=39,AWA_FIGHT=40,AWA_FLEE=41,AWA_ALARM=42,  /* the behaviour ratings (AIDT) */
    AWA_DISPOSITION=43,            /* base disposition (NPCs; get: as stored, see docs) */
    AWA_ONDEATH=44,                /* get: 1 once after the actor died (OnDeath), then 0 */
    AWA_DEAD=45,                   /* get: 1 while dead */
    AWA_STATS=46
};
/* Verbs (the scripts' ACTOR opcode). */
enum {AWV_GET=0,AWV_SET=1,AWV_MOD=2,AWV_MODCURRENT=3,AWV_RATIO=4};

/* Record flags (the actor table's ACTB flags). */
#define AWR_FEMALE 1
#define AWR_ESSENTIAL 2
#define AWR_RESPAWN 4
#define AWR_AUTOCALC 8
#define AWR_WALKS 16
#define AWR_SWIMS 32
#define AWR_FLIES 64
#define AWR_BIPEDAL 128
/* Live flags. */
#define AWL_USED 1
#define AWL_CHANGED 2              /* differs from its base: kept and saved */
#define AWL_DEAD 4
#define AWL_DIED 8                 /* died and OnDeath has not read it yet */
#define AWL_COMBAT 16              /* a script started combat with the player (StartCombat) */
/* Inventory entry flags (AINV). */
#define AWI_INV_EQUIPPED 1
#define AWI_INV_LEVELLED 2
#define AWI_INV_RESTOCKS 4
/* Item kinds (AITM). */
enum {AWK_UNKNOWN,AWK_WEAPON,AWK_ARMOR,AWK_CLOTHING,AWK_OTHER,AWK_LEVELLED};

/* One row of the actor table, decoded (aw_actorstate_base). */
typedef struct {
    uint16_t id,race,clas,faction;       /* string indexes of the file's STRS (AW_ACTOR_NONE: none) */
    unsigned char kind,flags;            /* kind 0 NPC, 1 creature; AWR_* */
    short level,rank;
    unsigned short attributes[8];
    unsigned char skills[27];
    unsigned char hello,fight,flee,alarm,disposition,reputation;
    unsigned short health,magicka,fatigue;
    uint32_t gold;
    uint16_t inv_first,inv_count,spell_first,spell_count;
    unsigned char weapon,type;           /* weapon: its inventory entry (0xFF none); creature type */
    unsigned short attack[6],soul;       /* creatures: chop/slash/thrust min,max; soul value */
} aw_actor_base_t;
/* A shared item (AITM). */
typedef struct {
    uint16_t id;unsigned char kind,type;unsigned short health,rating;unsigned char damage[6];unsigned short flags;
    float weight,speed,reach;
} aw_item_t;

/* The live record. Attributes and skills: modified = base + mod (mod: fortify minus damage, OpenMW's modStat). */
typedef struct {
    uint32_t reference;                  /* the placed reference; AW_ACTOR_PLAYER_REF the player */
    uint16_t base,flags;                 /* the ACTB row; AWL_* */
    short level;
    short attr_base[8],attr_mod[8];
    short skill_base[27],skill_mod[27];
    float dyn_base[3],dyn_cur[3];        /* health, magicka, fatigue */
    unsigned char ai[4];                 /* hello, fight, flee, alarm */
    short disposition;
    unsigned char kind,record_flags;
    unsigned char nitems,nspells;
    struct {uint16_t item;int16_t change;} items[AW_ACTOR_ITEMS];
    struct {uint16_t spell;int16_t change;} spells[AW_ACTOR_SPELLS];  /* change: +1 added, -1 removed */
} aw_actor_t;

/* The host: READ the bytes at OFFSET of id1/mwscript.awm (0 on success). */
typedef struct {
    int (*read)(void *context,uint32_t offset,void *out,uint32_t bytes);
    void *context;
} aw_actorstate_io_t;

typedef struct {
    unsigned long reads,finds,created,evicted,full,changed;
} aw_actorstate_stats_t;

/* Open the actor table: HEAD the file's first bytes (header and directory, at least 16 + 16 * sections); the pool
 * is cleared. 1 ready, 0 no actor table in this file. */
int AW_ActorStateOpen(const unsigned char *head,uint32_t head_bytes,const aw_actorstate_io_t *io);
void AW_ActorStateClose(void);
int AW_ActorStateReady(void);
int AW_ActorCount(void);
/* The ACTB row of an actor id (folded; binary search on disk), AW_ACTOR_NONE if none. */
int AW_ActorFind(const char *id);
/* The ACTB row the scripts' object OBJECT names (the resident OACT table), AW_ACTOR_NONE if none. */
int AW_ActorOfObject(int object,const uint16_t *oact,int count);
int AW_ActorBase(int row,aw_actor_base_t *out);
int AW_ActorItem(int item,aw_item_t *out);
/* The live record of a placed REFERENCE whose base is ROW; CREATE 1 makes it from the base when it does not exist
 * (an unchanged record may be dropped for a new one when the pool is full; a changed one never). */
aw_actor_t *AW_ActorGet(uint32_t reference,int row,int create);
/* The player's record (base: the "player" row); the host fills it from its character sheet (AW_ActorPlayerSet). */
aw_actor_t *AW_ActorPlayer(void);

/* Stats with OpenMW's semantics (docs/ACTOR_STATE.md "The calls"). */
float AW_ActorStat(const aw_actor_t *a,int stat);                 /* GET: modified value, current dynamic */
void AW_ActorSetStat(aw_actor_t *a,int stat,float value);         /* SET: the base (dynamics: base, current to it) */
void AW_ActorModStat(aw_actor_t *a,int stat,float value);         /* MOD: base and current change by VALUE */
void AW_ActorModCurrent(aw_actor_t *a,int dynamic,float value);   /* MODCURRENT: current only, capped at the base */
float AW_ActorRatio(const aw_actor_t *a,int dynamic);             /* current / base (1 when base is 0) */
int AW_ActorOnDeath(aw_actor_t *a);                               /* 1 once after it died */
void AW_ActorKill(aw_actor_t *a);                                 /* dead; OnDeath reads 1 once; dead count + 1 */
int AW_ActorDeadCount(int row);                                   /* GetDeadCount of an actor id */
/* Inventory: the base list plus the changes; ITEM an AITM row. */
int AW_ActorItemCount(const aw_actor_t *a,int item);
int AW_ActorAddItem(aw_actor_t *a,int item,int count);            /* 0 when the change list is full */
int AW_ActorRemoveItem(aw_actor_t *a,int item,int count);         /* removes up to what it has; returns how many */
int AW_ActorEquipped(const aw_actor_t *a,int entry);              /* 1: base entry ENTRY is worn or held */
/* The type of the weapon the record of ROW holds (its weapon entry: the WPDT type, OpenMW's weapon type 0..13), -1
 * none (the animation's stance, aw_animkit.c). */
int AW_ActorWeaponType(int row);
/* Spells: the base list plus the changes; SPELL an ASPT row. */
int AW_ActorHasSpell(const aw_actor_t *a,int spell);
/* Any spell of an ASPT type (2 blight, 3 disease) in the base list and the changes (GetBlightDisease,
 * GetCommonDisease). */
int AW_ActorHasSpellType(const aw_actor_t *a,int type);
int AW_ActorAddSpell(aw_actor_t *a,int spell);
/* A cure: every spell of an ASPT TYPE (2 blight, 3 disease) leaves the actor's list; how many were removed. */
int AW_ActorRemoveSpellType(aw_actor_t *a,int type);
int AW_ActorRemoveSpell(aw_actor_t *a,int spell);

/* Saved games: the changed records and the dead counts (a byte block, AWAS1). Export returns the bytes written
 * (0 nothing to save, -1 too small); Import returns 1, or 0 for a bad block (the pool is left empty). */
int AW_ActorStateExport(unsigned char *out,int capacity);
int AW_ActorStateImport(const unsigned char *data,int bytes);
const aw_actorstate_stats_t *AW_ActorStateStats(void);
/* Bytes held while open (the pool, the dead counts, the directory). */
unsigned long AW_ActorStateResident(void);
#endif
