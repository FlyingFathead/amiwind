/* SPDX-License-Identifier: GPL-2.0-or-later
 * Crime (CRIME-59; STEAL-WITNESSED-NO-CRIME-61; docs/GAME_FORMULAS.md "Crime, sneaking, locks and detection"): taking an
 * owned item where a witness sees it.
 *
 * The rules are the original's as OpenMW 0.51 implements them (apps/openmw/mwmechanics/mechanicsmanagerimp.cpp
 * itemTaken, commitCrime, canReportCrime, reportCrime, awarenessCheck; combat.cpp getFightDistanceBias), written
 * independently; every number is a game setting read from the player's own master at build time
 * (combat/settings.txt "crime NAME VALUE" lines, tools/prepare_combat.py CRIME_SETTINGS).
 *
 *   commitCrime   the NPCs within fAlarmRadius of the player (and the victim, the owner, wherever it stands) that
 *                 can report (alive, not knocked down, not fighting the victim) and have the player in sight (a line
 *                 of sight through the world, then the awareness roll; a player who does not sneak is always
 *                 noticed) are the witnesses; each says its Thief line.
 *   reportCrime   seen: when any NPC in the alarm radius has Alarm 100 or more, the bounty rises by
 *                 max(1, value x fCrimeStealing) and the game says sCrimeMessage. Every NPC in the radius reacts:
 *                 a guard with Alarm 100 is alarmed (pursuit to arrest comes with the guards' package, CRIME-59);
 *                 anyone else adds (fFightStealing x value + the disposition bias + the distance bias) x Alarm / 100
 *                 to its Fight and attacks when that reaches 100.
 *
 * aw_crime_rules.c holds the rules as pure functions (host tested, tests/aga_crime_rules_test.c); aw_crime.c runs
 * them on the world's NPCs. Nothing resident but the settings (about 60 bytes, read once at the first theft). */
#ifndef AW_CRIME_H
#define AW_CRIME_H

/* The game settings the crime rules read (the master file's GMST names; tools/prepare_combat.py CRIME_SETTINGS in
 * this order). */
typedef struct {
    float fAlarmRadius,fCrimeStealing,fDispStealing,fFightStealing;
    float fSneakSkillMult,fSneakBootMult,fSneakDistanceBase,fSneakDistanceMultiplier,fSneakNoViewMult,fSneakViewMult;
    float iCrimeThreshold;
} aw_crime_settings_t;
#define AW_CRIME_SETTING_COUNT 11
int AW_CrimeSettingSet(aw_crime_settings_t *s,const char *name,float value);
const char *AW_CrimeSettingName(int index);

/* The thief's side of the awareness check (OpenMW awarenessCheck: ptr). */
typedef struct {
    int sneaking;                       /* the sneak key held (AW_MoveSneaking) */
    float sneak,agility,luck;           /* modified skill and attributes */
    float boot_weight;                  /* the worn boots' weight while on the ground, else 0 */
    float fatigue_term;                 /* getFatigueTerm: fFatigueBase - fFatigueMult x (1 - fatigue / maximum) */
    float chameleon,invisibility;       /* the effects' magnitudes on the player */
} aw_crime_thief_t;
/* The observer's side. */
typedef struct {
    float sneak,agility,luck,blind,fatigue_term;
    int behind;                         /* the thief is more than 90 degrees off the observer's facing */
} aw_crime_observer_t;
/* The awareness target (OpenMW awarenessCheck: x - y); the observer notices the thief when its roll 0..99 is at
 * least this. DISTANCE in original units. Pure. */
float AW_CrimeAwarenessTarget(const aw_crime_settings_t *s,const aw_crime_thief_t *t,const aw_crime_observer_t *o,
                              float distance);
/* reportCrime's bounty for a theft of VALUE (count x the item's value; gold: the count): max(1, value x
 * fCrimeStealing). Pure. */
int AW_CrimeTheftBounty(const aw_crime_settings_t *s,int value);
/* reportCrime's theft reaction of a witness that is not an alarmed guard: the Fight it adds (0 when none), from
 * fFightStealing x VALUE, the disposition bias of its disposition change (fDispStealing x VALUE; the bias is
 * (50 - change) x FIGHT_DISP_MULT), the distance bias (DISTANCE_BASE - DISTANCE_MULT x DISTANCE, original units),
 * all times ALARM / 100 and capped at 100 - FIGHT. It attacks when FIGHT + the result reaches 100. Pure. */
float AW_CrimeTheftFight(const aw_crime_settings_t *s,int value,int fight,int alarm,float distance,
                         float fight_disp_mult,float distance_base,float distance_mult);
/* reportCrime: the crime is reported when a witness in the radius has Alarm 100 or more. Pure. */
#define AW_CRIME_REPORTS(alarm) ((alarm)>=100)
/* The awareness roll an observer keeps (OpenMW 0.51 creaturestats.cpp getAwarenessRoll and updateAwareness: rolled
 * 0..99 when asked, kept until 5 seconds have passed), in a small table by the observer's KEY; NOW in seconds (a NOW
 * before the stored time, a new map's clock, is no match). Pure. */
#define AW_CRIME_ROLL_SECONDS 5.0
typedef struct {int key,roll;double at;} aw_crime_roll_t;
int AW_CrimeRollFind(const aw_crime_roll_t *table,int count,int key,double now);   /* the kept roll, -1 none */
void AW_CrimeRollKeep(aw_crime_roll_t *table,int count,int key,int roll,double now);   /* an expired or the oldest slot */

/* aw_crime.c, the engine side. */
struct edict_s;
/* The facts of one NPC for the rules (the host fills them from its actor record, aw_mwhost.c). */
typedef struct {
    int alarm,fight,guard,can_report;   /* can_report: an NPC, alive, not knocked down */
    aw_crime_observer_t observer;
} aw_crime_witness_t;
extern int (*aw_crime_witness)(struct edict_s *e,aw_crime_witness_t *out);   /* 0: not an NPC that can witness */
extern int (*aw_crime_attack)(struct edict_s *e,int fight);                  /* the witness's new Fight; it attacks */
extern void (*aw_crime_thief)(aw_crime_thief_t *out);                        /* the player's side, by the host *//* The player took VALUE worth of something OWNER owns (an NPC record id, or a faction when FACTION): the crime as
 * commitCrime decides it. Returns the witnesses who saw it (0: no crime). */
int AW_CrimeTheft(const char *owner,int faction,int value);
/* The value of taking COUNT of item ID worth VALUE each: gold counts its pieces (OpenMW itemTaken isGold). */
int AW_CrimeTakenValue(const char *id,int count,int value);
/* Counters and the last crime for `dbg crime` (the console). */
void AW_CrimeInit(void);
/* MWSCRIPT-SMALL-FUNCTIONS-62, GetLOS and GetDetected (OpenMW 0.51 World::getLOS; actors.cpp isActorDetected;
 * mechanicsmanagerimp.cpp awarenessCheck): FROM sees TO eye to eye through the world (actors do not block; a hidden,
 * disabled one is never seen nor sees); OBSERVER notices ACTOR when it sees it and its kept roll is at least the
 * awareness target (the settings of the crime rules; without them every seen actor is noticed). */
int AW_CrimeSight(struct edict_s *from,struct edict_s *to);
int AW_CrimeDetects(struct edict_s *observer,const aw_crime_observer_t *o,struct edict_s *actor,const aw_crime_thief_t *t);
#endif
