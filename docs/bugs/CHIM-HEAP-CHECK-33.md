# CHIM-HEAP-CHECK-33: The heap check does not account for a CHIM map's zone bank

## Status: 8 October 2026

Open. Found by the first CHIM engine slice (branch v0.0.33-chim-engine).

## Symptom

`tools/check_world_map_heap.py` does not include the CHIM model zone bank taken from the Hunk.

## Where

`tools/check_world_map_heap.py`.

## How it happened

The zone is new.

## Why it was not caught

First CHIM engine slice; host tests only, no emulator run yet.

## Reproduction

Run the heap check on a CHIM frame.

## Repair

Not yet: model the zone bank and chunk directory in the heap check.

## Verification

Pending.

## Prevention

A heap-check test for CHIM maps.
