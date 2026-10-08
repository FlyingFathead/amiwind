# CONVERT-MERGE-NONPLANAR-32: Merged polygons can be slightly non-planar (up to about 0.05 units)

## Status: 8 October 2026

Open. Found by the texture-mapping snapping test.

## Symptom

Coplanar grouping rounds normals to 4 decimals and plane distances to 2, so a merged polygon
can bend by up to about 0.05 units.

## Where

`tools/mesh_geometry.py` (`surface_polygons`).

## How it happened

Rounded grouping keys.

## Why it was not caught

Small enough not to show.

## Reproduction

Measure vertex distances to each merged face's plane.

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

The same planarity check.
