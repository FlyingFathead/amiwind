# TOWN-FRAME-CEILING-32: ground above the town frame ceiling leaks the map

## Status: 8 October 2026

Open. Found by the public world estimate's sample conversions.

## Symptom

The town converter seals each frame with a sky box whose top is at 2,048 units. Where
the ground is higher, the spawn point ends up above the box, qbsp reports a leak and vis
stops ("couldn't read terrain.prt"). Seen converting exterior region w+00+11 022 (ground
at 3,120); 320 Vvardenfell regions have ground above 2,048.

## Where

`tools/import_town.py` (`terrain_map`, the frame's floor and ceiling).

## How it happened

The ceiling was chosen for the towns converted so far, all of them low.

## Why it was not caught

No high region was converted until the whole-world sample.

## Reproduction

Convert region w+00+11 022 with the town converter.

## Repair

Not yet: set each frame's ceiling from its highest ground plus headroom (within the
coordinate range), or shift the frame's local origin down.

## Verification

Pending.

## Prevention

The world estimate checks ground height against the frame ceiling (new column).
