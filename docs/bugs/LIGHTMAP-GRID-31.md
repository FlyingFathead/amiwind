# LIGHTMAP-GRID-31: some baked lightmaps sit one sample row or column off

## Status: 7 October 2026

Open. Cause found in source and measured in the shipped prison ship map; no
repair yet.

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

Not done: compute the grid exactly as `CalcSurfaceExtents` does, from the
single-precision vertices and texture axes (minimum extent 16), and pass it to
`bake_surface` as `sample_grid` (the grid helper in
`tools/repair_bsp_light_bounds.py` already does this).

## Verification

Pending: every face's stored grid equals the engine's after a rebuild.

## Prevention

A gate check that each face's lightmap size equals the engine's computed size.
