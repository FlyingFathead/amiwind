# ROOM-EMPTY-START-ON-REFERENCES-67: The start of a room without scenery is the middle of the box around its references: the player lands on a person or falls

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 20 November 2026, in v0.0.67 |
| Where | Empty rooms, the build's room start and the engine's arrival |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.67 (last seen) |
| Severity | high: the player lands on the head of a person who attacks, or falls without a floor |
| Family | Scene changes, arrivals and handoffs (`transitions-arrivals`) |
| Playtest version | a test session on the v0.0.67 line |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine unknown, world format unknown |
| Unknown because | found in a test session on the v0.0.67 line; the exact build is in the private notes |
| Platform or emulator | FS-UAE, A1200 68040 preset, JIT, 32 MB Fast |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Scene changes, arrivals and handoffs (`transitions-arrivals`). Cell, region and scene changes keep the player, view, equipment and sound intact. See [families](README.md#families).

- ACTOR-FRAME-FIT-MARGINAL-53 (no report page): The v0.0.53-dev3 image stopped in the actor placement gate: Mivul Urvon (Vivec frame, reference 135239) no longer fits, after the shared table grew by the dancers groups
- [ARRIVAL-CEILING-28](ARRIVAL-CEILING-28.md): Coordinate arrivals start inside solid ceiling shell
- [AW-20260928-01](AW-20260928-01.md): Prison ship to deck transition is intermittently very slow or freezes (FS-UAE)
- [AW-20260929-04](AW-20260929-04.md): Loading artwork flashes after intro movie
- AW25-01 (no report page): Seyda Neen walking reaches water before the island handoff
- [CENSUS-JAIL-SPOT-NO-FLOOR-65](CENSUS-JAIL-SPOT-NO-FLOOR-65.md): The Seyda Neen jail spot in the census office has no floor under it
- [CHIM-32MB-SAVE-ENTRY-48](CHIM-32MB-SAVE-ENTRY-48.md): A save, a start or a console jump into a place marked for 32 MB of Fast RAM was not refused on 16 MB
- [CHIM-INTRO-TP-OTHER-TOWN-33](CHIM-INTRO-TP-OTHER-TOWN-33.md): During the intro stages, travelling to Balmora on CHIM loads Seyda Neen's intro-docks frame map: the player lands in empty water
- [DISTRICT-ARRIVAL-DRIFT-67](DISTRICT-ARRIVAL-DRIFT-67.md): After a teleport into three of Mournhold's districts the player does not stand still: 9 to 48 units of drift in four seconds
- [DISTRICT-DOOR-SIDE-WALL-NO-FOCUS-67](DISTRICT-DOOR-SIDE-WALL-NO-FOCUS-67.md): Two doors of the Royal Palace courtyard cannot be used from outside: the game focuses nothing when the player stands in front of them
- [DOOR-BANK-STREAMED-FRAME-51](DOOR-BANK-STREAMED-FRAME-51.md): After a streamed crossing into another region frame, that frame s doors cannot be used: the engine reads only the start frame s door bank (830 of 1,102 entrances)
- [DOOR-CHECK-SEA-STORE-NAMES-68](DOOR-CHECK-SEA-STORE-NAMES-68.md): The image's door check traced Solstheim's doors in the far sea's world and counted 83 of them as unreachable
- [DOOR-HALL-SWING-DIRECTION-48](DOOR-HALL-SWING-DIRECTION-48.md): The census hall door may open the opposite way from the original game: it turns to closed plus 90 degrees where the original rule gives closed minus 90
- [DOOR-MOVERS-NOT-IN-55](DOOR-MOVERS-NOT-IN-55.md): Gates, trapdoors and bar counter flaps do not move: only doors that turn on a vertical hinge open
- [DOOR-PRISON-MARKER-65](DOOR-PRISON-MARKER-65.md): An invisible door by the census office in Seyda Neen drops the player under the office floor
- [DOOR-USE-ACROSS-FRAME-EDGE-68](DOOR-USE-ACROSS-FRAME-EDGE-68.md): A load door that stands on the edge between two outdoor frames cannot be used from the far side: at Mournhold's ladder down to Bamz-Amschend, the use key does nothing where the way out arrives
- DOOR-USE-BLOCKED-53 (no report page): 50 region-frame entrances cannot be used from where a player can stand: the use ray meets the entrance structure or the ground before the door, or there is no standing spot at it
- [DOOR-USE-COLLISION-FILLED-53](DOOR-USE-COLLISION-FILLED-53.md): 35 region-frame entrances cannot be reached through their converted collision: 24 Daedric shrine steps the player slides off, raised trapdoors under their tower hulls, Dwemer doors inside the terrain chunk
- [ENGINE-SCENE-NAME-BOUND-35](ENGINE-SCENE-NAME-BOUND-35.md): Scene links copied map names into 16-byte fields with strcpy
- INPUT-01 (no report page): Held Ctrl/Shift flight modifiers reset on cell changes
- [INTERIOR-SPAWN-UNDERWATER-41](INTERIOR-SPAWN-UNDERWATER-41.md): Vivec underworks rooms spawn under their water
- [INTRO-ROLES-30](INTRO-ROLES-30.md): NUM_FOR_EDICT bad-pointer crash on a Seyda Neen region change
- [LOAD-CLIENT-HALF-CONNECTED-67](LOAD-CLIENT-HALF-CONNECTED-67.md): A model file a map needs that is missing, or a bad server message, leaves the game on the loading screen: the client stops reading the map half connected
- [LOAD-ERROR-NOT-NAMED-67](LOAD-ERROR-NOT-NAMED-67.md): A place that cannot be reached or loaded is not named on screen: a dbg tp refusal is a console line only, and the failed-load box says only to look at the console
- [LOAD-FATAL-ERRORS-67](LOAD-FATAL-ERRORS-67.md): Memory that runs out or a damaged map file while a place loads ends the game instead of going back where the player was
- [MOURNHOLD-BAZAAR-UNDER-WATER-67](MOURNHOLD-BAZAAR-UNDER-WATER-67.md): Mournhold's Great Bazaar is under water: the player arrives and walks below a water surface, with the breath bar on, and drowns
- [PUNCH-3P-HEART-CHAMBER-67](PUNCH-3P-HEART-CHAMBER-67.md): After a teleport to the Heart Chamber the player's punch at a dreamer does not land or does not show in third-person view; in first person it works
- [ROOM-ARRIVAL-FLOODED-ON-ROOF-67](ROOM-ARRIVAL-FLOODED-ON-ROOF-67.md): Arriving in a flooded room puts the player on top of the room instead of in its water (Sotha Sil, Outer Flooded Halls)
- [ROOM-ARRIVAL-STAND-NO-SPOT-67](ROOM-ARRIVAL-STAND-NO-SPOT-67.md): About 146 room arrivals still find no place to set the player down (flooded rooms closed above, markers inside solid geometry)
- SEYDA-TRANSITION-29 (no report page): v0.0.29-dev1: Cell/sub-cell passage problems around Seyda Neen
- [TP-BAZAAR-ARRIVAL-UNDER-FLOOR-67](TP-BAZAAR-ARRIVAL-UNDER-FLOOR-67.md): The teleport to Mournhold's Great Bazaar leaves the player under the district's floor, in water
- [TRANSITION-EQUIPMENT-29](TRANSITION-EQUIPMENT-29.md): Carried torch blinks out on cell/sub-cell arrival
- TRANSITION-VIEW-29 (no report page): Automatic cell handoff forgets mouse orientation
- TRANSITION-VOICE-29 (no report page): Automatic cell handoff cuts active speech
- [VIEW-AUTOCENTER-29](VIEW-AUTOCENTER-29.md): Reported viewport/yaw resets while walking or crossing cells

Related bugs in other categories:

- [ROOM-EMPTY-PERSON-STANDS-HIGH-67](ROOM-EMPTY-PERSON-STANDS-HIGH-67.md): A person in a room without scenery stays at his placed height, about 80 units above the floor
- [ROOMS-SET-ASIDE-NOT-BUILT-67](ROOMS-SET-ASIDE-NOT-BUILT-67.md): Rooms that no door leads to are set aside and not built, although a script, a teleport or travel can lead there

<!-- END GENERATED CATEGORY -->
