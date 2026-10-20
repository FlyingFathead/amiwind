# CHIM-VIVEC-DOCK-WALKWAY-43: the walkway at the Vivec Hlaalu canton dock cannot be climbed

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.43-dev2 at 2026-10-18 20:29 +0300: maintainer, third person: the player sinks into the dock walkway up to the knees; the collision surface sits below the drawn planks, so the next edge is a step too high
- Reported with v0.0.43-dev2 at 2026-10-18 20:30 +0300: maintainer: likely every walkway of this kind (copied or similar meshes); sweep island-wide: every placement of the dock/walkway meshes, collision top against drawn top
- Reported with v0.0.43-dev2 at 2026-10-18 20:44 +0300: maintainer: another stuck spot on a wooden stair/walkway by the Vivec Arena canton (cell 4,-11, global 33216 -89297 727, local 112 715 181); same family

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 18 October 2026, in v0.0.43-dev2 |
| Where | Vivec, Hlaalu canton dock, cell 2,-11 (local -2198 1067 164); ex_v_dock_01 (ref 278930) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.43-dev2 (last seen) |
| Severity | medium: a walkway in Vivec cannot be climbed; the player is stuck at the spot |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| CHIM | Stairs and collision on CHIM worlds ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_18_v0.0.43-dev2_full-batch3_b55a5ce |
| From commit | source b55a5ce, engine b55a5ce, CHIM world b55a5ce |
| CHIM engine version | CHIM 0.2.1, engine b55a5ce, world format 0.7 |
| Platform or emulator | FS-UAE (maintainer playtest) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.46-dev1 (20 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 3 times; something has to be done](#persisting-reported-3-times-something-has-to-be-done)
- [Status: 18 October 2026](#status-18-october-2026)
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

## Status: 18 October 2026

Cause found and fixed in the shared converter (not yet in a build): a convex collision piece was built from too few
of its points, so its top cut under the walkway's planks. Island-wide the same cause leaves walkable collision more
than a step under 535 meshes, rocks and buildings included. Verification waits for a build with the fix.

## Symptom

At the Hlaalu canton dock in Vivec the player cannot walk up the walkway and stays stuck at its foot; in third person
the player stands knee-deep in the planks. A second spot by the Arena canton (cell 4,-11, local 112 715 181) is the
same: the player stops on the planks looking up the walkway.

## Where

Vivec, Hlaalu canton dock, cell 2,-11 (global position 23975 -87889 656, local -2198 1067 164); the dock model is
`ex_v_dock_01` (source reference 278930). The second spot is another placement of the same model (source reference
278913, frame-local origin 111.9 902.1 92.1); the pick found nothing there because that placement's origin is 187
units from the spot.

## How it happened

Morrowind collides with the dock's authored collision mesh (its RootCollisionNode), which follows the visible planks
to within 4 units. The CHIM converter turns that mesh into convex pieces (`mesh_geometry.collision_parts`). Since the
first repository release each piece's hull was built from only its extreme points along 14 fixed directions, which
gives fewer hull planes. On a deck that runs level and then slopes down, those points are the deck's far corners; the
hull's top then cuts the bend as a straight chord. Measured on `ex_v_dock_01`, the piece tops lie up to 19.4 units
(one unit here is four in the original) under the planks over the walkway's upper end (model-local y -157 to -205).
In the v0.0.43-dev2 frame at the first spot the collision top is at 143.8 and the drawn planks at 160.8: the player
stands 17 units low, and the next edge of the planks is more than a step (8.5) above his feet.

The v0.0.43-dev3 stair fix ([CHIM-STAIR-STEPS-SOLID-43](CHIM-STAIR-STEPS-SOLID-43.md)) does not change it: that rule
lowers collision that stands over visible steps, and this collision lies under them.

## Why it was not caught

The test that splits a convex piece measures only the source surface inside the hull (space the hull closes), never
surface the hull leaves outside. The stair gate walked this walkway and recorded failures, but as ramps that are not
part of a flight, which do not stop a build ([STAIR-FLIGHT-CORE-SPLIT-41](STAIR-FLIGHT-CORE-SPLIT-41.md) has the
same blind spot).

## Reproduction

In v0.0.43-dev2, go to the Hlaalu canton dock in Vivec and walk up the walkway at the spot above.

## Repair

`mesh_geometry.collision_parts` with `surface_loss` (SURFACE_LOSS, 0.5 units): a piece whose extreme-point hull leaves
any of its source points more than that outside keeps the hull of all its points. The CHIM model builder applies it to
the meshes listed in `config/collision-hull-surface.json` (setting `AMIWIND_COLLISION_HULL_POINTS`: `table` by
default; `all` for every mesh; `extremes` keeps the method before for A/B tests). With it the dock becomes 22 pieces
instead of 17, and no piece top lies under the planks by more than 0.5 units.

The table holds the 484 meshes measured on 18 October 2026: every exterior mesh of the base master whose walkable
collision lies more than a step over its extreme-point pieces and within a step with the rule (68,666 placements; 133
terrain rocks and other `f/` meshes, 282 `x/` buildings and walkways). Cost for those meshes at scale 1: clipnodes
132,874 to 203,984, standing-hull bytes 1,064,320 to 1,633,344 (one stored copy of each mesh). Every mesh in every
frame was measured the same way; the rule for all meshes would change 857 meshes and double their standing-hull bytes,
so it stays an option.

Memory, estimated on the v0.0.43-dev2 world: 471 of the table meshes are CHIM models (18,322 variants, 17.7 MB more
stored hull bytes on disk), placed in 1,119 of 1,298 frames. At each frame's heap peak the added hull bytes are at
most 110,272; no frame goes over its budget. The tightest is frame x+17 y+04 (headroom 77,456 to 33,600 bytes).
That estimate counted the standing hull only: in the v0.0.46-dev1 build the planes and nodes the extra hull facets
add to every placed model put six frames over the zone (x+17 y+04 by 174,640 bytes). From v0.0.46 a piece holds its
walkable surface only, not every point: [CHIM-HULL-SURFACE-HEAP-46](CHIM-HULL-SURFACE-HEAP-46.md).

The ex_v_dock_01 numbers: 17 to 22 pieces, 114 to 159 planes, 164 to 220 clipnodes, 1,312 to 1,760 bytes.

## Verification

Planned: the fixed frames through the stair gate and the heap gate, then walking up both walkways in the next build.

## Prevention

The collision surface gate (`chim.build.hull_surface_gate`) checks every CHIM mesh: the walkable surface of its
collision mesh must lie within a step of the top of its convex pieces (`mesh_geometry.surface_loss_depth`), or the
build stops naming the mesh and its depth. 35 measured meshes are still over a step with the rule, by other
converter paths, and are listed as known in the table for a follow-up (boats, rope bridges, Dwemer entrances, tents).
Ramps that the visible-tread rule replaces on purpose are not measured.

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
- [CHIM-SEYDA-EXPANDED-STAIRS-40](CHIM-SEYDA-EXPANDED-STAIRS-40.md): Expanded Seyda CHIM frame fails stair walks at two original references
- [CHIM-STAIR-GATE-POOL-BROKEN-42](CHIM-STAIR-GATE-POOL-BROKEN-42.md): The CHIM stair gate of a whole-Vivec MiniWind stopped the build: a walk worker was killed
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

Related bugs in other categories:

- [CHIM-HULL-SURFACE-HEAP-46](CHIM-HULL-SURFACE-HEAP-46.md): The walkway collision fix put six CHIM frames over the zone: every point of a convex piece kept, sides included

<!-- END GENERATED CATEGORY -->
