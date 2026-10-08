# AUDIO-MISSING-SOURCES-32: The image step reports missing sources for 7 voices and 2 effects

## Status: 8 October 2026

Open. Found in the v0.0.32-dev1 image logs (r5 and r6, same numbers).

## Symptom

The image step warns "[warning: missing source] voices: 7" and "effects: 2": nine sounds the catalogue expects
are not found in the inputs.

## Where

Image step audio staging.

## How it happened

Unknown.

## Why it was not caught

It is a warning, not a gate.

## Reproduction

dev1 image log.

## Repair

Not yet: list the nine, compare with v0.0.31's payload, decide which are real gaps.

## Verification

Pending.

## Prevention

Missing sources counted in the build summary with a limit of zero for shipped sounds.
