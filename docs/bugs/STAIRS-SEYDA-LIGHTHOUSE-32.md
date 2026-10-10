# STAIRS-SEYDA-LIGHTHOUSE-32: Seyda Neen lighthouse stairs are blocked (outside and inside)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:stair-walk |
| First noticed | 8 October 2026, in v0.0.32-dev2 |
| Where | Seyda Neen lighthouse, outside (sn012) and inside |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev2, v0.0.32 (last seen) |
| Severity | medium: Stairs cannot be used. |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| Playtest version | v0.0.32-dev2 |
| From commit | source and engine 2af54eb |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source (not in a build yet). Exterior: the shared stair rule now cuts slanted risers back
to vertical at the tread edge (`mesh_geometry.vertical_risers`, commit c1f4d87 on
v0.0.33-chim-format); the regenerated CHIM Seyda Neen passes the stair gate. Interior: the last
step was a gate artefact (branch v0.0.33-stairs-2, see "Interior" below).

Was (8 October 2026): the stair rule did not clear the exterior: verified on Seyda Neen regenerated
by the CHIM builder (M2), 8 October 2026 (see "Regenerated Seyda Neen" below). The interior step fails the gate. Found by the stair walkability gate ([COLLISION-STAIR-SLOPE-32](COLLISION-STAIR-SLOPE-32.md), `tools/stair_walk.py`) on the v0.0.32-dev2 maps, 8 October 2026.

In v0.0.32: the stair walkability gate that found this (`tools/stair_walk.py`, in the image step) is on a development branch and not in v0.0.32; v0.0.32 ships the staircase as described here.

## Symptom

See Where; the gate report (`stair-walk.json`) gives the walk detail.

## Where

Exterior sn012, `ex_common_lighthouse` (ref 114026): 5 steps at local about -244..-313 -585..-607 224..261, rises 3.8-6.7, blocked by vertical collision. Interior lighthouse, `in_common_lighthouse` (ref 129152): riser at local 45.7 16.5 -131.3, rise 4.1.

## Regenerated Seyda Neen (CHIM, 8 October 2026)

The CHIM builder regenerates Seyda Neen from the scene stage's inputs with the stair rule on. The
rule acts on this mesh (no RootCollisionNode): "authored plates" for four buried treads, 54 pieces
with exact bevels. The CHIM stair gate (the shared walker on the frame's own collision) still fails
the same five flight steps, all "blocked" on the way up. A trace at the blocked point:

- forward: a vertical face, the riser itself;
- the step up of 8.5: free;
- forward after the step up: free;
- settling down from there: the box lands on the next riser's authored plate, sloped with normal
  z 0.25-0.31 (72-76 degrees), so the walk (as the engine's step: the floor after a step must be
  walkable) rejects the step.

The steps' fronts lean back about 75 degrees in the mesh. The fix is in the shared stair rule
(`mesh_geometry.vertical_risers`, the same for the legacy maps and CHIM, c1f4d87): a collision
face steeper than walkable whose top edge is a tread's front edge is cut back to the vertical
plane through that edge. With the cut, the CHIM stair gate passes all five steps (a private lab
on the owner's mesh: 3 of 5 fail without the cut, 5 of 5 pass with it; the Seyda Neen world:
gate passed). Regression test: `tests/test_stair_slanted_risers.py`.

## Interior (9 October 2026)

On the lighthouse map rebuilt with the rule, the previous gate fails one step (local 45.7 16.5
-131.3, "start in solid"): the walk's settle point 8 units above its start was solid. With the
start column rule of [STAIRS-BALMORA-B01-32](STAIRS-BALMORA-B01-32.md) the walk starts, and is
blocked where the straight line meets the visible lighthouse wall (x 52.2 in the map, 0.9 units
into the standing box even within the gate's visual tolerance): the step has no straight visible
approach and is untestable, not a collision failure. Rebuilt map, this gate: 17 flight steps
passed, 0 failed.

## How it happened

Exterior: the lighthouse collides with its visual mesh through convex proxies; a vertical railing or wall arc closes the spiral treads. The stair rule changes this model (authored plates), but v0.0.32 ships the recorded Seyda Neen stage (BUILD-SEYDA-REGEN-30), so the shipped maps keep the old collision; the gate reports them without failing. Interior: two steps failed; with the rule one still starts in solid.

## Why it was not caught

No check walked converted stairs before the gate.

## Reproduction

`python3 tools/stair_walk.py <id1> --out stair-walk.json` on a build's final maps.

## Repair

- Exterior: `mesh_geometry.vertical_risers` in the shared stair rule (c1f4d87): a collision face
  steeper than walkable whose top edge is a tread's front edge is cut back to the vertical plane
  through that edge (regression test `tests/test_stair_slanted_risers.py`).
- Interior: the gate's start column rule (`tools/stair_walk.py`, v0.0.33-stairs-2; fixture in
  `tests/test_stair_walk_cases.py`).

## Verification

- Exterior: CHIM Seyda Neen world (seyda-003, built with c1f4d87): previous gate 7 flight steps
  passed (1 covered, 1 advisory); this gate 7 passed, 0 failed. Model-space lab of
  `ex_common_lighthouse` with the scene stage's collision: 5 of 5 flight steps pass.
- Interior: see above (17 passed, 0 failed on the rebuilt map).
- Pending: in-game walks inside and outside.

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
- [STAIRS-BALMORA-WESTSOUTH-32](STAIRS-BALMORA-WESTSOUTH-32.md): A Hlaalu hall staircase in a Balmora interior has no clear foot
- [STAIRS-SEYDA-WAREHOUSE-32](STAIRS-SEYDA-WAREHOUSE-32.md): A spiral stair in the Seyda Neen warehouse tower is blocked
- TERRAIN-TRAP-29 (no report page): v0.0.29-dev1: Player reportedly stuck on rocks beside structures
- [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md): Five Vivec Arena residents fail the actor placement gate
- [VIVEC-ARENA-TP-ARRIVAL-32](VIVEC-ARENA-TP-ARRIVAL-32.md): dbg tp vivec_arena leaves the player at the frame origin under the water
- [VIVEC-TEMPLE-STAIRS-33](VIVEC-TEMPLE-STAIRS-33.md): Palace steps and High Fane quarter flights fail the stair gate on the CHIM Vivec Temple frame

<!-- END GENERATED CATEGORY -->
