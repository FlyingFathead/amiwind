# RENDER-VISEDICTS-OVERFLOW-32: Entities beyond MAX_VISEDICTS (1,112) are dropped silently

## Status: 8 October 2026

Open. Found by the CHIM engine work; applies to the legacy engine too.

## Symptom

`R_StoreEfrags` drops entities beyond `MAX_VISEDICTS` (1,112) without any warning. Balmora views reach up to
451 placements plus NPCs today; denser towns or CHIM rings could exceed the limit, and objects would
vanish with no message.

## Where

`engine/aga/src/r_efrag.c` (`R_StoreEfrags`), `MAX_VISEDICTS`.

## How it happened

Upstream Quake behaviour.

## Why it was not caught

No counter for it.

## Reproduction

Force more than 1,112 visible entities.

## Repair

Not yet: count drops in the renderer counters, warn once in the console; size the limit from measurements.

## Verification

Pending.

## Prevention

A counter in `dbg rcount` and a check in the benchmark route.
