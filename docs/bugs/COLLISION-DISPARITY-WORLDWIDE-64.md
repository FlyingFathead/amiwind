# COLLISION-DISPARITY-WORLDWIDE-64: Collision data is far larger and deeper than the drawn meshes across the game

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 10 November 2026, in v0.0.64-dev3 |
| Where | converter collision hulls and clipnode chains of placed models in the CHIM stores |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.64-dev3 (last seen) |
| Severity | high: traces near such models walk hundreds to thousands of clipnodes and 123.8 MB of collision sits beside 145.8 MB of drawing in the flagged models alone |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| CHIM | Performance ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_11_10_v0.0.64-dev3_full-v0.0.64-dev3_bf2743f |
| From commit | source bf2743f, engine bf2743f, CHIM world bf2743f |
| CHIM engine version | CHIM 0.2.2, engine bf2743f, world format unknown |
| Unknown because | read from the collision census of the build, not from its receipt |
| Platform or emulator | not in game (found by the offline collision census of the built stores) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.64-dev4 (11 November 2026)._

## Status: 11 November 2026

Open. Reported by the maintainer after the Heart Chamber inspection. The collision census of the v0.0.64-dev3 build
(tools/collision_census.py, 37,706 models) shows that the disparity between collision and drawing is not a few models
but a pattern across the game. Direction decided: collision type 2 (approximate standing bevels) as the build default
for hollow models, balanced collision trees, collision built from the reduced drawn mesh, and census warnings on chain
depth and on the count ratio.

## Symptom

Collision data is much larger and much deeper than the meshes it belongs to. Movement and line-of-sight traces walk
hundreds to thousands of clipnodes through one model, and memory is spent on collision beside the drawing.

## Where

The collision built for placed models and interior pieces in the CHIM stores (converter collision hulls, standing
hulls and clipnode chains), and the census warning that is meant to flag them.

## What the census shows

- Deepest clipnode chain over 64 in 8,202 models, over 200 in 2,009 and over 500 in 517.
- Collision larger than the drawing by count (clipnodes against drawn faces, ratio over 4) in 2,106 models.
- 2,983 flagged models (chain over 200 or count ratio over 8) hold 123.8 MB of collision beside 145.8 MB of drawing.
- The worst chains reach the counter's cap of 32,768 (the Vivec Arena shell parts and the arena, Akulakhan's tiles, the
  Ghostfence citadel) or form one straight chain as long as the whole tree (the four in_*cave_21 cave pieces: 27,950
  clipnodes, deepest chain 27,950, for 1,077 faces).
- Example, the Heart Chamber bridge: 1,745 drawn faces, 22,865 clipnodes, 1,412 collision pieces, deepest chain 811,
  collision 712,976 bytes beside 548,900 bytes of drawing.

## How it happened

Standing-hull collision is built piece by piece as a chain of planes; a model with many pieces, or a hollow model, gets
a chain as long as its piece count, and the collision is built from the full source mesh instead of the reduced mesh
that is drawn. The related entries record the same cause on single model families.

## Why it was not caught

The census warning looked at bytes only (ratio above 2.0 with a minimum size). The Heart Chamber bridge has a byte ratio
of 1.30 but a count ratio of 13.91, so it was never flagged; chain depth was not checked at all.

## Reproduction

Run tools/collision_census.py on a CHIM build and sort by deepest chain or by count ratio.

## Repair

Tracked in the project plan as the worldwide collision reduction: collision type 2 as the default for hollow models,
balanced collision trees in place of straight chains, collision built from the reduced drawn mesh, and census warnings
on chain depth and count ratio besides bytes. Planned for v0.0.64-dev5.

## Verification

The census of the next full build shows no model with a chain over 200 or a count ratio over 8 that is not accepted by
name, the byte total of collision for the flagged models falls, and movement traces near the Heart Chamber bridge and
the cave pieces visit far fewer clipnodes.

## Prevention

The census warns on chain depth and on the count ratio, not only on bytes, and the build refuses a model over the
limits.

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
- CHIM-SOLSTHEIM-HULL-SURFACE-64 (no report page): The CHIM collision surface check refuses 25 Bloodmoon meshes that are not in its measured table
- CHIM-SOLSTHEIM-STAIR-CHECK-64 (no report page): The geometric stair check fails on three Bloodmoon meshes
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

- [CHIM-COLLISION-UNION-FALLBACK-41](CHIM-COLLISION-UNION-FALLBACK-41.md): Daedric ruin collision falls back to raw piece chains and puts Hla Oad's frames over the CHIM memory budget
- [CHIM-TRACE-TAIL-33](CHIM-TRACE-TAIL-33.md): A few CHIM collision traces visit thousands of clipnodes
- [INTERIOR-HULLS-HEAVY-32](INTERIOR-HULLS-HEAVY-32.md): Interior collision hulls are bigger than the interior geometry they belong to

<!-- END GENERATED CATEGORY -->
