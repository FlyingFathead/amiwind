# COMBAT-PLAYER-KNOCKDOWN-33: The player's knockdown and knockout exist only in the combat rules

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | engine/aga/src/aw_combat.c (player sheet), no view or movement effect |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: A knocked-down player keeps moving and fighting; only the defence penalty applies. |
| Family | Game logic (QuakeC) and saves (`game-logic`) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open. Found while building the Vivec Arena minigame (docs/COMBAT.md).

## Symptom

When a hit knocks the player down (or fatigue drops below zero), the readout says so and the
player loses evasion for the time, but the view does not fall and the player keeps walking and
punching.

## Where

`engine/aga/src/aw_combat.c`: the player's sheet carries the knocked state; nothing in the player's
movement or view reads it.

## How it happened

NPC knockdown has animation frames; the player has only the first-person view and the QuakeC hands,
and stopping input needs a hook in the client move path that the first combat layer did not add.

## Why it was not caught

The rules were tested; the player's presentation was out of scope for the first version.

## Reproduction

Always, with a low-Agility character in the arena: `dbg combat readout on` shows "you are knocked
down" while the player can still move.

## Repair

Not yet. Lower the view and drop the movement and attack input while knocked (the existing input
locks in aw_intro.c are the place), stand up after the knockdown time or when fatigue returns.

## Verification

None yet.

## Prevention

Rules that change a fighter's state list what the player sees and can do in that state.

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
- [DEBUG-MAP-SAVE-VALIDATION-32](DEBUG-MAP-SAVE-VALIDATION-32.md): After a debug map load of an open-world map the autosave fails validation; two of three also report Interior spawn blocked
- [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md): Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields
- RENDER-METADATA-29 (no report page): Native renderer metadata warns as an unknown QuakeC field
- SAVE-EQUIPMENT-29 (no report page): Quickload returns with hands and torch put away

<!-- END GENERATED CATEGORY -->
