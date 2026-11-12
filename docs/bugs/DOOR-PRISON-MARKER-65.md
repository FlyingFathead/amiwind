# DOOR-PRISON-MARKER-65: An invisible door by the census office in Seyda Neen drops the player under the office floor

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 12 November 2026, in v0.0.65-rc3 |
| Where | Seyda Neen, by the Census and Excise Office (the opening's town map) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.65 |
| Severity | high: the player falls into the void below the office and has to load a save |
| Family | Scene changes, arrivals and handoffs (`transitions-arrivals`) |
| Playtest version | v0.0.65-rc3 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.2, engine unknown, world format 0.11 |
| Unknown because | the build receipt does not record source commit, engine commit, world commit |
| Platform or emulator | Raspberry Pi 4B, Amiberry, the v0.0.65-rc3 image with the rc4 test engine (the maintainer's playtest) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.65-rc4 (12 November 2026)._

## Status: 12 November 2026

Open. Cause found; the engine fix is in v0.0.65-rc4 (to be checked in play). The source of the door table is still to be
fixed.

## Symptom

After the opening (the papers handed over, Sellus Gravius' office left for the town), going back into the census
office from the town loaded the office, and the player fell at once below its floor into the dark. The position
readout showed -16 83 2 in the office map; the office floor stands at about 69 there.

## Where

Seyda Neen, beside the Census and Excise Office, on the opening's own town map. The player lands in the census office
map, west of its hall, where the office has no floor.

## When and who

Reported by the maintainer on 12 November 2026, playing the v0.0.65 release candidate (the rc3 image with the rc4 test
engine) on the Raspberry Pi 4B. The same symptom, a fall into the void in the census office, was reported in
v0.0.21-dev2 (`AW-20260928-11`); that repair restored a missing room section, and it is not known
whether that report had this cause too.

## How it was found

The position readout on the Pi gave the landing spot. It is exactly the destination of the door table row with
reference 474482 (office map -16.7 85.2). In Morrowind.esm that reference is the PrisonMarker of the Seyda Neen cell: the
place an arrest in Seyda Neen sends the player to.

## How it happened

- The original stores the jail's destination as a door record (PrisonMarker, model Marker_Prison.nif). It is an editor
  marker: never drawn, never used by hand; the game reads it only to place a jailed player.
- The world door table (tools/world_doors.py, since v0.0.50) keeps prison markers apart: a row of kind "marker" for the
  jail, never a door in a door table.
- The opening's own door table for its Seyda Neen map (tools/prepare_doors.py, rules from v0.0.19 to v0.0.24, unchanged
  since v0.0.35) takes every door record with a destination, the prison marker included. Its tables doors-seyda.txt and
  scene-doors.txt carry reference 474482 as a door labelled Census and Excise Office, with a 67 by 66 unit box along the
  building.
- Using that "door" put the player on the jail spot, which has no floor in the census office map
  (`CENSUS-JAIL-SPOT-NO-FLOOR-65`).

## Why it was not caught

- During the opening the player never uses a door at that spot; every check of the opening followed the registration
  route.
- The image's arrival check passed without checking a single door arrival
  (`ARRIVAL-CHECK-EMPTY-65`).
- The door audits compared the door tables with the original's door records, and the marker is one.

## Reproduction

1. Play the opening to its end: out of Sellus Gravius' office into Seyda Neen.
2. Walk to the census office building by its courtyard door (the marker's box on the opening's town map: x 233 to 300,
   y 8 to 74).
3. Go in there: the census office loads and the player falls below its floor.

Offline: the image's door tables list reference 474482 (doors-seyda.txt and scene-doors.txt).

## Repair

- v0.0.65-rc4: the engine reads the image's prison markers (prison-markers.txt) and never takes a door table row with a
  marker's reference as a door, in any door table (engine/aga/src/aw_scene.c read_links_for, aw_crime.c).
- To do: the opening's door table writer leaves prison markers out at the source, as the world door table does.

## Verification

- The whole v0.0.65-rc3 image: 1,512 door tables scanned; the only rows that are markers are the two Seyda Neen rows of
  the opening's tables. Morrowind.esm has one marker kind among its door records (PrisonMarker, 6 placed: Seyda Neen,
  Pelagiad, Ebonheart, Wolverine Hall, Moonmoth and Buckmoth); the other five are kept out by the world door table.
- To check in play on rc4: nothing by the census building takes the player to the jail spot; the office's own doors
  still work.

## Prevention

- A build check refusing any door table row whose reference is a marker, together with a door-by-door arrival check
  (`ARRIVAL-CHECK-EMPTY-65`).
- The opening's maps and tables follow the world's rules, one path for both (the opening's census office and prison ship
  are the last two maps built the old way).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Scene changes, arrivals and handoffs (`transitions-arrivals`). Cell, region and scene changes keep the player, view, equipment and sound intact. See [families](README.md#families).

- ACTOR-FRAME-FIT-MARGINAL-53 (no report page): The v0.0.53-dev3 image stopped in the actor placement gate: Mivul Urvon (Vivec frame, reference 135239) no longer fits, after the shared table grew by the dancers groups
- ARRIVAL-CEILING-28 (no report page): Coordinate arrivals start inside solid ceiling shell
- [AW-20260928-01](AW-20260928-01.md): Prison ship to deck transition is intermittently very slow or freezes (FS-UAE)
- AW-20260929-04 (no report page): Loading artwork flashes after intro movie
- AW25-01 (no report page): Seyda Neen walking reaches water before the island handoff
- CENSUS-JAIL-SPOT-NO-FLOOR-65 (no report page): The Seyda Neen jail spot in the census office has no floor under it
- [CHIM-32MB-SAVE-ENTRY-48](CHIM-32MB-SAVE-ENTRY-48.md): A save, a start or a console jump into a place marked for 32 MB of Fast RAM was not refused on 16 MB
- [CHIM-INTRO-TP-OTHER-TOWN-33](CHIM-INTRO-TP-OTHER-TOWN-33.md): During the intro stages, travelling to Balmora on CHIM loads Seyda Neen's intro-docks frame map: the player lands in empty water
- [DOOR-BANK-STREAMED-FRAME-51](DOOR-BANK-STREAMED-FRAME-51.md): After a streamed crossing into another region frame, that frame s doors cannot be used: the engine reads only the start frame s door bank (830 of 1,102 entrances)
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

- ARRIVAL-CHECK-EMPTY-65 (no report page): The image's arrival check passes while it checks no door arrival

<!-- END GENERATED CATEGORY -->
