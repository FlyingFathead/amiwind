# STAIRS-BALMORA-WESTSOUTH-32: A Hlaalu hall staircase in a Balmora interior has no clear foot

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:stair-walk |
| First noticed | 8 October 2026, in v0.0.32-dev2 |
| Where | Balmora interior bmwestsouth, in_hlaalu_hall_stairsl |
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

Fixed in source on branch v0.0.33-stairs-2 (gate classification; not in a build yet). Not a stair
rule fault and not a placement overlap: the foot of the flight ends at a closed hinged door, which
is the known missing door interaction (AW-20260928-12). Was: fails the gate (start in solid). Found by the stair walkability gate ([COLLISION-STAIR-SLOPE-32](COLLISION-STAIR-SLOPE-32.md), `tools/stair_walk.py`) on the v0.0.32-dev2 maps, 8 October 2026.

In v0.0.32: the stair walkability gate that found this (`tools/stair_walk.py`, in the image step) is on a development branch and not in v0.0.32; v0.0.32 ships the staircase as described here.

## Symptom

See Where; the gate report (`stair-walk.json`) gives the walk detail.

## Where

bmwestsouth, `in_hlaalu_hall_stairsl` (ref 384371), riser at local 1048 1024 3809.3, rise 8.0; the solid at the foot belongs to ref 384326.

## How it happened

The standing hull at the visible foot of the flight is inside the collision of a neighbouring piece (384326). The stair's own authored collision is a 45-degree ramp (walkable at the 0.69 limit). The same model in bmeastguard passes after the gate's box-clearance check.

Cause (9 October 2026, measured on the v0.0.32 bmwestsouth map, the Western Guard Tower South
interior): ref 384326 is `in_hlaalu_door` (DOOR, not a load door: no teleport destination in
Morrowind.esm), closed (rotation 0), standing in its door jamb (`in_hlaalu_doorjamb`, ref 384380)
about 6 units in front of the first riser. Both entrances of the cell (the load door and the roof
trapdoor) arrive at the top of the flight; the door at the foot leads to the lower hall
(`in_hlaalu_hall_3way`). In Morrowind the player opens it; the converter keeps DOORs as closed
static geometry and AmiWind has no hinged-door interaction yet (AW-20260928-12, "Downstairs
interior doors cannot open"), so in AmiWind the flight ends at a closed door. The gate's straight
approach comes from beyond the door: at 11 units the start box is visibly inside the door; at 16.5
units it touches the door's face (0.03 inside the visual 0.5 tolerance) while the door's collision
plate (0.2 thick) reaches it, so the old gate reported "start in solid"; further back the walk is
blocked by the door. The stair's own collision is fine: the other 19 flight steps pass.

## Why it was not caught

No check walked converted stairs before the gate.

## Reproduction

`python3 tools/stair_walk.py <id1> --out stair-walk.json` on a build's final maps.

## Repair

Gate classification (`tools/stair_walk.py`): collision plates stand 0.2 off every visible surface,
so a start box closer than 0.25 to visible geometry is not an open start (retried up to 3 units to
the side, then further back), and a walk blocked where the box, grown by 0.25 sideways, meets
visible geometry is untestable ("visible geometry in the way"), not a collision failure. The flight
steps at the door are now untestable; collision solid where nothing visible is near still fails.
Opening hinged doors stays AW-20260928-12 (the lower hall of this tower is behind such a door).

## Verification

- v0.0.32 bmwestsouth map, previous gate: 19 flight steps passed, 2 failed (start in solid, ref
  384326); this gate: 19 passed, 2 untestable, 0 failures.
- Regression fixture: `tests/test_stair_walk_cases.py`
  `test_westsouth_closed_door_at_the_foot_is_not_a_stair_failure` (fails on the previous gate);
  `test_collision_solid_where_nothing_visible_is_near_still_fails` guards against hiding real faults.
- Pending: an in-game look at the foot of the flight (it should end at the closed door).

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
- [COLLISION-TRACE-COST-33](COLLISION-TRACE-COST-33.md): Movement traces near large models walk long standing-hull chains: tens of ms per trace on a slow 68040 (emulator-relative)
- [SEYDA-BLOCK-31](SEYDA-BLOCK-31.md): Invisible obstacle blocks the path on a Seyda Neen slope
- [STAIRS-ADDAMASARTUS-32](STAIRS-ADDAMASARTUS-32.md): A low step in the Addamasartus cave is blocked
- [STAIRS-BALMORA-B01-32](STAIRS-BALMORA-B01-32.md): A Balmora Hlaalu house staircase cannot be approached from below
- [STAIRS-SEYDA-LIGHTHOUSE-32](STAIRS-SEYDA-LIGHTHOUSE-32.md): Seyda Neen lighthouse stairs are blocked (outside and inside)
- [STAIRS-SEYDA-WAREHOUSE-32](STAIRS-SEYDA-WAREHOUSE-32.md): A spiral stair in the Seyda Neen warehouse tower is blocked
- TERRAIN-TRAP-29 (no report page): v0.0.29-dev1: Player reportedly stuck on rocks beside structures
- [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md): Five Vivec Arena residents fail the actor placement gate
- [VIVEC-ARENA-TP-ARRIVAL-32](VIVEC-ARENA-TP-ARRIVAL-32.md): dbg tp vivec_arena leaves the player at the frame origin under the water
- [VIVEC-TEMPLE-STAIRS-33](VIVEC-TEMPLE-STAIRS-33.md): Palace steps and High Fane quarter flights fail the stair gate on the CHIM Vivec Temple frame

<!-- END GENERATED CATEGORY -->
