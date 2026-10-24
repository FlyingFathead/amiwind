# BUILD-STAIR-WALK-BRUTE-FORCE-46: the builder walks the island to rediscover what the game already says

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 2 times; something has to be done

- Reported with v0.0.46-dev1 at 2026-10-20 14:48 +0300: Seen again in the v0.0.46-dev1 rebuild (try2): the CHIM stair gate walked 1196 frames again, 261,038 steps and ramps, 8 min 53 s (the first dev1 run is the first report)
- Reported with v0.0.46-dev1 at 2026-10-20 18:11 +0300: 2026-10-20 15:11 UTC: the dev1 rebuild walked 1,198 frames and 1,553 maps again after the heap fix (BUILD-STAIR-WALK-SCOPE-KEY-46)

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 20 October 2026, in v0.0.46-dev1 |
| Where | collision conversion and the CHIM stair gate (mesh_geometry, chim/validate) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.46-dev1 (last seen) |
| Severity | medium: About 1.5 million stair walks per full build, hours of build time, and collision kept more exact than needed (+55 MB planes and nodes island-wide) |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_20_v0.0.46-dev1_dev1_f5a1404a |
| From commit | source f5a1404, engine f5a1404, CHIM world f5a1404 |
| CHIM engine version | CHIM 0.2.1, engine f5a1404, world format 0.5 |
| Platform or emulator | not in game (a builder method, seen in build logs and timing) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.46-dev1 (20 October 2026)._

## Symptom

A full build walks every step and ramp of every frame to find out whether the collision it made can be walked:
about 1.5 million stair walks in the v0.0.46-dev1 build, most of the CHIM stage's time. The collision itself is
kept more exact than walking needs: the dock walkway repair (CHIM-VIVEC-DOCK-WALKWAY-43) kept every point of each
convex piece of 484 mesh types and added about 55 MB of stored planes and nodes over the island, enough to push six
frames over the memory budget.

## Where

The collision conversion (`tools/mesh_geometry.py`, the convex pieces) and the CHIM stair gate
(`tools/chim/validate.py`, the stair records).

## How it happened

The converter cuts each drawn Morrowind mesh into the convex pieces Quake collision needs, and the cut cannot always
keep the surface the player stands on. Every time a flight failed, a stair rule and a wider walk were added to catch
it. The answer was in the game data the whole time: each mesh's own collision node (or its drawn mesh), and the
original movement rules (the highest step, the steepest walkable slope, the player's size), which OpenMW's movement
code and the game settings give.

## Why it was not caught

The cost of the walks was treated as a speed problem each time, never as a sign that the method was the wrong way
round. Earlier entries of the same theme: BUILD-CHIM-STAIR-WALK-UNCACHED-36, BUILD-IMAGE-STAIR-WALK-SERIAL-36,
CHIM-STAIR-GATE-WORLD-RELOAD-36, BUILD-STAIR-KEY-BOOKKEEPING-36, BUILD-STAIR-WALK-BORDER-COPIES-41,
BUILD-STAIR-PASS-NOT-KEPT-41, BUILD-CHIM-STAIR-JOBS-AT-LAUNCH-42, BUILD-CHIM-STAIR-NO-REUSE-42 and
BUILD-IMAGE-STAIR-WALK-CORES-43. Each made the walks cheaper; none asked why they were needed.

## Reproduction

Any full build: the CHIM stage's stair gate and its time in the build summary.

## Repair

Open. Decided for the project, 20 October 2026 (roadmap: "Collision from what the game already knows"): a second
collision method beside today's, selected by a builder switch, built from the game's collision data and the movement
rules so that stairs and walkways are walkable by construction (a plate per tread or an invisible ramp under a flight,
steps still drawn). Its check is arithmetic: no standing surface lower than drawn by more than a step, no step above
the limit. The stair walk stays as a sample. Today's method is kept unchanged, with its stair gate and stair rules,
and the walk results already recorded (passed and failed, by the SHA-256 of the data walked) are kept as the
reference for the A/B.

## Verification

An A/B of both methods on the same frames: memory (bytes, planes, nodes), build time, a stair walk sample, and
in-game clips at stairs, docks and ladders. First, the same result at every place where a stair or collision bug
was fixed (Balmora, Seyda Neen, Vivec, the Temple and the bugs above).

## Prevention

A cost that comes back under new names is a method question: the register entries of one theme are read together
before the next speed fix.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`). Convex collision proxies invent steep faces or bury authored surfaces; Morrowind collides with authored geometry (step up 34 units, slope up to 46 degrees). Rule: follow_original_stair_rules plus a walkability gate. See [families](README.md#families).

- [BUILD-ACTOR-GATE-CHIM-FRAMES-36](BUILD-ACTOR-GATE-CHIM-FRAMES-36.md): The actor placement gate ignores CHIM frame residents: a CHIM-only build fails with no actors, and a blocked frame resident passes silently
- [BUILD-FLORA-STAIR-PLATES-BUDGET-36](BUILD-FLORA-STAIR-PLATES-BUDGET-36.md): The stair-plate collision rules raised a legacy open-world map past the BSP clip-node limit: world-flora failed on vf0779 (33,172 aggregate clipnodes > 32,767)
- [BUILD-HULL-ROUTE-BUDGET-33](BUILD-HULL-ROUTE-BUDGET-33.md): Routed standing hulls with copies overflow a legacy map's shared clipnode budget
- [BUILD-ROUTED-FLORA-RESERVE-33](BUILD-ROUTED-FLORA-RESERVE-33.md): Routed standing hulls push a legacy open-world map past the flora collision reserve: the full build stops in world-flora (vf0779)
- [BUILD-STAIR-FLAG-INERT-32](BUILD-STAIR-FLAG-INERT-32.md): The stair rule build option does nothing in v0.0.32
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
- [VIVEC-TEMPLE-STAIRS-33](VIVEC-TEMPLE-STAIRS-33.md): Palace steps and High Fane quarter flights fail the stair gate on the CHIM Vivec Temple frame
- [WORLD-SLOPE-STUCK-38](WORLD-SLOPE-STUCK-38.md): Player reports being stuck beside Ashlands terrain

Related bugs in other categories:

- [BUILD-CHIM-CONVERTER-CHANGE-FULL-REBUILD-46](BUILD-CHIM-CONVERTER-CHANGE-FULL-REBUILD-46.md): A change in the shared collision converter rebuilds every CHIM frame and everything after it, even where the output is identical
- [BUILD-CHIM-VIS-ROWS-KEY-BROAD-46](BUILD-CHIM-VIS-ROWS-KEY-BROAD-46.md): The CHIM visibility rows are keyed on the frames' whole collision, so every collision change redoes 75,904 units, and each frame took 4 times longer
- [BUILD-NPC-GALLERY-REBUILT-46](BUILD-NPC-GALLERY-REBUILT-46.md): The NPC gallery (3,551 models, 36 minutes) is rebuilt after a change in collision code that its models do not use
- [BUILD-RESIDENT-MAP-SLOWER-46](BUILD-RESIDENT-MAP-SLOWER-46.md): The resident-map step of the area and balmora-interiors stages ran 55 to 60 percent slower than its baseline with the same units
- [BUILD-STAIR-WALK-SCOPE-KEY-46](BUILD-STAIR-WALK-SCOPE-KEY-46.md): Development builds walk every step of the island again after any collision change: the CHIM gate ignored the walk scope and keyed each frame by all of its collision

<!-- END GENERATED CATEGORY -->
