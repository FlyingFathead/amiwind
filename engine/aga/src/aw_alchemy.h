/* SPDX-License-Identifier: GPL-2.0-or-later
 * Alchemy (ALCHEMY-61, docs/ALCHEMY.md): making potions from ingredients with the apparatus the player carries,
 * drinking potions and eating ingredients, as the original game does them.
 *
 * Rules from OpenMW 0.51 (reference, own code): apps/openmw/mwmechanics/alchemy.cpp (the effects two ingredients
 * share, in slot order; the alchemy factor; the apparatus' part in magnitude and duration; the potion's value and
 * weight; the success roll; which effects the Alchemy skill reveals, fWortChanceValue), mwmechanics/spellutil.cpp
 * rollIngredientEffect (eating: the first effect only, by a roll against skill, Intelligence, Luck and fatigue),
 * mwmechanics/spellcasting.cpp cast(Potion) (a potion acts on the drinker), mwworld/actioneat.cpp and alchemy.cpp
 * increaseSkill (the Alchemy skill's uses). The rules below are pure (aw_alchemy_rules.c, native tests
 * tests/test_alchemy.py); aw_alchemy.c is the engine glue: the window, the drink, the meal, the made potion.
 *
 * Data: an ingredient's, a potion's and an apparatus' alchemy numbers come in the item's own catalogue row (aw_inventory.h
 * AW_INV_ALCHEMY), read with the item; the game settings, lines, sounds and bottle looks in alchemy/settings.txt
 * (tools/prepare_alchemy.py), read when they are needed and freed after. */
#ifndef AW_ALCHEMY_H
#define AW_ALCHEMY_H
#include <stdint.h>
#include "aw_inventory.h"

#define AW_ALCHEMY_SLOTS 4              /* ingredients at once (OpenMW Alchemy::setAlchemist: four) */
#define AW_ALCHEMY_OUT AW_INV_ALCHEMY_EFFECTS   /* a potion's effects at most (four ingredients share at most 8) */
enum {AW_APPARATUS_MORTAR=0,AW_APPARATUS_ALEMBIC=1,AW_APPARATUS_CALCINATOR=2,AW_APPARATUS_RETORT=3,AW_APPARATUS_TYPES=4};
/* the magic effect record's flags the rules read (OpenMW components/esm3/loadmgef.hpp) */
#define AW_ALCHEMY_MGEF_NO_DURATION 0x4
#define AW_ALCHEMY_MGEF_NO_MAGNITUDE 0x8
#define AW_ALCHEMY_MGEF_HARMFUL 0x10
/* Create's results (OpenMW Alchemy::Result, in its order of checks) */
enum {AW_ALCHEMY_OK=0,AW_ALCHEMY_NO_MORTAR,AW_ALCHEMY_TOO_FEW,AW_ALCHEMY_NO_EFFECTS,AW_ALCHEMY_FAILED};

typedef struct {
    float wort;            /* fWortChanceValue */
    float strength_mult;   /* fPotionStrengthMult */
    float t1_mag,t1_dur;   /* fPotionT1MagMult, fPotionT1DurMult */
    int alchemy_mod;       /* iAlchemyMod */
    int loaded;            /* a bit per setting read; AW_ALCHEMY_SETTINGS_ALL when every one was */
} aw_alchemy_settings_t;
#define AW_ALCHEMY_SETTINGS_ALL 31
/* one ingredient in a slot: USED, its four effect slots (AW_ALCHEMY_NO_EFFECT empty), its weight */
typedef struct {int used;aw_alchemy_effect_t e[4];float weight;} aw_alchemy_slot_t;
/* the magic effect record of EFFECT: its flags (the hardcoded harmful flag included) and base cost; 0 unknown */
typedef int (*aw_alchemy_mgef_t)(void *ctx,int effect,uint32_t *flags,float *base_cost);

/* An ingredient's effect slot INDEX (0..3) is shown at Alchemy SKILL: skill >= fWortChanceValue x (INDEX + 1) (OpenMW
 * Alchemy::effectsDescription). */
int AW_AlchemyIngredientVisible(float alchemy,float wort,int index);
/* A potion's effect INDEX in the window's list is shown: 0-1 at wort, 2-3 at 2 wort, 4-5 at 3 wort, 6-7 at 4 wort
 * (OpenMW Alchemy::knownEffect). */
int AW_AlchemyPotionVisible(float alchemy,float wort,int index);
/* 1 when the effect names an attribute (Absorb, Damage, Drain, Fortify, Restore Attribute), 2 a skill, 0 neither. */
int AW_AlchemyArgKind(int effect);
/* The effects two or more of the four slots share, once each, in OpenMW's order (each earlier slot against every later
 * one, the earlier slot's effects in their order), keyed by effect and argument; durations and magnitudes 0. How many
 * (at most AW_ALCHEMY_OUT). */
int AW_AlchemyListEffects(const aw_alchemy_slot_t s[AW_ALCHEMY_SLOTS],aw_alchemy_effect_t out[AW_ALCHEMY_OUT]);
int AW_AlchemyCount(const aw_alchemy_slot_t s[AW_ALCHEMY_SLOTS]);
/* The alchemy factor: Alchemy + 0.1 Intelligence + 0.1 Luck (modified values). */
float AW_AlchemyFactor(float alchemy,float intelligence,float luck);
/* The apparatus' part (OpenMW Alchemy::applyTools) in a magnitude or duration VALUE of an effect with FLAGS, HARMFUL:
 * the retort (a helpful effect) or the alembic (a harmful one) with or without the calcinator; QUALITY[type] <= 0: not
 * there. 0 when the qualities give a division by 0 (the value is left), else 1. */
int AW_AlchemyTools(uint32_t flags,int harmful,const float quality[AW_APPARATUS_TYPES],float *value);
/* The potion of the slots (OpenMW Alchemy::updateEffects): with a mortar and at least two ingredients, x = factor x
 * mortar quality x fPotionStrengthMult; VALUE = (int)(x x iAlchemyMod); each shared effect's magnitude
 * (x / fPotionT1MagMult) / base cost and duration (x / fPotionT1DurMult) / base cost (1 when the record has none),
 * the apparatus' part, rounded; an effect is kept when both are above 0. OUT the effects, their count returned; -1
 * no mortar or fewer than two ingredients or the settings missing; an effect without its record is left out. */
int AW_AlchemyBrew(const aw_alchemy_settings_t *set,const aw_alchemy_slot_t s[AW_ALCHEMY_SLOTS],
                   const float quality[AW_APPARATUS_TYPES],float factor,aw_alchemy_mgef_t mgef,void *ctx,
                   aw_alchemy_effect_t out[AW_ALCHEMY_OUT],int *value);
/* Create's checks before the roll (OpenMW getReadyStatus; the name is the suggested one, never empty): AW_ALCHEMY_*. */
int AW_AlchemyReady(const aw_alchemy_slot_t s[AW_ALCHEMY_SLOTS],const float quality[AW_APPARATUS_TYPES]);
/* The roll (OpenMW createSingle): a potion when it has effects and FACTOR >= ROLL (0..99). */
int AW_AlchemySucceeds(float factor,int roll,int effects);
/* The made potion's weight: the ingredients' weights over their count (OpenMW addPotion). */
float AW_AlchemyWeight(const aw_alchemy_slot_t s[AW_ALCHEMY_SLOTS]);
/* Eating (OpenMW rollIngredientEffect, index 0): x = (Alchemy + 0.2 Intelligence + 0.1 Luck) x FATIGUE_TERM; ROLL
 * (0..99) > x: no effect (0). Else y = roll / min(x, 100) x 0.25 x; duration y (1 for an effect without duration),
 * magnitude floor(0.05 y / (0.1 base cost)) (floor(y / (0.1 cost)) without duration), at least 1 (1 for an effect
 * without magnitude). 1 with *MAGNITUDE and *DURATION. */
int AW_AlchemyEat(float alchemy,float intelligence,float luck,float fatigue_term,int roll,uint32_t flags,float base_cost,
                  unsigned short *magnitude,unsigned short *duration);
/* The best apparatus of each type among N carried (TYPE, QUALITY): the highest quality wins (OpenMW setAlchemist);
 * QUALITY_OUT[type] 0 when none; BEST[type] the index among the N, -1 none. */
void AW_AlchemyBestTools(const int *type,const float *quality,int n,float quality_out[AW_APPARATUS_TYPES],int best[AW_APPARATUS_TYPES]);
/* One "set NAME VALUE" line of alchemy/settings.txt into SET; 1 when NAME is one of the five settings. */
int AW_AlchemySetting(aw_alchemy_settings_t *set,const char *name,float value);

/* ---- engine glue (aw_alchemy.c) ---- */
void AW_AlchemyInit(void);
int AW_AlchemyActive(void);
#endif
