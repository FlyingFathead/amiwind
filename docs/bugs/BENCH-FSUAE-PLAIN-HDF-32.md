# BENCH-FSUAE-PLAIN-HDF-32: FS-UAE does not mount a plain 1.5 GiB partition hard file

## Status: 8 October 2026

Open (emulator behaviour). Found by the CHIM world-format follow-up (FFS sweep, branch
v0.0.33-chim-format).

## Symptom

A 1.5 GiB hard file holding one FFS partition without an RDB is not mounted by FS-UAE; the same
partition inside an RDB disk mounts and reads normally.

## Where

FS-UAE hard file handling; benchmark disks made outside the builder.

## How it happened

Emulator behaviour for large plain partition hard files.

## Why it was not caught

Benchmark disks were small plain partitions until the size sweep.

## Reproduction

Make a 1.5 GiB plain FFS partition hard file and mount it in FS-UAE.

## Repair

Benchmark disks of that size use an RDB wrapper, as the builder's world disks do.

## Verification

The RDB variant mounted and ran the sweep (8 October 2026).

## Prevention

Benchmark disk tooling writes RDB disks for large partitions.
