# COLLISION-RCN-SCOPE-32: Authored collision meshes (RootCollisionNode) are used by some converters only

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.31 |
| Where | Converters' collision source (prepare_scenery, prepare_area, prepare_census) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.48-dev2 |
| Severity | medium: Some converters collide with visual meshes, inventing steep faces. |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| Playtest version | v0.0.31 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.48-dev2 (22 October 2026)._

<!-- contents start -->
## Contents

- [Status: 22 October 2026](#status-22-october-2026)
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

## Status: 22 October 2026

Fixed in source for v0.0.48-dev2 (branch v0.0.48-authored-collision): one collision-source rule
for every mesh converter, the default (decided for the project, 22 October 2026). Not built and
not checked in game yet. Found by the collision census ([COLLISION_MESHES.md](../COLLISION_MESHES.md));
present in every release up to v0.0.47 that ships the Seyda Neen exterior or converted rooms.

## Symptom

Morrowind collides with a model's `RootCollisionNode` when it has one. Some AmiWind converters
ignore it and build the collision proxy from the visible mesh instead:

- **Seyda Neen exterior:** 86 models with authored collision (376 placements). Only
  `ex_de_ship` and `siltstrider` use it.
- **Converted rooms:** every model outside `meshes/i/` (furniture, doors, lights, containers,
  `x/` pieces):
  - Balmora rooms: 94 models, 1,138 placements;
  - Seyda Neen rooms with Addamasartus and the prison ship: 62 models, 416 placements.

The visual mesh is about five times the authored collision. Its convex proxies:

- cost more clip nodes (estimate: Seyda Neen exterior 63,576 against 13,247 from the authored
  collision);
- fill space the authored collision leaves open: proxy faces of 52-89 degrees over treads on
  Seyda houses, the lighthouse, the town gate, beds, tables, the loom and closets.

## Where

- `tools/prepare_scenery.py` `export_refs`: the authored collision is read only when the model's
  profile sets `collision_source`.
- `config/scenery_groups.json`: the Seyda Neen exterior scene (`prepare_scenery.py` main ->
  `prepare_mesh_bsp.py` main -> `prepare_seyda_regions.py`) sets it for the ship and the strider
  only.
- `tools/prepare_area.py` `interior_visual_profile`: rooms of `build_room`, used for Seyda Neen,
  `prepare_balmora_interiors.py` and `town_interiors.py`; it only sets it for `meshes/i/`.
- `tools/prepare_census.py`: same, for `meshes/i/` only.
- `tools/prepare_interior.py`: only for `in_prison_ship`.

Unaffected: the town importer (`import_town.py`: Balmora, Vivec Arena), world scenery, the door
overlay and the flora sprites, which use the authored collision for every model.

## How it happened

The collision source was added per converter as an opt-in profile field when each scene was
converted, instead of being the default of the shared export.

## Why it was not caught

No report lists the collision source per model, and no test compares it with the NIF.

## Reproduction

Read each placed model with `prepare_scenery.model_geometry(raw, N, collision=True)`. If it
returns triangles, compare with the profile the converter passes (`collision_source` missing =
visual). The measurement script and the per-model table are described in
[COLLISION_MESHES.md](../COLLISION_MESHES.md).

## Repair

v0.0.48-dev2: `tools/collision_source.py`, rules from OpenMW 0.51 `bulletnifloader.cpp`. The
root `RootCollisionNode` when present, else the drawn triangles; NC*/NCC nonsolid; `AvoidNode`
subtrees never collide. `prepare_scenery.export_refs` applies it to every model of every
converter, so no profile opts in and the `meshes/i/`-only limit of the room converters no
longer limits the source. A profile can still require the authored collision (`root_node`).
`--collision-source profile` (`AMIWIND_COLLISION_SOURCE`) keeps the rule before for A/B. The CHIM
source stage's receipt names the rule, so every CHIM source stage runs again once.

## Verification

Read only, on the v0.0.47 release build's room and Seyda Neen scenery exports with the
maintainer's own data (estimated clip nodes, `collision_pieces` plus `standing_planes`, summed over
placements; relative numbers):

| Area | Placements | Changed | Clip nodes before | after |
| --- | ---: | ---: | ---: | ---: |
| Balmora rooms (43) | 3,408 | 1,805 | 507,527 | 285,836 (-44 %) |
| Seyda Neen rooms (13 and Addamasartus) | 770 | 378 | 149,774 | 114,304 (-24 %) |
| Vivec rooms (CHIM rooms) | 13,271 | 6,220 | 4,302,819 | 3,569,324 (-17 %) |
| Seyda Neen scenery (`prepare_scenery`) | 2,789 | 1,568 | 344,060 | 93,495 (-73 %) |

On the changed placements alone: Balmora rooms 234,412 to 12,721, Seyda Neen scenery 329,641 to
79,076. Unit tests on synthetic NIFs: `tests/test_collision_source.py`. In-game check pending.

## Prevention

Every export's `scenery-report.json` lists the collision source of each model
(`collision_sources`). `tests/test_collision_source.py` fails when a model with a root
`RootCollisionNode` is read without it, or when an NC/NCC model is solid.

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
