# COMBAT-SETUP-DICE-BLOCK-33: The Arena setup offers no dice/style choice before a fight, and there is no block button

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.33-rc1 |
| Where | engine/aga/src/aw_arena.c setup, aw_menu.c, aw_combat.c |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-rc1 (last seen) |
| Severity | low: Both switches exist (Options > Controls) but not on the fight setup; a manual block is a requested AmiWind extension. |
| Family | Game logic (QuakeC) and saves (`game-logic`) |
| Playtest version | v0.0.33-rc1 |
| From commit | source 7ae3ea7, engine 7ae3ea7, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine 7ae3ea7, world format unknown |
| Unknown because | owner playtest report names no image commit or world format |
| Build note | owner playtest of a v0.0.33 build; the exact image commit is not in the report |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open (owner request from the playtest). The original blocks automatically (Block skill roll); a block button would be an AmiWind extension.

## Symptom

The owner wants to pick the hit chance mode (AmiWind dice extension or the original rolls) before the fight starts, and the right mouse button to block "as in Morrowind".

## Where

engine/aga/src/aw_arena.c (setup screen), engine/aga/src/aw_menu.c (Options > Controls), engine/aga/src/aw_combat.c (block).

## How it happened

The Combat style and Dice rolls switches live in Options > Controls only. Sources on blocking: the original has no block control: OpenMW blockMeleeAttack (combat.cpp) rolls the block automatically from the Block skill when a shield is carried, its input actions have no block action (mwinput/actions.hpp: Use = attack), and in the original the right mouse button opens the menus. A held block is therefore not original behaviour.

## Why it was not caught

The setup screen was built before the two switches existed.

## Reproduction

Always.

## Repair

Not yet. (1) The Arena setup screen shows both switches (same cvars aw_combat_dice / aw_combat_miss). (2) A held block button as a labelled AmiWind extension (default off, original automatic block stays the default) on the right mouse button's context action `+aw_alt` (MOUSE3 on the Amiga; COMPANION-PICK-RMB-33: picks a companion in pick mode, blocks in a fight), using the original block animation and the same block rules while held.

## Verification

None yet: menu test for the setup rows; rules test that the held block uses the original formula and is off by default.

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
- [COMBAT-FIST-BLOCK-33](COMBAT-FIST-BLOCK-33.md): A fighter with a shield blocks while fighting with fists
- [COMBAT-HIT-RECOVERY-33](COMBAT-HIT-RECOVERY-33.md): Fatigue hits did not stagger, and knockdowns lasted half a second too long
- [COMBAT-NO-CONDITION-33](COMBAT-NO-CONDITION-33.md): Weapon and shield condition were ignored in combat
- [COMBAT-NOT-SAVED-33](COMBAT-NOT-SAVED-33.md): Combat state and NPC deaths are not saved
- [COMBAT-PLAYER-ATTACK-TYPE-33](COMBAT-PLAYER-ATTACK-TYPE-33.md): The player's attack type and swing strength were random
- [COMBAT-PLAYER-DEATH-FALL-33](COMBAT-PLAYER-DEATH-FALL-33.md): The player does not collapse on death
- [COMBAT-PLAYER-KNOCKDOWN-33](COMBAT-PLAYER-KNOCKDOWN-33.md): The player's knockdown and knockout exist only in the combat rules
- [DEBUG-MAP-SAVE-VALIDATION-32](DEBUG-MAP-SAVE-VALIDATION-32.md): After a debug map load of an open-world map the autosave fails validation; two of three also report Interior spawn blocked
- [ENGINE-ANGLEMOD-RANGE-35](ENGINE-ANGLEMOD-RANGE-35.md): anglemod returned 360 for -360 and passed NaN and out-of-range values on
- [ENGINE-QC-ARGS-SYSERROR-35](ENGINE-QC-ARGS-SYSERROR-35.md): Bad QuakeC sound arguments stopped the program; lightstyle had no range check
- [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md): Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields
- RENDER-METADATA-29 (no report page): Native renderer metadata warns as an unknown QuakeC field
- SAVE-EQUIPMENT-29 (no report page): Quickload returns with hands and torch put away
- [SERVER-FRAME-ARRIVAL-33](SERVER-FRAME-ARRIVAL-33.md): The server frame costs about 226 ms per frame at the Balmora arrival camera on a slow 68040

<!-- END GENERATED CATEGORY -->
