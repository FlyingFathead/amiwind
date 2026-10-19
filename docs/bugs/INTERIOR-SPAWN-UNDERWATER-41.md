# INTERIOR-SPAWN-UNDERWATER-41: Vivec underworks rooms spawn under their water

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 16 October 2026, in v0.0.41 |
| Where | Interior converter spawn point (prepare_area.build_room) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.42 |
| Severity | medium: map, dbg tp and a direct start put the player 141 units under the water of Hlaalu Underworks (seven underworks rooms); doors unaffected |
| Family | Scene changes, arrivals and handoffs (`transitions-arrivals`) |
| Playtest version | 2026_10_16_v0.0.41_release_ce7ace6 |
| From commit | source and engine ce7ace6 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

## Status: 17 October 2026

Fixed on the v0.0.42 line. Present in v0.0.41 and earlier.

## Symptom

Loading Vivec, Hlaalu Underworks by its map name (the console's map command, `dbg tp` to the room, a direct
start into the room) puts the player in the sewer water: the view is the blue underwater fog with the corpse
in front. Found on 16 October 2026 while taking stills of the room in FS-UAE.

## Where

The room's own spawn point (info_player_start), written by the interior converter
(`tools/prepare_area.py`). Seven rooms are affected: the Foreign Quarter, Hall, Hlaalu, Redoran, St. Delyn,
St. Olms and Telvanni Underworks. Doors are not affected: every door keeps its own original arrival in the
door tables.

## How it happened

The converter took the first original arrival into the room as its spawn. In these rooms the first arrival
is the canal grate: the player swims in from the canal and arrives under the water (Hlaalu Underworks: water
at 0, arrival at -141, original units).

## Why it was not caught

No check compares the spawn point with the room's water height.

## Reproduction

`map vhi013` in the console of a build that holds Hlaalu Underworks.

## Repair

The spawn is the first original arrival that is not under the room's water (`prepare_area.spawn_entrance`); a
room whose arrivals are all under water keeps the first one. `AMIWIND_ROOM_SPAWN=first` keeps the earlier
rule. Hlaalu Underworks now spawns at a dry arrival (z 96).

## Verification

`tests/test_interior_limits_steps.py` (RoomSpawnTests); the seven rooms counted over every listed room
(203 rooms: only these seven move).

## Prevention

The spawn rule is tested; a room converter change that moves spawns is visible in the room receipts.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Scene changes, arrivals and handoffs (`transitions-arrivals`). Cell, region and scene changes keep the player, view, equipment and sound intact. See [families](README.md#families).

- ARRIVAL-CEILING-28 (no report page): Coordinate arrivals start inside solid ceiling shell
- [AW-20260928-01](AW-20260928-01.md): Prison ship to deck transition is intermittently very slow or freezes (FS-UAE)
- AW-20260929-04 (no report page): Loading artwork flashes after intro movie
- AW25-01 (no report page): Seyda Neen walking reaches water before the island handoff
- [CHIM-INTRO-TP-OTHER-TOWN-33](CHIM-INTRO-TP-OTHER-TOWN-33.md): During the intro stages, travelling to Balmora on CHIM loads Seyda Neen's intro-docks frame map: the player lands in empty water
- [ENGINE-SCENE-NAME-BOUND-35](ENGINE-SCENE-NAME-BOUND-35.md): Scene links copied map names into 16-byte fields with strcpy
- INPUT-01 (no report page): Held Ctrl/Shift flight modifiers reset on cell changes
- [INTRO-ROLES-30](INTRO-ROLES-30.md): NUM_FOR_EDICT bad-pointer crash on a Seyda Neen region change
- SEYDA-TRANSITION-29 (no report page): v0.0.29-dev1: Cell/sub-cell passage problems around Seyda Neen
- TRANSITION-EQUIPMENT-29 (no report page): Carried torch blinks out on cell/sub-cell arrival
- TRANSITION-VIEW-29 (no report page): Automatic cell handoff forgets mouse orientation
- TRANSITION-VOICE-29 (no report page): Automatic cell handoff cuts active speech
- VIEW-AUTOCENTER-29 (no report page): Reported viewport/yaw resets while walking or crossing cells

<!-- END GENERATED CATEGORY -->
