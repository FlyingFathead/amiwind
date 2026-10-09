# CHIM-COURT-BARREL-USE-33: Fargoth's ring barrel in the Census courtyard cannot be used on CHIM

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.33 |
| Where | Seyda Neen CHIM frame maps (tools/chim/frame_map.py), engine aw_opening.c |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33 (last seen) |
| Severity | critical: Blocks the opening sequence for every new game; regression against v0.0.32 (legacy courtyard) |
| Family | Game logic (QuakeC) and saves (`game-logic`) |
| CHIM | Engine streaming and memory ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | v0.0.33 final image (final3-4b26ffc) |
| From commit | source 4b26ffc, engine 4b26ffc, CHIM world 4b26ffc |
| CHIM engine version | CHIM 0.1.0, engine 4b26ffc, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on the v0.0.33 release line, with regression tests. Waiting for the rebuilt final image
and an in-game check.

## Symptom

On the v0.0.33 final image the barrel in the Census and Excise Office courtyard showed no "Take ring: E"
prompt and could not be used. The opening could not move on to the captain. In v0.0.32 (legacy region
maps) it worked.

## Where

- `tools/chim/frame_map.py` `frame_entities`: every `func_wall` with an `aw_ref` from a region map counts as
  a static object. A CHIM frame draws it and collides with it in its chunks and gives it no edict.
- `engine/aga/src/aw_opening.c` `opening_target`: finds the barrel (reference 172851) only as an edict with
  that `aw_ref` and a model.

## How it happened

The CHIM frame maps of Seyda Neen (`seyda-chim`, `sncourt-chim`, `intro_docks-chim`) were made from the
region maps by the rule "a func_wall with a reference number is a static in the chunks". The barrel is
such a func_wall in the region maps (`sncourt.bsp` and `seyda.bsp`: model `*39` / `*78`, origin
120.7 -45.8 46.3). The frame maps of the final image hold no entity with reference 172851, so the engine
had nothing to aim at. The barrel was still drawn and solid, so nothing looked wrong.

## Why it was not caught

The frame-map gates accounted for every static, but only as geometry. No gate knew which references the
engine looks up as edicts, and the CHIM smoke runs did not use the barrel.

## Reproduction

New game on a CHIM image, go through the Census office to the courtyard and aim at the barrel beside the
door: there is no prompt and E does nothing.

## Repair

- One list: `engine/aga/src/aw_activated.h` names every object the engine activates by its reference
  (`AW_REF_COURTYARD_BARREL`, `AW_REF_CENSUS_PAPERS`, `AW_REF_CENSUS_HALL_DOOR`). `aw_opening.c` uses
  those names, and the frame-map builder reads the same lines (`activated_refs`).
- Every CHIM frame map keeps an edict for each listed object found in its region maps: a func_wall with
  the region map's keys and a collision-only brush model (no faces) of the model's box, grown by one
  unit, so the aim trace reaches the edict before the chunk placement.
- The engine counts a world hit inside such a faceless marker's box as the object itself. Edicts with
  drawn faces (legacy maps) keep the plain rule.
- A gate refuses a frame map that misses an edict for a listed object, and regions that disagree about one.

## Verification

- `tests/test_chim_frame_map.py` `ActivatedObjectTests`: the engine header is the one list (no bare
  numbers in `aw_opening.c`), a frame map keeps the marker (faceless, solid, region-map origin), the check
  fails without it, and disagreeing regions are refused.
- `tests/aga_opening_test.c`: on a CHIM frame the barrel is targeted through the chunk collision;
  something in front still blocks it.
- The fixed builder was run on the final image's own staged maps: the three Seyda Neen frame maps gained
  exactly one entity each (the barrel), and nothing else changed.

## Prevention

The engine's list of activated objects and the builder's list of kept edicts come from one header,
and the frame-map gate checks it on every build. A new object the engine looks up by reference is added
to that header.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Game logic (QuakeC) and saves (`game-logic`). QuakeC entities, saves and game state. See [families](README.md#families).

- AW-20260928-10 (no report page): Interior door animation and sound missing
- AW-20260928-12 (no report page): Downstairs interior doors cannot open
- AW-20260928-19 (no report page): Courtyard barrel incorrectly says empty
- AW25-06 (no report page): Quicksave shown as empty; save ordering confusing
- [CENSUS-DOOR-STUCK-29](CENSUS-DOOR-STUCK-29.md): Player stuck after opening Census Office hall door
- CLOCK-01 (no report page): Automatic clock dropped fractional milliseconds each frame
- [COMBAT-FIST-BLOCK-33](COMBAT-FIST-BLOCK-33.md): A fighter with a shield blocks while fighting with fists
- [COMBAT-HIT-RECOVERY-33](COMBAT-HIT-RECOVERY-33.md): Fatigue hits did not stagger, and knockdowns lasted half a second too long
- [COMBAT-NO-CONDITION-33](COMBAT-NO-CONDITION-33.md): Weapon and shield condition were ignored in combat
- [COMBAT-NOT-SAVED-33](COMBAT-NOT-SAVED-33.md): Combat state and NPC deaths are not saved
- [COMBAT-PLAYER-ATTACK-TYPE-33](COMBAT-PLAYER-ATTACK-TYPE-33.md): The player's attack type and swing strength were random
- [COMBAT-PLAYER-KNOCKDOWN-33](COMBAT-PLAYER-KNOCKDOWN-33.md): The player's knockdown and knockout exist only in the combat rules
- [DEBUG-MAP-SAVE-VALIDATION-32](DEBUG-MAP-SAVE-VALIDATION-32.md): After a debug map load of an open-world map the autosave fails validation; two of three also report Interior spawn blocked
- [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md): Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields
- RENDER-METADATA-29 (no report page): Native renderer metadata warns as an unknown QuakeC field
- SAVE-EQUIPMENT-29 (no report page): Quickload returns with hands and torch put away

<!-- END GENERATED CATEGORY -->
