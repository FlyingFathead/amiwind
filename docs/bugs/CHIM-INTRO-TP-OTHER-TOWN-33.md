# CHIM-INTRO-TP-OTHER-TOWN-33: travelling to Balmora during the intro lands in Seyda Neen's docks frame

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 9 October 2026, in v0.0.33 |
| Where | engine aw_region.c AW_RegionSelect / AW_RegionWorldModel |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33 (last seen) |
| Severity | high: dbg tp balmora (or any travel to another CHIM town) between the ship and the Census office lands in an empty frame; saves made there reload into it |
| Family | Scene changes, arrivals and handoffs (`transitions-arrivals`) |
| CHIM | Engine streaming and memory ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | v0.0.33 final image (final2-f583c7b) |
| From commit | source f583c7b, engine f583c7b, CHIM world f583c7b |
| CHIM engine version | CHIM 0.1.0, engine f583c7b, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on the v0.0.33 release line, with a regression test.

## Symptom

The smoke test of the v0.0.33 final image started a new game and used `dbg tp balmora` from the prison
ship: the console said "Balmora (intro docks): CHIM frame map maps/intro_docks-chim.bsp" and the player
stood in empty water. A save made there reloaded into the same place.

## Where

`aw_region.c`: `AW_RegionSelect` and `AW_RegionWorldModel` choose the map of a town scene. Between the
ship and the Census office (the intro stages) they chose the intro docks' frame map for any town on CHIM.

## How it happened

The intro docks' frame map was added for Seyda Neen, whose intro uses it; the condition checked only
the story stage, not the town.

## Why it was not caught

The region test covered Seyda Neen's intro and Balmora outside the intro; MiniWind builds have no
intro docks.

## Reproduction

New game, then `dbg tp balmora` before leaving the Census office.

## Repair

The docks' frame map is chosen only for Seyda Neen (the town with the intro scenes); every other town
takes its own frame map in every story stage.

## Verification

`tests/aga_region_test.c` (Balmora during the intro stages takes `maps/balmora-chim.bsp`); the smoke of the
rebuilt final image repeats the teleport.

## Prevention

The full-image smoke travels to every CHIM town from the ship.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Scene changes, arrivals and handoffs (`transitions-arrivals`). Cell, region and scene changes keep the player, view, equipment and sound intact. See [families](README.md#families).

- ARRIVAL-CEILING-28 (no report page): Coordinate arrivals start inside solid ceiling shell
- [AW-20260928-01](AW-20260928-01.md): Prison ship to deck transition is intermittently very slow or freezes (FS-UAE)
- AW-20260929-04 (no report page): Loading artwork flashes after intro movie
- AW25-01 (no report page): Seyda Neen walking reaches water before the island handoff
- INPUT-01 (no report page): Held Ctrl/Shift flight modifiers reset on cell changes
- [INTRO-ROLES-30](INTRO-ROLES-30.md): NUM_FOR_EDICT bad-pointer crash on a Seyda Neen region change
- SEYDA-TRANSITION-29 (no report page): v0.0.29-dev1: Cell/sub-cell passage problems around Seyda Neen
- TRANSITION-EQUIPMENT-29 (no report page): Carried torch blinks out on cell/sub-cell arrival
- TRANSITION-VIEW-29 (no report page): Automatic cell handoff forgets mouse orientation
- TRANSITION-VOICE-29 (no report page): Automatic cell handoff cuts active speech
- VIEW-AUTOCENTER-29 (no report page): Reported viewport/yaw resets while walking or crossing cells

<!-- END GENERATED CATEGORY -->
