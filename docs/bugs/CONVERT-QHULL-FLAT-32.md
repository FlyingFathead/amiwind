# CONVERT-QHULL-FLAT-32: Collision building fails on a flat mesh (chitin shortbow)

## Status: 8 October 2026

Open. Found by the asset census (tools/asset_census.py).

## Symptom

`collision_parts` fails with a Qhull "initial simplex is flat" error on the chitin shortbow
mesh, so a placed chitin shortbow would stop a conversion.

## Where

`tools/mesh_geometry.py` (`collision_parts`).

## How it happened

Flat input to a convex hull.

## Why it was not caught

No world placement of it was converted yet.

## Reproduction

Run collision_parts on the chitin shortbow mesh.

## Repair

Not yet: handle flat parts (thin slab or no collision) in the shared code path.

## Verification

Pending.

## Prevention

A test with a flat mesh.
