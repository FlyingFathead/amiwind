# CHIM-HULL2-33: CHIM terrain uses the player hull for large entities

## Status: 8 October 2026

Open. Found by the second CHIM engine slice (terrain in the world tree; branch v0.0.33-chim-engine).

## Symptom

Format 0.1 stores one standing hull, so entities larger than 32 units collide with terrain as if they
were player-sized.

## Where

CHIM format hulls; engine hull 2.

## How it happened

One hull stored to save space.

## Why it was not caught

Host tests only so far; no emulator run on real data.

## Reproduction

A large creature on CHIM terrain.

## Repair

Not yet: decide whether hull 2 is needed (which actors are large); store it or clamp.

## Verification

Pending.

## Prevention

A host test with a large entity.
