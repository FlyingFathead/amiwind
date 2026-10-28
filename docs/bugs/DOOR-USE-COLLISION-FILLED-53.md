# DOOR-USE-COLLISION-FILLED-53: 35 region-frame entrances cannot be reached through their converted collision

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 26 October 2026, in v0.0.53-dev2 |
| Where | CHIM collision at load doors: tower and fort hulls, terrain chunks (region frames) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.54-dev2 |
| Severity | medium: 10 of 1,102 exterior entrances cannot be entered; the other 1,092 can |
| Family | Scene changes, arrivals and handoffs (`transitions-arrivals`) |
| CHIM | Engine streaming and memory ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_26_v0.0.53-dev2_dev2_eb5511aa |
| From commit | source eb5511a, engine eb5511a, CHIM world eb5511a |
| CHIM engine version | CHIM 0.2.2, engine eb5511a, world format 0.13 |
| Platform or emulator | not in game (found by the native door engine check over the image) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.53 (27 October 2026)._

## Status: 27 October 2026

Open, scheduled for v0.0.54. Found on 26 October 2026 by the door engine check of the v0.0.53 builds (the engine's own
door code over the finished image), after the doorway slack of
[DOOR-USE-BLOCKED-53](../BUGS.md) had made the other entrances usable. The fix changes the CHIM world's collision, so
it comes with a v0.0.54 build; `config/door-check-baseline.json` holds 1,067 usable entrances until then.

## Symptom

35 of the 1,102 exterior entrances keep the use key out of reach, because the converted collision fills the space the
player needs at the door:

- 24 Daedric shrine doors whose step collision is steeper than the walk, so the player slides back down the steps
  (confirmed in game at Kaushtarari and Ebernanit);
- 7 raised trapdoors under their tower or fort hulls (the Redoran guard towers of Ald-ruhn and Maar Gan, the Ald Velothi
  outpost, the Indarys Manor fort): the hull is solid from 2 to 44 units above the trapdoor;
- 2 Dwemer doors (Nchuleft, Bthungthumz) inside the frame's terrain chunk collision, which stands 90 to 124 units over
  the threshold where the original ground is at the threshold;
- an Ald-ruhn Redoran hut door and the Unmarked Shipwreck's upper trapdoor.

## Where

The CHIM collision at load doors in the region frames: the expanded standing hull of curved shrine steps, the tower and
fort hulls, and the terrain chunks near doors.

## What has to be done

Check each class against the original (OpenMW) and fix the collision conversion, not the doors one by one; then the
door engine check's usable count goes up to 1,102 and its baseline with it.

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
- [DOOR-BANK-STREAMED-FRAME-51](DOOR-BANK-STREAMED-FRAME-51.md): After a streamed crossing into another region frame, that frame s doors cannot be used: the engine reads only the start frame s door bank (830 of 1,102 entrances)
- DOOR-HALL-SWING-DIRECTION-48 (no report page): The census hall door may open the opposite way from the original game: it turns to closed plus 90 degrees where the original rule gives closed minus 90
- DOOR-USE-BLOCKED-53 (no report page): 50 region-frame entrances cannot be used from where a player can stand: the use ray meets the entrance structure or the ground before the door, or there is no standing spot at it
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

- [CHIM-REGION-DOORS-NO-PROMPT-42](CHIM-REGION-DOORS-NO-PROMPT-42.md): Doors in CHIM region cells show no entrance at all (no prompt, not even Interior unavailable), e.g. every door in Khuul
- DOOR-ENTRANCE-AUDIT-51 (no report page): Requested: an entrance check in every build: each exterior entrance of the original must have a door that leads into its interior, found from the map, missing ones listed

<!-- END GENERATED CATEGORY -->
