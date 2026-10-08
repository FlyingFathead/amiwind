# CHIM-READ-BUDGET-33: CHIM per-frame read budget can be exceeded by a whole lump

## Status: 8 October 2026

Open. Found by the first CHIM engine slice (branch v0.0.33-chim-engine).

## Symptom

A frame can read its budget plus one whole lump of a streamed model: 40,996 bytes against a 4,096-byte
budget in the test. Balmora's largest model is 366 KB, so a frame could stall badly.

## Where

CHIM model streaming (`chim_models`).

## How it happened

Sections are decoded whole.

## Why it was not caught

First CHIM engine slice; host tests only, no emulator run yet.

## Reproduction

The engine host test with a large model and a small budget.

## Repair

Not yet: resumable section decoders, or models split into budget-sized pieces by the builder.

## Verification

Pending.

## Prevention

A host test that no frame exceeds the budget by more than a fixed margin.
