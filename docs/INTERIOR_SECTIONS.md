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
