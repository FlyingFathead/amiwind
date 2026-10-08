# MODEL-SLOTS-256-32: Some Vivec interiors exceed the engine's 256 model slots; the heap check does not catch it

## Status: 8 October 2026

Open. Found by the map loader rework (decoding without staging).

## Symptom

vi027, vi058 and vi133 stop both loaders with `mod_numknown == MAX_MOD_KNOWN` (256 model slots);
the heap check passes them.

## Where

`engine/aga/src/model.c` (MAX_MOD_KNOWN) and the builder checks.

## How it happened

Each interior object is its own model (INTERIOR-INLINE-LIMIT-31) plus the game's other models.

## Why it was not caught

The heap check counts bytes, not model slots.

## Reproduction

Load vi027 in the engine.

## Repair

Not yet: the builder checks model slots per map; the lasting fix is interior placements
(INTERIOR-INLINE-LIMIT-31).

## Verification

Pending.

## Prevention

Model slot count in the builder limits check.
