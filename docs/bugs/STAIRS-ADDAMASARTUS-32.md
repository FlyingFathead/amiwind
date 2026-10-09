# STAIRS-ADDAMASARTUS-32: A low step in the Addamasartus cave is blocked

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:stair-walk |
| First noticed | 8 October 2026, in v0.0.32-dev2 |
| Where | Addamasartus cave, in_moldcave_09 (ref 89756) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev2, v0.0.32 (last seen) |
| Severity | low: A 1-unit step. |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| Playtest version | v0.0.32-dev2 |
| From commit | source and engine 2af54eb |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on branch v0.0.33-stairs-2 (gate classification; not in a build yet): there is no
step here. Was: fails the gate (blocked). Found by the stair walkability gate ([COLLISION-STAIR-SLOPE-32](COLLISION-STAIR-SLOPE-32.md), `tools/stair_walk.py`) on the v0.0.32-dev2 maps, 8 October 2026.

In v0.0.32: the stair walkability gate that found this (`tools/stair_walk.py`, in the image step) is on a development branch and not in v0.0.32; v0.0.32 ships the staircase as described here.

## Symptom

See Where; the gate report (`stair-walk.json`) gives the walk detail.

## Where

addamasartus, `in_moldcave_09` (ref 89756), riser at local 247.8 421.1 35.9, rise 1.0.

## How it happened

The walk is blocked by the cave collision just past a 1-unit step (surface 6.6 degrees). May be the cave proxy over a lip rather than a staircase; needs an in-game look.

Cause (9 October 2026, measured on the addamasartus map rebuilt with the rule): the "step" is two
triangles of the cave floor, tilted 4-10 degrees (normal z 0.986-0.997, inside the gate's 10-degree
"level" tolerance), that meet along one shared edge. The gate took the difference of their mean
heights (1.02) as a riser; at the shared edge the floor has no drop at all. The walk then went on
into a small rock (ref 326704, convex collision about 1.6 units wider than the visible rock), which
is collision fidelity, not a stair (COLLISION-CONVEX-LOSS-32 family). Morrowind has nothing to step
here either.

## Why it was not caught

No check walked converted stairs before the gate.

## Reproduction

`python3 tools/stair_walk.py <id1> --out stair-walk.json` on a build's final maps.

## Repair

Gate classification (`tools/stair_walk.py` `candidates`): a riser is a drop at the shared edge of
the two level faces (their edge heights at the middle of the overlap differ by more than 1 unit),
not a difference of their mean heights. Real steps keep their rise; tilted floor triangles that
share an edge are no longer steps.

## Verification

- Addamasartus map rebuilt with the stair rule, previous gate: 2 flight steps failed (1 gating);
  this gate: no flights (the cave has no staircase), 0 failures.
- Regression fixture: `tests/test_stair_walk_cases.py`
  `test_addamasartus_tilted_floor_triangles_are_not_a_step` (fails on the previous gate; a real
  1.5-unit riser stays a step).

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
- [STAIRS-BALMORA-B01-32](STAIRS-BALMORA-B01-32.md): A Balmora Hlaalu house staircase cannot be approached from below
- [STAIRS-BALMORA-WESTSOUTH-32](STAIRS-BALMORA-WESTSOUTH-32.md): A Hlaalu hall staircase in a Balmora interior has no clear foot
- [STAIRS-SEYDA-LIGHTHOUSE-32](STAIRS-SEYDA-LIGHTHOUSE-32.md): Seyda Neen lighthouse stairs are blocked (outside and inside)
- [STAIRS-SEYDA-WAREHOUSE-32](STAIRS-SEYDA-WAREHOUSE-32.md): A spiral stair in the Seyda Neen warehouse tower is blocked
- TERRAIN-TRAP-29 (no report page): v0.0.29-dev1: Player reportedly stuck on rocks beside structures
- [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md): Five Vivec Arena residents fail the actor placement gate
- [VIVEC-ARENA-TP-ARRIVAL-32](VIVEC-ARENA-TP-ARRIVAL-32.md): dbg tp vivec_arena leaves the player at the frame origin under the water

<!-- END GENERATED CATEGORY -->
