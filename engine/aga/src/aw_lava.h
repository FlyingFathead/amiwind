/* SPDX-License-Identifier: GPL-2.0-or-later
 * Lava (docs/LAVA.md): Quake's liquid contents with Morrowind's lava contract.
 * The builder turns each Morrowind lava pool into a shallow liquid brush with a
 * "*lava" warp texture, so the BSP compiler gives it CONTENTS_LAVA and the
 * renderer draws it with the warp span drawer, fully bright. This file adds
 * what the fork's game code lacks: the damage of the pool script (an actor
 * standing on it loses 20 health a second) and the in-lava view tint (a deep
 * blood red that deepens the longer the player stays in).
 * The rules are pure functions (aw_lava_rules.c, host-tested); aw_lava.c
 * applies them to the player. */
#ifndef AW_LAVA_H
#define AW_LAVA_H

#define AW_LAVA_CONTENTS (-5)          /* CONTENTS_LAVA, bspfile.h */
#define AW_LAVA_DEFAULT_DPS 20.0f      /* Morrowind's pool script: HurtStandingActor 20 */
#define AW_LAVA_DEFAULT_TINT "128 4 4" /* deep blood red (owner, 2026-10-09) */

/* 1 when an entity with this watertype / waterlevel stands in lava (feet or deeper). */
int AW_LavaIn(int watertype, int waterlevel);
/* Tint strength (0..255) after `seconds` in lava: `low` on stepping in, rising
 * linearly to `high` after `ramp` seconds (ramp <= 0: `high` at once). */
int AW_LavaTintPercent(float seconds, int low, int high, float ramp);
/* Parse "R G B" (0..255 each, clamped). Returns 1 on success; on a malformed
 * string it writes the default blood red and returns 0. */
int AW_LavaParseTint(const char *text, int rgb[3]);
/* Damage over one frame: dps * seconds, never negative (a paused frame hurts nothing). */
float AW_LavaDamage(float dps, float seconds);

/* Engine glue (aw_lava.c). */
void AW_LavaInit(void);
void AW_LavaPhysics(void);
/* Contents colour shift: eye_contents is the view leaf's contents. Writes the
 * lava tint (rgb, percent 0..255) and returns 1 when the eye is in lava or the
 * player's feet are in lava; otherwise returns 0 and writes nothing. */
int AW_LavaContentsShift(int eye_contents, int rgb[3], int *percent);
/* Seconds the player has stood in lava without leaving it (0 when out). */
float AW_LavaSeconds(void);

#endif
