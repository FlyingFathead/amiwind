/* SPDX-License-Identifier: GPL-2.0-or-later
 * The actor record: one per NPC and creature the game touches, owned by the engine from load (docs/ACTOR_STATE.md).
 *
 * The base of every actor is a row of the actor table the builder writes into id1/mwscript.awm (tools/mwscript/
 * actors.py: ACTB, AINV, AITM, ASPT, ASPL, OACT); the rows stay on disk and are read through the host's read
 * function when an actor is first needed. What play changes lives in a live record per placed reference (a pool of
 * blocks that grows only while every record in it is changed, below), saved with the game (the dead counts in the
 * actor block, the changed records in the world change list: AW_ActorStateExportCounts/Records) and found again by
 * the reference. Combat, behaviour and the scripts all read and write the same record through these calls; the scripts'
 * semantics are OpenMW's (apps/openmw/mwscript/statsextensions.cpp, aiextensions.cpp, containerextensions.cpp),
 * written independently.
 *
 * Pure C, no engine headers (native tests: tests/test_actorstate.py). */
#ifndef AW_ACTORSTATE_H
#define AW_ACTORSTATE_H
#include <stdint.h>

#define AW_ACTOR_NONE 0xFFFF
/* ACTOR-STATE-POOL-LIMITS-54 (CELL-CHANGES-59 slice 6): the live records come in blocks of AW_ACTOR_POOL; an unchanged
 * record gives its place to a new one, a changed one is never dropped: when every record is changed a new block is
 * taken, up to AW_ACTOR_POOL_MAX records (the game's actor table has 3,437 bases; it places 2,673 NPCs). The change
 * lists of one actor grow on demand up to AW_ACTOR_ITEMS / AW_ACTOR_SPELLS (were 12 and 8). */
#define AW_ACTOR_POOL 128          /* live records per block */
#define AW_ACTOR_POOL_MAX 8192     /* live records at most */
#define AW_ACTOR_ITEMS 255         /* inventory changes kept per actor (item, count change) */
#define AW_ACTOR_SPELLS 255        /* spell changes kept per actor (spell, added or removed) */
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
    uint16_t enchant;                    /* its enchantment's AENC row (AW_ActorEnchant), AW_ACTOR_NONE none (v0.0.61) */
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
    unsigned char nitems,nspells,items_capacity,spells_capacity;
    struct aw_actor_item_s {uint16_t item;int16_t change;} *items;      /* grown on demand (NULL: none) */
    struct aw_actor_spell_s {uint16_t spell;int16_t change;} *spells;   /* change: +1 added, -1 removed */
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
void AW_ActorFindForget(void);   /* the kept finds go (ARRIVAL-LONG-FRAME-DEV6-59; the table closes) */
/* The ACTB row the scripts' object OBJECT names (the resident OACT table), AW_ACTOR_NONE if none. */
int AW_ActorOfObject(int object,const uint16_t *oact,int count);
int AW_ActorBase(int row,aw_actor_base_t *out);
int AW_ActorItem(int item,aw_item_t *out);
/* The live record of a placed REFERENCE whose base is ROW; CREATE 1 makes it from the base when it does not exist
 * (an unchanged record may be dropped for a new one when the pool is full; a changed one never). */
aw_actor_t *AW_ActorGet(uint32_t reference,int row,int create);
/* The player's record (base: the "player" row); the host fills it from its character sheet (AW_ActorPlayerSet). */
aw_actor_t *AW_ActorPlayer(void);
/* ACTOR-STATS-ALL-61 (aw_stats.h, docs/ACTOR_STATS.md): the live record of a placed REFERENCE whose base is ROW, made
 * from its area's stat block B when it has none yet (the area load fills every placed actor's record this way, before
 * play; a record that exists is returned as it is). A record made from the base row without a block asks
 * aw_actor_stats_source (the host: the loaded areas' block of a placed reference; NULL or 0: the actor table's row,
 * the previous method, counted). AW_ActorStatsSwitch(-1) reads, 0 / 1 sets the area stats on (1, the default) or off
 * (the actor table's rows only); the value before. */
struct aw_stat_block_s;
aw_actor_t *AW_ActorFromStats(uint32_t reference,int row,const struct aw_stat_block_s *b);
extern int (*aw_actor_stats_source)(uint32_t reference,struct aw_stat_block_s *out);
int AW_ActorStatsSwitch(int on);
/* records made from area blocks, from the actor table's rows */
void AW_ActorStatsCounts(unsigned long out[2]);

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
/* 1 when a worn or held entry of A's base list is the AITM row ITEM, still carried (HasItemEquipped, v0.0.63) */
int AW_ActorWearsItem(const aw_actor_t *a,int item);
/* The type of the weapon the record of ROW holds (its weapon entry: the WPDT type, OpenMW's weapon type 0..13), -1
 * none (the animation's stance, aw_animkit.c). */
int AW_ActorWeaponType(int row);
/* The AENC row of the enchantment on the weapon the record of ROW holds (AW_ACTOR_NONE: none, or no weapon); *ITEM its
 * AITM row (-1 none). v0.0.61, an NPC's Cast When Strikes weapon. */
int AW_ActorWeaponEnchant(int row,int *item);
/* Spells: the base list plus the changes; SPELL an ASPT row. */
int AW_ActorHasSpell(const aw_actor_t *a,int spell);
/* Any spell of an ASPT type (2 blight, 3 disease) in the base list and the changes (GetBlightDisease,
 * GetCommonDisease). */
int AW_ActorHasSpellType(const aw_actor_t *a,int type);
int AW_ActorAddSpell(aw_actor_t *a,int spell);
/* A cure: every spell of an ASPT TYPE (2 blight, 3 disease) leaves the actor's list; how many were removed. */
int AW_ActorRemoveSpellType(aw_actor_t *a,int type);
int AW_ActorRemoveSpell(aw_actor_t *a,int spell);
/* A spell's type (ASPT), name and price cost (ASPC, the game's rule: tools/mwscript/actors.py spell_cost); 0 when
 * the table has no ASPC (before v0.0.58) or SPELL is out of range. */
int AW_ActorSpellInfo(int spell,int *type,char *name,int capacity,int *cost);
/* The spells A holds now (its base list with the changes), up to MAX; the count. */
int AW_ActorSpells(const aw_actor_t *a,int *out,int max);
/* The items A holds now (gold aside) with counts and whether equipped, up to MAX; and an item's id (folded). */
int AW_ActorItems(const aw_actor_t *a,int *items,int *counts,int *equipped,int max);
int AW_ActorItemId(int item,char *out,int capacity);
/* Things sold to merchants that did not stock them (BARTER-SOLD-ITEM-LOST-58): per merchant REFERENCE and id, a
 * count; added (DELTA > 0) or bought back (< 0); carried in the saved game as an AWSL block. */
/* Magic effects (AMGE, the MGEF records: flags, base cost, school) and a spell's effects (ASPE/AEFF, its ENAM);
 * read from disk when a window or a cast asks. 0 / none when the table predates them (v0.0.58). */
typedef struct {uint32_t flags;float base_cost;int school;char name[32];} aw_mgef_t;   /* name: the game's word */
typedef struct {int16_t effect;signed char skill,attribute;unsigned char range;unsigned short area,duration,magnitude_min,magnitude_max;} aw_spell_effect_t;
int AW_ActorMagicEffect(int index,aw_mgef_t *out);
#define AW_MGEF_FLAG_NO_MAGNITUDE 0x8u   /* the MGEF NoMagnitude flag (as aw_cast.h AW_MGEF_NO_MAGNITUDE) */
int AW_ActorSpellEffects(int spell,aw_spell_effect_t *out,int max);
/* A spell's SPDT flags (ASPT byte 3, v0.0.61): AW_SPELL_AUTOCALC, AW_SPELL_PC_START, AW_SPELL_ALWAYS; 0 in older
 * tables. */
#define AW_SPELL_AUTOCALC 1
#define AW_SPELL_PC_START 2
#define AW_SPELL_ALWAYS 4
int AW_ActorSpellFlags(int spell);
/* RESIST-NORMAL-WEAPONS-61 (v0.0.62): the summed magnitude of EFFECT (0..142, every argument) among the spells of A's
 * list that act always: every type but a castable spell (0) and a power (5), i.e. abilities, blights, diseases and
 * curses (rule from OpenMW 0.51 apps/openmw/mwmechanics/activespells.cpp update: such spells of the actor's list are
 * kept active with no end). OpenMW rolls each such effect's magnitude once; here the middle of its range, the same
 * number for every ability of the game data (minimum = maximum in all of them). Reads the actor's list and those
 * spells' effects from disk: the caller keeps the answer. 0 none. */
float AW_ActorPassiveMagnitude(const aw_actor_t *a,int effect);
/* Things the player made (bounded, saved: AWMD, AWEN): spells and enchanted items, up to 8 effects each. */
#define AW_MADE_EFFECTS 8
/* The game's enchantments (AENC, v0.0.61; tools/mwscript/actors.py): TYPE 0 cast once, 1 when strikes, 2 when used,
 * 3 constant effect; FLAGS 1 autocalc; COST the cast cost before the caster's Enchant skill; CHARGE the full charge;
 * the effects (the masters have at most 8). Find: the row of an enchantment id (folded; a binary search on disk, the
 * last 16 answers kept), AW_ACTOR_NONE none. */
typedef struct {int type,flags,n;float cost,charge;aw_spell_effect_t effect[AW_MADE_EFFECTS];} aw_enchant_t;
int AW_ActorEnchantCount(void);
int AW_ActorEnchantFind(const char *id);
int AW_ActorEnchant(int row,aw_enchant_t *out);
/* The starting spells of a new character (APCS, v0.0.61): the rule's game settings and the ASPT rows of the spells
 * flagged as starting spells, in the masters' record order; how many (0: an older table). */
typedef struct {float magicka_mult,chance,cost_mult;int max,skill_min;} aw_start_settings_t;
int AW_ActorStartSpells(aw_start_settings_t *set,int *rows,int max);
#define AW_MADE_ITEM_PREFIX "aw_made_"   /* the inventory id of made item N: aw_made_N */
/* ALCHEMY-61: a made potion is a made item whose cast type is AW_MADE_POTION: BASE the potion of the masters whose
 * bottle it borrows (model, picture), NAME its name, CHARGE its weight, CHARGE_MAX its value, the effects its own
 * (range Self, magnitude min = max); kept and saved with the enchanted items (AWEN, no new block) */
#define AW_MADE_POTION 4
#define AW_MADE_SPELL_BYTES 152
#define AW_MADE_ITEM_BYTES 200
typedef struct {char name[32];int effects;aw_spell_effect_t effect[AW_MADE_EFFECTS];} aw_made_spell_t;
typedef struct {char base[40],name[32];float charge,charge_max;unsigned char cast_type;int effects;
                aw_spell_effect_t effect[AW_MADE_EFFECTS];} aw_made_item_t;
void AW_MadeReset(void);
int AW_MadeSpellCount(void);
int AW_MadeItemCount(void);
const aw_made_spell_t *AW_MadeSpellAt(int i);
const aw_made_item_t *AW_MadeItemAt(int i);
int AW_MadeSpellAdd(const aw_made_spell_t *s);     /* its index, -1 full, not valid or no memory */
int AW_MadeItemAdd(const aw_made_item_t *m);
/* the inventory's way to the made items (aw_inventory.c; set to AW_MadeItemAt by the script host) */
extern const aw_made_item_t *(*aw_inventory_made_item)(int index);
int AW_MadeExport(unsigned char *out,int capacity);
int AW_MadeImport(const unsigned char *p,int bytes);
/* Filled soul gems (bounded, saved: AWSG): the gem id and the soul's creature (ACTB row); its soul value. */
void AW_GemsReset(void);
int AW_GemCount(void);
int AW_GemAdd(const char *gem,int creature);
int AW_GemAt(int i,char *gem,int capacity,int *creature);
int AW_GemRemove(int i);
int AW_GemSoul(int i);
int AW_GemsExport(unsigned char *out,int capacity);
int AW_GemsImport(const unsigned char *p,int bytes);
/* Places a script revealed on the map (ShowMap TEXT: the exterior cells whose name holds it; bounded, saved: AWMP),
 * kept for the map's place markers. */
void AW_RevealedReset(void);
int AW_RevealedCount(void);
const char *AW_RevealedAt(int i);
int AW_RevealedAdd(const char *text);
int AW_RevealedExport(unsigned char *out,int capacity);
int AW_RevealedImport(const unsigned char *p,int bytes);
void AW_SoldReset(void);
int AW_SoldCount(void);
int AW_SoldMax(void);
int AW_SoldAt(int i,uint32_t *reference,char *id,int capacity,int *count);
int AW_SoldAdd(uint32_t reference,const char *id,int delta);
int AW_SoldExport(unsigned char *out,int capacity);
int AW_SoldImport(const unsigned char *p,int bytes);

/* Saved games: the changed records and the dead counts (a byte block, AWAS1). Export returns the bytes written
 * (0 nothing to save, -1 too small); Import returns 1, or 0 for a bad block (the pool is left empty). */
int AW_ActorStateExport(unsigned char *out,int capacity);
int AW_ActorStateImport(const unsigned char *data,int bytes);
/* Slice 6 (the save's world change list, aw_ledger.h RECORDS): the dead counts alone as an AWAS1 block (records 0), and
 * the changed records alone as "AWAR": u8 version (1) u8 0 u16 0 u32 records, then each record as in AWAS1. Export
 * returns the bytes (OUT NULL: the bytes needed; 0 nothing; -1 too small). ImportRecords adds the records to the pool
 * after an Import (a reference already there is replaced); 1 good (also for 0 bytes), 0 a bad block (nothing added). */
int AW_ActorStateExportCounts(unsigned char *out,int capacity);
int AW_ActorStateExportRecords(unsigned char *out,int capacity);
int AW_ActorStateImportRecords(const unsigned char *data,int bytes);
/* CELL-CHANGES-59 slice 7: a respawned actor's live record goes (1 when there was one); after a load of another build's
 * save, every changed record and dead count goes (how many). */
int AW_ActorForget(uint32_t reference);
int AW_ActorStateDropAll(void);
/* UNDERWATER-BREATH-62: how many times the pool (the player's record included) was emptied; a change = the
 * character's spells must be applied again */
unsigned long AW_ActorStateEpoch(void);
/* Live records now and changed ones (for the status line and the tests). */
int AW_ActorStateLive(int *changed);
const aw_actorstate_stats_t *AW_ActorStateStats(void);
/* Bytes held while open (the pool, the dead counts, the directory). */
unsigned long AW_ActorStateResident(void);
#endif
