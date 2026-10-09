# BUILD-WORLD-PARTITION-MOUNT-33: Full v0.0.33-dev1 image stops at 'Please insert volume AW_WORLD3': a partition starts beyond 2 GiB

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | image step drive grouping (tools/world_volumes.py) and the RDB it writes |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | high: The full two-disk image does not boot past the loader (measured in FS-UAE 3.1.66 with Kickstart 3.1). |
| Family | Disk images, partitions and launchers (`disk-image-layout`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | v0.0.33-dev1 full build (full-033a) |
| From commit | source 7fa9b3a, engine 7fa9b3a, CHIM world 7fa9b3a |
| CHIM engine version | CHIM 0.1.0, engine 7fa9b3a, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open, repair ready on branch `v0.0.33-world-partition`. Verified on a repacked copy of the dev1 world
disk; the next full build verifies it end to end.

## Symptom

The full two-disk v0.0.33-dev1 image does not boot in FS-UAE 3.1.66 (Kickstart 3.1 A1200 ROM, the
playtest JIT profile). The hardware preflight passes, "Loading AmiWind v0.0.33-dev1" appears, then a
system requester asks "Please insert volume AW_WORLD3 in any drive" and stays. A MiniWind image (one
disk, partitions DH0 and DW0) and v0.0.32 (two world partitions) boot.

## Where

The image step of the builder: the drive grouping in `tools/world_volumes.py` (`hardfile_groups`) and
the RDB drives `tools/build_aga.py` writes from it.

## How it happened

The world disk `AmiWind-v0.0.33-dev1-world-01.hdf` (2,415,951,872 bytes) carried three partitions in
volume order:

| Partition | Volume | Start (bytes) | Size |
| --- | --- | --- | --- |
| DW1 | AW_WORLD1 | 32,768 | 1,920 MiB |
| DW2 | AW_WORLD2 | 2,013,298,688 | 256 MiB |
| DW3 | AW_WORLD3 (CHIM world) | 2,281,734,144 | 128 MiB |

All three are DOS\1 FFS, automount on, DosEnvec identical apart from the cylinders; each volume
carries the right label and reads back with the host tools. FS-UAE mounts the device for all three
partitions, but AmigaDOS (`Info`, run from a changed copy of the boot disk) reports
`DW3: Unreadable disk` and the requester "Not a DOS disk in device DW3"; the volume list has
AW_WORLD0 to AW_WORLD2 only. The engine adds `AW_WORLD0:id1` to `AW_WORLD3:id1` to its search path
from `world/volumes.awv` (count 4), so the first lookup that reaches the fourth path asks for the
missing volume.

DW3 is the only partition that starts at or beyond 2 GiB (2^31 bytes) of its drive. Partitions that
only end beyond 2 GiB work (DW2 ends at 2,281,734,144; DW0 on the boot disk ends at 4,026,564,608).
The drive grouping only kept each drive below 4 GiB; adding the CHIM world as a fourth world
partition put it behind 2,176 MiB of other partitions.

## Why it was not caught

The disk-layout checks looked at sizes (each partition below 2 GiB, each drive below 4 GiB), not at
start offsets. The image step reads every partition back with the host's Amiga file system tools,
which address the whole file and have no such limit, and the full two-disk image with the CHIM
volume had not been booted before.

## Reproduction

Boot fresh copies of `AmiWind-v0.0.33-dev1.hdf` and `AmiWind-v0.0.33-dev1-world-01.hdf` in FS-UAE
3.1.66 with Kickstart 3.1: the requester for AW_WORLD3 appears at load. A/B: the same three
partition images rebuilt in the order DW3, DW1, DW2 (DW3 at 32,768; DW2 now at 2,147,516,416, just
past 2 GiB) mount DW3 as AW_WORLD3 and fail DW2 with "Not a DOS disk": the failure follows the start
offset, not the partition contents.

## Repair

`hardfile_groups` places a partition on a drive only when the drive stays below 4 GiB and every
partition on it starts below 2 GiB. A drive that already fits keeps its order byte for byte; when
the volume order does not fit, the largest partition moves last (the order with the lowest last
start); when neither fits, the partition starts the next drive. For the dev1 sizes the world disk
becomes DW2, DW3, DW1 (starts 32,768; 268,468,224; 402,685,952) and stays one file of
2,415,951,872 bytes. The image step also gates the partition table as written: any partition that
starts at or beyond 2 GiB of its drive stops the build (`require_mountable`).

Owner order (9 October 2026): the image step now runs one disk-layout gate on every drive it writes,
for every image type the builder makes (full, MiniWind, release): `world_volumes.require_disk_layout`
checks every partition's start offset and size below 2 GiB, every file below 1 GiB (well under the
2 GiB file limit) and the drive below 4 GiB, names the drive, partition or file with the measured
value and the limit when one fails, and records the measured layout (start, size and largest file per
partition) as `disk_layout` in build.json.

## Verification

The dev1 partition images repacked with the new grouping and the builder's own `rdbtool` command
shape: the unchanged dev1 boot disk with that world disk boots to the main menu in FS-UAE 3.1.66.
Tests: `tests/test_world_volumes_layout.py` (the dev1 layout, order kept when it fits, largest last
only when needed, 500 generated layouts all mountable, the gate refusing DW3 at 2,281,734,144, and
the image step calling the gate). The next full build verifies the builder end to end.

## Prevention

The partition start limit is part of the drive grouping and a gate on the written RDB of every
drive. Which component holds the limit (the ROM FastFileSystem or the emulated device) was not
isolated; the rule applies to every launcher.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Disk images, partitions and launchers (`disk-image-layout`). Classic FFS limits: partitions under 2 GiB, few files per directory; launchers list every disk. See [families](README.md#families).

- [AMIGA-DISK-2GIB-LIMIT-33](AMIGA-DISK-2GIB-LIMIT-33.md): Amiga disk limits: partitions below 2 GiB and starting below 2 GiB, files well under 2 GiB, drive images below 4 GiB
- AW-20260928-17 (no report page): FS-UAE 24-bit-addressing option rejected
- [BENCH-FSUAE-PLAIN-HDF-32](BENCH-FSUAE-PLAIN-HDF-32.md): FS-UAE does not mount a plain 1.5 GiB partition hard file
- [BUILD-HDF-BUFFERS-32](BUILD-HDF-BUFFERS-32.md): Hard disk buffer and MaxTransfer defaults depend on the disk type
- [BUILD-LAYOUT-GATE-AFTER-WRITE-33](BUILD-LAYOUT-GATE-AFTER-WRITE-33.md): The disk-layout gate ran only after the partitions and drives were written, and not on the dry-run image
- [EMULATOR-TEMPLATES-WORLD-32](EMULATOR-TEMPLATES-WORLD-32.md): The static emulator templates list only the boot disk, not the world disk
- [FFS-DIRECTORY-HASH-32](FFS-DIRECTORY-HASH-32.md): Thousands of files in one directory are slow to open on a real FFS disk
- HDF-WRITER-01 (no report page): Private image refresh left file-owned blocks marked free
- [WORLD-HDF-OVER-2GIB-32](WORLD-HDF-OVER-2GIB-32.md): The world hard disk image is 32,768 bytes over 2 GiB
- [WORLD-THIRD-PARTITION-32](WORLD-THIRD-PARTITION-32.md): The world image now needs a fourth partition (DW2); launchers were only used with three

<!-- END GENERATED CATEGORY -->
