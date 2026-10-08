

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
