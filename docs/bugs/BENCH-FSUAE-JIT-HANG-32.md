# BENCH-FSUAE-JIT-HANG-32: An FS-UAE JIT session hung with a Windows-folder hard file mounted

## Status: 8 October 2026

Open. Cause unknown. Found by the CHIM world-format follow-up (FFS sweep, branch
v0.0.33-chim-format).

## Symptom

One FS-UAE session with the JIT profile stopped making progress for at least 10 minutes while a
hard file in a Windows folder shared into the container was mounted; one row of the JIT table was
left incomplete.

## Where

FS-UAE with the JIT profile; hard file on host storage shared from Windows.

## How it happened

Unknown. Seen once.

## Why it was not caught

First JIT run of the sweep with that hard file.

## Reproduction

Not yet reproduced: rerun the JIT seek sweep with the hard file in a Windows folder, then on a
Docker volume.

## Repair

Not yet. Disk timings use container-native storage anyway
([BENCH-HOST-STORAGE-32](BENCH-HOST-STORAGE-32.md)).

## Verification

Pending.

## Prevention

Benchmark sessions have a time limit and report a stalled session instead of waiting.
