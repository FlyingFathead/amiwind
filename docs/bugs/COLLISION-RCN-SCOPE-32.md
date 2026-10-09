# COLLISION-RCN-SCOPE-32: Authored collision meshes (RootCollisionNode) are used by some converters only

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.31 |
| Where | Converters' collision source (prepare_scenery, prepare_area, prepare_census) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31 (last seen) |
| Severity | medium: Some converters collide with visual meshes, inventing steep faces. |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| Playtest version | v0.0.31 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

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
