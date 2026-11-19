# DOOR-ARRIVAL-INSIDE-ACTOR-66: Coming back out of the census office onto the Seyda Neen street after a kill, the player arrives inside the guard who has walked to the door and stays stuck

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 2 times; something has to be done

- Reported with v0.0.66-dev7 at 2026-11-15 (time not recorded): Seen on the v0.0.66-dev7 image (FS-UAE at 32 MB Fast, JIT): the guard (128967) at 268 44 39 by the arrival point 266 36 55 after the return; "player is stuck." 3,498 times until part A ended.
- Reported with v0.0.66-dev9 at 2026-11-15 (time not recorded): Looked for on the v0.0.66-dev9 image (FS-UAE at 32 MB Fast, JIT): no "player is stuck." line in either part of the opening journey and no "Arrival:" line after step 6, because no actor stood on the street door's arrival point; the case was not exercised in play.

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 15 November 2026, in v0.0.66-dev5 |
| Where | Seyda Neen, the street door of the census office (113833) and its arrival point |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.66-dev5, v0.0.66-dev7 (last seen) |
| Severity | medium: the player is left inside the guard after a crime; whether the player can walk out is not yet seen |
| Family | Object placement and in-game geometry (`placement-geometry`) |
| Playtest version | 2026_11_15_v0.0.66-dev5_full-v0.0.66-dev5_18eb63f |
| From commit | source and engine 18eb63f |
| CHIM engine version | none: legacy engine |
| Platform or emulator | FS-UAE 3.1.66, JIT, A1200 68040 preset, 32 MB Fast |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-11-15: reported in v0.0.66-dev5
- 2026-11-15: seen again in v0.0.66-dev7: Seen on the v0.0.66-dev7 image (FS-UAE at 32 MB Fast, JIT): the guard (128967) at 268 44 39 by the arrival point 266 36 55 after the return; "player is stuck." 3,498 times until part A ended.
- 2026-11-15: seen again in v0.0.66-dev9: Looked for on the v0.0.66-dev9 image (FS-UAE at 32 MB Fast, JIT): no "player is stuck." line in either part of the opening journey and no "Arrival:" line after step 6, because no actor stood on the street door's arrival point; the case was ...

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.66-dev10 (15 November 2026)._

## Status: 15 November 2026

Fixed in source, covered by tests, to be confirmed in play. The v0.0.66-dev9 opening journey did not exercise the case: no actor stood on the street door's arrival point after step 6 (no "Arrival:" line) and the console of neither part has a "player is stuck." line. The entry stays open until a build shows the arrival with an actor on the point and the player walking away.

## Symptom

Seen in the opening journey on the v0.0.66-dev5 image and on the v0.0.66-dev7 image: in step 6 the player kills a resident on the street, goes into the census office and comes back out through its street door (`113833`). The guard (`128967`), who walks by his Wander package, had walked to the door while the player was inside and stood 8 units from the arrival point. The console then printed "Unstuck." three times and "player is stuck." every frame until the session ended.

## Where

Seyda Neen, the street door of the census office (`113833`) and its arrival point; the actors' join after an arrival (aw_scene.c) and the collision of two overlapping bodies (world.c).

## How it happened

Outdoors the scene's actors join after the arrival's check: they are queued with the arrival's ring, spawned over the next ticks and then moved to where the saved changes left them. The guard had walked to the door by his Wander package and came back 8 units from the arrival point, his box overlapping the player's. The engine's box clip then held both: a sweep that starts inside the sum of two boxes is solid until one frame's move leaves it whole, and the stuck search, which counted every body, failed in every frame. In the native test at the measured boxes, ten frames of walking away moved the player 0 units. Related: `WANDER-DOOR-RULE-66`.

## Why it was not caught

The journey stood still after the return (its steps 7 and 8 need no walking), so whether a player could walk out was not seen. The journey's kill took the nearest resident, so where the guard stood decided what was seen (`JOURNEY-STEP6-VICTIM-NEAREST-66`, fixed in v0.0.66-dev9).

## Reproduction

Kill a resident on the street, enter the census office and come back out by the street door while the guard stands by it.

## Repair

Fixed in source in v0.0.66-dev9: two bodies that already overlap collide as the original game's actors do, only a move toward the other's centre stops, so they walk apart (world.c, `aw_body_overlap 1`); the stuck search leaves other bodies out; and for three seconds after an arrival an actor that joins onto the player steps the player once to the nearest clear standing spot beside the point (aw_scene.c, `aw_arrival_clear 1`, the console line "Arrival: ... stood on the arrival point"). Both switches are on in the default configuration; 0 gives the old behaviour back. Tests: the walking-away case in tests/aga_body_overlap_test.c and the arrival case in tests/aga_scene_test.c.

## Verification

Not verified in play yet. The v0.0.66-dev9 journey did not exercise the case. A journey or a play session in which an actor stands on the arrival point after the return shows the "Arrival:" line and no "player is stuck." line.

## Prevention

The opening journey names its victim by reference, so the guard's place no longer decides whether the step shows the case; a step that puts an actor on the arrival point on purpose is the way to see it every time.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Object placement and in-game geometry (`placement-geometry`). Placed objects match the original (OpenMW A/B at the same pose). See [families](README.md#families).

- [AW-20260928-03](AW-20260928-03.md): Silt Strider landing geometry
- AW-20260928-04 (no report page): Invisible barriers across plank
- [AW-20260928-06](AW-20260928-06.md): Player can leave pier and become stranded
- AW-20260928-11 (no report page): Census missing floor and wall / falling into void
- [AW-20260928-20](AW-20260928-20.md): Census clipped outside room near captain wing
- [BALMORA-FLAMES-IN-SKY-51](BALMORA-FLAMES-IN-SKY-51.md): Four fire sprites in Balmora with no fire under them: two float in the air, two stand on the ground
- [CENSUS-BACK-TABLE-NOT-DRAWN-58](CENSUS-BACK-TABLE-NOT-DRAWN-58.md): The back-room table of the Census and Excise Office is not drawn
- [CENSUS-ENTITIES-30](CENSUS-ENTITIES-30.md): Census Office objects misplaced (upright rug, ceiling hole, tapestry)
- [CHIM-AZURA-DWEMER-RUIN-SHAPES-43](CHIM-AZURA-DWEMER-RUIN-SHAPES-43.md): A Dwemer ruin at Azura's Coast is drawn in the wrong shape
- [CHIM-AZURA-FLOATING-FLORA-43](CHIM-AZURA-FLOATING-FLORA-43.md): Plant or tree pieces hang in the air at Azura's Coast (cell 16,7)
- [CHIM-BC-TREE-PYRAMID-BOX-47](CHIM-BC-TREE-PYRAMID-BOX-47.md): Bitter Coast trees (flora_bc_tree family) look like a pyramid trunk with a flat box floating above it
- [CHIM-DAGOTH-UR-RUIN-CYLINDER-44](CHIM-DAGOTH-UR-RUIN-CYLINDER-44.md): Graphics translation glitch at Dagoth Ur: the blight cloud whirlwind (nested translucent cylinders) is drawn solid and still
- [CHIM-TERRAIN-ROCK-EXEMPT-38](CHIM-TERRAIN-ROCK-EXEMPT-38.md): Terrain-named placed rocks bypass experimental buried-surface clipping
- [CONVERTER-ROOT-ROTATION-30](CONVERTER-ROOT-ROTATION-30.md): Converter applied NIF root-node rotation to placed meshes
- [COURTYARD-ARRIVAL-STUCK-66](COURTYARD-ARRIVAL-STUCK-66.md): Arriving in the census courtyard from the back room, the player was once stuck in solid: twenty "player is stuck" lines and two moves out
- [CREATURE-FLOATING-62](CREATURE-FLOATING-62.md): A scrib in the wilderness floats above the terrain
- [PORT-ROCK-ROTATION-23](PORT-ROCK-ROTATION-23.md): A rock by the Seyda Neen port was converted with the wrong rotation
- [PRISON-SHIP-FLOOR-STUCK-67](PRISON-SHIP-FLOOR-STUCK-67.md): On the prison ship the player gets stuck on a floor tile that stands out of the hold floor
- [ROCK-FLORA-SURFACE-29](ROCK-FLORA-SURFACE-29.md): Angular rock-like surfaces newly appearing in Bitter Coast
- [ROOM-GROUND-STEEP-ICE-66](ROOM-GROUND-STEEP-ICE-66.md): With Bloodmoon selected, the image stage stopped on one Hound of Hircine in the Mortrag Glacier Inner Ring: its feet stand on a steep part of the converted ice floor
- SHACK-VISIBILITY-29 (no report page): Indrele Rathryon shack front walls missing
- [VODUNIUS-HOUSE-HOLES-23](VODUNIUS-HOUSE-HOLES-23.md): Visibility holes in Vodunius Nuccius' house in Seyda Neen
- [WEDGE-TRAP-24](WEDGE-TRAP-24.md): wedge1: the player is trapped at -225,348,131
- [WORLD-SHORE-OPEN-GEOMETRY-38](WORLD-SHORE-OPEN-GEOMETRY-38.md): Shoreline objects show large open sections and thin disconnected edges

Related bugs in other categories:

- [AMBIENT-UNSTUCK-FLOOD-61](AMBIENT-UNSTUCK-FLOOD-61.md): Walking residents in Seyda Neen keep falling back to the stuck-movement retry
- [JOURNEY-DOOR-USE-GOES-TO-ACTOR-66](JOURNEY-DOOR-USE-GOES-TO-ACTOR-66.md): The opening journey's use key at the census street door went to the body of the guard killed a step before, or to a message box still showing, and the step then waited for a load it had never asked for
- [JOURNEY-STEP6-VICTIM-NEAREST-66](JOURNEY-STEP6-VICTIM-NEAREST-66.md): The opening journey's step 6 killed the nearest resident, which could be the guard by the census office's street door, whose body then took the use key instead of the door
- [TP-BEING-TRIBUNAL-FALLS-THROUGH-67](TP-BEING-TRIBUNAL-FALLS-THROUGH-67.md): Teleporting to a character in some Tribunal interiors drops the player through the floor (the pawnbroker Ten-Tongues Weerhat, the Assassin)
- [WANDER-DOOR-RULE-66](WANDER-DOOR-RULE-66.md): A wandering resident can stop at a destination right by a door and stand there; the original sends an idle wanderer near a door walking

<!-- END GENERATED CATEGORY -->
