# INTERIOR-BAKE-UNIFORM-32: Some interior bakes are uniform (lights possibly missing)

## Status: 8 October 2026

Open. Found by the asset census (tools/asset_census.py).

## Symptom

The Addamasartus cave bake stores 239,110 samples in 2,351 bytes, and its rocks keep 14 bytes
for 60,490 samples: the light is uniform, which suggests missing light sources in the bake.

## Where

Interior light bake.

## How it happened

Unknown.

## Why it was not caught

No check on light variation.

## Reproduction

Read the Addamasartus map's lighting lump.

## Repair

Not yet: check the bake's light list against the cell's lights; headlamp-off frames.

## Verification

Pending.

## Prevention

Light variation check per interior.
