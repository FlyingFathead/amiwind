# COMBAT-NOT-SAVED-33: Combat state and NPC deaths are not saved

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | engine/aga/src/aw_combat.c (combat slots), aw_save.c (saves NPC health only) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: After loading, nobody is hostile and an NPC killed in normal play stands again; the arena minigame is unaffected (its session is restored). |
| Family | Game logic (QuakeC) and saves (`game-logic`) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open (a design limit of the first combat layer). Found while building the Vivec Arena minigame
(docs/COMBAT.md). The minigame itself is unaffected: its session restores the captured game.

## Symptom

Hit a resident in normal play and save during the fight: after loading, nobody is hostile. Kill a
resident, save and load: it stands again with its saved health.

## Where

`engine/aga/src/aw_combat.c` keeps the hostile NPCs in four fixed slots that the save does not
write; `aw_save.c` stores each NPC's health only; the QuakeC resident spawn knows no dead state.

## How it happened

The first combat layer was built for the arena test room, whose session is captured and restored,
so saving combat was left for later.

## Why it was not caught

No save format change was wanted for the debug minigame; the gap shows only in normal play.

## Reproduction

Always: punch a resident until it dies, save, load.

## Repair

Not yet. Needs a save record per hostile or dead NPC (record reference, health, fatigue, state) or
the original game's own dead-actor handling; a save format change, so it waits for an owner
decision.

## Verification

None yet.

## Prevention

Every new piece of runtime state names its save story in its design note (docs/COMBAT.md, Known
limits, now does).

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
- [COMBAT-PLAYER-ATTACK-TYPE-33](COMBAT-PLAYER-ATTACK-TYPE-33.md): The player's attack type and swing strength were random
- [COMBAT-PLAYER-KNOCKDOWN-33](COMBAT-PLAYER-KNOCKDOWN-33.md): The player's knockdown and knockout exist only in the combat rules
- [DEBUG-MAP-SAVE-VALIDATION-32](DEBUG-MAP-SAVE-VALIDATION-32.md): After a debug map load of an open-world map the autosave fails validation; two of three also report Interior spawn blocked
- [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md): Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields
- RENDER-METADATA-29 (no report page): Native renderer metadata warns as an unknown QuakeC field
- SAVE-EQUIPMENT-29 (no report page): Quickload returns with hands and torch put away

<!-- END GENERATED CATEGORY -->
