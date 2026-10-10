# DEBUG-MAP-SAVE-VALIDATION-32: After a debug map load of an open-world map the autosave fails validation; two of three also report Interior spawn blocked

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev3 |
| Where | Autosave after debug map load of open-world maps (aw_save.c) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev3 (last seen) |
| Severity | low: Debug path only; earlier saves are kept. |
| Family | Game logic (QuakeC) and saves (`game-logic`) |
| Playtest version | v0.0.32-dev3 |
| From commit | source and engine 91a7eeb |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open; cause unknown. Found in the v0.0.32-dev3 smoke test (FS-UAE, build from source 91a7eeb).
Seen on the debug path only.

## Symptom

In one session, after an autosave had just worked in Balmora ("Saved Autosave 2"), the console
command `map` was used to load three open-world maps:

| Map | Placement | Save |
| --- | --- | --- |
| `vf0291` | "Interior spawn blocked; use dbg noclip to inspect." | "Save state validation failed; previous saves retained." |
| `vf2386` | "Interior spawn: 0 0 -46" | "Save state validation failed; previous saves retained." |
| `vf2485` | "Interior spawn blocked; use dbg noclip to inspect." | "Save state validation failed; previous saves retained." |

The save code refused to write and kept the earlier saves, as designed; the fault is that the state
it was given did not pass validation.

## Where

- `engine/aga/src/aw_save.c` (`AW_SaveWrite`, autosave after a scene change) and
  `engine/aga/src/aw_save_codec.c` (`AW_SaveEncode`): the message comes from the encoder's
  validation.
- `engine/aga/src/aw_scene.c` (`AW_SceneSpawn`, `AW_InteriorPlace`): a map loaded with `map`
  rather than a scene change places the player with the interior standing-spot search around the
  map's start point.

## How it happened

Unknown. Open-world map names are valid save scenes (`AW_MapId` accepts `vfNNNN`), so the scene name
alone does not explain it. Candidates: a value outside the encoder's limits (position, actors
captured on the map, harvest state, story fields) after a load that bypasses the scene change; for
the blocked spawns, a start point more than the search's 88 units above the ground or inside
solid.

## Why it was not caught

The save tests cover saves after normal scene changes; debug map loads are not in the save tests,
and a refused save is only a console line.

## Reproduction

New game to release, then in the console: `map vf0291` (or `vf2386`, `vf2485`); wait for the
autosave a few seconds later and read the console.

## Repair

Not yet. First find which field fails (a debug print of the failing field in the encoder, or a
native test with a state captured after `map vf2386`). Then check whether a normal crossing into an
open-world map hits the same failure; if it does, this is not a debug-only fault.

## Verification

Pending.

## Prevention

Proposed: a save round trip after a debug map load and after an open-world crossing in the save
tests.

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
- [COMBAT-SETUP-DICE-BLOCK-33](COMBAT-SETUP-DICE-BLOCK-33.md): The Arena setup offers no dice/style choice before a fight, and there is no block button
- [ENGINE-ANGLEMOD-RANGE-35](ENGINE-ANGLEMOD-RANGE-35.md): anglemod returned 360 for -360 and passed NaN and out-of-range values on
- [ENGINE-QC-ARGS-SYSERROR-35](ENGINE-QC-ARGS-SYSERROR-35.md): Bad QuakeC sound arguments stopped the program; lightstyle had no range check
- [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md): Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields
- RENDER-METADATA-29 (no report page): Native renderer metadata warns as an unknown QuakeC field
- SAVE-EQUIPMENT-29 (no report page): Quickload returns with hands and torch put away
- [SERVER-FRAME-ARRIVAL-33](SERVER-FRAME-ARRIVAL-33.md): The server frame costs about 226 ms per frame at the Balmora arrival camera on a slow 68040

<!-- END GENERATED CATEGORY -->
