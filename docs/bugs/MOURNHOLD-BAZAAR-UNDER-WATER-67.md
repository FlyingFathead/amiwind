# MOURNHOLD-BAZAAR-UNDER-WATER-67: Mournhold's Great Bazaar is under water: the player arrives and walks below a water surface, with the breath bar on, and drowns

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 18 November 2026, in v0.0.67-dev2 |
| Where | the Mournhold test build of 104174ce (the first build with Mournhold's five outdoor districts): dbg tp greatbazaar and a walk there show a blue tint, the water surface from below and the breath bar running out (arrival local z -43 and -49 in the district's map mh0002). In Tribunal's data all five districts are flagged as having water but give no water height; the engine puts the surface at height 0, as OpenMW reads such a flag. The Great Bazaar's streets lie below 0 and the Plaza Brindisi Dorom's floor just above it (a water plane at its feet). The districts lie outside the regular map area of the game, so the normal water level should not apply there; the original has no water in these streets. |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.67-dev2 (last seen) |
| Severity | critical: a whole district of the city is unplayable: the player drowns in the Great Bazaar; the maintainer set it as P0 |
| Family | Scene changes, arrivals and handoffs (`transitions-arrivals`) |
| Playtest version | v0.0.67-dev2 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.2, engine unknown, world format 0.11 |
| Unknown because | the build receipt does not record source commit, engine commit, world commit |
| Platform or emulator | the Mournhold test build of 104174ce (FS-UAE, 32 MB Fast) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-11-18: reported in v0.0.67-dev2
- 2026-11-18 16:29 +0200: v0.0.67-dev2: Measured on the test image's own collision, in the original's units: in the Great Bazaar's western cell the surfaces a player can stand on lie between 25 and 297, none of them under 0; the street under the arrival point is at 297.
- 2026-11-18 18:05 +0200: v0.0.67-dev2: The arrival read second by second on the same test image: one second after the teleport by the district's name the eye is at frame-local -53 (the street is at 74) and it stays there: the player is set down low at once, he does not fall.

<!-- END GENERATED TIMELINE -->

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
- [DOOR-HALL-SWING-DIRECTION-48](DOOR-HALL-SWING-DIRECTION-48.md): The census hall door may open the opposite way from the original game: it turns to closed plus 90 degrees where the original rule gives closed minus 90
- [DOOR-MOVERS-NOT-IN-55](DOOR-MOVERS-NOT-IN-55.md): Gates, trapdoors and bar counter flaps do not move: only doors that turn on a vertical hinge open
- [DOOR-PRISON-MARKER-65](DOOR-PRISON-MARKER-65.md): An invisible door by the census office in Seyda Neen drops the player under the office floor
- DOOR-USE-BLOCKED-53 (no report page): 50 region-frame entrances cannot be used from where a player can stand: the use ray meets the entrance structure or the ground before the door, or there is no standing spot at it
- [DOOR-USE-COLLISION-FILLED-53](DOOR-USE-COLLISION-FILLED-53.md): 35 region-frame entrances cannot be reached through their converted collision: 24 Daedric shrine steps the player slides off, raised trapdoors under their tower hulls, Dwemer doors inside the terrain chunk
- [ENGINE-SCENE-NAME-BOUND-35](ENGINE-SCENE-NAME-BOUND-35.md): Scene links copied map names into 16-byte fields with strcpy
- INPUT-01 (no report page): Held Ctrl/Shift flight modifiers reset on cell changes
- [INTERIOR-SPAWN-UNDERWATER-41](INTERIOR-SPAWN-UNDERWATER-41.md): Vivec underworks rooms spawn under their water
- [INTRO-ROLES-30](INTRO-ROLES-30.md): NUM_FOR_EDICT bad-pointer crash on a Seyda Neen region change
- [LOAD-CLIENT-HALF-CONNECTED-67](LOAD-CLIENT-HALF-CONNECTED-67.md): A model file a map needs that is missing, or a bad server message, leaves the game on the loading screen: the client stops reading the map half connected
- [LOAD-ERROR-NOT-NAMED-67](LOAD-ERROR-NOT-NAMED-67.md): A place that cannot be reached or loaded is not named on screen: a dbg tp refusal is a console line only, and the failed-load box says only to look at the console
- [LOAD-FATAL-ERRORS-67](LOAD-FATAL-ERRORS-67.md): Memory that runs out or a damaged map file while a place loads ends the game instead of going back where the player was
- [PUNCH-3P-HEART-CHAMBER-67](PUNCH-3P-HEART-CHAMBER-67.md): After a teleport to the Heart Chamber the player's punch at a dreamer does not land or does not show in third-person view; in first person it works
- SEYDA-TRANSITION-29 (no report page): v0.0.29-dev1: Cell/sub-cell passage problems around Seyda Neen
- [TP-BAZAAR-ARRIVAL-UNDER-FLOOR-67](TP-BAZAAR-ARRIVAL-UNDER-FLOOR-67.md): The teleport to Mournhold's Great Bazaar leaves the player under the district's floor, in water
- [TRANSITION-EQUIPMENT-29](TRANSITION-EQUIPMENT-29.md): Carried torch blinks out on cell/sub-cell arrival
- TRANSITION-VIEW-29 (no report page): Automatic cell handoff forgets mouse orientation
- TRANSITION-VOICE-29 (no report page): Automatic cell handoff cuts active speech
- [VIEW-AUTOCENTER-29](VIEW-AUTOCENTER-29.md): Reported viewport/yaw resets while walking or crossing cells

Related bugs in other categories:

- [DISTRICT-PLACED-THINGS-NO-ROW-67](DISTRICT-PLACED-THINGS-NO-ROW-67.md): In Mournhold's districts no container, item, activator or door sign can be aimed at: their rows are keyed as a room's, and the game outdoors asks for the cells around the player

<!-- END GENERATED CATEGORY -->
