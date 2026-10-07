# SEYDA-LANTERNS-MISSING-31: Seyda Neen's lanterns light the night but are not in its maps

## Status: 7 October 2026

Open. Owner report on v0.0.31-dev5; cause known.

## Symptom

At night in Seyda Neen, walls are lit by lamp light with no lantern to be seen
("searchlights").

## Where

The night lamp table (`id1/world/lamps.awl`, written by
`tools/light_sources.py` from the original placements) lists Seyda Neen's
lanterns; the Seyda Neen maps do not contain their meshes.

## How it happened

The Seyda Neen scenery index used to build the Seyda maps has no light
placements (LIGH records), so the eight `light_com_lantern_02` lanterns and the
opening lantern never reached the maps, while the lamp table, built from the
original data, has them.

## Why it was not caught

The lamp table was checked against the census, not against the meshes present
in each map.

## Reproduction

v0.0.31-dev5, Seyda Neen at night near the houses by the docks; `dbg lamps`
lists lamps where no lantern is drawn.

## Repair

Not yet: add light placements to the Seyda Neen scenery conversion so the
lantern meshes are in the maps. Until then the lamp light is correct in place
but its lantern is invisible.

## Verification

Pending.

## Prevention

A lights gate per map: every lit lamp must have its mesh in that map, or be
reported.
