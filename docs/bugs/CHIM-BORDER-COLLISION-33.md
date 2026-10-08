# CHIM-BORDER-COLLISION-33: Collision near CHIM chunk borders ignores the neighbour chunk's ground

## Status: 8 October 2026

Open. Found by the second CHIM engine slice (terrain in the world tree; branch v0.0.33-chim-engine).

## Symptom

Each chunk's player hull is expanded only inside its own subtree, so near a border the neighbour's ground
is not felt: up to about 7 units of slope error.

## Where

CHIM builder hull pieces; engine hull 1 grafting.

## How it happened

Hulls are built per chunk.

## Why it was not caught

Host tests only so far; no emulator run on real data.

## Reproduction

Walk across a chunk border on a slope.

## Repair

Not yet: the builder extends hull pieces across borders by the box size.

## Verification

Pending.

## Prevention

A host test crossing borders on slopes.
