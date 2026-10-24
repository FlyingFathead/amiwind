# LIGHTMAP-TAIL-31: the last face's lightmap points past the end of the lighting lump

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:map-optimizer |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Interior lightmap bake (prepare_mesh_bsp.py, interior_lighting.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.32 |
| Severity | high: Seven Vivec interiors rejected by the optimizer. |
| Family | Mesh converter geometry (`converter-geometry`) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.44-dev1 (19 October 2026)._

## Status: 8 October 2026

Open. Cause found; repaired in source on the v0.0.32 Vivec fixes branch; not
shipped.

## Symptom

The map optimizer rejects some converted interiors with "Light sample range
outside lump": the room's last face needs more lightmap bytes than remain in
the lighting lump (St. Delyn Storage: offset 358,820 needs 84 bytes, 65 left).

## Where

The mesh converter's lightmap bake (`tools/prepare_mesh_bsp.py`,
`tools/interior_lighting.py` `bake_surface`), against the engine's
`CalcSurfaceExtents` (`engine/aga/src/model.c`). It is the visible end of
[LIGHTMAP-GRID-31](LIGHTMAP-GRID-31.md).

## How it happened

1. The bake sized each face's lightmap from the face's texture coordinates
   in double precision, before the vertices and texture axes were written to
   the map as single precision (and before shared vertices and mappings
   within 1e-5 were merged).
2. Imported texture coordinates often end exactly on a 16-texel line. After
   storage they sit a few millionths of a texel to either side. In St. Delyn
   Storage's last face the stored ends are -0.000023 and 192.00006 (bake: 0
   and 192), so the engine allocates 6 x 14 = 84 samples where the bake wrote
   5 x 13 = 65.
3. Every such face reads into the next face's samples; only the last face of
   the lump runs off its end, which the optimizer catches. In St. Delyn Storage
   3,379 of 29,874 converted faces had a shorter lightmap than the engine
   needs (engine rule; EXTENTS-FPU-RULE-31 describes why the rule itself also
   differed between FPUs).

## Why it was not caught

The bake's own comment noted a pending precision correction; only the last
face of a lump is range-checked, and the shipped interiors' last faces
happened to fit.

## Reproduction

Convert Vivec, St. Delyn Storage and run the map optimizer; or recompute each
face's engine grid from the stored values and compare it with the bytes up to
the next face's offset.

## Repair

The converter computes each face's lightmap grid after writing the face, from
the stored single-precision vertices and texture mapping, by the engine rule
(`tools/surface_grid.py`), and rebakes the face on that grid when it differs
from the bake's. It then rejects a face whose sample count differs from the
engine's.

## Verification

- `tests/test_surface_grid.py`: a lit face whose ends drift outward on storage
  is baked on the engine's 13 x 3 grid (the old bake wrote 11 x 3).
- Vivec dry run with the repaired converter (146 interiors, 192 exterior
  regions): all 7 rooms that failed this way (Dralor Manor, Hall of Wisdom,
  Hlaalu Prison Cells, St. Delyn Storage, Telvanni Vault, Mevel Fererus:
  Trader, Abbey of St. Delyn) pass the optimizer; every map as converted has
  0 faces whose engine-rule lightmap runs into the next face, and every
  optimized map passes the engine-rule light range check.
- Full Linux suite and warning-free engine build. In game: pending.

## Prevention

The converter checks every face's sample count against the engine grid; the
optimizer's oracle checks every face's range by the engine rule.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Mesh converter geometry (`converter-geometry`). Converted faces must be planar, wound to their plane, non-degenerate and within engine ranges; checked by the face validator. See [families](README.md#families).

- AW-20260928-21 (no report page): Exterior Census door/wall overlap
- AW25-02 (no report page): Dry valleys and rises rendered as flooded after coarse terrain conversion
- [BALMORA-TEMPLE-GEOMETRY-29](BALMORA-TEMPLE-GEOMETRY-29.md): Balmora Temple lower rooms: missing walls and floors, collision holes
- BSP-LIGHT-01 (no report page): Vodunius face lightmap range exceeded its lighting lump
- [BUILD-INTERIOR-INDEX-ROUTED-33](BUILD-INTERIOR-INDEX-ROUTED-33.md): Full build stops in the interior stage: the prison ship collision index expects a convex-piece chain, but the converter now routes large standing hulls
- [BUILD-SEYDA-OCEAN-FLOOR-40](BUILD-SEYDA-OCEAN-FLOOR-40.md): Expanded Seyda ocean terrain collapses onto the fixed BSP seal
- CHIM-CAVE21-NONCONVEX-FACE-48 (no report page): The cave piece shared by in_moldcave_21, in_mudcave_21, in_pycave_21 and in_lavacave_21 has a non-convex face, so its collision falls back to the piece chain in every room that uses it
- [CHIM-DOCK-TERRAIN-SEAM-47](CHIM-DOCK-TERRAIN-SEAM-47.md): A pale sliver gap shows where a dock end meets the ground (Bitter Coast, cell -5,-6)
- [CHIM-ROCKS-OPEN-SHELLS-43](CHIM-ROCKS-OPEN-SHELLS-43.md): Several rock meshes on CHIM do not close up: open faces where the rock should be solid
- CHIM-ROOM-LAVA-TOP-ROUNDING-48 (no report page): A lava room was kept as a room map: the pool top compared rounded (record -66.55, brush -66.56)
- [CHIM-STRIDER-SCALED-SEAMS-36](CHIM-STRIDER-SCALED-SEAMS-36.md): Seyda Neen's silt strider (scale 0.89 variant) still shows open seams; Balmora's (scale 1.0) is closed
- [CHIM-TERRAIN-DIAGONAL-40](CHIM-TERRAIN-DIAGONAL-40.md): Terrain triangle diagonals differ from the OpenMW 0.48 reference
- [CONVERT-COLLISION-FALLBACK-32](CONVERT-COLLISION-FALLBACK-32.md): Five Balmora meshes fall back to a collision union in qbsp
- [CONVERT-DEGENERATE-FACES-32](CONVERT-DEGENERATE-FACES-32.md): The converter writes degenerate faces (no area, slivers, repeated vertices)
- [CONVERT-FACE-PLANE-32](CONVERT-FACE-PLANE-32.md): Converter takes a merged face's plane from its first three vertices
- [CONVERT-FACE-WINDING-32](CONVERT-FACE-WINDING-32.md): Six prison faces are wound opposite to their plane side
- [CONVERT-MERGE-NONPLANAR-32](CONVERT-MERGE-NONPLANAR-32.md): Merged polygons can be slightly non-planar (up to about 0.05 units)
- [CONVERT-QHULL-FLAT-32](CONVERT-QHULL-FLAT-32.md): Collision building fails on a flat mesh (chitin shortbow)
- [CONVERT-TEXCOORD-RANGE-32](CONVERT-TEXCOORD-RANGE-32.md): Converter does not check the 16-bit texture-coordinate range
- [EXTENTS-RULE-OLD-INTERIORS-32](EXTENTS-RULE-OLD-INTERIORS-32.md): The v0.0.32 extent rule breaks the lightmaps of interiors converted before the grid fix
- GEO-01 (no report page): Giant mushroom cap gaps after material-wise mesh reduction
- GEO-03 (no report page): Canonical clipping stored reversed-winding fragments
- [GHOSTFENCE-NO-ANIMATION-46](GHOSTFENCE-NO-ANIMATION-46.md): The Ghostfence's shimmering curtain does not move: its texture scroll is dropped by the converter
- INLAND-SHORE-29 (no report page): v0.0.29-dev1: Angular/jagged inland shoreline
- [INTERIOR-HULL-CHAIN-33](INTERIOR-HULL-CHAIN-33.md): The Arena Pit's main structure collides through one chain of 36,545 clipnodes; every trace in the room walks it
- [LIGHTMAP-GRID-31](LIGHTMAP-GRID-31.md): Some baked lightmaps sit one sample row or column off
- [MESH-EBONHEART-DRAGON-PEDESTAL-42](MESH-EBONHEART-DRAGON-PEDESTAL-42.md): Ebonheart: the Imperial dragon statue floats; its converted model starts 236 units above its origin, nothing below
- [MESH-EXTENT-GRID-31](MESH-EXTENT-GRID-31.md): Grid-exact mesh faces exceed the 256-texel surface limit on the 68040
- [MESH-LOD-OPEN-SEAMS-33](MESH-LOD-OPEN-SEAMS-33.md): Static mesh reduction pulls open parts apart: the Silt Strider's hull shows the sky through its shell seams
- [MESH-LOD-TORN-MESHES-33](MESH-LOD-TORN-MESHES-33.md): Island-wide seam audit: 49 reduced meshes tear their seams (town flora, rocks, the arrival ship)
- [MESH-MUCKSPUNGE-SEAM-43](MESH-MUCKSPUNGE-SEAM-43.md): A muckspunge shows a black six-sided seam line across its top
- [MESH-VIVEC-CAP-GAP-38](MESH-VIVEC-CAP-GAP-38.md): Vivec giant mushroom cap has a visible opening
- [NPC-GALLERY-SPIKE-33](NPC-GALLERY-SPIKE-33.md): One gallery model has a vertex 12 units outside its source shape (simplifier spike)
- [NPC-JOINT-GAPS-33](NPC-JOINT-GAPS-33.md): NPC bodies open at the joints: each body part is reduced on its own and pulls back from the part it meets
- [ROUTED-HULL-NODE-ORDER-33](ROUTED-HULL-NODE-ORDER-33.md): A routed standing hull can start above nodes it reaches; the engine stops with "SV_RecursiveHullCheck: bad node number"
- SKY-GROUND-28 (no report page): Rebuilt LAND faces invisible; clouds scroll too fast
- [TOOL-ALIAS-FRAMES-33](TOOL-ALIAS-FRAMES-33.md): The alias model writer refuses more than 32 frames
- [TOOL-SIMPLIFY-MANIFOLD-32](TOOL-SIMPLIFY-MANIFOLD-32.md): Mesh reduction can return open or non-manifold meshes

Related bugs in other categories:

- [EXTENTS-FPU-RULE-31](EXTENTS-FPU-RULE-31.md): Surface extents and lightmap sizes depended on the FPU's arithmetic
- [VIVEC-HEAP-31](VIVEC-HEAP-31.md): Dense Vivec maps exceed the loader heap budget once mappings and extents no longer stop them

<!-- END GENERATED CATEGORY -->
