# STAIRS-SEYDA-WAREHOUSE-32: A spiral stair in the Seyda Neen warehouse tower is blocked

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:stair-walk |
| First noticed | 8 October 2026, in v0.0.32-dev2 |
| Where | Seyda Neen warehouse tower, in_common_tower_thatch (ref 321953) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev2, v0.0.32 (last seen) |
| Severity | medium: A staircase cannot be used. |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| Playtest version | v0.0.32-dev2 |
| From commit | source and engine 2af54eb |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on branch v0.0.33-stairs-2 (gate classification; not in a build yet): the last
failing step is walkable; the gate's start touched the tower wall. Was: fails the gate (start in
solid) after the rule. Found by the stair walkability gate ([COLLISION-STAIR-SLOPE-32](COLLISION-STAIR-SLOPE-32.md), `tools/stair_walk.py`) on the v0.0.32-dev2 maps, 8 October 2026.

In v0.0.32: the stair walkability gate that found this (`tools/stair_walk.py`, in the image step) is on a development branch and not in v0.0.32; v0.0.32 ships the staircase as described here.

## Symptom

See Where; the gate report (`stair-walk.json`) gives the walk detail.

## Where

warehouse, `in_common_tower_thatch` (ref 321953), riser at local 127.0 -7.6 8.2, rise 6.7.

## How it happened

The tower's authored plates had approximate standing bevels; 9 of its flight steps failed. With the stair rule (exact bevels on plate meshes with stairs) 8 pass; one riser still starts in solid.

Cause of the last one (9 October 2026, measured on the mesh and on the warehouse map rebuilt with
the rule): the tower's collision (`RootCollisionNode`) is an authored ramp of 33 degrees under the
visible spiral of block steps, beside the curved tower wall. The step runs diagonally, so the
standing box reaches 8.9 units towards the slanted wall; 11 units before the riser the box centre
is 8.78 units from the wall: the box touches the visible wall by 0.12 (inside the gate's 0.5
visual tolerance), and the wall's collision plate (0.2 thick) holds it, so the walk started in
solid. 3 units to the side the start is open and the step is climbed and descended.

## Why it was not caught

No check walked converted stairs before the gate.

## Reproduction

`python3 tools/stair_walk.py <id1> --out stair-walk.json` on a build's final maps.

## Repair

Gate classification (`tools/stair_walk.py`): a start box closer than 0.25 to a visible surface (the
collision plates stand 0.2 off each surface) is retried up to 3 units to either side, then further
back; a walk blocked where the box grown by 0.25 sideways meets visible geometry is untestable, not
a failure. The stair rule (exact bevels on the tower's plates) is unchanged.

## Verification

- Warehouse map rebuilt with the stair rule (v0.0.33-stairs-2 interior stage), previous gate: 12
  flight steps passed, 1 failed (start in solid); this gate: 13 passed, 0 failures (8 untestable:
  no straight visible approach on the spiral, as before).
- Model-space lab: 9 passed and 2 failing before, 10 passed and 0 failing after.
- Regression fixture: `tests/test_stair_walk_cases.py`
  `test_warehouse_start_grazing_a_wall_is_retried_to_the_side` (fails on the previous gate).
- Pending: an in-game walk up the tower.

## Prevention

The stair walkability gate in the image step.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`). Convex collision proxies invent steep faces or bury authored surfaces; Morrowind collides with authored geometry (step up 34 units, slope up to 46 degrees). Rule: follow_original_stair_rules plus a walkability gate. See [families](README.md#families).

- [BUILD-HULL-ROUTE-BUDGET-33](BUILD-HULL-ROUTE-BUDGET-33.md): Routed standing hulls with copies overflow a legacy map's shared clipnode budget
- [BUILD-ROUTED-FLORA-RESERVE-33](BUILD-ROUTED-FLORA-RESERVE-33.md): Routed standing hulls push a legacy open-world map past the flora collision reserve: the full build stops in world-flora (vf0779)
- [BUILD-STAIR-FLAG-INERT-32](BUILD-STAIR-FLAG-INERT-32.md): The stair rule build option does nothing in v0.0.32
- [CHIM-HULL-STAIR-EDGE-33](CHIM-HULL-STAIR-EDGE-33.md): With the qbsp-compiled terrain hull on Balmora's regular ground, one flight of stairs fails at a chunk edge
- [COLLISION-CONVEX-LOSS-32](COLLISION-CONVEX-LOSS-32.md): Convex collision proxies lose and invent authored surfaces
- [COLLISION-HULL-CHAINS-33](COLLISION-HULL-CHAINS-33.md): 183 brush models across the island collide through standing-hull chains 512 to 31,659 clipnodes deep
- [COLLISION-NC-FLAGS-32](COLLISION-NC-FLAGS-32.md): Morrowind no-collision and editor-marker flags (NC, NCC, MRK, AvoidNode) are ignored by the mesh converters
- [COLLISION-RCN-SCOPE-32](COLLISION-RCN-SCOPE-32.md): Authored collision meshes (RootCollisionNode) are used by some converters only
- [COLLISION-SEYDA-PREVIEW-BYPASS-32](COLLISION-SEYDA-PREVIEW-BYPASS-32.md): The legacy Seyda Neen preview builds its own convex collision
- [COLLISION-STAIR-SLOPE-32](COLLISION-STAIR-SLOPE-32.md): Convex collision proxies make stairs unclimbable
- [SEYDA-BLOCK-31](SEYDA-BLOCK-31.md): Invisible obstacle blocks the path on a Seyda Neen slope
- [STAIRS-ADDAMASARTUS-32](STAIRS-ADDAMASARTUS-32.md): A low step in the Addamasartus cave is blocked
- [STAIRS-BALMORA-B01-32](STAIRS-BALMORA-B01-32.md): A Balmora Hlaalu house staircase cannot be approached from below
- [STAIRS-BALMORA-WESTSOUTH-32](STAIRS-BALMORA-WESTSOUTH-32.md): A Hlaalu hall staircase in a Balmora interior has no clear foot
- [STAIRS-SEYDA-LIGHTHOUSE-32](STAIRS-SEYDA-LIGHTHOUSE-32.md): Seyda Neen lighthouse stairs are blocked (outside and inside)
- TERRAIN-TRAP-29 (no report page): v0.0.29-dev1: Player reportedly stuck on rocks beside structures
- [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md): Five Vivec Arena residents fail the actor placement gate
- [VIVEC-ARENA-TP-ARRIVAL-32](VIVEC-ARENA-TP-ARRIVAL-32.md): dbg tp vivec_arena leaves the player at the frame origin under the water

<!-- END GENERATED CATEGORY -->
