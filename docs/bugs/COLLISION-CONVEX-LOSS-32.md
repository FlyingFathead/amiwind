# COLLISION-CONVEX-LOSS-32: Convex collision proxies lose and invent authored surfaces

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev1 |
| Where | Convex collision proxies (tools/mesh_geometry.py, collision_parts) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev1 (last seen) |
| Severity | high: Hulls lose up to 107 units of surface and close space. |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| Playtest version | v0.0.32-dev1 |
| From commit | source and engine 978475d |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found while tracing [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md). Present in every
release that converts meshes with `collision_parts` (towns, open-world scenery).

## Symptom

The convex collision proxy of a mesh can be far from the authored collision surface in both
directions:

- **Lost surface:** each hull is built from at most 14 extreme points (one per sample
  direction), so authored triangles can lie outside it. Measured as the largest distance of a
  source vertex or triangle centre outside its own hull: `ex_vivec_c_02` 106.9 units,
  `ex_vivec_c_04` 97.1 (the Redoran canton top under Ordinator 241614 had no collision),
  Balmora `ex_velothi_temple_01` 31.9, `ex_hlaalu_buttress_05` 17.0, rocks up to 24.3, trees up
  to 23.2.
- **Invented solid:** groups of four or fewer triangles are accepted whatever their error, so
  hulls can close authored space. Deepest closed space: `ex_vivec_c_04` 34.7, Balmora rocks up to
  18.0 (`terrain_rock_wg_13`), trees up to 8.1.

## Where

`tools/mesh_geometry.py` `collision_parts` (14-direction support samples; split only above four
triangles and below depth 8). The module docstring calls this "can miss small details"; the
measured misses are not small.

Unaffected: meshes on surface collision (Balmora's hand-made architecture list, interiors except
rocks, and since VIVEC-ARENA-ACTORS-32 every exterior architecture mesh whose proxy closes more
than a step).

## How it happened

The proxy trades fidelity for clip-node count; the error test only measures triangle centres
inside the hull (invented solid), never surface left outside it, and small groups skip it.

## Why it was not caught

No check compares the proxy with the source surface. The actor gate and the walkability scans
measure the converted collision only.

## Reproduction

For each model of a town's scenery index, run `collision_parts` on its collision mesh and
measure, per hull, the largest distance of its source points outside the hull (lost) and the
`error` value (closed). Measured on the dev1 Balmora and Arena work directories.

## Repair

Not yet. The exterior-architecture part that blocked the Arena residents is repaired by the
surface rule of VIVEC-ARENA-ACTORS-32 (closed space deeper than the step height). Lost surfaces
and organic props (rocks, trees) are unchanged: a general change would alter Balmora and every
open-world map in the last release on the legacy engine. Candidates: build hulls from all points
of a group, split small groups that exceed the tolerance, and add lost surface to the error test,
then re-measure clip-node and heap budgets (the CHIM world format is the natural place).

## Verification

Pending.

## Prevention

Pending: a per-model fidelity report (closed and lost distance) in the conversion reports, with
a limit for architecture.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`). Convex collision proxies invent steep faces or bury authored surfaces; Morrowind collides with authored geometry (step up 34 units, slope up to 46 degrees). Rule: follow_original_stair_rules plus a walkability gate. See [families](README.md#families).

- [BUILD-HULL-ROUTE-BUDGET-33](BUILD-HULL-ROUTE-BUDGET-33.md): Routed standing hulls with copies overflow a legacy map's shared clipnode budget
- [BUILD-ROUTED-FLORA-RESERVE-33](BUILD-ROUTED-FLORA-RESERVE-33.md): Routed standing hulls push a legacy open-world map past the flora collision reserve: the full build stops in world-flora (vf0779)
- [BUILD-STAIR-FLAG-INERT-32](BUILD-STAIR-FLAG-INERT-32.md): The stair rule build option does nothing in v0.0.32
- [CHIM-HULL-STAIR-EDGE-33](CHIM-HULL-STAIR-EDGE-33.md): With the qbsp-compiled terrain hull on Balmora's regular ground, one flight of stairs fails at a chunk edge
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
- [STAIRS-SEYDA-LIGHTHOUSE-32](STAIRS-SEYDA-LIGHTHOUSE-32.md): Seyda Neen lighthouse stairs are blocked (outside and inside)
- [STAIRS-SEYDA-WAREHOUSE-32](STAIRS-SEYDA-WAREHOUSE-32.md): A spiral stair in the Seyda Neen warehouse tower is blocked
- TERRAIN-TRAP-29 (no report page): v0.0.29-dev1: Player reportedly stuck on rocks beside structures
- [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md): Five Vivec Arena residents fail the actor placement gate
- [VIVEC-ARENA-TP-ARRIVAL-32](VIVEC-ARENA-TP-ARRIVAL-32.md): dbg tp vivec_arena leaves the player at the frame origin under the water
- [VIVEC-TEMPLE-STAIRS-33](VIVEC-TEMPLE-STAIRS-33.md): Palace steps and High Fane quarter flights fail the stair gate on the CHIM Vivec Temple frame

Related bugs in other categories:

- [CONVERT-COLLISION-FALLBACK-32](CONVERT-COLLISION-FALLBACK-32.md): Five Balmora meshes fall back to a collision union in qbsp

<!-- END GENERATED CATEGORY -->
