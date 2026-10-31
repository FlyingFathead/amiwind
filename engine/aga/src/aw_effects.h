/* SPDX-License-Identifier: GPL-2.0-or-later
 * Spell effects on the player, the first slice (v0.0.57, SPELL-EFFECTS-57; docs/MWSCRIPT_BYTECODE.md "Spell effects:
 * the design"): Fortify, Drain, Damage and Restore of an attribute, a skill, health, magicka or fatigue, with
 * durations on the game clock. Rules from OpenMW 0.51 apps/openmw/mwmechanics/spelleffects.cpp (what each does, and
 * undoing it when it ends) and activespells.cpp (the list and its ticking), written independently. A fixed pool on the
 * actor record (aw_actorstate.h), no allocation.
 *
 * Pure C, no engine headers (native tests: tests/test_mwscript.py EffectTests). */
#ifndef AW_EFFECTS_H
#define AW_EFFECTS_H
#include "aw_actorstate.h"

#define AW_EFFECTS_MAX 16          /* active effects on the player at once */
enum {AW_FX_DRAIN=0,AW_FX_DAMAGE=1,AW_FX_RESTORE=2,AW_FX_FORTIFY=3};

void AW_EffectsReset(void);
/* An effect lands on A (the player's record): KIND AW_FX_*, STAT an AWA_* stat (attribute, skill, health, magicka,
 * fatigue), MAGNITUDE rolled already, SECONDS its duration (0: instant). Damage and Restore with a duration act each
 * second; Fortify and Drain hold until they end and are then undone. 1 taken, 0 refused (the pool is full). */
int AW_EffectsAdd(aw_actor_t *a,int kind,int stat,float magnitude,float seconds);
/* The game clock moved DT seconds: per-second effects act, ended ones are undone and leave. 1 when A changed. */
int AW_EffectsTick(aw_actor_t *a,float dt);
int AW_EffectsCount(void);
/* GetEffect: 1 when an effect of the game's effect NUMBER is active (only this slice's kinds can be). */
int AW_EffectsHas(int number);
unsigned long AW_EffectsRefused(void);
/* Saved games: "AWEF" u8 1 u8 count, then per effect u8 kind u8 stat f32 magnitude f32 seconds left (big-endian).
 * Export: bytes or -1 too small; Import: 1, or 0 for a bad block (then nothing is active). The record's stats were
 * saved as they stood, so an import only restores the list; nothing is applied again. */
int AW_EffectsExport(unsigned char *out,int capacity);
int AW_EffectsImport(const unsigned char *data,int bytes);
#endif
