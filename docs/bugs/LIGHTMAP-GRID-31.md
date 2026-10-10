# LIGHTMAP-GRID-31: some baked lightmaps sit one sample row or column off

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 7 October 2026, in v0.0.31-dev |
| Where | Interior lightmap bake (converter, tools/interior_lighting.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31-dev (last seen) |
| Severity | medium: Lightmaps off by one sample row or column: patchy, misplaced light. |
| Family | Mesh converter geometry (`converter-geometry`) |

<!-- END GENERATED FACTS -->

## Status: 7 October 2026

Open. Cause found in source and measured in the shipped prison ship map.
Repaired in the converter source on the v0.0.32 Vivec fixes branch (8 October
2026) for new conversions; shipped maps keep the fault until they are rebuilt.

## Symptom

Patchy, misplaced light near lamps in converted interiors: a light pool shifted
by one sample step, or a face reading part of its neighbour's light.

## Where

`tools/interior_lighting.py`, `bake_surface` (grid from `floor`/`ceil` of the
texture coordinates), against the engine's `CalcSurfaceExtents`
(`engine/aga/src/model.c`).

## How it happened

The bake computes each face's lightmap grid from the texture coordinates in
double precision, before the vertices are written to the map as single
precision. The engine computes the grid from the stored single-precision
values. When a texture coordinate lies exactly on a multiple of 16 (common:
imported coordinates run 0 to the texture size), the two can round to opposite
sides, so the stored lightmap is shifted by one row or column, and for some
faces the sample count differs from what the engine allocates, so it reads into
a neighbour's samples or drops a row. Measured in the prison ship: 925 of
26,551 faces differ from a recompute (918 with a coordinate on a multiple of
16, 241 with a different sample count); near the opening lantern 204 of 2,117
faces, worst error 120 of 255.

## Why it was not caught

The bake's own comment already notes a pending cross-FPU precision correction;
no check compared the bake's grid with the engine's for every face.

## Reproduction

Recompute the bake grid of every face of `prison.bsp` from the stored
single-precision data, as the engine does, and compare with the stored samples.

## Repair

The mesh converter computes each face's grid after writing it, from the
stored single-precision vertices and texture mapping, by the engine rule
(`tools/surface_grid.py`, minimum extent 16), and rebakes with `sample_grid`
where the bake's grid differs ([LIGHTMAP-TAIL-31](LIGHTMAP-TAIL-31.md)). The
engine rule itself is now one rule on every FPU
([EXTENTS-FPU-RULE-31](EXTENTS-FPU-RULE-31.md)). Shipped maps need a rebuild
with the repaired converter.

## Verification

The Vivec dry run before the repair: St. Delyn Storage had 3,379 of 29,874
converted faces with fewer lightmap bytes than the engine reads. After the
repair: 0 such faces in all 146 Vivec interiors and 192 exterior regions as
converted. Rebuilt shipped maps and in-game check: pending.

## Prevention

A gate check that each face's lightmap size equals the engine's computed size.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Mesh converter geometry (`converter-geometry`). Converted faces must be planar, wound to their plane, non-degenerate and within engine ranges; checked by the face validator. See [families](README.md#families).

- AW-20260928-21 (no report page): Exterior Census door/wall overlap
- AW25-02 (no report page): Dry valleys and rises rendered as flooded after coarse terrain conversion
- [BALMORA-TEMPLE-GEOMETRY-29](BALMORA-TEMPLE-GEOMETRY-29.md): Balmora Temple lower rooms: missing walls and floors, collision holes
- BSP-LIGHT-01 (no report page): Vodunius face lightmap range exceeded its lighting lump
- [BUILD-INTERIOR-INDEX-ROUTED-33](BUILD-INTERIOR-INDEX-ROUTED-33.md): Full build stops in the interior stage: the prison ship collision index expects a convex-piece chain, but the converter now routes large standing hulls
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
- INLAND-SHORE-29 (no report page): v0.0.29-dev1: Angular/jagged inland shoreline
- [INTERIOR-HULL-CHAIN-33](INTERIOR-HULL-CHAIN-33.md): The Arena Pit's main structure collides through one chain of 36,545 clipnodes; every trace in the room walks it
- [LIGHTMAP-TAIL-31](LIGHTMAP-TAIL-31.md): Interior lightmap: the last face points past the end of the lighting lump
- [MESH-EXTENT-GRID-31](MESH-EXTENT-GRID-31.md): Grid-exact mesh faces exceed the 256-texel surface limit on the 68040
- [MESH-LOD-OPEN-SEAMS-33](MESH-LOD-OPEN-SEAMS-33.md): Static mesh reduction pulls open parts apart: the Silt Strider's hull shows the sky through its shell seams
- [MESH-LOD-TORN-MESHES-33](MESH-LOD-TORN-MESHES-33.md): Island-wide seam audit: 49 reduced meshes tear their seams (town flora, rocks, the arrival ship)
- [NPC-GALLERY-SPIKE-33](NPC-GALLERY-SPIKE-33.md): One gallery model has a vertex 12 units outside its source shape (simplifier spike)
- [NPC-JOINT-GAPS-33](NPC-JOINT-GAPS-33.md): NPC bodies open at the joints: each body part is reduced on its own and pulls back from the part it meets
- [ROUTED-HULL-NODE-ORDER-33](ROUTED-HULL-NODE-ORDER-33.md): A routed standing hull can start above nodes it reaches; the engine stops with "SV_RecursiveHullCheck: bad node number"
- SKY-GROUND-28 (no report page): Rebuilt LAND faces invisible; clouds scroll too fast
- [TOOL-ALIAS-FRAMES-33](TOOL-ALIAS-FRAMES-33.md): The alias model writer refuses more than 32 frames
- [TOOL-SIMPLIFY-MANIFOLD-32](TOOL-SIMPLIFY-MANIFOLD-32.md): Mesh reduction can return open or non-manifold meshes

Related bugs in other categories:

- [EXTENTS-FPU-RULE-31](EXTENTS-FPU-RULE-31.md): Surface extents and lightmap sizes depended on the FPU's arithmetic
- [LIGHT-FALLOFF-31](LIGHT-FALLOFF-31.md): Interior lights stop dead at their radius

<!-- END GENERATED CATEGORY -->
