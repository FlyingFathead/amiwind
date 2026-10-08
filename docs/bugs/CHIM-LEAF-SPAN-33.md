# CHIM-LEAF-SPAN-33: 160 of 1,488 Balmora placements span more than 16 leaves

## Status: 8 October 2026

Open. Found by the first CHIM world-format build of Balmora (branch v0.0.33-chim-format, format 0.1).

## Symptom

160 placements touch more than 16 leaves (up to 237 leaves and 36 chunks), the limit at which Quake
treats an entity as visible everywhere (MAX_ENT_LEAFS).

## Where

CHIM placements; engine efrag linking.

## How it happened

Large buildings and walls span many leaves.

## Why it was not caught

First measurement.

## Reproduction

The CHIM validator report (flag on the placement record).

Still 160 placements in the format 0.3 statistics (8 October 2026): they are always sent, so
their faces count in every view ([CHIM-VIEW-FACES-33](CHIM-VIEW-FACES-33.md)). Candidate owner:
splitting large placements into pieces that each touch at most 16 leaves, or chunk-level linking.

## Repair

Not yet: chunk-level linking for flagged placements in the engine (format records the flag).

## Verification

Pending.

## Prevention

The validator counts flagged placements.
