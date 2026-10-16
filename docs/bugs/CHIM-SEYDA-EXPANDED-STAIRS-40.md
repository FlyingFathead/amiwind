# CHIM-SEYDA-EXPANDED-STAIRS-40: expanded Seyda stair gate

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:chim-stairs |
| First noticed | 15 October 2026, in v0.0.40-dev2 |
| Where | Expanded Seyda CHIM frame: original references 3322 and 3324 |
| Reproduction | once |
| Duplicate of | no |
| Persists in | v0.0.40-dev2 (last seen) |
| Severity | critical: The candidate stops at its required stair-walkability gate. |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| CHIM | Stairs and collision on CHIM worlds ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | v0.0.40-dev2 conversion |
| From commit | source d5d0d79, engine unknown, CHIM world d5d0d79 |
| CHIM engine version | CHIM 0.2.0, engine unknown, world format 0.7 |
| Unknown because | Offline gate against converted geometry; no runtime engine was exercised. |
| Platform or emulator | not in game (Offline CHIM stair walkability gate.) |

<!-- END GENERATED FACTS -->

## Symptom

The expanded Seyda CHIM frame fails 15 stair-flight probes across original
references 3322 and 3324. All report `start in solid`; the gate refuses the candidate.

## Where

Original-cell Seyda town expansion, converted frame `frames/x-02/y-09/frame.ccf`.
Both references are mirrored Imperial wall stairs, physically in owned core
cell (0, -8); their original declared CELL is (0, -7). All failures occur
before traversal. Separate supported-start controls establish a blocked centre route
on both stair references; they do not establish that every sideways route fails.
The first local probe is (4084.165, 3438.263, 490.646), rise 6.4.

## How it happened

Expanded original-cell conversion includes these references. The first completed
walk gate finds the failure. Two limitations are now distinguished: the 8-unit
start probe cannot reach support 11.65-13.56 units above its visual start, and
six physically supported free centre ascents still stop on a 57.50-degree
support face belonging to the stair itself. Earlier smaller-frame passes do
not cover this input. The original authored surface comparison remains pending.

## Why it was not caught

Structural, memory and allocator checks do not establish stair traversal. The
required stair gate caught this before candidate packaging.

## Reproduction

Run the CHIM stair gate on this expanded conversion: 18,024 candidates, 3,724
walked probes, 15 blocking failures and 532 advisory failures. Preserve the
original geometry and result while investigating the two references.

## Repair

15 October 2026, v0.0.40-dev2: fresh complete Seyda conversion at a4a475b passes structure, active-heap/zone and stair checks: 18,024 candidates, 3,724 walked, zero blocking failures, 532 advisory. Two Imperial stairs use original authored collision; render geometry is unchanged. Sixteen original owned cells and twenty apron cells are tracked separately. The 29 zone chunk loads without room remain explicit. Matched native traversal, adjacent-cell visual/collision seams and package acceptance are pending; issue remains open.

The strict original-collision source selection repairs the two measured models
in an isolated producer trial. All 15 old probes pass under existing lateral
sampling; the first centre start still touches neighbour 3329. The original
failed world remains unchanged. Fresh scenery, the complete conversion and
matched in-game traversal must verify the integrated candidate.
See [the collision repair](COLLISION-STAIR-SLOPE-32.md).

## Verification

Fresh full conversion at source a4a475b: 3,724 walked probes pass with zero
blocking failures and 532 advisory. Native traversal and package checks remain
pending. The original fifteen-failure result remains historical evidence.


Structure passes. Active-ring peak is 5,658,640 B against 6,242,304 B. The load
ring reaches 6,392,480 B at 27 over-budget positions. The zone simulation passes
17,424 steps with 29 loads without room and 24 partial activations. Those limits
remain explicit; none of these checks establishes native playability.

Follow-up traces reuse the canonical walker and unchanged collision data. Forward
and raised-forward moves are clear, but the final downward trace hits normal
Z 0.537310, below the unchanged walkable threshold 0.69. Independent descents
also stop; ten repeated idle settles at each supported top and bottom stay
stable. Changing step height, player size or global slope limits is not justified
by these results. The original 15-failure receipt remains unchanged.

Actual-game suspect-geometry captures are pending: no image using this expanded
frame is staged yet. Matched original traversal, native acceptance and packaging
remain unverified.

## Prevention

Keep the required walk gate for each changed frame and preserve original
reference identities so a local failure cannot disappear into a town-wide count.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`). Convex collision proxies invent steep faces or bury authored surfaces; Morrowind collides with authored geometry (step up 34 units, slope up to 46 degrees). Rule: follow_original_stair_rules plus a walkability gate. See [families](README.md#families).

- [BUILD-ACTOR-GATE-CHIM-FRAMES-36](BUILD-ACTOR-GATE-CHIM-FRAMES-36.md): The actor placement gate ignores CHIM frame residents: a CHIM-only build fails with no actors, and a blocked frame resident passes silently
- [BUILD-FLORA-STAIR-PLATES-BUDGET-36](BUILD-FLORA-STAIR-PLATES-BUDGET-36.md): The stair-plate collision rules raised a legacy open-world map past the BSP clip-node limit: world-flora failed on vf0779 (33,172 aggregate clipnodes > 32,767)
- [BUILD-HULL-ROUTE-BUDGET-33](BUILD-HULL-ROUTE-BUDGET-33.md): Routed standing hulls with copies overflow a legacy map's shared clipnode budget
- [BUILD-ROUTED-FLORA-RESERVE-33](BUILD-ROUTED-FLORA-RESERVE-33.md): Routed standing hulls push a legacy open-world map past the flora collision reserve: the full build stops in world-flora (vf0779)
- [BUILD-STAIR-FLAG-INERT-32](BUILD-STAIR-FLAG-INERT-32.md): The stair rule build option does nothing in v0.0.32
- [CHIM-HULL-STAIR-EDGE-33](CHIM-HULL-STAIR-EDGE-33.md): With the qbsp-compiled terrain hull on Balmora's regular ground, one flight of stairs fails at a chunk edge
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

<!-- END GENERATED CATEGORY -->
