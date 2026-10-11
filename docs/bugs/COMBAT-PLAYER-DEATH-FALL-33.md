# COMBAT-PLAYER-DEATH-FALL-33: The player does not collapse on death

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.33-rc1 |
| Where | engine/aga/src/aw_combat.c player death view |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.35 (last seen) |
| Severity | low: The view stays upright on death; the original shows the body falling. |
| Family | Game logic (QuakeC) and saves (`game-logic`) |
| Playtest version | v0.0.33-rc1 |
| From commit | source 7ae3ea7, engine 7ae3ea7, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine 7ae3ea7, world format unknown |
| Unknown because | owner playtest report names no image commit or world format |
| Build note | owner playtest of a v0.0.33 build; the exact image commit is not in the report |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open (owner playtest). 10 October 2026: repaired in source on v0.0.36-dev (gated); the in-game check is pending.

## Symptom

When the player dies the view does not fall to the ground as in Morrowind.

## Where

engine/aga/src/aw_combat.c (player death view), QuakeC player death.

## How it happened

Sources: OpenMW CharacterController::playRandomDeath switches the player to third person (World::useDeathCamera) and plays the body's death animation, because the first-person animations have no death. AmiWind has no third-person player body; the knockdown already lowers the view to the floor (player_down_view), but death does not use it.

## Why it was not caught

The knockdown view was written for knockdown and knockout only.

## Reproduction

Always.

## Repair

v0.0.36-dev: the player now has a body (a stand-in per playable race and sex, baked by the builder through the
NPC pipeline, tools/prepare_player_view.py) and, as in the original, death switches to the third-person death
camera while the body plays its death animation (engine/aga/src/aw_view.c; docs/THIRD_PERSON.md).
`aw_view_death 0` keeps the previous first-person death view.

## Verification

Source and gate: tests/aga_view_test.c, tests/test_third_person.py. Reference frames of the original sequence
from OpenMW 0.51 recorded for the A/B. To do: the same pose in game (death camera, fallen body, prompt).

## Prevention

Combat and death behaviour follow the original rules with the source named (OpenMW source, game settings); every presentation change gets a fixture or an in-game clip.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Game logic (QuakeC) and saves (`game-logic`). QuakeC entities, saves and game state. See [families](README.md#families).

- AW-20260928-10 (no report page): Interior door animation and sound missing
- AW-20260928-12 (no report page): Downstairs interior doors cannot open
- AW-20260928-19 (no report page): Courtyard barrel incorrectly says empty
- AW25-06 (no report page): Quicksave shown as empty; save ordering confusing
- [CENSUS-DOOR-STUCK-29](CENSUS-DOOR-STUCK-29.md): Player stuck after opening Census Office hall door
- [CHIM-COURT-BARREL-USE-33](CHIM-COURT-BARREL-USE-33.md): Census courtyard on CHIM: Fargoth's ring barrel cannot be used, so the opening cannot proceed
- CLOCK-01 (no report page): Automatic clock dropped fractional milliseconds each frame
- [COMBAT-BLOCKING-36](COMBAT-BLOCKING-36.md): Requested: blocking in combat - NPCs block by their Block skill with a block animation, the player blocks with the right mouse button
- [COMBAT-FIST-BLOCK-33](COMBAT-FIST-BLOCK-33.md): A fighter with a shield blocks while fighting with fists
- [COMBAT-HIT-RECOVERY-33](COMBAT-HIT-RECOVERY-33.md): Fatigue hits did not stagger, and knockdowns lasted half a second too long
- [COMBAT-NO-CONDITION-33](COMBAT-NO-CONDITION-33.md): Weapon and shield condition were ignored in combat
- [COMBAT-NOT-SAVED-33](COMBAT-NOT-SAVED-33.md): Combat state and NPC deaths are not saved
- [COMBAT-PLAYER-ATTACK-TYPE-33](COMBAT-PLAYER-ATTACK-TYPE-33.md): The player's attack type and swing strength were random
- [COMBAT-PLAYER-KNOCKDOWN-33](COMBAT-PLAYER-KNOCKDOWN-33.md): The player's knockdown and knockout exist only in the combat rules
- [COMBAT-SETUP-DICE-BLOCK-33](COMBAT-SETUP-DICE-BLOCK-33.md): The Arena setup offers no dice/style choice before a fight, and there is no block button
- [DEBUG-MAP-SAVE-VALIDATION-32](DEBUG-MAP-SAVE-VALIDATION-32.md): After a debug map load of an open-world map the autosave fails validation; two of three also report Interior spawn blocked
- [ENGINE-ANGLEMOD-RANGE-35](ENGINE-ANGLEMOD-RANGE-35.md): anglemod returned 360 for -360 and passed NaN and out-of-range values on
- [ENGINE-QC-ARGS-SYSERROR-35](ENGINE-QC-ARGS-SYSERROR-35.md): Bad QuakeC sound arguments stopped the program; lightstyle had no range check
- [PHYSICS-GRAVITY-SCALE-36](PHYSICS-GRAVITY-SCALE-36.md): Gravity is Quake's 800 although the world is scaled 0.25: jumps and falls are several times faster than the original
- [PLAYER-DEATH-LIMBO-35](PLAYER-DEATH-LIMBO-35.md): After the player dies there is no way out: the game stays in a limbo with no reload or retry
- [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md): Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields
- RENDER-METADATA-29 (no report page): Native renderer metadata warns as an unknown QuakeC field
- SAVE-EQUIPMENT-29 (no report page): Quickload returns with hands and torch put away
- [SERVER-FRAME-ARRIVAL-33](SERVER-FRAME-ARRIVAL-33.md): The server frame costs about 226 ms per frame at the Balmora arrival camera on a slow 68040
- [WAIT-DURING-COMBAT-36](WAIT-DURING-COMBAT-36.md): Waiting is allowed in the middle of a fight
- [WAIT-FEET-IN-WATER-36](WAIT-FEET-IN-WATER-36.md): Waiting is allowed with the feet in water (the original refuses it)

<!-- END GENERATED CATEGORY -->
