# Mechanics parity: every actor by its own stats

_Last updated with AmiWind v0.0.66-dev1 (13 November 2026)._

Every character, creature and NPC fights, moves, talks and reacts by its own attributes, skills, Fight, Flee,
disposition and gear. The reference for each rule is the OpenMW engine (0.51 source), which keeps the original
game's formulas and fixes a few of its bugs. This table lists each mechanic that should read an actor's stats, the
reference function, our function, and whether they agree.

- SAME: our function computes what the reference computes, with the same game settings.
- DIFFERENT: it reads the stats but the formula or a default differs; the column "Since" says when it was put right.
- MISSING: the stat or the step is not counted at all.

Line numbers are those of the files at the time of writing (OpenMW 0.51 `apps/openmw/`, our
`engine/aga/src/`). The game settings (fFatigueBase and the like) come from the player's own master file at build
time.

## Counts (v0.0.66-dev1, 13 November 2026)

25 rows: 16 SAME, 7 DIFFERENT (rows 4, 9, 10, 16, 20 and 25 put right in v0.0.66, row 21 in part), 1 MISSING put
right in v0.0.66 (row 23), and row 24 not audited yet.

## The table

| # | Mechanic | Reference (OpenMW) | Ours | Verdict | Stats it reads |
|---|----------|--------------------|------|---------|----------------|
| 1 | Hit chance | `mwmechanics/combat.cpp:316` getHitChance, `creaturestats.cpp` getFatigueTerm, getEvasion | `aw_combat_rules.c:73` AW_CombatHitChance | SAME | weapon skill (a creature's combat value), Agility, Luck, fatigue; Fortify Attack, Blind, Sanctuary, Chameleon, Invisibility |
| 2 | Weapon damage | `mwclass/npc.cpp:573` Npc::hit, `combat.cpp:452` adjustWeaponDamage | `aw_combat_rules.c:227` AW_CombatSwing | SAME | the weapon's chop/slash/thrust, its condition, Strength, swing strength |
| 3 | Weapon wear | `combat.cpp:416` reduceWeaponCondition | `aw_combat_rules.c` wear | SAME | damage dealt, the weapon's condition |
| 4 | Hand to hand | `combat.cpp:478` getHandToHandDamage, `:331` getHitChance, `:80` blockMeleeAttack | `aw_combat_rules.c:227` AW_CombatSwing | DIFFERENT, put right in v0.0.66 | Hand-to-hand skill, swing strength; a paralysed victim took fatigue damage only (the reference: health damage, no evasion and no block, as when knocked down) |
| 5 | A creature's own attack | `mwclass/creature.cpp:258` Creature::hit | `aw_combat_rules.c:227` AW_CombatSwing, `:350` AW_CombatCreatureSheet | SAME | the record's attack ranges, swing strength |
| 6 | A creature's melee weapon | `creature.cpp:258` Creature::hit with a weapon | `aw_combat_rules.c:371` AW_CombatCreatureWeapon | SAME | the weapon's damage and condition, Strength, the creature's combat value |
| 7 | Armour | `files/data-mw/scripts/omw/combat/local.lua` adjustDamageForArmor; `npc.cpp:1025` getArmorRating | `aw_combat_rules.c:227` (armour step), `:125` AW_CombatUnarmoredRating | SAME | armour rating (worn pieces and their skills, Unarmored) |
| 8 | Block chance | `combat.cpp:71` blockMeleeAttack | `aw_combat_rules.c:158` blocks | SAME | Block, Agility, Luck, fatigue of both; the attacker's weapon skill; swing strength; standing still |
| 9 | Block fatigue cost | `combat.cpp:157-168` blockMeleeAttack | `aw_combat_rules.c:158` blocks | DIFFERENT, put right in v0.0.66 | the load over the capacity (at most 1) x fFatigueBlockMult was not counted |
| 10 | Swing fatigue cost | `combat.cpp:532` applyFatigueLoss | `aw_combat_rules.c:227` AW_CombatSwing | DIFFERENT, put right in v0.0.66 | the load over the capacity x fFatigueAttackMult was not counted |
| 11 | Fatigue return | `mwmechanics/actors.cpp:939` calculateRestoration | `aw_combat_rules.c:339` AW_CombatRecover | SAME | Endurance |
| 12 | Knockdown | `local.lua` applyStagger; `npc.cpp:679` onHit | `aw_combat_rules.c:227` AW_CombatSwing | SAME | Agility, health damage |
| 13 | Knockout | `creaturestats.cpp` (fatigue below 0) | `aw_combat_rules.c:227`, `:339` | SAME | fatigue |
| 14 | Critical strike, damage to a fallen victim | `npc.cpp:573` Npc::hit | `aw_combat_rules.c:227` | SAME | awareness, knocked down |
| 15 | Attack on sight | `combat.cpp:623` isAggressive, `:556` getFightTerm, `:577` getFightDistanceBias | `aw_combat_rules.c:311` AW_CombatFightRating | SAME | Fight, disposition (an NPC's derived one, 50 for a creature), distance |
| 16 | Flee | `aicombataction.cpp:457` vanillaRateFlee, `:490` makeFleeDecision, `:160` prepareNextAction, `weaponpriority.cpp:173`, `spellpriority.cpp` vanillaRateSpell | `aw_combat_rules.c` AW_CombatFleeRatingVs, AW_CombatWerewolfFleeMod, AW_CombatSpellAntiFlee, AW_CombatFleeDecisionVs | DIFFERENT, put right in v0.0.66 | Flee, health, level; the rule was off by default, the werewolf case (iWereWolfFleeMod below iWereWolfLevelToAttack) and a spell as the best action were not counted |
| 17 | Disposition | `mechanicsmanagerimp.cpp` getDerivedDisposition | `aw_dial.c` AW_DialDisposition, `tools/dialogue_lut.py` | SAME (by `tests/aga_dial_rules_test.c`) | base disposition, race, Personality, faction rank and reaction, crime, disease, drawn weapon, Charm |
| 18 | Spell success | `spellutil.cpp:225` calcSpellBaseSuccessChance, `:272` getSpellSuccessChance | `aw_cast_rules.c:13` AW_CastBaseChance, `:31` AW_CastChance | SAME | the school's skill, Willpower, Luck, fatigue, Sound, Silence |
| 19 | Spell resistance | `spellresistance.cpp:29` getEffectResistance | `aw_cast_rules.c:78` AW_CastResistance | SAME | resist and weakness effects, Willpower, Luck, fatigue |
| 20 | Chase, flee and flight speed in a fight | `npc.cpp:864` / `creature.cpp:493` getMaxSpeed, `npc.cpp:1370`/`:1388`, `creature.cpp:866`/`:876` | `aw_move_rules.c:97` AW_MoveActorSpeed, `aw_combat.c` fighter_speed | DIFFERENT, put right in v0.0.66 | Speed, Athletics; every fighter used one fixed 200 game units a second |
| 21 | Wandering speed | the same getWalkSpeed | `aw_ambient.c` walk_speed | DIFFERENT: creatures put right in v0.0.66; an NPC on ForceRun still walks (open) | Speed (Athletics for the run) |
| 22 | The player's walk, run, swim, flight, jump, movement fatigue, encumbrance | `npc.cpp:864`, `actor.hpp` getSwimSpeedImpl, `character.cpp` | `aw_move_rules.c:58-180` | SAME | Speed, Athletics, Acrobatics, Strength, load, Burden, Feather, Levitate, Jump |
| 23 | An NPC's or creature's own load | `mwworld/class.cpp` getNormalizedEncumbrance, `npc.cpp:864` / `creature.cpp:493` getMaxSpeed | `aw_actorstate.c` AW_ActorCarriedWeight, `aw_combat.c` actor_load, `aw_move_rules.c` AW_MoveActorLoaded | MISSING, put right in v0.0.66 | the carried weight, Burden and Feather over Strength x fEncumbranceStrMult: in the fatigue of swings and blocks and in the fight's speed (over the limit: no movement; an NPC and a flyer slowed by fEncumberedMoveEffect) |
| 24 | Alarm and reporting a crime | `mechanicsmanagerimp.cpp` commitCrime, reportCrime | `aw_crime_rules.c` | not audited yet | Alarm, disposition, distance, sight |
| 25 | The weapon taken into a fight | `weaponpriority.cpp:23` rateWeapon, rateAmmo; `combat.cpp` getHitChance; `creature.cpp` getSkill | `tools/prepare_combat.py` equipment, best_weapon, combat_rating | DIFFERENT, put right in v0.0.66 | the weapon skills (a creature's Combat, Magic or Stealth), Agility, Luck: the melee weapon was the one of the highest maximum damage whatever the skill, a weapon of skill 0 was still taken |

## What changed in v0.0.66

- Every fighter chases, flees and flies at its own speed (row 20). An NPC runs at walk x (fBaseRunMultiplier +
  Athletics / 100 x fAthleticsRunBonus), its walk being fMinWalkSpeed + Speed / 100 x (fMaxWalkSpeed - fMinWalkSpeed);
  a creature moves at fMinWalkSpeedCreature + Speed / 100 x (fMaxWalkSpeedCreature - fMinWalkSpeedCreature) and does
  not run faster; a flyer by fMinFlySpeed..fMaxFlySpeed; a swimmer at its speed x (fSwimRunBase + Athletics / 100 x
  fSwimRunAthleticsMult). Example sheets (original units a second): an NPC at Speed 50 and Athletics 45 runs 330, a
  creature at Speed 25 moves 78.75, one at Speed 100 moves 300; the old fixed chase was 800. `aw_combat_speed` above
  0 still sets one fixed speed for everyone. Native tests: `tests/aga_move_rules_test.c`.
- The load counts in the fatigue cost of a swing and of a block (rows 9 and 10). The original masters set both
  factors to 0, so the original game plays as before; a mod that sets them is followed. Native tests:
  `tests/aga_combat_rules_test.c`.
- A wandering creature walks by the creature speeds (row 21).
- A paralysed victim takes a punch to health, has no evasion and cannot block (row 4; the knockdown's extra damage is
  not counted for it, as in the reference). Native tests: `tests/aga_combat_rules_test.c`.
- Fleeing follows the original's rule by default (row 16; `dbg combat flee off` keeps the earlier one, where a fighter
  runs only when it cannot reach the player). An NPC below iWereWolfLevelToAttack runs from a werewolf by
  iWereWolfFleeMod (both from the expansions' masters); when a spell is a fighter's best action, its success chance x
  fAIRangeMagicSpellMult (a Target effect) or fAIMagicSpellMult rates against fleeing in place of the weapon's rating.
  With the original settings only fighters of a very high Flee, or badly hurt ones with some Flee, ever run.
- A fighter's own load counts (row 23): what its record carries, with Burden and Feather, over Strength x
  fEncumbranceStrMult, read once when it engages; it enters the fatigue of its swings and blocks and its speed in the
  fight. Native tests: `tests/aga_move_rules_test.c`.
- The weapon a fighter takes into a fight is weighed by its own skills (row 25; the table in
  [ACTOR_RECORDS.md](ACTOR_RECORDS.md#combat-styles)).

## Open

- Row 21: an NPC on ForceRun while wandering.
- Row 24: the crime rules' audit.
- Row 16, the rest: a ranged weapon's anti-flee rating is still rated as a melee weapon's; potions and magic items as
  the best action are not weighed yet.
