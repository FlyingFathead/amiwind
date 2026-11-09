/* SPDX-License-Identifier: GPL-2.0-or-later
 * Breath and drowning under water (UNDERWATER-BREATH-62; docs/PLAYER_MOVEMENT.md "Breath and drowning").
 *
 * Rules from the original game as OpenMW 0.51 implements them (apps/openmw/mwmechanics/actors.cpp updateDrowning,
 * mwgui/hud.cpp setDrowningTimeLeft), written independently:
 * - while the player's head is under water (Quake: the eyes in a water volume, waterlevel 3) and no Water Breathing
 *   is on him, the breath left falls by the time passed, down to 0; out of the water (or with Water Breathing) it is
 *   full again at once: fHoldBreathTime seconds (Morrowind.esm: 20);
 * - with no breath left he loses fSuffocationDamage (3) health a second, continuously, and the "drown" sound plays
 *   (again whenever it has ended); god mode takes none (the one world-damage check, aw_combat.c AW_CombatHurtPlayer);
 * - Water Breathing is any magnitude of the effect (number 0) on the player: a race's ability (the Argonians'), a
 *   potion, a spell, a worn Constant Effect item, a script's ModWaterBreathing;
 * - the breath bar is shown while the breath left is under the full time (so: under water without Water
 *   Breathing), and it flashes once the breath is gone.
 * The settings come from the player's own master file at build time (combat/settings.txt "breath" lines,
 * tools/prepare_combat.py BREATH_SETTINGS); an image without them uses the original's values.
 * Not kept in saved games: a load, a new map or New Game gives a full breath. In noclip the breath stays full.
 *
 * The rules are pure functions (aw_breath_rules.c; tests/aga_breath_rules_test.c); aw_breath.c applies them. */
#ifndef AW_BREATH_H
#define AW_BREATH_H

#define AW_BREATH_HOLD_DEFAULT 20.0f         /* fHoldBreathTime, Morrowind.esm */
#define AW_BREATH_SUFFOCATION_DEFAULT 3.0f   /* fSuffocationDamage, Morrowind.esm */
#define AW_BREATH_WATER (-3)                 /* CONTENTS_WATER, bspfile.h */
#define AW_BREATH_SLIME (-4)                 /* CONTENTS_SLIME: water to breathe in, too */

typedef struct {float hold,suffocation;} aw_breath_settings_t;
#define AW_BREATH_SETTING_COUNT 2
void AW_BreathSettingsDefault(aw_breath_settings_t *s);
/* one "breath NAME VALUE" setting (fHoldBreathTime, fSuffocationDamage; case ignored); 1 when NAME is one of them
 * and VALUE is a number >= 0 */
int AW_BreathSettingSet(aw_breath_settings_t *s,const char *name,float value);
/* 1 when the head is under water: the eyes in a water (or slime) volume; lava is not water to hold the breath in */
int AW_BreathSubmerged(int watertype,int waterlevel);
/* the breath left after DT seconds: falling while SUBMERGED and not BREATHING (Water Breathing), never below 0;
 * else HOLD (full at once). LEFT < 0 means "full" (not yet set). */
float AW_BreathStep(float left,float hold,int submerged,int breathing,float dt);
/* the health lost over DT seconds with LEFT breath: SUFFOCATION x DT once it is 0, else 0 (never negative) */
float AW_BreathDamage(float left,float suffocation,float dt);
/* the bar: shown while LEFT is under HOLD; its fill 0..1 */
int AW_BreathBarShown(float left,float hold);
float AW_BreathFraction(float left,float hold);

/* Engine glue (aw_breath.c). */
void AW_BreathInit(void);
void AW_BreathPhysics(void);
/* aw_ui.c: the breath bar (top of the view, the middle) when shown: its fill and whether it flashes; 0 none */
extern int (*aw_breath_bar)(float *fraction,int *flashing);

#endif
