/* SPDX-License-Identifier: GPL-2.0-or-later
 * The werewolf's fight (NPC-WEREWOLF-FIGHTS-ARMED-68, v0.0.68): a werewolf, the player or any character a script turned,
 * fights with its claws only: hand to hand with the werewolf's own damage, no weapon, no shield, no spell and no magic
 * item. Pure rules beside aw_combat.h, in aw_combat_rules.c; kept out of aw_combat.h, which the CHIM world stage keys.
 * Rules from OpenMW 0.51 (read, not copied):
 *   apps/openmw/mwmechanics/mechanicsmanagerimp.cpp setWerewolf 1880-1908: every item taken off for any actor, the
 *     werewolf robe worn (no armour), the readied spell put away;
 *   apps/openmw/mwmechanics/aicombataction.cpp prepareNextAction 170-174: a werewolf character fights hand to hand and
 *     weighs nothing else (no potion, no magic item, no weapon, no spell, no flee rating); getMaxAttackDistance 363-375:
 *     its attack distance is fCombatDistance x (1 + fCombatDistanceWerewolfMod);
 *   apps/openmw/mwmechanics/combat.cpp getHandToHandDamage 478-514: a werewolf's blow is health damage, times the game's
 *     global WerewolfClawMult (a global, not a setting: the Dream of Hircine raises it), then fHandtoHandHealthPer;
 *   apps/openmw/mwclass/npc.cpp getEncumbrance 1013-1018: a werewolf carries no weight;
 *   apps/openmw/mwmechanics/aicombat.cpp chooseBestAttack 750-769: hand to hand, the attack type is a random one. */
#ifndef AW_COMBAT_WERE_H
#define AW_COMBAT_WERE_H
#include "aw_combat.h"

/* The global WerewolfClawMult when the game's scripts have none (OpenMW 0.51 mwworld/worldimp.cpp
 * generateDefaultGlobals: 25, Bloodmoon's own start value) */
#define AW_WERE_CLAW_MULT_DEFAULT 25.0f
/* fCombatDistanceWerewolfMod when the image has none (OpenMW 0.51 files/data-mw/scripts/omw/esmfallbacks.lua: 0.3) */
#define AW_WERE_DISTANCE_MOD_DEFAULT .3f

/* The sheet F as a werewolf fights (an NPC sheet or the player's; never a creature's): hand to hand (no weapon, its
 * reach, speed and weight none, the Hand-to-hand skill), no shield, nothing worn (the armour rating unarmoured, by the
 * Unarmored skill: the werewolf robe is no armour), no load. Its attributes, skills and dynamic stats stay. */
void AW_CombatWerewolfClaws(const aw_combat_settings_t *s,aw_fighter_t *f);
/* The melee swing of AW_CombatSwing with the attacker's CLAWS: below 0 the attacker is no werewolf (AW_CombatSwing
 * itself); 0 or above the attacker is a werewolf whose hand-to-hand blow is health damage, times CLAWS (the global
 * WerewolfClawMult now), then fHandtoHandHealthPer, before the critical, the knockdown's extra and the armour as any
 * blow. A weapon or a creature's own attack on the sheet is struck as before (a werewolf's sheet holds neither). */
void AW_CombatSwingClaws(const aw_combat_settings_t *s,aw_fighter_t *attacker,aw_fighter_t *victim,int attack,
                         float strength,float angle,int still,float claws,aw_combat_rng_t *r,aw_swing_t *out);
/* getMaxAttackDistance of a fighter that strikes hand to hand (original units): fCombatDistance, times 1 + MOD when it
 * is a WEREWOLF character */
float AW_CombatWerewolfAttackDistance(const aw_combat_settings_t *s,int werewolf,float mod);

#endif
