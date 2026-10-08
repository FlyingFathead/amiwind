# VF-VIS-LUMP-32: Open-world terrain maps spend about a fifth of their bytes on visibility data that culls little

## Status: 8 October 2026

Open. Found by the asset census (tools/asset_census.py). Estimated from a 1-in-10 sample.

## Symptom

About 21 % of the open-world (`vf`) map bytes, roughly 0.77 GB, are visibility lumps, although
visibility culls little outdoors (TOWN-VIS-OCCLUSION-31).

## Where

Open-world terrain map builds (vis pass).

## How it happened

Every map runs vis.

## Why it was not caught

Bytes per lump were not reviewed.

## Reproduction

Sum lump sizes over the vf maps.

## Repair

Superseded by the world streamer (heightfield terrain without vis); until then,
measure whether a minimal visibility lump changes anything.

## Verification

Pending.

## Prevention

Lump byte report per map family.
