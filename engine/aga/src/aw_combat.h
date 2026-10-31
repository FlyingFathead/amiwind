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
#include "aw_actorstate.h"

/* Attribute and skill indices of the original data (NPDT order). */
enum {AW_STR,AW_INT,AW_WIL,AW_AGI,AW_SPD,AW_END,AW_PER,AW_LUC};
enum {
    AW_SK_BLOCK=0,AW_SK_ARMORER=1,AW_SK_MEDIUM=2,AW_SK_HEAVY=3,AW_SK_BLUNT=4,AW_SK_LONG=5,
    AW_SK_AXE=6,AW_SK_SPEAR=7,AW_SK_UNARMORED=17,AW_SK_LIGHT=21,AW_SK_SHORT=22,AW_SK_H2H=26
};
enum {AW_ATTACK_CHOP,AW_ATTACK_SLASH,AW_ATTACK_THRUST};
enum {AW_HIT_MISS,AW_HIT_BLOCKED,AW_HIT_FATIGUE,AW_HIT_HEALTH};
/* Combat voice events (aw_combat_voice): the fight starts (once, on the calm to
 * hostile transition: the aggro line), the NPC swings (a taunt/attack chance),
 * it takes a hit, it flees, it dies. No event but DEATH follows a death. The
 * receiver owns the speech rules: the original odds, a taunt cooldown, no
 * repeat or overlap per actor, DEATH and HIT over taunts, a bound on voices
 * at once (docs/ROADMAP.md, combat speech). */
enum {AW_VOICE_START,AW_VOICE_SWING,AW_VOICE_HIT,AW_VOICE_FLEE,AW_VOICE_DEATH};

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
    float fNPCHealthBarTime,fNPCHealthBarFade,fWeaponDamageMult;
} aw_combat_settings_t;
#define AW_COMBAT_SETTING_COUNT 36

/* The aggro and flee ratings' game settings (combat/settings.txt "ai NAME VALUE" lines, tools/prepare_combat.py AI_SETTINGS;
 * the master file's GMST names). Kept apart from the melee settings: an image without them still fights, only the
 * aggro and flee rules are unavailable. */
typedef struct {
    float iFightDistanceBase,fFightDistanceMultiplier,fFightDispMult;
    float fAIFleeHealthMult,fAIFleeFleeMult,fAIMeleeWeaponMult,fAIMeleeArmorMult;
} aw_combat_ai_t;
#define AW_COMBAT_AI_COUNT 7
int AW_CombatAiSet(aw_combat_ai_t *a,const char *name,float value);
const char *AW_CombatAiName(int index);

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
    unsigned char staggered;            /* hit recovery: cannot block */
    unsigned char shield_class;         /* 0 light, 1 medium, 2 heavy (its block sound) */
    unsigned char block_off;            /* not ready to block (OpenMW isReadyToBlock): the player not
                                           holding the block button with aw_combat_block 1 (AmiWind extension) */
    unsigned char creature;             /* 0 an NPC or the player; 1 a creature striking with its own attacks
                                           (damage = its record's chop/slash/thrust); 2 a bipedal creature (hand to
                                           hand, its combat skill); AW_CombatCreatureSheet */
    unsigned int hit_classes;           /* the armour a blow can land on, 2 bits per AW_CombatArmorHitSlot slot: 0 none,
                                           1 light, 2 medium, 3 heavy (its hit sound; sheet field 12); AW_HIT_CLASS */
    float weapon_health,weapon_health_max,shield_health,shield_health_max;  /* condition; max 0 = unknown (full) */
} aw_fighter_t;
#define AW_HIT_CLASS(f,slot) ((int)(((f)->hit_classes>>(2*(slot)))&3u))
/* Two-handed weapon types (and hand to hand, which OpenMW's weapon table also marks
 * two-handed): no shield block. weapon = 1 + original type. */
#define AW_TWO_HANDED(w) ((w)==0 || (w)==3 || (w)==5 || (w)==6 || (w)==7 || (w)==9)

/* Deterministic rolls: one xorshift32 per encounter (seeded). */
typedef struct {unsigned long state;} aw_combat_rng_t;
void AW_CombatSeed(aw_combat_rng_t *r,unsigned long seed);
int AW_CombatRoll100(aw_combat_rng_t *r);           /* 0..99, as roll0to99 */
float AW_CombatRoll01(aw_combat_rng_t *r);          /* 0..1 inclusive, as rollClosedProbability */

/* One resolved swing, for the readout and the HUD. */
typedef struct {
    int chance,roll,outcome,critical,knockdown,blocked_roll,block_chance;
    int miss_style;                     /* a miss: 1 dodge, 2 block-like (AmiWind extension presentation) */
    int weapon_broke,shield_broke;
    float strength,damage,raw,weapon_wear;
} aw_swing_t;
/* aw_combat_dice: 1 (default) the original rolls; 0 (AmiWind extension) no dice:
 * every swing in reach hits, nothing is blocked, knockdown by the damage threshold
 * alone, NPC swing strength the mean. docs/COMBAT.md. */
extern int aw_combat_dice;
int AW_CombatCanBlock(const aw_combat_settings_t *s,const aw_fighter_t *v,float angle);
int AW_CombatBestAttackPlayer(const aw_fighter_t *f);
int AW_CombatMovementAttack(float forward,float side);

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
/* The sounds of one melee swing (docs/COMBAT.md "Sounds"): combat/settings.txt "sound KEY PATH" keys in this order. */
enum {AW_SND_HEALTH,AW_SND_MISS,AW_SND_PUNCH,AW_SND_LIGHT,AW_SND_MEDIUM,AW_SND_HEAVY,AW_SND_SWISH,AW_SND_CRITICAL,
      AW_SND_FALL,AW_SND_PUNCH2,AW_SND_COUNT};
#define AW_ARMOR_HIT_SLOTS 9
/* The armour slot a blow lands on for a roll 0..99 (OpenMW 0.51 files/data-mw/scripts/omw/combat/local.lua
 * pickRandomArmor): cuirass under 30, then helmet, greaves, boots, left and right pauldron (10 each), left and right
 * gauntlet (5 each), the shield from 90. */
int AW_CombatArmorHitSlot(int roll100);
/* The sounds of a resolved swing into SOUNDS (at most 4), returns how many (OpenMW 0.51): every melee swing its swing
 * sound (mwmechanics/character.cpp prepareHit, playSwishSound "Weapon Swish"); a block the shield's armour hit sound
 * (combat.cpp blockMeleeAttack); a miss "miss" only for the player's swing (combat/local.lua onHit); hand to hand
 * without health damage "Hand To Hand Hit" or "Hand To Hand Hit 2" (combat.cpp getHandToHandDamage); health damage
 * the armour hit sound of the piece the blow lands on (none for an empty slot; local.lua applyArmor), "Health
 * Damage" (local.lua onHit) and "critical damage" on a critical strike (mwclass/npc.cpp hit). ROLL picks the slot
 * and the punch sound; out NULL = a swing that reached nobody. */
int AW_CombatSwingSounds(const aw_swing_t *out,const aw_fighter_t *victim,int by_player,unsigned long roll,int *sounds);
/* A creature's fighter sheet from its actor record row (kind 1; docs/ACTOR_STATE.md), OpenMW 0.51 mwclass/creature.cpp:
 * the record's level, attributes, health, fatigue and magicka, Fight and Flee; every combat skill its combat value
 * (getSkill by specialization, as the actor record stores it); no armour (getArmorRating: equipment ignored, only the
 * Shield effect); its attacks as the chop, slash and thrust damage (hit: min + (max - min) x strength, health damage,
 * no strength modifier and no condition), a bipedal one punching by hand to hand instead. Carried weapons are not
 * read yet: a creature with one fights with its own attacks. 0 when ROW is not a creature. ID names the sheet. */
int AW_CombatCreatureSheet(const aw_actor_base_t *row,const char *id,aw_fighter_t *out);
/* Fatigue return per second of game time; knocked-out fighters stand when
 * fatigue is back above zero. Returns 1 when the fighter got up. */
int AW_CombatRecover(const aw_combat_settings_t *s,aw_fighter_t *f,float seconds);

/* Aggro: the effective Fight of an actor toward the player (OpenMW 0.51 mechanicsmanagerimp.cpp isAggressive with
 * combat.cpp getFightDistanceBias and getFightDispositionBias): Fight + (int)(iFightDistanceBase -
 * fFightDistanceMultiplier x distance + (50 - disposition) x fFightDispMult); hostile at 100 or more. distance in
 * original units; disposition 50 for a creature (and, until the actor record carries it, for an NPC). */
int AW_CombatFightRating(const aw_combat_ai_t *a,int fight,int disposition,float distance);
/* Flee (OpenMW aicombataction.cpp vanillaRateFlee and makeFleeDecision): Flee >= 100 rates Flee itself; else
 * (1 - health / maximum) x fAIFleeHealthMult + Flee x fAIFleeFleeMult, plus the distance bias when not zero; a
 * rating under 100 counts as 0. The fighter flees when it beats the rating of its best action: hand to hand 0, a
 * melee weapon armour rating x fAIMeleeArmorMult + its best maximum damage x skill / 100 x fAIMeleeWeaponMult
 * (weaponpriority.cpp vanillaRateWeaponAndAmmo). */
float AW_CombatFleeRating(const aw_combat_ai_t *a,const aw_fighter_t *f,float distance);
float AW_CombatAntiFleeRating(const aw_combat_ai_t *a,const aw_fighter_t *f);
int AW_CombatFleeDecision(const aw_combat_ai_t *a,const aw_fighter_t *f,float distance);

/* One encounter's totals (the arena's result screen). */
typedef struct {
    unsigned long seed;
    double started,ended,player_down_until;
    int won;
    int player_swings,player_hits,player_misses,npc_swings,npc_hits,npc_misses,npc_flees;
    float dealt_health,dealt_fatigue,taken_health,taken_fatigue;
    unsigned long player_blocks,npc_blocks,guards;   /* blocked blows (the player's, the NPCs'), block button presses with a shield */
} aw_combat_stats_t;

/* aw_combat.c: the engine side. */
extern aw_combat_settings_t aw_combat_settings;
extern aw_combat_ai_t aw_combat_ai;
int AW_CombatSettingsLoad(void);
int AW_CombatAiLoaded(void);            /* every "ai" line was in combat/settings.txt */
/* The combat layer's rule switches (dbg combat flee|sounds on/off; plain switches, not console variables: the
 * resident registry budget). AW_RULE_FLEE: flee by the Flee rating (OpenMW aicombataction.cpp makeFleeDecision);
 * AW_RULE_SOUNDS: the swing's sounds by AW_CombatSwingSounds. Both off by default (A/B); the combat playground switches
 * them on for its session. ON < 0 only reads; returns the value before the call. */
enum {AW_RULE_FLEE,AW_RULE_SOUNDS,AW_RULE_COUNT};
int AW_CombatRule(int rule,int on);
/* Combat sound KEY (AW_SND_*): its file (sound/ relative, "" when the image has none) and playing it locally. */
const char *AW_CombatSoundPath(int key);
int AW_CombatSoundPlay(int key);
struct edict_s;
/* Aggro on sight (the combat playground; the world's residents follow when the actor record carries Fight): the
 * effective Fight of E toward the player at their distance, and when it reaches 100 and E sees the player
 * (OpenMW Actors::engageCombat: getLOS, awarenessCheck; a player who is not sneaking is always noticed) E starts
 * fighting with SHEET and LAYOUT (AW_CombatEngage). Returns 1 when E fights (now or already), 0 when it stays
 * calm, -1 when the rule cannot run (no player, no ai settings). *rating and *distance (original units) get the
 * numbers; either may be NULL. */
int AW_CombatAggro(struct edict_s *e,const aw_fighter_t *sheet,const char *layout,int disposition,int *rating,float *distance);
/* A fighting actor that runs from the player (its Flee rating or no route to the player). */
int AW_CombatActorFleeing(struct edict_s *e);
/* The measured cost of the fighters' thinks: thinks per second since the encounter began, the mean and the
 * longest think in milliseconds, the fighters now in slots. */
void AW_CombatCost(float *per_second,float *ms_mean,float *ms_max,int *fighters);
int AW_CombatActorLoad(const char *id,aw_fighter_t *out);
void AW_CombatPlayerSheet(aw_fighter_t *out);
extern void (*aw_combat_equipment)(aw_fighter_t *sheet);
extern void (*aw_combat_equipment_store)(const aw_fighter_t *sheet);
void AW_CombatEquipmentStore(void);
/* The movement rules' view of the player (aw_move.c): knocked down/out, the one fatigue value
 * (and its maximum), and a fatigue loss (never below 0 unless already there). */
int AW_CombatPlayerKnocked(void);
float AW_CombatPlayerFatigue(float *maximum);
void AW_CombatPlayerFatigueLoss(float loss);
void AW_CombatEquipmentChanged(void);
int AW_CombatLoadout(const char *loadout,aw_fighter_t *out,char *chosen);
extern int (*aw_combat_input_locked)(void);
/* The held block (AmiWind extension, aw_combat_block 1, docs/COMBAT.md "Blocking"): 1 while the player
 * guards with a usable shield; the third-person body plays its block group meanwhile (aw_view.c). */
int AW_CombatGuarding(void);
/* The body's block clip after a blow was blocked: seconds left, 0 = none. */
float AW_CombatBlockShown(void);
extern const aw_fighter_t *aw_combat_player_preset;
void AW_CombatInit(void);
void AW_CombatPhysics(void);
int AW_CombatHurtPlayer(float damage,const char *cause);  /* world damage (lava); 1 = died now */
void AW_CombatSceneSpawn(void);
int AW_CombatEnemyBar(float *fraction,float *alpha);
int AW_CombatHostiles(void);
/* Someone fights the player and the player is alive: the battle music and the wait refusal ask this one check. */
int AW_PlayerInCombat(void);
struct edict_s;
int AW_CombatEngage(struct edict_s *e,const aw_fighter_t *fighter,const char *layout);
/* THE hand-off between combat and the other actor layers (ambient wander/idles, MWScript): one check, one end, one
 * notice. AW_CombatActorState: 0 = not in combat (the other layers own the actor), 1 = fighting (combat owns its
 * movement, frame and think; others yield), 2 = died in combat (nobody resumes it). AW_CombatActorEnd: ends this
 * actor's fight (StopCombat): its own think comes back, its carried items go; 1 when it was in combat.
 * aw_combat_actor_released (NULL = none): called once whenever an actor leaves combat alive (calm, end, the slot
 * given back), so a yielding layer resumes it there and nowhere else. */
int AW_CombatActorState(struct edict_s *e);
int AW_CombatActorEnd(struct edict_s *e);
extern void (*aw_combat_actor_released)(struct edict_s *e);
/* aw_combat_actor_died (NULL = none): called when a fallen fighter's slot is taken for a new fighter (more hostiles
 * than slots), so the owner records the death before the slot forgets it (aw_actors.c: the change list). */
extern void (*aw_combat_actor_died)(struct edict_s *e);
const aw_fighter_t *AW_CombatFighter(struct edict_s *e);
/* An engaged NPC's current swing: 0 chop, 1 slash, 2 thrust; -1 when it is not fighting (aw_animkit.c picks the
 * attack's keys by it, ANIM-GROUPS-NOT-HOOKED-54). */
int AW_CombatAttackType(struct edict_s *e);
void AW_CombatClear(void);
const aw_combat_stats_t *AW_CombatStats(void);
const aw_fighter_t *AW_CombatPlayer(void);
unsigned long AW_CombatSeedUsed(void);
extern void (*aw_combat_result)(int won);
extern void (*aw_combat_voice)(struct edict_s *e,int event);
/* An engaged NPC's health in percent (its fighter sheet), or -1 when it is not fighting (aw_anim.c voices). */
int AW_CombatHealthPercent(struct edict_s *e);
/* The death scene (aw_view.c): the quick retry of a lost fight (an AmiWind extension) and whether the
 * fight's own death music plays. */
int AW_CombatRetryAvailable(void);
int AW_CombatRetry(void);
int AW_CombatDeathMusicPlayed(void);
#endif
