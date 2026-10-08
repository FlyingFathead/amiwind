# LAMPS-CACHE-31: Night lamps beyond 96 per 3x3 cells are silently dropped (Vivec)

## Status: 8 October 2026

Open. Found by the whole-world measurement (every object placed, estimated per map, checked on 30 converted maps).

## Symptom

The night lamp table keeps at most 96 lamps for the 3x3 cells around the player and ignores
the rest. Vivec cells (2..4, -13..-10) hold 100-102 exterior lamps, so 4-6 never light; this
includes the Arena cell (4,-11). Nowhere else exceeds 13 % of the cache.

## Where

`engine/aga/src/aw_lamps.c`.

## How it happened

A fixed cache sized for Balmora and Seyda Neen.

## Why it was not caught

No converted area reached it.

## Reproduction

Count lamps per 3x3 cells in Vivec from the lamp table.

## Repair

Fixed in source (v0.0.32-dev): the cache holds 256 lamps (36 bytes each), drops are
counted and shown by `dbg lamps`, and `tools/night_lighting.py` refuses a lamp table whose
busiest 3 x 3 cells exceed the cache.

## Verification

Engine test with 300 lamps in one cell: 256 kept, 44 counted as dropped; builder
test refuses 257 lamps around one cell. Gate 094 green. In-game check in Vivec pending.

## Prevention

The builder reports the worst 3x3 lamp count per world.
