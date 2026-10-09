# CONVERT-FACE-PLANE-32: Converter takes a merged face's plane from its first three vertices

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Mesh converter (tools/prepare_mesh_bsp.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31, v0.0.32-dev (last seen) |
| Severity | medium: A merged face takes its plane from three collinear vertices and can sit 29 degrees off. |
| Family | Mesh converter geometry (`converter-geometry`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the texture-mapping snapping test. Fixed in snap mode only; the default path still has it.

## Symptom

A merged polygon can start with three collinear vertices; its plane is then wrong. In today's
output one face each in Khuul regions w-09+17036 and 037 (a Redoran hut) is 29 degrees off,
with vertices 3.49 units off the plane; with snapping a Seyda Neen house wall was 17.7 units off.

## Where

`tools/prepare_mesh_bsp.py` (`_prepare_placement`).

## How it happened

The plane is computed from the first three vertices; only the Temple path uses the whole polygon.

## Why it was not caught

No per-face planarity check.

## Reproduction

Check every face's vertices against its plane in a converted Khuul region.

Scope (face validator, shipped v0.0.31): 42 faces fail planarity (over 0.25 units) in 22 maps and
41 fail plane tilt (over 5 degrees) in 5 maps; worst a Temple face 27.1 units off its plane at
42 degrees. The Temple path computes the plane from the whole polygon and still has them, so
the shared builder must also refit or split non-planar merged polygons.

## Repair

One repair for all three (owner, 8 October 2026: no path-specific patches): a single
face builder used by every converter path (plane from the whole polygon, refit after
merging, the engine's extent rule, texture-coordinate range, lightmap size from stored
values), and a face validator run on every map as a builder gate. The validator runs
first over the shipped maps to measure how many faces are wrong today. The snap-mode
plane fix is removed once the shared builder is in.

## Verification

Pending.

## Prevention

A planarity check on converted faces.

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
- [CONVERT-FACE-WINDING-32](CONVERT-FACE-WINDING-32.md): Six prison faces are wound opposite to their plane side
- [CONVERT-MERGE-NONPLANAR-32](CONVERT-MERGE-NONPLANAR-32.md): Merged polygons can be slightly non-planar (up to about 0.05 units)
- [CONVERT-QHULL-FLAT-32](CONVERT-QHULL-FLAT-32.md): Collision building fails on a flat mesh (chitin shortbow)
- [CONVERT-TEXCOORD-RANGE-32](CONVERT-TEXCOORD-RANGE-32.md): Converter does not check the 16-bit texture-coordinate range
- [EXTENTS-RULE-OLD-INTERIORS-32](EXTENTS-RULE-OLD-INTERIORS-32.md): The v0.0.32 extent rule breaks the lightmaps of interiors converted before the grid fix
- GEO-01 (no report page): Giant mushroom cap gaps after material-wise mesh reduction
- GEO-03 (no report page): Canonical clipping stored reversed-winding fragments
- INLAND-SHORE-29 (no report page): v0.0.29-dev1: Angular/jagged inland shoreline
- [LIGHTMAP-GRID-31](LIGHTMAP-GRID-31.md): Some baked lightmaps sit one sample row or column off
- [LIGHTMAP-TAIL-31](LIGHTMAP-TAIL-31.md): Interior lightmap: the last face points past the end of the lighting lump
- [MESH-EXTENT-GRID-31](MESH-EXTENT-GRID-31.md): Grid-exact mesh faces exceed the 256-texel surface limit on the 68040
- [MESH-LOD-OPEN-SEAMS-33](MESH-LOD-OPEN-SEAMS-33.md): Static mesh reduction pulls open parts apart: the Silt Strider's hull shows the sky through its shell seams
- [ROUTED-HULL-NODE-ORDER-33](ROUTED-HULL-NODE-ORDER-33.md): A routed standing hull can start above nodes it reaches; the engine stops with "SV_RecursiveHullCheck: bad node number"
- SKY-GROUND-28 (no report page): Rebuilt LAND faces invisible; clouds scroll too fast
- [TOOL-ALIAS-FRAMES-33](TOOL-ALIAS-FRAMES-33.md): The alias model writer refuses more than 32 frames
- [TOOL-SIMPLIFY-MANIFOLD-32](TOOL-SIMPLIFY-MANIFOLD-32.md): Mesh reduction can return open or non-manifold meshes

<!-- END GENERATED CATEGORY -->
