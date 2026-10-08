# HEAP-MODEL-SUM-32: Summing per-object costs overestimates a map's heap (11 % median, 39 % worst)

## Status: 8 October 2026

Open. Found by the world streamer measurement (Balmora's 64 shipped maps,
extrapolated to the island).

## Symptom

Adding up each object's parts gives a heap above what `check_world_map_heap` reports for the
whole map, because objects share planes and vertexes inside a map. Related: the whole-world
fit predicts about 1.17 GB of exterior lightmaps while Balmora's real lightmap lumps are
about 3.5 % of what their face offsets imply.

## Where

Estimators built on per-object sums (world estimate, streamer estimate).

## How it happened

Sharing inside a map is not modelled.

## Why it was not caught

Calibrated on map totals.

## Reproduction

Compare per-object sums with check_world_map_heap on Balmora.

## Repair

Not yet: model sharing in the estimators; recalibrate exterior lightmaps on real lumps.

## Verification

Pending.

## Prevention

Estimator checks against measured maps in the suite.
