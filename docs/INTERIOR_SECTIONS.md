# Interior sections

An interior that does not fit its limits is split or lightened, never just left out. This page holds the
order of the repairs, how sections are cut and how cuts are tried in the inspector.

## Interiors over a limit: the order

A converted interior is a Quake map with three hard limits: 220 placed models of its own (inline models,
INTERIOR-INLINE-LIMIT-31), the room heap budget (VIVEC-HEAP-31) and the coordinate range of +-4,096 units
(INTERIOR-COORDS-31). The builder lists every room it leaves out with the limit it missed (for Vivec:
`chim-rooms-vivec_city/rooms.json`, key `excluded`). Repairs, in this order, each one measured before the
next:

1. **Numerous decorative meshes become sprites.** Potted plants and similar small scenery drawn as sprites
   are no inline models; the room gets fewer models, less memory and a faster frame. The sprite keeps the
   plant's outline (the sprite shape rule of the world flora).
2. **The heaviest meshes are reduced, mesh by mesh.** A per-mesh recipe (`config/visual-recipes.json`) or
   the mesh optimizer, as an A/B against the room's current build: the optimizer can make merged meshes
   larger, so only a measured gain is kept. Collision keeps the original mesh.
3. **Sub-cell cuts at hallways and doorways.** The room is split into sections where the player walks
   through a narrow passage anyway: doorway and hallway pieces and the narrow points of the walkable floor.
   Each section has its own limits; every original object stays in exactly one section
   (`tools/prepare_interior_sections.py`). Planned for v0.0.42: the builder proposes the cuts and scores
   each side against the limits; the proposal is reviewed in the inspector's divider (below).
4. **Recentring** for a room whose coordinates pass +-4,096.

### What the builder does today (v0.0.42)

- **Before any step: same-lit placements share one model.** A lit room bakes light into every placed object,
  so each one used to be a model of its own. A placement that no light can reach (every light farther than
  its reach from the object's bounding sphere plus the farthest lightmap sample) is lit by the room's ambient
  alone on every sample, so equal placements of the same mesh share one model; what is drawn does not change
  (`prepare_mesh_bsp.unlit_placement`, `tests/test_shared_ambient.py` checks every sample). Earlier rule:
  `AMIWIND_SHARED_AMBIENT=off`. Rooms with light zones never share.
- **Step 1, plants as sprites,** only for a room still over its model limit: the room converter converts it
  again with its nonsolid static plants (an NC/NCO marker or ground vegetation without an authored collision
  node) as sprites (`tools/interior_plants.py`). A sprite keeps the plant's outline from its alpha; since
  sprites are not lit by the renderer, each one is shaded with the room's colormap at the light its
  placement gets, one sprite file per plant mesh and light step. A sprite file counts as one model slot.
  Harvestable plants (containers) and plants you can bump into keep their mesh. The receipt
  (`conversion.json` `plant_sprites`, `limit_steps`) lists every plant and what it became. Earlier rule:
  `AMIWIND_INTERIOR_PLANTS=meshes` (the room fails as before). A room over its heap budget, which the room
  converter cannot see (the heap is estimated in the image step), asks for plant sprites in its town config row:
  `"plants": "sprites"` (Vivec, Hlaalu Underworks).
- **Step 3, cut proposal:** `tools/propose_interior_cuts.py ROOM_FOLDER ... --out proposal.json` reads
  converted rooms and proposes vertical cuts through doorway and hallway pieces, with the model slots of each
  side (by the converter's own sharing rule) and the placements a cut would cross. A proposal is reviewed in
  the inspector's divider before any section is built; no cut is applied by the builder.
- **Step 4, recentring:** a room row in the town config can carry `"recentre": [x, y, z]` (original units).
  The converter subtracts it from every position of the room, its lights and its arrivals, and every door bank
  that leads into the room subtracts it from the arrival (`town_interiors.room_offsets`, `recentre_cell`).

## Measured fallback after subdivision — 6 October 2026

Divide oversized interiors at natural doorways, corridors and cave bends first.
If a section still exceeds its memory/frame budget, use the polycount inspector
and allocation profile to identify the responsible objects. Selective lower-poly
variants of large decorative, non-pickable mushrooms or other costly scenery
are an approved fallback. Preserve silhouette, closed seams, UV/material
boundaries, collision and original placement. The wireframe is see-through;
density colours alone do not establish visible per-frame cost. Measure again
after conversion and on the Amiga before admission.

## Trying cuts in the 3D Map Inspector

The inspector's sub-cell divider draws candidate cuts through the converted
room, counts faces, placements, lightmap bytes and an estimated heap share for
each side, and exports the cuts as a section plan in the
`tools/prepare_interior_sections.py` format with the receipt fields left
`PENDING`. `tools/region_cuts.py plan` turns any section plan into an overlay
for review. See
[sub-cell cuts](POLYCOUNT_INSPECTOR.md#build-020-sub-cell-cuts-and-divider).
