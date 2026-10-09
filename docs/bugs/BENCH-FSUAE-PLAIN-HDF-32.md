# BENCH-FSUAE-PLAIN-HDF-32: FS-UAE does not mount a plain 1.5 GiB partition hard file

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.33-dev |
| Where | FS-UAE hard file handling for large benchmark disks |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: Emulator behaviour; large benchmark disks use an RDB wrapper as a workaround. |
| Family | Disk images, partitions and launchers (`disk-image-layout`) |

<!-- END GENERATED FACTS -->

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

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Disk images, partitions and launchers (`disk-image-layout`). Classic FFS limits: partitions under 2 GiB, few files per directory; launchers list every disk. See [families](README.md#families).

- [AMIGA-DISK-2GIB-LIMIT-33](AMIGA-DISK-2GIB-LIMIT-33.md): Amiga disk limits: partitions below 2 GiB and starting below 2 GiB, files well under 2 GiB, drive images below 4 GiB
- AW-20260928-17 (no report page): FS-UAE 24-bit-addressing option rejected
- [BUILD-HDF-BUFFERS-32](BUILD-HDF-BUFFERS-32.md): Hard disk buffer and MaxTransfer defaults depend on the disk type
- [BUILD-LAYOUT-GATE-AFTER-WRITE-33](BUILD-LAYOUT-GATE-AFTER-WRITE-33.md): The disk-layout gate ran only after the partitions and drives were written, and not on the dry-run image
- [BUILD-WORLD-PARTITION-MOUNT-33](BUILD-WORLD-PARTITION-MOUNT-33.md): Full v0.0.33-dev1 image stops at 'Please insert volume AW_WORLD3': a partition starts beyond 2 GiB
- [EMULATOR-TEMPLATES-WORLD-32](EMULATOR-TEMPLATES-WORLD-32.md): The static emulator templates list only the boot disk, not the world disk
- [FFS-DIRECTORY-HASH-32](FFS-DIRECTORY-HASH-32.md): Thousands of files in one directory are slow to open on a real FFS disk
- HDF-WRITER-01 (no report page): Private image refresh left file-owned blocks marked free
- [WORLD-HDF-OVER-2GIB-32](WORLD-HDF-OVER-2GIB-32.md): The world hard disk image is 32,768 bytes over 2 GiB
- [WORLD-THIRD-PARTITION-32](WORLD-THIRD-PARTITION-32.md): The world image now needs a fourth partition (DW2); launchers were only used with three

<!-- END GENERATED CATEGORY -->
