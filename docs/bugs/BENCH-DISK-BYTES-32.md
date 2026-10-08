# BENCH-DISK-BYTES-32: FS-UAE moves disk bytes at about 90 MB/s, so it cannot price what a walk reads

## Status: 8 October 2026

Open (benchmark method). Found by the CHIM world-format follow-up (branch v0.0.33-chim-format).

## Symptom

Emulated hard disk transfers run at about 90 MB/s, far above an A1200 IDE port. An emulator run
therefore prices seeks and AmigaDOS calls but not the bytes read, so it cannot judge CHIM against
the legacy layout over a whole walk, where CHIM reads about 1.8 times the bytes in fewer runs
([CHIM-READ-RUNS-33](CHIM-READ-RUNS-33.md)). At an assumed 2 MB/s IDE rate the Balmora walk would
take about 20.9 s with CHIM and 35.1 s with the legacy layout: an estimate, not a measurement.

## Where

`awbench replay` results in FS-UAE; the CHIM validator's read cost model.

## How it happened

The emulated hard disk is a virtual device backed by the PC's file cache.

## Why it was not caught

First whole-walk comparison of the two layouts.

## Reproduction

`awbench replay` of the walk's read list in FS-UAE: bytes per second far above any real IDE drive.

## Repair

Not yet: one `awbench replay` run of the walk on a real accelerated A1200 (see
[HARDWARE-BENCHMARK.md](../HARDWARE-BENCHMARK.md)); until then byte counts and read runs are the
currency, and any time per byte is an assumption that is labelled as one.

## Verification

Pending a hardware report.

## Prevention

Performance reports state which costs the emulator can price and mark assumed transfer rates.
