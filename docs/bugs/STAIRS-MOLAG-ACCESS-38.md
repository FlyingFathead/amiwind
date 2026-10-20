# STAIRS-MOLAG-ACCESS-38: Tel Uvirith walkway step and door stairs block normal walking

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 13 October 2026, in v0.0.38-dev2 |
| Where | Tel Uvirith exterior (10,1): raised walkway step and stairs to doors |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.38-dev2 (last seen) |
| Severity | high: Normal walking is blocked at walkway and door access points. |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| CHIM | Stairs and collision on CHIM worlds ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | MiniWind v0.0.38-dev2 diagnostic Tel Uvirith |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine unknown, world format unknown |
| Unknown because | Screenshot banner identifies dev2; exact played map and executable hash binding remains pending. |
| Platform or emulator | WinUAE |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.43-dev3 (18 October 2026)._

Location correction, 13 October 2026: the inspected cell (10,1) is Tel Uvirith
at Uvirith's Grave in Molag Amur, not Molag Mar. The established bug ID and
diagnostic filenames are retained for traceability. This correction does not
change the issue status or establish package/native acceptance.


## Symptom

The maintainer reports getting stuck at a raised walkway step and on the stairs leading to doors in the Tel Uvirith inspection map. Two screenshots document the walkway area. Door stair locations need individual capture and reference identification.

## Where

Exterior cell (10,1). The first screenshot HUD reads global XYZ approximately (85676,11440,1852), local XYZ (-84,-211,462), heading SE 137 degrees, time 15:16. Treat these as screenshot transcription pending exact pose readback. The visible build banner is v0.0.38-dev2 / Private door bitmap trial; the banner alone does not identify the exact compiled map revision.

## How it happened

Unknown. Possible collision-hull, step-height or missing support geometry must be distinguished from the original route design with matched OpenMW traversal. Do not assume a levitation requirement or blame render simplification without evidence.

## Why it was not caught

Visual inspection and noclip exploration do not establish that a route can be walked. This report identifies missing normal-walking coverage at these access points.

## Reproduction

1. Load the reported Tel Uvirith diagnostic map and approach the pictured walkway step in cell (10,1).
2. Disable noclip and try crossing in both directions under normal movement. The maintainer reports becoming stuck. God mode was on in the first screenshot; it does not bypass collision.
3. Independently exercise each reported stair approach to a door. Exact door references remain to be recorded.
4. Compare the same routes and poses in the original game through OpenMW, including whether ordinary walking or jumping succeeds.

## Repair

No repair established. Inspect AmiQuake step handling and the relevant CHIM hulls before choosing a local geometry or movement correction. Preserve the visible steps and door access; do not raise the global step limit merely to pass one location.

## Verification

Maintainer report and two original screenshots received. Independent reproduction, matched OpenMW comparison, exact model/reference binding and repaired normal-walking traversal are pending. Noclip is not an acceptance test.


## Existing staircase rules and tests

Use the existing [stair rules and gate](../STAIR_RULES.md) and
[ramp slope diagnosis](../STAIR_RAMP_WALKABILITY.md), rather than treating this
as a new movement-policy problem. The shared engine cutoff is
`AW_WALKABLE_Z = 0.69` (approximately 46.37 degrees from horizontal), with
an 8.5-unit step-up. The earlier measured ramp at 45.760 degrees failed the
old 0.7 cutoff; that does not establish the angle or cause at this location.

Trace the actual standing hull and record the blocking reference, full-precision
normal, surface angle and step rise. Check whether the diagnostic compile enabled
`follow_original_stair_rules` and whether its final map has a matching
`stair-walk.json` receipt. Exercise the existing `tools/stair_walk.py` checks on
the affected door flights and the individual walkway seam, then verify normal
walking in game. The documented gate treats lone steps as advisory, so a passing
flight gate alone cannot establish access across this pictured single step.
Confirm the current gate classification for each route rather than assuming it
was covered. Existing regression coverage includes `tests/aga_walk_test.c`,
`tests/test_walkability_audit.py` and `tests/test_stair_walk_cases.py`.

## Prevention

Add the walkway seam and each affected door stair flight to the stair/access regression routes. Verify both directions and doorway activation in the exact packaged candidate.

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
- [STAIRS-SEYDA-LIGHTHOUSE-32](STAIRS-SEYDA-LIGHTHOUSE-32.md): Seyda Neen lighthouse stairs are blocked (outside and inside)
- [STAIRS-SEYDA-WAREHOUSE-32](STAIRS-SEYDA-WAREHOUSE-32.md): A spiral stair in the Seyda Neen warehouse tower is blocked
- [STAIRS-VIVEC-ROOMS-JOINT-36](STAIRS-VIVEC-ROOMS-JOINT-36.md): Six flight steps in three Vivec rooms are blocked where one stair piece meets the next
- [TERRAIN-TRAP-29](TERRAIN-TRAP-29.md): v0.0.29-dev1: Player reportedly stuck on rocks beside structures
- [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md): Five Vivec Arena residents fail the actor placement gate
- [VIVEC-ARENA-TP-ARRIVAL-32](VIVEC-ARENA-TP-ARRIVAL-32.md): dbg tp vivec_arena leaves the player at the frame origin under the water
- [VIVEC-TEMPLE-STAIRS-33](VIVEC-TEMPLE-STAIRS-33.md): Palace steps and High Fane quarter flights fail the stair gate on the CHIM Vivec Temple frame
- [WORLD-SLOPE-STUCK-38](WORLD-SLOPE-STUCK-38.md): Player reports being stuck beside Ashlands terrain

<!-- END GENERATED CATEGORY -->
