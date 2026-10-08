# COLLISION-RCN-SCOPE-32: Authored collision meshes (RootCollisionNode) are used by some converters only

## Status: 8 October 2026

Open. Found by the collision census ([COLLISION_MESHES.md](../COLLISION_MESHES.md)). Present in
every release that ships the Seyda Neen exterior or converted rooms.

## Symptom

Morrowind collides with a model's `RootCollisionNode` when it has one. Some AmiWind converters
ignore it and build the collision proxy from the visible mesh instead:

- **Seyda Neen exterior:** 86 models with authored collision (376 placements). Only
  `ex_de_ship` and `siltstrider` use it.
- **Converted rooms:** every model outside `meshes/i/` (furniture, doors, lights, containers,
  `x/` pieces):
  - Balmora rooms: 94 models, 1,138 placements;
  - Seyda Neen rooms with Addamasartus and the prison ship: 62 models, 416 placements.

The visual mesh is about five times the authored collision. Its convex proxies:

- cost more clip nodes (estimate: Seyda Neen exterior 63,576 against 13,247 from the authored
  collision);
- fill space the authored collision leaves open: proxy faces of 52-89 degrees over treads on
  Seyda houses, the lighthouse, the town gate, beds, tables, the loom and closets.

## Where

- `tools/prepare_scenery.py` `export_refs`: the authored collision is read only when the model's
  profile sets `collision_source`.
- `config/scenery_groups.json`: the Seyda Neen exterior scene (`prepare_scenery.py` main ->
  `prepare_mesh_bsp.py` main -> `prepare_seyda_regions.py`) sets it for the ship and the strider
  only.
- `tools/prepare_area.py` `interior_visual_profile`: rooms of `build_room`, used for Seyda Neen,
  `prepare_balmora_interiors.py` and `town_interiors.py`; it only sets it for `meshes/i/`.
- `tools/prepare_census.py`: same, for `meshes/i/` only.
- `tools/prepare_interior.py`: only for `in_prison_ship`.

Unaffected: the town importer (`import_town.py`: Balmora, Vivec Arena), world scenery, the door
overlay and the flora sprites, which use the authored collision for every model.

## How it happened

The collision source was added per converter as an opt-in profile field when each scene was
converted, instead of being the default of the shared export.

## Why it was not caught

No report lists the collision source per model, and no test compares it with the NIF.

## Reproduction

Read each placed model with `prepare_scenery.model_geometry(raw, N, collision=True)`. If it
returns triangles, compare with the profile the converter passes (`collision_source` missing =
visual). The measurement script and the per-model table are described in
[COLLISION_MESHES.md](../COLLISION_MESHES.md).

## Repair

Not yet. Planned: one shared collision-source rule for every converter (root
`RootCollisionNode`, else visual), applied in the export (recommendation 1 in
COLLISION_MESHES.md). The Seyda Neen exterior and room maps change, so the rebuild needs the
walkability, actor-ground and clip-node gates.

## Verification

Pending.

## Prevention

Planned: the converter report records the collision source per model, and a test fails when a
model with a root `RootCollisionNode` is converted from its visual mesh.
