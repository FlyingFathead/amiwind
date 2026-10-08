# BUILD-MOJIBAKE-32: A builder error message contains mojibake

## Status: 8 October 2026

Open. Found by the builder coverage work (comparing the v0.0.31 harvest files with their plan).

## Symptom

The `--name` length error in `tools/build.py` reads "1Ã¢â‚¬â€œ64" instead of "1-64".

## Where

`tools/build.py`.

## How it happened

A dash was encoded twice at some point.

## Why it was not caught

Harvest data was prepared outside the builder and carried forward in patched images
(BUILD-HARVEST-NOT-BUILT-32), so no gate re-checked it against the maps it ships with.

## Reproduction

Compare the shipped harvest catalogues' pinned map hashes with the shipped maps.

## Repair

Not yet: plain ASCII text; a test that builder messages are clean UTF-8 without mojibake.

## Verification

Pending.

## Prevention

Harvest becomes a builder step that rebuilds its catalogues from the maps it ships with, with
the geometry gate in the image step.
