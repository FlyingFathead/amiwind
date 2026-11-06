/* SPDX-License-Identifier: GPL-2.0-or-later
 * Active spell effects (SPELL-EFFECTS-57; docs/MWSCRIPT_BYTECODE.md "Spell effects: the design", docs/MAGIC_EFFECTS.md
 * "Active effects"). v0.0.57's first slice held Fortify, Drain, Damage and Restore on the player; v0.0.61 keeps any
 * magic effect of the game (its effect number 0..142, OpenMW's MGEF index) on any actor record, by the actor's
 * reference: the player and the NPCs and creatures a spell lands on.
 *
 * Rules from OpenMW 0.51 (apps/openmw/mwmechanics/activespells.cpp, spelleffects.cpp applyMagicEffect,
 * components/esm3/loadmgef.cpp), written independently:
 * - an effect that is not "applied once" acts every second it is active, its magnitude a second (elemental damage,
 *   poison, sun damage, Damage and Restore of a stat, Absorb Health/Magicka/Fatigue, the disintegrations, the cures);
 *   with no duration it acts once, its whole magnitude;
 * - every other effect is applied once when it lands and undone when it ends: Fortify and Drain move the stat,
 *   Absorb Attribute/Skill drain the target; the rest (Light, Levitate, Shield, Feather, Night Eye, ...) only add
 *   their magnitude to the actor's effect magnitudes, which the engine's systems read (AW_EffectsMagnitude);
 * - effects on an actor whose record is not loaded do not tick (OpenMW updates only the actors in the active cells).
 * A fixed pool, no allocation: AW_EFFECTS_PLAYER entries at most on the player, AW_EFFECTS_MAX in all; a full pool
 * refuses a new effect (counted).
 *
 * Pure C, no engine headers (native tests: tests/test_mwscript.py EffectTests). */
#ifndef AW_EFFECTS_H
#define AW_EFFECTS_H
#include "aw_actorstate.h"

#define AW_EFFECTS_MAX 64          /* active effects at once, every actor together */
#define AW_EFFECTS_PLAYER 32       /* of them at most on the player; the rest stay for the NPCs */
#define AW_EFFECT_COUNT 143        /* the game's magic effect numbers 0..142 */
#define AW_EFFECT_NO_ARG 0xFF
#define AW_EFFECT_NO_SOURCE 0xFFFF
enum {AW_FX_DRAIN=0,AW_FX_DAMAGE=1,AW_FX_RESTORE=2,AW_FX_FORTIFY=3};
/* Some effect numbers the engine reads (OpenMW's MGEF indexes). */
enum {AW_EFFECT_WATER_BREATHING=0,AW_EFFECT_SWIFT_SWIM=1,AW_EFFECT_WATER_WALKING=2,AW_EFFECT_SHIELD=3,
      AW_EFFECT_FEATHER=8,AW_EFFECT_BURDEN=7,AW_EFFECT_JUMP=9,AW_EFFECT_LEVITATE=10,AW_EFFECT_SLOWFALL=11,
      AW_EFFECT_FIRE_DAMAGE=14,AW_EFFECT_SHOCK_DAMAGE=15,AW_EFFECT_FROST_DAMAGE=16,AW_EFFECT_POISON=27,
      AW_EFFECT_INVISIBILITY=39,AW_EFFECT_CHAMELEON=40,AW_EFFECT_LIGHT=41,AW_EFFECT_NIGHT_EYE=43,
      AW_EFFECT_PARALYZE=45,AW_EFFECT_SILENCE=46,AW_EFFECT_SOUND=48,AW_EFFECT_SUN_DAMAGE=135};

/* What an effect does to the stats: AW_FX_* (KIND) on the stat GROUP (0 attribute, 1 health, 2 magicka, 3 fatigue,
 * 4 skill), or -1 for an effect that only adds its magnitude. */
int AW_EffectKind(int effect,int *group);
/* 1 when the effect acts each second (not applied once). */
int AW_EffectPerSecond(int effect);
/* 1 when the effect is harmful: an attack when it lands on an actor (OpenMW's hardcoded harmful flag; the game
 * data's MGEF flags do not carry it). */
int AW_EffectHarmful(int effect);
/* The AWA_* stat of a GROUP and its ARG (attribute or skill index); -1 when it has none. */
int AW_EffectStat(int group,int arg);

void AW_EffectsReset(void);
/* An effect lands on A: EFFECT 0..142, ARG its attribute or skill (AW_EFFECT_NO_ARG), MAGNITUDE rolled already
 * (>= 0), SECONDS its duration (0: once), SOURCE the spell (ASPT row) or AW_EFFECT_NO_SOURCE. An effect that acts
 * each second with no duration acts at once; one applied once with no duration does nothing. 1 taken, 0 refused. */
int AW_EffectsLand(aw_actor_t *a,int effect,int arg,float magnitude,float seconds,int source);
/* v0.0.57's call: KIND AW_FX_* on the AWA_* STAT (the effect number is found from them). */
int AW_EffectsAdd(aw_actor_t *a,int kind,int stat,float magnitude,float seconds);
/* The game clock moved DT seconds for A: its per-second effects act, ended ones are undone and leave. 1 when A
 * changed. */
int AW_EffectsTick(aw_actor_t *a,float dt);
int AW_EffectsCount(void);                       /* every actor */
int AW_EffectsCountOn(uint32_t owner);
/* GetEffect: 1 when an effect of NUMBER is active on the player (AW_EffectsHas) or on OWNER. */
int AW_EffectsHas(int number);
int AW_EffectsHasOn(uint32_t owner,int number);
/* The summed magnitude of EFFECT on OWNER (ARG AW_EFFECT_NO_ARG: every argument). */
float AW_EffectsMagnitude(uint32_t owner,int effect,int arg);
/* The other actors that carry effects (not the player), up to MAX; their count. */
int AW_EffectsOwners(uint32_t *out,int max);
/* OWNER's effects go without being undone (it died or left the game); how many. */
int AW_EffectsForget(uint32_t owner);
/* The I-th active effect (0..AW_EffectsCount()-1), for the HUD and the status line; 1 when there is one. */
typedef struct {uint32_t owner;int effect,arg,source;float magnitude,left;} aw_effect_info_t;
int AW_EffectsAt(int i,aw_effect_info_t *out);
unsigned long AW_EffectsRefused(void);
/* Saved games: "AWEF" u8 2 u8 count, then per effect u32 owner u8 effect u8 arg u16 source f32 magnitude f32 seconds
 * left (big-endian), 16 bytes. Export: bytes or -1 too small; Import: 1, or 0 for a bad block (then nothing is
 * active); v0.0.57's version 1 blocks (the player's, 10 bytes an effect) still load. The records' stats were saved
 * as they stood, so an import only restores the list; nothing is applied again. */
int AW_EffectsExport(unsigned char *out,int capacity);
int AW_EffectsImport(const unsigned char *data,int bytes);
#endif
