# STAIRS-BALMORA-B01-32: A Balmora Hlaalu house staircase cannot be approached from below

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:stair-walk |
| First noticed | 8 October 2026, in v0.0.32-dev2 |
| Where | Balmora bm020, ex_hlaalu_b_01 (ref 41499) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.33 |
| Severity | medium: A staircase cannot be used. |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| Playtest version | v0.0.32-dev2 |
| From commit | source and engine 2af54eb |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.43-dev3 (18 October 2026)._

## Status: 9 October 2026

Fixed in source on branch v0.0.33-stairs-2 (not in a build yet): the collision was right, the gate's
walk started inside it. Was: fails the gate (start in solid). Found by the stair walkability gate ([COLLISION-STAIR-SLOPE-32](COLLISION-STAIR-SLOPE-32.md), `tools/stair_walk.py`) on the v0.0.32-dev2 maps, 8 October 2026.

In v0.0.32: the stair walkability gate that found this (`tools/stair_walk.py`, in the image step) is on a development branch and not in v0.0.32; v0.0.32 ships the staircase as described here.

## Symptom

See Where; the gate report (`stair-walk.json`) gives the walk detail.

## Where

bm020, `ex_hlaalu_b_01` (ref 41499), riser at local 705.6 -926.0 75.1 (heading east), rise 8.0.

## How it happened

The standing hull is solid above the stair foot from about 8 units before the riser (standing origin blocked up to z 135) where the visible approach is open (floor at 67.1, nothing above). The model is on Balmora's hand-made surface list (authored plates, exact bevels); its point collision is the authored 45-degree ramp.

Cause (9 October 2026, measured on the mesh in model space and on the bm020 map): the flight is
entered through an arch. The mesh's own collision (`RootCollisionNode`, 321 triangles, as
Morrowind collides) is a ramp of 45.6 degrees (normal z 0.697-0.702, walkable) through the
nosings, about 1-2.5 units above the visible treads, and the arch has a lintel whose underside is
at model z -38.07. The gate starts its walk 11 units before the riser on the visible tread level
and settles from 8 units above that. Here the start (model -107.4 6.95 -62.28) is 1.18 units
inside the ramp's standing hull (the box's front edge already reaches the ramp) and the settle
point 8 units higher is 0.4-0.6 units inside the lintel (plates of the arch top). Between them the
standing column is free (origin z about -60.9 to -54.9): a player stands there on the ramp, and
the ramp passes under the lintel with at least 2.6 units to spare. So "start in solid" was the
walk's start rule, not the collision: neither the authored collision nor the stair rule is at
fault (the rule does not change this mesh).

## Why it was not caught

No check walked converted stairs before the gate.

## Reproduction

`python3 tools/stair_walk.py <id1> --out stair-walk.json` on a build's final maps.

## Repair

The gate's walk (`tools/stair_walk.py` `walk`): when the settle point 8 units above the start is
solid, the walk settles from the highest free point of the column between the start and there
(`_start_column`, 0.25-unit steps). A start with no free point in that column is still "start in
solid". Shared by the legacy image step and the CHIM stair gate (`check_polys`).

## Verification

- Model-space lab (the mesh's own collision built by the shared `collision_pieces` and the CHIM
  brush writer, walked by `check_polys`): 6 flight steps, 5 passed and 1 start in solid before;
  6 of 6 pass after, up and down.
- Regression fixture: `tests/test_stair_walk_cases.py`
  `test_b01_ramp_under_a_low_lintel_starts_from_the_free_column` (fails on the previous gate).
- Real maps: see the gate tables in [COLLISION-STAIR-SLOPE-32](COLLISION-STAIR-SLOPE-32.md).
- Pending: an in-game walk up and down this staircase.

## Prevention

The stair walkability gate in the image step.

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
