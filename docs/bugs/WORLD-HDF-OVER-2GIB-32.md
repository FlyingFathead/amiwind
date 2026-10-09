# WORLD-HDF-OVER-2GIB-32: The world hard disk image is 32,768 bytes over 2 GiB

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev1 |
| Where | world drive layout (tools/world_volumes.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev1 (last seen) |
| Severity | medium: Disk image 32,768 bytes over 2 GiB may break tools with 2 GiB limits. |
| Family | Disk images, partitions and launchers (`disk-image-layout`) |
| Playtest version | v0.0.32-dev1 |
| From commit | source and engine 978475d |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

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

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Disk images, partitions and launchers (`disk-image-layout`). Classic FFS limits: partitions under 2 GiB, few files per directory; launchers list every disk. See [families](README.md#families).

- [AMIGA-DISK-2GIB-LIMIT-33](AMIGA-DISK-2GIB-LIMIT-33.md): Amiga disk limits: partitions below 2 GiB and starting below 2 GiB, files well under 2 GiB, drive images below 4 GiB
- AW-20260928-17 (no report page): FS-UAE 24-bit-addressing option rejected
- [BENCH-FSUAE-PLAIN-HDF-32](BENCH-FSUAE-PLAIN-HDF-32.md): FS-UAE does not mount a plain 1.5 GiB partition hard file
- [BUILD-HDF-BUFFERS-32](BUILD-HDF-BUFFERS-32.md): Hard disk buffer and MaxTransfer defaults depend on the disk type
- [BUILD-LAYOUT-GATE-AFTER-WRITE-33](BUILD-LAYOUT-GATE-AFTER-WRITE-33.md): The disk-layout gate ran only after the partitions and drives were written, and not on the dry-run image
- [BUILD-WORLD-PARTITION-MOUNT-33](BUILD-WORLD-PARTITION-MOUNT-33.md): Full v0.0.33-dev1 image stops at 'Please insert volume AW_WORLD3': a partition starts beyond 2 GiB
- [EMULATOR-TEMPLATES-WORLD-32](EMULATOR-TEMPLATES-WORLD-32.md): The static emulator templates list only the boot disk, not the world disk
- [FFS-DIRECTORY-HASH-32](FFS-DIRECTORY-HASH-32.md): Thousands of files in one directory are slow to open on a real FFS disk
- HDF-WRITER-01 (no report page): Private image refresh left file-owned blocks marked free
- [WORLD-THIRD-PARTITION-32](WORLD-THIRD-PARTITION-32.md): The world image now needs a fourth partition (DW2); launchers were only used with three

<!-- END GENERATED CATEGORY -->
