# MESH-EXTENT-GRID-31: grid-exact mesh faces exceed the 256-texel surface limit on the 68040

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | mesh converter split_surface; Vivec Underworks interiors |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | high: Thirteen Vivec interiors hit the surface extent limit and are rejected or stop the engine at load. |
| Family | Mesh converter geometry (`converter-geometry`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Repaired in source on the v0.0.32 Vivec fixes branch (8 October 2026);
not shipped.

## Symptom

Thirteen converted Vivec interiors (every Underworks and Puzzle Canal levels 1-5)
stop the engine while loading with a bad surface extents error; the map
optimizer rejects them.

## Where

`tools/mesh_geometry.py` `split_surface` (converter) and the 256-texel surface
check in `engine/aga/src/model.c` (`CalcSurfaceExtents`).

## How it happened

Quake's software renderer limits every surface to 256 texels across. The
converter splits large faces to stay under it, but its check rounds to the
16-texel grid. One polygon of `meshes/i/in_sewer_bcorr3_00.nif` spans exactly
240 texels with both ends on grid lines (240 <= 240 passes). Placing the mesh
and storing it as 32-bit floats moves the ends by about 0.003 texel; the
68040's wider intermediate precision then rounds each end outward by one
16-texel block, giving 272 > 256. A plain 32-bit check gives 256, which is why
the converter's own check passed.

## Why it was not caught

The converter checks extents with host floating point, not the target's
rounding; no earlier map had a face sitting exactly on the grid at the limit.

## Reproduction

Convert any Vivec Underworks interior with the current converter and load it
on the target, or run the map optimizer on it.

## Repair

- `tools/mesh_geometry.py` `split_surface` widens each span by 1/16 texel
  (`surface_grid.GRID_GUARD`) before rounding to the grid, so a span ending
  exactly on grid lines at the limit is split; a kept piece stays within 240
  texels whatever the rounding.
- The mesh converter checks every converted face's extents from the stored
  single-precision values under three rules: the engine's (double precision
  after every step, [EXTENTS-FPU-RULE-31](EXTENTS-FPU-RULE-31.md)), single
  precision after every step (GCC's `fsmul`/`fsadd`), and 68040 extended
  intermediates kept unrounded; any extent above 256 stops the conversion
  with the face named (`tools/surface_grid.py` `check_lumps`).
- Correction to the cause above: the compiled engine rounds every step to
  single precision on a real 68040 (256 for this face); the 272-texel stop
  matches the wider arithmetic of the emulator. The engine now uses one
  rule on every FPU.

## Verification

- `tests/test_surface_grid.py`: a synthetic 240-texel span with grid-exact
  ends that grows to 272 texels once stored; the old check keeps it whole,
  the guarded split cuts it into pieces of at most 240 texels under all three
  rules, and the converter check rejects the unsplit face.
- Vivec dry run with the repaired converter: all 13 maps that failed this way
  (Arena, Foreign Quarter, Hall, Hlaalu, Redoran, St. Delyn, St. Olms and
  Telvanni Underworks, Puzzle Canal levels 1-5) pass the map optimizer; the
  largest extent in all 338 converted maps is 240 texels. The other sewer maps
  outside Vivec (Falasmaryon, Hlormaren, Kogoruhn, Molag Mar) were not rerun.
- Full Linux suite and warning-free engine build. In game: pending.

## Prevention

The converter's three-rule extent check on every converted face.

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
- [LIGHTMAP-GRID-31](LIGHTMAP-GRID-31.md): Some baked lightmaps sit one sample row or column off
- [LIGHTMAP-TAIL-31](LIGHTMAP-TAIL-31.md): Interior lightmap: the last face points past the end of the lighting lump
- [MESH-LOD-OPEN-SEAMS-33](MESH-LOD-OPEN-SEAMS-33.md): Static mesh reduction pulls open parts apart: the Silt Strider's hull shows the sky through its shell seams
- [MESH-LOD-TORN-MESHES-33](MESH-LOD-TORN-MESHES-33.md): Island-wide seam audit: 49 reduced meshes tear their seams (town flora, rocks, the arrival ship)
- [ROUTED-HULL-NODE-ORDER-33](ROUTED-HULL-NODE-ORDER-33.md): A routed standing hull can start above nodes it reaches; the engine stops with "SV_RecursiveHullCheck: bad node number"
- SKY-GROUND-28 (no report page): Rebuilt LAND faces invisible; clouds scroll too fast
- [TOOL-ALIAS-FRAMES-33](TOOL-ALIAS-FRAMES-33.md): The alias model writer refuses more than 32 frames
- [TOOL-SIMPLIFY-MANIFOLD-32](TOOL-SIMPLIFY-MANIFOLD-32.md): Mesh reduction can return open or non-manifold meshes

Related bugs in other categories:

- [EXTENTS-FPU-RULE-31](EXTENTS-FPU-RULE-31.md): Surface extents and lightmap sizes depended on the FPU's arithmetic
- [VIVEC-HEAP-31](VIVEC-HEAP-31.md): Dense Vivec maps exceed the loader heap budget once mappings and extents no longer stop them
- [VIVEC-TEXINFO-31](VIVEC-TEXINFO-31.md): Dense Vivec canton regions exceed the 32,767 texture-mapping limit

<!-- END GENERATED CATEGORY -->
