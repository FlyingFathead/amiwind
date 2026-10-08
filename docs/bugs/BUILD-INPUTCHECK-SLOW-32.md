# BUILD-INPUTCHECK-SLOW-32: the game data reference check takes over 12 minutes through Docker

## Status: 8 October 2026

Open. Found by the known-inputs work; predates it.

## Symptom

`input_check.inspect` on the GOG installation took 767 s, and 781 s again when only 9 files
needed hashing: the time is not hashing.

## Where

`src/mwad/input_check.py`, `ensure_external()`.

## How it happened

`ensure_external()` runs for every one of about 21,000 files and walks every parent folder twice
looking for `pyproject.toml`: about 10 s per 500 files through the Windows/Docker bind mount.

## Why it was not caught

Build time was never profiled per stage.

## Reproduction

Run the reference check on a full installation inside the build container.

## Repair

Not yet: check the installation root once, not per file; part of the build profiler work.

## Verification

Pending.

## Prevention

Per-stage build timing in the build summary.
