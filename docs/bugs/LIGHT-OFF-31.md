# LIGHT-OFF-31: lights flagged Off by default would bake as lit

## Status: 7 October 2026

Repaired in source the day it was found, before any shipped map was affected.

## Symptom

None seen yet. Unlit props (burnt-out torches, unlit candles and lanterns)
would have shone like lit ones once their rooms were converted.

## Where

`tools/interior_lighting.py`, `bake_surface`, and `tools/light_sources.py`.

## How it happened

The original light record has an "Off by default" flag (0x20) for unlit
props: 26 light types, 136 placements in 56 cells (for example
`light_com_candle_01_off`, `light_com_torch_burnedout_01`). The bake read only
radius and colour, never the flags. None of the 62 cells converted so far
holds such a light, so no shipped map is affected.

## Why it was not caught

Light flags were carried into the lighting data but never read; found while
checking whether any original light follows a time of day (none does).

## Reproduction

Any cell holding an Off-by-default light, for example Vassir-Didanat Cave
(11 placements), once converted.

## Repair

The bake skips lights with the flag; the light-source mapping classes them as
`off` and writes no light entity for them.

## Verification

Unit tests: the same light bakes light without the flag and none with it; the
mapping returns no entity for an `off` light.

## Prevention

Every original light flag is either handled or listed as deliberately ignored
in `docs/LIGHT_SOURCES.md`.
