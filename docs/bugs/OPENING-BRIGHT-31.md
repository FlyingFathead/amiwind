# OPENING-BRIGHT-31: the prison ship hold is brighter than the original

## Status: 7 October 2026

Open. Measured against the original; no repair yet.

## Symptom

The opening scene is "too bright"; it should be murky (owner: about 0.4 of
luma too bright at the back of the hold, about 0.6 wanted there), with a
warm lantern toward Jiub.

## Where

The prison ship map's baked light (`tools/prepare_interior.py`,
`tools/interior_lighting.py`). The ship is excluded from the interior luma
setting by design, so `dbg luma` does not change it.

## How it happened

Measured with headlamp off at the same poses, AmiWind v0.0.31-dev2 against the
original (OpenMW reference, game hour 12): the AmiWind 3D view is 1.2 to 2.5
times brighter than the original at every pose (for example 28.5 against 16.0
mean luma looking forward from the start, 17.1 against 11.3 toward the port
hull). The original hold is very dark (mean luma 11 to 16); its start area is
only about 3 to 4 brighter when facing the hanging lantern. Likely
contributors: the bake's ambient floor and per-light falloff differ from the
original's (see [LIGHT-FALLOFF-31](LIGHT-FALLOFF-31.md)), and the hold has no
local darkening.

## Why it was not caught

The ship was never compared light by light with the original.

## Reproduction

New Game; compare the hold with OpenMW at the same position, heading and time.

## Repair

Not done. The owner also asks for more wood colour ("needs more wood colour"):
the original hold's warmth comes from its warm ambient (80, 61, 41) and orange
lanterns, while AmiWind's light is greyscale, so planks show only their dimmed
texture colour. Proposed: a warm colour table for the cell from its own ambient
colour (loaded with the map, no per-pixel cost), the original falloff in the
ship's bake, then a box zone
(a light multiplier for part of a map, baked offline with a soft edge, already
in the bake as an option) at the back of the hold, judged against the same
OpenMW poses.

## Verification

Pending.

## Prevention

The ship's start poses in the regular original-versus-AmiWind capture set.
