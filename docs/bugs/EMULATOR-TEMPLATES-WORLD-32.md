# EMULATOR-TEMPLATES-WORLD-32: The static emulator templates list only the boot disk, not the world disk

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev1 |
| Where | Static emulator templates (resources/emulators) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31, v0.0.32-dev1 (last seen) |
| Severity | medium: A player starting from a template gets no world partitions. |
| Family | Disk images, partitions and launchers (`disk-image-layout`) |
| Playtest version | v0.0.32-dev1 |
| From commit | source and engine 978475d |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Present in v0.0.31 and v0.0.32-dev1. Found in the v0.0.32-dev1 delivery checks.

## Symptom

The static templates in `resources/emulators/` do not include the world disk: the `.fs-uae` file
names only the boot hard disk image, and the WinUAE `.uae` file names no hard disk and asks the
player to select the boot image. A player who starts from a template
instead of a launcher gets no world partitions. The launchers add the world disk correctly.

## Where

`resources/emulators/AmiWind-<version>-FS-UAE.fs-uae`, `AmiWind-<version>-WinUAE.uae` and their
generator (`tools/emulator_configs.py`).

## How it happened

The templates were written for the single-disk layout and not updated when the world moved to its
own drive.

## Why it was not caught

Smoke tests use the launchers, never the templates.

## Reproduction

Read the dev1 templates: the FS-UAE one has one hard drive entry (the boot image), the WinUAE one
none.

## Repair

Not yet: generate the templates from the same drive list the launchers use (boot and world disks,
every partition), or remove them in favour of the launchers.

## Verification

Pending: boot from each template in FS-UAE and WinUAE and check every partition is mounted.

## Prevention

A test that the templates and the launchers list the same drives.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Disk images, partitions and launchers (`disk-image-layout`). Classic FFS limits: partitions under 2 GiB, few files per directory; launchers list every disk. See [families](README.md#families).

- [AMIGA-DISK-2GIB-LIMIT-33](AMIGA-DISK-2GIB-LIMIT-33.md): Amiga disk limits: partitions below 2 GiB and starting below 2 GiB, files well under 2 GiB, drive images below 4 GiB
- AW-20260928-17 (no report page): FS-UAE 24-bit-addressing option rejected
- [BENCH-FSUAE-PLAIN-HDF-32](BENCH-FSUAE-PLAIN-HDF-32.md): FS-UAE does not mount a plain 1.5 GiB partition hard file
- [BUILD-HDF-BUFFERS-32](BUILD-HDF-BUFFERS-32.md): Hard disk buffer and MaxTransfer defaults depend on the disk type
- [BUILD-LAYOUT-GATE-AFTER-WRITE-33](BUILD-LAYOUT-GATE-AFTER-WRITE-33.md): The disk-layout gate ran only after the partitions and drives were written, and not on the dry-run image
- [BUILD-WORLD-PARTITION-MOUNT-33](BUILD-WORLD-PARTITION-MOUNT-33.md): Full v0.0.33-dev1 image stops at 'Please insert volume AW_WORLD3': a partition starts beyond 2 GiB
- [FFS-DIRECTORY-HASH-32](FFS-DIRECTORY-HASH-32.md): Thousands of files in one directory are slow to open on a real FFS disk
- HDF-WRITER-01 (no report page): Private image refresh left file-owned blocks marked free
- [WORLD-HDF-OVER-2GIB-32](WORLD-HDF-OVER-2GIB-32.md): The world hard disk image is 32,768 bytes over 2 GiB
- [WORLD-THIRD-PARTITION-32](WORLD-THIRD-PARTITION-32.md): The world image now needs a fourth partition (DW2); launchers were only used with three

<!-- END GENERATED CATEGORY -->
