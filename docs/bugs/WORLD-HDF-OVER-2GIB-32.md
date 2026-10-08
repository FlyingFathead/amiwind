# WORLD-HDF-OVER-2GIB-32: The world hard disk image is 32,768 bytes over 2 GiB

## Status: 8 October 2026

Open. Found in the v0.0.32-dev1 delivery checks.

## Symptom

The dev1 world hard disk image is 2,147,516,416 bytes: 32,768 bytes over 2 GiB (2^31), although
each partition on it is under 2 GiB. Tools or file systems with a 2 GiB file limit (signed 32-bit
offsets) may refuse or truncate it.

## Where

World drive layout written by the builder (`tools/world_volumes.py`, the image step's RDB writer).

## How it happened

The drive size is the sum of its partitions plus the RDB area; with flora the partitions grew
([WORLD-THIRD-PARTITION-32](WORLD-THIRD-PARTITION-32.md)) and the total crossed 2^31.

## Why it was not caught

The disk-layout rules check partitions and files inside the volumes, not the size of the hard disk
image file itself. The project rule asks for files well under 2 GiB.

## Reproduction

Size of the world hard disk image in the dev1 payload.

## Repair

Not yet: cap each world drive image below 2 GiB with margin (move a partition to the next drive),
or document which tools need large-file support.

## Verification

Pending.

## Prevention

The disk-layout gate checks every hard disk image file against a limit well under 2 GiB.
