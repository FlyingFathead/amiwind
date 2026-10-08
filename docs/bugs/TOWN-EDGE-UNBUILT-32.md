# TOWN-EDGE-UNBUILT-32: Leaving a town into an unbuilt neighbour drops the player into a bare world map

## Status: 8 October 2026

Open. Found by the Vivec cantons import.

## Symptom

Walking off a canton bridge into a neighbour that is not installed drops the player into an
open-world terrain map without the Vivec structures; doors into towns that are blocked or not
opted in say "Interior not found" (no crash).

Owner report in v0.0.32-dev3 play (8 October 2026, "the transition between Vivec's area and the
local flora and fauna" is broken): after leaving the Vivec Arena area, at GLOBAL 42527 -94856 794
(LOCAL -120 349 198), heading NW 311, pitch 3, time 21:35, label "Vvardenfell / Ascadian Isles
Region" (an open-world map south of the Vivec frame, not yet identified), the view is a flat,
featureless grey ground slab with a hard straight edge under the night sky, with no flora or
objects. The Vivec preview does not join the open-world maps around it, and those maps show bare
flat ground there; why the ground is flat and empty is not yet measured. Owner decision: ship
v0.0.32 as is; joining Vivec to the world is CHIM work (M3/M4).

Second owner pose, same play session: GLOBAL 33587 -93027 1991 (LOCAL -307 -216 753), heading N
355, pitch 30, time 04:53, label "Vivec, St. Olms", seen from above (likely in noclip): the ground
beyond the canton is one flat grey slab with a hard edge, and the horizon fill is a flat grey band.

It goes both ways: from Vivec the world is bare flat ground, and from the open world Vivec cannot be
seen at all. Third owner pose: GLOBAL 49804 -84005 1015 (LOCAL -860 502 253), heading W 254, pitch
5, time 05:32, label "Ascadian Isles Region" (an open-world map east of Vivec): looking west toward
the city there is only flat grey terrain and a flat brown horizon band under the sunrise sky, no
cantons in the distance. The world maps' distant drawing does not contain the city; the preview
frame and the world maps are not merged ("it's not merged into the existing topomap correctly").
Fourth owner pose: GLOBAL 32225 -93454 2106 (LOCAL 376 -323 782), heading NE 059, pitch 30, time
02:08, label "Vivec, St. Delyn": where the St. Delyn canton should stand there is only a flat grey
slab; the canton is missing.

## Where

Town handoff (`aw_world.c`) and door targets.

## How it happened

Partial town sets were never installed together before.

## Why it was not caught

First multi-town city.

## Reproduction

Install one canton and walk off a bridge.

## Repair

Not yet: block or warn at frame edges toward uninstalled towns, or install cantons as a set.

## Verification

Pending.

## Prevention

Builder check of town sets with shared edges.
