# COLLISION-NC-FLAGS-32: Morrowind no-collision and editor-marker flags (NC, NCC, MRK, AvoidNode) are ignored by the mesh converters

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Mesh converters (prepare_scenery.py collision flags) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Banners, rugs, hooks and waterfalls are solid where Morrowind lets the player pass. |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the collision census ([COLLISION_MESHES.md](../COLLISION_MESHES.md)). Present in
every release with converted meshes.

## Symptom

Morrowind NIFs mark models that do not block the player with a root `NiStringExtraData`:

- `NC...` (in the base game always `NCO`): no collision;
- `NCC`: camera collision only.

`MRK` hides `Tri EditorMarker` shapes, and `AvoidNode` subtrees are NPC pathfinding avoid
shapes. In the base game 373 NIFs carry `NCO`, 48 `NCC`, 6 `MRK` and 6 have an `AvoidNode`.

The mesh converters read none of them. The flagged models become solid:

- banners, tapestries, rugs (`furn_rug_big_*`), hooks and candles;
- ground flora placed in rooms;
- the Vivec banners (`ex_v_ban_*`) and waterfalls.

Placements that Morrowind does not collide with: Balmora exterior 220 of 1,519, Seyda Neen
exterior 214 of 635, Vivec Arena 109 of 433, Balmora rooms 1,177 of 3,408, Seyda Neen rooms 277
of 1,004.

## Where

`tools/prepare_scenery.py` `model_geometry` and `export_refs`, and every converter that uses them
(towns, Seyda Neen, rooms, census, prison ship, world scenery). Only the flora sprite path
(`tools/prepare_tree_sprites.py` `collision_metadata`) honours `NC`/`NCO`; it does not know
`NCC`.

## How it happened

The converter only distinguishes visual and `RootCollisionNode` triangles; the root string flags
were never read.

## Why it was not caught

No comparison with Morrowind's collision rules (OpenMW
`components/nifbullet/bulletnifloader.cpp` `handleRoot`) existed until this census.

## Reproduction

List the root `NiStringExtraData` strings of each placed model. Every model with `NC*` is
converted with a solid collision proxy (`collision_pieces` without `collision_none`).

## Repair

Not yet. Planned with COLLISION-RCN-SCOPE-32, in one shared function:

- `NC*` and `NCC` mean `collision_none` for the player (AmiWind has no camera collision);
- `MRK` drops `Tri EditorMarker*` shapes;
- `AvoidNode` subtrees are excluded.

Rooms and towns then lose these solids, so the actor-ground and walkability gates must be rerun.

## Verification

Pending.

## Prevention

Planned: a unit test on synthetic NIFs for each flag, and a converter report listing the flags
per model.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`). Convex collision proxies invent steep faces or bury authored surfaces; Morrowind collides with authored geometry (step up 34 units, slope up to 46 degrees). Rule: follow_original_stair_rules plus a walkability gate. See [families](README.md#families).

- [BUILD-HULL-ROUTE-BUDGET-33](BUILD-HULL-ROUTE-BUDGET-33.md): Routed standing hulls with copies overflow a legacy map's shared clipnode budget
- [BUILD-ROUTED-FLORA-RESERVE-33](BUILD-ROUTED-FLORA-RESERVE-33.md): Routed standing hulls push a legacy open-world map past the flora collision reserve: the full build stops in world-flora (vf0779)
- [BUILD-STAIR-FLAG-INERT-32](BUILD-STAIR-FLAG-INERT-32.md): The stair rule build option does nothing in v0.0.32
- [CHIM-HULL-STAIR-EDGE-33](CHIM-HULL-STAIR-EDGE-33.md): With the qbsp-compiled terrain hull on Balmora's regular ground, one flight of stairs fails at a chunk edge
- [COLLISION-CONVEX-LOSS-32](COLLISION-CONVEX-LOSS-32.md): Convex collision proxies lose and invent authored surfaces
- [COLLISION-HULL-CHAINS-33](COLLISION-HULL-CHAINS-33.md): 183 brush models across the island collide through standing-hull chains 512 to 31,659 clipnodes deep
- [COLLISION-RCN-SCOPE-32](COLLISION-RCN-SCOPE-32.md): Authored collision meshes (RootCollisionNode) are used by some converters only
- [COLLISION-SEYDA-PREVIEW-BYPASS-32](COLLISION-SEYDA-PREVIEW-BYPASS-32.md): The legacy Seyda Neen preview builds its own convex collision
- [COLLISION-STAIR-SLOPE-32](COLLISION-STAIR-SLOPE-32.md): Convex collision proxies make stairs unclimbable
- [SEYDA-BLOCK-31](SEYDA-BLOCK-31.md): Invisible obstacle blocks the path on a Seyda Neen slope
- [STAIRS-ADDAMASARTUS-32](STAIRS-ADDAMASARTUS-32.md): A low step in the Addamasartus cave is blocked
- [STAIRS-BALMORA-B01-32](STAIRS-BALMORA-B01-32.md): A Balmora Hlaalu house staircase cannot be approached from below
- [STAIRS-BALMORA-WESTSOUTH-32](STAIRS-BALMORA-WESTSOUTH-32.md): A Hlaalu hall staircase in a Balmora interior has no clear foot
- [STAIRS-SEYDA-LIGHTHOUSE-32](STAIRS-SEYDA-LIGHTHOUSE-32.md): Seyda Neen lighthouse stairs are blocked (outside and inside)
- [STAIRS-SEYDA-WAREHOUSE-32](STAIRS-SEYDA-WAREHOUSE-32.md): A spiral stair in the Seyda Neen warehouse tower is blocked
- TERRAIN-TRAP-29 (no report page): v0.0.29-dev1: Player reportedly stuck on rocks beside structures
- [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md): Five Vivec Arena residents fail the actor placement gate
- [VIVEC-ARENA-TP-ARRIVAL-32](VIVEC-ARENA-TP-ARRIVAL-32.md): dbg tp vivec_arena leaves the player at the frame origin under the water

<!-- END GENERATED CATEGORY -->
