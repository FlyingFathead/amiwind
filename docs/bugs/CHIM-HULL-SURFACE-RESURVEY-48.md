# CHIM-HULL-SURFACE-RESURVEY-48: the v0.0.48-dev2 build stopped at the collision surface gate in Balmora

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 23 October 2026, in v0.0.48-dev2 |
| Where | CHIM collision surface gate, Balmora: ex_hlaalu_b_01, ex_hlaalu_b_04, ex_hlaalu_b_06 (64 units) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.48-dev2 (last seen) |
| Severity | high: the full build stops in its CHIM stage; no v0.0.48 release image |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_23_v0.0.48-dev2_dev2-try2_f9c18a50 |
| From commit | source f9c18a5, engine f9c18a5, CHIM world f9c18a5 |
| CHIM engine version | CHIM 0.2.1, engine f9c18a5, world format 0.7 |
| Platform or emulator | not in game (a builder gate stops the build) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.48 (23 October 2026)._

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

Cause measured and fixed in the shared converter and the gate; the hull-surface table is measured again under the
shipped collision defaults. Verified on a CHIM stage run of the three towns and 67 region frames (below); the full
release build is next.

## Symptom

The v0.0.48-dev2 full build (`2026_10_23_v0.0.48-dev2_dev2-try2_f9c18a50`) stopped in its CHIM stage:

    Error: balmora: collision surface gate: walkable collision more than 8.5 units under the convex pieces
    (CHIM-VIVEC-DOCK-WALKWAY-43; add the mesh to config/collision-hull-surface.json):
    meshes/x/ex_hlaalu_b_06.nif 64.00, meshes/x/ex_hlaalu_b_04.nif 64.00, meshes/x/ex_hlaalu_b_01.nif 64.00

Vivec City reported `ex_hlaalu_b_06` and the region frame x-05 y-04 `ex_hlaalu_b_04` in the same run. Only 19 of
the 1,351 areas had reached the gate when the build stopped.

## Where

The collision surface gate (`tools/chim/build.py` `hull_surface_gate`, `hull_surface_unit`), stair collision
method 1 (`tools/stair_mesh.py` `collision_pieces_mesh`, `mesh_unit_stair`) and the measured table
`config/collision-hull-surface.json`.

## How it happened

Two defaults changed in v0.0.48-dev2: the collision source (`authored`: the root RootCollisionNode, else the drawn
triangles) and stair collision method 1 (a flight that fails the geometric stair check gets a stairway mesh of
ramps or tread blocks).

1. **The gate measured collision the converter had removed on purpose.** Method 1 drops the collision triangles of
   each flight it replaces (treads, risers and a ramp over the steps) and builds the stairway mesh from the drawn
   flight. The gate still read the whole collision mesh, so those dropped treads counted, and where no piece lies
   under them they count as 64 units deep (the gate's reach: "no piece under it"). All three Balmora meshes are this
   case: `ex_hlaalu_b_01` (29 triangles removed, 31 tread blocks), `ex_hlaalu_b_04` (14 removed, a ramp and 4 tread
   blocks), `ex_hlaalu_b_06` (2 removed, a ramp and a tread block). Adding them to the table would not have helped:
   with the surface rule they were still 64 units deep. `ex_imp_govman_stair` (Ebonheart) is the fourth such mesh.
2. **The table was measured under the old collision choice.** `config/collision-hull-surface.json` (484 meshes, 35
   known) was measured on 18 October 2026, before either default changed. Under the shipped defaults 18 more meshes
   need the rule (the Bitter Coast longboats, rope bridges, weapons placed outdoors, `ex_dwrv_enter00`, `ex_ruin_30`
   and others) and 89 listed meshes no longer do (flora, Vivec banners and waterfalls among them).
3. **One mesh, several profiles.** A cell's visual recipe (the Telvanni coast) or a town's detail budget (Vivec)
   reduces the drawn mesh, and the visible-tread rule and method 1 read the drawn mesh. `ex_de_ship` passes the gate
   in Seyda Neen but fails it in the Telvanni recipe's cells (x+11 y+14, x+16 y+04, x+17 y+04 and x+16 y+05 in the
   first verify run): reduced to a quarter, it keeps none of the visible-tread rule's plates.

## Why it was not caught

The gate excluded the ramps the visible-tread rule replaces, but not the collision method 1 removes; method 1 became
the default without measuring the gate on every mesh under it. The table had no tool to measure it again: its
18 October numbers came from a one-off measurement, so nothing showed that it depended on the collision defaults
and on the cells' visual recipes.

## Reproduction

`tools/hull_surface_survey.py --data-files <Data Files> --work <scratch> --out <report>` at commit f9c18a50 (before
the fix): the three Hlaalu meshes are 64 units deep with and without the rule.

## Repair

1. **The gate leaves out what method 1 removed** (`stair_mesh.collision_pieces_mesh` `record`,
   `stair_mesh.mesh_unit_stair` lod `stair_removed_triangles`, `chim.build.hull_surface_unit`): the mesh worker
   records the collision triangles of the flights the stairway mesh replaced; the gate measures the rest of the
   collision mesh. The stairway mesh itself stays gated by the stair check. The shipped collision is unchanged: the
   pieces are the same, the lod records one more field.
2. **A re-runnable survey** (`tools/hull_surface_survey.py`): every exterior placement of the base master, split as
   the CHIM source stage splits scenery; one placement per distinct model exported with the CHIM group profile;
   each model prepared by the CHIM model builder's own workers (`chim.build.mesh_unit`,
   `stair_mesh.mesh_unit_stair`) under the shipped defaults, in every profile variant its placements get (a cell's
   visual recipe, a town's detail budget), and measured by the gate's own unit, without and with the rule; the table
   is written from that. 1,394 models (370 with more than one variant), under 4 minutes on 14 cores. It refuses to
   write a table when a mesh fails to measure.
3. **Recipe-scoped entries** (`recipe_meshes`, `chim.build.hull_surface_recipe_table`): a mesh that needs the rule
   only in the cells of one visual recipe gets it there only. `ex_de_ship` under the rule everywhere would add 8,122
   clipnodes to each of its default copies (Seyda Neen's ship among them), which pass the gate without it.
4. **The table measured again** (23 October 2026): 413 meshes (484 before: 18 added, 89 removed), 12 entries for a
   visual recipe only (`telvanni-v1`: 8, `tel-uvirith-v1`: 4), known list empty (35 before). Every mesh over a step
   without the rule is within a step with it, in every variant.

Memory, standing-hull clipnodes of the measured meshes in their default variant (`chim.models.model_image_lumps`;
both columns under the shipped collision defaults):

| Count | Old table | New table | Change |
| --- | --- | --- | --- |
| Meshes on the rule everywhere | 484 | 413 | -71 |
| Their exterior placements | 68,666 | 48,090 | -20,576 |
| Clipnodes, each mesh once | 749,069 | 749,005 | -64 |
| Clipnodes, times placements | 12,349,045 | 12,350,086 | +1,041 (+0.01 %) |

## Verification

CHIM stage alone (`tools/chim_build.py`, the dev2 build's options, no stair walk), commit ff378d73, run
`2026_10_23_v0.0.48-dev2_hull-surface-measure_ff378d73`: Balmora, Seyda Neen, Vivec City and 67 region frames (the
frames closest to the CHIM zone in the v0.0.47 build and their neighbours, the Hlaalu towns, the Telvanni coast,
the Grazelands and a spread of others).

- Collision surface gate: passed in all 69 areas it measures (Seyda Neen's frame comes from the legacy run and has
  no gate), Balmora 226 meshes and Vivec City 352 meshes included; the first two verify runs had stopped at
  `ex_de_ship` in four Telvanni coast frames (cause 3 above).
- CHIM heap gate: passed. Tightest frames: x-07 y-04 368 bytes headroom (v0.0.47: 37,808), x-08 y-04 3,200
  (40,640), x-11 y+15 16,656 (27,424), x+09 y+02 18,192 (21,616). The table changes in those frames are small
  (x-07 y-04: flora with no clipnodes and `ex_dae_ruin_stair01_short` leave the rule, 128 clipnodes per copy); the
  growth against v0.0.47 comes with the v0.0.48-dev2 collision defaults themselves.
- Validation: 0 failures in 70 frames.
- The run stopped afterwards at the CHIM stair check, on two meshes that are in neither table:
  `flora_tree_gl_06` (method 0 kept) and `ex_t_slavemarket` (method 1). That is a separate finding, reported under
  [CHIM-STAIR-METHOD1-UNFIXED-48](CHIM-STAIR-METHOD1-UNFIXED-48.md).

## Prevention

- The survey is a tool in the repo: when a collision default, a visual recipe or a detail budget changes, run it and
  commit the table it writes (`tests/test_hull_surface_survey.py` checks the table's format and that it names the
  shipped defaults it was measured under).
- The gate and the converter agree on what is walked: what a collision method removes on purpose is recorded by the
  converter and left out by the gate (`tests/test_hull_surface_loss.py`, `tests/test_stair_mesh.py`).

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
- [STEP-MOVEMENT-OPENMW-RULES-48](STEP-MOVEMENT-OPENMW-RULES-48.md): The player steps by Quake's rules, not Morrowind's, so stairs are proven by walks instead of by rule
- [TERRAIN-TRAP-29](TERRAIN-TRAP-29.md): v0.0.29-dev1: Player reportedly stuck on rocks beside structures
- [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md): Five Vivec Arena residents fail the actor placement gate
- [VIVEC-ARENA-TP-ARRIVAL-32](VIVEC-ARENA-TP-ARRIVAL-32.md): dbg tp vivec_arena leaves the player at the frame origin under the water
- [VIVEC-TEMPLE-STAIRS-33](VIVEC-TEMPLE-STAIRS-33.md): Palace steps and High Fane quarter flights fail the stair gate on the CHIM Vivec Temple frame
- [WORLD-SLOPE-STUCK-38](WORLD-SLOPE-STUCK-38.md): Player reports being stuck beside Ashlands terrain

Related bugs in other categories:

- CHIM-FRAME-16MB-REFUSAL-48 (no report page): Five CHIM region frames are over or within 64 KiB of the 16 MB heap budget: on 16 MB of Fast RAM (or with Extra RAM off) their rings may not fit the zone

<!-- END GENERATED CATEGORY -->
