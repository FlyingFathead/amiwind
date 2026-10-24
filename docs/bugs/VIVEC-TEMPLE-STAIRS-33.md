# VIVEC-TEMPLE-STAIRS-33: Palace steps and High Fane quarter flights fail the stair gate on the CHIM Vivec Temple frame

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.36-dev4 at 2026-10-11 05:32 +0300: PERSISTING: whole-city frame vivec_city fails the stair gate on the same refs 428484, 428530, 484457, 484458 (11 of 18 failed flight steps)
- Reported with v0.0.36-dev5 at 2026-10-11 09:41 +0300: PERSISTING: whole-city Vivec with rooms f6e08fe (dev5), accepted by ID for the dev MiniWind: same refs 428484, 428530, 484457, 484458 (11 flight steps)
- Reported with v0.0.36-dev5 at 2026-10-11 09:56 +0300: maintainer order (TG): fix for rc1

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | Vivec Temple frame (vivec_temple): ex_v_palace_steps_01, ex_vivec_hfq_01, ex_vivec_hfq_04 |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.36 |
| Severity | medium: Flights the player climbs in the original are blocked; the Temple frame cannot pass its stair gate until repaired. |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| CHIM | Stairs and collision on CHIM worlds ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 2a5bd0e, engine 2a5bd0e, CHIM world 2a5bd0e |
| CHIM engine version | CHIM 0.1.0, engine 2a5bd0e, world format 0.5 |
| Build note | vivec_temple CHIM world built from v0.0.33-chim-format with and without --cut-models-over 512 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.43-dev3 (18 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 3 times; something has to be done](#persisting-reported-3-times-something-has-to-be-done)
- [Status: 9 October 2026](#status-9-october-2026)
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

## Status: 9 October 2026

Open; persisting since v0.0.33-dev (9 October 2026), reported again on the whole-city frame in v0.0.36-dev4
and v0.0.36-dev5 (accepted by ID for the dev MiniWinds only). 11 October 2026: repaired in source on the
v0.0.36-stairs-rc1 line (two shared rules below), verification build pending. A private -devN test could
accept these placements by ID (`--accept-known-stair-findings VIVEC-TEMPLE-STAIRS-33`); rc and final builds
refuse it.

## Symptom

The CHIM stair gate stops a build of the `vivec_temple` frame on two meshes:

- `ex_v_palace_steps_01` (ref 428484, ref 428530): steps whose walk starts in solid, or is blocked by
  collision about 64 units above the step (risers 3.8 to 5.1 units).
- `ex_vivec_hfq_01` and `ex_vivec_hfq_04` (High Fane quarters, ref 484457, ref 484458): steps blocked by
  a 26.7-degree collision slope over the tread (risers 3.7 to 4.1 units).

## Where

The standing-hull collision of these meshes, as the shared collision layer builds it
(`mesh_geometry.collision_pieces` and the stair rule). The same flights fail with and without the
large-model cut, so the cut is not the cause.

## How it happened

Traced 11 October 2026 on the f6e08fe whole-city frame (all 11 flight steps reproduced offline):

- High Fane quarters (`ex_vivec_hfq_01`, `ex_vivec_hfq_04`, refs 484457 and 484458; authored plates, exact
  bevels): the authored collision (RootCollisionNode) puts a steep wedge (60-69 degrees, up to 92 units high)
  over the left part of the visible flight: the 26.7-degree authored ramp is 150 units wide, the wedge covers
  x 200-257 of it in the model, and the walk's line through the middle of the riser runs 2.8 units from the
  wedge, closer than the standing box's half width. The original game collides with the same authored
  surfaces, so the player climbs the open part (78 units wide); the gate only tried lines 1-3 units to the side.
- Palace steps (`ex_v_palace_steps_01`, refs 428484 and 428530): the convex approximation leaves pieces of
  three triangles that close 4.96 and 5.49 units of space (more than the tolerance 2, but a piece of at most
  four triangles is never split further); their hulls invent 67-degree faces over the treads, where a
  standing box stepping up comes down (and the first step starts in that solid).

The legacy builder never converted the Temple frame (VIVEC-HEAP-31 blocked it), so these meshes never met
the stair gate before.

## Why it was not caught

The Temple frame had never been built.

## Reproduction

`tools/chim_build.py --area vivec_temple --qbsp ... --sdk ... --validate`.

## Repair

Two shared rules (tools/mesh_geometry.py, tools/stair_walk.py), for every mesh with the mechanism:

- `collision_parts(..., plates, fill_plates)`: on a mesh with stairs (stair rule on), a piece that still
  closes more than the tolerance when it cannot be split further (at most four triangles) and whose hull
  invents a face too steep to stand on that no source triangle lies in becomes the authored plates of its
  triangles (exact standing bevels), as the stair rule already does for pieces that bury a tread
  (palace steps: 6 plates). The deep-fill test that keeps a whole mesh's authored surfaces
  (`surface_collision_beyond`) is measured on the plain convex proxies first: measured after the plates, it
  missed the Vivec palace stairs' 9.05 units, and the first whole-city build on the fix failed six of their
  flight steps (ex_vivec_ps_01, start in solid); a test pins the order.
- `stair_walk.other_lines`: a flight step whose line through the middle of the riser fails is walked along
  the other lines across the riser's width (every 4 units, nearest the middle first, the standing box within
  the riser); the first line walked up and down passes the step and is recorded in the row as `line` (its
  offset). A flight closed over its whole width still fails (the High Fane quarters pass at 4 units from the
  middle, as the player climbs them).

## Verification

Offline on the f6e08fe frame with the recomputed collision: all 11 flight steps pass (the High Fane
quarters along a line 4 units from the middle; the palace steps' first step through the middle, the other
two at 4 units). Synthetic tests: tests/test_stair_rc1_fixes.py (FillPlateTests, OtherLinesTests). Pending:
the whole-city MiniWind on the fixed builder with no accepted stair findings.

## Prevention

Every Vivec frame runs the stair gate; a convex piece that closes more than the tolerance on a mesh with
stairs is no longer kept; a flight passes only along a line the standing box really walks.

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
- [WORLD-SLOPE-STUCK-38](WORLD-SLOPE-STUCK-38.md): Player reports being stuck beside Ashlands terrain

<!-- END GENERATED CATEGORY -->
