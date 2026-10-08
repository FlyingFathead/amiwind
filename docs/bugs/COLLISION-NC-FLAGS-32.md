# COLLISION-NC-FLAGS-32: Morrowind no-collision and editor-marker flags (NC, NCC, MRK, AvoidNode) are ignored by the mesh converters

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
