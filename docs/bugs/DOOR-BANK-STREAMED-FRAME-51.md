# DOOR-BANK-STREAMED-FRAME-51: After a streamed crossing into another region frame, that frame's doors cannot be used: the engine reads only the start frame's door bank (830 of 1,102 entrances)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 25 October 2026, in v0.0.51 |
| Where | engine/aga/src/aw_scene.c read_links, aimed_door, door_status (sv.name, not the logical frame) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.53 |
| Severity | critical: Every region entrance (830 of 1,102) is dead once the player walks into its frame; five found in two hours of play |
| Family | Scene changes, arrivals and handoffs (`transitions-arrivals`) |
| CHIM | Engine streaming and memory ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_25_v0.0.51_final_d74cc652 |
| From commit | source 3c0c6c8, engine 3c0c6c8, CHIM world 3c0c6c8 |
| CHIM engine version | CHIM 0.2.2, engine 3c0c6c8, world format 0.12 |
| Platform or emulator | FS-UAE, JIT, A1200 profile, 32 MB Fast RAM |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.52 (26 October 2026)._

## Status: 26 October 2026

Open. Found on 25 October 2026 by the door audit (`tools/door_audit.py`), from the five dead entrances the maintainer
reported (CHIM-REGION-DOORS-NO-PROMPT-42). Not fixed in v0.0.52.

## Symptom

With `chim crossing 1` (the type 1 window, the default since v0.0.47) a walk into another region frame streams that
frame in, and the engine still names the start frame as the scene. The doors of the frame the player now stands in
give no prompt and cannot be used, although each is placed, linked and correct in its own frame; each of the five
reported ones was 14 to 35 map units from the player, inside the 56-unit reach. Of the 1,102 exterior entrances, all
usable on arrival by a level change, only 272 (the Balmora, Seyda Neen and Vivec town frames) are usable after walking
in: Grazelands 0 of 67, Azure's Coast 0 of 171, Red Mountain 0 of 12. Five were found in two hours of play.

## Where

`engine/aga/src/aw_scene.c`: `read_links` reads the door bank of the start frame's name, and `aimed_door`,
`door_status`, `AW_SceneActivate` and the door-ready check compare against it, while the frame the player stands in
is the logical scene (`logical_map` and `logical_offset`, already used for crossings). The hinged doors
(`aw_hinged_door.c`) have to be checked the same way.

## What has to be done

Read the door bank of the logical frame (or of every frame the window holds), with the player's eye moved by the
logical offset, in `read_links`, `aimed_door`, `door_status`, `AW_SceneActivate` and the door-ready check, and check
the hinged doors the same way. Then run the door audit again: every entrance must be usable after walking in, as it
is on arrival by a level change.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Scene changes, arrivals and handoffs (`transitions-arrivals`). Cell, region and scene changes keep the player, view, equipment and sound intact. See [families](README.md#families).

- ACTOR-FRAME-FIT-MARGINAL-53 (no report page): The v0.0.53-dev3 image stopped in the actor placement gate: Mivul Urvon (Vivec frame, reference 135239) no longer fits, after the shared table grew by the dancers groups
- ARRIVAL-CEILING-28 (no report page): Coordinate arrivals start inside solid ceiling shell
- [AW-20260928-01](AW-20260928-01.md): Prison ship to deck transition is intermittently very slow or freezes (FS-UAE)
- AW-20260929-04 (no report page): Loading artwork flashes after intro movie
- AW25-01 (no report page): Seyda Neen walking reaches water before the island handoff
- [CHIM-32MB-SAVE-ENTRY-48](CHIM-32MB-SAVE-ENTRY-48.md): A save, a start or a console jump into a place marked for 32 MB of Fast RAM was not refused on 16 MB
- [CHIM-INTRO-TP-OTHER-TOWN-33](CHIM-INTRO-TP-OTHER-TOWN-33.md): During the intro stages, travelling to Balmora on CHIM loads Seyda Neen's intro-docks frame map: the player lands in empty water
- DOOR-HALL-SWING-DIRECTION-48 (no report page): The census hall door may open the opposite way from the original game: it turns to closed plus 90 degrees where the original rule gives closed minus 90
- [DOOR-MOVERS-NOT-IN-55](DOOR-MOVERS-NOT-IN-55.md): Gates, trapdoors and bar counter flaps do not move: only doors that turn on a vertical hinge open
- DOOR-USE-BLOCKED-53 (no report page): 50 region-frame entrances cannot be used from where a player can stand: the use ray meets the entrance structure or the ground before the door, or there is no standing spot at it
- [DOOR-USE-COLLISION-FILLED-53](DOOR-USE-COLLISION-FILLED-53.md): 35 region-frame entrances cannot be reached through their converted collision: 24 Daedric shrine steps the player slides off, raised trapdoors under their tower hulls, Dwemer doors inside the terrain chunk
- [ENGINE-SCENE-NAME-BOUND-35](ENGINE-SCENE-NAME-BOUND-35.md): Scene links copied map names into 16-byte fields with strcpy
- INPUT-01 (no report page): Held Ctrl/Shift flight modifiers reset on cell changes
- [INTERIOR-SPAWN-UNDERWATER-41](INTERIOR-SPAWN-UNDERWATER-41.md): Vivec underworks rooms spawn under their water
- [INTRO-ROLES-30](INTRO-ROLES-30.md): NUM_FOR_EDICT bad-pointer crash on a Seyda Neen region change
- SEYDA-TRANSITION-29 (no report page): v0.0.29-dev1: Cell/sub-cell passage problems around Seyda Neen
- TRANSITION-EQUIPMENT-29 (no report page): Carried torch blinks out on cell/sub-cell arrival
- TRANSITION-VIEW-29 (no report page): Automatic cell handoff forgets mouse orientation
- TRANSITION-VOICE-29 (no report page): Automatic cell handoff cuts active speech
- VIEW-AUTOCENTER-29 (no report page): Reported viewport/yaw resets while walking or crossing cells

Related bugs in other categories:

- DOOR-ENTRANCE-AUDIT-51 (no report page): Requested: an entrance check in every build: each exterior entrance of the original must have a door that leads into its interior, found from the map, missing ones listed

<!-- END GENERATED CATEGORY -->
