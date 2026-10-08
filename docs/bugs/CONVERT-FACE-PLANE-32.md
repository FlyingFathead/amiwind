# CONVERT-FACE-PLANE-32: Converter takes a merged face's plane from its first three vertices

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
