# BUILD-STAIR-WALK-BRUTE-FORCE-46: the builder walks the island to rediscover what the game already says

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
- [CHIM-SEYDA-EXPANDED-STAIRS-40](CHIM-SEYDA-EXPANDED-STAIRS-40.md): Expanded Seyda CHIM frame fails stair walks at two original references
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
