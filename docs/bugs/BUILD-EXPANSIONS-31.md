# BUILD-EXPANSIONS-31: Tribunal and Bloodmoon cannot be converted with today's tools

## Status: 8 October 2026

Open. Found by the whole-world measurement (every object placed, estimated per map, checked on 30 converted maps).

## Symptom

The ESM loader rejects plugins, interiors read Morrowind.esm only and mesh export opens
Morrowind.bsa only: 1,112 expansion maps are out of reach. Measured anyway: Tribunal 95 maps
(34 over a limit), Bloodmoon 1,017 (126 over; 10 Solstheim regions exceed 600 edicts even
today, Lake Fjalding up to 989; 79 snow-forest regions over texinfo).

## Where

The ESM/BSA readers in the converters.

## How it happened

Only the base game was in scope.

## Why it was not caught

Not a goal until the whole-world plan.

## Reproduction

Point the converters at Tribunal.esm.

Related: the Toolkit's town labels come from Morrowind.esm only, so Solstheim cells have no
labels on the map metrics layer.

## Repair

Not yet: load plugins in order with record overrides; read every BSA.

## Verification

Pending.

## Prevention

Builder test with a synthetic plugin.
