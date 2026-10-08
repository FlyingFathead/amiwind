# CHIM-FROZEN-ACTORS-33: Frozen CHIM actors: projectiles stop mid-air and timers stop

## Status: 8 October 2026

Open. Found by the second CHIM engine slice (terrain in the world tree; branch v0.0.33-chim-engine).

## Symptom

Actors outside the ring are frozen: a projectile or item leaving the ring freezes in mid-air, QuakeC timers
on frozen entities stop, and an overdue think fires once when an entity unfreezes. The load-game path is
not yet tested.

## Where

`sv_phys.c` freeze hook.

## How it happened

Freezing all non-client movers outside grafted chunks.

## Why it was not caught

Host tests only so far; no emulator run on real data.

## Reproduction

Fire a projectile out of the ring; save and load near the ring edge.

## Repair

Not yet: review per entity type (remove projectiles leaving the ring, keep timers running, no burst
of overdue thinks); test the load path.

## Verification

Pending.

## Prevention

Host tests per entity type and for load.
