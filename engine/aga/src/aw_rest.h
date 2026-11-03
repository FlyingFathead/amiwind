/* SPDX-License-Identifier: GPL-2.0-or-later
 * Resting and waiting (docs/RESTING.md, REST-WAIT-59). aw_rest_rules.c holds the rules as pure functions (host tested
 * by tests/aga_rest_rules_test.c); aw_wait.c runs the T window, beds and the hours on the player.
 *
 * The rules follow the original as OpenMW 0.51 implements them (reference, own code): mwgui/waitdialog.cpp (rest or
 * wait, the refusals, the interruption roll, the level-up after a full rest), mwworld/worldimp.cpp canRest,
 * mwmechanics/actors.cpp restoreDynamicStats and getHoursToRest, mechanicsmanagerimp.cpp sleepInBed. The numbers are
 * the game settings of the player's own master file (levelup/rest.txt, tools/prepare_levelup.py).
 */
#ifndef AW_REST_H
#define AW_REST_H

typedef struct {
    float rest_magic;          /* fRestMagicMult: magicka per hour of rest per point of Intelligence */
    float end_fatigue;         /* fEndFatigueMult */
    float fatigue_base,fatigue_mult;   /* fFatigueReturnBase, fFatigueReturnMult */
    float sleep_rand,sleep_rest;       /* fSleepRandMod, fSleepRestMod: the wilderness interruption */
    float enc_str;             /* fEncumbranceStrMult: carrying capacity per point of Strength */
} aw_rest_settings_t;
#define AW_REST_SETTING_COUNT 7
int AW_RestSettingSet(aw_rest_settings_t *s,const char *name,float value);

/* The player's numbers the hours change: current and maximum of the three, the modified attributes that set the rates,
 * the carried weight, and the stunted-magicka mark (the Atronach's sign). */
typedef struct {
    float health,magicka,fatigue,health_max,magicka_max,fatigue_max;
    float endurance,intelligence,strength,carried;
    int stunted;
} aw_rest_body_t;

/* HOURS of rest (SLEEPING 1) or of waiting (0): fatigue in both, (fFatigueReturnBase + fFatigueReturnMult x (1 -
 * carried / capacity)) x fEndFatigueMult x Endurance x 3600 per hour, nothing when it is at or above its maximum;
 * resting only: health 0.1 x Endurance and magicka fRestMagicMult x Intelligence per hour (no magicka when stunted).
 * Each stops at its maximum. */
void AW_RestRestore(const aw_rest_settings_t *s,aw_rest_body_t *b,float hours,int sleeping);
/* "Until Healed": the hours that fill health and magicka, at least 1 (getHoursToRest); 0 when both are full (the
 * button is not offered). */
int AW_RestUntilHealed(const aw_rest_settings_t *s,const aw_rest_body_t *b);
/* The wilderness interruption (startWaiting): ROLL is the dice in 0..HOURS-1; the rest is interrupted when ROLL <
 * fSleepRandMod x HOURS and int(fSleepRestMod x HOURS) is not 0. Returns the hour the rest stops after (1..HOURS-1),
 * or 0 for an undisturbed rest. Never for 3 hours or less with the game's settings. */
int AW_RestInterruptAt(const aw_rest_settings_t *s,int hours,int roll);

/* The refusals (canRest): bits of what forbids the window; both lines can show together. */
enum {AW_REST_WATER=1,AW_REST_AIR=2,AW_REST_ENEMIES=4};
/* The flags for a player IN_WATER (feet in water), ON_GROUND, FLYING (levitating, noclip), ENEMIES near, BED used
 * (a bed lifts the air rule only). */
int AW_RestRefusal(int in_water,int on_ground,int flying,int enemies,int bed);
/* A bed's use (sleepInBed/isOwned): OWNER and FACTION ('-' or empty for none), the RANK it asks, the rental GLOBAL's
 * value (0 when none or not rented), the player's RANK in that faction (-1 not a member). 1 the player may sleep in it. */
int AW_RestBedAllowed(const char *owner,const char *faction,int rank,int global_value,int player_rank);

/* aw_wait.c: the engine side. */
int AW_RestOpen(unsigned long bed_reference);   /* T (0) or a bed's ShowRestMenu; 1 when the window opened */
int AW_RestSleeping(void);                      /* GetPCSleep: the window is open in rest mode */
/* A refused bed (the trespass crime, CRIME-59; NULL until it lands): the bed's reference and its owner or faction. */
extern void (*aw_rest_bed_refused)(unsigned long reference,const char *owner);
/* The interruption's creature (one from the region's sleep list, levelled at the player's level, within 220 units;
 * NULL until creatures can be placed from a levelled list). */
extern void (*aw_rest_spawn)(const char *sleep_list);
/* aw_mwhost.c: the player's spell effects over SECONDS of passing time. */
void AW_MwscriptEffectsAdvance(float seconds);
#endif
