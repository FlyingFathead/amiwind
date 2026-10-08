# CHIM-TERRAIN-GRAFT-33: CHIM chunk terrain is a brush entity, not part of the world tree, so it does not occlude

## Status: 8 October 2026

Open. Found by the first CHIM engine slice (branch v0.0.33-chim-engine).

## Symptom

Chunk terrain is drawn and collided as a brush entity. Until it is grafted into the world tree it does
not occlude (the vis rule), gives placements no leaves, has no water contents, and the per-chunk PVS row
is unused.

## Where

`engine/aga/src/chim/`; world model arrays in `model.c`.

## How it happened

Quake indexes world surfaces, leaves and hulls by position in the world model's own arrays; linking by pointer is not enough.

## Why it was not caught

First CHIM engine slice; host tests only, no emulator run yet.

## Reproduction

Load a CHIM frame; check leaves and contents at chunk terrain.

## Repair

Not yet (next engine slice): pooled world arrays with index relocation; note the 16-bit index cap
(65,535 resident world surfaces and vertices).

## Verification

Pending.

## Prevention

Host tests for grafted leaves, contents and occlusion.
