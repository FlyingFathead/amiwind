# CHIM-VOS-TEMPLE-WALKWAY-41: Vos walkway stair starts inside the Velothi temple's collision and fails the stair gate

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 16 October 2026, in v0.0.41-dev5 |
| Where | Vos (11,14): ex_vivec_b_wb_01 ref 177306 meets ex_velothi_temple_01 ref 177289 |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.41 |
| Severity | high: stopped the v0.0.41-dev5 build after 1 h 35 min; Vos cannot join CHIM while it fails |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| CHIM | Stairs and collision on CHIM worlds ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_16_v0.0.41-dev5_full-regional-bc-ac_c2aaf80 |
| From commit | source c2aaf80, engine c2aaf80, CHIM world c2aaf80 |
| CHIM engine version | CHIM 0.2.1, engine c2aaf80, world format 0.7 |
| Platform or emulator | not in game (the CHIM stair gate refuses the world at build time) |

<!-- END GENERATED FACTS -->

## Symptom
The v0.0.41-dev5 build stopped at the end of its CHIM stage, after 1 h 35 min. The stair gate found two
flight steps it cannot walk. Both are the same step, the top step of a walkway stair in Vos, walked in the
border of two new CHIM frames, (12,13) and (12,14). The detail: `start in solid`, in the collision of the
Velothi temple beside the stair. The CHIMport run of 11 October had already failed Vos's own stair walk.

## Where
Vos, cell (11,14), a classic cell next to the new frames: the walkway `ex_vivec_b_wb_01` (reference 177306)
runs under the base slab of the temple `ex_velothi_temple_01` (reference 177289).

## How it happened
The temple's collision is made of convex pieces (`mesh_geometry.collision_parts`). A piece may close up to
2 units of space that the visible mesh leaves open, and the compiled point hull reaches 5 units below the
slab's visible underside. Over the stair's top step the visible headroom is 38 units, and the standing box
is 33.25 units tall. The pieces leave less than that, so the walker's standing box starts inside the
temple's collision. Measured on the test world (point hull at the step's column):

| Surface | Height above the step |
| --- | --- |
| visible underside of the temple slab | 46.0 (38.2 over the top tread) |
| collision (point hull) | 40.5 |
| standing box | 33.25 |

The sibling mesh `ex_velothi_temple_02` already kept its authored collision surfaces for the same reason
(an authored underpass closed by the convex approximation).

## Why it was not caught
- Vos's own stair walk failed in the CHIMport run of 11 October; the finding stayed a tracker status and
  never became a bug page.
- The stair gate also walks every frame's border copies, so a classic neighbour's flight stopped a build of
  two other cells ([BUILD-STAIR-WALK-BORDER-COPIES-41](BUILD-STAIR-WALK-BORDER-COPIES-41.md)).
- The stair gate ran last, after the 77-minute world conversion.

## Reproduction
Build the two frames on their own: `tools/chim_build.py --chim-regions-cells '12,13:l 12,14:l' --validate`
(about 2 minutes). The stair gate fails on reference 177306 in both frames.

## Repair
`ex_velothi_temple_01` now keeps its authored collision surfaces (`tools/town_regions.py visual_profile`,
`hollow_collision` with exact bevels), like `ex_velothi_temple_02`. Regression test:
`tests/test_balmora.py` (the underpass profiles).

## Verification
v0.0.42 (B16), a Vos test world (cells 11,14, 12,13 and 12,14 built on their own, the v0.0.42 walker): with the name
list (`--collision-underside names`, the default) the stair gate passes and the heap gate passes (peak 5.17 of
6.24 MB).

## Prevention
- A CHIMport cell whose stair walk fails gets a bug page the same day, not only a tracker status.
- A general rule instead of the list of names (B16) was built and measured; it stays experimental
  (`--collision-underside rule`, `split`, `whole`; docs/EXPERIMENTAL_FLAGS.md). On every exterior mesh (1,017
  measured) and on the Vos test world:

| Rule | Meshes changed | Standing clip nodes (all meshes) | Vos walkway step | Vos heap peak |
| --- | --- | --- | --- | --- |
| names (default) | - | 643,637 | passes | 5.17 MB |
| a piece filling more than a unit under its own downward triangles: plates | 162 | +98,841 (+15 %) | start in solid | 5.53 MB |
| the same, split first | 162 | +22,887 (+3.6 %) | start in solid | 5.17 MB |
| a piece passing through any authored downward surface of the mesh: plates | 240 | +213,055 (+33 %) | start in solid | 5.63 MB |
| such a mesh keeps all its authored surfaces (whole) | 238 | +807,912 (x2.25) | passes | 7.21 MB (fails the 6.24 MB budget) |

  The blocking surface is a 22.7-degree slope of the temple base 53 units over the step: the step passes only
  when the whole temple keeps its authored surfaces with exact bevels, which the rule cannot give every mesh it
  catches within the heap budget. Next: find which of the temple's pieces closes the walkway (its point hull at
  the step) and make the rule about that piece's bevels.

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
- TERRAIN-TRAP-29 (no report page): v0.0.29-dev1: Player reportedly stuck on rocks beside structures
- [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md): Five Vivec Arena residents fail the actor placement gate
- [VIVEC-ARENA-TP-ARRIVAL-32](VIVEC-ARENA-TP-ARRIVAL-32.md): dbg tp vivec_arena leaves the player at the frame origin under the water
- [VIVEC-TEMPLE-STAIRS-33](VIVEC-TEMPLE-STAIRS-33.md): Palace steps and High Fane quarter flights fail the stair gate on the CHIM Vivec Temple frame
- [WORLD-SLOPE-STUCK-38](WORLD-SLOPE-STUCK-38.md): Player reports being stuck beside Ashlands terrain

Related bugs in other categories:

- [BUILD-STAIR-WALK-BORDER-COPIES-41](BUILD-STAIR-WALK-BORDER-COPIES-41.md): The CHIM stair gate walks every frame's whole border, so each cell's flights are walked many times and unreachable copies can fail a build

<!-- END GENERATED CATEGORY -->
