# REMOTE-STATE-WIDTH-31: Remote state file printed "51.*ld" for fractional fields

## Status: 8 October 2026

Fixed in source on the FPU fixes branch before any build left it; never released.

## Symptom

In an emulator benchmark with the FPU-fixes engine, `AWCTL:state.txt` showed
`frame_ms 51.*ld` (and the same for `realtime` and `angles`) instead of numbers.

## Where

`engine/aga/src/aw_remote.c`, the fixed-point formatter added to keep float
formatting out of the state file ([ENGINE-FPU-UNIMPL-31](ENGINE-FPU-UNIMPL-31.md)).

## How it happened

The formatter used a `*` field width (`%0*ld`). The Amiga C library does not
support `*` widths and printed the text literally.

## Why it was not caught

The host test of the remote pipe runs with the Linux C library, which supports
`*` widths; only the Amiga build shows the fault.

## Reproduction

Run the remote pipe (`aw_remote 1`) with the affected build and read
`state.txt`.

## Repair

Explicit `%01ld`/`%02ld` formats instead of a `*` width.

## Verification

8 October 2026: rebuilt engine in a remote session wrote `frame_ms 16.2` and
`angles -2.8 112.5`; the gate suite includes the new format test.

## Prevention

`tests/test_check_fpu_unimplemented.py` fails on any `*` field width in an engine
printf format string.
