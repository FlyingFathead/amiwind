# CHIM-PACK-DIRS-33: CHIM pack directories are fully resident and would grow to about 400 KB for the island

## Status: 8 October 2026

Open. Found by the first CHIM engine slice (branch v0.0.33-chim-engine).

## Symptom

Model and texture pack directories stay resident at 12 bytes per entry: about 6 KB for Balmora, about
400 KB for the island's roughly 33,000 variants.

## Where

CHIM pack directories.

## How it happened

Format 0.1 keeps one directory per pack.

## Why it was not caught

First CHIM engine slice; host tests only, no emulator run yet.

## Reproduction

Count directory entries.

The format 0.2 index would hold about 0.8 MB of model directory for the island's ~33,000 variants
(CHIM format work, 8 October 2026).

## Repair

Not yet: per-frame directories or offsets in chunk records.

## Verification

Pending.

## Prevention

A memory budget line for directories in the heap check.
