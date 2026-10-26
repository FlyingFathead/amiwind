# CHIM-STAIR-METHOD1-UNFIXED-48: Stair collision method 1 cannot yet make 11 meshes' flights pass the geometric stair check (ships, shipwreck, silt strider, tent, Daedric ruins and four buildings)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 22 October 2026, in v0.0.48-dev2 |
| Where | tools/stair_mesh.py collision_pieces_mesh; config/stair-check-known.json |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.48-dev2 (last seen) |
| Severity | medium: These flights keep method 0's collision, which the check does not prove climbable; nothing is walked any more to prove it |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| CHIM | Stairs and collision on CHIM worlds ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_21_v0.0.47_clean-public_791771f7 |
| From commit | source 791771f, engine 791771f, CHIM world 791771f |
| CHIM engine version | CHIM 0.2.1, engine 791771f, world format 0.11 |
| Platform or emulator | not in game (measured on the converter's collision of a finished build's meshes, read only (tools/stair_mesh_survey.py)) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.48-dev2 (23 October 2026)._

<!-- contents start -->
## Contents

- [Status: 23 October 2026](#status-23-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 23 October 2026

Open. Stair collision method 1 ([CHIM-STAIR-COLLISION-MESH-47](CHIM-STAIR-COLLISION-MESH-47.md)) is the default
since v0.0.48-dev2, decided for the project on 22 October 2026. These 11 meshes are the ones it cannot fix yet. They
are one class, listed in `config/stair-check-known.json` and never dropped.

Two more were added on 23 October 2026, found when the dev2 verify run checked the region frames under the new
default collision, and left the list the same day (v0.0.48, branch v0.0.48-fix-content-32mb):

- **A Grazelands tree** (`flora_tree_gl_06`) has no stairway: four root faces within 10 degrees of level, 1 to 2.5
  units apart, read as a flight of three levels. Its RootCollisionNode (the trunk) holds nothing under them, so the
  original stands nobody there: OpenMW 0.51 collides with the RootCollisionNode alone
  (`components/nifbullet/bulletnifloader.cpp`). The flight detector now takes a drawn level face as a tread only
  where the mesh's authored collision holds something under it (`stair_mesh.flights` `collision`). The same rule
  takes the false flight off `flora_tree_02`, whose roots method 1 had given a stairway collision mesh the original
  does not have.
- **The Telvanni slave market** (`ex_t_slavemarket`): its frames convert it under a visual recipe (`tel-uvirith-v1`,
  ratio 0.1). Method 1 took its flight, ramp and proof from that reduced mesh, while the build's stair check reads the
  mesh as drawn, where a tread stood 18.8 units over the ramp. Method 1 now takes the flights and the proof from the
  mesh as drawn (`collision_pieces_mesh` `drawn`); method 0's visible-tread rule keeps the reduced mesh. Its own
  collision then passes the check, and it ships it.

Measured on all 103 stair units of the v0.0.48-dev2 build (`2026_10_23_v0.0.48-dev2_dev2-try8_0754e9bc`, read only,
`tools/stair_mesh.py` from the branch): the 11 still fail as before (the silt strider now reports its method 0
collision as a fallback rather than as kept: the same collision); nothing else changed its result.

## Symptom

On these meshes, method 1's stairway collision (ramps or tread blocks) still fails the geometric stair check on at
least one flight, so the mesh keeps method 0's collision (the convex pieces with the stair rules). Method 0 also
fails the check there. Nothing walks the stairs any more, so nothing proves that these flights can be climbed:

| Mesh | Flights | Still failing |
| --- | ---: | ---: |
| `x/ex_de_ship` | 7 | 6 |
| `x/ex_de_shipwreck` | 5 | 2 |
| `r/siltstrider` | 1 | 1 |
| `x/ex_ashl_tent_03` | 5 | 3 |
| `x/ex_dae_ruin_04_skew_01` | 5 | 2 |
| `x/ex_dae_ruin_02_skew` (no RootCollisionNode) | 4 | 2 |
| `x/ex_dae_ruin_entry.max` (no RootCollisionNode) | 1 | 1 |
| `x/ex_de_shack_04` | 1 | 1 |
| `x/ex_common_house_tall_02` | 1 | 1 |
| `x/ex_hlaalu_bal_02` | 1 | 1 |
| `x/ex_hlaalu_dsteps_01` | 1 | 1 |

`ex_hlaalu_dsteps_01`'s own RootCollisionNode has faces of 46-48 degrees, which OpenMW cannot stand on either
([COLLISION_MESHES.md](../COLLISION_MESHES.md) "Stairs and ramps").

## Where

`tools/stair_mesh.py` (`collision_pieces_mesh`: a mesh whose flights do not all pass keeps method 0);
`config/stair-check-known.json` (the list); the CHIM stage's stair check (`stair_mesh.collect`,
`chim-world/chim-stair-check.json`, the build summary line).

## How it happened

Method 1 handles straight flights, landings, spiral stairs and walkways. These meshes have flights it does not model
yet: ladders and stairs between ship decks, tilted (skewed) ruins, a strider's boarding steps, and flights that run
into walls or overhangs within the standing box's height.

## Why it was not caught

Not a regression: measured when method 1 was made ([CHIM-STAIR-COLLISION-MESH-47](CHIM-STAIR-COLLISION-MESH-47.md)
"Verification", 11 meshes on the v0.0.46 build) and again for the default switch on the v0.0.47 build.

## Reproduction

`tools/stair_mesh_survey.py RUN --out DIR` on a finished build, read only: the meshes whose method 1 note says
"method 0 kept".

## Repair

Not yet. A build lists them as known (status `known`), so the default build does not stop on them. A mesh that
starts to pass is named under `known_passing` and leaves the list. Planned, per mesh class: walkway plates along
ship decks and ladders, flights of a skewed ruin checked in the mesh's own frame, and per-mesh rules where a flight
meets a wall.

## Verification

Measured 22 October 2026 on the v0.0.47 release build's 1,380 distinct CHIM meshes, read only: 97 hold flights (132
flights); method 1 changes 14, keeps 72, cannot fix these 11.

## Prevention

The list is checked: the CHIM stair check stops a build on any failing mesh not on it
(`tests/test_stair_mesh.py` `KnownMeshTests`).

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
- [STEP-MOVEMENT-OPENMW-RULES-48](STEP-MOVEMENT-OPENMW-RULES-48.md): The player steps by Quake's rules, not Morrowind's, so stairs are proven by walks instead of by rule
- [TERRAIN-TRAP-29](TERRAIN-TRAP-29.md): v0.0.29-dev1: Player reportedly stuck on rocks beside structures
- [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md): Five Vivec Arena residents fail the actor placement gate
- [VIVEC-ARENA-TP-ARRIVAL-32](VIVEC-ARENA-TP-ARRIVAL-32.md): dbg tp vivec_arena leaves the player at the frame origin under the water
- [VIVEC-TEMPLE-STAIRS-33](VIVEC-TEMPLE-STAIRS-33.md): Palace steps and High Fane quarter flights fail the stair gate on the CHIM Vivec Temple frame
- [WORLD-SLOPE-STUCK-38](WORLD-SLOPE-STUCK-38.md): Player reports being stuck beside Ashlands terrain

<!-- END GENERATED CATEGORY -->
