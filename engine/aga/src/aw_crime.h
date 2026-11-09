/* SPDX-License-Identifier: GPL-2.0-or-later
 * Crime (CRIME-59; STEAL-WITNESSED-NO-CRIME-61; docs/GAME_FORMULAS.md "Crime, sneaking, locks and detection"): the
 * player's crimes, their witnesses, the bounty, the guards' arrest, the fine and jail.
 *
 * The rules are the original's as OpenMW 0.51 implements them (apps/openmw/mwmechanics/mechanicsmanagerimp.cpp
 * itemTaken, commitCrime, canReportCrime, reportCrime, actorAttacked, canCommitCrimeAgainst, actorKilled,
 * awarenessCheck, sleepInBed; actors.cpp the guards' arrest on sight and the calm after a fine; aipursue.cpp;
 * mwworld/worldimp.cpp goToJail, confiscateStolenItems, updateDialogueGlobals; mwgui/jailscreen.cpp;
 * mwscript/miscextensions.cpp OpPayFine, OpPayFineThief, OpGoToJail; statsextensions.cpp OpOnMurder; the jail's skill
 * rule of files/data-mw/scripts/omw/playerskillhandlers.lua), written independently; every number is a game setting
 * read from the player's own master at build time (combat/settings.txt "crime NAME VALUE" lines,
 * tools/prepare_combat.py CRIME_SETTINGS).
 *
 *   commitCrime   the NPCs within fAlarmRadius of the player (and the victim, wherever it stands) that can report
 *                 (alive, not knocked down, not fighting the victim) and either are the victim of an assault (it knows
 *                 who hit it), hear a murder (any NPC but the victim) or have the player in sight (a line of sight
 *                 through the world, then the awareness roll; a player who does not sneak is always noticed) are the
 *                 witnesses; for a theft each says its Thief line. An assault nobody reports: the victim fights back.
 *   reportCrime   reported when any NPC in the radius has Alarm 100 or more (for trespass each of those says
 *                 Intruder): the bounty rises by the kind's setting and the game says sCrimeMessage. Every NPC in the
 *                 radius reacts: its disposition changes (for a while, or for good for a victim), a guard with Alarm
 *                 100 is alarmed and pursues to arrest, anyone else adds the kind's Fight with the disposition and
 *                 distance biases, x Alarm / 100, and attacks when that reaches 100. Each one that reacted keeps the
 *                 crime's number, so paying the fine calms it again. A murder marks the victim for OnMurder.
 *   arrest        an alarmed guard runs to the player and talks (the guard's greeting offers the fine, jail or
 *                 resisting); a guard that notices a player whose bounty is iCrimeThreshold or more pursues on sight,
 *                 at iCrimeThreshold x iCrimeThresholdMultiplier it attacks.
 *   PayFine       bounty 0, the stolen goods taken (into the nearest prison's evidence chest), every witness calmed.
 *   PayFineThief  bounty 0, witnesses calmed (the thieves' fixer: the goods stay).
 *   GotoJail      bounty 0, goods taken, witnesses calmed; max(1, bounty / iDaysinPrisonMod) days pass (rested), one
 *                 random skill a day falls by one (Security and Sneak rise instead), and the player is let out at the
 *                 nearest prison marker.
 *
 * aw_crime_rules.c holds the rules as pure functions (host tested, tests/aga_crime_rules_test.c); aw_crime.c runs
 * them on the world's NPCs. */
#ifndef AW_CRIME_H
#define AW_CRIME_H

/* The game settings the crime rules read (the master file's GMST names; tools/prepare_combat.py CRIME_SETTINGS in
 * this order). The first AW_CRIME_THEFT_SETTINGS are the theft's (an image built before v0.0.62 has those only: then
 * thefts alone are crimes). */
typedef struct {
    float fAlarmRadius,fCrimeStealing,fDispStealing,fFightStealing;
    float fSneakSkillMult,fSneakBootMult,fSneakDistanceBase,fSneakDistanceMultiplier,fSneakNoViewMult,fSneakViewMult;
    float iCrimeThreshold;
    /* v0.0.62 (CRIME-59): the other crimes, the arrest and jail */
    float iCrimeAttack,iCrimeKilling,iCrimeTresspass,iCrimePickPocket;
    float iDispAttackMod,fDispAttacking,iDispKilling,iDispTresspass,fDispPickPocketMod;
    float iFightAttack,iFightAttacking,iFightKilling,iFightTrespass,iFightPickpocket;
    float iDaysinPrisonMod,iCrimeThresholdMultiplier,fCrimeGoldDiscountMult,fCrimeGoldTurnInMult;
} aw_crime_settings_t;
#define AW_CRIME_THEFT_SETTINGS 11
#define AW_CRIME_SETTING_COUNT 29
int AW_CrimeSettingSet(aw_crime_settings_t *s,const char *name,float value);
const char *AW_CrimeSettingName(int index);

/* The kinds of crime (OpenMW MechanicsManager::OffenseType). */
enum {AW_CRIME_THEFT,AW_CRIME_PICKPOCKET,AW_CRIME_TRESPASS,AW_CRIME_ASSAULT,AW_CRIME_MURDER,AW_CRIME_BED,AW_CRIME_KINDS};
const char *AW_CrimeKindName(int kind);

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
/* reportCrime's bounty of any KIND (ARG: a theft's value): iCrimeTresspass (trespass, an owned bed), iCrimePickPocket,
 * iCrimeAttack, iCrimeKilling, the theft's above. Pure. */
int AW_CrimeBounty(const aw_crime_settings_t *s,int kind,int arg);
/* reportCrime's theft reaction of a witness that is not an alarmed guard: the Fight it adds (0 when none), from
 * fFightStealing x VALUE, the disposition bias of its disposition change (fDispStealing x VALUE; the bias is
 * (50 - change) x FIGHT_DISP_MULT), the distance bias (DISTANCE_BASE - DISTANCE_MULT x DISTANCE, original units),
 * all times ALARM / 100 and capped at 100 - FIGHT. It attacks when FIGHT + the result reaches 100. Pure. */
float AW_CrimeTheftFight(const aw_crime_settings_t *s,int value,int fight,int alarm,float distance,
                         float fight_disp_mult,float distance_base,float distance_mult);
/* reportCrime: the crime is reported when a witness in the radius has Alarm 100 or more. Pure. */
#define AW_CRIME_REPORTS(alarm) ((alarm)>=100)

/* reportCrime's reaction of one NPC in the alarm radius to a crime of KIND (ARG: a theft's value), for every kind. */
typedef struct {
    int alarm,fight;                    /* its Alarm and Fight ratings (the base: getBase) */
    int guard,victim;                   /* of class Guard; the crime's victim */
    int disposition;                    /* its derived disposition now (0..100) */
    float distance;                     /* to the player, original units */
} aw_crime_react_in_t;
typedef struct {
    int disposition;                    /* the disposition change (already kept within 0..100 of the disposition) */
    int permanent;                      /* 1: its base disposition changes (a victim), 0: the crime's temporary one */
    int alarmed;                        /* marked Alarmed for the dialogue */
    int pursue;                         /* an alarmed guard: it pursues to arrest */
    int attack;                         /* it attacks the player */
    int fight;                          /* its new Fight rating when it attacks */
    int crime_id;                       /* 1: it keeps the crime's number (calmed when the fine is paid) */
} aw_crime_react_t;
void AW_CrimeReact(const aw_crime_settings_t *s,int kind,int arg,const aw_crime_react_in_t *in,
                   float fight_disp_mult,float distance_base,float distance_mult,aw_crime_react_t *out);
/* commitCrime's witness test for one NPC that can report: the victim of an assault always knows (VICTIM_AWARE), a
 * murder is heard by every NPC but the victim, anything else needs SEEN (the line of sight and the awareness roll). */
int AW_CrimeWitness(int kind,int is_victim,int victim_aware,int seen);
/* canCommitCrimeAgainst: hitting or killing an NPC is a crime unless it is aggressive toward the player (its Fight
 * rating with the disposition and distance biases at 100 or more, or already fighting), engaged, pursuing, a werewolf
 * or a vampire. AGGRESSIVE as isAggressive works it out. */
int AW_CrimeCanCommitAgainst(int npc,int aggressive,int engaged,int pursuing,int werewolf,int vampire);
/* actorKilled: the player's killing of an NPC is a murder when it could commit a crime against it at the blow or the
 * victim keeps a crime's number (it reacted to one of the player's crimes: an assault on it, a theft it saw). */
int AW_CrimeIsMurder(int npc,int by_player,int can_commit,int crime_id);
/* goToJail: the days of a sentence for BOUNTY, max(1, bounty / iDaysinPrisonMod). */
int AW_CrimeJailDays(const aw_crime_settings_t *s,int bounty);
/* The jail's skill rule (playerskillhandlers.lua jailTimeServed): one skill a day, picked by the roll; Security (18)
 * and Sneak (19) rise by one (to 100), any other falls by one (to 0). The change to SKILL at BASE (+1, -1 or 0). */
int AW_CrimeJailSkill(int skill,int base);
/* updateDialogueGlobals: OUT[0] PCHasCrimeGold, [1] PCHasGoldDiscount, [2] CrimeGoldDiscount, [3] CrimeGoldTurnIn,
 * [4] PCHasTurnIn for BOUNTY and the player's GOLD. */
void AW_CrimeGoldGlobals(const aw_crime_settings_t *s,int bounty,int gold,int out[5]);
/* The guards on sight (actors.cpp): 0 nothing, 1 pursue to arrest (bounty at iCrimeThreshold), 2 attack (at
 * iCrimeThreshold x iCrimeThresholdMultiplier). */
int AW_CrimeGuardSight(const aw_crime_settings_t *s,int bounty);

/* The awareness roll an observer keeps (OpenMW 0.51 creaturestats.cpp getAwarenessRoll and updateAwareness: rolled
 * 0..99 when asked, kept until 5 seconds have passed), in a small table by the observer's KEY; NOW in seconds (a NOW
 * before the stored time, a new map's clock, is no match). Pure. */
#define AW_CRIME_ROLL_SECONDS 5.0
typedef struct {int key,roll;double at;} aw_crime_roll_t;
int AW_CrimeRollFind(const aw_crime_roll_t *table,int count,int key,double now);   /* the kept roll, -1 none */
void AW_CrimeRollKeep(aw_crime_roll_t *table,int count,int key,int roll,double now);   /* an expired or the oldest slot */

/* What the crime rules keep of an NPC (OpenMW NpcStats crime id, crime disposition modifier, CreatureStats alarmed,
 * murdered; the pursuit package), by its placed reference; a fixed table, the oldest calmed row reused. Pure. */
#define AW_CRIME_ACTORS 32
typedef struct {
    unsigned long ref;                  /* 0: a free row */
    int crime_id;                       /* -1: none */
    short disposition;                  /* the crime's temporary disposition change */
    unsigned char alarmed,murdered,pursue,attacked;
    int walk_edict;                     /* not saved: the edict the pursuit's walk was started on (0 none) */
} aw_crime_actor_t;
/* CRIME-SAVE-PURSUERS-62: the rows in a saved game (OpenMW keeps NpcStats' crime id and crime disposition, CreatureStats'
 * alarmed and murdered flags and the AiPursue package): "AWCR", version 1, the row count, then 12 bytes a row (u32
 * reference, s32 crime id, s16 disposition, flags 1 alarmed 2 murdered 4 pursues 8 attacked, 0), big-endian; only
 * rows that hold something. Pack: the bytes written, -1 when CAPACITY is short. Unpack: the table emptied, then
 * filled; the bytes read, -1 when the block is not one (the table left empty). */
#define AW_CRIME_SAVE_ROW 12
int AW_CrimeActorsPack(const aw_crime_actor_t *table,int count,unsigned char *out,int capacity);
int AW_CrimeActorsUnpack(aw_crime_actor_t *table,int count,const unsigned char *in,int bytes);
aw_crime_actor_t *AW_CrimeActorFind(aw_crime_actor_t *table,int count,unsigned long ref);
aw_crime_actor_t *AW_CrimeActorMake(aw_crime_actor_t *table,int count,unsigned long ref);   /* NULL: full */
/* PayFine / PayFineThief / GotoJail (recordCrimeId) and the calm of actors.cpp: every row whose crime is PAID or older
 * is calmed (crime id -1, not alarmed, no disposition change, no pursuit); the count of rows calmed. */
int AW_CrimeActorsCalm(aw_crime_actor_t *table,int count,int paid);

/* aw_crime.c, the engine side. */
struct edict_s;
/* The facts of one NPC for the rules (the host fills them from its actor record, aw_mwhost.c). */
typedef struct {
    int alarm,fight,guard,can_report;   /* can_report: an NPC, alive, not knocked down */
    int disposition;                    /* its derived disposition (the conversation's rule) */
    int engaged;                        /* it fights the player now */
    int aggressive;                     /* isAggressive toward the player */
    unsigned long reference;            /* its placed reference */
    int want_faction;                   /* in: the caller wants its faction (a string read: only for a crime's victim) */
    char faction[32];                   /* its faction ("" none or not asked) */
    aw_crime_observer_t observer;
} aw_crime_witness_t;
extern int (*aw_crime_witness)(struct edict_s *e,aw_crime_witness_t *out);   /* 0: not an NPC that can witness */
extern int (*aw_crime_attack)(struct edict_s *e,int fight);                  /* the witness's new Fight; it attacks */
extern void (*aw_crime_thief)(aw_crime_thief_t *out);                        /* the player's side, by the host */
/* the host's other acts: a disposition change (PERMANENT: its base), the end of a crime's fight (the Fight back to
 * FIGHT), a pursuit begun or ended (the ambient tables) */
extern void (*aw_crime_disposition)(struct edict_s *e,int change,int permanent);
extern void (*aw_crime_calm)(struct edict_s *e);
extern int (*aw_crime_pursue)(struct edict_s *e,int on);     /* aw_ambient.c AW_AmbientPursue */
extern int (*aw_crime_greet)(struct edict_s *e);            /* the guard talks to the player (ForceGreeting's act) */
extern int (*aw_crime_guard)(struct edict_s *e);            /* of class Guard (the class read once per class) */
/* The player took VALUE worth of something OWNER owns (an NPC record id, or a faction when FACTION): the crime as
 * commitCrime decides it. Returns the witnesses who saw it (0: no crime). */
int AW_CrimeTheft(const char *owner,int faction,int value);
/* The value of taking COUNT of item ID worth VALUE each: gold counts its pieces (OpenMW itemTaken isGold). */
int AW_CrimeTakenValue(const char *id,int count,int value);
/* The player's attack on NPC VICTIM (actorAttacked; called before its fight starts): an assault when the player can
 * commit a crime against it. 1 when a crime was committed. */
int AW_CrimeAssault(struct edict_s *victim);
/* The player killed NPC VICTIM (actorKilled; CAN_COMMIT: canCommitCrimeAgainst at the blow, -1 work it out now): a
 * murder when the rule says so. 1 when a murder was committed. */
int AW_CrimeKilled(struct edict_s *victim,int can_commit);
/* canCommitCrimeAgainst for VICTIM now (an NPC not aggressive, not engaged, not pursuing). */
int AW_CrimeCanCommit(struct edict_s *victim);
/* Trespass (unlockAttempted: picking or forcing an owned lock) and an owned bed used (sleepInBed): 1 when seen (the bed:
 * the sleep is refused). OWNER an NPC record id or a faction (FACTION). */
int AW_CrimeTrespass(const char *owner,int faction,int bed);
/* OnMurder of the NPC of placed reference REF: 1 once after its murder was reported. */
int AW_CrimeOnMurder(unsigned long ref);
/* The dialogue's Alarmed of the NPC of REF, and the crime's temporary disposition change of it (the conversation's
 * derived disposition adds it). */
int AW_CrimeAlarmed(unsigned long ref);
int AW_CrimeDispositionOf(unsigned long ref);
/* PayFine (CONFISCATE 1), PayFineThief (0) and GotoJail: see the top. GotoJail runs when the conversation has
 * closed (the player reads the guard's line first). */
void AW_CrimePayFine(int confiscate);
void AW_CrimeGoToJail(void);
int AW_CrimeInJail(void);              /* GetPCInJail: from GotoJail until the release */
/* updateDialogueGlobals: the crime gold globals set by name (SET_GLOBAL by the host) when a conversation opens. */
void AW_CrimeDialogueGlobals(int (*set_global)(const char *name,int value),int gold);
/* Once a frame (aw_mwhost.c): the pursuing guards, the arrest on sight, a pending jail. Nothing while no guard pursues,
 * the bounty is under iCrimeThreshold and no jail waits. */
void AW_CrimeTick(float dt);
/* CRIME-SAVE-PURSUERS-62: the NPCs' crime rows in a saved game (the AWCR block; aw_mwhost.c actors_export and
 * actors_import). Export: the bytes written, -1 short; Import: the bytes read, -1 unreadable (none kept); Reset: none
 * (a save without the block). A pursuer loaded walks again when its edict is here (pursuers()). */
int AW_CrimeActorsExport(unsigned char *out,int capacity);
int AW_CrimeActorsImport(const unsigned char *data,int bytes);
void AW_CrimeActorsReset(void);
/* Counters and the last crime for `dbg crime` (the console). */
void AW_CrimeInit(void);
/* MWSCRIPT-SMALL-FUNCTIONS-62, GetLOS and GetDetected (OpenMW 0.51 World::getLOS; actors.cpp isActorDetected;
 * mechanicsmanagerimp.cpp awarenessCheck): FROM sees TO eye to eye through the world (actors do not block; a hidden,
 * disabled one is never seen nor sees); OBSERVER notices ACTOR when it sees it and its kept roll is at least the
 * awareness target (the settings of the crime rules; without them every seen actor is noticed). */
int AW_CrimeSight(struct edict_s *from,struct edict_s *to);
/* fAlarmRadius in map units (the guards' reach for joining a fight, COMBAT-ACTOR-VS-ACTOR-62); 0 without the table */
float AW_CrimeAlarmRadius(void);
int AW_CrimeDetects(struct edict_s *observer,const aw_crime_observer_t *o,struct edict_s *actor,const aw_crime_thief_t *t);
#endif
