# EXTENTS-RULE-OLD-INTERIORS-32: The v0.0.32 extent rule breaks the lightmaps of interiors converted before the grid fix

## Status: 8 October 2026

Open. Found by the face validator (tools/check_faces.py) over every map of the shipped v0.0.31 image. Release blocker for any image that pairs the v0.0.32 engine with old interior maps.

## Symptom

Under the v0.0.32 engine's double-precision surface-extent rule, all 58 interiors lit by the
interior bake path in v0.0.31 (Balmora 42, Seyda Neen 15, the Temple) have lightmap faults:
30,695 faces read into the next face's samples and 7 past the end of the lighting lump. The
same maps are clean under the single-precision rule the v0.0.31 engine used. The 68040
extended rule gives the same faults, so an emulator that computes wider may already show
them in v0.0.31.

## Where

`engine/aga/src/model.c` (`CalcSurfaceExtents`, EXTENTS-FPU-RULE-31) against interior maps
baked before the LIGHTMAP-GRID-31 fix.

## How it happened

The engine's rule was unified on double precision; old interiors were baked to the old
single-precision grid.

## Why it was not caught

No check ran old maps against the new rule until the validator.

## Reproduction

`tools/check_faces.py` over a v0.0.31 interior with the default engine rule.

## Repair

Every interior shipped with the v0.0.32 engine is reconverted with the current tools (a
from-scratch build does this); the validator runs over every map of every image as a gate.

## Verification

Pending.

## Prevention

Face validator as a builder gate with the engine rule.
