# CHIM-LIGHT-CONTENTS-33: Actor lighting and water contents ignore CHIM chunks

## Status: 8 October 2026

Open. Found by the first CHIM engine slice (branch v0.0.33-chim-engine).

## Symptom

`R_LightPoint` lights actors from the world model only, not CHIM terrain, and `SV_PointContents` gives no
CHIM water.

## Where

`r_light.c`, `sv_world.c` with CHIM chunks.

## How it happened

Both read the world model.

## Why it was not caught

First CHIM engine slice; host tests only, no emulator run yet.

## Reproduction

Stand an actor on CHIM terrain; check its light and water state.

## Repair

Not yet: part of grafting terrain into the world tree (CHIM-TERRAIN-GRAFT-33).

## Verification

Pending.

## Prevention

Host tests.
