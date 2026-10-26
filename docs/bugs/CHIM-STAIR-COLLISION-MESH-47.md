# CHIM-STAIR-COLLISION-MESH-47: stair collision method 1, a stairway collision mesh proven by arithmetic

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 20 October 2026, in v0.0.46 |
| Where | collision of meshes with flights of stairs (tools/stair_mesh.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.46 (last seen) |
| Severity | medium: Replaces the stair walk the maintainer stopped; until it covers every flight it is experimental and off by default |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| CHIM | Stairs and collision on CHIM worlds ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_20_v0.0.46_release_a3fb9b74 |
| From commit | source a3fb9b7, engine a3fb9b7, CHIM world a3fb9b7 |
| CHIM engine version | CHIM 0.2.1, engine a3fb9b7, world format 0.7 |
| Platform or emulator | not in game (measured on the converter's collision of a finished build's meshes, read only; no image built with method 1 yet) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.48-dev2 (22 October 2026)._

<!-- contents start -->
## Contents

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

## Symptom

Today's collision for a flight of stairs (method 0) is the mesh's convex pieces, repaired where they bury the drawn
treads, and only a walk of every built frame proved that it can be climbed (BUILD-STAIR-WALK-BRUTE-FORCE-46). Walks
of the island's frames are stopped, decided for the project on 20 October 2026, so method 0's stairs are no longer
proven by anything. Method 1 is the replacement: collision for a flight that is walkable by construction, checked by
arithmetic on the collision itself.

## Where

`tools/stair_mesh.py` (the stairway mesh, the geometric stair check and method 1's own mesh worker,
`mesh_unit_stair`, unit kind `mesh-stair`); the switch `--stair-collision-method 0|1` on `tools/build.py` and
`tools/chim_build.py` (`AMIWIND_STAIR_COLLISION_METHOD`, `tools/stair_collision_env.py`), default 0. The shared
converter modules (`mesh_geometry`, `mesh_geometry_env`, `prepare_mesh_bsp`) hold no method 1 code: a default build's
mesh units keep the code keys they had before method 1 existed (`tests/test_stair_mesh_keys.py`).

## How it happened

Method 0 made the convex pieces first and repaired them after (stair plates, the visible-tread rule), then walked
the result. Method 1 starts from the movement rules: the step the player climbs (8.5 units here: Morrowind's 34 at
the converter's scale of 0.25, as OpenMW's movement code uses it), the steepest surface the player stands on (normal
z 0.69, about 46 degrees) and the standing box.

## Why it was not caught

Not a defect: the replacement method the maintainer asked for on 20 October 2026.

## Reproduction

`tools/stair_mesh_survey.py RUN --out DIR` measures both methods on the meshes of a finished build's CHIM frames,
read only; the unit tests are `tests/test_stair_mesh.py`.

## Repair

Method 1, per mesh:

1. The flights of the mesh as drawn are found from its level faces: treads that meet in plan (within 2.5 units, a
   bevelled nosing between them) at a rise of 1 unit to a step, along an edge the standing box fits, three or more
   levels in a chain. The detector of method 0's stair rules (a vertical riser at the very edge of each tread) finds
   flights in 23 of the build's meshes; this one in 97.
2. Each flight is checked on the mesh's own collision (its RootCollisionNode, else its drawn mesh) as method 0
   converts it before its repairs. A flight that passes keeps it.
3. A flight that fails is split at its landings into runs of steps; each run gets ramps (the hull of its tread
   corners and the same corners under its lowest tread, the top through the nosings), each grown up the run as far as
   it stays within a step of every tread, walkable and clear of other drawn geometry; landings and treads no ramp
   holds get one solid block per tread (down to the next lower tread). The collision mesh's own triangles of that
   flight are removed, the rest of the mesh is converted as before. One ramp per whole flight stays selectable
   (profile `stair_ramps` 'flight').
4. The check runs on the result. A mesh whose flights do not all pass keeps method 0's collision; the converter's
   note names the flight and the failed check.
5. Walkways (rope bridges, docks, boards: every rise of the flight at most 2.5 units) are not stairs: the level
   boards they continue into join them (boards within 6 units in plan: a rope bridge's gaps), and each run of
   boards gets sloped plates (the hull of the boards and the same 1 unit lower), grown along the way as far as they
   stay within a step of every board; ropes and posts may pass through them. A piece of the mesh's own collision
   that stands in a replaced flight's space first loses its upward faces over that flight and is made convex pieces
   again; only if the check then still fails does it become plates. Non-convex treads get one block per convex
   surface polygon, not one per triangle.
6. Seams: for every pair of treads meeting a step apart, the standing box goes from the closest places it stands on
   the lower one to those on the upper one in 1-unit steps, resting each time on the highest support under its
   footprint that is at most a step above the last (any drop allowed), with its height free; a seam no pair passes
   fails ('lip', 'gap' or 'blocked'). Plane arithmetic on the collision, not a walk of the frame. A flight whose
   ramps fail it is tried as blocks before the mesh falls back to method 0.
7. A build with method 1 writes every mesh's check into its frames' work folders, collects them into
   `chim-world/chim-stair-check.json` and its build summary, and fails on a mesh that fails the check under the
   collision it ships with.

The check (plane arithmetic, no walk): over a grid of points on every drawn tread with standing room above it, the
standing box's footprint (corners, edge midpoints, centre) rests on the highest collision top in reach (a step down
to a step up of the drawn tread). A place where collision stands in the box's height over that rest, or where it
rests on a surface steeper than walkable, is a place the box cannot stand (as the recorded walks never start there):
not a fault there, but a tread with no place to stand fails. Also failing: no support in reach of a tread, and a
rise over a step between neighbouring places the box stands whose drawn treads are at most a step apart. Each
failure names the flight, the tread level, the point and the value. The first form (the vertical line over each
point only) stays selectable for A/B (`form='point'`).

## Verification

Default builds are unchanged: the code keys of every CHIM unit kind (`tools/code_key.py`, `chim.units.CODE_ENTRIES`)
at this branch equal those of the dev line before method 1 (they had been rekeyed by method 1's first version: mesh,
variant, tiles, cut), and ten flight meshes converted by the default worker give byte-identical results at both.

The check places the standing box exactly: the collision pieces grown by the box (as the engine's standing hull is),
one column per place. Calibrated against the stair walks the v0.0.46 release build recorded (read from the build
pool, nothing walked; `tools/stair_mesh_calibrate.py`): 2,542 recorded step rows on 2,506 untilted placements;
275 rows whose walk could not start are not compared.

| Tread points | Exact box with seams (default) | Point form (first) |
| --- | --- | --- |
| Covered by a recorded walk | 3,098 of 35,624 | same |
| Both pass / both fail | 3,033 / 1 | 3,014 / 5 |
| Check fails, walk passed | 5 | 24 |
| Check passes, walk failed | 59 | 55 |
| Agreement on covered points | 97.9 % | 97.5 % |
| Flights the check fails (of 132) | 34 | 69 |

Measured on the same build's 1,380 distinct meshes, both methods with the same profile, written as the same collision
brush image (no build, nothing in game):

| | Method 0 | Method 1 (ramps per run) | Method 1 (one ramp per flight) |
| --- | --- | --- | --- |
| Flights failing the check (of 132) | 34 | 21 | 19 |
| Meshes kept / changed / cannot fix | - | 72 / 14 / 11 | 72 / 16 / 9 |
| Changed meshes: collision bytes | - | 918,460 to 1,022,284 (+11.3 %) | 1,081,988 to 1,236,264 (+14.3 %) |
| All 97 flight meshes: collision bytes | 13,433,116 | 13,536,940 (+0.8 %) | 13,587,392 (+1.1 %) |
| Rope bridge ex_ropebridge_01 | 3,624 | 58,284 | - |
| Stair ex_t_stair_lcurve | 7,708 | 29,840 | - |

Not done: an image with method 1 on and an in-game check at stairs, docks and ladders (waits for a build the
maintainer allows).

### Default since v0.0.48-dev2

Decided for the project on 22 October 2026 (the maintainer: "implement this"). Method 1 is the default;
`--stair-collision-method 0` keeps method 0 for A/B. What changed:

- **Per mesh.** The CHIM model builder first counts each distinct mesh's flights as drawn
  (`stair_mesh.flight_unit`, unit kind `stair-flights`, cached by the mesh's content). Only a mesh with a flight
  gets `stair_collision` `mesh` and method 1's worker (`mesh-stair`). Every other mesh keeps the default worker,
  profile and unit key, because method 1 is method 0 exactly on a mesh without a flight. A default build
  rebuilds the flight meshes only (97 of 1,380 on the v0.0.47 build), not every CHIM mesh.
- **The authored stair ramp stays a ramp** (`tools/authored_ramps.py`, `stair_mesh.keep_stair_ramps`). A convex
  piece that stands over a walkable ramp of the collision mesh lying on a drawn flight becomes the authored plates of
  its own triangles. That applies where the piece is steeper than walkable there, or more than a step over the ramp,
  and the authored surfaces themselves are not. The result is kept only when the stair check is not worse for it.
  Measured on the v0.0.47 build: 74 meshes have such stair ramps, method 0 leaves 14 of them faulty, and the guard
  repairs 12. Still faulty: `ex_de_ship` (on the known list) and `ex_v_palace_steps_01` (the plates failed the
  stair check there, so the guard was not kept).
- **Known meshes.** The 11 meshes method 1 cannot fix yet are listed in `config/stair-check-known.json` as one
  class, [CHIM-STAIR-METHOD1-UNFIXED-48](CHIM-STAIR-METHOD1-UNFIXED-48.md). The CHIM stair check reports them
  (status `known`) and stops only on a failing mesh that is not on the list.

Measured again on the v0.0.47 release build (read only, `tools/stair_mesh_survey.py`, no walk). The collision
source there already follows the new rule for CHIM exteriors (every CHIM model reads its RootCollisionNode); the
new rule changes only the 48 `NCC` models, and none of them has a flight. The numbers are the same as on the
v0.0.46 build: 1,380 distinct meshes, 97 with 132 flights; method 0 fails 34 flights on 24 meshes; method 1 changes
14 meshes (918,460 to 1,022,284 collision bytes, +11.3 %), keeps 72, cannot fix 11; collision bytes of all 97 flight
meshes 13,433,116 to 13,536,940 (+0.8 %).

## Prevention

Method 1 is the default since v0.0.48-dev2; the in-game check at stairs, docks and ladders is still to be recorded.
`tests/test_stair_mesh.py` covers the default switch, the per-mesh flight count, the known list and an authored
45-degree ramp kept walkable; `tests/test_stair_mesh_keys.py` keeps method 1's code out of the default mesh key.

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

Related bugs in other categories:

- [BUILD-STAIR-WALK-SCOPE-KEY-46](BUILD-STAIR-WALK-SCOPE-KEY-46.md): Development builds walk every step of the island again after any collision change: the CHIM gate ignored the walk scope and keyed each frame by all of its collision
- [CHIM-STAIR-STEPS-SOLID-43](CHIM-STAIR-STEPS-SOLID-43.md): Three stair meshes fail the CHIM stair walk: Redoran steps start in solid (Ald-ruhn, Maar Gan), Hlaalu steps blocked (Suran), a rope bridge starts in solid (0,8)

<!-- END GENERATED CATEGORY -->
