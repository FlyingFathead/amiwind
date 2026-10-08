# CHIM-ACTORS-OUTSIDE-RING-33: Actors outside the CHIM ring have no terrain collision

## Status: 8 October 2026

Open. Found by the first CHIM engine slice (branch v0.0.33-chim-engine).

## Symptom

Actors outside the loaded ring have no CHIM collision; actors that settle in the first server frames,
before the ring is primed, would fall through chunk terrain.

## Where

Server physics with CHIM chunks.

## How it happened

Collision exists only for loaded chunks.

## Why it was not caught

First CHIM engine slice; host tests only, no emulator run yet.

## Reproduction

Spawn an actor outside the ring.

## Repair

Not yet: freeze actors outside the ring (Morrowind only runs cells around the player), or keep a
coarse terrain hull resident.

## Verification

Pending.

## Prevention

A host test for actors at ring edges.
