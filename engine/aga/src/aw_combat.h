/* SPDX-License-Identifier: GPL-2.0-or-later
 * Melee combat for every NPC (docs/COMBAT.md). aw_combat_rules.c holds the
 * rules as pure functions (host tested); aw_combat.c runs them on edicts;
 * aw_arena.c is the Vivec Arena debug minigame that exercises them.
 *
 * The rules follow the original game's melee rules as the OpenMW engine
 * implements them (reference: OpenMW 0.51 apps/openmw/mwmechanics/combat.cpp,
 * creaturestats.cpp, mwclass/npc.cpp, files/data-mw/scripts/omw/combat/
 * local.lua). Independent code; the numbers come from the game settings in
 * the user's own master file at build time (combat/settings.txt).
 */
#ifndef AW_COMBAT_H
#define AW_COMBAT_H

/* Attribute and skill indices of the original data (NPDT order). */
enum {AW_STR,AW_INT,AW_WIL,AW_AGI,AW_SPD,AW_END,AW_PER,AW_LUC};
enum {
    AW_SK_BLOCK=0,AW_SK_ARMORER=1,AW_SK_MEDIUM=2,AW_SK_HEAVY=3,AW_SK_BLUNT=4,AW_SK_LONG=5,
    AW_SK_AXE=6,AW_SK_SPEAR=7,AW_SK_UNARMORED=17,AW_SK_LIGHT=21,AW_SK_SHORT=22,AW_SK_H2H=26
};
enum {AW_ATTACK_CHOP,AW_ATTACK_SLASH,AW_ATTACK_THRUST};
enum {AW_HIT_MISS,AW_HIT_BLOCKED,AW_HIT_FATIGUE,AW_HIT_HEALTH};

/* Game settings the rules read; names are the master file's GMST names. */
typedef struct {
    float fFatigueBase,fFatigueMult,fCombatDistance,fHandToHandReach;
    float fMinHandToHandMult,fMaxHandToHandMult,fHandtoHandHealthPer;
    float fDamageStrengthBase,fDamageStrengthMult,fCombatArmorMinMult,fCombatKODamageMult;
    float fCombatCriticalStrikeMult,fKnockDownMult,iKnockDownOddsBase,iKnockDownOddsMult;
    float fFatigueAttackBase,fFatigueAttackMult,fWeaponFatigueMult;
    float fFatigueReturnBase,fFatigueReturnMult,fUnarmoredBase1,fUnarmoredBase2;
    float iBlockMinChance,iBlockMaxChance,fSwingBlockBase,fSwingBlockMult,fBlockStillBonus;
    float fFatigueBlockBase,fFatigueBlockMult,fWeaponFatigueBlockMult;
    float fCombatBlockLeftAngle,fCombatBlockRightAngle,fCombatDelayNPC;
    float fNPCHealthBarTime,fNPCHealthBarFade;
} aw_combat_settings_t;
#define AW_COMBAT_SETTING_COUNT 35

/* One fighter's sheet: about 150 bytes. Values as the original data holds
 * them (attributes and skills 0..255, dynamic stats as floats). */
typedef struct {
    char id[32],name[32];
    short level;
    unsigned char attributes[8],skills[27];
    unsigned char fight,flee,shield;    /* shield: carries one (can block) */
    unsigned char weapon;               /* 0 hand to hand, else 1 + original weapon type */
    unsigned char weapon_skill;         /* skill index the weapon uses */
    unsigned char damage[3][2];         /* chop, slash, thrust: min, max */
    float reach,speed,weight,armor;     /* weapon reach/speed/weight; armour rating */
    float health,health_max,fatigue,fatigue_max,magicka;
    unsigned char knocked;              /* 1 knocked down (hit), 2 knocked out (fatigue) */
    unsigned char dead,aware,moving,attacking;
} aw_fighter_t;

/* Deterministic rolls: one xorshift32 per encounter (seeded). */
typedef struct {unsigned long state;} aw_combat_rng_t;
void AW_CombatSeed(aw_combat_rng_t *r,unsigned long seed);
int AW_CombatRoll100(aw_combat_rng_t *r);           /* 0..99, as roll0to99 */
float AW_CombatRoll01(aw_combat_rng_t *r);          /* 0..1 inclusive, as rollClosedProbability */

/* One resolved swing, for the readout and the HUD. */
typedef struct {
    int chance,roll,outcome,critical,knockdown,blocked_roll,block_chance;
    float strength,damage,raw;
} aw_swing_t;

int AW_CombatSettingIndex(const char *name);
int AW_CombatSettingSet(aw_combat_settings_t *s,const char *name,float value);
const char *AW_CombatSettingName(int index);
float AW_CombatFatigueTerm(const aw_combat_settings_t *s,const aw_fighter_t *f);
/* Hit chance in percent, not clamped (roll 0..99 below it hits). */
int AW_CombatHitChance(const aw_combat_settings_t *s,const aw_fighter_t *attacker,const aw_fighter_t *victim);
int AW_CombatBestAttack(const aw_fighter_t *f,aw_combat_rng_t *r);
float AW_CombatReach(const aw_combat_settings_t *s,const aw_fighter_t *f);  /* original units */
float AW_CombatUnarmoredRating(const aw_combat_settings_t *s,const aw_fighter_t *f);
/* The whole melee hit: roll, damage, block, armour, knockdown, fatigue loss
 * of the attacker; applies the result to both sheets. angle: attacker's
 * bearing from the victim's facing in degrees (-180..180; for blocking);
 * still: the victim is not walking (block bonus). */
void AW_CombatSwing(const aw_combat_settings_t *s,aw_fighter_t *attacker,aw_fighter_t *victim,
                    int attack,float strength,float angle,int still,aw_combat_rng_t *r,aw_swing_t *out);
/* Fatigue return per second of game time; knocked-out fighters stand when
 * fatigue is back above zero. Returns 1 when the fighter got up. */
int AW_CombatRecover(const aw_combat_settings_t *s,aw_fighter_t *f,float seconds);

/* One encounter's totals (the arena's result screen). */
typedef struct {
    unsigned long seed;
    double started,ended,player_down_until;
    int won;
    int player_swings,player_hits,player_misses,npc_swings,npc_hits,npc_misses,npc_flees;
    float dealt_health,dealt_fatigue,taken_health,taken_fatigue;
} aw_combat_stats_t;

/* aw_combat.c: the engine side. */
extern aw_combat_settings_t aw_combat_settings;
int AW_CombatSettingsLoad(void);
int AW_CombatActorLoad(const char *id,aw_fighter_t *out);
void AW_CombatPlayerSheet(aw_fighter_t *out);
void AW_CombatInit(void);
void AW_CombatPhysics(void);
void AW_CombatSceneSpawn(void);
int AW_CombatEnemyBar(float *fraction,float *alpha);
int AW_CombatHostiles(void);
struct edict_s;
int AW_CombatEngage(struct edict_s *e,const aw_fighter_t *fighter,const char *layout);
const aw_fighter_t *AW_CombatFighter(struct edict_s *e);
void AW_CombatClear(void);
const aw_combat_stats_t *AW_CombatStats(void);
const aw_fighter_t *AW_CombatPlayer(void);
unsigned long AW_CombatSeedUsed(void);
extern void (*aw_combat_result)(int won);
#endif
