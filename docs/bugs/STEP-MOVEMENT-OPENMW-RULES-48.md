# STEP-MOVEMENT-OPENMW-RULES-48: the player steps by Quake's rules, not Morrowind's, so stairs are proven by walks instead of by rule

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 22 October 2026, in v0.0.47-dev2 |
| Where | player movement (sv_phys.c SV_WalkMove, aw_walk.c, quakedef.h AW_WALKABLE_Z) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.47-dev2 (last seen) |
| Severity | medium: The engine's step and slope rules differ from the game's (9 of 25 synthetic cases), so stair traversal could not be proven from the data and was walked |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| CHIM | Stairs and collision on CHIM worlds ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_21_v0.0.47-dev2_dev2-try3_c20bc0d8 |
| From commit | source c20bc0d, engine c20bc0d, CHIM world c20bc0d |
| CHIM engine version | CHIM 0.2.1, engine c20bc0d, world format 0.7 |
| Platform or emulator | not in game (engine rules and an offline check; measured by native tests and a read-only survey) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.48-dev2 (22 October 2026)._

## Status: 22 October 2026

Open. The design note is [Step movement](../STEP_MOVEMENT.md). A prototype of Morrowind's step and slope rules
(as OpenMW 0.51 states them) is in the engine behind `aw_step_rules`, default 0: the shipped behaviour does not
change. Turning it on by default is the maintainer's decision (the note's proposal). Not tried in game yet.

## Symptom

Whether a Morrowind stair or slope can be climbed in AmiWind was settled by walking it (the stair walk, now
stopped by the maintainer: BUILD-STAIR-WALK-BRUTE-FORCE-46), because the engine's movement rules are Quake's and
differ from the game's. The maintainer (22 October 2026): there has to be a better way to make something
traversable, since the data is already there.

## Where

`engine/aga/src/sv_phys.c` (`SV_WalkMove`, `SV_FlyMove`), `engine/aga/src/aw_walk.c` (`AW_WalkPlayer`),
`engine/aga/src/quakedef.h` (`AW_WALKABLE_Z`); the converter's copies of the numbers in `tools/player_hull.py`.

## How it happened

AmiQuake's walk is Quake's: a step of 8.5 units tried only on the ground and only as far as the frame's own move, a
walkable slope of normal z 0.69 (46.4 degrees), the ground followed down 8.75 units, and a too-steep slope that a fast
walker can crawl up. Morrowind's rules (OpenMW: `stepper.cpp`, `movementsolver.cpp`, `constants.hpp`) differ: a 46
degree slope limit, three step tries reaching 10 and 20 units on, a step-down of 62, steps in the air, and a steep
slope that is a wall. Morrowind's stairs are traversable because their authored collision is a ramp at or under 45
degrees; with the rules matching, that holds by arithmetic. With rules that differ, it had to be walked.

## Why it was not caught

The movement rules were tuned case by case (the 0.69 limit for the Hlaalu ramps, the 8.75 step-down) instead of being
compared with the reference implementation as a whole.

## Reproduction

`tests/aga_step_rules_test.c` drives the engine's walk over synthetic risers, ramps, lips and drops: under the Quake
rules 9 of the 25 cases differ from OpenMW's rules (a 34.8 MW riser, 46 and 46.2-degree ramps climbed, 46.5 and
50-degree ramps crawled up at higher speeds or frame rates, a 55-degree 27 MW lip refused, drops of 36-62 MW fallen).

## Repair

Prototype (default off): `aw_step_rules 1` steps by OpenMW's rules (`sv_phys.c` `SV_StepRulesStep`, the steep-slope
rule in `SV_FlyMove`, `quakedef.h` `AW_WALKABLE`, the 16-unit ground following in `aw_walk.c`). The data side
combines with the authored-collision converter default (RootCollisionNode collision, authored ramps kept, stair
collision method 1), with the converter's numbers set to the engine's; the per-mesh check (`tools/stair_mesh.py`
`check_flight`) is the proof. See the note's method and proposal.

## Verification

- `tests/test_aga_native_source.py` `test_step_rules_match_openmw_over_synthetic_stairs_and_slopes`: every
  step-rules result matches OpenMW's rules at 160 and 400 MW/s and at 20 and 50 frames a second; the Quake rules
  lose no climb.
- `tools/step_rules_survey.py` over the v0.0.47-dev2 build (read only, no walk): 87 of the 97 stair meshes pass the
  check under the step rules with method 1 built for them, against 73 today; the 10 left are named in the note.
- Not in game yet.

## Prevention

One set of movement numbers for the engine, the converter and the check, taken from the reference implementation;
a stair is proven by the check on its own mesh, never by a walk.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`). Convex collision proxies invent steep faces or bury authored surfaces; Morrowind collides with authored geometry (step up 34 units, slope up to 46 degrees). Rule: follow_original_stair_rules plus a walkability gate. See [families](README.md#families).

- [BUILD-ACTOR-GATE-CHIM-FRAMES-36](BUILD-ACTOR-GATE-CHIM-FRAMES-36.md): The actor placement gate ignores CHIM frame residents: a CHIM-only build fails with no actors, and a blocked frame resident passes silently
- [BUILD-FLORA-STAIR-PLATES-BUDGET-36](BUILD-FLORA-STAIR-PLATES-BUDGET-36.md): The stair-plate collision rules raised a legacy open-world map past the BSP clip-node limit: world-flora failed on vf0779 (33,172 aggregate clipnodes > 32,767)
- [BUILD-HULL-ROUTE-BUDGET-33](BUILD-HULL-ROUTE-BUDGET-33.md): Routed standing hulls with copies overflow a legacy map's shared clipnode budget
- [BUILD-ROUTED-FLORA-RESERVE-33](BUILD-ROUTED-FLORA-RESERVE-33.md): Routed standing hulls push a legacy open-world map past the flora collision reserve: the full build stops in world-flora (vf0779)
- [BUILD-STAIR-FLAG-INERT-32](BUILD-STAIR-FLAG-INERT-32.md): The stair rule build option does nothing in v0.0.32
- [BUILD-STAIR-WALK-BRUTE-FORCE-46](BUILD-STAIR-WALK-BRUTE-FORCE-46.md): The builder walks every step of the island to find out whether its own collision can be walked, an answer the game data already holds
- [CHIM-HULL-STAIR-EDGE-33](CHIM-HULL-STAIR-EDGE-33.md): With the qbsp-compiled terrain hull on Balmora's regular ground, one flight of stairs fails at a chunk edge
- [CHIM-HULL-SURFACE-RESURVEY-48](CHIM-HULL-SURFACE-RESURVEY-48.md): The v0.0.48-dev2 build stopped at the collision surface gate in Balmora: the gate measured treads stair method 1 removed, and the hull-surface table was measured under the old collision defaults
- [CHIM-ROOM-CLIP-DRAWN-BOX-48](CHIM-ROOM-CLIP-DRAWN-BOX-48.md): A CHIM room's runtime collision skips a placement by its drawn box, and a store model's hull can reach past that box
- [CHIM-SEYDA-EXPANDED-STAIRS-40](CHIM-SEYDA-EXPANDED-STAIRS-40.md): Expanded Seyda CHIM frame fails stair walks at two original references
- [CHIM-STAIR-COLLISION-MESH-47](CHIM-STAIR-COLLISION-MESH-47.md): Stair collision method 1: a stairway collision mesh per flight, proven by a geometric check instead of a walk
- [CHIM-STAIR-GATE-POOL-BROKEN-42](CHIM-STAIR-GATE-POOL-BROKEN-42.md): The CHIM stair gate of a whole-Vivec MiniWind stopped the build: a walk worker was killed
- [CHIM-STAIR-METHOD1-UNFIXED-48](CHIM-STAIR-METHOD1-UNFIXED-48.md): Stair collision method 1 cannot yet make 11 meshes' flights pass the geometric stair check (ships, shipwreck, silt strider, tent, Daedric ruins and four buildings)
- [CHIM-VIVEC-DOCK-WALKWAY-43](CHIM-VIVEC-DOCK-WALKWAY-43.md): The player cannot climb the walkway at the Vivec Hlaalu canton dock and gets stuck
- [CHIM-VOS-TEMPLE-WALKWAY-41](CHIM-VOS-TEMPLE-WALKWAY-41.md): Vos walkway stair starts inside the Velothi temple's collision and fails the stair gate
- [COLLISION-CONVEX-LOSS-32](COLLISION-CONVEX-LOSS-32.md): Convex collision proxies lose and invent authored surfaces
- [COLLISION-HULL-CHAINS-33](COLLISION-HULL-CHAINS-33.md): 183 brush models across the island collide through standing-hull chains 512 to 31,659 clipnodes deep
- [COLLISION-NC-FLAGS-32](COLLISION-NC-FLAGS-32.md): Morrowind no-collision and editor-marker flags (NC, NCC, MRK, AvoidNode) are ignored by the mesh converters
- [COLLISION-RCN-SCOPE-32](COLLISION-RCN-SCOPE-32.md): Authored collision meshes (RootCollisionNode) are used by some converters only
- [COLLISION-ROUTE-NO-SPLIT-36](COLLISION-ROUTE-NO-SPLIT-36.md): Routed standing hulls of dense flora (kelp, kreshweed) stay one chain 277-305 clipnodes deep: the router finds no cut, so the cell stays hull-pending
- [COLLISION-SEYDA-PREVIEW-BYPASS-32](COLLISION-SEYDA-PREVIEW-BYPASS-32.md): The legacy Seyda Neen preview builds its own convex collision
- [COLLISION-STAIR-SLOPE-32](COLLISION-STAIR-SLOPE-32.md): Convex collision proxies make stairs unclimbable
- [COLLISION-TRACE-COST-33](COLLISION-TRACE-COST-33.md): Movement traces near large models walk long standing-hull chains: tens of ms per trace on a slow 68040 (emulator-relative)
- [COLLISION-TRACE-LIMIT-ROUTED-ROOM-36](COLLISION-TRACE-LIMIT-ROUTED-ROOM-36.md): The tool collision tracer stops on the Vivec Arena Pit's routed hull (visit limit), so its start spot cannot be traced
- [HULL-SURFACE-TENT03-MISSING-57](HULL-SURFACE-TENT03-MISSING-57.md): The collision surface table left out one Ashlander yurt (ex_ashl_tent_03): its walkable collision lay 64 units under its convex pieces
- [RECIPE-ROW-MOVES-COLLISION-57](RECIPE-ROW-MOVES-COLLISION-57.md): A mesh reduction row changed the Imperial ship's collision: the dev4 build stopped at the collision surface gate in Vivec City (64 units)
- RED-MOUNTAIN-SLOPE-TOO-STEEP-51 (no report page): Red Mountain (cell 2,7): a slope too steep to walk up, the player cannot go forward
- [ROOM-PYLON-ROOF-48](ROOM-PYLON-ROOF-48.md): Grand Inquisitor and Tamira Vian (Hall of Processing) stand inside collision: a convex piece of ex_stronghold_pylon01 slopes 14 units over the floor they stand on
- [ROOM-X-MESH-ROOF-SURVEY-48](ROOM-X-MESH-ROOF-SURVEY-48.md): 57 more exterior meshes placed in rooms have a convex collision piece standing more than a step over their own floor
- [SEYDA-BLOCK-31](SEYDA-BLOCK-31.md): Invisible obstacle blocks the path on a Seyda Neen slope
- [STAIR-DETECT-POSITION-41](STAIR-DETECT-POSITION-41.md): Stair step detection depends on where a frame puts the placement: a few borderline steps are found in one frame's copy and not in another's
- [STAIR-FLIGHT-CORE-SPLIT-41](STAIR-FLIGHT-CORE-SPLIT-41.md): The stair gate marks flights per 1024-unit core: a flight that crosses a core line loses its flight mark, so its failures do not stop a build
- [STAIRS-ADDAMASARTUS-32](STAIRS-ADDAMASARTUS-32.md): A low step in the Addamasartus cave is blocked
- [STAIRS-BALMORA-B01-32](STAIRS-BALMORA-B01-32.md): A Balmora Hlaalu house staircase cannot be approached from below
- [STAIRS-BALMORA-WESTSOUTH-32](STAIRS-BALMORA-WESTSOUTH-32.md): A Hlaalu hall staircase in a Balmora interior has no clear foot
- [STAIRS-EBONHEART-CHIM-36](STAIRS-EBONHEART-CHIM-36.md): Three Ebonheart flights fail the CHIM stair gate in the whole-city Vivec frame
- [STAIRS-MOLAG-ACCESS-38](STAIRS-MOLAG-ACCESS-38.md): Tel Uvirith walkway step and door stairs block normal walking
- [STAIRS-SEYDA-LIGHTHOUSE-32](STAIRS-SEYDA-LIGHTHOUSE-32.md): Seyda Neen lighthouse stairs are blocked (outside and inside)
- [STAIRS-SEYDA-WAREHOUSE-32](STAIRS-SEYDA-WAREHOUSE-32.md): A spiral stair in the Seyda Neen warehouse tower is blocked
- [STAIRS-VIVEC-ROOMS-JOINT-36](STAIRS-VIVEC-ROOMS-JOINT-36.md): Six flight steps in three Vivec rooms are blocked where one stair piece meets the next
- [TERRAIN-TRAP-29](TERRAIN-TRAP-29.md): v0.0.29-dev1: Player reportedly stuck on rocks beside structures
- [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md): Five Vivec Arena residents fail the actor placement gate
- [VIVEC-ARENA-TP-ARRIVAL-32](VIVEC-ARENA-TP-ARRIVAL-32.md): dbg tp vivec_arena leaves the player at the frame origin under the water
- [VIVEC-TEMPLE-STAIRS-33](VIVEC-TEMPLE-STAIRS-33.md): Palace steps and High Fane quarter flights fail the stair gate on the CHIM Vivec Temple frame
- [WORLD-SLOPE-STUCK-38](WORLD-SLOPE-STUCK-38.md): Player reports being stuck beside Ashlands terrain

<!-- END GENERATED CATEGORY -->
