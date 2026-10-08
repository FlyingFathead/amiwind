# TEST-NATIVE-TMPDIR-32: A native test overflows a 64-byte name buffer when the temp path is long

## Status: 8 October 2026

Fixed in source on v0.0.32-dev. Found by the parallel test runner work.

## Symptom

`tests/test_bsp_slice_load_native.py` aborts with "buffer overflow detected" when TMPDIR makes the temporary
.bsp path longer than about 63 characters: the harness copies the path into Quake's fixed 64-byte model
name.

## Where

The native test harness for the slice loader; Quake `model_t.name` (64 bytes).

## How it happened

The harness passes a full host temp path where the engine expects a short game path.

## Why it was not caught

Default temp paths are short.

## Reproduction

Run the test with a long TMPDIR.

## Repair

The test passes short relative names (the harness runs in the temp folder) and now always uses a
deliberately long temp path, so a regression shows at once.

## Verification

The test passes with a temp path over 63 characters; with the old absolute names it fails
(checked in Docker). Full suite in the gate.

## Prevention

Run the native tests once with a long TMPDIR in the suite.
