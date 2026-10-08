# LIGHTMAP-GRID-31: some baked lightmaps sit one sample row or column off

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
