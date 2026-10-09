# FFS-DIRECTORY-HASH-32: Thousands of files in one directory are slow to open on a real FFS disk

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Flat maps/ directory in the disk layout (tools/build_aga.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Crowded directory adds about 20 ms per map load in the emulator. |
| Family | Disk images, partitions and launchers (`disk-image-layout`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by an independent review of the open-world plan. First emulator measurement
8 October 2026 (CHIM world-format follow-up, branch v0.0.33-chim-format).

## Symptom

Classic FFS resolves names through 72 hash chains per directory. With thousands of maps in
`maps/`, each open walks long chains (an estimated ~135 block reads for 9,698 maps), which
costs seconds on a real disk and is invisible in the emulator.

## Where

Disk layout written by `tools/build_aga.py` (flat `maps/` directory).

## How it happened

Few maps until now.

## Why it was not caught

The emulator reads host files quickly.

## Reproduction

Count files per directory in a whole-world layout; time opens on a real FFS disk.

Measured in FS-UAE (8 October 2026): the legacy `maps/` folder holds about 2,741 entries. The same
maps loaded alone in a directory and among 2,677 dummy files: median 94 ms against 120 ms per map
load, about 20 ms extra per load from the crowded directory alone, in the emulator. A real disk is
expected to be slower per block read.

## Repair

Not yet: few large spatially ordered pack files (Quake PAK) instead of thousands of loose files.

## Verification

Pending: the emulator figure above; a real FFS disk number is still needed.

## Prevention

The builder reports files per directory with a limit (the classic FFS few-files-per-directory rule
of the disk-layout gate).

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
- HDF-WRITER-01 (no report page): Private image refresh left file-owned blocks marked free
- [WORLD-HDF-OVER-2GIB-32](WORLD-HDF-OVER-2GIB-32.md): The world hard disk image is 32,768 bytes over 2 GiB
- [WORLD-THIRD-PARTITION-32](WORLD-THIRD-PARTITION-32.md): The world image now needs a fourth partition (DW2); launchers were only used with three

Related bugs in other categories:

- [STREAM-FFS-SEEK-32](STREAM-FFS-SEEK-32.md): Random 16 KiB reads on FFS run at 0.44 MB/s and take most of the CPU

<!-- END GENERATED CATEGORY -->
